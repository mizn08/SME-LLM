"""Compute KPIs and aggregates from stored SME transactions."""

from __future__ import annotations

from calendar import month_abbr
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.models.cash_flow import CashFlowSnapshot
from app.models.transaction import FinancialTransaction


def compute_kpis_from_transactions(
    df: pd.DataFrame,
) -> dict[str, float]:
    """Derive simplified KPIs from a transaction DataFrame."""
    if df.empty:
        return {
            "current_ratio": 1.0,
            "days_cash_on_hand": 45.0,
            "burn_rate_monthly_rm": 0.0,
            "revenue_mtd_rm": 0.0,
            "expense_mtd_rm": 0.0,
            "net_operating_cash_rm": 0.0,
        }

    df = df.copy()
    df["txn_date"] = pd.to_datetime(df["txn_date"])
    today = pd.Timestamp.today().normalize()
    start_90 = today - pd.Timedelta(days=90)
    recent = df[df["txn_date"] >= start_90]

    inflows = recent.loc[~recent["is_expense"], "amount_rm"].sum()
    outflows = recent.loc[recent["is_expense"], "amount_rm"].sum()
    net = float(inflows - outflows)

    exp = recent[recent["is_expense"]]
    monthly_expense = exp.groupby(exp["txn_date"].dt.to_period("M"))["amount_rm"].sum()
    burn = float(monthly_expense.mean()) if len(monthly_expense) else float(
        exp["amount_rm"].sum() / 3.0
    )

    daily_out = burn / 30.0 if burn > 0 else 1.0
    days_cash = max(0.0, net / daily_out) if daily_out > 0 else 90.0

    inc = recent[~recent["is_expense"]]
    monthly_in = inc.groupby(inc["txn_date"].dt.to_period("M"))["amount_rm"].sum()
    avg_in = float(monthly_in.mean()) if len(monthly_in) else 0.0
    current_ratio = (avg_in / burn) if burn > 0 else 2.0

    mtd_mask = (df["txn_date"].dt.year == today.year) & (df["txn_date"].dt.month == today.month)
    mtd = df[mtd_mask]
    revenue_mtd = float(mtd.loc[~mtd["is_expense"], "amount_rm"].sum())
    expense_mtd = float(mtd.loc[mtd["is_expense"], "amount_rm"].sum())

    return {
        "current_ratio": round(min(max(current_ratio, 0.1), 10.0), 3),
        "days_cash_on_hand": round(days_cash, 1),
        "burn_rate_monthly_rm": round(burn, 2),
        "revenue_mtd_rm": round(revenue_mtd, 2),
        "expense_mtd_rm": round(expense_mtd, 2),
        "net_operating_cash_rm": round(net, 2),
    }


