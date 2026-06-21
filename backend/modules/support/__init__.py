"""
Support Tickets + Suggestions + In-App Notifications.

Endpoints:
  USER:
    POST   /api/support/tickets                 — create ticket
    GET    /api/support/tickets/me              — my tickets
    GET    /api/support/tickets/{id}            — thread
    POST   /api/support/tickets/{id}/messages   — reply
    POST   /api/support/ai-quick-answer         — AI tries to answer first

  ADMIN:
    GET    /api/admin/support/tickets           — all tickets (filter by status)
    POST   /api/admin/support/tickets/{id}/reply
    POST   /api/admin/support/tickets/{id}/close

  NOTIFICATIONS (any user):
    GET    /api/notifications/me                — paged
    POST   /api/notifications/{id}/read         — mark single
    POST   /api/notifications/mark-all-read

Collections:
  support_tickets    { id, user_id, subject, category (support|suggestion|bug|feature),
                       status (open|replied|closed), priority (low|normal|high),
                       created_at, last_message_at, last_replier_role, ai_answered }
  support_messages   { id, ticket_id, sender_id, sender_role (user|admin|ai), content, created_at }
  user_notifications { id, user_id, type, title, body, link, read, created_at }
"""
from __future__ import annotations
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("zenrex.support")
router = APIRouter(tags=["support"])


def _now(): return datetime.now(timezone.utc)
def _iso(d): return d.isoformat() if isinstance(d, datetime) else d


# ─────────────────── Models ───────────────────
class TicketIn(BaseModel):
    subject: str = Field(..., min_length=2, max_length=200)
    body: str = Field(..., min_length=2, max_length=4000)
    category: str = Field("support", pattern="^(support|suggestion|bug|feature|payout|refund|billing)$")
    priority: str = Field("normal", pattern="^(low|normal|high)$")


class MessageIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class AdminReplyIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    new_status: Optional[str] = Field(None, pattern="^(open|replied|awaiting_user|resolved|closed|auto_resolved)$")
    new_priority: Optional[str] = Field(None, pattern="^(low|normal|high)$")
    is_internal: bool = False


class AIQuickIn(BaseModel):
    question: str = Field(..., min_length=2, max_length=600)


# FAQ knowledge base — fast canned answers for common topics
_FAQ = [
    {
        "keys": ["payout", "تحويل", "سحب", "paypal", "بايبال", "فلوس", "عمولة", "عمولتي"],
        "answer": "لطلب تحويل أرباحك:\n1. اذهب إلى لوحة المسوّق (/affiliate)\n2. أضف بريد PayPal في إعدادات السحب\n3. اضغط 'طلب تحويل' — يخصم $2 رسوم وتستلم الباقي خلال 24-48 ساعة بعد موافقة الإدارة.\nالحد الأدنى $25.",
    },
    {
        "keys": ["affiliate", "marketer", "مسوّق", "مسوق", "تسويق", "كيف اصير مسوق"],
        "answer": "للانضمام لبرنامج المسوّقين:\n1. اذهب إلى /affiliate واضغط 'قدّم الآن'\n2. ستحصل على كود فريد\n3. شارك رابطك (/r/CODE) في تويتر/انستجرام/يوتيوب/واتساب\n4. عمولة 20% على كل عميل تجلبه.\nاستخدم مُنشئ الروابط داخل لوحتك لإنشاء روابط UTM احترافية.",
    },
    {
        "keys": ["language", "لغة", "ترجمة", "english", "إنجليزي"],
        "answer": "اضغط على أيقونة الـ globe في زاوية الشاشة لاختيار لغتك (97 لغة مدعومة). الموقع يكتشف لغتك تلقائياً من بلدك أيضاً.",
    },
    {
        "keys": ["price", "سعر", "اشتراك", "باقة", "ترقية", "credits", "شعلة"],
        "answer": "أسعارنا متدرجة:\n- مجاني: $0\n- Starter: $9\n- Indie: $29\n- Studio: $79\n- Pro Studio: $199\nاطلع على /pricing للتفاصيل الكاملة. كل دولار = 1000 شعلة.",
    },
    {
        "keys": ["website", "موقع", "freebuild", "بناء"],
        "answer": "لبناء موقع: اذهب إلى FreeBuild (/freebuild) وأخبر الذكاء بفكرتك. يبني لك الموقع كاملاً مع كود مباشر وحفظ تلقائي ودعم GitHub.",
    },
    {
        "keys": ["game", "لعبة", "ألعاب"],
        "answer": "Game Studio (/games) يبني لك ألعاب 2D/3D بالذكاء الاصطناعي مع HTML5/Unity/Phaser/Three.js.",
    },
]


