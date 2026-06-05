"""Extract text / transaction rows from any uploaded document (invoice OCR path)."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

import pandas as pd

from app.services.ocr_service import (
    _heuristic_parse,
    extract_invoice_text,
    is_garbage_text,
    rows_to_csv_bytes,
    sniff_file_kind,
    text_quality_score,
)
from app.services.requirement_parser_service import _extract_text_from_bytes


def _suffix(filename: str) -> str:
    return Path(filename or "upload").suffix.lower()


def _rows_from_dataframe(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    low_cols = {str(c).strip().lower(): c for c in df.columns}
    date_col = next(
        (low_cols[k] for k in low_cols if k in ("txn_date", "date", "date_time", "transaction date")),
        None,
    )
    amount_col = next(
        (low_cols[k] for k in low_cols if k in ("amount_rm", "amount", "value", "debit", "credit")),
        None,
    )
    cat_col = next((low_cols[k] for k in low_cols if k in ("category", "type", "description")), None)
    rows: list[dict[str, Any]] = []
    for _, row in df.head(100).iterrows():
        amt = None
        if amount_col is not None:
            try:
                amt = float(str(row[amount_col]).replace(",", "").replace("RM", "").strip())
            except (TypeError, ValueError):
                continue
        if amt is None:
            continue
        desc = str(row[cat_col])[:120] if cat_col is not None else "imported row"
        rows.append(
            {
                "txn_date": str(row[date_col])[:10] if date_col is not None else None,
                "amount_rm": abs(amt),
                "category": str(row[cat_col])[:80] if cat_col is not None else "imported",
                "description": desc,
                "is_expense": amt < 0 if amount_col and "credit" not in str(amount_col).lower() else True,
            }
        )
    return rows


def _try_read_tabular(raw: bytes, filename: str) -> pd.DataFrame | None:
    suffix = _suffix(filename)
    buf = io.BytesIO(raw)
    if suffix in (".xlsx", ".xls") or (raw[:2] == b"PK" and suffix in (".xlsx", ".xls", "")):
        try:
            return pd.read_excel(buf)
        except Exception:
            pass
    for sep in (",", "\t", None):
        try:
            buf.seek(0)
            if sep is None:
                df = pd.read_csv(buf, sep=None, engine="python")
            else:
                df = pd.read_csv(buf, sep=sep)
            if df is not None and not df.empty and len(df.columns) >= 2:
                return df
        except Exception:
            continue
    if suffix in (".csv", ".tsv", ".txt") or b"," in raw[:4096] or b"\t" in raw[:4096]:
        try:
            buf.seek(0)
            return pd.read_csv(buf, sep=None, engine="python")
        except Exception:
            return None
    return None


def _parse_text_document(text: str, engine: str, file_type: str) -> dict[str, Any]:
    text = (text or "").strip()
    warnings: list[str] = []
    if is_garbage_text(text):
        return {
            "text": text[:800],
            "parsed_rows": [],
            "engine": engine,
            "file_type": file_type,
            "warnings": ["text_low_quality"],
            "quality_score": round(text_quality_score(text), 2),
            "hint": (
                "Could not read useful text from this file. "
                "For scans use a clear JPG/PNG; for statements use CSV with amount_rm column."
            ),
        }
    rows = _heuristic_parse(text)
    return {
        "text": text[:8000],
        "parsed_rows": rows,
        "engine": engine,
        "file_type": file_type,
        "warnings": warnings if rows else ["no_rm_amounts_found"],
        "quality_score": round(text_quality_score(text), 2),
        "hint": None if rows else "No RM amounts found — check the file has totals like RM 120.50",
    }


def extract_from_upload(raw: bytes, filename: str = "upload") -> dict[str, Any]:
    """Accept any file; return text + parsed_rows when quality is good enough."""
    if not raw:
        return {"text": "", "parsed_rows": [], "error": "empty_file", "engine": "none"}

    name = Path(filename or "upload").name
    suffix = _suffix(name)
    kind = sniff_file_kind(raw)

    # Tabular first (best for bank exports)
    df = _try_read_tabular(raw, name)
    if df is not None and not df.empty:
        rows = _rows_from_dataframe(df)
        return {
            "text": df.head(20).to_string(),
            "parsed_rows": rows,
            "engine": "tabular",
            "file_type": suffix or "tabular",
            "quality_score": 1.0,
            "hint": "Tabular import OK — review on Health tab before syncing.",
        }

    # PDF — text layer only (never OCR binary PDF bytes)
    if kind == "pdf" or suffix == ".pdf":
        text = _extract_text_from_bytes(raw, name)
        out = _parse_text_document(text, "pdf_text", "pdf")
        if not out["parsed_rows"]:
            out["hint"] = (
                out.get("hint")
                or "PDF has little text (maybe scanned). Save pages as JPG or export CSV from your bank."
            )
        return out

    # Word
    if suffix == ".docx" or (kind == "zip" and name.lower().endswith(".docx")):
        text = _extract_text_from_bytes(raw, name)
        return _parse_text_document(text, "docx", "docx")

    # Excel in zip
    if suffix in (".xlsx", ".xls"):
        df = _try_read_tabular(raw, name)
        if df is not None and not df.empty:
            rows = _rows_from_dataframe(df)
            return {
                "text": df.head(20).to_string(),
                "parsed_rows": rows,
                "engine": "excel",
                "file_type": suffix,
                "quality_score": 1.0,
            }

    # Plain text
    if suffix in (".txt", ".json", ".md", ".log"):
        text = raw.decode("utf-8", errors="ignore")
        return _parse_text_document(text, "text", suffix)

    # Images only — real image magic bytes
    if kind in ("png", "jpeg", "gif", "bmp", "webp") or suffix in (
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".gif",
        ".tif",
        ".tiff",
    ):
        ocr = extract_invoice_text(raw)
        hint = ocr.get("hint")
        rows = ocr.get("parsed_rows") or []
        return {
            **ocr,
            "file_type": kind or suffix,
            "parsed_rows": rows,
            "hint": hint,
        }

    return {
        "text": "",
        "parsed_rows": [],
        "engine": "unsupported",
        "file_type": suffix or kind,
        "quality_score": 0.0,
        "hint": (
            f"File type '{suffix or kind}' not supported for OCR. "
            "Use CSV/Excel (best), searchable PDF, or JPG/PNG photo of invoice."
        ),
    }
