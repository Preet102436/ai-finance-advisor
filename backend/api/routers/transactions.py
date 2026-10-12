"""GET /transactions - list the current user's transactions, with optional
category/date filters. GET /transactions/categories - the distinct
categories used in the current user's transactions, for filter dropdowns.
POST /transactions - add a manual transaction (source='manual'), for
expenses/income the user types in by hand rather than syncing or scanning.
POST /transactions/import - bulk-import transactions from a .csv or .xlsx
file (source='import'), with best-effort auto-categorization by merchant/
description keywords.

GET/PUT/DELETE /transactions/{id} - fetch, edit (e.g. recategorise, fix an
amount) or remove a single transaction, regardless of how it got there
(bank sync, manual entry, import, or a scanned receipt) - scoped to the
current user's own accounts.
"""

import csv
import io
import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import BankAccount, Category, Receipt, Transaction, User
from schemas import CategoryOut, TransactionCreate, TransactionOut, TransactionUpdate

try:
    import openpyxl
except ImportError:
    openpyxl = None

router = APIRouter(prefix="/transactions", tags=["transactions"])

logger = logging.getLogger(__name__)


def _get_or_create_manual_account(db: Session, user: User) -> BankAccount:
    """Manual entries and imported rows still need a bank_accounts row to
    attach to (transactions.account_id is NOT NULL). Reuses one dedicated
    'manual-entry' account per user instead of creating a new one per
    transaction - mirrors the dedup approach used for sandbox-bank
    accounts in main.py's _persist_linked_account."""
    account = (
        db.query(BankAccount)
        .filter(
            BankAccount.user_id == user.user_id,
            BankAccount.provider_name == "manual-entry",
        )
        .first()
    )
    if account is not None:
        return account

    account = BankAccount(
        user_id=user.user_id,
        provider_name="manual-entry",
        external_ref=f"manual-{user.user_id}",
        account_type="manual",
        currency="AUD",
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def _resolve_category(db: Session, name: str | None) -> Category | None:
    """Looks up an existing category by (case-insensitive) name, creating
    one if it doesn't exist yet - the same pattern /bank/sync and the manual
    POST /transactions endpoint already use."""
    if not name:
        return None
    category = db.query(Category).filter(Category.name.ilike(name)).first()
    if category is None:
        category = Category(name=name)
        db.add(category)
        db.flush()
    return category


def _load_owned_transaction(db: Session, transaction_id: int, user: User) -> Transaction:
    """Fetches a transaction by id, scoped to one of the current user's own
    bank accounts - same ownership check GET /transactions already applies
    via its BankAccount join, so a user can never view, edit or delete
    someone else's transaction just by guessing an id."""
    txn = (
        db.query(Transaction)
        .join(BankAccount, Transaction.account_id == BankAccount.account_id)
        .filter(Transaction.transaction_id == transaction_id, BankAccount.user_id == user.user_id)
        .first()
    )
    if txn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return txn


def _txn_out(db: Session, txn: Transaction) -> TransactionOut:
    category_name = None
    if txn.category_id is not None:
        category = db.query(Category).filter(Category.category_id == txn.category_id).first()
        category_name = category.name if category else None
    return TransactionOut(
        transaction_id=txn.transaction_id,
        account_id=txn.account_id,
        category_id=txn.category_id,
        category_name=category_name,
        amount=float(txn.amount),
        description=txn.description,
        merchant=txn.merchant,
        txn_date=txn.txn_date,
        source=txn.source,
    )


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a transaction the user types in by hand (source='manual'),
    e.g. cash spending or income that never shows up via bank sync or a
    scanned receipt. category_name is resolved to an existing Category
    or created on the fly, the same way /bank/sync handles categories."""
    account = _get_or_create_manual_account(db, current_user)
    category = _resolve_category(db, payload.category_name)

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

    return TransactionOut(
        transaction_id=txn.transaction_id,
        account_id=txn.account_id,
        category_id=txn.category_id,
        category_name=category.name if category else None,
        amount=float(txn.amount),
        description=txn.description,
        merchant=txn.merchant,
        txn_date=txn.txn_date,
        source=txn.source,
    )


# --- CSV/Excel import -------------------------------------------------------

# Rule-based auto-categorization: fast, free, and works offline (unlike an
# LLM call per row) - good enough for common merchant names in an imported
# bank statement, and never blocks the import if a row doesn't match.
_CATEGORY_KEYWORDS = {
    "groceries": ["woolworths", "coles", "aldi", "iga", "grocery", "supermarket"],
    "dining": ["cafe", "coffee", "restaurant", "mcdonald", "kfc", "noodle", "pizza", "uber eats", "menulog", "doordash"],
    "subscriptions": ["netflix", "spotify", "disney", "subscription", "prime video", "stan", "youtube premium"],
    "utilities": ["electricity", "energy", "water corp", "gas bill", "utility", "telstra", "optus", "vodafone"],
    "transport": ["uber", "fuel", "petrol", "bp ", "shell", "myki", "opal", "transport", "parking"],
    "income": ["salary", "payroll", "wages", "employer", "payment received"],
    "health": ["pharmacy", "chemist", "medical", "doctor", "dental"],
    "entertainment": ["cinema", "movie", "event", "ticket"],
    "rent": ["rent", "landlord", "real estate"],
}

_COLUMN_ALIASES = {
    "date": {"date", "txn_date", "transaction date", "posted date", "transaction_date"},
    "description": {"description", "memo", "details", "narrative"},
    "merchant": {"merchant", "payee", "name"},
    "amount": {"amount", "value", "debit", "credit"},
    "category": {"category", "category_name"},
}

_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d/%m/%y", "%m/%d/%y"]


def _guess_category(merchant: str | None, description: str | None) -> str | None:
    text = f"{merchant or ''} {description or ''}".lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return None


def _map_headers(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, h in enumerate(headers):
        h_norm = (h or "").strip().lower()
        for field, aliases in _COLUMN_ALIASES.items():
            if h_norm in aliases and field not in mapping:
                mapping[field] = idx
    return mapping


def _parse_amount(raw: str) -> float:
    raw = raw.strip().replace(",", "").replace("$", "")
    if raw.startswith("(") and raw.endswith(")"):
        raw = "-" + raw[1:-1]
    return float(raw)


def _parse_date_flexible(raw: str) -> date:
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date format: {raw!r}")


def _rows_from_csv(text: str) -> list[dict]:
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    mapping = _map_headers(rows[0])
    if "date" not in mapping or "amount" not in mapping:
        raise ValueError("Could not find 'date' and 'amount' columns in the file header.")

    def _cell(row, field):
        idx = mapping.get(field)
        if idx is None or idx >= len(row):
            return None
        value = row[idx].strip()
        return value or None

    return [
        {
            "date_raw": _cell(row, "date"),
            "description": _cell(row, "description"),
            "merchant": _cell(row, "merchant"),
            "amount_raw": _cell(row, "amount"),
            "category": _cell(row, "category"),
        }
        for row in rows[1:]
        if any((c or "").strip() for c in row)
    ]


def _rows_from_xlsx(file_bytes: bytes) -> list[dict]:
    if openpyxl is None:
        raise RuntimeError("openpyxl is not installed on the server. Run: pip install openpyxl")
    workbook = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h) if h is not None else "" for h in rows[0]]
    mapping = _map_headers(headers)
    if "date" not in mapping or "amount" not in mapping:
        raise ValueError("Could not find 'date' and 'amount' columns in the file header.")

    def _cell(row, field):
        idx = mapping.get(field)
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    out = []
    for row in rows[1:]:
        if row is None or all(c is None for c in row):
            continue
        date_val = _cell(row, "date")
        date_raw = date_val.isoformat()[:10] if hasattr(date_val, "isoformat") else (str(date_val) if date_val is not None else None)
        amount_val = _cell(row, "amount")
        description = _cell(row, "description")
        merchant = _cell(row, "merchant")
        category = _cell(row, "category")
        out.append({
            "date_raw": date_raw,
            "description": str(description).strip() if description is not None else None,
            "merchant": str(merchant).strip() if merchant is not None else None,
            "amount_raw": str(amount_val) if amount_val is not None else None,
            "category": str(category).strip() if category is not None else None,
        })
    return out


@router.post("/import")
async def import_transactions(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk-import transactions from a bank-statement-style .csv or .xlsx
    file. Looks for date/amount columns (plus optional description/merchant/
    category) under a handful of common header names, auto-categorizes rows
    with no explicit category via merchant/description keyword matching, and
    inserts everything as source='import'. Rows that fail to parse are
    skipped and counted, never silently dropped without being reported."""
    filename = (file.filename or "").lower()
    content = await file.read()

    try:
        if filename.endswith(".csv"):
            raw_rows = _rows_from_csv(content.decode("utf-8-sig", errors="replace"))
        elif filename.endswith(".xlsx"):
            raw_rows = _rows_from_xlsx(content)
        else:
            raise HTTPException(status_code=400, detail="Only .csv and .xlsx files are supported.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    account = _get_or_create_manual_account(db, current_user)

    imported = 0
    skipped = 0
    auto_categorized = 0
    errors: list[str] = []

    for i, row in enumerate(raw_rows, start=2):  # row 1 is the header
        try:
            if not row.get("date_raw") or not row.get("amount_raw"):
                raise ValueError("missing date or amount")
            txn_date = _parse_date_flexible(row["date_raw"])
            amount = _parse_amount(row["amount_raw"])
        except (ValueError, TypeError) as exc:
            skipped += 1
            if len(errors) < 10:
                errors.append(f"row {i}: {exc}")
            continue

        category_name = row.get("category")
        if not category_name:
            category_name = _guess_category(row.get("merchant"), row.get("description"))
            if category_name:
                auto_categorized += 1
        category = _resolve_category(db, category_name)

        db.add(Transaction(
            account_id=account.account_id,
            category_id=category.category_id if category else None,
            amount=amount,
            description=row.get("description"),
            merchant=row.get("merchant"),
            txn_date=txn_date,
            source="import",
        ))
        imported += 1

    db.commit()

    return {
        "imported": imported,
        "skipped": skipped,
        "auto_categorized": auto_categorized,
        "errors": errors,
    }


@router.get("")
def list_transactions(
    category_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """limit/offset are optional - omit both to get every matching
    transaction back as a plain list (the Dashboard's month-to-date
    spending breakdown relies on that full-list behaviour and never
    paginates). Pass limit to get a paginated page instead: the response
    shape changes to {items, total, limit, offset} so the Transactions
    page can render "page X of Y" controls without ever loading someone's
    entire multi-year transaction history into the browser at once."""
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

    total = query.count()

    ordered = query.order_by(Transaction.txn_date.desc(), Transaction.transaction_id.desc())
    if limit is not None:
        ordered = ordered.offset(offset).limit(limit)
    rows = ordered.all()

    items = [
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

    if limit is None:
        return items

    return {"items": items, "total": total, "limit": limit, "offset": offset}


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
    txn = _load_owned_transaction(db, transaction_id, current_user)
    return _txn_out(db, txn)


@router.put("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit a transaction in place - fix an amount, re-date it, rename the
    merchant/description, or recategorise it. Only fields actually sent
    are changed; category_name is resolved to an existing category or
    created on the fly, the same as manual entry and CSV import."""
    txn = _load_owned_transaction(db, transaction_id, current_user)

    if payload.txn_date is not None:
        txn.txn_date = payload.txn_date
    if payload.amount is not None:
        txn.amount = payload.amount
    if payload.merchant is not None:
        txn.merchant = payload.merchant
    if payload.description is not None:
        txn.description = payload.description
    if payload.category_name is not None:
        category = _resolve_category(db, payload.category_name)
        txn.category_id = category.category_id if category else None

    db.commit()
    db.refresh(txn)
    return _txn_out(db, txn)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a transaction. Any receipt pointing at it is detached first
    (receipts.transaction_id has no ON DELETE rule, so it has to be
    cleared before the transaction can go) - the receipt image/OCR text
    itself is kept, just no longer tied to a transaction. Any anomaly
    flagged against it cascades automatically."""
    txn = _load_owned_transaction(db, transaction_id, current_user)

    try:
        (
            db.query(Receipt)
            .filter(Receipt.transaction_id == transaction_id)
            .update({Receipt.transaction_id: None}, synchronize_session=False)
        )
        db.delete(txn)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to delete transaction_id=%s", transaction_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete this transaction right now. Please try again.",
        )

    return None