def _faq_lookup(q: str) -> Optional[str]:
    q_l = q.lower()
    for entry in _FAQ:
        for k in entry["keys"]:
            if k.lower() in q_l:
                return entry["answer"]
    return None


# ─────────────────── AI Auto-Triage (single Claude call) ───────────────────
_REFUND_KEYWORDS = [
    "استرداد", "ارجاع", "إرجاع", "ترجيع", "ترجع", "استرجاع",
    "refund", "chargeback", "ارجع فلوسي", "رد فلوسي", "رد المبلغ",
    "ارجاع المبلغ", "أبغى فلوسي", "ابي فلوسي",
]


def _looks_like_refund(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in _REFUND_KEYWORDS)


async def _ai_triage(subject: str, body_text: str) -> dict:
    """
    Classify a new ticket and draft an AI reply in one Claude call.
    Returns: {category, priority, summary_ar, ai_reply_ar, escalate}

    Rules embedded in the prompt:
      - Refund → decline politely per ToS, escalate=False
      - Technical/billing → ask for screenshots if missing, escalate=True
      - Other → polite ack, escalate=True
    """
    # Cheap path: regex catches obvious refund requests so we never spend a
    # Claude turn on them.
    if _looks_like_refund(subject + " " + body_text):
        return {
            "category": "refund",
            "priority": "low",
            "summary_ar": f"طلب استرداد — {(subject or body_text)[:80]}",
            "ai_reply_ar": (
                "نقدّر تواصلك معنا.\n\n"
                "بحسب شروط استخدام Zenrex، النقاط المستخدمة في توليد محتوى بالذكاء الاصطناعي "
                "(مواقع/تطبيقات/صور/فيديوهات) **غير قابلة للاسترداد**، لأن تكلفة المعالجة تُدفع فور التوليد. "
                "الخدمة تُقدَّم \"كما هي\" بحسب الشروط المعلَنة عند التسجيل.\n\n"
                "إذا واجهتك مشكلة تقنية فعلية (مثل: شحنت ولم تصل النقاط، خطأ في خصم، عطل في التوليد)، "
                "أعد فتح تذكرة جديدة بنوع \"مشكلة تقنية\" وأرفق صورة/فيديو، وسنحلها بسرور خلال 24 ساعة."
            ),
            "escalate": False,
        }

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    use_emergent = False
    if not api_key:
        api_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
        use_emergent = True
    if not api_key:
        return {
            "category": "support",
            "priority": "normal",
            "summary_ar": (body_text[:140] + "…") if len(body_text) > 140 else body_text,
            "ai_reply_ar": "تم استلام رسالتك وسيرد عليك فريقنا قريباً.",
            "escalate": True,
        }

    system = (
        "أنت موظف دعم ذكي لمنصة Zenrex (منصة عربية لبناء مواقع/تطبيقات/ألعاب بالذكاء الاصطناعي). "
        "صنّف رسالة العميل واردّ بإيجاز.\n\n"
        "صنّفها لواحدة من:\n"
        "• refund    — طلب استرداد/إلغاء/إرجاع نقاط\n"
        "• bug       — خطأ تقني، عُطل، AI لا يستجيب\n"
        "• billing   — مشكلة دفع، شحن لم يصل، خصم خاطئ\n"
        "• feature   — طلب ميزة جديدة\n"
        "• suggestion— اقتراح تحسيني\n"
        "• support   — سؤال عام\n\n"
        "قواعد الرد:\n"
        "1) إذا refund: اعتذر بأدب واشرح أن النقاط المستخدمة غير قابلة للاسترداد بحسب الشروط. ضع escalate=false.\n"
        "2) إذا bug/billing: اشكر العميل، إذا لم يُرفق صور/فيديو اطلب رفعها، ثم أخبره أن الإدارة سترد خلال 24 ساعة. escalate=true.\n"
        "3) إذا feature/suggestion/support: رد ودياً وبإيجاز. escalate=true.\n\n"
        "أعد JSON فقط (بدون markdown):\n"
        "{\"category\":\"...\",\"priority\":\"low|normal|high\",\"summary_ar\":\"سطر واحد\",\"ai_reply_ar\":\"...\",\"escalate\":true|false}"
    )
    user_text = f"الموضوع: {subject}\n\nالرسالة:\n{body_text}"

    try:
        from anthropic import AsyncAnthropic
        kwargs = {"api_key": api_key}
        if use_emergent:
            kwargs["base_url"] = "https://integrations.emergentagent.com/llm"
        client = AsyncAnthropic(**kwargs)
        resp = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": user_text}],
        )
        raw = "".join(getattr(b, "text", "") for b in resp.content)
        import json, re
        m = re.search(r"\{[\s\S]*\}", raw)
        data = json.loads(m.group(0)) if m else json.loads(raw)
        cat = data.get("category", "support")
        valid_cats = {"refund", "bug", "billing", "feature", "suggestion", "support"}
        if cat not in valid_cats:
            cat = "support"
        return {
            "category": cat,
            "priority": data.get("priority") or "normal",
            "summary_ar": data.get("summary_ar") or body_text[:140],
            "ai_reply_ar": data.get("ai_reply_ar") or "تم استلام رسالتك.",
            "escalate": bool(data.get("escalate", True)),
        }
    except Exception:
        logger.warning("AI triage failed — using fallback", exc_info=True)
        return {
            "category": "support",
            "priority": "normal",
            "summary_ar": (body_text[:140] + "…") if len(body_text) > 140 else body_text,
            "ai_reply_ar": "تم استلام رسالتك وسيرد عليك فريقنا قريباً.",
            "escalate": True,
        }


