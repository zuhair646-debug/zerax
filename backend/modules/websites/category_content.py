"""
Category Content — per-category content for each placeholder used by archetypes.

An archetype defines section TYPES + placeholder IDs. This module maps each
(category_id, placeholder_id) pair to concrete section data — headline text,
images, items, etc. The result: same archetype × different category = a
genuinely different-looking template tuned to that business.
"""
from __future__ import annotations

from typing import Any, Dict, List


# ──────────────────────────────────────────────────────────────────────
# Per-category "tone" configuration (shapes ALL content)
# ──────────────────────────────────────────────────────────────────────
CATEGORY_CONFIG: Dict[str, Dict[str, Any]] = {
    "restaurant": {
        "hero_title": "نكهات تُحكى · تجربة تبقى",
        "hero_subtitle": "أطباقنا تحاكي أصالة المذاق الشرقي مع لمسة عصرية",
        "hero_image": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=1600&q=70",
        "cta": "احجز طاولة",
        "about_title": "قصة المطبخ",
        "about_text": "منذ 2015 ونحن نقدّم أفخر النكهات، من يد شيف مشهود له بتمكّنه وشغفه.",
        "primary_grid": "menu",
        "accent_emoji": "🍽️",
    },
    "coffee": {
        "hero_title": "قهوة مختصة · لحظات دافئة",
        "hero_subtitle": "حبوب مختارة بعناية، تحضير بشغف، خدمة من القلب",
        "hero_image": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=1600&q=70",
        "cta": "اطلب الآن",
        "about_title": "شغفنا بالقهوة",
        "about_text": "نختار الحبوب من أفضل المزارع في إثيوبيا وكولومبيا ونحمصها طازجة يومياً.",
        "primary_grid": "menu",
        "accent_emoji": "☕",
    },
    "store": {
        "hero_title": "تسوّق · اطلب · توصيل سريع",
        "hero_subtitle": "كل ما تحتاجه في مكان واحد — جودة مضمونة وأسعار تنافسية",
        "hero_image": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1600&q=70",
        "cta": "تسوّق الآن",
        "about_title": "تجربة تسوّق مختلفة",
        "about_text": "نعمل مع علامات موثوقة ونضمن لك جودة كل منتج، مع شحن سريع ومرتجعات سهلة.",
        "primary_grid": "products",
        "accent_emoji": "🛍️",
    },
    "barber": {
        "hero_title": "أسلوبك · بلمسة خبير",
        "hero_subtitle": "حلاقة متقنة، حلاقة ذقن فاخرة، تجربة رجولية لا تُنسى",
        "hero_image": "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=1600&q=70",
        "cta": "احجز موعد",
        "about_title": "فن الحلاقة الرجالية",
        "about_text": "صالون يجمع بين التقاليد الأصيلة وأحدث التقنيات، يقدّم خدمة استثنائية لكل عميل.",
        "primary_grid": "services",
        "accent_emoji": "💈",
    },
    "salon_women": {
        "hero_title": "جمالكِ · حكايتنا",
        "hero_subtitle": "سبا، شعر، أظافر، عروس — كل خدمة بلمسة فريدة",
        "hero_image": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1600&q=70",
        "cta": "احجزي موعد",
        "about_title": "عنايتكِ أولاً",
        "about_text": "فريقنا من الخبيرات يقدّم لكِ تجربة كاملة من اللحظة الأولى حتى آخر لمسة.",
        "primary_grid": "services",
        "accent_emoji": "💇‍♀️",
    },
    "pets": {
        "hero_title": "أصدقاؤك المفضّلون · برعاية محترفين",
        "hero_subtitle": "قص شعر، حمّام، فندقة، تطعيمات — حب وعناية لكل حيوان",
        "hero_image": "https://images.unsplash.com/photo-1425082661705-1834bfd09dca?w=1600&q=70",
        "cta": "احجز زيارة",
        "about_title": "عائلتك الصغيرة تستحق الأفضل",
        "about_text": "خبراء معتمدون يقدّمون رعاية متكاملة لقططك وكلابك في بيئة آمنة ومريحة.",
        "primary_grid": "services",
        "accent_emoji": "🐱",
    },
    "clinic": {
        "hero_title": "صحتك · أولويتنا",
        "hero_subtitle": "أطباء متخصصون، تقنيات حديثة، رعاية شاملة",
        "hero_image": "https://images.unsplash.com/photo-1587351021759-3e566b6af7cc?w=1600&q=70",
        "cta": "احجز كشف",
        "about_title": "رعاية طبية متميزة",
        "about_text": "عيادتنا تجمع أفضل الأطباء وأحدث المعدات لتقديم خدمة طبية بمستوى عالمي.",
        "primary_grid": "services",
        "accent_emoji": "🏥",
    },
    "bakery": {
        "hero_title": "حلوى طازجة · كل يوم",
        "hero_subtitle": "كيك مخصّص للمناسبات، حلويات شرقية، معجنات طازجة من الفرن",
        "hero_image": "https://images.unsplash.com/photo-1549007994-cb92caebd54b?w=1600&q=70",
        "cta": "اطلب الآن",
        "about_title": "خبرة 20 عاماً",
        "about_text": "صنعة عائلية متوارثة — نختار أفضل المكونات ونخبز يومياً لنضمن الطزاجة.",
        "primary_grid": "products",
        "accent_emoji": "🍰",
    },
    "car_wash": {
        "hero_title": "سيارتك · تلمع كالجديدة",
        "hero_subtitle": "غسيل متنقل يصلك أينما كنت، تلميع احترافي، حماية سيراميك",
        "hero_image": "https://images.unsplash.com/photo-1520340356584-f9917d1eea6f?w=1600&q=70",
        "cta": "احجز غسيل",
        "about_title": "خدمة سريعة واحترافية",
        "about_text": "فريق مدرّب يصل إليك بكل المعدات، ويعيد سيارتك كأنها خرجت من الوكالة.",
        "primary_grid": "services",
        "accent_emoji": "🚗",
    },
    "sports_club": {
        "hero_title": "العب · اربح · استمتع",
        "hero_subtitle": "ملاعب بادل وكرة قدم وتنس — حجوزات فورية، عروض مميزة",
        "hero_image": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1600&q=70",
        "cta": "احجز ملعب",
        "about_title": "نادي متكامل",
        "about_text": "ملاعب بمعايير دولية، إضاءة ممتازة، خدمات VIP لتجربة رياضية لا تُنسى.",
        "primary_grid": "services",
        "accent_emoji": "⚽",
    },
    "library": {
        "hero_title": "المعرفة · بين يديك",
        "hero_subtitle": "روايات، كتب علمية، قرطاسية — كل ما يحتاجه القارئ والطالب",
        "hero_image": "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=1600&q=70",
        "cta": "تصفّح الآن",
        "about_title": "شغفنا بالكتاب",
        "about_text": "آلاف العناوين، توصيات يومية، وخدمة توصيل سريع — المكتبة التي تنتظرها.",
        "primary_grid": "products",
        "accent_emoji": "📚",
    },
    "art_gallery": {
        "hero_title": "فن · يلامس الروح",
        "hero_subtitle": "لوحات أصلية، خط عربي، مقتنيات فريدة من فنانين محترفين",
        "hero_image": "https://images.unsplash.com/photo-1545987796-200677ee1011?w=1600&q=70",
        "cta": "شاهد المعرض",
        "about_title": "مساحة للفن الأصيل",
        "about_text": "نمثّل فنانين محليين وعالميين، ونقدّم أعمالاً أصلية مع شهادة موثّقة.",
        "primary_grid": "products",
        "accent_emoji": "🎨",
    },
    "maintenance": {
        "hero_title": "صيانة بيتك · بدون قلق",
        "hero_subtitle": "كهرباء، سباكة، تكييف — فنيون معتمدون، أسعار شفافة، خدمة سريعة",
        "hero_image": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=1600&q=70",
        "cta": "اطلب فني",
        "about_title": "ثقة وجودة",
        "about_text": "فنيون مختارون بعناية، تأمين على الأعمال، ضمان على الخدمة.",
        "primary_grid": "services",
        "accent_emoji": "🛠️",
    },
    "jewelry": {
        "hero_title": "أناقة · تبقى للأبد",
        "hero_subtitle": "مجوهرات ذهبية وألماس، تصاميم حصرية، جودة عالمية",
        "hero_image": "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=1600&q=70",
        "cta": "تسوّق المجموعة",
        "about_title": "فن المجوهرات",
        "about_text": "قطعة واحدة تغيّر إطلالتك بالكامل. تصاميم مصممة بدقة من يد صاغة محترفين.",
        "primary_grid": "products",
        "accent_emoji": "💍",
    },
    "plumbing": {
        "hero_title": "حلول سباكة · 24/7",
        "hero_subtitle": "تسربات، انسدادات، تركيبات — خدمة طوارئ بسرعة وجودة",
        "hero_image": "https://images.unsplash.com/photo-1606613221062-5c4c2d85ce31?w=1600&q=70",
        "cta": "اطلب فني",
        "about_title": "خبرة في كل حنفية",
        "about_text": "سنوات من الخبرة في كشف وإصلاح مشاكل السباكة بكفاءة وضمان.",
        "primary_grid": "services",
        "accent_emoji": "🔧",
    },
    "electrical": {
        "hero_title": "كهرباء · آمنة وسريعة",
        "hero_subtitle": "تمديدات، إصلاحات، مولدات — فنيون معتمدون بتأمين كامل",
        "hero_image": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1600&q=70",
        "cta": "اطلب خدمة",
        "about_title": "أمان الكهرباء",
        "about_text": "نلتزم بأعلى معايير السلامة في كل عمل كهربائي، مع ضمان على التركيبات.",
        "primary_grid": "services",
        "accent_emoji": "⚡",
    },
    "company": {
        "hero_title": "شركاء · في نجاحك",
        "hero_subtitle": "حلول مؤسسية متكاملة، فريق خبير، نتائج ملموسة",
        "hero_image": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1600&q=70",
        "cta": "تواصل معنا",
        "about_title": "من نحن",
        "about_text": "شركة رائدة في مجالها، تضع عملاءها في المركز وتقدّم حلولاً مبتكرة.",
        "primary_grid": "services",
        "accent_emoji": "🏢",
    },
    "portfolio": {
        "hero_title": "إبداع · يُروى بصرياً",
        "hero_subtitle": "مشاريع مختارة، تجربة بصرية فريدة، هوية تميّز عملك",
        "hero_image": "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=1600&q=70",
        "cta": "شاهد أعمالي",
        "about_title": "عن المصمم",
        "about_text": "7 سنوات من العمل مع علامات محلية وإقليمية على هويات بصرية وتجارب رقمية.",
        "primary_grid": "products",  # as gallery of works
        "accent_emoji": "🎭",
    },
    "saas": {
        "hero_title": "أتمتة · ذكاء · نمو",
        "hero_subtitle": "منصة واحدة لإدارة عملك كاملاً — جرّب مجاناً 14 يوماً",
        "hero_image": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=1600&q=70",
        "cta": "ابدأ مجاناً",
        "about_title": "لماذا نحن",
        "about_text": "بنينا المنصة الأكثر سهولة وقوة لإدارة الأعمال الصغيرة والمتوسطة.",
        "primary_grid": "services",
        "accent_emoji": "💻",
    },
    "gym": {
        "hero_title": "قوة · التزام · تحوّل",
        "hero_subtitle": "معدات حديثة، مدربون محترفون، حصص جماعية — عضويتك تفتح عالماً كاملاً",
        "hero_image": "https://images.unsplash.com/photo-1534258936925-c58bed479fcb?w=1600&q=70",
        "cta": "اشترك الآن",
        "about_title": "نادي متكامل",
        "about_text": "أكثر من مجرد صالة — مجتمع يدفعك للأفضل كل يوم.",
        "primary_grid": "services",
        "accent_emoji": "🏋️",
    },
    "academy": {
        "hero_title": "تعلّم · تطوّر · تميّز",
        "hero_subtitle": "كورسات احترافية من خبراء، شهادات معتمدة، وصول مدى الحياة",
        "hero_image": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=1600&q=70",
        "cta": "سجّل الآن",
        "about_title": "منصتنا التعليمية",
        "about_text": "آلاف الطلاب، مدرّبون خبراء، ومنهج عملي يضمن تطبيقاً فعلياً لكل مهارة.",
        "primary_grid": "services",  # courses displayed as service cards for now
        "accent_emoji": "🎓",
    },
    "blank": {
        "hero_title": "عنوان الصفحة",
        "hero_subtitle": "وصف قصير يلخص عملك في سطر أو اثنين",
        "hero_image": "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1600&q=70",
        "cta": "ابدأ الآن",
        "about_title": "عن الشركة",
        "about_text": "نبذة تعريفية يمكنك تعديلها لاحقاً من لوحة التحكم.",
        "primary_grid": "services",
        "accent_emoji": "✨",
    },
    "realestate": {
        "hero_title": "استثمر في عقارات دبي مع باتريوت",
        "hero_subtitle": "نساعدك في إيجاد عقارك المثالي — شقق، فلل، مشاريع حصرية، ومناطق راقية",
        "hero_image": "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=1600&q=70",
        "cta": "اطلب استشارة",
        "about_title": "متخصصو العقارات",
        "about_text": "خبراء عقاريون يقدمون لك المشورة المتخصصة لتحقيق أفضل عائد استثماري.",
        "primary_grid": "products",  # listings as products
        "accent_emoji": "🏛️",
    },
    "stocks": {
        "hero_title": "استثمار ذكي · بأمان",
        "hero_subtitle": "محاكاة تداول احترافية، تحليلات لحظية، وتوصيات من نخبة المتخصصين",
        "hero_image": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1600&q=70",
        "cta": "ابدأ الآن",
        "about_title": "منصتنا الاستثمارية",
        "about_text": "نقدم لك أدوات احترافية لتحليل الأسواق واتخاذ قرارات مدروسة.",
        "primary_grid": "services",
        "accent_emoji": "📈",
    },
    "medical": {
        "hero_title": "صحتك · أولويتنا",
        "hero_subtitle": "أطباء متخصصون، تقنيات حديثة، ورعاية شاملة من القلب",
        "hero_image": "https://images.unsplash.com/photo-1538108149393-fbbd81895907?w=1600&q=70",
        "cta": "احجز موعد",
        "about_title": "عن العيادة",
        "about_text": "خبرة تمتد لسنوات في تقديم رعاية طبية متميزة بأحدث المعايير.",
        "primary_grid": "services",
        "accent_emoji": "🏥",
    },
    "ecommerce": {
        "hero_title": "تسوّق · بسهولة وأمان",
        "hero_subtitle": "آلاف المنتجات، شحن سريع، أسعار تنافسية، وضمان رضى العميل",
        "hero_image": "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=1600&q=70",
        "cta": "تسوّق الآن",
        "about_title": "تجربة تسوّق فريدة",
        "about_text": "نختار لك بعناية أفضل المنتجات من علامات موثوقة بأسعار لا تُقاوم.",
        "primary_grid": "products",
        "accent_emoji": "🛒",
    },
    "cosmetics": {
        "hero_title": "جمالكِ · فنّ يُكتشف",
        "hero_subtitle": "مكياج فاخر، عطور حصرية، وعناية كاملة من أرقى العلامات العالمية",
        "hero_image": "https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=1600&q=70",
        "cta": "تسوّقي الآن",
        "about_title": "علاماتنا الموثوقة",
        "about_text": "نتعامل مع أفخر العلامات العالمية ونوفّر منتجات أصلية 100% بضمان كامل.",
        "primary_grid": "products",
        "accent_emoji": "💄",
    },
    "automotive": {
        "hero_title": "اقتني سيارة أحلامك",
        "hero_subtitle": "معرض سيارات فاخر، خيارات تمويل، ضمان شامل، وخدمة ما بعد البيع",
        "hero_image": "https://images.unsplash.com/photo-1494976388531-d1058494cdd8?w=1600&q=70",
        "cta": "اطلب اختبار قيادة",
        "about_title": "وكيلك المعتمد",
        "about_text": "أكثر من 500 سيارة جاهزة للتسليم — جديدة ومستعملة، مع خيارات تقسيط مرنة.",
        "primary_grid": "products",
        "accent_emoji": "🏎️",
    },
}


