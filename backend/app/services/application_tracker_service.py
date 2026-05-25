"""CRUD for financing application tracker records."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.application_tracker import ApplicationTracker
from app.schemas import ApplicationCreateRequest, ApplicationTrackerItem, ApplicationUpdateRequest

VALID_STATUSES = {"draft", "submitted", "under_review", "approved", "rejected"}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def list_applications(db: Session, sme_id: int) -> list[ApplicationTrackerItem]:
    rows = (
        db.query(ApplicationTracker)
        .filter(ApplicationTracker.sme_id == sme_id)
        .order_by(ApplicationTracker.updated_at.desc())
        .all()
    )
    return [ApplicationTrackerItem.model_validate(r) for r in rows]


def create_application(db: Session, payload: ApplicationCreateRequest) -> ApplicationTrackerItem:
    row = ApplicationTracker(
        sme_id=payload.sme_id,
        product_name=payload.product_name,
        product_type=payload.product_type,
        status="draft",
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ApplicationTrackerItem.model_validate(row)


def update_application(
    db: Session, app_id: int, payload: ApplicationUpdateRequest
) -> ApplicationTrackerItem | None:
    row = db.query(ApplicationTracker).filter(ApplicationTracker.id == app_id).first()
    if not row:
        return None
    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {payload.status}")
        row.status = payload.status
    if payload.notes is not None:
        row.notes = payload.notes
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return ApplicationTrackerItem.model_validate(row)
