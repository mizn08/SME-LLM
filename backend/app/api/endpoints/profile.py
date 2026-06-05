from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile

router = APIRouter(tags=["profile"])


class OnboardRequest(BaseModel):
    sme_id: int
    sector: str = Field(min_length=1, max_length=128)
    revenue_rm: float = Field(gt=0)
    employee_count: int = Field(ge=1, le=5000)
    sst_registered: bool = False
    cash_reserve_months: float = Field(ge=0, le=24)
    bumiputera: bool = False
    tech_focus: bool = False


class OnboardResponse(BaseModel):
    sme_id: int
    business_name: str
    industry: str
    annual_revenue_rm: float
    employee_count: int
    readiness_hint: str
    message: str


class SmeProfileSummary(BaseModel):
    sme_id: int
    business_name: str
    industry: str
    annual_revenue_rm: float
    employee_count: int
    bumiputera: bool


@router.get("/sme/{sme_id}/profile", response_model=SmeProfileSummary)
def get_sme_profile(sme_id: int, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return SmeProfileSummary(
        sme_id=sme.id,
        business_name=sme.business_name,
        industry=sme.industry,
        annual_revenue_rm=sme.annual_revenue_rm,
        employee_count=sme.employee_count,
        bumiputera=sme.bumiputera_flag,
    )


@router.post("/profile/onboard", response_model=OnboardResponse)
def onboard_profile(payload: OnboardRequest, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == payload.sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    sme.industry = payload.sector
    sme.annual_revenue_rm = payload.revenue_rm
    sme.employee_count = payload.employee_count
    sme.bumiputera_flag = payload.bumiputera
    sme.notes = (
        f"SST registered: {payload.sst_registered}; "
        f"Cash reserve months: {payload.cash_reserve_months}; "
        f"Tech focus: {payload.tech_focus}"
    )
    db.commit()
    db.refresh(sme)
    hint = (
        "Strong cash buffer — explore grants and BNPL for growth purchases."
        if payload.cash_reserve_months >= 3
        else "Build toward 3–6 months cash reserves (BNM/SME Corp guidance)."
    )
    return OnboardResponse(
        sme_id=sme.id,
        business_name=sme.business_name,
        industry=sme.industry,
        annual_revenue_rm=sme.annual_revenue_rm,
        employee_count=sme.employee_count,
        readiness_hint=hint,
        message="Profile saved. Dashboard will use your SME data on next refresh.",
    )
