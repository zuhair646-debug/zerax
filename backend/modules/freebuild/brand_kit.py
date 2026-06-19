"""AI Memory & Brand Kit — persistent customer preferences across projects.

A user's brand_kit lives at db.user_brand_kits and contains preferences they
have established over time: preferred colors, fonts, tone, industries built,
contact details, etc. The chat endpoint injects this into extra_ctx so the AI
starts every new project already knowing the customer.

We also passively *learn* from each project — after each `current_html` is
saved we extract obvious signals (dominant color, industry keywords) and merge
them into the brand_kit.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_brand_kit(db, user_id: str) -> Dict:
    """Fetch the user's brand kit; create empty doc if missing."""
    doc = await db.user_brand_kits.find_one({"user_id": user_id}, {"_id": 0})
    if doc:
        return doc
    new_kit = {
        "user_id": user_id,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "preferred_colors": [],        # e.g. ["#F4A261", "#E76F51"]
        "preferred_fonts": [],         # e.g. ["Cairo", "Tajawal"]
        "brand_voice": None,           # "ودود" | "فاخر" | "جريء" | "هادي"
        "industries": [],              # e.g. ["restaurant", "fitness"]
        "logo_url": None,
        "company_name": None,
        "contact_phone": None,
        "contact_email": None,
        "whatsapp": None,
        "tax_number": None,
        "commercial_registry": None,
        "project_count": 0,
        "notes": [],                   # free-form notes from past projects
    }
    await db.user_brand_kits.insert_one(new_kit)
    return new_kit


async def update_brand_kit(db, user_id: str, updates: Dict) -> None:
    """Merge updates into the user's brand kit."""
    updates["updated_at"] = _now_iso()
    await db.user_brand_kits.update_one(
        {"user_id": user_id},
        {"$set": updates},
        upsert=True,
    )


def format_brand_kit_for_prompt(kit: Dict) -> str:
    """Render the brand kit as an Arabic block for the AI system prompt.
    Returns empty string if the kit has no useful data yet."""
    if not kit:
        return ""

    interesting_fields = [
        kit.get("preferred_colors"),
        kit.get("preferred_fonts"),
        kit.get("brand_voice"),
        kit.get("industries"),
        kit.get("company_name"),
        kit.get("contact_phone"),
        kit.get("logo_url"),
    ]
    if not any(interesting_fields):
        return ""  # no meaningful preferences yet — don't pollute prompt

    lines = ["\n🧠 **هوية العميل المعروفة (Brand Kit — من المشاريع السابقة)**:"]
    pc = kit.get("preferred_colors") or []
    if pc:
        lines.append(f"  • ألوانه المفضّلة: {', '.join(pc[:5])}")
    pf = kit.get("preferred_fonts") or []
    if pf:
        lines.append(f"  • خطوطه: {', '.join(pf[:3])}")
    if kit.get("brand_voice"):
        lines.append(f"  • نبرته: {kit['brand_voice']}")
    inds = kit.get("industries") or []
    if inds:
        lines.append(f"  • قطاعاته السابقة: {', '.join(inds[-5:])}")
    if kit.get("company_name"):
        lines.append(f"  • اسم الشركة: {kit['company_name']}")
    if kit.get("contact_phone"):
        lines.append(f"  • هاتف الاتصال: {kit['contact_phone']}")
    if kit.get("whatsapp"):
        lines.append(f"  • WhatsApp: {kit['whatsapp']}")
    if kit.get("logo_url"):
        lines.append(f"  • شعار جاهز: {kit['logo_url']}")
    notes = kit.get("notes") or []
    if notes:
        lines.append(f"  • ملاحظات سابقة: {' | '.join(notes[-3:])}")
    pcount = kit.get("project_count", 0)
    if pcount > 0:
        lines.append(f"  • هذا مشروعه رقم {pcount + 1} معنا — كن طبيعياً، تكلّم بألفة.")
    lines.append("استخدم هذي المعلومات بطبيعية في التصميم بدون ما تذكرها صراحة للعميل.\n")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# PASSIVE LEARNING — extract signals from the generated HTML
