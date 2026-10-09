"""Shared helpers for loading a user's real transactions/budgets in the shape
chatbot_prototype.py's functions expect: transactions as
{date, category, amount, merchant} dicts, budgets as {category: amount}.

Used by /chat/messages and /savings/suggestions.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from models import BankAccount, Budget, Category, Forecast, Transaction


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


def load_latest_forecast(db: Session, user_id: int):
    """The most recently generated forecast batch (all rows share the same
    created_at from one POST /forecasts call), summarised as the chatbot
    prompt needs it. None if the user hasn't generated a forecast yet (e.g.
    hasn't opened the Dashboard this session) - /forecasts isn't run
    automatically on every chat message, only on Dashboard load, to avoid a
    chat question silently recomputing and overwriting stored forecast data.
    """
    latest_run = (
        db.query(Forecast.created_at)
        .filter(Forecast.user_id == user_id)
        .order_by(Forecast.created_at.desc())
        .first()
    )
    if latest_run is None:
        return None

    points = (
        db.query(Forecast)
        .filter(Forecast.user_id == user_id, Forecast.created_at == latest_run[0])
        .order_by(Forecast.forecast_date)
        .all()
    )
    if not points:
        return None

    first, last = points[0], points[-1]
    return {
        "method": first.model_version or "unknown",
        "days_ahead": len(points),
        "start_date": first.forecast_date.isoformat(),
        "start_balance": float(first.predicted_balance),
        "end_date": last.forecast_date.isoformat(),
        "end_balance": float(last.predicted_balance),
    }
