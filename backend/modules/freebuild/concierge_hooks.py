"""
🪝 Concierge Hooks — auto-detect integrations and inject wizard before code.

This middleware runs at the START of every freebuild chat turn:
  1. Reads the user's message
  2. Calls detect_required_integrations()
  3. If missing creds → emits wizard cards as SSE events
  4. Marks the build as PAUSED until creds are provided
  5. The AI's system prompt is augmented with brand_dna + concierge state

Designed to be called from `freebuild_chat.py` before the agent stream starts.
"""
from __future__ import annotations

import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

from .concierge.credential_vault import has_credential
from .concierge.knowledge import (
    detect_required_integrations, get_integration,
)
from .concierge.setup_wizard import (
    build_wizard_flow, card_cost_summary, card_intro,
)
from .concierge.state_machine import (
    ConciergeState, add_required_integration, mark_integration_satisfied,
    get_required_integrations, load_state, transition,
)

logger = logging.getLogger("zenrex.concierge_hooks")


def _detect_language(text: str) -> str:
    """Quick heuristic: Arabic if it contains Arabic chars, else English."""
    if not text:
        return "ar"
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    return "ar" if arabic_chars > 3 else "en"


async def precheck_integrations(
    db,
    user_id: str,
    project_id: str,
    user_message: str,
) -> Dict[str, Any]:
    """Run before the AI starts coding. Returns:
        {
          "should_block_build": bool,
          "pending": List[{integration_id, missing_keys}],
          "satisfied": List[integration_id],
          "language": str,
          "wizard_cards": List[dict],
          "system_prompt_hint": str  # to inject into AI's system message
        }
    """
    language = _detect_language(user_message)
    detected = detect_required_integrations(user_message, language)

    pending: List[Dict[str, Any]] = []
    satisfied: List[str] = []

    for iid in detected:
        integ = get_integration(iid)
        if not integ:
            continue
        creds = integ.get("required_credentials") or []
        if not creds:
            satisfied.append(iid)
            continue
        # Skip optional integrations that have a "use_our_default" fallback
        if integ.get("note_ar") and "نوفّر" in integ.get("note_ar", ""):
            # We have a default; treat as satisfied unless user explicitly wants own
            satisfied.append(iid)
            continue
        missing = []
        for c in creds:
            if not await has_credential(db, user_id, c["key"]):
                missing.append(c["key"])
        if missing:
            pending.append({"integration_id": iid, "missing_keys": missing})
            if db is not None:
                await add_required_integration(db, project_id, iid)
        else:
            satisfied.append(iid)
            if db is not None:
                await mark_integration_satisfied(db, project_id, iid)

    # Build wizard cards for pending
    wizard_cards: List[Dict[str, Any]] = []
    if pending:
        # Cost summary card up top
        wizard_cards.append(card_cost_summary([p["integration_id"] for p in pending], language))
        for p in pending:
            wizard_cards.extend(build_wizard_flow(p["integration_id"], language))

    should_block = bool(pending)

    # Build system-prompt hint for the AI (so it knows the context)
    hint_lines = []
    if satisfied:
        labels = [get_integration(i).get(f"{language}_label", i) for i in satisfied if get_integration(i)]
        hint_lines.append(f"✅ Already configured: {', '.join(labels)}")
    if pending:
        pending_labels = [get_integration(p["integration_id"]).get(f"{language}_label", p["integration_id"])
                          for p in pending if get_integration(p["integration_id"])]
        hint_lines.append(f"⏸️ Awaiting customer setup for: {', '.join(pending_labels)}")
        hint_lines.append(
            "DO NOT start coding any feature requiring these. Acknowledge the customer's request, "
            "show what you'll build, and tell them you've prepared a Setup Wizard."
            if language == "en" else
            "لا تبدأ بناء أي ميزة تحتاج هذه المفاتيح. اعترف بطلب العميل، اشرح ما ستبنيه، "
            "وأخبره أنك جهّزت Setup Wizard في الجانب."
        )
    system_prompt_hint = "\n".join(hint_lines)

    # Transition state if needed
    if db is not None and should_block:
        await transition(db, project_id, ConciergeState.SETUP_REQUIRED, {"pending": pending})

    return {
        "should_block_build": should_block,
        "pending": pending,
        "satisfied": satisfied,
        "language": language,
        "wizard_cards": wizard_cards,
        "system_prompt_hint": system_prompt_hint,
        "detected_integrations": detected,
    }


def stream_wizard_as_sse(check_result: Dict[str, Any]):
    """Yields SSE events for the wizard cards so frontend can render them."""
    import json
    if not check_result.get("wizard_cards"):
        return
    yield f"event: concierge_setup_required\ndata: {json.dumps({'pending_count': len(check_result['pending']), 'language': check_result['language']}, ensure_ascii=False)}\n\n"
    for card in check_result["wizard_cards"]:
        yield f"event: concierge_wizard_card\ndata: {json.dumps(card, ensure_ascii=False)}\n\n"
    yield f"event: concierge_setup_done\ndata: {json.dumps({'awaiting_user_action': True}, ensure_ascii=False)}\n\n"


async def resume_after_setup(db, user_id: str, project_id: str) -> Dict[str, Any]:
    """Called after the user submits all required creds. Validates state can resume."""
    state = await load_state(db, project_id)
    required = state.get("required_integrations") or []
    if not required:
        await transition(db, project_id, ConciergeState.BUILDING, {"resumed": True})
        return {"can_resume": True, "state": "building"}
    # Still has pending
    return {"can_resume": False, "still_pending": required}
