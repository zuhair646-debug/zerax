"""Plan Builder + Approval Contract.

The brain produces a structured JSON plan. The user sees it as a clean
checklist + cost preview, then approves / refines / cancels.

Once approved, the plan becomes a binding contract:
  • The executor walks through plan["steps"] in order
  • Each step has a `done` flag set after successful tool execution
  • The brain cannot skip steps or invent new ones mid-execution
  • If the user mid-stream says "stop" / "wait", we pause cleanly

This is the single biggest UX shift: NO MORE "AI builds something
unexpected for 5 minutes then charges you 500 credits".
"""
from typing import Any, Dict, List, Optional


# Cost estimates (credits) per step type — used in plan preview
STEP_COST: Dict[str, int] = {
    "create_page": 25,
    "delete_page": 8,
    "apply_section": 18,
    "write_full_html": 60,
    "move_section_to_page": 30,
    "keep_only_sections": 12,
    "remove_section": 8,
    "update_nav": 6,
    "fetch_image": 4,
    "fetch_font": 2,
    "self_test": 10,
    "visual_snapshot": 4,
}


def estimate_plan_cost(steps: List[Dict[str, Any]]) -> Dict[str, int]:
    """Compute (min, expected, max) credit cost for a plan."""
    expected = sum(STEP_COST.get(s.get("tool", ""), 15) for s in steps)
    # Add 20% buffer for retries + verification iterations
    return {
        "min": int(expected * 0.8),
        "expected": int(expected),
        "max": int(expected * 1.5),
    }


def _detect_multi_page_intent(user_goal: str, answers: Dict[str, Any]) -> bool:
    """Detect Multi-Page intent from the user's goal text + collected answers.

    Returns True if the user explicitly asked for separate pages, named multiple
    pages, or used keywords that imply a multi-page architecture.
    """
    g = (user_goal or "").lower()
    # Arabic + English keywords that strongly imply separate pages
    multi_signals = [
        "صفحة منفصلة", "صفحات منفصلة", "صفحات متعددة", "متعدد الصفحات",
        "كل صفحة", "صفحة للـ", "صفحة لـ", "صفحات مستقلة", "ملف منفصل",
        "صفحات",  # plural form (covers many natural expressions)
        "multi-page", "multi page", "multipage", "separate pages",
        "independent pages", "page for", "pages for",
        "menu page", "cart page", "about page", "contact page",
    ]
    # Project types that are inherently multi-page
    inherently_multi = [
        "تطبيق", "متجر", "منصة", "موقع تجاري", "ecommerce", "marketplace",
        "platform", "saas dashboard", "admin panel",
    ]
    if any(s in g for s in multi_signals):
        return True
    # Detect when user names 2+ distinct page-like sections (movies, series, cart, ...)
    page_name_hits = sum(1 for kw in (
        "movies", "أفلام", "series", "مسلسلات", "cart", "سلة", "checkout", "دفع",
        "profile", "حساب", "products", "منتجات", "about", "من نحن", "contact",
        "تواصل", "blog", "مدونة", "menu", "منيو", "delivery", "توصيل",
    ) if kw in g)
    if page_name_hits >= 2:
        return True
    # answers may have site_structure set explicitly
    structure = (answers.get("site_structure") or answers.get("section_layout") or "").lower()
    if any(s in structure for s in ["صفحات متعددة", "multi", "separate"]):
        return True
    # Inherent multi-page project types
    if any(s in g for s in inherently_multi):
        return True
    return False


