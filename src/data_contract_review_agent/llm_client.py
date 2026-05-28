"""Minimal OpenAI wrappers for optional LLM summary polish.

OpenAI is an optional boundary: imports are lazy and failures fall back to
deterministic summaries so core validation behavior remains unchanged.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_LLM_MODEL = "gpt-4.1-mini"


@dataclass(frozen=True)
class LLMClientAvailability:
    client: object | None
    reason: str | None = None


def create_openai_client() -> LLMClientAvailability:
    """Create OpenAI client lazily so base validation works without LLM dependencies."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return LLMClientAvailability(client=None, reason="OPENAI_API_KEY is not set")

    try:
        from openai import OpenAI
    except Exception:
        return LLMClientAvailability(client=None, reason="openai package is not installed")

    return LLMClientAvailability(client=OpenAI(), reason=None)


def call_openai_summary(client: object, prompt: str, model: str) -> str:
    """Execute one summary call and return markdown text from the responses API."""
    response = client.responses.create(model=model, input=prompt)
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    raise ValueError("OpenAI response did not contain output_text")
