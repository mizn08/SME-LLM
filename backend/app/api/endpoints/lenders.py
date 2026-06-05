from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile
from app.schemas import LenderDirectoryResponse, MatchedLenderResponse
from app.services import lender_service

router = APIRouter(tags=["lenders"])


@router.get("/lenders", response_model=LenderDirectoryResponse)
def list_lenders(
    islamic_only: bool = Query(False),
    q: str | None = Query(None, description="Search name, grant, BNPL, MADANI, MDEC, etc."),
    db: Session = Depends(get_db),
):
    lenders = lender_service.catalog_lenders(db, islamic_only=islamic_only)
    if q and q.strip():
        lenders = lender_service.search_lenders(lenders, q)
    return LenderDirectoryResponse(lenders=lenders, total=len(lenders))


@router.get("/sme/{sme_id}/lenders/matched", response_model=MatchedLenderResponse)
def matched_lenders(
    sme_id: int,
    islamic_only: bool = Query(False),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    matched = lender_service.matched_lenders(
        db, sme_id, islamic_only=islamic_only, query=q
    )
    return MatchedLenderResponse(sme_id=sme_id, matched=matched)
