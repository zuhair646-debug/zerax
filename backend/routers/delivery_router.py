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
import math
import random
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Literal
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/delivery", tags=["delivery"])

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between 2 GPS points in km."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


# Multi-country payout methods (used to populate the driver-form dropdown)
PAYOUT_METHODS = {
    "SA": [  # Saudi Arabia
        {"id": "stc_pay",    "name_ar": "STC Pay",       "field": "phone",  "icon": "📱"},
        {"id": "mada",       "name_ar": "تحويل بنكي مدى", "field": "iban",   "icon": "🏦"},
        {"id": "urpay",      "name_ar": "urpay",          "field": "phone",  "icon": "💳"},
        {"id": "alinma_pay", "name_ar": "الإنماء Pay",     "field": "phone",  "icon": "💳"},
        {"id": "cash",       "name_ar": "كاش يدوي",        "field": "note",   "icon": "💵"},
    ],
    "AE": [  # UAE
        {"id": "payby",      "name_ar": "PayBy",          "field": "phone",  "icon": "📱"},
        {"id": "e_and",      "name_ar": "e& Money",        "field": "phone",  "icon": "📱"},
        {"id": "bank_ae",    "name_ar": "تحويل بنكي UAE",  "field": "iban",   "icon": "🏦"},
        {"id": "cash",       "name_ar": "كاش يدوي",        "field": "note",   "icon": "💵"},
    ],
    "EG": [  # Egypt
        {"id": "vodafone_cash","name_ar":"Vodafone Cash", "field": "phone",  "icon": "📱"},
        {"id": "instapay",    "name_ar":"InstaPay",       "field": "phone",  "icon": "💳"},
        {"id": "fawry",       "name_ar":"Fawry",          "field": "phone",  "icon": "🏷️"},
        {"id": "bank_eg",     "name_ar":"تحويل بنكي EG",   "field": "iban",   "icon": "🏦"},
        {"id": "cash",        "name_ar":"كاش يدوي",        "field": "note",   "icon": "💵"},
    ],
    "KW": [  # Kuwait
        {"id": "knet",        "name_ar":"KNET",           "field": "iban",   "icon": "🏦"},
        {"id": "myfatoorah",  "name_ar":"MyFatoorah",     "field": "phone",  "icon": "💳"},
        {"id": "cash",        "name_ar":"كاش يدوي",        "field": "note",   "icon": "💵"},
    ],
    "BH": [{"id":"benefit","name_ar":"BenefitPay","field":"phone","icon":"📱"},{"id":"bank","name_ar":"تحويل بنكي","field":"iban","icon":"🏦"},{"id":"cash","name_ar":"كاش","field":"note","icon":"💵"}],
    "QA": [{"id":"qpay","name_ar":"QPay","field":"phone","icon":"📱"},{"id":"bank","name_ar":"تحويل بنكي","field":"iban","icon":"🏦"},{"id":"cash","name_ar":"كاش","field":"note","icon":"💵"}],
    "OM": [{"id":"omanpay","name_ar":"OmanNet","field":"phone","icon":"📱"},{"id":"bank","name_ar":"تحويل بنكي","field":"iban","icon":"🏦"},{"id":"cash","name_ar":"كاش","field":"note","icon":"💵"}],
    "IQ": [{"id":"zaincash","name_ar":"ZainCash","field":"phone","icon":"📱"},{"id":"asia_hawala","name_ar":"AsiaHawala","field":"phone","icon":"📱"},{"id":"cash","name_ar":"كاش","field":"note","icon":"💵"}],
}
COUNTRIES = [
    {"code": "SA", "name_ar": "السعودية",  "flag": "🇸🇦", "currency": "SAR"},
    {"code": "AE", "name_ar": "الإمارات",  "flag": "🇦🇪", "currency": "AED"},
    {"code": "EG", "name_ar": "مصر",       "flag": "🇪🇬", "currency": "EGP"},
    {"code": "KW", "name_ar": "الكويت",    "flag": "🇰🇼", "currency": "KWD"},
    {"code": "BH", "name_ar": "البحرين",   "flag": "🇧🇭", "currency": "BHD"},
    {"code": "QA", "name_ar": "قطر",       "flag": "🇶🇦", "currency": "QAR"},
    {"code": "OM", "name_ar": "عُمان",     "flag": "🇴🇲", "currency": "OMR"},
    {"code": "IQ", "name_ar": "العراق",    "flag": "🇮🇶", "currency": "IQD"},
]

