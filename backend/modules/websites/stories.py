"""
Stories + Animated Banner module for Storefronts
─────────────────────────────────────────────────
Lets every storefront owner publish:
  • Stories bar  — Instagram-style circular thumbnails on top of the homepage
  • Animated banner — full-width hero banner with image/video background

Each story / banner item supports:
  • Direct upload (image/video as data-URL)
  • Pasted external URL (e.g. CDN, YouTube embed link)
  • AI-generated image (Nano Banana via Emergent Universal Key)
  • AI-generated video (Sora 2 via Emergent Universal Key — async background job)

Public endpoints (storefront-side):
  GET  /api/websites/public/{slug}/stories    — visible stories for storefront

Client endpoints (require ClientToken):
  GET    /api/websites/client/stories
  POST   /api/websites/client/stories            — create
  PATCH  /api/websites/client/stories/{id}       — update
  DELETE /api/websites/client/stories/{id}
  POST   /api/websites/client/stories/reorder    — body: {ids: [...]}

  GET    /api/websites/client/banner             — get banner config
  PUT    /api/websites/client/banner             — update banner config

  POST   /api/websites/client/media/generate-image  — Nano Banana
  POST   /api/websites/client/media/generate-video  — Sora 2 (returns job_id)
  GET    /api/websites/client/media/jobs/{id}       — poll status
"""
import os
import uuid
import asyncio
import base64
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header as _Header
from pydantic import BaseModel, Field


log = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# In-memory job tracker for video generation (acceptable: jobs are ephemeral, we still persist
# the resulting story in MongoDB on completion).
_VIDEO_JOBS: Dict[str, Dict[str, Any]] = {}


# Maximum sizes/quotas (per-project) to keep storage costs predictable
MAX_STORIES_PER_PROJECT = 30
MAX_DATA_URL_SIZE = 8 * 1024 * 1024  # 8 MB cap on uploaded base64 (≈ 6 MB binary)


class StoryIn(BaseModel):
    type: str = "image"      # 'image' | 'video'
    media_url: str = ""      # data: URL or external URL
    poster_url: Optional[str] = ""  # thumbnail for video stories
    caption: Optional[str] = ""
    link: Optional[str] = ""           # CTA link
    duration_sec: Optional[int] = 6    # seconds shown in the viewer
    visible: Optional[bool] = True


class StoryPatch(BaseModel):
    media_url: Optional[str] = None
    poster_url: Optional[str] = None
    caption: Optional[str] = None
    link: Optional[str] = None
    duration_sec: Optional[int] = None
    visible: Optional[bool] = None


class BannerIn(BaseModel):
    enabled: Optional[bool] = None
    type: Optional[str] = None          # 'image' | 'video'
    media_url: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    cta_text: Optional[str] = None
    cta_link: Optional[str] = None
    animation: Optional[str] = None     # 'kenburns' | 'parallax' | 'fade' | 'none'
    overlay_opacity: Optional[float] = None  # 0..1


class GenImageIn(BaseModel):
    prompt: str
    add_as_story: Optional[bool] = True


class GenVideoIn(BaseModel):
    prompt: str
    duration: Optional[int] = 4         # 4 | 8 | 12 seconds
    size: Optional[str] = "1280x720"    # '1280x720' | '1024x1792' (vertical)
    add_as_story: Optional[bool] = True


def _validate_data_url(url: str) -> None:
    """Reject overly large data: URLs to keep DB writes safe."""
    if url.startswith("data:") and len(url) > MAX_DATA_URL_SIZE:
        raise HTTPException(413, f"الملف كبير جداً (الحد الأقصى {MAX_DATA_URL_SIZE // (1024*1024)} ميجا)")


# ─────────────────────────────────────────────────────────
# Background workers — Nano Banana (image) + Sora 2 (video)
# ─────────────────────────────────────────────────────────

async def _generate_image_nano_banana(prompt: str) -> str:
    """Returns a data URL (PNG) of the generated image, or raises HTTPException."""
    api_key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not api_key:
        raise HTTPException(500, "AI service unavailable")
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=api_key,
            session_id=f"img-{uuid.uuid4().hex[:10]}",
            system_message="You are an image-generation assistant. Always produce one high-quality image matching the user's brief.",
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
        log.error("Nano Banana failed: %s", e)
        raise HTTPException(500, f"فشل توليد الصورة: {str(e)[:200]}")


