"""Shared helpers for loading a user's real transactions/budgets in the shape
chatbot_prototype.py's functions expect: transactions as
{date, category, amount, merchant} dicts, budgets as {category: amount}.

Used by /chat/messages and /savings/suggestions.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from models import BankAccount, Budget, Category, Transaction


def load_user_transactions(
    db: Session,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    lookback_days: int | None = None,
):
    """Pass either an explicit start_date/end_date window, or lookback_days
    (days back from today); leave all three None for full history."""
    if start_date is None and lookback_days is not None:
        start_date = date.today() - timedelta(days=lookback_days)

    query = (
        db.query(Transaction, Category.name)
        .join(BankAccount, Transaction.account_id == BankAccount.account_id)
        .outerjoin(Category, Transaction.category_id == Category.category_id)
        .filter(BankAccount.user_id == user_id)
    )
    if start_date is not None:
        query = query.filter(Transaction.txn_date >= start_date)
    if end_date is not None:
        query = query.filter(Transaction.txn_date <= end_date)

    return [
        {
            "date": txn.txn_date.isoformat(),
            "category": category_name or "uncategorised",
            "amount": float(txn.amount),
            "merchant": txn.merchant or "",
        }
        for txn, category_name in query.all()
    ]


def load_user_budgets(db: Session, user_id: int):
    """{category: amount}, using each category's most recently generated budget."""
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
