"""
Learning Journal — the AI's persistent memory across sessions.

The AI logs an "lesson learned" after each successful task. These lessons
are stored in MongoDB and re-injected into the system prompt next time, so
the AI compounds intelligence day by day.

Schema (autocoder_lessons collection):
  {
    _id: ObjectId,
    id: str (uuid),
    source: 'owner' | 'user',
    actor_id: str | None,        # user id, if source=user
    task_summary: str,           # what was being done (≤200 chars)
    lesson: str,                 # the insight learned (≤500 chars)
    code_pattern: str | None,    # optional code snippet illustrating the pattern
    tags: [str],                 # ['frontend', 'auth', 'bug-fix', ...]
    pinned: bool,                # if true, always in prompt
    archived: bool,              # excluded from prompt + UI
    relevance_score: int,        # increases each time it's "useful again"
    created_at: ISO datetime,
    last_used_at: ISO datetime | None,
  }

Three AI tools:
  • record_lesson(summary, lesson, source, code_pattern?, tags?)
  • recall_lessons(query?, limit?)
  • promote_lesson(lesson_id, pinned=true/false)
"""
from __future__ import annotations
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Module-level DB binding (set at router creation)
_DB: Any = None


def bind_db(db) -> None:
    global _DB
    _DB = db


# ════════════════════════════════════════════════════════════════════════
# Core CRUD
# ════════════════════════════════════════════════════════════════════════
async def add_lesson(
    task_summary: str,
    lesson: str,
    source: str = "owner",
    actor_id: Optional[str] = None,
    code_pattern: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if _DB is None:
        return {"ok": False, "error": "DB not bound"}
    if not task_summary or not lesson:
        return {"ok": False, "error": "task_summary وlesson مطلوبين"}
    doc = {
        "id": str(uuid.uuid4()),
        "source": source if source in ("owner", "user", "system") else "owner",
        "actor_id": actor_id,
        "task_summary": task_summary[:500],
        "lesson": lesson[:1500],
        "code_pattern": (code_pattern or None)[:2000] if code_pattern else None,
        "tags": tags or [],
        "pinned": False,
        "archived": False,
        "relevance_score": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_used_at": None,
    }
    try:
        await _DB.autocoder_lessons.insert_one(doc.copy())
    except Exception as e:
        logger.warning(f"add_lesson failed: {e}")
        return {"ok": False, "error": str(e)}
    return {"ok": True, "lesson_id": doc["id"]}


async def query_lessons(
    query: str = "",
    limit: int = 20,
    source: str = "",
    include_archived: bool = False,
) -> List[Dict[str, Any]]:
    if _DB is None:
        return []
    filt: Dict[str, Any] = {}
    if not include_archived:
        filt["archived"] = {"$ne": True}
    if source:
        filt["source"] = source
    if query:
        # Mongo regex (case-insensitive) across summary + lesson + tags
        q = {"$regex": query, "$options": "i"}
        filt["$or"] = [
            {"task_summary": q}, {"lesson": q}, {"tags": q},
        ]
    cur = _DB.autocoder_lessons.find(filt, {"_id": 0}).sort([
        ("pinned", -1), ("relevance_score", -1), ("created_at", -1),
    ]).limit(limit)
    return await cur.to_list(limit)


async def promote(lesson_id: str, pinned: bool = True) -> Dict[str, Any]:
    if _DB is None:
        return {"ok": False, "error": "DB not bound"}
    res = await _DB.autocoder_lessons.update_one(
        {"id": lesson_id},
        {"$set": {"pinned": pinned}},
    )
    return {"ok": res.modified_count > 0, "lesson_id": lesson_id, "pinned": pinned}


async def archive(lesson_id: str, archived: bool = True) -> Dict[str, Any]:
    if _DB is None:
        return {"ok": False, "error": "DB not bound"}
    res = await _DB.autocoder_lessons.update_one(
        {"id": lesson_id},
        {"$set": {"archived": archived}},
    )
    return {"ok": res.modified_count > 0, "lesson_id": lesson_id, "archived": archived}


async def bump_relevance(lesson_id: str) -> None:
    if _DB is None:
        return
    try:
        await _DB.autocoder_lessons.update_one(
            {"id": lesson_id},
            {"$inc": {"relevance_score": 1},
             "$set": {"last_used_at": datetime.now(timezone.utc).isoformat()}},
        )
    except Exception:
        pass


async def get_stats() -> Dict[str, Any]:
    if _DB is None:
        return {"total": 0}
    total = await _DB.autocoder_lessons.count_documents({"archived": {"$ne": True}})
    pinned = await _DB.autocoder_lessons.count_documents({"pinned": True, "archived": {"$ne": True}})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_count = await _DB.autocoder_lessons.count_documents(
        {"archived": {"$ne": True}, "created_at": {"$regex": f"^{today}"}}
    )
    by_source: Dict[str, int] = {}
    async for doc in _DB.autocoder_lessons.aggregate([
        {"$match": {"archived": {"$ne": True}}},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
    ]):
        by_source[doc["_id"] or "unknown"] = doc["count"]
    return {
        "total": total,
        "pinned": pinned,
        "today": today_count,
        "by_source": by_source,
    }


# ════════════════════════════════════════════════════════════════════════
# Prompt injection — pin the most important lessons into system prompt
# ════════════════════════════════════════════════════════════════════════
async def build_lessons_for_prompt(max_lessons: int = 12) -> str:
    """Pull pinned + recent lessons and format them for the system prompt."""
    if _DB is None:
        return ""
    cur = _DB.autocoder_lessons.find(
        {"archived": {"$ne": True}},
        {"_id": 0, "lesson": 1, "task_summary": 1, "tags": 1, "source": 1, "pinned": 1, "created_at": 1, "code_pattern": 1},
    ).sort([("pinned", -1), ("relevance_score", -1), ("created_at", -1)]).limit(max_lessons)
    lessons = await cur.to_list(max_lessons)
    if not lessons:
        return ""
    lines = [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📚 الذاكرة المتراكمة — {len(lessons)} درس مستفاد من جلسات سابقة",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "هذه الدروس تعلّمتها من تفاعلات سابقة. التزم بها لتجنّب تكرار الأخطاء:",
        "",
    ]
    for i, ls in enumerate(lessons, 1):
        pin = "📌" if ls.get("pinned") else "•"
        src = ls.get("source", "owner")
        src_emoji = "👑" if src == "owner" else ("👤" if src == "user" else "🤖")
        summary = (ls.get("task_summary") or "")[:120]
        lesson = (ls.get("lesson") or "")[:300]
        tags = " ".join(f"#{t}" for t in (ls.get("tags") or [])[:3])
        lines.append(f"  {pin} {src_emoji} **{summary}**")
        lines.append(f"     → {lesson}")
        if tags:
            lines.append(f"     {tags}")
        if ls.get("code_pattern"):
            pat = ls["code_pattern"][:200].replace("\n", " ⏎ ")
            lines.append(f"     `{pat}`")
        lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 بعد ما تنجز أي مهمة، نادي **record_lesson** عشان نتذكّر سوياً.")
    lines.append("")
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════
# AI-callable tool wrappers
# ════════════════════════════════════════════════════════════════════════
async def tool_record_lesson(
    task_summary: str,
    lesson: str,
    source: str = "owner",
    code_pattern: str = "",
    tags: str = "",
) -> Dict[str, Any]:
    """Save a lesson learned. Use this after any successful task."""
    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    return await add_lesson(
        task_summary=task_summary,
        lesson=lesson,
        source=source,
        code_pattern=code_pattern or None,
        tags=tag_list,
    )


async def tool_recall_lessons(query: str = "", limit: int = 10, source: str = "") -> Dict[str, Any]:
    """Search the learning journal. Use this before tackling unfamiliar tasks."""
    items = await query_lessons(query=query, limit=limit, source=source)
    return {"ok": True, "count": len(items), "lessons": items}


async def tool_promote_lesson(lesson_id: str, pinned: bool = True) -> Dict[str, Any]:
    return await promote(lesson_id, pinned)


async def tool_learning_stats() -> Dict[str, Any]:
    return {"ok": True, "stats": await get_stats()}


# ════════════════════════════════════════════════════════════════════════
# Anthropic schemas
# ════════════════════════════════════════════════════════════════════════
LEARNING_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "record_lesson",
        "description": ("Save a lesson learned to the persistent journal. **استدعِها في نهاية كل مهمة ناجحة**. "
                       "لخّص في `task_summary` المهمة وفي `lesson` الدرس المستفاد (بحيث لو واجهتها مرة ثانية تعرفها فوراً). "
                       "tags: comma-separated مثل 'frontend,bug-fix,auth'."),
        "input_schema": {"type": "object", "properties": {
            "task_summary": {"type": "string", "description": "وش كانت المهمة (≤200 حرف)"},
            "lesson": {"type": "string", "description": "وش تعلّمت بالضبط (≤500 حرف)"},
            "source": {"type": "string", "description": "owner|user|system"},
            "code_pattern": {"type": "string", "description": "(اختياري) نمط كود مفيد"},
            "tags": {"type": "string", "description": "(اختياري) tags مفصولة بفاصلة"},
        }, "required": ["task_summary", "lesson"]},
    },
    {
        "name": "recall_lessons",
        "description": "Search the learning journal. Use BEFORE unfamiliar tasks to check if you've seen similar before.",
        "input_schema": {"type": "object", "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
            "source": {"type": "string", "description": "owner|user|system"},
        }, "required": []},
    },
    {
        "name": "promote_lesson",
        "description": "Pin a lesson so it always appears in your system prompt (most important insights).",
        "input_schema": {"type": "object", "properties": {
            "lesson_id": {"type": "string"},
            "pinned": {"type": "boolean"},
        }, "required": ["lesson_id"]},
    },
    {
        "name": "learning_stats",
        "description": "Show your learning progress (total lessons, today's, by source).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

LEARNING_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "record_lesson", "desc": "save a lesson learned", "args": ["task_summary", "lesson", "source?", "code_pattern?", "tags?"]},
    {"name": "recall_lessons", "desc": "search journal", "args": ["query?", "limit?", "source?"]},
    {"name": "promote_lesson", "desc": "pin a lesson", "args": ["lesson_id", "pinned?"]},
    {"name": "learning_stats", "desc": "progress summary", "args": []},
]

