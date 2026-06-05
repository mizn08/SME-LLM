"""Single source of truth for KPIs — same numbers as Health dashboard & RAG."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.models.sme import SMEProfile
from app.services import data_processor, forecast_service, health_score_service, unsupervised_service


def get_snapshot(db: Session, sme_id: int) -> dict[str, Any]:
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    fc = forecast_service.forecast_runway(db, sme_id, months_ahead=12)
    anomalies = unsupervised_service.detect_anomalies(db, sme_id)
    health = health_score_service.compute_health_score(
        kpis, fc.get("runway_days_est"), int(anomalies.get("total_flagged") or 0)
    )
    spending = data_processor.spending_by_category(df)
    weekly = _weekly_cashflow(df)
    revenue = _trailing_revenue(df)

    return {
        "sme_id": sme_id,
        "business_name": sme.business_name if sme else "",
        "industry": sme.industry if sme else "",
        "profile_annual_revenue_rm": float(sme.annual_revenue_rm) if sme else 0.0,
        "kpis": kpis,
        "runway_days_est": float(fc.get("runway_days_est") or 0),
        "forecast": fc,
        "health": health,
        "spending_categories": spending,
        "weekly": weekly,
        "trailing_annual_revenue_rm": revenue["trailing_annual_rm"],
        "avg_monthly_revenue_rm": revenue["avg_monthly_rm"],
        "anomaly_count": int(anomalies.get("total_flagged") or 0),
    }


def _trailing_revenue(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return {"trailing_annual_rm": 0.0, "avg_monthly_rm": 0.0}
    d = df.copy()
    d["txn_date"] = pd.to_datetime(d["txn_date"])
    cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=365)
    recent = d[d["txn_date"] >= cutoff]
    income = recent[~recent["is_expense"]]["amount_rm"].sum()
    months = max(recent["txn_date"].dt.to_period("M").nunique(), 1)
    avg_monthly = float(income) / months if months else 0.0
    return {
        "trailing_annual_rm": round(float(income), 2),
        "avg_monthly_rm": round(avg_monthly, 2),
    }


def _weekly_cashflow(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"net_rm": 0.0, "txn_count": 0, "largest_expense_category": None}
    d = df.copy()
    d["txn_date"] = pd.to_datetime(d["txn_date"])
    cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=7)
    week = d[d["txn_date"] >= cutoff]
    if week.empty:
        return {"net_rm": 0.0, "txn_count": 0, "largest_expense_category": None}
    income = float(week[~week["is_expense"]]["amount_rm"].sum())
    expense = float(week[week["is_expense"]]["amount_rm"].sum())
    top_cat = None
    exp = week[week["is_expense"]]
    if not exp.empty:
        top_cat = str(exp.groupby("category")["amount_rm"].sum().idxmax())
    return {
        "net_rm": round(income - expense, 2),
        "txn_count": int(len(week)),
        "largest_expense_category": top_cat,
    }


def format_dashboard_block(snap: dict[str, Any], lang: str = "en") -> str:
    k = snap["kpis"]
    w = snap["weekly"]
    if lang == "ms":
        lines = [
            "**Data anda (sama seperti tab Health):**",
            f"• Net tunai 90 hari: **RM {k['net_operating_cash_rm']:,.2f}**",
            f"• Tunai: **{k['days_cash_on_hand']:.1f} hari** | Burn bulanan: **RM {k['burn_rate_monthly_rm']:,.2f}**",
            f"• Ratio: {k['current_ratio']:.2f} | Skor kesihatan: **{snap['health']['health_score']}/100 ({snap['health']['health_grade']})**",
            f"• Minggu ini: net **RM {w['net_rm']:,.2f}** ({w['txn_count']} transaksi)",
        ]
    else:
        lines = [
            "**Your data (same as Health tab):**",
            f"• 90-day net operating cash: **RM {k['net_operating_cash_rm']:,.2f}**",
            f"• Days cash on hand: **{k['days_cash_on_hand']:.1f}** | Monthly burn: **RM {k['burn_rate_monthly_rm']:,.2f}**",
            f"• Current ratio: {k['current_ratio']:.2f} | Health score: **{snap['health']['health_score']}/100 (Grade {snap['health']['health_grade']})**",
            f"• This week: net **RM {w['net_rm']:,.2f}** over {w['txn_count']} transactions",
        ]
    if snap["spending_categories"]:
        top = snap["spending_categories"][0]
        lines.append(
            f"• Top spend category: **{top['category']}** ({top['pct']}% of expenses)"
            if lang == "en"
            else f"• Perbelanjaan tertinggi: **{top['category']}** ({top['pct']}%)"
        )
    return "\n".join(lines)
