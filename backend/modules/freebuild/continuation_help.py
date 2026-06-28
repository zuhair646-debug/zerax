"""Inline key-extraction help chat.

When a customer gets stuck pasting their provider key in the onboarding
wizard, they click the "أواجه مشكلة" button. That opens a tiny scoped
chat backed by this endpoint — a focused, provider-specific helper that
knows the exact UI flow for each of the 20 providers, can send image
references, and can ONLY discuss key-extraction (never executes tools,
never modifies code).

The chat is bounded by a per-provider FAQ + a strict system prompt that
forbids it from doing anything except guiding the user.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

logger = logging.getLogger("zenrex.continuation_help")
router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Quick FAQ shown immediately when the modal opens (before contacting AI).
# These are the 3 most common issues per provider — keeps users unstuck
# without burning AI tokens.
PROVIDER_HELP: Dict[str, Dict[str, Any]] = {
    "github": {
        "title_ar": "حلول سريعة لمشاكل GitHub Token",
        "direct_url": "https://github.com/settings/tokens/new",
        "image_hint": "/static/tutorials/github.html",
        "faq": [
            {"q": "ما ألقى Settings → Developer settings", "a": "اضغط على صورتك يمين فوق الصفحة → Settings → ثم انزل لتحت بالسايد بار اليسرى → Developer settings (آخر شي)"},
            {"q": "أي Scopes أختار؟", "a": "اختر: ✅ repo (كامل) ✅ workflow ✅ read:org. لا تختار 'admin' أو 'delete' للأمان."},
            {"q": "أنا في حساب Organization مو شخصي", "a": "تأكد إن الـ Organization مفعّل Personal Access Tokens (PAT). صاحب الـ org لازم يسمح فيها من Settings → Third-party access."},
            {"q": "نسخت التوكن وضاع", "a": "ولا مشكلة — احذف القديم من Settings → Tokens، واعمل واحد جديد فوراً. ما يظهر إلا مرة واحدة فقط."},
        ],
    },
    "gitlab": {
        "title_ar": "حلول سريعة لمشاكل GitLab Token",
        "direct_url": "https://gitlab.com/-/profile/personal_access_tokens",
        "image_hint": "/static/tutorials/gitlab.html",
        "faq": [
            {"q": "ما ألقى Personal Access Tokens", "a": "اضغط على صورتك يمين فوق → Edit profile → بعدها بالسايد بار اليسرى → Access Tokens"},
            {"q": "وش الـ Scopes المطلوبة؟", "a": "✅ api ✅ read_repository ✅ write_repository — هذي تكفي للاستنساخ والتعديل."},
            {"q": "GitLab Self-hosted (سيرفر خاص)", "a": "نفس الخطوات لكن من URL الـ GitLab الخاص فيك (مثل: gitlab.yourcompany.com/-/profile/personal_access_tokens)"},
        ],
    },
    "bitbucket": {
        "title_ar": "حلول سريعة لمشاكل Bitbucket App Password",
        "direct_url": "https://bitbucket.org/account/settings/app-passwords/",
        "image_hint": "/static/tutorials/bitbucket.html",
        "faq": [
            {"q": "ما عرفت أين App passwords", "a": "صورتك يمين فوق → Personal settings → بالسايد بار اليسرى → App passwords"},
            {"q": "وش الصلاحيات؟", "a": "✅ Repositories: Read + Write ✅ Pipelines: Read (اختياري). اكتب اسم 'Zenrex' عشان تميزه."},
        ],
    },
    "vercel": {
        "title_ar": "حلول سريعة لمشاكل Vercel Token",
        "direct_url": "https://vercel.com/account/tokens",
        "image_hint": "/static/tutorials/vercel.html",
        "faq": [
            {"q": "ما ألقى Tokens", "a": "صورتك يمين فوق → Account → بالسايد بار → Tokens"},
            {"q": "Team أو Personal؟", "a": "لو موقعك تحت Team — اختر الـ Team من القائمة. لو شخصي — اتركه Personal."},
            {"q": "Expiration وش أحط؟", "a": "1 Year موصى به. الـ Token يظل صالح طول هذي المدة بدون تجديد."},
        ],
    },
    "netlify": {
        "title_ar": "حلول سريعة لمشاكل Netlify Token",
        "direct_url": "https://app.netlify.com/user/applications#personal-access-tokens",
        "image_hint": "/static/tutorials/netlify.html",
        "faq": [
            {"q": "ما عرفت أين أحصّل التوكن", "a": "صورتك يمين فوق → User settings → بالسايد بار اليسرى → Applications → انزل لـ Personal access tokens"},
            {"q": "وش الـ Description؟", "a": "اكتب 'Zenrex Continuation' — هذا الاسم بس عشان تميّز التوكن لو بغيت تحذفه بعدين."},
        ],
    },
    "cloudflare_pages": {
        "title_ar": "حلول سريعة لمشاكل Cloudflare API Token",
        "direct_url": "https://dash.cloudflare.com/profile/api-tokens",
        "image_hint": "/static/tutorials/cloudflare_pages.html",
        "faq": [
            {"q": "Global API Key أو API Token؟", "a": "⚠️ مهم: استخدم API Token (مخصّص)، لا تستخدم Global API Key أبداً (خطر أمني)."},
            {"q": "أي Permissions أختار؟", "a": "Account → Cloudflare Pages → Edit. وإذا تبي تحدث DNS: Zone → DNS → Edit"},
        ],
    },
    "hetzner": {
        "title_ar": "حلول سريعة لمشاكل Hetzner API Token",
        "direct_url": "https://console.hetzner.cloud/",
        "image_hint": "/static/tutorials/hetzner.html",
        "faq": [
            {"q": "ما ألقى API Tokens", "a": "ادخل المشروع → بالسايد بار اليسرى → Security → API Tokens"},
            {"q": "Read أو Read & Write؟", "a": "Read & Write — عشان تقدر تنشر تحديثات على السيرفر."},
            {"q": "ضاع التوكن", "a": "اعمل واحد جديد. الـ Token يظهر مرة واحدة فقط، ما يقدر يعرضه أحد بعدها."},
        ],
    },
    "hostinger": {
        "title_ar": "حلول سريعة لمشاكل Hostinger FTP",
        "direct_url": "https://hpanel.hostinger.com/",
        "image_hint": "/static/tutorials/hostinger.html",
        "faq": [
            {"q": "ما ألقى FTP Accounts", "a": "ادخل hPanel → Hosting → اختر الموقع → بالسايد بار اليسرى → Files → FTP Accounts"},
            {"q": "وش الـ Host name؟", "a": "Hostinger يعطيك Host (مثل ftp.yourdomain.com) + Port (21). كلهم بصفحة FTP Accounts."},
        ],
    },
    "wordpress_com": {
        "title_ar": "حلول سريعة لمشاكل WordPress Application Password",
        "direct_url": "https://wordpress.com/me/security",
        "image_hint": "/static/tutorials/wordpress_com.html",
        "faq": [
            {"q": "ما ألقى Application Passwords", "a": "Profile → Security → انزل لتحت → Two-Step Authentication → Application Passwords (لازم 2FA مفعّل أولاً)"},
            {"q": "موقعي self-hosted (مو wordpress.com)", "a": "ادخل wp-admin → Users → Profile → انزل لتحت → Application Passwords. متاح من WordPress 5.6+"},
        ],
    },
    "other_hosting": {
        "title_ar": "حلول سريعة لـ cPanel/Plesk عام",
        "direct_url": "https://www.google.com/search?q=cPanel+FTP+account+create+tutorial",
        "image_hint": "/static/tutorials/other_hosting.html",
        "faq": [
            {"q": "ما ألقى cPanel", "a": "جرّب: yourdomain.com/cpanel أو yourdomain.com:2083. اسم المستخدم + كلمة السر بتجيك من مزوّد الاستضافة بالإيميل."},
            {"q": "FTP أو SFTP؟", "a": "SFTP أأمن (Port 22). لو مزوّدك ما يدعم، استخدم FTP (Port 21) — لكن لاتنسى تحط القاعدة في الـ allow list."},
        ],
    },
}


# Generic fallback for providers without a tailored FAQ
_GENERIC = {
    "title_ar": "حلول سريعة عامة",
    "direct_url": None,
    "image_hint": None,
    "faq": [
        {"q": "ما ألقى مكان إنشاء المفتاح", "a": "ابحث في إعدادات حسابك عن: API / Tokens / Developer / Access Keys / Personal Access Token"},
        {"q": "أنشأت المفتاح بس ضاع", "a": "احذفه واعمل واحد جديد. معظم المنصات تعرض المفتاح مرة واحدة فقط لأسباب أمنية."},
        {"q": "المفتاح يقول 'permission denied'", "a": "تأكد إن الـ Scopes/Permissions تشمل Read + Write للمستودع. كثير من المنصات تتطلب صلاحيات صريحة."},
    ],
}


@router.get("/continuation/help/{provider_id}")
async def get_provider_help(provider_id: str, user=Depends(lambda: None)):
    """Static FAQ + direct URL + image hint for a specific provider."""
    data = PROVIDER_HELP.get(provider_id) or _GENERIC.copy()
    return {"ok": True, "provider_id": provider_id, **data}


@router.post("/continuation/help/escalate")
async def escalate_to_engineer(payload: dict, request: Request):
    """Inject a primed help message into the project's chat history so the
    Engineering Manager AI takes over the help session with provider-aware
    context. The wizard temporarily unlocks the input field on the frontend
    so the customer can converse until they get their key."""
    from server import db, get_current_user  # type: ignore
    user = await get_current_user(request)
    pid = (payload.get("project_id") or "").strip()
    provider_id = (payload.get("provider_id") or "").strip()
    issue = (payload.get("issue") or "").strip()[:500]
    if not pid or not provider_id:
        raise HTTPException(status_code=400, detail="project_id + provider_id required")
    proj = await db.freebuild_projects.find_one(
        {"id": pid, "user_id": user["user_id"], "mode": "continuation"},
        {"_id": 0, "id": 1},
    )
    if proj is None:
        raise HTTPException(status_code=404, detail="not found")
    help_data = PROVIDER_HELP.get(provider_id) or _GENERIC
    prompt = (
        f"⚠️ **العميل عالق في خطوة استخراج مفتاح {provider_id}.**\n\n"
        f"المشكلة اللي وصفها: \"{issue or 'لم يحدد'}\"\n\n"
        f"🎯 **مهمتك الآن (وضع مساعدة فقط — لا تكتب كود، لا تستدعي أدوات):**\n"
        f"1. اسأل العميل ايش يشوف على شاشته الحالية\n"
        f"2. وجّهه خطوة بخطوة للوصول لـ: {help_data.get('direct_url', '(صفحة المفتاح)')}\n"
        f"3. لو حاب صور توضيحية، استخدم Markdown image syntax مع الـ links اللي معك\n"
        f"4. لا تنتقل لأي مهمة ثانية حتى يعطيك العميل المفتاح فعلياً\n\n"
        f"💡 **معلومات المزوّد:** {help_data.get('title_ar', '')}\n"
        f"الـ FAQ الأساسي: {', '.join(f.get('q', '') for f in help_data.get('faq', []))[:300]}"
    )
    await db.freebuild_projects.update_one(
        {"id": pid},
        {"$push": {"messages": {
            "role": "system",
            "content": prompt,
            "created_at": _now(),
            "kind": "help_escalation",
            "provider_id": provider_id,
        }},
         "$set": {
             "continuation_help_session": {
                 "active": True,
                 "provider_id": provider_id,
                 "issue": issue,
                 "started_at": _now(),
             },
             "updated_at": _now(),
         }},
    )
    return {
        "ok": True,
        "message": "تم فتح جلسة مساعدة مع المهندس. اكتب وصفك في الشات وهو سيرد عليك بإرشادات مخصّصة.",
        "unlock_chat_input": True,
    }


@router.post("/continuation/help/end")
async def end_help_session(payload: dict, request: Request):
    """Mark the help session as ended so the wizard can re-lock the chat
    input and resume the normal onboarding flow."""
    from server import db, get_current_user  # type: ignore
    user = await get_current_user(request)
    pid = (payload.get("project_id") or "").strip()
    if not pid:
        raise HTTPException(status_code=400, detail="project_id required")
    await db.freebuild_projects.update_one(
        {"id": pid, "user_id": user["user_id"]},
        {"$set": {"continuation_help_session.active": False, "updated_at": _now()}},
    )
    return {"ok": True}
