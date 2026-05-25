"""BNPL and grant marketplace — BNPL list from malaysia_bnpl_providers.json."""

from __future__ import annotations

from typing import Any

from app.services.bnpl_catalog_service import list_bnpl_providers, load_catalog

_GRANT_AND_CREDIT: list[dict[str, Any]] = [
    {
        "id": "tekun",
        "name": "TEKUN Nasional",
        "plan_label": "TEKUN Micro Credit",
        "type": "micro_credit",
        "description": "Government-backed micro-financing for Bumiputera and general SMEs.",
        "apply_url": "https://www.tekun.gov.my/",
        "sandbox": True,
    },
    {
        "id": "mdec_grant",
        "name": "MDEC Digital Grant",
        "plan_label": "MDEC Digital Grant",
        "type": "grant",
        "description": "Digitalisation grants for Malaysian SMEs adopting technology.",
        "apply_url": "https://mdec.my/",
        "sandbox": True,
    },
    {
        "id": "sme_corp",
        "name": "SME Corp Malaysia",
        "plan_label": "SME Corp schemes",
        "type": "grant",
        "description": "Federal SME agency — financing and grant programmes.",
        "apply_url": "https://www.smecorp.gov.my/",
        "sandbox": True,
    },
]


def list_providers(*, bnpl_only: bool = False) -> list[dict[str, Any]]:
    bnpl = list_bnpl_providers()
    if bnpl_only:
        return bnpl
    return bnpl + _GRANT_AND_CREDIT


def get_provider(provider_id: str) -> dict[str, Any] | None:
    for p in list_providers():
        if p["id"] == provider_id:
            return p
    return None


def track_application(sme_id: int, provider_id: str, status: str = "submitted") -> dict[str, Any]:
    provider = get_provider(provider_id)
    if not provider:
        return {"status": "error", "message": "Unknown provider"}
    return {
        "sme_id": sme_id,
        "provider": provider,
        "application_status": status,
        "tracking_id": f"APP-{sme_id}-{provider_id[:4].upper()}",
    }
