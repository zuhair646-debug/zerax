"""
Media Router — Quality-First Edition for Zenrex
═══════════════════════════════════════════════════════════════════════════
Smart selection of premium media models (image / video / voice / edit).

الفلسفة: نفس فلسفة auto_router.py — الجودة أولاً، السعر ثاني.

تم استبعاد كل الموديلات الضعيفة (SD 1.5 / SDXL / Stable Video XT...).
فقط الموديلات الـ Top-Tier 2025-2026.

═══ IMAGE TIER ═══
  💎 Premium (لا تقبل المساومة):
     - Flux 1.1 Pro Ultra  (إعلانات منتجات فاخرة)
     - GPT Image 1         (أعلى دقة في تتبع التعليمات)
     - Imagen 4 Ultra      (واقعية + نصوص داخل الصورة)

  ⚡ Strong (جودة عالية، سعر أفضل):
     - Flux 1.1 Pro        (الاستخدام اليومي)
     - Recraft V3          (شعارات + نص عربي)
     - Ideogram V3         (نصوص عربية واضحة)
     - Seedream 4 (Bytedance)  (كميات احترافية)

═══ VIDEO TIER ═══
  💎 Premium:
     - Veo 3 (Google)      (الأفضل عالمياً 2026)
     - Sora 2 (OpenAI)     (سينمائي بحت)
     - Kling 2.1 Master    (سينمائي + إخراج)

  ⚡ Strong:
     - Luma Ray 2          (حركة كاميرا سينمائية)
     - Minimax Hailuo 02   (ديناميكي للسوشال)
     - Runway Gen-4        (احترافي مرن)

═══ IMAGE EDIT TIER ═══
  - Nano Banana (Gemini)   (تعديل ذكي، يفهم "غيّر لون الورد فقط")
  - GPT Image Edit         (تعديل دقيق)
  - Flux Kontext           (تحرير متماسك)

═══ VOICE TIER ═══
  💎 Premium:
     - ElevenLabs v3       (الأفضل عالمياً، استنساخ صوت + لهجات)

  ⚡ Strong:
     - OpenAI TTS HD       (طبيعي بسعر معقول)

❌ تم استبعاد:
     - Stable Diffusion 1.5/2.1/XL (قديم، جودة ضعيفة)
     - SVD / Stable Video Diffusion (ضعيف مقابل Hunyuan)
     - أي موديل مجاني سريع منخفض الجودة
"""
from __future__ import annotations
import os
import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
# IMAGE MODELS — pricing (USD per image, standard resolution)
# ════════════════════════════════════════════════════════════════════════
IMAGE_MODELS: Dict[str, Dict] = {
    "flux_pro_ultra": {
        "label": "Flux 1.1 Pro Ultra",
        "provider": "fal",
        "endpoint": "fal-ai/flux-pro/v1.1-ultra",
        "price_usd": 0.06,
        "tier": "premium",
        "specialties": ["photorealistic", "product_ads", "luxury", "portraits", "fashion"],
        "quality": 10,
        "supports_arabic_text": False,
    },
    "gpt_image_1": {
        "label": "GPT Image 1",
        "provider": "openai",
        "endpoint": "gpt-image-1",
        "price_usd": 0.08,
        "tier": "premium",
        "specialties": ["instruction_following", "complex_scenes", "text_in_image", "compositing"],
        "quality": 10,
        "supports_arabic_text": True,
    },
    "imagen_4_ultra": {
        "label": "Imagen 4 Ultra",
        "provider": "fal",
        "endpoint": "fal-ai/imagen4/preview/ultra",
        "price_usd": 0.06,
        "tier": "premium",
        "specialties": ["photorealistic", "text_in_image", "ultra_detail"],
        "quality": 10,
        "supports_arabic_text": True,
    },
    "flux_pro": {
        "label": "Flux 1.1 Pro",
        "provider": "fal",
        "endpoint": "fal-ai/flux-pro/v1.1",
        "price_usd": 0.04,
        "tier": "strong",
        "specialties": ["general", "concept_art", "daily_use", "speed"],
        "quality": 9,
        "supports_arabic_text": False,
    },
    "recraft_v3": {
        "label": "Recraft V3",
        "provider": "fal",
        "endpoint": "fal-ai/recraft-v3",
        "price_usd": 0.04,
        "tier": "strong",
        "specialties": ["logos", "vectors", "text_in_image", "arabic_text", "brand_design"],
        "quality": 9,
        "supports_arabic_text": True,
    },
    "ideogram_v3": {
        "label": "Ideogram V3",
        "provider": "fal",
        "endpoint": "fal-ai/ideogram/v3",
        "price_usd": 0.04,
        "tier": "strong",
        "specialties": ["arabic_text", "typography", "posters", "social_media"],
        "quality": 9,
        "supports_arabic_text": True,
    },
    "seedream_4": {
        "label": "Bytedance Seedream 4",
        "provider": "fal",
        "endpoint": "fal-ai/bytedance/seedream/v4/text-to-image",
        "price_usd": 0.025,
        "tier": "strong",
        "specialties": ["bulk", "ecommerce", "product_photos", "speed"],
        "quality": 8,
        "supports_arabic_text": False,
    },
}


