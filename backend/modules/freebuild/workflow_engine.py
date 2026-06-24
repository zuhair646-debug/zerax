"""
Workflow Engine — 4-stage build protocol for Zenrex FreeBuild.

Applies uniformly to all three AI modes (claude_only / hybrid_gpt / hybrid_glm).

STAGES (state machine, persisted in `project.workflow_state.stage`):

  1. discovery       — AI asks the 8 discovery questions ONCE per project.
                       Cannot advance until answers collected.
  2. visual_skeleton — AI builds ALL pages with cohesive visual design,
                       nav links that navigate between pages, but buttons /
                       forms are INERT (no JS handlers, no data binding).
                       Customer reviews the visual before any wiring.
  3. wiring          — AI activates buttons one page at a time, in order.
                       After each page is wired, AI asks the customer to
                       verify before moving to the next page.
  4. surgical_edit   — Default for any edit on an existing project.
                       AI makes pinpoint changes without touching unrelated
                       design or behaviour.

The engine is intentionally simple: it does NOT call any LLM. It just reads
the saved project state and emits:
  • the current stage label
  • the system-prompt addendum the AI must follow
  • the gate conditions that block premature advancement
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

# Stage identifiers (single source of truth)
STAGE_DISCOVERY = "discovery"
STAGE_VISUAL_SKELETON = "visual_skeleton"
STAGE_WIRING = "wiring"
STAGE_SURGICAL_EDIT = "surgical_edit"

VALID_STAGES = {
    STAGE_DISCOVERY,
    STAGE_VISUAL_SKELETON,
    STAGE_WIRING,
    STAGE_SURGICAL_EDIT,
}

# Discovery questions — the EXACT 8 questions the AI must ask before any
# code is written on an empty project. Each question is short and answerable
# in one or two sentences so the discovery phase doesn't drag on.
DISCOVERY_QUESTIONS: List[Dict[str, str]] = [
    {"key": "site_purpose",
     "ar": "1. ما الهدف الأساسي من الموقع؟ (متجر، خدمات، عرض أعمال، تطبيق، ...)"},
    {"key": "page_count_and_names",
     "ar": "2. صفحة واحدة أم متعدد الصفحات؟ إذا متعدد: اعطني أسماء الصفحات (مثلاً: الرئيسية / مكتبة الأفلام / النقاط / الحساب)."},
    {"key": "page_contents",
     "ar": "3. ماذا يحتوي كل صفحة باختصار؟ (سطر واحد لكل صفحة)."},
    {"key": "target_audience",
     "ar": "4. من هو الجمهور المستهدف؟ (الفئة العمرية، البلد، الاهتمامات)."},
    {"key": "style_preference",
     "ar": "5. ما النمط البصري المطلوب؟ (مودرن / كلاسيكي / فاخر / بسيط)، مع ذكر ألوان مفضلة إن وُجدت."},
    {"key": "key_features",
     "ar": "6. ما الـ3 ميزات الأهم في الموقع؟ (مثلاً: دفع بالنقاط، تسجيل دخول، بحث متقدم)."},
    {"key": "branding",
     "ar": "7. هل هناك اسم وشعار للمشروع؟ وما اللغة الأساسية للمحتوى (عربي / إنجليزي / كلاهما)؟"},
    {"key": "competitors_or_refs",
     "ar": "8. أي موقع أو تطبيق تعتبره مرجعاً أو تريد أن نقترب من أسلوبه؟"},
]


def get_workflow_state(project: Dict[str, Any]) -> Dict[str, Any]:
    """Return the workflow state for a project (with safe defaults).

    Migration: any project without `workflow_state` is treated as starting
    fresh in `discovery` if empty, or `surgical_edit` if it has content.
    """
    state = (project or {}).get("workflow_state") or {}
    if "stage" not in state:
        current_html = (project or {}).get("current_html") or ""
        has_content = len(current_html) > 500 or bool((project or {}).get("pages"))
        state["stage"] = STAGE_SURGICAL_EDIT if has_content else STAGE_DISCOVERY
    if "discovery_answers" not in state:
        state["discovery_answers"] = {}
    if "wired_pages" not in state:
        state["wired_pages"] = []
    if "current_wiring_page" not in state:
        state["current_wiring_page"] = None
    return state


def discovery_complete(state: Dict[str, Any]) -> bool:
    """All 8 questions must have at least a short answer string."""
    answers = state.get("discovery_answers") or {}
    required_keys = {q["key"] for q in DISCOVERY_QUESTIONS}
    return all(answers.get(k) for k in required_keys)


def stage_prompt_addendum(state: Dict[str, Any], project: Dict[str, Any]) -> str:
    """Return the system-prompt addendum the AI must follow for the current stage.

    The addendum is INJECTED on top of the existing system prompt — it does
    not replace it. It states the contract: what to do, what NOT to do, and
    the gate conditions.
    """
    stage = state.get("stage") or STAGE_DISCOVERY
    if stage == STAGE_DISCOVERY:
        return _discovery_addendum(state)
    if stage == STAGE_VISUAL_SKELETON:
        return _visual_skeleton_addendum(state, project)
    if stage == STAGE_WIRING:
        return _wiring_addendum(state, project)
    return _surgical_edit_addendum()


def _discovery_addendum(state: Dict[str, Any]) -> str:
    """Force the AI to ask the 8 discovery questions and STOP — no code yet."""
    answers = state.get("discovery_answers") or {}
    remaining = [q for q in DISCOVERY_QUESTIONS if not answers.get(q["key"])]
    answered_summary = "\n".join(
        f"  ✅ {q['ar'].split('. ', 1)[-1]}: {answers.get(q['key'])}"
        for q in DISCOVERY_QUESTIONS if answers.get(q["key"])
    )
    if not remaining:
        return (
            "\n\n📋 **مرحلة Discovery: اكتملت الـ 8 أسئلة.**\n"
            "الآن انتقل لمرحلة Visual Skeleton (بناء التصميم البصري الكامل لكل الصفحات "
            "بدون تفعيل الأزرار). استدع `advance_workflow_stage(to=\"visual_skeleton\")`.\n"
        )
    lines = [
        "\n\n📋 **مرحلة Discovery — ممنوع كتابة أي كود الآن.**",
        "",
        "اطرح **الأسئلة التالية الناقصة فقط** على العميل في رسالة واحدة منظمة، "
        "وانتظر إجاباته. بعد كل إجابة، استدع "
        "`save_discovery_answer(key=\"...\", value=\"...\")` لحفظها. لا تستدع `apply_section` "
        "ولا `create_page` ولا `write_full_html` قبل اكتمال الـ 8 أسئلة كلها.",
        "",
        "**الأسئلة المتبقية:**",
    ]
    for q in remaining:
        lines.append(f"  • {q['ar']}")
    if answered_summary:
        lines.append("\n**الأسئلة المُجابة سابقاً:**")
        lines.append(answered_summary)
    return "\n".join(lines)


def _visual_skeleton_addendum(state: Dict[str, Any], project: Dict[str, Any]) -> str:
    """Build ALL pages with cohesive design. Buttons must stay inert."""
    answers = state.get("discovery_answers") or {}
    pages_hint = answers.get("page_count_and_names", "")
    contents_hint = answers.get("page_contents", "")
    return (
        "\n\n🎨 **مرحلة Visual Skeleton — تصميم بصري كامل بدون wiring.**\n\n"
        "**ما يجب فعله:**\n"
        f"  1. بناء كل الصفحات المطلوبة (حسب إجابة العميل: {pages_hint or '—'})\n"
        f"     بمحتوى متّسق (حسب: {contents_hint or '—'}).\n"
        "  2. كل صفحة مستقلة في الـ pages dict (استخدم `create_page` للصفحات الجديدة).\n"
        "  3. شريط تنقّل (`<nav>`) موحّد في كل الصفحات، روابطه `href=\"X.html\"` "
        "تنقل بين الصفحات فعلياً.\n"
        "  4. الأزرار، النماذج، dropdowns: **اعرضها مرئياً لكن اتركها خاملة** "
        "(لا `onclick`, لا `addEventListener`, لا JS handlers). أضف "
        "`data-wiring=\"pending\"` لكل زر/نموذج لتمييزه.\n"
        "  5. التصميم متناسق: نفس الـcolor palette، نفس الـfont، نفس الـspacing، "
        "نفس الـcomponents.\n\n"
        "**ممنوع في هذه المرحلة:**\n"
        "  ❌ ممنوع كتابة `<script>` يحتوي على event handlers أو state management.\n"
        "  ❌ ممنوع `fetch()` أو localStorage manipulation.\n"
        "  ❌ ممنوع استدعاء `finish` قبل ما تكتمل **كل الصفحات** ببنية بصرية "
        "حقيقية (Hero + 2-4 أقسام لكل صفحة).\n\n"
        "بعد ما تنتهي، استدع `advance_workflow_stage(to=\"wiring\")` ثم `finish` "
        "بملخّص يخبر العميل أن التصميم البصري جاهز للمراجعة."
    )


def _wiring_addendum(state: Dict[str, Any], project: Dict[str, Any]) -> str:
    """Wire buttons one page at a time, asking customer after each."""
    pages = list((project or {}).get("pages", {}).keys())
    wired = set(state.get("wired_pages") or [])
    current = state.get("current_wiring_page")
    pending = [p for p in pages if p not in wired]
    if not current and pending:
        # Pick the first un-wired page (index.html prioritized)
        current = "index.html" if "index.html" in pending else pending[0]
    return (
        "\n\n🔌 **مرحلة Wiring — تفعيل الأزرار صفحة-صفحة.**\n\n"
        f"**الصفحة الحالية:** `{current or '—'}`\n"
        f"**صفحات مُفعّلة سابقاً:** {', '.join(wired) if wired else 'لا شي بعد'}\n"
        f"**صفحات متبقية للتفعيل:** {', '.join(pending) if pending else 'كل الصفحات اكتملت'}\n\n"
        "**ما يجب فعله الآن:**\n"
        f"  1. ركّز فقط على `{current or 'الصفحة الحالية'}` — لا تلمس الصفحات الأخرى.\n"
        "  2. فعّل جميع الأزرار والنماذج فيها (أضف JS مناسب، احذف "
        "`data-wiring=\"pending\"` من كل عنصر فعّلته).\n"
        "  3. لا تغيّر التصميم البصري — فقط أضف السلوك.\n"
        "  4. بعد ما تنتهي، استدع `mark_page_wired(filename=\"...\")` "
        "ثم `finish` برسالة للعميل: \"فعّلت أزرار صفحة X. جربها وقولي إذا تشتغل صح "
        "قبل ما أنتقل للصفحة التالية\".\n\n"
        "**ممنوع:**\n"
        "  ❌ تفعيل أكثر من صفحة في turn واحد.\n"
        "  ❌ تغيير CSS / HTML structure للصفحات الأخرى.\n"
        "  ❌ استدعاء `finish` قبل تفعيل كل الأزرار في الصفحة الحالية."
    )


def _surgical_edit_addendum() -> str:
    """Default for established projects — pinpoint edits only."""
    return (
        "\n\n🔪 **مرحلة Surgical Edit — تعديلات جراحية فقط.**\n\n"
        "العميل يطلب تعديلاً محدداً. التزم بـ:\n"
        "  • استدع `list_sections` أولاً لرؤية البنية الحالية.\n"
        "  • طبّق التعديل على العنصر المحدد فقط (`apply_section`, `insert_html_at`, "
        "`batch_replace_in_pages`).\n"
        "  • لا تضِف أقساماً لم يطلبها العميل.\n"
        "  • لا تعيد بناء أي قسم بالكامل — التعديل يجب أن يحافظ على ≤2.5× حجم القسم الأصلي."
    )


# ─── Stage-advance helpers (called by the LLM through tools) ────────────────

def can_advance_to(project: Dict[str, Any], target_stage: str) -> tuple[bool, str]:
    """Gate function — returns (allowed, reason_if_blocked)."""
    state = get_workflow_state(project)
    current = state.get("stage")

    if target_stage not in VALID_STAGES:
        return (False, f"stage غير معروف: {target_stage}")

    # discovery → visual_skeleton: must have all 8 answers
    if current == STAGE_DISCOVERY and target_stage == STAGE_VISUAL_SKELETON:
        if not discovery_complete(state):
            answered = sum(1 for q in DISCOVERY_QUESTIONS
                           if (state.get("discovery_answers") or {}).get(q["key"]))
            return (False, f"Discovery غير مكتمل ({answered}/8). أكمل الأسئلة أولاً.")
        return (True, "")

    # visual_skeleton → wiring: must have ≥ 2 pages OR a single page with real content
    if current == STAGE_VISUAL_SKELETON and target_stage == STAGE_WIRING:
        pages = (project or {}).get("pages", {}) or {}
        if not pages:
            return (False, "لا يوجد أي صفحة لتفعيلها. ابنِ Visual Skeleton أولاً.")
        return (True, "")

    # wiring → surgical_edit: all pages wired
    if current == STAGE_WIRING and target_stage == STAGE_SURGICAL_EDIT:
        pages = list((project or {}).get("pages", {}).keys())
        wired = set(state.get("wired_pages") or [])
        unwired = [p for p in pages if p not in wired]
        if unwired:
            return (False, f"الصفحات التالية لم تُفعَّل بعد: {', '.join(unwired)}")
        return (True, "")

    # surgical_edit ↔ surgical_edit: always allowed
    if target_stage == STAGE_SURGICAL_EDIT:
        return (True, "")

    # discovery → wiring or surgical_edit: not allowed without visual skeleton
    if current == STAGE_DISCOVERY and target_stage in (STAGE_WIRING, STAGE_SURGICAL_EDIT):
        return (False, "ممنوع تخطّي Visual Skeleton. أكمل Discovery → Visual Skeleton أولاً.")

    return (True, "")


def stage_label_ar(stage: str) -> str:
    """User-facing Arabic label for a stage."""
    return {
        STAGE_DISCOVERY: "اكتشاف الفكرة (Q&A)",
        STAGE_VISUAL_SKELETON: "التصميم البصري",
        STAGE_WIRING: "تفعيل الأزرار",
        STAGE_SURGICAL_EDIT: "تعديلات جراحية",
    }.get(stage, stage)
