"""
Customer-facing AI Chat Bot
───────────────────────────
A smart, multi-turn AI assistant embedded in each generated storefront.
Knows the store's products/menu/hours/services and answers in Arabic.

Endpoints:
  POST /api/websites/public/{slug}/chatbot           — send a message
  GET  /api/websites/public/{slug}/chatbot/config    — public config (welcome, enabled)
  PUT  /api/websites/projects/{pid}/chatbot/config   — owner updates config

Features:
  • Uses Claude Sonnet via Emergent Universal Key
  • Per-session memory (kept in-process by emergentintegrations)
  • Owner can: toggle on/off, set welcome message, set business hours, set fallback message
  • Rate-limited per session-id (basic — 60 turns/hour)
"""
import os
import json
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from emergentintegrations.llm.chat import LlmChat, UserMessage

log = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


_RATE: Dict[str, list] = {}  # session_id → [timestamps]


def _check_rate(session_id: str, limit: int = 60, window: int = 3600) -> bool:
    now = time.time()
    arr = _RATE.setdefault(session_id, [])
    arr[:] = [t for t in arr if now - t < window]
    if len(arr) >= limit:
        return False
    arr.append(now)
    return True


def _extract_contact_info(project: Dict[str, Any]) -> Dict[str, str]:
    """Pull phone/whatsapp/address/email/socials from sections (contact, footer, hero)."""
    info: Dict[str, str] = {}
    for s in (project.get("sections") or []):
        d = s.get("data") or {}
        for k_src, k_dst in (("phone", "phone"), ("whatsapp", "whatsapp"),
                              ("email", "email"), ("address", "address"),
                              ("map_url", "map_url"), ("instagram", "instagram"),
                              ("twitter", "twitter"), ("facebook", "facebook"),
                              ("tiktok", "tiktok"), ("city", "city")):
            if d.get(k_src) and not info.get(k_dst):
                info[k_dst] = str(d[k_src])[:200]
    return info


def _extract_faq(project: Dict[str, Any]) -> list:
    out = []
    for s in (project.get("sections") or []):
        if s.get("type") == "faq":
            for q in (s.get("data") or {}).get("items") or []:
                out.append({"q": str(q.get("q", ""))[:200], "a": str(q.get("a", ""))[:400]})
    return out


def _extract_about(project: Dict[str, Any]) -> str:
    for s in (project.get("sections") or []):
        if s.get("type") == "about":
            d = s.get("data") or {}
            txt = (d.get("text") or "") + " " + (d.get("subtitle") or "")
            return txt.strip()[:600]
    return ""


