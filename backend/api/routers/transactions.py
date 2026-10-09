"""GET /transactions - list the current user's transactions, with optional
category/date/search filters. GET /transactions/categories - the distinct
categories used in the current user's transactions, for filter dropdowns.
GET /transactions/{id} - a single transaction's details.
POST /transactions - create a manual expense/income entry (source='manual').
PUT /transactions/{id}/category - recategorise a transaction.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import BankAccount, Category, Transaction, User
from schemas import CategoryOut, TransactionCategoryUpdate, TransactionCreate, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _get_or_create_category(db: Session, name: str) -> Category:
    category = db.query(Category).filter(Category.name == name).first()
    if category is None:
        category = Category(name=name)
        db.add(category)
        db.flush()
    return category


def _resolve_account(db: Session, current_user: User, account_id: int | None) -> BankAccount:
    accounts = db.query(BankAccount).filter(BankAccount.user_id == current_user.user_id).all()
    if not accounts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No linked bank account found")
    if account_id is None:
        if len(accounts) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiple accounts found; pass account_id to choose one",
            )
        return accounts[0]
    account = next((a for a in accounts if a.account_id == account_id), None)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


def _get_owned_transaction(db: Session, current_user: User, transaction_id: int) -> Transaction:
    txn = (
        db.query(Transaction)
        .join(BankAccount, Transaction.account_id == BankAccount.account_id)
        .filter(
            Transaction.transaction_id == transaction_id,
            BankAccount.user_id == current_user.user_id,
        )
        .first()
    )
    if txn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return txn


def _to_out(t: Transaction, category_name: str | None) -> TransactionOut:
    return TransactionOut(
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


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    category_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
    source: str | None = None,
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
    if source:
        query = query.filter(Transaction.source == source)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Transaction.merchant.ilike(like), Transaction.description.ilike(like))
        )

    rows = query.order_by(Transaction.txn_date.desc(), Transaction.transaction_id.desc()).all()
    return [_to_out(t, category_name) for t, category_name in rows]


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


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    txn = _get_owned_transaction(db, current_user, transaction_id)
    category_name = None
    if txn.category_id:
        category = db.get(Category, txn.category_id)
        category_name = category.name if category else None
    return _to_out(txn, category_name)


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manual expense/income entry - amount follows the same sign convention
    as everywhere else (negative = spend, positive = income)."""
    account = _resolve_account(db, current_user, payload.account_id)

    category = None
    if payload.category_name:
        category = _get_or_create_category(db, payload.category_name)

    txn = Transaction(
        account_id=account.account_id,
        category_id=category.category_id if category else None,
        amount=payload.amount,
        description=payload.description,
        merchant=payload.merchant,
        txn_date=payload.txn_date,
        source="manual",
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return _to_out(txn, category.name if category else None)


@router.put("/{transaction_id}/category", response_model=TransactionOut)
def update_transaction_category(
    transaction_id: int,
    payload: TransactionCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    txn = _get_owned_transaction(db, current_user, transaction_id)
    category = _get_or_create_category(db, payload.category_name)
    txn.category_id = category.category_id
    db.commit()
    db.refresh(txn)
    return _to_out(txn, category.name)
