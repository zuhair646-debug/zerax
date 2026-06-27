"""
🌐 Concierge HTTP Routes — endpoints the frontend calls during wizard flow.

Mounted under `/api/concierge/*`:
  - GET  /credentials/list                       → list user's saved keys
  - POST /credentials/save                       → save + validate
  - POST /credentials/validate/{key_name}        → validate without saving
  - DELETE /credentials/{key_name}               → remove
  - GET  /integrations/list                      → list all known integrations
  - GET  /integrations/{id}                      → details + setup steps
  - POST /project/{pid}/detect-needs             → from message → required integrations
  - GET  /project/{pid}/state                    → current state machine state
  - POST /project/{pid}/state/transition         → force a state transition (admin/debug)
  - GET  /project/{pid}/wizard                   → next card to render
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .credential_vault import (
    delete_credential, get_credential, has_credential,
    list_credentials, mark_validated, mask_for_display, store_credential,
)
from .knowledge import (
    detect_required_integrations, get_integration,
    list_integrations, render_setup_instructions_ar, render_setup_instructions_en,
)
from .setup_wizard import (
    build_wizard_flow, card_cost_summary, card_success,
)
from .state_machine import (
    ConciergeState, add_required_integration, get_required_integrations,
    load_state, mark_integration_satisfied, save_state, transition,
)
from .validators import validate_by_key_name

logger = logging.getLogger("zenrex.concierge.routes")

router = APIRouter(prefix="/api/concierge", tags=["concierge"])


# ─────────────────── Auth helper (lightweight) ───────────────────
async def _get_user_id(request: Request) -> str:
    """Get user_id from request. Falls back to anonymous_<ip> for unauthenticated."""
    # Try to use existing auth middleware (if any)
    user = getattr(request.state, "user", None)
    if user and getattr(user, "id", None):
        return str(user.id)
    if isinstance(user, dict) and user.get("id"):
        return str(user["id"])
    # Fallback: anonymous (still scoped per IP)
    client = request.client.host if request.client else "anon"
    return f"anon_{client}"


async def _get_db(request: Request):
    db = getattr(request.app.state, "db", None)
    if db is None:
        db = getattr(request.app.state, "mongo", None)
    if db is None:
        # Build directly from env if not in app.state
        try:
            import os
            from motor.motor_asyncio import AsyncIOMotorClient
            client = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db = client[os.environ["DB_NAME"]]
            request.app.state.db = db
        except Exception as e:
            logger.error(f"db not available: {e}")
            raise HTTPException(500, "database not available")
    return db


# ─────────────────── Schemas ───────────────────
class SaveCredBody(BaseModel):
    key_name: str
    value: str
    metadata: Optional[Dict[str, Any]] = None


class DetectNeedsBody(BaseModel):
    message: str
    language: str = "auto"


class StateTransitionBody(BaseModel):
    new_state: str
    payload: Optional[Dict[str, Any]] = None


# ─────────────────── Credential endpoints ───────────────────
@router.get("/credentials/list")
async def credentials_list(request: Request):
    db = await _get_db(request)
    uid = await _get_user_id(request)
    creds = await list_credentials(db, uid)
    return {"credentials": creds, "count": len(creds)}


@router.post("/credentials/save")
async def credentials_save(body: SaveCredBody, request: Request):
    db = await _get_db(request)
    uid = await _get_user_id(request)
    # Validate first
    validation = await validate_by_key_name(body.key_name, body.value)
    if not validation.get("valid"):
        return {"saved": False, "validation": validation}
    saved = await store_credential(db, uid, body.key_name, body.value, body.metadata)
    if saved:
        await mark_validated(db, uid, body.key_name, True)
    return {
        "saved": saved,
        "validation": validation,
        "masked": mask_for_display(body.value),
    }


@router.post("/credentials/validate/{key_name}")
async def credentials_validate(key_name: str, body: SaveCredBody, request: Request):
    """Validate a credential WITHOUT saving (preview)."""
    validation = await validate_by_key_name(key_name, body.value)
    return validation


@router.delete("/credentials/{key_name}")
async def credentials_delete(key_name: str, request: Request):
    db = await _get_db(request)
    uid = await _get_user_id(request)
    ok = await delete_credential(db, uid, key_name)
    return {"deleted": ok}


# ─────────────────── Integration catalog ───────────────────
@router.get("/integrations/list")
async def integrations_list_route():
    items = list_integrations()
    return {"integrations": items, "count": len(items)}


@router.get("/integrations/{integration_id}")
async def integration_detail(integration_id: str, language: str = "ar"):
    integ = get_integration(integration_id)
    if not integ:
        raise HTTPException(404, "integration not found")
    return {
        "integration": integ,
        "instructions_ar": render_setup_instructions_ar(integration_id),
        "instructions_en": render_setup_instructions_en(integration_id),
        "wizard_cards": build_wizard_flow(integration_id, language),
    }


# ─────────────────── Project state + needs ───────────────────
@router.post("/project/{project_id}/detect-needs")
async def detect_needs(project_id: str, body: DetectNeedsBody, request: Request):
    db = await _get_db(request)
    uid = await _get_user_id(request)
    needs = detect_required_integrations(body.message, body.language)
    # Cross-check with vault: which are already satisfied?
    pending = []
    satisfied = []
    for iid in needs:
        integ = get_integration(iid)
        if not integ:
            continue
        all_creds = (integ.get("required_credentials") or [])
        if not all_creds:
            satisfied.append(iid); continue
        missing = []
        for c in all_creds:
            if not await has_credential(db, uid, c["key"]):
                missing.append(c["key"])
        if missing:
            pending.append({"integration_id": iid, "missing_keys": missing})
            await add_required_integration(db, project_id, iid)
        else:
            satisfied.append(iid)
            await mark_integration_satisfied(db, project_id, iid)
    return {
        "detected": needs,
        "pending_setup": pending,
        "already_satisfied": satisfied,
        "cost_summary": card_cost_summary([p["integration_id"] for p in pending], body.language),
    }


@router.get("/project/{project_id}/state")
async def project_state(project_id: str, request: Request):
    db = await _get_db(request)
    state = await load_state(db, project_id)
    return state


@router.post("/project/{project_id}/state/transition")
async def project_state_transition(project_id: str, body: StateTransitionBody, request: Request):
    db = await _get_db(request)
    try:
        new_state = ConciergeState(body.new_state)
    except ValueError:
        raise HTTPException(400, f"invalid state: {body.new_state}")
    ok = await transition(db, project_id, new_state, body.payload)
    if not ok:
        raise HTTPException(409, "transition not allowed from current state")
    return {"transitioned": True, "new_state": new_state.value}


@router.post("/project/{project_id}/resume-after-setup")
async def project_resume_after_setup(project_id: str, request: Request):
    """Called by frontend after user completes the setup wizard."""
    from ..concierge_hooks import resume_after_setup  # noqa: E402
    db = await _get_db(request)
    uid = await _get_user_id(request)
    return await resume_after_setup(db, uid, project_id)


@router.get("/project/{project_id}/wizard")
async def project_wizard(project_id: str, request: Request, language: str = "ar"):
    """Return next pending wizard card(s) for a project."""
    db = await _get_db(request)
    pending_iids = await get_required_integrations(db, project_id)
    if not pending_iids:
        return {"all_done": True, "next_card": None, "pending_integrations": []}
    first = pending_iids[0]
    flow = build_wizard_flow(first, language)
    return {
        "all_done": False,
        "current_integration": first,
        "pending_integrations": pending_iids,
        "wizard_flow": flow,
    }
