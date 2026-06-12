"""Local Browser Relay & Desktop Agent Relay.

Two WebSocket bridges:
  1. Chrome Extension  — controls only browser tabs (`/api/local-browser/ws`)
  2. Desktop Agent     — native OS control: mouse, keyboard, files, apps
                         (`/api/desktop-agent/ws`)

----- Original docs (Chrome extension) -----

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
desktop_router = APIRouter(prefix="/api/desktop-agent", tags=["desktop-agent"])

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


# ═════════════════════════════════════════════════════════════════════════════
# DESKTOP AGENT RELAY (full native OS control on the user's laptop)
# ═════════════════════════════════════════════════════════════════════════════
import io
import os
import zipfile
from pathlib import Path
from fastapi.responses import StreamingResponse

# Separate pools so a Chrome ext and a desktop agent on the same project
# can co-exist without collisions.
_DESKTOP_PAIRINGS: Dict[str, Dict[str, Any]] = {}
_DESKTOP_ACTIVE_WS: Dict[str, WebSocket] = {}
_DESKTOP_PENDING: Dict[str, Dict[str, asyncio.Future]] = {}

DESKTOP_COMMAND_TIMEOUT_SECONDS = 60  # screenshots / downloads can take longer


def _cleanup_expired_desktop_pairings() -> None:
    now = time.time()
    expired = [c for c, info in _DESKTOP_PAIRINGS.items() if info.get("expires_at", 0) < now]
    for c in expired:
        _DESKTOP_PAIRINGS.pop(c, None)


def create_desktop_pairing(project_id: str) -> Dict[str, Any]:
    """Generate a 6-char pairing code for the Desktop Agent."""
    _cleanup_expired_desktop_pairings()
    code = _generate_pairing_code()
    _DESKTOP_PAIRINGS[code] = {
        "project_id": project_id,
        "expires_at": time.time() + PAIRING_TTL_SECONDS,
        "ws_connected": False,
    }
    return {
        "code": code,
        "expires_in_seconds": PAIRING_TTL_SECONDS,
    }


def is_desktop_agent_connected(project_id: str) -> bool:
    return project_id in _DESKTOP_ACTIVE_WS


async def send_command_to_desktop(project_id: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Send a command to the connected Desktop Agent and wait for its response."""
    ws = _DESKTOP_ACTIVE_WS.get(project_id)
    if not ws:
        return {
            "ok": False,
            "error": "no_desktop_agent_connected",
            "hint": "نزّل Zenrex Desktop Agent من رابط التنزيل، شغّله بالرمز اللي طلعه `desktop_pair`، وحاول مرّة ثانية.",
        }
    req_id = secrets.token_hex(6)
    fut: asyncio.Future = asyncio.get_event_loop().create_future()
    _DESKTOP_PENDING.setdefault(project_id, {})[req_id] = fut
    try:
        await ws.send_json({
            "type": "command",
            "request_id": req_id,
            "action": action,
            "params": params or {},
        })
    except Exception as e:
        _DESKTOP_PENDING[project_id].pop(req_id, None)
        return {"ok": False, "error": f"send failed: {e}"}
    try:
        result = await asyncio.wait_for(fut, timeout=DESKTOP_COMMAND_TIMEOUT_SECONDS)
        return result if isinstance(result, dict) else {"ok": True, "raw": result}
    except asyncio.TimeoutError:
        _DESKTOP_PENDING[project_id].pop(req_id, None)
        return {
            "ok": False,
            "error": f"desktop agent did not respond within {DESKTOP_COMMAND_TIMEOUT_SECONDS}s",
        }


# ─── HTTP endpoints ───────────────────────────────────────────────────────────
@desktop_router.post("/pair")
async def desktop_pair(request: Request):
    """Generate a desktop-agent pairing code."""
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    project_id = body.get("project_id")
    if not project_id:
        raise HTTPException(400, "project_id required")
    info = create_desktop_pairing(project_id)
    return {
        "ok": True,
        "code": info["code"],
        "expires_in_seconds": info["expires_in_seconds"],
        "download_url": "/api/desktop-agent/download",
        "instructions": (
            "1) نزّل Zenrex Desktop Agent (ZIP).  "
            "2) فك الضغط وشغّل installer المناسب لنظامك.  "
            f"3) السكربت بيسألك عن الرمز — الصق: {info['code']}"
        ),
    }


@desktop_router.get("/status")
async def desktop_status(project_id: str = Query(...)):
    return {
        "ok": True,
        "project_id": project_id,
        "connected": is_desktop_agent_connected(project_id),
    }


@desktop_router.post("/act")
async def desktop_act_http(request: Request):
    """Direct HTTP bridge to a paired Desktop Agent.

    Body: {project_id, action, params?}.  Used by the chat when running tools
    from outside the in-process AI loop, and by automated tests.
    """
    body = await request.json()
    project_id = body.get("project_id")
    action = body.get("action")
    params = body.get("params") or {}
    if not project_id or not action:
        raise HTTPException(400, "project_id + action required")
    result = await send_command_to_desktop(project_id, action, params)
    return result