def _extract_requested_pages(user_goal: str) -> List[str]:
    """Best-effort extraction of page filenames the user explicitly named.

    Example: "تطبيق فيه صفحة أفلام وصفحة مسلسلات وصفحة تسجيل دخول"
      → ["movies.html", "series.html", "login.html"]
    """
    g = (user_goal or "").lower()
    page_map = [
        (("movies", "أفلام", "فيلم"), "movies.html"),
        (("series", "مسلسلات", "مسلسل"), "series.html"),
        (("anime", "أنمي"), "anime.html"),
        (("cart", "سلة", "العربة"), "cart.html"),
        (("checkout", "دفع", "إتمام الطلب"), "checkout.html"),
        (("profile", "حساب", "ملف شخصي"), "profile.html"),
        (("login", "تسجيل دخول", "دخول"), "login.html"),
        (("signup", "register", "إنشاء حساب", "تسجيل"), "signup.html"),
        (("products", "منتجات"), "products.html"),
        (("about", "من نحن"), "about.html"),
        (("contact", "تواصل", "اتصل"), "contact.html"),
        (("blog", "مدونة"), "blog.html"),
        (("menu", "منيو", "قائمة الطعام"), "menu.html"),
        (("delivery", "توصيل"), "delivery.html"),
        (("services", "خدمات"), "services.html"),
        (("pricing", "الأسعار"), "pricing.html"),
        (("gallery", "معرض"), "gallery.html"),
        (("dashboard", "لوحة تحكم"), "dashboard.html"),
        (("admin",), "admin.html"),
        (("orders", "طلبات"), "orders.html"),
    ]
    requested = []
    for keywords, filename in page_map:
        if any(k in g for k in keywords) and filename not in requested:
            requested.append(filename)
    return requested


