from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile
from app.schemas import AgentAdviseRequest, AgentAdviseResponse, AgentInsight
from app.services import agent_orchestrator

router = APIRouter(tags=["v2-agents"])


@router.post("/agent/advise", response_model=AgentAdviseResponse)
def agent_advise(payload: AgentAdviseRequest, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == payload.sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    advice = agent_orchestrator.run_multi_agent(
        db,
        payload.sme_id,
        payload.purchase_amount,
        payload.purchase_category,
        payload.goal or "best financing option",
    )
    return AgentAdviseResponse(
        sme_id=payload.sme_id,
        lead_agent=advice.lead_agent,
        summary=advice.summary,
        agents=[AgentInsight(name=a["name"], insight=a["insight"]) for a in advice.agents],
        recommendation=advice.recommendation,
        rag_snippet=advice.rag_snippet,
        agent_trace=advice.agent_trace,
    )
