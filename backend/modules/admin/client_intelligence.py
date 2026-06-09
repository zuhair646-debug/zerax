"""
Client Intelligence Center — Admin-only deep view into every client's
activity. Strictly READ-ONLY: admins cannot impersonate, send messages,
or modify any client data. They see a full 360° report.

Endpoints (all under `/api/admin/intelligence`):

  GET  /clients                      — paginated list with summary stats
  GET  /clients/{user_id}/360        — full profile (everything)
  GET  /clients/{user_id}/conversations  — chats from all modules
  GET  /clients/{user_id}/projects   — websites/apps/games
  GET  /clients/{user_id}/media      — images + videos
  GET  /clients/{user_id}/payments   — orders + transactions
  GET  /clients/{user_id}/sessions   — visits + activity timeline
  POST /clients/{user_id}/ai-insights — Claude-generated audience analysis

All endpoints require role in {admin, super_admin, owner}.
"""
from __future__ import annotations
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

logger = logging.getLogger("zitex.admin.intelligence")

router = APIRouter(prefix="/admin/intelligence", tags=["admin", "intelligence"])


class InsightsReq(BaseModel):
    depth: str = "standard"  # standard | deep


# -----------------------------------------------------------------------
# Authorization helper
# -----------------------------------------------------------------------
def _is_admin(user: Dict[str, Any]) -> bool:
    if not user:
        return False
    role = (user.get("role") or "").lower()
    return role in {"admin", "super_admin", "owner"} or bool(user.get("is_owner"))


def _admin_only(user: Dict[str, Any]):
    if not _is_admin(user):
        raise HTTPException(403, "هذه الصفحة للأدمن فقط")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d: Any) -> Optional[str]:
    if not d:
        return None
    if isinstance(d, datetime):
        return d.isoformat()
    return str(d)


