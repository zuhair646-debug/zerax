"""
API Keys Health Center — Owner-only
═══════════════════════════════════════════════════════════════════════════
ميزات:
  1. فحص الحالة: متصل / ناقص
  2. فحص الرصيد الحي عبر API كل مزود (لما يكون مدعوم)
  3. روابط دفع مباشرة لكل خدمة
  4. تنبيهات الرصيد المنخفض
  5. تصنيف بالأهمية: critical / high / medium / optional
"""
from __future__ import annotations

import os
import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
# كل الخدمات المعتمدة في زيتاكس مع روابط الدفع والشحن
# ════════════════════════════════════════════════════════════════════════
SERVICES: List[Dict[str, Any]] = [
    # ── Tier 1: LLM Essentials ───────────────────────────────────────
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "category": "llm",
        "priority": "critical",
        "tier": 1,
        "icon": "Cpu",
        "color": "amber",
        "purpose_ar": "أذكى موديل للبرمجة وAuto-Coder",
        "env_vars": ["ANTHROPIC_API_KEY"],
        "billing_url": "https://console.anthropic.com/settings/billing",
        "keys_url": "https://console.anthropic.com/settings/keys",
        "signup_url": "https://console.anthropic.com/login",
        "balance_check": "anthropic",
        "low_balance_threshold_usd": 10,
    },
    {
        "id": "openai",
        "name": "OpenAI (GPT-5.5 + Sora 2 + GPT Image)",
        "category": "llm",
        "priority": "critical",
        "tier": 1,
        "icon": "Sparkles",
        "color": "emerald",
        "purpose_ar": "الإبداع + Sora فيديو + GPT Image + Whisper",
        "env_vars": ["OPENAI_API_KEY", "OPENAI_DIRECT_KEY"],
        "billing_url": "https://platform.openai.com/settings/organization/billing/overview",
        "keys_url": "https://platform.openai.com/api-keys",
        "signup_url": "https://platform.openai.com/signup",
        "balance_check": "openai",
        "low_balance_threshold_usd": 10,
    },
    {
        "id": "gemini",
        "name": "Google Gemini (+ Nano Banana)",
        "category": "llm",
        "priority": "high",
        "tier": 1,
        "icon": "Sparkles",
        "color": "sky",
        "purpose_ar": "سياق طويل + تعديل صور بالذكاء (Nano Banana)",
        "env_vars": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "billing_url": "https://console.cloud.google.com/billing",
        "keys_url": "https://aistudio.google.com/app/apikey",
        "signup_url": "https://aistudio.google.com/",
        "balance_check": None,
        "free_tier_note": "مجاني للبداية بسخاء",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek V3 🇨🇳",
        "category": "llm",
        "priority": "medium",
        "tier": 2,
        "icon": "Sparkles",
        "color": "violet",
        "purpose_ar": "reasoning + برمجة بسعر منخفض",
        "env_vars": ["DEEPSEEK_API_KEY"],
        "billing_url": "https://platform.deepseek.com/usage",
        "keys_url": "https://platform.deepseek.com/api_keys",
        "signup_url": "https://platform.deepseek.com/sign_up",
        "balance_check": "deepseek",
        "low_balance_threshold_usd": 3,
    },
    {
        "id": "qwen",
        "name": "Alibaba Qwen 🇨🇳",
        "category": "llm",
        "priority": "medium",
        "tier": 2,
        "icon": "Sparkles",
        "color": "rose",
        "purpose_ar": "الأفضل في العربي السعودي",
        "env_vars": ["DASHSCOPE_API_KEY", "QWEN_API_KEY"],
        "billing_url": "https://dashscope.console.aliyun.com/billing",
        "keys_url": "https://dashscope.console.aliyun.com/apiKey",
        "signup_url": "https://dashscope.console.aliyun.com/",
        "balance_check": None,
    },
    {
        "id": "kimi",
        "name": "Moonshot Kimi K2 🇨🇳",
        "category": "llm",
        "priority": "medium",
        "tier": 2,
        "icon": "Sparkles",
        "color": "indigo",
        "purpose_ar": "سياق 200K + عربي طبيعي",
        "env_vars": ["MOONSHOT_API_KEY", "KIMI_API_KEY"],
        "billing_url": "https://platform.moonshot.cn/console/account",
        "keys_url": "https://platform.moonshot.cn/console/api-keys",
        "signup_url": "https://platform.moonshot.cn/",
        "balance_check": None,
    },
    {
        "id": "openrouter",
        "name": "OpenRouter (بوابة 100+ موديل)",
        "category": "llm",
        "priority": "medium",
        "tier": 2,
        "icon": "Sparkles",
        "color": "fuchsia",
        "purpose_ar": "بوابة موديلات بسعر أرخص + fallback",
        "env_vars": ["OPENROUTER_API_KEY"],
        "billing_url": "https://openrouter.ai/settings/credits",
        "keys_url": "https://openrouter.ai/keys",
        "signup_url": "https://openrouter.ai/",
        "balance_check": "openrouter",
        "low_balance_threshold_usd": 5,
    },

    # ── Tier 1: Media Essentials ─────────────────────────────────────
    {
        "id": "fal",
        "name": "Fal.ai (Flux + Veo 3 + Kling)",
        "category": "media",
        "priority": "critical",
        "tier": 1,
        "icon": "Image",
        "color": "amber",
        "purpose_ar": "كل الصور والفيديو الفاخرة (Flux Pro Ultra, Veo 3, Kling 2.1)",
        "env_vars": ["FAL_KEY", "FAL_API_KEY"],
        "billing_url": "https://fal.ai/dashboard/billing",
        "keys_url": "https://fal.ai/dashboard/keys",
        "signup_url": "https://fal.ai/dashboard",
        "balance_check": None,
        "balance_url_hint": "https://fal.ai/dashboard/billing",
    },
    {
        "id": "runway",
        "name": "Runway Gen-4",
        "category": "media",
        "priority": "high",
        "tier": 2,
        "icon": "Video",
        "color": "rose",
        "purpose_ar": "فيديو احترافي VFX + إخراج",
        "env_vars": ["RUNWAY_API_KEY"],
        "billing_url": "https://app.runwayml.com/account/usage",
        "keys_url": "https://app.runwayml.com/account/api-keys",
        "signup_url": "https://app.runwayml.com/signup",
        "balance_check": None,
    },
    {
        "id": "elevenlabs",
        "name": "ElevenLabs (الأصوات الطبيعية)",
        "category": "voice",
        "priority": "critical",
        "tier": 1,
        "icon": "Mic",
        "color": "sky",
        "purpose_ar": "لهجات عربية طبيعية + استنساخ صوت",
        "env_vars": ["ELEVENLABS_API_KEY"],
        "billing_url": "https://elevenlabs.io/app/subscription",
        "keys_url": "https://elevenlabs.io/app/settings/api-keys",
        "signup_url": "https://elevenlabs.io/sign-up",
        "balance_check": "elevenlabs",
        "low_balance_threshold_credits": 10000,
    },

    # ── Tier 1: Infrastructure (Production-grade) ────────────────────
    {
        "id": "sentry",
        "name": "Sentry (مراقبة الأخطاء)",
        "category": "infra",
        "priority": "critical",
        "tier": 1,
        "icon": "AlertTriangle",
        "color": "rose",
        "purpose_ar": "إشعار فوري لأي خطأ في الموقع قبل ما يشتكي العميل",
        "env_vars": ["SENTRY_DSN"],
        "billing_url": "https://sentry.io/settings/billing/",
        "keys_url": "https://sentry.io/settings/projects/",
        "signup_url": "https://sentry.io/signup/",
        "balance_check": None,
        "free_tier_note": "مجاني 5K أخطاء/شهر",
    },
    {
        "id": "cloudflare_r2",
        "name": "Cloudflare R2 (تخزين دائم)",
        "category": "infra",
        "priority": "critical",
        "tier": 1,
        "icon": "Database",
        "color": "amber",
        "purpose_ar": "حفظ دائم للصور والفيديوهات (10GB مجاناً)",
        "env_vars": ["R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET", "R2_PUBLIC_URL", "CLOUDFLARE_ACCOUNT_ID"],
        "billing_url": "https://dash.cloudflare.com/?to=/:account/billing",
        "keys_url": "https://dash.cloudflare.com/?to=/:account/r2/api-tokens",
        "signup_url": "https://dash.cloudflare.com/sign-up",
        "balance_check": None,
        "free_tier_note": "مجاني 10GB شهرياً",
    },
    {
        "id": "upstash",
        "name": "Upstash Redis (مهام الخلفية)",
        "category": "infra",
        "priority": "high",
        "tier": 1,
        "icon": "Layers",
        "color": "emerald",
        "purpose_ar": "تشغيل توليد الفيديو الطويل بدون انتظار في الواجهة",
        "env_vars": ["REDIS_URL", "UPSTASH_REDIS_URL"],
        "billing_url": "https://console.upstash.com/billing",
        "keys_url": "https://console.upstash.com/",
        "signup_url": "https://console.upstash.com/login",
        "balance_check": None,
        "free_tier_note": "مجاني 10K طلب يومياً",
    },
    {
        "id": "resend",
        "name": "Resend (إيميلات احترافية)",
        "category": "infra",
        "priority": "high",
        "tier": 2,
        "icon": "Mail",
        "color": "indigo",
        "purpose_ar": "إيميلات ترحيب + فواتير + استعادة كلمة سر",
        "env_vars": ["RESEND_API_KEY", "EMAIL_FROM"],
        "billing_url": "https://resend.com/settings/billing",
        "keys_url": "https://resend.com/api-keys",
        "signup_url": "https://resend.com/signup",
        "balance_check": None,
        "free_tier_note": "مجاني 3,000 إيميل/شهر",
    },
    {
        "id": "posthog",
        "name": "PostHog (تحليلات المستخدمين)",
        "category": "infra",
        "priority": "medium",
        "tier": 2,
        "icon": "TrendingUp",
        "color": "violet",
        "purpose_ar": "تشوف كل ضغطة عميل، تحسّن التحويل",
        "env_vars": ["POSTHOG_KEY", "POSTHOG_HOST"],
        "billing_url": "https://app.posthog.com/organization/billing",
        "keys_url": "https://app.posthog.com/project/settings",
        "signup_url": "https://app.posthog.com/signup",
        "balance_check": None,
        "free_tier_note": "مجاني 1M event/شهر",
    },

    # ── Tier 3: Future expansion ─────────────────────────────────────
    {
        "id": "pinecone",
        "name": "Pinecone (ذاكرة طويلة + RAG)",
        "category": "infra",
        "priority": "medium",
        "tier": 3,
        "icon": "Database",
        "color": "fuchsia",
        "purpose_ar": "بحث دلالي + ذاكرة طويلة المدى",
        "env_vars": ["PINECONE_API_KEY", "PINECONE_INDEX"],
        "billing_url": "https://app.pinecone.io/organizations/-/billing",
        "keys_url": "https://app.pinecone.io/",
        "signup_url": "https://app.pinecone.io/",
        "balance_check": None,
        "free_tier_note": "مجاني للبداية",
    },
    {
        "id": "livekit",
        "name": "LiveKit (محادثة صوتية لايف)",
        "category": "voice",
        "priority": "medium",
        "tier": 3,
        "icon": "Mic",
        "color": "sky",
        "purpose_ar": "محادثة صوتية حية مع AI",
        "env_vars": ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"],
        "billing_url": "https://cloud.livekit.io/projects",
        "keys_url": "https://cloud.livekit.io/projects",
        "signup_url": "https://cloud.livekit.io/",
        "balance_check": None,
        "free_tier_note": "مجاني للبداية",
    },
    {
        "id": "twilio",
        "name": "Twilio (SMS + WhatsApp)",
        "category": "infra",
        "priority": "optional",
        "tier": 3,
        "icon": "MessageSquare",
        "color": "rose",
        "purpose_ar": "OTP + إشعارات SMS + WhatsApp Business",
        "env_vars": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER"],
        "billing_url": "https://console.twilio.com/billing/billing-overview",
        "keys_url": "https://console.twilio.com/",
        "signup_url": "https://console.twilio.com/",
        "balance_check": "twilio",
        "low_balance_threshold_usd": 5,
    },
]


