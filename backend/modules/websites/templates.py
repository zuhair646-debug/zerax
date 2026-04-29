"""Pre-built website templates — production-ready starting points.

Each template returns a list of sections. The visual editor lets the user
modify any of them after instantiation."""
from typing import List, Dict, Any


def _common_theme(primary="#FFD700", secondary="#1a1f3a", accent="#FF6B35"):
    return {
        "primary": primary, "secondary": secondary, "accent": accent,
        "background": "#0b0f1f", "text": "#ffffff",
        "font": "Tajawal", "radius": "medium",
    }


TEMPLATES: Dict[str, Dict[str, Any]] = {
    # ======================= STORE =======================
    "store": {
        "name": "متجر إلكتروني",
        "icon": "🛍️",
        "description": "متجر بسلاسل منتجات، عربة تسوّق، وصفحة دفع",
        "business_type": "store",
        "theme": _common_theme("#FF6B35", "#1a1f3a", "#FFD700"),
        "sections": [
            {"type": "hero", "order": 0, "data": {
                "title": "متجر الأناقة",
                "subtitle": "أفضل المنتجات بأفضل الأسعار — توصيل لكل المملكة",
                "cta_text": "تسوّق الآن",
                "cta_link": "#products",
                "image": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1600",
                "layout": "split",
            }},
            {"type": "features", "order": 1, "data": {
                "title": "لماذا متجرنا؟",
                "items": [
                    {"icon": "🚚", "title": "توصيل سريع", "text": "خلال 24 ساعة لجميع المدن"},
                    {"icon": "💳", "title": "دفع آمن", "text": "Apple Pay, Mada, STC Pay"},
                    {"icon": "🎁", "title": "ضمان الجودة", "text": "استرداد خلال 14 يوم"},
                ]}},
            {"type": "products", "order": 2, "data": {
                "title": "أبرز المنتجات",
                "items": [
                    {"name": "منتج 1", "price": "199 ريال", "old_price": "299", "image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600", "badge": "خصم 33%"},
                    {"name": "منتج 2", "price": "449 ريال", "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600"},
                    {"name": "منتج 3", "price": "89 ريال", "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600", "badge": "جديد"},
                    {"name": "منتج 4", "price": "329 ريال", "image": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=600"},
                ]}},
            {"type": "testimonials", "order": 3, "data": {
                "title": "آراء عملائنا",
                "items": [
                    {"name": "أحمد السالم", "text": "جودة ممتازة وتوصيل سريع!", "rating": 5},
                    {"name": "نورة العتيبي", "text": "أفضل متجر تعاملت معه", "rating": 5},
                ]}},
            {"type": "cta", "order": 4, "data": {
                "title": "انضم لنادي العملاء المميزين",
                "subtitle": "خصم 15% على أول طلب",
                "cta_text": "اشترك في النشرة",
            }},
            {"type": "footer", "order": 5, "data": {
                "brand": "متجر الأناقة", "email": "info@store.com", "phone": "+966 50 000 0000",
                "social": [{"icon": "instagram"}, {"icon": "twitter"}, {"icon": "tiktok"}],
            }},
        ],
    },

    # ======================= RESTAURANT =======================
    "restaurant": {
        "name": "مطعم",
        "icon": "🍽️",
        "description": "قائمة طعام، حجوزات، وصور الأطباق",
        "business_type": "restaurant",
        "theme": _common_theme("#D4AF37", "#1a0f0a", "#8B0000"),
        "sections": [
            {"type": "hero", "order": 0, "data": {
                "title": "مطعم الذوق الرفيع",
                "subtitle": "تجربة طعام لا تُنسى — أطباق أصيلة بلمسة عصرية",
                "cta_text": "احجز طاولتك",
                "cta_link": "#reservation",
                "image": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=1600",
                "layout": "full",
            }},
            {"type": "about", "order": 1, "data": {
                "title": "قصّتنا",
                "text": "تأسّس مطعمنا عام 2015 على يد الشيف خالد، بهدف تقديم أشهى الأطباق العربية والعالمية بجودة تنافس أرقى مطاعم العالم.",
                "image": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800",
            }},
            {"type": "menu", "order": 2, "data": {
                "title": "قائمتنا",
                "categories": [
                    {"name": "المقبّلات", "items": [
                        {"name": "حمص", "price": "18", "desc": "حمّص بيروتي أصلي مع زيت زيتون", "image": "https://images.unsplash.com/photo-1547592180-85f173990554?w=400"},
                        {"name": "تبولة", "price": "22", "desc": "بقدونس طازج وبرغل"},
                    ]},
                    {"name": "الأطباق الرئيسية", "items": [
                        {"name": "مندي لحم", "price": "85", "desc": "مندي لحم خروف على أصول الجنوب", "image": "https://images.unsplash.com/photo-1574484184081-afea8a62f9b0?w=400"},
                        {"name": "كبسة دجاج", "price": "65", "desc": "كبسة دجاج مع مكسرات"},
                    ]},
                ]}},
            {"type": "gallery", "order": 3, "data": {
                "title": "معرض الصور",
                "images": [
                    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800",
                    "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800",
                    "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800",
                    "https://images.unsplash.com/photo-1551782450-a2132b4ba21d?w=800",
                ]}},
            {"type": "contact", "order": 4, "data": {
                "title": "احجز طاولتك", "phone": "+966 11 000 0000", "address": "الرياض، طريق الملك فهد",
                "hours": "يومياً 12 ظهراً - 12 منتصف الليل",
            }},
            {"type": "footer", "order": 5, "data": {"brand": "مطعم الذوق الرفيع"}},
        ],
    },

    # ======================= COMPANY / CORPORATE =======================
    "company": {
        "name": "شركة / أعمال",
        "icon": "🏢",
        "description": "موقع احترافي لشركة أو أعمال استشارية",
        "business_type": "company",
        "theme": _common_theme("#3B82F6", "#0f172a", "#22D3EE"),
        "sections": [
            {"type": "hero", "order": 0, "data": {
                "title": "حلول احترافية لنموّ أعمالك",
                "subtitle": "نساعدك على الوصول لأهدافك بخطوات واضحة ونتائج مضمونة",
                "cta_text": "تحدث مع خبير",
                "cta_link": "#contact",
                "image": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1600",
                "layout": "split",
            }},
            {"type": "features", "order": 1, "data": {
                "title": "خدماتنا",
                "items": [
                    {"icon": "💼", "title": "استشارات أعمال", "text": "نُخطّط معك استراتيجية النمو"},
                    {"icon": "📊", "title": "تحليل السوق", "text": "دراسات معمّقة لقطاعك"},
                    {"icon": "⚡", "title": "تنفيذ سريع", "text": "نتائج خلال 30 يوماً"},
                    {"icon": "🎯", "title": "أهداف ذكية", "text": "نقيس ونحسّن باستمرار"},
                ]}},
            {"type": "about", "order": 2, "data": {
                "title": "من نحن",
                "text": "فريقنا يضمّ خبراء من قطاعات الاستشارات المالية والتسويق الرقمي، مع خبرة تمتدّ لأكثر من 15 عاماً.",
                "stats": [{"value": "500+", "label": "عميل راضٍ"}, {"value": "15", "label": "سنة خبرة"}, {"value": "98%", "label": "نسبة النجاح"}],
            }},
            {"type": "team", "order": 3, "data": {
                "title": "الفريق",
                "members": [
                    {"name": "د. محمد الأحمد", "role": "الرئيس التنفيذي", "image": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400"},
                    {"name": "م. سارة الزهراني", "role": "مديرة العمليات", "image": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400"},
                    {"name": "أ. عبدالله السعد", "role": "مدير التسويق", "image": "https://images.unsplash.com/photo-1519345182560-3f2917c472ef?w=400"},
                ]}},
            {"type": "cta", "order": 4, "data": {
                "title": "جاهز للبدء؟", "subtitle": "استشارة مجانية لمدة 30 دقيقة",
                "cta_text": "احجز الآن",
            }},
            {"type": "contact", "order": 5, "data": {"title": "تواصل معنا", "email": "info@company.com", "phone": "+966 11 000 0000"}},
            {"type": "footer", "order": 6, "data": {"brand": "شركتنا"}},
        ],
    },

    # ======================= PORTFOLIO =======================
    "portfolio": {
        "name": "معرض أعمال",
        "icon": "🎨",
        "description": "بورتفوليو شخصي لمصمم/مبرمج/مصور",
        "business_type": "portfolio",
        "theme": _common_theme("#EC4899", "#18181b", "#8B5CF6"),
        "sections": [
            {"type": "hero", "order": 0, "data": {
                "title": "أنا مصمم / مطوّر",
                "subtitle": "أبتكر منتجات رقمية تحكي قصصاً",
                "cta_text": "شاهد أعمالي",
                "cta_link": "#works",
                "image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800",
                "layout": "portrait",
            }},
            {"type": "about", "order": 1, "data": {
                "title": "نبذة",
                "text": "مصمم جرافيكي بخبرة 8 سنوات، عملتُ مع شركات ناشئة وعلامات كبرى. شغفي ابتكار هويّات بصرية متميّزة.",
            }},
            {"type": "gallery", "order": 2, "data": {
                "title": "أعمالي",
                "images": [
                    "https://images.unsplash.com/photo-1561070791-2526d30994b8?w=800",
                    "https://images.unsplash.com/photo-1558655146-9f40138edfeb?w=800",
                    "https://images.unsplash.com/photo-1581291518633-83b4ebd1d83e?w=800",
                    "https://images.unsplash.com/photo-1586281380349-632531db7ed4?w=800",
                    "https://images.unsplash.com/photo-1611162616475-46b635cb6868?w=800",
                    "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=800",
                ]}},
            {"type": "testimonials", "order": 3, "data": {
                "title": "ماذا يقولون عنّي",
                "items": [
                    {"name": "فيصل الدوسري", "text": "إبداع نادر وتسليم في الوقت", "rating": 5},
                ]}},
            {"type": "contact", "order": 4, "data": {"title": "لنعمل معاً", "email": "hello@me.com"}},
            {"type": "footer", "order": 5, "data": {"brand": "اسمي"}},
        ],
    },

    # ======================= SAAS / PRODUCT =======================
    "saas": {
        "name": "تطبيق / SaaS",
        "icon": "💻",
        "description": "صفحة هبوط لمنتج رقمي مع خطط اشتراك",
        "business_type": "saas",
        "theme": _common_theme("#10B981", "#0f172a", "#06B6D4"),
        "sections": [
            {"type": "hero", "order": 0, "data": {
                "title": "أتمتة تعمل كأنها سحر",
                "subtitle": "منتج SaaS يوفّر عليك 10 ساعات أسبوعياً",
                "cta_text": "جرّب مجاناً",
                "cta_link": "#pricing",
                "image": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1600",
                "layout": "split",
            }},
            {"type": "features", "order": 1, "data": {
                "title": "المميّزات",
                "items": [
                    {"icon": "⚡", "title": "سريع جداً", "text": "نتائج فورية"},
                    {"icon": "🔐", "title": "آمن", "text": "تشفير بنكي"},
                    {"icon": "🤝", "title": "دعم ٢٤/٧", "text": "فريق متاح دائماً"},
                    {"icon": "🌍", "title": "متعدد اللغات", "text": "13 لغة"},
                ]}},
            {"type": "pricing", "order": 2, "data": {
                "title": "خطط الاشتراك",
                "plans": [
                    {"name": "أساسي", "price": "49", "period": "شهرياً", "features": ["حتى 100 مهمة", "دعم بالبريد"], "cta": "ابدأ"},
                    {"name": "احترافي", "price": "149", "period": "شهرياً", "features": ["مهام لا محدودة", "دعم مباشر", "تقارير متقدّمة"], "cta": "الأكثر طلباً", "featured": True},
                    {"name": "شركات", "price": "مخصّص", "period": "", "features": ["كل مميزات الاحترافي", "إدارة حساب مخصّصة", "SLA"], "cta": "تواصل"},
                ]}},
            {"type": "faq", "order": 3, "data": {
                "title": "أسئلة شائعة",
                "items": [
                    {"q": "هل أستطيع الإلغاء في أي وقت؟", "a": "نعم، بدون أي رسوم إضافية."},
                    {"q": "هل تدعمون الدفع المحلي؟", "a": "نعم — Mada, Apple Pay, STC Pay."},
                ]}},
            {"type": "cta", "order": 4, "data": {"title": "جرّبه الآن مجاناً 14 يوم", "cta_text": "ابدأ تجربتك"}},
            {"type": "footer", "order": 5, "data": {"brand": "منتجي"}},
        ],
    },

    # ======================= BLANK =======================
    "blank": {
        "name": "فارغ / مخصّص",
        "icon": "✨",
        "description": "ابدأ من الصفر — أخبر المستشار عن فكرتك وسيبني لك تصميماً ابتكارياً",
        "business_type": "company",
        "theme": _common_theme(),
        "sections": [
            {"type": "hero", "order": 0, "data": {
                "title": "مشروعك الابتكاري يبدأ هنا",
                "subtitle": "أخبر المستشار الذكي بفكرتك وسأبني لك موقعاً فريداً يعكس طابع نشاطك — ألوان، أيقونات، تصاميم مخصّصة",
                "cta_text": "ابدأ الحوار مع المستشار ←",
                "cta_link": "#",
                "image": "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=1600",
                "layout": "split",
            }},
            {"type": "features", "order": 1, "data": {
                "title": "كيف يعمل؟",
                "items": [
                    {"icon": "💬", "title": "صف فكرتك", "text": "اكتب وصفاً حرّاً لنشاطك في الشات"},
                    {"icon": "🎨", "title": "تصميم ابتكاري", "text": "يطبّق المستشار أفكاراً بصرية فريدة"},
                    {"icon": "⚡", "title": "معاينة لايف", "text": "شاهد كل تغيير فوراً"},
                ]}},
            {"type": "cta", "order": 2, "data": {
                "title": "جرّب الآن", "subtitle": "اكتب في الشات مثلاً: 'أبي موقع لمتجر قطط'",
                "cta_text": "ابدأ ←",
            }},
            {"type": "footer", "order": 3, "data": {"brand": "موقعي المخصّص"}},
        ],
    },
}


def list_templates() -> List[Dict[str, Any]]:
    return [
        {"id": k, "name": v["name"], "icon": v["icon"], "description": v["description"], "business_type": v["business_type"]}
        for k, v in TEMPLATES.items()
    ]


def get_template(template_id: str) -> Dict[str, Any]:
    return TEMPLATES.get(template_id, TEMPLATES["blank"])
