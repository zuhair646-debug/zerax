"""
Zenrex Delivery Scheduling
──────────────────────────────────────────────────────────────────────────
Per-merchant operating hours (multi-window per day) + scheduled delivery
bookings. Customers can:
  • See "open now" or "next available at X"
  • Book delivery for a future date+time (e.g., tomorrow 9 AM)
  • Get auto-computed ETA window (e.g., 8:30–9:15)

Driver gets the order PREPARATION_MINUTES before the scheduled time so they
have time to pick up + travel to customer.

Endpoints (under /api/delivery/schedule/*):
  Public:
    GET  /api/delivery/schedule/hours?merchant_id=X
    GET  /api/delivery/schedule/is-open?merchant_id=X
    GET  /api/delivery/schedule/slots?merchant_id=X&date=YYYY-MM-DD
  Merchant:
    PUT  /api/delivery/schedule/hours      — save weekly hours + scheduling cfg
"""
from __future__ import annotations

import os
import jwt
from datetime import datetime, timezone, timedelta, time as _time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

router = APIRouter(prefix="/api/delivery/schedule", tags=["delivery-schedule"])

JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key")
_MONGO_URL = os.environ.get("MONGO_URL")
_DB_NAME = os.environ.get("DB_NAME")
_client: Optional[AsyncIOMotorClient] = None


def _db():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(_MONGO_URL)
    return _client[_DB_NAME]


DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
DAY_AR = {
    "saturday": "السبت", "sunday": "الأحد", "monday": "الاثنين",
    "tuesday": "الثلاثاء", "wednesday": "الأربعاء",
    "thursday": "الخميس", "friday": "الجمعة",
}

# ─────────────────────────────────────────────────────────────────────────
# Defaults — open all 7 days from 06:00 to 23:30 (single window)
# ─────────────────────────────────────────────────────────────────────────
DEFAULT_SCHEDULE: Dict[str, Any] = {
    "is_24_7": False,
    "timezone_offset_hours": 3,  # Saudi (UTC+3)
    "hours": {d: [{"open": "06:00", "close": "23:30"}] for d in DAYS},
    "scheduling": {
        "enabled": True,
        "advance_booking_days": 7,
        "slot_interval_minutes": 30,
        "preparation_minutes": 30,
        "eta_window_minutes": 45,
        "min_advance_minutes": 60,
        "max_orders_per_slot": 10,
    },
}


# ─────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────
class TimeWindow(BaseModel):
    open: str   # "HH:MM"
    close: str  # "HH:MM"


class HoursIn(BaseModel):
    is_24_7: Optional[bool] = None
    timezone_offset_hours: Optional[int] = None
    hours: Optional[Dict[str, List[TimeWindow]]] = None
    scheduling: Optional[Dict[str, Any]] = None


# ─────────────────────────────────────────────────────────────────────────
# Helpers
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
    return {"id": uid}


def _parse_hhmm(s: str) -> _time:
    h, m = s.split(":")
    return _time(int(h), int(m))


async def _get_schedule(merchant_id: str) -> Dict[str, Any]:
    db = _db()
    doc = await db.driver_configs.find_one({"merchant_id": merchant_id})
    if not doc:
        doc = await db.driver_configs.find_one()
    if not doc:
        return DEFAULT_SCHEDULE
    cfg = (doc or {}).get("config", {})
    sched = cfg.get("schedule") or {}
    out = {
        "is_24_7": sched.get("is_24_7", DEFAULT_SCHEDULE["is_24_7"]),
        "timezone_offset_hours": sched.get("timezone_offset_hours", DEFAULT_SCHEDULE["timezone_offset_hours"]),
        "hours": {**DEFAULT_SCHEDULE["hours"], **(sched.get("hours") or {})},
        "scheduling": {**DEFAULT_SCHEDULE["scheduling"], **(sched.get("scheduling") or {})},
    }
    return out


def _local_now(tz_offset_h: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=tz_offset_h)


def _is_open_at(sched: Dict[str, Any], dt: datetime) -> bool:
    if sched.get("is_24_7"):
        return True
    day_key = DAYS[dt.weekday()] if False else _pydate_to_day(dt)
    windows = sched["hours"].get(day_key, [])
    t = dt.time()
    for w in windows:
        try:
            o = _parse_hhmm(w["open"])
            c = _parse_hhmm(w["close"])
            if o <= t <= c:
                return True
        except Exception:
            continue
    return False


def _pydate_to_day(dt: datetime) -> str:
    """Python's weekday: Monday=0..Sunday=6. We map to our list."""
    # weekday(): Mon=0 ... Sun=6 → our list "sunday" at index 0
    mapping = {6: "sunday", 0: "monday", 1: "tuesday", 2: "wednesday",
               3: "thursday", 4: "friday", 5: "saturday"}
    return mapping[dt.weekday()]


def _next_opening(sched: Dict[str, Any], from_dt: datetime) -> Optional[datetime]:
    if sched.get("is_24_7"):
        return from_dt
    for offset in range(0, 14):
        d = from_dt + timedelta(days=offset)
        day_key = _pydate_to_day(d)
        wins = sched["hours"].get(day_key, [])
        for w in sorted(wins, key=lambda x: x["open"]):
            try:
                opener = datetime.combine(d.date(), _parse_hhmm(w["open"]))
                if offset == 0 and opener < from_dt.replace(tzinfo=None):
                    continue
                return opener
            except Exception:
                continue
    return None


