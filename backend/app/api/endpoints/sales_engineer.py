from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.quote import QuoteLog
from app.models.sme import SMEProfile
from app.schemas import (
    BusinessValueMetrics,
    ChatSource,
    QuoteHistoryItem,
    SalesAgentRunRequest,
    SalesAgentRunResponse,
)
from app.services import business_value_service, requirement_parser_service, sales_engineer_agent

router = APIRouter(tags=["v6-sales-engineer"])


@router.post("/sales-agent/run", response_model=SalesAgentRunResponse)
def run_sales_agent(payload: SalesAgentRunRequest, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == payload.sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    if not payload.brief_text and not payload.requirements:
        raise HTTPException(400, "Provide brief_text or requirements")
    try:
        out = sales_engineer_agent.run_sales_engineer(
            db,
            sme_id=payload.sme_id,
            brief_text=payload.brief_text,
            requirements=payload.requirements,
            location=payload.location,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Sales agent failed: {exc}") from exc
    bv_raw = dict(out["business_value"])
    bv_raw.pop("last_run_seconds", None)
    bv_raw.pop("last_run_minutes", None)
    return SalesAgentRunResponse(
        sme_id=out["sme_id"],
        requirements=out["requirements"],
        task_complete=out["task_complete"],
        agent_mode=out.get("agent_mode", "rule_fallback"),
        agent_trace=out["agent_trace"],
        reasoning_summary=out["reasoning_summary"],
        quote=out.get("quote"),
        business_value=BusinessValueMetrics(**bv_raw),
        rag_answer=out.get("rag_answer"),
        rag_mode=out.get("rag_mode"),
        rag_sources=[ChatSource(**s) for s in out.get("rag_sources", [])],
        error=out.get("error"),
    )


@router.get("/business-value/metrics", response_model=BusinessValueMetrics)
def business_value_metrics(sme_id: int | None = None, db: Session = Depends(get_db)):
    return BusinessValueMetrics(**business_value_service.compute_metrics(db, sme_id))


@router.get("/quote/history/{sme_id}", response_model=list[QuoteHistoryItem])
def quote_history(sme_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(QuoteLog)
        .filter(QuoteLog.sme_id == sme_id)
        .order_by(QuoteLog.id.desc())
        .limit(50)
        .all()
    )
    return [
        QuoteHistoryItem(
            quote_id=r.id,
            sme_id=r.sme_id,
            title=r.title,
            location=r.location,
            grand_total_rm=r.grand_total_rm,
            estimated_delivery_days=r.estimated_delivery_days,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.post("/sales-agent/parse-client-transcript")
async def parse_client_transcript(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith((".pdf", ".txt", ".docx", ".md", ".json", ".csv")):
        raise HTTPException(400, "Supported transcript types: .pdf, .txt, .docx, .md, .json, .csv")
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Empty file")
    text = requirement_parser_service._extract_text_from_bytes(raw, filename)
    if not text.strip():
        raise HTTPException(400, "No text extracted from transcript")
    return requirement_parser_service.summarize_transcript(text)
