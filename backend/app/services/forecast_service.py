"""Cash-flow forecast: Prophet / ARIMA with linear fallback."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services import data_processor


def _linear_forecast(series: list[dict[str, Any]], months_ahead: int) -> tuple[list[dict[str, Any]], str]:
    nets = [p["revenue_rm"] - p["expense_rm"] for p in series]
    x = list(range(len(nets)))
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(nets) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, nets))
    den = sum((xi - mean_x) ** 2 for xi in x) or 1.0
    slope = num / den
    last_net = nets[-1]
    points: list[dict[str, Any]] = []
    cumulative = 0.0
    for i in range(1, months_ahead + 1):
        projected_net = last_net + slope * i
        cumulative += projected_net
        points.append(
            {
                "month_offset": i,
                "projected_net_rm": round(projected_net, 2),
                "cumulative_net_rm": round(cumulative, 2),
                "lower_rm": round(projected_net * 0.85, 2),
                "upper_rm": round(projected_net * 1.15, 2),
            }
        )
    return points, "linear"


def _prophet_forecast(series: list[dict[str, Any]], months_ahead: int) -> tuple[list[dict[str, Any]], str] | None:
    try:
        import pandas as pd
        from prophet import Prophet

        df = pd.DataFrame(
            {
                "ds": pd.to_datetime([f"{p['month']}-01" for p in series]),
                "y": [p["revenue_rm"] - p["expense_rm"] for p in series],
            }
        )
        m = Prophet(yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False)
        m.fit(df)
        future = m.make_future_dataframe(periods=months_ahead, freq="MS")
        forecast = m.predict(future)
        tail = forecast.tail(months_ahead)
        points: list[dict[str, Any]] = []
        cumulative = 0.0
        for i, row in enumerate(tail.itertuples(), 1):
            yhat = float(row.yhat)
            cumulative += yhat
            points.append(
                {
                    "month_offset": i,
                    "projected_net_rm": round(yhat, 2),
                    "cumulative_net_rm": round(cumulative, 2),
                    "lower_rm": round(float(row.yhat_lower), 2),
                    "upper_rm": round(float(row.yhat_upper), 2),
                }
            )
        return points, "prophet"
    except Exception:
        return None


def _arima_forecast(series: list[dict[str, Any]], months_ahead: int) -> tuple[list[dict[str, Any]], str] | None:
    try:
        import numpy as np
        from statsmodels.tsa.arima.model import ARIMA

        nets = np.array([p["revenue_rm"] - p["expense_rm"] for p in series], dtype=float)
        model = ARIMA(nets, order=(1, 0, 1))
        fit = model.fit()
        pred = fit.forecast(steps=months_ahead)
        conf = fit.get_forecast(steps=months_ahead).conf_int(alpha=0.2)
        points: list[dict[str, Any]] = []
        cumulative = 0.0
        for i in range(months_ahead):
            yhat = float(pred[i])
            cumulative += yhat
            lo = float(conf[i, 0]) if conf is not None else yhat * 0.9
            hi = float(conf[i, 1]) if conf is not None else yhat * 1.1
            points.append(
                {
                    "month_offset": i + 1,
                    "projected_net_rm": round(yhat, 2),
                    "cumulative_net_rm": round(cumulative, 2),
                    "lower_rm": round(lo, 2),
                    "upper_rm": round(hi, 2),
                }
            )
        return points, "arima"
    except Exception:
        return None


def forecast_runway(db: Session, sme_id: int, months_ahead: int = 3) -> dict[str, Any]:
    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    series = data_processor.monthly_series(df)

    forecast_points: list[dict[str, Any]] = []
    method = "linear"
    runway_days = float(kpis.get("days_cash_on_hand", 0.0))

    if len(series) >= 3:
        for fn in (_prophet_forecast, _arima_forecast, _linear_forecast):
            if fn == _linear_forecast:
                forecast_points, method = _linear_forecast(series, months_ahead)
                break
            result = fn(series, months_ahead)
            if result:
                forecast_points, method = result
                break
    elif len(series) >= 2:
        forecast_points, method = _linear_forecast(series, months_ahead)

    if len(series) >= 2 and forecast_points:
        nets = [p["revenue_rm"] - p["expense_rm"] for p in series]
        slope = (nets[-1] - nets[0]) / max(len(nets) - 1, 1)
        burn = max(float(kpis.get("burn_rate_monthly_rm", 1.0)), 1.0)
        if slope < 0:
            months_to_zero = max(0.0, float(kpis.get("net_operating_cash_rm", 0)) / burn)
            runway_days = min(runway_days, months_to_zero * 30)

    alert = None
    if runway_days < 30:
        alert = "Critical: projected runway under 30 days — prioritise grants or BNPL."
    elif runway_days < 60:
        alert = "Warning: cash buffer tightening — review burn and financing options."

    return {
        "runway_days_est": round(runway_days, 1),
        "forecast_months": forecast_points,
        "forecast_method": method,
        "alert": alert,
    }
