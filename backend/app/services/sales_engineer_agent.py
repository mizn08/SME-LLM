"""ReAct-style autonomous sales engineer agent (dynamic tool routing)."""

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

TOOL_NAMES = (
    "search_products",
    "check_compatibility",
    "calculate_shipping",
    "apply_tax",
    "generate_quote",
)

_MAX_ITERATIONS = 8


def _rule_next_tool(state: dict[str, Any]) -> str:
    if not state.get("candidates"):
        return "search_products"
    if state.get("bom") and not state.get("shipping_rm"):
        return "calculate_shipping"
    if state.get("bom") and state.get("shipping_rm") is not None and not state.get("tax_rm"):
        return "apply_tax"
    if state.get("bom") and not state.get("quote_id"):
        return "generate_quote"
    if not state.get("bom"):
        return "check_compatibility"
    return "generate_quote"


def _llm_next_tool(state: dict[str, Any], brief: str) -> str | None:
    settings = get_settings()
    if not settings.active_llm_api_key:
        return None
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a sales engineer agent supervisor. Pick exactly ONE next tool. "
                    f"Tools: {', '.join(TOOL_NAMES)}. Respond JSON only: "
                    '{"tool":"search_products","reason":"..."}',
                ),
                ("human", "Brief: {brief}\nState: {state}"),
            ]
        )
        chain = prompt | ChatOpenAI(
            model=settings.active_llm_model,
            temperature=0.1,
            api_key=settings.active_llm_api_key,
            base_url=settings.active_llm_base_url,
        )
        msg = chain.invoke({"brief": brief, "state": json.dumps(state, default=str)[:2000]})
        text = str(msg.content)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            tool = data.get("tool", "")
            if tool in TOOL_NAMES:
                return tool
    except Exception:
        return None
    return None


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


def _build_bom_from_candidates(state: dict[str, Any], req: dict[str, Any]) -> None:
    budget = req.get("budget")
    constraints = [c.lower() for c in req.get("explicit_constraints", [])]
    bom: list[dict[str, Any]] = []
    selected_ids: list[str] = []

    for cand in state.get("candidates", []):
        pid = cand["product_id"]
        compat = product_catalog_service.check_compatibility(pid, selected_ids)
        if not compat["compatible"]:
            state.setdefault("reasoning", []).append(f"Rejected {pid}: {compat['note']}")
            continue
        if budget is not None:
            running = sum(i["unit_price_rm"] for i in bom) + cand["unit_price_rm"]
            if running > float(budget) * 1.05:
                state.setdefault("reasoning", []).append(f"Skipped {pid}: exceeds budget")
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
        if len(bom) >= 4:
            break
    state["bom"] = bom


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
        "trace": [{"step": "guardrail", "detail": "passed"}],
    }

    for i in range(_MAX_ITERATIONS):
        tool = _llm_next_tool(state, text) or _rule_next_tool(state)
        illegal = guardrail_service.block_illegal_actions([tool.replace("generate_", "")])
        if not illegal.safe and tool != "generate_quote":
            state["trace"].append({"step": f"iter_{i}", "detail": illegal.reason})
            break

        state["trace"].append({"step": f"iter_{i}", "tool": tool})

        if tool == "search_products":
            q = " ".join(
                filter(
                    None,
                    [
                        req.get("style"),
                        req.get("room_size"),
                        "gaming" if any("nvidia" in c.lower() or "gpu" in c.lower() for c in req.get("explicit_constraints", [])) else "",
                        "office",
                    ],
                )
            )
            cat = "gaming" if "gaming" in q.lower() or "nvidia" in text.lower() else None
            state["candidates"] = product_catalog_service.search_products(
                q,
                max_price=req.get("budget"),
                category=cat,
                style=req.get("style"),
            )
            state["reasoning"].append(f"Found {len(state['candidates'])} catalog candidates")

        elif tool == "check_compatibility":
            _build_bom_from_candidates(state, req)

        elif tool == "calculate_shipping" and state.get("bom"):
            from app.services.quote_service import _calc_shipping, _region_distance_km, _region_key

            loc = req.get("location") or location
            dist = _region_distance_km.get(_region_key(loc), 50)
            weight = sum(i.get("weight_kg", 0) * i["quantity"] for i in state["bom"])
            state["shipping_rm"] = _calc_shipping(weight, dist, "standard")
            state["reasoning"].append(f"Shipping RM {state['shipping_rm']:.2f} ({loc})")

        elif tool == "apply_tax" and state.get("bom"):
            from app.services.quote_service import _REGION_TAX_RATE, _region_key

            loc = req.get("location") or location
            rate = _REGION_TAX_RATE.get(_region_key(loc), 0.10)
            sub = sum(i["quantity"] * i["unit_price_rm"] for i in state["bom"])
            ship = state.get("shipping_rm") or 0.0
            state["tax_rm"] = round((sub + ship) * rate, 2)
            state["reasoning"].append(f"Tax RM {state['tax_rm']:.2f} at {rate*100:.0f}%")

        elif tool == "generate_quote":
            if not state.get("bom"):
                _build_bom_from_candidates(state, req)
            if not state["bom"]:
                raise ValueError("No compatible products found within constraints/budget")
            items = [QuoteLineItem(**i) for i in state["bom"]]
            payload = QuoteRequest(
                sme_id=sme_id,
                title="Autonomous Sales Engineer Quote",
                location=req.get("location") or location,
                budget_rm=req.get("budget"),
                reasoning_summary="\n".join(state.get("reasoning", [])),
                items=items,
            )
            quote = quote_service.build_quote(db, payload)
            state["quote_id"] = quote["quote_id"]
            state["quote"] = quote
            state["trace"].append({"step": "done", "detail": f"quote_id={quote['quote_id']}"})
            break

    elapsed = round(time.perf_counter() - started, 2)
    if state.get("quote_id"):
        from app.models.quote import QuoteLog

        row = db.query(QuoteLog).filter(QuoteLog.id == state["quote_id"]).first()
        if row:
            row.agent_duration_sec = elapsed
            db.commit()

    from app.services import business_value_service

    metrics = business_value_service.compute_metrics(db, sme_id)
    metrics["last_run_seconds"] = elapsed
    metrics["last_run_minutes"] = round(elapsed / 60.0, 2) if elapsed else AGENT_QUOTE_MINUTES / 60.0

    return {
        "sme_id": sme_id,
        "requirements": req,
        "agent_trace": state["trace"],
        "reasoning_summary": "\n".join(state.get("reasoning", [])),
        "quote": state.get("quote"),
        "business_value": metrics,
        "task_complete": state.get("quote_id") is not None,
    }
