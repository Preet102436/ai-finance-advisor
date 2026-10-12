"""/bank/sync - reads the sandbox's mocked transaction data and writes it
into the transactions table.

The /bank/link-account and /bank/link-account/callback routes for this
prefix are mounted separately in main.py, from link_account_api.py's router.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import BankAccount, Category, Receipt, Transaction, User
from sandbox_auth_test import mock_transactions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bank", tags=["bank"])


class BankAccountOut(BaseModel):
    account_id: int
    provider_name: str
    account_type: str | None = None
    currency: str | None = None
    linked_at: datetime


@router.get("/accounts", response_model=list[BankAccountOut])
def list_bank_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists the current user's actual linked bank accounts - this is
    what the Transactions page uses to decide whether to show "Link bank
    account" or "Unlink account".

    Deliberately excludes the internal 'manual-entry' bookkeeping account
    that /transactions and /transactions/import silently create to hang
    manually-typed or imported rows off of (transactions.account_id is
    NOT NULL, so something has to hold them). That account was never
    "linked" by the user, so adding a manual transaction - even after
    unlinking a real account - must never flip the button back to
    "Unlink account"."""
    accounts = (
        db.query(BankAccount)
        .filter(
            BankAccount.user_id == current_user.user_id,
            BankAccount.provider_name != "manual-entry",
        )
        .order_by(BankAccount.linked_at)
        .all()
    )
    return [
        BankAccountOut(
            account_id=a.account_id,
            provider_name=a.provider_name,
            account_type=a.account_type,
            currency=a.currency,
            linked_at=a.linked_at,
        )
        for a in accounts
    ]


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_bank_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unlink a bank account: detach any receipts pointing at its
    transactions (receipts.transaction_id has no ON DELETE rule, so it has
    to be cleared first - the receipt image/OCR text itself is kept, just
    no longer tied to a transaction), then delete the account. Deleting the
    account cascades to delete its transactions (and their anomalies), per
    the ON DELETE CASCADE on transactions.account_id. Once this account is
    gone, the user is free to link a new one."""
    account = (
        db.query(BankAccount)
        .filter(BankAccount.account_id == account_id, BankAccount.user_id == current_user.user_id)
        .first()
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    try:
        txn_ids = [
            row[0]
            for row in db.query(Transaction.transaction_id)
            .filter(Transaction.account_id == account.account_id)
            .all()
        ]
        if txn_ids:
            (
                db.query(Receipt)
                .filter(Receipt.transaction_id.in_(txn_ids))
                .update({Receipt.transaction_id: None}, synchronize_session=False)
            )

        db.delete(account)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to unlink account_id=%s", account_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not unlink this account right now. Please try again.",
        )

    return None


@router.post("/sync")
def sync_transactions(
    account_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Simulate a bank sync: fetch the sandbox's mocked transactions for the
    current user's linked account and insert any not already present as
    `transactions` rows with source='bank_sync'.

    Excludes the internal 'manual-entry' bookkeeping account (see
    /transactions' _get_or_create_manual_account) - that's not a real
    bank account to sync, and counting it here is what made this 400
    with "Multiple accounts found" for anyone who'd ever added a manual
    transaction or CSV import alongside one real linked account."""
    accounts = (
        db.query(BankAccount)
        .filter(
            BankAccount.user_id == current_user.user_id,
            BankAccount.provider_name != "manual-entry",
        )
        .all()
    )
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
        records = mock_transactions()
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
