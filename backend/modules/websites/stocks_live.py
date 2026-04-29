"""
Alpha Vantage live market data — drop-in replacement for the simulated MARKET dict.

Notes:
  • Free tier: 25 requests/day (was 500/day pre-2024). Use aggressive in-memory caching.
  • If `ALPHA_VANTAGE_KEY` env var is missing OR API errors, we fall back to the
    deterministic simulation (so the storefront never breaks).
  • Saudi Tadawul tickers are NOT covered by Alpha Vantage — they keep using simulation.

Public API:
  await get_live_quotes(symbols)  → dict of {symbol: {price, change_pct, name, market}}
                                     symbols are in the same `MARKET:TICKER` format used by
                                     the engines module.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx


log = logging.getLogger(__name__)

# In-memory cache: symbol → (timestamp, payload)
_CACHE: Dict[str, tuple[float, Dict[str, Any]]] = {}
CACHE_TTL = 60.0  # seconds — generous to stay inside the 25/day free tier

# We rate-limit to 4 outbound API calls per minute total to avoid rate-limit responses
_RATE_BUCKET: List[float] = []
_RATE_LIMIT = 4
_RATE_WINDOW = 60.0


def _api_key() -> str:
    return (os.environ.get("ALPHA_VANTAGE_KEY") or "").strip()


def is_configured() -> bool:
    return bool(_api_key())


def _can_call_api() -> bool:
    now = time.time()
    _RATE_BUCKET[:] = [t for t in _RATE_BUCKET if now - t < _RATE_WINDOW]
    if len(_RATE_BUCKET) >= _RATE_LIMIT:
        return False
    _RATE_BUCKET.append(now)
    return True


async def _fetch_global_quote(client: httpx.AsyncClient, ticker: str) -> Optional[Dict[str, Any]]:
    try:
        r = await client.get(
            "https://www.alphavantage.co/query",
            params={"function": "GLOBAL_QUOTE", "symbol": ticker, "apikey": _api_key()},
            timeout=8.0,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        q = data.get("Global Quote") or data.get("globalQuote") or {}
        # Alpha Vantage uses oddly-numbered keys like "05. price"
        price_raw = q.get("05. price") or q.get("price")
        change_raw = q.get("10. change percent") or q.get("changePercent")
        if not price_raw:
            return None
        try:
            price = float(price_raw)
        except Exception:
            return None
        try:
            change_pct = float(str(change_raw or "0").replace("%", "").strip())
        except Exception:
            change_pct = 0.0
        return {"price": round(price, 2), "change_pct": round(change_pct, 2)}
    except Exception as e:
        log.debug("alpha_vantage GLOBAL_QUOTE failed for %s: %s", ticker, e)
        return None


async def _fetch_crypto_rate(client: httpx.AsyncClient, base: str) -> Optional[Dict[str, Any]]:
    try:
        r = await client.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": base, "to_currency": "USD",
                "apikey": _api_key(),
            },
            timeout=8.0,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        node = data.get("Realtime Currency Exchange Rate") or {}
        rate = node.get("5. Exchange Rate")
        if not rate:
            return None
        try:
            return {"price": round(float(rate), 2), "change_pct": 0.0}
        except Exception:
            return None
    except Exception as e:
        log.debug("alpha_vantage CRYPTO failed for %s: %s", base, e)
        return None


async def get_live_quotes(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """Returns a dict of {symbol: {price, change_pct}} — only for symbols that resolved.
    Symbols are in `MARKET:TICKER` format. Tadawul symbols are skipped (not supported)."""
    if not is_configured():
        return {}

    out: Dict[str, Dict[str, Any]] = {}
    to_fetch: List[str] = []

    now = time.time()
    for sym in symbols:
        cached = _CACHE.get(sym)
        if cached and (now - cached[0]) < CACHE_TTL:
            out[sym] = cached[1]
        else:
            to_fetch.append(sym)

    if not to_fetch:
        return out

    async with httpx.AsyncClient() as client:
        tasks = []
        for sym in to_fetch:
            if not _can_call_api():
                break
            market, _, ticker = sym.partition(":")
            if market.upper() == "NASDAQ":
                tasks.append((sym, _fetch_global_quote(client, ticker)))
            elif market.upper() == "CRYPTO":
                tasks.append((sym, _fetch_crypto_rate(client, ticker)))
            # Tadawul → leave to fallback simulation
        if tasks:
            results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
            for (sym, _), res in zip(tasks, results):
                if isinstance(res, dict):
                    _CACHE[sym] = (now, res)
                    out[sym] = res
    return out
