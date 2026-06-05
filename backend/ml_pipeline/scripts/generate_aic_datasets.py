#!/usr/bin/env python3
"""Generate AIC demo datasets: transactions, forecasts, OCR invoices, transcripts, ML rows."""

from __future__ import annotations

import json
import random
from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "ml_pipeline" / "data" / "datasets"
MOBILE_DATA = ROOT.parent / "mobile_app" / "assets" / "datasets"
MOBILE_SAMPLE = ROOT.parent / "mobile_app" / "assets" / "sample_transactions.csv"
OCR_DIR = DATA_DIR / "ocr" / "invoices"
OCR_EXPECTED = DATA_DIR / "ocr" / "expected"

random.seed(42)
np.random.seed(42)

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

SME_PROFILES = {
    1: {
        "name": "Kopi Maju Enterprise",
        "industry": "F&B retail",
        "base_revenue": 48_000,
        "base_expense": 31_000,
        "rev_growth": 0.055,
        "exp_growth": 0.022,
    },
    2: {
        "name": "Harapan Agro Supplies",
        "industry": "Agriculture wholesale",
        "base_revenue": 72_000,
        "base_expense": 49_000,
        "rev_growth": 0.048,
        "exp_growth": 0.028,
    },
    3: {
        "name": "Urban Digital Services",
        "industry": "IT services",
        "base_revenue": 95_000,
        "base_expense": 58_000,
        "rev_growth": 0.062,
        "exp_growth": 0.035,
    },
}


def _month_starts(months: int, end: date | None = None) -> list[date]:
    end = end or date.today().replace(day=1)
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


def _split_total(total: float, n: int, jitter: float = 0.15) -> list[float]:
    if n <= 0 or total <= 0:
        return []
    weights = [random.uniform(1 - jitter, 1 + jitter) for _ in range(n)]
    s = sum(weights)
    parts = [round(total * w / s, 2) for w in weights]
    parts[-1] = round(total - sum(parts[:-1]), 2)
    return parts


def generate_positive_transactions(
    sme_id: int,
    *,
    months: int = 12,
    income_txns: int = 14,
    expense_txns: int = 18,
) -> pd.DataFrame:
    """12-month uplift: revenue grows faster than expenses → positive forecast line."""
    profile = SME_PROFILES[sme_id]
    rows: list[dict] = []
    month_dates = _month_starts(months)

    for idx, month_start in enumerate(month_dates):
        rev_total = profile["base_revenue"] * ((1 + profile["rev_growth"]) ** idx)
        exp_total = profile["base_expense"] * ((1 + profile["exp_growth"]) ** idx)
        days_in_month = monthrange(month_start.year, month_start.month)[1]

        for amt, cat, is_exp in [
            *[(a, random.choice(INCOME_CATS), False) for a in _split_total(rev_total, income_txns)],
            *[(a, random.choice(EXPENSE_CATS), True) for a in _split_total(exp_total, expense_txns)],
        ]:
            day = random.randint(1, days_in_month)
            txn_date = date(month_start.year, month_start.month, day)
            rows.append(
                {
                    "sme_id": sme_id,
                    "date": txn_date.isoformat(),
                    "amount": amt,
                    "category": cat,
                    "description": f"{profile['name']} — {cat} ({txn_date.strftime('%b %Y')})",
                    "is_expense": "true" if is_exp else "false",
                }
            )

    df = pd.DataFrame(rows)
    return df.sort_values("date").reset_index(drop=True)