def build_plan(
    user_goal: str,
    project_type: str,
    answers: Dict[str, Any],
    current_pages: List[str],
) -> Dict[str, Any]:
    """Convert collected discovery answers + user goal into a JSON plan.

    Returns:
      {
        "title": str,
        "summary": str,
        "steps": [
          {"id": "s1", "tool": "create_page", "args": {...}, "purpose": "..."},
          ...
        ],
        "cost_estimate": {"min": int, "expected": int, "max": int},
        "approval_required": True,
      }
    """
    steps: List[Dict[str, Any]] = []
    sid = 0

    def add(tool: str, args: Dict[str, Any], purpose: str):
        nonlocal sid
        sid += 1
        steps.append({"id": f"s{sid}", "tool": tool, "args": args,
                       "purpose": purpose, "done": False})

    # ─── Architecture detection ───────────────────────────────────────
    is_multi_page = _detect_multi_page_intent(user_goal, answers)
    requested_pages = _extract_requested_pages(user_goal) if is_multi_page else []

    # ─── MULTI-PAGE PATH: create separate .html files for each requested page
    if is_multi_page:
        # 1. Create every page the user explicitly named
        for page in requested_pages:
            if page not in current_pages and page != "index.html":
                add("create_page", {
                    "filename": page,
                    "title": _arabic_title_for(page, project_type),
                }, f"إنشاء الصفحة المستقلة {page} كملف HTML منفصل")
        # 2. If no pages explicitly named but project_type suggests structure,
        #    fall back to type-specific defaults (only for clearly multi-page types)
        if not requested_pages:
            if project_type == "ecommerce":
                for page in ("products.html", "cart.html", "about.html", "contact.html"):
                    if page not in current_pages:
                        add("create_page", {
                            "filename": page,
                            "title": _arabic_title_for(page, project_type),
                        }, f"إنشاء الصفحة المستقلة {page}")
            elif project_type == "portfolio":
                for page in ("projects.html", "about.html", "contact.html"):
                    if page not in current_pages:
                        add("create_page", {
                            "filename": page,
                            "title": _arabic_title_for(page, project_type),
                        }, f"إنشاء الصفحة المستقلة {page}")
        # 3. Build index.html as a real homepage (hero + page links + footer)
        #    — NOT a single-page template with all sections as placeholders
        add("apply_section", {
            "id": "hero", "op": "replace",
            "html": "<!-- Hero: عنوان المشروع + وصف موجز + CTA رئيسي -->",
        }, "بناء Hero للصفحة الرئيسية (index.html)")
        add("apply_section", {
            "id": "pages-nav", "op": "after", "ref_id": "hero",
            "html": "<!-- Grid of cards linking to each .html page -->",
        }, "إضافة بطاقات روابط للصفحات المنفصلة في index")
        add("apply_section", {
            "id": "footer", "op": "after", "ref_id": "pages-nav",
            "html": "<!-- Footer with contact + socials -->",
        }, "بناء الـ Footer")

    # ─── SINGLE-PAGE PATH: all sections inside index.html via apply_section
    else:
        if project_type == "ecommerce":
            add("apply_section", {
                "id": "hero", "op": "replace",
                "html": "<!-- Hero with product showcase + CTA -->",
            }, "بناء قسم البطل: عرض رئيسي + زر تسوّق")
            add("apply_section", {
                "id": "products", "op": "after", "ref_id": "hero",
                "html": "<!-- Product grid with real images -->",
            }, "بناء قسم المنتجات مع صور حقيقية وأزرار 'أضف للسلة' فعّالة")
            add("apply_section", {
                "id": "features", "op": "after", "ref_id": "products",
                "html": "<!-- Trust badges, shipping, returns -->",
            }, "بناء قسم المميزات + ضمان + شحن")
            add("apply_section", {
                "id": "footer", "op": "after", "ref_id": "features",
                "html": "<!-- Footer with contact + socials -->",
            }, "بناء الـ Footer مع التواصل والسوشيال")
        elif project_type == "portfolio":
            add("apply_section", {
                "id": "hero", "op": "replace",
                "html": "<!-- Hero: name + tagline + CTA -->",
            }, "بناء قسم البطل: الاسم + الوصف + CTA")
            add("apply_section", {
                "id": "featured", "op": "after", "ref_id": "hero",
                "html": "<!-- Featured projects grid -->",
            }, "عرض 3-6 مشاريع بارزة")
            add("apply_section", {
                "id": "skills", "op": "after", "ref_id": "featured",
                "html": "<!-- Skills / Tech stack -->",
            }, "قسم المهارات والتقنيات")
            add("apply_section", {
                "id": "contact", "op": "after", "ref_id": "skills",
                "html": "<!-- Contact form / links -->",
            }, "قسم التواصل")
        elif project_type == "saas_landing":
            add("apply_section", {"id": "hero", "op": "replace", "html": ""},
                 "Hero: المشكلة → الحل في 5 ثواني")
            add("apply_section", {"id": "features", "op": "after", "ref_id": "hero", "html": ""},
                 "3-6 مميزات أساسية مع icons")
            if answers.get("primary_cta"):
                add("apply_section", {"id": "cta", "op": "after", "ref_id": "features", "html": ""},
                     f"CTA رئيسي: {answers['primary_cta']}")
            add("apply_section", {"id": "pricing", "op": "after", "ref_id": "cta", "html": ""},
                 "قسم الأسعار")
            add("apply_section", {"id": "faq", "op": "after", "ref_id": "pricing", "html": ""},
                 "أسئلة شائعة")

    # 3. Verification step (always)
    add("self_test", {"scenarios": ["all buttons functional",
                                     "all nav links valid",
                                     "forms submit handler present"]},
         "اختبار ذاتي: كل الأزرار شغّالة، الـnav صحيح، النماذج تعمل")
    add("visual_snapshot", {}, "Snapshot نهائي للتحقق البصري")

    cost = estimate_plan_cost(steps)
    palette = answers.get("color_palette") or "الافتراضي"

    summary_lines = [
        f"📐 **خطة مشروع:** {_summarize_goal(user_goal)}",
        f"🎨 **اللوحة اللونية:** {palette}",
        f"📑 **عدد الخطوات:** {len(steps)}",
        f"💰 **تكلفة متوقعة:** {cost['expected']} شعلة (نطاق: {cost['min']}-{cost['max']})",
        "",
        "**الخطوات:**",
    ]
    for s in steps[:12]:
        summary_lines.append(f"  {s['id']}. {s['purpose']}")
    if len(steps) > 12:
        summary_lines.append(f"  … و {len(steps) - 12} خطوة أخرى")

    return {
        "title": f"خطة {_summarize_goal(user_goal)}",
        "summary": "\n".join(summary_lines),
        "steps": steps,
        "cost_estimate": cost,
        "approval_required": True,
        "answers_used": answers,
    }


# ─── Helpers ──────────────────────────────────────────────────────────
def _arabic_title_for(filename: str, project_type: str) -> str:
    stem = filename.replace(".html", "")
    mapping = {
        "about": "من نحن",
        "contact": "تواصل معنا",
        "products": "المنتجات",
        "projects": "المشاريع",
        "services": "خدماتنا",
        "pricing": "الأسعار",
        "blog": "المدوّنة",
        "faq": "أسئلة شائعة",
    }
    return mapping.get(stem, stem.replace("-", " ").title())


def _summarize_goal(goal: str) -> str:
    g = (goal or "").strip()[:60]
    return g if g else "مشروع جديد"
