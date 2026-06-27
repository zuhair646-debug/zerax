"""
🤝 Auto-E1 Reviewer — automatic "senior engineer review" that kicks in
silently within ~30 seconds when the AI keeps failing despite the Silent
Supervisor's interventions.

Owner directive (Arabic, Saudi): when the AI gets stuck and the Silent
Supervisor has nudged it twice without success, **automatically** invoke
E1's review pattern — analyze the failure, propose ONE concrete fix
(NOT a full rewrite), and persist a high-priority lesson so the model
stops repeating the mistake. The operator gets an email summary; the
customer never sees the intervention.

This is NOT a code-changing agent. It only produces:
  • A precise diagnosis (one paragraph)
  • A one-line corrective lesson (saved with priority="high")
  • The action the AI should take NEXT

The lesson goes through the same retrieval pipeline as everything else,
so even if the AI fails again later on a related task, the lesson surfaces.

Decision flow:
   Supervisor intervention #1  → record, inject standard nudge
   Supervisor intervention #2  → record, inject standard nudge
   Supervisor intervention #3  → 30s window for operator to react
                                  → if no operator action: Auto-E1 fires
                                  → review runs (Claude Sonnet 4.5)
                                  → high-priority lesson saved
                                  → next turn injects it
                                  → escalation email to operator with summary
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger("zenrex.auto_e1")

_AUTO_E1_THRESHOLD = 3   # # of supervisor interventions before auto-review fires
_REVIEW_TIMEOUT = 90.0   # seconds — Claude review budget


async def should_invoke_auto_e1(supervisor_state: Any) -> bool:
    """True when the silent supervisor has intervened enough that we need
    a smarter "senior engineer" pass."""
    if supervisor_state is None:
        return False
    n = getattr(supervisor_state, "intervention_count_total", 0) or 0
    return n >= _AUTO_E1_THRESHOLD


_E1_REVIEW_PROMPT = """أنت E1 — مهندس برمجيات أول داخل منصة Zenrex. مهمتك:
الذكاء الصناعي العامل (Claude Sonnet 4.5) يحاول إنجاز مهمة في مشروع موقع/تطبيق
عند العميل، لكن **تعثّر 3 مرات على الأقل** رغم المحاولات التلقائية للمراقب
الصامت (Silent Supervisor).

سأعطيك:
1) قائمة آخر الاستدعاءات التي فشل فيها (اسم الأداة، الخطأ، عدد التكرار).
2) آخر نص من الذكاء.
3) سياق المشروع (الصفحات الحالية + الـ Discovery blueprint إن وُجد).

مطلوب منك **3 مخرجات فقط** كـ JSON صرف، بدون أي نص قبله أو بعده:

{
  "diagnosis_ar": "سبب جذري واحد بجملتين كحد أقصى — لماذا فشل الذكاء؟",
  "lesson_ar": "درس واحد قصير وعملي (≤ 250 حرف) سيُحقن في system prompt
                للمحاولة القادمة. صياغة آمرة مباشرة. مثال: 'قبل استخدام
                deploy_to_vercel، تأكد من استدعاء request_credential
                ('vercel_token', ...) أولاً وانتظار حفظ التوكن.'",
  "next_action_ar": "خطوة واحدة محددة على الذكاء تنفيذها فوراً بدل تكرار الفشل."
}

قواعد:
- لا تقترح إعادة كتابة المشروع.
- لا تقترح استبدال أدوات بأخرى لم تُذكر.
- لا تخمّن — لو السياق مبهم، الـ diagnosis يقول 'سياق غير كافٍ' والـ lesson
  يقول 'اطلب توضيح من العميل قبل إعادة المحاولة'.
