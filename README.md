# AI-Powered Personal Finance Advisor

A **web application** that uses Generative AI to help users manage their personal
finances: expense tracking (bank sync, receipt OCR, and manual entry), AI-generated
budgets, spending insights, savings suggestions, a financial chatbot, predictive
cash-flow forecasting, and anomaly detection.

This is the COIT20273 capstone project (Term 2 2026).

> **Want to try the running app with minimal setup?** See
> [HOW-TO-RUN.txt](./HOW-TO-RUN.txt) - on Windows, run `INSTALL.bat` once, then
> double-click `START.bat` each time. Manual setup instructions (any OS) are
> below.

## Team

| Member | Subsystem |
|---|---|
| Parth Patel (12281818) | Budgeting & Forecasting |
| Preetkumar Navinbhai Patel (12277687) | Expense Tracking & OCR, Database & Backend Architecture |
| Thiwanka Kaushalya Nagasanga (12288198) | Conversational Chatbot (RAG) & Savings Recommendation |

## Status

Fully integrated web application - a FastAPI + PostgreSQL backend and a React
(Vite) frontend, with every subsystem below wired together behind real
authentication and a shared database. The project is also responsive down to
phone width (a hamburger-triggered slide-in sidebar below ~860px).

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, React Router |
| Backend | Python 3.11+, FastAPI, SQLAlchemy, JWT auth |
| Database | PostgreSQL 16 |
| AI / ML | RAG chatbot (optional OpenAI, rule-based fallback), forecasting (Prophet if installed, moving-average fallback), Tesseract OCR |
| Tooling | pytest |

## Features

- **Accounts** - register/login (JWT), profile, settings, account deletion
  (cascades every linked table).
- **Bank linking** - mocked Open Banking OAuth2-style flow (choose a bank,
  click through consent, pick an account) - no login form, nothing to type.
  Sync transactions, unlink/relink at any time. Manual transaction entry and
  CSV/Excel import both work with or without a linked bank account.
- **Transactions** - full CRUD (add, edit, delete, categorise) on every
  transaction, with filtering and CSV/Excel import.
- **Receipts** - photo upload with OCR (Tesseract) + category/total/merchant
  extraction, saved as a transaction (works with or without a linked bank).
- **Budgets** - AI-recommended monthly budgets per category from spending
  history, plus manual creation, increase/decrease/custom-amount editing,
  and deletion - all from the Dashboard's budget cards.
- **AI chat** - a Retrieval-Augmented Generation chatbot grounded in the
  user's real transactions/budgets; falls back to a rule-based reasoning
  engine with no API key required (works out of the box).
- **AI Insights** - pick a date range and get an AI-generated financial
  summary, category breakdown, anomaly/overspend flags with linked evidence
  transactions, and savings suggestions - exportable as CSV or PDF.
- **Forecasting** - predictive balance forecast (Prophet when available,
  moving-average fallback) with a confidence band.
- **Anomaly detection** - flags unusual transactions automatically.

## Repository structure

```
ai-finance-advisor/
├── frontend/                      # React (Vite) web app
│   └── src/
│       ├── pages/                 # Login, Register, Dashboard, Transactions,
│       │                          #   Chat, AI Insights, Profile, Settings
│       ├── components/            # Layout/nav, savings-suggestions
│       │                          #   panel, financial summary cards, etc.
│       └── lib/                   # API client + one module per feature area
├── backend/
│   ├── api/                      # FastAPI app (main.py, routers/, models.py, schemas.py)
│   │   └── routers/               # auth, users, bank, transactions, receipts,
│   │                               #   budgets, savings, chat, insights, forecasts,
│   │                               #   anomalies, settings
│   ├── budgeting-forecasting/      # Forecasting/anomaly-detection prototype + design notes
│   ├── expense-ocr/                # Bank-link mock OAuth2 + OCR prototype, mounted
│   │                              #   into backend/api/main.py
│   └── chatbot-savings/            # RAG chatbot + savings-suggestions logic, imported
│                                   #   by backend/api/routers/chat.py and savings.py
├── db/
│   └── schema.sql                 # Full database schema
├── sample-data/                   # Sample CSV import + OCR test receipts
├── docs/
│   ├── er-diagram.md
│   ├── budgeting-forecasting-design.md
│   ├── expense-ocr-design.md
│   ├── chatbot-savings-design.md
│   └── meeting-minutes.md
├── INSTALL.bat / START.bat        # One-click Windows install and start
├── setup-db.ps1                   # Windows database setup (used by INSTALL.bat)
├── TUNNEL.bat                     # Optional: share the running app over the internet
└── HOW-TO-RUN.txt                 # Step-by-step Windows guide
```

