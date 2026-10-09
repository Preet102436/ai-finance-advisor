"""
Integration test for POST /transactions/import-csv - bulk transaction
import from a CSV file (source='csv_import').

Covers: the exact sample CSV served to users at
frontend/public/sample-transactions.csv imports cleanly, a bad row (invalid
date/amount) is skipped with a reason instead of failing the whole upload,
and a CSV missing a required column is rejected up front.

Run with:
    pytest backend/api/test_csv_import.py
"""

import io
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import BankAccount, Transaction, User

client = TestClient(app)

SAMPLE_CSV_PATH = Path(__file__).resolve().parent.parent.parent / "frontend" / "public" / "sample-transactions.csv"


def _register_login_and_link():
    email = f"csv_import_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"
    client.post("/auth/register", json={"full_name": "CSV Import Test", "email": email, "password": password})
    login = client.post("/auth/login", json={"email": email, "password": password})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    link = client.post("/bank/link-account", headers=headers).json()
    client.post(
        "/bank/link-account/callback",
        headers=headers,
        json={"auth_code": link["auth_code"], "state": link["state"]},
    )
    return email, headers


def _delete_user(email):
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == email).delete()
        db.commit()
    finally:
        db.close()


def test_sample_csv_imports_cleanly():
    """The exact file users download from the UI must import without errors."""
    email, headers = _register_login_and_link()
    try:
        csv_bytes = SAMPLE_CSV_PATH.read_bytes()
        resp = client.post(
            "/transactions/import-csv",
            headers=headers,
            files={"file": ("sample-transactions.csv", io.BytesIO(csv_bytes), "text/csv")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["skipped"] == []
        assert data["imported"] == data["total_rows"] == 8

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            txns = (
                db.query(Transaction)
                .join(BankAccount, Transaction.account_id == BankAccount.account_id)
                .filter(BankAccount.user_id == user.user_id)
                .all()
            )
            assert len(txns) == 8
            assert all(t.source == "csv_import" for t in txns)
        finally:
            db.close()
    finally:
        _delete_user(email)


def test_bad_rows_are_skipped_not_fatal():
    email, headers = _register_login_and_link()
    try:
        csv_text = (
            "date,amount,merchant,category\n"
            "2026-10-01,-20.00,Good Cafe,dining\n"  # valid
            "not-a-date,-10.00,Bad Date,dining\n"  # invalid date
            "2026-10-03,not-a-number,Bad Amount,dining\n"  # invalid amount
            "2026-10-04,0,Zero Amount,dining\n"  # zero amount
            ",,,\n"  # missing required fields
            "2026-10-06,55.00,Second Good Row,income\n"  # valid
        )
        resp = client.post(
            "/transactions/import-csv",
            headers=headers,
            files={"file": ("bad.csv", io.BytesIO(csv_text.encode()), "text/csv")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_rows"] == 6
        assert data["imported"] == 2
        assert len(data["skipped"]) == 4
        # Row numbers account for the header row being row 1.
        assert {s["row"] for s in data["skipped"]} == {3, 4, 5, 6}
    finally:
        _delete_user(email)


def test_missing_required_column_is_rejected():
    email, headers = _register_login_and_link()
    try:
        csv_text = "merchant,category\nCorner Cafe,dining\n"
        resp = client.post(
            "/transactions/import-csv",
            headers=headers,
            files={"file": ("missing_columns.csv", io.BytesIO(csv_text.encode()), "text/csv")},
        )
        assert resp.status_code == 400
        assert "amount" in resp.json()["detail"]
    finally:
        _delete_user(email)


def test_non_csv_file_is_rejected():
    email, headers = _register_login_and_link()
    try:
        resp = client.post(
            "/transactions/import-csv",
            headers=headers,
            files={"file": ("not-a-csv.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert resp.status_code == 400
    finally:
        _delete_user(email)


if __name__ == "__main__":
    test_sample_csv_imports_cleanly()
    test_bad_rows_are_skipped_not_fatal()
    test_missing_required_column_is_rejected()
    test_non_csv_file_is_rejected()
    print("csv import tests passed.")
