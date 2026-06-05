"""Multi-agent orchestration: Grant, BNPL, and Cash specialists (LangChain)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.sme import SMEProfile
from app.services import data_processor, decision_engine, guardrail_service, rag_service
from app.services.langchain_tools import make_tools


@dataclass
class AgentAdvice:
    lead_agent: str
    summary: str
    agents: list[dict[str, str]]
    recommendation: dict[str, Any] | None
    rag_snippet: str | None
    agent_trace: list[dict[str, Any]]


def _route_agent(goal: str, category: str) -> str:
    text = f"{goal} {category}".lower()
    if any(w in text for w in ("grant", "scheme", "gov", "cggs", "madani", "tekun", "sme bank")):
        return "grant"
    if any(w in text for w in ("bnpl", "installment", "pay later", "split")):
        return "bnpl"
    if any(w in text for w in ("cash", "burn", "runway", "liquidity", "preserve")):
        return "cash"
    return "supervisor"


def _grant_agent(db: Session, sme: SMEProfile, category: str) -> str:
    schemes = decision_engine._eligible_gov_schemes(db, sme, category)  # noqa: SLF001
    if not schemes:
        return "No matching government schemes for this profile and purchase category."
    top = schemes[0]
    return (
        f"Grant specialist: consider {top.scheme_name} ({top.agency}), "
        f"up to RM {top.max_amount_rm or 0:,.0f}, {top.approval_speed_label}."
    )


def _bnpl_agent(db: Session, sme: SMEProfile, amount: float, category: str) -> str:
    df = data_processor.load_transactions_df(db, sme.id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    r = decision_engine.decide(db, sme, kpis, amount, category, None)
    if r.recommendation_type.lower() != "bnpl":
        return f"BNPL specialist: BNPL may not be optimal; engine suggests {r.recommendation_type} ({r.product_name})."
    return f"BNPL specialist: {r.product_name} — {r.explanation}"


def _cash_agent(db: Session, sme: SMEProfile) -> str:
    df = data_processor.load_transactions_df(db, sme.id)
    k = data_processor.compute_kpis_from_transactions(df)
    if k["days_cash_on_hand"] < 45:
        return (
            f"Cash specialist: runway is tight ({k['days_cash_on_hand']:.0f} days cash). "
            "Prioritise grants or BNPL to preserve working capital."
        )
    return (
        f"Cash specialist: {k['days_cash_on_hand']:.0f} days cash on hand — "
        "you have flexibility; compare total cost before drawing credit."
    )


def _langchain_agent_run(db: Session, sme_id: int, goal: str, amount: float, category: str) -> tuple[str | None, list[dict[str, Any]]]:
    settings = get_settings()
    if not settings.active_llm_api_key:
        return None, [{"step": "llm_disabled", "detail": "No active LLM API key configured"}]
    sanitized_goal = guardrail_service.sanitize_text(goal, max_len=600)
    safety = guardrail_service.detect_prompt_injection(sanitized_goal)
    if not safety.safe:
        return None, [{"step": "guardrail_block", "detail": safety.reason}]
    try:
        import time

        from langchain.agents import AgentExecutor, create_openai_tools_agent
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_openai import ChatOpenAI

        from app.services.llm_client import chutes_api_keys, is_rate_limited

        tools = make_tools(db, sme_id)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are the SME Advisor supervisor for Malaysia. Use tools to answer. "
                    "Coordinate BNPL, grants, and cash preservation. Be concise.",
                ),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ]
        )
        user_input = (
            f"Goal: {sanitized_goal}. Purchase RM {amount:,.0f}, category: {category}. "
            "Call tools and give a unified recommendation."
        )
        keys = chutes_api_keys(settings) if settings.CHUTES_API_KEY else [settings.active_llm_api_key]
        last_exc: Exception | None = None
        for attempt, api_key in enumerate(keys):
            try:
                llm = ChatOpenAI(
                    model=settings.CHUTES_CHAT_MODEL or settings.active_llm_model,
                    temperature=0.2,
                    api_key=api_key,
                    base_url=settings.active_llm_base_url,
                    max_retries=0,
                    request_timeout=int(getattr(settings, "CHUTES_CHAT_TIMEOUT_SEC", 90)),
                )
                agent = create_openai_tools_agent(llm, tools, prompt)
                executor = AgentExecutor(
                    agent=agent, tools=tools, verbose=False, max_iterations=4, return_intermediate_steps=True
                )
                result = executor.invoke({"input": user_input})
                trace = [
                    {"step": "agent_start", "detail": "LangChain tool agent invoked"},
                    {
                        "step": "tool_iterations",
                        "detail": str(len(result.get("intermediate_steps", []))),
                    },
                ]
                for idx, item in enumerate(result.get("intermediate_steps", []), start=1):
                    action = getattr(item[0], "tool", "unknown_tool")
                    trace.append({"step": f"tool_{idx}", "detail": str(action)})
                final_output = guardrail_service.sanitize_text(str(result.get("output", "")), max_len=1200)
                return final_output, trace
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if is_rate_limited(exc) and attempt < len(keys) - 1:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise
        if last_exc:
            raise last_exc
    except Exception as exc:  # noqa: BLE001
        return None, [{"step": "llm_error", "detail": f"{type(exc).__name__}: {exc}"}]


def run_multi_agent(
    db: Session,
    sme_id: int,
    purchase_amount: float,
    purchase_category: str,
    goal: str = "best financing option",
) -> AgentAdvice:
    sme = db.query(SMEProfile).filter(SMEProfile.id == sme_id).first()
    if not sme:
        return AgentAdvice(
            lead_agent="error",
            summary="SME not found",
            agents=[],
            recommendation=None,
            rag_snippet=None,
            agent_trace=[{"step": "error", "detail": "SME not found"}],
        )

    lead = _route_agent(goal, purchase_category)
    agents_out = [
        {"name": "grant", "insight": _grant_agent(db, sme, purchase_category)},
        {"name": "bnpl", "insight": _bnpl_agent(db, sme, purchase_amount, purchase_category)},
        {"name": "cash", "insight": _cash_agent(db, sme)},
    ]

    df = data_processor.load_transactions_df(db, sme_id)
    kpis = data_processor.compute_kpis_from_transactions(df)
    decision = decision_engine.decide(db, sme, kpis, purchase_amount, purchase_category, None)
    recommendation = {
        "recommendation_type": decision.recommendation_type,
        "product_name": decision.product_name,
        "explanation": decision.explanation,
        "confidence": decision.confidence,
        "cash_preserved_rm": decision.cash_preserved_rm,
    }

    rag = rag_service.financing_quote_advice(
        db,
        sme_id,
        quote_total_rm=float(purchase_amount),
        purchase_amount=float(purchase_amount),
        purchase_category=purchase_category,
    )
    rag_answer = rag.get("answer") or ""
    rag_snippet = rag_answer[:600] if rag_answer else None

    trace: list[dict[str, Any]] = [
        {"step": "route", "detail": f"lead_agent={lead}"},
        {"step": "specialists", "detail": "grant,bnpl,cash"},
        {"step": "engine_decision", "detail": recommendation["recommendation_type"]},
        {"step": "rag_sync", "detail": rag.get("mode") or "none"},
    ]
    llm_summary, llm_trace = _langchain_agent_run(db, sme_id, goal, purchase_amount, purchase_category)
    trace.extend(llm_trace)
    if llm_summary:
        summary = llm_summary
    else:
        lead_insight = next((a["insight"] for a in agents_out if a["name"] == lead), agents_out[0]["insight"])
        summary = (
            f"Lead agent: {lead}. {lead_insight} "
            f"Final engine pick: {decision.recommendation_type} — {decision.product_name}."
        )

    return AgentAdvice(
        lead_agent=lead,
        summary=summary,
        agents=agents_out,
        recommendation=recommendation,
        rag_snippet=rag_snippet,
        agent_trace=trace,
    )
