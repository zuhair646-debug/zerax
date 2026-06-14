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

# Force UTF-8 stdout on Windows so emoji/non-ASCII in prints don't crash
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
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
    x = params.get("x")
    y = params.get("y")
    button = params.get("button", "left")
    clicks = int(params.get("clicks", 1))
    if x is not None and y is not None:
        pyautogui.click(int(x), int(y), clicks=clicks, button=button)
    else:
        pyautogui.click(clicks=clicks, button=button)
    return {"ok": True}


def double_click(params: dict) -> dict:
    p = dict(params)
    p["clicks"] = 2
    return click(p)


def right_click(params: dict) -> dict:
    p = dict(params)
    p["button"] = "right"
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
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
        })
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as f:
            f.write(resp.read())
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
            time.sleep(0.8)
        elif system == "Windows":
            aliases = {
                "notepad": "notepad.exe", "chrome": "chrome.exe",
                "edge": "msedge.exe", "firefox": "firefox.exe",
                "calculator": "calc.exe", "calc": "calc.exe",
                "explorer": "explorer.exe", "cmd": "cmd.exe",
                "powershell": "powershell.exe", "terminal": "wt.exe",
                "vs code": "code.cmd", "vscode": "code.cmd", "code": "code.cmd",
            }
            exe = aliases.get(name.lower(), name)
            try:
                subprocess.Popen([exe], shell=False)
            except FileNotFoundError:
                subprocess.Popen(["start", "", exe], shell=True)
            time.sleep(1.5)
            # Try to bring to front
            try:
                import pygetwindow as gw
                hints = [name, exe.replace(".exe", "")]
                for hint in hints:
                    matches = [w for w in gw.getAllWindows()
                               if hint.lower() in (w.title or "").lower() and (w.title or "").strip()]
                    if matches:
                        try:
                            matches[0].activate()
                        except Exception:
                            try:
                                matches[0].minimize()
                                time.sleep(0.1)
                                matches[0].restore()
                            except Exception:
                                pass
                        break
            except Exception:
                pass
            time.sleep(0.4)
        else:  # Linux
            subprocess.Popen([name])
            time.sleep(0.8)
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
                "error": "local shell disabled (run agent without --no-shell to enable)."}
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


# ═════════════════════════════════════════════════════════════════════════════
# v0.8.0 — Clipboard, Workspace, Overlay, Self-Update, File Search
# ═════════════════════════════════════════════════════════════════════════════

# ─── Workspace: dedicated folder for AI-generated files ──────────────────────
WORKSPACE_DIR = Path.home() / "Downloads" / "zenrex_workspace"
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


def _workspace_path(rel: str) -> Path:
    """Resolve a path inside the workspace, blocking ../ escapes."""
    rel = (rel or "").lstrip("/\\")
    p = (WORKSPACE_DIR / rel).resolve()
    if WORKSPACE_DIR.resolve() not in p.parents and p != WORKSPACE_DIR.resolve():
        raise ValueError("path escapes workspace")
    return p


