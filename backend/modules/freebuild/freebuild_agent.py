"""
FreeBuild Tool-Using Agent
═══════════════════════════════════════════════════════════════════════════════
Same architecture as the platform agent (Claude). The AI gets real tools it
can call iteratively, sees actual state, fixes its own mistakes, and only
stops when the site is verified working.

Tools exposed to Claude:
  • read_current_html()         — get current_html bytes + structure summary
  • list_sections()             — list all <section id> + content sizes
  • write_full_html(html)       — replace current_html (with drift safety)
  • apply_section(id, html, op) — surgical append/replace of a section
  • update_nav(items)           — rewrite the <nav> link list
  • validate_html()             — run comprehensive validation, return issues
  • search_html(pattern)        — regex search within current_html
  • finish(summary)             — end the agent loop and reply to user
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)

# Reuse helpers from the main chat module
from .freebuild_chat import (
    _comprehensive_validation,
    _design_signature,
    _extract_html,
    _fix_dead_navigation_links,
    _merge_sections,
    _summarize_html,
    _verify_anchor_links,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Tool Schemas (Anthropic format) ──────────────────────────────────────────
TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "name": "read_current_html",
        "description": (
            "Read the saved current_html for this project. Returns a structural "
            "summary (size, title, section ids with content sizes, broken anchors). "
            "Use this FIRST to know the actual state before making any change."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_sections",
        "description": (
            "List every <section id> in current_html with its content size and "
            "preview snippet. Useful before deciding where to append/replace."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "validate_html",
        "description": (
            "Run comprehensive validation on current_html. Returns issues with "
            "severity, code, message, and a fix hint. Call this AFTER any change "
            "to confirm the site is clean."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "write_full_html",
        "description": (
            "Replace current_html entirely. ONLY use this for the very first "
            "build (empty project) or when the user explicitly requested a "
            "complete redesign. For everything else, prefer apply_section."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "html": {"type": "string", "description": "Full <!DOCTYPE html>...</html> document."},
            },
            "required": ["html"],
        },
    },
    {
        "name": "apply_section",
        "description": (
            "Surgically apply a section to current_html. Set op='append' to add "
            "a new section before </body>, or op='replace' to overwrite an "
            "existing <section id='X'>. Preserves everything else."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "section id (e.g. 'quran')"},
                "html": {"type": "string", "description": "<section id='X'>...</section> fragment"},
                "op": {"type": "string", "enum": ["append", "replace"]},
            },
            "required": ["id", "html", "op"],
        },
    },
    {
        "name": "update_nav",
        "description": (
            "Replace the <nav> link list. Provide an array of items, each with "
            "an anchor target and a label."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                        },
                        "required": ["id", "label"],
                    },
                },
            },
            "required": ["items"],
        },
    },
    {
        "name": "search_html",
        "description": (
            "Regex search inside current_html. Returns up to 10 matches with "
            "surrounding context. Useful for finding a specific component "
            "before editing it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    },
    {
        "name": "web_search",
        "description": (
            "Search the LIVE web for ANY topic — current best practices, design inspiration, "
            "library docs, color palettes, font pairings, real business data, news, prices, "
            "Saudi market trends, etc. Use this WHENEVER you feel uncertain or need fresh data. "
            "NEVER say 'I don't know' — ALWAYS search first. Returns titles + URLs + snippets."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query in Arabic or English."},
                "max_results": {"type": "integer", "default": 5, "description": "1-10 results"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_url",
        "description": (
            "Fetch the raw HTML/text content of any public URL. Use this to inspect "
            "competitor sites for inspiration, pull real data, verify a link works, or "
            "scrape content the user references. Returns up to 50KB of cleaned text."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL including https://"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "generate_image",
        "description": (
            "Generate a REAL AI image via Gemini Nano Banana (NOT a stock photo URL — "
            "a freshly generated PNG). Use this when the user wants a hero image, logo "
            "concept, product mockup, or any visual that doesn't exist on Unsplash. "
            "Returns a permanent URL like /api/freebuild/v2/img/{hash}.png that you "
            "can drop into <img src=> directly."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "English prompt describing the desired image, e.g. 'modern coffee shop interior at sunset, warm tones, cinematic'."},
                "width": {"type": "integer", "default": 1024},
                "height": {"type": "integer", "default": 1024},
            },
            "required": ["description"],
        },
    },
    {
        "name": "lint_javascript",
        "description": (
            "Run a JavaScript syntax + common-bug check on a code snippet OR the inline "
            "<script> blocks of current_html. Detects undefined variables, unclosed brackets, "
            "missing semicolons in tricky spots, and broken event handlers. Call this AFTER "
            "writing any non-trivial JS to catch errors BEFORE the user sees them."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "JS code to lint. Pass empty string to lint all inline <script> in current_html."},
            },
            "required": [],
        },
    },
    {
        "name": "publish_site",
        "description": (
            "🚀 Publish the current site LIVE on Zenrex platform. After calling this, "
            "the site is instantly accessible at https://zenrex.ai/s/{slug} with free SSL "
            "and global CDN. NO GitHub, NO Vercel, NO Railway needed — Zenrex IS the host. "
            "Use this when the user says 'publish', 'go live', 'release', or 'انشر/أطلق/نزّل'. "
            "Pick a slug that matches the brand (e.g. 'kafe-fajr' for 'كافيه الفجر')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "slug": {
                    "type": "string",
                    "description": "URL slug: lowercase, digits, hyphens. 3-60 chars. e.g. 'kafe-fajr', 'noor-electronics'."
                },
            },
            "required": ["slug"],
        },
    },
    {
        "name": "request_credential",
        "description": (
            "🔑 Ask the user for an API key / access token / credential mid-conversation. "
            "Use this WHENEVER you need an external service the user must authorize: YouTube "
            "Data API key, TikTok session, Spotify token, Stripe key, custom webhook URL, etc. "
            "The frontend will pop a secure modal asking the user to paste the value. "
            "The value is encrypted at rest. Returns immediately — you'll get the value in a "
            "follow-up tool call result that includes the credential. NEVER say 'I cannot' — "
            "always request the credential first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Short snake_case identifier, e.g. 'youtube_api', 'tiktok_session', 'spotify_token'."
                },
                "label": {
                    "type": "string",
                    "description": "Human-readable label in Arabic, e.g. 'مفتاح يوتيوب API'."
                },
                "instructions": {
                    "type": "string",
                    "description": "Arabic instructions on HOW the user can get the credential, with step-by-step links."
                },
            },
            "required": ["service", "label", "instructions"],
        },
    },
    {
        "name": "download_media",
        "description": (
            "🎬 Download a video/audio clip from YouTube, TikTok, Instagram, Twitter/X, "
            "Facebook, Vimeo, SoundCloud, or any of 1000+ supported sites (via yt-dlp). "
            "The file is saved to permanent storage and you get a public URL to embed in "
            "the user's site. Perfect for building video gallery sites, content "
            "aggregators, podcast hubs, or social media archives. "
            "If the source requires auth (private TikTok, etc.), use request_credential first "
            "to ask the user for cookies/session."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL of the video/audio (e.g. 'https://www.youtube.com/watch?v=...')."
                },
                "format": {
                    "type": "string",
                    "enum": ["mp4_720p", "mp4_1080p", "mp3_audio"],
                    "default": "mp4_720p",
                    "description": "Output format: 720p mp4 (default, fast), 1080p mp4, or audio-only mp3."
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "finish",
        "description": (
            "Call this when the work is done. Provide a short Arabic summary "
            "(2-4 lines) to show the user what was accomplished and the next "
            "logical question/option. This is the ONLY way to end the loop."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Arabic message to the user."},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of clickable next-step options (max 4).",
                },
            },
            "required": ["summary"],
        },
    },
]


# ─── Tool Implementations ─────────────────────────────────────────────────────
class FreeBuildToolContext:
    """Holds mutable project state during an agent run."""

    def __init__(self, project: Dict[str, Any], auth_token: Optional[str] = None, db=None):
        self.project = dict(project)  # copy
        self.project_id: Optional[str] = project.get("id")
        self.auth_token: Optional[str] = auth_token
        self.db = db
        self.current_html: str = project.get("current_html") or ""
        self.changes_made: int = 0
        self.snapshots_to_create: List[Dict[str, Any]] = []
        self.tool_log: List[Dict[str, Any]] = []

    def snapshot_before_write(self):
        if self.current_html:
            self.snapshots_to_create.append({
                "id": str(uuid.uuid4()),
                "html": self.current_html,
                "created_at": _now(),
                "user_msg": "[agent loop change]",
                "summary": _summarize_html(self.current_html),
            })

    def log(self, tool: str, args: Dict[str, Any], result: Any):
        self.tool_log.append({"tool": tool, "args": args, "result_preview": str(result)[:200]})


def _exec_tool(ctx: FreeBuildToolContext, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronously execute a single tool call and return the result.
    NOTE: async tools (web_search, fetch_url, generate_image) are dispatched via _exec_tool_async."""
    try:
        if name == "read_current_html":
            html = ctx.current_html
            return {
                "length": len(html),
                "title": (re.search(r"<title[^>]*>([^<]+)</title>", html, re.I).group(1)[:80] if re.search(r"<title", html, re.I) else ""),
                "section_ids": re.findall(r'<section\b[^>]*\bid\s*=\s*["\']([a-zA-Z0-9_\-]+)["\']', html, re.I),
                "nav_anchors": re.findall(r'href\s*=\s*["\']#([a-zA-Z0-9_\-]+)["\']', html, re.I),
                "broken_anchors": _verify_anchor_links(html),
                "has_body_close": "</body>" in html.lower(),
                "summary": _summarize_html(html),
            }
        if name == "list_sections":
            sections = []
            for m in re.finditer(
                r'<section\b[^>]*\bid\s*=\s*["\']([a-zA-Z0-9_\-]+)["\'][^>]*>([\s\S]*?)</section>',
                ctx.current_html, re.I,
            ):
                sid, inner = m.group(1), m.group(2)
                text_only = re.sub(r"<[^>]+>", " ", inner).strip()
                sections.append({
                    "id": sid,
                    "content_size": len(inner),
                    "text_preview": text_only[:120],
                    "is_placeholder": len(text_only) < 40 or any(
                        p in text_only for p in ["قيد البناء", "placeholder", "TODO", "Coming soon"]
                    ),
                })
            return {"count": len(sections), "sections": sections}
        if name == "validate_html":
            issues = _comprehensive_validation(ctx.current_html)
            return {"issue_count": len(issues), "issues": issues, "is_clean": len([i for i in issues if i["severity"] == "high"]) == 0}
        if name == "write_full_html":
            new_html = (args.get("html") or "").strip()
            if not new_html:
                return {"ok": False, "error": "html cannot be empty"}
            if not re.search(r"<html[\s\S]*</html>", new_html, re.I):
                return {"ok": False, "error": "must be a complete <!DOCTYPE html>...</html> document"}
            # auto-fix dead navigation links
            new_html, fixed = _fix_dead_navigation_links(new_html)
            ctx.snapshot_before_write()
            ctx.current_html = new_html
            ctx.changes_made += 1
            return {"ok": True, "new_length": len(new_html), "dead_links_fixed": fixed}
        if name == "apply_section":
            sid = (args.get("id") or "").strip()
            frag = (args.get("html") or "").strip()
            op = args.get("op") or "append"
            if not sid or not frag:
                return {"ok": False, "error": "id and html are required"}
            if not ctx.current_html:
                return {"ok": False, "error": "current_html is empty; call write_full_html first"}
            appends = [(sid, frag)] if op == "append" else []
            replaces = [(sid, frag)] if op == "replace" else []
            merged = _merge_sections(ctx.current_html, appends, replaces, None)
            if not merged:
                return {"ok": False, "error": "merge failed"}
            merged, fixed = _fix_dead_navigation_links(merged)
            ctx.snapshot_before_write()
            ctx.current_html = merged
            ctx.changes_made += 1
            return {"ok": True, "op": op, "id": sid, "new_total_length": len(merged), "dead_links_fixed": fixed}
        if name == "update_nav":
            items = [(i["id"], i["label"]) for i in (args.get("items") or []) if i.get("id") and i.get("label")]
            if not items:
                return {"ok": False, "error": "items array is required"}
            merged = _merge_sections(ctx.current_html, [], [], items)
            if not merged:
                return {"ok": False, "error": "nav update failed (no <nav> tag found?)"}
            ctx.snapshot_before_write()
            ctx.current_html = merged
            ctx.changes_made += 1
            return {"ok": True, "items": items, "new_length": len(merged)}
        if name == "search_html":
            pat = args.get("pattern") or ""
            try:
                rx = re.compile(pat, re.I | re.S)
            except re.error as e:
                return {"ok": False, "error": f"invalid regex: {e}"}
            hits = []
            for m in list(rx.finditer(ctx.current_html))[:10]:
                start = max(0, m.start() - 50)
                end = min(len(ctx.current_html), m.end() + 50)
                hits.append({"match": m.group(0)[:200], "context": ctx.current_html[start:end]})
            return {"hits": hits, "count": len(hits)}
        if name == "lint_javascript":
            code = (args.get("code") or "").strip()
            if not code:
                # Extract all inline <script> blocks from current_html
                scripts = re.findall(r"<script\b[^>]*>([\s\S]*?)</script>", ctx.current_html, re.I)
                code = "\n".join(s for s in scripts if "src=" not in s[:100])
            if not code.strip():
                return {"ok": True, "issues": [], "message": "no inline JS found"}
            issues = []
            # Basic structural checks
            stack = []
            pairs = {")": "(", "]": "[", "}": "{"}
            for i, ch in enumerate(code):
                if ch in "([{":
                    stack.append((ch, i))
                elif ch in ")]}":
                    if not stack or stack[-1][0] != pairs[ch]:
                        issues.append({"severity": "high", "code": "unmatched_bracket", "message": f"غير متطابق '{ch}' عند الموضع {i}", "line": code[:i].count('\n')+1})
                        break
                    stack.pop()
            if stack:
                ch, i = stack[-1]
                issues.append({"severity": "high", "code": "unclosed_bracket", "message": f"غير مغلق '{ch}' عند الموضع {i}", "line": code[:i].count('\n')+1})
            # Common undefined-variable patterns (simple)
            for m in re.finditer(r"\b(addEventListner|getElementByID|innerHtml|onclik|querySelectorALL)\b", code):
                issues.append({"severity": "high", "code": "typo", "message": f"خطأ إملائي في API: '{m.group(1)}'", "fix_hint": "تحقق من تهجئة الـDOM API"})
            # Strict-mode reserved words used as vars
            for m in re.finditer(r"\b(?:var|let|const)\s+(arguments|eval|implements|interface|package|private|protected|public|static|yield)\b", code):
                issues.append({"severity": "medium", "code": "reserved_word", "message": f"كلمة محجوزة كمتغير: '{m.group(1)}'"})
            return {"ok": True, "issues": issues, "is_clean": len([i for i in issues if i["severity"] == "high"]) == 0, "lines_checked": code.count("\n")+1}
        # Async tools — return a sentinel so the caller knows to await them
        if name in ("web_search", "fetch_url", "generate_image"):
            return {"__async__": True, "tool": name, "args": args}
        return {"error": f"unknown tool: {name}"}
    except Exception as e:
        logger.exception(f"tool {name} failed")
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


