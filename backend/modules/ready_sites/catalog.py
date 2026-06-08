"""Ready Sites — Catalog of types, visual patterns, and per-type features.

Design philosophy (Feb 2026 v2 — inspired by 14 real-world restaurant references):
- The homepage MUST be clean and visually-stunning. Photos do the talking, not buttons.
- WhatsApp, reservations, hours, contact form, social links → ALL belong in the FOOTER.
- No floating chat bubbles, no contact widgets mid-page, no reservation forms in the hero.
- Each pattern has a distinct PERSONALITY (cinematic / heritage / vegan / burger-cinema / rustic / brush-art).
"""
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


# 6 distinct restaurant patterns, deeply inspired by the 14 real references.
# Each pattern is a complete personality, not a template.
RESTAURANT_PATTERNS: List[Dict[str, Any]] = [
    {
        "id": "fork_noir",
        "name": "Fork Noir",
        "name_ar": "الشوكة السوداء",
        "vibe": "CINEMATIC · BLACK · FINE DINING",
        "vibe_ar": "سينمائي · أسود · فاخر",
        "preview_url": "/patterns/fork_noir.html",
        "design_directive": (
            "ULTRA-CINEMATIC homepage. Pure deep black background (#0a0a0a). "
            "Single colossal hero image: a silver fork lifting twirled pasta/noodles photographed against pitch black, "
            "occupying the RIGHT 55% of the screen edge-to-edge top-to-bottom. "
            "LEFT 45% contains: a slim minimalist top-left logo (typographic only, champagne color #c8a97e), "
            "horizontal nav bar (Home · Menu · Gallery · About), big serif italic Playfair Display title 'A genuine taste of...' "
            "with the cuisine type on the second line, and a single 'Order now' rectangular outlined button (no fill, champagne border). "
            "No phone, no WhatsApp, no hours visible on hero. "
            "Below the hero: a sticky horizontal scrolling category bar (Soups · Mains · Pizza · Drinks · Desserts) styled as rounded chips. "
            "Then a clean 3-column grid of dish cards on dark background. "
            "Quiet, refined, intimate fine-dining aesthetic. ZERO clutter."
        ),
        "palette": ["#0a0a0a", "#1a1a1a", "#c8a97e", "#e8d5b7", "#ffffff"],
        "fonts": ["Playfair Display", "Tajawal"],
    },
    {
        "id": "verdant_organic",
        "name": "Verdant Organic",
        "name_ar": "الأخضر العضوي",
        "vibe": "VEGAN · BRIGHT · WELLNESS",
        "vibe_ar": "نباتي · مشرق · صحي",
        "preview_url": "/patterns/verdant_organic.html",
        "design_directive": (
            "Split-screen hero: TOP HALF is a deep forest-night background (#0d1f1a) with serif italic 'Cozy' "
            "in green over a bold 'Vegetarian Restaurant' title, accompanied by a round white plate "
            "showcasing a colorful salad/bowl framed with a vivid green border (#22c55e). "
            "BOTTOM HALF is pure white showing: a split section with a dark food photo card on the left and "
            "an 'About us' paragraph + green pill CTA on the right. "
            "Below: 'Top Items We Have In' label + 4 round category icons (Lunch · Dinner · Dessert · Drinks). "
            "Then: a dark navy footer band with 'Food Menu' tabs styled as horizontal pills (active = green fill, others = white outline). "
            "Use a bright fresh green as the dominant accent. White feels clean and airy."
        ),
        "palette": ["#0d1f1a", "#22c55e", "#86efac", "#ffffff", "#f7fdf9"],
        "fonts": ["Playfair Display", "Tajawal"],
    },
    {
        "id": "saudi_heritage",
        "name": "Saudi Heritage",
        "name_ar": "التراث السعودي",
        "vibe": "TRADITIONAL · MAROON · WARM",
        "vibe_ar": "تراثي · عنّابي · دافئ",
        "preview_url": "/patterns/saudi_heritage.html",
        "design_directive": (
            "Authentically Saudi/Yemeni restaurant homepage. "
            "TOP: a tall ~50vh hero with a moody backdrop (charcoal+wood texture) and a HUGE round decorative ceramic plate "
            "(filled with golden mandi/biryani topped with grilled chicken) positioned LEFT, "
            "while the right side has the brand name in elegant Arabic Tajawal extra-bold + a 2-line tagline + "
            "a single outlined contact pill 'للاتصال بنا' (this is the ONLY contact mention on the homepage). "
            "BELOW: pure white section with ornamental gold divider + section title 'منيو المطعم' in burgundy. "
            "Then a CLEAN 3×3 grid of category cards (Pizza / Broast / Salads / Shawarma / Meat / Chicken / Sandwiches / Sweets / Soups) — "
            "each card is white with a soft shadow, a centered round food photo on top, burgundy title, gray subtitle. "
            "Burgundy/maroon header band (#7a1f2b) with logo on the right + horizontal nav. "
            "Avoid bright colors except sparingly. Feels like a respected family restaurant in Riyadh."
        ),
        "palette": ["#7a1f2b", "#a52a2a", "#b89968", "#fdfaf6", "#1a1a1a"],
        "fonts": ["Tajawal", "Amiri"],
    },
    {
        "id": "burger_cinema",
        "name": "Burger Cinema",
        "name_ar": "سينما البرجر",
        "vibe": "BOLD · RED · FAST-FOOD CINEMA",
        "vibe_ar": "جريء · أحمر · سينمائي",
        "preview_url": "/patterns/burger_cinema.html",
        "design_directive": (
            "BOLD fast-food cinematic homepage. Strong vertical SECTION RHYTHM alternating crimson red → black → cream. "
            "SECTION 1 (red): top nav (transparent), a giant 'World Famous Burger' headline on the LEFT in white serif, "
            "with a massive professional burger photo on the RIGHT (juicy, sliced, dripping cheese, with dramatic lighting). "
            "Price chip overlay '$12.50' at bottom-left of the photo. "
            "SECTION 2 (BLACK): 'Today Special' label + 4 product cards in a horizontal scroll (each card has dish photo, name, price, '+' button). "
            "SECTION 3 (CREAM #fdf6e8): 'Free delivery 7 days a week' big title with a glove-holding takeout bag photo on the left, "
            "and 3 feature rows (Quality Burgers · Diet Options · Code Burger) on the right with tiny icons. "
            "SECTION 4 (red again): huge italic outlined 'Reviews' text behind 3 customer cards with avatars + stars. "
            "Bold sans-serif Bebas Neue/Anton for English, Tajawal-Black for Arabic. Sticky red bottom-right cart pill."
        ),
        "palette": ["#dc2626", "#000000", "#fdf6e8", "#fbbf24", "#ffffff"],
        "fonts": ["Bebas Neue", "Tajawal"],
    },
    {
        "id": "rustic_plank",
        "name": "Rustic Plank",
        "name_ar": "الخشب الريفي",
        "vibe": "RUSTIC · WOODEN · ARTISAN",
        "vibe_ar": "ريفي · خشب · حِرفي",
        "preview_url": "/patterns/rustic_plank.html",
        "design_directive": (
            "ARTISAN rustic homepage. The OUTER body is a high-resolution dark walnut WOODEN PLANK TEXTURE (use a CSS gradient + noise to simulate). "
            "The MAIN content sits as a large white CARD (with subtle drop-shadow + ~24px border-radius) floating on top of the wood. "
            "Scattered around the card edges (peeking from behind): photos of spices in small dishes (top-left), succulents (bottom-left and top-right), "
            "a wooden cutting board with a burger or sandwich (LEFT half of hero), and falling french fries. "
            "Inside the card: top nav (Home · Special Menu · Foods · Drinks · Contact) with active item in RED, "
            "BIG centered title 'ONE-STOP / DELICIOUS / FOODS PLACE' with the middle word in screaming red, "
            "a paragraph of warm welcoming copy, and a single red ORDER NOW pill button. "
            "Below: a horizontal slider with 4 dish cards. "
            "Authentic, hand-curated, farm-to-table aesthetic. Earthy and inviting."
        ),
        "palette": ["#5d3a1f", "#dc2626", "#fdfaf6", "#86efac", "#1a1a1a"],
        "fonts": ["Poppins", "Tajawal"],
    },
    {
        "id": "brush_italian",
        "name": "Brush Italian",
        "name_ar": "الفرشاة الإيطالية",
        "vibe": "BRUSH ART · MINT · PIZZERIA",
        "vibe_ar": "فني · نعناعي · بيتزيريا",
        "preview_url": "/patterns/brush_italian.html",
        "design_directive": (
            "ARTISANAL Italian pizzeria homepage. Diagonal background SPLIT: top-left corner shows a warm amber/gold triangle "
            "(#f59e0b at 30% opacity), bottom-right shows a soft cool gray triangle — creating a subtle painterly diagonal cut. "
            "The main content sits as a giant browser-mockup with rounded corners + drop shadow. "
            "Inside the mockup: DARK NAV BAR (charcoal #1a1a1a) with the bilingual logo centered (English Italian script on top + Arabic name below), "
            "and nav items styled as Permanent Marker / handwritten brush font (Home · About · Our Secret · Menu · Gallery · Reservation · Contact · Order). "
            "HERO: a full-bleed dramatic photo of two hands tearing/sharing a steaming pizza slice (close-up cinematic), "
            "with HUGE handwritten brush-style title 'ITALIAN CUISINE' in white over the dark side of the image, "
            "and a single WHITE OUTLINED 'RESERVE NOW' pill button below. 3 carousel dots (active = mint green #34d399) at the bottom-center of hero. "
            "BELOW: 'About Us' card on the left with brush-style label and read-more link, "
            "and 2 atmospheric food photos (risotto + pasta in foil) stacked on the right. "
            "Mint green is used ONLY for tiny accents (active dot, CTA hover, brush underline). "
            "Hand-drawn, authentic, mediterranean pizzeria feel."
        ),
        "palette": ["#1a1a1a", "#f59e0b", "#34d399", "#fdfaf6", "#a8a29e"],
        "fonts": ["Permanent Marker", "Tajawal"],
    },
]


