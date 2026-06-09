"""
AutoCoder Meta — owner-only capability, gaps, self-check, and integration roadmap report.

This module intentionally lives outside modules/autocoder so the self-programming
engine remains untouched. It exposes stable read-only endpoints that the owner UI
or future agents can query to understand what the AutoCoder can do, how mature it
is, and what keys or integrations are still required before claiming “complete”.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends


LLM_PROVIDERS: List[Dict[str, Any]] = [
    {"id": "anthropic", "name": "Anthropic Claude", "env": "ANTHROPIC_API_KEY", "best_for": ["coding", "long_context", "agentic_reasoning"], "priority": "primary", "weight": 14},
    {"id": "openai", "name": "OpenAI", "env": "OPENAI_DIRECT_KEY", "fallback_env": "OPENAI_API_KEY", "best_for": ["general_chat", "vision", "tts", "structured_output"], "priority": "high", "weight": 12},
    {"id": "gemini", "name": "Google Gemini", "env": "GEMINI_API_KEY", "best_for": ["long_context", "multimodal", "arabic"], "priority": "high", "weight": 10},
    {"id": "groq", "name": "Groq", "env": "GROQ_API_KEY", "best_for": ["fast_responses", "cheap_light_tasks"], "priority": "medium", "weight": 6},
    {"id": "deepseek", "name": "DeepSeek", "env": "DEEPSEEK_API_KEY", "best_for": ["reasoning", "coding_cost_control"], "priority": "medium", "weight": 6},
    {"id": "openrouter", "name": "OpenRouter", "env": "OPENROUTER_API_KEY", "best_for": ["model_marketplace", "cost_routing", "fallbacks"], "priority": "recommended", "weight": 8},
]

RECOMMENDED_INTEGRATIONS: List[Dict[str, Any]] = [
    {
        "id": "sentry",
        "name": "Sentry",
        "priority": "critical",
        "env_vars": ["SENTRY_DSN"],
        "where": "https://sentry.io/settings/projects/",
        "why_ar": "مراقبة أخطاء frontend/backend تلقائياً مع stack traces وتنبيهات بدل انتظار البلاغات.",
        "adds": ["error_tracking", "release_health", "frontend_source_maps"],
        "weight": 10,
    },
    {
        "id": "cloudflare_r2",
        "name": "Cloudflare R2 / S3-compatible storage",
        "priority": "critical",
        "env_vars": ["R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET", "R2_PUBLIC_URL", "CLOUDFLARE_ACCOUNT_ID"],
        "where": "https://developers.cloudflare.com/r2/api/s3/tokens/",
        "why_ar": "تخزين دائم ومنظم للصور والفيديوهات ومرفقات العملاء بدلاً من الاعتماد على تخزين الحاوية.",
        "adds": ["persistent_media", "cdn_links", "signed_uploads", "asset_library"],
        "weight": 12,
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "priority": "high",
        "env_vars": ["OPENROUTER_API_KEY"],
        "where": "https://openrouter.ai/settings/keys",
        "why_ar": "يفتح بوابة نماذج كثيرة لتقليل التكلفة وزيادة المرونة مع fallback ذكي.",
        "adds": ["100+_models", "cost_routing", "fallback_models"],
        "weight": 8,
    },
    {
        "id": "redis_queue",
        "name": "Redis + background jobs",
        "priority": "high",
        "env_vars": ["REDIS_URL"],
        "where": "https://railway.app/template/redis أو Upstash Redis",
        "why_ar": "تشغيل المهام الطويلة مثل توليد الفيديو وبناء المواقع الكبيرة بالخلفية مع progress/retry.",
        "adds": ["job_queue", "progress_tracking", "retries", "rate_limit_cache"],
        "weight": 8,
    },
    {
        "id": "livekit",
        "name": "LiveKit",
        "priority": "high",
        "env_vars": ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"],
        "where": "https://cloud.livekit.io/projects",
        "why_ar": "مساعد صوتي/فيديو حي داخل Zerax مع avatar ومقاطعة صوتية realtime.",
        "adds": ["realtime_voice", "voice_rooms", "avatar_live_chat"],
        "weight": 7,
    },
    {
        "id": "resend",
        "name": "Resend / SendGrid email",
        "priority": "medium",
        "env_vars": ["RESEND_API_KEY", "EMAIL_FROM"],
        "where": "https://resend.com/api-keys",
        "why_ar": "رسائل ترحيب، فواتير، استعادة حساب، وتنبيهات تشغيلية.",
        "adds": ["transactional_email", "notifications"],
        "weight": 4,
    },
    {
        "id": "fal_runway_luma_heygen",
        "name": "Fal / Runway / Luma / HeyGen",
        "priority": "medium",
        "env_vars": ["FAL_KEY", "RUNWAY_API_KEY", "LUMAAI_API_KEY", "HEYGEN_API_KEY"],
        "where": "https://fal.ai/dashboard/keys",
        "why_ar": "رفع جودة توليد الصور والفيديو والأفاتار التجاري.",
        "adds": ["advanced_media_generation", "talking_avatar", "pro_video"],
        "weight": 6,
    },
    {
        "id": "vector_db",
        "name": "Pinecone / Qdrant / MongoDB Vector Search",
        "priority": "medium",
        "env_vars": ["PINECONE_API_KEY", "PINECONE_INDEX"],
        "where": "https://www.pinecone.io/ أو Qdrant Cloud",
        "why_ar": "ذاكرة معرفية طويلة وبحث دلالي في الكود والمستندات وقرارات المالك.",
        "adds": ["rag", "semantic_code_search", "long_term_memory"],
        "weight": 5,
    },
    {
        "id": "posthog",
        "name": "PostHog / product analytics",
        "priority": "medium",
        "env_vars": ["POSTHOG_KEY", "POSTHOG_HOST"],
        "where": "https://app.posthog.com/project/settings",
        "why_ar": "تحليل استخدام العملاء، funnel التسجيل والدفع، ومعرفة الميزات الناجحة.",
        "adds": ["analytics", "funnels", "feature_flags"],
        "weight": 4,
    },
    {
        "id": "twilio_whatsapp",
        "name": "Twilio / WhatsApp Business",
        "priority": "optional",
        "env_vars": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER"],
        "where": "https://console.twilio.com/",
        "why_ar": "OTP وتنبيهات واتساب/SMS وبوت تواصل للعملاء.",
        "adds": ["sms", "whatsapp_notifications", "otp"],
        "weight": 2,
    },
]

CAPABILITIES: List[Dict[str, Any]] = [
    {"area": "code", "level": "strong", "items": ["قراءة وتعديل كود Zerax", "إنشاء backend modules", "إنشاء صفحات React", "اختبار lint/build/endpoints", "commit/push/rollback"]},
    {"area": "ops", "level": "strong", "items": ["Railway logs/deploy/env", "Vercel deploy status/logs", "health overview", "browser testing", "screenshots"]},
    {"area": "ai", "level": "strong", "items": ["توجيه نماذج LLM", "توليد صور", "توليد صوت", "توليد فيديو", "تحليل vision عند تمرير صور", "web search"]},
    {"area": "product", "level": "strong", "items": ["بناء أقسام كاملة", "لوحات admin/client", "أنظمة دفع/credits", "media studios", "website/app builders"]},
    {"area": "memory", "level": "medium", "items": ["دروس مستمرة", "كاش ملفات وأسئلة", "استرجاع تجارب سابقة"]},
    {"area": "governance", "level": "medium", "items": ["تقارير جاهزية", "روابط مفاتيح", "قائمة نواقص مرتبة", "منع ادعاء الاكتمال قبل الفحص"]},
]

COMMUNICATION_CONTRACT: Dict[str, Any] = {
    "title": "طريقة عمل برمجة زيتاكس مع المالك",
    "before_building_any_section": [
        "أشرح فهمي للطلب في نقاط قصيرة.",
        "أحدد بالضبط ماذا سأبني: backend, frontend, database, permissions, dashboard card.",
        "أعرض المميزات المتوقعة والخدمات التي سيقدمها القسم.",
        "أبدأ التنفيذ الفعلي مباشرة بدون انتظار تأكيد إلا إذا كان القرار جوهرياً.",
    ],
    "after_finishing": [
        "أعرض روابط الصفحات أو endpoints.",
        "أذكر الاختبارات التي نجحت بالأدلة.",
        "أذكر النواقص فقط إذا كانت مفاتيح خارجية غير متوفرة.",
        "أختم بخلاصة مربعة: تم/روابط/نصائح/الخطوة التالية.",
    ],
}


def _mask_status(env_name: str) -> Dict[str, Any]:
    value = os.environ.get(env_name, "")
    return {
        "env": env_name,
        "configured": bool(value),
        "preview": (value[:4] + "..." + value[-4:]) if len(value) > 12 else ("***" if value else None),
    }


def _provider_status(provider: Dict[str, Any]) -> Dict[str, Any]:
    primary = _mask_status(provider["env"])
    fallback = _mask_status(provider["fallback_env"]) if provider.get("fallback_env") else None
    configured = primary["configured"] or bool(fallback and fallback["configured"])
    return {**provider, "configured": configured, "env_status": primary, "fallback_status": fallback}


def _integration_status(item: Dict[str, Any]) -> Dict[str, Any]:
    vars_status = [_mask_status(name) for name in item.get("env_vars", [])]
    configured_count = sum(1 for v in vars_status if v["configured"])
    total = len(vars_status)
    status = "configured" if total and configured_count == total else "partial" if configured_count else "missing"
    readiness_ratio = (configured_count / total) if total else 0
    return {**item, "status": status, "configured_count": configured_count, "total_env_vars": total, "readiness_ratio": readiness_ratio, "env_status": vars_status}


def _score_readiness(providers: List[Dict[str, Any]], integrations: List[Dict[str, Any]]) -> Dict[str, Any]:
    base_capability_points = 22  # code/ops/git/browser/db/tooling are already available in this deployment.
    provider_possible = sum(int(p.get("weight", 1)) for p in providers)
    provider_points = sum(int(p.get("weight", 1)) for p in providers if p.get("configured"))

    integration_possible = sum(int(i.get("weight", 1)) for i in integrations)
    integration_points = 0.0
    for item in integrations:
        integration_points += float(item.get("weight", 1)) * float(item.get("readiness_ratio", 0))

    possible = base_capability_points + provider_possible + integration_possible
    points = base_capability_points + provider_points + integration_points
    score = round((points / possible) * 100) if possible else 0

    critical_missing = [i for i in integrations if i.get("priority") == "critical" and i.get("status") != "configured"]
    high_missing = [i for i in integrations if i.get("priority") == "high" and i.get("status") != "configured"]

    if score >= 95 and not critical_missing:
        maturity = "complete"
        verdict_ar = "مكتمل تشغيلياً: أقدر أقول إن برمجة زيتاكس جاهز بمستوى عالي جداً ولا ينقصه شيء أساسي."
    elif score >= 80 and not critical_missing:
        maturity = "advanced"
        verdict_ar = "متقدم جداً: الأساس قوي، والنواقص المتبقية تحسينات توسّع وليست عوائق رئيسية."
    elif score >= 65:
        maturity = "strong_but_not_complete"
        verdict_ar = "قوي لكن غير مكتمل: أقدر أنفذ وأطور Zerax، لكن لا أقدر أقول مكتمل بالكامل قبل إغلاق النواقص الحرجة."
    else:
        maturity = "foundation"
        verdict_ar = "مرحلة تأسيس: توجد قدرات مهمة لكن يلزم إكمال تكاملات أساسية قبل الاعتماد العالي."

    return {
        "score": score,
        "maturity": maturity,
        "verdict_ar": verdict_ar,
        "points": round(points, 2),
        "possible_points": possible,
        "critical_missing_count": len(critical_missing),
        "high_missing_count": len(high_missing),
    }


def _next_actions(integrations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    order = {"critical": 0, "high": 1, "medium": 2, "optional": 3}
    pending = [item for item in integrations if item.get("status") != "configured"]
    pending.sort(key=lambda x: (order.get(str(x.get("priority")), 9), -int(x.get("weight", 0)), x.get("name", "")))
    actions = []
    for idx, item in enumerate(pending[:8], start=1):
        missing_env = [v["env"] for v in item.get("env_status", []) if not v.get("configured")]
        actions.append({
            "step": idx,
            "id": item["id"],
            "name": item["name"],
            "priority": item["priority"],
            "missing_env": missing_env,
            "where": item.get("where"),
            "why_ar": item.get("why_ar"),
        })
    return actions


def _build_report(owner: Dict[str, Any] | None = None) -> Dict[str, Any]:
    providers = [_provider_status(provider) for provider in LLM_PROVIDERS]
    integrations = [_integration_status(item) for item in RECOMMENDED_INTEGRATIONS]
    readiness = _score_readiness(providers, integrations)
    actions = _next_actions(integrations)
    configured_integrations = [i for i in integrations if i.get("status") == "configured"]
    configured_providers = [p for p in providers if p.get("configured")]

    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "owner_id": (owner or {}).get("id"),
        "readiness": readiness,
        "summary_ar": (
            "برمجة زيتاكس قادر حالياً على تطوير Zerax end-to-end: كود، اختبارات، نشر، مراقبة، وذكاء متعدد النماذج. "
            "لكن الاكتمال المطلق مشروط بإكمال التخزين الدائم والـobservability وتوسيع مسارات النماذج والمهام الخلفية."
        ),
        "configured_counts": {
            "llm_providers": len(configured_providers),
            "recommended_integrations": len(configured_integrations),
            "total_llm_providers": len(providers),
            "total_recommended_integrations": len(integrations),
        },
        "capabilities": CAPABILITIES,
        "communication_contract": COMMUNICATION_CONTRACT,
        "llm_providers": providers,
        "recommended_integrations": integrations,
        "next_actions": actions,
        "completion_definition_ar": [
            "لا أقول مكتمل بالكامل إلا إذا readiness.score >= 95.",
            "لازم كل critical integrations تكون configured، خصوصاً Sentry DSN وR2/S3 storage.",
            "لازم يبقى عندي GitHub/Railway/Vercel شغالة للنشر والإصلاح والrollback.",
            "أي نقص خارجي أذكره كرابط ومفتاح مطلوب، وليس كعذر لإيقاف التطوير الداخلي.",
        ],
    }


def create_autocoder_meta_router(db, get_current_user, require_owner):
    router = APIRouter(prefix="/api/autocoder-meta", tags=["autocoder-meta"])

    @router.get("/capabilities")
    async def capabilities(owner=Depends(require_owner)):
        """Read-only owner report: what AutoCoder can do, models, and recommended additions."""
        return _build_report(owner)

    @router.get("/self-check")
    async def self_check(owner=Depends(require_owner)):
        """Canonical self-check endpoint: can the AutoCoder honestly claim it is complete?"""
        report = _build_report(owner)
        readiness = report["readiness"]
        return {
            "ok": True,
            "complete": readiness["maturity"] == "complete",
            "score": readiness["score"],
            "maturity": readiness["maturity"],
            "verdict_ar": readiness["verdict_ar"],
            "must_fix_before_claiming_complete": report["next_actions"][:5],
            "communication_contract": COMMUNICATION_CONTRACT,
            "generated_at": report["generated_at"],
        }

    @router.get("/roadmap")
    async def roadmap(owner=Depends(require_owner)):
        """Same information in a compact implementation roadmap form."""
        report = _build_report(owner)
        return {
            "ok": True,
            "current_score": report["readiness"]["score"],
            "current_maturity": report["readiness"]["maturity"],
            "phases": [
                {"phase": 1, "title": "Production observability", "keys": ["SENTRY_DSN"], "link": "https://sentry.io/settings/projects/", "outcome": "أعرف أخطاء المستخدمين فوراً وأصلحها بدليل."},
                {"phase": 2, "title": "Persistent media storage", "keys": ["R2_* أو S3_*"], "link": "https://developers.cloudflare.com/r2/api/s3/tokens/", "outcome": "ملفات وصور وفيديوهات بروابط ثابتة وسريعة."},
                {"phase": 3, "title": "Model marketplace", "keys": ["OPENROUTER_API_KEY"], "link": "https://openrouter.ai/settings/keys", "outcome": "نماذج أكثر وتكلفة أقل وفشل أقل."},
                {"phase": 4, "title": "Background jobs", "keys": ["REDIS_URL"], "link": "https://railway.app/template/redis", "outcome": "مهام طويلة مستقرة مع progress."},
                {"phase": 5, "title": "Realtime AI", "keys": ["LIVEKIT_*"], "link": "https://cloud.livekit.io/projects", "outcome": "مساعد صوتي/مرئي مباشر داخل المنصة."},
                {"phase": 6, "title": "Advanced media", "keys": ["FAL_KEY", "HEYGEN_API_KEY", "RUNWAY_API_KEY"], "link": "https://fal.ai/dashboard/keys", "outcome": "وسائط AI تجارية أقوى."},
                {"phase": 7, "title": "RAG memory", "keys": ["PINECONE_* أو QDRANT_*"], "link": "https://www.pinecone.io/", "outcome": "ذاكرة معرفية وبحث دلالي عميق."},
            ],
            "next_actions": report["next_actions"],
        }

    return router
