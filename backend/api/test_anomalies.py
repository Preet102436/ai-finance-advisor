"""
Integration test for POST /anomalies.
Owner: Parth Patel

Exercises the real app end-to-end against the local Postgres database (see
README.md for setup): registers a user, links a mock bank account, inserts a
handful of same-category transactions with one clear outlier, and confirms
the outlier is flagged and written to `anomalies` with the right z-score -
while the normal transactions are left alone.

Run with:
    pytest backend/api/test_anomalies.py
"""

import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import Anomaly, Category, Transaction, User

client = TestClient(app)


def test_outlier_transaction_is_flagged_and_persisted():
    email = f"anomaly_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"
    transaction_ids = []

    try:
        register_resp = client.post(
            "/auth/register",
            json={"full_name": "Anomaly Test", "email": email, "password": password},
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
            category = db.query(Category).filter(Category.name == "groceries").first()
            if category is None:
                category = Category(name="groceries")
                db.add(category)
                db.flush()

            today = date.today()
            # Same shape as forecast_prototype.py's own
            # test_flags_outlier_amount_in_category: enough same-valued rows
            # that one big outlier still clears z_threshold=3.0 despite also
            # inflating the population stdev used to score itself.
            normal_amounts = [-50.0] * 10
            for i, amount in enumerate(normal_amounts):
                txn = Transaction(
                    account_id=account_id,
                    category_id=category.category_id,
                    amount=amount,
                    merchant="Woolworths",
                    txn_date=today - timedelta(days=i + 1),
                    source="bank_sync",
                )
                db.add(txn)
                db.flush()
                transaction_ids.append(txn.transaction_id)

            outlier = Transaction(
                account_id=account_id,
                category_id=category.category_id,
                amount=-900.0,
                merchant="Woolworths",
                txn_date=today,
                source="bank_sync",
            )
            db.add(outlier)
            db.flush()
            outlier_id = outlier.transaction_id
            transaction_ids.append(outlier_id)
            db.commit()
        finally:
            db.close()

        anomalies_resp = client.post("/anomalies", headers=headers)
        assert anomalies_resp.status_code == 200
        flagged = anomalies_resp.json()

        assert len(flagged) == 1
        assert flagged[0]["transaction_id"] == outlier_id
        assert flagged[0]["category_name"] == "groceries"
        assert flagged[0]["z_score"] > 3.0

        db = SessionLocal()
        try:
            anomaly = db.query(Anomaly).filter(Anomaly.transaction_id == outlier_id).first()
            assert anomaly is not None
            assert float(anomaly.anomaly_score) == flagged[0]["z_score"]

            for normal_id in transaction_ids[:-1]:
                assert db.query(Anomaly).filter(Anomaly.transaction_id == normal_id).first() is None
        finally:
            db.close()

        # Re-running should update the existing row, not duplicate it.
        rerun_resp = client.post("/anomalies", headers=headers)
        assert rerun_resp.status_code == 200
        assert len(rerun_resp.json()) == 1

        db = SessionLocal()
        try:
            count = db.query(Anomaly).filter(Anomaly.transaction_id == outlier_id).count()
            assert count == 1
        finally:
            db.close()
    finally:
        db = SessionLocal()
        try:
            # anomalies.transaction_id has no ON DELETE CASCADE, so these must
            # be removed before the user (whose delete cascades down through
            # bank_accounts -> transactions) or that delete will fail.
            db.query(Anomaly).filter(Anomaly.transaction_id.in_(transaction_ids)).delete(
                synchronize_session=False
            )
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    test_outlier_transaction_is_flagged_and_persisted()
    print("anomalies test passed.")
