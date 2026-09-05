-- AI-Powered Personal Finance Advisor
-- Shared database schema (PostgreSQL)
-- Owner: Preetkumar Navinbhai Patel (Expense Tracking & OCR / backend architecture)

CREATE TABLE users (
    user_id         SERIAL PRIMARY KEY,
    full_name       VARCHAR(150) NOT NULL,
    email           VARCHAR(150) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    data_processing_consent BOOLEAN NOT NULL DEFAULT FALSE,  -- GDPR/Privacy Act consent flag
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE bank_accounts (
    account_id      SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    provider_name   VARCHAR(100) NOT NULL,        -- e.g. sandbox bank name
    external_ref    VARCHAR(255) NOT NULL,        -- token/ID from Open Banking sandbox
    account_type    VARCHAR(50),
    currency        VARCHAR(10) DEFAULT 'AUD',
    linked_at       TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE categories (
    category_id     SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    parent_category INTEGER REFERENCES categories(category_id)
);

CREATE TABLE transactions (
    transaction_id  SERIAL PRIMARY KEY,
    account_id      INTEGER NOT NULL REFERENCES bank_accounts(account_id) ON DELETE CASCADE,
    category_id     INTEGER REFERENCES categories(category_id),
    amount          NUMERIC(12,2) NOT NULL,
    description     VARCHAR(255),
    merchant        VARCHAR(150),
    txn_date        DATE NOT NULL,
    source          VARCHAR(20) NOT NULL DEFAULT 'bank_sync',  -- bank_sync | manual | receipt_ocr
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE receipts (
    receipt_id      SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    transaction_id  INTEGER REFERENCES transactions(transaction_id),
    image_path      VARCHAR(255) NOT NULL,
    ocr_raw_text    TEXT,
    processed_at    TIMESTAMP
);

CREATE TABLE budgets (
    budget_id       SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category_id     INTEGER REFERENCES categories(category_id),
    period_month    DATE NOT NULL,           -- first day of the budget month
    recommended_amount NUMERIC(12,2) NOT NULL,
    generated_by    VARCHAR(20) NOT NULL DEFAULT 'ai_engine',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE forecasts (
    forecast_id     SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    forecast_date   DATE NOT NULL,
    predicted_balance NUMERIC(12,2) NOT NULL,
    lower_bound     NUMERIC(12,2),
    upper_bound     NUMERIC(12,2),
    model_version   VARCHAR(50),
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE anomalies (
    anomaly_id      SERIAL PRIMARY KEY,
    transaction_id  INTEGER NOT NULL REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    anomaly_score   NUMERIC(6,4) NOT NULL,
    reason          VARCHAR(255),
    detected_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE chat_messages (
    message_id      SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,   -- user | assistant
    content         TEXT NOT NULL,
    retrieved_context TEXT,                 -- RAG context used for this reply, if any
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