# ════════════════════════════════════════════════════════════════════════
# VIDEO MODELS — pricing (USD per second of generated video)
# ════════════════════════════════════════════════════════════════════════
VIDEO_MODELS: Dict[str, Dict] = {
    "veo_3": {
        "label": "Google Veo 3",
        "provider": "fal",
        "endpoint": "fal-ai/veo3",
        "price_per_second": 0.50,
        "tier": "premium",
        "specialties": ["cinematic", "realistic", "advertising", "premium_brand"],
        "quality": 10,
        "max_duration": 8,
        "has_audio": True,
    },
    "sora_2": {
        "label": "OpenAI Sora 2",
        "provider": "openai",
        "endpoint": "sora-2",
        "price_per_second": 0.50,
        "tier": "premium",
        "specialties": ["cinematic", "storytelling", "narrative", "film"],
        "quality": 10,
        "max_duration": 20,
        "has_audio": True,
    },
    "kling_2_1_master": {
        "label": "Kling 2.1 Master",
        "provider": "fal",
        "endpoint": "fal-ai/kling-video/v2.1/master/text-to-video",
        "price_per_second": 0.28,
        "tier": "premium",
        "specialties": ["cinematic", "motion", "directing", "complex_scenes"],
        "quality": 10,
        "max_duration": 10,
        "has_audio": False,
    },
    "luma_ray_2": {
        "label": "Luma Ray 2",
        "provider": "fal",
        "endpoint": "fal-ai/luma-ray-2",
        "price_per_second": 0.30,
        "tier": "strong",
        "specialties": ["camera_motion", "smooth_motion", "transitions"],
        "quality": 9,
        "max_duration": 9,
        "has_audio": False,
    },
    "runway_gen4": {
        "label": "Runway Gen-4",
        "provider": "runway",
        "endpoint": "gen-4",
        "price_per_second": 0.25,
        "tier": "strong",
        "specialties": ["professional", "vfx", "compositing", "controllable"],
        "quality": 9,
        "max_duration": 10,
        "has_audio": False,
    },
    "minimax_hailuo_02": {
        "label": "Minimax Hailuo 02",
        "provider": "fal",
        "endpoint": "fal-ai/minimax/hailuo-02/standard/text-to-video",
        "price_per_second": 0.045,
        "tier": "strong",
        "specialties": ["social_media", "fast", "dynamic", "tiktok_youtube_shorts"],
        "quality": 8,
        "max_duration": 6,
        "has_audio": False,
    },
}


# ════════════════════════════════════════════════════════════════════════
# IMAGE EDIT MODELS — for "change only the rose color" style edits
# ════════════════════════════════════════════════════════════════════════
IMAGE_EDIT_MODELS: Dict[str, Dict] = {
    "nano_banana": {
        "label": "Nano Banana (Gemini Image)",
        "provider": "gemini",
        "endpoint": "gemini-2.5-flash-image-preview",
        "price_usd": 0.04,
        "tier": "premium",
        "specialties": ["smart_edit", "natural_language_edits", "preserve_composition"],
        "quality": 10,
    },
    "flux_kontext": {
        "label": "Flux Kontext Pro",
        "provider": "fal",
        "endpoint": "fal-ai/flux-pro/kontext",
        "price_usd": 0.05,
        "tier": "premium",
        "specialties": ["consistent_edit", "character_consistency", "iterative"],
        "quality": 10,
    },
    "gpt_image_edit": {
        "label": "GPT Image Edit",
        "provider": "openai",
        "endpoint": "gpt-image-1",
        "price_usd": 0.08,
        "tier": "premium",
        "specialties": ["precise_edit", "complex_instructions", "inpaint"],
        "quality": 10,
    },
}