def _bootstrap_sh(public_base: str) -> str:
    """One-liner Bash installer for macOS/Linux.

    Usage:  curl -fsSL <base>/api/desktop-agent/bootstrap.sh | bash -s -- <code>
    """
    return f"""#!/usr/bin/env bash
# Zenrex Desktop Agent — one-line bootstrap (macOS / Linux)
set -e

CODE="${{1:-}}"
if [ -z "$CODE" ]; then
    echo ""
    read -p "🔑 Paste the 6-character pairing code from Zenrex: " CODE
fi

DEST="$HOME/.zenrex-desktop-agent"
ZIP_URL="{public_base}/api/desktop-agent/download"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  🤖 Zenrex Desktop Agent — One-line installer"
echo "═══════════════════════════════════════════════════════════"
echo "→ Install dir: $DEST"

# 1. Check Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python 3 not found."
    echo "   Mac:    brew install python3"
    echo "   Linux:  sudo apt install python3 python3-pip python3-tk scrot"
    exit 1
fi
echo "✓ Python $(python3 -c 'import sys; print(\"%d.%d\" % sys.version_info[:2])')"

# 2. Download + extract
mkdir -p "$DEST"
TMP=$(mktemp -d)
echo "→ Downloading agent ZIP..."
curl -fsSL "$ZIP_URL" -o "$TMP/agent.zip"

echo "→ Extracting..."
unzip -qo "$TMP/agent.zip" -d "$TMP"
# The ZIP contains a desktop_agent/ folder; flatten it into DEST.
cp -R "$TMP/desktop_agent/." "$DEST/"
rm -rf "$TMP"
chmod +x "$DEST/install.sh" "$DEST/run.sh" 2>/dev/null || true

# 3. Set up venv + install deps
cd "$DEST"
if [ ! -d ".venv" ]; then
    echo "→ Creating virtual environment..."
    python3 -m venv .venv
fi
echo "→ Installing dependencies (PyAutoGUI, mss, Pillow, websockets, pyperclip)..."
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt

# 4. Run!
echo ""
echo "✅ Setup complete. Connecting to Zenrex with code: $CODE"
echo "   (Press Ctrl+C anytime to disconnect.)"
echo ""
exec ./.venv/bin/python zenrex_agent.py --code "$CODE"
"""


def _bootstrap_ps1(public_base: str) -> str:
    """One-liner PowerShell installer for Windows.

    Usage:  iwr <base>/api/desktop-agent/bootstrap.ps1 -useb | iex
    """
    return f"""# Zenrex Desktop Agent  one-line bootstrap (Windows PowerShell)
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════"
Write-Host "   Zenrex Desktop Agent  One-line installer (Windows)"
Write-Host "═══════════════════════════════════════════════════════════"

$Code = if ($args.Count -gt 0) {{ $args[0] }} else {{ Read-Host "Paste the 6-character pairing code from Zenrex" }}
if (-not $Code) {{ Write-Error "Pairing code required."; exit 1 }}

$Dest = Join-Path $env:USERPROFILE ".zenrex-desktop-agent"
$ZipUrl = "{public_base}/api/desktop-agent/download"

# 1. Python check
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {{
    Write-Host "Python not found. Install from https://www.python.org/downloads/ (check 'Add to PATH')."
    exit 1
}}
Write-Host "OK Python found"

# 2. Download + extract
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
$Tmp = New-Item -ItemType Directory -Force -Path (Join-Path $env:TEMP "zenrex-da-$(Get-Random)")
$ZipPath = Join-Path $Tmp.FullName "agent.zip"
Write-Host "-> Downloading agent ZIP..."
Invoke-WebRequest -UseBasicParsing -Uri $ZipUrl -OutFile $ZipPath

Write-Host "-> Extracting..."
Expand-Archive -Path $ZipPath -DestinationPath $Tmp.FullName -Force
Copy-Item -Recurse -Force (Join-Path $Tmp.FullName "desktop_agent\\*") $Dest
Remove-Item -Recurse -Force $Tmp

# 3. venv + deps
Set-Location $Dest
if (-not (Test-Path ".venv\\Scripts\\python.exe")) {{
    Write-Host "-> Creating virtual environment..."
    python -m venv .venv
}}
Write-Host "-> Installing dependencies..."
& ".\\.venv\\Scripts\\python.exe" -m pip install --quiet --upgrade pip
& ".\\.venv\\Scripts\\python.exe" -m pip install --quiet -r requirements.txt

# 4. Run
Write-Host ""
Write-Host "OK Setup complete. Connecting to Zenrex with code: $Code"
Write-Host "   (Press Ctrl+C to disconnect.)"
Write-Host ""
& ".\\.venv\\Scripts\\python.exe" zenrex_agent.py --code $Code
"""


