"""Consultative Wizard Engine — guided step-by-step website building.

Flow:
  1. template_chosen   → user picked a template shell
  2. buttons           → button style (rounded/square/pill/sharp)
  3. colors            → color mood (classic/modern/warm/dark/pastel...)
  4. typography        → font style (modern/elegant/playful)
  5. features          → core extras (delivery, reservation, cart, booking...)
  6. dashboard         → admin dashboard yes/no
  7. dashboard_items   → (if yes) what's inside the dashboard
  8. sections          → which content sections to include
  9. content_detail    → fill real content for each section
 10. branding          → logo, brand name, tagline
 11. review            → show final preview
 12. finalize          → payment integration & contact form
 13. done              → site ready; chat becomes free-form

AI may SKIP or REORDER steps if user explicitly asks for something out-of-order
(e.g., "I want delivery for my restaurant" while on step 2).
"""
from typing import List, Dict, Any, Optional


# ---------------------------------------------------------------------------
# Vertical-specific question injection
# ---------------------------------------------------------------------------
def _vertical_steps(vertical_id: Optional[str]) -> List[Dict[str, Any]]:
    """Return dynamic steps generated from the vertical's wizard_questions.
    Each question becomes a step with id `vq_<question_id>`.
    """
    if not vertical_id:
        return []
    try:
        from .verticals import get_vertical
    except Exception:
        return []
    v = get_vertical(vertical_id) or {}
    out: List[Dict[str, Any]] = []
    for q in (v.get("wizard_questions") or []):
        chips = [{"id": str(i), "label": x, "value": x} for i, x in enumerate(q.get("chips") or [])]
        out.append({
            "id": f"vq_{q.get('id','unknown')}",
            "title": q.get("q", "سؤال"),
            "question": q.get("q", "سؤال"),
            "chips": chips,
            "render": "chips" if chips else "free_text",
            "applies": f"vq_{q.get('id','unknown')}",
            "vertical_specific": True,
        })
    return out


