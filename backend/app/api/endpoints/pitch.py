from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile
from app.schemas import PitchRequest, PitchResponse
from app.services import pitch_service

router = APIRouter(tags=["pitch"])


@router.post("/sme/{sme_id}/pitch", response_model=PitchResponse)
def generate_pitch(sme_id: int, body: PitchRequest, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    letter = pitch_service.generate_pitch(db, sme_id, body.lang, body.tone)
    return PitchResponse(sme_id=sme_id, lang=body.lang, tone=body.tone, letter=letter)
