"""
Store Router — Merchant products + Customer auth + Wishlist + Reviews + Orders.
All endpoints are prefixed with /api/store.

Owner: Zenrex Platform (Feb 2026)
"""
from __future__ import annotations

import os
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List

import jwt
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

log = logging.getLogger("store_router")
router = APIRouter(prefix="/api/store", tags=["store"])

# ── Mongo ─────────────────────────────────────────────────────────────────────
_mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _mongo[os.environ["DB_NAME"]]

# ── JWT helper ────────────────────────────────────────────────────────────────
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key")
JWT_ALG = "HS256"


def _create_token(sub: str, role: str, days: int = 7) -> str:
    payload = {
        "sub": sub,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=days),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def _bearer_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return _decode_token(authorization[7:])


async def merchant_user(payload: dict = Depends(_bearer_user)) -> dict:
    """For admin/owner/merchant routes — reuses platform JWT (which uses user_id)."""
    uid = payload.get("user_id") or payload.get("sub")
    if not uid:
        raise HTTPException(status_code=401, detail="Bad token")
    role = payload.get("role", "client")
    if role not in ("owner", "super_admin", "admin", "merchant"):
        raise HTTPException(status_code=403, detail="Merchant access only")
    return {"user_id": uid, "role": role}


async def customer_user(payload: dict = Depends(_bearer_user)) -> dict:
    """For customer routes — uses 'customer' role tokens minted by /api/store/customer/verify-otp."""
    if payload.get("role") != "customer":
        raise HTTPException(status_code=403, detail="Customer access only")
    return {"customer_id": payload["sub"], "phone": payload.get("phone")}


# ╔══════════════════════════════════════════════════════════════════════════════
# ║  CUSTOMER AUTH (phone + OTP)
# ╚══════════════════════════════════════════════════════════════════════════════
class OtpRequest(BaseModel):
    phone: str = Field(min_length=7, max_length=20)


class OtpVerify(BaseModel):
    phone: str
    code: str = Field(min_length=4, max_length=6)
    name: Optional[str] = None


@router.post("/customer/request-otp")
async def customer_request_otp(body: OtpRequest, request: Request):
    """Generate a 4-digit OTP and persist with 5min expiry. For now we return it in dev (not in production)."""
    phone = body.phone.strip()
    # Demo OTP: always 1234 (per existing convention in mockups)
    otp = "1234"
    await db.customer_otps.update_one(
        {"phone": phone},
        {
            "$set": {
                "phone": phone,
                "otp": otp,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
                "ip": request.client.host if request.client else "?",
            }
        },
        upsert=True,
    )
    log.info(f"customer OTP sent to {phone} (demo=1234)")
    return {"ok": True, "demo_otp": otp, "ttl_sec": 300}