async def _build_audit_snapshot(db, user_id: str) -> dict:
    """Compact audit snapshot of a user — shown to admins on every ticket."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0}) or {}
    try:
        txns = await db.payment_transactions.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("created_at", -1).limit(10).to_list(length=10)
    except Exception:
        txns = []
    try:
        usage = await db.usage_events.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("created_at", -1).limit(10).to_list(length=10)
    except Exception:
        usage = []
    try:
        project_count = await db.freebuild_projects.count_documents(
            {"user_id": user_id, "status": {"$ne": "deleted"}}
        )
    except Exception:
        project_count = 0
    try:
        storage_sub = await db.storage_subscriptions.find_one({"user_id": user_id}, {"_id": 0}) or {}
    except Exception:
        storage_sub = {}
    return {
        "user": {
            "id": user.get("id"),
            "email": user.get("email"),
            "name": user.get("name"),
            "role": user.get("role"),
            "credits": user.get("credits"),
            "storage_tier": user.get("storage_tier"),
            "created_at": _iso(user.get("created_at")),
        },
        "project_count": project_count,
        "storage_subscription": storage_sub,
        "recent_transactions": txns,
        "recent_usage": usage,
    }


# ─────────────────── Notify helper (callable from other modules) ───────────────────
def notify_factory(db):
    """Returns an async `notify` function bound to the given db handle.
    Sync factory so callers don't need to await it at app-init time."""
    async def notify(user_id: str, n_type: str, title: str, body: str, link: Optional[str] = None):
        try:
            await db.user_notifications.insert_one({
                "id": uuid.uuid4().hex,
                "user_id": user_id,
                "type": n_type,
                "title": title,
                "body": body,
                "link": link,
                "read": False,
                "created_at": _now(),
            })
        except Exception:
            logger.exception("notify failed")
    return notify


