"""Pre-computed analytics for RAG — synced with Health dashboard KPIs."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services import decision_engine
from app.services.financing_recommendation_service import (
    build_recommendation,
    resolve_purchase_scenario,
)
from app.services.sme_financial_snapshot import format_dashboard_block, get_snapshot


def _bnpl_instalments(db: Session, purchase_rm: float, top_n: int = 3) -> list[dict[str, Any]]:
    from app.models.bnpl import BNPLOffer

    rows: list[dict[str, Any]] = []
    for offer in db.query(BNPLOffer).all():
        if purchase_rm > offer.max_amount_rm:
            continue
        tenure = min(6, offer.max_tenure_months) or 3
        extra = decision_engine._bnpl_effective_cost(offer, purchase_rm, tenure)  # noqa: SLF001
        monthly = round((purchase_rm + extra) / tenure, 2)
        rows.append(
            {
                "product": offer.name,
                "provider": offer.provider,
                "tenure_months": tenure,
                "monthly_instalment_rm": monthly,
                "total_cost_rm": round(purchase_rm + extra, 2),
            }
        )
    rows.sort(key=lambda r: r["monthly_instalment_rm"])
    return rows[:top_n]


def _roi_estimate(purchase_rm: float, trailing_annual_rm: float, category: str) -> dict[str, Any]:
    uplift = {
        "digital": 0.08,
        "pos": 0.08,
        "equipment": 0.05,
        "software": 0.06,
        "agro": 0.04,
        "fnb": 0.06,
        "retail": 0.06,
    }.get(category, 0.05)
    base = trailing_annual_rm if trailing_annual_rm > 0 else 0.0
    annual_benefit = round(base * uplift, 2)
    monthly_benefit = round(annual_benefit / 12.0, 2) if annual_benefit else 0.0
    payback = round(purchase_rm / monthly_benefit, 1) if monthly_benefit > 0 else None
    roi_12m = round(((annual_benefit - purchase_rm) / purchase_rm) * 100.0, 1) if purchase_rm > 0 else 0.0
    return {
        "assumed_annual_uplift_pct": round(uplift * 100, 1),
        "trailing_annual_revenue_rm": base,
        "projected_annual_benefit_rm": annual_benefit,
        "payback_months": payback,
        "roi_12_month_pct": roi_12m,
    }


def build_analytics_context(
    db: Session,
    sme_id: int,
    question: str,
    *,
    purchase_amount: float | None = None,
    purchase_category: str | None = None,
    brief: bool = False,
) -> str:
    snap = get_snapshot(db, sme_id)
    amount, category = resolve_purchase_scenario(
        question, purchase_amount=purchase_amount, purchase_category=purchase_category
    )
    rec = build_recommendation(
        db, sme_id, purchase_amount=amount, purchase_category=category
    )
    k = snap["kpis"]
    if brief:
        return (
            "=== OPTIONAL SME DATA (only if user asks about their business) ===\n"
            f"Business: {snap['business_name']} | Health {snap['health']['health_score']}/100 | "
            f"90d net RM {k['net_operating_cash_rm']:,.2f} | runway {k['days_cash_on_hand']:.0f} days"
        )
    lines = [
        "=== COMPUTED ANALYTICS (same source as Health tab — cite exactly) ===",
        f"Business: {snap['business_name']} | Industry: {snap['industry']}",
        (
            f"KPIs: ratio {k['current_ratio']:.2f}, days cash {k['days_cash_on_hand']:.1f}, "
            f"burn RM {k['burn_rate_monthly_rm']:,.2f}, 90d net RM {k['net_operating_cash_rm']:,.2f}"
        ),
        (
            f"Weekly net RM {snap['weekly']['net_rm']:,.2f} ({snap['weekly']['txn_count']} txns) | "
            f"Health {snap['health']['health_score']}/100"
        ),
        f"Trailing 12m revenue from transactions: RM {snap['trailing_annual_revenue_rm']:,.2f}",
    ]
    for r in rec.get("reasons", []):
        lines.append(f"Reason: {r}")
    if amount is not None and category:
        roi = _roi_estimate(amount, snap["trailing_annual_revenue_rm"], category)
        lines.append(
            f"Purchase RM {amount:,.0f} ({category}): ROI {roi['roi_12_month_pct']:.1f}%, "
            f"payback {roi['payback_months']} mo (uplift {roi['assumed_annual_uplift_pct']:.1f}% on trailing revenue)"
        )
    return "\n".join(lines)


def build_analytics_answer(
    db: Session,
    sme_id: int,
    question: str,
    lang: str = "en",
    *,
    purchase_amount: float | None = None,
    purchase_category: str | None = None,
) -> str:
    amount, category = resolve_purchase_scenario(
        question, purchase_amount=purchase_amount, purchase_category=purchase_category
    )
    rec = build_recommendation(
        db, sme_id, purchase_amount=amount, purchase_category=category, lang=lang
    )
    snap = rec["snapshot"]
    parts = [rec["star_line"], "", format_dashboard_block(snap, lang), ""]

    if lang == "ms":
        parts.append("**Mengapa:**")
    else:
        parts.append("**Why this recommendation:**")
    for r in rec.get("reasons", []):
        parts.append(f"• {r}")
    parts.append("")

    fc = snap["forecast"]
    if lang == "ms":
        parts.append("**Ramalan 6 bulan (model sama seperti Health):**")
    else:
        parts.append("**6-month forecast (same model as Health chart):**")
    for pt in fc.get("forecast_months", [])[:6]:
        parts.append(f"• Month +{pt['month_offset']}: net RM {pt['projected_net_rm']:,.2f}")
    if fc.get("alert"):
        parts.append(f"• **Alert:** {fc['alert']}")
    parts.append("")

    if amount is not None and category:
        roi = _roi_estimate(amount, snap["trailing_annual_revenue_rm"], category)
        if lang == "ms":
            parts.append("**ROI (daripada transaksi anda, bukan anggaran profil):**")
        else:
            parts.append("**ROI (from your transactions, not profile guess):**")
        parts.append(
            f"• RM {amount:,.0f} {category}: **{roi['roi_12_month_pct']:.1f}%** over 12 months, "
            f"payback **{roi['payback_months']} months** "
            f"(based on trailing revenue RM {roi['trailing_annual_revenue_rm']:,.0f})"
        )
        bnpl = _bnpl_instalments(db, amount)
        if bnpl:
            parts.append("")
            if lang == "ms":
                parts.append("**BNPL (kiraan deterministik):**")
            else:
                parts.append("**BNPL (deterministic maths):**")
            for b in bnpl[:2]:
                parts.append(
                    f"• **{b['product']}**: RM {b['monthly_instalment_rm']:,.2f}/mo × {b['tenure_months']} mo"
                )
            ceil = rec.get("affordable_monthly_rm")
            if ceil:
                parts.append(
                    f"• Affordable ceiling (~12% avg monthly revenue): **RM {ceil:,.0f}/month**"
                    if lang == "en"
                    else f"• Siling mampu bayar: **RM {ceil:,.0f}/bulan**"
                )
    else:
        parts.append(
            "• Set purchase amount in **Simulate** (e.g. RM 50,000 equipment) — "
            "AI Advisor will use that figure for ROI and BNPL maths."
            if lang == "en"
            else "• Tetapkan jumlah di **Simulate** untuk ROI dan BNPL."
        )

    return "\n".join(parts)


def star_recommendation_fallback(
    db: Session,
    sme_id: int,
    question: str,
    lang: str = "en",
    *,
    purchase_amount: float | None = None,
    purchase_category: str | None = None,
) -> str:
    amount, category = resolve_purchase_scenario(
        question, purchase_amount=purchase_amount, purchase_category=purchase_category
    )
    rec = build_recommendation(
        db, sme_id, purchase_amount=amount, purchase_category=category, lang=lang
    )
    return rec["star_line"]
