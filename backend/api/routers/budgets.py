"""Stub router for /budgets - not implemented yet.

TODO:
- GET  /budgets               list current user's budgets (optionally filter by period_month)
- POST /budgets                create/override a budget for a category+month
- GET  /budgets/recommended    AI-generated recommended budgets (generated_by='ai_engine')
"""

from fastapi import APIRouter

router = APIRouter(prefix="/budgets", tags=["budgets"])
