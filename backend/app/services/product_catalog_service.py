"""Product catalog + compatibility (mock external catalog API with latency)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "product_catalog.json"
_CACHE: list[dict[str, Any]] | None = None


def _load_catalog() -> list[dict[str, Any]]:
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    return _CACHE


def search_products(
    query: str = "",
    *,
    max_price: float | None = None,
    category: str | None = None,
    style: str | None = None,
) -> list[dict[str, Any]]:
    """Simulate external catalog API latency."""
    time.sleep(0.25)
    items = _load_catalog()
    q = (query or "").lower()
    style_l = (style or "").lower()
    cat_l = (category or "").lower()
    out: list[dict[str, Any]] = []
    for p in items:
        if max_price is not None and p["unit_price_rm"] > max_price:
            continue
        if cat_l and p.get("category", "").lower() != cat_l:
            continue
        blob = " ".join(
            [
                p["name"].lower(),
                p.get("category", "").lower(),
                " ".join(p.get("tags", [])),
            ]
        )
        if style_l and style_l not in blob:
            continue
        if q:
            tokens = [t for t in q.split() if len(t) > 2]
            if tokens and not any(
                tok in blob or any(tok in tag for tag in p.get("tags", [])) for tok in tokens
            ):
                continue
        out.append(dict(p))
    return out[:12] if out else items[:6]


def check_compatibility(
    product_id: str,
    selected_ids: list[str] | None = None,
) -> dict[str, Any]:
    time.sleep(0.15)
    selected = set(selected_ids or [])
    catalog = {p["product_id"]: p for p in _load_catalog()}
    product = catalog.get(product_id)
    if not product:
        return {"product_id": product_id, "compatible": False, "note": "Unknown product"}

    notes: list[str] = []
    compatible = True

    for req in product.get("requires", []):
        if req not in selected:
            compatible = False
            notes.append(f"Missing required component: {req}")

    if not product.get("in_stock", True):
        compatible = False
        notes.append("Out of stock (+5 days ETA)")

    min_psu = product.get("compat_psu_watts_min")
    if min_psu:
        psu_watts = 0
        for sid in selected:
            psu = catalog.get(sid, {}).get("psu_watts")
            if psu:
                psu_watts = max(psu_watts, int(psu))
        if psu_watts < min_psu:
            compatible = False
            notes.append(f"PSU {psu_watts}W insufficient; need >= {min_psu}W")

    if "nvidia" in " ".join(product.get("tags", [])).lower():
        if "gpu" in product.get("tags", []) and not any(
            "nvidia" in catalog.get(s, {}).get("name", "").lower() for s in selected if s in catalog
        ):
            pass  # this product is the nvidia gpu

    note = "; ".join(notes) if notes else "Compatible with current BOM"
    return {
        "product_id": product_id,
        "compatible": compatible,
        "note": note,
    }


def product_to_line_item(product: dict[str, Any], *, compatible: bool, note: str) -> dict[str, Any]:
    return {
        "product_id": product["product_id"],
        "product_name": product["name"],
        "product_url": product.get("url", ""),
        "quantity": 1,
        "unit_price_rm": float(product["unit_price_rm"]),
        "weight_kg": float(product.get("weight_kg", 0)),
        "compatible": compatible,
        "compatibility_note": note,
    }
