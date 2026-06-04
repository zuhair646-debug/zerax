"""
Section AI Profiles — كل قسم في زيتاكس له "خبير" AI مخصص
═══════════════════════════════════════════════════════════════════════════
الفلسفة:
  - كل قسم (Website Builder, App Studio, Image Studio, Video Studio, Auto-Coder,
    Voice Studio, Mobile App Builder, Games...) له:
      • نخبة من الموديلات (Premium + Strong فقط، ما فيه ضعيف)
      • تنوّع داخل القسم (تصاميم مختلفة، أفكار متنوعة)
      • حدود صارمة (الخبير ما يخرج عن مجاله)
      • System prompt مخصص يحدد سلوكه

الفائدة:
  - تنوّع تلقائي في كل عملية إنشاء
  - أعلى جودة مضمونة في كل قسم
  - كل قسم له شخصية مستقلة (لا توجد قائمة موديلات موحّدة "عمياء")
"""
from __future__ import annotations
import os
import random
from typing import Dict, List, Optional, Tuple


# ════════════════════════════════════════════════════════════════════════
# أساس: من المتاح؟
# ════════════════════════════════════════════════════════════════════════
def _available() -> Dict[str, bool]:
    return {
        "claude":     bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()),
        "openai":     bool(os.environ.get("OPENAI_API_KEY", "") or os.environ.get("OPENAI_DIRECT_KEY", "")),
        "gemini":     bool(os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")),
        "deepseek":   bool(os.environ.get("DEEPSEEK_API_KEY", "")),
        "kimi":       bool(os.environ.get("MOONSHOT_API_KEY", "") or os.environ.get("KIMI_API_KEY", "")),
        "qwen":       bool(os.environ.get("DASHSCOPE_API_KEY", "") or os.environ.get("QWEN_API_KEY", "")),
        "fal":        bool(os.environ.get("FAL_KEY", "") or os.environ.get("FAL_API_KEY", "")),
        "elevenlabs": bool(os.environ.get("ELEVENLABS_API_KEY", "")),
        "runway":     bool(os.environ.get("RUNWAY_API_KEY", "")),
    }


