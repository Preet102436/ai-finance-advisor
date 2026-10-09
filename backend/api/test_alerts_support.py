"""
Integration test for the read-only support endpoints added for the alerts
bell and transaction details view: GET /anomalies (no recompute) and
GET /receipts/by-transaction/{id}.

Run with:
    pytest backend/api/test_alerts_support.py
"""

import io
import uuid
from datetime import date, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import Anomaly, BankAccount, Category, Transaction, User

client = TestClient(app)


def test_get_anomalies_is_read_only_and_matches_post():
    email = f"alerts_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"

    try:
        client.post("/auth/register", json={"full_name": "Alerts Test", "email": email, "password": password})
        login = client.post("/auth/login", json={"email": email, "password": password})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        link = client.post("/bank/link-account", headers=headers).json()
        cb = client.post(
            "/bank/link-account/callback",
            headers=headers,
            json={"auth_code": link["auth_code"], "state": link["state"]},
        )
        account_id = cb.json()["account_id"]

        # Before any detection has run, GET should just be empty (not fail).
        empty_resp = client.get("/anomalies", headers=headers)
        assert empty_resp.status_code == 200
        assert empty_resp.json() == []

        db = SessionLocal()
        try:
            category = db.query(Category).filter(Category.name == "groceries").first()
            today = date.today()
            for i in range(10):
                db.add(Transaction(
                    account_id=account_id, category_id=category.category_id, amount=-50.0,
                    merchant="Woolworths", txn_date=today - timedelta(days=i + 1), source="bank_sync",
                ))
            db.add(Transaction(
                account_id=account_id, category_id=category.category_id, amount=-900.0,
                merchant="Woolworths", txn_date=today, source="bank_sync",
            ))
            db.commit()
        finally:
            db.close()

        post_resp = client.post("/anomalies", headers=headers)
        assert post_resp.status_code == 200
        assert len(post_resp.json()) == 1

        get_resp = client.get("/anomalies", headers=headers)
        assert get_resp.status_code == 200
        assert len(get_resp.json()) == 1
        assert get_resp.json()[0]["amount"] == post_resp.json()[0]["amount"]
        assert "normal amount" in get_resp.json()[0]["reason"].lower()
    finally:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            if user:
                txn_ids = [
                    t.transaction_id
                    for t in db.query(Transaction.transaction_id)
                    .join(BankAccount, Transaction.account_id == BankAccount.account_id)
                    .filter(BankAccount.user_id == user.user_id)
                ]
                db.query(Anomaly).filter(Anomaly.transaction_id.in_(txn_ids)).delete(synchronize_session=False)
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


def test_receipt_lookup_by_transaction():
    email = f"receipt_lookup_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"
    sample_text = "WOOLWORTHS SUPERMARKET\nMilk 3.50\nTOTAL   20.00"

    try:
        client.post("/auth/register", json={"full_name": "Receipt Lookup", "email": email, "password": password})
        login = client.post("/auth/login", json={"email": email, "password": password})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        link = client.post("/bank/link-account", headers=headers).json()
        client.post(
            "/bank/link-account/callback",
            headers=headers,
            json={"auth_code": link["auth_code"], "state": link["state"]},
        )

        fake_image = io.BytesIO(b"not a real image")
        with patch("routers.receipts.extract_text", return_value=sample_text):
            upload_resp = client.post(
                "/receipts/upload", headers=headers, files={"file": ("r.jpg", fake_image, "image/jpeg")}
            )
        preview = upload_resp.json()

        confirm_resp = client.post(
            f"/receipts/{preview['receipt_id']}/confirm",
            headers=headers,
            json={
                "total": preview["predicted_total"],
                "category_name": preview["predicted_category"],
                "txn_date": date.today().isoformat(),
            },
        )
        transaction_id = confirm_resp.json()["transaction_id"]

        lookup_resp = client.get(f"/receipts/by-transaction/{transaction_id}", headers=headers)
        assert lookup_resp.status_code == 200
        assert lookup_resp.json()["ocr_raw_text"] == sample_text

        # A transaction with no receipt (e.g. manual entry) -> 404, not a crash.
        manual_resp = client.post(
            "/transactions",
            headers=headers,
            json={"amount": -10.0, "txn_date": date.today().isoformat(), "category_name": "dining"},
        )
        manual_txn_id = manual_resp.json()["transaction_id"]
        no_receipt_resp = client.get(f"/receipts/by-transaction/{manual_txn_id}", headers=headers)
        assert no_receipt_resp.status_code == 404
    finally:
        db = SessionLocal()
        try:
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    test_get_anomalies_is_read_only_and_matches_post()
    test_receipt_lookup_by_transaction()
    print("alerts support tests passed.")
