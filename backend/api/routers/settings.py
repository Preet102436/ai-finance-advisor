"""GET/PUT /settings - the current user's data-processing consent flag,
per the proposal's GDPR/Privacy Act commitment.

TODO (not implemented yet):
- account/notification preferences beyond consent (currency, alert thresholds)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import User
from schemas import ConsentOut, ConsentUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=ConsentOut)
def get_settings(current_user: User = Depends(get_current_user)):
    return ConsentOut(data_processing_consent=current_user.data_processing_consent)


@router.put("", response_model=ConsentOut)
def update_settings(
    payload: ConsentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.data_processing_consent = payload.data_processing_consent
    db.commit()
    db.refresh(current_user)
    return ConsentOut(data_processing_consent=current_user.data_processing_consent)