def _generate_video_sora_sync(prompt: str, duration: int, size: str) -> Optional[bytes]:
    """Sync Sora 2 call — must run in a worker thread (blocks 2-5 minutes)."""
    from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
    api_key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not api_key:
        return None
    vg = OpenAIVideoGeneration(api_key=api_key)
    return vg.text_to_video(
        prompt=prompt, model="sora-2", size=size, duration=duration, max_wait_time=900,
    )


async def _run_video_job(job_id: str, project_id: str, prompt: str, duration: int, size: str,
                         add_as_story: bool, database) -> None:
    """Background task: generates a video then stores it on the project."""
    try:
        _VIDEO_JOBS[job_id]["status"] = "processing"
        _VIDEO_JOBS[job_id]["started_at"] = _iso_now()
        # Run the blocking SDK call in a worker thread
        video_bytes = await asyncio.get_event_loop().run_in_executor(
            None, _generate_video_sora_sync, prompt, duration, size,
        )
        if not video_bytes:
            _VIDEO_JOBS[job_id].update({"status": "failed", "error": "Sora returned empty result"})
            return
        b64 = base64.b64encode(video_bytes).decode()
        media_url = f"data:video/mp4;base64,{b64}"
        story_id = None
        if add_as_story:
            story_id = await _append_story(database, project_id, {
                "type": "video",
                "media_url": media_url,
                "caption": prompt[:120],
                "duration_sec": min(duration, 15),
                "visible": True,
                "ai_generated": True,
            })
        _VIDEO_JOBS[job_id].update({
            "status": "done", "story_id": story_id,
            "media_url": media_url if not add_as_story else None,
            "completed_at": _iso_now(),
        })
    except Exception as e:
        log.error("video job %s failed: %s", job_id, e)
        _VIDEO_JOBS[job_id].update({"status": "failed", "error": str(e)[:300]})


async def _append_story(database, project_id: str, story: Dict[str, Any]) -> str:
    """Push a new story onto the project's stories array (cap at MAX)."""
    p = await database.website_projects.find_one({"id": project_id}, {"_id": 0, "stories": 1})
    existing = (p or {}).get("stories") or []
    if len(existing) >= MAX_STORIES_PER_PROJECT:
        # Drop the oldest one to make room
        existing.pop(0)
    sid = f"st-{uuid.uuid4().hex[:10]}"
    new = {
        "id": sid,
        "type": story.get("type", "image"),
        "media_url": story.get("media_url", ""),
        "poster_url": story.get("poster_url", ""),
        "caption": (story.get("caption") or "")[:200],
        "link": story.get("link", ""),
        "duration_sec": int(story.get("duration_sec") or 6),
        "visible": bool(story.get("visible", True)),
        "ai_generated": bool(story.get("ai_generated", False)),
        "created_at": _iso_now(),
    }
    existing.append(new)
    await database.website_projects.update_one(
        {"id": project_id},
        {"$set": {"stories": existing, "updated_at": _iso_now()}},
    )
    return sid


# ─────────────────────────────────────────────────────────
# Route registration
# ─────────────────────────────────────────────────────────

