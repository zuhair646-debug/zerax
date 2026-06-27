"""
🧠 Zenrex Orchestrator — Strangler Fig refactor wrapping freebuild_agent.py.

This module is a NON-INVASIVE overlay on top of the existing 11k-line
freebuild_agent.py. It:

  1. Receives a user message via a new endpoint.
  2. Classifies the intent into one or more domains (code / visual / audio /
     video / narrative / multi).
  3. Routes single-domain requests to the appropriate Cortex.
  4. Coordinates multi-domain requests by calling cortices in parallel.
  5. Streams unified SSE events to the client.

⚠️ Safety contract:
  - `freebuild_agent.py` is NEVER imported-and-modified.
  - All Cortices are new files — no edits to existing code.
  - Default classification = "code" → delegates to legacy freebuild_agent.
  - Feature-flag controlled via env `ORCHESTRATOR_ENABLED=true|false`.
  - On any Cortex error → falls back to legacy path automatically.

Public entry point:
    async for chunk in stream_via_orchestrator(project, message, ...):
        yield chunk
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

from .classifier import classify_intent_domain, DomainIntent

logger = logging.getLogger("zenrex.orchestrator")


def is_orchestrator_enabled() -> bool:
    """Feature flag — default OFF for safety. Owner enables in .env."""
    return os.environ.get("ORCHESTRATOR_ENABLED", "false").lower() == "true"


async def stream_via_orchestrator(
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
    force_domain: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Stream events using the orchestrator.

    If ORCHESTRATOR_ENABLED=false → directly delegate to legacy
    `stream_agent_turn` (zero behavioural difference).

    If `force_domain` is provided, classifier is bypassed.
    """
    # ── Hard safety: if disabled, behave exactly like legacy. ────────────
    if not is_orchestrator_enabled():
        async for chunk in _legacy_stream(
            project, user_message, history, ctx_holder, user_language,
            auth_token, db, is_owner, max_iterations, inject_workflow_addendum,
        ):
            yield chunk
        return

    # ── Classify intent (cheap regex first; LLM only if ambiguous). ──────
    if force_domain and force_domain in ("code", "visual", "audio", "video", "narrative", "multi"):
        intent = DomainIntent(primary=force_domain, secondary=[], confidence=1.0,
                              rationale=f"forced via force_domain={force_domain}")
    else:
        intent = classify_intent_domain(user_message)
    logger.info(f"[orchestrator] intent={intent.primary} secondary={intent.secondary}")

    # Emit a single 'orchestrator' event so the client knows the route.
    yield _sse("orchestrator", {
        "primary_domain": intent.primary,
        "secondary_domains": intent.secondary,
        "confidence": intent.confidence,
        "rationale": intent.rationale,
    })

    # ── Route ───────────────────────────────────────────────────────────
    # Multi-domain → fan out to parallel cortices, then merge.
    if intent.primary == "multi" or (intent.secondary and len(intent.secondary) > 0):
        async for chunk in _run_multi_domain(
            project, user_message, intent, history, ctx_holder, user_language,
            auth_token, db, is_owner, max_iterations,
        ):
            yield chunk
        return

    # Single-domain → dispatch to one cortex.
    cortex_fn = _get_cortex(intent.primary)
    try:
        async for chunk in cortex_fn(
            project=project,
            user_message=user_message,
            history=history,
            ctx_holder=ctx_holder,
            user_language=user_language,
            auth_token=auth_token,
            db=db,
            is_owner=is_owner,
            max_iterations=max_iterations,
            inject_workflow_addendum=inject_workflow_addendum,
        ):
            yield chunk
    except Exception as e:
        logger.exception(f"[orchestrator] cortex {intent.primary} failed — falling back")
        yield _sse("orchestrator_fallback", {
            "from_cortex": intent.primary,
            "to": "legacy_code_cortex",
            "reason": f"{type(e).__name__}: {str(e)[:160]}",
        })
        async for chunk in _legacy_stream(
            project, user_message, history, ctx_holder, user_language,
            auth_token, db, is_owner, max_iterations, inject_workflow_addendum,
        ):
            yield chunk


