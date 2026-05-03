"""
Domain Intelligence Library for FreeBuild v2.

Each blueprint defines, for a specific domain:
    • PERSONAS — who uses the site (admin, parent, kid, customer, etc.)
    • PAGES — required SPA hash routes with purpose & content
    • FEATURES — what each page must include (interactive widgets, AI hooks)
    • FLOWS — end-to-end user journeys (e.g. parent → load credit → kid earns)
    • INTEGRATIONS — APIs / browser features the AI must wire up
    • COHESION — cross-page linking rules
    • DESIGN — palette, typography, vibe

The architect AI receives the matching blueprint as a hardened system message
so it cannot ship a half-baked site missing critical features.
"""
from typing import Dict, Any, List, Optional


# ─── Domain detection: keywords (Arabic + English) → blueprint key ─────
DOMAIN_KEYWORDS: List[tuple] = [
    (("قرآن", "قران", "تحفيظ", "حفظ", "مصحف", "تلاوة", "تجويد", "تسميع",
      "قارئ", "قراء", "حلقة", "حلقات",
      "quran", "memorization", "tajweed", "recitation", "reciter"),
     "quran_memorization"),
    (("مطعم", "مقهى", "كافيه", "منيو", "وجبات", "أكل", "حجز طاولة",
      "restaurant", "cafe", "menu", "dining"),
     "restaurant"),
    (("متجر", "بضاعة", "منتج", "منتجات", "سلة", "شراء", "بيع", "إلكتروني",
      "store", "shop", "ecommerce", "cart", "checkout", "products"),
     "ecommerce_store"),
    (("نادي", "رياضي", "كرة", "لاعب", "لاعبين", "مباراة", "بطولة", "مشجع",
      "club", "sports", "football", "soccer", "match", "league"),
     "sports_club"),
    (("عيادة", "طبيب", "أطباء", "صحة", "حجز موعد", "كشف", "علاج",
      "clinic", "doctor", "medical", "health"),
     "clinic"),
    (("أكاديمية", "تعليم", "دورة", "دورات", "كورس", "طلاب", "معلم", "مدرس",
      "academy", "course", "courses", "education", "tutor"),
     "academy_education"),
    (("عقار", "عقاري", "فيلا", "بيت", "شقة", "أرض",
      "real-estate", "property", "villa"),
     "realestate"),
    (("صالون", "حلاقة", "تجميل", "سبا", "salon", "spa", "beauty"),
     "salon_beauty"),
]


