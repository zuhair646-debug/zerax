"""
Withdrawals — Driver earnings withdrawal requests.
Driver creates a withdrawal; merchant reviews + approves in their dashboard.
"""
from __future__ import annotations
import os, uuid, jwt
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

router = APIRouter(prefix="/api/delivery/withdrawals", tags=["withdrawals"])
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key")
_MONGO_URL = os.environ.get("MONGO_URL")
_DB_NAME = os.environ.get("DB_NAME")
_c: Optional[AsyncIOMotorClient] = None
def _db():
    global _c
    if _c is None: _c = AsyncIOMotorClient(_MONGO_URL)
    return _c[_DB_NAME]
def _now(): return datetime.now(timezone.utc).isoformat()

def _merchant(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required")
    try:
        p = jwt.decode(authorization.split(" ",1)[1], JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid token")
    return {"id": p.get("user_id") or p.get("sub")}


class WithdrawIn(BaseModel):
    amount_gross_sar: float
    method: str = "iban"     # iban / stc_pay / urpay / wallet
    account: str
    driver_name: Optional[str] = ""
    driver_phone: Optional[str] = ""


@router.post("")
async def create_withdrawal(body: WithdrawIn, authorization: Optional[str] = Header(None)):
    """Driver creates a withdrawal request."""
    if not authorization or not authorization.lower().startswith("drivertoken "):
        raise HTTPException(401, "DriverToken required")
    dtok = authorization.split(" ",1)[1]
    db = _db()
    # Resolve "default" merchant (single-tenant demo). In prod, link via driver→merchant assignment.
    cfg = await db.driver_configs.find_one()
    if not cfg:
        raise HTTPException(404, "No merchant config")
    merchant_id = cfg["merchant_id"]
    fee = (cfg.get("config", {}).get("earnings", {}) or {}).get("withdrawal_fee_sar", 4)
    net = round(body.amount_gross_sar - fee, 2)
    wid = "wd_" + uuid.uuid4().hex[:10]
    doc = {
        "id": wid,
        "merchant_id": merchant_id,
        "driver_token": dtok,
        "driver_name": body.driver_name,
        "driver_phone": body.driver_phone,
        "amount_gross_sar": body.amount_gross_sar,
        "fee_sar": fee,
        "amount_net_sar": net,
        "method": body.method,
        "account": body.account,
        "status": "pending",
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db.withdrawals.insert_one(doc)
    doc.pop("_id", None)
    return {"ok": True, "withdrawal": doc}


@router.get("")
async def list_withdrawals(user=Depends(_merchant), status: Optional[str] = None):
    db = _db()
    q: Dict[str, Any] = {"merchant_id": user["id"]}
    if status: q["status"] = status
    items = await db.withdrawals.find(q).sort("created_at", -1).limit(200).to_list(200)
    for d in items: d.pop("_id", None)
    return {"withdrawals": items, "count": len(items)}


@router.post("/{wid}/approve")
async def approve(wid: str, user=Depends(_merchant)):
    db = _db()
    await db.withdrawals.update_one({"id": wid, "merchant_id": user["id"]},
        {"$set": {"status": "approved", "approved_at": _now(), "updated_at": _now()}})
    return {"ok": True}


@router.post("/{wid}/reject")
async def reject(wid: str, body: Dict[str, Any], user=Depends(_merchant)):
    db = _db()
    await db.withdrawals.update_one({"id": wid, "merchant_id": user["id"]},
        {"$set": {"status": "rejected", "reject_reason": (body or {}).get("reason",""), "updated_at": _now()}})
    return {"ok": True}
