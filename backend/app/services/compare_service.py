"""Side-by-side financing comparison (BNPL, grant, micro-credit, cash)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.sme import SMEProfile
from app.services import data_processor, decision_engine, ml_predictor


def compare_financing(
    db: Session,
    sme: SMEProfile,
    purchase_amount: float,
    purchase_category: str,
    *,
    include_sst: bool = False,
    islamic_only: bool = False,
) -> dict[str, Any]:
    df = data_processor.load_transactions_df(db, sme.id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    features = ml_predictor.build_feature_vector(kpis, purchase_amount, purchase_category)
    ml_prob, _ = ml_predictor.predict_probability(features)

    sst_rm = purchase_amount * 0.06 if include_sst else 0.0
    options: list[dict[str, Any]] = []

    # Cash
    options.append(
        {
            "type": "Cash",
            "product_name": "Pay with operating cash",
            "additional_cost_rm": 0.0,
            "cash_preserved_rm": 0.0,
            "total_with_sst_rm": round(purchase_amount + sst_rm, 2),
            "suitability_score": round(1.0 - ml_prob, 3),
            "notes": "No financing fees; reduces liquidity immediately.",
        }
    )

    # Government schemes (grants vs soft loans — do not mislabel TEKUN as grant)
    for g in decision_engine._eligible_gov_schemes(db, sme, purchase_category):  # noqa: SLF001
        aid = (g.aid_type or "").lower()
        if aid == "grant":
            opt_type = "Grant"
            covers = purchase_amount <= float(g.max_amount_rm or 0)
            score = 0.88 if covers else 0.45
            note = (
                f"{g.agency} — max RM {g.max_amount_rm:,.0f}, non-repayable"
                if covers
                else f"{g.agency} — max RM {g.max_amount_rm:,.0f} (partial vs RM {purchase_amount:,.0f} purchase)"
            )
        elif aid in ("soft_loan", "loan"):
            opt_type = "SoftLoan"
            score = 0.5
            note = f"{g.agency} soft loan — repayable; rate {g.interest_rate_label}"
        else:
            opt_type = "GovAid"
            score = 0.4
            note = f"{g.agency} — {g.aid_type}"
        if kpis.get("days_cash_on_hand", 99) < 30 and opt_type != "Grant":
            score = round(score * 0.65, 3)
        options.append(
            {
                "type": opt_type,
                "product_name": g.scheme_name,
                "additional_cost_rm": 0.0 if opt_type == "Grant" else float(purchase_amount * 0.05),
                "cash_preserved_rm": float(min(purchase_amount, g.max_amount_rm or purchase_amount)),
                "total_with_sst_rm": round(sst_rm if opt_type == "Grant" else purchase_amount + sst_rm, 2),
                "suitability_score": score,
                "notes": note,
            }
        )

    # BNPL + credit
    from app.models.bnpl import BNPLOffer
    from app.models.credit_line import CreditLineOffer

    tenure = 6
    for b in db.query(BNPLOffer).all():
        if islamic_only and "islamic" not in b.name.lower() and "halal" not in b.provider.lower():
            continue
        if purchase_amount > b.max_amount_rm:
            continue
        cost = decision_engine._bnpl_effective_cost(b, purchase_amount, tenure)  # noqa: SLF001
        options.append(
            {
                "type": "BNPL",
                "product_name": b.name,
                "additional_cost_rm": round(cost, 2),
                "cash_preserved_rm": round(purchase_amount * 0.6, 2),
                "total_with_sst_rm": round(purchase_amount + cost + sst_rm, 2),
                "suitability_score": round(0.5 + ml_prob / 4, 3),
                "notes": f"{b.provider} · up to {b.max_tenure_months} months",
            }
        )

    for c in db.query(CreditLineOffer).all():
        if islamic_only and "islamic" not in c.name.lower() and c.product_type != "islamic":
            continue
        if purchase_amount > c.max_amount_rm:
            continue
        cost = decision_engine._credit_cost(c, purchase_amount, tenure)  # noqa: SLF001
        options.append(
            {
                "type": "MicroCredit",
                "product_name": c.name,
                "additional_cost_rm": round(cost, 2),
                "cash_preserved_rm": round(purchase_amount * 0.4, 2),
                "total_with_sst_rm": round(purchase_amount + cost + sst_rm, 2),
                "suitability_score": round(0.45 + ml_prob / 5, 3),
                "notes": f"APR {c.annual_interest_rate_pct}% · {c.provider}",
            }
        )

    primary = decision_engine.decide(db, sme, kpis, purchase_amount, purchase_category, None)
    options.sort(key=lambda o: o["additional_cost_rm"])
    return {
        "sme_id": sme.id,
        "purchase_amount_rm": purchase_amount,
        "purchase_category": purchase_category,
        "include_sst": include_sst,
        "sst_estimated_rm": round(sst_rm, 2),
        "ml_financing_probability": round(ml_prob, 4),
        "recommended": {
            "type": primary.recommendation_type,
            "product_name": primary.product_name,
        },
        "options": options,
    }
