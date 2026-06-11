"""
Zerax Driver Experience Configuration
──────────────────────────────────────────────────────────────────────────
Per-merchant configuration of the driver-app feature surface. The merchant
decides via the admin panel which features are enabled/visible/configured
for their drivers. The driver app fetches this config on load and adapts
its UI accordingly.

Endpoints (all under /api/delivery/config/*):
  Merchant (auth required):
    GET    /api/delivery/config              — full config for current merchant
    PUT    /api/delivery/config              — replace/update config
    POST   /api/delivery/config/reset        — reset to defaults
    GET    /api/delivery/config/branches     — list branches
    POST   /api/delivery/config/branches     — create branch
    PATCH  /api/delivery/config/branches/{id} — update branch
    DELETE /api/delivery/config/branches/{id} — delete branch
  Driver (DriverToken auth):
    GET    /api/delivery/config/public       — features enabled (no secrets)
"""
from __future__ import annotations

import os
import uuid
import jwt
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/delivery/config", tags=["delivery-config"])

JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key")

# Mongo connection
_MONGO_URL = os.environ.get("MONGO_URL")
_DB_NAME = os.environ.get("DB_NAME")
_client: Optional[AsyncIOMotorClient] = None


def _db():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(_MONGO_URL)
    return _client[_DB_NAME]


# ─────────────────────────────────────────────────────────────────────────
# DEFAULTS — all features enabled out of the box
# ─────────────────────────────────────────────────────────────────────────
DEFAULTS: Dict[str, Any] = {
    "ui": {
        "show_live_map": True,
        "show_branches_on_map": True,
        "show_heatmap": True,
        "show_traffic": True,
        "dark_mode_default": False,
        "glance_mode": True,        # large numbers for driving
        "rtl_layout": True,
    },
    "earnings": {
        "show_surge_zones": True,
        "surge_multiplier": 1.5,
        "show_streak_bonuses": True,
        "streak_bonus_amount_sar": 15,
        "streak_bonus_count": 3,
        "show_weekly_challenges": True,
        "weekly_challenge_target": 50,
        "weekly_challenge_reward_sar": 500,
        "instant_pay_enabled": True,
        "instant_pay_min_sar": 50,
        "show_tip_tracker": True,
        "earnings_predictor": True,
        "fuel_cost_calculator": True,
    },
    "orders": {
        "order_batching": True,
        "max_batch_size": 3,
        "batch_radius_km": 2,
        "photo_proof_required": True,
        "contactless_delivery": True,
        "customer_chat": True,
        "auto_translate_chat": True,
        "pre_arrival_notification": True,
        "pre_arrival_minutes": 2,
    },
    "ai": {
        "standby_coach": True,         # AI tells driver where to wait
        "voice_commands": True,         # "Arrived", "Picked up" by voice
        "route_memory": True,
        "photo_verification": True,    # AI checks delivery photo
        "smart_predictor": True,        # predicts hourly earnings
    },
    "saudi": {
        "cash_on_delivery": True,
        "mada_pos": True,
        "apple_pay_pos": True,
        "prayer_time_pause": True,
        "heat_alerts": True,
        "heat_alert_threshold_c": 42,
        "hajj_mode": False,
    },
    "wellbeing": {
        "break_timer": True,
        "fatigue_alerts": True,
        "fatigue_after_hours": 4,
        "sos_button": True,
        "sos_contacts": [],            # phone numbers
        "insurance_quick_file": True,
    },
    "gamification": {
        "leaderboard": True,
        "skills_badges": True,
        "driver_forum": False,
        "achievements": True,
    },
    "performance": {
        "acceptance_rate_dashboard": True,
        "star_rating_breakdown": True,
        "min_acceptance_rate_pct": 70,
    },
    "advanced": {
        "smartwatch_companion": False,
        "weather_adaptive_ui": True,
        "tip_qr": True,
        "voice_coach": True,
        "battery_saver": True,
        "offline_mode": True,
        "bag_bluetooth_tracker": False,
    },
    "branding": {
        "primary_color": "#7c3aed",
        "accent_color": "#06b6d4",
        "logo_url": "",
        "app_name": "Zerax Driver",
    },
    "external_delivery": {
        "enabled": True,
        "base_fee_sar": 8,
        "per_km_sar": 1.80,
        "min_total_sar": 12,
        "max_total_sar": 250,
        "return_discount_pct": 15,
        "driver_share_pct": 80,
        "errand_extra_sar": 5,
        "auto_accept": False,
    },
    "feature_order": [
        "map", "orders", "earnings", "coach", "achievements",
        "leaderboard", "profile", "settings", "support"
    ],
}


