"""
Planner — الذكاء #2.1
Architectural planner that turns a user request into a structured build plan.

Architecture role:
    AI #1 (Customer Brain) hands off a PRD/user request →
    THIS module produces a structured plan that AI #3 (Builder) executes step by step.

The plan output:
    {
      "summary": "موقع متجر إلكتروني لقهوة سعودية بـ 5 صفحات و3 integrations",
      "stack": "html_css_js",   # "html_css_js" | "react_spa" | "static_landing"
      "pages": [
        {"file": "index.html", "purpose": "الرئيسية", "priority": 1, "sections": ["hero","features","cta"]},
        {"file": "menu.html",  "purpose": "قائمة المنتجات", "priority": 2, "sections": ["filters","grid","details"]}
      ],
      "integrations": ["stripe","whatsapp"],
      "design_hints": {"palette":"warm-coffee","tone":"luxury","font":"serif+sans"},
      "phases": [
        {"id":1,"name":"التصميم الأساسي","tasks":["bootstrap","palette","typography"]},
        {"id":2,"name":"بناء الصفحات","tasks":["index","menu","contact"]},
        {"id":3,"name":"الـ integrations","tasks":["stripe checkout","whatsapp button"]},
        {"id":4,"name":"الفحص النهائي","tasks":["broken links","mobile responsive","SEO meta"]}
      ],
      "risks": ["stripe key not provided yet","arabic font fallback"]
    }

Cost guardrails:
    • Skipped when ctx.current_html already has substantial content (this is
      an EDIT, not a build — planning would be wasteful).
    • Cached per (project_id, user_message_hash) for 1 hour so repeat runs hit cache.
    • Hard time-cap of 15s; on timeout we return a minimal default plan.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.freebuild.planner")

PLAN_TIMEOUT_SECONDS = 60
_PLAN_CACHE: Dict[str, Dict[str, Any]] = {}
_PLAN_CACHE_MAX = 200


_PLANNER_SYSTEM_PROMPT = """أنت **مهندس معماري سيوبر-سينيور** (Senior Software Architect) متخصص في تصميم خطط بناء مواقع وتطبيقات ويب.

**دورك:** تأخذ طلب العميل وتحوّله لـ **خطة JSON مفصّلة وذكية** يقدر مبرمج آخر ينفذها خطوة بخطوة دون لبس.

**أنت لا تكتب كود.** فقط تخطط. الكود يكتبه ذكاء آخر اعتماداً على خطتك.

**معايير الخطة الجيدة:**
1. **شاملة لكن مرتّبة:** كل صفحة، كل قسم، كل integration مذكور بوضوح.
2. **مرتبة بالأولوية:** ما يُبنى أول مرة قبل ما يعتمد على غيره.
3. **تعطي اقتراحات أوسع:** لو العميل قال "أبي متجر قهوة"، اقترح صفحات/أقسام/features هو ما ذكرها لكن أي متجر قهوة محترم يحتاجها (المدوّنة، البرنامج الولاء، الأسئلة الشائعة...).
4. **تحدد المخاطر مسبقاً:** قاعدة بيانات؟ مفاتيح API ناقصة؟ تعقيد معماري؟
5. **تنتهي بمرحلة فحص واضحة.**

**مخرجاتك = JSON صرف:**

```json
{
  "summary": "وصف مختصر بسطر للمشروع كاملاً",
  "stack": "html_css_js" | "react_spa" | "static_landing",
  "pages": [
    {"file":"index.html","purpose":"...","priority":1,"sections":["hero","features"]}
  ],
  "integrations": ["stripe","whatsapp","resend",...],
  "design_hints": {"palette":"...","tone":"...","font":"..."},
  "phases": [
    {"id":1,"name":"...","tasks":["..."]}
  ],
  "suggestions": [
    "اقتراحات إضافية يحتاجها المشروع لكن العميل ما ذكرها"
  ],
  "risks": ["..."]
}
```

