"""GET /transactions - list the current user's transactions, with optional
category/date filters. GET /transactions/categories - the distinct
categories used in the current user's transactions, for filter dropdowns.

TODO (not implemented yet):
- GET    /transactions/{id}   fetch a single transaction
- POST   /transactions        create a manual transaction (source='manual')
- PUT    /transactions/{id}   edit a transaction (e.g. recategorise)
- DELETE /transactions/{id}   remove a transaction
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import BankAccount, Category, Transaction, User
from schemas import CategoryOut, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    category_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Transaction, Category.name)
        .join(BankAccount, Transaction.account_id == BankAccount.account_id)
        .outerjoin(Category, Transaction.category_id == Category.category_id)
        .filter(BankAccount.user_id == current_user.user_id)
    )
    if category_id is not None:
        query = query.filter(Transaction.category_id == category_id)
    if start_date is not None:
        query = query.filter(Transaction.txn_date >= start_date)
    if end_date is not None:
        query = query.filter(Transaction.txn_date <= end_date)

    rows = query.order_by(Transaction.txn_date.desc(), Transaction.transaction_id.desc()).all()

    return [
        TransactionOut(
            transaction_id=t.transaction_id,
            account_id=t.account_id,
            category_id=t.category_id,
            category_name=category_name,
            amount=float(t.amount),
            description=t.description,
            merchant=t.merchant,
            txn_date=t.txn_date,
            source=t.source,
        )
        for t, category_name in rows
    ]


@router.get("/categories", response_model=list[CategoryOut])
def list_transaction_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(Category)
        .join(Transaction, Transaction.category_id == Category.category_id)
        .join(BankAccount, Transaction.account_id == BankAccount.account_id)
        .filter(BankAccount.user_id == current_user.user_id)
        .distinct()
        .order_by(Category.name)
        .all()
    )
    return [CategoryOut(category_id=c.category_id, name=c.name) for c in rows]
