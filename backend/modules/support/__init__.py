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

logger = logging.getLogger("zitex.support")
router = APIRouter(tags=["support"])


def _now(): return datetime.now(timezone.utc)
def _iso(d): return d.isoformat() if isinstance(d, datetime) else d


# ─────────────────── Models ───────────────────
class TicketIn(BaseModel):
    subject: str = Field(..., min_length=2, max_length=200)
    body: str = Field(..., min_length=2, max_length=4000)
    category: str = Field("support", pattern="^(support|suggestion|bug|feature|payout)$")
    priority: str = Field("normal", pattern="^(low|normal|high)$")


class MessageIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


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
        await db.support_tickets.insert_one({
            "id": tid,
            "user_id": uid,
            "user_email": user.get("email"),
            "user_name": user.get("name") or user.get("email"),
            "subject": body.subject,
            "category": body.category,
            "priority": body.priority,
            "status": "open",
            "created_at": _now(),
            "last_message_at": _now(),
            "last_replier_role": "user",
            "ai_answered": False,
        })
        # First message
        await db.support_messages.insert_one({
            "id": uuid.uuid4().hex,
            "ticket_id": tid,
            "sender_id": uid,
            "sender_role": "user",
            "content": body.body,
            "created_at": _now(),
        })
        # AI quick-answer (FAQ first, then Claude as fallback)
        ai_text = _faq_lookup(body.subject + " " + body.body)
        if ai_text:
            await db.support_messages.insert_one({
                "id": uuid.uuid4().hex,
                "ticket_id": tid,
                "sender_id": "ai",
                "sender_role": "ai",
                "content": ai_text,
                "created_at": _now(),
            })
            await db.support_tickets.update_one(
                {"id": tid},
                {"$set": {"ai_answered": True, "last_message_at": _now(),
                          "last_replier_role": "ai", "status": "replied"}},
            )
        # Notify admins
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
                    "title": f"📨 تذكرة جديدة: {body.category}",
                    "body": body.subject[:120],
                    "link": "/admin/support",
                    "read": False,
                    "created_at": _now(),
                })
        except Exception:
            pass
        return {"id": tid, "ai_answered": bool(ai_text)}

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
                "أنت موظف دعم فني محترف لمنصة Zitex (مواقع وتطبيقات وألعاب وصور وفيديوهات بالذكاء الاصطناعي). "
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
