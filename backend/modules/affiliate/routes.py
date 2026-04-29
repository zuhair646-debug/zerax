"""
Affiliate Marketing Program — paid commission per referred subscription.

Flow:
  1. User applies → creates `affiliates` doc with status='pending'
  2. Owner approves → status='active', unique 8-char code generated
  3. User shares link: https://APP/register?aff=XXXXX
  4. New user signs up — backend captures `aff` param, sets `affiliate_ref` on user doc
  5. When that user pays for a subscription, billing webhook calls `record_commission()`
     which credits the affiliate's pending_balance (commission_pct of payment)
  6. Affiliate sees dashboard with referrals + earnings + payout history
  7. Owner can mark payouts as paid (moves from pending_balance → paid_total)

Collections:
  affiliates           — { user_id, code, status, commission_pct, pending_balance, paid_total, ... }
  affiliate_referrals  — { code, referred_user_id, signup_at, paid_at, amount, commission, txn_session_id }
  affiliate_payouts    — { user_id, amount, method, note, at, by }
"""
import secrets
import string
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_code(n: int = 8) -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(n))


DEFAULT_COMMISSION_PCT = 20.0  # 20% of every payment


# ─────────────────────────────────────────────────────────────────
# Helper used by the billing webhook (called from outside this module)
# ─────────────────────────────────────────────────────────────────
async def record_commission(
    database,
    referred_user_id: str,
    txn_session_id: str,
    amount: float,
    currency: str = "usd",
):
    """
    Called by the Stripe webhook handler immediately after a subscription is activated.
    If the referred user has an affiliate code, credit the affiliate's pending balance.
    """
    try:
        user = await database.users.find_one(
            {"id": referred_user_id}, {"_id": 0, "affiliate_ref": 1}
        )
        if not user:
            return
        code = (user.get("affiliate_ref") or "").strip().upper()
        if not code:
            return

        aff = await database.affiliates.find_one({"code": code, "status": "active"}, {"_id": 0})
        if not aff:
            return

        # Idempotency — don't double-credit if the same session is processed twice
        existing = await database.affiliate_referrals.find_one(
            {"txn_session_id": txn_session_id, "code": code}, {"_id": 0}
        )
        if existing and existing.get("paid_at"):
            return

        pct = float(aff.get("commission_pct") or DEFAULT_COMMISSION_PCT)
        commission = round(float(amount or 0) * pct / 100.0, 2)

        # Upsert referral row, marking it as paid
        await database.affiliate_referrals.update_one(
            {"txn_session_id": txn_session_id, "code": code},
            {
                "$set": {
                    "code": code,
                    "referred_user_id": referred_user_id,
                    "txn_session_id": txn_session_id,
                    "amount": float(amount or 0),
                    "currency": currency,
                    "commission": commission,
                    "paid_at": _iso_now(),
                },
                "$setOnInsert": {"signup_at": _iso_now()},
            },
            upsert=True,
        )

        # Credit pending balance
        await database.affiliates.update_one(
            {"code": code},
            {
                "$inc": {
                    "pending_balance": commission,
                    "lifetime_earnings": commission,
                    "lifetime_referrals_paid": 1,
                }
            },
        )
    except Exception:
        # Never break a payment because of affiliate logic
        pass


async def record_signup(database, referred_user_id: str, code: str):
    """Called from the register endpoint when a new user signed up via ?aff=XXX."""
    code = (code or "").strip().upper()
    if not code:
        return
    aff = await database.affiliates.find_one({"code": code, "status": "active"}, {"_id": 0})
    if not aff:
        return
    # Stamp the user with the code (so commission can attribute later when they pay)
    await database.users.update_one(
        {"id": referred_user_id}, {"$set": {"affiliate_ref": code}}
    )
    # Track the signup event
    await database.affiliate_referrals.insert_one({
        "code": code,
        "referred_user_id": referred_user_id,
        "signup_at": _iso_now(),
    })
    await database.affiliates.update_one(
        {"code": code}, {"$inc": {"lifetime_referrals_signups": 1}}
    )


