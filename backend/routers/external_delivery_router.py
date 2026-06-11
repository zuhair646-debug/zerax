"""
Zerax External Delivery / Errand Service (Mrsool-style)
──────────────────────────────────────────────────────────────────────────
Customer requests a delivery from any pickup → any drop-off (multi-stop
supported, optional return trip). System auto-computes distance via
Haversine, applies merchant's per-km pricing, customer pays online, order
lands in merchant dashboard. Driver sees only their commission (not what
customer paid — merchant keeps the margin).

Endpoints (under /api/delivery/external/*):

  Public (no auth — customer can browse):
    POST /api/delivery/external/quote          — compute price for stops
    POST /api/delivery/external/order          — create order + payment
    GET  /api/delivery/external/order/{id}     — public order status

  Merchant (Bearer JWT):
    GET  /api/delivery/external/orders         — list merchant's external orders
    POST /api/delivery/external/orders/{id}/accept   — accept + dispatch
    POST /api/delivery/external/orders/{id}/reject   — reject + refund flag

  Driver (DriverToken):
    GET  /api/delivery/external/driver/feed    — orders assigned to driver
                                                  with COMMISSION ONLY shown
"""
from __future__ import annotations

import os
import uuid
import math
import jwt
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient

router = APIRouter(prefix="/api/delivery/external", tags=["external-delivery"])

JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key")
_MONGO_URL = os.environ.get("MONGO_URL")
_DB_NAME = os.environ.get("DB_NAME")
_client: Optional[AsyncIOMotorClient] = None


def _db():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(_MONGO_URL)
    return _client[_DB_NAME]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────────────────
# Pricing defaults (merchant-overrideable via driver_configs)
# ─────────────────────────────────────────────────────────────────────────
DEFAULT_PRICING = {
    "base_fee_sar": 8,             # fixed pickup fee
    "per_km_sar": 1.80,            # cost per km
    "min_total_sar": 12,           # floor
    "max_total_sar": 250,          # cap
    "return_discount_pct": 15,     # discount on return-trip leg
    "driver_share_pct": 80,        # what driver actually earns of merchant's revenue
    "errand_extra_sar": 5,         # extra fee for "errand"/shopping type
    "auto_accept": False,          # if true, merchant skips manual approval
    "enabled": True,
}


# ─────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────
class Stop(BaseModel):
    label: str                            # "نقطة استلام" / "نقطة تسليم" / "صيدلية"
    lat: float
    lng: float
    address: Optional[str] = ""
    type: str = "stop"                    # pickup / dropoff / stop / return
    instructions: Optional[str] = ""      # what to buy / what to deliver


class QuoteIn(BaseModel):
    merchant_id: str
    customer_lat: float
    customer_lng: float
    stops: List[Stop]                     # at least one
    return_to_customer: bool = False
    service_type: str = "delivery"        # delivery | errand | pickup


class QuoteOut(BaseModel):
    distance_km: float
    legs: List[Dict[str, Any]]
    base_fee_sar: float
    distance_fee_sar: float
    extra_fee_sar: float
    total_sar: float
    nearest_branch: Optional[Dict[str, Any]] = None
    eta_minutes: int


class OrderIn(BaseModel):
    merchant_id: str
    customer_name: str
    customer_phone: str
    customer_lat: float
    customer_lng: float
    stops: List[Stop]
    return_to_customer: bool = False
    service_type: str = "delivery"
    payment_method: str = "card"          # card | apple_pay | mada
    notes: Optional[str] = ""


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────
def _haversine_km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    """Great-circle distance between two GPS points in km."""
    R = 6371.0
    dlat = math.radians(b_lat - a_lat)
    dlng = math.radians(b_lng - a_lng)
    s = math.sin(dlat / 2) ** 2 + math.cos(math.radians(a_lat)) * math.cos(math.radians(b_lat)) * math.sin(dlng / 2) ** 2
    return round(2 * R * math.asin(math.sqrt(s)), 3)


