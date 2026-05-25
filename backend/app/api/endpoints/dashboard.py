from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sme import SMEProfile
from app.schemas import (
    DashboardKPIs,
    DashboardResponse,
    MonthlySeriesPoint,
    ForecastMonth,
)
from app.services import data_processor, forecast_service, health_score_service, unsupervised_service

router = APIRouter(tags=["dashboard"])


@router.get("/sme/{sme_id}/dashboard", response_model=DashboardResponse)
def get_dashboard(sme_id: int, db: Session = Depends(get_db)):
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        raise HTTPException(404, "SME not found")
    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    series = [MonthlySeriesPoint(**p) for p in data_processor.monthly_series(df)]
    fc = forecast_service.forecast_runway(db, sme_id)
    anomalies = unsupervised_service.detect_anomalies(db, sme_id)
    alerts: list[str] = []
    if fc.get("alert"):
        alerts.append(fc["alert"])
    if anomalies.get("total_flagged", 0) > 0:
        alerts.append(f"{anomalies['total_flagged']} unusual transactions detected.")


    health = health_score_service.compute_health_score(
        kpis, fc.get("runway_days_est"), int(anomalies.get("total_flagged") or 0)
    )
    return DashboardResponse(
        sme_id=sme_id,
        business_name=sme.business_name,
        industry=sme.industry,
        kpis=DashboardKPIs(**kpis),
        monthly_series=series,
        runway_days_est=fc.get("runway_days_est"),
        forecast_months=[ForecastMonth(**m) for m in fc.get("forecast_months", [])],
        alerts=alerts,
        anomaly_count=int(anomalies.get("total_flagged") or 0),
        health_score=health["health_score"],
        health_grade=health["health_grade"],
        health_label=health["health_label"],
    )