def monthly_series(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    d = df.copy()
    d["txn_date"] = pd.to_datetime(d["txn_date"])
    d["month"] = d["txn_date"].dt.to_period("M")
    rows: list[dict[str, Any]] = []
    for period, g in d.groupby("month"):
        rev = float(g.loc[~g["is_expense"], "amount_rm"].sum())
        exp = float(g.loc[g["is_expense"], "amount_rm"].sum())
        label = f"{month_abbr[int(period.month)]} {int(period.year)}"
        rows.append(
            {
                "_sort": str(period),
                "month": label,
                "revenue_rm": rev,
                "expense_rm": exp,
            }
        )
    rows.sort(key=lambda x: x["_sort"])
    for r in rows:
        r.pop("_sort", None)
    return rows[-18:]


def persist_snapshot(db: Session, sme_id: int, kpis: dict[str, float]) -> CashFlowSnapshot:
    snap = CashFlowSnapshot(
        sme_id=sme_id,
        snapshot_date=date.today(),
        current_ratio=kpis["current_ratio"],
        days_cash_on_hand=kpis["days_cash_on_hand"],
        burn_rate_monthly_rm=kpis["burn_rate_monthly_rm"],
        revenue_mtd_rm=kpis["revenue_mtd_rm"],
        expense_mtd_rm=kpis["expense_mtd_rm"],
        net_operating_cash_rm=kpis["net_operating_cash_rm"],
    )
    db.add(snap)
    return snap


def load_transactions_df(db: Session, sme_id: int) -> pd.DataFrame:
    q = (
        db.query(FinancialTransaction)
        .filter(FinancialTransaction.sme_id == sme_id)
        .order_by(FinancialTransaction.txn_date)
        .all()
    )
    if not q:
        return pd.DataFrame(columns=["txn_date", "amount_rm", "category", "is_expense"])
    return pd.DataFrame(
        [
            {
                "txn_date": t.txn_date,
                "amount_rm": t.amount_rm,
                "category": t.category,
                "is_expense": t.is_expense,
            }
            for t in q
        ]
    )


def _pick_column(col_map: dict[str, str], exact: list[str], contains: list[str]) -> str | None:
    for key in exact:
        if key in col_map:
            return col_map[key]
    for norm, original in col_map.items():
        for token in contains:
            if token in norm:
                return original
    return None


def clean_csv_dataframe(
    raw: pd.DataFrame,
    *,
    default_is_expense: bool | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Standardise uploaded columns (flexible headers) and return (df, report_messages)."""
    report: list[str] = []
    col_map = {str(c).lower().strip(): c for c in raw.columns}
    rename: dict[str, str] = {}

    date_col = _pick_column(
        col_map,
        ["date", "txn_date", "transaction_date", "trans_date", "posting_date", "date_time"],
        ["date", "time", "posted", "txn"],
    )
    amount_col = _pick_column(
        col_map,
        ["amount", "amount_rm", "value", "sum", "total"],
        ["amount", "value", "debit", "credit", "sum", "total", "rm"],
    )
    category_col = _pick_column(
        col_map,
        ["category", "type", "cat", "classification"],
        ["category", "type", "class"],
    )
    desc_col = _pick_column(
        col_map,
        ["description", "desc", "memo", "note", "details", "narration"],
        ["desc", "memo", "note", "detail", "narrat"],
    )
    expense_col = _pick_column(
        col_map,
        ["is_expense", "expense", "is_debit"],
        ["expense", "debit"],
    )

    if date_col:
        rename[date_col] = "txn_date"
    if amount_col:
        rename[amount_col] = "amount_rm"
    if category_col:
        rename[category_col] = "category"
    if desc_col:
        rename[desc_col] = "description"
    if expense_col:
        rename[expense_col] = "is_expense"

    df = raw.rename(columns=rename)
    missing = {k for k in ("txn_date", "amount_rm", "category") if k not in df.columns}
    if missing:
        raise ValueError(
            f"Missing required columns after normalisation: {missing}. "
            f"Found headers: {list(raw.columns)}"
        )

    df["txn_date"] = pd.to_datetime(df["txn_date"], errors="coerce").dt.date
    df["amount_rm"] = pd.to_numeric(df["amount_rm"], errors="coerce").abs()
    df["category"] = df["category"].astype(str).str.strip()
    if "description" not in df.columns:
        df["description"] = ""
    if "is_expense" not in df.columns:
        df["is_expense"] = default_is_expense if default_is_expense is not None else True
    else:
        df["is_expense"] = df["is_expense"].map(
            lambda x: str(x).lower() in ("1", "true", "yes", "y", "expense", "debit")
        )

    before = len(df)
    df = df.dropna(subset=["txn_date", "amount_rm"])
    report.append(f"Dropped {before - len(df)} rows with invalid dates or amounts.")
    report.append(f"Loaded {len(df)} valid transactions.")
    return df, report


def merge_upload_frames(frames: list[tuple[pd.DataFrame, str]]) -> tuple[pd.DataFrame, list[str]]:
    """Combine multiple uploaded tables (e.g. Income + Expenses CSV)."""
    if not frames:
        raise ValueError("No data to import.")
    parts: list[pd.DataFrame] = []
    report: list[str] = []
    for raw, label in frames:
        name = label.lower()
        default_expense = None
        if "expense" in name:
            default_expense = True
        elif "income" in name:
            default_expense = False
        cleaned, lines = clean_csv_dataframe(raw, default_is_expense=default_expense)
        parts.append(cleaned)
        report.append(f"{label}: {len(cleaned)} rows")
        report.extend(lines)
    merged = pd.concat(parts, ignore_index=True)
    report.insert(0, f"Merged {len(merged)} transactions from {len(parts)} file(s).")
    return merged, report


def spending_by_category(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Expense breakdown by category for donut chart."""
    if df.empty:
        return []
    d = df.copy()
    exp = d[d["is_expense"]]
    if exp.empty:
        return []
    grouped = exp.groupby("category")["amount_rm"].sum().sort_values(ascending=False)
    total = float(grouped.sum()) or 1.0
    return [
        {
            "category": str(cat),
            "amount_rm": round(float(amt), 2),
            "pct": round(float(amt) / total * 100, 1),
        }
        for cat, amt in grouped.items()
    ]
