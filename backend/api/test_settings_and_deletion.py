"""
Integration tests for GET/PUT /settings and DELETE /users/me.
Owner: Preetkumar Navinbhai Patel

Exercises the real app end-to-end against the local Postgres database (see
README.md for setup): confirms the consent flag defaults to False, can be
toggled, and that deleting a user cascades away every table the proposal's
GDPR/Privacy Act commitment names - bank_accounts, transactions, receipts,
budgets, forecasts, anomalies, and chat_messages - including anomalies,
whose transaction_id FK previously had no ON DELETE CASCADE and would have
made this deletion fail outright.

Run with:
    pytest backend/api/test_settings_and_deletion.py
"""

import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import (
    Anomaly,
    BankAccount,
    Budget,
    ChatMessage,
    Forecast,
    Receipt,
    Transaction,
    User,
)

client = TestClient(app)


def _register_and_login():
    email = f"settings_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"
    register_resp = client.post(
        "/auth/register",
        json={"full_name": "Settings Test", "email": email, "password": password},
    )
    assert register_resp.status_code == 201
    user_id = register_resp.json()["user_id"]

    login_resp = client.post("/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
    return email, user_id, headers


def test_consent_flag_defaults_false_and_can_be_toggled():
    email, _user_id, headers = _register_and_login()
    try:
        get_resp = client.get("/settings", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json() == {"data_processing_consent": False}

        put_resp = client.put(
            "/settings", headers=headers, json={"data_processing_consent": True}
        )
        assert put_resp.status_code == 200
        assert put_resp.json() == {"data_processing_consent": True}

        get_again = client.get("/settings", headers=headers)
        assert get_again.json() == {"data_processing_consent": True}
    finally:
        db = SessionLocal()
        try:
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


def test_settings_requires_auth():
    assert client.get("/settings").status_code == 401
    assert client.put("/settings", json={"data_processing_consent": True}).status_code == 401


def test_delete_me_cascades_every_linked_table():
    email, user_id, headers = _register_and_login()

    link_resp = client.post("/bank/link-account", headers=headers)
    link_data = link_resp.json()
    callback_resp = client.post(
        "/bank/link-account/callback",
        headers=headers,
        json={"auth_code": link_data["auth_code"], "state": link_data["state"]},
    )
    account_id = callback_resp.json()["account_id"]

    sync_resp = client.post("/bank/sync", headers=headers)
    assert sync_resp.status_code == 200
    assert sync_resp.json()["synced"] > 0

    db = SessionLocal()
    try:
        # A budget, a forecast, a chat message, and - the one that used to
        # block deletion outright - an anomaly on one of the synced txns.
        txn = db.query(Transaction).filter(Transaction.account_id == account_id).first()
        txn_id = txn.transaction_id
        db.add(Budget(
            user_id=user_id, category_id=txn.category_id, period_month=date.today().replace(day=1),
            recommended_amount=100.0, generated_by="ai_engine",
        ))
        db.add(Forecast(
            user_id=user_id, forecast_date=date.today() + timedelta(days=1),
            predicted_balance=500.0, model_version="moving_average",
        ))
        db.add(ChatMessage(user_id=user_id, role="user", content="How am I doing?"))
        db.add(Anomaly(transaction_id=txn_id, anomaly_score=4.2, reason="test anomaly"))
        db.add(Receipt(
            user_id=user_id, transaction_id=txn_id,
            image_path="/tmp/fake.jpg", ocr_raw_text="fake receipt text",
        ))
        db.commit()
    finally:
        db.close()

    delete_resp = client.delete("/users/me", headers=headers)
    assert delete_resp.status_code == 204

    db = SessionLocal()
    try:
        assert db.query(User).filter(User.user_id == user_id).first() is None
        assert db.query(BankAccount).filter(BankAccount.account_id == account_id).first() is None
        assert db.query(Transaction).filter(Transaction.account_id == account_id).count() == 0
        assert db.query(Receipt).filter(Receipt.user_id == user_id).count() == 0
        assert db.query(Budget).filter(Budget.user_id == user_id).count() == 0
        assert db.query(Forecast).filter(Forecast.user_id == user_id).count() == 0
        assert db.query(ChatMessage).filter(ChatMessage.user_id == user_id).count() == 0
        assert db.query(Anomaly).filter(Anomaly.transaction_id == txn_id).count() == 0
    finally:
        db.close()

    # The user no longer exists, so its token should no longer authenticate.
    assert client.get("/users/me", headers=headers).status_code == 401


def test_delete_me_requires_auth():
    assert client.delete("/users/me").status_code == 401


if __name__ == "__main__":
    test_consent_flag_defaults_false_and_can_be_toggled()
    test_settings_requires_auth()
    test_delete_me_cascades_every_linked_table()
    test_delete_me_requires_auth()
    print("settings and deletion tests passed.")
