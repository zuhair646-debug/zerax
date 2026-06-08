"""
Zitex Ready-Made Sites Module — Wizard-driven deep-vertical AI site builder.

Flow:
    1) Pick site type (restaurant / store / clinic / ...)
    2) Pick visual pattern (4 distinct, hand-designed visual languages)
    3) Provide branding (logo upload OR text logo OR AI-designed) + business name + tagline
    4) Pick features (24 restaurant features by default — all enabled, user can opt-out)
    5) AI generates the FULL HTML/CSS/JS site, strictly following the chosen pattern,
       with all selected features wired in. Result is stored as a ready_sites_project.

Endpoints (all under /api/ready-sites):
    GET  /catalog                      — full catalog (types + patterns + features)
    POST /start                        — start a wizard session
    POST /select-type                  — choose site type
    POST /select-pattern               — choose visual pattern
    POST /branding                     — set logo + name + tagline
    POST /features                     — toggle features
    POST /generate                     — call Claude → full site HTML
    GET  /projects                     — list user projects
    GET  /project/{id}
    GET  /preview/{id}                 — public HTML render
    DELETE /project/{id}

Pricing:
    Generate: 40 credits per ready site (deep generation incl. cart/admin/reservations).
"""
from __future__ import annotations

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, Field

from .catalog import (
    SITE_TYPES,
    RESTAURANT_PATTERNS,
    RESTAURANT_FEATURES,
    get_pattern,
    get_type,
)
from .agent import generate_ready_site, refine_ready_site

logger = logging.getLogger(__name__)

GENERATE_COST = 40
REFINE_COST = 5  # cost per AI refinement chat message


# ---- Pydantic Models ----

class StartIn(BaseModel):
    pass


class SelectTypeIn(BaseModel):
    session_id: str
    type_id: str


class SelectPatternIn(BaseModel):
    session_id: str
    pattern_id: str


class BrandingIn(BaseModel):
    session_id: str
    business_name: str = Field(..., min_length=1, max_length=80)
    tagline: Optional[str] = Field(default="", max_length=200)
    logo_mode: str = Field(default="text")  # 'text' | 'upload' | 'ai'
    logo_url: Optional[str] = ""  # for 'upload' mode (data URL or http URL)
    logo_text: Optional[str] = ""  # for 'text' mode
    logo_ai_prompt: Optional[str] = ""  # for 'ai' mode (reserved)


class FeaturesIn(BaseModel):
    session_id: str
    enabled: List[str] = Field(default_factory=list)


class GenerateIn(BaseModel):
    session_id: str


class RefineIn(BaseModel):
    message: str = Field(..., min_length=2, max_length=2000)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _run_generation(db, session_id: str, user_id: str) -> None:
    """Background task — generates HTML, stores project, updates session.
    Runs detached from the request context so ingress timeouts don't matter."""
    try:
        sess = await db.ready_sites_sessions.find_one(
            {"id": session_id, "user_id": user_id}, {"_id": 0}
        )
        if not sess:
            return

        type_id = sess.get("type_id") or "restaurant"
        pattern_id = sess.get("pattern_id") or ""
        pattern = get_pattern(type_id, pattern_id)
        if not pattern:
            raise RuntimeError("النمط البصري المختار غير موجود")
        branding = sess.get("branding") or {}
        enabled = sess.get("features") or []
        features_full = [f for f in RESTAURANT_FEATURES if f["id"] in enabled]

        # Pre-generate project_id so Zitex tracking link is unique per site.
        project_id = str(uuid.uuid4())

        result = await generate_ready_site(
            type_id=type_id,
            pattern=pattern,
            branding=branding,
            features=features_full,
            project_id=project_id,
        )
        html = result["html"]
        admin_creds = result["admin_credentials"]
        seed_summary = result.get("seed_summary", {})

        slug = (branding.get("business_name", "site") or "site").strip().replace(" ", "-").lower()[:40] or "site"
        project = {
            "id": project_id,
            "user_id": user_id,
            "session_id": session_id,
            "type_id": type_id,
            "pattern_id": pattern_id,
            "branding": branding,
            "features": enabled,
            "html": html,
            "admin_credentials": admin_creds,
            "seed_summary": seed_summary,
            "refinement_history": [],
            "name": branding.get("business_name", "موقعي"),
            "slug": f"{slug}-{project_id[:6]}",
            "credits_spent": GENERATE_COST,
            "version": 1,
            "created_at": _now(),
            "updated_at": _now(),
        }
        await db.ready_sites_projects.insert_one(project)
        await db.ready_sites_sessions.update_one(
            {"id": session_id},
            {"$set": {"phase": "done", "project_id": project_id, "last_error": None}}
        )
    except Exception as e:
        logger.exception(f"[READY_SITES] background generate failed: {e}")
        # Refund credits + reset phase
        try:
            await db.users.update_one(
                {"id": user_id},
                {"$inc": {"credits": GENERATE_COST},
                 "$push": {"credit_history": {"amount": GENERATE_COST, "reason": f"refund_ready_sites_failed: {str(e)[:80]}", "timestamp": _now()}}}
            )
        except Exception:
            pass
        await db.ready_sites_sessions.update_one(
            {"id": session_id},
            {"$set": {"phase": "ready", "last_error": str(e)[:200]}}
        )


