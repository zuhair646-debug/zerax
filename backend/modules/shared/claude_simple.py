"""
Unified single-shot Claude helper — Independence-first.

Resolution order for the API:
    1. ANTHROPIC_API_KEY direct (the platform owner's own Anthropic key) — preferred.
    2. EMERGENT_LLM_KEY fallback via emergentintegrations — kept ONLY for
       backwards compatibility so nothing breaks before the owner sets
       their direct key.

The owner can verify which path is live by calling `which_provider()`.

Public surface:
    await ask_claude(system, user_message, ...) → str   # one-turn helper
    which_provider() → "anthropic_direct" | "emergent" | "none"
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger("zenrex.shared.claude_simple")

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


def which_provider() -> str:
    """Tell the operator which provider is active right now."""
    if (os.environ.get("ANTHROPIC_API_KEY") or "").strip():
        return "anthropic_direct"
    if (os.environ.get("EMERGENT_LLM_KEY") or "").strip():
        return "emergent"
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
    # Anthropic SDK returns a Message with content blocks (TextBlock).
    parts: list[str] = []
    for block in (resp.content or []):
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()


async def _ask_emergent_fallback(
    system: str,
    user_message: str,
    session_id: str,
    model: str,
    max_tokens: int,
) -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
    key = os.environ["EMERGENT_LLM_KEY"].strip()
    chat = LlmChat(
        api_key=key,
        session_id=session_id,
        system_message=system,
    ).with_model("anthropic", model).with_params(max_tokens=max_tokens)
    resp = await chat.send_message(UserMessage(text=user_message))
    return resp if isinstance(resp, str) else str(resp)


async def ask_claude(
    system: str,
    user_message: str,
    session_id: str = "anon",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4000,
    timeout: float = 90.0,
) -> str:
    """One-shot Claude call. Prefers direct Anthropic; falls back to Emergent.

    Returns the text response (may be empty on failure).
    Raises on configuration error (no provider available).
    """
    provider = which_provider()
    if provider == "none":
        raise RuntimeError(
            "ما فيه مزود Claude متاح. ضع ANTHROPIC_API_KEY في .env (مفضّل) "
            "أو EMERGENT_LLM_KEY (احتياطي)."
        )

    # Direct first.
    if provider == "anthropic_direct":
        try:
            return await asyncio.wait_for(
                _ask_anthropic_direct(system, user_message, model, max_tokens, timeout),
                timeout=timeout + 5,
            )
        except Exception as e:
            # Drop to emergent if available.
            logger.warning(f"[claude_simple] direct failed: {e}; trying emergent fallback")
            if (os.environ.get("EMERGENT_LLM_KEY") or "").strip():
                try:
                    return await asyncio.wait_for(
                        _ask_emergent_fallback(system, user_message, session_id, model, max_tokens),
                        timeout=timeout + 5,
                    )
                except Exception as e2:
                    logger.exception(f"[claude_simple] emergent fallback also failed: {e2}")
                    raise
            raise

    # Emergent only path.
    return await asyncio.wait_for(
        _ask_emergent_fallback(system, user_message, session_id, model, max_tokens),
        timeout=timeout + 5,
    )
