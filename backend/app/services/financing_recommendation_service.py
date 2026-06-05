"""Reasoned financing recommendation — shared by RAG, nudges, and compare."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.sme import SMEProfile
from app.services import compare_service, data_processor, decision_engine
from app.services.sme_financial_snapshot import get_snapshot


def parse_purchase_amount(text: str) -> float | None:
    low = text.lower()
    amounts: list[float] = []
    for m in re.finditer(r"(?:rm|myr)\s*([0-9][0-9,]*(?:\.\d+)?)", low):
        amounts.append(float(m.group(1).replace(",", "")))
    return amounts[-1] if amounts else None


def parse_purchase_category(text: str) -> str | None:
    low = text.lower()
    for cat in ("pos", "digital", "equipment", "software", "agro", "fnb", "retail"):
        if cat in low:
            return cat
    if "point of sale" in low:
        return "digital"
    return None


def normalize_purchase_category(raw: str | None) -> str | None:
    if not raw:
        return None
    low = raw.lower().strip()
    if "digital" in low or "software" in low or "pos" in low:
        return "digital"
    if "equip" in low:
        return "equipment"
    if "market" in low:
        return "retail"
    if "logist" in low:
        return "retail"
    if "agri" in low or "agro" in low:
        return "agro"
    if "suppl" in low:
        return "retail"
    parsed = parse_purchase_category(low)
    return parsed or low.split()[0] if low else None


def resolve_purchase_scenario(
    question: str,
    *,
    purchase_amount: float | None = None,
    purchase_category: str | None = None,
) -> tuple[float | None, str | None]:
    """Simulate-tab amount always wins; never parse RM from chat history blobs."""
    if purchase_amount is not None and purchase_amount > 0:
        cat = normalize_purchase_category(purchase_category) or parse_purchase_category(question) or "equipment"
        return purchase_amount, cat
    from_question = parse_purchase_amount(question)
    amount = from_question
    if amount is not None and amount <= 0:
        amount = None
    cat = parse_purchase_category(question) or normalize_purchase_category(purchase_category)
    if amount is None:
        cat = None
    return amount, cat


def _affordable_monthly(kpis: dict[str, float], avg_monthly_revenue: float) -> float:
    burn = max(float(kpis.get("burn_rate_monthly_rm") or 0), 1.0)
    rev = max(avg_monthly_revenue * 0.12, 0.0)
    return round(max(rev, burn * 0.08, 150.0), 2)


def build_recommendation(
    db: Session,
    sme_id: int,
    *,
    purchase_amount: float | None = None,
    purchase_category: str | None = None,
    lang: str = "en",
) -> dict[str, Any]:
    snap = get_snapshot(db, sme_id)
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        return {"star_line": "**Star recommendation:** Upload transactions on the Health tab.", "reasons": []}

    kpis = snap["kpis"]
    affordable = _affordable_monthly(kpis, snap["avg_monthly_revenue_rm"])
    reasons: list[str] = []

    if purchase_amount is None:
        net = kpis["net_operating_cash_rm"]
        runway = kpis["days_cash_on_hand"]
        if net < 0 and runway < 30:
            star = (
                "**Star recommendation:** **Stabilise cash first** — do not add new financing until "
                f"90-day net cash (currently **RM {net:,.2f}**) improves."
            )
            reasons = [
                f"90-day net cash is **RM {net:,.2f}** (Health tab).",
                f"Runway **{runway:.0f} days** with monthly burn **RM {kpis['burn_rate_monthly_rm']:,.2f}**.",
                "Set a purchase amount in **Simulate** to compare BNPL vs grant for a specific item.",
            ]
        else:
            star = (
                "**Star recommendation:** Use **Simulate** with your exact purchase amount — "
                "advice will cite the same KPIs as your Health tab."
            )
            reasons = [
                f"Health score **{snap['health']['health_score']}/100**; net cash **RM {net:,.2f}**.",
                "No purchase amount in your question — ROI and instalment math need a specific RM figure.",
            ]
        return {
            "star_line": star,
            "reasons": reasons,
            "snapshot": snap,
            "purchase_amount": None,
            "purchase_category": None,
            "decision": None,
        }

    category = normalize_purchase_category(purchase_category) or "equipment"
    decision = decision_engine.decide(db, sme, kpis, purchase_amount, category, None)
    compare = compare_service.compare_financing(db, sme, purchase_amount, category)

    star = f"**Star recommendation:** **{decision.recommendation_type}** — {decision.product_name}."
    reasons.append(decision.explanation)

    if kpis["days_cash_on_hand"] < 30:
        reasons.append(
            f"Runway is **{kpis['days_cash_on_hand']:.0f} days** — repayable options add risk when burn is "
            f"**RM {kpis['burn_rate_monthly_rm']:,.2f}/month**."
        )
    reasons.append(
        f"Affordable instalment ceiling (12% avg monthly revenue): about **RM {affordable:,.0f}/month** "
        f"(avg revenue **RM {snap['avg_monthly_revenue_rm']:,.0f}/mo** from your transactions)."
    )

    grants = [o for o in compare.get("options", []) if o["type"] == "Grant"]
    if grants and decision.recommendation_type != "Grant":
        g = grants[0]
        reasons.append(
            f"Grant **{g['product_name']}** may cover up to part of RM {purchase_amount:,.0f} — "
            "check max amount in Grants tab."
        )
    if decision.recommendation_type == "BNPL":
        bnpl_opts = [o for o in compare.get("options", []) if o["type"] == "BNPL"]
        if bnpl_opts:
            reasons.append(f"Lowest BNPL extra cost in catalog: **RM {bnpl_opts[0]['additional_cost_rm']:,.2f}**.")

    return {
        "star_line": star,
        "reasons": reasons,
        "snapshot": snap,
        "purchase_amount": purchase_amount,
        "purchase_category": category,
        "decision": decision,
        "compare": compare,
        "affordable_monthly_rm": affordable,
    }
