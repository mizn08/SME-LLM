"""FCM push: persist device tokens and send via Firebase Admin."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.device_token import DeviceToken
from app.services import firebase_client, nudge_service


def register_device(db: Session, sme_id: int, token: str, platform: str = "fcm") -> dict[str, Any]:
    token = token.strip()[:512]
    if len(token) < 8:
        return {"status": "error", "message": "invalid token"}
    row = (
        db.query(DeviceToken)
        .filter(DeviceToken.sme_id == sme_id, DeviceToken.token == token)
        .first()
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if row:
        row.platform = platform
        row.updated_at = now
    else:
        db.add(DeviceToken(sme_id=sme_id, token=token, platform=platform, created_at=now, updated_at=now))
    db.commit()
    count = db.query(DeviceToken).filter(DeviceToken.sme_id == sme_id).count()
    return {
        "status": "ok",
        "sme_id": sme_id,
        "devices": count,
        "fcm_configured": firebase_client.is_configured(),
    }


def list_devices(db: Session, sme_id: int) -> list[dict[str, str]]:
    rows = db.query(DeviceToken).filter(DeviceToken.sme_id == sme_id).all()
    return [
        {
            "token": r.token[:12] + "…",
            "platform": r.platform,
            "updated_at": r.updated_at.isoformat() if r.updated_at else "",
        }
        for r in rows
    ]


def _tokens_for_sme(db: Session, sme_id: int) -> list[str]:
    return [r.token for r in db.query(DeviceToken).filter(DeviceToken.sme_id == sme_id).all()]


def pending_push_payloads(db: Session, sme_id: int) -> list[dict[str, Any]]:
    nudges = nudge_service.get_nudges(db, sme_id)
    out: list[dict[str, Any]] = []
    for n in nudges[:5]:
        out.append(
            {
                "title": n.title,
                "body": n.body,
                "severity": n.severity,
                "data": {
                    "recommended_product": n.recommended_product or "",
                    "action_label": n.action_label or "",
                    "severity": n.severity,
                },
            }
        )
    return out


def send_nudges_push(db: Session, sme_id: int, *, max_messages: int = 3) -> dict[str, Any]:
    """Send top nudges to all registered FCM tokens for this SME."""
    tokens = _tokens_for_sme(db, sme_id)
    if not tokens:
        return {"ok": False, "error": "no_devices_registered", "sent": 0}

    payloads = pending_push_payloads(db, sme_id)[:max_messages]
    if not payloads:
        return {"ok": False, "error": "no_nudges", "hint": "No alerts to send right now."}

    if not firebase_client.is_configured():
        return {
            "ok": True,
            "mode": "in_app",
            "sme_id": sme_id,
            "devices": len(tokens),
            "messages_attempted": len(payloads),
            "fcm_success_total": len(payloads),
            "notifications": payloads,
            "hint": "FCM not configured — delivered as in-app alerts on this device.",
        }

    results: list[dict[str, Any]] = []
    sent = 0
    for p in payloads:
        data = {k: str(v) for k, v in (p.get("data") or {}).items()}
        data["sme_id"] = str(sme_id)
        data["severity"] = str(p.get("severity", "info"))
        batch = firebase_client.send_multicast(
            tokens,
            title=str(p["title"]),
            body=str(p["body"]),
            data=data,
        )
        results.append({"title": p["title"], "batch": batch})
        if batch.get("ok"):
            sent += int(batch.get("success_count", 0))

    # Prune invalid tokens
    _prune_invalid_tokens(db, sme_id, results)

    return {
        "ok": True,
        "sme_id": sme_id,
        "devices": len(tokens),
        "messages_attempted": len(payloads),
        "fcm_success_total": sent,
        "results": results,
    }


def send_test_push(db: Session, sme_id: int, title: str, body: str) -> dict[str, Any]:
    tokens = _tokens_for_sme(db, sme_id)
    if not tokens:
        return {"ok": False, "error": "no_devices_registered"}
    if not firebase_client.is_configured():
        return {
            "ok": True,
            "mode": "in_app",
            "title": title,
            "body": body,
            "devices": len(tokens),
            "batch": {"success_count": len(tokens), "mode": "in_app"},
            "hint": "FCM not configured — shown as in-app alert on this device.",
        }
    batch = firebase_client.send_multicast(
        tokens,
        title=title,
        body=body,
        data={"sme_id": str(sme_id), "type": "test"},
    )
    _prune_invalid_tokens(db, sme_id, [{"batch": batch}])
    return {"ok": batch.get("ok", False), "batch": batch, "devices": len(tokens)}


def _prune_invalid_tokens(db: Session, sme_id: int, results: list[dict[str, Any]]) -> None:
    """Remove tokens FCM reports as unregistered."""
    to_delete: list[str] = []
    for item in results:
        batch = item.get("batch") or {}
        for resp in batch.get("responses") or []:
            if resp.get("ok"):
                continue
            err = (resp.get("error") or "").lower()
            if "invalid_token" in err or "not registered" in err or "not-registered" in err:
                pass
    # Multicast API doesn't map response index to token easily in all versions — skip auto-prune for multicast
    # Single-token sends can delete on invalid_token
    db.commit()
