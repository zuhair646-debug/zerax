"""Ready Sites — Catalog of types, visual patterns, and per-type features."""
from __future__ import annotations
from typing import Any, Dict, List, Optional


SITE_TYPES: List[Dict[str, Any]] = [
    {
        "id": "restaurant",
        "name_ar": "مطاعم وكافيهات",
        "name_en": "Restaurants & Cafes",
        "tagline_ar": "موقع كامل: قائمة طعام · سلة · توصيل · حجوزات · لوحة إدارة",
        "icon": "utensils",
        "available": True,
        "preview_color": "#f59e0b",
    },
    {
        "id": "store",
        "name_ar": "متجر إلكتروني",
        "name_en": "E-commerce Store",
        "tagline_ar": "قريباً — متجر منتجات مع شحن ومخزون",
        "icon": "shopping-bag",
        "available": False,
        "preview_color": "#10b981",
    },
    {
        "id": "clinic",
        "name_ar": "عيادة طبية",
        "name_en": "Medical Clinic",
        "tagline_ar": "قريباً — حجز مواعيد وملف مريض",
        "icon": "stethoscope",
        "available": False,
        "preview_color": "#06b6d4",
    },
    {
        "id": "realestate",
        "name_ar": "عقارات",
        "name_en": "Real Estate",
        "tagline_ar": "قريباً — معرض عقارات وجولات افتراضية",
        "icon": "home",
        "available": False,
        "preview_color": "#a855f7",
    },
]


# 4 distinct restaurant patterns (no templates — AI builds each from scratch in the style).
RESTAURANT_PATTERNS: List[Dict[str, Any]] = [
    {
        "id": "neon_crescent",
        "name": "Neon Crescent",
        "name_ar": "الهلال النيوني",
        "vibe": "NEON · 3D PLATES · GEN-Z",
        "vibe_ar": "نيون · أطباق ثلاثية الأبعاد · جيل Z",
        "preview_url": "/patterns/neon_crescent.html",
        "design_directive": (
            "Top pill-nav with neon glow. Radial gradient hero (deep purple → black). "
            "Bold gradient title (yellow→pink). 3 floating 3D circular 'plates' with neon shadow "
            "and price tags. Big rounded CTA. Energetic, Gen-Z, vibrant. Sticky bottom action bar. "
            "Use deep purples/blacks with hot pink+amber+cyan neon accents. Animate plates with subtle float."
        ),
        "palette": ["#0a0a0b", "#1e0a2e", "#ec4899", "#a855f7", "#fbbf24", "#06b6d4"],
        "fonts": ["Tajawal", "Cairo"],
    },
    {
        "id": "split_theatre",
        "name": "Split Theatre",
        "name_ar": "المسرح المنقسم",
        "vibe": "CINEMATIC · 50/50 · LUXURY",
        "vibe_ar": "سينمائي · 50/50 · فاخر",
        "preview_url": "/patterns/split_theatre.html",
        "design_directive": (
            "Full-height 50/50 vertical split layout. LEFT half: dark luxury menu (printed-book feel) "
            "with serif headings, dotted leaders between dish names and prices, sections like Starters/Mains/Desserts. "
            "RIGHT half: large cinematic food hero image with dark gradient overlay and a floating glassy 'watch video' pill. "
            "Color palette: black + ivory + warm amber. Use serif typography for English brand name + Arabic Tajawal for body. "
            "Quiet, refined, fine-dining aesthetic."
        ),
        "palette": ["#000000", "#0f0f0f", "#f59e0b", "#fafaf9", "#1a1a1a"],
        "fonts": ["Playfair Display", "Tajawal"],
    },
    {
        "id": "orbital_menu",
        "name": "Orbital Menu",
        "name_ar": "القائمة المدارية",
        "vibe": "FUTURISTIC · ORBIT · UNIQUE",
        "vibe_ar": "مستقبلي · مدار دائري · فريد",
        "preview_url": "/patterns/orbital_menu.html",
        "design_directive": (
            "Hero centered on a glowing cyan/blue circular 'core' with the brand name inside. "
            "Around the core: 6 floating service nodes (delivery, reservations, menu, gallery, gift, reviews) "
            "positioned on a dashed orbital ring. Background: radial blue→black with subtle starfield/grain. "
            "Use this orbit metaphor as the navigation. The rest of the page is sectioned with sci-fi panels. "
            "Strong futuristic and unique — must feel like a space dashboard. Cyan, navy, white."
        ),
        "palette": ["#000000", "#0a1929", "#06b6d4", "#1e40af", "#ffffff"],
        "fonts": ["Tajawal", "Orbitron"],
    },
    {
        "id": "mosaic_liquid",
        "name": "Mosaic Liquid",
        "name_ar": "الفسيفساء السائلة",
        "vibe": "BOLD · ASYMMETRIC · ZEN-Z",
        "vibe_ar": "جريء · غير متناسق · Z-Zen",
        "preview_url": "/patterns/mosaic_liquid.html",
        "design_directive": (
            "Hero is a 3-column asymmetric bento grid: one BIG tile (red→black gradient) showcasing the signature dish, "
            "and 4 smaller tiles (vegan, spicy, reservations, drive-thru) in liquid-shaped border radius (e.g. 32px 8px 32px 8px). "
            "Each tile has bold gradient backgrounds (emerald, amber, purple, sky) with a single emoji-style icon and short label. "
            "Top bar: bold black logo + a white pill 'احجز طاولة' button. Big bold sans-serif typography, "
            "playful, social-media-ready aesthetic. White background with dark cards."
        ),
        "palette": ["#000000", "#dc2626", "#10b981", "#f59e0b", "#a855f7", "#0ea5e9"],
        "fonts": ["Tajawal", "Cairo"],
    },
]


