"""
Video Studio v2 — Multi-stage cinematic workflow with series memory.

Pipeline:
  ┌──────────────┐   ┌──────────────┐   ┌────────────────┐   ┌──────────┐   ┌────────────┐
  │ 1. CHAT      │ → │ 2. SCRIPT    │ → │ 3. STORYBOARD  │ → │ 4. APPROVE│ → │ 5. RENDER  │
  │  brief +     │   │  script +    │   │  preview imgs  │   │  client   │   │  pay+Sora 2│
  │  intent      │   │  shot list   │   │  (FREE)        │   │  signs    │   │  per shot  │
  └──────────────┘   └──────────────┘   └────────────────┘   └──────────┘   └────────────┘

Key features:
  • Series memory — episodes share characters, style seed, color palette,
    so episode N+1 looks consistent with N. Stored in
    `video_series` (one doc per series) and `video_episodes` (one doc per episode).
  • Free until render — the client only pays when they tap "موافق ابدأ الإنتاج".
  • Storyboard images use Nano Banana (Gemini, via EMERGENT_LLM_KEY).
  • Final render uses Sora 2 via emergentintegrations.

Endpoints:
  POST /api/video-studio/series                   — list user's series
  POST /api/video-studio/series/create            — new series (or auto)
  POST /api/video-studio/chat                     — conversational session (uses SectionAgent)
  POST /api/video-studio/script                   — generate/iterate script + shot list (free)
  POST /api/video-studio/storyboard               — generate preview images for shots (free)
  POST /api/video-studio/approve                  — gate: snapshot what will be billed
  POST /api/video-studio/render                   — PAID — deduct credits + Sora 2
  GET  /api/video-studio/episode/{id}             — full episode state
  GET  /api/video-studio/series/{id}/episodes     — list episodes in a series
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
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ════════════════════════════════════════════════════════════════════════
# PRICING — only billed at render step
# ════════════════════════════════════════════════════════════════════════
PRICE_PER_SHOT_4S = 8         # credits — Sora 2 ~4s shot
PRICE_PER_SHOT_8S = 14
PRICE_PER_SHOT_12S = 20
PRICE_STORYBOARD_BONUS = 0    # free, period


def shot_price(duration_seconds: int) -> int:
    if duration_seconds <= 4:
        return PRICE_PER_SHOT_4S
    if duration_seconds <= 8:
        return PRICE_PER_SHOT_8S
    return PRICE_PER_SHOT_12S


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
    style_direction: str = ""  # e.g. "anime cyberpunk", "documentary 35mm"
    main_characters: List[Dict[str, str]] = []  # [{name, desc}]


class ScriptIn(BaseModel):
    session_id: str
    series_id: Optional[str] = None
    brief: str = Field(..., min_length=4)
    episode_number: Optional[int] = None
    requested_shots: int = Field(default=4, ge=1, le=12)
    shot_duration: int = Field(default=8, ge=4, le=12)


class StoryboardIn(BaseModel):
    episode_id: str


class ApproveIn(BaseModel):
    episode_id: str
    confirmed: bool = True


class RenderIn(BaseModel):
    episode_id: str


# ════════════════════════════════════════════════════════════════════════
# Script LLM helper — produces structured shots in JSON
# ════════════════════════════════════════════════════════════════════════
SCRIPT_SYSTEM = (
    "أنت مخرج سينمائي سعودي محترف. مهمتك تحويل فكرة العميل إلى سيناريو منظّم. "
    "أرجع JSON صالح فقط — بدون نص خارج JSON. الـschema:\n"
    "{\n"
    '  "title": "عنوان قصير",\n'
    '  "logline": "ملخص بسطر",\n'
    '  "characters": [{"name": "...", "desc": "وصف بصري دقيق (شعر/ملابس/عمر/مزاج)"}],\n'
    '  "style": "ستايل بصري عام (lighting + color + camera) بالإنجليزية cinematic",\n'
    '  "shots": [\n'
    "    {\n"
    '      "n": 1,\n'
    '      "title_ar": "عنوان اللقطة بالعربي",\n'
    '      "narration_ar": "نص الراوي/الحوار (اختياري)",\n'
    '      "visual_en": "Cinematic English prompt — describe action, framing, lens, lighting, motion",\n'
    '      "duration": 8\n'
    "    }\n"
    "  ]\n"
    "}"
)


async def _generate_script(brief: str, *, series_ctx: Optional[Dict[str, Any]] = None,
                           requested_shots: int = 4, shot_duration: int = 8) -> Dict[str, Any]:
    """Call OpenAI/Claude to produce a structured script JSON."""
    extra_ctx = ""
    if series_ctx:
        extra_ctx = (
            "\n\n📌 سياق السلسلة (حافظ على التناسق):\n"
            + json.dumps(series_ctx, ensure_ascii=False)[:1500]
        )

    user_prompt = (
        f"البريف من العميل:\n{brief}\n\n"
        f"عدد اللقطات المطلوبة: {requested_shots}\n"
        f"مدة كل لقطة (تقريباً): {shot_duration} ثانية\n"
        f"{extra_ctx}\n\n"
        "أعد JSON فقط."
    )

    oai = (os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    if oai:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {oai}"},
                    json={
                        "model": "gpt-4o",
                        "messages": [
                            {"role": "system", "content": SCRIPT_SYSTEM},
                            {"role": "user", "content": user_prompt},
                        ],
                        "response_format": {"type": "json_object"},
                        "max_tokens": 2500,
                    },
                )
                if r.status_code == 200:
                    raw = r.json()["choices"][0]["message"]["content"]
                    return json.loads(raw)
        except Exception as e:
            logger.warning(f"script openai failed: {e}")

    # Fallback: Claude via Emergent key
    em_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if em_key:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
            chat = LlmChat(api_key=em_key, session_id=str(uuid.uuid4()),
                           system_message=SCRIPT_SYSTEM + "\n\nأعد JSON فقط، بدون أي شرح خارج JSON.")
            chat = chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            chat = chat.with_max_tokens(2500)
            resp = await chat.send_message(UserMessage(text=user_prompt))
            raw = str(resp)
            # Try to extract JSON block
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                return json.loads(m.group(0))
        except Exception as e:
            logger.warning(f"script claude failed: {e}")

    raise HTTPException(503, "تعذّر توليد السيناريو — تأكد من مفاتيح الذكاء.")


# ════════════════════════════════════════════════════════════════════════
# Storyboard images — Nano Banana via emergentintegrations
# ════════════════════════════════════════════════════════════════════════
STORYBOARD_DIR = Path("/app/backend/static/video_storyboards")
STORYBOARD_DIR.mkdir(parents=True, exist_ok=True)


async def _gen_storyboard_image(prompt: str, *, style: str = "") -> Optional[str]:
    """Return a public URL for a generated storyboard frame, or None."""
    em_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not em_key:
        return None
    try:
        from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration  # type: ignore
    except Exception:
        OpenAIImageGeneration = None

    # Build the visual prompt with consistent style seed if provided
    full = prompt.strip()
    if style:
        full = f"{full}. Visual style: {style}. Cinematic frame, 16:9, high detail."
    else:
        full = f"{full}. Cinematic frame, 16:9, high detail, professional lighting."

    # Try Gemini Nano Banana via emergentintegrations
    try:
        from emergentintegrations.llm.gemini.image_generation import GeminiImageGeneration  # type: ignore
        gen = GeminiImageGeneration(api_key=em_key)
        images = await gen.generate_images(
            prompt=full,
            model="gemini-2.5-flash-image-preview",
            number_of_images=1,
        )
        if images:
            img_bytes = images[0]
            fname = f"{uuid.uuid4().hex}.png"
            (STORYBOARD_DIR / fname).write_bytes(img_bytes)
            return f"/api/video-studio/storyboard-img/{fname}"
    except Exception as e:
        logger.warning(f"nano banana failed: {e}")

    # Last resort: OpenAI gpt-image-1
    if OpenAIImageGeneration:
        try:
            gen = OpenAIImageGeneration(api_key=em_key)
            images = await gen.generate_images(prompt=full, model="gpt-image-1",
                                               number_of_images=1, size="1536x1024")
            if images:
                img_bytes = images[0]
                fname = f"{uuid.uuid4().hex}.png"
                (STORYBOARD_DIR / fname).write_bytes(img_bytes)
                return f"/api/video-studio/storyboard-img/{fname}"
        except Exception as e:
            logger.warning(f"openai image fallback failed: {e}")
    return None


# ════════════════════════════════════════════════════════════════════════
# Sora 2 render — for final stage only
# ════════════════════════════════════════════════════════════════════════
async def _render_shot(prompt: str, duration: int) -> Optional[str]:
    """Render one shot via Sora 2. Returns base64 data URL or None."""
    em_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not em_key:
        return None
    try:
        from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration  # type: ignore
        gen = OpenAIVideoGeneration(api_key=em_key)
        sora_dur = min(12, max(4, duration))
        video_bytes = gen.text_to_video(
            prompt=prompt, model="sora-2",
            size="1280x720", duration=sora_dur, max_wait_time=600,
        )
        if video_bytes:
            return "data:video/mp4;base64," + base64.b64encode(video_bytes).decode("utf-8")
    except Exception as e:
        logger.error(f"sora render failed: {e}")
    return None


# ════════════════════════════════════════════════════════════════════════
# Router factory
# ════════════════════════════════════════════════════════════════════════
def create_video_studio_router(db, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/api/video-studio", tags=["video-studio"])

    # Bind shared agent core (idempotent)
    try:
        from modules.shared import bind_db as _shared_bind, SectionAgent
        _shared_bind(db)
    except Exception as e:
        logger.warning(f"shared bind failed: {e}")
        SectionAgent = None  # type: ignore

    async def _get_credits(user_id: str) -> int:
        d = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
        return int((d or {}).get("credits", 0))

    # ── Series CRUD ────────────────────────────────────────────────────
    @router.get("/series")
    async def list_series(user=Depends(get_current_user)):
        cur = db.video_series.find({"user_id": user["user_id"]}, {"_id": 0}).sort([("updated_at", -1)]).limit(50)
        items = await cur.to_list(50)
        # Decorate with episode count
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
        # Build a series-aware persona addition
        extra = ""
        if payload.series_id:
            s = await db.video_series.find_one({"id": payload.series_id, "user_id": user["user_id"]}, {"_id": 0})
            if s:
                eps_count = await db.video_episodes.count_documents({"series_id": s["id"]})
                extra = (
                    f"\n\n📺 المستخدم يعمل على سلسلة '{s.get('title')}' (الحلقة رقم {eps_count + 1}). "
                    f"الأسلوب المرجعي: {s.get('style_direction') or 'غير محدد'}. "
                    f"الشخصيات الرئيسية: {json.dumps(s.get('main_characters', []), ensure_ascii=False)}. "
                    "حافظ على الـlook نفسه ولا تكسر الشخصيات بين الحلقات."
                )
        agent = SectionAgent("video", extra_persona=extra)
        result = await agent.chat(user["user_id"], payload.message, session_id=payload.session_id or "")
        return result

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
            # Pull prior episode summaries for continuity
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
        )

        # Estimate cost (not deducted yet)
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
            "script": script,
            "shots": shots,
            "storyboard": [],          # filled by /storyboard step
            "estimated_cost": cost,
            "stage": "script",         # script → storyboard → approved → rendered
            "approved_at": None,
            "rendered_at": None,
            "credits_charged": 0,
            "final_clips": [],
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

        style = (ep.get("script") or {}).get("style", "")
        shots = ep.get("shots") or []
        # Generate in parallel with concurrency cap
        sem = asyncio.Semaphore(3)

        async def _one(shot: Dict[str, Any]) -> Dict[str, Any]:
            async with sem:
                url = await _gen_storyboard_image(shot.get("visual_en") or shot.get("title_ar") or "", style=style)
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

    # ── Approve gate (FREE, just records intent) ───────────────────────
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
        # Confirm cost snapshot
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
        cost = ep.get("estimated_cost", 0)

        # Atomic deduction
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

        # Render shots sequentially (Sora 2 is heavy)
        final_clips: List[Dict[str, Any]] = []
        failed = 0
        for shot in (ep.get("shots") or []):
            prompt = shot.get("visual_en") or shot.get("title_ar") or ""
            duration = int(shot.get("duration") or 8)
            clip = await _render_shot(prompt, duration)
            final_clips.append({
                "n": shot.get("n"),
                "title_ar": shot.get("title_ar"),
                "duration": duration,
                "video_url": clip,
                "ok": clip is not None,
            })
            if clip is None:
                failed += 1

        # If everything failed → refund
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
        # Touch series timestamp
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

    # ── Static asset serving for storyboard previews ───────────────────
    @router.get("/storyboard-img/{filename}")
    async def get_storyboard_img(filename: str):
        from fastapi.responses import FileResponse
        # Prevent path traversal
        if "/" in filename or ".." in filename:
            raise HTTPException(400, "bad filename")
        p = STORYBOARD_DIR / filename
        if not p.exists():
            raise HTTPException(404, "not found")
        return FileResponse(str(p), media_type="image/png")

    return router
