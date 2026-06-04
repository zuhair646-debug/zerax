"""Channel connectors — Telegram / Discord / Email (Resend) / Twitter / WhatsApp.

Each connector exposes:
  - publish(text, image_url) → returns external_id
  - reply(to_user, text) → respond to inbound message
  - is_configured() → bool

Missing credentials raise a clear ValueError so the UI knows what to ask for.
"""
import os
import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger("zitex.marketing.connectors")


# ─── Telegram ─────────────────────────────────────────────
async def telegram_publish(text: str, image_url: Optional[str] = None, channel_id: Optional[str] = None) -> Dict[str, Any]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = channel_id or os.environ.get("TELEGRAM_CHANNEL_ID")
    if not token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN + TELEGRAM_CHANNEL_ID required. Get token from @BotFather.")
    base = f"https://api.telegram.org/bot{token}"
    async with httpx.AsyncClient(timeout=30) as client:
        if image_url:
            # Telegram needs absolute URL or upload; build absolute from backend
            if image_url.startswith("/"):
                public = os.environ.get("PUBLIC_BASE_URL", "https://zitex-production.up.railway.app")
                image_url = public.rstrip("/") + image_url
            r = await client.post(f"{base}/sendPhoto", data={
                "chat_id": chat_id, "caption": text[:1024], "photo": image_url, "parse_mode": "HTML",
            })
        else:
            r = await client.post(f"{base}/sendMessage", data={
                "chat_id": chat_id, "text": text, "parse_mode": "HTML",
            })
        r.raise_for_status()
        data = r.json()
        return {"ok": True, "message_id": data.get("result", {}).get("message_id"), "platform": "telegram"}


def telegram_is_configured() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN")) and bool(os.environ.get("TELEGRAM_CHANNEL_ID"))


# ─── Discord (webhook based — simplest) ─────────────────────
async def discord_publish(text: str, image_url: Optional[str] = None) -> Dict[str, Any]:
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        raise ValueError("DISCORD_WEBHOOK_URL required. Server Settings → Integrations → Create Webhook.")
    payload: Dict[str, Any] = {"content": text[:2000], "username": "Zitex AI"}
    if image_url:
        if image_url.startswith("/"):
            public = os.environ.get("PUBLIC_BASE_URL", "https://zitex-production.up.railway.app")
            image_url = public.rstrip("/") + image_url
        payload["embeds"] = [{"image": {"url": image_url}}]
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(webhook, json=payload)
        r.raise_for_status()
        return {"ok": True, "platform": "discord"}


def discord_is_configured() -> bool:
    return bool(os.environ.get("DISCORD_WEBHOOK_URL"))


# ─── Email (Resend) ─────────────────────────────────────────
async def email_publish(text: str, subject: str = "Zitex — جديد!", to_list: Optional[list] = None, image_url: Optional[str] = None) -> Dict[str, Any]:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise ValueError("RESEND_API_KEY required from resend.com.")
    sender = os.environ.get("RESEND_FROM", "Zitex <noreply@zitex.com>")
    recipients = to_list or []
    if not recipients:
        # fallback to a configured newsletter list
        nl = os.environ.get("MARKETING_NEWSLETTER_LIST", "")
        recipients = [e.strip() for e in nl.split(",") if e.strip()]
    if not recipients:
        raise ValueError("No recipients. Set MARKETING_NEWSLETTER_LIST env or pass to_list.")

    img_html = ""
    if image_url:
        if image_url.startswith("/"):
            public = os.environ.get("PUBLIC_BASE_URL", "https://zitex-production.up.railway.app")
            image_url = public.rstrip("/") + image_url
        img_html = f'<img src="{image_url}" style="max-width:100%;border-radius:12px;margin:16px 0"/>'
    html = f'<div dir="rtl" style="font-family:system-ui;line-height:1.7;color:#1a1a1a">{img_html}<div style="white-space:pre-wrap">{text}</div><div style="margin-top:24px;padding-top:16px;border-top:1px solid #eee;font-size:12px;color:#888">للإيقاف اضغط <a href="https://zitex.com/unsubscribe">هنا</a></div></div>'

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"from": sender, "to": recipients, "subject": subject, "html": html},
        )
        r.raise_for_status()
        return {"ok": True, "platform": "email", "sent_to": len(recipients), "id": r.json().get("id")}