# ─────────────────────────────────────────────────────────────────────────────
# In-memory stores (seeded with demo data)
# ─────────────────────────────────────────────────────────────────────────────
DRIVERS: Dict[str, dict] = {}
ORDERS: Dict[str, dict] = {}
PAYOUTS: Dict[str, dict] = {}     # payout_id -> {driver_id, amount, method, account, status, created_at}
OTPS: Dict[str, dict] = {}        # phone -> {code, expires}
TOKENS: Dict[str, str] = {}       # token -> driver_id
SETTINGS = {
    "country": "SA",
    "currency": "SAR",
    "free_delivery_threshold_sar": 200,
    "base_fee_sar": 5,                # fixed pickup fee
    "per_km_sar": 1.20,               # PRICE PER KM — merchant configurable
    "min_fee_sar": 8,                 # minimum charge floor
    "max_fee_sar": 60,                # cap so very far orders aren't absurd
    "driver_share_default_pct": 80,   # commission drivers get 80% by default
    "merchant_share_default_pct": 20, # merchant keeps 20% of delivery fee
    "working_hours": {"open": "08:00", "close": "23:30"},
    "branches": [
        {"id": "br_riyadh_main",  "name_ar": "الرياض - الفرع الرئيسي", "lat": 24.7136, "lng": 46.6753, "phone": "0112000000", "is_main": True},
        {"id": "br_riyadh_north", "name_ar": "الرياض - فرع شمال",      "lat": 24.8200, "lng": 46.6200, "phone": "0112000001", "is_main": False},
    ],
    "zones": [
        {"id": "north_riyadh", "name_ar": "شمال الرياض", "fee_sar": 15, "eta_min": 30},
        {"id": "south_riyadh", "name_ar": "جنوب الرياض", "fee_sar": 18, "eta_min": 35},
        {"id": "east_riyadh",  "name_ar": "شرق الرياض",  "fee_sar": 15, "eta_min": 28},
        {"id": "west_riyadh",  "name_ar": "غرب الرياض",  "fee_sar": 20, "eta_min": 40},
        {"id": "central",      "name_ar": "وسط الرياض",  "fee_sar": 12, "eta_min": 22},
    ],
    "auto_assign": True,
    "allow_cash_on_delivery": True,
    "use_distance_pricing": True,     # if False fallback to flat per-zone fee
}