def _merged_steps(project: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Return STEPS with vertical-specific questions spliced in right after 'variant',
    AND deep widget-style steps right after 'extras' (one per chosen extra + cart for ecom)."""
    vertical_id = ((project or {}).get("vertical")) if project else None
    v_steps = _vertical_steps(vertical_id)

    # 🆕 Per-extra widget style steps with 3 visual options + AI custom
    extras_chosen = (((project or {}).get("wizard") or {}).get("answers") or {}).get("extras") or []
    if not isinstance(extras_chosen, list):
        extras_chosen = []
    EXTRA_TO_WIDGET = {
        "whatsapp_float": "whatsapp",
        "sticky_phone":   "whatsapp",   # phone shares whatsapp visual style
        "scroll_top":     "scroll_top",
        "book_float":     "book_float",
        "announce_bar":   "announce_bar",
        "rating_widget":  "whatsapp",
    }
    style_steps: List[Dict[str, Any]] = []
    seen_widgets: set = set()  # dedup so we don't ask the same widget twice
    try:
        from .widget_styles import WIDGETS
    except Exception:
        WIDGETS = {}
    for ext in extras_chosen:
        wid = EXTRA_TO_WIDGET.get(ext)
        if not wid or wid not in WIDGETS or wid in seen_widgets:
            continue
        seen_widgets.add(wid)
        w = WIDGETS[wid]
        variants = list((w.get("variants") or {}).items())[:3]
        chips = [{"id": vid, "label": v.get("name_ar", vid), "value": vid} for vid, v in variants]
        chips.append({"id": "ai_custom", "label": "🤖 صمّم لي بمزاجي (AI)", "value": "ai_custom"})
        style_steps.append({
            "id": f"style_{wid}",
            "title": f"شكل {w.get('name_ar', wid)}",
            "question": f"✨ اختر شكل {w.get('name_ar', wid)} — أو اطلب من الذكاء الاصطناعي تصميماً مخصّصاً بمزاجك:",
            "chips": chips,
            "render": "chips",
            "applies": f"widget_style_{wid}",
            "vertical_specific": True,
            "widget_id": wid,
        })
    # Cart style step for any e-commerce-like vertical
    biz = ((project or {}).get("business_type") or (project or {}).get("template") or "").lower()
    if biz in ("store", "ecommerce", "cosmetics", "automotive", "jewelry", "bakery", "restaurant", "coffee", "pets") and "cart" in WIDGETS and "cart" not in seen_widgets:
        seen_widgets.add("cart")
        w = WIDGETS["cart"]
        variants = list((w.get("variants") or {}).items())[:3]
        chips = [{"id": vid, "label": v.get("name_ar", vid), "value": vid} for vid, v in variants]
        chips.append({"id": "ai_custom", "label": "🤖 صمّم سلة بمزاجي (AI)", "value": "ai_custom"})
        style_steps.append({
            "id": "style_cart",
            "title": "شكل السلة",
            "question": "🛒 اختر شكل سلة التسوّق — أو اطلب من AI تصميماً مخصّصاً بمزاجك:",
            "chips": chips,
            "render": "chips",
            "applies": "widget_style_cart",
            "vertical_specific": True,
            "widget_id": "cart",
        })

    out: List[Dict[str, Any]] = []
    for s in STEPS:
        out.append(s)
        if s["id"] == "variant":
            out.extend(v_steps)
        if s["id"] == "extras":
            out.extend(style_steps)
    return out


# ---------------------------------------------------------------------------
# Step definitions
# ---------------------------------------------------------------------------
STEPS: List[Dict[str, Any]] = [
    {
        "id": "brief",
        "title": "وصف النشاط",
        "question": "✨ صف لي نشاطك بحرّية — كلما كان وصفك أغنى، كان تصميمي أكثر إبداعاً.",
        "chips": [],
        "render": "free_text",
        "free_text": True,
        "applies": "brief",
        # Only active when template is 'blank' or user explicitly requests a custom start
        "condition": lambda ans: ans.get("__show_brief__", False),
    },
    {
        "id": "variant",
        "title": "النمط البصري",
        "question": "ممتاز! ✨ اخترت هذا القالب. الآن اختر النمط البصري — كل نمط مختلف بألوانه وإحساسه:",
        "chips": [],   # rendered as rich variant-picker in UI
        "render": "variants",
        "applies": "variant",
    },
    {
        "id": "buttons",
        "title": "شكل الأزرار",
        "question": "جميل! الآن أخبرني — ما شكل الأزرار اللي يعجبك؟",
        "chips": [
            {"id": "pill",    "label": "دائرية كاملة",    "value": "full"},
            {"id": "rounded", "label": "زوايا ناعمة",     "value": "large"},
            {"id": "medium",  "label": "زوايا متوسطة",    "value": "medium"},
            {"id": "sharp",   "label": "حادة (مستطيلة)",   "value": "none"},
        ],
        "render": "chips",
        "applies": "button_radius",
    },
    {
        "id": "colors",
        "title": "الأجواء اللونية",
        "question": "رائع! الآن اختر الأجواء اللونية اللي تناسب نشاطك:",
        "chips": [
            {"id": "classic",  "label": "كلاسيكي ذهبي",   "value": "classic"},
            {"id": "modern",   "label": "عصري أزرق",      "value": "modern"},
            {"id": "warm",     "label": "دافئ برتقالي",   "value": "warm"},
            {"id": "luxury",   "label": "فاخر ذهبي-أسود", "value": "luxury"},
            {"id": "dark_pro", "label": "داكن احترافي",    "value": "dark_pro"},
            {"id": "nature",   "label": "طبيعي أخضر",     "value": "nature"},
            {"id": "pastel",   "label": "هادئ باستيل",    "value": "pastel"},
            {"id": "bold",     "label": "جريء أحمر",      "value": "bold"},
        ],
        "applies": "color_variant",
    },
    {
        "id": "typography",
        "title": "الخط",
        "question": "ممتاز 🎨 أي خط تفضّل لموقعك؟",
        "chips": [
            {"id": "Tajawal",    "label": "تجوال (عصري متوازن)", "value": "Tajawal"},
            {"id": "Cairo",      "label": "القاهرة (واضح)",       "value": "Cairo"},
            {"id": "Amiri",      "label": "أميري (فخم كلاسيكي)",  "value": "Amiri"},
            {"id": "Readex Pro", "label": "ريدكس (ناعم حديث)",     "value": "Readex Pro"},
            {"id": "Almarai",    "label": "المراعي (نظيف)",       "value": "Almarai"},
        ],
        "applies": "font",
    },
    {
        "id": "features",
        "title": "المميزات الأساسية",
        "question": "تمام 👌 أي من هذه الخدمات تحتاجها في موقعك؟ (اختر عدة)",
        "chips": [
            {"id": "delivery",    "label": "🛵 خدمة توصيل"},
            {"id": "reservation", "label": "📅 حجز مسبق"},
            {"id": "cart",        "label": "🛒 عربة تسوق"},
            {"id": "booking",     "label": "⏰ حجز مواعيد"},
            {"id": "whatsapp",    "label": "💬 تواصل واتساب"},
            {"id": "map",         "label": "📍 خريطة الموقع"},
            {"id": "reviews",     "label": "⭐ تقييمات العملاء"},
            {"id": "newsletter",  "label": "📧 نشرة بريدية"},
        ],
        "multi": True,
        "applies": "features_list",
    },
    {
        "id": "dashboard",
        "title": "لوحة تحكم",
        "question": "🎛️ وصلنا للوحة التحكم! اختر الشكل — وستتحوّل المعاينة فوراً لعرض لوحة التحكم بملء الشاشة:",
        "chips": [
            {"id": "sidebar", "label": "📋 شريط جانبي (موصى به)"},
            {"id": "cards",   "label": "📇 بطاقات كاملة"},
            {"id": "tabs",    "label": "🗂️ تبويبات أفقية"},
            {"id": "none",    "label": "❌ لا أحتاجها"},
        ],
        "render": "chips",
        "applies": "dashboard_layout",
    },
    {
        "id": "dashboard_items",
        "title": "محتويات لوحة التحكم",
        "question": "ممتاز! اختر العناصر التي تريدها — كل خيار يظهر فوراً في اللوحة:",
        "chips": [
            {"id": "orders",    "label": "📦 الطلبات"},
            {"id": "customers", "label": "👥 العملاء"},
            {"id": "products",  "label": "🏷️ المنتجات"},
            {"id": "analytics", "label": "📊 الإحصائيات"},
            {"id": "messages",  "label": "💬 الرسائل"},
            {"id": "reports",   "label": "📈 التقارير"},
            {"id": "users",     "label": "🔐 المستخدمون والأدوار"},
            {"id": "settings",  "label": "⚙️ الإعدادات"},
            {"id": "calendar",  "label": "📅 التقويم"},
            {"id": "inventory", "label": "📋 المخزون"},
            {"id": "payments",  "label": "💳 المدفوعات"},
            {"id": "reviews",   "label": "⭐ التقييمات"},
        ],
        "multi": True,
        "render": "chips",
        "condition": lambda ans: ans.get("dashboard") and ans.get("dashboard") != "none",
        "applies": "dashboard_items",
    },
    {
        "id": "sections",
        "title": "أقسام الموقع",
        "question": "الآن اختر الأقسام اللي تريدها في صفحتك الرئيسية:",
        "chips": [
            {"id": "hero",         "label": "🎯 قسم رئيسي (Hero)"},
            {"id": "about",        "label": "📖 من نحن"},
            {"id": "features",     "label": "✨ مميزاتنا"},
            {"id": "menu",         "label": "🍽️ قائمة الطعام"},
            {"id": "products",     "label": "🛍️ المنتجات"},
            {"id": "gallery",      "label": "🖼️ معرض صور"},
            {"id": "testimonials", "label": "💬 آراء العملاء"},
            {"id": "team",         "label": "👥 الفريق"},
            {"id": "pricing",      "label": "💰 خطط الأسعار"},
            {"id": "faq",          "label": "❓ أسئلة شائعة"},
            {"id": "contact",      "label": "📞 تواصل معنا"},
            {"id": "cta",          "label": "📢 دعوة للتسجيل"},
        ],
        "multi": True,
        "applies": "sections_list",
    },
    {
        "id": "branding",
        "title": "الهوية",
        "question": "أخبرني عن هوية نشاطك — ما اسم العلامة التجارية وشعارها؟",
        "chips": [],  # free text only
        "free_text": True,
        "applies": "branding",
    },
    {
        "id": "payment",
        "title": "وسائل الدفع",
        "question": "ممتاز 💳 ما وسائل الدفع التي تريد دعمها؟",
        "chips": [
            {"id": "stripe",   "label": "💳 Stripe (فيزا/ماستركارد)"},
            {"id": "mada",     "label": "🏦 مدى"},
            {"id": "applepay", "label": "📱 Apple Pay"},
            {"id": "stcpay",   "label": "💰 STC Pay"},
            {"id": "paypal",   "label": "🅿️ PayPal"},
            {"id": "cod",      "label": "💵 الدفع عند الاستلام"},
            {"id": "bank",     "label": "🏛️ تحويل بنكي"},
            {"id": "none",     "label": "لا أحتاج دفع حالياً"},
        ],
        "multi": True,
        "applies": "payment_methods",
    },
    {
        "id": "extras",
        "title": "إضافات حيّة",
        "question": "✨ هنا تختار الإضافات التفاعلية — كل اختيار يظهر فوراً كعنصر حيّ في موقعك!",
        "chips": [
            {"id": "sticky_phone",  "label": "📞 زر جوال لاصق"},
            {"id": "whatsapp_float","label": "💬 واتساب عائم"},
            {"id": "announce_bar",  "label": "📢 شريط إعلاني علوي"},
            {"id": "countdown",     "label": "⏰ عدّاد تنازلي"},
            {"id": "video_section", "label": "🎬 قسم فيديو تعريفي"},
            {"id": "newsletter",    "label": "📧 نموذج اشتراك"},
            {"id": "rating_widget", "label": "⭐ شارة التقييم"},
            {"id": "social_bar",    "label": "📱 أيقونات التواصل"},
            {"id": "trust_badges",  "label": "🛡️ شارات ثقة"},
            {"id": "scroll_top",    "label": "⬆️ زر العودة للأعلى"},
            {"id": "live_chat",     "label": "💬 محادثة فورية"},
            {"id": "stats_band",    "label": "📊 شريط إحصائيات"},
        ],
        "multi": True,
        "render": "chips",
        "applies": "extras",
    },
    {
        "id": "final_confirm",
        "title": "المراجعة النهائية",
        "question": "🎉 تمّت كل المراحل! قبل الاعتماد الرسمي — هل تريد إضافة أي شيء آخر للموقع؟ تصفّح المعاينة جيداً.",
        "chips": [
            {"id": "approve", "label": "✅ اعتماد نهائي", "value": "approve"},
            {"id": "more",    "label": "➕ أحتاج إضافات أخرى", "value": "more"},
            {"id": "redo_colors", "label": "🎨 إعادة ضبط الألوان", "value": "redo_colors"},
            {"id": "redo_sections","label": "📋 تعديل الأقسام", "value": "redo_sections"},
        ],
        "render": "chips",
        "applies": "final_confirm",
    },
    {
        "id": "review",
        "title": "مراجعة",
        "question": "الموقع جاهز! راجع المعاينة على اليسار — أي تعديل اكتبه لي الآن.",
        "chips": [
            {"id": "approve", "label": "✅ اعتماد نهائي"},
            {"id": "change_colors", "label": "🎨 تغيير الألوان"},
            {"id": "change_buttons", "label": "🔘 تغيير الأزرار"},
            {"id": "add_section", "label": "➕ إضافة قسم"},
        ],
        "applies": "review_action",
    },
]


# ---------------------------------------------------------------------------
# Color variant map (re-uses variants.py themes)
# ---------------------------------------------------------------------------
COLOR_VARIANT_MAP = {
    "classic":  {"primary": "#D4AF37", "secondary": "#1a1f3a", "accent": "#8B0000"},
    "modern":   {"primary": "#3B82F6", "secondary": "#0f172a", "accent": "#22D3EE"},
    "warm":     {"primary": "#F59E0B", "secondary": "#18181b", "accent": "#EF4444"},
    "luxury":   {"primary": "#D4AF37", "secondary": "#0a0a0a", "accent": "#B8860B", "background": "#0a0a0a"},
    "dark_pro": {"primary": "#06B6D4", "secondary": "#020617", "accent": "#F59E0B", "background": "#020617"},
    "nature":   {"primary": "#10B981", "secondary": "#064e3b", "accent": "#F59E0B"},
    "pastel":   {"primary": "#A78BFA", "secondary": "#FDF2F8", "accent": "#F472B6", "background": "#FDF2F8", "text": "#581c87"},
    "bold":     {"primary": "#DC2626", "secondary": "#18181b", "accent": "#FBBF24"},
    "minimal":  {"primary": "#000000", "secondary": "#ffffff", "accent": "#6B7280", "background": "#ffffff", "text": "#18181b"},
}


RADIUS_MAP = {
    "full": "full", "large": "large", "medium": "medium", "none": "none",
}


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------
def default_wizard_state() -> Dict[str, Any]:
    return {
        "active": True,
        "step": "variant",
        "answers": {},
        "completed": [],
    }


def get_step(step_id: str, project: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    for s in _merged_steps(project):
        if s["id"] == step_id:
            return s
    return None


def next_step_id(current: str, answers: Dict[str, Any], project: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Return the next step id after `current`, applying conditional skips."""
    all_steps = _merged_steps(project)
    ids = [s["id"] for s in all_steps]
    try:
        idx = ids.index(current)
    except ValueError:
        return all_steps[0]["id"]
    for s in all_steps[idx + 1:]:
        cond = s.get("condition")
        if cond and not cond(answers):
            continue
        return s["id"]
    return None  # end


def get_chips_for_step(step_id: str, project: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    s = get_step(step_id, project)
    return (s or {}).get("chips", []) or []


def get_question_for_step(step_id: str, project: Optional[Dict[str, Any]] = None) -> str:
    s = get_step(step_id, project)
    return (s or {}).get("question", "")


def steps_metadata(project: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Public list (without python callables)."""
    out = []
    for s in _merged_steps(project):
        out.append({k: v for k, v in s.items() if k != "condition"})
    return out


# ---------------------------------------------------------------------------
# Apply a wizard answer to the project
# ---------------------------------------------------------------------------
def apply_answer(project: Dict[str, Any], step_id: str, value: Any) -> Dict[str, Any]:
    """Mutate-and-return project after applying the answer for `step_id`.
    Always keeps theme/sections consistent with the chosen template shell."""
    theme = dict(project.get("theme") or {})
    wizard = project.get("wizard") or default_wizard_state()
    ans = dict(wizard.get("answers") or {})

    if step_id == "variant":
        # Apply the chosen visual variant theme (preserves template sections)
        from .variants import STYLE_VARIANTS
        v = next((x for x in STYLE_VARIANTS if x["id"] == str(value)), None)
        if v:
            theme.update(v["theme_override"])
        ans["variant"] = value
    elif step_id == "buttons":
        # value is radius token (full/large/medium/none)
        theme["radius"] = RADIUS_MAP.get(str(value), "medium")
        ans["buttons"] = value
    elif step_id == "colors":
        palette = COLOR_VARIANT_MAP.get(str(value))
        if palette:
            theme.update(palette)
        ans["colors"] = value
    elif step_id == "typography":
        theme["font"] = str(value) or "Tajawal"
        ans["typography"] = value
    elif step_id == "features":
        ans["features"] = value if isinstance(value, list) else [value]
        project = _apply_features(project, ans["features"])
        # _apply_features mutates project["theme"] — sync local `theme` back
        theme = dict(project.get("theme") or {})
    elif step_id == "dashboard":
        ans["dashboard"] = value
        project = _apply_dashboard_layout(project, value, ans)
    elif step_id == "dashboard_items":
        ans["dashboard_items"] = value if isinstance(value, list) else [value]
        project = _apply_dashboard_items(project, ans["dashboard_items"])
    elif step_id == "sections":
        ans["sections_wanted"] = value if isinstance(value, list) else [value]
        project = _apply_sections_selection(project, ans["sections_wanted"])
    elif step_id == "branding":
        ans["branding"] = value  # free text
        project = _apply_branding(project, str(value))
    elif step_id == "payment":
        ans["payment"] = value if isinstance(value, list) else [value]
    elif step_id == "extras":
        ans["extras"] = value if isinstance(value, list) else [value]
        project = _apply_extras(project, ans["extras"])
        theme = dict(project.get("theme") or {})  # sync back after mutation
    elif step_id == "final_confirm":
        ans["final_confirm"] = value
        if value == "approve":
            project["status"] = "approved"
            project["approved_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    elif step_id == "review":
        ans["review"] = value
    elif step_id.startswith("vq_"):
        # Vertical-specific free-form answer — stored in `answers.vertical.<id>`
        key = step_id[3:]
        vert_map = dict(ans.get("vertical") or {})
        vert_map[key] = value
        ans["vertical"] = vert_map
    elif step_id.startswith("style_"):
        # 🆕 Per-widget style picker (e.g. style_whatsapp, style_cart) — applied to widget_styles
        widget_id = step_id.replace("style_", "", 1)
        styles = dict(project.get("widget_styles") or {})
        widget_state = dict(styles.get(widget_id) or {})
        if value == "ai_custom":
            widget_state["variant"] = "ai_custom"
            widget_state["awaiting_ai_brief"] = True  # frontend will prompt for description
        else:
            widget_state["variant"] = value
            widget_state.pop("awaiting_ai_brief", None)
        styles[widget_id] = widget_state
        project["widget_styles"] = styles
        styles_map = dict(ans.get("widget_styles") or {})
        styles_map[widget_id] = value
        ans["widget_styles"] = styles_map

    wizard["answers"] = ans
    wizard["completed"] = list(dict.fromkeys((wizard.get("completed") or []) + [step_id]))
    nxt = next_step_id(step_id, ans, project)
    wizard["step"] = nxt or "done"
    if not nxt:
        wizard["active"] = False

    project["theme"] = theme
    project["wizard"] = wizard
    return project


def _apply_sections_selection(project: Dict[str, Any], wanted: List[str]) -> Dict[str, Any]:
    """Keep only wanted sections (preserving order + data) + ensure footer at end."""
    if not wanted:
        return project
    current = project.get("sections") or []
    kept, seen = [], set()
    # preserve order of existing sections that are wanted
    for s in current:
        t = s.get("type")
        if t in wanted and t not in seen:
            kept.append(s)
            seen.add(t)
    # add any wanted that weren't in current (minimal stubs)
    for t in wanted:
        if t not in seen:
            kept.append({"type": t, "order": len(kept), "visible": True, "data": _default_data_for_type(t)})
            seen.add(t)
    # ensure footer last
    if "footer" not in seen:
        kept.append({"type": "footer", "order": len(kept), "visible": True, "data": {"brand": (project.get("name") or "موقعي")}})
    project["sections"] = [{**s, "order": i} for i, s in enumerate(kept)]
    return project


def _default_data_for_type(t: str) -> Dict[str, Any]:
    defaults = {
        "hero":         {"title": "عنوان رئيسي", "subtitle": "عنوان فرعي", "cta_text": "ابدأ الآن", "layout": "split"},
        "features":     {"title": "مميزاتنا", "items": [{"icon": "✨", "title": "ميزة", "text": "وصف"}]},
        "about":        {"title": "من نحن", "text": "اكتب نبذة عن نشاطك."},
        "products":     {"title": "منتجاتنا", "items": []},
        "menu":         {"title": "القائمة", "categories": []},
        "gallery":      {"title": "معرض الصور", "images": []},
        "testimonials": {"title": "آراء العملاء", "items": []},
        "team":         {"title": "فريقنا", "members": []},
        "pricing":      {"title": "الأسعار", "plans": []},
        "faq":          {"title": "أسئلة شائعة", "items": []},
        "contact":      {"title": "تواصل معنا", "email": "", "phone": ""},
        "cta":          {"title": "جاهز للبدء؟", "cta_text": "انضم إلينا"},
        "footer":       {"brand": "موقعي"},
    }
    return defaults.get(t, {"title": t})


def _apply_branding(project: Dict[str, Any], text: str) -> Dict[str, Any]:
    """Very small heuristic: use the user's text as brand/title."""
    if not text:
        return project
    text = text.strip()
    project["name"] = text[:80]
    sections = project.get("sections") or []
    for s in sections:
        if s.get("type") == "hero":
            s["data"] = {**(s.get("data") or {}), "title": text[:60]}
        if s.get("type") == "footer":
            s["data"] = {**(s.get("data") or {}), "brand": text[:40]}
    project["sections"] = sections
    return project


def _find_dashboard_section(sections: List[Dict[str, Any]]) -> int:
    for i, s in enumerate(sections):
        if s.get("type") == "dashboard":
            return i
    return -1


def _apply_dashboard_layout(project: Dict[str, Any], layout: str, ans: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure dashboard section exists with selected layout. Remove if 'none'."""
    import uuid as _uuid
    sections = list(project.get("sections") or [])
    idx = _find_dashboard_section(sections)
    if layout == "none":
        if idx >= 0:
            sections.pop(idx)
            project["sections"] = [{**s, "order": i} for i, s in enumerate(sections)]
        return project
    items = ans.get("dashboard_items") or []
    dash_data = {"layout": layout, "title": "لوحة التحكم", "items": items, "contact": {}}
    if idx >= 0:
        sections[idx] = {**sections[idx], "data": {**(sections[idx].get("data") or {}), **dash_data}}
    else:
        # Insert before footer
        insert_at = len(sections)
        for i, s in enumerate(sections):
            if s.get("type") == "footer":
                insert_at = i
                break
        sections.insert(insert_at, {
            "id": f"sec-{_uuid.uuid4().hex[:8]}", "type": "dashboard",
            "order": insert_at, "visible": True, "data": dash_data,
        })
    project["sections"] = [{**s, "order": i} for i, s in enumerate(sections)]
    return project


def _apply_dashboard_items(project: Dict[str, Any], items: List[str]) -> Dict[str, Any]:
    sections = list(project.get("sections") or [])
    idx = _find_dashboard_section(sections)
    if idx < 0:
        # Create default cards dashboard
        return _apply_dashboard_layout(project, "cards", {"dashboard_items": items})
    sections[idx] = {**sections[idx], "data": {**(sections[idx].get("data") or {}), "items": items}}
    project["sections"] = sections
    return project


def _apply_extras(project: Dict[str, Any], extras: List[str]) -> Dict[str, Any]:
    """Store extras in theme so renderer can emit floating widgets.

    Also inject visible sections for some extras (video, newsletter, stats_band).
    """
    import uuid as _uuid
    theme = {**(project.get("theme") or {}), "extras": extras}
    project["theme"] = theme
    # Section-based extras: toggle insertion/removal
    section_extras = {
        "video_section":   ("video",       {"title": "شاهد قصتنا", "url": "https://www.youtube.com/embed/dQw4w9WgXcQ"}),
        "newsletter":      ("newsletter",  {"title": "اشترك في نشرتنا", "subtitle": "خصومات حصرية وعروض أولاً"}),
        "stats_band":      ("stats_band",  {"title": "أرقام نفتخر بها", "items": [
            {"label": "عميل سعيد", "value": "5,000+"},
            {"label": "طلب منفّذ", "value": "12,400"},
            {"label": "سنوات خبرة", "value": "10"},
            {"label": "تقييم", "value": "4.9★"},
        ]}),
    }
    sections = list(project.get("sections") or [])
    # Remove previously-inserted extra sections not currently wanted
    wanted_types = {section_extras[e][0] for e in extras if e in section_extras}
    sections = [s for s in sections if s.get("type") not in {"video", "newsletter", "stats_band"} or s.get("type") in wanted_types]
    # Insert wanted ones before footer if not present
    existing_types = {s.get("type") for s in sections}
    footer_idx = next((i for i, s in enumerate(sections) if s.get("type") == "footer"), len(sections))
    for e in extras:
        if e in section_extras:
            stype, sdata = section_extras[e]
            if stype not in existing_types:
                sections.insert(footer_idx, {"id": f"sec-{_uuid.uuid4().hex[:8]}", "type": stype,
                                              "order": footer_idx, "visible": True, "data": sdata})
                footer_idx += 1
    project["sections"] = [{**s, "order": i} for i, s in enumerate(sections)]
    return project


# ---------------------------------------------------------------------------
# Features → visible elements (extras + sections)
# Each selected feature must IMMEDIATELY materialize in the live preview.
# ---------------------------------------------------------------------------
FEATURE_TO_EXTRAS = {
    "whatsapp":    "whatsapp_float",
    "cart":        "cart_float",
    "booking":     "book_float",
    "reviews":     "rating_widget",
}

FEATURE_TO_SECTION = {
    "reservation": ("reservation", {"title": "احجز طاولتك", "subtitle": "اضمن مكانك قبل الزحام", "cta_text": "احجز الآن"}),
    "map":         ("map_embed", {"title": "موقعنا على الخريطة", "address": "الرياض، المملكة العربية السعودية", "lat": 24.7136, "lng": 46.6753}),
    "newsletter":  ("newsletter", {"title": "اشترك في نشرتنا", "subtitle": "عروض حصرية وأخبار أولاً"}),
    "delivery":    ("delivery_banner", {"title": "🛵 توصيل سريع", "subtitle": "توصيل مجاني للطلبات فوق 100 ريال", "cta_text": "اطلب الآن"}),
}

_FEATURE_SECTION_TYPES = {v[0] for v in FEATURE_TO_SECTION.values()}
_FEATURE_EXTRA_IDS = set(FEATURE_TO_EXTRAS.values())


def _apply_features(project: Dict[str, Any], features: List[str]) -> Dict[str, Any]:
    """Translate selected features into VISIBLE extras + sections in the live preview."""
    import uuid as _uuid
    theme = dict(project.get("theme") or {})
    existing_extras = list(theme.get("extras") or [])
    kept_extras = [e for e in existing_extras if e not in _FEATURE_EXTRA_IDS]
    for f in features:
        ex = FEATURE_TO_EXTRAS.get(f)
        if ex and ex not in kept_extras:
            kept_extras.append(ex)
    theme["extras"] = kept_extras
    project["theme"] = theme

    wanted_section_types = set()
    wanted_section_data = {}
    for f in features:
        if f in FEATURE_TO_SECTION:
            stype, sdata = FEATURE_TO_SECTION[f]
            wanted_section_types.add(stype)
            wanted_section_data[stype] = sdata

    sections = list(project.get("sections") or [])
    sections = [s for s in sections if s.get("type") not in _FEATURE_SECTION_TYPES or s.get("type") in wanted_section_types]
    existing_types = {s.get("type") for s in sections}
    footer_idx = next((i for i, s in enumerate(sections) if s.get("type") == "footer"), len(sections))
    for stype in wanted_section_types:
        if stype not in existing_types:
            sections.insert(footer_idx, {
                "id": f"sec-{_uuid.uuid4().hex[:8]}", "type": stype,
                "order": footer_idx, "visible": True, "data": wanted_section_data[stype],
            })
            footer_idx += 1
    project["sections"] = [{**s, "order": i} for i, s in enumerate(sections)]
    return project
