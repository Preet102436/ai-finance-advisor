"""POST /chat/messages - RAG-backed chat endpoint.

Wires chatbot_prototype.py's retrieval/prompt/LLM logic to the current
user's real transactions and budgets: retrieves relevant rows, builds a
grounded prompt, calls the LLM, and logs the exchange (including the
retrieved context) into chat_messages.

PUT /chat/messages/{id}/rating - thumbs up/down on an assistant reply.

TODO (not implemented yet):
- GET /chat/messages   fetch current user's chat history
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from chatbot_prototype import (
    build_context_block,
    build_prompt,
    call_llm,
    category_totals_for,
    detect_over_budget_categories,
    generate_savings_suggestions,
    retrieve_relevant_transactions,
)
from database import get_db
from deps import get_current_user
from finance_data import load_latest_forecast, load_user_budgets, load_user_transactions
from models import ChatMessage, User
from schemas import ChatRatingUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    message_id: int
    answer: str
    retrieved_context: str


def _offline_fallback_answer(
    question: str, retrieved: list[dict], retrieved_context: str, budgets: dict, forecast: dict | None
) -> str:
    """Builds a plain-language answer from real data when the LLM is
    unavailable, picking which real data to lead with based on what the
    question is actually asking about - so two different questions never
    both collapse to "here's your 5 most recent transactions"."""
    question_lower = question.lower()

    if not retrieved_context and not budgets and forecast is None:
        return (
            "I don't have any transaction history to answer that yet. Try syncing your "
            "bank account or uploading a receipt on the Transactions page first."
        )

    if any(word in question_lower for word in ("forecast", "predict", "balance", "future")):
        if forecast:
            return (
                f"Based on your {forecast['method']} forecast, your balance is projected to go "
                f"from ${forecast['start_balance']:.2f} on {forecast['start_date']} to "
                f"${forecast['end_balance']:.2f} by {forecast['end_date']} "
                f"({forecast['days_ahead']} days ahead). This is a projection from your recent "
                "spending pattern, not a guarantee."
            )
        return (
            "I don't have a balance forecast yet - visit the Dashboard to generate one, then ask "
            "me again."
        )

    if any(word in question_lower for word in ("budget", "over budget", "status", "on track")):
        totals = category_totals_for(retrieved)
        over_budget = detect_over_budget_categories(totals, budgets) if budgets else {}
        if over_budget:
            lines = [f"- {cat}: ${amt:.2f} over budget" for cat, amt in over_budget.items()]
            return "You're over budget in:\n" + "\n".join(lines)
        if budgets:
            return "You're within budget in every category I have data for right now. Nice work."
        return "You don't have any budgets set yet - set one on the Dashboard to track this."

    if any(word in question_lower for word in ("save", "saving", "reduce", "cut back")):
        suggestions = generate_savings_suggestions(retrieved, budgets) if budgets else []
        if suggestions:
            return "Here's where you could save:\n\n" + "\n".join(f"- {s}" for s in suggestions)
        return "I don't see any categories over budget right now, so there's nothing urgent to cut."

    if retrieved_context:
        return (
            "I can't put together a personalised answer right now, but here's what I "
            "found in your recent transactions that relates to your question:\n\n"
            + retrieved_context
        )
    return (
        "I don't have any transaction history to answer that yet. Try syncing your "
        "bank account or uploading a receipt on the Transactions page first."
    )


@router.post("/messages", response_model=ChatResponse)
def send_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transactions = load_user_transactions(db, current_user.user_id, lookback_days=90)
    budgets = load_user_budgets(db, current_user.user_id)
    forecast = load_latest_forecast(db, current_user.user_id)

    retrieved = retrieve_relevant_transactions(
        payload.question, transactions=transactions, known_categories=budgets.keys()
    )
    prompt = build_prompt(payload.question, retrieved, budgets=budgets, forecast=forecast)
    retrieved_context = build_context_block(retrieved)

    answer = None
    if current_user.ai_enabled:
        try:
            answer = call_llm(prompt)
        except Exception:
            # call_llm() already catches its own API/network errors and
            # returns None - this is a defense-in-depth backstop (same
            # pattern as every other router's external-call try/except) so a
            # chat request can never 500 just because the LLM call misbehaved.
            logger.exception("call_llm raised unexpectedly; falling back to offline behaviour")
            answer = None

    if not answer:
        # None: no OPENAI_API_KEY configured, or the model call failed/returned
        # no content. Either way there's no real answer to show. Fall back to
        # a plain-language message - built from real budgets/forecast/retrieved
        # data, varied by what the question is actually asking about, so
        # different questions never collapse to the same canned sentence just
        # because the LLM is unavailable.
        answer = _offline_fallback_answer(payload.question, retrieved, retrieved_context, budgets, forecast)

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
    )


@router.put("/messages/{message_id}/rating")
def rate_message(
    message_id: int,
    payload: ChatRatingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.message_id == message_id,
            ChatMessage.user_id == current_user.user_id,
            ChatMessage.role == "assistant",
        )
        .first()
    )
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    message.rating = payload.rating
    db.commit()
    return {"message_id": message_id, "rating": payload.rating}
