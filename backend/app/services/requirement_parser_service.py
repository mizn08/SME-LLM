"""Parse unstructured client brief text/files into structured requirements."""

from __future__ import annotations

import io
import re


def _extract_text_from_bytes(content: bytes, filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            return ""
    if name.endswith(".docx"):
        try:
            import docx

            document = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in document.paragraphs)
        except Exception:
            return ""
    if name.endswith(".json"):
        return content.decode("utf-8", errors="ignore")
    if name.endswith(".md"):
        return content.decode("utf-8", errors="ignore")
    if name.endswith(".csv"):
        return content.decode("utf-8", errors="ignore")
    return content.decode("utf-8", errors="ignore")


def _normalize_transcript_text(raw_text: str) -> str:
    text = (raw_text or "").replace("\r", "\n")
    # Keep dialogue lines like "Client: ...", "[00:12] SME: ...", "Speaker 1 - ..."
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    cleaned: list[str] = []
    for line in lines:
        line = re.sub(r"^\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*", "", line)
        line = re.sub(r"^(speaker\s*\d+)\s*[:\-]\s*", r"\1: ", line, flags=re.I)
        cleaned.append(line)
    return "\n".join(cleaned)


def summarize_transcript(raw_text: str) -> dict:
    normalized = _normalize_transcript_text(raw_text)
    parsed = parse_requirement_text(normalized)
    lower = normalized.lower()
    speaker_turns = len(
        re.findall(
            r"(?:^|\n)\s*(?:client|customer|owner|founder|sme|agent|speaker\s*\d+)\s*[:\-]",
            lower,
        )
    )
    evidence = []
    for key, pat in (
        ("budget", r"(?:rm|myr)\s*[0-9][0-9,]*(?:\.\d+)?"),
        ("location", r"(kuala lumpur|selangor|penang|johor bahru|johor|perak|sabah|sarawak|melaka|negeri sembilan)"),
        ("category", r"(e-?commerce|website|inventory sync|pos|point of sale|equipment|software|digital upgrade)"),
    ):
        m = re.search(pat, lower)
        if m:
            evidence.append({"field": key, "match": m.group(1) if m.lastindex else m.group(0)})

    confidence = 0.35
    if parsed.get("budget") is not None:
        confidence += 0.25
    if parsed.get("location"):
        confidence += 0.15
    if parsed.get("purchase_category"):
        confidence += 0.15
    if parsed.get("explicit_constraints"):
        confidence += 0.10

    return {
        **parsed,
        "source_type": "transcript",
        "speaker_turns": speaker_turns,
        "confidence": round(min(confidence, 0.95), 2),
        "evidence": evidence[:6],
        "normalized_preview": normalized[:1000],
    }


def parse_requirement_text(raw_text: str) -> dict:
    text = " ".join((raw_text or "").strip().split())
    lower = text.lower()

    budget_match = re.search(r"(rm|myr)\s*([0-9][0-9,]*(?:\.\d+)?)", lower)
    location_match = re.search(
        r"(kuala lumpur|selangor|penang|johor bahru|johor|perak|sabah|sarawak|melaka|negeri sembilan)",
        lower,
    )
    category_match = re.search(
        r"(e-?commerce|website|inventory sync|pos|point of sale|fnb|retail|agro|equipment|router|"
        r"digital upgrade|software|micro[- ]?credit|bnpl|grant)",
        lower,
    )

    constraints = []
    for phrase in (
        "bnpl",
        "grant",
        "micro-credit",
        "low monthly payment",
        "islamic financing",
        "cash flow",
        "no collateral",
    ):
        if phrase in lower:
            constraints.append(phrase)

    budget_value = None
    if budget_match:
        budget_value = float(budget_match.group(2).replace(",", ""))

    purchase_category = None
    if category_match:
        token = category_match.group(1).lower().replace(" ", "-")
        if token in ("pos", "point-of-sale"):
            purchase_category = "pos"
        elif token in ("fnb", "retail", "agro", "equipment", "router"):
            purchase_category = token
        elif token in ("e-commerce", "ecommerce", "website", "inventory-sync", "software"):
            purchase_category = "ecommerce"
        elif "digital" in token:
            purchase_category = "digital"

    return {
        "budget": budget_value,
        "currency": budget_match.group(1).upper() if budget_match else "RM",
        "purchase_category": purchase_category,
        "explicit_constraints": constraints,
        "location": location_match.group(1).title() if location_match else "Kuala Lumpur",
        "source_chars": len(text),
    }


def parse_requirement_file(content: bytes, filename: str) -> dict:
    text = _extract_text_from_bytes(content, filename)
    return parse_requirement_text(text)
