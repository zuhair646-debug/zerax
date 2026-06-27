"""
🧠 AI Lessons Admin API — REST endpoints for the operator to:
  • View all stored lessons (with effectiveness metrics)
  • Add a manual lesson (priority=critical, always-on)
  • Update / delete a lesson
  • View Auto-E1 review history

Mounted at /api/admin/lessons. Owner-only (uses the same is_owner check as
the rest of the admin routes).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from pydantic import BaseModel, Field

log = logging.getLogger("zenrex.lessons_admin")

router = APIRouter(prefix="/api/admin/lessons", tags=["ai-lessons-admin"])


class ManualLessonIn(BaseModel):
    guidance_ar: str = Field(..., min_length=8, max_length=3000)
    project_id: Optional[str] = None
    priority: str = "critical"          # critical | high | medium | low
    pattern: Optional[str] = "manual_operator_rule"


def register_lessons_admin(app, db, get_current_user, is_owner_check):
    """Wire the router into the FastAPI app. The host provides:
      • db                — Motor database handle
      • get_current_user  — dependency that resolves the JWT
      • is_owner_check    — function(user_dict) -> bool
    """

    async def _require_owner(user=Depends(get_current_user)):
        if not is_owner_check(user):
            raise HTTPException(403, "owner only")
        return user

    @router.get("")
    async def list_lessons(limit: int = 100, user=Depends(_require_owner)):
        from modules.freebuild.lesson_retrieval import get_lesson_stats
        items = await get_lesson_stats(db, limit=limit)
        # Sort: critical first, then by effectiveness desc, then by recency
        priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        items.sort(key=lambda L: (
            priority_rank.get(L.get("priority", "medium"), 2),
            -float(L.get("effectiveness", 0) or 0),
            -(L.get("injection_count") or 0),
        ))
        return {"ok": True, "items": items, "count": len(items)}

    @router.post("")
    async def create_manual_lesson(body: ManualLessonIn, user=Depends(_require_owner)):
        from modules.freebuild.lesson_retrieval import save_lesson
        if body.priority not in ("critical", "high", "medium", "low"):
            raise HTTPException(400, "priority must be critical/high/medium/low")
        lid = await save_lesson(
            db,
            project_id=body.project_id,
            guidance_ar=body.guidance_ar.strip(),
            pattern=(body.pattern or "manual_operator_rule"),
            priority=body.priority,
            source="manual_operator",
            details={"author_user_id": user.get("user_id")},
        )
        if not lid:
            raise HTTPException(500, "failed to save lesson")
        # Drop an owner notification so it shows in the audit trail
        try:
            from modules.freebuild.escalation_bridge import create_escalation
            await create_escalation(
                db=db,
                project_id=body.project_id,
                user_id=user.get("user_id"),
                reason="manual_lesson",
                severity="low",
                context={"lesson": body.guidance_ar[:240]},
            )
        except Exception:
            pass
        return {"ok": True, "id": lid}

    @router.delete("/{lesson_id}")
    async def delete_lesson(lesson_id: str, user=Depends(_require_owner)):
        r = await db.ai_learned_lessons.delete_one({"id": lesson_id})
        return {"ok": True, "deleted": r.deleted_count}

    @router.patch("/{lesson_id}")
    async def update_lesson(
        lesson_id: str,
        guidance_ar: Optional[str] = Form(None),
        priority: Optional[str] = Form(None),
        user=Depends(_require_owner),
    ):
        updates = {}
        if guidance_ar:
            updates["guidance_ar"] = guidance_ar.strip()[:3000]
        if priority and priority in ("critical", "high", "medium", "low"):
            updates["priority"] = priority
        if not updates:
            raise HTTPException(400, "nothing to update")
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        r = await db.ai_learned_lessons.update_one({"id": lesson_id}, {"$set": updates})
        return {"ok": True, "modified": r.modified_count}

    @router.get("/e1-reviews")
    async def list_e1_reviews(limit: int = 50, user=Depends(_require_owner)):
        cursor = db.ai_e1_reviews.find({}, {"_id": 0}).sort("ts", -1).limit(limit)
        items = []
        async for d in cursor:
            items.append(d)
        return {"ok": True, "items": items}

    # ─────────────────────────────────────────────────────────────────
    # 📚 Library Registry endpoints (read-only registry view + usage)
    # ─────────────────────────────────────────────────────────────────
    @router.get("/library-registry")
    async def get_library_registry(user=Depends(_require_owner)):
        """Return the current registry JSON (for the admin UI)."""
        from modules.freebuild.library_registry import LIBRARY_REGISTRY
        return {"ok": True, "registry": LIBRARY_REGISTRY}

    @router.get("/library-usage")
    async def get_library_usage(user=Depends(_require_owner)):
        """Track how often each library was injected (registry + tavily-discovered)."""
        cursor = db.library_usage_stats.find({}, {"_id": 0}).sort("injects", -1).limit(200)
        items = []
        async for d in cursor:
            items.append(d)
        # promotion queue (Tavily libs with 3+ successes awaiting owner approval)
        promo_cursor = db.library_promotion_queue.find({"status": "pending"}, {"_id": 0})
        promos = []
        async for d in promo_cursor:
            promos.append(d)
        return {"ok": True, "items": items, "promotion_queue": promos, "count": len(items)}

    app.include_router(router)
    log.info("AI Lessons admin module registered (/api/admin/lessons/*)")
