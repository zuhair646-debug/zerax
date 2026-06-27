"""
Zenrex Storage Billing — Unified storage subscription system.

Separates storage quotas from AI credits. Users subscribe to a monthly plan
that gives them MB/GB of storage across ALL surfaces (websites, apps, games,
images, videos). If the subscription lapses, files enter a 10-day grace
period (emails sent on days 1/5/8). After grace, files are ARCHIVED
(invisible to user but kept on our server) for 6 months. User can recover
their files by paying a tiered recovery fee + renewing subscription.

Pricing (linear, monthly USD via PayPal):
  free  -> $0    10 MB    (default)
  s50   -> $5    50 MB
  s100  -> $10   100 MB   (most popular)
  s150  -> $15   150 MB
  s200  -> $20   200 MB
  s300  -> $30   300 MB
  s500  -> $50   500 MB
  s1000 -> $100  1 GB

Recovery (one-time, PayPal):
  small  -> $3   <50 MB
  medium -> $5   <100 MB
  large  -> $10  <250 MB
  xl     -> $25  <1 GB

Note: Lemon Squeezy fully removed in Feb 2026 — PayPal is the sole processor.
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
# Linear pricing per owner directive (Feb 2026 v2):
#   • Starter: 10MB at $3/mo (no free tier).
#   • Then +$5 per +50MB up to 1 GB.
#   • All plans monthly; PayPal-only.
#   • Recovery fee = DOUBLE the plan price (per-plan dynamic).
STORAGE_PLANS = {
    "starter10": {
        "id": "starter10",
        "label_ar": "بداية",
        "label_en": "Starter",
        "price_usd": 3,
        "quota_mb": 10,
        "monthly": True,
        "description_ar": "بداية المشوار — 10 ميجا تخزين",
        "highlight": False,
    },
    "s50": {
        "id": "s50",
        "label_ar": "50 ميجا",
        "label_en": "50 MB",
        "price_usd": 5,
        "quota_mb": 50,
        "monthly": True,
        "description_ar": "بداية المشروع — 50 ميجا تخزين",
        "highlight": False,
    },
    "s100": {
        "id": "s100",
        "label_ar": "100 ميجا",
        "label_en": "100 MB",
        "price_usd": 10,
        "quota_mb": 100,
        "monthly": True,
        "description_ar": "الأكثر شعبية — 100 ميجا تخزين",
        "highlight": True,
    },
    "s150": {
        "id": "s150",
        "label_ar": "150 ميجا",
        "label_en": "150 MB",
        "price_usd": 15,
        "quota_mb": 150,
        "monthly": True,
        "description_ar": "للمشاريع المتنامية — 150 ميجا تخزين",
        "highlight": False,
    },
    "s200": {
        "id": "s200",
        "label_ar": "200 ميجا",
        "label_en": "200 MB",
        "price_usd": 20,
        "quota_mb": 200,
        "monthly": True,
        "description_ar": "للمحتوى الثقيل — 200 ميجا تخزين",
        "highlight": False,
    },
    "s300": {
        "id": "s300",
        "label_ar": "300 ميجا",
        "label_en": "300 MB",
        "price_usd": 30,
        "quota_mb": 300,
        "monthly": True,
        "description_ar": "للمشاريع المتقدمة — 300 ميجا تخزين",
        "highlight": False,
    },
    "s500": {
        "id": "s500",
        "label_ar": "500 ميجا",
        "label_en": "500 MB",
        "price_usd": 50,
        "quota_mb": 500,
        "monthly": True,
        "description_ar": "للاستوديوهات — 500 ميجا تخزين",
        "highlight": False,
    },
    "s1000": {
        "id": "s1000",
        "label_ar": "1 جيجا",
        "label_en": "1 GB",
        "price_usd": 100,
        "quota_mb": 1024,
        "monthly": True,
        "description_ar": "للمشاريع الكبيرة — 1 جيجا تخزين",
        "highlight": False,
    },
}

# ─── Recovery fee tiers (one-time, PayPal) ──────────────────────────────
# Per-plan dynamic recovery: 2× the plan's monthly price.
# Computed via `recovery_fee_for_plan(plan_id)`.
RECOVERY_TIERS = {}


def recovery_fee_for_plan(plan_id: str) -> dict:
    """Calculate the per-plan recovery fee (2× monthly price).

    Triggered when the user is late paying / cancelled and wants to unlock
    their archived files. Doubles the plan price as a penalty.
    """
    plan = STORAGE_PLANS.get(plan_id) or STORAGE_PLANS["starter10"]
    fee = round(plan["price_usd"] * 2, 2)
    return {
        "id": f"recovery_{plan_id}",
        "label_ar": f"استرداد {plan['label_ar']}",
        "plan_id": plan_id,
        "plan_price_usd": plan["price_usd"],
        "price_usd": fee,
        "quota_mb": plan["quota_mb"],
    }


# ─── Grace period config ────────────────────────────────────────────────
GRACE_DAYS = 10
ARCHIVE_RETENTION_DAYS = 180   # 6 months — after this we may purge


def pick_recovery_tier(used_mb: float = 0, plan_id: str = "starter10") -> dict:
    """Return the recovery tier for the user's CURRENT plan (2× plan price).

    `used_mb` kept for backwards-compat only — recovery is now per-plan,
    not per-size.
    """
    return recovery_fee_for_plan(plan_id)


class CheckoutIn(BaseModel):
    plan_id: str


class RecoveryCheckoutIn(BaseModel):
    # tier auto-picked from user's archived size; this just confirms intent
    confirm: bool = True


class StorageCaptureIn(BaseModel):
    txn_ref: str
    order_id: Optional[str] = None
    payer_id: Optional[str] = None


async def _get_user_storage_subscription(db, user_id: str) -> dict:
    """Fetch (or default) the user's storage subscription record."""
    sub = await db.storage_subscriptions.find_one({"user_id": user_id}, {"_id": 0})
    if not sub:
        # New user — defaults to "trial": 10 MB free for evaluation,
        # must subscribe to keep using. No legacy 'free' plan anymore.
        return {
            "user_id": user_id,
            "plan_id": "trial",                # synthetic — not in STORAGE_PLANS
            "status": "trial",                 # trial | active | past_due | archived | cancelled
            "paypal_subscription_id": None,
            "current_period_end": None,
            "grace_started_at": None,
            "archived_at": None,
        }
    return sub


