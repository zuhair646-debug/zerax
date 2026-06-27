"""
🚨 Escalation Bridge — automatic alerts to the human operator/employee when
the AI repeatedly fails despite all autonomous mitigations (Silent Supervisor +
Honesty Wrapper).

Owner directive (Arabic, Saudi): the AI must try its 90+ tools first. If it
gives up OR loops more than N times in a single conversation, send the
operator an email + create an in-app admin notification with full context
(project_id, last N messages, supervisor intervention log). The customer
shouldn't have to ask for help — the system notices and escalates.

Trigger thresholds (deliberately conservative — escalation is rare and
costs operator attention):
  • supervisor_interventions ≥ 3 in a single turn → escalate
  • honesty_violation occurs                       → escalate
  • assistant_gave_up sentinel fires               → escalate (immediate)

Persistence:
  • `ai_escalations` collection — one document per escalation event.
  • `admin_notifications`         — surfaced in the AdminNotifications.js UI.

Outbound:
  • Email via Resend (re-uses the existing OWNER_EMAIL config from .env).
  • In-product banner via the existing AdminNotifications stream.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

log = logging.getLogger("zenrex.escalation")

_RESEND_API = "https://api.resend.com/emails"


async def create_escalation(
    *,
    db,
    project_id: Optional[str],
    user_id: Optional[str],
    reason: str,
    context: Dict[str, Any],
    severity: str = "medium",
) -> Dict[str, Any]:
    """Persist + dispatch an escalation. Idempotent within a 5-minute window
    on (project_id, reason) so a stuck loop doesn't spam the operator.

    Returns: {ok, escalation_id, suppressed?: bool}
    """
    if db is None:
        return {"ok": False, "error": "db not available"}

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # De-dupe: suppress identical reason within 5 minutes
    try:
        from datetime import timedelta
        window_start = (now - timedelta(minutes=5)).isoformat()
        recent = await db.ai_escalations.find_one({
            "project_id": project_id,
            "reason": reason,
            "ts": {"$gte": window_start},
        })
        if recent:
            return {"ok": True, "suppressed": True, "escalation_id": recent.get("id")}
    except Exception:
        pass

    esc_id = str(uuid.uuid4())
    doc = {
        "id": esc_id,
        "project_id": project_id,
        "user_id": user_id,
        "reason": reason,
        "severity": severity,
        "context": context,
        "ts": now_iso,
        "resolved": False,
    }
    try:
        await db.ai_escalations.insert_one(doc)
    except Exception as e:
        log.warning(f"[escalation] insert failed: {e}")
        return {"ok": False, "error": str(e)}

    # In-app admin notification (consumed by AdminNotifications.js via
    # /api/owner/notifications). Schema must match the existing collection:
    # `owner_notifications` with `created_at` (not `ts`) and `read` (default false).
    try:
        await db.owner_notifications.insert_one({
            "id": str(uuid.uuid4()),
            "type": "ai_escalation",
            "severity": severity,
            "title": _title_ar_for_reason(reason),
            "message": _body_ar_for_reason(reason, context),
            "project_id": project_id,
            "user_id": user_id,
            "escalation_id": esc_id,
            "read": False,
            "created_at": now_iso,
        })
    except Exception as e:
        log.debug(f"[escalation] owner_notifications insert failed: {e}")

    # Outbound email
    await _send_email_via_resend(reason, severity, project_id, user_id, context)

    return {"ok": True, "escalation_id": esc_id, "suppressed": False}


async def _send_email_via_resend(
    reason: str,
    severity: str,
    project_id: Optional[str],
    user_id: Optional[str],
    context: Dict[str, Any],
) -> None:
    """Send an Arabic email to the operator via Resend. Skips silently if
    RESEND_API_KEY / OWNER_EMAIL aren't configured — never crashes the chat."""
    api_key = os.environ.get("RESEND_API_KEY")
    to_addr = os.environ.get("OWNER_EMAIL") or os.environ.get("OPERATOR_EMAIL")
    from_addr = os.environ.get("RESEND_FROM") or "Zenrex Alerts <alerts@zenrex.ai>"
    if not api_key or not to_addr:
        log.info(f"[escalation] email skipped (no RESEND_API_KEY/OWNER_EMAIL) reason={reason}")
        return

    title = _title_ar_for_reason(reason)
    body = _body_ar_for_reason(reason, context)
    severity_label = {"critical": "🔴 حرج", "high": "🟠 عالٍ", "medium": "🟡 متوسط", "low": "🟢 منخفض"}.get(severity, severity)

    html = f"""
<div dir="rtl" style="font-family:Tahoma,Arial,sans-serif;max-width:640px;margin:auto;background:#0c0c12;color:#e5e7eb;padding:24px;border-radius:14px;">
  <h2 style="color:#67e8f9;margin:0 0 8px;">{title}</h2>
  <p style="margin:0 0 16px;color:#9ca3af;font-size:13px;">شدّة الحدث: <b>{severity_label}</b></p>
  <div style="background:#1a1a24;border-right:3px solid #f59e0b;padding:12px 16px;border-radius:6px;font-size:14px;line-height:1.7;">
    {body}
  </div>
  <div style="margin-top:18px;font-size:12px;color:#6b7280;">
    Project: <code style="color:#a5f3fc;">{project_id or '—'}</code><br/>
    User: <code style="color:#a5f3fc;">{user_id or '—'}</code><br/>
    Time: {datetime.now(timezone.utc).isoformat()}
  </div>
  <p style="margin-top:22px;font-size:11px;color:#6b7280;">— Zenrex Auto-Escalation Bridge</p>
</div>
"""
    try:
        async with httpx.AsyncClient(timeout=15) as cl:
            r = await cl.post(
                _RESEND_API,
                json={
                    "from": from_addr,
                    "to": [to_addr],
                    "subject": f"[Zenrex] {title}",
                    "html": html,
                },
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if r.status_code not in (200, 202):
                log.warning(f"[escalation] resend {r.status_code}: {r.text[:200]}")
    except Exception as e:
        log.warning(f"[escalation] email send failed: {type(e).__name__}: {e}")


def _title_ar_for_reason(reason: str) -> str:
    return {
        "supervisor_thrashing": "🛡️ مراقب تلقائي: الذكاء عالق في لوب متكرر",
        "honesty_violation": "🛡️ فحص الصدق: ادّعى الذكاء إنجازاً بدون تحقق",
        "assistant_gave_up": "🚧 الذكاء استسلم — يحتاج تدخل بشري",
        "tool_chain_failure": "❌ سلسلة فشل في الأدوات",
        "auto_e1_review": "🤝 E1 تدخّل تلقائياً وأنتج درساً تصحيحياً",
        "manual_lesson": "📝 درس يدوي من الموظف",
    }.get(reason, f"⚠️ تنبيه AI: {reason}")


def _body_ar_for_reason(reason: str, context: Dict[str, Any]) -> str:
    """Plain-text Arabic body. Kept short — the operator wants signal, not noise."""
    if reason == "supervisor_thrashing":
        n = context.get("intervention_count", "?")
        last = context.get("last_pattern", {})
        return (
            f"الذكاء الصناعي تدخّل المراقب التلقائي <b>{n}</b> مرات في نفس المحادثة. "
            f"آخر نمط: <code>{last.get('pattern', '?')}</code> على أداة "
            f"<code>{last.get('tool_name', '?')}</code>. "
            f"يُنصح بمراجعة المشروع وتعديل خارطة الطريق يدوياً."
        )
    if reason == "honesty_violation":
        ex = context.get("excerpt", "")[:200]
        return (
            f"الذكاء ادّعى إنجاز شيء بدون استدعاء أي أداة تحقق فعلية. "
            f"المقتطف: «{ex}». تم حفظ الدرس وسيُحقن في الدور القادم تلقائياً، "
            f"لكن إن تكرر الأمر فالنموذج يحتاج تعديل في الـ system prompt."
        )
    if reason == "assistant_gave_up":
        return (
            "الذكاء صرّح بعجزه عن إكمال المهمة. هذا نادر جداً — تأكد إن العميل "
            "ما طلب شيء خارج صلاحياتنا، وإلا الذكاء يحتاج تدريب على هذا النمط."
        )
    if reason == "tool_chain_failure":
        return (
            f"تكرر فشل أدوات متعددة بشكل غير معتاد. ربما هناك خلل في DB أو "
            f"خدمة خارجية. السياق: <pre style='direction:ltr;text-align:left'>"
            f"{str(context)[:600]}</pre>"
        )
    if reason == "auto_e1_review":
        diag = context.get("diagnosis", "—")
        lesson = context.get("lesson", "—")
        nxt = context.get("next_action", "—")
        return (
            f"الذكاء تعثّر 3 مرات، فتدخّل <b>E1 تلقائياً</b> وأنتج التشخيص التالي:<br/><br/>"
            f"<b>التشخيص:</b> {diag}<br/>"
            f"<b>الدرس المحقون:</b> {lesson}<br/>"
            f"<b>الخطوة القادمة:</b> {nxt}<br/><br/>"
            f"<i>الدرس انحفظ بـ priority=high وراح يطلع في system prompt الدور القادم تلقائياً. "
            f"لا تحتاج عمل شيء — هذا فقط للعلم.</i>"
        )
    if reason == "manual_lesson":
        ls = context.get("lesson", "—")
        return f"تمت إضافة درس يدوي بواسطة الموظف:<br/><br/><b>«{ls}»</b><br/><br/><i>تم تطبيقه بـ priority=critical.</i>"
    return f"<pre style='direction:ltr;text-align:left'>{str(context)[:800]}</pre>"


# ─────────────────────────────────────────────────────────────────────────────
# Trigger detector — called from chat loop
# ─────────────────────────────────────────────────────────────────────────────

def should_escalate(
    *,
    supervisor_state: Any,
    honesty_violation: bool,
    last_pattern: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Decide whether to trigger an escalation. Returns the escalation
    descriptor or None.
    """
    # Honesty violation — always escalate (low severity, just FYI)
    if honesty_violation:
        return {"reason": "honesty_violation", "severity": "low"}
    if supervisor_state is None:
        return None
    n = getattr(supervisor_state, "intervention_count_total", 0) or 0
    if n >= 3:
        return {
            "reason": "supervisor_thrashing",
            "severity": "high" if n >= 5 else "medium",
            "context": {
                "intervention_count": n,
                "last_pattern": last_pattern or {},
            },
        }
    if last_pattern and last_pattern.get("pattern") == "assistant_gave_up":
        return {"reason": "assistant_gave_up", "severity": "high"}
    return None
