"""Marketing API routes — all owner-only. Factory pattern.

Endpoints:
  GET    /api/marketing/overview         — stats + recent posts + channel status
  GET    /api/marketing/personas         — list 5 personas
  GET    /api/marketing/channels         — channel connection status
  POST   /api/marketing/generate         — AI generate 1 post
  POST   /api/marketing/generate-batch   — generate N posts (queued for review)
  GET    /api/marketing/posts            — list posts (filter by status)
  POST   /api/marketing/posts/{id}/approve  — approve & schedule
  POST   /api/marketing/posts/{id}/publish  — publish NOW to selected channels
  POST   /api/marketing/posts/{id}/reject   — reject
  DELETE /api/marketing/posts/{id}          — delete
  POST   /api/marketing/schedule         — turn on/off auto-pilot
  GET    /api/marketing/schedule/status  — get scheduler state
"""
import asyncio
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field

from .personas import PERSONAS, PERSONA_MAP
from .content_gen import generate_post, generate_batch
from .connectors import get_all_status, publish_to

logger = logging.getLogger("zenrex.marketing.routes")


# Models
class GenerateIn(BaseModel):
    persona_id: str = "devs"
    platform: str = "twitter"
    topic_hint: Optional[str] = None
    generate_image: bool = False


class BatchIn(BaseModel):
    count: int = Field(5, ge=1, le=20)
    platforms: Optional[List[str]] = None


class PublishIn(BaseModel):
    channels: List[str]
    to_number: Optional[str] = None


