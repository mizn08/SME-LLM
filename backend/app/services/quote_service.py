"""Deterministic quote builder with shipping/tax/ETA and persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.quote import QuoteLog
from app.schemas import QuoteRequest
from app.services import guardrail_service

_REGION_TAX_RATE = {
    "kuala lumpur": 0.10,
    "selangor": 0.10,
    "penang": 0.08,
    "johor": 0.09,
    "sabah": 0.07,
    "sarawak": 0.07,
}

_REGION_DISTANCE_KM = {
    "kuala lumpur": 20,
    "selangor": 40,
    "penang": 360,
    "johor": 330,
    "sabah": 1620,
    "sarawak": 1180,
}

_SERVICE_LEVEL_MULTIPLIER = {"economy": 1.0, "standard": 1.25, "express": 1.6}


def _region_key(location: str) -> str:
    return (location or "kuala lumpur").strip().lower()


def _calc_shipping(weight_kg: float, distance_km: float, service_level: str) -> float:
    level_mult = _SERVICE_LEVEL_MULTIPLIER.get((service_level or "standard").lower(), 1.25)
    base = 8.0
    distance_fee = (distance_km / 100.0) * 2.5
    weight_fee = weight_kg * 1.8
    return round((base + distance_fee + weight_fee) * level_mult, 2)


def _calc_eta_days(distance_km: float, all_in_stock: bool) -> int:
    eta = 3 + int(distance_km / 200)
    if not all_in_stock:
        eta += 5
    return eta


def build_quote(db: Session, payload: QuoteRequest) -> dict[str, Any]:
    settings = get_settings()
    location_key = _region_key(payload.location)
    tax_rate = _REGION_TAX_RATE.get(location_key, 0.10)
    distance_km = _REGION_DISTANCE_KM.get(location_key, 50)

    items = [item.model_dump() for item in payload.items]
    subtotal = round(sum(item["quantity"] * item["unit_price_rm"] for item in items), 2)
    total_weight = sum(item.get("weight_kg", 0.0) * item["quantity"] for item in items)
    all_in_stock = all(item.get("compatible", True) for item in items)
    shipping = _calc_shipping(total_weight, distance_km, payload.service_level)
    taxable = max(subtotal + shipping - payload.discount_rm, 0.0)
    tax = round(taxable * tax_rate, 2)
    grand_total = round(taxable + tax, 2)
    eta_days = _calc_eta_days(distance_km, all_in_stock)

    budget_check = guardrail_service.enforce_budget_cap(
        budget_rm=payload.budget_rm,
        total_rm=grand_total,
        tolerance=settings.BUDGET_TOLERANCE_PCT,
    )
    if not budget_check.safe:
        raise ValueError(f"Quote blocked by guardrail: {budget_check.reason}")

    quote = QuoteLog(
        sme_id=payload.sme_id,
        title=payload.title,
        location=payload.location,
        line_items=items,
        subtotal_rm=subtotal,
        shipping_rm=shipping,
        tax_rm=tax,
        discount_rm=payload.discount_rm,
        grand_total_rm=grand_total,
        tax_rate=tax_rate,
        estimated_delivery_days=eta_days,
        reasoning_summary=payload.reasoning_summary,
        budget_rm=payload.budget_rm,
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)

    return {
        "quote_id": quote.id,
        "sme_id": payload.sme_id,
        "title": payload.title,
        "location": payload.location,
        "items": items,
        "breakdown": {
            "subtotal_rm": subtotal,
            "shipping_rm": shipping,
            "tax_rm": tax,
            "discount_rm": payload.discount_rm,
            "grand_total_rm": grand_total,
            "tax_rate": tax_rate,
            "estimated_delivery_days": eta_days,
        },
        "within_budget": True if payload.budget_rm is not None else None,
        "reasoning_summary": payload.reasoning_summary or "Deterministic pricing + compatibility checks applied.",
        "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    }