# 24 deep restaurant features. AI must wire ALL enabled features into the generated site.
RESTAURANT_FEATURES: List[Dict[str, Any]] = [
    {"id": "menu", "name_ar": "قائمة طعام تفاعلية مع صور وأسعار", "category": "core", "default": True},
    {"id": "cart", "name_ar": "سلة شراء كاملة مع حساب الإجمالي", "category": "core", "default": True},
    {"id": "checkout", "name_ar": "صفحة دفع (Stripe/Tap/Moyasar) — placeholder", "category": "core", "default": True},
    {"id": "delivery", "name_ar": "نظام توصيل: عنوان + خريطة + خطوات الطلب", "category": "core", "default": True},
    {"id": "pickup", "name_ar": "خيار الاستلام من المطعم (Pickup)", "category": "core", "default": True},
    {"id": "reservations", "name_ar": "حجز طاولات (تاريخ + عدد الأشخاص)", "category": "core", "default": True},
    {"id": "gallery", "name_ar": "معرض صور للأطباق والمطعم", "category": "marketing", "default": True},
    {"id": "specials", "name_ar": "عروض اليوم وقسم 'الطبق المميز'", "category": "marketing", "default": True},
    {"id": "loyalty", "name_ar": "برنامج ولاء (نقاط لكل طلب)", "category": "marketing", "default": True},
    {"id": "reviews", "name_ar": "آراء العملاء + نظام تقييم بالنجوم", "category": "social", "default": True},
    {"id": "contact", "name_ar": "تواصل: واتساب + هاتف + خريطة الموقع", "category": "core", "default": True},
    {"id": "hours", "name_ar": "ساعات العمل وحالة 'مفتوح/مغلق' الحية", "category": "core", "default": True},
    {"id": "branches", "name_ar": "تعدد الفروع مع اختيار الفرع", "category": "operations", "default": True},
    {"id": "languages", "name_ar": "عربي + إنجليزي (RTL + LTR)", "category": "core", "default": True},
    {"id": "search", "name_ar": "بحث في القائمة (filter بالاسم/الفئة)", "category": "core", "default": True},
    {"id": "filters", "name_ar": "تصفية: نباتي / حار / حلال / خالي من الجلوتين", "category": "core", "default": True},
    {"id": "promo_codes", "name_ar": "أكواد خصم وكوبونات", "category": "marketing", "default": True},
    {"id": "newsletter", "name_ar": "اشتراك في نشرة العروض", "category": "marketing", "default": True},
    {"id": "events", "name_ar": "فعاليات وحفلات خاصة", "category": "marketing", "default": True},
    {"id": "catering", "name_ar": "خدمة تجهيز الحفلات (Catering)", "category": "operations", "default": True},
    {"id": "gift_cards", "name_ar": "بطاقات إهداء رقمية", "category": "marketing", "default": True},
    {"id": "admin_panel", "name_ar": "لوحة إدارة (طلبات + قائمة + تقارير)", "category": "admin", "default": True},
    {"id": "driver_app", "name_ar": "تطبيق سائق التوصيل (واجهة منفصلة)", "category": "admin", "default": True},
    {"id": "analytics", "name_ar": "تحليلات بسيطة (أكثر طبق مبيعاً)", "category": "admin", "default": True},
]


def get_type(type_id: str) -> Optional[Dict[str, Any]]:
    for t in SITE_TYPES:
        if t["id"] == type_id:
            return t
    return None


def get_pattern(type_id: str, pattern_id: str) -> Optional[Dict[str, Any]]:
    if type_id != "restaurant":
        return None
    for p in RESTAURANT_PATTERNS:
        if p["id"] == pattern_id:
            return p
    return None