async def _evaluate_subscription_state(db, user_id: str) -> dict:
    """Lazily refresh the user's subscription state on every read.

    Implements the auto-suspension policy (Feb 2026):
      • active   → if current_period_end passed → past_due (grace starts)
      • past_due → if >GRACE_DAYS passed → archived (lock access)
      • archived → stays archived until /recovery/checkout is paid
      • trial    → if account is older than 7 days → archived (block)

    Returns the (possibly updated) subscription doc.
    """
    sub = await _get_user_storage_subscription(db, user_id)
    now = datetime.now(timezone.utc)
    status = sub.get("status", "trial")
    plan_id = sub.get("plan_id", "trial")

    updates = {}

    # 1) active → past_due if period ended
    if status == "active":
        period_end_iso = sub.get("current_period_end")
        if period_end_iso:
            try:
                period_end = datetime.fromisoformat(period_end_iso)
                if period_end < now:
                    updates["status"] = "past_due"
                    updates["grace_started_at"] = now.isoformat()
                    status = "past_due"
            except Exception:
                pass

    # 2) past_due → archived if grace expired
    if status == "past_due":
        grace_iso = sub.get("grace_started_at")
        if grace_iso:
            try:
                grace_start = datetime.fromisoformat(grace_iso)
                if (now - grace_start).days >= GRACE_DAYS:
                    updates["status"] = "archived"
                    updates["archived_at"] = now.isoformat()
                    status = "archived"
            except Exception:
                pass

    # 3) trial (new users with no plan) — auto-expire after 7 days
    if status == "trial" and plan_id == "trial":
        # First touch — store the trial start
        if not sub.get("trial_started_at"):
            updates["trial_started_at"] = now.isoformat()
            updates["user_id"] = user_id
            updates["plan_id"] = "trial"
            updates["status"] = "trial"
        else:
            try:
                trial_start = datetime.fromisoformat(sub["trial_started_at"])
                if (now - trial_start).days >= 7:
                    updates["status"] = "archived"
                    updates["archived_at"] = now.isoformat()
                    status = "archived"
            except Exception:
                pass

    if updates:
        await db.storage_subscriptions.update_one(
            {"user_id": user_id},
            {"$set": {**updates, "updated_at": now.isoformat()}},
            upsert=True,
        )
        # Lock/unlock the user's archived flag synchronously
        if updates.get("status") == "archived":
            await db.users.update_one({"id": user_id}, {"$set": {"storage_archived": True}})
        sub = {**sub, **updates}

    return sub