def detect_domain(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.lower()
    scores: Dict[str, int] = {}
    for kws, key in DOMAIN_KEYWORDS:
        for kw in kws:
            if kw in t:
                scores[key] = scores.get(key, 0) + 1
    if not scores:
        return None
    return max(scores.items(), key=lambda x: x[1])[0]


# ─── Blueprints ────────────────────────────────────────────────────────
BLUEPRINTS: Dict[str, Dict[str, Any]] = {
    # ═══════════════════════════════════════════════════════════════════
    "quran_memorization": {
        "title": "موقع تحفيظ القرآن الكريم",
        "personas": [
            "👨‍👩 الأب/الأم (الراعي): يدير حساب الطفل، يحوّل المكافآت، يتابع التقدم",
            "👶 الطفل/الطالب: يحفظ، يسجّل صوته، يستلم تصحيح فوري من الذكاء",
            "🧑‍🏫 المعلم/المشرف: يضيف خطط الحفظ، يتابع الطلاب، يقيّم",
            "🏛️ الإدارة: تدير المحتوى، القراء، الإحصائيات",
        ],
        "pages": [
            ("#/home", "الواجهة الرئيسية: hero قوي + هدف الموقع + كروت تنقل لكل قسم رئيسي"),
            ("#/login", "تسجيل الدخول للأب/الطفل/المعلم"),
            ("#/register", "إنشاء حساب — اختيار النوع (أب/طفل/معلم)"),
            ("#/dashboard-parent", "لوحة الأب: إحصائيات تقدم الطفل + رصيد المكافآت + زر تحويل + نشاط أخير"),
            ("#/dashboard-child", "لوحة الطفل: درس اليوم + نقاطي + شجرة الإنجاز + زر بدء التحفيظ"),
            ("#/readers", "مكتبة القرّاء: 6+ قرّاء بكروت + مشغّل صوت لكل قارئ (mp3quran.net)"),
            ("#/memorize", "صفحة التحفيظ التفاعلية: عرض الآية + زر تشغيل + زر تسجيل + مرئي صوت + AI feedback"),
            ("#/lessons", "خطة الحفظ: قائمة بـ surahs/آيات مرتبة بنظام التدرّج + شريط تقدم"),
            ("#/rewards", "نظام المكافآت: نقاطي + leaderboard + متجر مكافآت + سجل التحويلات"),
            ("#/transfer", "تحويل مكافآت: form للأب يحدد المبلغ والمناسبة + سجل التحويلات السابقة"),
            ("#/leaderboard", "ترتيب الطلاب: top 20 طالب الأسبوع/الشهر + medals"),
            ("#/teacher", "صفحة المعلم: قائمة الطلاب + تقدم كل طالب + assign خطة"),
            ("#/profile", "ملف المستخدم: الاسم، الصورة، النقاط، الإنجازات، تغيير كلمة السر"),
            ("#/settings", "الإعدادات: لغة، إشعارات، اختيار قارئ مفضل، تغيير كلمة السر"),
            ("#/about", "نبذة + رؤية الموقع + الفريق + شراكات (مثلاً: نموذج تحفيظ جامعة الملك سعود)"),
            ("#/contact", "تواصل: form + معلومات + خريطة"),
        ],
        "must_have_features": [
            "🎙️ زر تسجيل الصوت في #/memorize: يستخدم Web Audio API + MediaRecorder. عرض موجة الصوت visualizer مباشر.",
            "🤖 AI تصحيح: بعد تسجيل الطفل، يظهر pseudo-feedback (placeholder div بنفسجي) 'الذكاء يحلل التلاوة...' ثم rating ⭐⭐⭐⭐ + tips للتحسين. مكان للاتصال بـAPI لاحقاً.",
            "📚 #/readers (مكتبة القرّاء): **إجباري عرض كل الـ20 قارئ** المتوفرين في الـverified library. Grid 3 أعمدة، كل بطاقة فيها صورة أيقونة (أول حرف من اسم القارئ على دائرة ذهبية)، الاسم، البلد، البايو، و`<audio controls>` بصوت السورة الكاملة. **استدعِ `quran_reciter_lookup` بدون name مرة وحدة** للحصول على كل الـ20.",
            "🔢 سلكتر السور: dropdown في #/readers يضم 114 سورة. عند الاختيار، JavaScript يحدّث كل الـaudio elements بـURL السورة الجديدة (`server{server}.mp3quran.net/{slug}/{surah:03d}.mp3`).",
            "📈 خطة حفظ ذكية في #/lessons: التدرّج (سور قصيرة → طويلة) + repetition spaced — كل آية تتكرر بعد 1، 3، 7، 14 يوم.",
            "🏆 نقاط فورية: كل آية محفوظة = 10 نقاط، تجويد ممتاز = +5 bonus.",
            "💰 محفظة مكافآت قابلة للتحويل: الأب يحدد قيمة 100 نقطة (مثلاً 5 ريال) + يحوّل عبر #/transfer.",
            "🔁 وضع الترديد التلقائي: تشغيل آية، توقّف، reciting، تشغيل مرة ثانية — بحلقة قابلة للتخصيص.",
            "🎯 تتبّع نقاط الضعف: كل سورة فيها كلمات الطفل أخطأ فيها → highlight بالأحمر للتمرين.",
            "🌙 ثيم ديني: amber/dark + خط Amiri Quran للآيات + خط Tajawal للنصوص.",
            "📱 لوحة الأب فيها live notification feed: 'فهد حفظ سورة الفجر، +50 نقطة الآن'.",
        ],
        "user_flows": [
            "1. الأب يسجّل → ينشئ حساب الطفل → يربط الحسابين.",
            "2. المعلم يحدد خطة حفظ للطفل (مثلاً: جزء عمّ في 60 يوم).",
            "3. الطفل يفتح #/memorize → يسمع الآية بصوت قارئه المفضل → يضغط 'سجّل صوتي' → يقرأ → يسلّم.",
            "4. الذكاء يقيّم → يعطي نقاط → الأب يحصل notification.",
            "5. الطفل يفتح #/rewards → يشوف نقاطه → يطلب تحويل من الأب.",
            "6. الأب يفتح #/transfer → يوافق → النقاط تتحوّل لرصيد قابل للسحب أو هدية.",
        ],
        "integrations": [
            "Web Audio API + MediaRecorder للتسجيل (browser-native)",
            "Canvas للـwaveform visualizer",
            "mp3quran.net CDN لتلاوات القرّاء",
            "خطوط Google: Amiri Quran + Tajawal + Reem Kufi",
            "localStorage لحفظ تقدم الطفل (offline-first)",
        ],
        "cohesion_rules": [
            "كرت 'القرّاء' في #/home → لازم يلينك لـ#/readers",
            "كرت 'ابدأ التحفيظ' → #/memorize",
            "كرت 'المكافآت' → #/rewards",
            "كرت 'لوحة الأب' → #/dashboard-parent",
            "في #/dashboard-child: زر 'حوّل مكافآتي' → #/transfer",
            "في #/leaderboard: كل اسم طالب → #/profile/{id}",
        ],
        "design": {
            "palette": "amber/gold (#d4af37, #f59e0b) on deep navy/black (#0a0a14, #1a1208) — feeling reverent",
            "fonts": "Amiri Quran للآيات، Reem Kufi للعناوين، Tajawal للنصوص",
            "vibe": "spiritual, premium, scholarly. Generous whitespace. Gold dividers.",
        },
    },

    # ═══════════════════════════════════════════════════════════════════
    "restaurant": {
        "title": "موقع مطعم",
        "personas": ["👨‍🍳 المالك/الإدارة", "🧑 العميل (يحجز/يطلب)", "🚚 موصّل"],
        "pages": [
            ("#/home", "Hero بصورة طبق + CTA حجز/طلب + مميزات + قسم منيو سريع"),
            ("#/menu", "منيو كامل: tabs (مقبلات/أطباق/حلويات/مشروبات) + كروت + سعر + add-to-cart"),
            ("#/menu/{item-id}", "صفحة طبق: صور + وصف + مكونات + customize + reviews"),
            ("#/reservation", "حجز طاولة: form (تاريخ، وقت، عدد، ملاحظات)"),
            ("#/orders", "طلبات الديليفري: تتبع حالة الطلب live"),
            ("#/cart", "سلة + قسائم خصم + total"),
            ("#/checkout", "اختيار شحن/استلام + دفع"),
            ("#/about", "قصة المطعم + الشيف + الفريق"),
            ("#/contact", "تواصل + خريطة + ساعات العمل"),
            ("#/loyalty", "برنامج الولاء: نقاطي + مستويات + هدايا"),
        ],
        "must_have_features": [
            "🛒 سلة عائمة في كل الصفحات",
            "🗓️ حجز طاولة مع time slots",
            "🏆 برنامج ولاء بنقاط",
            "📍 خريطة Google embed",
            "📸 معرض صور للمكان",
            "⭐ تقييمات العملاء",
        ],
        "cohesion_rules": [
            "صورة طبق في #/home → #/menu/{id}",
            "زر CTA → #/reservation",
            "كل طبق في #/menu → #/menu/{id}",
        ],
        "design": {
            "palette": "warm reds + cream + dark wood feel",
            "fonts": "Tajawal للنصوص، Cairo Black للعناوين",
            "vibe": "cozy, appetizing, warm",
        },
    },

    # ═══════════════════════════════════════════════════════════════════
    "ecommerce_store": {
        "title": "متجر إلكتروني",
        "personas": ["🏪 المالك", "🛍️ العميل", "🚚 شركة شحن"],
        "pages": [
            ("#/home", "Hero + best sellers + categories + new arrivals"),
            ("#/products", "قائمة منتجات + filters + search + sort"),
            ("#/products/{id}", "صفحة منتج: gallery + variants + reviews + related"),
            ("#/categories", "كل الفئات بكروت كبيرة"),
            ("#/cart", "سلة"),
            ("#/checkout", "بيانات شحن + دفع"),
            ("#/account", "حسابي: orders + addresses + wishlist"),
            ("#/wishlist", "المفضلة"),
            ("#/orders", "طلباتي + tracking"),
            ("#/login"), ("#/register"),
            ("#/about"), ("#/contact"), ("#/faq"),
        ],
        "must_have_features": [
            "🔍 search bar في navbar",
            "🛒 سلة بـlive count badge",
            "❤️ wishlist toggle على كل منتج",
            "⭐ rating + reviews",
            "🚚 خيارات شحن متعددة في #/checkout",
            "💳 دفع متعدد (Stripe/COD)",
        ],
        "cohesion_rules": [
            "كرت منتج → #/products/{id}",
            "أيقونة سلة في navbar → #/cart",
            "badge wishlist → #/wishlist",
        ],
        "design": {"palette": "modern + brand color", "fonts": "Tajawal", "vibe": "clean, conversion-focused"},
    },

    # ═══════════════════════════════════════════════════════════════════
    "sports_club": {
        "title": "نادي رياضي",
        "personas": ["⚽ النادي", "🧑 المشجع", "👤 اللاعب", "📊 المحلل"],
        "pages": [
            ("#/home", "Hero + آخر مباريات + لاعبي الأسبوع + رابطة"),
            ("#/players", "قائمة اللاعبين بكروت بصور"),
            ("#/players/{id}", "صفحة لاعب: stats + matches + photos"),
            ("#/matches", "جدول المباريات: قادمة/سابقة + scores"),
            ("#/matches/{id}", "تفاصيل مباراة: events live + lineups + stats"),
            ("#/standings", "الترتيب في الدوري"),
            ("#/news", "أخبار النادي"),
            ("#/store", "متجر النادي: قمصان/أوشحة"),
            ("#/fans", "نقاط المشجعين + leaderboard + مكافآت"),
            ("#/membership", "اشتراك عضوية النادي"),
            ("#/tickets", "حجز تذاكر مباراة"),
            ("#/about"), ("#/contact"),
        ],
        "must_have_features": [
            "📊 stats cards حية في #/home",
            "🎫 شراء تذاكر",
            "🏆 leaderboard للمشجعين",
            "🎁 مكافآت ولاء",
            "🎨 ألوان النادي",
        ],
        "cohesion_rules": [
            "كرت لاعب → #/players/{id}",
            "كرت مباراة → #/matches/{id}",
            "زر شراء تذكرة → #/tickets",
        ],
        "design": {"palette": "ألوان النادي (أخضر سعودي / أزرق / أحمر)", "vibe": "energetic, bold"},
    },

    # ═══════════════════════════════════════════════════════════════════
    "clinic": {
        "title": "عيادة طبية",
        "personas": ["🏥 الإدارة", "👨‍⚕️ الطبيب", "🧑 المريض"],
        "pages": [
            ("#/home", "Hero + خدمات + أطباء + احجز الآن"),
            ("#/services", "كل الخدمات/التخصصات"),
            ("#/services/{id}", "تفاصيل خدمة"),
            ("#/doctors", "قائمة الأطباء بكروت"),
            ("#/doctors/{id}", "بروفايل طبيب + المواعيد المتاحة"),
            ("#/booking", "حجز موعد: خطوات (طبيب → خدمة → تاريخ → تأكيد)"),
            ("#/my-appointments", "مواعيدي + إعادة جدولة + إلغاء"),
            ("#/medical-records", "ملفي الطبي: تشخيصات + وصفات"),
            ("#/login"), ("#/register"),
            ("#/about"), ("#/contact"),
        ],
        "must_have_features": [
            "🗓️ نظام حجز مواعيد كامل",
            "📋 ملف طبي للمريض",
            "💊 وصفات طبية",
            "📞 hotline زر",
        ],
        "cohesion_rules": [
            "كرت طبيب → #/doctors/{id}",
            "كرت خدمة → #/services/{id}",
            "زر احجز → #/booking",
        ],
        "design": {"palette": "أزرق طبي ناعم + أبيض", "vibe": "professional, clean, trustworthy"},
    },

    # ═══════════════════════════════════════════════════════════════════
    "academy_education": {
        "title": "أكاديمية تعليم",
        "personas": ["🎓 الأكاديمية", "🧑‍🏫 المعلم", "👶 الطالب", "👨‍👩 ولي الأمر"],
        "pages": [
            ("#/home", "Hero + دوراتنا + شهاداتنا + مميزات"),
            ("#/courses", "كل الدورات بكروت + filters حسب المستوى"),
            ("#/courses/{id}", "تفاصيل دورة: محتوى + معلم + سعر + اشترك"),
            ("#/lessons/{course-id}", "دروس الدورة: video player + ملاحظات"),
            ("#/quiz/{lesson-id}", "اختبار الدرس"),
            ("#/dashboard-student", "لوحة الطالب: دوراتي + تقدمي + شهاداتي"),
            ("#/dashboard-parent", "لوحة الوالد: تقدم الأبناء"),
            ("#/dashboard-teacher", "لوحة المعلم: طلابي + تقييمات"),
            ("#/certificates", "شهاداتي"),
            ("#/leaderboard", "أفضل الطلاب"),
            ("#/profile"), ("#/login"), ("#/register"),
            ("#/about"), ("#/contact"),
        ],
        "must_have_features": [
            "🎥 فيديو دروس placeholder",
            "📝 اختبارات + scoring",
            "🏅 شهادات إنجاز",
            "📊 تقدم visual في كل دورة",
            "💬 chat مع المعلم placeholder",
        ],
        "cohesion_rules": [
            "كرت دورة → #/courses/{id}",
            "زر ابدأ الدرس → #/lessons/{id}",
            "زر شهاداتي → #/certificates",
        ],
        "design": {"palette": "أزرق علمي + أخضر تقدّم", "vibe": "modern educational"},
    },

    # ═══════════════════════════════════════════════════════════════════
    "realestate": {
        "title": "موقع عقاري",
        "personas": ["🏘️ شركة عقارية", "🧑 مشتري/مستأجر", "👨‍💼 وكيل"],
        "pages": [
            ("#/home", "Hero + بحث متقدم + properties مميزة"),
            ("#/properties", "كل العقارات + filters (نوع/سعر/منطقة) + map"),
            ("#/properties/{id}", "تفاصيل عقار: gallery + specs + location + agent"),
            ("#/agents", "وكلاؤنا"),
            ("#/agents/{id}", "بروفايل وكيل + listings"),
            ("#/inquiry", "نموذج استفسار"),
            ("#/saved", "العقارات المحفوظة"),
            ("#/about"), ("#/contact"),
        ],
        "must_have_features": [
            "🔍 بحث متقدم بـfilters",
            "🗺️ خريطة embed",
            "📞 زر اتصال على كل property",
            "❤️ حفظ العقار",
            "💰 حاسبة قسط",
        ],
        "cohesion_rules": [
            "كرت عقار → #/properties/{id}",
            "كرت وكيل → #/agents/{id}",
        ],
        "design": {"palette": "luxe gold + dark", "vibe": "premium, trustworthy"},
    },

    # ═══════════════════════════════════════════════════════════════════
    "salon_beauty": {
        "title": "صالون / مركز تجميل",
        "personas": ["💇 الإدارة", "🧑‍💼 موظف/فني", "👤 العميلة"],
        "pages": [
            ("#/home", "Hero + خدماتنا + احجز موعد"),
            ("#/services", "كل الخدمات + الأسعار"),
            ("#/services/{id}", "تفاصيل خدمة"),
            ("#/booking", "حجز موعد"),
            ("#/staff", "فريق الفنيين"),
            ("#/gallery", "معرض الأعمال"),
            ("#/about"), ("#/contact"),
            ("#/loyalty", "نقاط ولاء"),
        ],
        "must_have_features": [
            "🗓️ حجز موعد",
            "💅 معرض أعمال",
            "🎁 برنامج ولاء",
        ],
        "cohesion_rules": [
            "كرت خدمة → #/services/{id}",
            "زر احجز → #/booking",
        ],
        "design": {"palette": "وردي/ذهبي راقي", "vibe": "elegant, feminine, premium"},
    },
}


# ─── Generic fallback for unknown domains ──────────────────────────────
GENERIC_BLUEPRINT = {
    "title": "موقع مخصّص",
    "personas": ["🧑 المستخدم", "🏛️ الإدارة"],
    "pages": [
        ("#/home", "Hero + value prop + 3-6 ميزة رئيسية + CTA"),
        ("#/login"), ("#/register"),
        ("#/dashboard", "لوحة المستخدم"),
        ("#/profile"), ("#/settings"),
        ("#/about"), ("#/contact"),
    ],
    "must_have_features": [
        "🔐 auth: login + register + dashboard",
        "📱 navbar pill-style ذهبي للنشط",
        "📞 معلومات تواصل",
    ],
    "cohesion_rules": [
        "كرت في #/home → صفحة فرعية مفصّلة",
    ],
    "design": {"palette": "أنيق mocha/dark", "vibe": "modern, premium"},
}


def render_blueprint_block(domain_key: Optional[str]) -> str:
    """Format the blueprint as a Markdown block to inject into the architect's
    system prompt. Falls back to generic if domain unknown."""
    bp = BLUEPRINTS.get(domain_key or "") or GENERIC_BLUEPRINT
    parts: List[str] = []
    parts.append(f"# 🧠 خبرة المجال — {bp['title']}\n")
    parts.append(
        "أنت الآن خبير متخصّص في هذا المجال بـ15 سنة خبرة. الـcheck-list التالية "
        "**إجباري** أنه يكون كل بند منها مغطّى في الموقع قبل تقول 'done'.\n"
    )

    parts.append("\n## 👥 الشخصيات (Personas)")
    for p in bp.get("personas", []):
        parts.append(f"- {p}")

    parts.append("\n## 📄 الصفحات الإجبارية (كلها لازم تكون موجودة في نفس الـHTML كـSPA hash routes)")
    for entry in bp.get("pages", []):
        if isinstance(entry, tuple):
            route = entry[0]
            desc = entry[1] if len(entry) > 1 else ""
            parts.append(f"- `{route}` — {desc}")
        elif isinstance(entry, str):
            parts.append(f"- `{entry}`")

    if bp.get("must_have_features"):
        parts.append("\n## ⚡ مميزات إجبارية (لا يكتمل الموقع إلا بهذه)")
        for f in bp["must_have_features"]:
            parts.append(f"- {f}")

    if bp.get("user_flows"):
        parts.append("\n## 🔁 رحلات المستخدم (User Flows)")
        for f in bp["user_flows"]:
            parts.append(f"{f}")

    if bp.get("integrations"):
        parts.append("\n## 🔌 تقنيات/تكاملات مطلوبة")
        for i in bp["integrations"]:
            parts.append(f"- {i}")

    if bp.get("cohesion_rules"):
        parts.append(
            "\n## 🔗 قواعد الترابط (إجبارية) — كل عنصر في الرئيسية لازم يلينك "
            "لصفحته الفرعية المناسبة"
        )
        for c in bp["cohesion_rules"]:
            parts.append(f"- {c}")

    d = bp.get("design") or {}
    if d:
        parts.append("\n## 🎨 الهوية البصرية المقترحة")
        if d.get("palette"):
            parts.append(f"- ألوان: {d['palette']}")
        if d.get("fonts"):
            parts.append(f"- خطوط: {d['fonts']}")
        if d.get("vibe"):
            parts.append(f"- طابع عام: {d['vibe']}")

    parts.append(
        "\n## 🚨 قواعد الاكتمال (لا تكتب next_question_type=done إلا بعد التحقق)\n"
        "1. كل صفحة من القائمة فوق موجودة كـ`<section class=\"page\" id=\"page-XXX\">`.\n"
        "2. كل كرت/feature في #/home يلينك فعلياً (`<a href=\"#/...\">`) لصفحة موجودة.\n"
        "3. كل ميزة إجبارية مذكورة فوق منفّذة كـUI حقيقي (مو نص فقط).\n"
        "4. كل صورة في sub-page غنية وذات سياق (alt تفصيلي بالعربي للذكاء يولّدها).\n"
        "5. الـnavbar فيه روابط لكل الصفحات الرئيسية.\n"
        "6. لو وجدت أي قسم ناقص → أضفه في الـhtml_update القادم. لا تسأل أسئلة فاضية وقت في انتظارك.\n"
    )

    return "\n".join(parts)


# ─── Internal-linking enforcement instructions ─────────────────────────
LINKING_RULES = """
## 🔗 قواعد الربط الداخلي (إجبارية)

كل عنصر في الموقع له معنى تنقّلي **لازم** يكون clickable ويوديك لصفحة فرعية حقيقية.

### القواعد:
1. **كل كرت في صفحة الرئيسية** يجب أن يكون `<a href="#/sub-route">` يلفّ المحتوى. لا كرت بدون رابط.
2. **كل صورة سياقية** (مو decoration) يجب أن تكون داخل `<a href="#/sub-route">`. مثال:
   ```html
   <a href="#/rewards" class="card">
     <img src="@@IMG/auto@@" alt="كأس ذهبي وهدايا للأطفال المتميزين">
     <h3>نظام المكافآت</h3>
     <p>اكسب نقاط واحصل على هدايا</p>
   </a>
   ```
3. **كل زر CTA** ("ابدأ الآن"، "اعرض المزيد"، "تفاصيل أكثر") لازم يكون `<a>` أو يستدعي navigation. ممنوع `<button>` فاضي.
4. **لا dead links**: لو حطّيت `href="#/X"` لازم يكون موجود `<section id="page-X">` في نفس الـHTML.
5. **navbar links** كلها تشتغل، التبويب النشط بلون ذهبي تلقائياً (CSS `:target` أو JavaScript).
6. **الصفحات الفرعية ما تكون فاضية** — كل صفحة فرعية فيها هيرو + 3-5 أقسام + بيانات حقيقية + CTAs.
7. **breadcrumb** في الصفحات الفرعية: `الرئيسية / المكتبة / السديس`.
"""
