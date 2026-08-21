"""Stub router for /forecasts - not implemented yet.

TODO:
- GET /forecasts            list current user's balance forecasts
- GET /forecasts/latest      most recent forecast (predicted_balance, lower/upper_bound)
- POST /forecasts/generate   trigger the forecasting model for the current user
"""

from fastapi import APIRouter

router = APIRouter(prefix="/forecasts", tags=["forecasts"])