def _quota_for_subscription(sub: dict) -> dict:
    """Resolve effective quota + lock state from a subscription doc.

    Returns: {plan_id, quota_mb, label_ar, status, locked, locked_reason, ...}
    """
    status = sub.get("status", "trial")
    plan_id = sub.get("plan_id", "trial")

    # Trial: 2 MB free for evaluation — small on purpose so users hit the
    # paywall fast and must subscribe to keep going.
    if plan_id == "trial" or plan_id == "free":
        quota_mb = 2
        label_ar = "تجريبية"
        price_usd = 0
    else:
        plan = STORAGE_PLANS.get(plan_id) or STORAGE_PLANS["starter10"]
        quota_mb = plan["quota_mb"]
        label_ar = plan["label_ar"]
        price_usd = plan["price_usd"]

    locked = status in ("archived", "cancelled")
    locked_reason = None
    if status == "archived":
        locked_reason = "انتهت فترة السماح — ادفع رسم الاسترداد لفك القفل"
    elif status == "cancelled":
        locked_reason = "اشتراكك ملغى — اشترك من جديد للوصول لملفاتك"

    return {
        "plan_id": plan_id,
        "label_ar": label_ar,
        "price_usd": price_usd,
        "quota_mb": quota_mb,
        "status": status,
        "locked": locked,
        "locked_reason": locked_reason,
    }


async def _calc_usage_mb(db, user_id: str) -> float:
    """Compute the user's storage footprint in MB across every surface.

    Mirrors the logic in freebuild_chat._user_total_bytes (kept in sync).
    """
    total = 0
    cur = db.freebuild_projects.find(
        {"user_id": user_id, "status": {"$ne": "deleted"}},
        {"current_html": 1, "messages": 1, "approved_assets": 1},
    )
    projects = await cur.to_list(length=1000)
    for p in projects:
        total += len((p.get("current_html") or "").encode("utf-8", errors="ignore"))
        for m in (p.get("messages") or []):
            total += len((m.get("content") or "").encode("utf-8", errors="ignore"))
        for a in (p.get("approved_assets") or []):
            total += len((a.get("prompt") or "").encode("utf-8", errors="ignore"))
            total += len((a.get("image_url") or "").encode("utf-8", errors="ignore"))
    try:
        assets = await db.freebuild_assets.find(
            {"user_id": user_id}, {"size_bytes": 1, "file_size": 1}
        ).to_list(length=5000)
        for a in assets:
            total += int(a.get("size_bytes") or a.get("file_size") or 0)
    except Exception:
        pass
    return total / (1024 * 1024)


