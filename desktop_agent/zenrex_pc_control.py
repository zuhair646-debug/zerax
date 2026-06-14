"""
Zenrex PC Control + Autonomous Game Mode (runs locally on user's PC).

A standalone FastAPI service on port 7862 that gives Zenrex AI the ability to:
  • Take screenshots
  • Move mouse / click / type / press keys
  • Play games autonomously via a vision-driven loop

Architecture:
  user browser ──► http://127.0.0.1:7862 (this app)
                       │
                       ├── /screen.jpg          → live screenshot
                       ├── POST /control/click  → manual control
                       ├── POST /control/type
                       ├── POST /control/key
                       ├── POST /game/start     → start autonomous loop
                       ├── POST /game/stop      → abort
                       ├── GET  /game/status    → live status + thoughts
                       └── /                    → control-panel UI

The autonomous "game mode" loop:
  1. Take a screenshot
  2. Send to Claude Sonnet 4.5 (vision) with the game-goal + prior actions
  3. Parse JSON action: {action, x, y, text, key, reasoning, done}
  4. Execute action via pyautogui
  5. Sleep N seconds, repeat (until done=true OR user clicks Stop)

Identity: This is Zenrex, created from scratch by Zuhair Abbas.
Run: python zenrex_pc_control.py  (or via the desktop shortcut)
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import platform
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Hide console window on Windows
try:
    if os.name == "nt":
        import ctypes
        _hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if _hwnd:
            ctypes.windll.user32.ShowWindow(_hwnd, 0)
except Exception:
    pass

import pyautogui
import mss
from PIL import Image
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
import uvicorn

# ─── Config ──────────────────────────────────────────────────────────────────
APP_NAME = "Zenrex PC Control"
APP_VERSION = "0.1.0"
PORT = 7862

# Emergent LLM key — baked in at install time via env var.
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "").strip()

pyautogui.FAILSAFE = True   # mouse to top-left aborts
pyautogui.PAUSE = 0.05

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("zenrex-control")

app = FastAPI(title=APP_NAME, version=APP_VERSION)


# ─── Game-mode state ─────────────────────────────────────────────────────────
class GameState:
    """Holds the running game-loop state. One game at a time."""
    def __init__(self) -> None:
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.game_name = ""
        self.goal = ""
        self.iteration = 0
        self.max_iterations = 200
        self.history: List[Dict[str, Any]] = []  # last actions + thoughts
        self.last_thought = ""
        self.last_action: Dict[str, Any] = {}
        self.error: Optional[str] = None
        self.started_at: Optional[float] = None
        self.delay_seconds = 3.0  # between iterations

    def reset(self) -> None:
        self.running = False
        self.task = None
        self.iteration = 0
        self.history = []
        self.last_thought = ""
        self.last_action = {}
        self.error = None
        self.started_at = None


GAME = GameState()


# ─── Screen capture ──────────────────────────────────────────────────────────
def take_screenshot(max_width: int = 1280, quality: int = 60) -> tuple[bytes, int, int]:
    """Return JPEG bytes + (full_width, full_height)."""
    with mss.mss() as sct:
        mon = sct.monitors[1]
        sct_img = sct.grab(mon)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        full_w, full_h = mon["width"], mon["height"]
        if img.width > max_width:
            r = max_width / img.width
            img = img.resize((max_width, int(img.height * r)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue(), full_w, full_h


@app.get("/screen.jpg")
def screen_jpg():
    img_bytes, _, _ = take_screenshot()
    return Response(img_bytes, media_type="image/jpeg",
                    headers={"Cache-Control": "no-store"})


@app.get("/screen-size")
def screen_size():
    w, h = pyautogui.size()
    return {"width": int(w), "height": int(h)}


# ─── Manual control endpoints ────────────────────────────────────────────────
@app.post("/control/click")
async def control_click(request: Request):
    body = await request.json()
    x = body.get("x")
    y = body.get("y")
    button = body.get("button", "left")
    clicks = int(body.get("clicks", 1))
    duration = float(body.get("duration", 0.3))
    if x is not None and y is not None:
        pyautogui.moveTo(int(x), int(y), duration=duration,
                         tween=pyautogui.easeInOutQuad)
        time.sleep(0.05)
        pyautogui.click(int(x), int(y), clicks=clicks, button=button)
    else:
        pyautogui.click(clicks=clicks, button=button)
    return {"ok": True}


@app.post("/control/move")
async def control_move(request: Request):
    body = await request.json()
    pyautogui.moveTo(int(body.get("x", 0)), int(body.get("y", 0)),
                     duration=float(body.get("duration", 0.3)),
                     tween=pyautogui.easeInOutQuad)
    return {"ok": True}


@app.post("/control/type")
async def control_type(request: Request):
    body = await request.json()
    text = body.get("text", "")
    interval = float(body.get("interval", 0.03))
    is_ascii = all(ord(c) < 128 for c in text)
    if is_ascii:
        pyautogui.typewrite(text, interval=interval)
    else:
        # Unicode (e.g. Arabic) → clipboard paste
        try:
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return {"ok": True, "chars": len(text)}


@app.post("/control/key")
async def control_key(request: Request):
    body = await request.json()
    key = body.get("key", "").strip()
    if not key:
        raise HTTPException(400, "key required")
    parts = [p.strip() for p in key.split("+") if p.strip()]
    if len(parts) == 1:
        pyautogui.press(parts[0])
    else:
        pyautogui.hotkey(*parts)
    return {"ok": True, "key": key}


@app.post("/control/scroll")
async def control_scroll(request: Request):
    body = await request.json()
    pyautogui.scroll(int(body.get("amount", -3)))
    return {"ok": True}


@app.post("/control/hotkey")
async def control_hotkey(request: Request):
    body = await request.json()
    keys = body.get("keys", [])
    if not keys:
        raise HTTPException(400, "keys required")
    pyautogui.hotkey(*[str(k).lower() for k in keys])
    return {"ok": True}


# ─── Game-mode: vision-driven autonomous loop ────────────────────────────────
GAME_SYSTEM_PROMPT = """You are Zenrex — an autonomous PC-control AI created from scratch by Zuhair Abbas.
You are playing the game "{game_name}". Your goal: {goal}

