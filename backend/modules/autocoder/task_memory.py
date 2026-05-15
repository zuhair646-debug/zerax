"""
Task Memory — persistent state of in-progress work.

The big complaint: every new conversation, the AI re-reads the same files
and asks the same questions. This module fixes that.

Mongo collection: `autocoder_tasks`
  {
    id, owner_id, title, status: 'active'|'paused'|'completed'|'failed',
    goal, steps_done: [{step, summary, ts}],
    files_touched: [str], files_read: [{path, mtime, sha8}],
    decisions_made: [{q, choice, ts}],
    blockers: [str],
    started_at, last_updated_at, completed_at
  }

Key behavior — when a new chat starts, the AI **automatically calls**
`active_tasks()` first. If there's an active task it continues from `steps_done`
instead of starting over.
"""
from __future__ import annotations
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DB: Any = None


def bind_db(db) -> None:
    global _DB
    _DB = db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_sha8(path: str) -> str:
    try:
        p = Path(path)
        if not p.exists() or p.is_dir():
            return ""
        return hashlib.sha256(p.read_bytes()).hexdigest()[:8]
    except Exception:
        return ""


# ════════════════════════════════════════════════════════════════════════
# CRUD
# ════════════════════════════════════════════════════════════════════════
async def start_task(title: str, goal: str = "", owner_id: str = "") -> Dict[str, Any]:
    if _DB is None:
        return {"ok": False, "error": "DB not bound"}
    doc = {
        "id": str(uuid.uuid4()),
        "owner_id": owner_id or "owner",
        "title": title[:200],
        "goal": goal[:1000],
        "status": "active",
        "steps_done": [],
        "files_touched": [],
        "files_read": [],
        "decisions_made": [],
        "blockers": [],
        "started_at": _now(),
        "last_updated_at": _now(),
        "completed_at": None,
    }
    try:
        await _DB.autocoder_tasks.insert_one(doc.copy())
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "task_id": doc["id"], "title": doc["title"]}


async def list_tasks(status: str = "active", limit: int = 10) -> List[Dict[str, Any]]:
    if _DB is None:
        return []
    filt: Dict[str, Any] = {}
    if status:
        filt["status"] = status
    cur = _DB.autocoder_tasks.find(filt, {"_id": 0}).sort([("last_updated_at", -1)]).limit(limit)
    return await cur.to_list(limit)


async def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    if _DB is None:
        return None
    return await _DB.autocoder_tasks.find_one({"id": task_id}, {"_id": 0})


async def update_task(
    task_id: str,
    add_step: str = "",
    file_touched: str = "",
    file_read: str = "",
    decision: str = "",
    blocker: str = "",
    status: str = "",
) -> Dict[str, Any]:
    if _DB is None:
        return {"ok": False, "error": "DB not bound"}
    set_doc: Dict[str, Any] = {"last_updated_at": _now()}
    push_doc: Dict[str, Any] = {}
    if status:
        set_doc["status"] = status
        if status in ("completed", "failed"):
            set_doc["completed_at"] = _now()
    if add_step:
        push_doc["steps_done"] = {"summary": add_step[:300], "ts": _now()}
    if file_touched:
        push_doc["files_touched"] = file_touched
    if file_read:
        push_doc["files_read"] = {"path": file_read, "sha8": _file_sha8(file_read), "ts": _now()}
    if decision:
        push_doc["decisions_made"] = {"text": decision[:300], "ts": _now()}
    if blocker:
        push_doc["blockers"] = blocker[:300]
    update: Dict[str, Any] = {"$set": set_doc}
    if push_doc:
        update["$push"] = push_doc
    res = await _DB.autocoder_tasks.update_one({"id": task_id}, update)
    if res.matched_count == 0:
        return {"ok": False, "error": f"task {task_id} not found"}
    return {"ok": True, "task_id": task_id, "updated": list(set_doc.keys()) + list(push_doc.keys())}


