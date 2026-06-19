"""
Auto-Resume Reminders — friendly nudges that pull users back to projects they
started but never finished. Works across ALL project types (websites, apps,
games, films, video studio).

Cadence: 24h → 72h → 168h (7 days). After 3 attempts we stop pinging.
Idempotent: one tracker doc per (user_id, project_id) in
`db.resume_reminders` so we never double-send.

Email transport: Resend (re-uses RESEND_API_KEY + FROM_EMAIL/FROM_NAME from
the existing pricing/invoice flow).

Channel: email today; phone/WhatsApp can be added later via the same scheduler
without changing the scan logic.

Mounted from server.py via `register_resume_reminders(db, app, get_current_user)`.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException

log = logging.getLogger("zenrex.resume_reminder")

# How often the scheduler scans.
SCAN_INTERVAL_SECONDS = 60 * 60  # hourly

# Reminder cadence (hours since updated_at; index = reminder number).
REMINDER_AT_HOURS = [24, 72, 168]
MAX_REMINDERS = len(REMINDER_AT_HOURS)

# Project sources — (collection_name, mode_label, build_resume_url_fn)
def _freebuild_url(p: Dict[str, Any]) -> str:
    if p.get("mode") == "app":
        return f"https://zenrex.ai/freebuild/chat/{p['id']}"
    return f"https://zenrex.ai/freebuild/chat/{p['id']}"

def _game_url(p: Dict[str, Any]) -> str:
    return f"https://zenrex.ai/games/chat/{p.get('id') or p.get('_id')}"

def _video_url(p: Dict[str, Any]) -> str:
    return f"https://zenrex.ai/studio/video/{p.get('id') or p.get('_id')}"

SOURCES = [
    {
        "collection": "freebuild_projects",
        "label_fn": lambda p: {
            "app": "تطبيق جوال",
            "image_studio": "مشروع صور",
            "video_studio": "مشروع فيديو",
            "anime_studio": "مشروع أنمي",
            "longform_video": "فيديو طويل",
        }.get(p.get("mode"), "موقع"),
        "emoji_fn": lambda p: {
            "app": "📱",
            "image_studio": "🎨",
            "video_studio": "🎬",
            "anime_studio": "🌸",
            "longform_video": "🎥",
        }.get(p.get("mode"), "🌐"),
        "url_fn": _freebuild_url,
        "completion_fields": ["deployed_url", "exported_at"],
        "started_check": lambda p: bool(p.get("current_html")) or len(p.get("messages") or []) > 2,
    },
    {
        "collection": "game_projects",
        "label_fn": lambda p: "لعبة",
        "emoji_fn": lambda p: "🎮",
        "url_fn": _game_url,
        "completion_fields": ["published_at", "exported_at"],
        "started_check": lambda p: bool(p.get("scenes")) or bool(p.get("characters")) or len(p.get("messages") or []) > 1,
    },
    {
        "collection": "video_series",
        "label_fn": lambda p: "سلسلة فيديو",
        "emoji_fn": lambda p: "📺",
        "url_fn": _video_url,
        "completion_fields": ["finalized_at"],
        "started_check": lambda p: bool(p.get("episodes")) or bool(p.get("title")),
    },
]


def _hours_since(dt_value: Any) -> Optional[float]:
    """Return hours elapsed since `dt_value` (handles str ISO + datetime)."""
    if not dt_value:
        return None
    try:
        if isinstance(dt_value, datetime):
            dt = dt_value
        else:
            dt = datetime.fromisoformat(str(dt_value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        return delta.total_seconds() / 3600
    except Exception:
        return None


def _next_reminder_index(hours_idle: float, sent_count: int) -> Optional[int]:
    """Decide which reminder slot to fire (0-based), if any."""
    if sent_count >= MAX_REMINDERS:
        return None
    expected = sent_count  # next one to send
    threshold = REMINDER_AT_HOURS[expected]
    return expected if hours_idle >= threshold else None


def _build_email_html(*, user_name: str, project_name: str, emoji: str, label: str,
                       resume_url: str, hours_idle: float, reminder_no: int) -> str:
    tone_by_no = {
        1: "مشروعك بانتظارك! يكفي ٥ دقائق تخلصه.",
        2: "ما زلت تذكر مشروعك؟ كل خطوة تقربك من النشر.",
        3: "آخر تذكير منّا — مشروعك يستحق يشوف النور.",
    }
    headline = tone_by_no.get(reminder_no, "أكمل مشروعك")
    days = max(1, int(hours_idle / 24))
    return f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:#0a0a0a;font-family:-apple-system,Segoe UI,Tahoma,sans-serif">
  <table align="center" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:32px auto;background:#111;border-radius:16px;padding:32px;border:1px solid rgba(212,175,55,0.25)">
    <tr><td style="text-align:center;padding-bottom:16px">
      <img src="https://zenrex.ai/zenrex-logo.png" alt="Zenrex" width="56" height="56" style="object-fit:contain">
      <div style="background:linear-gradient(90deg,#FFD86B,#D4AF37);-webkit-background-clip:text;background-clip:text;color:transparent;font-weight:900;font-size:18px;margin-top:8px">زنركس AI</div>
    </td></tr>
    <tr><td>
      <h1 style="color:#FFD86B;font-size:22px;margin:0 0 8px;text-align:center">{emoji} {headline}</h1>
      <p style="color:#ddd;font-size:14px;line-height:1.7;text-align:center;margin:0 0 24px">
        أهلاً {user_name}،<br>
        {label} اللي بدأت اشتغل عليه باسم <b style="color:#FFD86B">"{project_name}"</b>
        من <b>{days}</b> {"يوم" if days == 1 else "أيام"} وما اكتمل بعد.
      </p>
      <table align="center" cellpadding="0" cellspacing="0" style="margin:0 auto 24px">
        <tr><td style="background:linear-gradient(135deg,#FFD86B,#D4AF37);border-radius:12px">
          <a href="{resume_url}" style="display:inline-block;padding:14px 36px;color:#000;font-weight:900;text-decoration:none;font-size:15px">
            👈 أكمل المشروع الآن
          </a>
        </td></tr>
      </table>
      <div style="background:rgba(212,175,55,0.08);border-right:3px solid #FFD86B;padding:14px 18px;border-radius:8px;margin-bottom:24px">
        <p style="color:#fff;font-size:13px;margin:0;line-height:1.6">
          💡 <b>نصيحة:</b> الذكاء يحفظ كل خطوة. تقدر ترجع لنفس النقطة بالضبط — بدون فقدان أي شيء.
        </p>
      </div>
      <p style="color:#666;font-size:11px;text-align:center;margin:0">
        ما تبي تستلم هذا النوع من التذكيرات؟
        <a href="https://zenrex.ai/account/notifications" style="color:#FFD86B">عطّلها من هنا</a>.
      </p>
    </td></tr>
    <tr><td style="text-align:center;padding-top:24px;border-top:1px solid #222;margin-top:24px">
      <p style="color:#555;font-size:10px;margin:12px 0 0">© Zenrex · zenrex.ai · منصة الإبداع بالذكاء الاصطناعي</p>
    </td></tr>
  </table>
</body></html>
"""


