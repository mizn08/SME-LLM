"""RAG: vector DB (v3) with BM25 fallback; optional OpenAI generation; streaming + BM."""

from __future__ import annotations

import json
import re
from typing import Any, Iterator

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.sme import SMEProfile
from app.services.knowledge_base import build_all_documents
from app.services.llm_client import invoke_chat, stream_chat
from app.services.rag_analytics_service import build_analytics_context
from app.services.financing_recommendation_service import build_recommendation, resolve_purchase_scenario

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


def _boost_docs_for_question(all_docs: list[Document], question: str, base: list[Document]) -> list[Document]:
    """Ensure financing-type docs appear when the question asks about them."""
    low = question.lower()
    wanted: set[str] = set()
    if any(w in low for w in ("bnpl", "pay later", "paylater", "installment", "atome", "grab", "spaylater")):
        wanted.add("bnpl")
    if any(w in low for w in ("grant", "geran", "mdec", "matrade", "madani", "gov")):
        wanted.add("gov_aid")
    if any(w in low for w in ("micro", "credit", "tekun", "loan", "cgc", "mara")):
        wanted.add("credit")
    if not wanted:
        return base

    out = list(base)
    seen = {d.page_content[:80] for d in out}
    for doc in all_docs:
        doc_type = doc.metadata.get("type")
        if doc_type in wanted and doc.page_content[:80] not in seen:
            out.append(doc)
            seen.add(doc.page_content[:80])
    return out[:8]


def _retrieve(db: Session, sme_id: int, question: str) -> tuple[list[Document], str]:
    settings = get_settings()
    all_docs = build_all_documents(db, sme_id)
    if settings.USE_VECTOR_RAG:
        try:
            from app.services import vector_rag_service

            docs = vector_rag_service.vector_query(db, sme_id, question)
            return _boost_docs_for_question(all_docs, question, docs), "chroma_vector"
        except Exception:
            pass
    retriever = _get_bm25(db, sme_id)
    docs = retriever.invoke(question)
    return _boost_docs_for_question(all_docs, question, docs), "bm25"


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
        return " Jawab dalam Bahasa Malaysia yang natural dan mesra."
    return " Answer in natural, conversational English."


def _is_meta_or_emotional(question: str) -> bool:
    low = question.lower()
    cues = (
        "upset",
        "angry",
        "frustrat",
        "not answer",
        "didn't answer",
        "dont answer",
        "don't answer",
        "wrong",
        "hallucin",
        "template",
        "copy paste",
        "hello",
        "hi ",
        "who are you",
        "thank",
        "help me understand",
    )
    return any(c in low for c in cues)


def _is_financing_question(question: str) -> bool:
    low = question.lower()
    cues = (
        "bnpl",
        "grant",
        "loan",
        "financ",
        "purchase",
        "buy ",
        "cash flow",
        "runway",
        "burn",
        "roi",
        "forecast",
        "instalment",
        "installment",
        "should i",
        "recommend",
        "afford",
        "simulate",
        "geran",
        "kredit",
        "pembiayaan",
    )
    return any(c in low for c in cues)


def _is_personal_business_question(question: str) -> bool:
    low = question.lower()
    personal = (
        "my business",
        "my sme",
        "our shop",
        "our store",
        "my company",
        "my shop",
        "should i buy",
        "should i get",
        "can i afford",
        "for my ",
        "our business",
        "based on my data",
        "my health tab",
        "my runway",
        "my cash",
    )
    return any(c in low for c in personal)


