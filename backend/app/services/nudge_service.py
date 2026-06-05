"""Proactive AI nudges from runway, grants, compliance, and anomaly signals."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.sme import SMEProfile
from app.schemas import NudgeItem
from app.services import grant_eligibility_service, unsupervised_service
from app.services.financing_recommendation_service import build_recommendation, normalize_purchase_category
from app.services.sme_financial_snapshot import get_snapshot


def get_nudges(
    db: Session,
    sme_id: int,
    *,
    purchase_amount: float | None = None,
    purchase_category: str | None = None,
) -> list[NudgeItem]:
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        return []

    snap = get_snapshot(db, sme_id)
    kpis = snap["kpis"]
    fc = snap["forecast"]
    anomalies = unsupervised_service.detect_anomalies(db, sme_id)
    grants = grant_eligibility_service.match_grants(db, sme_id=sme_id)
    runway = float(fc.get("runway_days_est") or kpis.get("days_cash_on_hand", 90))
    anomaly_count = int(anomalies.get("total_flagged") or 0)
    weekly_net = snap["weekly"]["net_rm"]
    nudges: list[NudgeItem] = []

    cat = normalize_purchase_category(purchase_category)
    rec = build_recommendation(
        db,
        sme_id,
        purchase_amount=purchase_amount,
        purchase_category=cat,
    )
    star = rec.get("star_line", "").replace("**Star recommendation:**", "").strip()
    reasons = rec.get("reasons") or []

    if runway < 30 or kpis.get("net_operating_cash_rm", 0) < 0:
        body_parts = [
            f"Runway **{runway:.0f} days** · 90-day net cash **RM {kpis['net_operating_cash_rm']:,.2f}**.",
            f"This week net **RM {weekly_net:,.2f}** ({snap['weekly']['txn_count']} transactions).",
        ]
        if reasons:
            body_parts.append(reasons[0].replace("**", ""))
        nudges.append(
            NudgeItem(
                severity="critical",
                title="Cash runway under 30 days",
                body=" ".join(body_parts),
                recommended_product=star[:120] if star else None,
                action_label="View financing options",
            )
        )
    elif runway < 60:
        nudges.append(
            NudgeItem(
                severity="warning",
                title="Tight cash position",
                body=(
                    f"About {runway:.0f} days of cash remaining. "
                    f"Monthly burn RM {kpis['burn_rate_monthly_rm']:,.2f}. "
                    "Compare BNPL vs grant in Simulate before committing."
                ),
                recommended_product=star[:120] if star else "Use Simulate tab",
                action_label="Open simulator",
            )
        )

    if grants:
        top = grants[0]
        name = top.get("scheme_name") or top.get("product_name") or "Government grant"
        max_amt = top.get("max_amount_rm")
        extra = f" (max RM {max_amt:,.0f})" if max_amt else ""
        nudges.append(
            NudgeItem(
                severity="info",
                title="Grant match available",
                body=f"You may qualify for {name}{extra}. Eligibility uses your transaction KPIs, not profile guesses.",
                recommended_product=name,
                action_label="Check grants",
            )
        )

    nudges.append(
        NudgeItem(
            severity="info",
            title="e-Invoice Phase 5 reminder",
            body="SMEs under RM1M turnover must comply by July 2026. Ensure your accounting system is ready.",
            recommended_product=None,
            action_label="View compliance",
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
                body=(
                    f"Inflows are not covering outflows (ratio {kpis['current_ratio']:.2f}). "
                    f"Trailing revenue RM {snap['trailing_annual_revenue_rm']:,.0f} from transactions."
                ),
                recommended_product=star[:120] if star else None,
                action_label="Check grant eligibility",
            )
        )

    if not nudges:
        nudges.append(
            NudgeItem(
                severity="info",
                title="Finances look stable",
                body="No urgent alerts. Use the simulator to plan your next purchase financing.",
                recommended_product=None,
                action_label="Simulate purchase",
            )
        )

    return nudges
