"""Desktop Agent Tools — full native OS control on the OWNER's laptop.

These tools are gated to the platform owner (added to OWNER_ONLY_TOOL_NAMES in
freebuild_agent.py). The AI uses them to drive PyAutoGUI on a paired desktop
agent script the owner downloaded and is running.

Tools:
  • desktop_pair        → Generate a 6-char code + download URL.
  • desktop_status      → Is a desktop agent currently connected?
  • desktop_screenshot  → Get a JPEG of the owner's screen.
  • desktop_act         → Run a single OS action (mouse / keyboard / file / app).
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List

logger = logging.getLogger("zenrex.desktop_agent_tools")


# ─── Anthropic tool schemas ──────────────────────────────────────────────────
DESKTOP_TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "desktop_pair",
        "description": (
            "🖥️ Start a pairing handshake so the OWNER can connect their PHYSICAL "
            "laptop (Mac/Windows/Linux) to this AI session. Returns a 6-character "
            "`code` field + a ready-rendered `display_block`. "
            "⚠️ CRITICAL: The `code` field is AUTHORITATIVE — echo it VERBATIM to "
            "the user. Never invent, paraphrase, or modify it. Valid characters "
            "are uppercase A-Z and digits 2-9 only (no 0/O/I/1). Prefer copying "
            "the entire `display_block` text into your reply to guarantee accuracy. "
            "Use this ONCE per session before any other `desktop_*` tool. After "
            "the user runs the agent with the code, you gain native OS control: "
            "mouse, keyboard, downloads, opening apps, screenshots of the whole desktop."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "desktop_status",
        "description": (
            "🔌 Check whether the Desktop Agent is currently connected for this "
            "project. Returns {connected: bool, agent_info?}. Call this before "
            "`desktop_act` to give the user a clear instruction if not yet paired."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "desktop_screenshot",
        "description": (
            "📸 Capture the OWNER's primary display as JPEG. Returns "
            "{screenshot_b64, size: {width, height}}. Use this to SEE what the "
            "user is looking at before deciding where to click. Always screenshot "
            "first when navigating an unfamiliar UI."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "desktop_act",
        "description": (
            "🤖 Execute a single OS-level action on the OWNER's machine via the "
            "paired Desktop Agent. Use after `desktop_screenshot` to know the "
            "coordinates. Always describe what you're about to do BEFORE doing "
            "destructive actions. Move mouse to top-left corner aborts (FAILSAFE)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "move_mouse", "click", "double_click", "right_click",
                        "type", "press_key", "scroll",
                        "download_file", "open_app", "open_url", "focus_window",
                        "cursor_position", "screen_size",
                        "list_dir", "read_file", "write_file", "make_dir",
                        "run_shell",
                    ],
                    "description": (
                        "move_mouse(x,y) | click(x,y,button,clicks) | "
                        "double_click(x,y) | right_click(x,y) | type(text) | "
                        "press_key(key — Windows uses 'winleft+r' not 'win+r'; "
                        "'enter','ctrl+c','alt+tab') | "
                        "scroll(amount: + up / - down) | download_file(url,filename?) "
                        "| open_app(name — e.g. 'notepad','chrome','VS Code'). "
                        "On Windows tries to bring window to focus automatically. | "
                        "open_url(url) — opens in default browser + focuses it. | "
                        "focus_window(title) — bring an existing window to front by "
                        "title substring (e.g. 'Notepad','Chrome'). | "
                        "cursor_position() | screen_size() | list_dir(path) | "
                        "read_file(path,max_bytes?) | write_file(path,content) | "
                        "make_dir(path) | run_shell(command,timeout?) — shell needs "
                        "--allow-shell flag on agent."
                    ),
                },
                "params": {
                    "type": "object",
                    "description": "Action-specific parameters. See action description.",
                },
            },
            "required": ["action"],
        },
    },
]

DESKTOP_TOOL_LABELS_AR: Dict[str, Dict[str, str]] = {
    "desktop_pair":       {"running": "🖥️ يولّد رمز ربط للجهاز...",
                            "done": "✅ الرمز جاهز — نزّل التطبيق وشغّله"},
    "desktop_status":     {"running": "🔌 يفحص اتصال جهازك...",
                            "done": "✅ تم الفحص"},
    "desktop_screenshot": {"running": "📸 يلتقط شاشتك...",
                            "done": "✅ الشاشة محفوظة"},
    "desktop_act":        {"running": "🖱️ ينفّذ على جهازك مباشرة...",
                            "done": "✅ تم التنفيذ على جهازك"},
    "desktop_paste":      {"running": "📋 يكتب نص عبر الحافظة (سريع)...",
                            "done": "✅ تم الكتب"},
    "desktop_find":       {"running": "🔍 يبحث عن عنصر على الشاشة...",
                            "done": "✅ تم تحديد العنصر"},
    "desktop_click_text": {"running": "👆 ينقر على النص المرئي...",
                            "done": "✅ تم النقر"},
    "desktop_chat_send":  {"running": "💬 يكتب ويرسل في الـ chat...",
                            "done": "✅ تم الإرسال"},
    "desktop_overlay":    {"running": "🪟 يحدّث الـ overlay على شاشتك...",
                            "done": "✅ overlay محدّث"},
    "desktop_workspace":  {"running": "📁 يعمل على مجلد العمل zenrex_workspace...",
                            "done": "✅ تمّت العملية"},
    "desktop_search_files":{"running": "🗂️ يبحث عن ملفاتك...",
                             "done": "✅ تم البحث"},
}

DESKTOP_TOOL_NAMES: tuple = tuple(t["name"] for t in DESKTOP_TOOL_SCHEMAS) + (
    "desktop_paste", "desktop_find", "desktop_click_text", "desktop_chat_send",
    "desktop_overlay", "desktop_workspace", "desktop_search_files",
)


# ─── v0.8.0 high-level tool schemas ──────────────────────────────────────────
DESKTOP_TOOL_SCHEMAS.extend([
    {
        "name": "desktop_paste",
        "description": (
            "📋 Type ANY text (Arabic, emoji, code, 1000+ chars) into the currently "
            "focused field using clipboard paste — 10x faster than `type` and "
            "handles all unicode correctly. Use this instead of `desktop_act type` "
            "for anything longer than 30 chars or containing non-ASCII."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "desktop_find",
        "description": (
            "🔍 Find a UI element on the owner's screen by natural-language "
            "description (uses Claude Vision). Returns {x, y, width, height, "
            "confidence}. Use this BEFORE clicking when you're not 100% sure of "
            "coordinates — much more reliable than guessing from a screenshot."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string",
                                "description": "e.g. 'the chat message input box', "
                                               "'the Send button', 'the file attach paperclip'"},
            },
            "required": ["description"],
        },
    },
    {
        "name": "desktop_click_text",
        "description": (
            "👆 Click on a UI element identified by natural-language description. "
            "Convenience: runs `desktop_find` then `desktop_act click`. Use for "
            "buttons, links, menu items you can describe."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "double": {"type": "boolean", "description": "double-click if true"},
            },
            "required": ["description"],
        },
    },
    {
        "name": "desktop_chat_send",
        "description": (
            "💬 Smart all-in-one: find the chat input on the owner's screen, click "
            "it, paste your message via clipboard, then click Send. Reliable end-to-"
            "end for sending a message in any chat UI. Use this instead of "
            "stitching desktop_find + desktop_act + desktop_paste manually."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "input_hint": {"type": "string",
                               "description": "(optional) text describing the input — "
                                              "default 'chat message input box'"},
                "send_hint": {"type": "string",
                              "description": "(optional) default 'Send button or arrow'"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "desktop_overlay",
        "description": (
            "🪟 Show / update / hide a floating status overlay on the owner's "
            "screen (top-right). Use 'show' or 'update' at the start of each task "
            "so the owner sees what you're doing live. Use 'hide' when done."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["show", "update", "hide"]},
                "text": {"type": "string"},
                "title": {"type": "string", "description": "(optional) header line"},
            },
            "required": ["mode"],
        },
    },
    {
        "name": "desktop_workspace",
        "description": (
            "📁 Manage files in ~/Downloads/zenrex_workspace/ on the owner's "
            "machine — a sandbox folder for AI-generated reports, code, PDFs, etc. "
            "Modes: save (filename + content or content_b64), list (subdir?), "
            "read (filename)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["save", "list", "read"]},
                "filename": {"type": "string"},
                "content": {"type": "string"},
                "content_b64": {"type": "string"},
                "subdir": {"type": "string"},
            },
            "required": ["mode"],
        },
    },
    {
        "name": "desktop_search_files",
        "description": (
            "🗂️ Search the owner's machine for files matching a pattern "
            "(e.g. '*.pdf', '*report*'). Searches Documents + Downloads + Desktop "
            "by default, or pass custom `roots`."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "e.g. '*.pdf'"},
                "roots": {"type": "array", "items": {"type": "string"},
                          "description": "(optional) custom search paths"},
                "max_results": {"type": "integer", "description": "default 100"},
            },
            "required": ["pattern"],
        },
    },
])


# ─── Implementations ─────────────────────────────────────────────────────────
def _public_base() -> str:
    return (os.environ.get("BACKEND_URL", "") or "").rstrip("/")


async def desktop_pair(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if not ctx.project_id:
        return {"ok": False, "error": "project_id required"}
    try:
        from .local_browser_relay import create_desktop_pairing
        info = create_desktop_pairing(ctx.project_id)
        base = _public_base()
        code = info["code"]  # <-- AUTHORITATIVE. Echo this string verbatim.
        ps_cmd = f"iwr {base}/api/desktop-agent/bootstrap.ps1 -useb | iex"
        sh_cmd = f"curl -fsSL {base}/api/desktop-agent/bootstrap.sh | bash"
        # display_block is ready-to-render markdown the model can copy 1:1.
        display_block = (
            f"🔑 **رمز ربط الجهاز:** `{code}`  ⏱️ صالح 10 دقايق\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**الحالة الأولى — التطبيق مركّب عندك:**\n"
            f"افتح أيقونة **\"Zenrex Desktop Agent\"** من سطح المكتب → "
            f"الصق الرمز `{code}` في الخانة → اضغط **Connect**.\n\n"
            f"**الحالة الثانية — أول مرة (يحتاج تثبيت):**\n"
            f"افتح **PowerShell** (Start → اكتب `powershell`) والصق:\n"
            f"```powershell\n{ps_cmd}\n```\n"
            f"لما يطلب الرمز اكتب: **`{code}`**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        return {
            "ok": True,
            "code": code,                                            # <-- AUTHORITATIVE
            "expires_in_seconds": info["expires_in_seconds"],
            "download_url": f"{base}/api/desktop-agent/download" if base else "/api/desktop-agent/download",
            "install_command_windows": ps_cmd,
            "install_command_mac_linux": sh_cmd,
            "display_block": display_block,
            "model_instruction": (
                "CRITICAL: Echo the `code` field VERBATIM in your reply. "
                "Do NOT modify, rephrase, or invent a code. The user MUST receive "
                f"exactly: {code}"
            ),
        }
    except Exception as e:
        logger.exception("desktop_pair failed")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def desktop_status(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if not ctx.project_id:
        return {"ok": False, "error": "project_id required"}
    try:
        from .local_browser_relay import is_desktop_agent_connected, _DESKTOP_PAIRINGS
        connected = is_desktop_agent_connected(ctx.project_id)
        info = {}
        # Try to grab agent info from any active pairing for this project
        for _code, p in _DESKTOP_PAIRINGS.items():
            if p.get("project_id") == ctx.project_id and p.get("ws_connected"):
                info = p.get("agent_info") or {}
                break
        return {
            "ok": True,
            "connected": connected,
            "agent_info": info,
            "message": ("✅ Desktop Agent متصل وجاهز للتنفيذ على جهازك." if connected
                        else "❌ Desktop Agent غير متصل. استدعِ `desktop_pair` أولاً."),
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def desktop_screenshot(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if not ctx.project_id:
        return {"ok": False, "error": "project_id required"}
    try:
        from .local_browser_relay import send_command_to_desktop
        result = await send_command_to_desktop(ctx.project_id, "screenshot", {})
        result["kind"] = "desktop_screenshot"
        return result
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def desktop_act(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if not ctx.project_id:
        return {"ok": False, "error": "project_id required"}
    action = (args.get("action") or "").strip().lower()
    params = args.get("params") or {}
    if not action:
        return {"ok": False, "error": "action required"}
    try:
        from .local_browser_relay import send_command_to_desktop
        result = await send_command_to_desktop(ctx.project_id, action, params)
        result["kind"] = "desktop_step"
        result["action"] = action
        return result
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


# ─── v0.8.0 high-level tool handlers ─────────────────────────────────────────
async def desktop_paste(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if not ctx.project_id:
        return {"ok": False, "error": "project_id required"}
    text = args.get("text", "")
    if not text:
        return {"ok": False, "error": "text required"}
    from .local_browser_relay import send_command_to_desktop
    result = await send_command_to_desktop(ctx.project_id, "clipboard_paste", {"text": text})
    result["kind"] = "desktop_paste"
    return result


async def desktop_find(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    """Use Claude Vision to find a UI element."""
    if not ctx.project_id:
        return {"ok": False, "error": "project_id required"}
    description = (args.get("description") or "").strip()
    if not description:
        return {"ok": False, "error": "description required"}
    from .local_browser_relay import send_command_to_desktop, desktop_find_element
    from fastapi import Request
    # Take screenshot
    shot = await send_command_to_desktop(ctx.project_id, "screenshot", {})
    if not shot.get("ok"):
        return {"ok": False, "error": f"screenshot failed: {shot.get('error','')[:120]}"}
    screenshot_b64 = shot.get("screenshot_b64", "")
    # Call the vision endpoint directly (in-process)
    class _FakeReq:
        async def json(self):
            return {"project_id": ctx.project_id, "description": description,
                    "screenshot_b64": screenshot_b64}
    try:
        r = await desktop_find_element(_FakeReq())  # type: ignore[arg-type]
        if isinstance(r, dict):
            r["kind"] = "desktop_find"
            return r
        return {"ok": False, "error": "unexpected vision response"}
    except Exception as e:
        return {"ok": False, "error": f"vision error: {type(e).__name__}: {str(e)[:200]}"}


async def desktop_click_text(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if not ctx.project_id:
        return {"ok": False, "error": "project_id required"}
    description = (args.get("description") or "").strip()
    if not description:
        return {"ok": False, "error": "description required"}
    find_result = await desktop_find(ctx, {"description": description})
    if not find_result.get("ok"):
        return find_result
    if int(find_result.get("confidence", 0)) < 40:
        return {"ok": False, "error": "low confidence finding element",
                "find_result": find_result}
    x = int(find_result.get("x", 0))
    y = int(find_result.get("y", 0))
    if not x or not y:
        return {"ok": False, "error": "vision returned 0 coords", "find_result": find_result}
    from .local_browser_relay import send_command_to_desktop
    action = "double_click" if args.get("double") else "click"
    click_result = await send_command_to_desktop(ctx.project_id, action, {"x": x, "y": y})
    click_result["kind"] = "desktop_click_text"
    click_result["found_at"] = {"x": x, "y": y, "confidence": find_result.get("confidence")}
    return click_result


async def desktop_chat_send(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    """Smart composite: find input → click → paste → click Send."""
    if not ctx.project_id:
        return {"ok": False, "error": "project_id required"}
    text = args.get("text", "")
    if not text:
        return {"ok": False, "error": "text required"}
    input_hint = args.get("input_hint") or "the chat message text input box"
    send_hint = args.get("send_hint") or "the Send button (arrow or paper-plane icon)"

    from .local_browser_relay import send_command_to_desktop
    steps: List[Dict[str, Any]] = []

    # 1) find + click the input
    found_input = await desktop_find(ctx, {"description": input_hint})
    steps.append({"step": "find_input", "result": {k: v for k, v in found_input.items()
                                                    if k not in ("raw",)}})
    if not found_input.get("ok") or int(found_input.get("confidence", 0)) < 40:
        return {"ok": False, "steps": steps, "error": "couldn't locate chat input"}
    x, y = int(found_input["x"]), int(found_input["y"])
    if not x or not y:
        return {"ok": False, "steps": steps, "error": "vision returned 0,0 for input"}
    click_result = await send_command_to_desktop(ctx.project_id, "click", {"x": x, "y": y})
    steps.append({"step": "click_input", "result": click_result})

    import asyncio
    await asyncio.sleep(0.4)

    # 2) clear existing + paste
    await send_command_to_desktop(ctx.project_id, "press_key", {"key": "ctrl+a"})
    await asyncio.sleep(0.15)
    await send_command_to_desktop(ctx.project_id, "press_key", {"key": "delete"})
    await asyncio.sleep(0.15)
    paste_result = await send_command_to_desktop(ctx.project_id, "clipboard_paste", {"text": text})
    steps.append({"step": "paste", "result": paste_result})

    await asyncio.sleep(0.4)

    # 3) find + click Send button
    found_send = await desktop_find(ctx, {"description": send_hint})
    steps.append({"step": "find_send", "result": {k: v for k, v in found_send.items()
                                                   if k not in ("raw",)}})
    if found_send.get("ok") and int(found_send.get("confidence", 0)) >= 40 and found_send.get("x"):
        sx, sy = int(found_send["x"]), int(found_send["y"])
        send_click = await send_command_to_desktop(ctx.project_id, "click", {"x": sx, "y": sy})
        steps.append({"step": "click_send", "result": send_click})
    else:
        # Fall back to Enter key
        enter_result = await send_command_to_desktop(ctx.project_id, "press_key", {"key": "enter"})
        steps.append({"step": "press_enter_fallback", "result": enter_result})

    return {"ok": True, "kind": "desktop_chat_send", "text_len": len(text), "steps": steps}


async def desktop_overlay(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if not ctx.project_id:
        return {"ok": False, "error": "project_id required"}
    mode = (args.get("mode") or "").lower()
    action_map = {"show": "overlay_show", "update": "overlay_update", "hide": "overlay_hide"}
    if mode not in action_map:
        return {"ok": False, "error": "mode must be show/update/hide"}
    from .local_browser_relay import send_command_to_desktop
    params = {}
    if mode in ("show", "update"):
        params["text"] = args.get("text", "")
        if args.get("title"):
            params["title"] = args["title"]
    result = await send_command_to_desktop(ctx.project_id, action_map[mode], params)
    result["kind"] = "desktop_overlay"
    return result


async def desktop_workspace(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if not ctx.project_id:
        return {"ok": False, "error": "project_id required"}
    mode = (args.get("mode") or "").lower()
    action_map = {"save": "workspace_save", "list": "workspace_list", "read": "workspace_read"}
    if mode not in action_map:
        return {"ok": False, "error": "mode must be save/list/read"}
    from .local_browser_relay import send_command_to_desktop
    params = {k: v for k, v in args.items() if k != "mode"}
    result = await send_command_to_desktop(ctx.project_id, action_map[mode], params)
    result["kind"] = f"desktop_workspace_{mode}"
    return result


async def desktop_search_files(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if not ctx.project_id:
        return {"ok": False, "error": "project_id required"}
    from .local_browser_relay import send_command_to_desktop
    result = await send_command_to_desktop(ctx.project_id, "search_files", {
        "pattern": args.get("pattern", "*"),
        "roots": args.get("roots") or [],
        "max_results": args.get("max_results", 100),
    })
    result["kind"] = "desktop_search_files"
    return result


# ─── Master dispatcher ───────────────────────────────────────────────────────
async def dispatch_desktop(ctx, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    fn_map = {
        "desktop_pair": desktop_pair,
        "desktop_status": desktop_status,
        "desktop_screenshot": desktop_screenshot,
        "desktop_act": desktop_act,
        # v0.8.0
        "desktop_paste": desktop_paste,
        "desktop_find": desktop_find,
        "desktop_click_text": desktop_click_text,
        "desktop_chat_send": desktop_chat_send,
        "desktop_overlay": desktop_overlay,
        "desktop_workspace": desktop_workspace,
        "desktop_search_files": desktop_search_files,
    }
    fn = fn_map.get(name)
    if not fn:
        return {"ok": False, "error": f"unknown desktop tool: {name}"}
    try:
        return await fn(ctx, args)
    except Exception as e:
        logger.exception(f"desktop tool {name} failed")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
