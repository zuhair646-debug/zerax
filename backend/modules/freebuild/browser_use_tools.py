"""
Zenrex AI Brain — Browser Use Tools (Phase 5).

Gives the AI direct, supervised control over a real web browser to log into
the user's accounts and perform actions on their behalf. Uses Playwright +
Claude Vision in a perceive→decide→act loop.

Architecture:
  • Each session is an isolated Playwright BrowserContext.
  • Sessions live in-memory keyed by session_id, auto-expiring after 30 min idle.
  • Storage state (cookies + localStorage) can be persisted encrypted per-project
    so the user logs in ONCE and the AI reuses the session forever after.
  • `browser_act(session_id, instruction)` runs a vision-guided autonomous loop:
    screenshot → Claude vision → JSON {action, selector|text|url} → execute → repeat.

Safety:
  • All actions are project-scoped.
  • Max 8 vision steps per act() call.
  • Sessions auto-close on idle.
  • Storage states are Fernet-encrypted at rest.
  • The user sees every screenshot + decision in the chat UI.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("zenrex.browser_use_tools")

# Module-level session registry. Each entry: {
#   'playwright', 'browser', 'context', 'page', 'project_id',
#   'created_at', 'last_used'
# }
_SESSIONS: Dict[str, Dict[str, Any]] = {}
_SESSION_TTL_SECONDS = 30 * 60  # 30 minutes idle
_MAX_VISION_STEPS = 8


PHASE5_TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "browser_start",
        "description": (
            "🌐 Open a new real browser session (Playwright Chromium). Optionally "
            "auto-load a previously-saved login state for `account_label` so the "
            "session is ALREADY signed-in. Returns a session_id you pass to "
            "subsequent browser_* tools. Use this whenever the user wants you to "
            "do something on their behalf inside a third-party site they own "
            "(Gmail, Twitter, Stripe Dashboard, ...). 30-minute idle timeout."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "account_label": {"type": "string",
                                   "description": "Optional snake_case label of a saved session to load (e.g. 'gmail_main', 'twitter_business')."},
                "headless": {"type": "boolean", "default": True},
            },
            "required": [],
        },
    },
    {
        "name": "browser_goto",
        "description": (
            "↗️ Navigate the browser session to a URL. Waits for DOM ready. "
            "Returns a screenshot + page title + final URL."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "url": {"type": "string"},
                "wait_seconds": {"type": "integer", "default": 2, "minimum": 0, "maximum": 15},
            },
            "required": ["session_id", "url"],
        },
    },
    {
        "name": "browser_act",
        "description": (
            "🧠 AUTONOMOUS browser action loop. Takes a high-level instruction in "
            "Arabic or English ('سجّل دخولي بحسابي X و Y', 'افتح أحدث رسالة وارد عليها بنعم', "
            "'go to Stripe payouts and tell me my balance'). The AI takes a "
            "screenshot, decides the next click/type/scroll via vision, executes, "
            "and repeats up to 8 steps. Returns every step + the final outcome + "
            "final screenshot. **WARNING**: this can perform real actions on real "
            "accounts. Make sure the user explicitly asked for this."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "instruction": {"type": "string", "description": "What you want the browser to accomplish."},
                "max_steps": {"type": "integer", "default": 6, "minimum": 1, "maximum": 8},
            },
            "required": ["session_id", "instruction"],
        },
    },
    {
        "name": "browser_screenshot",
        "description": "📸 Take a screenshot of the current browser page. Returns base64 JPEG.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "full_page": {"type": "boolean", "default": False},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "browser_save_session",
        "description": (
            "💾 Save the current logged-in state (cookies + localStorage) ENCRYPTED. "
            "Next time the user wants to use this account, just call `browser_start` "
            "with the same account_label and they're already signed in. Call this "
            "AFTER you've helped the user sign in once."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "account_label": {"type": "string", "description": "snake_case label, e.g. 'gmail_main'."},
            },
            "required": ["session_id", "account_label"],
        },
    },
    {
        "name": "browser_list_accounts",
        "description": "📋 List saved browser-session accounts for this project (labels + last used).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "browser_close",
        "description": "🛑 Close a browser session and free its resources.",
        "input_schema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    },
]


PHASE5_TOOL_LABELS_AR: Dict[str, Dict[str, str]] = {
    "browser_start":         {"running": "🌐 يفتح متصفح حقيقي...",
                               "done": "✅ المتصفح جاهز"},
    "browser_goto":          {"running": "↗️ يتصفّح للرابط...",
                               "done": "✅ تم التصفّح"},
    "browser_act":           {"running": "🧠 الذكاء يتحكم بالمتصفح (perceive→decide→act)...",
                               "done": "✅ المهمة في المتصفح اكتملت"},
    "browser_screenshot":    {"running": "📸 يلتقط الشاشة...",
                               "done": "✅ تم التقاط الصورة"},
    "browser_save_session":  {"running": "💾 يحفظ جلسة الدخول مشفّرة...",
                               "done": "✅ جلسة الدخول محفوظة"},
    "browser_list_accounts": {"running": "📋 يعرض الحسابات المحفوظة...",
                               "done": "✅ القائمة جاهزة"},
    "browser_close":         {"running": "🛑 يغلق المتصفح...",
                               "done": "✅ تم إغلاق الجلسة"},
}


PHASE5_TOOL_NAMES: tuple = tuple(t["name"] for t in PHASE5_TOOL_SCHEMAS)


# ─── Helpers ──────────────────────────────────────────────────────────────────
async def _cleanup_idle_sessions():
    """Background cleanup of idle browser sessions."""
    now = time.time()
    expired = [sid for sid, s in _SESSIONS.items()
               if now - s.get("last_used", 0) > _SESSION_TTL_SECONDS]
    for sid in expired:
        try:
            await _close_session(sid)
        except Exception:
            pass


async def _close_session(session_id: str):
    s = _SESSIONS.pop(session_id, None)
    if not s:
        return
    try:
        if s.get("context"):
            await s["context"].close()
        if s.get("browser"):
            await s["browser"].close()
        if s.get("playwright"):
            await s["playwright"].stop()
    except Exception:
        pass


def _get_session(session_id: str) -> Optional[Dict[str, Any]]:
    s = _SESSIONS.get(session_id)
    if s:
        s["last_used"] = time.time()
    return s


async def _save_storage_state_encrypted(db, project_id: str, account_label: str, storage_state: dict) -> bool:
    if db is None:
        return False
    try:
        from .freebuild_chat import _enc  # type: ignore
        blob = json.dumps(storage_state, separators=(",", ":"))
        await db.freebuild_browser_sessions.update_one(
            {"project_id": project_id, "account_label": account_label},
            {"$set": {
                "project_id": project_id,
                "account_label": account_label,
                "storage_enc": _enc(blob),
                "updated_at": time.time(),
            }, "$setOnInsert": {"created_at": time.time()}},
            upsert=True,
        )
        return True
    except Exception as e:
        logger.warning(f"save_storage_state failed: {e}")
        return False


async def _load_storage_state(db, project_id: str, account_label: str) -> Optional[dict]:
    if db is None:
        return None
    try:
        from .freebuild_chat import _dec  # type: ignore
        doc = await db.freebuild_browser_sessions.find_one(
            {"project_id": project_id, "account_label": account_label}
        )
        if not doc:
            return None
        blob = _dec(doc.get("storage_enc") or "")
        if not blob:
            return None
        return json.loads(blob)
    except Exception as e:
        logger.warning(f"load_storage_state failed: {e}")
        return None


async def _take_screenshot_b64(page, full_page: bool = False) -> str:
    try:
        b = await page.screenshot(type="jpeg", quality=55, full_page=full_page)
        return base64.b64encode(b).decode("ascii")
    except Exception as e:
        logger.warning(f"screenshot failed: {e}")
        return ""


# ─── Tool implementations ────────────────────────────────────────────────────
async def browser_start(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if not ctx.project_id:
        return {"ok": False, "error": "project_id required"}
    await _cleanup_idle_sessions()

    try:
        from playwright.async_api import async_playwright  # type: ignore
    except ImportError:
        return {"ok": False, "error": "playwright not installed"}

    label = (args.get("account_label") or "").strip().lower() or None
    headless = bool(args.get("headless", True))

    try:
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=headless, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])

        # Try to load saved storage state
        storage_state = None
        loaded_from_save = False
        if label:
            storage_state = await _load_storage_state(ctx.db, ctx.project_id, label)
            if storage_state:
                loaded_from_save = True

        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            storage_state=storage_state,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        )
        page = await context.new_page()

        session_id = "br_" + str(uuid.uuid4())[:12]
        now = time.time()
        _SESSIONS[session_id] = {
            "playwright": pw,
            "browser": browser,
            "context": context,
            "page": page,
            "project_id": ctx.project_id,
            "account_label": label,
            "created_at": now,
            "last_used": now,
        }
        return {
            "ok": True,
            "session_id": session_id,
            "account_label": label,
            "session_loaded_from_save": loaded_from_save,
            "message": (f"🌐 المتصفح جاهز (محمّل بجلسة '{label}' المحفوظة)."
                        if loaded_from_save else "🌐 متصفح جديد بدون تسجيل دخول مسبق."),
        }
    except Exception as e:
        return {"ok": False, "error": f"browser_start: {type(e).__name__}: {str(e)[:200]}"}


async def browser_goto(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    session = _get_session(args.get("session_id") or "")
    if not session:
        return {"ok": False, "error": "invalid or expired session_id"}
    if session["project_id"] != ctx.project_id:
        return {"ok": False, "error": "session does not belong to this project"}
    url = (args.get("url") or "").strip()
    if not url:
        return {"ok": False, "error": "url required"}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    wait = max(0, min(int(args.get("wait_seconds") or 2), 15))
    try:
        page = session["page"]
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        if wait:
            await page.wait_for_timeout(wait * 1000)
        b64 = await _take_screenshot_b64(page)
        return {
            "ok": True,
            "session_id": args["session_id"],
            "final_url": page.url,
            "title": await page.title(),
            "screenshot_b64": b64,
            "kind": "browser_step",
        }
    except Exception as e:
        return {"ok": False, "error": f"browser_goto: {type(e).__name__}: {str(e)[:200]}"}


async def browser_screenshot(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    session = _get_session(args.get("session_id") or "")
    if not session:
        return {"ok": False, "error": "invalid session_id"}
    if session["project_id"] != ctx.project_id:
        return {"ok": False, "error": "session not in this project"}
    try:
        b64 = await _take_screenshot_b64(session["page"], full_page=bool(args.get("full_page")))
        return {"ok": True, "session_id": args["session_id"], "screenshot_b64": b64,
                "url": session["page"].url, "kind": "browser_step"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def browser_save_session(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    session = _get_session(args.get("session_id") or "")
    if not session:
        return {"ok": False, "error": "invalid session_id"}
    if session["project_id"] != ctx.project_id:
        return {"ok": False, "error": "session not in this project"}
    label = (args.get("account_label") or "").strip().lower()
    if not label:
        return {"ok": False, "error": "account_label required"}
    try:
        state = await session["context"].storage_state()
        ok = await _save_storage_state_encrypted(ctx.db, ctx.project_id, label, state)
        if not ok:
            return {"ok": False, "error": "could not persist storage state"}
        n_cookies = len(state.get("cookies", []))
        return {"ok": True, "account_label": label, "cookies_saved": n_cookies,
                "message": f"💾 جلسة '{label}' محفوظة مع {n_cookies} كوكيز. مرة الجاية حنرجع لها فوراً."}
    except Exception as e:
        return {"ok": False, "error": f"browser_save_session: {type(e).__name__}: {str(e)[:200]}"}


async def browser_list_accounts(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if ctx.db is None:
        return {"ok": False, "error": "DB missing"}
    try:
        cur = ctx.db.freebuild_browser_sessions.find(
            {"project_id": ctx.project_id},
            {"_id": 0, "account_label": 1, "updated_at": 1, "created_at": 1},
        )
        docs = await cur.to_list(length=50)
        return {"ok": True, "count": len(docs), "accounts": docs}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def browser_close(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    sid = args.get("session_id") or ""
    if sid not in _SESSIONS:
        return {"ok": False, "error": "invalid session_id"}
    if _SESSIONS[sid]["project_id"] != ctx.project_id:
        return {"ok": False, "error": "session not in this project"}
    await _close_session(sid)
    return {"ok": True, "session_id": sid, "message": "🛑 تم إغلاق المتصفح."}


# ─── Vision-guided autonomous loop (browser_act) ──────────────────────────────
_BROWSER_ACT_SYSTEM_PROMPT = """You are controlling a web browser on the user's behalf.

