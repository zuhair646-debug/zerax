"""Stripe subscription billing routes for Zenrex Website Studio gate.

Uses emergentintegrations Stripe SDK. Single fixed package: studio_monthly @ $50 USD.
Subscription is simulated as a one-time $50 payment granting 30 days of studio access.

Security:
- All package amounts defined server-side (never trust frontend amount)
- Success/cancel URLs built from frontend origin_url parameter
- Idempotent: payment_transactions status is only updated once per session
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

# Stripe integration — uses our local shim over the official `stripe` Python
# SDK (so we don't depend on emergentintegrations). The shim exposes the same
# interface the previous integration provided.
try:
    from .stripe_shim import (
        StripeCheckout,
        CheckoutSessionRequest,
    )
    _STRIPE_SDK_AVAILABLE = True
except Exception as _stripe_imp_err:  # pragma: no cover
    StripeCheckout = None  # type: ignore
    CheckoutSessionRequest = None  # type: ignore
    _STRIPE_SDK_AVAILABLE = False
    _STRIPE_SDK_ERROR = str(_stripe_imp_err)

log = logging.getLogger(__name__)

# Fixed server-side packages — Credits-based pricing (1 credit ≈ 500 AI tokens).
# `credits` is the amount added to user balance on successful payment.
PACKAGES: Dict[str, Dict[str, Any]] = {
    # ─── One-time top-up — no expiry on the credits ───────────────────
    "project_pack": {
        "name": "Project Pack",
        "price_usd": 49.00,                # Launch promo price
        "original_price_usd": 79.00,
        "discount_pct": 38,
        "promo_label": "عرض الإطلاق",
        "currency": "usd",
        "duration_days": 30,               # tier label expiry (credits never expire)
        "subscription_type": "tier_upgrade",
        "tier": "starter",
        "credits": 5_000,
    },
    # ─── Monthly subscriptions — credits refill on each renewal ──────
    "tier_starter_monthly": {
        "name": "Starter",
        "price_usd": 19.00,
        "original_price_usd": 29.00,
        "discount_pct": 35,
        "promo_label": "عرض الإطلاق",
        "currency": "usd",
        "duration_days": 30,
        "subscription_type": "tier_upgrade",
        "tier": "starter",
        "credits": 2_000,
    },
    "tier_pro_monthly": {
        "name": "Pro",
        "price_usd": 69.00,
        "original_price_usd": 99.00,
        "discount_pct": 30,
        "promo_label": "عرض الإطلاق",
        "currency": "usd",
        "duration_days": 30,
        "subscription_type": "tier_upgrade",
        "tier": "pro",
        "credits": 8_000,
    },
    "tier_studio_monthly": {
        "name": "Studio",
        "price_usd": 199.00,
        "original_price_usd": 299.00,
        "discount_pct": 33,
        "promo_label": "عرض الإطلاق",
        "currency": "usd",
        "duration_days": 30,
        "subscription_type": "tier_upgrade",
        "tier": "studio",
        "credits": 25_000,
    },
    # ─── Ready Sites — one-off purchases (USD) ─────────────────────────
    "ready_sites_trial": {
        "name": "Ready Sites — Paid Trial (7 days)",
        "price_usd": 9.00,
        "currency": "usd",
        "duration_days": 7,
        "subscription_type": "ready_sites",
        "plan": "trial",
        "credits": 500,
    },
    "ready_sites_purchase": {
        "name": "Ready Sites — Full Ownership",
        "price_usd": 79.00,
        "currency": "usd",
        "duration_days": 365,
        "subscription_type": "ready_sites",
        "plan": "purchase",
        "credits": 5_000,
    },
}


class CheckoutRequestBody(BaseModel):
    package_id: str
    origin_url: str  # from window.location.origin on frontend
    # Optional metadata merged into Stripe session — used by feature-specific
    # webhooks (e.g. ready_sites passes category_id + plan so the project is
    # auto-created after payment).
    extra_metadata: Optional[Dict[str, Any]] = None


def register_routes(app, db, get_current_user):
    router = APIRouter(prefix="/api/billing", tags=["billing"])
    webhook_router = APIRouter(prefix="/api", tags=["billing-webhook"])

    async def _find_ready_sites_project_id(db, session_id):
        """Look up the FreeBuild project created for a ready_sites payment."""
        try:
            proj = await db.freebuild_chat_projects.find_one(
                {"ready_sites_session_id": session_id},
                {"id": 1, "_id": 0},
            )
            return (proj or {}).get("id")
        except Exception:
            return None

    async def _create_ready_sites_project(db, txn, pkg):
        """Idempotently create a Ready Sites FreeBuild project after payment.

        Reads category_id + plan from the transaction metadata (Stripe session
        metadata that was set during /billing/checkout via extra_metadata).
        Skips if a project for this session_id was already created (prevents
        double-fulfillment when both webhook and polling fire).
        """
        import uuid
        meta = txn.get("metadata") or {}
        category_id = meta.get("category_id")
        if not category_id:
            log.warning(f"[ready_sites] No category_id in metadata for txn {txn.get('session_id')}")
            return
        # Idempotency — skip if we already created the project for this session
        existing = await db.freebuild_chat_projects.find_one(
            {"ready_sites_session_id": txn.get("session_id")},
            {"id": 1, "_id": 0},
        )
        if existing:
            log.info(f"[ready_sites] Project already exists for session {txn.get('session_id')}")
            return
        # Inline category labels (kept in sync with modules/ready_sites/QUICK_CATEGORY_LABELS)
        _CAT_LABELS = {
            "restaurants": {"ar": "مطاعم وكافيهات", "icon": "🍽️", "kind": "restaurant"},
            "electronics": {"ar": "إلكترونيات وتقنية", "icon": "📱", "kind": "store"},
            "stationery":  {"ar": "قرطاسيات ومكتبات", "icon": "✏️", "kind": "store"},
            "grocery":     {"ar": "بقالات وسوبرماركت", "icon": "🛒", "kind": "store"},
            "pharmacy":    {"ar": "صيدليات", "icon": "💊", "kind": "store"},
            "fashion":     {"ar": "أزياء وموضة", "icon": "👗", "kind": "store"},
            "beauty":      {"ar": "تجميل وعطور", "icon": "💄", "kind": "store"},
            "flowers":     {"ar": "زهور وهدايا", "icon": "🌸", "kind": "store"},
        }
        cat = _CAT_LABELS.get(category_id) or {"ar": category_id, "icon": "🛍️", "kind": "store"}
        plan = pkg.get("plan", "purchase")
        project_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        trial_until = None
        if plan == "trial":
            trial_until = (datetime.now(timezone.utc) + timedelta(days=pkg.get("duration_days", 7))).isoformat()
        greeting = (
            f"أهلاً وسهلاً! 👋\n\n"
            f"مبروك دفعك واختيارك قالب **{cat['ar']}** {cat['icon']}.\n\n"
            f"عشان أبدأ ببناء موقعك، أحتاج معلومتين فقط:\n\n"
            f"1️⃣ **اسم متجرك** (مثل: مطعم الفجر، صيدلية النور...)\n"
            f"2️⃣ **اللوغو**:\n"
            f"   • ارفعه لو عندك واحد جاهز\n"
            f"   • أو قول لي وصف بسيط وأنا أصمّمه لك\n\n"
            f"بمجرد ما تعطيني المعلومتين، راح أبني الموقع كاملاً في دقائق ✨"
        )
        first_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": greeting,
            "timestamp": now,
        }
        await db.freebuild_chat_projects.insert_one({
            "id": project_id,
            "user_id": txn["user_id"],
            "name": f"{cat['icon']} {cat['ar']}",
            "category_id": category_id,
            "category_name": cat["ar"],
            "category_icon": cat["icon"],
            "category_kind": cat.get("kind"),
            "plan": plan,
            "trial_until": trial_until,
            "source": "ready-sites",
            "ready_sites_session_id": txn.get("session_id"),
            "current_html": "",
            "messages": [first_message],
            "created_at": now,
            "updated_at": now,
        })
        log.info(f"[ready_sites] ✓ Created project {project_id} for user {txn['user_id']} (plan={plan})")

    def _stripe_client(http_request: Request) -> StripeCheckout:
        if not _STRIPE_SDK_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="مزود الدفع غير مهيأ على هذا الخادم — تواصل مع الدعم",
            )
        api_key = os.environ.get("STRIPE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Stripe غير مُهيأ")
        host_url = str(http_request.base_url).rstrip("/")
        webhook_url = f"{host_url}/api/webhook/stripe"
        return StripeCheckout(api_key=api_key, webhook_url=webhook_url)

    async def _get_active_subscription(user_id: str) -> Optional[dict]:
        """Return active studio subscription doc if one exists, else None."""
        now_iso = datetime.now(timezone.utc).isoformat()
        sub = await db.studio_subscriptions.find_one(
            {
                "user_id": user_id,
                "status": "active",
                "expires_at": {"$gt": now_iso},
            },
            {"_id": 0},
        )
        return sub

    # -------------------- SUBSCRIPTION STATUS --------------------
    @router.get("/subscription")
    async def get_my_subscription(current_user: dict = Depends(get_current_user)):
        """Check if the current user has an active studio subscription."""
        user_doc = await db.users.find_one({"id": current_user["user_id"]}, {"_id": 0, "password": 0})
        if not user_doc:
            raise HTTPException(status_code=404, detail="المستخدم غير موجود")

        # Owner / admin bypass
        if user_doc.get("is_owner") or user_doc.get("role") in ("owner", "super_admin", "admin"):
            return {
                "active": True,
                "bypass": True,
                "reason": "owner",
                "expires_at": None,
                "package_id": None,
            }

        sub = await _get_active_subscription(current_user["user_id"])
        if sub:
            return {
                "active": True,
                "bypass": False,
                "expires_at": sub.get("expires_at"),
                "package_id": sub.get("package_id"),
                "started_at": sub.get("started_at"),
            }
        return {"active": False, "bypass": False, "expires_at": None, "package_id": None}

    @router.get("/packages")
    async def list_packages():
        """Publicly list available subscription packages (credits-based)."""
        return {
            "packages": [
                {
                    "id": pid,
                    "name": pkg["name"],
                    "price_usd": pkg["price_usd"],
                    "original_price_usd": pkg.get("original_price_usd"),
                    "discount_pct": pkg.get("discount_pct"),
                    "promo_label": pkg.get("promo_label"),
                    "currency": pkg["currency"],
                    "duration_days": pkg["duration_days"],
                    "subscription_type": pkg.get("subscription_type"),
                    "tier": pkg.get("tier"),
                    "credits": pkg.get("credits", 0),
                }
                for pid, pkg in PACKAGES.items()
            ]
        }

    # -------------------- CREATE CHECKOUT SESSION --------------------
    @router.post("/checkout")
    async def create_checkout(
        body: CheckoutRequestBody,
        http_request: Request,
        current_user: dict = Depends(get_current_user),
    ):
        if body.package_id not in PACKAGES:
            raise HTTPException(status_code=400, detail="الباقة غير موجودة")

        pkg = PACKAGES[body.package_id]
        amount = float(pkg["price_usd"])
        currency = pkg["currency"]

        origin = body.origin_url.rstrip("/")
        success_url = f"{origin}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{origin}/billing/cancel"

        metadata = {
            "user_id": current_user["user_id"],
            "package_id": body.package_id,
            "source": "zenrex_studio_gate",
        }
        # Merge in feature-specific metadata (ready_sites category/plan etc.)
        if body.extra_metadata and isinstance(body.extra_metadata, dict):
            for k, v in body.extra_metadata.items():
                # Stripe metadata values must be strings <500 chars
                if v is None:
                    continue
                metadata[str(k)] = str(v)[:500]

        stripe = _stripe_client(http_request)
        try:
            checkout_req = CheckoutSessionRequest(
                amount=amount,
                currency=currency,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata,
            )
            session = await stripe.create_checkout_session(checkout_req)
        except Exception as e:
            log.error(f"Stripe checkout session error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"فشل إنشاء جلسة الدفع: {e}")

        # Record transaction as initiated (server-side amount only)
        txn = {
            "session_id": session.session_id,
            "user_id": current_user["user_id"],
            "package_id": body.package_id,
            "amount": amount,
            "currency": currency,
            "payment_status": "initiated",
            "status": "open",
            "metadata": metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.payment_transactions.insert_one(txn)

        return {"url": session.url, "session_id": session.session_id}

    # -------------------- POLL CHECKOUT STATUS --------------------
    @router.get("/status/{session_id}")
    async def checkout_status(
        session_id: str,
        http_request: Request,
        current_user: dict = Depends(get_current_user),
    ):
        txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        if not txn:
            raise HTTPException(status_code=404, detail="الجلسة غير موجودة")

        # Ownership check
        if txn.get("user_id") != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="غير مصرح")

        # Poll Stripe for the latest status
        stripe = _stripe_client(http_request)
        try:
            status_resp = await stripe.get_checkout_status(session_id)
        except Exception as e:
            log.error(f"Stripe status poll error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"فشل التحقق من الدفع: {e}")

        new_payment_status = status_resp.payment_status
        new_status = status_resp.status

        # Only fulfil once (idempotent)
        already_paid = txn.get("payment_status") == "paid"

        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "payment_status": new_payment_status,
                    "status": new_status,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

        if new_payment_status == "paid" and not already_paid:
            pkg_id = txn.get("package_id", "tier_studio_monthly")
            pkg = PACKAGES.get(pkg_id, PACKAGES["tier_studio_monthly"])
            started_at = datetime.now(timezone.utc)
            expires_at = started_at + timedelta(days=pkg["duration_days"])

            sub_doc = {
                "user_id": txn["user_id"],
                "package_id": pkg_id,
                "status": "active",
                "started_at": started_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "session_id": session_id,
                "amount": txn.get("amount"),
                "currency": txn.get("currency"),
                "created_at": started_at.isoformat(),
            }
            await db.studio_subscriptions.insert_one(sub_doc)
            log.info(f"Activated studio subscription for user {txn['user_id']} until {expires_at}")

            # ── Tier upgrade fulfillment (credits-based) ──
            if pkg.get("subscription_type") == "tier_upgrade":
                credits_to_add = int(pkg.get("credits") or 0)
                await db.users.update_one(
                    {"id": txn["user_id"]},
                    {
                        "$set": {
                            "storage_tier": pkg["tier"],
                            "tier_expires_at": expires_at.isoformat(),
                        },
                        "$inc": {"credits": credits_to_add},
                    },
                )
                log.info(f"Added {credits_to_add} credits to user {txn['user_id']} (tier={pkg['tier']})")

            # ── Ready Sites fulfillment (one-off, creates a project + credits) ──
            elif pkg.get("subscription_type") == "ready_sites":
                credits_to_add = int(pkg.get("credits") or 0)
                if credits_to_add:
                    await db.users.update_one(
                        {"id": txn["user_id"]},
                        {"$inc": {"credits": credits_to_add}},
                    )
                try:
                    await _create_ready_sites_project(db, txn, pkg)
                except Exception as _rs_err:
                    log.warning(f"Failed to auto-create ready_sites project: {_rs_err}")

        return {
            "session_id": session_id,
            "status": new_status,
            "payment_status": new_payment_status,
            "amount_total": status_resp.amount_total,
            "currency": status_resp.currency,
            "fulfilled": new_payment_status == "paid",
            "package_id": txn.get("package_id"),
            "project_id": await _find_ready_sites_project_id(db, session_id),
        }

    # -------------------- WEBHOOK --------------------
    @webhook_router.post("/webhook/stripe")
    async def stripe_webhook(request: Request):
        body = await request.body()
        signature = request.headers.get("Stripe-Signature", "")

        api_key = os.environ.get("STRIPE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Stripe غير مُهيأ")
        host_url = str(request.base_url).rstrip("/")
        webhook_url = f"{host_url}/api/webhook/stripe"
        stripe = StripeCheckout(api_key=api_key, webhook_url=webhook_url)

        try:
            event = await stripe.handle_webhook(body, signature)
        except Exception as e:
            log.error(f"Stripe webhook error: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail="Invalid webhook")

        session_id = event.session_id
        if not session_id:
            return {"received": True}

        txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        if not txn:
            return {"received": True, "note": "unknown session"}

        already_paid = txn.get("payment_status") == "paid"

        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "payment_status": event.payment_status,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "last_webhook_event": event.event_type,
                }
            },
        )

        if event.payment_status == "paid" and not already_paid:
            pkg_id = txn.get("package_id", "tier_studio_monthly")
            pkg = PACKAGES.get(pkg_id, PACKAGES["tier_studio_monthly"])
            started_at = datetime.now(timezone.utc)
            expires_at = started_at + timedelta(days=pkg["duration_days"])
            await db.studio_subscriptions.insert_one(
                {
                    "user_id": txn["user_id"],
                    "package_id": pkg_id,
                    "status": "active",
                    "started_at": started_at.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "session_id": session_id,
                    "amount": txn.get("amount"),
                    "currency": txn.get("currency"),
                    "source": "webhook",
                    "created_at": started_at.isoformat(),
                }
            )
            log.info(f"[webhook] Activated studio subscription for user {txn['user_id']}")

            # ── Tier upgrade fulfillment (credits-based) ──
            if pkg.get("subscription_type") == "tier_upgrade":
                credits_to_add = int(pkg.get("credits") or 0)
                await db.users.update_one(
                    {"id": txn["user_id"]},
                    {
                        "$set": {
                            "storage_tier": pkg["tier"],
                            "tier_expires_at": expires_at.isoformat(),
                        },
                        "$inc": {"credits": credits_to_add},
                    },
                )
                log.info(f"[webhook] Added {credits_to_add} credits to user {txn['user_id']} (tier={pkg['tier']})")

            # ── Ready Sites fulfillment (one-off, creates project + credits) ──
            elif pkg.get("subscription_type") == "ready_sites":
                credits_to_add = int(pkg.get("credits") or 0)
                if credits_to_add:
                    await db.users.update_one(
                        {"id": txn["user_id"]},
                        {"$inc": {"credits": credits_to_add}},
                    )
                try:
                    await _create_ready_sites_project(db, txn, pkg)
                except Exception as _rs_err:
                    log.warning(f"[webhook] Failed to auto-create ready_sites project: {_rs_err}")

            # 🆕 Affiliate commission hook (best-effort, never breaks payment)
            try:
                from modules.affiliate.routes import record_commission
                await record_commission(
                    db,
                    referred_user_id=txn["user_id"],
                    txn_session_id=session_id,
                    amount=float(txn.get("amount") or 0),
                    currency=str(txn.get("currency") or "usd"),
                )
            except Exception as _afe:
                log.warning(f"affiliate commission hook failed: {_afe}")

        return {"received": True}

    app.include_router(router)
    app.include_router(webhook_router)
    log.info("Billing module registered (Stripe)")