# ──────────────────────────────────────────────────────────────────────
# Placeholder content builders (return section data dicts)
# All builders accept category_id so images come from the curated library
# ──────────────────────────────────────────────────────────────────────
def _cat_imgs(category_id: str, count: int = 8) -> List[str]:
    """Return curated images for a category (or fallback)."""
    try:
        from .category_images import get_category_images
        lib = get_category_images(category_id)
        return (lib * ((count // len(lib)) + 1))[:count]  # tile if needed
    except Exception:
        return ["https://images.unsplash.com/photo-1557804506-669a67965ba0?w=800&q=70"] * count


def _menu_sample(cfg: Dict[str, Any], category_id: str = "blank") -> Dict[str, Any]:
    emoji = cfg.get("accent_emoji", "🍽️")
    imgs = _cat_imgs(category_id, 5)
    return {"title": f"{emoji} قائمتنا المختارة", "categories": [
        {"name": "الأكثر طلباً", "items": [
            {"name": "الطبق الخاص", "price": "95", "desc": "وصفة البيت — لا تفوّتها", "image": imgs[0]},
            {"name": "الطبق المميز", "price": "75", "desc": "بمذاق لا يقاوم", "image": imgs[1]},
            {"name": "الطبق الكلاسيكي", "price": "55", "desc": "تقليدي وأصيل", "image": imgs[2]},
        ]},
        {"name": "المشروبات", "items": [
            {"name": "مشروب البيت", "price": "25", "desc": "تركيبة خاصة", "image": imgs[3]},
            {"name": "قهوة مختصة", "price": "20", "image": imgs[4]},
        ]},
    ]}


def _services_sample(cfg: Dict[str, Any], category_id: str = "blank") -> Dict[str, Any]:
    emoji = cfg.get("accent_emoji", "✂️")
    imgs = _cat_imgs(category_id, 4)
    return {"title": f"{emoji} خدماتنا", "items": [
        {"name": "الخدمة الأساسية", "desc": "وصف الخدمة الأولى", "icon": "⭐", "image": imgs[0]},
        {"name": "الخدمة المميزة", "desc": "وصف الخدمة الثانية", "icon": "✨", "image": imgs[1]},
        {"name": "الخدمة الفاخرة", "desc": "وصف الخدمة الثالثة", "icon": "💎", "image": imgs[2]},
        {"name": "خدمة VIP", "desc": "تجربة استثنائية كاملة", "icon": "👑", "image": imgs[3]},
    ]}


def _products_sample(cfg: Dict[str, Any], large: bool = False, category_id: str = "blank") -> Dict[str, Any]:
    emoji = cfg.get("accent_emoji", "🛒")
    count = 8 if large else 4
    imgs = _cat_imgs(category_id, count)
    items = [{"name": f"منتج {i+1}", "price": str(50 + i * 20), "image": imgs[i], "stock": 15 - i} for i in range(count)]
    return {"title": f"{emoji} منتجاتنا", "items": items}


def _default_gallery(count: int = 6, category_id: str = "blank") -> Dict[str, Any]:
    return {"title": "معرض الصور", "images": _cat_imgs(category_id, count)}


def _testimonials(count: int = 3) -> Dict[str, Any]:
    items = [
        {"name": "سارة أحمد", "text": "تجربة استثنائية من الألف إلى الياء، أنصح الجميع بها.", "rating": 5},
        {"name": "محمد الشهري", "text": "الجودة عالية والخدمة سريعة. عودة مؤكدة!", "rating": 5},
        {"name": "لمى الزهراني", "text": "تعاملوا معي بكل احترافية وأخرجوا أفضل نتيجة ممكنة.", "rating": 5},
        {"name": "خالد العلي", "text": "سعر مناسب وجودة مميزة. شكراً لكم.", "rating": 4},
        {"name": "فاطمة الدوسري", "text": "أحسن مكان جربته — سرعة ونظافة واهتمام.", "rating": 5},
    ]
    return {"title": "آراء عملائنا", "items": items[:count]}


def _pricing() -> Dict[str, Any]:
    return {"title": "خطط الأسعار", "plans": [
        {"name": "الأساسية", "price": "99", "period": "شهرياً", "features": ["ميزة 1", "ميزة 2", "دعم بريد"], "cta": "اشترك"},
        {"name": "المميزة", "price": "199", "period": "شهرياً", "featured": True,
         "features": ["كل ميزات الأساسية", "أولوية الدعم", "ميزات متقدمة", "تقارير شهرية"], "cta": "الأكثر شعبية"},
        {"name": "الشركات", "price": "499", "period": "شهرياً",
         "features": ["كل ميزات المميزة", "مدير حساب مخصص", "تكامل API", "SLA 99.9%"], "cta": "تواصل معنا"},
    ]}


def _team(count: int = 3) -> Dict[str, Any]:
    people = [
        {"name": "أحمد العلي", "role": "المدير التنفيذي", "image": "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=400&q=70"},
        {"name": "سارة المطيري", "role": "مديرة العمليات", "image": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=400&q=70"},
        {"name": "فهد الزهراني", "role": "رئيس التصميم", "image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&q=70"},
        {"name": "نورة القحطاني", "role": "مديرة التسويق", "image": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=400&q=70"},
        {"name": "ماجد الشمري", "role": "مدير التطوير", "image": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&q=70"},
        {"name": "ريم الحربي", "role": "مديرة الحسابات", "image": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&q=70"},
    ]
    return {"title": "فريقنا", "members": people[:count]}


def _stats(big: bool = False) -> Dict[str, Any]:
    return {"title": "أرقام تتحدث عن نفسها", "items": [
        {"value": "500+", "label": "عميل سعيد", "icon": "😊"},
        {"value": "15", "label": "سنة خبرة", "icon": "🏆"},
        {"value": "98%", "label": "رضا العملاء", "icon": "⭐"},
        {"value": "24/7", "label": "دعم متواصل", "icon": "⏰"},
    ]}


def _faq(count: int = 6) -> Dict[str, Any]:
    items = [
        {"q": "كم يستغرق تقديم الخدمة؟", "a": "عادة من ساعة إلى 3 ساعات حسب طبيعة الطلب."},
        {"q": "هل تقدمون ضماناً؟", "a": "نعم، نضمن جودة خدماتنا ونعيد الكرة مجاناً إن لم ترضَ."},
        {"q": "كيف أحجز موعداً؟", "a": "عبر الموقع مباشرة، أو الاتصال، أو الواتساب."},
        {"q": "ما وسائل الدفع المتاحة؟", "a": "بطاقات مدى، فيزا، ماستركارد، Apple Pay، STC Pay، والدفع عند الاستلام."},
        {"q": "هل الخدمة متوفرة في جميع المدن؟", "a": "حالياً الرياض وجدة والدمام، ونخطط للتوسع."},
        {"q": "هل يوجد خصم للكميات الكبيرة؟", "a": "نعم، خصومات خاصة تبدأ من 10% للطلبات الكبيرة."},
        {"q": "كيف يمكنني إلغاء الطلب؟", "a": "من خلال حسابك قبل 24 ساعة من الموعد."},
        {"q": "ما سياسة الاسترجاع؟", "a": "خلال 14 يوماً من الاستلام، بشرط عدم الاستخدام."},
        {"q": "هل تقدمون فواتير ضريبية؟", "a": "نعم، فواتير ضريبية معتمدة من هيئة الزكاة والدخل."},
        {"q": "كيف أتواصل مع خدمة العملاء؟", "a": "واتساب 24/7 أو البريد الإلكتروني."},
    ]
    return {"title": "الأسئلة الشائعة", "items": items[:count]}


def _timeline(count: int = 4) -> Dict[str, Any]:
    items = [
        {"year": "2015", "title": "البداية", "text": "انطلقنا بفكرة بسيطة وفريق صغير شغوف."},
        {"year": "2018", "title": "التوسّع", "text": "افتتاح فرعنا الثاني وتوسيع قاعدة العملاء."},
        {"year": "2021", "title": "التميّز", "text": "حصلنا على جائزة أفضل علامة في القطاع."},
        {"year": "2023", "title": "الابتكار", "text": "أطلقنا خدمات رقمية متقدمة ومنصات جديدة."},
        {"year": "2025", "title": "اليوم", "text": "آلاف العملاء الراضين ونموّ مستمر."},
    ]
    return {"title": "قصتنا عبر السنوات", "items": items[:count]}


def _process_steps(count: int = 4) -> Dict[str, Any]:
    items = [
        {"n": "1", "title": "احجز الموعد", "text": "اختر الوقت المناسب لك من خلال الموقع"},
        {"n": "2", "title": "اعتمد التفاصيل", "text": "نتواصل معك لتأكيد التفاصيل الدقيقة"},
        {"n": "3", "title": "نبدأ العمل", "text": "فريقنا يبدأ الخدمة بدقة واحتراف"},
        {"n": "4", "title": "استمتع بالنتيجة", "text": "تسلّم العمل النهائي مع ضمان الجودة"},
        {"n": "5", "title": "المتابعة", "text": "نتابع معك لضمان رضاك الكامل"},
    ]
    return {"title": "كيف نعمل", "items": items[:count]}


def _reservation_form() -> Dict[str, Any]:
    return {"title": "احجز موعدك", "subtitle": "أدخل بياناتك ونتواصل معك فوراً",
            "fields": ["الاسم", "رقم الجوال", "التاريخ المفضّل", "ملاحظات"]}


def _map_big() -> Dict[str, Any]:
    return {"title": "موقعنا", "lat": 24.7136, "lng": 46.6753, "address": "الرياض — حي العليا — شارع الأمير محمد"}


def _newsletter_card() -> Dict[str, Any]:
    return {"title": "اشترك في نشرتنا",
            "subtitle": "كن أول من يعلم بالعروض والخدمات الجديدة — هدية ترحيبية بقيمة 50 ر.س",
            "cta": "اشترك الآن"}


def _categories_6() -> Dict[str, Any]:
    return {"title": "تصفّح حسب الفئة", "items": [
        {"name": "الأكثر طلباً", "icon": "🔥", "count": 24},
        {"name": "الجديد", "icon": "✨", "count": 12},
        {"name": "عروض", "icon": "💰", "count": 18},
        {"name": "فاخر", "icon": "💎", "count": 8},
        {"name": "اقتصادي", "icon": "💵", "count": 32},
        {"name": "الكل", "icon": "📦", "count": 120},
    ]}


def _cta(big: bool = False, minimal: bool = False) -> Dict[str, Any]:
    if minimal:
        return {"title": "جاهز للبداية؟", "subtitle": "", "cta_text": "ابدأ الآن"}
    if big:
        return {"title": "جاهز لتبدأ؟ هذه أفضل لحظة", "subtitle": "انضم إلى آلاف العملاء الذين اختارونا",
                "cta_text": "ابدأ الآن مجاناً"}
    return {"title": "نحن بانتظارك", "subtitle": "تواصل معنا اليوم واحصل على استشارة مجانية",
            "cta_text": "تواصل معنا"}


def _about(variant: str = "short") -> Dict[str, Any]:
    if variant == "detailed":
        return {"title": "من نحن", "text": (
            "نؤمن بأن التميّز ليس صدفة، بل نتيجة لاهتمام مستمر بالتفاصيل الصغيرة. "
            "منذ تأسيسنا، والتزمنا بتقديم خدمة تفوق توقعات عملائنا. فريقنا يضم "
            "خبراء في مجالاتهم، يعملون بشغف وإخلاص ليصلوا بك إلى أفضل نتيجة ممكنة. "
            "اختيارك لنا ليس مجرد خدمة — بل شراكة طويلة الأمد نبنيها بالثقة."
        )}
    if variant == "elegant":
        return {"title": "نبذة", "text": "حيث يلتقي الشغف بالاحتراف — نصنع تجارب استثنائية بكل تفاصيلها."}
    return {"title": "نبذة عنا", "text": "نقدّم خدمات متميزة بفريق محترف وأسعار تنافسية منذ أكثر من 10 سنوات."}


def _contact(variant: str = "card") -> Dict[str, Any]:
    base = {
        "title": "تواصل معنا",
        "phone": "+966 11 123 4567",
        "email": "hello@example.com",
        "address": "الرياض — المملكة العربية السعودية",
        "hours": "الأحد - الخميس · 9 ص - 10 م",
    }
    if variant == "simple":
        return {"title": "تواصل", "phone": base["phone"], "email": base["email"]}
    return base


def _features(variant: str = "3") -> Dict[str, Any]:
    items = [
        {"title": "جودة مضمونة", "text": "معايير عالية في كل التفاصيل", "icon": "✓"},
        {"title": "سرعة في التنفيذ", "text": "التزام تام بالمواعيد", "icon": "⚡"},
        {"title": "دعم متواصل", "text": "فريق متاح لمساعدتك", "icon": "💬"},
        {"title": "أسعار شفافة", "text": "لا رسوم خفية", "icon": "💰"},
    ]
    if variant == "3":
        return {"title": "لماذا نحن؟", "items": items[:3]}
    if variant == "alt_3":
        return {"title": "مميزاتنا", "items": items[:3], "layout": "alt"}
    if variant == "cards_4":
        return {"title": "ما يميّزنا", "items": items}
    return {"title": "مميزاتنا", "items": items[:3]}


def _quote_big() -> Dict[str, Any]:
    return {"title": "",
            "text": "التميّز ليس مهارة، بل موقف. ومع كل تجربة، يزداد إيماننا بهذا.",
            "author": "المؤسس والمدير التنفيذي"}


# ──────────────────────────────────────────────────────────────────────
# Main resolver — builds concrete section data for a placeholder
# ──────────────────────────────────────────────────────────────────────
def resolve_placeholder(placeholder_id: str, category_id: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve a section placeholder to concrete data for a category."""
    pid = placeholder_id

    # Substitute {primary_content*} with the category's primary_grid content
    if pid == "{primary_content}" or pid == "{primary_content_large}":
        primary = cfg.get("primary_grid", "services")
        large = pid == "{primary_content_large}"
        if primary == "menu":
            return _menu_sample(cfg, category_id)
        if primary == "products":
            return _products_sample(cfg, large=large, category_id=category_id)
        return _services_sample(cfg, category_id)

    # Static placeholders
    MAP = {
        "hero_classic": lambda: {"title": cfg["hero_title"], "subtitle": cfg["hero_subtitle"],
                                 "cta_text": cfg["cta"], "image": cfg["hero_image"], "layout": "centered"},
        "hero_editorial": lambda: {"title": cfg["hero_title"], "subtitle": cfg["hero_subtitle"],
                                   "cta_text": cfg["cta"], "image": cfg["hero_image"], "layout": "magazine"},
        "hero_split": lambda: {"title": cfg["hero_title"], "subtitle": cfg["hero_subtitle"],
                               "cta_text": cfg["cta"], "image": cfg["hero_image"], "layout": "split"},
        "hero_story": lambda: {"title": cfg["hero_title"], "subtitle": cfg["hero_subtitle"],
                               "cta_text": cfg["cta"], "image": cfg["hero_image"], "layout": "story"},
        "hero_full_image": lambda: {"title": cfg["hero_title"], "subtitle": cfg["hero_subtitle"],
                                    "cta_text": cfg["cta"], "image": cfg["hero_image"], "layout": "full"},
        "hero_portrait": lambda: {"title": cfg["hero_title"], "subtitle": cfg["hero_subtitle"],
                                  "cta_text": cfg["cta"], "image": cfg["hero_image"], "layout": "portrait"},
        "hero_banner_bold": lambda: {"title": cfg["hero_title"], "subtitle": cfg["hero_subtitle"],
                                     "cta_text": cfg["cta"], "image": cfg["hero_image"], "layout": "full"},
        "hero_boxed": lambda: {"title": cfg["hero_title"], "subtitle": cfg["hero_subtitle"],
                               "cta_text": cfg["cta"], "image": cfg["hero_image"], "layout": "boxed"},
        "hero_with_form": lambda: {"title": cfg["hero_title"], "subtitle": cfg["hero_subtitle"],
                                   "cta_text": cfg["cta"], "image": cfg["hero_image"], "layout": "form"},
        # 🆕 5 premium template hero placeholders — use existing layouts, override visually via CSS
        "hero_promo_grid": lambda: {"title": cfg["hero_title"], "subtitle": cfg["hero_subtitle"],
                                    "cta_text": cfg["cta"], "image": cfg["hero_image"], "layout": "split"},
        "hero_diagonal": lambda: {"title": cfg["hero_title"], "subtitle": cfg["hero_subtitle"],
                                  "cta_text": cfg["cta"], "image": cfg["hero_image"], "layout": "split"},
        "hero_organic": lambda: {"title": cfg["hero_title"], "subtitle": cfg["hero_subtitle"],
                                 "cta_text": cfg["cta"], "image": cfg["hero_image"], "layout": "split"},
        "hero_glitch": lambda: {"title": cfg["hero_title"], "subtitle": cfg["hero_subtitle"],
                                "cta_text": cfg["cta"], "image": cfg["hero_image"], "layout": "portrait"},

        "about_short": lambda: _about("short") | {"title": cfg.get("about_title", "نبذة"),
                                                  "text": cfg.get("about_text", "")},
        "about_detailed": lambda: _about("detailed") | {"title": cfg.get("about_title", "من نحن")},
        "about_elegant": lambda: _about("elegant"),

        "features_3": lambda: _features("3"),
        "features_alt_3": lambda: _features("alt_3"),
        "features_cards_4": lambda: _features("cards_4"),

        "gallery_6": lambda: _default_gallery(6, category_id),
        "gallery_8": lambda: _default_gallery(8, category_id),

        "testimonials_3": lambda: _testimonials(3),
        "testimonials_5": lambda: _testimonials(5),

        "pricing_3": lambda: _pricing(),

        "team_3": lambda: _team(3),
        "team_4": lambda: _team(4),
        "team_6": lambda: _team(6),

        "stats_4": lambda: _stats(),
        "stats_4_big": lambda: _stats(big=True),

        "faq_6": lambda: _faq(6),
        "faq_10": lambda: _faq(10),

        "timeline_4": lambda: _timeline(4),
        "timeline_5": lambda: _timeline(5),

        "steps_4": lambda: _process_steps(4),
        "steps_5": lambda: _process_steps(5),

        "reservation_form": _reservation_form,
        "map_big": _map_big,
        "newsletter_card": _newsletter_card,
        "categories_6": _categories_6,

        "cta_band": lambda: _cta(),
        "cta_band_big": lambda: _cta(big=True),
        "cta_minimal": lambda: _cta(minimal=True),

        "contact_card": lambda: _contact("card"),
        "contact_full": lambda: _contact("card"),
        "contact_simple": lambda: _contact("simple"),

        "quote_big": _quote_big,

        "products_dense": lambda: _products_sample(cfg, large=True),
    }

    fn = MAP.get(pid)
    if fn:
        return fn()
    # Unknown placeholder — return a minimal shell
    return {"title": cfg.get("about_title", pid), "text": ""}


# ──────────────────────────────────────────────────────────────────────
# Section-type resolution: {primary_grid} → menu/products/services
# ──────────────────────────────────────────────────────────────────────
def resolve_section_type(section_type: str, cfg: Dict[str, Any]) -> str:
    if section_type == "{primary_grid}":
        return cfg.get("primary_grid", "services")
    return section_type


def get_category_config(category_id: str) -> Dict[str, Any]:
    return CATEGORY_CONFIG.get(category_id, CATEGORY_CONFIG["blank"])
