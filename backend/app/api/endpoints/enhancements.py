"""Bundled enhancement endpoints: fraud, credit, banking, workflows, marketplace, bots, reports."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile
from app.services import (
    bot_service,
    credit_score_service,
    fraud_service,
    marketplace_service,
    open_banking_service,
    report_pdf_service,
    workflow_service,
)

router = APIRouter(tags=["enhancements"])


class BankConnectRequest(BaseModel):
    sme_id: int
    bank_id: str


class WorkflowStartRequest(BaseModel):
    sme_id: int
    workflow_id: str


class WorkflowAdvanceRequest(BaseModel):
    sme_id: int
    workflow_id: str
    step_index: int = 0
    approved: bool = True


class BotMessageRequest(BaseModel):
    sme_id: int
    text: str = Field(min_length=1)
    channel: str = "whatsapp"
    persona: str | None = None
    language: str | None = None


class CreditSimRequest(BaseModel):
    sme_id: int
    scenario: str = "bnpl_purchase"


class MarketplaceTrackRequest(BaseModel):
    sme_id: int
    provider_id: str
    status: str = "submitted"


@router.get("/sme/{sme_id}/fraud-scan")
def fraud_scan(sme_id: int, db: Session = Depends(get_db)):
    return fraud_service.scan_transactions(db, sme_id)


@router.post("/credit/simulate")
def credit_simulate(payload: CreditSimRequest, db: Session = Depends(get_db)):
    return credit_score_service.simulate(db, payload.sme_id, payload.scenario)


@router.get("/open-banking/banks")
def list_banks():
    return {"banks": open_banking_service.list_banks()}


@router.post("/connect-bank")
def connect_bank(payload: BankConnectRequest):
    return open_banking_service.connect_bank(payload.sme_id, payload.bank_id)


@router.get("/sme/{sme_id}/bank-connections")
def bank_connections(sme_id: int):
    return {"sme_id": sme_id, "connections": open_banking_service.get_connections(sme_id)}


@router.post("/sme/{sme_id}/bank-sync")
def bank_sync(sme_id: int):
    return open_banking_service.sync_transactions(sme_id)


@router.get("/workflows")
def list_workflows():
    return {
        "workflows": [
            {"id": "tekun_grant", "name": "TEKUN grant pre-qualification"},
            {"id": "auto_bnpl_rules", "name": "Auto-BNPL rules"},
        ]
    }


@router.post("/workflows/start")
def start_workflow(payload: WorkflowStartRequest, db: Session = Depends(get_db)):
    return workflow_service.start_workflow(db, payload.sme_id, payload.workflow_id)


@router.post("/workflows/advance")
def advance_workflow(payload: WorkflowAdvanceRequest, db: Session = Depends(get_db)):
    return workflow_service.advance_workflow(
        db, payload.sme_id, payload.workflow_id, payload.step_index, payload.approved
    )


@router.post("/marketplace/track")
def marketplace_track(payload: MarketplaceTrackRequest):
    return marketplace_service.track_application(
        payload.sme_id, payload.provider_id, payload.status
    )


@router.post("/bots/message")
def bot_message(payload: BotMessageRequest, db: Session = Depends(get_db)):
    return bot_service.handle_message(
        db,
        payload.sme_id,
        payload.text,
        payload.channel,
        payload.persona,
        payload.language,
    )


@router.get("/sme/{sme_id}/report/{audience}")
def audience_report(sme_id: int, audience: str, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    if audience not in ("bank", "board", "tax"):
        raise HTTPException(400, "audience must be bank | board | tax")
    return report_pdf_service.build_report(db, sme_id, audience)
