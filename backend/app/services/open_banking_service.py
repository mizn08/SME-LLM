"""Open Banking sandbox stub (FPX/ORMB-style demo)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# In-memory linked banks per SME (demo)
_links: dict[int, list[dict[str, Any]]] = {}


def list_banks() -> list[dict[str, str]]:
    return [
        {"id": "maybank", "name": "Maybank", "sandbox": True},
        {"id": "cimb", "name": "CIMB", "sandbox": True},
        {"id": "rhb", "name": "RHB Bank", "sandbox": True},
        {"id": "hongleong", "name": "Hong Leong Bank", "sandbox": True},
    ]


def connect_bank(sme_id: int, bank_id: str) -> dict[str, Any]:
    banks = {b["id"]: b["name"] for b in list_banks()}
    if bank_id not in banks:
        return {"status": "error", "message": "Unknown bank"}
    entry = {
        "bank_id": bank_id,
        "bank_name": banks[bank_id],
        "status": "linked",
        "linked_at": datetime.now(timezone.utc).isoformat(),
        "last_sync": None,
    }
    _links.setdefault(sme_id, [])
    if not any(x["bank_id"] == bank_id for x in _links[sme_id]):
        _links[sme_id].append(entry)
    return {"status": "ok", "sme_id": sme_id, "connection": entry, "oauth_url": f"/connect-bank/callback?sme={sme_id}&bank={bank_id}"}


def sync_transactions(sme_id: int) -> dict[str, Any]:
    conns = _links.get(sme_id, [])
    if not conns:
        return {"status": "error", "message": "No bank linked. POST /connect-bank first."}
    now = datetime.now(timezone.utc).isoformat()
    for c in conns:
        c["last_sync"] = now
    demo_rows = [
        {"txn_date": "2026-05-20", "amount_rm": -450.0, "category": "utilities", "description": "TNB (auto-sync)", "is_expense": True},
        {"txn_date": "2026-05-22", "amount_rm": 3200.0, "category": "sales", "description": "Customer payment (auto-sync)", "is_expense": False},
    ]
    return {
        "status": "ok",
        "sme_id": sme_id,
        "banks_synced": len(conns),
        "imported_count": len(demo_rows),
        "preview_rows": demo_rows,
        "note": "Sandbox mode — merge preview_rows via CSV upload or future persist endpoint.",
    }


def get_connections(sme_id: int) -> list[dict[str, Any]]:
    return _links.get(sme_id, [])
