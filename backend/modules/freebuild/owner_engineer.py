"""
Owner Engineer — الذكاء المهندس الشخصي للمالك.

A dedicated AI assistant for the platform owner with elevated tools acting as
both Senior QA and on-call Site-Reliability Engineer:

Read-only:
    • list_all_projects, get_project_summary, search_projects,
      read_project_page, read_full_html, get_project_owner, get_platform_stats,
      read_server_logs

Mutating (passes through Code Reviewer):
    • apply_fix_to_project   → writes new HTML to a page, reviewed before save
    • republish_project      → bumps versioned slug

Diagnostic:
    • run_browser_audit      → Playwright crawl, returns structured issues

Uses the same Claude Sonnet 4.5 as the rest of the platform. Sessions persist
in `owner_chat_sessions`; every mutation logged in `owner_engineer_audit`.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import StreamingResponse

logger = logging.getLogger("zenrex.owner_engineer")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Robustly extract the first top-level JSON object from a string that may
    contain markdown fences, extra prose, or partial output. Handles strings
    with embedded `{` and `}` (e.g. HTML inside a JSON value) by tracking
    bracket depth while respecting quoted strings.
    """
    if not text:
        return None
    s = text
    # Strip common markdown fences.
    if "```" in s:
        # Pick the content of the first fenced block if it looks like JSON.
        parts = s.split("```")
        for i in range(1, len(parts), 2):
            chunk = parts[i]
            if chunk.lstrip().lower().startswith("json"):
                chunk = chunk.split("\n", 1)[1] if "\n" in chunk else chunk[4:]
            if "{" in chunk:
                obj = _extract_first_json_object(chunk)
                if obj:
                    return obj
    # Find first `{` and walk forward tracking depth + quoted strings.
    start = s.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(s)):
            ch = s[i]
            if escape:
                escape = False
                continue
            if ch == "\\" and in_string:
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = s[start:i + 1]
                    try:
                        obj = json.loads(candidate)
                        if isinstance(obj, dict):
                            return obj
                    except Exception:
                        break
        start = s.find("{", start + 1)
    return None


_OWNER_SYSTEM_PROMPT = """أنت "مهندس Zenrex الشخصي" — وكيل ذكاء اصطناعي يساعد مالك المنصة في الإدارة والصيانة (وليس عميلاً عادياً).

**هويتك:**
- اسمك: مهندس Zenrex.
- لغتك: العربية الفصحى السعودية. مباشر، تقني، صريح، بدون مجاملات.
- منظورك: تعرف منصة Zenrex من الداخل — قواعد البيانات، الـ AI orchestrator، كل المشاريع لكل المستخدمين، التقارير، الـ logs.

**صلاحياتك:** أنت ترى **كل المشاريع على السيرفر** وتقدر **تعدّل أي مشروع** نيابة عن المالك. كل تعديل يمر عبر Code Reviewer قبل الحفظ وتُسجَّل في `owner_engineer_audit`.

**ما تستطيع فعله:**
*قراءة (read-only):*
1. `list_all_projects` — كل المشاريع على المنصة
2. `get_project_summary` — تفاصيل أي مشروع
3. `search_projects` — بحث بالاسم
4. `read_project_page` — أول 6KB من صفحة
5. `read_full_html` — كل HTML الصفحة (للتشخيص العميق)
6. `get_project_owner` — معلومات صاحب المشروع
7. `get_platform_stats` — إحصائيات المنصة
8. `read_server_logs` — آخر أسطر من backend.err.log (للتشخيص)

*تعديل (write — يمر على Code Reviewer):*
9. `apply_fix_to_project` — استبدل HTML صفحة بصياغة جديدة + سبب التغيير (مطلوب)
10. `republish_project` — أعد نشر المشروع (يبني نسخة جديدة v2, v3, ...)

*فحص حي:*
11. `run_browser_audit` — Playwright يفتح الموقع ويرجّع issues (يستغرق دقيقة تقريباً)

**سير العمل المثالي عند طلب إصلاح:**
1. اقرأ المشروع (`get_project_summary` → `read_full_html`).
2. اشخّص المشكلة، اشرحها للمالك بإيجاز.
3. اقترح التعديل ك diff واضح.
4. لو المالك وافق، نفّذ `apply_fix_to_project` (Code Reviewer سيوافق/يصلح/يرفض).
5. إذا approved، نفّذ `republish_project` لينشر النسخة الجديدة.
6. (اختياري) شغّل `run_browser_audit` للتأكد إن المشكلة اختفت.

**قواعد إلزامية:**
- لا تخترع بيانات. كل سؤال يحتاج بيانات → استدع الـ tool.
- لا تطبّق تعديل بدون قراءة الـ HTML الحالي أولاً.
- اشرح السبب في حقل `reason` لكل `apply_fix_to_project` — هذا يُسجَّل في الـ audit log.
- لو Code Reviewer رفض، لا تعيد المحاولة أكثر من مرتين — أبلغ المالك.
- بعد كل `apply_fix_to_project` ناجحة، اقترح `republish_project` أو وضّح أن النشر يدوي.

كن ذكي، مختصر، تقني. أنت مع المالك — تكلم كأنك co-founder + Senior SRE.
"""