def _build_system_prompt(project: Dict[str, Any], customer: Optional[Dict[str, Any]] = None) -> str:
    """Build a comprehensive knowledge-base prompt for the storefront AI."""
    name = project.get("name") or "المتجر"
    vertical = project.get("vertical") or "store"
    cfg = project.get("chatbot_config") or {}
    welcome = cfg.get("welcome_message") or ""
    hours = cfg.get("business_hours") or ""
    extra = cfg.get("extra_context") or ""

    # ───────── PRODUCTS (full list, no truncation in count) ─────────
    products = []
    for p in (project.get("products") or []):
        line = f"• {p.get('name','')}"
        if p.get("price") is not None:
            line += f" — {p['price']} ر.س"
        if p.get("category"):
            line += f" [{p['category']}]"
        if p.get("stock") is not None:
            line += f" (المخزون: {p['stock']})"
        if p.get("description"):
            line += f" — {str(p['description'])[:140]}"
        products.append(line)
    product_block = "\n".join(products) if products else "(لا توجد منتجات بعد)"

    # ───────── SERVICES ─────────
    services = []
    for s in (project.get("services") or []):
        sline = f"• {s.get('name','')}"
        if s.get("price") is not None:
            sline += f" — {s['price']} ر.س"
        if s.get("duration_min"):
            sline += f" — {s['duration_min']} دقيقة"
        if s.get("description"):
            sline += f" — {str(s['description'])[:140]}"
        services.append(sline)
    services_block = "\n".join(services) if services else ""

    # ───────── LISTINGS (real estate) ─────────
    listings = []
    for ll in (project.get("listings") or [])[:60]:
        ln = f"• {ll.get('title','')}"
        if ll.get("price") is not None:
            ln += f" — {ll['price']} ر.س"
        if ll.get("city"):
            ln += f" — {ll['city']}"
        if ll.get("rooms"):
            ln += f" — {ll['rooms']} غرف"
        if ll.get("area_m2"):
            ln += f" — {ll['area_m2']} م²"
        listings.append(ln)
    listings_block = "\n".join(listings) if listings else ""

    # ───────── SHIPPING ─────────
    shipping = project.get("shipping_settings") or {}
    ship_lines = []
    if shipping.get("local_delivery_enabled"):
        fee = shipping.get("local_delivery_fee", 0)
        eta = shipping.get("local_delivery_eta_hours", "")
        city = shipping.get("store_city", "")
        ship_lines.append(f"• توصيل داخلي{f' (مدينة {city})' if city else ''}: {fee} ر.س{f' — التوصيل خلال {eta} ساعة' if eta else ''}")
    if shipping.get("free_shipping_above_sar"):
        ship_lines.append(f"• شحن مجاني للطلبات فوق {shipping['free_shipping_above_sar']} ر.س")
    enabled_providers = shipping.get("enabled_providers") or []
    if enabled_providers:
        prov_names = {"smsa": "SMSA", "aramex": "Aramex", "saudi_post": "البريد السعودي (SPL)",
                      "naqel": "ناقل", "dhl": "DHL", "fedex": "FedEx"}
        pretty = " · ".join(prov_names.get(p, p) for p in enabled_providers)
        ship_lines.append(f"• شركات الشحن المتاحة: {pretty}")
    if shipping.get("cod_markup_enabled"):
        ship_lines.append(f"• الدفع عند الاستلام متاح (+{shipping.get('cod_markup_sar', 0)} ر.س رسوم)")
    if shipping.get("insurance_enabled"):
        ship_lines.append(f"• تأمين الشحن متاح ({shipping.get('insurance_percent', 0)}% — حد أدنى {shipping.get('insurance_min_sar', 0)} ر.س)")
    if shipping.get("pickup_enabled"):
        addr = shipping.get("pickup_address", "")
        ship_lines.append(f"• استلام من المتجر متاح (مجاناً){f' — العنوان: {addr}' if addr else ''}")
    shipping_block = "\n".join(ship_lines) if ship_lines else ""

    # ───────── COUPONS ─────────
    coupons = []
    for c in (project.get("coupons") or []):
        if not c.get("active", True):
            continue
        code = c.get("code", "")
        kind = c.get("type", "percent")
        val = c.get("value", 0)
        if kind == "percent":
            coupons.append(f"• {code}: خصم {val}%")
        else:
            coupons.append(f"• {code}: خصم {val} ر.س")
    coupons_block = "\n".join(coupons) if coupons else ""

    # ───────── LOYALTY ─────────
    loyalty = project.get("loyalty_settings") or {}
    loyalty_block = ""
    if loyalty.get("enabled"):
        lines = []
        if loyalty.get("welcome_bonus"):
            lines.append(f"• {loyalty['welcome_bonus']} نقطة ترحيبية للأعضاء الجدد")
        if loyalty.get("points_per_sar"):
            lines.append(f"• {loyalty['points_per_sar']} نقطة لكل 1 ر.س مشتريات")
        if loyalty.get("redeem_rate"):
            lines.append(f"• قيمة النقطة: {loyalty['redeem_rate']} ر.س عند الاستبدال")
        if loyalty.get("referral_bonus"):
            lines.append(f"• {loyalty['referral_bonus']} نقطة عند دعوة صديق")
        loyalty_block = "\n".join(lines)

    # ───────── PAYMENT GATEWAYS ─────────
    pgs = project.get("payment_gateways") or {}
    enabled_pgs = [k for k, v in pgs.items() if isinstance(v, dict) and v.get("enabled")]
    pretty_pg = {"stripe": "بطاقات Visa/Master/مدى (Stripe)", "tap": "Tap (مدى/STC Pay)",
                 "moyasar": "Moyasar", "paypal": "PayPal", "tabby": "تابي (تقسيط)",
                 "tamara": "تمارا (تقسيط)", "cod": "الدفع عند الاستلام"}
    payments_block = "\n".join(f"• {pretty_pg.get(k, k)}" for k in enabled_pgs) if enabled_pgs else ""

    # ───────── SECTIONS / CONTACT / ABOUT / FAQ ─────────
    contact = _extract_contact_info(project)
    contact_lines = []
    for label, key in (("📞 الهاتف", "phone"), ("💬 واتساب", "whatsapp"),
                        ("📧 البريد", "email"), ("📍 العنوان", "address"),
                        ("🗺️ الموقع على الخريطة", "map_url"),
                        ("📷 إنستغرام", "instagram"), ("🐦 تويتر", "twitter"),
                        ("📘 فيسبوك", "facebook"), ("🎵 تيك توك", "tiktok")):
        if contact.get(key):
            contact_lines.append(f"{label}: {contact[key]}")
    contact_block = "\n".join(contact_lines)

    about = _extract_about(project)
    faq = _extract_faq(project)
    faq_block = "\n".join(f"س: {f['q']}\nج: {f['a']}" for f in faq) if faq else ""

    # ───────── CUSTOMER CONTEXT (if logged in) ─────────
    customer_block = ""
    if customer:
        cust_lines = [f"اسم الزبون: {customer.get('name', '')}".strip()]
        recent_orders = customer.get("recent_orders") or []
        if recent_orders:
            cust_lines.append("طلبات الزبون الأخيرة:")
            for o in recent_orders[:5]:
                cust_lines.append(
                    f"• #{o.get('id','')[:8]} — {o.get('status','')} — {o.get('total',0)} ر.س"
                    + (f" — تتبع: {o.get('tracking_url','')}" if o.get('tracking_url') else "")
                )
        customer_block = "\n".join(cust_lines)

    return f"""أنت "مساعد {name}" — مساعد ذكي خبير لمتجر/مكان أعمال {name} (نوع: {vertical}). تتحدث العربية الفصحى المبسطة بأسلوب ودود، دقيق، ومحترف.

🎯 مهمتك:
- جاوب الزبون بدقة باستخدام المعلومات أدناه فقط
- اقترح منتجات/خدمات ذات صلة بناءً على احتياج الزبون
- ساعد في تتبع الطلبات إذا كانت بيانات الزبون متاحة
- اشرح طرق الدفع/الشحن/الاسترجاع/الكوبونات بوضوح
- إذا كان السؤال خارج معلوماتك أو يحتاج موظف بشري (شكوى، طلب خاص، تخصيص، استرجاع، مشكلة في الفاتورة، طلب تواصل مباشر) → ابدأ ردك بالكلمة السرية الخاصة [HANDOFF] ثم اشرح للزبون أنك ستحول طلبه لموظف.
- لا تختلق أسعاراً أو منتجات أو خصومات غير موجودة هنا
- لا تطلب معلومات حساسة (بطاقات بنكية، كلمات سر، رموز OTP)
- اجعل الردود قصيرة (٢-٤ أسطر عادةً) لكن مفيدة

═════════ معلومات المتجر ═════════
🏪 الاسم: {name}
🏷️ النوع: {vertical}
{f"⏰ ساعات العمل: {hours}" if hours else ""}
{f"💡 رسالة الترحيب: {welcome}" if welcome else ""}

{f"═════════ عن المتجر ═════════{chr(10)}{about}" if about else ""}

{f"═════════ التواصل ═════════{chr(10)}{contact_block}" if contact_block else ""}

═════════ المنتجات ({len(project.get('products') or [])}) ═════════
{product_block}

{f"═════════ الخدمات ═════════{chr(10)}{services_block}" if services_block else ""}

{f"═════════ العقارات/القوائم ═════════{chr(10)}{listings_block}" if listings_block else ""}

{f"═════════ 🚚 الشحن والتوصيل ═════════{chr(10)}{shipping_block}" if shipping_block else ""}

{f"═════════ 💳 طرق الدفع ═════════{chr(10)}{payments_block}" if payments_block else ""}

{f"═════════ 🎟️ كوبونات الخصم ═════════{chr(10)}{coupons_block}" if coupons_block else ""}

{f"═════════ 🎁 برنامج الولاء ═════════{chr(10)}{loyalty_block}" if loyalty_block else ""}

{f"═════════ ❓ أسئلة شائعة ═════════{chr(10)}{faq_block}" if faq_block else ""}

{f"═════════ معلومات إضافية من المالك ═════════{chr(10)}{extra}" if extra else ""}

{f"═════════ 👤 الزبون الحالي ═════════{chr(10)}{customer_block}" if customer_block else ""}

⚠️ تذكير أخير:
- إذا الزبون احتاج لمحادثة موظف بشري، أو سأل سؤالاً ما تقدر تجاوب عليه بثقة عالية → ابدأ الرد بـ [HANDOFF] ثم اعتذر بلطف.
- لا تكتب [HANDOFF] إلا إذا فعلاً تحتاج تحويل للموظف."""


