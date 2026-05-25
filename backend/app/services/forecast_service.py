"""Simple cash-flow forecast (linear trend on monthly net)."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.services import data_processor


def forecast_runway(db: Session, sme_id: int, months_ahead: int = 3) -> dict[str, Any]:
    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    series = data_processor.monthly_series(df)

    forecast_points: list[dict[str, Any]] = []
    runway_days = kpis.get("days_cash_on_hand", 0.0)

    if len(series) >= 2:
        nets = [p["revenue_rm"] - p["expense_rm"] for p in series]
        x = list(range(len(nets)))
        # linear slope
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(nets) / n
        num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, nets))
        den = sum((xi - mean_x) ** 2 for xi in x) or 1.0
        slope = num / den
        last_net = nets[-1]
        burn = max(kpis.get("burn_rate_monthly_rm", 1.0), 1.0)
        cumulative = 0.0
        for i in range(1, months_ahead + 1):
            projected_net = last_net + slope * i
            cumulative += projected_net
            forecast_points.append(
                {
                    "month_offset": i,
                    "projected_net_rm": round(projected_net, 2),
                    "cumulative_net_rm": round(cumulative, 2),
                }
            )
        if slope < 0 and burn > 0:
            months_to_zero = max(0.0, kpis.get("net_operating_cash_rm", 0) / burn)
            runway_days = min(runway_days, months_to_zero * 30)

    alert = None
    if runway_days < 30:
        alert = "Critical: projected runway under 30 days — prioritise grants or BNPL."
    elif runway_days < 60:
        alert = "Warning: cash buffer tightening — review burn and financing options."

    return {
        "runway_days_est": round(runway_days, 1),
        "forecast_months": forecast_points,
        "alert": alert,
    }