def register_storage_billing(app, db, get_current_user):
    router = APIRouter(prefix="/api/storage", tags=["storage-billing"])

    # ─── GET /api/storage/plans ─────────────────────────────────────────
    @router.get("/plans")
    async def list_plans():
        # PayPal is the sole processor — all paid plans are available
        # as long as PAYPAL_CLIENT_ID/SECRET are configured.
        pp_ok = bool(os.environ.get("PAYPAL_CLIENT_ID") and os.environ.get("PAYPAL_SECRET"))
        out = []
        for plan in STORAGE_PLANS.values():
            available = pp_ok  # No free plan exists anymore — all require PayPal
            recovery = recovery_fee_for_plan(plan["id"])
            out.append({
                **plan,
                "available": available,
                "quota_gb": round(plan["quota_mb"] / 1024, 2),
                "recovery_price_usd": recovery["price_usd"],
            })
        return {"plans": out, "recovery": [], "grace_days": GRACE_DAYS}

    # ─── GET /api/storage/subscription ──────────────────────────────────
    @router.get("/subscription")
    async def get_subscription(user=Depends(get_current_user)):
        # Lazy state evaluation — auto-suspends if subscription expired
        sub = await _evaluate_subscription_state(db, user["user_id"])
        info = _quota_for_subscription(sub)
        # Compute grace countdown if past_due
        grace_days_left = None
        if sub.get("status") == "past_due" and sub.get("grace_started_at"):
            try:
                started = datetime.fromisoformat(sub["grace_started_at"])
                elapsed = (datetime.now(timezone.utc) - started).days
                grace_days_left = max(0, GRACE_DAYS - elapsed)
            except Exception:
                pass
        # Trial countdown
        trial_days_left = None
        if info["plan_id"] == "trial" and sub.get("trial_started_at"):
            try:
                started = datetime.fromisoformat(sub["trial_started_at"])
                elapsed = (datetime.now(timezone.utc) - started).days
                trial_days_left = max(0, 7 - elapsed)
            except Exception:
                pass
        # Recovery fee — for the user's "best fit" plan when archived
        recovery_plan_id = info["plan_id"] if info["plan_id"] in STORAGE_PLANS else "starter10"
        recovery = recovery_fee_for_plan(recovery_plan_id)
        return {
            "plan_id": info["plan_id"],
            "plan_label_ar": info["label_ar"],
            "plan_quota_mb": info["quota_mb"],
            "plan_quota_gb": round(info["quota_mb"] / 1024, 2),
            "plan_price_usd": info["price_usd"],
            "status": info["status"],
            "locked": info["locked"],
            "locked_reason": info["locked_reason"],
            "current_period_end": sub.get("current_period_end"),
            "grace_started_at": sub.get("grace_started_at"),
            "grace_days_left": grace_days_left,
            "trial_started_at": sub.get("trial_started_at"),
            "trial_days_left": trial_days_left,
            "archived_at": sub.get("archived_at"),
            "recovery_price_usd": recovery["price_usd"],
            "can_purchase": True,
        }

    # ─── GET /api/storage/check ─ Quota gate for frontend/backend gates ──
    # Returns whether the user is currently allowed to perform write/save
    # operations. Used by chat, project saves, etc. to block requests when
    # the user is over quota, archived, or past_due.
    @router.get("/check")
    async def storage_check(user=Depends(get_current_user)):
        sub = await _evaluate_subscription_state(db, user["user_id"])
        info = _quota_for_subscription(sub)
        # Compute current usage
        used_mb = await _calc_usage_mb(db, user["user_id"])
        quota_mb = info["quota_mb"]
        usage_pct = round((used_mb / quota_mb * 100), 1) if quota_mb > 0 else 0
        over_quota = used_mb >= quota_mb
        allowed = (not info["locked"]) and (not over_quota)
        reason = None
        if info["locked"]:
            reason = info["locked_reason"]
        elif over_quota:
            reason = "امتلأت مساحتك — قم بترقية اشتراكك للمتابعة"
        return {
            "allowed": allowed,
            "reason": reason,
            "used_mb": round(used_mb, 3),
            "quota_mb": quota_mb,
            "usage_pct": usage_pct,
            "status": info["status"],
            "plan_id": info["plan_id"],
            "locked": info["locked"],
            "over_quota": over_quota,
        }

    # ─── POST /api/storage/checkout ─────────────────────────────────────
    @router.post("/checkout")
    async def create_storage_checkout(body: CheckoutIn, user=Depends(get_current_user)):
        plan = STORAGE_PLANS.get(body.plan_id)
        if not plan:
            raise HTTPException(400, "خطة غير صحيحة")
        # Note: no free tier — all plans require PayPal checkout.

        # ─── PayPal (Lemon Squeezy removed — Feb 2026) ─────────────────
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
            txn_ref = str(uuid.uuid4())
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": f"{frontend}/billing/storage?status=success&txn={txn_ref}",
                    "cancel_url": f"{frontend}/billing/storage?status=cancelled",
                },
                "transactions": [{
                    "item_list": {"items": [{
                        "name": f"Storage {plan['label_ar']} ({plan['quota_mb']}MB)",
                        "sku": f"storage_{plan['id']}",
                        "price": f"{plan['price_usd']:.2f}",
                        "currency": "USD",
                        "quantity": 1,
                    }]},
                    "amount": {"total": f"{plan['price_usd']:.2f}", "currency": "USD"},
                    "description": plan["description_ar"],
                }],
            })
            if not payment.create():
                raise HTTPException(500, f"فشل PayPal: {payment.error}")
            approval_url = next(
                (link.href for link in payment.links if link.rel == "approval_url"), None
            )
            if not approval_url:
                raise HTTPException(500, "PayPal لم يرجع رابط الموافقة")
            await db.payment_transactions.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user["user_id"],
                "method": "paypal",
                "paypal_order_id": payment.id,
                "txn_ref": txn_ref,
                "kind": "storage_subscription",
                "plan_id": plan["id"],
                "amount_usd": plan["price_usd"],
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            return {"checkout_url": approval_url, "txn_ref": txn_ref, "method": "paypal"}
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"[storage/checkout] PayPal exception: {e}", exc_info=True)
            raise HTTPException(500, f"خطأ في PayPal: {e}")

    # ─── POST /api/storage/recovery/checkout ────────────────────────────
    # Recovery fee = 2× the plan's monthly price (per-plan, not per-size).
    # Triggered when the user is past_due/archived and wants to unlock files.
    @router.post("/recovery/checkout")
    async def create_recovery_checkout(_body: RecoveryCheckoutIn, user=Depends(get_current_user)):
        sub = await _get_user_storage_subscription(db, user["user_id"])
        if sub.get("status") not in ("archived", "past_due", "cancelled"):
            raise HTTPException(400, "حسابك نشط — لا حاجة للاسترداد")
        plan_id = sub.get("plan_id") or "starter10"
        tier = recovery_fee_for_plan(plan_id)
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
            txn_ref = str(uuid.uuid4())
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": f"{frontend}/billing/storage?status=recovered&txn={txn_ref}",
                    "cancel_url": f"{frontend}/billing/storage?status=cancelled",
                },
                "transactions": [{
                    "item_list": {"items": [{
                        "name": f"Storage Recovery — {tier['label_ar']}",
                        "sku": f"storage_recovery_{tier['id']}",
                        "price": f"{tier['price_usd']:.2f}",
                        "currency": "USD",
                        "quantity": 1,
                    }]},
                    "amount": {"total": f"{tier['price_usd']:.2f}", "currency": "USD"},
                    "description": f"استرداد ملفات الأرشيف — {tier['label_ar']}",
                }],
            })
            if not payment.create():
                raise HTTPException(500, f"فشل PayPal: {payment.error}")
            approval_url = next(
                (link.href for link in payment.links if link.rel == "approval_url"), None
            )
            if not approval_url:
                raise HTTPException(500, "PayPal لم يرجع رابط الموافقة")
            await db.payment_transactions.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user["user_id"],
                "method": "paypal",
                "paypal_order_id": payment.id,
                "txn_ref": txn_ref,
                "kind": "storage_recovery",
                "recovery_tier": tier["id"],
                "amount_usd": tier["price_usd"],
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            return {"checkout_url": approval_url, "txn_ref": txn_ref, "tier": tier}
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"[storage/recovery] PayPal exception: {e}", exc_info=True)
            raise HTTPException(500, f"خطأ في PayPal: {e}")

    # ─── POST /api/storage/capture ─ PayPal return handler ────────────
    # Called by the frontend `BillingStorage` page after the user returns
    # from PayPal. Finds the pending transaction, executes the payment,
    # and activates the storage subscription (or recovery).
    @router.post("/capture")
    async def storage_capture(body: StorageCaptureIn, user=Depends(get_current_user)):
        txn = await db.payment_transactions.find_one(
            {"txn_ref": body.txn_ref, "user_id": user["user_id"]}, {"_id": 0},
        )
        if not txn:
            raise HTTPException(404, "السجل غير موجود")
        if txn.get("status") == "completed":
            return {"ok": True, "already": True, "kind": txn.get("kind"), "plan_id": txn.get("plan_id")}
        # Execute the PayPal payment
        try:
            import paypalrestsdk
            paypalrestsdk.configure({
                "mode": os.environ.get("PAYPAL_MODE", "live"),
                "client_id": os.environ["PAYPAL_CLIENT_ID"],
                "client_secret": os.environ["PAYPAL_SECRET"],
            })
            order_id = body.order_id or txn.get("paypal_order_id")
            payment = paypalrestsdk.Payment.find(order_id)
            if not payment:
                raise HTTPException(404, "الطلب غير موجود في PayPal")
            if body.payer_id and payment.state != "approved":
                ok = payment.execute({"payer_id": body.payer_id})
                if not ok:
                    log.error(f"[storage/capture] execute failed: {payment.error}")
                    raise HTTPException(500, f"فشل تنفيذ الدفع: {payment.error}")
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"[storage/capture] exception: {e}", exc_info=True)
            raise HTTPException(500, f"خطأ في PayPal: {e}")

        uid = user["user_id"]
        kind = txn.get("kind")

        # ── A) Storage subscription activation ─────────────────────────
        if kind == "storage_subscription":
            plan_id = txn.get("plan_id") or "s50"
            plan = STORAGE_PLANS.get(plan_id) or STORAGE_PLANS["s50"]
            period_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
            await db.storage_subscriptions.update_one(
                {"user_id": uid},
                {"$set": {
                    "user_id": uid,
                    "plan_id": plan_id,
                    "status": "active",
                    "paypal_subscription_id": None,
                    "current_period_end": period_end,
                    "grace_started_at": None,
                    "archived_at": None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }},
                upsert=True,
            )
            await db.users.update_one(
                {"id": uid},
                {"$set": {
                    "storage_tier": plan_id,
                    "storage_quota_mb": plan["quota_mb"],
                    "storage_archived": False,
                }},
            )
            await db.freebuild_projects.update_many(
                {"user_id": uid, "status": "archived"},
                {"$set": {"status": "active"}},
            )
            await db.payment_transactions.update_one(
                {"txn_ref": body.txn_ref},
                {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}},
            )
            log.info(f"[storage-capture] subscription {plan_id} active for {uid}")
            return {"ok": True, "kind": "storage_subscription", "plan_id": plan_id}

        # ── B) Recovery activation ─────────────────────────────────────
        if kind == "storage_recovery":
            await db.storage_subscriptions.update_one(
                {"user_id": uid},
                {"$set": {
                    "status": "past_due",            # still must renew sub
                    "archived_at": None,
                    "archived_size_mb": 0,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
            await db.freebuild_projects.update_many(
                {"user_id": uid, "status": "archived"},
                {"$set": {"status": "active"}},
            )
            await db.users.update_one(
                {"id": uid},
                {"$set": {"storage_archived": False}},
            )
            await db.payment_transactions.update_one(
                {"txn_ref": body.txn_ref},
                {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}},
            )
            log.info(f"[storage-capture] recovery applied for {uid}")
            return {"ok": True, "kind": "storage_recovery"}

        return {"ok": True, "kind": kind, "skipped": "unknown_kind"}

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
