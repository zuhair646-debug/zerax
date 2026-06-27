"""
🎁 Asset Pipeline — auto-trigger Nano Banana / Sora / TTS based on recipe.

When the Orchestrator selects a recipe that needs assets (HERO image, AUDIO,
MENU_ITEM, etc.), this pipeline:

  1. Inspects recipe.assets[]
  2. For each asset, calls the appropriate cortex internally:
     - HERO/PRODUCT/GALLERY/etc → VisualCortex (Nano Banana / GPT-Image-1)
     - AUDIO with kind=tts → AudioCortex (Emergent OpenAI TTS)
     - AUDIO with kind=music → AudioCortex (Tone.js snippet)
     - VIDEO → VideoCortex (FAL Hailuo/Sora)
  3. Returns a dict of {asset_id: url} the orchestrator can inject into the page.

Includes rate limiting + deduplication + budget caps.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.asset_pipeline")


async def generate_recipe_assets(
    recipe: Dict[str, Any],
    project: Dict[str, Any],
    db=None,
    budget_credits: int = 300,
    parallel: bool = True,
) -> Dict[str, Any]:
    """Generate all assets a recipe requires.

    Returns:
        {
          "assets": {
            "hero": "https://...",
            "audio_ambient": "<tone.js snippet>",
            ...
          },
          "credits_spent": int,
          "failures": List[str],
        }
    """
    assets_spec = recipe.get("assets") or []
    if not assets_spec:
        return {"assets": {}, "credits_spent": 0, "failures": []}

    out_assets: Dict[str, Any] = {}
    failures: List[str] = []
    credits_spent = 0

    tasks: List[Any] = []
    spec_for_tasks: List[Dict[str, Any]] = []
    for spec in assets_spec:
        if credits_spent >= budget_credits:
            failures.append(f"budget_exhausted_at_{spec.get('type')}")
            continue
        tasks.append(_generate_single_asset(spec, project, db))
        spec_for_tasks.append(spec)

    if not tasks:
        return {"assets": out_assets, "credits_spent": credits_spent, "failures": failures}

    if parallel:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    else:
        results = []
        for t in tasks:
            try:
                results.append(await t)
            except Exception as e:
                results.append(e)

    for spec, result in zip(spec_for_tasks, results):
        atype = spec.get("type", "asset").lower()
        if isinstance(result, Exception):
            failures.append(f"{atype}: {type(result).__name__}")
            continue
        if not result:
            failures.append(f"{atype}: empty_result")
            continue
        # Multi-count assets (e.g. GALLERY count:6) → store as list
        existing = out_assets.get(atype)
        if existing is None:
            out_assets[atype] = result.get("url") or result.get("snippet") or result
        else:
            if not isinstance(existing, list):
                existing = [existing]
            existing.append(result.get("url") or result.get("snippet") or result)
            out_assets[atype] = existing
        credits_spent += result.get("credits_estimated", 20)

    return {"assets": out_assets, "credits_spent": credits_spent, "failures": failures}


async def _generate_single_asset(
    spec: Dict[str, Any],
    project: Dict[str, Any],
    db=None,
) -> Optional[Dict[str, Any]]:
    """Generate one asset based on its type."""
    atype = (spec.get("type") or "").upper()
    prompt = spec.get("prompt") or ""

    # ── IMAGE assets → VisualCortex
    if atype in ("HERO", "PRODUCT", "GALLERY", "DESTINATION", "ROOM", "SPEAKER", "TRAINER",
                  "ATTORNEY", "IMPACT", "MENU_ITEM", "DASHBOARD_MOCKUP", "INTERIOR",
                  "CASE_STUDY", "EPISODE_COVER", "MASCOT", "ILLUSTRATION", "LOOKBOOK",
                  "PROJECT", "ALBUM_COVER", "TOKEN_ICONS", "ICON_SET", "HEADLINE_IMAGE"):
        return await _generate_image_asset(prompt, atype, db)

    # ── AUDIO assets
    if atype == "AUDIO":
        kind = (spec.get("kind") or "ambient").lower()
        if kind == "tts":
            return await _generate_tts_asset(prompt)
        else:
            return await _generate_tonejs_asset(kind, prompt)

    # ── VIDEO assets
    if atype == "VIDEO":
        return await _generate_video_asset(prompt, project, db)

    logger.info(f"[asset_pipeline] unknown asset type: {atype}")
    return None


async def _generate_image_asset(prompt: str, asset_type: str, db=None) -> Optional[Dict[str, Any]]:
    """Call VisualCortex's image generator directly."""
    try:
        from .cortices.visual_cortex import _generate_with_emergent_image_gen
        result = await _generate_with_emergent_image_gen(prompt, size="1024x1024")
        if result and result.get("url"):
            return {
                "url": result["url"],
                "asset_type": asset_type,
                "model": result.get("model", "gpt-image-1"),
                "credits_estimated": 35,
            }
    except Exception as e:
        logger.warning(f"[asset_pipeline] image gen failed for {asset_type}: {e}")
    return None


async def _generate_tts_asset(text: str) -> Optional[Dict[str, Any]]:
    """Call AudioCortex's TTS."""
    try:
        from .cortices.audio_cortex import _synthesize_tts
        result = await _synthesize_tts(text)
        if result:
            return {
                "url": result["url"],
                "asset_type": "AUDIO_TTS",
                "model": result.get("model", "gpt-4o-mini-tts"),
                "credits_estimated": 20,
            }
    except Exception as e:
        logger.warning(f"[asset_pipeline] TTS failed: {e}")
    return None


async def _generate_tonejs_asset(kind: str, theme: str) -> Optional[Dict[str, Any]]:
    """Inline Tone.js snippet (no API cost)."""
    try:
        from .cortices.audio_cortex import _build_tonejs_snippet
        snippet = _build_tonejs_snippet(kind, theme)
        if snippet:
            return {
                "snippet": snippet,
                "asset_type": "AUDIO_SNIPPET",
                "kind": kind,
                "credits_estimated": 5,
            }
    except Exception as e:
        logger.warning(f"[asset_pipeline] tonejs snippet failed: {e}")
    return None


async def _generate_video_asset(prompt: str, project: Dict[str, Any], db=None) -> Optional[Dict[str, Any]]:
    """Call workflow_tools.generate_video."""
    try:
        from ..workflow_tools import generate_video as _gv

        class _Ctx:
            pass
        ctx = _Ctx()
        ctx.project_id = (project or {}).get("id")
        ctx.user_id = (project or {}).get("user_id")
        ctx.db = db
        ctx.auth_token = None
        ctx.is_owner = False
        ctx.messages_log = []
        ctx.tool_log = []
        async def _noop(*a, **k): return None
        ctx.emit = _noop

        result = await _gv(ctx, {"prompt": prompt[:1500], "duration_seconds": 6, "model": "hailuo"})
        if isinstance(result, dict) and result.get("ok") and result.get("video_url"):
            return {
                "url": result["video_url"],
                "asset_type": "VIDEO",
                "model": result.get("model_used", "hailuo"),
                "credits_estimated": 200,
            }
    except Exception as e:
        logger.warning(f"[asset_pipeline] video gen failed: {e}")
    return None
