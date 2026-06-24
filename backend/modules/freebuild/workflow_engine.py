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

# Discovery topics — the MINIMUM coverage required before allowing the
# transition to visual_skeleton. The AI is FREE to ask questions in any
# style/order, as many or as few as needed, and to phrase them naturally
# based on the customer's idea (a movie site vs a restaurant menu vs a
# portfolio site need different question shapes). What we enforce is that
# by the end of the discovery stage, the AI has saved an answer under each
# of these 4 essential topic keys. Optional keys can be filled or skipped.
DISCOVERY_REQUIRED_TOPICS = {
    "site_purpose",         # What is this site for?
    "page_count_and_names", # Single-page vs multi-page; if multi, what pages?
    "page_contents",        # What does each page contain (1 line each)?
    "style_preference",     # Visual style + colour direction
}
DISCOVERY_OPTIONAL_TOPICS = {
    "target_audience",
    "key_features",
    "branding",
    "competitors_or_refs",
}
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
    """Discovery is complete when the 4 REQUIRED topics have been answered.

    Optional topics (audience, features, branding, refs) can be skipped if the
    AI feels they aren't needed for the customer's specific project. This
    intentionally trusts the AI to judge what's needed — we only enforce the
    bare minimum so it can't skip everything.
    """
    answers = state.get("discovery_answers") or {}
    return all(answers.get(k) for k in DISCOVERY_REQUIRED_TOPICS)


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
    """Free-form smart discovery — AI asks questions tailored to the customer's idea.

    We give the AI a FRAMEWORK (4 essential topics + 4 optional), not a script.
    We only enforce that the 4 essential topics have saved answers by the end.
    """
    answers = state.get("discovery_answers") or {}
    covered_required = [k for k in DISCOVERY_REQUIRED_TOPICS if answers.get(k)]
    missing_required = [k for k in DISCOVERY_REQUIRED_TOPICS if not answers.get(k)]
    covered_optional = [k for k in DISCOVERY_OPTIONAL_TOPICS if answers.get(k)]

    if not missing_required:
        return (
            "\n\n📋 **مرحلة Discovery: الأساسيات اكتملت.**\n"
            f"غُطّيت {len(covered_required)}/4 موضوع أساسي + "
            f"{len(covered_optional)}/4 اختياري. تستطيع الانتقال لـ Visual Skeleton عبر "
            "`advance_workflow_stage(to=\"visual_skeleton\")` الآن، أو طرح أسئلة "
            "إضافية لو تحتاج تفاصيل أكثر.\n"
        )

    topic_descriptions = {
        "site_purpose": "الهدف من الموقع والمشكلة التي يحلها",
        "page_count_and_names": "عدد الصفحات وأسماؤها (لو multi-page)",
        "page_contents": "محتوى كل صفحة باختصار",
        "style_preference": "النمط البصري والألوان",
        "target_audience": "الجمهور المستهدف (اختياري)",
        "key_features": "الميزات الأهم (اختياري)",
        "branding": "اسم/شعار/لغة (اختياري)",
        "competitors_or_refs": "مراجع مشابهة (اختياري)",
    }
    lines = [
        "\n\n📋 **مرحلة Discovery — اسأل بحرية وبذكاء.**",
        "",
        "أنت مهندس متمرس. **اطرح أسئلة ذكية مخصّصة لفكرة العميل** — مو أسئلة "
        "محفوظة من قائمة جامدة. أسلوبك طبيعي مثل محادثة استشارية: لو قال "
        "\"موقع أفلام\" اسأل عن المصادر والترجمة ونظام المشاهدة؛ لو قال \"متجر\" "
        "اسأل عن المنتجات والشحن والدفع.",
        "",
        f"**الحد الأدنى المطلوب قبل البناء: 4 مواضيع أساسية (حالياً {len(covered_required)}/4):**",
    ]
    for k in DISCOVERY_REQUIRED_TOPICS:
        mark = "✅" if answers.get(k) else "⏳"
        lines.append(f"  {mark} `{k}` — {topic_descriptions.get(k, '')}")
    lines.append(f"\n**مواضيع اختيارية (اسأل عنها بحرية لو رأيت إنها مفيدة، حالياً {len(covered_optional)}/4):**")
    for k in DISCOVERY_OPTIONAL_TOPICS:
        mark = "✅" if answers.get(k) else "○"
        lines.append(f"  {mark} `{k}` — {topic_descriptions.get(k, '')}")
    lines.extend([
        "",
        "**قواعد المرحلة:**",
        "  • بعد كل إجابة من العميل، استدع "
        "`save_discovery_answer(key=\"...\", value=\"...\")` فوراً لحفظها.",
        "  • تقدر تسأل سؤالاً واحداً أو 3 أسئلة في رسالة، حسب ما يناسب السياق.",
        "  • تقدر تجمع معلومات عدة في إجابة واحدة وتحفظها تحت keys مختلفة.",
        "  • **ممنوع** استدعاء `apply_section / create_page / write_full_html` "
        "قبل اكتمال الـ 4 مواضيع الأساسية وانتقالك لـ visual_skeleton عبر "
        "`advance_workflow_stage(to=\"visual_skeleton\")`.",
        "",
    ])
    if answers:
        lines.append("**ما حفظته سابقاً:**")
        for k, v in answers.items():
            lines.append(f"  ✅ {k}: {v[:150]}")
    return "\n".join(lines)


