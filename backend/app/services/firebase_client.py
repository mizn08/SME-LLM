"""Firebase Admin SDK — FCM send when credentials are configured."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_initialized = False


def is_configured() -> bool:
    s = get_settings()
    if s.FCM_ENABLED is False:
        return False
    return bool(s.firebase_credentials_dict)


def _credentials_dict() -> dict[str, Any] | None:
    return get_settings().firebase_credentials_dict


def ensure_initialized() -> bool:
    global _initialized
    if _initialized:
        return True
    creds = _credentials_dict()
    if not creds:
        return False
    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(creds))
        _initialized = True
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Firebase init failed: %s", exc)
        return False


def send_to_token(
    token: str,
    *,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Send one FCM message. Returns {ok, message_id} or {ok: False, error}."""
    if not ensure_initialized():
        return {"ok": False, "error": "firebase_not_configured"}
    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items() if v is not None},
            token=token,
        )
        message_id = messaging.send(message)
        return {"ok": True, "message_id": message_id}
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
        if "registration-token-not-registered" in err.lower() or "not registered" in err.lower():
            return {"ok": False, "error": "invalid_token", "detail": err}
        return {"ok": False, "error": err}


def send_multicast(
    tokens: list[str],
    *,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not tokens:
        return {"ok": True, "success_count": 0, "failure_count": 0}
    if not ensure_initialized():
        return {"ok": False, "error": "firebase_not_configured"}
    try:
        from firebase_admin import messaging

        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items() if v is not None},
            tokens=tokens,
        )
        batch = messaging.send_each_for_multicast(message)
        return {
            "ok": True,
            "success_count": batch.success_count,
            "failure_count": batch.failure_count,
            "responses": [
                {"ok": r.success, "message_id": r.message_id, "error": str(r.exception) if r.exception else None}
                for r in batch.responses
            ],
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
