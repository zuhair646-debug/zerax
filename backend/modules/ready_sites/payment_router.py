"""
Ready Sites — Payment Methods (PayPal + LemonSqueezy)

Users pay for Ready Sites Trial ($9) or Purchase ($79) via:
  • PayPal  (direct via paypalrestsdk — credentials in .env)
  • LemonSqueezy (REST API — credentials in .env, requires variant IDs)

After successful payment, a FreeBuild project is auto-created with category
context so the user lands in the chat with AI ready to ask for logo + name.
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

# Same labels used in the main ready_sites flow
CATEGORY_LABELS = {
    "restaurants": {"ar": "مطاعم وكافيهات", "icon": "🍽️", "kind": "restaurant"},
    "electronics": {"ar": "إلكترونيات وتقنية", "icon": "📱", "kind": "store"},
    "stationery":  {"ar": "قرطاسيات ومكتبات", "icon": "✏️", "kind": "store"},
    "grocery":     {"ar": "بقالات وسوبرماركت", "icon": "🛒", "kind": "store"},
    "pharmacy":    {"ar": "صيدليات", "icon": "💊", "kind": "store"},
    "fashion":     {"ar": "أزياء وموضة", "icon": "👗", "kind": "store"},
    "beauty":      {"ar": "تجميل وعطور", "icon": "💄", "kind": "store"},
    "flowers":     {"ar": "زهور وهدايا", "icon": "🌸", "kind": "store"},
}

# Plan → USD price + credits added
PLAN_CONFIG = {
    "trial":    {"price_usd": 9.00,  "credits": 500,   "duration_days": 7,   "label": "Ready Sites — Paid Trial (7 days)"},
    "purchase": {"price_usd": 79.00, "credits": 5_000, "duration_days": 365, "label": "Ready Sites — Full Ownership"},
}


class PayPalCreateIn(BaseModel):
    category_id: str
    plan: str  # "trial" | "purchase"
    return_url: Optional[str] = None  # frontend success URL


class PayPalCaptureIn(BaseModel):
    order_id: str   # PayPal order ID
    payer_id: Optional[str] = None


class LemonCreateIn(BaseModel):
    category_id: str
    plan: str  # "trial" | "purchase"


async def _create_ready_sites_project(db, user_id: str, category_id: str, plan: str,
                                       method: str, txn_ref: str):
    """Idempotently create a FreeBuild project for a Ready Sites purchase."""
    # Idempotency check
    existing = await db.freebuild_chat_projects.find_one(
        {"ready_sites_txn_ref": txn_ref}, {"id": 1, "_id": 0},
    )
    if existing:
        return existing["id"]
    cat = CATEGORY_LABELS.get(category_id) or {"ar": category_id, "icon": "🛍️", "kind": "store"}
    cfg = PLAN_CONFIG.get(plan) or PLAN_CONFIG["trial"]
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    trial_until = (
        (datetime.now(timezone.utc) + timedelta(days=cfg["duration_days"])).isoformat()
        if plan == "trial" else None
    )
    greeting = (
        f"أهلاً وسهلاً! 👋\n\n"
        f"مبروك دفعك واختيارك قالب **{cat['ar']}** {cat['icon']}.\n\n"
        f"عشان أبدأ ببناء موقعك، أحتاج معلومتين فقط:\n\n"
        f"1️⃣ **اسم متجرك**\n"
        f"2️⃣ **اللوغو** (ارفعه أو وصفه وأنا أصمّمه)\n\n"
        f"بمجرد ما تعطيني المعلومتين، راح أبني الموقع كاملاً في دقائق ✨"
    )
    await db.freebuild_chat_projects.insert_one({
        "id": project_id,
        "user_id": user_id,
        "name": f"{cat['icon']} {cat['ar']}",
        "category_id": category_id,
        "category_name": cat["ar"],
        "category_icon": cat["icon"],
        "category_kind": cat.get("kind"),
        "plan": plan,
        "trial_until": trial_until,
        "source": "ready-sites",
        "ready_sites_payment_method": method,
        "ready_sites_txn_ref": txn_ref,
        "current_html": "",
        "messages": [{
            "id": str(uuid.uuid4()), "role": "assistant",
            "content": greeting, "timestamp": now,
        }],
        "created_at": now,
        "updated_at": now,
    })
    # Add credits to user balance
    credits_to_add = int(cfg["credits"])
    if credits_to_add:
        await db.users.update_one(
            {"id": user_id}, {"$inc": {"credits": credits_to_add}},
        )
    log.info(f"[ready-sites/{method}] ✓ Created project {project_id} for user {user_id}")
    return project_id


def register_payment_routes(app, db, get_current_user):
    """Mount /api/ready-sites/paypal/* and /api/ready-sites/lemonsqueezy/*"""
    router = APIRouter(prefix="/api/ready-sites", tags=["ready-sites-payments"])

    # ─────────────────────────────── PAYPAL ───────────────────────────────
    @router.post("/paypal/create")
    async def paypal_create(body: PayPalCreateIn, user=Depends(get_current_user)):
        cfg = PLAN_CONFIG.get(body.plan)
        if not cfg:
            raise HTTPException(400, "خطة غير صحيحة")
        if body.category_id not in CATEGORY_LABELS:
            raise HTTPException(400, "تخصص غير صحيح")
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
            ret = body.return_url or f"{frontend}/ready-sites/paypal-return"
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": f"{ret}?plan={body.plan}&category={body.category_id}",
                    "cancel_url": f"{frontend}/ready-sites/purchase?category={body.category_id}",
                },
                "transactions": [{
                    "item_list": {"items": [{
                        "name": cfg["label"],
                        "sku": f"ready_sites_{body.plan}",
                        "price": f"{cfg['price_usd']:.2f}",
                        "currency": "USD",
                        "quantity": 1,
                    }]},
                    "amount": {"total": f"{cfg['price_usd']:.2f}", "currency": "USD"},
                    "description": f"Zenrex Ready Sites — {body.plan} ({body.category_id})",
                }],
            })
            if not payment.create():
                log.error(f"[paypal/create] failed: {payment.error}")
                raise HTTPException(500, f"فشل PayPal: {payment.error}")
            # Find approval URL
            approval_url = next(
                (link.href for link in payment.links if link.rel == "approval_url"),
                None,
            )
            if not approval_url:
                raise HTTPException(500, "PayPal لم يرجع رابط الموافقة")
            # Store pending txn
            await db.ready_sites_payments.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user["user_id"],
                "method": "paypal",
                "paypal_order_id": payment.id,
                "category_id": body.category_id,
                "plan": body.plan,
                "amount_usd": cfg["price_usd"],
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            return {"order_id": payment.id, "approval_url": approval_url}
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"[paypal/create] exception: {e}", exc_info=True)
            raise HTTPException(500, f"خطأ في PayPal: {e}")

    @router.post("/paypal/capture")
    async def paypal_capture(body: PayPalCaptureIn, user=Depends(get_current_user)):
        """Called by the return-URL page after the customer approves the payment."""
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
            txn = await db.ready_sites_payments.find_one(
                {"paypal_order_id": body.order_id, "user_id": user["user_id"]},
                {"_id": 0},
            )
            if not txn:
                raise HTTPException(404, "السجل غير موجود")

            # If already captured (idempotent), return the project
            if txn.get("status") == "completed":
                return {"ok": True, "project_id": txn.get("project_id"), "already": True}

            # Execute the payment
            executed = payment.execute({"payer_id": body.payer_id}) if body.payer_id else True
            if body.payer_id and not executed:
                log.error(f"[paypal/capture] execute failed: {payment.error}")
                raise HTTPException(500, f"فشل تنفيذ الدفع: {payment.error}")

            # Create project + add credits
            project_id = await _create_ready_sites_project(
                db, user["user_id"], txn["category_id"], txn["plan"],
                "paypal", body.order_id,
            )
            await db.ready_sites_payments.update_one(
                {"paypal_order_id": body.order_id},
                {"$set": {
                    "status": "completed",
                    "project_id": project_id,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
            return {"ok": True, "project_id": project_id, "redirect": f"/freebuild/chat/{project_id}?source=ready-sites"}
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"[paypal/capture] exception: {e}", exc_info=True)
            raise HTTPException(500, f"خطأ: {e}")

    # ─────────────────────────────── LEMONSQUEEZY ─────────────────────────
    @router.post("/lemonsqueezy/create")
    async def lemon_create(body: LemonCreateIn, user=Depends(get_current_user)):
        cfg = PLAN_CONFIG.get(body.plan)
        if not cfg:
            raise HTTPException(400, "خطة غير صحيحة")
        if body.category_id not in CATEGORY_LABELS:
            raise HTTPException(400, "تخصص غير صحيح")
        api_key = os.environ.get("LEMONSQUEEZY_API_KEY")
        store_id = os.environ.get("LEMONSQUEEZY_STORE_ID")
        if not (api_key and store_id):
            raise HTTPException(503, "LemonSqueezy غير مُهيأ على الخادم")

        # Variant ID per plan — must be set in env after creating products in
        # LemonSqueezy dashboard. We try env first, fall back to a generic
        # custom-price variant (if you set one as default).
        variant_id = os.environ.get(f"LEMONSQUEEZY_VARIANT_{body.plan.upper()}")
        if not variant_id:
            raise HTTPException(
                503,
                f"لازم تنشئ منتج '{cfg['label']}' في LemonSqueezy وتضع LEMONSQUEEZY_VARIANT_{body.plan.upper()} في الـ .env",
            )

        frontend = os.environ.get("FRONTEND_URL", "https://zenrex.ai").rstrip("/")
        # Unique reference so we can match the webhook event back to our project
        txn_ref = str(uuid.uuid4())
        # Fetch user email — `user` from get_current_user only has user_id
        u_doc = await db.users.find_one({"id": user["user_id"]}, {"email": 1, "_id": 0})
        u_email = (u_doc or {}).get("email") or "customer@zenrex.ai"
        payload = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_data": {
                        "email": u_email,
                        "custom": {
                            "user_id": user["user_id"],
                            "category_id": body.category_id,
                            "plan": body.plan,
                            "txn_ref": txn_ref,
                        },
                    },
                    "product_options": {
                        "redirect_url": f"{frontend}/ready-sites/lemon-return?txn={txn_ref}",
                    },
                    "checkout_options": {
                        "embed": False,
                        "media": False,
                        "logo": True,
                    },
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
                log.error(f"[lemonsqueezy/create] {r.status_code}: {r.text[:300]}")
                raise HTTPException(500, f"LemonSqueezy: {r.status_code}")
            data = r.json()
            checkout_url = data.get("data", {}).get("attributes", {}).get("url")
            if not checkout_url:
                raise HTTPException(500, "LemonSqueezy لم يرجع رابط")
            await db.ready_sites_payments.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user["user_id"],
                "method": "lemonsqueezy",
                "txn_ref": txn_ref,
                "category_id": body.category_id,
                "plan": body.plan,
                "amount_usd": cfg["price_usd"],
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            return {"checkout_url": checkout_url, "txn_ref": txn_ref}
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"[lemonsqueezy/create] exception: {e}", exc_info=True)
            raise HTTPException(500, f"خطأ LemonSqueezy: {e}")

    # Public webhook — LemonSqueezy POSTs here when payment succeeds
    @router.post("/lemonsqueezy/webhook")
    async def lemon_webhook(request_body: dict):
        """Process LemonSqueezy order_created event → create project + credits."""
        try:
            event = request_body.get("meta", {}).get("event_name", "")
            if event not in ("order_created", "subscription_created"):
                return {"ok": True, "skipped": event}
            attrs = request_body.get("data", {}).get("attributes", {})
            custom = (attrs.get("first_order_item", {}).get("custom_data")
                      or attrs.get("custom_data") or {})
            txn_ref = custom.get("txn_ref")
            if not txn_ref:
                log.warning("[lemon webhook] no txn_ref in custom data")
                return {"ok": True, "skipped": "no_txn_ref"}
            txn = await db.ready_sites_payments.find_one({"txn_ref": txn_ref}, {"_id": 0})
            if not txn:
                log.warning(f"[lemon webhook] txn {txn_ref} not found")
                return {"ok": True, "skipped": "txn_not_found"}
            if txn.get("status") == "completed":
                return {"ok": True, "already": True}
            project_id = await _create_ready_sites_project(
                db, txn["user_id"], txn["category_id"], txn["plan"],
                "lemonsqueezy", txn_ref,
            )
            await db.ready_sites_payments.update_one(
                {"txn_ref": txn_ref},
                {"$set": {"status": "completed", "project_id": project_id,
                          "completed_at": datetime.now(timezone.utc).isoformat()}},
            )
            return {"ok": True, "project_id": project_id}
        except Exception as e:
            log.error(f"[lemon webhook] error: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}

    # Frontend polls this after returning from LemonSqueezy hosted page
    @router.get("/payment-status/{txn_ref}")
    async def payment_status(txn_ref: str, user=Depends(get_current_user)):
        txn = await db.ready_sites_payments.find_one(
            {"txn_ref": txn_ref, "user_id": user["user_id"]}, {"_id": 0},
        )
        if not txn:
            raise HTTPException(404, "غير موجود")
        return {
            "status": txn.get("status"),
            "project_id": txn.get("project_id"),
        }

    app.include_router(router)
    log.info("Ready Sites payment routes registered (PayPal + LemonSqueezy)")
