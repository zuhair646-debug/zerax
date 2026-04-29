"""
Zitex Site Banner & Stories
───────────────────────────
The platform's own marketing site (NOT the multi-tenant storefronts) gets the same
treatment storefronts get: a rotating animated banner + stories ribbon, displayed in
two places:
  • Outside  — Landing/Login/Register pages (above the fold)
  • Inside   — Authenticated dashboard root (above sections)

Data model:
  • Collection `site_banner_slides`    — array of slides for the rotating banner
  • Collection `site_stories`          — circular stories below the banner

Routes:
  Public (no auth):
    GET  /api/site/banner       → {slides, rotate_seconds}
    GET  /api/site/stories      → {stories}

  Admin (Bearer JWT, role=owner):
    POST   /api/site/banner/slides
    PATCH  /api/site/banner/slides/{id}
    DELETE /api/site/banner/slides/{id}
    POST   /api/site/banner/reorder            body: {ids: [...]}
    PUT    /api/site/banner/settings           body: {rotate_seconds, animation}

    POST   /api/site/stories
    PATCH  /api/site/stories/{id}
    DELETE /api/site/stories/{id}
    POST   /api/site/stories/reorder           body: {ids: [...]}

    POST   /api/site/media/generate-image      body: {prompt, target: 'banner'|'story'}
    POST   /api/site/media/generate-video      body: {prompt, duration, size, target}
    GET    /api/site/media/jobs/{id}
"""
import asyncio
import base64
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel


log = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


_SETTINGS_DOC_ID = "global"
MAX_DATA_URL_SIZE = 10 * 1024 * 1024  # 10 MB cap

_VIDEO_JOBS: Dict[str, Dict[str, Any]] = {}


class SlideIn(BaseModel):
    type: str = "image"            # 'image' | 'video' | 'animated'
    media_url: str = ""
    poster_url: Optional[str] = ""
    title: Optional[str] = ""
    subtitle: Optional[str] = ""
    cta_text: Optional[str] = ""
    cta_link: Optional[str] = ""
    duration_sec: Optional[int] = 6
    visible: Optional[bool] = True
    # placement: where this slide appears
    placement: Optional[str] = "both"  # 'outside' | 'inside' | 'both'


class SlidePatch(BaseModel):
    type: Optional[str] = None
    media_url: Optional[str] = None
    poster_url: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    cta_text: Optional[str] = None
    cta_link: Optional[str] = None
    duration_sec: Optional[int] = None
    visible: Optional[bool] = None
    placement: Optional[str] = None


class BannerSettingsIn(BaseModel):
    rotate_seconds: Optional[int] = None     # how often to switch slides (3..20)
    animation: Optional[str] = None          # 'fade' | 'slide' | 'kenburns'
    overlay_opacity: Optional[float] = None


class StoryIn(BaseModel):
    type: str = "image"
    media_url: str = ""
    poster_url: Optional[str] = ""
    caption: Optional[str] = ""
    link: Optional[str] = ""
    duration_sec: Optional[int] = 6
    visible: Optional[bool] = True
    placement: Optional[str] = "both"


class StoryPatch(BaseModel):
    media_url: Optional[str] = None
    poster_url: Optional[str] = None
    caption: Optional[str] = None
    link: Optional[str] = None
    duration_sec: Optional[int] = None
    visible: Optional[bool] = None
    placement: Optional[str] = None


class GenImageIn(BaseModel):
    prompt: str
    target: Optional[str] = "story"   # 'banner' | 'story'


class GenVideoIn(BaseModel):
    prompt: str
    duration: Optional[int] = 4
    size: Optional[str] = "1280x720"
    target: Optional[str] = "banner"


def _validate_data_url(url: str) -> None:
    if url.startswith("data:") and len(url) > MAX_DATA_URL_SIZE:
        raise HTTPException(413, f"الملف كبير جداً (الحد {MAX_DATA_URL_SIZE // (1024*1024)} ميجا)")


