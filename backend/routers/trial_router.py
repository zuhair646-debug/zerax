"""
Zerax Trial / Demo System
==========================
Lets prospective merchants try the full platform instantly:
  1. Click "Try Free" → unique tenant created in seconds
  2. Get unique URL + credentials → 3-hour sandbox-isolated dashboard
  3. Pre-seeded with sample products + branches + theme + customer + driver
  4. After expiry, data is wiped (or upgraded to paid plan)
  5. Optional paid extension (e.g., 24h for 20 points)

All trial data lives under collection `trial_tenants` and shares the existing
collections but tagged with `tenant_id = trial_xxx` so it's invisible to
production users.

Owner: Zerax Platform (Feb 2026)
"""
from __future__ import annotations

import os
import logging
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

log = logging.getLogger("trial_router")

_mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _mongo[os.environ["DB_NAME"]]

router = APIRouter(prefix="/api/trial", tags=["trial"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(8)}"


def _hash_pwd(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────
# SAMPLE SEED DATA (so the trial dashboard isn't empty)
# ─────────────────────────────────────────────────────────────────────────
SAMPLE_PRODUCTS = [
    {"name": "iPhone 17 Pro Max", "price": 5499, "category": "إلكترونيات", "stock": 25,
     "img": "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600",
     "description": "iPhone 17 Pro Max — معالج A19 Bionic · شاشة 6.9'' ProMotion · 5G · مقاوم للماء IP68"},
    {"name": "ساعة Apple Watch Series 11", "price": 1899, "category": "إلكترونيات", "stock": 12,
     "img": "https://images.unsplash.com/photo-1546054454-aa26e2b734c7?w=600",
     "description": "Apple Watch Series 11 — قياس ECG · GPS مدمج · مقاومة للماء حتى 50م"},
    {"name": "AirPods Pro 3", "price": 999, "category": "إلكترونيات", "stock": 50,
     "img": "https://images.unsplash.com/photo-1605236453806-6ff36851218e?w=600",
     "description": "AirPods Pro الجيل الثالث · إلغاء ضوضاء نشط · بطارية 30 ساعة"},
    {"name": "حقيبة ظهر فاخرة", "price": 349, "category": "إكسسوارات", "stock": 30,
     "img": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600",
     "description": "حقيبة جلد طبيعي · مقاومة للماء · جيوب متعددة للابتوب 16''"},
    {"name": "ساعة Rolex Submariner", "price": 45000, "category": "ساعات فاخرة", "stock": 3,
     "img": "https://images.unsplash.com/photo-1587836374828-4dbafa94cf0e?w=600",
     "description": "Rolex Submariner — أيقونة ساعات الغوص · مقاومة 300م · حركة أوتوماتيكية"},
]

SAMPLE_BRANCH = {
    "name": "الفرع الرئيسي - الرياض",
    "address": "الرياض - حي العليا - شارع التحلية",
    "lat": 24.7136, "lng": 46.6753,
    "delivery_radius_km": 30,
    "shipping_fee": 15,
    "manager_name": "أحمد العتيبي",
    "is_active": True,
}


class TrialStartIn(BaseModel):
    business_name: str = Field(default="متجر تجريبي", max_length=100)
    industry: str = "electronics"
    duration_hours: int = Field(default=3, ge=1, le=72)
    paid: bool = False  # if True, deducts points; if False = free 3h trial
    referrer_email: Optional[str] = None


@router.post("/start")
async def start_trial(body: TrialStartIn, request: Request):
    """
    Anonymous endpoint — anyone can call. Creates a trial tenant in <1 sec.
    Returns unique URLs + credentials for admin/customer/driver portals.
    """
    # Rate-limit by IP (best-effort) — max 3 trials per IP per day
    ip = request.client.host if request.client else "unknown"
    today_start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = await db.trial_tenants.count_documents({"created_ip": ip, "created_at": {"$gte": today_start.isoformat()}})
    if today_count >= 5:
        raise HTTPException(status_code=429, detail="تم تجاوز الحد اليومي للتجارب من هذا الجهاز (5 يومياً). تواصل معنا للمزيد.")

    trial_id = _gen_id("trial")
    short = secrets.token_hex(3).upper()  # 6-char readable suffix
    admin_email = f"trial-{short.lower()}@zerax.demo"
    admin_pwd = secrets.token_urlsafe(8)
    customer_phone = "055" + str(secrets.randbelow(10000000)).zfill(7)
    expires_at = _now() + timedelta(hours=body.duration_hours)

    tenant = {
        "id": trial_id,
        "short_code": short,
        "business_name": body.business_name,
        "industry": body.industry,
        "duration_hours": body.duration_hours,
        "paid": body.paid,
        "admin_email": admin_email,
        "admin_password_hash": _hash_pwd(admin_pwd),
        "admin_password_plain": admin_pwd,  # only stored briefly for retrieval — wiped on expiry
        "customer_phone": customer_phone,
        "customer_otp": "1234",
        "driver_phone": customer_phone,
        "driver_otp": "1234",
        "created_at": _now_iso(),
        "expires_at": expires_at.isoformat(),
        "status": "active",
        "created_ip": ip,
        "referrer_email": body.referrer_email,
        "extended_count": 0,
    }
    await db.trial_tenants.insert_one(dict(tenant))

    # Also register the trial admin in `users` collection so JWT login works
    await db.users.update_one(
        {"email": admin_email},
        {"$set": {
            "id": trial_id,
            "email": admin_email,
            "password_hash": _hash_pwd(admin_pwd),
            "role": "merchant",
            "store_name": body.business_name,
            "tenant_id": trial_id,
            "is_trial": True,
            "trial_expires_at": expires_at.isoformat(),
            "created_at": _now_iso(),
        }},
        upsert=True,
    )

    # Seed sample products
    for i, p in enumerate(SAMPLE_PRODUCTS):
        doc = {
            **p,
            "id": _gen_id("prod"),
            "merchant_id": trial_id,
            "tenant_id": trial_id,
            "is_trial": True,
            "active": True,
            "created_at": _now_iso(),
            "rating": 4.5 + (i * 0.1),
            "sales": 10 + i * 5,
        }
        await db.store_products.insert_one(doc)

    # Seed a sample branch
    branch_doc = {**SAMPLE_BRANCH, "id": _gen_id("br"), "merchant_id": trial_id, "tenant_id": trial_id, "is_trial": True, "created_at": _now_iso()}
    await db.store_branches.insert_one(branch_doc)

    # Seed a sample customer
    cust_id = _gen_id("cust")
    await db.customers.update_one(
        {"phone": customer_phone},
        {"$set": {
            "id": cust_id,
            "phone": customer_phone,
            "name": "محمد تجريبي",
            "tenant_id": trial_id,
            "is_trial": True,
            "merchant_id": trial_id,
            "created_at": _now_iso(),
            "loyalty_points": 50,
        }},
        upsert=True,
    )

    # Pre-seed the merchant theme (Zerax default — they can customize)
    await db.merchant_themes.update_one(
        {"merchant_id": trial_id},
        {"$set": {
            "merchant_id": trial_id,
            "mode": "dark",
            "font_family": "Tajawal",
            "colors": {"bg": "#0a0a14", "surface": "#14142b", "accent": "#7c3aed", "amber": "#fbbf24", "text": "#f1f5f9", "border": "#2d2d4a"},
            "store_name": body.business_name,
            "is_trial": True,
            "created_at": _now_iso(),
        }},
        upsert=True,
    )

    # Build URLs
    base = str(request.base_url).rstrip("/")
    return {
        "trial_id": trial_id,
        "short_code": short,
        "expires_at": expires_at.isoformat(),
        "duration_hours": body.duration_hours,
        "urls": {
            "admin": f"{base}/mockups/admin.html?trial={trial_id}",
            "customer": f"{base}/mockups/app_mode_full.html?m={trial_id}",
            "driver": f"{base}/mockups/driver_app.html?t={trial_id}",
        },
        "credentials": {
            "admin": {"email": admin_email, "password": admin_pwd},
            "customer": {"phone": customer_phone, "otp": "1234"},
            "driver": {"phone": customer_phone, "otp": "1234"},
        },
        "seeded": {
            "products": len(SAMPLE_PRODUCTS),
            "branches": 1,
            "customers": 1,
        },
        "tutorial_url": f"{base}/mockups/trial_guide.html",
    }


@router.get("/{trial_id}")
async def get_trial_info(trial_id: str):
    """Public — returns info about a trial (time remaining, urls). Used by landing page."""
    t = await db.trial_tenants.find_one({"id": trial_id}, {"_id": 0, "admin_password_hash": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Trial not found")
    expires = datetime.fromisoformat(t["expires_at"])
    remaining = (expires - _now()).total_seconds()
    t["expired"] = remaining <= 0
    t["remaining_seconds"] = max(0, int(remaining))
    t["remaining_hours"] = round(max(0, remaining / 3600), 1)
    return t


class ExtendIn(BaseModel):
    trial_id: str
    additional_hours: int = Field(default=24, ge=1, le=168)
    payment_points: int = 20


@router.post("/extend")
async def extend_trial(body: ExtendIn):
    """Paid extension — adds hours to a trial."""
    t = await db.trial_tenants.find_one({"id": body.trial_id})
    if not t:
        raise HTTPException(status_code=404, detail="Trial not found")
    new_expires = datetime.fromisoformat(t["expires_at"]) + timedelta(hours=body.additional_hours)
    await db.trial_tenants.update_one(
        {"id": body.trial_id},
        {
            "$set": {"expires_at": new_expires.isoformat(), "paid": True},
            "$inc": {"extended_count": 1},
            "$push": {"extensions": {"hours": body.additional_hours, "points": body.payment_points, "at": _now_iso()}},
        },
    )
    await db.users.update_one({"tenant_id": body.trial_id}, {"$set": {"trial_expires_at": new_expires.isoformat()}})
    return {"ok": True, "new_expires_at": new_expires.isoformat(), "added_hours": body.additional_hours}


@router.post("/convert")
async def convert_trial_to_full(body: dict):
    """Trial user liked it → convert to permanent account (kept data, removed trial flags)."""
    trial_id = body.get("trial_id")
    permanent_email = body.get("email")
    if not trial_id or not permanent_email:
        raise HTTPException(status_code=400, detail="trial_id and email required")
    t = await db.trial_tenants.find_one({"id": trial_id})
    if not t:
        raise HTTPException(status_code=404, detail="Trial not found")
    # Mark all trial data as permanent
    await db.users.update_one(
        {"tenant_id": trial_id},
        {"$set": {"is_trial": False, "email": permanent_email, "converted_from_trial_at": _now_iso()}, "$unset": {"trial_expires_at": ""}},
    )
    await db.store_products.update_many({"tenant_id": trial_id}, {"$unset": {"is_trial": ""}})
    await db.store_branches.update_many({"tenant_id": trial_id}, {"$unset": {"is_trial": ""}})
    await db.customers.update_many({"tenant_id": trial_id}, {"$unset": {"is_trial": ""}})
    await db.merchant_themes.update_many({"merchant_id": trial_id}, {"$unset": {"is_trial": ""}})
    await db.trial_tenants.update_one({"id": trial_id}, {"$set": {"status": "converted", "converted_at": _now_iso(), "converted_email": permanent_email}})
    return {"ok": True, "message": "تم تحويل التجربة إلى حساب دائم 🎉"}


@router.post("/cleanup-expired")
async def cleanup_expired():
    """Admin-internal — wipes expired trial data. Should be called by a cron/task."""
    cursor = db.trial_tenants.find({"status": "active", "expires_at": {"$lt": _now_iso()}})
    wiped = 0
    async for t in cursor:
        tid = t["id"]
        await db.store_products.delete_many({"tenant_id": tid})
        await db.store_branches.delete_many({"tenant_id": tid})
        await db.customers.delete_many({"tenant_id": tid})
        await db.merchant_themes.delete_many({"merchant_id": tid})
        await db.users.delete_many({"tenant_id": tid})
        await db.trial_tenants.update_one({"id": tid}, {"$set": {"status": "expired", "wiped_at": _now_iso()}, "$unset": {"admin_password_plain": ""}})
        wiped += 1
    return {"ok": True, "wiped": wiped}


@router.get("/admin/list")
async def list_trials(status: Optional[str] = None, limit: int = 50):
    q = {"status": status} if status else {}
    items = await db.trial_tenants.find(q, {"_id": 0, "admin_password_hash": 0}).sort("created_at", -1).to_list(limit)
    return {"items": items, "count": len(items)}


@router.get("/health")
async def health():
    return {
        "ok": True,
        "active_trials": await db.trial_tenants.count_documents({"status": "active"}),
        "total_trials": await db.trial_tenants.count_documents({}),
        "converted": await db.trial_tenants.count_documents({"status": "converted"}),
        "expired": await db.trial_tenants.count_documents({"status": "expired"}),
    }