# ════════════════════════════════════════════════════════════════════════
# تعريف الأقسام — كل قسم له خبير + نخبة موديلات
# ════════════════════════════════════════════════════════════════════════
SECTIONS: Dict[str, Dict] = {

    # ─────────────────────────────────────────────────────────────────
    # 🌐 منشئ المواقع (FreeBuild / Website Builder)
    # ─────────────────────────────────────────────────────────────────
    "website_builder": {
        "label": "منشئ المواقع",
        "icon": "Globe",
        "color": "fuchsia",
        "scope": "websites_only",
        "description": "خبير في بناء مواقع متكاملة من الصفر. كل تصميم يكون عالم جديد متنوّع.",
        "constraints": [
            "ممنوع برمجة تطبيقات موبايل هنا",
            "ممنوع توليد صور خارج سياق الموقع",
            "ممنوع كتابة كود backend مستقل",
            "التركيز فقط: HTML/CSS/JS، Tailwind، تصاميم SPA",
        ],
        "diversity_strategy": "rotate_design_persona",
        "design_personas": [
            "minimalist_japanese",      # ياباني بسيط
            "brutalist_bold",            # وحشي جريء
            "neon_cyberpunk",            # نيون سايبربانك
            "luxury_arabic",             # عربي فاخر
            "y2k_retro",                 # ريترو 2000
            "swiss_editorial",           # سويسري تحريري
            "glassmorphism_premium",     # زجاجي فاخر
            "neo_brutalism",             # نيو بروتاليزم
            "art_deco_elegance",         # آرت ديكو
            "scandinavian_clean",        # اسكندنافي نظيف
            "memphis_playful",           # ممفيس مرح
            "kinetic_typography",        # تايبوغرافي حركي
        ],
        "models": {
            "primary":   [("claude", 10), ("openai", 9)],
            "secondary": [("deepseek", 8), ("kimi", 8)],
            "fallback":  [("gemini", 9)],
        },
        "system_prompt": (
            "أنت خبير بناء مواقع في زيتاكس. مهمتك الوحيدة: تصميم مواقع متكاملة من الصفر.\n"
            "قواعد صارمة:\n"
            "1) كل موقع تصنعه = عالم بصري جديد ومختلف تماماً عن السابق.\n"
            "2) ممنوع التكرار في التصاميم. كل مشروع يحصل على شخصية تصميم فريدة.\n"
            "3) استخدم Tailwind + animations + glassmorphism حسب persona الجلسة.\n"
            "4) لا تخرج عن مجال المواقع — لا تطبيقات موبايل ولا backend منفصل.\n"
            "5) كل قسم في الموقع له design pattern مختلف (Hero, About, CTA, Footer).\n"
            "6) اللغة العربية لازم تكون RTL وخطوط عربية حقيقية.\n"
        ),
    },

    # ─────────────────────────────────────────────────────────────────
    # 📱 منشئ التطبيقات (App Studio)
    # ─────────────────────────────────────────────────────────────────
    "app_studio": {
        "label": "منشئ التطبيقات",
        "icon": "AppWindow",
        "color": "indigo",
        "scope": "apps_only",
        "description": "خبير في تصميم وبناء تطبيقات React كاملة. كل تطبيق له هوية مميزة.",
        "constraints": [
            "ممنوع بناء مواقع تسويقية هنا",
            "ممنوع توليد صور خارج التطبيق",
            "التركيز: React + State Management + UI components + API integration",
        ],
        "diversity_strategy": "rotate_app_archetype",
        "design_personas": [
            "saas_dashboard_minimal",      # داشبورد SaaS بسيط
            "ios_native_glassy",           # iOS أصلي زجاجي
            "android_material_3",          # ماتيريال أندرويد
            "fintech_dark_premium",        # فينتك داكن فاخر
            "social_media_vibrant",        # سوشال نابض
            "ecommerce_clean_modern",      # تجارة الكترونية نظيف
            "productivity_focus_mode",     # إنتاجية مركزة
            "creator_studio_dark",         # استوديو المبدعين
        ],
        "models": {
            "primary":   [("claude", 10), ("openai", 10)],
            "secondary": [("deepseek", 9)],
            "fallback":  [("gemini", 9)],
        },
        "system_prompt": (
            "أنت خبير بناء تطبيقات React في زيتاكس. مهمتك الوحيدة: بناء تطبيقات كاملة.\n"
            "قواعد:\n"
            "1) كل تطبيق له هوية تصميم مميزة (archetype) — لا تكرر.\n"
            "2) استخدم shadcn/ui + Tailwind + lucide-react.\n"
            "3) أنشئ صفحات منفصلة، state management واضح، روابط API منظمة.\n"
            "4) ممنوع كتابة موقع تسويقي بدل تطبيق. هذا قسم التطبيقات.\n"
            "5) اللغة الافتراضية: العربية RTL.\n"
        ),
    },

    # ─────────────────────────────────────────────────────────────────
    # 🎨 استوديو الصور (Image Studio)
    # ─────────────────────────────────────────────────────────────────
    "image_studio": {
        "label": "استوديو الصور",
        "icon": "Image",
        "color": "amber",
        "scope": "images_only",
        "description": "خبير في توليد وتعديل الصور بأعلى جودة عالمية.",
        "constraints": [
            "ممنوع توليد كود أو نص طويل",
            "ممنوع توليد فيديو هنا (له قسمه)",
            "التركيز: prompt engineering + اختيار الموديل المناسب",
        ],
        "diversity_strategy": "rotate_style_dna",
        "design_personas": [
            "cinematic_film",              # سينمائي
            "studio_portrait",             # بورتري استوديو
            "editorial_fashion",           # موضة تحريرية
            "product_advertising",         # إعلان منتج
            "anime_illustration",          # رسم أنمي
            "vintage_film_grain",          # حبيبات فيلم قديم
            "neon_synthwave",              # نيون سينث-وايف
            "dreamy_pastel",               # حالم باستيل
            "watercolor_painting",         # ألوان مائية
            "3d_render_octane",            # رندر 3D
        ],
        "image_models": [
            ("flux_pro_ultra", "fal", 10, ["luxury", "photorealistic"]),
            ("gpt_image_1", "openai", 10, ["complex_scenes", "text_in_image"]),
            ("imagen_4_ultra", "fal", 10, ["realistic", "arabic_text"]),
            ("flux_pro", "fal", 9, ["daily", "general"]),
            ("recraft_v3", "fal", 9, ["logos", "arabic_text"]),
            ("ideogram_v3", "fal", 9, ["typography", "arabic"]),
            ("seedream_4", "fal", 8, ["bulk", "ecommerce"]),
        ],
        "edit_models": [
            ("nano_banana", "gemini", 10),
            ("flux_kontext", "fal", 10),
            ("gpt_image_edit", "openai", 10),
        ],
        "system_prompt": (
            "أنت خبير الصور في زيتاكس. مهمتك: توليد وتعديل صور بأعلى جودة.\n"
            "قواعد:\n"
            "1) اختر أفضل موديل حسب نوع الطلب (شعار→Recraft، فاخر→Flux Pro Ultra، نص عربي→Ideogram).\n"
            "2) كل توليد جديد = أسلوب جديد. لا تكرر نفس الستايل.\n"
            "3) للتعديل: استخدم Nano Banana للتعديلات الذكية (غيّر فقط جزء معين).\n"
            "4) ممنوع توليد فيديو هنا.\n"
        ),
    },

    # ─────────────────────────────────────────────────────────────────
    # 🎬 استوديو الفيديو (Video Studio)
    # ─────────────────────────────────────────────────────────────────
    "video_studio": {
        "label": "استوديو الفيديو",
        "icon": "Video",
        "color": "rose",
        "scope": "videos_only",
        "description": "خبير سينمائي يحوّل أفكارك لأفلام قصيرة باستخدام أحدث الموديلات.",
        "constraints": [
            "ممنوع توليد صور ثابتة (له قسم منفصل)",
            "ممنوع كتابة كود أو نص طويل",
            "التركيز: prompt cinematic + اختيار موديل الفيديو الأمثل",
        ],
        "diversity_strategy": "rotate_cinematic_style",
        "design_personas": [
            "wes_anderson_symmetrical",    # أندرسون متماثل
            "noir_film_dramatic",          # نوار درامي
            "anime_cinematic",             # أنمي سينمائي
            "documentary_realism",         # وثائقي واقعي
            "music_video_dynamic",         # موسيقي ديناميكي
            "advertising_glossy",          # إعلاني لامع
            "indie_handheld",              # مستقل بكاميرا يد
            "blockbuster_epic",            # ملحمي بلوكباستر
        ],
        "video_models": [
            ("veo_3", "fal", 10, ["cinematic", "advertising"], 0.50, 8),
            ("sora_2", "openai", 10, ["narrative", "storytelling"], 0.50, 20),
            ("kling_2_1_master", "fal", 10, ["cinematic", "motion"], 0.28, 10),
            ("luma_ray_2", "fal", 9, ["camera_motion"], 0.30, 9),
            ("runway_gen4", "runway", 9, ["vfx", "professional"], 0.25, 10),
            ("minimax_hailuo_02", "fal", 8, ["social_media", "fast"], 0.045, 6),
        ],
        "system_prompt": (
            "أنت خبير الفيديو السينمائي في زيتاكس. مهمتك: تحويل الأفكار لأفلام قصيرة.\n"
            "قواعد:\n"
            "1) للإعلانات الفاخرة → Veo 3.\n"
            "2) للقصص الطويلة → Sora 2.\n"
            "3) للمشاهد المعقدة → Kling 2.1.\n"
            "4) للسوشال السريع → Minimax Hailuo.\n"
            "5) كل فيديو = أسلوب سينمائي جديد (rotate persona).\n"
        ),
    },

    # ─────────────────────────────────────────────────────────────────
    # 🎵 استوديو الصوت (Voice Studio)
    # ─────────────────────────────────────────────────────────────────
    "voice_studio": {
        "label": "استوديو الصوت",
        "icon": "Mic",
        "color": "sky",
        "scope": "voice_only",
        "description": "خبير الأصوات الطبيعية واستنساخ اللهجات (سعودي، خليجي، شامي، مصري).",
        "constraints": [
            "ممنوع توليد نص طويل (هذا للذكاء النصي)",
            "ممنوع توليد صور أو فيديو",
            "التركيز: TTS + Voice Cloning + Dialects",
        ],
        "diversity_strategy": "rotate_voice_persona",
        "design_personas": [
            "saudi_male_warm",
            "saudi_female_clear",
            "khaleeji_news_anchor",
            "standard_arabic_formal",
            "egyptian_friendly",
            "english_professional",
        ],
        "voice_models": [
            ("elevenlabs_v3", "elevenlabs", 10, ["dialects", "arabic_dialects", "clone"]),
            ("openai_tts_hd", "openai", 9, ["natural", "multilingual"]),
        ],
        "system_prompt": (
            "أنت خبير الأصوات في زيتاكس. الأفضل: ElevenLabs v3 لكل اللهجات العربية.\n"
            "قواعد:\n"
            "1) للهجات → ElevenLabs دائماً.\n"
            "2) للنصوص العامة → OpenAI TTS HD احتياط.\n"
            "3) كل voice persona = صوت مختلف.\n"
        ),
    },

    # ─────────────────────────────────────────────────────────────────
    # 🔧 منشئ تطبيقات الموبايل (Mobile App Builder)
    # ─────────────────────────────────────────────────────────────────
    "mobile_app_builder": {
        "label": "منشئ تطبيقات الموبايل",
        "icon": "Smartphone",
        "color": "violet",
        "scope": "mobile_apps_only",
        "description": "خبير React Native / Expo لبناء تطبيقات iOS و Android.",
        "constraints": [
            "ممنوع بناء مواقع ويب",
            "ممنوع كود backend",
            "التركيز: React Native + Expo + native components",
        ],
        "diversity_strategy": "rotate_mobile_archetype",
        "design_personas": [
            "ios_human_interface",
            "material_you_dynamic",
            "fintech_mobile_dark",
            "social_app_vibrant",
            "ecommerce_mobile",
            "fitness_tracker_clean",
        ],
        "models": {
            "primary":   [("claude", 10), ("openai", 10)],
            "secondary": [("deepseek", 9)],
            "fallback":  [("gemini", 9)],
        },
        "system_prompt": (
            "أنت خبير React Native في زيتاكس. مهمتك: بناء تطبيقات موبايل أصلية.\n"
            "قواعد:\n"
            "1) iOS = Human Interface Guidelines.\n"
            "2) Android = Material You.\n"
            "3) ممنوع تصاميم ويب هنا.\n"
        ),
    },

    # ─────────────────────────────────────────────────────────────────
    # 🛠️ Auto-Coder (المالك فقط)
    # ─────────────────────────────────────────────────────────────────
    "auto_coder": {
        "label": "برمجة زيتاكس",
        "icon": "Cpu",
        "color": "emerald",
        "scope": "platform_self_only",
        "owner_only": True,
        "description": "مهندس زيتاكس الذي يبرمج المنصة نفسها (للمالك فقط).",
        "constraints": [
            "يعمل فقط على كود زيتاكس داخل /app",
            "ممنوع توليد محتوى للمستخدمين",
            "تنفيذ أدوات حقيقية: git, file ops, deploy",
        ],
        "diversity_strategy": "task_aware_routing",
        "models": {
            "primary":   [("claude", 10), ("openai", 10)],
            "secondary": [("deepseek", 9), ("kimi", 8)],
            "fallback":  [("gemini", 9)],
        },
        "system_prompt": "أنت مهندس زيتاكس. تطوير، إصلاح، ونشر المنصة فقط.",
    },

    # ─────────────────────────────────────────────────────────────────
    # 🎮 الألعاب (Games) — يظهر في القائمة بدون برمجة فعلية بعد
    # ─────────────────────────────────────────────────────────────────
    "games_studio": {
        "label": "استوديو الألعاب",
        "icon": "Gamepad2",
        "color": "lime",
        "scope": "games_only",
        "visible_only": True,
        "coming_soon": True,
        "description": "خبير توليد ألعاب تفاعلية (HTML5 + Phaser/Three.js). قيد التطوير.",
        "constraints": [
            "ممنوع بناء مواقع تسويقية",
            "التركيز: ألعاب HTML5 / WebGL",
        ],
        "diversity_strategy": "rotate_game_genre",
        "design_personas": [
            "puzzle_minimal",
            "platformer_pixel_art",
            "endless_runner_neon",
            "card_strategy",
            "rhythm_music",
            "idle_clicker",
        ],
        "models": {
            "primary":   [("claude", 10), ("openai", 10)],
            "secondary": [("deepseek", 9)],
        },
        "system_prompt": "أنت خبير ألعاب HTML5 (Phaser/Three.js/p5.js). قيد التحضير.",
    },

    # ─────────────────────────────────────────────────────────────────
    # 💬 الذكاء العام للمحادثة (Open Chat / Agents)
    # ─────────────────────────────────────────────────────────────────
    "general_chat": {
        "label": "المحادثة العامة",
        "icon": "MessageSquare",
        "color": "zinc",
        "scope": "open_chat",
        "description": "ذكاء عام للأسئلة والمحادثات المفتوحة.",
        "constraints": [
            "ممنوع تنفيذ كود مدمر",
            "حدّد المهمة وحوّل لقسم متخصص إذا لزم",
        ],
        "diversity_strategy": "task_aware",
        "models": {
            "primary":   [("claude", 10), ("openai", 10)],
            "secondary": [("qwen", 10), ("kimi", 9), ("deepseek", 9)],
            "fallback":  [("gemini", 9)],
        },
        "system_prompt": (
            "أنت ذكاء زيتاكس العام. أجب باللهجة السعودية الطبيعية. "
            "للمهام المتخصصة (صور، فيديو، كود)، اقترح القسم المناسب."
        ),
    },
}


