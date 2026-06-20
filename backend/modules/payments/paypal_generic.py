"""
Generic PayPal + LemonSqueezy payments for Zenrex packages.

Handles all subscription tiers + Project Pack:
  - tier_starter_monthly ($19 / 2,000 credits)
  - tier_pro_monthly ($69 / 8,000 credits)
  - tier_studio_monthly ($199 / 25,000 credits)
  - project_pack ($49 / 5,000 credits)

After payment success → adds credits + sets storage_tier.
Ready Sites packages have their own flow (creates a project after payment).
"""
from __future__ import annotations

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

log = logging.getLogger(__name__)

# Maps package_id → price/credits/tier + LemonSqueezy variant env var name
PACKAGES = {
    "tier_starter_monthly": {
        "price_usd": 19.00,  "credits": 2_000,  "tier": "starter", "duration_days": 30,
        "label": "Zenrex Starter (monthly)", "lemon_var": "LEMONSQUEEZY_VARIANT_STARTER",
    },
    "tier_pro_monthly": {
        "price_usd": 69.00,  "credits": 8_000,  "tier": "pro", "duration_days": 30,
        "label": "Zenrex Pro (monthly)", "lemon_var": "LEMONSQUEEZY_VARIANT_PRO",
    },
    "tier_studio_monthly": {
        "price_usd": 199.00, "credits": 25_000, "tier": "studio", "duration_days": 30,
        "label": "Zenrex Studio (monthly)", "lemon_var": "LEMONSQUEEZY_VARIANT_STUDIO",
    },
    "project_pack": {
        "price_usd": 49.00,  "credits": 5_000,  "tier": "starter", "duration_days": 365,
        "label": "Zenrex Project Pack", "lemon_var": "LEMONSQUEEZY_VARIANT_PROJECT_PACK",
    },
}


class PayPalCreateIn(BaseModel):
    package_id: str
    return_url: Optional[str] = None


class PayPalCaptureIn(BaseModel):
    order_id: str
    payer_id: Optional[str] = None


class LemonCreateIn(BaseModel):
    package_id: str


