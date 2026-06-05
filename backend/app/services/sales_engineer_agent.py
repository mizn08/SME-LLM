"""Autonomous sales engineer — LLM-supervised tool loop with guardrail boundaries."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas import QuoteLineItem, QuoteRequest
from app.services import guardrail_service, product_catalog_service, quote_service, requirement_parser_service
from app.services.business_value_service import AGENT_QUOTE_MINUTES
from app.services.guardrail_service import GuardrailResult

TOOL_NAMES = (
    "search_products",
    "check_compatibility",
    "calculate_shipping",
    "apply_tax",
    "generate_quote",
)

_MAX_ITERATIONS = 10

_TOOL_HELP = {
    "search_products": "Search catalog for items matching the client brief (can repeat with new keywords).",
    "check_compatibility": "Build BOM from candidates; validate compatibility and budget.",
    "calculate_shipping": "Estimate shipping to client location (requires BOM).",
    "apply_tax": "Apply regional SST/tax (requires BOM).",
    "generate_quote": "Persist final quote to database (requires BOM or candidates).",
}


def _state_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_count": len(state.get("candidates") or []),
        "bom_items": len(state.get("bom") or []),
        "shipping_rm": state.get("shipping_rm"),
        "tax_rm": state.get("tax_rm"),
        "quote_id": state.get("quote_id"),
        "recent_tools": list(state.get("_recent_tools") or [])[-5:],
    }


def _rule_next_tool(state: dict[str, Any]) -> str:
    """Deterministic fallback when LLM is unavailable or stuck."""
    if not state.get("candidates"):
        return "search_products"
    if not state.get("bom"):
        if state.get("bom_built"):
            return "generate_quote"
        return "check_compatibility"
    if state.get("shipping_rm") is None:
        return "calculate_shipping"
    if state.get("tax_rm") is None:
        return "apply_tax"
    if not state.get("quote_id"):
        return "generate_quote"
    return "generate_quote"


def _tool_prerequisites(tool: str, state: dict[str, Any]) -> GuardrailResult:
    bom = state.get("bom") or []
    candidates = state.get("candidates") or []
    if tool == "search_products":
        return GuardrailResult(True, "ok")
    if tool == "check_compatibility":
        if not candidates:
            return GuardrailResult(False, "need_candidates_first")
        return GuardrailResult(True, "ok")
    if tool == "calculate_shipping":
        if not bom:
            return GuardrailResult(False, "need_bom_first")
        return GuardrailResult(True, "ok")
    if tool == "apply_tax":
        if not bom:
            return GuardrailResult(False, "need_bom_first")
        return GuardrailResult(True, "ok")
    if tool == "generate_quote":
        if not bom and not candidates:
            return GuardrailResult(False, "need_search_first")
        return GuardrailResult(True, "ok")
    return GuardrailResult(False, f"unknown_tool:{tool}")


def _correct_tool_for_block(reason: str, state: dict[str, Any]) -> str:
    if reason == "need_search_first":
        return "search_products"
    if reason == "need_candidates_first":
        return "search_products"
    if reason == "need_bom_first":
        return "check_compatibility" if state.get("candidates") else "search_products"
    return _rule_next_tool(state)


def _parse_llm_json(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _llm_plan_workflow(brief: str) -> tuple[list[tuple[str, str]] | None, str]:
    """One-shot LLM plan — avoids per-step API calls that exceed client timeouts."""
    settings = get_settings()
    if not settings.active_llm_api_key:
        return None, "no_llm_key"
    try:
        from app.services.llm_client import invoke_chat

        tool_lines = "\n".join(f"- {name}: {_TOOL_HELP[name]}" for name in TOOL_NAMES)
        text = invoke_chat(
            [
                (
                    "system",
                    "You are an autonomous sales engineer supervisor for Malaysian SMEs. "
                    "Given a client brief, plan the full tool sequence to search catalog, "
                    "validate compatibility, price shipping/tax, and generate a quote.\n\n"
                    f"Tools:\n{tool_lines}\n\n"
                    "Return JSON only: "
                    '{"plan":[{"tool":"search_products","reason":"short why"},...]}\n'
                    "Typical order: search_products → check_compatibility → calculate_shipping "
                    "→ apply_tax → generate_quote. Always end with generate_quote.",
                ),
                ("human", f"Client brief:\n{brief}"),
            ],
            temperature=0.1,
            settings=settings,
            max_tokens=512,
            max_rounds=2,
        )
        data = _parse_llm_json(text)
        if not data:
            return None, "llm_parse_failed"
        raw_plan = data.get("plan") or data.get("steps") or []
        steps: list[tuple[str, str]] = []
        for item in raw_plan:
            if not isinstance(item, dict):
                continue
            tool = str(item.get("tool", "")).strip()
            reason = str(item.get("reason", "")).strip() or "planned"
            if tool in TOOL_NAMES:
                steps.append((tool, reason))
        if not steps:
            return None, "llm_empty_plan"
        if steps[-1][0] != "generate_quote":
            steps.append(("generate_quote", "finalize quote"))
        return steps, "llm_plan"
    except Exception as exc:  # noqa: BLE001
        return None, f"llm_error:{type(exc).__name__}"


def _llm_next_tool(
    state: dict[str, Any],
    brief: str,
    *,
    blocked_tool: str | None = None,
    blocked_reason: str | None = None,
) -> tuple[str | None, str]:
    settings = get_settings()
    if not settings.active_llm_api_key:
        return None, "no_llm_key"
    try:
        from app.services.llm_client import invoke_chat

        tool_lines = "\n".join(f"- {name}: {_TOOL_HELP[name]}" for name in TOOL_NAMES)
        snapshot = json.dumps(_state_snapshot(state), indent=2)
        extra = ""
        if blocked_tool and blocked_reason:
            extra = (
                f"\nYour previous choice '{blocked_tool}' was BLOCKED by guardrails: {blocked_reason}. "
                "Pick a different valid tool."
            )
        text = invoke_chat(
            [
                (
                    "system",
                    "You are an autonomous sales engineer supervisor for Malaysian SMEs. "
                    "Pick exactly ONE next tool based on the client brief and current state. "
                    "You may re-run search_products if results are poor. "
                    "Do not call generate_quote until compatibility and pricing steps are reasonable.\n\n"
                    f"Tools:\n{tool_lines}\n\n"
                    'Respond with JSON only: {"tool":"search_products","reason":"short why"}',
                ),
                ("human", f"Client brief:\n{brief}\n\nState:\n{snapshot}{extra}"),
            ],
            temperature=0.1,
            settings=settings,
            max_tokens=256,
            max_rounds=2,
        )
        data = _parse_llm_json(text)
        if not data:
            return None, "llm_parse_failed"
        tool = str(data.get("tool", "")).strip()
        reason = str(data.get("reason", "")).strip() or "llm_choice"
        if tool in TOOL_NAMES:
            return tool, reason
        return None, f"llm_invalid_tool:{tool}"
    except Exception as exc:  # noqa: BLE001
        return None, f"llm_error:{type(exc).__name__}"


def _choose_next_tool(state: dict[str, Any], brief: str) -> tuple[str, str, str]:
    """Returns (tool, routing_source, detail)."""
    queue: list[tuple[str, str]] = state.get("_llm_plan_queue") or []
    while queue:
        tool, reason = queue.pop(0)
        state["_llm_plan_queue"] = queue
        prereq = _tool_prerequisites(tool, state)
        if not prereq.safe:
            corrected = _correct_tool_for_block(prereq.reason, state)
            if corrected not in {t for t, _ in queue}:
                queue.insert(0, (corrected, f"corrected:{prereq.reason}"))
                state["_llm_plan_queue"] = queue
            return corrected, "guardrail_corrected", f"{prereq.reason}->{corrected}"
        illegal = guardrail_service.block_illegal_actions([tool.replace("generate_", "")])
        if not illegal.safe and tool != "generate_quote":
            continue
        return tool, "llm", reason

    recent = state.get("_recent_tools") or []
    if len(recent) >= 2 and recent[-1] == recent[-2]:
        tool = _rule_next_tool(state)
        return tool, "rule_unstick", "repeated_tool_breaker"

    tool, llm_reason = _llm_next_tool(state, brief)
    if tool:
        prereq = _tool_prerequisites(tool, state)
        if not prereq.safe:
            retry_tool, retry_reason = _llm_next_tool(
                state,
                brief,
                blocked_tool=tool,
                blocked_reason=prereq.reason,
            )
            if retry_tool:
                retry_pre = _tool_prerequisites(retry_tool, state)
                if retry_pre.safe:
                    tool = retry_tool
                    llm_reason = retry_reason
                    prereq = retry_pre
                else:
                    tool = _correct_tool_for_block(prereq.reason, state)
                    return tool, "guardrail_corrected", f"{prereq.reason}->{tool}"
            else:
                tool = _correct_tool_for_block(prereq.reason, state)
                return tool, "guardrail_corrected", f"{prereq.reason}->{tool}"

        illegal = guardrail_service.block_illegal_actions([tool.replace("generate_", "")])
        if not illegal.safe and tool != "generate_quote":
            return _rule_next_tool(state), "guardrail_block", illegal.reason

        return tool, "llm", llm_reason

    fallback = _rule_next_tool(state)
    return fallback, "rule_fallback", llm_reason


def _merge_requirements(brief: str | None, requirements: dict[str, Any] | None) -> dict[str, Any]:
    if requirements:
        base = dict(requirements)
    else:
        base = requirement_parser_service.parse_requirement_text(brief or "")
    if brief and not base.get("explicit_constraints"):
        low = brief.lower()
        if "nvidia" in low:
            base.setdefault("explicit_constraints", []).append("gpu must be NVIDIA")
        if "no drill" in low:
            base.setdefault("explicit_constraints", []).append("no drilling")
    return base


def _build_bom_from_candidates(
    state: dict[str, Any],
    req: dict[str, Any],
    *,
    budget_slack: float = 0.82,
) -> None:
    budget = req.get("budget")
    constraints = [c.lower() for c in req.get("explicit_constraints", [])]
    purchase_category = (req.get("purchase_category") or "").lower()
    bom: list[dict[str, Any]] = []
    selected_ids: list[str] = []
    max_items = 1 if purchase_category in ("pos", "ecommerce") else 4
    if budget is not None:
        slack = 1.0 if purchase_category in ("pos", "ecommerce") else budget_slack
        subtotal_cap = float(budget) * slack
    else:
        subtotal_cap = None

    for cand in state.get("candidates", []):
        pid = cand["product_id"]
        compat = product_catalog_service.check_compatibility(pid, selected_ids)
        if not compat["compatible"]:
            state.setdefault("reasoning", []).append(f"Rejected {pid}: {compat['note']}")
            continue
        if purchase_category == "pos" and "pos" not in cand.get("tags", []):
            continue
        if purchase_category == "ecommerce" and "ecommerce" not in cand.get("tags", []):
            continue
        if subtotal_cap is not None:
            running = sum(i["unit_price_rm"] for i in bom) + cand["unit_price_rm"]
            if running > subtotal_cap:
                state.setdefault("reasoning", []).append(f"Skipped {pid}: exceeds budget after shipping/tax")
                continue
        if any("nvidia" in c for c in constraints) and "gpu" in cand.get("tags", []):
            if "nvidia" not in cand.get("name", "").lower():
                continue
        line = product_catalog_service.product_to_line_item(
            cand, compatible=True, note=compat["note"]
        )
        bom.append(line)
        selected_ids.append(pid)
        state.setdefault("reasoning", []).append(f"Added {cand['name']}: {compat['note']}")
        if len(bom) >= max_items:
            break
    state["bom"] = bom
    state["bom_built"] = True


def _search_products(state: dict[str, Any], text: str, req: dict[str, Any]) -> None:
    low = text.lower()
    sme_terms: list[str] = []
    for term in (
        "ecommerce",
        "e-commerce",
        "website",
        "inventory",
        "pos",
        "fnb",
        "retail",
        "agro",
        "router",
        "equipment",
        "digital",
    ):
        if term.replace("-", "") in low.replace("-", "") or term in low:
            sme_terms.append(term.replace("-", ""))
    if any(k in low for k in ("e-commerce", "ecommerce", "website", "inventory sync")):
        sme_terms = ["ecommerce", "website", "inventory"]
    q = " ".join(
        dict.fromkeys(
            filter(
                None,
                sme_terms
                or [
                    req.get("purchase_category"),
                    req.get("style"),
                    "pos" if "pos" in low else None,
                ],
            )
        )
    )
    cat = (
        "agro"
        if "agro" in low
        else (
            "digital"
            if any(
                t in low
                for t in ("pos", "router", "gpu", "digital", "e-commerce", "ecommerce", "website")
            )
            else None
        )
    )
    state["candidates"] = product_catalog_service.search_products(
        q,
        max_price=req.get("budget"),
        category=cat,
        style=req.get("style"),
    )
    state.setdefault("reasoning", []).append(f"Found {len(state['candidates'])} catalog candidates")


def _execute_tool(
    db: Session,
    *,
    tool: str,
    state: dict[str, Any],
    text: str,
    req: dict[str, Any],
    sme_id: int,
    location: str,
) -> bool:
    """Run one tool. Returns True if agent loop should stop (quote done)."""
    if tool == "search_products":
        _search_products(state, text, req)
        return False

    if tool == "check_compatibility":
        _build_bom_from_candidates(state, req)
        return False

    if tool == "calculate_shipping" and state.get("bom"):
        from app.services.quote_service import _REGION_DISTANCE_KM, _calc_shipping, _region_key

        loc = req.get("location") or location
        dist = _REGION_DISTANCE_KM.get(_region_key(loc), 50)
        weight = sum(i.get("weight_kg", 0) * i["quantity"] for i in state["bom"])
        state["shipping_rm"] = _calc_shipping(weight, dist, "standard")
        state.setdefault("reasoning", []).append(f"Shipping RM {state['shipping_rm']:.2f} ({loc})")
        return False

    if tool == "apply_tax" and state.get("bom"):
        from app.services.quote_service import _REGION_TAX_RATE, _region_key

        loc = req.get("location") or location
        rate = _REGION_TAX_RATE.get(_region_key(loc), 0.10)
        sub = sum(i["quantity"] * i["unit_price_rm"] for i in state["bom"])
        ship = state.get("shipping_rm") or 0.0
        state["tax_rm"] = round((sub + ship) * rate, 2)
        state.setdefault("reasoning", []).append(f"Tax RM {state['tax_rm']:.2f} at {rate*100:.0f}%")
        return False

    if tool == "generate_quote":
        if not state.get("bom"):
            _build_bom_from_candidates(state, req)
        if not state["bom"]:
            _build_bom_from_candidates(state, req, budget_slack=1.0)
        if not state["bom"]:
            raise ValueError(
                "No compatible products found within budget. "
                "Try a higher budget or a different purchase brief."
            )
        items = [QuoteLineItem(**i) for i in state["bom"]]
        payload = QuoteRequest(
            sme_id=sme_id,
            title="SME Advisor Financing Quote",
            location=req.get("location") or location,
            budget_rm=req.get("budget"),
            reasoning_summary="\n".join(state.get("reasoning", [])),
            items=items,
        )
        quote = quote_service.build_quote(db, payload)
        state["quote_id"] = quote["quote_id"]
        state["quote"] = quote
        state["trace"].append({"step": "done", "detail": f"quote_id={quote['quote_id']}"})
        return True

    return False


def run_sales_engineer(
    db: Session,
    *,
    sme_id: int,
    brief_text: str | None = None,
    requirements: dict[str, Any] | None = None,
    location: str = "Kuala Lumpur",
) -> dict[str, Any]:
    started = time.perf_counter()
    text = guardrail_service.sanitize_text(brief_text or json.dumps(requirements or {}))
    safety = guardrail_service.detect_prompt_injection(text)
    if not safety.safe:
        raise ValueError(f"Guardrail blocked request: {safety.reason}")

    req = _merge_requirements(brief_text, requirements)
    state: dict[str, Any] = {
        "requirements": req,
        "candidates": [],
        "bom": [],
        "shipping_rm": None,
        "tax_rm": None,
        "quote_id": None,
        "reasoning": [],
        "_recent_tools": [],
        "_llm_plan_queue": [],
        "trace": [{"step": "guardrail", "detail": "passed"}],
    }
    routing_sources: list[str] = []

    plan, plan_meta = _llm_plan_workflow(text)
    if plan:
        state["_llm_plan_queue"] = plan
        state["trace"].append({"step": "llm_plan", "detail": f"{len(plan)} steps · {plan_meta}"})

    for i in range(_MAX_ITERATIONS):
        if state.get("quote_id"):
            break

        tool, source, detail = _choose_next_tool(state, text)
        routing_sources.append(source)
        prereq = _tool_prerequisites(tool, state)
        if not prereq.safe:
            state["trace"].append(
                {"step": f"iter_{i}", "tool": tool, "source": source, "detail": f"skipped:{prereq.reason}"}
            )
            continue

        state["trace"].append(
            {
                "step": f"iter_{i}",
                "tool": tool,
                "source": source,
                "detail": detail,
            }
        )
        state["_recent_tools"] = (state.get("_recent_tools") or []) + [tool]

        done = _execute_tool(
            db,
            tool=tool,
            state=state,
            text=text,
            req=req,
            sme_id=sme_id,
            location=location,
        )
        if done:
            break

    agent_mode = "llm_supervised" if any(s == "llm" for s in routing_sources) else "rule_fallback"

    elapsed = round(time.perf_counter() - started, 2)
    if state.get("quote_id"):
        from app.models.quote import QuoteLog

        row = db.query(QuoteLog).filter(QuoteLog.id == state["quote_id"]).first()
        if row:
            row.agent_duration_sec = elapsed
            db.commit()

    from app.services import business_value_service, rag_service

    metrics = business_value_service.compute_metrics(db, sme_id)
    metrics["last_run_seconds"] = elapsed
    metrics["last_run_minutes"] = round(elapsed / 60.0, 2) if elapsed else AGENT_QUOTE_MINUTES / 60.0

    rag_answer: str | None = None
    rag_mode: str | None = None
    rag_sources: list[dict[str, Any]] = []
    quote = state.get("quote")
    if quote:
        grand = quote.get("breakdown", {}).get("grand_total_rm", 0)
        budget = req.get("budget") or grand
        rag = rag_service.financing_quote_advice(
            db,
            sme_id,
            quote_total_rm=float(grand),
            purchase_amount=float(budget) if budget else float(grand),
            purchase_category=req.get("purchase_category"),
        )
        rag_answer = rag.get("answer")
        rag_mode = rag.get("mode")
        rag_sources = rag.get("sources", [])
        state["trace"].append({"step": "rag_sync", "detail": rag_mode or "bm25"})

    error: str | None = None
    if not state.get("quote_id"):
        if state.get("candidates") and not state.get("bom"):
            error = (
                "No line items fit the budget after tax/shipping allowance. "
                "Increase budget or simplify the brief."
            )
        elif not state.get("candidates"):
            error = "No catalog products matched the brief. Try different keywords (POS, equipment, digital)."

    return {
        "sme_id": sme_id,
        "requirements": req,
        "agent_trace": state["trace"],
        "agent_mode": agent_mode,
        "reasoning_summary": "\n".join(state.get("reasoning", [])),
        "quote": quote,
        "business_value": metrics,
        "task_complete": state.get("quote_id") is not None,
        "error": error,
        "rag_answer": rag_answer,
        "rag_mode": rag_mode,
        "rag_sources": rag_sources,
    }
