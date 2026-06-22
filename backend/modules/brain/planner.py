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

    # ─── Plan synthesis based on project type ─────────────────────────
    structure = answers.get("site_structure") or answers.get("section_layout") or ""
    is_multi_page = ("صفحات متعددة" in structure
                      or "multi" in structure.lower()
                      or "metric" in structure.lower())

    # 1. Create core pages (if multi-page)
    if is_multi_page and "about.html" not in current_pages:
        if project_type == "ecommerce":
            for page in ("products.html", "about.html", "contact.html"):
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

    # 2. Build the homepage sections (depends on type)
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
