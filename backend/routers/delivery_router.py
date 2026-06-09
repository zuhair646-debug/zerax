"""
Zerax Delivery & Driver Management
-----------------------------------
Three-sided delivery system: merchant ↔ driver ↔ customer.

Endpoints (all under /api/delivery/*):
  Drivers:
    GET    /drivers                  — list (optional ?store=)
    POST   /drivers                  — create / upsert
    PATCH  /drivers/{id}             — update (status, availability, area)
    DELETE /drivers/{id}             — remove
  Driver auth (demo):
    POST   /driver/login             — by phone (auto-creates demo OTP)
    POST   /driver/verify-otp        — exchange OTP for token
    GET    /driver/me                — get current driver (by token)
  Orders:
    GET    /orders                   — list (filters: status, driver_id, store)
    POST   /orders                   — create new delivery order
    GET    /orders/{id}              — single order
    PATCH  /orders/{id}/assign       — assign driver
    PATCH  /orders/{id}/status       — change status
    POST   /orders/{id}/location     — driver pings GPS coord
    GET    /orders/{id}/track        — public customer tracking
  Settings:
    GET    /settings                 — zones, fees, free-threshold, hours
    PATCH  /settings                 — update settings
    GET    /stats                    — quick aggregate stats for ACP

In-memory storage keeps the demo deterministic and instant; can be swapped
for a Mongo backend without changing the route contracts.
"""
import uuid
import random
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Literal
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/delivery", tags=["delivery"])

# ─────────────────────────────────────────────────────────────────────────────
# In-memory stores (seeded with demo data)
# ─────────────────────────────────────────────────────────────────────────────
DRIVERS: Dict[str, dict] = {}
ORDERS: Dict[str, dict] = {}
OTPS: Dict[str, dict] = {}        # phone -> {code, expires}
TOKENS: Dict[str, str] = {}       # token -> driver_id
SETTINGS = {
    "free_delivery_threshold_sar": 200,
    "base_fee_sar": 15,
    "per_km_sar": 2,
    "working_hours": {"open": "08:00", "close": "23:30"},
    "zones": [
        {"id": "north_riyadh", "name_ar": "شمال الرياض", "fee_sar": 15, "eta_min": 30},
        {"id": "south_riyadh", "name_ar": "جنوب الرياض", "fee_sar": 18, "eta_min": 35},
        {"id": "east_riyadh",  "name_ar": "شرق الرياض",  "fee_sar": 15, "eta_min": 28},
        {"id": "west_riyadh",  "name_ar": "غرب الرياض",  "fee_sar": 20, "eta_min": 40},
        {"id": "central",      "name_ar": "وسط الرياض",  "fee_sar": 12, "eta_min": 22},
    ],
    "auto_assign": True,
    "allow_cash_on_delivery": True,
}