def email_is_configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY"))


# ─── Twitter / X (v2) ───────────────────────────────────────
async def twitter_publish(text: str, image_url: Optional[str] = None) -> Dict[str, Any]:
    bearer = os.environ.get("TWITTER_BEARER_TOKEN")
    if not bearer:
        raise ValueError("TWITTER_BEARER_TOKEN required from developer.twitter.com (Basic plan $100/mo).")
    # Note: media upload on v2 requires OAuth 1.0a with separate keys; for now post text-only via v2.
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.twitter.com/2/tweets",
            headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"},
            json={"text": text[:280]},
        )
        if r.status_code >= 400:
            raise RuntimeError(f"Twitter API error {r.status_code}: {r.text[:200]}")
        return {"ok": True, "platform": "twitter", "id": r.json().get("data", {}).get("id")}


def twitter_is_configured() -> bool:
    return bool(os.environ.get("TWITTER_BEARER_TOKEN"))


# ─── WhatsApp (Twilio) ──────────────────────────────────────
async def whatsapp_publish(text: str, to_number: str) -> Dict[str, Any]:
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth = os.environ.get("TWILIO_AUTH_TOKEN")
    wa_from = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")  # sandbox default
    if not sid or not auth:
        raise ValueError("TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN required from twilio.com.")
    async with httpx.AsyncClient(timeout=30, auth=(sid, auth)) as client:
        r = await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            data={"From": wa_from, "To": f"whatsapp:{to_number}", "Body": text[:1024]},
        )
        if r.status_code >= 400:
            raise RuntimeError(f"Twilio WA error {r.status_code}: {r.text[:200]}")
        return {"ok": True, "platform": "whatsapp", "sid": r.json().get("sid")}


def whatsapp_is_configured() -> bool:
    return bool(os.environ.get("TWILIO_ACCOUNT_SID")) and bool(os.environ.get("TWILIO_AUTH_TOKEN"))


# ─── Instagram Business (Graph API) ─────────────────────────
async def instagram_publish(text: str, image_url: str) -> Dict[str, Any]:
    """Instagram Graph API requires a public image URL — text-only posts not supported."""
    access = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    ig_id = os.environ.get("INSTAGRAM_BUSINESS_ID")
    if not access or not ig_id:
        raise ValueError("INSTAGRAM_ACCESS_TOKEN + INSTAGRAM_BUSINESS_ID required (Business account + Meta App).")
    if not image_url:
        raise ValueError("Instagram requires an image URL.")
    if image_url.startswith("/"):
        public = os.environ.get("PUBLIC_BASE_URL", "https://zitex-production.up.railway.app")
        image_url = public.rstrip("/") + image_url

    async with httpx.AsyncClient(timeout=60) as client:
        # 1. Create media container
        r1 = await client.post(
            f"https://graph.facebook.com/v18.0/{ig_id}/media",
            params={"image_url": image_url, "caption": text[:2200], "access_token": access},
        )
        r1.raise_for_status()
        container = r1.json().get("id")
        # 2. Publish
        r2 = await client.post(
            f"https://graph.facebook.com/v18.0/{ig_id}/media_publish",
            params={"creation_id": container, "access_token": access},
        )
        r2.raise_for_status()
        return {"ok": True, "platform": "instagram", "id": r2.json().get("id")}


def instagram_is_configured() -> bool:
    return bool(os.environ.get("INSTAGRAM_ACCESS_TOKEN")) and bool(os.environ.get("INSTAGRAM_BUSINESS_ID"))


