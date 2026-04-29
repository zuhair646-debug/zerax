"""
Health-check + scheduled maintenance + alerts for all clients.

Tasks:
  - run_all_health_checks() — ping each client's Railway deployment, store status
  - alert_on_failure() — generate WhatsApp deep-link if owner phone configured
  - schedule_loop() — background asyncio task that runs health checks every N hours
"""
import asyncio
import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import vault
from . import actions as ops


log = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


_HEALTHY = {"SUCCESS", "DEPLOYED", "RUNNING", "BUILDING"}
_FAILING = {"FAILED", "CRASHED", "REMOVED", "STOPPED"}


def _classify(status: str) -> str:
    s = (status or "").upper()
    if s in _HEALTHY:
        return "healthy"
    if s in _FAILING:
        return "failing"
    if s in {"INITIALIZING", "QUEUED", "WAITING"}:
        return "pending"
    return "unknown"


async def health_check_one(client_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Return a dict describing health for a single client."""
    rw = client_doc.get("railway") or {}
    out: Dict[str, Any] = {
        "client_id": client_doc.get("id"),
        "client_name": client_doc.get("name"),
        "checked_at": _iso_now(),
        "railway": {"configured": False, "state": "n/a"},
        "vercel": {"configured": bool((client_doc.get("vercel") or {}).get("token_enc"))},
        "github": {"configured": bool((client_doc.get("github") or {}).get("token_enc"))},
    }
    if rw.get("token_enc") and rw.get("service_id") and rw.get("environment_id"):
        out["railway"]["configured"] = True
        try:
            dep = await ops.railway_latest_deploy(
                vault.decrypt(rw["token_enc"]), rw["service_id"], rw["environment_id"]
            )
            status = dep.get("status") or ""
            out["railway"].update({
                "status": status,
                "state": _classify(status),
                "url": dep.get("staticUrl") or dep.get("url") or "",
                "deployment_id": dep.get("id"),
                "created_at": dep.get("createdAt"),
            })
        except Exception as e:
            out["railway"].update({"state": "error", "error": str(e)[:200]})
    return out


def whatsapp_link(phone: str, message: str) -> str:
    """Build a wa.me deep-link the owner can click to alert customer/themselves."""
    if not phone:
        return ""
    p = "".join(ch for ch in phone if ch.isdigit())
    return f"https://wa.me/{p}?text={urllib.parse.quote(message)}"


async def run_all_health_checks(database) -> Dict[str, Any]:
    """Loop over all operator_clients, store result, broadcast over WS, generate alerts."""
    clients = await database.operator_clients.find({}, {"_id": 0}).to_list(500)
    settings = await database.operator_settings.find_one({"_id": "global"}, {"_id": 0}) or {}
    alert_phone = (settings.get("alert_phone") or "").strip()

    results: List[Dict[str, Any]] = []
    alerts: List[Dict[str, Any]] = []

    for c in clients:
        h = await health_check_one(c)
        results.append(h)
        # Persist last health on the client
        await database.operator_clients.update_one(
            {"id": c["id"]},
            {"$set": {"last_health": h, "last_health_at": _iso_now()}},
        )
        # Save snapshot for history (keep last 200 per client)
        await database.operator_health_history.update_one(
            {"client_id": c["id"]},
            {"$push": {"snapshots": {"$each": [h], "$slice": -200}}},
            upsert=True,
        )
        # Trigger alert if state is failing and a previous snapshot was healthy
        rw = h.get("railway") or {}
        if rw.get("state") == "failing":
            msg = f"⚠️ خلل: مشروع {c.get('name')} على Railway في حالة {rw.get('status')}"
            wa = whatsapp_link(alert_phone, msg) if alert_phone else ""
            alert_doc = {
                "client_id": c["id"],
                "kind": "deployment_failed",
                "title": msg,
                "whatsapp_link": wa,
                "at": _iso_now(),
                "seen": False,
            }
            await database.operator_alerts.insert_one(alert_doc)
            alerts.append(alert_doc)

            # 🆕 AI Auto-Fix Mode
            if c.get("auto_fix_enabled"):
                try:
                    from .agent import AgentRunner
                    import uuid as _uuid
                    runner = AgentRunner(database, c, f"autofix-{_uuid.uuid4()}", "auto-fix-bot")
                    fix_prompt = (
                        "تشغيل تلقائي: اكتشفت خاصية الفحص الدوري أن آخر deployment على Railway فاشل "
                        f"(status={rw.get('status')}). افحص السبب الجذري عبر سحب سجلات Railway "
                        "وقراءة الملفات ذات الصلة (مثل railway.toml, Procfile, requirements.txt). "
                        "إن وجدت إصلاحاً واضحاً، طبّقه عبر write_file ثم railway_redeploy. "
                        "احفظ الدرس في الذاكرة عبر remember. أنهِ بـ done مع رسالة تلخّص ما حدث."
                    )
                    result = await runner.run(fix_prompt)
                    final_msg = (result or {}).get("final", "(لا رد)")
                    summary = f"🤖 إصلاح تلقائي لـ {c.get('name')}: {final_msg[:200]}"
                    wa2 = whatsapp_link(alert_phone, summary) if alert_phone else ""
                    await database.operator_alerts.insert_one({
                        "client_id": c["id"],
                        "kind": "auto_fix_attempted",
                        "title": summary,
                        "whatsapp_link": wa2,
                        "at": _iso_now(),
                        "seen": False,
                    })
                except Exception as e:
                    log.error("auto-fix failed for %s: %s", c.get("name"), e)

    # Realtime broadcast (fire-and-forget, ignore failures)
    try:
        from server import realtime_broadcast_global  # type: ignore
        await realtime_broadcast_global("operator_health", {"results": results, "at": _iso_now()})
    except Exception:
        pass

    return {"checked": len(results), "alerts": len(alerts), "results": results}


_loop_task: Optional[asyncio.Task] = None


async def _scheduler_loop(database, interval_seconds: int):
    while True:
        try:
            await run_all_health_checks(database)
        except Exception as e:
            log.error("health-check loop error: %s", e)
        await asyncio.sleep(interval_seconds)


def start_scheduler(database, interval_seconds: int = 6 * 3600):
    """Start the background scheduler (idempotent)."""
    global _loop_task
    if _loop_task and not _loop_task.done():
        return
    try:
        loop = asyncio.get_event_loop()
        _loop_task = loop.create_task(_scheduler_loop(database, interval_seconds))
        log.info("operator scheduler started — every %ss", interval_seconds)
    except Exception as e:
        log.error("failed to start scheduler: %s", e)