# ═════════════════════════════════════════════════════════════
def build_router(db, get_current_user):

    def _is_admin(u):
        role = (u.get("role") or "").lower()
        return role in {"admin", "super_admin", "owner"} or bool(u.get("is_owner"))

    # ───── USER ─────
    @router.post("/support/tickets")
    async def create_ticket(body: TicketIn, user=Depends(get_current_user)):
        uid = user["user_id"]
        tid = uuid.uuid4().hex
        # AI auto-triage (refund auto-decline, technical → ask for media)
        triage = await _ai_triage(body.subject, body.body)
        final_category = body.category if body.category != "support" else triage["category"]
        final_priority = body.priority if body.priority != "normal" else triage["priority"]
        # If AI says auto-resolved (refund), close it immediately.
        ai_resolved = not triage["escalate"]
        initial_status = "auto_resolved" if ai_resolved else "open"

        # Cache an audit snapshot at creation time so admins always have one.
        try:
            audit = await _build_audit_snapshot(db, uid)
        except Exception:
            audit = {}

        await db.support_tickets.insert_one({
            "id": tid,
            "user_id": uid,
            "user_email": user.get("email"),
            "user_name": user.get("name") or user.get("email"),
            "subject": body.subject,
            "category": final_category,
            "priority": final_priority,
            "status": initial_status,
            "ai_summary": triage["summary_ar"],
            "ai_answered": True,
            "ai_resolved": ai_resolved,
            "audit_snapshot": audit,
            "created_at": _now(),
            "last_message_at": _now(),
            "last_replier_role": "ai",
            "unread_for_user": True,
            "unread_for_admin": not ai_resolved,
        })
        # User's first message
        await db.support_messages.insert_one({
            "id": uuid.uuid4().hex,
            "ticket_id": tid,
            "sender_id": uid,
            "sender_role": "user",
            "content": body.body,
            "attachments": [],
            "created_at": _now(),
        })
        # AI auto-reply
        await db.support_messages.insert_one({
            "id": uuid.uuid4().hex,
            "ticket_id": tid,
            "sender_id": "ai",
            "sender_role": "ai",
            "content": triage["ai_reply_ar"],
            "attachments": [],
            "created_at": _now(),
        })
        # Notify admins ONLY for tickets that escalate
        if not ai_resolved:
            try:
                admins = await db.users.find(
                    {"$or": [{"role": "admin"}, {"role": "super_admin"}, {"role": "owner"}, {"is_owner": True}]},
                    {"_id": 0, "id": 1},
                ).to_list(length=20)
                for ad in admins:
                    await db.user_notifications.insert_one({
                        "id": uuid.uuid4().hex,
                        "user_id": ad["id"],
                        "type": "support_new",
                        "title": f"📨 تذكرة جديدة: {final_category}",
                        "body": body.subject[:120],
                        "link": "/admin/support",
                        "read": False,
                        "created_at": _now(),
                    })
            except Exception:
                pass
        return {
            "id": tid,
            "category": final_category,
            "status": initial_status,
            "ai_answered": True,
            "ai_resolved": ai_resolved,
            "ai_reply": triage["ai_reply_ar"],
        }

    @router.get("/support/tickets/me")
    async def my_tickets(user=Depends(get_current_user)):
        uid = user["user_id"]
        out = []
        async for t in db.support_tickets.find({"user_id": uid}, {"_id": 0}, sort=[("last_message_at", -1)]).limit(100):
            t["created_at"] = _iso(t.get("created_at"))
            t["last_message_at"] = _iso(t.get("last_message_at"))
            out.append(t)
        return {"items": out, "total": len(out)}

    @router.get("/support/tickets/{tid}")
    async def get_ticket(tid: str, user=Depends(get_current_user)):
        t = await db.support_tickets.find_one({"id": tid}, {"_id": 0})
        if not t:
            raise HTTPException(404, "غير موجود")
        if t["user_id"] != user["user_id"] and not _is_admin(user):
            raise HTTPException(403, "لا يمكنك رؤية هذه التذكرة")
        msgs = []
        async for m in db.support_messages.find({"ticket_id": tid}, {"_id": 0}, sort=[("created_at", 1)]):
            m["created_at"] = _iso(m.get("created_at"))
            msgs.append(m)
        t["created_at"] = _iso(t.get("created_at"))
        t["last_message_at"] = _iso(t.get("last_message_at"))
        return {"ticket": t, "messages": msgs}

    @router.post("/support/tickets/{tid}/messages")
    async def add_message(tid: str, body: MessageIn, user=Depends(get_current_user)):
        t = await db.support_tickets.find_one({"id": tid})
        if not t:
            raise HTTPException(404, "غير موجود")
        if t["user_id"] != user["user_id"] and not _is_admin(user):
            raise HTTPException(403, "ممنوع")
        role = "admin" if _is_admin(user) and t["user_id"] != user["user_id"] else "user"
        await db.support_messages.insert_one({
            "id": uuid.uuid4().hex,
            "ticket_id": tid,
            "sender_id": user["user_id"],
            "sender_role": role,
            "content": body.content,
            "created_at": _now(),
        })
        new_status = "replied" if role == "admin" else "open"
        await db.support_tickets.update_one(
            {"id": tid},
            {"$set": {"last_message_at": _now(), "last_replier_role": role, "status": new_status}},
        )
        # Notify the other party
        try:
            other = t["user_id"] if role == "admin" else None
            if other:
                await db.user_notifications.insert_one({
                    "id": uuid.uuid4().hex,
                    "user_id": other,
                    "type": "support_reply",
                    "title": "💬 رد من فريق الدعم",
                    "body": f"{body.content[:120]}",
                    "link": f"/support/tickets/{tid}",
                    "read": False,
                    "created_at": _now(),
                })
            else:
                # user sent → notify admins
                admins = await db.users.find(
                    {"$or": [{"role": "admin"}, {"role": "super_admin"}, {"role": "owner"}]},
                    {"_id": 0, "id": 1},
                ).to_list(length=10)
                for ad in admins:
                    await db.user_notifications.insert_one({
                        "id": uuid.uuid4().hex,
                        "user_id": ad["id"],
                        "type": "support_user_reply",
                        "title": "💬 رد جديد من العميل",
                        "body": body.content[:120],
                        "link": "/admin/support",
                        "read": False,
                        "created_at": _now(),
                    })
        except Exception:
            pass
        return {"ok": True}

    @router.post("/support/ai-quick-answer")
    async def ai_quick(body: AIQuickIn, user=Depends(get_current_user)):
        """AI tries to answer instantly before user even submits ticket."""
        faq = _faq_lookup(body.question)
        if faq:
            return {"answer": faq, "source": "faq", "confident": True}
        # Fall back to Claude
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
            prompt = (
                "أنت موظف دعم فني محترف لمنصة Zenrex (مواقع وتطبيقات وألعاب وصور وفيديوهات بالذكاء الاصطناعي). "
                "أجب بإيجاز (4 أسطر كحد أقصى) وبالعربية ووُدّ. "
                "إذا لم تعرف الإجابة، قل: 'سأحوّل سؤالك لفريقنا — اضغط إرسال التذكرة'.\n\n"
                f"سؤال العميل: {body.question}"
            )
            r = await client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            txt = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
            return {"answer": txt, "source": "ai", "confident": "حوّل" not in txt}
        except Exception:
            return {"answer": "سأحوّل سؤالك لفريقنا — اضغط إرسال التذكرة", "source": "fallback", "confident": False}

    # ───── ADMIN ─────
    @router.get("/admin/support/tickets")
    async def admin_list(status: Optional[str] = None, category: Optional[str] = None,
                          user=Depends(get_current_user)):
        if not _is_admin(user):
            raise HTTPException(403, "للأدمن فقط")
        m = {}
        if status: m["status"] = status
        if category: m["category"] = category
        out = []
        async for t in db.support_tickets.find(m, {"_id": 0}, sort=[("last_message_at", -1)]).limit(200):
            t["created_at"] = _iso(t.get("created_at"))
            t["last_message_at"] = _iso(t.get("last_message_at"))
            out.append(t)
        return {"items": out, "total": len(out)}

    @router.post("/admin/support/tickets/{tid}/close")
    async def admin_close(tid: str, user=Depends(get_current_user)):
        if not _is_admin(user):
            raise HTTPException(403, "للأدمن فقط")
        await db.support_tickets.update_one({"id": tid}, {"$set": {"status": "closed", "closed_at": _now()}})
        return {"ok": True}

    @router.get("/support/unread-count")
    async def support_unread_count(user=Depends(get_current_user)):
        n = await db.support_tickets.count_documents({
            "user_id": user["user_id"],
            "unread_for_user": True,
        })
        return {"unread": n}

    @router.post("/support/tickets/{tid}/attach")
    async def attach_files(tid: str, user=Depends(get_current_user)):
        # Placeholder removed — use the proper one below.
        raise HTTPException(410, "Deprecated — use the new attach endpoint")

    # ───── ADMIN ─────
    @router.get("/admin/support/tickets/{tid}")
    async def admin_get_ticket(tid: str, user=Depends(get_current_user)):
        if not _is_admin(user):
            raise HTTPException(403, "للأدمن فقط")
        t = await db.support_tickets.find_one({"id": tid}, {"_id": 0})
        if not t:
            raise HTTPException(404, "غير موجود")
        # Refresh the audit snapshot on each admin view
        try:
            t["audit_snapshot"] = await _build_audit_snapshot(db, t["user_id"])
        except Exception:
            pass
        msgs = []
        async for m in db.support_messages.find({"ticket_id": tid}, {"_id": 0}, sort=[("created_at", 1)]):
            m["created_at"] = _iso(m.get("created_at"))
            msgs.append(m)
        t["created_at"] = _iso(t.get("created_at"))
        t["last_message_at"] = _iso(t.get("last_message_at"))
        # Mark admin-read
        await db.support_tickets.update_one({"id": tid}, {"$set": {"unread_for_admin": False}})
        return {"ticket": t, "messages": msgs}

    @router.post("/admin/support/tickets/{tid}/reply")
    async def admin_reply(tid: str, body: AdminReplyIn, user=Depends(get_current_user)):
        if not _is_admin(user):
            raise HTTPException(403, "للأدمن فقط")
        t = await db.support_tickets.find_one({"id": tid})
        if not t:
            raise HTTPException(404, "غير موجود")
        await db.support_messages.insert_one({
            "id": uuid.uuid4().hex,
            "ticket_id": tid,
            "sender_id": user["user_id"],
            "sender_role": "admin",
            "sender_name": user.get("name") or user.get("email") or "فريق الدعم",
            "content": body.content,
            "attachments": [],
            "is_internal": bool(body.is_internal),
            "created_at": _now(),
        })
        update = {"updated_at": _now()}
        if not body.is_internal:
            update["last_message_at"] = _now()
            update["last_replier_role"] = "admin"
            update["status"] = body.new_status or "replied"
            update["unread_for_user"] = True
            update["unread_for_admin"] = False
        if body.new_priority:
            update["priority"] = body.new_priority
        await db.support_tickets.update_one({"id": tid}, {"$set": update})
        # Notify user
        if not body.is_internal:
            try:
                await db.user_notifications.insert_one({
                    "id": uuid.uuid4().hex,
                    "user_id": t["user_id"],
                    "type": "support_reply",
                    "title": "💬 رد من فريق الدعم",
                    "body": body.content[:120],
                    "link": f"/support/tickets/{tid}",
                    "read": False,
                    "created_at": _now(),
                })
            except Exception:
                pass
        return {"ok": True}

    # ───── NOTIFICATIONS ─────
    @router.get("/notifications/me")
    async def my_notifications(limit: int = 30, user=Depends(get_current_user)):
        uid = user["user_id"]
        out = []
        async for n in db.user_notifications.find({"user_id": uid}, {"_id": 0}, sort=[("created_at", -1)]).limit(limit):
            n["created_at"] = _iso(n.get("created_at"))
            out.append(n)
        unread = await db.user_notifications.count_documents({"user_id": uid, "read": False})
        return {"items": out, "unread": unread}

    @router.post("/notifications/{nid}/read")
    async def mark_read(nid: str, user=Depends(get_current_user)):
        await db.user_notifications.update_one(
            {"id": nid, "user_id": user["user_id"]},
            {"$set": {"read": True}},
        )
        return {"ok": True}

    @router.post("/notifications/mark-all-read")
    async def mark_all(user=Depends(get_current_user)):
        await db.user_notifications.update_many(
            {"user_id": user["user_id"], "read": False},
            {"$set": {"read": True}},
        )
        return {"ok": True}

    return router


