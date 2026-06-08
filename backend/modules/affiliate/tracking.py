"""
Affiliate Marketing — Full Tracking & Analytics Engine

Builds on top of /app/backend/modules/affiliate/routes.py:
- Click tracking with source detection (Referer + UTM)
- Cookie-based attribution (30-day window)
- Post management (where affiliates publish their links)
- Funnel analytics: click → signup → paid
- Per-affiliate impact reports (CR, AOV, ROI)
- Admin views: list affiliates, deep-dive impact, leaderboards

Collections:
  affiliate_clicks  — every link click (NEW)
    { id, code, ip, country, device, browser, os, referer, referer_host,
      utm_source, utm_medium, utm_campaign, utm_content, post_url,
      user_agent, landing_url, created_at,
      converted_to_signup (bool), signup_user_id, signup_at,
      became_paid (bool), paid_at, total_paid_usd }
  affiliate_posts   — where the affiliate published their link (NEW)
    { id, affiliate_user_id, platform, post_url, note, created_at, last_click_at, clicks_30d }
"""
from __future__ import annotations
import os
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("zitex.affiliate.tracking")

router = APIRouter(tags=["affiliate-tracking"])


class PostIn(BaseModel):
    post_url: str
    platform: Optional[str] = None
    note: Optional[str] = None


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: Any) -> Optional[str]:
    if not d:
        return None
    if isinstance(d, datetime):
        return d.isoformat()
    return str(d)


# Known social/messaging platforms — match Referer host or UTM source
_PLATFORM_MAP = {
    "twitter.com": "twitter", "t.co": "twitter", "x.com": "twitter",
    "facebook.com": "facebook", "fb.com": "facebook", "m.facebook.com": "facebook", "l.facebook.com": "facebook",
    "instagram.com": "instagram", "l.instagram.com": "instagram",
    "youtube.com": "youtube", "youtu.be": "youtube",
    "tiktok.com": "tiktok", "vm.tiktok.com": "tiktok",
    "linkedin.com": "linkedin",
    "snapchat.com": "snapchat",
    "telegram.org": "telegram", "t.me": "telegram",
    "whatsapp.com": "whatsapp", "wa.me": "whatsapp", "api.whatsapp.com": "whatsapp",
    "reddit.com": "reddit", "old.reddit.com": "reddit",
    "discord.com": "discord", "discord.gg": "discord",
    "pinterest.com": "pinterest",
    "google.com": "google", "google.com.sa": "google", "www.google.com": "google",
    "bing.com": "bing", "duckduckgo.com": "duckduckgo",
}


def _classify_platform(referer: str, utm_source: str) -> str:
    """Best-effort classification of the traffic source platform."""
    if utm_source:
        s = utm_source.lower().strip()
        # Normalise common variants
        if s in {"tw", "twitter", "x"}:
            return "twitter"
        if s in {"ig", "insta", "instagram"}:
            return "instagram"
        if s in {"fb", "facebook"}:
            return "facebook"
        if s in {"yt", "youtube"}:
            return "youtube"
        if s in {"tt", "tiktok"}:
            return "tiktok"
        if s in {"li", "linkedin"}:
            return "linkedin"
        if s in {"wa", "whatsapp"}:
            return "whatsapp"
        if s in {"tg", "telegram"}:
            return "telegram"
        if s in {"sc", "snap", "snapchat"}:
            return "snapchat"
        return s  # whatever they wrote (email/blog/etc.)
    if referer:
        try:
            host = urlparse(referer).netloc.lower()
            for k, v in _PLATFORM_MAP.items():
                if k in host:
                    return v
        except Exception:
            pass
    return "direct"


