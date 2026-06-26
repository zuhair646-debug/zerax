"""
Generic PayPal payments for Zenrex packages.

Handles all subscription tiers + Project Pack.
After payment success → adds credits + sets storage_tier.
Ready Sites packages have their own flow (creates a project after payment).

Note: Lemon Squeezy was fully removed in Feb 2026. PayPal is the sole processor.
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

# Credit-only packages.
PACKAGES = {
    "credits_mini":   {"price_usd": 9.00,    "credits": 1_200,   "label": "1,200 Credits"},
    "credits_small":  {"price_usd": 19.00,   "credits": 2_800,   "label": "2,800 Credits"},
    "credits_medium": {"price_usd": 49.00,   "credits": 7_500,   "label": "7,500 Credits"},
    "credits_large":  {"price_usd": 99.00,   "credits": 16_000,  "label": "16,000 Credits"},
    "credits_xl":     {"price_usd": 199.00,  "credits": 32_000,  "label": "32,000 Credits"},
    "credits_pro":    {"price_usd": 500.00,  "credits": 80_000,  "label": "80,000 Credits"},
    "credits_mega":   {"price_usd": 1000.00, "credits": 160_000, "label": "160,000 Credits"},
    "credits_enterprise": {"price_usd": 3000.00, "credits": 510_000, "label": "510,000 Credits"},
}

# Custom amount: 130 credits/$ (sits just below the smallest pack at 133 cr/$
# so packs always offer the better bulk-discount value, no inversion at $10K).
CREDITS_PER_USD = 130
CUSTOM_MIN_USD = 5
CUSTOM_MAX_USD = 10000

# Progressive bonus on top of base rate. Tiers MUST mirror frontend
# CUSTOM_BONUS_TIERS so the receipt matches the on-screen quote.
CUSTOM_BONUS_TIERS = [
    (100,   499,   500),       # +500 credits
    (500,   999,   5_000),     # +5,000
    (1000,  2999,  20_000),    # +20,000
    (3000,  4999,  70_000),    # +70,000
    (5000,  7499,  200_000),   # +200,000
    (7500,  9999,  350_000),   # +350,000
    (10000, 10000, 500_000),   # +500,000 🎁 max-tier promo
]


def _custom_bonus(amt_usd: float) -> int:
    if not amt_usd or amt_usd < 100:
        return 0
    for lo, hi, bonus in CUSTOM_BONUS_TIERS:
        if lo <= amt_usd <= hi:
            return int(bonus)
    return 0


class PayPalCreateIn(BaseModel):
    package_id: str
    return_url: Optional[str] = None


class PayPalCaptureIn(BaseModel):
    order_id: str
    payer_id: Optional[str] = None


class CustomAmountIn(BaseModel):
    amount_usd: float  # USD amount the user wants to pay
    method: str        # "paypal" only (Lemon Squeezy removed Feb 2026)


# ═════════════════════════════════════════════════════════════════
# 💳 UNIVERSAL PayPal payload — defined at MODULE level so FastAPI
# can resolve the type annotation during route registration
# (defining it inside register_payments() caused NameError).
# ═════════════════════════════════════════════════════════════════
class UniversalCreateIn(BaseModel):
    pkg_id: str                       # e.g. "storage_starter" / "code_only" / "independence"
    amount_usd: float                 # final price the user is paying
    meta: Optional[dict] = None       # context (project_id, tier, etc.)
    return_path: Optional[str] = None  # frontend path to land on after capture


def register_payments(app, db, get_current_user):
    router = APIRouter(prefix="/api/payments", tags=["payments"])

    # ═════════════════════════════════════════════════════════════
    # 💳 UNIVERSAL PayPal — single endpoint that any feature can use
    # (storage tiers, independence tier, code unlock, etc.). Replaces
    # the per-feature endpoints since Lemon Squeezy is being removed.
    # ═════════════════════════════════════════════════════════════
    @router.post("/paypal/create")
    async def paypal_create_universal(body: UniversalCreateIn, user=Depends(get_current_user)):
        if not (os.environ.get("PAYPAL_CLIENT_ID") and os.environ.get("PAYPAL_SECRET")):
            raise HTTPException(503, "PayPal غير مُهيأ على الخادم")
        if body.amount_usd <= 0 or body.amount_usd > 5000:
            raise HTTPException(400, "مبلغ غير صالح")
        try:
            import paypalrestsdk
            paypalrestsdk.configure({
                "mode": os.environ.get("PAYPAL_MODE", "live"),
                "client_id": os.environ["PAYPAL_CLIENT_ID"],
                "client_secret": os.environ["PAYPAL_SECRET"],
            })
            frontend = os.environ.get("FRONTEND_URL", "https://zenrex.ai").rstrip("/")
            ret_path = body.return_path or "/payments/paypal-return"
            label = (body.meta or {}).get("label_ar") or body.pkg_id

            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": f"{frontend}{ret_path}?pkg={body.pkg_id}",
                    "cancel_url": f"{frontend}/pricing?cancelled=1",
                },
                "transactions": [{
                    "item_list": {"items": [{
                        "name": label[:120], "sku": body.pkg_id[:120],
                        "price": f"{body.amount_usd:.2f}", "currency": "USD", "quantity": 1,
                    }]},
                    "amount": {"total": f"{body.amount_usd:.2f}", "currency": "USD"},
                    "description": label[:120],
                }],
            })
            if not payment.create():
                log.error(f"[paypal/create-universal] failed: {payment.error}")
                raise HTTPException(500, f"فشل PayPal: {payment.error}")
            approval_url = next((link.href for link in payment.links if link.rel == "approval_url"), None)
            if not approval_url:
                raise HTTPException(500, "PayPal لم يرجع رابط الموافقة")
            await db.payment_transactions.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user["user_id"],
                "method": "paypal",
                "paypal_order_id": payment.id,
                "pkg_id": body.pkg_id,
                "amount_usd": body.amount_usd,
                "meta": body.meta or {},
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            return {"order_id": payment.id, "approval_url": approval_url, "amount_usd": body.amount_usd, "pkg_id": body.pkg_id}
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"[paypal/create-universal] exception: {e}", exc_info=True)
            raise HTTPException(500, f"خطأ في PayPal: {e}")

    # ───────────────────────────── PayPal (legacy: credit packages) ─────────────────────────────
    @router.post("/paypal/create-credits")
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
                "amount_usd": pkg["price_usd"], "credits": pkg["credits"],
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
                    "credits_added": pkg.get("credits", 0)}
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"[paypal/capture] exception: {e}", exc_info=True)
            raise HTTPException(500, f"خطأ: {e}")

    # ───────────────────────── Lemon Squeezy removed (Feb 2026) ─────────────────────────

    @router.get("/payment-status/{txn_ref}")
    async def payment_status(txn_ref: str, user=Depends(get_current_user)):
        txn = await db.payment_transactions.find_one(
            {"txn_ref": txn_ref, "user_id": user["user_id"]}, {"_id": 0},
        )
        if not txn:
            raise HTTPException(404, "غير موجود")
        return {"status": txn.get("status"), "package_id": txn.get("package_id")}

    @router.post("/custom/create")
    async def custom_create(body: CustomAmountIn, user=Depends(get_current_user)):
        """User picks any amount → gets amount * CREDITS_PER_USD credits + tiered bonus."""
        amt = float(body.amount_usd or 0)
        if amt < CUSTOM_MIN_USD or amt > CUSTOM_MAX_USD:
            raise HTTPException(400, f"المبلغ يجب أن يكون بين ${CUSTOM_MIN_USD} و ${CUSTOM_MAX_USD}")
        base_credits = int(round(amt * CREDITS_PER_USD))
        bonus = _custom_bonus(amt)
        credits = base_credits + bonus
        # Build a synthetic package for this transaction
        synthetic_pkg_id = f"custom_{int(amt*100)}"
        bonus_suffix = f" (+{bonus:,} bonus)" if bonus else ""
        synthetic_pkg = {
            "price_usd": round(amt, 2),
            "credits": credits,
            "label": f"{credits:,} Credits — Custom${int(amt)}{bonus_suffix}",
        }
        if body.method == "paypal":
            # Use the same PayPal flow but with synthetic package
            PACKAGES[synthetic_pkg_id] = synthetic_pkg
            return await paypal_create(PayPalCreateIn(package_id=synthetic_pkg_id), user)
        else:
            raise HTTPException(400, "المبلغ المخصص متاح حالياً عبر PayPal فقط")

    app.include_router(router)
    log.info("Generic payments registered (PayPal + Custom — Lemon Squeezy removed)")


async def _grant_package(db, user_id: str, pkg: dict):
    """Add credits after successful payment (no subscription/tier logic — all one-time)."""
    credits = int(pkg.get("credits") or 0)
    if credits:
        await db.users.update_one({"id": user_id}, {"$inc": {"credits": credits}})
    log.info(f"[payments] granted +{credits} credits to user {user_id}")

