"""Agentic multi-step workflow stubs (LangGraph-style state machine)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services import grant_eligibility_service, rag_service


_WORKFLOWS = {
    "tekun_grant": {
        "name": "TEKUN grant pre-qualification",
        "steps": ["check_eligibility", "gather_documents", "draft_application", "await_approval"],
    },
    "auto_bnpl_rules": {
        "name": "Auto-BNPL rules",
        "steps": ["analyse_spending", "propose_rules", "confirm_with_user", "activate_rules"],
    },
}


def start_workflow(db: Session, sme_id: int, workflow_id: str) -> dict[str, Any]:
    wf = _WORKFLOWS.get(workflow_id)
    if not wf:
        return {"status": "error", "message": f"Unknown workflow: {workflow_id}"}
    return {
        "status": "started",
        "workflow_id": workflow_id,
        "name": wf["name"],
        "sme_id": sme_id,
        "current_step": wf["steps"][0],
        "steps": wf["steps"],
        "requires_approval": True,
    }


def advance_workflow(db: Session, sme_id: int, workflow_id: str, step_index: int, approved: bool) -> dict[str, Any]:
    wf = _WORKFLOWS.get(workflow_id)
    if not wf:
        return {"status": "error", "message": "Unknown workflow"}
    steps = wf["steps"]
    if step_index >= len(steps):
        return {"status": "completed", "workflow_id": workflow_id, "message": "Workflow finished"}
    if not approved:
        return {"status": "paused", "workflow_id": workflow_id, "step": steps[step_index], "message": "Awaiting user approval"}

    next_idx = step_index + 1
    result: dict[str, Any] = {
        "status": "in_progress" if next_idx < len(steps) else "completed",
        "workflow_id": workflow_id,
        "completed_step": steps[step_index],
        "next_step": steps[next_idx] if next_idx < len(steps) else None,
    }

    if workflow_id == "tekun_grant" and step_index == 0:
        grants = grant_eligibility_service.match_grants(db, sme_id=sme_id)
        result["grant_matches"] = grants[:3]
    elif workflow_id == "tekun_grant" and step_index == 2:
        rag = rag_service.rag_query(db, sme_id, "TEKUN micro credit eligibility documents Malaysia")
        result["draft_snippet"] = rag["answer"][:500]

    return result
