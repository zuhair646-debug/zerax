"""
Independence Status — owner-only dashboard showing which API keys are
configured for direct (independent) use vs falling back to Emergent.

Endpoint: GET /api/admin/independence-status
"""
from __future__ import annotations
import os
from typing import Any, Dict, List
from fastapi import APIRouter, Depends


def _check(env_name: str, prefix: str = "") -> Dict[str, Any]:
    val = os.environ.get(env_name, "").strip()
    is_set = bool(val)
    is_valid = is_set and (not prefix or val.startswith(prefix))
    return {
        "set": is_set,
        "valid_format": is_valid,
        "preview": (val[:8] + "..." + val[-4:]) if is_set and len(val) > 14 else ("***" if is_set else None),
    }


# Catalog of every integration. Each entry describes:
#   - what it powers, who provides it, where to get the key,
#   - direct console URL, pricing note, and the env var name(s).
INTEGRATIONS = [
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "name_ar": "كلود (Claude Sonnet 4.5)",
        "powers_ar": "برمجة زيتاكس + الذكاء الرئيسي (Claude path)",
        "env_var": "ANTHROPIC_API_KEY",
        "key_prefix": "sk-ant",
        "console_url": "https://console.anthropic.com/settings/keys",
        "signup_url": "https://console.anthropic.com",
        "pricing_url": "https://www.anthropic.com/pricing",
        "pricing_note_ar": "$3/1M input · $15/1M output (محادثة عادية ≈ سنت)",
        "fallback_env": "EMERGENT_LLM_KEY",
        "fallback_label_ar": "يستخدم مفتاح Emergent (تنخصم نقاط)",
        "category": "ai",
        "priority": "high",
    },
    {
        "id": "openai",
        "name": "OpenAI GPT-4o + DALL-E",
        "name_ar": "OpenAI (GPT-4o + GPT Image 1)",
        "powers_ar": "الذكاء الرئيسي (GPT-4o path) + توليد صور gpt-image-1",
        "env_var": "OPENAI_DIRECT_KEY",
        "key_prefix": "sk-",
        "console_url": "https://platform.openai.com/api-keys",
        "signup_url": "https://platform.openai.com/signup",
        "pricing_url": "https://openai.com/api/pricing",
        "pricing_note_ar": "GPT-4o: $2.50/1M input · صور: ~$0.04/صورة",
        "fallback_env": None,
        "fallback_label_ar": "ميزة معطّلة بدون مفتاح",
        "category": "ai",
        "priority": "high",
    },
    {
        "id": "elevenlabs",
        "name": "ElevenLabs TTS",
        "name_ar": "ElevenLabs (الصوت)",
        "powers_ar": "صوت زارا/ليلى + توليد الموسيقى المحيطية",
        "env_var": "ELEVENLABS_API_KEY",
        "key_prefix": "",
        "console_url": "https://elevenlabs.io/app/settings/api-keys",
        "signup_url": "https://elevenlabs.io/sign-up",
        "pricing_url": "https://elevenlabs.io/pricing",
        "pricing_note_ar": "Starter: $5/شهر · 30K حرف",
        "fallback_env": None,
        "fallback_label_ar": "Avatar voice معطّل",
        "category": "ai",
        "priority": "medium",
    },
    {
        "id": "stripe",
        "name": "Stripe Payments",
        "name_ar": "Stripe (المدفوعات)",
        "powers_ar": "اشتراكات Studio + معالجة بطاقات",
        "env_var": "STRIPE_API_KEY",
        "key_prefix": "sk_",
        "console_url": "https://dashboard.stripe.com/apikeys",
        "signup_url": "https://dashboard.stripe.com/register",
        "pricing_url": "https://stripe.com/pricing",
        "pricing_note_ar": "2.9% + $0.30 لكل عملية",
        "fallback_env": None,
        "fallback_label_ar": "المدفوعات معطّلة",
        "category": "payments",
        "priority": "high",
    },
    {
        "id": "paypal",
        "name": "PayPal",
        "name_ar": "PayPal (المدفوعات)",
        "powers_ar": "خيار دفع بديل (اختياري)",
        "env_var": "PAYPAL_CLIENT_ID",
        "key_prefix": "",
        "console_url": "https://developer.paypal.com/dashboard/applications/live",
        "signup_url": "https://www.paypal.com/business",
        "pricing_url": "https://www.paypal.com/us/business/fees",
        "pricing_note_ar": "3.49% + رسوم ثابتة",
        "fallback_env": None,
        "fallback_label_ar": "اختياري — تركها معطّلة طبيعي",
        "category": "payments",
        "priority": "low",
    },
    {
        "id": "alpha_vantage",
        "name": "Alpha Vantage",
        "name_ar": "Alpha Vantage (الأسهم)",
        "powers_ar": "بيانات الأسهم اللحظية",
        "env_var": "ALPHA_VANTAGE_KEY",
        "key_prefix": "",
        "console_url": "https://www.alphavantage.co/support/#api-key",
        "signup_url": "https://www.alphavantage.co/support/#api-key",
        "pricing_url": "https://www.alphavantage.co/premium/",
        "pricing_note_ar": "مجاني (25 طلب/يوم) · $50/شهر للاستخدام الكثيف",
        "fallback_env": None,
        "fallback_label_ar": "بيانات الأسهم معطّلة",
        "category": "data",
        "priority": "low",
    },
    {
        "id": "emergent",
        "name": "Emergent Universal Key",
        "name_ar": "مفتاح Emergent (احتياطي)",
        "powers_ar": "Fallback لـ Claude/OpenAI + توليد الصور (Nano Banana) + Sora 2",
        "env_var": "EMERGENT_LLM_KEY",
        "key_prefix": "sk-emergent",
        "console_url": "#",  # internal
        "signup_url": "#",
        "pricing_url": "#",
        "pricing_note_ar": "موجود تلقائياً (تنخصم نقاط لما يُستخدم)",
        "fallback_env": None,
        "fallback_label_ar": "احتياطي — لا تحذفه",
        "category": "fallback",
        "priority": "managed",
    },
]


def create_independence_router(db, require_owner) -> APIRouter:
    router = APIRouter(prefix="/api/admin", tags=["admin-independence"])

    @router.get("/independence-status")
    async def status(owner=Depends(require_owner)):
        """Return status of every integration: which use direct keys (independent)
        vs fallback to Emergent."""
        items: List[Dict[str, Any]] = []
        independent_count = 0
        total_used = 0
        for ig in INTEGRATIONS:
            check = _check(ig["env_var"], ig.get("key_prefix", ""))
            using_fallback = (not check["valid_format"]) and bool(ig.get("fallback_env")) and bool(os.environ.get(ig["fallback_env"], "").strip())
            is_independent = check["valid_format"]
            status_label = (
                "🔓 مستقل" if is_independent
                else ("⚡ يستخدم Emergent" if using_fallback else "❌ غير مفعّل")
            )
            status_color = "green" if is_independent else ("amber" if using_fallback else "red")
            if ig["category"] != "fallback":
                total_used += 1
                if is_independent:
                    independent_count += 1
            items.append({
                **ig,
                "configured": check["set"],
                "valid_format": check["valid_format"],
                "preview": check["preview"],
                "is_independent": is_independent,
                "using_fallback": using_fallback,
                "status_label": status_label,
                "status_color": status_color,
            })
        # Categorize
        return {
            "independent_count": independent_count,
            "total_count": total_used,
            "all_independent": independent_count == total_used and total_used > 0,
            "integrations": items,
            "owner_id": owner.get("id"),
        }

    return router
