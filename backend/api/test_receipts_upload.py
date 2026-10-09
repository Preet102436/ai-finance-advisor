"""
Integration test for POST /receipts/upload + POST /receipts/{id}/confirm.
Owner: Preetkumar Navinbhai Patel

Exercises the real app end-to-end against the local Postgres database (see
README.md for setup): registers a user, links a mock bank account, uploads a
receipt (preview only, nothing saved as a transaction yet), confirms it, and
checks matching receipts + transactions rows land in the database.

Tesseract isn't installed in this dev environment, so - the same way
ocr_prototype.py's own tests exercise the classifier via
process_receipt_from_text() instead of a real image - this test patches
extract_text() to return sample OCR-style text instead of actually running
the OCR engine. Everything else (the upload, the confirm, the DB writes, the
response) is the real code path.

Run with:
    pytest backend/api/test_receipts_upload.py
"""

import io
import uuid
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import Receipt, Transaction, User

client = TestClient(app)

SAMPLE_RECEIPT_TEXT = "WOOLWORTHS SUPERMARKET\nMilk 3.50\nBread 4.20\nTOTAL   45.20"


def test_uploaded_receipt_previews_then_confirms_into_transaction():
    email = f"receipt_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"

    try:
        register_resp = client.post(
            "/auth/register",
            json={"full_name": "Receipt Test", "email": email, "password": password},
        )
        assert register_resp.status_code == 201

        login_resp = client.post("/auth/login", json={"email": email, "password": password})
        assert login_resp.status_code == 200
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        link_resp = client.post("/bank/link-account", headers=headers)
        assert link_resp.status_code == 200
        link_data = link_resp.json()

        callback_resp = client.post(
            "/bank/link-account/callback",
            headers=headers,
            json={"auth_code": link_data["auth_code"], "state": link_data["state"]},
        )
        assert callback_resp.status_code == 200
        account_id = callback_resp.json()["account_id"]

        fake_image = io.BytesIO(b"not a real image, OCR is mocked below")
        with patch("routers.receipts.extract_text", return_value=SAMPLE_RECEIPT_TEXT):
            upload_resp = client.post(
                "/receipts/upload",
                headers=headers,
                files={"file": ("receipt.jpg", fake_image, "image/jpeg")},
            )

        assert upload_resp.status_code == 200
        preview = upload_resp.json()
        assert preview["predicted_category"] == "groceries"
        assert preview["predicted_total"] == 45.20
        # Case may come back normalised if an OPENAI_API_KEY is configured
        # (LLM extraction) or verbatim from the heuristic fallback otherwise.
        assert preview["predicted_merchant"].strip().lower() == "woolworths supermarket"
        receipt_id = preview["receipt_id"]

        # Nothing should be saved as a transaction until confirmed.
        db = SessionLocal()
        try:
            receipt = db.get(Receipt, receipt_id)
            assert receipt is not None
            assert receipt.transaction_id is None
            assert receipt.ocr_raw_text == SAMPLE_RECEIPT_TEXT
        finally:
            db.close()

        confirm_resp = client.post(
            f"/receipts/{receipt_id}/confirm",
            headers=headers,
            json={
                "total": preview["predicted_total"],
                "category_name": preview["predicted_category"],
                "merchant": preview["predicted_merchant"],
                "txn_date": date.today().isoformat(),
            },
        )
        assert confirm_resp.status_code == 200
        confirm_data = confirm_resp.json()
        transaction_id = confirm_data["transaction_id"]
        assert confirm_data["total"] == 45.20
        assert confirm_data["category_name"] == "groceries"

        db = SessionLocal()
        try:
            receipt = db.get(Receipt, receipt_id)
            assert receipt.transaction_id == transaction_id

            transaction = db.get(Transaction, transaction_id)
            assert transaction is not None
            assert transaction.account_id == account_id
            assert transaction.source == "receipt_ocr"
            assert transaction.merchant == preview["predicted_merchant"]
            assert float(transaction.amount) == -45.20
        finally:
            db.close()

        # Confirming the same receipt twice should be rejected, not double-save.
        reconfirm_resp = client.post(
            f"/receipts/{receipt_id}/confirm",
            headers=headers,
            json={
                "total": 45.20,
                "category_name": "groceries",
                "txn_date": date.today().isoformat(),
            },
        )
        assert reconfirm_resp.status_code == 400
    finally:
        db = SessionLocal()
        try:
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    test_uploaded_receipt_previews_then_confirms_into_transaction()
    print("receipts upload/confirm test passed.")
