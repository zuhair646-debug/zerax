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

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ════════════════════════════════════════════════════════════════════════
# PRICING — credits only billed at render step
# ════════════════════════════════════════════════════════════════════════
PRICE_PER_SHOT_4S = 8
PRICE_PER_SHOT_8S = 14
PRICE_PER_SHOT_12S = 20


def shot_price(duration_seconds: int) -> int:
    if duration_seconds <= 4:
        return PRICE_PER_SHOT_4S
    if duration_seconds <= 8:
        return PRICE_PER_SHOT_8S
    return PRICE_PER_SHOT_12S


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
    requested_shots: int = Field(default=4, ge=1, le=12)
    shot_duration: int = Field(default=8, ge=4, le=12)
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
async def _render_shot(prompt: str, duration: int, *, aspect: str = "16x9") -> Optional[str]:
    """Render via Sora 2 using the owner's own OpenAI account."""
    key = _owner_openai_key()
    if not key:
        return None
    try:
        from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration  # type: ignore
        gen = OpenAIVideoGeneration(api_key=key)
        sora_dur = min(12, max(4, duration))
        size = _aspect_to_size(aspect)
        # Sora 2 currently supports 1280x720 and 720x1280 only — coerce square→16x9
        if size not in ("1280x720", "720x1280"):
            size = "1280x720"
        video_bytes = gen.text_to_video(
            prompt=prompt, model="sora-2",
            size=size, duration=sora_dur, max_wait_time=600,
        )
        if video_bytes:
            return "data:video/mp4;base64," + base64.b64encode(video_bytes).decode("utf-8")
    except Exception as e:
        logger.error(f"sora render failed: {e}")
    return None


# ════════════════════════════════════════════════════════════════════════
# Social share captions — built locally (no API call)
# ════════════════════════════════════════════════════════════════════════
def _social_captions(script: Dict[str, Any]) -> Dict[str, str]:
    title = (script.get("title") or "").strip() or "حلقة جديدة من زيتاكس"
    logline = (script.get("logline") or "").strip()
    hashtags = "#زيتاكس #فيديو_بالذكاء_الاصطناعي #ai #zitex"
    return {
        "tiktok": f"{title}\n{logline}\n\n{hashtags} #fyp #tiktok",
        "instagram": f"{title}\n{logline}\n\n{hashtags} #reels #instagram",
        "twitter": f"{title} — {logline}\n\n{hashtags}",
        "youtube": f"{title}\n\n{logline}\n\n{hashtags}",
        "snapchat": f"{title}\n{logline}",
    }


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
            "owner_key_configured": bool(_owner_openai_key()),
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

    # ── Render (PAY here) ──────────────────────────────────────────────
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
                "ما فيه مفتاح OpenAI خاص بك. الإنتاج يتطلب OPENAI_DIRECT_KEY عشان "
                "ما يتم الخصم من حساب المنصة.")
        cost = ep.get("estimated_cost", 0)
        aspect = ep.get("aspect_ratio") or "16x9"

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

        final_clips: List[Dict[str, Any]] = []
        failed = 0
        for shot in (ep.get("shots") or []):
            prompt = shot.get("visual_en") or shot.get("title_ar") or ""
            # Add subtitle hint as overlay text in the visual prompt only if present
            sub = shot.get("subtitle_translation")
            if sub:
                prompt = f"{prompt}. Include caption text reading: {sub}"
            duration = int(shot.get("duration") or 8)
            clip = await _render_shot(prompt, duration, aspect=aspect)
            final_clips.append({
                "n": shot.get("n"),
                "title_ar": shot.get("title_ar"),
                "dialogue": shot.get("dialogue"),
                "subtitle_translation": sub,
                "duration": duration,
                "video_url": clip,
                "ok": clip is not None,
            })
            if clip is None:
                failed += 1

        if failed == len(final_clips) and final_clips:
            await db.users.update_one(
                {"id": user["user_id"]},
                {"$inc": {"credits": cost},
                 "$push": {"credit_history": {
                     "amount": cost,
                     "reason": f"refund_video_studio_ep_{ep.get('episode_number')}_all_failed",
                     "timestamp": _now(),
                 }}}
            )
            await db.video_episodes.update_one(
                {"id": ep["id"]},
                {"$set": {"stage": "approved", "updated_at": _now(),
                          "last_error": "all shots failed to render"}}
            )
            raise HTTPException(500, "فشل إنتاج جميع اللقطات. تمت إعادة النقاط.")

        await db.video_episodes.update_one(
            {"id": ep["id"]},
            {"$set": {
                "stage": "rendered",
                "rendered_at": _now(),
                "credits_charged": cost,
                "final_clips": final_clips,
                "updated_at": _now(),
            }}
        )
        if ep.get("series_id"):
            await db.video_series.update_one(
                {"id": ep["series_id"]},
                {"$set": {"updated_at": _now()}},
            )

        return {
            "ok": True,
            "episode_id": ep["id"],
            "clips": final_clips,
            "shots_rendered": len(final_clips) - failed,
            "shots_failed": failed,
            "credits_charged": cost,
            "credits_remaining": await _get_credits(user["user_id"]),
        }

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