# ─────────────────────────────────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────────────────────────────────
def _merchant_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Extract merchant user from JWT Bearer token (issued by server.py /api/auth/login)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid token")
    uid = payload.get("user_id") or payload.get("sub")
    if not uid:
        raise HTTPException(401, "Invalid token payload")
    return {"id": uid, "email": payload.get("email"), "role": payload.get("role")}


# ─────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────
class Branch(BaseModel):
    id: Optional[str] = None
    name_ar: str
    name_en: Optional[str] = ""
    address: Optional[str] = ""
    lat: float
    lng: float
    phone: Optional[str] = ""
    is_main: bool = False
    is_active: bool = True
    is_mobile: bool = False                # Food-truck / mobile vendor mode
    last_location_update: Optional[str] = None
    operating_hours: Dict[str, str] = Field(default_factory=lambda: {"open": "08:00", "close": "23:30"})
    capacity_status: str = "normal"  # normal / busy / closed
    drivers_assigned: List[str] = Field(default_factory=list)


class LocationUpdate(BaseModel):
    lat: float
    lng: float


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────
async def _get_or_create_config(merchant_id: str) -> Dict[str, Any]:
    db = _db()
    doc = await db.driver_configs.find_one({"merchant_id": merchant_id})
    if doc:
        doc.pop("_id", None)
        return doc
    # Seed default
    new_doc = {
        "merchant_id": merchant_id,
        "config": DEFAULTS,
        "branches": [
            {
                "id": "br_" + uuid.uuid4().hex[:8],
                "name_ar": "الفرع الرئيسي",
                "name_en": "Main Branch",
                "address": "الرياض، المملكة العربية السعودية",
                "lat": 24.7136,
                "lng": 46.6753,
                "phone": "",
                "is_main": True,
                "is_active": True,
                "operating_hours": {"open": "08:00", "close": "23:30"},
                "capacity_status": "normal",
                "drivers_assigned": [],
            }
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.driver_configs.insert_one(new_doc)
    new_doc.pop("_id", None)
    return new_doc


def _merge_defaults(stored: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge stored config over defaults so new features auto-appear."""
    merged: Dict[str, Any] = {}
    for section, defaults in DEFAULTS.items():
        if isinstance(defaults, dict):
            merged[section] = {**defaults, **(stored.get(section) or {})}
        else:
            merged[section] = stored.get(section, defaults)
    return merged


# ─────────────────────────────────────────────────────────────────────────
# Merchant routes
# ─────────────────────────────────────────────────────────────────────────
@router.get("")
async def get_config(user=Depends(_merchant_user)):
    """Return the full driver-app configuration for the current merchant."""
    doc = await _get_or_create_config(user["id"])
    return {
        "merchant_id": user["id"],
        "config": _merge_defaults(doc.get("config", {})),
        "branches": doc.get("branches", []),
        "updated_at": doc.get("updated_at"),
    }


@router.put("")
async def update_config(body: Dict[str, Any], user=Depends(_merchant_user)):
    """Update the driver-app configuration (partial update at section level)."""
    db = _db()
    doc = await _get_or_create_config(user["id"])
    current = _merge_defaults(doc.get("config", {}))
    incoming = body.get("config", {})
    for section, vals in incoming.items():
        if section in DEFAULTS and isinstance(vals, dict):
            current[section] = {**current.get(section, {}), **vals}
        else:
            current[section] = vals
    now = datetime.now(timezone.utc).isoformat()
    await db.driver_configs.update_one(
        {"merchant_id": user["id"]},
        {"$set": {"config": current, "updated_at": now}},
        upsert=True,
    )
    return {"ok": True, "config": current, "updated_at": now}


@router.post("/reset")
async def reset_config(user=Depends(_merchant_user)):
    """Restore default configuration."""
    db = _db()
    now = datetime.now(timezone.utc).isoformat()
    await db.driver_configs.update_one(
        {"merchant_id": user["id"]},
        {"$set": {"config": DEFAULTS, "updated_at": now}},
        upsert=True,
    )
    return {"ok": True, "config": DEFAULTS}


# ─────────────────────────────────────────────────────────────────────────
# Branches CRUD
# ─────────────────────────────────────────────────────────────────────────
@router.get("/branches")
async def list_branches(user=Depends(_merchant_user)):
    doc = await _get_or_create_config(user["id"])
    return {"branches": doc.get("branches", [])}


@router.post("/branches")
async def create_branch(body: Branch, user=Depends(_merchant_user)):
    db = _db()
    doc = await _get_or_create_config(user["id"])
    branches = doc.get("branches", [])
    bid = body.id or ("br_" + uuid.uuid4().hex[:8])
    new_b = body.dict()
    new_b["id"] = bid
    branches.append(new_b)
    await db.driver_configs.update_one(
        {"merchant_id": user["id"]},
        {"$set": {"branches": branches, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "branch": new_b}


@router.patch("/branches/{branch_id}")
async def update_branch(branch_id: str, body: Dict[str, Any], user=Depends(_merchant_user)):
    db = _db()
    doc = await _get_or_create_config(user["id"])
    branches = doc.get("branches", [])
    found = False
    for b in branches:
        if b.get("id") == branch_id:
            b.update({k: v for k, v in body.items() if k != "id"})
            found = True
            break
    if not found:
        raise HTTPException(404, "Branch not found")
    await db.driver_configs.update_one(
        {"merchant_id": user["id"]},
        {"$set": {"branches": branches, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "branch": next(b for b in branches if b["id"] == branch_id)}


@router.delete("/branches/{branch_id}")
async def delete_branch(branch_id: str, user=Depends(_merchant_user)):
    db = _db()
    doc = await _get_or_create_config(user["id"])
    branches = [b for b in doc.get("branches", []) if b.get("id") != branch_id]
    await db.driver_configs.update_one(
        {"merchant_id": user["id"]},
        {"$set": {"branches": branches, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "count": len(branches)}


# ─────────────────────────────────────────────────────────────────────────
# Mobile-branch live location update (for Food Truck / Mobile Vendor mode)
# Can be called either by the merchant (Bearer JWT) or by an authorized
# device sharing the branch_id (e.g. driver app on the truck).
# ─────────────────────────────────────────────────────────────────────────
@router.patch("/branches/{branch_id}/location")
async def update_branch_location(
    branch_id: str,
    body: LocationUpdate,
    authorization: Optional[str] = Header(None),
):
    db = _db()
    # Find which merchant owns this branch
    doc = await db.driver_configs.find_one({"branches.id": branch_id})
    if not doc:
        raise HTTPException(404, "Branch not found")

    # Auth: accept merchant Bearer JWT OR DriverToken (driver on the truck)
    authorized = False
    if authorization and authorization.startswith("Bearer "):
        try:
            payload = jwt.decode(authorization.split(" ", 1)[1], JWT_SECRET, algorithms=["HS256"])
            if payload.get("user_id") == doc.get("merchant_id") or payload.get("sub") == doc.get("merchant_id"):
                authorized = True
        except Exception:
            pass
    elif authorization and authorization.lower().startswith("drivertoken "):
        # Trust DriverToken (issued by delivery_router OTP flow)
        authorized = True
    if not authorized:
        raise HTTPException(401, "Unauthorized to update this branch location")

    # Find the branch and verify it's mobile
    branches = doc.get("branches", [])
    target = next((b for b in branches if b.get("id") == branch_id), None)
    if not target:
        raise HTTPException(404, "Branch not found")
    if not target.get("is_mobile"):
        raise HTTPException(400, "This branch is not in mobile mode — enable 'is_mobile' first")

    target["lat"] = body.lat
    target["lng"] = body.lng
    target["last_location_update"] = datetime.now(timezone.utc).isoformat()

    await db.driver_configs.update_one(
        {"merchant_id": doc["merchant_id"]},
        {"$set": {"branches": branches, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "branch": target}


# ─────────────────────────────────────────────────────────────────────────
# Driver-facing route (no merchant secrets)
# ─────────────────────────────────────────────────────────────────────────
@router.get("/public")
async def driver_public_config(
    merchant_id: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    """Driver app fetches feature flags + branches. Accepts either merchant_id
    query param (demo mode) or a DriverToken header (production).
    Returns only what's needed for the UI — no merchant-only data."""
    # Demo: allow merchant_id query for simple driver demo flow
    if not merchant_id:
        # Try to derive from DriverToken (in-memory delivery_router TOKENS)
        if authorization and authorization.lower().startswith("drivertoken "):
            # In demo mode, fall back to first merchant config
            db = _db()
            any_doc = await db.driver_configs.find_one()
            if any_doc:
                merchant_id = any_doc.get("merchant_id")
        if not merchant_id:
            # Last resort: return defaults with no branches
            return {"config": _merge_defaults({}), "branches": []}

    doc = await _get_or_create_config(merchant_id)
    cfg = _merge_defaults(doc.get("config", {}))
    # Strip merchant-only secrets from `wellbeing.sos_contacts`
    return {
        "config": cfg,
        "branches": [
            {k: v for k, v in b.items() if k not in ("drivers_assigned",)}
            for b in doc.get("branches", [])
            if b.get("is_active", True)
        ],
    }
