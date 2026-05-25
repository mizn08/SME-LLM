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
from app.services import chat_memory_service, rag_service

router = APIRouter(tags=["v2-rag"])


def _chat_with_memory(
    db: Session,
    sme_id: int,
    message: str,
    persona: str | None,
    language: str | None,
    history: list[ChatMemoryTurn] | None = None,
) -> ChatResponse:
    if history:
        chat_memory_service.sync_from_client(sme_id, history)
    prefix = chat_memory_service.context_prefix(sme_id)
    enriched = f"{prefix}Current question: {message}" if prefix else message
    result = rag_service.rag_query(db, sme_id, enriched, persona, language=language)
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
        db, payload.sme_id, payload.message, payload.persona, payload.language
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
    )


@router.get("/chat/stream")
def chat_stream(
    sme_id: int,
    message: str,
    persona: str | None = None,
    language: str | None = None,
    db: Session = Depends(get_db),
):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    prefix = chat_memory_service.context_prefix(sme_id)
    enriched = f"{prefix}Current question: {message}" if prefix else message

    def generate():
        full: list[str] = []
        for line in rag_service.rag_stream(db, sme_id, enriched, persona, language):
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
