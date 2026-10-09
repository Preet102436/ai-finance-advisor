"""
Integration test for POST /transactions (manual entry), PUT
/transactions/{id}/category (recategorise), GET /transactions/{id}, and the
`search` filter on GET /transactions.

Run with:
    pytest backend/api/test_manual_transactions.py
"""

import uuid
from datetime import date

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import User

client = TestClient(app)


def test_manual_entry_recategorise_and_search():
    email = f"manual_txn_test_{uuid.uuid4().hex[:8]}@example.com"
    other_email = f"manual_txn_other_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"

    try:
        register_resp = client.post(
            "/auth/register",
            json={"full_name": "Manual Txn Test", "email": email, "password": password},
        )
        assert register_resp.status_code == 201

        login_resp = client.post("/auth/login", json={"email": email, "password": password})
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        link_resp = client.post("/bank/link-account", headers=headers)
        link_data = link_resp.json()
        callback_resp = client.post(
            "/bank/link-account/callback",
            headers=headers,
            json={"auth_code": link_data["auth_code"], "state": link_data["state"]},
        )
        assert callback_resp.status_code == 200

        # Create a manual expense.
        create_resp = client.post(
            "/transactions",
            headers=headers,
            json={
                "amount": -42.50,
                "txn_date": date.today().isoformat(),
                "category_name": "dining",
                "merchant": "Local Diner",
                "description": "Dinner with friends",
            },
        )
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["source"] == "manual"
        assert created["category_name"] == "dining"
        assert created["merchant"] == "Local Diner"
        txn_id = created["transaction_id"]

        # Fetch it back by id.
        get_resp = client.get(f"/transactions/{txn_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["merchant"] == "Local Diner"

        # Search by merchant.
        search_resp = client.get("/transactions", headers=headers, params={"search": "diner"})
        assert search_resp.status_code == 200
        assert any(t["transaction_id"] == txn_id for t in search_resp.json())

        no_match_resp = client.get(
            "/transactions", headers=headers, params={"search": "nonexistent-merchant-xyz"}
        )
        assert no_match_resp.status_code == 200
        assert no_match_resp.json() == []

        # Recategorise it.
        recat_resp = client.put(
            f"/transactions/{txn_id}/category",
            headers=headers,
            json={"category_name": "entertainment"},
        )
        assert recat_resp.status_code == 200
        assert recat_resp.json()["category_name"] == "entertainment"

        # A different user must not be able to see or edit this transaction.
        client.post(
            "/auth/register",
            json={"full_name": "Other User", "email": other_email, "password": password},
        )
        other_login = client.post("/auth/login", json={"email": other_email, "password": password})
        other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

        forbidden_get = client.get(f"/transactions/{txn_id}", headers=other_headers)
        assert forbidden_get.status_code == 404
    finally:
        db = SessionLocal()
        try:
            db.query(User).filter(User.email.in_([email, other_email])).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    test_manual_entry_recategorise_and_search()
    print("manual transactions test passed.")
