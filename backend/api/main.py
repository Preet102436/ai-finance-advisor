"""
AI-Powered Personal Finance Advisor - main FastAPI app.

Run locally (from backend/api/):
    pip install -r requirements.txt
    uvicorn main:app --reload

See README.md in this directory for local Postgres setup.
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# backend/expense-ocr and backend/budgeting-forecasting use hyphens in their
# directory names, so they can't be imported as normal dotted packages - add
# them to sys.path instead so we can import their modules directly, the same
# way each subsystem's own README does.
EXPENSE_OCR_DIR = Path(__file__).resolve().parent.parent / "expense-ocr"
if str(EXPENSE_OCR_DIR) not in sys.path:
    sys.path.insert(0, str(EXPENSE_OCR_DIR))

BUDGETING_FORECASTING_DIR = Path(__file__).resolve().parent.parent / "budgeting-forecasting"
if str(BUDGETING_FORECASTING_DIR) not in sys.path:
    sys.path.insert(0, str(BUDGETING_FORECASTING_DIR))

from link_account_api import router as link_account_router  # noqa: E402

from routers import (  # noqa: E402
    auth,
    budgets,
    chat,
    forecasts,
    receipts,
    savings,
    settings,
    transactions,
    users,
)

app = FastAPI(title="AI-Powered Personal Finance Advisor")

# Allow the local Vite dev server (frontend/) to call this API cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(forecasts.router)
app.include_router(receipts.router)
app.include_router(chat.router)
app.include_router(savings.router)
app.include_router(settings.router)
app.include_router(link_account_router)


@app.get("/health")
def health():
    return {"status": "ok"}
