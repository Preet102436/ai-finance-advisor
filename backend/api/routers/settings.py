"""GET/PUT /settings - the current user's data-processing consent flag (GDPR/
Privacy Act commitment) and AI preference (whether chat/receipt-scanning use
the LLM at all, vs. heuristics-only).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import User
from schemas import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings(current_user: User = Depends(get_current_user)):
    return SettingsOut(
        data_processing_consent=current_user.data_processing_consent,
        ai_enabled=current_user.ai_enabled,
    )


@router.put("", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.data_processing_consent is not None:
        current_user.data_processing_consent = payload.data_processing_consent
    if payload.ai_enabled is not None:
        current_user.ai_enabled = payload.ai_enabled
    db.commit()
    db.refresh(current_user)
    return SettingsOut(
        data_processing_consent=current_user.data_processing_consent,
        ai_enabled=current_user.ai_enabled,
    )
