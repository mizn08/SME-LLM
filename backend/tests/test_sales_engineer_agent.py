"""Unit tests for LLM-supervised sales engineer routing."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services import sales_engineer_agent as sea


def test_tool_prerequisites_block_shipping_without_bom():
    state = {"candidates": [{"product_id": "p1"}], "bom": []}
    result = sea._tool_prerequisites("calculate_shipping", state)
    assert not result.safe
    assert result.reason == "need_bom_first"


def test_tool_prerequisites_allow_search_anytime():
    state = {"candidates": [], "bom": []}
    assert sea._tool_prerequisites("search_products", state).safe


def test_correct_tool_for_block():
    state = {"candidates": [], "bom": []}
    assert sea._correct_tool_for_block("need_bom_first", state) == "search_products"
    state["candidates"] = [{"product_id": "p1"}]
    assert sea._correct_tool_for_block("need_bom_first", state) == "check_compatibility"


def test_choose_next_tool_uses_llm_plan_queue():
    state = {
        "candidates": [],
        "bom": [],
        "_recent_tools": [],
        "_llm_plan_queue": [("search_products", "start catalog search")],
    }
    tool, source, detail = sea._choose_next_tool(state, "POS for cafe")
    assert tool == "search_products"
    assert source == "llm"
    assert detail == "start catalog search"
    assert state["_llm_plan_queue"] == []


def test_choose_next_tool_uses_llm_when_valid():
    state = {"candidates": [], "bom": [], "_recent_tools": []}
    with patch.object(sea, "_llm_next_tool", return_value=("search_products", "catalog first")):
        tool, source, detail = sea._choose_next_tool(state, "POS for cafe")
    assert tool == "search_products"
    assert source == "llm"
    assert detail == "catalog first"


def test_choose_next_tool_guardrail_corrects_invalid_llm_pick():
    state = {"candidates": [], "bom": [], "_recent_tools": []}
    with patch.object(
        sea,
        "_llm_next_tool",
        side_effect=[("calculate_shipping", "ship early"), (None, "retry_failed")],
    ):
        tool, source, _ = sea._choose_next_tool(state, "POS for cafe")
    assert tool == "search_products"
    assert source == "guardrail_corrected"


def test_choose_next_tool_rule_fallback_without_llm():
    state = {"candidates": [], "bom": [], "_recent_tools": []}
    with patch.object(sea, "_llm_next_tool", return_value=(None, "no_llm_key")):
        tool, source, _ = sea._choose_next_tool(state, "POS for cafe")
    assert tool == "search_products"
    assert source == "rule_fallback"


def test_choose_next_tool_unsticks_repeated_tool():
    state = {"candidates": [{"product_id": "p1"}], "bom": [], "_recent_tools": ["search_products", "search_products"]}
    tool, source, _ = sea._choose_next_tool(state, "POS for cafe")
    assert tool == "check_compatibility"
    assert source == "rule_unstick"


@pytest.mark.integration
def test_run_sales_engineer_rule_fallback_completes(db_session):
    out = sea.run_sales_engineer(
        db_session,
        sme_id=1,
        brief_text="Need a POS system for a small cafe, budget RM 8000, Kuala Lumpur",
        location="Kuala Lumpur",
    )
    assert out["task_complete"] is True
    assert out["quote"] is not None
    assert out["agent_mode"] in ("llm_supervised", "rule_fallback")
    tools = [s.get("tool") for s in out["agent_trace"] if s.get("tool")]
    assert "search_products" in tools
    assert "generate_quote" in tools
