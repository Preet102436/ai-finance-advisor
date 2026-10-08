# Backend API

FastAPI backend for the AI-Powered Personal Finance Advisor. Connects to a local
PostgreSQL database using the shared schema in [`db/schema.sql`](../../db/schema.sql).

## 1. Local Postgres setup

Assumes PostgreSQL is already installed and running locally (not Docker).

```bash
# Create the database (run once)
createdb -U postgres finance_advisor
# or: psql -U postgres -c "CREATE DATABASE finance_advisor;"

# Apply the shared schema
psql -U postgres -d finance_advisor -f ../../db/schema.sql
```

If you already have a local database from before the consent/anomalies-cascade schema
update, `db/schema.sql` won't retroactively alter existing tables (`CREATE TABLE` fails
if the table exists) - apply these two statements once instead of recreating the DB:

```sql
ALTER TABLE users ADD COLUMN data_processing_consent BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE anomalies DROP CONSTRAINT anomalies_transaction_id_fkey;
ALTER TABLE anomalies ADD CONSTRAINT anomalies_transaction_id_fkey
  FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE CASCADE;
```

If you already have a local database from before the user-profile fields were added
(phone/address/monthly income), apply this once too:

```sql
ALTER TABLE users ADD COLUMN phone VARCHAR(30);
ALTER TABLE users ADD COLUMN address VARCHAR(255);
ALTER TABLE users ADD COLUMN monthly_income NUMERIC(12, 2);
```

If you already have a local database from before `categories.name` and
`budgets(user_id, category_id, period_month)` became unique (needed to stop
duplicate categories/budgets - see `routers/budgets.py`), dedupe first, then
add the constraints:

```sql
-- Merge any existing duplicate category names into one row each.
WITH canonical AS (
  SELECT name, MIN(category_id) AS keep_id FROM categories GROUP BY name
)
UPDATE transactions t SET category_id = c.keep_id
FROM categories dup JOIN canonical c ON c.name = dup.name
WHERE t.category_id = dup.category_id AND dup.category_id <> c.keep_id;
-- (repeat the UPDATE above for budgets.category_id and categories.parent_category)
DELETE FROM categories WHERE category_id NOT IN (SELECT MIN(category_id) FROM categories GROUP BY name);

-- Drop any duplicate (user_id, category_id, period_month) budget rows, keeping the oldest.
DELETE FROM budgets b USING budgets b2
WHERE b.user_id = b2.user_id AND b.category_id = b2.category_id
  AND b.period_month = b2.period_month AND b.budget_id > b2.budget_id;

ALTER TABLE categories ADD CONSTRAINT categories_name_key UNIQUE (name);
ALTER TABLE budgets ADD CONSTRAINT budgets_user_category_month_key UNIQUE (user_id, category_id, period_month);
```

If you already have a local database from before chat message rating
(thumbs up/down) was added:

```sql
ALTER TABLE chat_messages ADD COLUMN rating VARCHAR(10);
```

If you already have a local database from before the AI Preferences toggle
and the receipts cascade fix (disconnecting a bank account with any
receipt-scanned transactions used to fail with a foreign-key error):

```sql
ALTER TABLE users ADD COLUMN ai_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE receipts DROP CONSTRAINT receipts_transaction_id_fkey;
ALTER TABLE receipts ADD CONSTRAINT receipts_transaction_id_fkey
  FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE CASCADE;
```

If you already have a local database from before the bank-link flow started
collecting an editable account number/type (the "Select an account" step):

```sql
ALTER TABLE bank_accounts ADD COLUMN account_number_display VARCHAR(50);
```

## 2. Configure environment

```bash
cp .env.example .env
# then edit .env with your local Postgres host/port/user/password/db name
# and a real JWT_SECRET_KEY (see the comment in .env.example)
```

`.env` is gitignored and must never be committed.

## 3. Install dependencies and run

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

The app starts on http://127.0.0.1:8000 - interactive docs at `/docs`, health check
at `/health`.

## Routes

- `POST /auth/register`, `POST /auth/login`, `GET /users/me` - implemented (bcrypt
  password hashing, JWT bearer auth).
- `POST /link-account`, `POST /link-account/callback` - mounted from
  [`backend/expense-ocr/link_account_api.py`](../expense-ocr/link_account_api.py).
- `/transactions`, `/budgets`, `/forecasts`, `/receipts`, `/chat`, `/savings`,
  `/settings` - empty TODO-commented router stubs for later phases.