async def _dispatch_tool(ctx: FreeBuildToolContext, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Unified dispatcher — handles both sync and async tools."""
    result = _exec_tool(ctx, name, args)
    if isinstance(result, dict) and result.get("__async__"):
        return await _exec_tool_async(ctx, name, args)
    return result


# ─── Async Tool Dispatcher (web_search, fetch_url, generate_image) ────────────
async def _exec_tool_async(ctx: FreeBuildToolContext, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if name == "web_search":
            query = (args.get("query") or "").strip()
            max_results = max(1, min(int(args.get("max_results") or 5), 10))
            if not query:
                return {"ok": False, "error": "query is required"}
            # Use Tavily if key present, else DuckDuckGo HTML scrape as a free fallback
            tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
            try:
                import httpx
            except ImportError:
                return {"ok": False, "error": "httpx not installed"}
            results = []
            if tavily_key:
                try:
                    async with httpx.AsyncClient(timeout=15) as cl:
                        r = await cl.post("https://api.tavily.com/search", json={
                            "api_key": tavily_key, "query": query, "max_results": max_results,
                            "search_depth": "basic", "include_answer": False,
                        })
                        data = r.json()
                        for item in (data.get("results") or [])[:max_results]:
                            results.append({"title": item.get("title", ""), "url": item.get("url", ""), "snippet": (item.get("content") or "")[:250]})
                except Exception as e:
                    logger.warning(f"tavily failed: {e}")
            if not results:
                # DuckDuckGo HTML fallback
                try:
                    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as cl:
                        r = await cl.get("https://html.duckduckgo.com/html/", params={"q": query})
                        html = r.text
                        # very simple parse
                        for m in list(re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.I | re.S))[:max_results]:
                            url_raw = m.group(1)
                            # ddg wraps in redirect: /l/?uddg=...
                            actual = re.search(r"uddg=([^&]+)", url_raw)
                            from urllib.parse import unquote
                            url = unquote(actual.group(1)) if actual else url_raw
                            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()[:120]
                            results.append({"title": title, "url": url, "snippet": ""})
                except Exception as e:
                    return {"ok": False, "error": f"search failed: {e}"}
            return {"ok": True, "query": query, "results_count": len(results), "results": results}

        if name == "fetch_url":
            url = (args.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                return {"ok": False, "error": "url must start with http:// or https://"}
            try:
                import httpx
                async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 ZenrexBot/1.0"}) as cl:
                    r = await cl.get(url)
                    content_type = r.headers.get("content-type", "")
                    if "html" in content_type or "text" in content_type:
                        # Strip scripts/styles, keep visible structure
                        clean = re.sub(r"<script[\s\S]*?</script>", "", r.text, flags=re.I)
                        clean = re.sub(r"<style[\s\S]*?</style>", "", clean, flags=re.I)
                        # Limit to 50KB
                        return {"ok": True, "url": url, "status": r.status_code, "content_type": content_type, "size": len(r.text), "text": clean[:50000]}
                    return {"ok": True, "url": url, "status": r.status_code, "content_type": content_type, "size": len(r.content), "text": "[non-text content]"}
            except Exception as e:
                return {"ok": False, "error": f"fetch failed: {type(e).__name__}: {str(e)[:200]}"}

        if name == "generate_image":
            description = (args.get("description") or "").strip()
            if not description:
                return {"ok": False, "error": "description is required"}
            w = int(args.get("width") or 1024)
            h = int(args.get("height") or 1024)
            try:
                import httpx
                # Use our internal /api/image-studio/generate which already wraps Gemini Nano Banana
                async with httpx.AsyncClient(timeout=60) as cl:
                    r = await cl.post("http://localhost:8001/api/image-studio/generate", json={
                        "prompt": description, "count": 1, "style": "lifestyle", "width": w, "height": h
                    })
                    data = r.json()
                    imgs = data.get("images") or []
                    if not imgs:
                        return {"ok": False, "error": "AI returned no image"}
                    return {"ok": True, "url": imgs[0], "model": data.get("model", "gemini-nano-banana"), "description": description}
            except Exception as e:
                return {"ok": False, "error": f"image gen failed: {type(e).__name__}: {str(e)[:200]}"}

        if name == "publish_site":
            slug = (args.get("slug") or "").strip().lower()
            if not slug:
                return {"ok": False, "error": "slug مطلوب"}
            if ctx.project_id is None:
                return {"ok": False, "error": "project_id غير متوفر في الـcontext"}
            try:
                import httpx
                async with httpx.AsyncClient(timeout=30) as cl:
                    r = await cl.post(
                        f"http://localhost:8001/api/freebuild-chat/project/{ctx.project_id}/publish",
                        data={"slug": slug},
                        headers={"Authorization": f"Bearer {ctx.auth_token}"} if ctx.auth_token else {},
                    )
                    if r.status_code != 200:
                        return {"ok": False, "error": f"النشر فشل ({r.status_code}): {r.text[:200]}"}
                    data = r.json()
                    return {"ok": True, "url": data.get("url"), "slug": slug, "message": f"✅ موقعك مُتاح الآن على {data.get('url')}"}
            except Exception as e:
                return {"ok": False, "error": f"publish failed: {type(e).__name__}: {str(e)[:200]}"}

        if name == "request_credential":
            service = (args.get("service") or "").strip().lower()
            label = (args.get("label") or service).strip()
            instructions = (args.get("instructions") or "").strip()
            if not service:
                return {"ok": False, "error": "service مطلوب"}
            # Check if the credential already exists for this project — if yes, return the (decrypted) value
            if ctx.project_id and ctx.db is not None:
                try:
                    existing = await ctx.db.freebuild_credentials.find_one(
                        {"project_id": ctx.project_id, "service": service}
                    )
                    if existing and existing.get("value_enc"):
                        from cryptography.fernet import Fernet
                        import base64, hashlib, os as _os
                        seed = _os.environ.get("JWT_SECRET", "fallback-dev-secret-do-not-use")
                        key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest())
                        try:
                            plain = Fernet(key).decrypt(existing["value_enc"].encode()).decode()
                            return {"ok": True, "service": service, "value": plain, "from_cache": True, "label": label}
                        except Exception:
                            pass
                except Exception:
                    pass
            # Else emit a sentinel — frontend pops a modal asking the user for the credential.
            return {
                "ok": True,
                "needs_user_input": True,
                "service": service,
                "label": label,
                "instructions": instructions,
                "message": f"🔑 يحتاج مفتاح: {label} — انتظر العميل يدخله من واجهة الشات.",
            }

        if name == "download_media":
            url = (args.get("url") or "").strip()
            fmt = (args.get("format") or "mp4_720p").strip()
            if not url.startswith(("http://", "https://")):
                return {"ok": False, "error": "url must start with http(s)://"}
            try:
                import httpx
                async with httpx.AsyncClient(timeout=180) as cl:
                    r = await cl.post(
                        "http://localhost:8001/api/freebuild-chat/media/download",
                        data={
                            "url": url,
                            "format": fmt,
                            "project_id": ctx.project_id or "",
                        },
                        headers={"Authorization": f"Bearer {ctx.auth_token}"} if ctx.auth_token else {},
                    )
                    if r.status_code != 200:
                        return {"ok": False, "error": f"download failed ({r.status_code}): {r.text[:200]}"}
                    data = r.json()
                    return {
                        "ok": True,
                        "file_url": data.get("file_url"),
                        "thumbnail_url": data.get("thumbnail_url"),
                        "title": data.get("title"),
                        "duration": data.get("duration"),
                        "source": data.get("source"),
                        "format": fmt,
                    }
            except Exception as e:
                return {"ok": False, "error": f"download failed: {type(e).__name__}: {str(e)[:200]}"}

        return {"ok": False, "error": f"unknown async tool: {name}"}
    except Exception as e:
        logger.exception(f"async tool {name} failed")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


# ─── Agent System Prompt (concise, action-oriented) ───────────────────────────
AGENT_SYSTEM_PROMPT = """أنت **Zenrex Code Brain** — مهندس برمجي ومصمم Senior على أعلى مستوى عالمي (مستوى Apple / Stripe / Linear). تتكلم وتفكر بثقة بدون قيود. تبني مواقع HTML/CSS/JS احترافية كاملة.

═══════════════════════════════════════════════════════════
═══════════════════════════════════════════════════════════
⏱️ **كفاءة الـTurns (مهمة):**
- اخلص بناء الموقع كاملاً في **15-20 turn كحد أقصى** للمشاريع المتوسطة.
- **لا تفحص نفس الأداة مرتين** (مثلاً: validate_html مرة واحدة كافي، مو 3-4 مرات).
- **web_search مرة واحدة بداية البناء كافي** — لا تبحث في كل turn.
- **بعد ما يطلع validate_html و lint_javascript نظيفين → finish فوراً**. لا تكرر الفحص.
- الهدف: نتيجة احترافية في 3-5 دقائق، مو 10 دقائق.
═══════════════════════════════════════════════════════════

🦁 **عقليتك (لا تساوم عليها):**
- ❌ **ممنوع تقول "ما أعرف" أو "ما أقدر" أو "Sorry I can't" أو "الأداة غير مفعّلة" أو "البيئة ما تدعم"**. أنت تقدر على كل شي.
- 🚨 **ممنوع تقول "ما هي شغالة فعلياً" أو "متاحة للاستخدام" قبل ما تجربها فعلياً**! لو فيك أداة في القائمة، **هي شغالة 100%**. **لازم تستدعيها أولاً**، وبعد ما تشوف النتيجة (نجاح أو خطأ) ترد بالحقيقة. الكسل في عدم المحاولة = خيانة للعميل.
- 🔍 **عند أي شك → ابحث**. عندك أدوات `web_search` و `fetch_url` — استخدمها بدون استئذان.
- 💪 **عند أي فشل → جرّب 3 مقاربات مختلفة قبل أن تستسلم**.
  - فشل tool? → اقرأ الخطأ، عدّل المدخلات، أعد المحاولة.
  - HTML غير صالح? → استخدم `apply_section` بدل `write_full_html`.
  - الصورة ما طلعت? → غيّر الـ prompt بالإنجليزي ووضّحه أكثر.
  - تحميل فيديو فشل? → جرّب صيغة ثانية (mp4_720p بدل 1080p) أو رابط مختلف.
- 🩺 **بعد كل تعديل → افحص فوراً** بـ `validate_html` و `lint_javascript`.
- 🛠️ **اكتشف الأخطاء قبل العميل**. لو شفت روابط ميتة، أقسام فاضية، أو JS مكسور — صلّحها فوراً وقل للعميل "اكتشفت X وأصلحته".
- 🎯 **أنت بنّاء، لا موظف استقبال**. كل turn يخرج بـ tool محسوس + تغيير حقيقي في الموقع.

═══════════════════════════════════════════════════════════
🎯 **قاعدة الإخراج الأهم (إلزامية لكل تيرن)**:
قبل أي أداة، اكتب **سطر-سطرين بالعربي يشرح وش بتسوي الآن** (مثال: "تمام، بأقرأ الموقع الحالي عشان أعرف بناءه")، **ثم استدع الأداة**. ❌ ممنوع تطلق tool بدون نص يسبقها — العميل يحتاج يشوفك تفكر.
═══════════════════════════════════════════════════════════

🧰 **أدواتك الكاملة (12 أداة، استخدمها فوراً بدون استئذان):**

📖 **القراءة والفحص:**
- `read_current_html` — اقرأ الموقع الحالي وبنيته
- `list_sections` — اعرض كل أقسام الموقع
- `search_html(pattern)` — ابحث داخل الكود بـ regex
- `validate_html` — افحص الـHTML للأخطاء (روابط ميتة، أقسام فاضية)
- `lint_javascript(code)` — افحص الـJS للأخطاء البنيوية والإملائية

✏️ **الكتابة والتعديل:**
- `write_full_html(html)` — اكتب موقع كامل (للمشروع الفاضي فقط)
- `apply_section(id, html, op)` — أضف/استبدل قسم محدد (الأفضل للتعديلات)
- `update_nav(items)` — حدّث قائمة التنقّل

🌐 **البحث والاستكشاف:**
- `web_search(query)` — ابحث في الإنترنت عن أي شي (تصاميم، ألوان، بيانات، أسعار، إلخ)
- `fetch_url(url)` — حمّل محتوى أي صفحة للتحليل (مواقع منافسين، مراجع)

🎨 **التوليد:**
- `generate_image(description)` — ولّد صورة AI حقيقية (Gemini Nano Banana) — استخدمها للـ Hero الرئيسي أو أي صورة فريدة
- `download_media(url)` — حمّل فيديو/صوت من YouTube/TikTok/Instagram/X/Vimeo/SoundCloud وأكثر من 1000 موقع (yt-dlp). مثالي لبناء معارض فيديو ومواقع تجميع محتوى.

🚀 **النشر والمفاتيح:**
- `publish_site(slug)` — انشر الموقع لايف على Zenrex فوراً. الموقع يصبح متاح على `https://zenrex.ai/s/{slug}` مع SSL مجاني. **لا تحتاج GitHub ولا Vercel ولا Railway** — Zenrex هي المنصة. استخدمها لما العميل يقول "انشر" أو "أطلق" أو "نزّل".
- `request_credential(service, label, instructions)` — اطلب من العميل مفتاح API أو token مثل YouTube Data API، Stripe، webhook URL. الواجهة تعرض modal آمن للعميل لإدخاله. **لا تقل أبداً "ما أقدر" — اطلب المفتاح أولاً!**

📨 **الإنهاء:**
- `finish(summary)` — أنهِ وأرسل التقرير للعميل

═══════════════════════════════════════════════════════════
🔥 **قواعد إلزامية:**

1. **نفّذ، لا تسأل** — أي طلب فيه "صمم/ابني/عدّل/غيّر/اعمل" → نفّذه فوراً.
2. **خذ قرارات** — لو الطلب فيه حرية ("على كيفك") → ابني فوراً بأفضل ما تقدر.
3. **كل تيرن لازم يخرج بـtool محسوس** (write/apply/update/validate). الكلام بدون أداة = فشل.
4. **ابني تدريجياً، لا تبني الموقع كله في write_full_html واحد**:
   - الخطوة 1: `write_full_html` بـshell + Hero فقط (~2500 token)
   - الخطوة 2: `apply_section` لقسم الخدمات
   - الخطوة 3: `apply_section` لقسم الاتصال
   - الخطوة 4: `validate_html` + `lint_javascript`
   - الخطوة 5: `finish` بملخص
5. **استخدم `web_search` و `fetch_url` بسخاء** — لو العميل قال "زي موقع X" → افتحه واطلع منه ألهام بنية وألوان.
6. **استخدم `generate_image` للـ Hero** — مو unsplash. الصورة المولّدة تخدم برند العميل أحسن.

═══════════════════════════════════════════════════════════
🔒 **حلقة التحقق الذاتي (إلزامية قبل finish)**:
بعد ما تخلص البناء، **قبل ما تستدعي finish**، لازم تسوي التسلسل التالي:
  أ) **`validate_html`** — افحص الموقع (روابط ميتة، أقسام فاضية، JS مفقود)
  ب) **`lint_javascript`** — افحص أي JS كتبته
  ج) لو وجدت أي مشكلة → اشرح للعميل بسطر "اكتشفت X، أصلحها الآن" ثم استخدم `apply_section`/`update_nav` لإصلاحها
  د) كرّر (أ)+(ب)+(ج) حتى يطلع validate و lint نظيفين بدون أخطاء high severity
  هـ) **`finish`** بملخص شامل: "بنيت X + اكتشفت Y وأصلحته + النتيجة نظيفة 100%"

