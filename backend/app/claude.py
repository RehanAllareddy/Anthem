"""Thin wrapper around the Anthropic SDK for JSON-shaped calls.

Never log prompts or responses from here: they can contain what a user shared
about how they're feeling.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any, Dict

import anthropic

from .config import get_settings

log = logging.getLogger(__name__)


class ClaudeUnavailable(RuntimeError):
    """Raised when Claude can't produce a usable answer (refusal, outage, bad JSON)."""


@lru_cache
def _client() -> anthropic.Anthropic:
    key = get_settings().anthropic_api_key
    # With no key in .env the SDK falls back to ANTHROPIC_API_KEY / `ant auth login`.
    return anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()


def claude_json(
    *,
    system: str,
    user: str,
    schema: Dict[str, Any],
    max_tokens: int = 8000,
    effort: str = "medium",
) -> Dict[str, Any]:
    settings = get_settings()
    try:
        response = _client().beta.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={
                "effort": effort,
                "format": {"type": "json_schema", "schema": schema},
            },
            # If a safety classifier declines, let the API retry on its recommended fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.APIStatusError as e:
        log.warning("Claude API error status=%s request_id=%s", e.status_code, e.request_id)
        raise ClaudeUnavailable("api_error") from e
    except anthropic.APIConnectionError as e:
        log.warning("Claude API connection error")
        raise ClaudeUnavailable("connection_error") from e

    if response.stop_reason == "refusal":
        log.warning("Claude declined request_id=%s", response._request_id)
        raise ClaudeUnavailable("refusal")
    if response.stop_reason == "max_tokens":
        raise ClaudeUnavailable("truncated")

    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        raise ClaudeUnavailable("no_text")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ClaudeUnavailable("bad_json") from e
