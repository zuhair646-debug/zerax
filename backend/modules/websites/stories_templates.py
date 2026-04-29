"""
Stories Templates Library
─────────────────────────
A curated catalog of ready-made Story templates the storefront owner can use
with one click. Each template has:
  • id, name, emoji, description
  • category   — 'sale' | 'new_product' | 'thanks' | 'event' | 'feature' | 'announcement' | 'reminder'
  • output     — 'image' | 'video'
  • vertical_tags — list of vertical IDs this template is best suited for ('all' for any)
  • duration_sec  — for video templates (4 | 8 | 12)
  • size       — '1280x720' (landscape) or '1024x1792' (vertical, for stories)
  • fields     — list of {name, label, type, required, default} the user must/may fill
  • prompt     — Python format string. Receives: store_name, vertical, primary_color,
                 secondary_color, language, plus all `fields` values.
  • caption_tpl — Caption shown under the story (same placeholders).

Designed to feel premium — every prompt asks for "luxury cinematic quality",
"professional product photography", "soft golden lighting", etc., to match the
overall storefront aesthetic.
"""

TEMPLATES = [
    # ─────────── SALE / DISCOUNT ───────────
    {
        "id": "sale_flash_image",
        "name": "خصم خاطف",
        "emoji": "⚡",
        "description": "إعلان تخفيض حصري بنسبة محدّدة",
        "category": "sale",
        "output": "image",
        "vertical_tags": ["all"],
        "size": "1024x1792",
        "fields": [
            {"name": "discount", "label": "نسبة الخصم %", "type": "number", "required": True, "default": 20},
            {"name": "product_hint", "label": "المنتج المعروض (اختياري)", "type": "text", "required": False, "default": ""},
        ],
        "prompt": (
            "Premium cinematic luxury advertisement story for {store_name}. "
            "Dramatic vertical poster announcing a flash sale with HUGE bold Arabic text '{discount}% خصم'. "
            "{product_hint_inline}"
            "Background uses {primary_color} accents and warm golden lighting, professional product photography, "
            "high contrast, depth of field, ultra-sharp detail, 4K quality, no people. Eye-catching, modern, premium feel."
        ),
        "caption_tpl": "⚡ خصم {discount}% — لا تفوّت الفرصة!",
    },
    {
        "id": "sale_video_promo",
        "name": "إعلان تخفيضات (فيديو)",
        "emoji": "🎬",
        "description": "فيديو سينمائي لإعلان عرض",
        "category": "sale",
        "output": "video",
        "vertical_tags": ["all"],
        "duration_sec": 4,
        "size": "1024x1792",
        "fields": [
            {"name": "discount", "label": "نسبة الخصم %", "type": "number", "required": True, "default": 25},
        ],
        "prompt": (
            "Cinematic vertical 4-second luxury commercial intro for a {vertical}. "
            "Slow-motion close-up of beautifully lit product, soft golden hour lighting, "
            "Arabic text overlay appears: 'خصم {discount}%'. {primary_color} brand accents. "
            "Professional cinematography, smooth camera movement, premium feel, no people."
        ),
        "caption_tpl": "🎬 خصم {discount}% لفترة محدودة",
    },

    # ─────────── NEW PRODUCT ───────────
    {
        "id": "new_product_reveal",
        "name": "كشف منتج جديد",
        "emoji": "✨",
        "description": "إعلان إطلاق منتج جديد",
        "category": "new_product",
        "output": "image",
        "vertical_tags": ["all"],
        "size": "1024x1792",
        "fields": [
            {"name": "product_name", "label": "اسم المنتج", "type": "text", "required": True, "default": ""},
            {"name": "product_desc", "label": "وصف قصير", "type": "text", "required": False, "default": ""},
        ],
        "prompt": (
            "Vertical luxury product launch poster for {store_name}. Hero shot of '{product_name}' "
            "{product_desc_inline}floating in elegant studio space, dramatic spotlight, soft shadows, "
            "{primary_color} subtle gradient background, professional commercial photography, ultra-detailed, "
            "8K quality. Arabic header text 'جديد ✨' subtly placed on top."
        ),
        "caption_tpl": "✨ جديد: {product_name}",
    },
    {
        "id": "new_product_video",
        "name": "إطلاق منتج (فيديو)",
        "emoji": "🚀",
        "description": "فيديو 360° لمنتج جديد",
        "category": "new_product",
        "output": "video",
        "vertical_tags": ["all"],
        "duration_sec": 4,
        "size": "1024x1792",
        "fields": [
            {"name": "product_name", "label": "اسم المنتج", "type": "text", "required": True, "default": ""},
        ],
        "prompt": (
            "Cinematic vertical 4-second product reveal video. Close-up rotating shot of {product_name}, "
            "studio lighting on dark gradient background with {primary_color} accents, slow motion, "
            "luxury feel, no people, professional commercial cinematography."
        ),
        "caption_tpl": "🚀 منتجنا الجديد {product_name}",
    },

    # ─────────── THANKS / LOYALTY ───────────
    {
        "id": "thanks_customers",
        "name": "شكراً لزبائننا",
        "emoji": "💖",
        "description": "بطاقة شكر للعملاء",
        "category": "thanks",
        "output": "image",
        "vertical_tags": ["all"],
        "size": "1024x1792",
        "fields": [],
        "prompt": (
            "Heartwarming luxury thank-you story poster for {store_name}. "
            "Beautiful soft ambient scene with warm golden light, elegant typography placeholder, "
            "{primary_color} highlights, cozy atmosphere, professional photography, "
            "premium minimalist design. Vertical format. The text 'شكراً لكم 💖' centered."
        ),
        "caption_tpl": "💖 شكراً لكل عملائنا الكرام",
    },

    # ─────────── EVENTS / OPENING ───────────
    {
        "id": "event_announcement",
        "name": "إعلان حدث",
        "emoji": "🎉",
        "description": "إعلان حدث/فعالية/افتتاح",
        "category": "event",
        "output": "image",
        "vertical_tags": ["all"],
        "size": "1024x1792",
        "fields": [
            {"name": "event_title", "label": "عنوان الحدث", "type": "text", "required": True, "default": ""},
            {"name": "event_date", "label": "التاريخ والوقت", "type": "text", "required": False, "default": ""},
        ],
        "prompt": (
            "Festive luxury event announcement vertical poster for {store_name}. "
            "Sophisticated celebration theme with confetti, {primary_color} bokeh lights, "
            "elegant venue ambience, professional cinematic photography, premium feel, no people. "
            "Arabic text overlay '{event_title}' {event_date_inline}."
        ),
        "caption_tpl": "🎉 {event_title}",
    },

    # ─────────── FEATURE HIGHLIGHTS (vertical-aware) ───────────
    {
        "id": "feature_food_special",
        "name": "طبق اليوم",
        "emoji": "🍽️",
        "description": "تسليط الضوء على طبق مميز",
        "category": "feature",
        "output": "image",
        "vertical_tags": ["restaurant", "cafe", "food_delivery"],
        "size": "1024x1792",
        "fields": [
            {"name": "dish_name", "label": "اسم الطبق", "type": "text", "required": True, "default": ""},
        ],
        "prompt": (
            "Mouth-watering top-down shot of {dish_name} as the hero, beautifully plated, "
            "fresh ingredients around, warm restaurant lighting, soft steam rising, "
            "professional food photography, ultra-sharp, vertical format, premium feel. "
            "Subtle Arabic header 'طبق اليوم'."
        ),
        "caption_tpl": "🍽️ طبق اليوم: {dish_name}",
    },
    {
        "id": "feature_salon_service",
        "name": "خدمة مميزة",
        "emoji": "💅",
        "description": "إعلان خدمة سبا/صالون",
        "category": "feature",
        "output": "image",
        "vertical_tags": ["salon", "spa", "beauty"],
        "size": "1024x1792",
        "fields": [
            {"name": "service_name", "label": "اسم الخدمة", "type": "text", "required": True, "default": ""},
        ],
        "prompt": (
            "Luxury vertical spa/beauty advertisement for {service_name}. "
            "Soft warm lighting, elegant minimalist setup, {primary_color} subtle accents, "
            "premium relaxing atmosphere, professional photography, no people, vertical format."
        ),
        "caption_tpl": "💅 خدمة مميزة: {service_name}",
    },
    {
        "id": "feature_property_listing",
        "name": "عرض عقار",
        "emoji": "🏠",
        "description": "إعلان لعقار مميز",
        "category": "feature",
        "output": "image",
        "vertical_tags": ["real_estate"],
        "size": "1024x1792",
        "fields": [
            {"name": "property_type", "label": "نوع العقار", "type": "text", "required": True, "default": "فيلا فاخرة"},
            {"name": "city", "label": "المدينة", "type": "text", "required": False, "default": ""},
        ],
        "prompt": (
            "Cinematic luxury real-estate vertical advertisement. Stunning {property_type} "
            "{city_inline}exterior at golden hour, modern architecture, lush landscaping, "
            "warm interior glow, professional architectural photography, ultra-sharp, vertical format."
        ),
        "caption_tpl": "🏠 {property_type}{city_inline_caption}",
    },

    # ─────────── ANNOUNCEMENTS / REMINDERS ───────────
    {
        "id": "announce_hours",
        "name": "ساعات العمل",
        "emoji": "🕐",
        "description": "تنبيه ساعات العمل / تغييرها",
        "category": "announcement",
        "output": "image",
        "vertical_tags": ["all"],
        "size": "1024x1792",
        "fields": [
            {"name": "hours", "label": "ساعات العمل", "type": "text", "required": True, "default": "9 صباحاً - 12 منتصف الليل"},
        ],
        "prompt": (
            "Minimalist luxury vertical announcement card for {store_name}. "
            "Elegant clock or sunrise motif, {primary_color} accents on dark gradient, "
            "premium typography placeholder, professional design. "
            "Arabic text 'ساعات العمل' header and '{hours}' subheader."
        ),
        "caption_tpl": "🕐 ساعات العمل: {hours}",
    },
    {
        "id": "reminder_free_delivery",
        "name": "توصيل مجاني",
        "emoji": "🚚",
        "description": "تذكير بحد التوصيل المجاني",
        "category": "reminder",
        "output": "image",
        "vertical_tags": ["all"],
        "size": "1024x1792",
        "fields": [
            {"name": "threshold", "label": "حد الطلب (ر.س)", "type": "number", "required": True, "default": 100},
        ],
        "prompt": (
            "Cheerful vertical advertising story for {store_name}. "
            "Stylized delivery scooter/box, {primary_color} brand color, dynamic motion lines, "
            "professional commercial illustration style, premium feel. "
            "Arabic text overlay 'توصيل مجاني فوق {threshold} ر.س'."
        ),
        "caption_tpl": "🚚 توصيل مجاني فوق {threshold} ر.س",
    },
    {
        "id": "announce_ramadan",
        "name": "عرض رمضاني",
        "emoji": "🌙",
        "description": "إعلان عرض موسمي (رمضان)",
        "category": "announcement",
        "output": "image",
        "vertical_tags": ["all"],
        "size": "1024x1792",
        "fields": [
            {"name": "offer_text", "label": "نص العرض", "type": "text", "required": True, "default": "خصم 30% طوال الشهر الكريم"},
        ],
        "prompt": (
            "Luxury Ramadan-themed vertical poster for {store_name}. "
            "Elegant crescent moon, golden lanterns, deep purple-and-gold color palette, "
            "Arabic calligraphy aesthetic, professional cinematic lighting, premium feel. "
            "Arabic text 'رمضان كريم' top and '{offer_text}' subtle below."
        ),
        "caption_tpl": "🌙 رمضان كريم — {offer_text}",
    },
    {
        "id": "announce_weekend",
        "name": "عرض نهاية الأسبوع",
        "emoji": "🎁",
        "description": "تخفيضات نهاية الأسبوع",
        "category": "sale",
        "output": "image",
        "vertical_tags": ["all"],
        "size": "1024x1792",
        "fields": [
            {"name": "discount", "label": "نسبة الخصم %", "type": "number", "required": True, "default": 15},
        ],
        "prompt": (
            "Modern vertical weekend-sale story poster. Dynamic geometric design, bold contrasting colors with "
            "{primary_color} highlights, golden glow effects, premium feel, no people. "
            "Arabic text 'عرض الويكند' top and 'خصم {discount}%' large center."
        ),
        "caption_tpl": "🎁 عرض الويكند — خصم {discount}%",
    },
]


