"""
🧠 Discovery Brain — AI #1.5
═════════════════════════════════════════════════════════════════════
Before the Builder starts writing HTML, the Discovery Brain plays
the role of a senior product consultant. Given the customer's idea
(e.g. "أبي موقع أفلام" / "متجر إلكتروني" / "تطبيق توصيل"), it:

  1. Classifies the vertical (Arabic + English).
  2. Researches the domain — what does this kind of product NEED to
     be complete? (Admin panel? Subscriptions? Drivers panel? Maps?
     Inventory? Reviews? Ads? Multi-tenant? Localization? ...)
  3. Produces a phased Roadmap (5-10 phases) the customer can see.
  4. Splits work into Essential modules vs Optional modules.
  5. Drafts 15-25 PROGRESSIVE questions — grouped into batches of
     5 — so the customer answers them gradually instead of being
     overwhelmed by a giant form.

Every answer the customer gives is stored in `project.discovery.answers`
and the active modules update accordingly. The Builder (AI #3) later
receives the full blueprint + answers as context, so it stops
"guessing" the scope and starts executing a clear plan phase-by-phase.

This module uses Claude directly via `claude_simple` — no Emergent
proxy. Returns a JSON blueprint validated against a strict schema.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from modules.shared.claude_simple import ask_claude

_logger = logging.getLogger(__name__)


_DISCOVERY_SYSTEM_PROMPT = """أنت "مستشار منتجات Zenrex" — خبير في تحليل الأفكار وبناء خرائط طريق متكاملة.

**مهمتك:** عميل أعطاك فكرة بسيطة (مثلاً "أبي موقع أفلام") — مهمتك أن تستخرج:
1. تصنيف الـ vertical (streaming / ecommerce / saas / education / restaurant / blog / portfolio / booking / community / marketplace / fintech / healthcare / real-estate / logistics / events / nonprofit / other).
2. خارطة طريق من 5-10 مراحل (Phases) مرتبة منطقياً.
3. قائمة الميزات الأساسية (essentials — لا يقوم المنتج بدونها).
4. قائمة الميزات الاختيارية (optional — تحتاج قرار من العميل).
5. **15-25 سؤالاً متخصصاً** يساعدك تحدد الـ scope النهائي. **قسّمهم على دفعات من 5 أسئلة** ابدأها من الأهم.

**نموذج الإخراج (JSON صارم — لا نص قبل أو بعد):**
{
  "vertical": "streaming_movies",
  "vertical_name_ar": "منصة أفلام/مسلسلات",
  "vertical_summary_ar": "موقع بث محتوى مرئي بـ catalog + player + اشتراكات + لوحة إدارة...",
  "phases": [
    {"id": 1, "name_ar": "التأسيس", "desc_ar": "Auth + DB + Landing + شعار", "essential": true},
    {"id": 2, "name_ar": "الكاتالوج", "desc_ar": "قائمة الأفلام + بحث + فلترة + صفحة تفاصيل", "essential": true},
    {"id": 3, "name_ar": "المُشغّل", "desc_ar": "Player + جودات + ترجمة + ملء الشاشة", "essential": true},
    {"id": 4, "name_ar": "حسابات وقوائم", "desc_ar": "Profile + Watchlist + Continue Watching", "essential": true},
    {"id": 5, "name_ar": "الاشتراكات والدفع", "desc_ar": "Stripe + خطط شهرية + Trial", "essential": false},
    {"id": 6, "name_ar": "الإعلانات", "desc_ar": "Pre-roll + Mid-roll للمستخدمين المجانيين", "essential": false},
    {"id": 7, "name_ar": "لوحة الإدارة", "desc_ar": "رفع محتوى + إدارة عملاء + إحصائيات", "essential": true},
    {"id": 8, "name_ar": "التوصيات الذكية", "desc_ar": "AI Recommendations + Trending", "essential": false}
  ],
  "essentials": ["auth", "catalog", "player", "user_profile", "admin_panel"],
  "optional_modules": [
    {"key": "subscriptions", "name_ar": "اشتراكات شهرية مدفوعة", "depends_on": []},
    {"key": "ads", "name_ar": "إعلانات للمستخدمين المجانيين", "depends_on": []},
    {"key": "recommendations", "name_ar": "توصيات بالذكاء الصناعي", "depends_on": ["catalog"]},
    {"key": "downloads_offline", "name_ar": "تنزيل offline للجوال", "depends_on": ["pwa"]},
    {"key": "live_chat", "name_ar": "دردشة دعم فني مباشرة", "depends_on": []}
  ],
  "questions": [
    {
      "id": "q1", "batch": 1, "priority": "high",
      "question_ar": "كم نوع محتوى تبي؟ (أفلام فقط / مسلسلات / وثائقي / الكل)",
      "answer_type": "single_choice",
      "options": ["أفلام فقط", "مسلسلات فقط", "وثائقي فقط", "كل الأنواع"],
      "triggers_module": "catalog_categories",
      "default_answer": "كل الأنواع"
    },
    {
      "id": "q2", "batch": 1, "priority": "high",
      "question_ar": "نظام الدفع: اشتراك شهري / دفع لكل فيلم / مجاناً مع إعلانات / الكل؟",
      "answer_type": "single_choice",
      "options": ["اشتراك شهري", "دفع لكل فيلم", "مجاناً مع إعلانات", "خليط من الثلاثة"],
      "triggers_module": "subscriptions_or_ads"
    }
    // ... ضع 15-25 سؤالاً، مع batch 1..5 و priority high/medium/low
  ],
  "estimated_total_pages": 8,
  "estimated_build_minutes": 12,
  "complexity": "متوسط",
  "recommended_tech": ["React + FastAPI + MongoDB"],
  "notes_ar": "ملاحظات تقنية أو تجارية مفيدة للمستشار."
}

