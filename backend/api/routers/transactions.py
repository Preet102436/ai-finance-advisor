"""Stub router for /transactions - not implemented yet.

TODO:
- GET    /transactions            list current user's transactions (filter by date/category/account)
- GET    /transactions/{id}       fetch a single transaction
- POST   /transactions            create a manual transaction (source='manual')
- PUT    /transactions/{id}       edit a transaction (e.g. recategorise)
- DELETE /transactions/{id}       remove a transaction
"""

from fastapi import APIRouter

router = APIRouter(prefix="/transactions", tags=["transactions"])
