"""Malaysia BNPL provider catalog (JSON-backed)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.bnpl import BNPLOffer

_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "malaysia_bnpl_providers.json"


@lru_cache
def load_catalog() -> list[dict[str, Any]]:
    with _CATALOG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def list_bnpl_providers() -> list[dict[str, Any]]:
    return [
        {
            "id": p["id"],
            "name": p["provider"],
            "plan_label": p["plan_label"],
            "type": "bnpl",
            "max_amount_rm": p["max_amount_rm"],
            "max_tenure_months": p["max_tenure_months"],
            "interest_free_days": p.get("interest_free_days", 0),
            "effective_monthly_rate_pct": p.get("effective_monthly_rate_pct", 0),
            "description": p.get("description", ""),
            "apply_url": p.get("apply_url", ""),
            "sandbox": True,
        }
        for p in load_catalog()
    ]


def plan_choices() -> list[dict[str, str | None]]:
    """Simulator dropdown: Auto-select + each plan label."""
    choices: list[dict[str, str | None]] = [{"label": "Auto-select", "value": None}]
    for p in load_catalog():
        choices.append({"label": p["plan_label"], "value": p["plan_label"]})
    return choices


def _offer_from_entry(p: dict[str, Any]) -> BNPLOffer:
    return BNPLOffer(
        name=p["plan_label"],
        provider=p["provider"],
        max_amount_rm=float(p["max_amount_rm"]),
        max_tenure_months=int(p["max_tenure_months"]),
        interest_free_days=int(p.get("interest_free_days", 0)),
        effective_monthly_rate_pct=float(p.get("effective_monthly_rate_pct", 0)),
        notes=p.get("description"),
    )


def seed_bnpl_offers(db: Session) -> int:
    """Insert catalog offers if table is empty."""
    if db.query(BNPLOffer).count() > 0:
        return 0
    rows = [_offer_from_entry(p) for p in load_catalog()]
    db.add_all(rows)
    db.commit()
    return len(rows)


def sync_bnpl_offers(db: Session) -> dict[str, int]:
    """Add any catalog plans missing from bnpl_offer (keeps existing rows)."""
    existing = {o.name for o in db.query(BNPLOffer).all()}
    added = 0
    for p in load_catalog():
        if p["plan_label"] in existing:
            continue
        db.add(_offer_from_entry(p))
        added += 1
    if added:
        db.commit()
    return {"added": added, "total": db.query(BNPLOffer).count()}