# ─────────────────────────────────────────────────────────
# AI media generation (shared with storefront stories module)
# ─────────────────────────────────────────────────────────

async def _generate_image_nano_banana(prompt: str) -> str:
    api_key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not api_key:
        raise HTTPException(500, "AI service unavailable")
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=api_key,
            session_id=f"site-img-{uuid.uuid4().hex[:10]}",
            system_message="You are a luxury brand-image assistant. Always produce a single high-quality cinematic image.",
        )
        chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
        _, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
        if not images:
            raise HTTPException(500, "لم يُنتَج أي صورة")
        img = images[0]
        return f"data:{img.get('mime_type', 'image/png')};base64,{img['data']}"
    except HTTPException:
        raise
    except Exception as e:
        log.error("site image gen failed: %s", e)
        raise HTTPException(500, f"فشل توليد الصورة: {str(e)[:200]}")


def _generate_video_sora_sync(prompt: str, duration: int, size: str) -> Optional[bytes]:
    from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
    api_key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not api_key:
        return None
    vg = OpenAIVideoGeneration(api_key=api_key)
    return vg.text_to_video(prompt=prompt, model="sora-2", size=size,
                             duration=duration, max_wait_time=900)


async def _run_video_job(job_id: str, prompt: str, duration: int, size: str,
                         target: str, database) -> None:
    try:
        _VIDEO_JOBS[job_id]["status"] = "processing"
        video_bytes = await asyncio.get_event_loop().run_in_executor(
            None, _generate_video_sora_sync, prompt, duration, size,
        )
        if not video_bytes:
            _VIDEO_JOBS[job_id].update({"status": "failed", "error": "Sora returned empty"})
            return
        b64 = base64.b64encode(video_bytes).decode()
        media_url = f"data:video/mp4;base64,{b64}"
        new_id = None
        if target == "banner":
            new_id = await _push_slide(database, {
                "type": "video", "media_url": media_url,
                "title": prompt[:60], "subtitle": "", "cta_text": "", "cta_link": "",
                "duration_sec": min(12, duration), "visible": True, "placement": "both",
                "ai_generated": True,
            })
        else:
            new_id = await _push_story(database, {
                "type": "video", "media_url": media_url,
                "caption": prompt[:120], "duration_sec": min(15, duration),
                "visible": True, "placement": "both", "ai_generated": True,
            })
        _VIDEO_JOBS[job_id].update({
            "status": "done", "id": new_id, "target": target, "completed_at": _iso_now(),
        })
    except Exception as e:
        log.error("site video job failed: %s", e)
        _VIDEO_JOBS[job_id].update({"status": "failed", "error": str(e)[:300]})


async def _push_slide(database, doc: Dict[str, Any]) -> str:
    slide = {
        "id": f"sl-{uuid.uuid4().hex[:10]}",
        "type": doc.get("type", "image"),
        "media_url": doc.get("media_url", ""),
        "poster_url": doc.get("poster_url", ""),
        "title": (doc.get("title") or "")[:120],
        "subtitle": (doc.get("subtitle") or "")[:200],
        "cta_text": (doc.get("cta_text") or "")[:60],
        "cta_link": doc.get("cta_link", ""),
        "duration_sec": int(doc.get("duration_sec") or 6),
        "visible": bool(doc.get("visible", True)),
        "placement": doc.get("placement", "both"),
        "ai_generated": bool(doc.get("ai_generated", False)),
        "order": int(datetime.now(timezone.utc).timestamp()),
        "created_at": _iso_now(),
    }
    await database.site_banner_slides.insert_one(slide.copy())
    return slide["id"]


