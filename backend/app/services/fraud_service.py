"""Transaction fraud/risk scoring (rules + anomaly fusion)."""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.services import data_processor, unsupervised_service


def scan_transactions(db: Session, sme_id: int) -> dict[str, Any]:
    df = data_processor.load_transactions_df(db, sme_id)
    if df.empty:
        return {"sme_id": sme_id, "flagged": [], "total_flagged": 0, "risk_summary": "No transactions"}

    anomalies = unsupervised_service.detect_anomalies(db, sme_id)
    anomaly_ids = {a.get("id") for a in anomalies.get("anomalies", []) if a.get("id")}

    flagged: list[dict[str, Any]] = []
    if "description" not in df.columns:
        df["description"] = ""

    desc_counts = Counter(df["description"].astype(str).str.lower().str.strip())
    for _, row in df.iterrows():
        risk = 0.0
        reasons: list[str] = []
        tid = row.get("id")
        amt = float(row.get("amount_rm", 0) or 0)
        desc = str(row.get("description", "")).lower().strip()

        if tid in anomaly_ids:
            risk += 40
            reasons.append("ML anomaly score")

        if desc_counts.get(desc, 0) > 2 and amt > 500:
            risk += 25
            reasons.append("Duplicate invoice pattern")

        if amt > 20000:
            risk += 20
            reasons.append("Large transfer")

        txn_date = row.get("txn_date")
        if hasattr(txn_date, "hour") and txn_date.hour >= 22 and amt > 1000:
            risk += 15
            reasons.append("After-hours transaction")

        if risk >= 35:
            flagged.append(
                {
                    "transaction_id": int(tid) if tid is not None else None,
                    "amount_rm": amt,
                    "description": str(row.get("description", ""))[:120],
                    "risk_score": min(100, int(risk)),
                    "reasons": reasons,
                }
            )

    flagged.sort(key=lambda x: x["risk_score"], reverse=True)
    return {
        "sme_id": sme_id,
        "flagged": flagged[:20],
        "total_flagged": len(flagged),
        "risk_summary": (
            f"{len(flagged)} high-risk transaction(s) detected."
            if flagged
            else "No high-risk transactions in latest scan."
        ),
    }
