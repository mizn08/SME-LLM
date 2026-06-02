from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile
from app.schemas import QuoteRequest, QuoteResponse
from app.services import quote_service

router = APIRouter(tags=["v6-quote"])


@router.post("/quote/generate", response_model=QuoteResponse)
def generate_quote(payload: QuoteRequest, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == payload.sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    try:
        return QuoteResponse(**quote_service.build_quote(db, payload))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