async def _push_story(database, doc: Dict[str, Any]) -> str:
    s = {
        "id": f"st-{uuid.uuid4().hex[:10]}",
        "type": doc.get("type", "image"),
        "media_url": doc.get("media_url", ""),
        "poster_url": doc.get("poster_url", ""),
        "caption": (doc.get("caption") or "")[:200],
        "link": doc.get("link", ""),
        "duration_sec": int(doc.get("duration_sec") or 6),
        "visible": bool(doc.get("visible", True)),
        "placement": doc.get("placement", "both"),
        "ai_generated": bool(doc.get("ai_generated", False)),
        "order": int(datetime.now(timezone.utc).timestamp()),
        "created_at": _iso_now(),
    }
    await database.site_stories.insert_one(s.copy())
    return s["id"]


# ─────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────

def init_routes(database, get_current_user, owner_dep) -> APIRouter:
    """`get_current_user` = generic JWT auth dep; `owner_dep` = require owner role."""
    r = APIRouter(prefix="/site", tags=["site"])

    # ─── PUBLIC: banner + stories ───
    @r.get("/banner")
    async def _public_banner(placement: Optional[str] = None):
        q: Dict[str, Any] = {"visible": True}
        if placement:
            q["placement"] = {"$in": [placement, "both"]}
        cur = database.site_banner_slides.find(q, {"_id": 0}).sort("order", 1)
        slides = await cur.to_list(50)
        s = await database.site_settings.find_one({"_id": _SETTINGS_DOC_ID}, {"_id": 0}) or {}
        return {
            "slides": slides,
            "rotate_seconds": int(s.get("rotate_seconds") or 6),
            "animation": s.get("animation") or "fade",
            "overlay_opacity": s.get("overlay_opacity") if s.get("overlay_opacity") is not None else 0.5,
        }

    @r.get("/stories")
    async def _public_stories(placement: Optional[str] = None):
        q: Dict[str, Any] = {"visible": True}
        if placement:
            q["placement"] = {"$in": [placement, "both"]}
        cur = database.site_stories.find(q, {"_id": 0}).sort("order", 1)
        return {"stories": await cur.to_list(50)}

    # ─── ADMIN: banner CRUD ───
    @r.post("/banner/slides")
    async def _slide_create(body: SlideIn, _u: dict = Depends(owner_dep)):
        _validate_data_url(body.media_url or "")
        if not body.media_url:
            raise HTTPException(400, "media_url required")
        sid = await _push_slide(database, body.dict())
        return {"ok": True, "id": sid}

    @r.patch("/banner/slides/{slide_id}")
    async def _slide_patch(slide_id: str, body: SlidePatch, _u: dict = Depends(owner_dep)):
        upd = {k: v for k, v in body.dict().items() if v is not None}
        if "media_url" in upd:
            _validate_data_url(upd["media_url"])
        if not upd:
            raise HTTPException(400, "nothing to update")
        upd["updated_at"] = _iso_now()
        res = await database.site_banner_slides.update_one({"id": slide_id}, {"$set": upd})
        if res.matched_count == 0:
            raise HTTPException(404, "Not found")
        return {"ok": True}

    @r.delete("/banner/slides/{slide_id}")
    async def _slide_delete(slide_id: str, _u: dict = Depends(owner_dep)):
        await database.site_banner_slides.delete_one({"id": slide_id})
        return {"ok": True}

    class ReorderIn(BaseModel):
        ids: List[str]

    @r.post("/banner/reorder")
    async def _slide_reorder(body: ReorderIn, _u: dict = Depends(owner_dep)):
        for i, sid in enumerate(body.ids):
            await database.site_banner_slides.update_one({"id": sid}, {"$set": {"order": i}})
        return {"ok": True}

    @r.put("/banner/settings")
    async def _banner_settings(body: BannerSettingsIn, _u: dict = Depends(owner_dep)):
        upd = {k: v for k, v in body.dict().items() if v is not None}
        if "rotate_seconds" in upd:
            upd["rotate_seconds"] = max(2, min(30, int(upd["rotate_seconds"])))
        if upd:
            upd["updated_at"] = _iso_now()
            await database.site_settings.update_one(
                {"_id": _SETTINGS_DOC_ID}, {"$set": upd}, upsert=True,
            )
        cur = await database.site_settings.find_one({"_id": _SETTINGS_DOC_ID}, {"_id": 0})
        return cur or {}

    # ─── ADMIN: stories CRUD ───
    @r.post("/stories")
    async def _story_create(body: StoryIn, _u: dict = Depends(owner_dep)):
        _validate_data_url(body.media_url or "")
        if not body.media_url:
            raise HTTPException(400, "media_url required")
        sid = await _push_story(database, body.dict())
        return {"ok": True, "id": sid}

    @r.patch("/stories/{story_id}")
    async def _story_patch(story_id: str, body: StoryPatch, _u: dict = Depends(owner_dep)):
        upd = {k: v for k, v in body.dict().items() if v is not None}
        if "media_url" in upd:
            _validate_data_url(upd["media_url"])
        if not upd:
            raise HTTPException(400, "nothing to update")
        upd["updated_at"] = _iso_now()
        res = await database.site_stories.update_one({"id": story_id}, {"$set": upd})
        if res.matched_count == 0:
            raise HTTPException(404, "Not found")
        return {"ok": True}

    @r.delete("/stories/{story_id}")
    async def _story_delete(story_id: str, _u: dict = Depends(owner_dep)):
        await database.site_stories.delete_one({"id": story_id})
        return {"ok": True}

    @r.post("/stories/reorder")
    async def _story_reorder(body: ReorderIn, _u: dict = Depends(owner_dep)):
        for i, sid in enumerate(body.ids):
            await database.site_stories.update_one({"id": sid}, {"$set": {"order": i}})
        return {"ok": True}

    # ─── ADMIN: AI media generation ───
    @r.post("/media/generate-image")
    async def _gen_image(body: GenImageIn, _u: dict = Depends(owner_dep)):
        prompt = (body.prompt or "").strip()
        if not prompt:
            raise HTTPException(400, "prompt required")
        media_url = await _generate_image_nano_banana(prompt[:800])
        target = body.target or "story"
        if target == "banner":
            sid = await _push_slide(database, {
                "type": "image", "media_url": media_url,
                "title": prompt[:60], "duration_sec": 6, "visible": True,
                "placement": "both", "ai_generated": True,
            })
            return {"ok": True, "target": "banner", "id": sid, "media_url": media_url}
        sid = await _push_story(database, {
            "type": "image", "media_url": media_url,
            "caption": prompt[:120], "duration_sec": 6, "visible": True,
            "placement": "both", "ai_generated": True,
        })
        return {"ok": True, "target": "story", "id": sid, "media_url": media_url}

    @r.post("/media/generate-video")
    async def _gen_video(body: GenVideoIn, _u: dict = Depends(owner_dep)):
        prompt = (body.prompt or "").strip()
        if not prompt:
            raise HTTPException(400, "prompt required")
        duration = int(body.duration or 4)
        if duration not in (4, 8, 12):
            duration = 4
        size = body.size or "1280x720"
        if size not in ("1280x720", "1792x1024", "1024x1792", "1024x1024"):
            size = "1280x720"
        target = body.target or "banner"
        job_id = f"vj-{uuid.uuid4().hex[:12]}"
        _VIDEO_JOBS[job_id] = {
            "id": job_id, "prompt": prompt[:200],
            "status": "queued", "queued_at": _iso_now(), "target": target,
        }
        asyncio.create_task(_run_video_job(job_id, prompt, duration, size, target, database))
        return {"ok": True, "job_id": job_id, "status": "queued",
                "estimated_seconds": 120 if duration == 4 else 240}

    @r.get("/media/jobs/{job_id}")
    async def _job(job_id: str, _u: dict = Depends(owner_dep)):
        j = _VIDEO_JOBS.get(job_id)
        if not j:
            raise HTTPException(404, "Job not found")
        return j

    return r