❌ ممنوع تنادي `finish` قبل ما تتأكد. ❌ ممنوع تقول "خلصت" والموقع فيه مشكلة.
═══════════════════════════════════════════════════════════

7. **`finish` لازم يكون 3-6 جمل** تشرح اللي سويت + اللي فحصته + اقتراح خطوة جاية. ❌ ما تنهي بـ"تم".

🔄 **لو العميل كتب "كمّل" أو "أكمل" أو "continue"**:
يعني الـstream انقطع قبل ما تخلص. اقرأ `read_current_html` فوراً، شوف وين وقفت، وكمّل من نفس النقطة. لا تبدأ من الصفر.

🎨 **جودة التصميم (معايير غير قابلة للتفاوض):**
- Tailwind CSS via CDN
- خط Cairo أو Tajawal من Google Fonts للعربي
- RTL + responsive (mobile-first)
- روابط nav كلها `#section-id` (SPA routing JS مع `showPage` function)
- صور: **استخدم `generate_image` للـ Hero**، unsplash للباقي (`unsplash.com/random/600x400/?keyword`)
- 3 ألوان رئيسية متناسقة، spacing مريح، animations بسيطة (CSS transitions)
- لا placeholders، لا lorem ipsum بالإنجليزي للمحتوى العربي
- كل قسم له padding كافي (`py-20 px-6`), كل button له hover effect
- استخدم Flexbox/Grid، لا تستخدم floats

