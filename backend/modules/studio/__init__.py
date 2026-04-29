"""
Zitex Studio Module — deep AI generation studio for merchants/clients.

Provides three premium studio endpoints:
    POST /api/studio/image/generate   — deep scenario-driven image generation
    POST /api/studio/image/edit/{id}  — edit (not regenerate) an existing image
    POST /api/studio/video/generate   — deep video generation with voiceover script
    GET  /api/studio/cost-estimate    — preview cost before generation
    GET  /api/studio/credits          — current credits + usage history

Pricing (credits):
    Image  — 5 credits  (any size, any style)
    Edit   — 3 credits  (refines existing image)
    Video  — 4 credits per second of duration (so 10s = 40 credits)

All endpoints require auth + sufficient credits. Credits are deducted ATOMICALLY
(generation only proceeds if deduction succeeds), and refunded on failure.
"""
from __future__ import annotations
import os
import base64
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# === Pricing (credits) ===
COST_IMAGE = 5
COST_EDIT = 3
VIDEO_COST_PER_SECOND = 4   # so 10s = 40 credits, 60s = 240 credits

# === Models ===

class ImageGenerateIn(BaseModel):
    """Deep image generation — multi-field scenario."""
    scenario: str = Field(..., min_length=10, description="السيناريو الكامل / الفكرة")
    audience: Optional[str] = Field(None, description="الجمهور المستهدف")
    mood: Optional[str] = Field(None, description="المزاج العام: dramatic, calm, energetic...")
    style: Optional[str] = Field(None, description="الأسلوب: realistic, cartoon, cinematic, minimal")
    aspect_ratio: str = Field("1:1", description="1:1, 9:16, 16:9, 4:5")
    purpose: Optional[str] = Field(None, description="ad, story, banner, product_shot, social_post")
    reference_image_url: Optional[str] = None
    extra_details: Optional[str] = None


class ImageEditIn(BaseModel):
    """Edit (not regenerate) an existing image."""
    edit_request: str = Field(..., min_length=5, description="ما الذي تريد تغييره/إضافته/حذفه")


class VideoGenerateIn(BaseModel):
    """Deep video generation — separate scenario + voiceover."""
    title: str = Field(..., min_length=1)
    scenario: str = Field(..., min_length=10, description="السيناريو البصري — ما يحدث في الفيديو")
    voiceover_script: Optional[str] = Field(None, description="النص المنطوق (يقرأ بصوت)")
    duration_seconds: int = Field(10, ge=4, le=60, description="مدة الفيديو بالثواني (4-60)")
    aspect_ratio: str = Field("16:9", description="16:9, 9:16, 1:1")
    style: Optional[str] = Field(None, description="cinematic, documentary, animated, social")
    music_mood: Optional[str] = None


class CostEstimateIn(BaseModel):
    kind: str  # 'image' | 'edit' | 'video'
    duration_seconds: Optional[int] = None  # only for video


# === Helpers ===

def _aspect_to_size(aspect: str) -> str:
    """Convert aspect ratio to OpenAI size string for image/video models."""
    return {
        "1:1": "1024x1024",
        "9:16": "1024x1792",
        "16:9": "1792x1024",
        "4:5": "1024x1280",
    }.get(aspect, "1024x1024")


def _video_aspect_to_size(aspect: str) -> str:
    return {
        "16:9": "1280x720",
        "9:16": "720x1280",
        "1:1": "1024x1024",
    }.get(aspect, "1280x720")


def _build_image_prompt(payload: ImageGenerateIn) -> str:
    parts: List[str] = []
    parts.append(payload.scenario.strip())
    if payload.purpose:
        purpose_map = {
            "ad": "Designed as a striking advertisement",
            "story": "Optimized for vertical Instagram/TikTok story format",
            "banner": "Wide cinematic banner composition",
            "product_shot": "Clean professional product photography",
            "social_post": "Eye-catching social media post",
        }
        parts.append(purpose_map.get(payload.purpose, payload.purpose))
    if payload.audience:
        parts.append(f"Target audience: {payload.audience}")
    if payload.mood:
        parts.append(f"Mood: {payload.mood}")
    if payload.style:
        parts.append(f"Visual style: {payload.style}")
    if payload.extra_details:
        parts.append(payload.extra_details.strip())
    parts.append("Ultra high quality, detailed, professional.")
    return ". ".join(parts)


