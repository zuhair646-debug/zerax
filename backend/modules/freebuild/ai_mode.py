"""
AI Mode Router — Hybrid Orchestration for Zenrex FreeBuild.

Three modes selectable from Admin panel:
  - "claude_only" : Claude Sonnet 4.5 handles every phase (default, stable).
  - "hybrid_gpt"  : GPT-5.5 handles first creative build, Claude handles edits.
  - "hybrid_glm"  : GLM-4.6 (Zhipu) via OpenRouter handles first creative build,
                    Claude handles edits.

The mode is a single document in MongoDB `platform_settings`.
The choice is platform-wide (not per-project) so behaviour is predictable
during the user's testing phase.
"""

from __future__ import annotations
import os
from typing import Any, Dict, Tuple

# Module-level constants (no magic numbers in callers)
SETTINGS_COLLECTION = "platform_settings"
SETTINGS_DOC_ID = "ai_mode"
DEFAULT_MODE = "claude_only"
VALID_MODES = {"claude_only", "hybrid_gpt", "hybrid_glm"}

# Backwards compat: accept "hybrid" as an alias for "hybrid_gpt"
LEGACY_HYBRID_ALIAS = "hybrid"

# Provider/model identifiers
CLAUDE_PROVIDER = "anthropic"
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
GPT_PROVIDER = "openai_direct"
GPT_MODEL = "gpt-5.5"
# GLM-4.6 via OpenRouter (no Chinese phone-verification required).
# Set OPENROUTER_API_KEY in env. Backwards-compat: ZHIPU_API_KEY (direct z.ai)
# still honoured as fallback.
GLM_PROVIDER = "openrouter_glm"
GLM_MODEL = "z-ai/glm-4.6"

# Phase identifiers
PHASE_FIRST_DESIGN = "first_design"
PHASE_SURGICAL = "surgical"


async def get_ai_mode(db: Any) -> str:
    """Read the current AI mode from MongoDB. Defaults to claude_only."""
    if db is None:
        return DEFAULT_MODE
    try:
        doc = await db[SETTINGS_COLLECTION].find_one({"_id": SETTINGS_DOC_ID})
        if doc:
            raw = doc.get("mode")
            if raw == LEGACY_HYBRID_ALIAS:
                return "hybrid_gpt"
            if raw in VALID_MODES:
                return raw
    except Exception:
        pass
    return DEFAULT_MODE


async def set_ai_mode(db: Any, mode: str) -> None:
    """Persist the AI mode. Raises ValueError if invalid."""
    if mode == LEGACY_HYBRID_ALIAS:
        mode = "hybrid_gpt"
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid mode '{mode}'. Must be one of: {sorted(VALID_MODES)}")
    if db is None:
        raise RuntimeError("Database required to persist AI mode")
    await db[SETTINGS_COLLECTION].update_one(
        {"_id": SETTINGS_DOC_ID},
        {"$set": {"mode": mode}},
        upsert=True,
    )


def classify_phase(user_message: str, project: Dict[str, Any]) -> str:
    """Classify the current request into a build phase."""
    msg = (user_message or "").lower()
    msg_raw = user_message or ""
    current_html = (project or {}).get("current_html") or ""
    has_content = len(current_html) > 500

    REBUILD_MARKERS = (
        "from scratch", "rebuild", "redesign", "start over",
    )
    REBUILD_AR = (
        "من الصفر", "اعد بناء", "اعد تصميم", "أعد بناء", "أعد تصميم",
        "ابدأ من جديد", "ابدأ من الصفر", "احذف كل شي وابدأ",
    )
    if any(m in msg for m in REBUILD_MARKERS) or any(m in msg_raw for m in REBUILD_AR):
        return PHASE_FIRST_DESIGN

    if not has_content:
        BUILD_VERBS = ("build ", "create ", "make a ", "design ")
        BUILD_AR = ("ابني", "اصنع", "سوي", "انشئ", "اعمل")
        if any(v in msg for v in BUILD_VERBS) or any(v in msg_raw for v in BUILD_AR):
            return PHASE_FIRST_DESIGN
        return PHASE_FIRST_DESIGN

    return PHASE_SURGICAL


def pick_provider(ai_mode: str, phase: str) -> Tuple[str, str]:
    """Decide which (provider, model) handles this turn."""
    if phase == PHASE_FIRST_DESIGN:
        if ai_mode == "hybrid_gpt":
            if os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY"):
                return (GPT_PROVIDER, GPT_MODEL)
        elif ai_mode == "hybrid_glm":
            if os.environ.get("OPENROUTER_API_KEY") or os.environ.get("ZHIPU_API_KEY"):
                return (GLM_PROVIDER, GLM_MODEL)
    return (CLAUDE_PROVIDER, CLAUDE_MODEL)


def describe_choice(ai_mode: str, phase: str) -> str:
    """Human-readable summary for SSE / logs."""
    provider, model = pick_provider(ai_mode, phase)
    if phase == PHASE_FIRST_DESIGN:
        if ai_mode == "hybrid_gpt" and provider == GPT_PROVIDER:
            return "Hybrid -> GPT-5.5 (creative design)"
        if ai_mode == "hybrid_glm" and provider == GLM_PROVIDER:
            return "Hybrid -> GLM-4.6 (design rank #1 globally)"
    return "Claude Sonnet 4.5 (discipline + surgical edits)"
