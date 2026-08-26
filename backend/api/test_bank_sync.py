"""
Integration test for the /bank/link-account -> /bank/sync flow.
Owner: Preetkumar Navinbhai Patel

Exercises the real app end-to-end against the local Postgres database (see
README.md for setup): registers a user, links a mock bank account, syncs
transactions, and confirms a synced row actually lands in `transactions`.

Run with:
    pytest backend/api/test_bank_sync.py
"""

import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import Transaction, User

client = TestClient(app)


def test_synced_transaction_appears_in_database():
    email = f"bank_sync_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"

    try:
        register_resp = client.post(
            "/auth/register",
            json={"full_name": "Bank Sync Test", "email": email, "password": password},
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
        callback_data = callback_resp.json()
        account_id = callback_data["account_id"]
        assert account_id is not None
        assert callback_data["external_ref"]

        sync_resp = client.post("/bank/sync", headers=headers)
        assert sync_resp.status_code == 200
        sync_data = sync_resp.json()
        assert sync_data["account_id"] == account_id
        assert sync_data["synced"] > 0

        db = SessionLocal()
        try:
            txns = db.query(Transaction).filter(Transaction.account_id == account_id).all()
            assert len(txns) == sync_data["synced"]
            assert all(t.source == "bank_sync" for t in txns)
        finally:
            db.close()

        # Re-syncing should not create duplicates.
        resync_resp = client.post("/bank/sync", headers=headers)
        assert resync_resp.status_code == 200
        assert resync_resp.json()["synced"] == 0
    finally:
        db = SessionLocal()
        try:
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    test_synced_transaction_appears_in_database()
    print("bank sync test passed.")