VALID_STATUS = ("pending", "assigned", "picked_up", "delivering", "delivered", "cancelled")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_demo():
    """Seed deterministic demo data on first import."""
    if DRIVERS:
        return
    demo_drivers = [
        {"name": "أحمد السبيعي",   "phone": "0501111111", "vehicle": "موتر",   "area": "north_riyadh",  "rating": 4.8, "status": "online",   "deliveries_today": 6},
        {"name": "خالد العتيبي",   "phone": "0552222222", "vehicle": "موتر",   "area": "east_riyadh",   "rating": 4.9, "status": "delivering", "deliveries_today": 8},
        {"name": "سلطان القحطاني", "phone": "0533333333", "vehicle": "دباب",   "area": "central",       "rating": 4.7, "status": "online",   "deliveries_today": 5},
        {"name": "فيصل الشمري",    "phone": "0544444444", "vehicle": "موتر",   "area": "west_riyadh",   "rating": 4.8, "status": "offline",  "deliveries_today": 0},
        {"name": "بدر الدوسري",    "phone": "0555555555", "vehicle": "موتر",   "area": "south_riyadh",  "rating": 4.9, "status": "delivering", "deliveries_today": 7},
    ]
    for d in demo_drivers:
        did = "drv_" + uuid.uuid4().hex[:8]
        DRIVERS[did] = {
            "id": did, **d,
            "earnings_today_sar": d["deliveries_today"] * 18,
            "earnings_week_sar":  d["deliveries_today"] * 18 * 6 + random.randint(80, 220),
            "current_location": {"lat": 24.7 + random.random() * 0.1, "lng": 46.6 + random.random() * 0.1},
            "joined_at": _now(),
        }

    # Demo orders in various states
    demo_orders = [
        {"customer": "نوف العتيبي",  "phone": "0567778888", "address": "حي النرجس، شارع الأمير سلطان", "zone": "north_riyadh",  "total_sar": 245, "items": [{"name": "iPhone 17 Pro", "qty": 1, "sar": 245}], "status": "delivered"},
        {"customer": "خالد المطيري", "phone": "0561234567", "address": "حي العليا، شارع التحلية",       "zone": "central",       "total_sar": 89,  "items": [{"name": "سماعات AirPods", "qty": 1, "sar": 89}], "status": "delivering"},
        {"customer": "ريم القحطاني",  "phone": "0578889999", "address": "حي الياسمين، شارع 60",         "zone": "north_riyadh",  "total_sar": 320, "items": [{"name": "ساعة Apple Watch", "qty": 1, "sar": 320}], "status": "assigned"},
        {"customer": "محمد الزهراني", "phone": "0533123456", "address": "حي الحمراء، شارع الستين",      "zone": "east_riyadh",   "total_sar": 145, "items": [{"name": "حقيبة ظهر", "qty": 1, "sar": 145}], "status": "pending"},
        {"customer": "سارة العنزي",  "phone": "0598765432", "address": "حي السويدي، شارع الأربعين",    "zone": "south_riyadh",  "total_sar": 67,  "items": [{"name": "سماعات لاسلكية", "qty": 1, "sar": 67}], "status": "pending"},
    ]
    driver_ids = list(DRIVERS.keys())
    for i, o in enumerate(demo_orders):
        oid = "ord_" + uuid.uuid4().hex[:8]
        zone = next((z for z in SETTINGS["zones"] if z["id"] == o["zone"]), SETTINGS["zones"][0])
        st = o["status"]
        assigned_drv = None
        if st in ("assigned", "picked_up", "delivering", "delivered"):
            # pick a driver in same zone if available
            in_zone = [d for d in DRIVERS.values() if d["area"] == o["zone"]]
            assigned_drv = (in_zone or driver_ids and [DRIVERS[driver_ids[i % len(driver_ids)]]])[0]
            assigned_drv = assigned_drv["id"] if isinstance(assigned_drv, dict) else assigned_drv
        ORDERS[oid] = {
            "id": oid,
            "customer_name": o["customer"],
            "customer_phone": o["phone"],
            "address": o["address"],
            "zone": o["zone"],
            "total_sar": o["total_sar"],
            "delivery_fee_sar": 0 if o["total_sar"] >= SETTINGS["free_delivery_threshold_sar"] else zone["fee_sar"],
            "items": o["items"],
            "status": st,
            "driver_id": assigned_drv,
            "payment_method": "cash" if i % 2 == 0 else "card",
            "eta_min": zone["eta_min"],
            "created_at": _now(),
            "updated_at": _now(),
            "status_log": [{"status": "pending", "at": _now()}] +
                          ([{"status": "assigned", "at": _now()}] if st != "pending" else []),
            "current_location": {"lat": 24.7 + random.random() * 0.1, "lng": 46.6 + random.random() * 0.1} if st == "delivering" else None,
            "rating": 5 if st == "delivered" else None,
            "notes": "",
        }


_seed_demo()


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────
class DriverIn(BaseModel):
    name: str
    phone: str
    vehicle: str = "موتر"
    area: str = "central"
    status: Literal["online", "offline", "delivering"] = "online"


class DriverPatch(BaseModel):
    name: Optional[str] = None
    vehicle: Optional[str] = None
    area: Optional[str] = None
    status: Optional[Literal["online", "offline", "delivering"]] = None


class OrderItem(BaseModel):
    name: str
    qty: int = 1
    sar: float = 0


