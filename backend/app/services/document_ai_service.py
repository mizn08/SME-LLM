"""Structured document extraction (regex + optional LLM vision)."""

from __future__ import annotations

import io
import re
from typing import Any

from app.core.config import get_settings
from app.services.document_intake_service import extract_from_upload


def extract_structured(file_bytes: bytes, filename: str = "upload") -> dict[str, Any]:
    base = extract_from_upload(file_bytes, filename)
    text = base.get("text", "")
    structured = build_structured_fields(text, base.get("parsed_rows", []))
    settings = get_settings()
    if settings.active_llm_api_key and text:
        llm_fields = _llm_structure(text)
        if llm_fields:
            structured.update({k: v for k, v in llm_fields.items() if v})
    return {
        **base,
        "structured": structured,
        "engine": str(base.get("engine", "unknown")) + "+document_ai",
    }


def build_structured_fields(text: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "vendor": _find_vendor(text),
        "invoice_date": _find_date(text),
        "total_rm": _find_total(text),
        "sst_rm": _find_sst(text),
        "line_items": _line_items(text, rows),
        "category_guess": _guess_category(text),
    }


def _find_vendor(text: str) -> str | None:
    for line in text.splitlines()[:8]:
        line = line.strip()
        if len(line) > 4 and not re.search(r"invoice|receipt|tax", line, re.I):
            return line[:80]
    return None


def _find_date(text: str) -> str | None:
    m = re.search(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", text)
    return m.group(1) if m else None


def _find_total(text: str) -> float | None:
    patterns = [
        r"total\s*(?:due)?\s*:?\s*RM\s*([\d,]+\.?\d*)",
        r"amount\s*due\s*:?\s*RM\s*([\d,]+\.?\d*)",
        r"RM\s*([\d,]+\.?\d*)\s*$",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I | re.M)
        if m:
            return float(m.group(1).replace(",", ""))
    return None


def _find_sst(text: str) -> float | None:
    m = re.search(r"SST\s*(?:6%|8%)?\s*:?\s*RM\s*([\d,]+\.?\d*)", text, re.I)
    return float(m.group(1).replace(",", "")) if m else None


def _line_items(text: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for r in rows[:20]:
        items.append(
            {
                "description": r.get("description", "")[:80],
                "amount_rm": r.get("amount_rm"),
                "category": r.get("category", "invoice"),
            }
        )
    return items


def _guess_category(text: str) -> str:
    low = text.lower()
    if any(w in low for w in ("fuel", "petrol", "shell", "petronas")):
        return "transport"
    if any(w in low for w in ("rent", "lease", "office")):
        return "rent"
    if any(w in low for w in ("software", "cloud", "subscription")):
        return "technology"
    return "general_expense"


def _llm_structure(text: str) -> dict[str, Any] | None:
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        settings = get_settings()
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "Extract invoice JSON keys: vendor, invoice_date, total_rm, sst_rm. Numbers only for amounts."),
                ("human", "{text}"),
            ]
        )
        chain = prompt | ChatOpenAI(
            model=settings.active_llm_model,
            temperature=0,
            api_key=settings.active_llm_api_key,
            base_url=settings.active_llm_base_url,
        )
        msg = chain.invoke({"text": text[:3000]})
        return {"vendor": str(msg.content)[:80]}
    except Exception:
        return None
