from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile
from app.schemas import GoalCreate, GoalOut, GoalProgressUpdate
from app.services import goal_service

router = APIRouter(tags=["goals"])


@router.get("/sme/{sme_id}/goals", response_model=list[GoalOut])
def list_goals(sme_id: int, db: Session = Depends(get_db)):
    return goal_service.list_goals(db, sme_id)


@router.post("/goals", response_model=GoalOut)
def create_goal(payload: GoalCreate, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == payload.sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return goal_service.create_goal(db, payload)


@router.patch("/goals/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, payload: GoalProgressUpdate, db: Session = Depends(get_db)):
    out = goal_service.update_progress(db, goal_id, payload.current_amount_rm)
    if not out:
        raise HTTPException(404, "Goal not found")
    return out