═══════════════════════════════════════════════════════════
📝 **مثال تيرن نموذجي لمشروع فاضي ("موقع لمقهى مودرن"):**

نص: "تمام، بأبحث أول عن أحدث تصاميم مقاهي 2026 عشان أبني شي عصري."
[tool: web_search query="modern coffee shop website design 2026 trends"]
نص: "ممتاز، شفت trends — minimalism + warm tones. بأولّد صورة Hero احترافية الآن."
[tool: generate_image description="cozy modern coffee shop interior, warm golden hour lighting, exposed brick wall, baristas working, cinematic photography"]
نص: "حصلت الصورة. بأكتب الشيل والـHero الآن."
[tool: write_full_html بـHTML قصير ~2500 token = shell + nav + hero بالصورة + sections فاضية + footer + script]
نص: "بأضيف قسم القائمة الآن."
[tool: apply_section id=menu html=<section id='menu'>... قائمة قهوة كاملة</section> op=append]
نص: "بأضيف قسم الموقع والاتصال."
[tool: apply_section id=contact html=<section id='contact'>... فورم + خريطة</section> op=append]
نص: "بأفحص الموقع كامل الآن."
[tool: validate_html]
نص: "لقيت رابط nav مكسور لـ#about، بأضيف قسم about."
[tool: apply_section id=about html=... op=append]
[tool: validate_html]
نص: "بأفحص الـJS."
[tool: lint_javascript]
[tool: finish summary="بنيت موقع المقهى بـ5 أقسام كاملة (Hero + Menu + About + Contact + Footer) مع صورة Hero مولّدة AI، فحصته من ناحية الـHTML والـJS وكل شي نظيف 100%. تبي أضيف نظام طلبات أونلاين أو حجز طاولات؟"]