async def complete_task(task_id: str, summary: str = "") -> Dict[str, Any]:
    if summary:
        await update_task(task_id, add_step=f"✅ COMPLETED: {summary}")
    return await update_task(task_id, status="completed")


# ════════════════════════════════════════════════════════════════════════
# File-read cache — avoid re-reading unchanged files
# ════════════════════════════════════════════════════════════════════════
async def was_file_read(file_path: str, in_active_tasks: bool = True) -> Optional[Dict[str, Any]]:
    """Return a previous read record if file was read before AND hasn't changed."""
    if _DB is None:
        return None
    current_sha = _file_sha8(file_path)
    if not current_sha:
        return None
    filt: Dict[str, Any] = {"files_read.path": file_path}
    if in_active_tasks:
        filt["status"] = "active"
    doc = await _DB.autocoder_tasks.find_one(filt, {"_id": 0, "id": 1, "title": 1, "files_read.$": 1})
    if not doc:
        return None
    reads = doc.get("files_read", [])
    for fr in reads:
        if fr.get("path") == file_path:
            unchanged = fr.get("sha8") == current_sha
            return {
                "task_id": doc["id"],
                "task_title": doc.get("title"),
                "previous_sha8": fr.get("sha8"),
                "current_sha8": current_sha,
                "unchanged": unchanged,
                "read_at": fr.get("ts"),
            }
    return None