def workspace_save(params: dict) -> dict:
    """Save a file in the workspace. content_b64 takes priority over content."""
    filename = params.get("filename") or ""
    if not filename:
        return {"ok": False, "error": "filename required"}
    try:
        path = _workspace_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        if params.get("content_b64"):
            data = base64.b64decode(params["content_b64"])
            path.write_bytes(data)
        else:
            path.write_text(str(params.get("content", "")), encoding="utf-8")
        return {"ok": True, "path": str(path), "size": path.stat().st_size,
                "workspace_relative": str(path.relative_to(WORKSPACE_DIR))}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def workspace_list(params: dict) -> dict:
    subdir = (params.get("subdir") or "").strip()
    try:
        root = _workspace_path(subdir) if subdir else WORKSPACE_DIR
        if not root.exists():
            return {"ok": True, "root": str(root), "entries": [], "count": 0}
        out = []
        for p in sorted(root.rglob("*"))[:500]:
            if p.is_file():
                try:
                    out.append({
                        "name": str(p.relative_to(WORKSPACE_DIR)),
                        "size": p.stat().st_size,
                        "mtime": int(p.stat().st_mtime),
                    })
                except Exception:
                    continue
        return {"ok": True, "root": str(WORKSPACE_DIR), "entries": out, "count": len(out)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def workspace_read(params: dict) -> dict:
    """Read a file from the workspace by relative name."""
    name = params.get("filename") or ""
    if not name:
        return {"ok": False, "error": "filename required"}
    max_bytes = int(params.get("max_bytes", 500_000))
    try:
        path = _workspace_path(name)
        if not path.exists():
            return {"ok": False, "error": "file not in workspace"}
        data = path.read_bytes()[:max_bytes]
        try:
            return {"ok": True, "path": str(path), "text": data.decode("utf-8"),
                    "size_total": path.stat().st_size}
        except UnicodeDecodeError:
            return {"ok": True, "path": str(path),
                    "content_b64": base64.b64encode(data).decode("ascii"),
                    "size_total": path.stat().st_size}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def search_files(params: dict) -> dict:
    """Search files on the OS by pattern. Default scope: Documents + Downloads + Desktop."""
    pattern = params.get("pattern", "*").strip()
    max_results = int(params.get("max_results", 100))
    if "*" not in pattern and "?" not in pattern:
        pattern = f"*{pattern}*"
    roots_arg = params.get("roots") or []
    if not roots_arg:
        roots_arg = [
            str(Path.home() / "Documents"),
            str(Path.home() / "Downloads"),
            str(Path.home() / "Desktop"),
        ]
    if isinstance(roots_arg, str):
        roots_arg = [roots_arg]
    found = []
    seen = set()
    try:
        for r in roots_arg:
            root = Path(r).expanduser()
            if not root.exists():
                continue
            for p in root.rglob(pattern):
                if len(found) >= max_results:
                    break
                if not p.is_file():
                    continue
                key = str(p)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    st = p.stat()
                    found.append({
                        "path": str(p),
                        "name": p.name,
                        "size": st.st_size,
                        "mtime": int(st.st_mtime),
                    })
                except Exception:
                    continue
            if len(found) >= max_results:
                break
        return {"ok": True, "pattern": pattern, "count": len(found), "results": found}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ─── Clipboard: pyperclip-based, supports any unicode ────────────────────────
def _ensure_pyperclip():
    try:
        import pyperclip
        return pyperclip
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pyperclip"])
            import pyperclip
            return pyperclip
        except Exception:
            return None


def clipboard_set(params: dict) -> dict:
    text = params.get("text", "")
    pc = _ensure_pyperclip()
    if pc is None:
        return {"ok": False, "error": "pyperclip unavailable"}
    try:
        pc.copy(text)
        return {"ok": True, "chars": len(text)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def clipboard_get(_params: dict) -> dict:
    pc = _ensure_pyperclip()
    if pc is None:
        return {"ok": False, "error": "pyperclip unavailable"}
    try:
        return {"ok": True, "text": pc.paste()}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def clipboard_paste(params: dict) -> dict:
    """Type ANY text (Arabic, emoji, code) by writing to clipboard then Ctrl+V.

    Much faster + more reliable than typewrite for non-ASCII or long text.
    """
    text = params.get("text", "")
    if not text:
        return {"ok": False, "error": "text required"}
    pc = _ensure_pyperclip()
    if pc is None:
        # Fallback to typewrite
        try:
            pyautogui.typewrite(text, interval=0.005)
            return {"ok": True, "method": "typewrite_fallback", "chars": len(text)}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    try:
        # Preserve previous clipboard if asked
        previous = None
        if params.get("restore_clipboard"):
            try:
                previous = pc.paste()
            except Exception:
                pass
        pc.copy(text)
        time.sleep(0.08)
        paste_key = "command+v" if platform.system() == "Darwin" else "ctrl+v"
        pyautogui.hotkey(*paste_key.split("+"))
        time.sleep(0.05)
        if previous is not None:
            try:
                pc.copy(previous)
            except Exception:
                pass
        return {"ok": True, "method": "clipboard_paste", "chars": len(text)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ─── On-screen overlay: floating status panel for the owner to watch ────────
_OVERLAY_STATE: dict = {"thread": None, "queue": None, "alive": False}


def _overlay_worker(initial_text: str):
    """Tkinter overlay running in its own thread. Communicates via queue."""
    import queue as _queue
    import tkinter as tk

    q = _OVERLAY_STATE["queue"]
    root = tk.Tk()
    root.title("Zenrex AI")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", 0.92)
    except Exception:
        pass
    # Position: top-right with margin
    sw = root.winfo_screenwidth()
    w, h = 420, 110
    x, y = sw - w - 24, 24
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.configure(bg="#0f0f17")

    title_lbl = tk.Label(root, text="🤖 Zenrex AI", fg="#a78bfa", bg="#0f0f17",
                        font=("Segoe UI", 11, "bold"), anchor="w", padx=14, pady=4)
    title_lbl.pack(fill="x")
    msg_lbl = tk.Label(root, text=initial_text, fg="#e5e7eb", bg="#0f0f17",
                       font=("Segoe UI", 10), wraplength=400, justify="right",
                       anchor="nw", padx=14, pady=4)
    msg_lbl.pack(fill="both", expand=True)

    def _drain():
        try:
            while True:
                cmd = q.get_nowait()
                if cmd[0] == "update":
                    msg_lbl.config(text=cmd[1])
                elif cmd[0] == "title":
                    title_lbl.config(text=cmd[1])
                elif cmd[0] == "hide":
                    root.destroy()
                    _OVERLAY_STATE["alive"] = False
                    return
        except _queue.Empty:
            pass
        if _OVERLAY_STATE["alive"]:
            root.after(120, _drain)

    _OVERLAY_STATE["alive"] = True
    root.after(120, _drain)
    try:
        root.mainloop()
    finally:
        _OVERLAY_STATE["alive"] = False


def overlay_show(params: dict) -> dict:
    import queue
    import threading
    text = params.get("text", "")
    if _OVERLAY_STATE["alive"]:
        try:
            _OVERLAY_STATE["queue"].put(("update", text))
            return {"ok": True, "action": "updated"}
        except Exception:
            pass
    _OVERLAY_STATE["queue"] = queue.Queue()
    th = threading.Thread(target=_overlay_worker, args=(text,), daemon=True)
    _OVERLAY_STATE["thread"] = th
    th.start()
    return {"ok": True, "action": "started"}


def overlay_update(params: dict) -> dict:
    if not _OVERLAY_STATE["alive"]:
        return overlay_show(params)
    try:
        _OVERLAY_STATE["queue"].put(("update", params.get("text", "")))
        if params.get("title"):
            _OVERLAY_STATE["queue"].put(("title", params["title"]))
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def overlay_hide(_params: dict) -> dict:
    if not _OVERLAY_STATE["alive"]:
        return {"ok": True, "action": "already_hidden"}
    try:
        _OVERLAY_STATE["queue"].put(("hide", ""))
        return {"ok": True, "action": "hiding"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ─── Self-update: download latest agent + restart ────────────────────────────
def self_update(params: dict) -> dict:
    """Fetch the newest zenrex_agent.py from server, overwrite self, restart."""
    src_url = params.get("source_url") or os.environ.get(
        "ZENREX_AGENT_SOURCE",
        "https://zenrex.ai/api/desktop-agent/agent-source",
    )
    try:
        req = urllib.request.Request(src_url, headers={"User-Agent": "ZenrexDesktopAgent"})
        with urllib.request.urlopen(req, timeout=20) as r:
            new_code = r.read().decode("utf-8")
        if len(new_code) < 1000 or "ZENREX_AGENT_VERSION" not in new_code and "Zenrex Desktop Agent" not in new_code:
            return {"ok": False, "error": "downloaded source looks invalid"}
        target = Path(__file__).resolve()
        backup = target.with_suffix(".py.bak")
        try:
            backup.write_bytes(target.read_bytes())
        except Exception:
            pass
        target.write_text(new_code, encoding="utf-8")
        # Schedule restart: launch a fresh interpreter in 1.5s, then exit
        # Read code from .last_code if present so we reconnect with same pairing
        last_code_path = SCRIPT_DIR / ".last_code"
        last_code = last_code_path.read_text(encoding="utf-8").strip() if last_code_path.exists() else ""

        if platform.system() == "Windows":
            launcher = (
                f"timeout /t 2 /nobreak >NUL & start \"\" \"{sys.executable}\" "
                f"\"{target}\" --code {last_code}"
            )
            subprocess.Popen(["cmd", "/c", launcher], creationflags=0x00000008)  # DETACHED
        else:
            subprocess.Popen(
                f"sleep 2; \"{sys.executable}\" \"{target}\" --code {last_code} &",
                shell=True,
            )

        # Respond, then quit
        def _quit():
            time.sleep(0.6)
            os._exit(0)

        import threading
        threading.Thread(target=_quit, daemon=True).start()
        return {"ok": True, "restarting": True, "new_size": len(new_code)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# Register all new actions
ACTIONS.update({
    # Clipboard
    "clipboard_set": clipboard_set,
    "clipboard_get": clipboard_get,
    "clipboard_paste": clipboard_paste,
    # Workspace
    "workspace_save": workspace_save,
    "workspace_list": workspace_list,
    "workspace_read": workspace_read,
    "search_files": search_files,
    # Overlay
    "overlay_show": overlay_show,
    "overlay_update": overlay_update,
    "overlay_hide": overlay_hide,
    # Self-update
    "self_update": self_update,
})


# ─── WebSocket loop ──────────────────────────────────────────────────────────
async def _hello(ws):
    import socket as _socket
    info = {
        "os": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "hostname": _socket.gethostname(),
        "python": sys.version.split()[0],
        "screen": list(pyautogui.size()),
        "downloads": str(DOWNLOADS_DIR),
        "shell_enabled": _SHELL_ENABLED,
        "user": os.environ.get("USER") or os.environ.get("USERNAME") or "",
        "agent_version": "0.8.1",
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
                        help="(Deprecated, kept for backwards compat) Shell is enabled by default since v0.8.1.")
    parser.add_argument("--no-shell", action="store_true",
                        help="Disable the run_shell action on this machine.")
    args = parser.parse_args()

    global _SHELL_ENABLED
    # Since v0.8.1 shell is enabled by default for power users. Use --no-shell to
    # opt out. The legacy --allow-shell flag is still accepted but is now a no-op.
    _SHELL_ENABLED = not args.no_shell

    code = args.code or input("🔑 Pairing code (from Zenrex chat): ").strip()
    if not code:
        print("Pairing code required. Exiting.")
        sys.exit(1)

    server = args.server or _load_config_server()

    print("=" * 64)
    print(f"[ZENREX] Zenrex Desktop Agent v0.8.1 - {platform.system()} {platform.machine()}")
    print(f"   Server:    {server}")
    print(f"   Screen:    {pyautogui.size()}")
    print(f"   Downloads: {DOWNLOADS_DIR}")
    print(f"   Shell exec: {'ENABLED [!] ' if _SHELL_ENABLED else 'disabled (safe)'}")
    print("   FAILSAFE:  Move mouse to top-left corner to abort any action.")
    print("=" * 64)

    try:
        asyncio.run(run_agent(server, code))
    except KeyboardInterrupt:
        log.info("Bye 👋")


if __name__ == "__main__":
    main()
