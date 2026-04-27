"""Verticals — domain-specific configuration for generated sites.

Each vertical defines:
- wizard_questions: unique onboarding steps (overrides generic wizard)
- sections: list of section templates to pre-seed
- features: functional modules to enable (bookings | products | portfolio | orders)
- dashboard_tabs: tabs that should appear in ClientDashboard
- sample_data: seed content to demonstrate the template

Modules (reusable):
- orders   — restaurants/cafes (existing)
- bookings — salon, pets, medical, gym (appointment system)
- products — e-commerce, electronics (catalog + variants + inventory)
- portfolio — stocks (simulation only)
"""
from __future__ import annotations

VERTICALS = {
    # ────────────────────────────────────────────────────────────────
    "restaurant": {
        "id": "restaurant",
        "name_ar": "مطاعم ومقاهي",
        "icon": "🍽️",
        "color": "#D97706",
        "features": ["orders"],
        "checkout_type": "delivery",
        "dashboard_tabs": ["orders", "livemap", "customers", "drivers", "delivery", "payments", "coupons", "loyalty"],
        "wizard_questions": [
            {"id": "cuisine", "q": "ما نوع المطبخ الذي تقدّمه؟", "chips": ["شرقي", "إيطالي", "سوشي", "برجر", "قهوة مختصة", "حلويات"]},
            {"id": "avg_prep", "q": "متوسط وقت تجهيز الطلب؟", "chips": ["5-10 دقائق", "10-20 دقيقة", "20-30 دقيقة", "+30 دقيقة"]},
            {"id": "delivery_radius", "q": "نطاق التوصيل (كم)؟", "chips": ["3 كم", "5 كم", "10 كم", "15 كم"]},
        ],
        "sample_sections": ["hero", "menu_grid", "about", "gallery", "contact"],
    },

    # ────────────────────────────────────────────────────────────────
    "salon": {
        "id": "salon",
        "name_ar": "صالونات وحلاقة",
        "icon": "💈",
        "color": "#7C3AED",
        "features": ["bookings", "services"],
        "checkout_type": "appointment",
        "dashboard_tabs": ["appointments", "services", "staff", "customers", "payments", "coupons"],
        "wizard_questions": [
            {"id": "services", "q": "ما الخدمات التي تقدّمها؟", "chips": ["قص شعر", "حلاقة ذقن", "صبغة", "حمام مغربي", "مانيكير", "تسريحات"]},
            {"id": "staff_count", "q": "كم عدد الموظفين في الصالون؟", "chips": ["1", "2-3", "4-6", "+7"]},
            {"id": "working_hours", "q": "ساعات العمل؟", "chips": ["9 ص - 9 م", "10 ص - 10 م", "2 م - 12 ص", "24 ساعة"]},
            {"id": "slot_duration", "q": "مدة الموعد الواحد؟", "chips": ["30 دقيقة", "45 دقيقة", "60 دقيقة", "90 دقيقة"]},
            {"id": "gender", "q": "للجنس؟", "chips": ["رجال", "نساء", "عوائل"]},
        ],
        "sample_services": [
            {"id": "s1", "name": "قص شعر كلاسيكي", "price": 50, "duration_min": 30},
            {"id": "s2", "name": "حلاقة ذقن", "price": 30, "duration_min": 20},
            {"id": "s3", "name": "صبغة شعر", "price": 150, "duration_min": 60},
        ],
        "sample_sections": ["hero", "services_grid", "staff_showcase", "booking_widget", "gallery", "testimonials", "contact"],
    },

    # ────────────────────────────────────────────────────────────────
    "pets": {
        "id": "pets",
        "name_ar": "خدمات الحيوانات الأليفة",
        "icon": "🐱",
        "color": "#DB2777",
        "features": ["bookings", "services", "pet_registry"],
        "checkout_type": "appointment",
        "dashboard_tabs": ["appointments", "services", "pets", "customers", "payments"],
        "wizard_questions": [
            {"id": "pet_types", "q": "ما أنواع الحيوانات التي تتعامل معها؟", "chips": ["قطط", "كلاب", "طيور", "أسماك", "حيوانات نادرة"]},
            {"id": "services", "q": "ما الخدمات؟", "chips": ["قص شعر", "قص أظافر", "حمّام", "فندقة", "تطعيمات", "تدريب"]},
            {"id": "pickup", "q": "هل توصّل/تستلم من المنزل؟", "chips": ["نعم، مجاناً", "نعم، برسوم", "لا"]},
        ],
        "sample_services": [
            {"id": "p1", "name": "حلاقة قط", "price": 80, "duration_min": 45, "pet_types": ["قطط"]},
            {"id": "p2", "name": "قص أظافر", "price": 25, "duration_min": 15, "pet_types": ["قطط", "كلاب"]},
            {"id": "p3", "name": "حمّام كامل", "price": 60, "duration_min": 40, "pet_types": ["قطط", "كلاب"]},
            {"id": "p4", "name": "فندقة يومية", "price": 50, "duration_min": 1440, "pet_types": ["قطط", "كلاب"]},
        ],
        "sample_sections": ["hero", "services_grid", "pet_registry", "booking_widget", "gallery", "contact"],
    },

    # ────────────────────────────────────────────────────────────────
    "ecommerce": {
        "id": "ecommerce",
        "name_ar": "تجارة إلكترونية",
        "icon": "🛒",
        "color": "#059669",
        "features": ["products", "orders"],
        "checkout_type": "shipping",
        "dashboard_tabs": ["products", "orders", "inventory", "customers", "payments", "coupons", "shipping"],
        "wizard_questions": [
            {"id": "product_type", "q": "ما نوع المنتجات؟", "chips": ["إلكترونيات", "ملابس", "إكسسوارات", "منزل وديكور", "كتب", "رياضية", "مستحضرات تجميل"]},
            {"id": "variants", "q": "هل تحتاج خيارات (مقاس/لون)؟", "chips": ["نعم، مهم جداً", "نعم، أحياناً", "لا"]},
            {"id": "stock_tracking", "q": "إدارة المخزون؟", "chips": ["نعم، دقيق", "مراقبة عامة", "لا"]},
            {"id": "shipping", "q": "مناطق الشحن؟", "chips": ["الرياض فقط", "السعودية كلها", "الخليج", "دولي"]},
        ],
        "sample_products": [
            {"id": "e1", "name": "سماعة لاسلكية", "price": 299, "stock": 15, "category": "إلكترونيات",
             "variants": [{"name": "اللون", "options": ["أسود", "أبيض", "ذهبي"]}]},
            {"id": "e2", "name": "ساعة ذكية", "price": 799, "stock": 8, "category": "إلكترونيات",
             "variants": [{"name": "اللون", "options": ["فضي", "أسود"]}, {"name": "الحجم", "options": ["42mm", "46mm"]}]},
        ],
        "sample_sections": ["hero", "product_grid_filters", "featured_products", "categories_grid", "testimonials", "contact"],
    },

    # ────────────────────────────────────────────────────────────────
    "stocks": {
        "id": "stocks",
        "name_ar": "استثمار وأسهم ذكي",
        "icon": "📈",
        "color": "#2563EB",
        "features": ["portfolio", "ai_trading"],
        "checkout_type": "none",
        "simulation_only": True,
        "dashboard_tabs": ["portfolio", "watchlist", "ai_signals", "trades"],
        "wizard_questions": [
            {"id": "markets", "q": "أي أسواق تريد متابعتها؟", "chips": ["تداول السعودي", "أمريكا (NASDAQ/NYSE)", "عملات رقمية", "خليجية"]},
            {"id": "ai_mode", "q": "مستوى المساعد الذكي؟", "chips": ["مبتدئ - تعليم وشرح", "متوسط - توصيات", "متقدم - تنفيذ محاكاة"]},
            {"id": "initial_balance", "q": "رصيد المحاكاة الافتراضي؟", "chips": ["10,000 ر.س", "50,000 ر.س", "100,000 ر.س"]},
        ],
        "sample_sections": ["hero_ticker", "portfolio_widget", "watchlist_grid", "ai_chat", "market_news", "contact"],
        "disclaimer_ar": "⚠️ هذا تطبيق محاكاة للتعلم فقط. لا يتعامل بأموال حقيقية ولا يقدّم توصيات استثمارية.",
    },

    # ────────────────────────────────────────────────────────────────
    "medical": {
        "id": "medical",
        "name_ar": "عيادات طبية",
        "icon": "🏥",
        "color": "#DC2626",
        "features": ["bookings", "services", "branches"],
        "checkout_type": "appointment",
        "dashboard_tabs": ["appointments", "services", "doctors", "patients", "payments", "branches"],
        "wizard_questions": [
            {"id": "specialty", "q": "ما التخصص؟", "chips": ["عام", "أسنان", "جلدية", "نسائية", "أطفال", "عظام", "قلب", "عيون"]},
            {"id": "doctors_count", "q": "عدد الأطباء؟", "chips": ["1", "2-5", "6-10", "+10"]},
            {"id": "branches", "q": "عدد الفروع؟", "chips": ["1", "2", "3-5", "+5"]},
            {"id": "insurance", "q": "تقبلون تأمين؟", "chips": ["نعم، كل الشركات", "شركات محددة", "لا"]},
        ],
        "sample_services": [
            {"id": "m1", "name": "كشف عام", "price": 150, "duration_min": 30},
            {"id": "m2", "name": "تنظيف أسنان", "price": 300, "duration_min": 45},
            {"id": "m3", "name": "فحص شامل", "price": 800, "duration_min": 90},
        ],
        "sample_sections": ["hero", "services_grid", "doctors_showcase", "booking_widget", "branches_map", "testimonials", "contact"],
    },

    # ────────────────────────────────────────────────────────────────
    "gym": {
        "id": "gym",
        "name_ar": "صالات رياضية وتدريب",
        "icon": "🏋️",
        "color": "#0891B2",
        "features": ["bookings", "services", "memberships"],
        "checkout_type": "subscription",
        "dashboard_tabs": ["memberships", "classes", "trainers", "members", "payments"],
        "wizard_questions": [
            {"id": "facility", "q": "نوع المرفق؟", "chips": ["صالة حديد", "كروس فت", "يوجا/بيلاتس", "ملاكمة/دفاع", "سباحة"]},
            {"id": "classes", "q": "حصص جماعية؟", "chips": ["نعم، يومية", "نعم، أسبوعية", "لا، تدريب فردي فقط"]},
            {"id": "subscription_models", "q": "نماذج الاشتراك؟", "chips": ["شهري فقط", "شهري + ربع سنوي", "مرن (يومي/أسبوعي/شهري)"]},
        ],
        "sample_services": [
            {"id": "g1", "name": "اشتراك شهري", "price": 250, "duration_days": 30, "type": "membership"},
            {"id": "g2", "name": "اشتراك سنوي", "price": 2400, "duration_days": 365, "type": "membership"},
            {"id": "g3", "name": "مدرب شخصي", "price": 150, "duration_min": 60, "type": "session"},
        ],
        "sample_membership_plans": [
            {"id": "mp1", "name": "شهري أساسي", "price": 250, "period_days": 30, "benefits": ["وصول كامل للصالة", "خزانة"], "featured": False},
            {"id": "mp2", "name": "ربع سنوي", "price": 650, "period_days": 90, "benefits": ["كل ميزات الشهري", "جلسة مدرب شخصي مجانية", "خصم على المكملات"], "featured": True},
            {"id": "mp3", "name": "سنوي VIP", "price": 2400, "period_days": 365, "benefits": ["كل الميزات", "4 جلسات مدرب شخصي شهرياً", "دروس يوجا مجانية", "منشفة وماء"], "featured": False},
        ],
        "sample_sections": ["hero", "memberships_pricing", "classes_schedule", "trainers_showcase", "gallery", "contact"],
    },

    # ────────────────────────────────────────────────────────────────
    "academy": {
        "id": "academy",
        "name_ar": "أكاديميات تعليمية",
        "icon": "🎓",
        "color": "#7C2D12",
        "features": ["courses", "enrollments"],
        "checkout_type": "enrollment",
        "dashboard_tabs": ["courses", "students", "enrollments", "payments"],
        "wizard_questions": [
            {"id": "subject", "q": "الموضوع التعليمي؟", "chips": ["برمجة", "لغات", "تصميم", "إدارة أعمال", "تطوير ذاتي", "دين وقرآن"]},
            {"id": "format", "q": "صيغة الكورسات؟", "chips": ["فيديو مسجل", "بث مباشر", "مختلط", "نص ومقالات"]},
            {"id": "certification", "q": "شهادات؟", "chips": ["نعم، معتمدة", "شهادة حضور", "لا"]},
        ],
        "sample_courses": [
            {"id": "crs1", "title": "أساسيات البرمجة بـPython", "description": "دورة شاملة للمبتدئين — 30 درس تفاعلي", "price": 299, "duration_hours": 15, "level": "beginner", "instructor": "أحمد المحمد", "category": "برمجة"},
            {"id": "crs2", "title": "تصميم UI/UX احترافي", "description": "من الصفر إلى احتراف Figma والـdesign systems", "price": 499, "duration_hours": 25, "level": "intermediate", "instructor": "سارة العلي", "category": "تصميم"},
            {"id": "crs3", "title": "إدارة الأعمال الحديثة", "description": "أدوات القيادة والاستراتيجية للرواد", "price": 799, "duration_hours": 40, "level": "advanced", "instructor": "د. محمد الشهري", "category": "إدارة أعمال"},
        ],
        "sample_sections": ["hero", "courses_grid", "instructors", "testimonials", "faq", "contact"],
    },

    # ────────────────────────────────────────────────────────────────
    "realestate": {
        "id": "realestate",
        "name_ar": "دلّال عقارات",
        "icon": "🏛️",
        "color": "#B87333",
        "features": ["listings", "commission_calculator", "mortgage_calculator", "lead_capture"],
        "checkout_type": "inquiry",
        "dashboard_tabs": ["listings", "inquiries", "commissions", "agents", "payments"],
        "wizard_questions": [
            {"id": "agent_role", "q": "دورك في السوق؟", "chips": ["دلّال مستقل", "مكتب وساطة", "مطوّر عقاري", "مزيج"]},
            {"id": "listing_type", "q": "نوع العقارات اللي تسوّقها؟", "chips": ["شقق", "فلل", "أراضي", "تجاري", "مزارع", "كل الأنواع"]},
            {"id": "transaction", "q": "بيع/إيجار/الاثنين؟", "chips": ["بيع فقط", "إيجار فقط", "الاثنين"]},
            {"id": "areas", "q": "المناطق التي تغطيها؟", "chips": ["الرياض", "جدة", "الدمام", "مكة", "كل السعودية", "الخليج"]},
            {"id": "commission_pct", "q": "نسبة العمولة الافتراضية؟", "chips": ["2.5%", "3%", "5%", "تتفاوض"]},
            {"id": "lead_priority", "q": "أهم شيء عندك؟", "chips": ["عرض العقارات بطريقة فاخرة", "حساب العمولات تلقائياً", "التقاط leads بسرعة", "كلهم"]},
        ],
        "sample_listings": [
            {"id": "rl1", "title": "فيلا فاخرة - حي السفارات", "price": 2500000, "transaction": "بيع",
             "type": "فيلا", "city": "الرياض", "district": "السفارات", "area_sqm": 450,
             "bedrooms": 5, "bathrooms": 6, "commission_pct": 2.5,
             "image": "https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=600&q=70"},
            {"id": "rl2", "title": "شقة بإطلالة بحرية", "price": 850000, "transaction": "بيع",
             "type": "شقة", "city": "جدة", "district": "الكورنيش", "area_sqm": 180,
             "bedrooms": 3, "bathrooms": 3, "commission_pct": 2.5,
             "image": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=600&q=70"},
            {"id": "rl3", "title": "أرض تجارية - طريق الملك", "price": 1800000, "transaction": "بيع",
             "type": "أرض", "city": "الرياض", "district": "العليا", "area_sqm": 600,
             "bedrooms": 0, "bathrooms": 0, "commission_pct": 3.0,
             "image": "https://images.unsplash.com/photo-1501183638710-841dd1904471?w=600&q=70"},
        ],
        "sample_sections": ["hero_search", "listings_grid", "commission_summary", "map_view", "agents_card", "contact"],
    },

    # ════════════════════════════════════════════════════════════════
    # 🆕 Feb 26, 2026 — 8 NEW VERTICALS
    # ════════════════════════════════════════════════════════════════

    "salon_women": {
        "id": "salon_women",
        "name_ar": "صالون نساء",
        "icon": "💇‍♀️",
        "color": "#EC4899",
        "features": ["bookings", "services"],
        "checkout_type": "appointment",
        "dashboard_tabs": ["appointments", "services", "staff", "customers", "payments", "coupons"],
        "wizard_questions": [
            {"id": "categories", "q": "ما الأقسام؟", "chips": ["شعر", "بشرة وسبا", "أظافر", "حناء وعروس", "مكياج", "ليزر"]},
            {"id": "specialty", "q": "التخصص الرئيسي؟", "chips": ["تجميل عام", "عروس/مناسبات", "سبا استرخاء", "مراكز متكاملة"]},
            {"id": "working_hours", "q": "ساعات العمل؟", "chips": ["10 ص - 10 م", "9 ص - 9 م", "أيام العمل + ويكند"]},
            {"id": "booking_type", "q": "نوع الحجز؟", "chips": ["موعد فردي", "باقات/اشتراكات", "الاثنين"]},
        ],
        "sample_services": [
            {"id": "sw1", "name": "قص وتصفيف شعر", "price": 150, "duration_min": 60, "category": "شعر"},
            {"id": "sw2", "name": "صبغة كاملة", "price": 400, "duration_min": 120, "category": "شعر"},
            {"id": "sw3", "name": "مانيكير وباديكير", "price": 120, "duration_min": 60, "category": "أظافر"},
            {"id": "sw4", "name": "حنّاء عروس", "price": 600, "duration_min": 180, "category": "حناء وعروس"},
        ],
        "sample_sections": ["hero", "services_grid", "booking_widget", "gallery", "testimonials", "contact"],
    },

    "bakery": {
        "id": "bakery",
        "name_ar": "مخبز وحلويات",
        "icon": "🍰",
        "color": "#F472B6",
        "features": ["products", "orders", "custom_orders"],
        "checkout_type": "delivery",
        "dashboard_tabs": ["products", "orders", "custom_orders", "livemap", "customers", "drivers", "payments", "coupons"],
        "wizard_questions": [
            {"id": "type", "q": "نوع المخبز؟", "chips": ["كيك ومناسبات", "مخبز شرقي", "كروسان وقهوة", "حلويات فاخرة", "معجنات"]},
            {"id": "custom", "q": "طلبات خاصة بالمناسبات؟", "chips": ["نعم، تخصيص كامل", "قوالب جاهزة فقط", "الاثنين"]},
            {"id": "lead_time", "q": "مدة التحضير المسبق للطلبات الخاصة؟", "chips": ["24 ساعة", "48 ساعة", "3 أيام", "أسبوع"]},
        ],
        "sample_products": [
            {"id": "b1", "name": "كيكة عيد ميلاد", "price": 180, "stock": 20, "category": "كيك",
             "variants": [{"name": "النكهة", "options": ["شوكولاتة", "فانيلا", "فراولة"]}, {"name": "الحجم", "options": ["صغير", "وسط", "كبير"]}]},
            {"id": "b2", "name": "كرواسون زبدة", "price": 8, "stock": 200, "category": "معجنات"},
            {"id": "b3", "name": "كنافة بالجبن", "price": 45, "stock": 50, "category": "حلويات شرقية"},
        ],
        "sample_sections": ["hero", "product_grid_filters", "custom_order_form", "gallery", "testimonials", "contact"],
    },

    "car_wash": {
        "id": "car_wash",
        "name_ar": "غسيل سيارات متنقل",
        "icon": "🚗",
        "color": "#0EA5E9",
        "features": ["bookings", "services", "mobile_service"],
        "checkout_type": "appointment_location",
        "dashboard_tabs": ["appointments", "services", "technicians", "livemap", "customers", "payments"],
        "wizard_questions": [
            {"id": "service_type", "q": "نوع الخدمة؟", "chips": ["غسيل فقط", "تلميع كامل", "تنظيف داخلي", "حماية سيراميك", "خدمة متنقلة"]},
            {"id": "location_mode", "q": "أين تقدّم الخدمة؟", "chips": ["مقر ثابت", "متنقل للعميل", "الاثنين"]},
            {"id": "car_types", "q": "أنواع السيارات؟", "chips": ["سيدان", "SUV", "شاحنات صغيرة", "دراجات نارية", "الكل"]},
        ],
        "sample_services": [
            {"id": "cw1", "name": "غسيل خارجي سريع", "price": 30, "duration_min": 20, "category": "غسيل"},
            {"id": "cw2", "name": "غسيل داخلي وخارجي", "price": 80, "duration_min": 45, "category": "غسيل"},
            {"id": "cw3", "name": "تلميع شامل", "price": 250, "duration_min": 120, "category": "تلميع"},
            {"id": "cw4", "name": "حماية سيراميك", "price": 800, "duration_min": 240, "category": "حماية"},
        ],
        "sample_sections": ["hero", "services_grid", "booking_widget", "coverage_map", "testimonials", "contact"],
    },

    "sports_club": {
        "id": "sports_club",
        "name_ar": "نوادي رياضية",
        "icon": "⚽",
        "color": "#059669",
        "features": ["bookings", "memberships", "facilities"],
        "checkout_type": "subscription",
        "dashboard_tabs": ["memberships", "bookings", "facilities", "members", "trainers", "payments"],
        "wizard_questions": [
            {"id": "facility_types", "q": "نوع الملاعب؟", "chips": ["كرة قدم", "كرة سلة", "تنس", "بادل", "سكواش", "سباحة"]},
            {"id": "membership_types", "q": "نماذج العضوية؟", "chips": ["شهري", "سنوي", "حجز بالساعة", "الكل"]},
            {"id": "facilities_count", "q": "عدد الملاعب؟", "chips": ["1-2", "3-5", "6-10", "+10"]},
        ],
        "sample_services": [
            {"id": "sc1", "name": "حجز ملعب بادل (ساعة)", "price": 150, "duration_min": 60, "type": "booking"},
            {"id": "sc2", "name": "حجز ملعب كرة قدم (ساعة)", "price": 250, "duration_min": 60, "type": "booking"},
            {"id": "sc3", "name": "عضوية شهرية مفتوحة", "price": 500, "duration_days": 30, "type": "membership"},
        ],
        "sample_sections": ["hero", "facilities_showcase", "booking_widget", "memberships_pricing", "gallery", "contact"],
    },

    "library": {
        "id": "library",
        "name_ar": "مكتبة وقرطاسية",
        "icon": "📚",
        "color": "#7C3AED",
        "features": ["products", "orders", "isbn_search"],
        "checkout_type": "delivery",
        "dashboard_tabs": ["products", "orders", "categories", "authors", "customers", "payments", "coupons"],
        "wizard_questions": [
            {"id": "focus", "q": "التخصص؟", "chips": ["كتب عامة", "قرطاسية مدرسية", "كتب إسلامية", "أدوات مكتبية", "الكل"]},
            {"id": "isbn_support", "q": "بحث بـISBN؟", "chips": ["نعم، أساسي", "قريباً", "لا"]},
            {"id": "shipping", "q": "التوصيل؟", "chips": ["محلي فقط", "السعودية", "الخليج"]},
        ],
        "sample_products": [
            {"id": "l1", "name": "كتاب الأسود يليق بك", "price": 45, "stock": 30, "category": "روايات",
             "variants": [{"name": "الغلاف", "options": ["عادي", "مقوى"]}]},
            {"id": "l2", "name": "دفتر A4 - 200 صفحة", "price": 15, "stock": 100, "category": "قرطاسية"},
            {"id": "l3", "name": "القرآن الكريم - تجويد", "price": 75, "stock": 50, "category": "إسلامية"},
        ],
        "sample_sections": ["hero", "categories_grid", "product_grid_filters", "featured_products", "testimonials", "contact"],
    },

    "art_gallery": {
        "id": "art_gallery",
        "name_ar": "معارض فنية",
        "icon": "🎨",
        "color": "#B45309",
        "features": ["products", "exhibitions", "virtual_tour"],
        "checkout_type": "inquiry_and_shipping",
        "dashboard_tabs": ["artworks", "exhibitions", "artists", "inquiries", "sold", "payments"],
        "wizard_questions": [
            {"id": "style", "q": "النمط الفني؟", "chips": ["معاصر", "تراثي", "خط عربي", "تجريدي", "واقعي", "مختلط"]},
            {"id": "artists_count", "q": "عدد الفنانين؟", "chips": ["فنان واحد", "2-5", "6-15", "+15"]},
            {"id": "price_range", "q": "نطاق الأسعار؟", "chips": ["< 1,000 ر.س", "1-5 آلاف", "5-20 ألف", "+20 ألف"]},
        ],
        "sample_products": [
            {"id": "a1", "name": "لوحة زيتية - صحراء", "price": 3500, "stock": 1, "category": "معاصر",
             "variants": [{"name": "الإطار", "options": ["بدون", "خشب", "ذهبي"]}], "artist": "محمد العلي"},
            {"id": "a2", "name": "خط عربي - آية الكرسي", "price": 1200, "stock": 1, "category": "خط عربي", "artist": "فاطمة الخالدي"},
        ],
        "sample_sections": ["hero", "featured_artworks", "product_grid_filters", "artists_showcase", "gallery", "contact"],
    },

    "maintenance": {
        "id": "maintenance",
        "name_ar": "فني صيانة منزلية",
        "icon": "🛠️",
        "color": "#EA580C",
        "features": ["bookings", "services", "estimates"],
        "checkout_type": "service_visit",
        "dashboard_tabs": ["appointments", "services", "technicians", "livemap", "customers", "estimates", "payments"],
        "wizard_questions": [
            {"id": "trades", "q": "التخصصات؟", "chips": ["كهرباء", "سباكة", "تكييف", "نجارة", "صيانة عامة", "دهان", "الكل"]},
            {"id": "service_area", "q": "نطاق العمل؟", "chips": ["حي محدد", "مدينة كاملة", "عدة مدن"]},
            {"id": "emergency", "q": "خدمة طوارئ 24/7؟", "chips": ["نعم", "أوقات محددة", "لا"]},
        ],
        "sample_services": [
            {"id": "mt1", "name": "زيارة تشخيص (كهرباء)", "price": 100, "duration_min": 30, "category": "كهرباء"},
            {"id": "mt2", "name": "إصلاح تسريب حنفية", "price": 150, "duration_min": 45, "category": "سباكة"},
            {"id": "mt3", "name": "تنظيف وصيانة مكيف", "price": 120, "duration_min": 60, "category": "تكييف"},
        ],
        "sample_sections": ["hero", "services_grid", "booking_widget", "how_it_works", "testimonials", "contact"],
    },

    "jewelry": {
        "id": "jewelry",
        "name_ar": "مجوهرات وذهب",
        "icon": "💍",
        "color": "#FBBF24",
        "features": ["products", "gold_calculator", "orders"],
        "checkout_type": "delivery",
        "dashboard_tabs": ["products", "orders", "gold_prices", "categories", "customers", "payments"],
        "wizard_questions": [
            {"id": "product_type", "q": "نوع المجوهرات؟", "chips": ["ذهب", "ألماس", "فضة", "لؤلؤ", "مختلط"]},
            {"id": "occasions", "q": "مناسبات خاصة؟", "chips": ["خواتم زواج", "هدايا", "مجموعات يومية", "مناسبات فاخرة"]},
            {"id": "live_gold_price", "q": "سعر الذهب اللحظي؟", "chips": ["نعم، أساسي", "اختياري", "لا"]},
        ],
        "sample_products": [
            {"id": "j1", "name": "خاتم ذهب عيار 21", "price": 2800, "stock": 5, "category": "خواتم",
             "variants": [{"name": "المقاس", "options": ["16", "17", "18", "19"]}]},
            {"id": "j2", "name": "قلادة ألماس", "price": 12500, "stock": 2, "category": "قلادات"},
            {"id": "j3", "name": "إسورة فضة", "price": 450, "stock": 15, "category": "أساور"},
        ],
        "sample_sections": ["hero", "gold_ticker", "product_grid_filters", "categories_grid", "gold_calculator", "contact"],
    },

    # ════════════════════════════════════════════════════════════════
    # 🆕 Feb 27, 2026 — Cosmetics & Automotive verticals
    # ════════════════════════════════════════════════════════════════
    "cosmetics": {
        "id": "cosmetics",
        "name_ar": "مكياج وعطور",
        "icon": "💄",
        "color": "#E91E63",
        "features": ["products", "orders", "wishlists"],
        "checkout_type": "delivery",
        "dashboard_tabs": ["products", "orders", "categories", "customers", "coupons", "payments"],
        "wizard_questions": [
            {"id": "category_focus", "q": "ما الفئات الرئيسية؟", "chips": ["مكياج", "عطور", "عناية بالبشرة", "عناية بالشعر", "أدوات تجميل", "الكل"]},
            {"id": "brand_tier", "q": "مستوى العلامات؟", "chips": ["فاخرة عالمية", "متوسطة", "اقتصادية", "مزيج"]},
            {"id": "delivery_speed", "q": "سرعة التوصيل؟", "chips": ["نفس اليوم", "يومين", "3-5 أيام", "حسب المنطقة"]},
        ],
        "sample_products": [
            {"id": "cs1", "name": "أحمر شفاه فاخر", "price": 180, "stock": 25, "category": "مكياج"},
            {"id": "cs2", "name": "عطر فرنسي 100ml", "price": 650, "stock": 12, "category": "عطور"},
            {"id": "cs3", "name": "كريم ترطيب يومي", "price": 220, "stock": 40, "category": "عناية بالبشرة"},
            {"id": "cs4", "name": "بالتة ظلال 12 لون", "price": 290, "stock": 18, "category": "مكياج"},
        ],
        "sample_sections": ["hero", "categories_grid", "product_grid_filters", "testimonials", "newsletter", "contact"],
    },

    "automotive": {
        "id": "automotive",
        "name_ar": "معارض سيارات",
        "icon": "🏎️",
        "color": "#DC2626",
        "features": ["products", "test_drive_booking", "financing"],
        "checkout_type": "inquiry",  # inquiry-based; not direct purchase
        "dashboard_tabs": ["products", "inquiries", "test_drives", "customers", "payments"],
        "wizard_questions": [
            {"id": "car_types", "q": "أنواع السيارات؟", "chips": ["سيدان", "SUV", "هاتشباك", "بيك أب", "رياضية", "كل الأنواع"]},
            {"id": "condition", "q": "حالة السيارات؟", "chips": ["جديدة فقط", "مستعملة فقط", "الاثنين", "كلاسيكية"]},
            {"id": "financing", "q": "تقدّم تمويلاً؟", "chips": ["نعم، بنوك متعددة", "تأجير منتهي بالتمليك", "كاش فقط"]},
            {"id": "warranty", "q": "ضمان مقدّم؟", "chips": ["3 سنوات أو 100 ألف كم", "5 سنوات", "حسب الموديل", "بدون ضمان"]},
        ],
        "sample_products": [
            {"id": "ca1", "name": "تويوتا كامري 2025", "price": 125000, "stock": 4, "category": "سيدان",
             "image": "https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?w=600&q=70",
             "variants": [{"name": "الموديل", "options": ["GLE", "GLX-V6", "Hybrid"]}]},
            {"id": "ca2", "name": "نيسان باترول 2024", "price": 285000, "stock": 2, "category": "SUV",
             "image": "https://images.unsplash.com/photo-1494976388531-d1058494cdd8?w=600&q=70"},
            {"id": "ca3", "name": "مرسيدس C200 2024", "price": 215000, "stock": 3, "category": "سيدان فاخرة",
             "image": "https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?w=600&q=70"},
            {"id": "ca4", "name": "هيونداي توسان 2025", "price": 92000, "stock": 6, "category": "SUV",
             "image": "https://images.unsplash.com/photo-1502877338535-766e1452684a?w=600&q=70"},
        ],
        "sample_sections": ["hero", "product_grid_filters", "test_drive_booking", "financing_calculator", "testimonials", "contact"],
    },
}


def list_verticals():
    """Safe public list for the frontend picker."""
    out = []
    for v in VERTICALS.values():
        out.append({
            "id": v["id"],
            "name_ar": v["name_ar"],
            "icon": v["icon"],
            "color": v["color"],
            "features": v["features"],
            "checkout_type": v["checkout_type"],
            "simulation_only": v.get("simulation_only", False),
            "dashboard_tabs": v["dashboard_tabs"],
        })
    return out


def get_vertical(vid: str):
    return VERTICALS.get(vid)


def get_wizard_questions(vid: str):
    v = VERTICALS.get(vid)
    return v["wizard_questions"] if v else []


def has_feature(vid: str, feature: str) -> bool:
    v = VERTICALS.get(vid)
    return v is not None and feature in (v.get("features") or [])


def get_sample_services(vid: str):
    v = VERTICALS.get(vid)
    return (v or {}).get("sample_services", [])


def get_sample_products(vid: str):
    v = VERTICALS.get(vid)
    return (v or {}).get("sample_products", [])
