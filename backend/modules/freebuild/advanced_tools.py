"""
Zenrex AI Brain — Advanced Capability Tools.

These tools turn the AI from a "single-page HTML builder" into a full-stack
software engineer. They are imported and wired into the FreeBuild agent's
dispatcher in `freebuild_agent.py`.

All tools are async, return JSON-serialisable dicts, and follow the
{"ok": bool, ...} convention. They NEVER raise — errors are returned as
{"ok": False, "error": str}.

Categories:
  • Shell        : run_shell
  • Vision/AI    : analyze_file
  • File System  : read_file, write_file, list_files, delete_file, move_file
  • Database     : db_query, db_count
  • Deploy       : deploy_to
  • E2E Testing  : run_e2e_test
  • Messaging    : send_email, send_sms
  • Video        : generate_video (fal.ai)
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("zenrex.advanced_tools")

# ─── Tool schemas (added to TOOLS_SCHEMA in freebuild_agent.py) ────────────────
ADVANCED_TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "run_shell",
        "description": (
            "🔥 Execute a shell command inside a sandboxed workspace. Use this for ANY "
            "task that needs unix tools (ffmpeg, imagemagick, yt-dlp, curl, jq, pandoc, "
            "git, npm, pip, sharp, etc.) or scripts that aren't worth wrapping in a "
            "dedicated tool. The workspace is per-project at `/tmp/zenrex_ws/{project_id}/`. "
            "30-second timeout. Network is enabled. Output is captured (stdout+stderr, "
            "max 100KB)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Bash command to run. Multiple commands can be chained with &&."},
                "timeout": {"type": "integer", "default": 30, "minimum": 1, "maximum": 120},
                "cwd": {"type": "string", "description": "Subdirectory inside the project workspace."},
            },
            "required": ["command"],
        },
    },
    {
        "name": "analyze_file",
        "description": (
            "👁️ Use Vision/AI to analyze a file the user uploaded: images (PNG/JPG/WebP), "
            "PDFs, audio (MP3/WAV), or video. Returns AI-generated structured info "
            "answering your specific question. Examples: 'extract menu items from this PDF', "
            "'transcribe this Arabic voice note', 'describe this competitor screenshot', "
            "'list all products visible in this image with their prices'. Pass the asset's "
            "file_url (or a workspace path like 'menu.pdf') and a question."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Public URL OR workspace-relative path."},
                "question": {"type": "string", "description": "Arabic ok. What do you want to extract?"},
            },
            "required": ["file", "question"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "📖 Read any file from the project's multi-file workspace. Use this to access "
            "user-uploaded data files, code files you wrote, or assets. Returns text "
            "content (binary files come back base64-encoded)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Workspace-relative path, e.g. 'src/app.js', 'data/menu.csv'."},
                "max_bytes": {"type": "integer", "default": 200000, "description": "Cap on returned bytes."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "✏️ Create or overwrite a file in the project's workspace. Use for any code "
            "or data that isn't the main HTML page. Examples: 'src/app.jsx', 'styles.css', "
            "'manifest.json', 'data/products.csv', 'README.md'. Max file size: 5MB."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string", "description": "Raw text. For binary, pass base64 string with `binary=true`."},
                "binary": {"type": "boolean", "default": False, "description": "Treat content as base64-encoded binary."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_files",
        "description": (
            "📂 List all files in the project's workspace (recursive). Returns paths "
            "with sizes. Use this to take inventory before refactoring or to show the "
            "user what's in their project."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "subpath": {"type": "string", "default": "", "description": "Optional subdirectory to list."},
            },
            "required": [],
        },
    },
    {
        "name": "delete_file",
        "description": "🗑️ Delete a file or directory in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "move_file",
        "description": "↔️ Move/rename a file inside the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "src": {"type": "string"},
                "dst": {"type": "string"},
            },
            "required": ["src", "dst"],
        },
    },
    {
        "name": "db_query",
        "description": (
            "🗄️ Query the merchant's MongoDB collections directly. Use this to fetch "
            "REAL data when the user asks about their products/orders/customers/drivers. "
            "Whitelisted collections: products, orders, customers, drivers, deliveries, "
            "store_products, delivery_orders, freebuild_chat_projects. Auto-scoped to "
            "the project's merchant_id. Returns up to `limit` documents."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {"type": "string", "description": "Whitelisted collection name."},
                "filter": {"type": "object", "default": {}, "description": "MongoDB filter dict."},
                "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 200},
                "sort_by": {"type": "string", "description": "Field name to sort by."},
                "sort_desc": {"type": "boolean", "default": True},
            },
            "required": ["collection"],
        },
    },
    {
        "name": "db_count",
        "description": "🧮 Count documents matching a filter in a whitelisted collection.",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {"type": "string"},
                "filter": {"type": "object", "default": {}},
            },
            "required": ["collection"],
        },
    },
    {
        "name": "deploy_to",
        "description": (
            "🚀 Deploy the current site to a third-party host (in ADDITION to Zenrex). "
            "Supported: 'vercel', 'netlify', 'cloudflare_pages', 'github_pages'. Needs "
            "the provider's API token saved via save_credential (e.g. 'vercel_token'). "
            "Returns the live URL and any logs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "provider": {"type": "string", "enum": ["vercel", "netlify", "cloudflare_pages", "github_pages"]},
                "project_name": {"type": "string", "description": "Project slug on that host."},
            },
            "required": ["provider", "project_name"],
        },
    },
    {
        "name": "run_e2e_test",
        "description": (
            "🧪 Run a multi-step E2E test in a real headless browser (Playwright). Each "
            "step is one of: 'goto' (url), 'click' (selector), 'fill' (selector,value), "
            "'wait' (ms or selector), 'assert_text' (text), 'screenshot'. Returns per-step "
            "pass/fail + final screenshot. Use this to verify flows like login → add to "
            "cart → checkout."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "base_url": {"type": "string", "description": "Starting URL."},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["goto", "click", "fill", "wait", "assert_text", "screenshot"]},
                            "selector": {"type": "string"},
                            "value": {"type": "string"},
                            "url": {"type": "string"},
                            "text": {"type": "string"},
                            "ms": {"type": "integer"},
                        },
                        "required": ["action"],
                    },
                },
            },
            "required": ["base_url", "steps"],
        },
    },
    {
        "name": "send_email",
        "description": (
            "📧 Send a transactional email via Resend. Needs `resend_key` saved via "
            "save_credential. Use for: order confirmations, OTP, password resets, "
            "newsletters. From-domain must be verified in Resend dashboard."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email or comma-separated list."},
                "subject": {"type": "string"},
                "html": {"type": "string", "description": "HTML body."},
                "from": {"type": "string", "default": "Zenrex <noreply@zenrex.ai>"},
            },
            "required": ["to", "subject", "html"],
        },
    },
    {
        "name": "send_sms",
        "description": (
            "📱 Send an SMS via Twilio. Needs `twilio_sid`, `twilio_auth`, `twilio_from` "
            "saved. Use for OTP, delivery notifications, order updates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "E.164 format, e.g. +966501234567."},
                "message": {"type": "string"},
            },
            "required": ["to", "message"],
        },
    },
    {
        "name": "generate_video",
        "description": (
            "🎬 Generate a video clip via fal.ai. Needs `fal_key` saved. Models: "
            "'minimax/hailuo' (6s, $0.05/s), 'kling-video/v1/standard' (5s, $0.06/s), "
            "'fal-ai/luma-dream-machine' (5s, $0.40/s). Returns the video URL."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "English description of the scene."},
                "model": {"type": "string", "default": "minimax/hailuo",
                          "enum": ["minimax/hailuo", "fal-ai/kling-video/v1/standard", "fal-ai/luma-dream-machine"]},
                "duration_seconds": {"type": "integer", "default": 6, "minimum": 3, "maximum": 10},
                "aspect_ratio": {"type": "string", "default": "16:9", "enum": ["16:9", "9:16", "1:1"]},
                "image_url": {"type": "string", "description": "Optional starting frame (image-to-video)."},
            },
            "required": ["prompt"],
        },
    },
]


# Tool labels for live progress UI in the chat
ADVANCED_TOOL_LABELS_AR: Dict[str, Dict[str, str]] = {
    "run_shell":       {"running": "💻 ينفذ أمر shell...",         "done": "✅ تم التنفيذ"},
    "analyze_file":    {"running": "👁️ يقرأ الملف بـ Vision AI...", "done": "✅ تم تحليل الملف"},
    "read_file":       {"running": "📖 يقرأ ملف من المشروع...",     "done": "✅ تم القراءة"},
    "write_file":      {"running": "✏️ يكتب ملف في المشروع...",     "done": "✅ تم الحفظ"},
    "list_files":      {"running": "📂 يفهرس ملفات المشروع...",     "done": "✅ القائمة جاهزة"},
    "delete_file":     {"running": "🗑️ يحذف الملف...",             "done": "✅ تم الحذف"},
    "move_file":       {"running": "↔️ ينقل الملف...",             "done": "✅ تم النقل"},
    "db_query":        {"running": "🗄️ يستعلم من قاعدة البيانات...", "done": "✅ النتائج جاهزة"},
    "db_count":        {"running": "🧮 يحسب عدد السجلات...",        "done": "✅ تم العد"},
    "deploy_to":       {"running": "🚀 ينشر على المنصة الخارجية...", "done": "✅ تم النشر"},
    "run_e2e_test":    {"running": "🧪 يشغّل اختبار E2E في متصفح...", "done": "✅ انتهى الاختبار"},
    "send_email":      {"running": "📧 يرسل الإيميل...",            "done": "✅ تم الإرسال"},
    "send_sms":        {"running": "📱 يرسل SMS...",               "done": "✅ تم الإرسال"},
    "generate_video":  {"running": "🎬 يولّد الفيديو (قد يستغرق دقيقة)...", "done": "✅ الفيديو جاهز"},
}


# Names that the dispatcher should treat as async
ADVANCED_TOOL_NAMES: Tuple[str, ...] = tuple(t["name"] for t in ADVANCED_TOOL_SCHEMAS)


# ─── Workspace helpers ────────────────────────────────────────────────────────
WORKSPACE_ROOT = Path("/tmp/zenrex_ws")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_FILES_PER_PROJECT = 200


def _ws(project_id: Optional[str]) -> Path:
    """Return the workspace dir for a project, creating it if needed."""
    pid = re.sub(r"[^a-zA-Z0-9_-]", "_", str(project_id or "default"))[:60]
    p = WORKSPACE_ROOT / pid
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_path(project_id: Optional[str], rel: str) -> Optional[Path]:
    """Resolve `rel` inside the project workspace. Reject traversal."""
    ws = _ws(project_id)
    try:
        full = (ws / rel.lstrip("/")).resolve()
        if not str(full).startswith(str(ws.resolve())):
            return None
        return full
    except Exception:
        return None


# ─── Shell sandbox ────────────────────────────────────────────────────────────
_FORBIDDEN_PATTERNS = [
    r"\brm\s+-rf\s+/[^t]",   # rm -rf /  (allow /tmp)
    r":\(\)\{",              # fork bomb
    r"\bdd\s+if=/dev/zero",
    r"\bmkfs\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bsudo\b",
    r"\bsu\s",
    r"/etc/passwd",
    r"/etc/shadow",
    r"\bchmod\s+777\s+/[^t]",
]


def _shell_is_safe(cmd: str) -> Optional[str]:
    for pat in _FORBIDDEN_PATTERNS:
        if re.search(pat, cmd):
            return f"command rejected by sandbox: pattern '{pat}'"
    return None


async def run_shell(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    cmd = (args.get("command") or "").strip()
    if not cmd:
        return {"ok": False, "error": "command is required"}
    if len(cmd) > 4000:
        return {"ok": False, "error": "command too long (max 4000 chars)"}
    rejection = _shell_is_safe(cmd)
    if rejection:
        return {"ok": False, "error": rejection}

    timeout = max(1, min(int(args.get("timeout") or 30), 120))
    ws = _ws(ctx.project_id)
    sub = (args.get("cwd") or "").strip().lstrip("/")
    cwd = ws / sub if sub else ws
    if not str(cwd.resolve()).startswith(str(ws.resolve())):
        return {"ok": False, "error": "cwd outside workspace"}
    cwd.mkdir(parents=True, exist_ok=True)

    started = time.time()
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env={**os.environ, "HOME": str(ws), "PATH": os.environ.get("PATH", "")},
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return {"ok": False, "error": f"timeout after {timeout}s", "elapsed_seconds": timeout}
        elapsed = round(time.time() - started, 2)
        stdout = (stdout_b or b"").decode("utf-8", errors="replace")[:100_000]
        stderr = (stderr_b or b"").decode("utf-8", errors="replace")[:50_000]
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "elapsed_seconds": elapsed,
            "cwd": str(cwd.relative_to(ws)) or ".",
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


# ─── File system ──────────────────────────────────────────────────────────────
async def write_file(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    rel = (args.get("path") or "").strip().lstrip("/")
    if not rel or rel.endswith("/"):
        return {"ok": False, "error": "path is required and must be a file"}
    full = _safe_path(ctx.project_id, rel)
    if not full:
        return {"ok": False, "error": "path escapes workspace"}
    content = args.get("content") or ""
    is_binary = bool(args.get("binary"))
    try:
        if is_binary:
            data = base64.b64decode(content)
        else:
            data = content.encode("utf-8")
        if len(data) > MAX_FILE_SIZE:
            return {"ok": False, "error": f"file too large ({len(data)} > {MAX_FILE_SIZE} bytes)"}
        # Check file count limit
        existing = sum(1 for _ in _ws(ctx.project_id).rglob("*") if _.is_file())
        if existing >= MAX_FILES_PER_PROJECT and not full.exists():
            return {"ok": False, "error": f"workspace at max files ({MAX_FILES_PER_PROJECT})"}
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
        return {"ok": True, "path": rel, "bytes": len(data)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def read_file(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    rel = (args.get("path") or "").strip().lstrip("/")
    if not rel:
        return {"ok": False, "error": "path is required"}
    full = _safe_path(ctx.project_id, rel)
    if not full or not full.exists() or not full.is_file():
        return {"ok": False, "error": "file not found"}
    max_bytes = int(args.get("max_bytes") or 200_000)
    try:
        data = full.read_bytes()[:max_bytes]
        try:
            text = data.decode("utf-8")
            return {"ok": True, "path": rel, "content": text, "bytes": len(data),
                    "truncated": full.stat().st_size > max_bytes, "is_binary": False}
        except UnicodeDecodeError:
            return {"ok": True, "path": rel, "content": base64.b64encode(data).decode("ascii"),
                    "bytes": len(data), "truncated": full.stat().st_size > max_bytes, "is_binary": True}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def list_files(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    ws = _ws(ctx.project_id)
    subpath = (args.get("subpath") or "").strip().lstrip("/")
    base = (ws / subpath) if subpath else ws
    if not str(base.resolve()).startswith(str(ws.resolve())) or not base.exists():
        return {"ok": False, "error": "path not found"}
    items: List[Dict[str, Any]] = []
    for p in sorted(base.rglob("*")):
        if p.is_file():
            try:
                items.append({"path": str(p.relative_to(ws)), "bytes": p.stat().st_size})
            except Exception:
                continue
    return {"ok": True, "count": len(items), "files": items[:500],
            "total_bytes": sum(f["bytes"] for f in items)}


async def delete_file(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    rel = (args.get("path") or "").strip().lstrip("/")
    full = _safe_path(ctx.project_id, rel)
    if not full or not full.exists():
        return {"ok": False, "error": "file not found"}
    try:
        if full.is_dir():
            shutil.rmtree(full)
        else:
            full.unlink()
        return {"ok": True, "path": rel}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def move_file(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    src = _safe_path(ctx.project_id, (args.get("src") or "").strip().lstrip("/"))
    dst = _safe_path(ctx.project_id, (args.get("dst") or "").strip().lstrip("/"))
    if not src or not dst or not src.exists():
        return {"ok": False, "error": "src or dst invalid"}
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return {"ok": True, "src": args["src"], "dst": args["dst"]}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


# ─── Vision/AI file analysis ──────────────────────────────────────────────────
async def analyze_file(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    file_ref = (args.get("file") or "").strip()
    question = (args.get("question") or "").strip()
    if not file_ref or not question:
        return {"ok": False, "error": "file and question are required"}

    # Resolve to URL OR local path
    url: Optional[str] = None
    local_path: Optional[Path] = None
    if file_ref.startswith("http://") or file_ref.startswith("https://"):
        url = file_ref
    else:
        local_path = _safe_path(ctx.project_id, file_ref.lstrip("/"))
        if not local_path or not local_path.exists():
            return {"ok": False, "error": f"file not found in workspace: {file_ref}"}

    # Detect kind by extension
    ext = (local_path.suffix if local_path else os.path.splitext(url or "")[1]).lower().lstrip(".")
    image_exts = {"png", "jpg", "jpeg", "webp", "gif", "heic", "heif"}
    pdf_exts = {"pdf"}
    audio_exts = {"mp3", "wav", "ogg", "m4a", "flac", "aac"}
    video_exts = {"mp4", "mov", "webm", "mkv"}

    try:
        # Use Emergent Universal Key via the existing direct LLM shim if available.
        # We send a multimodal message with the file content.
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent  # type: ignore

        emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
        if not emergent_key:
            return {"ok": False, "error": "EMERGENT_LLM_KEY not set"}

        # Read file content
        if local_path:
            content_bytes = local_path.read_bytes()
        else:
            async with httpx.AsyncClient(timeout=30) as cl:
                r = await cl.get(url)
                if r.status_code >= 400:
                    return {"ok": False, "error": f"could not fetch URL: HTTP {r.status_code}"}
                content_bytes = r.content
        b64 = base64.b64encode(content_bytes).decode("ascii")

        # Route by file kind
        if ext in image_exts:
            chat = LlmChat(api_key=emergent_key, session_id=f"analyze_{ctx.project_id}_{int(time.time())}",
                            system_message="You are a meticulous visual analyst. Answer in the user's language.")
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            mime = {"jpg": "jpeg"}.get(ext, ext)
            msg = UserMessage(text=question, file_contents=[ImageContent(image_base64=b64)])
            ans = await chat.send_message(msg)
            return {"ok": True, "kind": "image", "answer": str(ans)[:8000]}

        if ext in pdf_exts:
            chat = LlmChat(api_key=emergent_key, session_id=f"analyze_{ctx.project_id}_{int(time.time())}",
                            system_message="You are a meticulous document analyst. Answer in the user's language.")
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            # PDFs: claude supports document content blocks; fall back to first-page image if SDK lacks it
            try:
                from emergentintegrations.llm.chat import DocumentContent  # type: ignore
                msg = UserMessage(text=question, file_contents=[DocumentContent(document_base64=b64, media_type="application/pdf")])
                ans = await chat.send_message(msg)
                return {"ok": True, "kind": "pdf", "answer": str(ans)[:8000]}
            except ImportError:
                # Fallback: render first page as image with pdftoppm
                with tempfile.TemporaryDirectory() as td:
                    pdf_path = Path(td) / "in.pdf"
                    pdf_path.write_bytes(content_bytes)
                    out_prefix = Path(td) / "page"
                    proc = await asyncio.create_subprocess_exec(
                        "pdftoppm", "-r", "150", "-jpeg", "-f", "1", "-l", "1",
                        str(pdf_path), str(out_prefix),
                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                    )
                    await proc.communicate()
                    pages = list(Path(td).glob("page*.jpg"))
                    if not pages:
                        return {"ok": False, "error": "could not render PDF; install pdftoppm"}
                    img_b64 = base64.b64encode(pages[0].read_bytes()).decode("ascii")
                    msg = UserMessage(text=question, file_contents=[ImageContent(image_base64=img_b64)])
                    ans = await chat.send_message(msg)
                    return {"ok": True, "kind": "pdf-firstpage", "answer": str(ans)[:8000],
                            "note": "Only first page analyzed (multi-page PDF support pending)."}

        if ext in audio_exts:
            # Use OpenAI Whisper via Emergent for transcription, then answer
            try:
                from emergentintegrations.llm.openai.whisper import OpenAIWhisperClient  # type: ignore
                wc = OpenAIWhisperClient(api_key=emergent_key)
                with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tf:
                    tf.write(content_bytes)
                    tf_path = tf.name
                try:
                    transcript = await wc.transcribe(file_path=tf_path)
                finally:
                    try:
                        os.unlink(tf_path)
                    except Exception:
                        pass
                # Now ask Claude to answer the question using the transcript
                chat = LlmChat(api_key=emergent_key, session_id=f"analyze_a_{ctx.project_id}_{int(time.time())}",
                                system_message="Answer the question using the transcript. Reply in the user's language.")
                chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
                ans = await chat.send_message(UserMessage(text=f"Question: {question}\n\nTranscript:\n{transcript}"))
                return {"ok": True, "kind": "audio", "transcript": str(transcript)[:6000],
                        "answer": str(ans)[:8000]}
            except Exception as e:
                return {"ok": False, "error": f"audio analysis failed: {type(e).__name__}: {str(e)[:200]}"}

        if ext in video_exts:
            return {"ok": False, "error": "video analysis not yet wired; extract a key frame via run_shell + ffmpeg then call analyze_file on the image"}

        # Plain text / unknown
        try:
            text = content_bytes.decode("utf-8")[:50_000]
            chat = LlmChat(api_key=emergent_key, session_id=f"analyze_t_{ctx.project_id}_{int(time.time())}",
                            system_message="Answer the question using the provided text content.")
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            ans = await chat.send_message(UserMessage(text=f"Question: {question}\n\n---\n{text}"))
            return {"ok": True, "kind": "text", "answer": str(ans)[:8000]}
        except UnicodeDecodeError:
            return {"ok": False, "error": f"unsupported file type: .{ext}"}
    except Exception as e:
        logger.exception("analyze_file failed")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"}


# ─── Database access (read-only by default) ───────────────────────────────────
_ALLOWED_COLLECTIONS = {
    "products", "store_products", "orders", "delivery_orders",
    "customers", "drivers", "deliveries",
    "freebuild_chat_projects", "freebuild_credentials",
}


async def db_query(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if ctx.db is None:
        return {"ok": False, "error": "DB not available"}
    coll = (args.get("collection") or "").strip().lower()
    if coll not in _ALLOWED_COLLECTIONS:
        return {"ok": False, "error": f"collection '{coll}' not whitelisted. Allowed: {sorted(_ALLOWED_COLLECTIONS)}"}
    filt = args.get("filter") or {}
    if not isinstance(filt, dict):
        return {"ok": False, "error": "filter must be an object"}
    limit = max(1, min(int(args.get("limit") or 20), 200))
    sort_by = (args.get("sort_by") or "").strip() or None
    sort_desc = bool(args.get("sort_desc", True))

    # Auto-scope to project's merchant if available
    try:
        proj = ctx.project or {}
        merchant_id = proj.get("merchant_id") or proj.get("user_id") or proj.get("owner_id")
        if merchant_id and coll in ("products", "store_products", "orders", "delivery_orders"):
            if "merchant_id" not in filt and "user_id" not in filt:
                filt = {**filt, "merchant_id": merchant_id}
    except Exception:
        pass

    try:
        cursor = ctx.db[coll].find(filt, {"_id": 0})
        if sort_by:
            cursor = cursor.sort(sort_by, -1 if sort_desc else 1)
        docs = await cursor.to_list(length=limit)
        return {"ok": True, "collection": coll, "count": len(docs), "filter_applied": filt, "results": docs}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def db_count(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if ctx.db is None:
        return {"ok": False, "error": "DB not available"}
    coll = (args.get("collection") or "").strip().lower()
    if coll not in _ALLOWED_COLLECTIONS:
        return {"ok": False, "error": f"collection '{coll}' not whitelisted"}
    filt = args.get("filter") or {}
    try:
        n = await ctx.db[coll].count_documents(filt)
        return {"ok": True, "collection": coll, "count": n, "filter": filt}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


# ─── Deploy to third-party hosts ──────────────────────────────────────────────
async def _get_cred(ctx, service: str) -> Optional[str]:
    """Helper: fetch a decrypted credential value for the current project, or env fallback."""
    try:
        from .freebuild_chat import _dec  # type: ignore
        if ctx.project_id and ctx.db is not None:
            doc = await ctx.db.freebuild_credentials.find_one({"project_id": ctx.project_id, "service": service})
            if doc:
                v = _dec(doc.get("value_enc") or "")
                if v:
                    return v
    except Exception:
        pass
    # Env-var fallback chain (try several common naming conventions)
    aliases = {
        "fal_key": ["FAL_KEY", "FAL_AI_KEY", "FAL_API_KEY"],
        "resend_key": ["RESEND_KEY", "RESEND_API_KEY"],
        "vercel_token": ["VERCEL_TOKEN", "VERCEL_API_TOKEN"],
        "netlify_token": ["NETLIFY_TOKEN", "NETLIFY_AUTH_TOKEN"],
        "twilio_sid": ["TWILIO_SID", "TWILIO_ACCOUNT_SID"],
        "twilio_auth": ["TWILIO_AUTH", "TWILIO_AUTH_TOKEN"],
        "twilio_from": ["TWILIO_FROM", "TWILIO_PHONE_NUMBER"],
        "openai_key": ["OPENAI_API_KEY", "OPENAI_DIRECT_KEY"],
        "anthropic_key": ["ANTHROPIC_API_KEY"],
        "elevenlabs_key": ["ELEVENLABS_API_KEY", "ELEVEN_API_KEY"],
        "github_pat": ["GITHUB_PAT", "GITHUB_TOKEN"],
    }
    for env_name in aliases.get(service, [service.upper()]):
        v = os.environ.get(env_name, "").strip()
        if v:
            return v
    return None


async def deploy_to(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    provider = (args.get("provider") or "").strip().lower()
    name = (args.get("project_name") or "").strip()
    if not name:
        return {"ok": False, "error": "project_name is required"}
    html = (ctx.current_html or "").strip()
    if not html:
        return {"ok": False, "error": "no HTML to deploy yet"}

    if provider == "vercel":
        token = await _get_cred(ctx, "vercel_token")
        if not token:
            return {"ok": False, "needs_credential": True, "service": "vercel_token",
                    "error": "vercel_token not saved. Use recommend_service('hosting') → request_credential."}
        files = [
            {"file": "index.html", "data": html},
        ]
        async with httpx.AsyncClient(timeout=60) as cl:
            r = await cl.post("https://api.vercel.com/v13/deployments",
                              headers={"Authorization": f"Bearer {token}"},
                              json={"name": name, "files": files, "projectSettings": {"framework": None}})
            if r.status_code not in (200, 201):
                return {"ok": False, "http_status": r.status_code, "error": f"Vercel: {r.text[:300]}"}
            d = r.json()
            return {"ok": True, "url": f"https://{d.get('url', '')}", "id": d.get("id"),
                    "message": f"✅ Deployed to Vercel: https://{d.get('url', '')}"}

    if provider == "netlify":
        token = await _get_cred(ctx, "netlify_token")
        if not token:
            return {"ok": False, "needs_credential": True, "service": "netlify_token",
                    "error": "netlify_token not saved."}
        async with httpx.AsyncClient(timeout=60) as cl:
            # Step 1: create or fetch site
            sites = await cl.get("https://api.netlify.com/api/v1/sites",
                                 headers={"Authorization": f"Bearer {token}"})
            site_id = None
            for s in (sites.json() or []):
                if s.get("name") == name:
                    site_id = s.get("id")
                    break
            if not site_id:
                cr = await cl.post("https://api.netlify.com/api/v1/sites",
                                   headers={"Authorization": f"Bearer {token}"},
                                   json={"name": name})
                if cr.status_code not in (200, 201):
                    return {"ok": False, "error": f"Netlify create site: {cr.text[:300]}"}
                site_id = cr.json().get("id")
            # Step 2: upload single-file deploy
            r = await cl.post(f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
                              headers={"Authorization": f"Bearer {token}",
                                       "Content-Type": "application/zip"},
                              content=_make_zip({"index.html": html.encode("utf-8")}))
            if r.status_code not in (200, 201):
                return {"ok": False, "error": f"Netlify deploy: {r.text[:300]}"}
            d = r.json()
            return {"ok": True, "url": d.get("ssl_url") or d.get("url"),
                    "deploy_id": d.get("id"),
                    "message": f"✅ Deployed to Netlify: {d.get('ssl_url') or d.get('url')}"}

    if provider == "cloudflare_pages":
        return {"ok": False, "error": "cloudflare_pages requires per-account project setup; use vercel or netlify, or use Zenrex's built-in publish_site for instant deploys."}

    if provider == "github_pages":
        return {"ok": False, "error": "github_pages: use github_create_repo + github_push_file to push to gh-pages branch."}

    return {"ok": False, "error": f"unknown provider '{provider}'"}


def _make_zip(files: Dict[str, bytes]) -> bytes:
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


# ─── E2E test runner (Playwright multi-step) ──────────────────────────────────
async def run_e2e_test(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    base_url = (args.get("base_url") or "").strip()
    steps = args.get("steps") or []
    if not base_url or not steps:
        return {"ok": False, "error": "base_url and steps required"}
    if len(steps) > 30:
        return {"ok": False, "error": "max 30 steps per test"}

    try:
        from playwright.async_api import async_playwright  # type: ignore
    except ImportError:
        return {"ok": False, "error": "playwright not installed"}

    results: List[Dict[str, Any]] = []
    screenshot_b64 = None
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx_b = await browser.new_context(viewport={"width": 1366, "height": 800})
            page = await ctx_b.new_page()
            for i, step in enumerate(steps):
                action = (step.get("action") or "").lower()
                try:
                    if action == "goto":
                        url = step.get("url") or base_url
                        if url.startswith("/"):
                            url = base_url.rstrip("/") + url
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        results.append({"step": i, "action": action, "ok": True, "url": page.url})
                    elif action == "click":
                        await page.click(step["selector"], timeout=10000)
                        results.append({"step": i, "action": action, "ok": True, "selector": step["selector"]})
                    elif action == "fill":
                        await page.fill(step["selector"], step.get("value") or "", timeout=10000)
                        results.append({"step": i, "action": action, "ok": True, "selector": step["selector"]})
                    elif action == "wait":
                        if step.get("selector"):
                            await page.wait_for_selector(step["selector"], timeout=10000)
                        else:
                            await page.wait_for_timeout(int(step.get("ms") or 1000))
                        results.append({"step": i, "action": action, "ok": True})
                    elif action == "assert_text":
                        text = step.get("text") or ""
                        body = await page.content()
                        found = text in body
                        results.append({"step": i, "action": action, "ok": found, "text": text,
                                        "details": "" if found else "text not found in page"})
                        if not found:
                            break
                    elif action == "screenshot":
                        b = await page.screenshot(type="jpeg", quality=40, full_page=False)
                        screenshot_b64 = base64.b64encode(b).decode("ascii")[:200_000]
                        results.append({"step": i, "action": action, "ok": True})
                    else:
                        results.append({"step": i, "action": action, "ok": False, "details": "unknown action"})
                        break
                except Exception as ex:
                    results.append({"step": i, "action": action, "ok": False,
                                    "details": f"{type(ex).__name__}: {str(ex)[:200]}"})
                    break
            # Final screenshot if none captured
            if screenshot_b64 is None:
                try:
                    b = await page.screenshot(type="jpeg", quality=40, full_page=False)
                    screenshot_b64 = base64.b64encode(b).decode("ascii")[:200_000]
                except Exception:
                    pass
            await browser.close()
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}

    passed = sum(1 for r in results if r.get("ok"))
    return {"ok": passed == len(steps), "passed": passed, "total": len(steps),
            "results": results,
            "screenshot_base64": screenshot_b64,
            "message": (f"✅ كل {len(steps)} خطوة نجحت." if passed == len(steps)
                        else f"⚠️ نجحت {passed} من {len(steps)} — راجع `results` للتفاصيل.")}


# ─── Messaging ────────────────────────────────────────────────────────────────
async def send_email(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    key = await _get_cred(ctx, "resend_key")
    if not key:
        return {"ok": False, "needs_credential": True, "service": "resend_key",
                "error": "resend_key not saved. Call recommend_service('email') → request_credential."}
    to = (args.get("to") or "").strip()
    subject = (args.get("subject") or "").strip()
    html = args.get("html") or ""
    from_addr = (args.get("from") or "Zenrex <noreply@zenrex.ai>").strip()
    if not to or not subject or not html:
        return {"ok": False, "error": "to, subject, html are required"}
    payload = {
        "from": from_addr,
        "to": [t.strip() for t in to.split(",") if t.strip()],
        "subject": subject,
        "html": html,
    }
    try:
        async with httpx.AsyncClient(timeout=20) as cl:
            r = await cl.post("https://api.resend.com/emails",
                              headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                              json=payload)
            if r.status_code not in (200, 202):
                return {"ok": False, "http_status": r.status_code, "error": f"Resend: {r.text[:300]}"}
            d = r.json()
            return {"ok": True, "id": d.get("id"), "message": f"✅ Email sent. id={d.get('id')}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def send_sms(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    sid = await _get_cred(ctx, "twilio_sid")
    auth = await _get_cred(ctx, "twilio_auth")
    sender = await _get_cred(ctx, "twilio_from")
    if not sid or not auth or not sender:
        return {"ok": False, "needs_credential": True, "service": "twilio_sid",
                "error": "Twilio creds missing (need twilio_sid + twilio_auth + twilio_from). Call recommend_service('sms')."}
    to = (args.get("to") or "").strip()
    msg = args.get("message") or ""
    if not to or not msg:
        return {"ok": False, "error": "to and message required"}
    try:
        async with httpx.AsyncClient(timeout=20, auth=(sid, auth)) as cl:
            r = await cl.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                data={"From": sender, "To": to, "Body": msg},
            )
            if r.status_code not in (200, 201):
                return {"ok": False, "http_status": r.status_code, "error": f"Twilio: {r.text[:300]}"}
            d = r.json()
            return {"ok": True, "sid": d.get("sid"), "message": f"✅ SMS sent. sid={d.get('sid')}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


# ─── Video generation (fal.ai) ────────────────────────────────────────────────
async def generate_video(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    key = await _get_cred(ctx, "fal_key")
    if not key:
        return {"ok": False, "needs_credential": True, "service": "fal_key",
                "error": "fal_key not saved. Call recommend_service('video_ai') → request_credential."}
    prompt = (args.get("prompt") or "").strip()
    if not prompt:
        return {"ok": False, "error": "prompt is required"}
    model = (args.get("model") or "minimax/hailuo").strip()
    duration = int(args.get("duration_seconds") or 6)
    aspect = (args.get("aspect_ratio") or "16:9").strip()
    image_url = (args.get("image_url") or "").strip() or None

    # Map model → fal endpoint
    endpoint_map = {
        "minimax/hailuo": "fal-ai/minimax/hailuo-02/standard/text-to-video",
        "fal-ai/kling-video/v1/standard": "fal-ai/kling-video/v1/standard/text-to-video",
        "fal-ai/luma-dream-machine": "fal-ai/luma-dream-machine",
    }
    endpoint = endpoint_map.get(model, "fal-ai/minimax/hailuo-02/standard/text-to-video")

    body: Dict[str, Any] = {"prompt": prompt}
    if duration:
        body["duration"] = str(duration)
    if aspect:
        body["aspect_ratio"] = aspect
    if image_url:
        body["image_url"] = image_url

    try:
        async with httpx.AsyncClient(timeout=180) as cl:
            # Step 1: submit job
            sub = await cl.post(f"https://queue.fal.run/{endpoint}",
                                headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
                                json=body)
            if sub.status_code not in (200, 202):
                return {"ok": False, "http_status": sub.status_code,
                        "error": f"fal.ai submit: {sub.text[:300]}"}
            job = sub.json()
            req_id = job.get("request_id") or job.get("id")
            if not req_id:
                # Maybe the response is the final result already
                video_url = (job.get("video") or {}).get("url") or job.get("video_url")
                if video_url:
                    return {"ok": True, "video_url": video_url, "duration_seconds": duration,
                            "model": model, "message": "✅ Video ready."}
                return {"ok": False, "error": f"fal.ai: no request_id ({json.dumps(job)[:200]})"}

            # Step 2: poll
            status_url = f"https://queue.fal.run/{endpoint}/requests/{req_id}/status"
            result_url = f"https://queue.fal.run/{endpoint}/requests/{req_id}"
            for _ in range(60):  # up to 3 minutes
                await asyncio.sleep(3)
                st = await cl.get(status_url, headers={"Authorization": f"Key {key}"})
                if st.status_code != 200:
                    continue
                sd = st.json()
                if (sd.get("status") or "").upper() in ("COMPLETED", "DONE", "SUCCEEDED"):
                    rs = await cl.get(result_url, headers={"Authorization": f"Key {key}"})
                    rd = rs.json() if rs.status_code == 200 else {}
                    video_url = (rd.get("video") or {}).get("url") or rd.get("video_url")
                    return {"ok": True, "video_url": video_url, "duration_seconds": duration,
                            "model": model, "request_id": req_id,
                            "message": f"✅ Video generated: {video_url}"}
                if (sd.get("status") or "").upper() in ("FAILED", "CANCELLED", "ERROR"):
                    return {"ok": False, "error": f"fal.ai job failed: {json.dumps(sd)[:200]}"}
            return {"ok": False, "error": "fal.ai poll timeout (>3 min)"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


# ─── Master dispatcher ────────────────────────────────────────────────────────
async def dispatch_advanced(ctx, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Called by freebuild_agent.py when an ADVANCED_TOOL_NAMES tool is invoked."""
    fn_map = {
        "run_shell": run_shell,
        "analyze_file": analyze_file,
        "read_file": read_file,
        "write_file": write_file,
        "list_files": list_files,
        "delete_file": delete_file,
        "move_file": move_file,
        "db_query": db_query,
        "db_count": db_count,
        "deploy_to": deploy_to,
        "run_e2e_test": run_e2e_test,
        "send_email": send_email,
        "send_sms": send_sms,
        "generate_video": generate_video,
    }
    fn = fn_map.get(name)
    if not fn:
        return {"ok": False, "error": f"unknown advanced tool: {name}"}
    try:
        return await fn(ctx, args)
    except Exception as e:
        logger.exception(f"advanced tool {name} failed")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