# ════════════════════════════════════════════════════════════════════════
# Balance checkers — live API calls to fetch real-time balance
# ════════════════════════════════════════════════════════════════════════
async def _check_anthropic_balance() -> Optional[Dict[str, Any]]:
    """Anthropic doesn't expose a public balance API. Return None — UI shows 'Open dashboard'."""
    return None


async def _check_openai_balance() -> Optional[Dict[str, Any]]:
    """OpenAI removed public balance endpoint in 2024. Return None."""
    return None


async def _check_deepseek_balance() -> Optional[Dict[str, Any]]:
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        return None
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.get("https://api.deepseek.com/user/balance",
                            headers={"Authorization": f"Bearer {key}"})
            if r.status_code != 200:
                return None
            data = r.json()
            infos = data.get("balance_infos") or []
            if infos:
                usd_info = next((b for b in infos if b.get("currency") == "USD"), infos[0])
                return {
                    "balance": float(usd_info.get("total_balance", 0)),
                    "currency": usd_info.get("currency", "USD"),
                    "is_available": data.get("is_available", False),
                }
    except Exception as e:
        logger.debug(f"deepseek balance check failed: {e}")
    return None


async def _check_openrouter_balance() -> Optional[Dict[str, Any]]:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return None
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.get("https://openrouter.ai/api/v1/key",
                            headers={"Authorization": f"Bearer {key}"})
            if r.status_code != 200:
                return None
            data = (r.json() or {}).get("data") or {}
            usage = float(data.get("usage", 0))
            limit = data.get("limit")
            if limit is not None:
                remaining = max(0.0, float(limit) - usage)
                return {"balance": remaining, "used": usage, "limit": float(limit), "currency": "USD"}
            return {"used": usage, "currency": "USD"}
    except Exception as e:
        logger.debug(f"openrouter balance check failed: {e}")
    return None


