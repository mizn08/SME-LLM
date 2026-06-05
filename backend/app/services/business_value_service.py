"""Business value metrics for agentic quote demos."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.quote import QuoteLog

MANUAL_QUOTE_MINUTES = 45
AGENT_QUOTE_MINUTES = 2
HOURLY_RATE_RM = 120.0
HUMAN_ERROR_RATE = 0.18
ASSUMED_QUOTES_PER_MONTH = 40


def compute_metrics(db: Session, sme_id: int | None = None) -> dict:
    q = db.query(QuoteLog)
    if sme_id is not None:
        q = q.filter(QuoteLog.sme_id == sme_id)
    quotes = q.order_by(QuoteLog.id.desc()).limit(200).all()

    total = len(quotes)
    success = 0
    within_budget = 0
    for qt in quotes:
        items = qt.line_items or []
        if items and all(i.get("compatible", True) for i in items):
            success += 1
        if qt.budget_rm and qt.grand_total_rm <= qt.budget_rm * 1.05:
            within_budget += 1

    success_rate = (success / total) if total else 0.0
    budget_success_rate = (within_budget / total) if total else 0.0
    time_saved_min = max(MANUAL_QUOTE_MINUTES - AGENT_QUOTE_MINUTES, 0) * max(total, 1)
    cost_saved_rm = round((time_saved_min / 60.0) * HOURLY_RATE_RM, 2)
    cycle_reduction_pct = (
        max((MANUAL_QUOTE_MINUTES - AGENT_QUOTE_MINUTES) / MANUAL_QUOTE_MINUTES, 0.0) * 100.0
        if MANUAL_QUOTE_MINUTES
        else 0.0
    )
    error_reduction_pct = max((HUMAN_ERROR_RATE - max(1.0 - success_rate, 0.0)), 0.0) * 100.0
    annual_time_saved_hours = round(
        (MANUAL_QUOTE_MINUTES - AGENT_QUOTE_MINUTES) * ASSUMED_QUOTES_PER_MONTH * 12 / 60.0,
        1,
    )
    annual_cost_saved_rm = round(annual_time_saved_hours * HOURLY_RATE_RM, 2)

    return {
        "quotes_generated": total,
        "manual_quote_minutes_avg": MANUAL_QUOTE_MINUTES,
        "agent_quote_minutes_avg": AGENT_QUOTE_MINUTES,
        "time_saved_minutes_total": time_saved_min,
        "time_saved_minutes_per_quote": max(MANUAL_QUOTE_MINUTES - AGENT_QUOTE_MINUTES, 0),
        "cost_saved_rm": cost_saved_rm,
        "success_rate": round(success_rate, 3),
        "within_budget_rate": round(budget_success_rate, 3),
        "human_error_rate_benchmark": HUMAN_ERROR_RATE,
        "hourly_rate_rm": HOURLY_RATE_RM,
        "quote_cycle_time_reduction_pct": round(cycle_reduction_pct, 1),
        "error_reduction_pct": round(error_reduction_pct, 1),
        "assumed_quotes_per_month": ASSUMED_QUOTES_PER_MONTH,
        "annual_time_saved_hours": annual_time_saved_hours,
        "annual_cost_saved_rm": annual_cost_saved_rm,
    }