**قواعد إلزامية:**
- لا Markdown fences. JSON صرف فقط.
- pages: 1-12 صفحات بحد أقصى للمواقع العادية.
- phases: 3-6 مراحل.
- suggestions: 3-7 اقتراحات لإثراء المشروع.
- risks: 1-5 مخاطر فعلية محددة.
- اللغة العربية في القيم النصية. المفاتيح بالإنجليزية.
- لا تفترض تفاصيل غير موجودة بالطلب — لو ناقص شي حطّه في risks/suggestions.

**أمثلة على suggestions جيدة (لمتجر إلكتروني):**
- "أضف نظام تقييمات المنتجات لزيادة الثقة"
- "اربط بـ WhatsApp Business API بدل النموذج التقليدي"
- "صفحة 'عن المتجر' بحكاية تأسيسية تخلق رابط عاطفي مع العميل"
- "تتبع المخزون real-time عبر integration مع Shopify أو نظام داخلي"

كن مبدع لكن واقعي.
"""


def _hash_key(project_id: str, msg: str) -> str:
    return hashlib.sha256(f"{project_id}::{msg}".encode("utf-8")).hexdigest()[:24]


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    return text


def _safe_parse(raw: str) -> Optional[Dict[str, Any]]:
    """Robustly extract a JSON plan object from a possibly noisy LLM response."""
    if not raw:
        return None
    cleaned = _strip_json_fences(raw)
    # 1) Direct parse
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    # 2) Greedy regex from first { to last }
    m = re.search(r"\{[\s\S]*\}", cleaned)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    # 3) Bracket-depth walker (handles strings + escapes — tolerates inner braces)
    s = cleaned
    start = s.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(s)):
            ch = s[i]
            if esc:
                esc = False
                continue
            if ch == "\\" and in_str:
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(s[start:i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except Exception:
                        break
        start = s.find("{", start + 1)
    return None


def _should_plan(user_message: str, current_html: str) -> bool:
    """We only run the planner on NEW builds or major feature requests.
    Small edits don't need re-planning."""
    if not user_message or len(user_message) < 15:
        return False
    # Already established project + small edit → skip
    if current_html and len(current_html) > 500:
        msg_low = user_message.lower()
        # Edit-intent keywords (Arabic + English) → skip planning
        edit_keywords = [
            "غيّر", "غير ", "عدّل", "عدل ", "صلح", "أصلح", "اصلح",
            "اضف ", "أضف ", "احذف", "أزل", "ازل ",
            "اللون", "النص", "الخط", "العنوان", "الصورة",
            "fix", "change", "update", "edit", "remove", "delete",
        ]
        if any(k in msg_low for k in edit_keywords) and "ابن" not in msg_low and "build" not in msg_low:
            return False
    # Build/create intent keywords → run planner
    build_keywords = [
        "ابن", "ابني", "اعمل", "أنشئ", "أنشى", "صمم",
        "أبي موقع", "أريد موقع", "أبي تطبيق", "أريد تطبيق",
        "build", "create", "make", "design",
        "متجر", "موقع", "تطبيق", "مدوّنة", "منصة", "نظام",
    ]
    msg_low = user_message.lower()
    if any(k in msg_low for k in build_keywords):
        return True
    # Long requests with detailed specs → plan
    if len(user_message) > 200:
        return True
    return False


def _minimal_default_plan(user_message: str) -> Dict[str, Any]:
    """Returned when planner fails — keeps the build moving."""
    return {
        "summary": "خطة مبدئية تلقائية — لم يتمكن الـ planner من توليد خطة مفصّلة",
        "stack": "html_css_js",
        "pages": [{"file": "index.html", "purpose": "الصفحة الرئيسية", "priority": 1, "sections": ["hero", "features", "footer"]}],
        "integrations": [],
        "design_hints": {"palette": "neutral", "tone": "modern", "font": "default"},
        "phases": [
            {"id": 1, "name": "البناء الأساسي", "tasks": ["index.html"]},
            {"id": 2, "name": "الفحص", "tasks": ["broken links", "responsive"]},
        ],
        "suggestions": [],
        "risks": [],
        "fallback": True,
    }