# ─── Registry ───────────────────────────────────────────────
CONNECTORS = {
    "telegram": {
        "publish": telegram_publish,
        "is_configured": telegram_is_configured,
        "label": "Telegram",
        "icon": "send",
        "color": "#26A5E4",
        "cost": "مجاني",
        "needs_image": False,
        "setup_steps": [
            "افتح @BotFather في Telegram",
            "أرسل /newbot ثم سمّ البوت ZitexBot",
            "احفظ الـ Token الذي يعطيك إياه",
            "أنشئ قناة عامة @zitexai واجعل البوت admin فيها",
            "أضف TELEGRAM_BOT_TOKEN و TELEGRAM_CHANNEL_ID لـ Railway env",
        ],
    },
    "discord": {
        "publish": discord_publish,
        "is_configured": discord_is_configured,
        "label": "Discord",
        "icon": "message-circle",
        "color": "#5865F2",
        "cost": "مجاني",
        "needs_image": False,
        "setup_steps": [
            "افتح سيرفر Discord الخاص بك",
            "Server Settings → Integrations → Webhooks",
            "Create Webhook → اختر القناة → انسخ الـ URL",
            "أضف DISCORD_WEBHOOK_URL لـ Railway env",
        ],
    },
    "email": {
        "publish": email_publish,
        "is_configured": email_is_configured,
        "label": "البريد الإلكتروني",
        "icon": "mail",
        "color": "#EA580C",
        "cost": "مجاني حتى 3000 إيميل/شهر",
        "needs_image": False,
        "setup_steps": [
            "RESEND_API_KEY متوفر بالفعل ✅",
            "أضف MARKETING_NEWSLETTER_LIST قائمة بريد مفصولة بفاصلة",
        ],
    },
    "twitter": {
        "publish": twitter_publish,
        "is_configured": twitter_is_configured,
        "label": "Twitter / X",
        "icon": "twitter",
        "color": "#1DA1F2",
        "cost": "$100/شهر (Basic plan)",
        "needs_image": False,
        "setup_steps": [
            "اشترك بـ Twitter Developer Basic plan",
            "أنشئ App → احصل على Bearer Token",
            "أضف TWITTER_BEARER_TOKEN لـ Railway env",
        ],
    },
    "whatsapp": {
        "publish": whatsapp_publish,
        "is_configured": whatsapp_is_configured,
        "label": "WhatsApp",
        "icon": "phone",
        "color": "#25D366",
        "cost": "Twilio Sandbox مجاني، Production ~$0.005/رسالة",
        "needs_image": False,
        "setup_steps": [
            "افتح حساب على twilio.com",
            "Activate WhatsApp Sandbox (مجاني للتجربة)",
            "انسخ Account SID و Auth Token",
            "أضفهم لـ Railway env",
        ],
    },
    "instagram": {
        "publish": instagram_publish,
        "is_configured": instagram_is_configured,
        "label": "Instagram",
        "icon": "instagram",
        "color": "#E1306C",
        "cost": "مجاني (يحتاج Business account)",
        "needs_image": True,
        "setup_steps": [
            "حوّل حساب Instagram لـ Business Account",
            "اربطه بـ Facebook Page",
            "أنشئ Meta App على developers.facebook.com",
            "احصل على Long-Lived Access Token + Business Account ID",
            "أضفهم لـ Railway env",
        ],
    },
}


def get_all_status() -> Dict[str, Any]:
    return {
        name: {
            "label": meta["label"],
            "icon": meta["icon"],
            "color": meta["color"],
            "cost": meta["cost"],
            "configured": meta["is_configured"](),
            "needs_image": meta["needs_image"],
            "setup_steps": meta["setup_steps"],
        }
        for name, meta in CONNECTORS.items()
    }


async def publish_to(channel: str, post: Dict[str, Any]) -> Dict[str, Any]:
    if channel not in CONNECTORS:
        raise ValueError(f"Unknown channel: {channel}")
    fn = CONNECTORS[channel]["publish"]
    text = post.get("text", "")
    img = post.get("image_url")
    if channel == "instagram" and not img:
        raise ValueError("Instagram requires an image — please regenerate with image enabled.")
    # Channels with different signatures
    if channel == "whatsapp":
        # need to_number — extract from post or use default test
        to = post.get("to_number") or os.environ.get("MARKETING_WHATSAPP_TEST")
        if not to:
            raise ValueError("MARKETING_WHATSAPP_TEST or post.to_number required for WhatsApp")
        return await fn(text, to)
    if channel == "email":
        return await fn(text, subject=post.get("subject", f"Zitex — {post.get('topic','')}"), image_url=img)
    if channel == "instagram":
        return await fn(text, img)
    return await fn(text, img)
