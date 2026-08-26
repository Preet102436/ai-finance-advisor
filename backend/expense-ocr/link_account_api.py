"""
Expense Tracking & OCR Subsystem - /link-account API stub
Owner: Preetkumar Navinbhai Patel

Wraps the mocked OAuth2 flow from sandbox_auth_test.py (MockSandboxProvider) as a
real FastAPI route, so the "Link account" flow described in
docs/expense-ocr-design.md can be exercised end-to-end from the frontend during
local development. Still prototype-stage: MockSandboxProvider stands in for a real
Open Banking sandbox until credentials are approved. Persistence is optional and
injected by the caller (see create_router()) - when mounted by backend/api/main.py
it writes the hashed external_ref to bank_accounts; run standalone, it doesn't.

Requires: pip install fastapi uvicorn pydantic

Usage:
    uvicorn link_account_api:app --reload
"""

import secrets

try:
    from fastapi import APIRouter, Depends, FastAPI, HTTPException
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from sandbox_auth_test import MockSandboxProvider, external_ref_for_storage

CLIENT_ID = "ai-finance-advisor-dev"
REDIRECT_URI = "http://localhost:3000/oauth/callback"


def create_router(on_link_success=None, get_db_dependency=None, get_current_user_dependency=None):
    """Build the APIRouter for the link-account flow, so it can be mounted
    into another FastAPI app (see backend/api/main.py). Raises if
    fastapi/pydantic aren't installed.

    By default (no arguments) this runs standalone with no auth and no
    persistence, exactly as before - useful for exercising the mocked OAuth
    flow on its own. When backend/api/main.py mounts this router it passes
    real dependencies so `/link-account/callback` writes a bank_accounts row:

    - `get_current_user_dependency`: a FastAPI dependency resolving the
      authenticated user (e.g. deps.get_current_user)
    - `get_db_dependency`: a FastAPI dependency yielding a DB session (e.g.
      database.get_db)
    - `on_link_success(db, user_id, external_ref) -> account_id`: called once
      the token exchange succeeds, responsible for persisting the account
    """
    if not FASTAPI_AVAILABLE:
        raise RuntimeError(
            "fastapi/pydantic not installed. Run: pip install fastapi uvicorn pydantic"
        )

    class CallbackRequest(BaseModel):
        auth_code: str
        state: str
        client_secret: str = "dev-secret"

    def _no_auth():
        return None

    def _no_db():
        return None

    auth_dependency = get_current_user_dependency or _no_auth
    db_dependency = get_db_dependency or _no_db

    router = APIRouter(tags=["link-account"])
    provider = MockSandboxProvider()
    pending_states = {}

    @router.post("/link-account")
    def link_account(current_user=Depends(auth_dependency)):
        """Step 1: user clicks "Link account" in the web app.

        In the real flow this would return a redirect URL to the sandbox
        provider's consent screen. MockSandboxProvider has no real consent
        screen, so we issue the authorisation code directly here, letting the
        rest of the flow be exercised without a live provider.
        """
        state = secrets.token_urlsafe(8)
        auth_code, returned_state = provider.authorize(CLIENT_ID, REDIRECT_URI, state)
        pending_states[returned_state] = {
            "auth_code": auth_code,
            "user_id": getattr(current_user, "user_id", None),
        }
        return {"auth_code": auth_code, "state": returned_state, "redirect_uri": REDIRECT_URI}

    @router.post("/link-account/callback")
    def link_account_callback(
        payload: CallbackRequest,
        current_user=Depends(auth_dependency),
        db=Depends(db_dependency),
    ):
        """Step 2: provider redirects back with an authorisation code.

        Exchanges the code for a token pair, and - when mounted with real
        dependencies - writes the hashed reference to bank_accounts via
        `on_link_success`. The raw access/refresh tokens never leave the
        backend and are never persisted.
        """
        record = pending_states.get(payload.state)
        if not record or record["auth_code"] != payload.auth_code:
            raise HTTPException(status_code=400, detail="CSRF state mismatch")

        try:
            token_response = provider.exchange_token(
                payload.auth_code, CLIENT_ID, payload.client_secret
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        del pending_states[payload.state]
        external_ref = external_ref_for_storage(token_response["access_token"])

        account_id = None
        user_id = getattr(current_user, "user_id", None) or record["user_id"]
        if on_link_success is not None and db is not None and user_id is not None:
            account_id = on_link_success(db, user_id, external_ref)

        return {
            "account_id": account_id,
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