# ──────────────────────────────────────────────────────────────────────────────

INDUSTRY_KEYWORDS = {
    "restaurant": ["مطعم", "قائمة طعام", "وجبات", "طلب", "كافيه", "مقهى"],
    "fitness": ["لياقة", "تدريب", "جيم", "صالة", "مدرّب", "تخسيس"],
    "salon": ["صالون", "حلاقة", "تجميل", "مكياج", "أظافر"],
    "clinic": ["عيادة", "طبيب", "كشف", "علاج", "حجز موعد"],
    "ecommerce": ["متجر", "تسوق", "منتجات", "سلة", "إضافة للسلة"],
    "education": ["أكاديمية", "دورات", "تعلّم", "كورس", "مدرسة"],
    "realestate": ["عقار", "شقق", "فلل", "إيجار", "بيع"],
    "automotive": ["سيارات", "مركبات", "صيانة", "ورشة"],
    "beauty": ["تجميل", "عناية", "بشرة", "شعر"],
    "education": ["تعليم", "دورة", "تدريب"],
    "tech": ["برمجة", "تطبيق", "موقع", "تقنية"],
    "pets": ["حيوانات", "قطط", "كلاب", "بيطرية"],
}


def _detect_industry(html: str) -> Optional[str]:
    text = re.sub(r"<[^>]+>", " ", html)  # strip tags
    text_low = text.lower()
    scores: Dict[str, int] = {}
    for ind, kws in INDUSTRY_KEYWORDS.items():
        for kw in kws:
            if kw in text_low:
                scores[ind] = scores.get(ind, 0) + 1
    if not scores:
        return None
    return max(scores, key=scores.get)


def _extract_colors(html: str) -> List[str]:
    """Pull hex colors from inline style/CSS — top 5 unique."""
    hexes = re.findall(r"#([0-9a-fA-F]{6})\b", html)
    if not hexes:
        return []
    counts = Counter(hexes)
    return [f"#{c}" for c, _ in counts.most_common(5)]


def _extract_fonts(html: str) -> List[str]:
    """Find Google Font names used."""
    fonts: List[str] = []
    for m in re.finditer(r"fonts\.googleapis\.com/css2\?family=([A-Za-z+]+)", html):
        name = m.group(1).replace("+", " ")
        if name not in fonts:
            fonts.append(name)
    return fonts


def extract_signals_from_html(html: str) -> Dict:
    """Return signals to merge into the brand kit."""
    if not html:
        return {}
    return {
        "colors": _extract_colors(html)[:3],
        "fonts": _extract_fonts(html)[:2],
        "industry": _detect_industry(html),
    }


async def learn_from_project(db, user_id: str, html: str, project_name: str = "") -> None:
    """Merge signals from a completed project into the user's brand kit."""
    signals = extract_signals_from_html(html)
    if not any(signals.values()):
        return
    kit = await get_brand_kit(db, user_id)
    # Merge colors (most-recent prepended)
    if signals.get("colors"):
        existing = list(kit.get("preferred_colors") or [])
        new_colors = [c for c in signals["colors"] if c not in existing]
        # cap to last 10
        kit["preferred_colors"] = (new_colors + existing)[:10]
    if signals.get("fonts"):
        existing = list(kit.get("preferred_fonts") or [])
        for f in signals["fonts"]:
            if f not in existing:
                existing.insert(0, f)
        kit["preferred_fonts"] = existing[:5]
    if signals.get("industry"):
        ind_list = list(kit.get("industries") or [])
        ind = signals["industry"]
        if ind not in ind_list:
            ind_list.append(ind)
        kit["industries"] = ind_list[-10:]
    kit["project_count"] = int(kit.get("project_count") or 0) + 1
    notes = list(kit.get("notes") or [])
    if project_name:
        notes.append(f"{project_name} ({signals.get('industry') or 'misc'})")
    kit["notes"] = notes[-15:]
    await update_brand_kit(db, user_id, kit)


__all__ = [
    "get_brand_kit",
    "update_brand_kit",
    "format_brand_kit_for_prompt",
    "learn_from_project",
    "extract_signals_from_html",
]