# ════════════════════════════════════════════════════════════════════════
# Resolver: لكل قسم، أرجع أفضل موديل متاح + persona متنوّعة
# ════════════════════════════════════════════════════════════════════════
def pick_for_section(section_id: str, seed: Optional[int] = None) -> Dict:
    """
    Pick the best available LLM model + diversity persona for a section.
    Returns: {section, model, persona, system_prompt, reason}
    """
    sec = SECTIONS.get(section_id)
    if not sec:
        return {"error": "section_not_found", "available_sections": list(SECTIONS.keys())}

    avail = _available()

    # 1. Pick best LLM model
    selected_model: Optional[Tuple[str, int]] = None
    selected_tier: str = ""
    models_config = sec.get("models", {})

    for tier in ("primary", "secondary", "fallback"):
        ranked = models_config.get(tier, [])
        # Sort by quality desc
        ranked_sorted = sorted(ranked, key=lambda x: -x[1])
        for prov, q in ranked_sorted:
            if avail.get(prov):
                selected_model = (prov, q)
                selected_tier = tier
                break
        if selected_model:
            break

    # 2. Pick a diverse persona (rotation via seed/random)
    personas = sec.get("design_personas", [])
    persona = None
    if personas:
        if seed is not None:
            persona = personas[seed % len(personas)]
        else:
            persona = random.choice(personas)

    return {
        "section": section_id,
        "section_label": sec.get("label"),
        "model": selected_model[0] if selected_model else None,
        "model_quality": selected_model[1] if selected_model else 0,
        "model_tier": selected_tier,
        "persona": persona,
        "diversity_strategy": sec.get("diversity_strategy"),
        "system_prompt": sec.get("system_prompt", ""),
        "scope": sec.get("scope"),
        "constraints": sec.get("constraints", []),
        "reason": _why(section_id, selected_model[0] if selected_model else None, persona),
    }


