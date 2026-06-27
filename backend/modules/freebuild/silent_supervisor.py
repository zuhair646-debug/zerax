"""
👁️ Silent Supervisor — automatic detection of "AI is stuck" patterns,
silent injection of corrective guidance into the AI's context so it learns
and stops repeating mistakes.

The owner's directive (Arabic, Saudi): when the AI gets stuck in a loop or
keeps failing on the same task, **don't bother the user** — automatically
detect it and silently nudge the AI back on track. The AI must LEARN from
the correction so it doesn't repeat. Goal: lower error rate, raise
independence, lower reliance on the operator.

How it works:
  1. Every tool call result is fed through `record_tool_event()`.
  2. The supervisor builds a sliding window of the last N events.
  3. Heuristics detect 3 stuck patterns:
       a) Same tool failed 3+ times in a row.
       b) Same destructive action (e.g. write_full_html with same payload)
          repeated 3+ times.
       c) AI emitted "stuck" sentinels in its text (e.g. "I cannot", "ما أقدر",
          "أعتذر، لا أستطيع").
  4. When a pattern fires, `build_supervisor_injection()` produces an
     Arabic guidance string that the chat loop injects as a SYSTEM tool
     result on the next turn — invisible to the customer.
  5. The correction is also persisted to `ai_learned_lessons` collection
     so it's surfaced in the AI's system prompt on future turns.

This is deliberately small + dependency-free. The chat loop only needs to
call `record_tool_event` + `maybe_intervene`.
"""
from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

log = logging.getLogger("zenrex.silent_supervisor")

# Sentinel phrases that mean the AI is giving up.
_STUCK_PHRASES_AR = (
    "أعتذر، لا أستطيع",
    "ما أقدر",
    "غير قادر",
    "لم أستطع",
    "I cannot",
    "I'm unable",
    "I am unable",
    "I'm stuck",
    "stuck in a loop",
    "I apologize, but I can't",
)

_WINDOW_SIZE = 12       # last N events kept per session
_FAIL_THRESHOLD = 3     # 3 consecutive failures of the same tool → intervene
_REPEAT_THRESHOLD = 3   # 3 identical (tool, payload-hash) → intervene


class SupervisorState:
    """Per-session sliding window of tool events. Cheap, in-memory only."""

    __slots__ = ("events", "interventions_this_turn", "intervention_count_total")

    def __init__(self):
        self.events: Deque[Dict[str, Any]] = deque(maxlen=_WINDOW_SIZE)
        self.interventions_this_turn: int = 0
        self.intervention_count_total: int = 0


