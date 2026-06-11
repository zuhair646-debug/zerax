"""
AI Core — the smart intelligence layer that sits between Zenrex and upstream LLM APIs.

Purpose: Maximum protection against cost overruns + maximum quality.

5 protection layers:
    1. Usage caps per subscription tier (messages/images/videos per month)
    2. Rate limiting (requests/minute + requests/hour)
    3. Response cache (semantic dedup — identical or similar queries reuse answer)
    4. Smart model router (cheap model for simple queries, premium for complex)
    5. Cost tracking per request (real-time margin monitoring)

All Zenrex AI endpoints (avatar, chatbots, wizards) can route through `ai_core.chat()`
and get automatic protection.
"""
from __future__ import annotations
import os
import hashlib
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============== PRICING CONFIG ==============
# Upstream cost per 1K tokens (USD) — actual OpenAI/Anthropic rates (approx Q1 2026)
MODEL_COSTS_USD = {
    "cheap":    {"in": 0.00015, "out": 0.0006,  "model": "claude-haiku-4-5-20251001",   "provider": "anthropic"},
    "standard": {"in": 0.003,   "out": 0.015,   "model": "claude-sonnet-4-5-20250929",  "provider": "anthropic"},
    "premium":  {"in": 0.015,   "out": 0.075,   "model": "claude-opus-4-5-20251101",    "provider": "anthropic"},
}
USD_TO_SAR = 3.75


# ============== SUBSCRIPTION TIERS ==============
TIERS: Dict[str, Dict[str, Any]] = {
    "free":    {"label": "مجاني",     "price_sar": 0,   "chat_msgs": 50,    "images": 2,   "videos": 0,   "rate_per_min": 5,  "rate_per_hour": 30},
    "trial":   {"label": "تجربة",     "price_sar": 0,   "chat_msgs": 150,   "images": 5,   "videos": 1,   "rate_per_min": 8,  "rate_per_hour": 60},
    "basic":   {"label": "أساسي",     "price_sar": 29,  "chat_msgs": 500,   "images": 20,  "videos": 3,   "rate_per_min": 10, "rate_per_hour": 120},
    "pro":     {"label": "برو",       "price_sar": 99,  "chat_msgs": 2000,  "images": 100, "videos": 20,  "rate_per_min": 15, "rate_per_hour": 300},
    "business":{"label": "الأعمال",   "price_sar": 299, "chat_msgs": 5000,  "images": 300, "videos": 60,  "rate_per_min": 20, "rate_per_hour": 600},
}


# ============== MODEL ROUTER ==============
COMPLEX_KEYWORDS = [
    "اشرح", "حلل", "قارن", "اكتب كود", "code", "debug", "algorithm",
    "لخص", "ترجم", "أنشئ", "صمم", "خطة", "استراتيجية", "بحث",
    "legal", "regulation", "قانون", "عقد", "explain in detail",
]
SIMPLE_KEYWORDS = [
    "مرحبا", "هلا", "شلون", "كيفك", "وش تسوي", "ok", "tnx", "شكرا",
    "نعم", "لا", "باي", "مع السلامة",
]


def classify_complexity(message: str) -> str:
    """Returns 'cheap' | 'standard' | 'premium' based on message characteristics."""
    m = (message or "").strip().lower()
    length = len(m)

    # Super short → cheap
    if length < 15:
        return "cheap"

    # Has explicit complex keywords → premium
    if any(kw in m for kw in COMPLEX_KEYWORDS):
        if length > 200 or m.count("؟") + m.count("?") > 1:
            return "premium"
        return "standard"

    # Simple greeting keywords + short → cheap
    if length < 40 and any(kw in m for kw in SIMPLE_KEYWORDS):
        return "cheap"

    # Medium-length Q&A → standard
    if length < 300:
        return "standard"

    # Long detailed question → premium
    return "premium"


