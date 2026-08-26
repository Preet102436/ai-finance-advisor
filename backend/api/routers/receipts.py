"""POST /receipts/upload - accept a receipt image, run it through
ocr_prototype.py's extraction/classification logic, and write matching
receipts + transactions rows.

TODO (not implemented yet):
- GET  /receipts        list current user's receipts
- GET  /receipts/{id}   fetch a receipt (incl. ocr_raw_text, linked transaction)
"""

import uuid
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import BankAccount, Category, Receipt, Transaction, User
from ocr_prototype import classify_category, extract_text, extract_total

router = APIRouter(prefix="/receipts", tags=["receipts"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads" / "receipts"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_account(db: Session, current_user: User, account_id: int | None) -> BankAccount:
    accounts = db.query(BankAccount).filter(BankAccount.user_id == current_user.user_id).all()
    if not accounts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No linked bank account found")

    if account_id is None:
        if len(accounts) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiple accounts found; pass ?account_id= to choose one",
            )
        return accounts[0]

    account = next((a for a in accounts if a.account_id == account_id), None)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


def _get_or_create_category(db: Session, name: str) -> Category:
    category = db.query(Category).filter(Category.name == name).first()
    if category is None:
        category = Category(name=name)
        db.add(category)
        db.flush()
    return category


def store_receipt_and_transaction(
    db: Session,
    current_user: User,
    raw_text: str,
    image_path: str,
    account_id: int | None = None,
):
    """Classify OCR'd receipt text and write the matching receipts +
    transactions rows. Shared by the upload endpoint and tests, so the
    classification/persistence logic is exercisable with sample OCR text
    (see test_receipts_upload.py) without needing a real OCR engine."""
    predicted_total = extract_total(raw_text)
    predicted_category = classify_category(raw_text)

    if predicted_total is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not find a total on this receipt; try a clearer image",
        )

    account = _resolve_account(db, current_user, account_id)

    category = None
    if predicted_category != "uncategorised":
        category = _get_or_create_category(db, predicted_category)

    # Receipts represent spend, so store as a negative amount - the same
    # sign convention bank_sync and manual transactions use.
    transaction = Transaction(
        account_id=account.account_id,
        category_id=category.category_id if category else None,
        amount=-predicted_total,
        description=f"Receipt upload ({predicted_category})",
        txn_date=date.today(),
        source="receipt_ocr",
    )
    db.add(transaction)
    db.flush()

    receipt = Receipt(
        user_id=current_user.user_id,
        transaction_id=transaction.transaction_id,
        image_path=image_path,
        ocr_raw_text=raw_text,
        processed_at=datetime.utcnow(),
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    return {
        "receipt_id": receipt.receipt_id,
        "transaction_id": transaction.transaction_id,
        "predicted_category": predicted_category,
        "predicted_total": predicted_total,
    }


@router.post("/upload")
def upload_receipt(
    file: UploadFile = File(...),
    account_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    suffix = Path(file.filename or "").suffix or ".jpg"
    stored_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    stored_path.write_bytes(file.file.read())

    try:
        raw_text = extract_text(str(stored_path))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OCR engine unavailable: {exc}",
        )

    return store_receipt_and_transaction(db, current_user, raw_text, str(stored_path), account_id)