async def _send_email(to_email: str, subject: str, html: str) -> bool:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        log.warning("[RESUME-REMINDER] RESEND_API_KEY missing — skipping send")
        return False
    from_email = os.environ.get("FROM_EMAIL", "onboarding@resend.dev")
    from_name = os.environ.get("FROM_NAME", "Zenrex")
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "from": f"{from_name} <{from_email}>",
                    "to": [to_email],
                    "subject": subject,
                    "html": html,
                },
            )
            if r.status_code >= 400:
                log.warning(f"[RESUME-REMINDER] Resend {r.status_code}: {r.text[:200]}")
                return False
            return True
    except Exception as e:
        log.error(f"[RESUME-REMINDER] send error: {e}")
        return False


async def _process_project(db, source: Dict[str, Any], project: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
    """Decide if a reminder is due for a single project; send + record. Returns trace dict."""
    pid = project.get("id") or str(project.get("_id"))
    uid = project.get("user_id")
    if not uid or not pid:
        return {"skipped": "missing_user_or_id"}

    # Skip completed/deployed/deleted
    if any(project.get(f) for f in source["completion_fields"]):
        return {"skipped": "completed"}
    if project.get("status") in ("deployed", "completed", "deleted", "archived"):
        return {"skipped": "status_terminal"}
    if not source["started_check"](project):
        return {"skipped": "not_really_started"}

    hours_idle = _hours_since(project.get("updated_at") or project.get("created_at"))
    if hours_idle is None or hours_idle < REMINDER_AT_HOURS[0]:
        return {"skipped": f"too_fresh_{hours_idle}"}

    # Look up tracker
    tracker_key = {"user_id": uid, "project_id": pid, "collection": source["collection"]}
    tracker = await db.resume_reminders.find_one(tracker_key) or {}
    sent_count = int(tracker.get("sent_count", 0))

    next_idx = _next_reminder_index(hours_idle, sent_count)
    if next_idx is None and not force:
        return {"skipped": f"already_max_or_not_due_sent={sent_count}_hours={hours_idle:.1f}"}
    if force and next_idx is None:
        next_idx = min(sent_count, MAX_REMINDERS - 1)

    # User lookup
    user = await db.users.find_one({"id": uid}, {"email": 1, "name": 1, "reminder_opt_out": 1})
    if not user or not user.get("email"):
        return {"skipped": "user_or_email_missing"}
    if user.get("reminder_opt_out"):
        return {"skipped": "user_opted_out"}

    label = source["label_fn"](project)
    emoji = source["emoji_fn"](project)
    resume_url = source["url_fn"](project)
    name = project.get("name") or "بدون اسم"
    html = _build_email_html(
        user_name=user.get("name") or "صديقي",
        project_name=name, emoji=emoji, label=label,
        resume_url=resume_url, hours_idle=hours_idle,
        reminder_no=next_idx + 1,
    )
    subject = f"{emoji} {name} — ما زلت تذكره؟"
    sent = await _send_email(user["email"], subject, html)
    now = datetime.now(timezone.utc).isoformat()
    if sent:
        await db.resume_reminders.update_one(
            tracker_key,
            {
                "$set": {
                    "user_id": uid, "project_id": pid, "collection": source["collection"],
                    "last_reminder_at": now,
                    "last_reminder_index": next_idx,
                },
                "$inc": {"sent_count": 1},
                "$push": {"history": {"at": now, "index": next_idx, "hours_idle": round(hours_idle, 1)}},
            },
            upsert=True,
        )
    return {"sent": sent, "to": user["email"], "project": name, "index": next_idx, "hours_idle": round(hours_idle, 1)}


async def run_one_pass(db, force: bool = False) -> Dict[str, Any]:
    """Single scan across all configured sources. Returns a summary."""
    summary = {"scanned": 0, "sent": 0, "skipped": 0, "errors": 0, "by_source": {}}
    for source in SOURCES:
        coll = source["collection"]
        try:
            cur = db[coll].find(
                {"status": {"$nin": ["deleted", "archived"]}},
                {"id": 1, "_id": 1, "user_id": 1, "name": 1, "mode": 1, "updated_at": 1,
                 "created_at": 1, "current_html": 1, "messages": 1, "deployed_url": 1,
                 "exported_at": 1, "status": 1, "scenes": 1, "characters": 1, "episodes": 1,
                 "title": 1, "published_at": 1, "finalized_at": 1},
            ).limit(2000)
            items = await cur.to_list(length=2000)
        except Exception as e:
            log.warning(f"[RESUME-REMINDER] could not read {coll}: {e}")
            summary["errors"] += 1
            continue
        per = {"scanned": len(items), "sent": 0, "skipped": 0}
        for p in items:
            summary["scanned"] += 1
            try:
                trace = await _process_project(db, source, p, force=force)
                if trace.get("sent"):
                    per["sent"] += 1
                    summary["sent"] += 1
                else:
                    per["skipped"] += 1
                    summary["skipped"] += 1
            except Exception as e:
                summary["errors"] += 1
                log.exception(f"[RESUME-REMINDER] process_project failed: {e}")
        summary["by_source"][coll] = per
    log.info(f"[RESUME-REMINDER] pass complete: {summary}")
    return summary


async def _scheduler_loop(db):
    log.info(f"[RESUME-REMINDER] scheduler running (every {SCAN_INTERVAL_SECONDS}s)")
    # Slight startup delay so we don't compete with other init tasks.
    await asyncio.sleep(120)
    while True:
        try:
            await run_one_pass(db, force=False)
        except Exception as e:
            log.exception(f"[RESUME-REMINDER] loop error: {e}")
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


def register_resume_reminders(db, app, get_current_user):
    """Mount admin + user endpoints, then schedule the background loop."""
    router = APIRouter(prefix="/api/resume-reminders", tags=["resume-reminders"])

    @router.get("/me")
    async def my_settings(user=Depends(get_current_user)):
        u = await db.users.find_one({"id": user["user_id"]}, {"reminder_opt_out": 1})
        return {"opt_out": bool((u or {}).get("reminder_opt_out", False))}

    @router.post("/me/opt-out")
    async def opt_out(payload: dict, user=Depends(get_current_user)):
        opt = bool(payload.get("opt_out", True))
        await db.users.update_one({"id": user["user_id"]}, {"$set": {"reminder_opt_out": opt}})
        return {"ok": True, "opt_out": opt}

    @router.get("/me/history")
    async def my_history(user=Depends(get_current_user)):
        cur = db.resume_reminders.find(
            {"user_id": user["user_id"]},
            {"_id": 0, "project_id": 1, "collection": 1, "sent_count": 1,
             "last_reminder_at": 1, "last_reminder_index": 1},
        ).limit(100)
        return {"items": await cur.to_list(length=100)}

    @router.post("/admin/run-now")
    async def admin_run_now(payload: dict = None, user=Depends(get_current_user)):
        if user.get("role") not in ("owner", "super_admin", "admin"):
            raise HTTPException(403, "admin only")
        force = bool((payload or {}).get("force", False))
        return await run_one_pass(db, force=force)

    app.include_router(router)

    @app.on_event("startup")
    async def _start():
        asyncio.create_task(_scheduler_loop(db))