# ════════════════════════════════════════════════════════════════════════
# VOICE MODELS — TTS (text-to-speech) + voice cloning
# ════════════════════════════════════════════════════════════════════════
VOICE_MODELS: Dict[str, Dict] = {
    "elevenlabs_v3": {
        "label": "ElevenLabs v3",
        "provider": "elevenlabs",
        "endpoint": "eleven_v3",
        "price_per_1k_chars": 0.30,
        "tier": "premium",
        "specialties": ["natural_voice", "voice_clone", "dialects", "arabic_dialects", "emotion"],
        "quality": 10,
        "languages": ["arabic", "saudi", "khaleeji", "egyptian", "english", "100+ langs"],
    },
    "openai_tts_hd": {
        "label": "OpenAI TTS HD",
        "provider": "openai",
        "endpoint": "tts-1-hd",
        "price_per_1k_chars": 0.030,
        "tier": "strong",
        "specialties": ["natural_voice", "fast", "multilingual"],
        "quality": 9,
        "languages": ["english", "arabic", "many"],
    },
}


# ════════════════════════════════════════════════════════════════════════
# Task detection — figure out the user's intent from prompt
# ════════════════════════════════════════════════════════════════════════
def detect_image_intent(prompt: str, options: Optional[Dict] = None) -> List[str]:
    """Return list of matching specialty tags for the user's image request."""
    p = (prompt or "").lower()
    tags: List[str] = []

    patterns = {
        "luxury":           [r"\bluxury\b", r"\bفاخر", r"\bعطر", r"\bperfume", r"\bجوهر", r"\bsaph", r"\bgold\b", r"ذهب"],
        "product_ads":      [r"\bإعلان", r"\bمنتج", r"\bproduct\b", r"\bad\b", r"\bcommercial\b", r"\bbranding\b"],
        "photorealistic":   [r"\bواقعي", r"\bفوتوغراف", r"\brealistic\b", r"\bphoto", r"\b8k\b", r"\bhdr\b"],
        "portraits":        [r"\bبورتري", r"\bportrait\b", r"\bوجه\b", r"\bface\b"],
        "fashion":          [r"\bأزياء", r"\bfashion\b", r"\bmodel\b", r"\bموديل"],
        "logos":            [r"\bشعار", r"\blogo\b", r"\bbrand mark\b", r"\bعلامة تجارية"],
        "arabic_text":      [r"اكتب.*بالعربي.*صورة", r"\bعربي.*داخل", r"شعار عربي", r"عنوان عربي.*صورة"],
        "text_in_image":    [r"\btext in\b", r"\bwith text\b", r"poster.*saying", r"عنوان", r"\btypography\b"],
        "posters":          [r"\bبوستر", r"\bposter\b", r"\bملصق"],
        "social_media":     [r"\bسوشال", r"\bsocial\b", r"\binstagram\b", r"\btiktok\b", r"\bسناب"],
        "concept_art":      [r"\bconcept art\b", r"\billustration\b", r"\bرسم"],
        "ecommerce":        [r"\bمتجر", r"\becommerce\b", r"\bproduct catalog\b", r"\bامازون", r"\bسلة"],
        "bulk":             [r"\b\d{2,}\s*صورة", r"\bbulk\b", r"\bbatch\b", r"كميات"],
        "instruction_following": [r"\bخطوات", r"\bمعقد", r"\bcomplex\b", r"\bdetailed.*instructions\b"],
    }

    for tag, pats in patterns.items():
        if any(re.search(p_, p) for p_ in pats):
            tags.append(tag)

    if not tags:
        tags = ["general"]
    return tags


