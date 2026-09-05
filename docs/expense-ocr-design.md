# Expense Tracking & OCR Subsystem — Design Notes

**Owner:** Preetkumar Navinbhai Patel (Expense Tracking & OCR, Backend Architecture)
**Status:** Complete. Bank sync, receipt OCR, the Transactions/receipt-upload UI,
and the consent/data-deletion settings required by the proposal's GDPR/Privacy Act
commitment are all implemented and tested end-to-end against real Postgres and a
real Tesseract install (see `backend/expense-ocr/`, `backend/api/`, `frontend/`).

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

## Privacy & Data Deletion Flow (GDPR/Privacy Act commitment)
1. `users.data_processing_consent` (new column) tracks whether the user has
   consented to their financial data being processed to generate budgets,
   forecasts, and suggestions - readable/settable via `GET`/`PUT /settings`, and
   surfaced as a toggle on the frontend's Settings page.
2. `DELETE /users/me` permanently deletes the user; every other table
   (`bank_accounts`, `transactions`, `receipts`, `budgets`, `forecasts`,
   `anomalies`, `chat_messages`) cascades away via the `ON DELETE CASCADE`
   foreign keys in `db/schema.sql` - the endpoint itself is just `db.delete(user)`,
   no manual per-table cleanup.
3. The frontend's Settings page exposes this as a "Delete my data" button behind
   an explicit confirmation step, then logs the user out and redirects to `/login`.

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
- [x] `POST /receipts/upload` (`backend/api/routers/receipts.py`): accepts an image
      upload, runs `ocr_prototype.py`'s `extract_text`/`extract_total`/
      `classify_category`, writes matching `receipts` (with the raw OCR text) and
      `transactions` (`source='receipt_ocr'`) rows, and returns the predicted
      category/total. `backend/api/test_receipts_upload.py` covers the endpoint
      end-to-end by patching `extract_text()` to return sample OCR text (mirroring
      how `ocr_prototype.py`'s own tests use `process_receipt_from_text`)
- [x] Tesseract OCR engine installed in the dev environment and verified against a
      real generated receipt image end-to-end through `/receipts/upload` (not just
      the mocked-text test path) - correctly reads the merchant/total and returns
      the right predicted category
- [x] Real Transactions page (`frontend/src/pages/TransactionsPage.jsx`): lists
      transactions with category/date filters, a "Sync bank account" button wired
      to `/bank/sync`, and a receipt-upload form displaying the predicted
      category/total from `/receipts/upload`
- [x] `data_processing_consent` column added to `users` (`db/schema.sql` +
      `models.py`); `GET`/`PUT /settings` (`backend/api/routers/settings.py`) read
      and update it
- [x] `DELETE /users/me` (`backend/api/routers/users.py`) deletes the user and lets
      `ON DELETE CASCADE` remove every linked table. Fixed a real gap found while
      building this: `anomalies.transaction_id` had no cascade (every other
      user-owned table did), which would have made deletion fail outright for any
      user with a flagged anomaly - added the cascade in `db/schema.sql` (existing
      local databases need the `ALTER TABLE` in `backend/api/README.md`)
- [x] Settings page on the frontend (`frontend/src/pages/SettingsPage.jsx`): a
      consent toggle (saves immediately, reverts on failure) and a "Delete my data"
      button behind an explicit confirm/cancel step, then logs out and redirects to
      `/login`. Found and fixed a real bug while testing this: `apiClient.js` tried
      to parse the empty `204 No Content` body from `DELETE /users/me` as JSON and
      threw - it now skips body parsing for 204 responses
- [x] `/bank/sync` and `/receipts/upload` wrapped in try/except around their
      external-call and DB-write steps: a sandbox/OCR failure now logs the full
      traceback server-side (`logging.exception`) and returns a clean 502/503/500
      JSON error instead of an unhandled crash
- [x] Integration test (`backend/api/test_settings_and_deletion.py`, pytest):
      consent defaults to `False` and can be toggled, both `/settings` and
      `DELETE /users/me` require auth, and deletion cascades away a bank account,
      transactions, a receipt, a budget, a forecast, a chat message, and - the case
      that used to fail outright - an anomaly
- [ ] Auto-categorisation upgraded from keyword rules to a trained classifier
- [ ] Live scheduled sync job (planned for Weeks 7-8) - `/bank/sync` above is
      user-triggered, not yet a scheduled job

## Next Steps
- Connect the OAuth2 flow to a registered sandbox app (currently tested with mock
  responses) once sandbox credentials are approved.
- Expand the keyword categoriser into a small trained NLP model using labelled sample
  receipts.
- Turn `/bank/sync` into a scheduled job instead of a manually-triggered endpoint.