# ============== CACHE KEY ==============
def _normalize_for_cache(text: str) -> str:
    """Lowercase, strip punctuation/extra spaces — so similar questions hit same cache."""
    t = (text or "").lower().strip()
    t = re.sub(r"[^\w\s\u0600-\u06FF]+", " ", t)  # keep alphanum + Arabic letters
    t = re.sub(r"\s+", " ", t).strip()
    return t


def cache_key_for(system_hash: str, user_msg: str) -> str:
    norm = _normalize_for_cache(user_msg)
    raw = f"{system_hash}::{norm}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


# ============== MODELS ==============
class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    system_prompt: Optional[str] = "You are a helpful assistant."
    force_tier: Optional[str] = None  # 'cheap' | 'standard' | 'premium' | None (auto)
    use_cache: bool = True
    context_tag: Optional[str] = "general"  # for analytics grouping


class UsageResponse(BaseModel):
    tier: str
    period_start: str
    chat_used: int
    chat_limit: int
    images_used: int
    images_limit: int
    videos_used: int
    videos_limit: int
    cost_usd: float
    cost_sar: float
    revenue_sar: float
    margin_sar: float
    margin_pct: float
    healthy: bool


class SetTierIn(BaseModel):
    user_id: str
    tier: str


# ============== HELPERS ==============
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _period_start() -> datetime:
    n = _now()
    return n.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _hash_system(system: str) -> str:
    return hashlib.md5((system or "").encode("utf-8")).hexdigest()[:10]


def _estimate_tokens(text: str) -> int:
    """Rough estimate: 1 token ≈ 4 chars English / 2 chars Arabic."""
    if not text:
        return 0
    # Arabic chars are typically 2-3 chars per token
    arabic = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    other = len(text) - arabic
    return max(1, int(arabic / 2 + other / 4))


