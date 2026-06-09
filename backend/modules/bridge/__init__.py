"""
Channel Bridge — connects Zerax platform-generated assets (studio images/videos)
to the owner's client websites. Auto-publishes to stories/banners or media library.

Endpoints:
    GET  /api/bridge/projects              — list owner's website projects
    POST /api/bridge/push-to-story         — push a studio asset as a Story on a site
    POST /api/bridge/push-to-banner        — push a studio asset as Banner slide
    GET  /api/bridge/history?project_id=   — list assets pushed to a site

Each push deducts 2 points (small ops fee). Only Zerax-generated assets
(from studio_assets, video_wizard_results, image_wizard_results) are bridgeable.
"""
from __future__ import annotations
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

BRIDGE_PUSH_COST = 2  # points per push


class PushIn(BaseModel):
    project_id: str
    asset_id: str
    asset_source: str  # 'studio' | 'video_wizard' | 'image_wizard'
    caption: Optional[str] = ""
    link: Optional[str] = ""


class BannerPushIn(BaseModel):
    project_id: str
    asset_id: str
    asset_source: str
    title: Optional[str] = ""
    subtitle: Optional[str] = ""
    cta_label: Optional[str] = ""
    cta_link: Optional[str] = ""


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _find_asset(db, asset_id: str, asset_source: str, user_id: str) -> Optional[dict]:
    col = {
        "studio":        "studio_assets",
        "video_wizard":  "video_wizard_results",
        "image_wizard":  "image_wizard_results",
    }.get(asset_source)
    if not col:
        return None
    return await db[col].find_one({"id": asset_id, "user_id": user_id}, {"_id": 0})