def detect_video_intent(prompt: str, duration_seconds: int = 5) -> List[str]:
    """Return list of matching specialty tags for video request."""
    p = (prompt or "").lower()
    tags: List[str] = []
    patterns = {
        "cinematic":     [r"\bسينمائي", r"\bcinematic\b", r"\bfilm\b", r"\bhollywood\b", r"\b4k\b"],
        "realistic":     [r"\bواقعي", r"\brealistic\b", r"\bdocumentary\b"],
        "advertising":   [r"\bإعلان", r"\bad\b", r"\bcommercial\b", r"\bbrand video\b"],
        "narrative":     [r"\bقصة", r"\bstory\b", r"\bnarrative\b", r"\bplot\b"],
        "social_media":  [r"\bسوشال", r"\btiktok\b", r"\binstagram\b", r"\breel\b", r"\bسناب"],
        "fast":          [r"\bسريع", r"\bquick\b", r"\bfast\b", r"\bمسودة"],
        "camera_motion": [r"\bcamera movement\b", r"\bحركة كاميرا", r"\bdolly\b", r"\borbit\b"],
        "vfx":           [r"\bvfx\b", r"\bمؤثرات\b", r"\beffects\b"],
        "dynamic":       [r"\bديناميكي", r"\bdynamic\b", r"\baction\b", r"\bحركة سريعة"],
    }
    for tag, pats in patterns.items():
        if any(re.search(p_, p) for p_ in pats):
            tags.append(tag)
    if not tags:
        tags = ["cinematic"]  # default to highest quality intent
    return tags