# ─────────────────────────────────────────────────────────────────────────────
# Cortex registry
# ─────────────────────────────────────────────────────────────────────────────
def _get_cortex(domain: str):
    """Return the streaming function for a given domain."""
    from .cortices.code_cortex import stream_code_cortex
    from .cortices.visual_cortex import stream_visual_cortex
    from .cortices.audio_cortex import stream_audio_cortex
    from .cortices.video_cortex import stream_video_cortex
    from .cortices.narrative_cortex import stream_narrative_cortex

    return {
        "code": stream_code_cortex,
        "visual": stream_visual_cortex,
        "audio": stream_audio_cortex,
        "video": stream_video_cortex,
        "narrative": stream_narrative_cortex,
    }.get(domain, stream_code_cortex)


# ─────────────────────────────────────────────────────────────────────────────
# Multi-domain coordination
# ─────────────────────────────────────────────────────────────────────────────
async def _run_multi_domain(
    project, user_message, intent, history, ctx_holder, user_language,
    auth_token, db, is_owner, max_iterations,
) -> AsyncGenerator[str, None]:
    """Run multiple cortices in sequence with shared context (parallel via queue).

    For now we run sequentially with a shared `accumulated_assets` dict so each
    cortex sees the previous outputs (e.g. logo → website that embeds the logo).
    Truly parallel will come once we've validated the sequencing model.
    """
    shared_assets: Dict[str, Any] = {}
    order = [intent.primary] + intent.secondary
    # Dedupe preserving order
    seen = set()
    order = [d for d in order if not (d in seen or seen.add(d))]

    yield _sse("multi_domain_plan", {
        "order": order,
        "shared_context_keys": [],
        "message": f"📋 سأنفّذ الطلب على {len(order)} مراحل متخصصة بالترتيب.",
    })

    for i, domain in enumerate(order):
        yield _sse("multi_domain_step", {
            "step": i + 1,
            "total": len(order),
            "domain": domain,
            "shared_assets_so_far": list(shared_assets.keys()),
        })
        cortex_fn = _get_cortex(domain)
        try:
            async for chunk in cortex_fn(
                project=project,
                user_message=user_message,
                history=history,
                ctx_holder=ctx_holder,
                user_language=user_language,
                auth_token=auth_token,
                db=db,
                is_owner=is_owner,
                max_iterations=max_iterations,
                inject_workflow_addendum=False,
                shared_assets=shared_assets,
            ):
                yield chunk
                # Capture any 'asset_produced' events into shared_assets
                if "asset_produced" in chunk:
                    try:
                        import json
                        for line in chunk.split("\n"):
                            if line.startswith("data:"):
                                d = json.loads(line[5:].strip())
                                if "asset_type" in d and "asset_url" in d:
                                    shared_assets[d["asset_type"]] = d["asset_url"]
                    except Exception:
                        pass
        except Exception as e:
            logger.exception(f"[orchestrator/multi] domain {domain} failed")
            yield _sse("multi_domain_step_failed", {
                "step": i + 1,
                "domain": domain,
                "error": f"{type(e).__name__}: {str(e)[:160]}",
            })
            continue

    yield _sse("multi_domain_complete", {
        "domains_executed": order,
        "shared_assets": list(shared_assets.keys()),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _sse(event: str, data: Dict[str, Any]) -> str:
    import json
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _legacy_stream(
    project, user_message, history, ctx_holder, user_language,
    auth_token, db, is_owner, max_iterations, inject_workflow_addendum,
) -> AsyncGenerator[str, None]:
    """Delegate to the original freebuild_agent.stream_agent_turn — pure pass-through."""
    from ..freebuild_agent import stream_agent_turn
    async for chunk in stream_agent_turn(
        project, user_message, history,
        ctx_holder=ctx_holder,
        user_language=user_language,
        auth_token=auth_token,
        db=db,
        is_owner=is_owner,
        max_iterations=max_iterations,
        inject_workflow_addendum=inject_workflow_addendum,
    ):
        yield chunk
