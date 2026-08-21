"""/budgets router.

TODO (not implemented yet):
- GET  /budgets    list current user's budgets (optionally filter by period_month)
- POST /budgets     create/override a budget for a category+month
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import Date, func
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import BankAccount, Budget, Category, Transaction, User
from schemas import BudgetOut

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _subtract_months(d: date, months: int) -> date:
    year = d.year
    month = d.month - months
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


@router.post("/recommend", response_model=list[BudgetOut])
def recommend_budgets(
    window_months: int = 3,
    savings_target: float = 0.05,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recommend a monthly budget per category from the user's trailing spend.

    Aggregates the last `window_months` complete calendar months of expense
    transactions (amount < 0) per category, takes a recency-weighted average
    (most recent month weighted highest), applies a `savings_target` reduction
    (default 5%), and upserts the result into `budgets` for the current
    calendar month (generated_by='ai_engine').
    """
    today = date.today()
    period_month = today.replace(day=1)
    window_start = _subtract_months(period_month, window_months)

    month_expr = func.date_trunc("month", Transaction.txn_date).cast(Date).label("month")

    rows = (
        db.query(Transaction.category_id, month_expr, func.sum(Transaction.amount).label("total"))
        .join(BankAccount, Transaction.account_id == BankAccount.account_id)
        .filter(
            BankAccount.user_id == current_user.user_id,
            Transaction.txn_date >= window_start,
            Transaction.txn_date < period_month,
            Transaction.category_id.isnot(None),
            Transaction.amount < 0,
        )
        .group_by(Transaction.category_id, month_expr)
        .all()
    )

    by_category: dict[int, list[tuple[date, float]]] = {}
    for category_id, month, total in rows:
        by_category.setdefault(category_id, []).append((month, float(total)))

    if not by_category:
        return []

    category_names = {
        c.category_id: c.name
        for c in db.query(Category).filter(Category.category_id.in_(by_category.keys())).all()
    }

    results = []
    for category_id, monthly in by_category.items():
        monthly.sort(key=lambda pair: pair[0])
        weights = range(1, len(monthly) + 1)
        weighted_sum = sum(abs(total) * w for (_, total), w in zip(monthly, weights))
        weighted_avg = weighted_sum / sum(weights)
        recommended_amount = round(weighted_avg * (1 - savings_target), 2)

        budget = (
            db.query(Budget)
            .filter(
                Budget.user_id == current_user.user_id,
                Budget.category_id == category_id,
                Budget.period_month == period_month,
                Budget.generated_by == "ai_engine",
            )
            .first()
        )
        if budget:
            budget.recommended_amount = recommended_amount
        else:
            budget = Budget(
                user_id=current_user.user_id,
                category_id=category_id,
                period_month=period_month,
                recommended_amount=recommended_amount,
                generated_by="ai_engine",
            )
            db.add(budget)
        db.flush()

        results.append(
            BudgetOut(
                budget_id=budget.budget_id,
                category_id=category_id,
                category_name=category_names.get(category_id, "unknown"),
                period_month=period_month,
                recommended_amount=recommended_amount,
                months_considered=len(monthly),
                generated_by="ai_engine",
            )
        )

    db.commit()
    return results
