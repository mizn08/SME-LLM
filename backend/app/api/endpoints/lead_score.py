from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile
from app.schemas import LeadScoreResponse
from app.services import lead_score_service

router = APIRouter(tags=["lead-score"])


@router.get("/sme/{sme_id}/lead-scores", response_model=LeadScoreResponse)
def get_lead_scores(sme_id: int, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    scores = lead_score_service.compute_lead_scores(db, sme_id)
    return LeadScoreResponse(sme_id=sme_id, scores=scores)
