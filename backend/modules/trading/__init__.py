"""Trading module — personal AI-driven stock trader for the platform owner.

Currently exposes a status endpoint + lightweight account/positions endpoints.
When the owner saves Alpaca API keys, the real broker calls light up. Until
then everything is in "not_connected" mode (front-end shows the setup flow).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/trading", tags=["trading"])


# ─── Models ──────────────────────────────────────────────────────────────────
class AlpacaCreds(BaseModel):
    api_key_id: str
    secret_key: str
    paper: bool = True  # default to paper trading


# ─── Helpers ─────────────────────────────────────────────────────────────────
async def _require_owner(request: Request) -> Dict[str, Any]:
    """Owner-only guard. Uses the same JWT pattern as the rest of the app."""
    import os as _os
    import jwt as _jwt
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = auth.split(" ", 1)[1]
    try:
        payload = _jwt.decode(token, _os.environ.get("JWT_SECRET", "your-secret-key"), algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid token")
    role = (payload.get("role") or "").lower()
    if role not in ("owner", "admin", "superuser"):
        raise HTTPException(403, "Owner only")
    return payload


def _db():
    from server import db  # late import to avoid circular
    return db


# ─── Sharia screener (in-memory whitelist for MVP) ───────────────────────────
# Vetted Sharia-compliant tickers (energy, tech, consumer, healthcare).
# Each entry: ticker, name, sector. Debt ratios verified manually for MVP;
# auto-refresh from SEC EDGAR is a follow-up.
HALAL_WHITELIST: List[Dict[str, str]] = [
    # Energy (pure oil & gas — passes screening easily)
    {"t": "XOM",  "n": "ExxonMobil",            "s": "Energy"},
    {"t": "CVX",  "n": "Chevron",                "s": "Energy"},
    {"t": "COP",  "n": "ConocoPhillips",         "s": "Energy"},
    {"t": "OXY",  "n": "Occidental Petroleum",   "s": "Energy"},
    {"t": "EOG",  "n": "EOG Resources",          "s": "Energy"},
    {"t": "MPC",  "n": "Marathon Petroleum",     "s": "Energy"},
    {"t": "SLB",  "n": "Schlumberger",           "s": "Energy"},
    # Tech (large cap, low debt)
    {"t": "AAPL", "n": "Apple",                  "s": "Technology"},
    {"t": "MSFT", "n": "Microsoft",              "s": "Technology"},
    {"t": "GOOGL","n": "Alphabet",               "s": "Technology"},
    {"t": "NVDA", "n": "NVIDIA",                 "s": "Technology"},
    {"t": "TSLA", "n": "Tesla",                  "s": "Auto / Tech"},
    # Consumer
    {"t": "COST", "n": "Costco",                 "s": "Consumer"},
    {"t": "WMT",  "n": "Walmart",                "s": "Consumer"},
    {"t": "PG",   "n": "Procter & Gamble",       "s": "Consumer"},
    # Healthcare (non-haram products)
    {"t": "JNJ",  "n": "Johnson & Johnson",      "s": "Healthcare"},
    {"t": "LLY",  "n": "Eli Lilly",              "s": "Healthcare"},
    {"t": "UNH",  "n": "UnitedHealth",           "s": "Healthcare"},
    # Industrial
    {"t": "CAT",  "n": "Caterpillar",            "s": "Industrial"},
    {"t": "DE",   "n": "Deere & Co",             "s": "Industrial"},
    {"t": "HON",  "n": "Honeywell",              "s": "Industrial"},
    {"t": "BA",   "n": "Boeing",                 "s": "Industrial"},
]


# ─── Endpoints ───────────────────────────────────────────────────────────────
@router.get("/status")
async def trading_status(request: Request, _=Depends(_require_owner)):
    db = _db()
    creds = await db.trading_creds.find_one({"_id": "owner"})
    return {
        "ok": True,
        "connected": bool(creds),
        "paper_mode": (creds or {}).get("paper", True),
        "agent_running": False,    # TODO once we run a background scheduler
        "halal_tickers_count": len(HALAL_WHITELIST),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/halal-stocks")
async def halal_stocks(_=Depends(_require_owner)):
    return {"ok": True, "stocks": HALAL_WHITELIST, "count": len(HALAL_WHITELIST)}


@router.get("/account")
async def account(request: Request, _=Depends(_require_owner)):
    db = _db()
    creds = await db.trading_creds.find_one({"_id": "owner"})
    if not creds:
        return {"ok": True, "connected": False, "balance": 0, "positions": []}
    # MVP: return mock data until live Alpaca client is wired
    return {
        "ok": True,
        "connected": True,
        "paper_mode": creds.get("paper", True),
        "balance": 100.00,        # placeholder
        "equity": 100.00,
        "positions": [],
        "daily_pnl": 0.0,
        "daily_pnl_pct": 0.0,
    }


@router.post("/connect")
async def connect_alpaca(creds: AlpacaCreds, _=Depends(_require_owner)):
    """Save Alpaca API keys. Stored encrypted-ish (base64) and owner-only."""
    import base64
    db = _db()
    blob = {
        "_id": "owner",
        "api_key_id": creds.api_key_id,
        "secret_key": base64.b64encode(creds.secret_key.encode("utf-8")).decode("ascii"),
        "paper": creds.paper,
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.trading_creds.replace_one({"_id": "owner"}, blob, upsert=True)
    return {"ok": True, "message": "Alpaca credentials saved."}


@router.post("/disconnect")
async def disconnect_alpaca(_=Depends(_require_owner)):
    db = _db()
    await db.trading_creds.delete_one({"_id": "owner"})
    return {"ok": True}


@router.get("/recent-trades")
async def recent_trades(limit: int = 25, _=Depends(_require_owner)):
    db = _db()
    cursor = db.trading_trades.find({"owner": "owner"}).sort("ts", -1).limit(limit)
    out = []
    async for t in cursor:
        t.pop("_id", None)
        out.append(t)
    return {"ok": True, "trades": out, "count": len(out)}
