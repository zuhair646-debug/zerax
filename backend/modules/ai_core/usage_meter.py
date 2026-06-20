"""
AI Usage Meter — Tokens In/Out, Cost, Daily Quota, and Admin Visibility.

Every Zenrex AI call (across all sections) should go through `record_usage()`
so we know exactly how much each user/project consumed. Free tier gets a
daily token cap; over the cap the AI politely asks for an upgrade.

Public surface:
  - record_usage(db, user_id, project_id, section, tokens_in, tokens_out,
                 model_label="zenrex-ai")
  - get_user_daily_usage(db, user_id) → {tokens, cost_usd, calls}
  - check_quota(db, user_id, user_doc) → {allowed, reason, used, cap}

Admin router:
  - GET /api/usage/me                      → personal usage (today + lifetime)
  - GET /api/admin/usage/top-spenders      → top N users by tokens this month
  - GET /api/admin/usage/by-project        → top N projects by tokens this month

Pricing assumptions (Emergent LLM key, Claude Sonnet 4.5):
  input  ~$3.00 / 1M tokens
  output ~$15.00 / 1M tokens

Free-tier caps (override per user with `users.daily_token_cap`):
  daily_token_cap          = 50_000  (~$0.15 worst case)
  daily_request_cap        = 100
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

log = logging.getLogger("zenrex.usage_meter")

# ─── Pricing ──────────────────────────────────────────────────────────────
COST_INPUT_PER_1M = 3.0    # USD per 1M input tokens
COST_OUTPUT_PER_1M = 15.0  # USD per 1M output tokens

# ─── Credits system (1 credit ≈ $0.005 actual cost = ~500 AI tokens) ──
# We bill the user at 200 credits per dollar of actual cost (≥ 2× margin).
CREDITS_PER_USD = 200
FREE_SIGNUP_CREDITS = 200  # given to brand-new users on registration


def _credits_for_cost(cost_usd: float) -> int:
    """Convert a real-USD cost into the credits to deduct from user balance."""
    import math
    return max(1, int(math.ceil((cost_usd or 0) * CREDITS_PER_USD)))


# ─── Free-tier caps ──────────────────────────────────────────────────────
# Free tier = ONE WOW demo only. Just enough tokens to build a single
# initial design that hooks the customer (≈ 4-5 messages), then we hit
# the cap and convert them to a paid plan.
DEFAULT_FREE_DAILY_TOKENS = 120_000   # ≈ $0.38 real cost — one polished demo
DEFAULT_FREE_DAILY_REQUESTS = 12

# Higher caps for paid tiers (calibrated for healthy margins).
#   Starter $29 → 600K tokens (~ $1.90 cost) → margin ≈ $27
#   Pro     $99 → 3M  tokens (~ $9.50 cost) → margin ≈ $89
#   Studio  $299 → 18M tokens (~ $57 cost) → margin ≈ $242
TIER_DAILY_TOKENS = {
    "free":    120_000,
    "starter": 600_000,
    "pro":     3_000_000,
    "studio":  18_000_000,
}


def _today_key(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d")


def _estimate_cost(tokens_in: int, tokens_out: int) -> float:
    return round(
        (tokens_in * COST_INPUT_PER_1M + tokens_out * COST_OUTPUT_PER_1M) / 1_000_000,
        6,
    )


async def record_usage(
    db,
    user_id: str,
    project_id: Optional[str],
    section: str,
    tokens_in: int,
    tokens_out: int,
    model_label: str = "zenrex-ai",
) -> Dict[str, Any]:
    """Log a usage event + deduct credits via the central pricing catalog.

    Uses `modules.pricing.credits.charge_user("text_claude_1k", multiplier)`
    so every section deducts using the same source of truth (SERVICE_COSTS).
    """
    try:
        cost = _estimate_cost(tokens_in or 0, tokens_out or 0)
        total_tokens = int((tokens_in or 0) + (tokens_out or 0))
        # Multiplier = total_tokens / 1000 (catalog charges per 1K tokens)
        multiplier = max(0.001, total_tokens / 1000.0)
        now = datetime.now(timezone.utc)
        # Log raw event
        await db.usage_events.insert_one({
            "user_id": user_id,
            "project_id": project_id,
            "section": section,
            "tokens_in": int(tokens_in or 0),
            "tokens_out": int(tokens_out or 0),
            "cost_usd": cost,
            "model_label": model_label,
            "ts": now.isoformat(),
            "ymd": _today_key(now),
        })
        # Aggregate per day
        await db.usage_daily.update_one(
            {"user_id": user_id, "ymd": _today_key(now)},
            {
                "$inc": {
                    "tokens_in": int(tokens_in or 0),
                    "tokens_out": int(tokens_out or 0),
                    "calls": 1,
                    "cost_usd": cost,
                },
                "$setOnInsert": {"user_id": user_id, "ymd": _today_key(now)},
            },
            upsert=True,
        )
        # Deduct credits via the central pricing catalog. Owners are exempt.
        credits_used = 0
        try:
            from modules.pricing.credits import charge_user
            await charge_user(
                db, user_id, "text_claude_1k",
                multiplier=multiplier,
                meta={"section": section, "project_id": project_id, "tokens": total_tokens},
            )
            # Estimate the actual amount charged: catalog credits × multiplier
            from modules.pricing.catalog import SERVICE_COSTS
            svc = SERVICE_COSTS.get("text_claude_1k") or {}
            credits_used = int(float(svc.get("credits", 0)) * multiplier)
        except ValueError:
            # User out of credits — surface error to caller
            return {"ok": False, "error": "no_credits", "cost_usd": cost}
        except Exception as _ce:
            log.warning(f"[USAGE-METER] credits charge failed: {_ce}")
        return {"ok": True, "cost_usd": cost, "credits_used": credits_used}
    except Exception as e:
        log.warning(f"[USAGE-METER] record_usage failed: {e}")
        return {"ok": False, "error": str(e)}


async def get_user_daily_usage(db, user_id: str) -> Dict[str, Any]:
    doc = await db.usage_daily.find_one(
        {"user_id": user_id, "ymd": _today_key()},
        {"_id": 0},
    )
    return doc or {"tokens_in": 0, "tokens_out": 0, "calls": 0, "cost_usd": 0.0}


async def check_quota(db, user_id: str, user_doc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Decide if this user can make another AI call right now.

    Credits-based: if `users.credits` > 0 → allow. Otherwise block
    and prompt upgrade. Admin/owner bypass.
    """
    if user_doc is None:
        user_doc = await db.users.find_one(
            {"id": user_id},
            {"credits": 1, "storage_tier": 1, "role": 1},
        ) or {}

    # Owner / super_admin never throttled.
    if (user_doc.get("role") or "").lower() in ("owner", "super_admin"):
        return {"allowed": True, "reason": "admin", "credits": None}

    balance = int(user_doc.get("credits") or 0)
    tier = (user_doc.get("storage_tier") or "free").lower()

    if balance <= 0:
        return {
            "allowed": False,
            "reason": "no_credits",
            "credits": 0,
            "next_tier_label": "Starter" if tier == "free" else "Pro",
            "message": (
                "رصيد النقاط انتهى. اشحن باقة جديدة لمواصلة الإنشاء — "
                "كل النقاط متاحة فوراً بعد الدفع."
            ),
        }
    return {"allowed": True, "reason": "ok", "credits": balance}


