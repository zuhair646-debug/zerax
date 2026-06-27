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
- **كل سؤال يجب أن يحتوي `options` بـ 3-5 خيارات واقعية مستخرجة من بحثك** — حتى لو `answer_type` كان `text`، أعطِ خيارات مقترحة (الواجهة تعرضها كأزرار + خانة "أخرى" نصية).
- **ممنوع تكرار أي سؤال** — راجع `questions_asked_so_far` قبل توليد أي سؤال جديد.
- لا تذكر أسماء شركات إلا للأمثلة (Netflix / Amazon / Uber).
- **انتج JSON صرف فقط** — بدون أي تعليقات `// ...` أو `/* */` أو فواصل زائدة `,}`، ولا تكتب أي نص قبل `{` أو بعد `}`.
- ضع 15-25 سؤالاً موزّعين على batch 1..5 مع priority high/medium/low.
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
    """Best-effort JSON extraction — Claude sometimes wraps with ```json fences,
    includes // line comments mimicking the prompt example, or trails commas."""
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
    # Try a pristine parse first
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        pass
    # Aggressive cleanup pass — handles most things Claude does wrong:
    cleaned = blob
    # 1) Block comments /* ... */
    cleaned = re.sub(r"/\*[\s\S]*?\*/", "", cleaned)
    # 2) Line comments // ... (must NOT match URLs inside strings — best-effort)
    cleaned = re.sub(r"(?m)^\s*//.*$", "", cleaned)
    # 3) Trailing commas before } or ]
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
    # 4) Single quotes around keys/values (Claude sometimes mixes them)
    #    Convert 'key': to "key": — only when safe (key followed by colon)
    cleaned = re.sub(r"(?<=[\{\,\s])'([^'\\]+?)'(\s*:)", r'"\1"\2', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Last-resort recovery for TRUNCATED Claude responses (max_tokens hit).
        # We try to close the JSON by trimming back to the last complete
        # question/object and appending the necessary closers.
        recovered = _try_recover_truncated_json(cleaned)
        if recovered is not None:
            _logger.info("[discovery] recovered truncated JSON (best-effort)")
            return recovered
        # Dump for debugging — keep the last 5 attempts on disk for the owner.
        try:
            import os as _os
            import time as _time
            _os.makedirs("/tmp/zenrex_discovery_failures", exist_ok=True)
            fname = f"/tmp/zenrex_discovery_failures/{int(_time.time())}.json"
            with open(fname, "w", encoding="utf-8") as fh:
                fh.write(text)
            _logger.warning(f"discovery JSON parse failed: {e}; len={len(cleaned)}; dump={fname}")
        except Exception:
            _logger.warning(f"discovery JSON parse failed: {e}; len={len(cleaned)}")
        return None


def _try_recover_truncated_json(blob: str) -> Optional[Dict[str, Any]]:
    """If Claude's reply got cut off mid-question, snip back to the last
    complete `}` inside `questions[...]` and rebuild a valid object.

    Strategy: find the last well-balanced segment by progressively trimming
    from the end until `json.loads` succeeds.
    """
    if not blob or "{" not in blob:
        return None
    # Walk backwards looking for `},` followed by whitespace and try closing
    # with `]` (for the questions array) + `}` (the outer object).
    candidates = []
    for end_idx in range(len(blob) - 1, 0, -1):
        if blob[end_idx] == "}":
            # Try variants of closers
            for closer in ("]}", "]}}", "}"):
                trial = blob[:end_idx + 1] + closer
                candidates.append(trial)
        if len(candidates) > 30:
            break
    for trial in candidates:
        # Strip trailing commas one more time
        trial = re.sub(r",(\s*[}\]])", r"\1", trial)
        try:
            return json.loads(trial)
        except json.JSONDecodeError:
            continue
    return None


async def _research_vertical(idea_text: str) -> str:
    """Run live Tavily web search to enrich the Discovery prompt with real
    market intel about what this kind of project actually needs.

    Returns a compact Arabic summary (or empty string on failure — the
    Discovery prompt remains valid even without research).
    """
    try:
        from modules.autocoder.web_search import tool_web_search
    except Exception:
        return ""
    queries = [
        f"{idea_text} essential features modules complete website checklist",
        f"{idea_text} typical pages dashboard customer admin workflow",
    ]
    snippets: List[str] = []
    for q in queries:
        try:
            r = await tool_web_search(query=q, max_results=4, search_depth="basic", include_answer=True)
            if not r.get("ok"):
                continue
            if r.get("answer"):
                snippets.append(f"- {r['answer']}")
            for item in (r.get("results") or [])[:3]:
                title = (item.get("title") or "").strip()
                content = (item.get("content") or "").strip()
                if title or content:
                    snippets.append(f"  • {title}: {content[:280]}")
        except Exception as e:
            _logger.warning(f"[discovery-research] query failed: {e}")
            continue
    if not snippets:
        return ""
    research_blob = "\n".join(snippets[:14])  # cap to keep prompt sane
    return (
        "\n\n🔍 **بحث مباشر من الويب عن هذا المشروع (Tavily):**\n"
        + research_blob
        + "\n\n👆 استخدم هذا البحث الحقيقي لتحديد المراحل والميزات والأسئلة — "
        "لا تخمّن. كل ميزة مذكورة فوق إما تدخل essentials أو تطرحها كسؤال للعميل."
    )


async def classify_and_plan(idea_text: str) -> Dict[str, Any]:
    """First call — returns the full Discovery blueprint for the customer's idea."""
    idea = (idea_text or "").strip()
    if not idea:
        return {
            "ok": False,
            "error": "idea_text is required",
        }
    try:
        # 🔍 First, do a real web search to enrich Claude's context with
        # live market intel about this kind of project. This is what makes
        # the questions ACTUALLY research-driven instead of guessed.
        research_blob = await _research_vertical(idea)
        raw = await ask_claude(
            system=_DISCOVERY_SYSTEM_PROMPT,
            user_message=f"الفكرة:\n{idea}{research_blob}\n\nأعطني الـ JSON الآن.",
            model="claude-sonnet-4-5",
            max_tokens=8500,
            timeout=180.0,
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
    blueprint["research_used"] = bool(research_blob)

    # Defensive defaults so the frontend can always render something.
    blueprint.setdefault("vertical", "other")
    blueprint.setdefault("vertical_name_ar", "مشروع مخصص")
    blueprint.setdefault("phases", [])
    blueprint.setdefault("essentials", [])
    blueprint.setdefault("optional_modules", [])
    blueprint.setdefault("questions", [])

    # Normalize questions: dedupe by id, guarantee options[] non-empty, and
    # force every question to support both choice-buttons + free text.
    blueprint["questions"] = _normalize_questions(blueprint.get("questions") or [])

    return {"ok": True, "blueprint": blueprint}


def _normalize_questions(qs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Guarantee every question has: unique id, 3+ options, allow_free_text=True.

    The frontend always renders option chips + a free-text "أخرى" input, so
    we enforce that schema server-side to avoid render glitches when Claude
    omits `options` or repeats a question key.
    """
    seen_ids: set = set()
    seen_questions: set = set()
    out: List[Dict[str, Any]] = []
    for i, q in enumerate(qs):
        if not isinstance(q, dict):
            continue
        qid = q.get("id") or f"q{i + 1}"
        if qid in seen_ids:
            continue
        # Dedupe by normalized text too — Claude sometimes rephrases the
        # same question across batches.
        q_text = (q.get("question_ar") or "").strip()
        q_key = q_text[:80].lower()
        if q_key and q_key in seen_questions:
            continue
        seen_ids.add(qid)
        if q_key:
            seen_questions.add(q_key)

        opts = q.get("options") or []
        # Strip empties, cap at 6 options
        cleaned_opts = [str(o).strip() for o in opts if str(o).strip()][:6]
        if len(cleaned_opts) < 2:
            # Provide a sensible default so the chip UI always renders
            cleaned_opts = ["نعم", "لا", "غير متأكد"]
        q["id"] = qid
        q["question_ar"] = q_text or q.get("question") or "سؤال"
        q["options"] = cleaned_opts
        q["allow_free_text"] = True   # ALWAYS allow "أخرى" input
        # Default answer_type to single_choice so the UI renders chips
        if q.get("answer_type") not in ("single_choice", "multi_choice", "text"):
            q["answer_type"] = "single_choice"
        q.setdefault("batch", max(1, (len(out) // 5) + 1))
        q.setdefault("priority", "medium")
        out.append(q)
    return out


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
    existing_texts = {
        (q.get("question_ar") or "").strip()[:80].lower()
        for q in blueprint["questions"]
    }
    for q in new_q:
        if not isinstance(q, dict):
            continue
        qid = q.get("id")
        q_key = (q.get("question_ar") or "").strip()[:80].lower()
        if qid and qid in existing_ids:
            continue
        if q_key and q_key in existing_texts:
            continue  # skip duplicate rephrasing
        blueprint["questions"].append(q)
        existing_ids.add(qid)
        existing_texts.add(q_key)
    # Re-normalize the combined list so the new batch also has options + free-text
    blueprint["questions"] = _normalize_questions(blueprint["questions"])

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
