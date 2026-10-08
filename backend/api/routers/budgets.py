"""/budgets router.

GET  /budgets              list the current user's budgets for a period (default: this month)
POST /budgets               create/override a budget for a category, current month (user-set)
PUT  /budgets/{id}          edit a budget's amount
POST /budgets/recommend     AI-recommended budgets from trailing spend (see below)
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Date, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import BankAccount, Budget, Category, Transaction, User
from schemas import BudgetCreate, BudgetOut, BudgetUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _get_or_create_category(db: Session, name: str) -> Category:
    category = db.query(Category).filter(Category.name == name).first()
    if category is None:
        category = Category(name=name)
        db.add(category)
        db.flush()
    return category


def _get_owned_budget(db: Session, current_user: User, budget_id: int) -> Budget:
    budget = (
        db.query(Budget)
        .filter(Budget.budget_id == budget_id, Budget.user_id == current_user.user_id)
        .first()
    )
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return budget


@router.get("", response_model=list[BudgetOut])
def list_budgets(
    period_month: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Defaults to the current calendar month if period_month isn't given."""
    target_month = (period_month or date.today()).replace(day=1)

    rows = (
        db.query(Budget, Category.name)
        .join(Category, Budget.category_id == Category.category_id)
        .filter(Budget.user_id == current_user.user_id, Budget.period_month == target_month)
        .order_by(Category.name)
        .all()
    )
    return [
        BudgetOut(
            budget_id=b.budget_id,
            category_id=b.category_id,
            category_name=category_name,
            period_month=b.period_month,
            recommended_amount=float(b.recommended_amount),
            months_considered=1,
            generated_by=b.generated_by,
        )
        for b, category_name in rows
    ]


@router.post("", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """User-set budget for a category, for the current calendar month. If one
    already exists for that category/month it's overwritten (same upsert
    behaviour as /budgets/recommend), so this also works as "edit by name"."""
    period_month = date.today().replace(day=1)
    category = _get_or_create_category(db, payload.category_name)

    # Atomic upsert (not check-then-insert): two near-simultaneous requests
    # for the same category/month - e.g. React StrictMode double-invoking an
    # effect in dev - would otherwise both see "no existing row" and both
    # insert, violating the budgets(user_id, category_id, period_month)
    # unique constraint, or worse (before that constraint existed) silently
    # creating duplicate rows. ON CONFLICT makes the DB resolve the race.
    stmt = (
        pg_insert(Budget.__table__)
        .values(
            user_id=current_user.user_id,
            category_id=category.category_id,
            period_month=period_month,
            recommended_amount=payload.amount,
            generated_by="user",
        )
        .on_conflict_do_update(
            index_elements=["user_id", "category_id", "period_month"],
            set_={"recommended_amount": payload.amount, "generated_by": "user"},
        )
        .returning(Budget.budget_id)
    )
    budget_id = db.execute(stmt).scalar_one()
    db.commit()

    return BudgetOut(
        budget_id=budget_id,
        category_id=category.category_id,
        category_name=category.name,
        period_month=period_month,
        recommended_amount=payload.amount,
        months_considered=1,
        generated_by="user",
    )


@router.put("/{budget_id}", response_model=BudgetOut)
def update_budget(
    budget_id: int,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = _get_owned_budget(db, current_user, budget_id)
    budget.recommended_amount = payload.amount
    budget.generated_by = "user"
    db.commit()
    db.refresh(budget)

    category = db.get(Category, budget.category_id)
    return BudgetOut(
        budget_id=budget.budget_id,
        category_id=budget.category_id,
        category_name=category.name if category else "unknown",
        period_month=budget.period_month,
        recommended_amount=float(budget.recommended_amount),
        months_considered=1,
        generated_by=budget.generated_by,
    )


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

            # Atomic upsert, same reasoning as POST /budgets - a check-then-
            # insert here raced under React StrictMode's double-invoked dev
            # effect and created duplicate rows before the unique constraint
            # (and this fix) existed. The `where` clause additionally makes
            # sure a user's manual override (generated_by='user') is never
            # silently clobbered by a later AI recalculation, since the
            # Dashboard re-runs this on every page load.
            stmt = (
                pg_insert(Budget.__table__)
                .values(
                    user_id=current_user.user_id,
                    category_id=category_id,
                    period_month=period_month,
                    recommended_amount=recommended_amount,
                    generated_by="ai_engine",
                )
                .on_conflict_do_update(
                    index_elements=["user_id", "category_id", "period_month"],
                    set_={"recommended_amount": recommended_amount},
                    where=(Budget.__table__.c.generated_by != "user"),
                )
                .returning(Budget.budget_id, Budget.recommended_amount, Budget.generated_by)
            )
            row = db.execute(stmt).first()
            if row is None:
                # The WHERE clause blocked the update (existing row is a
                # user override) and the insert hit the same conflict, so
                # RETURNING yielded nothing - fetch the existing row as-is
                # instead of overwriting the user's own amount.
                existing = (
                    db.query(Budget)
                    .filter(
                        Budget.user_id == current_user.user_id,
                        Budget.category_id == category_id,
                        Budget.period_month == period_month,
                    )
                    .one()
                )
                budget_id, saved_amount, saved_generated_by = (
                    existing.budget_id,
                    existing.recommended_amount,
                    existing.generated_by,
                )
            else:
                budget_id, saved_amount, saved_generated_by = row

            results.append(
                BudgetOut(
                    budget_id=budget_id,
                    category_id=category_id,
                    category_name=category_names.get(category_id, "unknown"),
                    period_month=period_month,
                    recommended_amount=float(saved_amount),
                    months_considered=len(monthly),
                    generated_by=saved_generated_by,
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
