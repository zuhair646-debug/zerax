"""
Affiliate Payouts — Self-service withdrawal requests for marketers.

Flow:
  1. Marketer adds PayPal email (mandatory)
  2. Marketer requests payout (e.g. $50) → system deducts $2 fee → net $48
  3. Admin sees request in /admin/payouts
  4. Admin pays via PayPal manually → clicks "Mark Paid"
  5. Marketer receives notification "تم تحويل $48 إلى your@email.com"
  6. Marketer's pending_balance is decremented on REQUEST (locked), then
     on rejection it's restored, on paid it's moved to paid_total.

Collections:
  affiliate_payouts:
    { id, user_id, code, amount_requested_usd, fee_usd, amount_net_usd,
      paypal_email, status (pending|paid|rejected),
      requested_at, processed_at, processed_by, paid_txn_ref,
      rejection_reason, notes }
  user_notifications: see notifications module
"""
from __future__ import annotations
import os
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger("zitex.affiliate.payouts")
router = APIRouter(tags=["affiliate-payouts"])

PAYOUT_FEE_USD = 2.0
MIN_PAYOUT_USD = 25.0  # حد أدنى لطلب السحب


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d): return d.isoformat() if isinstance(d, datetime) else d


class PaypalEmailIn(BaseModel):
    paypal_email: EmailStr


class PayoutRequestIn(BaseModel):
    amount_usd: float = Field(..., gt=0)


class MarkPaidIn(BaseModel):
    paid_txn_ref: Optional[str] = None
    notes: Optional[str] = None


class RejectPayoutIn(BaseModel):
    reason: str


