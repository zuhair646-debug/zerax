"""
Zenrex Desktop Agent — GUI version (Tkinter, runs with pythonw.exe, no terminal).

Saves the last-used pairing code to ~/.zenrex-desktop-agent/.last_code so the
app remembers it across launches. The user just clicks Connect.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import platform
import queue
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import Tk, StringVar, ttk, Text, END, DISABLED, NORMAL, messagebox, Frame, Label, Button, Entry

# Required deps (installed by bootstrap)
import pyautogui
import mss
from PIL import Image
import websockets

# ─── Config & constants ──────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
LAST_CODE_FILE = SCRIPT_DIR / ".last_code"
DEFAULT_WS = "wss://zenrex.ai/api/desktop-agent/ws"
DOWNLOADS_DIR = Path.home() / "Downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

pyautogui.FAILSAFE = True


def _load_server() -> str:
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


def _platform_base() -> str:
    cfg = SCRIPT_DIR / "config.json"
    if cfg.exists():
        try:
            return json.loads(cfg.read_text(encoding="utf-8")).get("platform", "")
        except Exception:
            return ""
    return ""


# ─── Action handlers (same as console version) ──────────────────────────────
def _safe_path(p: str) -> Path:
    return Path(os.path.expanduser(str(p))).resolve()


def screenshot(_):
    with mss.mss() as sct:
        mon = sct.monitors[1]
        sct_img = sct.grab(mon)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        if img.width > 1600:
            r = 1600 / img.width
            img = img.resize((1600, int(img.height * r)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=55)
        return {"ok": True, "screenshot_b64": base64.b64encode(buf.getvalue()).decode("ascii"),
                "size": {"width": mon["width"], "height": mon["height"]},
                "encoded_size": {"width": img.width, "height": img.height}}


def _smooth_duration(from_x: int, from_y: int, to_x: int, to_y: int) -> float:
    """Pick a duration that feels human: ~600px/sec, min 0.4s, max 1.6s."""
    import math
    dist = math.hypot(to_x - from_x, to_y - from_y)
    return max(0.4, min(1.6, dist / 600.0))


def move_mouse(p):
    cur_x, cur_y = pyautogui.position()
    tx = int(p.get("x", 0)); ty = int(p.get("y", 0))
    dur = p.get("duration")
    if dur is None:
        dur = _smooth_duration(cur_x, cur_y, tx, ty)
    pyautogui.moveTo(tx, ty, duration=float(dur), tween=pyautogui.easeInOutQuad)
    return {"ok": True, "duration": dur}


def click(p):
    x, y = p.get("x"), p.get("y")
    btn, n = p.get("button", "left"), int(p.get("clicks", 1))
    if x is not None and y is not None:
        # Move smoothly first so the user SEES where the click will land
        cur_x, cur_y = pyautogui.position()
        pyautogui.moveTo(int(x), int(y),
                          duration=_smooth_duration(cur_x, cur_y, int(x), int(y)),
                          tween=pyautogui.easeInOutQuad)
        time.sleep(0.15)
        pyautogui.click(int(x), int(y), clicks=n, button=btn)
    else:
        pyautogui.click(clicks=n, button=btn)
    return {"ok": True}


def double_click(p):
    q = dict(p); q["clicks"] = 2; return click(q)


def right_click(p):
    q = dict(p); q["button"] = "right"; return click(q)


def type_text(p):
    text = p.get("text", "")
    # Default to a "visible-typing" speed (~25 chars/sec) so the user sees
    # each character appear. Caller can override with explicit interval.
    interval = float(p.get("interval", 0.04))
    try:
        pyautogui.typewrite(text, interval=interval)
    except Exception:
        try:
            import pyperclip
            pyperclip.copy(text)
            paste = "command+v" if platform.system() == "Darwin" else "ctrl+v"
            pyautogui.hotkey(*paste.split("+"))
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return {"ok": True, "chars": len(text)}


def press_key(p):
    parts = [x.strip() for x in p.get("key", "").split("+") if x.strip()]
    if not parts:
        return {"ok": False, "error": "key required"}
    if len(parts) == 1:
        pyautogui.press(parts[0])
    else:
        pyautogui.hotkey(*parts)
    return {"ok": True}


def scroll(p):
    pyautogui.scroll(int(p.get("amount", -3))); return {"ok": True}


def download_file(p):
    url = p.get("url", "")
    if not url:
        return {"ok": False, "error": "url required"}
    name = p.get("filename") or url.rsplit("/", 1)[-1].split("?")[0] or "download"
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


def _focus_window_by_title(needle: str) -> bool:
    """Bring a window matching `needle` (case-insensitive substring) to the front.
    Returns True if a window was activated.
    """
    try:
        import pygetwindow as gw
    except Exception:
        return False
    try:
        needle_low = needle.lower()
        for w in gw.getAllWindows():
            try:
                if needle_low in (w.title or "").lower() and (w.title or "").strip():
                    try:
                        if w.isMinimized:
                            w.restore()
                    except Exception:
                        pass
                    try:
                        w.activate()
                    except Exception:
                        # Common Win32 fallback: minimize + restore forces foreground
                        try:
                            w.minimize(); time.sleep(0.1); w.restore()
                        except Exception:
                            pass
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


# Map common app aliases to executables + likely window-title fragments
_WIN_APP_ALIASES = {
    "notepad":     ("notepad.exe",     ["Notepad", "المفكرة"]),
    "chrome":      ("chrome.exe",      ["Chrome", "Google Chrome"]),
    "edge":        ("msedge.exe",      ["Edge", "Microsoft Edge"]),
    "firefox":     ("firefox.exe",     ["Firefox", "Mozilla Firefox"]),
    "calculator":  ("calc.exe",        ["Calculator", "الآلة الحاسبة"]),
    "calc":        ("calc.exe",        ["Calculator", "الآلة الحاسبة"]),
    "explorer":    ("explorer.exe",    ["File Explorer", "مستكشف الملفات"]),
    "file explorer": ("explorer.exe",  ["File Explorer", "مستكشف الملفات"]),
    "cmd":         ("cmd.exe",         ["Command Prompt", "cmd"]),
    "powershell":  ("powershell.exe",  ["PowerShell"]),
    "terminal":    ("wt.exe",          ["Terminal"]),
    "vs code":     ("code.cmd",        ["Visual Studio Code", "VS Code"]),
    "vscode":      ("code.cmd",        ["Visual Studio Code", "VS Code"]),
    "code":        ("code.cmd",        ["Visual Studio Code", "VS Code"]),
}


def open_app(p):
    name = (p.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "name required"}
    s = platform.system()
    try:
        if s == "Darwin":
            subprocess.Popen(["open", "-a", name])
            time.sleep(0.8)
        elif s == "Windows":
            key = name.lower()
            exe, title_hints = _WIN_APP_ALIASES.get(key, (None, [name]))
            # Choose what to spawn
            if exe:
                # Try direct exe first (faster, no shell overhead)
                try:
                    subprocess.Popen([exe], shell=False)
                except FileNotFoundError:
                    subprocess.Popen(["start", "", exe], shell=True)
            else:
                subprocess.Popen(["start", "", name], shell=True)
            # Wait + try to bring to front using any matching title hint
            focused = False
            for _ in range(15):  # up to ~3s
                time.sleep(0.2)
                for hint in title_hints:
                    if _focus_window_by_title(hint):
                        focused = True
                        break
                if focused:
                    break
            # Final small settle delay so the app accepts keystrokes
            time.sleep(0.4)
            return {"ok": True, "app": name, "focused": focused}
        else:  # Linux
            subprocess.Popen([name])
            time.sleep(0.8)
        return {"ok": True, "app": name}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def focus_window(p):
    """Bring an existing window to the front by title substring."""
    title = (p.get("title") or "").strip()
    if not title:
        return {"ok": False, "error": "title required"}
    return {"ok": _focus_window_by_title(title), "title": title}


def open_url(p):
    url = p.get("url", "")
    if not url:
        return {"ok": False, "error": "url required"}
    webbrowser.open(url)
    # Give the browser ~1.5s + try to focus
    time.sleep(1.2)
    for hint in ("Chrome", "Edge", "Firefox", "Opera", "Safari"):
        if _focus_window_by_title(hint):
            break
    time.sleep(0.3)
    return {"ok": True, "url": url}


def cursor_position(_):
    x, y = pyautogui.position(); return {"ok": True, "x": int(x), "y": int(y)}


def screen_size(_):
    w, h = pyautogui.size(); return {"ok": True, "width": int(w), "height": int(h)}


def list_dir(p):
    path = _safe_path(p.get("path") or str(Path.home()))
    if not path.is_dir():
        return {"ok": False, "error": "not a directory"}
    out = []
    for c in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:500]:
        try:
            out.append({"name": c.name, "is_dir": c.is_dir(),
                        "size": c.stat().st_size if c.is_file() else None})
        except Exception:
            pass
    return {"ok": True, "path": str(path), "entries": out, "count": len(out)}


def read_file(p):
    path = _safe_path(p.get("path", ""))
    if not path.is_file():
        return {"ok": False, "error": "not found"}
    data = path.read_bytes()[:int(p.get("max_bytes", 200_000))]
    try:
        return {"ok": True, "path": str(path), "text": data.decode("utf-8"),
                "size_total": path.stat().st_size, "size_returned": len(data)}
    except UnicodeDecodeError:
        return {"ok": True, "path": str(path),
                "binary_b64": base64.b64encode(data).decode("ascii"),
                "size_total": path.stat().st_size, "size_returned": len(data)}


def write_file(p):
    path = _safe_path(p.get("path", ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(p.get("content", "")), encoding="utf-8")
    return {"ok": True, "path": str(path), "bytes": path.stat().st_size}


def make_dir(p):
    path = _safe_path(p.get("path", "")); path.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "path": str(path)}


ACTIONS = {
    "screenshot": screenshot, "move_mouse": move_mouse, "click": click,
    "double_click": double_click, "right_click": right_click,
    "type": type_text, "press_key": press_key, "scroll": scroll,
    "download_file": download_file, "open_app": open_app, "open_url": open_url,
    "focus_window": focus_window,
    "cursor_position": cursor_position, "screen_size": screen_size,
    "list_dir": list_dir, "read_file": read_file, "write_file": write_file,
    "make_dir": make_dir,
}


# Human-readable description of each action for the floating overlay
ACTION_LABELS_AR = {
    "screenshot":      ("📸", "يلتقط شاشتك..."),
    "move_mouse":      ("🖱️", "يحرّك الماوس..."),
    "click":           ("👆", "يضغط..."),
    "double_click":    ("👆👆", "ضغط مزدوج..."),
    "right_click":     ("🖱️", "ضغط يمين..."),
    "type":            ("⌨️", "يكتب..."),
    "press_key":       ("🎹", "يضغط مفتاح..."),
    "scroll":          ("🖱️", "يمرّر الشاشة..."),
    "download_file":   ("📥", "ينزّل ملف..."),
    "open_app":        ("🚀", "يفتح تطبيق..."),
    "open_url":        ("🌐", "يفتح موقع..."),
    "focus_window":    ("🎯", "يجيب نافذة للواجهة..."),
    "cursor_position": ("📍", "يتحقق من موقع الماوس..."),
    "screen_size":     ("📐", "يقيس الشاشة..."),
    "list_dir":        ("📁", "يتصفح مجلد..."),
    "read_file":       ("📖", "يقرأ ملف..."),
    "write_file":      ("✍️", "يكتب ملف..."),
    "make_dir":        ("📁", "ينشئ مجلد..."),
    "run_shell":       ("💻", "ينفّذ أمر..."),
}


def _humanize_action(action: str, params: dict) -> str:
    icon, label = ACTION_LABELS_AR.get(action, ("⚙️", action))
    detail = ""
    if action == "type" and params.get("text"):
        t = str(params["text"]); detail = f": “{t[:40]}{'…' if len(t)>40 else ''}”"
    elif action == "open_url" and params.get("url"):
        detail = f": {params['url'][:50]}"
    elif action == "open_app" and params.get("name"):
        detail = f": {params['name']}"
    elif action == "click" and params.get("x") is not None:
        detail = f" @ ({params['x']}, {params['y']})"
    elif action == "move_mouse":
        detail = f" → ({params.get('x','?')}, {params.get('y','?')})"
    elif action == "download_file" and params.get("url"):
        detail = f": {params['url'][:40]}…"
    elif action == "press_key" and params.get("key"):
        detail = f": {params['key']}"
    elif action in ("write_file", "read_file", "list_dir") and params.get("path"):
        detail = f": {params['path']}"
    return f"{icon}  {label}{detail}"


# ─── WebSocket worker thread ─────────────────────────────────────────────────
class AgentWorker(threading.Thread):
    def __init__(self, server_url: str, code: str, log_q: queue.Queue,
                 status_q: queue.Queue, action_q: queue.Queue):
        super().__init__(daemon=True)
        self.server_url = server_url
        self.code = code
        self.log_q = log_q
        self.status_q = status_q
        self.action_q = action_q
        self._stop = threading.Event()
        self._loop = None

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        try:
            self.log_q.put_nowait(f"[{ts}] {msg}")
        except queue.Full:
            pass

    def status(self, state: str):
        try:
            self.status_q.put_nowait(state)
        except queue.Full:
            pass

    def announce(self, text: str):
        try:
            self.action_q.put_nowait(text)
        except queue.Full:
            pass

    def stop(self):
        self._stop.set()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    async def _run_async(self):
        url = f"{self.server_url}?code={self.code}"
        self.log(f"Connecting to {url} …")
        backoff = 2
        while not self._stop.is_set():
            try:
                async with websockets.connect(url, ping_interval=20, max_size=8 * 1024 * 1024) as ws:
                    self.status("connected")
                    self.log("✅ Connected — waiting for AI commands")
                    backoff = 2
                    # Hello
                    info = {
                        "os": platform.system(), "release": platform.release(),
                        "machine": platform.machine(), "python": sys.version.split()[0],
                        "screen": list(pyautogui.size()),
                        "downloads": str(DOWNLOADS_DIR),
                        "user": os.environ.get("USER") or os.environ.get("USERNAME") or "",
                    }
                    await ws.send(json.dumps({"type": "hello", "info": info}))
                    async for raw in ws:
                        if self._stop.is_set():
                            break
                        try:
                            msg = json.loads(raw)
                        except Exception:
                            continue
                        t = msg.get("type")
                        if t == "command":
                            action = msg.get("action", "")
                            params = msg.get("params") or {}
                            human = _humanize_action(action, params)
                            self.log(f"→ {action}")
                            self.announce(human)
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
                        elif t == "ping":
                            await ws.send(json.dumps({"type": "pong"}))
                        elif t == "paired":
                            self.log(f"🔗 Paired with project {msg.get('project_id')}")
                        elif t == "error":
                            self.log(f"⚠️ Server: {msg.get('message')}")
            except Exception as e:
                if self._stop.is_set():
                    break
                self.status("reconnecting")
                self.log(f"Disconnected ({e.__class__.__name__}); retry in {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
        self.status("disconnected")
        self.log("Stopped.")

    def run(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._run_async())
        except Exception as e:
            self.log(f"Fatal: {e}")
            self.status("disconnected")


# ─── GUI ─────────────────────────────────────────────────────────────────────
class ZenrexGUI:
    PRIMARY = "#7c3aed"        # purple
    BG = "#0f0f17"             # near-black
    BG2 = "#1a1a26"
    FG = "#e5e7eb"
    MUTED = "#9ca3af"
    OK = "#10b981"
    WARN = "#f59e0b"
    ERR = "#ef4444"

    def __init__(self):
        self.root = Tk()
        self.root.title("Zenrex Desktop Agent")
        self.root.geometry("520x520")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self.code_var = StringVar()
        self.worker: AgentWorker | None = None
        self.log_q: queue.Queue = queue.Queue(maxsize=200)
        self.status_q: queue.Queue = queue.Queue(maxsize=50)
        self.action_q: queue.Queue = queue.Queue(maxsize=200)

        self._build_ui()
        self._build_overlay()
        self._load_last_code()
        # Poll worker queues every 100ms
        self.root.after(100, self._drain_queues)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─── UI construction ────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        header = Frame(self.root, bg=self.BG, pady=20)
        header.pack(fill="x")
        Label(header, text="⚡ Zenrex Desktop Agent",
              font=("Segoe UI", 18, "bold"), fg=self.FG, bg=self.BG).pack()
        Label(header, text="Native OS control for Zenrex AI",
              font=("Segoe UI", 10), fg=self.MUTED, bg=self.BG).pack(pady=(2, 0))

        # Status pill
        self.status_frame = Frame(self.root, bg=self.BG, pady=8)
        self.status_frame.pack()
        self.status_dot = Label(self.status_frame, text="●", font=("Segoe UI", 14, "bold"),
                                fg=self.ERR, bg=self.BG)
        self.status_dot.pack(side="left", padx=(0, 6))
        self.status_text = Label(self.status_frame, text="Not connected",
                                  font=("Segoe UI", 10), fg=self.MUTED, bg=self.BG)
        self.status_text.pack(side="left")

        # Code input card
        card = Frame(self.root, bg=self.BG2, padx=24, pady=20)
        card.pack(fill="x", padx=24, pady=8)
        Label(card, text="Pairing code", font=("Segoe UI", 9, "bold"),
              fg=self.MUTED, bg=self.BG2).pack(anchor="w")
        entry_row = Frame(card, bg=self.BG2)
        entry_row.pack(fill="x", pady=(8, 0))
        self.code_entry = Entry(entry_row, textvariable=self.code_var, font=("Consolas", 16, "bold"),
                                bg=self.BG, fg=self.FG, insertbackground=self.FG,
                                relief="flat", justify="center", width=12)
        self.code_entry.pack(side="left", ipady=8, padx=(0, 6), fill="x", expand=True)
        # Paste button — pulls clipboard into the entry
        self.paste_btn = Button(entry_row, text="📋", font=("Segoe UI", 11),
                                 bg=self.BG, fg=self.FG, relief="flat",
                                 activebackground=self.BG2, activeforeground="white",
                                 padx=10, pady=8, cursor="hand2",
                                 command=self._paste_clipboard)
        self.paste_btn.pack(side="left", padx=(0, 6))
        # Connect button
        self.connect_btn = Button(entry_row, text="Connect", font=("Segoe UI", 10, "bold"),
                                   bg=self.PRIMARY, fg="white", relief="flat",
                                   activebackground="#6d28d9", activeforeground="white",
                                   padx=18, pady=8, cursor="hand2",
                                   command=self._toggle_connection)
        self.connect_btn.pack(side="right")
        # Keyboard bindings: Ctrl+V paste + Enter to connect
        self.code_entry.bind("<Control-v>", lambda e: self._paste_clipboard() or "break")
        self.code_entry.bind("<Control-V>", lambda e: self._paste_clipboard() or "break")
        # Some Arabic-layout keyboards send different keysym for V — bind to any printable too
        self.code_entry.bind("<Return>", lambda e: self._toggle_connection())
        # Right-click context menu (Cut/Copy/Paste)
        self._build_entry_context_menu()

        # Get-code helper
        help_row = Frame(self.root, bg=self.BG)
        help_row.pack(fill="x", padx=24, pady=(0, 8))
        Label(help_row, text="Need a code? In your Zenrex chat type:",
              font=("Segoe UI", 9), fg=self.MUTED, bg=self.BG).pack(side="left")
        Label(help_row, text="\"اربط جهازي\"", font=("Segoe UI", 9, "bold"),
              fg=self.PRIMARY, bg=self.BG).pack(side="left", padx=4)
        platform_url = _platform_base()
        if platform_url:
            link = Label(help_row, text="↗ Open chat", font=("Segoe UI", 9, "underline"),
                          fg=self.PRIMARY, bg=self.BG, cursor="hand2")
            link.pack(side="right")
            link.bind("<Button-1>", lambda e: webbrowser.open(platform_url))

        # Activity log
        log_label_row = Frame(self.root, bg=self.BG)
        log_label_row.pack(fill="x", padx=24, pady=(12, 4))
        Label(log_label_row, text="Activity", font=("Segoe UI", 9, "bold"),
              fg=self.MUTED, bg=self.BG).pack(side="left")

        log_card = Frame(self.root, bg=self.BG2)
        log_card.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        self.log_text = Text(log_card, font=("Consolas", 9), bg=self.BG2, fg=self.FG,
                              relief="flat", height=12, padx=12, pady=10, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state=DISABLED)

        # Footer
        footer = Frame(self.root, bg=self.BG, pady=8)
        footer.pack(fill="x")
        Label(footer,
              text="🛡️ Move mouse to top-left to abort any AI action  •  Close window to disconnect",
              font=("Segoe UI", 8), fg=self.MUTED, bg=self.BG).pack()

    # ─── State management ───────────────────────────────────────────────────
    def _set_status(self, state: str):
        mapping = {
            "connected":    (self.OK,    "Connected — AI can control this machine"),
            "reconnecting": (self.WARN,  "Reconnecting…"),
            "disconnected": (self.ERR,   "Not connected"),
        }
        color, text = mapping.get(state, (self.MUTED, state))
        self.status_dot.config(fg=color)
        self.status_text.config(text=text)
        # Update button label
        if state == "connected" or state == "reconnecting":
            self.connect_btn.config(text="Disconnect", bg="#374151")
        else:
            self.connect_btn.config(text="Connect", bg=self.PRIMARY)

    def _append_log(self, msg: str):
        self.log_text.configure(state=NORMAL)
        self.log_text.insert(END, msg + "\n")
        # Cap to last 400 lines
        if int(self.log_text.index("end-1c").split(".")[0]) > 400:
            self.log_text.delete("1.0", "200.0")
        self.log_text.see(END)
        self.log_text.configure(state=DISABLED)

    def _drain_queues(self):
        try:
            while True:
                self._append_log(self.log_q.get_nowait())
        except queue.Empty:
            pass
        try:
            while True:
                self._set_status(self.status_q.get_nowait())
        except queue.Empty:
            pass
        try:
            while True:
                self._show_overlay(self.action_q.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self._drain_queues)

    def _build_overlay(self):
        """A small always-on-top widget that announces the AI's current action.

        Positioned bottom-right by default. Auto-hides after 3s of inactivity.
        """
        from tkinter import Toplevel
        self.overlay = Toplevel(self.root)
        self.overlay.overrideredirect(True)         # no window decorations
        self.overlay.attributes("-topmost", True)   # always on top
        try:
            self.overlay.attributes("-alpha", 0.92)
        except Exception:
            pass
        self.overlay.configure(bg="#0a0a14")
        # Position bottom-right
        sw = self.overlay.winfo_screenwidth()
        sh = self.overlay.winfo_screenheight()
        w, h = 480, 64
        self.overlay.geometry(f"{w}x{h}+{sw - w - 24}+{sh - h - 80}")
        # Inner frame with a thin purple left border
        border = Frame(self.overlay, bg=self.PRIMARY)
        border.pack(side="left", fill="y")
        Label(border, text="", width=1, bg=self.PRIMARY).pack(fill="y")
        body = Frame(self.overlay, bg="#0a0a14")
        body.pack(side="left", fill="both", expand=True, padx=14, pady=10)
        Label(body, text="ZENREX AI", font=("Segoe UI", 7, "bold"),
              fg=self.PRIMARY, bg="#0a0a14").pack(anchor="w")
        self.overlay_action_label = Label(
            body, text="", font=("Segoe UI", 11, "bold"),
            fg="white", bg="#0a0a14", anchor="w", justify="left",
        )
        self.overlay_action_label.pack(anchor="w", fill="x")
        self.overlay.withdraw()  # hidden until first action
        self._overlay_hide_job = None

    def _show_overlay(self, text: str):
        self.overlay_action_label.config(text=text)
        try:
            self.overlay.deiconify()
            self.overlay.lift()
        except Exception:
            pass
        # Cancel previous hide job
        if self._overlay_hide_job is not None:
            try:
                self.root.after_cancel(self._overlay_hide_job)
            except Exception:
                pass
        self._overlay_hide_job = self.root.after(4000, self._hide_overlay)

    def _hide_overlay(self):
        try:
            self.overlay.withdraw()
        except Exception:
            pass

    # ─── Clipboard helpers ───────────────────────────────────────────────────
    def _paste_clipboard(self):
        """Replace the entry text with clipboard contents (uppercased, stripped)."""
        try:
            text = self.root.clipboard_get()
        except Exception:
            return
        cleaned = "".join(c for c in text if c.isalnum()).upper()[:6]
        if cleaned:
            self.code_var.set(cleaned)
            self.code_entry.icursor("end")
            # Flash the paste button for feedback
            self.paste_btn.config(text="✓")
            self.root.after(800, lambda: self.paste_btn.config(text="📋"))

    def _build_entry_context_menu(self):
        from tkinter import Menu
        m = Menu(self.root, tearoff=0, bg=self.BG2, fg=self.FG,
                  activebackground=self.PRIMARY, activeforeground="white",
                  bd=0)
        m.add_command(label="Paste", command=self._paste_clipboard)
        m.add_command(label="Copy", command=lambda: (
            self.root.clipboard_clear(),
            self.root.clipboard_append(self.code_var.get())
        ))
        m.add_command(label="Clear", command=lambda: self.code_var.set(""))
        self._entry_menu = m

        def show_menu(e):
            try:
                m.tk_popup(e.x_root, e.y_root)
            finally:
                m.grab_release()
        self.code_entry.bind("<Button-3>", show_menu)        # right-click
        self.code_entry.bind("<Button-2>", show_menu)        # middle-click (some setups)

    # ─── Connection control ─────────────────────────────────────────────────
    def _toggle_connection(self):
        if self.worker and self.worker.is_alive():
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        code = self.code_var.get().strip().upper()
        if len(code) < 4:
            messagebox.showwarning("Invalid code", "Please paste the pairing code from your Zenrex chat.")
            return
        self.code_var.set(code)
        self._save_last_code(code)
        self._set_status("reconnecting")
        self._append_log(f"Starting connection with code {code}…")
        self.worker = AgentWorker(_load_server(), code, self.log_q, self.status_q, self.action_q)
        self.worker.start()

    def _disconnect(self):
        if self.worker:
            self._append_log("Disconnect requested.")
            self.worker.stop()
        self._set_status("disconnected")

    def _save_last_code(self, code: str):
        try:
            LAST_CODE_FILE.write_text(code, encoding="utf-8")
        except Exception:
            pass

    def _load_last_code(self):
        if LAST_CODE_FILE.exists():
            try:
                code = LAST_CODE_FILE.read_text(encoding="utf-8").strip().upper()
                if code:
                    self.code_var.set(code)
            except Exception:
                pass

    def _on_close(self):
        if self.worker and self.worker.is_alive():
            self.worker.stop()
        self.root.after(150, self.root.destroy)

    def run(self):
        self.root.mainloop()


def main():
    # Silence noisy stderr from websockets in pythonw mode
    logging.basicConfig(level=logging.WARNING)
    app = ZenrexGUI()
    app.run()


if __name__ == "__main__":
    main()
