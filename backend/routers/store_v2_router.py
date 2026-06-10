"""
Store Router V2 — Complete E-commerce Backend
==============================================
Adds the missing pieces that were previously localStorage-only:
  • Orders + Checkout
  • Cart
  • Store Credit Wallet
  • Returns Management
  • Subscriptions (recurring orders)
  • Multi-Branch (with inventory per branch)
  • Referrals
  • Saved Cards
  • Merchant AI Profile (onboarding context for Zerax AI)

All endpoints are prefixed with /api/store/v2.
Reuses the JWT helpers from store_router.py so auth stays unified.

Owner: Zerax Platform (Feb 2026)
"""
from __future__ import annotations

import os
import logging
import secrets
import math
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

# Re-use auth dependencies from the main store router
from routers.store_router import merchant_user, customer_user, db as _db

log = logging.getLogger("store_v2_router")
router = APIRouter(prefix="/api/store/v2", tags=["store-v2"])
db = _db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(10)}"


# ╔══════════════════════════════════════════════════════════════════════════════
# ║  ORDERS + CHECKOUT
# ╚══════════════════════════════════════════════════════════════════════════════
class CartItem(BaseModel):
    product_id: str
    qty: int = Field(ge=1)
    price: float = Field(ge=0)
    name: str = ""
    img: str = ""
    variant: Optional[Dict[str, Any]] = None  # color/size/storage


class CheckoutIn(BaseModel):
    items: List[CartItem]
    shipping_address: Dict[str, Any] = {}
    branch_id: Optional[str] = None
    payment_method: str = "cod"  # cod | mada | tabby | tamara | stripe
    coupon: Optional[str] = None
    use_store_credit: float = 0
    notes: str = ""


@router.post("/checkout")
async def checkout(body: CheckoutIn, u: dict = Depends(customer_user)):
    """Customer places an order. Deducts store credit if requested, decreases stock."""
    if not body.items:
        raise HTTPException(status_code=400, detail="Empty cart")

    subtotal = sum(i.price * i.qty for i in body.items)
    shipping = float(body.shipping_address.get("shipping_fee", 15))
    vat = round(subtotal * 0.15, 2)
    credit_applied = 0.0

    # Validate + apply store credit
    if body.use_store_credit > 0:
        wallet = await db.store_credit_wallets.find_one({"customer_id": u["customer_id"]})
        bal = (wallet or {}).get("balance", 0)
        credit_applied = min(body.use_store_credit, bal, subtotal + vat + shipping)

    total = max(0, subtotal + vat + shipping - credit_applied)

    # Decrement product stock atomically (best-effort)
    for it in body.items:
        await db.store_products.update_one(
            {"id": it.product_id, "stock": {"$gte": it.qty}},
            {"$inc": {"stock": -it.qty, "sales": it.qty}},
        )

    order = {
        "id": _gen_id("ord"),
        "customer_id": u["customer_id"],
        "phone": u.get("phone"),
        "items": [i.model_dump() for i in body.items],
        "subtotal": subtotal,
        "vat": vat,
        "shipping": shipping,
        "credit_applied": credit_applied,
        "total": round(total, 2),
        "currency": "SAR",
        "shipping_address": body.shipping_address,
        "branch_id": body.branch_id,
        "payment_method": body.payment_method,
        "payment_status": "pending" if body.payment_method != "cod" else "cod",
        "status": "new",  # new → confirmed → preparing → out_for_delivery → delivered → cancelled
        "coupon": body.coupon,
        "notes": body.notes,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "timeline": [{"status": "new", "at": _now_iso()}],
    }
    await db.store_orders.insert_one(dict(order))
    order.pop("_id", None)

    # Deduct from wallet
    if credit_applied > 0:
        await db.store_credit_wallets.update_one(
            {"customer_id": u["customer_id"]},
            {
                "$inc": {"balance": -credit_applied},
                "$push": {"history": {"type": "spend", "amount": -credit_applied, "order_id": order["id"], "at": _now_iso()}},
            },
        )

    # Award loyalty points (1 pt per 10 SAR)
    points = int(total / 10)
    if points > 0:
        await db.customers.update_one(
            {"id": u["customer_id"]},
            {"$inc": {"loyalty_points": points, "orders_count": 1}},
        )

    return {"order": order, "loyalty_earned": points}


