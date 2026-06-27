"""
PayPal Subscriptions API — true recurring billing for Zenrex storage tiers.

Why a separate module? `paypalrestsdk` is the legacy v1 SDK that doesn't
expose the new `/v1/billing/plans` + `/v1/billing/subscriptions` endpoints
cleanly. We call them directly via httpx so we get full control over the
recurring lifecycle (creation, cancellation, webhooks).

Reference: https://developer.paypal.com/docs/api/subscriptions/v1/

Lifecycle (fully automated — zero user intervention):
  1. User clicks "اشترك" on a tier in /billing/storage
  2. POST /api/storage/subscribe → we ensure a PayPal Plan exists for the
     tier, then create a Subscription → return PayPal `approval_url`
  3. User approves on PayPal → PayPal redirects them back
  4. PayPal webhook `BILLING.SUBSCRIPTION.ACTIVATED` → we mark active
  5. PayPal auto-charges on day-30 → `PAYMENT.SALE.COMPLETED` → we extend
  6. Failed charge → `PAYMENT.SALE.DENIED` → past_due (grace) → archived
  7. User cancels (or PayPal cancels): `BILLING.SUBSCRIPTION.CANCELLED`
     → we keep access till current_period_end, then archive
"""
from __future__ import annotations

import os
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

log = logging.getLogger(__name__)


def _pp_base_url() -> str:
    mode = os.environ.get("PAYPAL_MODE", "live").lower()
    return "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"


async def _pp_token() -> str:
    """Fetch an OAuth2 access token (~9 hours valid; we fetch per-request)."""
    cid = os.environ.get("PAYPAL_CLIENT_ID")
    sec = os.environ.get("PAYPAL_SECRET")
    if not (cid and sec):
        raise HTTPException(503, "PayPal غير مُهيأ")
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(
            f"{_pp_base_url()}/v1/oauth2/token",
            auth=(cid, sec),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
        )
    if r.status_code >= 400:
        log.error(f"[paypal-subs] token error {r.status_code}: {r.text[:200]}")
        raise HTTPException(500, "فشل المصادقة مع PayPal")
    return r.json()["access_token"]


async def _ensure_product(db, token: str) -> str:
    """Idempotently create the master PayPal product for storage subscriptions."""
    doc = await db.paypal_products.find_one({"key": "zenrex_storage"}, {"_id": 0})
    if doc and doc.get("paypal_product_id"):
        return doc["paypal_product_id"]
    payload = {
        "name": "Zenrex Storage",
        "description": "اشتراك تخزين شهري متجدد على منصة Zenrex",
        "type": "SERVICE",
        "category": "SOFTWARE",
    }
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(
            f"{_pp_base_url()}/v1/catalogs/products",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "PayPal-Request-Id": f"zenrex-prod-{uuid.uuid4()}",
            },
            json=payload,
        )
    if r.status_code >= 400:
        log.error(f"[paypal-subs] product error {r.status_code}: {r.text[:300]}")
        raise HTTPException(500, "فشل إنشاء منتج PayPal")
    pid = r.json()["id"]
    await db.paypal_products.update_one(
        {"key": "zenrex_storage"},
        {"$set": {"key": "zenrex_storage", "paypal_product_id": pid}},
        upsert=True,
    )
    return pid