## Running it

### Easiest on Windows

**New to this? Start here - one-time setup, about 10 minutes:**

1. **Python 3.11 or newer** - https://www.python.org/downloads/
   During install, tick "Add python.exe to PATH". (`pip`, Python's package
   installer, is bundled with Python - there's nothing extra to install for it.)
2. **Node.js (LTS version)** - https://nodejs.org/
3. **PostgreSQL 16 or 17** - https://www.postgresql.org/download/windows/
   When the installer asks for a password, enter `postgres` and keep the
   default port `5432`.
4. *(Optional)* **Tesseract OCR** - only needed for receipt photo upload -
   https://github.com/UB-Mannheim/tesseract/wiki - install to the default
   folder `C:\Program Files\Tesseract-OCR\`.

**Then, every time you want to run the app:**

Right-click `INSTALL.bat` and choose "Run as administrator" the first time -
it installs the Python/Node packages from step 1-2 above and sets up the
database for you, so you never need to type a `pip`, `npm`, or `psql`
command yourself. After that, just double-click `START.bat` each time - it
opens the backend, the frontend, and your browser at `http://localhost:5173`.
`TUNNEL.bat` optionally shares that running app over the internet (e.g. to
try it on a phone).

**If something goes wrong:**

| Problem | Fix |
|---|---|
| "Python not found" / "Node.js not found" | Install it (step 1 or 2 above), close the window, run `INSTALL.bat` again. |
| "Password reset failed" during install | Right-click `INSTALL.bat` > Run as administrator. |
| "Failed to fetch" on login/register | The Backend window isn't running or shows an error - close both windows and double-click `START.bat` again. If it says "password authentication failed", run `INSTALL.bat` again as administrator. |
| Blank page / can't connect right after `START.bat` | Wait a few seconds and refresh `http://localhost:5173` - the servers are still starting up. |
| Port 8000 or 5173 already in use | An old copy is still running - close its windows, or restart your PC. |
| Backend window shows `column ... does not exist` / register fails with a 500 or "Failed to fetch" | Your local database is from an older version of this project. Close the Backend/Frontend windows and right-click `INSTALL.bat` > Run as administrator again - it now patches an existing database up to the current schema automatically (see `db/schema_updates.sql`), no data lost. |
| Receipt upload says Tesseract not found | Install Tesseract (step 4 above), or add `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe` to `backend\api\.env`. |
| `'pytest' is not recognized` / `'uvicorn' is not recognized` | Use `python -m pytest` or `python -m uvicorn main:app --reload` instead - pip installed them, but their standalone `.exe` isn't always on PATH. `python -m <tool>` always works since `python` itself already does. |

### Manual setup (Windows, Mac, or Linux)

Prerequisites: PostgreSQL 16, Python 3.11+ (`pip` comes bundled with it, no
separate install needed), Node.js 18+.

**1. Database**

```bash
psql -h localhost -U postgres -c "CREATE DATABASE finance_advisor;"
psql -h localhost -U postgres -d finance_advisor -f db/schema.sql
```

**2. Backend**

```bash
cd backend/api
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1   |   Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit DB_PASSWORD / JWT_SECRET_KEY
uvicorn main:app --reload
```

`.env` options (see `.env.example` for the full list with comments):
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - your local Postgres
- `JWT_SECRET_KEY` - generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `TESSERACT_CMD` - only needed if `tesseract` isn't already on your system PATH (common on Windows)
- `OPENAI_API_KEY` - optional; chat and receipt category/total extraction both have
  working fallbacks without it

**3. Frontend**

```bash
cd frontend
npm install
npm run dev   # /api calls are proxied to the backend on :8000
```

Open http://localhost:5173, click Register, and try it out.

## Testing

```bash
cd backend/api
python -m pytest
```

The suite registers/logs in a fresh test user for each test, so it needs a
running Postgres database (same `.env` as above) - it isn't mocked.

## Notes / known limitations

- The bank-link flow is a mocked Open Banking sandbox - click "Link a bank
  account", choose the sandbox demo bank, and click through the consent
  screens. There's no login form and nothing to type; swapping in a real
  provider is future work, not part of this assessment's scope.
- `OPENAI_API_KEY` is optional everywhere it's used; omitting it degrades
  gracefully to rule-based logic rather than failing.
- This setup is for local use/demonstration - the JWT secret and DB password
  are development placeholders, not production secrets.
