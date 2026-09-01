"""
Integration test for GET /savings/suggestions.
Owner: Thiwanka Kaushalya Nagasanga

Exercises the real app end-to-end against the local Postgres database (see
README.md for setup): registers a user, links a mock bank account, inserts
real dining transactions that push this month's spend over a real budget
(generated via /budgets/recommend), then confirms /savings/suggestions
returns a suggestion naming the over-budget category and the merchant
driving it - and that categories still under budget aren't suggested.

Run with:
    pytest backend/api/test_savings.py
"""

import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import Category, Transaction, User

client = TestClient(app)


def test_suggestion_names_the_overspend_category_and_merchant():
    email = f"savings_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"

    try:
        register_resp = client.post(
            "/auth/register",
            json={"full_name": "Savings Test", "email": email, "password": password},
        )
        assert register_resp.status_code == 201

        login_resp = client.post("/auth/login", json={"email": email, "password": password})
        assert login_resp.status_code == 200
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        link_resp = client.post("/bank/link-account", headers=headers)
        link_data = link_resp.json()
        callback_resp = client.post(
            "/bank/link-account/callback",
            headers=headers,
            json={"auth_code": link_data["auth_code"], "state": link_data["state"]},
        )
        account_id = callback_resp.json()["account_id"]

        db = SessionLocal()
        try:
            dining = db.query(Category).filter(Category.name == "dining").first()
            if dining is None:
                dining = Category(name="dining")
                db.add(dining)
                db.flush()
            groceries = db.query(Category).filter(Category.name == "groceries").first()
            if groceries is None:
                groceries = Category(name="groceries")
                db.add(groceries)
                db.flush()

            today = date.today()

            # Trailing months of modest dining/groceries spend, so
            # /budgets/recommend has history to generate a real budget from.
            for i in range(3):
                month_offset = 35 + i * 25
                db.add(Transaction(
                    account_id=account_id, category_id=dining.category_id, amount=-30.0,
                    merchant="Corner Cafe", txn_date=today - timedelta(days=month_offset),
                    source="bank_sync",
                ))
                db.add(Transaction(
                    account_id=account_id, category_id=groceries.category_id, amount=-60.0,
                    merchant="Woolworths", txn_date=today - timedelta(days=month_offset),
                    source="bank_sync",
                ))
            db.commit()

            recommend_resp = client.post(
                "/budgets/recommend", headers=headers, params={"window_months": 6}
            )
            assert recommend_resp.status_code == 200
            budgets = {b["category_name"]: b["recommended_amount"] for b in recommend_resp.json()}
            assert "dining" in budgets

            # This month: blow well past the dining budget with repeat visits
            # to one merchant, while staying comfortably under groceries. All
            # dated `today` (not spread across a few days back) since today
            # could be early in the month and spreading them risks landing
            # back in the prior (excluded) month.
            for i in range(4):
                db.add(Transaction(
                    account_id=account_id, category_id=dining.category_id, amount=-80.0,
                    merchant="Rustic Kitchen", txn_date=today,
                    source="bank_sync",
                ))
            db.add(Transaction(
                account_id=account_id, category_id=groceries.category_id, amount=-20.0,
                merchant="Woolworths", txn_date=today, source="bank_sync",
            ))
            db.commit()
        finally:
            db.close()

        suggestions_resp = client.get("/savings/suggestions", headers=headers)
        assert suggestions_resp.status_code == 200
        suggestions = suggestions_resp.json()

        dining_suggestions = [s for s in suggestions if s["category"] == "dining"]
        assert len(dining_suggestions) == 1
        suggestion = dining_suggestions[0]

        assert suggestion["overspend"] > 0
        assert suggestion["top_merchant"] == "Rustic Kitchen"
        assert suggestion["merchant_visit_count"] == 4
        assert "Rustic Kitchen" in suggestion["suggestion"]
        assert "dining" in suggestion["suggestion"]

        # Groceries stayed under budget - no suggestion for it.
        assert all(s["category"] != "groceries" for s in suggestions)
    finally:
        db = SessionLocal()
        try:
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


def test_no_suggestions_when_nothing_is_over_budget():
    email = f"savings_ok_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"

    try:
        register_resp = client.post(
            "/auth/register",
            json={"full_name": "Savings OK Test", "email": email, "password": password},
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

        resp = client.get("/savings/suggestions", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        db = SessionLocal()
        try:
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    test_suggestion_names_the_overspend_category_and_merchant()
    test_no_suggestions_when_nothing_is_over_budget()
    print("savings suggestions tests passed.")
