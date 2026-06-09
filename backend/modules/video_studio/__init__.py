"""
Video Studio v2.1 — Multi-stage cinematic workflow with series memory.

Pipeline (FREE except RENDER):
  CHAT → SCRIPT → STORYBOARD → APPROVE → RENDER → SHARE

Key features:
  • Series memory (video_series + video_episodes).
  • Free until render.
  • Owner-controlled keys ONLY — never falls back to EMERGENT_LLM_KEY for
    paid operations (storyboard images + Sora 2 render). If the owner has
    not configured their own OPENAI_DIRECT_KEY in env or vault, the
    operation errors with a clear message rather than billing the platform.
  • Multi-language scripts: AR (saudi, egyptian, kuwaiti, gulf), EN, JA, FR, etc.
  • Optional Arabic subtitle even when the speech is non-Arabic.
  • Aspect ratio per platform (16:9 / 9:16 for TikTok/Reels).
  • Public share URL + auto-generated TikTok/IG captions.
"""
from __future__ import annotations
import os
import re
import json
import uuid
import base64
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ════════════════════════════════════════════════════════════════════════
# PRICING — credits only billed at render step.
# Customer picks duration; longer = more credits. We allow up to 120s custom.
# ════════════════════════════════════════════════════════════════════════
PRICE_TIERS = [
    {"max_seconds": 15,  "credits": 25,  "label": "15 ثانية"},
    {"max_seconds": 30,  "credits": 45,  "label": "30 ثانية"},
    {"max_seconds": 45,  "credits": 65,  "label": "45 ثانية"},
    {"max_seconds": 60,  "credits": 85,  "label": "دقيقة"},
    {"max_seconds": 90,  "credits": 130, "label": "دقيقة ونصف"},
    {"max_seconds": 120, "credits": 175, "label": "دقيقتين"},
]
PRICE_PER_SECOND_OVER_120 = 1.6  # credits/sec for ultra-long custom durations


def shot_price(duration_seconds: int) -> int:
    d = max(4, int(duration_seconds or 8))
    for tier in PRICE_TIERS:
        if d <= tier["max_seconds"]:
            return tier["credits"]
    # >120s — linear scaling
    extra = d - 120
    return int(PRICE_TIERS[-1]["credits"] + extra * PRICE_PER_SECOND_OVER_120)


# ════════════════════════════════════════════════════════════════════════
# LANGUAGE / DIALECT / ART STYLE catalogues — surfaced to the frontend
# ════════════════════════════════════════════════════════════════════════
LANGUAGE_OPTIONS = [
    {"id": "ar-saudi",    "label": "عربي — سعودي",    "for_voice": "ar-SA"},
    {"id": "ar-egyptian", "label": "عربي — مصري",     "for_voice": "ar-EG"},
    {"id": "ar-kuwaiti",  "label": "عربي — كويتي",    "for_voice": "ar-KW"},
    {"id": "ar-gulf",     "label": "عربي — خليجي",    "for_voice": "ar-SA"},
    {"id": "ar-msa",      "label": "عربي فصيح",       "for_voice": "ar-XA"},
    {"id": "en-us",       "label": "English",         "for_voice": "en-US"},
    {"id": "ja-jp",       "label": "日本語 Japanese", "for_voice": "ja-JP"},
    {"id": "fr-fr",       "label": "Français",        "for_voice": "fr-FR"},
    {"id": "es-es",       "label": "Español",         "for_voice": "es-ES"},
    {"id": "tr-tr",       "label": "Türkçe",          "for_voice": "tr-TR"},
    {"id": "ur-pk",       "label": "اردو Urdu",        "for_voice": "ur-PK"},
]

ART_STYLES = [
    {"id": "hyperreal",     "label": "واقعي تماماً (لا يُفرّق عن الحقيقي)",
     "prompt_seed": (
         "Shot on ARRI Alexa 65, anamorphic 35mm lenses, natural sunlight, "
         "subtle film grain, real human actors, documentary cinematography, "
         "photorealistic, indistinguishable from real footage, NO CGI look, "
         "no artificial smoothing, no oversaturation, no anime, no illustration, "
         "no 3D rendering, real-world physics"
     )},
    {"id": "cinematic",     "label": "سينمائي واقعي",  "prompt_seed": "Cinematic 35mm film, natural lighting, shallow depth of field"},
    {"id": "anime",         "label": "أنمي",            "prompt_seed": "Modern Japanese anime style, vibrant colors, expressive eyes, Studio Ghibli mood"},
    {"id": "3d_animation",  "label": "أنيمشن ثلاثي الأبعاد", "prompt_seed": "Pixar-style 3D animation, soft global illumination, expressive characters"},
    {"id": "photoreal",     "label": "صور واقعية",      "prompt_seed": "Photorealistic, sharp detail, professional photography"},
    {"id": "cartoon",       "label": "كرتون",           "prompt_seed": "2D flat cartoon, bold outlines, saturated palette"},
    {"id": "watercolor",    "label": "ألوان مائية",     "prompt_seed": "Watercolor painting, soft washes, paper texture"},
    {"id": "oil",           "label": "زيتية",           "prompt_seed": "Oil painting, rich impasto strokes, classical chiaroscuro"},
    {"id": "noir",          "label": "نوار أبيض/أسود",  "prompt_seed": "Black and white film noir, deep shadows, smoke and fog"},
    {"id": "cyberpunk",     "label": "سايبربانك",       "prompt_seed": "Neon cyberpunk, rain-soaked streets, magenta and cyan glow"},
    {"id": "documentary",   "label": "وثائقي",          "prompt_seed": "Documentary handheld camera, natural light, observational framing"},
]

GENRES = [
    {"id": "drama",        "label": "درامي"},
    {"id": "comedy",       "label": "كوميدي"},
    {"id": "action",       "label": "أكشن"},
    {"id": "documentary",  "label": "وثائقي"},
    {"id": "educational",  "label": "تعليمي"},
    {"id": "advertising",  "label": "إعلاني"},
    {"id": "horror",       "label": "رعب"},
    {"id": "romance",      "label": "رومنسي"},
]

ASPECT_RATIOS = [
    {"id": "16x9", "label": "16:9 — يوتيوب / تلفزيون", "size": "1280x720"},
    {"id": "9x16", "label": "9:16 — تيك توك / ريلز / شورتس", "size": "720x1280"},
    {"id": "1x1",  "label": "1:1 — إنستقرام (مربع)",   "size": "1024x1024"},
]


# ════════════════════════════════════════════════════════════════════════
# OWNER KEYS — explicitly NOT EMERGENT_LLM_KEY. The owner is billed via
# their own OpenAI / Gemini accounts. If keys are missing we fail loudly.
# ════════════════════════════════════════════════════════════════════════
def _owner_openai_key() -> str:
    """Return the owner's OpenAI key from env or vault (NEVER EMERGENT)."""
    k = (os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    if k and k.startswith("sk-"):
        return k
    try:
        from modules.autocoder.credentials_vault import vault_get  # type: ignore
        for name in ("OPENAI_DIRECT_KEY", "OPENAI_API_KEY"):
            v = (vault_get(name) or "").strip()
            if v and v.startswith("sk-"):
                return v
    except Exception:
        pass
    return ""


def _owner_gemini_key() -> str:
    k = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if k:
        return k
    try:
        from modules.autocoder.credentials_vault import vault_get  # type: ignore
        for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            v = (vault_get(name) or "").strip()
            if v:
                return v
    except Exception:
        pass
    return ""


# ════════════════════════════════════════════════════════════════════════
# Pydantic schemas
# ════════════════════════════════════════════════════════════════════════
class ChatIn(BaseModel):
    session_id: Optional[str] = None
    series_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=12000)


class SeriesCreateIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    description: str = ""
    style_direction: str = ""
    main_characters: List[Dict[str, str]] = []


class ScriptIn(BaseModel):
    session_id: str
    series_id: Optional[str] = None
    brief: str = Field(..., min_length=4)
    episode_number: Optional[int] = None
    requested_shots: int = Field(default=4, ge=1, le=24)
    shot_duration: int = Field(default=15, ge=4, le=300)
    language: str = Field(default="ar-saudi")
    dialect_notes: str = ""
    subtitle_language: str = ""            # "" = no subtitle; else target lang id
    art_style: str = Field(default="cinematic")
    genre: str = Field(default="drama")
    aspect_ratio: str = Field(default="16x9")
    voice_gender: str = Field(default="male")
    extra_directives: str = ""


class StoryboardIn(BaseModel):
    episode_id: str


class ApproveIn(BaseModel):
    episode_id: str
    confirmed: bool = True


class RenderIn(BaseModel):
    episode_id: str


class ShareIn(BaseModel):
    episode_id: str
    slug: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════
# Script LLM — uses owner's OpenAI key only (never Emergent)
# ════════════════════════════════════════════════════════════════════════
def _build_script_system(language: str, subtitle_language: str, art_style: str, genre: str,
                         voice_gender: str, dialect_notes: str) -> str:
    lang = next((x for x in LANGUAGE_OPTIONS if x["id"] == language), LANGUAGE_OPTIONS[0])
    sub = next((x for x in LANGUAGE_OPTIONS if x["id"] == subtitle_language), None)
    art = next((x for x in ART_STYLES if x["id"] == art_style), ART_STYLES[0])
    gen = next((x for x in GENRES if x["id"] == genre), GENRES[0])

    subtitle_block = ""
    if sub and sub["id"] != lang["id"]:
        subtitle_block = (
            f"\nIMPORTANT: dialogue must be authored in {lang['label']} "
            f"but each shot MUST include a `subtitle_translation` field translating "
            f"the dialogue into {sub['label']} for on-screen subtitles."
        )

    return (
        "أنت مخرج سينمائي محترف. مهمتك تحويل فكرة العميل إلى سيناريو منظّم. "
        "أرجع JSON صالح فقط — بدون نص خارج JSON. الـschema:\n"
        "{\n"
        '  "title": "string",\n'
        '  "logline": "string (one sentence)",\n'
        '  "characters": [{"name": "string", "desc": "visual description (hair/clothes/age/mood)"}],\n'
        '  "style": "string (English cinematic style: lighting + color + camera)",\n'
        f'  "language": "{lang["id"]}",\n'
        '  "shots": [\n'
        "    {\n"
        '      "n": 1,\n'
        '      "title_ar": "shot title in Arabic",\n'
        '      "scenario_ar": "internal description of what happens in this shot, in Arabic",\n'
        '      "dialogue": "the line a character or narrator says — written in the target language",\n'
        '      "dialogue_speaker": "name of character / narrator / null",\n'
        '      "subtitle_translation": "Arabic translation of dialogue if user requested subtitles, else empty string",\n'
        '      "visual_en": "Cinematic English prompt for image/video generation",\n'
        '      "duration": 8\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"Target dialogue language: {lang['label']} ({lang['for_voice']}).\n"
        f"{('Dialect notes: ' + dialect_notes) if dialect_notes else ''}\n"
        f"Art style: {art['label']} — bake into every shot's visual_en: '{art['prompt_seed']}'.\n"
        f"Genre: {gen['label']}.\n"
        f"Primary voice gender: {voice_gender}.\n"
        f"{subtitle_block}\n"
        "Return JSON only."
    )


async def _generate_script(brief: str, *, series_ctx: Optional[Dict[str, Any]] = None,
                           requested_shots: int = 4, shot_duration: int = 8,
                           language: str = "ar-saudi", dialect_notes: str = "",
                           subtitle_language: str = "", art_style: str = "cinematic",
                           genre: str = "drama", voice_gender: str = "male",
                           extra_directives: str = "") -> Dict[str, Any]:
    sys_prompt = _build_script_system(language, subtitle_language, art_style, genre,
                                      voice_gender, dialect_notes)

    extra_ctx = ""
    if series_ctx:
        extra_ctx = (
            "\n\n📌 Series context (keep consistent):\n"
            + json.dumps(series_ctx, ensure_ascii=False)[:1500]
        )

    user_prompt = (
        f"العميل يقول:\n{brief}\n\n"
        f"عدد اللقطات المطلوبة: {requested_shots}\n"
        f"مدة كل لقطة (تقريباً): {shot_duration} ثانية\n"
        f"{('توجيهات إضافية: ' + extra_directives) if extra_directives else ''}"
        f"{extra_ctx}\n\nأعد JSON فقط."
    )

    key = _owner_openai_key()
    if not key:
        raise HTTPException(
            400,
            "ما فيه مفتاح OpenAI خاص بك. ادخل على /admin/independence وأضف "
            "OPENAI_DIRECT_KEY عشان ما يتم الخصم من حساب المنصة.",
        )

    try:
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 3500,
                },
            )
            if r.status_code != 200:
                raise HTTPException(503, f"OpenAI رفض الطلب: {r.text[:200]}")
            raw = r.json()["choices"][0]["message"]["content"]
            return json.loads(raw)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"script gen failed: {e}")
        raise HTTPException(503, f"تعذّر توليد السيناريو: {str(e)[:200]}")


# ════════════════════════════════════════════════════════════════════════
# Storyboard images — owner's OpenAI key
# ════════════════════════════════════════════════════════════════════════
STORYBOARD_DIR = Path("/app/backend/static/video_storyboards")
STORYBOARD_DIR.mkdir(parents=True, exist_ok=True)


def _aspect_to_size(aspect: str) -> str:
    a = next((x for x in ASPECT_RATIOS if x["id"] == aspect), ASPECT_RATIOS[0])
    return a["size"]