async def _get_pricing(merchant_id: str) -> Dict[str, Any]:
    db = _db()
    doc = await db.driver_configs.find_one({"merchant_id": merchant_id})
    if not doc:
        # Demo fallback — pick any merchant config
        doc = await db.driver_configs.find_one()
    cfg = (doc or {}).get("config", {})
    user_pricing = cfg.get("external_delivery", {}) or {}
    return {**DEFAULT_PRICING, **user_pricing}


async def _nearest_branch(merchant_id: str, lat: float, lng: float) -> Optional[Dict[str, Any]]:
    db = _db()
    doc = await db.driver_configs.find_one({"merchant_id": merchant_id})
    if not doc:
        doc = await db.driver_configs.find_one()
    branches = (doc or {}).get("branches", []) if doc else []
    if not branches:
        return None
    actives = [b for b in branches if b.get("is_active", True) and b.get("capacity_status") != "closed"]
    if not actives:
        return None
    actives.sort(key=lambda b: _haversine_km(lat, lng, b["lat"], b["lng"]))
    return actives[0]


async def _resolve_merchant_id(merchant_id: str) -> str:
    """If 'demo' or empty, return the first available merchant_id from configs."""
    if merchant_id and merchant_id != "demo":
        return merchant_id
    db = _db()
    doc = await db.driver_configs.find_one()
    return doc.get("merchant_id") if doc else merchant_id


def _compute_quote(stops: List[Stop], cust_lat: float, cust_lng: float,
                   branch: Optional[Dict[str, Any]], return_trip: bool,
                   pricing: Dict[str, Any], service_type: str) -> Dict[str, Any]:
    """Build leg-by-leg distance breakdown."""
    legs: List[Dict[str, Any]] = []
    total_km = 0.0

    # Leg 1: branch (or first stop) → customer
    cursor_lat, cursor_lng = (branch["lat"], branch["lng"]) if branch else (stops[0].lat, stops[0].lng)
    cursor_label = branch["name_ar"] if branch else stops[0].label

    # Walk through stops in order
    for stop in stops:
        d = _haversine_km(cursor_lat, cursor_lng, stop.lat, stop.lng)
        legs.append({
            "from": cursor_label,
            "to": stop.label,
            "km": d,
            "instructions": stop.instructions or "",
        })
        total_km += d
        cursor_lat, cursor_lng = stop.lat, stop.lng
        cursor_label = stop.label

    # Return trip back to customer location
    if return_trip:
        d = _haversine_km(cursor_lat, cursor_lng, cust_lat, cust_lng)
        legs.append({
            "from": cursor_label,
            "to": "موقع العميل (عودة)",
            "km": d,
            "instructions": "",
            "is_return": True,
        })
        # Return leg gets a discount
        discount = pricing["return_discount_pct"] / 100.0
        total_km += d * (1 - discount)

    distance_fee = round(total_km * pricing["per_km_sar"], 2)
    extra = pricing["errand_extra_sar"] if service_type == "errand" else 0.0
    raw_total = pricing["base_fee_sar"] + distance_fee + extra
    total = max(pricing["min_total_sar"], min(pricing["max_total_sar"], round(raw_total, 2)))

    eta = max(8, int(total_km * 2.2 + 5))  # ~2.2 min/km city avg + 5 min prep

    return {
        "distance_km": round(total_km, 2),
        "legs": legs,
        "base_fee_sar": pricing["base_fee_sar"],
        "distance_fee_sar": distance_fee,
        "extra_fee_sar": extra,
        "total_sar": total,
        "eta_minutes": eta,
    }


