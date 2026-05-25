"""Seed demo financial goals for each SME."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.goal import FinancialGoal
from app.models.sme import SMEProfile


def seed_demo_goals(db: Session) -> int:
    smes = db.query(SMEProfile).all()
    if not smes:
        return 0
    existing = db.query(FinancialGoal).count()
    if existing > 0:
        return 0
    templates = [
        ("Save RM50K for equipment", 50000, 12000, "equipment"),
        ("Reduce monthly burn 15%", 30000, 8000, "efficiency"),
        ("Build 3-month cash reserve", 90000, 45000, "savings"),
    ]
    count = 0
    for sme in smes:
        for title, target, current, cat in templates[:2]:
            db.add(
                FinancialGoal(
                    sme_id=sme.id,
                    title=title,
                    target_amount_rm=target,
                    current_amount_rm=current,
                    category=cat,
                    status="active",
                )
            )
            count += 1
    db.commit()
    return count
