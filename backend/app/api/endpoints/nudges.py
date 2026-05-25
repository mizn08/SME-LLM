from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile
from app.schemas import NudgeResponse
from app.services import nudge_service

router = APIRouter(tags=["nudges"])


@router.get("/sme/{sme_id}/nudges", response_model=NudgeResponse)
def get_nudges(sme_id: int, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    nudges = nudge_service.get_nudges(db, sme_id)
    return NudgeResponse(sme_id=sme_id, nudges=nudges)
