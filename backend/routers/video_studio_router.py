"""
Zenrex Video Studio — Promo Video Generator
-------------------------------------------
Generates short marketing videos (15s / 30s / 45s / 60s) for merchants.

Pipeline:
  1. (optional) AI storyboard generation → Arabic narration + scene prompts
  2. Zenrex Voice Engine (currently OpenAI TTS, abstracted) → MP3 narration
  3. ffmpeg slideshow stitch (scene images + audio + logo + title) → MP4

Designed so the underlying TTS / video provider can be swapped with Zenrex's own
internal engine without touching the frontend contract.
"""
import os
import re
import json
import uuid
import base64
import shutil
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/promo-video", tags=["promo-video"])

# ─────────────────────────────────────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────────────────────────────────────
STATIC_DIR = Path("/app/backend/static")
VIDEOS_DIR = STATIC_DIR / "videos"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR = STATIC_DIR / "_video_tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Pricing (Zenrex credits)  — frontend MUST mirror these
# ─────────────────────────────────────────────────────────────────────────────
COST_STORYBOARD = 5
COST_PER_5_SECONDS = 5   # 30s = 30 credits, 45s = 45 credits, 60s = 60 credits


# ─────────────────────────────────────────────────────────────────────────────
# Voice abstraction — "Zenrex Voice Engine"
# Currently powered by OpenAI TTS via EMERGENT_LLM_KEY.
# Swap this single mapping when the real Zenrex voice service is online.
# ─────────────────────────────────────────────────────────────────────────────
ZENREX_VOICE_MAP = {
    # Arabic voices (5 main characters)
    "zenrex_male_deep":     {"provider": "openai_tts", "voice": "onyx",   "model": "tts-1-hd"},
    "zenrex_male_warm":     {"provider": "openai_tts", "voice": "echo",   "model": "tts-1-hd"},
    "zenrex_male_youth":    {"provider": "openai_tts", "voice": "fable",  "model": "tts-1-hd"},
    "zenrex_female_warm":   {"provider": "openai_tts", "voice": "shimmer","model": "tts-1-hd"},
    "zenrex_female_clear":  {"provider": "openai_tts", "voice": "nova",   "model": "tts-1-hd"},
    "zenrex_neutral":       {"provider": "openai_tts", "voice": "alloy",  "model": "tts-1-hd"},
    # Premium character variants (mapped to same underlying TTS voices but exposed as distinct personalities)
    "zenrex_narrator_pro":  {"provider": "openai_tts", "voice": "onyx",   "model": "tts-1-hd"},
    "zenrex_friend_chat":   {"provider": "openai_tts", "voice": "echo",   "model": "tts-1-hd"},
    "zenrex_announcer":     {"provider": "openai_tts", "voice": "fable",  "model": "tts-1-hd"},
    "zenrex_storyteller_f": {"provider": "openai_tts", "voice": "shimmer","model": "tts-1-hd"},
    "zenrex_news_anchor":   {"provider": "openai_tts", "voice": "nova",   "model": "tts-1-hd"},
    "zenrex_documentary":   {"provider": "openai_tts", "voice": "alloy",  "model": "tts-1-hd"},
}
DEFAULT_VOICE = "zenrex_male_deep"


# ═════════════════════════════════════════════════════════════════════════════
# 1) STORYBOARD
# ═════════════════════════════════════════════════════════════════════════════
class StoryboardRequest(BaseModel):
    product_name: str
    product_description: Optional[str] = ""
    duration_seconds: int = 30   # 15 | 30 | 45 | 60
    tone: str = "energetic"      # energetic | luxury | warm | tech
    lang: str = "ar"             # ar | en | …
    dialect: Optional[str] = None  # full dialect code e.g. ar-sa-hijazi, ar-kw, ar-eg
    cta: Optional[str] = None    # e.g. "اطلب الآن"


class StoryboardScene(BaseModel):
    seq: int
    narration: str        # spoken Arabic line (≤ ~12 words for 5-sec scene)
    visual_prompt: str    # English prompt for image generation
    text_overlay: Optional[str] = None  # optional short on-screen caption


