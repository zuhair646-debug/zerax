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


_OWNER_SYSTEM_PROMPT = """أنت "مهندس Zenrex الداخلي" — وكيل ذكاء اصطناعي خاص بمالك المنصة فقط.

**هويتك:**
- اسمك: مهندس Zenrex الداخلي.
- مالكك الوحيد: محمد (مالك Zenrex). أنت لا تتعامل مع عملاء أبداً.
- لغتك: العربية السعودية الفصحى. مباشر، تقني، حازم، صريح، بدون مجاملات أو رموز إيموجي زائدة.
- منظورك: ترى منصة Zenrex من الداخل — DB، AI orchestrator، كل المشاريع، التقارير، الـ logs.

**حدودك الأمنية الإلزامية (لا تنتهكها أبداً):**
- ❌ ممنوع تعديل كود `zenrex.ai` الإنتاجي (الـ repo).
- ❌ ممنوع التحدث مع أي عميل أو نشر شي علني.
- ❌ ممنوع تعديل مشروع عميل ما لم يطلب المالك ذلك صراحةً + يذكر PID.
- ❌ ممنوع كتابة ملفات على disk دون أمر مباشر.
- ✅ مسموح: قراءة بيانات Zenrex DB، التحليل، اقتراح patches للـ system prompts برمجياً، عزل أقسام عبر Maintenance Mode، تدخل محدد في مشاريع عميل بأمر صريح من المالك.

**مهمتك الأساسية (ركّز عليها دائماً):**
1. **مراقبة الذكاء الصناعي البنّاء** (freebuild_agent) — هل يصير عنده أخطاء متكررة؟ هل يعلق؟ هل يدمّر تصاميم؟
2. **إعطاء تقارير دورية للمالك** عند الطلب — تقرير اليوم، الأخطاء المتكررة، حالة الصحة.
3. **اقتراح تصحيحات برمجية** للذكاء الصناعي البنّاء عبر `propose_system_prompt_patch` (المالك يراجع ويوافق).
4. **عزل أقسام للصيانة** لما تسوي تعديل، عبر `enter_maintenance_mode` (الأقسام: صور، فيديو، ألعاب، global) — بدون ما يتعطل باقي الموقع.
5. **تدخل محدود ومدروس** في مشروع عميل لو المالك طلب — صحح، وثبّت، وارجّع الـ AI البنّاء يكمل عبر `resume_project_ai`.

**ما تستطيع فعله (كل أدواتك):**
*قراءة:*
- list_all_projects, get_project_summary, search_projects, read_project_page,
  read_full_html, get_project_owner, get_platform_stats, read_server_logs

*تحليل ميداني (الأهم لمهمتك):*
- get_daily_report — تقرير شامل لآخر N ساعة
- analyze_ai_errors — يدوّر على أخطاء متكررة من الـ AI البنّاء
- list_pending_patches — قائمة اقتراحات الإصلاح المعلقة
- list_maintenance_modes — حالة الصيانة الحالية

*تحكم (يلزم أمر صريح من المالك):*
- propose_system_prompt_patch — يحفظ اقتراح إصلاح للذكاء الصناعي (لا يطبّق تلقائياً)
- enter_maintenance_mode / exit_maintenance_mode — عزل قسم أو إعادته
- apply_fix_to_project — تعديل صفحة في مشروع عميل (يمر عبر Code Reviewer)
- republish_project — نشر نسخة جديدة
- resume_project_ai — حقن رسالة في شات مشروع لإعادة تشغيل الـ AI البنّاء

*فحص حي:*
- run_browser_audit — Playwright يفتح موقع منشور ويرجّع issues

**سير العمل المثالي للحالات الشائعة:**

🅰️ المالك يقول "أعطني تقرير اليوم":
→ get_daily_report(24) → اعرض ملخصاً منظّماً (مشاريع، أخطاء، صيانة، patches، credits).

🅱️ المالك يقول "ليش الـ AI يكرر نفس الخطأ؟":
→ analyze_ai_errors(24) → اعرض الأنماط مع التوصيات → إن وجدت سبباً واضحاً، استخدم
  propose_system_prompt_patch لاقتراح إصلاح.

🅲️ المالك يقول "ادخل مشروع <PID> صحح <X> ورجّع الـ AI يكمل":
→ get_project_summary → read_full_html → اشخّص → apply_fix_to_project (مع reason واضح) →
  republish_project → resume_project_ai برسالة مختصرة للـ AI البنّاء يكمل.

🅳️ المالك يقول "اوقف قسم الفيديوهات نص ساعة عشان أحدّث":
→ enter_maintenance_mode("videos", 30, "...") → اعرض مدة الإيقاف ووقت العودة.

**قواعد إلزامية:**
- لا تخترع بيانات. كل سؤال يحتاج بيانات → استدع الـ tool.
- كل اقتراح تصحيح للذكاء الصناعي يجب أن يكون مرتكزاً على `observation` ميداني فعلي
  (من analyze_ai_errors أو get_daily_report).
- لو المالك ما حدد PID صراحةً، لا تتدخل في مشروع.
- بعد تدخّل في مشروع، **استخدم resume_project_ai** برسالة موجزة للـ AI البنّاء — لا تترك المشروع
  ميتاً.
- كن مختصر وحاد. أنت أداة عمل، لست chatbot ودود.

أنت مع مالك المنصة. تكلم كأنك CTO + Senior SRE — حاد، عملي، بدون حشو.
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
        # 🆕 Owner-Engineer specialized tools.
        {
            "name": "get_daily_report",
            "description": "Comprehensive ops report for the owner: new + published projects, engineer summons, tool failures, active maintenance, pending patches, credits used.",
            "input_schema": {"type": "object", "properties": {
                "hours": {"type": "integer", "description": "Lookback window in hours (1..168, default 24)."},
            }},
        },
        {
            "name": "analyze_ai_errors",
            "description": "Scans recent chat sessions for repeated AI failure patterns (announce-and-stop, placeholder leaks, tool loops, code-reviewer rejections) and gives recommendations.",
            "input_schema": {"type": "object", "properties": {
                "period_hours": {"type": "integer", "description": "Lookback window (default 24)."},
                "min_repeats": {"type": "integer", "description": "Minimum occurrences to flag (default 2)."},
            }},
        },
        {
            "name": "propose_system_prompt_patch",
            "description": "Save a proposal to amend an AI system prompt (e.g. freebuild_agent). Owner reviews + applies manually — this tool does NOT auto-edit files.",
            "input_schema": {"type": "object", "properties": {
                "observation": {"type": "string", "description": "What you noticed wrong with the AI's behavior."},
                "suggested_change": {"type": "string", "description": "Exact rewrite or addition to the system prompt."},
                "rationale": {"type": "string", "description": "Why this change should help."},
                "target": {"type": "string", "description": "Which AI to patch (default freebuild_agent)."},
            }, "required": ["observation", "suggested_change"]},
        },
        {
            "name": "list_pending_patches",
            "description": "List pending system-prompt patch proposals awaiting the owner's review.",
            "input_schema": {"type": "object", "properties": {"limit": {"type": "integer"}}},
        },
        {
            "name": "enter_maintenance_mode",
            "description": "Activate maintenance for one section (images/videos/games/global) for N minutes. The middleware returns 503 + a friendly Arabic banner on matching API paths. Other sections stay live.",
            "input_schema": {"type": "object", "properties": {
                "section": {"type": "string", "description": "One of: images, videos, games, global"},
                "duration_minutes": {"type": "integer", "description": "5..1440 (default 30)"},
                "banner_ar": {"type": "string", "description": "Optional custom Arabic banner."},
            }, "required": ["section"]},
        },
        {
            "name": "exit_maintenance_mode",
            "description": "End maintenance for a section immediately.",
            "input_schema": {"type": "object", "properties": {
                "section": {"type": "string"},
            }, "required": ["section"]},
        },
        {
            "name": "list_maintenance_modes",
            "description": "List all maintenance entries (active + ended) for the dashboard.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "resume_project_ai",
            "description": "Inject a 'مهندس Zenrex الداخلي' note into a specific project's chat session so the building AI sees it on the next turn and resumes work after the owner intervened.",
            "input_schema": {"type": "object", "properties": {
                "project_id": {"type": "string"},
                "message": {"type": "string", "description": "Arabic note for the building AI (≤ 1000 chars)."},
            }, "required": ["project_id", "message"]},
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
    """Tail backend logs from whichever source is available.

    Production (zenrex.ai) runs via Docker → use `docker logs`.
    Preview env runs via supervisor → tail the log file.
    """
    import asyncio as _asyncio
    lines = max(1, min(int(lines or 80), 200))
    sources_tried: List[str] = []

    # 1) Supervisor log file (preview env) + in-container file mirror (prod).
    candidates = [
        "/var/log/supervisor/backend.err.log",
        "/var/log/supervisor/backend.out.log",
        "/tmp/backend.log",  # In-container mirror (configured in server.py startup)
        "/app/logs/backend.log",
    ]
    for path in candidates:
        sources_tried.append(path)
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    f.seek(0, 2)
                    size = f.tell()
                    read_size = min(size, 250_000)
                    f.seek(size - read_size)
                    data = f.read().decode("utf-8", errors="replace")
                all_lines = data.splitlines()
                if filter_str:
                    all_lines = [ln for ln in all_lines if filter_str.lower() in ln.lower()]
                tail = all_lines[-lines:]
                return {
                    "ok": True, "source": path, "lines_returned": len(tail),
                    "filter": filter_str, "logs": "\n".join(tail),
                }
            except Exception as e:
                sources_tried.append(f"{path}:ERROR:{e}")

    # 2) Docker container logs (production VPS).
    for container in ("zerax-backend", "zenrex-backend", "backend"):
        sources_tried.append(f"docker:{container}")
        try:
            proc = await _asyncio.create_subprocess_exec(
                "docker", "logs", "--tail", str(min(lines * 4, 600)), container,
                stdout=_asyncio.subprocess.PIPE, stderr=_asyncio.subprocess.STDOUT,
            )
            out, _ = await _asyncio.wait_for(proc.communicate(), timeout=10)
            if proc.returncode == 0 and out:
                txt = out.decode("utf-8", errors="replace")
                all_lines = txt.splitlines()
                if filter_str:
                    all_lines = [ln for ln in all_lines if filter_str.lower() in ln.lower()]
                tail = all_lines[-lines:]
                return {
                    "ok": True, "source": f"docker:{container}",
                    "lines_returned": len(tail), "filter": filter_str,
                    "logs": "\n".join(tail),
                }
        except FileNotFoundError:
            # docker not installed on this host
            break
        except Exception as e:
            sources_tried.append(f"docker:{container}:ERROR:{str(e)[:80]}")

    return {
        "ok": False,
        "error": "no log source available",
        "sources_tried": sources_tried,
    }


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


# ─────────────────────────────────────────────────────────────────────
# 🆕 Daily Report — comprehensive snapshot of the last N hours.
# ─────────────────────────────────────────────────────────────────────
async def _tool_get_daily_report(db, hours: int = 24) -> Dict[str, Any]:
    """Comprehensive ops report for the owner: projects, AI behavior, errors, credits."""
    from datetime import timedelta as _td
    hours = max(1, min(int(hours or 24), 168))  # 1h..7d
    since = (datetime.now(timezone.utc) - _td(hours=hours))
    since_iso = since.isoformat()

    # Projects created / published in window.
    projects_total = await db.freebuild_projects.count_documents({}) if hasattr(db.freebuild_projects, "count_documents") else 0
    projects_new = await db.freebuild_projects.count_documents({"created_at": {"$gte": since_iso}})
    projects_published_today = await db.freebuild_projects.count_documents(
        {"published_at": {"$gte": since_iso}}
    )

    # Recent published projects (top 10 newest).
    recent_pub_cursor = db.freebuild_projects.find(
        {"published_at": {"$gte": since_iso}},
        {"_id": 0, "id": 1, "name": 1, "user_id": 1, "published_slug": 1,
         "published_version": 1, "published_at": 1, "mode": 1},
    ).sort("published_at", -1).limit(10)
    recent_pub = [doc async for doc in recent_pub_cursor]
    for p in recent_pub:
        p["owner_email"] = await _resolve_owner_email(db, p.get("user_id"))

    # Engineer summons (when the AI ASKED for help itself — a sign of trouble).
    engineer_summons_count = 0
    try:
        engineer_summons_count = await db.engineer_summon_log.count_documents(
            {"created_at": {"$gte": since_iso}}
        )
    except Exception:
        engineer_summons_count = 0

    # Tool failures in the window (scan recent chat sessions for tool_result errors).
    tool_failure_samples: List[Dict[str, Any]] = []
    try:
        sess_cursor = db.freebuild_chat_sessions.find(
            {"updated_at": {"$gte": since_iso}},
            {"_id": 0, "project_id": 1, "messages": 1, "updated_at": 1},
        ).sort("updated_at", -1).limit(50)
        async for s in sess_cursor:
            for m in (s.get("messages") or [])[-30:]:
                content = m.get("content") or ""
                if isinstance(content, str) and ("ERROR" in content or "error" in content.lower()) and len(tool_failure_samples) < 10:
                    tool_failure_samples.append({
                        "project_id": s.get("project_id"),
                        "snippet": content[:160],
                        "when": m.get("ts") or s.get("updated_at"),
                    })
    except Exception:
        pass

    # Active maintenance modes.
    maint_active = []
    try:
        async for m in db.zenrex_maintenance.find(
            {"active": True},
            {"_id": 0, "section": 1, "banner_ar": 1, "ends_at": 1, "started_at": 1, "user_id": 1},
        ):
            maint_active.append(m)
    except Exception:
        pass

    # Pending system-prompt patches awaiting owner approval.
    pending_patches = 0
    try:
        pending_patches = await db.engineer_patch_proposals.count_documents({"status": "pending"})
    except Exception:
        pending_patches = 0

    # Credits used (best-effort — table may not exist on dev).
    credits_used = None
    try:
        cursor = db.credits_ledger.aggregate([
            {"$match": {"created_at": {"$gte": since_iso}, "delta": {"$lt": 0}}},
            {"$group": {"_id": None, "total": {"$sum": "$delta"}}},
        ])
        async for row in cursor:
            credits_used = abs(row.get("total") or 0)
            break
    except Exception:
        credits_used = None

    return {
        "ok": True,
        "window_hours": hours,
        "since": since_iso,
        "projects_total_all_time": projects_total,
        "projects_created_in_window": projects_new,
        "projects_published_in_window": projects_published_today,
        "recent_published": recent_pub,
        "engineer_summons_in_window": engineer_summons_count,
        "tool_failure_samples": tool_failure_samples,
        "active_maintenance_modes": maint_active,
        "pending_system_prompt_patches": pending_patches,
        "credits_used_in_window": credits_used,
    }


async def _tool_analyze_ai_errors(db, period_hours: int = 24, min_repeats: int = 2) -> Dict[str, Any]:
    """Scan recent chat sessions for repeated AI failure patterns (token stalls,
    placeholder leaks, loop hits, code reviewer rejections)."""
    from datetime import timedelta as _td
    import re as _re
    hours = max(1, min(int(period_hours or 24), 168))
    since = (datetime.now(timezone.utc) - _td(hours=hours)).isoformat()

    patterns = {
        "anti_announce_and_stop": _re.compile(r"Anti.?Announce.?and.?Stop|انتظر دقيقة|سأبدأ التنفيذ"),
        "placeholder_leak": _re.compile(r"\[placeholder|placeholder.text|TODO:|TBD|XXX", _re.IGNORECASE),
        "tool_loop_blocked": _re.compile(r"NO_LOOPS|tool.loop|repeated.tool", _re.IGNORECASE),
        "code_reviewer_reject": _re.compile(r"code.reviewer.rejected|REJECTED|قد رفض", _re.IGNORECASE),
        "404_published": _re.compile(r"published.404|slug.not.found", _re.IGNORECASE),
        "design_changed_arbitrarily": _re.compile(r"changed.design|بدّل التصميم|غير التصميم", _re.IGNORECASE),
    }
    hits: Dict[str, List[Dict[str, Any]]] = {k: [] for k in patterns}

    try:
        cursor = db.freebuild_chat_sessions.find(
            {"updated_at": {"$gte": since}},
            {"_id": 0, "project_id": 1, "messages": 1, "updated_at": 1},
        ).sort("updated_at", -1).limit(200)
        async for s in cursor:
            for m in (s.get("messages") or [])[-50:]:
                text = m.get("content") or ""
                if not isinstance(text, str):
                    continue
                for key, rx in patterns.items():
                    if rx.search(text) and len(hits[key]) < 20:
                        hits[key].append({
                            "project_id": s.get("project_id"),
                            "ts": m.get("ts") or s.get("updated_at"),
                            "snippet": text[:200],
                        })
    except Exception as e:
        return {"ok": False, "error": f"scan_failed: {e}"}

    # Convert to summary.
    summary = []
    for key, items in hits.items():
        if len(items) >= min_repeats:
            summary.append({
                "pattern": key,
                "occurrences": len(items),
                "first_seen_project": items[0].get("project_id"),
                "samples": items[:3],
            })
    summary.sort(key=lambda x: x["occurrences"], reverse=True)

    recommendations: List[str] = []
    if any(s["pattern"] == "anti_announce_and_stop" for s in summary):
        recommendations.append("الـ Anti-Stoppage Guard يتم تشغيله — تحقق من system prompt Rule 11.")
    if any(s["pattern"] == "placeholder_leak" for s in summary):
        recommendations.append("الـ Code Reviewer يجب أن يرفض أي HTML يحوي placeholder/TODO.")
    if any(s["pattern"] == "tool_loop_blocked" for s in summary):
        recommendations.append("الـ NO_LOOPS guard يحجب tool calls متكررة — راجع لماذا الـ AI يكررها.")
    if any(s["pattern"] == "design_changed_arbitrarily" for s in summary):
        recommendations.append("احرص على قاعدة 'الحفاظ على التصميم' (Design Preservation) في system prompt.")

    return {
        "ok": True,
        "window_hours": hours,
        "patterns_with_repeats": summary,
        "recommendations": recommendations,
        "scanned_min_repeats": min_repeats,
    }


async def _tool_propose_system_prompt_patch(
    db, observation: str, suggested_change: str, rationale: str, target: str = "freebuild_agent",
    actor_user_id: str = "",
) -> Dict[str, Any]:
    """Saves a system-prompt-improvement proposal. The owner reviews + applies manually
    via the UI (we do NOT auto-write the file — this is a safety boundary)."""
    if not observation or not suggested_change:
        return {"ok": False, "error": "observation and suggested_change are required"}
    proposal = {
        "id": str(uuid.uuid4()),
        "target": (target or "freebuild_agent")[:60],
        "observation": observation[:2000],
        "suggested_change": suggested_change[:4000],
        "rationale": (rationale or "")[:1000],
        "status": "pending",  # pending | approved | rejected | applied
        "created_at": _now_iso(),
        "proposed_by_user_id": actor_user_id,
    }
    await db.engineer_patch_proposals.insert_one(proposal)
    proposal.pop("_id", None)
    return {"ok": True, "proposal": proposal, "note": "اقتراح محفوظ. راجعه من تبويب «اقتراحات الإصلاح» وطبّقه يدوياً عبر «تطبيق» (لن يُكتب أوتوماتيكياً على ملفات السيرفر)."}


async def _tool_list_pending_patches(db, limit: int = 20) -> Dict[str, Any]:
    items = []
    try:
        cursor = db.engineer_patch_proposals.find(
            {"status": "pending"}, {"_id": 0}
        ).sort("created_at", -1).limit(int(limit or 20))
        async for p in cursor:
            items.append(p)
    except Exception:
        pass
    return {"ok": True, "patches": items, "count": len(items)}


async def _tool_enter_maintenance_mode(
    db, section: str, duration_minutes: int = 30, banner_ar: str = "", actor_user_id: str = "",
) -> Dict[str, Any]:
    """Activates maintenance mode for a section. The middleware reads this on each
    request and returns 503 + JSON banner for matching API paths. Sections:
    'images' | 'videos' | 'games' | 'global'."""
    from datetime import timedelta as _td
    sec = (section or "").strip().lower()
    if sec not in {"images", "videos", "games", "global"}:
        return {"ok": False, "error": "section must be one of: images, videos, games, global"}
    duration_minutes = max(5, min(int(duration_minutes or 30), 24 * 60))
    ends_at = (datetime.now(timezone.utc) + _td(minutes=duration_minutes)).isoformat()
    default_banner = (
        f"⚙️ قسم «{sec}» في تحديث جزئي حالياً — راح يعود خلال {duration_minutes} دقيقة. "
        "باقي الموقع شغّال طبيعي."
    )
    doc = {
        "section": sec,
        "active": True,
        "banner_ar": (banner_ar or default_banner)[:300],
        "started_at": _now_iso(),
        "ends_at": ends_at,
        "user_id": actor_user_id,
    }
    await db.zenrex_maintenance.update_one(
        {"section": sec},
        {"$set": doc},
        upsert=True,
    )
    return {"ok": True, "maintenance": doc}


async def _tool_exit_maintenance_mode(db, section: str, actor_user_id: str = "") -> Dict[str, Any]:
    sec = (section or "").strip().lower()
    if not sec:
        return {"ok": False, "error": "section is required"}
    await db.zenrex_maintenance.update_one(
        {"section": sec},
        {"$set": {"active": False, "ended_at": _now_iso(), "ended_by": actor_user_id}},
    )
    return {"ok": True, "section": sec, "active": False}


async def _tool_list_maintenance_modes(db) -> Dict[str, Any]:
    items = []
    try:
        async for m in db.zenrex_maintenance.find({}, {"_id": 0}):
            items.append(m)
    except Exception:
        pass
    return {"ok": True, "modes": items}


async def _tool_resume_project_ai(
    db, project_id: str, message: str, actor_user_id: str = "",
) -> Dict[str, Any]:
    """Inject a system-as-owner message into a project's chat session so the
    next time the user opens it, the AI sees a fresh instruction (e.g.
    'مهندس Zenrex Internal: عدّلت قسم hero يدوياً — كمل العمل من حيث وقفت')."""
    proj = await _find_project(db, project_id)
    if not proj:
        return {"ok": False, "error": "project not found"}
    note = (message or "").strip()
    if not note:
        return {"ok": False, "error": "message is required"}
    try:
        await db.freebuild_chat_sessions.update_one(
            {"project_id": project_id},
            {
                "$push": {
                    "messages": {
                        "role": "system",
                        "content": f"[🛠️ مهندس Zenrex الداخلي تدخّل]: {note[:1000]}",
                        "ts": _now_iso(),
                        "actor": actor_user_id,
                    },
                },
                "$set": {"updated_at": _now_iso()},
                "$setOnInsert": {"project_id": project_id, "created_at": _now_iso()},
            },
            upsert=True,
        )
    except Exception as e:
        return {"ok": False, "error": f"chat_session_write_failed: {e}"}
    return {"ok": True, "project_id": project_id, "injected": True, "note_preview": note[:200]}


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
        # 🆕 Owner-Engineer specialized tools (daily ops, maintenance, patches).
        if name == "get_daily_report":
            return await _tool_get_daily_report(db, args.get("hours", 24))
        if name == "analyze_ai_errors":
            return await _tool_analyze_ai_errors(
                db, args.get("period_hours", 24), args.get("min_repeats", 2),
            )
        if name == "propose_system_prompt_patch":
            return await _tool_propose_system_prompt_patch(
                db, args.get("observation", ""), args.get("suggested_change", ""),
                args.get("rationale", ""), args.get("target", "freebuild_agent"),
                actor_user_id,
            )
        if name == "list_pending_patches":
            return await _tool_list_pending_patches(db, args.get("limit", 20))
        if name == "enter_maintenance_mode":
            return await _tool_enter_maintenance_mode(
                db, args.get("section", ""), args.get("duration_minutes", 30),
                args.get("banner_ar", ""), actor_user_id,
            )
        if name == "exit_maintenance_mode":
            return await _tool_exit_maintenance_mode(
                db, args.get("section", ""), actor_user_id,
            )
        if name == "list_maintenance_modes":
            return await _tool_list_maintenance_modes(db)
        if name == "resume_project_ai":
            return await _tool_resume_project_ai(
                db, args.get("project_id", ""), args.get("message", ""), actor_user_id,
            )
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

        api_key_present = bool(
            (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
            or (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
        )
        if not api_key_present:
            raise HTTPException(500, "No Claude key configured (ANTHROPIC_API_KEY or EMERGENT_LLM_KEY)")

        from modules.shared.claude_simple import ask_claude  # type: ignore

        async def event_stream():
            yield f"event: start\ndata: {json.dumps({'session_id': sid, 'project_id': project_id})}\n\n"
            try:
                system_prompt = _OWNER_SYSTEM_PROMPT + project_context_block + (
                    "\n\n**TOOLS AVAILABLE:** " + json.dumps(_tools_schema(), ensure_ascii=False)
                    + "\n\nعند استدعاء أداة، اكتب فقط JSON نقي بدون markdown fences وبدون أي شرح إضافي، مثال صحيح:\n"
                    + '{"tool": "get_platform_stats", "args": {}}\n'
                    + 'ممنوع كتابة ```json أو ``` حول الـ JSON. ممنوع كتابة أي نص قبله أو بعده. '
                    + "بعد ما يجيك tool_result، أكمل المحادثة عادي بالعربي السعودي."
                )

                conversation = "\n".join(
                    f"{m['role'].upper()}: {m.get('content','')}" for m in history[-12:]
                )

                # Tool loop (max 10 iterations — supports read→fix→republish→audit chains)
                final_answer = ""
                for _ in range(10):
                    resp = await ask_claude(
                        system=system_prompt,
                        user_message=conversation,
                        session_id=sid,
                        max_tokens=4000,
                        timeout=60,
                    )
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

    # ────────────────────────────────────────────────────────────────────
    # 🛠️ IN-CHAT ENGINEER SUMMON  (any user, scoped to their own project)
    # ────────────────────────────────────────────────────────────────────
    # When the user types "استدعي المهندس" in FreeBuild chat, the frontend
    # POSTs here instead of the normal agent stream. The engineer runs
    # against THIS project only, with these tools:
    #   read_full_html · run_browser_audit · apply_fix_to_project ·
    #   republish_project · get_project_summary
    # Streamed back as event: engineer_start / engineer_tool / engineer_text /
    # engineer_done so the UI can render the conversation in purple.

    _ENGINEER_SCOPED_SYSTEM = """أنت "مهندس Zenrex" — مهندس صيانة وإصلاح للمشروع الحالي حصراً.