def _is_educational_or_survey(question: str) -> bool:
    """General BNPL/finance Q&A or pasted test lists — not 'advise my shop'."""
    if _is_personal_business_question(question):
        return False
    low = question.lower()
    numbered = len(re.findall(r"\b\d{1,3}[\.\):]", question))
    qmarks = question.count("?")
    if numbered >= 2 or qmarks >= 3:
        return True
    survey_cues = (
        "category ",
        "edge-case",
        "edge case",
        "test question",
        "questionnaire",
        "explain the",
        "what are the",
        "how does ",
        "how do ",
        "compare ",
        "in general",
        "hypothetically",
        "list the",
        "describe the",
        "what is an sla",
        "what is a ",
        "why would ",
        "causes for",
        "us-focused",
        "u.s.",
        "united states",
        "testing",
        "questions for",
    )
    if any(c in low for c in ("us-focused", "u.s.", "united states", "testing")):
        return True
    if any(c in low for c in survey_cues) and len(question) > 200:
        return True
    if len(question) > 600 and _is_financing_question(question):
        return True
    if len(question) > 1200 and qmarks >= 1:
        return True
    return False


def _filter_docs_for_educational(docs: list[Document]) -> list[Document]:
    """Drop per-SME profile/KPI docs so the model does not pivot to one business."""
    general = {"bnpl", "gov_aid", "credit"}
    filtered = [d for d in docs if d.metadata.get("type") in general]
    return filtered if filtered else docs[:4]


def _history_messages(history: list[dict[str, str]] | None, max_turns: int = 8) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for turn in (history or [])[-max_turns:]:
        role = turn.get("role", "")
        text = (turn.get("text") or "").strip()
        if not text:
            continue
        if role == "user":
            out.append(("human", text[:1200]))
        elif role == "assistant":
            out.append(("ai", text[:800]))
    return out


def _system_prompt(
    persona: str | None,
    lang: str,
    *,
    financing: bool,
    meta: bool,
    educational: bool = False,
) -> str:
    personas = _PERSONA_SYSTEM.get(lang, _PERSONA_SYSTEM["en"])
    persona_system = personas.get((persona or "").lower(), personas["default"])
    persona_system += _lang_instruction(lang)
    if educational:
        base = (
            persona_system
            + " The user pasted general finance/BNPL questions (possibly US or global examples). "
            "Your job is to ANSWER those questions directly — not to redirect to one SME's dashboard. "
            "Never say you cannot answer because you only advise Malaysian owners or because questions are US-focused. "
            "Explain concepts clearly; add brief Malaysia/US differences only where helpful. "
            "Do not open with Kopi Maju, runway, health score, or product recommendations unless they ask about their business. "
            "If there are many questions, group by theme (models, SLAs, refunds, metrics, risk). "
            "Never invent specific RM amounts for their business."
        )
    else:
        base = (
            persona_system
            + " You are having a real chat with a Malaysian SME owner — not filling a form. "
            "Read their latest message carefully and respond to what they actually asked. "
            "You may also answer general finance education when asked; do not refuse open questions. "
            "Use COMPUTED ANALYTICS numbers when discussing their money (they match the Health tab). "
            "Never invent RM amounts or products. "
            "Do not paste a fixed report template. Write 2–4 short paragraphs in plain language. "
            "Use **bold** sparingly for one key takeaway if helpful."
        )
    if educational:
        base += (
            " Answer every substantive point in the user's message before any optional offer to personalize."
        )
    elif meta:
        base += (
            " The user may be frustrated or off-topic — acknowledge that first, then offer to help "
            "with their underlying financing or cash question. Be empathetic and direct."
        )
    elif financing:
        base += (
            " They asked about money/financing for their business — give one clear recommendation in prose, "
            "then briefly explain why using 2–3 facts from analytics. "
            "If analytics says Hold or stabilise cash, do not push BNPL or loans. "
            "Soft loans are repayable — never call them grants."
        )
    else:
        base += (
            " This is an open question — explain clearly without dumping every KPI. "
            "Only cite specific RM figures when directly relevant."
        )
    return base