# ─────────────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────────────
def _merchant_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    try:
        payload = jwt.decode(authorization.split(" ", 1)[1], JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid token")
    uid = payload.get("user_id") or payload.get("sub")
    if not uid:
        raise HTTPException(401, "Invalid token payload")
    return {"id": uid, "email": payload.get("email"), "role": payload.get("role")}


# ─────────────────────────────────────────────────────────────────────────
# Public endpoints
# ─────────────────────────────────────────────────────────────────────────
@router.post("/quote", response_model=QuoteOut)
async def quote(body: QuoteIn):
    """Compute price for an external delivery without creating an order."""
    if not body.stops:
        raise HTTPException(400, "At least one stop is required")
    mid = await _resolve_merchant_id(body.merchant_id)
    pricing = await _get_pricing(mid)
    if not pricing.get("enabled", True):
        raise HTTPException(400, "External delivery is disabled for this merchant")
    branch = await _nearest_branch(mid, body.customer_lat, body.customer_lng)
    q = _compute_quote(body.stops, body.customer_lat, body.customer_lng, branch,
                       body.return_to_customer, pricing, body.service_type)
    q["nearest_branch"] = branch
    return q


@router.post("/order")
async def create_order(body: OrderIn):
    """Customer creates an external delivery order. Returns payment URL/info."""
    if not body.stops:
        raise HTTPException(400, "At least one stop is required")
    mid = await _resolve_merchant_id(body.merchant_id)
    pricing = await _get_pricing(mid)
    if not pricing.get("enabled", True):
        raise HTTPException(400, "External delivery is disabled for this merchant")

    branch = await _nearest_branch(mid, body.customer_lat, body.customer_lng)
    quote_data = _compute_quote(body.stops, body.customer_lat, body.customer_lng, branch,
                                body.return_to_customer, pricing, body.service_type)

    total = quote_data["total_sar"]
    driver_share = round(total * pricing["driver_share_pct"] / 100.0, 2)
    merchant_share = round(total - driver_share, 2)

    oid = "ext_" + uuid.uuid4().hex[:10]
    order = {
        "id": oid,
        "merchant_id": mid,
        "kind": "external",
        "service_type": body.service_type,
        "customer_name": body.customer_name,
        "customer_phone": body.customer_phone,
        "customer_lat": body.customer_lat,
        "customer_lng": body.customer_lng,
        "stops": [s.dict() for s in body.stops],
        "return_to_customer": body.return_to_customer,
        "branch_id": branch["id"] if branch else None,
        "branch_name": branch["name_ar"] if branch else None,
        "distance_km": quote_data["distance_km"],
        "legs": quote_data["legs"],
        "total_sar": total,
        "driver_share_sar": driver_share,
        "merchant_share_sar": merchant_share,
        "payment_method": body.payment_method,
        "payment_status": "paid",   # sandbox — auto-paid
        "status": "accepted" if pricing.get("auto_accept") else "pending_merchant",
        "assigned_driver_id": None,
        "notes": body.notes or "",
        "eta_minutes": quote_data["eta_minutes"],
        "created_at": _now(),
        "updated_at": _now(),
    }

    db = _db()
    await db.external_orders.insert_one(order)
    order.pop("_id", None)

    return {
        "ok": True,
        "order_id": oid,
        "total_sar": total,
        "status": order["status"],
        "payment_redirect": None,  # sandbox: no redirect, already "paid"
        "eta_minutes": quote_data["eta_minutes"],
        "branch": branch,
    }


@router.get("/order/{order_id}")
async def public_order_status(order_id: str):
    db = _db()
    o = await db.external_orders.find_one({"id": order_id})
    if not o:
        raise HTTPException(404, "Order not found")
    o.pop("_id", None)
    # Hide driver_share from public view
    o.pop("driver_share_sar", None)
    o.pop("merchant_share_sar", None)
    return o


# ─────────────────────────────────────────────────────────────────────────
# Merchant endpoints
# ─────────────────────────────────────────────────────────────────────────
@router.get("/orders")
async def merchant_orders(user=Depends(_merchant_user), status: Optional[str] = None):
    db = _db()
    q: Dict[str, Any] = {"merchant_id": user["id"]}
    if status:
        q["status"] = status
    items = await db.external_orders.find(q).sort("created_at", -1).limit(200).to_list(200)
    for o in items:
        o.pop("_id", None)
    return {"orders": items, "count": len(items)}


@router.post("/orders/{order_id}/accept")
async def accept_order(order_id: str, body: Dict[str, Any], user=Depends(_merchant_user)):
    driver_id = (body or {}).get("driver_id")
    db = _db()
    o = await db.external_orders.find_one({"id": order_id, "merchant_id": user["id"]})
    if not o:
        raise HTTPException(404, "Order not found")
    update = {
        "status": "assigned" if driver_id else "accepted",
        "assigned_driver_id": driver_id,
        "updated_at": _now(),
    }
    await db.external_orders.update_one({"id": order_id}, {"$set": update})
    return {"ok": True, "status": update["status"], "driver_id": driver_id}


@router.post("/orders/{order_id}/reject")
async def reject_order(order_id: str, body: Dict[str, Any], user=Depends(_merchant_user)):
    reason = (body or {}).get("reason", "")
    db = _db()
    o = await db.external_orders.find_one({"id": order_id, "merchant_id": user["id"]})
    if not o:
        raise HTTPException(404, "Order not found")
    await db.external_orders.update_one(
        {"id": order_id},
        {"$set": {"status": "rejected", "reject_reason": reason, "updated_at": _now()}},
    )
    return {"ok": True, "refund_required": True}


# ─────────────────────────────────────────────────────────────────────────
# Driver endpoints — sees ONLY their commission, not customer's paid total
# ─────────────────────────────────────────────────────────────────────────
@router.get("/driver/feed")
async def driver_feed(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.lower().startswith("drivertoken "):
        raise HTTPException(401, "Missing DriverToken")
    # In demo, surface all accepted external orders (in production, filter by driver_id)
    db = _db()
    items = await db.external_orders.find({"status": {"$in": ["accepted", "assigned"]}}).sort("created_at", -1).limit(50).to_list(50)
    out = []
    for o in items:
        out.append({
            "id": o["id"],
            "service_type": o.get("service_type", "delivery"),
            "customer_name": o["customer_name"],
            "customer_phone": o["customer_phone"][:6] + "****",  # masked
            "stops": o["stops"],
            "branch_name": o.get("branch_name"),
            "distance_km": o["distance_km"],
            "earnings_sar": o["driver_share_sar"],   # ← driver sees ONLY this
            "eta_minutes": o["eta_minutes"],
            "created_at": o["created_at"],
            "notes": o.get("notes", ""),
        })
    return {"orders": out, "count": len(out)}


@router.post("/driver/orders/{order_id}/take")
async def driver_take(order_id: str, authorization: Optional[str] = Header(None)):
    """Driver self-assigns an unassigned external order."""
    if not authorization or not authorization.lower().startswith("drivertoken "):
        raise HTTPException(401, "Missing DriverToken")
    token = authorization.split(" ", 1)[1]
    db = _db()
    o = await db.external_orders.find_one({"id": order_id})
    if not o:
        raise HTTPException(404, "Order not found")
    if o.get("assigned_driver_id"):
        raise HTTPException(409, "Already assigned")
    await db.external_orders.update_one(
        {"id": order_id},
        {"$set": {"assigned_driver_id": token, "status": "assigned", "updated_at": _now()}},
    )
    return {"ok": True, "earnings_sar": o["driver_share_sar"]}


@router.post("/driver/orders/{order_id}/complete")
async def driver_complete(order_id: str, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.lower().startswith("drivertoken "):
        raise HTTPException(401, "Missing DriverToken")
    db = _db()
    o = await db.external_orders.find_one({"id": order_id})
    if not o:
        raise HTTPException(404, "Order not found")
    await db.external_orders.update_one(
        {"id": order_id},
        {"$set": {"status": "delivered", "delivered_at": _now(), "updated_at": _now()}},
    )
    return {"ok": True, "earnings_sar": o["driver_share_sar"]}
