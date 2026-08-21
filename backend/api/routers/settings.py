"""Stub router for /settings - not implemented yet.

TODO:
- GET /settings                current user's account/notification preferences
- PUT /settings                 update preferences (e.g. currency, alert thresholds)
- DELETE /settings/account       delete the current user's account and data
"""

from fastapi import APIRouter

router = APIRouter(prefix="/settings", tags=["settings"])
