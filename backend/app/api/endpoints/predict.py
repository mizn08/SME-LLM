from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.gov_aid import GovFinancialAid
from app.models.prediction import PredictionLog
from app.models.sme import SMEProfile
from app.schemas import GovAidOut, PredictRequest, PredictResponse, ShapExplainResponse, ShapItem, ShapWaterfallItem
from app.services import bandit_service, data_processor, decision_engine, lead_score_service, rl_policy_service

router = APIRouter(tags=["predict"])


@router.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == payload.sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    df = data_processor.load_transactions_df(db, payload.sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)

    result = decision_engine.decide(
        db,
        sme,
        kpis,
        payload.purchase_amount,
        payload.purchase_category,
        payload.selected_bnpl_plan,
    )

    log = PredictionLog(
        sme_id=payload.sme_id,
        request_payload=payload.model_dump(),
        recommendation_type=result.recommendation_type,
        product_name=result.product_name,
        explanation=result.explanation,
        cash_preserved_rm=result.cash_preserved_rm,
        additional_cost_rm=result.additional_cost_rm,
        confidence=result.confidence,
        shap_values=result.shap_values,
        ml_probability=result.ml_probability,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    bandit = bandit_service.select_arm_ucb(db)
    rl = rl_policy_service.select_action(db, payload.sme_id, payload.purchase_amount)
    lead_scores = lead_score_service.compute_lead_scores(db, payload.sme_id)

    return PredictResponse(
        prediction_id=log.id,
        recommendation_type=result.recommendation_type,
        product_name=result.product_name,
        explanation=result.explanation,
        cash_preserved_rm=result.cash_preserved_rm,
        additional_cost_rm=result.additional_cost_rm,
        confidence=result.confidence,
        shap_values=[ShapItem(**s) for s in result.shap_values],
        ml_probability=result.ml_probability,
        bandit_suggested_arm=bandit["suggested_arm"],
        rl_suggested_action=rl["action"],
        lead_scores=lead_scores,
    )


@router.get("/sme/{sme_id}/shap-explain", response_model=ShapExplainResponse)
def shap_explain(
    sme_id: int,
    purchase_amount: float = 5000,
    purchase_category: str = "equipment",
    db: Session = Depends(get_db),
):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    result = decision_engine.decide(db, sme, kpis, purchase_amount, purchase_category, None)
    baseline = 0.5
    cumulative = baseline
    waterfall: list[ShapWaterfallItem] = []
    for s in result.shap_values:
        impact = float(s.get("impact", 0))
        cumulative += impact
        waterfall.append(
            ShapWaterfallItem(
                feature=str(s.get("feature", "")),
                impact=impact,
                direction=str(s.get("direction", "neutral")),
                cumulative=round(cumulative, 4),
            )
        )
    return ShapExplainResponse(
        sme_id=sme_id,
        baseline=baseline,
        prediction=round(cumulative, 4),
        waterfall=waterfall,
    )


@router.get("/gov-aid", response_model=list[GovAidOut])
def list_gov_aid(db: Session = Depends(get_db)):
    rows = db.query(GovFinancialAid).order_by(GovFinancialAid.id).all()
    return [GovAidOut.model_validate(r, from_attributes=True) for r in rows]
