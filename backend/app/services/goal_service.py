"""SME financial goal tracking."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.goal import FinancialGoal
from app.schemas import GoalCreate, GoalOut


def list_goals(db: Session, sme_id: int) -> list[GoalOut]:
    rows = db.query(FinancialGoal).filter(FinancialGoal.sme_id == sme_id).order_by(FinancialGoal.id).all()
    return [_to_out(r) for r in rows]


def create_goal(db: Session, payload: GoalCreate) -> GoalOut:
    row = FinancialGoal(
        sme_id=payload.sme_id,
        title=payload.title,
        target_amount_rm=payload.target_amount_rm,
        current_amount_rm=payload.current_amount_rm,
        deadline=payload.deadline,
        category=payload.category,
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


def update_progress(db: Session, goal_id: int, current_amount_rm: float) -> GoalOut | None:
    row = db.query(FinancialGoal).filter(FinancialGoal.id == goal_id).first()
    if not row:
        return None
    row.current_amount_rm = current_amount_rm
    if current_amount_rm >= row.target_amount_rm:
        row.status = "completed"
    db.commit()
    db.refresh(row)
    return _to_out(row)


def _to_out(row: FinancialGoal) -> GoalOut:
    progress = min(100.0, (row.current_amount_rm / row.target_amount_rm * 100) if row.target_amount_rm else 0)
    return GoalOut(
        id=row.id,
        sme_id=row.sme_id,
        title=row.title,
        target_amount_rm=row.target_amount_rm,
        current_amount_rm=row.current_amount_rm,
        deadline=row.deadline,
        category=row.category,
        status=row.status,
        progress_pct=round(progress, 1),
    )
