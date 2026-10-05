# AI-Powered Personal Finance Advisor

A **web application** that uses Generative AI to help users manage their personal
finances: automated expense tracking, AI-generated budgets, spending insights, savings
suggestions, and a financial chatbot, plus advanced features (predictive cash-flow
forecasting & anomaly detection, receipt OCR + AI categorisation, and a
Retrieval-Augmented Generation chatbot).

This is the COIT20273 capstone project (Term 2 2026).

## Team

| Member | Subsystem |
|---|---|
| Parth Patel (12281818) | Budgeting & Forecasting |
| Preetkumar Navinbhai Patel (12277687) | Expense Tracking & OCR, Database & Backend Architecture |
| Thiwanka Kaushalya Nagasanga (12288198) | Conversational Chatbot (RAG) & Savings Recommendation |

## Repository structure

```
ai-finance-advisor/
├── frontend/                      Web app frontend (React + Vite)
├── backend/
│   ├── api/                       The real backend (FastAPI app, routers, database, tests)
│   ├── budgeting-forecasting/     Parth: forecasting + anomaly detection logic
│   ├── expense-ocr/               Preetkumar: bank sync + receipt OCR logic
│   └── chatbot-savings/           Thiwanka: RAG chatbot + savings logic
├── db/
│   └── schema.sql                 Shared database schema
└── docs/
    ├── er-diagram.md
    ├── budgeting-forecasting-design.md
    ├── expense-ocr-design.md
    ├── chatbot-savings-design.md
    └── meeting-minutes.md
```

## Status

Fully integrated: a working FastAPI backend + PostgreSQL database + React frontend,
covering registration/login, bank account linking & syncing, receipt upload with OCR,
transaction browsing, AI-generated budgets, balance forecasting, anomaly detection,
savings suggestions, an AI chatbot, and account/privacy settings.

---

# How to run this project

This guide assumes **no prior setup on your machine** and explains every step in full,
including exactly what to type. It's written for Windows (the team's dev environment),
with notes for Mac/Linux where it differs. Follow the steps in order.

You need three pieces of software running at once to use the app:
1. **PostgreSQL** — the database (stores users, transactions, etc.)
2. **The backend** — a Python program that serves the API (the "brain")
3. **The frontend** — a web page you open in your browser (what you actually click around in)

## Step 1 — Install the required software

Install these one at a time. If you're not sure whether something is already
installed, just try the "check" command for it in a terminal — if it prints a
version number, it's already there and you can skip that install.

### 1a. Python (3.11 or 3.12 recommended)

Download from **https://www.python.org/downloads/** — get the latest **3.12** release
(3.11 also works and is what this project has been most tested against). During
installation on Windows, **tick the "Add python.exe to PATH" checkbox** on the first
install screen.

> **If you already have a different or newer Python version installed** (e.g. 3.13 or
> 3.14), don't uninstall it — just install 3.11 or 3.12 *alongside* it. Windows's Python
> Launcher (`py`) lets you pick which one to use per-command, which this guide uses
> throughout (`py -3.12 -m ...`) specifically so a newer default Python on your system
> never gets in the way. Very new Python versions (3.13+) can hit package installation
> problems because some dependencies don't have ready-made installers for them yet —
> that's exactly what 3.11/3.12 avoids.

Check it worked (open a new terminal/PowerShell window first):
```
py -0
```
This lists every Python version Windows knows about. Confirm `3.11` or `3.12` appears
in the list.

*(Mac/Linux: install via https://www.python.org/downloads/ or your package manager,
and use `python3.12` instead of `py -3.12 -m` in every command below.)*

### 1b. PostgreSQL (the database)

Download from **https://www.postgresql.org/download/windows/** and run the installer.
- When asked to set a password for the `postgres` user, pick one and **write it down** —
  you'll need it in Step 2.
- Keep the default port (`5432`).
- You can leave "Stack Builder" unchecked at the end.

Check it worked:
```
psql --version
```

### 1c. Node.js (for the frontend)

Download the **LTS** version from **https://nodejs.org/** and run the installer
(defaults are fine).

Check it worked:
```
node --version
npm --version
```

### 1d. Tesseract OCR (for reading receipt photos)

Download the Windows installer from
**https://github.com/UB-Mannheim/tesseract/wiki** (the standard Windows build) and
run it with default settings (default install location:
`C:\Program Files\Tesseract-OCR`).

You don't need to add it to PATH — Step 3 below sets an environment variable that
points straight at it, which is more reliable on Windows.

### 1e. Git (only if you don't already have the project folder)

Download from **https://git-scm.com/downloads** if you need to clone the repository.
If you already have the `ai-finance-advisor` folder on your computer, skip this.

---

## Step 2 — Set up the database

Open a terminal in the project's root folder (`ai-finance-advisor`) and run:

```
createdb -U postgres finance_advisor
```
This will ask for the PostgreSQL password you set in Step 1b. It creates an empty
database called `finance_advisor`.

Now load the project's table structure into it:
```
psql -U postgres -d finance_advisor -f db/schema.sql
```

---

## Step 3 — Set up and run the backend

Open a terminal **in the `backend/api` folder**:
```
cd backend/api
```

Install the Python packages this project needs (replace `3.12` with `3.11` if that's
the one you installed):
```
py -3.12 -m pip install -r requirements.txt --upgrade
```
> The `--upgrade` flag matters: without it, if you already had an older copy of a
> package like SQLAlchemy installed from something unrelated, pip will leave it alone
> instead of updating it to the version this project needs.

