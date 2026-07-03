"""Thin wrapper around the Anthropic SDK. Import call_claude and extract_json from here."""
from __future__ import annotations

import json
import logging
import re

import anthropic

from triage_agent.shared.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 1024


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def call_claude(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    client: anthropic.Anthropic | None = None,
) -> str:
    if client is None:
        client = get_client()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text  # type: ignore[union-attr]


def extract_json(text: str) -> dict:
    """Extract a JSON object from text, handling ```json ... ``` fences."""
    # Strip code fences
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return json.loads(match.group(1))
    # Find bare JSON object (handle any prose before/after)
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(text[start:end])
    return json.loads(text)