def _write_csv(df: pd.DataFrame, path: Path, *, drop_sme: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.drop(columns=["sme_id"], errors="ignore") if drop_sme else df
    out.to_csv(path, index=False)


def generate_income_expense_split(full: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    income = full[full["is_expense"].astype(str).str.lower() == "false"].copy()
    expense = full[full["is_expense"].astype(str).str.lower() == "true"].copy()
    return income, expense


def generate_ml_training(n: int = 2400) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        dch = float(np.clip(np.random.normal(75, 25), 15, 180))
        cr = float(np.clip(np.random.normal(1.55, 0.28), 0.8, 4.5))
        burn = float(np.clip(np.random.lognormal(9.2, 0.45), 8000, 150000))
        purchase = float(np.clip(np.random.lognormal(9.4, 0.55), 2000, 180000))
        monthly_net = float(np.clip(np.random.normal(12000, 18000), -5000, 80000))
        row = {
            "days_cash_on_hand": round(dch, 1),
            "current_ratio": round(cr, 3),
            "burn_rate_monthly_rm": round(burn, 2),
            "purchase_amount": round(purchase, 2),
            "purchase_to_burn": round(purchase / burn, 3),
            "is_digitalisation": int(random.random() < 0.25),
            "is_agri": int(random.random() < 0.15),
            "monthly_net_cash": round(monthly_net, 2),
            "recommended_product": random.choice(["bnpl", "grant", "micro_credit", "cash"]),
        }
        stress = row["days_cash_on_hand"] < 45 and row["purchase_to_burn"] > 1.0
        growth = row["current_ratio"] < 1.3 and row["purchase_amount"] > 20000
        row["label"] = 1 if stress or growth else 0
        rows.append(row)
    return pd.DataFrame(rows)


def generate_bnpl_scenarios() -> pd.DataFrame:
    scenarios = [
        (8000, "pos", "Kopi Maju POS upgrade"),
        (12000, "ecommerce", "Inventory + website package"),
        (25000, "equipment", "Commercial kitchen equipment"),
        (45000, "digital", "Cloud + CRM stack"),
        (15000, "agro", "Irrigation pump set"),
        (6000, "retail", "Display fixtures"),
        (18000, "fnb", "Second outlet fit-out"),
        (32000, "equipment", "Delivery van down payment"),
        (9500, "pos", "Tablet POS terminals x4"),
        (55000, "digital", "ERP migration"),
        (22000, "agro", "Cold storage unit"),
        (14000, "retail", "Seasonal stock purchase"),
    ]
    rows = []
    for amt, cat, title in scenarios:
        rows.append(
            {
                "sme_id": random.choice([1, 2, 3]),
                "purchase_amount_rm": amt,
                "purchase_category": cat,
                "scenario_title": title,
                "include_sst": random.choice([True, False]),
                "islamic_only": random.choice([True, False]),
                "expected_path": random.choice(["bnpl", "grant", "micro_credit", "cash"]),
            }
        )
    return pd.DataFrame(rows)


def generate_quote_lines() -> pd.DataFrame:
    lines = [
        ("POS-001", "Sunmi V2 POS Terminal", 2890, 1, "pos"),
        ("POS-002", "Cash drawer + printer bundle", 890, 1, "pos"),
        ("ECOM-001", "Shopify SME website setup", 4500, 1, "ecommerce"),
        ("ECOM-002", "Inventory sync module", 3200, 1, "ecommerce"),
        ("EQ-001", "Commercial espresso machine", 8500, 1, "equipment"),
        ("DIG-001", "Managed Wi-Fi router", 680, 2, "digital"),
        ("AGR-001", "Irrigation controller", 4200, 1, "agro"),
    ]
    return pd.DataFrame(
        [
            {
                "product_id": pid,
                "name": name,
                "unit_price_rm": price,
                "quantity": qty,
                "purchase_category": cat,
            }
            for pid, name, price, qty, cat in lines
        ]
    )


def generate_financial_goals() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"sme_id": 1, "goal_type": "runway", "target_value": 90, "unit": "days", "priority": "high"},
            {"sme_id": 1, "goal_type": "revenue", "target_value": 90000, "unit": "rm_monthly", "priority": "medium"},
            {"sme_id": 2, "goal_type": "equipment", "target_value": 35000, "unit": "rm", "priority": "high"},
            {"sme_id": 3, "goal_type": "digital", "target_value": 50000, "unit": "rm", "priority": "high"},
        ]
    )