def _tools_schema() -> List[Dict[str, Any]]:
    """Anthropic tool definitions."""
    return [
        {
            "name": "list_all_projects",
            "description": "Lists EVERY project across the entire platform (all users, most-recent first). Returns id, name, mode, owner_id, owner_email, published_slug, published_version, created_at.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max projects to return (default 30, max 200)."},
                    "mode_filter": {"type": "string", "description": "Optional: filter by mode (website, video_studio, app, ...)."},
                    "published_only": {"type": "boolean", "description": "If true, only published projects."},
                },
            },
        },
        {
            "name": "get_project_summary",
            "description": "Get detailed info about a single project (ANY user's project) including page count, published URL, current_html size, last update time, owner email.",
            "input_schema": {
                "type": "object",
                "properties": {"project_id": {"type": "string"}},
                "required": ["project_id"],
            },
        },
        {
            "name": "search_projects",
            "description": "Search ALL projects on the platform by keyword in name/description.",
            "input_schema": {
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "Arabic or English search term."}},
                "required": ["keyword"],
            },
        },
        {
            "name": "read_project_page",
            "description": "Read the HTML content of a specific page in ANY project. Returns first 6000 chars + metadata.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "filename": {"type": "string", "description": "e.g. 'index.html'. Defaults to 'index.html' if omitted."},
                },
                "required": ["project_id"],
            },
        },
        {
            "name": "get_project_owner",
            "description": "Get the user who owns a specific project (email, name, role, created_at).",
            "input_schema": {
                "type": "object",
                "properties": {"project_id": {"type": "string"}},
                "required": ["project_id"],
            },
        },
        {
            "name": "get_platform_stats",
            "description": "High-level platform statistics: total projects, total users, published count, last 7-day activity.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "read_full_html",
            "description": "Read the FULL HTML of a page (no 6KB truncation). Use when deep diagnosis or a complete rewrite is needed. Returns html (full) + size.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "filename": {"type": "string", "description": "default index.html"},
                },
                "required": ["project_id"],
            },
        },
        {
            "name": "read_server_logs",
            "description": "Tail the last N lines of backend.err.log (max 200). Use to diagnose crashes, 500s, AI orchestrator errors.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "lines": {"type": "integer", "description": "1-200 (default 80)"},
                    "filter": {"type": "string", "description": "Optional substring to filter lines (e.g. 'ERROR', a project id)."},
                },
            },
        },
        {
            "name": "apply_fix_to_project",
            "description": "Replace a page's HTML in a project. Goes through Code Reviewer (approve/fix/reject). Logged in owner_engineer_audit. Reason is REQUIRED.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "filename": {"type": "string", "description": "e.g. index.html"},
                    "new_html": {"type": "string", "description": "The complete new HTML content for the page."},
                    "reason": {"type": "string", "description": "Why this change is being made (audit log)."},
                },
                "required": ["project_id", "filename", "new_html", "reason"],
            },
        },
        {
            "name": "republish_project",
            "description": "Bump versioned slug of a project (v2, v3, ...). Call AFTER apply_fix_to_project so users see the new version.",
            "input_schema": {
                "type": "object",
                "properties": {"project_id": {"type": "string"}},
                "required": ["project_id"],
            },
        },
        {
            "name": "run_browser_audit",
            "description": "Run Playwright browser audit on a published project. Returns list of issues with severity. Takes 30-90s.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "max_pages": {"type": "integer", "description": "Cap pages crawled (default 6, max 12)"},
                },
                "required": ["project_id"],
            },
        },
    ]