You receive a screenshot of the current screen.
You must reply with STRICT JSON ONLY (no markdown, no prose) describing the NEXT single action:

{{
  "thought": "short reasoning about what you see and why you chose this action (in the user's language)",
  "action": "click" | "double_click" | "right_click" | "type" | "key" | "hotkey" | "scroll" | "wait" | "done",
  "x": int (required for click actions, in screen pixels at the encoded resolution given),
  "y": int (required for click actions),
  "text": "string" (required for action=type),
  "key": "string" (required for action=key, e.g. 'enter', 'esc', 'tab'),
  "keys": ["ctrl","c"] (required for action=hotkey),
  "amount": int (for scroll: negative = down, positive = up),
  "wait_seconds": float (for action=wait, default 2),
  "done": false (set true ONLY if the goal is fully accomplished)
}}

Rules:
- The screenshot coordinates are at the encoded resolution {enc_w}x{enc_h}. The actual screen is {real_w}x{real_h}. You may emit either; the runtime will scale.
- Be conservative. Prefer slow, deliberate actions.
- If the game / page is still loading, return action=wait with wait_seconds=2-4.
- If you are uncertain or stuck, return action=wait (do not click randomly).
- NEVER click outside the visible window. NEVER take destructive actions like closing the browser.
- If you see the goal is accomplished, set "done": true.

