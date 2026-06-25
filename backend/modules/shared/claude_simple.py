"""
Pure Anthropic Direct — No Emergent, No Middleman.

This module is the SINGLE source of truth for Claude calls from
non-streaming code paths (planner, code reviewer, owner engineer).

Independence guarantee:
    • Calls go DIRECTLY to api.anthropic.com via the official `anthropic` SDK.
    • There is NO fallback to Emergent. If ANTHROPIC_API_KEY is missing or
      Anthropic is unreachable, the call fails LOUDLY so the platform owner
      sees the problem instead of silently routing through a third party.

Public surface:
    await ask_claude(system, user_message, ...) → str   # one-turn helper
    which_provider() → "anthropic_direct" | "none"
"""
from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger("zenrex.shared.claude_simple")

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


def which_provider() -> str:
    """Returns 'anthropic_direct' if the platform is independent, else 'none'.

    Emergent is deliberately NOT reported here — this platform no longer
    routes any Claude traffic through it.
    """
    if (os.environ.get("ANTHROPIC_API_KEY") or "").strip():
        return "anthropic_direct"
    return "none"


async def _ask_anthropic_direct(
    system: str,
    user_message: str,
    model: str,
    max_tokens: int,
    timeout: float,
) -> str:
    from anthropic import AsyncAnthropic
    key = os.environ["ANTHROPIC_API_KEY"].strip()
    client = AsyncAnthropic(api_key=key, timeout=timeout)
    resp = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    parts: list[str] = []
    for block in (resp.content or []):
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()


async def ask_claude(
    system: str,
    user_message: str,
    session_id: str = "anon",  # noqa: ARG001 — kept for API compatibility
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4000,
    timeout: float = 90.0,
) -> str:
    """One-shot Claude call — Anthropic Direct ONLY.

    Returns the text response (may be empty on failure).
    Raises RuntimeError if no Anthropic key is configured.
    """
    if which_provider() != "anthropic_direct":
        raise RuntimeError(
            "ANTHROPIC_API_KEY غير مهيّأ. ضع المفتاح في backend/.env — "
            "Zenrex لا يستخدم أي مزود وسيط."
        )
    return await asyncio.wait_for(
        _ask_anthropic_direct(system, user_message, model, max_tokens, timeout),
        timeout=timeout + 5,
    )
