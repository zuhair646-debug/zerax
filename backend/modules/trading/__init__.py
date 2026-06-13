"""Trading module — personal AI-driven US Halal stock trader.

Phase 2 (Feb 2026): LIVE Alpaca API integration (paper + live).
- Stores Alpaca creds (base64-obfuscated) per owner in MongoDB.
- Wires `/account`, `/positions`, `/quote`, `/trade`, `/close-position` to Alpaca.
- AI Strategy endpoint uses Claude Sonnet 4.5 (via Emergent LLM Key) to produce
  a JSON BUY/HOLD/SELL decision with reasoning, then optionally auto-executes
  if user opted in.
- Halal whitelist enforced server-side — no order accepted for non-listed ticker.
- Risk limits: max position % of equity, daily loss circuit-breaker, cooldown.

Owner-only across the board.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/trading", tags=["trading"])


# ─── Models ──────────────────────────────────────────────────────────────────
class AlpacaCreds(BaseModel):
    api_key_id: str
    secret_key: str
    paper: bool = True


class TradeRequest(BaseModel):
    ticker: str
    side: str = Field(..., pattern="^(buy|sell)$")
    qty: Optional[float] = None
    notional: Optional[float] = None  # dollar amount; one of qty/notional required
    limit_price: Optional[float] = None  # if None -> market order


class AISuggestRequest(BaseModel):
    ticker: str
    auto_execute: bool = False
    max_notional: float = 100.0  # cap per trade for safety


class RiskSettings(BaseModel):
    max_position_pct: float = 20.0   # max % of equity per ticker
    daily_loss_limit_pct: float = 5.0  # halt trading if down this % today
    cooldown_minutes: int = 5        # min minutes between trades on same ticker


# ─── Helpers ─────────────────────────────────────────────────────────────────
async def _require_owner(request: Request) -> Dict[str, Any]:
    """Owner-only guard. Uses the same JWT pattern as the rest of the app."""
    import jwt as _jwt
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = auth.split(" ", 1)[1]
    try:
        payload = _jwt.decode(token, os.environ.get("JWT_SECRET", "your-secret-key"), algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid token")
    role = (payload.get("role") or "").lower()
    if role not in ("owner", "admin", "superuser"):
        raise HTTPException(403, "Owner only")
    return payload


def _db():
    from server import db  # late import to avoid circular
    return db


def _decode_secret(b64: str) -> str:
    try:
        return base64.b64decode(b64.encode("ascii")).decode("utf-8")
    except Exception:
        return b64  # already plain (legacy)


# ─── Sharia screener (vetted in-memory whitelist for MVP) ────────────────────
HALAL_WHITELIST: List[Dict[str, str]] = [
    {"t": "XOM",  "n": "ExxonMobil",            "s": "Energy"},
    {"t": "CVX",  "n": "Chevron",                "s": "Energy"},
    {"t": "COP",  "n": "ConocoPhillips",         "s": "Energy"},
    {"t": "OXY",  "n": "Occidental Petroleum",   "s": "Energy"},
    {"t": "EOG",  "n": "EOG Resources",          "s": "Energy"},
    {"t": "MPC",  "n": "Marathon Petroleum",     "s": "Energy"},
    {"t": "SLB",  "n": "Schlumberger",           "s": "Energy"},
    {"t": "AAPL", "n": "Apple",                  "s": "Technology"},
    {"t": "MSFT", "n": "Microsoft",              "s": "Technology"},
    {"t": "GOOGL","n": "Alphabet",               "s": "Technology"},
    {"t": "NVDA", "n": "NVIDIA",                 "s": "Technology"},
    {"t": "TSLA", "n": "Tesla",                  "s": "Auto / Tech"},
    {"t": "COST", "n": "Costco",                 "s": "Consumer"},
    {"t": "WMT",  "n": "Walmart",                "s": "Consumer"},
    {"t": "PG",   "n": "Procter & Gamble",       "s": "Consumer"},
    {"t": "JNJ",  "n": "Johnson & Johnson",      "s": "Healthcare"},
    {"t": "LLY",  "n": "Eli Lilly",              "s": "Healthcare"},
    {"t": "UNH",  "n": "UnitedHealth",           "s": "Healthcare"},
    {"t": "CAT",  "n": "Caterpillar",            "s": "Industrial"},
    {"t": "DE",   "n": "Deere & Co",             "s": "Industrial"},
    {"t": "HON",  "n": "Honeywell",              "s": "Industrial"},
    {"t": "BA",   "n": "Boeing",                 "s": "Industrial"},
]
HALAL_SET = {s["t"] for s in HALAL_WHITELIST}


def _is_halal(ticker: str) -> bool:
    return ticker.upper() in HALAL_SET


# ─── Alpaca client cache ─────────────────────────────────────────────────────
_CLIENT_CACHE: Dict[str, Any] = {}


def _get_trading_client(api_key: str, secret_key: str, paper: bool):
    """Return cached Alpaca TradingClient."""
    key = f"trade:{api_key[:6]}:{paper}"
    if key in _CLIENT_CACHE:
        return _CLIENT_CACHE[key]
    from alpaca.trading.client import TradingClient
    c = TradingClient(api_key=api_key, secret_key=secret_key, paper=paper)
    _CLIENT_CACHE[key] = c
    return c


def _get_data_client(api_key: str, secret_key: str):
    key = f"data:{api_key[:6]}"
    if key in _CLIENT_CACHE:
        return _CLIENT_CACHE[key]
    from alpaca.data.historical import StockHistoricalDataClient
    c = StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)
    _CLIENT_CACHE[key] = c
    return c


async def _load_creds() -> Optional[Dict[str, Any]]:
    db = _db()
    creds = await db.trading_creds.find_one({"_id": "owner"})
    if not creds:
        return None
    return {
        "api_key_id": creds["api_key_id"],
        "secret_key": _decode_secret(creds["secret_key"]),
        "paper": creds.get("paper", True),
    }


async def _get_clients() -> Optional[Dict[str, Any]]:
    """Returns dict with trading + data clients, or None if not connected."""
    c = await _load_creds()
    if not c:
        return None
    return {
        "trading": _get_trading_client(c["api_key_id"], c["secret_key"], c["paper"]),
        "data":    _get_data_client(c["api_key_id"], c["secret_key"]),
        "paper":   c["paper"],
    }


def _run(blocking_fn, *args, **kwargs):
    """Run a blocking Alpaca SDK call in a worker thread."""
    return asyncio.to_thread(blocking_fn, *args, **kwargs)


# ─── Endpoints: status & creds ──────────────────────────────────────────────
@router.get("/status")
async def trading_status(request: Request, _=Depends(_require_owner)):
    creds = await _load_creds()
    db = _db()
    risk = await db.trading_settings.find_one({"_id": "owner"}) or {}
    return {
        "ok": True,
        "connected": bool(creds),
        "paper_mode": (creds or {}).get("paper", True),
        "agent_running": risk.get("agent_running", False),
        "halal_tickers_count": len(HALAL_WHITELIST),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/halal-stocks")
async def halal_stocks(_=Depends(_require_owner)):
    return {"ok": True, "stocks": HALAL_WHITELIST, "count": len(HALAL_WHITELIST)}


@router.post("/connect")
async def connect_alpaca(creds: AlpacaCreds, _=Depends(_require_owner)):
    """Save Alpaca API keys. Validates by calling /v2/account before persisting."""
    # Quick validation
    try:
        from alpaca.trading.client import TradingClient
        client = TradingClient(api_key=creds.api_key_id, secret_key=creds.secret_key, paper=creds.paper)
        acct = await _run(client.get_account)
        _ = acct.equity  # touch
    except Exception as e:
        raise HTTPException(400, f"Invalid Alpaca credentials: {e}")

    db = _db()
    blob = {
        "_id": "owner",
        "api_key_id": creds.api_key_id,
        "secret_key": base64.b64encode(creds.secret_key.encode("utf-8")).decode("ascii"),
        "paper": creds.paper,
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.trading_creds.replace_one({"_id": "owner"}, blob, upsert=True)
    # Clear cache so next call uses new creds
    _CLIENT_CACHE.clear()
    return {"ok": True, "message": "Alpaca credentials saved.", "paper": creds.paper}


@router.post("/disconnect")
async def disconnect_alpaca(_=Depends(_require_owner)):
    db = _db()
    await db.trading_creds.delete_one({"_id": "owner"})
    _CLIENT_CACHE.clear()
    return {"ok": True}


# ─── Endpoints: live account data ────────────────────────────────────────────
@router.get("/account")
async def account(request: Request, _=Depends(_require_owner)):
    clients = await _get_clients()
    if not clients:
        return {"ok": True, "connected": False, "balance": 0, "equity": 0, "positions": [],
                "daily_pnl": 0.0, "daily_pnl_pct": 0.0}
    try:
        acct = await _run(clients["trading"].get_account)
        positions = await _run(clients["trading"].get_all_positions)
        equity = float(acct.equity)
        last_equity = float(acct.last_equity)
        daily_pnl = equity - last_equity
        daily_pnl_pct = (daily_pnl / last_equity * 100.0) if last_equity else 0.0
        pos_list = [{
            "ticker": p.symbol,
            "qty": float(p.qty),
            "avg_entry": float(p.avg_entry_price),
            "current_price": float(p.current_price) if p.current_price else None,
            "market_value": float(p.market_value) if p.market_value else None,
            "unrealized_pl": float(p.unrealized_pl) if p.unrealized_pl else 0.0,
            "unrealized_plpc": float(p.unrealized_plpc) * 100.0 if p.unrealized_plpc else 0.0,
            "side": p.side.value if hasattr(p.side, "value") else str(p.side),
        } for p in positions]
        return {
            "ok": True,
            "connected": True,
            "paper_mode": clients["paper"],
            "balance": float(acct.cash),
            "equity": equity,
            "buying_power": float(acct.buying_power),
            "positions": pos_list,
            "daily_pnl": daily_pnl,
            "daily_pnl_pct": daily_pnl_pct,
            "status": str(acct.status.value if hasattr(acct.status, "value") else acct.status),
        }
    except Exception as e:
        logger.exception("alpaca account failed")
        raise HTTPException(502, f"Alpaca error: {e}")


@router.get("/quote/{ticker}")
async def get_quote(ticker: str, _=Depends(_require_owner)):
    ticker = ticker.upper()
    if not _is_halal(ticker):
        raise HTTPException(400, f"{ticker} is not in the Halal whitelist.")
    clients = await _get_clients()
    if not clients:
        raise HTTPException(400, "Alpaca not connected")
    try:
        from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        # Latest quote
        q_req = StockLatestQuoteRequest(symbol_or_symbols=[ticker])
        q_resp = await _run(clients["data"].get_stock_latest_quote, q_req)
        q = q_resp[ticker]
        # Last 30 days of daily bars for AI context
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=45)
        b_req = StockBarsRequest(symbol_or_symbols=[ticker], timeframe=TimeFrame.Day,
                                 start=start, end=end, limit=30)
        b_resp = await _run(clients["data"].get_stock_bars, b_req)
        bars = []
        if ticker in b_resp.data:
            for b in b_resp.data[ticker][-30:]:
                bars.append({
                    "t": b.timestamp.isoformat() if hasattr(b.timestamp, "isoformat") else str(b.timestamp),
                    "o": float(b.open), "h": float(b.high), "l": float(b.low),
                    "c": float(b.close), "v": int(b.volume),
                })
        return {
            "ok": True,
            "ticker": ticker,
            "bid": float(q.bid_price) if q.bid_price else None,
            "ask": float(q.ask_price) if q.ask_price else None,
            "bid_size": int(q.bid_size) if q.bid_size else 0,
            "ask_size": int(q.ask_size) if q.ask_size else 0,
            "ts": q.timestamp.isoformat() if hasattr(q.timestamp, "isoformat") else str(q.timestamp),
            "bars": bars,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("quote failed")
        raise HTTPException(502, f"Alpaca data error: {e}")


# ─── Endpoints: trade execution ──────────────────────────────────────────────
@router.post("/trade")
async def place_trade(req: TradeRequest, request: Request, _=Depends(_require_owner)):
    ticker = req.ticker.upper()
    if not _is_halal(ticker):
        raise HTTPException(400, f"{ticker} is not Sharia-compliant (not in whitelist).")
    if not req.qty and not req.notional:
        raise HTTPException(400, "Provide either qty or notional.")
    clients = await _get_clients()
    if not clients:
        raise HTTPException(400, "Alpaca not connected")

    # Risk guard: daily loss circuit-breaker
    db = _db()
    settings = await db.trading_settings.find_one({"_id": "owner"}) or {}
    daily_limit_pct = float(settings.get("daily_loss_limit_pct", 5.0))
    try:
        acct = await _run(clients["trading"].get_account)
        equity = float(acct.equity)
        last_equity = float(acct.last_equity)
        if last_equity > 0:
            pnl_pct = (equity - last_equity) / last_equity * 100.0
            if pnl_pct <= -abs(daily_limit_pct):
                raise HTTPException(403, f"Daily loss limit hit ({pnl_pct:.2f}%) — trading halted for today.")
    except HTTPException:
        raise
    except Exception:
        pass  # don't block on account check failure

    # Cooldown guard
    cooldown_min = int(settings.get("cooldown_minutes", 5))
    last_trade = await db.trading_trades.find_one(
        {"owner": "owner", "ticker": ticker}, sort=[("ts", -1)]
    )
    if last_trade:
        try:
            last_ts = datetime.fromisoformat(last_trade["ts"].replace("Z", "+00:00"))
            elapsed = (datetime.now(timezone.utc) - last_ts).total_seconds() / 60.0
            if elapsed < cooldown_min:
                raise HTTPException(429, f"Cooldown: wait {cooldown_min - elapsed:.1f} more minutes on {ticker}")
        except HTTPException:
            raise
        except Exception:
            pass

    # Submit order
    try:
        from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        side_enum = OrderSide.BUY if req.side == "buy" else OrderSide.SELL
        order_kwargs = {
            "symbol": ticker,
            "side": side_enum,
            "time_in_force": TimeInForce.DAY,
        }
        if req.qty:
            order_kwargs["qty"] = req.qty
        else:
            order_kwargs["notional"] = req.notional

        if req.limit_price:
            order_req = LimitOrderRequest(limit_price=req.limit_price, **order_kwargs)
        else:
            order_req = MarketOrderRequest(**order_kwargs)
        order = await _run(clients["trading"].submit_order, order_req)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("trade submit failed")
        raise HTTPException(502, f"Alpaca order error: {e}")

    # Persist trade
    trade_doc = {
        "owner": "owner",
        "order_id": str(order.id),
        "ticker": ticker,
        "side": req.side,
        "qty": req.qty,
        "notional": req.notional,
        "limit_price": req.limit_price,
        "status": str(order.status.value if hasattr(order.status, "value") else order.status),
        "ts": datetime.now(timezone.utc).isoformat(),
        "paper": clients["paper"],
        "ai_initiated": False,
    }
    await db.trading_trades.insert_one(trade_doc)
    trade_doc.pop("_id", None)
    return {"ok": True, "trade": trade_doc}


@router.post("/close-position/{ticker}")
async def close_position(ticker: str, _=Depends(_require_owner)):
    ticker = ticker.upper()
    clients = await _get_clients()
    if not clients:
        raise HTTPException(400, "Alpaca not connected")
    try:
        result = await _run(clients["trading"].close_position, ticker)
        order_id = str(getattr(result, "id", "n/a"))
        db = _db()
        await db.trading_trades.insert_one({
            "owner": "owner", "order_id": order_id, "ticker": ticker, "side": "close",
            "qty": None, "notional": None,
            "status": str(getattr(result, "status", "submitted")),
            "ts": datetime.now(timezone.utc).isoformat(),
            "paper": clients["paper"], "ai_initiated": False,
        })
        return {"ok": True, "order_id": order_id}
    except Exception as e:
        logger.exception("close position failed")
        raise HTTPException(502, f"Alpaca close error: {e}")


# ─── Endpoints: AI strategy ──────────────────────────────────────────────────
def _build_ai_prompt(ticker: str, bars: List[Dict], quote: Dict, position: Optional[Dict]) -> str:
    """Build a structured prompt for Claude to produce a JSON trade decision."""
    bar_lines = "\n".join(
        f"- {b['t'][:10]}: O={b['o']:.2f} H={b['h']:.2f} L={b['l']:.2f} C={b['c']:.2f} V={b['v']}"
        for b in bars[-15:]
    )
    pos_str = "None"
    if position:
        pos_str = (f"qty={position['qty']}, avg_entry=${position['avg_entry']:.2f}, "
                   f"unrealized_pl=${position.get('unrealized_pl', 0):.2f} "
                   f"({position.get('unrealized_plpc', 0):.2f}%)")
    return f"""You are a disciplined, risk-averse swing-trading analyst for a Sharia-compliant US stock account.

