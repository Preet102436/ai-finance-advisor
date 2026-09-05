"""
Tests that /budgets/recommend, /forecasts, and /anomalies fail cleanly
(logged, clean JSON error) instead of crashing when their underlying
computation blows up - e.g. a forecasting failure on insufficient/irregular
data. Each test forces the relevant computation function to raise, using
real data set up through the actual API (not mocks of the DB itself).
Owner: Parth Patel

Run with:
    pytest backend/api/test_error_handling.py
"""

import uuid
from datetime import date, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import BankAccount, Category, Transaction, User

client = TestClient(app)


def _register_login_link_and_sync():
    email = f"errhandling_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"

    register_resp = client.post(
        "/auth/register",
        json={"full_name": "Error Handling Test", "email": email, "password": password},
    )
    assert register_resp.status_code == 201

    login_resp = client.post("/auth/login", json={"email": email, "password": password})
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    link_resp = client.post("/bank/link-account", headers=headers)
    link_data = link_resp.json()
    client.post(
        "/bank/link-account/callback",
        headers=headers,
        json={"auth_code": link_data["auth_code"], "state": link_data["state"]},
    )

    sync_resp = client.post("/bank/sync", headers=headers)
    assert sync_resp.status_code == 200
    assert sync_resp.json()["synced"] > 0

    return email, headers


def _delete_user(email):
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == email).delete()
        db.commit()
    finally:
        db.close()


def test_forecast_computation_failure_returns_clean_422():
    email, headers = _register_login_link_and_sync()
    try:
        with patch("routers.forecasts.forecast_balance", side_effect=RuntimeError("boom")):
            resp = client.post("/forecasts", headers=headers)
        assert resp.status_code == 422
        assert "forecast" in resp.json()["detail"].lower()
    finally:
        _delete_user(email)


def test_anomaly_detection_failure_returns_clean_422():
    email, headers = _register_login_link_and_sync()
    try:
        with patch("routers.anomalies.detect_anomalies", side_effect=RuntimeError("boom")):
            resp = client.post("/anomalies", headers=headers)
        assert resp.status_code == 422
        assert "anomaly detection" in resp.json()["detail"].lower()
    finally:
        _delete_user(email)


def test_budget_save_failure_returns_clean_500_and_rolls_back():
    email, headers = _register_login_link_and_sync()
    try:
        # /bank/sync's mock data all lands in the current (excluded) month, so
        # /budgets/recommend needs its own trailing-month history to have
        # anything to compute/save at all.
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            account = db.query(BankAccount).filter(BankAccount.user_id == user.user_id).first()
            category = db.query(Category).filter(Category.name == "groceries").first()
            if category is None:
                category = Category(name="groceries")
                db.add(category)
                db.flush()
            for i in range(3):
                db.add(Transaction(
                    account_id=account.account_id, category_id=category.category_id,
                    amount=-50.0, merchant="Woolworths",
                    txn_date=date.today() - timedelta(days=35 + i * 25),
                    source="bank_sync",
                ))
            db.commit()
        finally:
            db.close()

        with patch("routers.budgets.Budget", side_effect=RuntimeError("boom")):
            resp = client.post("/budgets/recommend", headers=headers, params={"window_months": 6})
        assert resp.status_code == 500
        assert "budget" in resp.json()["detail"].lower()

        # Confirm nothing was left half-committed.
        db = SessionLocal()
        try:
            from models import Budget as BudgetModel
            user = db.query(User).filter(User.email == email).first()
            assert db.query(BudgetModel).filter(BudgetModel.user_id == user.user_id).count() == 0
        finally:
            db.close()
    finally:
        _delete_user(email)


if __name__ == "__main__":
    test_forecast_computation_failure_returns_clean_422()
    test_anomaly_detection_failure_returns_clean_422()
    test_budget_save_failure_returns_clean_500_and_rolls_back()
    print("error handling tests passed.")
