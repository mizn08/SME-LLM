"""Autonomous financing application draft generator."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.sme import SMEProfile
from app.services import data_processor, decision_engine, lead_score_service


def generate_draft(
    db: Session,
    sme_id: int,
    product_type: str,
    purchase_amount: float = 0,
    purchase_category: str = "Equipment",
) -> dict:
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        return {"error": "SME not found"}

    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    scores = lead_score_service.compute_lead_scores(db, sme_id)
    match = next((s for s in scores if s.product_type == product_type), scores[0] if scores else None)

    amount = purchase_amount or float(kpis.get("burn_rate_monthly_rm", 10000)) * 2
    rec = decision_engine.decide(db, sme, kpis, amount, purchase_category, None)

    sections = {
        "applicant": {
            "business_name": sme.business_name,
            "industry": sme.industry,
            "sme_id": sme_id,
        },
        "requested_product": {
            "product_type": product_type,
            "product_name": rec.product_name if product_type == "bnpl" else match.product_name if match else rec.product_name,
            "amount_rm": amount,
            "category": purchase_category,
        },
        "financial_summary": {
            "current_ratio": kpis.get("current_ratio"),
            "days_cash_on_hand": kpis.get("days_cash_on_hand"),
            "burn_rate_monthly_rm": kpis.get("burn_rate_monthly_rm"),
            "revenue_mtd_rm": kpis.get("revenue_mtd_rm"),
        },
        "match_score": match.score if match else 0,
        "match_reasons": match.reasons if match else [],
        "narrative": (
            f"{sme.business_name} requests {product_type.replace('_', ' ')} financing of RM {amount:,.0f} "
            f"for {purchase_category}. "
            f"Recommendation engine suggests: {rec.recommendation_type} — {rec.product_name}. "
            f"{rec.explanation}"
        ),
        "supporting_documents": [
            "SSM certificate",
            "6-month bank statements",
            "Latest management accounts",
            "Purchase quotation",
        ],
        "status": "draft",
    }
    return sections
