"""WhatsApp / Telegram bot webhook wrappers around RAG chat."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services import chat_memory_service, rag_service


def handle_message(
    db: Session,
    sme_id: int,
    text: str,
    channel: str = "whatsapp",
    persona: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    prefix = chat_memory_service.context_prefix(sme_id)
    enriched = f"{prefix}Current question: {text}" if prefix else text
    result = rag_service.rag_query(db, sme_id, enriched, persona, language=language)
    chat_memory_service.append_turn(sme_id, "user", text)
    chat_memory_service.append_turn(sme_id, "assistant", result["answer"])
    quick_replies = [
        "What is my cash runway?",
        "Best BNPL for RM5K equipment",
        "Grant eligibility check",
    ]
    return {
        "channel": channel,
        "sme_id": sme_id,
        "reply": result["answer"],
        "mode": result["mode"],
        "quick_replies": quick_replies,
    }
