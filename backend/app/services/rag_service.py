"""RAG: vector DB (v3) with BM25 fallback; optional OpenAI generation; streaming + BM."""

from __future__ import annotations

import json
from typing import Any, Iterator

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.knowledge_base import build_all_documents

_retriever_cache: dict[int, BM25Retriever] = {}


def _get_bm25(db: Session, sme_id: int) -> BM25Retriever:
    if sme_id not in _retriever_cache:
        docs = build_all_documents(db, sme_id)
        if not docs:
            docs = [Document(page_content="No data loaded for this SME yet.")]
        retriever = BM25Retriever.from_documents(docs)
        retriever.k = 5
        _retriever_cache[sme_id] = retriever
    return _retriever_cache[sme_id]


def invalidate_rag_cache(sme_id: int | None = None) -> None:
    if sme_id is None:
        _retriever_cache.clear()
    else:
        _retriever_cache.pop(sme_id, None)
    if get_settings().USE_VECTOR_RAG:
        from app.services import vector_rag_service

        vector_rag_service.invalidate_vector_cache(sme_id)


def _retrieve(db: Session, sme_id: int, question: str) -> tuple[list[Document], str]:
    settings = get_settings()
    if settings.USE_VECTOR_RAG:
        try:
            from app.services import vector_rag_service

            docs = vector_rag_service.vector_query(db, sme_id, question)
            return docs, "chroma_vector"
        except Exception:
            pass
    retriever = _get_bm25(db, sme_id)
    return retriever.invoke(question), "bm25"


_PERSONA_PREFIX = {
    "banker": "Puan Sarah (conservative banker): ",
    "towkay": "Uncle Ah Kow (experienced towkay): ",
    "mdec": "Dr Aisha (MDEC digital consultant): ",
}

_PERSONA_SYSTEM = {
    "en": {
        "banker": "You are Puan Sarah, a conservative Malaysian banker. Formal, risk-aware.",
        "towkay": "You are Uncle Ah Kow, a seasoned Malaysian SME towkay. Practical, light Manglish.",
        "mdec": "You are Dr Aisha, an MDEC digitalisation consultant. Focus on grants and tech.",
        "default": "You are SME Advisor for Malaysian SMEs.",
    },
    "ms": {
        "banker": "Anda ialah Puan Sarah, banker Malaysia yang konservatif. Formal, berfokus risiko.",
        "towkay": "Anda ialah Uncle Ah Kow, towkay SME berpengalaman. Praktikal, guna BM ringkas.",
        "mdec": "Anda ialah Dr Aisha, perunding digital MDEC. Fokus geran dan digitalisasi.",
        "default": "Anda ialah Penasihat SME untuk perniagaan Malaysia.",
    },
}


def _lang_code(language: str | None) -> str:
    if not language:
        return "en"
    low = language.lower()
    if low in ("ms", "bm", "malay", "bahasa"):
        return "ms"
    return "en"


def _persona_prefix(persona: str | None) -> str:
    if not persona:
        return ""
    return _PERSONA_PREFIX.get(persona.lower(), "")


def _lang_instruction(lang: str) -> str:
    if lang == "ms":
        return " Jawab dalam Bahasa Malaysia yang jelas dan profesional."
    return " Answer in clear English."


def _template_answer(
    question: str, docs: list[Document], persona: str | None = None, lang: str = "en"
) -> str:
    if not docs:
        if lang == "ms":
            return "Data belum diindeks. Muat naik CSV di tab Health dahulu."
        return "I do not have enough indexed data yet. Upload a CSV on the Health tab first."
    bullets = []
    for i, d in enumerate(docs[:4], 1):
        src = d.metadata.get("type", "info")
        bullets.append(f"{i}. [{src}] {d.page_content[:280]}")
    context = "\n".join(bullets)
    if lang == "ms":
        body = (
            f"Soalan: {question}\n\n"
            "Berikut ditemui dalam pangkalan pengetahuan SME Advisor:\n\n"
            f"{context}\n\n"
            "Tip: Guna Simulator untuk cadangan pembiayaan formal dengan skor ML."
        )
    else:
        body = (
            f"Question: {question}\n\n"
            "Here is what I found in your SME Advisor knowledge base:\n\n"
            f"{context}\n\n"
            "Tip: Run the Purchase Simulator for a formal financing recommendation with ML scores."
        )
    return _persona_prefix(persona) + body


def _openai_answer(
    question: str, docs: list[Document], persona: str | None = None, lang: str = "en"
) -> str:
    settings = get_settings()
    if not settings.active_llm_api_key:
        return _template_answer(question, docs, persona, lang)
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        context = "\n\n".join(d.page_content for d in docs[:5])
        personas = _PERSONA_SYSTEM.get(lang, _PERSONA_SYSTEM["en"])
        persona_system = personas.get((persona or "").lower(), personas["default"])
        persona_system += _lang_instruction(lang)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    persona_system + " Answer using ONLY the context. Mention RM when relevant. Be concise.",
                ),
                ("human", "Context:\n{context}\n\nQuestion: {question}"),
            ]
        )
        chain = prompt | ChatOpenAI(
            model=settings.active_llm_model,
            temperature=0.2,
            api_key=settings.active_llm_api_key,
            base_url=settings.active_llm_base_url,
        )
        msg = chain.invoke({"context": context, "question": question})
        return str(msg.content)
    except Exception as exc:  # noqa: BLE001
        return _template_answer(question, docs, persona, lang) + f"\n\n(LLM unavailable: {exc})"


def _stream_tokens(text: str, chunk_size: int = 12) -> Iterator[str]:
    words = text.split(" ")
    buf: list[str] = []
    for w in words:
        buf.append(w)
        if len(buf) >= chunk_size // 3 + 1:
            yield " ".join(buf) + " "
            buf = []
    if buf:
        yield " ".join(buf)


def rag_query(
    db: Session,
    sme_id: int,
    question: str,
    persona: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    lang = _lang_code(language)
    docs, retrieval_mode = _retrieve(db, sme_id, question)
    settings = get_settings()
    if settings.active_llm_api_key:
        answer = _openai_answer(question, docs, persona, lang)
        mode = f"{retrieval_mode}+openai"
    else:
        answer = _template_answer(question, docs, persona, lang)
        mode = retrieval_mode

    sources = [{"type": d.metadata.get("type"), "snippet": d.page_content[:200]} for d in docs]
    return {"answer": answer, "sources": sources, "mode": mode, "language": lang}


def rag_stream(
    db: Session,
    sme_id: int,
    question: str,
    persona: str | None = None,
    language: str | None = None,
) -> Iterator[str]:
    """Yield SSE data lines."""
    result = rag_query(db, sme_id, question, persona, language)
    payload_start = {
        "type": "meta",
        "mode": result["mode"],
        "sources": result["sources"],
        "language": result.get("language", "en"),
    }
    yield f"data: {json.dumps(payload_start)}\n\n"
    for chunk in _stream_tokens(result["answer"]):
        yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"
