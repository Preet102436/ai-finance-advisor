"""/budgets router.

GET /budgets - list the current user's budgets for the current month
(both AI-recommended and user-created). This is what the Dashboard
renders - POST /budgets/recommend only upserts AI-recommended budgets and
returns just those, so relying on its return value alone would silently
drop any budget the user created or edited themselves.
POST /budgets/recommend - auto-generate budgets from trailing spend.
POST /budgets - create a user-defined budget in a category, with an
amount the user picks themselves (generated_by='user').
PATCH /budgets/{budget_id} - increase/decrease an existing budget's amount.
DELETE /budgets/{budget_id} - remove a budget.
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Date, func
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import BankAccount, Budget, Category, Transaction, User
from schemas import BudgetCreate, BudgetOut, BudgetUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _subtract_months(d: date, months: int) -> date:
    year = d.year
    month = d.month - months
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def _resolve_category(db: Session, name: str) -> Category:
    """Looks up an existing category by (case-insensitive) name, creating
    one if it doesn't exist yet - same pattern used by /bank/sync and
    POST /transactions for on-the-fly category creation."""
    category = db.query(Category).filter(Category.name.ilike(name)).first()
    if category is None:
        category = Category(name=name)
        db.add(category)
        db.flush()
    return category


def _budget_out(db: Session, budget: Budget) -> BudgetOut:
    category = db.query(Category).filter(Category.category_id == budget.category_id).first()
    return BudgetOut(
        budget_id=budget.budget_id,
        category_id=budget.category_id,
        category_name=category.name if category else "unknown",
        period_month=budget.period_month,
        recommended_amount=float(budget.recommended_amount),
        months_considered=0,
        generated_by=budget.generated_by,
    )


@router.get("", response_model=list[BudgetOut])
def list_budgets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Every budget the user has for the current calendar month - AI-
    recommended ones (generated_by='ai_engine') and ones they created or
    edited themselves (generated_by='user') alike. A brand-new category
    budget shows up here immediately, even before it has any trailing
    spend history for the recommend engine to consider."""
    period_month = date.today().replace(day=1)
    rows = (
        db.query(Budget)
        .filter(Budget.user_id == current_user.user_id, Budget.period_month == period_month)
        .all()
    )
    return [_budget_out(db, b) for b in rows]


@router.post("", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create (or override, if one already exists for this category this
    month) a budget the user sets themselves for a category - including a
    brand-new category that doesn't have any transactions yet."""
    period_month = date.today().replace(day=1)
    category = _resolve_category(db, payload.category_name.strip())

    try:
        budget = (
            db.query(Budget)
            .filter(
                Budget.user_id == current_user.user_id,
                Budget.category_id == category.category_id,
                Budget.period_month == period_month,
            )
            .first()
        )
        if budget:
            budget.recommended_amount = payload.amount
            budget.generated_by = "user"
        else:
            budget = Budget(
                user_id=current_user.user_id,
                category_id=category.category_id,
                period_month=period_month,
                recommended_amount=payload.amount,
                generated_by="user",
            )
            db.add(budget)
        db.commit()
        db.refresh(budget)
    except Exception:
        db.rollback()
        logger.exception("Failed to create budget for user_id=%s", current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create this budget right now. Please try again.",
        )

    return _budget_out(db, budget)


@router.patch("/{budget_id}", response_model=BudgetOut)
def update_budget(
    budget_id: int,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Increase or decrease a budget's amount - set it directly to the new
    total the user wants for that category."""
    budget = (
        db.query(Budget)
        .filter(Budget.budget_id == budget_id, Budget.user_id == current_user.user_id)
        .first()
    )
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    budget.recommended_amount = payload.amount
    db.commit()
    db.refresh(budget)
    return _budget_out(db, budget)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = (
        db.query(Budget)
        .filter(Budget.budget_id == budget_id, Budget.user_id == current_user.user_id)
        .first()
    )
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    db.delete(budget)
    db.commit()
    return None


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
    (default 5%), and creates a budget for the current calendar month
    (generated_by='ai_engine') for any category that doesn't already have
    one this month.

    Deliberately never touches a budget that already exists for a
    category this month - whether the user created it, edited one of
    these AI amounts with PATCH, or deleted one outright. Once a row
    exists (or has been removed), the user owns it from the Dashboard's
    budget cards; re-running this (e.g. just by revisiting the Dashboard,
    which calls this automatically the first time) must never silently
    overwrite an edit or resurrect a delete.
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

    try:
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
                )
                .first()
            )
            if budget is not None:
                # A budget already exists for this category this month -
                # whether it's a prior AI recommendation (possibly since
                # edited by hand) or one the user created from scratch.
                # Report its current, real state and move on without
                # touching it.
                results.append(
                    BudgetOut(
                        budget_id=budget.budget_id,
                        category_id=category_id,
                        category_name=category_names.get(category_id, "unknown"),
                        period_month=period_month,
                        recommended_amount=float(budget.recommended_amount),
                        months_considered=len(monthly),
                        generated_by=budget.generated_by,
                    )
                )
                continue

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
    except Exception:
        db.rollback()
        logger.exception(
            "Budget recommendation failed for user_id=%s", current_user.user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not compute budget recommendations right now. Please try again.",
        )

    return results