def init_routes(database) -> APIRouter:
    r = APIRouter(prefix="/websites", tags=["chatbot"])

    # ── Public: get chatbot config (welcome message, enabled flag) ──
    @r.get("/public/{slug}/chatbot/config")
    async def _public_config(slug: str):
        p = await database.website_projects.find_one(
            {"slug": slug, "status": "approved"},
            {"_id": 0, "name": 1, "chatbot_config": 1},
        )
        if not p:
            raise HTTPException(404, "غير موجود")
        cfg = p.get("chatbot_config") or {}
        return {
            "enabled": bool(cfg.get("enabled")),
            "welcome_message": cfg.get("welcome_message") or f"مرحباً! أنا المساعد الذكي لـ {p.get('name','المتجر')}. كيف أساعدك؟",
            "store_name": p.get("name") or "",
        }

    class ChatIn(BaseModel):
        message: str
        session_id: Optional[str] = None
        history: Optional[list] = None  # client-side transcript [{role, text}]

    @r.post("/public/{slug}/chatbot")
    async def _public_chat(slug: str, body: ChatIn):
        text = (body.message or "").strip()
        if not text:
            raise HTTPException(400, "message required")
        if len(text) > 1000:
            raise HTTPException(400, "message too long")

        p = await database.website_projects.find_one(
            {"slug": slug, "status": "approved"}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "غير موجود")

        cfg = p.get("chatbot_config") or {}
        if not cfg.get("enabled"):
            raise HTTPException(403, "المساعد الذكي غير مفعّل")

        api_key = os.environ.get("EMERGENT_LLM_KEY", "")
        if not api_key:
            raise HTTPException(500, "AI service unavailable")

        session_id = (body.session_id or "anon") + "@" + slug
        if not _check_rate(session_id):
            raise HTTPException(429, "لقد تجاوزت الحد المسموح. حاول لاحقاً.")

        try:
            chat = LlmChat(
                api_key=api_key,
                session_id=f"chatbot-{p['id']}-{session_id}",
                system_message=_build_system_prompt(p),
            ).with_model("anthropic", "claude-sonnet-4-5-20250929")

            reply = await chat.send_message(UserMessage(text=text))

            # Detect handoff request from the model
            handoff = False
            if isinstance(reply, str) and reply.lstrip().startswith("[HANDOFF]"):
                handoff = True
                reply = reply.replace("[HANDOFF]", "", 1).strip()
                if not reply:
                    reply = "سأحوّلك مباشرة لأحد موظفينا — اضغط الزر أدناه لإرسال طلبك."

            ym = datetime.now(timezone.utc).strftime("%Y-%m")
            await database.website_projects.update_one(
                {"id": p["id"]},
                {"$inc": {f"chatbot_usage.{ym}.messages": 1, **({f"chatbot_usage.{ym}.handoffs": 1} if handoff else {})}},
            )
            # Log message for analytics (capped collection — keep last 500/project)
            try:
                await database.chatbot_messages.insert_one({
                    "id": str(uuid.uuid4()),
                    "project_id": p["id"],
                    "session_id": session_id,
                    "user_text": text[:500],
                    "reply_text": (reply or "")[:500] if isinstance(reply, str) else "",
                    "handoff": bool(handoff),
                    "at": _iso_now(),
                })
                # Trim oldest beyond 500
                count = await database.chatbot_messages.count_documents({"project_id": p["id"]})
                if count > 500:
                    excess = count - 500
                    olds = await database.chatbot_messages.find(
                        {"project_id": p["id"]}, {"_id": 1}
                    ).sort("at", 1).limit(excess).to_list(excess)
                    if olds:
                        await database.chatbot_messages.delete_many({"_id": {"$in": [o["_id"] for o in olds]}})
            except Exception as _le:
                log.debug("chatbot log failed: %s", _le)
            return {"reply": reply, "session_id": session_id, "handoff": handoff}
        except Exception as e:
            raise HTTPException(500, f"AI error: {str(e)[:200]}")

    # ── Public: handoff to a human (creates a support ticket on the project) ──
    class HandoffIn(BaseModel):
        session_id: Optional[str] = None
        name: Optional[str] = None
        contact: Optional[str] = None  # phone/whatsapp/email
        message: Optional[str] = None
        transcript: Optional[list] = None  # [{role, text}]

    @r.post("/public/{slug}/chatbot/handoff")
    async def _public_handoff(slug: str, body: HandoffIn):
        p = await database.website_projects.find_one(
            {"slug": slug, "status": "approved"},
            {"_id": 0, "id": 1, "name": 1, "support_tickets": 1, "chatbot_config": 1},
        )
        if not p:
            raise HTTPException(404, "غير موجود")

        # Compose a readable transcript
        lines = []
        for m in (body.transcript or [])[-30:]:
            role = "زبون" if (m.get("role") == "user") else "مساعد"
            txt = str(m.get("text", ""))[:600]
            lines.append(f"{role}: {txt}")
        transcript_txt = "\n".join(lines) or "(لا يوجد سجل محادثة)"

        subject = (body.message or "طلب تواصل من المساعد الذكي")[:200]
        description = (
            f"📞 الاسم: {body.name or '(مجهول)'}\n"
            f"📲 وسيلة التواصل: {body.contact or '(لم يُذكر)'}\n"
            f"🗒️ ملاحظات الزبون: {body.message or '(لا توجد)'}\n\n"
            f"=== سجل المحادثة ===\n{transcript_txt}"
        )[:4000]

        # 🆕 Generate WhatsApp deep-links
        import urllib.parse as _up
        store = p.get("name") or "متجركم"
        cfg_now = p.get("chatbot_config") or {}
        owner_phone = (cfg_now.get("notify_whatsapp") or "").strip()

        # Link 1 (for OWNER): pre-filled message reminding him a customer needs help
        owner_msg = (
            f"🔔 طلب تواصل جديد على متجر {store}\n\n"
            f"العميل: {body.name or 'مجهول'}\n"
            f"التواصل: {body.contact or 'لم يُذكر'}\n"
            f"الملاحظة: {body.message or 'لا توجد'}\n\n"
            "افتح لوحة التحكم للرد عبر تذكرة الدعم."
        )
        owner_wa_link = ""
        if owner_phone:
            digits = "".join(ch for ch in owner_phone if ch.isdigit())
            owner_wa_link = f"https://wa.me/{digits}?text={_up.quote(owner_msg)}"

        # Link 2 (for OWNER → CUSTOMER reply): if customer left a phone, prepare a wa.me link
        # the owner can click to start the conversation directly with them.
        reply_to_customer_link = ""
        cust_contact = (body.contact or "").strip()
        if cust_contact and any(ch.isdigit() for ch in cust_contact):
            cdigits = "".join(ch for ch in cust_contact if ch.isdigit())
            if len(cdigits) >= 8:
                reply_msg = f"مرحباً {body.name or ''}! تواصلنا معك ردّاً على استفسارك في {store}. كيف يمكننا خدمتك؟"
                reply_to_customer_link = f"https://wa.me/{cdigits}?text={_up.quote(reply_msg)}"

        import uuid as _uuid
        ticket = {
            "id": str(_uuid.uuid4()),
            "at": _iso_now(),
            "subject": subject,
            "description": description,
            "category": "chatbot_handoff",
            "status": "open",
            "source": "chatbot",
            "customer": {
                "name": (body.name or "")[:80],
                "contact": (body.contact or "")[:80],
                "session_id": body.session_id or "",
            },
            "whatsapp": {
                "owner_alert_link": owner_wa_link,
                "reply_to_customer_link": reply_to_customer_link,
            },
        }
        await database.website_projects.update_one(
            {"id": p["id"]},
            {"$push": {"support_tickets": ticket}, "$set": {"updated_at": _iso_now()}},
        )
        return {
            "ok": True,
            "ticket_id": ticket["id"],
            "owner_notified": bool(owner_wa_link),
        }

    return r