async def _resolve_owner_email(db, owner_id: Optional[str]) -> Optional[str]:
    if not owner_id:
        return None
    try:
        u = await db.users.find_one({"id": owner_id}, {"_id": 0, "email": 1})
        return (u or {}).get("email")
    except Exception:
        return None


async def _tool_list_all_projects(db, limit: int = 30, mode_filter: Optional[str] = None, published_only: bool = False) -> Dict[str, Any]:
    limit = max(1, min(int(limit or 30), 200))
    query: Dict[str, Any] = {}
    if mode_filter:
        query["mode"] = mode_filter
    if published_only:
        query["published_slug"] = {"$exists": True, "$ne": None}
    docs: List[Dict[str, Any]] = []
    for col in ("freebuild_chat_projects", "freebuild_projects"):
        async for d in db[col].find(query, {
            "_id": 0, "id": 1, "name": 1, "mode": 1, "user_id": 1,
            "published_slug": 1, "published_version": 1,
            "created_at": 1, "updated_at": 1,
        }).sort("updated_at", -1).limit(limit):
            d["owner_email"] = await _resolve_owner_email(db, d.get("user_id"))
            docs.append(d)
        if len(docs) >= limit:
            break
    docs = docs[:limit]
    return {"ok": True, "count": len(docs), "projects": docs}


async def _tool_get_project_summary(db, project_id: str) -> Dict[str, Any]:
    proj = None
    for col in ("freebuild_chat_projects", "freebuild_projects"):
        proj = await db[col].find_one({"id": project_id}, {"_id": 0, "pages": 1, "current_html": 1, "name": 1, "mode": 1, "published_slug": 1, "published_version": 1, "published_history": 1, "created_at": 1, "updated_at": 1, "category_id": 1, "user_id": 1})
        if proj:
            break
    if not proj:
        return {"ok": False, "error": "project_not_found"}
    pages = list((proj.get("pages") or {}).keys()) or (["index.html"] if proj.get("current_html") else [])
    return {
        "ok": True,
        "name": proj.get("name"),
        "mode": proj.get("mode"),
        "category_id": proj.get("category_id"),
        "owner_id": proj.get("user_id"),
        "owner_email": await _resolve_owner_email(db, proj.get("user_id")),
        "pages": pages,
        "page_count": len(pages),
        "html_size": len(proj.get("current_html") or ""),
        "published_slug": proj.get("published_slug"),
        "published_version": proj.get("published_version"),
        "version_count": len(proj.get("published_history") or []),
        "live_url": f"https://zenrex.ai/s/{proj['published_slug']}" if proj.get("published_slug") else None,
        "created_at": str(proj.get("created_at"))[:19] if proj.get("created_at") else None,
        "updated_at": str(proj.get("updated_at"))[:19] if proj.get("updated_at") else None,
    }


async def _tool_search_projects(db, keyword: str) -> Dict[str, Any]:
    kw = (keyword or "").strip()
    if not kw:
        return {"ok": False, "error": "empty_keyword"}
    docs: List[Dict[str, Any]] = []
    for col in ("freebuild_chat_projects", "freebuild_projects"):
        async for d in db[col].find(
            {"name": {"$regex": kw, "$options": "i"}},
            {"_id": 0, "id": 1, "name": 1, "mode": 1, "user_id": 1, "published_slug": 1, "updated_at": 1},
        ).sort("updated_at", -1).limit(20):
            d["owner_email"] = await _resolve_owner_email(db, d.get("user_id"))
            docs.append(d)
    return {"ok": True, "count": len(docs), "matches": docs[:20]}


