"""Auto-generate bank statement style summary from transactions."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import data_processor


def summarize_statement(db: Session, sme_id: int, months: int = 3) -> dict:
    df = data_processor.load_transactions_df(db, sme_id)
    if df.empty:
        return {
            "sme_id": sme_id,
            "summary": "No transactions loaded. Upload CSV to generate a statement summary.",
            "periods": [],
            "totals": {},
        }

    import pandas as pd

    d = df.copy()
    d["txn_date"] = pd.to_datetime(d["txn_date"])
    d["month"] = d["txn_date"].dt.to_period("M")
    periods = []
    for period, g in d.groupby("month"):
        inc = float(g.loc[~g["is_expense"], "amount_rm"].sum())
        exp = float(g.loc[g["is_expense"], "amount_rm"].sum())
        periods.append(
            {
                "month": str(period),
                "total_credits_rm": round(inc, 2),
                "total_debits_rm": round(exp, 2),
                "net_rm": round(inc - exp, 2),
                "transaction_count": len(g),
            }
        )
    periods = periods[-months:]

    total_in = sum(p["total_credits_rm"] for p in periods)
    total_out = sum(p["total_debits_rm"] for p in periods)
    by_cat = (
        d[d["is_expense"]]
        .groupby("category")["amount_rm"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )
    top_cats = [{"category": k, "amount_rm": round(float(v), 2)} for k, v in by_cat.items()]

    summary = (
        f"Over {len(periods)} month(s): total credits RM {total_in:,.0f}, "
        f"debits RM {total_out:,.0f}, net RM {total_in - total_out:,.0f}. "
        f"Largest expense categories: {', '.join(c['category'] for c in top_cats[:3]) or 'n/a'}."
    )

    return {
        "sme_id": sme_id,
        "summary": summary,
        "periods": periods,
        "totals": {
            "credits_rm": round(total_in, 2),
            "debits_rm": round(total_out, 2),
            "net_rm": round(total_in - total_out, 2),
        },
        "top_expense_categories": top_cats,
    }
