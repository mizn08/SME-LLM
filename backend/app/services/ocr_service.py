"""Invoice / receipt OCR (Tesseract) with quality checks — rejects garbage output."""

from __future__ import annotations

import io
import os
import re
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

# Realistic invoice line amounts (RM)
_MIN_AMOUNT = 0.50
_MAX_AMOUNT = 2_000_000.0


def text_quality_score(text: str) -> float:
    """Share of characters that look like normal invoice text (ASCII letters/digits/punct)."""
    if not text:
        return 0.0
    good = sum(
        1
        for c in text
        if c.isascii() and (c.isalnum() or c in " .,/-:$%()#@'\n\r\t")
    )
    return good / len(text)


def is_garbage_text(text: str) -> bool:
    if len(text.strip()) < 8:
        return True
    if text_quality_score(text) < 0.78:
        return True
    non_ascii = sum(1 for c in text if ord(c) > 127)
    if non_ascii / max(len(text), 1) > 0.03:
        return True
    # Too few real words
    words = re.findall(r"[A-Za-z]{3,}", text)
    if len(words) < 2 and len(text) > 40:
        return True
    return False


def is_readable_description(desc: str) -> bool:
    desc = (desc or "").strip()
    if "SST" in desc.upper():
        return True
    if len(desc) < 4:
        return False
    letters = sum(c.isalpha() for c in desc)
    if letters / len(desc) < 0.35 and "RM" not in desc.upper():
        return False
    if sum(1 for c in desc if ord(c) > 127) > 1:
        return False
    if re.search(r"[^\x00-\x7F]{3,}", desc):
        return False
    return True


def sniff_file_kind(raw: bytes) -> str:
    if raw[:4] == b"%PDF":
        return "pdf"
    if raw[:2] == b"PK":
        return "zip"
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if raw[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if raw[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if raw[:2] == b"BM":
        return "bmp"
    if raw[:4] == b"RIFF" and len(raw) > 12 and raw[8:12] == b"WEBP":
        return "webp"
    return "unknown"


def _configure_tesseract(pytesseract: Any) -> str | None:
    """Point pytesseract at the Tesseract binary (Windows often lacks PATH after install)."""
    env_cmd = (os.environ.get("TESSERACT_CMD") or "").strip()
    if env_cmd and Path(env_cmd).is_file():
        pytesseract.pytesseract.tesseract_cmd = env_cmd
        return env_cmd

    found = shutil.which("tesseract")
    if found:
        pytesseract.pytesseract.tesseract_cmd = found
        return found

    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        Path("/usr/bin/tesseract"),
        Path("/usr/local/bin/tesseract"),
        Path("/opt/homebrew/bin/tesseract"),
    ]
    for path in candidates:
        if path.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(path)
            return str(path)
    return None


def _preprocess_image(img: Any) -> Any:
    from PIL import Image, ImageOps

    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    # Upscale small scans for better OCR
    w, h = img.size
    if max(w, h) < 1200:
        scale = 1200 / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)))
    return img


def extract_invoice_text(image_bytes: bytes) -> dict[str, Any]:
    kind = sniff_file_kind(image_bytes)
    if kind in ("pdf", "zip", "unknown"):
        return {
            "text": "",
            "parsed_rows": [],
            "error": "not_an_image",
            "hint": "This file is not a photo/scan. Use PDF/CSV import or upload a JPG/PNG invoice image.",
            "engine": "rejected",
            "quality_score": 0.0,
        }

    try:
        from PIL import Image
        import pytesseract
    except ImportError as exc:
        return {
            "text": "",
            "error": f"OCR dependencies missing: {exc}",
            "parsed_rows": [],
            "engine": "none",
            "hint": "Run: pip install -r backend/requirements-v3-ocr.txt",
        }

    if not _configure_tesseract(pytesseract):
        return {
            "text": "",
            "error": "tesseract_not_found",
            "parsed_rows": [],
            "engine": "none",
            "hint": (
                "Install Tesseract OCR (winget install UB-Mannheim.TesseractOCR), "
                "then restart the API. Or set TESSERACT_CMD to tesseract.exe."
            ),
        }

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
        img = _preprocess_image(img)
        config = "--psm 6 -l eng"
        text = pytesseract.image_to_string(img, config=config)
    except Exception as exc:  # noqa: BLE001
        return {
            "text": "",
            "error": str(exc),
            "parsed_rows": [],
            "hint": "Could not read image — try a clearer photo or export PDF as CSV.",
            "engine": "tesseract",
        }

    text = (text or "").strip()
    quality = text_quality_score(text)
    if is_garbage_text(text):
        return {
            "text": text[:500],
            "parsed_rows": [],
            "error": "ocr_low_quality",
            "hint": (
                "OCR quality too low (blurry scan, wrong file type, or encrypted PDF saved as image). "
                "Try: a sharp JPG/PNG photo, or upload a CSV export from your accounting app."
            ),
            "engine": "tesseract",
            "quality_score": round(quality, 2),
        }

    rows = _heuristic_parse(text)
    return {
        "text": text,
        "parsed_rows": rows,
        "engine": "tesseract",
        "quality_score": round(quality, 2),
    }


def _heuristic_parse(text: str) -> list[dict[str, Any]]:
    if is_garbage_text(text):
        return []
    rows: list[dict[str, Any]] = []
    # Require RM + proper money (always sen .XX) — blocks junk like "Rm9" from OCR noise
    amount_re = re.compile(
        r"\bRM\s*((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2}))\b",
        re.I,
    )
    date_re = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b")
    for line in text.splitlines():
        line = line.strip()
        if len(line) < 6:
            continue
        am = amount_re.search(line)
        if not am:
            continue
        try:
            amt = float(am.group(1).replace(",", ""))
        except ValueError:
            continue
        if amt < _MIN_AMOUNT or amt > _MAX_AMOUNT:
            continue
        desc = _normalize_description(line[:120])
        if not is_readable_description(desc):
            continue
        # Skip tiny amounts on junk lines unless line looks like a total/invoice
        low = desc.lower()
        if amt < 10 and not any(w in low for w in ("total", "amount", "due", "grand", "invoice", "paid")):
            continue
        dt = date_re.search(line)
        rows.append(
            {
                "txn_date": dt.group(1) if dt else None,
                "amount_rm": amt,
                "category": "invoice",
                "description": desc,
                "is_expense": True,
            }
        )
    return rows[:50]


def _normalize_description(desc: str) -> str:
    desc = (desc or "").strip()
    # Drop OCR noise at line start (punctuation fragments).
    desc = re.sub(r"^[^A-Za-z0-9]+", "", desc)
    # Normalize separators for readability.
    desc = re.sub(r"\s*[:|]\s*", " - ", desc)
    desc = re.sub(r"\s+", " ", desc).strip()

    low = desc.lower()
    if "grand total" in low:
        return "Grand total"
    if "subtotal" in low:
        return "Subtotal"
    if "sst" in low:
        return "SST"
    if "total due" in low:
        return "Total due"
    return desc[:120]


def rows_to_csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b"txn_date,amount_rm,category,description,is_expense\n"
    df = pd.DataFrame(rows)
    for col in ("txn_date", "amount_rm", "category", "description", "is_expense"):
        if col not in df.columns:
            df[col] = None
    return df.to_csv(index=False).encode("utf-8")