def generate_ocr_invoice_png(path: Path, invoice: dict) -> None:
    from PIL import Image, ImageDraw, ImageFont

    w, h = 900, 1100
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    try:
        title_font = ImageFont.truetype("arial.ttf", 36)
        body_font = ImageFont.truetype("arial.ttf", 28)
    except OSError:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    y = 40
    draw.text((40, y), invoice["header"], fill="black", font=title_font)
    y += 60
    for line in invoice["lines"]:
        draw.text((40, y), line, fill="black", font=body_font)
        y += 42

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG")


def generate_ocr_pack() -> list[str]:
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    OCR_EXPECTED.mkdir(parents=True, exist_ok=True)
    invoices = [
        {
            "file": "invoice_kopi_maju_supplies.png",
            "header": "TAX INVOICE — Kopi Maju Enterprise",
            "lines": [
                "Date: 2025-11-18",
                "Supplier: Bean & Brew Trading",
                "Arabica beans 20kg RM 1,240.00",
                "Milk powder bulk RM 380.00",
                "Subtotal RM 1,620.00",
                "SST RM 97.20",
                "Grand total RM 1,717.20",
            ],
            "expected": [
                ("2025-11-18", 1240.00, "Arabica beans 20kg"),
                ("2025-11-18", 380.00, "Milk powder bulk"),
                ("2025-11-18", 1620.00, "Subtotal"),
                ("2025-11-18", 97.20, "SST"),
                ("2025-11-18", 1717.20, "Grand total"),
            ],
        },
        {
            "file": "invoice_agro_equipment.png",
            "header": "INVOICE — Harapan Agro Supplies",
            "lines": [
                "Date: 2025-12-02",
                "Vendor: AgriTech KL",
                "Irrigation pump RM 4,850.00",
                "Installation labour RM 650.00",
                "Subtotal RM 5,500.00",
                "SST RM 330.00",
                "Grand total RM 5,830.00",
            ],
            "expected": [
                ("2025-12-02", 4850.00, "Irrigation pump"),
                ("2025-12-02", 650.00, "Installation labour"),
                ("2025-12-02", 5500.00, "Subtotal"),
                ("2025-12-02", 330.00, "SST"),
                ("2025-12-02", 5830.00, "Grand total"),
            ],
        },
        {
            "file": "invoice_digital_software.png",
            "header": "INVOICE — Urban Digital Services",
            "lines": [
                "Date: 2026-01-10",
                "Vendor: CloudStack MY",
                "CRM annual licence RM 3,600.00",
                "Support package RM 900.00",
                "Subtotal RM 4,500.00",
                "SST RM 270.00",
                "Grand total RM 4,770.00",
            ],
            "expected": [
                ("2026-01-10", 3600.00, "CRM annual licence"),
                ("2026-01-10", 900.00, "Support package"),
                ("2026-01-10", 4500.00, "Subtotal"),
                ("2026-01-10", 270.00, "SST"),
                ("2026-01-10", 4770.00, "Grand total"),
            ],
        },
    ]

    written: list[str] = []
    for inv in invoices:
        png_path = OCR_DIR / inv["file"]
        generate_ocr_invoice_png(png_path, inv)
        written.append(str(png_path.relative_to(DATA_DIR)))

        exp_rows = [
            {
                "txn_date": d,
                "amount_rm": amt,
                "category": "invoice",
                "description": desc,
                "is_expense": True,
            }
            for d, amt, desc in inv["expected"]
        ]
        exp_df = pd.DataFrame(exp_rows)
        exp_path = OCR_EXPECTED / inv["file"].replace(".png", "_expected.csv")
        exp_df.to_csv(exp_path, index=False)
        written.append(str(exp_path.relative_to(DATA_DIR)))

        txt_path = DATA_DIR / "ocr" / "text" / inv["file"].replace(".png", ".txt")
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text("\n".join([inv["header"], *inv["lines"]]), encoding="utf-8")
        written.append(str(txt_path.relative_to(DATA_DIR)))

    manifest = DATA_DIR / "ocr" / "README.txt"
    manifest.write_text(
        "Upload PNG files from ocr/invoices/ via Insights → Scan invoice.\n"
        "Expected parsed rows are in ocr/expected/*_expected.csv for validation.\n",
        encoding="utf-8",
    )
    return written