def _resolve_public_base(request: Request) -> str:
    public_base = os.environ.get("BACKEND_URL", "").rstrip("/")
    if not public_base:
        scheme = "https" if request.url.scheme in ("https", "wss") else "http"
        public_base = f"{scheme}://{request.url.netloc}"
    return public_base


@desktop_router.get("/bootstrap.sh")
async def desktop_bootstrap_sh(request: Request):
    """One-line installer (Bash) — `curl ... | bash -s -- CODE`."""
    from fastapi.responses import PlainTextResponse
    script = _bootstrap_sh(_resolve_public_base(request))
    return PlainTextResponse(script, media_type="text/x-shellscript",
                              headers={"Cache-Control": "no-store"})


@desktop_router.get("/bootstrap.ps1")
async def desktop_bootstrap_ps1(request: Request):
    """One-line installer (PowerShell) — `iwr ... | iex`."""
    from fastapi.responses import PlainTextResponse
    script = _bootstrap_ps1(_resolve_public_base(request))
    return PlainTextResponse(script, media_type="text/plain",
                              headers={"Cache-Control": "no-store"})


@desktop_router.get("/download")
async def desktop_download(request: Request):
    """Return a ready-to-run ZIP of the Desktop Agent.

    Bakes the current platform's WebSocket URL into a `config.json` inside the
    archive so the user doesn't have to configure anything.
    """
    public_base = os.environ.get("BACKEND_URL", "").rstrip("/")
    if not public_base:
        # Fall back to request host
        scheme = "https" if request.url.scheme in ("https", "wss") else "http"
        public_base = f"{scheme}://{request.url.netloc}"
    ws_url = public_base.replace("https://", "wss://").replace("http://", "ws://") + "/api/desktop-agent/ws"

    desktop_dir = Path(__file__).resolve().parents[3] / "desktop_agent"
    if not desktop_dir.exists():
        raise HTTPException(500, "desktop_agent source not found on server")

    # Build the ZIP in-memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for fp in desktop_dir.rglob("*"):
            if fp.is_file() and "__pycache__" not in fp.parts and not fp.name.startswith("."):
                rel = fp.relative_to(desktop_dir.parent)  # zenrex_desktop_agent/...
                z.write(fp, arcname=str(rel))
        # Inject config.json with the right server URL
        z.writestr(
            "desktop_agent/config.json",
            json.dumps({"server_ws": ws_url, "platform": public_base}, indent=2, ensure_ascii=False),
        )

    buf.seek(0)
    headers = {
        "Content-Disposition": 'attachment; filename="ZenrexDesktopAgent.zip"',
        "Cache-Control": "no-store",
    }
    return StreamingResponse(buf, media_type="application/zip", headers=headers)


# ─── WebSocket endpoint (desktop agent connects here) ────────────────────────
@desktop_router.websocket("/ws")
async def desktop_agent_ws(ws: WebSocket, code: str = Query(...)):
    await ws.accept()
    _cleanup_expired_desktop_pairings()
    pairing = _DESKTOP_PAIRINGS.get(code)
    if not pairing:
        await ws.send_json({"type": "error", "message": "invalid_or_expired_pairing_code"})
        await ws.close(code=4401)
        return
    project_id = pairing["project_id"]
    prev = _DESKTOP_ACTIVE_WS.get(project_id)
    if prev:
        try:
            await prev.close(code=4000)
        except Exception:
            pass
    _DESKTOP_ACTIVE_WS[project_id] = ws
    pairing["ws_connected"] = True
    _DESKTOP_PENDING.setdefault(project_id, {})
    await ws.send_json({
        "type": "paired",
        "project_id": project_id,
        "message": "✅ Connected to Zenrex (Desktop Agent)",
    })
    logger.info(f"[desktop-agent] connected for project {project_id}")
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
                req_id = msg.get("request_id")
                fut = _DESKTOP_PENDING.get(project_id, {}).pop(req_id, None)
                if fut and not fut.done():
                    fut.set_result(msg.get("payload") or {})
            elif mtype == "event":
                logger.debug(f"[desktop-agent] event from {project_id}: {msg.get('event')}")
            elif mtype == "hello":
                # Agent identifies itself with OS/version info
                pairing["agent_info"] = msg.get("info") or {}
    except WebSocketDisconnect:
        logger.info(f"[desktop-agent] disconnected for project {project_id}")
    except Exception as e:
        logger.warning(f"[desktop-agent] ws error: {e}")
    finally:
        if _DESKTOP_ACTIVE_WS.get(project_id) is ws:
            _DESKTOP_ACTIVE_WS.pop(project_id, None)
        for req_id, fut in list(_DESKTOP_PENDING.get(project_id, {}).items()):
            if not fut.done():
                fut.set_result({"ok": False, "error": "desktop_agent_disconnected"})
