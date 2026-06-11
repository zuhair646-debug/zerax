"""
Integrations status helper — gives the auto-coder a single tool to introspect
which third-party integrations have credentials, which are missing, and how
to add them.

This complements `independence/keys` (user-facing UI) by exposing the same
data through a tool the AI can call (`integrations_status()`).
"""
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional


# All integrations Zenrex *could* use, their env-var names, and how to obtain.
# This is the single source of truth — keep it in sync with the Independence UI cards.
INTEGRATIONS_CATALOG: List[Dict[str, Any]] = [
    # ───────── LLM providers ─────────
    {"id": "anthropic", "label": "Anthropic Claude", "env": ["ANTHROPIC_API_KEY"],
     "category": "llm", "where": "https://console.anthropic.com/settings/keys",
     "purpose": "نص + استدلال الأدوات (Auto-Coder الأساسي)"},
    {"id": "openai", "label": "OpenAI", "env": ["OPENAI_API_KEY", "OPENAI_DIRECT_KEY"],
     "category": "llm", "where": "https://platform.openai.com/api-keys",
     "purpose": "GPT-4o / GPT-5.5 + التوليد متعدد الوسائط (vision في FreeBuild)"},
    {"id": "gemini", "label": "Google Gemini", "env": ["GEMINI_API_KEY"],
     "category": "llm", "where": "https://aistudio.google.com/apikey",
     "purpose": "Gemini 3 + توليد الصور Nano Banana"},
    {"id": "groq", "label": "Groq Llama", "env": ["GROQ_API_KEY"],
     "category": "llm", "where": "https://console.groq.com/keys",
     "purpose": "Llama 3.3 + استدلال سريع جداً"},
    {"id": "openrouter", "label": "OpenRouter", "env": ["OPENROUTER_API_KEY"],
     "category": "llm-optional", "where": "https://openrouter.ai/keys",
     "purpose": "وصول لـ100+ نموذج عبر API واحد"},
    {"id": "deepseek", "label": "DeepSeek", "env": ["DEEPSEEK_API_KEY"],
     "category": "llm-optional", "where": "https://platform.deepseek.com/api_keys",
     "purpose": "نماذج رخيصة قوية للـreasoning"},
    {"id": "mistral", "label": "Mistral", "env": ["MISTRAL_API_KEY"],
     "category": "llm-optional", "where": "https://console.mistral.ai/api-keys/",
     "purpose": "نماذج أوروبية مفتوحة"},
    {"id": "huggingface", "label": "HuggingFace", "env": ["HF_TOKEN"],
     "category": "llm-optional", "where": "https://huggingface.co/settings/tokens",
     "purpose": "وصول لآلاف نماذج open-source"},
    # ───────── Web search (for Auto-Coder grounding) ─────────
    {"id": "tavily", "label": "Tavily Web Search", "env": ["TAVILY_API_KEY"],
     "category": "infra", "where": "https://app.tavily.com",
     "purpose": "بحث ويب حي للأخبار/التوثيق (1000 credit/شهر مجاني)"},
    # ───────── Media generation ─────────
    {"id": "fal", "label": "Fal.ai", "env": ["FAL_KEY"],
     "category": "media", "where": "https://fal.ai/dashboard/keys",
     "purpose": "صور وفيديو سريع (FLUX, AnimateDiff)"},
    {"id": "runway", "label": "Runway", "env": ["RUNWAY_API_KEY"],
     "category": "media", "where": "https://app.runwayml.com/account",
     "purpose": "Gen-3 Alpha فيديو احترافي"},
    {"id": "luma", "label": "Luma AI", "env": ["LUMAAI_API_KEY"],
     "category": "media", "where": "https://lumalabs.ai/dream-machine/api/keys",
     "purpose": "Dream Machine لتوليد الفيديو"},
    {"id": "heygen", "label": "HeyGen", "env": ["HEYGEN_API_KEY"],
     "category": "media", "where": "https://app.heygen.com/settings?nav=API",
     "purpose": "أفاتار رقمية + voice cloning"},
    {"id": "stability", "label": "Stability AI", "env": ["STABILITY_API_KEY"],
     "category": "media", "where": "https://platform.stability.ai/account/keys",
     "purpose": "Stable Diffusion + SD3 + Stable Video"},
    {"id": "replicate", "label": "Replicate", "env": ["REPLICATE_API_TOKEN"],
     "category": "media", "where": "https://replicate.com/account/api-tokens",
     "purpose": "آلاف نماذج مفتوحة (FLUX, LLaMA, Whisper, etc.)"},
    {"id": "elevenlabs", "label": "ElevenLabs", "env": ["ELEVENLABS_API_KEY"],
     "category": "media", "where": "https://elevenlabs.io/app/settings/api-keys",
     "purpose": "أصوات عربية احترافية + clone"},
    # ───────── Payments ─────────
    {"id": "stripe", "label": "Stripe", "env": ["STRIPE_API_KEY", "STRIPE_WEBHOOK_SECRET"],
     "category": "payments", "where": "https://dashboard.stripe.com/apikeys",
     "purpose": "دفع subscriptions + شحن رصيد"},
    # ───────── Auth ─────────
    {"id": "google_oauth", "label": "Google OAuth", "env": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
     "category": "auth", "where": "https://console.cloud.google.com/apis/credentials",
     "purpose": "تسجيل الدخول السريع بحساب جوجل"},
    # ───────── Infrastructure ─────────
    {"id": "github", "label": "GitHub", "env": ["GITHUB_TOKEN", "GITHUB_REPO"],
     "category": "infra", "where": "https://github.com/settings/tokens",
     "purpose": "الـAuto-Coder يدفع كود + يفتح PRs"},
    {"id": "railway", "label": "Railway", "env": ["RAILWAY_TOKEN", "RAILWAY_PROJECT_ID", "RAILWAY_SERVICE_ID", "RAILWAY_ENVIRONMENT_ID"],
     "category": "infra", "where": "https://railway.app/account/tokens",
     "purpose": "نشر backend + قراءة logs + rollback"},
    {"id": "vercel", "label": "Vercel", "env": ["VERCEL_TOKEN", "VERCEL_ORG_ID", "VERCEL_PROJECT_ID"],
     "category": "infra", "where": "https://vercel.com/account/tokens",
     "purpose": "نشر frontend + معاينات PR"},
    # ───────── Storage / CDN ─────────
    {"id": "aws", "label": "AWS S3", "env": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
     "category": "storage", "where": "https://console.aws.amazon.com/iam/home#/security_credentials",
     "purpose": "تخزين ملفات + بث وسائط"},
    {"id": "cloudflare", "label": "Cloudflare", "env": ["CLOUDFLARE_API_TOKEN"],
     "category": "storage", "where": "https://dash.cloudflare.com/profile/api-tokens",
     "purpose": "CDN + R2 storage + Workers"},
    # ───────── Realtime / Communication ─────────
    {"id": "livekit", "label": "LiveKit", "env": ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"],
     "category": "realtime", "where": "https://cloud.livekit.io/projects",
     "purpose": "محادثة صوت/فيديو لحظية"},
    {"id": "twilio", "label": "Twilio", "env": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"],
     "category": "realtime", "where": "https://console.twilio.com/",
     "purpose": "إرسال SMS + WhatsApp"},
    # ───────── Observability ─────────
    {"id": "sentry", "label": "Sentry", "env": ["SENTRY_DSN"],
     "category": "observability", "where": "https://sentry.io/settings/projects/",
     "purpose": "مراقبة الأخطاء + alerting"},
]


