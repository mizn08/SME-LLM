from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile
from app.schemas import NudgeResponse
from app.services import firebase_client, nudge_service, push_service

router = APIRouter(tags=["notifications"])


class DeviceRegisterRequest(BaseModel):
    sme_id: int
    fcm_token: str = Field(min_length=8, max_length=512)
    platform: str = "fcm"


class TestPushRequest(BaseModel):
    sme_id: int
    title: str = "SME Advisor"
    body: str = "Test notification from SME Advisor"


@router.post("/notifications/register")
def register_device(payload: DeviceRegisterRequest, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == payload.sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return push_service.register_device(db, payload.sme_id, payload.fcm_token, payload.platform)


@router.post("/notifications/send")
def send_push_notifications(sme_id: int, db: Session = Depends(get_db)):
    """Send current nudges to all FCM devices for this SME."""
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return push_service.send_nudges_push(db, sme_id)


@router.post("/notifications/test")
def test_push(payload: TestPushRequest, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == payload.sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return push_service.send_test_push(db, payload.sme_id, payload.title, payload.body)


@router.get("/notifications/status")
def notification_status():
    return {
        "fcm_configured": firebase_client.is_configured(),
        "fcm_enabled": True,
    }


@router.get("/sme/{sme_id}/notifications/pending")
def pending_notifications(sme_id: int, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return {
        "sme_id": sme_id,
        "fcm_configured": firebase_client.is_configured(),
        "devices_registered": len(push_service.list_devices(db, sme_id)),
        "devices": push_service.list_devices(db, sme_id),
        "push_payloads": push_service.pending_push_payloads(db, sme_id),
    }


@router.get("/sme/{sme_id}/nudges", response_model=NudgeResponse)
def get_nudges(sme_id: int, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return NudgeResponse(sme_id=sme_id, nudges=nudge_service.get_nudges(db, sme_id))
