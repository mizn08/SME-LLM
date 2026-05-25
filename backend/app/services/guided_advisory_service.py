"""Guided 5-step advisory recommendation."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas import GuidedAdvisoryRequest, GuidedAdvisoryResponse
from app.services import data_processor, lead_score_service, pitch_service


def run_guided_advisory(db: Session, req: GuidedAdvisoryRequest) -> GuidedAdvisoryResponse:
    scores = lead_score_service.compute_lead_scores(db, req.sme_id)
    df = data_processor.load_transactions_df(db, req.sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)

    # Score products by goal + constraint
    weights = {"bnpl": 0, "micro_credit": 0, "grant": 0}
    for s in scores:
        weights[s.product_type] = s.score

    if req.goal in ("expand", "digitalise"):
        weights["grant"] += 15
        weights["bnpl"] += 10
    elif req.goal == "survive":
        weights["micro_credit"] += 20
        weights["bnpl"] += 15
    elif req.goal == "export":
        weights["grant"] += 25

    if req.main_constraint == "cash":
        weights["bnpl"] += 20
    elif req.main_constraint == "collateral":
        weights["grant"] += 15
        weights["bnpl"] += 10
    elif req.main_constraint == "eligibility":
        weights["grant"] += 10

    if req.timeline_months <= 3:
        weights["bnpl"] += 15
    else:
        weights["grant"] += 10

    top_type = max(weights, key=weights.get)
    top_score = next((s for s in scores if s.product_type == top_type), scores[0])

    product_names = {
        "bnpl": "BNPL — Atome / Grab PayLater",
        "micro_credit": "TEKUN / CGC Micro Credit",
        "grant": "MDEC / MATRADE Grant",
    }

    reasoning = list(top_score.reasons)
    reasoning.append(f"Goal '{req.goal}' with RM {req.amount_rm:,.0f} over {req.timeline_months} months")
    reasoning.append(f"Main constraint: {req.main_constraint}")

    next_steps = [
        "Run Purchase Simulator to validate ML recommendation",
        "Generate pitch letter for bank or agency",
        "Open grant checklist and track application status",
    ]
    if req.main_constraint == "cash":
        next_steps.insert(0, "Compare BNPL plans to preserve working capital")

    pitch = pitch_service.generate_pitch(db, req.sme_id, lang="en", tone="formal")[:500]

    return GuidedAdvisoryResponse(
        sme_id=req.sme_id,
        recommendation=(
            f"Based on your {req.business_type} business, we recommend **{product_names[top_type]}** "
            f"for RM {req.amount_rm:,.0f} within {req.timeline_months} months."
        ),
        top_product=product_names[top_type],
        top_product_type=top_type,
        reasoning=reasoning,
        next_steps=next_steps,
        pitch_snippet=pitch + "...",
    )
