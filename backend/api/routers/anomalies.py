"""/anomalies router.

Runs forecast_prototype.py's detect_anomalies() against the current user's
real transactions and persists flagged rows into the anomalies table.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from forecast_prototype import detect_anomalies
from models import Anomaly, BankAccount, Category, Transaction, User
from schemas import AnomalyOut

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.post("", response_model=list[AnomalyOut])
def detect_and_store_anomalies(
    lookback_days: int = 180,
    z_threshold: float = 3.0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Flag transactions whose amount is a z-score outlier within their own
    category, over the last `lookback_days` days, and upsert them into
    `anomalies`. Returns the current list of flagged transactions.
    """
    window_start = date.today() - timedelta(days=lookback_days)

    transactions = (
        db.query(Transaction)
        .join(BankAccount, Transaction.account_id == BankAccount.account_id)
        .filter(
            BankAccount.user_id == current_user.user_id,
            Transaction.txn_date >= window_start,
            Transaction.category_id.isnot(None),
        )
        .all()
    )

    rows = [
        {
            "transaction_id": t.transaction_id,
            "date": t.txn_date,
            "amount": float(t.amount),
            "category": t.category_id,
            "merchant": t.merchant,
        }
        for t in transactions
    ]

    flagged = detect_anomalies(rows, z_threshold=z_threshold)
    if not flagged:
        return []

    category_ids = {f["category"] for f in flagged}
    category_names = {
        c.category_id: c.name
        for c in db.query(Category).filter(Category.category_id.in_(category_ids)).all()
    }

    results = []
    for f in flagged:
        reason = f"amount is a {f['z_score']}-sigma outlier vs its category's history"

        anomaly = db.query(Anomaly).filter(Anomaly.transaction_id == f["transaction_id"]).first()
        if anomaly:
            anomaly.anomaly_score = f["z_score"]
            anomaly.reason = reason
        else:
            anomaly = Anomaly(
                transaction_id=f["transaction_id"],
                anomaly_score=f["z_score"],
                reason=reason,
            )
            db.add(anomaly)
        db.flush()

        results.append(
            AnomalyOut(
                anomaly_id=anomaly.anomaly_id,
                transaction_id=f["transaction_id"],
                category_id=f["category"],
                category_name=category_names.get(f["category"], "unknown"),
                txn_date=f["date"],
                amount=f["amount"],
                merchant=f["merchant"],
                z_score=f["z_score"],
                reason=reason,
            )
        )

    db.commit()
    return results
