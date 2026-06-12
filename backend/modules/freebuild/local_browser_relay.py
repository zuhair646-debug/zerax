"""Local Browser Relay — WebSocket bridge between the AI and the user's Chrome.

Architecture:
  • User installs Zenrex Chrome Extension once.
  • Extension opens a WebSocket to `wss://zenrex.ai/api/local-browser/ws?token=PAIRING_CODE`.
  • AI calls `local_browser_*` tools → backend looks up the active connection
    for that project → sends the command over the WS → extension executes it
    on the user's actual browser tab → returns result (screenshot, DOM info).

  • Pairing flow:
      1. AI calls `local_browser_pair()` → returns a 6-digit code + QR URL.
      2. User opens the extension popup, pastes the code → extension stores it.
      3. Extension connects to WS with the code → backend validates + binds
         the WS to the project_id.
      4. Subsequent AI commands flow through.
"""
from __future__ import annotations

import asyncio
import json
import logging
import secrets
import string
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("zenrex.local_browser")

router = APIRouter(prefix="/api/local-browser", tags=["local-browser"])

# In-memory: pairing_code → {project_id, expires_at, ws_connected}
_PAIRINGS: Dict[str, Dict[str, Any]] = {}
# In-memory: project_id → active WebSocket
_ACTIVE_WS: Dict[str, WebSocket] = {}
# In-memory: project_id → asyncio.Future for pending command responses keyed by request_id
_PENDING_RESPONSES: Dict[str, Dict[str, asyncio.Future]] = {}

PAIRING_TTL_SECONDS = 10 * 60  # 10 minutes
COMMAND_TIMEOUT_SECONDS = 30


def _generate_pairing_code() -> str:
    """6-character uppercase alphanumeric pairing code."""
    alphabet = string.ascii_uppercase + string.digits
    # Avoid confusing chars (0/O, I/1)
    alphabet = alphabet.replace("0", "").replace("O", "").replace("I", "").replace("1", "")
    return "".join(secrets.choice(alphabet) for _ in range(6))


def _cleanup_expired_pairings():
    now = time.time()
    expired = [code for code, info in _PAIRINGS.items() if info.get("expires_at", 0) < now]
    for c in expired:
        _PAIRINGS.pop(c, None)


# ─── HTTP endpoints ───────────────────────────────────────────────────────────
@router.post("/pair")
async def create_pairing(request: Request):
    """AI tool calls this to generate a pairing code for the user."""
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    project_id = body.get("project_id")
    if not project_id:
        raise HTTPException(400, "project_id required")
    _cleanup_expired_pairings()
    code = _generate_pairing_code()
    _PAIRINGS[code] = {
        "project_id": project_id,
        "expires_at": time.time() + PAIRING_TTL_SECONDS,
        "ws_connected": False,
    }
    return {
        "ok": True,
        "code": code,
        "expires_in_seconds": PAIRING_TTL_SECONDS,
        "instructions": (
            "افتح إضافة Zenrex في متصفحك → ضع الرمز التالي → اضغط 'ربط'. "
            f"الرمز: {code}"
        ),
    }


@router.get("/status")
async def status(project_id: str = Query(...)):
    """Check whether a browser extension is connected for this project."""
    connected = project_id in _ACTIVE_WS
    return {"ok": True, "project_id": project_id, "connected": connected}


# ─── WebSocket endpoint (extension connects here) ────────────────────────────
@router.websocket("/ws")
async def extension_ws(ws: WebSocket, code: str = Query(...)):
    await ws.accept()
    _cleanup_expired_pairings()
    pairing = _PAIRINGS.get(code)
    if not pairing:
        await ws.send_json({"type": "error", "message": "invalid_or_expired_pairing_code"})
        await ws.close(code=4401)
        return
    project_id = pairing["project_id"]
    # Bind this WS to the project; replace any prior connection
    prev = _ACTIVE_WS.get(project_id)
    if prev:
        try:
            await prev.close(code=4000)
        except Exception:
            pass
    _ACTIVE_WS[project_id] = ws
    pairing["ws_connected"] = True
    _PENDING_RESPONSES.setdefault(project_id, {})
    await ws.send_json({"type": "paired", "project_id": project_id,
                        "message": "✅ Connected to Zenrex"})
    logger.info(f"[local-browser] extension connected for project {project_id}")

    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except Exception:
                continue
            mtype = msg.get("type")
            if mtype == "ping":
                await ws.send_json({"type": "pong", "ts": time.time()})
            elif mtype == "response":
                # Command result coming back from the extension
                req_id = msg.get("request_id")
                fut = _PENDING_RESPONSES.get(project_id, {}).pop(req_id, None)
                if fut and not fut.done():
                    fut.set_result(msg.get("payload") or {})
            elif mtype == "event":
                # Async events (tab opened, click happened, etc.) — log for now
                logger.debug(f"[local-browser] event from {project_id}: {msg.get('event')}")
    except WebSocketDisconnect:
        logger.info(f"[local-browser] extension disconnected for project {project_id}")
    except Exception as e:
        logger.warning(f"[local-browser] ws error: {e}")
    finally:
        if _ACTIVE_WS.get(project_id) is ws:
            _ACTIVE_WS.pop(project_id, None)
        # Resolve any dangling futures with errors
        for req_id, fut in list(_PENDING_RESPONSES.get(project_id, {}).items()):
            if not fut.done():
                fut.set_result({"ok": False, "error": "extension_disconnected"})


# ─── Helpers used by the AI tools ─────────────────────────────────────────────
async def send_command_to_extension(project_id: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Send a command to the connected extension and wait for its response."""
    ws = _ACTIVE_WS.get(project_id)
    if not ws:
        return {"ok": False,
                "error": "no_extension_connected",
                "hint": "ادعُ `local_browser_pair` ليحصل العميل على رمز التوصيل ويربط الإضافة أولاً."}
    req_id = secrets.token_hex(6)
    fut: asyncio.Future = asyncio.get_event_loop().create_future()
    _PENDING_RESPONSES.setdefault(project_id, {})[req_id] = fut
    try:
        await ws.send_json({
            "type": "command",
            "request_id": req_id,
            "action": action,
            "params": params,
        })
    except Exception as e:
        _PENDING_RESPONSES[project_id].pop(req_id, None)
        return {"ok": False, "error": f"send failed: {e}"}
    try:
        result = await asyncio.wait_for(fut, timeout=COMMAND_TIMEOUT_SECONDS)
        return result if isinstance(result, dict) else {"ok": True, "raw": result}
    except asyncio.TimeoutError:
        _PENDING_RESPONSES[project_id].pop(req_id, None)
        return {"ok": False, "error": f"extension did not respond within {COMMAND_TIMEOUT_SECONDS}s"}


def is_extension_connected(project_id: str) -> bool:
    return project_id in _ACTIVE_WS