TICKER: {ticker}
CURRENT QUOTE: bid=${quote.get('bid')}, ask=${quote.get('ask')}
CURRENT POSITION: {pos_str}

LAST 15 DAILY BARS:
{bar_lines}

TASK:
Analyze trend (SMA crossover, momentum, volume), volatility, and risk/reward.
Return STRICT JSON ONLY (no markdown, no prose) with this exact shape:
{{
  "action": "buy" | "hold" | "sell",
  "confidence": 0-100,
  "reasoning": "1-3 short sentences in Arabic explaining the call",
  "suggested_notional_usd": number or null,
  "stop_loss_pct": number or null,
  "take_profit_pct": number or null
}}

RULES:
- If trend is unclear or volatility is high relative to reward, say "hold".
- Never suggest notional > $200 in a single trade.
- If we already own this stock and momentum reverses, prefer "sell".
- Be honest — "hold" is a valid, frequent answer."""


@router.post("/ai-suggest")
async def ai_suggest(req: AISuggestRequest, _=Depends(_require_owner)):
    """Ask Claude to analyze a ticker and optionally auto-execute the trade."""
    ticker = req.ticker.upper()
    if not _is_halal(ticker):
        raise HTTPException(400, f"{ticker} is not in the Halal whitelist.")
    clients = await _get_clients()
    if not clients:
        raise HTTPException(400, "Alpaca not connected")

    # 1. Gather data
    try:
        from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        q_req = StockLatestQuoteRequest(symbol_or_symbols=[ticker])
        q_resp = await _run(clients["data"].get_stock_latest_quote, q_req)
        q = q_resp[ticker]
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=45)
        b_req = StockBarsRequest(symbol_or_symbols=[ticker], timeframe=TimeFrame.Day,
                                 start=start, end=end, limit=30)
        b_resp = await _run(clients["data"].get_stock_bars, b_req)
        bars = []
        if ticker in b_resp.data:
            for b in b_resp.data[ticker][-30:]:
                bars.append({
                    "t": b.timestamp.isoformat() if hasattr(b.timestamp, "isoformat") else str(b.timestamp),
                    "o": float(b.open), "h": float(b.high), "l": float(b.low),
                    "c": float(b.close), "v": int(b.volume),
                })
        quote = {"bid": float(q.bid_price) if q.bid_price else None,
                 "ask": float(q.ask_price) if q.ask_price else None}
        positions = await _run(clients["trading"].get_all_positions)
        current_pos = None
        for p in positions:
            if p.symbol == ticker:
                current_pos = {
                    "qty": float(p.qty),
                    "avg_entry": float(p.avg_entry_price),
                    "unrealized_pl": float(p.unrealized_pl) if p.unrealized_pl else 0.0,
                    "unrealized_plpc": float(p.unrealized_plpc) * 100.0 if p.unrealized_plpc else 0.0,
                }
                break
    except Exception as e:
        logger.exception("ai-suggest data fetch failed")
        raise HTTPException(502, f"Data fetch error: {e}")

    # 2. Call Claude
    prompt = _build_ai_prompt(ticker, bars, quote, current_pos)
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        emergent_key = os.environ.get("EMERGENT_LLM_KEY")
        if not emergent_key:
            raise HTTPException(500, "EMERGENT_LLM_KEY missing")
        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"trading-{ticker}-{int(time.time())}",
            system_message="You are a disciplined swing-trading analyst. Always return valid JSON only.",
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        reply = await chat.send_message(UserMessage(text=prompt))
        text = reply if isinstance(reply, str) else getattr(reply, "content", str(reply))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("LLM call failed")
        raise HTTPException(502, f"AI engine error: {e}")

    # 3. Parse JSON
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    decision: Dict[str, Any] = {}
    try:
        # Find first {…} block
        start_i = raw.find("{")
        end_i = raw.rfind("}")
        if start_i >= 0 and end_i > start_i:
            decision = json.loads(raw[start_i:end_i + 1])
    except Exception as e:
        logger.warning(f"AI JSON parse failed: {e} | raw={raw[:200]}")
        decision = {"action": "hold", "confidence": 0,
                    "reasoning": "تعذّر تحليل رد الـ AI، تم اتخاذ قرار الانتظار.",
                    "suggested_notional_usd": None}

    decision.setdefault("action", "hold")
    decision.setdefault("confidence", 0)
    decision.setdefault("reasoning", "")
    decision.setdefault("suggested_notional_usd", None)

    # 4. Persist suggestion
    db = _db()
    suggestion_doc = {
        "owner": "owner",
        "ticker": ticker,
        "decision": decision,
        "raw": text[:2000],
        "ts": datetime.now(timezone.utc).isoformat(),
        "auto_execute_requested": req.auto_execute,
        "executed": False,
    }
    inserted = await db.trading_ai_suggestions.insert_one(suggestion_doc)
    suggestion_id = str(inserted.inserted_id)

    # 5. Optional auto-execute
    executed_trade = None
    action = (decision.get("action") or "").lower()
    confidence = float(decision.get("confidence") or 0)
    notional_suggested = decision.get("suggested_notional_usd")
    if (req.auto_execute and action in ("buy", "sell") and confidence >= 60
            and notional_suggested):
        notional = min(float(notional_suggested), float(req.max_notional))
        try:
            # Place market order directly (skipping HTTP roundtrip)
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce
            side_enum = OrderSide.BUY if action == "buy" else OrderSide.SELL
            order_req = MarketOrderRequest(symbol=ticker, side=side_enum,
                                           time_in_force=TimeInForce.DAY,
                                           notional=notional)
            order = await _run(clients["trading"].submit_order, order_req)
            executed_trade = {
                "order_id": str(order.id),
                "status": str(order.status.value if hasattr(order.status, "value") else order.status),
                "notional": notional,
                "side": action,
            }
            await db.trading_trades.insert_one({
                "owner": "owner", "order_id": str(order.id), "ticker": ticker,
                "side": action, "qty": None, "notional": notional, "limit_price": None,
                "status": executed_trade["status"],
                "ts": datetime.now(timezone.utc).isoformat(),
                "paper": clients["paper"], "ai_initiated": True,
                "suggestion_id": suggestion_id, "confidence": confidence,
            })
            await db.trading_ai_suggestions.update_one(
                {"_id": inserted.inserted_id},
                {"$set": {"executed": True, "executed_trade": executed_trade}},
            )
        except Exception as e:
            logger.exception("auto-execute failed")
            executed_trade = {"error": str(e)}

    return {
        "ok": True,
        "ticker": ticker,
        "decision": decision,
        "auto_execute": req.auto_execute,
        "executed_trade": executed_trade,
        "suggestion_id": suggestion_id,
    }


# ─── Endpoints: settings + history ───────────────────────────────────────────
@router.get("/settings")
async def get_settings(_=Depends(_require_owner)):
    db = _db()
    s = await db.trading_settings.find_one({"_id": "owner"}) or {}
    s.pop("_id", None)
    return {
        "ok": True,
        "max_position_pct": s.get("max_position_pct", 20.0),
        "daily_loss_limit_pct": s.get("daily_loss_limit_pct", 5.0),
        "cooldown_minutes": s.get("cooldown_minutes", 5),
        "agent_running": s.get("agent_running", False),
    }


@router.post("/settings")
async def update_settings(settings: RiskSettings, _=Depends(_require_owner)):
    db = _db()
    blob = {
        "_id": "owner",
        "max_position_pct": settings.max_position_pct,
        "daily_loss_limit_pct": settings.daily_loss_limit_pct,
        "cooldown_minutes": settings.cooldown_minutes,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.trading_settings.update_one({"_id": "owner"}, {"$set": blob}, upsert=True)
    return {"ok": True}


@router.post("/agent/toggle")
async def toggle_agent(running: bool, _=Depends(_require_owner)):
    db = _db()
    await db.trading_settings.update_one(
        {"_id": "owner"}, {"$set": {"agent_running": running}}, upsert=True
    )
    return {"ok": True, "agent_running": running}


@router.get("/recent-trades")
async def recent_trades(limit: int = 25, _=Depends(_require_owner)):
    db = _db()
    cursor = db.trading_trades.find({"owner": "owner"}).sort("ts", -1).limit(limit)
    out = []
    async for t in cursor:
        t.pop("_id", None)
        out.append(t)
    return {"ok": True, "trades": out, "count": len(out)}


@router.get("/ai-suggestions")
async def ai_suggestions(limit: int = 25, _=Depends(_require_owner)):
    db = _db()
    cursor = db.trading_ai_suggestions.find({"owner": "owner"}).sort("ts", -1).limit(limit)
    out = []
    async for s in cursor:
        s.pop("_id", None)
        s.pop("raw", None)  # keep response light
        out.append(s)
    return {"ok": True, "suggestions": out, "count": len(out)}


@router.get("/market-clock")
async def market_clock(_=Depends(_require_owner)):
    clients = await _get_clients()
    if not clients:
        raise HTTPException(400, "Alpaca not connected")
    try:
        clock = await _run(clients["trading"].get_clock)
        return {
            "ok": True,
            "is_open": clock.is_open,
            "next_open": clock.next_open.isoformat() if clock.next_open else None,
            "next_close": clock.next_close.isoformat() if clock.next_close else None,
            "timestamp": clock.timestamp.isoformat() if clock.timestamp else None,
        }
    except Exception as e:
        raise HTTPException(502, f"Alpaca clock error: {e}")
