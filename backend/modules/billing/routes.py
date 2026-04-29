"""Stripe subscription billing routes for Zitex Website Studio gate.

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

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
)

log = logging.getLogger(__name__)

# Fixed server-side packages (price_usd is authoritative)
PACKAGES: Dict[str, Dict[str, Any]] = {
    "studio_monthly": {
        "name": "اشتراك استوديو المواقع - شهري",
        "price_usd": 50.00,
        "currency": "usd",
        "duration_days": 30,
        "subscription_type": "website_studio",
    },
}


class CheckoutRequestBody(BaseModel):
    package_id: str
    origin_url: str  # from window.location.origin on frontend


def register_routes(app, db, get_current_user):
    router = APIRouter(prefix="/api/billing", tags=["billing"])
    webhook_router = APIRouter(prefix="/api", tags=["billing-webhook"])

    def _stripe_client(http_request: Request) -> StripeCheckout:
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
        """Publicly list available subscription packages."""
        return {
            "packages": [
                {
                    "id": pid,
                    "name": pkg["name"],
                    "price_usd": pkg["price_usd"],
                    "currency": pkg["currency"],
                    "duration_days": pkg["duration_days"],
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
            "source": "zitex_studio_gate",
        }

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
            pkg_id = txn.get("package_id", "studio_monthly")
            pkg = PACKAGES.get(pkg_id, PACKAGES["studio_monthly"])
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

        return {
            "session_id": session_id,
            "status": new_status,
            "payment_status": new_payment_status,
            "amount_total": status_resp.amount_total,
            "currency": status_resp.currency,
            "fulfilled": new_payment_status == "paid",
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
            pkg_id = txn.get("package_id", "studio_monthly")
            pkg = PACKAGES.get(pkg_id, PACKAGES["studio_monthly"])
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
