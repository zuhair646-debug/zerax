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
            "code and a ZIP download URL for the Zenrex Desktop Agent. Use this "
            "ONCE per session before any other `desktop_*` tool. After the user "
            "runs the agent with the code, you gain native OS control: mouse, "
            "keyboard, downloads, opening apps, screenshots of the whole desktop."
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
}

DESKTOP_TOOL_NAMES: tuple = tuple(t["name"] for t in DESKTOP_TOOL_SCHEMAS)


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
        sh_cmd = f'curl -fsSL {base}/api/desktop-agent/bootstrap.sh | bash -s -- {info["code"]}'
        ps_cmd = f'iwr {base}/api/desktop-agent/bootstrap.ps1 -useb | iex'
        return {
            "ok": True,
            "code": info["code"],
            "expires_in_seconds": info["expires_in_seconds"],
            "download_url": f"{base}/api/desktop-agent/download" if base else "/api/desktop-agent/download",
            "one_line_install_mac_linux": sh_cmd,
            "one_line_install_windows": ps_cmd,
            "instructions": (
                "🚀 **أسهل طريقة — أمر واحد ينزّل ويشغّل كل شي:**\n\n"
                f"**Mac / Linux** (Terminal):\n"
                f"```bash\n{sh_cmd}\n```\n\n"
                f"**Windows** (PowerShell):\n"
                f"```powershell\n{ps_cmd} {info['code']}\n```\n\n"
                f"🔑 الرمز: **{info['code']}** (صالح 10 دقايق)\n"
                f"بعد التشغيل بيطلع لك ✅ Connected، وأقدر أتحكم في جهازك مباشرة."
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


# ─── Master dispatcher ───────────────────────────────────────────────────────
async def dispatch_desktop(ctx, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    fn_map = {
        "desktop_pair": desktop_pair,
        "desktop_status": desktop_status,
        "desktop_screenshot": desktop_screenshot,
        "desktop_act": desktop_act,
    }
    fn = fn_map.get(name)
    if not fn:
        return {"ok": False, "error": f"unknown desktop tool: {name}"}
    try:
        return await fn(ctx, args)
    except Exception as e:
        logger.exception(f"desktop tool {name} failed")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
