from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import (
    ApplicationCreateRequest,
    ApplicationTrackerItem,
    ApplicationTrackerResponse,
    ApplicationUpdateRequest,
)
from app.services import application_tracker_service

router = APIRouter(tags=["application-tracker"])


@router.get("/sme/{sme_id}/applications", response_model=ApplicationTrackerResponse)
def list_applications(sme_id: int, db: Session = Depends(get_db)):
    apps = application_tracker_service.list_applications(db, sme_id)
    return ApplicationTrackerResponse(sme_id=sme_id, applications=apps)


@router.post("/applications", response_model=ApplicationTrackerItem)
def create_application(payload: ApplicationCreateRequest, db: Session = Depends(get_db)):
    return application_tracker_service.create_application(db, payload)


@router.patch("/applications/{app_id}", response_model=ApplicationTrackerItem)
def update_application(
    app_id: int, payload: ApplicationUpdateRequest, db: Session = Depends(get_db)
):
    try:
        row = application_tracker_service.update_application(db, app_id, payload)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not row:
        raise HTTPException(404, "Application not found")
    return row