def create_ready_sites_router(db, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/api/ready-sites", tags=["ready-sites"])

    async def _credits(uid: str) -> int:
        u = await db.users.find_one({"id": uid}, {"_id": 0, "credits": 1})
        return int((u or {}).get("credits", 0) or 0)

    async def _deduct(uid: str, amount: int, reason: str) -> bool:
        r = await db.users.update_one(
            {"id": uid, "credits": {"$gte": amount}},
            {"$inc": {"credits": -amount},
             "$push": {"credit_history": {"amount": -amount, "reason": reason, "timestamp": _now()}}}
        )
        return r.modified_count > 0

    async def _refund(uid: str, amount: int, reason: str):
        await db.users.update_one(
            {"id": uid},
            {"$inc": {"credits": amount},
             "$push": {"credit_history": {"amount": amount, "reason": reason, "timestamp": _now()}}}
        )

    # ---- Catalog (public) ----
    @router.get("/catalog")
    async def catalog():
        return {
            "types": SITE_TYPES,
            "patterns": {"restaurant": RESTAURANT_PATTERNS},
            "features": {"restaurant": RESTAURANT_FEATURES},
            "generate_cost": GENERATE_COST,
        }

    # ---- Start wizard session ----
    @router.post("/start")
    async def start(_: StartIn, user=Depends(get_current_user)):
        sid = str(uuid.uuid4())
        await db.ready_sites_sessions.insert_one({
            "id": sid,
            "user_id": user["user_id"],
            "phase": "select_type",  # → select_pattern → branding → features → ready → generating → done
            "type_id": None,
            "pattern_id": None,
            "branding": {},
            "features": [],
            "created_at": _now(),
        })
        return {"session_id": sid, "phase": "select_type"}

    # ---- Step 1: select type ----
    @router.post("/select-type")
    async def select_type(payload: SelectTypeIn, user=Depends(get_current_user)):
        if not get_type(payload.type_id):
            raise HTTPException(400, "نوع موقع غير معروف")
        sess = await db.ready_sites_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not sess:
            raise HTTPException(404, "الجلسة غير موجودة")

        await db.ready_sites_sessions.update_one(
            {"id": payload.session_id},
            {"$set": {"type_id": payload.type_id, "phase": "select_pattern"}}
        )
        patterns = RESTAURANT_PATTERNS if payload.type_id == "restaurant" else []
        return {"phase": "select_pattern", "patterns": patterns}

    # ---- Step 2: select pattern ----
    @router.post("/select-pattern")
    async def select_pattern(payload: SelectPatternIn, user=Depends(get_current_user)):
        sess = await db.ready_sites_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not sess:
            raise HTTPException(404, "الجلسة غير موجودة")
        pat = get_pattern(sess.get("type_id") or "", payload.pattern_id)
        if not pat:
            raise HTTPException(400, "نمط بصري غير معروف")

        await db.ready_sites_sessions.update_one(
            {"id": payload.session_id},
            {"$set": {"pattern_id": payload.pattern_id, "phase": "branding"}}
        )
        return {"phase": "branding", "pattern": pat}

    # ---- Step 3: branding ----
    @router.post("/branding")
    async def branding(payload: BrandingIn, user=Depends(get_current_user)):
        sess = await db.ready_sites_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not sess:
            raise HTTPException(404, "الجلسة غير موجودة")
        if payload.logo_mode not in ("text", "upload", "ai"):
            raise HTTPException(400, "logo_mode غير صالح")

        branding = {
            "business_name": payload.business_name.strip(),
            "tagline": (payload.tagline or "").strip(),
            "logo_mode": payload.logo_mode,
            "logo_url": (payload.logo_url or "").strip(),
            "logo_text": (payload.logo_text or "").strip(),
            "logo_ai_prompt": (payload.logo_ai_prompt or "").strip(),
        }

        # default features list for restaurant if user didn't customize yet
        default_features = [f["id"] for f in RESTAURANT_FEATURES if f.get("default", True)]

        await db.ready_sites_sessions.update_one(
            {"id": payload.session_id},
            {"$set": {"branding": branding, "features": default_features, "phase": "features"}}
        )
        return {"phase": "features", "features": RESTAURANT_FEATURES, "default_enabled": default_features}

    # ---- Step 4: features ----
    @router.post("/features")
    async def features(payload: FeaturesIn, user=Depends(get_current_user)):
        sess = await db.ready_sites_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not sess:
            raise HTTPException(404, "الجلسة غير موجودة")

        valid_ids = {f["id"] for f in RESTAURANT_FEATURES}
        clean = [fid for fid in payload.enabled if fid in valid_ids]
        if not clean:
            raise HTTPException(400, "اختر ميزة واحدة على الأقل")

        credits = await _credits(user["user_id"])
        await db.ready_sites_sessions.update_one(
            {"id": payload.session_id},
            {"$set": {"features": clean, "phase": "ready"}}
        )
        return {
            "phase": "ready",
            "features_count": len(clean),
            "estimated_cost": GENERATE_COST,
            "credits_balance": credits,
            "can_afford": credits >= GENERATE_COST,
        }

    # ---- Step 5: generate (kicks off background task) ----
    @router.post("/generate")
    async def generate(payload: GenerateIn, user=Depends(get_current_user)):
        sess = await db.ready_sites_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not sess:
            raise HTTPException(404, "الجلسة غير موجودة")
        if sess.get("phase") == "generating":
            return {"ok": True, "phase": "generating", "started": False}
        if sess.get("phase") != "ready":
            raise HTTPException(400, "أكمل خطوات المعالج قبل التوليد")

        ok = await _deduct(user["user_id"], GENERATE_COST, "ready_sites_generate")
        if not ok:
            raise HTTPException(402, f"رصيدك ما يكفي ({GENERATE_COST} نقطة مطلوبة)")

        await db.ready_sites_sessions.update_one(
            {"id": payload.session_id},
            {"$set": {"phase": "generating", "generation_started_at": _now(), "last_error": None}}
        )

        # Background task — do NOT await
        import asyncio
        asyncio.create_task(_run_generation(db, payload.session_id, user["user_id"]))
        return {"ok": True, "phase": "generating", "started": True}

    # ---- Poll generation status ----
    @router.get("/status/{session_id}")
    async def status(session_id: str, user=Depends(get_current_user)):
        sess = await db.ready_sites_sessions.find_one(
            {"id": session_id, "user_id": user["user_id"]},
            {"_id": 0, "phase": 1, "project_id": 1, "last_error": 1, "generation_started_at": 1}
        )
        if not sess:
            raise HTTPException(404, "الجلسة غير موجودة")
        phase = sess.get("phase")
        out = {"phase": phase}
        if phase == "done" and sess.get("project_id"):
            out["project_id"] = sess["project_id"]
            out["preview_url"] = f"/api/ready-sites/preview/{sess['project_id']}"
        if sess.get("last_error"):
            out["error"] = sess["last_error"]
        return out

    # ---- List user projects ----
    @router.get("/projects")
    async def list_projects(user=Depends(get_current_user)):
        cursor = db.ready_sites_projects.find(
            {"user_id": user["user_id"]},
            {"_id": 0, "html": 0}
        ).sort("created_at", -1)
        items = await cursor.to_list(length=100)
        return {"projects": items, "count": len(items)}

    @router.get("/project/{project_id}")
    async def get_project(project_id: str, user=Depends(get_current_user)):
        p = await db.ready_sites_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "المشروع غير موجود")
        return p

    @router.get("/preview/{project_id}")
    async def preview(project_id: str):
        p = await db.ready_sites_projects.find_one(
            {"id": project_id}, {"_id": 0, "html": 1}
        )
        if not p or not p.get("html"):
            raise HTTPException(404, "preview not found")
        return Response(content=p["html"], media_type="text/html")

    @router.delete("/project/{project_id}")
    async def delete_project(project_id: str, user=Depends(get_current_user)):
        r = await db.ready_sites_projects.delete_one(
            {"id": project_id, "user_id": user["user_id"]}
        )
        if r.deleted_count == 0:
            raise HTTPException(404, "المشروع غير موجود")
        return {"ok": True}

    # ---- Zitex Branding Tracker (public) ----
    @router.get("/track-visit/{project_id}")
    async def track_visit(project_id: str):
        """Fired from the Zitex footer pixel. Records that an end-customer saw the site."""
        try:
            await db.ready_sites_projects.update_one(
                {"id": project_id},
                {
                    "$inc": {"visits_count": 1},
                    "$set": {"last_visit_at": _now()},
                },
            )
        except Exception:
            pass
        # 1x1 transparent GIF
        gif = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        return Response(content=gif, media_type="image/gif",
                        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})

    # ---- Zitex Admin: view ALL ready-site projects across all tenants ----
    @router.get("/admin/owned-sites")
    async def admin_owned_sites(user=Depends(get_current_user)):
        """Returns every Ready Site we've ever built. Used by Zitex's own admin dashboard
        to track customer sites that carry our branded footer link."""
        if not user.get("is_admin"):
            raise HTTPException(403, "صلاحيات المسؤول مطلوبة")
        cursor = db.ready_sites_projects.find(
            {},
            {"_id": 0, "html": 0, "admin_credentials": 0, "refinement_history": 0}
        ).sort("created_at", -1)
        items = await cursor.to_list(length=500)
        # Enrich with the live preview link
        for it in items:
            it["preview_url"] = f"/api/ready-sites/preview/{it['id']}"
            it["track_url"] = f"https://zitex.com/?ref={it['id']}"
        # Aggregate totals
        total_sites = len(items)
        total_visits = sum(int(it.get("visits_count", 0) or 0) for it in items)
        return {
            "sites": items,
            "total_sites": total_sites,
            "total_visits": total_visits,
        }

    # ---- AI Refinement Chat ----
    @router.post("/refine/{project_id}")
    async def refine(project_id: str, payload: RefineIn, user=Depends(get_current_user)):
        """Apply a natural-language change to the site's HTML via AI."""
        p = await db.ready_sites_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "المشروع غير موجود")

        ok = await _deduct(user["user_id"], REFINE_COST, "ready_sites_refine")
        if not ok:
            raise HTTPException(402, f"رصيدك ما يكفي ({REFINE_COST} نقاط لكل تعديل)")

        try:
            new_html = await refine_ready_site(p["html"], payload.message.strip())
            new_version = int(p.get("version", 1)) + 1
            history_entry = {
                "version": new_version,
                "message": payload.message.strip()[:500],
                "timestamp": _now(),
            }
            await db.ready_sites_projects.update_one(
                {"id": project_id},
                {
                    "$set": {"html": new_html, "version": new_version, "updated_at": _now()},
                    "$push": {"refinement_history": history_entry},
                }
            )
            return {
                "ok": True,
                "version": new_version,
                "preview_url": f"/api/ready-sites/preview/{project_id}",
                "credits_remaining": await _credits(user["user_id"]),
                "message": payload.message.strip()[:200],
            }
        except Exception as e:
            await _refund(user["user_id"], REFINE_COST, f"refund_refine_failed: {str(e)[:80]}")
            logger.exception(f"[READY_SITES] refine failed: {e}")
            raise HTTPException(500, f"فشل التعديل. تمت إعادة النقاط. ({str(e)[:120]})")

    @router.get("/refine/{project_id}/history")
    async def refine_history(project_id: str, user=Depends(get_current_user)):
        p = await db.ready_sites_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"_id": 0, "refinement_history": 1, "version": 1}
        )
        if not p:
            raise HTTPException(404, "المشروع غير موجود")
        return {
            "history": p.get("refinement_history", []),
            "current_version": p.get("version", 1),
        }

    return router
