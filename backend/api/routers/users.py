"""GET /users/me - protected route, returns the authenticated user.
PATCH /users/me - updates the current user's editable profile fields
(full name, phone, date of birth, location).
PUT /users/me/password - changes the current user's password.
DELETE /users/me - deletes the user and all their linked data, per the
proposal's GDPR/Privacy Act commitment."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import User
from schemas import PasswordChange, UserOut, UserProfileUpdate
from security import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_current_user(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Only updates fields the client actually sent, so a client can PATCH
    a single field (e.g. just location) without clobbering the others."""
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()


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
