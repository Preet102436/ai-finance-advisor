"""POST /chat/messages - RAG-backed chat endpoint.

Wires chatbot_prototype.py's retrieval/prompt/LLM logic to the current
user's real transactions and budgets: retrieves relevant rows, builds a
grounded prompt, calls the LLM, and logs the exchange (including the
retrieved context) into chat_messages.

TODO (not implemented yet):
- GET /chat/messages   fetch current user's chat history
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from chatbot_prototype import build_context_block, build_prompt, call_llm, retrieve_relevant_transactions
from database import get_db
from deps import get_current_user
from models import BankAccount, Budget, Category, ChatMessage, Transaction, User

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    message_id: int
    answer: str
    retrieved_context: str


def _load_user_transactions(db: Session, user_id: int, lookback_days: int = 90):
    """Real transactions in chatbot_prototype's expected shape:
    {date, category, amount, merchant}."""
    window_start = date.today() - timedelta(days=lookback_days)
    rows = (
        db.query(Transaction, Category.name)
        .join(BankAccount, Transaction.account_id == BankAccount.account_id)
        .outerjoin(Category, Transaction.category_id == Category.category_id)
        .filter(BankAccount.user_id == user_id, Transaction.txn_date >= window_start)
        .all()
    )
    return [
        {
            "date": txn.txn_date.isoformat(),
            "category": category_name or "uncategorised",
            "amount": float(txn.amount),
            "merchant": txn.merchant or "",
        }
        for txn, category_name in rows
    ]


def _load_user_budgets(db: Session, user_id: int):
    """Real budgets in chatbot_prototype's expected shape: {category: amount},
    using each category's most recently generated budget."""
    rows = (
        db.query(Budget, Category.name)
        .join(Category, Budget.category_id == Category.category_id)
        .filter(Budget.user_id == user_id)
        .order_by(Budget.period_month.desc())
        .all()
    )
    budgets = {}
    for budget, category_name in rows:
        # Ordered most-recent period_month first, so the first time we see a
        # category is its latest budget.
        budgets.setdefault(category_name, float(budget.recommended_amount))
    return budgets


@router.post("/messages", response_model=ChatResponse)
def send_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transactions = _load_user_transactions(db, current_user.user_id)
    budgets = _load_user_budgets(db, current_user.user_id)

    retrieved = retrieve_relevant_transactions(
        payload.question, transactions=transactions, known_categories=budgets.keys()
    )
    prompt = build_prompt(payload.question, retrieved, budgets=budgets)
    retrieved_context = build_context_block(retrieved)

    answer = call_llm(prompt)
    if answer is None:
        answer = (
            "(No LLM API key configured on the server, so this is a preview of what "
            "would have been sent - not a real answer.)\n\n" + prompt
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