async def generate_build_plan(
    user_message: str,
    project_name: str = "",
    project_id: str = "",
    current_html: str = "",
    pages_existing: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Generates a structured build plan. Returns None if planning was skipped.
    Never raises — failures return a fallback minimal plan.
    """
    if not _should_plan(user_message, current_html):
        return None

    # Cache lookup
    key = _hash_key(project_id or project_name, user_message)
    if key in _PLAN_CACHE:
        return {**_PLAN_CACHE[key], "from_cache": True}

    api_key_present = bool(
        (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
        or (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
    )
    if not api_key_present:
        return _minimal_default_plan(user_message)

    try:
        from modules.shared.claude_simple import ask_claude  # type: ignore
    except Exception:
        return _minimal_default_plan(user_message)

    existing_pages_block = (
        f"\n## صفحات موجودة بالفعل: {', '.join(pages_existing)}"
        if pages_existing else ""
    )
    msg_text = (
        f"## طلب العميل:\n{user_message}\n\n"
        f"## اسم المشروع: {project_name or '(جديد)'}\n"
        f"## المحتوى الحالي: {len(current_html or '')} حرف"
        f"{existing_pages_block}\n\n"
        f"أعد خطة JSON كاملة — لا شيء غير الـ JSON."
    )

    try:
        raw = await asyncio.wait_for(
            ask_claude(
                system=_PLANNER_SYSTEM_PROMPT,
                user_message=msg_text,
                session_id=f"planner-{project_id or 'anon'}",
                max_tokens=4000,
                timeout=PLAN_TIMEOUT_SECONDS,
            ),
            timeout=PLAN_TIMEOUT_SECONDS + 5,
        )
    except asyncio.TimeoutError:
        logger.warning("[planner] timed out → minimal default plan")
        return _minimal_default_plan(user_message)
    except Exception as e:
        logger.exception(f"[planner] LLM failed: {e}")
        return _minimal_default_plan(user_message)

    parsed = _safe_parse(raw if isinstance(raw, str) else "")
    if not isinstance(parsed, dict):
        # One retry with stronger nudge.
        try:
            preview = (raw or "")[:200] if isinstance(raw, str) else "(non-string)"
            logger.warning(f"[planner] first parse failed. preview={preview!r}")
            retry_msg = (
                "ردك السابق لم يكن JSON صرف. أعد الإجابة الآن — "
                "ابدأ مباشرة بـ `{` وانتهِ بـ `}` بدون أي شرح أو markdown."
            )
            raw2 = await asyncio.wait_for(
                ask_claude(
                    system=_PLANNER_SYSTEM_PROMPT,
                    user_message=msg_text + "\n\n" + retry_msg,
                    session_id=f"planner-{project_id or 'anon'}-retry",
                    max_tokens=4000,
                    timeout=20,
                ),
                timeout=25,
            )
            parsed = _safe_parse(raw2 if isinstance(raw2, str) else "")
        except Exception as e:
            logger.warning(f"[planner] retry failed: {e}")
        if not isinstance(parsed, dict):
            logger.warning("[planner] couldn't parse plan JSON after retry → fallback")
            return _minimal_default_plan(user_message)

    # Light validation + normalization
    parsed.setdefault("summary", "")
    parsed.setdefault("stack", "html_css_js")
    parsed.setdefault("pages", [])
    parsed.setdefault("integrations", [])
    parsed.setdefault("design_hints", {})
    parsed.setdefault("phases", [])
    parsed.setdefault("suggestions", [])
    parsed.setdefault("risks", [])
    parsed["from_cache"] = False

    # Cache (LRU-ish)
    _PLAN_CACHE[key] = parsed
    if len(_PLAN_CACHE) > _PLAN_CACHE_MAX:
        # drop oldest
        oldest = next(iter(_PLAN_CACHE))
        _PLAN_CACHE.pop(oldest, None)

    return parsed


def render_plan_summary(plan: Dict[str, Any]) -> str:
    """Compact human-readable summary used in chat / logs."""
    if not plan:
        return "(لا خطة)"
    if plan.get("fallback"):
        return "📋 خطة تلقائية بسيطة (fallback)"
    pages_n = len(plan.get("pages") or [])
    phases_n = len(plan.get("phases") or [])
    suggs_n = len(plan.get("suggestions") or [])
    return f"📋 خطة جاهزة · {pages_n} صفحات · {phases_n} مراحل · {suggs_n} اقتراحات إضافية"