def build_router_with_uploads(db, get_current_user):
    """Adds upload + serve endpoints on top of the base support router."""
    from fastapi import UploadFile, File
    from fastapi.responses import FileResponse

    r = build_router(db, get_current_user)

    ALLOWED = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif",
               "video/mp4", "video/webm", "video/quicktime", "application/pdf"}
    MAX_BYTES = 25 * 1024 * 1024

    @r.post("/support/tickets/{tid}/upload", response_model=None)
    async def upload_attachment(
        tid: str,
        files: list = File(...),
        user=Depends(get_current_user),
    ):
        t = await db.support_tickets.find_one({"id": tid})
        if not t:
            raise HTTPException(404, "غير موجود")
        if t["user_id"] != user["user_id"]:
            raise HTTPException(403, "ممنوع")
        upload_dir = os.environ.get("ZENREX_SUPPORT_UPLOAD_DIR", "/app/data/support_uploads")
        os.makedirs(upload_dir, exist_ok=True)
        atts = []
        for f in files[:5]:
            if f.content_type not in ALLOWED:
                raise HTTPException(400, f"نوع غير مسموح: {f.content_type}")
            data = await f.read()
            if len(data) > MAX_BYTES:
                raise HTTPException(413, "ملف أكبر من 25 ميجا")
            fname = f"{uuid.uuid4().hex}_{(f.filename or 'file').replace('/', '_')[:80]}"
            with open(os.path.join(upload_dir, fname), "wb") as fh:
                fh.write(data)
            atts.append({
                "url": f"/api/support/attachment/{fname}",
                "name": f.filename or fname,
                "mime": f.content_type,
                "size": len(data),
            })
        await db.support_messages.insert_one({
            "id": uuid.uuid4().hex,
            "ticket_id": tid,
            "sender_id": user["user_id"],
            "sender_role": "user",
            "content": f"🖇️ أرفقت {len(atts)} ملف(ات) لتوضيح المشكلة",
            "attachments": atts,
            "created_at": _now(),
        })
        await db.support_tickets.update_one(
            {"id": tid},
            {"$set": {
                "last_message_at": _now(),
                "last_replier_role": "user",
                "status": "open",
                "unread_for_admin": True,
            }},
        )
        return {"attachments": atts}

    @r.get("/support/attachment/{filename}")
    async def get_attachment(filename: str, user=Depends(get_current_user)):
        if "/" in filename or ".." in filename:
            raise HTTPException(400, "اسم ملف غير صالح")
        upload_dir = os.environ.get("ZENREX_SUPPORT_UPLOAD_DIR", "/app/data/support_uploads")
        full = os.path.join(upload_dir, filename)
        if not os.path.exists(full):
            raise HTTPException(404, "غير موجود")
        return FileResponse(full)

    return r
