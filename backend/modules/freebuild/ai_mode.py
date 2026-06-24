"""
AI Mode Router — Hybrid Orchestration for Zenrex FreeBuild.

Two modes selectable from Admin panel:
  • "claude_only"  → All phases use Claude Sonnet 4.5 (default, stable).
  • "hybrid"       → Phase routing:
        Discovery / surgical edits / debug → Claude Sonnet 4.5  (discipline)
        First creative build               → OpenAI GPT-5.5      (visual flair)

The mode is a single document in MongoDB `platform_settings`.
The choice is platform-wide (not per-project) so behaviour is predictable
during the user's testing phase.

Phase detection rules (deterministic, no LLM call):
  • If project has NO existing content (current_html < 500 chars) AND
    user_message has BUILD verbs (ابني/سوي/أنشئ/build/create) → "first_design".
  • If project has existing content AND user_message matches surgical
    verbs OR has no rebuild markers → "surgical".
  • If user_message has explicit rebuild markers (من الصفر/rebuild) → "first_design".
  • Otherwise → "surgical" (safe default for existing projects).
  • discovery is a sub-phase of any of the above when the model still
    needs to ask a question — no separate routing needed; Claude handles it.

Public API:
  await get_ai_mode(db) -> str               # "claude_only" | "hybrid"
  await set_ai_mode(db, mode) -> None
  classify_phase(user_message, project) -> str   # "first_design" | "surgical"
  pick_provider(ai_mode, phase) -> (provider, model)
"""

from __future__ import annotations
import os
from typing import Any, Dict, Tuple

# Module-level constants (no magic numbers in callers)
SETTINGS_COLLECTION = "platform_settings"
SETTINGS_DOC_ID = "ai_mode"
DEFAULT_MODE = "claude_only"
VALID_MODES = {"claude_only", "hybrid_gpt", "hybrid_glm"}

# Backwards compat: accept "hybrid" as an alias for "hybrid_gpt" (the original
# Hybrid mode shipped before GLM was added). This keeps any previously-saved
# admin setting working without manual migration.
LEGACY_HYBRID_ALIAS = "hybrid"

# Provider/model identifiers
CLAUDE_PROVIDER = "anthropic"
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
GPT_PROVIDER = "openai_direct"
GPT_MODEL = "gpt-5.5"
# Zhipu GLM-5.2 — China's top-ranked design model (Design Arena #1 globally,
# 6x cheaper than GPT-5.5, OpenAI-compatible API via z.ai).
GLM_PROVIDER = "zhipu_glm"
GLM_MODEL = "glm-4.6"  # latest stable production model from Zhipu

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
            # Legacy alias: pre-GLM saves stored "hybrid" → map to hybrid_gpt
            if raw == LEGACY_HYBRID_ALIAS:
                return "hybrid_gpt"
            if raw in VALID_MODES:
                return raw
    except Exception:
        pass
    return DEFAULT_MODE


async def set_ai_mode(db: Any, mode: str) -> None:
    """Persist the AI mode. Raises ValueError if invalid."""
    # Accept the legacy alias on writes too so any external caller is forgiving
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
    """Classify the current request into a build phase.

    Pure-Python deterministic classifier — no LLM call.
    """
    msg = (user_message or "").lower()
    msg_raw = user_message or ""
    current_html = (project or {}).get("current_html") or ""
    has_content = len(current_html) > 500

    # Explicit rebuild markers → fresh design pass
    REBUILD_MARKERS = (
        "من الصفر", "من جديد", "اعد بناء", "أعد بناء", "اعد البناء",
        "اعد تصميم", "أعد تصميم", "ابدأ من جديد", "ابدأ من الصفر",
        "احذف كل شي وابدأ", "احذف الكل",
        "rebuild", "redesign", "start over", "from scratch",
    )
    if any(m in msg_raw or m in msg for m in REBUILD_MARKERS):
        return PHASE_FIRST_DESIGN

    # Build verbs on empty/near-empty project → first design
    if not has_content:
        BUILD_VERBS = (
            "ابني", "اصنع", "أنشئ", "انشئ", "اعمل لي", "سوّي لي", "سوي لي",
            "build ", "create ", "make a ", "design ",
        )
        if any(v in msg_raw or v in msg for v in BUILD_VERBS):
            return PHASE_FIRST_DESIGN
        # Empty project + ambiguous message → still treat as first_design
        # (user is likely creating something new)
        return PHASE_FIRST_DESIGN

    # Existing project + no rebuild markers → surgical edits
    return PHASE_SURGICAL


def pick_provider(ai_mode: str, phase: str) -> Tuple[str, str]:
    """Decide which (provider, model) handles this turn.

    Returns:
        Tuple of (provider_key, model_id) compatible with _stream_one_provider.
    """
    if phase == PHASE_FIRST_DESIGN:
        if ai_mode == "hybrid_gpt":
            if os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY"):
                return (GPT_PROVIDER, GPT_MODEL)
        elif ai_mode == "hybrid_glm":
            if os.environ.get("ZHIPU_API_KEY"):
                return (GLM_PROVIDER, GLM_MODEL)
    # Default: Claude for everything (also the fallback when keys are missing)
    return (CLAUDE_PROVIDER, CLAUDE_MODEL)


def describe_choice(ai_mode: str, phase: str) -> str:
    """Human-readable summary for SSE / logs."""
    provider, model = pick_provider(ai_mode, phase)
    if phase == PHASE_FIRST_DESIGN:
        if ai_mode == "hybrid_gpt" and provider == GPT_PROVIDER:
            return "Hybrid → GPT-5.5 (التصميم الإبداعي)"
        if ai_mode == "hybrid_glm" and provider == GLM_PROVIDER:
            return "Hybrid → GLM-5.2 (تصميم #1 عالمياً)"
    return "Claude Sonnet 4.5 (الانضباط والتعديل الجراحي)"
