"""Weekly digest — top events from last 7 days."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from app.schemas import DigestEvent, DigestResponse
from app.services import data_processor


def get_weekly_digest(db: Session, sme_id: int) -> DigestResponse:
    df = data_processor.load_transactions_df(db, sme_id)
    week_label = f"Week ending {date.today().strftime('%d %b %Y')}"

    if df.empty:
        return DigestResponse(
            sme_id=sme_id,
            week_label=week_label,
            events=[],
            summary="No transactions yet. Upload a CSV to see your weekly digest.",
        )

    d = df.copy()
    d["txn_date"] = pd.to_datetime(d["txn_date"])
    cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=7)
    week = d[d["txn_date"] >= cutoff]

    if week.empty:
        return DigestResponse(
            sme_id=sme_id,
            week_label=week_label,
            events=[],
            summary="No activity in the last 7 days.",
        )

    events: list[DigestEvent] = []

    income = week[~week["is_expense"]]
    if not income.empty:
        top_in = income.loc[income["amount_rm"].idxmax()]
        events.append(
            DigestEvent(
                icon="trending_up",
                title="Largest income",
                detail=str(top_in.get("category", "Income")),
                amount_rm=float(top_in["amount_rm"]),
            )
        )

    expense = week[week["is_expense"]]
    if not expense.empty:
        top_exp = expense.loc[expense["amount_rm"].idxmax()]
        events.append(
            DigestEvent(
                icon="trending_down",
                title="Largest expense",
                detail=str(top_exp.get("category", "Expense")),
                amount_rm=float(top_exp["amount_rm"]),
            )
        )

    # Unusual: amount > 2x category mean in full history
    if not expense.empty:
        d_exp = d[d["is_expense"]].copy()
        d_exp["_mean"] = d_exp.groupby("category")["amount_rm"].transform("mean")
        unusual = week[week["is_expense"] & (week["amount_rm"] > week["category"].map(
            lambda c: d_exp[d_exp["category"] == c]["_mean"].max() * 2 if c in d_exp["category"].values else 0
        ))]
        if not unusual.empty:
            row = unusual.iloc[0]
            events.append(
                DigestEvent(
                    icon="warning",
                    title="Unusual spend",
                    detail=f"{row['category']} — higher than typical",
                    amount_rm=float(row["amount_rm"]),
                )
            )

    events = events[:3]
    net = float(income["amount_rm"].sum() - expense["amount_rm"].sum()) if not week.empty else 0
    summary = (
        f"This week in your business: net cash flow RM {net:,.0f} over {len(week)} transactions. "
        + (events[0].title + " stood out." if events else "")
    )

    return DigestResponse(
        sme_id=sme_id,
        week_label=week_label,
        events=events,
        summary=summary,
    )