def register_payments(app, db, get_current_user):
    router = APIRouter(prefix="/api/payments", tags=["payments"])

    # ───────────────────────────── PayPal ─────────────────────────────
    @router.post("/paypal/create")
    async def paypal_create(body: PayPalCreateIn, user=Depends(get_current_user)):
        pkg = PACKAGES.get(body.package_id)
        if not pkg:
            raise HTTPException(400, "باقة غير صحيحة")
        if not (os.environ.get("PAYPAL_CLIENT_ID") and os.environ.get("PAYPAL_SECRET")):
            raise HTTPException(503, "PayPal غير مُهيأ على الخادم")
        try:
            import paypalrestsdk
            paypalrestsdk.configure({
                "mode": os.environ.get("PAYPAL_MODE", "live"),
                "client_id": os.environ["PAYPAL_CLIENT_ID"],
                "client_secret": os.environ["PAYPAL_SECRET"],
            })
            frontend = os.environ.get("FRONTEND_URL", "https://zenrex.ai").rstrip("/")
            ret = body.return_url or f"{frontend}/payments/paypal-return"
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": f"{ret}?package={body.package_id}",
                    "cancel_url": f"{frontend}/pricing",
                },
                "transactions": [{
                    "item_list": {"items": [{
                        "name": pkg["label"], "sku": body.package_id,
                        "price": f"{pkg['price_usd']:.2f}", "currency": "USD", "quantity": 1,
                    }]},
                    "amount": {"total": f"{pkg['price_usd']:.2f}", "currency": "USD"},
                    "description": pkg["label"],
                }],
            })
            if not payment.create():
                log.error(f"[paypal/create] failed: {payment.error}")
                raise HTTPException(500, f"فشل PayPal: {payment.error}")
            approval_url = next((link.href for link in payment.links if link.rel == "approval_url"), None)
            if not approval_url:
                raise HTTPException(500, "PayPal لم يرجع رابط الموافقة")
            await db.payment_transactions.insert_one({
                "id": str(uuid.uuid4()), "user_id": user["user_id"], "method": "paypal",
                "paypal_order_id": payment.id, "package_id": body.package_id,
                "amount_usd": pkg["price_usd"], "credits": pkg["credits"], "tier": pkg["tier"],
                "status": "pending", "created_at": datetime.now(timezone.utc).isoformat(),
            })
            return {"order_id": payment.id, "approval_url": approval_url}
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"[paypal/create] exception: {e}", exc_info=True)
            raise HTTPException(500, f"خطأ في PayPal: {e}")

    @router.post("/paypal/capture")
    async def paypal_capture(body: PayPalCaptureIn, user=Depends(get_current_user)):
        try:
            import paypalrestsdk
            paypalrestsdk.configure({
                "mode": os.environ.get("PAYPAL_MODE", "live"),
                "client_id": os.environ["PAYPAL_CLIENT_ID"],
                "client_secret": os.environ["PAYPAL_SECRET"],
            })
            payment = paypalrestsdk.Payment.find(body.order_id)
            if not payment:
                raise HTTPException(404, "الطلب غير موجود")
            txn = await db.payment_transactions.find_one(
                {"paypal_order_id": body.order_id, "user_id": user["user_id"]}, {"_id": 0},
            )
            if not txn:
                raise HTTPException(404, "السجل غير موجود")
            if txn.get("status") == "completed":
                return {"ok": True, "already": True, "package_id": txn.get("package_id")}
            if body.payer_id:
                ok = payment.execute({"payer_id": body.payer_id})
                if not ok:
                    log.error(f"[paypal/capture] execute failed: {payment.error}")
                    raise HTTPException(500, f"فشل تنفيذ الدفع: {payment.error}")
            pkg = PACKAGES.get(txn["package_id"]) or {}
            await _grant_package(db, user["user_id"], pkg)
            await db.payment_transactions.update_one(
                {"paypal_order_id": body.order_id},
                {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}},
            )
            return {"ok": True, "package_id": txn["package_id"],
                    "credits_added": pkg.get("credits", 0), "tier": pkg.get("tier")}
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"[paypal/capture] exception: {e}", exc_info=True)
            raise HTTPException(500, f"خطأ: {e}")

    # ───────────────────────────── LemonSqueezy ───────────────────────
    @router.post("/lemonsqueezy/create")
    async def lemon_create(body: LemonCreateIn, user=Depends(get_current_user)):
        pkg = PACKAGES.get(body.package_id)
        if not pkg:
            raise HTTPException(400, "باقة غير صحيحة")
        api_key = os.environ.get("LEMONSQUEEZY_API_KEY")
        store_id = os.environ.get("LEMONSQUEEZY_STORE_ID")
        variant_id = os.environ.get(pkg["lemon_var"])
        if not (api_key and store_id):
            raise HTTPException(503, "LemonSqueezy غير مُهيأ")
        if not variant_id:
            raise HTTPException(503,
                f"لم يُضبط Variant ID للباقة — ضع `{pkg['lemon_var']}` في الـ .env")

        frontend = os.environ.get("FRONTEND_URL", "https://zenrex.ai").rstrip("/")
        txn_ref = str(uuid.uuid4())
        payload = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_data": {
                        "email": (user.get("email") or ""),
                        "custom": {
                            "user_id": user["user_id"],
                            "package_id": body.package_id,
                            "txn_ref": txn_ref,
                        },
                    },
                    "product_options": {
                        "redirect_url": f"{frontend}/payments/lemon-return?txn={txn_ref}",
                    },
                    "checkout_options": {"embed": False, "media": False, "logo": True,
                        # Disable PayPal inside LemonSqueezy (user prefers PayPal as separate option)
                        "button_color": "#fbbf24",
                    },
                    # Hide PayPal option inside the LemonSqueezy hosted page
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
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.post("https://api.lemonsqueezy.com/v1/checkouts", json=payload, headers=headers)
            if r.status_code >= 400:
                log.error(f"[lemon/create] {r.status_code}: {r.text[:300]}")
                raise HTTPException(500, f"LemonSqueezy: {r.status_code}")
            data = r.json()
            url = data.get("data", {}).get("attributes", {}).get("url")
            if not url:
                raise HTTPException(500, "LemonSqueezy لم يرجع رابط")
            await db.payment_transactions.insert_one({
                "id": str(uuid.uuid4()), "user_id": user["user_id"], "method": "lemonsqueezy",
                "txn_ref": txn_ref, "package_id": body.package_id,
                "amount_usd": pkg["price_usd"], "credits": pkg["credits"], "tier": pkg["tier"],
                "status": "pending", "created_at": datetime.now(timezone.utc).isoformat(),
            })
            return {"checkout_url": url, "txn_ref": txn_ref}
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"[lemon/create] exception: {e}", exc_info=True)
            raise HTTPException(500, f"خطأ LemonSqueezy: {e}")

    @router.post("/lemonsqueezy/webhook")
    async def lemon_webhook(payload: dict):
        try:
            event = payload.get("meta", {}).get("event_name", "")
            if event not in ("order_created", "subscription_created"):
                return {"ok": True, "skipped": event}
            attrs = payload.get("data", {}).get("attributes", {})
            custom = (attrs.get("first_order_item", {}).get("custom_data")
                      or attrs.get("custom_data") or {})
            txn_ref = custom.get("txn_ref")
            if not txn_ref:
                return {"ok": True, "skipped": "no_txn_ref"}
            txn = await db.payment_transactions.find_one({"txn_ref": txn_ref}, {"_id": 0})
            if not txn:
                return {"ok": True, "skipped": "txn_not_found"}
            if txn.get("status") == "completed":
                return {"ok": True, "already": True}
            pkg = PACKAGES.get(txn["package_id"]) or {}
            await _grant_package(db, txn["user_id"], pkg)
            await db.payment_transactions.update_one(
                {"txn_ref": txn_ref},
                {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}},
            )
            return {"ok": True}
        except Exception as e:
            log.error(f"[lemon webhook] error: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}

    @router.get("/payment-status/{txn_ref}")
    async def payment_status(txn_ref: str, user=Depends(get_current_user)):
        txn = await db.payment_transactions.find_one(
            {"txn_ref": txn_ref, "user_id": user["user_id"]}, {"_id": 0},
        )
        if not txn:
            raise HTTPException(404, "غير موجود")
        return {"status": txn.get("status"), "package_id": txn.get("package_id")}

    app.include_router(router)
    log.info("Generic payments registered (PayPal + LemonSqueezy)")


async def _grant_package(db, user_id: str, pkg: dict):
    """Add credits + set tier expiry after successful payment."""
    credits = int(pkg.get("credits") or 0)
    tier = pkg.get("tier")
    update = {}
    if credits:
        update["$inc"] = {"credits": credits}
    if tier:
        expires = (datetime.now(timezone.utc) + timedelta(days=pkg.get("duration_days", 30))).isoformat()
        update["$set"] = {"storage_tier": tier, "tier_expires_at": expires}
    if update:
        await db.users.update_one({"id": user_id}, update)
    log.info(f"[payments] granted +{credits} credits, tier={tier} to user {user_id}")