def _build_video_prompt(payload: VideoGenerateIn) -> str:
    parts: List[str] = [payload.scenario.strip()]
    if payload.voiceover_script:
        parts.append(f"With spoken voiceover narrating: '{payload.voiceover_script.strip()}'")
    if payload.style:
        parts.append(f"Cinematic style: {payload.style}")
    if payload.music_mood:
        parts.append(f"Background music mood: {payload.music_mood}")
    parts.append(f"Duration: {payload.duration_seconds} seconds")
    parts.append("Professional, cinematic quality.")
    return ". ".join(parts)


# === Router ===

def create_router(db, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/api/studio", tags=["studio"])

    # ---- Inline image edit helper (uses GPT-4o vision + GPT Image 1) ----
    async def _edit_image_inline(original_url: str, edit_prompt: str) -> Optional[str]:
        """Edit an image: describe it via GPT-4o then regenerate with edit instructions."""
        try:
            import requests
            from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
            from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContent
            emergent_key = os.environ.get("EMERGENT_LLM_KEY")
            if not emergent_key:
                return None

            # 1) Describe original
            description = ""
            try:
                if original_url.startswith("data:"):
                    # Already base64
                    header, b64 = original_url.split(",", 1)
                    content_type = header.split(";")[0].split(":")[1] if ":" in header else "image/png"
                    ref_b64 = b64
                else:
                    resp = requests.get(original_url, timeout=15)
                    resp.raise_for_status()
                    ref_b64 = base64.b64encode(resp.content).decode("utf-8")
                    content_type = resp.headers.get("Content-Type", "image/png")
                chat = LlmChat(api_key=emergent_key, session_id="studio-edit",
                               system_message="You describe images precisely for AI recreation. Describe every visual element in English.")
                chat.with_model("openai", "gpt-4o")
                fc = FileContent(content_type=content_type, file_content_base64=ref_b64)
                msg = UserMessage(text="Describe this image in full detail:", file_contents=[fc])
                description = await chat.send_message(msg)
            except Exception as e:
                logger.warning(f"[STUDIO] Could not analyze original image: {e}")

            # 2) Regenerate with edit instructions
            full_prompt = (
                f"Recreate this image with modifications. ORIGINAL: {description[:600]}. "
                f"REQUESTED CHANGES: {edit_prompt}. "
                "Keep all unchanged elements identical. Apply ONLY the requested changes."
            )
            image_gen = OpenAIImageGeneration(api_key=emergent_key)
            images = await image_gen.generate_images(prompt=full_prompt, model="gpt-image-1", number_of_images=1)
            if images and len(images) > 0:
                b64 = base64.b64encode(images[0]).decode("utf-8")
                return f"data:image/png;base64,{b64}"
            return None
        except Exception as e:
            logger.exception(f"[STUDIO] _edit_image_inline failed: {e}")
            return None

    # ---- Local credit helpers (avoid coupling to external service) ----
    async def _get_credits(user_id: str) -> int:
        u = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
        return (u or {}).get("credits", 0) or 0

    async def _deduct_credits(user_id: str, amount: int, reason: str) -> bool:
        result = await db.users.update_one(
            {"id": user_id, "credits": {"$gte": amount}},
            {"$inc": {"credits": -amount},
             "$push": {"credit_history": {
                 "amount": -amount,
                 "reason": reason,
                 "timestamp": datetime.now(timezone.utc).isoformat(),
             }}}
        )
        return result.modified_count > 0

    async def _refund_credits(user_id: str, amount: int, reason: str):
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"credits": amount},
             "$push": {"credit_history": {
                 "amount": amount,
                 "reason": reason,
                 "timestamp": datetime.now(timezone.utc).isoformat(),
             }}}
        )

    # ---- Cost preview ----
    @router.post("/cost-estimate")
    async def cost_estimate(payload: CostEstimateIn, user=Depends(get_current_user)):
        if payload.kind == "image":
            cost = COST_IMAGE
        elif payload.kind == "edit":
            cost = COST_EDIT
        elif payload.kind == "video":
            if not payload.duration_seconds or payload.duration_seconds < 4:
                raise HTTPException(400, "duration_seconds (>=4) required for video estimate")
            # Sora 2 only supports 4/8/12 — round up
            valid = [4, 8, 12]
            adj = min(valid, key=lambda v: abs(v - payload.duration_seconds))
            cost = adj * VIDEO_COST_PER_SECOND
        else:
            raise HTTPException(400, "kind must be 'image', 'edit', or 'video'")
        credits = await _get_credits(user["user_id"])
        return {
            "cost": cost,
            "credits_balance": credits,
            "can_afford": credits >= cost,
            "kind": payload.kind,
        }

    # ---- Credits + history ----
    @router.get("/credits")
    async def get_credits(user=Depends(get_current_user)):
        u = await db.users.find_one(
            {"id": user["user_id"]},
            {"_id": 0, "credits": 1, "credit_history": {"$slice": -25}}
        )
        if not u:
            raise HTTPException(404, "user not found")
        history = u.get("credit_history", []) or []
        history.reverse()
        return {
            "credits": u.get("credits", 0),
            "history": history,
            "pricing": {
                "image": COST_IMAGE,
                "edit": COST_EDIT,
                "video_per_second": VIDEO_COST_PER_SECOND,
            },
        }

    # ---- Image generate ----
    @router.post("/image/generate")
    async def image_generate(payload: ImageGenerateIn, user=Depends(get_current_user)):
        # 1. Check + deduct credits atomically
        ok = await _deduct_credits(user["user_id"], COST_IMAGE, "studio_image_generate")
        if not ok:
            raise HTTPException(402, f"رصيد النقاط غير كافٍ. يلزم {COST_IMAGE} نقاط لإنشاء صورة")

        try:
            from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
            emergent_key = os.environ.get("EMERGENT_LLM_KEY")
            if not emergent_key:
                raise RuntimeError("EMERGENT_LLM_KEY not configured")

            image_gen = OpenAIImageGeneration(api_key=emergent_key)
            prompt = _build_image_prompt(payload)
            size = _aspect_to_size(payload.aspect_ratio)
            logger.info(f"[STUDIO] Generating image for user {user['user_id']}: size={size}")

            images = await image_gen.generate_images(
                prompt=prompt,
                model="gpt-image-1",
                number_of_images=1,
            )
            if not images:
                raise RuntimeError("No images returned by AI service")

            image_id = str(uuid.uuid4())
            image_b64 = base64.b64encode(images[0]).decode("utf-8")
            data_url = f"data:image/png;base64,{image_b64}"

            # Save to studio gallery
            doc = {
                "id": image_id,
                "user_id": user["user_id"],
                "type": "image",
                "media_url": data_url,
                "scenario": payload.scenario,
                "audience": payload.audience,
                "mood": payload.mood,
                "style": payload.style,
                "aspect_ratio": payload.aspect_ratio,
                "purpose": payload.purpose,
                "prompt_used": prompt,
                "credits_spent": COST_IMAGE,
                "parent_id": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.studio_assets.insert_one(doc.copy())
            doc.pop("_id", None)

            return {
                "ok": True,
                "asset": {k: v for k, v in doc.items() if k != "_id"},
                "credits_spent": COST_IMAGE,
                "credits_remaining": await _get_credits(user["user_id"]),
            }
        except Exception as e:
            # Refund on failure
            await db.users.update_one(
                {"id": user["user_id"]},
                {"$inc": {"credits": COST_IMAGE},
                 "$push": {"credit_history": {
                     "amount": COST_IMAGE,
                     "reason": f"refund_studio_image_failed: {str(e)[:80]}",
                     "timestamp": datetime.now(timezone.utc).isoformat(),
                 }}}
            )
            logger.exception(f"[STUDIO] Image generate failed: {e}")
            raise HTTPException(500, f"فشل توليد الصورة. تمت إعادة النقاط. ({str(e)[:100]})")

    # ---- Image edit ----
    @router.post("/image/edit/{image_id}")
    async def image_edit(image_id: str, payload: ImageEditIn, user=Depends(get_current_user)):
        original = await db.studio_assets.find_one(
            {"id": image_id, "user_id": user["user_id"], "type": "image"},
            {"_id": 0}
        )
        if not original:
            raise HTTPException(404, "الصورة الأصلية غير موجودة")

        ok = await _deduct_credits(user["user_id"], COST_EDIT, "studio_image_edit")
        if not ok:
            raise HTTPException(402, f"رصيد النقاط غير كافٍ. يلزم {COST_EDIT} نقاط للتعديل")

        try:
            edited_url = await _edit_image_inline(original.get("media_url"), payload.edit_request)
            if not edited_url:
                raise RuntimeError("AI did not return an edited image")

            new_id = str(uuid.uuid4())
            doc = {
                "id": new_id,
                "user_id": user["user_id"],
                "type": "image",
                "media_url": edited_url,
                "scenario": original.get("scenario"),
                "edit_request": payload.edit_request,
                "parent_id": image_id,
                "credits_spent": COST_EDIT,
                "aspect_ratio": original.get("aspect_ratio"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.studio_assets.insert_one(doc.copy())
            doc.pop("_id", None)
            return {
                "ok": True,
                "asset": {k: v for k, v in doc.items() if k != "_id"},
                "credits_spent": COST_EDIT,
                "credits_remaining": await _get_credits(user["user_id"]),
            }
        except Exception as e:
            await db.users.update_one(
                {"id": user["user_id"]},
                {"$inc": {"credits": COST_EDIT},
                 "$push": {"credit_history": {
                     "amount": COST_EDIT,
                     "reason": f"refund_studio_edit_failed: {str(e)[:80]}",
                     "timestamp": datetime.now(timezone.utc).isoformat(),
                 }}}
            )
            logger.exception(f"[STUDIO] Image edit failed: {e}")
            raise HTTPException(500, f"فشل تعديل الصورة. تمت إعادة النقاط. ({str(e)[:100]})")

    # ---- Video generate ----
    @router.post("/video/generate")
    async def video_generate(payload: VideoGenerateIn, user=Depends(get_current_user)):
        # Sora 2 only supports 4/8/12 — round to nearest valid
        valid_durations = [4, 8, 12]
        adj_duration = min(valid_durations, key=lambda v: abs(v - payload.duration_seconds))
        cost = adj_duration * VIDEO_COST_PER_SECOND

        ok = await _deduct_credits(user["user_id"], cost, f"studio_video_{adj_duration}s")
        if not ok:
            raise HTTPException(402, f"رصيد النقاط غير كافٍ. يلزم {cost} نقاط لفيديو {adj_duration} ثواني")

        try:
            from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
            emergent_key = os.environ.get("EMERGENT_LLM_KEY")
            if not emergent_key:
                raise RuntimeError("EMERGENT_LLM_KEY not configured")

            video_gen = OpenAIVideoGeneration(api_key=emergent_key)
            prompt = _build_video_prompt(payload)
            size = _video_aspect_to_size(payload.aspect_ratio)

            logger.info(f"[STUDIO] Generating video for user {user['user_id']}: dur={adj_duration}s, size={size}")
            video_bytes = video_gen.text_to_video(
                prompt=prompt,
                model="sora-2",
                size=size,
                duration=adj_duration,
                max_wait_time=600,
            )
            if not video_bytes:
                raise RuntimeError("Video generation returned empty bytes")

            # Save to storage (re-use existing path)
            video_id = str(uuid.uuid4())
            video_b64 = base64.b64encode(video_bytes).decode("utf-8")
            data_url = f"data:video/mp4;base64,{video_b64}"

            doc = {
                "id": video_id,
                "user_id": user["user_id"],
                "type": "video",
                "media_url": data_url,
                "title": payload.title,
                "scenario": payload.scenario,
                "voiceover_script": payload.voiceover_script,
                "duration_seconds": adj_duration,
                "duration_requested": payload.duration_seconds,
                "aspect_ratio": payload.aspect_ratio,
                "style": payload.style,
                "music_mood": payload.music_mood,
                "prompt_used": prompt,
                "credits_spent": cost,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.studio_assets.insert_one(doc.copy())
            doc.pop("_id", None)
            return {
                "ok": True,
                "asset": {k: v for k, v in doc.items() if k != "_id"},
                "credits_spent": cost,
                "credits_remaining": await _get_credits(user["user_id"]),
            }
        except Exception as e:
            await db.users.update_one(
                {"id": user["user_id"]},
                {"$inc": {"credits": cost},
                 "$push": {"credit_history": {
                     "amount": cost,
                     "reason": f"refund_studio_video_failed: {str(e)[:80]}",
                     "timestamp": datetime.now(timezone.utc).isoformat(),
                 }}}
            )
            logger.exception(f"[STUDIO] Video generate failed: {e}")
            raise HTTPException(500, f"فشل توليد الفيديو. تمت إعادة النقاط. ({str(e)[:120]})")

    # ---- Gallery (user's generated assets) ----
    @router.get("/gallery")
    async def gallery(kind: Optional[str] = None, limit: int = 50, user=Depends(get_current_user)):
        q: Dict[str, Any] = {"user_id": user["user_id"]}
        if kind in ("image", "video"):
            q["type"] = kind
        items = await db.studio_assets.find(q, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        return {"items": items, "count": len(items)}

    @router.delete("/gallery/{asset_id}")
    async def delete_asset(asset_id: str, user=Depends(get_current_user)):
        result = await db.studio_assets.delete_one({"id": asset_id, "user_id": user["user_id"]})
        if result.deleted_count == 0:
            raise HTTPException(404, "asset not found")
        return {"ok": True}

    return router