LEARNING_TOOL_HANDLERS = {
    "record_lesson": tool_record_lesson,
    "recall_lessons": tool_recall_lessons,
    "promote_lesson": tool_promote_lesson,
    "learning_stats": tool_learning_stats,
}


def learning_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in LEARNING_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return f"✗ {(result.get('error') or '')[:120]}"
    if name == "record_lesson":
        return f"📚 درس مسجّل: {result.get('lesson_id', '')[:8]}..."
    if name == "recall_lessons":
        return f"{result.get('count', 0)} درس مطابق"
    if name == "promote_lesson":
        return f"📌 {'مثبّت' if result.get('pinned') else 'مفكوك'}"
    if name == "learning_stats":
        s = result.get("stats", {})
        return f"📊 {s.get('total')} درس · اليوم {s.get('today')} · مثبّت {s.get('pinned')}"
    return None


def learning_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name == "recall_lessons":
        out = []
        for ls in result.get("lessons", [])[:5]:
            out.append(f"  📚 {ls.get('task_summary','')[:60]}")
            out.append(f"     → {ls.get('lesson','')[:120]}")
        return "\n".join(out)
    if name == "learning_stats":
        import json as _j
        return _j.dumps(result.get("stats", {}), ensure_ascii=False, indent=2)
    return None


LEARNING_PROMPT_RULES = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 التعلّم المستمر — لا تنسى ما تعلّمته
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

عندك ذاكرة دائمة الآن (autocoder_lessons collection) تستمر عبر الجلسات.

📌 سير العمل:

  1. **قبل المهمة** (للمهام غير المألوفة):
     → recall_lessons(query="auth bug") — هل واجهت شي مشابه قبل؟

  2. **بعد المهمة الناجحة**:
     → record_lesson(
         task_summary="إصلاح رفع صور Vercel HTTPS",
         lesson="navigator.mediaDevices لا يعمل على HTTP — لازم HTTPS",
         tags="frontend,bug-fix,browser-api"
       )

  3. **لما تكتشف pattern مهم**:
     → record_lesson + promote_lesson(pinned=true) للأنماط الذهبية

🎯 المالك يطلع على هذه الدروس في /admin/learning ويشوف تطورك يوماً بيوم.
   كل درس مفيد = خطوة في النضج.

⚠️ **مهم**: لا تسجّل دروس تافهة (مثل "Python يستخدم indentation"). فقط الدروس
   الخاصة بالموقع/المشروع/المالك التي ستوفر عليك وقت لاحقاً.
"""
