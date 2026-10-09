"""Regression test for a real gap: when the LLM is unavailable (ai_enabled
off, or no OPENAI_API_KEY), every chat question used to collapse to the same
"I can't put together a personalised answer..." + last-5-transactions
message, regardless of what was actually asked. Fixed in
routers/chat.py::_offline_fallback_answer, which now varies the answer by
question topic (forecast / budget / savings / generic) using real data.

Run with:
    pytest backend/api/test_chat_offline_fallback.py
"""

import uuid

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _register_and_login():
    email = f"offline_fallback_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"
    client.post("/auth/register", json={"full_name": "x", "email": email, "password": password})
    login = client.post("/auth/login", json={"email": email, "password": password})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    return email, headers


def test_different_offline_questions_get_different_answers():
    email, headers = _register_and_login()
    try:
        # Force the offline path regardless of whether an OPENAI_API_KEY is
        # configured in this environment, so the test is deterministic.
        client.put("/settings", headers=headers, json={"ai_enabled": False})

        link = client.post("/bank/link-account", headers=headers).json()
        client.post(
            "/bank/link-account/callback",
            headers=headers,
            json={"auth_code": link["auth_code"], "state": link["state"]},
        )
        client.post("/bank/sync", headers=headers)

        budget_q = client.post("/chat/messages", headers=headers, json={"question": "Am I over budget this month?"})
        savings_q = client.post("/chat/messages", headers=headers, json={"question": "How can I save money?"})
        forecast_q = client.post("/chat/messages", headers=headers, json={"question": "What's my balance forecast?"})

        assert budget_q.status_code == savings_q.status_code == forecast_q.status_code == 200

        budget_answer = budget_q.json()["answer"]
        savings_answer = savings_q.json()["answer"]
        forecast_answer = forecast_q.json()["answer"]

        # The old bug: all three would be identical. Now each is grounded in
        # a different slice of real data and must differ from the others.
        assert budget_answer != savings_answer
        assert budget_answer != forecast_answer
        assert savings_answer != forecast_answer

        # No forecast has been generated yet for this user, so the forecast
        # answer should say so rather than silently reusing another topic's text.
        assert "forecast" in forecast_answer.lower()
    finally:
        from database import SessionLocal
        from models import User

        db = SessionLocal()
        try:
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    test_different_offline_questions_get_different_answers()
    print("offline fallback differentiation test passed.")