# ============== AI CORE ROUTER ==============
def create_ai_core_router(db, get_current_user, get_current_user_optional=None) -> APIRouter:
    router = APIRouter(prefix="/api/ai-core", tags=["ai-core"])

    async def _get_user_tier(user_id: str) -> str:
        u = await db.users.find_one({"id": user_id}, {"_id": 0, "ai_tier": 1, "is_owner": 1, "role": 1})
        if not u:
            return "free"
        if u.get("is_owner") or u.get("role") in ("owner", "super_admin", "admin"):
            return "business"  # admins unlimited-ish
        return u.get("ai_tier") or "free"

    async def _get_usage_this_month(user_id: str) -> Dict[str, Any]:
        """Aggregate usage from ai_core_logs for current period."""
        period = _period_start()
        pipeline = [
            {"$match": {"user_id": user_id, "created_at": {"$gte": period.isoformat()}}},
            {"$group": {
                "_id": "$context_tag",
                "count": {"$sum": 1},
                "cost_usd": {"$sum": "$cost_usd"},
            }},
        ]
        rows = await db.ai_core_logs.aggregate(pipeline).to_list(length=50)
        by_tag: Dict[str, Dict[str, Any]] = {r["_id"]: {"count": r["count"], "cost_usd": r["cost_usd"]} for r in rows}
        total_cost = sum(r.get("cost_usd") or 0 for r in rows)

        # Count chat across all tags
        chat_count = sum(v["count"] for k, v in by_tag.items() if k not in ("image", "video"))
        images = (by_tag.get("image") or {}).get("count", 0)
        videos = (by_tag.get("video") or {}).get("count", 0)

        return {
            "chat_count": chat_count,
            "images": images,
            "videos": videos,
            "cost_usd": total_cost,
            "cost_sar": total_cost * USD_TO_SAR,
            "by_tag": by_tag,
        }

    async def _check_rate_limit(user_id: str, tier_cfg: Dict[str, Any]) -> Tuple[bool, str]:
        now = _now()
        one_min_ago = now - timedelta(minutes=1)
        one_hour_ago = now - timedelta(hours=1)

        minute_count = await db.ai_core_logs.count_documents({
            "user_id": user_id,
            "created_at": {"$gte": one_min_ago.isoformat()},
        })
        if minute_count >= tier_cfg["rate_per_min"]:
            return False, f"⏱️ تجاوزت الحد ({tier_cfg['rate_per_min']} طلب/دقيقة). خذ نفس وحاول بعد دقيقة."

        hour_count = await db.ai_core_logs.count_documents({
            "user_id": user_id,
            "created_at": {"$gte": one_hour_ago.isoformat()},
        })
        if hour_count >= tier_cfg["rate_per_hour"]:
            return False, f"⏱️ تجاوزت الحد ({tier_cfg['rate_per_hour']} طلب/ساعة). حاول بعد قليل."

        return True, ""

    async def _check_usage_cap(user_id: str, tier_cfg: Dict[str, Any], context_tag: str) -> Tuple[bool, str]:
        usage = await _get_usage_this_month(user_id)
        if context_tag == "image":
            if usage["images"] >= tier_cfg["images"]:
                return False, f"🚫 وصلت الحد الأقصى ({tier_cfg['images']} صورة/شهر). رقّي اشتراكك أو استخدم نقاط."
        elif context_tag == "video":
            if usage["videos"] >= tier_cfg["videos"]:
                return False, f"🚫 وصلت الحد الأقصى ({tier_cfg['videos']} فيديو/شهر). رقّي اشتراكك."
        else:
            if usage["chat_count"] >= tier_cfg["chat_msgs"]:
                return False, f"🚫 وصلت الحد الأقصى ({tier_cfg['chat_msgs']} رسالة/شهر). رقّي اشتراكك أو استخدم نقاط."
        return True, ""

    # ===== TIERS CATALOG =====
    @router.get("/tiers")
    async def tiers_catalog():
        return {"tiers": {k: {**v, "id": k} for k, v in TIERS.items()}}

    # ===== MY USAGE =====
    @router.get("/usage/me", response_model=UsageResponse)
    async def my_usage(user=Depends(get_current_user)):
        tier = await _get_user_tier(user["user_id"])
        tier_cfg = TIERS[tier]
        usage = await _get_usage_this_month(user["user_id"])

        revenue_sar = float(tier_cfg["price_sar"])
        cost_sar = usage["cost_sar"]
        margin_sar = revenue_sar - cost_sar
        margin_pct = (margin_sar / revenue_sar * 100) if revenue_sar > 0 else 100.0

        return UsageResponse(
            tier=tier,
            period_start=_period_start().isoformat(),
            chat_used=usage["chat_count"],
            chat_limit=tier_cfg["chat_msgs"],
            images_used=usage["images"],
            images_limit=tier_cfg["images"],
            videos_used=usage["videos"],
            videos_limit=tier_cfg["videos"],
            cost_usd=round(usage["cost_usd"], 6),
            cost_sar=round(cost_sar, 4),
            revenue_sar=revenue_sar,
            margin_sar=round(margin_sar, 2),
            margin_pct=round(margin_pct, 1),
            healthy=margin_pct > 30.0,
        )

    # ===== SMART CHAT (main endpoint) =====
    @router.post("/chat")
    async def smart_chat(payload: ChatIn, user=Depends(get_current_user)):
        user_id = user["user_id"]
        tier = await _get_user_tier(user_id)
        tier_cfg = TIERS[tier]
        ctx_tag = payload.context_tag or "general"

        # 1. Rate limit
        ok, reason = await _check_rate_limit(user_id, tier_cfg)
        if not ok:
            raise HTTPException(429, reason)

        # 2. Usage cap
        ok, reason = await _check_usage_cap(user_id, tier_cfg, ctx_tag)
        if not ok:
            raise HTTPException(402, reason)

        # 3. Cache check
        system_hash = _hash_system(payload.system_prompt or "")
        ckey = cache_key_for(system_hash, payload.message)
        cached = None
        if payload.use_cache:
            cached_doc = await db.ai_core_cache.find_one({"key": ckey}, {"_id": 0})
            if cached_doc:
                # TTL: 7 days
                try:
                    created = datetime.fromisoformat(cached_doc["created_at"].replace("Z", "+00:00"))
                    if (_now() - created) < timedelta(days=7):
                        cached = cached_doc["reply"]
                        # Increment hit counter
                        await db.ai_core_cache.update_one(
                            {"key": ckey},
                            {"$inc": {"hits": 1}, "$set": {"last_hit_at": _now().isoformat()}}
                        )
                except Exception:
                    pass

        if cached:
            # Log as a cache hit (zero cost)
            await db.ai_core_logs.insert_one({
                "user_id": user_id,
                "tier": tier,
                "context_tag": ctx_tag,
                "message_length": len(payload.message),
                "model_tier": "cache",
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "cached": True,
                "created_at": _now().isoformat(),
            })
            return {
                "reply": cached,
                "model_tier": "cache",
                "cached": True,
                "cost_usd": 0.0,
                "cost_sar": 0.0,
            }

        # 4. Model routing
        model_tier = payload.force_tier or classify_complexity(payload.message)
        if model_tier not in MODEL_COSTS_USD:
            model_tier = "standard"
        model_cfg = MODEL_COSTS_USD[model_tier]

        # 5. Call LLM
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            emergent_key = os.environ.get("EMERGENT_LLM_KEY")
            if not emergent_key:
                raise HTTPException(503, "AI service not configured")
            chat = LlmChat(
                api_key=emergent_key,
                session_id=payload.session_id or f"aicore-{user_id[:8]}",
                system_message=payload.system_prompt or "You are a helpful assistant.",
            )
            chat.with_model(model_cfg["provider"], model_cfg["model"])
            reply = await chat.send_message(UserMessage(text=payload.message))
        except Exception as e:
            logger.exception(f"[AI-CORE] LLM call failed: {e}")
            raise HTTPException(500, "فشل توليد الرد. حاول مرة ثانية.")

        # 6. Cost tracking
        tokens_in = _estimate_tokens(payload.message + (payload.system_prompt or ""))
        tokens_out = _estimate_tokens(reply)
        cost_usd = (tokens_in / 1000.0) * model_cfg["in"] + (tokens_out / 1000.0) * model_cfg["out"]

        # 7. Write cache
        if payload.use_cache:
            try:
                await db.ai_core_cache.update_one(
                    {"key": ckey},
                    {"$set": {
                        "key": ckey,
                        "reply": reply,
                        "model_tier": model_tier,
                        "system_hash": system_hash,
                        "sample_question": payload.message[:200],
                        "created_at": _now().isoformat(),
                    }, "$setOnInsert": {"hits": 0}},
                    upsert=True,
                )
            except Exception as e:
                logger.warning(f"[AI-CORE] cache write failed: {e}")

        # 8. Log
        await db.ai_core_logs.insert_one({
            "user_id": user_id,
            "tier": tier,
            "context_tag": ctx_tag,
            "message_length": len(payload.message),
            "model_tier": model_tier,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd,
            "cached": False,
            "created_at": _now().isoformat(),
        })

        return {
            "reply": reply,
            "model_tier": model_tier,
            "cached": False,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(cost_usd, 6),
            "cost_sar": round(cost_usd * USD_TO_SAR, 4),
        }

    # ===== ADMIN: platform-wide stats =====
    @router.get("/admin/stats")
    async def admin_stats(days: int = 30, user=Depends(get_current_user)):
        if not (user.get("is_owner") or user.get("role") in ("owner", "super_admin", "admin")):
            raise HTTPException(403, "owner only")

        since = _now() - timedelta(days=days)
        # Total requests & cost
        pipeline = [
            {"$match": {"created_at": {"$gte": since.isoformat()}}},
            {"$group": {
                "_id": "$model_tier",
                "count": {"$sum": 1},
                "cost_usd": {"$sum": "$cost_usd"},
                "tokens_in": {"$sum": "$tokens_in"},
                "tokens_out": {"$sum": "$tokens_out"},
            }},
        ]
        rows = await db.ai_core_logs.aggregate(pipeline).to_list(length=10)
        by_tier = {r["_id"]: {
            "count": r["count"],
            "cost_usd": round(r["cost_usd"], 4),
            "cost_sar": round(r["cost_usd"] * USD_TO_SAR, 2),
            "tokens_in": r["tokens_in"],
            "tokens_out": r["tokens_out"],
        } for r in rows}

        total_requests = sum(v["count"] for v in by_tier.values())
        total_cost_usd = sum(v["cost_usd"] for v in by_tier.values())
        cached_count = by_tier.get("cache", {}).get("count", 0)
        paid_count = total_requests - cached_count
        savings_pct = (cached_count / total_requests * 100) if total_requests > 0 else 0.0

        # Top consumers
        top_pipeline = [
            {"$match": {"created_at": {"$gte": since.isoformat()}, "cached": {"$ne": True}}},
            {"$group": {
                "_id": "$user_id",
                "count": {"$sum": 1},
                "cost_usd": {"$sum": "$cost_usd"},
            }},
            {"$sort": {"cost_usd": -1}},
            {"$limit": 20},
        ]
        top_rows = await db.ai_core_logs.aggregate(top_pipeline).to_list(length=20)
        # Enrich with user info
        top_users = []
        for r in top_rows:
            u = await db.users.find_one({"id": r["_id"]}, {"_id": 0, "email": 1, "name": 1, "ai_tier": 1})
            tier_id = (u or {}).get("ai_tier") or "free"
            tier_revenue = TIERS.get(tier_id, TIERS["free"])["price_sar"]
            cost_sar = r["cost_usd"] * USD_TO_SAR
            margin = tier_revenue - cost_sar
            top_users.append({
                "user_id": r["_id"],
                "email": (u or {}).get("email", "unknown"),
                "name": (u or {}).get("name", ""),
                "tier": tier_id,
                "requests": r["count"],
                "cost_usd": round(r["cost_usd"], 4),
                "cost_sar": round(cost_sar, 2),
                "tier_revenue_sar": tier_revenue,
                "margin_sar": round(margin, 2),
                "is_losing": margin < 0,
            })

        return {
            "period_days": days,
            "total_requests": total_requests,
            "paid_requests": paid_count,
            "cached_requests": cached_count,
            "cache_savings_pct": round(savings_pct, 1),
            "total_cost_usd": round(total_cost_usd, 4),
            "total_cost_sar": round(total_cost_usd * USD_TO_SAR, 2),
            "by_tier": by_tier,
            "top_consumers": top_users,
        }

    # ===== ADMIN: cache stats =====
    @router.get("/admin/cache/stats")
    async def cache_stats(user=Depends(get_current_user)):
        if not (user.get("is_owner") or user.get("role") in ("owner", "super_admin", "admin")):
            raise HTTPException(403, "owner only")
        total = await db.ai_core_cache.count_documents({})
        total_hits = 0
        rows = await db.ai_core_cache.find({}, {"_id": 0, "hits": 1}).to_list(length=10000)
        total_hits = sum(r.get("hits", 0) for r in rows)
        # Top cached Q
        top = await db.ai_core_cache.find({}, {"_id": 0, "sample_question": 1, "hits": 1, "model_tier": 1}).sort("hits", -1).limit(10).to_list(length=10)
        return {
            "total_cached_entries": total,
            "total_cache_hits": total_hits,
            "top_cached_questions": top,
        }

    # ===== OWNER: set user tier =====
    @router.post("/admin/set-tier")
    async def set_tier(payload: SetTierIn, user=Depends(get_current_user)):
        if not (user.get("is_owner") or user.get("role") in ("owner", "super_admin", "admin")):
            raise HTTPException(403, "owner only")
        if payload.tier not in TIERS:
            raise HTTPException(400, f"Invalid tier. Must be one of: {list(TIERS.keys())}")
        result = await db.users.update_one(
            {"id": payload.user_id},
            {"$set": {"ai_tier": payload.tier, "ai_tier_updated_at": _now().isoformat()}}
        )
        if result.matched_count == 0:
            raise HTTPException(404, "user not found")
        return {"ok": True, "user_id": payload.user_id, "tier": payload.tier}

    return router