# ─────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────
def init_routes(database, auth_dep) -> APIRouter:
    r = APIRouter(prefix="/affiliate", tags=["affiliate"])

    async def _require_owner(current_user: dict = Depends(auth_dep)) -> dict:
        if (current_user or {}).get("role") != "owner":
            raise HTTPException(403, "Owner access only")
        return current_user

    # ── Public-ish: validate a code (used by /register page to show the marketer's name) ──
    @r.get("/validate/{code}")
    async def _validate(code: str):
        aff = await database.affiliates.find_one(
            {"code": code.upper(), "status": "active"}, {"_id": 0, "code": 1, "user_id": 1}
        )
        if not aff:
            return {"valid": False}
        u = await database.users.find_one({"id": aff["user_id"]}, {"_id": 0, "name": 1, "email": 1})
        return {"valid": True, "code": aff["code"], "marketer_name": (u or {}).get("name", "مسوّق")}

    # ── User-facing: apply / dashboard ──
    class ApplyIn(BaseModel):
        method: Optional[str] = ""        # how they will market (social, blog, etc)
        notes: Optional[str] = ""

    @r.post("/apply")
    async def _apply(body: ApplyIn, current_user: dict = Depends(auth_dep)):
        uid = current_user["user_id"]
        existing = await database.affiliates.find_one({"user_id": uid}, {"_id": 0})
        if existing:
            return {"status": existing.get("status"), "code": existing.get("code", "")}
        doc = {
            "user_id": uid,
            "code": "",
            "status": "pending",
            "commission_pct": DEFAULT_COMMISSION_PCT,
            "pending_balance": 0.0,
            "paid_total": 0.0,
            "lifetime_earnings": 0.0,
            "lifetime_referrals_signups": 0,
            "lifetime_referrals_paid": 0,
            "method": (body.method or "")[:200],
            "notes": (body.notes or "")[:1000],
            "created_at": _iso_now(),
            "updated_at": _iso_now(),
        }
        await database.affiliates.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @r.get("/me")
    async def _me(current_user: dict = Depends(auth_dep)):
        """Marketer's full dashboard data."""
        uid = current_user["user_id"]
        aff = await database.affiliates.find_one({"user_id": uid}, {"_id": 0})
        if not aff:
            return {"enrolled": False}

        refs: List[Dict[str, Any]] = []
        if aff.get("code"):
            cur = database.affiliate_referrals.find(
                {"code": aff["code"]}, {"_id": 0}
            ).sort("signup_at", -1).limit(200)
            async for d in cur:
                # Decorate with referred user's email/name (best-effort)
                u = await database.users.find_one(
                    {"id": d.get("referred_user_id")}, {"_id": 0, "email": 1, "name": 1}
                )
                d["referred_user"] = {
                    "email": (u or {}).get("email", "—"),
                    "name": (u or {}).get("name", ""),
                }
                refs.append(d)

        payouts = await database.affiliate_payouts.find(
            {"user_id": uid}, {"_id": 0}
        ).sort("at", -1).limit(50).to_list(50)

        return {
            "enrolled": True,
            "affiliate": aff,
            "referrals": refs,
            "payouts": payouts,
        }

    # ── Admin-only ──
    @r.get("/admin/list")
    async def _admin_list(_u: dict = Depends(_require_owner)):
        docs = await database.affiliates.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
        # Decorate
        out = []
        for d in docs:
            u = await database.users.find_one(
                {"id": d.get("user_id")}, {"_id": 0, "email": 1, "name": 1}
            )
            d["user"] = {"email": (u or {}).get("email", ""), "name": (u or {}).get("name", "")}
            out.append(d)
        return {"affiliates": out, "total": len(out)}

    class ApproveIn(BaseModel):
        commission_pct: Optional[float] = None  # override default
        approved: bool = True

    @r.post("/admin/{user_id}/approve")
    async def _admin_approve(user_id: str, body: ApproveIn, _u: dict = Depends(_require_owner)):
        aff = await database.affiliates.find_one({"user_id": user_id}, {"_id": 0})
        if not aff:
            raise HTTPException(404, "Application not found")
        patch: Dict[str, Any] = {"updated_at": _iso_now()}
        if body.approved:
            patch["status"] = "active"
            if not aff.get("code"):
                # Generate a unique code
                while True:
                    code = _gen_code(8)
                    if not await database.affiliates.find_one({"code": code}):
                        break
                patch["code"] = code
            if body.commission_pct is not None:
                patch["commission_pct"] = float(body.commission_pct)
        else:
            patch["status"] = "rejected"
        await database.affiliates.update_one({"user_id": user_id}, {"$set": patch})
        fresh = await database.affiliates.find_one({"user_id": user_id}, {"_id": 0})
        return fresh

    class PayoutIn(BaseModel):
        amount: float
        method: Optional[str] = "manual"
        note: Optional[str] = ""

    @r.post("/admin/{user_id}/payout")
    async def _admin_payout(user_id: str, body: PayoutIn, current_user: dict = Depends(_require_owner)):
        aff = await database.affiliates.find_one({"user_id": user_id}, {"_id": 0})
        if not aff:
            raise HTTPException(404, "Affiliate not found")
        if body.amount <= 0:
            raise HTTPException(400, "amount must be > 0")
        if body.amount > float(aff.get("pending_balance") or 0):
            raise HTTPException(400, "amount exceeds pending balance")
        await database.affiliate_payouts.insert_one({
            "user_id": user_id,
            "amount": float(body.amount),
            "method": body.method or "manual",
            "note": (body.note or "")[:300],
            "at": _iso_now(),
            "by": current_user.get("email") or current_user["user_id"],
        })
        await database.affiliates.update_one(
            {"user_id": user_id},
            {"$inc": {"pending_balance": -float(body.amount), "paid_total": float(body.amount)},
             "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True}

    @r.get("/admin/stats")
    async def _admin_stats(_u: dict = Depends(_require_owner)):
        agg = await database.affiliates.aggregate([
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "active": {"$sum": {"$cond": [{"$eq": ["$status", "active"]}, 1, 0]}},
                "pending": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}},
                "lifetime_earnings": {"$sum": "$lifetime_earnings"},
                "pending_balance": {"$sum": "$pending_balance"},
                "paid_total": {"$sum": "$paid_total"},
            }},
        ]).to_list(1)
        s = agg[0] if agg else {"total": 0, "active": 0, "pending": 0, "lifetime_earnings": 0, "pending_balance": 0, "paid_total": 0}
        s.pop("_id", None)
        # Top 5 marketers
        top = await database.affiliates.find(
            {"status": "active"}, {"_id": 0, "user_id": 1, "code": 1, "lifetime_earnings": 1, "lifetime_referrals_paid": 1}
        ).sort("lifetime_earnings", -1).limit(5).to_list(5)
        for t in top:
            u = await database.users.find_one(
                {"id": t["user_id"]}, {"_id": 0, "email": 1, "name": 1}
            )
            t["user"] = {"email": (u or {}).get("email", ""), "name": (u or {}).get("name", "")}
        return {"stats": s, "top": top}

    return r
