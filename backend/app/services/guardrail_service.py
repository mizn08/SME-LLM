"""Guardrails for agent/user input and budget constraints."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


_INJECTION_PATTERNS = (
    r"ignore (all|previous|prior) instructions",
    r"reveal (the )?(system|developer) prompt",
    r"bypass (safety|guardrails|policy)",
    r"tool.?call purchase",
    r"execute (shell|command|script)",
)

_ILLEGAL_ACTIONS = {"purchase", "checkout", "wire_transfer", "delete_data", "drop_table"}


@dataclass
class GuardrailResult:
    safe: bool
    reason: str = ""


def sanitize_text(text: str, *, max_len: int = 8000) -> str:
    """Trim length but keep newlines so multi-question prompts stay detectable."""
    raw = (text or "").strip()
    if not raw:
        return ""
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines()]
    compact = "\n".join(line for line in lines if line)
    return compact[:max_len]


def detect_prompt_injection(text: str) -> GuardrailResult:
    lowered = (text or "").lower()
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return GuardrailResult(False, f"suspicious_pattern:{pattern}")
    return GuardrailResult(True, "ok")


def block_illegal_actions(actions: Iterable[str]) -> GuardrailResult:
    lowered = {a.lower().strip() for a in actions}
    illegal = sorted(lowered.intersection(_ILLEGAL_ACTIONS))
    if illegal:
        return GuardrailResult(False, f"illegal_actions:{','.join(illegal)}")
    return GuardrailResult(True, "ok")


def enforce_budget_cap(*, budget_rm: float | None, total_rm: float, tolerance: float = 0.05) -> GuardrailResult:
    if budget_rm is None:
        return GuardrailResult(True, "no_budget")
    allowed_max = budget_rm * (1.0 + tolerance)
    if total_rm > allowed_max:
        return GuardrailResult(False, f"budget_exceeded:{total_rm:.2f}>{allowed_max:.2f}")
    return GuardrailResult(True, "ok")
