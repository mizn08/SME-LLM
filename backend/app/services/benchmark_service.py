"""Industry benchmark comparison (hardcoded medians)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.sme import SMEProfile
from app.schemas import BenchmarkMetric, BenchmarkResponse
from app.services import data_processor


_INDUSTRY_MEDIANS: dict[str, dict[str, tuple[float, str]]] = {
    "Food & Beverage": {
        "Monthly revenue (RM)": (45000, "RM"),
        "Gross margin %": (35, "%"),
        "Monthly burn (RM)": (32000, "RM"),
    },
    "Agriculture": {
        "Monthly revenue (RM)": (28000, "RM"),
        "Gross margin %": (28, "%"),
        "Monthly burn (RM)": (22000, "RM"),
    },
    "Technology": {
        "Monthly revenue (RM)": (65000, "RM"),
        "Gross margin %": (55, "%"),
        "Monthly burn (RM)": (48000, "RM"),
    },
}

_DEFAULT = _INDUSTRY_MEDIANS["Food & Beverage"]


def _normalize_industry(industry: str) -> str:
    low = industry.lower()
    if "food" in low or "beverage" in low or "f&b" in low:
        return "Food & Beverage"
    if "agri" in low or "farm" in low:
        return "Agriculture"
    if "tech" in low or "digital" in low or "software" in low:
        return "Technology"
    return "Food & Beverage"


def get_benchmark(db: Session, sme_id: int) -> BenchmarkResponse:
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    industry = _normalize_industry(sme.industry if sme else "SME")
    medians = _INDUSTRY_MEDIANS.get(industry, _DEFAULT)

    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    revenue = float(kpis.get("revenue_mtd_rm", 0))
    burn = float(kpis.get("burn_rate_monthly_rm", 0))
    margin_pct = max(0, ((revenue - burn) / revenue * 100)) if revenue > 0 else 0

    sme_vals = {
        "Monthly revenue (RM)": revenue,
        "Gross margin %": round(margin_pct, 1),
        "Monthly burn (RM)": burn,
    }

    metrics: list[BenchmarkMetric] = []
    above = 0
    below = 0
    for label, (median, unit) in medians.items():
        val = sme_vals[label]
        metrics.append(
            BenchmarkMetric(
                label=label,
                sme_value=round(val, 2),
                industry_median=median,
                unit=unit,
            )
        )
        if label == "Monthly burn (RM)":
            if val < median:
                above += 1
            else:
                below += 1
        elif val >= median:
            above += 1
        else:
            below += 1

    summary = (
        f"You compare favourably on {above} of {len(metrics)} metrics vs {industry} peers. "
        f"Focus on metrics below median to improve competitiveness."
    )
    return BenchmarkResponse(
        sme_id=sme_id,
        industry=industry,
        metrics=metrics,
        summary=summary,
    )
