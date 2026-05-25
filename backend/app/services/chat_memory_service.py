"""In-memory per-SME conversation store (max 20 turns)."""

from __future__ import annotations

from app.schemas import ChatMemoryTurn

_MAX_TURNS = 20
_store: dict[int, list[dict[str, str]]] = {}


def get_history(sme_id: int) -> list[ChatMemoryTurn]:
    raw = _store.get(sme_id, [])
    return [ChatMemoryTurn(role=t["role"], text=t["text"]) for t in raw]


def append_turn(sme_id: int, role: str, text: str) -> None:
    if sme_id not in _store:
        _store[sme_id] = []
    _store[sme_id].append({"role": role, "text": text[:2000]})
    if len(_store[sme_id]) > _MAX_TURNS:
        _store[sme_id] = _store[sme_id][-_MAX_TURNS:]


def sync_from_client(sme_id: int, history: list[ChatMemoryTurn]) -> None:
    if history:
        _store[sme_id] = [{"role": h.role, "text": h.text[:2000]} for h in history[-_MAX_TURNS:]]


def context_prefix(sme_id: int, max_turns: int = 6) -> str:
    turns = _store.get(sme_id, [])[-max_turns:]
    if not turns:
        return ""
    lines = [f"{t['role'].upper()}: {t['text'][:400]}" for t in turns]
    return "Recent conversation:\n" + "\n".join(lines) + "\n\n"


def clear(sme_id: int) -> None:
    _store.pop(sme_id, None)
