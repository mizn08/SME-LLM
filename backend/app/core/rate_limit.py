"""Per-SME / per-token rate limit key for slowapi."""

from __future__ import annotations

from fastapi import Request
from slowapi.util import get_remote_address


def rate_limit_key(request: Request) -> str:
    sme = request.query_params.get("sme_id") or request.headers.get("X-SME-ID")
    if sme:
        return f"sme:{sme}"
    if request.method in ("POST", "PATCH", "PUT"):
        try:
            # Best-effort for JSON bodies (not consumed — Starlette may cache on some setups)
            pass
        except Exception:
            pass
    auth = request.headers.get("Authorization")
    if auth:
        return f"auth:{auth[:48]}"
    return get_remote_address(request)