**صلاحياتك (لهذا المشروع فقط):**
1. `get_project_summary` — تفاصيل المشروع
2. `read_full_html` — اقرأ HTML أي صفحة
3. `run_browser_audit` — افتح الموقع المنشور بـ Playwright وافحص الأخطاء فعلياً
4. `apply_fix_to_project` — أصلح الكود (مع Code Reviewer قبل الحفظ)
5. `republish_project` — انشر النسخة الجديدة

**سير العمل الإلزامي عند استدعائك:**
1. **افحص أولاً** — `get_project_summary` ثم `read_full_html` للصفحة المعنية
2. **شخّص بصدق** — لو الموقع منشور، شغّل `run_browser_audit` تشوف الأخطاء الفعلية
3. **اشرح ما وجدته** للعميل بلغة بسيطة (سبب المشكلة + الحل المقترح)
4. **اقترح الإصلاح** كخيارات (1️⃣ سريع / 2️⃣ شامل) ودع العميل يختار
5. **بعد موافقته**، نفّذ `apply_fix_to_project` ثم `republish_project`
6. **تحقق** بـ `run_browser_audit` ثاني لو منشور

**ممنوع:**
- ممنوع الكذب أو الاختراع. كل ادعاء يجب أن يستند إلى نتيجة tool.
- ممنوع تحط فيكس بدون ما تقرأ الكود الحالي.
- ممنوع تكتب "سأفحص الآن" بدون استدعاء tool فعلي.

