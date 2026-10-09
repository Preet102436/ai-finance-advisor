"""
Integration test proving the chatbot is actually grounded in the user's real
forecast data - a real gap found after the fact: build_prompt() never
received forecast data at all, so a question like "what's my balance
forecast?" had nothing real to answer from. Covers both the new
finance_data.load_latest_forecast() helper and chatbot_prototype.build_prompt()
including it in the constructed prompt.

Run with:
    pytest backend/api/test_chat_forecast_context.py
"""

import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
from finance_data import load_latest_forecast
from main import app  # import main first - it adds chatbot-savings/ to sys.path
from models import User

from chatbot_prototype import build_prompt  # noqa: E402

client = TestClient(app)


def test_chat_prompt_includes_real_forecast_data():
    email = f"forecast_chat_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"

    try:
        client.post("/auth/register", json={"full_name": "x", "email": email, "password": password})
        login = client.post("/auth/login", json={"email": email, "password": password})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        link = client.post("/bank/link-account", headers=headers).json()
        client.post(
            "/bank/link-account/callback",
            headers=headers,
            json={"auth_code": link["auth_code"], "state": link["state"]},
        )
        client.post("/bank/sync", headers=headers)

        # No forecast generated yet - load_latest_forecast() must return None,
        # not raise, and the chat endpoint must still work.
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            assert load_latest_forecast(db, user.user_id) is None
        finally:
            db.close()

        chat_before = client.post("/chat/messages", headers=headers, json={"question": "hi"})
        assert chat_before.status_code == 200

        # Generate a real forecast (same as visiting the Dashboard would).
        forecast_resp = client.post("/forecasts", headers=headers, params={"days_ahead": 7})
        assert forecast_resp.status_code == 200
        forecast_data = forecast_resp.json()

        db = SessionLocal()
        try:
            summary = load_latest_forecast(db, user.user_id)
        finally:
            db.close()

        assert summary is not None
        assert summary["days_ahead"] == len(forecast_data["forecast"])
        assert summary["end_balance"] == forecast_data["forecast"][-1]["predicted_balance"]

        # The actual prompt sent to the LLM must mention the real numbers -
        # this is the part that was silently missing before.
        prompt = build_prompt("What's my balance forecast?", [], budgets={}, forecast=summary)
        assert str(summary["end_balance"]) in prompt or f"{summary['end_balance']:.2f}" in prompt
        assert summary["method"] in prompt

        chat_after = client.post(
            "/chat/messages", headers=headers, json={"question": "What's my balance forecast?"}
        )
        assert chat_after.status_code == 200
    finally:
        db = SessionLocal()
        try:
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    test_chat_prompt_includes_real_forecast_data()
    print("chat forecast context test passed.")
