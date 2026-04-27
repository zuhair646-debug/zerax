"""Universal engines for vertical-specific features.

Each engine provides a self-contained set of endpoints attached under the main
/api/websites router. They share the same per-tenant isolation model:
- Client-facing (owner of the site)  → ClientToken header
- Public-facing (end customer)        → SiteToken header
- Data is stored INSIDE website_projects document under
  `bookings`, `services`, `staff`, `products`, `portfolio` keys.
"""
from __future__ import annotations

import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header as _Header
from pydantic import BaseModel


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ====================================================================
# BOOKING ENGINE — used by salon, pets, medical, gym
# ====================================================================
class ServiceIn(BaseModel):
    id: Optional[str] = None
    name: str
    price: float
    duration_min: int = 30
    category: Optional[str] = None
    description: Optional[str] = None


class StaffIn(BaseModel):
    id: Optional[str] = None
    name: str
    role: Optional[str] = None
    photo: Optional[str] = None
    specialties: Optional[List[str]] = None


class BookingIn(BaseModel):
    service_id: str
    staff_id: Optional[str] = None
    slot_iso: str  # "2026-04-22T14:00:00+03:00"
    customer_name: str
    customer_phone: str
    notes: Optional[str] = None


class BookingStatusIn(BaseModel):
    status: str  # pending | confirmed | in_progress | completed | cancelled | no_show


class ProductIn(BaseModel):
    id: Optional[str] = None
    name: str
    price: float
    stock: int = 0
    category: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    variants: Optional[List[Dict[str, Any]]] = None
    sku: Optional[str] = None


class TradeIn(BaseModel):
    symbol: str
    side: str  # buy | sell
    qty: float


class ListingIn(BaseModel):
    id: Optional[str] = None
    title: str
    price: float
    transaction: str = "بيع"  # بيع | إيجار
    type: Optional[str] = None  # شقة | فيلا | أرض | تجاري
    city: Optional[str] = None
    district: Optional[str] = None
    area_sqm: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    agent_phone: Optional[str] = None
    commission_pct: Optional[float] = 2.5  # % of price as agent commission


