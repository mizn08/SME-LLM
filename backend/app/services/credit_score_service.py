"""Synthetic SME credit score simulation."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services import data_processor, forecast_service


def _base_score(kpis: dict[str, Any], runway: float) -> int:
    score = 620
    ratio = float(kpis.get("current_ratio", 1))
    if ratio >= 1.5:
        score += 45
    elif ratio >= 1.0:
        score += 20
    else:
        score -= 35
    if runway >= 90:
        score += 40
    elif runway >= 60:
        score += 15
    elif runway < 30:
        score -= 50
    return max(300, min(850, score))


def simulate(db: Session, sme_id: int, scenario: str) -> dict[str, Any]:
    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    fc = forecast_service.forecast_runway(db, sme_id)
    runway = float(fc.get("runway_days_est") or kpis.get("days_cash_on_hand", 60))
    base = _base_score(kpis, runway)

    deltas = {
        "bnpl_purchase": ("Use BNPL for RM5K equipment", 12, "Preserves cash; diversifies credit mix"),
        "micro_credit": ("Take RM20K micro-credit", -18, "Increases utilisation; short-term dip"),
        "grant_only": ("Secure MDEC grant (no debt)", 25, "Improves liquidity without leverage"),
        "late_payment": ("Miss 2 supplier payments", -45, "Payment history deterioration"),
        "reduce_burn": ("Cut burn 15% for 3 months", 30, "Stronger runway and ratio"),
    }
    label, delta, note = deltas.get(scenario, ("Current trajectory", 0, "Baseline"))
    projected = max(300, min(850, base + delta))

    return {
        "sme_id": sme_id,
        "scenario": scenario,
        "scenario_label": label,
        "current_score": base,
        "projected_score": projected,
        "delta": projected - base,
        "grade": _grade(projected),
        "explanation": note,
        "factors": [
            {"name": "Liquidity ratio", "impact": "positive" if kpis.get("current_ratio", 1) >= 1 else "negative"},
            {"name": "Cash runway", "impact": "positive" if runway >= 60 else "negative"},
            {"name": "Scenario", "impact": "positive" if delta >= 0 else "negative"},
        ],
    }


def _grade(score: int) -> str:
    if score >= 750:
        return "A"
    if score >= 680:
        return "B"
    if score >= 600:
        return "C"
    return "D"
