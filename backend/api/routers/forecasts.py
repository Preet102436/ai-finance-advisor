"""/forecasts router.

TODO (not implemented yet):
- GET /forecasts    list current user's stored balance forecasts
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from forecast_prototype import forecast_balance
from models import BankAccount, Forecast, Transaction, User
from schemas import ForecastPoint, ForecastResponse

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.post("", response_model=ForecastResponse)
def generate_forecast(
    account_id: int | None = None,
    days_ahead: int = 14,
    use_prophet: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Forecast an account's balance from its real transaction history.

    Builds the daily net cash-flow series (sum of signed transaction amounts
    per day) for the given account, runs it through
    forecast_prototype.forecast_balance() (Prophet if available, otherwise a
    moving-average fallback), and stores the resulting points into
    `forecasts` (keyed by user_id, per the current schema - there is no
    per-account column there yet).
    """
    accounts = db.query(BankAccount).filter(BankAccount.user_id == current_user.user_id).all()
    if not accounts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No linked bank account found")

    if account_id is None:
        if len(accounts) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiple accounts found; pass ?account_id= to choose one",
            )
        account = accounts[0]
    else:
        account = next((a for a in accounts if a.account_id == account_id), None)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    rows = (
        db.query(Transaction.txn_date, func.sum(Transaction.amount).label("total"))
        .filter(Transaction.account_id == account.account_id)
        .group_by(Transaction.txn_date)
        .order_by(Transaction.txn_date)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No transaction history for this account to forecast from",
        )

    daily_totals = {txn_date: float(total) for txn_date, total in rows}

    forecast, method = forecast_balance(daily_totals, days_ahead, use_prophet=use_prophet)

    points = []
    for point in forecast:
        record = Forecast(
            user_id=current_user.user_id,
            forecast_date=point["date"],
            predicted_balance=point["predicted_balance"],
            lower_bound=point.get("lower_bound"),
            upper_bound=point.get("upper_bound"),
            model_version=method,
        )
        db.add(record)
        points.append(
            ForecastPoint(
                forecast_date=point["date"],
                predicted_balance=point["predicted_balance"],
                lower_bound=point.get("lower_bound"),
                upper_bound=point.get("upper_bound"),
            )
        )

    db.commit()

    return ForecastResponse(
        account_id=account.account_id,
        method=method,
        days_ahead=days_ahead,
        forecast=points,
    )