**لغتك:** عربي سعودي. تقني، صريح، مباشر. أنت مهندس لا مساعد.

عند استدعاء أداة: اكتب JSON نقي بدون ```json ولا أي شرح حوله. مثال:
{"tool": "read_full_html", "args": {"project_id": "...", "filename": "index.html"}}
"""

    @router.post("/project/{pid}/engineer-summon")
    async def engineer_summon(
        pid: str,
        message: str = Form(...),
        user=Depends(get_current_user),
    ):
        """Engineer summoned inside a regular FreeBuild chat. Scoped to ONE project."""
        # Verify the user owns this project (cross-project access stays in /owner/engineer/* only).
        proj = await db.freebuild_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0, "id": 1, "name": 1, "user_id": 1, "messages": 1, "published_slug": 1}
        ) or await db.freebuild_chat_projects.find_one(
            {"id": pid, "user_id": user["user_id"]}, {"_id": 0, "id": 1, "name": 1, "user_id": 1, "messages": 1, "published_slug": 1}
        )
        if not proj:
            raise HTTPException(404, "Project not found or access denied")

        uid = user["user_id"]
        sid = f"engineer-{pid}"

        # Project-focused context block.
        summary = await _tool_get_project_summary(db, pid)
        ctx_block = ""
        if summary.get("ok"):
            ctx_block = (
                f"\n\n**المشروع الحالي (قيد التشخيص):**\n"
                f"- id: {pid}\n"
                f"- name: {summary.get('name')}\n"
                f"- mode: {summary.get('mode')}\n"
                f"- pages: {summary.get('page_count')} ({', '.join((summary.get('pages') or [])[:6])})\n"
                f"- published: {summary.get('live_url') or 'غير منشور'}\n"
                f"كل tool call استخدم project_id={pid} بدون سؤال.\n"
            )

        try:
            from modules.shared.claude_simple import ask_claude
        except Exception:
            raise HTTPException(500, "Claude unavailable")

        async def event_stream():
            yield f"event: engineer_start\ndata: {json.dumps({'project_id': pid, 'name': proj.get('name')}, ensure_ascii=False)}\n\n"
            try:
                system_prompt = _ENGINEER_SCOPED_SYSTEM + ctx_block + (
                    "\n\n**TOOLS:**\n" + json.dumps([
                        t for t in _tools_schema()
                        if t["name"] in ("get_project_summary", "read_full_html",
                                         "run_browser_audit", "apply_fix_to_project",
                                         "republish_project")
                    ], ensure_ascii=False)
                )
                conversation = f"USER: {message}"

                final_answer = ""
                tool_steps: List[Dict[str, Any]] = []
                for _ in range(8):
                    resp = await ask_claude(
                        system=system_prompt,
                        user_message=conversation,
                        session_id=sid,
                        max_tokens=4000,
                        timeout=60,
                    )
                    txt = (resp or "").strip()
                    tool_json = _extract_first_json_object(txt)
                    if tool_json and tool_json.get("tool"):
                        tool_name = tool_json.get("tool")
                        tool_args = tool_json.get("args") or {}
                        # Hard-bind project_id to this project only.
                        tool_args["project_id"] = pid
                        args_preview = {
                            k: (v[:120] + "...[truncated]" if isinstance(v, str) and len(v) > 200 else v)
                            for k, v in tool_args.items()
                        }
                        yield f"event: engineer_tool\ndata: {json.dumps({'name': tool_name, 'args': args_preview}, ensure_ascii=False)}\n\n"
                        result = await _dispatch_owner_tool(db, tool_name, tool_args, actor_user_id=uid)
                        result_preview = {
                            k: (v[:300] + "...[truncated]" if isinstance(v, str) and len(v) > 500 else v)
                            for k, v in result.items()
                        }
                        yield f"event: engineer_tool_result\ndata: {json.dumps({'name': tool_name, 'result': result_preview}, ensure_ascii=False)}\n\n"
                        tool_steps.append({"name": tool_name, "ok": bool(result.get("ok"))})
                        conversation += f"\nASSISTANT: {txt[:400]}\nTOOL_RESULT[{tool_name}]: {json.dumps(result, ensure_ascii=False)[:2800]}"
                        continue
                    final_answer = txt
                    break

                yield f"event: engineer_text\ndata: {json.dumps({'content': final_answer or 'فحص اكتمل.', 'tools_run': len(tool_steps)}, ensure_ascii=False)}\n\n"

                # Persist into the project's message history so the chat preserves the engineer's turn.
                try:
                    eng_msg = {
                        "role": "engineer",
                        "content": final_answer or "فحص اكتمل.",
                        "ts": _now_iso(),
                        "tool_steps": tool_steps,
                    }
                    user_msg = {"role": "user", "content": message, "ts": _now_iso(), "summon": "engineer"}
                    for col in ("freebuild_projects", "freebuild_chat_projects"):
                        await db[col].update_one(
                            {"id": pid, "user_id": uid},
                            {"$push": {"messages": {"$each": [user_msg, eng_msg]}}},
                        )
                except Exception as e:
                    logger.warning(f"[engineer-summon] persist failed: {e}")

                yield f"event: engineer_done\ndata: {json.dumps({'ok': True}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.exception(f"[engineer-summon] failed: {e}")
                yield f"event: engineer_error\ndata: {json.dumps({'message': str(e)[:200]}, ensure_ascii=False)}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @router.get("/owner/engineer/independence")
    async def owner_independence(user=Depends(get_current_user)):
        """Reports which AI providers the platform actually uses.

        Zenrex is committed to direct provider connections only — no
        middlemen, no Emergent, no proxy. This endpoint confirms that
        commitment in real time.
        """
        _ensure_owner(user)
        try:
            from modules.shared.claude_simple import which_provider
            provider = which_provider()
        except Exception:
            provider = "none"
        anthropic_key_set = bool((os.environ.get("ANTHROPIC_API_KEY") or "").strip())
        openai_key_set = bool((os.environ.get("OPENAI_API_KEY") or "").strip())
        fal_key_set = bool((os.environ.get("FAL_KEY") or "").strip())
        emergent_key_set = bool((os.environ.get("EMERGENT_LLM_KEY") or "").strip())
        return {
            "primary": provider,
            "independent": provider == "anthropic_direct",
            "providers": {
                "anthropic": {
                    "key_set": anthropic_key_set,
                    "usage": "Claude Sonnet 4.5 — كل الذكاء (البناء، الخطة، المراجعة، المهندس)",
                    "cost_share": "~90%",
                },
                "openai": {
                    "key_set": openai_key_set,
                    "usage": "Whisper STT فقط — لتحويل الصوت لنص في الشات",
                    "cost_share": "~3%",
                },
                "fal": {
                    "key_set": fal_key_set,
                    "usage": "FLUX — توليد صور المشاريع",
                    "cost_share": "~7%",
                },
            },
            "emergent_key_still_in_env": emergent_key_set,
            "emergent_actually_used": False,  # Hardcoded: code path removed entirely.
            "message": (
                "✅ مستقل 100%. كل النداءات مباشرة للمزودين الأصليين. لا Emergent ولا أي وسيط." if provider == "anthropic_direct"
                else "🚨 ANTHROPIC_API_KEY غير موجود! الذكاء معطّل."
            ),
        }

    # ─────────────────────────────────────────────────────────────────
    # 🆕 Dashboard REST endpoints (used by the new OwnerEngineer UI for
    # cards/widgets — NOT the chat. The chat uses the streaming endpoint.)
    # ─────────────────────────────────────────────────────────────────
    @router.get("/owner/engineer/daily-report")
    async def owner_daily_report(hours: int = 24, user=Depends(get_current_user)):
        _ensure_owner(user)
        return await _tool_get_daily_report(db, hours)

    @router.get("/owner/engineer/error-analysis")
    async def owner_error_analysis(
        period_hours: int = 24, min_repeats: int = 2, user=Depends(get_current_user),
    ):
        _ensure_owner(user)
        return await _tool_analyze_ai_errors(db, period_hours, min_repeats)

    @router.get("/owner/engineer/patches")
    async def owner_list_patches(user=Depends(get_current_user)):
        _ensure_owner(user)
        return await _tool_list_pending_patches(db, 50)

    @router.post("/owner/engineer/patches/{pid}/approve")
    async def owner_approve_patch(pid: str, user=Depends(get_current_user)):
        _ensure_owner(user)
        res = await db.engineer_patch_proposals.update_one(
            {"id": pid},
            {"$set": {"status": "approved", "approved_by": user["user_id"], "approved_at": _now_iso()}},
        )
        if res.matched_count == 0:
            raise HTTPException(404, "patch not found")
        return {"ok": True, "id": pid, "status": "approved"}

    @router.post("/owner/engineer/patches/{pid}/reject")
    async def owner_reject_patch(pid: str, user=Depends(get_current_user)):
        _ensure_owner(user)
        res = await db.engineer_patch_proposals.update_one(
            {"id": pid},
            {"$set": {"status": "rejected", "rejected_by": user["user_id"], "rejected_at": _now_iso()}},
        )
        if res.matched_count == 0:
            raise HTTPException(404, "patch not found")
        return {"ok": True, "id": pid, "status": "rejected"}

    @router.get("/owner/engineer/maintenance")
    async def owner_list_maintenance(user=Depends(get_current_user)):
        _ensure_owner(user)
        return await _tool_list_maintenance_modes(db)

    @router.post("/owner/engineer/maintenance/enter")
    async def owner_enter_maintenance(
        section: str = Form(...),
        duration_minutes: int = Form(30),
        banner_ar: str = Form(""),
        user=Depends(get_current_user),
    ):
        _ensure_owner(user)
        return await _tool_enter_maintenance_mode(
            db, section, duration_minutes, banner_ar, user["user_id"],
        )

    @router.post("/owner/engineer/maintenance/exit")
    async def owner_exit_maintenance(
        section: str = Form(...),
        user=Depends(get_current_user),
    ):
        _ensure_owner(user)
        return await _tool_exit_maintenance_mode(db, section, user["user_id"])

    # Public read of active maintenance (no auth) so frontend banners can show.
    @router.get("/maintenance/active")
    async def public_active_maintenance():
        items: List[Dict[str, Any]] = []
        try:
            now_iso = _now_iso()
            async for m in db.zenrex_maintenance.find(
                {"active": True}, {"_id": 0, "section": 1, "banner_ar": 1, "ends_at": 1, "started_at": 1},
            ):
                # Auto-expire if ends_at passed.
                if m.get("ends_at") and m["ends_at"] < now_iso:
                    await db.zenrex_maintenance.update_one(
                        {"section": m["section"]}, {"$set": {"active": False, "auto_ended": True}},
                    )
                    continue
                items.append(m)
        except Exception:
            pass
        return {"active": items}