async def _check_elevenlabs_balance() -> Optional[Dict[str, Any]]:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        return None
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.get("https://api.elevenlabs.io/v1/user/subscription",
                            headers={"xi-api-key": key})
            if r.status_code == 200:
                data = r.json()
                used = int(data.get("character_count", 0))
                limit = int(data.get("character_limit", 0))
                remaining = max(0, limit - used)
                return {
                    "credits_remaining": remaining,
                    "credits_used": used,
                    "credits_limit": limit,
                    "tier": data.get("tier", "unknown"),
                }
            # Key works for TTS but lacks "user_read" — verify by hitting TTS endpoint
            if r.status_code == 401:
                # Probe TTS endpoint with a tiny generation to confirm it can produce audio
                probe = await c.post(
                    "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM",
                    headers={"xi-api-key": key, "Content-Type": "application/json"},
                    json={"text": ".", "model_id": "eleven_multilingual_v2"},
                )
                if probe.status_code == 200:
                    return {
                        "tier": "active",
                        "tts_works": True,
                        "note_ar": "المفتاح يعمل للتوليد. لا يدعم قراءة الرصيد (صلاحيات مقيّدة).",
                    }
    except Exception as e:
        logger.debug(f"elevenlabs balance check failed: {e}")
    return None


async def _check_twilio_balance() -> Optional[Dict[str, Any]]:
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    tok = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    if not (sid and tok):
        return None
    try:
        async with httpx.AsyncClient(timeout=8.0, auth=(sid, tok)) as c:
            r = await c.get(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Balance.json")
            if r.status_code != 200:
                return None
            data = r.json()
            return {"balance": float(data.get("balance", 0)),
                    "currency": data.get("currency", "USD")}
    except Exception as e:
        logger.debug(f"twilio balance check failed: {e}")
    return None


BALANCE_CHECKERS = {
    "anthropic":  _check_anthropic_balance,
    "openai":     _check_openai_balance,
    "deepseek":   _check_deepseek_balance,
    "openrouter": _check_openrouter_balance,
    "elevenlabs": _check_elevenlabs_balance,
    "twilio":     _check_twilio_balance,
}


def _mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 10:
        return "***"
    return value[:4] + "..." + value[-4:]


def _service_state(svc: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve current env state of a service."""
    env_vars = svc.get("env_vars", [])
    configured: List[Dict[str, Any]] = []
    missing: List[str] = []
    primary_set = False
    for ev in env_vars:
        val = os.environ.get(ev, "").strip()
        if val:
            configured.append({"env": ev, "preview": _mask_key(val)})
            primary_set = True
        else:
            missing.append(ev)

    # For services with alternative envs (OPENAI_API_KEY OR OPENAI_DIRECT_KEY),
    # primary_set being true on any means it's available.
    total = len(env_vars)
    is_complete = len(configured) == total
    is_partial = primary_set and not is_complete

    return {
        "configured_count": len(configured),
        "total_env_vars": total,
        "configured_envs": configured,
        "missing_envs": missing,
        "is_complete": is_complete,
        "is_partial": is_partial,
        "is_available": primary_set,
    }


async def get_services_status() -> Dict[str, Any]:
    """Return full status with live balances (parallel checks)."""
    # Start all balance checks in parallel
    balance_tasks = {}
    for svc in SERVICES:
        bc = svc.get("balance_check")
        if bc and bc in BALANCE_CHECKERS:
            balance_tasks[svc["id"]] = asyncio.create_task(BALANCE_CHECKERS[bc]())

    # Resolve balances
    balances: Dict[str, Optional[Dict[str, Any]]] = {}
    for sid, task in balance_tasks.items():
        try:
            balances[sid] = await asyncio.wait_for(task, timeout=10.0)
        except Exception:
            balances[sid] = None

    services_out = []
    summary = {"critical_missing": 0, "high_missing": 0, "low_balance": 0,
               "configured": 0, "total": len(SERVICES)}
    for svc in SERVICES:
        state = _service_state(svc)
        balance = balances.get(svc["id"])

        # Detect low balance
        low_balance = False
        threshold_usd = svc.get("low_balance_threshold_usd")
        threshold_credits = svc.get("low_balance_threshold_credits")
        if balance and threshold_usd is not None:
            b = balance.get("balance")
            if b is not None and b < threshold_usd:
                low_balance = True
                summary["low_balance"] += 1
        elif balance and threshold_credits is not None:
            c = balance.get("credits_remaining")
            if c is not None and c < threshold_credits:
                low_balance = True
                summary["low_balance"] += 1

        # Status traffic light
        if not state["is_available"]:
            if svc["priority"] == "critical":
                light = "red"
                summary["critical_missing"] += 1
            elif svc["priority"] == "high":
                light = "orange"
                summary["high_missing"] += 1
            else:
                light = "gray"
        elif low_balance:
            light = "yellow"
        elif state["is_partial"]:
            light = "orange"
        else:
            light = "green"
            summary["configured"] += 1

        services_out.append({
            **svc,
            **state,
            "balance": balance,
            "low_balance": low_balance,
            "status_light": light,
        })

    # Sort: red/orange first, then yellow, then green
    light_order = {"red": 0, "orange": 1, "yellow": 2, "gray": 3, "green": 4}
    services_out.sort(key=lambda x: (light_order.get(x["status_light"], 5), x["tier"], x["name"]))

    return {
        "services": services_out,
        "summary": summary,
        "categories": ["llm", "media", "voice", "infra"],
    }


# ════════════════════════════════════════════════════════════════════════
# Router factory
# ════════════════════════════════════════════════════════════════════════
def create_keys_router(db, get_current_user, require_owner) -> APIRouter:
    router = APIRouter(prefix="/api/owner/keys", tags=["api-keys"])

    @router.get("/status")
    async def status(owner=Depends(require_owner)):
        return await get_services_status()

    @router.get("/services")
    async def services_list(owner=Depends(require_owner)):
        return {"services": SERVICES}

    @router.post("/refresh-balance/{service_id}")
    async def refresh_balance(service_id: str, owner=Depends(require_owner)):
        svc = next((s for s in SERVICES if s["id"] == service_id), None)
        if not svc:
            raise HTTPException(404, "service not found")
        bc = svc.get("balance_check")
        if not bc or bc not in BALANCE_CHECKERS:
            return {"service_id": service_id, "balance": None,
                    "message": "هذا المزود لا يدعم فحص الرصيد المباشر. افتح dashboard للتحقق."}
        balance = await BALANCE_CHECKERS[bc]()
        return {"service_id": service_id, "balance": balance}

    return router
