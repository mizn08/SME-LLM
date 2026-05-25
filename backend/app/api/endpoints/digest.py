from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile
from app.schemas import DigestResponse
from app.services import digest_service

router = APIRouter(tags=["digest"])


@router.get("/sme/{sme_id}/digest", response_model=DigestResponse)
def get_digest(sme_id: int, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return digest_service.get_weekly_digest(db, sme_id)
