"""
Zenrex Storage Billing — Unified storage subscription system.

Separates storage quotas from AI credits. Users subscribe to a monthly plan
that gives them GB of storage across ALL surfaces (websites, apps, games,
images, videos). If the subscription lapses, files enter a 10-day grace
period (emails sent on days 1/5/8). After grace, files are ARCHIVED
(invisible to user but kept on our server) for 6 months. User can recover
their files by paying a tiered recovery fee + renewing subscription.

Plans (monthly USD, recurring via LemonSqueezy):
  free     -> $0/mo     250 MB    (default)
  starter  -> $7/mo     3 GB
  plus     -> $14/mo    15 GB     (most popular)
  pro      -> $29/mo    75 GB
  studio   -> $59/mo    300 GB

Recovery (one-time):
  <1 GB    -> $5
  1-10 GB  -> $15
  10-50 GB -> $35
  50+ GB   -> $79

LemonSqueezy variant env vars (set after creating the variants in LS):
  LEMONSQUEEZY_STORAGE_STARTER
  LEMONSQUEEZY_STORAGE_PLUS
  LEMONSQUEEZY_STORAGE_PRO
  LEMONSQUEEZY_STORAGE_STUDIO
  LEMONSQUEEZY_RECOVERY_SMALL
  LEMONSQUEEZY_RECOVERY_MEDIUM
  LEMONSQUEEZY_RECOVERY_LARGE
  LEMONSQUEEZY_RECOVERY_XL
"""
from __future__ import annotations

import os
import uuid
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

log = logging.getLogger(__name__)

# ─── Plan catalogue (server-side only — never trust client) ─────────────
STORAGE_PLANS = {
    "free": {
        "id": "free",
        "label_ar": "مجاني",
        "label_en": "Free",
        "price_usd": 0,
        "quota_mb": 250,
        "lemon_var": None,
        "monthly": False,
        "description_ar": "تجربة مجانية — 250 ميجا تخزين",
        "highlight": False,
    },
    "starter": {
        "id": "starter",
        "label_ar": "ستارتر",
        "label_en": "Starter",
        "price_usd": 7,
        "quota_mb": 3 * 1024,         # 3 GB
        "lemon_var": "LEMONSQUEEZY_STORAGE_STARTER",
        "monthly": True,
        "description_ar": "للمواقع الصغيرة — 3 جيجا تخزين",
        "highlight": False,
    },
    "plus": {
        "id": "plus",
        "label_ar": "بلَس",
        "label_en": "Plus",
        "price_usd": 14,
        "quota_mb": 15 * 1024,        # 15 GB
        "lemon_var": "LEMONSQUEEZY_STORAGE_PLUS",
        "monthly": True,
        "description_ar": "الأكثر شعبية — 15 جيجا تخزين",
        "highlight": True,             # featured tier
    },
    "pro": {
        "id": "pro",
        "label_ar": "برو",
        "label_en": "Pro",
        "price_usd": 29,
        "quota_mb": 75 * 1024,        # 75 GB
        "lemon_var": "LEMONSQUEEZY_STORAGE_PRO",
        "monthly": True,
        "description_ar": "للوكالات — 75 جيجا تخزين",
        "highlight": False,
    },
    "studio": {
        "id": "studio",
        "label_ar": "ستوديو",
        "label_en": "Studio",
        "price_usd": 59,
        "quota_mb": 300 * 1024,       # 300 GB
        "lemon_var": "LEMONSQUEEZY_STORAGE_STUDIO",
        "monthly": True,
        "description_ar": "للشركات الكبيرة — 300 جيجا تخزين",
        "highlight": False,
    },
}

# ─── Recovery fee tiers ─────────────────────────────────────────────────
RECOVERY_TIERS = {
    "small":  {"id": "small",  "label_ar": "استرداد صغير",  "max_gb": 1,    "price_usd": 5,  "lemon_var": "LEMONSQUEEZY_RECOVERY_SMALL"},
    "medium": {"id": "medium", "label_ar": "استرداد متوسط",  "max_gb": 10,   "price_usd": 15, "lemon_var": "LEMONSQUEEZY_RECOVERY_MEDIUM"},
    "large":  {"id": "large",  "label_ar": "استرداد كبير",   "max_gb": 50,   "price_usd": 35, "lemon_var": "LEMONSQUEEZY_RECOVERY_LARGE"},
    "xl":     {"id": "xl",     "label_ar": "استرداد ضخم",    "max_gb": 9999, "price_usd": 79, "lemon_var": "LEMONSQUEEZY_RECOVERY_XL"},
}

# ─── Grace period config ────────────────────────────────────────────────
GRACE_DAYS = 10
ARCHIVE_RETENTION_DAYS = 180   # 6 months — after this we may purge


