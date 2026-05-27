"""Minimal OpenAI client wrappers for optional LLM summary polish."""

from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_LLM_MODEL = "gpt-4.1-mini"


@dataclass(frozen=True)
class LLMClientAvailability:
    client: object | None
    reason: str | None = None


def create_openai_client() -> LLMClientAvailability:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return LLMClientAvailability(client=None, reason="OPENAI_API_KEY is not set")

    try:
        from openai import OpenAI
    except Exception:
        return LLMClientAvailability(client=None, reason="openai package is not installed")

    return LLMClientAvailability(client=OpenAI(), reason=None)


def call_openai_summary(client: object, prompt: str, model: str) -> str:
    response = client.responses.create(model=model, input=prompt)
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    raise ValueError("OpenAI response did not contain output_text")