def _light_fallback(
    db: Session,
    sme_id: int,
    raw_question: str,
    lang: str,
    *,
    purchase_amount: float | None = None,
    purchase_category: str | None = None,
) -> str:
    rec = build_recommendation(
        db,
        sme_id,
        purchase_amount=purchase_amount,
        purchase_category=purchase_category,
        lang=lang,
    )
    snap = rec["snapshot"]
    k = snap["kpis"]
    if lang == "ms":
        intro = (
            "Maaf — enjin AI sedang sibuk, jadi saya ringkaskan berdasarkan data Health tab anda."
        )
    else:
        if get_settings().active_llm_api_key:
            intro = (
                "Sorry — the live AI model hit an error (timeout or server issue). "
                "Here is a concise answer from your synced Health data."
            )
        else:
            intro = (
                "Sorry — no AI API key in .env (set CHUTES_API_KEY or CHUTES_API_TOKEN). "
                "Here is a concise answer from your synced Health data."
            )
    if _is_meta_or_emotional(raw_question) and not _is_financing_question(raw_question):
        if lang == "ms":
            return (
                "Saya faham kekecewaan anda — maaf jawapan tadi tidak tepat. "
                "Tanya semula soalan anda (contoh: BNPL vs geran, ramalan tunai, atau perbelanjaan marketing) "
                f"dan saya akan jawab terus. Data Health tab anda: net 90 hari **RM {k['net_operating_cash_rm']:,.2f}**, "
                f"runway **{k['days_cash_on_hand']:.0f} hari**."
            )
        return (
            "I hear you — sorry the last reply missed your question. "
            "Ask again in your own words (e.g. BNPL vs grant, cash forecast, or why runway is zero) "
            f"and I will answer directly. Your synced Health data: 90-day net **RM {k['net_operating_cash_rm']:,.2f}**, "
            f"runway **{k['days_cash_on_hand']:.0f} days**."
        )
    body = (
        f"{intro}\n\n{rec['star_line']}\n\n"
        f"Your 90-day net cash is **RM {k['net_operating_cash_rm']:,.2f}**, "
        f"runway **{k['days_cash_on_hand']:.0f} days**, burn **RM {k['burn_rate_monthly_rm']:,.2f}/month**. "
        "Ask a follow-up and I will explain in more detail."
    )
    return body


def _template_answer(
    db: Session,
    sme_id: int,
    raw_question: str,
    docs: list[Document],
    persona: str | None = None,
    lang: str = "en",
    *,
    purchase_amount: float | None = None,
    purchase_category: str | None = None,
) -> str:
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if sme:
        return _persona_prefix(persona) + _light_fallback(
            db,
            sme_id,
            raw_question,
            lang,
            purchase_amount=purchase_amount,
            purchase_category=purchase_category,
        )
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
        body = f"Soalan: {raw_question}\n\n{context}"
    else:
        body = f"Question: {raw_question}\n\n{context}"
    return _persona_prefix(persona) + body


def _build_llm_messages(
    db: Session,
    sme_id: int,
    raw_question: str,
    docs: list[Document],
    persona: str | None,
    lang: str,
    history: list[dict[str, str]] | None,
    *,
    purchase_amount: float | None = None,
    purchase_category: str | None = None,
) -> tuple[list[tuple[str, str]], bool]:
    educational = _is_educational_or_survey(raw_question)
    use_docs = _filter_docs_for_educational(docs) if educational else docs[:5]
    context = "\n\n".join(d.page_content for d in use_docs[:5])
    analytics = ""
    if not educational:
        analytics = build_analytics_context(
            db,
            sme_id,
            raw_question,
            purchase_amount=purchase_amount,
            purchase_category=purchase_category,
        )
        amt, cat = resolve_purchase_scenario(
            raw_question, purchase_amount=purchase_amount, purchase_category=purchase_category
        )
        if amt:
            analytics += (
                f"\nSimulate purchase locked: RM {amt:,.0f} ({cat}) — "
                "do not substitute category spend totals."
            )
        rec = build_recommendation(
            db, sme_id, purchase_amount=amt, purchase_category=cat, lang=lang
        )
        analytics += f"\nEngine recommendation: {rec['star_line']}"

    meta = _is_meta_or_emotional(raw_question)
    financing = _is_financing_question(raw_question) and not educational
    system = _system_prompt(
        persona, lang, financing=financing, meta=meta, educational=educational
    )
    if context:
        system += "\n\nReference material (product catalog only; do not copy verbatim):\n" + context[:3500]
    if analytics:
        system += "\n\n" + analytics

    messages: list[tuple[str, str]] = [("system", system)]
    messages.extend(_history_messages(history))
    human = raw_question
    if educational:
        human = (
            "Answer the following questions directly in your reply (do not refuse or redirect "
            "to one business dashboard):\n\n"
            + raw_question
        )
    messages.append(("human", human))
    return messages, educational