async def _gen_storyboard_image(prompt: str, *, style_seed: str = "",
                                aspect: str = "16x9") -> Optional[str]:
    key = _owner_openai_key()
    if not key:
        return None
    full = prompt.strip()
    if style_seed:
        full = f"{full}. {style_seed}. High detail, professional lighting."
    # gpt-image-1 only supports specific sizes; map our aspect into one
    size_map = {"16x9": "1536x1024", "9x16": "1024x1536", "1x1": "1024x1024"}
    size = size_map.get(aspect, "1536x1024")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": "gpt-image-1", "prompt": full[:3500], "size": size, "n": 1},
            )
            if r.status_code != 200:
                logger.warning(f"image gen failed {r.status_code}: {r.text[:200]}")
                return None
            data = r.json().get("data", [{}])[0]
            # OpenAI returns either url or b64_json
            if data.get("b64_json"):
                img_bytes = base64.b64decode(data["b64_json"])
            elif data.get("url"):
                async with httpx.AsyncClient(timeout=60.0) as c2:
                    rr = await c2.get(data["url"])
                    img_bytes = rr.content
            else:
                return None
            fname = f"{uuid.uuid4().hex}.png"
            (STORYBOARD_DIR / fname).write_bytes(img_bytes)
            return f"/api/video-studio/storyboard-img/{fname}"
    except Exception as e:
        logger.warning(f"storyboard image error: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════
# Sora 2 render — owner's OpenAI key (never EMERGENT_LLM_KEY)
# ════════════════════════════════════════════════════════════════════════
async def _render_shot(prompt: str, duration: int, *, aspect: str = "16x9") -> Dict[str, Any]:
    """Render via Sora 2. Sora 2 only supports 4/8/12 second clips, so for
    longer durations we split into multiple sub-clips and concat as a list.
    Returns {ok, clips: [data_url, ...], error?}. Captures full error
    details so the frontend can surface them.
    """
    key = _owner_openai_key()
    if not key:
        return {"ok": False, "clips": [], "error": "no_openai_key"}
    try:
        from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration  # type: ignore
    except Exception as e:
        return {"ok": False, "clips": [], "error": f"sora_lib_missing: {e}"}
    size = _aspect_to_size(aspect)
    if size not in ("1280x720", "720x1280"):
        size = "1280x720"

    # Sora 2 supports 4, 8, 12 seconds — split longer durations
    target = max(4, int(duration or 8))
    plan: List[int] = []
    remaining = target
    while remaining > 0:
        chunk = 12 if remaining >= 12 else (8 if remaining >= 8 else 4)
        plan.append(chunk)
        remaining -= chunk
    # cap to 6 sub-clips to avoid runaway costs
    plan = plan[:6]

    gen = OpenAIVideoGeneration(api_key=key)
    clips: List[str] = []
    last_error: Optional[str] = None
    for sub_dur in plan:
        try:
            video_bytes = gen.text_to_video(
                prompt=prompt, model="sora-2",
                size=size, duration=sub_dur, max_wait_time=900,
            )
            if video_bytes:
                clips.append("data:video/mp4;base64," + base64.b64encode(video_bytes).decode("utf-8"))
            else:
                last_error = "empty_response_from_sora"
        except Exception as e:
            last_error = f"{type(e).__name__}: {str(e)[:240]}"
            logger.error(f"sora sub-clip failed (duration={sub_dur}): {last_error}")
            break  # don't retry the rest if one failed (likely an auth/access issue)
    if not clips:
        return {"ok": False, "clips": [], "error": last_error or "no_clips_produced"}
    return {"ok": True, "clips": clips, "error": last_error}


# ════════════════════════════════════════════════════════════════════════
# Social share captions — built locally (no API call)
# ════════════════════════════════════════════════════════════════════════
def _social_captions(script: Dict[str, Any]) -> Dict[str, str]:
    title = (script.get("title") or "").strip() or "حلقة جديدة من زيتاكس"
    logline = (script.get("logline") or "").strip()
    hashtags = "#زيتاكس #فيديو_بالذكاء_الاصطناعي #ai #zerax"
    return {
        "tiktok": f"{title}\n{logline}\n\n{hashtags} #fyp #tiktok",
        "instagram": f"{title}\n{logline}\n\n{hashtags} #reels #instagram",
        "twitter": f"{title} — {logline}\n\n{hashtags}",
        "youtube": f"{title}\n\n{logline}\n\n{hashtags}",
        "snapchat": f"{title}\n{logline}",
    }


class ProductionAssetIn(BaseModel):
    series_id: str = Field(..., min_length=1)
    kind: str = Field(..., description="character|villain|location|prop|vehicle")
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(..., min_length=4, max_length=2000)
    art_style: str = Field(default="hyperreal")
    attributes: Dict[str, Any] = {}


class RelationshipIn(BaseModel):
    series_id: str
    from_asset_id: str
    to_asset_id: str
    kind: str = Field(..., description="loves|hates|allies|enemies|family|mentor|rival")
    notes: str = ""


class ProducerChatIn(BaseModel):
    series_id: str
    step: str = Field(..., description="discover|villains|heroes|locations|relationships|ready")
    message: str = ""


# ════════════════════════════════════════════════════════════════════════
# Router factory
# ════════════════════════════════════════════════════════════════════════
def create_video_studio_router(db, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/api/video-studio", tags=["video-studio"])

    try:
        from modules.shared import bind_db as _shared_bind, SectionAgent
        _shared_bind(db)
    except Exception as e:
        logger.warning(f"shared bind failed: {e}")
        SectionAgent = None  # type: ignore

    async def _get_credits(user_id: str) -> int:
        d = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
        return int((d or {}).get("credits", 0))

    # ── Catalogues ─────────────────────────────────────────────────────
    @router.get("/options")
    async def options(_=Depends(get_current_user)):
        return {
            "ok": True,
            "languages": LANGUAGE_OPTIONS,
            "art_styles": ART_STYLES,
            "genres": GENRES,
            "aspect_ratios": ASPECT_RATIOS,
            "voice_genders": [{"id": "male", "label": "ذكر"}, {"id": "female", "label": "أنثى"}],
            "duration_tiers": [
                {"seconds": t["max_seconds"], "credits": t["credits"], "label": t["label"]}
                for t in PRICE_TIERS
            ],
            "price_per_second_over_120": PRICE_PER_SECOND_OVER_120,
            "owner_key_configured": bool(_owner_openai_key()),
            "openai_keys_url": "https://platform.openai.com/api-keys",
            "openai_billing_url": "https://platform.openai.com/account/billing/overview",
            "sora_access_url": "https://sora.com/onboarding",
        }

    # ── Series CRUD ────────────────────────────────────────────────────
    @router.get("/series")
    async def list_series(user=Depends(get_current_user)):
        cur = db.video_series.find({"user_id": user["user_id"]}, {"_id": 0}).sort([("updated_at", -1)]).limit(50)
        items = await cur.to_list(50)
        for s in items:
            s["episode_count"] = await db.video_episodes.count_documents({"series_id": s["id"]})
        return {"ok": True, "series": items}

    @router.post("/series/create")
    async def create_series(payload: SeriesCreateIn, user=Depends(get_current_user)):
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "title": payload.title,
            "description": payload.description,
            "style_direction": payload.style_direction,
            "main_characters": payload.main_characters,
            "created_at": _now(),
            "updated_at": _now(),
        }
        await db.video_series.insert_one(doc.copy())
        return {"ok": True, "series": {k: v for k, v in doc.items() if k != "_id"}}

    @router.get("/series/{series_id}/episodes")
    async def list_episodes(series_id: str, user=Depends(get_current_user)):
        cur = db.video_episodes.find(
            {"series_id": series_id, "user_id": user["user_id"]}, {"_id": 0}
        ).sort([("episode_number", 1)]).limit(100)
        eps = await cur.to_list(100)
        return {"ok": True, "episodes": eps}

    # ── Chat (uses SectionAgent for free conversational guidance) ──────
    @router.post("/chat")
    async def chat(payload: ChatIn, user=Depends(get_current_user)):
        if SectionAgent is None:
            raise HTTPException(503, "shared agent core not available")
        extra = ""
        if payload.series_id:
            s = await db.video_series.find_one({"id": payload.series_id, "user_id": user["user_id"]}, {"_id": 0})
            if s:
                eps_count = await db.video_episodes.count_documents({"series_id": s["id"]})
                extra = (
                    f"\n\n📺 المستخدم يعمل على سلسلة '{s.get('title')}' "
                    f"(الحلقة {eps_count + 1}). الستايل: {s.get('style_direction') or 'غير محدد'}. "
                    f"الشخصيات: {json.dumps(s.get('main_characters', []), ensure_ascii=False)}. "
                    "حافظ على نفس الـlook بين الحلقات."
                )
        agent = SectionAgent("video", extra_persona=extra)
        return await agent.chat(user["user_id"], payload.message, session_id=payload.session_id or "")

    # ── Script generation (FREE) ───────────────────────────────────────
    @router.post("/script")
    async def gen_script(payload: ScriptIn, user=Depends(get_current_user)):
        series_ctx: Optional[Dict[str, Any]] = None
        ep_num = payload.episode_number or 1
        if payload.series_id:
            s = await db.video_series.find_one(
                {"id": payload.series_id, "user_id": user["user_id"]}, {"_id": 0}
            )
            if not s:
                raise HTTPException(404, "series not found")
            cur = db.video_episodes.find(
                {"series_id": s["id"]}, {"_id": 0, "episode_number": 1, "script": 1}
            ).sort([("episode_number", -1)]).limit(3)
            prior = await cur.to_list(3)
            series_ctx = {
                "title": s.get("title"),
                "style_direction": s.get("style_direction"),
                "main_characters": s.get("main_characters", []),
                "prior_episodes": [
                    {"n": p.get("episode_number"), "logline": (p.get("script") or {}).get("logline")}
                    for p in prior
                ],
            }
            ep_num = (max([p.get("episode_number", 0) for p in prior]) if prior else 0) + 1

        script = await _generate_script(
            payload.brief,
            series_ctx=series_ctx,
            requested_shots=payload.requested_shots,
            shot_duration=payload.shot_duration,
            language=payload.language,
            dialect_notes=payload.dialect_notes,
            subtitle_language=payload.subtitle_language,
            art_style=payload.art_style,
            genre=payload.genre,
            voice_gender=payload.voice_gender,
            extra_directives=payload.extra_directives,
        )

        shots = script.get("shots", []) or []
        cost = sum(shot_price(int(sh.get("duration") or payload.shot_duration)) for sh in shots)

        ep_id = str(uuid.uuid4())
        ep_doc = {
            "id": ep_id,
            "user_id": user["user_id"],
            "session_id": payload.session_id,
            "series_id": payload.series_id or "",
            "episode_number": ep_num,
            "brief": payload.brief,
            "language": payload.language,
            "subtitle_language": payload.subtitle_language or "",
            "art_style": payload.art_style,
            "genre": payload.genre,
            "aspect_ratio": payload.aspect_ratio,
            "voice_gender": payload.voice_gender,
            "script": script,
            "shots": shots,
            "storyboard": [],
            "estimated_cost": cost,
            "stage": "script",
            "approved_at": None,
            "rendered_at": None,
            "credits_charged": 0,
            "final_clips": [],
            "share_slug": "",
            "created_at": _now(),
            "updated_at": _now(),
        }
        await db.video_episodes.insert_one(ep_doc.copy())
        return {
            "ok": True,
            "episode": {k: v for k, v in ep_doc.items() if k != "_id"},
            "estimated_cost_credits": cost,
            "note": "السيناريو جاهز. لا خصم بعد. التالي: استدع /storyboard لمعاينة كل لقطة كصور.",
        }

    # ── Storyboard preview (FREE) ──────────────────────────────────────
    @router.post("/storyboard")
    async def gen_storyboard(payload: StoryboardIn, user=Depends(get_current_user)):
        ep = await db.video_episodes.find_one(
            {"id": payload.episode_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not ep:
            raise HTTPException(404, "episode not found")
        if ep.get("stage") not in ("script", "storyboard"):
            raise HTTPException(400, f"episode stage is '{ep.get('stage')}' — storyboard already done or past it")
        if not _owner_openai_key():
            raise HTTPException(400,
                "ما فيه مفتاح OpenAI خاص بك. ادخل /admin/independence وضع OPENAI_DIRECT_KEY قبل الـstoryboard.")

        art = next((x for x in ART_STYLES if x["id"] == ep.get("art_style")), ART_STYLES[0])
        aspect = ep.get("aspect_ratio") or "16x9"
        shots = ep.get("shots") or []
        sem = asyncio.Semaphore(3)

        async def _one(shot: Dict[str, Any]) -> Dict[str, Any]:
            async with sem:
                url = await _gen_storyboard_image(
                    shot.get("visual_en") or shot.get("title_ar") or "",
                    style_seed=art["prompt_seed"], aspect=aspect,
                )
                return {**shot, "preview_url": url, "preview_failed": url is None}

        decorated = await asyncio.gather(*[_one(s) for s in shots])
        await db.video_episodes.update_one(
            {"id": ep["id"]},
            {"$set": {
                "shots": decorated,
                "storyboard": [{"n": s.get("n"), "preview_url": s.get("preview_url")} for s in decorated],
                "stage": "storyboard",
                "updated_at": _now(),
            }},
        )
        previews_ok = sum(1 for s in decorated if s.get("preview_url"))
        return {
            "ok": True,
            "episode_id": ep["id"],
            "previews_generated": previews_ok,
            "total_shots": len(decorated),
            "shots": decorated,
            "note": "اللقطات جاهزة كصور preview. راجع وعدّل قبل ما تضغط 'موافق' لبدء الإنتاج.",
        }

    # ── Approve gate (FREE) ────────────────────────────────────────────
    @router.post("/approve")
    async def approve(payload: ApproveIn, user=Depends(get_current_user)):
        ep = await db.video_episodes.find_one(
            {"id": payload.episode_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not ep:
            raise HTTPException(404, "episode not found")
        if ep.get("stage") != "storyboard":
            raise HTTPException(400, "must finish storyboard before approving")
        if not payload.confirmed:
            raise HTTPException(400, "approval requires confirmed=true")
        cost = ep.get("estimated_cost", 0)
        credits = await _get_credits(user["user_id"])
        if credits < cost:
            raise HTTPException(402, f"رصيد غير كافٍ. تحتاج {cost} نقطة، رصيدك {credits}.")
        await db.video_episodes.update_one(
            {"id": ep["id"]},
            {"$set": {"stage": "approved", "approved_at": _now(), "updated_at": _now()}},
        )
        return {
            "ok": True,
            "episode_id": ep["id"],
            "cost_to_be_charged_on_render": cost,
            "credits_before": credits,
            "note": "تمّت الموافقة. عند استدعاء /render سيتم خصم النقاط مرة واحدة.",
        }

    # ── Render (PAY here) — background task with live status ──────────
    async def _do_render(episode_id: str, user_id: str, cost: int) -> None:
        ep = await db.video_episodes.find_one({"id": episode_id}, {"_id": 0})
        if not ep:
            return
        aspect = ep.get("aspect_ratio") or "16x9"
        shots = ep.get("shots") or []
        total = len(shots)
        final_clips: List[Dict[str, Any]] = []
        failed = 0
        last_error: Optional[str] = None

        await db.video_episodes.update_one(
            {"id": episode_id},
            {"$set": {
                "render_status": {
                    "running": True, "phase": "starting",
                    "completed": 0, "total": total, "errors": [],
                    "started_at": _now(),
                },
                "updated_at": _now(),
            }},
        )

        for idx, shot in enumerate(shots):
            n = shot.get("n", idx + 1)
            prompt = shot.get("visual_en") or shot.get("title_ar") or ""
            sub = shot.get("subtitle_translation")
            if sub:
                prompt = f"{prompt}. Include caption text reading: {sub}"
            duration = int(shot.get("duration") or 8)

            await db.video_episodes.update_one(
                {"id": episode_id},
                {"$set": {
                    "render_status.phase": f"shot_{n}",
                    "render_status.current_shot": n,
                    "render_status.completed": idx,
                    "render_status.updated_at": _now(),
                }},
            )

            result = await _render_shot(prompt, duration, aspect=aspect)
            if result.get("ok") and result.get("clips"):
                # Concat note: we keep sub-clips as separate URLs; FE plays them sequentially
                final_clips.append({
                    "n": n,
                    "title_ar": shot.get("title_ar"),
                    "dialogue": shot.get("dialogue"),
                    "subtitle_translation": sub,
                    "duration": duration,
                    "video_url": result["clips"][0],  # primary clip
                    "sub_clips": result["clips"],     # full list (for >12s shots)
                    "ok": True,
                })
            else:
                failed += 1
                last_error = result.get("error") or "unknown"
                final_clips.append({
                    "n": n,
                    "title_ar": shot.get("title_ar"),
                    "duration": duration,
                    "video_url": None,
                    "ok": False,
                    "error": last_error,
                })
                await db.video_episodes.update_one(
                    {"id": episode_id},
                    {"$push": {"render_status.errors": {"n": n, "error": last_error}}},
                )

        # Refund if everything failed
        if failed == total and total > 0:
            await db.users.update_one(
                {"id": user_id},
                {"$inc": {"credits": cost},
                 "$push": {"credit_history": {
                     "amount": cost,
                     "reason": f"refund_render_ep_{ep.get('episode_number')}_all_failed",
                     "timestamp": _now(),
                 }}}
            )
            await db.video_episodes.update_one(
                {"id": episode_id},
                {"$set": {
                    "stage": "approved",
                    "updated_at": _now(),
                    "last_error": last_error or "all_failed",
                    "render_status": {
                        "running": False, "phase": "failed_refunded",
                        "completed": total, "total": total,
                        "errors": [{"n": c.get("n"), "error": c.get("error")} for c in final_clips if not c.get("ok")],
                        "finished_at": _now(),
                    },
                }},
            )
            return

        await db.video_episodes.update_one(
            {"id": episode_id},
            {"$set": {
                "stage": "rendered",
                "rendered_at": _now(),
                "credits_charged": cost,
                "final_clips": final_clips,
                "updated_at": _now(),
                "render_status": {
                    "running": False,
                    "phase": "completed" if failed == 0 else "completed_with_errors",
                    "completed": total, "total": total,
                    "shots_failed": failed,
                    "finished_at": _now(),
                },
            }},
        )
        if ep.get("series_id"):
            await db.video_series.update_one(
                {"id": ep["series_id"]},
                {"$set": {"updated_at": _now()}},
            )

    @router.post("/render")
    async def render(payload: RenderIn, user=Depends(get_current_user)):
        ep = await db.video_episodes.find_one(
            {"id": payload.episode_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not ep:
            raise HTTPException(404, "episode not found")
        if ep.get("stage") != "approved":
            raise HTTPException(400, f"episode stage='{ep.get('stage')}' — must approve first")
        if not _owner_openai_key():
            raise HTTPException(400,
                "ما فيه مفتاح OpenAI خاص بك. الإنتاج يتطلب OPENAI_DIRECT_KEY.")
        cost = ep.get("estimated_cost", 0)

        deduct = await db.users.update_one(
            {"id": user["user_id"], "credits": {"$gte": cost}},
            {"$inc": {"credits": -cost},
             "$push": {"credit_history": {
                 "amount": -cost,
                 "reason": f"video_studio_render_ep_{ep.get('episode_number')}",
                 "timestamp": _now(),
             }}}
        )
        if deduct.modified_count == 0:
            raise HTTPException(402, f"رصيد غير كافٍ ({cost} نقطة).")

        # Mark rendering immediately so any concurrent /render is rejected
        await db.video_episodes.update_one(
            {"id": ep["id"]},
            {"$set": {"stage": "rendering", "updated_at": _now()}},
        )
        # Kick off background task — return immediately so the UI can poll
        asyncio.create_task(_do_render(ep["id"], user["user_id"], cost))

        return {
            "ok": True,
            "episode_id": ep["id"],
            "background": True,
            "estimated_cost_credits": cost,
            "credits_remaining": await _get_credits(user["user_id"]),
            "poll_url": f"/api/video-studio/render-status/{ep['id']}",
            "note": "بدأ الإنتاج في الخلفية. تابع التقدّم من صفحة /chat/video/render.",
        }

    @router.get("/render-status/{episode_id}")
    async def render_status(episode_id: str, user=Depends(get_current_user)):
        ep = await db.video_episodes.find_one(
            {"id": episode_id, "user_id": user["user_id"]},
            {"_id": 0, "id": 1, "stage": 1, "render_status": 1,
             "final_clips": 1, "credits_charged": 1, "shots": 1, "script": 1,
             "episode_number": 1, "last_error": 1},
        )
        if not ep:
            raise HTTPException(404, "episode not found")
        return {"ok": True, "episode": ep}

    @router.get("/episode/{episode_id}")
    async def get_episode(episode_id: str, user=Depends(get_current_user)):
        ep = await db.video_episodes.find_one(
            {"id": episode_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not ep:
            raise HTTPException(404, "episode not found")
        return {"ok": True, "episode": ep}

    # ── Share + Social ─────────────────────────────────────────────────
    @router.post("/share")
    async def make_share(payload: ShareIn, user=Depends(get_current_user)):
        ep = await db.video_episodes.find_one(
            {"id": payload.episode_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not ep:
            raise HTTPException(404, "episode not found")
        if ep.get("stage") != "rendered":
            raise HTTPException(400, "ما تقدر تشارك حلقة ما زالت في الإنتاج.")
        slug = (payload.slug or "").strip().lower()
        slug = re.sub(r"[^a-z0-9-]+", "-", slug)[:60] or uuid.uuid4().hex[:10]
        # Ensure uniqueness
        existing = await db.video_episodes.find_one({"share_slug": slug}, {"_id": 0, "id": 1})
        if existing and existing.get("id") != ep["id"]:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"
        await db.video_episodes.update_one(
            {"id": ep["id"]},
            {"$set": {"share_slug": slug, "updated_at": _now()}},
        )
        captions = _social_captions(ep.get("script") or {})
        return {
            "ok": True,
            "slug": slug,
            "public_url": f"/api/video-studio/p/{slug}",
            "captions": captions,
        }

    @router.get("/p/{slug}", response_class=HTMLResponse)
    async def public_view(slug: str):
        ep = await db.video_episodes.find_one({"share_slug": slug}, {"_id": 0})
        if not ep or ep.get("stage") != "rendered":
            raise HTTPException(404, "not found")
        clips = ep.get("final_clips") or []
        script = ep.get("script") or {}
        title = script.get("title", "حلقة زيتاكس")
        logline = script.get("logline", "")
        clip_blocks = "".join(
            f'<div class="clip"><video controls src="{c.get("video_url","")}"></video>'
            f'<p class="cap">{c.get("title_ar","")}</p></div>'
            for c in clips if c.get("video_url")
        )
        html = f"""<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><title>{title} · زيتاكس</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{{background:#0b0d12;color:#f4f4f5;font-family:Tajawal,system-ui,sans-serif;margin:0;padding:24px;}}
.wrap{{max-width:760px;margin:0 auto;}}
h1{{font-size:24px;margin:.5em 0 .2em;}}
.logline{{color:#a1a1aa;font-size:14px;margin-bottom:18px}}
.clip{{margin-bottom:18px;background:#12161e;border:1px solid #27272a;border-radius:12px;overflow:hidden}}
.clip video{{width:100%;display:block;background:#000}}
.cap{{padding:8px 12px;font-size:13px;color:#d4d4d8;margin:0}}
.footer{{margin-top:24px;font-size:11px;color:#71717a;text-align:center}}
</style></head><body><div class="wrap">
<h1>{title}</h1><div class="logline">{logline}</div>
{clip_blocks}
<div class="footer">صُنع بواسطة <b>زيتاكس</b></div>
</div></body></html>"""
        return HTMLResponse(html)

    # ── Narration → Film (YouTuber voiceover → cinematic film) ─────────
    # Receives an audio file (mp3/m4a/wav) of someone narrating a story.
    # Whisper transcribes (using OWNER's OpenAI key), GPT-4o segments it
    # into scenes with cinematic visual prompts that follow the narration
    # exactly. By default we apply the 'hyperreal' style so the output is
    # indistinguishable from real footage.
    @router.post("/narration-to-script")
    async def narration_to_script(
        audio: UploadFile = File(...),
        series_id: str = Form(""),
        language: str = Form("ar-saudi"),
        art_style: str = Form("hyperreal"),
        aspect_ratio: str = Form("16x9"),
        max_shots: int = Form(8),
        user=Depends(get_current_user),
    ):
        if audio is None:
            raise HTTPException(400, "audio file is required")
        key = _owner_openai_key()
        if not key:
            raise HTTPException(400, "ما فيه OPENAI_DIRECT_KEY خاص بك — أضفه من /admin/independence.")

        # 1. Save upload + send to Whisper
        suffix = (audio.filename or "audio.mp3").split(".")[-1][:6]
        tmp_path = Path("/tmp") / f"narr_{uuid.uuid4().hex}.{suffix}"
        try:
            data = await audio.read()
            if not data or len(data) < 1000:
                raise HTTPException(400, "ملف الصوت فارغ أو صغير جداً")
            if len(data) > 25 * 1024 * 1024:
                raise HTTPException(413, "حجم الملف أكبر من 25MB — قسّمه أو اضغطه أولاً.")
            tmp_path.write_bytes(data)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"فشل حفظ الملف: {e}")

        try:
            import httpx
            async with httpx.AsyncClient(timeout=180.0) as client:
                with open(tmp_path, "rb") as fh:
                    files = {"file": (audio.filename or "audio.mp3", fh, "audio/mpeg")}
                    r = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {key}"},
                        data={"model": "whisper-1", "response_format": "verbose_json"},
                        files=files,
                    )
                if r.status_code != 200:
                    raise HTTPException(503, f"Whisper رفض: {r.text[:200]}")
                tx = r.json()
                full_text = (tx.get("text") or "").strip()
                segments = tx.get("segments") or []
                if not full_text:
                    raise HTTPException(500, "Whisper رجّع نص فارغ")
        finally:
            try:
                tmp_path.unlink()
            except Exception:
                pass

        # 2. Ask GPT to split into cinematic shots matching the narration
        art = next((x for x in ART_STYLES if x["id"] == art_style), ART_STYLES[0])
        sys_prompt = (
            "أنت مخرج أفلام واقعية. عندك نص رواية صوتية كاملة. مهمتك تقسيمها "
            "إلى لقطات سينمائية، كل لقطة:\n"
            "  • تبقي نص الراوي EXACTLY كما هو (لا تغيّر كلمة من كلامه).\n"
            "  • تختار toolkit بصري واقعي ١٠٠٪ يتطابق مع ما يقوله.\n"
            "  • visual_en بالإنجليزية وصفاً صارماً للمشهد الحقيقي (no CGI look).\n"
            "أرجع JSON: {title, logline, shots: [{n, narration_ar, visual_en, duration}]}\n"
            f"الستايل البصري الإجباري في كل visual_en:\n{art['prompt_seed']}\n"
            f"عدد لقطات تقديري: {max_shots} (يجوز أقل لو النص قصير).\n"
            "مدة كل لقطة 4–12 ثانية حسب طول الجملة الصوتية."
        )
        user_prompt = (
            f"النص الكامل بصوت الراوي:\n```\n{full_text[:6000]}\n```\n\n"
            f"الـsegments من Whisper مع التوقيتات:\n"
            + json.dumps([{"start": s.get("start"), "end": s.get("end"), "text": s.get("text")}
                          for s in segments[:60]], ensure_ascii=False)[:4000]
            + "\n\nأرجع JSON فقط."
        )
        async with httpx.AsyncClient(timeout=90.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 4000,
                },
            )
            if r.status_code != 200:
                raise HTTPException(503, f"GPT رفض: {r.text[:200]}")
            script = json.loads(r.json()["choices"][0]["message"]["content"])

        shots = script.get("shots", []) or []
        cost = sum(shot_price(int(sh.get("duration") or 8)) for sh in shots)

        ep_id = str(uuid.uuid4())
        ep_doc = {
            "id": ep_id,
            "user_id": user["user_id"],
            "session_id": "narration",
            "series_id": series_id or "",
            "episode_number": 1,
            "brief": f"[Narration upload] {full_text[:120]}…",
            "narration_full_text": full_text,
            "narration_segments": segments,
            "language": language,
            "subtitle_language": "",
            "art_style": art_style,
            "genre": "documentary",
            "aspect_ratio": aspect_ratio,
            "voice_gender": "narration_uploaded",
            "use_uploaded_voice": True,
            "script": script,
            "shots": shots,
            "storyboard": [],
            "estimated_cost": cost,
            "stage": "script",
            "approved_at": None,
            "rendered_at": None,
            "credits_charged": 0,
            "final_clips": [],
            "share_slug": "",
            "created_at": _now(),
            "updated_at": _now(),
        }
        await db.video_episodes.insert_one(ep_doc.copy())
        return {
            "ok": True,
            "episode": {k: v for k, v in ep_doc.items() if k != "_id" and k != "narration_segments"},
            "estimated_cost_credits": cost,
            "shots_count": len(shots),
            "transcribed_chars": len(full_text),
            "note": "تم تفريغ صوت الراوي وتقسيمه إلى لقطات. التالي: ولّد الستوري بورد، ثم وافق على الإنتاج.",
        }

    # ── PRODUCTION STUDIO: Characters / Locations / Props (PAID) ──────
    # Each asset = 1 image generation + persistence. Charged immediately
    # because they're standalone deliverables the user can re-use across
    # episodes. Cost depends on quality tier.
    ASSET_KINDS = {
        "character": {"label_ar": "شخصية", "cost": 6,
                      "style_seed": "Full body character reference sheet, neutral pose, plain background, "
                                    "consistent design for series re-use, T-pose, sharp facial details"},
        "villain":   {"label_ar": "شخصية شريرة", "cost": 6,
                      "style_seed": "Full body villain character reference sheet, menacing pose, "
                                    "dark lighting, plain background, consistent design for series re-use"},
        "location":  {"label_ar": "مكان / موقع", "cost": 5,
                      "style_seed": "Wide establishing shot, environment design, no characters, "
                                    "consistent lighting for series re-use, atmospheric"},
        "prop":      {"label_ar": "غرض / دعامة", "cost": 3,
                      "style_seed": "Product/prop reference, isolated on neutral background, "
                                    "clean angle, ready for compositing"},
        "vehicle":   {"label_ar": "وسيلة نقل", "cost": 4,
                      "style_seed": "Vehicle 3/4 reference shot, isolated on neutral background, clean lighting"},
    }

    class _UnusedPlaceholder(BaseModel):  # noqa: F841 — kept to preserve indentation
        pass

    @router.post("/production/asset")
    async def create_asset(payload: ProductionAssetIn, user=Depends(get_current_user)):
        kind_meta = ASSET_KINDS.get(payload.kind)
        if not kind_meta:
            raise HTTPException(400, f"kind غير معروف: {payload.kind}")
        if not _owner_openai_key():
            raise HTTPException(400, "أضف OPENAI_DIRECT_KEY قبل بناء الأصول.")
        # Verify series ownership
        s = await db.video_series.find_one(
            {"id": payload.series_id, "user_id": user["user_id"]}, {"_id": 0, "id": 1}
        )
        if not s:
            raise HTTPException(404, "series not found")
        cost = kind_meta["cost"]
        # Atomic credits deduction
        deduct = await db.users.update_one(
            {"id": user["user_id"], "credits": {"$gte": cost}},
            {"$inc": {"credits": -cost},
             "$push": {"credit_history": {
                 "amount": -cost,
                 "reason": f"production_{payload.kind}_{payload.name[:40]}",
                 "timestamp": _now(),
             }}},
        )
        if deduct.modified_count == 0:
            raise HTTPException(402, f"رصيد غير كافٍ ({cost} نقطة).")

        art = next((x for x in ART_STYLES if x["id"] == payload.art_style), ART_STYLES[0])
        full_prompt = (
            f"{payload.description}. "
            f"{kind_meta['style_seed']}. "
            f"{art['prompt_seed']}"
        )
        url = await _gen_storyboard_image(full_prompt, style_seed="", aspect="1x1")
        if not url:
            # refund on failure
            await db.users.update_one(
                {"id": user["user_id"]},
                {"$inc": {"credits": cost},
                 "$push": {"credit_history": {
                     "amount": cost,
                     "reason": f"refund_production_{payload.kind}_failed",
                     "timestamp": _now(),
                 }}},
            )
            raise HTTPException(500, "فشل توليد الصورة — تمت إعادة النقاط.")

        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "series_id": payload.series_id,
            "kind": payload.kind,
            "kind_label_ar": kind_meta["label_ar"],
            "name": payload.name,
            "description": payload.description,
            "image_url": url,
            "art_style": payload.art_style,
            "attributes": payload.attributes,
            "cost_paid": cost,
            "created_at": _now(),
        }
        await db.production_assets.insert_one(doc.copy())
        return {
            "ok": True,
            "asset": {k: v for k, v in doc.items() if k != "_id"},
            "credits_charged": cost,
            "credits_remaining": await _get_credits(user["user_id"]),
        }

    @router.get("/production/series/{series_id}/assets")
    async def list_assets(series_id: str, user=Depends(get_current_user)):
        cur = db.production_assets.find(
            {"series_id": series_id, "user_id": user["user_id"]}, {"_id": 0}
        ).sort([("created_at", -1)]).limit(200)
        items = await cur.to_list(200)
        # Also include relationships
        rels_cur = db.production_relationships.find(
            {"series_id": series_id, "user_id": user["user_id"]}, {"_id": 0}
        ).limit(500)
        relationships = await rels_cur.to_list(500)
        return {"ok": True, "assets": items, "relationships": relationships}

    @router.delete("/production/asset/{asset_id}")
    async def delete_asset(asset_id: str, user=Depends(get_current_user)):
        r = await db.production_assets.delete_one({"id": asset_id, "user_id": user["user_id"]})
        # Drop any relationships referencing it
        await db.production_relationships.delete_many(
            {"user_id": user["user_id"],
             "$or": [{"from_asset_id": asset_id}, {"to_asset_id": asset_id}]}
        )
        return {"ok": True, "deleted": r.deleted_count}

    @router.post("/production/relationship")
    async def create_relationship(payload: RelationshipIn, user=Depends(get_current_user)):
        if payload.from_asset_id == payload.to_asset_id:
            raise HTTPException(400, "علاقة الشخصية بنفسها غير مسموحة")
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "series_id": payload.series_id,
            "from_asset_id": payload.from_asset_id,
            "to_asset_id": payload.to_asset_id,
            "kind": payload.kind,
            "notes": payload.notes,
            "created_at": _now(),
        }
        await db.production_relationships.insert_one(doc.copy())
        return {"ok": True, "relationship": {k: v for k, v in doc.items() if k != "_id"}}

    @router.delete("/production/relationship/{rel_id}")
    async def delete_relationship(rel_id: str, user=Depends(get_current_user)):
        r = await db.production_relationships.delete_one({"id": rel_id, "user_id": user["user_id"]})
        return {"ok": True, "deleted": r.deleted_count}

    # AI Producer wizard — guides the user step by step through universe-building
    @router.post("/production/producer-chat")
    async def producer_chat(payload: ProducerChatIn, user=Depends(get_current_user)):
        s = await db.video_series.find_one(
            {"id": payload.series_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not s:
            raise HTTPException(404, "series not found")
        # Fetch existing assets for context
        a_cur = db.production_assets.find(
            {"series_id": payload.series_id, "user_id": user["user_id"]}, {"_id": 0, "kind": 1, "name": 1, "description": 1}
        ).limit(50)
        assets = await a_cur.to_list(50)
        chars = [a for a in assets if a.get("kind") in ("character", "villain")]
        locs = [a for a in assets if a.get("kind") == "location"]

        try:
            from modules.shared import SectionAgent
        except Exception:
            raise HTTPException(503, "shared agent core unavailable")

        step_hints = {
            "discover": "ساعد العميل يحدّد: ١) النوع (رعب/أكشن/درامي/أنمي…) ٢) المزاج العام ٣) الجمهور المستهدف. اقترح أفكاراً جريئة.",
            "villains": "ساعده يبني فريق الأشرار. اسأل عن دافع كل شرير، مظهره، قوّته، نقطة ضعفه. أوصِ بإنشاء كل شخصية عبر زر '+ شخصية شريرة'.",
            "heroes":  "ساعده يبني فريق الأبطال. اسأل عن عدد الأبطال، خلفياتهم، تخصّص كل واحد، شخصيته. أوصِ بإنشاء كل شخصية.",
            "locations": "ساعده يصمّم الأماكن الرئيسية (المدينة، البحر، السفينة، المستودع). كل مكان = أصل مستقل تدفع عليه.",
            "relationships": "اقترح خريطة علاقات بين الشخصيات (يحب/يكره/حليف/عدو/عائلة/معلم/منافس). كلما زادت العلاقات، عمقت الحبكة.",
            "ready": "كل العالم جاهز. اشرح كيف العميل يستخدم هذه الشخصيات والأماكن في كتابة الحلقات.",
        }
        extra_persona = (
            f"\n\n🎬 وضع منتج تنفيذي (Production Studio). السلسلة: {s.get('title')}. "
            f"الستايل المرجعي: {s.get('style_direction') or '—'}.\n"
            f"المرحلة الحالية: **{payload.step}** — {step_hints.get(payload.step, '')}\n\n"
            f"الشخصيات المسجّلة حتى الآن ({len(chars)}): "
            + (", ".join(f"{c['name']} ({c['kind']})" for c in chars[:10]) or "(لا شيء)")
            + f"\nالأماكن المسجّلة ({len(locs)}): "
            + (", ".join(c["name"] for c in locs[:10]) or "(لا شيء)")
            + "\n\nقواعد سلوكك: تكلّم كمنتج فاهم، اقترح عدد شخصيات معقول، حفّز العميل يستثمر "
            "في بناء عالمه (كل أصل مدفوع لكن يُعاد استخدامه عبر كل الحلقات → ROI ممتاز). "
            "في كل ردّ، اعطِ خياراً واحداً واضحاً + سعره + زر إجراء يستدعيه العميل."
        )
        agent = SectionAgent("video", extra_persona=extra_persona, strict_scope=False)
        result = await agent.chat(user["user_id"], payload.message or "ابدأ الإرشاد",
                                  session_id=f"prod_{payload.series_id}_{payload.step}")
        return {
            "ok": True,
            "step": payload.step,
            "reply": result.get("reply"),
            "session_id": result.get("session_id"),
            "context": {
                "characters_count": len(chars),
                "locations_count": len(locs),
                "asset_kinds": list(ASSET_KINDS.keys()),
                "asset_costs": {k: v["cost"] for k, v in ASSET_KINDS.items()},
            },
        }

    @router.get("/production/asset-kinds")
    async def list_asset_kinds(_=Depends(get_current_user)):
        return {
            "ok": True,
            "kinds": [
                {"id": k, "label_ar": v["label_ar"], "cost": v["cost"]}
                for k, v in ASSET_KINDS.items()
            ],
        }

    # ── DISCOVER — community feed of public episodes ───────────────────
    @router.get("/discover")
    async def discover(limit: int = 30, _=Depends(get_current_user)):
        """Public-only feed of rendered + shared episodes from all users."""
        cur = db.video_episodes.find(
            {"share_slug": {"$ne": ""}, "stage": "rendered"},
            {"_id": 0, "id": 1, "user_id": 1, "share_slug": 1,
             "script": 1, "art_style": 1, "language": 1, "aspect_ratio": 1,
             "final_clips": 1, "rendered_at": 1, "views": 1, "likes": 1},
        ).sort([("rendered_at", -1)]).limit(min(100, max(1, limit)))
        items = await cur.to_list(100)
        # Decorate with thumbnail + first-clip URL + author display
        feed = []
        for ep in items:
            clips = ep.get("final_clips") or []
            first = next((c for c in clips if c.get("video_url")), None)
            user_doc = await db.users.find_one({"id": ep.get("user_id")}, {"_id": 0, "name": 1, "username": 1})
            feed.append({
                "id": ep["id"],
                "share_slug": ep.get("share_slug"),
                "public_url": f"/api/video-studio/p/{ep.get('share_slug')}",
                "title": (ep.get("script") or {}).get("title", "حلقة"),
                "logline": (ep.get("script") or {}).get("logline", ""),
                "art_style": ep.get("art_style"),
                "language": ep.get("language"),
                "aspect_ratio": ep.get("aspect_ratio"),
                "first_clip_url": (first or {}).get("video_url"),
                "shots_count": len(clips),
                "views": ep.get("views", 0),
                "likes": ep.get("likes", 0),
                "rendered_at": ep.get("rendered_at"),
                "author": (user_doc or {}).get("name") or (user_doc or {}).get("username") or "مستخدم",
            })
        return {"ok": True, "feed": feed, "count": len(feed)}

    @router.post("/discover/{episode_id}/like")
    async def like_episode(episode_id: str, _=Depends(get_current_user)):
        r = await db.video_episodes.update_one(
            {"id": episode_id, "share_slug": {"$ne": ""}, "stage": "rendered"},
            {"$inc": {"likes": 1}},
        )
        if r.modified_count == 0:
            raise HTTPException(404, "not shareable")
        return {"ok": True}

    @router.post("/discover/{episode_id}/view")
    async def view_episode(episode_id: str, _=Depends(get_current_user)):
        await db.video_episodes.update_one(
            {"id": episode_id, "share_slug": {"$ne": ""}, "stage": "rendered"},
            {"$inc": {"views": 1}},
        )
        return {"ok": True}

    # ── Static asset serving for storyboard previews ───────────────────
    @router.get("/storyboard-img/{filename}")
    async def get_storyboard_img(filename: str):
        if "/" in filename or ".." in filename:
            raise HTTPException(400, "bad filename")
        p = STORYBOARD_DIR / filename
        if not p.exists():
            raise HTTPException(404, "not found")
        return FileResponse(str(p), media_type="image/png")

    return router
