"""
Expense Tracking & OCR Subsystem - /link-account API stub
Owner: Preetkumar Navinbhai Patel

Wraps the mocked OAuth2 flow from sandbox_auth_test.py (MockSandboxProvider) as a
real FastAPI route, so the "Link account" flow described in
docs/expense-ocr-design.md can be exercised end-to-end from the frontend during
local development. Still prototype-stage: MockSandboxProvider stands in for a real
Open Banking sandbox until credentials are approved, and no persistence layer is
wired up yet (bank_accounts.external_ref would be written here in the real
implementation).

Requires: pip install fastapi uvicorn pydantic

Usage:
    uvicorn link_account_api:app --reload
"""

import secrets

try:
    from fastapi import APIRouter, FastAPI, HTTPException
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from sandbox_auth_test import MockSandboxProvider, external_ref_for_storage

CLIENT_ID = "ai-finance-advisor-dev"
REDIRECT_URI = "http://localhost:3000/oauth/callback"


def create_router():
    """Build the APIRouter for the link-account flow, so it can be mounted
    into another FastAPI app (see backend/api/main.py). Raises if
    fastapi/pydantic aren't installed."""
    if not FASTAPI_AVAILABLE:
        raise RuntimeError(
            "fastapi/pydantic not installed. Run: pip install fastapi uvicorn pydantic"
        )

    class CallbackRequest(BaseModel):
        auth_code: str
        state: str
        client_secret: str = "dev-secret"

    router = APIRouter(tags=["link-account"])
    provider = MockSandboxProvider()
    pending_states = {}

    @router.post("/link-account")
    def link_account():
        """Step 1: user clicks "Link account" in the web app.

        In the real flow this would return a redirect URL to the sandbox
        provider's consent screen. MockSandboxProvider has no real consent
        screen, so we issue the authorisation code directly here, letting the
        rest of the flow be exercised without a live provider.
        """
        state = secrets.token_urlsafe(8)
        auth_code, returned_state = provider.authorize(CLIENT_ID, REDIRECT_URI, state)
        pending_states[returned_state] = auth_code
        return {"auth_code": auth_code, "state": returned_state, "redirect_uri": REDIRECT_URI}

    @router.post("/link-account/callback")
    def link_account_callback(payload: CallbackRequest):
        """Step 2: provider redirects back with an authorisation code.

        Exchanges the code for a token pair and returns only the hashed
        reference that would be stored in bank_accounts.external_ref - the raw
        access/refresh tokens never leave the backend.
        """
        if pending_states.get(payload.state) != payload.auth_code:
            raise HTTPException(status_code=400, detail="CSRF state mismatch")

        try:
            token_response = provider.exchange_token(
                payload.auth_code, CLIENT_ID, payload.client_secret
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        del pending_states[payload.state]
        external_ref = external_ref_for_storage(token_response["access_token"])
        return {
            "external_ref": external_ref,
            "token_type": token_response["token_type"],
            "expires_in": token_response["expires_in"],
        }

    return router


def create_app():
    """Build a standalone FastAPI app wrapping the router, for running this
    module on its own (uvicorn link_account_api:app --reload)."""
    app = FastAPI(title="Expense Tracking & OCR - Link Account API")
    app.include_router(create_router())
    return app


router = create_router() if FASTAPI_AVAILABLE else None
app = create_app() if FASTAPI_AVAILABLE else None