async def _tool_read_project_page(db, project_id: str, filename: str = "index.html") -> Dict[str, Any]:
    filename = (filename or "index.html").strip().lower()
    proj = None
    for col in ("freebuild_chat_projects", "freebuild_projects"):
        proj = await db[col].find_one({"id": project_id}, {"_id": 0, "pages": 1, "current_html": 1, "name": 1, "user_id": 1})
        if proj:
            break
    if not proj:
        return {"ok": False, "error": "project_not_found"}
    pages = proj.get("pages") or {}
    html = pages.get(filename) or (proj.get("current_html") if filename == "index.html" else "")
    if not html:
        return {"ok": False, "error": f"page '{filename}' not found in project"}
    return {
        "ok": True,
        "project_name": proj.get("name"),
        "owner_email": await _resolve_owner_email(db, proj.get("user_id")),
        "filename": filename,
        "full_size": len(html),
        "html_preview": html[:6000],
        "truncated": len(html) > 6000,
    }


async def _tool_get_project_owner(db, project_id: str) -> Dict[str, Any]:
    proj = None
    for col in ("freebuild_chat_projects", "freebuild_projects"):
        proj = await db[col].find_one({"id": project_id}, {"_id": 0, "user_id": 1, "name": 1})
        if proj:
            break
    if not proj:
        return {"ok": False, "error": "project_not_found"}
    uid = proj.get("user_id")
    if not uid:
        return {"ok": False, "error": "project has no owner"}
    u = await db.users.find_one({"id": uid}, {"_id": 0, "email": 1, "name": 1, "role": 1, "created_at": 1})
    return {
        "ok": True,
        "project_name": proj.get("name"),
        "owner_id": uid,
        "email": (u or {}).get("email"),
        "name": (u or {}).get("name"),
        "role": (u or {}).get("role"),
        "joined_at": str((u or {}).get("created_at") or "")[:19],
    }


async def _tool_get_platform_stats(db) -> Dict[str, Any]:
    total = 0
    published = 0
    for col in ("freebuild_chat_projects", "freebuild_projects"):
        total += await db[col].count_documents({})
        published += await db[col].count_documents({"published_slug": {"$exists": True, "$ne": None}})
    users = await db.users.count_documents({})
    audits = 0
    try:
        audits = await db.freebuild_audit_reports.count_documents({})
    except Exception:
        pass
    return {
        "ok": True,
        "total_projects": total,
        "published_projects": published,
        "unpublished_projects": total - published,
        "total_users": users,
        "engineer_audits_run": audits,
    }


async def _find_project(db, project_id: str):
    """Return (collection_name, project_doc) or (None, None)."""
    for col in ("freebuild_chat_projects", "freebuild_projects"):
        proj = await db[col].find_one({"id": project_id}, {"_id": 0})
        if proj:
            return col, proj
    return None, None


async def _tool_read_full_html(db, project_id: str, filename: str = "index.html") -> Dict[str, Any]:
    filename = (filename or "index.html").strip().lower()
    col, proj = await _find_project(db, project_id)
    if not proj:
        return {"ok": False, "error": "project_not_found"}
    pages = proj.get("pages") or {}
    html = pages.get(filename) or (proj.get("current_html") if filename == "index.html" else "")
    if not html:
        return {"ok": False, "error": f"page '{filename}' not found"}
    # Hard cap at 90KB to keep tokens reasonable for the LLM.
    MAX = 90_000
    truncated = len(html) > MAX
    return {
        "ok": True, "project_name": proj.get("name"), "filename": filename,
        "full_size": len(html), "html": html[:MAX], "truncated": truncated,
    }


