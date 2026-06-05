"""Shared Chutes/OpenAI client with key rotation, streaming, and 429 retry."""

from __future__ import annotations

import time
from collections.abc import Iterator

from app.core.config import Settings, get_settings


def chutes_api_keys(settings: Settings | None = None) -> list[str]:
    return (settings or get_settings()).chutes_api_keys


def is_rate_limited(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "maximum capacity" in text or "rate limit" in text or "too many requests" in text


def is_retryable_llm_error(exc: Exception) -> bool:
    """Try next key/model on rate limits, timeouts, and missing models."""
    if is_rate_limited(exc):
        return True
    text = str(exc).lower()
    return (
        "model not found" in text
        or "404" in text
        or "timeout" in text
        or "timed out" in text
        or "connection" in text
        or "503" in text
        or "502" in text
    )


def _models_to_try(settings: Settings, *, prefer_fast: bool = True) -> list[str]:
    fast = getattr(settings, "CHUTES_CHAT_MODEL", None) or settings.active_llm_model
    heavy = settings.active_llm_model
    fallback = getattr(settings, "CHUTES_FALLBACK_MODEL", None)
    if prefer_fast:
        models = [fast]
        if heavy not in models:
            models.append(heavy)
    else:
        models = [heavy]
        if fast not in models:
            models.append(fast)
    # Skip known-invalid Chutes models (e.g. old Qwen ids in .env)
    if fallback and fallback not in models and "qwen" not in fallback.lower():
        models.append(fallback)
    return list(dict.fromkeys(m for m in models if m))


def _to_langchain_messages(messages: list[tuple[str, str]]):
    """Build message objects without ChatPromptTemplate (avoids KeyError on JSON braces)."""
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    out = []
    for role, content in messages:
        if role == "system":
            out.append(SystemMessage(content=content))
        elif role in ("human", "user"):
            out.append(HumanMessage(content=content))
        elif role in ("ai", "assistant"):
            out.append(AIMessage(content=content))
        else:
            out.append(HumanMessage(content=content))
    return out


def _make_llm(
    settings: Settings,
    model: str,
    api_key: str,
    *,
    temperature: float,
    timeout: int,
    max_tokens: int | None = None,
):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens or int(getattr(settings, "CHUTES_MAX_TOKENS", 1024)),
        api_key=api_key,
        base_url=settings.active_llm_base_url,
        max_retries=0,
        request_timeout=timeout,
    )


def invoke_chat(
    messages: list[tuple[str, str]],
    *,
    temperature: float | None = None,
    settings: Settings | None = None,
    prefer_fast: bool = True,
    max_rounds: int | None = None,
    max_tokens: int | None = None,
) -> str:
    """Invoke chat model with retries across keys, rounds, and optional fallback model."""
    s = settings or get_settings()
    if not s.active_llm_api_key:
        raise RuntimeError("No LLM API key configured")
    if temperature is None:
        temperature = float(getattr(s, "CHUTES_TEMPERATURE", 0.7))

    lc_messages = _to_langchain_messages(messages)
    keys = chutes_api_keys(s) if s.uses_chutes else [s.active_llm_api_key]
    rounds = max_rounds if max_rounds is not None else min(max(int(getattr(s, "CHUTES_MAX_RETRIES", 4)), 1), 2)
    timeout = int(getattr(s, "CHUTES_CHAT_TIMEOUT_SEC", 90))
    last_exc: Exception | None = None

    for model in _models_to_try(s, prefer_fast=prefer_fast):
        for round_idx in range(rounds):
            for key_idx, api_key in enumerate(keys):
                try:
                    llm = _make_llm(
                        s,
                        model,
                        api_key,
                        temperature=temperature,
                        timeout=timeout,
                        max_tokens=max_tokens,
                    )
                    msg = llm.invoke(lc_messages)
                    return str(msg.content)
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    if not is_retryable_llm_error(exc):
                        raise
                    if is_rate_limited(exc):
                        wait = min(1 + key_idx + round_idx * 2, 8)
                        time.sleep(wait)
                    continue

    raise last_exc or RuntimeError("LLM invocation failed after retries")


def stream_chat(
    messages: list[tuple[str, str]],
    *,
    temperature: float | None = None,
    settings: Settings | None = None,
    max_tokens: int | None = None,
) -> Iterator[str]:
    """Stream tokens from the fast chat model (falls back to invoke on failure)."""
    s = settings or get_settings()
    if not s.active_llm_api_key:
        raise RuntimeError("No LLM API key configured")
    if temperature is None:
        temperature = float(getattr(s, "CHUTES_TEMPERATURE", 0.7))

    lc_messages = _to_langchain_messages(messages)
    keys = chutes_api_keys(s) if s.uses_chutes else [s.active_llm_api_key]
    timeout = int(getattr(s, "CHUTES_CHAT_TIMEOUT_SEC", 90))
    last_exc: Exception | None = None

    for model in _models_to_try(s, prefer_fast=True):
        for api_key in keys:
            try:
                llm = _make_llm(
                    s,
                    model,
                    api_key,
                    temperature=temperature,
                    timeout=timeout,
                    max_tokens=max_tokens,
                )
                for chunk in llm.stream(lc_messages):
                    text = getattr(chunk, "content", None)
                    if text:
                        yield str(text)
                return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if not is_retryable_llm_error(exc):
                    break

    text = invoke_chat(
        messages,
        temperature=temperature,
        settings=s,
        prefer_fast=True,
        max_tokens=max_tokens,
    )
    yield text
