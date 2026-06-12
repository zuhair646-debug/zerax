"""
Zenrex Desktop Agent — connects your computer to Zenrex AI for full remote control.

Installs once, runs in the background. The Zenrex AI can:
  • Capture your screen (full desktop, all apps)
  • Move your mouse and click anywhere
  • Type text
  • Press keyboard shortcuts
  • Download files to your Downloads folder
  • Open native applications
  • Run terminal commands (with your confirmation)

Usage:
    pip install -r requirements.txt
    python zenrex_agent.py --code ABC123

(Get the pairing code by asking the AI: "اربط جهازي")
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import logging
import os
import platform
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# Required: pip install pyautogui mss pillow websockets
try:
    import pyautogui
    import mss
    from PIL import Image
    import websockets
except ImportError:
    print("Missing dependencies. Run: pip install pyautogui mss pillow websockets")
    sys.exit(1)

# ────────────────────────────────────────────────────────────────────────────
ZENREX_WS_BASE = os.environ.get("ZENREX_WS", "wss://zenrex.ai/api/desktop-agent/ws")
DOWNLOADS_DIR = Path.home() / "Downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Safety: disable PyAutoGUI's failsafe? No — keep it (move mouse to corner to abort)
pyautogui.FAILSAFE = True

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
log = logging.getLogger("zenrex-agent")


# ─── Action handlers ────────────────────────────────────────────────────────
def screenshot() -> dict:
    """Capture the full primary screen as JPEG base64."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # primary screen
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"ok": True, "screenshot_b64": b64,
            "size": {"width": monitor["width"], "height": monitor["height"]}}


def move_mouse(params: dict) -> dict:
    pyautogui.moveTo(int(params.get("x", 0)), int(params.get("y", 0)),
                      duration=float(params.get("duration", 0.2)))
    return {"ok": True}


def click(params: dict) -> dict:
    x = params.get("x")
    y = params.get("y")
    button = params.get("button", "left")
    clicks = int(params.get("clicks", 1))
    if x is not None and y is not None:
        pyautogui.click(int(x), int(y), clicks=clicks, button=button)
    else:
        pyautogui.click(clicks=clicks, button=button)
    return {"ok": True}


def type_text(params: dict) -> dict:
    text = params.get("text", "")
    interval = float(params.get("interval", 0.02))
    pyautogui.typewrite(text, interval=interval)
    return {"ok": True, "chars": len(text)}


def press_key(params: dict) -> dict:
    """Press a single key or a combination, e.g. 'cmd+space', 'enter', 'cmd+c'."""
    key = params.get("key", "")
    parts = [p.strip() for p in key.split("+") if p.strip()]
    if len(parts) == 1:
        pyautogui.press(parts[0])
    else:
        pyautogui.hotkey(*parts)
    return {"ok": True, "key": key}


def scroll(params: dict) -> dict:
    amount = int(params.get("amount", -3))
    pyautogui.scroll(amount)
    return {"ok": True}


def download_file(params: dict) -> dict:
    """Download a URL directly to the user's Downloads folder."""
    url = params.get("url", "")
    name = params.get("filename") or url.rsplit("/", 1)[-1].split("?")[0] or "download"
    name = "".join(c for c in name if c.isalnum() or c in "._-")[:120]
    dest = DOWNLOADS_DIR / name
    try:
        urllib.request.urlretrieve(url, dest)
        return {"ok": True, "path": str(dest), "bytes": dest.stat().st_size}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def open_app(params: dict) -> dict:
    """Open a native application by name."""
    name = params.get("name", "")
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.Popen(["open", "-a", name])
        elif system == "Windows":
            subprocess.Popen(["start", "", name], shell=True)
        else:  # Linux
            subprocess.Popen([name])
        return {"ok": True, "app": name}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def get_cursor_position(_params: dict) -> dict:
    x, y = pyautogui.position()
    return {"ok": True, "x": x, "y": y}


# Safety-gated: only run if user has explicitly confirmed
_SHELL_ENABLED = False


def run_local_shell(params: dict) -> dict:
    """Run a shell command on the user's machine. Disabled by default."""
    if not _SHELL_ENABLED:
        return {"ok": False, "error": "local shell disabled. Re-run agent with --allow-shell"}
    cmd = params.get("command", "")
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                            timeout=int(params.get("timeout", 30)))
        return {"ok": r.returncode == 0, "stdout": r.stdout[:50000],
                "stderr": r.stderr[:10000], "exit_code": r.returncode}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


ACTIONS = {
    "screenshot": lambda p: screenshot(),
    "move_mouse": move_mouse,
    "click": click,
    "type": type_text,
    "press_key": press_key,
    "scroll": scroll,
    "download_file": download_file,
    "open_app": open_app,
    "cursor_position": get_cursor_position,
    "run_shell": run_local_shell,
}


# ─── WebSocket loop ──────────────────────────────────────────────────────────
async def run_agent(code: str):
    url = f"{ZENREX_WS_BASE}?code={code}"
    log.info(f"Connecting to {url}…")
    while True:
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                log.info("✅ Connected. Listening for commands…")
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue
                    if msg.get("type") == "command":
                        action = msg.get("action")
                        params = msg.get("params") or {}
                        fn = ACTIONS.get(action)
                        if not fn:
                            payload = {"ok": False, "error": f"unknown action: {action}"}
                        else:
                            try:
                                payload = fn(params)
                            except Exception as e:
                                payload = {"ok": False, "error": f"{type(e).__name__}: {e}"}
                        await ws.send(json.dumps({
                            "type": "response",
                            "request_id": msg.get("request_id"),
                            "payload": payload,
                        }))
                    elif msg.get("type") == "ping":
                        await ws.send(json.dumps({"type": "pong"}))
                    elif msg.get("type") == "paired":
                        log.info(f"🔗 Paired with project {msg.get('project_id')}")
                    elif msg.get("type") == "error":
                        log.error(f"Server error: {msg.get('message')}")
        except (websockets.ConnectionClosed, OSError) as e:
            log.warning(f"Connection lost ({e}); reconnecting in 5s…")
            await asyncio.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="Zenrex Desktop Agent")
    parser.add_argument("--code", required=True, help="6-character pairing code from Zenrex chat.")
    parser.add_argument("--allow-shell", action="store_true",
                        help="Allow the AI to run shell commands on this machine (DANGER).")
    args = parser.parse_args()

    global _SHELL_ENABLED
    _SHELL_ENABLED = args.allow_shell

    print("=" * 60)
    print(f"🤖 Zenrex Desktop Agent v0.1 — {platform.system()} {platform.machine()}")
    print(f"   Screen: {pyautogui.size()}")
    print(f"   Downloads → {DOWNLOADS_DIR}")
    print(f"   Shell exec: {'ENABLED ⚠️' if _SHELL_ENABLED else 'disabled (safe)'}")
    print(f"   FAILSAFE: Move mouse to top-left corner to abort.")
    print("=" * 60)

    try:
        asyncio.run(run_agent(args.code))
    except KeyboardInterrupt:
        log.info("Bye 👋")


if __name__ == "__main__":
    main()