# -----------------------------------------------------------------------
# Public router builder — called from server.py with `db` and `get_current_user`
# -----------------------------------------------------------------------
def build_router(db, get_current_user):

    @router.get("/clients")
    async def list_clients(
        q: str = Query("", description="Search by email or name"),
        limit: int = Query(50, ge=1, le=200),
        skip: int = Query(0, ge=0),
        sort_by: str = Query("last_active", regex="^(last_active|total_spent|created_at|name)$"),
        user=Depends(get_current_user),
    ):
        _admin_only(user)
        # Build base filter
        match: Dict[str, Any] = {}
        if q:
            q = q.strip()
            match["$or"] = [
                {"email": {"$regex": q, "$options": "i"}},
                {"name": {"$regex": q, "$options": "i"}},
            ]
        # Get users
        cursor = db.users.find(match, {
            "_id": 0, "id": 1, "email": 1, "name": 1, "role": 1,
            "created_at": 1, "country": 1, "credits": 1, "last_login": 1, "plan": 1,
        }).limit(500)  # cap base set; sort happens after enrichment
        users = await cursor.to_list(length=500)

        # Enrich each user with summary stats in parallel
        out = []
        for u in users:
            uid = u.get("id")
            if not uid:
                continue
            # Spend total
            agg = await db.payment_orders.aggregate([
                {"$match": {"user_id": uid, "status": "completed"}},
                {"$group": {"_id": None,
                            "total_usd": {"$sum": "$amount"},
                            "count": {"$sum": 1}}},
            ]).to_list(length=1)
            total_spent = float(agg[0]["total_usd"]) if agg else 0.0
            order_count = int(agg[0]["count"]) if agg else 0

            # Last activity (most recent across activity_logs)
            last_act = await db.activity_logs.find_one(
                {"user_id": uid},
                {"_id": 0, "created_at": 1, "action": 1},
                sort=[("created_at", -1)],
            )

            # Counts of artifacts created
            projects_count = await db.freebuild_projects.count_documents({"user_id": uid})
            games_count = await db.game_projects.count_documents({"user_id": uid})
            images_count = await db.image_generations.count_documents({"user_id": uid})
            videos_count = await db.video_generations.count_documents({"user_id": uid})
            chats_count = await db.chat_sessions.count_documents({"user_id": uid})

            out.append({
                "id": uid,
                "email": u.get("email"),
                "name": u.get("name") or u.get("email"),
                "role": u.get("role"),
                "country": u.get("country"),
                "credits": u.get("credits", 0),
                "plan": u.get("plan", "free"),
                "created_at": _iso(u.get("created_at")),
                "last_login": _iso(u.get("last_login")),
                "last_active": _iso(last_act.get("created_at") if last_act else None) or _iso(u.get("last_login")) or _iso(u.get("created_at")),
                "last_action": last_act.get("action") if last_act else None,
                "total_spent_usd": round(total_spent, 2),
                "order_count": order_count,
                "counts": {
                    "websites": projects_count,
                    "games": games_count,
                    "images": images_count,
                    "videos": videos_count,
                    "chats": chats_count,
                },
            })

        # Sort
        key_map = {
            "last_active": lambda r: r.get("last_active") or "",
            "total_spent": lambda r: r.get("total_spent_usd") or 0,
            "created_at": lambda r: r.get("created_at") or "",
            "name": lambda r: (r.get("name") or "").lower(),
        }
        out.sort(key=key_map[sort_by], reverse=(sort_by != "name"))
        total = len(out)
        sliced = out[skip:skip + limit]
        return {"total": total, "items": sliced, "limit": limit, "skip": skip}

    # -------------------------------------------------------------------
    @router.get("/clients/{user_id}/360")
    async def client_360(user_id: str, user=Depends(get_current_user)):
        _admin_only(user)
        u = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if not u:
            raise HTTPException(404, "العميل غير موجود")

        # Spend
        agg = await db.payment_orders.aggregate([
            {"$match": {"user_id": user_id, "status": "completed"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        ]).to_list(length=1)
        total_spent = float(agg[0]["total"]) if agg else 0.0
        orders_completed = int(agg[0]["count"]) if agg else 0

        # Activity heatmap (last 30 days)
        thirty_ago = _now() - timedelta(days=30)
        recent_acts = await db.activity_logs.find(
            {"user_id": user_id, "created_at": {"$gte": thirty_ago}},
            {"_id": 0, "action": 1, "created_at": 1, "ip_address": 1},
            sort=[("created_at", -1)],
        ).limit(200).to_list(length=200)
        heat: Dict[str, int] = {}
        ips: set = set()
        for a in recent_acts:
            d = a.get("created_at")
            if isinstance(d, datetime):
                k = d.date().isoformat()
                heat[k] = heat.get(k, 0) + 1
            if a.get("ip_address"):
                ips.add(a["ip_address"])

        # Counts
        counts = {
            "websites": await db.freebuild_projects.count_documents({"user_id": user_id}),
            "games": await db.game_projects.count_documents({"user_id": user_id}),
            "images": await db.image_generations.count_documents({"user_id": user_id})
                       + await db.user_images.count_documents({"user_id": user_id}),
            "videos": await db.video_generations.count_documents({"user_id": user_id})
                       + await db.video_requests.count_documents({"user_id": user_id}),
            "chats": await db.chat_sessions.count_documents({"user_id": user_id}),
            "freebuild_sessions": await db.freebuild_sessions.count_documents({"user_id": user_id})
                                   + await db.freebuild_v2_sessions.count_documents({"user_id": user_id}),
        }

        # Engagement score (0-100)
        engagement = min(100, int(
            counts["websites"] * 8 +
            counts["games"] * 10 +
            counts["images"] * 2 +
            counts["videos"] * 4 +
            counts["chats"] * 3 +
            min(total_spent, 200) * 0.2
        ))

        u.pop("password", None)
        return {
            "user": {
                "id": u.get("id"),
                "email": u.get("email"),
                "name": u.get("name"),
                "role": u.get("role"),
                "country": u.get("country"),
                "credits": u.get("credits", 0),
                "plan": u.get("plan", "free"),
                "created_at": _iso(u.get("created_at")),
                "last_login": _iso(u.get("last_login")),
            },
            "spend": {
                "total_usd": round(total_spent, 2),
                "orders_completed": orders_completed,
            },
            "activity": {
                "total_actions_30d": len(recent_acts),
                "heatmap": heat,
                "unique_ips": len(ips),
                "recent_actions": [{
                    "action": a.get("action"),
                    "at": _iso(a.get("created_at")),
                    "ip": a.get("ip_address"),
                } for a in recent_acts[:20]],
            },
            "counts": counts,
            "engagement_score": engagement,
        }

    # -------------------------------------------------------------------
    @router.get("/clients/{user_id}/conversations")
    async def client_conversations(user_id: str, limit: int = 50, user=Depends(get_current_user)):
        _admin_only(user)
        # Pull from multiple chat collections
        out = []
        # freebuild_projects.messages
        async for p in db.freebuild_projects.find(
            {"user_id": user_id},
            {"_id": 0, "id": 1, "name": 1, "messages": 1, "created_at": 1, "updated_at": 1},
            sort=[("updated_at", -1)],
        ).limit(limit):
            msgs = p.get("messages") or []
            out.append({
                "source": "freebuild",
                "session_id": p.get("id"),
                "title": p.get("name"),
                "message_count": len(msgs),
                "messages": [{
                    "role": m.get("role"),
                    "content": (m.get("content") or "")[:1200],  # cap
                    "at": _iso(m.get("timestamp") or m.get("created_at")),
                } for m in msgs[-30:]],
                "created_at": _iso(p.get("created_at")),
                "updated_at": _iso(p.get("updated_at")),
            })
        # chat_sessions
        async for s in db.chat_sessions.find(
            {"user_id": user_id},
            {"_id": 0},
            sort=[("updated_at", -1)],
        ).limit(limit):
            msgs = s.get("messages") or []
            out.append({
                "source": "chat",
                "session_id": s.get("id"),
                "title": s.get("title") or s.get("session_type"),
                "message_count": len(msgs),
                "messages": [{
                    "role": m.get("role"),
                    "content": (m.get("content") or "")[:1200],
                    "at": _iso(m.get("timestamp") or m.get("created_at")),
                } for m in msgs[-30:]],
                "created_at": _iso(s.get("created_at")),
                "updated_at": _iso(s.get("updated_at")),
            })
        # game_projects (description + brief, no chat usually)
        async for g in db.game_projects.find(
            {"user_id": user_id},
            {"_id": 0, "id": 1, "title": 1, "description": 1, "game_type": 1, "created_at": 1},
            sort=[("created_at", -1)],
        ).limit(20):
            out.append({
                "source": "game",
                "session_id": g.get("id"),
                "title": g.get("title"),
                "message_count": 1,
                "messages": [{"role": "user", "content": g.get("description") or "", "at": _iso(g.get("created_at"))}],
                "created_at": _iso(g.get("created_at")),
                "updated_at": _iso(g.get("created_at")),
            })
        # sort by updated_at desc
        out.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
        return {"items": out[:limit], "total": len(out)}

    # -------------------------------------------------------------------
    @router.get("/clients/{user_id}/projects")
    async def client_projects(user_id: str, user=Depends(get_current_user)):
        _admin_only(user)
        # Websites (freebuild)
        websites = []
        async for p in db.freebuild_projects.find(
            {"user_id": user_id},
            {"_id": 0, "id": 1, "name": 1, "slug": 1, "current_html": 1, "html": 1,
             "credits_spent": 1, "version": 1, "created_at": 1, "updated_at": 1, "type_id": 1},
            sort=[("updated_at", -1)],
        ).limit(60):
            html = p.get("current_html") or p.get("html") or ""
            websites.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "slug": p.get("slug"),
                "type": p.get("type_id"),
                "has_html": bool(html),
                "html_length": len(html) if html else 0,
                "credits_spent": p.get("credits_spent", 0),
                "version": p.get("version", 1),
                "created_at": _iso(p.get("created_at")),
                "updated_at": _iso(p.get("updated_at")),
            })
        # Games
        games = []
        async for g in db.game_projects.find(
            {"user_id": user_id},
            {"_id": 0, "id": 1, "title": 1, "game_type": 1, "programming_type": 1,
             "current_phase": 1, "preview_url": 1, "created_at": 1, "updated_at": 1},
            sort=[("created_at", -1)],
        ).limit(60):
            games.append({
                "id": g.get("id"),
                "title": g.get("title"),
                "game_type": g.get("game_type"),
                "framework": g.get("programming_type"),
                "phase": g.get("current_phase"),
                "preview_url": g.get("preview_url"),
                "created_at": _iso(g.get("created_at")),
                "updated_at": _iso(g.get("updated_at")),
            })
        # Apps (conversion / native)
        apps = []
        async for a in db.app_projects.find(
            {"user_id": user_id}, {"_id": 0},
            sort=[("created_at", -1)],
        ).limit(40):
            apps.append({
                "id": a.get("id"),
                "name": a.get("name") or a.get("title"),
                "status": a.get("status"),
                "created_at": _iso(a.get("created_at")),
            })
        async for a in db.app_conversion_projects.find(
            {"user_id": user_id}, {"_id": 0},
            sort=[("created_at", -1)],
        ).limit(40):
            apps.append({
                "id": a.get("id"),
                "name": a.get("name") or a.get("title") or "Conversion",
                "type": "conversion",
                "status": a.get("status"),
                "created_at": _iso(a.get("created_at")),
            })
        return {"websites": websites, "games": games, "apps": apps,
                "total": len(websites) + len(games) + len(apps)}

    # -------------------------------------------------------------------
    @router.get("/clients/{user_id}/media")
    async def client_media(user_id: str, user=Depends(get_current_user)):
        _admin_only(user)
        images = []
        async for i in db.image_generations.find(
            {"user_id": user_id}, {"_id": 0},
            sort=[("created_at", -1)],
        ).limit(60):
            images.append({
                "id": i.get("id"),
                "url": i.get("image_url"),
                "prompt": i.get("prompt"),
                "status": i.get("status"),
                "created_at": _iso(i.get("created_at")),
            })
        async for i in db.user_images.find(
            {"user_id": user_id}, {"_id": 0},
            sort=[("created_at", -1)],
        ).limit(40):
            images.append({
                "id": i.get("id"),
                "url": i.get("url"),
                "prompt": i.get("prompt"),
                "source": "user_images",
                "created_at": _iso(i.get("created_at")),
            })
        videos = []
        async for v in db.video_generations.find(
            {"user_id": user_id}, {"_id": 0},
            sort=[("created_at", -1)],
        ).limit(60):
            videos.append({
                "id": v.get("id"),
                "url": v.get("video_url"),
                "prompt": v.get("prompt"),
                "status": v.get("status"),
                "created_at": _iso(v.get("created_at")),
            })
        return {"images": images, "videos": videos,
                "total_images": len(images), "total_videos": len(videos)}

    # -------------------------------------------------------------------
    @router.get("/clients/{user_id}/payments")
    async def client_payments(user_id: str, user=Depends(get_current_user)):
        _admin_only(user)
        orders = []
        async for o in db.payment_orders.find(
            {"user_id": user_id}, {"_id": 0},
            sort=[("created_at", -1)],
        ).limit(100):
            orders.append({
                "id": o.get("id"),
                "package": o.get("package_id"),
                "type": o.get("package_type"),
                "amount": o.get("amount"),
                "currency": o.get("currency"),
                "status": o.get("status"),
                "method": o.get("payment_method"),
                "credits_added": o.get("credits_added"),
                "created_at": _iso(o.get("created_at")),
                "completed_at": _iso(o.get("completed_at")),
            })
        tx = []
        async for t in db.credit_transactions.find(
            {"user_id": user_id}, {"_id": 0},
            sort=[("created_at", -1)],
        ).limit(100):
            tx.append({
                "id": t.get("id"),
                "delta": t.get("amount") or t.get("delta"),
                "reason": t.get("reason") or t.get("description"),
                "at": _iso(t.get("created_at")),
            })
        return {"orders": orders, "credit_history": tx,
                "total_orders": len(orders), "total_completed": sum(1 for o in orders if o["status"] == "completed")}

    # -------------------------------------------------------------------
    @router.get("/clients/{user_id}/sessions")
    async def client_sessions(user_id: str, user=Depends(get_current_user)):
        _admin_only(user)
        acts = []
        async for a in db.activity_logs.find(
            {"user_id": user_id}, {"_id": 0},
            sort=[("created_at", -1)],
        ).limit(120):
            acts.append({
                "id": a.get("id"),
                "action": a.get("action"),
                "type": a.get("action_type"),
                "details": a.get("details"),
                "ip": a.get("ip_address"),
                "at": _iso(a.get("created_at")),
            })
        # Aggregate IPs and unique days
        ips = set(a["ip"] for a in acts if a.get("ip"))
        days = set((a["at"] or "")[:10] for a in acts if a.get("at"))
        return {
            "events": acts,
            "total": len(acts),
            "unique_ips": len(ips),
            "active_days_recent": len([d for d in days if d]),
        }

    # -------------------------------------------------------------------
    @router.post("/clients/{user_id}/ai-insights")
    async def client_ai_insights(user_id: str, user=Depends(get_current_user)):
        _admin_only(user)
        u = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if not u:
            raise HTTPException(404, "العميل غير موجود")

        # Gather recent context the AI will analyse
        chats: List[str] = []
        async for p in db.freebuild_projects.find(
            {"user_id": user_id}, {"_id": 0, "messages": 1, "name": 1},
        ).limit(15):
            name = p.get("name") or "مشروع"
            for m in (p.get("messages") or [])[-10:]:
                role = m.get("role")
                content = (m.get("content") or "")[:400]
                if content:
                    chats.append(f"[{name} | {role}]: {content}")
        async for s in db.chat_sessions.find(
            {"user_id": user_id}, {"_id": 0, "messages": 1, "title": 1},
        ).limit(10):
            t = s.get("title") or "chat"
            for m in (s.get("messages") or [])[-8:]:
                content = (m.get("content") or "")[:400]
                if content:
                    chats.append(f"[{t} | {m.get('role')}]: {content}")

        # Game / image / video prompts
        prompts: List[str] = []
        async for g in db.game_projects.find({"user_id": user_id}, {"_id": 0, "description": 1, "game_type": 1}).limit(10):
            d = g.get("description")
            if d:
                prompts.append(f"[game/{g.get('game_type')}]: {d[:300]}")
        async for i in db.image_generations.find({"user_id": user_id}, {"_id": 0, "prompt": 1}).limit(20):
            p = i.get("prompt")
            if p:
                prompts.append(f"[image]: {p[:200]}")
        async for v in db.video_generations.find({"user_id": user_id}, {"_id": 0, "prompt": 1}).limit(15):
            p = v.get("prompt")
            if p:
                prompts.append(f"[video]: {p[:200]}")

        # Spend
        agg = await db.payment_orders.aggregate([
            {"$match": {"user_id": user_id, "status": "completed"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        ]).to_list(length=1)
        total_spent = float(agg[0]["total"]) if agg else 0.0
        order_count = int(agg[0]["count"]) if agg else 0

        # Compose context
        ctx_lines = [
            f"العميل: {u.get('name') or u.get('email')}",
            f"البريد: {u.get('email')}",
            f"الدولة: {u.get('country') or 'غير محددة'}",
            f"الباقة: {u.get('plan', 'free')}",
            f"المبلغ المنفق: ${total_spent:.2f} ({order_count} طلب)",
            f"الرصيد الحالي: {u.get('credits', 0)} شعلة",
            "",
            "آخر 50 رسالة/طلب من العميل (تمثّل سلوكه وأسلوبه):",
            *chats[-50:],
            "",
            "آخر prompts (تكشف الذوق والاهتمامات):",
            *prompts[-40:],
        ]
        context_blob = "\n".join(ctx_lines)[:18000]  # cap tokens

        prompt = (
            "أنت محلل سلوك عملاء محترف لمنصة Zerax (مواقع، تطبيقات، ألعاب، صور وفيديوهات بالذكاء الاصطناعي).\n"
            "ستحلل سلوك عميل واحد من السياق التالي وتعطي تقرير محترف بصيغة JSON صارمة فقط:\n\n"
            "```json\n"
            "{\n"
            '  "profile_summary": "فقرة موجزة 2-3 جمل عن شخصية العميل وأسلوبه",\n'
            '  "top_interests": ["اهتمام1", "اهتمام2", ...],\n'
            '  "industry_guess": "القطاع الأرجح",\n'
            '  "tone_style": "أسلوب الكتابة (رسمي/ودي/تقني/إلخ)",\n'
            '  "buying_intent": "low|medium|high",\n'
            '  "lifecycle_stage": "explorer|active_builder|loyal|churning|whale",\n'
            '  "satisfaction_signal": "negative|neutral|positive",\n'
            '  "suggested_campaigns": [\n'
            '    {"title": "اسم الحملة", "channel": "email|whatsapp|in_app|ads", "message": "صياغة الإعلان المقترحة", "offer": "العرض الموصى به"}\n'
            '  ],\n'
            '  "upsell_ideas": ["فكرة1", "فكرة2"],\n'
            '  "risk_flags": ["إن وُجد"],\n'
            '  "next_best_action": "الإجراء التالي الفوري الذي يُحدث أكبر أثر"\n'
            "}\n"
            "```\n\n"
            "اكتب كل النصوص بالعربية فقط. لا تضف شرحاً خارج JSON.\n\n"
            f"=== سياق العميل ===\n{context_blob}\n=== انتهى ==="
        )

        # Call Claude
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
            r = await client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        except Exception as e:
            logger.exception("ai-insights claude failed")
            raise HTTPException(503, f"تعذّر استدعاء الذكاء: {type(e).__name__}")

        # Extract JSON
        import json as _json
        import re as _re
        m = _re.search(r"```json\s*(\{.*?\})\s*```", raw, _re.S)
        blob = m.group(1) if m else raw
        m2 = _re.search(r"\{.*\}", blob, _re.S)
        if m2:
            blob = m2.group(0)
        try:
            data = _json.loads(blob)
        except Exception:
            data = {"raw": raw[:4000], "_parse_error": True}

        # Persist for caching / audit
        await db.client_intelligence_reports.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "report": data,
                "generated_at": _now(),
                "generated_by": user.get("user_id"),
            }},
            upsert=True,
        )

        return {"report": data, "generated_at": _iso(_now())}

    return router
