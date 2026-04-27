"""
engines_v2.py — Phase 2 vertical engines.

New engines added:
  • Courses Engine        → academy vertical (lessons, enrollments)
  • Memberships Engine    → gym + sports_club verticals (plans, subscriptions)
  • Events/Tickets Engine → art_gallery + any vertical (ticketed events)
  • Gold Ticker           → jewelry vertical (live-ish gold prices)
  • ISBN Search           → library vertical (Open Library lookup)
  • Driver Analytics      → weekly performance KPIs per driver

All endpoints are registered on the shared websites router at /api/websites/*.
"""
from __future__ import annotations

import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Header as _Header
from pydantic import BaseModel


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Pydantic models ─────────────────────────────────────────────────
class CourseIn(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    price: float = 0
    duration_hours: Optional[float] = None
    lessons: Optional[List[Dict[str, Any]]] = None
    category: Optional[str] = None
    instructor: Optional[str] = None
    image: Optional[str] = None
    level: Optional[str] = "beginner"  # beginner/intermediate/advanced


class EnrollmentIn(BaseModel):
    course_id: str
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = ""


class MembershipPlanIn(BaseModel):
    id: Optional[str] = None
    name: str
    price: float = 0
    period_days: int = 30  # 30=monthly, 365=yearly
    benefits: Optional[List[str]] = None
    max_bookings_per_month: Optional[int] = None
    featured: bool = False


class SubscribeIn(BaseModel):
    plan_id: str
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = ""


class EventIn(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    starts_at: str  # ISO
    ends_at: Optional[str] = None
    venue: Optional[str] = ""
    price: float = 0
    capacity: int = 100
    image: Optional[str] = None


class TicketIn(BaseModel):
    event_id: str
    quantity: int = 1
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = ""


def register_engines_v2(r: APIRouter, database, resolve_client, resolve_site_customer):
    """Mount all v2 engine routes on the shared router."""

    # ════════════════════════════════════════════════════════════════
    # 🎓 COURSES ENGINE — academy vertical
    # ════════════════════════════════════════════════════════════════
    @r.get("/client/courses")
    async def _courses_list(authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        return {"courses": p.get("courses") or []}

    @r.post("/client/courses")
    async def _courses_create(body: CourseIn, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        c = body.model_dump()
        c["id"] = c.get("id") or f"crs_{uuid.uuid4().hex[:8]}"
        c["created_at"] = _iso_now()
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$push": {"courses": c}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True, "course": c}

    @r.patch("/client/courses/{course_id}")
    async def _courses_update(course_id: str, body: CourseIn, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        courses = [{**c, **{k: v for k, v in body.model_dump(exclude_none=True).items() if k != "id"}} if c.get("id") == course_id else c for c in (p.get("courses") or [])]
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$set": {"courses": courses, "updated_at": _iso_now()}}
        )
        return {"ok": True}

    @r.delete("/client/courses/{course_id}")
    async def _courses_delete(course_id: str, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        courses = [c for c in (p.get("courses") or []) if c.get("id") != course_id]
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$set": {"courses": courses, "updated_at": _iso_now()}}
        )
        return {"ok": True}

    @r.get("/public/{slug}/courses")
    async def _public_courses(slug: str):
        p = await database.website_projects.find_one({"slug": slug, "status": "approved"}, {"_id": 0})
        if not p:
            raise HTTPException(404, "Site not found")
        return {"courses": p.get("courses") or []}

    @r.post("/public/{slug}/enroll")
    async def _public_enroll(slug: str, body: EnrollmentIn):
        p = await database.website_projects.find_one({"slug": slug, "status": "approved"}, {"_id": 0})
        if not p:
            raise HTTPException(404, "Site not found")
        course = next((c for c in (p.get("courses") or []) if c.get("id") == body.course_id), None)
        if not course:
            raise HTTPException(404, "Course not found")
        enrollment = {
            "id": f"enr_{uuid.uuid4().hex[:8]}",
            "course_id": body.course_id,
            "course_title": course.get("title"),
            "customer_name": body.customer_name,
            "customer_phone": body.customer_phone,
            "customer_email": body.customer_email,
            "price": course.get("price", 0),
            "status": "pending",
            "created_at": _iso_now(),
        }
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$push": {"enrollments": enrollment}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True, "enrollment": enrollment}

    @r.get("/client/enrollments")
    async def _enrollments_list(authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        return {"enrollments": p.get("enrollments") or []}

    # ════════════════════════════════════════════════════════════════
    # 🏋️ MEMBERSHIPS ENGINE — gym, sports_club verticals
    # ════════════════════════════════════════════════════════════════
    @r.get("/client/membership-plans")
    async def _plans_list(authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        return {"plans": p.get("membership_plans") or []}

    @r.post("/client/membership-plans")
    async def _plans_create(body: MembershipPlanIn, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        plan = body.model_dump()
        plan["id"] = plan.get("id") or f"pln_{uuid.uuid4().hex[:8]}"
        plan["created_at"] = _iso_now()
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$push": {"membership_plans": plan}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True, "plan": plan}

    @r.delete("/client/membership-plans/{plan_id}")
    async def _plans_delete(plan_id: str, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        plans = [x for x in (p.get("membership_plans") or []) if x.get("id") != plan_id]
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$set": {"membership_plans": plans, "updated_at": _iso_now()}}
        )
        return {"ok": True}

    @r.post("/public/{slug}/subscribe")
    async def _subscribe(slug: str, body: SubscribeIn):
        p = await database.website_projects.find_one({"slug": slug, "status": "approved"}, {"_id": 0})
        if not p:
            raise HTTPException(404, "Site not found")
        plan = next((x for x in (p.get("membership_plans") or []) if x.get("id") == body.plan_id), None)
        if not plan:
            raise HTTPException(404, "Plan not found")
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=int(plan.get("period_days", 30)))
        sub = {
            "id": f"sub_{uuid.uuid4().hex[:8]}",
            "plan_id": plan["id"],
            "plan_name": plan.get("name"),
            "customer_name": body.customer_name,
            "customer_phone": body.customer_phone,
            "customer_email": body.customer_email,
            "price": plan.get("price", 0),
            "starts_at": start.isoformat(),
            "ends_at": end.isoformat(),
            "status": "active",
            "created_at": _iso_now(),
        }
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$push": {"subscriptions": sub}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True, "subscription": sub}

    @r.get("/client/subscriptions")
    async def _subs_list(authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        subs = p.get("subscriptions") or []
        # Enrich with status_computed (active / expired)
        now_iso = _iso_now()
        for s in subs:
            s["status_computed"] = "active" if (s.get("ends_at", "9999") > now_iso) else "expired"
        return {"subscriptions": subs}

    # ════════════════════════════════════════════════════════════════
    # 🎫 EVENTS / TICKETS ENGINE
    # ════════════════════════════════════════════════════════════════
    @r.get("/client/events")
    async def _events_list(authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        events = p.get("events") or []
        # Enrich with tickets_sold count
        tickets = p.get("tickets") or []
        for e in events:
            sold = sum(t.get("quantity", 1) for t in tickets if t.get("event_id") == e.get("id"))
            e["tickets_sold"] = sold
            e["tickets_available"] = max(0, int(e.get("capacity", 100)) - sold)
        return {"events": events}

    @r.post("/client/events")
    async def _events_create(body: EventIn, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        ev = body.model_dump()
        ev["id"] = ev.get("id") or f"evt_{uuid.uuid4().hex[:8]}"
        ev["created_at"] = _iso_now()
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$push": {"events": ev}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True, "event": ev}

    @r.delete("/client/events/{event_id}")
    async def _events_delete(event_id: str, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        events = [e for e in (p.get("events") or []) if e.get("id") != event_id]
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$set": {"events": events, "updated_at": _iso_now()}}
        )
        return {"ok": True}

    @r.get("/public/{slug}/events")
    async def _public_events(slug: str):
        p = await database.website_projects.find_one({"slug": slug, "status": "approved"}, {"_id": 0})
        if not p:
            raise HTTPException(404, "Site not found")
        events = p.get("events") or []
        tickets = p.get("tickets") or []
        for e in events:
            sold = sum(t.get("quantity", 1) for t in tickets if t.get("event_id") == e.get("id"))
            e["tickets_available"] = max(0, int(e.get("capacity", 100)) - sold)
        return {"events": events}

    @r.post("/public/{slug}/buy-ticket")
    async def _buy_ticket(slug: str, body: TicketIn):
        p = await database.website_projects.find_one({"slug": slug, "status": "approved"}, {"_id": 0})
        if not p:
            raise HTTPException(404, "Site not found")
        event = next((e for e in (p.get("events") or []) if e.get("id") == body.event_id), None)
        if not event:
            raise HTTPException(404, "Event not found")
        # Capacity check
        sold = sum(t.get("quantity", 1) for t in (p.get("tickets") or []) if t.get("event_id") == body.event_id)
        remaining = max(0, int(event.get("capacity", 100)) - sold)
        if body.quantity > remaining:
            raise HTTPException(400, f"المقاعد المتبقية: {remaining}")
        ticket = {
            "id": f"tkt_{uuid.uuid4().hex[:8]}",
            "event_id": body.event_id,
            "event_title": event.get("title"),
            "quantity": body.quantity,
            "customer_name": body.customer_name,
            "customer_phone": body.customer_phone,
            "customer_email": body.customer_email,
            "total": float(event.get("price", 0)) * body.quantity,
            "status": "paid",
            "created_at": _iso_now(),
        }
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$push": {"tickets": ticket}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True, "ticket": ticket}

    @r.get("/client/tickets")
    async def _tickets_list(authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        return {"tickets": p.get("tickets") or []}

    # ════════════════════════════════════════════════════════════════
    # 💰 GOLD TICKER — jewelry vertical
    # ════════════════════════════════════════════════════════════════
    # Simple cache: 10 minutes
    _gold_cache = {"at": None, "data": None}

    async def _fetch_gold_price() -> Dict[str, Any]:
        """Fetch current gold price (SAR/gram for common karats).
        Uses free API; falls back to reasonable estimates if offline.
        """
        now = datetime.now(timezone.utc)
        cached = _gold_cache.get("data")
        cache_at = _gold_cache.get("at")
        if cached and cache_at and (now - cache_at).total_seconds() < 600:
            return cached
        # Try free public API (metals.live is no-key). If fails, fallback.
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                # Simple free endpoint; may change — we guard with fallback
                resp = await client.get("https://api.gold-api.com/price/XAU")
                resp.raise_for_status()
                j = resp.json()
                # XAU ounce in USD → convert to SAR/gram (1oz = 31.1035g, 1 USD ≈ 3.75 SAR)
                usd_per_oz = float(j.get("price", 2050))
                sar_per_gram_24 = (usd_per_oz * 3.75) / 31.1035
                out = {
                    "source": "gold-api.com",
                    "currency": "SAR",
                    "per_gram": {
                        "24k": round(sar_per_gram_24, 2),
                        "22k": round(sar_per_gram_24 * 22 / 24, 2),
                        "21k": round(sar_per_gram_24 * 21 / 24, 2),
                        "18k": round(sar_per_gram_24 * 18 / 24, 2),
                    },
                    "fetched_at": now.isoformat(),
                    "live": True,
                }
        except Exception:
            # Realistic fallback (approx Feb 2026)
            base = 302.0
            out = {
                "source": "fallback",
                "currency": "SAR",
                "per_gram": {
                    "24k": base,
                    "22k": round(base * 22 / 24, 2),
                    "21k": round(base * 21 / 24, 2),
                    "18k": round(base * 18 / 24, 2),
                },
                "fetched_at": now.isoformat(),
                "live": False,
            }
        _gold_cache["data"] = out
        _gold_cache["at"] = now
        return out

    @r.get("/gold-prices")
    async def _gold_prices():
        return await _fetch_gold_price()

    @r.get("/public/{slug}/gold-prices")
    async def _public_gold_prices(slug: str):
        # Public ticker for jewelry sites
        p = await database.website_projects.find_one({"slug": slug, "status": "approved"}, {"_id": 0, "vertical": 1})
        if not p:
            raise HTTPException(404, "Site not found")
        return await _fetch_gold_price()

    # ════════════════════════════════════════════════════════════════
    # 📚 ISBN SEARCH — library vertical
    # ════════════════════════════════════════════════════════════════
    @r.get("/isbn-search")
    async def _isbn_search(isbn: str):
        """Look up book metadata from Open Library by ISBN."""
        isbn = (isbn or "").strip().replace("-", "").replace(" ", "")
        if not isbn or len(isbn) not in (10, 13):
            raise HTTPException(400, "ISBN غير صالح (10 أو 13 رقم)")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r1 = await client.get(f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data")
                r1.raise_for_status()
                j = r1.json()
                key = f"ISBN:{isbn}"
                if key not in j:
                    return {"found": False, "isbn": isbn}
                book = j[key]
                return {
                    "found": True,
                    "isbn": isbn,
                    "title": book.get("title"),
                    "authors": [a.get("name") for a in (book.get("authors") or [])],
                    "publishers": [p.get("name") for p in (book.get("publishers") or [])],
                    "publish_date": book.get("publish_date"),
                    "number_of_pages": book.get("number_of_pages"),
                    "cover": (book.get("cover") or {}).get("medium") or (book.get("cover") or {}).get("large"),
                    "url": book.get("url"),
                    "subjects": [s.get("name") for s in (book.get("subjects") or [])][:8],
                }
        except httpx.HTTPError:
            raise HTTPException(503, "خدمة البحث غير متاحة حالياً")

    # ════════════════════════════════════════════════════════════════
    # 📊 DRIVER WEEKLY ANALYTICS
    # ════════════════════════════════════════════════════════════════
    @r.get("/client/drivers/analytics")
    async def _drivers_analytics(days: int = 7, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        days = max(1, min(90, int(days)))
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        drivers = p.get("drivers") or []
        orders = [o for o in (p.get("orders") or []) if o.get("created_at", "") >= cutoff]
        results = []
        for d in drivers:
            did = d.get("id")
            d_orders = [o for o in orders if o.get("assigned_driver") == did or o.get("driver_id") == did]
            completed = [o for o in d_orders if o.get("status") in ("delivered", "completed")]
            # Delivery time: delivered_at - assigned_at (in minutes)
            delivery_times = []
            for o in completed:
                try:
                    assigned = o.get("assigned_at") or o.get("created_at")
                    delivered = o.get("delivered_at") or o.get("updated_at")
                    if assigned and delivered:
                        a = datetime.fromisoformat(assigned.replace("Z", "+00:00"))
                        b = datetime.fromisoformat(delivered.replace("Z", "+00:00"))
                        mins = (b - a).total_seconds() / 60
                        if 0 < mins < 360:  # sanity cap 6h
                            delivery_times.append(mins)
                except Exception:
                    pass
            ratings = [float(o.get("rating")) for o in completed if o.get("rating") is not None]
            avg_delivery = round(sum(delivery_times) / len(delivery_times), 1) if delivery_times else None
            avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
            total_earnings = sum(float(o.get("total", 0)) for o in completed)
            results.append({
                "driver_id": did,
                "driver_name": d.get("name"),
                "phone": d.get("phone"),
                "orders_assigned": len(d_orders),
                "orders_completed": len(completed),
                "completion_rate": round(100 * len(completed) / len(d_orders), 1) if d_orders else 0,
                "avg_delivery_min": avg_delivery,
                "avg_rating": avg_rating,
                "total_earnings": round(total_earnings, 2),
                "status": d.get("status", "offline"),
            })
        # Sort by orders_completed desc
        results.sort(key=lambda x: x["orders_completed"], reverse=True)
        return {
            "window_days": days,
            "since": cutoff,
            "total_drivers": len(drivers),
            "total_orders": len(orders),
            "drivers": results,
        }