def filter_for_vertical(vertical: str | None):
    """Return templates suitable for the given vertical (or 'all' tagged)."""
    v = (vertical or "").lower()
    if not v:
        return list(TEMPLATES)
    return [t for t in TEMPLATES if "all" in t["vertical_tags"] or v in t["vertical_tags"]]


def get_template(tid: str):
    for t in TEMPLATES:
        if t["id"] == tid:
            return t
    return None


def render_prompt(tpl: dict, ctx: dict) -> tuple[str, str]:
    """Fill the template's prompt + caption with the user-supplied context.
    Returns (rendered_prompt, rendered_caption)."""
    safe_ctx = {
        "store_name": ctx.get("store_name") or "the brand",
        "vertical": ctx.get("vertical") or "premium store",
        "primary_color": ctx.get("primary_color") or "warm gold",
        "secondary_color": ctx.get("secondary_color") or "deep navy",
        "language": ctx.get("language") or "Arabic",
    }
    safe_ctx.update({k: v for k, v in (ctx.get("fields") or {}).items()})

    # Pretty inlines for optional fields (avoid leaving "None " in the prompt)
    pd = safe_ctx.get("product_desc") or ""
    safe_ctx["product_desc_inline"] = f"described as '{pd}', " if pd else ""
    ph = safe_ctx.get("product_hint") or ""
    safe_ctx["product_hint_inline"] = f"Show a single hero {ph}. " if ph else ""
    ed = safe_ctx.get("event_date") or ""
    safe_ctx["event_date_inline"] = f"taking place on {ed}" if ed else ""
    city = safe_ctx.get("city") or ""
    safe_ctx["city_inline"] = f"in {city} " if city else ""
    safe_ctx["city_inline_caption"] = f" — {city}" if city else ""

    try:
        prompt = tpl["prompt"].format(**safe_ctx)
    except KeyError as e:
        raise ValueError(f"Missing template field: {e}")
    try:
        caption = tpl["caption_tpl"].format(**safe_ctx)
    except KeyError:
        caption = tpl["name"]
    return prompt, caption[:120]
