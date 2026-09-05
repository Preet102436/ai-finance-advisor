"""POST /chat/messages - RAG-backed chat endpoint.

Wires chatbot_prototype.py's retrieval/prompt/LLM logic to the current
user's real transactions and budgets: retrieves relevant rows, builds a
grounded prompt, calls the LLM, and logs the exchange (including the
retrieved context) into chat_messages.

TODO (not implemented yet):
- GET /chat/messages   fetch current user's chat history
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from chatbot_prototype import build_context_block, build_prompt, call_llm, retrieve_relevant_transactions
from database import get_db
from deps import get_current_user
from finance_data import load_user_budgets, load_user_transactions
from models import ChatMessage, User

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    message_id: int
    answer: str
    retrieved_context: str


@router.post("/messages", response_model=ChatResponse)
def send_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transactions = load_user_transactions(db, current_user.user_id, lookback_days=90)
    budgets = load_user_budgets(db, current_user.user_id)

    retrieved = retrieve_relevant_transactions(
        payload.question, transactions=transactions, known_categories=budgets.keys()
    )
    prompt = build_prompt(payload.question, retrieved, budgets=budgets)
    retrieved_context = build_context_block(retrieved)

    answer = call_llm(prompt)
    if not answer:
        # None: no OPENAI_API_KEY configured. Empty string: the model call
        # succeeded but returned no content (seen with real "gpt-5" calls) -
        # either way there's no real answer to show. Fall back to a plain-
        # language message built from the already-human-readable
        # retrieved_context, never the raw LLM prompt (which is full of
        # instructions/formatting meant for a model, not a person).
        if retrieved_context:
            answer = (
                "I can't put together a personalised answer right now, but here's what I "
                "found in your recent transactions that relates to your question:\n\n"
                + retrieved_context
            )
        else:
            answer = (
                "I don't have any transaction history to answer that yet. Try syncing your "
                "bank account or uploading a receipt on the Transactions page first."
            )

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