VALID_STATUS = ("pending", "assigned", "picked_up", "delivering", "delivered", "cancelled")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_demo():
    """Seed deterministic demo data on first import."""
    if DRIVERS:
        return
    demo_drivers = [
        {"name": "أحمد السبيعي",   "phone": "0501111111", "vehicle": "موتر",   "area": "north_riyadh",  "rating": 4.8, "status": "online",     "deliveries_today": 6, "employment_type": "commission", "share_per_delivery_sar": 8, "monthly_salary_sar": 0,    "payout_method": "stc_pay",   "payout_account": "0501111111", "country": "SA"},
        {"name": "خالد العتيبي",   "phone": "0552222222", "vehicle": "موتر",   "area": "east_riyadh",   "rating": 4.9, "status": "delivering", "deliveries_today": 8, "employment_type": "commission", "share_per_delivery_sar": 8, "monthly_salary_sar": 0,    "payout_method": "stc_pay",   "payout_account": "0552222222", "country": "SA"},
        {"name": "سلطان القحطاني", "phone": "0533333333", "vehicle": "دباب",   "area": "central",       "rating": 4.7, "status": "online",     "deliveries_today": 5, "employment_type": "salaried",   "share_per_delivery_sar": 0, "monthly_salary_sar": 4500, "payout_method": "mada",      "payout_account": "SA03 8000 0000 6080 1016 7519", "country": "SA"},
        {"name": "فيصل الشمري",    "phone": "0544444444", "vehicle": "موتر",   "area": "west_riyadh",   "rating": 4.8, "status": "offline",    "deliveries_today": 0, "employment_type": "commission", "share_per_delivery_sar": 7, "monthly_salary_sar": 0,    "payout_method": "urpay",     "payout_account": "0544444444", "country": "SA"},
        {"name": "بدر الدوسري",    "phone": "0555555555", "vehicle": "موتر",   "area": "south_riyadh",  "rating": 4.9, "status": "delivering", "deliveries_today": 7, "employment_type": "salaried",   "share_per_delivery_sar": 0, "monthly_salary_sar": 5000, "payout_method": "alinma_pay","payout_account": "0555555555", "country": "SA"},
    ]
    for d in demo_drivers:
        did = "drv_" + uuid.uuid4().hex[:8]
        DRIVERS[did] = {
            "id": did, **d,
            "earnings_today_sar": d["deliveries_today"] * (d.get("share_per_delivery_sar") or 8),
            "earnings_week_sar":  d["deliveries_today"] * (d.get("share_per_delivery_sar") or 8) * 6 + random.randint(80, 220),
            "balance_pending_sar": d["deliveries_today"] * (d.get("share_per_delivery_sar") or 8),
            "current_location": {"lat": 24.7 + random.random() * 0.1, "lng": 46.6 + random.random() * 0.1},
            "joined_at": _now(),
        }

    # Demo orders in various states (with real GPS coords around Riyadh)
    demo_orders = [
        {"customer": "نوف العتيبي",  "phone": "0567778888", "address": "حي النرجس، شارع الأمير سلطان", "zone": "north_riyadh",  "lat": 24.835, "lng": 46.665, "total_sar": 245, "items": [{"name": "iPhone 17 Pro", "qty": 1, "sar": 245}], "status": "delivered"},
        {"customer": "خالد المطيري", "phone": "0561234567", "address": "حي العليا، شارع التحلية",       "zone": "central",       "lat": 24.706, "lng": 46.678, "total_sar": 89,  "items": [{"name": "سماعات AirPods", "qty": 1, "sar": 89}], "status": "delivering"},
        {"customer": "ريم القحطاني",  "phone": "0578889999", "address": "حي الياسمين، شارع 60",         "zone": "north_riyadh",  "lat": 24.852, "lng": 46.640, "total_sar": 320, "items": [{"name": "ساعة Apple Watch", "qty": 1, "sar": 320}], "status": "assigned"},
        {"customer": "محمد الزهراني", "phone": "0533123456", "address": "حي الحمراء، شارع الستين",      "zone": "east_riyadh",   "lat": 24.740, "lng": 46.795, "total_sar": 145, "items": [{"name": "حقيبة ظهر", "qty": 1, "sar": 145}], "status": "pending"},
        {"customer": "سارة العنزي",  "phone": "0598765432", "address": "حي السويدي، شارع الأربعين",    "zone": "south_riyadh",  "lat": 24.615, "lng": 46.690, "total_sar": 67,  "items": [{"name": "سماعات لاسلكية", "qty": 1, "sar": 67}], "status": "pending"},
    ]
    main_branch = SETTINGS["branches"][0]
    driver_ids = list(DRIVERS.keys())
    for i, o in enumerate(demo_orders):
        oid = "ord_" + uuid.uuid4().hex[:8]
        zone = next((z for z in SETTINGS["zones"] if z["id"] == o["zone"]), SETTINGS["zones"][0])
        distance_km = haversine_km(main_branch["lat"], main_branch["lng"], o["lat"], o["lng"])
        # Apply per-km pricing with floor/cap
        if o["total_sar"] >= SETTINGS["free_delivery_threshold_sar"]:
            fee = 0
        else:
            raw = SETTINGS["base_fee_sar"] + distance_km * SETTINGS["per_km_sar"]
            fee = round(max(SETTINGS["min_fee_sar"], min(SETTINGS["max_fee_sar"], raw)), 2)

        st = o["status"]
        assigned_drv = None
        if st in ("assigned", "picked_up", "delivering", "delivered"):
            in_zone = [d for d in DRIVERS.values() if d["area"] == o["zone"]]
            assigned_drv = (in_zone or [DRIVERS[driver_ids[i % len(driver_ids)]]])[0]
            assigned_drv = assigned_drv["id"]

        # Driver/merchant share computation
        drv_data = DRIVERS.get(assigned_drv) if assigned_drv else None
        driver_share = 0.0
        merchant_share = float(fee)
        if drv_data and fee > 0:
            if drv_data["employment_type"] == "commission":
                driver_share = float(drv_data.get("share_per_delivery_sar") or round(fee * SETTINGS["driver_share_default_pct"] / 100, 2))
                merchant_share = round(fee - driver_share, 2)
            else:
                # Salaried drivers don't take a per-delivery cut — merchant keeps all
                driver_share = 0.0
                merchant_share = float(fee)

        ORDERS[oid] = {
            "id": oid,
            "branch_id": main_branch["id"],
            "customer_name": o["customer"],
            "customer_phone": o["phone"],
            "address": o["address"],
            "customer_lat": o["lat"],
            "customer_lng": o["lng"],
            "zone": o["zone"],
            "distance_km": distance_km,
            "total_sar": o["total_sar"],
            "delivery_fee_sar": fee,
            "driver_share_sar": driver_share,
            "merchant_share_sar": merchant_share,
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
    employment_type: Literal["salaried", "commission"] = "commission"
    share_per_delivery_sar: float = 8.0
    monthly_salary_sar: float = 0.0
    payout_method: str = "stc_pay"
    payout_account: str = ""
    country: str = "SA"


class DriverPatch(BaseModel):
    name: Optional[str] = None
    vehicle: Optional[str] = None
    area: Optional[str] = None
    status: Optional[Literal["online", "offline", "delivering"]] = None
    employment_type: Optional[Literal["salaried", "commission"]] = None
    share_per_delivery_sar: Optional[float] = None
    monthly_salary_sar: Optional[float] = None
    payout_method: Optional[str] = None
    payout_account: Optional[str] = None


class OrderItem(BaseModel):
    name: str
    qty: int = 1
    sar: float = 0


class OrderIn(BaseModel):
    customer_name: str
    customer_phone: str
    address: str
    customer_lat: Optional[float] = None
    customer_lng: Optional[float] = None
    zone: str = "central"
    branch_id: Optional[str] = None
    items: List[OrderItem]
    total_sar: float
    payment_method: Literal["cash", "card", "wallet"] = "cash"
    notes: str = ""


class CalcFeeIn(BaseModel):
    branch_id: Optional[str] = None
    customer_lat: float
    customer_lng: float
    total_sar: float = 0


class BranchIn(BaseModel):
    name_ar: str
    lat: float
    lng: float
    phone: str = ""
    is_main: bool = False


class PayoutIn(BaseModel):
    driver_id: str
    amount_sar: float
    method: Optional[str] = None     # overrides driver default if set
    account: Optional[str] = None
    note: str = ""


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
def _compute_fee(branch_id: Optional[str], cust_lat: Optional[float], cust_lng: Optional[float], total_sar: float):
    """Returns (distance_km, fee_sar). Free if total >= threshold OR coords missing."""
    branch = None
    if branch_id:
        branch = next((b for b in SETTINGS["branches"] if b["id"] == branch_id), None)
    if not branch:
        branch = next((b for b in SETTINGS["branches"] if b.get("is_main")), SETTINGS["branches"][0])

    distance = 0.0
    if cust_lat is not None and cust_lng is not None:
        distance = haversine_km(branch["lat"], branch["lng"], cust_lat, cust_lng)

    if total_sar >= SETTINGS["free_delivery_threshold_sar"] and SETTINGS["free_delivery_threshold_sar"] > 0:
        return distance, 0.0

    if SETTINGS.get("use_distance_pricing", True) and distance > 0:
        raw = SETTINGS["base_fee_sar"] + distance * SETTINGS["per_km_sar"]
        fee = round(max(SETTINGS["min_fee_sar"], min(SETTINGS["max_fee_sar"], raw)), 2)
    else:
        # fallback to flat zone fee — handled by caller
        fee = SETTINGS["min_fee_sar"]
    return distance, fee


def _compute_shares(fee: float, driver: Optional[dict]):
    """Returns (driver_share, merchant_share) based on driver employment type."""
    if not driver or fee <= 0:
        return 0.0, float(fee)
    if driver["employment_type"] == "commission":
        ds = float(driver.get("share_per_delivery_sar") or round(fee * SETTINGS["driver_share_default_pct"] / 100, 2))
        ds = min(ds, fee)  # never exceed total fee
        return ds, round(fee - ds, 2)
    return 0.0, float(fee)  # salaried


def _auto_assign_driver(zone: str, cust_lat: Optional[float] = None, cust_lng: Optional[float] = None, max_active: int = 3) -> Optional[str]:
    """
    Pick best driver: prefer drivers in the same zone with FEWER than max_active deliveries.
    Tie-breaker: closest to customer location (or branch if no customer coords).
    Drivers can carry multiple orders (up to max_active by default).
    """
    available = [d for d in DRIVERS.values() if d["status"] in ("online", "delivering")]
    if not available:
        return None

    # Count each driver's current active orders
    active_count = {d["id"]: sum(1 for o in ORDERS.values() if o.get("driver_id") == d["id"] and o["status"] not in ("delivered", "cancelled")) for d in available}
    eligible = [d for d in available if active_count[d["id"]] < max_active]
    if not eligible:
        return None

    # Prefer same zone
    same_zone = [d for d in eligible if d["area"] == zone]
    pool = same_zone or eligible

    # Sort by distance (if coords) then by load
    def score(d):
        load = active_count[d["id"]]
        if cust_lat is None or cust_lng is None or not d.get("current_location"):
            return (load, 0)
        dist = haversine_km(d["current_location"]["lat"], d["current_location"]["lng"], cust_lat, cust_lng)
        return (load, dist)
    pool.sort(key=score)
    return pool[0]["id"]


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
    branch_id = payload.branch_id or (next((b["id"] for b in SETTINGS["branches"] if b.get("is_main")), SETTINGS["branches"][0]["id"]))
    distance, fee = _compute_fee(branch_id, payload.customer_lat, payload.customer_lng, payload.total_sar)
    # If no coords (distance=0) fall back to zone fee
    if distance == 0 and fee == SETTINGS["min_fee_sar"] and not SETTINGS.get("use_distance_pricing", True):
        fee = 0 if payload.total_sar >= SETTINGS["free_delivery_threshold_sar"] else zone["fee_sar"]

    drv_id = _auto_assign_driver(payload.zone, payload.customer_lat, payload.customer_lng) if SETTINGS["auto_assign"] else None
    status = "assigned" if drv_id else "pending"
    log = [{"status": "pending", "at": _now()}]
    if drv_id:
        log.append({"status": "assigned", "at": _now()})

    drv_data = DRIVERS.get(drv_id) if drv_id else None
    driver_share, merchant_share = _compute_shares(fee, drv_data)

    ORDERS[oid] = {
        "id": oid,
        "branch_id": branch_id,
        "customer_name": payload.customer_name,
        "customer_phone": payload.customer_phone,
        "address": payload.address,
        "customer_lat": payload.customer_lat,
        "customer_lng": payload.customer_lng,
        "zone": payload.zone,
        "distance_km": distance,
        "total_sar": payload.total_sar,
        "delivery_fee_sar": fee,
        "driver_share_sar": driver_share,
        "merchant_share_sar": merchant_share,
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
            earn = float(o.get("driver_share_sar") or 0)
            # Salaried drivers don't earn per delivery — but still count the delivery
            if d.get("employment_type") == "commission":
                d["earnings_today_sar"] = round(d.get("earnings_today_sar", 0) + earn, 2)
                d["earnings_week_sar"]  = round(d.get("earnings_week_sar", 0) + earn, 2)
                d["balance_pending_sar"] = round(d.get("balance_pending_sar", 0) + earn, 2)
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
    return {"status": "ok", "drivers": len(DRIVERS), "orders": len(ORDERS), "zones": len(SETTINGS["zones"]), "branches": len(SETTINGS["branches"])}


# ═════════════════════════════════════════════════════════════════════════════
# BRANCHES
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/branches")
async def list_branches():
    return {"branches": SETTINGS["branches"]}


@router.post("/branches")
async def create_branch(payload: BranchIn):
    bid = "br_" + uuid.uuid4().hex[:8]
    branch = {"id": bid, **payload.model_dump()}
    if branch["is_main"]:
        for b in SETTINGS["branches"]:
            b["is_main"] = False
    SETTINGS["branches"].append(branch)
    return branch


@router.delete("/branches/{branch_id}")
async def delete_branch(branch_id: str):
    before = len(SETTINGS["branches"])
    SETTINGS["branches"] = [b for b in SETTINGS["branches"] if b["id"] != branch_id]
    if len(SETTINGS["branches"]) == before:
        raise HTTPException(status_code=404, detail="branch not found")
    return {"ok": True, "id": branch_id}


# ═════════════════════════════════════════════════════════════════════════════
# FEE CALCULATOR (distance-based)
# ═════════════════════════════════════════════════════════════════════════════
@router.post("/calculate-fee")
async def calculate_fee(payload: CalcFeeIn):
    """Pure calculator — does not create an order. Used by frontend to show
    real-time fee breakdown as customer/merchant enters delivery address."""
    distance, fee = _compute_fee(payload.branch_id, payload.customer_lat, payload.customer_lng, payload.total_sar)
    # Mock a default commission split (driver_share_default_pct)
    driver_share = round(fee * SETTINGS["driver_share_default_pct"] / 100, 2) if fee > 0 else 0
    merchant_share = round(fee - driver_share, 2) if fee > 0 else 0
    return {
        "distance_km": distance,
        "fee_sar": fee,
        "is_free": fee == 0,
        "free_threshold_sar": SETTINGS["free_delivery_threshold_sar"],
        "base_fee_sar": SETTINGS["base_fee_sar"],
        "per_km_sar": SETTINGS["per_km_sar"],
        "min_fee_sar": SETTINGS["min_fee_sar"],
        "max_fee_sar": SETTINGS["max_fee_sar"],
        "driver_share_sar": driver_share,
        "merchant_share_sar": merchant_share,
        "currency": SETTINGS["currency"],
    }


# ═════════════════════════════════════════════════════════════════════════════
# PAYOUTS (driver wage transfers)
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/payouts")
async def list_payouts(driver_id: Optional[str] = None, limit: int = 50):
    items = list(PAYOUTS.values())
    if driver_id:
        items = [p for p in items if p["driver_id"] == driver_id]
    items.sort(key=lambda p: p["created_at"], reverse=True)
    return {"payouts": items[:limit], "count": len(items)}


@router.post("/payouts")
async def create_payout(payload: PayoutIn):
    drv = DRIVERS.get(payload.driver_id)
    if not drv:
        raise HTTPException(status_code=404, detail="driver not found")
    if payload.amount_sar <= 0:
        raise HTTPException(status_code=400, detail="amount must be > 0")
    pid = "pay_" + uuid.uuid4().hex[:10]
    method = payload.method or drv.get("payout_method", "stc_pay")
    account = payload.account or drv.get("payout_account", "")
    PAYOUTS[pid] = {
        "id": pid,
        "driver_id": payload.driver_id,
        "driver_name": drv["name"],
        "amount_sar": round(payload.amount_sar, 2),
        "method": method,
        "account": account,
        "status": "completed",
        "note": payload.note,
        "created_at": _now(),
        "reference": "ZRX-" + uuid.uuid4().hex[:8].upper(),
    }
    # Decrement pending balance for commission drivers
    if drv.get("employment_type") == "commission":
        drv["balance_pending_sar"] = round(max(0, drv.get("balance_pending_sar", 0) - payload.amount_sar), 2)
    return PAYOUTS[pid]


# ═════════════════════════════════════════════════════════════════════════════
# PAYOUT METHODS (multi-country)
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/payout-methods")
async def get_payout_methods(country: str = "SA"):
    methods = PAYOUT_METHODS.get(country.upper(), PAYOUT_METHODS["SA"])
    return {"country": country.upper(), "methods": methods}


@router.get("/countries")
async def get_countries():
    return {"countries": COUNTRIES}