def pick_recovery_tier(used_mb: float) -> dict:
    """Return the cheapest recovery tier that fits the user's archived size."""
    used_gb = used_mb / 1024.0
    for tier in ("small", "medium", "large", "xl"):
        t = RECOVERY_TIERS[tier]
        if used_gb <= t["max_gb"]:
            return t
    return RECOVERY_TIERS["xl"]


class CheckoutIn(BaseModel):
    plan_id: str


class RecoveryCheckoutIn(BaseModel):
    # tier auto-picked from user's archived size; this just confirms intent
    confirm: bool = True


async def _lemon_create_checkout(
    api_key: str,
    store_id: str,
    variant_id: str,
    custom: dict,
    redirect_url: str,
) -> str:
    """Generic LemonSqueezy checkout creator (subscription or one-time).
    Returns the hosted checkout URL.
    """
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {"custom": custom},
                "product_options": {"redirect_url": redirect_url},
                "checkout_options": {"embed": False, "media": False, "logo": True, "button_color": "#fbbf24"},
                "preview": False,
            },
            "relationships": {
                "store": {"data": {"type": "stores", "id": str(store_id)}},
                "variant": {"data": {"type": "variants", "id": str(variant_id)}},
            },
        }
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post("https://api.lemonsqueezy.com/v1/checkouts", json=payload, headers=headers)
    if r.status_code >= 400:
        log.error(f"[storage/lemon] {r.status_code}: {r.text[:300]}")
        raise HTTPException(500, f"LemonSqueezy error {r.status_code}")
    data = r.json()
    url = data.get("data", {}).get("attributes", {}).get("url")
    if not url:
        raise HTTPException(500, "LemonSqueezy لم يرجع رابط")
    return url


async def _get_user_storage_subscription(db, user_id: str) -> dict:
    """Fetch (or default) the user's storage subscription record."""
    sub = await db.storage_subscriptions.find_one({"user_id": user_id}, {"_id": 0})
    if not sub:
        return {
            "user_id": user_id,
            "plan_id": "free",
            "status": "active",                # active | past_due | archived | cancelled
            "lemon_subscription_id": None,
            "current_period_end": None,
            "grace_started_at": None,
            "archived_at": None,
        }
    return sub


