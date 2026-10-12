"""POST /chat/messages - RAG-backed chat endpoint.

Wires chatbot_prototype.py's retrieval/prompt/LLM logic, plus
finance_insights.py's financial-summary + deterministic-answer layer, to the
current user's real transactions and budgets. For specific question types
(affordability, overspending, a monthly summary, savings tips, a next-month
budget, a savings-goal plan, "what if" projections) the answer is computed
directly from the user's real numbers and never depends on the LLM being
reachable. Everything else still goes through the existing retrieval +
prompt + LLM path, now given the full financial summary as extra context
instead of only the keyword-matched transactions.

Each response also carries:
- `sources`: a short, itemised list of what actually grounded this answer
  (e.g. "This month's transactions (18)", "Budget comparison across 4
  categories") so the UI can show real RAG evidence instead of just a claim.
- `suggested_followups`: a handful of contextual next questions, generated
  from the detected intent and the user's own numbers, for the chat UI to
  show as buttons instead of the same static quick prompts every time.

TODO (not implemented yet):
- GET /chat/messages   fetch current user's chat history
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from chatbot_prototype import build_context_block, build_prompt, call_llm, retrieve_relevant_transactions
from database import get_db
from deps import get_current_user
from finance_data import load_latest_forecast, load_user_budgets, load_user_transactions
from finance_insights import (
    build_summary_context_block,
    compute_financial_summary,
    detect_intent,
    deterministic_answer,
    suggested_followups,
)
from models import ChatMessage, User

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    message_id: int
    answer: str
    retrieved_context: str
    sources: list[str] = []
    suggested_followups: list[str] = []


def _offline_fallback_answer(question: str, summary: dict, forecast: dict | None, summary_context: str) -> str:
    """Grounded fallback text for when no LLM is reachable (no
    OPENAI_API_KEY, or the call failed or returned nothing) and
    detect_intent()/deterministic_answer() didn't already handle the
    question with a real computed answer - i.e. intent == "general".

    Regression fix: every such question used to collapse to the exact same
    "I can't reach the AI model... + summary_context" string, so two
    different general-intent questions (e.g. a budget check and a forecast
    question) came back byte-identical (see test_chat_offline_fallback.py).
    This varies the answer by topic, using the same real summary/forecast
    data the rest of the module already has on hand, so unrelated questions
    stop looking like a canned response."""
    q = question.lower()
    prefix = "I can't reach the AI model right now, but"

    if "forecast" in q or "predict" in q:
        if forecast is None:
            return (
                f"{prefix} you haven't generated a balance forecast yet - visit the "
                "Forecasts section of the Dashboard to generate one from your real "
                "transaction history."
            )
        return (
            f"{prefix} here's your most recent forecast: the {forecast['method']} model "
            f"predicts a balance of ${forecast['end_balance']:.2f} by {forecast['end_date']} "
            f"({forecast['days_ahead']} day(s) ahead)."
        )

    if "budget" in q or "overspend" in q:
        over = [c for c in summary["category_vs_budget"] if c["over_budget"]]
        if over:
            lines = [
                f"- {c['category']}: ${c['spent']:.2f} spent vs a ${c['budget']:.2f} budget"
                for c in over
            ]
            return f"{prefix} here's your budget check:\n" + "\n".join(lines)
        if summary["category_vs_budget"]:
            return f"{prefix} you're within budget in every category that has one set this month."
        return (
            f"{prefix} you don't have any budgets set yet - the Budgets page can "
            "generate some from your spending history."
        )

    if "sav" in q:
        if summary["category_deltas"]:
            top = summary["category_deltas"][:3]
            lines = [f"- {c['category']}: ${c['this_month']:.2f} this month" for c in top]
            return (
                f"{prefix} here are your top spending categories, the best place to look "
                "for savings:\n" + "\n".join(lines)
            )
        return f"{prefix} here's your financial summary:\n\n{summary_context}"

    return f"{prefix} here's your financial summary:\n\n{summary_context}"


@router.post("/messages", response_model=ChatResponse)
def send_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 120 days back so the financial summary can compare this month to last
    # month, not just look at a single month in isolation.
    transactions = load_user_transactions(db, current_user.user_id, lookback_days=120)
    budgets = load_user_budgets(db, current_user.user_id)
    summary = compute_financial_summary(transactions, budgets)

    intent = detect_intent(payload.question)
    answer = deterministic_answer(payload.question, summary)
    retrieved_context = build_summary_context_block(summary)

    # Base evidence list for the deterministic / summary-grounded path -
    # built from whatever the summary actually contains, not a fixed claim.
    sources = []
    if summary["transaction_count"] == 0:
        sources.append("General financial guidance (no transaction history yet)")
    else:
        sources.append(f"This month's transactions ({len(transactions)} over the last 120 days)")
        sources.append("Income and expense totals for this month")
        if summary["category_vs_budget"]:
            sources.append(f"Budget comparison across {len(summary['category_vs_budget'])} categories")
        if summary["category_deltas"]:
            sources.append("Spending trends vs last month")

    if answer is None:
        # No specific intent matched (e.g. open-ended questions like "give me
        # a monthly saving plan") - fall back to the RAG + LLM path, but with
        # the full financial summary as context, not just keyword-matched
        # transactions, so the model has real numbers to reason over.
        retrieved = retrieve_relevant_transactions(
            payload.question, transactions=transactions, known_categories=budgets.keys()
        )
        transaction_context = build_context_block(retrieved)
        forecast = load_latest_forecast(db, current_user.user_id)
        prompt = build_prompt(payload.question, retrieved, budgets=budgets, forecast=forecast)
        summary_context = retrieved_context  # keep the summary text for the no-LLM fallback message below
        prompt = (
            "Here is the user's overall financial summary for this month:\n"
            f"{summary_context}\n\n" + prompt
        )

        # Whether or not the LLM is reachable, retrieved_context (the API
        # response field) should show the real transactions this answer is
        # grounded in rather than staying on the generic summary block - it
        # previously only updated on a successful LLM call, so the no-API-key
        # fallback answer never showed the transaction-level evidence behind it.
        retrieved_context = transaction_context or retrieved_context

        llm_answer = call_llm(prompt)
        if llm_answer:
            answer = llm_answer
            sources = [f"Transactions matching your question ({len(retrieved)})"]
            sources.append("This month's financial summary")
        else:
            # None: no OPENAI_API_KEY configured. Empty string: the model call
            # succeeded but returned no content (seen with real "gpt-5" calls).
            # Either way, fall back to real data rather than a generic "I
            # can't help" message - and vary it by question topic so two
            # different offline questions don't come back identical (see
            # _offline_fallback_answer's docstring).
            answer = _offline_fallback_answer(payload.question, summary, forecast, summary_context)

    followups = suggested_followups(intent, summary)

    db.add(ChatMessage(user_id=current_user.user_id, role="user", content=payload.question))
    assistant_message = ChatMessage(
        user_id=current_user.user_id,
        role="assistant",
        content=answer,
        retrieved_context=retrieved_context,
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return ChatResponse(
        message_id=assistant_message.message_id,
        answer=answer,
        retrieved_context=retrieved_context,
        sources=sources,
        suggested_followups=followups,
    )
