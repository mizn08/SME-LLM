"""Seed 12 months of positive-growth transactions per SME (forecast-friendly)."""

from __future__ import annotations

import random
from calendar import monthrange
from datetime import date

from sqlalchemy.orm import Session

from app.models.sme import SMEProfile
from app.models.transaction import FinancialTransaction
from app.services.data_processor import compute_kpis_from_transactions, load_transactions_df, persist_snapshot

INCOME_CATS = ["Sales - Retail", "Sales - Wholesale", "Services - Digital"]
EXPENSE_CATS = [
    "Supplies",
    "Utilities",
    "Payroll",
    "Marketing",
    "Digital / Software",
    "Equipment",
    "Logistics",
]

_PROFILES = {
    1: {"base_revenue": 48_000, "base_expense": 31_000, "rev_growth": 0.055, "exp_growth": 0.022},
    2: {"base_revenue": 72_000, "base_expense": 49_000, "rev_growth": 0.048, "exp_growth": 0.028},
    3: {"base_revenue": 95_000, "base_expense": 58_000, "rev_growth": 0.062, "exp_growth": 0.035},
}


def _month_starts(months: int) -> list[date]:
    end = date.today().replace(day=1)
    out: list[date] = []
    y, m = end.year, end.month
    for _ in range(months):
        out.append(date(y, m, 1))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    out.reverse()
    return out


def _split_total(total: float, n: int) -> list[float]:
    weights = [random.uniform(0.85, 1.15) for _ in range(n)]
    s = sum(weights)
    parts = [round(total * w / s, 2) for w in weights]
    parts[-1] = round(total - sum(parts[:-1]), 2)
    return parts


def seed_six_month_transactions(db: Session) -> int:
    """Insert transactions if none exist. Returns rows inserted."""
    if db.query(FinancialTransaction).first():
        return 0

    smes = db.query(SMEProfile).order_by(SMEProfile.id).all()
    if not smes:
        return 0

    random.seed(42)
    rows: list[FinancialTransaction] = []

    for sme in smes:
        profile = _PROFILES.get(sme.id, _PROFILES[1])
        for idx, month_start in enumerate(_month_starts(12)):
            rev_total = profile["base_revenue"] * ((1 + profile["rev_growth"]) ** idx)
            exp_total = profile["base_expense"] * ((1 + profile["exp_growth"]) ** idx)
            days_in_month = monthrange(month_start.year, month_start.month)[1]

            for amt, cat, is_exp in [
                *[(a, random.choice(INCOME_CATS), False) for a in _split_total(rev_total, 12)],
                *[(a, random.choice(EXPENSE_CATS), True) for a in _split_total(exp_total, 16)],
            ]:
                txn_date = date(
                    month_start.year,
                    month_start.month,
                    random.randint(1, days_in_month),
                )
                rows.append(
                    FinancialTransaction(
                        sme_id=sme.id,
                        txn_date=txn_date,
                        amount_rm=amt,
                        category=cat,
                        description=f"{sme.business_name} — {cat}",
                        is_expense=is_exp,
                    )
                )

    db.bulk_save_objects(rows)
    db.flush()

    for sme in smes:
        df = load_transactions_df(db, sme.id)
        kpis = compute_kpis_from_transactions(df)
        persist_snapshot(db, sme.id, kpis)

    db.commit()
    return len(rows)