**قواعد إلزامية:**
- لا تخترع vertical إذا الفكرة غير واضحة — استخدم `"other"` واسأل سؤال توضيحي في `q1`.
- الأسئلة تكون **محددة وعملية** (لا أسئلة فلسفية)، تساعد في اتخاذ قرار تقني.
- كل سؤال له `triggers_module` يربطه بميزة في `essentials` أو `optional_modules`.
- لا تذكر أسماء شركات إلا للأمثلة (Netflix / Amazon / Uber).
- **انتج JSON فقط** — لا تكتب أي شي قبله أو بعده.
"""


_QUESTION_BATCH_FOLLOWUP_PROMPT = """العميل أجاب على دفعة الأسئلة الحالية. مهمتك:
1. اقرأ الإجابات.
2. حدّث قائمة الـ optional_modules: فعّل/ألغِ الميزات بناء على الإجابات.
3. ولّد دفعة الأسئلة التالية (5 أسئلة كحد أقصى) بناء على ما تعلمته.
4. إذا كل المعلومات الأساسية مكتملة، أعد `"ready_to_build": true`.

**نموذج الإخراج (JSON صارم):**
{
  "ready_to_build": false,
  "module_updates": {
    "ads": "disabled_by_user",
    "subscriptions": "confirmed"
  },
  "next_batch_questions": [
    {"id": "q6", "batch": 2, "priority": "high", "question_ar": "...", "answer_type": "...", "options": [...], "triggers_module": "..."}
  ],
  "summary_for_customer_ar": "ممتاز! حدّدنا أنك تبي اشتراك شهري بدون إعلانات. باقي ٥ أسئلة عشان نخلّص.",
  "progress_pct": 35
}
"""


def _strip_json(text: str) -> Optional[Dict[str, Any]]:
    """Best-effort JSON extraction — Claude sometimes wraps with ```json fences."""
    if not text:
        return None
    text = text.strip()
    # Remove fences.
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Find first { and last }.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    blob = text[start:end + 1]
    try:
        return json.loads(blob)
    except json.JSONDecodeError as e:
        _logger.warning(f"discovery JSON parse failed: {e}; len={len(blob)}")
        return None


async def classify_and_plan(idea_text: str) -> Dict[str, Any]:
    """First call — returns the full Discovery blueprint for the customer's idea."""
    idea = (idea_text or "").strip()
    if not idea:
        return {
            "ok": False,
            "error": "idea_text is required",
        }
    try:
        raw = await ask_claude(
            system=_DISCOVERY_SYSTEM_PROMPT,
            user_message=f"الفكرة:\n{idea}\n\nأعطني الـ JSON الآن.",
            model="claude-sonnet-4-5",
            max_tokens=6000,
        )
    except Exception as e:
        return {"ok": False, "error": f"claude_call_failed: {e}"}

    blueprint = _strip_json(raw)
    if not blueprint:
        return {"ok": False, "error": "discovery_json_parse_failed", "raw_preview": (raw or "")[:400]}

    # Inject server-side metadata.
    blueprint["id"] = str(uuid.uuid4())
    blueprint["created_at"] = datetime.now(timezone.utc).isoformat()
    blueprint["answers"] = {}
    blueprint["completed_batches"] = []
    blueprint["status"] = "in_discovery"  # in_discovery | ready_to_build | building | done
    blueprint["progress_pct"] = 0

    # Defensive defaults so the frontend can always render something.
    blueprint.setdefault("vertical", "other")
    blueprint.setdefault("vertical_name_ar", "مشروع مخصص")
    blueprint.setdefault("phases", [])
    blueprint.setdefault("essentials", [])
    blueprint.setdefault("optional_modules", [])
    blueprint.setdefault("questions", [])

    return {"ok": True, "blueprint": blueprint}


async def advance_discovery(
    blueprint: Dict[str, Any],
    new_answers: Dict[str, str],
) -> Dict[str, Any]:
    """After a batch of answers, ask Claude to update the blueprint + return
    the next batch of questions or signal `ready_to_build`."""
    if not blueprint:
        return {"ok": False, "error": "blueprint missing"}
    blueprint.setdefault("answers", {})
    blueprint["answers"].update(new_answers or {})

    summary_for_claude = {
        "vertical": blueprint.get("vertical"),
        "essentials": blueprint.get("essentials", []),
        "optional_modules": blueprint.get("optional_modules", []),
        "questions_asked_so_far": blueprint.get("questions", []),
        "answers_so_far": blueprint["answers"],
    }
    try:
        raw = await ask_claude(
            system=_QUESTION_BATCH_FOLLOWUP_PROMPT,
            user_message=(
                "تقدم العميل في الـ Discovery. هذي حالة المشروع الحالية:\n"
                + json.dumps(summary_for_claude, ensure_ascii=False, indent=2)
                + "\n\nأعطني الدفعة التالية من الأسئلة أو ready_to_build."
            ),
            model="claude-sonnet-4-5",
            max_tokens=3500,
        )
    except Exception as e:
        return {"ok": False, "error": f"claude_call_failed: {e}"}

    update = _strip_json(raw)
    if not update:
        return {"ok": False, "error": "discovery_advance_parse_failed", "raw_preview": (raw or "")[:400]}

    # Apply module updates.
    mod_updates = update.get("module_updates") or {}
    if mod_updates:
        for mod in blueprint.get("optional_modules", []):
            key = mod.get("key")
            if key in mod_updates:
                mod["status"] = mod_updates[key]

    # Append new questions.
    new_q = update.get("next_batch_questions") or []
    blueprint.setdefault("questions", [])
    existing_ids = {q.get("id") for q in blueprint["questions"]}
    for q in new_q:
        if q.get("id") and q["id"] not in existing_ids:
            blueprint["questions"].append(q)

    blueprint["progress_pct"] = max(
        blueprint.get("progress_pct", 0),
        int(update.get("progress_pct", 0) or 0),
    )
    if update.get("ready_to_build"):
        blueprint["status"] = "ready_to_build"
        blueprint["progress_pct"] = 100

    return {
        "ok": True,
        "blueprint": blueprint,
        "summary_for_customer_ar": update.get("summary_for_customer_ar", ""),
        "ready_to_build": bool(update.get("ready_to_build")),
    }


def render_blueprint_for_builder(blueprint: Dict[str, Any]) -> str:
    """Format the blueprint as an Arabic system-prompt snippet that the
    Builder (AI #3) can inject when generating HTML. This is what turns
    "guessing the scope" into "executing a clear plan"."""
    if not blueprint:
        return ""
    lines: List[str] = []
    lines.append("📋 **خارطة طريق المشروع (من Discovery Brain):**")
    lines.append(f"- النوع: {blueprint.get('vertical_name_ar') or blueprint.get('vertical')}")
    if blueprint.get("vertical_summary_ar"):
        lines.append(f"- ملخص: {blueprint['vertical_summary_ar']}")
    phases = blueprint.get("phases") or []
    if phases:
        lines.append("- المراحل:")
        for p in phases:
            mark = "✅" if p.get("essential") else "🟡"
            lines.append(f"  {mark} المرحلة {p.get('id')}: {p.get('name_ar')} — {p.get('desc_ar', '')}")
    ess = blueprint.get("essentials") or []
    if ess:
        lines.append(f"- ميزات أساسية: {', '.join(ess)}")
    opt = blueprint.get("optional_modules") or []
    active_opt = [m for m in opt if (m.get("status") in (None, "confirmed", "enabled"))]
    if active_opt:
        lines.append("- ميزات اختيارية مُفعّلة:")
        for m in active_opt:
            lines.append(f"  · {m.get('name_ar')} ({m.get('key')})")
    answers = blueprint.get("answers") or {}
    if answers:
        lines.append("- إجابات العميل:")
        for qid, ans in list(answers.items())[:25]:
            lines.append(f"  · {qid}: {ans}")
    lines.append(
        "⚠️ ابني المشروع وفق هذه الخطة، مرحلة-بمرحلة. لا تتجاوز أو تختصر المراحل الأساسية. "
        "إذا احتجت قرار غير موجود في الإجابات، اسأل العميل في الشات قبل البناء."
    )
    return "\n".join(lines)