def _parse_ua(ua: str) -> Dict[str, str]:
    if not ua:
        return {"device": "unknown", "browser": "unknown", "os": "unknown"}
    ua_l = ua.lower()
    device = "mobile" if any(k in ua_l for k in ("mobile", "iphone", "android")) else "desktop"
    if "ipad" in ua_l or "tablet" in ua_l:
        device = "tablet"
    browser = "other"
    for b in ("edg/", "edge", "chrome", "firefox", "safari", "opera"):
        if b in ua_l:
            browser = b.replace("/", "").replace("edg", "edge")
            break
    osys = "other"
    for o in ("windows", "mac os", "macintosh", "iphone", "ipad", "android", "linux"):
        if o in ua_l:
            osys = "mac" if o == "macintosh" else o.replace(" ", "_")
            break
    return {"device": device, "browser": browser, "os": osys}


# ─────────────────────────────────────────────────────────────────
def build_router(db, get_current_user):

    # ============================================================
    # PUBLIC: redirect + click tracking
    # ============================================================
    @router.get("/r/{code}")
    async def affiliate_redirect(code: str, request: Request,
                                  s: Optional[str] = Query(None, description="utm_source shortcut"),
                                  m: Optional[str] = Query(None, description="utm_medium shortcut"),
                                  c: Optional[str] = Query(None, description="utm_campaign shortcut"),
                                  to: Optional[str] = Query(None, description="landing page slug")):
        """Affiliate landing endpoint. Logs click + sets attribution cookie + redirects."""
        code = (code or "").upper().strip()
        if not code or len(code) < 4:
            raise HTTPException(404, "رابط غير صحيح")
        aff = await db.affiliates.find_one({"code": code})
        if not aff:
            raise HTTPException(404, "رابط المسوّق غير موجود")

        # Capture request data
        ua = request.headers.get("user-agent", "")
        referer = request.headers.get("referer", "")
        ip = (request.headers.get("x-forwarded-for", "") or
              request.headers.get("x-real-ip", "") or
              (request.client.host if request.client else "") or "").split(",")[0].strip()
        # UTM (query params override aliases)
        qp = request.query_params
        utm_source = qp.get("utm_source") or s or ""
        utm_medium = qp.get("utm_medium") or m or ""
        utm_campaign = qp.get("utm_campaign") or c or ""
        utm_content = qp.get("utm_content") or ""
        post_url = qp.get("post") or ""

        platform = _classify_platform(referer, utm_source)
        ua_info = _parse_ua(ua)

        # Persist click
        try:
            click = {
                "id": __import__("uuid").uuid4().hex,
                "code": code,
                "affiliate_user_id": aff.get("user_id"),
                "ip": ip,
                "user_agent": ua,
                "referer": referer,
                "referer_host": (urlparse(referer).netloc.lower() if referer else ""),
                "platform": platform,
                "utm_source": utm_source,
                "utm_medium": utm_medium,
                "utm_campaign": utm_campaign,
                "utm_content": utm_content,
                "post_url": post_url,
                "device": ua_info["device"],
                "browser": ua_info["browser"],
                "os": ua_info["os"],
                "landing_url": to or "/",
                "created_at": _now(),
                "converted_to_signup": False,
                "became_paid": False,
            }
            await db.affiliate_clicks.insert_one(click)

            # Update per-post counters if a post_url was provided
            if post_url:
                await db.affiliate_posts.update_one(
                    {"affiliate_user_id": aff.get("user_id"), "post_url": post_url},
                    {"$set": {"last_click_at": _now()},
                     "$inc": {"clicks_total": 1}},
                    upsert=True,
                )
        except Exception:
            logger.exception("failed to log affiliate click")

        # Build destination URL
        landing = to or "/"
        if not landing.startswith("/"):
            landing = "/" + landing
        dest = f"{landing}?aff={code}"

        # Redirect + set attribution cookie (30 days)
        resp = RedirectResponse(url=dest, status_code=302)
        resp.set_cookie(
            "zitex_aff",
            code,
            max_age=60 * 60 * 24 * 30,  # 30 days
            httponly=False,
            samesite="lax",
            path="/",
        )
        # Also store click id so signup-binding is precise
        resp.set_cookie(
            "zitex_aff_click",
            click["id"],
            max_age=60 * 60 * 24 * 30,
            httponly=False,
            samesite="lax",
            path="/",
        )
        return resp

    # ============================================================
    # PUBLIC helper: called from signup handler to bind click → user
    # (server-side import, not exposed as an HTTP route)
    # ============================================================
    async def bind_click_to_signup(click_id: str, user_id: str):
        if not click_id or not user_id:
            return
        try:
            await db.affiliate_clicks.update_one(
                {"id": click_id},
                {"$set": {
                    "converted_to_signup": True,
                    "signup_user_id": user_id,
                    "signup_at": _now(),
                }},
            )
        except Exception:
            logger.exception("bind_click_to_signup failed")

    # Stash this helper on the router module so other modules can import it
    router.bind_click_to_signup = bind_click_to_signup  # type: ignore

    # ============================================================
    # AFFILIATE: my dashboard
    # ============================================================
    @router.get("/affiliate/me/dashboard")
    async def my_dashboard(user=Depends(get_current_user)):
        uid = user["user_id"]
        aff = await db.affiliates.find_one({"user_id": uid}, {"_id": 0})
        if not aff:
            return {"is_affiliate": False, "code": None}
        code = aff.get("code")

        # Time windows
        now = _now()
        d7 = now - timedelta(days=7)
        d30 = now - timedelta(days=30)

        async def _count(match):
            return await db.affiliate_clicks.count_documents(match)

        clicks_total = await _count({"code": code})
        clicks_7d = await _count({"code": code, "created_at": {"$gte": d7}})
        clicks_30d = await _count({"code": code, "created_at": {"$gte": d30}})
        unique_ip = len(await db.affiliate_clicks.distinct("ip", {"code": code, "created_at": {"$gte": d30}}))
        signups_total = await _count({"code": code, "converted_to_signup": True})
        signups_30d = await _count({"code": code, "converted_to_signup": True, "created_at": {"$gte": d30}})
        paid_total = await _count({"code": code, "became_paid": True})

        # Source breakdown (30d)
        platform_agg = await db.affiliate_clicks.aggregate([
            {"$match": {"code": code, "created_at": {"$gte": d30}}},
            {"$group": {"_id": "$platform", "clicks": {"$sum": 1}}},
            {"$sort": {"clicks": -1}},
        ]).to_list(length=30)

        # Device breakdown
        device_agg = await db.affiliate_clicks.aggregate([
            {"$match": {"code": code, "created_at": {"$gte": d30}}},
            {"$group": {"_id": "$device", "clicks": {"$sum": 1}}},
        ]).to_list(length=10)

        # Country breakdown — we don't geo-lookup here, but unique IPs give proxy
        # (extend later with MaxMind GeoIP if desired)

        # Daily timeseries (last 30d)
        daily = await db.affiliate_clicks.aggregate([
            {"$match": {"code": code, "created_at": {"$gte": d30}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "clicks": {"$sum": 1},
                "signups": {"$sum": {"$cond": ["$converted_to_signup", 1, 0]}},
            }},
            {"$sort": {"_id": 1}},
        ]).to_list(length=60)

        # Conversion rate
        cr_signup = round((signups_30d / clicks_30d * 100), 2) if clicks_30d else 0.0
        cr_paid = round((paid_total / signups_total * 100), 2) if signups_total else 0.0

        # Impact score 0-100: heuristic combining volume + quality
        # CR signup matters most (people from this affiliate convert)
        # plus monetary impact
        impact = min(100, int(
            min(clicks_30d, 500) * 0.05 +   # up to 25
            min(signups_30d, 100) * 0.5 +   # up to 50
            cr_signup * 0.3 +               # up to ~25
            float(aff.get("lifetime_earnings", 0)) * 0.5  # bonus
        ))

        return {
            "is_affiliate": True,
            "code": code,
            "status": aff.get("status"),
            "commission_pct": aff.get("commission_pct", 20.0),
            "earnings": {
                "pending_balance": float(aff.get("pending_balance", 0)),
                "paid_total": float(aff.get("paid_total", 0)),
                "lifetime_earnings": float(aff.get("lifetime_earnings", 0)),
            },
            "stats": {
                "clicks_total": clicks_total,
                "clicks_7d": clicks_7d,
                "clicks_30d": clicks_30d,
                "unique_visitors_30d": unique_ip,
                "signups_total": signups_total,
                "signups_30d": signups_30d,
                "paid_referrals_total": paid_total,
                "signup_conversion_pct": cr_signup,
                "paid_conversion_pct": cr_paid,
                "impact_score": impact,
            },
            "platforms": [{"platform": p["_id"] or "direct", "clicks": p["clicks"]} for p in platform_agg],
            "devices": [{"device": d["_id"] or "unknown", "clicks": d["clicks"]} for d in device_agg],
            "daily": [{"date": x["_id"], "clicks": x["clicks"], "signups": x["signups"]} for x in daily],
        }

    # ============================================================
    # AFFILIATE: posts (places they published the link)
    # ============================================================
    @router.get("/affiliate/me/posts")
    async def my_posts(user=Depends(get_current_user)):
        uid = user["user_id"]
        out = []
        async for p in db.affiliate_posts.find({"affiliate_user_id": uid}, {"_id": 0}, sort=[("last_click_at", -1)]):
            # Pull live click count from clicks collection (more reliable)
            clicks = await db.affiliate_clicks.count_documents({
                "affiliate_user_id": uid,
                "post_url": p.get("post_url"),
            })
            signups = await db.affiliate_clicks.count_documents({
                "affiliate_user_id": uid,
                "post_url": p.get("post_url"),
                "converted_to_signup": True,
            })
            out.append({
                **p,
                "clicks": clicks,
                "signups": signups,
                "conversion_pct": round((signups / clicks * 100), 2) if clicks else 0.0,
                "created_at": _iso(p.get("created_at")),
                "last_click_at": _iso(p.get("last_click_at")),
            })
        return {"items": out, "total": len(out)}

    @router.post("/affiliate/me/posts")
    async def add_post(body: PostIn, user=Depends(get_current_user)):
        uid = user["user_id"]
        aff = await db.affiliates.find_one({"user_id": uid})
        if not aff:
            raise HTTPException(403, "أنت لست مسوّقاً مفعّلاً")
        host = (urlparse(body.post_url).netloc.lower() if body.post_url else "")
        platform = body.platform or _classify_platform(body.post_url, "")
        doc = {
            "id": __import__("uuid").uuid4().hex,
            "affiliate_user_id": uid,
            "code": aff.get("code"),
            "post_url": body.post_url.strip(),
            "platform": platform,
            "host": host,
            "note": body.note,
            "created_at": _now(),
            "last_click_at": None,
            "clicks_total": 0,
        }
        await db.affiliate_posts.update_one(
            {"affiliate_user_id": uid, "post_url": doc["post_url"]},
            {"$setOnInsert": doc},
            upsert=True,
        )
        return {"ok": True}

    @router.delete("/affiliate/me/posts/{post_id}")
    async def del_post(post_id: str, user=Depends(get_current_user)):
        uid = user["user_id"]
        r = await db.affiliate_posts.delete_one({"id": post_id, "affiliate_user_id": uid})
        return {"deleted": r.deleted_count}

    # ============================================================
    # AFFILIATE: generate share links with proper UTM tagging
    # ============================================================
    @router.get("/affiliate/me/link-builder")
    async def link_builder(platform: str = "twitter", campaign: str = "default",
                            user=Depends(get_current_user)):
        uid = user["user_id"]
        aff = await db.affiliates.find_one({"user_id": uid})
        if not aff:
            raise HTTPException(403, "أنت لست مسوّقاً")
        code = aff.get("code")
        base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/") or "https://zitex.com"
        # Prefer a short tracker route
        params = f"utm_source={platform}&utm_medium=social&utm_campaign={campaign}"
        return {
            "code": code,
            "short_url": f"{base}/r/{code}?s={platform}&c={campaign}",
            "full_url": f"{base}/?aff={code}&{params}",
            "post_url_template": f"{base}/r/{code}?s={platform}&c={campaign}&post=POST_URL_HERE",
        }

    # ============================================================
    # ADMIN: list affiliates + impact analysis
    # ============================================================
    def _is_admin(u: Dict[str, Any]) -> bool:
        role = (u.get("role") or "").lower()
        return role in {"admin", "super_admin", "owner"} or bool(u.get("is_owner"))

    @router.get("/admin/affiliates/list")
    async def admin_list(q: str = "", limit: int = 50, skip: int = 0,
                          sort_by: str = "lifetime_earnings",
                          user=Depends(get_current_user)):
        if not _is_admin(user):
            raise HTTPException(403, "للأدمن فقط")
        match: Dict[str, Any] = {}
        out = []
        async for a in db.affiliates.find(match, {"_id": 0}):
            uid = a.get("user_id")
            u = await db.users.find_one({"id": uid}, {"_id": 0, "name": 1, "email": 1, "country": 1, "created_at": 1})
            if not u:
                continue
            if q and q.lower() not in (u.get("email", "") + u.get("name", "")).lower():
                continue
            code = a.get("code")
            clicks_30d = await db.affiliate_clicks.count_documents({
                "code": code, "created_at": {"$gte": _now() - timedelta(days=30)},
            })
            signups_30d = await db.affiliate_clicks.count_documents({
                "code": code, "converted_to_signup": True, "created_at": {"$gte": _now() - timedelta(days=30)},
            })
            posts_count = await db.affiliate_posts.count_documents({"affiliate_user_id": uid})
            out.append({
                "user_id": uid,
                "name": u.get("name") or u.get("email"),
                "email": u.get("email"),
                "country": u.get("country"),
                "code": code,
                "status": a.get("status"),
                "commission_pct": a.get("commission_pct"),
                "pending_balance": float(a.get("pending_balance", 0)),
                "paid_total": float(a.get("paid_total", 0)),
                "lifetime_earnings": float(a.get("lifetime_earnings", 0)),
                "lifetime_signups": a.get("lifetime_referrals_signups", 0),
                "lifetime_paid": a.get("lifetime_referrals_paid", 0),
                "clicks_30d": clicks_30d,
                "signups_30d": signups_30d,
                "posts_count": posts_count,
                "joined_at": _iso(a.get("created_at")),
            })
        key_map = {
            "lifetime_earnings": lambda r: r.get("lifetime_earnings", 0),
            "clicks_30d": lambda r: r.get("clicks_30d", 0),
            "signups_30d": lambda r: r.get("signups_30d", 0),
            "joined_at": lambda r: r.get("joined_at") or "",
        }
        out.sort(key=key_map.get(sort_by, key_map["lifetime_earnings"]), reverse=True)
        return {"total": len(out), "items": out[skip:skip + limit]}

    @router.get("/admin/affiliates/{user_id}/impact")
    async def admin_impact(user_id: str, user=Depends(get_current_user)):
        if not _is_admin(user):
            raise HTTPException(403, "للأدمن فقط")
        a = await db.affiliates.find_one({"user_id": user_id}, {"_id": 0})
        if not a:
            raise HTTPException(404, "غير موجود")
        code = a.get("code")
        now = _now()
        d30 = now - timedelta(days=30)

        # Funnel
        clicks_total = await db.affiliate_clicks.count_documents({"code": code})
        clicks_30 = await db.affiliate_clicks.count_documents({"code": code, "created_at": {"$gte": d30}})
        signups = await db.affiliate_clicks.count_documents({"code": code, "converted_to_signup": True})
        paid = await db.affiliate_clicks.count_documents({"code": code, "became_paid": True})

        # Revenue brought
        paid_clicks = db.affiliate_clicks.find({"code": code, "became_paid": True}, {"_id": 0, "total_paid_usd": 1})
        total_revenue = 0.0
        async for c in paid_clicks:
            total_revenue += float(c.get("total_paid_usd", 0) or 0)

        # Recent clicks (raw events) for forensics
        recent = []
        async for c in db.affiliate_clicks.find(
            {"code": code}, {"_id": 0},
            sort=[("created_at", -1)],
        ).limit(50):
            recent.append({
                "at": _iso(c.get("created_at")),
                "platform": c.get("platform"),
                "country": c.get("country"),
                "device": c.get("device"),
                "browser": c.get("browser"),
                "os": c.get("os"),
                "referer": c.get("referer"),
                "post_url": c.get("post_url"),
                "converted": c.get("converted_to_signup"),
                "paid": c.get("became_paid"),
                "ip": (c.get("ip") or "")[:7] + "***",  # mask last octets
            })

        # Platform mix 30d
        plats = await db.affiliate_clicks.aggregate([
            {"$match": {"code": code, "created_at": {"$gte": d30}}},
            {"$group": {"_id": "$platform", "clicks": {"$sum": 1},
                         "signups": {"$sum": {"$cond": ["$converted_to_signup", 1, 0]}}}},
            {"$sort": {"clicks": -1}},
        ]).to_list(length=30)

        # Top posts
        posts = []
        async for p in db.affiliate_posts.find({"affiliate_user_id": user_id}, {"_id": 0}):
            clicks = await db.affiliate_clicks.count_documents({"affiliate_user_id": user_id, "post_url": p["post_url"]})
            signups_p = await db.affiliate_clicks.count_documents({
                "affiliate_user_id": user_id, "post_url": p["post_url"], "converted_to_signup": True})
            posts.append({
                "post_url": p["post_url"],
                "platform": p.get("platform"),
                "clicks": clicks,
                "signups": signups_p,
                "conversion_pct": round((signups_p / clicks * 100), 2) if clicks else 0.0,
                "note": p.get("note"),
            })
        posts.sort(key=lambda x: x["clicks"], reverse=True)

        # Effectiveness verdict
        cr = (signups / clicks_total * 100) if clicks_total else 0
        if clicks_total < 20:
            verdict = "too_new"
            verdict_label = "جديد جداً — مازال يحتاج وقت للحكم"
        elif cr < 1:
            verdict = "low"
            verdict_label = "تأثير ضعيف — معظم الناس يضغطون لكن لا يسجلون"
        elif cr < 5:
            verdict = "fair"
            verdict_label = "تأثير متوسط"
        elif cr < 15:
            verdict = "good"
            verdict_label = "تأثير جيد — معدل تحويل صحي"
        else:
            verdict = "excellent"
            verdict_label = "نجم! معدل تحويل ممتاز"

        return {
            "affiliate": {
                "user_id": user_id,
                "code": code,
                "commission_pct": a.get("commission_pct"),
                "status": a.get("status"),
            },
            "funnel": {
                "clicks_total": clicks_total,
                "clicks_30d": clicks_30,
                "signups": signups,
                "paid_customers": paid,
                "total_revenue_generated_usd": round(total_revenue, 2),
                "signup_cr_pct": round(cr, 2),
            },
            "verdict": {"key": verdict, "label": verdict_label},
            "platforms": [{"platform": p["_id"] or "direct", "clicks": p["clicks"], "signups": p["signups"]} for p in plats],
            "top_posts": posts[:20],
            "recent_clicks": recent,
        }

    return router
