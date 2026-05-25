from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile
from app.schemas import BenchmarkResponse
from app.services import benchmark_service

router = APIRouter(tags=["benchmark"])


@router.get("/sme/{sme_id}/benchmark", response_model=BenchmarkResponse)
def get_benchmark(sme_id: int, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return benchmark_service.get_benchmark(db, sme_id)