# ── Owner / Client config endpoints — both routes mounted on main websites router ──
class ChatbotCfg(BaseModel):
    enabled: Optional[bool] = None
    welcome_message: Optional[str] = None
    business_hours: Optional[str] = None
    extra_context: Optional[str] = None
    notify_whatsapp: Optional[str] = None  # owner's WhatsApp phone for handoff alerts


_ALLOWED_CFG_KEYS = ("enabled", "welcome_message", "business_hours", "extra_context", "notify_whatsapp")


def register_owner_endpoints(r: APIRouter, database, auth_dep, resolve_client=None):
    """Mount owner + client config endpoints on the main websites router."""
    from fastapi import Header as _Header

    @r.get("/projects/{project_id}/chatbot/config")
    async def _cfg_get(project_id: str, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]},
            {"_id": 0, "chatbot_config": 1, "chatbot_usage": 1, "name": 1},
        )
        if not p:
            raise HTTPException(404, "Not found")
        cfg = dict(p.get("chatbot_config") or {})
        cfg["usage"] = p.get("chatbot_usage") or {}
        return cfg

    @r.put("/projects/{project_id}/chatbot/config")
    async def _cfg_put(project_id: str, body: ChatbotCfg, current_user: dict = Depends(auth_dep)):
        p = await database.website_projects.find_one(
            {"id": project_id, "user_id": current_user["user_id"]}, {"_id": 0, "id": 1}
        )
        if not p:
            raise HTTPException(404, "Not found")
        patch: Dict[str, Any] = {}
        for k in _ALLOWED_CFG_KEYS:
            v = getattr(body, k)
            if v is not None:
                patch[f"chatbot_config.{k}"] = v
        if patch:
            patch["updated_at"] = _iso_now()
            await database.website_projects.update_one({"id": project_id}, {"$set": patch})
        fresh = await database.website_projects.find_one({"id": project_id}, {"_id": 0, "chatbot_config": 1})
        return (fresh or {}).get("chatbot_config") or {}

    # ── Client-side endpoints (use client session token) ──
    if resolve_client is None:
        return

    @r.get("/client/chatbot/config")
    async def _client_cfg_get(authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        cfg = dict(p.get("chatbot_config") or {})
        cfg["usage"] = p.get("chatbot_usage") or {}
        return cfg

    @r.put("/client/chatbot/config")
    async def _client_cfg_put(body: ChatbotCfg, authorization: str = _Header(None)):
        p = await resolve_client(authorization or "")
        patch: Dict[str, Any] = {}
        for k in _ALLOWED_CFG_KEYS:
            v = getattr(body, k)
            if v is not None:
                patch[f"chatbot_config.{k}"] = v
        if patch:
            patch["updated_at"] = _iso_now()
            await database.website_projects.update_one({"id": p["id"]}, {"$set": patch})
        fresh = await database.website_projects.find_one({"id": p["id"]}, {"_id": 0, "chatbot_config": 1})
        return (fresh or {}).get("chatbot_config") or {}

    # 🆕 Conversation Analytics — gives owner insight on what customers ask + handoff rate
    @r.get("/client/chatbot/analytics")
    async def _client_analytics(authorization: str = _Header(None), days: int = 30):
        p = await resolve_client(authorization or "")
        from datetime import timedelta
        since = (datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 365)))).isoformat()
        cur = database.chatbot_messages.find(
            {"project_id": p["id"], "at": {"$gte": since}},
            {"_id": 0, "user_text": 1, "handoff": 1, "session_id": 1, "at": 1},
        ).sort("at", -1).limit(500)
        msgs = await cur.to_list(500)

        total = len(msgs)
        handoffs = sum(1 for m in msgs if m.get("handoff"))
        sessions = len({m.get("session_id") for m in msgs if m.get("session_id")})

        # Topic detection by keyword presence (simple, fast, deterministic)
        topics = {
            "💰 الأسعار": ["سعر", "كم", "تكلفة", "رخيص", "غالي"],
            "🚚 الشحن": ["شحن", "توصيل", "متى يوصل", "أيام التوصيل", "كم يوم"],
            "🕐 ساعات العمل": ["ساعات", "متى تفتحون", "متى تسكرون", "دوام", "وقت العمل"],
            "📦 المنتجات": ["منتج", "متوفر", "موجود", "عندكم", "تبيعون"],
            "🎟️ خصومات": ["خصم", "كوبون", "تخفيض", "عرض", "كود"],
            "💳 الدفع": ["دفع", "بطاقة", "كاش", "تحويل", "stc", "مدى"],
            "📞 تواصل": ["تواصل", "رقم", "اتصال", "موظف", "خدمة العملاء"],
            "↩️ استرجاع": ["ارجاع", "استرجاع", "شكوى", "استبدال"],
        }
        topic_counts = {k: 0 for k in topics}
        for m in msgs:
            t = (m.get("user_text") or "").lower()
            for label, kws in topics.items():
                if any(kw in t for kw in kws):
                    topic_counts[label] += 1

        # Top "lost" (likely unanswered) questions = those that triggered handoff
        lost = [{"text": m.get("user_text") or "", "at": m.get("at")}
                for m in msgs if m.get("handoff")][:20]
        recent = [{"text": m.get("user_text") or "", "at": m.get("at"), "handoff": bool(m.get("handoff"))}
                  for m in msgs[:20]]

        return {
            "totals": {
                "messages": total,
                "handoffs": handoffs,
                "handoff_rate_pct": round((handoffs / total * 100) if total else 0, 1),
                "unique_sessions": sessions,
            },
            "topics": [{"label": k, "count": v} for k, v in
                       sorted(topic_counts.items(), key=lambda kv: -kv[1])],
            "lost_questions": lost,
            "recent": recent,
            "window_days": days,
        }
