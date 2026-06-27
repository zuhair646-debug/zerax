"""
Library Registry — vetted CDN libraries the AI can inject in one tool call.

Architecture:
  • `/app/backend/data/library_registry.json` is the source of truth.
  • `library_summary_for_prompt()` returns a compact Arabic-friendly summary
    that the system prompt embeds in every turn (zero token waste).
  • `inject_library(ctx, args)` is the new AI tool that wires CSS + JS + init
    snippet into a page surgically (idempotent — won't double-inject).
  • `record_library_usage()` tracks Tavily-discovered libs. After 3 successful
    invocations of the same lib, it's auto-promoted into the registry under
    the `experimental` tier (community-contributed lessons).

This file is loaded by `freebuild_agent.py` and exposes:
  - LIBRARY_REGISTRY (dict)
  - LIBRARY_TOOL_SCHEMA (Anthropic-tool spec)
  - library_summary_for_prompt(max_chars=2400)
  - inject_library(ctx, args) -> dict
  - record_library_usage(db, project_id, lib_name, success)
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.library_registry")

REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "library_registry.json"
_CACHE: Dict[str, Any] = {}


def _load() -> Dict[str, Any]:
    """Load the registry from disk (cached)."""
    if "data" not in _CACHE or _CACHE.get("path_mtime") != REGISTRY_PATH.stat().st_mtime:
        try:
            with open(REGISTRY_PATH, encoding="utf-8") as f:
                _CACHE["data"] = json.load(f)
                _CACHE["path_mtime"] = REGISTRY_PATH.stat().st_mtime
        except Exception as e:
            logger.error(f"failed to load registry: {e}")
            _CACHE["data"] = {"categories": {}, "version": "0"}
    return _CACHE["data"]


LIBRARY_REGISTRY = _load()


# ─────────────────────────────────────────────────────────────────────────────
# Prompt-side summary (embedded in system prompt — extremely terse).
# ─────────────────────────────────────────────────────────────────────────────
def library_summary_for_prompt(max_chars: int = 2400) -> str:
    """Return a compact Arabic-friendly atlas the AI reads each turn."""
    data = _load()
    cats = data.get("categories", {})
    lines = [
        "📚 **Capability Atlas — مكتبات معتمدة (استخدم `inject_library` بدلاً من كتابة CDN يدوياً):**",
    ]
    for cat_id, cat in cats.items():
        ar = cat.get("ar_label", cat_id)
        variants = cat.get("variants", {})
        parts = []
        for tier_id in ("primary", "alternative", "experimental"):
            v = variants.get(tier_id)
            if not v:
                continue
            tier_icon = {"primary": "⭐", "alternative": "🔄", "experimental": "🧪"}[tier_id]
            parts.append(f"{tier_icon}{v.get('lib','?')}({v.get('bundle_kb',0)}KB)")
        lines.append(f"  • `{cat_id}` ({ar}): " + " | ".join(parts))
    lines.append("")
    lines.append("القاعدة: لما طلب العميل يطابق فئة، استدعِ `inject_library(category, variant, page)` "
                 "و**لا تكتب** `<script src='cdn...'>` يدوياً. الـ tool يحقن CSS+JS+boilerplate في 5 ثواني.")
    out = "\n".join(lines)
    if len(out) > max_chars:
        out = out[: max_chars - 50] + "\n…(مقتطف)"
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Tool schema (registered alongside ADVANCED_TOOL_SCHEMAS)
# ─────────────────────────────────────────────────────────────────────────────
LIBRARY_TOOL_SCHEMA = {
    "name": "inject_library",
    "description": (
        "📚 Inject a vetted CDN library into a page surgically. Reads from the "
        "internal library registry (15 categories × 3 variants). Handles "
        "<link> in <head>, <script defer> at end of <body>, and an init "
        "snippet at a chosen anchor. Idempotent — won't double-inject. "
        "Use this INSTEAD of manually writing <script src='https://cdn...'> "
        "for charts, maps, realtime, animation, 3D, canvas editors, code "
        "editors, tables, calendar, forms, checkout, web3, video/audio, "
        "search, llm proxy. List available with `category='?'`."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": (
                    "One of: charts, maps, realtime, animation, 3d, canvas_editor, "
                    "code_editor, tables, calendar, forms, checkout, wallet_web3, "
                    "video_audio, search, llm_proxy. Pass '?' to get the list."
                ),
            },
            "variant": {
                "type": "string",
                "enum": ["primary", "alternative", "experimental"],
                "default": "primary",
                "description": "Which variant to use. Default 'primary' (lightest, most common).",
            },
            "page": {
                "type": "string",
                "default": "index.html",
                "description": "Target page filename. Default index.html.",
            },
            "anchor_selector": {
                "type": "string",
                "description": (
                    "CSS selector inside the page where the init snippet should "
                    "go (e.g. '#main', 'section#chart-section'). If omitted or "
                    "not found, the snippet is appended before </body>."
                ),
            },
            "template_id": {
                "type": "string",
                "description": (
                    "Suffix replacing the literal 'TPL' placeholder in IDs/snippets. "
                    "Use unique per call (e.g. 'sales', 'driver-map'). Default 'main'."
                ),
            },
            "skip_init_snippet": {
                "type": "boolean",
                "default": False,
                "description": "Set true if you only want CSS+JS loaded, no DOM markup.",
            },
        },
        "required": ["category"],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
_RE_HEAD_CLOSE = re.compile(r"</head\s*>", re.IGNORECASE)
_RE_BODY_CLOSE = re.compile(r"</body\s*>", re.IGNORECASE)
_RE_HTML_CLOSE = re.compile(r"</html\s*>", re.IGNORECASE)


def _ensure_head_body(html: str) -> str:
    """Make sure the page has <head> and <body> tags before we inject."""
    if not html or not html.strip():
        return (
            '<!DOCTYPE html><html lang="ar" dir="rtl"><head>'
            '<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>صفحة</title></head><body></body></html>"
        )
    if "<head" not in html.lower():
        if "<html" in html.lower():
            html = re.sub(r"(<html[^>]*>)", r"\1<head><meta charset=\"UTF-8\"></head>", html, count=1, flags=re.IGNORECASE)
        else:
            html = '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"></head>' + html + "</html>"
    if "<body" not in html.lower():
        html = _RE_HEAD_CLOSE.sub("</head><body>", html, count=1) + "</body></html>" if "</body" not in html.lower() else html
    return html


def _inject_into_head(html: str, fragment: str) -> str:
    """Insert fragment right before </head>. Idempotent on exact-match fragments."""
    if fragment in html:
        return html  # already there
    if _RE_HEAD_CLOSE.search(html):
        return _RE_HEAD_CLOSE.sub(fragment + "\n</head>", html, count=1)
    # No </head> — append at start
    return fragment + "\n" + html


def _inject_before_body_close(html: str, fragment: str) -> str:
    """Insert fragment right before </body>. Idempotent."""
    if fragment in html:
        return html
    if _RE_BODY_CLOSE.search(html):
        return _RE_BODY_CLOSE.sub(fragment + "\n</body>", html, count=1)
    if _RE_HTML_CLOSE.search(html):
        return _RE_HTML_CLOSE.sub(fragment + "\n</html>", html, count=1)
    return html + "\n" + fragment


def _inject_at_anchor(html: str, anchor_selector: str, fragment: str) -> tuple[str, bool]:
    """Insert fragment inside the first element matching anchor_selector.
    Returns (new_html, matched). Very lightweight selector — supports
    '#id', '.class', 'tag', and 'tag#id'.
    """
    sel = anchor_selector.strip()
    if not sel:
        return html, False
    # Build a regex from the selector
    if sel.startswith("#"):
        ident = re.escape(sel[1:])
        pat = re.compile(r'(<[a-zA-Z][^>]*?id\s*=\s*["\']' + ident + r'["\'][^>]*>)', re.IGNORECASE)
    elif sel.startswith("."):
        cls = re.escape(sel[1:])
        pat = re.compile(r'(<[a-zA-Z][^>]*?class\s*=\s*["\'][^"\']*\b' + cls + r'\b[^"\']*["\'][^>]*>)', re.IGNORECASE)
    else:
        m = re.match(r"^([a-zA-Z]+)(?:#([\w-]+))?$", sel)
        if not m:
            return html, False
        tag, ident = m.group(1), m.group(2)
        if ident:
            pat = re.compile(r"(<" + tag + r'[^>]*?id\s*=\s*["\']' + re.escape(ident) + r'["\'][^>]*>)', re.IGNORECASE)
        else:
            pat = re.compile(r"(<" + tag + r"\b[^>]*>)", re.IGNORECASE)
    new_html, n = pat.subn(r"\1\n" + fragment, html, count=1)
    return new_html, n > 0


# ─────────────────────────────────────────────────────────────────────────────
# Main tool implementation
# ─────────────────────────────────────────────────────────────────────────────
async def inject_library(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    """Inject a registered library into a project page.

    `ctx` is FreeBuildToolContext (has `ctx.pages` dict & `ctx.active_page`).
    """
    data = _load()
    cats = data.get("categories", {})
    category = (args.get("category") or "").strip()
    variant = (args.get("variant") or "primary").strip()
    page = (args.get("page") or ctx.active_page or "index.html").strip()
    anchor_selector = (args.get("anchor_selector") or "").strip()
    template_id = re.sub(r"[^a-zA-Z0-9_-]", "", (args.get("template_id") or "main"))[:30] or "main"
    skip_init = bool(args.get("skip_init_snippet"))

    # Discovery mode
    if category in ("?", "list", "help", ""):
        return {
            "ok": True,
            "mode": "list",
            "categories": {
                cid: {
                    "ar_label": c.get("ar_label"),
                    "keywords": c.get("keywords", [])[:5],
                    "variants": list(c.get("variants", {}).keys()),
                }
                for cid, c in cats.items()
            },
            "tip": "استدعِ مرة أخرى مع category و variant.",
        }

    cat = cats.get(category)
    if not cat:
        return {
            "ok": False,
            "error": f"unknown category '{category}'. Use category='?' to list.",
            "available": list(cats.keys()),
        }
    v = (cat.get("variants") or {}).get(variant)
    if not v:
        return {
            "ok": False,
            "error": f"unknown variant '{variant}' for category '{category}'.",
            "available_variants": list(cat.get("variants", {}).keys()),
        }

    # Resolve target page
    if not getattr(ctx, "pages", None):
        ctx.pages = {}
    if page not in ctx.pages:
        # If no pages dict, fall back to current_html on the active_page
        if page == getattr(ctx, "active_page", "index.html") and getattr(ctx, "current_html", ""):
            ctx.pages[page] = ctx.current_html
        else:
            return {
                "ok": False,
                "error": f"page '{page}' not found in project. Available: {list(ctx.pages.keys()) or ['(empty)']}",
            }

    html = _ensure_head_body(ctx.pages[page])
    initial_size = len(html)
    actions: List[str] = []

    # 1. CSS <link>s into <head>
    for css_url in v.get("cdn_css") or []:
        tag = f'<link rel="stylesheet" href="{css_url}" data-zenrex-lib="{v["lib"]}">'
        before = html
        html = _inject_into_head(html, tag)
        if html != before:
            actions.append(f"head: <link {css_url}>")

    # 2. JS <script>s at end of <body>
    for js_url in v.get("cdn_js") or []:
        tag = f'<script src="{js_url}" defer data-zenrex-lib="{v["lib"]}"></script>'
        before = html
        html = _inject_before_body_close(html, tag)
        if html != before:
            actions.append(f"body: <script {js_url}>")

    # 3. Init snippet
    if not skip_init and v.get("init_snippet"):
        snippet = v["init_snippet"].replace("TPL", template_id)
        # Wrap in <script> only if the snippet isn't already a tag (some 3D snippets are mixed HTML+script)
        if snippet.lstrip().startswith("<"):
            block = (
                f'\n<!-- ⚡ inject_library:{v["lib"]} variant={variant} category={category} id={template_id} -->\n'
                + snippet
                + "\n"
            )
        else:
            block = (
                f'\n<!-- ⚡ inject_library:{v["lib"]} variant={variant} category={category} id={template_id} -->\n'
                f"<script>\n{snippet}\n</script>\n"
            )
        if block.strip() in html:
            actions.append("init: (already present, skipped)")
        elif anchor_selector:
            new_html, matched = _inject_at_anchor(html, anchor_selector, block)
            if matched:
                html = new_html
                actions.append(f"init: at {anchor_selector}")
            else:
                html = _inject_before_body_close(html, block)
                actions.append(f"init: before </body> (anchor '{anchor_selector}' not found)")
        else:
            html = _inject_before_body_close(html, block)
            actions.append("init: before </body>")

    # 4. Persist
    ctx.pages[page] = html
    if page == getattr(ctx, "active_page", "index.html"):
        ctx.current_html = html
    ctx.changes_made = getattr(ctx, "changes_made", 0) + 1
    if hasattr(ctx, "_sync_active_page"):
        try:
            ctx._sync_active_page()
        except Exception:
            pass

    # 5. Track usage (best-effort, never crash)
    try:
        db = getattr(ctx, "db", None)
        if db is not None:
            await db.library_usage_stats.update_one(
                {"lib": v["lib"]},
                {
                    "$inc": {"injects": 1},
                    "$set": {
                        "category": category,
                        "variant": variant,
                        "last_used_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "$setOnInsert": {
                        "first_used_at": datetime.now(timezone.utc).isoformat(),
                        "source": "registry",
                    },
                },
                upsert=True,
            )
    except Exception as e:
        logger.warning(f"library_usage_stats update failed: {e}")

    return {
        "ok": True,
        "lib": v["lib"],
        "version": v.get("version"),
        "category": category,
        "variant": variant,
        "page": page,
        "actions": actions,
        "bytes_added": len(html) - initial_size,
        "dom_anchor_hint": v.get("dom_anchor_hint"),
        "use_when": v.get("use_when"),
        "free_tier_note": v.get("free_tier_note"),
        "message": (
            f"✅ {v['lib']}@{v.get('version','?')} ({variant}) "
            f"حُقن في {page}. "
            f"{len(actions)} عمليات. ضع `{v.get('dom_anchor_hint','')}` في صفحتك حيث تريد العنصر."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Auto-promotion: Tavily-discovered libs become "experimental" after 3 wins
# ─────────────────────────────────────────────────────────────────────────────
async def record_library_usage(
    db, project_id: str, lib_name: str, category: Optional[str] = None,
    cdn_js: Optional[List[str]] = None, success: bool = True,
) -> None:
    """Track an externally-discovered library. After 3 successes → suggest
    promotion to the registry. Owner sees these in /admin/lessons → 'pending
    promotions' (future UI)."""
    if not db or not lib_name:
        return
    try:
        await db.library_usage_stats.update_one(
            {"lib": lib_name},
            {
                "$inc": {"successes": 1 if success else 0, "failures": 0 if success else 1, "external_uses": 1},
                "$set": {
                    "last_used_at": datetime.now(timezone.utc).isoformat(),
                    "category_hint": category,
                    "cdn_js": cdn_js or [],
                    "last_project": project_id,
                },
                "$setOnInsert": {
                    "source": "tavily",
                    "first_used_at": datetime.now(timezone.utc).isoformat(),
                },
            },
            upsert=True,
        )
        # Check promotion threshold
        row = await db.library_usage_stats.find_one({"lib": lib_name})
        if row and row.get("source") == "tavily" and row.get("successes", 0) >= 3 and not row.get("promoted"):
            await db.library_promotion_queue.insert_one({
                "lib": lib_name,
                "category_hint": category,
                "cdn_js": cdn_js or [],
                "successes": row.get("successes"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending",
            })
            await db.library_usage_stats.update_one(
                {"lib": lib_name},
                {"$set": {"promoted": True}},
            )
            logger.info(f"🆕 lib '{lib_name}' queued for promotion (3 successful uses).")
    except Exception as e:
        logger.warning(f"record_library_usage error: {e}")
