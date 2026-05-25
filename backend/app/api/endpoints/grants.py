from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import grant_eligibility_service

router = APIRouter(tags=["grants"])


class GrantEligibilityRequest(BaseModel):
    sme_id: int | None = None
    bumiputera: bool = False
    revenue_rm: float = Field(default=0, ge=0)
    sector: str = ""
    ssm_registered: bool = True
    tech_focus: bool = False
    export_intent: bool = False
    veteran: bool = False


class GrantMatchOut(BaseModel):
    scheme_id: int
    scheme_name: str
    agency: str
    aid_type: str
    max_amount_rm: float | None
    match_reasons: list[str]
    priority: int


class GrantEligibilityResponse(BaseModel):
    matches: list[GrantMatchOut]
    total: int


@router.post("/grants/eligibility", response_model=GrantEligibilityResponse)
def grant_eligibility(payload: GrantEligibilityRequest, db: Session = Depends(get_db)):
    rows = grant_eligibility_service.match_grants(
        db,
        sme_id=payload.sme_id,
        bumiputera=payload.bumiputera,
        revenue_rm=payload.revenue_rm,
        sector=payload.sector,
        ssm_registered=payload.ssm_registered,
        tech_focus=payload.tech_focus,
        export_intent=payload.export_intent,
        veteran=payload.veteran,
    )
    return GrantEligibilityResponse(
        matches=[GrantMatchOut(**r) for r in rows],
        total=len(rows),
    )


@router.get("/grants/eligibility/{sme_id}", response_model=GrantEligibilityResponse)
def grant_eligibility_for_sme(sme_id: int, db: Session = Depends(get_db)):
    rows = grant_eligibility_service.match_grants(db, sme_id=sme_id)
    return GrantEligibilityResponse(
        matches=[GrantMatchOut(**r) for r in rows],
        total=len(rows),
    )
