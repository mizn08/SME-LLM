from __future__ import annotations

import io
from pathlib import Path
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.sme import SMEProfile
from app.models.transaction import FinancialTransaction
from app.services import data_processor, rag_service

router = APIRouter(tags=["upload"])

_TABULAR_SUFFIXES = {".csv", ".tsv", ".txt", ".xlsx", ".xls"}


def _save_upload_file(sme_id: int, filename: str, raw_bytes: bytes) -> Path:
    settings = get_settings()
    dest_dir = Path(settings.UPLOAD_DIR) / str(sme_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename or "upload").name
    dest = dest_dir / safe_name
    dest.write_bytes(raw_bytes)
    return dest


def _upload_dir(sme_id: int) -> Path:
    return Path(get_settings().UPLOAD_DIR) / str(sme_id)


def _try_read_tabular(raw_bytes: bytes, filename: str) -> pd.DataFrame | None:
    """Best-effort parse; returns None if format is not tabular yet."""
    suffix = Path(filename or "").suffix.lower()
    buf = io.BytesIO(raw_bytes)

    if suffix in (".xlsx", ".xls"):
        try:
            return pd.read_excel(buf)
        except Exception:
            return None

    for sep in (",", "\t", None):
        try:
            buf.seek(0)
            if sep is None:
                return pd.read_csv(buf, sep=None, engine="python")
            return pd.read_csv(buf, sep=sep)
        except Exception:
            continue

    if suffix in (".csv", ".tsv", ".txt") or b"," in raw_bytes[:4096] or b"\t" in raw_bytes[:4096]:
        try:
            buf.seek(0)
            return pd.read_csv(buf, sep=None, engine="python")
        except Exception:
            return None
    return None


def _default_is_expense(filename: str) -> bool | None:
    low = filename.lower()
    if "expense" in low or "debit" in low or "outflow" in low:
        return True
    if "income" in low or "revenue" in low or "inflow" in low or "credit" in low:
        return False
    return None


def _persist_transactions(
    db: Session,
    sme_id: int,
    df: pd.DataFrame,
) -> tuple[int, dict[str, float]]:
    db.query(FinancialTransaction).filter(FinancialTransaction.sme_id == sme_id).delete()
    rows = []
    for _, row in df.iterrows():
        rows.append(
            FinancialTransaction(
                sme_id=sme_id,
                txn_date=row["txn_date"],
                amount_rm=float(row["amount_rm"]),
                category=str(row["category"]),
                description=str(row.get("description") or ""),
                is_expense=bool(row["is_expense"]),
            )
        )
    db.bulk_save_objects(rows)
    kpis = data_processor.compute_kpis_from_transactions(df)
    data_processor.persist_snapshot(db, sme_id, kpis)
    db.commit()
    rag_service.invalidate_rag_cache(sme_id)
    return len(rows), kpis


def reprocess_saved_uploads(db: Session, sme_id: int) -> dict:
    """Import all tabular files saved for this SME (merge Income + Expenses, etc.)."""
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")

    upload_dir = _upload_dir(sme_id)
    if not upload_dir.is_dir():
        raise HTTPException(404, "No uploads found for this SME.")

    frames: list[tuple[pd.DataFrame, str]] = []
    skipped: list[str] = []
    for path in sorted(upload_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in _TABULAR_SUFFIXES:
            continue
        raw_bytes = path.read_bytes()
        raw_df = _try_read_tabular(raw_bytes, path.name)
        if raw_df is None or raw_df.empty:
            skipped.append(path.name)
            continue
        frames.append((raw_df, path.name))

    if not frames:
        raise HTTPException(
            400,
            "No tabular uploads to import. Upload CSV or Excel files first.",
        )

    merged, report = data_processor.merge_upload_frames(frames)
    if merged.empty:
        raise HTTPException(400, "No valid transaction rows after cleaning.")

    count, kpis = _persist_transactions(db, sme_id, merged)
    if skipped:
        report.append(f"Skipped non-tabular files: {', '.join(skipped)}")
    return {
        "sme_id": sme_id,
        "status": "imported",
        "transactions_imported": count,
        "files_processed": [name for _, name in frames],
        "cleaning_report": report,
        "kpis": kpis,
    }


def _import_single_file(
    db: Session,
    sme_id: int,
    raw_df: pd.DataFrame,
    filename: str,
) -> tuple[int, list[str], dict[str, float]]:
    cleaned, report = data_processor.clean_csv_dataframe(
        raw_df,
        default_is_expense=_default_is_expense(filename),
    )
    count, kpis = _persist_transactions(db, sme_id, cleaned)
    return count, report, kpis


@router.post("/sme/{sme_id}/reprocess-uploads")
def reprocess_uploads(sme_id: int, db: Session = Depends(get_db)):
    """Re-import all saved uploads for this SME (use after column-mapping fix or multiple files)."""
    return reprocess_saved_uploads(db, sme_id)


@router.post("/upload-csv")
@router.post("/upload")
async def upload_data_file(
    sme_id: Annotated[int, Form()],
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Accept any file type — store on server; import tabular data when possible."""
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")

    filename = file.filename or "upload"
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(400, "Empty file.")

    saved_path = _save_upload_file(sme_id, filename, raw_bytes)
    report: list[str] = [
        f"Saved {filename} ({len(raw_bytes):,} bytes) to {saved_path.as_posix()}.",
    ]

    raw_df = _try_read_tabular(raw_bytes, filename)
    if raw_df is None or raw_df.empty:
        return {
            "sme_id": sme_id,
            "status": "stored",
            "file_name": filename,
            "stored_path": saved_path.as_posix(),
            "transactions_imported": 0,
            "cleaning_report": report
            + [
                "File accepted. Server-side preprocessing will map columns and refresh KPIs.",
            ],
            "kpis": None,
        }

    try:
        count, clean_report, kpis = _import_single_file(db, sme_id, raw_df, filename)
        report.extend(clean_report)
        return {
            "sme_id": sme_id,
            "status": "imported",
            "file_name": filename,
            "stored_path": saved_path.as_posix(),
            "transactions_imported": count,
            "cleaning_report": report,
            "kpis": kpis,
        }
    except ValueError:
        db.rollback()
        try:
            merged_result = reprocess_saved_uploads(db, sme_id)
            merged_result["file_name"] = filename
            merged_result["stored_path"] = saved_path.as_posix()
            merged_result["cleaning_report"] = report + list(merged_result.get("cleaning_report", []))
            return merged_result
        except HTTPException:
            db.rollback()
        except ValueError as exc:
            db.rollback()
            return {
                "sme_id": sme_id,
                "status": "stored",
                "file_name": filename,
                "stored_path": saved_path.as_posix(),
                "transactions_imported": 0,
                "cleaning_report": report
                + [
                    f"Could not auto-map columns yet ({exc}).",
                    "Tap “Import saved files” or upload again after fixing headers.",
                ],
                "kpis": None,
            }
