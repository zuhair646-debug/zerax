"""
Owner Engineer — الذكاء المهندس الشخصي للمالك.

A dedicated AI assistant for the platform owner with elevated tools:
    • list_my_projects  → enumerate every project the owner owns
    • get_project_summary → details for a specific project
    • search_projects → keyword search across owner's projects
    • read_project_page → read the HTML of a specific page within a project
    • get_platform_stats → high-level health metrics

Uses the same Claude Sonnet 4.5 with a strict "Senior AI Engineer" persona.
Owner messages persist in `owner_chat_sessions` collection so context carries
across browser sessions.
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


_OWNER_SYSTEM_PROMPT = """أنت "مهندس Zenrex الشخصي" — وكيل ذكاء اصطناعي يساعد مالك المنصة (وليس عميلاً عادياً).

**هويتك:**
- اسمك: مهندس Zenrex.
- لغتك: العربية الفصحى السعودية. تكون مباشر، تقني، صريح، بدون مجاملات.
- منظورك: أنت تعرف منصة Zenrex من الداخل — قواعد البيانات، الـ AI orchestrator، كل المشاريع لكل المستخدمين، التقارير.

**صلاحياتك:** أنت ترى **كل المشاريع على السيرفر** (ليس فقط مشاريع المالك). كل مستخدم وكل مشروع متاح للقراءة والاستعراض.

**المالك يستخدمك لـ:**
1. **استعراض كل المشاريع** — يقول "أعطني آخر المشاريع" → تستدعي `list_all_projects`.
2. **فهم وضع مشروع معين** — يقول "كيف حال مشروع X؟" → `get_project_summary`.
3. **البحث في الأرشيف** — "وين مشروع اليوتيوب للأطفال؟" → `search_projects` (يبحث بكل السيرفر).
4. **قراءة كود صفحة** — "ايش فيه index.html من مشروع X؟" → `read_project_page`.
5. **معلومات صاحب المشروع** — "مين صاحب مشروع X؟" → `get_project_owner`.
6. **إحصائيات المنصة** — "كم مشروع نشط الأسبوع؟" → `get_platform_stats`.
7. **مساعدته في القرارات التقنية** — مناقشات معمارية، اقتراحات تحسين، تشخيص bugs.

**قواعد إلزامية:**
- لا تخترع بيانات. إذا احتجت معلومة عن مشروع، استدع الـ tool — لا تخمّن.
- لا تكتب كود من ذاكرتك يدّعي إنه من المشروع — اقرأه أولاً.
- لا تسأل أسئلة كثيرة — استخدم الـ tools لجلب البيانات بنفسك.
- المالك يثق فيك — لا تتردد في عرض بيانات أي مشروع لأي مستخدم (هذي صلاحية المالك).
- التعديل المباشر للكود غير مفعّل بعد — إذا طُلب، اقترح خطة وأبلغ المالك.

كن ذكي، مختصر، تقني. أنت مع المالك — تكلم كأنك co-founder.
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


async def _dispatch_owner_tool(db, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
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
        if name == "get_project_owner":
            return await _tool_get_project_owner(db, args.get("project_id", ""))
        if name == "get_platform_stats":
            return await _tool_get_platform_stats(db)
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

                # Tool loop (max 5 iterations)
                final_answer = ""
                import re as _re
                for _ in range(5):
                    resp = await chat.send_message(UserMessage(text=conversation))
                    if not isinstance(resp, str):
                        resp = str(resp)
                    txt = resp.strip()
                    # Be tolerant: extract first JSON object from text (handles ```json fences).
                    tool_json = None
                    m = _re.search(r"\{[^{}]*\"tool\"[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", txt, _re.DOTALL)
                    if m:
                        try:
                            tool_json = json.loads(m.group(0))
                        except Exception:
                            tool_json = None
                    if tool_json and tool_json.get("tool"):
                        tool_name = tool_json.get("tool")
                        tool_args = tool_json.get("args") or {}
                        yield f"event: tool\ndata: {json.dumps({'name': tool_name, 'args': tool_args}, ensure_ascii=False)}\n\n"
                        result = await _dispatch_owner_tool(db, tool_name, tool_args)
                        yield f"event: tool_result\ndata: {json.dumps({'name': tool_name, 'result': result}, ensure_ascii=False)}\n\n"
                        conversation += f"\nASSISTANT: {txt}\nTOOL_RESULT[{tool_name}]: {json.dumps(result, ensure_ascii=False)[:2000]}"
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
