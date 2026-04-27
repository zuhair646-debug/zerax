"""
Template Archetypes — 20 STRUCTURALLY DISTINCT templates.

Each archetype defines a COMPLETELY DIFFERENT page structure (different hero,
different section mix, different arrangement, different content density).
Archetypes are color-agnostic — they use a NEUTRAL DEFAULT theme.
Colors are chosen in a separate wizard step AFTER the user picks an archetype.

Combined with the 20 categories in catalog.py, this produces
20 archetypes × 20 categories = 400 distinct template instances
(each genuinely different — not just color variants of each other).

Content placeholders (e.g., {services}, {products}, {menu}) are filled
per-category by category_content.py at resolve time.
"""
from __future__ import annotations

from typing import Any, Dict, List


# Default neutral theme — applied to ALL archetypes.
# Colors are picked AFTER template selection in wizard step `colors`.
NEUTRAL_THEME = {
    "primary": "#FFD700",     # gold
    "secondary": "#0b0f1f",
    "accent": "#D97706",
    "bg": "#0b0f1f",
    "text": "#ffffff",
    "font": "Tajawal",
    "radius": "medium",
}


# Each archetype is a SPEC: a list of (section_type, style_variant?, placeholder_id?)
# The resolver fills placeholders with category-specific content and assigns order.
ARCHETYPES: List[Dict[str, Any]] = [
    {
        "id": "classic_stack",
        "name_ar": "كلاسيكي متراكم",
        "description": "تدفق كلاسيكي من الأعلى للأسفل — hero مركزي، عن المتجر، خدمات/منتجات، آراء، تواصل. مناسب لأي فئة.",
        "hero_layout": "centered",
        "density": "comfortable",
        "sections": [
            ("hero", None, "hero_classic"),
            ("about", None, "about_short"),
            ("features", None, "features_3"),
            ("{primary_grid}", "grid", "{primary_content}"),
            ("testimonials", "grid", "testimonials_3"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "magazine",
        "name_ar": "أسلوب المجلة",
        "description": "تخطيط تحريري — hero مجلة، عناوين كبيرة، أعمدة نص، معرض masonry.",
        "hero_layout": "magazine",
        "density": "dense",
        "sections": [
            ("hero", None, "hero_editorial"),
            ("story_timeline", None, "timeline_4"),
            ("{primary_grid}", "grid", "{primary_content}"),
            ("gallery", "masonry", "gallery_8"),
            ("quote", None, "quote_big"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "split_screen",
        "name_ar": "شاشة مقسّمة",
        "description": "كل قسم نصف-نص نصف-صورة مع تبديل بين يمين ويسار. ديناميكي ومتوازن.",
        "hero_layout": "split",
        "density": "comfortable",
        "sections": [
            ("hero", None, "hero_split"),
            ("features", None, "features_alt_3"),
            ("{primary_grid}", "grid", "{primary_content}"),
            ("testimonials", "carousel", "testimonials_3"),
            ("cta", None, "cta_band"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "longform_story",
        "name_ar": "قصة طويلة",
        "description": "سردية — جدول زمني، خطوات، اقتباسات كبيرة بين الأقسام. للعلامات ذات القصة.",
        "hero_layout": "story",
        "density": "spacious",
        "sections": [
            ("hero", None, "hero_story"),
            ("story_timeline", None, "timeline_5"),
            ("process_steps", None, "steps_4"),
            ("quote", None, "quote_big"),
            ("testimonials", "quote-big", "testimonials_3"),
            ("cta", None, "cta_band"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "gallery_first",
        "name_ar": "المعرض أولاً",
        "description": "شريط معرض كبير فوق كل شيء. بصري قوي — للمطاعم، الصالونات، المعارض.",
        "hero_layout": "full",
        "density": "visual",
        "sections": [
            ("hero", None, "hero_full_image"),
            ("gallery", "strip", "gallery_8"),
            ("about", None, "about_short"),
            ("{primary_grid}", "grid", "{primary_content}"),
            ("testimonials", "grid", "testimonials_3"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "minimal_portrait",
        "name_ar": "عمودي بسيط",
        "description": "بطاقة عمودية، 3 أقسام فقط، مساحات بيضاء كثيرة. للعلامات الفاخرة البسيطة.",
        "hero_layout": "portrait",
        "density": "minimal",
        "sections": [
            ("hero", None, "hero_portrait"),
            ("about", None, "about_elegant"),
            ("cta", None, "cta_minimal"),
            ("contact", None, "contact_simple"),
        ],
    },
    {
        "id": "bold_banner",
        "name_ar": "بانر جريء",
        "description": "بانر ضخم، شريط إحصائيات، تسعير وCTA. لعرض قوي مبيعي.",
        "hero_layout": "full",
        "density": "bold",
        "sections": [
            ("hero", None, "hero_banner_bold"),
            ("stats", None, "stats_4"),
            ("pricing", "cards", "pricing_3"),
            ("testimonials", "grid", "testimonials_3"),
            ("cta", None, "cta_band_big"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "card_stack",
        "name_ar": "بطاقات متراصة",
        "description": "كل قسم بطاقة مستقلة بظلال وحواف واضحة. منظم جداً.",
        "hero_layout": "boxed",
        "density": "carded",
        "sections": [
            ("hero", None, "hero_boxed"),
            ("features", None, "features_cards_4"),
            ("{primary_grid}", "grid", "{primary_content}"),
            ("pricing", "cards", "pricing_3"),
            ("testimonials", "grid", "testimonials_3"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "asymmetric",
        "name_ar": "غير متماثل",
        "description": "شبكات منزاحة، اقتباسات وسط، ترتيب عكسي. للمبدعين.",
        "hero_layout": "magazine",
        "density": "creative",
        "sections": [
            ("hero", None, "hero_editorial"),
            ("about", None, "about_elegant"),
            ("features", None, "features_alt_3"),
            ("quote", None, "quote_big"),
            ("{primary_grid}", "grid", "{primary_content}"),
            ("gallery", "masonry", "gallery_6"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "services_showcase",
        "name_ar": "عرض الخدمات",
        "description": "الخدمات/المنتجات تشغل أغلب الصفحة. خطوات + فريق + تواصل.",
        "hero_layout": "centered",
        "density": "focused",
        "sections": [
            ("hero", None, "hero_classic"),
            ("{primary_grid}", "grid", "{primary_content_large}"),
            ("process_steps", None, "steps_4"),
            ("team", "grid", "team_3"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "booking_first",
        "name_ar": "الحجز أولاً",
        "description": "نموذج الحجز فوق الصفحة مباشرة — للصالون، الطبي، الجيم، غسيل السيارات.",
        "hero_layout": "form",
        "density": "action",
        "sections": [
            ("hero", None, "hero_with_form"),
            ("{primary_grid}", "grid", "{primary_content}"),
            ("reservation", None, "reservation_form"),
            ("about", None, "about_short"),
            ("testimonials", "carousel", "testimonials_3"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "process_steps",
        "name_ar": "الخطوات",
        "description": "كيف نعمل؟ 4 خطوات مرقمة ضخمة تشرح الرحلة.",
        "hero_layout": "centered",
        "density": "educational",
        "sections": [
            ("hero", None, "hero_classic"),
            ("process_steps", None, "steps_5"),
            ("features", None, "features_3"),
            ("cta", None, "cta_band"),
            ("faq", None, "faq_6"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "team_centric",
        "name_ar": "الفريق في القلب",
        "description": "الفريق بصور دائرية كبيرة في المقدمة. للعيادات، الصالونات، الأكاديميات.",
        "hero_layout": "centered",
        "density": "human",
        "sections": [
            ("hero", None, "hero_classic"),
            ("team", "circles", "team_6"),
            ("about", None, "about_short"),
            ("{primary_grid}", "grid", "{primary_content}"),
            ("testimonials", "grid", "testimonials_3"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "reviews_driven",
        "name_ar": "تقودها الآراء",
        "description": "الآراء الضخمة أعلى الصفحة — إثبات اجتماعي قوي.",
        "hero_layout": "centered",
        "density": "trust",
        "sections": [
            ("hero", None, "hero_classic"),
            ("testimonials", "quote-big", "testimonials_5"),
            ("stats", None, "stats_4"),
            ("{primary_grid}", "grid", "{primary_content}"),
            ("cta", None, "cta_band"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "pricing_table",
        "name_ar": "جدول الأسعار",
        "description": "جدول مقارنة SaaS-style. خطط جنباً إلى جنب بمميزات تفصيلية.",
        "hero_layout": "boxed",
        "density": "comparative",
        "sections": [
            ("hero", None, "hero_boxed"),
            ("pricing", "table", "pricing_3"),
            ("features", None, "features_3"),
            ("faq", None, "faq_6"),
            ("testimonials", "grid", "testimonials_3"),
            ("cta", None, "cta_band"),
        ],
    },
    {
        "id": "faq_heavy",
        "name_ar": "معلومات وأسئلة",
        "description": "أسئلة شائعة مطوّلة — للخدمات المعقدة أو الطبية أو القانونية.",
        "hero_layout": "centered",
        "density": "informational",
        "sections": [
            ("hero", None, "hero_classic"),
            ("about", None, "about_detailed"),
            ("{primary_grid}", "grid", "{primary_content}"),
            ("faq", None, "faq_10"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "stats_numbers",
        "name_ar": "الأرقام والإنجازات",
        "description": "4 إحصائيات ضخمة، إنجازات، فريق. للمؤسسات والشركات.",
        "hero_layout": "split",
        "density": "corporate",
        "sections": [
            ("hero", None, "hero_split"),
            ("stats", None, "stats_4_big"),
            ("about", None, "about_detailed"),
            ("features", None, "features_cards_4"),
            ("team", "grid", "team_4"),
            ("cta", None, "cta_band"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "location_map",
        "name_ar": "الموقع والخريطة",
        "description": "خريطة كبيرة + بطاقة تواصل + ساعات العمل. للمواقع الفيزيائية.",
        "hero_layout": "centered",
        "density": "local",
        "sections": [
            ("hero", None, "hero_classic"),
            ("about", None, "about_short"),
            ("map", None, "map_big"),
            ("contact", None, "contact_full"),
            ("gallery", "grid", "gallery_6"),
        ],
    },
    {
        "id": "newsletter_first",
        "name_ar": "النشرة البريدية",
        "description": "التقاط leads مبكر — نشرة، قيمة مقترحة، مقتطف عن الشركة.",
        "hero_layout": "centered",
        "density": "lead",
        "sections": [
            ("hero", None, "hero_classic"),
            ("features", None, "features_3"),
            ("newsletter_section", None, "newsletter_card"),
            ("about", None, "about_short"),
            ("cta", None, "cta_band"),
            ("contact", None, "contact_simple"),
        ],
    },
    {
        "id": "product_dense",
        "name_ar": "منتجات كثيفة",
        "description": "شبكة منتجات ضخمة مع فلاتر — لـPinterest، المتاجر، المكتبات، المجوهرات.",
        "hero_layout": "full",
        "density": "catalog",
        "sections": [
            ("hero", None, "hero_full_image"),
            ("product_grid_filters", None, "products_dense"),
            ("categories_grid", None, "categories_6"),
            ("testimonials", "carousel", "testimonials_3"),
            ("contact", None, "contact_card"),
        ],
    },
    # ═══════════════════════════════════════════════════════════════
    # 🆕 Premium reference templates (based on user-supplied designs)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "beauty_megamart",
        "name_ar": "متجر الجمال الفاخر",
        "description": "متجر بنفسجي/وردي بصدارة 3 أعمدة + دوائر فئات + شريط خدمات (مستوحى من Original Hubs).",
        "hero_layout": "promo_grid",
        "density": "rich",
        "sections": [
            ("hero", None, "hero_promo_grid"),
            ("team", "circles", "team_6"),  # rendered as category circles via CSS
            ("features", None, "features_cards_4"),  # services band
            ("products", "grid", "{primary_content_large}"),
            ("testimonials", "carousel", "testimonials_3"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "realestate_luxury_dark",
        "name_ar": "عقارات فاخرة كحلية",
        "description": "أسود فاخر + نحاسي + نموذج بحث عقارات على Hero — مستوحى من Patriot Dubai.",
        "hero_layout": "form_overlay",
        "density": "luxury",
        "sections": [
            ("hero", None, "hero_with_form"),
            ("gallery", "grid", "gallery_8"),  # Lifestyle gallery
            ("team", "rows", "team_3"),  # Real Estate Specialists
            ("features", None, "features_cards_4"),  # Exclusive Projects
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "editorial_diagonal",
        "name_ar": "مجلة قطرية",
        "description": "تخطيط قطري حاد — صور مقطوعة بزوايا قطرية، أرقام أقسام كبيرة، خط Serif فاخر.",
        "hero_layout": "diagonal",
        "density": "editorial",
        "sections": [
            ("hero", None, "hero_diagonal"),
            ("about", None, "about_short"),
            ("{primary_grid}", "grid", "{primary_content}"),
            ("gallery", "masonry", "gallery_6"),
            ("quote", None, "quote_big"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "organic_blobs",
        "name_ar": "عضوي ترابي",
        "description": "أشكال عضوية انسيابية — صور بحدود غير منتظمة، ألوان طبيعية ترابية، روح يدوية.",
        "hero_layout": "organic",
        "density": "warm",
        "sections": [
            ("hero", None, "hero_organic"),
            ("about", None, "about_elegant"),
            ("{primary_grid}", "grid", "{primary_content}"),
            ("testimonials", "grid", "testimonials_3"),
            ("gallery", "grid", "gallery_6"),
            ("contact", None, "contact_card"),
        ],
    },
    {
        "id": "cyber_glitch",
        "name_ar": "سايبر نيون",
        "description": "مستقبلي نيون — خلفيات سوداء، تأثيرات glitch، خطوط مونوسبيس، قطع زوايا hexagonal.",
        "hero_layout": "glitch",
        "density": "futuristic",
        "sections": [
            ("hero", None, "hero_glitch"),
            ("stats", None, "stats_4"),
            ("{primary_grid}", "grid", "{primary_content}"),
            ("features", None, "features_cards_4"),
            ("cta", None, "cta_band"),
            ("contact", None, "contact_card"),
        ],
    },
]


def list_archetypes() -> List[Dict[str, Any]]:
    """Safe public list for the archetype picker."""
    return [{
        "id": a["id"],
        "name_ar": a["name_ar"],
        "description": a["description"],
        "hero_layout": a["hero_layout"],
        "density": a["density"],
        "sections_count": len(a["sections"]),
    } for a in ARCHETYPES]


def get_archetype(archetype_id: str) -> Dict[str, Any]:
    for a in ARCHETYPES:
        if a["id"] == archetype_id:
            return a
    return None