class StoryboardResponse(BaseModel):
    title: str
    full_narration: str
    scenes: List[StoryboardScene]
    cta: str
    duration_seconds: int
    cost: int


def _strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        # remove first fence line and last ```
        s = re.sub(r"^```(?:json|JSON)?\s*\n", "", s)
        s = re.sub(r"\n```\s*$", "", s)
    return s.strip()


@router.post("/storyboard", response_model=StoryboardResponse)
async def generate_storyboard(req: StoryboardRequest):
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
    if req.duration_seconds not in (15, 30, 45, 60):
        raise HTTPException(status_code=400, detail="duration_seconds must be 15/30/45/60")

    scene_count = max(3, min(8, req.duration_seconds // 5))  # ~5 sec per scene
    cta_default = "اطلب الآن" if req.lang == "ar" else "Order now"
    cta = (req.cta or cta_default).strip()

    # Build a strong, dialect-specific language instruction
    DIALECT_MAP = {
        "ar-sa": "العربية باللهجة السعودية النجدية (لهجة الرياض): يلاه، خلاص، يبا، كذا، الحين، يا حلو",
        "ar-sa-hijazi": "العربية باللهجة الحجازية (جدة/مكة): يلا، كده، إيش، طيب، إنت، عنّك",
        "ar-sa-eastern": "العربية باللهجة الشرقية السعودية (الدمام/الأحساء)",
        "ar-sa-southern": "العربية باللهجة الجنوبية السعودية (أبها/جازان)",
        "ar-kw": "العربية باللهجة الكويتية: شلون، عاد، ها، الحين، شفيك",
        "ar-ae": "العربية باللهجة الإماراتية: شو، الحين، يبا، شحالك",
        "ar-qa": "العربية باللهجة القطرية",
        "ar-bh": "العربية باللهجة البحرينية",
        "ar-om": "العربية باللهجة العُمانية",
        "ar-eg": "العربية باللهجة المصرية: إيه، عايز، كده، خالص، أوي، يلا",
        "ar-jo": "العربية باللهجة الأردنية",
        "ar-lb": "العربية باللهجة اللبنانية",
        "ar-sy": "العربية باللهجة السورية",
        "ar-ps": "العربية باللهجة الفلسطينية",
        "ar-iq": "العربية باللهجة العراقية: شلون، شكو، هواي",
        "ar-ye": "العربية باللهجة اليمنية",
        "ar-ma": "العربية باللهجة المغربية الدارجة",
        "ar-dz": "العربية باللهجة الجزائرية",
        "ar-tn": "العربية باللهجة التونسية",
        "ar-ly": "العربية باللهجة الليبية",
        "ar-sd": "العربية باللهجة السودانية",
        "ar-msa": "العربية الفصحى الحديثة (MSA) — رسمية وراقية",
        "ar": "العربية باللهجة السعودية النجدية (الافتراضي)",
        "en-us": "English (American, conversational)",
        "en-gb": "English (British, polished)",
        "en": "English (natural marketing copy)",
        "fr": "Français (marketing naturel)",
        "es": "Español (marketing natural)",
        "de": "Deutsch (natürliche Werbesprache)",
        "it": "Italiano (marketing naturale)",
        "pt-br": "Português brasileiro (marketing natural)",
        "ru": "Русский (естественный маркетинг)",
        "tr": "Türkçe (doğal pazarlama)",
        "fa": "فارسی (تبلیغاتی روان)",
        "ur": "اردو (طبیعی مارکیٹنگ)",
        "hi": "हिन्दी (प्राकृतिक मार्केटिंग)",
        "bn": "বাংলা (স্বাভাবিক বিপণন)",
        "id": "Bahasa Indonesia (pemasaran natural)",
        "ms": "Bahasa Melayu (pemasaran semula jadi)",
        "th": "ภาษาไทย (การตลาดที่เป็นธรรมชาติ)",
        "vi": "Tiếng Việt (tiếp thị tự nhiên)",
        "zh-cn": "中文普通话 (自然营销文案)",
        "zh-tw": "繁體中文 (自然行銷文案)",
        "ja": "日本語 (自然なマーケティング)",
        "ko": "한국어 (자연스러운 마케팅)",
        "sw": "Kiswahili (uuzaji wa asili)",
    }
    dialect_code = (req.dialect or req.lang or "ar").lower()
    lang_instruction = DIALECT_MAP.get(dialect_code) or DIALECT_MAP.get(req.lang) or "العربية الفصحى"
    is_arabic = dialect_code.startswith("ar")
    lang_short = "Arabic" if is_arabic else "the target language"

    sys_msg = (
        f"You are Zenrex MarketingDirector — an elite advertising copywriter. "
        f"You MUST write all narration and titles in: {lang_instruction}. "
        f"NEVER use English unless the requested language IS English. Output ONLY valid JSON. No markdown, no commentary."
    )
    user_prompt = f"""Create a {req.duration_seconds}-second promotional ad storyboard.

PRODUCT: {req.product_name}
DESCRIPTION: {req.product_description or '(no description provided)'}
TONE: {req.tone}
LANGUAGE (STRICT — DO NOT DEVIATE): {lang_instruction}
SCENES: exactly {scene_count} scenes (~5 seconds each)
CTA (final scene): "{cta}"

Output STRICT JSON:
{{
  "title": "<8-word headline in {lang_instruction}>",
  "scenes": [
    {{
      "seq": 1,
      "narration": "<short spoken line in {lang_instruction}, ≤ 12 words, MUST match the dialect EXACTLY>",
      "visual_prompt": "<ENGLISH cinematic image-gen prompt describing exact shot — keep this in English ALWAYS since it feeds an image model>",
      "text_overlay": "<optional 2-3 word on-screen caption in {lang_instruction}, or null>"
    }}
  ]
}}

CRITICAL Rules:
- ALL narration + ALL title + ALL text_overlay MUST be in {lang_instruction}. Not English (unless EN was requested).
- The LAST scene's narration MUST end with the CTA "{cta}".
- visual_prompt always stays in English (it feeds an image model).
- Keep narrations punchy and natural — use the requested dialect's authentic words and expressions.
- Return raw JSON only.
"""

    from emergentintegrations.llm.chat import LlmChat, UserMessage
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"vstory-{uuid.uuid4().hex[:10]}",
            system_message=sys_msg,
        )
        chat.with_model("gemini", "gemini-2.5-flash")
        raw = await chat.send_message(UserMessage(text=user_prompt))
        text = _strip_code_fences(str(raw))
        data = json.loads(text)
    except json.JSONDecodeError:
        # Salvage: try to find first { ... } block
        m = re.search(r"\{[\s\S]+\}", text)
        if not m:
            raise HTTPException(status_code=502, detail="AI returned non-JSON storyboard")
        try:
            data = json.loads(m.group(0))
        except Exception:
            raise HTTPException(status_code=502, detail="AI returned malformed storyboard")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storyboard failed: {str(e)[:200]}")

    scenes_raw = data.get("scenes") or []
    if not scenes_raw:
        raise HTTPException(status_code=502, detail="AI returned empty scenes")

    scenes = []
    for i, s in enumerate(scenes_raw[:scene_count]):
        scenes.append(StoryboardScene(
            seq=i + 1,
            narration=str(s.get("narration", "")).strip(),
            visual_prompt=str(s.get("visual_prompt", "")).strip(),
            text_overlay=(str(s["text_overlay"]).strip() if s.get("text_overlay") else None),
        ))

    full_narration = " ".join(sc.narration for sc in scenes)
    return StoryboardResponse(
        title=str(data.get("title", req.product_name))[:120],
        full_narration=full_narration,
        scenes=scenes,
        cta=cta,
        duration_seconds=req.duration_seconds,
        cost=COST_STORYBOARD,
    )


# ═════════════════════════════════════════════════════════════════════════════
# 2) VIDEO GENERATION
# ═════════════════════════════════════════════════════════════════════════════
class VideoScene(BaseModel):
    image_base64: Optional[str] = None    # data URI or raw base64
    image_url: Optional[str] = None       # absolute http(s) url
    narration: str = ""
    text_overlay: Optional[str] = None


class VideoGenerateRequest(BaseModel):
    title: str
    scenes: List[VideoScene]              # 3..8 scenes
    duration_seconds: int = 30            # 15 | 30 | 45 | 60
    voice: str = DEFAULT_VOICE
    full_narration: Optional[str] = None  # if absent, joined from scenes
    logo_base64: Optional[str] = None     # optional watermark (data URI ok)
    brand_color: str = "#7c3aed"
    cta: Optional[str] = "اطلب الآن"
    lang: str = "ar"


class VideoGenerateResponse(BaseModel):
    video_url: str        # /api/static/videos/xxx.mp4
    audio_url: str        # /api/static/videos/xxx.mp3
    duration_seconds: int
    voice_used: str
    cost: int
    scenes_count: int


def _decode_image(data: str, dest: Path) -> bool:
    """Accept data URI or pure base64; write PNG/JPG bytes to dest. Returns success."""
    if not data:
        return False
    try:
        if data.startswith("data:"):
            data = data.split(",", 1)[1]
        raw = base64.b64decode(data)
        dest.write_bytes(raw)
        return dest.stat().st_size > 200
    except Exception as e:
        logger.warning(f"image decode failed: {e}")
        return False


async def _download_image(url: str, dest: Path) -> bool:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as cli:
            r = await cli.get(url)
            if r.status_code == 200 and len(r.content) > 200:
                dest.write_bytes(r.content)
                return True
    except Exception as e:
        logger.warning(f"image download failed {url}: {e}")
    return False


def _ffmpeg(args: List[str], timeout: int = 180) -> None:
    """Run ffmpeg with given args; raise HTTPException on failure."""
    try:
        proc = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
            capture_output=True, text=True, timeout=timeout,
        )
        if proc.returncode != 0:
            err = (proc.stderr or "")[-400:]
            logger.error(f"ffmpeg failed: {err}")
            raise HTTPException(status_code=500, detail=f"ffmpeg failed: {err}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="ffmpeg timeout")


@router.post("/generate", response_model=VideoGenerateResponse)
async def generate_video(req: VideoGenerateRequest):
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
    if req.duration_seconds not in (15, 30, 45, 60):
        raise HTTPException(status_code=400, detail="duration_seconds must be 15/30/45/60")
    if not req.scenes or len(req.scenes) < 1:
        raise HTTPException(status_code=400, detail="at least 1 scene required")
    if len(req.scenes) > 8:
        raise HTTPException(status_code=400, detail="max 8 scenes")

    voice_cfg = ZENREX_VOICE_MAP.get(req.voice) or ZENREX_VOICE_MAP[DEFAULT_VOICE]
    job_id = uuid.uuid4().hex[:14]
    work_dir = TMP_DIR / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ── 1) Resolve images ────────────────────────────────────────────────
        image_paths: List[Path] = []
        for idx, sc in enumerate(req.scenes):
            dest = work_dir / f"scene_{idx:02d}.jpg"
            ok = False
            if sc.image_base64:
                ok = _decode_image(sc.image_base64, dest)
            if not ok and sc.image_url:
                ok = await _download_image(sc.image_url, dest)
            if not ok:
                # fallback solid-color slide
                _ffmpeg([
                    "-f", "lavfi", "-i", f"color=c={req.brand_color}:s=1080x1920:d=1",
                    "-frames:v", "1", str(dest)
                ])
            image_paths.append(dest)

        scene_count = len(image_paths)
        per_scene = req.duration_seconds / scene_count

        # ── 2) Generate TTS narration ────────────────────────────────────────
        narration = (req.full_narration or
                     " ".join(s.narration for s in req.scenes if s.narration)).strip()
        if not narration:
            narration = req.title
        if len(narration) > 4000:
            narration = narration[:4000]

        audio_path = work_dir / "narration.mp3"
        try:
            from emergentintegrations.llm.openai import OpenAITextToSpeech
            tts = OpenAITextToSpeech(api_key=api_key)
            audio_bytes = await tts.generate_speech(
                text=narration,
                model=voice_cfg["model"],
                voice=voice_cfg["voice"],
                response_format="mp3",
                speed=1.0,
            )
            audio_path.write_bytes(audio_bytes)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)[:200]}")

        # ── 3) Build slideshow with ffmpeg ───────────────────────────────────
        # Vertical 1080x1920 (social-first). Each image gets a subtle ken-burns zoom.
        # We assemble per-scene MP4 clips, then concat, then mix with audio.
        clips_list = work_dir / "clips.txt"
        with clips_list.open("w") as lf:
            for idx, ip in enumerate(image_paths):
                clip_path = work_dir / f"clip_{idx:02d}.mp4"
                # Scale + pad to 1080x1920, simple zoompan effect, 30fps
                vf = (
                    "scale=1080:1920:force_original_aspect_ratio=increase,"
                    "crop=1080:1920,"
                    "zoompan=z='min(zoom+0.0010,1.15)':d=" + str(int(per_scene * 30)) +
                    ":s=1080x1920:fps=30"
                )
                _ffmpeg([
                    "-loop", "1", "-i", str(ip),
                    "-t", f"{per_scene:.3f}",
                    "-vf", vf,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                    "-preset", "veryfast",
                    str(clip_path),
                ])
                lf.write(f"file '{clip_path.name}'\n")

        slideshow = work_dir / "slideshow.mp4"
        _ffmpeg([
            "-f", "concat", "-safe", "0", "-i", str(clips_list),
            "-c", "copy", str(slideshow),
        ])

        # ── 4) Logo watermark (optional) ─────────────────────────────────────
        watermarked = slideshow
        if req.logo_base64:
            logo_path = work_dir / "logo.png"
            if _decode_image(req.logo_base64, logo_path):
                watermarked = work_dir / "watermarked.mp4"
                # Overlay logo top-right at ~160px wide
                _ffmpeg([
                    "-i", str(slideshow), "-i", str(logo_path),
                    "-filter_complex",
                    "[1:v]scale=160:-1[lg];[0:v][lg]overlay=W-w-40:40",
                    "-c:a", "copy",
                    str(watermarked),
                ])

        # ── 5) Title + CTA text overlay ──────────────────────────────────────
        titled = work_dir / "titled.mp4"
        # Try to find an Arabic-capable font, fallback to default
        font_candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        font = next((f for f in font_candidates if os.path.exists(f)), None)

        # Escape title/cta for ffmpeg drawtext (single quotes + colons)
        def _esc(t: str) -> str:
            return (t or "").replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019")

        title_txt = _esc(req.title)[:60]
        cta_txt = _esc(req.cta or "")[:30]

        if font and (title_txt or cta_txt):
            drawtexts = []
            if title_txt:
                drawtexts.append(
                    f"drawtext=fontfile='{font}':text='{title_txt}':"
                    f"fontsize=58:fontcolor=white:borderw=4:bordercolor=black@0.6:"
                    f"x=(w-text_w)/2:y=140"
                )
            if cta_txt:
                drawtexts.append(
                    f"drawtext=fontfile='{font}':text='{cta_txt}':"
                    f"fontsize=72:fontcolor=white:box=1:boxcolor={req.brand_color}@0.85:"
                    f"boxborderw=24:x=(w-text_w)/2:y=h-260:"
                    f"enable='gte(t,{max(0, req.duration_seconds - 4)})'"
                )
            _ffmpeg([
                "-i", str(watermarked),
                "-vf", ",".join(drawtexts),
                "-c:a", "copy",
                str(titled),
            ])
        else:
            shutil.copy(watermarked, titled)

        # ── 6) Mux audio (pad audio with silence to match target duration) ───
        # Pad audio to exact target duration so the video is always the
        # advertised length (e.g. exactly 30s) — never cut short by TTS length.
        padded_audio = work_dir / "narration_padded.m4a"
        _ffmpeg([
            "-i", str(audio_path),
            "-af", f"apad=whole_dur={req.duration_seconds}",
            "-t", str(req.duration_seconds),
            "-c:a", "aac", "-b:a", "192k",
            str(padded_audio),
        ])

        final_path = VIDEOS_DIR / f"{job_id}.mp4"
        _ffmpeg([
            "-i", str(titled), "-i", str(padded_audio),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "copy",
            "-t", str(req.duration_seconds),
            str(final_path),
        ])

        # Persist audio too (so the user can preview/download voiceover alone)
        public_audio = VIDEOS_DIR / f"{job_id}.mp3"
        shutil.copy(audio_path, public_audio)

        cost = (req.duration_seconds // 5) * COST_PER_5_SECONDS

        return VideoGenerateResponse(
            video_url=f"/api/static/videos/{job_id}.mp4",
            audio_url=f"/api/static/videos/{job_id}.mp3",
            duration_seconds=req.duration_seconds,
            voice_used=req.voice,
            cost=cost,
            scenes_count=scene_count,
        )
    finally:
        # Cleanup tmp working dir
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


# ═════════════════════════════════════════════════════════════════════════════
# 3) ZENREX CREDITS — mock recharge endpoint (synced with main Zenrex wallet)
# ═════════════════════════════════════════════════════════════════════════════
class RechargeRequest(BaseModel):
    package_id: str       # 'starter' | 'pro' | 'agency' | 'enterprise'
    payment_method: str   # 'mada' | 'visa' | 'mastercard' | 'apple_pay' | 'stc_pay'
    user_id: Optional[str] = "demo_user"


class RechargeResponse(BaseModel):
    success: bool
    transaction_id: str
    credits_added: int
    new_balance_hint: int
    package: str
    payment_method: str
    receipt_number: str


CREDIT_PACKAGES = {
    "starter":    {"credits": 500,   "price_sar": 49,   "label_ar": "البداية",  "label_en": "Starter"},
    "pro":        {"credits": 2500,  "price_sar": 199,  "label_ar": "المحترف", "label_en": "Pro"},
    "agency":     {"credits": 6000,  "price_sar": 449,  "label_ar": "الوكالة",  "label_en": "Agency"},
    "enterprise": {"credits": 15000, "price_sar": 999,  "label_ar": "المؤسسي", "label_en": "Enterprise"},
}


@router.get("/packages")
async def list_packages():
    return {"packages": [{"id": k, **v} for k, v in CREDIT_PACKAGES.items()]}


@router.post("/recharge", response_model=RechargeResponse)
async def recharge_credits(req: RechargeRequest):
    """Mock recharge — simulates the inline payment gateway flow.

    In production this should call the real Zenrex wallet service.
    """
    pkg = CREDIT_PACKAGES.get(req.package_id)
    if not pkg:
        raise HTTPException(status_code=400, detail="unknown package")
    if req.payment_method not in ("mada", "visa", "mastercard", "apple_pay", "stc_pay"):
        raise HTTPException(status_code=400, detail="unknown payment method")

    tx = f"ZX-{uuid.uuid4().hex[:10].upper()}"
    receipt = f"RCT-{uuid.uuid4().hex[:8].upper()}"
    # Simulate gateway latency
    await asyncio.sleep(0.4)
    return RechargeResponse(
        success=True,
        transaction_id=tx,
        credits_added=pkg["credits"],
        new_balance_hint=pkg["credits"],
        package=req.package_id,
        payment_method=req.payment_method,
        receipt_number=receipt,
    )


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "voices": list(ZENREX_VOICE_MAP.keys()),
        "packages": list(CREDIT_PACKAGES.keys()),
    }