async def _ensure_billing_plan(db, token: str, product_id: str, plan_id: str, plan: dict) -> str:
    """Idempotently create a PayPal Billing Plan for the given storage tier."""
    doc = await db.paypal_plans.find_one({"plan_id": plan_id}, {"_id": 0})
    if doc and doc.get("paypal_plan_id"):
        return doc["paypal_plan_id"]
    payload = {
        "product_id": product_id,
        "name": f"Zenrex Storage — {plan['label_ar']} ({plan['quota_mb']}MB)",
        "description": f"اشتراك شهري {plan['quota_mb']} ميجا تخزين — ${plan['price_usd']}/شهر",
        "status": "ACTIVE",
        "billing_cycles": [{
            "frequency": {"interval_unit": "MONTH", "interval_count": 1},
            "tenure_type": "REGULAR",
            "sequence": 1,
            "total_cycles": 0,  # 0 = infinite
            "pricing_scheme": {
                "fixed_price": {"value": f"{plan['price_usd']:.2f}", "currency_code": "USD"},
            },
        }],
        "payment_preferences": {
            "auto_bill_outstanding": True,
            "setup_fee": {"value": "0", "currency_code": "USD"},
            "setup_fee_failure_action": "CONTINUE",
            "payment_failure_threshold": 3,
        },
    }
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.post(
            f"{_pp_base_url()}/v1/billing/plans",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "PayPal-Request-Id": f"zenrex-plan-{plan_id}-{uuid.uuid4()}",
            },
            json=payload,
        )
    if r.status_code >= 400:
        log.error(f"[paypal-subs] plan {plan_id} error {r.status_code}: {r.text[:300]}")
        raise HTTPException(500, f"فشل إنشاء خطة PayPal: {plan_id}")
    pp_plan_id = r.json()["id"]
    await db.paypal_plans.update_one(
        {"plan_id": plan_id},
        {"$set": {
            "plan_id": plan_id,
            "paypal_plan_id": pp_plan_id,
            "price_usd": plan["price_usd"],
            "quota_mb": plan["quota_mb"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    return pp_plan_id


class SubscribeIn(BaseModel):
    plan_id: str


def register_paypal_subscriptions(app, db, get_current_user, STORAGE_PLANS, GRACE_DAYS):
    router = APIRouter(prefix="/api/storage", tags=["storage-subscriptions"])

    # ─── POST /api/storage/subscribe ────────────────────────────────────
    # Replaces the legacy one-time /checkout with a TRUE recurring sub.
    @router.post("/subscribe")
    async def subscribe(body: SubscribeIn, user=Depends(get_current_user)):
        plan = STORAGE_PLANS.get(body.plan_id)
        if not plan:
            raise HTTPException(400, "باقة غير صحيحة")
        token = await _pp_token()
        product_id = await _ensure_product(db, token)
        pp_plan_id = await _ensure_billing_plan(db, token, product_id, body.plan_id, plan)

        frontend = os.environ.get("FRONTEND_URL", "https://zenrex.ai").rstrip("/")
        u_doc = await db.users.find_one({"id": user["user_id"]}, {"_id": 0, "email": 1}) or {}
        u_email = u_doc.get("email") or "customer@zenrex.ai"

        payload = {
            "plan_id": pp_plan_id,
            "custom_id": user["user_id"],
            "application_context": {
                "brand_name": "Zenrex",
                "locale": "ar-SA",
                "shipping_preference": "NO_SHIPPING",
                "user_action": "SUBSCRIBE_NOW",
                "payment_method": {
                    "payer_selected": "PAYPAL",
                    "payee_preferred": "IMMEDIATE_PAYMENT_REQUIRED",
                },
                "return_url": f"{frontend}/billing/storage?subscribed=1",
                "cancel_url": f"{frontend}/billing/storage?cancelled=1",
            },
            "subscriber": {"email_address": u_email},
        }
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.post(
                f"{_pp_base_url()}/v1/billing/subscriptions",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "PayPal-Request-Id": f"sub-{user['user_id']}-{uuid.uuid4()}",
                    "Prefer": "return=representation",
                },
                json=payload,
            )
        if r.status_code >= 400:
            log.error(f"[paypal-subs] create error {r.status_code}: {r.text[:400]}")
            raise HTTPException(500, f"فشل إنشاء الاشتراك في PayPal ({r.status_code})")
        data = r.json()
        approval = next((l["href"] for l in data.get("links", []) if l["rel"] == "approve"), None)
        if not approval:
            raise HTTPException(500, "PayPal لم يرجع رابط الموافقة")

        # Save the pending subscription so we can match it back on webhook
        await db.storage_subscriptions.update_one(
            {"user_id": user["user_id"]},
            {"$set": {
                "user_id": user["user_id"],
                "plan_id": body.plan_id,
                "status": "pending_approval",
                "paypal_subscription_id": data["id"],
                "auto_renew": True,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
        return {"approval_url": approval, "subscription_id": data["id"], "plan_id": body.plan_id}

    # ─── POST /api/storage/cancel-subscription ─────────────────────────
    @router.post("/cancel-subscription")
    async def cancel_subscription(user=Depends(get_current_user)):
        sub = await db.storage_subscriptions.find_one(
            {"user_id": user["user_id"]}, {"_id": 0},
        )
        if not sub:
            raise HTTPException(400, "لا يوجد اشتراك للإلغاء")
        if sub.get("status") in ("cancelled", "archived"):
            return {"ok": True, "already": True}

        pp_sub_id = sub.get("paypal_subscription_id")
        now_iso = datetime.now(timezone.utc).isoformat()

        # ── Pending approval → user never finished the PayPal flow,
        #    no recurring payment was set up yet. Revert to trial state.
        if sub.get("status") == "pending_approval":
            await db.storage_subscriptions.update_one(
                {"user_id": user["user_id"]},
                {"$set": {
                    "plan_id": "trial",
                    "status": "trial",
                    "auto_renew": False,
                    "paypal_subscription_id": None,
                    "current_period_end": None,
                    "cancelled_at": now_iso,
                    "updated_at": now_iso,
                }},
            )
            return {"ok": True, "cancelled": True, "was_pending": True}

        # ── Active / past_due → ask PayPal to stop charging.
        if pp_sub_id:
            try:
                token = await _pp_token()
                async with httpx.AsyncClient(timeout=15.0) as c:
                    r = await c.post(
                        f"{_pp_base_url()}/v1/billing/subscriptions/{pp_sub_id}/cancel",
                        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                        json={"reason": "Cancelled by user via Zenrex"},
                    )
                # PayPal returns 204 No Content on success. 422 = already cancelled.
                if r.status_code not in (200, 204, 422):
                    log.error(f"[paypal-subs] cancel error {r.status_code}: {r.text[:300]}")
                    # Don't block local cancellation — user demanded auto-stop
                    # of withdrawals. Mark locally anyway so /subscription
                    # reflects truth.
            except Exception as e:
                log.warning(f"[paypal-subs] cancel exception: {e}")

        # Mark `auto_renew=false` so the auto-evaluator eventually archives
        # the account after `current_period_end` passes (giving the user the
        # paid period they already paid for). We do NOT set status='cancelled'
        # immediately — the user demanded "keep access for the paid month".
        await db.storage_subscriptions.update_one(
            {"user_id": user["user_id"]},
            {"$set": {
                "auto_renew": False,
                "cancelled_at": now_iso,
                "updated_at": now_iso,
            }},
        )
        return {
            "ok": True,
            "cancelled": True,
            "access_until": sub.get("current_period_end"),
        }

    # ─── POST /api/storage/paypal-webhook ──────────────────────────────
    # PayPal calls this URL on subscription events. Configure in dashboard:
    #   Events: BILLING.SUBSCRIPTION.ACTIVATED / .CANCELLED / .SUSPENDED /
    #           .EXPIRED, PAYMENT.SALE.COMPLETED, PAYMENT.SALE.DENIED
    @router.post("/paypal-webhook")
    async def paypal_webhook(request: Request):
        try:
            body = await request.json()
        except Exception:
            return {"ok": False, "error": "invalid_json"}
        event_type = body.get("event_type", "")
        resource = body.get("resource", {}) or {}
        log.info(f"[paypal-webhook] event={event_type}")

        # Subscription lifecycle
        if event_type in (
            "BILLING.SUBSCRIPTION.ACTIVATED", "BILLING.SUBSCRIPTION.CREATED",
            "BILLING.SUBSCRIPTION.UPDATED", "BILLING.SUBSCRIPTION.RE-ACTIVATED",
        ):
            sub_id = resource.get("id")
            user_id = resource.get("custom_id") or _extract_user_from_sub(resource)
            if user_id and sub_id:
                # Read next billing time to compute current_period_end
                next_billing = (resource.get("billing_info") or {}).get("next_billing_time")
                if not next_billing:
                    next_billing = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                # Resolve plan
                pp_plan_id = resource.get("plan_id")
                local_plan = await db.paypal_plans.find_one(
                    {"paypal_plan_id": pp_plan_id}, {"_id": 0, "plan_id": 1},
                ) or {}
                await db.storage_subscriptions.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "user_id": user_id,
                        "plan_id": local_plan.get("plan_id") or "starter10",
                        "status": "active",
                        "paypal_subscription_id": sub_id,
                        "current_period_end": next_billing,
                        "auto_renew": True,
                        "grace_started_at": None,
                        "archived_at": None,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                    upsert=True,
                )
                # Lift any archived flag
                await db.users.update_one(
                    {"id": user_id},
                    {"$set": {"storage_archived": False}},
                )
                log.info(f"[paypal-webhook] subscription active for {user_id}")
            return {"ok": True}

        # Successful recurring payment → extend period
        if event_type == "PAYMENT.SALE.COMPLETED":
            sub_id = (resource.get("billing_agreement_id")
                      or (resource.get("supplementary_data", {}).get("related_ids", {}).get("subscription_id")))
            if sub_id:
                sub_doc = await db.storage_subscriptions.find_one(
                    {"paypal_subscription_id": sub_id}, {"_id": 0, "user_id": 1},
                )
                if sub_doc:
                    new_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                    await db.storage_subscriptions.update_one(
                        {"user_id": sub_doc["user_id"]},
                        {"$set": {
                            "status": "active",
                            "current_period_end": new_end,
                            "grace_started_at": None,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }},
                    )
                    await db.users.update_one(
                        {"id": sub_doc["user_id"]},
                        {"$set": {"storage_archived": False}},
                    )
                    log.info(f"[paypal-webhook] renewed for {sub_doc['user_id']}")
            return {"ok": True}

        # Failed charge → start grace period
        if event_type in ("PAYMENT.SALE.DENIED", "BILLING.SUBSCRIPTION.PAYMENT.FAILED"):
            sub_id = (resource.get("billing_agreement_id")
                      or (resource.get("id") if "BILLING" in event_type else None))
            if sub_id:
                sub_doc = await db.storage_subscriptions.find_one(
                    {"paypal_subscription_id": sub_id}, {"_id": 0, "user_id": 1},
                )
                if sub_doc:
                    await db.storage_subscriptions.update_one(
                        {"user_id": sub_doc["user_id"]},
                        {"$set": {
                            "status": "past_due",
                            "grace_started_at": datetime.now(timezone.utc).isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }},
                    )
                    log.info(f"[paypal-webhook] past_due for {sub_doc['user_id']}")
            return {"ok": True}

        # Cancelled / suspended → keep access till period_end, then evaluator archives
        if event_type in ("BILLING.SUBSCRIPTION.CANCELLED", "BILLING.SUBSCRIPTION.SUSPENDED", "BILLING.SUBSCRIPTION.EXPIRED"):
            sub_id = resource.get("id")
            user_id = resource.get("custom_id") or _extract_user_from_sub(resource)
            if not user_id and sub_id:
                sub_doc = await db.storage_subscriptions.find_one(
                    {"paypal_subscription_id": sub_id}, {"_id": 0, "user_id": 1},
                ) or {}
                user_id = sub_doc.get("user_id")
            if user_id:
                await db.storage_subscriptions.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "auto_renew": False,
                        "cancelled_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
                log.info(f"[paypal-webhook] cancelled for {user_id}")
            return {"ok": True}

        # Unknown event — log + ack
        return {"ok": True, "skipped": event_type}

    app.include_router(router)
    log.info("PayPal Subscriptions module registered (/api/storage/subscribe + cancel + webhook)")


def _extract_user_from_sub(resource: dict) -> Optional[str]:
    """Best-effort user_id resolution from a subscription resource."""
    if resource.get("custom_id"):
        return resource["custom_id"]
    return None