def record_tool_event(state: SupervisorState, name: str, args: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Push one tool call + result onto the rolling window."""
    if state is None:
        return
    try:
        ok = bool((result or {}).get("ok", True))
        err = (result or {}).get("error") if not ok else None
        # Compact payload fingerprint to detect duplicate calls.
        import hashlib
        try:
            import json as _json
            payload_str = _json.dumps(args or {}, sort_keys=True, ensure_ascii=False)[:1200]
        except Exception:
            payload_str = str(args)[:1200]
        h = hashlib.sha1(payload_str.encode("utf-8")).hexdigest()[:10]
        state.events.append({
            "name": name,
            "payload_hash": h,
            "ok": ok,
            "error": (err or "")[:200] if err else None,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        log.debug(f"[supervisor] record_event error: {e}")


def record_assistant_text(state: SupervisorState, text: str) -> None:
    """Detect explicit give-up phrases in the model's text."""
    if state is None or not text:
        return
    txt = (text or "").lower()
    for needle in _STUCK_PHRASES_AR:
        if needle.lower() in txt:
            state.events.append({
                "name": "_assistant_text",
                "payload_hash": "give_up",
                "ok": False,
                "error": f"sentinel:{needle}",
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            return


def detect_stuck_pattern(state: SupervisorState) -> Optional[Dict[str, Any]]:
    """Return a {pattern, details} dict if the AI looks stuck, else None."""
    if state is None or len(state.events) < 2:
        return None

    # 3) Explicit give-up text — check FIRST so it fires on the first occurrence
    # (no minimum event count for this signal).
    for e in reversed(list(state.events)[-4:]):
        if e["name"] == "_assistant_text" and e.get("payload_hash") == "give_up":
            return {
                "pattern": "assistant_gave_up",
                "trigger": e.get("error"),
            }

    if len(state.events) < _FAIL_THRESHOLD:
        return None

    recent = list(state.events)[-_FAIL_THRESHOLD:]
    # 1) Same tool failing 3 times in a row.
    if all(not e["ok"] for e in recent) and len(set(e["name"] for e in recent)) == 1:
        name = recent[0]["name"]
        errs = [e.get("error") for e in recent if e.get("error")]
        return {
            "pattern": "repeated_tool_failure",
            "tool_name": name,
            "errors": errs,
            "count": len(recent),
        }

    # 2) Same exact tool call (name + payload hash) repeated 3+ times.
    last3 = list(state.events)[-_REPEAT_THRESHOLD:]
    if len(set((e["name"], e["payload_hash"]) for e in last3)) == 1 and last3[0]["name"] != "_assistant_text":
        return {
            "pattern": "loop_same_call",
            "tool_name": last3[0]["name"],
            "payload_hash": last3[0]["payload_hash"],
            "count": len(last3),
        }

    return None


def build_supervisor_injection(pattern: Dict[str, Any], project_state: Dict[str, Any]) -> str:
    """Produce a strict Arabic guidance message that will be injected as a
    tool-result on the next turn. The AI sees it as system feedback and
    must adjust its strategy."""
    pat = pattern.get("pattern")
    if pat == "repeated_tool_failure":
        tool = pattern.get("tool_name", "?")
        errs = pattern.get("errors") or []
        last_err = (errs[-1] if errs else "") or "غير معروف"
        return (
            "🛑 **مُراقب تلقائي (Silent Supervisor)** — اكتشفت أنك فشلت "
            f"{pattern.get('count', 3)} مرات متتالية على نفس الأداة `{tool}`.\n"
            f"آخر خطأ: «{last_err}»\n\n"
            "⚠️ **توقّف عن تكرار نفس المحاولة.** بدلاً من الإصرار على نفس النهج:\n"
            "1) إقرأ الخطأ بتمعّن — هل هو خطأ صلاحية، صلاحية API، شكل بيانات، أم timeout؟\n"
            "2) إذا كان مفتاح/توكن مفقود → استخدم `request_credential` لطلبه من العميل.\n"
            "3) إذا كان حجم/JSON/شكل → استخدم أداة تحقّق أبسط أولاً (مثل `list_pages` "
            "أو `read_current_html`) لفهم الحالة قبل التعديل.\n"
            "4) إذا فشلت كل المحاولات → استخدم `troubleshoot_agent` للحصول على RCA "
            "متخصص.\n\n"
            "🧠 **القاعدة التي يجب أن تتعلمها:** بعد فشلين متتاليين، غيّر النهج "
            "بدل ما تكرر نفس الأمر."
        )
    if pat == "loop_same_call":
        tool = pattern.get("tool_name", "?")
        return (
            "🔁 **مُراقب تلقائي** — لاحظت أنك استدعيت نفس الأداة "
            f"(`{tool}`) بنفس البيانات بالضبط {pattern.get('count', 3)} مرات.\n"
            "هذا لوب صريح. **اخرج منه فوراً:**\n"
            "• إذا كنت تنتظر تأكيد → الأداة الناجحة أول مرة لا تُعاد.\n"
            "• إذا كنت تعدّل HTML → ربما الـ snapshot القديم نفسه الجديد. استخدم "
            "`read_current_html` ثم قارن قبل إعادة الكتابة.\n"
            "• إذا اعتقدت أنه فشل → افحص `result.ok` الفعلي — قد يكون نجح وأنت لم تنتبه."
        )
    if pat == "assistant_gave_up":
        return (
            "🚧 **مُراقب تلقائي** — قلت إنك «لا تستطيع» أو شيئاً مشابهاً.\n"
            "هذا غير مقبول. أنت تملك 90+ أداة. **أي مهمة تتعلق بهذا المشروع لديك "
            "أداة تنفّذها.** قبل أن تستسلم:\n"
            "• استخدم `list_pages` لمعرفة ما لديك.\n"
            "• استخدم `read_current_html` لفحص الكود.\n"
            "• استخدم `audit_html` لاكتشاف المشاكل.\n"
            "• استخدم `web_search` للبحث عن حلول.\n"
            "• استخدم `troubleshoot_agent` للحصول على مساعدة متخصصة.\n\n"
            "إذا فعلاً لا توجد أداة (وهذا نادر جداً) — اطلب من العميل بوضوح ما تحتاجه."
        )
    return ""


async def persist_lesson(db, project_id: Optional[str], lesson: str, pattern: Dict[str, Any]) -> None:
    """Save the lesson so future sessions can reference it via `recall`.

    Stored in `ai_learned_lessons` with project scope. The AI's system prompt
    (assembled per-turn) injects the latest 5 lessons so the model literally
    "remembers" past mistakes without the owner having to retrain it.
    """
    if db is None:
        return
    try:
        await db.ai_learned_lessons.insert_one({
            "project_id": project_id,
            "pattern": pattern.get("pattern"),
            "details": pattern,
            "guidance_ar": lesson[:2000],
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        log.debug(f"[supervisor] persist_lesson failed: {e}")


async def recent_lessons_for_prompt(db, project_id: Optional[str], limit: int = 5) -> List[str]:
    """Fetch the most recent lessons for this project + global ones.
    Used by freebuild_agent to enrich the system prompt."""
    if db is None:
        return []
    try:
        cursor = db.ai_learned_lessons.find(
            {"$or": [{"project_id": project_id}, {"project_id": None}]},
            {"_id": 0, "guidance_ar": 1, "pattern": 1, "ts": 1},
        ).sort("ts", -1).limit(limit)
        out: List[str] = []
        async for doc in cursor:
            txt = doc.get("guidance_ar")
            if txt:
                out.append(txt)
        return out
    except Exception as e:
        log.debug(f"[supervisor] recent_lessons failed: {e}")
        return []