# 24 deep restaurant features. AI must wire ALL enabled features into the generated site.
# IMPORTANT: All contact/reservation/whatsapp/hours features RENDER IN FOOTER (or a dedicated section near bottom),
# never in the middle of the page or as floating widgets on the hero.
RESTAURANT_FEATURES: List[Dict[str, Any]] = [
    {"id": "menu", "name_ar": "قائمة طعام تفاعلية مع صور وأسعار", "category": "core", "default": True},
    {"id": "cart", "name_ar": "سلة شراء كاملة مع حساب الإجمالي", "category": "core", "default": True},
    {"id": "checkout", "name_ar": "صفحة دفع (Stripe/Tap/Moyasar) — placeholder", "category": "core", "default": True},
    {"id": "delivery", "name_ar": "نظام توصيل: عنوان + خريطة + خطوات الطلب", "category": "core", "default": True},
    {"id": "pickup", "name_ar": "خيار الاستلام من المطعم (Pickup)", "category": "core", "default": True},
    {"id": "reservations", "name_ar": "حجز طاولات (في الفوتر فقط)", "category": "core", "default": True},
    {"id": "gallery", "name_ar": "معرض صور للأطباق والمطعم", "category": "marketing", "default": True},
    {"id": "specials", "name_ar": "عروض اليوم وقسم 'الطبق المميز'", "category": "marketing", "default": True},
    {"id": "loyalty", "name_ar": "برنامج ولاء (نقاط لكل طلب)", "category": "marketing", "default": True},
    {"id": "reviews", "name_ar": "آراء العملاء + نظام تقييم بالنجوم", "category": "social", "default": True},
    {"id": "contact", "name_ar": "تواصل: واتساب + هاتف + خريطة (في الفوتر فقط)", "category": "footer", "default": True},
    {"id": "hours", "name_ar": "ساعات العمل وحالة 'مفتوح/مغلق' (في الفوتر)", "category": "footer", "default": True},
    {"id": "branches", "name_ar": "تعدد الفروع مع اختيار الفرع", "category": "operations", "default": True},
    {"id": "languages", "name_ar": "عربي + إنجليزي (RTL + LTR)", "category": "core", "default": True},
    {"id": "search", "name_ar": "بحث في القائمة (filter بالاسم/الفئة)", "category": "core", "default": True},
    {"id": "filters", "name_ar": "تصفية: نباتي / حار / حلال / خالي من الجلوتين", "category": "core", "default": True},
    {"id": "promo_codes", "name_ar": "أكواد خصم وكوبونات", "category": "marketing", "default": True},
    {"id": "newsletter", "name_ar": "اشتراك في نشرة العروض (في الفوتر)", "category": "footer", "default": True},
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