def _openai_answer(
    db: Session,
    sme_id: int,
    raw_question: str,
    docs: list[Document],
    persona: str | None = None,
    lang: str = "en",
    history: list[dict[str, str]] | None = None,
    *,
    purchase_amount: float | None = None,
    purchase_category: str | None = None,
) -> tuple[str, bool]:
    settings = get_settings()
    if not settings.active_llm_api_key:
        return (
            _template_answer(
                db,
                sme_id,
                raw_question,
                docs,
                persona,
                lang,
                purchase_amount=purchase_amount,
                purchase_category=purchase_category,
            ),
            False,
        )
    try:
        messages, educational = _build_llm_messages(
            db,
            sme_id,
            raw_question,
            docs,
            persona,
            lang,
            history,
            purchase_amount=purchase_amount,
            purchase_category=purchase_category,
        )
        max_tokens = 3072 if educational else int(getattr(settings, "CHUTES_MAX_TOKENS", 1024))
        return (
            invoke_chat(
                messages,
                settings=settings,
                prefer_fast=True,
                max_rounds=2,
                max_tokens=max_tokens,
            ),
            True,
        )
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning("LLM fallback: %s", exc)
        return (
            _persona_prefix(persona)
            + _light_fallback(
                db,
                sme_id,
                raw_question,
                lang,
                purchase_amount=purchase_amount,
                purchase_category=purchase_category,
            ),
            False,
        )


def financing_quote_advice(
    db: Session,
    sme_id: int,
    *,
    quote_total_rm: float,
    purchase_amount: float,
    purchase_category: str | None,
    lang: str = "en",
) -> dict[str, Any]:
    """Fast BNPL/grant/credit advice after SME Quote — avoids heavy RAG + bad fallbacks."""
    import logging

    from app.services.financing_recommendation_service import build_recommendation
    from app.services.rag_analytics_service import build_analytics_answer

    rec = build_recommendation(
        db,
        sme_id,
        purchase_amount=purchase_amount,
        purchase_category=purchase_category or "digital",
        lang=lang,
    )
    k = rec["snapshot"]["kpis"]
    health = rec["snapshot"]["health"]["health_score"]
    settings = get_settings()
    if settings.active_llm_api_key:
        try:
            answer = invoke_chat(
                [
                    (
                        "system",
                        "You are SME Advisor for Malaysian SMEs. Write 3 short paragraphs: "
                        "compare BNPL vs grant vs micro-credit for this purchase. "
                        "Use only the facts provided. Do not refuse or say you lack data.",
                    ),
                    (
                        "human",
                        f"Quote total RM {quote_total_rm:,.2f}. Purchase budget RM {purchase_amount:,.0f} "
                        f"({purchase_category or 'general'}).\n"
                        f"Recommendation: {rec['star_line']}\n"
                        f"90-day net cash RM {k['net_operating_cash_rm']:,.2f}, runway "
                        f"{k['days_cash_on_hand']:.0f} days, health score {health}/100.\n"
                        "Which path fits best and what is the main risk?",
                    ),
                ],
                settings=settings,
                max_tokens=900,
                max_rounds=2,
                temperature=0.5,
            )
            return {"answer": answer, "mode": "quote_financing+llm", "sources": [], "language": lang}
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).warning("Quote financing LLM failed: %s", exc)

    answer = build_analytics_answer(
        db,
        sme_id,
        f"Financing for RM {purchase_amount:,.0f} purchase",
        lang=lang,
        purchase_amount=purchase_amount,
        purchase_category=purchase_category,
    )
    return {"answer": answer, "mode": "quote_financing+analytics", "sources": [], "language": lang}