def generate_transcripts() -> None:
    (DATA_DIR / "transcripts").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "requirements").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "transcripts" / "client_pos_fnb.txt").write_text(
        """Client: We run Kopi Maju and need a complete POS + inventory + website package.
Client: Budget around RM 12000 and we prefer low monthly payment in Kuala Lumpur.
Client: Delivery and setup should be this month.
Agent: Noted — compare BNPL vs grant vs micro-credit options.
""",
        encoding="utf-8",
    )
    (DATA_DIR / "transcripts" / "client_ecommerce.txt").write_text(
        """Client: Harapan Agro wants e-commerce with inventory sync for agro products.
Client: Budget RM 25000, location Penang, need BNPL with 6-month terms.
Agent: Any grant eligibility for digitalisation?
Client: Yes, MDEC-style grant if possible. No drilling on warehouse setup.
""",
        encoding="utf-8",
    )
    (DATA_DIR / "requirements" / "brief_pos_kl.json").write_text(
        json.dumps(
            {
                "budget": 12000,
                "location": "Kuala Lumpur",
                "purchase_category": "pos",
                "style": "modern",
                "explicit_constraints": ["bnpl", "low monthly payment", "inventory sync"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _prepare_demo_session(sme1_full: pd.DataFrame) -> None:
    """Handy files for live demo manual upload (project root demo_session/)."""
    import shutil

    demo = ROOT.parent / "demo_session"
    demo.mkdir(exist_ok=True)
    sme1_full.drop(columns=["sme_id"]).to_csv(
        demo / "DEMO_01_forecast_transactions_kopi_maju.csv",
        index=False,
    )
    src_png = OCR_DIR / "invoice_kopi_maju_supplies.png"
    if src_png.is_file():
        shutil.copy2(src_png, demo / "DEMO_02_invoice_kopi_maju_supplies.png")
    src_txt = DATA_DIR / "transcripts" / "client_pos_fnb.txt"
    if src_txt.is_file():
        shutil.copy2(src_txt, demo / "DEMO_03_client_transcript_pos.txt")


def write_manifest(files: list[str]) -> None:
    lines = [
        "# AIC Synthetic Dataset Catalog",
        "",
        "Generated by `python ml_pipeline/scripts/generate_aic_datasets.py`.",
        "All transaction sets use **positive 12-month growth** (revenue > expense uplift) for forecast charts.",
        "",
        "| # | File | Purpose |",
        "|---|------|---------|",
    ]
    catalog = [
        ("01", "01_sme1_kopi_maju_12m_uplift.csv", "SME 1 F&B — full 12-month positive cashflow"),
        ("02", "02_sme2_harapan_agro_12m_uplift.csv", "SME 2 Agriculture"),
        ("03", "03_sme3_urban_digital_12m_uplift.csv", "SME 3 IT services"),
        ("04", "04_sme1_income_stream.csv", "Income-only upload (merge with expenses)"),
        ("05", "05_sme1_expense_stream.csv", "Expense-only upload"),
        ("06", "06_all_smes_combined.csv", "All SMEs combined benchmark set"),
        ("07", "07_ml_training_aic.csv", "ML /predict training features + labels"),
        ("08", "08_bnpl_simulation_scenarios.csv", "Design & Finance simulator scenarios"),
        ("09", "09_quote_catalog_lines.csv", "Sales Engineer quote line reference"),
        ("10", "10_financial_goals.csv", "Goals widget / planning"),
        ("11", "transcripts/client_pos_fnb.txt", "Sales Engineer unstructured input"),
        ("12", "transcripts/client_ecommerce.txt", "Agro e-commerce transcript"),
        ("13", "requirements/brief_pos_kl.json", "Structured requirements JSON"),
        ("14", "ocr/invoices/*.png", "OCR scan targets (Tesseract)"),
        ("15", "ocr/expected/*_expected.csv", "Expected OCR parse output"),
    ]
    for num, fname, purpose in catalog:
        lines.append(f"| {num} | `{fname}` | {purpose} |")
    lines.extend(["", "## Forecast demo", "", "Upload `01_sme1_kopi_maju_12m_uplift.csv` → Home dashboard shows **Forecast net** dashed line on chart.", ""])
    (DATA_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MOBILE_DATA.mkdir(parents=True, exist_ok=True)

    all_frames: list[pd.DataFrame] = []
    written: list[str] = []

    for sme_id in (1, 2, 3):
        df = generate_positive_transactions(sme_id, months=12)
        all_frames.append(df)
        fname = f"{sme_id:02d}_sme{sme_id}_{SME_PROFILES[sme_id]['name'].split()[0].lower()}_12m_uplift.csv"
        if sme_id == 1:
            fname = "01_sme1_kopi_maju_12m_uplift.csv"
        elif sme_id == 2:
            fname = "02_sme2_harapan_agro_12m_uplift.csv"
        else:
            fname = "03_sme3_urban_digital_12m_uplift.csv"
        path = DATA_DIR / fname
        _write_csv(df, path)
        written.append(fname)

        if sme_id == 1:
            inc, exp = generate_income_expense_split(df)
            _write_csv(inc, DATA_DIR / "04_sme1_income_stream.csv")
            _write_csv(exp, DATA_DIR / "05_sme1_expense_stream.csv")
            written.extend(["04_sme1_income_stream.csv", "05_sme1_expense_stream.csv"])

    combined = pd.concat(all_frames, ignore_index=True)
    _write_csv(combined, DATA_DIR / "06_all_smes_combined.csv")
    written.append("06_all_smes_combined.csv")

    ml = generate_ml_training()
    ml.to_csv(DATA_DIR / "07_ml_training_aic.csv", index=False)
    ml.to_csv(ROOT / "ml_pipeline" / "data" / "ml_training.csv", index=False)
    written.append("07_ml_training_aic.csv")

    generate_bnpl_scenarios().to_csv(DATA_DIR / "08_bnpl_simulation_scenarios.csv", index=False)
    generate_quote_lines().to_csv(DATA_DIR / "09_quote_catalog_lines.csv", index=False)
    generate_financial_goals().to_csv(DATA_DIR / "10_financial_goals.csv", index=False)
    written.extend(
        [
            "08_bnpl_simulation_scenarios.csv",
            "09_quote_catalog_lines.csv",
            "10_financial_goals.csv",
        ]
    )

    generate_transcripts()
    written.extend(
        [
            "transcripts/client_pos_fnb.txt",
            "transcripts/client_ecommerce.txt",
            "requirements/brief_pos_kl.json",
        ]
    )

    ocr_files = generate_ocr_pack()
    written.extend(ocr_files)

    # Mobile bundled assets
    sme1 = all_frames[0].drop(columns=["sme_id"])
    sme1.to_csv(MOBILE_SAMPLE, index=False)
    for src in DATA_DIR.glob("*.csv"):
        target = MOBILE_DATA / src.name
        pd.read_csv(src).to_csv(target, index=False)

    ocr_mobile = MOBILE_DATA / "ocr" / "invoices"
    ocr_mobile.mkdir(parents=True, exist_ok=True)
    import shutil

    for png in OCR_DIR.glob("*.png"):
        shutil.copy2(png, ocr_mobile / png.name)

    # Legacy combined sample
    pd.read_csv(DATA_DIR / "01_sme1_kopi_maju_12m_uplift.csv").drop(columns=["sme_id"]).to_csv(
        ROOT / "ml_pipeline" / "data" / "sample_sme_transactions.csv",
        index=False,
    )

    write_manifest(written)
    _prepare_demo_session(all_frames[0])
    print(f"Wrote {len(written)} dataset artifacts under {DATA_DIR}")
    print(f"Mobile assets: {MOBILE_DATA}")
    print(f"Default upload sample: {MOBILE_SAMPLE}")


if __name__ == "__main__":
    main()
