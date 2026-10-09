"""
Integration test for manual budget CRUD (GET/POST/PUT /budgets) and
GET /insights (month-over-month trends, budget warnings, end-of-month
prediction).

Run with:
    pytest backend/api/test_budgets_and_insights.py
"""

import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import Category, Transaction, User

client = TestClient(app)


def _subtract_months(d: date, months: int) -> date:
    year = d.year
    month = d.month - months
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def test_manual_budget_crud_and_insights():
    email = f"budget_insight_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"

    try:
        register_resp = client.post(
            "/auth/register",
            json={"full_name": "Budget Insight Test", "email": email, "password": password},
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
        account_id = callback_resp.json()["account_id"]

        # Create a manual budget for "dining".
        create_resp = client.post(
            "/budgets", headers=headers, json={"category_name": "dining", "amount": 50.0}
        )
        assert create_resp.status_code == 201
        budget = create_resp.json()
        assert budget["category_name"] == "dining"
        assert budget["recommended_amount"] == 50.0
        assert budget["generated_by"] == "user"
        budget_id = budget["budget_id"]

        # Creating again for the same category/month overwrites, not duplicates.
        overwrite_resp = client.post(
            "/budgets", headers=headers, json={"category_name": "dining", "amount": 60.0}
        )
        assert overwrite_resp.status_code == 201
        assert overwrite_resp.json()["budget_id"] == budget_id
        assert overwrite_resp.json()["recommended_amount"] == 60.0

        # Edit it directly by id.
        edit_resp = client.put(f"/budgets/{budget_id}", headers=headers, json={"amount": 40.0})
        assert edit_resp.status_code == 200
        assert edit_resp.json()["recommended_amount"] == 40.0

        # List budgets for this month includes it.
        list_resp = client.get("/budgets", headers=headers)
        assert list_resp.status_code == 200
        assert any(b["budget_id"] == budget_id for b in list_resp.json())

        # Seed transactions: last month $20 dining (so this month's $45 is a
        # clear >10% increase), and this month $45 dining (90% of the $40 for
        # overspend) in the db directly, same pattern as other tests here.
        db = SessionLocal()
        try:
            category = db.query(Category).filter(Category.name == "dining").first()
            today = date.today()
            last_month = _subtract_months(today.replace(day=1), 1)

            db.add(
                Transaction(
                    account_id=account_id,
                    category_id=category.category_id,
                    amount=-20.0,
                    merchant="Old Cafe",
                    txn_date=last_month + timedelta(days=2),
                    source="bank_sync",
                )
            )
            db.add(
                Transaction(
                    account_id=account_id,
                    category_id=category.category_id,
                    amount=-45.0,
                    merchant="New Cafe",
                    txn_date=today,
                    source="bank_sync",
                )
            )
            db.commit()
        finally:
            db.close()

        insights_resp = client.get("/insights", headers=headers)
        assert insights_resp.status_code == 200
        insights = insights_resp.json()
        assert len(insights) > 0

        messages = " | ".join(i["message"] for i in insights)
        assert "dining" in messages.lower()
        # $45 spent against a $40 budget is over budget - should be flagged critical.
        assert any(i["severity"] == "critical" and "dining" in i["message"].lower() for i in insights)
    finally:
        db = SessionLocal()
        try:
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    test_manual_budget_crud_and_insights()
    print("budgets/insights test passed.")
