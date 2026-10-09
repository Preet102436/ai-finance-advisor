"""GET /insights - plain-language analysis of the current user's real spending:
month-over-month category trends, budget overspend warnings, and an
end-of-month spend prediction. All computed from real transactions/budgets,
no LLM call - deterministic and always available.
"""

import calendar
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import BankAccount, Budget, Category, Transaction, User
from schemas import InsightOut

router = APIRouter(prefix="/insights", tags=["insights"])


def _subtract_months(d: date, months: int) -> date:
    year = d.year
    month = d.month - months
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def _category_spend(db: Session, user_id: int, start: date, end: date) -> dict[int, float]:
    """{category_id: total spend (positive number)} for amount<0 transactions
    in [start, end)."""
    rows = (
        db.query(Transaction.category_id, func.sum(Transaction.amount))
        .join(BankAccount, Transaction.account_id == BankAccount.account_id)
        .filter(
            BankAccount.user_id == user_id,
            Transaction.txn_date >= start,
            Transaction.txn_date < end,
            Transaction.category_id.isnot(None),
            Transaction.amount < 0,
        )
        .group_by(Transaction.category_id)
        .all()
    )
    return {category_id: abs(float(total)) for category_id, total in rows}


@router.get("", response_model=list[InsightOut])
def get_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    this_month_start = today.replace(day=1)
    last_month_start = _subtract_months(this_month_start, 1)

    # end is exclusive in _category_spend, so +1 day to include today's own transactions.
    this_month_spend = _category_spend(
        db, current_user.user_id, this_month_start, today + timedelta(days=1)
    )
    last_month_spend = _category_spend(db, current_user.user_id, last_month_start, this_month_start)

    category_ids = set(this_month_spend) | set(last_month_spend)
    category_names = {
        c.category_id: c.name
        for c in db.query(Category).filter(Category.category_id.in_(category_ids)).all()
    } if category_ids else {}

    insights: list[InsightOut] = []

    # 1. Month-over-month trend per category (biggest moves first, skip tiny
    # amounts so a $2 category doubling doesn't drown out real signal).
    trends = []
    for category_id in category_ids:
        current = this_month_spend.get(category_id, 0.0)
        previous = last_month_spend.get(category_id, 0.0)
        if previous < 5:
            continue
        change_pct = (current - previous) / previous * 100
        if abs(change_pct) < 10:
            continue
        trends.append((abs(change_pct), category_id, change_pct, current, previous))

    trends.sort(reverse=True)
    for _, category_id, change_pct, current, previous in trends[:3]:
        name = category_names.get(category_id, "this category")
        direction = "increased" if change_pct > 0 else "decreased"
        insights.append(
            InsightOut(
                severity="warning" if change_pct > 0 else "info",
                message=(
                    f"{name.capitalize()} spending {direction} {abs(change_pct):.0f}% "
                    f"compared to last month (${current:.2f} vs ${previous:.2f})."
                ),
                category_name=name,
            )
        )

    # 2. Budget status / overspending warnings for this month.
    budgets = (
        db.query(Budget, Category.name)
        .join(Category, Budget.category_id == Category.category_id)
        .filter(Budget.user_id == current_user.user_id, Budget.period_month == this_month_start)
        .all()
    )
    for budget, name in budgets:
        spent = this_month_spend.get(budget.category_id, 0.0)
        limit = float(budget.recommended_amount)
        if limit <= 0:
            continue
        ratio = spent / limit
        if ratio >= 1:
            insights.append(
                InsightOut(
                    severity="critical",
                    message=(
                        f"You've exceeded your {name} budget by "
                        f"${spent - limit:.2f} this month (${spent:.2f} of ${limit:.2f})."
                    ),
                    category_name=name,
                )
            )
        elif ratio >= 0.8:
            insights.append(
                InsightOut(
                    severity="warning",
                    message=(
                        f"You may exceed your {name} budget this month - "
                        f"already at {ratio * 100:.0f}% (${spent:.2f} of ${limit:.2f})."
                    ),
                    category_name=name,
                )
            )

    # 3. End-of-month spend prediction: straight-line extrapolation of total
    # spend-to-date across the days elapsed this month.
    days_elapsed = today.day
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    total_spent_so_far = sum(this_month_spend.values())
    if total_spent_so_far > 0 and days_elapsed > 0:
        projected = total_spent_so_far / days_elapsed * days_in_month
        total_budget = sum(float(b.recommended_amount) for b, _ in budgets)
        message = (
            f"At your current pace, you're on track to spend about ${projected:.2f} "
            f"this month (${total_spent_so_far:.2f} so far, day {days_elapsed} of {days_in_month})."
        )
        severity = "info"
        if total_budget > 0 and projected > total_budget:
            message += f" That would be ${projected - total_budget:.2f} over your combined budget."
            severity = "warning"
        insights.append(InsightOut(severity=severity, message=message, category_name=None))

    return insights
