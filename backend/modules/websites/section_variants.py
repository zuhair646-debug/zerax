"""
Section-level style variants catalog.

Each section type can have multiple visual styles. The renderer reads
`section.data.style` to pick the variant. The UI reads this catalog to
show the client a picker per section.
"""

CATALOG = {
    "menu": {
        "label": "قائمة الطعام",
        "variants": [
            {"id": "grid", "label": "شبكة بصور", "description": "بطاقات مع صور — الأمثل للمطاعم البصرية"},
            {"id": "list", "label": "قائمة أنيقة", "description": "تخطيط قائمة رأسية مع نقاط تربط الاسم بالسعر"},
            {"id": "carousel", "label": "شريط أفقي", "description": "بطاقات متحركة أفقياً — عصري ومشوق"},
        ],
    },
    "gallery": {
        "label": "المعرض",
        "variants": [
            {"id": "grid", "label": "شبكة منتظمة", "description": "مربعات متساوية — كلاسيكي"},
            {"id": "masonry", "label": "Pinterest Masonry", "description": "أعمدة بصور بأحجام مختلفة"},
            {"id": "strip", "label": "شريط أفقي", "description": "تمرير أفقي بأسلوب cinematic"},
        ],
    },
    "testimonials": {
        "label": "آراء العملاء",
        "variants": [
            {"id": "grid", "label": "بطاقات", "description": "بطاقات مع تقييم نجوم"},
            {"id": "carousel", "label": "شريط أفقي", "description": "بطاقات متحركة — أكثر حيوية"},
            {"id": "quote-big", "label": "اقتباسات كبيرة", "description": "حجم كبير مع شريط ذهبي على الجانب"},
        ],
    },
    "team": {
        "label": "الفريق",
        "variants": [
            {"id": "grid", "label": "شبكة بصور مربعة", "description": "الأسلوب الافتراضي"},
            {"id": "circles", "label": "صور دائرية", "description": "مناسب للصالون/العيادات"},
            {"id": "rows", "label": "صفوف أفقية", "description": "مثل قائمة اتصال — رسمي"},
        ],
    },
    "pricing": {
        "label": "الأسعار",
        "variants": [
            {"id": "cards", "label": "بطاقات", "description": "3 خطط جنباً إلى جنب"},
            {"id": "table", "label": "جدول مقارنة", "description": "ميزات الصفوف × خطط الأعمدة — شامل"},
            {"id": "minimal", "label": "قائمة بسيطة", "description": "صف واحد لكل خطة — أنيق"},
        ],
    },
}


def get_variants_for_type(section_type: str):
    """Return the variants list for a given section type, or [] if none."""
    entry = CATALOG.get(section_type)
    if not entry:
        return []
    return entry.get("variants", [])


def catalog_public():
    """Return full catalog for the client dashboard UI."""
    return CATALOG
