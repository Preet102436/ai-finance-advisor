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
