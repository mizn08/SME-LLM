"""Industry peer benchmarking with P25/P50/P75 bands."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.sme import SMEProfile
from app.schemas import BenchmarkMetric, BenchmarkResponse
from app.services import data_processor

_INDUSTRY: dict[str, dict[str, tuple[float, float, float, float, str]]] = {
    "Food & Beverage": {
        "Monthly revenue (RM)": (28000, 45000, 72000, 120000, "RM"),
        "Gross margin %": (22, 35, 48, 60, "%"),
        "Monthly burn (RM)": (22000, 32000, 48000, 65000, "RM"),
        "Current ratio": (0.85, 1.15, 1.45, 1.8, "x"),
    },
    "Agriculture": {
        "Monthly revenue (RM)": (18000, 28000, 42000, 65000, "RM"),
        "Gross margin %": (18, 28, 38, 50, "%"),
        "Monthly burn (RM)": (15000, 22000, 35000, 48000, "RM"),
        "Current ratio": (0.8, 1.05, 1.3, 1.6, "x"),
    },
    "Technology": {
        "Monthly revenue (RM)": (42000, 65000, 95000, 150000, "RM"),
        "Gross margin %": (40, 55, 68, 78, "%"),
        "Monthly burn (RM)": (35000, 48000, 72000, 95000, "RM"),
        "Current ratio": (0.9, 1.25, 1.55, 2.0, "x"),
    },
}


def _normalize_industry(industry: str) -> str:
    low = industry.lower()
    if "food" in low or "beverage" in low or "f&b" in low:
        return "Food & Beverage"
    if "agri" in low or "farm" in low:
        return "Agriculture"
    if "tech" in low or "digital" in low or "software" in low:
        return "Technology"
    return "Food & Beverage"


def _percentile(val: float, p25: float, p50: float, p75: float) -> int:
    if val <= p25:
        return 25
    if val <= p50:
        return 50
    if val <= p75:
        return 75
    return 90


def get_benchmark(db: Session, sme_id: int) -> BenchmarkResponse:
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    industry = _normalize_industry(sme.industry if sme else "SME")
    bands = _INDUSTRY.get(industry, _INDUSTRY["Food & Beverage"])

    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    revenue = float(kpis.get("revenue_mtd_rm", 0))
    burn = float(kpis.get("burn_rate_monthly_rm", 0))
    margin_pct = max(0, ((revenue - burn) / revenue * 100)) if revenue > 0 else 0
    ratio = float(kpis.get("current_ratio", 1))

    sme_vals = {
        "Monthly revenue (RM)": revenue,
        "Gross margin %": round(margin_pct, 1),
        "Monthly burn (RM)": burn,
        "Current ratio": round(ratio, 2),
    }

    metrics: list[BenchmarkMetric] = []
    above = 0
    for label, (p25, p50, p75, _p90, unit) in bands.items():
        val = sme_vals[label]
        pct = _percentile(val, p25, p50, p75)
        metrics.append(
            BenchmarkMetric(
                label=label,
                sme_value=round(val, 2),
                industry_median=p50,
                industry_p25=p25,
                industry_p75=p75,
                percentile=pct,
                unit=unit,
            )
        )
        if label == "Monthly burn (RM)":
            if val <= p50:
                above += 1
        elif val >= p50:
            above += 1

    summary = (
        f"vs {industry} peers (P25/P50/P75): you rank at or above median on "
        f"{above} of {len(metrics)} metrics. Lower burn and higher margin improve competitiveness."
    )
    return BenchmarkResponse(sme_id=sme_id, industry=industry, metrics=metrics, summary=summary)
