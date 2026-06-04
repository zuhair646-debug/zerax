"""
AutoCoder Meta — owner-only capability, gaps, and integration roadmap report.

This module intentionally lives outside modules/autocoder so the self-programming
engine remains untouched. It exposes stable read-only endpoints that the owner UI
or future agents can query to understand what the AutoCoder can do and what keys
or integrations are still recommended.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends


LLM_PROVIDERS: List[Dict[str, Any]] = [
    {"id": "anthropic", "name": "Anthropic Claude", "env": "ANTHROPIC_API_KEY", "best_for": ["coding", "long_context", "agentic_reasoning"], "priority": "primary"},
    {"id": "openai", "name": "OpenAI", "env": "OPENAI_DIRECT_KEY", "fallback_env": "OPENAI_API_KEY", "best_for": ["general_chat", "vision", "tts", "structured_output"], "priority": "high"},
    {"id": "gemini", "name": "Google Gemini", "env": "GEMINI_API_KEY", "best_for": ["long_context", "multimodal", "arabic"], "priority": "high"},
    {"id": "groq", "name": "Groq", "env": "GROQ_API_KEY", "best_for": ["fast_responses", "cheap_light_tasks"], "priority": "medium"},
    {"id": "deepseek", "name": "DeepSeek", "env": "DEEPSEEK_API_KEY", "best_for": ["reasoning", "coding_cost_control"], "priority": "medium"},
    {"id": "openrouter", "name": "OpenRouter", "env": "OPENROUTER_API_KEY", "best_for": ["model_marketplace", "cost_routing", "fallbacks"], "priority": "recommended"},
]

RECOMMENDED_INTEGRATIONS: List[Dict[str, Any]] = [
    {
        "id": "sentry",
        "name": "Sentry",
        "priority": "critical",
        "env_vars": ["SENTRY_DSN"],
        "why_ar": "مراقبة أخطاء frontend/backend تلقائياً مع stack traces وتنبيهات بدل انتظار البلاغات.",
        "adds": ["error_tracking", "release_health", "frontend_source_maps"],
    },
    {
        "id": "cloudflare_r2",
        "name": "Cloudflare R2 / S3-compatible storage",
        "priority": "critical",
        "env_vars": ["R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET", "R2_PUBLIC_URL", "CLOUDFLARE_ACCOUNT_ID"],
        "why_ar": "تخزين دائم ومنظم للصور والفيديوهات ومرفقات العملاء بدلاً من الاعتماد على تخزين الحاوية.",
        "adds": ["persistent_media", "cdn_links", "signed_uploads", "asset_library"],
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "priority": "high",
        "env_vars": ["OPENROUTER_API_KEY"],
        "why_ar": "يفتح بوابة نماذج كثيرة لتقليل التكلفة وزيادة المرونة مع fallback ذكي.",
        "adds": ["100+_models", "cost_routing", "fallback_models"],
    },
    {
        "id": "redis_queue",
        "name": "Redis + background jobs",
        "priority": "high",
        "env_vars": ["REDIS_URL"],
        "why_ar": "تشغيل المهام الطويلة مثل توليد الفيديو وبناء المواقع الكبيرة بالخلفية مع progress/retry.",
        "adds": ["job_queue", "progress_tracking", "retries", "rate_limit_cache"],
    },
    {
        "id": "livekit",
        "name": "LiveKit",
        "priority": "high",
        "env_vars": ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"],
        "why_ar": "مساعد صوتي/فيديو حي داخل Zitex مع avatar ومقاطعة صوتية realtime.",
        "adds": ["realtime_voice", "voice_rooms", "avatar_live_chat"],
    },
    {
        "id": "resend",
        "name": "Resend / SendGrid email",
        "priority": "medium",
        "env_vars": ["RESEND_API_KEY", "EMAIL_FROM"],
        "why_ar": "رسائل ترحيب، فواتير، استعادة حساب، وتنبيهات تشغيلية.",
        "adds": ["transactional_email", "notifications"],
    },
    {
        "id": "fal_runway_luma_heygen",
        "name": "Fal / Runway / Luma / HeyGen",
        "priority": "medium",
        "env_vars": ["FAL_KEY", "RUNWAY_API_KEY", "LUMAAI_API_KEY", "HEYGEN_API_KEY"],
        "why_ar": "رفع جودة توليد الصور والفيديو والأفاتار التجاري.",
        "adds": ["advanced_media_generation", "talking_avatar", "pro_video"],
    },
    {
        "id": "vector_db",
        "name": "Pinecone / Qdrant / MongoDB Vector Search",
        "priority": "medium",
        "env_vars": ["PINECONE_API_KEY", "PINECONE_INDEX"],
        "why_ar": "ذاكرة معرفية طويلة وبحث دلالي في الكود والمستندات وقرارات المالك.",
        "adds": ["rag", "semantic_code_search", "long_term_memory"],
    },
    {
        "id": "posthog",
        "name": "PostHog / product analytics",
        "priority": "medium",
        "env_vars": ["POSTHOG_KEY", "POSTHOG_HOST"],
        "why_ar": "تحليل استخدام العملاء، funnel التسجيل والدفع، ومعرفة الميزات الناجحة.",
        "adds": ["analytics", "funnels", "feature_flags"],
    },
    {
        "id": "twilio_whatsapp",
        "name": "Twilio / WhatsApp Business",
        "priority": "optional",
        "env_vars": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER"],
        "why_ar": "OTP وتنبيهات واتساب/SMS وبوت تواصل للعملاء.",
        "adds": ["sms", "whatsapp_notifications", "otp"],
    },
]

CAPABILITIES: List[Dict[str, Any]] = [
    {"area": "code", "items": ["قراءة وتعديل كود Zitex", "إنشاء backend modules", "إنشاء صفحات React", "اختبار lint/build/endpoints", "commit/push/rollback"]},
    {"area": "ops", "items": ["Railway logs/deploy/env", "Vercel deploy status/logs", "health overview", "browser testing", "screenshots"]},
    {"area": "ai", "items": ["توجيه نماذج LLM", "توليد صور", "توليد صوت", "توليد فيديو", "تحليل vision عند تمرير صور", "web search"]},
    {"area": "product", "items": ["بناء أقسام كاملة", "لوحات admin/client", "أنظمة دفع/credits", "media studios", "website/app builders"]},
]


def _mask_status(env_name: str) -> Dict[str, Any]:
    value = os.environ.get(env_name, "")
    return {
        "env": env_name,
        "configured": bool(value),
        "preview": (value[:4] + "..." + value[-4:]) if len(value) > 12 else ("***" if value else None),
    }


def _integration_status(item: Dict[str, Any]) -> Dict[str, Any]:
    vars_status = [_mask_status(name) for name in item.get("env_vars", [])]
    configured_count = sum(1 for v in vars_status if v["configured"])
    total = len(vars_status)
    status = "configured" if total and configured_count == total else "partial" if configured_count else "missing"
    return {**item, "status": status, "configured_count": configured_count, "total_env_vars": total, "env_status": vars_status}


def create_autocoder_meta_router(db, get_current_user, require_owner):
    router = APIRouter(prefix="/api/autocoder-meta", tags=["autocoder-meta"])

    @router.get("/capabilities")
    async def capabilities(owner=Depends(require_owner)):
        """Read-only owner report: what AutoCoder can do, models, and recommended additions."""
        providers = []
        for provider in LLM_PROVIDERS:
            primary = _mask_status(provider["env"])
            fallback = _mask_status(provider["fallback_env"]) if provider.get("fallback_env") else None
            providers.append({**provider, "configured": primary["configured"] or bool(fallback and fallback["configured"]), "env_status": primary, "fallback_status": fallback})

        integrations = [_integration_status(item) for item in RECOMMENDED_INTEGRATIONS]
        return {
            "ok": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "owner_id": (owner or {}).get("id"),
            "summary_ar": "برمجة زيتاكس قادر على تعديل Zitex end-to-end. أعلى الإضافات المقترحة: Sentry، تخزين R2/S3، OpenRouter، Redis queue، LiveKit.",
            "capabilities": CAPABILITIES,
            "llm_providers": providers,
            "recommended_integrations": integrations,
            "recommended_next_steps": [
                "إضافة SENTRY_DSN ثم ربط Sentry بالـbackend والـfrontend.",
                "إضافة Cloudflare R2/S3 لتخزين كل الوسائط والمرفقات بشكل دائم.",
                "إضافة OPENROUTER_API_KEY وتوسيع ai_core/router لسياسات cheap/balanced/best/vision/arabic.",
                "إضافة REDIS_URL للمهام الطويلة مع progress/retry.",
                "إضافة LIVEKIT_* عند رغبة المالك بمساعد صوتي حي أو avatar مباشر.",
            ],
        }

    @router.get("/roadmap")
    async def roadmap(owner=Depends(require_owner)):
        """Same information in a compact implementation roadmap form."""
        return {
            "ok": True,
            "phases": [
                {"phase": 1, "title": "Production observability", "keys": ["SENTRY_DSN"], "outcome": "أعرف أخطاء المستخدمين فوراً وأصلحها بدليل."},
                {"phase": 2, "title": "Persistent media storage", "keys": ["R2_* أو S3_*"], "outcome": "ملفات وصور وفيديوهات بروابط ثابتة وسريعة."},
                {"phase": 3, "title": "Model marketplace", "keys": ["OPENROUTER_API_KEY"], "outcome": "نماذج أكثر وتكلفة أقل وفشل أقل."},
                {"phase": 4, "title": "Background jobs", "keys": ["REDIS_URL"], "outcome": "مهام طويلة مستقرة مع progress."},
                {"phase": 5, "title": "Realtime AI", "keys": ["LIVEKIT_*"], "outcome": "مساعد صوتي/مرئي مباشر داخل المنصة."},
                {"phase": 6, "title": "Advanced media", "keys": ["FAL_KEY", "HEYGEN_API_KEY", "RUNWAY_API_KEY"], "outcome": "وسائط AI تجارية أقوى."},
                {"phase": 7, "title": "RAG memory", "keys": ["PINECONE_* أو QDRANT_*"], "outcome": "ذاكرة معرفية وبحث دلالي عميق."},
            ],
        }

    return router
