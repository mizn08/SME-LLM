from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import GrantChecklistResponse
from app.services import grant_checklist_service

router = APIRouter(tags=["grant-checklist"])


@router.get("/grants/{grant_id}/checklist", response_model=GrantChecklistResponse)
def grant_checklist(grant_id: int, db: Session = Depends(get_db)):
    result = grant_checklist_service.get_checklist(db, grant_id)
    if not result:
        raise HTTPException(404, "Grant scheme not found")
    return result
