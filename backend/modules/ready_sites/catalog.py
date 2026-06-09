"""Ready Sites — Catalog of types, visual patterns, and per-type features.

Design philosophy (Feb 2026 v3):
- Each business type has 4-6 distinct visual patterns + 20+ features.
- Homepage = clean & cinematic. Contact/booking/hours = footer.
- AI prompt is steered through `design_directive` + Python data injection.
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
        "tagline_ar": "متجر منتجات + سلة + توصيل + لوحة إدارة + تتبع مخزون",
        "icon": "shopping-bag",
        "available": True,
        "preview_color": "#10b981",
    },
    {
        "id": "clinic",
        "name_ar": "عيادة طبية",
        "name_en": "Medical Clinic",
        "tagline_ar": "حجز مواعيد + ملفات مرضى + أطباء + لوحة إدارة",
        "icon": "stethoscope",
        "available": True,
        "preview_color": "#06b6d4",
    },
    {
        "id": "realestate",
        "name_ar": "عقارات",
        "name_en": "Real Estate",
        "tagline_ar": "معرض عقارات + استفسارات + وسطاء + خرائط + لوحة إدارة",
        "icon": "home",
        "available": True,
        "preview_color": "#a855f7",
    },
]


# ───────────────────────── RESTAURANT PATTERNS ─────────────────────────
RESTAURANT_PATTERNS: List[Dict[str, Any]] = [
    {
        "id": "fork_noir", "name": "Fork Noir", "name_ar": "الشوكة السوداء",
        "vibe": "CINEMATIC · BLACK · FINE DINING", "vibe_ar": "سينمائي · أسود · فاخر",
        "preview_url": "/patterns/fork_noir.html",
        "design_directive": (
            "ULTRA-CINEMATIC homepage. Pure deep black (#0a0a0a). Single colossal hero image: silver fork lifting twirled pasta against pitch black, "
            "right 55% of screen. Left 45%: champagne #c8a97e minimalist logo, horizontal nav, big serif italic Playfair Display title 'A genuine taste of...', "
            "single outlined 'Order now' button. No phone, no WhatsApp on hero. Sticky horizontal category chips below. 3-column dish grid on dark. Quiet, refined."
        ),
        "palette": ["#0a0a0a", "#1a1a1a", "#c8a97e", "#e8d5b7", "#ffffff"],
        "fonts": ["Playfair Display", "Tajawal"],
    },
    {
        "id": "verdant_organic", "name": "Verdant Organic", "name_ar": "الأخضر العضوي",
        "vibe": "VEGAN · BRIGHT · WELLNESS", "vibe_ar": "نباتي · مشرق · صحي",
        "preview_url": "/patterns/verdant_organic.html",
        "design_directive": (
            "Split hero: top half deep forest-night (#0d1f1a) with green-bordered colorful salad plate, bottom half pure white. "
            "Round category icons (Lunch/Dinner/Dessert/Drinks). Dark navy footer band with pill tabs. Bright fresh green accent."
        ),
        "palette": ["#0d1f1a", "#22c55e", "#86efac", "#ffffff", "#f7fdf9"],
        "fonts": ["Playfair Display", "Tajawal"],
    },
    {
        "id": "saudi_heritage", "name": "Saudi Heritage", "name_ar": "التراث السعودي",
        "vibe": "TRADITIONAL · MAROON · WARM", "vibe_ar": "تراثي · عنّابي · دافئ",
        "preview_url": "/patterns/saudi_heritage.html",
        "design_directive": (
            "Authentically Saudi homepage. Tall ~50vh hero: charcoal+wood texture backdrop, huge round ceramic plate with golden mandi/biryani on LEFT, "
            "brand name in Tajawal extra-bold + tagline + single outlined 'للاتصال بنا' pill on right. Burgundy header band #7a1f2b. White section with gold divider + "
            "burgundy section title. Clean 3x3 grid of category cards (Pizza/Broast/Salads/Shawarma/Meat/Chicken). Family-restaurant feel."
        ),
        "palette": ["#7a1f2b", "#a52a2a", "#b89968", "#fdfaf6", "#1a1a1a"],
        "fonts": ["Tajawal", "Amiri"],
    },
    {
        "id": "burger_cinema", "name": "Burger Cinema", "name_ar": "سينما البرجر",
        "vibe": "BOLD · RED · FAST-FOOD CINEMA", "vibe_ar": "جريء · أحمر · سينمائي",
        "preview_url": "/patterns/burger_cinema.html",
        "design_directive": (
            "Bold cinematic fast-food. Vertical rhythm: crimson red → black → cream. Section 1 red: huge burger photo right, 'World Famous Burger' serif left, $price chip. "
            "Section 2 black: 'Today Special' horizontal cards with '+' buttons. Section 3 cream: 'Free delivery 7 days' with takeout bag photo. Section 4 red: huge italic 'Reviews'. "
            "Bebas Neue / Anton font. Sticky red cart pill."
        ),
        "palette": ["#dc2626", "#000000", "#fdf6e8", "#fbbf24", "#ffffff"],
        "fonts": ["Bebas Neue", "Tajawal"],
    },
    {
        "id": "rustic_plank", "name": "Rustic Plank", "name_ar": "الخشب الريفي",
        "vibe": "RUSTIC · WOODEN · ARTISAN", "vibe_ar": "ريفي · خشب · حِرفي",
        "preview_url": "/patterns/rustic_plank.html",
        "design_directive": (
            "Artisan rustic. Body = dark walnut wood plank texture (CSS gradient). Main content = large white card floating on top with shadow & 24px radius. "
            "Scattered photos: spices, succulents, wooden cutting board with sandwich, falling french fries. Inside card: nav with active item in RED, "
            "centered title 'ONE-STOP / DELICIOUS / FOODS PLACE' middle word in red, single red 'ORDER NOW' pill. Horizontal slider of 4 dishes. Earthy, hand-curated."
        ),
        "palette": ["#5d3a1f", "#dc2626", "#fdfaf6", "#86efac", "#1a1a1a"],
        "fonts": ["Poppins", "Tajawal"],
    },
    {
        "id": "brush_italian", "name": "Brush Italian", "name_ar": "الفرشاة الإيطالية",
        "vibe": "BRUSH ART · MINT · PIZZERIA", "vibe_ar": "فني · نعناعي · بيتزيريا",
        "preview_url": "/patterns/brush_italian.html",
        "design_directive": (
            "Artisanal Italian pizzeria. Diagonal background: amber #f59e0b 30% top-left, cool gray bottom-right. Content in browser-mockup with shadow. "
            "Dark nav bar with bilingual logo. HERO: cinematic close-up of hands sharing pizza slice. Huge Permanent Marker title 'ITALIAN CUISINE' over dark. "
            "Outlined white 'RESERVE NOW' pill. Mint #34d399 only for tiny accents. About Us card + 2 atmospheric food photos."
        ),
        "palette": ["#1a1a1a", "#f59e0b", "#34d399", "#fdfaf6", "#a8a29e"],
        "fonts": ["Permanent Marker", "Tajawal"],
    },
]


# ───────────────────────── STORE PATTERNS ─────────────────────────
STORE_PATTERNS: List[Dict[str, Any]] = [
    {
        "id": "luxe_mono", "name": "Luxe Mono", "name_ar": "الفخامة الأحادية",
        "vibe": "PREMIUM · MINIMAL · BLACK-GOLD", "vibe_ar": "فاخر · مينمالست · أسود وذهبي",
        "preview_url": "/patterns/store_luxe.html",
        "design_directive": (
            "Premium luxury e-commerce. Pure black background (#0a0a0a) with sparing gold (#c8a97e) accents. "
            "Hero: huge silent product photo (single hero item) on right 60%, brand name in Playfair Display large italic on left + thin gold underline + outlined 'SHOP NOW' button. "
            "Sticky thin nav top. Below: 'CURATED COLLECTION' section with 4-column product grid, each product card pure white inside black, "
            "minimalist text only: name + price (no clutter, no badges). Quiet, refined, fashion-magazine feel."
        ),
        "palette": ["#0a0a0a", "#c8a97e", "#1a1a1a", "#ffffff", "#e8d5b7"],
        "fonts": ["Playfair Display", "Tajawal"],
    },
    {
        "id": "neon_tech", "name": "Neon Tech", "name_ar": "تك نيون",
        "vibe": "TECH · NEON · GADGETS", "vibe_ar": "تقني · نيون · إلكترونيات",
        "preview_url": "/patterns/store_neon.html",
        "design_directive": (
            "Cyberpunk tech store. Deep navy (#0f172a) background with neon cyan (#06b6d4) + magenta (#ec4899) accents. "
            "Hero: tilted product 3D mockup (headphones/smartphone) on right with neon glow halo, "
            "big sans-serif 'FUTURE IS HERE' title with gradient cyan→magenta. "
            "Single neon-outlined 'SHOP COLLECTION' button. Glass-morphism product cards 4-column. "
            "Featured deal countdown timer. Hover lift effects."
        ),
        "palette": ["#0f172a", "#06b6d4", "#ec4899", "#fbbf24", "#f1f5f9"],
        "fonts": ["Space Grotesk", "Tajawal"],
    },
    {
        "id": "boho_pastel", "name": "Boho Pastel", "name_ar": "بوهو باستيل",
        "vibe": "FEMININE · PASTEL · LIFESTYLE", "vibe_ar": "أنثوي · باستيل · حياة",
        "preview_url": "/patterns/store_boho.html",
        "design_directive": (
            "Soft feminine boutique. Pastel cream (#fef7ed) background with rose-gold (#e8b4a0) + sage (#9ca989) accents. "
            "Hero: model holding tote bag, soft natural light, on right. Brand name in handwritten serif (Cormorant Garamond) on left. "
            "Soft rounded everything (24px+). 3-column product grid with rose borders on hover. Pinterest aesthetic."
        ),
        "palette": ["#fef7ed", "#e8b4a0", "#9ca989", "#d4a574", "#5d4e37"],
        "fonts": ["Cormorant Garamond", "Tajawal"],
    },
    {
        "id": "saudi_market", "name": "Saudi Market", "name_ar": "السوق السعودي",
        "vibe": "AUTHENTIC · GREEN-GOLD · LOCAL", "vibe_ar": "أصيل · أخضر وذهبي · محلي",
        "preview_url": "/patterns/store_saudi.html",
        "design_directive": (
            "Authentic Saudi e-commerce inspired by Najdi heritage. Saudi green (#006633) header + gold (#fbbf24) accents on cream (#fdfaf6). "
            "Hero: Arabic calligraphy as decorative pattern, single product showcase with arabesque-bordered frame. "
            "Big Tajawal-Black brand name + decorative gold divider + dual CTAs 'تسوّق الآن' and 'اطلب عبر واتساب'. "
            "Categories shown as ornate gold-bordered cards. Tradi-tech feel."
        ),
        "palette": ["#006633", "#fbbf24", "#fdfaf6", "#7a1f2b", "#1a1a1a"],
        "fonts": ["Tajawal", "Amiri"],
    },
    {
        "id": "studio_white", "name": "Studio White", "name_ar": "الاستوديو الأبيض",
        "vibe": "MINIMAL · WHITE · GALLERY", "vibe_ar": "مينمالست · أبيض · معرض",
        "preview_url": "/patterns/store_studio.html",
        "design_directive": (
            "Pure white gallery e-commerce. White (#ffffff) background, thin charcoal (#1a1a1a) lines, single bright accent (electric blue #2563eb). "
            "Hero: massive single product photo on white with shadow, sparse meaningful copy on left. "
            "Grid spacing very generous (~80px gaps). Apple-style attention to typography (Inter). "
            "Hover reveals second product image (color/angle variant)."
        ),
        "palette": ["#ffffff", "#1a1a1a", "#2563eb", "#f3f4f6", "#fbbf24"],
        "fonts": ["Inter", "Tajawal"],
    },
    {
        "id": "warm_artisan", "name": "Warm Artisan", "name_ar": "الحرفي الدافئ",
        "vibe": "ARTISAN · TERRACOTTA · HANDMADE", "vibe_ar": "حرفي · طيني · يدوي",
        "preview_url": "/patterns/store_artisan.html",
        "design_directive": (
            "Handmade artisan goods. Warm terracotta (#c2410c) + cream (#fef3c7) + olive (#65a30d) palette. "
            "Hero: hand-thrown ceramic bowl photographed top-down on rough linen with hand-written serif title. "
            "Texture grain throughout. Story-telling about each maker. Photos look like home-studio shots."
        ),
        "palette": ["#c2410c", "#fef3c7", "#65a30d", "#7c2d12", "#fdfaf6"],
        "fonts": ["Cormorant Garamond", "Tajawal"],
    },
]


# ───────────────────────── CLINIC PATTERNS ─────────────────────────
CLINIC_PATTERNS: List[Dict[str, Any]] = [
    {
        "id": "calm_blue", "name": "Calm Blue", "name_ar": "الأزرق الهادئ",
        "vibe": "TRUSTED · BLUE · MEDICAL", "vibe_ar": "موثوق · أزرق · طبي",
        "preview_url": "/patterns/clinic_blue.html",
        "design_directive": (
            "Trusted medical clinic. Clean white background with calm blue (#2563eb) accents. "
            "Hero: smiling doctor in white coat on right, big Tajawal title 'صحتك أولوية' on left, "
            "tagline + single CTA 'احجز موعدك الآن'. Trust indicators bar (years of service + patients served + doctors). "
            "Below: 'تخصصاتنا' grid with 6 specialty cards (Cardiology/Dermatology/Pediatrics/Dental/Ophthalmology/Internal Medicine). "
            "Soft shadows, rounded 16px corners. Healthcare professional feel."
        ),
        "palette": ["#2563eb", "#ffffff", "#dbeafe", "#0f172a", "#22c55e"],
        "fonts": ["Tajawal", "Inter"],
    },
    {
        "id": "wellness_green", "name": "Wellness Green", "name_ar": "العافية الخضراء",
        "vibe": "WELLNESS · GREEN · HOLISTIC", "vibe_ar": "صحي · أخضر · شامل",
        "preview_url": "/patterns/clinic_wellness.html",
        "design_directive": (
            "Wellness center. Sage green (#16a34a) + cream (#fefce8) + earthy brown (#78350f) palette. "
            "Hero: leaves overlay, doctor hands holding patient hands, soft natural light. Title 'صحة شاملة لك ولعائلتك' in serif. "
            "Below: services as horizontal scrolling cards with photos. Calm, natural, holistic vibe."
        ),
        "palette": ["#16a34a", "#fefce8", "#78350f", "#86efac", "#1a1a1a"],
        "fonts": ["Cormorant Garamond", "Tajawal"],
    },
    {
        "id": "dental_white", "name": "Dental White", "name_ar": "الأسنان البيضاء",
        "vibe": "DENTAL · PURE · SMILE", "vibe_ar": "أسنان · نقي · ابتسامة",
        "preview_url": "/patterns/clinic_dental.html",
        "design_directive": (
            "Dental clinic specialized. Pure white + soft mint (#a7f3d0) + electric blue (#2563eb). "
            "Hero: macro of bright smile on right, 'ابتسامتك سرّ جمالك' title left. "
            "3D tooth icon decoration. 'احجز فحص مجاني' CTA. Below: before/after cases gallery. Professional cosmetic dentist feel."
        ),
        "palette": ["#ffffff", "#a7f3d0", "#2563eb", "#fbbf24", "#0f172a"],
        "fonts": ["Tajawal", "Inter"],
    },
    {
        "id": "pediatric_sunny", "name": "Pediatric Sunny", "name_ar": "الأطفال المشرقة",
        "vibe": "KIDS · YELLOW · PLAYFUL", "vibe_ar": "أطفال · أصفر · مرح",
        "preview_url": "/patterns/clinic_kids.html",
        "design_directive": (
            "Pediatric clinic. Bright sunny yellow (#fbbf24) + sky blue (#3b82f6) + cream (#fef3c7). "
            "Hero: cartoon-style child with stethoscope toy. Round, playful, soft everything. Comic Sans? No — Tajawal bold large. "
            "Service cards with smiling kid icons. Vaccine schedule prominently shown. Parent-friendly tone."
        ),
        "palette": ["#fbbf24", "#3b82f6", "#fef3c7", "#22c55e", "#1a1a1a"],
        "fonts": ["Tajawal", "Poppins"],
    },
]


# ───────────────────────── REALESTATE PATTERNS ─────────────────────────
REALESTATE_PATTERNS: List[Dict[str, Any]] = [
    {
        "id": "luxe_estate", "name": "Luxe Estate", "name_ar": "العقار الفاخر",
        "vibe": "LUXURY · DARK · ARCHITECTURAL", "vibe_ar": "فاخر · داكن · معماري",
        "preview_url": "/patterns/realestate_luxe.html",
        "design_directive": (
            "Luxury real estate. Pure black (#0a0a0a) + champagne gold (#c8a97e). "
            "Hero: cinematic full-bleed photo of luxury villa exterior at golden hour, large Playfair italic title 'عقارات فاخرة في الرياض' overlayed. "
            "Search bar (location + bedrooms + price range) as floating glass card. Property cards: large photo + price chip + key specs (bedrooms/bathrooms/sqm). "
            "Single 'عرض كل العقارات' CTA. Quiet, premium, magazine-style."
        ),
        "palette": ["#0a0a0a", "#c8a97e", "#1a1a1a", "#ffffff", "#e8d5b7"],
        "fonts": ["Playfair Display", "Tajawal"],
    },
    {
        "id": "modern_blueprint", "name": "Modern Blueprint", "name_ar": "المخطط الحديث",
        "vibe": "MODERN · BLUE · ARCHITECTURAL", "vibe_ar": "حديث · أزرق · معماري",
        "preview_url": "/patterns/realestate_modern.html",
        "design_directive": (
            "Modern architectural real estate. Deep navy (#0f172a) header + crisp blue (#3b82f6) accents + white. "
            "Hero: split-screen — left side a blueprint-style architectural diagram with property stats overlay, right side a real photo of a modern villa. "
            "Smart filters bar (City / Type / Price). Cards as map pins with mini-photos. Mortgage calculator widget."
        ),
        "palette": ["#0f172a", "#3b82f6", "#dbeafe", "#fbbf24", "#1e293b"],
        "fonts": ["Inter", "Tajawal"],
    },
    {
        "id": "warm_homes", "name": "Warm Homes", "name_ar": "البيوت الدافئة",
        "vibe": "FAMILY · WARM · WELCOMING", "vibe_ar": "عائلي · دافئ · ترحيبي",
        "preview_url": "/patterns/realestate_warm.html",
        "design_directive": (
            "Family-friendly real estate. Warm cream (#fef3c7) background + terracotta (#c2410c) + sage (#65a30d). "
            "Hero: family on a porch of a suburban home (Saudi-style). Title 'بيتك الجديد ينتظرك' in serif. "
            "Property cards rounded, warm shadows. Highlights school districts + parks nearby. Trust through warmth."
        ),
        "palette": ["#fef3c7", "#c2410c", "#65a30d", "#7c2d12", "#1a1a1a"],
        "fonts": ["Cormorant Garamond", "Tajawal"],
    },
    {
        "id": "saudi_vision", "name": "Saudi Vision", "name_ar": "رؤية سعودية",
        "vibe": "SAUDI · GREEN-GOLD · VISION 2030", "vibe_ar": "سعودي · أخضر وذهبي · رؤية 2030",
        "preview_url": "/patterns/realestate_saudi.html",
        "design_directive": (
            "Saudi Vision 2030 inspired real estate. Saudi green (#006633) + gold (#fbbf24) + white. "
            "Hero: aerial shot of Riyadh skyline (Kingdom Tower visible) with green/gold gradient overlay. Title in Tajawal-Black + Arabic calligraphy decoration. "
            "Featured projects: NEOM / Diriyah / Red Sea as showcase cards. Patriotic, ambitious tone."
        ),
        "palette": ["#006633", "#fbbf24", "#ffffff", "#7a1f2b", "#1a1a1a"],
        "fonts": ["Tajawal", "Amiri"],
    },
]


# ───────────────────────── FEATURES PER TYPE ─────────────────────────
RESTAURANT_FEATURES: List[Dict[str, Any]] = [
    {"id": "menu", "name_ar": "قائمة طعام تفاعلية مع صور وأسعار", "category": "core", "default": True},
    {"id": "cart", "name_ar": "سلة شراء كاملة مع حساب الإجمالي", "category": "core", "default": True},
    {"id": "checkout", "name_ar": "صفحة دفع (Stripe/Tap/Moyasar)", "category": "core", "default": True},
    {"id": "delivery", "name_ar": "نظام توصيل: عنوان + خريطة + خطوات الطلب", "category": "core", "default": True},
    {"id": "pickup", "name_ar": "خيار الاستلام من المطعم (Pickup)", "category": "core", "default": True},
    {"id": "reservations", "name_ar": "حجز طاولات", "category": "core", "default": True},
    {"id": "gallery", "name_ar": "معرض صور للأطباق والمطعم", "category": "marketing", "default": True},
    {"id": "specials", "name_ar": "عروض اليوم وقسم 'الطبق المميز'", "category": "marketing", "default": True},
    {"id": "loyalty", "name_ar": "برنامج ولاء (نقاط لكل طلب)", "category": "marketing", "default": True},
    {"id": "reviews", "name_ar": "آراء العملاء + نظام تقييم بالنجوم", "category": "social", "default": True},
    {"id": "contact", "name_ar": "تواصل: واتساب + هاتف + خريطة", "category": "footer", "default": True},
    {"id": "hours", "name_ar": "ساعات العمل وحالة 'مفتوح/مغلق'", "category": "footer", "default": True},
    {"id": "branches", "name_ar": "تعدد الفروع مع اختيار الفرع", "category": "operations", "default": True},
    {"id": "search", "name_ar": "بحث في القائمة", "category": "core", "default": True},
    {"id": "filters", "name_ar": "تصفية: نباتي / حار / حلال", "category": "core", "default": True},
    {"id": "admin_panel", "name_ar": "لوحة إدارة (طلبات + قائمة + تقارير)", "category": "admin", "default": True},
    {"id": "driver_app", "name_ar": "تطبيق سائق التوصيل", "category": "admin", "default": True},
    {"id": "analytics", "name_ar": "تحليلات (أكثر طبق مبيعاً)", "category": "admin", "default": True},
]

STORE_FEATURES: List[Dict[str, Any]] = [
    {"id": "catalog", "name_ar": "كتالوج منتجات مع صور وأسعار", "category": "core", "default": True},
    {"id": "cart", "name_ar": "سلة شراء + Checkout كامل", "category": "core", "default": True},
    {"id": "checkout", "name_ar": "دفع آمن (مدى/فيزا/STC Pay/Apple Pay)", "category": "core", "default": True},
    {"id": "shipping", "name_ar": "شحن داخلي وخارجي + حساب التكلفة", "category": "core", "default": True},
    {"id": "inventory", "name_ar": "تتبع مخزون لحظي", "category": "operations", "default": True},
    {"id": "categories", "name_ar": "تصنيفات منتجات هرمية", "category": "core", "default": True},
    {"id": "variants", "name_ar": "خيارات المنتج (لون / مقاس / كمية)", "category": "core", "default": True},
    {"id": "search", "name_ar": "بحث ذكي + فلاتر متقدمة", "category": "core", "default": True},
    {"id": "wishlist", "name_ar": "قائمة الأمنيات للزبون", "category": "social", "default": True},
    {"id": "reviews", "name_ar": "تقييمات منتجات بالنجوم", "category": "social", "default": True},
    {"id": "promo_codes", "name_ar": "أكواد خصم + كوبونات", "category": "marketing", "default": True},
    {"id": "loyalty", "name_ar": "نقاط ولاء", "category": "marketing", "default": True},
    {"id": "contact", "name_ar": "تواصل: واتساب + هاتف", "category": "footer", "default": True},
    {"id": "admin_panel", "name_ar": "لوحة تحكم (طلبات/منتجات/مخزون/تقارير)", "category": "admin", "default": True},
    {"id": "driver_app", "name_ar": "تطبيق سائق توصيل", "category": "admin", "default": True},
    {"id": "analytics", "name_ar": "تحليلات مبيعات", "category": "admin", "default": True},
]

CLINIC_FEATURES: List[Dict[str, Any]] = [
    {"id": "specialties", "name_ar": "عرض التخصصات الطبية", "category": "core", "default": True},
    {"id": "doctors", "name_ar": "صفحات الأطباء (سيرة ذاتية + تخصص)", "category": "core", "default": True},
    {"id": "appointments", "name_ar": "حجز مواعيد إلكتروني", "category": "core", "default": True},
    {"id": "patient_portal", "name_ar": "بوابة المريض (ملف طبي)", "category": "core", "default": True},
    {"id": "services", "name_ar": "خدمات وأسعار", "category": "core", "default": True},
    {"id": "insurance", "name_ar": "التأمينات المقبولة", "category": "operations", "default": True},
    {"id": "lab_results", "name_ar": "نتائج المختبرات", "category": "operations", "default": True},
    {"id": "prescriptions", "name_ar": "وصفات طبية إلكترونية", "category": "operations", "default": True},
    {"id": "telemedicine", "name_ar": "استشارة عن بُعد", "category": "core", "default": True},
    {"id": "reviews", "name_ar": "آراء المرضى", "category": "social", "default": True},
    {"id": "contact", "name_ar": "تواصل: واتساب + هاتف + خريطة", "category": "footer", "default": True},
    {"id": "hours", "name_ar": "ساعات الدوام", "category": "footer", "default": True},
    {"id": "admin_panel", "name_ar": "لوحة إدارة (مواعيد/مرضى/أطباء/تقارير)", "category": "admin", "default": True},
    {"id": "doctor_app", "name_ar": "تطبيق الطبيب (مرضى اليوم)", "category": "admin", "default": True},
    {"id": "analytics", "name_ar": "تحليلات الزيارات والمواعيد", "category": "admin", "default": True},
]

REALESTATE_FEATURES: List[Dict[str, Any]] = [
    {"id": "listings", "name_ar": "معرض عقارات مع صور وتفاصيل", "category": "core", "default": True},
    {"id": "search", "name_ar": "بحث متقدم (مدينة/نوع/سعر)", "category": "core", "default": True},
    {"id": "filters", "name_ar": "فلاتر (غرف نوم / مساحة / حالة)", "category": "core", "default": True},
    {"id": "map", "name_ar": "خريطة تفاعلية للعقارات", "category": "core", "default": True},
    {"id": "details", "name_ar": "صفحة تفاصيل العقار + معرض صور", "category": "core", "default": True},
    {"id": "inquiry", "name_ar": "نموذج استفسار/طلب جولة", "category": "core", "default": True},
    {"id": "mortgage", "name_ar": "حاسبة قروض عقارية", "category": "tools", "default": True},
    {"id": "agents", "name_ar": "صفحات الوسطاء العقاريين", "category": "core", "default": True},
    {"id": "favorites", "name_ar": "حفظ المفضلة للزبون", "category": "social", "default": True},
    {"id": "compare", "name_ar": "مقارنة بين العقارات", "category": "tools", "default": True},
    {"id": "virtual_tour", "name_ar": "جولة افتراضية 360°", "category": "marketing", "default": True},
    {"id": "contact", "name_ar": "تواصل: واتساب + هاتف", "category": "footer", "default": True},
    {"id": "admin_panel", "name_ar": "لوحة إدارة (عقارات/استفسارات/وسطاء)", "category": "admin", "default": True},
    {"id": "agent_app", "name_ar": "تطبيق الوسيط (الاستفسارات)", "category": "admin", "default": True},
    {"id": "analytics", "name_ar": "تحليلات المشاهدات والاستفسارات", "category": "admin", "default": True},
]


PATTERNS_BY_TYPE: Dict[str, List[Dict[str, Any]]] = {
    "restaurant": RESTAURANT_PATTERNS,
    "store": STORE_PATTERNS,
    "clinic": CLINIC_PATTERNS,
    "realestate": REALESTATE_PATTERNS,
}

FEATURES_BY_TYPE: Dict[str, List[Dict[str, Any]]] = {
    "restaurant": RESTAURANT_FEATURES,
    "store": STORE_FEATURES,
    "clinic": CLINIC_FEATURES,
    "realestate": REALESTATE_FEATURES,
}


def get_type(type_id: str) -> Optional[Dict[str, Any]]:
    for t in SITE_TYPES:
        if t["id"] == type_id:
            return t
    return None


def get_pattern(type_id: str, pattern_id: str) -> Optional[Dict[str, Any]]:
    patterns = PATTERNS_BY_TYPE.get(type_id, [])
    for p in patterns:
        if p["id"] == pattern_id:
            return p
    return None


def get_features(type_id: str) -> List[Dict[str, Any]]:
    return FEATURES_BY_TYPE.get(type_id, [])