def _generate_slots(sched: Dict[str, Any], target_date: datetime, now_local: datetime) -> List[Dict[str, str]]:
    """Build available slot labels for a given local date."""
    if sched.get("is_24_7"):
        # Generate slots from 00:00 to 23:30
        slots = []
        interval = sched["scheduling"]["slot_interval_minutes"]
        cur = datetime.combine(target_date.date(), _time(0, 0))
        end = datetime.combine(target_date.date(), _time(23, 30))
        while cur <= end:
            if cur > now_local.replace(tzinfo=None) + timedelta(minutes=sched["scheduling"]["min_advance_minutes"]):
                slots.append({
                    "value": cur.strftime("%H:%M"),
                    "label": cur.strftime("%H:%M"),
                })
            cur += timedelta(minutes=interval)
        return slots

    day_key = _pydate_to_day(target_date)
    windows = sched["hours"].get(day_key, [])
    interval = sched["scheduling"]["slot_interval_minutes"]
    min_ahead = sched["scheduling"]["min_advance_minutes"]
    out: List[Dict[str, str]] = []
    for w in windows:
        try:
            o = _parse_hhmm(w["open"])
            c = _parse_hhmm(w["close"])
            cur = datetime.combine(target_date.date(), o)
            end = datetime.combine(target_date.date(), c)
            while cur + timedelta(minutes=interval) <= end:
                if cur > now_local.replace(tzinfo=None) + timedelta(minutes=min_ahead):
                    eta_win = sched["scheduling"]["eta_window_minutes"]
                    half = eta_win // 2
                    win_start = (cur - timedelta(minutes=half)).time().strftime("%H:%M")
                    win_end = (cur + timedelta(minutes=eta_win - half)).time().strftime("%H:%M")
                    out.append({
                        "value": cur.strftime("%H:%M"),
                        "label": cur.strftime("%H:%M"),
                        "eta_window": f"{win_start} – {win_end}",
                    })
                cur += timedelta(minutes=interval)
        except Exception:
            continue
    return out


# ─────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────
@router.get("/hours")
async def public_hours(merchant_id: Optional[str] = None):
    if not merchant_id or merchant_id == "demo":
        db = _db()
        any_doc = await db.driver_configs.find_one()
        if any_doc:
            merchant_id = any_doc.get("merchant_id")
    sched = await _get_schedule(merchant_id or "")
    sched["day_labels"] = DAY_AR
    return sched


@router.get("/is-open")
async def is_open_now(merchant_id: Optional[str] = None):
    if not merchant_id or merchant_id == "demo":
        db = _db()
        any_doc = await db.driver_configs.find_one()
        if any_doc:
            merchant_id = any_doc.get("merchant_id")
    sched = await _get_schedule(merchant_id or "")
    now_local = _local_now(sched["timezone_offset_hours"])
    open_now = _is_open_at(sched, now_local)
    next_open = _next_opening(sched, now_local) if not open_now else None
    return {
        "is_open": open_now,
        "is_24_7": sched.get("is_24_7", False),
        "now_local": now_local.strftime("%Y-%m-%d %H:%M"),
        "next_open_at": next_open.strftime("%Y-%m-%d %H:%M") if next_open else None,
        "next_open_label": _format_next_open(next_open) if next_open else None,
        "current_day": _pydate_to_day(now_local),
        "current_day_ar": DAY_AR[_pydate_to_day(now_local)],
        "today_windows": sched["hours"].get(_pydate_to_day(now_local), []),
    }


def _format_next_open(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    now = datetime.now()
    today = now.date()
    if dt.date() == today:
        return f"اليوم الساعة {dt.strftime('%H:%M')}"
    if dt.date() == today + timedelta(days=1):
        return f"بكرة الساعة {dt.strftime('%H:%M')}"
    return f"{DAY_AR[_pydate_to_day(dt)]} الساعة {dt.strftime('%H:%M')}"


@router.get("/slots")
async def get_slots(merchant_id: Optional[str] = None, date: Optional[str] = None):
    """Return available scheduling slots for a date (YYYY-MM-DD)."""
    if not merchant_id or merchant_id == "demo":
        db = _db()
        any_doc = await db.driver_configs.find_one()
        if any_doc:
            merchant_id = any_doc.get("merchant_id")
    sched = await _get_schedule(merchant_id or "")
    now_local = _local_now(sched["timezone_offset_hours"])
    try:
        target = datetime.strptime(date, "%Y-%m-%d") if date else now_local
    except Exception:
        target = now_local
    slots = _generate_slots(sched, target, now_local)
    return {
        "date": target.strftime("%Y-%m-%d"),
        "day_ar": DAY_AR[_pydate_to_day(target)],
        "slots": slots,
        "is_24_7": sched.get("is_24_7", False),
        "preparation_minutes": sched["scheduling"]["preparation_minutes"],
    }


@router.put("/hours")
async def save_hours(body: HoursIn, user=Depends(_merchant_user)):
    db = _db()
    doc = await db.driver_configs.find_one({"merchant_id": user["id"]})
    cfg = (doc or {}).get("config", {})
    cur_schedule = cfg.get("schedule", {}) or {}

    if body.is_24_7 is not None:
        cur_schedule["is_24_7"] = body.is_24_7
    if body.timezone_offset_hours is not None:
        cur_schedule["timezone_offset_hours"] = body.timezone_offset_hours
    if body.hours is not None:
        cur_schedule["hours"] = {k: [w.dict() for w in v] for k, v in body.hours.items()}
    if body.scheduling is not None:
        cur_schedule["scheduling"] = {**(cur_schedule.get("scheduling") or {}), **body.scheduling}

    new_cfg = {**cfg, "schedule": cur_schedule}
    await db.driver_configs.update_one(
        {"merchant_id": user["id"]},
        {"$set": {"config": new_cfg, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"ok": True, "schedule": cur_schedule}