Previous actions taken so far (most-recent last):
{history}"""


async def _claude_decide(game: GameState, jpg_bytes: bytes,
                         enc_w: int, enc_h: int,
                         real_w: int, real_h: int) -> Dict[str, Any]:
    """Send screenshot to Claude Sonnet 4.5 via Emergent LLM and parse JSON."""
    if not EMERGENT_LLM_KEY:
        return {"action": "error",
                "error": "EMERGENT_LLM_KEY missing — pass it via env to enable game mode."}
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    except Exception as e:
        return {"action": "error",
                "error": f"emergentintegrations not installed: {e}"}

    history_brief = []
    for h in game.history[-6:]:
        history_brief.append({
            "i": h.get("iteration"),
            "action": h.get("action", {}).get("action"),
            "x": h.get("action", {}).get("x"),
            "y": h.get("action", {}).get("y"),
            "thought": (h.get("action", {}).get("thought", "") or "")[:120],
        })
    history_txt = json.dumps(history_brief, ensure_ascii=False, indent=2)

    sys_msg = GAME_SYSTEM_PROMPT.format(
        game_name=game.game_name, goal=game.goal,
        enc_w=enc_w, enc_h=enc_h, real_w=real_w, real_h=real_h,
        history=history_txt,
    )

    chat = (
        LlmChat(api_key=EMERGENT_LLM_KEY,
                session_id=f"zenrex-game-{int(game.started_at or time.time())}",
                system_message=sys_msg)
        .with_model("anthropic", "claude-sonnet-4-5-20250929")
    )
    b64 = base64.b64encode(jpg_bytes).decode("ascii")
    msg = UserMessage(
        text=(f"Iteration {game.iteration}/{game.max_iterations}. "
              f"Reply with strict JSON describing the next single action."),
        file_contents=[ImageContent(image_base64=b64)],
    )
    try:
        raw = await chat.send_message(msg)
    except Exception as e:
        return {"action": "error", "error": f"LLM call failed: {e}"}

    text = raw if isinstance(raw, str) else getattr(raw, "content", str(raw))
    text = text.strip().strip("`")
    if text.lower().startswith("json"):
        text = text[4:].strip()
    si, ei = text.find("{"), text.rfind("}")
    if si < 0 or ei <= si:
        return {"action": "error", "error": f"non-JSON LLM reply: {text[:200]}"}
    try:
        data = json.loads(text[si:ei + 1])
        # Scale coordinates if they appear to be at the encoded resolution
        if "x" in data and "y" in data and isinstance(data.get("x"), (int, float)):
            if enc_w and real_w and enc_w != real_w:
                data["x"] = int(round(float(data["x"]) * real_w / enc_w))
                data["y"] = int(round(float(data["y"]) * real_h / enc_h))
        return data
    except Exception as e:
        return {"action": "error", "error": f"JSON parse failed: {e}"}


async def _execute_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single decided action via pyautogui."""
    a = (action.get("action") or "").lower()
    try:
        if a == "click":
            x, y = int(action["x"]), int(action["y"])
            pyautogui.moveTo(x, y, duration=0.35, tween=pyautogui.easeInOutQuad)
            time.sleep(0.1)
            pyautogui.click(x, y)
        elif a == "double_click":
            x, y = int(action["x"]), int(action["y"])
            pyautogui.moveTo(x, y, duration=0.35, tween=pyautogui.easeInOutQuad)
            time.sleep(0.1)
            pyautogui.doubleClick(x, y)
        elif a == "right_click":
            x, y = int(action["x"]), int(action["y"])
            pyautogui.moveTo(x, y, duration=0.35, tween=pyautogui.easeInOutQuad)
            time.sleep(0.1)
            pyautogui.rightClick(x, y)
        elif a == "type":
            text = str(action.get("text", ""))
            if all(ord(c) < 128 for c in text):
                pyautogui.typewrite(text, interval=0.03)
            else:
                try:
                    import pyperclip
                    pyperclip.copy(text)
                    pyautogui.hotkey("ctrl", "v")
                except Exception as e:
                    return {"ok": False, "error": str(e)}
        elif a == "key":
            pyautogui.press(str(action.get("key", "")).strip())
        elif a == "hotkey":
            keys = [str(k).lower() for k in action.get("keys", [])]
            if keys:
                pyautogui.hotkey(*keys)
        elif a == "scroll":
            pyautogui.scroll(int(action.get("amount", -3)))
        elif a == "wait":
            await asyncio.sleep(float(action.get("wait_seconds", 2)))
        elif a == "done":
            return {"ok": True, "done": True}
        elif a == "error":
            return {"ok": False, "error": action.get("error", "unknown")}
        else:
            return {"ok": False, "error": f"unknown action: {a}"}
        return {"ok": True}
    except pyautogui.FailSafeException:
        return {"ok": False, "error": "failsafe_triggered (mouse hit top-left)"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


async def _game_loop(game: GameState) -> None:
    """The autonomous game-playing loop. Runs as an asyncio task."""
    log.info(f"[game] loop start: {game.game_name} — goal: {game.goal}")
    while game.running and game.iteration < game.max_iterations:
        game.iteration += 1
        try:
            jpg, real_w, real_h = take_screenshot(max_width=1280, quality=55)
            # encoded size — match what take_screenshot did
            enc_img = Image.open(io.BytesIO(jpg))
            enc_w, enc_h = enc_img.size
            action = await _claude_decide(game, jpg, enc_w, enc_h, real_w, real_h)
        except Exception as e:
            game.error = f"decide error: {e}"
            log.exception("[game] decide failed")
            break

        game.last_action = action
        game.last_thought = action.get("thought", "") or ""
        log.info(f"[game] #{game.iteration} → {action.get('action')} "
                 f"x={action.get('x')} y={action.get('y')} "
                 f"thought={game.last_thought[:80]}")

        if action.get("done"):
            game.history.append({
                "iteration": game.iteration,
                "action": action,
                "result": {"ok": True, "done": True},
                "ts": time.time(),
            })
            break

        result = await _execute_action(action)
        game.history.append({
            "iteration": game.iteration,
            "action": action,
            "result": result,
            "ts": time.time(),
        })

        if not result.get("ok"):
            game.error = result.get("error")
            log.warning(f"[game] action failed: {result.get('error')}")
            # Don't break — let the LLM see the result on next iteration
        if result.get("done"):
            break

        await asyncio.sleep(game.delay_seconds)

    game.running = False
    log.info(f"[game] loop done after {game.iteration} iterations "
             f"(error={game.error})")


@app.post("/game/start")
async def game_start(request: Request):
    body = await request.json()
    if GAME.running:
        return JSONResponse({"ok": False, "error": "already_running"}, status_code=409)
    GAME.reset()
    GAME.game_name = (body.get("game_name") or "Unknown Game").strip()[:120]
    GAME.goal = (body.get("goal") or "explore and learn").strip()[:600]
    GAME.max_iterations = max(1, min(500, int(body.get("max_iterations", 100))))
    GAME.delay_seconds = max(0.5, min(15.0, float(body.get("delay_seconds", 3.0))))
    GAME.started_at = time.time()
    GAME.running = True
    GAME.task = asyncio.create_task(_game_loop(GAME))
    return {"ok": True, "game_name": GAME.game_name, "goal": GAME.goal,
            "max_iterations": GAME.max_iterations,
            "delay_seconds": GAME.delay_seconds}


@app.post("/game/stop")
async def game_stop():
    if not GAME.running:
        return {"ok": True, "was_running": False}
    GAME.running = False
    if GAME.task:
        await asyncio.sleep(0.1)
    return {"ok": True, "was_running": True, "iterations": GAME.iteration}


@app.get("/game/status")
async def game_status():
    return {
        "ok": True,
        "running": GAME.running,
        "game_name": GAME.game_name,
        "goal": GAME.goal,
        "iteration": GAME.iteration,
        "max_iterations": GAME.max_iterations,
        "delay_seconds": GAME.delay_seconds,
        "last_thought": GAME.last_thought,
        "last_action": GAME.last_action,
        "error": GAME.error,
        "started_at": GAME.started_at,
        "history_size": len(GAME.history),
        "history": GAME.history[-10:],   # last 10
    }


# ─── Health / identity ───────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "ok": True,
        "app": APP_NAME,
        "version": APP_VERSION,
        "identity": "Zenrex — created from scratch by Zuhair Abbas",
        "platform": platform.system(),
        "release": platform.release(),
        "user": os.environ.get("USERNAME") or os.environ.get("USER") or "?",
        "screen": list(pyautogui.size()),
        "emergent_key_present": bool(EMERGENT_LLM_KEY),
    }


