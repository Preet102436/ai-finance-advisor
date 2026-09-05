"""GET /users/me - protected route, returns the authenticated user.
DELETE /users/me - deletes the user and all their linked data, per the
proposal's GDPR/Privacy Act commitment."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import User
from schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deletes the user row; every other table (bank_accounts, transactions,
    receipts, budgets, forecasts, anomalies, chat_messages) cascades via the
    ON DELETE CASCADE foreign keys defined in db/schema.sql."""
    db.delete(current_user)
    db.commit()