# ════════════════════════════════════════════════════════════════════════
# Availability — which keys are configured
# ════════════════════════════════════════════════════════════════════════
def media_availability() -> Dict[str, bool]:
    return {
        "fal":        bool(os.environ.get("FAL_KEY", "") or os.environ.get("FAL_API_KEY", "")),
        "openai":     bool(os.environ.get("OPENAI_API_KEY", "") or os.environ.get("OPENAI_DIRECT_KEY", "")),
        "gemini":     bool(os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")),
        "elevenlabs": bool(os.environ.get("ELEVENLABS_API_KEY", "")),
        "runway":     bool(os.environ.get("RUNWAY_API_KEY", "")),
    }


# ════════════════════════════════════════════════════════════════════════
# Quality-first pickers
# ════════════════════════════════════════════════════════════════════════
def pick_image_model(prompt: str,
                     priority: str = "quality",
                     options: Optional[Dict] = None) -> Dict:
    """
    Pick best image model for the prompt.

    priority:
      - "quality" (default) : Always pick highest quality available
      - "balanced"          : Quality primary, price tiebreak
      - "cost_aware"        : Among Premium+Strong, choose cheaper if quality close
    """
    tags = detect_image_intent(prompt, options)
    avail = media_availability()

    # Score each model
    scored: List[Tuple[str, int, float]] = []
    for key, m in IMAGE_MODELS.items():
        if not avail.get(m["provider"], False):
            continue
        # Match score: +2 per matching specialty, base = quality
        match_bonus = sum(2 for t in tags if t in m["specialties"])
        # Arabic text required?
        if "arabic_text" in tags and not m.get("supports_arabic_text"):
            continue
        score = m["quality"] * 10 + match_bonus
        scored.append((key, score, m["price_usd"]))

    if not scored:
        return {"model_key": None, "error": "no_image_provider_available",
                "message": "أضف FAL_KEY أو OPENAI_API_KEY أو GEMINI_API_KEY"}

    if priority == "quality":
        # Highest score first, then cheapest as tiebreak
        scored.sort(key=lambda x: (-x[1], x[2]))
    elif priority == "balanced":
        # Subtract price penalty
        scored.sort(key=lambda x: (-(x[1] - x[2] * 50), x[2]))
    else:  # cost_aware
        scored.sort(key=lambda x: (x[2], -x[1]))

    best_key = scored[0][0]
    model = IMAGE_MODELS[best_key]
    return {
        "model_key": best_key,
        "label": model["label"],
        "provider": model["provider"],
        "endpoint": model["endpoint"],
        "price_usd": model["price_usd"],
        "quality": model["quality"],
        "tier": model["tier"],
        "matched_specialties": [t for t in tags if t in model["specialties"]],
        "intent_tags": tags,
        "fallbacks": [s[0] for s in scored[1:4]],
        "reason": _image_reason(best_key, tags),
    }


def pick_video_model(prompt: str,
                     duration_seconds: int = 5,
                     priority: str = "quality") -> Dict:
    """Pick best video model for the prompt."""
    tags = detect_video_intent(prompt, duration_seconds)
    avail = media_availability()

    scored: List[Tuple[str, int, float]] = []
    for key, m in VIDEO_MODELS.items():
        if not avail.get(m["provider"], False):
            continue
        if duration_seconds > m["max_duration"]:
            continue
        match_bonus = sum(2 for t in tags if t in m["specialties"])
        score = m["quality"] * 10 + match_bonus
        cost_for_clip = m["price_per_second"] * duration_seconds
        scored.append((key, score, cost_for_clip))

    if not scored:
        return {"model_key": None, "error": "no_video_provider_available",
                "message": "أضف FAL_KEY أو OPENAI_API_KEY"}

    if priority == "quality":
        scored.sort(key=lambda x: (-x[1], x[2]))
    elif priority == "balanced":
        scored.sort(key=lambda x: (-(x[1] - x[2] * 5), x[2]))
    else:
        scored.sort(key=lambda x: (x[2], -x[1]))

    best_key = scored[0][0]
    m = VIDEO_MODELS[best_key]
    return {
        "model_key": best_key,
        "label": m["label"],
        "provider": m["provider"],
        "endpoint": m["endpoint"],
        "price_per_second": m["price_per_second"],
        "cost_for_clip": round(m["price_per_second"] * duration_seconds, 3),
        "quality": m["quality"],
        "tier": m["tier"],
        "has_audio": m["has_audio"],
        "matched_specialties": [t for t in tags if t in m["specialties"]],
        "intent_tags": tags,
        "fallbacks": [s[0] for s in scored[1:4]],
        "reason": _video_reason(best_key, tags),
    }


def pick_image_edit_model(prompt: str = "", priority: str = "quality") -> Dict:
    """Pick best image-edit model. Default: Nano Banana for natural edits."""
    avail = media_availability()
    p = (prompt or "").lower()
    preferred_order = []
    # Iterative / consistency edits → Flux Kontext
    if any(k in p for k in ["consistent", "iterative", "same character", "نفس الشخصية"]):
        preferred_order = ["flux_kontext", "nano_banana", "gpt_image_edit"]
    # Complex multi-step instructions → GPT Image Edit
    elif any(k in p for k in ["complex", "detailed", "step", "خطوة"]):
        preferred_order = ["gpt_image_edit", "nano_banana", "flux_kontext"]
    else:
        # Natural language tweaks → Nano Banana (default)
        preferred_order = ["nano_banana", "flux_kontext", "gpt_image_edit"]

    for key in preferred_order:
        m = IMAGE_EDIT_MODELS[key]
        if avail.get(m["provider"], False):
            return {
                "model_key": key,
                "label": m["label"],
                "provider": m["provider"],
                "endpoint": m["endpoint"],
                "price_usd": m["price_usd"],
                "quality": m["quality"],
                "reason": _edit_reason(key),
            }
    return {"model_key": None, "error": "no_edit_provider_available",
            "message": "أضف GEMINI_API_KEY أو FAL_KEY أو OPENAI_API_KEY"}


def pick_voice_model(text: str = "", priority: str = "quality") -> Dict:
    """Pick best voice/TTS model. Default to ElevenLabs for natural dialects."""
    avail = media_availability()
    p = (text or "").lower()

    # Arabic / dialect / cloning → ElevenLabs is mandatory
    needs_dialect = any(k in p for k in ["سعودي", "خليجي", "مصري", "شامي", "لهجة", "dialect", "clone"])

    if avail.get("elevenlabs"):
        m = VOICE_MODELS["elevenlabs_v3"]
        return {
            "model_key": "elevenlabs_v3",
            "label": m["label"],
            "provider": m["provider"],
            "endpoint": m["endpoint"],
            "price_per_1k_chars": m["price_per_1k_chars"],
            "quality": m["quality"],
            "reason": "ElevenLabs v3 — الأفضل عالمياً للأصوات الطبيعية واللهجات",
        }

    if needs_dialect and not avail.get("elevenlabs"):
        return {"model_key": None, "error": "elevenlabs_required",
                "message": "للهجات العربية الطبيعية، أضف ELEVENLABS_API_KEY"}

    if avail.get("openai"):
        m = VOICE_MODELS["openai_tts_hd"]
        return {
            "model_key": "openai_tts_hd",
            "label": m["label"],
            "provider": m["provider"],
            "endpoint": m["endpoint"],
            "price_per_1k_chars": m["price_per_1k_chars"],
            "quality": m["quality"],
            "reason": "OpenAI TTS HD — صوت طبيعي بسعر منخفض",
        }
    return {"model_key": None, "error": "no_voice_provider",
            "message": "أضف ELEVENLABS_API_KEY أو OPENAI_API_KEY"}


# ════════════════════════════════════════════════════════════════════════
# Reasoning strings (UI explanations)
# ════════════════════════════════════════════════════════════════════════
def _image_reason(key: str, tags: List[str]) -> str:
    matched = ", ".join(tags) if tags else "general"
    reasons = {
        "flux_pro_ultra": f"Flux Pro Ultra — الأفضل للصور الفاخرة والواقعية ({matched})",
        "gpt_image_1":    f"GPT Image 1 — أعلى دقة في تنفيذ التعليمات المعقدة ({matched})",
        "imagen_4_ultra": f"Imagen 4 Ultra — واقعية ودعم نصوص في الصورة ({matched})",
        "flux_pro":       f"Flux Pro 1.1 — جودة عالية للاستخدام اليومي ({matched})",
        "recraft_v3":     f"Recraft V3 — متخصص الشعارات والنصوص داخل الصورة ({matched})",
        "ideogram_v3":    f"Ideogram V3 — الأفضل للنصوص العربية في التصاميم ({matched})",
        "seedream_4":     f"Seedream 4 — جودة احترافية بسعر منخفض ({matched})",
    }
    return reasons.get(key, f"{key} متاح ومناسب")


def _video_reason(key: str, tags: List[str]) -> str:
    matched = ", ".join(tags) if tags else "general"
    reasons = {
        "veo_3":            f"Google Veo 3 — الأفضل عالمياً في الفيديو السينمائي ({matched})",
        "sora_2":           f"Sora 2 — قصصي سينمائي مع صوت ({matched})",
        "kling_2_1_master": f"Kling 2.1 Master — إخراج سينمائي وحركة معقدة ({matched})",
        "luma_ray_2":       f"Luma Ray 2 — حركة كاميرا ناعمة ({matched})",
        "runway_gen4":      f"Runway Gen-4 — احترافي ومرن للـ VFX ({matched})",
        "minimax_hailuo_02": f"Minimax Hailuo — ديناميكي للسوشال ميديا ({matched})",
    }
    return reasons.get(key, f"{key} متاح ومناسب")


def _edit_reason(key: str) -> str:
    reasons = {
        "nano_banana":    "Nano Banana — يفهم 'غيّر فقط لون الورد' بدون لمس الباقي",
        "flux_kontext":   "Flux Kontext — يحافظ على الشخصية والتركيب عبر التعديلات",
        "gpt_image_edit": "GPT Image Edit — تنفيذ تعليمات معقدة بدقة",
    }
    return reasons.get(key, key)


# ════════════════════════════════════════════════════════════════════════
# Public catalog for the admin UI
# ════════════════════════════════════════════════════════════════════════
def catalog() -> Dict:
    """Return full catalog for admin dashboard."""
    avail = media_availability()
    return {
        "image": [
            {**m, "key": k, "available": avail.get(m["provider"], False)}
            for k, m in IMAGE_MODELS.items()
        ],
        "video": [
            {**m, "key": k, "available": avail.get(m["provider"], False)}
            for k, m in VIDEO_MODELS.items()
        ],
        "image_edit": [
            {**m, "key": k, "available": avail.get(m["provider"], False)}
            for k, m in IMAGE_EDIT_MODELS.items()
        ],
        "voice": [
            {**m, "key": k, "available": avail.get(m["provider"], False)}
            for k, m in VOICE_MODELS.items()
        ],
        "availability": avail,
        "philosophy": "الجودة أولاً. السعر ثاني. ممنوع أي موديل أقل من المستوى Strong.",
    }