def build_router(db, get_current_user, notify):
    """
    notify: async function(user_id, type, title, body, link=None) → records a notification
    """

    def _is_admin(u):
        role = (u.get("role") or "").lower()
        return role in {"admin", "super_admin", "owner"} or bool(u.get("is_owner"))

    # ════════════════════════════════════════════════════════════
    # MARKETER: set PayPal email + view info
    # ════════════════════════════════════════════════════════════
    @router.post("/affiliate/me/paypal-email")
    async def set_paypal_email(body: PaypalEmailIn, user=Depends(get_current_user)):
        uid = user["user_id"]
        a = await db.affiliates.find_one({"user_id": uid})
        if not a:
            raise HTTPException(403, "أنت لست مسوّقاً")
        await db.affiliates.update_one(
            {"user_id": uid},
            {"$set": {"paypal_email": str(body.paypal_email), "paypal_set_at": _now()}},
        )
        return {"ok": True, "paypal_email": str(body.paypal_email)}

    @router.get("/affiliate/me/payout-info")
    async def payout_info(user=Depends(get_current_user)):
        uid = user["user_id"]
        a = await db.affiliates.find_one({"user_id": uid}, {"_id": 0})
        if not a:
            raise HTTPException(403, "أنت لست مسوّقاً")
        return {
            "pending_balance": float(a.get("pending_balance", 0)),
            "paid_total": float(a.get("paid_total", 0)),
            "lifetime_earnings": float(a.get("lifetime_earnings", 0)),
            "paypal_email": a.get("paypal_email"),
            "fee_usd": PAYOUT_FEE_USD,
            "min_payout_usd": MIN_PAYOUT_USD,
        }

    # ════════════════════════════════════════════════════════════
    # MARKETER: request a payout (lock balance immediately)
    # ════════════════════════════════════════════════════════════
    @router.post("/affiliate/me/payout/request")
    async def request_payout(body: PayoutRequestIn, user=Depends(get_current_user)):
        uid = user["user_id"]
        a = await db.affiliates.find_one({"user_id": uid})
        if not a:
            raise HTTPException(403, "أنت لست مسوّقاً")

        amount = float(body.amount_usd)
        if amount < MIN_PAYOUT_USD:
            raise HTTPException(400, f"الحد الأدنى للسحب ${MIN_PAYOUT_USD}")

        pending = float(a.get("pending_balance", 0))
        if amount > pending + 0.001:
            raise HTTPException(400, f"الرصيد المتاح ${pending:.2f} فقط")

        if not a.get("paypal_email"):
            raise HTTPException(400, "أضف بريد PayPal أولاً")

        # Prevent stacking requests
        existing = await db.affiliate_payouts.find_one({"user_id": uid, "status": "pending"})
        if existing:
            raise HTTPException(400, "عندك طلب معلّق بالفعل — انتظر معالجته")

        fee = PAYOUT_FEE_USD
        net = round(amount - fee, 2)
        doc = {
            "id": uuid.uuid4().hex,
            "user_id": uid,
            "code": a.get("code"),
            "amount_requested_usd": round(amount, 2),
            "fee_usd": fee,
            "amount_net_usd": net,
            "paypal_email": a.get("paypal_email"),
            "status": "pending",
            "requested_at": _now(),
            "processed_at": None,
            "processed_by": None,
            "paid_txn_ref": None,
        }
        await db.affiliate_payouts.insert_one(doc)
        # Lock the funds (subtract from pending_balance immediately)
        await db.affiliates.update_one(
            {"user_id": uid},
            {"$inc": {"pending_balance": -amount, "locked_in_payouts": amount}},
        )

        # Notify admins (best-effort)
        try:
            admins = await db.users.find(
                {"$or": [{"role": "admin"}, {"role": "super_admin"}, {"role": "owner"}, {"is_owner": True}]},
                {"_id": 0, "id": 1},
            ).to_list(length=20)
            for ad in admins:
                await notify(
                    user_id=ad["id"],
                    n_type="payout_request",
                    title="💰 طلب تحويل جديد",
                    body=f"المسوّق طلب ${amount:.2f} (يستلم ${net:.2f} بعد رسوم ${fee:.2f})",
                    link="/admin/payouts",
                )
        except Exception:
            logger.exception("notify admins failed")

        return {
            "ok": True,
            "id": doc["id"],
            "amount_requested": round(amount, 2),
            "fee": fee,
            "amount_net": net,
            "status": "pending",
            "estimated_processing": "24-48 ساعة",
        }

    # ════════════════════════════════════════════════════════════
    # MARKETER: my payout history
    # ════════════════════════════════════════════════════════════
    @router.get("/affiliate/me/payouts")
    async def my_payouts(user=Depends(get_current_user)):
        uid = user["user_id"]
        out = []
        async for p in db.affiliate_payouts.find({"user_id": uid}, {"_id": 0}, sort=[("requested_at", -1)]).limit(50):
            p["requested_at"] = _iso(p.get("requested_at"))
            p["processed_at"] = _iso(p.get("processed_at"))
            out.append(p)
        return {"items": out, "total": len(out)}

    # ════════════════════════════════════════════════════════════
    # ADMIN: list payouts
    # ════════════════════════════════════════════════════════════
    @router.get("/admin/payouts")
    async def admin_payouts(status: Optional[str] = None, user=Depends(get_current_user)):
        if not _is_admin(user):
            raise HTTPException(403, "للأدمن فقط")
        match = {}
        if status and status in {"pending", "paid", "rejected"}:
            match["status"] = status
        out = []
        async for p in db.affiliate_payouts.find(match, {"_id": 0}, sort=[("requested_at", -1)]).limit(200):
            u = await db.users.find_one({"id": p.get("user_id")}, {"_id": 0, "name": 1, "email": 1, "country": 1})
            p["user"] = {
                "name": (u or {}).get("name"),
                "email": (u or {}).get("email"),
                "country": (u or {}).get("country"),
            }
            p["requested_at"] = _iso(p.get("requested_at"))
            p["processed_at"] = _iso(p.get("processed_at"))
            out.append(p)
        return {"items": out, "total": len(out)}

    @router.post("/admin/payouts/{payout_id}/mark-paid")
    async def admin_mark_paid(payout_id: str, body: MarkPaidIn, user=Depends(get_current_user)):
        if not _is_admin(user):
            raise HTTPException(403, "للأدمن فقط")
        p = await db.affiliate_payouts.find_one({"id": payout_id})
        if not p:
            raise HTTPException(404, "غير موجود")
        if p["status"] != "pending":
            raise HTTPException(400, f"الحالة الحالية: {p['status']}")
        await db.affiliate_payouts.update_one(
            {"id": payout_id},
            {"$set": {
                "status": "paid",
                "processed_at": _now(),
                "processed_by": user["user_id"],
                "paid_txn_ref": body.paid_txn_ref,
                "notes": body.notes,
            }},
        )
        # Move locked → paid_total
        await db.affiliates.update_one(
            {"user_id": p["user_id"]},
            {"$inc": {
                "locked_in_payouts": -p["amount_requested_usd"],
                "paid_total": p["amount_net_usd"],
                "total_fees_paid": p["fee_usd"],
            }},
        )
        # Notify
        try:
            await notify(
                user_id=p["user_id"],
                n_type="payout_paid",
                title="✅ تم تحويل أموالك",
                body=f"تم تحويل ${p['amount_net_usd']:.2f} إلى {p['paypal_email']}" +
                     (f" (مرجع: {body.paid_txn_ref})" if body.paid_txn_ref else ""),
                link="/affiliate",
            )
        except Exception:
            logger.exception("notify user failed")
        return {"ok": True}

    @router.post("/admin/payouts/{payout_id}/reject")
    async def admin_reject(payout_id: str, body: RejectPayoutIn, user=Depends(get_current_user)):
        if not _is_admin(user):
            raise HTTPException(403, "للأدمن فقط")
        p = await db.affiliate_payouts.find_one({"id": payout_id})
        if not p:
            raise HTTPException(404, "غير موجود")
        if p["status"] != "pending":
            raise HTTPException(400, f"الحالة الحالية: {p['status']}")
        await db.affiliate_payouts.update_one(
            {"id": payout_id},
            {"$set": {
                "status": "rejected",
                "processed_at": _now(),
                "processed_by": user["user_id"],
                "rejection_reason": body.reason,
            }},
        )
        # Restore locked → pending_balance
        await db.affiliates.update_one(
            {"user_id": p["user_id"]},
            {"$inc": {
                "locked_in_payouts": -p["amount_requested_usd"],
                "pending_balance": p["amount_requested_usd"],
            }},
        )
        try:
            await notify(
                user_id=p["user_id"],
                n_type="payout_rejected",
                title="⛔ تم رفض طلب التحويل",
                body=f"رصيدك أعيد. السبب: {body.reason}",
                link="/affiliate",
            )
        except Exception:
            pass
        return {"ok": True}

    return router