def _visual_skeleton_addendum(state: Dict[str, Any], project: Dict[str, Any]) -> str:
    """Build ALL pages with cohesive design + WORKING nav between pages."""
    answers = state.get("discovery_answers") or {}
    pages_hint = answers.get("page_count_and_names", "")
    contents_hint = answers.get("page_contents", "")
    style_hint = answers.get("style_preference", "")
    return (
        "\n\n🎨 **مرحلة Visual Skeleton — تصميم بصري كامل + nav يعمل.**\n\n"
        "**ما يجب فعله:**\n"
        f"  1. ابنِ كل الصفحات المطلوبة (حسب: {pages_hint or '—'}) "
        f"بمحتوى متّسق مع: {contents_hint or '—'}.\n"
        f"  2. التزم بالنمط: {style_hint or 'حديث ومنسق'}. كل الصفحات على نفس "
        "color palette، نفس الخط، نفس components.\n"
        "  3. كل صفحة مستقلة في الـ pages dict (استخدم `create_page`).\n"
        "  4. ⭐ **شريط nav موحد في كل الصفحات، روابطه `<a href=\"X.html\">` "
        "يجب أن تنقل العميل فعلياً بين الصفحات منذ هذه المرحلة.** هذا يخلي العميل "
        "يستعرض الـ Visual Skeleton طبيعياً.\n"
        "  5. كل صفحة فيها Hero + 2-4 أقسام محتوى حقيقي (مو بس placeholder).\n"
        "  6. الأزرار/forms الداخلية (مثل \"اشترك\"، \"اشترِ النقاط\"، \"احفظ\") "
        "اعرضها مرئياً مع `data-wiring=\"pending\"` — **لا تُضِف لها JS handlers الآن**. "
        "هذه أزرار وظيفية تحتاج backend logic، نفعّلها في مرحلة Wiring.\n"
        "  7. الأزرار البصرية البحتة (تبديل theme، scroll-to-top، فتح modal بسيط) "
        "تقدر تفعّلها مباشرة لأنها لا تحتاج backend.\n\n"
        "**ممنوع في هذه المرحلة:**\n"
        "  ❌ استدعاء `finish` قبل ما تكتمل **كل الصفحات** بمحتوى حقيقي.\n"
        "  ❌ ترك صفحة بـ Hero فقط — كل صفحة تحتاج محتوى يستحق المشاهدة.\n\n"
        "بعد ما تنتهي، استدع `advance_workflow_stage(to=\"wiring\")` ثم `finish` "
        "برسالة للعميل: \"التصميم البصري جاهز. تنقّل بين الصفحات وراجعها، "
        "ثم نبدأ تفعيل الأزرار الوظيفية.\""
    )


def _surgical_edit_addendum() -> str:
    """Default for established projects — pinpoint edits with smart guidance."""
    return (
        "\n\n🔪 **مرحلة Surgical Edit — تعديلات جراحية مع المرونة.**\n\n"
        "**خطوات التعامل مع طلب تعديل:**\n"
        "  1. ابدأ بـ `list_sections` أو `read_current_html` لرؤية البنية الحالية.\n"
        "  2. حدد بدقة العنصر/القسم الذي يحتاج التعديل.\n"
        "  3. اختر الأداة الأنسب:\n"
        "     • تغيير نص أو attribute → `batch_replace_in_pages`\n"
        "     • إضافة سطر/قسم صغير → `insert_html_at`\n"
        "     • استبدال قسم كامل بآخر → `apply_section(op='replace')`\n"
        "     • إصلاح زر لا يعمل → `insert_html_at` مع `<script>` JS handler\n"
        "     • تغيير الألوان عبر الموقع → `update_pages_theme`\n"
        "     • إضافة CSS عام → `inject_global_css`\n\n"
        "**القواعد الذكية (لا تعتبرها قيوداً، بل إرشادات):**\n"
        "  • التعديل لقسم موجود: حافظ على نفس بنية الـ classes والـ structure؛ "
        "إذا كان حجم القسم الجديد أكبر من 4× القسم الأصلي، فهذا غالباً إعادة بناء "
        "كاملة وليس تعديلاً — تأكد إن هذا فعلاً ما طلبه العميل.\n"
        "  • لا تضِف أقساماً لم يطلبها العميل صراحة (newsletter, FAQ, testimonials...).\n"
        "  • إذا العميل قال \"الزر الفلاني ما يشتغل\" — هذا طلب wiring، استخدم "
        "`insert_html_at` لإضافة `<script>` يفعّل الزر، **بدون تغيير شكله أو موقعه**.\n"
        "  • بعد كل تعديل، استدع `read_current_html` للتأكد من النتيجة قبل ما "
        "تقول \"تم\"."
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


def _surgical_edit_addendum_OLD_REMOVED() -> str:
    """REMOVED — replaced by smarter version above. This stub exists to keep
    the import surface stable for any external caller. Will be deleted in a
    future refactor."""
    return ""


# ─── Stage-advance helpers (called by the LLM through tools) ────────────────

def can_advance_to(project: Dict[str, Any], target_stage: str) -> tuple[bool, str]:
    """Gate function — returns (allowed, reason_if_blocked)."""
    state = get_workflow_state(project)
    current = state.get("stage")

    if target_stage not in VALID_STAGES:
        return (False, f"stage غير معروف: {target_stage}")

    # discovery → visual_skeleton: must have all 4 REQUIRED topics
    if current == STAGE_DISCOVERY and target_stage == STAGE_VISUAL_SKELETON:
        if not discovery_complete(state):
            answered = sum(1 for k in DISCOVERY_REQUIRED_TOPICS
                           if (state.get("discovery_answers") or {}).get(k))
            return (False, f"Discovery غير مكتمل ({answered}/4 موضوع أساسي). أكمل المواضيع الأساسية الناقصة أولاً.")
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
