"""
Integration test for POST /chat/messages.
Owner: Thiwanka Kaushalya Nagasanga

Exercises the real app end-to-end against the local Postgres database (see
README.md for setup): registers a user, links a mock bank account, inserts
real dining transactions, generates a real budget for that category (via
/budgets/recommend), then asks the chat endpoint about dining - confirming
the retrieval pulled the real transactions/budget (not the prototype's
SAMPLE_TRANSACTIONS/SAMPLE_BUDGETS) and that both the question and answer
were logged to chat_messages with the retrieved context attached.

No OPENAI_API_KEY is configured in this dev environment, so call_llm() falls
back to its documented offline behaviour (no LLM actually called) - the same
path chatbot_prototype.py itself is designed to be testable through.

Run with:
    pytest backend/api/test_chat.py
"""

import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models import Category, ChatMessage, Transaction, User

client = TestClient(app)


def test_chat_answer_is_grounded_in_real_data_and_logged():
    email = f"chat_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"

    try:
        register_resp = client.post(
            "/auth/register",
            json={"full_name": "Chat Test", "email": email, "password": password},
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
            category = db.query(Category).filter(Category.name == "dining").first()
            if category is None:
                category = Category(name="dining")
                db.add(category)
                db.flush()

            today = date.today()
            # /budgets/recommend only looks at trailing *complete* calendar
            # months before the current one, so these need to land there.
            for i, amount in enumerate([-45.0, -38.0, -60.0, -22.0]):
                db.add(
                    Transaction(
                        account_id=account_id,
                        category_id=category.category_id,
                        amount=amount,
                        merchant="Corner Cafe",
                        txn_date=today - timedelta(days=35 + i * 5),
                        source="bank_sync",
                    )
                )
            db.commit()
        finally:
            db.close()

        # Real budget for "dining", generated the same way a real user would.
        recommend_resp = client.post(
            "/budgets/recommend", headers=headers, params={"window_months": 6}
        )
        assert recommend_resp.status_code == 200
        assert any(b["category_name"] == "dining" for b in recommend_resp.json())

        chat_resp = client.post(
            "/chat/messages",
            headers=headers,
            json={"question": "Am I over budget on dining?"},
        )
        assert chat_resp.status_code == 200
        chat_data = chat_resp.json()

        assert "dining" in chat_data["retrieved_context"].lower()
        assert "Corner Cafe" in chat_data["retrieved_context"]
        # Sample data ("Rustic Kitchen" etc.) must not leak into a real answer.
        assert "Rustic Kitchen" not in chat_data["retrieved_context"]
        assert chat_data["answer"]

        db = SessionLocal()
        try:
            messages = (
                db.query(ChatMessage)
                .filter(ChatMessage.message_id.in_([chat_data["message_id"]]))
                .all()
            )
            assert len(messages) == 1
            assistant_message = messages[0]
            assert assistant_message.role == "assistant"
            assert assistant_message.retrieved_context == chat_data["retrieved_context"]

            user_message = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.user_id == assistant_message.user_id,
                    ChatMessage.role == "user",
                )
                .first()
            )
            assert user_message is not None
            assert user_message.content == "Am I over budget on dining?"
            assert user_message.retrieved_context is None
        finally:
            db.close()
    finally:
        db = SessionLocal()
        try:
            db.query(User).filter(User.email == email).delete()
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    test_chat_answer_is_grounded_in_real_data_and_logged()
    print("chat test passed.")
