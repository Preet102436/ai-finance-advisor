"""POST /receipts/upload - accept a receipt image, run it through
ocr_prototype.py's extraction/classification logic, and write matching
receipts + transactions rows.

TODO (not implemented yet):
- GET  /receipts        list current user's receipts
- GET  /receipts/{id}   fetch a receipt (incl. ocr_raw_text, linked transaction)
"""

import logging
import uuid
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import BankAccount, Category, Receipt, Transaction, User
from ocr_prototype import (
    InvalidImageError,
    OCRUnavailableError,
    classify_category,
    extract_merchant,
    extract_text,
    extract_total,
)
from routers.transactions import _get_or_create_manual_account

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/receipts", tags=["receipts"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads" / "receipts"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_account(db: Session, current_user: User, account_id: int | None) -> BankAccount:
    # Excludes the internal 'manual-entry' bookkeeping account - a receipt
    # scan should attach to a real linked bank account, and counting the
    # manual-entry one here caused the same spurious "Multiple accounts
    # found" error /bank/sync had.
    accounts = (
        db.query(BankAccount)
        .filter(
            BankAccount.user_id == current_user.user_id,
            BankAccount.provider_name != "manual-entry",
        )
        .all()
    )
    if account_id is None and not accounts:
        # No bank linked - file the receipt under the same 'manual-entry'
        # account manual transactions and CSV imports use, so receipt
        # scanning works with or without a linked bank.
        return _get_or_create_manual_account(db, current_user)

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

    try:
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
            merchant=extract_merchant(raw_text),
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
    except Exception:
        db.rollback()
        logger.exception(
            "Failed to save receipt/transaction for user_id=%s", current_user.user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The receipt was read but saving it failed. Please try again.",
        )

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
    try:
        stored_path.write_bytes(file.file.read())
    except Exception:
        logger.exception("Failed to save uploaded receipt file to %s", stored_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save the uploaded file. Please try again.",
        )

    try:
        raw_text = extract_text(str(stored_path))
    except InvalidImageError:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That file isn't a readable image. Upload a JPG or PNG photo of the receipt.",
        )
    except OCRUnavailableError as exc:
        logger.error("OCR engine unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The OCR engine isn't set up on the server (Tesseract not found). "
            "See TESSERACT_CMD in backend/api/.env.example.",
        )
    except Exception:
        logger.exception("OCR engine call failed for %s", stored_path)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The OCR engine is unavailable right now. Please try again later.",
        )

    return store_receipt_and_transaction(db, current_user, raw_text, str(stored_path), account_id)