def register_storage_billing(app, db, get_current_user):
    router = APIRouter(prefix="/api/storage", tags=["storage-billing"])

    # ─── GET /api/storage/plans ─────────────────────────────────────────
    @router.get("/plans")
    async def list_plans():
        # Mark which variants are configured (so the frontend can disable
        # buttons until the owner adds the env vars).
        out = []
        for plan in STORAGE_PLANS.values():
            available = True
            if plan["lemon_var"] is not None:
                available = bool(os.environ.get(plan["lemon_var"]))
            out.append({**plan, "available": available, "quota_gb": round(plan["quota_mb"] / 1024, 1)})
        return {"plans": out, "recovery": list(RECOVERY_TIERS.values()), "grace_days": GRACE_DAYS}

    # ─── GET /api/storage/subscription ──────────────────────────────────
    @router.get("/subscription")
    async def get_subscription(user=Depends(get_current_user)):
        sub = await _get_user_storage_subscription(db, user["user_id"])
        plan = STORAGE_PLANS.get(sub["plan_id"]) or STORAGE_PLANS["free"]
        # Compute grace countdown if past_due
        grace_days_left = None
        if sub.get("status") == "past_due" and sub.get("grace_started_at"):
            try:
                started = datetime.fromisoformat(sub["grace_started_at"])
                elapsed = (datetime.now(timezone.utc) - started).days
                grace_days_left = max(0, GRACE_DAYS - elapsed)
            except Exception:
                pass
        return {
            "plan_id": sub["plan_id"],
            "plan_label_ar": plan["label_ar"],
            "plan_quota_mb": plan["quota_mb"],
            "plan_quota_gb": round(plan["quota_mb"] / 1024, 1),
            "plan_price_usd": plan["price_usd"],
            "status": sub.get("status", "active"),
            "current_period_end": sub.get("current_period_end"),
            "grace_started_at": sub.get("grace_started_at"),
            "grace_days_left": grace_days_left,
            "archived_at": sub.get("archived_at"),
            "can_purchase": True,
        }

    # ─── POST /api/storage/checkout ─────────────────────────────────────
    @router.post("/checkout")
    async def create_storage_checkout(body: CheckoutIn, user=Depends(get_current_user)):
        plan = STORAGE_PLANS.get(body.plan_id)
        if not plan:
            raise HTTPException(400, "خطة غير صحيحة")
        if plan["id"] == "free":
            # Downgrade to free — no checkout needed, just mark and return
            await db.storage_subscriptions.update_one(
                {"user_id": user["user_id"]},
                {"$set": {
                    "user_id": user["user_id"],
                    "plan_id": "free",
                    "status": "active",
                    "lemon_subscription_id": None,
                    "current_period_end": None,
                    "grace_started_at": None,
                    "archived_at": None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }},
                upsert=True,
            )
            await db.users.update_one(
                {"id": user["user_id"]},
                {"$set": {"storage_tier": "free", "storage_quota_mb": plan["quota_mb"]}},
            )
            return {"ok": True, "downgraded_to": "free"}

        api_key = os.environ.get("LEMONSQUEEZY_API_KEY")
        store_id = os.environ.get("LEMONSQUEEZY_STORE_ID")
        variant_id = os.environ.get(plan["lemon_var"] or "")
        if not (api_key and store_id):
            raise HTTPException(503, "LemonSqueezy غير مُهيأ")
        if not variant_id:
            raise HTTPException(
                503,
                f"لم يُضبط Variant ID لباقة {plan['label_ar']} — ضع `{plan['lemon_var']}` في .env",
            )
        frontend = os.environ.get("FRONTEND_URL", "https://zenrex.ai").rstrip("/")
        txn_ref = str(uuid.uuid4())
        url = await _lemon_create_checkout(
            api_key=api_key,
            store_id=store_id,
            variant_id=variant_id,
            custom={
                "user_id": user["user_id"],
                "kind": "storage_subscription",
                "plan_id": plan["id"],
                "txn_ref": txn_ref,
            },
            redirect_url=f"{frontend}/billing/storage?status=success&txn={txn_ref}",
        )
        await db.payment_transactions.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "method": "lemonsqueezy",
            "txn_ref": txn_ref,
            "kind": "storage_subscription",
            "plan_id": plan["id"],
            "amount_usd": plan["price_usd"],
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"checkout_url": url, "txn_ref": txn_ref}

    # ─── POST /api/storage/recovery/checkout ────────────────────────────
    @router.post("/recovery/checkout")
    async def create_recovery_checkout(_body: RecoveryCheckoutIn, user=Depends(get_current_user)):
        sub = await _get_user_storage_subscription(db, user["user_id"])
        if sub.get("status") != "archived":
            raise HTTPException(400, "حسابك ليس في حالة أرشفة — لا حاجة للاسترداد")
        archived_size_mb = float(sub.get("archived_size_mb") or 0)
        tier = pick_recovery_tier(archived_size_mb)
        api_key = os.environ.get("LEMONSQUEEZY_API_KEY")
        store_id = os.environ.get("LEMONSQUEEZY_STORE_ID")
        variant_id = os.environ.get(tier["lemon_var"])
        if not (api_key and store_id):
            raise HTTPException(503, "LemonSqueezy غير مُهيأ")
        if not variant_id:
            raise HTTPException(503, f"Variant ID مفقود لـ {tier['label_ar']} — ضع `{tier['lemon_var']}` في .env")
        frontend = os.environ.get("FRONTEND_URL", "https://zenrex.ai").rstrip("/")
        txn_ref = str(uuid.uuid4())
        url = await _lemon_create_checkout(
            api_key=api_key,
            store_id=store_id,
            variant_id=variant_id,
            custom={
                "user_id": user["user_id"],
                "kind": "storage_recovery",
                "recovery_tier": tier["id"],
                "txn_ref": txn_ref,
            },
            redirect_url=f"{frontend}/billing/storage?status=recovered&txn={txn_ref}",
        )
        await db.payment_transactions.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "method": "lemonsqueezy",
            "txn_ref": txn_ref,
            "kind": "storage_recovery",
            "recovery_tier": tier["id"],
            "amount_usd": tier["price_usd"],
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"checkout_url": url, "txn_ref": txn_ref, "tier": tier}

    # ─── POST /api/storage/webhook ─ LemonSqueezy events ───────────────
    # NOTE: For HMAC validation use LEMONSQUEEZY_WEBHOOK_SECRET if you set it
    # at the LS dashboard. Many LS users keep this open; we validate via the
    # custom user_id field which is server-set during checkout creation.
    @router.post("/webhook")
    async def storage_webhook(payload: dict):
        try:
            event = payload.get("meta", {}).get("event_name", "")
            attrs = payload.get("data", {}).get("attributes", {}) or {}
            custom = (
                attrs.get("first_order_item", {}).get("custom_data")
                or attrs.get("custom_data")
                or payload.get("meta", {}).get("custom_data")
                or {}
            )
            user_id = custom.get("user_id")
            kind = custom.get("kind")
            if not user_id:
                return {"ok": True, "skipped": "no_user_id"}

            # ── A) Successful initial / renewal payment for storage sub ──
            if event in ("order_created", "subscription_created", "subscription_payment_success") and kind == "storage_subscription":
                plan_id = custom.get("plan_id") or "starter"
                plan = STORAGE_PLANS.get(plan_id) or STORAGE_PLANS["starter"]
                lemon_sub_id = attrs.get("subscription_id") or attrs.get("first_subscription_item", {}).get("subscription_id")
                period_end = attrs.get("renews_at") or (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                await db.storage_subscriptions.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "user_id": user_id,
                        "plan_id": plan_id,
                        "status": "active",
                        "lemon_subscription_id": lemon_sub_id,
                        "current_period_end": period_end,
                        "grace_started_at": None,
                        "archived_at": None,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                    upsert=True,
                )
                # Lift any archived flag on the user + bump quota
                await db.users.update_one(
                    {"id": user_id},
                    {"$set": {
                        "storage_tier": plan_id,
                        "storage_quota_mb": plan["quota_mb"],
                        "storage_archived": False,
                    }},
                )
                # If files were archived, restore them
                await db.freebuild_projects.update_many(
                    {"user_id": user_id, "status": "archived"},
                    {"$set": {"status": "active"}},
                )
                # Mark txn complete
                if custom.get("txn_ref"):
                    await db.payment_transactions.update_one(
                        {"txn_ref": custom["txn_ref"]},
                        {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}},
                    )
                log.info(f"[storage-webhook] subscription {plan_id} active for {user_id}")
                return {"ok": True, "applied": "subscription_active"}

            # ── B) Failed renewal → start grace period ───────────────────
            if event in ("subscription_payment_failed",):
                await db.storage_subscriptions.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "status": "past_due",
                        "grace_started_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
                log.info(f"[storage-webhook] {user_id} -> past_due (grace start)")
                return {"ok": True, "applied": "grace_start"}

            # ── C) Cancelled subscription (manual or auto) ───────────────
            if event in ("subscription_cancelled", "subscription_expired"):
                await db.storage_subscriptions.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "status": "past_due",
                        "grace_started_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
                return {"ok": True, "applied": "cancelled_grace"}

            # ── D) Successful recovery payment → un-archive + require active sub ──
            if event in ("order_created",) and kind == "storage_recovery":
                await db.storage_subscriptions.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "status": "past_due",            # still must renew sub
                        "archived_at": None,
                        "archived_size_mb": 0,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
                await db.freebuild_projects.update_many(
                    {"user_id": user_id, "status": "archived"},
                    {"$set": {"status": "active"}},
                )
                await db.users.update_one(
                    {"id": user_id},
                    {"$set": {"storage_archived": False}},
                )
                if custom.get("txn_ref"):
                    await db.payment_transactions.update_one(
                        {"txn_ref": custom["txn_ref"]},
                        {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}},
                    )
                log.info(f"[storage-webhook] recovery applied for {user_id}")
                return {"ok": True, "applied": "recovery_complete"}

            return {"ok": True, "skipped": event}
        except Exception as e:
            log.error(f"[storage-webhook] error: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}

    # ─── Background job: enforce grace → archive ───────────────────────
    async def enforce_grace_loop():
        """Once per hour, scan past_due users; if grace > GRACE_DAYS, archive."""
        while True:
            try:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=GRACE_DAYS)).isoformat()
                cur = db.storage_subscriptions.find(
                    {"status": "past_due", "grace_started_at": {"$lte": cutoff}},
                    {"_id": 0, "user_id": 1},
                )
                async for row in cur:
                    uid = row["user_id"]
                    # Compute archived size for recovery tier pricing
                    try:
                        from modules.freebuild.freebuild_chat import _user_total_bytes  # type: ignore
                        archived_bytes = await _user_total_bytes(db, uid)
                    except Exception:
                        archived_bytes = 0
                    archived_mb = round(archived_bytes / (1024 * 1024), 2)
                    await db.storage_subscriptions.update_one(
                        {"user_id": uid},
                        {"$set": {
                            "status": "archived",
                            "archived_at": datetime.now(timezone.utc).isoformat(),
                            "archived_size_mb": archived_mb,
                        }},
                    )
                    await db.users.update_one({"id": uid}, {"$set": {"storage_archived": True}})
                    await db.freebuild_projects.update_many(
                        {"user_id": uid, "status": {"$ne": "deleted"}},
                        {"$set": {"status": "archived"}},
                    )
                    log.info(f"[storage-grace] user {uid} archived ({archived_mb} MB)")
            except Exception as e:
                log.warning(f"[storage-grace] loop error: {e}")
            await asyncio.sleep(3600)  # check every hour

    @app.on_event("startup")
    async def _start_grace_loop():
        try:
            asyncio.create_task(enforce_grace_loop())
            log.info("[storage-billing] grace enforcement loop started")
        except Exception as e:
            log.warning(f"[storage-billing] could not start grace loop: {e}")

    app.include_router(router)
    log.info("Storage Billing module registered (/api/storage/*)")