- اللغة: عربية فصحى مفهومة (يجوز خلط مع مصطلحات تقنية انجليزية).
"""


async def run_auto_e1_review(
    *,
    db,
    project_id: Optional[str],
    user_id: Optional[str],
    supervisor_events: List[Dict[str, Any]],
    last_assistant_text: str,
    project_state: Dict[str, Any],
) -> Dict[str, Any]:
    """Synchronously runs the E1 review and persists the resulting lesson.

    Returns:
      {ok, diagnosis_ar, lesson_ar, next_action_ar, lesson_id} on success,
      or {ok: False, error} on failure (e.g., Claude API down).
    """
    try:
        from modules.shared.claude_simple import ask_claude
    except Exception as e:
        return {"ok": False, "error": f"claude_unavailable: {e}"}

    # Build a compact context for Claude — keep it under 4K tokens
    failures_summary = []
    for ev in (supervisor_events or [])[-8:]:
        if ev.get("ok"):
            continue
        failures_summary.append(
            f"- tool={ev.get('name','?')} error={(ev.get('error') or '')[:140]}"
        )
    failures_blob = "\n".join(failures_summary) or "(لا توجد سجلات أخطاء واضحة)"

    pages_summary = []
    pages = (project_state or {}).get("pages") or {}
    for pname in list(pages)[:6]:
        pages_summary.append(f"  • {pname}")
    pages_blob = "\n".join(pages_summary) or "  (لا صفحات بعد)"

    user_block = (
        "🛠️ سجل آخر الاستدعاءات الفاشلة:\n"
        f"{failures_blob}\n\n"
        "💬 آخر رد من الذكاء (مقتطف):\n"
        f"«{(last_assistant_text or '')[:600]}»\n\n"
        "📂 صفحات المشروع:\n"
        f"{pages_blob}\n\n"
        "أعطني الـ JSON الآن."
    )

    try:
        raw = await ask_claude(
            system=_E1_REVIEW_PROMPT,
            user_message=user_block,
            model="claude-sonnet-4-5",
            max_tokens=1500,
            timeout=_REVIEW_TIMEOUT,
        )
    except Exception as e:
        return {"ok": False, "error": f"review_call_failed: {e}"}

    # Parse JSON (re-use the lenient stripper from discovery_brain)
    try:
        from .discovery_brain import _strip_json
        review = _strip_json(raw)
    except Exception:
        review = None
    if not review:
        return {"ok": False, "error": "review_json_parse_failed", "raw_preview": (raw or "")[:300]}

    diagnosis = (review.get("diagnosis_ar") or "").strip()
    lesson = (review.get("lesson_ar") or "").strip()
    next_action = (review.get("next_action_ar") or "").strip()
    if not lesson:
        return {"ok": False, "error": "review_missing_lesson"}

    # Save the lesson with HIGH priority so it ranks above standard ones
    lesson_text = (
        f"🛡️ **درس مراجعة E1 (تلقائي)**:\n{lesson}\n\n"
        f"_سبب: {diagnosis or 'مشكلة متكررة'}_\n"
        f"_الخطوة التالية: {next_action or 'انتظر تعليمات العميل قبل إعادة المحاولة'}_"
    )
    lesson_id = None
    try:
        from .lesson_retrieval import save_lesson
        lesson_id = await save_lesson(
            db,
            project_id=project_id,
            guidance_ar=lesson_text,
            pattern="auto_e1_review",
            priority="high",
            source="auto_e1",
            details={
                "diagnosis": diagnosis,
                "next_action": next_action,
                "trigger_user_id": user_id,
                "failures": failures_summary,
            },
        )
    except Exception as e:
        log.warning(f"[auto_e1] save_lesson failed: {e}")

    # Persist a separate audit log
    try:
        if db is not None:
            await db.ai_e1_reviews.insert_one({
                "project_id": project_id,
                "user_id": user_id,
                "diagnosis_ar": diagnosis,
                "lesson_ar": lesson,
                "next_action_ar": next_action,
                "lesson_id": lesson_id,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
    except Exception:
        pass

    return {
        "ok": True,
        "diagnosis_ar": diagnosis,
        "lesson_ar": lesson,
        "next_action_ar": next_action,
        "lesson_id": lesson_id,
    }
