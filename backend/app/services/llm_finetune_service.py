"""Fine-tuned SME LLM — status + optional local inference stub."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import get_settings


def finetune_status() -> dict[str, Any]:
    settings = get_settings()
    adapter = Path(settings.FINETUNE_ADAPTER_DIR)
    has_adapter = adapter.is_dir() and any(adapter.iterdir())
    return {
        "adapter_dir": str(adapter),
        "adapter_ready": has_adapter,
        "base_model": settings.FINETUNE_BASE_MODEL,
        "method": "lora_peft_stub",
        "note": "Run backend/ml_pipeline/scripts/finetune_sme_llm.py to prepare adapters.",
    }


def generate_local(prompt: str, max_tokens: int = 256) -> dict[str, Any]:
    settings = get_settings()
    adapter = Path(settings.FINETUNE_ADAPTER_DIR)
    if not adapter.is_dir() or not any(adapter.iterdir()):
        return {
            "text": None,
            "mode": "unavailable",
            "message": "No fine-tuned adapter found. Use RAG chat or configure CHUTES_API_KEY / OPENAI_API_KEY.",
        }
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        tok = AutoTokenizer.from_pretrained(settings.FINETUNE_BASE_MODEL)
        model = AutoModelForCausalLM.from_pretrained(
            settings.FINETUNE_BASE_MODEL,
            torch_dtype=torch.float32,
            device_map="cpu",
        )
        inputs = tok(prompt, return_tensors="pt")
        out = model.generate(**inputs, max_new_tokens=max_tokens)
        text = tok.decode(out[0], skip_special_tokens=True)
        return {"text": text, "mode": "local_finetuned_stub"}
    except Exception as exc:  # noqa: BLE001
        return {"text": None, "mode": "error", "message": str(exc)}
