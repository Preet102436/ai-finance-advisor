"""
Integration test for GET/PUT /users/me/profile and GET/DELETE
/bank/accounts - the Settings page's Profile and Connected Accounts tabs.

The disconnect test specifically covers a real bug found while building
this: disconnecting an account with a receipt-scanned transaction used to
hit a foreign-key violation, because receipts.transaction_id had no
ON DELETE CASCADE (fixed in db/schema.sql + models.py).

Run with:
    pytest backend/api/test_profile_and_accounts.py
"""

import io
import uuid
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import BankAccount, User

client = TestClient(app)


def test_profile_update_and_read():
    email = f"profile_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"

    try:
        client.post("/auth/register", json={"full_name": "Profile Test", "email": email, "password": password})
        login = client.post("/auth/login", json={"email": email, "password": password})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        empty_resp = client.get("/users/me/profile", headers=headers)
        assert empty_resp.status_code == 200
        assert empty_resp.json()["phone"] is None

        update_resp = client.put(
            "/users/me/profile",
            headers=headers,
            json={"phone": "0400 000 000", "address": "1 Example St", "monthly_income": 5000.0},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["phone"] == "0400 000 000"
        assert update_resp.json()["monthly_income"] == 5000.0

        get_resp = client.get("/users/me/profile", headers=headers)
        assert get_resp.json()["address"] == "1 Example St"
    finally:
        db = SessionLocal()
        try:
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


def test_disconnect_account_with_receipt_transaction_does_not_fk_violate():
    email = f"disconnect_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"
    sample_text = "WOOLWORTHS SUPERMARKET\nMilk 3.50\nTOTAL   20.00"

    try:
        client.post("/auth/register", json={"full_name": "Disconnect Test", "email": email, "password": password})
        login = client.post("/auth/login", json={"email": email, "password": password})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        link = client.post("/bank/link-account", headers=headers).json()
        cb = client.post(
            "/bank/link-account/callback",
            headers=headers,
            json={"auth_code": link["auth_code"], "state": link["state"]},
        )
        account_id = cb.json()["account_id"]

        list_resp = client.get("/bank/accounts", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1
        assert list_resp.json()[0]["account_id"] == account_id

        client.post("/bank/sync", headers=headers)

        fake_image = io.BytesIO(b"not a real image")
        with patch("routers.receipts.extract_text", return_value=sample_text):
            upload_resp = client.post(
                "/receipts/upload", headers=headers, files={"file": ("r.jpg", fake_image, "image/jpeg")}
            )
        preview = upload_resp.json()
        client.post(
            f"/receipts/{preview['receipt_id']}/confirm",
            headers=headers,
            json={
                "total": preview["predicted_total"],
                "category_name": preview["predicted_category"],
                "txn_date": date.today().isoformat(),
            },
        )

        # This is the regression check: used to 500 with a ForeignKeyViolation.
        delete_resp = client.delete(f"/bank/accounts/{account_id}", headers=headers)
        assert delete_resp.status_code == 204

        db = SessionLocal()
        try:
            assert db.get(BankAccount, account_id) is None
        finally:
            db.close()

        empty_list_resp = client.get("/bank/accounts", headers=headers)
        assert empty_list_resp.json() == []
    finally:
        db = SessionLocal()
        try:
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    test_profile_update_and_read()
    test_disconnect_account_with_receipt_transaction_does_not_fk_violate()
    print("profile and accounts tests passed.")