class ScheduleIn(BaseModel):
    enabled: bool
    interval_minutes: int = Field(60, ge=15, le=1440)
    channels: List[str] = Field(default_factory=lambda: ["telegram", "discord", "email"])
    auto_approve: bool = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_marketing_router(db, require_owner_dep):
    """Factory: builds APIRouter with proper Depends bound to require_owner."""
    router = APIRouter(prefix="/marketing", tags=["marketing"])
    scheduler_state: Dict[str, Any] = {
        "running": False,
        "interval_minutes": 60,
        "last_run": None,
        "next_run": None,
        "channels": ["telegram"],
        "auto_approve": False,
    }
    scheduler_task: Dict[str, Optional[asyncio.Task]] = {"task": None}

    # ── Inject saved credentials into os.environ at startup ──
    async def _restore_credentials():
        import os
        try:
            cur = db.marketing_credentials.find({}, {"_id": 0})
            async for doc in cur:
                key = doc.get("key")
                val = doc.get("value")
                if key and val:
                    os.environ[key] = val
            logger.info("[marketing] credentials restored from DB")
        except Exception:
            logger.exception("[marketing] credentials restore failed")

    async def _save_post(post: Dict[str, Any], status: str = "draft") -> Dict[str, Any]:
        doc = {
            "id": secrets.token_hex(10),
            "created_at": _now(),
            "status": status,
            **post,
        }
        await db.marketing_posts.insert_one(doc.copy())
        doc.pop("_id", None)
        return doc

    async def _list_posts(status_filter: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        q = {}
        if status_filter:
            q["status"] = status_filter
        cur = db.marketing_posts.find(q, {"_id": 0}).sort([("created_at", -1)]).limit(limit)
        return [p async for p in cur]

    async def _scheduler_loop():
        logger.info("[marketing.scheduler] started")
        try:
            iter_count = 0
            while scheduler_state.get("running"):
                try:
                    interval = int(scheduler_state.get("interval_minutes", 60))
                    channels = scheduler_state.get("channels", ["telegram"])
                    auto_approve = bool(scheduler_state.get("auto_approve", False))
                    persona = PERSONAS[iter_count % len(PERSONAS)]["id"]
                    platform = channels[iter_count % len(channels)] if channels else "telegram"
                    iter_count += 1

                    logger.info(f"[scheduler] generating persona={persona} platform={platform}")
                    post = await generate_post(persona_id=persona, platform=platform, generate_image=True)
                    doc = await _save_post(post, status="scheduled" if auto_approve else "draft")

                    if auto_approve:
                        for ch in channels:
                            try:
                                await publish_to(ch, doc)
                            except Exception as e:
                                logger.warning(f"[scheduler] publish {ch} failed: {e}")
                        await db.marketing_posts.update_one(
                            {"id": doc["id"]},
                            {"$set": {"status": "published", "published_at": _now()}},
                        )

                    scheduler_state["last_run"] = _now()
                    scheduler_state["next_run"] = (
                        datetime.now(timezone.utc) + timedelta(minutes=interval)
                    ).isoformat()
                except Exception:
                    logger.exception("[scheduler] iteration error")
                await asyncio.sleep(interval * 60)
        except asyncio.CancelledError:
            logger.info("[marketing.scheduler] cancelled")

    @router.get("/overview")
    async def overview(owner=Depends(require_owner_dep)):
        total = await db.marketing_posts.count_documents({})
        by_status = {}
        for s in ["draft", "scheduled", "published", "rejected", "failed"]:
            by_status[s] = await db.marketing_posts.count_documents({"status": s})
        recent = await _list_posts(limit=10)
        return {
            "total_posts": total,
            "by_status": by_status,
            "recent": recent,
            "channels": get_all_status(),
            "personas": PERSONAS,
            "scheduler": scheduler_state,
        }

    @router.get("/personas")
    async def list_personas(owner=Depends(require_owner_dep)):
        return {"personas": PERSONAS}

    @router.get("/channels")
    async def channels_status(owner=Depends(require_owner_dep)):
        return {"channels": get_all_status()}

    @router.get("/credentials/{channel}")
    async def get_channel_credentials(channel: str, owner=Depends(require_owner_dep)):
        """Return stored (masked) credentials for a channel."""
        from .connectors import CONNECTORS as _CONNS
        if channel not in _CONNS:
            raise HTTPException(404, "channel not found")
        fields = _CONNS[channel].get("fields", [])
        result = {}
        for f in fields:
            doc = await db.marketing_credentials.find_one({"key": f["key"]}, {"_id": 0, "value": 1})
            v = doc.get("value") if doc else None
            if not v:
                import os
                v = os.environ.get(f["key"], "")
            # mask secrets
            if v and f.get("secret"):
                if len(v) > 12:
                    masked = v[:4] + "•" * 8 + v[-4:]
                else:
                    masked = "•" * len(v)
                result[f["key"]] = {"value": masked, "has_value": True}
            else:
                result[f["key"]] = {"value": v or "", "has_value": bool(v)}
        return {"channel": channel, "fields": fields, "values": result}

    @router.post("/credentials/{channel}")
    async def save_channel_credentials(channel: str, payload: Dict[str, str] = Body(...), owner=Depends(require_owner_dep)):
        """Save credentials for a channel.
        Body: {"TELEGRAM_BOT_TOKEN": "...", "TELEGRAM_CHANNEL_ID": "@xxx"}
        Empty/masked values (containing •) are ignored to preserve existing.
        """
        import os
        from .connectors import CONNECTORS as _CONNS
        if channel not in _CONNS:
            raise HTTPException(404, "channel not found")
        valid_keys = {f["key"] for f in _CONNS[channel].get("fields", [])}
        saved = 0
        for k, v in payload.items():
            if k not in valid_keys:
                continue
            if not v or "•" in v:
                continue  # skip empty/masked
            v = v.strip()
            await db.marketing_credentials.update_one(
                {"key": k},
                {"$set": {"key": k, "value": v, "channel": channel, "updated_at": _now()}},
                upsert=True,
            )
            os.environ[k] = v  # live inject
            saved += 1
        return {"ok": True, "saved": saved, "channel": channel, "configured": _CONNS[channel]["is_configured"]()}

    @router.delete("/credentials/{channel}/{key}")
    async def delete_credential(channel: str, key: str, owner=Depends(require_owner_dep)):
        import os
        await db.marketing_credentials.delete_one({"key": key})
        os.environ.pop(key, None)
        return {"ok": True}

    @router.post("/test-publish/{channel}")
    async def test_publish(channel: str, payload: Dict[str, Any] = Body(default={}), owner=Depends(require_owner_dep)):
        """Send a test message to verify the channel is wired up correctly."""
        from .connectors import publish_to as _pub
        test_post = {
            "text": payload.get("text") or "🤖 رسالة اختبار من Zenrex Marketing Suite ✨\nلو وصلتك = القناة شغّالة 100%!",
            "image_url": None,
            "topic": "اختبار",
            "to_number": payload.get("to_number"),
        }
        try:
            r = await _pub(channel, test_post)
            return {"ok": True, **r}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}


    @router.post("/generate")
    async def generate_one(payload: GenerateIn, owner=Depends(require_owner_dep)):
        try:
            post = await generate_post(
                persona_id=payload.persona_id,
                platform=payload.platform,
                topic_hint=payload.topic_hint,
                generate_image=payload.generate_image,
            )
            doc = await _save_post(post, status="draft")
            return {"ok": True, "post": doc}
        except Exception as e:
            logger.exception("generate failed")
            raise HTTPException(500, f"توليد فشل: {str(e)[:200]}")

    @router.post("/generate-batch")
    async def generate_batch_endpoint(payload: BatchIn, owner=Depends(require_owner_dep)):
        try:
            posts = await generate_batch(count=payload.count, platforms=payload.platforms)
            saved = []
            for p in posts:
                if p.get("error"):
                    continue
                saved.append(await _save_post(p, status="draft"))
            return {"ok": True, "saved": len(saved), "posts": saved}
        except Exception as e:
            logger.exception("batch failed")
            raise HTTPException(500, f"توليد مجموعة فشل: {str(e)[:200]}")

    @router.get("/posts")
    async def list_posts(status: Optional[str] = None, limit: int = 50, owner=Depends(require_owner_dep)):
        posts = await _list_posts(status_filter=status, limit=min(limit, 200))
        return {"posts": posts}

    @router.post("/posts/{post_id}/approve")
    async def approve_post(post_id: str, owner=Depends(require_owner_dep)):
        res = await db.marketing_posts.update_one(
            {"id": post_id}, {"$set": {"status": "scheduled", "approved_at": _now()}}
        )
        if res.matched_count == 0:
            raise HTTPException(404, "post not found")
        return {"ok": True}

    @router.post("/posts/{post_id}/reject")
    async def reject_post(post_id: str, owner=Depends(require_owner_dep)):
        res = await db.marketing_posts.update_one(
            {"id": post_id}, {"$set": {"status": "rejected", "rejected_at": _now()}}
        )
        if res.matched_count == 0:
            raise HTTPException(404, "post not found")
        return {"ok": True}

    @router.delete("/posts/{post_id}")
    async def delete_post(post_id: str, owner=Depends(require_owner_dep)):
        res = await db.marketing_posts.delete_one({"id": post_id})
        if res.deleted_count == 0:
            raise HTTPException(404, "post not found")
        return {"ok": True}

    @router.post("/posts/{post_id}/publish")
    async def publish_post(post_id: str, payload: PublishIn, owner=Depends(require_owner_dep)):
        post = await db.marketing_posts.find_one({"id": post_id}, {"_id": 0})
        if not post:
            raise HTTPException(404, "post not found")
        results: List[Dict[str, Any]] = []
        if payload.to_number:
            post["to_number"] = payload.to_number
        for ch in payload.channels:
            try:
                r = await publish_to(ch, post)
                results.append({"channel": ch, "ok": True, **r})
            except Exception as e:
                results.append({"channel": ch, "ok": False, "error": str(e)[:200]})
        any_ok = any(r.get("ok") for r in results)
        await db.marketing_posts.update_one(
            {"id": post_id},
            {"$set": {
                "status": "published" if any_ok else "failed",
                "published_at": _now(),
                "publish_results": results,
            }},
        )
        return {"ok": any_ok, "results": results}

    @router.post("/schedule")
    async def schedule_set(payload: ScheduleIn, owner=Depends(require_owner_dep)):
        scheduler_state.update({
            "running": payload.enabled,
            "interval_minutes": payload.interval_minutes,
            "channels": payload.channels,
            "auto_approve": payload.auto_approve,
        })
        await db.marketing_settings.update_one(
            {"_id": "scheduler"},
            {"$set": {**scheduler_state, "updated_at": _now()}},
            upsert=True,
        )
        if payload.enabled:
            if scheduler_task["task"] is None or scheduler_task["task"].done():
                scheduler_task["task"] = asyncio.create_task(_scheduler_loop())
        else:
            t = scheduler_task["task"]
            if t and not t.done():
                t.cancel()
        return {"ok": True, "scheduler": scheduler_state}

    @router.get("/schedule/status")
    async def schedule_status(owner=Depends(require_owner_dep)):
        return scheduler_state

    # ── Restore scheduler state on startup ──
    async def _restore():
        try:
            await _restore_credentials()  # inject saved keys into os.environ
            st = await db.marketing_settings.find_one({"_id": "scheduler"}, {"_id": 0})
            if st and st.get("running"):
                scheduler_state.update(st)
                scheduler_task["task"] = asyncio.create_task(_scheduler_loop())
        except Exception:
            logger.exception("scheduler restore failed")

    try:
        asyncio.get_event_loop().create_task(_restore())
    except RuntimeError:
        # no running loop yet — defer
        pass

    return router


# Backwards-compat exports
def register_scheduler(*args, **kwargs):
    """Deprecated: use create_marketing_router(db, require_owner_dep) instead."""
    pass