def create_bridge_router(db, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/api/bridge", tags=["channel-bridge"])

    @router.get("/projects")
    async def list_projects(user=Depends(get_current_user)):
        # Support both owner_id (new) and user_id (legacy) fields
        rows = await db.website_projects.find(
            {"$or": [{"owner_id": user["user_id"]}, {"user_id": user["user_id"]}]},
            {"_id": 0, "id": 1, "name": 1, "slug": 1, "category": 1, "vertical": 1}
        ).sort("created_at", -1).to_list(length=100)
        return {"projects": rows, "count": len(rows)}

    @router.post("/push-to-story")
    async def push_to_story(payload: PushIn, user=Depends(get_current_user)):
        # Support both owner_id (new) and user_id (legacy) fields
        project = await db.website_projects.find_one(
            {"id": payload.project_id, "$or": [{"owner_id": user["user_id"]}, {"user_id": user["user_id"]}]},
            {"_id": 0, "id": 1, "slug": 1, "name": 1}
        )
        if not project:
            raise HTTPException(404, "المشروع مش موجود")

        asset = await _find_asset(db, payload.asset_id, payload.asset_source, user["user_id"])
        if not asset:
            raise HTTPException(404, "الأصل غير موجود أو ليس ملكك")

        # Deduct fee
        result = await db.users.update_one(
            {"id": user["user_id"], "credits": {"$gte": BRIDGE_PUSH_COST}},
            {"$inc": {"credits": -BRIDGE_PUSH_COST},
             "$push": {"credit_history": {
                 "amount": -BRIDGE_PUSH_COST,
                 "reason": f"bridge_story_{payload.project_id[:8]}",
                 "timestamp": _now().isoformat(),
             }}}
        )
        if result.modified_count == 0:
            raise HTTPException(402, f"محتاج {BRIDGE_PUSH_COST} نقطة للنشر")

        media_url = asset.get("media_url", "")
        media_type = "video" if payload.asset_source == "video_wizard" or media_url.startswith("data:video") else "image"

        # Determine story position (append)
        existing_count = await db.site_stories.count_documents({"project_id": payload.project_id})

        story_doc = {
            "id": str(uuid.uuid4()),
            "project_id": payload.project_id,
            "slug": project.get("slug"),
            "media_url": media_url,
            "media_type": media_type,
            "caption": payload.caption or "",
            "link": payload.link or "",
            "visible": True,
            "position": existing_count,
            "source": f"zitex_bridge_{payload.asset_source}",
            "source_asset_id": payload.asset_id,
            "created_at": _now().isoformat(),
        }
        await db.site_stories.insert_one(story_doc.copy())

        # Log bridge history
        await db.bridge_history.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "project_id": payload.project_id,
            "target": "story",
            "asset_id": payload.asset_id,
            "asset_source": payload.asset_source,
            "target_ref": story_doc["id"],
            "cost": BRIDGE_PUSH_COST,
            "created_at": _now().isoformat(),
        })

        story_doc.pop("_id", None)
        return {
            "ok": True,
            "story": story_doc,
            "credits_deducted": BRIDGE_PUSH_COST,
            "message": f"✓ تم نشر الأصل كـStory في متجر '{project.get('name', 'متجرك')}'",
        }

    @router.post("/push-to-banner")
    async def push_to_banner(payload: BannerPushIn, user=Depends(get_current_user)):
        # Support both owner_id (new) and user_id (legacy) fields
        project = await db.website_projects.find_one(
            {"id": payload.project_id, "$or": [{"owner_id": user["user_id"]}, {"user_id": user["user_id"]}]},
            {"_id": 0, "id": 1, "slug": 1, "name": 1}
        )
        if not project:
            raise HTTPException(404, "المشروع مش موجود")

        asset = await _find_asset(db, payload.asset_id, payload.asset_source, user["user_id"])
        if not asset:
            raise HTTPException(404, "الأصل غير موجود")

        result = await db.users.update_one(
            {"id": user["user_id"], "credits": {"$gte": BRIDGE_PUSH_COST}},
            {"$inc": {"credits": -BRIDGE_PUSH_COST},
             "$push": {"credit_history": {
                 "amount": -BRIDGE_PUSH_COST,
                 "reason": f"bridge_banner_{payload.project_id[:8]}",
                 "timestamp": _now().isoformat(),
             }}}
        )
        if result.modified_count == 0:
            raise HTTPException(402, f"محتاج {BRIDGE_PUSH_COST} نقطة للنشر")

        media_url = asset.get("media_url", "")
        media_type = "video" if payload.asset_source == "video_wizard" or media_url.startswith("data:video") else "image"

        existing_count = await db.site_banner_slides.count_documents({"project_id": payload.project_id})
        slide_doc = {
            "id": str(uuid.uuid4()),
            "project_id": payload.project_id,
            "slug": project.get("slug"),
            "media_url": media_url,
            "media_type": media_type,
            "title": payload.title or "",
            "subtitle": payload.subtitle or "",
            "cta_label": payload.cta_label or "",
            "cta_link": payload.cta_link or "",
            "visible": True,
            "position": existing_count,
            "source": f"zitex_bridge_{payload.asset_source}",
            "source_asset_id": payload.asset_id,
            "created_at": _now().isoformat(),
        }
        await db.site_banner_slides.insert_one(slide_doc.copy())

        await db.bridge_history.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "project_id": payload.project_id,
            "target": "banner",
            "asset_id": payload.asset_id,
            "asset_source": payload.asset_source,
            "target_ref": slide_doc["id"],
            "cost": BRIDGE_PUSH_COST,
            "created_at": _now().isoformat(),
        })

        slide_doc.pop("_id", None)
        return {
            "ok": True,
            "slide": slide_doc,
            "credits_deducted": BRIDGE_PUSH_COST,
            "message": f"✓ تم نشر الأصل كبنر في متجر '{project.get('name', 'متجرك')}'",
        }

    @router.get("/history")
    async def bridge_history(project_id: str, user=Depends(get_current_user)):
        # Support both owner_id (new) and user_id (legacy) fields
        project = await db.website_projects.find_one(
            {"id": project_id, "$or": [{"owner_id": user["user_id"]}, {"user_id": user["user_id"]}]},
            {"_id": 0, "id": 1}
        )
        if not project:
            raise HTTPException(404, "المشروع مش موجود")
        rows = await db.bridge_history.find(
            {"user_id": user["user_id"], "project_id": project_id},
            {"_id": 0}
        ).sort("created_at", -1).limit(50).to_list(length=50)
        return {"history": rows, "count": len(rows), "push_cost": BRIDGE_PUSH_COST}

    return router
