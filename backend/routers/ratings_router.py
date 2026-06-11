"""
Driver Ratings & Reviews
─────────────────────────────────────────
Customers rate drivers + leave comments after delivery.
Visible to:
  - The driver (in their Profile section)
  - The merchant (transparency in admin panel)
  - Other customers (when assigning a delivery)
"""
from __future__ import annotations
import os, uuid, jwt
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient

router = APIRouter(prefix="/api/delivery/ratings", tags=["driver-ratings"])
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key")
_MONGO_URL = os.environ.get("MONGO_URL")
_DB_NAME = os.environ.get("DB_NAME")
_c: Optional[AsyncIOMotorClient] = None

def _db():
    global _c
    if _c is None: _c = AsyncIOMotorClient(_MONGO_URL)
    return _c[_DB_NAME]

def _now(): return datetime.now(timezone.utc).isoformat()

def _merchant(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer required")
    try:
        p = jwt.decode(authorization.split(" ",1)[1], JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid token")
    return {"id": p.get("user_id") or p.get("sub")}


class RatingIn(BaseModel):
    driver_id: str                       # driver phone or token
    driver_name: Optional[str] = ""
    order_id: Optional[str] = ""
    customer_name: str
    customer_phone: Optional[str] = ""
    stars: int = Field(ge=1, le=5)
    comment: Optional[str] = ""
    tags: List[str] = []                 # ["سريع","مهذب","نظيف"]


@router.post("")
async def submit_rating(body: RatingIn):
    """Customer submits a rating + comment for a driver."""
    db = _db()
    cfg = await db.driver_configs.find_one()
    merchant_id = cfg.get("merchant_id") if cfg else None
    rid = "rt_" + uuid.uuid4().hex[:10]
    doc = {
        "id": rid,
        "merchant_id": merchant_id,
        "driver_id": body.driver_id,
        "driver_name": body.driver_name,
        "order_id": body.order_id,
        "customer_name": body.customer_name,
        "customer_phone": (body.customer_phone or "")[:6] + ("****" if body.customer_phone else ""),
        "stars": body.stars,
        "comment": body.comment,
        "tags": body.tags,
        "created_at": _now(),
    }
    await db.driver_ratings.insert_one(doc)
    doc.pop("_id", None)
    # Update driver summary
    summary = await _summary(body.driver_id)
    return {"ok": True, "rating": doc, "summary": summary}


async def _summary(driver_id: str) -> Dict[str, Any]:
    db = _db()
    items = await db.driver_ratings.find({"driver_id": driver_id}).to_list(500)
    if not items:
        return {"avg": 0, "count": 0, "breakdown": {"5":0,"4":0,"3":0,"2":0,"1":0}}
    total = sum(i["stars"] for i in items)
    bd = {"5":0,"4":0,"3":0,"2":0,"1":0}
    for i in items:
        bd[str(i["stars"])] += 1
    return {
        "avg": round(total / len(items), 2),
        "count": len(items),
        "breakdown": bd,
    }


@router.get("/driver/{driver_id}")
async def driver_ratings(driver_id: str, limit: int = 50):
    """Public: list ratings + summary for one driver."""
    db = _db()
    items = await db.driver_ratings.find({"driver_id": driver_id}).sort("created_at", -1).limit(limit).to_list(limit)
    for d in items: d.pop("_id", None)
    summary = await _summary(driver_id)
    return {"summary": summary, "ratings": items}


@router.get("/merchant")
async def merchant_all_ratings(user=Depends(_merchant)):
    """Merchant sees ALL driver ratings for transparency."""
    db = _db()
    items = await db.driver_ratings.find({"merchant_id": user["id"]}).sort("created_at", -1).limit(500).to_list(500)
    for d in items: d.pop("_id", None)
    # Aggregate per driver
    by_driver: Dict[str, Any] = {}
    for it in items:
        did = it["driver_id"]
        if did not in by_driver:
            by_driver[did] = {"driver_id": did, "driver_name": it.get("driver_name") or "سائق", "ratings":[], "total_stars":0, "count":0}
        by_driver[did]["ratings"].append(it)
        by_driver[did]["total_stars"] += it["stars"]
        by_driver[did]["count"] += 1
    drivers = []
    for did, info in by_driver.items():
        info["avg"] = round(info["total_stars"] / info["count"], 2) if info["count"] else 0
        info["ratings"] = info["ratings"][:5]   # last 5 per driver
        del info["total_stars"]
        drivers.append(info)
    drivers.sort(key=lambda x: x["count"], reverse=True)
    return {"drivers": drivers, "total_ratings": len(items)}


@router.get("/summary/{driver_id}")
async def public_summary(driver_id: str):
    return await _summary(driver_id)
