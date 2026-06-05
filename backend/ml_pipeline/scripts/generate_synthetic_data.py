#!/usr/bin/env python3
"""Generate synthetic SME transactions (500+) and ML training rows."""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "ml_pipeline" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)
np.random.seed(42)

CATEGORIES = [
    ("Supplies", True),
    ("Utilities", True),
    ("Logistics", True),
    ("Sales - Retail", False),
    ("Sales - Wholesale", False),
    ("Digital / Software", True),
    ("Equipment", True),
    ("Marketing", True),
]


def make_transactions() -> pd.DataFrame:
    rows: list[dict] = []
    base_dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(330)]
    for sme_id in (1, 2, 3):
        scale = {1: 1.0, 2: 1.4, 3: 2.2}[sme_id]
        n = 220 if sme_id != 3 else 200
        for _ in range(n):
            d = random.choice(base_dates)
            cat, is_exp = random.choice(CATEGORIES)
            if random.random() < 0.55:
                is_exp = True
            if not is_exp:
                amt = round(random.lognormvariate(9.2, 0.35) * scale, 2)
            else:
                amt = round(random.lognormvariate(8.4, 0.45) * scale, 2)
            rows.append(
                {
                    "sme_id": sme_id,
                    "date": d.isoformat(),
                    "amount": amt,
                    "category": cat,
                    "description": f"Synthetic line item {len(rows)}",
                    "is_expense": "true" if is_exp else "false",
                }
            )
    return pd.DataFrame(rows)


def label_row(r: dict) -> int:
    """Heuristic label: external financing improves cash flow stress scenario."""
    stress = r["days_cash_on_hand"] < 40 and r["purchase_to_burn"] > 1.1
    growth = r["current_ratio"] < 1.25 and r["purchase_amount"] > 15000
    return 1 if stress or growth else 0


def make_ml_dataset(n: int = 2000) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        dch = float(np.clip(np.random.normal(55, 35), 5, 180))
        cr = float(np.clip(np.random.normal(1.35, 0.35), 0.6, 4.0))
        burn = float(np.clip(np.random.lognormal(9.0, 0.5), 3000, 120000))
        purchase = float(np.clip(np.random.lognormal(9.5, 0.6), 500, 200000))
        p2b = purchase / burn
        is_dig = float(random.random() < 0.22)
        is_agri = float(random.random() < 0.12)
        monthly_net = float(np.random.normal(8000, 25000))
        row = {
            "days_cash_on_hand": dch,
            "current_ratio": cr,
            "burn_rate_monthly_rm": burn,
            "purchase_amount": purchase,
            "purchase_to_burn": p2b,
            "is_digitalisation": is_dig,
            "is_agri": is_agri,
            "monthly_net_cash": monthly_net,
        }
        row["label"] = label_row(row)
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    import runpy

    runpy.run_path(str(Path(__file__).resolve().parent / "generate_aic_datasets.py"), run_name="__main__")


if __name__ == "__main__":
    main()