Create your personal config file by copying the example:
```
copy .env.example .env
```
Open the new `backend/api/.env` file in any text editor and fill in:
- `DB_USER` / `DB_PASSWORD` — your PostgreSQL username/password from Step 1b
  (username is `postgres` unless you changed it)
- `JWT_SECRET_KEY` — replace the placeholder with a real random value. Generate one with:
  ```
  py -3.12 -c "import secrets; print(secrets.token_urlsafe(48))"
  ```
  Copy the output into the `.env` file.
- `TESSERACT_CMD` — uncomment this line (remove the leading `#`) and make sure the path
  matches where Tesseract installed in Step 1d. Default is already correct:
  `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`
- `OPENAI_API_KEY` — **optional**. If you have an OpenAI API key, uncomment this line
  and paste it in — this turns on the AI chatbot and smarter receipt reading. Without
  it, the app still works fully, just with simpler fallback behaviour for those two
  features (see "What works without an OpenAI key" below).

Now start the backend:
```
py -3.12 -m uvicorn main:app --reload
```
If it worked, you'll see `Uvicorn running on http://127.0.0.1:8000`. **Leave this
terminal window open** — closing it stops the backend. You can check it's alive by
opening **http://localhost:8000/health** in a browser; it should show `{"status":"ok"}`.

---

## Step 4 — Set up and run the frontend

Open a **new, second terminal window** (keep the backend one running) and go to the
frontend folder:
```
cd frontend
```

Install its packages:
```
npm install
```

Create its config file:
```
copy .env.example .env
```
The defaults in this file are already correct as long as the backend is running on
`http://localhost:8000` (the default from Step 3) — no editing needed.

Start the frontend:
```
npm run dev
```
You'll see a message with a local address, normally **http://localhost:5173**.

---

## Step 5 — Use the app

Open **http://localhost:5173** in your browser. Then:

1. Click **Register**, fill in a name/email/password (8+ characters), submit.
2. You're now logged in, on the Dashboard.
3. Go to **Transactions** → click **Link bank account** → click **Sync bank account**.
   This connects a simulated/demo bank account and pulls in example transactions so
   there's real data to explore (this app doesn't connect to a real bank).
4. Try uploading a photo of a receipt under "Upload a receipt" — it'll read the total
   and guess a category.
5. Go to **Dashboard** to see AI-generated budgets, a balance forecast chart, spending
   by category, and any unusual transactions flagged.
6. Go to **Chat** and ask something like "How much did I spend on groceries?"
7. Go to **Settings** to see the data-processing consent toggle and account deletion.

---

## What works without an OpenAI key

The `OPENAI_API_KEY` setting in Step 3 is optional. Without it:
- **Chat** still answers, using a plain-language summary built directly from your real
  transactions, instead of an AI-written response.
- **Receipt upload** still reads totals and guesses categories, using a simpler
  keyword/pattern-matching method instead of AI, which works well for common,
  clearly-labelled receipts but is less flexible with unusual formats.

Nothing breaks either way — the AI key just makes those two features smarter.

---

## Running the automated tests

To check everything is working correctly end-to-end, from `backend/api`:
```
py -3.12 -m pytest -q
```
A healthy run ends with `13 passed`. This exercises the real app against your real
database — register, login, link a bank account, sync, upload a receipt, chat,
generate budgets/forecasts/anomalies, change settings, and delete an account — and
checks every step worked and the database ended up in the right state.

---

## Troubleshooting

**`ImportError: cannot import name 'DeclarativeBase' from 'sqlalchemy.orm'`**
You have more than one Python version installed, and the command you ran picked a
different one than the one you installed packages into (the old version doesn't have
the newer SQLAlchemy). Always use `py -3.12 -m` (or whichever version you set up)
in front of `pip`, `uvicorn`, and `pytest` commands — never run bare `python`,
`pip`, `uvicorn`, or `pytest` in this project, since those can silently resolve to a
different, unconfigured Python install. Run `py -0` to see which versions Windows
knows about.

**`TesseractNotFoundError: tesseract is not installed or it's not in your PATH`**
Tesseract is installed but the backend doesn't know where. Make sure
`TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe` is uncommented in
`backend/api/.env` (no `#` at the start of the line), matching wherever you actually
installed it, then fully stop (Ctrl+C) and restart the backend — `.env` is only
read when the backend starts, not picked up automatically while it's running.

**Backend won't connect to the database / "password authentication failed"**
Double-check `DB_USER` and `DB_PASSWORD` in `backend/api/.env` match what you set
when installing PostgreSQL in Step 1b.

**Frontend loads but every page shows an error / can't reach the backend**
Make sure the backend terminal (Step 3) is still running and shows no errors, and
that `frontend/.env`'s `VITE_API_BASE_URL` matches the address it's running on
(default `http://localhost:8000`).

**Receipt upload says "Could not find a total on this receipt"**
Use a clear, well-lit, non-blurry photo. Very unusual receipt layouts can still
trip up the fallback reader (see "What works without an OpenAI key" above) — an
OpenAI key makes this meaningfully more robust.

**Port already in use (`8000` or `5173`)**
Something else on your computer is already using that port. Either close whatever
that is, or run the backend on a different port with
`py -3.12 -m uvicorn main:app --reload --port 8001` (and update
`frontend/.env`'s `VITE_API_BASE_URL` to match).