# ─── Router ───────────────────────────────────────────────────────────────
def make_usage_router(db, get_current_user):
    router = APIRouter(prefix="/api/usage", tags=["usage-meter"])

    @router.get("/me")
    async def my_usage(user=Depends(get_current_user)):
        uid = user["user_id"]
        today = await get_user_daily_usage(db, uid)
        # 30-day rollup
        since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        cur = db.usage_events.find({"user_id": uid, "ts": {"$gte": since}},
                                   {"_id": 0, "tokens_in": 1, "tokens_out": 1, "cost_usd": 1, "credits_used": 1})
        items = await cur.to_list(length=10000)
        month_tokens = sum((it.get("tokens_in", 0) + it.get("tokens_out", 0)) for it in items)
        month_cost = round(sum(it.get("cost_usd", 0) for it in items), 4)
        month_credits = sum(it.get("credits_used", 0) for it in items)
        # Quota status + credits balance
        user_doc = await db.users.find_one(
            {"id": uid}, {"storage_tier": 1, "credits": 1, "role": 1},
        )
        q = await check_quota(db, uid, user_doc)
        return {
            "today": today,
            "month_tokens": month_tokens,
            "month_cost_usd": month_cost,
            "month_credits": month_credits,
            "credits": int((user_doc or {}).get("credits") or 0),
            "tier": (user_doc or {}).get("storage_tier") or "free",
            "quota": q,
        }

    @router.get("/credits")
    async def my_credits(user=Depends(get_current_user)):
        """Lightweight endpoint for the navbar credits badge — quick to poll."""
        uid = user["user_id"]
        u = await db.users.find_one({"id": uid}, {"_id": 0, "credits": 1, "role": 1, "storage_tier": 1})
        role = (u or {}).get("role") or ""
        if role.lower() in ("owner", "super_admin"):
            return {"credits": None, "unlimited": True, "tier": (u or {}).get("storage_tier") or "free"}
        return {
            "credits": int((u or {}).get("credits") or 0),
            "unlimited": False,
            "tier": (u or {}).get("storage_tier") or "free",
        }

    @router.get("/me/per-project")
    async def my_per_project(user=Depends(get_current_user)):
        uid = user["user_id"]
        since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        pipeline = [
            {"$match": {"user_id": uid, "ts": {"$gte": since}}},
            {"$group": {
                "_id": "$project_id",
                "tokens_in": {"$sum": "$tokens_in"},
                "tokens_out": {"$sum": "$tokens_out"},
                "cost_usd": {"$sum": "$cost_usd"},
                "calls": {"$sum": 1},
            }},
            {"$sort": {"cost_usd": -1}},
            {"$limit": 50},
        ]
        results = await db.usage_events.aggregate(pipeline).to_list(length=50)
        return {"items": [{"project_id": r["_id"], **{k: r[k] for k in ("tokens_in", "tokens_out", "cost_usd", "calls")}} for r in results]}

    # ─── Admin endpoints ──────────────────────────────────────────────
    def _ensure_admin(user):
        role = (user.get("role") or "").lower()
        if role not in ("owner", "super_admin", "admin"):
            raise HTTPException(403, "Admin only")

    @router.get("/admin/top-spenders")
    async def top_spenders(limit: int = 20, user=Depends(get_current_user)):
        _ensure_admin(user)
        since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        pipeline = [
            {"$match": {"ts": {"$gte": since}}},
            {"$group": {
                "_id": "$user_id",
                "tokens_in": {"$sum": "$tokens_in"},
                "tokens_out": {"$sum": "$tokens_out"},
                "cost_usd": {"$sum": "$cost_usd"},
                "calls": {"$sum": 1},
            }},
            {"$sort": {"cost_usd": -1}},
            {"$limit": int(limit)},
        ]
        results = await db.usage_events.aggregate(pipeline).to_list(length=int(limit))
        # Enrich with email/name
        out = []
        for r in results:
            u = await db.users.find_one({"id": r["_id"]}, {"email": 1, "name": 1, "storage_tier": 1, "_id": 0})
            out.append({
                "user_id": r["_id"],
                "email": (u or {}).get("email", "?"),
                "name": (u or {}).get("name", ""),
                "tier": (u or {}).get("storage_tier", "free"),
                "tokens_in": r["tokens_in"],
                "tokens_out": r["tokens_out"],
                "tokens_total": r["tokens_in"] + r["tokens_out"],
                "cost_usd": round(r["cost_usd"], 4),
                "calls": r["calls"],
            })
        return {"items": out, "since_days": 30}

    @router.get("/admin/by-project")
    async def by_project(limit: int = 20, user=Depends(get_current_user)):
        _ensure_admin(user)
        since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        pipeline = [
            {"$match": {"ts": {"$gte": since}, "project_id": {"$ne": None}}},
            {"$group": {
                "_id": {"project_id": "$project_id", "user_id": "$user_id", "section": "$section"},
                "tokens_in": {"$sum": "$tokens_in"},
                "tokens_out": {"$sum": "$tokens_out"},
                "cost_usd": {"$sum": "$cost_usd"},
                "calls": {"$sum": 1},
            }},
            {"$sort": {"cost_usd": -1}},
            {"$limit": int(limit)},
        ]
        results = await db.usage_events.aggregate(pipeline).to_list(length=int(limit))
        out = []
        for r in results:
            proj = await db.freebuild_projects.find_one({"id": r["_id"]["project_id"]}, {"name": 1, "mode": 1, "_id": 0})
            u = await db.users.find_one({"id": r["_id"]["user_id"]}, {"email": 1, "_id": 0})
            out.append({
                "project_id": r["_id"]["project_id"],
                "project_name": (proj or {}).get("name", "?"),
                "section": r["_id"]["section"],
                "user_email": (u or {}).get("email", "?"),
                "tokens_total": r["tokens_in"] + r["tokens_out"],
                "cost_usd": round(r["cost_usd"], 4),
                "calls": r["calls"],
            })
        return {"items": out}

    @router.get("/admin/totals")
    async def totals(user=Depends(get_current_user)):
        _ensure_admin(user)
        now = datetime.now(timezone.utc)
        since_24h = (now - timedelta(hours=24)).isoformat()
        since_30d = (now - timedelta(days=30)).isoformat()
        async def _sum(since):
            pipeline = [
                {"$match": {"ts": {"$gte": since}}},
                {"$group": {"_id": None, "tokens": {"$sum": {"$add": ["$tokens_in", "$tokens_out"]}},
                            "cost": {"$sum": "$cost_usd"}, "calls": {"$sum": 1}}}
            ]
            r = await db.usage_events.aggregate(pipeline).to_list(length=1)
            return r[0] if r else {"tokens": 0, "cost": 0.0, "calls": 0}
        d24 = await _sum(since_24h)
        d30 = await _sum(since_30d)
        return {
            "last_24h": {"tokens": d24.get("tokens", 0), "cost_usd": round(d24.get("cost", 0), 4), "calls": d24.get("calls", 0)},
            "last_30d": {"tokens": d30.get("tokens", 0), "cost_usd": round(d30.get("cost", 0), 4), "calls": d30.get("calls", 0)},
        }

    return router
