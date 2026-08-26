# Expense Tracking & OCR Subsystem — Design Notes

**Owner:** Preetkumar Navinbhai Patel (Expense Tracking & OCR, Backend Architecture)
**Status:** Bank sandbox auth flow and OCR pipeline designed; stubs implemented
(see `backend/expense-ocr/`). Main backend scaffolded with DB connection, auth,
and router stubs (see `backend/api/`).

## Purpose
Automatically sync bank transactions from a sandbox Open Banking-style API, and allow
users to photograph receipts, which are OCR-scanned and auto-categorised.

## Bank Sync Flow (OAuth2)
1. User initiates "Link account" in the web app.
2. Backend redirects to the sandbox provider's OAuth2 consent screen.
3. On consent, the provider returns an authorisation code to a registered redirect URI.
4. Backend exchanges the code for an access/refresh token pair (never exposed to the
   frontend) and stores only a reference token against `bank_accounts.external_ref`.
5. A scheduled sync job calls the provider's transactions endpoint and inserts new rows
   into `transactions`, tagging `source = 'bank_sync'`.

## Receipt OCR Flow
1. User uploads a receipt photo from the web app.
2. Backend stores the image and runs Tesseract OCR to extract raw text.
3. A lightweight rule/keyword-based classifier (prototype stage) maps extracted merchant
   and item text to a `category_id`; this will be upgraded to a trained NLP classifier
   in a later iteration.
4. A `transactions` row is created with `source = 'receipt_ocr'`, linked to the
   corresponding `receipts` row.

## Current Progress
- [x] Database schema finalised for `bank_accounts`, `transactions`, and `receipts`
- [x] OAuth2 sandbox flow designed and a standalone test script written
      (`sandbox_auth_test.py`)
- [x] OCR prototype implemented against sample receipt images (`ocr_prototype.py`)
- [x] `/link-account` FastAPI route (`link_account_api.py`) wrapping the sandbox
      OAuth2 flow as a real, callable API (still backed by `MockSandboxProvider`)
- [x] Keyword classifier expanded with more brands/terms and three new categories
      (entertainment, health, shopping); unit tests added (`test_ocr_prototype.py`,
      pytest) covering the new sample receipts
- [x] Main FastAPI backend scaffolded (`backend/api/`): SQLAlchemy connection to
      Postgres via `db/schema.sql` and a `.env`-based config, bcrypt-hashed
      `/auth/register` + `/auth/login` issuing JWTs, protected `/users/me`, empty
      TODO-commented stubs for `/transactions`, `/budgets`, `/forecasts`,
      `/receipts`, `/chat`, `/savings`, `/settings`, and `link_account_api.py`'s
      router mounted in
- [x] `/bank/link-account` and `/bank/link-account/callback` wired into the real app
      with auth + a DB session (`link_account_api.create_router()` now takes optional
      `on_link_success`/dependency hooks, wired in `backend/api/main.py`); the callback
      writes a real `bank_accounts` row with the hashed `external_ref`. Running
      `link_account_api.py` standalone still works with no auth/persistence.
- [x] `POST /bank/sync` (`backend/api/routers/bank.py`): reads the sandbox's mocked
      transaction data (`sandbox_auth_test.mock_transactions()`, new) and inserts
      `transactions` rows with `source='bank_sync'`, skipping rows already synced
- [x] Integration test (`backend/api/test_bank_sync.py`, pytest) exercising
      register -> login -> link-account -> callback -> sync end-to-end and confirming
      the synced rows land in the database, plus a re-sync produces no duplicates
- [ ] Auto-categorisation upgraded from keyword rules to a trained classifier
- [ ] Live scheduled sync job (planned for Weeks 7-8) - `/bank/sync` above is
      user-triggered, not yet a scheduled job

## Next Steps
- Connect the OAuth2 flow to a registered sandbox app (currently tested with mock
  responses) once sandbox credentials are approved.
- Expand the keyword categoriser into a small trained NLP model using labelled sample
  receipts.
- Turn `/bank/sync` into a scheduled job instead of a manually-triggered endpoint.