class OrderIn(BaseModel):
    customer_name: str
    customer_phone: str
    address: str
    zone: str = "central"
    items: List[OrderItem]
    total_sar: float
    payment_method: Literal["cash", "card", "wallet"] = "cash"
    notes: str = ""


class AssignIn(BaseModel):
    driver_id: str


class StatusIn(BaseModel):
    status: Literal["pending", "assigned", "picked_up", "delivering", "delivered", "cancelled"]


class LocationIn(BaseModel):
    lat: float
    lng: float


class LoginIn(BaseModel):
    phone: str


class VerifyIn(BaseModel):
    phone: str
    code: str


class SettingsPatch(BaseModel):
    free_delivery_threshold_sar: Optional[float] = None
    base_fee_sar: Optional[float] = None
    per_km_sar: Optional[float] = None
    auto_assign: Optional[bool] = None
    allow_cash_on_delivery: Optional[bool] = None


# ═════════════════════════════════════════════════════════════════════════════
# DRIVERS
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/drivers")
async def list_drivers(status: Optional[str] = None, area: Optional[str] = None):
    items = list(DRIVERS.values())
    if status:
        items = [d for d in items if d["status"] == status]
    if area:
        items = [d for d in items if d["area"] == area]
    return {"drivers": items, "count": len(items)}


@router.post("/drivers")
async def create_driver(payload: DriverIn):
    # If phone already exists, update; else create
    existing = next((d for d in DRIVERS.values() if d["phone"] == payload.phone), None)
    if existing:
        existing.update(payload.model_dump())
        return existing
    did = "drv_" + uuid.uuid4().hex[:8]
    DRIVERS[did] = {
        "id": did, **payload.model_dump(),
        "rating": 5.0,
        "deliveries_today": 0,
        "earnings_today_sar": 0,
        "earnings_week_sar": 0,
        "current_location": None,
        "joined_at": _now(),
    }
    return DRIVERS[did]