# ─── Control-panel UI ────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(_INDEX_HTML)


_INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl"><head>
<meta charset="utf-8"/>
<title>Zenrex — التحكم بالجهاز ووضع الألعاب</title>
<style>
  :root{ --bg:#0a0a14; --panel:#15151f; --line:#2a2a36; --text:#e5e7eb;
         --muted:#9ca3af; --accent:#a78bfa; --green:#10b981; --red:#ef4444;
         --amber:#f59e0b; }
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);min-height:100vh;
       font-family:'Segoe UI',Tahoma,Arial,sans-serif;font-size:14px}
  header{padding:14px 22px;background:var(--panel);border-bottom:1px solid var(--line);
         display:flex;justify-content:space-between;align-items:center;gap:12px}
  h1{font-size:16px;color:var(--accent);font-weight:600}
  .badge{font-size:11px;padding:3px 8px;border-radius:6px;background:#222;color:var(--muted)}
  .badge.live{background:#064e3b;color:#10b981}
  .grid{display:grid;grid-template-columns:1.4fr 1fr;gap:18px;padding:18px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
  .card h2{font-size:13px;color:var(--accent);font-weight:600;margin-bottom:12px;
           text-transform:uppercase;letter-spacing:0.06em}
  .screen-wrap{background:#000;border-radius:10px;overflow:hidden;
               aspect-ratio:16/9;display:flex;align-items:center;justify-content:center;
               position:relative;cursor:crosshair}
  .screen-wrap img{width:100%;height:100%;object-fit:contain;display:block;
                    user-select:none;-webkit-user-drag:none}
  .screen-wrap .crosshair{position:absolute;width:18px;height:18px;border:2px solid var(--accent);
                          border-radius:50%;pointer-events:none;
                          box-shadow:0 0 8px rgba(167,139,250,0.6);display:none}
  label{display:block;margin-top:10px;color:var(--muted);font-size:12px}
  input,textarea,select{width:100%;background:#0a0a14;border:1px solid var(--line);
                        color:var(--text);padding:9px 11px;border-radius:8px;
                        font-family:inherit;font-size:13px;margin-top:4px}
  textarea{resize:vertical;min-height:60px}
  button{cursor:pointer;background:var(--accent);color:#0a0a14;border:none;
         padding:10px 14px;border-radius:8px;font-weight:600;font-size:13px;
         transition:filter .15s;margin-top:10px}
  button:hover{filter:brightness(1.1)}
  button.secondary{background:#222;color:var(--text);border:1px solid var(--line)}
  button.danger{background:var(--red);color:#fff}
  button.success{background:var(--green);color:#0a0a14}
  .row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
  .row > *{flex:1;min-width:80px}
  .status-line{display:flex;align-items:center;gap:8px;padding:8px 10px;
               background:#0a0a14;border:1px solid var(--line);border-radius:8px;
               font-size:12px;color:var(--muted);margin-top:10px}
  .dot{width:8px;height:8px;border-radius:50%;background:#444}
  .dot.run{background:var(--green);box-shadow:0 0 8px var(--green);
            animation:pulse 1.2s ease-in-out infinite}
  .dot.err{background:var(--red)}
  @keyframes pulse{50%{opacity:.45}}
  .thought{background:#0a0a14;border:1px solid var(--line);border-radius:8px;
           padding:10px 12px;font-size:13px;color:var(--text);
           min-height:54px;max-height:140px;overflow-y:auto;margin-top:10px;
           white-space:pre-wrap;line-height:1.5}
  .history{margin-top:10px;font-family:'Consolas',monospace;font-size:11px;
           color:var(--muted);max-height:200px;overflow-y:auto;
           background:#0a0a14;border:1px solid var(--line);border-radius:8px;padding:8px}
  .history .row-item{padding:4px 0;border-bottom:1px solid #1a1a26}
  .history .row-item:last-child{border-bottom:none}
  .history .a{color:var(--accent)}
  .games{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:8px}
  .games button{padding:14px 8px;text-align:center;background:#1a1a26;
                color:var(--text);border:1px solid var(--line);font-size:12px}
  .games button:hover{border-color:var(--accent);color:var(--accent)}
  .small{font-size:11px;color:var(--muted)}
  @media(max-width:880px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
  <div style="display:flex;align-items:center;gap:10px">
    <h1>⚡ Zenrex — تحكم بالجهاز</h1>
    <span class="badge" id="ver">v0.1.0</span>
    <span class="badge" id="ident">Zuhair Abbas</span>
  </div>
  <div style="display:flex;align-items:center;gap:10px">
    <span class="dot" id="game-dot"></span>
    <span class="small" id="game-state">جاهز</span>
  </div>
</header>

<div class="grid">
  <!-- ── LEFT: Live screen + manual control ────────────────── -->
  <div>
    <div class="card">
      <h2>الشاشة الحية (انقر على الصورة للتحكم بالمؤشر)</h2>
      <div class="screen-wrap" id="screen-wrap">
        <img id="screen" alt="screen"/>
        <div class="crosshair" id="cross"></div>
      </div>
      <div class="row">
        <button class="secondary" id="refresh-btn">↻ تحديث الصورة</button>
        <button class="secondary" id="autorefresh-btn">⏱ تحديث تلقائي</button>
        <span class="status-line" id="screen-info">—</span>
      </div>
    </div>

    <div class="card" style="margin-top:18px">
      <h2>تحكم يدوي</h2>
      <label>اكتب نصّاً</label>
      <input id="type-text" placeholder="مثال: hello world"/>
      <div class="row">
        <button id="type-btn">⌨ اكتب</button>
      </div>

      <label>اضغط مفتاحاً (مثال: enter, esc, ctrl+c, alt+tab)</label>
      <input id="key-text" placeholder="enter"/>
      <div class="row">
        <button id="key-btn">⏎ اضغط</button>
        <button class="secondary" data-key="enter">Enter</button>
        <button class="secondary" data-key="escape">Esc</button>
        <button class="secondary" data-key="tab">Tab</button>
        <button class="secondary" data-key="space">Space</button>
        <button class="secondary" data-key="ctrl+c">Ctrl+C</button>
        <button class="secondary" data-key="ctrl+v">Ctrl+V</button>
        <button class="secondary" data-key="alt+tab">Alt+Tab</button>
      </div>
    </div>
  </div>

  <!-- ── RIGHT: Game Mode (autonomous) ─────────────────────── -->
  <div>
    <div class="card">
      <h2>🎮 وضع اللعب الذاتي</h2>

      <label>اختر لعبة سريعة</label>
      <div class="games">
        <button data-name="Travian" data-goal="ادخل لعبة Travian من المتصفح، سجّل دخول إذا لزم، ثم استكشف القرية، ابنِ مبنىً، واحصد المحاصيل.">Travian</button>
        <button data-name="Browser Game" data-goal="استكشف اللعبة المعروضة في المتصفح، اقرأ القوائم، واتخذ خطوات منطقية للتقدم.">لعبة متصفح</button>
        <button data-name="Custom" data-goal="">يدوي</button>
      </div>

      <label>اسم اللعبة</label>
      <input id="game-name" placeholder="Travian"/>

      <label>الهدف (بلغتك — كلما كان واضحاً كان أفضل)</label>
      <textarea id="game-goal" placeholder="مثال: افتح لعبة Travian في المتصفح، استكشف القرية، وابنِ أول مبنى."></textarea>

      <div class="row">
        <div>
          <label>أقصى عدد محاولات</label>
          <input id="game-max" type="number" value="100" min="1" max="500"/>
        </div>
        <div>
          <label>التأخير بين كل خطوة (ث)</label>
          <input id="game-delay" type="number" value="3" min="0.5" max="15" step="0.5"/>
        </div>
      </div>

      <div class="row">
        <button class="success" id="game-start">▶ ابدأ اللعب</button>
        <button class="danger" id="game-stop">■ إيقاف</button>
      </div>

      <div class="status-line">
        <span class="dot" id="loop-dot"></span>
        <span id="loop-status">في انتظار البدء</span>
        <span style="margin-inline-start:auto" class="small" id="loop-iter">—</span>
      </div>

      <label style="margin-top:14px">🧠 آخر تفكير لـ Zenrex</label>
      <div class="thought" id="thought">—</div>

      <label>سجل الخطوات</label>
      <div class="history" id="history"><div class="small">لم يبدأ بعد.</div></div>

      <p class="small" style="margin-top:10px">
        💡 نصيحة: حرّك الفأرة إلى أعلى-يسار الشاشة كزر طوارئ (FailSafe).
      </p>
    </div>
  </div>
</div>

<script>
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

// ── Screen live refresh ───────────────────────────────────
let autoRefresh = false;
let realW = 1920, realH = 1080;
async function refreshScreen(){
  const t = Date.now();
  $('#screen').src = `/screen.jpg?t=${t}`;
  try{
    const r = await fetch('/screen-size'); const d = await r.json();
    realW = d.width; realH = d.height;
    $('#screen-info').textContent = `الشاشة الحقيقية: ${realW}×${realH}`;
  }catch(e){}
}
refreshScreen();
$('#refresh-btn').onclick = refreshScreen;
$('#autorefresh-btn').onclick = () => {
  autoRefresh = !autoRefresh;
  $('#autorefresh-btn').textContent = autoRefresh ? '⏸ إيقاف التحديث' : '⏱ تحديث تلقائي';
  if (autoRefresh) loopAuto();
};
async function loopAuto(){
  while (autoRefresh){
    await refreshScreen();
    await new Promise(r=>setTimeout(r,1500));
  }
}

// ── Click on screen image to control mouse ─────────────────
const img = $('#screen');
const wrap = $('#screen-wrap');
const cross = $('#cross');
img.addEventListener('mousemove', e => {
  const rect = img.getBoundingClientRect();
  const px = e.clientX - rect.left, py = e.clientY - rect.top;
  cross.style.display = 'block';
  cross.style.left = (px - 9) + 'px';
  cross.style.top = (py - 9) + 'px';
});
img.addEventListener('mouseleave', () => cross.style.display='none');
img.addEventListener('click', async e => {
  const rect = img.getBoundingClientRect();
  const x = Math.round((e.clientX - rect.left) / rect.width * realW);
  const y = Math.round((e.clientY - rect.top) / rect.height * realH);
  await fetch('/control/click', { method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({x, y}) });
  setTimeout(refreshScreen, 250);
});

// ── Manual control ────────────────────────────────────────
$('#type-btn').onclick = async () => {
  const text = $('#type-text').value;
  if (!text) return;
  await fetch('/control/type', { method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify({text}) });
  $('#type-text').value = '';
  setTimeout(refreshScreen, 250);
};
$('#key-btn').onclick = async () => {
  const key = $('#key-text').value.trim();
  if (!key) return;
  await fetch('/control/key', { method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify({key}) });
  setTimeout(refreshScreen, 250);
};
$$('button[data-key]').forEach(b => b.onclick = async () => {
  await fetch('/control/key', { method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({key: b.dataset.key}) });
  setTimeout(refreshScreen, 250);
});

// ── Game-mode shortcuts ────────────────────────────────────
$$('.games button').forEach(b => b.onclick = () => {
  $('#game-name').value = b.dataset.name;
  $('#game-goal').value = b.dataset.goal;
});

// ── Game-mode start/stop ───────────────────────────────────
$('#game-start').onclick = async () => {
  const r = await fetch('/game/start', { method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      game_name: $('#game-name').value || 'Custom',
      goal: $('#game-goal').value || 'explore',
      max_iterations: parseInt($('#game-max').value || '100'),
      delay_seconds: parseFloat($('#game-delay').value || '3')
    })
  });
  const d = await r.json();
  if (!d.ok){ alert(d.error || 'فشل البدء'); return; }
  if (!autoRefresh){ autoRefresh = true; $('#autorefresh-btn').textContent='⏸ إيقاف التحديث'; loopAuto(); }
};
$('#game-stop').onclick = async () => {
  await fetch('/game/stop', { method:'POST' });
};

// ── Poll game status ───────────────────────────────────────
async function pollStatus(){
  try{
    const r = await fetch('/game/status'); const d = await r.json();
    const dot = $('#loop-dot'), state = $('#loop-status'), iter = $('#loop-iter');
    const gameDot = $('#game-dot'), gameState = $('#game-state');
    if (d.running){
      dot.className = 'dot run'; gameDot.className = 'dot run';
      state.textContent = `يلعب: ${d.game_name}`;
      gameState.textContent = `يلعب • ${d.game_name}`;
      iter.textContent = `${d.iteration}/${d.max_iterations}`;
    } else if (d.error){
      dot.className = 'dot err'; gameDot.className = 'dot err';
      state.textContent = `خطأ: ${d.error}`;
      gameState.textContent = 'متوقف';
      iter.textContent = `${d.iteration} خطوة`;
    } else {
      dot.className = 'dot'; gameDot.className = 'dot';
      state.textContent = d.iteration > 0 ? `انتهى بعد ${d.iteration} خطوة` : 'في انتظار البدء';
      gameState.textContent = 'جاهز';
      iter.textContent = d.iteration > 0 ? `${d.iteration} خطوة` : '—';
    }
    $('#thought').textContent = d.last_thought || '—';
    if (d.history && d.history.length){
      $('#history').innerHTML = d.history.slice().reverse().map(h => {
        const a = h.action || {};
        const x = a.x !== undefined ? ` (${a.x},${a.y})` : '';
        const ok = h.result && h.result.ok ? '✓' : '✗';
        return `<div class="row-item"><span class="a">#${h.iteration} ${ok} ${a.action||'?'}${x}</span> — ${(a.thought||'').slice(0,80)}</div>`;
      }).join('');
    }
  }catch(e){}
  setTimeout(pollStatus, 1200);
}
pollStatus();

// Identity / version
(async () => {
  try{
    const r = await fetch('/health'); const d = await r.json();
    $('#ver').textContent = 'v' + d.version;
    if (!d.emergent_key_present){
      $('#ident').textContent = '⚠ بدون مفتاح ذكاء';
      $('#ident').style.background = '#7c2d12';
      $('#ident').style.color = '#fed7aa';
    }
  }catch(e){}
})();
</script>
</body></html>
"""


# ─── Entry point ─────────────────────────────────────────────────────────────
def main() -> None:
    log.info(f"{APP_NAME} v{APP_VERSION} starting on http://127.0.0.1:{PORT}")
    log.info(f"Emergent LLM key present: {bool(EMERGENT_LLM_KEY)}")
    # Auto-open browser to the control panel
    if "--no-browser" not in sys.argv:
        threading.Thread(target=_open_browser_delayed, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


def _open_browser_delayed() -> None:
    time.sleep(1.5)
    try:
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{PORT}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