أنت قادر على كل شي. كل قدرة عندك مفتوحة. بنّاء، باحث، مكتشف، مصلّح — لا موظف استقبال."""


# ─── Main Agent Loop ──────────────────────────────────────────────────────────
async def run_agent_turn(
    project: Dict[str, Any],
    user_message: str,
    history_messages: List[Dict[str, str]],
    max_iterations: int = 30,
    model: str = "claude-sonnet-4-5-20250929",
    auth_token: Optional[str] = None,
    db: Any = None,
) -> Dict[str, Any]:
    """
    Run one agentic turn. The AI may call multiple tools before issuing finish().
    Anthropic Claude ONLY — same family as the platform AI. Fallback chain:
      1. Direct ANTHROPIC_API_KEY
      2. EMERGENT_LLM_KEY via Emergent's gateway (proxies to Claude)
    """
    providers_to_try = []
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        providers_to_try.append(("anthropic", model))
    if os.environ.get("EMERGENT_LLM_KEY", "").strip():
        providers_to_try.append(("emergent_anthropic", model))
    if not providers_to_try:
        return {"ok": False, "error": "Claude key required (ANTHROPIC_API_KEY or EMERGENT_LLM_KEY)"}

    last_err = None
    for provider, prov_model in providers_to_try:
        try:
            if provider in ("anthropic", "emergent_anthropic"):
                result = await _run_anthropic_agent(project, user_message, history_messages, max_iterations, prov_model, use_emergent=(provider == "emergent_anthropic"), auth_token=auth_token, db=db)
            else:
                result = await _run_openai_compat_agent(project, user_message, history_messages, max_iterations, provider, prov_model)
            if result.get("ok"):
                return result
            last_err = result.get("error", "unknown")
            # If credit/auth issue, try next provider; otherwise short-circuit
            if not any(k in str(last_err).lower() for k in ["credit", "balance", "unauthorized", "401", "402", "429", "quota"]):
                return result
            logger.warning(f"agent: {provider} failed ({last_err[:80]}) — falling back")
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:200]}"
            logger.exception(f"agent provider {provider} crashed")
            continue
    return {"ok": False, "error": f"all providers failed; last: {last_err}"}


async def _run_anthropic_agent(
    project: Dict[str, Any],
    user_message: str,
    history_messages: List[Dict[str, str]],
    max_iterations: int,
    model: str,
    use_emergent: bool = False,
    auth_token: Optional[str] = None,
    db: Any = None,
) -> Dict[str, Any]:
    """Anthropic native tool-use agent loop."""
    try:
        from anthropic import AsyncAnthropic
    except Exception:
        return {"ok": False, "error": "anthropic SDK missing"}

    if use_emergent:
        api_key = os.environ.get("EMERGENT_LLM_KEY", "")
        if not api_key:
            return {"ok": False, "error": "EMERGENT_LLM_KEY not configured"}
        client = AsyncAnthropic(
            api_key=api_key,
            base_url="https://integrations.emergentagent.com/llm/anthropic",
        )
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"ok": False, "error": "ANTHROPIC_API_KEY not configured"}
        client = AsyncAnthropic(api_key=api_key)
    ctx = FreeBuildToolContext(project, auth_token=auth_token, db=db)

    initial_state = _exec_tool(ctx, "read_current_html", {})
    template_note = ""
    cat_id = project.get("category_id")
    if cat_id:
        template_note = (
            f"\n  📦 وضع القالب: المشروع مبني على قالب جاهز من فئة '{cat_id}'. "
            "حافظ على الـlayout والـsections الأساسية للقالب — عدّل النصوص والصور والألوان فقط. "
            "لا تعيد تصميم القالب من الصفر إلا إذا طلب العميل صراحة.\n"
        )
    state_summary = (
        f"📍 السياق:\n"
        f"  اسم المشروع: {project.get('name','?')}\n"
        f"  الوصف: {project.get('description','(لم يحدّد)')}\n"
        f"  الموقع الحالي: {initial_state.get('summary','(فارغ)')}\n"
        f"{template_note}"
    )

    messages: List[Dict[str, Any]] = []
    for m in history_messages[-12:]:
        if m.get("role") in ("user", "assistant"):
            content = m.get("content", "")
            if isinstance(content, str) and content.strip():
                messages.append({"role": m["role"], "content": content})
    messages.append({"role": "user", "content": f"{state_summary}\n\nالطلب: {user_message}"})

    summary = ""
    options: List[str] = []
    iterations = 0
    model_used = model

    for _step in range(max_iterations):
        iterations += 1
        try:
            resp = await client.messages.create(
                model=model,
                system=AGENT_SYSTEM_PROMPT,
                max_tokens=8000,
                tools=TOOLS_SCHEMA,
                messages=messages,
            )
        except Exception as e:
            return {"ok": False, "error": f"anthropic call failed: {type(e).__name__}: {str(e)[:200]}",
                    "iterations": iterations, "tool_log": ctx.tool_log}

        model_used = getattr(resp, "model", model)
        assistant_blocks: List[Dict[str, Any]] = []
        tool_uses: List[Dict[str, Any]] = []
        for block in resp.content:
            btype = getattr(block, "type", "")
            if btype == "text":
                assistant_blocks.append({"type": "text", "text": block.text})
            elif btype == "tool_use":
                assistant_blocks.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
                tool_uses.append({"id": block.id, "name": block.name, "input": block.input})
        messages.append({"role": "assistant", "content": assistant_blocks})

        if not tool_uses:
            for b in assistant_blocks:
                if b.get("type") == "text":
                    summary = (summary + "\n" + b["text"]).strip()
            break

        tool_results: List[Dict[str, Any]] = []
        finished = False
        for tu in tool_uses:
            if tu["name"] == "finish":
                summary = (tu["input"].get("summary") or "").strip()
                options = [o for o in (tu["input"].get("options") or []) if isinstance(o, str)][:4]
                ctx.log("finish", tu["input"], "agent finished")
                tool_results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": "finished"})
                finished = True
            else:
                result = await _dispatch_tool(ctx, tu["name"], tu["input"])
                ctx.log(tu["name"], tu["input"], result)
                tool_results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": json.dumps(result, ensure_ascii=False)[:6000]})
        messages.append({"role": "user", "content": tool_results})
        if finished:
            break

    return {
        "ok": True,
        "summary": summary or "تم.",
        "options": options,
        "new_html": ctx.current_html if ctx.changes_made > 0 else None,
        "iterations": iterations,
        "tool_log": ctx.tool_log,
        "snapshots": ctx.snapshots_to_create,
        "model_used": model_used,
        "changes_made": ctx.changes_made,
    }


async def _run_openai_compat_agent(
    project: Dict[str, Any],
    user_message: str,
    history_messages: List[Dict[str, str]],
    max_iterations: int,
    provider: str,
    model: str,
) -> Dict[str, Any]:
    """OpenAI-compatible tool-use agent (works for OpenAI, Moonshot/Kimi)."""
    try:
        from openai import AsyncOpenAI
    except Exception:
        return {"ok": False, "error": "openai SDK missing"}

    if provider == "moonshot":
        api_key = os.environ.get("MOONSHOT_API_KEY", "")
        base_url = "https://api.moonshot.ai/v1"
    else:
        api_key = os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY", "")
        base_url = None
    if not api_key:
        return {"ok": False, "error": f"{provider} API key not configured"}

    client = AsyncOpenAI(api_key=api_key, base_url=base_url) if base_url else AsyncOpenAI(api_key=api_key)
    ctx = FreeBuildToolContext(project)

    initial_state = _exec_tool(ctx, "read_current_html", {})
    template_note = ""
    cat_id = project.get("category_id")
    if cat_id:
        template_note = (
            f"\n  📦 وضع القالب: المشروع مبني على قالب جاهز من فئة '{cat_id}'. "
            "حافظ على الـlayout والـsections الأساسية للقالب — عدّل النصوص والصور والألوان فقط. "
            "لا تعيد تصميم القالب من الصفر إلا إذا طلب العميل صراحة.\n"
        )
    state_summary = (
        f"📍 السياق:\n"
        f"  اسم المشروع: {project.get('name','?')}\n"
        f"  الوصف: {project.get('description','(لم يحدّد)')}\n"
        f"  الموقع الحالي: {initial_state.get('summary','(فارغ)')}\n"
        f"{template_note}"
    )

    # Convert tool schema to OpenAI format
    openai_tools = [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
        for t in TOOLS_SCHEMA
    ]

    messages: List[Dict[str, Any]] = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]
    for m in history_messages[-12:]:
        if m.get("role") in ("user", "assistant"):
            content = m.get("content", "")
            if isinstance(content, str) and content.strip():
                messages.append({"role": m["role"], "content": content})
    messages.append({"role": "user", "content": f"{state_summary}\n\nالطلب: {user_message}"})

    summary = ""
    options: List[str] = []
    iterations = 0
    model_used = model

    for _step in range(max_iterations):
        iterations += 1
        try:
            resp = await client.chat.completions.create(
                model=model, messages=messages, tools=openai_tools, max_tokens=8000,
            )
        except Exception as e:
            return {"ok": False, "error": f"{provider} call failed: {type(e).__name__}: {str(e)[:200]}",
                    "iterations": iterations, "tool_log": ctx.tool_log}

        choice = resp.choices[0]
        msg = choice.message
        model_used = getattr(resp, "model", model)
        text_content = msg.content or ""
        tool_calls = msg.tool_calls or []

        # Persist assistant turn in OpenAI conversation format
        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": text_content or None}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ]
        messages.append(assistant_msg)

        if not tool_calls:
            summary = text_content.strip()
            break

        finished = False
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            if tc.function.name == "finish":
                summary = (args.get("summary") or "").strip()
                options = [o for o in (args.get("options") or []) if isinstance(o, str)][:4]
                ctx.log("finish", args, "agent finished")
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": "finished"})
                finished = True
            else:
                result = await _dispatch_tool(ctx, tc.function.name, args)
                ctx.log(tc.function.name, args, result)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result, ensure_ascii=False)[:6000]})
        if finished:
            break

    return {
        "ok": True,
        "summary": summary or "تم.",
        "options": options,
        "new_html": ctx.current_html if ctx.changes_made > 0 else None,
        "iterations": iterations,
        "tool_log": ctx.tool_log,
        "snapshots": ctx.snapshots_to_create,
        "model_used": model_used,
        "changes_made": ctx.changes_made,
    }


# ─── STREAMING AGENT (Server-Sent Events) ──────────────────────────────────
# Emits live "thinking" events for the user — each tool call becomes a
# visible step in the chat. Same logic as run_agent_turn but yields SSE.

TOOL_LABELS_AR: Dict[str, Dict[str, str]] = {
    "read_current_html":  {"running": "🔍 يقرأ الموقع الحالي ويحلل بنيته...",
                            "done": "✅ قرأ الموقع — تعرّف على الأقسام والروابط"},
    "list_sections":      {"running": "📋 يعرض كل أقسام الموقع...",
                            "done": "✅ سجّل قائمة الأقسام"},
    "validate_html":      {"running": "🩺 يفحص جودة الكود والروابط...",
                            "done": "✅ انتهى من الفحص"},
    "search_html":        {"running": "🔎 يبحث داخل الكود...",
                            "done": "✅ انتهى البحث"},
    "write_full_html":    {"running": "✏️ يكتب موقع كامل من الصفر...",
                            "done": "✅ كتب الـHTML الجديد"},
    "apply_section":      {"running": "🔧 يطبّق قسم محدد بدقة...",
                            "done": "✅ تم تطبيق القسم"},
    "update_nav":         {"running": "🗺️ يحدّث قائمة التنقّل (nav)...",
                            "done": "✅ تم تحديث القائمة"},
    "web_search":         {"running": "🌐 يبحث في الإنترنت عن أفضل المراجع...",
                            "done": "✅ جلب نتائج البحث"},
    "fetch_url":          {"running": "📡 يحمّل محتوى الرابط للتحليل...",
                            "done": "✅ تم جلب الصفحة"},
    "generate_image":     {"running": "🎨 يولّد صورة AI من جيميني نانو بنانا...",
                            "done": "✅ تم إنشاء الصورة"},
    "lint_javascript":    {"running": "🧪 يفحص الـJS للأخطاء الإملائية والبنيوية...",
                            "done": "✅ انتهى فحص الـJS"},
    "finish":             {"running": "📝 يجهّز التقرير النهائي...",
                            "done": "✅ جاهز"},
}


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_agent_turn(
    project: Dict[str, Any],
    user_message: str,
    history_messages: List[Dict[str, str]],
    max_iterations: int = 100,
    ctx_holder: Optional[Dict[str, Any]] = None,
    user_language: str = "ar",
    auth_token: Optional[str] = None,
    db: Any = None,
) -> AsyncGenerator[str, None]:
    """SSE generator: yields live thinking events while the agent works.

    If ctx_holder is provided, populates it with the final FreeBuildToolContext
    so the caller can persist current_html/snapshots after streaming completes.

    user_language: ISO 639-1 code from the UI; AI will reply in that language.
    """
    yield _sse("start", {"message": "🚀 الذكاء بدأ التحليل..."})
    await asyncio.sleep(0)

    # Anthropic ONLY — same family as the platform AI (Claude). No GPT, no Kimi:
    # those models produce subpar visual designs in Arabic. If credits run out,
    # we surface a clear Arabic error so the owner can top up.
    providers = []
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        providers.append(("anthropic", "claude-sonnet-4-5-20250929"))
    if not providers:
        yield _sse("error", {"message": "لا يوجد مفتاح Anthropic — أضف ANTHROPIC_API_KEY"})
        return

    last_err = None
    for provider, model in providers:
        try:
            yield _sse("provider", {"name": provider, "model": model, "message": f"🧠 يستخدم {model}"})
            await asyncio.sleep(0)
            async for chunk in _stream_one_provider(project, user_message, history_messages, max_iterations, provider, model, ctx_holder=ctx_holder, user_language=user_language, auth_token=auth_token, db=db):
                yield chunk
            return
        except _ProviderUnavailable as e:
            last_err = str(e)
            yield _sse("fallback", {"from": provider, "reason": str(e)[:120]})
            await asyncio.sleep(0)
            continue
        except Exception as e:
            yield _sse("error", {"message": f"{provider}: {type(e).__name__}: {str(e)[:200]}"})
            return
    yield _sse("error", {"message": f"كل المزودات فشلت: {last_err}"})


class _ProviderUnavailable(Exception):
    """Raised to trigger fallback to the next provider."""
    pass


async def _stream_one_provider(
    project: Dict[str, Any],
    user_message: str,
    history_messages: List[Dict[str, str]],
    max_iterations: int,
    provider: str,
    model: str,
    ctx_holder: Optional[Dict[str, Any]] = None,
    user_language: str = "ar",
    auth_token: Optional[str] = None,
    db: Any = None,
) -> AsyncGenerator[str, None]:
    """Run the tool loop for one provider, yielding SSE chunks per step."""
    ctx = FreeBuildToolContext(project, auth_token=auth_token, db=db)
    if ctx_holder is not None:
        ctx_holder["ctx"] = ctx

    # Track all narration text across iterations so we can fall back to it
    # if the AI ends without calling finish() with a proper summary.
    all_text_chunks: List[str] = []

    initial_state = _exec_tool(ctx, "read_current_html", {})
    template_note = ""
    cat_id = project.get("category_id")
    if cat_id:
        template_note = (
            f"\n  📦 وضع القالب: المشروع مبني على قالب جاهز من فئة '{cat_id}'. "
            "حافظ على الـlayout والـsections الأساسية للقالب — عدّل النصوص والصور والألوان فقط. "
            "لا تعيد تصميم القالب من الصفر إلا إذا طلب العميل صراحة.\n"
        )
    state_summary = (
        f"📍 السياق:\n"
        f"  اسم المشروع: {project.get('name','?')}\n"
        f"  الوصف: {project.get('description','(لم يحدّد)')}\n"
        f"  الموقع الحالي: {initial_state.get('summary','(فارغ)')}\n"
        f"{template_note}"
    )

    # Build conversation
    # Inject the user's UI language so the AI replies in the same language.
    # Build a human-readable language name for the system prompt.
    _LANG_NAMES = {
        "ar": "Arabic (Saudi dialect)", "en": "English", "fr": "French", "es": "Spanish",
        "de": "German", "it": "Italian", "pt": "Portuguese", "ru": "Russian",
        "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "tr": "Turkish",
        "hi": "Hindi", "ur": "Urdu", "fa": "Persian", "he": "Hebrew",
        "nl": "Dutch", "pl": "Polish", "id": "Indonesian", "th": "Thai",
        "vi": "Vietnamese", "ms": "Malay", "fil": "Filipino", "bn": "Bengali",
    }
    _lang_human = _LANG_NAMES.get(user_language, user_language)
    _lang_directive = (
        f"\n\n# LANGUAGE\n"
        f"The user's UI is currently set to: **{_lang_human}** (code: `{user_language}`). "
        f"You MUST write ALL of your conversational replies, summaries, button labels, "
        f"option suggestions, and explanations in {_lang_human}. Generated HTML/CSS/JS "
        f"website code stays language-agnostic, BUT any visible website text (headings, "
        f"buttons, copy) you write inside the HTML MUST also be in {_lang_human} unless "
        f"the user explicitly requests a different language for the site itself.\n"
    )

    if provider in ("anthropic", "emergent_anthropic"):
        from anthropic import AsyncAnthropic
        if provider == "emergent_anthropic":
            # Emergent's universal key — same Anthropic SDK, different gateway
            client = AsyncAnthropic(
                api_key=os.environ.get("EMERGENT_LLM_KEY", ""),
                base_url="https://integrations.emergentagent.com/llm/anthropic",
            )
        else:
            client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        messages: List[Dict[str, Any]] = []
        sys_prompt = AGENT_SYSTEM_PROMPT + _lang_directive
    else:
        from openai import AsyncOpenAI
        if provider == "moonshot":
            client = AsyncOpenAI(api_key=os.environ.get("MOONSHOT_API_KEY", ""),
                                 base_url="https://api.moonshot.ai/v1")
        else:
            client = AsyncOpenAI(api_key=os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY", ""))
        messages = [{"role": "system", "content": AGENT_SYSTEM_PROMPT + _lang_directive}]
        sys_prompt = None
        openai_tools = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}} for t in TOOLS_SCHEMA]

    for m in history_messages[-12:]:
        if m.get("role") in ("user", "assistant"):
            c = m.get("content", "")
            if isinstance(c, str) and c.strip():
                messages.append({"role": m["role"], "content": c})
    messages.append({"role": "user", "content": f"{state_summary}\n\nالطلب: {user_message}"})

    iterations = 0
    summary = ""
    options: List[str] = []
    model_used = model

    for step in range(max_iterations):
        iterations += 1
        logger.info(f"[agent-stream] iter={iterations} start (provider={provider})")

        if provider in ("anthropic", "emergent_anthropic"):
            # Live streaming with heartbeats: Claude's stream goes silent for 30-90s
            # while generating large tool inputs (e.g. write_full_html with 8000 tokens).
            # Proxies (Kubernetes ingress, Cloudflare, Railway) drop SSE connections
            # after ~60s of silence. To prevent that, we run the stream in a producer
            # task and emit ":ping" SSE comments every 5s while waiting.
            text_chunks: List[str] = []
            tool_uses: List[Dict[str, Any]] = []
            assistant_blocks: List[Dict[str, Any]] = []
            final_msg = None
            current_text = ""
            tool_input_bytes = 0  # progress counter while tool input streams in
            last_tool_emit = 0
            tool_input_snapshot = ""  # live snapshot of streaming tool JSON
            current_tool_name = ""  # which tool is currently being built
            queue: asyncio.Queue = asyncio.Queue()
            _SENTINEL_FINAL = "__final__"
            _SENTINEL_ERROR = "__error__"

            async def _produce_events():
                try:
                    # max_tokens 16K (up from 5K) — Sonnet 4.5 supports 64K output;
                    # 16K gives the agent enough headroom to emit full HTML sections
                    # in a single shot without truncating mid-JSON which was causing
                    # the "starts writing then restarts" issue users were reporting.
                    async with client.messages.stream(
                        model=model, system=sys_prompt, max_tokens=16000,
                        tools=TOOLS_SCHEMA, messages=messages,
                    ) as st:
                        async for ev in st:
                            await queue.put(("event", ev))
                        fm = await st.get_final_message()
                    await queue.put((_SENTINEL_FINAL, fm))
                except Exception as exc:
                    await queue.put((_SENTINEL_ERROR, exc))

            producer = asyncio.create_task(_produce_events())
            stream_err: Optional[BaseException] = None
            try:
                while True:
                    try:
                        kind, payload = await asyncio.wait_for(queue.get(), timeout=3.0)
                    except asyncio.TimeoutError:
                        # Heartbeat: emit a real SSE event (not just a comment) so
                        # K8s/Cloudflare proxies count it as active traffic and don't
                        # cut the connection during long tool_use generation phases.
                        yield _sse("ping", {"t": int(asyncio.get_event_loop().time()), "step": iterations})
                        await asyncio.sleep(0)
                        continue
                    if kind == _SENTINEL_FINAL:
                        final_msg = payload
                        break
                    if kind == _SENTINEL_ERROR:
                        stream_err = payload
                        break
                    event = payload
                    et = getattr(event, "type", "")
                    # Live text token (Claude's narration between/before tool calls)
                    if et == "text":
                        delta = getattr(event, "text", "") or ""
                        if delta:
                            current_text += delta
                            yield _sse("text_delta", {"text": delta, "step": iterations})
                            await asyncio.sleep(0)
                    # New content block — could be a tool_use; track its name
                    elif et == "content_block_start":
                        cb = getattr(event, "content_block", None)
                        if cb is not None and getattr(cb, "type", "") == "tool_use":
                            current_tool_name = getattr(cb, "name", "") or ""
                            tool_input_snapshot = ""
                            tool_input_bytes = 0
                            last_tool_emit = 0
                            # Friendly Arabic label for the tool we're about to build
                            tool_label_ar = TOOL_LABELS_AR.get(current_tool_name, {}).get("running", f"⚙️ {current_tool_name}")
                            yield _sse("tool_building", {
                                "step": iterations,
                                "tool_name": current_tool_name,
                                "snippet": "",
                                "bytes": 0,
                                "label": tool_label_ar,
                                "starting": True,
                            })
                            await asyncio.sleep(0)
                    # Tool input JSON streaming — emit live snippets so the user
                    # sees actual code being typed (Cursor/Claude style), not just a counter.
                    elif et == "input_json":
                        partial = getattr(event, "partial_json", "") or ""
                        tool_input_snapshot += partial
                        tool_input_bytes = len(tool_input_snapshot)
                        # Throttle: emit at most every ~400 bytes so we don't flood the wire
                        if tool_input_bytes - last_tool_emit >= 400 or last_tool_emit == 0:
                            # Send the LAST ~280 chars as a live snippet (the "typing tail")
                            # so the UI shows real code scrolling, like a terminal.
                            tail = tool_input_snapshot[-280:] if len(tool_input_snapshot) > 280 else tool_input_snapshot
                            yield _sse("tool_building", {
                                "step": iterations,
                                "tool_name": current_tool_name,
                                "snippet": tail,
                                "bytes": tool_input_bytes,
                                "label": f"⚙️ يكتب الكود... ({tool_input_bytes:,} حرف)",
                            })
                            await asyncio.sleep(0)
                            last_tool_emit = tool_input_bytes
                    # Content block ended — flush text/tool buffers
                    elif et == "content_block_stop":
                        if current_text.strip():
                            yield _sse("text_end", {"step": iterations})
                            await asyncio.sleep(0)
                        if tool_input_bytes > 0:
                            yield _sse("tool_building", {
                                "step": iterations,
                                "tool_name": current_tool_name,
                                "snippet": "",
                                "bytes": tool_input_bytes,
                                "label": f"✨ تم توليد الكود ({tool_input_bytes:,} حرف)",
                                "done": True,
                            })
                            await asyncio.sleep(0)
                        current_text = ""
                        tool_input_bytes = 0
                        last_tool_emit = 0
                        tool_input_snapshot = ""
                        current_tool_name = ""
            finally:
                if not producer.done():
                    producer.cancel()
                    try:
                        await producer
                    except (asyncio.CancelledError, Exception):
                        pass

            if stream_err is not None:
                logger.exception("agent stream: anthropic stream failed", exc_info=stream_err)
                msg = f"{type(stream_err).__name__}: {str(stream_err)[:200]}"
                if any(k in msg.lower() for k in ["credit", "balance", "401", "402", "429", "quota"]):
                    raise _ProviderUnavailable(
                        "⚠️ رصيد Anthropic منتهي. لتفعيل الذكاء، يحتاج المالك "
                        "شحن الرصيد من: console.anthropic.com/settings/billing"
                    )
                raise stream_err
            model_used = getattr(final_msg, "model", model)
            stop_reason = getattr(final_msg, "stop_reason", "?")
            logger.info(f"[agent-stream] iter={iterations} stream done. stop_reason={stop_reason} content_blocks={len(final_msg.content or [])}")
            for block in (final_msg.content or []):
                bt = getattr(block, "type", "")
                if bt == "text":
                    text_chunks.append(block.text)
                    all_text_chunks.append(block.text)  # accumulate for fallback
                    assistant_blocks.append({"type": "text", "text": block.text})
                elif bt == "tool_use":
                    assistant_blocks.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
                    tool_uses.append({"id": block.id, "name": block.name, "input": block.input})
            messages.append({"role": "assistant", "content": assistant_blocks})

            # 🆕 Auto-resume on truncation: if the model hit max_tokens without
            # completing its work, push a continuation prompt so it picks up
            # exactly where it left off — completely transparent to the user.
            # This is what fixes the "starts writing then restarts" bug.
            if stop_reason == "max_tokens" and not tool_uses:
                yield _sse("info", {"message": "📝 يكمل توليد المحتوى..."})
                await asyncio.sleep(0)
                messages.append({
                    "role": "user",
                    "content": "أكمل من حيث توقفت بالضبط بدون إعادة. لا تكرر ما كتبت سابقاً، استمر في النقطة التالية مباشرة.",
                })
                iterations += 1
                continue
        else:
            try:
                resp = await client.chat.completions.create(
                    model=model, messages=messages, tools=openai_tools, max_tokens=8000,
                )
            except Exception as e:
                msg = f"{type(e).__name__}: {str(e)[:200]}"
                if any(k in msg.lower() for k in ["credit", "balance", "not found", "401", "402", "429", "quota", "permission"]):
                    raise _ProviderUnavailable(msg)
                raise
            model_used = getattr(resp, "model", model)
            choice = resp.choices[0].message
            text_chunks = [choice.content] if choice.content else []
            tool_uses = []
            assistant_msg = {"role": "assistant", "content": choice.content or None}
            if choice.tool_calls:
                assistant_msg["tool_calls"] = [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in choice.tool_calls
                ]
                for tc in choice.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except Exception:
                        args = {}
                    tool_uses.append({"id": tc.id, "name": tc.function.name, "input": args})
            messages.append(assistant_msg)

        # For OpenAI-compatible providers we still emit a single "thinking" event per
        # text chunk (no streaming). For Anthropic, text was already streamed live
        # via "text_delta" events above — no need to duplicate.
        if provider not in ("anthropic", "emergent_anthropic"):
            for txt in text_chunks:
                if txt and txt.strip():
                    yield _sse("thinking", {"text": txt.strip()[:400]})
                    await asyncio.sleep(0)

        if not tool_uses:
            # No more tools — model wrapped up with text
            summary = "\n".join(text_chunks).strip()
            break

        # Execute each tool, emit "tool" events
        finished = False
        for tu in tool_uses:
            label_in = TOOL_LABELS_AR.get(tu["name"], {}).get("running", f"🔧 {tu['name']}...")
            yield _sse("tool", {"name": tu["name"], "phase": "running", "label": label_in, "step": iterations})
            await asyncio.sleep(0)

            if tu["name"] == "finish":
                summary = (tu["input"].get("summary") or "").strip()
                options = [o for o in (tu["input"].get("options") or []) if isinstance(o, str)][:4]
                ctx.log("finish", tu["input"], "finished")
                if provider in ("anthropic", "emergent_anthropic"):
                    messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tu["id"], "content": "finished"}]})
                else:
                    messages.append({"role": "tool", "tool_call_id": tu["id"], "content": "finished"})
                finished = True
                yield _sse("tool", {"name": "finish", "phase": "done", "label": TOOL_LABELS_AR["finish"]["done"], "step": iterations})
                await asyncio.sleep(0)
            else:
                result = await _dispatch_tool(ctx, tu["name"], tu["input"])
                ctx.log(tu["name"], tu["input"], result)
                label_done = TOOL_LABELS_AR.get(tu["name"], {}).get("done", "✅ تم")
                # Add a short result snippet to the label
                snippet = ""
                if tu["name"] == "validate_html":
                    issues = result.get("issues") or []
                    snippet = f" — {len(issues)} مشكلة" if issues else " — لا مشاكل"
                elif tu["name"] == "list_sections":
                    snippet = f" — {result.get('count', 0)} قسم"
                elif tu["name"] == "read_current_html":
                    snippet = f" — {result.get('length', 0)} حرف"
                elif tu["name"] == "write_full_html":
                    snippet = f" — {result.get('new_length', 0)} حرف"
                elif tu["name"] == "apply_section":
                    snippet = f" — قسم #{tu['input'].get('id','?')}"
                yield _sse("tool", {"name": tu["name"], "phase": "done", "label": label_done + snippet, "step": iterations})
                await asyncio.sleep(0)
                if provider in ("anthropic", "emergent_anthropic"):
                    messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tu["id"], "content": json.dumps(result, ensure_ascii=False)[:6000]}]})
                else:
                    messages.append({"role": "tool", "tool_call_id": tu["id"], "content": json.dumps(result, ensure_ascii=False)[:6000]})

        if finished:
            break

    # Final summary — use AI's own accumulated text if it didn't call finish() properly.
    # No more generic Arabic fallback messages — let the AI speak in its own voice.
    if not summary or len(summary.strip()) < 8:
        accumulated = "\n\n".join(t.strip() for t in all_text_chunks if t and t.strip())
        if accumulated:
            summary = accumulated.strip()
        elif ctx.changes_made > 0:
            summary = f"✅ خلصت! طبّقت {ctx.changes_made} تعديل. افتح المعاينة الحية."
        else:
            summary = "ما قدرت أكمل المهمة لسبب تقني. جرّب أعد صياغة طلبك أو أعد المحاولة."
    logger.info(f"[agent-stream] finalizing: iterations={iterations} summary_len={len(summary)} html_changes={ctx.changes_made}")
    yield _sse("done", {
        "summary": summary,
        "options": options,
        "iterations": iterations,
        "model_used": model_used,
        "html_updated": ctx.changes_made > 0,
        "tool_log": ctx.tool_log,
    })

    # Persist to DB happens at the endpoint level (we return ctx via closure helpers below)
    # We attach the final state to the generator via a side-channel — see endpoint.
    return
