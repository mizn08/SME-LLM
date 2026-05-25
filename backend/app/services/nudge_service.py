"""Proactive AI nudges from runway and anomaly signals."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.sme import SMEProfile
from app.schemas import NudgeItem
from app.services import data_processor, forecast_service, unsupervised_service


def get_nudges(db: Session, sme_id: int) -> list[NudgeItem]:
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        return []

    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    fc = forecast_service.forecast_runway(db, sme_id)
    anomalies = unsupervised_service.detect_anomalies(db, sme_id)
    runway = float(fc.get("runway_days_est") or kpis.get("days_cash_on_hand", 90))
    anomaly_count = int(anomalies.get("total_flagged") or 0)
    nudges: list[NudgeItem] = []

    if runway < 30:
        nudges.append(
            NudgeItem(
                severity="critical",
                title="Cash runway under 30 days",
                body=f"Estimated runway is {runway:.0f} days. Consider micro-credit or a grant to bridge operations.",
                recommended_product="TEKUN Micro Credit",
                action_label="View financing options",
            )
        )
    elif runway < 60:
        nudges.append(
            NudgeItem(
                severity="warning",
                title="Tight cash position",
                body=f"About {runway:.0f} days of cash remaining. BNPL can preserve liquidity for essential purchases.",
                recommended_product="BNPL (Atome / Grab PayLater)",
                action_label="Open simulator",
            )
        )

    if anomaly_count >= 3:
        nudges.append(
            NudgeItem(
                severity="warning",
                title=f"{anomaly_count} unusual transactions",
                body="Review flagged expenses — they may indicate fraud or miscategorised costs.",
                recommended_product=None,
                action_label="View insights",
            )
        )
    elif anomaly_count > 0:
        nudges.append(
            NudgeItem(
                severity="info",
                title="Unusual spending detected",
                body=f"{anomaly_count} transaction(s) deviate from your normal pattern.",
                recommended_product=None,
                action_label="Review transactions",
            )
        )

    if kpis.get("current_ratio", 1) < 1.0:
        nudges.append(
            NudgeItem(
                severity="warning",
                title="Liquidity ratio below 1.0",
                body="Monthly inflows are not covering outflows. Grants or staged BNPL may help.",
                recommended_product="MDEC Digital Grant",
                action_label="Check grant eligibility",
            )
        )

    if not nudges:
        nudges.append(
            NudgeItem(
                severity="info",
                title="Finances look stable",
                body="No urgent alerts. Use the simulator to plan your next purchase financing.",
                recommended_product="BNPL",
                action_label="Simulate purchase",
            )
        )

    return nudges
