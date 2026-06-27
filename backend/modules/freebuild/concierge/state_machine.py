"""
🤖 Concierge State Machine — manages multi-turn conversation flow.

States:
  • GATHERING_BRIEF — collecting the customer's idea
  • CONFIRMING_SCOPE — validating understanding ("هل هذا صحيح؟")
  • SETUP_REQUIRED — detected missing integration(s), need creds
  • COLLECTING_CREDS — wizard active, user pasting keys
  • VALIDATING_CREDS — testing entered keys against APIs
  • BUILDING — actual code/asset generation
  • REVIEWING — Reviewer Cortex pass
  • DELIVERED — done, project ready
  • PAUSED_AWAITING_USER — waiting on something from user (e.g. payment)

Transitions are stored per-project in MongoDB so customer can return any time.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.concierge.state")


class ConciergeState(str, Enum):
    GATHERING_BRIEF = "gathering_brief"
    CONFIRMING_SCOPE = "confirming_scope"
    SETUP_REQUIRED = "setup_required"
    COLLECTING_CREDS = "collecting_creds"
    VALIDATING_CREDS = "validating_creds"
    BUILDING = "building"
    REVIEWING = "reviewing"
    DELIVERED = "delivered"
    PAUSED_AWAITING_USER = "paused_awaiting_user"


# Valid transitions
_ALLOWED: Dict[str, set] = {
    ConciergeState.GATHERING_BRIEF: {ConciergeState.CONFIRMING_SCOPE, ConciergeState.SETUP_REQUIRED, ConciergeState.BUILDING},
    ConciergeState.CONFIRMING_SCOPE: {ConciergeState.SETUP_REQUIRED, ConciergeState.BUILDING, ConciergeState.GATHERING_BRIEF},
    ConciergeState.SETUP_REQUIRED: {ConciergeState.COLLECTING_CREDS, ConciergeState.GATHERING_BRIEF},
    ConciergeState.COLLECTING_CREDS: {ConciergeState.VALIDATING_CREDS, ConciergeState.COLLECTING_CREDS, ConciergeState.PAUSED_AWAITING_USER},
    ConciergeState.VALIDATING_CREDS: {ConciergeState.BUILDING, ConciergeState.COLLECTING_CREDS, ConciergeState.SETUP_REQUIRED},
    ConciergeState.BUILDING: {ConciergeState.REVIEWING, ConciergeState.PAUSED_AWAITING_USER, ConciergeState.SETUP_REQUIRED},
    ConciergeState.REVIEWING: {ConciergeState.DELIVERED, ConciergeState.BUILDING},
    ConciergeState.DELIVERED: {ConciergeState.GATHERING_BRIEF, ConciergeState.BUILDING},  # for follow-up changes
    ConciergeState.PAUSED_AWAITING_USER: {ConciergeState.COLLECTING_CREDS, ConciergeState.BUILDING, ConciergeState.GATHERING_BRIEF},
}


async def load_state(db, project_id: str) -> Dict[str, Any]:
    """Load current state for a project. Returns default if none."""
    if db is None or not project_id:
        return _default_state(project_id)
    try:
        doc = await db.concierge_state.find_one({"project_id": project_id}, {"_id": 0})
        if doc:
            return doc
    except Exception as e:
        logger.warning(f"[concierge.state] load failed: {e}")
    return _default_state(project_id)


async def save_state(db, project_id: str, updates: Dict[str, Any]) -> None:
    """Merge updates into the state record. Always sets updated_at."""
    if db is None or not project_id:
        return
    updates = {**updates, "updated_at": datetime.now(timezone.utc).isoformat()}
    try:
        await db.concierge_state.update_one(
            {"project_id": project_id},
            {"$set": updates, "$setOnInsert": {"project_id": project_id, "created_at": updates["updated_at"]}},
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"[concierge.state] save failed: {e}")


async def transition(db, project_id: str, new_state: ConciergeState, payload: Optional[Dict[str, Any]] = None) -> bool:
    """Move to a new state if transition is allowed. Returns True if applied."""
    current = await load_state(db, project_id)
    cur_state = current.get("state") or ConciergeState.GATHERING_BRIEF.value
    try:
        cur_enum = ConciergeState(cur_state)
    except ValueError:
        cur_enum = ConciergeState.GATHERING_BRIEF

    allowed = _ALLOWED.get(cur_enum, set())
    if new_state not in allowed and new_state != cur_enum:
        logger.warning(f"[concierge.state] illegal transition {cur_enum} → {new_state}")
        return False

    history = current.get("history", []) or []
    history.append({
        "from": cur_enum.value,
        "to": new_state.value,
        "at": datetime.now(timezone.utc).isoformat(),
        "payload": (payload or {}),
    })

    await save_state(db, project_id, {
        "state": new_state.value,
        "history": history[-50:],  # cap
        "payload": payload or {},
    })
    return True


async def add_required_integration(db, project_id: str, integration_id: str) -> None:
    """Add a needed integration to the project's setup checklist."""
    cur = await load_state(db, project_id)
    required = cur.get("required_integrations") or []
    if integration_id not in required:
        required.append(integration_id)
        await save_state(db, project_id, {"required_integrations": required})


async def remove_required_integration(db, project_id: str, integration_id: str) -> None:
    cur = await load_state(db, project_id)
    required = [i for i in (cur.get("required_integrations") or []) if i != integration_id]
    await save_state(db, project_id, {"required_integrations": required})


async def get_required_integrations(db, project_id: str) -> List[str]:
    cur = await load_state(db, project_id)
    return cur.get("required_integrations") or []


def _default_state(project_id: str) -> Dict[str, Any]:
    return {
        "project_id": project_id,
        "state": ConciergeState.GATHERING_BRIEF.value,
        "history": [],
        "required_integrations": [],
        "satisfied_integrations": [],
        "payload": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def mark_integration_satisfied(db, project_id: str, integration_id: str) -> None:
    """Move an integration from required → satisfied (creds validated)."""
    cur = await load_state(db, project_id)
    required = [i for i in (cur.get("required_integrations") or []) if i != integration_id]
    satisfied = list(cur.get("satisfied_integrations") or [])
    if integration_id not in satisfied:
        satisfied.append(integration_id)
    await save_state(db, project_id, {
        "required_integrations": required,
        "satisfied_integrations": satisfied,
    })
