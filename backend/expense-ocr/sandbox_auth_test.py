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
import secrets
import time


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