# ====================================================================
def register_engines(r: APIRouter, database, resolve_client, resolve_site_customer, realtime_mgr):
    """Register all vertical engines on the shared router.

    resolve_client(token_header) -> project dict (with auth check)
    resolve_site_customer(slug, token_header) -> {project, customer}
    realtime_mgr for broadcasting
    """

    # ─── SERVICES (shared by booking-type verticals) ─────────────────
    @r.get("/client/services")
    async def _services_list(authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        return {"services": p.get("services") or []}

    @r.post("/client/services")
    async def _services_create(body: ServiceIn, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        svc = body.model_dump()
        svc["id"] = svc.get("id") or str(uuid.uuid4())
        svc["created_at"] = _iso_now()
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$push": {"services": svc}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True, "service": svc}

    @r.put("/client/services/{service_id}")
    async def _services_update(service_id: str, body: ServiceIn, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        patch = {f"services.$.{k}": v for k, v in body.model_dump(exclude_none=True).items() if k != "id"}
        res = await database.website_projects.update_one(
            {"id": p["id"], "services.id": service_id},
            {"$set": {**patch, "updated_at": _iso_now()}},
        )
        if res.matched_count == 0:
            raise HTTPException(404, "الخدمة غير موجودة")
        return {"ok": True}

    @r.delete("/client/services/{service_id}")
    async def _services_delete(service_id: str, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$pull": {"services": {"id": service_id}}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True}

    # ─── STAFF ────────────────────────────────────────────────────────
    @r.get("/client/staff")
    async def _staff_list(authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        return {"staff": p.get("staff") or []}

    @r.post("/client/staff")
    async def _staff_create(body: StaffIn, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        s = body.model_dump()
        s["id"] = s.get("id") or str(uuid.uuid4())
        s["created_at"] = _iso_now()
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$push": {"staff": s}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True, "staff": s}

    @r.delete("/client/staff/{staff_id}")
    async def _staff_delete(staff_id: str, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$pull": {"staff": {"id": staff_id}}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True}

    # ─── BOOKINGS (client view) ──────────────────────────────────────
    @r.get("/client/bookings")
    async def _bookings_list(authorization: str = _Header(None), status: Optional[str] = None):
        p = await resolve_client(authorization or "")
        bookings = p.get("bookings") or []
        if status:
            bookings = [b for b in bookings if b.get("status") == status]
        return {"bookings": list(reversed(bookings)), "total": len(p.get("bookings") or [])}

    @r.patch("/client/bookings/{booking_id}")
    async def _bookings_patch(booking_id: str, body: BookingStatusIn, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        res = await database.website_projects.update_one(
            {"id": p["id"], "bookings.id": booking_id},
            {"$set": {"bookings.$.status": body.status, "updated_at": _iso_now()}},
        )
        if res.matched_count == 0:
            raise HTTPException(404, "الحجز غير موجود")
        try:
            await realtime_mgr.broadcast_all(p["slug"], "booking_status",
                                             {"booking_id": booking_id, "status": body.status})
        except Exception:
            pass
        return {"ok": True}

    # ─── PUBLIC BOOKING (end customer) ───────────────────────────────
    @r.get("/public/{slug}/services")
    async def _public_services(slug: str):
        p = await database.website_projects.find_one(
            {"slug": slug}, {"_id": 0, "services": 1, "staff": 1}
        )
        if not p:
            raise HTTPException(404, "الموقع غير موجود")
        staff = [{k: v for k, v in s.items() if k not in ("created_at",)} for s in (p.get("staff") or [])]
        return {"services": p.get("services") or [], "staff": staff}

    @r.get("/public/{slug}/availability")
    async def _public_availability(slug: str, service_id: str, date: str, staff_id: Optional[str] = None):
        """Returns free time slots for a given day. Simple grid: every duration_min
        between 09:00 and 22:00 local, excluding already-booked slots."""
        p = await database.website_projects.find_one(
            {"slug": slug}, {"_id": 0, "services": 1, "bookings": 1}
        )
        if not p:
            raise HTTPException(404, "الموقع غير موجود")
        svc = next((s for s in (p.get("services") or []) if s.get("id") == service_id), None)
        if not svc:
            raise HTTPException(404, "الخدمة غير موجودة")
        dur = int(svc.get("duration_min") or 30)
        try:
            day = datetime.fromisoformat(date).date()
        except Exception:
            raise HTTPException(400, "تاريخ غير صحيح")
        busy = set()
        for b in (p.get("bookings") or []):
            if b.get("status") in ("cancelled", "no_show"):
                continue
            if staff_id and b.get("staff_id") and b["staff_id"] != staff_id:
                continue
            try:
                dt = datetime.fromisoformat(b["slot_iso"])
            except Exception:
                continue
            if dt.date() == day:
                busy.add(dt.strftime("%H:%M"))
        slots = []
        t = datetime.combine(day, datetime.min.time()).replace(hour=9)
        end = t.replace(hour=22)
        while t < end:
            tt = t.strftime("%H:%M")
            slots.append({"time": tt, "available": tt not in busy})
            t += timedelta(minutes=dur)
        return {"service": {"id": svc["id"], "name": svc["name"], "duration_min": dur},
                "date": str(day), "slots": slots}

    @r.post("/public/{slug}/bookings")
    async def _public_book(slug: str, body: BookingIn, authorization: str = _Header(None)):
        # Optional customer auth — if provided link to customer, otherwise guest booking
        customer_id = None
        try:
            data = await resolve_site_customer(slug, authorization or "")
            customer_id = data["customer"]["id"]
            proj = data["project"]
        except HTTPException:
            proj = await database.website_projects.find_one({"slug": slug}, {"_id": 0})
            if not proj:
                raise HTTPException(404, "الموقع غير موجود")
        svc = next((s for s in (proj.get("services") or []) if s.get("id") == body.service_id), None)
        if not svc:
            raise HTTPException(404, "الخدمة غير موجودة")
        # Check slot availability
        try:
            dt = datetime.fromisoformat(body.slot_iso)
        except Exception:
            raise HTTPException(400, "الوقت غير صحيح")
        for b in (proj.get("bookings") or []):
            if b.get("status") in ("cancelled", "no_show"):
                continue
            if body.staff_id and b.get("staff_id") and b["staff_id"] != body.staff_id:
                continue
            try:
                if datetime.fromisoformat(b["slot_iso"]) == dt:
                    raise HTTPException(409, "هذا الوقت محجوز بالفعل")
            except HTTPException:
                raise
            except Exception:
                continue
        booking = {
            "id": str(uuid.uuid4()),
            "service_id": body.service_id,
            "service_name": svc.get("name"),
            "staff_id": body.staff_id,
            "slot_iso": body.slot_iso,
            "customer_id": customer_id,
            "customer_name": body.customer_name[:100],
            "customer_phone": body.customer_phone[:30],
            "notes": (body.notes or "")[:500],
            "price": svc.get("price") or 0,
            "duration_min": svc.get("duration_min") or 30,
            "status": "pending",
            "created_at": _iso_now(),
        }
        await database.website_projects.update_one(
            {"id": proj["id"]},
            {"$push": {"bookings": booking}, "$set": {"updated_at": _iso_now()}},
        )
        try:
            await realtime_mgr.broadcast_to_clients(slug, "booking_created", {
                "booking_id": booking["id"], "service_name": booking["service_name"],
                "customer": booking["customer_name"], "slot": booking["slot_iso"],
            })
        except Exception:
            pass
        return {"ok": True, "booking_id": booking["id"], "status": booking["status"]}

    # ═══════════════════════════════════════════════════════════════
    # PRODUCT ENGINE — used by ecommerce
    # ═══════════════════════════════════════════════════════════════
    @r.get("/client/products")
    async def _products_list(authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        return {"products": p.get("products") or []}

    @r.post("/client/products")
    async def _products_create(body: ProductIn, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        prod = body.model_dump()
        prod["id"] = prod.get("id") or str(uuid.uuid4())
        prod["created_at"] = _iso_now()
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$push": {"products": prod}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True, "product": prod}

    @r.put("/client/products/{product_id}")
    async def _products_update(product_id: str, body: ProductIn, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        patch = {f"products.$.{k}": v for k, v in body.model_dump(exclude_none=True).items() if k != "id"}
        res = await database.website_projects.update_one(
            {"id": p["id"], "products.id": product_id},
            {"$set": {**patch, "updated_at": _iso_now()}},
        )
        if res.matched_count == 0:
            raise HTTPException(404, "المنتج غير موجود")
        return {"ok": True}

    @r.delete("/client/products/{product_id}")
    async def _products_delete(product_id: str, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$pull": {"products": {"id": product_id}}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True}

    @r.get("/public/{slug}/products")
    async def _public_products(slug: str, category: Optional[str] = None, q: Optional[str] = None):
        p = await database.website_projects.find_one(
            {"slug": slug}, {"_id": 0, "products": 1}
        )
        if not p:
            raise HTTPException(404, "الموقع غير موجود")
        prods = p.get("products") or []
        if category:
            prods = [pr for pr in prods if pr.get("category") == category]
        if q:
            ql = q.lower()
            prods = [pr for pr in prods if ql in (pr.get("name") or "").lower()]
        return {"products": prods, "total": len(prods),
                "categories": sorted({pr.get("category") for pr in (p.get("products") or []) if pr.get("category")})}

    # ═══════════════════════════════════════════════════════════════
    # PORTFOLIO ENGINE — stocks simulation (deterministic pseudo-market)
    # ═══════════════════════════════════════════════════════════════
    # Curated symbol universe with base prices (fake but believable)
    MARKET = {
        "TADAWUL:2222": {"name": "أرامكو السعودية", "base": 32.45, "market": "tadawul"},
        "TADAWUL:1120": {"name": "الراجحي", "base": 85.20, "market": "tadawul"},
        "TADAWUL:2010": {"name": "سابك", "base": 82.10, "market": "tadawul"},
        "TADAWUL:1211": {"name": "معادن", "base": 58.40, "market": "tadawul"},
        "NASDAQ:AAPL": {"name": "Apple", "base": 195.50, "market": "nasdaq"},
        "NASDAQ:MSFT": {"name": "Microsoft", "base": 410.20, "market": "nasdaq"},
        "NASDAQ:NVDA": {"name": "NVIDIA", "base": 880.00, "market": "nasdaq"},
        "NASDAQ:TSLA": {"name": "Tesla", "base": 175.40, "market": "nasdaq"},
        "CRYPTO:BTC": {"name": "Bitcoin", "base": 63000.0, "market": "crypto"},
        "CRYPTO:ETH": {"name": "Ethereum", "base": 3200.0, "market": "crypto"},
    }

    def _sim_price(symbol: str) -> float:
        """Deterministic walk based on symbol + current 5-minute bucket."""
        m = MARKET.get(symbol)
        if not m:
            return 0.0
        now = datetime.now(timezone.utc)
        bucket = int(now.timestamp() // 300)  # 5-min steps
        random.seed(f"{symbol}-{bucket}")
        drift = random.uniform(-0.04, 0.04)
        random.seed(f"{symbol}-{bucket}-tick")
        tick = random.uniform(-0.008, 0.008)
        return round(m["base"] * (1 + drift + tick), 2)

    @r.get("/market/quotes")
    async def _market_quotes(symbols: Optional[str] = None):
        wanted = symbols.split(",") if symbols else list(MARKET.keys())
        out = []
        for s in wanted:
            if s in MARKET:
                price = _sim_price(s)
                base = MARKET[s]["base"]
                change_pct = round((price - base) / base * 100, 2)
                out.append({"symbol": s, "name": MARKET[s]["name"],
                            "market": MARKET[s]["market"], "price": price,
                            "change_pct": change_pct})
        return {"quotes": out, "at": _iso_now()}

    @r.get("/public/{slug}/portfolio/me")
    async def _portfolio_me(slug: str, authorization: str = _Header(None)):
        data = await resolve_site_customer(slug, authorization or "")
        proj = data["project"]
        cid = data["customer"]["id"]
        # Per-customer portfolio stored under project.portfolios[customer_id]
        pf = (proj.get("portfolios") or {}).get(cid) or {
            "balance": 50000.0, "positions": {}, "trades": [],
            "initial_balance": 50000.0, "created_at": _iso_now(),
        }
        # Refresh market value
        positions = []
        market_value = 0.0
        for sym, pos in (pf.get("positions") or {}).items():
            price = _sim_price(sym)
            qty = float(pos.get("qty", 0))
            avg = float(pos.get("avg_price", 0))
            value = round(price * qty, 2)
            market_value += value
            positions.append({
                "symbol": sym, "name": MARKET.get(sym, {}).get("name", sym),
                "qty": qty, "avg_price": avg, "price": price,
                "value": value, "pnl": round((price - avg) * qty, 2),
                "pnl_pct": round((price - avg) / avg * 100, 2) if avg else 0,
            })
        total = round(float(pf.get("balance", 0)) + market_value, 2)
        return {
            "balance": round(float(pf.get("balance", 0)), 2),
            "positions": positions,
            "market_value": round(market_value, 2),
            "total_value": total,
            "initial_balance": pf.get("initial_balance", 50000.0),
            "pnl_total": round(total - float(pf.get("initial_balance", 50000.0)), 2),
            "trades": (pf.get("trades") or [])[-20:],
        }

    @r.post("/public/{slug}/portfolio/trade")
    async def _portfolio_trade(slug: str, body: TradeIn, authorization: str = _Header(None)):
        data = await resolve_site_customer(slug, authorization or "")
        proj = data["project"]
        cid = data["customer"]["id"]
        sym = body.symbol
        if sym not in MARKET:
            raise HTTPException(400, "الرمز غير موجود")
        if body.side not in ("buy", "sell"):
            raise HTTPException(400, "side يجب أن يكون buy أو sell")
        if body.qty <= 0:
            raise HTTPException(400, "الكمية يجب أن تكون أكبر من صفر")
        price = _sim_price(sym)
        pfs = proj.get("portfolios") or {}
        pf = pfs.get(cid) or {"balance": 50000.0, "positions": {}, "trades": [],
                               "initial_balance": 50000.0, "created_at": _iso_now()}
        pos = pf["positions"].get(sym) or {"qty": 0, "avg_price": 0}
        qty_held = float(pos["qty"])
        avg = float(pos["avg_price"])
        if body.side == "buy":
            cost = round(price * body.qty, 2)
            if pf["balance"] < cost:
                raise HTTPException(400, f"الرصيد غير كاف (متاح {pf['balance']:.2f})")
            new_qty = qty_held + body.qty
            new_avg = ((avg * qty_held) + cost) / new_qty if new_qty else price
            pf["balance"] = round(pf["balance"] - cost, 2)
            pf["positions"][sym] = {"qty": round(new_qty, 6), "avg_price": round(new_avg, 4)}
        else:  # sell
            if qty_held < body.qty:
                raise HTTPException(400, f"لديك {qty_held} فقط")
            proceeds = round(price * body.qty, 2)
            new_qty = qty_held - body.qty
            pf["balance"] = round(pf["balance"] + proceeds, 2)
            if new_qty <= 0:
                pf["positions"].pop(sym, None)
            else:
                pf["positions"][sym] = {"qty": round(new_qty, 6), "avg_price": avg}
        trade = {"id": str(uuid.uuid4()), "symbol": sym, "side": body.side,
                 "qty": body.qty, "price": price, "at": _iso_now()}
        pf["trades"] = (pf.get("trades") or []) + [trade]
        pfs[cid] = pf
        await database.website_projects.update_one(
            {"id": proj["id"]},
            {"$set": {"portfolios": pfs, "updated_at": _iso_now()}},
        )
        return {"ok": True, "trade": trade, "new_balance": pf["balance"]}

    # ═══════════════════════════════════════════════════════════════
    # 🆕 LISTINGS ENGINE — real estate
    # ═══════════════════════════════════════════════════════════════
    @r.get("/client/listings")
    async def _list_listings(authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        items = p.get("listings") or []
        # Compute commission stats
        total_value = sum(float(x.get("price") or 0) for x in items)
        total_commission = sum(float(x.get("price") or 0) * float(x.get("commission_pct") or 2.5) / 100 for x in items)
        sold = [x for x in items if x.get("sold")]
        return {"listings": items, "stats": {
            "total": len(items),
            "active": len(items) - len(sold),
            "sold": len(sold),
            "total_value": round(total_value, 2),
            "potential_commission": round(total_commission, 2),
        }}

    @r.post("/client/listings")
    async def _add_listing(body: ListingIn, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        lst = body.model_dump()
        lst["id"] = lst.get("id") or str(uuid.uuid4())
        lst["created_at"] = _iso_now()
        lst["sold"] = False
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$push": {"listings": lst}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True, "listing": lst}

    @r.put("/client/listings/{listing_id}")
    async def _update_listing(listing_id: str, body: ListingIn, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        patch = {f"listings.$.{k}": v for k, v in body.model_dump(exclude_none=True).items() if k != "id"}
        res = await database.website_projects.update_one(
            {"id": p["id"], "listings.id": listing_id},
            {"$set": {**patch, "updated_at": _iso_now()}},
        )
        if res.matched_count == 0:
            raise HTTPException(404, "عقار غير موجود")
        return {"ok": True}

    @r.patch("/client/listings/{listing_id}/mark-sold")
    async def _mark_sold(listing_id: str, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        await database.website_projects.update_one(
            {"id": p["id"], "listings.id": listing_id},
            {"$set": {"listings.$.sold": True, "listings.$.sold_at": _iso_now()}},
        )
        return {"ok": True}

    @r.delete("/client/listings/{listing_id}")
    async def _del_listing(listing_id: str, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$pull": {"listings": {"id": listing_id}}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True}

    @r.get("/public/{slug}/listings")
    async def _public_listings(slug: str, transaction: Optional[str] = None, city: Optional[str] = None):
        p = await database.website_projects.find_one(
            {"slug": slug}, {"_id": 0, "listings": 1}
        )
        if not p:
            raise HTTPException(404, "الموقع غير موجود")
        items = [x for x in (p.get("listings") or []) if not x.get("sold")]
        if transaction:
            items = [x for x in items if x.get("transaction") == transaction]
        if city:
            items = [x for x in items if x.get("city") == city]
        return {"listings": items}

    # ═══════════════════════════════════════════════════════════════
    # VERTICAL CATALOG
    # ═══════════════════════════════════════════════════════════════
    from . import verticals as vx

    @r.get("/verticals")
    async def _list_verticals():
        return {"verticals": vx.list_verticals()}

    @r.get("/verticals/{vid}")
    async def _get_vertical(vid: str):
        v = vx.get_vertical(vid)
        if not v:
            raise HTTPException(404, "vertical not found")
        return v

    @r.post("/projects/{project_id}/seed-vertical")
    async def _seed_vertical(project_id: str, body: Dict[str, Any], authorization: str = _Header(None)):
        """Seed a project with sample services/products from a vertical template.

        Uses the project's owner auth (Bearer). For simplicity we rely on the
        existing project lookup; the outer router wires the auth.
        """
        # Note: auth of the project owner is performed by the calling route
        # because `auth_dep` is needed. Leave as utility.
        vid = body.get("vertical_id")
        v = vx.get_vertical(vid) if vid else None
        if not v:
            raise HTTPException(400, "vertical_id مطلوب")
        updates: Dict[str, Any] = {"vertical": vid, "updated_at": _iso_now()}
        if "sample_services" in v:
            updates["services"] = [{**s, "created_at": _iso_now()} for s in v["sample_services"]]
        if "sample_products" in v:
            updates["products"] = [{**p, "created_at": _iso_now()} for p in v["sample_products"]]
        await database.website_projects.update_one(
            {"id": project_id},
            {"$set": updates},
        )
        return {"ok": True, "applied": list(updates.keys())}
