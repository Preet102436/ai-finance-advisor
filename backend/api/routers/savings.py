"""Stub router for /savings - not implemented yet.

TODO:
- GET /savings/goals          list current user's savings goals
- POST /savings/goals          create a savings goal
- GET /savings/suggestions     AI-generated savings suggestions based on spending patterns
"""

from fastapi import APIRouter

router = APIRouter(prefix="/savings", tags=["savings"])