def list_sections(include_hidden: bool = False, owner: bool = False) -> List[Dict]:
    """List all sections with their current model assignment + status."""
    avail = _available()
    out: List[Dict] = []
    for sid, sec in SECTIONS.items():
        if sec.get("owner_only") and not owner:
            continue
        # Compute best available LLM model
        best_model = None
        best_quality = 0
        for tier in ("primary", "secondary", "fallback"):
            for prov, q in sec.get("models", {}).get(tier, []):
                if avail.get(prov):
                    best_model = prov
                    best_quality = q
                    break
            if best_model:
                break

        # For media sections, the "current model" is the best media model
        for media_list_key in ("image_models", "video_models", "voice_models"):
            if best_model:
                break
            for entry in sec.get(media_list_key, []):
                # entry = (key, provider, quality, ...)
                if len(entry) >= 3 and avail.get(entry[1]):
                    best_model = entry[0]
                    best_quality = entry[2]
                    break

        media_count = (
            len(sec.get("image_models", [])) +
            len(sec.get("video_models", [])) +
            len(sec.get("voice_models", [])) +
            len(sec.get("edit_models", []))
        )

        out.append({
            "id": sid,
            "label": sec.get("label"),
            "icon": sec.get("icon"),
            "color": sec.get("color"),
            "description": sec.get("description"),
            "scope": sec.get("scope"),
            "personas_count": len(sec.get("design_personas", [])),
            "models_count": sum(len(sec.get("models", {}).get(t, [])) for t in ("primary","secondary","fallback")) + media_count,
            "current_model": best_model,
            "current_quality": best_quality,
            "constraints": sec.get("constraints", []),
            "coming_soon": sec.get("coming_soon", False),
            "owner_only": sec.get("owner_only", False),
            "available": bool(best_model),
        })
    return out


def get_section_detail(section_id: str) -> Optional[Dict]:
    """Full section detail (for admin UI)."""
    sec = SECTIONS.get(section_id)
    if not sec:
        return None
    avail = _available()
    # Resolve which models are currently usable
    resolved_models: List[Dict] = []
    for tier in ("primary", "secondary", "fallback"):
        for prov, q in sec.get("models", {}).get(tier, []):
            resolved_models.append({
                "provider": prov,
                "quality": q,
                "tier": tier,
                "available": avail.get(prov, False),
            })
    return {
        "id": section_id,
        **{k: v for k, v in sec.items() if k != "models"},
        "resolved_models": resolved_models,
        "image_models": sec.get("image_models", []),
        "video_models": sec.get("video_models", []),
        "voice_models": sec.get("voice_models", []),
        "edit_models": sec.get("edit_models", []),
    }


def _why(section_id: str, model: Optional[str], persona: Optional[str]) -> str:
    if not model:
        return f"⚠️ {section_id}: لا يوجد موديل متاح. أضف المفاتيح."
    persona_txt = f" • هوية: {persona}" if persona else ""
    return f"🎯 {section_id} → {model}{persona_txt}"
