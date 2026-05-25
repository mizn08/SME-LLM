"""Audience-specific report payloads for PDF generation."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.sme import SMEProfile
from app.services import (
    benchmark_service,
    data_processor,
    forecast_service,
    fraud_service,
    grant_eligibility_service,
    health_score_service,
    unsupervised_service,
)


def build_report(db: Session, sme_id: int, audience: str = "bank") -> dict[str, Any]:
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        return {"error": "SME not found"}

    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    fc = forecast_service.forecast_runway(db, sme_id)
    anomalies = unsupervised_service.detect_anomalies(db, sme_id)
    health = health_score_service.compute_health_score(
        kpis, fc.get("runway_days_est"), int(anomalies.get("total_flagged") or 0)
    )
    grants = grant_eligibility_service.match_grants(db, sme_id=sme_id)
    bench = benchmark_service.get_benchmark(db, sme_id)
    fraud = fraud_service.scan_transactions(db, sme_id)

    base = {
        "sme_id": sme_id,
        "business_name": sme.business_name,
        "industry": sme.industry,
        "audience": audience,
        "health": health,
        "kpis": kpis,
        "forecast": fc,
        "generated_at": "2026-05-26",
    }

    if audience == "bank":
        return {
            **base,
            "title": "Financing Application Summary",
            "sections": ["Executive summary", "KPIs", "Cash forecast", "Peer benchmark", "Risk scan"],
            "benchmark_summary": bench.summary,
            "fraud_summary": fraud.get("risk_summary"),
            "grant_matches": grants[:5],
            "recommendation": "Suitable for staged BNPL or micro-credit based on runway and ratio.",
        }
    if audience == "board":
        return {
            **base,
            "title": "Board Meeting Pack",
            "sections": ["KPI dashboard", "Anomalies", "Grant pipeline", "Forecast"],
            "anomaly_count": anomalies.get("total_flagged", 0),
            "benchmark_metrics": [m.model_dump() for m in bench.metrics],
        }
    if audience == "tax":
        return {
            **base,
            "title": "Tax & Expense Summary",
            "sections": ["Expense categories", "SST notes", "Compliance"],
            "compliance": [
                {"item": "SST registration", "status": "review"},
                {"item": "e-Invoice readiness", "status": "in_progress"},
            ],
            "expense_mtd_rm": kpis.get("expense_mtd_rm"),
        }
    return {**base, "title": "SME Advisor Report", "sections": ["Overview"]}
