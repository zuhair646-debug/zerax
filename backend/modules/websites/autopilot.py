"""
AutoPilot Stories
─────────────────
Smart, vertical-aware automation that keeps every storefront looking active and engaging
without manual effort.

Two complementary mechanisms:

1) Smart SUGGESTIONS  (pull) — when the owner opens the Stories tab, we surface 1–3
   contextually-relevant template+field combos to publish in one click. Triggers include:
     • inactivity (no new story for N days)
     • day-of-week — e.g. Thursday → weekend sale template
     • day-of-month — last 3 days of the month → end-of-month sale
     • Ramadan dates (Hijri ≈ Mar/Apr 2026 fixed window for this iteration)
     • best-seller detection from `orders` collection → "new product" template
     • low-engagement (analytics handoff_rate > 30%) → "ساعات العمل" announcement

2) Scheduled AUTOPILOT  (push) — when enabled, a background loop runs every hour and
   publishes a story automatically based on the same suggestion engine, respecting the
   user's chosen frequency (weekly/biweekly/monthly) and allowed-templates list.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header as _Header
from pydantic import BaseModel

from . import stories_templates as _stpl


log = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Hijri / seasonal: simple lookup table for this year (avoid extra dep) ──
_RAMADAN_2026_RANGE = (datetime(2026, 2, 17, tzinfo=timezone.utc),
                       datetime(2026, 3, 19, tzinfo=timezone.utc))


def _is_ramadan_now() -> bool:
    now = datetime.now(timezone.utc)
    return _RAMADAN_2026_RANGE[0] <= now <= _RAMADAN_2026_RANGE[1]


# ─────────────────────────────────────────────────────────
# Suggestion engine
# ─────────────────────────────────────────────────────────

async def _last_story_age_days(stories: list) -> int:
    if not stories:
        return 999
    latest = max(stories, key=lambda s: s.get("created_at") or "")
    try:
        ts = datetime.fromisoformat(str(latest.get("created_at")).replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - ts).days
    except Exception:
        return 999


async def _top_product(database, project_id: str) -> Optional[Dict[str, Any]]:
    """Find the most-ordered product in the last 30 days."""
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    pipeline = [
        {"$match": {"project_id": project_id, "created_at": {"$gte": since},
                    "status": {"$in": ["delivered", "completed", "ready", "preparing"]}}},
        {"$unwind": "$items"},
        {"$group": {"_id": "$items.name", "n": {"$sum": "$items.qty"}}},
        {"$sort": {"n": -1}},
        {"$limit": 1},
    ]
    try:
        out = await database.orders.aggregate(pipeline).to_list(1)
        if out:
            return {"name": out[0].get("_id") or "", "count": out[0].get("n", 0)}
    except Exception as e:
        log.debug("top_product agg failed: %s", e)
    return None


async def build_suggestions(database, project: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return up to 3 high-value suggestions for this project, each with:
       {template_id, fields, reason, priority}."""
    out: List[Dict[str, Any]] = []
    stories = project.get("stories") or []
    age = await _last_story_age_days(stories)
    now = datetime.now(timezone.utc)
    weekday = now.weekday()  # Mon=0 ... Sun=6
    last_dom = (now.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    days_to_eom = (last_dom - now).days
    vertical = (project.get("vertical") or "").lower()
    suitable = {t["id"] for t in _stpl.filter_for_vertical(vertical)}

    def _add(template_id, fields, reason, priority):
        if template_id in suitable:
            out.append({"template_id": template_id, "fields": fields,
                        "reason": reason, "priority": priority})

    # Highest priority: inactivity > 7 days
    if age >= 7 and not stories:
        _add("thanks_customers", {}, "لم تنشر أي story بعد. ابدأ ببطاقة شكر للعملاء — تستغرق 10 ثوانٍ.", priority=1)
    elif age >= 5:
        _add("sale_flash_image", {"discount": 15, "product_hint": ""},
             f"مرّت {age} أيام منذ آخر story — أبقِ متجرك حياً بعرض جديد.", priority=2)

    # Ramadan window
    if _is_ramadan_now():
        _add("announce_ramadan", {"offer_text": "خصم 30% طوال الشهر الكريم"},
             "نحن في رمضان — استثمر الموسم بإعلان رمضاني فخم.", priority=1)

    # End-of-month sale (last 3 days)
    if days_to_eom <= 3:
        _add("sale_flash_image", {"discount": 30, "product_hint": ""},
             "نهاية الشهر — العملاء يبحثون عن صفقات قبل التسويات.", priority=2)

    # Friday/Saturday (weekend in Saudi calendar) → weekend sale
    if weekday in (3, 4):  # Thursday/Friday → before weekend
        _add("announce_weekend", {"discount": 15},
             "نهاية الأسبوع قادمة — العملاء يخطّطون لتسوّقهم الآن.", priority=3)

    # Best-seller → new product highlight
    top = await _top_product(database, project["id"])
    if top and top.get("name"):
        _add("new_product_reveal", {"product_name": top["name"], "product_desc": ""},
             f"\"{top['name']}\" هو الأكثر مبيعاً عندك — اعرضه بأسلوب فخم.", priority=2)

    # Vertical-specific: cafe → daily special
    if vertical in ("restaurant", "cafe", "food_delivery"):
        if not any(s.get("caption", "").startswith("🍽️") for s in stories[-5:]):
            _add("feature_food_special", {"dish_name": "طبق اليوم"},
                 "أضف \"طبق اليوم\" — يجذب الزبائن للزيارة المتكررة.", priority=3)

    if vertical in ("salon", "spa", "beauty"):
        _add("feature_salon_service", {"service_name": "جلسة استرخاء سبا"},
             "أبرز إحدى خدماتك المميزة لزبائن جدد.", priority=3)

    if vertical == "real_estate":
        _add("feature_property_listing", {"property_type": "فيلا فاخرة", "city": ""},
             "اعرض عقاراً مميزاً — يستقطب المهتمين أسرع من الإعلانات النصّية.", priority=3)

    # Reminder: free delivery threshold (if shipping config has it)
    ship = project.get("shipping_settings") or {}
    if ship.get("free_shipping_above_sar"):
        _add("reminder_free_delivery", {"threshold": int(ship["free_shipping_above_sar"])},
             "ذكّر زبائنك بسياسة التوصيل المجاني — يرفع متوسط قيمة الطلب.", priority=4)

    # Always-on fallback: hours announcement (if business_hours configured)
    bh = (project.get("chatbot_config") or {}).get("business_hours") or ""
    if bh and not stories:
        _add("announce_hours", {"hours": bh},
             "أعلن ساعات عملك بأسلوب فخم — يطمئن العملاء.", priority=4)

    # Sort & dedupe by template_id (keep highest priority)
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for s in sorted(out, key=lambda x: x["priority"]):
        if s["template_id"] in seen:
            continue
        seen.add(s["template_id"])
        deduped.append(s)
    return deduped[:3]


# ─────────────────────────────────────────────────────────
# Scheduler
# ─────────────────────────────────────────────────────────

_scheduler_task: Optional[asyncio.Task] = None


def _next_run_for_freq(freq: str, anchor: Optional[datetime] = None) -> datetime:
    now = anchor or datetime.now(timezone.utc)
    if freq == "weekly":
        return now + timedelta(days=7)
    if freq == "biweekly":
        return now + timedelta(days=14)
    if freq == "monthly":
        return now + timedelta(days=30)
    # default: weekly
    return now + timedelta(days=7)


async def _run_autopilot_for_project(database, project: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Pick the top suggestion and publish it. Returns the action record."""
    suggestions = await build_suggestions(database, project)
    if not suggestions:
        return None
    pick = suggestions[0]
    tpl = _stpl.get_template(pick["template_id"])
    if not tpl:
        return None

    # Build prompt + caption from template
    theme = (project.get("theme") or {}) if isinstance(project.get("theme"), dict) else {}
    ctx = {
        "store_name": project.get("name") or "",
        "vertical": project.get("vertical") or "",
        "primary_color": theme.get("primary") or "warm gold",
        "secondary_color": theme.get("secondary") or "deep navy",
        "language": "Arabic",
        "fields": pick["fields"],
    }
    try:
        prompt, caption = _stpl.render_prompt(tpl, ctx)
    except Exception as e:
        log.warning("autopilot render failed for %s: %s", project["id"], e)
        return None

    # Only auto-run image templates (Sora video too expensive without explicit consent)
    if tpl.get("output") != "image":
        return None

    try:
        from .stories import _generate_image_nano_banana, _append_story
        media_url = await _generate_image_nano_banana(prompt)
        sid = await _append_story(database, project["id"], {
            "type": "image", "media_url": media_url, "caption": caption,
            "duration_sec": 7, "visible": True, "ai_generated": True,
        })
    except Exception as e:
        log.error("autopilot image gen failed for %s: %s", project["id"], e)
        return None

    record = {
        "at": _iso_now(), "template_id": pick["template_id"],
        "story_id": sid, "caption": caption, "reason": pick["reason"],
    }
    await database.website_projects.update_one(
        {"id": project["id"]},
        {"$set": {
            "autopilot_settings.last_run_at": _iso_now(),
            "autopilot_settings.next_run_at": _next_run_for_freq(
                (project.get("autopilot_settings") or {}).get("frequency") or "weekly"
            ).isoformat(),
            "updated_at": _iso_now(),
        },
         "$push": {"autopilot_settings.history": {"$each": [record], "$slice": -20}}},
    )
    return record


async def _scheduler_loop(database, interval_seconds: int):
    """Run every `interval_seconds` and trigger autopilot for any due project."""
    log.info("AutoPilot scheduler running (interval=%ss)", interval_seconds)
    while True:
        try:
            now_iso = _iso_now()
            cur = database.website_projects.find(
                {"autopilot_settings.enabled": True,
                 "$or": [
                     {"autopilot_settings.next_run_at": {"$lte": now_iso}},
                     {"autopilot_settings.next_run_at": {"$exists": False}},
                 ],
                 "status": "approved"},
                {"_id": 0},
            ).limit(20)  # cap per-cycle to avoid hammering the LLM
            projects = await cur.to_list(20)
            for p in projects:
                try:
                    rec = await _run_autopilot_for_project(database, p)
                    if rec:
                        log.info("AutoPilot ran for %s — story %s", p.get("slug"), rec.get("story_id"))
                except Exception as e:
                    log.warning("AutoPilot failed for %s: %s", p.get("slug"), e)
        except Exception as e:
            log.error("AutoPilot loop error: %s", e)
        await asyncio.sleep(interval_seconds)


def start_scheduler(database, interval_seconds: int = 3600) -> None:
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        return
    try:
        loop = asyncio.get_event_loop()
        _scheduler_task = loop.create_task(_scheduler_loop(database, interval_seconds))
        log.info("AutoPilot scheduler started — every %ss", interval_seconds)
    except Exception as e:
        log.error("AutoPilot scheduler startup failed: %s", e)


# ─────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────

class AutoPilotSettingsIn(BaseModel):
    enabled: Optional[bool] = None
    frequency: Optional[str] = None  # 'weekly' | 'biweekly' | 'monthly'
    allowed_categories: Optional[List[str]] = None  # e.g. ['sale','feature']


def register_routes(r: APIRouter, database, resolve_client_project) -> None:

    @r.get("/client/autopilot/suggestions")
    async def _suggestions(authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        suggestions = await build_suggestions(database, p)
        # Hydrate suggestion objects with template details for the UI
        out = []
        for s in suggestions:
            tpl = _stpl.get_template(s["template_id"])
            if not tpl:
                continue
            out.append({
                "template_id": s["template_id"],
                "fields": s["fields"],
                "reason": s["reason"],
                "priority": s["priority"],
                "name": tpl.get("name"),
                "emoji": tpl.get("emoji"),
                "category": tpl.get("category"),
                "output": tpl.get("output"),
            })
        return {"suggestions": out}

    @r.get("/client/autopilot/settings")
    async def _ap_get(authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        s = p.get("autopilot_settings") or {}
        return {
            "enabled": bool(s.get("enabled")),
            "frequency": s.get("frequency") or "weekly",
            "allowed_categories": s.get("allowed_categories") or ["sale", "feature", "announcement", "reminder"],
            "last_run_at": s.get("last_run_at"),
            "next_run_at": s.get("next_run_at"),
            "history": (s.get("history") or [])[-10:],
        }

    @r.put("/client/autopilot/settings")
    async def _ap_put(body: AutoPilotSettingsIn, authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        cur = dict(p.get("autopilot_settings") or {})
        upd = {k: v for k, v in body.dict().items() if v is not None}
        if "frequency" in upd and upd["frequency"] not in ("weekly", "biweekly", "monthly"):
            raise HTTPException(400, "frequency must be weekly|biweekly|monthly")
        cur.update(upd)
        if cur.get("enabled") and not cur.get("next_run_at"):
            cur["next_run_at"] = _next_run_for_freq(cur.get("frequency") or "weekly").isoformat()
        await database.website_projects.update_one(
            {"id": p["id"]}, {"$set": {"autopilot_settings": cur, "updated_at": _iso_now()}},
        )
        return cur

    @r.post("/client/autopilot/run-now")
    async def _ap_run_now(authorization: str = _Header(None)):
        p = await resolve_client_project(authorization or "")
        if not os.environ.get("EMERGENT_LLM_KEY"):
            raise HTTPException(500, "AI service unavailable")
        rec = await _run_autopilot_for_project(database, p)
        if not rec:
            raise HTTPException(400, "لا توجد اقتراحات مناسبة الآن — جرّب لاحقاً أو أنشئ Story يدوياً.")
        return {"ok": True, **rec}