def rag_query(
    db: Session,
    sme_id: int,
    question: str,
    persona: str | None = None,
    language: str | None = None,
    *,
    raw_question: str | None = None,
    history: list[dict[str, str]] | None = None,
    purchase_amount: float | None = None,
    purchase_category: str | None = None,
) -> dict[str, Any]:
    lang = _lang_code(language)
    raw = (raw_question or question).strip()
    docs, retrieval_mode = _retrieve(db, sme_id, raw)
    settings = get_settings()
    if settings.active_llm_api_key:
        answer, llm_used = _openai_answer(
            db,
            sme_id,
            raw,
            docs,
            persona,
            lang,
            history,
            purchase_amount=purchase_amount,
            purchase_category=purchase_category,
        )
        tag = "educational" if _is_educational_or_survey(raw) else "advisory"
        mode = f"{retrieval_mode}+{tag}+llm" if llm_used else f"{retrieval_mode}+{tag}+fallback"
    else:
        answer = _template_answer(
            db,
            sme_id,
            raw,
            docs,
            persona,
            lang,
            purchase_amount=purchase_amount,
            purchase_category=purchase_category,
        )
        mode = f"{retrieval_mode}+fallback"

    sources = [{"type": d.metadata.get("type"), "snippet": d.page_content[:200]} for d in docs]
    return {"answer": answer, "sources": sources, "mode": mode, "language": lang}


def rag_stream(
    db: Session,
    sme_id: int,
    question: str,
    persona: str | None = None,
    language: str | None = None,
    *,
    raw_question: str | None = None,
    history: list[dict[str, str]] | None = None,
    purchase_amount: float | None = None,
    purchase_category: str | None = None,
) -> Iterator[str]:
    """Yield SSE data lines with true LLM token streaming when available."""
    lang = _lang_code(language)
    raw = (raw_question or question).strip()
    docs, retrieval_mode = _retrieve(db, sme_id, raw)
    settings = get_settings()
    sources = [{"type": d.metadata.get("type"), "snippet": d.page_content[:200]} for d in docs]

    payload_start = {
        "type": "meta",
        "mode": f"{retrieval_mode}+llm_stream",
        "sources": sources,
        "language": lang,
    }
    yield f"data: {json.dumps(payload_start)}\n\n"

    if not settings.active_llm_api_key:
        answer = _template_answer(
            db,
            sme_id,
            raw,
            docs,
            persona,
            lang,
            purchase_amount=purchase_amount,
            purchase_category=purchase_category,
        )
        yield f"data: {json.dumps({'type': 'token', 'text': answer})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    try:
        messages, educational = _build_llm_messages(
            db,
            sme_id,
            raw,
            docs,
            persona,
            lang,
            history,
            purchase_amount=purchase_amount,
            purchase_category=purchase_category,
        )
        max_tokens = 3072 if educational else int(getattr(settings, "CHUTES_MAX_TOKENS", 1024))
        streamed_any = False
        try:
            for token in stream_chat(messages, settings=settings, max_tokens=max_tokens):
                streamed_any = True
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
        except Exception as stream_exc:  # noqa: BLE001
            import logging

            logging.getLogger(__name__).warning("LLM stream failed: %s", stream_exc)
            if not streamed_any:
                reply = invoke_chat(
                    messages,
                    settings=settings,
                    max_tokens=max_tokens,
                    max_rounds=2,
                )
                yield f"data: {json.dumps({'type': 'token', 'text': reply})}\n\n"
                streamed_any = True
        if streamed_any:
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning("LLM chat failed: %s", exc)
        answer = _light_fallback(
            db,
            sme_id,
            raw,
            lang,
            purchase_amount=purchase_amount,
            purchase_category=purchase_category,
        )
        yield f"data: {json.dumps({'type': 'token', 'text': answer})}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"

