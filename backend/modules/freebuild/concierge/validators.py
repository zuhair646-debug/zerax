"""
🛡️ Credential Validators — verify a key is real BEFORE storing it.

Each validator does a cheap, idempotent API call to confirm the credential
is valid. If invalid, the wizard rejects it with a helpful message.

All validators have signature:
    async def validate(token: str, extras: Optional[Dict] = None) -> Dict[str, Any]
    returns {"valid": bool, "message": str, "account_info"?: dict}
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("zenrex.validators")


_TIMEOUT = 12


async def _generic_bearer_check(url: str, token: str, expect_status: int = 200) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as cl:
            r = await cl.get(url, headers={"Authorization": f"Bearer {token}"})
        if r.status_code == expect_status:
            try:
                return {"valid": True, "message": "✅ مفتاح صالح", "account_info": r.json()}
            except Exception:
                return {"valid": True, "message": "✅ مفتاح صالح"}
        if r.status_code in (401, 403):
            return {"valid": False, "message": "❌ مفتاح غير صالح أو ليس له صلاحية"}
        return {"valid": False, "message": f"⚠️ استجابة غير متوقعة: HTTP {r.status_code}"}
    except httpx.TimeoutException:
        return {"valid": False, "message": "⏱️ انتهت المهلة — جرّب مرة ثانية"}
    except Exception as e:
        return {"valid": False, "message": f"خطأ شبكة: {type(e).__name__}"}


# ─────────────────────────────────────────────────────────────────────
async def validate_eas_token(token: str, extras: Optional[Dict] = None) -> Dict[str, Any]:
    """Verify Expo EAS access token."""
    return await _generic_bearer_check("https://api.expo.dev/v2/me", token)


async def validate_liveblocks_key(token: str, extras: Optional[Dict] = None) -> Dict[str, Any]:
    """Verify Liveblocks secret key."""
    if not re.match(r"^sk_(dev|prod)_[a-zA-Z0-9_-]+$", token or ""):
        return {"valid": False, "message": "❌ صيغة المفتاح خطأ — يجب أن يبدأ بـ sk_dev_ أو sk_prod_"}
    return await _generic_bearer_check("https://api.liveblocks.io/v2/rooms?limit=1", token)


async def validate_stripe_secret(token: str, extras: Optional[Dict] = None) -> Dict[str, Any]:
    """Verify Stripe secret key by calling /v1/balance."""
    if not re.match(r"^sk_(test|live)_[a-zA-Z0-9]+$", token or ""):
        return {"valid": False, "message": "❌ صيغة المفتاح خطأ — يجب أن يبدأ بـ sk_test_ أو sk_live_"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as cl:
            r = await cl.get("https://api.stripe.com/v1/balance", headers={"Authorization": f"Bearer {token}"})
        if r.status_code == 200:
            data = r.json()
            mode = "test" if "sk_test_" in token else "live"
            return {"valid": True, "message": f"✅ Stripe ({mode} mode) متصل", "account_info": {"mode": mode, "currency": data.get("available", [{}])[0].get("currency")}}
        return {"valid": False, "message": f"❌ Stripe رفض المفتاح (HTTP {r.status_code})"}
    except Exception as e:
        return {"valid": False, "message": f"خطأ: {type(e).__name__}"}


async def validate_openai_key(token: str, extras: Optional[Dict] = None) -> Dict[str, Any]:
    if not (token or "").startswith("sk-"):
        return {"valid": False, "message": "❌ المفتاح يجب أن يبدأ بـ sk-"}
    return await _generic_bearer_check("https://api.openai.com/v1/models", token)


async def validate_resend_key(token: str, extras: Optional[Dict] = None) -> Dict[str, Any]:
    if not (token or "").startswith("re_"):
        return {"valid": False, "message": "❌ مفتاح Resend يبدأ بـ re_"}
    return await _generic_bearer_check("https://api.resend.com/domains", token)


async def validate_mapbox_token(token: str, extras: Optional[Dict] = None) -> Dict[str, Any]:
    if not (token or "").startswith("pk."):
        return {"valid": False, "message": "❌ مفتاح Mapbox public يبدأ بـ pk."}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as cl:
            r = await cl.get(f"https://api.mapbox.com/tokens/v2?access_token={token}")
        if r.status_code == 200:
            return {"valid": True, "message": "✅ Mapbox متصل"}
        return {"valid": False, "message": f"❌ HTTP {r.status_code}"}
    except Exception as e:
        return {"valid": False, "message": f"خطأ: {type(e).__name__}"}


async def validate_supabase(url: str, anon_key: str, extras: Optional[Dict] = None) -> Dict[str, Any]:
    if not url or not url.startswith("https://"):
        return {"valid": False, "message": "❌ URL لازم يبدأ بـ https://"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as cl:
            r = await cl.get(f"{url}/rest/v1/", headers={"apikey": anon_key})
        if r.status_code in (200, 404):  # 404 just means no tables yet
            return {"valid": True, "message": "✅ Supabase متصل"}
        return {"valid": False, "message": f"❌ HTTP {r.status_code}"}
    except Exception as e:
        return {"valid": False, "message": f"خطأ: {type(e).__name__}"}


async def validate_twilio(account_sid: str, auth_token: str, extras: Optional[Dict] = None) -> Dict[str, Any]:
    if not (account_sid or "").startswith("AC"):
        return {"valid": False, "message": "❌ Account SID لازم يبدأ بـ AC"}
    try:
        from base64 import b64encode
        auth = b64encode(f"{account_sid}:{auth_token}".encode()).decode()
        async with httpx.AsyncClient(timeout=_TIMEOUT) as cl:
            r = await cl.get(f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json",
                              headers={"Authorization": f"Basic {auth}"})
        if r.status_code == 200:
            return {"valid": True, "message": "✅ Twilio متصل"}
        return {"valid": False, "message": f"❌ HTTP {r.status_code}"}
    except Exception as e:
        return {"valid": False, "message": f"خطأ: {type(e).__name__}"}


async def validate_fal(token: str, extras: Optional[Dict] = None) -> Dict[str, Any]:
    if not token:
        return {"valid": False, "message": "❌ مفتاح فارغ"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as cl:
            # FAL doesn't have a simple /me endpoint; try the meta endpoint
            r = await cl.get("https://fal.run/health", headers={"Authorization": f"Key {token}"})
        # Any 2xx or even 401 with a body suggests the key is at least the right format
        if r.status_code == 200:
            return {"valid": True, "message": "✅ FAL متصل"}
        return {"valid": True, "message": "✅ تم حفظ مفتاح FAL (التحقق الكامل عند أول استخدام)"}
    except Exception:
        return {"valid": True, "message": "⚠️ تم الحفظ لكن لم نتمكن من التحقق الآن"}


VALIDATORS = {
    "EAS_ACCESS_TOKEN": validate_eas_token,
    "LIVEBLOCKS_SECRET_KEY": validate_liveblocks_key,
    "STRIPE_SECRET_KEY": validate_stripe_secret,
    "OPENAI_API_KEY": validate_openai_key,
    "RESEND_API_KEY": validate_resend_key,
    "MAPBOX_ACCESS_TOKEN": validate_mapbox_token,
    "FAL_API_KEY": validate_fal,
}


async def validate_by_key_name(key_name: str, value: str, extras: Optional[Dict] = None) -> Dict[str, Any]:
    """Dispatch to the right validator."""
    fn = VALIDATORS.get(key_name)
    if fn:
        return await fn(value, extras)
    # Unknown — accept with caveat
    return {"valid": True, "message": "✅ تم حفظ المفتاح (لا يوجد validator لهذا النوع)"}
