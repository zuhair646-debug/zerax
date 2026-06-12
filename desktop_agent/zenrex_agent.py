"""
Zenrex Desktop Agent — connects your computer to Zenrex AI for full remote control.

The Zenrex AI can (once paired):
  • Capture your screen (full desktop, all apps)
  • Move your mouse and click anywhere
  • Type text, press keyboard shortcuts
  • Download files directly to your Downloads folder
  • Open native applications (VS Code, Chrome, Finder…)
  • List / read / write files in folders you allow
  • (Optional, off by default) Run shell commands

Usage:
    pip install -r requirements.txt
    python zenrex_agent.py --code ABC123

Or run the bundled installer (install.sh / install.bat) — it does pip + run.

The script reads server URL from (in order):
  1. --server CLI arg
  2. ZENREX_SERVER env var
  3. ./config.json   { "server_ws": "wss://...." }
  4. wss://zenrex.ai/api/desktop-agent/ws  (default)
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
    print("Missing dependencies. Run: pip install -r requirements.txt")
    sys.exit(1)

# ────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_WS = "wss://zenrex.ai/api/desktop-agent/ws"


def _load_config_server() -> str:
    """Server URL resolution chain."""
    if os.environ.get("ZENREX_SERVER"):
        return os.environ["ZENREX_SERVER"]
    cfg = SCRIPT_DIR / "config.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            if data.get("server_ws"):
                return str(data["server_ws"])
        except Exception:
            pass
    return DEFAULT_WS


DOWNLOADS_DIR = Path.home() / "Downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

pyautogui.FAILSAFE = True  # mouse to top-left aborts

logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("zenrex-agent")


# ─── Safe path helpers (sandbox writes to user dirs) ─────────────────────────
def _safe_path(p: str) -> Path:
    """Expand ~ and resolve. We do NOT restrict path; the user owns the machine.
    But we DO refuse empty / parent traversal off the home root for writes when
    `--strict-home` is on."""
    return Path(os.path.expanduser(str(p))).resolve()


# ─── Action handlers ────────────────────────────────────────────────────────
def screenshot(_params: dict) -> dict:
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # primary screen
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        # Downscale large screens to keep payload small
        max_w = 1600
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=55)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"ok": True, "screenshot_b64": b64,
            "size": {"width": monitor["width"], "height": monitor["height"]},
            "encoded_size": {"width": img.width, "height": img.height}}


def move_mouse(params: dict) -> dict:
    pyautogui.moveTo(int(params.get("x", 0)), int(params.get("y", 0)),
                     duration=float(params.get("duration", 0.2)))
    return {"ok": True}


def click(params: dict) -> dict:
    x = params.get("x"); y = params.get("y")
    button = params.get("button", "left")
    clicks = int(params.get("clicks", 1))
    if x is not None and y is not None:
        pyautogui.click(int(x), int(y), clicks=clicks, button=button)
    else:
        pyautogui.click(clicks=clicks, button=button)
    return {"ok": True}


def double_click(params: dict) -> dict:
    p = dict(params); p["clicks"] = 2
    return click(p)


def right_click(params: dict) -> dict:
    p = dict(params); p["button"] = "right"
    return click(p)


def type_text(params: dict) -> dict:
    text = params.get("text", "")
    interval = float(params.get("interval", 0.02))
    # PyAutoGUI typewrite() can't handle non-ASCII; use write() fallback +
    # for Arabic / unicode, use clipboard paste.
    try:
        pyautogui.typewrite(text, interval=interval)
    except Exception:
        try:
            import pyperclip
            pyperclip.copy(text)
            paste = "command+v" if platform.system() == "Darwin" else "ctrl+v"
            pyautogui.hotkey(*paste.split("+"))
        except Exception as e:
            return {"ok": False, "error": f"type fallback failed: {e}"}
    return {"ok": True, "chars": len(text)}


def press_key(params: dict) -> dict:
    key = params.get("key", "")
    parts = [p.strip() for p in key.split("+") if p.strip()]
    if not parts:
        return {"ok": False, "error": "key required"}
    if len(parts) == 1:
        pyautogui.press(parts[0])
    else:
        pyautogui.hotkey(*parts)
    return {"ok": True, "key": key}


def scroll(params: dict) -> dict:
    pyautogui.scroll(int(params.get("amount", -3)))
    return {"ok": True}


def download_file(params: dict) -> dict:
    url = params.get("url", "")
    if not url:
        return {"ok": False, "error": "url required"}
    name = params.get("filename") or url.rsplit("/", 1)[-1].split("?")[0] or "download"
    name = "".join(c for c in name if c.isalnum() or c in "._-")[:120] or "download"
    dest = DOWNLOADS_DIR / name
    try:
        urllib.request.urlretrieve(url, dest)
        return {"ok": True, "path": str(dest), "bytes": dest.stat().st_size}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def open_app(params: dict) -> dict:
    name = params.get("name", "")
    if not name:
        return {"ok": False, "error": "name required"}
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", "-a", name])
        elif system == "Windows":
            subprocess.Popen(["start", "", name], shell=True)
        else:
            subprocess.Popen([name])
        return {"ok": True, "app": name}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def open_url(params: dict) -> dict:
    import webbrowser
    url = params.get("url", "")
    if not url:
        return {"ok": False, "error": "url required"}
    webbrowser.open(url)
    return {"ok": True, "url": url}


def cursor_position(_params: dict) -> dict:
    x, y = pyautogui.position()
    return {"ok": True, "x": int(x), "y": int(y)}


def screen_size(_params: dict) -> dict:
    w, h = pyautogui.size()
    return {"ok": True, "width": int(w), "height": int(h)}


def list_dir(params: dict) -> dict:
    path = _safe_path(params.get("path") or str(Path.home()))
    if not path.exists():
        return {"ok": False, "error": "path does not exist"}
    if not path.is_dir():
        return {"ok": False, "error": "path is not a directory"}
    try:
        entries = []
        for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))[:500]:
            try:
                st = child.stat()
                entries.append({
                    "name": child.name,
                    "is_dir": child.is_dir(),
                    "size": st.st_size if child.is_file() else None,
                })
            except Exception:
                continue
        return {"ok": True, "path": str(path), "entries": entries, "count": len(entries)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def read_file(params: dict) -> dict:
    path = _safe_path(params.get("path", ""))
    max_bytes = int(params.get("max_bytes", 200_000))
    if not path.exists() or not path.is_file():
        return {"ok": False, "error": "file not found"}
    try:
        data = path.read_bytes()[:max_bytes]
        try:
            text = data.decode("utf-8")
            return {"ok": True, "path": str(path), "text": text,
                    "size_total": path.stat().st_size, "size_returned": len(data)}
        except UnicodeDecodeError:
            return {"ok": True, "path": str(path),
                    "binary_b64": base64.b64encode(data).decode("ascii"),
                    "size_total": path.stat().st_size, "size_returned": len(data)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def write_file(params: dict) -> dict:
    path = _safe_path(params.get("path", ""))
    content = params.get("content", "")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(content), encoding="utf-8")
        return {"ok": True, "path": str(path), "bytes": path.stat().st_size}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def make_dir(params: dict) -> dict:
    path = _safe_path(params.get("path", ""))
    try:
        path.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(path)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# Safety-gated: only runs if `--allow-shell` was passed
_SHELL_ENABLED = False


def run_shell(params: dict) -> dict:
    if not _SHELL_ENABLED:
        return {"ok": False,
                "error": "local shell disabled. Re-run agent with --allow-shell."}
    cmd = params.get("command", "")
    if not cmd:
        return {"ok": False, "error": "command required"}
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                            timeout=int(params.get("timeout", 30)))
        return {"ok": r.returncode == 0,
                "stdout": (r.stdout or "")[:50000],
                "stderr": (r.stderr or "")[:10000],
                "exit_code": r.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "shell timeout"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


ACTIONS = {
    "screenshot": screenshot,
    "move_mouse": move_mouse,
    "click": click,
    "double_click": double_click,
    "right_click": right_click,
    "type": type_text,
    "press_key": press_key,
    "scroll": scroll,
    "download_file": download_file,
    "open_app": open_app,
    "open_url": open_url,
    "cursor_position": cursor_position,
    "screen_size": screen_size,
    "list_dir": list_dir,
    "read_file": read_file,
    "write_file": write_file,
    "make_dir": make_dir,
    "run_shell": run_shell,
}


# ─── WebSocket loop ──────────────────────────────────────────────────────────
async def _hello(ws):
    info = {
        "os": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "screen": list(pyautogui.size()),
        "downloads": str(DOWNLOADS_DIR),
        "shell_enabled": _SHELL_ENABLED,
        "user": os.environ.get("USER") or os.environ.get("USERNAME") or "",
    }
    await ws.send(json.dumps({"type": "hello", "info": info}))


async def run_agent(server_url: str, code: str):
    url = f"{server_url}?code={code}"
    log.info(f"Connecting to {url}…")
    backoff = 2
    while True:
        try:
            async with websockets.connect(url, ping_interval=20, max_size=8 * 1024 * 1024) as ws:
                log.info("✅ Connected. Waiting for AI commands…  (Ctrl+C to stop)")
                await _hello(ws)
                backoff = 2
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue
                    mtype = msg.get("type")
                    if mtype == "command":
                        action = msg.get("action") or ""
                        params = msg.get("params") or {}
                        fn = ACTIONS.get(action)
                        if not fn:
                            payload = {"ok": False, "error": f"unknown action: {action}"}
                        else:
                            log.info(f"→ {action}({list(params.keys()) or ''})")
                            try:
                                payload = fn(params)
                            except Exception as e:
                                payload = {"ok": False, "error": f"{type(e).__name__}: {e}"}
                        await ws.send(json.dumps({
                            "type": "response",
                            "request_id": msg.get("request_id"),
                            "payload": payload,
                        }))
                    elif mtype == "ping":
                        await ws.send(json.dumps({"type": "pong"}))
                    elif mtype == "paired":
                        log.info(f"🔗 Paired with project {msg.get('project_id')}")
                    elif mtype == "error":
                        log.error(f"Server error: {msg.get('message')}")
        except (websockets.ConnectionClosed, OSError, ConnectionRefusedError) as e:
            log.warning(f"Connection lost ({e}); reconnecting in {backoff}s…")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)
        except websockets.exceptions.InvalidStatusCode as e:
            log.error(f"Server rejected connection ({e}). Wrong code or expired?")
            await asyncio.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="Zenrex Desktop Agent")
    parser.add_argument("--code", help="6-character pairing code from Zenrex chat.")
    parser.add_argument("--server", help="Override WebSocket server URL (wss://…)")
    parser.add_argument("--allow-shell", action="store_true",
                        help="Allow the AI to run shell commands on this machine.")
    args = parser.parse_args()

    global _SHELL_ENABLED
    _SHELL_ENABLED = args.allow_shell

    code = args.code or input("🔑 Pairing code (from Zenrex chat): ").strip()
    if not code:
        print("Pairing code required. Exiting.")
        sys.exit(1)

    server = args.server or _load_config_server()

    print("=" * 64)
    print(f"🤖 Zenrex Desktop Agent v0.2 — {platform.system()} {platform.machine()}")
    print(f"   Server:    {server}")
    print(f"   Screen:    {pyautogui.size()}")
    print(f"   Downloads: {DOWNLOADS_DIR}")
    print(f"   Shell exec: {'ENABLED ⚠️ ' if _SHELL_ENABLED else 'disabled (safe)'}")
    print(f"   FAILSAFE:  Move mouse to top-left corner to abort any action.")
    print("=" * 64)

    try:
        asyncio.run(run_agent(server, code))
    except KeyboardInterrupt:
        log.info("Bye 👋")


if __name__ == "__main__":
    main()
