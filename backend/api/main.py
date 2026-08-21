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

# backend/expense-ocr uses a hyphen in its directory name, so it can't be
# imported as a normal dotted package - add it to sys.path instead so we can
# `import link_account_api` the same way its own README does.
EXPENSE_OCR_DIR = Path(__file__).resolve().parent.parent / "expense-ocr"
if str(EXPENSE_OCR_DIR) not in sys.path:
    sys.path.insert(0, str(EXPENSE_OCR_DIR))

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
