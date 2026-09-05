"""
Expense Tracking & OCR Subsystem - Open Banking Sandbox OAuth2 Flow (stub/test)
Owner: Preetkumar Navinbhai Patel

This is a standalone, mocked test of the OAuth2 authorisation-code flow that will be
used against a real Open Banking-style sandbox once credentials are approved. It
exercises the same steps and data shape without calling a live provider, so the flow
can be unit-tested and reviewed before wiring it into the main backend.

Real usage will replace MockSandboxProvider with actual HTTP calls to the sandbox's
/authorize and /token endpoints.
"""

import base64
import hashlib
import random
import secrets
import time
from datetime import date, timedelta


class MockSandboxProvider:
    """Stands in for a real Open Banking sandbox during local development/testing."""

    def __init__(self):
        self._issued_codes = {}
        self._issued_tokens = {}

    def authorize(self, client_id, redirect_uri, state):
        # In a real flow this would redirect the user to a consent screen.
        auth_code = secrets.token_urlsafe(16)
        self._issued_codes[auth_code] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "expires_at": time.time() + 60,
        }
        return auth_code, state

    def exchange_token(self, auth_code, client_id, client_secret):
        record = self._issued_codes.get(auth_code)
        if not record or record["client_id"] != client_id:
            raise ValueError("Invalid authorisation code")
        if record["expires_at"] < time.time():
            raise ValueError("Authorisation code expired")

        access_token = base64.urlsafe_b64encode(secrets.token_bytes(24)).decode()
        refresh_token = base64.urlsafe_b64encode(secrets.token_bytes(24)).decode()
        self._issued_tokens[access_token] = {"client_id": client_id}
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 3600,
            "token_type": "Bearer",
        }


def external_ref_for_storage(access_token):
    """We never store the raw access token. We store a hashed reference so the
    bank_accounts.external_ref column never exposes usable credentials directly,
    even if the database were compromised - the real token lives in a separate,
    more tightly-controlled secrets store in the full implementation."""
    return hashlib.sha256(access_token.encode()).hexdigest()


MERCHANTS_BY_CATEGORY = {
    "groceries": ["Woolworths", "Coles", "Aldi", "IGA"],
    "dining": ["Cafe Nero", "The Corner Bistro", "Pizzeria Napoli", "Golden Dragon Takeaway"],
    "utilities": ["EnergyCo", "CityWater", "MetroGas", "NetLine Broadband"],
    "subscriptions": ["Netflix", "Spotify", "Disney+"],
    "transport": ["Uber", "Metro Transit", "CityCab", "Shell Petrol"],
    "entertainment": ["Hoyts Cinema", "Ticketmaster", "Steam"],
    "health": ["City Chemist", "Wellness Clinic", "Bright Smile Dental"],
    "shopping": ["Kmart", "Target", "Amazon", "Big W"],
}

# (min, max) magnitude per category - amounts are stored as negative (spend).
AMOUNT_RANGES = {
    "groceries": (15, 120),
    "dining": (8, 60),
    "utilities": (40, 150),
    "subscriptions": (5, 20),
    "transport": (5, 45),
    "entertainment": (10, 80),
    "health": (10, 100),
    "shopping": (10, 150),
}

DESCRIPTIONS_BY_CATEGORY = {
    "groceries": "Groceries",
    "dining": "Meal",
    "utilities": "Utility bill",
    "subscriptions": "Subscription",
    "transport": "Fare",
    "entertainment": "Entertainment",
    "health": "Health/pharmacy",
    "shopping": "Purchase",
}

INCOME_RANGE = (2200, 3800)


def mock_transactions(seed=None, anchor_date=None):
    """Canned-but-randomised transaction data standing in for a call to the
    sandbox's /transactions endpoint, until real Open Banking credentials are
    approved.

    `seed` (pass the linked account's id) makes the randomness deterministic
    per account: the same account always regenerates the exact same rows, so
    /bank/sync's "skip already-synced" duplicate check keeps working across
    re-syncs, while different accounts/users get different amounts,
    categories, merchants and transaction counts.

    `anchor_date` (pass the account's linked_at date) is what dates are
    computed relative to. Anchoring to link time rather than "today" means
    the same account produces the exact same dates no matter which day you
    sync on - anchoring to "today" would make every day's sync compute a
    different absolute date for what's otherwise an identical row, which the
    duplicate check (an exact date match) wouldn't recognise as the same
    transaction, so a fresh batch would get inserted on every new day.
    Defaults to today, for standalone/CLI use with no linked account.
    """
    rng = random.Random(seed)
    today = anchor_date or date.today()
    categories = list(AMOUNT_RANGES.keys())

    records = []
    # A handful of transactions per category (not just one), so a single
    # sync gives budgets/anomalies enough same-category history to be
    # meaningful without the user having to upload receipts by hand.
    for category in categories:
        for _ in range(rng.randint(2, 5)):
            low, high = AMOUNT_RANGES[category]
            records.append({
                "date": today - timedelta(days=rng.randint(1, 75)),
                "amount": -round(rng.uniform(low, high), 2),
                "description": DESCRIPTIONS_BY_CATEGORY[category],
                "merchant": rng.choice(MERCHANTS_BY_CATEGORY[category]),
                "category": category,
            })

    # One salary deposit per (roughly) month of history covered above.
    for month in range(3):
        records.append({
            "date": today - timedelta(days=month * 30 + rng.randint(1, 5)),
            "amount": round(rng.uniform(*INCOME_RANGE), 2),
            "description": "Salary",
            "merchant": "Employer Pty Ltd",
            "category": "income",
        })

    records.sort(key=lambda r: r["date"], reverse=True)
    return records


def run_flow_test():
    provider = MockSandboxProvider()
    client_id = "ai-finance-advisor-dev"
    redirect_uri = "http://localhost:3000/oauth/callback"
    state = secrets.token_urlsafe(8)

    auth_code, returned_state = provider.authorize(client_id, redirect_uri, state)
    assert returned_state == state, "CSRF state mismatch - would abort in real flow"

    token_response = provider.exchange_token(auth_code, client_id, client_secret="dev-secret")
    stored_ref = external_ref_for_storage(token_response["access_token"])

    print("Authorisation code issued:", auth_code)
    print("Token exchange successful. Token type:", token_response["token_type"])
    print("Value that would be stored in bank_accounts.external_ref:", stored_ref)
    print("\nFlow test passed.")


if __name__ == "__main__":
    run_flow_test()