At each step you receive:
1. A screenshot of the current page.
2. The high-level instruction the user wants accomplished.
3. The page URL and title.
4. A short history of actions you've taken so far.

You must reply with ONLY a JSON object describing the NEXT atomic action:

{
  "action": "click" | "type" | "press" | "scroll" | "goto" | "wait" | "done" | "give_up",
  "selector": "<CSS selector OR visible text in quotes>",   // for click/type
  "text": "<text to type>",                                   // for type
  "key": "Enter|Tab|ArrowDown|...",                          // for press
  "url": "https://...",                                       // for goto
  "ms": 1000,                                                 // for wait
  "reason": "<one short Arabic sentence: why this action>"
}

RULES:
- ONE action per response. No prose outside the JSON.
- Prefer text-based selectors (text="Sign in") over fragile CSS classes.
- For click selectors, you can use Playwright text selectors like text="Submit" or role-based like getByRole.
- If a page asks for credentials and you don't have them, return action="give_up" with a clear reason so the user can supply them.
- When the goal is fully achieved, return action="done" with a summary in `reason`.
- NEVER perform destructive actions (delete account, send money) without explicit user confirmation. If the goal involves such actions, action="give_up" and explain.
"""


async def _vision_decide_next_action(instruction: str, screenshot_b64: str,
                                     page_url: str, page_title: str,
                                     history: List[str]) -> Dict[str, Any]:
    """Call Claude with vision to decide the next browser action."""
    api_key = (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY") or "").strip()
    if not api_key:
        return {"action": "give_up", "reason": "No Anthropic key available"}
    history_text = "\n".join(f"  - {h}" for h in history[-6:]) or "  (none)"
    user_text = (
        f"GOAL: {instruction}\n\n"
        f"CURRENT PAGE: {page_title} — {page_url}\n\n"
        f"ACTIONS SO FAR:\n{history_text}\n\n"
        "What's the next single action?"
    )
    body = {
        "model": "claude-sonnet-4-5-20250929",
        "max_tokens": 500,
        "system": _BROWSER_ACT_SYSTEM_PROMPT,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/jpeg",
                    "data": screenshot_b64[:4_000_000],
                }},
                {"type": "text", "text": user_text},
            ],
        }],
    }
    try:
        async with httpx.AsyncClient(timeout=45) as cl:
            r = await cl.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=body,
            )
        if r.status_code != 200:
            return {"action": "give_up", "reason": f"vision call HTTP {r.status_code}: {r.text[:120]}"}
        d = r.json()
        blocks = d.get("content") or []
        text = "\n".join(b.get("text") or "" for b in blocks if b.get("type") == "text").strip()
        # Extract JSON block
        jstart = text.find("{")
        jend = text.rfind("}")
        if jstart < 0 or jend < 0:
            return {"action": "give_up", "reason": f"vision did not return JSON: {text[:120]}"}
        parsed = json.loads(text[jstart:jend + 1])
        return parsed
    except Exception as e:
        return {"action": "give_up", "reason": f"vision error: {type(e).__name__}: {str(e)[:120]}"}


async def _execute_browser_action(page, action: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single decoded action on the Playwright page."""
    a = (action.get("action") or "").lower()
    try:
        if a == "click":
            sel = action.get("selector") or ""
            await page.locator(sel).first.click(timeout=8000)
            return {"ok": True}
        if a == "type":
            sel = action.get("selector") or ""
            text = action.get("text") or ""
            loc = page.locator(sel).first
            await loc.click(timeout=5000)
            await loc.fill(text, timeout=5000)
            return {"ok": True}
        if a == "press":
            await page.keyboard.press(action.get("key") or "Enter")
            return {"ok": True}
        if a == "scroll":
            await page.evaluate(f"window.scrollBy(0, {int(action.get('ms') or 400)})")
            return {"ok": True}
        if a == "goto":
            url = action.get("url") or ""
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            return {"ok": True}
        if a == "wait":
            await page.wait_for_timeout(int(action.get("ms") or 1000))
            return {"ok": True}
        if a in ("done", "give_up"):
            return {"ok": True, "terminal": True}
        return {"ok": False, "error": f"unknown action '{a}'"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def browser_act(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    session = _get_session(args.get("session_id") or "")
    if not session:
        return {"ok": False, "error": "invalid session_id"}
    if session["project_id"] != ctx.project_id:
        return {"ok": False, "error": "session not in this project"}
    instruction = (args.get("instruction") or "").strip()
    if not instruction:
        return {"ok": False, "error": "instruction required"}
    max_steps = max(1, min(int(args.get("max_steps") or 6), _MAX_VISION_STEPS))
    page = session["page"]

    history: List[str] = []
    steps: List[Dict[str, Any]] = []
    final_screenshot = ""
    final_status = "in_progress"

    for step_i in range(max_steps):
        # 1. Perceive
        screenshot = await _take_screenshot_b64(page)
        if not screenshot:
            steps.append({"step": step_i, "error": "screenshot failed"})
            break
        # 2. Decide
        decision = await _vision_decide_next_action(
            instruction, screenshot, page.url, await page.title(), history,
        )
        action_name = (decision.get("action") or "").lower()
        reason = decision.get("reason", "")
        history.append(f"{action_name}: {reason or decision.get('selector') or decision.get('url') or ''}")
        # 3. Act
        if action_name in ("done", "give_up"):
            steps.append({
                "step": step_i,
                "action": action_name,
                "reason": reason,
                "screenshot_b64": screenshot[:50],  # truncate for log; full is final
            })
            final_status = action_name
            final_screenshot = screenshot
            break
        exec_result = await _execute_browser_action(page, decision)
        # Tiny pause for DOM to settle
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass
        await page.wait_for_timeout(600)
        steps.append({
            "step": step_i,
            "action": action_name,
            "selector": decision.get("selector"),
            "text": (decision.get("text") or "")[:60],
            "url": decision.get("url"),
            "reason": reason,
            "executed_ok": exec_result.get("ok", False),
            "exec_error": exec_result.get("error"),
        })
        if not exec_result.get("ok"):
            # don't give up; let the next iteration's screenshot inform the vision model
            pass
        final_screenshot = screenshot

    # Capture a final screenshot
    final_screenshot = await _take_screenshot_b64(page)
    if final_status == "in_progress":
        final_status = "max_steps_reached"

    return {
        "ok": final_status == "done",
        "kind": "browser_act_report",
        "session_id": args["session_id"],
        "instruction": instruction,
        "status": final_status,
        "step_count": len(steps),
        "steps": steps,
        "final_url": page.url,
        "final_title": await page.title(),
        "final_screenshot_b64": final_screenshot,
        "message": (
            f"✅ المهمة في المتصفح اكتملت ({len(steps)} خطوات)." if final_status == "done"
            else f"⏸️ {final_status} — راجع الخطوات للتفاصيل."
        ),
    }


# ─── Master dispatcher ────────────────────────────────────────────────────────
async def dispatch_browser(ctx, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    fn_map = {
        "browser_start": browser_start,
        "browser_goto": browser_goto,
        "browser_act": browser_act,
        "browser_screenshot": browser_screenshot,
        "browser_save_session": browser_save_session,
        "browser_list_accounts": browser_list_accounts,
        "browser_close": browser_close,
    }
    fn = fn_map.get(name)
    if not fn:
        return {"ok": False, "error": f"unknown browser tool: {name}"}
    try:
        return await fn(ctx, args)
    except Exception as e:
        logger.exception(f"browser tool {name} failed")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
