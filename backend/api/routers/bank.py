"""/bank/sync - reads the sandbox's mocked transaction data and writes it
into the transactions table.

The /bank/link-account and /bank/link-account/callback routes for this
prefix are mounted separately in main.py, from link_account_api.py's router.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import BankAccount, Category, Transaction, User
from sandbox_auth_test import mock_transactions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bank", tags=["bank"])


@router.post("/sync")
def sync_transactions(
    account_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Simulate a bank sync: fetch the sandbox's mocked transactions for the
    current user's linked account and insert any not already present as
    `transactions` rows with source='bank_sync'."""
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

    try:
        records = mock_transactions(seed=account.account_id, anchor_date=account.linked_at.date())
    except Exception:
        logger.exception(
            "Bank sandbox call failed during /bank/sync for account_id=%s", account.account_id
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the bank sandbox to sync transactions. Please try again later.",
        )

    try:
        inserted_ids = []
        for record in records:
            already_synced = (
                db.query(Transaction)
                .filter(
                    Transaction.account_id == account.account_id,
                    Transaction.txn_date == record["date"],
                    Transaction.amount == record["amount"],
                    Transaction.merchant == record["merchant"],
                )
                .first()
            )
            if already_synced:
                continue

            category = None
            category_name = record.get("category")
            if category_name:
                category = db.query(Category).filter(Category.name == category_name).first()
                if category is None:
                    category = Category(name=category_name)
                    db.add(category)
                    db.flush()

            txn = Transaction(
                account_id=account.account_id,
                category_id=category.category_id if category else None,
                amount=record["amount"],
                description=record.get("description"),
                merchant=record.get("merchant"),
                txn_date=record["date"],
                source="bank_sync",
            )
            db.add(txn)
            db.flush()
            inserted_ids.append(txn.transaction_id)

        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "Failed to save synced transactions for account_id=%s", account.account_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sync retrieved data from the bank sandbox but saving it failed. Please try again.",
        )

    return {
        "account_id": account.account_id,
        "synced": len(inserted_ids),
        "transaction_ids": inserted_ids,
    }
