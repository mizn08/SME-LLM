from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile
from app.schemas import (
    ChatMemoryTurn,
    ChatRequest,
    ChatResponse,
    ChatSource,
    ChatWithMemoryRequest,
)
from app.services import chat_memory_service, guardrail_service, rag_service

router = APIRouter(tags=["v2-rag"])


def _chat_with_memory(
    db: Session,
    sme_id: int,
    message: str,
    persona: str | None,
    language: str | None,
    history: list[ChatMemoryTurn] | None = None,
    purchase_amount: float | None = None,
    purchase_category: str | None = None,
) -> ChatResponse:
    safe_msg = guardrail_service.sanitize_text(message)
    inj = guardrail_service.detect_prompt_injection(safe_msg)
    if not inj.safe:
        return ChatResponse(
            sme_id=sme_id,
            message=message,
            answer="Request blocked by safety guardrail. Please rephrase your financing question.",
            mode="guardrail_block",
            sources=[],
            language=language,
        )
    if history:
        chat_memory_service.sync_from_client(sme_id, history)
    prefix = chat_memory_service.context_prefix(sme_id)
    enriched = f"{prefix}Current question: {safe_msg}" if prefix else safe_msg
    mem_hist = [{"role": h.role, "text": h.text} for h in chat_memory_service.get_history(sme_id)]
    result = rag_service.rag_query(
        db,
        sme_id,
        enriched,
        persona,
        language=language,
        raw_question=safe_msg,
        history=mem_hist,
        purchase_amount=purchase_amount,
        purchase_category=purchase_category,
    )
    chat_memory_service.append_turn(sme_id, "user", message)
    chat_memory_service.append_turn(sme_id, "assistant", result["answer"])
    return ChatResponse(
        sme_id=sme_id,
        message=message,
        answer=result["answer"],
        mode=result["mode"],
        sources=[ChatSource(**s) for s in result["sources"]],
        language=result.get("language"),
    )


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == payload.sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return _chat_with_memory(
        db,
        payload.sme_id,
        payload.message,
        payload.persona,
        payload.language,
        purchase_amount=payload.purchase_amount,
        purchase_category=payload.purchase_category,
    )


@router.post("/chat/memory", response_model=ChatResponse)
def chat_with_memory(payload: ChatWithMemoryRequest, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == payload.sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return _chat_with_memory(
        db,
        payload.sme_id,
        payload.message,
        payload.persona,
        payload.language,
        payload.history,
        purchase_amount=payload.purchase_amount,
        purchase_category=payload.purchase_category,
    )


@router.get("/chat/stream")
def chat_stream(
    sme_id: int,
    message: str,
    persona: str | None = None,
    language: str | None = None,
    purchase_amount: float | None = None,
    purchase_category: str | None = None,
    db: Session = Depends(get_db),
):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    prefix = chat_memory_service.context_prefix(sme_id)
    enriched = f"{prefix}Current question: {message}" if prefix else message
    mem_hist = [{"role": h.role, "text": h.text} for h in chat_memory_service.get_history(sme_id)]

    def generate():
        full: list[str] = []
        for line in rag_service.rag_stream(
            db,
            sme_id,
            enriched,
            persona,
            language,
            raw_question=message,
            history=mem_hist,
            purchase_amount=purchase_amount,
            purchase_category=purchase_category,
        ):
            yield line
            if line.startswith("data: "):
                import json

                try:
                    obj = json.loads(line[6:].strip())
                    if obj.get("type") == "token":
                        full.append(obj.get("text", ""))
                except json.JSONDecodeError:
                    pass
        answer = "".join(full).strip()
        chat_memory_service.append_turn(sme_id, "user", message)
        chat_memory_service.append_turn(sme_id, "assistant", answer)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/sme/{sme_id}/chat/history", response_model=list[ChatMemoryTurn])
def get_chat_history(sme_id: int, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return chat_memory_service.get_history(sme_id)


@router.delete("/sme/{sme_id}/chat/history")
def clear_chat_history(sme_id: int, db: Session = Depends(get_db)):
    chat_memory_service.clear(sme_id)
    return {"status": "ok", "sme_id": sme_id}


@router.post("/chat/reindex")
def reindex_rag(sme_id: int, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    rag_service.invalidate_rag_cache(sme_id)
    rag_service.rag_query(db, sme_id, "reindex")
    return {"status": "ok", "sme_id": sme_id}