@router.post("/customer/verify-otp")
async def customer_verify_otp(body: OtpVerify):
    phone = body.phone.strip()
    rec = await db.customer_otps.find_one({"phone": phone})
    if not rec:
        raise HTTPException(status_code=400, detail="اطلب رمز OTP أولاً")
    # Check expiry
    try:
        exp = datetime.fromisoformat(rec["expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp:
            raise HTTPException(status_code=400, detail="انتهت صلاحية الرمز — اطلب رمزاً جديداً")
    except HTTPException:
        raise
    except Exception:
        pass
    if (body.code or "").strip() != rec.get("otp"):
        raise HTTPException(status_code=400, detail="الرمز غير صحيح")
    # Find-or-create customer
    cust = await db.customers.find_one({"phone": phone})
    if not cust:
        cust = {
            "id": secrets.token_urlsafe(12),
            "phone": phone,
            "name": (body.name or "").strip(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "loyalty_points": 0,
            "orders_count": 0,
        }
        await db.customers.insert_one(dict(cust))
    cust.pop("_id", None)
    token = _create_token(cust["id"], "customer", days=30)
    # Clean OTP
    await db.customer_otps.delete_one({"phone": phone})
    return {"token": token, "user": {**cust, "phone": phone}}


@router.get("/customer/me")
async def customer_me(u: dict = Depends(customer_user)):
    cust = await db.customers.find_one({"id": u["customer_id"]}, {"_id": 0})
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    return cust


# ╔══════════════════════════════════════════════════════════════════════════════
# ║  PRODUCTS CRUD (merchant)
# ╚══════════════════════════════════════════════════════════════════════════════
class ProductIn(BaseModel):
    name: str
    price: float = 0
    stock: int = 0
    sku: Optional[str] = ""
    stock_low: int = 5
    mfg: Optional[str] = ""
    exp: Optional[str] = ""
    track_expiry: bool = False
    cat: Optional[str] = ""
    img: Optional[str] = ""
    desc: Optional[str] = ""
    analysis: Optional[dict] = None


@router.get("/products")
async def list_products(merchant_id: Optional[str] = None):
    """Public list — used by both merchant dashboard + customer storefront."""
    q = {"merchant_id": merchant_id} if merchant_id else {}
    items = await db.store_products.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"items": items, "count": len(items)}


@router.post("/products")
async def create_product(body: ProductIn, u: dict = Depends(merchant_user)):
    doc = body.model_dump()
    doc.update(
        {
            "id": "p" + secrets.token_urlsafe(8),
            "merchant_id": u["user_id"],
            "sales": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    await db.store_products.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@router.put("/products/{pid}")
async def update_product(pid: str, body: ProductIn, u: dict = Depends(merchant_user)):
    upd = body.model_dump()
    upd["updated_at"] = datetime.now(timezone.utc).isoformat()
    r = await db.store_products.update_one({"id": pid, "merchant_id": u["user_id"]}, {"$set": upd})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    doc = await db.store_products.find_one({"id": pid}, {"_id": 0})
    return doc


@router.delete("/products/{pid}")
async def delete_product(pid: str, u: dict = Depends(merchant_user)):
    r = await db.store_products.delete_one({"id": pid, "merchant_id": u["user_id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"ok": True, "deleted": pid}


# ╔══════════════════════════════════════════════════════════════════════════════
# ║  WISHLIST (customer)
# ╚══════════════════════════════════════════════════════════════════════════════
class WishlistIn(BaseModel):
    product_id: str


@router.get("/wishlist")
async def get_wishlist(u: dict = Depends(customer_user)):
    doc = await db.customer_wishlists.find_one({"customer_id": u["customer_id"]}, {"_id": 0})
    return {"items": (doc or {}).get("items", [])}


@router.post("/wishlist")
async def toggle_wishlist(body: WishlistIn, u: dict = Depends(customer_user)):
    doc = await db.customer_wishlists.find_one({"customer_id": u["customer_id"]})
    items: List[str] = (doc or {}).get("items", [])
    if body.product_id in items:
        items.remove(body.product_id)
        action = "removed"
    else:
        items.append(body.product_id)
        action = "added"
    await db.customer_wishlists.update_one(
        {"customer_id": u["customer_id"]},
        {"$set": {"customer_id": u["customer_id"], "items": items, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"action": action, "items": items}


# ╔══════════════════════════════════════════════════════════════════════════════
# ║  REVIEWS
# ╚══════════════════════════════════════════════════════════════════════════════
class ReviewIn(BaseModel):
    product_id: str
    stars: int = Field(ge=1, le=5)
    text: str = Field(min_length=1, max_length=1000)


@router.get("/reviews/{product_id}")
async def list_reviews(product_id: str):
    items = await db.product_reviews.find({"product_id": product_id}, {"_id": 0}).sort("created_at", -1).to_list(200)
    avg = round(sum(r.get("stars", 0) for r in items) / len(items), 1) if items else 0
    return {"items": items, "count": len(items), "avg": avg}


@router.post("/reviews")
async def add_review(body: ReviewIn, u: dict = Depends(customer_user)):
    cust = await db.customers.find_one({"id": u["customer_id"]}, {"_id": 0})
    # Check if customer actually purchased this product
    has_purchase = await db.store_orders.find_one({
        "customer_id": u["customer_id"],
        "items.product_id": body.product_id,
        "status": {"$in": ["completed", "delivered", "paid"]},
    })
    doc = {
        "id": "rev" + secrets.token_urlsafe(8),
        "product_id": body.product_id,
        "customer_id": u["customer_id"],
        "name": (cust or {}).get("name") or u.get("phone") or "عميل",
        "stars": body.stars,
        "text": body.text.strip(),
        "verified_purchase": bool(has_purchase),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.product_reviews.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


class TranslateIn(BaseModel):
    text: str
    target_lang: str = "ar"   # ar / en / zh / hi / fr / es / ur ...


@router.post("/reviews/translate")
async def translate_review(body: TranslateIn):
    """Translate a review comment to a target language using direct LLM shim."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        lang_names = {
            "ar":"Arabic","en":"English","zh":"Chinese (Simplified)",
            "hi":"Hindi","fr":"French","es":"Spanish","ur":"Urdu",
            "tr":"Turkish","fa":"Persian","bn":"Bengali","de":"German",
        }
        target_name = lang_names.get(body.target_lang, "Arabic")
        chat = LlmChat(api_key="x", session_id="trans_"+secrets.token_urlsafe(4),
                       system_message=f"You are a precise translator. Translate the given text to {target_name}. Output ONLY the translation, no explanations, no quotes.")
        chat.with_model("gemini", "gemini-2.5-flash")
        out = await chat.send_message(UserMessage(text=body.text))
        return {"ok": True, "translated": (out or "").strip(), "target_lang": body.target_lang}
    except Exception as e:
        return {"ok": False, "translated": body.text, "error": str(e)[:200]}


@router.get("/orders/customer/pending-reviews")
async def customer_pending_reviews(u: dict = Depends(customer_user)):
    """Returns delivered orders + which products this customer hasn't reviewed yet."""
    orders = await db.store_orders.find(
        {"customer_id": u["customer_id"], "status": {"$in": ["completed","delivered","paid"]}},
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    # Get all this customer's review product_ids
    revs = await db.product_reviews.find({"customer_id": u["customer_id"]}, {"_id":0,"product_id":1}).to_list(500)
    reviewed = {r["product_id"] for r in revs}
    pending = []
    for o in orders:
        for it in o.get("items", []):
            pid = it.get("product_id") or it.get("id")
            if pid and pid not in reviewed:
                pending.append({
                    "order_id": o.get("id"),
                    "product_id": pid,
                    "product_name": it.get("name") or it.get("title") or "منتج",
                    "image": it.get("image") or "",
                    "delivered_at": o.get("delivered_at") or o.get("created_at"),
                })
    return {"pending": pending, "count": len(pending)}


# ╔══════════════════════════════════════════════════════════════════════════════
# ║  HEALTH
# ╚══════════════════════════════════════════════════════════════════════════════
@router.get("/health")
async def health():
    n_prod = await db.store_products.count_documents({})
    n_cust = await db.customers.count_documents({})
    n_rev = await db.product_reviews.count_documents({})
    return {"ok": True, "products": n_prod, "customers": n_cust, "reviews": n_rev}