# ════════════════════════════════════════════════════════════════════════
# Session brief — auto-prepended on every chat session
# ════════════════════════════════════════════════════════════════════════
async def build_session_brief(max_tasks: int = 3) -> str:
    """Pulled into system prompt — tells the AI 'here's where we left off'."""
    if _DB is None:
        return ""
    active = await list_tasks(status="active", limit=max_tasks)
    if not active:
        return ""
    lines = [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🎯 المهام النشطة — {len(active)} مهمة قيد التنفيذ (لا تبدأ من الصفر)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    for t in active:
        lines.append(f"")
        lines.append(f"  📋 **{t['title']}** (#{t['id'][:8]})")
        if t.get("goal"):
            lines.append(f"     🎯 الهدف: {t['goal'][:200]}")
        steps = t.get("steps_done", [])
        if steps:
            lines.append(f"     ✅ خطوات منجزة ({len(steps)}):")
            for s in steps[-5:]:
                lines.append(f"        • {s.get('summary','')[:120]}")
        if t.get("blockers"):
            lines.append(f"     🚧 عوائق: {' · '.join(t['blockers'][-3:])}")
        files_read = t.get("files_read", [])
        if files_read:
            recent = [fr.get("path", "") for fr in files_read[-5:]]
            lines.append(f"     📄 ملفات قرأتها سابقاً: {' · '.join(p.split('/')[-1] for p in recent)}")
        files_touched = t.get("files_touched", [])
        if files_touched:
            lines.append(f"     ✏️ ملفات عدّلتها: {len(files_touched)}")
    lines.append("")
    lines.append("⚡ التزم: استدعِ `task_resume(task_id)` للاطلاع على التفاصيل الكاملة ثم كمّل من المكان اللي وقفت فيه.")
    lines.append("    لا تعيد قراءة الملفات اللي قريتها (استخدم `was_file_read(path)` للتأكد).")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════════
# AI tool wrappers
# ════════════════════════════════════════════════════════════════════════
async def tool_active_tasks() -> Dict[str, Any]:
    """🔥 استدعها أول شي في كل محادثة جديدة — تشوف لو في مهام لم تنته."""
    items = await list_tasks(status="active", limit=10)
    return {"ok": True, "count": len(items), "tasks": items}


async def tool_task_resume(task_id: str) -> Dict[str, Any]:
    """Full details of an in-progress task to continue from where you left off."""
    t = await get_task(task_id)
    if not t:
        return {"ok": False, "error": f"task {task_id} not found"}
    return {"ok": True, "task": t}


async def tool_task_start(title: str, goal: str = "") -> Dict[str, Any]:
    """Start tracking a new task. Returns task_id you'll use for update calls."""
    return await start_task(title=title, goal=goal)


async def tool_task_update(
    task_id: str,
    step: str = "",
    file_read: str = "",
    file_touched: str = "",
    decision: str = "",
    blocker: str = "",
) -> Dict[str, Any]:
    """Update the active task: add a step / record a file read or write / log a decision / flag a blocker."""
    return await update_task(
        task_id,
        add_step=step, file_read=file_read, file_touched=file_touched,
        decision=decision, blocker=blocker,
    )


async def tool_task_complete(task_id: str, summary: str = "") -> Dict[str, Any]:
    """Mark task as completed."""
    return await complete_task(task_id, summary)


async def tool_was_file_read(file_path: str) -> Dict[str, Any]:
    """Check if you already read this file in an active task — if unchanged, skip re-reading."""
    r = await was_file_read(file_path, in_active_tasks=True)
    return {"ok": True, "found": r is not None, "info": r}


# ════════════════════════════════════════════════════════════════════════
# Anthropic schemas
# ════════════════════════════════════════════════════════════════════════
MEMORY_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "active_tasks",
        "description": ("🔥 **استدعها أول شي في كل محادثة جديدة** — ترجع المهام اللي لم تكمل. "
                       "لو فيها مهمة نشطة، كمّل من المكان اللي وقفت فيه بدل ما تبدأ من الصفر."),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "task_resume",
        "description": "اعرض كل تفاصيل مهمة (خطوات منجزة، ملفات مقروءة، قرارات، عوائق) عشان تكمل منها.",
        "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
    },
    {
        "name": "task_start",
        "description": "ابدأ tracking مهمة جديدة — استدعها لما المالك يطلب شي. تحفظ ها task_id للـ updates.",
        "input_schema": {"type": "object", "properties": {
            "title": {"type": "string", "description": "عنوان مختصر للمهمة"},
            "goal": {"type": "string", "description": "تفاصيل الهدف"},
        }, "required": ["title"]},
    },
    {
        "name": "task_update",
        "description": ("سجّل تقدّم: خطوة جديدة / قراءة ملف / تعديل ملف / قرار / عائق. "
                       "**استدعها بعد كل خطوة كبيرة** عشان لو انقطعت المحادثة، الذكاء التالي يكمّل."),
        "input_schema": {"type": "object", "properties": {
            "task_id": {"type": "string"},
            "step": {"type": "string", "description": "ما الذي أنجزته"},
            "file_read": {"type": "string", "description": "(اختياري) ملف قرأته"},
            "file_touched": {"type": "string", "description": "(اختياري) ملف عدّلته"},
            "decision": {"type": "string", "description": "(اختياري) قرار اتخذته"},
            "blocker": {"type": "string", "description": "(اختياري) شي يعطّلك"},
        }, "required": ["task_id"]},
    },
    {
        "name": "task_complete",
        "description": "أنهِ المهمة (status=completed). مرّر summary بالنتيجة النهائية.",
        "input_schema": {"type": "object", "properties": {
            "task_id": {"type": "string"},
            "summary": {"type": "string"},
        }, "required": ["task_id"]},
    },
    {
        "name": "was_file_read",
        "description": ("هل قريت هذا الملف قبل في مهمة نشطة؟ لو نعم وما تغيّر، **لا تعيد قراءته** — وفّر tokens. "
                       "ترجع: {found, info: {previous_sha8, unchanged, read_at}}."),
        "input_schema": {"type": "object", "properties": {
            "file_path": {"type": "string"},
        }, "required": ["file_path"]},
    },
]

MEMORY_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "active_tasks", "desc": "list in-progress tasks", "args": []},
    {"name": "task_resume", "desc": "full task details", "args": ["task_id"]},
    {"name": "task_start", "desc": "begin tracking", "args": ["title", "goal?"]},
    {"name": "task_update", "desc": "log progress", "args": ["task_id", "step?", "file_read?", "file_touched?", "decision?", "blocker?"]},
    {"name": "task_complete", "desc": "mark done", "args": ["task_id", "summary?"]},
    {"name": "was_file_read", "desc": "check file-read cache", "args": ["file_path"]},
]

