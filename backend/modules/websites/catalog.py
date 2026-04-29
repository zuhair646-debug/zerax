"""Category catalog — each business category has multiple layout variants.

Used for the two-stage picker:
  1. User picks a CATEGORY (restaurant / coffee / barber / ...)
  2. User browses LAYOUTS inside that category with live preview
  3. User confirms → project is created from the chosen layout

Each layout is a full template: name + icon + theme + sections.
Visual style variants (from variants.py) are still applied on top.
"""
from typing import Dict, Any, List
from .templates import TEMPLATES as BASE_TEMPLATES


def _img(u: str) -> str:
    return u


def _theme(primary, secondary="#18181b", accent=None, bg="#0b0f1f", text="#ffffff", font="Tajawal", radius="medium"):
    return {"primary": primary, "secondary": secondary, "accent": accent or primary,
            "background": bg, "text": text, "font": font, "radius": radius}


# ============================================================================
# EXTENDED LAYOUTS (in addition to the 6 base TEMPLATES)
# ============================================================================
EXTRA_LAYOUTS: Dict[str, List[Dict[str, Any]]] = {

    # ---------------------- RESTAURANT — extra layouts ----------------------
    "restaurant": [
        {
            "id": "restaurant_modern",
            "name": "مطعم عصري",
            "icon": "🍴",
            "description": "تصميم مودرن بمعرض أطباق كبير",
            "theme": _theme("#F59E0B", "#0f172a", "#EF4444", radius="large"),
            "sections": [
                {"type": "hero", "order": 0, "data": {
                    "title": "نكهات تحكي قصصاً",
                    "subtitle": "مطبخ عصري، أطباق مبتكرة، تجربة لا تُنسى",
                    "cta_text": "احجز الآن", "cta_link": "#reservation",
                    "image": _img("https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1600"),
                    "layout": "full",
                }},
                {"type": "gallery", "order": 1, "data": {
                    "title": "معرض الأطباق",
                    "images": [
                        "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800",
                        "https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=800",
                        "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800",
                        "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800",
                        "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800",
                        "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=800",
                    ]}},
                {"type": "menu", "order": 2, "data": {"title": "قائمتنا المختارة", "categories": [
                    {"name": "الأطباق الرئيسية", "items": [
                        {"name": "ريبآي ستيك", "price": "180", "desc": "مشوي ببطء مع صلصة الفلفل"},
                        {"name": "سلمون مشوي", "price": "120", "desc": "مع خضار موسمية"},
                    ]},
                ]}},
                {"type": "testimonials", "order": 3, "data": {"title": "آراء الضيوف", "items": [
                    {"name": "سارة", "text": "تجربة استثنائية!", "rating": 5},
                ]}},
                {"type": "contact", "order": 4, "data": {"title": "احجز طاولتك", "phone": "+966 11 000 0000"}},
                {"type": "footer", "order": 5, "data": {"brand": "مطعم عصري"}},
            ],
        },
        {
            "id": "restaurant_streetfood",
            "name": "طعام الشارع",
            "icon": "🌮",
            "description": "بسيط وسريع، للبرجر والتكس مكس",
            "theme": _theme("#DC2626", "#18181b", "#FBBF24", radius="none", font="Cairo"),
            "sections": [
                {"type": "hero", "order": 0, "data": {
                    "title": "🔥 طعم الشارع الأصيل",
                    "subtitle": "برجر، تاكو، هوت دوغ — كما تحبّه",
                    "cta_text": "اطلب الآن",
                    "image": _img("https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=1600"),
                    "layout": "portrait",
                }},
                {"type": "menu", "order": 1, "data": {"title": "القائمة السريعة", "categories": [
                    {"name": "برجر", "items": [{"name": "كلاسيك", "price": "35"}, {"name": "تشيز", "price": "40"}]},
                    {"name": "تاكوز", "items": [{"name": "بيف", "price": "28"}, {"name": "تشيكن", "price": "25"}]},
                ]}},
                {"type": "cta", "order": 2, "data": {"title": "اطلب توصيل الآن!", "cta_text": "واتساب"}},
                {"type": "footer", "order": 3, "data": {"brand": "طعم الشارع"}},
            ],
        },
    ],

    # ---------------------- COFFEE ---------------------------
    "coffee": [
        {
            "id": "coffee_cozy",
            "name": "كوفي دافئ",
            "icon": "☕",
            "description": "أجواء هادئة، قهوة مختصة",
            "theme": _theme("#92400E", "#1c1917", "#D97706", bg="#fffbeb", text="#1c1917", font="Amiri", radius="large"),
            "sections": [
                {"type": "hero", "order": 0, "data": {
                    "title": "☕ فنجان يحكي قصة",
                    "subtitle": "قهوة مختصة، حبوب محمّصة يومياً، جو يجمعك بأصدقائك",
                    "cta_text": "زوروا الكوفي", "cta_link": "#location",
                    "image": _img("https://images.unsplash.com/photo-1511920170033-f8396924c348?w=1600"),
                    "layout": "split",
                }},
                {"type": "menu", "order": 1, "data": {"title": "قائمة المشروبات", "categories": [
                    {"name": "قهوة ساخنة", "items": [
                        {"name": "إسبريسو", "price": "12", "desc": "محضّرة من حبوب إثيوبية"},
                        {"name": "لاتيه", "price": "18", "desc": "حليب مقطر مع فن الآرت"},
                        {"name": "كابتشينو", "price": "17"},
                    ]},
                    {"name": "قهوة باردة", "items": [
                        {"name": "آيس لاتيه", "price": "20"},
                        {"name": "V60 Cold Brew", "price": "22"},
                    ]},
                ]}},
                {"type": "gallery", "order": 2, "data": {"title": "من أجواء الكوفي", "images": [
                    "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800",
                    "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=800",
                    "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=800",
                    "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=800",
                ]}},
                {"type": "about", "order": 3, "data": {"title": "قصة الكوفي",
                    "text": "نحمّص حبوبنا في نفس اليوم، لتصل إلى فنجانك بأعلى جودة."}},
                {"type": "contact", "order": 4, "data": {"title": "تواصل معنا", "hours": "يومياً 7 ص - 12 م"}},
                {"type": "footer", "order": 5, "data": {"brand": "كوفي دافئ"}},
            ],
        },
        {
            "id": "coffee_specialty",
            "name": "كوفي مختص حديث",
            "icon": "🫘",
            "description": "مودرن، ثلث-ويف، مختارات",
            "theme": _theme("#0f172a", "#fef3c7", "#D4AF37", bg="#fef3c7", text="#0f172a", font="Readex Pro", radius="small"),
            "sections": [
                {"type": "hero", "order": 0, "data": {
                    "title": "Third Wave Coffee",
                    "subtitle": "من المزرعة إلى الفنجان — شفافية مطلقة في كل خطوة",
                    "cta_text": "استكشف",
                    "image": _img("https://images.unsplash.com/photo-1442512595331-e89e73853f31?w=1600"),
                    "layout": "portrait",
                }},
                {"type": "features", "order": 1, "data": {"title": "ميّزاتنا", "items": [
                    {"icon": "🌿", "title": "حبوب أحادية المنشأ", "text": "من أفضل المزارع"},
                    {"icon": "🔥", "title": "تحميص يومي", "text": "على مرأى العين"},
                    {"icon": "☕", "title": "باريستا محترف", "text": "خبرة دولية"},
                ]}},
                {"type": "menu", "order": 2, "data": {"title": "Brewing Methods", "categories": [
                    {"name": "Espresso Bar", "items": [{"name": "Single Origin Espresso", "price": "15"}]},
                    {"name": "Pour Over", "items": [{"name": "V60", "price": "25"}, {"name": "Chemex", "price": "28"}]},
                ]}},
                {"type": "footer", "order": 3, "data": {"brand": "Specialty Coffee"}},
            ],
        },
    ],

    # ---------------------- BARBER ---------------------------
    "barber": [
        {
            "id": "barber_classic",
            "name": "حلاقة كلاسيكية",
            "icon": "💈",
            "description": "أسلوب رجالي كلاسيكي، خشب وجلد",
            "theme": _theme("#D4AF37", "#18181b", "#8B4513", bg="#0c0a09", text="#fafaf9", radius="small", font="Amiri"),
            "sections": [
                {"type": "hero", "order": 0, "data": {
                    "title": "💈 صالون الفرسان",
                    "subtitle": "حلاقة رجالية بلمسة كلاسيكية منذ 1985",
                    "cta_text": "احجز موعدك", "cta_link": "#booking",
                    "image": _img("https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=1600"),
                    "layout": "full",
                }},
                {"type": "features", "order": 1, "data": {"title": "خدماتنا", "items": [
                    {"icon": "✂️", "title": "قصّة كلاسيكية", "text": "من أمهر حلاقينا"},
                    {"icon": "🪒", "title": "حلاقة لحية بالموس", "text": "تجربة احترافية"},
                    {"icon": "💆", "title": "تدليك الرأس", "text": "استرخاء تام"},
                ]}},
                {"type": "pricing", "order": 2, "data": {"title": "الأسعار", "plans": [
                    {"name": "شعر فقط", "price": "60", "period": "", "features": ["غسيل", "قصّة", "تصفيف"], "cta": "احجز"},
                    {"name": "شعر + لحية", "price": "100", "period": "", "features": ["كل ما سبق", "تشكيل لحية", "موس كلاسيكي"], "cta": "احجز", "featured": True},
                    {"name": "الباقة الذهبية", "price": "180", "period": "", "features": ["شعر+لحية", "تدليك", "قناع وجه", "مشروب"], "cta": "احجز"},
                ]}},
                {"type": "gallery", "order": 3, "data": {"title": "أعمالنا", "images": [
                    "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=800",
                    "https://images.unsplash.com/photo-1622286346003-c1d76abe4d97?w=800",
                    "https://images.unsplash.com/photo-1634449571010-02389ed0f9b0?w=800",
                    "https://images.unsplash.com/photo-1599351431202-1e0f0137899a?w=800",
                ]}},
                {"type": "contact", "order": 4, "data": {"title": "احجز بالهاتف", "phone": "+966 11 000 0000", "hours": "يومياً 10 ص - 12 م"}},
                {"type": "footer", "order": 5, "data": {"brand": "صالون الفرسان"}},
            ],
        },
        {
            "id": "barber_modern",
            "name": "حلاقة عصرية",
            "icon": "✂️",
            "description": "مودرن، شبابي، أسلوب أوروبي",
            "theme": _theme("#06B6D4", "#020617", "#F59E0B", radius="large", font="Cairo"),
            "sections": [
                {"type": "hero", "order": 0, "data": {
                    "title": "ستايلك يحكي عنك",
                    "subtitle": "قصّات عصرية مستوحاة من أحدث الصيحات الأوروبية",
                    "cta_text": "احجز الآن",
                    "image": _img("https://images.unsplash.com/photo-1621605815971-fbc98d665033?w=1600"),
                    "layout": "split",
                }},
                {"type": "features", "order": 1, "data": {"title": "لماذا نحن؟", "items": [
                    {"icon": "💎", "title": "حلاقون محترفون", "text": "دورات دولية مستمرة"},
                    {"icon": "🎨", "title": "تصاميم حصرية", "text": "قصّات لا تجدها في مكان آخر"},
                    {"icon": "📅", "title": "حجز أونلاين", "text": "اختر الوقت المناسب"},
                ]}},
                {"type": "team", "order": 2, "data": {"title": "فريقنا", "members": [
                    {"name": "أحمد", "role": "الحلاق الرئيسي", "image": "https://images.unsplash.com/photo-1622286346003-c1d76abe4d97?w=400"},
                    {"name": "خالد", "role": "خبير اللحى", "image": "https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?w=400"},
                ]}},
                {"type": "cta", "order": 3, "data": {"title": "غيّر مظهرك الآن", "cta_text": "احجز موعد"}},
                {"type": "footer", "order": 4, "data": {"brand": "صالون ستايل"}},
            ],
        },
    ],

    # ---------------------- PETS / CATS ---------------------------
    "pets": [
        {
            "id": "pets_cat_store",
            "name": "متجر قطط",
            "icon": "🐱",
            "description": "كل احتياجات قطتك الأنيقة",
            "theme": _theme("#D97706", "#451a03", "#F59E0B", bg="#fef3c7", text="#451a03", radius="full", font="Cairo"),
            "sections": [
                {"type": "hero", "order": 0, "data": {
                    "title": "🐾 مملكة القطط",
                    "subtitle": "طعام فاخر، ألعاب مرحة، عناية مميزة — كل ما تحتاجه قطتك",
                    "cta_text": "تسوّق الآن 🐾", "cta_link": "#products",
                    "image": _img("https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=1600"),
                    "layout": "split",
                }},
                {"type": "features", "order": 1, "data": {"title": "🐾 لماذا نحن؟", "items": [
                    {"icon": "🥫", "title": "طعام طبيعي 100%", "text": "بلا مواد حافظة"},
                    {"icon": "🧸", "title": "ألعاب آمنة", "text": "خامات خالية من السموم"},
                    {"icon": "🚚", "title": "توصيل نفس اليوم", "text": "للرياض وجدة"},
                    {"icon": "💚", "title": "عيادة شريكة", "text": "استشارة بيطرية مجانية"},
                ]}},
                {"type": "products", "order": 2, "data": {"title": "منتجات قطتك المفضلة", "items": [
                    {"name": "طعام جاف بريميوم", "price": "89 ريال", "image": "https://images.unsplash.com/photo-1583511655826-05700d52f4d9?w=600", "badge": "الأكثر مبيعاً"},
                    {"name": "لعبة كرة النشاط", "price": "45 ريال", "image": "https://images.unsplash.com/photo-1587764379873-97837921fd44?w=600"},
                    {"name": "شجرة القطط الفاخرة", "price": "299 ريال", "image": "https://images.unsplash.com/photo-1526336024174-e58f5cdd8e13?w=600", "badge": "خصم 20%"},
                    {"name": "بطانية ناعمة", "price": "65 ريال", "image": "https://images.unsplash.com/photo-1595433707802-6b2626ef1c91?w=600"},
                ]}},
                {"type": "gallery", "order": 3, "data": {"title": "قطط سعيدة 😻", "images": [
                    "https://images.unsplash.com/photo-1543852786-1cf6624b9987?w=800",
                    "https://images.unsplash.com/photo-1573865526739-10659fec78a5?w=800",
                    "https://images.unsplash.com/photo-1592194996308-7b43878e84a6?w=800",
                    "https://images.unsplash.com/photo-1574158622682-e40e69881006?w=800",
                ]}},
                {"type": "cta", "order": 4, "data": {"title": "🐾 انضم لنادي محبّي القطط", "subtitle": "خصم 15% على أول طلب", "cta_text": "سجّل مجاناً"}},
                {"type": "footer", "order": 5, "data": {"brand": "مملكة القطط"}},
            ],
            "custom_css": ".btn-primary::before{content:'🐾 '} .feature-card{background:linear-gradient(135deg,#fef3c722,#fde68a22)!important}",
        },
        {
            "id": "pets_general",
            "name": "متجر حيوانات أليفة",
            "icon": "🐶",
            "description": "لكل الحيوانات الأليفة: قطط وكلاب وطيور",
            "theme": _theme("#10B981", "#064e3b", "#F59E0B", radius="large", font="Tajawal"),
            "sections": [
                {"type": "hero", "order": 0, "data": {
                    "title": "رفيقك الأليف يستحق الأفضل",
                    "subtitle": "منتجات عناية لقطط، كلاب، طيور، أسماك — كل شيء في مكان واحد",
                    "cta_text": "ابدأ التسوّق",
                    "image": _img("https://images.unsplash.com/photo-1601758124510-52d02ddb7cbd?w=1600"),
                    "layout": "split",
                }},
                {"type": "features", "order": 1, "data": {"title": "خدماتنا", "items": [
                    {"icon": "🐱", "title": "قطط", "text": "طعام وألعاب وعناية"},
                    {"icon": "🐶", "title": "كلاب", "text": "أطواق وطعام وتدريب"},
                    {"icon": "🐦", "title": "طيور", "text": "أقفاص وأكسسوارات"},
                    {"icon": "🐠", "title": "أسماك", "text": "أحواض ومعدات"},
                ]}},
                {"type": "products", "order": 2, "data": {"title": "الأكثر مبيعاً", "items": []}},
                {"type": "cta", "order": 3, "data": {"title": "عضوية VIP", "subtitle": "خصم دائم + توصيل مجاني", "cta_text": "سجّل الآن"}},
                {"type": "footer", "order": 4, "data": {"brand": "متجر الحيوانات الأليفة"}},
            ],
        },
    ],

    # ---------------------- CLINIC ---------------------------
    "clinic": [
        {
            "id": "clinic_dental",
            "name": "عيادة أسنان",
            "icon": "🦷",
            "description": "طب أسنان تجميلي وعلاجي",
            "theme": _theme("#06B6D4", "#0f172a", "#3B82F6", bg="#f0f9ff", text="#0f172a", radius="medium", font="Readex Pro"),
            "sections": [
                {"type": "hero", "order": 0, "data": {
                    "title": "ابتسامتك تستحق الأفضل 🦷",
                    "subtitle": "عيادة أسنان عصرية — تقنيات رقمية، فريق متخصص، راحة مطلقة",
                    "cta_text": "احجز كشفاً مجانياً",
                    "image": _img("https://images.unsplash.com/photo-1629909613654-28e377c37b09?w=1600"),
                    "layout": "split",
                }},
                {"type": "features", "order": 1, "data": {"title": "خدماتنا", "items": [
                    {"icon": "✨", "title": "تجميل الأسنان", "text": "ابتسامة هوليود، قشور بورسلين"},
                    {"icon": "🔬", "title": "علاج الجذور", "text": "بدون ألم باستخدام الميكروسكوب"},
                    {"icon": "🦷", "title": "زراعة الأسنان", "text": "أحدث التقنيات العالمية"},
                    {"icon": "👨‍⚕️", "title": "تقويم الأسنان", "text": "شفاف أو معدني"},
                ]}},
                {"type": "team", "order": 2, "data": {"title": "فريق الأطباء", "members": [
                    {"name": "د. محمد العلي", "role": "استشاري تجميل أسنان", "image": "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=400"},
                    {"name": "د. نورة سليم", "role": "أخصائية تقويم", "image": "https://images.unsplash.com/photo-1594824476967-48c8b964273f?w=400"},
                ]}},
                {"type": "testimonials", "order": 3, "data": {"title": "شهادات المرضى", "items": [
                    {"name": "عبدالله", "text": "فريق محترف وخدمة ممتازة", "rating": 5},
                ]}},
                {"type": "contact", "order": 4, "data": {"title": "احجز موعدك", "phone": "+966 11 000 0000", "hours": "السبت - الخميس 9 ص - 10 م"}},
                {"type": "footer", "order": 5, "data": {"brand": "عيادة الابتسامة"}},
            ],
        },
        {
            "id": "clinic_general",
            "name": "عيادة عامة",
            "icon": "🏥",
            "description": "عيادة شاملة للعائلة",
            "theme": _theme("#3B82F6", "#0f172a", "#10B981", bg="#f8fafc", text="#0f172a", radius="medium"),
            "sections": [
                {"type": "hero", "order": 0, "data": {
                    "title": "🏥 عيادة العائلة الشاملة",
                    "subtitle": "أطباء متخصصون، تشخيص دقيق، رعاية من القلب",
                    "cta_text": "احجز موعداً",
                    "image": _img("https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?w=1600"),
                    "layout": "split",
                }},
                {"type": "features", "order": 1, "data": {"title": "التخصصات", "items": [
                    {"icon": "👶", "title": "أطفال", "text": "رعاية شاملة للمواليد والأطفال"},
                    {"icon": "❤️", "title": "باطنية", "text": "فحوصات دورية وعلاج الأمراض"},
                    {"icon": "👁️", "title": "عيون", "text": "فحص شامل ونظارات"},
                    {"icon": "🦴", "title": "عظام", "text": "إصابات ومفاصل"},
                ]}},
                {"type": "contact", "order": 2, "data": {"title": "تواصل معنا", "phone": "+966 11 000 0000"}},
                {"type": "footer", "order": 3, "data": {"brand": "عيادة العائلة"}},
            ],
        },
    ],

    # ---------------------- PLUMBING ---------------------------
    "plumbing": [
        {
            "id": "plumbing_service",
            "name": "خدمات سباكة",
            "icon": "🔧",
            "description": "سبّاك محترف متوفّر 24/7",
            "theme": _theme("#2563EB", "#18181b", "#F59E0B", radius="medium", font="Cairo"),
            "sections": [
                {"type": "hero", "order": 0, "data": {
                    "title": "🔧 سبّاكنا متوفر لك 24/7",
                    "subtitle": "إصلاح تسريبات، تمديد مواسير، تركيب أدوات صحية — بأسعار عادلة",
                    "cta_text": "اتصل الآن",
                    "image": _img("https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=1600"),
                    "layout": "split",
                }},
                {"type": "features", "order": 1, "data": {"title": "خدماتنا", "items": [
                    {"icon": "💧", "title": "كشف تسريبات", "text": "بأحدث الأجهزة بدون تكسير"},
                    {"icon": "🚿", "title": "تركيب سخانات", "text": "كهربائية وغاز وشمسية"},
                    {"icon": "🚽", "title": "تركيب أدوات صحية", "text": "مرحاض، مغسلة، شطاف"},
                    {"icon": "🔨", "title": "تسليك مجاري", "text": "خدمة طوارئ سريعة"},
                ]}},
                {"type": "pricing", "order": 2, "data": {"title": "أسعارنا الشفافة", "plans": [
                    {"name": "كشف مجاني", "price": "0", "period": "ريال", "features": ["تقييم المشكلة", "عرض سعر واضح", "بدون التزام"], "cta": "احجز"},
                    {"name": "إصلاح عادي", "price": "من 150", "period": "ريال", "features": ["قطع غيار أصلية", "ضمان 30 يوم", "فني معتمد"], "cta": "اطلب", "featured": True},
                    {"name": "عقد صيانة سنوي", "price": "1200", "period": "ريال", "features": ["زيارتين شهرياً", "خصم 30%", "أولوية الطوارئ"], "cta": "اشترك"},
                ]}},
                {"type": "testimonials", "order": 3, "data": {"title": "عملاء راضون", "items": [
                    {"name": "فهد", "text": "حضر بسرعة وأصلح المشكلة بكفاءة", "rating": 5},
                ]}},
                {"type": "cta", "order": 4, "data": {"title": "📞 اتصل الآن — جاهزون خلال 30 دقيقة", "cta_text": "اتصل بنا"}},
                {"type": "contact", "order": 5, "data": {"title": "تواصل", "phone": "+966 50 000 0000"}},
                {"type": "footer", "order": 6, "data": {"brand": "سبّاك الثقة"}},
            ],
        },
    ],

    # ---------------------- ELECTRICAL ---------------------------
    "electrical": [
        {
            "id": "electrical_service",
            "name": "خدمات كهرباء",
            "icon": "⚡",
            "description": "كهربائي معتمد لكل الأعطال",
            "theme": _theme("#FBBF24", "#18181b", "#F97316", radius="medium", font="Cairo"),
            "sections": [
                {"type": "hero", "order": 0, "data": {
                    "title": "⚡ كهربائي بين يديك",
                    "subtitle": "إصلاح أعطال، تمديد كهرباء، تركيب إنارة، صيانة لوحات — بضمان كامل",
                    "cta_text": "اطلب فنّياً",
                    "image": _img("https://images.unsplash.com/photo-1621905252507-b35492cc74b4?w=1600"),
                    "layout": "split",
                }},
                {"type": "features", "order": 1, "data": {"title": "خدماتنا", "items": [
                    {"icon": "💡", "title": "تركيب إنارة", "text": "LED وسبوتات وثريّات"},
                    {"icon": "🔌", "title": "تمديد كهرباء", "text": "منازل ومكاتب ومحلات"},
                    {"icon": "⚠️", "title": "إصلاح أعطال", "text": "طوارئ 24/7"},
                    {"icon": "🏠", "title": "لوحات رئيسية", "text": "ترقية وصيانة"},
                ]}},
                {"type": "pricing", "order": 2, "data": {"title": "الأسعار", "plans": [
                    {"name": "كشف", "price": "مجاني", "period": "", "features": ["تقييم شامل", "بدون التزام"], "cta": "احجز"},
                    {"name": "صيانة منزل", "price": "300", "period": "ريال", "features": ["فحص كامل", "إصلاح الأعطال الصغيرة"], "cta": "اطلب", "featured": True},
                    {"name": "تمديد كامل", "price": "حسب الموقع", "period": "", "features": ["تصميم مخطط", "تمديد احترافي", "ضمان 5 سنوات"], "cta": "استشر"},
                ]}},
                {"type": "team", "order": 3, "data": {"title": "فنيون معتمدون", "members": [
                    {"name": "سالم العتيبي", "role": "كهربائي رئيسي (12 سنة خبرة)", "image": ""},
                ]}},
                {"type": "cta", "order": 4, "data": {"title": "⚡ خدمة الطوارئ 24/7", "cta_text": "اتصل الآن"}},
                {"type": "footer", "order": 5, "data": {"brand": "كهربائي الثقة"}},
            ],
        },
    ],

    # ---------------------- STORE — extra layouts ----------------------
    "store": [
        {
            "id": "store_fashion",
            "name": "متجر أزياء",
            "icon": "👗",
            "description": "موضة عصرية، بوتيك أنيق",
            "theme": _theme("#EC4899", "#18181b", "#A78BFA", radius="small", font="Readex Pro"),
            "sections": [
                {"type": "hero", "order": 0, "data": {
                    "title": "أناقتك تبدأ هنا",
                    "subtitle": "أحدث صيحات الموضة — لمن تحبّ أن تبرز",
                    "cta_text": "اكتشف الكوليكشن", "image": _img("https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1600"),
                    "layout": "split",
                }},
                {"type": "products", "order": 1, "data": {"title": "أحدث المجموعة", "items": [
                    {"name": "فستان سهرة", "price": "599", "image": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=600", "badge": "جديد"},
                    {"name": "قميص قطني", "price": "149", "image": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600"},
                    {"name": "حقيبة يد", "price": "329", "image": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=600"},
                    {"name": "حذاء رياضي", "price": "449", "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600", "badge": "رائج"},
                ]}},
                {"type": "gallery", "order": 2, "data": {"title": "ستايلك", "images": [
                    "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=800",
                    "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=800",
                    "https://images.unsplash.com/photo-1558769132-cb1aea458c5e?w=800",
                    "https://images.unsplash.com/photo-1603252109303-2751441dd157?w=800",
                ]}},
                {"type": "cta", "order": 3, "data": {"title": "خصم 20% على أول طلب", "cta_text": "اشترك"}},
                {"type": "footer", "order": 4, "data": {"brand": "بوتيك الأناقة"}},
            ],
        },
    ],
}


# ============================================================================
# Category → layouts (combine base templates + extra layouts)
# ============================================================================
def _base_as_layout(key: str) -> Dict[str, Any]:
    t = BASE_TEMPLATES[key]
    return {
        "id": key, "name": t["name"], "icon": t["icon"], "description": t["description"],
        "theme": t["theme"], "sections": t["sections"], "custom_css": "",
    }


# Categories ordered for display (with professional Unsplash hero images)
CATEGORIES: List[Dict[str, Any]] = [
    {"id": "restaurant", "name": "مطاعم",           "icon": "🍽️", "color": "#D4AF37",
     "image": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=600&q=70"},
    {"id": "coffee",     "name": "كوفي شوب",         "icon": "☕", "color": "#92400E",
     "image": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=600&q=70"},
    {"id": "store",      "name": "متاجر",            "icon": "🛍️", "color": "#FF6B35",
     "image": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=600&q=70"},
    {"id": "barber",     "name": "حلاقة رجال",        "icon": "💈", "color": "#D4AF37",
     "image": "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=600&q=70"},
    {"id": "salon_women","name": "صالون نساء",        "icon": "💇‍♀️", "color": "#EC4899",
     "image": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=600&q=70"},
    {"id": "pets",       "name": "قطط وحيوانات",     "icon": "🐱", "color": "#D97706",
     "image": "https://images.unsplash.com/photo-1425082661705-1834bfd09dca?w=600&q=70"},
    {"id": "clinic",     "name": "عيادات",           "icon": "🏥", "color": "#06B6D4",
     "image": "https://images.unsplash.com/photo-1587351021759-3e566b6af7cc?w=600&q=70"},
    {"id": "bakery",     "name": "مخبز وحلويات",      "icon": "🍰", "color": "#F472B6",
     "image": "https://images.unsplash.com/photo-1549007994-cb92caebd54b?w=600&q=70"},
    {"id": "car_wash",   "name": "غسيل سيارات",       "icon": "🚗", "color": "#0EA5E9",
     "image": "https://images.unsplash.com/photo-1520340356584-f9917d1eea6f?w=600&q=70"},
    {"id": "sports_club","name": "نوادي رياضية",      "icon": "🏋️", "color": "#059669",
     "image": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=600&q=70"},
    {"id": "library",    "name": "مكتبة وقرطاسية",    "icon": "📚", "color": "#7C3AED",
     "image": "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=600&q=70"},
    {"id": "art_gallery","name": "معارض فنية",        "icon": "🎨", "color": "#B45309",
     "image": "https://images.unsplash.com/photo-1545987796-200677ee1011?w=600&q=70"},
    {"id": "maintenance","name": "فني صيانة",         "icon": "🛠️", "color": "#EA580C",
     "image": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&q=70"},
    {"id": "jewelry",    "name": "مجوهرات وذهب",      "icon": "💍", "color": "#FBBF24",
     "image": "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=600&q=70"},
    {"id": "gym",        "name": "صالات رياضية",       "icon": "🏋️", "color": "#0891B2",
     "image": "https://images.unsplash.com/photo-1534258936925-c58bed479fcb?w=600&q=70"},
    {"id": "academy",    "name": "أكاديميات تعليمية",   "icon": "🎓", "color": "#7C2D12",
     "image": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=600&q=70"},
    {"id": "plumbing",   "name": "سباكة",             "icon": "🔧", "color": "#2563EB",
     "image": "https://images.unsplash.com/photo-1606613221062-5c4c2d85ce31?w=600&q=70"},
    {"id": "electrical", "name": "كهرباء",            "icon": "⚡", "color": "#FBBF24",
     "image": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&q=70"},
    {"id": "company",    "name": "شركات",             "icon": "🏢", "color": "#3B82F6",
     "image": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=600&q=70"},
    {"id": "portfolio",  "name": "بورتفوليو",          "icon": "🎭", "color": "#EC4899",
     "image": "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=600&q=70"},
    {"id": "saas",       "name": "SaaS / تطبيقات",   "icon": "💻", "color": "#10B981",
     "image": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=600&q=70"},
    # 🆕 New categories — Feb 27, 2026
    {"id": "cosmetics",  "name": "مكياج وعطور",       "icon": "💄", "color": "#E91E63",
     "image": "https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=600&q=70"},
    {"id": "automotive", "name": "معارض سيارات",       "icon": "🏎️", "color": "#DC2626",
     "image": "https://images.unsplash.com/photo-1494976388531-d1058494cdd8?w=600&q=70"},
    {"id": "realestate", "name": "دلّال عقارات",        "icon": "🏛️", "color": "#B87333",
     "image": "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&q=70"},
    {"id": "blank",      "name": "مخصّص / فارغ",       "icon": "✨", "color": "#FFD700",
     "image": "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=600&q=70"},
]


def list_categories() -> List[Dict[str, Any]]:
    out = []
    for c in CATEGORIES:
        out.append({**c, "layouts_count": len(list_layouts(c["id"]))})
    return out


def _mutate_sections(base_sections: List[Dict[str, Any]], hero_layout: str, arrangement: str) -> List[Dict[str, Any]]:
    """Apply a structural arrangement to base sections — creates radically different layouts."""
    out = []
    footer = None
    non_hero = []
    for s in base_sections:
        if s.get("type") == "hero":
            new = {**s, "data": {**(s.get("data") or {}), "layout": hero_layout}}
            out.append(new)
        elif s.get("type") == "footer":
            footer = s
        else:
            non_hero.append(s)

    # arrangement strategies: each produces a DIFFERENT structural feel
    if arrangement == "story_first":
        # Brand story timeline comes right after hero
        out.append({
            "id": "story-tl-auto", "type": "story_timeline", "order": 1, "visible": True,
            "data": {"title": "قصتنا", "items": [
                {"year": "2015", "title": "البداية", "text": "انطلقنا برؤية فريدة لخدمة مميزة."},
                {"year": "2019", "title": "التوسّع", "text": "فتحنا فروعاً في 3 مدن جديدة."},
                {"year": "2022", "title": "التميّز", "text": "أُعلنّا كأفضل علامة في المنطقة."},
                {"year": "2025", "title": "اليوم", "text": "آلاف العملاء الراضين عنا."},
            ]},
        })
        out.extend(non_hero)
    elif arrangement == "process_first":
        # "How it works" steps come right after hero
        out.append({
            "id": "ps-auto", "type": "process_steps", "order": 1, "visible": True,
            "data": {"title": "كيف تعمل خدمتنا؟", "items": [
                {"title": "اختر", "text": "تصفّح خياراتنا بسهولة"},
                {"title": "اطلب", "text": "قدّم طلبك في دقائق"},
                {"title": "استمتع", "text": "نوصّل إليك أينما كنت"},
            ]},
        })
        out.extend(non_hero)
    elif arrangement == "reservation_first":
        # Booking form comes right after hero
        out.append({
            "id": "res-auto", "type": "reservation", "order": 1, "visible": True,
            "data": {"title": "احجز مكانك الآن", "subtitle": "لا تفوّت فرصتك — املأ النموذج وسنعاود التواصل فوراً"},
        })
        out.extend(non_hero)
    elif arrangement == "feature_alt":
        # Replace features with alt layout
        swapped = []
        for s in non_hero:
            if s.get("type") == "features":
                swapped.append({**s, "data": {**(s.get("data") or {}), "layout": "alt"}})
            else:
                swapped.append(s)
        out.extend(swapped)
    elif arrangement == "quote_middle":
        # Insert a big quote block in the middle
        mid = len(non_hero) // 2
        out.extend(non_hero[:mid])
        out.append({
            "id": "q-auto", "type": "quote", "order": 0, "visible": True,
            "data": {"text": "خدمة استثنائية تفوق التوقّعات — كل مرة.", "author": "ضيف دائم", "role": "عميل منذ 2020"},
        })
        out.extend(non_hero[mid:])
    elif arrangement == "horizontal_features":
        # Features as horizontal list (different visual)
        swapped = []
        for s in non_hero:
            if s.get("type") == "features":
                swapped.append({**s, "data": {**(s.get("data") or {}), "layout": "horizontal"}})
            else:
                swapped.append(s)
        out.extend(swapped)
    elif arrangement == "reversed":
        # Reverse the section order
        out.extend(list(reversed(non_hero)))
    else:  # "default"
        out.extend(non_hero)

    if footer:
        out.append(footer)
    # Renumber orders
    return [{**s, "order": i} for i, s in enumerate(out)]


def list_layouts(category_id: str) -> List[Dict[str, Any]]:
    """Return 20 STRUCTURALLY DISTINCT templates for this category.

    Each template is an archetype × this category's content. No color
    variants — colors are chosen in a separate wizard step AFTER the user
    picks a template. Same archetype × different category = meaningfully
    different-looking template (different hero text, different images,
    different primary grid = menu/products/services).
    """
    from .template_archetypes import ARCHETYPES, NEUTRAL_THEME
    from .category_content import get_category_config, resolve_placeholder, resolve_section_type
    from .template_themes import apply_archetype_theme, get_hero_image_for

    cfg = get_category_config(category_id)
    out: List[Dict[str, Any]] = []

    for arch in ARCHETYPES:
        # Build per-archetype theme (unique palette, font, hero image, custom CSS)
        archetype_theme = apply_archetype_theme(arch["id"], category_id, dict(NEUTRAL_THEME))
        archetype_hero = get_hero_image_for(category_id, arch["id"])

        sections: List[Dict[str, Any]] = []
        for idx, (section_type, style, placeholder_id) in enumerate(arch["sections"]):
            resolved_type = resolve_section_type(section_type, cfg)
            data = resolve_placeholder(placeholder_id, category_id, cfg)
            # Override hero image with archetype-specific image so each card looks different
            if resolved_type == "hero":
                data = {**data, "image": archetype_hero}
            if style:
                data = {**data, "style": style}
            sections.append({
                "id": f"sec-{arch['id']}-{idx}",
                "type": resolved_type,
                "order": idx,
                "visible": True,
                "data": data,
            })
        # Append standard footer
        sections.append({
            "id": f"sec-{arch['id']}-footer",
            "type": "footer",
            "order": len(sections),
            "visible": True,
            "data": {"brand": cfg.get("hero_title", "موقعك").split("·")[0].strip(),
                     "about": cfg.get("about_text", "")},
        })
        out.append({
            "id": f"{category_id}__{arch['id']}",
            "name": arch["name_ar"],
            "icon": cfg.get("accent_emoji", "✨"),
            "description": arch["description"],
            "density": arch["density"],
            "hero_layout": arch["hero_layout"],
            "sections_count": len(sections),
            "theme": archetype_theme,
            "theme_name": archetype_theme.get("_archetype_theme_name"),
            "hero_image": archetype_theme.get("_hero_image"),
            "sections": sections,
        })
    return out


def get_layout(category_id: str, layout_id: str) -> Dict[str, Any]:
    for L in list_layouts(category_id):
        if L["id"] == layout_id:
            return L
    # Fallback: first layout of category
    lst = list_layouts(category_id)
    return lst[0] if lst else _base_as_layout("blank")