@router.get("/orders")
async def my_orders(u: dict = Depends(customer_user)):
    """List orders for the logged-in customer."""
    items = await db.store_orders.find({"customer_id": u["customer_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"items": items, "count": len(items)}


@router.get("/orders/{order_id}")
async def get_order(order_id: str, u: dict = Depends(customer_user)):
    o = await db.store_orders.find_one({"id": order_id, "customer_id": u["customer_id"]}, {"_id": 0})
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return o


@router.get("/merchant/orders")
async def merchant_orders(u: dict = Depends(merchant_user), status: Optional[str] = None, branch_id: Optional[str] = None):
    """Merchant lists all orders for their store, filterable by status/branch."""
    q: Dict[str, Any] = {}  # TODO: scope by merchant_id once products carry it correctly
    if status:
        q["status"] = status
    if branch_id:
        q["branch_id"] = branch_id
    items = await db.store_orders.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"items": items, "count": len(items)}


class OrderStatusIn(BaseModel):
    status: str


@router.patch("/merchant/orders/{order_id}/status")
async def update_order_status(order_id: str, body: OrderStatusIn, u: dict = Depends(merchant_user)):
    valid = {"new", "confirmed", "preparing", "out_for_delivery", "delivered", "cancelled"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid}")
    await db.store_orders.update_one(
        {"id": order_id},
        {
            "$set": {"status": body.status, "updated_at": _now_iso()},
            "$push": {"timeline": {"status": body.status, "at": _now_iso()}},
        },
    )
    return {"ok": True, "status": body.status}


# ╔══════════════════════════════════════════════════════════════════════════════
# ║  STORE CREDIT WALLET
# ╚══════════════════════════════════════════════════════════════════════════════
@router.get("/wallet")
async def get_wallet(u: dict = Depends(customer_user)):
    w = await db.store_credit_wallets.find_one({"customer_id": u["customer_id"]}, {"_id": 0})
    if not w:
        w = {"customer_id": u["customer_id"], "balance": 0, "history": [], "created_at": _now_iso()}
        await db.store_credit_wallets.insert_one(dict(w))
        w.pop("_id", None)
    return w


class CreditAdjustIn(BaseModel):
    customer_id: str
    amount: float  # positive = credit, negative = debit
    reason: str = ""
    related_order_id: Optional[str] = None


@router.post("/merchant/wallet/adjust")
async def merchant_adjust_credit(body: CreditAdjustIn, u: dict = Depends(merchant_user)):
    """Merchant adds/removes store credit for a customer (refunds, promotions, etc.)."""
    await db.store_credit_wallets.update_one(
        {"customer_id": body.customer_id},
        {
            "$inc": {"balance": body.amount},
            "$push": {"history": {"type": "credit" if body.amount > 0 else "debit", "amount": body.amount, "reason": body.reason, "order_id": body.related_order_id, "at": _now_iso(), "by": u["user_id"]}},
            "$setOnInsert": {"customer_id": body.customer_id, "created_at": _now_iso()},
        },
        upsert=True,
    )
    w = await db.store_credit_wallets.find_one({"customer_id": body.customer_id}, {"_id": 0})
    return w


# ╔══════════════════════════════════════════════════════════════════════════════
# ║  RETURNS
# ╚══════════════════════════════════════════════════════════════════════════════
class ReturnIn(BaseModel):
    order_id: str
    reason: str = Field(min_length=3, max_length=500)
    items: List[Dict[str, Any]] = []  # [{product_id, qty}]
    refund_to_wallet: bool = True


@router.post("/returns")
async def create_return(body: ReturnIn, u: dict = Depends(customer_user)):
    order = await db.store_orders.find_one({"id": body.order_id, "customer_id": u["customer_id"]}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] != "delivered":
        raise HTTPException(status_code=400, detail="Only delivered orders can be returned")

    ret = {
        "id": _gen_id("ret"),
        "order_id": body.order_id,
        "customer_id": u["customer_id"],
        "reason": body.reason.strip(),
        "items": body.items or order["items"],
        "refund_amount": order["total"],
        "refund_to_wallet": body.refund_to_wallet,
        "status": "pending",  # pending → approved → refunded → rejected
        "created_at": _now_iso(),
    }
    await db.store_returns.insert_one(dict(ret))
    ret.pop("_id", None)
    return ret


@router.get("/returns")
async def my_returns(u: dict = Depends(customer_user)):
    items = await db.store_returns.find({"customer_id": u["customer_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"items": items, "count": len(items)}


class ReturnStatusIn(BaseModel):
    status: str  # approved | rejected | refunded


@router.patch("/merchant/returns/{return_id}")
async def update_return_status(return_id: str, body: ReturnStatusIn, u: dict = Depends(merchant_user)):
    valid = {"pending", "approved", "refunded", "rejected"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid}")
    ret = await db.store_returns.find_one({"id": return_id})
    if not ret:
        raise HTTPException(status_code=404, detail="Return not found")
    await db.store_returns.update_one({"id": return_id}, {"$set": {"status": body.status, "updated_at": _now_iso()}})
    # If approved & refund_to_wallet → credit wallet
    if body.status == "refunded" and ret.get("refund_to_wallet"):
        await db.store_credit_wallets.update_one(
            {"customer_id": ret["customer_id"]},
            {
                "$inc": {"balance": ret["refund_amount"]},
                "$push": {"history": {"type": "credit", "amount": ret["refund_amount"], "reason": f"Refund for return {return_id}", "order_id": ret["order_id"], "at": _now_iso()}},
                "$setOnInsert": {"customer_id": ret["customer_id"], "created_at": _now_iso()},
            },
            upsert=True,
        )
    return {"ok": True, "status": body.status}


# ╔══════════════════════════════════════════════════════════════════════════════
# ║  SUBSCRIPTIONS (recurring orders)
# ╚══════════════════════════════════════════════════════════════════════════════
class SubscriptionIn(BaseModel):
    product_id: str
    qty: int = 1
    frequency: str = "monthly"  # weekly | biweekly | monthly | quarterly
    next_delivery: Optional[str] = None
    shipping_address: Dict[str, Any] = {}


@router.post("/subscriptions")
async def create_subscription(body: SubscriptionIn, u: dict = Depends(customer_user)):
    freq_days = {"weekly": 7, "biweekly": 14, "monthly": 30, "quarterly": 90}.get(body.frequency, 30)
    sub = {
        "id": _gen_id("sub"),
        "customer_id": u["customer_id"],
        "product_id": body.product_id,
        "qty": body.qty,
        "frequency": body.frequency,
        "freq_days": freq_days,
        "next_delivery": body.next_delivery or (datetime.now(timezone.utc) + timedelta(days=freq_days)).date().isoformat(),
        "shipping_address": body.shipping_address,
        "status": "active",  # active | paused | cancelled
        "created_at": _now_iso(),
    }
    await db.store_subscriptions.insert_one(dict(sub))
    sub.pop("_id", None)
    return sub


@router.get("/subscriptions")
async def my_subscriptions(u: dict = Depends(customer_user)):
    items = await db.store_subscriptions.find({"customer_id": u["customer_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"items": items, "count": len(items)}


@router.patch("/subscriptions/{sub_id}")
async def update_subscription(sub_id: str, action: str, u: dict = Depends(customer_user)):
    valid = {"pause", "resume", "cancel"}
    if action not in valid:
        raise HTTPException(status_code=400, detail=f"action must be one of {valid}")
    status = {"pause": "paused", "resume": "active", "cancel": "cancelled"}[action]
    r = await db.store_subscriptions.update_one(
        {"id": sub_id, "customer_id": u["customer_id"]}, {"$set": {"status": status, "updated_at": _now_iso()}}
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"ok": True, "status": status}


# ╔══════════════════════════════════════════════════════════════════════════════
# ║  MULTI-BRANCH (with Haversine distance)
# ╚══════════════════════════════════════════════════════════════════════════════
def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


class BranchIn(BaseModel):
    name: str
    address: str = ""
    phone: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    delivery_radius_km: float = 25
    shipping_fee: float = 15
    is_active: bool = True
    manager_name: str = ""


@router.get("/branches")
async def list_branches(merchant_id: Optional[str] = None, lat: Optional[float] = None, lng: Optional[float] = None):
    """Public list of branches. If lat/lng provided, returns nearest first."""
    q = {"merchant_id": merchant_id} if merchant_id else {}
    items = await db.store_branches.find(q, {"_id": 0}).to_list(200)
    if lat is not None and lng is not None:
        for b in items:
            if b.get("lat") is not None and b.get("lng") is not None:
                b["distance_km"] = round(_haversine_km(lat, lng, b["lat"], b["lng"]), 2)
            else:
                b["distance_km"] = None
        items.sort(key=lambda x: (x["distance_km"] is None, x.get("distance_km") or 0))
    return {"items": items, "count": len(items)}


@router.post("/branches")
async def create_branch(body: BranchIn, u: dict = Depends(merchant_user)):
    doc = body.model_dump()
    doc.update({"id": _gen_id("br"), "merchant_id": u["user_id"], "created_at": _now_iso()})
    await db.store_branches.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@router.put("/branches/{branch_id}")
async def update_branch(branch_id: str, body: BranchIn, u: dict = Depends(merchant_user)):
    r = await db.store_branches.update_one(
        {"id": branch_id, "merchant_id": u["user_id"]},
        {"$set": {**body.model_dump(), "updated_at": _now_iso()}},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Branch not found")
    doc = await db.store_branches.find_one({"id": branch_id}, {"_id": 0})
    return doc


@router.delete("/branches/{branch_id}")
async def delete_branch(branch_id: str, u: dict = Depends(merchant_user)):
    r = await db.store_branches.delete_one({"id": branch_id, "merchant_id": u["user_id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Branch not found")
    return {"ok": True}


# ╔══════════════════════════════════════════════════════════════════════════════
# ║  REFERRALS
# ╚══════════════════════════════════════════════════════════════════════════════
@router.get("/referral/me")
async def my_referral(u: dict = Depends(customer_user)):
    """Get or create my referral code."""
    cust = await db.customers.find_one({"id": u["customer_id"]})
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    code = cust.get("referral_code")
    if not code:
        code = "REF" + secrets.token_hex(3).upper()
        await db.customers.update_one({"id": u["customer_id"]}, {"$set": {"referral_code": code}})
    # Count successful referrals
    count = await db.referrals.count_documents({"referrer_id": u["customer_id"], "status": "completed"})
    earnings = await db.referrals.aggregate([{"$match": {"referrer_id": u["customer_id"], "status": "completed"}}, {"$group": {"_id": None, "total": {"$sum": "$reward"}}}]).to_list(1)
    return {"code": code, "successful_referrals": count, "total_earned": (earnings[0]["total"] if earnings else 0)}


class RedeemReferralIn(BaseModel):
    code: str


@router.post("/referral/redeem")
async def redeem_referral(body: RedeemReferralIn, u: dict = Depends(customer_user)):
    code = body.code.strip().upper()
    referrer = await db.customers.find_one({"referral_code": code})
    if not referrer:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    if referrer["id"] == u["customer_id"]:
        raise HTTPException(status_code=400, detail="Can't refer yourself")
    # Check if already redeemed
    existing = await db.referrals.find_one({"referee_id": u["customer_id"]})
    if existing:
        raise HTTPException(status_code=400, detail="Referral already redeemed")
    ref = {
        "id": _gen_id("ref"),
        "referrer_id": referrer["id"],
        "referee_id": u["customer_id"],
        "code": code,
        "reward": 25,  # SAR to referrer once referee completes first order
        "status": "pending",
        "created_at": _now_iso(),
    }
    await db.referrals.insert_one(dict(ref))
    # Welcome credit for new customer
    await db.store_credit_wallets.update_one(
        {"customer_id": u["customer_id"]},
        {"$inc": {"balance": 10}, "$push": {"history": {"type": "credit", "amount": 10, "reason": f"Welcome via referral {code}", "at": _now_iso()}}, "$setOnInsert": {"customer_id": u["customer_id"], "created_at": _now_iso()}},
        upsert=True,
    )
    return {"ok": True, "credit_added": 10}


# ╔══════════════════════════════════════════════════════════════════════════════
# ║  SAVED CARDS (tokenized — never stores full PAN)
# ╚══════════════════════════════════════════════════════════════════════════════
class SavedCardIn(BaseModel):
    last4: str = Field(min_length=4, max_length=4)
    brand: str  # visa | mada | mastercard | amex
    holder: str = ""
    expiry: str = ""  # MM/YY
    gateway_token: str = ""  # tokenized by PSP (Stripe/HyperPay/Moyasar)


@router.get("/saved-cards")
async def list_saved_cards(u: dict = Depends(customer_user)):
    items = await db.saved_cards.find({"customer_id": u["customer_id"]}, {"_id": 0, "gateway_token": 0}).to_list(20)
    return {"items": items}


@router.post("/saved-cards")
async def add_saved_card(body: SavedCardIn, u: dict = Depends(customer_user)):
    doc = body.model_dump()
    doc.update({"id": _gen_id("card"), "customer_id": u["customer_id"], "created_at": _now_iso()})
    await db.saved_cards.insert_one(dict(doc))
    doc.pop("_id", None)
    doc.pop("gateway_token", None)
    return doc


@router.delete("/saved-cards/{card_id}")
async def delete_saved_card(card_id: str, u: dict = Depends(customer_user)):
    r = await db.saved_cards.delete_one({"id": card_id, "customer_id": u["customer_id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"ok": True}


# ╔══════════════════════════════════════════════════════════════════════════════
# ║  MERCHANT AI PROFILE  (the "auto-train" context the user requested)
# ║  Filled at merchant-store-creation time, NOT by the merchant manually.
# ║  Zerax AI uses this as system context to behave per-merchant.
# ╚══════════════════════════════════════════════════════════════════════════════
class MerchantAIProfileIn(BaseModel):
    industry: str = ""  # electronics | clothes | food | meds | beauty | home | sports | books | cars | pets ...
    sub_categories: List[str] = []
    target_markets: List[str] = ["sa"]  # ISO country codes
    brand_tone: str = "professional"  # professional | friendly | luxury | casual | youthful
    languages: List[str] = ["ar"]
    typical_color_palette: List[str] = []  # ["#7c3aed","#fbbf24"]
    photography_style: str = "product"  # product | lifestyle | luxury | flat | 3d
    notes: str = ""  # free text from onboarding chat


@router.get("/merchant/ai-profile")
async def get_ai_profile(u: dict = Depends(merchant_user)):
    p = await db.merchant_ai_profiles.find_one({"merchant_id": u["user_id"]}, {"_id": 0})
    return p or {"merchant_id": u["user_id"], "exists": False}


@router.put("/merchant/ai-profile")
async def upsert_ai_profile(body: MerchantAIProfileIn, u: dict = Depends(merchant_user)):
    doc = body.model_dump()
    doc.update({"merchant_id": u["user_id"], "updated_at": _now_iso()})
    await db.merchant_ai_profiles.update_one(
        {"merchant_id": u["user_id"]},
        {"$set": doc, "$setOnInsert": {"created_at": _now_iso()}},
        upsert=True,
    )
    saved = await db.merchant_ai_profiles.find_one({"merchant_id": u["user_id"]}, {"_id": 0})
    return saved


# ╔══════════════════════════════════════════════════════════════════════════════
# ║  HEALTH
# ╚══════════════════════════════════════════════════════════════════════════════
@router.get("/health")
async def health():
    return {
        "ok": True,
        "orders": await db.store_orders.count_documents({}),
        "wallets": await db.store_credit_wallets.count_documents({}),
        "returns": await db.store_returns.count_documents({}),
        "subscriptions": await db.store_subscriptions.count_documents({}),
        "branches": await db.store_branches.count_documents({}),
        "referrals": await db.referrals.count_documents({}),
        "saved_cards": await db.saved_cards.count_documents({}),
        "ai_profiles": await db.merchant_ai_profiles.count_documents({}),
    }
