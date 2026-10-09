"""POST /receipts/upload - accept a receipt image, run OCR + extraction, and
return a PREVIEW (merchant/total/category/date) without saving a transaction
yet. POST /receipts/{id}/confirm - save the (possibly user-edited) fields as
a real transaction. Splitting it this way means a wrong OCR/AI guess never
silently becomes incorrect financial data - the user always confirms first.

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
from ocr_prototype import extract_receipt_fields, extract_text
from schemas import ReceiptConfirm, ReceiptConfirmOut, ReceiptOut, ReceiptPreviewOut

logger = logging.getLogger(__name__)

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


def _get_pending_receipt(db: Session, current_user: User, receipt_id: int) -> Receipt:
    receipt = (
        db.query(Receipt)
        .filter(Receipt.receipt_id == receipt_id, Receipt.user_id == current_user.user_id)
        .first()
    )
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    if receipt.transaction_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This receipt has already been confirmed",
        )
    return receipt


@router.get("/by-transaction/{transaction_id}", response_model=ReceiptOut)
def get_receipt_for_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Used by the Transactions page's details view to show receipt info
    (scanned text, when it was processed) for a receipt_ocr transaction."""
    receipt = (
        db.query(Receipt)
        .filter(Receipt.transaction_id == transaction_id, Receipt.user_id == current_user.user_id)
        .first()
    )
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No receipt for this transaction")
    return ReceiptOut(
        receipt_id=receipt.receipt_id,
        transaction_id=receipt.transaction_id,
        ocr_raw_text=receipt.ocr_raw_text,
        processed_at=receipt.processed_at,
    )


@router.post("/upload", response_model=ReceiptPreviewOut)
def upload_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Step 1: OCR the image and return a preview - nothing is saved as a
    transaction yet. Still writes a `receipts` row (transaction_id=None) so
    the raw OCR text/image are kept even if the user never confirms."""
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
    except Exception:
        logger.exception("OCR engine call failed for %s", stored_path)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The OCR engine is unavailable right now. Please try again later.",
        )

    fields = extract_receipt_fields(raw_text, use_llm=current_user.ai_enabled)

    try:
        receipt = Receipt(
            user_id=current_user.user_id,
            transaction_id=None,
            image_path=str(stored_path),
            ocr_raw_text=raw_text,
            processed_at=datetime.utcnow(),
        )
        db.add(receipt)
        db.commit()
        db.refresh(receipt)
    except Exception:
        db.rollback()
        logger.exception("Failed to save receipt for user_id=%s", current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The receipt was read but saving it failed. Please try again.",
        )

    return ReceiptPreviewOut(
        receipt_id=receipt.receipt_id,
        predicted_merchant=fields["merchant"],
        predicted_total=fields["total"],
        predicted_category=fields["category"],
        predicted_date=date.today(),
        raw_text=raw_text.strip(),
    )


@router.post("/{receipt_id}/confirm", response_model=ReceiptConfirmOut)
def confirm_receipt(
    receipt_id: int,
    payload: ReceiptConfirm,
    account_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Step 2: save the (possibly user-corrected) preview fields as a real
    transaction, linked back to the pending receipt from step 1."""
    receipt = _get_pending_receipt(db, current_user, receipt_id)
    account = _resolve_account(db, current_user, account_id)

    try:
        category = _get_or_create_category(db, payload.category_name)

        # Receipts represent spend, so store as a negative amount - the same
        # sign convention bank_sync and manual transactions use.
        transaction = Transaction(
            account_id=account.account_id,
            category_id=category.category_id,
            amount=-abs(payload.total),
            merchant=payload.merchant,
            description=f"Receipt upload ({payload.category_name})",
            txn_date=payload.txn_date,
            source="receipt_ocr",
        )
        db.add(transaction)
        db.flush()

        receipt.transaction_id = transaction.transaction_id
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "Failed to confirm receipt_id=%s for user_id=%s", receipt_id, current_user.user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save this transaction. Please try again.",
        )

    return ReceiptConfirmOut(
        receipt_id=receipt.receipt_id,
        transaction_id=transaction.transaction_id,
        category_name=payload.category_name,
        total=abs(payload.total),
    )