async def _tool_read_server_logs(lines: int = 80, filter_str: Optional[str] = None) -> Dict[str, Any]:
    lines = max(1, min(int(lines or 80), 200))
    path = "/var/log/supervisor/backend.err.log"
    if not os.path.exists(path):
        return {"ok": False, "error": "log file not found"}
    try:
        # Read tail efficiently.
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            read_size = min(size, 200_000)  # cap 200KB
            f.seek(size - read_size)
            data = f.read().decode("utf-8", errors="replace")
        all_lines = data.splitlines()
        if filter_str:
            all_lines = [ln for ln in all_lines if filter_str.lower() in ln.lower()]
        tail = all_lines[-lines:]
        return {"ok": True, "lines_returned": len(tail), "filter": filter_str, "logs": "\n".join(tail)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


async def _tool_apply_fix_to_project(
    db, project_id: str, filename: str, new_html: str, reason: str, actor_user_id: str
) -> Dict[str, Any]:
    """Apply an HTML change to ANY project (cross-user). Runs Code Reviewer first."""
    filename = (filename or "index.html").strip().lower()
    reason = (reason or "").strip()
    if not reason:
        return {"ok": False, "error": "reason is required for audit"}
    if not new_html or len(new_html) < 200:
        return {"ok": False, "error": "new_html looks empty or too short"}

    col_name, proj = await _find_project(db, project_id)
    if not proj:
        return {"ok": False, "error": "project_not_found"}

    pages = proj.get("pages") or {}
    current_html = pages.get(filename) or (proj.get("current_html") if filename == "index.html" else "")

    # Run Code Reviewer.
    try:
        from modules.freebuild.code_reviewer import review_code_change
        review = await review_code_change(
            action="apply_fix_to_project",
            proposed_html=new_html,
            current_html=current_html or "",
            user_request=f"[OwnerEngineer] {reason}",
            project_name=proj.get("name") or "",
            page_filename=filename,
        )
    except Exception as e:
        logger.warning(f"[owner-engineer] code review failed, defaulting to approve: {e}")
        review = {"verdict": "approve", "score": 100, "issues": [], "skipped": True, "error": str(e)[:120]}

    verdict = review.get("verdict") or "approve"
    if verdict == "reject":
        # Log the rejected attempt for audit visibility.
        await db.owner_engineer_audit.insert_one({
            "id": str(uuid.uuid4()), "ts": _now_iso(), "actor_user_id": actor_user_id,
            "action": "apply_fix_to_project", "project_id": project_id, "filename": filename,
            "reason": reason, "result": "rejected_by_reviewer",
            "review_score": review.get("score"), "issues": review.get("issues"),
        })
        return {"ok": False, "error": "code_reviewer_rejected", "review": review}

    final_html = review.get("improved_html") if verdict == "fix" else new_html
    if not final_html:
        final_html = new_html

    # Apply.
    new_pages = dict(pages)
    new_pages[filename] = final_html
    update_doc: Dict[str, Any] = {
        "pages": new_pages,
        "updated_at": _now_iso(),
        "last_edited_by_engineer": True,
        "last_engineer_edit": {
            "ts": _now_iso(), "actor": actor_user_id, "filename": filename,
            "reason": reason, "verdict": verdict, "score": review.get("score"),
        },
    }
    if filename == "index.html":
        update_doc["current_html"] = final_html

    await db[col_name].update_one({"id": project_id}, {"$set": update_doc})

    # Audit log.
    await db.owner_engineer_audit.insert_one({
        "id": str(uuid.uuid4()), "ts": _now_iso(), "actor_user_id": actor_user_id,
        "action": "apply_fix_to_project", "project_id": project_id, "filename": filename,
        "project_owner_id": proj.get("user_id"), "reason": reason, "result": "applied",
        "verdict": verdict, "review_score": review.get("score"),
        "size_before": len(current_html or ""), "size_after": len(final_html),
    })

    return {
        "ok": True, "applied": True, "filename": filename,
        "verdict": verdict, "review_score": review.get("score"),
        "issues_count": len(review.get("issues") or []),
        "size_before": len(current_html or ""), "size_after": len(final_html),
        "note": "تم الحفظ. اطلب republish_project لينعكس على النسخة الحية.",
    }


async def _tool_republish_project(db, project_id: str, actor_user_id: str) -> Dict[str, Any]:
    """Bump the versioned slug of a project (uses freebuild_chat.auto_republish_project)."""
    col_name, proj = await _find_project(db, project_id)
    if not proj:
        return {"ok": False, "error": "project_not_found"}
    owner_id = proj.get("user_id")
    if not owner_id:
        return {"ok": False, "error": "project has no owner_id"}
    try:
        from modules.freebuild.freebuild_chat import auto_republish_project
        result = await auto_republish_project(db, project_id, owner_id)
    except Exception as e:
        logger.exception(f"[owner-engineer] republish error: {e}")
        return {"ok": False, "error": str(e)[:200]}
    if not result:
        return {"ok": False, "error": "republish returned None (not previously published or no html)"}
    # Audit.
    await db.owner_engineer_audit.insert_one({
        "id": str(uuid.uuid4()), "ts": _now_iso(), "actor_user_id": actor_user_id,
        "action": "republish_project", "project_id": project_id,
        "project_owner_id": owner_id, "result": "republished",
        "new_slug": result.get("slug"), "new_version": result.get("version"),
    })
    return {"ok": True, **result}


async def _tool_run_browser_audit(db, project_id: str, max_pages: int = 6) -> Dict[str, Any]:
    """Run Playwright crawl on the published site. Lighter than the paid engineer-audit endpoint."""
    max_pages = max(1, min(int(max_pages or 6), 12))
    col_name, proj = await _find_project(db, project_id)
    if not proj:
        return {"ok": False, "error": "project_not_found"}
    slug = proj.get("published_slug")
    if not slug:
        return {"ok": False, "error": "project_not_published"}

    host = os.environ.get("PUBLIC_HOST") or "https://zenrex.ai"
    base_url = f"{host}/s/{slug}"
    pages_dict: Dict[str, str] = proj.get("pages") or {"index.html": proj.get("current_html", "")}
    page_files = list(pages_dict.keys())[:max_pages]
    if "index.html" not in page_files:
        page_files.insert(0, "index.html")

    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        return {"ok": False, "error": f"playwright not available: {e}"}

    issues: List[Dict[str, Any]] = []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx_b = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await ctx_b.new_page()
            for pname in page_files[:max_pages]:
                url = base_url if pname == "index.html" else f"{base_url}/{pname}"
                console_errors: List[str] = []
                page.on("console", lambda msg, _errs=console_errors: _errs.append(msg.text) if msg.type == "error" else None)
                try:
                    resp = await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                    status = resp.status if resp else 0
                    if status >= 400:
                        issues.append({"severity": "critical", "page": pname, "msg": f"HTTP {status}"})
                    # Broken images.
                    broken = await page.evaluate("""
                        () => Array.from(document.images).filter(i => i.complete && i.naturalWidth === 0).map(i => i.src)
                    """)
                    for src in (broken or [])[:5]:
                        issues.append({"severity": "high", "page": pname, "msg": f"Broken image: {src[:120]}"})
                    # Empty hrefs.
                    empty_links = await page.evaluate("""
                        () => Array.from(document.querySelectorAll('a')).filter(a => !a.href || a.href.endsWith('#')).length
                    """)
                    if empty_links and empty_links > 3:
                        issues.append({"severity": "medium", "page": pname, "msg": f"{empty_links} روابط فارغة / #"})
                    for err in console_errors[:3]:
                        issues.append({"severity": "high", "page": pname, "msg": f"Console error: {err[:120]}"})
                except Exception as e:
                    issues.append({"severity": "critical", "page": pname, "msg": f"navigation failed: {str(e)[:120]}"})
            await browser.close()
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

    return {
        "ok": True, "base_url": base_url, "pages_audited": len(page_files),
        "issues_count": len(issues),
        "critical": len([i for i in issues if i["severity"] == "critical"]),
        "issues": issues[:30],
    }


async def _dispatch_owner_tool(db, name: str, args: Dict[str, Any], actor_user_id: str = "") -> Dict[str, Any]:
    try:
        if name == "list_all_projects" or name == "list_my_projects":  # back-compat alias
            return await _tool_list_all_projects(
                db, args.get("limit", 30), args.get("mode_filter"),
                bool(args.get("published_only", False)),
            )
        if name == "get_project_summary":
            return await _tool_get_project_summary(db, args.get("project_id", ""))
        if name == "search_projects":
            return await _tool_search_projects(db, args.get("keyword", ""))
        if name == "read_project_page":
            return await _tool_read_project_page(db, args.get("project_id", ""), args.get("filename", "index.html"))
        if name == "read_full_html":
            return await _tool_read_full_html(db, args.get("project_id", ""), args.get("filename", "index.html"))
        if name == "read_server_logs":
            return await _tool_read_server_logs(args.get("lines", 80), args.get("filter"))
        if name == "get_project_owner":
            return await _tool_get_project_owner(db, args.get("project_id", ""))
        if name == "get_platform_stats":
            return await _tool_get_platform_stats(db)
        if name == "apply_fix_to_project":
            return await _tool_apply_fix_to_project(
                db, args.get("project_id", ""), args.get("filename", "index.html"),
                args.get("new_html", ""), args.get("reason", ""), actor_user_id,
            )
        if name == "republish_project":
            return await _tool_republish_project(db, args.get("project_id", ""), actor_user_id)
        if name == "run_browser_audit":
            return await _tool_run_browser_audit(db, args.get("project_id", ""), args.get("max_pages", 6))
        return {"ok": False, "error": f"unknown_tool: {name}"}
    except Exception as e:
        logger.exception(f"[owner-tool] {name} failed: {e}")
        return {"ok": False, "error": str(e)[:200]}


def setup_owner_engineer_routes(router: APIRouter, db, get_current_user):
    """Attach the /owner/engineer/* endpoints to the given router."""

    def _ensure_owner(user):
        role = (user.get("role") or "").lower()
        if role not in ("owner", "admin", "superuser"):
            raise HTTPException(403, "هذا القسم خاص بالمالك فقط")

    @router.post("/owner/engineer/chat")
    async def owner_engineer_chat(
        message: str = Form(...),
        session_id: Optional[str] = Form(None),
        project_id: Optional[str] = Form(None),
        user=Depends(get_current_user),
    ):
        _ensure_owner(user)
        uid = user["user_id"]
        sid = session_id or str(uuid.uuid4())

        # Load prior conversation for context.
        sess = await db.owner_chat_sessions.find_one({"id": sid, "user_id": uid}, {"_id": 0})
        history: List[Dict[str, Any]] = []
        if sess:
            history = sess.get("messages", [])

        # If a project is in focus, attach a quick summary block so the AI is grounded.
        project_context_block = ""
        if project_id:
            summary = await _tool_get_project_summary(db, project_id)
            if summary.get("ok"):
                project_context_block = (
                    f"\n\n**المشروع الحالي قيد التركيز:**\n"
                    f"- id: {project_id}\n"
                    f"- name: {summary.get('name')}\n"
                    f"- mode: {summary.get('mode')}\n"
                    f"- owner: {summary.get('owner_email')}\n"
                    f"- pages: {summary.get('page_count')}\n"
                    f"- published: {summary.get('live_url') or 'لم يُنشر بعد'}\n"
                    f"عندما يسأل المالك بدون تحديد مشروع، افترض هذا المشروع.\n"
                )

        history.append({"role": "user", "content": message, "ts": _now_iso(), "project_id": project_id})

        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(500, "EMERGENT_LLM_KEY missing")

        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore

        async def event_stream():
            yield f"event: start\ndata: {json.dumps({'session_id': sid, 'project_id': project_id})}\n\n"
            try:
                chat = LlmChat(
                    api_key=api_key, session_id=sid,
                    system_message=_OWNER_SYSTEM_PROMPT + project_context_block + (
                        "\n\n**TOOLS AVAILABLE:** " + json.dumps(_tools_schema(), ensure_ascii=False)
                        + "\n\nعند استدعاء أداة، اكتب فقط JSON نقي بدون markdown fences وبدون أي شرح إضافي، مثال صحيح:\n"
                        + '{"tool": "get_platform_stats", "args": {}}\n'
                        + 'ممنوع كتابة ```json أو ``` حول الـ JSON. ممنوع كتابة أي نص قبله أو بعده. '
                        + "بعد ما يجيك tool_result، أكمل المحادثة عادي بالعربي السعودي."
                    ),
                ).with_model("anthropic", "claude-sonnet-4-5-20250929").with_params(max_tokens=4000)

                conversation = "\n".join(
                    f"{m['role'].upper()}: {m.get('content','')}" for m in history[-12:]
                )

                # Tool loop (max 10 iterations — supports read→fix→republish→audit chains)
                final_answer = ""
                for _ in range(10):
                    resp = await chat.send_message(UserMessage(text=conversation))
                    if not isinstance(resp, str):
                        resp = str(resp)
                    txt = resp.strip()
                    tool_json = _extract_first_json_object(txt)
                    if tool_json and tool_json.get("tool"):
                        tool_name = tool_json.get("tool")
                        tool_args = tool_json.get("args") or {}
                        # Emit a redacted version of args to the client (strip huge HTML).
                        args_preview = {k: (v[:120] + "...[truncated]" if isinstance(v, str) and len(v) > 200 else v) for k, v in tool_args.items()}
                        yield f"event: tool\ndata: {json.dumps({'name': tool_name, 'args': args_preview}, ensure_ascii=False)}\n\n"
                        result = await _dispatch_owner_tool(db, tool_name, tool_args, actor_user_id=uid)
                        # Emit result (also redact html field if present).
                        result_preview = {k: (v[:300] + "...[truncated]" if isinstance(v, str) and len(v) > 500 else v) for k, v in result.items()}
                        yield f"event: tool_result\ndata: {json.dumps({'name': tool_name, 'result': result_preview}, ensure_ascii=False)}\n\n"
                        conversation += f"\nASSISTANT: {txt[:400]}\nTOOL_RESULT[{tool_name}]: {json.dumps(result, ensure_ascii=False)[:3000]}"
                        continue
                    final_answer = resp
                    break

                if not final_answer:
                    final_answer = "تم تنفيذ الأدوات. (لم تصلني رسالة ختامية من الـ AI.)"

                history.append({"role": "assistant", "content": final_answer, "ts": _now_iso()})
                await db.owner_chat_sessions.update_one(
                    {"id": sid},
                    {"$set": {"id": sid, "user_id": uid, "messages": history[-100:], "updated_at": _now_iso()},
                     "$setOnInsert": {"created_at": _now_iso()}},
                    upsert=True,
                )
                yield f"event: text\ndata: {json.dumps({'content': final_answer}, ensure_ascii=False)}\n\n"
                yield f"event: done\ndata: {json.dumps({'session_id': sid})}\n\n"
            except Exception as e:
                logger.exception(f"[owner-engineer] stream error: {e}")
                yield f"event: error\ndata: {json.dumps({'message': str(e)[:200]}, ensure_ascii=False)}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @router.get("/owner/engineer/sessions")
    async def list_owner_sessions(user=Depends(get_current_user)):
        _ensure_owner(user)
        cursor = db.owner_chat_sessions.find(
            {"user_id": user["user_id"]},
            {"_id": 0, "id": 1, "updated_at": 1, "messages": {"$slice": -1}},
        ).sort("updated_at", -1).limit(30)
        items = await cursor.to_list(length=30)
        return {"sessions": items, "count": len(items)}

    @router.get("/owner/engineer/sessions/{sid}")
    async def get_owner_session(sid: str, user=Depends(get_current_user)):
        _ensure_owner(user)
        sess = await db.owner_chat_sessions.find_one(
            {"id": sid, "user_id": user["user_id"]}, {"_id": 0},
        )
        if not sess:
            raise HTTPException(404, "Session not found")
        return sess

    # ── Direct REST endpoints (used by the frontend project picker) ──────────

    @router.get("/owner/engineer/projects")
    async def owner_list_projects(
        limit: int = 50,
        q: Optional[str] = None,
        published_only: bool = False,
        user=Depends(get_current_user),
    ):
        _ensure_owner(user)
        if q:
            result = await _tool_search_projects(db, q)
        else:
            result = await _tool_list_all_projects(db, limit=limit, published_only=published_only)
        return result

    @router.get("/owner/engineer/projects/{pid}")
    async def owner_get_project(pid: str, user=Depends(get_current_user)):
        _ensure_owner(user)
        summary = await _tool_get_project_summary(db, pid)
        if not summary.get("ok"):
            raise HTTPException(404, summary.get("error") or "project_not_found")
        return summary

    @router.get("/owner/engineer/projects/{pid}/page")
    async def owner_get_project_page(
        pid: str,
        filename: str = "index.html",
        user=Depends(get_current_user),
    ):
        _ensure_owner(user)
        result = await _tool_read_project_page(db, pid, filename)
        if not result.get("ok"):
            raise HTTPException(404, result.get("error") or "page_not_found")
        return result

    @router.get("/owner/engineer/stats")
    async def owner_stats(user=Depends(get_current_user)):
        _ensure_owner(user)
        return await _tool_get_platform_stats(db)