@router.patch("/drivers/{driver_id}")
async def update_driver(driver_id: str, payload: DriverPatch):
    d = DRIVERS.get(driver_id)
    if not d:
        raise HTTPException(status_code=404, detail="driver not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        d[k] = v
    return d


@router.delete("/drivers/{driver_id}")
async def delete_driver(driver_id: str):
    if driver_id not in DRIVERS:
        raise HTTPException(status_code=404, detail="driver not found")
    # unassign from active orders
    for o in ORDERS.values():
        if o.get("driver_id") == driver_id and o["status"] not in ("delivered", "cancelled"):
            o["driver_id"] = None
            o["status"] = "pending"
    del DRIVERS[driver_id]
    return {"ok": True, "id": driver_id}


# ═════════════════════════════════════════════════════════════════════════════
# DRIVER AUTH (demo OTP)
# ═════════════════════════════════════════════════════════════════════════════
@router.post("/driver/login")
async def driver_login(payload: LoginIn):
    drv = next((d for d in DRIVERS.values() if d["phone"] == payload.phone), None)
    if not drv:
        raise HTTPException(status_code=404, detail="رقم الجوال غير مسجل كسائق")
    code = "1234"  # deterministic demo OTP — easy to test
    OTPS[payload.phone] = {"code": code, "expires": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()}
    return {"ok": True, "demo_code": code, "message": "رمز OTP أُرسل (للتجربة: 1234)"}


@router.post("/driver/verify-otp")
async def verify_otp(payload: VerifyIn):
    rec = OTPS.get(payload.phone)
    if not rec or rec["code"] != payload.code:
        raise HTTPException(status_code=401, detail="رمز OTP غير صحيح")
    drv = next((d for d in DRIVERS.values() if d["phone"] == payload.phone), None)
    if not drv:
        raise HTTPException(status_code=404, detail="السائق غير موجود")
    token = "drvtok_" + uuid.uuid4().hex
    TOKENS[token] = drv["id"]
    return {"token": token, "driver": drv}


def _resolve_driver(authorization: Optional[str]) -> dict:
    if not authorization or not authorization.startswith("DriverToken "):
        raise HTTPException(status_code=401, detail="مطلوب توكن السائق")
    tok = authorization.split(" ", 1)[1]
    did = TOKENS.get(tok)
    if not did or did not in DRIVERS:
        raise HTTPException(status_code=401, detail="توكن غير صالح")
    return DRIVERS[did]


@router.get("/driver/me")
async def driver_me(authorization: Optional[str] = Header(default=None)):
    drv = _resolve_driver(authorization)
    return drv


@router.get("/driver/feed")
async def driver_feed(authorization: Optional[str] = Header(default=None)):
    """Active + completed-today orders for the logged-in driver."""
    drv = _resolve_driver(authorization)
    mine = [o for o in ORDERS.values() if o.get("driver_id") == drv["id"]]
    active = [o for o in mine if o["status"] not in ("delivered", "cancelled")]
    done_today = [o for o in mine if o["status"] == "delivered"]
    return {
        "driver": drv,
        "active": sorted(active, key=lambda o: o["created_at"]),
        "done_today": done_today,
        "summary": {
            "deliveries_today": len(done_today) + len(active),
            "earnings_today_sar": drv.get("earnings_today_sar", 0),
            "earnings_week_sar":  drv.get("earnings_week_sar", 0),
            "rating": drv.get("rating", 5.0),
        }
    }


# ═════════════════════════════════════════════════════════════════════════════
# ORDERS
# ═════════════════════════════════════════════════════════════════════════════
def _auto_assign_driver(zone: str) -> Optional[str]:
    candidates = [d for d in DRIVERS.values() if d["status"] == "online" and d["area"] == zone]
    if not candidates:
        candidates = [d for d in DRIVERS.values() if d["status"] == "online"]
    if not candidates:
        return None
    # pick driver with fewest active deliveries
    active_count = {d["id"]: sum(1 for o in ORDERS.values() if o.get("driver_id") == d["id"] and o["status"] not in ("delivered", "cancelled")) for d in candidates}
    return min(candidates, key=lambda d: active_count[d["id"]])["id"]


@router.get("/orders")
async def list_orders(status: Optional[str] = None, driver_id: Optional[str] = None, limit: int = 50):
    items = list(ORDERS.values())
    if status:
        items = [o for o in items if o["status"] == status]
    if driver_id:
        items = [o for o in items if o.get("driver_id") == driver_id]
    items.sort(key=lambda o: o["created_at"], reverse=True)
    return {"orders": items[:limit], "count": len(items)}


@router.post("/orders")
async def create_order(payload: OrderIn):
    oid = "ord_" + uuid.uuid4().hex[:8]
    zone = next((z for z in SETTINGS["zones"] if z["id"] == payload.zone), SETTINGS["zones"][0])
    fee = 0 if payload.total_sar >= SETTINGS["free_delivery_threshold_sar"] else zone["fee_sar"]
    drv_id = _auto_assign_driver(payload.zone) if SETTINGS["auto_assign"] else None
    status = "assigned" if drv_id else "pending"
    log = [{"status": "pending", "at": _now()}]
    if drv_id:
        log.append({"status": "assigned", "at": _now()})
    ORDERS[oid] = {
        "id": oid,
        "customer_name": payload.customer_name,
        "customer_phone": payload.customer_phone,
        "address": payload.address,
        "zone": payload.zone,
        "total_sar": payload.total_sar,
        "delivery_fee_sar": fee,
        "items": [it.model_dump() for it in payload.items],
        "status": status,
        "driver_id": drv_id,
        "payment_method": payload.payment_method,
        "eta_min": zone["eta_min"],
        "created_at": _now(),
        "updated_at": _now(),
        "status_log": log,
        "current_location": None,
        "rating": None,
        "notes": payload.notes,
    }
    return ORDERS[oid]


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    o = ORDERS.get(order_id)
    if not o:
        raise HTTPException(status_code=404, detail="order not found")
    return o


@router.patch("/orders/{order_id}/assign")
async def assign_order(order_id: str, payload: AssignIn):
    o = ORDERS.get(order_id)
    if not o:
        raise HTTPException(status_code=404, detail="order not found")
    if payload.driver_id not in DRIVERS:
        raise HTTPException(status_code=404, detail="driver not found")
    o["driver_id"] = payload.driver_id
    if o["status"] == "pending":
        o["status"] = "assigned"
        o["status_log"].append({"status": "assigned", "at": _now()})
    o["updated_at"] = _now()
    return o


@router.patch("/orders/{order_id}/status")
async def update_order_status(order_id: str, payload: StatusIn, authorization: Optional[str] = Header(default=None)):
    o = ORDERS.get(order_id)
    if not o:
        raise HTTPException(status_code=404, detail="order not found")
    # if driver auth header is present, only allow the assigned driver to change
    if authorization and authorization.startswith("DriverToken "):
        drv = _resolve_driver(authorization)
        if o.get("driver_id") != drv["id"]:
            raise HTTPException(status_code=403, detail="هذا الطلب غير مخصص لك")
    o["status"] = payload.status
    o["status_log"].append({"status": payload.status, "at": _now()})
    o["updated_at"] = _now()
    if payload.status == "delivered" and o.get("driver_id"):
        d = DRIVERS.get(o["driver_id"])
        if d:
            d["deliveries_today"] = d.get("deliveries_today", 0) + 1
            d["earnings_today_sar"] = d.get("earnings_today_sar", 0) + 18  # SAR per delivery
            d["earnings_week_sar"] = d.get("earnings_week_sar", 0) + 18
    return o


@router.post("/orders/{order_id}/location")
async def update_location(order_id: str, payload: LocationIn, authorization: Optional[str] = Header(default=None)):
    o = ORDERS.get(order_id)
    if not o:
        raise HTTPException(status_code=404, detail="order not found")
    o["current_location"] = {"lat": payload.lat, "lng": payload.lng, "at": _now()}
    if authorization and authorization.startswith("DriverToken "):
        drv = _resolve_driver(authorization)
        drv["current_location"] = {"lat": payload.lat, "lng": payload.lng}
    return {"ok": True, "location": o["current_location"]}


@router.get("/orders/{order_id}/track")
async def public_track(order_id: str):
    """Public tracking endpoint (no auth) for the customer."""
    o = ORDERS.get(order_id)
    if not o:
        raise HTTPException(status_code=404, detail="طلب غير موجود")
    drv = DRIVERS.get(o.get("driver_id")) if o.get("driver_id") else None
    return {
        "id": o["id"],
        "status": o["status"],
        "status_log": o["status_log"],
        "eta_min": o["eta_min"],
        "address": o["address"],
        "items": o["items"],
        "total_sar": o["total_sar"],
        "delivery_fee_sar": o["delivery_fee_sar"],
        "current_location": o.get("current_location"),
        "driver": {
            "name": drv["name"],
            "phone": drv["phone"],
            "vehicle": drv.get("vehicle", "موتر"),
            "rating": drv.get("rating", 5.0),
        } if drv else None,
    }


# ═════════════════════════════════════════════════════════════════════════════
# SETTINGS + STATS
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/settings")
async def get_settings():
    return SETTINGS


@router.patch("/settings")
async def update_settings(payload: SettingsPatch):
    for k, v in payload.model_dump(exclude_none=True).items():
        SETTINGS[k] = v
    return SETTINGS


@router.get("/stats")
async def stats():
    by_status = {s: 0 for s in VALID_STATUS}
    total_today_sar = 0.0
    active_drivers = 0
    for o in ORDERS.values():
        by_status[o["status"]] = by_status.get(o["status"], 0) + 1
        if o["status"] == "delivered":
            total_today_sar += float(o.get("delivery_fee_sar", 0)) + float(o.get("total_sar", 0))
    for d in DRIVERS.values():
        if d["status"] in ("online", "delivering"):
            active_drivers += 1
    return {
        "by_status": by_status,
        "active_drivers": active_drivers,
        "total_drivers": len(DRIVERS),
        "total_orders": len(ORDERS),
        "revenue_today_sar": round(total_today_sar, 2),
    }


@router.get("/health")
async def health():
    return {"status": "ok", "drivers": len(DRIVERS), "orders": len(ORDERS), "zones": len(SETTINGS["zones"])}
