# Entity-Relationship Diagram

**Owner:** Preetkumar Navinbhai Patel (Expense Tracking & OCR / Database & Backend Architecture)
**Status:** Refined from the initial proposal-stage data model. Adds `receipts`, `forecasts`,
`anomalies`, and `chat_messages` tables to support the advanced subsystems, and separates
`bank_accounts` from `users` to support multiple linked accounts per user.

```mermaid

erDiagram
    direction TB

    USERS {
        INTEGER user_id PK
        VARCHAR full_name
        VARCHAR email UK
        VARCHAR password_hash
        VARCHAR phone
        DATE date_of_birth
        VARCHAR location
        BOOLEAN data_processing_consent
        TIMESTAMP created_at
    }

    BANK_ACCOUNTS {
        INTEGER account_id PK
        INTEGER user_id FK
        VARCHAR provider_name
        VARCHAR external_ref
        VARCHAR account_type
        VARCHAR currency
        TIMESTAMP linked_at
    }

    CATEGORIES {
        INTEGER category_id PK
        VARCHAR name
        INTEGER parent_category FK
    }

    TRANSACTIONS {
        INTEGER transaction_id PK
        INTEGER account_id FK
        INTEGER category_id FK
        DECIMAL amount
        VARCHAR description
        VARCHAR merchant
        DATE txn_date
        VARCHAR source
        TIMESTAMP created_at
    }

    RECEIPTS {
        INTEGER receipt_id PK
        INTEGER user_id FK
        INTEGER transaction_id FK
        VARCHAR image_path
        TEXT ocr_raw_text
        TIMESTAMP processed_at
    }

    BUDGETS {
        INTEGER budget_id PK
        INTEGER user_id FK
        INTEGER category_id FK
        DATE period_month
        DECIMAL recommended_amount
        VARCHAR generated_by
        TIMESTAMP created_at
    }

    FORECASTS {
        INTEGER forecast_id PK
        INTEGER user_id FK
        DATE forecast_date
        DECIMAL predicted_balance
        DECIMAL lower_bound
        DECIMAL upper_bound
        VARCHAR model_version
        TIMESTAMP created_at
    }

    ANOMALIES {
        INTEGER anomaly_id PK
        INTEGER transaction_id FK
        DECIMAL anomaly_score
        VARCHAR reason
        TIMESTAMP detected_at
    }

    CHAT_MESSAGES {
        INTEGER message_id PK
        INTEGER user_id FK
        VARCHAR role
        TEXT content
        TEXT retrieved_context
        TIMESTAMP created_at
    }

    USERS ||--o{ BANK_ACCOUNTS : owns
    BANK_ACCOUNTS ||--o{ TRANSACTIONS : has

    CATEGORIES |o--o{ TRANSACTIONS : classifies
    CATEGORIES |o--o{ BUDGETS : "budgeted for"
    CATEGORIES |o--o{ CATEGORIES : "parent of"

    USERS ||--o{ BUDGETS : sets
    USERS ||--o{ RECEIPTS : uploads
    TRANSACTIONS |o--o{ RECEIPTS : "linked to"

    USERS ||--o{ FORECASTS : "forecast for"
    TRANSACTIONS ||--o{ ANOMALIES : "flagged as"
    USERS ||--o{ CHAT_MESSAGES : sends

```

## Notes on refinement since Assessment 1

- The original proposal described the data required only at a high level (user profile,
  transactions, receipts, budget/category metadata). This diagram formalises that into
  concrete tables and foreign-key relationships.
- `bank_accounts` is separated from `users` (1-to-many) so the system can support more
  than one linked sandbox account per user, matching the Open Banking-style scope in the
  proposal.
- `anomalies` references `transactions` directly rather than duplicating transaction data,
  keeping the anomaly-detection subsystem's output lightweight.
- `chat_messages.retrieved_context` stores the retrieved snippets used for a given chatbot
  reply, which supports the RAG design described in `chatbot-savings-design.md`.
