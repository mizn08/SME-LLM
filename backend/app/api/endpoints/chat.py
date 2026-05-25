from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
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
from app.services import chat_memory_service, rag_service

router = APIRouter(tags=["v2-rag"])


def _chat_with_memory(
    db: Session,
    sme_id: int,
    message: str,
    persona: str | None,
    history: list[ChatMemoryTurn] | None = None,
) -> ChatResponse:
    if history:
        chat_memory_service.sync_from_client(sme_id, history)
    prefix = chat_memory_service.context_prefix(sme_id)
    enriched = f"{prefix}Current question: {message}" if prefix else message
    result = rag_service.rag_query(db, sme_id, enriched, persona)
    chat_memory_service.append_turn(sme_id, "user", message)
    chat_memory_service.append_turn(sme_id, "assistant", result["answer"])
    return ChatResponse(
        sme_id=sme_id,
        message=message,
        answer=result["answer"],
        mode=result["mode"],
        sources=[ChatSource(**s) for s in result["sources"]],
    )


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == payload.sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return _chat_with_memory(db, payload.sme_id, payload.message, payload.persona)


@router.post("/chat/memory", response_model=ChatResponse)
def chat_with_memory(payload: ChatWithMemoryRequest, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == payload.sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    return _chat_with_memory(
        db, payload.sme_id, payload.message, payload.persona, payload.history
    )


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