def register_routes(r: APIRouter, database, resolve_client_project) -> None:
    """Register stories + banner + media routes on the main websites router."""

    # ─── Public: stories visible on storefront ───
    @r.get("/public/{slug}/stories")
    async def _public_stories(slug: str):
        p = await database.website_projects.find_one(
            {"slug": slug, "status": "approved"},
            {"_id": 0, "stories": 1, "banner": 1, "name": 1},
        )
        if not p:
            raise HTTPException(404, "Not found")
        stories = [s for s in (p.get("stories") or []) if s.get("visible", True)]
        banner = p.get("banner") or {}
        if not banner.get("enabled"):
            banner = {"enabled": False}
        return {"stories": stories, "banner": banner, "store_name": p.get("name") or ""}

    # ─── Client: list stories (incl. hidden) ───
    @r.get("/client/stories")
    async def _client_list(authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        return {"stories": p.get("stories") or []}

    @r.post("/client/stories")
    async def _client_create(body: StoryIn, authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        _validate_data_url(body.media_url or "")
        if not body.media_url:
            raise HTTPException(400, "media_url required")
        sid = await _append_story(database, p["id"], body.dict())
        fresh = await database.website_projects.find_one({"id": p["id"]}, {"_id": 0, "stories": 1})
        return {"ok": True, "id": sid, "stories": (fresh or {}).get("stories") or []}

    @r.patch("/client/stories/{story_id}")
    async def _client_patch(story_id: str, body: StoryPatch, authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        stories = list(p.get("stories") or [])
        found = False
        for i, s in enumerate(stories):
            if s.get("id") == story_id:
                upd = {k: v for k, v in body.dict().items() if v is not None}
                if "media_url" in upd:
                    _validate_data_url(upd["media_url"])
                stories[i] = {**s, **upd}
                found = True
                break
        if not found:
            raise HTTPException(404, "story not found")
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$set": {"stories": stories, "updated_at": _iso_now()}},
        )
        return {"ok": True, "stories": stories}

    @r.delete("/client/stories/{story_id}")
    async def _client_delete(story_id: str, authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        stories = [s for s in (p.get("stories") or []) if s.get("id") != story_id]
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$set": {"stories": stories, "updated_at": _iso_now()}},
        )
        return {"ok": True}

    class ReorderIn(BaseModel):
        ids: List[str]

    @r.post("/client/stories/reorder")
    async def _client_reorder(body: ReorderIn, authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        idx = {sid: i for i, sid in enumerate(body.ids)}
        stories = sorted(p.get("stories") or [], key=lambda s: idx.get(s.get("id"), 999))
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$set": {"stories": stories, "updated_at": _iso_now()}},
        )
        return {"ok": True, "stories": stories}

    # ─── Client: banner ───
    @r.get("/client/banner")
    async def _banner_get(authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        return p.get("banner") or {"enabled": False, "animation": "kenburns", "overlay_opacity": 0.45}

    @r.put("/client/banner")
    async def _banner_put(body: BannerIn, authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        if body.media_url:
            _validate_data_url(body.media_url)
        upd = {k: v for k, v in body.dict().items() if v is not None}
        cur = dict(p.get("banner") or {})
        cur.update(upd)
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$set": {"banner": cur, "updated_at": _iso_now()}},
        )
        return cur

    # ─── Client: AI Media generation ───
    @r.post("/client/media/generate-image")
    async def _gen_image(body: GenImageIn, authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        prompt = (body.prompt or "").strip()
        if not prompt:
            raise HTTPException(400, "prompt required")
        if len(prompt) > 800:
            prompt = prompt[:800]
        media_url = await _generate_image_nano_banana(prompt)
        story_id = None
        if body.add_as_story:
            story_id = await _append_story(database, p["id"], {
                "type": "image", "media_url": media_url,
                "caption": prompt[:120], "duration_sec": 6,
                "visible": True, "ai_generated": True,
            })
        return {"ok": True, "media_url": media_url, "story_id": story_id}

    @r.post("/client/media/generate-video")
    async def _gen_video(body: GenVideoIn, authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        prompt = (body.prompt or "").strip()
        if not prompt:
            raise HTTPException(400, "prompt required")
        duration = int(body.duration or 4)
        if duration not in (4, 8, 12):
            duration = 4
        size = body.size or "1280x720"
        if size not in ("1280x720", "1792x1024", "1024x1792", "1024x1024"):
            size = "1280x720"
        job_id = f"vj-{uuid.uuid4().hex[:12]}"
        _VIDEO_JOBS[job_id] = {
            "id": job_id,
            "project_id": p["id"],
            "prompt": prompt[:200],
            "status": "queued",
            "queued_at": _iso_now(),
        }
        # Fire and forget
        asyncio.create_task(_run_video_job(job_id, p["id"], prompt, duration, size,
                                            bool(body.add_as_story), database))
        return {"ok": True, "job_id": job_id, "status": "queued",
                "estimated_seconds": 120 if duration == 4 else 240}

    @r.get("/client/media/jobs/{job_id}")
    async def _job_status(job_id: str, authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        job = _VIDEO_JOBS.get(job_id)
        if not job or job.get("project_id") != p["id"]:
            raise HTTPException(404, "Job not found")
        # Mask big media_url unless explicitly attached as story
        out = {k: v for k, v in job.items() if k != "media_url"}
        if job.get("status") == "done":
            fresh = await database.website_projects.find_one({"id": p["id"]}, {"_id": 0, "stories": 1})
            out["stories"] = (fresh or {}).get("stories") or []
        return out

    # ─── Stories Templates Library — one-click AI-generated stories ───
    from . import stories_templates as _stpl

    @r.get("/client/stories/templates")
    async def _list_templates(authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        items = _stpl.filter_for_vertical(p.get("vertical"))
        # Strip the heavy `prompt` text from listing — only needed at render time
        return {"templates": [
            {k: v for k, v in t.items() if k not in ("prompt", "caption_tpl")}
            for t in items
        ]}

    class TemplateApplyIn(BaseModel):
        template_id: str
        fields: Optional[Dict[str, Any]] = None

    @r.post("/client/stories/from-template")
    async def _apply_template(body: TemplateApplyIn, authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        tpl = _stpl.get_template(body.template_id)
        if not tpl:
            raise HTTPException(404, "قالب غير موجود")
        # Validate required fields
        fields = body.fields or {}
        missing = [f["label"] for f in tpl.get("fields", [])
                   if f.get("required") and not str(fields.get(f["name"]) or "").strip()]
        if missing:
            raise HTTPException(400, f"يجب تعبئة: {', '.join(missing)}")

        # Build context from project + brand colors
        theme = (p.get("theme") or {}) if isinstance(p.get("theme"), dict) else {}
        ctx = {
            "store_name": p.get("name") or "",
            "vertical": p.get("vertical") or "",
            "primary_color": theme.get("primary") or "warm gold",
            "secondary_color": theme.get("secondary") or "deep navy",
            "language": "Arabic",
            "fields": fields,
        }
        try:
            prompt, caption = _stpl.render_prompt(tpl, ctx)
        except ValueError as e:
            raise HTTPException(400, str(e))

        # IMAGE template — generate inline & attach as story
        if tpl.get("output") == "image":
            media_url = await _generate_image_nano_banana(prompt)
            sid = await _append_story(database, p["id"], {
                "type": "image", "media_url": media_url,
                "caption": caption, "duration_sec": 7,
                "visible": True, "ai_generated": True,
            })
            return {"ok": True, "type": "image", "story_id": sid, "caption": caption}

        # VIDEO template — kick off Sora job
        duration = int(tpl.get("duration_sec") or 4)
        size = tpl.get("size") or "1024x1792"
        job_id = f"vj-{uuid.uuid4().hex[:12]}"
        _VIDEO_JOBS[job_id] = {
            "id": job_id, "project_id": p["id"],
            "prompt": prompt[:200], "caption": caption,
            "status": "queued", "queued_at": _iso_now(),
        }

        async def _enrich_story_caption():
            """When the Sora job finishes, override the auto-caption with the template caption."""
            for _ in range(360):  # poll up to ~30 minutes
                await asyncio.sleep(5)
                j = _VIDEO_JOBS.get(job_id)
                if not j or j.get("status") in ("done", "failed"):
                    break
            j = _VIDEO_JOBS.get(job_id) or {}
            sid = j.get("story_id")
            if sid:
                await database.website_projects.update_one(
                    {"id": p["id"], "stories.id": sid},
                    {"$set": {"stories.$.caption": caption}},
                )

        asyncio.create_task(_run_video_job(job_id, p["id"], prompt, duration, size, True, database))
        asyncio.create_task(_enrich_story_caption())
        return {"ok": True, "type": "video", "job_id": job_id,
                "caption": caption, "estimated_seconds": 120 if duration == 4 else 240}
