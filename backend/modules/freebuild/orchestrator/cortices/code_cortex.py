"""
🟦 CodeCortex — thin wrapper around the legacy freebuild_agent.stream_agent_turn.

For now this is a PURE PASS-THROUGH so we get zero behavioural change for
code/website requests. Later we can:
  - Trim the system prompt to code-only domains (drop video/image modes)
  - Use a cheaper model variant
  - Add code-specific lessons retrieval namespace
"""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger("zenrex.cortex.code")


async def stream_code_cortex(
    project: Dict[str, Any],
    user_message: str,
    history: List[Dict[str, Any]],
    ctx_holder: Dict[str, Any],
    user_language: str = "ar",
    auth_token: Optional[str] = None,
    db=None,
    is_owner: bool = False,
    max_iterations: int = 60,
    inject_workflow_addendum: bool = False,
    shared_assets: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[str, None]:
    """Delegate to legacy freebuild_agent.stream_agent_turn.

    If `shared_assets` is provided (multi-domain coordination), prepend a
    system note so the agent knows about pre-generated logo/audio/video URLs.
    """
    msg = user_message
    if shared_assets:
        # Inject context about prior cortex outputs as a hint
        asset_hint = "\n\n📦 **أصول جاهزة من الـ cortices الأخرى — استخدمها في الكود:**\n"
        for k, v in shared_assets.items():
            asset_hint += f"  • {k}: `{v}`\n"
        msg = user_message + asset_hint

    from ...freebuild_agent import stream_agent_turn
    async for chunk in stream_agent_turn(
        project, msg, history,
        ctx_holder=ctx_holder,
        user_language=user_language,
        auth_token=auth_token,
        db=db,
        is_owner=is_owner,
        max_iterations=max_iterations,
        inject_workflow_addendum=inject_workflow_addendum,
    ):
        yield chunk