MEMORY_TOOL_HANDLERS = {
    "active_tasks": tool_active_tasks,
    "task_resume": tool_task_resume,
    "task_start": tool_task_start,
    "task_update": tool_task_update,
    "task_complete": tool_task_complete,
    "was_file_read": tool_was_file_read,
}


def memory_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in MEMORY_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return f"✗ {(result.get('error') or '')[:120]}"
    if name == "active_tasks":
        return f"{result.get('count', 0)} مهمة نشطة"
    if name == "task_start":
        return f"📋 task: {result.get('title','')[:60]} (#{result.get('task_id','')[:8]})"
    if name == "task_resume":
        t = result.get("task", {})
        return f"📋 {t.get('title','')[:60]} · {len(t.get('steps_done',[]))} خطوة · {len(t.get('files_touched',[]))} ملف"
    if name == "task_update":
        return "📝 saved"
    if name == "task_complete":
        return "✅ task completed"
    if name == "was_file_read":
        info = result.get("info")
        if not info:
            return "جديد — اقرأ الملف"
        return ("✓ نفس النسخة — لا تعيد القراءة" if info.get("unchanged") else "⚠️ تغيّر — أعد القراءة")
    return None


def memory_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name == "active_tasks":
        out = []
        for t in result.get("tasks", []):
            out.append(f"  📋 {t.get('title','')[:70]} (#{t.get('id','')[:8]})")
            steps = t.get("steps_done", [])
            if steps:
                out.append(f"     last: {steps[-1].get('summary','')[:80]}")
        return "\n".join(out)
    if name == "task_resume":
        t = result.get("task", {})
        out = [
            f"📋 {t.get('title')}",
            f"🎯 {t.get('goal','—')[:200]}",
            f"📊 status: {t.get('status')} · {len(t.get('steps_done',[]))} steps",
        ]
        for s in t.get("steps_done", [])[-5:]:
            out.append(f"  ✓ {s.get('summary','')[:100]}")
        if t.get("blockers"):
            out.append(f"🚧 blockers: {' · '.join(t['blockers'])}")
        return "\n".join(out)
    return None


MEMORY_PROMPT_RULES = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 ذاكرة المشروع — استمرارية بين المحادثات
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 **القاعدة #1**: أول استدعاء في كل محادثة جديدة لازم يكون:
   → active_tasks()

   لو رجعت مهام نشطة → لا تبدأ من الصفر! استدعِ task_resume(task_id)
   واكمل من المكان اللي وقفت عنده.

📋 سير العمل الكامل:

  ١. أول رسالة في محادثة: active_tasks() — هل في مهمة معلّقة؟
       • لو نعم: task_resume(id) → اقرأ steps_done + files_touched + blockers
       • لو لا: استمر طبيعي

  ٢. لما المالك يطلب شي جديد:
       → task_start(title='...', goal='...') — تحصل task_id
       → احفظ الـtask_id في الذاكرة الذاتية للمحادثة

  ٣. بعد كل خطوة كبيرة (read_file/edit_file/git_push/إلخ):
       → task_update(task_id, step='عدّلت X', file_touched='Y')
       → عشان لو الجلسة انتهت، الذكاء التالي يعرف وين وصلت

  ٤. قبل أي read_file على ملف كبير:
       → was_file_read(file_path) — لو unchanged، **لا تقرأ مرة ثانية** (وفّر tokens)

  ٥. لما تنهي المهمة:
       → task_complete(task_id, summary='النتيجة النهائية')

💰 التوفير: لو الذكاء يتذكر إنه قرأ AdminAutoCoder.js قبل، يوفّر ~4000 token كل مرة.

⚠️ **المالك يلاحظ** إذا الذكاء يعيد قراءة نفس الشي. لا تعيدها.
"""
