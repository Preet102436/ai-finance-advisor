"""/anomalies router.

Runs forecast_prototype.py's detect_anomalies() against the current user's
real transactions and persists flagged rows into the anomalies table.
"""

import logging
from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from forecast_prototype import detect_anomalies
from models import Anomaly, BankAccount, Category, Transaction, User
from schemas import AnomalyOut

logger = logging.getLogger(__name__)

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

    try:
        flagged = detect_anomalies(rows, z_threshold=z_threshold)
    except Exception:
        logger.exception(
            "Anomaly detection failed for user_id=%s (transaction_count=%d)",
            current_user.user_id, len(rows),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Could not run anomaly detection on the available transaction history "
                "(it may be too sparse). Try syncing more transactions first."
            ),
        )

    if not flagged:
        return []

    # Per-category "normal" amount (mean of every other transaction in the
    # same category, excluding the flagged one itself) so the stored reason
    # can say what's actually unusual about the amount, not just cite a bare
    # z-score - this also powers the alerts bell's human-readable text.
    amounts_by_category = defaultdict(list)
    for r in rows:
        amounts_by_category[r["category"]].append((r["transaction_id"], abs(r["amount"])))

    try:
        category_ids = {f["category"] for f in flagged}
        category_names = {
            c.category_id: c.name
            for c in db.query(Category).filter(Category.category_id.in_(category_ids)).all()
        }

        results = []
        for f in flagged:
            same_category = amounts_by_category.get(f["category"], [])
            normal_amounts = [amt for tid, amt in same_category if tid != f["transaction_id"]]
            normal_amount = (
                sum(normal_amounts) / len(normal_amounts) if normal_amounts else abs(f["amount"])
            )
            reason = (
                f"${abs(f['amount']):.2f} is a {f['z_score']}-sigma outlier vs the normal amount "
                f"for this category (around ${normal_amount:.2f})"
            )

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
    except Exception:
        db.rollback()
        logger.exception("Failed to save flagged anomalies for user_id=%s", current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Anomalies were detected but saving them failed. Please try again.",
        )

    return results


@router.get("", response_model=list[AnomalyOut])
def list_anomalies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Read-only - returns whatever POST /anomalies has already flagged and
    stored for the current user, without re-running detection. Powers the
    alerts bell and the dashboard's "flagged anomalies" card, neither of
    which should trigger a fresh (and possibly slow) detection pass on every
    page load.
    """
    rows = (
        db.query(Anomaly, Transaction, Category.name)
        .join(Transaction, Anomaly.transaction_id == Transaction.transaction_id)
        .join(BankAccount, Transaction.account_id == BankAccount.account_id)
        .outerjoin(Category, Transaction.category_id == Category.category_id)
        .filter(BankAccount.user_id == current_user.user_id)
        .order_by(Anomaly.detected_at.desc())
        .all()
    )

    return [
        AnomalyOut(
            anomaly_id=anomaly.anomaly_id,
            transaction_id=txn.transaction_id,
            category_id=txn.category_id,
            category_name=category_name or "unknown",
            txn_date=txn.txn_date,
            amount=float(txn.amount),
            merchant=txn.merchant,
            z_score=float(anomaly.anomaly_score),
            reason=anomaly.reason,
        )
        for anomaly, txn, category_name in rows
    ]
