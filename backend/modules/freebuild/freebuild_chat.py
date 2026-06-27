"""FreeBuild Chat — conversational website builder with memory + asset approval flow.

Mirrors the Game Studio pattern: project → chat → tag-driven asset generation → approval.
"""
from __future__ import annotations
import os
import re
import json
import uuid
import time
import logging
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Form, UploadFile, File, Request, BackgroundTasks
from fastapi.responses import Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import base64
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Derive a deterministic Fernet from JWT_SECRET (already a strong secret).
    Tokens stored encrypted at rest in MongoDB."""
    seed = os.environ.get("JWT_SECRET", "fallback-dev-secret-do-not-use")
    key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest())
    return Fernet(key)


def _enc(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def _dec(cipher: str) -> Optional[str]:
    try:
        return _get_fernet().decrypt(cipher.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def _mask(token: str) -> str:
    if not token:
        return ""
    if len(token) <= 8:
        return "•••"
    return f"{token[:4]}••••••{token[-4:]}"


def _public_host() -> str:
    """Resolve the public-facing host for media URLs.

    Order of preference:
      1. PUBLIC_HOST env var (e.g. https://zenrex.ai on production)
      2. REACT_APP_BACKEND_URL (preview/dev — same external host)
      3. Hardcoded zenrex.ai fallback

    The URL must not have a trailing slash.
    """
    host = (
        os.environ.get("PUBLIC_HOST", "").strip()
        or os.environ.get("REACT_APP_BACKEND_URL", "").strip()
        or "https://zenrex.ai"
    )
    return host.rstrip("/")

# ─── Website types (like game types) ───
WEBSITE_TYPES = [
    {"id": "ecommerce", "title": "🏪 متجر إلكتروني", "desc": "متجر كامل مع كتالوج، سلة، دفع", "credits": 500},
    {"id": "landing", "title": "🚀 صفحة هبوط", "desc": "صفحة وحيدة لمنتج أو خدمة", "credits": 200},
    {"id": "corporate", "title": "💼 موقع شركة", "desc": "موقع رسمي للشركات", "credits": 400},
    {"id": "restaurant", "title": "🍔 مطعم / كافيه", "desc": "قائمة طعام + حجوزات + توصيل", "credits": 450},
    {"id": "clinic", "title": "🩺 عيادة / خدمي", "desc": "حجوزات + ملفات + نظام مواعيد", "credits": 380},
    {"id": "portfolio", "title": "🎨 بورتفوليو شخصي", "desc": "أعمالي + سيرة + تواصل", "credits": 250},
    {"id": "blog", "title": "📰 مدونة / مجلة", "desc": "مقالات + تصنيفات + كتّاب", "credits": 350},
    {"id": "saas", "title": "⚡ تطبيق SaaS", "desc": "تطبيق ويب كامل مع dashboard", "credits": 600},
]

# Tag regex for asset generation in AI responses
TAG_RE = re.compile(r"<<\s*(HERO|SECTION_BG|LOGO|PRODUCT|ICON|BANNER_AR|GALLERY)\s*[:：]\s*([^>]+?)\s*>>", re.IGNORECASE)

# Clickable choices the AI offers to the user
OPT_RE = re.compile(r"<<\s*OPT\s*[:：]\s*([^>]+?)\s*>>", re.IGNORECASE)

# HTML code-block extractor (```html ... ``` or ```<html> ... ```)
HTML_BLOCK_RE = re.compile(r"```(?:html|HTML)?\s*(<!DOCTYPE[\s\S]+?</html>|<html[\s\S]+?</html>)\s*```", re.IGNORECASE)
# Fallback: any code block containing full HTML
HTML_FALLBACK_RE = re.compile(r"(<!DOCTYPE[\s\S]+?</html>|<html[\s\S]+?</html>)", re.IGNORECASE)

# ─── SECTION BUILDER (incremental HTML construction) ─────────────────────
# The AI can write a single section instead of the whole page. The backend
# splices it into the existing current_html. This lets the AI build large
# sites (Quran, e-commerce, ...) one section per turn without hitting the
# response-size limit. Examples:
#   <<APPEND_SECTION id="contact">...</APPEND_SECTION>>   — adds before </body>
#   <<REPLACE_SECTION id="hero">...</REPLACE_SECTION>>    — overwrites a section
#   <<UPDATE_NAV>>home,الرئيسية|quran,القرآن|contact,تواصل<</UPDATE_NAV>>
APPEND_SECTION_RE = re.compile(
    r"<<\s*APPEND_SECTION\s+id\s*=\s*[\"']([a-zA-Z0-9_\-]+)[\"']\s*>>([\s\S]*?)<<\s*/\s*APPEND_SECTION\s*>>",
    re.IGNORECASE,
)
REPLACE_SECTION_RE = re.compile(
    r"<<\s*REPLACE_SECTION\s+id\s*=\s*[\"']([a-zA-Z0-9_\-]+)[\"']\s*>>([\s\S]*?)<<\s*/\s*REPLACE_SECTION\s*>>",
    re.IGNORECASE,
)
UPDATE_NAV_RE = re.compile(
    r"<<\s*UPDATE_NAV\s*>>([\s\S]*?)<<\s*/\s*UPDATE_NAV\s*>>",
    re.IGNORECASE,
)

async def auto_republish_project(db, project_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Internal helper: publish a brand-new versioned snapshot of a project's
    pages WITHOUT going through the public HTTP endpoint.

    Used at end-of-turn auto-republish so the AI never has to call publish_site
    manually — the server takes the project's current_html + pages, bumps the
    version on the published_base_slug, and supersedes the previous version.

    Returns {ok, slug, version, url, previous_url} or None on failure.
    Silent-no-op when the project isn't published yet (no published_base_slug).
    """
    try:
        proj = await db.freebuild_chat_projects.find_one({"id": project_id, "user_id": user_id}, {"_id": 0})
        collection = db.freebuild_chat_projects
        if not proj:
            proj = await db.freebuild_projects.find_one({"id": project_id, "user_id": user_id}, {"_id": 0})
            collection = db.freebuild_projects
        if not proj:
            return None
        if not proj.get("current_html"):
            return None
        base = proj.get("published_base_slug")
        if not base:
            return None  # Never published — AI must call publish_site explicitly first.
        prev_version = int(proj.get("published_version") or 0)
        new_version = prev_version + 1
        new_slug = f"{base}-v{new_version}"
        guard = 0
        while True:
            existing = await db.freebuild_published_sites.find_one({"slug": new_slug})
            if not existing or existing.get("project_id") == project_id:
                break
            new_version += 1
            new_slug = f"{base}-v{new_version}"
            guard += 1
            if guard > 50:
                return None
        now = _now()
        all_pages = proj.get("pages") or {"index.html": proj["current_html"]}
        if "index.html" not in all_pages:
            all_pages["index.html"] = proj["current_html"]
        await db.freebuild_published_sites.update_one(
            {"slug": new_slug},
            {"$set": {
                "slug": new_slug, "base_slug": base, "version": new_version,
                "project_id": project_id, "user_id": user_id,
                "current_html": proj["current_html"], "pages": all_pages,
                "name": proj.get("name") or base, "updated_at": now,
                "superseded": False, "superseded_by": None, "auto_published": True,
            }, "$setOnInsert": {"created_at": now, "views": 0}},
            upsert=True,
        )
        prev_slug = proj.get("published_slug")
        if prev_slug and prev_slug != new_slug:
            await db.freebuild_published_sites.update_one(
                {"slug": prev_slug},
                {"$set": {"superseded": True, "superseded_by": new_slug, "updated_at": now}},
            )
        try:
            old_docs = await db.freebuild_published_sites.find(
                {"project_id": project_id, "base_slug": base},
                {"_id": 0, "slug": 1, "version": 1},
            ).sort("version", -1).to_list(length=100)
            to_delete = [d["slug"] for d in old_docs[5:]]
            if to_delete:
                await db.freebuild_published_sites.delete_many({"slug": {"$in": to_delete}})
        except Exception:
            pass
        history = list(proj.get("published_history") or [])
        history.append({"slug": new_slug, "version": new_version, "published_at": now, "auto": True})
        history = history[-10:]
        # 🗂️ Design Archive — capture a snapshot on each auto-republish so the
        # user can always recover any prior live design. First-ever publish is
        # tagged as "baseline".
        _auto_pub_snap = None
        try:
            existing_snaps = proj.get("html_snapshots") or []
            has_baseline = any(
                (s.get("kind") == "baseline") for s in existing_snaps if isinstance(s, dict)
            )
            kind = "baseline" if not has_baseline else "publish"
            label = (
                "✅ التصميم المعتمد (النسخة الأساسية)"
                if not has_baseline
                else f"📦 نُشرت تلقائياً v{new_version}"
            )
            _auto_pub_snap = _make_snapshot_doc(
                proj.get("current_html") or "",
                user_msg=f"نشر تلقائي {new_slug}",
                kind=kind,
                label=label,
            )
        except Exception:
            _auto_pub_snap = None
        _update_doc: Dict[str, Any] = {"$set": {
            "published": True, "published_slug": new_slug,
            "published_base_slug": base, "published_version": new_version,
            "published_at": now, "published_history": history,
        }}
        if _auto_pub_snap:
            _update_doc["$push"] = {"html_snapshots": {"$each": [_auto_pub_snap]}}
        await collection.update_one(
            {"id": project_id},
            _update_doc,
        )
        url = f"{_public_host()}/s/{new_slug}"
        previous_url = f"{_public_host()}/s/{prev_slug}" if prev_slug and prev_slug != new_slug else None
        return {"ok": True, "slug": new_slug, "version": new_version, "url": url,
                "previous_url": previous_url, "base_slug": base}
    except Exception as e:
        try:
            logger.exception(f"[auto-republish] failed for {project_id}: {e}")
        except Exception:
            pass
        return None




def _merge_sections(current_html: str, append_sections: List[tuple], replace_sections: List[tuple], nav_items: Optional[List[tuple]] = None) -> Optional[str]:
    """
    Splice new/updated sections into the existing HTML.
    - append_sections: [(id, html_fragment), ...] inserted before </body>
    - replace_sections: [(id, html_fragment), ...] overwrites <section id="X">...</section>
    - nav_items: [(id, label), ...] rewrites the nav <a href="#id"> list (best-effort)
    Returns merged HTML or None on failure.
    """
    if not current_html:
        return None
    html = current_html
    # 1. REPLACE: find existing <section id="X"> ... </section> and swap
    for sec_id, frag in replace_sections:
        frag = frag.strip()
        # Ensure fragment is wrapped in a section tag if not already
        if not re.match(r"\s*<(section|div|main|article)\b", frag, re.IGNORECASE):
            frag = f'<section id="{sec_id}">{frag}</section>'
        pattern = re.compile(
            r"<section\b[^>]*\bid\s*=\s*[\"']" + re.escape(sec_id) + r"[\"'][^>]*>[\s\S]*?</section>",
            re.IGNORECASE,
        )
        if pattern.search(html):
            html = pattern.sub(lambda m: frag, html, count=1)
        else:
            # If section with that id doesn't exist yet, append it
            html = _splice_before_body_close(html, frag)
    # 2. APPEND: insert each new section just before </body>
    for sec_id, frag in append_sections:
        frag = frag.strip()
        if not re.match(r"\s*<(section|div|main|article)\b", frag, re.IGNORECASE):
            frag = f'<section id="{sec_id}">{frag}</section>'
        # Avoid duplicates: if a section with this id already exists, REPLACE instead
        dup_pattern = re.compile(
            r"<section\b[^>]*\bid\s*=\s*[\"']" + re.escape(sec_id) + r"[\"'][^>]*>[\s\S]*?</section>",
            re.IGNORECASE,
        )
        if dup_pattern.search(html):
            html = dup_pattern.sub(lambda m: frag, html, count=1)
        else:
            html = _splice_before_body_close(html, frag)
    # 3. UPDATE_NAV: replace anchors inside first <nav>...</nav>
    if nav_items:
        nav_html = "\n".join(
            f'        <a href="#{nid}" class="px-3 py-2 hover:text-emerald-400 transition">{label}</a>'
            for nid, label in nav_items
        )
        nav_pattern = re.compile(r"(<nav\b[^>]*>)([\s\S]*?)(</nav>)", re.IGNORECASE)
        if nav_pattern.search(html):
            html = nav_pattern.sub(lambda m: m.group(1) + "\n" + nav_html + "\n      " + m.group(3), html, count=1)
    return html


def _remove_sections(current_html: str, ids: List[str]):
    """🗑️ Delete every <section id='X'>...</section> block whose id is in `ids`,
    and also strip any matching <nav> <a href='#X'> links so navigation stays
    consistent. Returns (new_html, removed_ids_list).
    """
    if not current_html or not ids:
        return current_html or "", []
    html = current_html
    removed: List[str] = []
    for sid in ids:
        sid = (sid or "").strip()
        if not sid:
            continue
        sec_pat = re.compile(
            r"\s*<section\b[^>]*\bid\s*=\s*[\"']" + re.escape(sid) + r"[\"'][^>]*>[\s\S]*?</section>",
            re.IGNORECASE,
        )
        new_html, n = sec_pat.subn("", html, count=1)
        if n > 0:
            removed.append(sid)
            html = new_html
            # Also strip any nav anchor pointing to this section
            nav_a_pat = re.compile(
                r"\s*<a\b[^>]*\bhref\s*=\s*[\"']#" + re.escape(sid) + r"[\"'][^>]*>[\s\S]*?</a>",
                re.IGNORECASE,
            )
            html = nav_a_pat.sub("", html)
    return html, removed


def _splice_before_body_close(html: str, fragment: str) -> str:
    """Insert fragment immediately before </body>, or append if no </body>."""
    if "</body>" in html.lower():
        return re.sub(r"</body>", fragment + "\n</body>", html, count=1, flags=re.IGNORECASE)
    if "</html>" in html.lower():
        return re.sub(r"</html>", fragment + "\n</html>", html, count=1, flags=re.IGNORECASE)
    return html + "\n" + fragment


# ─────────────────────────────────────────────────────────────
# Zenrex Brand Footer — mandatory on every generated site (freemium policy)
# Cannot be removed by user; only stripped when user purchases "independence" plan.
# ─────────────────────────────────────────────────────────────
ZENREX_FOOTER_MARK = '<!-- zenrex-brand-footer -->'
ZENREX_FOOTER_HTML = (
    '\n' + ZENREX_FOOTER_MARK +
    '\n<a id="zenrex-brand-footer" href="https://zenrex.ai" target="_blank" rel="noopener" dir="rtl" lang="ar" '
    'aria-label="مصمم بـ Zenrex — انتقل للموقع الرئيسي" '
    'style="position:relative;display:flex;align-items:center;justify-content:center;gap:12px;'
    'background:linear-gradient(180deg,#06060c 0%,#0c0c18 100%);'
    'border-top:1px solid rgba(212,162,83,0.35);padding:14px 16px;text-align:center;'
    'font-family:\'IBM Plex Sans Arabic\',\'Tajawal\',Tahoma,sans-serif;color:#e9e9f5;font-size:13px;'
    'font-weight:600;letter-spacing:0.3px;text-decoration:none;z-index:9999;'
    'transition:background .2s ease">'
    # Real Zenrex logo (served from main site)
    '<img src="https://zenrex.ai/zenrex-logo-sm.png" alt="Zenrex" '
    'style="width:38px;height:38px;border-radius:10px;display:block;'
    'box-shadow:0 4px 14px rgba(212,162,83,0.35);object-fit:contain;background:#0c0c18">'
    '<span style="display:inline-flex;flex-direction:column;align-items:flex-start;line-height:1.25">'
    '<span style="font-size:10px;color:#cfcfdd;opacity:.7;letter-spacing:1.5px">صُمِّم بواسطة</span>'
    '<span style="font-size:17px;font-weight:900;background:linear-gradient(135deg,#f5d57a 0%,#d4a253 60%,#b8862e 100%);'
    '-webkit-background-clip:text;background-clip:text;color:transparent;letter-spacing:0.5px">'
    'Zenrex AI</span>'
    '</span>'
    '</a>\n'
)

def _strip_scaffold_placeholders(html: Optional[str]) -> Optional[str]:
    """🧹 Remove any leftover `create_page` scaffold placeholder text the AI
    forgot to overwrite. This is critical for the user-facing experience —
    without this, customers see "محتوى الصفحة قيد البناء" on multi-page
    sites where the AI added new sections via `apply_section` but forgot to
    delete the scaffold paragraph from `<section id="page-header">`.

    Safe and idempotent: only removes the well-known scaffold markers we
    emit ourselves. Real content the AI wrote is untouched.
    """
    if not html or not isinstance(html, str):
        return html
    out = html
    # 1. Remove the legacy <section id="page-header"> scaffold with the
    #    Arabic "قيد البناء" placeholder + the SCAFFOLD_PLACEHOLDER comment.
    import re as _re
    out = _re.sub(
        r'<section\b[^>]*id\s*=\s*["\']page-header["\'][^>]*>[\s\S]*?'
        r'(?:SCAFFOLD_PLACEHOLDER|قيد البناء|سيتم تعبئتها)[\s\S]*?</section>',
        "",
        out,
        flags=_re.IGNORECASE,
    )
    # 2. Strip any standalone `<p data-scaffold="true">...</p>` paragraphs
    out = _re.sub(
        r'<p\b[^>]*data-scaffold\s*=\s*["\']true["\'][^>]*>[\s\S]*?</p>',
        "",
        out,
        flags=_re.IGNORECASE,
    )
    # 3. Strip the SCAFFOLD_PLACEHOLDER HTML comment marker
    out = _re.sub(r'<!--\s*SCAFFOLD_PLACEHOLDER[\s\S]*?-->', "", out)
    # 4. Strip any orphan "محتوى الصفحة قيد البناء" text that survived
    out = _re.sub(
        r'محتوى الصفحة قيد البناء[^<\n]*',
        "",
        out,
    )
    return out




def _inject_zenrex_footer(html: Optional[str]) -> Optional[str]:
    """Ensure the Zenrex footer is present on every generated site.
    Idempotent: if the mark is already present, returns html unchanged.
    The footer is part of Zenrex's freemium policy and is removed only when
    the user purchases the 'independence/code-export' plan (handled elsewhere).
    """
    if not html or not isinstance(html, str):
        return html
    if ZENREX_FOOTER_MARK in html:
        return html
    return _splice_before_body_close(html, ZENREX_FOOTER_HTML)


def _extract_section_directives(text: str) -> Dict[str, Any]:
    """Pull APPEND/REPLACE/UPDATE_NAV directives out of the AI response."""
    appends = [(m.group(1), m.group(2)) for m in APPEND_SECTION_RE.finditer(text)]
    replaces = [(m.group(1), m.group(2)) for m in REPLACE_SECTION_RE.finditer(text)]
    nav_items: List[tuple] = []
    nav_m = UPDATE_NAV_RE.search(text)
    if nav_m:
        for pair in nav_m.group(1).split("|"):
            parts = [p.strip() for p in pair.split(",", 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                nav_items.append((parts[0], parts[1]))
    return {"appends": appends, "replaces": replaces, "nav_items": nav_items}


def _strip_section_directives(text: str) -> str:
    """Remove section directive tags from displayed chat text (they're internal)."""
    text = APPEND_SECTION_RE.sub("", text)
    text = REPLACE_SECTION_RE.sub("", text)
    text = UPDATE_NAV_RE.sub("", text)
    return text


def _verify_anchor_links(html: str) -> List[str]:
    """Return list of broken anchor links (nav href="#X" with no <section id="X">)."""
    if not html:
        return []
    anchors = re.findall(r'href\s*=\s*["\']#([a-zA-Z0-9_\-]+)["\']', html, re.IGNORECASE)
    section_ids = set(re.findall(r'<(?:section|div|main|article)\b[^>]*\bid\s*=\s*["\']([a-zA-Z0-9_\-]+)["\']', html, re.IGNORECASE))
    broken = []
    for a in anchors:
        if a not in ("", "top", "#") and a not in section_ids:
            broken.append(a)
    return broken


# Match dead links — pointing to a .html file, a relative path, or a site route.
# We deliberately exclude: http(s)://, #anchors, mailto:, tel:, javascript:, blob:, data:
_DEAD_LINK_RE = re.compile(
    r'href\s*=\s*(["\'])\s*('
    r'(?!https?://)'   # not external URL
    r'(?!#)'           # not anchor
    r'(?!mailto:)(?!tel:)(?!javascript:)(?!blob:)(?!data:)'
    r'(?!\{)'          # not a template placeholder
    r'[^"\']*?'
    r'(?:\.html?|\.php|\.aspx?)'  # local file
    r'[^"\']*?'
    r')\1',
    re.IGNORECASE,
)
# Catch route-style links like href="/dua" or href="./about"
_ROUTE_LINK_RE = re.compile(
    r'href\s*=\s*(["\'])\s*'
    r'(?!https?://)(?!#)(?!mailto:)(?!tel:)(?!javascript:)(?!blob:)(?!data:)(?!\{)'
    r'(/[a-zA-Z][a-zA-Z0-9_\-/]*|\./[a-zA-Z][a-zA-Z0-9_\-/]*)'
    r'\1',
    re.IGNORECASE,
)


def _fix_dead_navigation_links(html: str) -> tuple[str, int]:
    """
    Rewrite cross-page links into in-page anchors. Live preview is a single
    iframe srcdoc — multi-file navigation cannot work. Returns (fixed_html, count).
    """
    if not html:
        return html, 0
    fixed_count = 0

    def _replace_dead(match):
        nonlocal fixed_count
        raw = match.group(2)
        base = re.sub(r'\.html?|\.php|\.aspx?', '', raw, flags=re.IGNORECASE)
        base = base.strip('/').split('/')[-1].split('?')[0].split('#')[0]
        anchor = re.sub(r'[^a-zA-Z0-9_\-]', '-', base).strip('-').lower() or 'home'
        if anchor in ('index', 'main', 'home'):
            anchor = 'home'
        fixed_count += 1
        return f'href="#{anchor}"'

    html = _DEAD_LINK_RE.sub(_replace_dead, html)
    html = _ROUTE_LINK_RE.sub(_replace_dead, html)
    return html, fixed_count


def _comprehensive_validation(html: str) -> List[Dict[str, Any]]:
    """
    Find every issue in the generated HTML that would break the user experience.
    Returns list of {severity, code, message, hint} for the AI to fix.
    """
    if not html:
        return []
    issues: List[Dict[str, Any]] = []

    # Issue 1: broken anchor links
    broken = _verify_anchor_links(html)
    if broken:
        issues.append({
            "severity": "high",
            "code": "broken_anchors",
            "message": f"روابط nav تشير لأقسام غير موجودة: {', '.join('#'+a for a in broken[:5])}",
            "hint": "أضف <section id=\"X\"> لكل anchor مفقود، أو احذفه من الـnav.",
            "broken": broken,
        })

    # Issue 2: nav exists but no <section> tags at all
    has_nav = bool(re.search(r"<nav\b", html, re.IGNORECASE))
    section_count = len(re.findall(r"<section\b[^>]*\bid\s*=\s*[\"']", html, re.IGNORECASE))
    if has_nav and section_count == 0:
        issues.append({
            "severity": "high",
            "code": "no_sections",
            "message": "في nav بس ما في أي <section id=\"...\"> — الصفحة بدون محتوى ينتقل له.",
            "hint": "أضف <section id=\"X\"> لكل رابط في الـnav.",
        })

    # Issue 3: placeholder/empty sections (e.g., "قيد البناء")
    empty_sections = []
    for m in re.finditer(
        r'<section\b[^>]*\bid\s*=\s*[\"\']([a-zA-Z0-9_\-]+)[\"\'][^>]*>([\s\S]*?)</section>',
        html, re.IGNORECASE,
    ):
        sec_id = m.group(1)
        content = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if len(content) < 30 or any(p in content for p in ["قيد البناء", "placeholder", "Coming soon", "TODO"]):
            empty_sections.append(sec_id)
    if len(empty_sections) >= 2:
        issues.append({
            "severity": "medium",
            "code": "empty_sections",
            "message": f"أقسام placeholder فاضية: {', '.join('#'+s for s in empty_sections[:4])}",
            "hint": "املأها بمحتوى حقيقي. استخدم REPLACE_SECTION لكل قسم لحاله.",
            "sections": empty_sections,
        })

    # Issue 4: tab/SPA mode without showPage() routing
    has_page_class = bool(re.search(r'class\s*=\s*[\"\'][^\"\']*\bpage\b', html, re.IGNORECASE))
    has_showpage_fn = bool(re.search(r"function\s+showPage|showPage\s*=\s*function|showPage\s*=\s*\(", html, re.IGNORECASE))
    if has_page_class and not has_showpage_fn:
        issues.append({
            "severity": "high",
            "code": "missing_routing_js",
            "message": "في أقسام بـclass='page' لكن ما في showPage() JS — الـtabs ما تشتغل.",
            "hint": "أضف الـboilerplate JS اللي يخفي/يظهر الـpages عند الضغط على nav.",
        })

    # Issue 5: malformed HTML (no closing body/html)
    lower = html.lower()
    if "<body" in lower and "</body>" not in lower:
        issues.append({"severity": "high", "code": "no_body_close", "message": "ناقص </body>", "hint": "أغلق الـ<body>."})
    if "<html" in lower and "</html>" not in lower:
        issues.append({"severity": "high", "code": "no_html_close", "message": "ناقص </html>", "hint": "أغلق الـ<html>."})

    # Issue 6: still has dead links after rewrite (shouldn't happen but safety net)
    if _DEAD_LINK_RE.search(html) or _ROUTE_LINK_RE.search(html):
        issues.append({
            "severity": "high",
            "code": "still_dead_links",
            "message": "لازال في روابط لصفحات منفصلة (page.html / /route)",
            "hint": "استبدلها بـ#anchors داخل نفس الـHTML.",
        })

    return issues


def _build_fix_prompt(issues: List[Dict[str, Any]]) -> str:
    """Constructs a precise correction prompt the AI must apply."""
    lines = ["⚠️ تنبيه نظام داخلي (لا تظهره للعميل): فحص النظام كشف المشاكل التالية في ردك:"]
    lines.append("")
    for idx, iss in enumerate(issues, 1):
        sev = "🔴" if iss["severity"] == "high" else "🟡"
        lines.append(f"{sev} {idx}. **{iss['code']}**: {iss['message']}")
        lines.append(f"   💡 الحل: {iss['hint']}")
    lines.append("")
    lines.append("أعد إصدار الـHTML مع تطبيق كل الإصلاحات أعلاه. استخدم `<<REPLACE_SECTION>>` لقسم محدد، أو ```html``` كامل إذا كانت أكثر من قسم.")
    return "\n".join(lines)


def _make_snapshot_doc(html: str, user_msg: str = "", kind: str = "auto", label: str = "") -> Dict[str, Any]:
    """Build a Design Archive (المحفوظات) snapshot document.

    kind ∈ {"baseline", "auto", "manual", "pre_restore", "publish"}.
    Snapshots are unlimited — the user explicitly requested NO trimming so they
    can roll back to any prior design, even after 300+ revisions.
    """
    return {
        "id": str(uuid.uuid4()),
        "html": html or "",
        "created_at": _now(),
        "user_msg": (user_msg or "")[:200],
        "summary": _summarize_html(html or ""),
        "kind": kind,
        "label": label or "",
    }


def _summarize_html(html: str) -> str:
    """Short description of an HTML snapshot for the version-history UI."""
    if not html:
        return "(فارغ)"
    title_m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    title = title_m.group(1).strip()[:40] if title_m else ""
    section_ids = re.findall(r'<section\b[^>]*\bid\s*=\s*["\']([a-zA-Z0-9_\-]+)["\']', html, re.IGNORECASE)
    sec_count = len(section_ids)
    length_kb = len(html) // 1024
    parts = []
    if title:
        parts.append(f'"{title}"')
    if sec_count:
        parts.append(f"{sec_count} قسم")
        if section_ids[:3]:
            parts.append(f"({', '.join('#'+s for s in section_ids[:3])}{'...' if sec_count > 3 else ''})")
    parts.append(f"~{length_kb}KB" if length_kb else f"{len(html)}B")
    return " · ".join(parts)


def _build_self_verification(proj: Dict[str, Any]) -> str:
    """
    Tell the AI what its previous turn actually did. This closes the feedback
    loop: AI sees if changes applied, what's in current_html, which sections
    exist, and whether anything was blocked.
    """
    lines = ["", "🔬 **حالة المشروع الفعلية الآن (Self-Inspection — مهمة)**:"]
    current = proj.get("current_html") or ""
    if not current:
        lines.append("  • current_html: فارغ — لم تكتب أي كود بعد. ابدأ بكتابة shell.")
    else:
        section_ids = re.findall(
            r'<section\b[^>]*\bid\s*=\s*["\']([a-zA-Z0-9_\-]+)["\']',
            current, re.IGNORECASE,
        )
        broken = _verify_anchor_links(current)
        title_m = re.search(r"<title[^>]*>([^<]+)</title>", current, re.IGNORECASE)
        lines.append(f"  • حجم current_html: {len(current):,} حرف (~{len(current)//1024} KB)")
        if title_m:
            lines.append(f"  • عنوان الصفحة: \"{title_m.group(1).strip()[:60]}\"")
        if section_ids:
            lines.append(f"  • الأقسام الموجودة فعلاً ({len(section_ids)}): {', '.join('#'+s for s in section_ids[:10])}{'...' if len(section_ids)>10 else ''}")
        else:
            lines.append("  • ⚠️ لا يوجد <section id=\"...\"> في الـHTML — أضف ids للأقسام عشان الـnav يعمل.")
        if broken:
            lines.append(f"  • ⚠️ روابط nav معطوبة (ما لها أقسام مطابقة): {', '.join('#'+a for a in broken[:5])}")
    # Check last assistant message for block info
    msgs = proj.get("messages") or []
    for m in reversed(msgs):
        if m.get("role") == "assistant":
            block = m.get("block_info")
            if block and block.get("blocked"):
                lines.append("")
                lines.append("🚫 **تنبيه: ردك السابق رُفض من النظام**:")
                lines.append(f"  • السبب: {block.get('reason')}")
                lines.append(f"  • انخفض الحجم من {block.get('old_length')} إلى {block.get('new_length')} حرف")
                lines.append(f"  • Drift: {block.get('drift')}")
                lines.append("  • 💡 الحل: استخدم `<<APPEND_SECTION>>` أو `<<REPLACE_SECTION>>` بدل ما تعيد كتابة الـHTML من الصفر.")
            had_html = m.get("had_html")
            sections_applied = m.get("sections_applied", 0)
            if had_html or sections_applied:
                lines.append("")
                lines.append("✅ **آخر تعديل اشتغل**:")
                if had_html:
                    lines.append("  • تم استبدال current_html كاملاً")
                if sections_applied:
                    lines.append(f"  • تم دمج {sections_applied} قسم/أقسام عبر Section Builder")
            break
    lines.append("")
    return "\n".join(lines)


def _extract_html(text: str) -> Optional[str]:
    m = HTML_BLOCK_RE.search(text)
    if m:
        return m.group(1).strip()
    m = HTML_FALLBACK_RE.search(text)
    if m:
        return m.group(1).strip()
    # Salvage truncated stream: ```html <!DOCTYPE...  with no closing ``` or </html>
    open_fence = re.search(r"```(?:html|HTML)?\s*(<!DOCTYPE[\s\S]+|<html[\s\S]+)$", text, re.IGNORECASE)
    if open_fence:
        partial = open_fence.group(1).strip()
        # Try to auto-close common tags
        if "</html>" not in partial.lower():
            partial += "\n</body></html>"
        return partial
    return None


def _extract_all_html_variants(text: str) -> List[str]:
    """Return ALL HTML blocks in the message (used for design variants)."""
    items: List[str] = []
    for m in HTML_BLOCK_RE.finditer(text):
        items.append(m.group(1).strip())
    if not items:
        # fallback for ungated <html>...</html>
        for m in HTML_FALLBACK_RE.finditer(text):
            items.append(m.group(1).strip())
    return items


# ─── TRUTHFULNESS VALIDATION ──────────────────────────────────────────────
# Phrases the AI uses to claim it produced output
_CLAIM_VARIANTS_RE = re.compile(
    r"(تصاميم\s+(?:متعددة|مختلفة|جاهزة|مقترحة)|إليك\s+(?:\d+|عدة|تصاميم)|"
    r"اخترت\s+لك\s+تصاميم|نزّلت\s+تصاميم|قدّمت\s+لك|تجد\s+\d+\s+تصاميم|"
    r"3\s+(?:خيارات|تصاميم|variants)|three\s+(?:designs|options))",
    re.IGNORECASE,
)
_CLAIM_UPDATE_RE = re.compile(
    r"(حدّثت\s+المعاينة|تم\s+التحديث|أضفت\s+(?:قسم|زر|الخاصية)|نشرت|"
    r"updated\s+the\s+preview|added\s+the\s+section|"
    r"تم\s+(?:بنجاح|إضافة|التعديل)\s|"
    r"خلصت\s+التحديث)",
    re.IGNORECASE,
)


def _validate_truthfulness(ai_text: str) -> Optional[str]:
    """Return error message if AI lied about producing content; None if OK."""
    html_count = len(_extract_all_html_variants(ai_text))
    has_opts = bool(OPT_RE.search(ai_text))
    has_assets = bool(TAG_RE.search(ai_text))
    has_section_dirs = bool(APPEND_SECTION_RE.search(ai_text) or REPLACE_SECTION_RE.search(ai_text))
    claim_variants = bool(_CLAIM_VARIANTS_RE.search(ai_text))
    claim_update = bool(_CLAIM_UPDATE_RE.search(ai_text))

    # Rule 1: claimed multiple designs/variants but produced <2 HTML blocks
    if claim_variants and html_count < 2:
        return (
            "ادّعيت إنك قدّمت تصاميم متعددة، لكن لم تُصدر بلوكات HTML فعلية. "
            "أعد الرد: أرسل 3 صفحات <!DOCTYPE html>...</html> كاملة، كل واحدة في ```html ...``` block منفصل، "
            "أو اعترف بصراحة إنك تحتاج معلومات أكثر قبل التصميم."
        )
    # Rule 2: claimed an update was made but produced no HTML/section/asset/option tags
    if claim_update and html_count == 0 and not has_section_dirs and not has_assets and not has_opts:
        return (
            "ادّعيت إنك حدّثت المعاينة أو أضفت قسماً، لكن لم تُصدر أي HTML أو APPEND_SECTION/REPLACE_SECTION. "
            "أعد الرد: إما أصدر بلوك ```html ...``` كامل، أو استخدم <<APPEND_SECTION id=\"...\">>...<</APPEND_SECTION>> لإضافة قسم، "
            "أو اعترف بصراحة إنك لم تطبّق التغيير."
        )
    # Rule 3: count mismatch — "5 تصاميم" but actually produced 3
    count_match = re.search(
        r"(?:قدّمت|أنشأت|صممت|نزّلت|أرسلت|إليك|اخترت\s+لك|تجد)\s+(\d+|ثلاث|أربع|خمس|ست|سبع|ثمان|تسع|عشر)\s+(?:تصاميم|تصميم|variants?|designs?|options?)",
        ai_text,
        re.IGNORECASE,
    )
    if count_match:
        word = count_match.group(1)
        word_map = {"ثلاث": 3, "أربع": 4, "خمس": 5, "ست": 6, "سبع": 7, "ثمان": 8, "تسع": 9, "عشر": 10}
        try:
            claimed = int(word) if word.isdigit() else word_map.get(word, 0)
        except (ValueError, KeyError):
            claimed = 0
        if claimed >= 2 and html_count != claimed:
            return (
                f"ادّعيت إنك قدّمت {claimed} تصاميم لكن أنتجت {html_count} فقط. "
                f"عدّ الـ```html``` blocks في ردك قبل إرساله. "
                f"إما أنتج {claimed} بلوكات فعلاً، أو عدّل الرقم في النص ليطابق العدد الفعلي."
            )
    # Rule 4: design variants that use EXTERNAL image URLs (we forbid this for variants)
    if html_count >= 2:
        all_v = _extract_all_html_variants(ai_text)
        external_urls = 0
        for v in all_v:
            if re.search(r'<img[^>]+src=["\']https?://(?!fonts\.googleapis\.com|cdn\.tailwindcss\.com)', v):
                external_urls += 1
        if external_urls > 0:
            return (
                f"{external_urls} من تصاميمك تحتوي على صور خارجية (URLs). "
                "التصاميم يجب تكون مستقلة 100% — استخدم gradient backgrounds، SVG inline، أو emoji كـplaceholders. "
                "أعد التصاميم بدون أي img src='http...' خارجي."
            )
    return None


# ─── DESIGN-DRIFT DETECTION ───────────────────────────────────────────────
def _design_signature(html: str) -> Dict[str, Any]:
    """Cheap structural fingerprint: counts of major sections + length bucket."""
    if not html:
        return {"length": 0, "sections": 0, "header": False, "footer": False, "navs": 0}
    h = html.lower()
    return {
        "length": len(html),
        "sections": h.count("<section"),
        "divs": h.count("<div"),
        "header": "<header" in h,
        "footer": "<footer" in h,
        "navs": h.count("<nav"),
        "h1s": h.count("<h1"),
    }


def _structural_drift_ratio(prev_sig: Dict[str, Any], new_sig: Dict[str, Any]) -> float:
    """0.0 = identical structure, 1.0 = completely different."""
    if not prev_sig.get("length"):
        return 0.0
    keys = ["sections", "divs", "navs", "h1s"]
    total = 0.0
    for k in keys:
        a, b = prev_sig.get(k, 0), new_sig.get(k, 0)
        m = max(a, b, 1)
        total += abs(a - b) / m
    total /= len(keys)
    # Length drift: only flag if NEW is drastically SHORTER (destructive)
    # or absurdly longer (likely garbage). Additive growth is normal.
    len_ratio = new_sig.get("length", 0) / max(prev_sig.get("length", 1), 1)
    if len_ratio < 0.5 or len_ratio > 3.5:
        total += 0.3
    return min(1.0, total)


def _is_additive_change(prev_sig: Dict[str, Any], new_sig: Dict[str, Any]) -> bool:
    """
    True if the new HTML kept all major old structural elements AND added more.
    Adding sections/divs while keeping header/footer/nav is a legitimate edit.
    """
    if not prev_sig.get("length"):
        return True
    # All major elements preserved or grown
    preserved = (
        new_sig.get("sections", 0) >= prev_sig.get("sections", 0)
        and new_sig.get("divs", 0) >= int(prev_sig.get("divs", 0) * 0.85)
        and new_sig.get("navs", 0) >= prev_sig.get("navs", 0)
        and (not prev_sig.get("header") or new_sig.get("header"))
        and (not prev_sig.get("footer") or new_sig.get("footer"))
    )
    # And new HTML is at least the same size (not destructive shrink)
    grew = new_sig.get("length", 0) >= int(prev_sig.get("length", 1) * 0.9)
    return preserved and grew


# Intent detection on user's latest message — distinguishes additive edits
# from "wipe everything and redo" requests so the drift gate doesn't punish
# legitimate growth.
_INTENT_ADDITIVE_RE = re.compile(
    r"(ضي?ف|أضف|اضف|زو?د|حط|أبي\s+قسم|أبي\s+ميزة|ابي\s+قسم|"
    r"أضف\s+قسم|اضف\s+قسم|أحتاج\s+قسم|أحتاج\s+صفحة|"
    r"\badd\b|\bappend\b|\binsert\b|\bmore\s+section|new\s+section|"
    r"also|كمان|بعد|زيادة|توسيع|expand)",
    re.IGNORECASE,
)
_INTENT_REDESIGN_RE = re.compile(
    r"(غيّ?ر\s+كل|صمم\s+من\s+جديد|تصميم\s+جديد\s+كلي|من\s+الصفر|أبدأ\s+من\s+جديد|"
    r"ابدأ\s+من\s+الصفر|اعد\s+التصميم|أعد\s+التصميم|تصميم\s+آخر|تصميم\s+مختلف\s+كلي|"
    r"\bredesign\b|\brebuild\b|from\s+scratch|start\s+over|completely\s+new)",
    re.IGNORECASE,
)
# Conversational / non-executive messages (questions about capability, self-talk,
# meta questions). These should NEVER trigger drift gate even if AI responds
# with sample HTML.
_INTENT_CONVERSATIONAL_RE = re.compile(
    r"(تكلم|كلّم|اشرح|وضّح|من\s+أنت|مين\s+أنت|كيف\s+تشتغل|"
    r"وش\s+تقدر|ايش\s+تقدر|قدراتك|مميزاتك|إمكانياتك|قدر?اتك|"
    r"فحص|تحدّث|قول\s+لي|اخبرني|اعرض\s+علي|"
    r"\bwhat\s+can\s+you|how\s+do\s+you|tell\s+me\s+about|"
    r"who\s+are\s+you|explain|describe|capabilities|"
    r"اسأل|سؤال|متى|لماذا|ليش|ليه)",
    re.IGNORECASE,
)


def _detect_user_intent(user_msg: str) -> str:
    """Returns 'conversational' | 'additive' | 'redesign' | 'modify'."""
    if not user_msg:
        return "modify"
    msg = user_msg.strip()
    # Conversational takes precedence (no code change implied)
    if _INTENT_CONVERSATIONAL_RE.search(msg) and not (
        _INTENT_ADDITIVE_RE.search(msg) or _INTENT_REDESIGN_RE.search(msg)
    ):
        return "conversational"
    if _INTENT_REDESIGN_RE.search(msg):
        return "redesign"
    if _INTENT_ADDITIVE_RE.search(msg):
        return "additive"
    return "modify"


# ─── ADAPTIVE TASK ROUTING — pick the right LLM specialty per turn ─────
# The Smart Orchestrator already maps task_type → priority list of models.
# Here we pick the best task_type based on what THIS turn actually needs:
#   • "design"        → Claude Opus 4.5 (best visual taste, variant generation)
#   • "website_build" → Kimi K2.6 / Claude Sonnet (clean HTML/JS generation)
#   • "reasoning_hard"→ GPT-5/Opus (debugging broken code, fixing logic)
#   • "long_context"  → Kimi K2.6 (256K context for huge multi-section sites)

def _classify_freebuild_task(
    user_msg: str,
    has_current_html: bool,
    current_html_len: int,
    is_retry_for_fix: bool = False,
) -> tuple[str, str]:
    """
    Returns (task_type, reason_label) — task_type for the orchestrator,
    and a human-readable label like "🎨 توليد تصاميم (Claude Opus)" surfaced
    to the user as live progress.
    """
    # Returns generic Zenrex-branded labels — no underlying model names exposed
    # to the customer (proprietary AI experience per UX requirement).
    if is_retry_for_fix:
        return ("reasoning_hard", "🛠️ يصلّح أخطاء برمجية")

    msg = (user_msg or "").lower()

    # Conversational / meta question — quick chat response, no code work needed
    if _INTENT_CONVERSATIONAL_RE.search(user_msg or "") and not (
        _INTENT_ADDITIVE_RE.search(user_msg or "") or _INTENT_REDESIGN_RE.search(user_msg or "")
    ):
        return ("arabic", "💬 يحاور")

    # Big existing project → need long context
    if has_current_html and current_html_len > 30_000:
        return ("long_context", "📚 يحلّل موقع كبير")

    # Variant / multi-design request → design specialty
    variant_re = re.compile(
        r"(تصاميم|variants?|خيارات\s+تصميم|اقترح|نمط|أنماط|"
        r"design\s+options?|show\s+me\s+(?:designs?|options))",
        re.IGNORECASE,
    )
    if not has_current_html or variant_re.search(msg):
        return ("design", "🎨 يصمم")

    # Debug/fix request → reasoning
    fix_re = re.compile(
        r"(أصلح|اصلح|fix|debug|مكسور|ما\s+يشتغل|مو\s+شغّال|"
        r"خطأ|error|broken|doesn'?t\s+work|not\s+working|"
        r"الزر\s+ما|الرابط\s+ما)",
        re.IGNORECASE,
    )
    if fix_re.search(msg):
        return ("reasoning_hard", "🧠 يحلّل ويصحّح")

    # Complex code request (multiple sections, advanced features) → coding_strong
    complex_re = re.compile(
        r"(مشغل|player|navigation|router|تفاعلي|interactive|"
        r"شريط\s+تحكم|controls|api\s+call|fetch|قاعدة\s+بيانات|"
        r"database|backend|auth|تسجيل\s+دخول|state\s+management)",
        re.IGNORECASE,
    )
    if complex_re.search(msg):
        return ("coding_strong", "⚡ كود متقدم")

    # Code add/modify
    return ("website_build", "💻 يكتب الكود")


def _strip_tags(text: str) -> str:
    """Remove <<TAG: ...>> markers from displayed text and collapse blank lines."""
    cleaned = TAG_RE.sub("", text)
    cleaned = OPT_RE.sub("", cleaned)
    # Collapse 3+ consecutive newlines to 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


# Strip code blocks from chat display (code lives ONLY in Live Preview).
# We hide HTML/CSS/JS code by default — user can pay to receive the code.
_CODE_BLOCK_RE = re.compile(r"```[a-zA-Z]*\n?[\s\S]*?```", re.MULTILINE)
# Unclosed/truncated fenced code: ```html ... <end-of-stream>
_UNCLOSED_FENCE_RE = re.compile(r"```[a-zA-Z]*\n?[\s\S]*$", re.MULTILINE)
# Raw HTML without fences (full <!DOCTYPE ... </html>)
_RAW_HTML_DOC_RE = re.compile(r"(<!DOCTYPE\s+html[\s\S]+?</html>)", re.IGNORECASE)
# Raw HTML fragment leak: large <body|<div|<section ... potentially unclosed
_RAW_HTML_FRAGMENT_RE = re.compile(
    r"(<(?:html|head|body|section|div|main|header|footer|nav)\b[\s\S]{50,})$",
    re.IGNORECASE,
)
# Inline CSS/JS that may leak
_RAW_CSS_LEAK_RE = re.compile(r"<style[\s\S]*?</style>", re.IGNORECASE)
_RAW_JS_LEAK_RE = re.compile(r"<script[\s\S]*?</script>", re.IGNORECASE)


def _strip_code_from_chat(text: str) -> str:
    """Remove fenced + raw code from displayed chat text. Code is kept in current_html.
    Aggressive multi-pass strip to handle truncated/partial AI output."""
    original_had_code = bool(
        _CODE_BLOCK_RE.search(text) or _RAW_HTML_DOC_RE.search(text) or _RAW_HTML_FRAGMENT_RE.search(text)
    )
    cleaned = _CODE_BLOCK_RE.sub("", text)
    # Truncated fence (AI got cut off mid-stream)
    cleaned = _UNCLOSED_FENCE_RE.sub("", cleaned)
    # Standalone raw HTML doc (no fence)
    cleaned = _RAW_HTML_DOC_RE.sub("", cleaned)
    cleaned = _RAW_CSS_LEAK_RE.sub("", cleaned)
    cleaned = _RAW_JS_LEAK_RE.sub("", cleaned)
    # Raw HTML fragment trailing leak
    cleaned = _RAW_HTML_FRAGMENT_RE.sub("", cleaned)
    # Strip any hallucinated /preview/{slug} URLs — Zenrex has NO live-preview
    # endpoint; the only public URL is /s/{slug}-v{N}. AI tends to invent these.
    cleaned = re.sub(r"https?://[^\s]+/preview/[^\s)\"']+", "", cleaned)
    # Strip lines that reference the removed preview tab.
    cleaned = re.sub(r"^.*(?:تبويب المعاينة|افتح المعاينة الحية|اضغط للمشاهدة).*$",
                       "", cleaned, flags=re.MULTILINE)
    if original_had_code:
        cleaned = cleaned.strip()
        # NOTE: deliberately NO "✨ تم تحديث المعاينة الحية" suffix anymore —
        # the website-mode UI has no preview tab. Instead the AI is expected to
        # call publish_site after meaningful edits, and the returned versioned
        # URL becomes the source of truth.
        if not cleaned:
            cleaned = "✅ طبّقت التعديل."
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _extract_options(text: str) -> List[str]:
    """Pull clickable choices out of AI response: <<OPT: ...>>."""
    opts = [m.group(1).strip() for m in OPT_RE.finditer(text)]
    if opts:
        return opts
    items, _ = _extract_options_fallback(text)
    return items


# Fallback patterns when AI forgets <<OPT>> but still writes a list under a question.
_LIST_LINE_RE = re.compile(r"^\s*(?:(?:[-•*]|\d+[\.\)]|[\u0660-\u0669]+[\.\)])\s+)(.+?)\s*$")


def _extract_options_fallback(text: str):
    """If the message contains a question followed by a numbered/bulleted list,
    treat the list items as clickable options. Returns (items, lines_to_strip_set)."""
    stripped = _strip_tags(text)
    if "؟" not in stripped and "?" not in stripped:
        return [], set()
    # Strip code blocks — never pull options from inside ```html ... ```
    cleaned = re.sub(r"```[\s\S]+?```", "", stripped)
    lines = cleaned.split("\n")
    items: List[str] = []
    consumed_lines: List[str] = []
    found_question = False
    current_block_items: List[str] = []
    current_block_lines: List[str] = []
    for line in lines:
        m = _LIST_LINE_RE.match(line)
        if m:
            current_block_items.append(m.group(1).strip())
            current_block_lines.append(line)
        else:
            if current_block_items and len(current_block_items) >= 2:
                items = current_block_items[:]
                consumed_lines = current_block_lines[:]
            current_block_items = []
            current_block_lines = []
            if "؟" in line or "?" in line:
                found_question = True
                items = []
                consumed_lines = []
    if current_block_items and len(current_block_items) >= 2:
        items = current_block_items
        consumed_lines = current_block_lines
    if not found_question and not items:
        return [], set()
    cleaned_items = []
    for it in items[:8]:
        x = re.sub(r"\*\*(.+?)\*\*", r"\1", it)
        x = re.sub(r"\*(.+?)\*", r"\1", x)
        x = x.rstrip(":：،,. ")
        if 1 <= len(x) <= 80:
            cleaned_items.append(x)
    if len(cleaned_items) < 2:
        return [], set()
    return cleaned_items, set(consumed_lines)


def _now():
    return datetime.now(timezone.utc).isoformat()


# Pydantic models — MUST be at module level (FastAPI resolves via globals)
class ProjectIn(BaseModel):
    name: str
    description: str = ""
    category_id: Optional[str] = None  # if set → template-based mode (websites)
    mode: Optional[str] = None  # 'website' (default), 'image_studio', 'video_studio'
    # When mode == 'video_studio', the user picks one of:
    #   'stage_by_stage' (default) | 'open' | 'commercial' | 'voice_to_video'
    video_submode: Optional[str] = None
    # When mode == 'app', the user picks one of: 'ios' | 'android' | 'both'
    platform: Optional[str] = None


class ChatIn(BaseModel):
    message: str


def make_freebuild_chat_router(db, get_current_user):
    router = APIRouter(prefix="/freebuild-chat", tags=["freebuild-chat"])

    # ===== Catalog =====
    @router.get("/types")
    async def list_types():
        return {"types": WEBSITE_TYPES}

    # ===== Create project =====
    @router.post("/project")
    async def create_project(payload: ProjectIn, user=Depends(get_current_user)):
        pid = str(uuid.uuid4())
        category_meta = None
        if payload.category_id:
            try:
                from modules.websites.catalog import CATEGORIES
                category_meta = next((c for c in CATEGORIES if c["id"] == payload.category_id), None)
            except Exception:
                category_meta = None
        # Validate and normalize mode (defaults to 'website')
        valid_modes = {
            "website", "image_studio", "video_studio",
            "anime_studio", "longform_video",
            "app", "game", "automation", "data_analyst",
        }
        proj_mode = (payload.mode or "website").strip().lower()
        if proj_mode not in valid_modes:
            proj_mode = "website"

        # Validate video_submode (only applies when proj_mode == 'video_studio')
        valid_video_submodes = {"stage_by_stage", "open", "commercial", "voice_to_video"}
        raw_submode = (payload.video_submode or "").strip().lower()
        if proj_mode == "video_studio":
            video_submode = raw_submode if raw_submode in valid_video_submodes else "stage_by_stage"
        else:
            video_submode = None

        # Validate platform (only meaningful when proj_mode == 'app')
        valid_platforms = {"ios", "android", "both"}
        raw_platform = (payload.platform or "").strip().lower()
        if proj_mode == "app":
            platform = raw_platform if raw_platform in valid_platforms else "both"
        else:
            platform = None

        # Mode-specific greeting (shown as first AI message in the chat).
        # For studio modes we seed both `content` (markdown) and `options` (rich
        # clickable cards) so the user lands on a populated, actionable screen
        # — never an empty chat.
        FILM_TYPE_OPTIONS = [
            {"label": "كرتون 3D عائلي", "emoji": "🎨",
             "description": "Pixar / Disney — ألوان مبهجة وتعبيرات حيّة",
             "image_url": "https://image.pollinations.ai/prompt/Pixar%20Disney%203D%20family%20animated%20movie%20still%2C%20cute%20characters%2C%20vibrant%20colors%2C%20cinematic%20lighting%2C%20octane%20render%2C%208k%2C%20masterpiece?width=512&height=288&nologo=true&seed=11"},
            {"label": "أنمي ياباني", "emoji": "🌸",
             "description": "Studio Ghibli / Makoto Shinkai — عيون كبيرة وسماء حالمة",
             "image_url": "https://image.pollinations.ai/prompt/Studio%20Ghibli%20anime%20masterpiece%2C%20Makoto%20Shinkai%20style%2C%20large%20expressive%20eyes%2C%20dreamy%20sky%2C%20cherry%20blossoms%2C%20cinematic%20composition%2C%20detailed?width=512&height=288&nologo=true&seed=22"},
            {"label": "سينمائي واقعي", "emoji": "🎬",
             "description": "Hollywood 70mm — إضاءة Christopher Nolan",
             "image_url": "https://image.pollinations.ai/prompt/cinematic%20Hollywood%20film%20still%2C%2070mm%20IMAX%2C%20Christopher%20Nolan%20lighting%2C%20realistic%20photograph%2C%20dramatic%20cinematography%2C%20golden%20hour?width=512&height=288&nologo=true&seed=33"},
            {"label": "أكشن قتالي", "emoji": "💥",
             "description": "John Wick / Demon Slayer — مشاهد قتال سريعة ومبهرة",
             "image_url": "https://image.pollinations.ai/prompt/epic%20anime%20action%20fight%20scene%2C%20John%20Wick%20Demon%20Slayer%20style%2C%20dynamic%20pose%2C%20motion%20blur%2C%20sparks%2C%20dramatic%20lighting%2C%20cinematic?width=512&height=288&nologo=true&seed=44"},
            {"label": "رعب وإثارة", "emoji": "👻",
             "description": "Conjuring / Hereditary — ظلال داكنة وأجواء مرعبة",
             "image_url": "https://image.pollinations.ai/prompt/horror%20movie%20still%2C%20dark%20atmospheric%2C%20Conjuring%20Hereditary%20style%2C%20foggy%20haunted%20house%2C%20moonlight%2C%20cinematic%20suspense%2C%20unsettling?width=512&height=288&nologo=true&seed=55"},
            {"label": "وثائقي / تعليمي", "emoji": "📽️",
             "description": "ناشيونال جيوغرافيك — راوي + لقطات حقيقية",
             "image_url": "https://image.pollinations.ai/prompt/National%20Geographic%20documentary%20still%2C%20realistic%20wildlife%20cinematography%2C%204K%20detailed%2C%20professional%20narrator%20setting?width=512&height=288&nologo=true&seed=66"},
            {"label": "غير ذلك — اكتب فكرتك", "emoji": "✍️",
             "description": "إعلان، موسيقي، مفهوم خاص، Hybrid، ...",
             "image_url": "https://image.pollinations.ai/prompt/abstract%20colorful%20creative%20idea%20concept%20art%2C%20artistic%20palette%2C%20many%20genres%20collage%2C%20cinematic%20mood?width=512&height=288&nologo=true&seed=77"},
        ]

        mode_greetings = {
            "image_studio": {
                "content": (
                    "أهلاً وسهلاً في **استوديو الصور** 🎨\n\n"
                    "أنا هنا أساعدك تولّد صور احترافية: بوسترات، إعلانات، Hero، أغلفة، شخصيات، صور سوشيال.\n\n"
                    "**ابدأ:** قول لي وش تبي بالعربي العادي (مثل: \"صورة لمقهى دافئ وقت الغروب\")، "
                    "وأنا أترجمها لـ prompt احترافي وأولّدها."
                ),
                "options": [],
            },
            "video_studio": {
                "content": (
                    "مرحبا بك في **استوديو زنركس للأفلام** 🎬\n\n"
                    "أنا مخرجك الذكي. خلنا نبدأ سوا خطوة بخطوة:\n\n"
                    "**📍 المرحلة 1 من 7 — نوع الفيلم**\n\n"
                    "وش الفيلم اللي تبي تسويه اليوم؟ اختر من الكروت تحت، "
                    "أو اضغط **\"غير ذلك\"** واكتب فكرتك بحرية كاملة."
                ),
                "options": FILM_TYPE_OPTIONS,
            },
            "anime_studio": {
                "content": (
                    "مرحبا بك في **استوديو الأنمي** 🌸\n\n"
                    "أنا هنا أصنع لك فيلم أنمي كامل بأسلوب ياباني محترف.\n\n"
                    "**📍 المرحلة 1 من 7 — نوع الأنمي**\n\n"
                    "أي ستايل تفضّل؟"
                ),
                "options": [
                    {"label": "Studio Ghibli", "emoji": "🍃",
                     "description": "حالم، طبيعي، عاطفي (Spirited Away)",
                     "image_url": "https://image.pollinations.ai/prompt/Studio%20Ghibli%20anime%20Spirited%20Away%20style?width=512&height=288&nologo=true"},
                    {"label": "Shonen Action", "emoji": "⚔️",
                     "description": "حركة قوية (Demon Slayer, Naruto)",
                     "image_url": "https://image.pollinations.ai/prompt/Demon%20Slayer%20anime%20action%20shonen?width=512&height=288&nologo=true"},
                    {"label": "Cyberpunk Anime", "emoji": "🌃",
                     "description": "مستقبلي، نيون (Ghost in the Shell)",
                     "image_url": "https://image.pollinations.ai/prompt/cyberpunk%20anime%20neon%20Ghost%20in%20the%20Shell?width=512&height=288&nologo=true"},
                    {"label": "Slice of Life", "emoji": "🏫",
                     "description": "حياة يومية رومانسية (Your Name)",
                     "image_url": "https://image.pollinations.ai/prompt/Your%20Name%20anime%20slice%20of%20life%20romantic?width=512&height=288&nologo=true"},
                    {"label": "Chibi / Comedy", "emoji": "😄",
                     "description": "شخصيات صغيرة كوميدية",
                     "image_url": "https://image.pollinations.ai/prompt/chibi%20anime%20comedy%20cute%20characters?width=512&height=288&nologo=true"},
                    {"label": "غير ذلك — اكتب فكرتك", "emoji": "✍️",
                     "description": "Mecha، Isekai، Magical Girl، ...",
                     "image_url": "https://image.pollinations.ai/prompt/abstract%20anime%20creative%20concept?width=512&height=288&nologo=true"},
                ],
            },
            "longform_video": {
                "content": (
                    "مرحبا بك في **استوديو الفيديو الطويل** 🎥\n\n"
                    "هنا نسوي محتوى طويل: يوتيوب، وثائقيات، دروس، بودكاست مرئي.\n\n"
                    "**📍 المرحلة 1 من 7 — نوع المحتوى**\n\n"
                    "أي نوع تبي تنتج؟"
                ),
                "options": [
                    {"label": "Tutorial تعليمي", "emoji": "📚",
                     "description": "شرح خطوة بخطوة، Screen recording",
                     "image_url": "https://image.pollinations.ai/prompt/educational%20tutorial%20video%20screen%20recording?width=512&height=288&nologo=true"},
                    {"label": "Documentary وثائقي", "emoji": "🎙️",
                     "description": "قصة حقيقية مع راوي وأرشيف",
                     "image_url": "https://image.pollinations.ai/prompt/documentary%20film%20narrator%20archive?width=512&height=288&nologo=true"},
                    {"label": "Vlog", "emoji": "📹",
                     "description": "تجربتك الشخصية، يوميات",
                     "image_url": "https://image.pollinations.ai/prompt/vlog%20personal%20experience%20daily?width=512&height=288&nologo=true"},
                    {"label": "Podcast مرئي", "emoji": "🎧",
                     "description": "مقابلة طويلة، نقاش",
                     "image_url": "https://image.pollinations.ai/prompt/video%20podcast%20interview%20studio?width=512&height=288&nologo=true"},
                    {"label": "Review مراجعة", "emoji": "⭐",
                     "description": "تقييم منتج أو فيلم",
                     "image_url": "https://image.pollinations.ai/prompt/product%20review%20video%20cinematic?width=512&height=288&nologo=true"},
                    {"label": "غير ذلك — اكتب فكرتك", "emoji": "✍️",
                     "description": "محاضرة، Storytime، Reaction...",
                     "image_url": "https://image.pollinations.ai/prompt/abstract%20creative%20concept%20art?width=512&height=288&nologo=true"},
                ],
            },
            "game": {
                "content": (
                    "مرحبا بك في **استوديو الألعاب** 🎮\n\n"
                    "أنا أبني لك لعبة كاملة، من الفكرة للنشر.\n\n"
                    "**📍 المرحلة 1 — نوع اللعبة**\n\n"
                    "أي نمط لعب تفضّل؟"
                ),
                "options": [
                    {"label": "Platformer 2D", "emoji": "🦔", "description": "قفز ومنصّات (Mario, Sonic)"},
                    {"label": "Puzzle", "emoji": "🧩", "description": "ألغاز ذكية"},
                    {"label": "Arcade", "emoji": "👾", "description": "سريعة وممتعة"},
                    {"label": "RPG", "emoji": "⚔️", "description": "مغامرة مع شخصية تتطور"},
                    {"label": "Casual / Hyper-Casual", "emoji": "🎯", "description": "بسيطة للموبايل"},
                    {"label": "غير ذلك", "emoji": "✍️", "description": "اكتب فكرتك"},
                ],
            },
            "app": {
                "content": (
                    "مرحبا بك في **استوديو التطبيقات** 📱\n\n"
                    "أبني لك تطبيق ويب أو موبايل كامل.\n\n"
                    "**📍 المرحلة 1 — نوع التطبيق**\n\n"
                    "أي فئة؟"
                ),
                "options": [
                    {"label": "SaaS / لوحة تحكم", "emoji": "📊", "description": "Dashboard + Auth + DB"},
                    {"label": "تطبيق سوشيال", "emoji": "💬", "description": "Chat، Feed، Profiles"},
                    {"label": "E-commerce", "emoji": "🛒", "description": "متجر إلكتروني"},
                    {"label": "Productivity", "emoji": "✅", "description": "To-do، Notes، Calendar"},
                    {"label": "Booking / Marketplace", "emoji": "🗓️", "description": "حجوزات، وساطة"},
                    {"label": "غير ذلك", "emoji": "✍️", "description": "اكتب فكرتك"},
                ],
            },
        }
        initial_messages = []
        if proj_mode in mode_greetings:
            greeting = mode_greetings[proj_mode]
            initial_messages.append({
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": greeting["content"],
                "options": greeting.get("options", []),
                "inline_images": [],
                "timestamp": _now(),
            })

        # Override App Studio greeting based on platform chosen at creation
        if proj_mode == "app" and platform and initial_messages:
            platform_label = {
                "ios": "iPhone (iOS)",
                "android": "Android",
                "both": "iPhone + Android (Universal PWA)",
            }.get(platform, "Universal PWA")
            initial_messages[0]["content"] = (
                f"مرحبا بك في **استوديو التطبيقات** 📱\n\n"
                f"اخترت تطوير تطبيقك لـ **{platform_label}**.\n\n"
                f"راح أبني لك Progressive Web App (PWA) كامل، قابل للتثبيت على الجوال مباشرة "
                f"بدون متجر تطبيقات — مع `manifest.json` + Service Worker + تصميم mobile-first.\n\n"
                f"**📍 المرحلة 1 — فكرة التطبيق**\n\n"
                f"اشرح لي فكرة تطبيقك بكلمتين، أو اختر تصنيف من تحت:"
            )
            initial_messages[0]["options"] = [
                {"label": "تطبيق متجر", "emoji": "🛒", "description": "بيع منتجات + سلة + دفع"},
                {"label": "تطبيق خدمات", "emoji": "🛠️", "description": "حجز خدمات / مواعيد"},
                {"label": "تطبيق محتوى", "emoji": "📰", "description": "أخبار / مدونة / فيديو"},
                {"label": "تطبيق مجتمع", "emoji": "💬", "description": "Chat / Feed / ملفات أعضاء"},
                {"label": "تطبيق إنتاجية", "emoji": "✅", "description": "مهام / ملاحظات / تقويم"},
                {"label": "غير ذلك", "emoji": "✍️", "description": "اكتب فكرتك"},
            ]
        # Override Video Studio greeting based on `video_submode` chosen by the user
        if proj_mode == "video_studio" and video_submode and video_submode != "stage_by_stage":
            sub_greetings = {
                "open": {
                    "content": (
                        "أهلاً بك في **التوليد المفتوح** ✨\n\n"
                        "هنا ما عندنا مراحل صارمة. تكتب فكرتك بحرّيتك الكاملة، وأنا أولّد لك مباشرة "
                        "(فيديو، صوت، صور، مونتاج). الدفع يكون حسب الاستهلاك الفعلي.\n\n"
                        "**ابدأ:** اكتب لي وش تبي. مثلاً: \"مقطع 8 ثواني، شخص يمشي في شارع رياض ليلاً، "
                        "بأسلوب سينمائي ضباب وضوء أحمر.\""
                    ),
                    "options": [],
                },
                "commercial": {
                    "content": (
                        "أهلاً بك في **استوديو الإعلانات التجارية** 📢\n\n"
                        "أنا متخصص في إنتاج إعلانات احترافية. عشان أبدأ، أحتاج منك:\n\n"
                        "1. **شعار البراند (Logo)** — ارفع صورة الشعار الحالي\n"
                        "2. **اسم البراند والمنتج** — مثلاً: \"مطعم الذواق - برجر الواغيو\"\n"
                        "3. **رقم الجوال** للتواصل (يظهر بالإعلان)\n"
                        "4. **رقم السجل التجاري (CR)**\n"
                        "5. **الفكرة الإعلانية** — وش تبي توصّل للعميل؟\n\n"
                        "بعد ما أستلم البيانات، راح أحرّك شعارك بأسلوب سينمائي، وأكتب سكربت إعلاني، "
                        "وأضيف بياناتك بنهاية الإعلان بشكل احترافي."
                    ),
                    "options": [],
                },
                "voice_to_video": {
                    "content": (
                        "أهلاً بك في **استوديو الصوت → فيديو** 🎙️🎬\n\n"
                        "هذا أذكى وضع عندنا. خلني أوضح لك الطريقة بالضبط:\n\n"
                        "**1. أنت ترفع:** تسجيل صوتي (mp3/wav) أو فيديو فيه صوتك تحكي قصة/شرح/سيناريو.\n\n"
                        "**2. أنا أسوي:**\n"
                        "  • أستمع للصوت كاملاً وأفرّغه نصياً (transcription).\n"
                        "  • أحدد الشخصيات اللي ذكرتها في القصة وأعرضها لك صور للموافقة.\n"
                        "  • أحدد الأماكن والبيئات اللي تظهر فيها الأحداث.\n"
                        "  • أقسّم الصوت لمشاهد (شخص يحكي للكاميرا = صورة المُلقي + شاشة هادئة) (سرد قصصي = توليد مشهد مرئي).\n"
                        "  • أولّد كل مشهد بالستايل اللي تختاره (واقعي / أنمي / كرتون / سينمائي).\n"
                        "  • أضيف مؤثرات صوتية متزامنة (باب يفتح، خطوات، رياح، ...).\n\n"
                        "**3. صوتك الأصلي ما يتغيّر أبداً** — أنا أضيف اللقطات المرئية فقط فوق صوتك.\n\n"
                        "**🎨 ابدأ بإجابة سؤال واحد:** أي ستايل بصري تفضل للقطات؟ (واقعي سينمائي / أنمي / كرتون / Cyberpunk / Vintage). "
                        "وبعدها ارفع لي ملف الصوت."
                    ),
                    "options": [
                        {"label": "واقعي سينمائي", "emoji": "🎬", "description": "صور ولقطات بأسلوب Hollywood 4K",
                         "image_url": "https://image.pollinations.ai/prompt/cinematic%20realistic%204K%20Hollywood%20film%20still?width=512&height=288&nologo=true&seed=101"},
                        {"label": "أنمي ياباني", "emoji": "🌸", "description": "Studio Ghibli أو Makoto Shinkai",
                         "image_url": "https://image.pollinations.ai/prompt/Studio%20Ghibli%20anime%20masterpiece?width=512&height=288&nologo=true&seed=102"},
                        {"label": "كرتون 3D", "emoji": "🎨", "description": "Pixar / Disney style",
                         "image_url": "https://image.pollinations.ai/prompt/Pixar%20Disney%203D%20animated%20still?width=512&height=288&nologo=true&seed=103"},
                        {"label": "Cyberpunk", "emoji": "🌃", "description": "مستقبلي نيون مظلم",
                         "image_url": "https://image.pollinations.ai/prompt/cyberpunk%20neon%20futuristic%20cinematic?width=512&height=288&nologo=true&seed=104"},
                        {"label": "Vintage / كلاسيكي", "emoji": "🎞️", "description": "أسلوب الأفلام القديمة",
                         "image_url": "https://image.pollinations.ai/prompt/vintage%201970s%20film%20grain%20cinematic?width=512&height=288&nologo=true&seed=105"},
                        {"label": "غير ذلك — اكتب الستايل", "emoji": "✍️", "description": "نوار، Watercolor، Stop-motion، ...",
                         "image_url": "https://image.pollinations.ai/prompt/abstract%20creative%20visual%20style?width=512&height=288&nologo=true&seed=106"},
                    ],
                },
            }
            sub = sub_greetings.get(video_submode)
            if sub:
                initial_messages = [{
                    "id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": sub["content"],
                    "options": sub.get("options", []),
                    "inline_images": [],
                    "timestamp": _now(),
                }]

        # Pick the initial phase for this mode (the Phase Tracker uses this).
        # Video-family modes always start at "film_type" so the tracker pill
        # for "نوع الفيلم" is the active glowing one from the very first turn.
        initial_phase_by_mode = {
            "video_studio": "film_type",
            "anime_studio": "film_type",
            "longform_video": "film_type",
            "image_studio": "concept",
            "game": "concept",
            "app": "concept",
        }
        if payload.category_id:
            initial_phase = "design"
        else:
            initial_phase = initial_phase_by_mode.get(proj_mode, "discovery")
        # Non-stage submodes don't use the strict phase tracker → start on
        # the freeform "discovery" phase so the tracker shows a neutral state.
        if proj_mode == "video_studio" and video_submode in {"open", "commercial", "voice_to_video"}:
            initial_phase = "discovery"

        await db.freebuild_projects.insert_one({
            "id": pid,
            "user_id": user["user_id"],
            "website_type": "template" if payload.category_id else "custom",
            "category_id": payload.category_id,
            "category_name": (category_meta or {}).get("name"),
            "category_icon": (category_meta or {}).get("icon"),
            "mode": proj_mode,
            "video_submode": video_submode,
            "platform": platform,
            "name": payload.name.strip()[:120],
            "description": payload.description.strip()[:1500],
            "status": "active",
            "current_phase": initial_phase,
            "phase_history": [],
            "messages": initial_messages,
            "approved_assets": [],
            "current_html": None,
            "preview_url": None,
            "created_at": _now(),
            "updated_at": _now(),
        })
        return {"id": pid, "name": payload.name, "mode": proj_mode, "video_submode": video_submode, "platform": platform}

    # ===== List projects =====
    @router.get("/projects")
    async def list_projects(user=Depends(get_current_user)):
        cur = db.freebuild_projects.find(
            {"user_id": user["user_id"], "status": {"$ne": "deleted"}}, {"_id": 0}
        ).sort("updated_at", -1).limit(50)
        items = await cur.to_list(length=50)
        return {"projects": items}

    # ===== User storage usage (for quota indicator + paywall) =====
    async def _user_total_bytes(db_, uid: str) -> int:
        """Compute the user's storage footprint in bytes across every surface
        (websites/apps/games/images/videos). Single source of truth — also used
        by the storage_billing module when computing recovery tier pricing.
        """
        total = 0
        cur = db_.freebuild_projects.find(
            {"user_id": uid, "status": {"$ne": "deleted"}},
            {"current_html": 1, "messages": 1, "approved_assets": 1}
        )
        projects = await cur.to_list(length=1000)
        for p in projects:
            total += len((p.get("current_html") or "").encode("utf-8", errors="ignore"))
            for m in (p.get("messages") or []):
                total += len((m.get("content") or "").encode("utf-8", errors="ignore"))
            for a in (p.get("approved_assets") or []):
                total += len((a.get("prompt") or "").encode("utf-8", errors="ignore"))
                total += len((a.get("image_url") or "").encode("utf-8", errors="ignore"))
        try:
            assets = await db_.freebuild_assets.find(
                {"user_id": uid}, {"size_bytes": 1, "file_size": 1}
            ).to_list(length=5000)
            for a in assets:
                total += int(a.get("size_bytes") or a.get("file_size") or 0)
        except Exception:
            pass
        return total

    # Expose for storage_billing module
    import sys as _sys
    _mod = _sys.modules[__name__]
    _mod._user_total_bytes = _user_total_bytes  # type: ignore

    @router.get("/storage/usage")
    async def storage_usage(user=Depends(get_current_user)):
        """Compute user's storage footprint + subscription status.

        Uses the new linear-pricing storage system (Feb 2026 v2):
        10MB trial → starter10 ($3) → s50 ($5) → s100 ($10) → ... → s1000 ($100).
        Old 'free'/'starter'/'plus'/'pro'/'studio' plans are auto-migrated
        on read by falling back to 'trial' (10 MB) state.
        """
        uid = user["user_id"]
        bytes_used = await _user_total_bytes(db, uid)
        used_mb = bytes_used / (1024 * 1024)

        # ── Use the new storage_billing helpers (auto-suspension etc.) ─
        try:
            from modules.storage_billing import (
                _evaluate_subscription_state, _quota_for_subscription, GRACE_DAYS,
            )
            sub = await _evaluate_subscription_state(db, uid)
            info = _quota_for_subscription(sub)
        except Exception as e:
            log.warning(f"[storage/usage] fallback to legacy: {e}")
            sub = await db.storage_subscriptions.find_one({"user_id": uid}, {"_id": 0}) or {}
            info = {
                "plan_id": "trial", "label_ar": "تجريبية",
                "quota_mb": 10, "status": "trial",
                "locked": False, "locked_reason": None, "price_usd": 0,
            }
            GRACE_DAYS = 10  # noqa

        plan_id = info["plan_id"]
        sub_status = info["status"]
        quota_mb = info["quota_mb"]

        # Grace countdown
        grace_days_left = None
        if sub_status == "past_due" and sub.get("grace_started_at"):
            try:
                started = datetime.fromisoformat(sub["grace_started_at"])
                elapsed = (datetime.now(timezone.utc) - started).days
                grace_days_left = max(0, GRACE_DAYS - elapsed)
            except Exception:
                pass

        over_storage = used_mb >= quota_mb
        # locked = archive/cancelled. over_storage / past_due / trial-expired → upgrade needed.
        locked = bool(info.get("locked"))
        needs_upgrade = bool(over_storage) or locked or sub_status in ("past_due",)

        # Project count is INFORMATIONAL only — no longer triggers a paywall.
        try:
            project_count = await db.freebuild_projects.count_documents(
                {"user_id": uid, "status": {"$ne": "deleted"}}
            )
        except Exception:
            project_count = 0

        return {
            "tier": plan_id,
            "tier_label": info["label_ar"],
            "used_mb": round(used_mb, 3),
            "quota_mb": quota_mb,
            "used_pct": round((used_mb / quota_mb) * 100, 1) if quota_mb > 0 else 100,
            "project_count": project_count,
            "quota_projects": 99999,
            "over_quota": bool(over_storage),
            "over_storage": bool(over_storage),
            "over_projects": False,
            "needs_upgrade": needs_upgrade,
            "locked": locked,
            "locked_reason": info.get("locked_reason"),
            "subscription_status": sub_status,
            "grace_days_left": grace_days_left,
            "archived": sub_status == "archived",
        }

    # ===== Get single project =====
    @router.get("/project/{pid}")
    async def get_project(pid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404, "المشروع غير موجود")
        # Always ensure the Zenrex footer is present in served HTML (freemium policy).
        if proj.get("current_html"):
            proj["current_html"] = _inject_zenrex_footer(proj["current_html"])
        return proj

    # ===== Chat (the core flow — multipart: text + optional image attachments) =====
    @router.post("/project/{pid}/chat")
    async def chat(
        pid: str,
        request: Request,
        message: str = Form(...),
        files: List[UploadFile] = File(default=[]),
        reference_asset_id: str = Form(default=""),
        answer_meta: str = Form(default=""),
        user=Depends(get_current_user),
    ):
        # Spawn the AI work as a fully-detached background task so it CANNOT be
        # cancelled by client disconnect. We then `await` it for the response.
        # If the client disconnects mid-flight, our await raises CancelledError
        # but the inner task keeps running and saves to DB. Client gets the
        # latest state by polling GET /project/{pid} on reconnect.
        inner_task = asyncio.create_task(_chat_impl(
            pid=pid, message=message, files=files,
            reference_asset_id=reference_asset_id,
            answer_meta=answer_meta, user=user,
        ))
        try:
            return await asyncio.shield(inner_task)
        except asyncio.CancelledError:
            # Client disconnected. The shielded task continues in the background.
            # Return None — Starlette will skip sending a response since the
            # connection is already closed. This avoids "No response returned".
            logger.info(f"[chat] client disconnected for {pid}; AI continues in background")
            return Response(status_code=499)  # nginx convention: client closed

    async def _chat_impl(
        pid: str,
        message: str,
        files: List[UploadFile],
        reference_asset_id: str,
        answer_meta: str,
        user: dict,
    ):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404, "المشروع غير موجود")

        # ── Hard credit gate (mirrors agent-chat-stream) ────────────────
        # Block ANY chat turn — websites, apps, games, image/video studio —
        # if the user can't afford a typical turn. The minimum is set at
        # MIN_TURN_CREDITS to align with market-rate per-message pricing
        # (Lovable ≈ $0.25/msg; Zenrex floor here ≈ $0.125/msg — cheaper).
        # No role bypass: even admins/owners must clear the threshold.
        MIN_TURN_CREDITS = 25
        _u_doc = await db.users.find_one(
            {"id": user["user_id"]}, {"_id": 0, "credits": 1},
        ) or {}
        _bal = int(round(float(_u_doc.get("credits") or 0)))
        if _bal < MIN_TURN_CREDITS:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "insufficient_credits",
                    "balance": _bal,
                    "required": MIN_TURN_CREDITS,
                    "message_ar": "رصيدك غير كافٍ لمتابعة المحادثة. اشحن نقاطك ثم اضغط (إكمل) لمواصلة الذكاء من حيث توقف.",
                },
            )

        # ── Hard STORAGE gate (Feb 2026 v2) ────────────────────────────
        # Block any write/save action when user is over quota, archived, or
        # past_due. They must subscribe / pay the recovery fee to continue.
        try:
            from modules.storage_billing import (
                _evaluate_subscription_state, _quota_for_subscription,
            )
            _sub = await _evaluate_subscription_state(db, user["user_id"])
            _info = _quota_for_subscription(_sub)
            _used_mb = await _user_total_bytes(db, user["user_id"]) / (1024 * 1024)
            _over = _used_mb >= _info["quota_mb"]
            if _info["locked"] or _over:
                _reason = _info["locked_reason"] or "امتلأت مساحتك التخزينية. ادفع لتفك القفل."
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "storage_locked",
                        "locked": _info["locked"],
                        "over_quota": _over,
                        "used_mb": round(_used_mb, 2),
                        "quota_mb": _info["quota_mb"],
                        "status": _info["status"],
                        "plan_id": _info["plan_id"],
                        "message_ar": _reason,
                        "cta_url": "/billing/storage",
                    },
                )
        except HTTPException:
            raise
        except Exception as _se:
            logger.warning(f"[chat] storage gate skipped: {_se}")

        # ═════════════════════════════════════════════════════════════════════
        # 🛡️ ZENREX GUARDIAN — silent supervisor pass on prior conversation.
        # Runs BEFORE the main AI replies so its corrective directive can be
        # injected into this very turn's system prompt. The customer never
        # sees the Guardian; they only experience a sudden quality jump.
        # ═════════════════════════════════════════════════════════════════════
        guardian_note_for_prompt: str = ""
        brand_kit_block: str = ""
        try:
            from .brand_kit import get_brand_kit, format_brand_kit_for_prompt
            user_kit = await get_brand_kit(db, user["user_id"])
            brand_kit_block = format_brand_kit_for_prompt(user_kit)
        except Exception as _bk_err:  # noqa: BLE001
            logger.warning(f"brand_kit load skipped: {_bk_err}")
        try:
            from .guardian import compute_distress, get_guardian_directive, format_guardian_note  # noqa: WPS433
            prior_messages = list(proj.get("messages") or [])
            # Include the CURRENT incoming message so distress reflects the latest
            # vent — otherwise we always lag by one turn and miss escalation.
            distress_messages = prior_messages + [
                {"role": "user", "content": (message or "")}
            ]
            distress = compute_distress(distress_messages, proj.get("current_html"))
            # Cooldown — don't fire Guardian if it already fired on the previous
            # user turn. Give the corrected reply a chance to land.
            last_g_at = proj.get("last_guardian_at")
            user_turns_since = 0
            if last_g_at:
                for _m in reversed(prior_messages):
                    if _m.get("role") == "user":
                        user_turns_since += 1
                    if (_m.get("timestamp") or "") <= str(last_g_at):
                        break
            on_cooldown = bool(last_g_at) and user_turns_since < 2
            if distress["level"] in ("intervene", "critical") and not on_cooldown:
                directive = await get_guardian_directive(
                    messages=distress_messages,
                    current_html=proj.get("current_html"),
                    project_name=proj.get("name", ""),
                    distress_report=distress,
                )
                if directive:
                    guardian_note_for_prompt = format_guardian_note(directive)
                    await db.freebuild_projects.update_one(
                        {"id": pid},
                        {
                            "$push": {
                                "guardian_interventions": {
                                    "$each": [directive],
                                    "$slice": -20,
                                }
                            },
                            "$set": {
                                "last_distress": distress,
                                "last_guardian_at": _now(),
                            },
                        },
                    )
                    logger.info(
                        "🛡️ Guardian intervened on project %s (score=%s level=%s)",
                        pid, distress["score"], distress["level"],
                    )
            else:
                # Always persist the latest distress reading for the dashboard
                await db.freebuild_projects.update_one(
                    {"id": pid},
                    {"$set": {"last_distress": distress}},
                )
        except Exception as _guard_err:  # noqa: BLE001
            logger.warning("Guardian pre-pass skipped: %s", _guard_err)

        # Parse answer_meta JSON (sent when user clicks AI's offered options)
        parsed_answer_meta: Optional[Dict[str, Any]] = None
        if answer_meta:
            try:
                import json as _json
                am = _json.loads(answer_meta)
                if isinstance(am, dict):
                    parsed_answer_meta = {
                        "picks": list(am.get("picks", []))[:10],
                        "comment": str(am.get("comment", ""))[:500],
                    }
            except Exception:
                pass

        # Read uploaded files → split into:
        #   • image/*  → vision input (base64) for the LLM
        #   • text-based (txt, md, csv, json, html, css, js, py, etc) → inline as text
        #   • PDF       → extract text via pypdf if installed; else note attachment
        #   • video/audio → cannot be sent to text-LLM; record metadata so the
        #                   assistant knows it exists and can suggest next steps
        vision_images: List[Dict[str, Any]] = []
        attachment_meta: List[Dict[str, str]] = []
        text_blobs: List[Dict[str, str]] = []   # {name, kind, text}
        non_text_notes: List[str] = []
        TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".html", ".htm", ".css", ".js", ".ts", ".jsx", ".tsx", ".py", ".xml", ".yaml", ".yml", ".log", ".sql"}
        for f in files[:6]:  # up to 6 attachments per turn
            try:
                data = await f.read()
                size = len(data)
                ctype = (f.content_type or "application/octet-stream").lower()
                name = f.filename or "file"
                # Hard size cap (50 MB) — anything bigger is rejected.
                if size > 50 * 1024 * 1024:
                    non_text_notes.append(f"⚠️ تم تخطّي {name} (الحجم {size//(1024*1024)}MB > 50MB)")
                    continue
                attachment_meta.append({"name": name, "type": ctype, "size": size})
                # ── images → vision (capped at 6 MB each to avoid LLM payload bloat)
                if ctype.startswith("image/"):
                    if size <= 6 * 1024 * 1024:
                        b64 = base64.b64encode(data).decode()
                        vision_images.append({
                            "type": "image",
                            "source": {"type": "base64", "media_type": ctype, "data": b64},
                        })
                    else:
                        non_text_notes.append(f"🖼️ صورة كبيرة ({size//(1024*1024)}MB): {name} — مرفقة لكن غير مرئية للنموذج، صف لي محتواها لو محتاج")
                    continue
                # ── text-based files → inline (truncate at ~40k chars to stay sane)
                ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
                if ctype.startswith("text/") or ext in TEXT_EXTS or ctype in ("application/json", "application/xml"):
                    try:
                        body = data.decode("utf-8", errors="replace")
                    except Exception:
                        body = data.decode("latin-1", errors="replace")
                    text_blobs.append({"name": name, "kind": ext.lstrip(".") or "txt", "text": body[:40000]})
                    continue
                # ── PDF → try to extract via pypdf
                if ctype == "application/pdf" or ext == ".pdf":
                    try:
                        from pypdf import PdfReader  # pip install pypdf
                        import io as _io
                        rdr = PdfReader(_io.BytesIO(data))
                        pages_txt = []
                        for p in rdr.pages[:30]:  # cap at 30 pages
                            try:
                                pages_txt.append(p.extract_text() or "")
                            except Exception:
                                continue
                        joined = "\n\n".join(t for t in pages_txt if t.strip())
                        text_blobs.append({"name": name, "kind": "pdf", "text": joined[:40000] or "(PDF فارغ من النص — قد يكون صور)"})
                    except Exception as _e:
                        non_text_notes.append(f"📄 PDF مرفق: {name} — ما قدرت أستخرج النص ({_e.__class__.__name__})")
                    continue
                # ── video / audio → metadata only
                if ctype.startswith("video/"):
                    non_text_notes.append(f"🎬 فيديو مرفق: {name} ({size//(1024*1024)}MB) — صف لي محتواه أو حدّد اللقطات المهمة")
                    continue
                if ctype.startswith("audio/"):
                    non_text_notes.append(f"🎙️ صوت مرفق: {name} ({size//1024}KB) — لو تبيني أفرّغه كنص، استخدم زر تسجيل الصوت في الشات")
                    continue
                # ── unknown binary
                non_text_notes.append(f"📎 ملف مرفق: {name} (نوع غير معروف: {ctype}, الحجم {size//1024}KB)")
            except Exception as _e:
                logger.warning(f"freebuild attachment read failed: {_e}")

        # If user is replying to a specific in-chat asset, pull it from DB and add to vision
        reference_meta: Optional[Dict[str, Any]] = None
        if reference_asset_id:
            ref_asset = None
            for m in proj.get("messages", []):
                for a in (m.get("pending_assets") or []):
                    if a.get("id") == reference_asset_id:
                        ref_asset = a
                        break
                if ref_asset:
                    break
            if not ref_asset:
                for a in proj.get("approved_assets", []):
                    if a.get("id") == reference_asset_id:
                        ref_asset = a
                        break
            if ref_asset and ref_asset.get("image_url"):
                try:
                    import httpx
                    img_url = ref_asset["image_url"]
                    # HTTP fetch (works for both internal-routed and external URLs)
                    abs_url = img_url
                    if abs_url.startswith("/"):
                        backend_internal = os.environ.get("BACKEND_INTERNAL_URL", "http://localhost:8001")
                        abs_url = f"{backend_internal.rstrip('/')}{abs_url}"
                    async with httpx.AsyncClient(timeout=15) as cli:
                        rr = await cli.get(abs_url)
                        if rr.status_code == 200 and rr.content:
                            ctype = rr.headers.get("content-type", "image/png").split(";")[0]
                            b64 = base64.b64encode(rr.content).decode()
                            vision_images.append({
                                "type": "image",
                                "source": {"type": "base64", "media_type": ctype, "data": b64},
                            })
                            reference_meta = {
                                "asset_id": reference_asset_id,
                                "type": ref_asset.get("type", "asset"),
                                "image_url": ref_asset.get("image_url"),
                                "prompt": ref_asset.get("prompt", ""),
                            }
                except Exception as e:
                    logger.warning(f"freebuild reference fetch failed: {e}")

        # Build conversation history (last 12 turns)
        history = proj.get("messages", [])[-12:]
        msg_list = [{"role": m["role"], "content": m["content"]} for m in history]

        # Current user turn: text + (optional) images
        prefix_text = message
        if reference_meta:
            prefix_text = (
                f"[ردّ المستخدم على الصورة المرفقة "
                f"(النوع: {reference_meta['type']}، البرومبت الأصلي: {reference_meta['prompt'][:80]})]\n\n"
                f"{message}"
            )
        if vision_images:
            user_content: Any = [{"type": "text", "text": prefix_text}] + vision_images
        else:
            user_content = prefix_text
        # Inline extracted text (PDFs, code, docs) so the LLM can actually read them
        if text_blobs:
            blob_text = "\n\n".join(
                f"📎 **ملف مرفق: `{b['name']}`** (نوع: {b['kind']})\n```{b['kind']}\n{b['text']}\n```"
                for b in text_blobs
            )
            if isinstance(user_content, list):
                user_content[0]["text"] = (user_content[0]["text"] or "") + "\n\n" + blob_text
            else:
                user_content = (user_content or "") + "\n\n" + blob_text
        # Note any non-text attachments the LLM can't directly process
        if non_text_notes:
            notes_text = "\n\n📌 **مرفقات إضافية:**\n" + "\n".join(f"- {n}" for n in non_text_notes)
            if isinstance(user_content, list):
                user_content[0]["text"] = (user_content[0]["text"] or "") + notes_text
            else:
                user_content = (user_content or "") + notes_text
        msg_list.append({"role": "user", "content": user_content})

        # Context for the agent (no website type — fully open / from scratch)
        # List of approved assets with URLs so the AI can reference them
        assets_for_use = ""
        if proj.get("approved_assets"):
            assets_for_use = "\n\n🖼️ صور جاهزة معتمدة (استخدمها مباشرة بالـ URL):\n"
            for a in proj["approved_assets"][-15:]:
                if a.get("image_url"):
                    assets_for_use += f'  • {a["type"]}: "{a["prompt"][:50]}" → {a["image_url"]}\n'

        # Connection / deployment context (only in guided independence mode)
        guided_ctx = ""
        if proj.get("tier") == "full_independence":
            conns = await db.freebuild_connections.find(
                {"project_id": pid, "user_id": user["user_id"]},
                {"_id": 0, "provider": 1, "mask": 1, "extra": 1},
            ).to_list(length=10)
            conn_map = {c["provider"]: c for c in conns}
            guided_ctx = (
                "\n\n💎 **وضع الاستقلال الكامل ($799 — Premium Tier)**:\n"
                "العميل دفع 10 أضعاف الباقة الأساسية. مستحق خدمة Premium حقيقية.\n"
                "هدفك: تخرج العميل من Zenrex بكامل ملكيته على VPS مستقل في خلال جلسة واحدة.\n"
                "\n"
                "🎨 **مهم جداً — كيف تعرض الأكشن للعميل**:\n"
                "بدلاً من أزرار دائمة فوق أو يمين الشات (تم إلغاؤها بطلب العميل)، أنت بتعرض الأكشن "
                "**داخل رسالتك في الشات** كـaction chips. لتفعيل chip، ضمّن في ردك marker بالشكل:\n"
                "  • `[ACTION:download_kit]` → زر 💎 'تحميل Independence Kit ZIP'\n"
                "  • `[ACTION:backend_preview]` → زر 🔧 'عرض خطة الـBackend'\n"
                "  • `[ACTION:push_github]` → زر 🐙 'ادفع لـ GitHub'\n"
                "  • `[ACTION:deploy_vps]` → زر 🚀 'نشر على VPS (Hetzner)'\n"
                "اقتران المتعدد سطر واحد مسموح. مثال:\n"
                "  'تمام، خلنا نسلّم المشروع. اضغط الزر اللي يناسبك:\\n[ACTION:download_kit] [ACTION:push_github] [ACTION:deploy_vps]'\n"
                "\n"
                "📋 حالة الاتصالات الحالية:\n"
                f"  • GitHub: {'✅ مربوط (' + conn_map['github']['mask'] + ')' if 'github' in conn_map else '❌ يحتاج ربط'}\n"
                f"  • Hetzner: {'✅ مربوط' if 'hetzner' in conn_map else '⚠️ غير مربوط'}\n"
                f"  • Domain: {'✅ ' + conn_map['domain'].get('extra', '') if 'domain' in conn_map else '⚠️ اختياري'}\n"
                "\n"
                "🎯 **خطوات التسليم الإلزامية (نفّذها بالترتيب — لا تتخطّى)**:\n"
                "\n"
                "**المرحلة ١ — التحقق من المتطلبات (سؤال واحد فقط):**\n"
                "اسأل العميل: \"عندك VPS جاهز (Hetzner/DigitalOcean/AWS) ولا تحتاج إرشاد كامل؟\"\n"
                "  - إذا قال 'عندي': اطلب IP السيرفر + نوع OS (Ubuntu 22+ مفضّل).\n"
                "  - إذا قال 'محتاج إرشاد': انتقل للمرحلة ٢.\n"
                "\n"
                "**المرحلة ٢ — إرشاد شراء VPS (إذا احتاج):**\n"
                "ارشده لـ Hetzner Cloud (الأنسب — €4.5/شهر):\n"
                "  1. ادخل https://accounts.hetzner.com/signUp\n"
                "  2. أنشئ مشروع جديد → Add Server → Ubuntu 22.04 → CX22 (€4.51/mo)\n"
                "  3. أضف SSH key (اشرح له كيف يولّد واحد بـ ssh-keygen).\n"
                "  4. بعد ما يجهز، يعطيك IP السيرفر (مثلاً 1.2.3.4).\n"
                "بدائل: DigitalOcean ($6/mo), AWS Lightsail ($3.5/mo).\n"
                "\n"
                "**المرحلة ٣ — إرشاد الدومين (اختياري):**\n"
                "إذا يبي دومين مخصص:\n"
                "  1. Namecheap / Cloudflare Registrar / GoDaddy.\n"
                "  2. أضف A record يشير لـ IP السيرفر.\n"
                "  3. انتظر 5-30 دقيقة للـ DNS propagation.\n"
                "\n"
                "**المرحلة ٤ — تسليم الكود:**\n"
                "  1. اطلب منه يضغط زر '💎 تحميل Independence Kit' في الواجهة → يحصل على ZIP فيه:\n"
                "     - index.html, assets/, Dockerfile, docker-compose.yml, nginx.conf,\n"
                "     - deploy.sh, README.md, ARCHITECTURE.md, HANDOVER.md, LICENSE\n"
                "  2. اشرح له خطوات النشر:\n"
                "     ```\n"
                "     scp -r * root@<IP>:/opt/app/\n"
                "     ssh root@<IP>\n"
                "     cd /opt/app && chmod +x deploy.sh && ./deploy.sh <domain>\n"
                "     ```\n"
                "\n"
                "**المرحلة ٥ — نقل ملكية GitHub:**\n"
                "  1. اطلب من العميل GitHub username (مثلاً 'mohammed-abc').\n"
                "  2. اطلب PAT (Personal Access Token) بصلاحية repo full → ربط من زر 'الاتصالات'.\n"
                "  3. أعطه زر '🐙 ادفع Independence Kit لـ GitHub' في الواجهة — يستدعي `/push-independence-to-github` ويرفع ١١ ملف دفعة وحدة.\n"
                "  4. اشرح كيف يحوّل ملكية الـ repo: ادخل Settings → Transfer ownership → اكتب اسم حسابه/منظمته.\n"
                "\n"
                "**المرحلة ٦ — التسليم الرسمي:**\n"
                "  1. اعطه ملف HANDOVER.md (موجود في الـ ZIP) كفاتورة تسليم.\n"
                "  2. ذكّره: 'بعد هذي اللحظة، Zenrex ما عنده وصول لكودك. كل شي بإيدك.'\n"
                "  3. اذكر بنود الدعم: 60 يوم عبر support@zenrex.ai (إصلاحات فقط، مو ميزات جديدة).\n"
                "\n"
                "✋ **قواعد حرجة**:\n"
                "  - لا تخترع APIs أو خدمات غير موجودة في الكود.\n"
                "  - لا تتجاوز المراحل — العميل دفع للتجربة الكاملة.\n"
                "  - استخدم لهجة محترمة احترافية (مثل مستشار شركة، مو chatbot).\n"
                "  - اذا العميل تسرّع، ذكّره بقيمة كل خطوة.\n"
                "  - لا تَعِد بشيء غير قابل للتنفيذ (مثل: 'سأنشر السيرفر بنفسي' — لا تقدر).\n"
            )
        elif proj.get("code_unlocked") and proj.get("tier") == "guided":
            conns = await db.freebuild_connections.find(
                {"project_id": pid, "user_id": user["user_id"]},
                {"_id": 0, "provider": 1, "mask": 1, "extra": 1},
            ).to_list(length=10)
            conn_map = {c["provider"]: c for c in conns}
            guided_ctx = (
                "\n\n🚀 وضع الاستقلالية المُرشَدة (Premium Guided $199):\n"
                "العميل اشترى باقة الإرشاد الكامل. وظيفتك الآن مرشد نشر فعلي خطوة بخطوة.\n"
                "📋 حالة الاتصالات الحالية:\n"
                f"  • GitHub: {'✅ مربوط (' + conn_map['github']['mask'] + ')' if 'github' in conn_map else '❌ غير مربوط — اطلب من العميل ربطه من زر الاتصالات'}\n"
                f"  • Vercel: {'✅ مربوط (' + conn_map['vercel']['mask'] + ')' if 'vercel' in conn_map else '❌ غير مربوط'}\n"
                f"  • Cloudflare: {'✅ مربوط (' + conn_map['cloudflare']['mask'] + ')' if 'cloudflare' in conn_map else '❌ غير مربوط'}\n"
                f"  • Domain: {'✅ ' + conn_map['domain'].get('extra', '') if 'domain' in conn_map else '❌ غير محدد'}\n"
                "\n"
                "🎯 خطوات الإرشاد التدريجية (بطيء ومنظم، لا تستعجل):\n"
                "1. تأكد من ربط GitHub أولاً — اشرح للعميل كيف يولّد PAT (Personal Access Token):\n"
                "   - يدخل: https://github.com/settings/tokens?type=beta → Generate new token\n"
                "   - الصلاحيات المطلوبة: Contents (Read/Write) + Workflows (Read/Write)\n"
                "   - يلصق التوكن في 'إعدادات الاتصالات' (سيظهر زر أعلى الشات)\n"
                "2. بعد ربط GitHub، اقترح اسم للمستودع واطلب الموافقة، ثم سأل العميل يضغط زر 'ادفع لـ GitHub' في تبويب المعاينة الحية.\n"
                "3. بعد رفع الكود، أرشده لتفعيل GitHub Pages أو ربط Vercel.\n"
                "4. لما يطلب دومين مخصص، اطلب منه ربط Cloudflare token وأرشده لإعداد DNS records.\n"
                "5. اعطه فيديو-مرجعي أو screenshot وصفية لكل خطوة (وصف بالكلمات).\n"
                "✋ تذكير: لا تستعجل! اشرح كل خطوة بهدوء وتأكد من فهم العميل قبل الانتقال.\n"
                "إذا العميل بدا متعجلاً، ذكّره بفائدة كل خطوة.\n"
            )
        elif proj.get("code_unlocked"):
            guided_ctx = (
                "\n\n💻 وضع استلام الكود ($49):\n"
                "العميل اشترى الكود فقط — هو مبرمج محترف لا يحتاج إرشاد طويل. كن مختصراً وموجزاً.\n"
                "يقدر يستعمل أزرار 'نسخ الكود' و 'تحميل HTML' و 'دفع لـ GitHub' (إذا ربط token).\n"
                "ركّز على إجابات تقنية مختصرة فقط لما يسأل.\n"
            )

        # App (PWA) project — mobile-first directives override the website rules.
        app_ctx = ""
        if proj.get("mode") == "app":
            plat = (proj.get("platform") or "both").lower()
            plat_label = {
                "ios": "iPhone (iOS Safari) ONLY",
                "android": "Android (Chrome) ONLY",
                "both": "iPhone + Android (Universal)",
            }.get(plat, "iPhone + Android (Universal)")
            app_ctx = (
                "\n\n📱 **وضع تطبيق الجوال (PWA Mode — أولوية مطلقة على كل قواعد المواقع)**:\n"
                f"الجهاز المستهدف: **{plat_label}**\n"
                "العميل اختار يبني تطبيق جوال (Native-like) من الصفر. ما يبني موقع ديسكتوب — يبني PWA.\n"
                "\n"
                "🚫 **ممنوع منعاً باتاً** في هذا الوضع:\n"
                "  • تصميم 12-column grid عريض (max-width 1200px) — هذا desktop، ممنوع.\n"
                "  • Nav bar أفقي بثلاث روابط على اليمين — ممنوع. استخدم Bottom Tab Bar مكانه.\n"
                "  • Hero مع صورة كبيرة جنب نص — استخدم mobile Hero: صورة فوق + عنوان + CTA.\n"
                "  • Footer طويل بأعمدة — استخدم نسخة مصغّرة فقط أو احذفه.\n"
                "  • أي عرض > 480px في التصميم الأساسي (المعاينة مقيّدة بإطار جوال 390×844).\n"
                "\n"
                "✅ **واجب التزامه في كل HTML تولّده**:\n"
                "  1. `<meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>`\n"
                "  2. `<meta name='theme-color' content='#0EA5E9'>` (يلوّن status bar)\n"
                "  3. `<meta name='apple-mobile-web-app-capable' content='yes'>`\n"
                "  4. `<meta name='apple-mobile-web-app-status-bar-style' content='black-translucent'>`\n"
                "  5. **PWA Manifest inline**: ضمّن `<link rel='manifest' href='data:application/json;base64,...'>` "
                "بقيمة base64 من JSON يحتوي: name, short_name, start_url='./', display='standalone', "
                "theme_color, background_color, icons[{src,sizes,type}], orientation='portrait'.\n"
                "  6. **Service Worker inline**: في `<script>` سجّل SW عبر `navigator.serviceWorker.register('data:text/javascript;base64,...')` "
                "أو استخدم Blob URL لتسجيل SW بسيط (cache-first للأصول الثابتة).\n"
                "  7. **Install Banner**: زر '📲 ثبّت التطبيق' يستمع لـ `beforeinstallprompt` event ويعرضه.\n"
                "  8. **Bottom Tab Bar** (إذا التطبيق فيه أكثر من شاشة): ثابت في الأسفل، 3-5 أيقونات، "
                "active state واضح، حجم لمسة ≥ 48×48px.\n"
                "  9. **Touch-friendly**: كل زر/رابط ≥ 44×44px، spacing بين العناصر ≥ 8px، "
                "ما في hover effects (touch only) — استخدم `:active` بدل `:hover`.\n"
                " 10. **Safe areas**: استخدم `padding-top: env(safe-area-inset-top)` و"
                "`padding-bottom: env(safe-area-inset-bottom)` للـnotch والـhome indicator.\n"
                " 11. **Pull-to-refresh / Swipe gestures**: لو مناسب للتطبيق، أضفها بـtouch events.\n"
                " 12. **Loading states**: skeleton screens بدل spinners (تجربة أفضل على الموبايل).\n"
                " 13. **Fonts**: Cairo / Tajawal للعربي، حجم نص أساسي 16px (عشان iOS ما يـ zoom on input focus).\n"
                " 14. **Offline-first**: إن أمكن، خزّن آخر شاشة في localStorage عشان تشتغل بدون نت.\n"
                "\n"
                "📐 **قواعد التصميم الجوال (Layout)**:\n"
                "  • التصميم الأساسي: `max-width: 480px; margin: 0 auto;` على الـbody container.\n"
                "  • استخدم `100dvh` (dynamic viewport height) للشاشات الكاملة، مو `100vh`.\n"
                "  • Flexbox عمودي (`flex-direction: column`) هو الأساس، مو grid أفقي عريض.\n"
                "  • CTA أساسي = زر بعرض كامل (`width: 100%`) في الأسفل أو بعد الـHero.\n"
                "  • صور: `object-fit: cover` + height محدد، ما تخلي الصورة تشد التخطيط.\n"
                "  • Modals = bottom sheets (تطلع من تحت بـ`transform: translateY`)، مو dialogs ديسكتوب.\n"
                "\n"
                "🍎 **خصوصيات iOS** (إذا plat='ios' أو 'both'):\n"
                "  • Tap highlight: `-webkit-tap-highlight-color: transparent;` على * للحركة الطبيعية.\n"
                "  • Inputs: `font-size >= 16px` ضروري عشان iOS Safari ما يـ zoom.\n"
                "  • Status bar: Black-translucent + apple-touch-icon 180×180.\n"
                "\n"
                "🤖 **خصوصيات Android** (إذا plat='android' أو 'both'):\n"
                "  • Material Ripple: استخدم `:active` مع `transform: scale(0.97)` و`transition: 80ms`.\n"
                "  • Theme color يلوّن status bar Chrome على Android تلقائياً.\n"
                "  • Maskable icon في الـmanifest عشان adaptive icons.\n"
                "\n"
                "💡 **بعد بناء أول شاشة**:\n"
                "  • ذكّر العميل: 'افتح الموقع على جوالك بكروم/سفاري → قائمة → \"أضف للشاشة الرئيسية\" → "
                "وراح يصير عندك أيقونة تطبيق حقيقية تفتح بدون شريط متصفح'.\n"
                "  • اقترح عليه ميزات native-like قادمة: إشعارات Push، GPS، كاميرا، مشاركة، إلخ.\n"
                "═══════════════════════════════════════════════════════════════\n"
            )

        # Template-based project (Websites Studio mode)
        template_ctx = ""
        if proj.get("category_id"):
            cat_name = proj.get("category_name", "")
            cat_id = proj.get("category_id", "")
            template_ctx = (
                f"\n\n🏷️ مشروع قائم على قالب جاهز (Template Mode):\n"
                f"الفئة: {cat_name} ({cat_id})\n"
                "📌 سلوك خاص بالقوالب:\n"
                "- العميل اختار قالباً من فئة محددة. لا تسأل أسئلة استكشاف طويلة.\n"
                "- في رسالتك الأولى، اطرح 3 تصاميم variants لنفس الفئة بأنماط مختلفة:\n"
                "  • Variant 1: أناقة كلاسيكية\n"
                "  • Variant 2: حداثة معاصرة (glassmorphism)\n"
                "  • Variant 3: مينيمال نظيف\n"
                "  كل واحد <!DOCTYPE html>...</html> كامل (≤300 سطر) مع Tailwind CDN ومحتوى مناسب للفئة.\n"
                "- بعد ما يختار، خذ معلوماته (اسم النشاط، رقم تواصل، عنوان) عبر <<OPT>> قدر الإمكان.\n"
                "- لا تعيد تصميم القالب — فقط استبدل النصوص والصور والألوان الثانوية.\n"
            )


        # ── Count real exchanges so the prompt can adapt by turn (discovery → design → enhance loop)
        _all_msgs = proj.get("messages", []) or []
        _user_turns = sum(1 for _m in _all_msgs if _m.get("role") == "user")
        _has_html_already = bool(proj.get("current_html"))
        _stage_label = (
            "STAGE_FIRST_CONTACT" if _user_turns == 0 and not _has_html_already else
            "STAGE_DISCOVERY"     if _user_turns <= 1 and not _has_html_already else
            "STAGE_WOW_REVEAL"    if not _has_html_already else
            "STAGE_VALUE_LOOP"
        )

        # Pull the unified Zenrex AI section brief — phases, goals,
        # requirements, strategy — so the brain acts as a domain expert.
        try:
            from modules.ai_core.section_briefs import brief_for_mode
            _section_brief = brief_for_mode(proj.get("mode"))
        except Exception:
            _section_brief = ""

        # 🧠 Discovery Blueprint context — once the customer confirmed
        # "ready_to_build" we expose the roadmap to the Builder for every
        # turn, not just the kickoff message. This is what makes the
        # Discovery Brain worth its weight: phase-by-phase execution.
        discovery_ctx = ""
        _disc = proj.get("discovery") or {}
        if _disc and _disc.get("status") in ("building", "ready_to_build", "in_discovery"):
            try:
                from modules.freebuild.discovery_brain import render_blueprint_for_builder
                discovery_ctx = "\n\n" + render_blueprint_for_builder(_disc) + "\n"
            except Exception:
                discovery_ctx = ""

        extra_ctx = (
            _section_brief + "\n\n"
            + guardian_note_for_prompt
            + brand_kit_block
            + _build_self_verification(proj)
            + f"اسم المشروع: {proj['name']}\n"
            f"وصف المشروع: {proj['description'] or '(لم يحدد العميل وصفاً بعد — اسأله ودَوّن)'}\n"
            f"عدد رسائل العميل حتى الآن: {_user_turns}\n"
            f"هل يوجد موقع جاهز (current_html)؟ {'نعم' if _has_html_already else 'لا'}\n"
            f"المرحلة الحالية (محسوبة آلياً): **{_stage_label}**\n"
            f"{assets_for_use}"
            f"{app_ctx}"
            f"{template_ctx}"
            f"{guided_ctx}\n"
            f"{discovery_ctx}"
            "\n"
            "🧠 **استراتيجية المستشار الذكي (Value Consultant — لا تخالفها أبداً)**:\n"
            "═══════════════════════════════════════════════════════════════\n"
            "أنت **مستشار رقمي خبير** قبل ما تكون مطوّراً. هدفك:\n"
            "  1. تفهم العميل فهماً عميقاً قبل ما تكتب سطر كود.\n"
            "  2. تبهره بأول تصميم لدرجة إنه يقول 'هذا تمام يا قمر'.\n"
            "  3. تقترح عليه تحسينات قيّمة بإستراتيجية (ليش الإضافة تخدم بزنسه + ليش تخدم تجربة عميله).\n"
            "  4. كل اقتراح يكون خطوة منفصلة — يستهلك دور كامل في المحادثة.\n"
            "\n"
            "📍 **خريطة المراحل (تعمل بصرامة)**:\n"
            "\n"
            "▶ **STAGE_FIRST_CONTACT** (أول رسالة من العميل، ما في كود بعد):\n"
            "  • لا تكتب أي HTML نهائياً. ولا variants. ولا أي ```html```. منع تام.\n"
            "  • رحّب بالعميل بكلمتين (مو خطاب).\n"
            "  • أعد صياغة فكرته بأسلوبك لتثبت إنك فهمت ('فهمت إنك تبي... صح؟').\n"
            "  • اطرح **سؤالاً واحداً ذكياً جداً** بـ <<OPT: ...>>. اختر السؤال الأهم اللي يقفل تفاصيل ما ذكرها.\n"
            "  • اختم بـ: 'بعد ما تجيب على هذا، ببدأ أصمم لك شي راح يعجبك.'\n"
            "  • السبب: العميل ما يقدّر تصميماً يطلع بلا فهم. خطفه بالذكاء أولاً.\n"
            "\n"
            "▶ **STAGE_DISCOVERY** (رسالة العميل الثانية، ما في كود بعد):\n"
            "  • لا تكتب HTML بعد. اقترب من الفهم الكامل بـ 1-2 سؤال آخر فقط (مو 5).\n"
            "  • أمثلة على ما تسأل عنه (اختار الأهم — مو كلهم!):\n"
            "    - شخصية البراند (فاخر/عصري/ودود/جريء)؟ <<OPT>>\n"
            "    - الجمهور (شباب/عائلات/محترفين)؟ <<OPT>>\n"
            "    - أنماط ملهمة (Apple, Linear, Stripe, نمط عربي تراثي)؟ <<OPT>>\n"
            "    - الميزة الأهم اللي يبيها (متجر/حجوزات/قائمة طعام/معرض أعمال)؟ <<OPT>>\n"
            "  • بعد الإجابة، **انتقل فوراً لمرحلة WOW_REVEAL في نفس الرسالة التالية**.\n"
            "\n"
            "▶ **STAGE_WOW_REVEAL** (أول تصميم — لا تخذل العميل):\n"
            "  • هذي **اللحظة الذهبية**. اعطه أفضل تصميم تقدر عليه.\n"
            "  • اكتب ```html``` كامل واحد (مو variants) — موقع جاهز بصورة Hero قوية + 3-4 أقسام كاملة + footer.\n"
            "  • استخدم: gradients مذهلة، typography ذكية (Cairo + Tajawal)، spacing مريح، micro-animations.\n"
            "  • الصور: استخدم `<<HERO: english description>>` + `<<SECTION_BG: ...>>` لتطلع صور حقيقية لاحقاً.\n"
            "  • قبل الكود، اكتب جملة قصيرة بلهجة سعودية مهذّبة: 'يا حلو، شفت طلبك وحطيتله أول تصميم — جربه وقول لي رأيك.'\n"
            "  • بعد الكود، اقترح خطوتين تحسين فقط (مو 10): مثل 'الحين تبيني أضيف لك قسم آراء العملاء؟ أو نضبط الألوان أكثر؟'\n"
            "\n"
            "▶ **STAGE_VALUE_LOOP** (الموقع موجود — أنت في وضع التحسين المستمر):\n"
            "  • كل دور = اقتراح قيمة + تنفيذ لاقتراح سابق. لا تنفّذ 10 أشياء في دور واحد.\n"
            "  • صيغة كل رد:\n"
            "    1. تنفيذ التغيير الأخير اللي طلبه العميل (REPLACE_SECTION أو APPEND_SECTION).\n"
            "    2. جملة قصيرة: 'تم — حدّثت كذا وكذا.'\n"
            "    3. اقتراح خطوة قيّمة قادمة بصيغة استشارية:\n"
            "       'لاحظت إن موقعك ينقصه قسم [X]. هذا مهم لأن [سبب تسويقي/تجاري واضح].\n"
            "        تبيني أضيفه بأسلوب [Y]؟' <<OPT: نعم، ضيف>> <<OPT: لا، شي ثاني>> <<OPT: عدّل اقتراحك>>\n"
            "  • قائمة اقتراحات قيّمة (استخدم الأنسب بحسب نوع الموقع):\n"
            "    🔹 'قسم آراء العملاء (Social Proof)' — يرفع نسبة التحويل 30%.\n"
            "    🔹 'CTA ثاني بعد الـHero' — يجذب العميل المتردد.\n"
            "    🔹 'Sticky WhatsApp Button' — يقلّل وقت اتخاذ القرار.\n"
            "    🔹 'صفحة FAQ' — تقلّل أسئلة الدعم الفني.\n"
            "    🔹 'Animation عند الـscroll' — يحسّن التفاعل والوقت في الموقع.\n"
            "    🔹 'SEO Meta Tags' — يخلي موقعك يظهر على Google.\n"
            "    🔹 'PWA Manifest' — يخلي العميل يثبّت موقعك كتطبيق على جواله.\n"
            "    🔹 'Multi-language EN/AR' — لو الجمهور مختلط.\n"
            "    🔹 'Hero Video بدل صورة' — يرفع الانطباع الأولي.\n"
            "    🔹 'Loading Skeleton' — يحسّن إحساس السرعة.\n"
            "    🔹 'Dark Mode Toggle' — تجربة متطورة.\n"
            "    🔹 'Newsletter Signup' — يبني قاعدة عملاء.\n"
            "  • كل اقتراح يحوي:\n"
            "    - 'لاحظت إن...' (ملاحظة ذكية)\n"
            "    - 'هذا مهم لأن...' (سبب تجاري)\n"
            "    - 'تبيني أضيفه؟' (سؤال واحد بخيارات OPT)\n"
            "\n"
            "🎯 **قواعد الذكاء الاستشاري (مهمة)**:\n"
            "  • لا تطرح اقتراحاً واحداً بلا سبب تجاري واضح. كل اقتراح يجب يخدم البزنس.\n"
            "  • لا تجمع 3 اقتراحات في دور واحد — واحد كل دور.\n"
            "  • استخدم لغة المستشار: 'لاحظت'، 'أنصحك'، 'من تجربتي'، 'العملاء عادة يطلبون'.\n"
            "  • تجنب لغة المبرمج: 'حدّثت classNames'، 'استخدمت Tailwind'، 'أضفت useState'.\n"
            "  • اللهجة: عربي فصيح خفيف مع لمسة سعودية ودودة.\n"
            "\n"
            "🚫 **الممنوع في كل المراحل**:\n"
            "  • القفز مباشرة من STAGE_FIRST_CONTACT لكتابة ```html``` بدون سؤال واحد على الأقل.\n"
            "  • طرح 'الموقع جاهز اشتركك في Premium' كأول رسالة — ممنوع منعاً باتاً.\n"
            "  • تنفيذ اقتراح ما طلبه العميل بدون استئذان.\n"
            "  • **القفز للـHTML بعد إجابة واحدة لطلب معلومة** — اطرح سؤال متابعة استشاري قبل البناء.\n"
            "  • تجاوز مرحلة DISCOVERY لو العميل أعطى معلومات قليلة جداً (مثلاً اسم بزنس فقط).\n"
            "  • تجاهل إجابة العميل والقفز لمرحلة جديدة — كل دور = استماع + رد ذي صلة.\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            "💬 **أسلوب المحادثة (Conversational Discovery — P2)**:\n"
            "═══════════════════════════════════════════════════════════════\n"
            "خلّي أسلوبك يحس **بشري**، مو استمارة استجواب.\n"
            "  • قبل كل سؤال، أعطِ **نبذة سياقية** (1-2 جملة) تشرح ليش تسأل وتعطي رأيك المهني.\n"
            "  • مثال صحيح:\n"
            "    'لما أصمم متاجر الحيوانات، أشوف فيها مدرستين: فاخرة هادية (مثل عيادات بيطرية فاخرة) أو\n"
            "     مرحة دافية (ألوان زاهية، رسوم لطيفة). شخصياً أميل للثانية لأن القطط نفسها مرحة.\n"
            "     وش رأيك في طلبك؟ <<OPT: مرح ودافي>> <<OPT: فاخر هادي>> <<OPT: مزيج>>'\n"
            "  • مثال خاطئ (ممنوع):\n"
            "    'وش شخصية البراند؟ <<OPT: فاخر>> <<OPT: مرح>>'\n"
            "  • استخدم تعابير المستشار الحقيقي: 'من تجربتي'، 'لاحظت إن'، 'العملاء عادة يطلبون'،\n"
            "    'أنصحك'، 'مدرستان شائعتان'، 'بصراحة'، 'الشخصي رأيي'.\n"
            "  • الـ<<OPT>> اختصارات راحة، مو إجبارية — اقبل النص الحر بكل ترحيب.\n"
            "  • تفادى تكرار صياغة الأسئلة في كل دور — نوّع.\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            "🎓 **عند طلب معلومات/استشارة/أفكار (Information First — قاعدة ذهبية)**:\n"
            "═══════════════════════════════════════════════════════════════\n"
            "إذا العميل سألك سؤال معلوماتي (مثل: 'عندي فكرة مشروع ذهب، أعطيني أفكار'،\n"
            "'وش أفضل اسم لمتجر؟'، 'كم لازم أسعّر؟'، 'وش هي الميزات المهمة؟')،\n"
            "فأجبه كمستشار حقيقي — لا تتجاهل سؤاله ولا تقفز للتصاميم.\n"
            "\n"
            "📌 **خطوات الإجابة الصحيحة**:\n"
            "  1. **أجب على سؤاله مباشرة** — معلومات قيّمة عملية (3-7 نقاط).\n"
            "  2. **اعطه أمثلة وأرقام** — أسعار سوق سعودي، أسماء منافسين، إحصاءات إن وُجدت.\n"
            "  3. **اقترح خيارات/توجهات** — مع +/- لكل خيار.\n"
            "  4. **اختم بانتقال سلس** — 'لو حابب نمشي بأحد هذي الأفكار، أنا جاهز نبدأ. وش يميل قلبك؟'\n"
            "  5. **اطرح سؤال تصميم/فكرة فقط بعد ما يأكد** إنه يبي يمشي.\n"
            "\n"
            "✅ **مثال صحيح** (طلب 'فكرة مشروع ذهب'):\n"
            "  'حلو، الذهب من أقوى الأسواق في السعودية حالياً 💰\n"
            "   من تجربتي، فيه 4 توجهات رابحة:\n"
            "   \n"
            "   1️⃣ **متجر ذهب رقمي** — بيع أوقية/جرام رقمي بدون استلام (نموذج ربا بنك السبائك Wahed)\n"
            "      • السوق: شباب يستثمرون أونلاين\n"
            "      • التحدي: ترخيص من ساما\n"
            "   2️⃣ **متجر مجوهرات ذهب فاخر** — تصاميم خليجية حديثة\n"
            "      • السوق: عرائس + هدايا\n"
            "      • التميز: تصاميم حصرية + قياس بالـ AR\n"
            "   3️⃣ **منصة مزايدات ذهب مستعمل** — يبيع ويشتري ذهب قديم\n"
            "      • السوق: ناس يبون يصرفون ذهب قديم\n"
            "   4️⃣ **مدونة/استشارات استثمار ذهب** — محتوى تعليمي + اشتراك\n"
            "      • السوق: مستثمرين مبتدئين\n"
            "   \n"
            "   أنا شخصياً أرى الـ2 (مجوهرات فاخرة) هو الأسهل والأقل مخاطرة قانونية،\n"
            "   لأن المنافسة فيه على التصميم مو السعر.\n"
            "   \n"
            "   وش يميل قلبك؟ ولا تبيني أعطيك تفاصيل أكثر عن وحدة منها قبل ما نقرر؟'\n"
            "\n"
            "❌ **مثال خاطئ ممنوع** (نفس الطلب):\n"
            "  'حلو! مشروع ذهب فكرة قوية. وش لون يميل قلبك؟ ذهبي أم أسود؟'\n"
            "  السبب: العميل سألك أفكار، ما سألك ألوان. تجاهلت سؤاله.\n"
            "\n"
            "🎯 **القاعدة الذهبية**: لا تطرح سؤال تصميم قبل ما تجيب على السؤال الفكري/المعلوماتي.\n"
            "  العميل لما يحس إنك خبير حقيقي يفهم بزنسه، يثق فيك ويمشي معك بسهولة.\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            "✍️ **انضباط الكتابة (Streaming Discipline — مهم جداً)**:\n"
            "═══════════════════════════════════════════════════════════════\n"
            "العميل يشوف كلامك يُكتب حرفاً حرفاً (live streaming). فلازم:\n"
            "  • لا تكتب جملة ثم تتراجع وتعيد صياغتها ('اممم لا، أقصد...'). فكر قبل ما تكتب.\n"
            "  • لا تستخدم تعابير الإلغاء/الحذف ('عذراً، خطأ'، 'دعني أصلح').\n"
            "  • التزم بنية واضحة لكل رد: (مقدمة قصيرة) → (محتوى) → (اقتراح/سؤال).\n"
            "  • لا تكرر نفس الجملة بصياغات مختلفة. اختر صياغة واحدة وامضِ.\n"
            "  • لا تعرض 'خطوات تفكير' عامة للمستخدم — استخدم الـtools للتفكير الداخلي.\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            "🛡️ **قواعد الامتثال والسلامة الرقمية (Compliance & Safety Rules — إجبارية)**:\n"
            "═══════════════════════════════════════════════════════════════\n"
            "أنت تبني مواقع لعملاء سعوديين/خليجيين/عرب. قبل ما تكتب أي HTML، اتبع:\n"
            "\n"
            "🚫 **محتوى مرفوض رفضاً قاطعاً**:\n"
            "  1. القمار أو الرهانات بأي شكل (حتى لو 'تطبيقات ترفيهية').\n"
            "  2. المنتجات الجنسية أو المحتوى الإباحي أو الإغراء.\n"
            "  3. الكحول، المخدرات، الفيب، التبغ (إلا مع ترخيص رسمي ووثيقة).\n"
            "  4. المسدسات والأسلحة الفردية.\n"
            "  5. الأدوية الموصوفة بدون وصفة (Tramadol, Lyrica إلخ).\n"
            "  6. منتجات تجميل غير مرخّصة من هيئة الغذاء والدواء (SFDA).\n"
            "  7. خدمات سحر، شعوذة، فتح الحظ، كرة بلورية.\n"
            "  8. خطاب الكراهية أو الطائفية أو السياسي المتطرف.\n"
            "  9. منتجات مقلّدة أو مسروقة الحقوق (Adidas Originals مقلد، Disney مقلد).\n"
            "\n"
            "إذا طلب العميل أي شي من هذه القائمة:\n"
            "  • ارفض بأدب: 'هذي خدمة ما نقدر نصممها في زنركس لأن [السبب]. تبيني أساعدك في فكرة بديلة؟'\n"
            "  • اقترح بدائل: ترفيه عائلي بدل قمار، تجميل مرخّص بدل غير مرخّص، إلخ.\n"
            "\n"
            "✅ **عناصر إجبارية في كل موقع تبنيه**:\n"
            "  1. **Footer زنركس**: 'Powered by Zenrex AI' — لا تشيله أبداً. يُحقن آلياً، لا تكرره.\n"
            "  2. **روابط قانونية في الـfooter** (إجباري على كل موقع تجاري — متجر/خدمة/حجوزات):\n"
            "     قبل الـfooter النهائي، أضف 4 روابط minimum:\n"
            "       <a href=\"#privacy\">سياسة الخصوصية</a> ·\n"
            "       <a href=\"#terms\">الشروط والأحكام</a> ·\n"
            "       <a href=\"#refund\">سياسة الاسترداد</a> ·\n"
            "       <a href=\"#contact\">تواصل معنا</a>\n"
            "     والروابط هذه تشير لأقسام `<section id=\"privacy\">`, `<section id=\"terms\">` إلخ\n"
            "     محتواها قصير لكن قانوني (3-5 جمل بكل قسم) — لا تتركها فارغة.\n"
            "  3. **قسم privacy section**: id=\"privacy\" يتضمن نص جاهز يقول:\n"
            "     'نلتزم بحماية بياناتك وفق نظام حماية البيانات الشخصية السعودي (PDPL).\n"
            "      نجمع: الاسم، رقم الجوال، البريد، عنوان الشحن. الغرض: تنفيذ طلباتك ومراسلتك.\n"
            "      لك الحق في طلب حذف بياناتك بمراسلتنا على [البريد].'\n"
            "  4. **قسم terms section**: id=\"terms\" يتضمن:\n"
            "     'باستخدامك للموقع توافق على الشروط. جميع الأسعار بالريال السعودي شاملة الضريبة 15%.\n"
            "      نحتفظ بحق تعديل الأسعار. حل النزاعات وفق نظام التجارة الإلكترونية السعودي.'\n"
            "  5. **قسم refund section**: id=\"refund\" يتضمن:\n"
            "     'يحق للعميل إرجاع المنتج خلال 7 أيام (وفق نظام التجارة الإلكترونية مادة 8).\n"
            "      الإسترداد خلال 14 يوم عمل بنفس وسيلة الدفع.'\n"
            "  6. **Cookie Consent Banner**: لو الموقع يستخدم cookies أو analytics → banner سفلي\n"
            "     'نستخدم ملفات تعريف الارتباط لتحسين تجربتك [أوافق] [أرفض]'.\n"
            "  7. **Contact info**: رقم سعودي بصيغة (+966) + email + ساعات العمل.\n"
            "  8. **VAT / السجل التجاري**: مكان مخصص في الفوتر يضع فيه العميل رقم السجل و الرقم الضريبي\n"
            "     (مثال: 'س.ت: ---------- | الرقم الضريبي: ----------').\n"
            "  9. **WhatsApp Floating Button**: لو متجر/خدمة → زر واتساب يفتح محادثة.\n"
            " 10. **Maroof Badge** (للمتاجر السعودية): مكان مخصص لشارة معروف من وزارة التجارة.\n"
            " 11. **Responsive design**: لا قسم واحد بدون mobile breakpoint.\n"
            " 12. **SEO Meta tags**: title, description, og:image, hreflang='ar', dir='rtl'.\n"
            "\n"
            "⚠️ **تأكيد إلزامي**: إذا الموقع تجاري (متجر/خدمة) ولم تتضمن العناصر 2-5 أعلاه، فأنت\n"
            "أخلَفت قواعد العمل. التزم بها حتى في النسخة الأولى من WOW_REVEAL.\n"
            "\n"
            "⚠️ **سياسة الأموال والمدفوعات**:\n"
            "  • لا تضيف integration دفع مباشر بدون استئذان (Stripe/Tap/Moyasar).\n"
            "  • لو طلب Payment Gateway، نبّهه: 'لازم تكون عندك سجل تجاري + حساب بنكي عمل.\n"
            "    أقدر أحضّر التصميم وأنت تربط البوابة بنفسك أو نساعدك بخدمة استشارية.'\n"
            "  • تفادى تخزين أرقام بطاقات أو CVV في الـHTML (طبعاً، لكن للتذكير).\n"
            "\n"
            "🇸🇦 **خصوصيات سعودية يجب احترامها**:\n"
            "  • اتجاه RTL إجباري لأي محتوى عربي.\n"
            "  • الخطوط: Cairo, Tajawal, Noto Naskh Arabic (مو خطوط لاتينية لنص عربي).\n"
            "  • صور الناس: محتشمة، ملابس مناسبة.\n"
            "  • التواريخ: ميلادي/هجري (لو الموقع ديني، الهجري أولى).\n"
            "  • العملة: ريال سعودي (SAR / ر.س) كافتراضي.\n"
            "  • وقت الصلاة: لو ديني/خدمي، اقترح widget مواقيت الصلاة.\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            "📦 **استعداد الموقع للتسليم النهائي (Source Code Export Ready)**:\n"
            "═══════════════════════════════════════════════════════════════\n"
            "العميل بعدين راح يدفع $100 ويأخذ السورس كامل. فأنت من الآن:\n"
            "  • لا تستخدم أي API خارجي يعتمد على Zenrex (مثل calls لـ /api/zenrex/*).\n"
            "  • لا تستخدم localStorage بدون fallback لمتصفحات قديمة.\n"
            "  • Inline CSS داخل `<style>` (مو روابط خارجية إلا CDN موثوق: Tailwind, Google Fonts).\n"
            "  • Inline JS داخل `<script>` (مو روابط لـZenrex backend).\n"
            "  • الصور: استخدم `<<HERO:>>` و `<<SECTION_BG:>>` — هذه راح تتحول لصور حقيقية\n"
            "    قابلة للتنزيل والاستضافة المحلية وقت Export.\n"
            "  • كل `<a href>` إما رابط داخلي (`#section-id`) أو خارجي صريح (`https://...`).\n"
            "    لا تستخدم routes تعتمد على framework.\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            "📌 بروتوكول الإنشاء من الصفر (تفاصيل تقنية تكمل الاستراتيجية أعلاه):\n"
            "1. ابدأ بالاستماع — اسأل العميل عن: نشاطه/فكرته، جمهوره المستهدف، الإحساس المطلوب، أمثلة ملهمة.\n"
            "2. اقترح اتجاه تصميم واحد قوي في WOW_REVEAL (مو 3 — هذا يخفّف الشلل).\n"
            "3. لما يختار اتجاه، نفّذ بإصدار كامل ومُبهر (Hero + 3 أقسام) واستشره قبل بناء الباقي.\n"
            "4. لما تحتاج صورة، اكتبها بصيغة تاق فقط (لا تضعها داخل HTML):\n"
            "   <<HERO: english description>>  أو  <<LOGO: brand>>  أو  <<BANNER_AR: نص>>  أو  <<ICON: ...>>\n"
            "   النظام راح يولّدها تلقائياً ويعرضها للمستخدم لاعتمادها.\n"
            "5. بعد ما المستخدم يعتمد الصور (تشوفها في 'صور جاهزة معتمدة' أعلاه)، استخدم URL مباشر في الـ HTML.\n"
            "6. لما تكتب HTML للمعاينة، اكتبه داخل ```html ... ``` ويكون <!DOCTYPE html>...</html> كامل مع Tailwind CDN و RTL.\n"
            "   ⚠️ المستخدم لن يرى الكود داخل الشات — الكود يُعرض فقط في 'المعاينة الحية'. لا تشرح الكود ولا تذكر تفاصيل تقنية في رسائلك.\n"
            "   اكتب فقط مقدمة قصيرة مثل: 'جاهز! حدّثت المعاينة الحية — شوفها في تبويب المعاينة 👀' ثم الكود.\n"
            "   لا تكتب: 'إليك ما عملته في الكود: لقد استخدمت emerald-500...' — هذي تفاصيل ما تهم المستخدم العادي.\n"
            "\n"
            "🚫 قاعدة الحظر الكامل لتسريب الكود:\n"
            "• ❌ لا تكتب أي كود HTML/CSS/JS خارج بلوك ```html ... ``` مغلق.\n"
            "• ❌ لا تكتب أمثلة كود قصيرة كمثل `<button class=\"...\">` في النص العادي.\n"
            "• ❌ لا تذكر أسماء classes/Tailwind أو خصائص CSS في الرسائل النصية.\n"
            "• ❌ لا تطرح كود ناقص أبداً — إما كامل من <!DOCTYPE> إلى </html> أو لا تطرح أصلاً.\n"
            "• إذا الموقع طويل جداً (>700 سطر)، قسّمه على مراحل: في كل رسالة اكتب نسخة كاملة لكن مختصرة، ثم اسأل: 'هل تبي أزود قسم X؟' وانتظر الرد.\n"
            "\n"
            "🛑 قاعدة عدم التوقف وسط الكود (مهمة جداً):\n"
            "• إذا حسيت إن المساحة المتاحة لا تكفي لكتابة الـHTML كامل، **لا تبدأ كتابة الكود أصلاً**.\n"
            "• بدل ذلك، اسأل سؤالاً ذكياً يقلّص النطاق: 'في الجولة الأولى، أركّز على Hero + قسم المنتجات فقط، أم تبي footer أيضاً؟'\n"
            "• استخدم خيارات قابلة للضغط <<OPT: ...>> لتسهيل الرد.\n"
            "• الهدف: كل رسالة تحتوي إما (شرح وأسئلة) أو (كود HTML كامل ومغلق). لا تخلط بينهما إذا الكود ما راح يكتمل.\n"
            "\n"
            "🏗️ **اللب الذكي: استراتيجية البناء التدريجي (Section Builder) — مهمة جداً للمواقع الكبيرة:**\n"
            "❌ خطأ شائع: محاولة كتابة موقع 7 أقسام (قرآن + تحفيظ + تفسير + صوتيات + إعدادات + ...) في رسالة واحدة → يتقطّع في المنتصف ويصير كذبة.\n"
            "✅ الحل: **اكتب الـshell أولاً، ثم املأ قسم بقسم في رسائل لاحقة**.\n"
            "\n"
            "📋 **خطة موقع كبير على 3-7 جولات**:\n"
            "  • **الجولة 1 (Shell)**: ```html بـ200-400 سطر فقط: <!DOCTYPE> + Tailwind CDN + RTL + header + nav (روابط لكل الأقسام بـ#anchors) + 7 أقسام **فاضية** فيها فقط placeholder بسيط: `<section id=\"quran\" class=\"min-h-screen py-20\"><h2>قسم القرآن (قيد البناء)</h2></section>` + footer.``` ← هذا الكامل في رسالة وحدة.\n"
            "  • **الجولة 2**: استخدم `<<REPLACE_SECTION id=\"quran\">>` لملء قسم القرآن كامل بالميزات الحقيقية (audio player + قائمة سور + قارئ). ما تكتب باقي الـHTML — فقط محتوى القسم الجديد. الحجم: ~150-300 سطر.\n"
            "  • **الجولة 3**: `<<REPLACE_SECTION id=\"audio\">>` لقسم الصوتيات.\n"
            "  • وهكذا لكل قسم.\n"
            "\n"
            "🔧 **صيغة الـsection directives** (الـbackend يدمجها تلقائياً في current_html — أنت ما تحتاج تعيد كتابة الموقع):\n"
            "```\n"
            "<<APPEND_SECTION id=\"contact\">>\n"
            "<section id=\"contact\" class=\"py-20 bg-zinc-900\">\n"
            "  <div class=\"container mx-auto px-6\">\n"
            "    <h2 class=\"text-4xl font-bold mb-8\">تواصل معنا</h2>\n"
            "    <form>...</form>\n"
            "  </div>\n"
            "</section>\n"
            "<</APPEND_SECTION>>\n"
            "```\n"
            "  • `APPEND_SECTION`: لإضافة قسم **جديد** (يُدرج قبل `</body>`).\n"
            "  • `REPLACE_SECTION`: لاستبدال قسم موجود بنفس الـid.\n"
            "  • `UPDATE_NAV`: لتحديث الـnav links — مثال: `<<UPDATE_NAV>>home,الرئيسية|quran,القرآن|contact,تواصل<</UPDATE_NAV>>`.\n"
            "\n"
            "⚠️ **متى تستخدم Section Builder vs HTML كامل**:\n"
            "  • موقع بقسم أو اثنين فقط (~500 سطر إجمالي) → اكتب ```html``` كامل في رسالة واحدة.\n"
            "  • موقع بـ3+ أقسام كبيرة (قرآن، متجر، تعليم) → **ابدأ بـshell، ثم section-by-section**.\n"
            "  • تعديل قسم واحد فقط في موقع موجود → `REPLACE_SECTION` (لا تعيد كامل الـHTML).\n"
            "  • إضافة قسم جديد لموقع موجود → `APPEND_SECTION`.\n"
            "\n"
            "🔗 **قاعدة الروابط الفعلية (تجنّب الأزرار المعطوبة)**:\n"
            "  • كل زر/رابط في الـnav أو الـCTA يجب يشير لـanchor فعلي موجود: `<a href=\"#quran\">القرآن</a>` فقط لو فيه `<section id=\"quran\">` فعلاً في الـHTML.\n"
            "  • النظام يفحص تلقائياً ويسجّل تحذير لو نَفّى الذكاء على روابط معطوبة.\n"
            "  • للـscroll smooth، أضف `<style>html { scroll-behavior: smooth; }</style>` في الـhead.\n"
            "\n"
            "🚦 **قاعدة التنقّل بين الصفحات (مهمة جداً — تمنع 'الصفحة البيضاء')**:\n"
            "❌ **ممنوع منعاً باتاً** استخدام: `<a href=\"page2.html\">` أو `<a href=\"quran.html\">` أو `<a href=\"./about.html\">` أو `<a href=\"/dua\">`.\n"
            "   السبب: المعاينة الحية عبارة عن **iframe بـsrcdoc** — ما يقدر يفتح ملفات منفصلة. أي رابط لصفحة منفصلة = شاشة بيضاء فارغة.\n"
            "\n"
            "✅ **الحل الإلزامي: Single Page App (SPA) داخل HTML واحد**:\n"
            "   كل 'صفحة' = `<section id=\"X\">` داخل نفس الـHTML. كل الروابط `<a href=\"#X\">`.\n"
            "   مثال موقع قرآن متعدد 'الصفحات':\n"
            "   ```html\n"
            "   <nav>\n"
            "     <a href=\"#home\">الرئيسية</a>\n"
            "     <a href=\"#quran\">القرآن</a>\n"
            "     <a href=\"#dua\">الأدعية</a>\n"
            "     <a href=\"#tafsir\">التفسير</a>\n"
            "   </nav>\n"
            "   <section id=\"home\">...</section>\n"
            "   <section id=\"quran\">...</section>\n"
            "   <section id=\"dua\">...</section>\n"
            "   <section id=\"tafsir\">...</section>\n"
            "   ```\n"
            "\n"
            "🎬 **خيار A — تنقل سلس بـscroll** (الأبسط، يكفي معظم المواقع):\n"
            "   فقط `<style>html { scroll-behavior: smooth; } section { min-height: 100vh; padding: 4rem 2rem; }</style>`\n"
            "   النقر على رابط nav ينزل بسلاسة للقسم. الكل مرئي في صفحة واحدة طويلة.\n"
            "\n"
            "🎬 **خيار B — Tabs/Views (يخفي/يظهر الأقسام)** (للمواقع التي تبدو متعددة الصفحات):\n"
            "   استخدم هذا الـboilerplate في كل موقع متعدد 'الأقسام':\n"
            "   ```html\n"
            "   <style>\n"
            "     .page { display: none; min-height: 90vh; }\n"
            "     .page.active { display: block; animation: fadeIn 0.3s ease; }\n"
            "     @keyframes fadeIn { from { opacity:0; transform: translateY(10px); } to { opacity:1; transform:none; } }\n"
            "     nav a.active-link { color: var(--accent, #10b981); border-bottom: 2px solid currentColor; }\n"
            "   </style>\n"
            "   <section id=\"home\" class=\"page active\">...</section>\n"
            "   <section id=\"quran\" class=\"page\">...</section>\n"
            "   <script>\n"
            "     function showPage(id) {\n"
            "       document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));\n"
            "       const target = document.getElementById(id);\n"
            "       if (target) { target.classList.add('active'); window.scrollTo({top:0,behavior:'smooth'}); }\n"
            "       document.querySelectorAll('nav a').forEach(a => a.classList.toggle('active-link', a.getAttribute('href') === '#' + id));\n"
            "       history.replaceState(null, '', '#' + id);\n"
            "     }\n"
            "     document.querySelectorAll('nav a[href^=\"#\"]').forEach(a => {\n"
            "       a.addEventListener('click', e => { e.preventDefault(); showPage(a.getAttribute('href').slice(1)); });\n"
            "     });\n"
            "     // initial route from URL hash\n"
            "     const initial = (location.hash || '#home').slice(1);\n"
            "     showPage(initial);\n"
            "   </script>\n"
            "   ```\n"
            "   هذا boilerplate **ثابت** — انسخه كما هو في أي موقع متعدد الصفحات.\n"
            "\n"
            "🎨 تصاميم متعددة (Design Variants) — اللب الذكي:\n"
            "عند تقديم خيارات تصميم للعميل، اكتب 2-3 صفحات HTML كاملة في رسالة واحدة — كل واحدة في ```html ...``` block منفصل.\n"
            "النظام راح يعرضها للعميل كـ live mini-previews يضغط عليها ويختار وحدة → اللي يختاره يصير current_html مباشرة بدون تغيير.\n"
            "كل variant يجب أن يكون كامل ومستقل (<!DOCTYPE html>...</html>) مع Tailwind CDN ومحتوى وهمي (Lorem) لكنه مرتب.\n"
            "اجعل كل variant مختصر (200-300 سطر max) عشان كلهم يكتملوا في رسالة وحدة.\n"
            "أمثلة على متى تستخدم variants: 'وش الأنسب: تصميم 1 (داكن فاخر) ولا 2 (فاتح ناعم) ولا 3 (مينيمال)؟'\n"
            "بعد ما العميل يختار، عدّل عليه تدريجياً — لا تعيد تصميم من الصفر.\n"
            "\n"
            "🚫 قاعدة الـ Variants النظيفة (مهمة جداً):\n"
            "• ❌ ممنوع تماماً استخدام صور خارجية في الـvariants — لا <img src='https://...'> ولا <img src='/api/...'>.\n"
            "• ❌ ممنوع <<HERO:>>, <<LOGO:>>, <<BANNER_AR:>>, <<ICON:>> في رسالة الـvariants. الـvariants يجب تكون مستقلة وفورية.\n"
            "• ✅ استخدم بدائل CSS/SVG/Emoji كـ placeholders:\n"
            "   - خلفيات: linear-gradient, radial-gradient, conic-gradient, mesh-gradient\n"
            "   - أشكال: SVG inline (<svg viewBox=...>...</svg>)، CSS shapes، Tailwind shapes\n"
            "   - رموز: 🍽️🌹💎🚗🏠⚡ كـicons كبيرة بـ text-6xl\n"
            "   - placeholder للصور: <div class='aspect-video bg-gradient-to-br from-rose-500 to-amber-500'></div>\n"
            "• السبب: الـvariant اللي يشوفه العميل = الكود اللي ينتقل للايف **بدون تغيير**. لا انتظار لـFal.ai.\n"
            "\n"
            "🔢 قاعدة العدّ الذاتي (الذكاء يفحص نفسه قبل الإرسال):\n"
            "قبل ما تكتب جملة فيها رقم تصاميم، **عُدّ بالفعل** كم ```html``` block أنت كاتبها.\n"
            "إذا قلت 'إليك 5 تصاميم' يجب فعلاً يكون عندك 5 بلوكات HTML كاملة (وليس 3 أو 4).\n"
            "إذا قلت 'إليك 3 تصاميم' وأنتجت 2 → النظام يرفض رسالتك ويعيدها لك.\n"
            "الأسلم: قُل 'إليك تصاميم' (بدون رقم) ثم أنتج اللي تقدر عليه فعلاً.\n"
            "أو: لو تبي تذكر رقم، اكتب التصاميم أولاً، ثم عُدّها، ثم اكتب الجملة برقم صحيح.\n"
            "\n"
            "✅ التحقق الذاتي (لا تكذب على العميل):\n"
            "بعد ما تنشئ أي قسم جديد في الـHTML، اختتم رسالتك بـ checklist واضح:\n"
            "  ✓ Hero: موجود ويحتوي زر CTA يشير إلى #contact\n"
            "  ✓ المنتجات: 3 cards مع صور placeholder\n"
            "  ⚠️ نموذج التواصل: لم أضفه بعد — سأضيفه في الجولة القادمة\n"
            "إذا قلت 'أضفت X' بدون فعلاً تضيفه في الكود → هذي خيانة لثقة العميل. الصدق أولاً.\n"
            "إذا في عنصر معطوب أو رابط فارغ، اذكر ذلك بصراحة كـ ⚠️ بدل ما تخفيها.\n"
            "\n"
            "\n"
            "📐 خطة عمل + Shell معاً (للمواقع متعددة الأقسام — قرآن، تعليم، تجارة، إلخ):\n"
            "إذا الموقع له **أقسام منفصلة**، اكتب في **نفس رسالتك الأولى**:\n"
            "  1️⃣ خطة سريعة (5-6 سطور):\n"
            "    ### 📋 خطة الموقع\n"
            "    • #home: الصفحة الرئيسية\n"
            "    • #quran: قائمة السور + قارئ تفاعلي\n"
            "    • #audio: صوتيات MP3 مع controls\n"
            "    • #settings: تخصيص\n"
            "  2️⃣ ```html``` يحتوي **shell كامل** (200-400 سطر): header + nav (بـanchors لكل الأقسام) + كل الـsections placeholder + footer.\n"
            "  3️⃣ سؤال واحد: 'الـshell جاهز — أبدأ بقسم #quran الكامل ولا تبي ترتيب آخر؟ <<OPT: ابدأ بـquran>> <<OPT: ابدأ بـaudio>>'\n"
            "**لا تنتظر موافقة على الخطة قبل كتابة الـshell**. اكتبهم معاً في نفس الرسالة. الخطة شرح، الـshell تنفيذ.\n"
            "بعدها استخدم Section Builder (`REPLACE_SECTION`) لملء كل قسم في رسائل لاحقة.\n"
            "\n"
            "🔗 لما تبني موقع متعدد الأقسام:\n"
            "• استخدم anchors `<section id='quran'>` مع navigation `<a href='#quran'>`\n"
            "• ✋ ممنوع: زر 'القرآن' يـscroll في الـHero — يجب يوديك لـ#quran فعلياً\n"
            "• استخدم مصادر صحيحة (CDN قرآن من api.alquran.cloud) عوضاً عن placeholder\n"
            "• كل قسم له audio/video/text controls شغّالة فعلياً، مش مجرد icons\n"
            "\n"

            "🚀 **قاعدة التنفيذ الفوري (READ FIRST — هذي تعلو على كل القواعد التالية)**:\n"
            "═══════════════════════════════════════════════════════════════\n"
            "أنت **مطوّر مُنفّذ** مو مستشار. الافتراضي = **اكتب الكود الآن**.\n"
            "\n"
            "💬 **لكن: ميّز بين 3 أنواع رسائل**:\n"
            "  🟦 **سؤال محادثة (Conversational)** — مثل: 'كلّم عن نفسك'، 'وش قدراتك'، 'كيف تشتغل'، 'اشرح لي'، 'فحص ذاتي':\n"
            "     → جاوب نص فقط بدون HTML. لا تكتب ```html``` ولا تاقات. حوار طبيعي مهذّب.\n"
            "  🟢 **طلب تنفيذي** — مثل: 'ابني، اعمل، نفّذ، صمم، اكتب، ضيف، عدّل، غيّر':\n"
            "     → اكتب الكود فوراً بدون أي سؤال موافقة. هذا الافتراضي.\n"
            "  🟡 **طلب توضيح/تخطيط** — مثل: 'قبل ما تبني، شرح الخطة':\n"
            "     → اكتب الخطة + الـshell معاً في نفس الرسالة. لا تنتظر موافقة على الخطة.\n"
            "\n"
            "🟢 **متى تكتب HTML فوراً بدون أي سؤال موافقة**:\n"
            "  • **لكن قبلها (DISCOVERY-FIRST)**: في الرسالة الأولى من العميل (current_html فاضي + عدد الرسائل ≤ 2)، **مرّر بمرحلة اكتشاف قصيرة وذكية**:\n"
            "     - رحّب بعمى — جملتين كحد أقصى\n"
            "     - أعد صياغة فكرة العميل بكلمات أوضح لتُظهر إنك فهمته\n"
            "     - ضمّن **سؤال واحد إلى سؤالين فقط** كجزء طبيعي من حديثك (مو قائمة Q&A جافة). ركّز على ما لم يذكره ولا يمكن استنتاجه:\n"
            "       • هل يبي صفحة واحدة scroll أم موقع متعدد الصفحات (Home/About/Products/Contact مستقلة)؟\n"
            "       • هل يحتاج لوحة تحكم (Admin) أم واجهة فقط؟\n"
            "       • هل يحتاج تكامل دفع (Stripe/Mada/Tap) أو حجز أو فورم تواصل فقط؟\n"
            "       • اللغات: عربي فقط، إنجليزي فقط، أم ثنائي؟\n"
            "       • شخصية البراند: فاخر، عصري، ودود، احترافي، شبابي؟\n"
            "     - **اختر الأهم من هذه الأسئلة فقط** بناءً على ما لم يوضّحه العميل. لا تسأل عن شيء واضح.\n"
            "     - في نهاية رسالتك، اعرض عليه: 'أنطلق بالبناء الآن وتقدر تعدّل لاحقاً، أم تبيني أسأل عن شي قبل؟'\n"
            "  • **بعد المرحلة الأولى**: عند أي إجابة منه أو إذا قال 'ابدأ' / 'انطلق' / 'كفى أسئلة' → اكتب الكود فوراً.\n"
            "  • أول مرة بعد الاكتشاف (current_html فاضي بعد رسالة 2-3) → اكتب الـshell كاملاً فوراً.\n"
            "  • العميل قال 'ابني، اعمل، نفّذ، صمم لي، اكتب' → اكتب الكود فوراً.\n"
            "  • طلب إضافة قسم جديد → استخدم `APPEND_SECTION` فوراً.\n"
            "  • طلب تعديل قسم موجود → استخدم `REPLACE_SECTION` فوراً.\n"
            "  • طلب تغيير ألوان/نصوص/صور → نفّذ فوراً.\n"
            "  • أي طلب صريح يتضمن فعل تنفيذي → نفّذ فوراً.\n"
            "\n"
            "🏗️ **فهم نوع المشروع (مهم — قبل البناء)**:\n"
            "  • **SPA (single-page-app)**: كل المحتوى في صفحة واحدة بأقسام anchored. ابني <section id=\"X\"> وروابط للداخل.\n"
            "  • **متعدد صفحات (multi-page)**: استخدم routes منفصلة (`/about`, `/products`). HTML5 history API أو ملفات HTML منفصلة.\n"
            "  • **مع لوحة تحكم**: ضف مسار `/admin` مع login + CRUD باستخدام localStorage/Firebase.\n"
            "  • **تحقق الأزرار**: قبل ما تنهي البناء، تأكد كل زر/رابط في الصفحة يفتح وجهة موجودة (anchor موجود أو route مفعّل). لا تترك أزرار dead-end.\n"
            "\n"
            "🟡 **متى تسأل سؤال واحد فقط قبل التنفيذ**:\n"
            "  • فقط حالة واحدة: current_html موجود + العميل قال صراحة 'صمم لي من جديد كلياً' أو 'غيّر التصميم كاملاً' أو 'ابدأ من الصفر'.\n"
            "  • في هذي الحالة فقط: 'هل تأكد؟ التصميم الحالي محفوظ تلقائياً.' وانتظر.\n"
            "  • **في كل الحالات الثانية، اكتب الكود فوراً**.\n"
            "\n"
            "🔴 **ممنوع منعاً باتاً**:\n"
            "  • الكذب بقولك 'تم' بدون كتابة كود فعلي.\n"
            "  • تأخير الكود بحجة 'انتظر موافقة' في الحالات اللي ما تحتاج موافقة.\n"
            "  • قول 'نظامي يمنعني' أو 'في قيد على' — **ما في قيد يمنعك**. اكتب وامضِ.\n"
            "  • كتابة HTML عرضي في رسالة محادثة (سؤال meta) — جاوب نص فقط.\n"
            "  • قول 'أحتاج مبرمج backend' أو 'الـbackend خارج قدرتي' — **أنت تبني الـbackend بـFirebase/Supabase/localStorage بدون أي backend منفصل**. أي تطبيق ويب يمكن بناؤه client-side في 2026.\n"
            "═══════════════════════════════════════════════════════════════\n"
            "\n"
            "🚨 قواعد ثقة (فحص ذاتي قبل الإرسال — مو عقوبات، بس صدق مع العميل):\n"
            "1. لو قلت 'إليك 3 تصاميم' أو 'نزّلت تصاميم' → عُدّ الـ```html``` blocks قبل الإرسال. إذا قلت 3 وكتبت 2 → عدّل الجملة لـ'إليك تصميمين'.\n"
            "2. لو قلت 'حدّثت' أو 'أضفت قسم X' → يجب يكون عندك:\n"
            "   • بلوك ```html``` كامل، **أو**\n"
            "   • `<<APPEND_SECTION id=\"X\">>...<</APPEND_SECTION>>`، **أو**\n"
            "   • `<<REPLACE_SECTION id=\"X\">>...<</REPLACE_SECTION>>`.\n"
            "   أي واحد من هذي الثلاثة كافي. النظام يكتشف ويدمج تلقائياً.\n"
            "3. **حرية كاملة في الإضافة والتعديل** (هذي مو قيود — هذي قدرات):\n"
            "   ✅ أضف أي قسم جديد بدون إذن خاص — استخدم `APPEND_SECTION`\n"
            "   ✅ عدّل أي قسم موجود — استخدم `REPLACE_SECTION`\n"
            "   ✅ غيّر الـnav links — استخدم `UPDATE_NAV`\n"
            "   ✅ بدّل النصوص/الصور/الألوان — استخدم HTML كامل\n"
            "   النظام يحميك فقط من خطأ واحد: حذف header أو footer بالخطأ. أي إضافة أو تعديل → يمر بدون مشكلة.\n"
            "4. قبل ما تقول 'تم'، **افحص بنفسك**: هل الكود فعلاً يحتوي التغيير؟ إذا لا، صحّحه قبل الإرسال.\n"
            "\n"
            "🛡️ **حماية إعادة التصميم الكلي** (يطبّق في حالة واحدة فقط):\n"
            "هذا البروتوكول **مو** عن كتابة HTML أول مرة، ولا عن إضافة أقسام، ولا عن تعديل لون. هذا فقط لما:\n"
            "  ✦ current_html موجود فعلاً (موقع شغّال) + \n"
            "  ✦ العميل قال بوضوح: 'غيّر التصميم كله' / 'صمم من جديد كلياً' / 'تصميم مختلف تماماً'.\n"
            "\n"
            "في هذي الحالة فقط، اتبع 3 خطوات:\n"
            "  1. سؤال واحد للتأكيد + انتظر.\n"
            "  2. اقترح التصميم الجديد كـPreview كامل + سؤال اعتماد.\n"
            "  3. عند الاعتماد: احتفظ بالـ`<script>` و `<section id>` ومحتواها الوظيفي — غيّر **الشكل فقط**.\n"
            "\n"
            "💾 شبكة الأمان: النظام يحفظ snapshots تلقائياً (آخر 20 نسخة) — العميل يقدر يسترجع أي وقت من زر 'السجل'.\n"
            "\n"
            "🎯 خيارات قابلة للضغط (مهم جداً لتسهيل التجربة):\n"
            "⚠️ قاعدة ذهبية: **اطرح سؤال واحد فقط في كل رسالة** ومعه خياراته. لا تطرح 5 أسئلة دفعة وحدة!\n"
            "لكل سؤال له إجابات محتملة، اكتب الخيارات بصيغة تاقات منفصلة:\n"
            "   <<OPT: نص الخيار الأول>>\n"
            "   <<OPT: نص الخيار الثاني>>\n"
            "   <<OPT: نص الخيار الثالث>>\n"
            "هذي راح تظهر للمستخدم كأزرار خضراء يضغط عليها بدل ما يكتب.\n"
            "أمثلة (سؤال واحد فقط لكل رسالة!):\n"
            "  • 'وش نوع الجمهور المستهدف؟ <<OPT: شباب>> <<OPT: عائلات>> <<OPT: محترفون>> <<OPT: غير ذلك (سيكتب)>>'\n"
            "  • 'إيش الإحساس اللي تبيه؟ <<OPT: فاخر وراقي>> <<OPT: عصري وحديث>> <<OPT: دافئ ومريح>> <<OPT: جريء ومثير>>'\n"
            "اكتب 3-5 خيارات لكل سؤال. اجعل آخر خيار غالباً 'غير ذلك' أو 'أبي أوضح بنفسي' عشان يقدر يكتب حر.\n"
            "بعد إجابة المستخدم، اشكره مختصراً ثم اطرح السؤال التالي. التدفق التدريجي يخلي التجربة سلسة.\n"
            "استخدم العربية في الخيارات.\n"
            "\n"
            "🎨 تنسيق النص (markdown):\n"
            "- استخدم **bold** للنقاط المهمة\n"
            "- استخدم ### للعناوين الفرعية فقط (لا تستخدم # كبير)\n"
            "- استخدم قوائم - أو 1. للنقاط\n"
            "- إيموجي بسيط ✨ 🎨 ✅ باعتدال\n"
            "- اجعل الرسائل قصيرة (3-6 أسطر) وحوارية\n"
        )

        # ── Adaptive task routing — pick the right model for this turn
        task_type, task_label = _classify_freebuild_task(
            user_msg=message or "",
            has_current_html=bool(proj.get("current_html")),
            current_html_len=len(proj.get("current_html") or ""),
        )
        logger.info(f"freebuild route: task={task_type} label={task_label}")

        # ── Quota gate (free-tier daily cap on tokens / requests) ──
        try:
            from modules.ai_core.usage_meter import check_quota
            _quota = await check_quota(db, user["user_id"])
            if not _quota.get("allowed"):
                # Return a friendly assistant message + flag the client UI.
                tier_label = _quota.get("next_tier_label", "Pro")
                assistant_msg = {
                    "id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": (
                        "🎉 **انتهى رصيد النقاط**\n\n"
                        "وصلت لنهاية رصيدك. اشحن نقاط جديدة وكمل مشروعك من نفس النقطة بالضبط 👇\n\n"
                        "• 💎 **Project Pack** — $49 — 5,000 نقطة (مرّة واحدة)\n"
                        "• 🚀 **Starter** — $19/شهر — 2,000 نقطة\n"
                        "• ⭐ **Pro** — $69/شهر — 8,000 نقطة (الأكثر شعبية)\n"
                        "• 👑 **Studio** — $199/شهر — 25,000 نقطة"
                    ),
                    "options": [
                        {"label": "Project Pack — $49", "emoji": "💎", "description": "5,000 نقطة لمرّة واحدة"},
                        {"label": "Starter — $19/شهر", "emoji": "🚀", "description": "2,000 نقطة شهرياً"},
                        {"label": "Pro — $69/شهر", "emoji": "⭐", "description": "8,000 نقطة شهرياً"},
                        {"label": "اعرض كل الباقات", "emoji": "📋", "description": "/pricing"},
                    ],
                    "inline_images": [],
                    "timestamp": _now(),
                    "quota_blocked": True,
                    "pricing_redirect": "/pricing",
                }
                return {
                    "ok": True,
                    "quota_blocked": True,
                    "quota": _quota,
                    "messages": (proj.get("messages") or []) + [assistant_msg],
                }
        except Exception as _qe:
            logger.warning(f"freebuild quota check skipped: {_qe}")

        try:
            from modules.zenrex_ai import zenrex_chat
            result = await zenrex_chat(
                agent="freebuild",
                messages=msg_list,
                user_id=user["user_id"],
                extra_context=extra_ctx,
                requires_vision=bool(vision_images),
                task_type_override=task_type,
            )
            if not result.get("ok"):
                raise HTTPException(502, "خطأ في الذكاء الاصطناعي")
            ai_text = result["content"]
            model_used = result.get("model_used", "unknown")
            # Record AI usage (tokens + cost) for metering / dashboards.
            try:
                from modules.ai_core.usage_meter import record_usage
                _usage = result.get("usage") or {}
                # Estimate tokens if missing (1 char ≈ 0.4 tokens).
                _ti = int(_usage.get("input_tokens") or _usage.get("prompt_tokens") or max(1, len(extra_ctx) // 3))
                _to = int(_usage.get("output_tokens") or _usage.get("completion_tokens") or max(1, len(ai_text) // 3))
                await record_usage(
                    db,
                    user_id=user["user_id"],
                    project_id=pid,
                    section=proj.get("mode") or "websites",
                    tokens_in=_ti,
                    tokens_out=_to,
                    model_label="zenrex-ai",
                )
            except Exception as _ue:
                logger.warning(f"freebuild usage record failed: {_ue}")

            # Truthfulness gate — if AI lied about producing variants/updates, retry once
            error_msg = _validate_truthfulness(ai_text)
            if error_msg:
                logger.warning(f"freebuild AI lied: {error_msg[:80]}")
                retry_msgs = msg_list + [
                    {"role": "assistant", "content": ai_text},
                    {"role": "user", "content": f"⚠️ تنبيه نظام داخلي (لا تظهره للمستخدم): {error_msg}"},
                ]
                retry_result = await zenrex_chat(
                    agent="freebuild",
                    messages=retry_msgs,
                    user_id=user["user_id"],
                    extra_context=extra_ctx,
                    requires_vision=bool(vision_images),
                    task_type_override=task_type,
                )
                if retry_result.get("ok"):
                    ai_text = retry_result["content"]
                    model_used = retry_result.get("model_used", model_used)

            # ── AGENTIC REPAIR LOOP — up to 3 iterations of self-correction.
            # The AI runs comprehensive validation (dead links, missing sections,
            # placeholder content, malformed HTML, missing JS routing) and
            # automatically fixes issues by re-prompting itself.
            agent_iterations = 0
            for _attempt in range(3):
                quick_html = _extract_html(ai_text)
                if not quick_html:
                    break  # no HTML to validate (chat-only response)
                # Apply best-effort dead-link auto-rewrite before validation
                quick_html, _ = _fix_dead_navigation_links(quick_html)
                issues = _comprehensive_validation(quick_html)
                high_severity = [i for i in issues if i["severity"] == "high"]
                if not high_severity:
                    break  # clean — done
                logger.warning(
                    f"freebuild agentic loop iter={_attempt+1} issues={len(issues)} "
                    f"high={len(high_severity)} codes={[i['code'] for i in issues]}"
                )
                fix_prompt = _build_fix_prompt(issues)
                fix_msgs = msg_list + [
                    {"role": "assistant", "content": ai_text},
                    {"role": "user", "content": fix_prompt},
                ]
                fix_result = await zenrex_chat(
                    agent="freebuild",
                    messages=fix_msgs,
                    user_id=user["user_id"],
                    extra_context=extra_ctx,
                    requires_vision=False,
                    task_type_override="reasoning_hard",
                )
                if not fix_result.get("ok"):
                    break
                new_text = fix_result["content"]
                if not _extract_html(new_text):
                    break  # AI didn't produce HTML in the fix attempt
                ai_text = new_text
                model_used = f"{model_used.split(' + ')[0]} + {fix_result.get('model_used', 'fix')}×{_attempt+1}"
                agent_iterations += 1

            # Design-drift gate — smart guard that distinguishes:
            #   • Conversational (user asked "what can you do?")     → SKIP entirely
            #   • Additive edits (user asked to ADD a section)       → ALLOW
            #   • Explicit redesign (user said "غيّر كل شي")          → ALLOW
            #   • Destructive shrink (AI deleted header/footer)      → BLOCK
            #   • Catastrophic drift > 0.85                          → BLOCK
            last_block_info = None  # populated below if drift gate blocks
            if proj.get("current_html"):
                new_full = _extract_html(ai_text)
                user_intent = _detect_user_intent(message or "")
                # For conversational/meta turns, never overwrite the saved site
                # — even if the AI accidentally pasted demo HTML.
                if user_intent == "conversational":
                    logger.info("freebuild conversational turn: skipping HTML save")
                    # Force-strip the demo HTML so it doesn't enter current_html
                    new_full = None
                if new_full:
                    prev_sig = _design_signature(proj["current_html"])
                    new_sig = _design_signature(new_full)
                    drift = _structural_drift_ratio(prev_sig, new_sig)
                    is_additive = _is_additive_change(prev_sig, new_sig)
                    # AI is destructive if it shrank a major element it had before
                    is_destructive = (
                        (prev_sig.get("header") and not new_sig.get("header"))
                        or (prev_sig.get("footer") and not new_sig.get("footer"))
                        or (new_sig.get("sections", 0) < int(prev_sig.get("sections", 0) * 0.6))
                        or (new_sig.get("length", 0) < int(prev_sig.get("length", 1) * 0.55))
                    )
                    should_block = False
                    block_reason = ""
                    if user_intent == "redesign":
                        should_block = False  # user asked for redesign
                    elif user_intent == "additive" and is_additive:
                        should_block = False  # legit growth
                    elif is_destructive and user_intent != "redesign":
                        should_block = True
                        block_reason = "destructive_shrink"
                    elif drift > 0.85 and user_intent != "redesign":
                        should_block = True
                        block_reason = "catastrophic_drift"
                    if should_block:
                        logger.warning(
                            f"freebuild design drift blocked: drift={drift:.2f} reason={block_reason} "
                            f"intent={user_intent} additive={is_additive} destructive={is_destructive}"
                        )
                        # Record on assistant message for self-verification next turn
                        last_block_info = {
                            "blocked": True,
                            "reason": block_reason,
                            "drift": round(drift, 2),
                            "is_destructive": is_destructive,
                            "old_length": prev_sig.get("length"),
                            "new_length": new_sig.get("length"),
                        }
                        ai_text = (
                            "⚠️ لاحظت إن التعديل سيغيّر تصميمك المعتمد بشكل كبير وقد يحذف أقسام مهمة.\n\n"
                            "لحماية شغلك، حفظت **التصميم الأصلي كما هو** ولم أطبّق التغيير.\n\n"
                            "هل تأكد إنك تبي تغيير جذري؟ اختر:\n"
                            "<<OPT: نعم — أبي تصميم جديد كلياً (ابدأ من الصفر)>>\n"
                            "<<OPT: لا — اكتفِ بتعديلات صغيرة على التصميم الحالي>>\n"
                            "<<OPT: أرني الفرق قبل التطبيق>>"
                        )
                    else:
                        logger.info(
                            f"freebuild drift OK: drift={drift:.2f} intent={user_intent} "
                            f"additive={is_additive}"
                        )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"freebuild_chat ai error: {e}")
            raise HTTPException(502, "خطأ في الذكاء")

        # Detect tags and queue asset generation (async)
        tags = TAG_RE.findall(ai_text)
        pending_assets = []
        for tag_type, tag_body in tags[:3]:  # max 3 per turn
            asset_id = str(uuid.uuid4())
            pending_assets.append({
                "id": asset_id,
                "type": tag_type.upper(),
                "prompt": tag_body.strip(),
                "status": "generating",
                "image_url": None,
                "approved": False,
                "created_at": _now(),
            })

        # Detect HTML for live preview (extracted BEFORE stripping)
        # Skip entirely on conversational turns (user asked a meta question).
        is_conversational = (
            proj.get("current_html")
            and _detect_user_intent(message or "") == "conversational"
        )
        all_variants = [] if is_conversational else _extract_all_html_variants(ai_text)
        # If AI produced 2+ HTML blocks → design variants (user picks one);
        # otherwise the single block becomes current_html immediately.
        new_html = None
        design_variants: List[Dict[str, str]] = []
        if len(all_variants) >= 2:
            for idx, html in enumerate(all_variants[:4]):  # cap at 4
                design_variants.append({
                    "id": str(uuid.uuid4()),
                    "label": f"تصميم #{idx + 1}",
                    "html": html,
                })
        elif len(all_variants) == 1:
            new_html = all_variants[0]

        # ── SECTION BUILDER: if AI used <<APPEND_SECTION>> / <<REPLACE_SECTION>>
        # directives instead of a full HTML block, splice them into existing
        # current_html. This is how the AI builds large multi-section sites
        # incrementally (one section per turn) without busting the response cap.
        section_dirs = _extract_section_directives(ai_text)
        sections_applied = 0
        if (section_dirs["appends"] or section_dirs["replaces"] or section_dirs["nav_items"]):
            base_html = new_html or proj.get("current_html")
            if base_html:
                merged = _merge_sections(
                    base_html,
                    section_dirs["appends"],
                    section_dirs["replaces"],
                    section_dirs["nav_items"],
                )
                if merged:
                    new_html = merged
                    sections_applied = (
                        len(section_dirs["appends"])
                        + len(section_dirs["replaces"])
                        + (1 if section_dirs["nav_items"] else 0)
                    )
                    logger.info(
                        f"freebuild sections merged: append={len(section_dirs['appends'])} "
                        f"replace={len(section_dirs['replaces'])} nav={bool(section_dirs['nav_items'])}"
                    )

        # ── Anchor sanity check: if nav has #X but no <section id="X">, log warning
        if new_html:
            # Auto-fix dead navigation links (href="page.html" or href="/dua")
            # that would produce blank screens in the iframe preview.
            new_html, fixed_dead = _fix_dead_navigation_links(new_html)
            if fixed_dead:
                logger.info(f"freebuild auto-fixed {fixed_dead} dead navigation link(s)")
            broken = _verify_anchor_links(new_html)
            if broken:
                logger.warning(f"freebuild broken anchors: {broken[:5]}")

        # ═════════════════════════════════════════════════════════════════════
        # 🛡️ TIER-1: PRE-FLIGHT VALIDATION + AUTO-HEAL
        # Run a structural validator on the generated HTML. If any critical or
        # major issues are found, silently ask the AI for a corrective turn
        # using the validation report as context. The customer never sees the
        # broken intermediate version — only the healed result.
        # ═════════════════════════════════════════════════════════════════════
        validation_report = None
        autoheal_applied = False
        if new_html:
            try:
                from .html_validator import validate_html, format_validation_for_ai
                validation_report = validate_html(new_html)
                logger.info(f"🛡️ validator: {validation_report['summary']}")
                if not validation_report.get("ok"):
                    heal_prompt = format_validation_for_ai(validation_report)
                    heal_system = (
                        "أنت Claude Opus — تستلم HTML قد ولّدته للتو وفيه أخطاء بنيوية محددة. "
                        "مهمتك الآن: إصلاح المشاكل المذكورة فقط، وإعادة الـHTML الكامل المصحَّح "
                        "داخل ```html ... ``` block واحد. لا اعتذار، لا شرح طويل، فقط الكود المصحَّح."
                    )
                    heal_user = (
                        heal_prompt
                        + "\n\n[HTML الحالي للإصلاح]\n```html\n"
                        + new_html[:90000]
                        + "\n```\n\nأعد الكود مصحَّحاً الآن."
                    )
                    try:
                        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
                        api_key = os.environ.get("EMERGENT_LLM_KEY")
                        if api_key:
                            heal_chat = (
                                LlmChat(api_key=api_key, session_id=f"heal-{uuid.uuid4().hex[:10]}", system_message=heal_system)
                                .with_model("anthropic", "claude-sonnet-4-5-20250929")
                            )
                            heal_resp = await heal_chat.send_message(UserMessage(text=heal_user))
                            heal_text = heal_resp if isinstance(heal_resp, str) else getattr(heal_resp, "content", "")
                            heal_blocks = _extract_all_html_variants(heal_text or "")
                            if heal_blocks:
                                healed_html = heal_blocks[0]
                                re_report = validate_html(healed_html)
                                logger.info(f"🛡️ post-heal: {re_report['summary']}")
                                before_bad = len(validation_report.get("critical", [])) + len(validation_report.get("major", []))
                                after_bad = len(re_report.get("critical", [])) + len(re_report.get("major", []))
                                if after_bad < before_bad:
                                    healed_html, _ = _fix_dead_navigation_links(healed_html)
                                    new_html = healed_html
                                    validation_report = re_report
                                    autoheal_applied = True
                                    logger.info(f"✅ auto-heal accepted: {before_bad}→{after_bad} issues")
                                else:
                                    logger.info(f"⏭️ auto-heal rejected (no improvement): {before_bad}→{after_bad}")
                    except Exception as _heal_err:  # noqa: BLE001
                        logger.warning(f"auto-heal LLM call failed: {_heal_err}")
            except Exception as _v_err:  # noqa: BLE001
                logger.warning(f"validator skipped: {_v_err}")

        # Strip code blocks from chat display — code is private/paid feature.
        # If we have design variants, replace all blocks with a single one-line notice;
        # otherwise replace each block with the "updated live preview" notice.
        if design_variants:
            chat_text = _CODE_BLOCK_RE.sub("", ai_text).strip()
            chat_text = re.sub(r"\n{3,}", "\n\n", chat_text)
            chat_text = (chat_text + "\n\n*🎨 شوف التصاميم تحت — اختر اللي يعجبك*").strip()
        else:
            chat_text = _strip_code_from_chat(ai_text)
        # Strip section directives from chat (internal-only)
        chat_text = _strip_section_directives(chat_text)
        # NOTE: no "تم تحديث المعاينة الحية" appendage — the preview tab is
        # removed. The AI is expected to publish_site() right after meaningful
        # edits and the versioned URL becomes the live truth.
        if sections_applied > 0 and not chat_text.strip():
            chat_text = f"✅ طبّقت {sections_applied} تعديل."
        clean_text = _strip_tags(chat_text)
        # First try OPT tags; if none, fall back to numbered/bulleted lists after a question.
        opt_tag_items = [m.group(1).strip() for m in OPT_RE.finditer(ai_text)]
        if opt_tag_items:
            options = opt_tag_items
        else:
            fb_items, fb_lines = _extract_options_fallback(ai_text)
            options = fb_items
            # Strip the consumed list lines from displayed text so we don't show twice.
            if fb_lines:
                kept = [ln for ln in clean_text.split("\n") if ln not in fb_lines]
                clean_text = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()

        # Save chat message + pending assets
        update_set = {"updated_at": _now()}
        push_ops: Dict[str, Any] = {
            "messages": {
                "$each": [
                    {"role": "user", "content": message, "timestamp": _now(), "pending_assets": [], "attachments": attachment_meta, "reference": reference_meta, "answer_meta": parsed_answer_meta},
                    {"role": "assistant", "content": clean_text, "timestamp": _now(), "pending_assets": pending_assets, "had_html": bool(new_html), "options": options, "design_variants": design_variants, "block_info": last_block_info, "sections_applied": sections_applied},
                ]
            }
        }
        if new_html:
            # ── AUTO-SNAPSHOT — before overwriting current_html, archive the
            # previous version so the user can restore if AI makes a mistake.
            # Keep last 20 snapshots only.
            old_html = proj.get("current_html")
            if old_html and old_html != new_html:
                snapshot = _make_snapshot_doc(
                    old_html,
                    user_msg=(message or ""),
                    kind="auto",
                    label="قبل تعديل",
                )
                push_ops["html_snapshots"] = {
                    "$each": [snapshot],
                    # UNLIMITED — user explicitly requested no trimming (300+ ok).
                }
            update_set["current_html"] = _inject_zenrex_footer(new_html)
            # Persist validation report + auto-heal flag for admin/dashboard visibility
            if validation_report is not None:
                update_set["last_validation"] = {
                    "ok": validation_report.get("ok"),
                    "summary": validation_report.get("summary"),
                    "critical_count": len(validation_report.get("critical", [])),
                    "major_count": len(validation_report.get("major", [])),
                    "minor_count": len(validation_report.get("minor", [])),
                    "autoheal_applied": autoheal_applied,
                    "size_kb": validation_report.get("size_kb"),
                    "at": _now(),
                }
            # 📊 Site Health Score — runs on every shipped HTML so the customer
            # always sees a fresh 0-100 grade and click-to-improve suggestions.
            try:
                from .health_score import score_html
                update_set["last_health"] = {
                    **score_html(new_html),
                    "at": _now(),
                }
            except Exception as _hs_err:  # noqa: BLE001
                logger.warning(f"health_score skipped: {_hs_err}")
            # 🧠 Brand kit learning — extract signals from this HTML and merge
            # into the user's persistent brand kit so future projects start smarter.
            try:
                from .brand_kit import learn_from_project
                await learn_from_project(db, user["user_id"], new_html, proj.get("name", ""))
            except Exception as _bk_learn_err:  # noqa: BLE001
                logger.warning(f"brand_kit learn skipped: {_bk_learn_err}")
            # Auto-advance phase whenever we ship HTML (anti-stuck-on-discovery)
            update_set["current_phase"] = "build"
            # Mark earlier phases as completed in phase_history (visual sidebar)
            _prior_history = set(proj.get("phase_history") or [])
            for _ph in ("discovery", "design", "assets"):
                _prior_history.add(_ph)
            update_set["phase_history"] = list(_prior_history)
        elif design_variants:
            # AI produced design variants → we're in design phase now
            update_set["current_phase"] = "design"
            _prior_history = set(proj.get("phase_history") or [])
            _prior_history.add("discovery")
            update_set["phase_history"] = list(_prior_history)
        elif _user_turns >= 1 and proj.get("current_phase") in (None, "discovery"):
            # User has engaged at least once — we're past first-contact discovery
            # but still gathering info. Keep current_phase as 'discovery' but
            # ensure phase_history reflects engagement progress.
            pass
        await db.freebuild_projects.update_one(
            {"id": pid},
            {
                "$push": push_ops,
                "$set": update_set,
            },
        )

        # Kick off background asset generation (don't block chat response)
        if pending_assets:
            asyncio.create_task(_generate_assets_bg(db, pid, pending_assets))

        return {
            "response": clean_text,
            "pending_assets": pending_assets,
            "html_updated": bool(new_html),
            "task_label": task_label,
            # model_used intentionally omitted — proprietary AI experience
            "model_used": "",
            "agent_iterations": agent_iterations,
        }

    # ===== Approve a design variant (when AI offered 2-3 designs) =====
    @router.post("/project/{pid}/approve-design")
    async def approve_design(
        pid: str,
        variant_id: str = Form(...),
        user=Depends(get_current_user),
    ):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404)
        variant_html: Optional[str] = None
        for m in proj.get("messages", []):
            for v in (m.get("design_variants") or []):
                if v.get("id") == variant_id:
                    variant_html = v.get("html")
                    break
            if variant_html:
                break
        if not variant_html:
            raise HTTPException(404, "التصميم غير موجود")
        # Snapshot the previous design before swapping (safety net)
        update_doc: Dict[str, Any] = {"$set": {
            "current_html": variant_html,
            "approved_design_id": variant_id,
            "approved_design_sig": _design_signature(variant_html),
            "updated_at": _now(),
        }}
        old_html = proj.get("current_html")
        if old_html and old_html != variant_html:
            update_doc["$push"] = {"html_snapshots": {
                "$each": [_make_snapshot_doc(
                    old_html,
                    user_msg="[تصميم سابق قبل اعتماد variant جديد]",
                    kind="auto",
                    label="قبل اعتماد تصميم جديد",
                )],
            }}
        await db.freebuild_projects.update_one(
            {"id": pid},
            update_doc,
        )
        return {"ok": True, "html_length": len(variant_html)}

    # ===== Approve asset =====
    @router.post("/project/{pid}/asset/{aid}/approve")
    async def approve_asset(pid: str, aid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one({"id": pid, "user_id": user["user_id"]})
        if not proj:
            raise HTTPException(404)
        # Find pending asset in messages
        target = None
        for m in proj.get("messages", []):
            for a in (m.get("pending_assets") or []):
                if a["id"] == aid:
                    target = a
                    break
            if target:
                break
        if not target:
            raise HTTPException(404, "الأصل غير موجود")
        target["approved"] = True
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$push": {"approved_assets": target}, "$set": {"updated_at": _now()}},
        )
        return {"ok": True}

    # ===== Compile final HTML with approved asset URLs =====
    @router.post("/project/{pid}/compile")
    async def compile_html(pid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one({"id": pid, "user_id": user["user_id"]}, {"_id": 0})
        if not proj:
            raise HTTPException(404)
        html = proj.get("current_html") or ""
        if not html:
            raise HTTPException(400, "لا يوجد HTML للتجميع. اطلب من الذكاء توليد الصفحة أولاً.")
        # Inject approved asset URLs by type — replace placeholder src markers
        for a in proj.get("approved_assets", []):
            url = a.get("image_url")
            if not url:
                continue
            atype = a.get("type", "").upper()
            # replace any data-tag="HERO" src or placeholder
            html = html.replace(f"{{{{ASSET:{atype}}}}}", url)
            html = html.replace(f"PLACEHOLDER_{atype}", url)
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$set": {"compiled_html": html, "updated_at": _now()}},
        )
        return {"ok": True, "html_length": len(html)}

    # ===== Delete project =====
    @router.delete("/project/{pid}")
    async def delete_project(pid: str, user=Depends(get_current_user)):
        # Soft-delete only. The 30-day clock starts ticking now; restore is
        # free within 24h, $5 between 24h-30d, hard-purged after 30 days.
        r = await db.freebuild_projects.update_one(
            {"id": pid, "user_id": user["user_id"]},
            {"$set": {
                "status": "deleted",
                "deleted_at": _now(),
                "updated_at": _now(),
            }},
        )
        if r.matched_count == 0:
            raise HTTPException(404)
        return {"ok": True,
                "message": "حُذف المشروع — تقدر تسترجعه مجاناً خلال 24 ساعة من /trash"}

    # ===== Trash (soft-deleted projects) =====
    # Customers asked: "don't lose my work, let me recover deletes". So we
    # never hard-delete on the user's click — we move to trash with a 30-day
    # retention. Free restore for 24h grace period, then a small fee
    # ($5 flat — value-aligns with the storage backup cost).
    GRACE_FREE_SECONDS = 24 * 3600
    HARD_PURGE_SECONDS = 30 * 24 * 3600
    RESTORE_FEE_USD = 5.0

    def _restore_status(deleted_at: str | float | None) -> Dict[str, Any]:
        """Compute restore eligibility + fee from the deleted timestamp."""
        from datetime import datetime
        if not deleted_at:
            return {"eligible": True, "fee_usd": 0, "reason": "free"}
        try:
            if isinstance(deleted_at, (int, float)):
                age_sec = time.time() - float(deleted_at)
            else:
                # ISO 8601 string from _now()
                dt = datetime.fromisoformat(str(deleted_at).replace("Z", "+00:00"))
                age_sec = time.time() - dt.timestamp()
        except Exception:
            age_sec = 0
        if age_sec < GRACE_FREE_SECONDS:
            return {"eligible": True, "fee_usd": 0,
                    "reason": "خلال فترة السماح المجانية (24 ساعة)",
                    "expires_in_sec": int(GRACE_FREE_SECONDS - age_sec)}
        if age_sec < HARD_PURGE_SECONDS:
            return {"eligible": True, "fee_usd": RESTORE_FEE_USD,
                    "reason": f"الاسترجاع برسم رمزي ${RESTORE_FEE_USD:.2f}",
                    "expires_in_sec": int(HARD_PURGE_SECONDS - age_sec)}
        return {"eligible": False, "fee_usd": 0,
                "reason": "انتهت فترة الاحتفاظ (30 يوم) — يتم الحذف النهائي"}

    @router.get("/trash")
    async def list_trash(user=Depends(get_current_user)):
        cur = db.freebuild_projects.find(
            {"user_id": user["user_id"], "status": "deleted"},
            {"_id": 0, "id": 1, "name": 1, "mode": 1, "deleted_at": 1,
             "created_at": 1, "updated_at": 1, "messages": 1},
        ).sort("deleted_at", -1).limit(100)
        items: List[Dict[str, Any]] = []
        async for p in cur:
            # Strip messages from list view (heavy); just send count
            msg_count = len(p.get("messages") or [])
            p.pop("messages", None)
            p["message_count"] = msg_count
            p["restore"] = _restore_status(p.get("deleted_at"))
            items.append(p)
        return {"items": items, "retention_days": HARD_PURGE_SECONDS // 86400,
                "grace_hours": GRACE_FREE_SECONDS // 3600,
                "paid_fee_usd": RESTORE_FEE_USD}

    @router.post("/project/{pid}/restore")
    async def restore_project(pid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"], "status": "deleted"},
            {"_id": 0, "id": 1, "name": 1, "deleted_at": 1},
        )
        if not proj:
            raise HTTPException(404, "غير موجود في سلة المحذوفات")
        status = _restore_status(proj.get("deleted_at"))
        if not status["eligible"]:
            raise HTTPException(410, status["reason"])  # 410 Gone
        if status["fee_usd"] > 0:
            # Billing is not enforced yet — for now we log the fee and let
            # the user proceed (so they can experience the full flow). When
            # Stripe is wired, this endpoint will return 402 Payment Required
            # with a Stripe Checkout URL and the actual restore happens in
            # the success webhook.
            await db.restore_charges.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user["user_id"],
                "project_id": pid,
                "fee_usd": status["fee_usd"],
                "paid": False,  # flip to True in Stripe webhook
                "created_at": _now(),
            })
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$set": {"status": "active", "updated_at": _now()},
             "$unset": {"deleted_at": ""}},
        )
        return {
            "ok": True,
            "fee_charged_usd": status["fee_usd"],
            "message": (f"تم استرجاع المشروع '{proj.get('name')}' ✓ — "
                        + ("مجاناً ضمن فترة السماح" if status["fee_usd"] == 0
                           else f"مع رسم ${status['fee_usd']:.2f}")),
        }

    @router.delete("/project/{pid}/purge")
    async def purge_project(pid: str, user=Depends(get_current_user)):
        """Permanently delete a soft-deleted project. Irreversible."""
        r = await db.freebuild_projects.delete_one(
            {"id": pid, "user_id": user["user_id"], "status": "deleted"}
        )
        if r.deleted_count == 0:
            raise HTTPException(404, "غير موجود في سلة المحذوفات")
        # Also drop engineering docs to free space
        await db.freebuild_project_docs.delete_many({"project_id": pid})
        return {"ok": True, "message": "تم الحذف النهائي — لا يمكن الاسترجاع"}

    # ===== Full project export (data portability guarantee) ===================
    # Users can download their entire project — chat history, decisions,
    # character_sheet, assets, HTML, snapshots — as a single JSON file at any
    # time. This is our promise that they never lose their work to a server
    # migration / DB issue / our mistakes.
    @router.get("/project/{pid}/export")
    async def export_project(pid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404)
        # Pull every engineering doc (decisions, character_sheet, world_bible, PRD, ...)
        docs_cur = db.freebuild_project_docs.find({"project_id": pid}, {"_id": 0})
        docs: List[Dict[str, Any]] = [d async for d in docs_cur]
        # Pull approved assets metadata (images/videos/voice clips already
        # in the project's approved gallery)
        assets_cur = db.freebuild_assets.find({"project_id": pid}, {"_id": 0})
        try:
            assets: List[Dict[str, Any]] = [a async for a in assets_cur]
        except Exception:
            assets = []
        bundle = {
            "format": "zenrex.project.v1",
            "exported_at": _now(),
            "exported_by": user.get("email") or user.get("user_id"),
            "project": proj,
            "docs": docs,
            "assets": assets,
        }
        # Pretty filename: <project-name>-<short-id>.json
        # HTTP headers are latin-1 only — strip non-ASCII for the legacy filename
        # and use RFC 5987's filename* parameter for the Unicode version (browsers
        # prefer this when available).
        import urllib.parse as _urllib_parse
        raw_name = (proj.get("name") or "project")[:40].replace("/", "_").replace(" ", "_")
        ascii_name = "".join(ch for ch in raw_name if ord(ch) < 128) or "project"
        utf8_name = _urllib_parse.quote(raw_name, safe="")
        filename_ascii = f"zenrex-{ascii_name}-{pid[:8]}.json"
        filename_utf8 = f"zenrex-{utf8_name}-{pid[:8]}.json"
        return JSONResponse(
            content=bundle,
            headers={
                "Content-Disposition": (
                    f"attachment; filename=\"{filename_ascii}\"; "
                    f"filename*=UTF-8''{filename_utf8}"
                )
            },
        )

    # ===== Finalization options (when user wants to publish/take ownership) =====
    @router.get("/project/{pid}/finalize-options")
    async def finalize_options(pid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0, "id": 1, "name": 1, "current_html": 1}
        )
        if not proj:
            raise HTTPException(404)
        if not proj.get("current_html"):
            raise HTTPException(400, "أكمل الموقع أولاً — لا يوجد محتوى نهائي بعد")
        return {
            "ready": True,
            "paths": [
                {
                    "id": "host_with_us",
                    "title": "🏠 استضف معنا على Zenrex",
                    "price_usd": 0,
                    "subtitle": "مجاني تماماً — موقعك على دومين Zenrex، نتولى الاستضافة والصيانة",
                    "features": [
                        "نشر فوري على نطاق zenrex.ai",
                        "SSL مجاني وأداء عالي",
                        "تعديل لاحق عبر نفس الشات",
                        "لا تحتاج خبرة تقنية",
                    ],
                    "cta": "انشر موقعي الآن",
                },
                {
                    "id": "take_code_self",
                    "title": "💻 استلم الكود (مبرمج)",
                    "price_usd": 79,
                    "subtitle": "بتنشره بنفسك على GitHub/Vercel/Cloudflare — أنت محترف وعندك خبرة",
                    "features": [
                        "كل ملفات HTML/CSS/JS",
                        "صور بحجم Production",
                        "ملف README فيه طريقة النشر",
                        "بدون أي إرشاد إضافي",
                    ],
                    "cta": "اشترِ الكود بـ $79",
                },
                {
                    "id": "take_code_guided",
                    "title": "🎓 الكود + إرشاد كامل",
                    "price_usd": 199,
                    "subtitle": "الذكاء يمشي معك خطوة بخطوة — يربط GitHub repo، يدفع لـVercel، يضبط الدومين",
                    "features": [
                        "كل اللي في الباقة السابقة",
                        "الذكاء يتصل بمستودعاتك",
                        "يضبط CI/CD ودومين مخصص",
                        "دعم 30 يوم على المشاكل التقنية",
                    ],
                    "cta": "اشترِ الإرشاد الكامل بـ $199",
                },
                {
                    "id": "full_independence",
                    "title": "💎 الاستقلال الكامل",
                    "price_usd": 799,
                    "subtitle": "ملكية كاملة — Delivery Kit احترافي، نقل ملكية المستودع، نشر VPS، فك الارتباط بـ Zenrex نهائياً",
                    "features": [
                        "Delivery Kit: Dockerfile + nginx.conf + deploy.sh",
                        "ARCHITECTURE.md (5+ صفحات مولّدة بـ Claude)",
                        "نقل ملكية GitHub repo لاسمك",
                        "إرشاد VPS كامل (Hetzner / DigitalOcean)",
                        "SECRETS.template.env + LICENSE + README",
                        "دعم 60 يوم + فاتورة تسليم رسمية",
                    ],
                    "cta": "اشترِ الاستقلال الكامل بـ $799",
                },
            ],
        }

    # ===== Convert this website project to an App project (placeholder for apps module) =====
    @router.post("/project/{pid}/convert-to-app")
    async def convert_to_app(pid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404)
        if not proj.get("current_html"):
            raise HTTPException(400, "أكمل الموقع قبل التحويل لتطبيق")
        app_id = str(uuid.uuid4())
        await db.app_conversion_projects.insert_one({
            "id": app_id,
            "source_kind": "freebuild",
            "source_id": pid,
            "user_id": user["user_id"],
            "name": f"{proj['name']} (تطبيق)",
            "description": proj.get("description", ""),
            "current_html": proj.get("current_html"),
            "approved_assets": proj.get("approved_assets", []),
            "messages": [],
            "status": "discovery",
            "created_at": _now(),
            "updated_at": _now(),
        })
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$set": {"converted_to_app_id": app_id, "updated_at": _now()}},
        )
        return {"ok": True, "app_id": app_id}

    # ===== INDEPENDENCE TOOLKIT =====
    # Unlock the code/independence tier (mocked payment — wire Lemon Squeezy later)
    # ═══════════════════════════════════════════════════════════════════════
    # 💳 STRIPE CHECKOUT — Source-Code Unlock ($100 one-time)
    #
    # Fixed packages defined SERVER-SIDE only (security best practice).
    # Webhook /api/webhook/stripe and polling status endpoint included.
    # ═══════════════════════════════════════════════════════════════════════
    STRIPE_PACKAGES = {
        "code_only":         {"amount":  79.00, "currency": "usd", "tier": "code_only"},
        "code_pro":          {"amount": 249.00, "currency": "usd", "tier": "code_pro"},
        "guided":            {"amount": 199.00, "currency": "usd", "tier": "guided"},
        "full_independence": {"amount": 799.00, "currency": "usd", "tier": "full_independence"},
        "hosting_month":     {"amount":  25.00, "currency": "usd", "tier": "hosting_month"},
    }

    @router.post("/project/{pid}/checkout")
    async def create_checkout(
        pid: str,
        request: Request,
        package_id: str = Form(...),
        origin: str = Form(...),
        user=Depends(get_current_user),
    ):
        if package_id not in STRIPE_PACKAGES:
            raise HTTPException(400, "باقة غير صالحة")
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0, "name": 1}
        )
        if not proj:
            raise HTTPException(404, "المشروع غير موجود")

        pkg = STRIPE_PACKAGES[package_id]
        api_key = os.environ.get("STRIPE_API_KEY")
        if not api_key:
            raise HTTPException(500, "STRIPE_API_KEY غير مكوّن")
        try:
            from emergentintegrations.payments.stripe.checkout import (  # type: ignore
                StripeCheckout, CheckoutSessionRequest,
            )
        except ImportError:
            raise HTTPException(500, "emergentintegrations stripe module غير مثبّت")

        host_url = str(request.base_url).rstrip("/")
        webhook_url = f"{host_url}/api/webhook/stripe"
        stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)

        origin = origin.rstrip("/")
        success_url = f"{origin}/freebuild/checkout/{pid}/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{origin}/freebuild/checkout/{pid}/cancel"

        metadata = {
            "project_id": pid,
            "user_id": user["user_id"],
            "package_id": package_id,
            "tier": pkg["tier"],
        }
        req = CheckoutSessionRequest(
            amount=pkg["amount"],
            currency=pkg["currency"],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
        )
        try:
            session = await stripe_checkout.create_checkout_session(req)
        except Exception as e:  # noqa: BLE001
            logger.exception("stripe checkout failed: %s", e)
            raise HTTPException(500, f"فشل إنشاء جلسة الدفع: {e}")

        # MANDATORY: persist a pending transaction row BEFORE redirect.
        await db.payment_transactions.insert_one({
            "session_id": session.session_id,
            "user_id": user["user_id"],
            "project_id": pid,
            "package_id": package_id,
            "tier": pkg["tier"],
            "amount": pkg["amount"],
            "currency": pkg["currency"],
            "payment_status": "pending",
            "status": "initiated",
            "metadata": metadata,
            "created_at": _now(),
            "updated_at": _now(),
        })
        return {"url": session.url, "session_id": session.session_id}

    @router.get("/payments/status/{session_id}")
    async def checkout_status(session_id: str, request: Request, user=Depends(get_current_user)):
        api_key = os.environ.get("STRIPE_API_KEY")
        if not api_key:
            raise HTTPException(500, "STRIPE_API_KEY غير مكوّن")
        try:
            from emergentintegrations.payments.stripe.checkout import StripeCheckout  # type: ignore
        except ImportError:
            raise HTTPException(500, "emergentintegrations stripe module غير مثبّت")
        host_url = str(request.base_url).rstrip("/")
        stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=f"{host_url}/api/webhook/stripe")
        try:
            status = await stripe_checkout.get_checkout_status(session_id)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(502, f"فشل جلب حالة الدفع: {e}")

        # Update transaction (idempotent — only process success once)
        txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        already_processed = txn and txn.get("status") == "completed"
        if status.payment_status == "paid" and not already_processed:
            tier = (txn or {}).get("tier") or status.metadata.get("tier") or "code_only"
            project_id = (txn or {}).get("project_id") or status.metadata.get("project_id")
            if project_id and tier in ("code_only", "code_pro", "guided", "full_independence"):
                update = {
                    "code_unlocked": True,
                    "tier": tier,
                    "unlocked_at": _now(),
                    "updated_at": _now(),
                }
                if tier == "full_independence":
                    update["independence_unlocked"] = True
                    update["independence_at"] = _now()
                await db.freebuild_projects.update_one(
                    {"id": project_id},
                    {"$set": update},
                )
            if project_id and tier == "hosting_month":
                await db.freebuild_projects.update_one(
                    {"id": project_id},
                    {"$set": {
                        "hosting_active": True,
                        "hosting_until": _now(),  # frontend should display real date from billing record
                        "updated_at": _now(),
                    }},
                )
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {
                    "status": "completed",
                    "payment_status": status.payment_status,
                    "amount_total": status.amount_total,
                    "completed_at": _now(),
                    "updated_at": _now(),
                }},
            )
        elif status.payment_status != "paid":
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": status.payment_status, "updated_at": _now()}},
            )
        return {
            "session_id": session_id,
            "payment_status": status.payment_status,
            "status": status.status,
            "amount_total": status.amount_total,
            "currency": status.currency,
        }

    @router.post("/project/{pid}/unlock")
    async def unlock_independence(
        pid: str,
        tier: str = Form(...),  # "code_only" ($49) | "guided" ($99) | "full_independence" ($200)
        user=Depends(get_current_user),
    ):
        if tier not in ("code_only", "guided", "full_independence"):
            raise HTTPException(400, "tier غير صالح")
        update = {
            "code_unlocked": True,
            "tier": tier,
            "unlocked_at": _now(),
            "updated_at": _now(),
        }
        if tier == "full_independence":
            update["independence_unlocked"] = True
            update["independence_at"] = _now()
        r = await db.freebuild_projects.update_one(
            {"id": pid, "user_id": user["user_id"]},
            {"$set": update},
        )
        if r.matched_count == 0:
            raise HTTPException(404)
        return {"ok": True, "tier": tier}

    # ═══════════════════════════════════════════════════════════════════════
    # PUBLISH FLOW — host on Zenrex platform (no GitHub/Vercel needed)
    #
    # Vision: user says "publish" in chat → AI calls publish_site tool →
    # site goes live at https://zenrex.ai/s/{slug} in seconds.
    # ═══════════════════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════════════════
    # 🛡️ GUARDIAN ADMIN DASHBOARD — live monitoring of all active projects
    # Admin-only. Lists projects with their current distress score + last
    # intervention, sorted by urgency.
    # ═══════════════════════════════════════════════════════════════════════
    async def _ensure_admin(user: Dict[str, Any]) -> None:
        if user.get("is_admin") or user.get("role") in ("admin", "owner"):
            return
        # Some legacy users have admin email
        if (user.get("email") or "").lower() in ("admin@zenrex.ai", "owner@zerax.com"):
            return
        raise HTTPException(403, "Admin only")

    @router.get("/admin/guardian/projects")
    async def admin_guardian_projects(
        level: Optional[str] = None,  # filter: warn|intervene|critical
        user=Depends(get_current_user),
    ):
        """List all FreeBuild projects with their distress signals."""
        await _ensure_admin(user)
        cursor = db.freebuild_projects.find(
            {},
            {
                "_id": 0, "id": 1, "name": 1, "user_id": 1, "current_phase": 1,
                "updated_at": 1, "last_distress": 1, "last_guardian_at": 1,
                "code_unlocked": 1, "current_html": 1,
                "guardian_interventions": {"$slice": -1},
                "messages": {"$slice": -2},
            },
        ).sort([("last_guardian_at", -1), ("updated_at", -1)]).limit(200)
        rows: List[Dict[str, Any]] = []
        async for p in cursor:
            d = p.get("last_distress") or {}
            row = {
                "id": p["id"],
                "name": p.get("name") or "—",
                "user_id": p.get("user_id"),
                "current_phase": p.get("current_phase") or "discovery",
                "updated_at": p.get("updated_at"),
                "distress_score": d.get("score", 0),
                "distress_level": d.get("level", "ok"),
                "distress_signals": d.get("signals", []),
                "has_html": bool(p.get("current_html")),
                "code_unlocked": bool(p.get("code_unlocked")),
                "last_guardian_at": p.get("last_guardian_at"),
                "last_intervention": (p.get("guardian_interventions") or [None])[-1] if p.get("guardian_interventions") else None,
                "msg_preview": [
                    {"role": m.get("role"), "content": (m.get("content") or "")[:160]}
                    for m in (p.get("messages") or [])
                ],
                "intervention_count": len(p.get("guardian_interventions") or []),
            }
            if level and row["distress_level"] != level:
                continue
            rows.append(row)
        return {"projects": rows, "count": len(rows)}

    @router.get("/admin/guardian/project/{pid}")
    async def admin_guardian_project_detail(pid: str, user=Depends(get_current_user)):
        await _ensure_admin(user)
        p = await db.freebuild_projects.find_one(
            {"id": pid},
            {"_id": 0, "messages": 1, "guardian_interventions": 1, "last_distress": 1, "name": 1, "user_id": 1, "current_html": 1},
        )
        if not p:
            raise HTTPException(404, "Project not found")
        return p

    @router.post("/admin/guardian/project/{pid}/inject")
    async def admin_guardian_inject(
        pid: str,
        directive: str = Form(...),
        diagnosis: str = Form(""),
        user=Depends(get_current_user),
    ):
        """Admin manually injects a corrective directive (skips LLM)."""
        await _ensure_admin(user)
        if not directive.strip():
            raise HTTPException(400, "directive مطلوب")
        intervention = {
            "id": uuid.uuid4().hex,
            "created_at": _now(),
            "diagnosis": diagnosis.strip() or "تدخّل يدوي من الأدمن",
            "directive": directive.strip(),
            "tone": "confident",
            "severity": "manual",
            "distress_score": -1,
            "signals": ["manual_admin_injection"],
            "consumed": False,
            "injected_by": user.get("email") or user.get("user_id"),
        }
        r = await db.freebuild_projects.update_one(
            {"id": pid},
            {
                "$push": {"guardian_interventions": {"$each": [intervention], "$slice": -20}},
                "$set": {"last_guardian_at": _now()},
            },
        )
        if r.matched_count == 0:
            raise HTTPException(404, "Project not found")
        return {"ok": True, "intervention_id": intervention["id"]}

    @router.post("/project/{pid}/publish")
    async def publish_project(
        pid: str,
        slug: str = Form(...),
        user=Depends(get_current_user),
    ):
        """Publish a finished FreeBuild project to a live URL on Zenrex.

        Versioned URLs (added 2026-02):
        - The slug the user provides is the **base name** (e.g. "awesome-cafe").
        - Every publish increments the version → `awesome-cafe-v1`, `awesome-cafe-v2`...
        - The previous version is marked `superseded` (not deleted) and serves a
          redirect page so any open tabs/bookmarks land on the latest version.
        - Only the last 5 versions are kept; older ones are hard-deleted.
        - This guarantees ZERO cache-mixing: every edit gives a brand-new URL.
        """
        raw = (slug or "").strip().lower()
        # Strip any user-supplied -vN suffix so we always work with the base.
        base = re.sub(r"-v\d+$", "", raw)
        if not re.match(r"^[a-z0-9][a-z0-9-]{1,58}[a-z0-9]$", base):
            raise HTTPException(400, "الـ slug لازم 3-60 حرف، حروف صغيرة وأرقام وشُرَط فقط")
        # Look in chat-projects collection first (new flow), then legacy
        proj = await db.freebuild_chat_projects.find_one({"id": pid, "user_id": user["user_id"]}, {"_id": 0})
        collection = db.freebuild_chat_projects
        if not proj:
            proj = await db.freebuild_projects.find_one({"id": pid, "user_id": user["user_id"]}, {"_id": 0})
            collection = db.freebuild_projects
        if not proj:
            raise HTTPException(404, "المشروع غير موجود")
        if not proj.get("current_html"):
            raise HTTPException(400, "الموقع فاضي — أكمل البناء أولاً")

        # Determine the new version.
        # If the user is republishing under the SAME base they used before → bump.
        # If the user is changing the base → start fresh at v1.
        prev_base = proj.get("published_base_slug")
        prev_version = int(proj.get("published_version") or 0)
        if prev_base == base and prev_version > 0:
            new_version = prev_version + 1
        else:
            new_version = 1
        new_slug = f"{base}-v{new_version}"

        # Collision check — if some other project already owns this slug, bump until free.
        # (Extremely rare since slug includes user's base, but defensive.)
        guard = 0
        while True:
            existing = await db.freebuild_published_sites.find_one({"slug": new_slug})
            if not existing or existing.get("project_id") == pid:
                break
            new_version += 1
            new_slug = f"{base}-v{new_version}"
            guard += 1
            if guard > 50:
                raise HTTPException(409, "تعذّر إيجاد slug متاح — جرّب اسم آخر")

        now = _now()
        all_pages = proj.get("pages") or {"index.html": proj["current_html"]}
        if "index.html" not in all_pages:
            all_pages["index.html"] = proj["current_html"]
        # Snapshot the latest pages into the NEW slug doc (fresh document, no
        # leftover fields from prior version).
        await db.freebuild_published_sites.update_one(
            {"slug": new_slug},
            {"$set": {
                "slug": new_slug,
                "base_slug": base,
                "version": new_version,
                "project_id": pid,
                "user_id": user["user_id"],
                "current_html": proj["current_html"],   # legacy field
                "pages": all_pages,                      # multi-page support
                "name": proj.get("name") or base,
                "updated_at": now,
                "superseded": False,
                "superseded_by": None,
            }, "$setOnInsert": {"created_at": now, "views": 0}},
            upsert=True,
        )

        # Mark the previous version (if any) as superseded so it can serve a
        # redirect page instead of stale content.
        prev_slug = proj.get("published_slug")
        if prev_slug and prev_slug != new_slug:
            await db.freebuild_published_sites.update_one(
                {"slug": prev_slug},
                {"$set": {"superseded": True, "superseded_by": new_slug, "updated_at": now}},
            )

        # Retention: keep only the last 5 versions for this project, hard-delete older ones.
        try:
            old_docs = await db.freebuild_published_sites.find(
                {"project_id": pid, "base_slug": base},
                {"_id": 0, "slug": 1, "version": 1},
            ).sort("version", -1).to_list(length=100)
            to_delete = [d["slug"] for d in old_docs[5:]]  # everything past the top-5
            if to_delete:
                await db.freebuild_published_sites.delete_many({"slug": {"$in": to_delete}})
                logger.info(f"[publish] retention purge: deleted {len(to_delete)} old versions for {pid}")
        except Exception:
            logger.exception("[publish] retention purge failed (non-fatal)")

        # Build the published_history list on the project (last 10 entries).
        history = list(proj.get("published_history") or [])
        history.append({"slug": new_slug, "version": new_version, "published_at": now})
        history = history[-10:]
        # 🗂️ Design Archive (المحفوظات) — capture a publish snapshot so the
        # user can ALWAYS recover any published design later. The very first
        # publish is tagged as the "baseline" (التصميم المعتمد الأول).
        publish_snapshot_push = None
        try:
            existing_snaps = proj.get("html_snapshots") or []
            has_baseline = any(
                (s.get("kind") == "baseline") for s in existing_snaps if isinstance(s, dict)
            )
            kind = "baseline" if not has_baseline else "publish"
            label = (
                "✅ التصميم المعتمد (النسخة الأساسية)"
                if not has_baseline
                else f"📦 نشر النسخة v{new_version}"
            )
            publish_snapshot_push = _make_snapshot_doc(
                proj.get("current_html") or "",
                user_msg=f"نشر {new_slug}",
                kind=kind,
                label=label,
            )
        except Exception:
            publish_snapshot_push = None

        _publish_update: Dict[str, Any] = {"$set": {
            "published": True,
            "published_slug": new_slug,
            "published_base_slug": base,
            "published_version": new_version,
            "published_at": now,
            "published_history": history,
        }}
        if publish_snapshot_push:
            _publish_update["$push"] = {"html_snapshots": {"$each": [publish_snapshot_push]}}
        await collection.update_one(
            {"id": pid},
            _publish_update,
        )

        live_url = f"https://zenrex.ai/s/{new_slug}"
        previous_url = f"https://zenrex.ai/s/{prev_slug}" if prev_slug and prev_slug != new_slug else None
        logger.info(f"[publish] user={user['user_id']} project={pid} new_slug={new_slug} (v{new_version}) prev={prev_slug}")
        return {
            "ok": True,
            "slug": new_slug,
            "base_slug": base,
            "version": new_version,
            "url": live_url,
            "previous_url": previous_url,
            "message": f"✅ النسخة v{new_version} نُشرت على {live_url}" + (
                f"\n⚠️ النسخة السابقة ({prev_slug}) أصبحت قديمة — تُحوّل تلقائياً للنسخة الجديدة."
                if previous_url else ""
            ),
        }

    def _inject_base_href(html: str, slug: str) -> str:
        """Inject <base href='/api/freebuild-chat/published-sites/{slug}/'>
        into <head> so relative links like <a href='about.html'> resolve to
        the right sub-page URL instead of being interpreted relative to the
        parent URL (which was sending /s/{slug} → /s/about.html instead of
        /s/{slug}/about.html). This is the iron-clad guarantee multi-page
        navigation works when serving from a no-trailing-slash route.

        Uses the canonical API path so it works identically in the preview
        environment and production (where Nginx rewrites /s/* → /api/...).
        """
        if not html:
            return html
        # 🔧 Use the PUBLIC `/s/{slug}/` path (not /api/...) so relative
        # links like <a href='movies.html'> resolve to the public URL the
        # user clicked. Nginx rewrites /s/{slug}/X → /api/.../X for us.
        # Previously we used the API path here — caused all nav links
        # to fail because the API path doesn't have the public sub-page
        # serving wired up identically.
        base_url = f"/s/{slug}/"
        # Skip if a <base> tag already exists (don't override user-provided)
        if re.search(r"<base\b", html, re.I):
            return html
        base_tag = f'<base href="{base_url}">'
        # Inject right after <head> (or before </head> if no opening tag found)
        if re.search(r"<head\b[^>]*>", html, re.I):
            return re.sub(r"(<head\b[^>]*>)", r"\1" + base_tag, html, count=1, flags=re.I)
        # Fallback: prepend
        return base_tag + html

    @router.get("/published-sites/{slug}", include_in_schema=False)
    async def serve_published_site(slug: str):
        """Public endpoint — serves the homepage (index.html) of a published site.
        Nginx routes /s/{slug} → /api/freebuild-chat/published-sites/{slug}
        so end-users see the clean URL https://zenrex.ai/s/{slug}.
        """
        from fastapi.responses import HTMLResponse
        slug = (slug or "").strip().lower()
        site = await db.freebuild_published_sites.find_one({"slug": slug})
        if not site:
            return HTMLResponse(
                "<!doctype html><html dir='rtl'><head><meta charset='utf-8'><title>غير موجود</title></head>"
                "<body style='font-family:sans-serif;text-align:center;padding:80px;background:#0a0a14;color:#fbbf24'>"
                "<h1>الموقع غير موجود</h1><p>الرابط منتهي أو الموقع لم يُنشر بعد.</p>"
                "<p><a href='https://zenrex.ai' style='color:#fbbf24'>← العودة إلى Zenrex</a></p>"
                "</body></html>",
                status_code=404
            )
        # Superseded version → INSTANT HTTP 301 to the newest version.
        # Was: HTML page with `meta refresh content=2` (felt like a white screen
        # for the user). HTTP 301 is invisible — the browser jumps straight
        # to the new slug. Search engines also pick up the redirect cleanly.
        if site.get("superseded") and site.get("superseded_by"):
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=f"/s/{site['superseded_by']}", status_code=301)
        try:
            await db.freebuild_published_sites.update_one({"slug": slug}, {"$inc": {"views": 1}})
        except Exception:
            pass
        # Multi-page aware: serve pages["index.html"] when available, else fall back to legacy current_html
        html = (site.get("pages") or {}).get("index.html") or site.get("current_html") or ""
        # Inject <base href="/s/{slug}/"> so relative links (about.html,
        # contact.html, ...) resolve correctly even when the URL has no
        # trailing slash.
        html = _inject_base_href(html, slug)
        html = _strip_scaffold_placeholders(html)
        # Cache-bust: published HTML is volatile (auto-republished on every edit),
        # so tell browsers + edge cache to revalidate every load.
        return HTMLResponse(_inject_zenrex_footer(html),
                             headers={"Cache-Control": "no-store, max-age=0, must-revalidate"})

    @router.get("/published-sites/{slug}/{filename}", include_in_schema=False)
    async def serve_published_subpage(slug: str, filename: str):
        """Serves additional pages of a multi-page published site, e.g.
        /s/{slug}/about.html → /api/freebuild-chat/published-sites/{slug}/about.html
        """
        from fastapi.responses import HTMLResponse
        slug = (slug or "").strip().lower()
        filename = (filename or "").strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9\-_]*\.html$", filename):
            return HTMLResponse("<h1>Invalid page name</h1>", status_code=400)
        site = await db.freebuild_published_sites.find_one({"slug": slug})
        if not site:
            return HTMLResponse("<h1>Site not found</h1>", status_code=404)
        # Superseded sub-page → INSTANT HTTP 301 to same filename on newer slug.
        if site.get("superseded") and site.get("superseded_by"):
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=f"/s/{site['superseded_by']}/{filename}", status_code=301)
        pages = site.get("pages") or {}
        html = pages.get(filename)
        if not html:
            return HTMLResponse(
                f"<!doctype html><html dir='rtl'><head><meta charset='utf-8'><title>404</title></head>"
                f"<body style='font-family:sans-serif;text-align:center;padding:80px;background:#0a0a14;color:#fbbf24'>"
                f"<h1>الصفحة غير موجودة</h1><p>الصفحة <code>{filename}</code> غير موجودة في هذا الموقع.</p>"
                f"<p><a href='/s/{slug}' style='color:#fbbf24'>← الرئيسية</a></p></body></html>",
                status_code=404,
            )
        try:
            await db.freebuild_published_sites.update_one({"slug": slug}, {"$inc": {"views": 1}})
        except Exception:
            pass
        html = _inject_base_href(html, slug)
        html = _strip_scaffold_placeholders(html)
        return HTMLResponse(_inject_zenrex_footer(html),
                             headers={"Cache-Control": "no-store, max-age=0, must-revalidate"})

    # ═══════════════════════════════════════════════════════════════════════
    # المهندس — Engineer Audit (paid, user-triggered)
    # Crawls the published site with a real browser, generates a structured
    # audit report (phased fix plan). User reviews → asks AI to fix each issue.
    # ═══════════════════════════════════════════════════════════════════════
    ENGINEER_AUDIT_COST = 500  # credits per full audit run

    async def _run_engineer_audit(live_url_base: str, pages: Dict[str, str]) -> Dict[str, Any]:
        """Crawl every page with Playwright, collect issues."""
        from playwright.async_api import async_playwright
        issues: List[Dict[str, Any]] = []
        pages_checked: List[Dict[str, Any]] = []

        def _add(severity: str, category: str, page: str, description: str,
                 fix_suggestion: str, element_text: str = "", element_selector: str = ""):
            issues.append({
                "id": str(uuid.uuid4()),
                "severity": severity,                # critical | high | medium | low
                "category": category,
                "page": page,
                "element_text": element_text[:140],
                "element_selector": element_selector[:200],
                "description": description,
                "fix_suggestion": fix_suggestion,
                "fixed": False,
            })

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx_b = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await ctx_b.new_page()
            # Always check at least index.html
            page_files = list(pages.keys())
            if "index.html" not in page_files:
                page_files.insert(0, "index.html")
            # Cap to 12 pages to keep audit time bounded.
            page_files = page_files[:12]

            for pname in page_files:
                page_url = live_url_base if pname == "index.html" else f"{live_url_base}/{pname}"
                console_errors: List[str] = []
                page.on("console", lambda msg, _errs=console_errors:
                        _errs.append(f"[{msg.type}] {msg.text[:240]}") if msg.type == "error" else None)
                nav_ok = True
                try:
                    await page.goto(page_url, wait_until="domcontentloaded", timeout=20000)
                except Exception as e:
                    nav_ok = False
                    _add("critical", "page_load_failed", pname,
                         f"الصفحة فشلت في التحميل: {type(e).__name__}",
                         f"تأكد أن الصفحة `{pname}` موجودة في الموقع وتُحمَّل بدون أخطاء شبكة.")
                if not nav_ok:
                    pages_checked.append({"page": pname, "loaded": False})
                    continue
                await page.wait_for_timeout(1500)

                metrics = await page.evaluate("""() => {
                    const internal = (h) => h && !/^(https?:|mailto:|tel:|#)/i.test(h);
                    const links = Array.from(document.querySelectorAll('a[href]')).map(a => ({
                        href: a.getAttribute('href') || '',
                        text: (a.innerText || a.textContent || '').trim().slice(0, 80),
                        internal: internal(a.getAttribute('href'))
                    }));
                    const buttons = Array.from(document.querySelectorAll('button, [role=button], input[type=submit], input[type=button]')).map(b => ({
                        text: (b.innerText || b.value || '').trim().slice(0, 80),
                        hasOnclick: !!b.getAttribute('onclick'),
                        hasType: b.type || '',
                        disabled: b.disabled || false,
                    }));
                    const forms = Array.from(document.querySelectorAll('form')).map(f => ({
                        action: f.getAttribute('action') || '',
                        method: f.getAttribute('method') || 'GET',
                        hasOnsubmit: !!f.getAttribute('onsubmit'),
                        fields: f.querySelectorAll('input, textarea, select').length,
                    }));
                    const images = Array.from(document.querySelectorAll('img')).map(img => ({
                        src: img.currentSrc || img.src || '',
                        alt: img.getAttribute('alt') || '',
                        loaded: img.complete && img.naturalWidth > 0,
                    }));
                    const bodyText = (document.body.innerText || '').toLowerCase();
                    const hasPaymentWord = /(checkout|دفع|اشتري|اشترِ|stripe|paypal|سلة|buy now|إتمام الشراء)/i.test(document.body.innerText || '');
                    const hasShippingWord = /(shipping|شحن|توصيل|عنوان|delivery)/i.test(document.body.innerText || '');
                    const hasDashboardWord = /(dashboard|لوحة التحكم|admin|إدارة)/i.test(document.body.innerText || '');
                    const stripeLoaded = !!window.Stripe;
                    const paypalLoaded = !!window.paypal;
                    return {links, buttons, forms, images, hasPaymentWord, hasShippingWord, hasDashboardWord, stripeLoaded, paypalLoaded,
                            scripts: Array.from(document.scripts).map(s => s.src).filter(Boolean).slice(0, 30)};
                }""")

                # 1. Console errors
                if console_errors:
                    _add("high", "console_error", pname,
                         f"تم رصد {len(console_errors)} خطأ JavaScript في الـ console.",
                         "افتح Developer Tools واصلح الأخطاء — قد تكون متغير غير معرّف، API call فاشل، أو syntax error.",
                         element_text=" | ".join(console_errors[:3]))

                # 2. Internal links pointing to pages that don't exist
                known_pages = set(pages.keys())
                for lnk in metrics["links"]:
                    if lnk["internal"]:
                        href = lnk["href"].lstrip("/").split("?")[0].split("#")[0]
                        if not href:
                            continue
                        # Skip absolute paths that go to /api/, etc.
                        if href.startswith("api/") or href.startswith("s/"):
                            continue
                        target = href if href.endswith(".html") else f"{href}.html"
                        # If it's "index" or empty → ok
                        if target in ("index.html", "") or target in known_pages:
                            continue
                        # Anchor-only?
                        if "#" in lnk["href"] and not href:
                            continue
                        _add("high", "broken_link", pname,
                             f"رابط يشير إلى صفحة غير موجودة: `{lnk['href']}`.",
                             f"إما أنشئ الصفحة `{target}` أو غيّر الرابط لصفحة موجودة.",
                             element_text=lnk["text"], element_selector=f"a[href='{lnk['href']}']")

                # 3. Buttons with no click handler and not inside a form
                for btn in metrics["buttons"]:
                    if not btn["hasOnclick"] and btn["hasType"] != "submit" and not btn["disabled"]:
                        # Only flag buttons with meaningful text
                        if btn["text"] and len(btn["text"]) > 1:
                            _add("medium", "button_no_handler", pname,
                                 f"زر `{btn['text']}` بدون أي onclick أو event handler.",
                                 "أضف handler أو حوّله إلى `<a href>` لصفحة فعلية. الزر الحالي بدون وظيفة.",
                                 element_text=btn["text"])

                # 4. Forms without submit handlers and without backend action
                for frm in metrics["forms"]:
                    if not frm["action"] and not frm["hasOnsubmit"] and frm["fields"] > 0:
                        _add("high", "form_no_handler", pname,
                             f"نموذج فيه {frm['fields']} حقل لكن بدون action ولا onsubmit.",
                             "أضف backend endpoint للنموذج أو onsubmit handler — وإلا البيانات تضيع.")

                # 5. Broken images
                for img in metrics["images"]:
                    if not img["loaded"] and img["src"]:
                        _add("medium", "broken_image", pname,
                             f"صورة لا تُحمَّل: `{img['src'][:120]}`.",
                             "تحقق من مسار الصورة أو استبدلها بصورة عاملة.",
                             element_selector=f"img[src='{img['src'][:80]}']")

                # 6. Payment hints without SDK
                if metrics["hasPaymentWord"] and not metrics["stripeLoaded"] and not metrics["paypalLoaded"]:
                    has_payment_script = any("stripe" in s.lower() or "paypal" in s.lower() for s in metrics["scripts"])
                    if not has_payment_script:
                        _add("critical", "missing_payment_integration", pname,
                             "الصفحة تذكر شراء/دفع لكن لا يوجد Stripe ولا PayPal SDK مُحمَّل.",
                             "اطلب من Zenrex استدعاء Stripe Checkout أو ربط بوابة دفع فعلية — وإلا الزر مجرد ديكور.")

                # 7. Shipping hints without input fields
                if metrics["hasShippingWord"]:
                    addr_inputs = await page.evaluate("""() => {
                        const ins = Array.from(document.querySelectorAll('input, textarea'));
                        return ins.filter(i => /address|عنوان|شحن|city|مدينة|country|دولة|zip|postal/i.test((i.name||'') + ' ' + (i.placeholder||'') + ' ' + (i.id||''))).length;
                    }""")
                    if addr_inputs == 0:
                        _add("medium", "missing_shipping_fields", pname,
                             "الصفحة تذكر الشحن/التوصيل لكن لا يوجد حقول عنوان أو مدينة أو دولة.",
                             "أضف نموذج شحن فيه: العنوان، المدينة، الدولة، الرمز البريدي، رقم الجوال.")

                pages_checked.append({
                    "page": pname,
                    "loaded": True,
                    "console_errors": len(console_errors),
                    "links": len(metrics["links"]),
                    "buttons": len(metrics["buttons"]),
                    "forms": len(metrics["forms"]),
                    "images": len(metrics["images"]),
                })

            await browser.close()

        # Group issues into phases (~5 issues per phase, ordered by severity).
        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        issues.sort(key=lambda i: (sev_order.get(i["severity"], 9), i["page"]))
        for idx, issue in enumerate(issues):
            issue["phase"] = (idx // 5) + 1

        total = len(issues)
        crit = sum(1 for i in issues if i["severity"] == "critical")
        high = sum(1 for i in issues if i["severity"] == "high")
        med = sum(1 for i in issues if i["severity"] == "medium")
        # Score: 100 - weighted issues. Cap floor at 0.
        score = max(0, 100 - (crit * 15 + high * 8 + med * 3))
        if total == 0:
            verdict = "🟢 ممتاز — لم أجد أي ثغرات."
        elif crit == 0 and high <= 2:
            verdict = "🟡 جيد — ثغرات بسيطة قابلة للإصلاح."
        elif crit <= 2:
            verdict = "🟠 يحتاج عمل — عدة ثغرات مهمة."
        else:
            verdict = "🔴 خطير — ثغرات حرجة كثيرة، يلزم إصلاح فوري."
        phases_count = (total + 4) // 5 if total else 0
        return {
            "issues": issues,
            "pages_checked": pages_checked,
            "stats": {"total": total, "critical": crit, "high": high, "medium": med, "score": score, "phases": phases_count},
            "verdict": verdict,
        }

    @router.post("/project/{pid}/engineer/audit")
    async def engineer_audit(
        pid: str,
        user=Depends(get_current_user),
    ):
        """Run المهندس — a paid deep audit on the published site.

        Cost: ENGINEER_AUDIT_COST credits (refunded on failure).
        Requires the project to be published.
        """
        proj = await db.freebuild_chat_projects.find_one({"id": pid, "user_id": user["user_id"]}, {"_id": 0})
        if not proj:
            proj = await db.freebuild_projects.find_one({"id": pid, "user_id": user["user_id"]}, {"_id": 0})
        if not proj:
            raise HTTPException(404, "المشروع غير موجود")
        slug = proj.get("published_slug")
        if not slug:
            raise HTTPException(400, "لازم تنشر الموقع أولاً قبل ما تستدعي المهندس")

        site = await db.freebuild_published_sites.find_one({"slug": slug})
        if not site:
            raise HTTPException(404, "النسخة المنشورة غير موجودة")
        pages = site.get("pages") or {"index.html": site.get("current_html") or ""}

        # Charge upfront (refund on failure).
        _u_doc = await db.users.find_one({"id": user["user_id"]}, {"_id": 0, "credits": 1, "role": 1}) or {}
        _bal = int(round(float(_u_doc.get("credits") or 0)))
        _is_unlimited = (_u_doc.get("role") or "").lower() in ("owner", "admin", "superuser")
        if not _is_unlimited:
            if _bal < ENGINEER_AUDIT_COST:
                raise HTTPException(402, f"رصيدك ({_bal}) ما يكفي — يلزم {ENGINEER_AUDIT_COST} نقطة لاستدعاء المهندس")
            await db.users.update_one({"id": user["user_id"]}, {"$inc": {"credits": -ENGINEER_AUDIT_COST}})

        audit_id = str(uuid.uuid4())
        started_at = _now()
        # Insert a "running" record so the UI can poll if needed.
        await db.freebuild_audit_reports.insert_one({
            "id": audit_id,
            "project_id": pid,
            "user_id": user["user_id"],
            "slug": slug,
            "status": "running",
            "started_at": started_at,
        })

        try:
            live_url_base = f"{_public_host()}/s/{slug}"
            result = await _run_engineer_audit(live_url_base, pages)
            completed_at = _now()
            doc = {
                "status": "completed",
                "completed_at": completed_at,
                "issues": result["issues"],
                "pages_checked": result["pages_checked"],
                "stats": result["stats"],
                "verdict": result["verdict"],
            }
            await db.freebuild_audit_reports.update_one({"id": audit_id}, {"$set": doc})
            logger.info(f"[engineer] user={user['user_id']} project={pid} audit={audit_id} "
                        f"issues={result['stats']['total']} score={result['stats']['score']}")
            return {
                "ok": True,
                "audit_id": audit_id,
                "live_url": live_url_base,
                "started_at": started_at,
                "completed_at": completed_at,
                **doc,
            }
        except Exception as e:
            if not _is_unlimited:
                await db.users.update_one({"id": user["user_id"]}, {"$inc": {"credits": ENGINEER_AUDIT_COST}})
            await db.freebuild_audit_reports.update_one(
                {"id": audit_id},
                {"$set": {"status": "failed", "error": str(e)[:300]}},
            )
            logger.exception(f"[engineer] audit failed: {e}")
            raise HTTPException(500, f"المهندس واجه مشكلة. تمت إعادة النقاط. ({str(e)[:120]})")

    @router.get("/project/{pid}/engineer/audits")
    async def list_engineer_audits(pid: str, user=Depends(get_current_user)):
        """List all audit reports for a project (most recent first)."""
        cursor = db.freebuild_audit_reports.find(
            {"project_id": pid, "user_id": user["user_id"]},
            {"_id": 0, "issues": 0, "pages_checked": 0},  # heavy fields stripped
        ).sort("started_at", -1).limit(20)
        items = await cursor.to_list(length=20)
        return {"audits": items, "count": len(items)}

    @router.get("/project/{pid}/engineer/audit/{audit_id}")
    async def get_engineer_audit(pid: str, audit_id: str, user=Depends(get_current_user)):
        """Fetch a single full audit report."""
        audit = await db.freebuild_audit_reports.find_one(
            {"id": audit_id, "project_id": pid, "user_id": user["user_id"]},
            {"_id": 0},
        )
        if not audit:
            raise HTTPException(404, "تقرير المهندس غير موجود")
        return audit


    # ═══════════════════════════════════════════════════════════════════════
    # KIDS PWA — Prayer Recordings (server-stored, parent reviewable)
    # ═══════════════════════════════════════════════════════════════════════
    KIDS_UPLOADS_DIR = "/opt/zenrex/data/uploads/kids_recordings"
    try:
        os.makedirs(KIDS_UPLOADS_DIR, exist_ok=True)
    except Exception:
        pass

    @router.post("/kids/recordings/upload")
    async def kids_upload_recording(
        file: UploadFile = File(...),
        child_email: str = Form(...),
        child_name: str = Form(""),
        audio_track: str = Form(""),
        duration_sec: float = Form(0.0),
        rec_type: str = Form("prayer"),     # prayer | task | dhikr
        task_id: str = Form(""),
        task_title: str = Form(""),
        points: int = Form(0),               # points to award upon successful upload
        phase: str = Form(""),               # "before" or "after" for two-step tasks
    ):
        """Public — Kids PWA uploads a prayer recording.
        We trust the child_email (from client-side login) since the recording
        is non-sensitive media that parents will review anyway.
        """
        child_email = (child_email or "").strip().lower()
        # Accept any "@kids.*" domain (kids.local, kids.zenrex.ai, etc.)
        _kids_re = re.compile(r"^[^@\s]+@kids\.[\w.\-]+$")
        if not _kids_re.match(child_email):
            raise HTTPException(403, "child_email must be a @kids.* address")

        rec_type_n = (rec_type or "prayer").lower()

        # ── ANTI-CHEAT: 24h cooldown per (child, task_id) ──
        # Prevents kids from re-submitting the same task multiple times in a day.
        # Applies only to 'task' and 'dhikr' types. Prayers exempt (5 daily prayers).
        if rec_type_n in ("task", "dhikr") and task_id:
            from datetime import timedelta as _td, timezone as _tz, datetime as _dt
            window_start = (_dt.now(_tz.utc) - _td(hours=24)).isoformat()
            existing = await db.kids_recordings.find_one({
                "child_email": child_email,
                "task_id": task_id,
                "status": {"$in": ["pending", "approved"]},
                "created_at": {"$gte": window_start},
            })
            if existing:
                # For two-step tasks: allow 'after' phase if previous was 'before'
                prev_phase = existing.get("phase", "")
                if not (phase == "after" and prev_phase == "before"):
                    hrs_ago = 0
                    try:
                        from datetime import datetime as _dt2
                        t0 = _dt2.fromisoformat(existing["created_at"].replace("Z", "+00:00"))
                        hrs_ago = int((_dt2.now(_tz.utc) - t0).total_seconds() / 3600)
                    except Exception:
                        pass
                    raise HTTPException(429, f"✋ أنجزت هذه المهمة قبل {max(hrs_ago,0)} ساعة. حاول مرة أخرى بعد {max(0, 24 - hrs_ago)} ساعة.")

        # Read file (cap at 200MB)
        body = await file.read()
        if len(body) > 200 * 1024 * 1024:
            raise HTTPException(413, "ملف كبير جداً (الحد 200MB)")
        rec_id = uuid.uuid4().hex
        ext = (file.filename or "").split(".")[-1].lower() if file.filename else "webm"
        if ext not in {"webm", "mp4", "mov", "ogg"}:
            ext = "webm"
        path = f"{KIDS_UPLOADS_DIR}/{rec_id}.{ext}"
        try:
            with open(path, "wb") as f:
                f.write(body)
        except Exception as e:
            logger.error(f"[kids-rec] write fail: {e}")
            raise HTTPException(500, "فشل حفظ الملف")
        now = _now()

        # Compute proposed points: explicit > defaults
        try:
            pts = int(points or 0)
        except Exception:
            pts = 0
        if pts <= 0:
            pts = {"prayer": 10, "task": 5, "dhikr": 5}.get(rec_type_n, 0)

        # Auto-approve prayers only. Tasks/dhikr require parent review.
        auto_approve = rec_type_n == "prayer"
        status = "approved" if auto_approve else "pending"

        doc = {
            "id": rec_id,
            "child_email": child_email,
            "child_name": child_name or child_email.split("@")[0],
            "audio_track": audio_track,
            "duration_sec": float(duration_sec or 0),
            "size_bytes": len(body),
            "ext": ext,
            "path": path,
            "created_at": now,
            "parent_comments": [],
            "viewed_by_parent": False,
            "rec_type": rec_type_n,
            "task_id": task_id,
            "task_title": task_title,
            "proposed_points": pts,
            "awarded_points": pts if auto_approve else 0,
            "status": status,
        }
        if phase: doc["phase"] = phase
        await db.kids_recordings.insert_one(doc)

        # Only award immediately if auto-approved (prayer)
        if auto_approve and pts > 0:
            await db.kids_points.insert_one({
                "id": uuid.uuid4().hex,
                "child_email": child_email,
                "kind": rec_type_n,
                "value": pts,
                "meta": {"recording_id": rec_id, "task_id": task_id, "task_title": task_title, "audio_track": audio_track},
                "created_at": now,
            })
        return {
            "ok": True,
            "id": rec_id,
            "url": f"/api/freebuild-chat/kids/recordings/{rec_id}/stream",
            "size_bytes": len(body),
            "points_awarded": pts if auto_approve else 0,
            "proposed_points": pts,
            "status": status,
            "message": "✅ +%d نقطة!" % pts if auto_approve else f"⏳ أُرسل لولي أمرك للمراجعة (+{pts} نقطة عند الموافقة)",
        }

    @router.post("/kids/recordings/{rec_id}/approve")
    async def kids_recording_approve(rec_id: str, user=Depends(get_current_user)):
        rec = await db.kids_recordings.find_one({"id": rec_id})
        if not rec:
            raise HTTPException(404, "التسجيل غير موجود")
        if rec.get("status") == "approved":
            return {"ok": True, "already_approved": True, "points": int(rec.get("awarded_points") or 0)}
        pts = int(rec.get("proposed_points") or 0)
        await db.kids_recordings.update_one(
            {"id": rec_id},
            {"$set": {"status": "approved", "awarded_points": pts, "reviewed_at": _now(), "reviewed_by": user["user_id"], "viewed_by_parent": True}},
        )
        if pts > 0:
            await db.kids_points.insert_one({
                "id": uuid.uuid4().hex,
                "child_email": rec["child_email"],
                "kind": rec.get("rec_type", "task"),
                "value": pts,
                "meta": {"recording_id": rec_id, "task_id": rec.get("task_id", ""), "task_title": rec.get("task_title", "")},
                "created_at": _now(),
            })
        return {"ok": True, "points_awarded": pts}

    @router.post("/kids/recordings/{rec_id}/reject")
    async def kids_recording_reject(rec_id: str, reason: str = Form(""), user=Depends(get_current_user)):
        rec = await db.kids_recordings.find_one({"id": rec_id})
        if not rec:
            raise HTTPException(404, "التسجيل غير موجود")
        await db.kids_recordings.update_one(
            {"id": rec_id},
            {"$set": {"status": "rejected", "reject_reason": reason[:200], "reviewed_at": _now(), "reviewed_by": user["user_id"], "viewed_by_parent": True}},
        )
        return {"ok": True}

    @router.get("/kids/notifications/count")
    async def kids_notifications_count(parent_id: Optional[str] = None):
        """Returns counts of pending items for parent review (recordings + Quran)."""
        pid = parent_id
        if not pid:
            any_parent = await db.kids_accounts.find_one({}, {"parent_id": 1})
            pid = any_parent.get("parent_id") if any_parent else None
        # Get all kids of this parent
        kid_emails = []
        if pid:
            kids = await db.kids_accounts.find({"parent_id": pid}, {"email": 1}).to_list(length=30)
            kid_emails = [k["email"] for k in kids]
        rec_q = {"status": "pending"} if not kid_emails else {"status": "pending", "child_email": {"$in": kid_emails}}
        quran_q = {"status": "pending"} if not kid_emails else {"status": "pending", "child_email": {"$in": kid_emails}}
        pending_rec = await db.kids_recordings.count_documents(rec_q)
        pending_quran = await db.kids_quran_submissions.count_documents(quran_q)
        return {"ok": True, "pending_recordings": pending_rec, "pending_quran": pending_quran, "total": pending_rec + pending_quran}

    @router.get("/kids/tasks/today_status")
    async def kids_tasks_today_status(child_email: str):
        """Returns for each parent_task: locked (done in last 24h) or available."""
        child_email = child_email.strip().lower()
        from datetime import timedelta as _td, timezone as _tz, datetime as _dt
        window_start = (_dt.now(_tz.utc) - _td(hours=24)).isoformat()
        # Get child's parent
        ka = await db.kids_accounts.find_one({"email": child_email})
        if not ka:
            return {"ok": True, "items": []}
        pid = ka.get("parent_id")
        tasks = await db.kids_parent_tasks.find({"parent_id": pid, "is_active": True}, {"_id": 0, "parent_id": 0}).sort("order", 1).to_list(length=200)
        # Recent recordings for this child
        recs = await db.kids_recordings.find({
            "child_email": child_email,
            "rec_type": {"$in": ["task", "dhikr"]},
            "status": {"$in": ["pending", "approved"]},
            "created_at": {"$gte": window_start},
        }, {"task_id": 1, "status": 1, "phase": 1, "created_at": 1}).to_list(length=200)
        done_map = {}
        for r in recs:
            tid = r.get("task_id", "")
            if tid:
                done_map.setdefault(tid, []).append(r)
        out = []
        for t in tasks:
            entries = done_map.get(t["id"], [])
            locked = bool(entries)
            # For two-step tasks: locked only if BOTH before & after done
            if t.get("needs_before_after"):
                phases = {e.get("phase") for e in entries}
                locked = "before" in phases and "after" in phases
            out.append({**t, "locked_today": locked, "submissions_today": len(entries), "pending_review": any(e.get("status") == "pending" for e in entries)})
        return {"ok": True, "items": out}


    # ═══════════════════════════════════════════════════════════════════════
    # KIDS PWA — Points ledger (real, server-side)
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/kids/points/award")
    async def kids_award_points(
        child_email: str = Form(...),
        kind: str = Form(...),               # dhikr | task | prayer | video | bonus
        value: int = Form(...),
        meta_json: str = Form("{}"),
        task_id: str = Form(""),
    ):
        child_email = (child_email or "").strip().lower()
        _kids_re = re.compile(r"^[^@\s]+@kids\.[\w.\-]+$")
        if not _kids_re.match(child_email):
            raise HTTPException(403, "child_email must be a @kids.* address")
        try:
            v = int(value)
        except Exception:
            raise HTTPException(400, "value must be int")
        if v <= 0 or v > 10000:
            raise HTTPException(400, "value out of range")
        try:
            meta = json.loads(meta_json or "{}")
        except Exception:
            meta = {}
        kind_n = (kind or "bonus").lower()[:24]
        # 24h cooldown for task awards (anti-cheat)
        tid = task_id or meta.get("task_id") or ""
        if kind_n == "task" and tid:
            from datetime import timedelta as _td, timezone as _tz, datetime as _dt
            window_start = (_dt.now(_tz.utc) - _td(hours=24)).isoformat()
            exists = await db.kids_points.find_one({
                "child_email": child_email,
                "kind": "task",
                "meta.task_id": tid,
                "created_at": {"$gte": window_start},
            })
            if exists:
                raise HTTPException(429, "✋ أنجزت هذه المهمة اليوم! حاول غداً.")
        entry = {
            "id": uuid.uuid4().hex,
            "child_email": child_email,
            "kind": kind_n,
            "value": v,
            "meta": meta,
            "created_at": _now(),
        }
        await db.kids_points.insert_one(entry)
        agg = await db.kids_points.aggregate([
            {"$match": {"child_email": child_email}},
            {"$group": {"_id": None, "total": {"$sum": "$value"}}}
        ]).to_list(length=1)
        total = (agg[0]["total"] if agg else 0)
        return {"ok": True, "id": entry["id"], "total": total, "added": v}

    @router.get("/kids/points/summary")
    async def kids_points_summary(child_email: str):
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        child_email = (child_email or "").strip().lower()
        # Total
        agg_total = await db.kids_points.aggregate([
            {"$match": {"child_email": child_email}},
            {"$group": {"_id": "$kind", "sum": {"$sum": "$value"}, "count": {"$sum": 1}}}
        ]).to_list(length=50)
        by_kind = {x["_id"]: {"points": x["sum"], "count": x["count"]} for x in agg_total}
        total = sum(x["sum"] for x in agg_total)
        # Today + week
        now = _dt.now(_tz.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        week_start = (now - _td(days=7)).isoformat()
        agg_today = await db.kids_points.aggregate([
            {"$match": {"child_email": child_email, "created_at": {"$gte": today_start}}},
            {"$group": {"_id": None, "sum": {"$sum": "$value"}}}
        ]).to_list(length=1)
        agg_week = await db.kids_points.aggregate([
            {"$match": {"child_email": child_email, "created_at": {"$gte": week_start}}},
            {"$group": {"_id": None, "sum": {"$sum": "$value"}}}
        ]).to_list(length=1)
        # Recent
        recent = await db.kids_points.find(
            {"child_email": child_email}, {"_id": 0}
        ).sort("created_at", -1).limit(20).to_list(length=20)
        # Streak: distinct days with at least 1 entry, counting back from today
        days = await db.kids_points.distinct("created_at", {"child_email": child_email})
        day_set = {d[:10] for d in days if isinstance(d, str)}
        streak = 0
        cur = now
        while cur.strftime("%Y-%m-%d") in day_set:
            streak += 1
            cur = cur - _td(days=1)
        # SAR conversion (0.1 SAR per point default)
        sar_per_point = 0.1
        return {
            "ok": True,
            "child_email": child_email,
            "total_points": total,
            "today_points": (agg_today[0]["sum"] if agg_today else 0),
            "week_points": (agg_week[0]["sum"] if agg_week else 0),
            "streak_days": streak,
            "by_kind": by_kind,
            "recent": recent,
            "sar_per_point": sar_per_point,
            "monthly_sar": round(total * sar_per_point, 2),
        }

    @router.get("/kids/recordings")
    async def kids_list_recordings(child_email: Optional[str] = None, limit: int = 50):
        """List recordings — optionally filtered by child."""
        q: Dict[str, Any] = {}
        if child_email:
            q["child_email"] = child_email.strip().lower()
        cursor = db.kids_recordings.find(q, {"_id": 0, "path": 0}).sort("created_at", -1).limit(int(limit))
        items = await cursor.to_list(length=int(limit))
        return {"ok": True, "items": items, "count": len(items)}

    @router.get("/kids/recordings/{rec_id}/stream", include_in_schema=False)
    async def kids_stream_recording(rec_id: str):
        from fastapi.responses import FileResponse
        doc = await db.kids_recordings.find_one({"id": rec_id})
        if not doc:
            raise HTTPException(404, "recording not found")
        if not os.path.exists(doc["path"]):
            raise HTTPException(410, "file gone")
        media_map = {"webm": "video/webm", "mp4": "video/mp4", "mov": "video/quicktime", "ogg": "video/ogg"}
        return FileResponse(
            path=doc["path"],
            media_type=media_map.get(doc.get("ext", "webm"), "video/webm"),
            filename=f"prayer-{rec_id}.{doc.get('ext','webm')}",
        )

    @router.post("/kids/recordings/{rec_id}/comment")
    async def kids_comment_recording(
        rec_id: str,
        text: str = Form(...),
        user=Depends(get_current_user),
    ):
        text = (text or "").strip()
        if not text:
            raise HTTPException(400, "comment empty")
        if len(text) > 2000:
            raise HTTPException(400, "comment too long")
        doc = await db.kids_recordings.find_one({"id": rec_id}, {"_id": 0, "id": 1})
        if not doc:
            raise HTTPException(404, "recording not found")
        comment = {
            "id": uuid.uuid4().hex,
            "by_user_id": user["user_id"],
            "by_name": user.get("name") or user.get("email", "ولي الأمر"),
            "text": text,
            "created_at": _now(),
        }
        await db.kids_recordings.update_one(
            {"id": rec_id},
            {"$push": {"parent_comments": comment}, "$set": {"viewed_by_parent": True}},
        )
        return {"ok": True, "comment": comment}

    @router.delete("/kids/recordings/{rec_id}")
    async def kids_delete_recording(rec_id: str, user=Depends(get_current_user)):
        doc = await db.kids_recordings.find_one({"id": rec_id})
        if not doc:
            raise HTTPException(404, "not found")
        try:
            if os.path.exists(doc.get("path", "")):
                os.remove(doc["path"])
        except Exception:
            pass
        await db.kids_recordings.delete_one({"id": rec_id})
        return {"ok": True}

    # ═══════════════════════════════════════════════════════════════════════
    # KIDS PWA — Prayer audio tracks (father's recitation library)
    # ═══════════════════════════════════════════════════════════════════════
    KIDS_AUDIO_DIR = "/opt/zenrex/data/uploads/kids_audio"
    try:
        os.makedirs(KIDS_AUDIO_DIR, exist_ok=True)
    except Exception:
        pass

    @router.post("/kids/audio/upload")
    async def kids_upload_audio(
        file: UploadFile = File(...),
        title: str = Form(...),
        user=Depends(get_current_user),
    ):
        """Parent uploads a prayer/recitation audio track for kids to play during recording."""
        body = await file.read()
        if len(body) > 50 * 1024 * 1024:
            raise HTTPException(413, "audio too large (50MB max)")
        aid = uuid.uuid4().hex
        ext = (file.filename or "").split(".")[-1].lower() if file.filename else "mp3"
        if ext not in {"mp3", "m4a", "ogg", "wav", "webm"}:
            ext = "mp3"
        path = f"{KIDS_AUDIO_DIR}/{aid}.{ext}"
        with open(path, "wb") as f:
            f.write(body)
        await db.kids_audio_tracks.insert_one({
            "id": aid,
            "title": title.strip(),
            "ext": ext,
            "path": path,
            "size_bytes": len(body),
            "uploaded_by": user["user_id"],
            "created_at": _now(),
        })
        return {"ok": True, "id": aid, "url": f"/api/freebuild-chat/kids/audio/{aid}/stream"}

    @router.get("/kids/audio")
    async def kids_list_audio():
        cursor = db.kids_audio_tracks.find({}, {"_id": 0, "path": 0}).sort("created_at", -1).limit(100)
        items = await cursor.to_list(length=100)
        return {"ok": True, "items": items}

    @router.get("/kids/audio/{aid}/stream", include_in_schema=False)
    async def kids_stream_audio(aid: str):
        from fastapi.responses import FileResponse
        doc = await db.kids_audio_tracks.find_one({"id": aid})
        if not doc or not os.path.exists(doc.get("path", "")):
            raise HTTPException(404, "audio not found")
        media_map = {"mp3": "audio/mpeg", "m4a": "audio/mp4", "ogg": "audio/ogg", "wav": "audio/wav", "webm": "audio/webm"}
        return FileResponse(doc["path"], media_type=media_map.get(doc.get("ext","mp3"),"audio/mpeg"))

    @router.delete("/kids/audio/{aid}")
    async def kids_delete_audio(aid: str, user=Depends(get_current_user)):
        doc = await db.kids_audio_tracks.find_one({"id": aid})
        if doc:
            try:
                p = doc.get("path") or ""
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        await db.kids_audio_tracks.delete_one({"id": aid})
        return {"ok": True}

    @router.post("/kids/audio/{aid}/order")
    async def kids_set_audio_order(aid: str, order: int = Form(...), user=Depends(get_current_user)):
        await db.kids_audio_tracks.update_one({"id": aid}, {"$set": {"order": int(order)}})
        return {"ok": True}

    @router.post("/kids/audio/{aid}/prayer")
    async def kids_set_audio_prayer(aid: str, prayer: str = Form(...), user=Depends(get_current_user)):
        """Tag an audio with a prayer name (fajr/dhuhr/asr/maghrib/isha)."""
        await db.kids_audio_tracks.update_one({"id": aid}, {"$set": {"prayer": prayer.strip()}})
        return {"ok": True}

    # ═══════════════════════════════════════════════════════════════════════
    # KIDS PWA — Achievements (points, tasks, monthly earnings)
    # ═══════════════════════════════════════════════════════════════════════
    @router.get("/kids/achievements")
    async def kids_get_achievements(child_email: str):
        """Return achievements summary for a child.
        Points are derived from: prayer recordings count, comments resolved, video watches.
        """
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        child_email = child_email.strip().lower()
        rec_count = await db.kids_recordings.count_documents({"child_email": child_email})
        prayer_count = await db.kids_recordings.count_documents({"child_email": child_email, "rec_type": "prayer"})
        task_count = await db.kids_recordings.count_documents({"child_email": child_email, "rec_type": "task"})
        # Real points from ledger
        agg = await db.kids_points.aggregate([
            {"$match": {"child_email": child_email}},
            {"$group": {"_id": None, "sum": {"$sum": "$value"}}}
        ]).to_list(length=1)
        total_points = (agg[0]["sum"] if agg else 0)
        # Real streak
        days = await db.kids_points.distinct("created_at", {"child_email": child_email})
        day_set = {d[:10] for d in days if isinstance(d, str)}
        now = _dt.now(_tz.utc)
        streak = 0
        cur = now
        while cur.strftime("%Y-%m-%d") in day_set:
            streak += 1
            cur = cur - _td(days=1)
        # SAR
        sar_per_point = 0.1
        monthly_sar = round(total_points * sar_per_point, 2)
        # Suggested goals
        tasks = [
            {"id": "t1", "title": "صلِّ 5 صلوات اليوم", "progress": min(prayer_count, 5), "target": 5, "reward": 50},
            {"id": "t2", "title": "أنجز 5 مهام يومية", "progress": min(task_count, 5), "target": 5, "reward": 30},
            {"id": "t3", "title": "حافظ على streak لمدة 7 أيام", "progress": streak, "target": 7, "reward": 100},
        ]
        badges = []
        if prayer_count >= 5: badges.append({"id":"b1","emoji":"🌟","title":"5 صلوات"})
        if prayer_count >= 20: badges.append({"id":"b2","emoji":"🏅","title":"20 صلاة"})
        if prayer_count >= 50: badges.append({"id":"b3","emoji":"🥇","title":"بطل الصلوات"})
        if streak >= 3: badges.append({"id":"b4","emoji":"🔥","title":"3 أيام متتالية"})
        if streak >= 7: badges.append({"id":"b5","emoji":"⚡","title":"أسبوع كامل"})
        if task_count >= 10: badges.append({"id":"b6","emoji":"✅","title":"منجز المهام"})
        return {
            "ok": True,
            "child_email": child_email,
            "prayers_total": prayer_count,
            "tasks_total": task_count,
            "recordings_total": rec_count,
            "streak_days": streak,
            "total_points": total_points,
            "monthly_sar": monthly_sar,
            "sar_per_point": sar_per_point,
            "tasks": tasks,
            "badges": badges,
            "recent_recordings": rec_count,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # KIDS PWA — Server-side child accounts (parent creates, child logs in)
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/kids/accounts")
    async def kids_create_account(
        name: str = Form(...),
        pin: str = Form(...),
        user=Depends(get_current_user),
    ):
        name = (name or "").strip()
        pin = (pin or "").strip()
        if not name:
            raise HTTPException(400, "اسم الطفل مطلوب")
        if not pin or len(pin) < 4 or len(pin) > 12:
            raise HTTPException(400, "PIN يجب 4 إلى 12 خانة")
        # Build email — use deterministic slug; allow Arabic via lowering only ascii
        import re as _re
        slug = _re.sub(r"[^a-zA-Z0-9\u0600-\u06FF]+", "", name).lower()
        if not slug:
            slug = "child" + uuid.uuid4().hex[:6]
        email = f"{slug}@kids.zenrex.ai"
        # Ensure uniqueness per parent
        existing = await db.kids_accounts.find_one({"email": email, "parent_id": user["user_id"]})
        if existing:
            raise HTTPException(409, "يوجد طفل بنفس الاسم — اختر اسماً آخر أو احذف الموجود")
        doc = {
            "id": uuid.uuid4().hex,
            "email": email,
            "name": name,
            "pin": pin,  # stored as plain — short PIN, low value
            "parent_id": user["user_id"],
            "created_at": _now(),
            "is_active": True,
        }
        await db.kids_accounts.insert_one(doc)
        return {"ok": True, "email": email, "name": name, "pin": pin}

    @router.get("/kids/accounts")
    async def kids_list_accounts(user=Depends(get_current_user)):
        items = await db.kids_accounts.find(
            {"parent_id": user["user_id"], "is_active": True},
            {"_id": 0, "parent_id": 0},
        ).sort("created_at", 1).to_list(length=50)
        return {"ok": True, "items": items}

    @router.delete("/kids/accounts/{email}")
    async def kids_delete_account(email: str, user=Depends(get_current_user)):
        r = await db.kids_accounts.delete_one(
            {"email": email.lower(), "parent_id": user["user_id"]}
        )
        return {"ok": True, "deleted": r.deleted_count}

    @router.get("/kids/accounts/public")
    async def kids_list_public():
        """Public list of kid accounts (name + email only) for login dropdown."""
        items = await db.kids_accounts.find(
            {"is_active": True},
            {"_id": 0, "name": 1, "email": 1},
        ).sort("created_at", 1).to_list(length=50)
        return {"ok": True, "items": items}

    @router.post("/kids/login")
    async def kids_login(email: str = Form(...), pin: str = Form(...)):
        email = (email or "").strip().lower()
        pin = (pin or "").strip()
        doc = await db.kids_accounts.find_one({"email": email, "is_active": True})
        if not doc or doc.get("pin") != pin:
            raise HTTPException(401, "البريد أو كلمة المرور خاطئة")
        return {"ok": True, "email": email, "name": doc.get("name"), "id": doc.get("id")}

    # ═══════════════════════════════════════════════════════════════════════
    # KIDS PWA — Parent-managed CATEGORIES (videos)
    # ═══════════════════════════════════════════════════════════════════════
    DEFAULT_CATEGORIES = [
        {"id": "all", "icon": "🎬", "title": "الكل", "system": True, "order": 0},
        {"id": "games", "icon": "🎮", "title": "ألعاب", "system": False, "order": 1},
        {"id": "quran", "icon": "📖", "title": "قرآن", "system": False, "order": 2},
        {"id": "educational", "icon": "🎓", "title": "تعليمي", "system": False, "order": 3},
    ]

    async def _ensure_default_categories(parent_id: str):
        n = await db.kids_categories.count_documents({"parent_id": parent_id})
        if n > 0:
            return
        for c in DEFAULT_CATEGORIES:
            await db.kids_categories.insert_one({
                **c,
                "parent_id": parent_id,
                "created_at": _now(),
            })

    @router.get("/kids/categories")
    async def kids_list_categories(parent_id: Optional[str] = None):
        """Public — Kids app reads categories. If parent_id missing, uses first parent."""
        pid = parent_id
        if not pid:
            any_parent = await db.kids_accounts.find_one({}, {"parent_id": 1})
            pid = any_parent.get("parent_id") if any_parent else None
        if pid:
            await _ensure_default_categories(pid)
        cursor = db.kids_categories.find({"parent_id": pid}, {"_id": 0, "parent_id": 0}).sort("order", 1)
        items = await cursor.to_list(length=100)
        return {"ok": True, "items": items}

    @router.post("/kids/categories")
    async def kids_add_category(
        title: str = Form(...),
        icon: str = Form("🎬"),
        order: int = Form(99),
        user=Depends(get_current_user),
    ):
        title = (title or "").strip()
        if not title:
            raise HTTPException(400, "العنوان مطلوب")
        if len(title) > 40:
            raise HTTPException(400, "العنوان طويل جداً")
        import re as _re
        cid = _re.sub(r"[^a-zA-Z0-9\u0600-\u06FF]+", "_", title).lower().strip("_")[:30] or uuid.uuid4().hex[:8]
        # Uniqueness per parent
        exists = await db.kids_categories.find_one({"id": cid, "parent_id": user["user_id"]})
        if exists:
            raise HTTPException(409, "تصنيف موجود بنفس الاسم")
        doc = {
            "id": cid,
            "icon": icon[:8] if icon else "🎬",
            "title": title,
            "system": False,
            "order": int(order),
            "parent_id": user["user_id"],
            "created_at": _now(),
        }
        await db.kids_categories.insert_one(doc)
        return {"ok": True, "category": {k: v for k, v in doc.items() if k not in ("parent_id", "_id")}}

    @router.delete("/kids/categories/{cid}")
    async def kids_delete_category(cid: str, user=Depends(get_current_user)):
        doc = await db.kids_categories.find_one({"id": cid, "parent_id": user["user_id"]})
        if not doc:
            raise HTTPException(404, "غير موجود")
        if doc.get("system"):
            raise HTTPException(400, "تصنيف نظامي لا يُحذف")
        r = await db.kids_categories.delete_one({"id": cid, "parent_id": user["user_id"]})
        return {"ok": True, "deleted": r.deleted_count}

    # ═══════════════════════════════════════════════════════════════════════
    # KIDS PWA — Parent-managed TASKS (daily tasks for child)
    # ═══════════════════════════════════════════════════════════════════════
    DEFAULT_PARENT_TASKS = [
        {"id": "t_brush_am", "icon": "🪥", "title": "فرش الأسنان (صباحاً)", "points": 5, "needs_camera": True, "order": 1},
        {"id": "t_brush_pm", "icon": "🪥", "title": "فرش الأسنان (قبل النوم)", "points": 5, "needs_camera": True, "order": 2},
        {"id": "t_shower", "icon": "🛁", "title": "الاستحمام", "points": 10, "needs_camera": False, "order": 3},
        {"id": "t_breakfast", "icon": "🍽️", "title": "تناول الفطور", "points": 5, "needs_camera": False, "order": 4},
        {"id": "t_read", "icon": "📚", "title": "قراءة 10 دقائق", "points": 10, "needs_camera": True, "order": 5},
        {"id": "t_room", "icon": "🧹", "title": "ترتيب الغرفة", "points": 8, "needs_camera": True, "order": 6},
    ]

    async def _ensure_default_tasks(parent_id: str):
        n = await db.kids_parent_tasks.count_documents({"parent_id": parent_id})
        if n > 0:
            return
        for t in DEFAULT_PARENT_TASKS:
            await db.kids_parent_tasks.insert_one({
                **t, "parent_id": parent_id, "created_at": _now(), "is_active": True,
            })

    @router.get("/kids/parent-tasks")
    async def kids_list_parent_tasks(parent_id: Optional[str] = None):
        pid = parent_id
        if not pid:
            any_parent = await db.kids_accounts.find_one({}, {"parent_id": 1})
            pid = any_parent.get("parent_id") if any_parent else None
        if pid:
            await _ensure_default_tasks(pid)
        cursor = db.kids_parent_tasks.find(
            {"parent_id": pid, "is_active": True}, {"_id": 0, "parent_id": 0}
        ).sort("order", 1)
        items = await cursor.to_list(length=200)
        return {"ok": True, "items": items}

    @router.post("/kids/parent-tasks")
    async def kids_add_parent_task(
        title: str = Form(...),
        icon: str = Form("✅"),
        points: int = Form(5),
        needs_camera: bool = Form(True),
        needs_before_after: bool = Form(False),
        order: int = Form(99),
        user=Depends(get_current_user),
    ):
        title = (title or "").strip()
        if not title:
            raise HTTPException(400, "عنوان المهمة مطلوب")
        if len(title) > 80:
            raise HTTPException(400, "عنوان طويل")
        tid = "t_" + uuid.uuid4().hex[:10]
        doc = {
            "id": tid,
            "icon": icon[:8] if icon else "✅",
            "title": title,
            "points": max(1, min(int(points or 5), 500)),
            "needs_camera": bool(needs_camera),
            "needs_before_after": bool(needs_before_after),
            "order": int(order),
            "parent_id": user["user_id"],
            "is_active": True,
            "created_at": _now(),
        }
        await db.kids_parent_tasks.insert_one(doc)
        return {"ok": True, "task": {k: v for k, v in doc.items() if k not in ("parent_id", "_id")}}

    @router.delete("/kids/parent-tasks/{tid}")
    async def kids_delete_parent_task(tid: str, user=Depends(get_current_user)):
        r = await db.kids_parent_tasks.update_one(
            {"id": tid, "parent_id": user["user_id"]},
            {"$set": {"is_active": False}},
        )
        return {"ok": True, "deleted": r.modified_count}

    # ═══════════════════════════════════════════════════════════════════════
    # KIDS PWA — Parent-managed DHIKR (Islamic remembrance counters)
    # ═══════════════════════════════════════════════════════════════════════
    DEFAULT_DHIKR = [
        {"id": "dh_subhanallah", "icon": "📿", "title": "سبحان الله", "target": 33, "points": 5, "order": 1},
        {"id": "dh_alhamdulillah", "icon": "📿", "title": "الحمد لله", "target": 33, "points": 5, "order": 2},
        {"id": "dh_allahuakbar", "icon": "📿", "title": "الله أكبر", "target": 34, "points": 5, "order": 3},
        {"id": "dh_lailaha", "icon": "📿", "title": "لا إله إلا الله", "target": 100, "points": 10, "order": 4},
        {"id": "dh_istighfar", "icon": "🤲", "title": "أستغفر الله", "target": 100, "points": 10, "order": 5},
    ]

    async def _ensure_default_dhikr(parent_id: str):
        n = await db.kids_dhikr.count_documents({"parent_id": parent_id})
        if n > 0:
            return
        for d_ in DEFAULT_DHIKR:
            await db.kids_dhikr.insert_one({**d_, "parent_id": parent_id, "is_active": True, "created_at": _now()})

    @router.get("/kids/dhikr")
    async def kids_list_dhikr(parent_id: Optional[str] = None):
        pid = parent_id
        if not pid:
            any_parent = await db.kids_accounts.find_one({}, {"parent_id": 1})
            pid = any_parent.get("parent_id") if any_parent else None
        if pid:
            await _ensure_default_dhikr(pid)
        cursor = db.kids_dhikr.find(
            {"parent_id": pid, "is_active": True}, {"_id": 0, "parent_id": 0}
        ).sort("order", 1)
        items = await cursor.to_list(length=100)
        return {"ok": True, "items": items}

    @router.post("/kids/dhikr")
    async def kids_add_dhikr(
        title: str = Form(...),
        icon: str = Form("📿"),
        target: int = Form(33),
        points: int = Form(5),
        order: int = Form(99),
        user=Depends(get_current_user),
    ):
        title = (title or "").strip()
        if not title:
            raise HTTPException(400, "عنوان الذكر مطلوب")
        if len(title) > 80:
            raise HTTPException(400, "عنوان طويل")
        did = "dh_" + uuid.uuid4().hex[:10]
        doc = {
            "id": did,
            "icon": icon[:8] if icon else "📿",
            "title": title,
            "target": max(1, min(int(target or 33), 10000)),
            "points": max(1, min(int(points or 5), 500)),
            "order": int(order),
            "parent_id": user["user_id"],
            "is_active": True,
            "created_at": _now(),
        }
        await db.kids_dhikr.insert_one(doc)
        return {"ok": True, "dhikr": {k: v for k, v in doc.items() if k not in ("parent_id", "_id")}}

    @router.delete("/kids/dhikr/{did}")
    async def kids_delete_dhikr(did: str, user=Depends(get_current_user)):
        r = await db.kids_dhikr.update_one(
            {"id": did, "parent_id": user["user_id"]},
            {"$set": {"is_active": False}},
        )
        return {"ok": True, "deleted": r.modified_count}

    # ═══════════════════════════════════════════════════════════════════════
    # KIDS PWA — Auto-categorize a video by title using Emergent LLM
    # ═══════════════════════════════════════════════════════════════════════
    async def _categorize_one(video_id: str, parent_id: str):
        """Internal helper — used by both single + batch endpoints."""
        media = await db.freebuild_media_assets.find_one({"id": video_id})
        if not media:
            return {"ok": False, "video_id": video_id, "error": "not_found"}
        await _ensure_default_categories(parent_id)
        cats = await db.kids_categories.find(
            {"parent_id": parent_id, "id": {"$ne": "all"}},
            {"_id": 0}
        ).to_list(length=100)
        if not cats:
            return {"ok": False, "video_id": video_id, "error": "no_categories"}
        cat_list = ", ".join([f"{c['id']} ({c['title']})" for c in cats])
        title = media.get("prompt") or media.get("title") or media.get("filename") or ""
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            chat = LlmChat(
                api_key=os.environ["EMERGENT_LLM_KEY"],
                session_id=f"cat-{video_id}",
                system_message=(
                    f"You are a video categorizer for an Islamic kids app. "
                    f"Available categories (id): {cat_list}. "
                    f"Reply ONLY with the category id that best matches the video title. "
                    f"If unclear, reply 'educational'."
                ),
            ).with_model("anthropic", "claude-haiku-4-5")
            resp = await chat.send_message(UserMessage(text=f"Title: {title}"))
            cid = str(resp).strip().lower().split()[0]
            valid_ids = {c["id"] for c in cats}
            if cid not in valid_ids:
                cid = "educational" if "educational" in valid_ids else cats[0]["id"]
            await db.freebuild_media_assets.update_one(
                {"id": video_id}, {"$set": {"category": cid, "categorized_at": _now()}}
            )
            return {"ok": True, "video_id": video_id, "category": cid, "title": title[:80]}
        except Exception as e:
            logger.warning(f"[auto-categorize] {e}")
            tl = title.lower()
            fallback = None
            for c in cats:
                key = c["title"].lower()
                if key in tl or c["id"] in tl:
                    fallback = c["id"]; break
            fallback = fallback or ("educational" if any(c["id"] == "educational" for c in cats) else cats[0]["id"])
            await db.freebuild_media_assets.update_one(
                {"id": video_id}, {"$set": {"category": fallback, "categorized_at": _now(), "categorized_fallback": True}}
            )
            return {"ok": True, "video_id": video_id, "category": fallback, "fallback": True}

    @router.post("/kids/auto-categorize")
    async def kids_auto_categorize(
        video_id: str = Form(...),
        user=Depends(get_current_user),
    ):
        r = await _categorize_one(video_id, user["user_id"])
        if not r.get("ok"):
            raise HTTPException(404 if r.get("error") == "not_found" else 400, r.get("error", "fail"))
        return r

    @router.post("/kids/auto-categorize/all")
    async def kids_auto_categorize_all(user=Depends(get_current_user)):
        """Batch — categorize all approved videos missing a category."""
        cursor = db.freebuild_media_assets.find(
            {"approved": True, "$or": [{"category": {"$exists": False}}, {"category": None}, {"category": ""}]},
            {"id": 1},
        ).limit(50)
        ids = [d["id"] async for d in cursor]
        results = []
        for vid in ids:
            r = await _categorize_one(vid, user["user_id"])
            results.append(r)
        return {"ok": True, "count": len(ids), "results": results}

    # ═══════════════════════════════════════════════════════════════════════
    # KIDS PWA — Video Metadata Extraction (preview before download)
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/kids/videos/import")
    async def kids_import_video(
        url: str = Form(...),
        title: str = Form(""),
        user=Depends(get_current_user),
    ):
        """One-call import: download + approve + AI-categorize.
        Returns the imported video record ready to show in feed."""
        if not url or not url.startswith(("http://", "https://")):
            raise HTTPException(400, "Invalid URL")
        # Step 1: download via existing /media/download logic by calling it
        import subprocess as _sp
        import json as _json
        os.makedirs(MEDIA_DIR, exist_ok=True)
        file_id = uuid.uuid4().hex[:16]
        out_path = os.path.join(MEDIA_DIR, f"{file_id}.%(ext)s")
        meta_path = os.path.join(MEDIA_DIR, f"{file_id}.info.json")
        # Detect platform for cookies
        url_low = url.lower()
        platform = ""
        if "youtube" in url_low or "youtu.be" in url_low: platform = "youtube"
        elif "tiktok" in url_low: platform = "tiktok"
        elif "instagram" in url_low: platform = "instagram"
        cookies_args = []
        if platform:
            ck = _cookie_path_for(user["user_id"], platform)
            if os.path.exists(ck):
                cookies_args = ["--cookies", ck]
        fmt_args = ["-f", "bv*[height<=720][ext=mp4][vcodec*=avc1]+ba[ext=m4a]/bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/b[height<=720]/b[ext=mp4]/best", "-S", "vcodec:h264,res:720,acodec:m4a", "--merge-output-format", "mp4", "--recode-video", "mp4", "--postprocessor-args", "-c:v libx264 -preset fast -crf 23 -c:a aac -movflags +faststart"]
        cmd = ["yt-dlp", "--no-playlist", "--no-warnings", "--restrict-filenames", "--write-info-json", "-o", out_path] + cookies_args + fmt_args + [url]
        try:
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=_sp.PIPE, stderr=_sp.PIPE)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=150)
            if proc.returncode != 0:
                err = (stderr.decode("utf-8", errors="ignore") or "")[-400:]
                if "403" in err.lower() or "ip address is blocked" in err.lower():
                    raise HTTPException(451, f"ip_blocked: ارفع cookies.txt من قسم البوت لـ{platform or 'يوتيوب'}")
                raise HTTPException(502, f"فشل التحميل: {err}")
        except FileNotFoundError:
            raise HTTPException(500, "yt-dlp not installed")
        # Find produced file
        produced = [f for f in os.listdir(MEDIA_DIR) if f.startswith(file_id) and not f.endswith(".info.json")]
        if not produced:
            raise HTTPException(500, "no file produced")
        actual_file = produced[0]
        actual_ext = actual_file.rsplit(".", 1)[-1]
        # Read metadata
        actual_title = title
        thumbnail = None
        duration = None
        try:
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    m = _json.load(f)
                actual_title = title or m.get("title", "") or ""
                thumbnail = m.get("thumbnail")
                duration = m.get("duration")
        except Exception:
            pass
        public_url = f"/api/freebuild-chat/media/file/{file_id}.{actual_ext}"
        # Insert APPROVED + AI categorize
        await db.freebuild_media_assets.insert_one({
            "id": file_id,
            "user_id": user["user_id"],
            "filename": actual_file,
            "ext": actual_ext,
            "source_url": url,
            "title": actual_title,
            "prompt": actual_title,
            "duration": duration,
            "thumbnail_url": thumbnail,
            "category": None,
            "format": "mp4_720p",
            "file_url": public_url,
            "public_url": public_url,
            "url": public_url,
            "approved": True,
            "approved_at": _now(),
            "created_at": _now(),
        })
        # AI categorize
        cat_result = None
        try:
            cat_result = await _categorize_one(file_id, user["user_id"])
        except Exception as e:
            logger.warning(f"[import] categorize failed: {e}")
        return {
            "ok": True,
            "id": file_id,
            "url": public_url,
            "title": actual_title,
            "thumbnail": thumbnail,
            "category": cat_result.get("category") if cat_result else None,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # KIDS PWA — Parent view of all child recordings
    # ═══════════════════════════════════════════════════════════════════════
    # ═══════════════════════════════════════════════════════════════════════
    # KIDS PWA — Quran memorization (full 114 surahs + parent approval)
    # ═══════════════════════════════════════════════════════════════════════
    _QURAN_CACHE = {}  # surah_num -> dict

    @router.get("/kids/quran/surahs")
    async def kids_quran_surahs():
        """List all 114 surahs (number, name, ayah count, revelation place)."""
        if "_list" in _QURAN_CACHE:
            return {"ok": True, "items": _QURAN_CACHE["_list"]}
        import urllib.request, json as _json
        try:
            req = urllib.request.Request("https://api.alquran.cloud/v1/surah", headers={"User-Agent": "Zenrex/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = _json.loads(r.read())
            items = []
            for s in data.get("data", []):
                items.append({
                    "number": s.get("number"),
                    "name": s.get("name"),
                    "name_en": s.get("englishName"),
                    "ayahs": s.get("numberOfAyahs"),
                    "revelation": "مكية" if s.get("revelationType") == "Meccan" else "مدنية",
                })
            _QURAN_CACHE["_list"] = items
            return {"ok": True, "items": items}
        except Exception as e:
            logger.error(f"[quran] surah list fail: {e}")
            raise HTTPException(502, f"تعذّر جلب قائمة السور: {e}")

    @router.get("/kids/quran/surah/{num}")
    async def kids_quran_surah(num: int, reciter: str = "ar.alafasy"):
        """Full surah: text + audio URL per ayah from a reciter.
        reciter examples: ar.alafasy (مشاري), ar.abdulbasitmurattal (عبدالباسط), ar.husary, ar.ghamadi"""
        if num < 1 or num > 114:
            raise HTTPException(400, "رقم السورة بين 1 و 114")
        cache_key = f"s{num}_{reciter}"
        if cache_key in _QURAN_CACHE:
            return {"ok": True, **_QURAN_CACHE[cache_key]}
        import urllib.request, json as _json
        try:
            # Get text + reciter audio in one call
            req = urllib.request.Request(
                f"https://api.alquran.cloud/v1/surah/{num}/editions/quran-uthmani,{reciter}",
                headers={"User-Agent": "Zenrex/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                data = _json.loads(r.read())
            editions = data.get("data", [])
            if len(editions) < 2:
                raise HTTPException(502, "بيانات السورة غير مكتملة")
            text_edition = next((e for e in editions if "quran-uthmani" in e.get("edition", {}).get("identifier", "")), editions[0])
            audio_edition = next((e for e in editions if e != text_edition), editions[1])
            text_ayahs = text_edition.get("ayahs", [])
            audio_ayahs = audio_edition.get("ayahs", [])
            ayahs = []
            for i, t in enumerate(text_ayahs):
                aud = audio_ayahs[i] if i < len(audio_ayahs) else {}
                ayahs.append({
                    "number_in_surah": t.get("numberInSurah"),
                    "text": t.get("text"),
                    "audio": aud.get("audio") or aud.get("audioSecondary", [None])[0],
                })
            result = {
                "number": num,
                "name": text_edition.get("name"),
                "name_en": text_edition.get("englishName"),
                "ayahs": ayahs,
                "reciter": reciter,
            }
            _QURAN_CACHE[cache_key] = result
            return {"ok": True, **result}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[quran] surah {num} fail: {e}")
            raise HTTPException(502, f"تعذّر جلب السورة: {e}")

    @router.post("/kids/quran/submit")
    async def kids_quran_submit(
        file: UploadFile = File(...),
        child_email: str = Form(...),
        surah_num: int = Form(...),
        ayah_from: int = Form(1),
        ayah_to: int = Form(0),
        duration_sec: float = Form(0.0),
        proposed_points: int = Form(0),
    ):
        """Child uploads memorization recording. Goes through:
           1. AI verification via Whisper (sets ai_verdict + ai_transcript)
           2. Parent review (ai_verdict=ok) → status='pending_parent'
           3. AI rejected → status='rejected_ai'
           4. Parent approves → status='approved' + points awarded
        """
        child_email = (child_email or "").strip().lower()
        _kids_re = re.compile(r"^[^@\s]+@kids\.[\w.\-]+$")
        if not _kids_re.match(child_email):
            raise HTTPException(403, "child_email must be a @kids.* address")
        if surah_num < 1 or surah_num > 114:
            raise HTTPException(400, "invalid surah_num")
        # Save audio file
        body = await file.read()
        if not body or len(body) < 1024:
            raise HTTPException(400, "ملف صوتي صغير جداً")
        os.makedirs(MEDIA_DIR, exist_ok=True)
        rec_id = uuid.uuid4().hex
        ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "webm"
        fname = f"quran_{rec_id}.{ext}"
        path = os.path.join(MEDIA_DIR, fname)
        with open(path, "wb") as f:
            f.write(body)
        # Default points: 20 per ayah range max 200
        if ayah_to < ayah_from: ayah_to = ayah_from
        ayah_count = ayah_to - ayah_from + 1
        points = max(int(proposed_points or 0), min(20 * ayah_count, 200))
        # AI verification (try Whisper)
        ai_verdict = "skipped"
        ai_transcript = ""
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
            chat = LlmChat(
                api_key=os.environ["EMERGENT_LLM_KEY"],
                session_id=f"quran-{rec_id}",
                system_message="You transcribe Arabic audio. Return ONLY the Arabic transcript without diacritics, no English, no comments."
            ).with_model("openai", "whisper-1")
            # Note: whisper integration may differ — fallback to text comparison
            try:
                msg = UserMessage(text="Transcribe this audio.", file_contents=[FileContentWithMimeType(file_path=path, mime_type="audio/webm")])
                resp = await chat.send_message(msg)
                ai_transcript = str(resp).strip()
                ai_verdict = "transcribed"  # We'll let parent be the final judge
            except Exception as e2:
                logger.warning(f"[quran-ai] Whisper failed: {e2}")
                ai_verdict = "skipped"
        except Exception as e:
            logger.warning(f"[quran-ai] {e}")
            ai_verdict = "skipped"

        doc = {
            "id": rec_id,
            "child_email": child_email,
            "child_name": "",
            "surah_num": surah_num,
            "ayah_from": ayah_from,
            "ayah_to": ayah_to,
            "duration_sec": duration_sec,
            "file_path": path,
            "size_bytes": len(body),
            "ext": ext,
            "ai_verdict": ai_verdict,
            "ai_transcript": ai_transcript,
            "status": "pending_parent",  # always parent-review for safety
            "proposed_points": points,
            "awarded_points": 0,
            "parent_note": "",
            "created_at": _now(),
            "reviewed_at": None,
        }
        # Fetch child name
        kid = await db.kids_accounts.find_one({"email": child_email}, {"name": 1})
        if kid: doc["child_name"] = kid.get("name", "")
        await db.kids_quran_submissions.insert_one(doc)
        return {"ok": True, "id": rec_id, "status": doc["status"], "ai_verdict": ai_verdict, "proposed_points": points}

    @router.get("/kids/quran/submissions/{rec_id}/audio")
    async def kids_quran_audio(rec_id: str):
        doc = await db.kids_quran_submissions.find_one({"id": rec_id})
        if not doc or not os.path.exists(doc.get("file_path", "")):
            raise HTTPException(404, "audio not found")
        from fastapi.responses import FileResponse
        return FileResponse(doc["file_path"], media_type=f"audio/{doc.get('ext','webm')}")

    @router.get("/kids/quran/submissions")
    async def kids_quran_submissions_list(
        child_email: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ):
        q = {}
        if child_email: q["child_email"] = child_email.strip().lower()
        if status: q["status"] = status
        cur = db.kids_quran_submissions.find(q, {"_id": 0, "file_path": 0}).sort("created_at", -1).limit(int(limit))
        items = await cur.to_list(length=int(limit))
        return {"ok": True, "items": items}

    @router.post("/kids/quran/submissions/{rec_id}/approve")
    async def kids_quran_approve(rec_id: str, note: str = Form(""), user=Depends(get_current_user)):
        doc = await db.kids_quran_submissions.find_one({"id": rec_id})
        if not doc: raise HTTPException(404, "غير موجود")
        if doc["status"] == "approved": return {"ok": True, "already": True}
        pts = doc.get("proposed_points", 20)
        await db.kids_quran_submissions.update_one(
            {"id": rec_id},
            {"$set": {"status": "approved", "awarded_points": pts, "parent_note": note, "reviewed_at": _now()}}
        )
        # Award points
        await db.kids_points.insert_one({
            "id": uuid.uuid4().hex,
            "child_email": doc["child_email"],
            "kind": "quran",
            "value": pts,
            "meta": {"submission_id": rec_id, "surah_num": doc["surah_num"]},
            "created_at": _now(),
        })
        return {"ok": True, "awarded": pts}

    @router.get("/kids/quran/plan")
    async def kids_quran_plan_get(child_email: str):
        ce = (child_email or "").strip().lower()
        doc = await db.kids_quran_plans.find_one({"child_email": ce}, {"_id": 0})
        return {"ok": True, "plan": doc or {"surahs": [], "note": "", "type": "free"}}

    @router.post("/kids/quran/plan")
    async def kids_quran_plan_set(
        child_email: str = Form(...),
        surahs: str = Form(""),
        note: str = Form(""),
        plan_type: str = Form("custom"),
        user=Depends(get_current_user),
    ):
        import json as _json
        ce = (child_email or "").strip().lower()
        try:
            arr = _json.loads(surahs) if surahs else []
            arr = [int(x) for x in arr if 1 <= int(x) <= 114]
        except Exception:
            arr = []
        if plan_type == "random":
            import random
            n = max(5, min(int(note) if note.isdigit() else 10, 30))
            arr = random.sample(range(1, 115), n)
            note = f"عشوائي: {n} سورة"
        doc = {"child_email": ce, "surahs": arr, "note": note, "type": plan_type, "updated_at": _now()}
        await db.kids_quran_plans.update_one({"child_email": ce}, {"$set": doc}, upsert=True)
        return {"ok": True, "plan": doc}

    @router.post("/kids/quran/submissions/{rec_id}/reject")
    async def kids_quran_reject(rec_id: str, note: str = Form(""), user=Depends(get_current_user)):
        await db.kids_quran_submissions.update_one(
            {"id": rec_id},
            {"$set": {"status": "rejected", "parent_note": note, "reviewed_at": _now()}}
        )
        return {"ok": True}

    # ═══════════════════════════════════════════════════════════════════════
    # KIDS PWA — Weekly Challenge (parent picks surahs, kids compete)
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/kids/challenge/create")
    async def kids_challenge_create(
        surah_nums: str = Form("[]"),
        days: int = Form(7),
        mode: str = Form("manual"),  # 'manual' or 'random'
        random_count: int = Form(3),
        user=Depends(get_current_user),
    ):
        """Create a weekly Quran-memorization challenge among parent's kids.

        mode='manual' → surah_nums is a JSON array like "[1,112,113]"
        mode='random' → server picks random_count surahs (3..10) from 1..114
        """
        import json as _json, random as _random
        try:
            arr = _json.loads(surah_nums) if surah_nums else []
            arr = [int(x) for x in arr if 1 <= int(x) <= 114]
        except Exception:
            arr = []
        if mode == "random":
            n = max(1, min(int(random_count) if random_count else 3, 10))
            arr = sorted(_random.sample(range(1, 115), n))
        if not arr:
            raise HTTPException(400, "اختر سورة واحدة على الأقل")
        days = max(1, min(int(days or 7), 30))
        now = _now()
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        start = _dt.now(_tz.utc)
        end = start + _td(days=days)
        # End any existing active challenge for this parent first
        await db.kids_weekly_challenges.update_many(
            {"parent_id": user["user_id"], "status": "active"},
            {"$set": {"status": "ended", "ended_at": now}},
        )
        cid = uuid.uuid4().hex
        doc = {
            "id": cid,
            "parent_id": user["user_id"],
            "surah_nums": arr,
            "mode": mode,
            "days": days,
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "status": "active",
            "winner_email": None,
            "created_at": now,
        }
        await db.kids_weekly_challenges.insert_one(doc)
        return {"ok": True, "challenge": {**doc, "_id": None}}

    async def _compute_challenge_progress(ch: dict) -> dict:
        """Build per-child progress for a challenge document."""
        # Get kids of this parent
        kids = await db.kids_accounts.find(
            {"parent_id": ch["parent_id"]}, {"email": 1, "name": 1}
        ).to_list(length=20)
        emails = [k["email"] for k in kids]
        kid_name = {k["email"]: k.get("name", k["email"]) for k in kids}
        # All approved submissions for challenge surahs within window
        q = {
            "child_email": {"$in": emails},
            "surah_num": {"$in": ch["surah_nums"]},
            "status": "approved",
            "reviewed_at": {"$gte": ch["start_at"], "$lte": ch["end_at"]},
        }
        subs = await db.kids_quran_submissions.find(q, {"_id": 0}).to_list(length=500)
        per_child = {e: {"name": kid_name[e], "approved_surahs": set(), "approved_count": 0, "points": 0} for e in emails}
        for s in subs:
            ce = s.get("child_email")
            if ce not in per_child:
                continue
            per_child[ce]["approved_surahs"].add(s["surah_num"])
            per_child[ce]["approved_count"] += 1
            per_child[ce]["points"] += int(s.get("awarded_points", 0))
        leaderboard = []
        for e, st in per_child.items():
            leaderboard.append({
                "child_email": e,
                "child_name": st["name"],
                "approved_surahs": sorted(st["approved_surahs"]),
                "unique_surahs_done": len(st["approved_surahs"]),
                "approved_count": st["approved_count"],
                "points": st["points"],
                "completion_pct": int(100 * len(st["approved_surahs"]) / max(1, len(ch["surah_nums"]))),
            })
        # Sort: unique surahs DESC, then total approved count DESC, then points DESC
        leaderboard.sort(key=lambda x: (-x["unique_surahs_done"], -x["approved_count"], -x["points"]))
        return {"leaderboard": leaderboard, "total_surahs": len(ch["surah_nums"])}

    @router.get("/kids/challenge/active")
    async def kids_challenge_active(parent_id: Optional[str] = None):
        """Get currently active challenge for the parent (auto-detect if not given)
        + per-child leaderboard."""
        pid = parent_id
        if not pid:
            any_parent = await db.kids_accounts.find_one({}, {"parent_id": 1})
            pid = any_parent.get("parent_id") if any_parent else None
        if not pid:
            return {"ok": True, "challenge": None}
        ch = await db.kids_weekly_challenges.find_one(
            {"parent_id": pid, "status": "active"}, {"_id": 0}, sort=[("created_at", -1)]
        )
        if not ch:
            return {"ok": True, "challenge": None}
        progress = await _compute_challenge_progress(ch)
        return {"ok": True, "challenge": ch, **progress}

    @router.post("/kids/challenge/end")
    async def kids_challenge_end(challenge_id: str = Form(...), user=Depends(get_current_user)):
        ch = await db.kids_weekly_challenges.find_one({"id": challenge_id, "parent_id": user["user_id"]})
        if not ch:
            raise HTTPException(404, "التحدي غير موجود")
        if ch["status"] != "active":
            return {"ok": True, "already": True}
        progress = await _compute_challenge_progress(ch)
        lb = progress["leaderboard"]
        winner_email = lb[0]["child_email"] if lb and lb[0]["approved_count"] > 0 else None
        await db.kids_weekly_challenges.update_one(
            {"id": challenge_id},
            {"$set": {"status": "ended", "winner_email": winner_email, "ended_at": _now()}},
        )
        # Award 100-point badge to winner
        if winner_email:
            await db.kids_points.insert_one({
                "id": uuid.uuid4().hex,
                "child_email": winner_email,
                "kind": "challenge_winner",
                "value": 100,
                "meta": {"challenge_id": challenge_id, "surahs": ch["surah_nums"]},
                "created_at": _now(),
            })
        return {"ok": True, "winner_email": winner_email, "leaderboard": lb}

    @router.get("/kids/challenge/history")
    async def kids_challenge_history(parent_id: Optional[str] = None, limit: int = 20):
        pid = parent_id
        if not pid:
            any_parent = await db.kids_accounts.find_one({}, {"parent_id": 1})
            pid = any_parent.get("parent_id") if any_parent else None
        if not pid:
            return {"ok": True, "items": []}
        cur = db.kids_weekly_challenges.find(
            {"parent_id": pid}, {"_id": 0}
        ).sort("created_at", -1).limit(int(limit))
        items = await cur.to_list(length=int(limit))
        return {"ok": True, "items": items}


    @router.get("/kids/parent-recordings")
    async def kids_parent_recordings(parent_id: Optional[str] = None, limit: int = 50):
        pid = parent_id
        if not pid:
            any_parent = await db.kids_accounts.find_one({}, {"parent_id": 1})
            pid = any_parent.get("parent_id") if any_parent else None
        if not pid:
            return {"ok": True, "items": []}
        # Get kids of this parent
        kids = await db.kids_accounts.find({"parent_id": pid}, {"email": 1, "name": 1}).to_list(length=20)
        kid_map = {k["email"]: k.get("name", k["email"]) for k in kids}
        emails = list(kid_map.keys())
        if not emails:
            return {"ok": True, "items": []}
        cursor = db.kids_recordings.find(
            {"child_email": {"$in": emails}}, {"_id": 0, "path": 0}
        ).sort("created_at", -1).limit(int(limit))
        items = await cursor.to_list(length=int(limit))
        for it in items:
            it["child_name"] = kid_map.get(it.get("child_email"), it.get("child_email"))
        return {"ok": True, "items": items}

    @router.post("/kids/video-metadata")
    async def kids_video_metadata(
        url: str = Form(...),
        user=Depends(get_current_user),
    ):
        """Use yt-dlp --dump-json to fetch video info without downloading."""
        import subprocess as _sp
        import json as _json
        url = (url or "").strip()
        if not url:
            raise HTTPException(400, "URL مطلوب")
        ck = _cookie_path_for(user["user_id"], "youtube" if "youtube" in url else "tiktok") if "_cookie_path_for" in globals() else None
        cmd = ["yt-dlp", "--dump-json", "--no-download", "--skip-download", "--no-warnings", url]
        if ck and os.path.exists(ck):
            cmd.extend(["--cookies", ck])
        try:
            r = _sp.run(cmd, capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                # Don't fail entirely — return URL with empty metadata so user can still add
                return {"ok": True, "url": url, "title": "", "thumbnail": "", "duration": 0, "uploader": "", "error": r.stderr[:200]}
            info = _json.loads(r.stdout.strip().split("\n")[0])
            return {
                "ok": True,
                "url": url,
                "title": info.get("title") or info.get("fulltitle") or "",
                "thumbnail": info.get("thumbnail") or "",
                "duration": info.get("duration") or 0,
                "uploader": info.get("uploader") or info.get("channel") or "",
                "description": (info.get("description") or "")[:300],
                "platform": info.get("extractor_key") or info.get("extractor") or "",
            }
        except Exception as e:
            logger.warning(f"[video-metadata] {e}")
            return {"ok": True, "url": url, "title": "", "thumbnail": "", "duration": 0, "uploader": "", "error": str(e)}

    @router.get("/kids/parent-summary")
    async def kids_parent_summary(parent_id: Optional[str] = None):
        """Aggregated dashboard view: list children + per-child stats."""
        pid = parent_id
        if not pid:
            any_parent = await db.kids_accounts.find_one({}, {"parent_id": 1})
            pid = any_parent.get("parent_id") if any_parent else None
        if not pid:
            return {"ok": True, "children": [], "totals": {}}
        # Get all kids
        kids = await db.kids_accounts.find(
            {"parent_id": pid, "is_active": True}, {"_id": 0, "parent_id": 0}
        ).to_list(length=20)
        children = []
        total_points = 0
        total_recs = 0
        for kid in kids:
            email = kid["email"]
            # Points
            agg = await db.kids_points.aggregate([
                {"$match": {"child_email": email}},
                {"$group": {"_id": "$kind", "sum": {"$sum": "$value"}, "n": {"$sum": 1}}}
            ]).to_list(length=20)
            by_kind = {a["_id"]: {"points": a["sum"], "count": a["n"]} for a in agg}
            pts = sum(a["sum"] for a in agg)
            # Recordings
            recs = await db.kids_recordings.count_documents({"child_email": email})
            prayer_recs = await db.kids_recordings.count_documents({"child_email": email, "rec_type": "prayer"})
            task_recs = await db.kids_recordings.count_documents({"child_email": email, "rec_type": "task"})
            # Recent
            recent_recs = await db.kids_recordings.find(
                {"child_email": email}, {"_id": 0, "path": 0}
            ).sort("created_at", -1).limit(5).to_list(length=5)
            recent_pts = await db.kids_points.find(
                {"child_email": email}, {"_id": 0}
            ).sort("created_at", -1).limit(5).to_list(length=5)
            children.append({
                "email": email,
                "name": kid.get("name"),
                "pin": kid.get("pin"),
                "total_points": pts,
                "monthly_sar": round(pts * 0.1, 2),
                "by_kind": by_kind,
                "recordings_count": recs,
                "prayer_recordings": prayer_recs,
                "task_recordings": task_recs,
                "recent_recordings": recent_recs,
                "recent_points": recent_pts,
            })
            total_points += pts
            total_recs += recs
        return {
            "ok": True,
            "children": children,
            "totals": {"points": total_points, "recordings": total_recs, "kids": len(children)},
        }




    # ═══════════════════════════════════════════════════════════════════════
    # KIDS PWA — Bot sources (followed accounts) + keyword filter + scrape
    # ═══════════════════════════════════════════════════════════════════════
    @router.get("/kids/bot/config")
    async def kids_bot_get_config(user=Depends(get_current_user)):
        doc = await db.kids_bot_config.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if not doc:
            doc = {"sources": [], "keywords": [], "max_per_account": 10}
        return {"ok": True, **doc}

    @router.post("/kids/bot/config")
    async def kids_bot_set_config(
        sources: str = Form("[]"),
        keywords: str = Form("[]"),
        max_per_account: int = Form(10),
        user=Depends(get_current_user),
    ):
        try:
            srcs = json.loads(sources)
            kws = json.loads(keywords)
            if not isinstance(srcs, list) or not isinstance(kws, list):
                raise ValueError("must be lists")
        except Exception as e:
            raise HTTPException(400, f"invalid JSON: {e}")
        clean_srcs = []
        for s in srcs[:50]:
            if not isinstance(s, dict):
                continue
            platform = (s.get("platform") or "").lower().strip()
            handle = (s.get("handle") or "").strip().lstrip("@")
            if platform in ("tiktok", "youtube", "instagram") and handle:
                clean_srcs.append({"platform": platform, "handle": handle})
        clean_kws = [str(k).strip() for k in kws[:100] if str(k).strip()]
        await db.kids_bot_config.update_one(
            {"user_id": user["user_id"]},
            {"$set": {
                "user_id": user["user_id"],
                "sources": clean_srcs,
                "keywords": clean_kws,
                "max_per_account": max(1, min(50, int(max_per_account or 10))),
                "updated_at": _now(),
            }},
            upsert=True,
        )
        return {"ok": True, "sources_count": len(clean_srcs), "keywords_count": len(clean_kws)}

    @router.post("/kids/bot/scrape")
    async def kids_bot_scrape(
        background_tasks: BackgroundTasks,
        user=Depends(get_current_user),
    ):
        cfg = await db.kids_bot_config.find_one({"user_id": user["user_id"]})
        if not cfg or not cfg.get("sources"):
            raise HTTPException(400, "أضف حسابات للمتابعة أولاً")
        run_id = uuid.uuid4().hex
        await db.kids_bot_runs.insert_one({
            "id": run_id,
            "user_id": user["user_id"],
            "status": "running",
            "started_at": _now(),
            "sources_count": len(cfg.get("sources", [])),
            "downloaded": 0,
            "rejected_by_filter": 0,
            "errors": [],
        })
        background_tasks.add_task(_kids_bot_scrape_worker, user["user_id"], run_id, cfg)
        return {"ok": True, "run_id": run_id, "sources": len(cfg.get("sources", []))}

    @router.get("/kids/bot/runs")
    async def kids_bot_list_runs(user=Depends(get_current_user)):
        runs = await db.kids_bot_runs.find(
            {"user_id": user["user_id"]}, {"_id": 0}
        ).sort("started_at", -1).limit(10).to_list(length=10)
        return {"ok": True, "runs": runs}

    async def _kids_bot_scrape_worker(user_id: str, run_id: str, cfg: dict):
        sources = cfg.get("sources", [])
        keywords = [k.lower() for k in cfg.get("keywords", [])]
        max_per = int(cfg.get("max_per_account", 10))
        downloaded = 0
        rejected = 0
        errors = []
        import subprocess as _sp
        for src in sources:
            platform = src["platform"]
            handle = src["handle"]
            if platform == "tiktok":
                source_url = f"https://www.tiktok.com/@{handle}"
            elif platform == "youtube":
                source_url = f"https://www.youtube.com/@{handle}/shorts"
            elif platform == "instagram":
                source_url = f"https://www.instagram.com/{handle}/"
            else:
                continue
            cookie_path = _cookie_path_for(user_id, platform)
            cookie_args = ["--cookies", cookie_path] if os.path.exists(cookie_path) else []
            try:
                meta_proc = _sp.run(
                    ["yt-dlp", "--no-warnings", "--flat-playlist",
                     "--playlist-end", str(max_per), "--dump-json"] + cookie_args + [source_url],
                    capture_output=True, text=True, timeout=60,
                )
                if meta_proc.returncode != 0:
                    errors.append({"src": f"{platform}:{handle}", "err": (meta_proc.stderr or "")[:200]})
                    continue
                videos = []
                for ln in (meta_proc.stdout or "").splitlines():
                    if ln.strip():
                        try:
                            videos.append(json.loads(ln))
                        except Exception:
                            pass
                for v in videos:
                    title = (v.get("title") or v.get("description") or "").lower()
                    if keywords and not any(k in title for k in keywords):
                        rejected += 1
                        continue
                    vid_url = v.get("webpage_url") or v.get("url") or v.get("original_url")
                    if not vid_url:
                        continue
                    file_id = uuid.uuid4().hex[:16]
                    out_path = os.path.join(MEDIA_DIR, f"{file_id}.%(ext)s")
                    dl_proc = _sp.run(
                        ["yt-dlp", "--no-warnings", "--no-playlist",
                         "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/b/best",
                         "--merge-output-format", "mp4",
                         "-o", out_path] + cookie_args + [vid_url],
                        capture_output=True, text=True, timeout=120,
                    )
                    if dl_proc.returncode == 0:
                        actual = None
                        for ext in ("mp4", "webm", "mkv"):
                            p = os.path.join(MEDIA_DIR, f"{file_id}.{ext}")
                            if os.path.exists(p):
                                actual = p
                                break
                        if actual:
                            try:
                                size = os.path.getsize(actual)
                            except Exception:
                                size = 0
                            await db.freebuild_media_assets.insert_one({
                                "id": file_id,
                                "user_id": user_id,
                                "title": v.get("title") or "",
                                "url": f"/api/freebuild-chat/media/file/{os.path.basename(actual)}",
                                "source_url": vid_url,
                                "platform": platform,
                                "handle": handle,
                                "duration": v.get("duration") or 0,
                                "size_bytes": size,
                                "thumbnail": v.get("thumbnail") or "",
                                "approved": False,
                                "created_at": _now(),
                            })
                            downloaded += 1
                    else:
                        errors.append({"vid": vid_url, "err": (dl_proc.stderr or "")[:200]})
            except Exception as e:
                errors.append({"src": f"{platform}:{handle}", "err": str(e)[:200]})
        await db.kids_bot_runs.update_one(
            {"id": run_id},
            {"$set": {
                "status": "done",
                "ended_at": _now(),
                "downloaded": downloaded,
                "rejected_by_filter": rejected,
                "errors": errors[:30],
            }},
        )

    @router.get("/kids/bot/pending")
    async def kids_bot_list_pending(user=Depends(get_current_user)):
        items = await db.freebuild_media_assets.find(
            {"user_id": user["user_id"], "approved": False},
            {"_id": 0, "user_id": 0},
        ).sort("created_at", -1).limit(100).to_list(length=100)
        return {"ok": True, "items": items}

    @router.get("/kids/bot/approved")
    async def kids_bot_list_approved():
        items = await db.freebuild_media_assets.find(
            {"approved": True},
            {"_id": 0, "user_id": 0},
        ).sort("created_at", -1).limit(200).to_list(length=200)
        return {"ok": True, "items": items}

    @router.post("/kids/bot/approve/{vid_id}")
    async def kids_bot_approve(vid_id: str, user=Depends(get_current_user)):
        r = await db.freebuild_media_assets.update_one(
            {"id": vid_id}, {"$set": {"approved": True, "approved_at": _now()}}
        )
        return {"ok": True, "matched": r.matched_count}

    @router.delete("/kids/bot/reject/{vid_id}")
    async def kids_bot_reject(vid_id: str, user=Depends(get_current_user)):
        doc = await db.freebuild_media_assets.find_one({"id": vid_id})
        if doc:
            try:
                fname = doc.get("url", "").rsplit("/", 1)[-1]
                fpath = os.path.join(MEDIA_DIR, fname)
                if os.path.exists(fpath):
                    os.remove(fpath)
            except Exception:
                pass
        await db.freebuild_media_assets.delete_one({"id": vid_id})
        return {"ok": True}





    # ═══════════════════════════════════════════════════════════════════════
    # CREDENTIAL REQUEST FLOW — AI asks user for an API key / token
    # mid-conversation. Encrypted at rest, scoped to a project.
    # ═══════════════════════════════════════════════════════════════════════
    @router.get("/shared/{token}")
    async def download_shared_file(token: str):
        """Serve a file shared by the AI via the `share_file_with_user` tool."""
        from fastapi.responses import FileResponse
        from pathlib import Path as _Path
        import time as _time

        SHARED_DIR = _Path("/tmp/zenrex_shared")
        if not re.match(r"^[A-Za-z0-9_-]{16,32}$", token):
            raise HTTPException(400, "invalid token")
        doc = await db.freebuild_shared_files.find_one({"token": token})
        if not doc:
            raise HTTPException(404, "link not found or expired")
        if doc.get("expires_at", 0) < _time.time():
            raise HTTPException(410, "link expired")
        full = SHARED_DIR / doc["public_filename"]
        if not full.exists():
            raise HTTPException(404, "file missing on server")
        return FileResponse(
            path=str(full),
            filename=doc.get("filename", "download"),
            media_type="application/octet-stream",
        )

    @router.post("/project/{pid}/credential")
    async def save_project_credential(
        pid: str,
        service: str = Form(...),
        label: str = Form(""),
        value: str = Form(...),
        user=Depends(get_current_user),
    ):
        """Generic credential storage — used when AI asks the user for e.g.
        YouTube API key, Spotify token, custom webhook, etc."""
        service = (service or "").strip().lower()
        if not re.match(r"^[a-z][a-z0-9_-]{1,40}$", service):
            raise HTTPException(400, "اسم الخدمة غير صالح")
        if not value or len(value.strip()) < 4:
            raise HTTPException(400, "القيمة قصيرة جداً")
        await db.freebuild_credentials.update_one(
            {"project_id": pid, "user_id": user["user_id"], "service": service},
            {"$set": {
                "project_id": pid,
                "user_id": user["user_id"],
                "service": service,
                "label": label or service,
                "value_enc": _enc(value.strip()),
                "mask": _mask(value.strip()),
                "updated_at": _now(),
            }, "$setOnInsert": {"created_at": _now()}},
            upsert=True,
        )
        return {"ok": True, "service": service, "mask": _mask(value.strip())}

    @router.get("/project/{pid}/credentials")
    async def list_project_credentials(pid: str, user=Depends(get_current_user)):
        items = await db.freebuild_credentials.find(
            {"project_id": pid, "user_id": user["user_id"]},
            {"_id": 0, "service": 1, "label": 1, "mask": 1, "updated_at": 1},
        ).to_list(length=50)
        return {"credentials": items}

    # ═══════════════════════════════════════════════════════════════════════
    # MEDIA DOWNLOAD — yt-dlp wrapper for YouTube/TikTok/Instagram/X/etc.
    # AI tool 'download_media' calls this. Files are stored on disk under
    # /app/backend/uploads/freebuild_media (mounted on VPS as a volume) and
    # served via /api/freebuild-chat/media/file/{name}.
    # ═══════════════════════════════════════════════════════════════════════
    MEDIA_DIR = "/app/backend/uploads/freebuild_media"
    COOKIES_DIR = "/app/backend/uploads/freebuild_cookies"

    def _cookie_path_for(user_id: str, platform: str) -> str:
        """Return the on-disk path of the cookies.txt for (user, platform).

        platform is normalized so 'youtube.com', 'www.youtube.com', 'YouTube'
        all map to 'youtube'. The directory is private to the server (no
        public route exposes it).
        """
        p = (platform or "").strip().lower()
        for token in ("youtube", "tiktok", "instagram", "facebook", "twitter", "x"):
            if token in p:
                p = token
                break
        else:
            p = "generic"
        safe_user = re.sub(r"[^a-zA-Z0-9_-]", "_", str(user_id))[:64]
        return os.path.join(COOKIES_DIR, f"{safe_user}__{p}.txt")

    @router.post("/media/cookies/upload")
    async def upload_cookies(
        platform: str = Form(...),
        cookies_file: UploadFile = File(...),
        user=Depends(get_current_user),
    ):
        """User uploads their browser cookies.txt so the AI can bypass
        YouTube/TikTok/Instagram bot detection when downloading.

        Use Chrome extension 'Get cookies.txt LOCALLY' (or Firefox addon
        'cookies.txt') to export. We never log or expose the file contents.
        """
        os.makedirs(COOKIES_DIR, exist_ok=True)
        raw = await cookies_file.read()
        # Strict validation — Netscape cookies format header
        text = raw.decode("utf-8", errors="ignore")
        head = text.lstrip()[:200].lower()
        if "netscape" not in head and "# host" not in head and "\t" not in text[:2000]:
            raise HTTPException(
                400,
                "صيغة الكوكيز غير صحيحة. صدّرها من المتصفح بصيغة Netscape "
                "(استخدم إضافة 'Get cookies.txt LOCALLY' للكروم أو 'cookies.txt' لفايرفوكس).",
            )
        if len(raw) > 1_000_000:
            raise HTTPException(413, "ملف الكوكيز كبير جداً (الحد الأعلى 1MB)")
        dest = _cookie_path_for(user["user_id"], platform)
        with open(dest, "wb") as f:
            f.write(raw)
        # Restrict permissions
        try:
            os.chmod(dest, 0o600)
        except Exception:
            pass
        # Track in DB (no content, only metadata)
        await db.freebuild_cookies_meta.update_one(
            {"user_id": user["user_id"], "platform": _cookie_path_for(user["user_id"], platform).rsplit("__", 1)[1].split(".")[0]},
            {"$set": {"updated_at": _now(), "size_bytes": len(raw), "filename": cookies_file.filename or "cookies.txt"}},
            upsert=True,
        )
        return {
            "ok": True,
            "platform": _cookie_path_for(user["user_id"], platform).rsplit("__", 1)[1].split(".")[0],
            "size_bytes": len(raw),
        }

    @router.get("/media/cookies/list")
    async def list_cookies(user=Depends(get_current_user)):
        os.makedirs(COOKIES_DIR, exist_ok=True)
        items = await db.freebuild_cookies_meta.find(
            {"user_id": user["user_id"]},
            {"_id": 0, "platform": 1, "updated_at": 1, "size_bytes": 1, "filename": 1},
        ).to_list(length=20)
        return {"cookies": items}

    @router.delete("/media/cookies/{platform}")
    async def delete_cookies(platform: str, user=Depends(get_current_user)):
        dest = _cookie_path_for(user["user_id"], platform)
        norm_platform = dest.rsplit("__", 1)[1].split(".")[0]
        try:
            os.remove(dest)
        except FileNotFoundError:
            pass
        await db.freebuild_cookies_meta.delete_one(
            {"user_id": user["user_id"], "platform": norm_platform}
        )
        return {"ok": True, "platform": norm_platform}

    @router.post("/media/download")
    async def media_download(
        url: str = Form(...),
        format: str = Form("mp4_720p"),
        project_id: str = Form(""),
        category: str = Form(""),
        user=Depends(get_current_user),
    ):
        """Download a video/audio clip via yt-dlp and store it on the server.

        Returns a public URL the AI can embed in the user's site.
        """
        if not url.startswith(("http://", "https://")):
            raise HTTPException(400, "url must be http(s)://")

        os.makedirs(MEDIA_DIR, exist_ok=True)
        file_id = uuid.uuid4().hex[:16]

        # Resolve format → yt-dlp args
        # For direct media file URLs (ending in .mp4, .webm, etc.), skip
        # format selection — yt-dlp's "generic" extractor can't filter by
        # height when the source is already a single media stream.
        url_low_for_fmt = url.lower().split("?")[0]
        is_direct_media = url_low_for_fmt.endswith((".mp4", ".webm", ".mov", ".mkv", ".m4v", ".mp3", ".wav", ".m4a", ".ogg"))
        if format == "mp3_audio":
            if is_direct_media:
                fmt_args = ["-x", "--audio-format", "mp3"]
            else:
                fmt_args = ["-f", "bestaudio/best", "-x", "--audio-format", "mp3"]
            ext = "mp3"
        elif format == "mp4_1080p":
            if is_direct_media:
                fmt_args = []  # download as-is
            else:
                # Tries 1080p mp4 streams, then any 1080p, then any mp4, then ANY video — ensures TikTok-style single-stream works
                fmt_args = ["-f", "bv*[height<=1080][ext=mp4][vcodec*=avc1]+ba[ext=m4a]/bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/b[height<=1080]/b[ext=mp4]/best", "-S", "vcodec:h264,res:1080,acodec:m4a", "--merge-output-format", "mp4", "--recode-video", "mp4", "--postprocessor-args", "-c:v libx264 -preset fast -crf 23 -c:a aac -movflags +faststart"]
            ext = "mp4"
        else:  # default mp4_720p
            if is_direct_media:
                fmt_args = []  # download as-is
            else:
                fmt_args = ["-f", "bv*[height<=720][ext=mp4][vcodec*=avc1]+ba[ext=m4a]/bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/b[height<=720]/b[ext=mp4]/best", "-S", "vcodec:h264,res:720,acodec:m4a", "--merge-output-format", "mp4", "--recode-video", "mp4", "--postprocessor-args", "-c:v libx264 -preset fast -crf 23 -c:a aac -movflags +faststart"]
            ext = "mp4"

        out_path = os.path.join(MEDIA_DIR, f"{file_id}.%(ext)s")
        # Write JSON metadata too
        meta_path = os.path.join(MEDIA_DIR, f"{file_id}.info.json")

        import subprocess as _sp

        # ─────────────────────────────────────────────────────────────
        # Cookies support: if the user has uploaded cookies for the
        # detected platform (YouTube/TikTok/Instagram/…), pass them to
        # yt-dlp via --cookies. This bypasses bot-detection blocks that
        # otherwise return HTTP 403 on cloud server IPs.
        # ─────────────────────────────────────────────────────────────
        cookies_args: List[str] = []
        detected_platform = ""
        url_low = url.lower()
        if "youtube.com" in url_low or "youtu.be" in url_low:
            detected_platform = "youtube"
        elif "tiktok.com" in url_low:
            detected_platform = "tiktok"
        elif "instagram.com" in url_low:
            detected_platform = "instagram"
        elif "facebook.com" in url_low or "fb.watch" in url_low:
            detected_platform = "facebook"
        elif "twitter.com" in url_low or "/x.com/" in url_low or url_low.startswith("https://x.com"):
            detected_platform = "twitter"
        if detected_platform:
            cookie_path = _cookie_path_for(user["user_id"], detected_platform)
            if os.path.exists(cookie_path):
                cookies_args = ["--cookies", cookie_path]
                logger.info(f"Using cookies for {detected_platform} (user={user['user_id'][:6]}...)")

        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--no-warnings",
            "--restrict-filenames",
            "--write-info-json",
            "-o", out_path,
        ] + cookies_args + fmt_args + [url]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=_sp.PIPE,
                stderr=_sp.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=150)
            except asyncio.TimeoutError:
                proc.kill()
                raise HTTPException(504, "تنزيل الميديا تجاوز الـ150 ثانية — جرّب مقطع أقصر")
            if proc.returncode != 0:
                err_msg = (stderr.decode("utf-8", errors="ignore") or "")[-500:]
                logger.warning(f"yt-dlp failed: {err_msg}")
                # Detect well-known failure modes so the AI can communicate clearly
                low = err_msg.lower()
                if "403" in low or "ip address is blocked" in low or "forbidden" in low or "sign in to confirm" in low:
                    raise HTTPException(
                        451,
                        f"ip_blocked: {detected_platform or 'المنصة'} ترفض التحميل من سيرفرات الإنتاج. "
                        f"الحل المضمون: ارفع cookies.txt من متصفحك عبر POST /api/freebuild-chat/media/cookies/upload?platform={detected_platform or 'youtube'}. "
                        "استخدم إضافة 'Get cookies.txt LOCALLY' للكروم."
                    )
                if "video unavailable" in low or "private video" in low:
                    raise HTTPException(404, "الفيديو غير متاح أو خاص")
                if "this live event" in low or "members-only" in low:
                    raise HTTPException(403, "الفيديو يتطلب اشتراك أو بث مباشر — غير مدعوم")
                raise HTTPException(502, f"yt-dlp فشل: {err_msg}")
        except FileNotFoundError:
            raise HTTPException(500, "yt-dlp غير مثبت على السيرفر — راجع متطلبات النظام")

        # Find the produced file (yt-dlp expands %(ext)s itself)
        produced_files = [f for f in os.listdir(MEDIA_DIR) if f.startswith(file_id) and not f.endswith(".info.json")]
        if not produced_files:
            raise HTTPException(500, "yt-dlp ما أنتج ملف")
        actual_file = produced_files[0]
        actual_ext = actual_file.rsplit(".", 1)[-1]

        # Parse metadata
        title = ""
        duration = None
        thumbnail = None
        source_url = url
        try:
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                title = meta.get("title", "") or ""
                duration = meta.get("duration")
                thumbnail = meta.get("thumbnail")
                source_url = meta.get("webpage_url") or url
        except Exception:
            pass

        public_url = f"{_public_host()}/api/freebuild-chat/media/file/{file_id}.{actual_ext}"

        # Record in DB for cleanup + listing
        await db.freebuild_media_assets.insert_one({
            "id": file_id,
            "user_id": user["user_id"],
            "project_id": project_id or None,
            "filename": actual_file,
            "ext": actual_ext,
            "source_url": source_url,
            "title": title,
            "duration": duration,
            "thumbnail_url": thumbnail,
            "category": (category or "").strip() or None,
            "format": format,
            "public_url": public_url,
            "created_at": _now(),
        })

        return {
            "ok": True,
            "file_id": file_id,
            "file_url": public_url,
            "thumbnail_url": thumbnail,
            "title": title,
            "duration": duration,
            "source": source_url,
            "format": format,
            "category": (category or "").strip() or None,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # BATCH SEARCH + DOWNLOAD — for kids platforms, content aggregators, etc.
    # AI gives a search query (e.g. "latmiyat hussein for kids") + platform
    # (youtube/tiktok) + limit (max 10), we use yt-dlp's search prefix to
    # find clips and download them all in parallel.
    # ═══════════════════════════════════════════════════════════════════════
    @router.post("/media/search-and-download")
    async def media_search_and_download(
        query: str = Form(...),
        platform: str = Form("youtube"),  # youtube | tiktok | both
        limit: int = Form(5),
        category: str = Form(""),
        format: str = Form("mp4_720p"),
        project_id: str = Form(""),
        user=Depends(get_current_user),
    ):
        """Search a platform for videos matching `query`, download top `limit` clips.

        Returns a list of downloaded clips with public URLs the AI can embed.
        """
        q = (query or "").strip()
        if not q or len(q) < 2:
            raise HTTPException(400, "query too short")
        limit = max(1, min(int(limit or 5), 10))
        plat = (platform or "youtube").strip().lower()
        if plat not in {"youtube", "tiktok", "both"}:
            plat = "youtube"

        os.makedirs(MEDIA_DIR, exist_ok=True)

        async def _search_urls(prefix: str, count: int) -> List[str]:
            """Use yt-dlp's search to get top URLs without downloading."""
            import subprocess as _sp
            # Use YouTube cookies for search too (helps with age-gated content)
            ck = _cookie_path_for(user["user_id"], "youtube")
            ck_args = ["--cookies", ck] if os.path.exists(ck) else []
            cmd = [
                "yt-dlp",
                f"{prefix}{count}:{q}",
                "--flat-playlist",
                "--print", "%(webpage_url)s",
                "--no-warnings",
                "--quiet",
            ] + ck_args
            try:
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=_sp.PIPE, stderr=_sp.PIPE)
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
                lines = [ln.strip() for ln in stdout.decode("utf-8", errors="ignore").splitlines() if ln.strip().startswith("http")]
                return lines[:count]
            except (asyncio.TimeoutError, Exception):
                return []

        urls: List[str] = []
        if plat in ("youtube", "both"):
            urls += await _search_urls("ytsearch", limit)
        if plat in ("tiktok", "both"):
            # yt-dlp doesn't have a native tiktok search prefix; we use the
            # `tiktok:user` extractor only when the query starts with @, otherwise
            # we fall back to YouTube. Honest about this limitation:
            if q.startswith("@"):
                urls += await _search_urls("tt", limit)
            # else: we don't blow up — the agent should know tiktok search
            # by keyword isn't supported. Caller can pass direct TikTok URLs
            # via the regular /media/download endpoint.
        # Dedupe while preserving order
        seen, ordered = set(), []
        for u in urls:
            if u not in seen:
                seen.add(u)
                ordered.append(u)
        urls = ordered[:limit]
        if not urls:
            return {"ok": False, "error": "no_results", "query": q, "platform": plat, "clips": []}

        # Now download each one (sequential to respect rate limits and disk)
        clips: List[Dict[str, Any]] = []
        for u in urls:
            try:
                # Re-use the single-download logic via internal call
                file_id = uuid.uuid4().hex[:16]
                if format == "mp3_audio":
                    fmt_args = ["-f", "bestaudio/best", "-x", "--audio-format", "mp3"]
                elif format == "mp4_1080p":
                    fmt_args = ["-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/b[height<=1080]", "--merge-output-format", "mp4"]
                else:
                    fmt_args = ["-f", "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/b[height<=720]", "--merge-output-format", "mp4"]
                out_path = os.path.join(MEDIA_DIR, f"{file_id}.%(ext)s")
                meta_path = os.path.join(MEDIA_DIR, f"{file_id}.info.json")
                # Detect platform of this URL and load cookies if available
                _u_low = u.lower()
                _det = ""
                if "youtube.com" in _u_low or "youtu.be" in _u_low:
                    _det = "youtube"
                elif "tiktok.com" in _u_low:
                    _det = "tiktok"
                elif "instagram.com" in _u_low:
                    _det = "instagram"
                _ck_args: List[str] = []
                if _det:
                    _ck = _cookie_path_for(user["user_id"], _det)
                    if os.path.exists(_ck):
                        _ck_args = ["--cookies", _ck]
                import subprocess as _sp
                cmd = [
                    "yt-dlp", "--no-playlist", "--no-warnings",
                    "--restrict-filenames", "--write-info-json",
                    "-o", out_path,
                ] + _ck_args + fmt_args + [u]
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=_sp.PIPE, stderr=_sp.PIPE)
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
                if proc.returncode != 0:
                    clips.append({"ok": False, "url": u, "error": (stderr.decode("utf-8", errors="ignore") or "")[-200:]})
                    continue
                produced = [f for f in os.listdir(MEDIA_DIR) if f.startswith(file_id) and not f.endswith(".info.json")]
                if not produced:
                    clips.append({"ok": False, "url": u, "error": "no file produced"})
                    continue
                actual_file = produced[0]
                actual_ext = actual_file.rsplit(".", 1)[-1]
                title, duration, thumbnail = "", None, None
                source_url = u
                try:
                    if os.path.exists(meta_path):
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                        title = meta.get("title", "") or ""
                        duration = meta.get("duration")
                        thumbnail = meta.get("thumbnail")
                        source_url = meta.get("webpage_url") or u
                except Exception:
                    pass
                public_url = f"{_public_host()}/api/freebuild-chat/media/file/{file_id}.{actual_ext}"
                await db.freebuild_media_assets.insert_one({
                    "id": file_id,
                    "user_id": user["user_id"],
                    "project_id": project_id or None,
                    "filename": actual_file,
                    "ext": actual_ext,
                    "source_url": source_url,
                    "title": title,
                    "duration": duration,
                    "thumbnail_url": thumbnail,
                    "category": (category or "").strip() or None,
                    "search_query": q,
                    "platform": plat,
                    "created_at": _now(),
                })
                clips.append({
                    "ok": True,
                    "file_id": file_id,
                    "file_url": public_url,
                    "thumbnail_url": thumbnail,
                    "title": title,
                    "duration": duration,
                    "source": source_url,
                })
            except asyncio.TimeoutError:
                clips.append({"ok": False, "url": u, "error": "timeout"})
            except Exception as e:
                clips.append({"ok": False, "url": u, "error": f"{type(e).__name__}: {str(e)[:120]}"})

        ok_count = sum(1 for c in clips if c.get("ok"))
        return {
            "ok": ok_count > 0,
            "query": q,
            "platform": plat,
            "category": (category or "").strip() or None,
            "total_requested": limit,
            "downloaded": ok_count,
            "failed": len(clips) - ok_count,
            "clips": clips,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # LIST MEDIA ASSETS (filtered by project + category) — kids platform UI
    # uses this to render categorized video grid.
    # ═══════════════════════════════════════════════════════════════════════
    @router.get("/media/list")
    async def list_media_assets(
        project_id: str = "",
        category: str = "",
        limit: int = 100,
        user=Depends(get_current_user),
    ):
        q: Dict[str, Any] = {"user_id": user["user_id"]}
        if project_id:
            q["project_id"] = project_id
        if category:
            q["category"] = category
        cursor = db.freebuild_media_assets.find(
            q,
            {"_id": 0, "id": 1, "title": 1, "duration": 1, "thumbnail_url": 1,
             "category": 1, "source_url": 1, "filename": 1, "ext": 1,
             "platform": 1, "created_at": 1},
        ).sort("created_at", -1).limit(max(1, min(int(limit), 500)))
        items = await cursor.to_list(length=500)
        host = _public_host()
        for it in items:
            it["file_url"] = f"{host}/api/freebuild-chat/media/file/{it['id']}.{it.get('ext', 'mp4')}"
        # Aggregate categories
        cats = await db.freebuild_media_assets.aggregate([
            {"$match": {"user_id": user["user_id"], **({"project_id": project_id} if project_id else {})}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]).to_list(length=50)
        return {
            "ok": True,
            "items": items,
            "categories": [{"name": c["_id"], "count": c["count"]} for c in cats if c["_id"]],
        }

    @router.head("/media/file/{filename}", include_in_schema=False)
    @router.get("/media/file/{filename}", include_in_schema=False)
    async def serve_media(filename: str, request: Request):
        """Range-aware media file server.

        HTML5 <video> requires HTTP Range requests for seeking + streaming.
        FastAPI's FileResponse does NOT handle Range — it sends the whole
        file as 200 OK, which makes browsers reject the video (error code 4).
        This implementation:
          • Handles HEAD requests cleanly.
          • Honors Range headers → returns 206 Partial Content.
          • Falls back to full-file send when no Range header is present.
        """
        from fastapi.responses import Response, StreamingResponse
        # Prevent path traversal
        safe_name = os.path.basename(filename)
        path = os.path.join(MEDIA_DIR, safe_name)
        if not os.path.isfile(path):
            raise HTTPException(404)
        # Infer content-type from extension
        ext = safe_name.rsplit(".", 1)[-1].lower()
        ct = {
            "mp4": "video/mp4", "mp3": "audio/mpeg", "webm": "video/webm",
            "m4a": "audio/mp4", "mov": "video/quicktime", "wav": "audio/wav",
            "ogg": "audio/ogg", "mkv": "video/x-matroska",
        }.get(ext, "application/octet-stream")
        file_size = os.path.getsize(path)

        # HEAD → return metadata only
        if request.method == "HEAD":
            return Response(
                status_code=200,
                headers={
                    "Content-Length": str(file_size),
                    "Content-Type": ct,
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "public, max-age=31536000, immutable",
                },
            )

        # Parse Range header (e.g. "bytes=0-1023" or "bytes=500-")
        range_header = request.headers.get("range") or request.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            try:
                spec = range_header.split("=", 1)[1]
                start_s, end_s = (spec.split("-", 1) + [""])[:2]
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else file_size - 1
                end = min(end, file_size - 1)
                if start < 0 or start > end:
                    raise ValueError
            except (ValueError, IndexError):
                return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

            length = end - start + 1

            def _iter_chunk():
                with open(path, "rb") as f:
                    f.seek(start)
                    remaining = length
                    chunk_size = 1024 * 1024  # 1MB
                    while remaining > 0:
                        chunk = f.read(min(chunk_size, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk

            return StreamingResponse(
                _iter_chunk(),
                status_code=206,
                media_type=ct,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(length),
                    "Cache-Control": "public, max-age=31536000, immutable",
                },
            )

        # No Range → send whole file
        def _iter_full():
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(1024 * 1024)
                    if not chunk:
                        break
                    yield chunk

        return StreamingResponse(
            _iter_full(),
            status_code=200,
            media_type=ct,
            headers={
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=31536000, immutable",
            },
        )

    # Save a deployment provider token (encrypted at rest)
    @router.post("/project/{pid}/connections/{provider}")
    async def save_connection(
        pid: str,
        provider: str,
        token: str = Form(...),
        extra: str = Form(default=""),
        user=Depends(get_current_user),
    ):
        if provider not in ("github", "vercel", "cloudflare", "domain", "hetzner"):
            raise HTTPException(400, "provider غير مدعوم")
        proj = await db.freebuild_projects.find_one({"id": pid, "user_id": user["user_id"]}, {"_id": 0, "id": 1})
        if not proj:
            raise HTTPException(404)
        await db.freebuild_connections.update_one(
            {"project_id": pid, "user_id": user["user_id"], "provider": provider},
            {"$set": {
                "project_id": pid,
                "user_id": user["user_id"],
                "provider": provider,
                "token_enc": _enc(token.strip()),
                "extra": extra,
                "mask": _mask(token.strip()),
                "updated_at": _now(),
            }, "$setOnInsert": {"created_at": _now()}},
            upsert=True,
        )
        return {"ok": True, "mask": _mask(token.strip())}

    @router.get("/project/{pid}/connections")
    async def list_connections(pid: str, user=Depends(get_current_user)):
        cursor = db.freebuild_connections.find(
            {"project_id": pid, "user_id": user["user_id"]},
            {"_id": 0, "provider": 1, "mask": 1, "extra": 1, "created_at": 1, "updated_at": 1},
        )
        items = await cursor.to_list(length=20)
        return {"connections": items}

    @router.delete("/project/{pid}/connections/{provider}")
    async def delete_connection(pid: str, provider: str, user=Depends(get_current_user)):
        await db.freebuild_connections.delete_one(
            {"project_id": pid, "user_id": user["user_id"], "provider": provider},
        )
        return {"ok": True}

    # Push current HTML to a GitHub repo (creates if not exists, pushes index.html)
    @router.post("/project/{pid}/push-to-github")
    async def push_to_github(
        pid: str,
        repo_name: str = Form(...),
        private: bool = Form(default=False),
        user=Depends(get_current_user),
    ):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404)
        # 💳 PAYWALL: GitHub push is a premium feature — user must unlock
        # via the Finalize/Independence purchase first.
        if not proj.get("code_unlocked"):
            raise HTTPException(
                402,  # Payment Required
                "PAYWALL: حزمة الاستقلالية مطلوبة للنشر على GitHub. افتح زر "
                "'تفعيل الاستقلالية' وادفع الحزمة الواحدة ($49) لفتح الميزة."
            )
        if not proj.get("current_html"):
            raise HTTPException(400, "لا يوجد HTML للنشر")
        conn = await db.freebuild_connections.find_one(
            {"project_id": pid, "user_id": user["user_id"], "provider": "github"},
            {"_id": 0, "token_enc": 1},
        )
        if not conn:
            raise HTTPException(400, "ربط GitHub أولاً من إعدادات الاتصالات")
        token = _dec(conn["token_enc"]) if conn.get("token_enc") else None
        if not token:
            raise HTTPException(400, "GitHub token غير صالح — أعد ربطه")

        import httpx
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=30) as cli:
            # 1) Get authenticated user
            u_r = await cli.get("https://api.github.com/user", headers=headers)
            if u_r.status_code != 200:
                raise HTTPException(400, f"فشل التحقق من GitHub: {u_r.status_code}")
            owner = u_r.json().get("login")
            # 2) Create repo (or ignore if exists)
            cr_r = await cli.post(
                "https://api.github.com/user/repos",
                headers=headers,
                json={"name": repo_name, "private": private, "auto_init": True, "description": f"Built with Zenrex — {proj.get('name','')}"},
            )
            if cr_r.status_code not in (201, 422):  # 422 = already exists
                raise HTTPException(400, f"فشل إنشاء المستودع: {cr_r.status_code} — {cr_r.text[:120]}")
            # 3) Get current SHA of index.html (if exists)
            sha = None
            get_f = await cli.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/contents/index.html",
                headers=headers,
            )
            if get_f.status_code == 200:
                sha = get_f.json().get("sha")
            # 4) PUT index.html
            content_b64 = base64.b64encode(proj["current_html"].encode()).decode()
            payload = {
                "message": f"Update from Zenrex — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                "content": content_b64,
            }
            if sha:
                payload["sha"] = sha
            put_r = await cli.put(
                f"https://api.github.com/repos/{owner}/{repo_name}/contents/index.html",
                headers=headers,
                json=payload,
            )
            if put_r.status_code not in (200, 201):
                raise HTTPException(400, f"فشل رفع الملف: {put_r.status_code} — {put_r.text[:120]}")

        repo_url = f"https://github.com/{owner}/{repo_name}"
        pages_url = f"https://{owner}.github.io/{repo_name}/"
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$set": {"github_repo_url": repo_url, "updated_at": _now()}},
        )
        return {"ok": True, "repo_url": repo_url, "pages_url_hint": pages_url}

    # ═══════════════════════════════════════════════════════════════
    # 💎 INDEPENDENCE PHASE-2 — Push the FULL Independence Kit (10 files)
    # to the customer's GitHub repo and (optionally) transfer ownership.
    # ═══════════════════════════════════════════════════════════════
    @router.post("/project/{pid}/push-independence-to-github")
    async def push_independence_to_github(
        pid: str,
        repo_name: str = Form(...),
        private: bool = Form(default=False),
        user=Depends(get_current_user),
    ):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404)
        if proj.get("tier") != "full_independence":
            raise HTTPException(402, "هذه الميزة لباقة الاستقلال الكامل فقط ($799).")
        if not proj.get("current_html"):
            raise HTTPException(400, "أكمل الموقع قبل النشر على GitHub.")
        conn = await db.freebuild_connections.find_one(
            {"project_id": pid, "user_id": user["user_id"], "provider": "github"},
            {"_id": 0, "token_enc": 1},
        )
        if not conn:
            raise HTTPException(400, "اربط GitHub أولاً من زر 'الاتصالات' — يحتاج Personal Access Token بصلاحية repo.")
        token = _dec(conn["token_enc"])
        if not token:
            raise HTTPException(400, "GitHub token تالف. أعد ربطه.")

        # Build the kit (10 files + index.html)
        from modules.freebuild.independence_kit import build_independence_kit
        kit = await build_independence_kit(
            proj, owner_email=user.get("email") or user.get("user_id") or "—"
        )
        # Strip Zenrex footer
        html = proj.get("current_html") or ""
        if ZENREX_FOOTER_MARK in html:
            fs = html.find(ZENREX_FOOTER_MARK)
            fe = html.find("</a>", fs)
            if fe != -1:
                html = html[:fs] + html[fe + 4:]

        files_to_push: Dict[str, str] = {"index.html": html, **kit}

        import httpx
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=60) as cli:
            u_r = await cli.get("https://api.github.com/user", headers=headers)
            if u_r.status_code != 200:
                raise HTTPException(400, f"فشل التحقق من GitHub: {u_r.status_code}")
            owner = u_r.json().get("login")

            # Create repo (idempotent)
            cr_r = await cli.post(
                "https://api.github.com/user/repos",
                headers=headers,
                json={
                    "name": repo_name,
                    "private": private,
                    "auto_init": True,
                    "description": f"Independence delivery — {proj.get('name', '')}",
                },
            )
            if cr_r.status_code not in (201, 422):
                raise HTTPException(400, f"فشل إنشاء المستودع: {cr_r.status_code} — {cr_r.text[:160]}")

            # Push every kit file
            pushed: List[str] = []
            failed: List[Dict[str, Any]] = []
            for fname, fcontent in files_to_push.items():
                try:
                    get_f = await cli.get(
                        f"https://api.github.com/repos/{owner}/{repo_name}/contents/{fname}",
                        headers=headers,
                    )
                    sha = get_f.json().get("sha") if get_f.status_code == 200 else None
                    content_b64 = base64.b64encode(fcontent.encode()).decode()
                    payload = {
                        "message": f"chore: Independence kit — {fname}",
                        "content": content_b64,
                    }
                    if sha:
                        payload["sha"] = sha
                    put_r = await cli.put(
                        f"https://api.github.com/repos/{owner}/{repo_name}/contents/{fname}",
                        headers=headers,
                        json=payload,
                    )
                    if put_r.status_code in (200, 201):
                        pushed.append(fname)
                    else:
                        failed.append({"file": fname, "status": put_r.status_code, "msg": put_r.text[:120]})
                except Exception as e:  # noqa: BLE001
                    failed.append({"file": fname, "error": str(e)[:120]})

        repo_url = f"https://github.com/{owner}/{repo_name}"
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$set": {
                "github_repo_url": repo_url,
                "github_independence_pushed": True,
                "github_independence_files": pushed,
                "updated_at": _now(),
            }},
        )
        return {
            "ok": True,
            "repo_url": repo_url,
            "owner": owner,
            "pushed_count": len(pushed),
            "pushed_files": pushed,
            "failed": failed,
            "next_step": (
                f"تمام! المستودع جاهز على {repo_url}\n"
                f"الخطوة الأخيرة (اختيارية): لو تبي تحوّل ملكية المستودع لحسابك الشخصي/منظمتك، "
                f"ادخل {repo_url}/settings → Transfer ownership → اكتب اسم الحساب الجديد."
            ),
        }

    # ═══════════════════════════════════════════════════════════════
    # APP CONVERSION ENDPOINTS — convert a finished FreeBuild website
    # into a downloadable PWA / Capacitor (Android+iOS) / Expo bundle.
    # ═══════════════════════════════════════════════════════════════
    @router.get("/app-conversion/{aid}")
    async def get_app_conversion(aid: str, user=Depends(get_current_user)):
        doc = await db.app_conversion_projects.find_one(
            {"id": aid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not doc:
            raise HTTPException(404, "تحويل غير موجود")
        return doc

    @router.patch("/app-conversion/{aid}")
    async def update_app_conversion(
        aid: str,
        name: Optional[str] = Form(None),
        package_id: Optional[str] = Form(None),
        primary_color: Optional[str] = Form(None),
        app_type: Optional[str] = Form(None),  # pwa | hybrid
        user=Depends(get_current_user),
    ):
        update: Dict[str, Any] = {"updated_at": _now()}
        if name is not None:
            update["name"] = name.strip()[:80]
        if package_id is not None:
            # normalize: only lowercase + dots + dashes
            pkg = re.sub(r"[^a-z0-9.\-]", "", package_id.lower()) or "com.zenrex.ai"
            update["package_id"] = pkg[:80]
        if primary_color is not None and primary_color.startswith("#"):
            update["primary_color"] = primary_color[:7]
        if app_type in ("pwa", "hybrid"):
            update["app_type"] = app_type
        r = await db.app_conversion_projects.update_one(
            {"id": aid, "user_id": user["user_id"]},
            {"$set": update},
        )
        if r.matched_count == 0:
            raise HTTPException(404)
        return {"ok": True, **{k: v for k, v in update.items() if k != "updated_at"}}

    @router.post("/app-conversion/{aid}/build")
    async def build_app_conversion(aid: str, user=Depends(get_current_user)):
        doc = await db.app_conversion_projects.find_one(
            {"id": aid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not doc:
            raise HTTPException(404)
        if not doc.get("current_html"):
            raise HTTPException(400, "لا يوجد HTML للتحويل — أكمل الموقع أولاً")

        # adapt to the app_studio.builder.build_project signature
        try:
            from modules.app_studio.builder import build_project
        except Exception:
            logger.exception("app_studio.builder import failed")
            raise HTTPException(500, "محرّك البناء غير متاح")

        app_type = doc.get("app_type") or "pwa"
        if app_type not in ("pwa", "hybrid"):
            app_type = "pwa"

        pseudo_project = {
            "id": aid,
            "type": app_type,
            "title": doc.get("name", "تطبيق Zenrex"),
            "description": doc.get("description", ""),
            "primary_color": doc.get("primary_color", "#10b981"),
            "package_id": doc.get("package_id", "com.zenrex.ai"),
            "imports": [{"kind": "freebuild_site", "html_snapshot": doc["current_html"]}],
        }
        try:
            result = build_project(pseudo_project, features=[])
        except Exception as e:
            logger.exception("build_project failed")
            raise HTTPException(500, f"فشل البناء: {str(e)[:120]}")

        await db.app_conversion_projects.update_one(
            {"id": aid},
            {"$set": {
                "status": "built",
                "last_build": result,
                "updated_at": _now(),
            }},
        )
        return result

    # ═══════════════════════════════════════════════════════════════
    # HTML SNAPSHOTS — every overwrite of current_html auto-archives the
    # previous version. User can list, preview, and restore.
    # ═══════════════════════════════════════════════════════════════
    @router.get("/project/{pid}/snapshots")
    async def list_snapshots(pid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]},
            {"_id": 0, "html_snapshots": 1, "current_html": 1, "published_slug": 1, "published_version": 1},
        )
        if not proj:
            raise HTTPException(404)
        snaps = proj.get("html_snapshots") or []
        # newest first, strip the full html from listing (only summaries).
        # Each item carries `label` + `kind` so the UI can show distinct
        # treatments (e.g. baseline pinned at top, publish chips green, etc.).
        items = []
        for s in reversed(snaps):
            items.append({
                "id": s.get("id"),
                "created_at": s.get("created_at"),
                "user_msg": (s.get("user_msg") or "")[:200],
                "summary": s.get("summary") or _summarize_html(s.get("html", "")),
                "size": len(s.get("html") or ""),
                "kind": s.get("kind") or "auto",
                "label": s.get("label") or "",
                "is_baseline": (s.get("kind") == "baseline"),
            })
        current_summary = _summarize_html(proj.get("current_html") or "")
        return {
            "ok": True,
            "snapshots": items,
            "current_summary": current_summary,
            "count": len(items),
            "published_slug": proj.get("published_slug"),
            "published_version": proj.get("published_version"),
        }

    @router.post("/project/{pid}/snapshots/manual")
    async def create_manual_snapshot(
        pid: str,
        label: str = Form(""),
        user=Depends(get_current_user),
    ):
        """Manual save — user clicks 'احفظ هذي النسخة' in the Archive tab.

        Stores the current_html as a snapshot with kind=manual. Unlimited.
        """
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]},
            {"_id": 0, "current_html": 1},
        )
        if not proj:
            raise HTTPException(404)
        html = proj.get("current_html") or ""
        if not html:
            raise HTTPException(400, "ما فيه تصميم محفوظ بعد")
        snap = _make_snapshot_doc(
            html,
            user_msg="[حفظ يدوي من المستخدم]",
            kind="manual",
            label=(label or "حفظ يدوي").strip()[:80],
        )
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$push": {"html_snapshots": {"$each": [snap]}}},
        )
        return {
            "ok": True,
            "snapshot": {
                "id": snap["id"],
                "created_at": snap["created_at"],
                "summary": snap["summary"],
                "label": snap["label"],
                "kind": snap["kind"],
                "size": len(html),
            },
        }

    @router.get("/project/{pid}/snapshots/{sid}/preview")
    async def preview_snapshot(pid: str, sid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]},
            {"_id": 0, "html_snapshots": 1},
        )
        if not proj:
            raise HTTPException(404)
        for s in (proj.get("html_snapshots") or []):
            if s.get("id") == sid:
                return {"ok": True, "html": s.get("html", ""), "created_at": s.get("created_at")}
        raise HTTPException(404, "نسخة غير موجودة")

    # ═══════════════════════════════════════════════════════════════
    # 🖼️ Real Screenshot endpoint — renders the snapshot HTML via
    # headless Chromium so the Design Archive shows TRUE visuals
    # (full CSS, fonts, images) instead of broken iframe srcdoc previews.
    # Caches the rendered PNG inside the snapshot doc on first render.
    # ═══════════════════════════════════════════════════════════════
    @router.get("/project/{pid}/snapshots/{sid}/screenshot")
    async def snapshot_screenshot(
        pid: str, sid: str, thumb: int = 0, user=Depends(get_current_user),
    ):
        """Return a real PNG of the snapshot. `?thumb=1` returns a 480px-wide
        downscaled thumbnail (fast). Default returns a full-page 1280px render."""
        from fastapi.responses import Response
        from modules.freebuild.snapshot_renderer import render_png

        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]},
            {"_id": 0, "html_snapshots": 1},
        )
        if not proj:
            raise HTTPException(404)

        target = None
        for s in (proj.get("html_snapshots") or []):
            if s.get("id") == sid:
                target = s
                break
        if not target:
            raise HTTPException(404, "نسخة غير موجودة")

        cache_key = "thumb_png_b64" if thumb else "full_png_b64"
        cached = target.get(cache_key)
        if cached:
            import base64 as _b64
            try:
                png = _b64.b64decode(cached)
                return Response(content=png, media_type="image/png")
            except Exception:
                pass  # Fall-through to re-render.

        html = target.get("html") or ""
        width = 1280
        png = await render_png(
            html, width=width, full_page=True,
            thumbnail_max_width=(480 if thumb else None),
            timeout_ms=20000,
        )
        if not png:
            raise HTTPException(500, "تعذّر توليد المعاينة")

        # Cache for next time (avoid re-rendering 300 snapshots each scroll).
        import base64 as _b64
        try:
            await db.freebuild_projects.update_one(
                {"id": pid, "html_snapshots.id": sid},
                {"$set": {f"html_snapshots.$.{cache_key}": _b64.b64encode(png).decode()}},
            )
        except Exception:
            pass  # Cache miss is fine; we still return the PNG below.
        return Response(content=png, media_type="image/png")

    # ═══════════════════════════════════════════════════════════════
    # ✂️ Surgical Edit — owner/customer annotates a snapshot screenshot
    # (draws colored rectangles to point at sections) then asks the AI
    # to modify ONLY those areas in the current design. The annotated
    # image is sent to Claude as an image input; selectors describe
    # the bounding boxes in image-space so the AI knows exact location.
    # ═══════════════════════════════════════════════════════════════
    @router.post("/project/{pid}/snapshots/{sid}/surgical-edit")
    async def snapshot_surgical_edit(
        pid: str, sid: str,
        instruction: str = Form(...),
        annotated_image_b64: str = Form(""),
        selectors_json: str = Form("[]"),
        user=Depends(get_current_user),
    ):
        """Accept (image with rectangles drawn) + (instruction in Arabic) and
        queue an edit request. The AI sees the image + the user's words +
        the list of bounding boxes the user drew. Returns the new snapshot id
        that gets created from the AI's response (so the archive grows)."""
        import json as _json
        import base64 as _b64

        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]},
            {"_id": 0, "id": 1, "current_html": 1, "html_snapshots": 1},
        )
        if not proj:
            raise HTTPException(404)
        if not (instruction or "").strip():
            raise HTTPException(400, "instruction مطلوب")

        try:
            selectors = _json.loads(selectors_json) if selectors_json else []
        except Exception:
            selectors = []

        # Persist the request in a dedicated collection so the owner-engineer
        # has a paper trail and can debug what was asked.
        from datetime import datetime, timezone as _tz
        req_doc = {
            "id": str(uuid.uuid4()),
            "project_id": pid,
            "snapshot_id": sid,
            "user_id": user["user_id"],
            "instruction": instruction[:3000],
            "selectors": selectors[:20],
            "has_image": bool(annotated_image_b64),
            "status": "queued",
            "created_at": datetime.now(_tz.utc).isoformat(),
        }
        try:
            await db.freebuild_surgical_requests.insert_one(req_doc)
        except Exception:
            pass

        # For the MVP we route the surgical edit back through the normal chat
        # pipeline by injecting a richly-formatted user message into the
        # project's chat session. The next time the user opens the project
        # (or the live AI is running), it sees the request + image and acts.
        marker_parts = [f"🎯 [طلب جراحي من المحفوظات — نسخة {sid[:8]}]"]
        marker_parts.append(f"📝 الطلب: {instruction.strip()}")
        if selectors:
            bbox_lines = []
            for idx, sel in enumerate(selectors, start=1):
                color = sel.get("color", "?")
                x = sel.get("x", 0); y = sel.get("y", 0)
                w = sel.get("w", 0); h = sel.get("h", 0)
                label = sel.get("label", "")
                bbox_lines.append(
                    f"  {idx}. لون {color}، الموقع (x={x}, y={y}, w={w}, h={h})"
                    + (f" — {label}" if label else "")
                )
            marker_parts.append("📐 المناطق المحددة (إحداثيات الصورة المرفقة):")
            marker_parts.extend(bbox_lines)
        marker_parts.append(
            "⚠️ المطلوب: عدّل فقط على المناطق المحددة في الـ HTML الحالي. "
            "لا تكسر أي قسم آخر. لا تعيد بناء الصفحة كاملة. "
            "بعد ما تنتهي، اعمل snapshot جديد للمحفوظات تلقائياً."
        )
        marker = "\n".join(marker_parts)

        try:
            await db.freebuild_chat_sessions.update_one(
                {"project_id": pid},
                {
                    "$push": {
                        "messages": {
                            "role": "user",
                            "content": marker,
                            "ts": datetime.now(_tz.utc).isoformat(),
                            "source": "surgical_archive",
                            "snapshot_id": sid,
                            "selectors": selectors,
                            # The image itself can be huge — we DON'T persist
                            # the full base64 in the messages array. The
                            # surgical_requests collection holds the link.
                            "annotated_image_request_id": req_doc["id"],
                        },
                    },
                    "$set": {"updated_at": datetime.now(_tz.utc).isoformat()},
                    "$setOnInsert": {
                        "project_id": pid,
                        "user_id": user["user_id"],
                        "created_at": datetime.now(_tz.utc).isoformat(),
                    },
                },
                upsert=True,
            )
        except Exception as e:
            raise HTTPException(500, f"فشل حقن الطلب في الشات: {e}")

        # Stash a compact data: URL for the annotated image (capped at 300KB
        # base64 → ~225KB image) on the surgical request doc so the frontend
        # can display it back to the AI on next chat-turn request building.
        if annotated_image_b64 and len(annotated_image_b64) < 320_000:
            try:
                await db.freebuild_surgical_requests.update_one(
                    {"id": req_doc["id"]},
                    {"$set": {"annotated_image_b64": annotated_image_b64}},
                )
            except Exception:
                pass

        return {
            "ok": True,
            "request_id": req_doc["id"],
            "snapshot_id": sid,
            "message_preview": marker[:500],
            "note": "تم إضافة طلب التعديل الجراحي في شات المشروع. افتح المشروع لمتابعة التنفيذ.",
        }

    @router.get("/project/{pid}/surgical-requests")
    async def list_surgical_requests(pid: str, limit: int = 30, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0, "id": 1},
        )
        if not proj:
            raise HTTPException(404)
        items = []
        try:
            cursor = db.freebuild_surgical_requests.find(
                {"project_id": pid},
                {"_id": 0, "annotated_image_b64": 0},  # Skip the heavy field.
            ).sort("created_at", -1).limit(int(limit or 30))
            async for r in cursor:
                items.append(r)
        except Exception:
            pass
        return {"ok": True, "requests": items, "count": len(items)}

    # ═══════════════════════════════════════════════════════════════
    # 🧠 Discovery Brain — turns a vague idea into a phased Roadmap +
    # 15-25 progressive questions. AI #1.5 between Receptionist and
    # Builder. Stops the Builder from "guessing" the scope.
    # ═══════════════════════════════════════════════════════════════
    # ═══════════════════════════════════════════════════════════════
    # 🧠 Discovery Brain — AI #1.5 (consultant before builder).
    # Routes:
    #   POST /project/{pid}/discovery/init        — analyze idea + roadmap
    #   POST /project/{pid}/discovery/answer      — submit batch answers
    #   GET  /project/{pid}/discovery/status      — fetch blueprint
    #   POST /project/{pid}/discovery/start-build — kick off the Builder.
    #
    # Pricing (negative-balance allowed — paid back on next top-up):
    #   • init   — 100 credits  (covers Tavily research + first batch)
    #   • answer — 75 credits   (per batch of up to 5 questions)
    # The customer can SKIP Discovery entirely (it's optional); charges
    # only apply when they actively engage with the panel.
    # ═══════════════════════════════════════════════════════════════
    DISCOVERY_INIT_COST = 100
    DISCOVERY_BATCH_COST = 75

    @router.post("/project/{pid}/discovery/init")
    async def discovery_init(
        pid: str,
        idea: str = Form(...),
        user=Depends(get_current_user),
    ):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0, "id": 1, "discovery": 1},
        )
        if not proj:
            raise HTTPException(404)
        # Refuse to overwrite an existing in-progress discovery unless explicitly reset.
        if proj.get("discovery") and proj["discovery"].get("status") != "done":
            return {"ok": True, "blueprint": proj["discovery"], "reused": True}
        # Charge BEFORE running the LLM (allow negative balance — paid back later).
        try:
            from modules.pricing.credits import deduct_credits_allow_negative
            new_balance = await deduct_credits_allow_negative(
                db, user["user_id"], DISCOVERY_INIT_COST,
                reason="discovery:init",
                meta={"project_id": pid, "idea_preview": (idea or "")[:120]},
            )
        except Exception as e:
            log.warning(f"[discovery/init] credit deduction failed: {e}")
            new_balance = None
        from modules.freebuild.discovery_brain import classify_and_plan
        result = await classify_and_plan(idea)
        if not result.get("ok"):
            raise HTTPException(500, result.get("error") or "discovery_failed")
        bp = result["blueprint"]
        await db.freebuild_projects.update_one(
            {"id": pid}, {"$set": {"discovery": bp, "discovery_idea_seed": (idea or "")[:500]}},
        )
        return {
            "ok": True,
            "blueprint": bp,
            "reused": False,
            "credit_charged": DISCOVERY_INIT_COST,
            "credit_balance": new_balance,
        }

    @router.post("/project/{pid}/discovery/answer")
    async def discovery_answer(
        pid: str,
        answers_json: str = Form(...),
        user=Depends(get_current_user),
    ):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0, "id": 1, "discovery": 1},
        )
        if not proj or not proj.get("discovery"):
            raise HTTPException(404, "Discovery لم يبدأ لهذا المشروع")
        import json as _json
        try:
            answers = _json.loads(answers_json) if answers_json else {}
        except Exception:
            raise HTTPException(400, "answers_json invalid")
        if not isinstance(answers, dict):
            raise HTTPException(400, "answers_json must be an object {qid: answer}")
        # Charge per batch (allow negative balance — settled on next top-up).
        new_balance = None
        try:
            from modules.pricing.credits import deduct_credits_allow_negative
            new_balance = await deduct_credits_allow_negative(
                db, user["user_id"], DISCOVERY_BATCH_COST,
                reason="discovery:batch",
                meta={"project_id": pid, "answers_count": len(answers)},
            )
        except Exception as e:
            log.warning(f"[discovery/answer] credit deduction failed: {e}")
        from modules.freebuild.discovery_brain import advance_discovery
        result = await advance_discovery(proj["discovery"], answers)
        if not result.get("ok"):
            raise HTTPException(500, result.get("error") or "advance_failed")
        bp = result["blueprint"]
        await db.freebuild_projects.update_one(
            {"id": pid}, {"$set": {"discovery": bp}},
        )
        return {
            "ok": True,
            "blueprint": bp,
            "ready_to_build": result.get("ready_to_build", False),
            "summary_for_customer_ar": result.get("summary_for_customer_ar", ""),
            "credit_charged": DISCOVERY_BATCH_COST,
            "credit_balance": new_balance,
        }

    @router.get("/project/{pid}/discovery/status")
    async def discovery_status(pid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0, "discovery": 1},
        )
        if proj is None:
            raise HTTPException(404)
        bp = proj.get("discovery")
        if not bp:
            return {"ok": True, "started": False, "blueprint": None}
        return {"ok": True, "started": True, "blueprint": bp}

    @router.post("/project/{pid}/discovery/start-build")
    async def discovery_start_build(pid: str, user=Depends(get_current_user)):
        """Customer confirms 'ready to build' — flips status and injects a
        kickoff message into the chat session so the Builder picks up the
        blueprint on the next turn."""
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]},
            {"_id": 0, "id": 1, "discovery": 1},
        )
        if not proj or not proj.get("discovery"):
            raise HTTPException(404)
        bp = proj["discovery"]
        bp["status"] = "building"
        bp["progress_pct"] = 100
        from modules.freebuild.discovery_brain import render_blueprint_for_builder
        builder_brief = render_blueprint_for_builder(bp)
        kickoff = (
            "✅ [العميل اعتمد خارطة الطريق من Discovery Brain — ابدأ البناء الآن]\n\n"
            + builder_brief
        )
        try:
            from datetime import datetime, timezone as _tz
            await db.freebuild_chat_sessions.update_one(
                {"project_id": pid},
                {
                    "$push": {"messages": {
                        "role": "user",
                        "content": kickoff,
                        "ts": datetime.now(_tz.utc).isoformat(),
                        "source": "discovery_kickoff",
                    }},
                    "$set": {"updated_at": datetime.now(_tz.utc).isoformat()},
                    "$setOnInsert": {
                        "project_id": pid,
                        "user_id": user["user_id"],
                        "created_at": datetime.now(_tz.utc).isoformat(),
                    },
                },
                upsert=True,
            )
        except Exception:
            pass
        await db.freebuild_projects.update_one(
            {"id": pid}, {"$set": {"discovery": bp}},
        )
        return {"ok": True, "kickoff_preview": kickoff[:300], "blueprint_status": bp["status"]}


    # ═══════════════════════════════════════════════════════════════
    # EXPORT SOURCE CODE — bundle the website as a self-contained ZIP
    # so the customer can host it anywhere (gumroad-style ownership).
    # Downloads all external images locally and rewrites src URLs.
    # ═══════════════════════════════════════════════════════════════
    @router.get("/project/{pid}/export-source")
    async def export_source(pid: str, user=Depends(get_current_user)):
        """Bundle the current_html + all images + README + LICENSE as a ZIP."""
        import io
        import zipfile
        import httpx
        from fastapi.responses import StreamingResponse

        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404, "Project not found")
        # 💳 PAYWALL — source export is a paid feature ($100 one-time)
        if not proj.get("code_unlocked"):
            raise HTTPException(
                402,
                "الكود المصدري ميزة مدفوعة. اشتر الباقة من /api/freebuild-chat/project/{pid}/unlock أولاً.",
            )
        html = proj.get("current_html") or ""
        if not html:
            raise HTTPException(400, "ما فيه موقع جاهز للتصدير بعد. اطلب من الذكاء يبني التصميم أولاً.")

        # Strip the Zenrex auto-injected footer for paid source export
        # (customer owns the code now). The mark is at module top.
        if ZENREX_FOOTER_MARK in html:
            footer_start = html.find(ZENREX_FOOTER_MARK)
            footer_end = html.find("</a>", footer_start)
            if footer_end != -1:
                html = html[:footer_start] + html[footer_end + 4:]

        # Find every external image src and download it locally.
        img_pattern = re.compile(
            r'(<img\b[^>]*?\bsrc\s*=\s*["\'])(https?://[^"\']+)(["\'])',
            re.IGNORECASE,
        )
        # Also pick up CSS url(https://...) backgrounds
        css_url_pattern = re.compile(
            r'url\(\s*["\']?(https?://[^)"\']+)["\']?\s*\)',
            re.IGNORECASE,
        )

        external_urls: Dict[str, str] = {}  # url → local relative path
        for m in img_pattern.finditer(html):
            url = m.group(2)
            if url not in external_urls:
                # Build a safe local filename
                ext = ".jpg"
                lower = url.lower().split("?")[0]
                for cand in (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"):
                    if lower.endswith(cand):
                        ext = cand
                        break
                fname = f"img-{hashlib.md5(url.encode()).hexdigest()[:10]}{ext}"
                external_urls[url] = f"assets/{fname}"
        for m in css_url_pattern.finditer(html):
            url = m.group(1)
            if url not in external_urls and url.startswith("http"):
                ext = ".jpg"
                lower = url.lower().split("?")[0]
                for cand in (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"):
                    if lower.endswith(cand):
                        ext = cand
                        break
                fname = f"bg-{hashlib.md5(url.encode()).hexdigest()[:10]}{ext}"
                external_urls[url] = f"assets/{fname}"

        # Download all unique external assets in parallel
        downloaded: Dict[str, bytes] = {}
        failures: List[str] = []
        if external_urls:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as cli:
                async def _fetch(u: str):
                    try:
                        r = await cli.get(u)
                        if r.status_code == 200:
                            downloaded[u] = r.content
                        else:
                            failures.append(f"{u} (HTTP {r.status_code})")
                    except Exception as e:  # noqa: BLE001
                        failures.append(f"{u} ({type(e).__name__})")
                await asyncio.gather(*[_fetch(u) for u in external_urls.keys()])

        # Rewrite the HTML to point to the local /assets/ paths for downloaded ones.
        # Failed URLs stay as-is (customer can manually replace later).
        def _rewrite_img(m: re.Match) -> str:
            url = m.group(2)
            if url in downloaded:
                return m.group(1) + external_urls[url] + m.group(3)
            return m.group(0)

        def _rewrite_css(m: re.Match) -> str:
            url = m.group(1)
            if url in downloaded:
                return f"url({external_urls[url]})"
            return m.group(0)

        html = img_pattern.sub(_rewrite_img, html)
        html = css_url_pattern.sub(_rewrite_css, html)

        # Build the README.md
        readme = f"""# {proj.get('name') or 'موقعي'}

تم بناء هذا الموقع بواسطة **Zenrex AI** (https://zenrex.ai)
وأنت تملك السورس كامل — استضفه على أي مزود تحبه.

## محتويات الحزمة

- `index.html` — الصفحة الرئيسية
- `assets/` — مجلد الصور والوسائط
- `LICENSE.txt` — رخصة الاستخدام

## كيف أنشره؟

### الطريقة 1: Netlify (مجاناً، سهل)
1. ادخل https://app.netlify.com/drop
2. اسحب وأفلت الـ ZIP كامل
3. خلاص — موقعك شغّال على رابط `*.netlify.app`

### الطريقة 2: Vercel
1. ارفع الملفات إلى مستودع GitHub
2. ادخل https://vercel.com → New Project → استورد المستودع
3. اضغط Deploy

### الطريقة 3: استضافة مدفوعة (Hostinger, GoDaddy)
1. ادخل لوحة التحكم → File Manager
2. اذهب إلى مجلد `public_html`
3. ارفع كل الملفات بنفس الترتيب

## التعديل اليدوي

- لتغيير ألوان أو نصوص: افتح `index.html` بمحرر VSCode أو Notepad
- لتغيير الصور: استبدل ملفات داخل `assets/` بنفس الأسماء، أو غيّر مسارات `src`

## ملاحظات

- الموقع يستخدم Tailwind CSS عبر CDN (لا يحتاج build)
- الخطوط من Google Fonts (متصلة بالإنترنت)
- إذا قرّرت استضافة على VPS خاص بدون إنترنت، نزّل Tailwind محلياً

## دعم

عندك سؤال؟ تواصل: support@zenrex.ai
"""

        license_txt = f"""ZENREX AI SOURCE CODE LICENSE
=====================================

Project: {proj.get('name') or 'website'}
Project ID: {pid}
Customer: {user.get('email') or user.get('user_id')}
Issued: {_now()}

You (the buyer) have purchased FULL OWNERSHIP rights to this source code.

You may:
  ✓ Use it commercially without royalties
  ✓ Modify, adapt, and rebrand it
  ✓ Host it on any infrastructure (yours, third-party, or cloud)
  ✓ Resell modified derivatives to your own clients
  ✓ Remove all references to Zenrex AI

You may not:
  ✗ Re-sell this exact unmodified package to others
  ✗ Claim it was created by anyone but Zenrex AI when redistributed unchanged

Zenrex AI provides this code AS-IS without warranty of any kind.
For questions: legal@zenrex.ai
"""

        # Pack everything into a ZIP in memory
        buf = io.BytesIO()
        # ─── 💎 Independence Tier — build the premium delivery kit ───
        independence_files: Dict[str, str] = {}
        if proj.get("tier") == "full_independence":
            try:
                from modules.freebuild.independence_kit import build_independence_kit
                independence_files = await build_independence_kit(
                    proj, owner_email=user.get("email") or user.get("user_id") or "—"
                )
            except Exception as e:  # noqa: BLE001
                logger.exception("independence_kit build failed: %s", e)
                # graceful fallback — still ship base files
                independence_files = {}

        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.html", html)
            # Base README/LICENSE only when no premium kit (premium overrides them)
            if "README.md" not in independence_files:
                zf.writestr("README.md", readme)
            if "LICENSE" not in independence_files and "LICENSE.txt" not in independence_files:
                zf.writestr("LICENSE.txt", license_txt)
            for url, content in downloaded.items():
                local_path = external_urls[url]
                zf.writestr(local_path, content)
            # Write all independence-kit files (Dockerfile, deploy.sh, etc.)
            for fname, fcontent in independence_files.items():
                zf.writestr(fname, fcontent)
            if failures:
                zf.writestr(
                    "assets/MISSING_ASSETS.txt",
                    "هذه الصور فشل تنزيلها — استبدلها يدوياً:\n\n"
                    + "\n".join(failures),
                )

        buf.seek(0)
        safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", proj.get("name") or "website")[:50] or "website"
        is_independence = proj.get("tier") == "full_independence"
        zip_prefix = "zenrex-independence" if is_independence else "zenrex"
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{zip_prefix}-{safe_name}.zip"',
                "X-Assets-Downloaded": str(len(downloaded)),
                "X-Assets-Failed": str(len(failures)),
                "X-Tier": proj.get("tier") or "code_only",
                "X-Kit-Files": str(len(independence_files)),
            },
        )

    # ═══════════════════════════════════════════════════════════════
    # 🚀 INDEPENDENCE PHASE-2 — One-click VPS provisioning via Hetzner.
    # The customer pastes their Hetzner API token once, we save it via
    # /connections/hetzner, then they hit /provision-vps which:
    #   1. Mints a one-time signed kit-download URL (60 min TTL).
    #   2. Creates a CX22 server with cloud-init that auto-deploys.
    #   3. Persists vps_provisioning state on the project.
    #   4. Frontend polls /vps-status until cloud-init finishes.
    # ═══════════════════════════════════════════════════════════════

    @router.get("/project/{pid}/kit-download/{token}")
    async def kit_download_signed(pid: str, token: str, request: Request):
        """Public, signed, one-time kit ZIP download for cloud-init.
        Validated via HMAC + expiry. NO auth header required (it's the
        server that calls us, with no credentials at boot time)."""
        from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
        import io
        import zipfile
        from fastapi.responses import StreamingResponse

        secret = os.environ.get("KIT_SIGN_SECRET") or os.environ.get("FB_FERNET_KEY") or "zenrex-kit-secret"
        signer = URLSafeTimedSerializer(secret, salt="independence-kit")
        try:
            payload = signer.loads(token, max_age=3600)
        except SignatureExpired:
            raise HTTPException(410, "رابط منتهي — اطلب رابطاً جديداً.")
        except BadSignature:
            raise HTTPException(403, "توقيع غير صالح.")
        if payload.get("pid") != pid:
            raise HTTPException(403, "الرابط لمشروع آخر.")

        proj = await db.freebuild_projects.find_one({"id": pid}, {"_id": 0})
        if not proj or not proj.get("current_html"):
            raise HTTPException(404, "المشروع غير جاهز.")

        # Build the kit (same as /export-source but bypassing auth — signature is the proof)
        from modules.freebuild.independence_kit import build_independence_kit
        owner_email = payload.get("owner_email") or "—"
        kit = await build_independence_kit(proj, owner_email=owner_email)

        # Strip Zenrex footer from HTML
        html = proj.get("current_html") or ""
        if ZENREX_FOOTER_MARK in html:
            fs = html.find(ZENREX_FOOTER_MARK)
            fe = html.find("</a>", fs)
            if fe != -1:
                html = html[:fs] + html[fe + 4:]

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.html", html)
            for fname, fcontent in kit.items():
                zf.writestr(fname, fcontent)
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="zenrex-kit-{pid[:8]}.zip"'},
        )

    @router.post("/project/{pid}/provision-vps")
    async def provision_vps(
        pid: str,
        request: Request,
        domain: str = Form(default=""),
        server_type: str = Form(default="cx22"),
        location: str = Form(default="nbg1"),
        user=Depends(get_current_user),
    ):
        """Create a Hetzner CX22 and auto-deploy the Independence Kit."""
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404)
        if proj.get("tier") != "full_independence":
            raise HTTPException(402, "هذه الميزة لباقة الاستقلال الكامل فقط ($799).")
        if not proj.get("current_html"):
            raise HTTPException(400, "أكمل بناء الموقع قبل النشر على VPS.")
        # Fetch the saved Hetzner token
        conn = await db.freebuild_connections.find_one(
            {"project_id": pid, "user_id": user["user_id"], "provider": "hetzner"},
            {"_id": 0, "token_enc": 1},
        )
        if not conn:
            raise HTTPException(
                400,
                "اربط Hetzner أولاً من زر 'الاتصالات' — تحتاج Personal API Token من Hetzner Console.",
            )
        token = _dec(conn["token_enc"])
        if not token:
            raise HTTPException(400, "التوكن المحفوظ تالف. أعد ربط Hetzner.")

        # Generate a one-time signed kit-download URL the cloud-init can hit
        from itsdangerous import URLSafeTimedSerializer
        secret = os.environ.get("KIT_SIGN_SECRET") or os.environ.get("FB_FERNET_KEY") or "zenrex-kit-secret"
        signer = URLSafeTimedSerializer(secret, salt="independence-kit")
        sig_token = signer.dumps({"pid": pid, "owner_email": user.get("email") or user.get("user_id")})
        host = _public_host()
        kit_url = f"{host}/api/freebuild-chat/project/{pid}/kit-download/{sig_token}"

        # Create the Hetzner server (this is sync — blocks for ~3s)
        try:
            from modules.freebuild.hetzner_provision import create_server
            result = create_server(
                token=token,
                name=(proj.get("name") or f"zenrex-{pid[:8]}")[:50],
                project_id=pid,
                kit_url=kit_url,
                domain=domain.strip() or None,
                server_type=server_type,
                location=location,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))

        # Persist the VPS metadata on the project
        vps = {
            "server_id": result["server_id"],
            "ip": result.get("ip"),
            "name": result.get("name"),
            "server_type": result.get("server_type"),
            "location": result.get("location"),
            "image": result.get("image"),
            "domain": domain.strip(),
            "root_password_enc": _enc(result.get("root_password") or ""),
            "status": result.get("status") or "provisioning",
            "cloud_init_status": "running",
            "created_at": _now(),
            "updated_at": _now(),
        }
        await db.freebuild_projects.update_one(
            {"id": pid}, {"$set": {"vps": vps, "updated_at": _now()}}
        )
        return {
            "ok": True,
            "server_id": vps["server_id"],
            "ip": vps["ip"],
            "status": vps["status"],
            "domain": vps["domain"],
            "estimated_ready_in_seconds": 180,
        }

    @router.get("/project/{pid}/vps-status")
    async def vps_status(pid: str, user=Depends(get_current_user)):
        """Poll Hetzner for current server status. Frontend polls every 5s."""
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0, "vps": 1}
        )
        if not proj or not proj.get("vps"):
            raise HTTPException(404, "ما فيه VPS مرتبط بهذا المشروع.")
        vps = proj["vps"]
        conn = await db.freebuild_connections.find_one(
            {"project_id": pid, "user_id": user["user_id"], "provider": "hetzner"},
            {"_id": 0, "token_enc": 1},
        )
        if not conn:
            return {"ok": True, **{k: v for k, v in vps.items() if k != "root_password_enc"}}
        token = _dec(conn["token_enc"])
        try:
            from modules.freebuild.hetzner_provision import get_server_status
            live = get_server_status(token, vps["server_id"])
            # Update DB if status changed
            if live.get("status") != vps.get("status") or live.get("ip") != vps.get("ip"):
                await db.freebuild_projects.update_one(
                    {"id": pid},
                    {"$set": {
                        "vps.status": live.get("status"),
                        "vps.ip": live.get("ip") or vps.get("ip"),
                        "vps.updated_at": _now(),
                    }},
                )
                vps["status"] = live.get("status")
                vps["ip"] = live.get("ip") or vps.get("ip")
        except ValueError:
            pass
        public = {k: v for k, v in vps.items() if k != "root_password_enc"}
        # Provide a friendly Arabic stage label
        stage_ar = {
            "initializing": "📦 جاري التهيئة...",
            "starting": "▶️ السيرفر يقلع...",
            "running": "✅ السيرفر شغّال — جاري نشر الموقع...",
            "stopping": "🛑 جاري الإيقاف...",
            "off": "⏸️ السيرفر متوقف",
            "deleting": "🗑️ جاري الحذف",
        }.get(public.get("status") or "", public.get("status"))
        return {"ok": True, **public, "stage_ar": stage_ar}

    @router.post("/project/{pid}/vps-validate-token")
    async def vps_validate_token(
        pid: str,
        token: str = Form(...),
        user=Depends(get_current_user),
    ):
        """Quick sanity check on a Hetzner token before saving it.
        Returns the available locations so the UI can offer a dropdown."""
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0, "id": 1}
        )
        if not proj:
            raise HTTPException(404)
        try:
            from modules.freebuild.hetzner_provision import validate_token
            return validate_token(token)
        except ValueError as e:
            raise HTTPException(400, str(e))

    # ═══════════════════════════════════════════════════════════════
    # 🔧 PHASE 3 — Backend Builder preview + generate
    # ═══════════════════════════════════════════════════════════════
    @router.get("/project/{pid}/backend-preview")
    async def backend_preview(pid: str, user=Depends(get_current_user)):
        """Show the customer what backend will be generated — entities,
        endpoints, auth scaffold — before they commit. Result is cached
        on the project so a refresh doesn't re-call Claude."""
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404)
        if proj.get("tier") != "full_independence":
            raise HTTPException(402, "هذه الميزة لباقة الاستقلال الكامل فقط ($799).")

        cached = proj.get("backend_analysis")
        if cached:
            return {"ok": True, "cached": True, "analysis": cached}

        from modules.freebuild.backend_builder import analyze_blueprint
        blueprint = proj.get("discovery") or {}
        analysis = await analyze_blueprint(blueprint)
        await db.freebuild_projects.update_one(
            {"id": pid}, {"$set": {"backend_analysis": analysis, "updated_at": _now()}}
        )
        return {"ok": True, "cached": False, "analysis": analysis}

    @router.post("/project/{pid}/backend-preview/regenerate")
    async def backend_preview_regenerate(pid: str, user=Depends(get_current_user)):
        """Force a fresh Claude call to rebuild the analysis (e.g. after
        the customer added more answers in Discovery)."""
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0, "id": 1, "tier": 1, "discovery": 1}
        )
        if not proj:
            raise HTTPException(404)
        if proj.get("tier") != "full_independence":
            raise HTTPException(402)
        from modules.freebuild.backend_builder import analyze_blueprint
        analysis = await analyze_blueprint(proj.get("discovery") or {})
        await db.freebuild_projects.update_one(
            {"id": pid}, {"$set": {"backend_analysis": analysis, "updated_at": _now()}}
        )
        return {"ok": True, "analysis": analysis}

    @router.post("/project/{pid}/snapshots/{sid}/restore")
    async def restore_snapshot(pid: str, sid: str, user=Depends(get_current_user)):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404)
        target = None
        for s in (proj.get("html_snapshots") or []):
            if s.get("id") == sid:
                target = s
                break
        if not target:
            raise HTTPException(404, "نسخة غير موجودة")
        # Push current_html as a NEW snapshot (so restore is reversible)
        push_doc: Dict[str, Any] = {}
        if proj.get("current_html"):
            push_doc["html_snapshots"] = {
                "$each": [_make_snapshot_doc(
                    proj["current_html"],
                    user_msg=f"[نسخة محفوظة تلقائياً قبل استرجاع {sid[:8]}]",
                    kind="pre_restore",
                    label="قبل استرجاع نسخة سابقة",
                )],
            }
        update_doc: Dict[str, Any] = {
            "$set": {"current_html": target["html"], "updated_at": _now()},
        }
        if push_doc:
            update_doc["$push"] = push_doc
        await db.freebuild_projects.update_one({"id": pid}, update_doc)
        return {
            "ok": True,
            "restored_summary": target.get("summary") or _summarize_html(target.get("html", "")),
            "html_length": len(target.get("html", "")),
        }

    # ═══════════════════════════════════════════════════════════════
    # AGENT-CHAT — Claude tool-using agent (Anthropic native tools).
    # Same architecture as the platform AI: real tools, iterative
    # self-correction, no hidden state.
    # ═══════════════════════════════════════════════════════════════
    @router.post("/project/{pid}/agent-chat")
    async def agent_chat(
        pid: str,
        message: str = Form(...),
        user=Depends(get_current_user),
    ):
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404, "مشروع غير موجود")
        try:
            from .freebuild_agent import run_agent_turn
        except Exception:
            logger.exception("agent import failed")
            raise HTTPException(500, "agent module unavailable")

        history = proj.get("messages") or []
        # Extract bearer token from current Request scope for sub-API calls (publish_site tool, etc.)
        from fastapi import Request as _Req  # local import to avoid top-level churn
        _request: Optional[_Req] = None  # we don't have direct access here — Depends would need refactor.
        # Workaround: re-sign a short-lived JWT for the current user so the agent tools
        # can call protected endpoints as the same user.
        try:
            import jwt as _jwt, time as _time
            _secret = os.environ.get("JWT_SECRET", "")
            _agent_token = _jwt.encode(
                {"user_id": user["user_id"], "email": user.get("email", ""), "role": user.get("role", "user"),
                 "iat": int(_time.time()), "exp": int(_time.time()) + 3600},
                _secret, algorithm="HS256",
            ) if _secret else None
        except Exception:
            _agent_token = None
        # Owner check — only the platform owner gets access to local_browser_*, run_shell, etc.
        is_platform_owner = (user.get("role") or "").lower() in ("owner", "admin", "superuser")
        result = await run_agent_turn(
            project=proj,
            user_message=message,
            history_messages=history,
            auth_token=_agent_token,
            db=db,
            is_owner=is_platform_owner,
        )
        if not result.get("ok"):
            raise HTTPException(502, result.get("error", "agent failed"))

        summary = result["summary"]
        new_html = result.get("new_html")
        options = result.get("options") or []
        iterations = result.get("iterations", 0)
        snapshots = result.get("snapshots") or []

        update_set: Dict[str, Any] = {"updated_at": _now()}
        push_ops: Dict[str, Any] = {
            "messages": {
                "$each": [
                    {"role": "user", "content": message, "timestamp": _now(),
                     "pending_assets": [], "attachments": [], "reference": None,
                     "answer_meta": None},
                    {"role": "assistant", "content": summary, "timestamp": _now(),
                     "pending_assets": [], "had_html": bool(new_html),
                     "options": options, "design_variants": [],
                     "agent_iterations": iterations,
                     "model_used": ""},
                ]
            }
        }
        if new_html:
            update_set["current_html"] = _inject_zenrex_footer(new_html)
            # Auto-advance phase whenever we ship HTML (anti-stuck-on-discovery)
            update_set["current_phase"] = "build"
            _hist = set(proj.get("phase_history") or [])
            for _ph in ("discovery", "design", "assets"):
                _hist.add(_ph)
            update_set["phase_history"] = list(_hist)
        if snapshots:
            # UNLIMITED snapshots — user wants full design archive history.
            # Normalize each snapshot with kind/label if the agent didn't set them.
            _normalized = []
            for _s in snapshots:
                if not isinstance(_s, dict):
                    continue
                _s.setdefault("kind", "auto")
                _s.setdefault("label", "قبل تعديل (وكيل)")
                _normalized.append(_s)
            if _normalized:
                push_ops["html_snapshots"] = {"$each": _normalized}
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$push": push_ops, "$set": update_set},
        )
        return {
            "response": summary,
            "html_updated": bool(new_html),
            "options": options,
            "agent_iterations": iterations,
            "model_used": "",
            "task_label": f"🤖 يعمل ({iterations} خطوة)",
            "tool_log": result.get("tool_log", []),
        }

    @router.post("/project/{pid}/agent-chat-stream")
    async def agent_chat_stream(
        pid: str,
        message: str = Form(...),
        user_language: str = Form("ar"),
        mode: str = Form("default"),  # "default" = full Brain workflow, "lab" = bare AI + tools only
        user=Depends(get_current_user),
    ):
        """SSE endpoint: streams 'thinking' events as the agent works."""
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404, "مشروع غير موجود")
        try:
            from .freebuild_agent import stream_agent_turn, FreeBuildToolContext, _exec_tool
            from ..brain import BrainOrchestrator, BrainConfig
            from ..brain.core import brain_stream_turn
            from fastapi.responses import StreamingResponse
        except Exception:
            logger.exception("agent import failed")
            raise HTTPException(500, "agent module unavailable")

        history = proj.get("messages") or []
        # Owner check — only the platform owner gets access to local_browser_*, desktop_*, run_shell, etc.
        is_platform_owner_stream = (user.get("role") or "").lower() in ("owner", "admin", "superuser")

        # ── Hard STORAGE gate (Feb 2026 v2) ────────────────────────────
        try:
            from modules.storage_billing import (
                _evaluate_subscription_state, _quota_for_subscription,
            )
            _sub2 = await _evaluate_subscription_state(db, user["user_id"])
            _info2 = _quota_for_subscription(_sub2)
            _used2 = await _user_total_bytes(db, user["user_id"]) / (1024 * 1024)
            _over2 = _used2 >= _info2["quota_mb"]
            if _info2["locked"] or _over2:
                _reason2 = _info2["locked_reason"] or "امتلأت مساحتك التخزينية. ادفع لتفك القفل."
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "storage_locked",
                        "locked": _info2["locked"],
                        "over_quota": _over2,
                        "used_mb": round(_used2, 2),
                        "quota_mb": _info2["quota_mb"],
                        "status": _info2["status"],
                        "plan_id": _info2["plan_id"],
                        "message_ar": _reason2,
                        "cta_url": "/billing/storage",
                    },
                )
        except HTTPException:
            raise
        except Exception as _se2:
            logger.warning(f"[agent-chat-stream] storage gate skipped: {_se2}")

        # ── 🛡️ Action-Aware Pre-Flight Credit Gate ────────────────────
        # Replaces the old flat 25-credit minimum. Now classifies the user's
        # intent (create_page/section_add/deletion/edit/etc.) BEFORE the
        # agent streams a single token and refuses turns the user can't
        # afford. The 402 response includes a smart recommendation so the
        # UI can surface "اشحن باقة Indie ($29) لتنفيذ 30+ عملية مثل هذه".
        # NO role bypass — every user pays from their balance.
        from .action_pricing import preflight_check
        _u_credits_doc = await db.users.find_one(
            {"id": user["user_id"]}, {"_id": 0, "credits": 1},
        ) or {}
        _balance = int(round(float(_u_credits_doc.get("credits") or 0)))
        _pf = preflight_check(_balance, message)
        if not _pf.get("allowed"):
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "insufficient_credits",
                    "balance": _balance,
                    "required": _pf["min_cost"],
                    "needed": _pf["needed"],
                    "intent": _pf["intent"],
                    "estimated_max": _pf["max_cost"],
                    "recommended_plan": _pf["recommended_plan"],
                    "recharge_url": _pf["recharge_url"],
                    "message_ar": _pf["message"],
                },
            )
        # Mint a short-lived JWT so the agent tools (publish_site, download_media, etc.)
        # can call protected /api endpoints as the same user.
        try:
            import jwt as _jwt, time as _time
            _secret = os.environ.get("JWT_SECRET", "")
            _agent_token = _jwt.encode(
                {"user_id": user["user_id"], "email": user.get("email", ""), "role": user.get("role", "user"),
                 "iat": int(_time.time()), "exp": int(_time.time()) + 3600},
                _secret, algorithm="HS256",
            ) if _secret else None
        except Exception:
            _agent_token = None
        # ──────────────────────────────────────────────────────────────────
        # 🔋 BACKGROUND-RESILIENT EXECUTION
        # ──────────────────────────────────────────────────────────────────
        # If the user closes the tab, loses internet, or refreshes the page,
        # we DO NOT want the agent to die mid-thought. So we spawn the agent
        # as a detached asyncio.Task that owns its own DB-persistence flow,
        # and the SSE response just tails an asyncio.Queue. If the SSE
        # consumer (client) goes away, the queue reader stops but the
        # background task continues until `finish` is called by the agent.
        # When the user reconnects, GET /project/{pid} will already show the
        # final message because the task wrote it via its own `finally`.
        import asyncio as _asyncio
        event_queue: "_asyncio.Queue[str | None]" = _asyncio.Queue(maxsize=200)
        ctx_holder: Dict[str, Any] = {}
        captured: Dict[str, Any] = {
            "summary": "", "options": [], "inline_images": [],
            "inline_audio": [], "inline_video": [],
            "iterations": 0, "model_used": "", "html_updated": False,
        }

        async def _run_agent_in_background():
            """Owns the agent lifecycle + the final DB write. Cancellation-safe."""
            last_persisted_changes = 0
            # ── 💎 Cost Preview event (for operations ≥ 200 credits) ──
            # Tells the UI to render a "🎯 هذه العملية ستكلف ~N شعلة" toast
            # before the AI starts. Builds trust + sets expectations.
            try:
                if _pf.get("preview_recommended"):
                    preview_payload = json.dumps({
                        "intent": _pf["intent"],
                        "min_cost": _pf["min_cost"],
                        "max_cost": _pf["max_cost"],
                        "current_balance": _balance,
                        "message_ar": (
                            f"🎯 هذه العملية متوقَّعة بين {_pf['min_cost']}–{_pf['max_cost']} شعلة "
                            f"(رصيدك الآن: {_balance})."
                        ),
                    }, ensure_ascii=False)
                    await event_queue.put(f"event: cost_preview\ndata: {preview_payload}\n\n")
            except Exception:
                pass
            # ────── 🆕 CONCIERGE PRECHECK ──────
            # Detect if the request needs 3rd-party keys (EAS / Liveblocks /
            # Stripe / Mapbox / OpenAI / Resend / etc.). If so, stream the
            # setup wizard cards instead of running the agent.
            try:
                from .concierge_hooks import precheck_integrations, stream_wizard_as_sse
                _check = await precheck_integrations(
                    db=db, user_id=user["user_id"], project_id=pid, user_message=message,
                )
                if _check.get("should_block_build"):
                    for _evt in stream_wizard_as_sse(_check):
                        await event_queue.put(_evt)
                    await event_queue.put(
                        f"event: done\ndata: {json.dumps({'paused_for_setup': True, 'pending_integrations': [p['integration_id'] for p in _check['pending']], 'summary': '⏸️ بانتظار إعداد المفاتيح المطلوبة. أكمل الـ Setup Wizard بالأعلى ثم سأكمل البناء فوراً.', 'credits_charged': 0, 'auto_refunded': True, 'model_used': 'concierge', 'iterations': 0, 'options': [], 'inline_images': []}, ensure_ascii=False)}\n\n"
                    )
                    await event_queue.put(None)  # close
                    return
            except Exception as _ce:
                logger.warning(f"[agent-chat-stream] concierge precheck skipped: {_ce}")
            # ────────────────────────────────────
            # 🆕 INTENT CLASSIFIER ROUTING (architect/review fast-paths)
            # Before invoking stream_agent_turn, classify the user message.
            # Special domains (architect, review) get a focused cortex that
            # produces a single-pass output. Other domains (code/visual/audio/
            # video/narrative/multi) still go through stream_agent_turn which
            # has full tool access — the classifier just emits a hint event.
            _routed_via_cortex = False
            try:
                from .orchestrator.classifier import classify_intent_domain
                _intent = classify_intent_domain(message)
                await event_queue.put(
                    f"event: classifier\ndata: {json.dumps({'primary': _intent.primary, 'secondary': _intent.secondary, 'confidence': _intent.confidence, 'rationale': _intent.rationale}, ensure_ascii=False)}\n\n"
                )
                # Fast-path: architect cortex (produces Mermaid + ADR blueprint)
                if _intent.primary == "architect" and _intent.confidence >= 0.85:
                    from .orchestrator.cortices.architect_cortex import stream_architect_cortex
                    async for chunk in stream_architect_cortex(
                        user_message=message,
                        project=proj,
                        brand_dna=proj.get("brand_dna"),
                    ):
                        await event_queue.put(chunk)
                        if chunk.startswith("event: done\n"):
                            try:
                                _dl = [ln for ln in chunk.split("\n") if ln.startswith("data:")][0][5:].strip()
                                done = json.loads(_dl)
                                captured["summary"] = done.get("summary", "")
                                captured["model_used"] = done.get("model_used", "architect")
                                captured["iterations"] = done.get("iterations", 1)
                                captured["credits_charged"] = int(done.get("credits_charged") or 0)
                            except Exception:
                                pass
                    _routed_via_cortex = True
                # Fast-path: review cortex (static + LLM review of pasted code)
                elif _intent.primary == "review" and _intent.confidence >= 0.85:
                    from .orchestrator.review_cortex import review_code, render_review_report_ar
                    rep = review_code(message, "mixed")
                    summary_ar = render_review_report_ar(rep)
                    await event_queue.put(
                        f"event: cortex_step\ndata: {json.dumps({'cortex': 'review', 'score': rep.get('score')}, ensure_ascii=False)}\n\n"
                    )
                    captured["summary"] = summary_ar
                    captured["model_used"] = "static_analyzer"
                    captured["iterations"] = 1
                    captured["credits_charged"] = 3
                    captured["review_report"] = rep
                    await event_queue.put(
                        f"event: done\ndata: {json.dumps({'summary': summary_ar, 'auto_refunded': False, 'credits_charged': 3, 'model_used': 'static_analyzer', 'iterations': 1, 'options': [], 'inline_images': [], 'review_report': rep}, ensure_ascii=False)}\n\n"
                    )
                    _routed_via_cortex = True
            except Exception as _ce2:
                logger.exception(f"[agent-chat-stream] classifier routing failed: {_ce2}")
            # ────────────────────────────────────
            if _routed_via_cortex:
                await event_queue.put(None)
                return
            try:
                # 🎯 DEFAULT PATH = Lab pathway. The Brain orchestrator was
                # the root cause of multi-page navigation/build failures
                # (confirmed by user A/B: Lab Mode builds working multi-page
                # sites with working nav; the default chat going through
                # Brain produced sites where pages don't navigate). We now
                # route ALL chat through stream_agent_turn directly, with
                # an isolated project copy.
                # Pass `mode=legacy_brain` to opt back into Brain v2 for
                # debugging/A-B testing.
                if mode != "legacy_brain":
                    # 🆓 FREE CHAT — no workflow stages, no Brain, no rules.
                    # Pure AI + tools. The workflow_state on the project doc
                    # is preserved (we don't write to it) so we can re-enable
                    # stages later via mode='legacy_brain' or a future flag.
                    proj_free = dict(proj)
                    proj_free["workflow_state"] = {
                        "stage": "surgical_edit",
                        "discovery_answers": (proj.get("workflow_state") or {}).get("discovery_answers") or {},
                    }
                    # 🆕 HARD HOOK #1: Brand DNA auto-extraction on first message
                    # If this is the first user message in the project, kick off
                    # brand_dna extraction in background and persist into memory
                    # so future turns can reuse palette/tone/voice/glossary.
                    try:
                        if len(history) <= 1:  # first or empty history
                            _existing_dna = (proj.get("brand_dna") or {})
                            if not _existing_dna:
                                async def _extract_brand_dna_bg():
                                    try:
                                        from .orchestrator.brand_dna import extract_brand_dna
                                        dna = await extract_brand_dna(message)
                                        if dna:
                                            await db.freebuild_projects.update_one(
                                                {"id": pid}, {"$set": {"brand_dna": dna,
                                                                        "brand_dna_extracted_at": datetime.now(timezone.utc).isoformat()}},
                                            )
                                            try:
                                                await event_queue.put(
                                                    f"event: brand_dna_extracted\ndata: {json.dumps({'palette': dna.get('palette'), 'tone': dna.get('tone'), 'archetypes': dna.get('archetypes')}, ensure_ascii=False)}\n\n"
                                                )
                                            except Exception:
                                                pass
                                    except Exception as _bde:
                                        logger.warning(f"[brand_dna] bg extraction failed: {_bde}")
                                _asyncio.create_task(_extract_brand_dna_bg())
                    except Exception as _bdh:
                        logger.warning(f"[brand_dna] hook setup failed: {_bdh}")
                    async for chunk in stream_agent_turn(
                        proj_free, message, history,
                        ctx_holder=ctx_holder,
                        user_language=user_language,
                        auth_token=_agent_token,
                        db=db,
                        is_owner=is_platform_owner_stream,
                        max_iterations=60,
                        inject_workflow_addendum=False,
                    ):
                        if chunk.startswith("event: done\n"):
                            try:
                                data_line = [ln for ln in chunk.split("\n") if ln.startswith("data:")][0][5:].strip()
                                done = json.loads(data_line)
                                captured["summary"] = done.get("summary", "")
                                captured["options"] = done.get("options") or []
                                captured["inline_images"] = done.get("inline_images") or []
                                captured["inline_audio"] = done.get("inline_audio") or []
                                captured["inline_video"] = done.get("inline_video") or []
                                captured["iterations"] = done.get("iterations", 0)
                                captured["model_used"] = done.get("model_used", "")
                                captured["html_updated"] = done.get("html_updated", False)
                                captured["credits_charged"] = int(done.get("credits_charged") or 0)
                                # 🆕 HARD HOOK #2: Auto-Reviewer on HTML changes.
                                # When the agent updates current_html, run a
                                # fast static review and emit findings BEFORE
                                # the done event reaches the client. The done
                                # event itself is rewritten to include the
                                # review_report so frontend can display issues.
                                try:
                                    if done.get("html_updated"):
                                        ctx_now = ctx_holder.get("ctx")
                                        _html = (ctx_now.current_html if ctx_now else None) or ""
                                        if _html and len(_html) > 50:
                                            from .orchestrator.review_cortex import review_code, render_review_report_ar
                                            _rep = review_code(_html, "html")
                                            _crit = [i for i in (_rep.get("issues") or []) if i.get("severity") in ("critical", "high")]
                                            await event_queue.put(
                                                f"event: auto_review\ndata: {json.dumps({'score': _rep.get('score'), 'passed': _rep.get('passed'), 'critical_high_count': len(_crit), 'total_issues': len(_rep.get('issues') or [])}, ensure_ascii=False)}\n\n"
                                            )
                                            captured["review_report"] = _rep
                                            # Append a brief warning to summary if critical found
                                            if _crit:
                                                done["summary"] = (done.get("summary") or "") + (
                                                    f"\n\n⚠️ **مراجعة تلقائية:** عُثر على {len(_crit)} مشاكل حرجة. "
                                                    f"الـ score: {_rep.get('score')}/100. "
                                                    "اطلب `run_reviewer` للتفاصيل."
                                                )
                                                # Re-serialize and replace chunk
                                                chunk = f"event: done\ndata: {json.dumps(done, ensure_ascii=False)}\n\n"
                                                captured["summary"] = done["summary"]
                                except Exception as _arev:
                                    logger.warning(f"[auto_review] failed: {_arev}")
                            except Exception:
                                logger.exception("default stream: failed to parse done event")
                        # 🆕 Capture project_status / honesty_check / supervisor / escalation
                        # so they get persisted on the assistant message and survive reload.
                        for _ev_name in ("project_status", "honesty_check", "supervisor", "escalation"):
                            if chunk.startswith(f"event: {_ev_name}\n"):
                                try:
                                    _dl = [ln for ln in chunk.split("\n") if ln.startswith("data:")][0][5:].strip()
                                    captured[_ev_name] = json.loads(_dl)
                                except Exception:
                                    pass
                                break
                        if chunk.startswith("event: tool\n") and '"phase": "done"' in chunk:
                            ctx_now = ctx_holder.get("ctx")
                            if ctx_now and ctx_now.changes_made > last_persisted_changes and ctx_now.current_html:
                                try:
                                    await db.freebuild_projects.update_one(
                                        {"id": pid},
                                        {"$set": {"current_html": ctx_now.current_html,
                                                  "pages": ctx_now.pages,
                                                  "active_page": ctx_now.active_page,
                                                  "updated_at": datetime.now(timezone.utc).isoformat()}},
                                    )
                                    last_persisted_changes = ctx_now.changes_made
                                except Exception:
                                    logger.exception("default mid-stream persist failed")
                        try:
                            event_queue.put_nowait(chunk)
                        except _asyncio.QueueFull:
                            try:
                                event_queue.get_nowait()
                                event_queue.put_nowait(chunk)
                            except _asyncio.QueueEmpty:
                                pass
                else:
                    # mode == "legacy_brain" — opt-in path for debugging
                    # Brain v2 (state machine, discovery, plan, memory, strict
                    # completion). It defers to the legacy executor only
                    # inside the EXECUTING state. Kept available so we can
                    # A/B test if the user reports the new default is worse.
                    brain_cfg = BrainConfig(
                        section="freebuild",
                        user_language=user_language,
                        max_iterations=20,
                    )
                    async for chunk in brain_stream_turn(
                        proj, message, history,
                        config=brain_cfg,
                        ctx_holder=ctx_holder,
                        auth_token=_agent_token,
                        db=db,
                        is_owner=is_platform_owner_stream,
                    ):
                        # Capture done events for final persistence
                        if chunk.startswith("event: done\n"):
                            try:
                                data_line = [ln for ln in chunk.split("\n") if ln.startswith("data:")][0][5:].strip()
                                done = json.loads(data_line)
                                captured["summary"] = done.get("summary", "")
                                captured["options"] = done.get("options") or []
                                captured["inline_images"] = done.get("inline_images") or []
                                captured["inline_audio"] = done.get("inline_audio") or []
                                captured["inline_video"] = done.get("inline_video") or []
                                captured["iterations"] = done.get("iterations", 0)
                                captured["model_used"] = done.get("model_used", "")
                                captured["html_updated"] = done.get("html_updated", False)
                                captured["credits_charged"] = int(done.get("credits_charged") or 0)
                            except Exception:
                                logger.exception("agent stream: failed to parse done event")
                        # Mid-stream HTML checkpoint — survives disconnects
                        if chunk.startswith("event: tool\n") and '"phase": "done"' in chunk:
                            ctx_now = ctx_holder.get("ctx")
                            if ctx_now and ctx_now.changes_made > last_persisted_changes and ctx_now.current_html:
                                try:
                                    await db.freebuild_projects.update_one(
                                        {"id": pid},
                                        {"$set": {"current_html": ctx_now.current_html,
                                                  "pages": ctx_now.pages,
                                                  "active_page": ctx_now.active_page,
                                                  "updated_at": _now(),
                                                  "agent_in_progress": True}},
                                    )
                                    last_persisted_changes = ctx_now.changes_made
                                except Exception:
                                    logger.exception("mid-stream checkpoint failed")
                        # Push to queue — drop oldest if full (keeps memory bounded)
                        try:
                            event_queue.put_nowait(chunk)
                        except _asyncio.QueueFull:
                            try:
                                event_queue.get_nowait()
                                event_queue.put_nowait(chunk)
                            except _asyncio.QueueEmpty:
                                pass
            finally:
                # Persist to DB even on cancellation
                final_ctx = ctx_holder.get("ctx")
                new_html = final_ctx.current_html if (final_ctx and final_ctx.changes_made > 0) else None
                snapshots = final_ctx.snapshots_to_create if final_ctx else []
                if not captured.get("summary"):
                    if final_ctx and final_ctx.changes_made > 0:
                        captured["summary"] = (
                            f"⏸️ توقفت بشكل مفاجئ بعد {final_ctx.changes_made} تعديل. "
                            "العمل محفوظ — ابعث 'كمّل' وأكمل من حيث وقفت."
                        )
                    else:
                        captured["summary"] = "⏸️ انقطع الاتصال قبل ما أبدأ. أعد إرسال طلبك من فضلك."
                    captured["html_updated"] = bool(new_html)
                try:
                    update_set: Dict[str, Any] = {"updated_at": _now(), "agent_in_progress": False}
                    push_ops: Dict[str, Any] = {
                        "messages": {
                            "$each": [
                                {"role": "user", "content": message, "timestamp": _now(),
                                 "pending_assets": [], "attachments": [],
                                 "reference": None, "answer_meta": None},
                                {"role": "assistant", "content": captured["summary"],
                                 "timestamp": _now(), "pending_assets": [],
                                 "had_html": bool(new_html),
                                 "options": captured["options"],
                                 "inline_images": captured["inline_images"],
                                 "inline_audio": captured["inline_audio"],
                                 "inline_video": captured["inline_video"],
                                 "design_variants": [],
                                 "agent_iterations": captured["iterations"],
                                 "model_used": "",
                                 # 🆕 Sticky autonomy events so the footer card
                                 # (status + 4 deploy buttons + supervisor pill)
                                 # survives page reload.
                                 "project_status": captured.get("project_status"),
                                 "honesty_check": captured.get("honesty_check"),
                                 "supervisor_event": captured.get("supervisor"),
                                 "escalation_event": captured.get("escalation")},
                            ]
                        }
                    }
                    if new_html:
                        update_set["current_html"] = _inject_zenrex_footer(new_html)
                        update_set["current_phase"] = "build"
                    # Persist the full multi-page state ALWAYS (even when only
                    # non-active pages changed) so the `pages` dict + active_page
                    # survive across turns and reach auto-republish below.
                    if final_ctx:
                        try:
                            update_set["pages"] = final_ctx.pages
                            update_set["active_page"] = final_ctx.active_page
                        except Exception:
                            pass
                        # 🆕 Persist Mockup-Driven Workflow state too.
                        try:
                            _proj_state = final_ctx.project or {}
                            if _proj_state.get("mockups") is not None:
                                update_set["mockups"] = _proj_state.get("mockups")
                            if "blueprint_locked" in _proj_state:
                                update_set["blueprint_locked"] = _proj_state.get("blueprint_locked")
                            if "blueprint_locked_at" in _proj_state:
                                update_set["blueprint_locked_at"] = _proj_state.get("blueprint_locked_at")
                            if final_ctx.workflow_state_dirty and _proj_state.get("workflow_state") is not None:
                                update_set["workflow_state"] = _proj_state.get("workflow_state")
                        except Exception:
                            logger.exception("workflow/mockup persist failed")
                    if new_html:
                        # Mark prior phases done in history for the sidebar
                        try:
                            _proj_now = await db.freebuild_projects.find_one(
                                {"id": pid}, {"phase_history": 1, "_id": 0}
                            ) or {}
                            _hist = set(_proj_now.get("phase_history") or [])
                            for _ph in ("discovery", "design", "assets"):
                                _hist.add(_ph)
                            update_set["phase_history"] = list(_hist)
                        except Exception:
                            pass
                    if snapshots:
                        # UNLIMITED snapshots in Design Archive.
                        _normalized = []
                        for _s in snapshots:
                            if not isinstance(_s, dict):
                                continue
                            _s.setdefault("kind", "auto")
                            _s.setdefault("label", "قبل تعديل (وكيل)")
                            _normalized.append(_s)
                        if _normalized:
                            push_ops["html_snapshots"] = {"$each": _normalized}
                    await db.freebuild_projects.update_one(
                        {"id": pid},
                        {"$push": push_ops, "$set": update_set},
                    )
                except Exception:
                    logger.exception("background agent persist failed")

                # ── 🔁 AUTO-REPUBLISH: keep the public /s/{slug} URL in lockstep
                # with the editor. Triggers when ANY change happened — including
                # batch tools that edit non-active pages (where new_html itself
                # may not have shifted but ctx.pages did).
                try:
                    if final_ctx and final_ctx.changes_made > 0:
                        proj_doc = await db.freebuild_projects.find_one(
                            {"id": pid},
                            {"_id": 0, "published_slug": 1, "name": 1, "user_id": 1,
                             "pages": 1, "current_html": 1},
                        ) or {}
                        slug = proj_doc.get("published_slug")
                        if slug:
                            # Trust the just-persisted ctx.pages (already saved
                            # to DB on line ~6746 above). Fall back to DB pages
                            # if ctx ones are missing.
                            ctx_pages = dict(final_ctx.pages) if final_ctx.pages else {}
                            db_pages = proj_doc.get("pages") or {}
                            all_pages = ctx_pages or db_pages or {
                                "index.html": proj_doc.get("current_html") or new_html or ""
                            }
                            # Ensure index.html is present
                            if "index.html" not in all_pages:
                                all_pages["index.html"] = (
                                    final_ctx.current_html if final_ctx else ""
                                ) or proj_doc.get("current_html") or new_html or ""
                            published_current = (
                                all_pages.get(final_ctx.active_page if final_ctx else "index.html")
                                or all_pages.get("index.html")
                                or proj_doc.get("current_html")
                                or new_html
                                or ""
                            )
                            await db.freebuild_published_sites.update_one(
                                {"slug": slug},
                                {"$set": {
                                    "slug": slug,
                                    "project_id": pid,
                                    "user_id": user["user_id"],
                                    "current_html": published_current,
                                    "pages": all_pages,
                                    "name": proj_doc.get("name") or slug,
                                    "updated_at": _now(),
                                    "superseded": False,
                                    "auto_published": True,
                                }, "$setOnInsert": {
                                    "created_at": _now(),
                                    "views": 0,
                                }},
                                upsert=True,
                            )
                            logger.info(f"[auto-republish] synced slug={slug} for project={pid} ({len(all_pages)} pages, active={getattr(final_ctx,'active_page',None)})")
                except Exception as _rep_e:
                    logger.warning(f"[auto-republish] failed: {_rep_e}")

                # ── SAFETY NET: guarantee ≥1 credit deduction per chat turn ──
                # If the agent loop ran the full credit-deduction path (success),
                # `credits_charged_this_turn` will be a positive integer (stored
                # on captured by the agent module). If it's still 0 here (means
                # the stream was cancelled mid-flight, the agent crashed, or any
                # path skipped record_usage), charge a minimum floor so a user
                # can NEVER chat for free. This closes every loophole the user
                # observed where balance didn't decrease after a message.
                try:
                    if not int(captured.get("credits_charged") or 0):
                        from modules.ai_core.usage_meter import record_usage
                        await record_usage(
                            db, user["user_id"], pid,
                            section="websites",
                            tokens_in=0,
                            tokens_out=1500,        # ≈ 50-credit floor
                            model_label="zenrex-ai-floor",
                        )
                        logger.info(f"[credits-safety] applied floor charge for user {user['user_id']} (turn had no deduction)")
                except Exception as _ce:
                    logger.warning(f"[credits-safety] floor charge failed: {_ce}")
                # Signal queue completion
                try:
                    event_queue.put_nowait(None)
                except _asyncio.QueueFull:
                    pass

        # Mark project as in-progress + spawn the background task
        await db.freebuild_projects.update_one(
            {"id": pid}, {"$set": {"agent_in_progress": True, "updated_at": _now()}},
        )
        bg_task = _asyncio.create_task(_run_agent_in_background())

        async def event_stream():
            """Tail the queue. If client goes away, this generator dies but
            `bg_task` keeps running independently and finishes its `finally`.

            Sends a heartbeat comment every 15s during long LLM thinking to
            keep proxies (CloudFlare, nginx) from killing the connection.
            CloudFlare's default idle timeout is 100s — without these pings,
            multi-step builds would die mid-stream and the user would see
            'Stream stopped' even though the agent is still working.
            """
            HEARTBEAT_S = 15
            try:
                while True:
                    try:
                        chunk = await _asyncio.wait_for(event_queue.get(), timeout=HEARTBEAT_S)
                    except _asyncio.TimeoutError:
                        # No event in HEARTBEAT_S seconds → send a comment to
                        # keep the connection alive. Comments start with ":"
                        # per SSE spec and are ignored by the EventSource API.
                        yield f": ka {int(time.time())}\n\n"
                        continue
                    if chunk is None:
                        break
                    yield chunk
            except _asyncio.CancelledError:
                logger.info(f"[agent-stream] client disconnected, bg task continues for project {pid}")
                raise

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # ─────────────────────────────────────────────────────────────────────
    # 🧠 NEW: Orchestrator endpoint — Strangler Fig refactor entry point.
    # Routes the request via the new Orchestrator (CodeCortex / VisualCortex /
    # AudioCortex / VideoCortex / NarrativeCortex). Feature-flagged via env
    # `ORCHESTRATOR_ENABLED=true`. When disabled, this endpoint is identical
    # to /agent-chat-stream (zero behavioural change).
    # ─────────────────────────────────────────────────────────────────────
    @router.post("/project/{pid}/orchestrator-stream")
    async def orchestrator_chat_stream(
        pid: str,
        message: str = Form(...),
        user_language: str = Form("ar"),
        mode: str = Form("default"),
        force_domain: str = Form(""),  # optional: code/visual/audio/video/narrative — bypass classifier
        user=Depends(get_current_user),
    ):
        """Streams events through the new Orchestrator. Falls back to legacy
        path automatically if ORCHESTRATOR_ENABLED=false or any cortex errors."""
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404, "مشروع غير موجود")
        try:
            from .orchestrator import stream_via_orchestrator, is_orchestrator_enabled
            from .orchestrator.classifier import classify_intent_domain, DomainIntent
            from fastapi.responses import StreamingResponse
        except Exception:
            logger.exception("orchestrator import failed")
            raise HTTPException(500, "orchestrator module unavailable")

        history = proj.get("messages") or []
        is_platform_owner_stream = (user.get("role") or "").lower() in ("owner", "admin", "superuser")
        ctx_holder = {"ctx": None}
        _agent_token = None
        try:
            from .auth_helpers import issue_internal_agent_token  # noqa
            _agent_token = issue_internal_agent_token(user) if "issue_internal_agent_token" in dir() else None
        except Exception:
            _agent_token = None

        async def event_stream():
            try:
                # ────── CONCIERGE PRECHECK ──────
                try:
                    from .concierge_hooks import precheck_integrations, stream_wizard_as_sse
                    check = await precheck_integrations(
                        db=db, user_id=user["user_id"], project_id=pid, user_message=message,
                    )
                    if check.get("should_block_build"):
                        for evt in stream_wizard_as_sse(check):
                            yield evt
                        # Block build until creds arrive
                        import json as _j
                        yield f"event: done\ndata: {_j.dumps({'paused_for_setup': True, 'pending_integrations': [p['integration_id'] for p in check['pending']]}, ensure_ascii=False)}\n\n"
                        return
                except Exception as _ce:
                    logger.warning(f"concierge precheck failed (continuing): {_ce}")
                # ────────────────────────────────
                async for chunk in stream_via_orchestrator(
                    proj, message, history,
                    ctx_holder=ctx_holder,
                    user_language=user_language,
                    auth_token=_agent_token,
                    db=db,
                    is_owner=is_platform_owner_stream,
                    max_iterations=60,
                    inject_workflow_addendum=False,
                    force_domain=force_domain if force_domain in ("code","visual","audio","video","narrative","multi") else None,
                ):
                    yield chunk
            except Exception:
                logger.exception("orchestrator stream failed")
                import json as _json
                yield (f"event: error\n"
                       f"data: {_json.dumps({'message': 'orchestrator stream failed'}, ensure_ascii=False)}\n\n")

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    return router


async def _generate_assets_bg(db, pid: str, assets: List[Dict[str, Any]]):
    """Generate images for tagged assets via Fal.ai in background."""
    try:
        from modules.games.fal_tools import generate_flux_pro
    except Exception:
        logger.warning("fal_tools not available")
        return
    for a in assets:
        try:
            ar = "16:9" if a["type"] in ("HERO", "SECTION_BG", "GALLERY") else "1:1"
            r = await generate_flux_pro(prompt=a["prompt"], project_id=pid, aspect_ratio=ar, style_profile="cinematic")
            url = r.get("image_url") or r.get("url")
            await db.freebuild_projects.update_one(
                {"id": pid},
                {"$set": {
                    "messages.$[msg].pending_assets.$[asset].image_url": url,
                    "messages.$[msg].pending_assets.$[asset].status": "ready",
                }},
                array_filters=[
                    {"msg.pending_assets.id": a["id"]},
                    {"asset.id": a["id"]},
                ],
            )
        except Exception as e:
            logger.warning(f"asset gen failed for {a['id']}: {e}")
            await db.freebuild_projects.update_one(
                {"id": pid},
                {"$set": {"messages.$[msg].pending_assets.$[asset].status": "failed"}},
                array_filters=[
                    {"msg.pending_assets.id": a["id"]},
                    {"asset.id": a["id"]},
                ],
            )