def _check_one(item: Dict[str, Any]) -> Dict[str, Any]:
    have = []
    miss = []
    for ev in item["env"]:
        if (os.environ.get(ev) or "").strip():
            have.append(ev)
        else:
            miss.append(ev)
    return {
        **item,
        "configured": len(have) == len(item["env"]),
        "have": have,
        "missing": miss,
    }


async def tool_integrations_status(category: Optional[str] = None) -> Dict[str, Any]:
    """List ALL Zenrex integrations and which env-vars are configured.

    Args:
        category: optional filter — 'llm', 'llm-optional', 'media', 'payments',
                  'auth', 'infra', 'storage', 'realtime', 'observability'.
    """
    items = [_check_one(x) for x in INTEGRATIONS_CATALOG]
    if category:
        items = [x for x in items if x.get("category") == category]
    by_status = {"configured": [], "partial": [], "missing": []}
    for it in items:
        if it["configured"]:
            by_status["configured"].append(it)
        elif it["have"]:
            by_status["partial"].append(it)
        else:
            by_status["missing"].append(it)
    summary = (
        f"✅ مفعّل: {len(by_status['configured'])} · "
        f"⚠️ ناقص: {len(by_status['partial'])} · "
        f"❌ غير مهيأ: {len(by_status['missing'])}"
    )
    return {
        "ok": True,
        "summary": summary,
        "configured": [{"id": x["id"], "label": x["label"]} for x in by_status["configured"]],
        "partial": [{"id": x["id"], "label": x["label"], "missing": x["missing"]} for x in by_status["partial"]],
        "missing": [
            {"id": x["id"], "label": x["label"], "env": x["env"], "where": x["where"], "purpose": x["purpose"]}
            for x in by_status["missing"]
        ],
        "total": len(items),
    }


INTEGRATIONS_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "integrations_status",
        "description": "📊 اعرض حالة كل تكاملات Zenrex (LLM، دفع، تخزين، realtime…) — وش مهيأ ووش ناقص. اختياري filter بالـcategory.",
        "input_schema": {"type": "object", "properties": {
            "category": {"type": "string", "enum": [
                "llm", "llm-optional", "media", "payments", "auth", "infra",
                "storage", "realtime", "observability",
            ]},
        }, "required": []},
    },
]

INTEGRATIONS_TOOL_HANDLERS = {
    "integrations_status": tool_integrations_status,
}

INTEGRATIONS_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "integrations_status", "desc": "list configured/missing integrations", "args": ["category?"]},
]


def integrations_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name != "integrations_status":
        return None
    if not result.get("ok"):
        return None
    return result.get("summary", "integrations checked")


def integrations_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name != "integrations_status":
        return None
    if not result.get("ok"):
        return None
    lines = []
    if result.get("configured"):
        lines.append("✅ مهيأة: " + ", ".join(x["label"] for x in result["configured"]))
    if result.get("missing"):
        lines.append("❌ ناقصة:")
        for x in result["missing"][:8]:
            lines.append(f"  • {x['label']} → {x['where']}")
    return "\n".join(lines)[:1200]
