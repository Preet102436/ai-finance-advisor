-- AI-Powered Personal Finance Advisor
-- Idempotent schema updates: brings an EXISTING database up to date with
-- db/schema.sql. Safe to run any number of times on any database state -
-- every statement is a no-op if the column is already there, and nothing
-- here ever drops or rewrites existing data.
--
-- Why this file exists: setup-db.ps1 only loads db/schema.sql (CREATE
-- TABLE) the very first time, when the `users` table doesn't exist yet. A
-- teammate who set up their database against an older version of this
-- project keeps that older table shape forever - CREATE TABLE never
-- revisits a table that already exists. This file adds back any columns
-- the schema has gained since, so `INSTALL.bat` stays a one-click fix for
-- "column ... does not exist" errors instead of requiring a manual DROP
-- DATABASE.

ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(30);
ALTER TABLE users ADD COLUMN IF NOT EXISTS date_of_birth DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS location VARCHAR(150);
ALTER TABLE users ADD COLUMN IF NOT EXISTS data_processing_consent BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE bank_accounts ADD COLUMN IF NOT EXISTS account_type VARCHAR(50);
ALTER TABLE bank_accounts ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'AUD';

ALTER TABLE transactions ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'bank_sync';

ALTER TABLE receipts ADD COLUMN IF NOT EXISTS ocr_raw_text TEXT;
ALTER TABLE receipts ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP;

ALTER TABLE budgets ADD COLUMN IF NOT EXISTS generated_by VARCHAR(20) NOT NULL DEFAULT 'ai_engine';

ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS lower_bound NUMERIC(12,2);
ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS upper_bound NUMERIC(12,2);
ALTER TABLE forecasts ADD COLUMN IF NOT EXISTS model_version VARCHAR(50);

ALTER TABLE anomalies ADD COLUMN IF NOT EXISTS reason VARCHAR(255);

ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS retrieved_context TEXT;
