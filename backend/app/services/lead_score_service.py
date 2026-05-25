"""Lead scoring for BNPL, micro-credit, and grant products."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas import LeadScoreItem
from app.services import data_processor, forecast_service


def compute_lead_scores(db: Session, sme_id: int) -> list[LeadScoreItem]:
    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    fc = forecast_service.forecast_runway(db, sme_id)
    runway = float(fc.get("runway_days_est") or kpis.get("days_cash_on_hand", 45))
    ratio = float(kpis.get("current_ratio", 1))
    burn = float(kpis.get("burn_rate_monthly_rm", 0))
    revenue = float(kpis.get("revenue_mtd_rm", 0))

    scores: list[LeadScoreItem] = []

    # BNPL — best when cash is tight but business is operating
    bnpl = 50
    reasons_bnpl: list[str] = []
    if runway < 90:
        bnpl += 20
        reasons_bnpl.append("BNPL preserves cash for runway under 90 days")
    if ratio >= 1.0:
        bnpl += 15
        reasons_bnpl.append("Positive liquidity ratio supports repayment")
    if burn > 0 and revenue > burn * 0.8:
        bnpl += 10
        reasons_bnpl.append("Revenue covers most monthly burn")
    if runway < 30:
        bnpl -= 15
        reasons_bnpl.append("Very low runway — confirm BNPL instalments are affordable")
    scores.append(
        LeadScoreItem(
            product_type="bnpl",
            product_name="BNPL (Pay-in-3 / PayLater)",
            score=max(0, min(100, bnpl)),
            reasons=reasons_bnpl or ["Moderate fit for equipment and digital purchases"],
        )
    )

    # Micro-credit
    mc = 40
    reasons_mc: list[str] = []
    if runway < 60:
        mc += 25
        reasons_mc.append("Micro-credit suits bridging cash gaps under 60-day runway")
    if ratio < 1.2:
        mc += 15
        reasons_mc.append("Working capital loan can stabilise liquidity")
    if burn > 5000:
        mc += 10
        reasons_mc.append("Meaningful monthly burn warrants structured credit")
    scores.append(
        LeadScoreItem(
            product_type="micro_credit",
            product_name="TEKUN / CGC Micro Credit",
            score=max(0, min(100, mc)),
            reasons=reasons_mc or ["Consider if you need lump-sum working capital"],
        )
    )

    # Grant
    gr = 35
    reasons_gr: list[str] = []
    if ratio >= 1.0:
        gr += 20
        reasons_gr.append("Stable operations align with grant compliance")
    if revenue > 10000:
        gr += 15
        reasons_gr.append("Revenue level supports grant reporting requirements")
    if runway >= 45:
        gr += 15
        reasons_gr.append("Adequate runway allows time for grant disbursement")
    scores.append(
        LeadScoreItem(
            product_type="grant",
            product_name="MDEC / MATRADE Grants",
            score=max(0, min(100, gr)),
            reasons=reasons_gr or ["Check sector-specific grant schemes"],
        )
    )

    return scores
