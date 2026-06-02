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
    return content.decode("utf-8", errors="ignore")


def parse_requirement_text(raw_text: str) -> dict:
    text = " ".join((raw_text or "").strip().split())
    lower = text.lower()

    room_match = re.search(r"(\d+\s*x\s*\d+\s*(?:ft|feet|m|meter|metre))", lower)
    budget_match = re.search(r"(rm|myr)\s*([0-9][0-9,]*(?:\.\d+)?)", lower)
    style_match = re.search(r"(minimalist|modern|industrial|scandinavian|classic)", lower)
    location_match = re.search(r"(kuala lumpur|selangor|penang|johor|sabah|sarawak)", lower)

    constraints = []
    for phrase in ("no drilling", "must fit under desk", "quiet", "small footprint", "portable"):
        if phrase in lower:
            constraints.append(phrase)

    budget_value = None
    if budget_match:
        budget_value = float(budget_match.group(2).replace(",", ""))

    return {
        "room_size": room_match.group(1) if room_match else None,
        "budget": budget_value,
        "currency": budget_match.group(1).upper() if budget_match else "RM",
        "style": style_match.group(1) if style_match else None,
        "explicit_constraints": constraints,
        "location": location_match.group(1).title() if location_match else "Kuala Lumpur",
        "source_chars": len(text),
    }


def parse_requirement_file(content: bytes, filename: str) -> dict:
    text = _extract_text_from_bytes(content, filename)
    return parse_requirement_text(text)
