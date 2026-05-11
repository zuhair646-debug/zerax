"""
Independence Status — owner-only dashboard showing which API keys are
configured for direct (independent) use vs falling back to Emergent.

Endpoint: GET /api/admin/independence-status
"""
from __future__ import annotations
import os
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException

try:
    from modules.autocoder.credentials_vault import vault_get as _vault_get
except Exception:
    def _vault_get(_k: str):  # type: ignore
        return None

from .tutorials import get_tutorial, RAILWAY_TUTORIAL


def _check(env_name: str, prefix: str = "") -> Dict[str, Any]:
    val = (os.environ.get(env_name) or "").strip()
    source = "env" if val else None
    if not val:
        v2 = _vault_get(env_name)
        if v2:
            val = v2.strip()
            source = "vault"
    is_set = bool(val)
    is_valid = is_set and (not prefix or val.startswith(prefix))
    return {
        "set": is_set,
        "valid_format": is_valid,
        "source": source,
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
    # ════════════════════════════════════════════════════════════════════
    # 🤖 إضافي — LLM Providers
    # ════════════════════════════════════════════════════════════════════
    {
        "id": "groq",
        "name": "Groq (Llama 3.3)",
        "name_ar": "Groq — لاما 3.3 70B (سريع جداً)",
        "powers_ar": "موديل بديل سريع للذكاء (الـAuto-Coder + AI Agent)",
        "env_var": "GROQ_API_KEY",
        "key_prefix": "gsk_",
        "console_url": "https://console.groq.com/keys",
        "signup_url": "https://console.groq.com",
        "pricing_url": "https://groq.com/pricing",
        "pricing_note_ar": "مجاني (محدود الـrate) · مدفوع $0.59/1M tokens",
        "fallback_env": "EMERGENT_LLM_KEY",
        "fallback_label_ar": "Auto-Coder يستخدم Claude بدلاً",
        "category": "ai", "priority": "medium",
    },
    {
        "id": "gemini",
        "name": "Google Gemini 2.5 Flash",
        "name_ar": "Gemini 2.5 Flash (Google)",
        "powers_ar": "موديل Google السريع + multimodal (نص+صور)",
        "env_var": "GEMINI_API_KEY",
        "key_prefix": "",
        "console_url": "https://aistudio.google.com/app/apikey",
        "signup_url": "https://aistudio.google.com",
        "pricing_url": "https://ai.google.dev/pricing",
        "pricing_note_ar": "مجاني (1500 طلب/يوم) · $0.075/1M input بعدها",
        "fallback_env": "EMERGENT_LLM_KEY",
        "fallback_label_ar": "Auto-Coder يستخدم Claude بدلاً",
        "category": "ai", "priority": "medium",
    },
    {
        "id": "openrouter",
        "name": "OpenRouter (300+ models)",
        "name_ar": "OpenRouter — وصول لـ300+ موديل",
        "powers_ar": "DeepSeek, Llama, Mistral, Qwen, Gemma من API واحدة",
        "env_var": "OPENROUTER_API_KEY",
        "key_prefix": "sk-or-",
        "console_url": "https://openrouter.ai/keys",
        "signup_url": "https://openrouter.ai",
        "pricing_url": "https://openrouter.ai/models",
        "pricing_note_ar": "Pay-as-you-go (أرخص أحياناً من OpenAI مباشرة)",
        "fallback_env": None,
        "fallback_label_ar": "تنوّع الموديلات معطّل",
        "category": "ai", "priority": "medium",
    },
    {
        "id": "mistral",
        "name": "Mistral AI",
        "name_ar": "Mistral (Large + Codestral)",
        "powers_ar": "موديل أوروبي ممتاز للبرمجة (Codestral)",
        "env_var": "MISTRAL_API_KEY", "key_prefix": "",
        "console_url": "https://console.mistral.ai/api-keys",
        "signup_url": "https://console.mistral.ai",
        "pricing_url": "https://mistral.ai/technology/#pricing",
        "pricing_note_ar": "$0.50-$2/1M tokens",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "ai", "priority": "low",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek V3",
        "name_ar": "DeepSeek V3 (أرخص بكثير من GPT)",
        "powers_ar": "موديل صيني ممتاز للبرمجة بسعر منخفض جداً",
        "env_var": "DEEPSEEK_API_KEY", "key_prefix": "sk-",
        "console_url": "https://platform.deepseek.com/api_keys",
        "signup_url": "https://platform.deepseek.com",
        "pricing_url": "https://platform.deepseek.com/api-docs/pricing",
        "pricing_note_ar": "$0.14/1M input · $0.28/1M output (≈10× أرخص من GPT)",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "ai", "priority": "low",
    },
    {
        "id": "huggingface",
        "name": "Hugging Face",
        "name_ar": "Hugging Face (آلاف الموديلات)",
        "powers_ar": "وصول لمكتبة الموديلات + Inference API",
        "env_var": "HF_TOKEN", "key_prefix": "hf_",
        "console_url": "https://huggingface.co/settings/tokens",
        "signup_url": "https://huggingface.co/join",
        "pricing_url": "https://huggingface.co/pricing",
        "pricing_note_ar": "مجاني (محدود) · $9/شهر للـPro",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "ai", "priority": "low",
    },
    # ════════════════════════════════════════════════════════════════════
    # 🎨 Media Generation
    # ════════════════════════════════════════════════════════════════════
    {
        "id": "fal",
        "name": "fal.ai",
        "name_ar": "fal.ai — أفضل توليد صور/فيديو (FLUX, SDXL, Veo)",
        "powers_ar": "صور احترافية + فيديو + Lip-sync + ControlNet",
        "env_var": "FAL_KEY", "key_prefix": "",
        "console_url": "https://fal.ai/dashboard/keys",
        "signup_url": "https://fal.ai",
        "pricing_url": "https://fal.ai/pricing",
        "pricing_note_ar": "Pay-per-image (~$0.01-0.10/صورة)",
        "fallback_env": "EMERGENT_LLM_KEY",
        "fallback_label_ar": "يستخدم Nano Banana من Emergent",
        "category": "media", "priority": "high",
    },
    {
        "id": "stability",
        "name": "Stability AI",
        "name_ar": "Stable Diffusion API",
        "powers_ar": "توليد صور SD/SDXL مباشرة",
        "env_var": "STABILITY_API_KEY", "key_prefix": "sk-",
        "console_url": "https://platform.stability.ai/account/keys",
        "signup_url": "https://platform.stability.ai",
        "pricing_url": "https://platform.stability.ai/pricing",
        "pricing_note_ar": "Credits — $10 = ~500 صورة",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "media", "priority": "medium",
    },
    {
        "id": "runway",
        "name": "Runway Gen-3",
        "name_ar": "Runway (فيديو احترافي)",
        "powers_ar": "توليد فيديو سينمائي من نص/صورة",
        "env_var": "RUNWAY_API_KEY", "key_prefix": "",
        "console_url": "https://dev.runwayml.com",
        "signup_url": "https://dev.runwayml.com",
        "pricing_url": "https://runwayml.com/pricing",
        "pricing_note_ar": "Credits — ~$0.05-0.20/ثانية فيديو",
        "fallback_env": None, "fallback_label_ar": "بديل: Sora 2 من Emergent",
        "category": "media", "priority": "medium",
    },
    {
        "id": "luma",
        "name": "Luma Dream Machine",
        "name_ar": "Luma AI (فيديو + 3D)",
        "powers_ar": "توليد فيديو واقعي + Genie 3D",
        "env_var": "LUMAAI_API_KEY", "key_prefix": "luma-",
        "console_url": "https://lumalabs.ai/dream-machine/api",
        "signup_url": "https://lumalabs.ai",
        "pricing_url": "https://lumalabs.ai/dream-machine/api",
        "pricing_note_ar": "Pay-per-video",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "media", "priority": "low",
    },
    {
        "id": "deepgram",
        "name": "Deepgram STT",
        "name_ar": "Deepgram (تفريغ صوتي سريع)",
        "powers_ar": "تفريغ صوت → نص في زمن حقيقي (أسرع وأرخص من Whisper)",
        "env_var": "DEEPGRAM_API_KEY", "key_prefix": "",
        "console_url": "https://console.deepgram.com",
        "signup_url": "https://console.deepgram.com/signup",
        "pricing_url": "https://deepgram.com/pricing",
        "pricing_note_ar": "$200 رصيد مجاني · $0.0043/دقيقة بعدها",
        "fallback_env": None, "fallback_label_ar": "يستخدم Whisper المحلي",
        "category": "media", "priority": "medium",
    },
    {
        "id": "assemblyai",
        "name": "AssemblyAI",
        "name_ar": "AssemblyAI (تفريغ + Speaker ID)",
        "powers_ar": "تفريغ متقدم مع تمييز المتحدثين + Sentiment",
        "env_var": "ASSEMBLYAI_API_KEY", "key_prefix": "",
        "console_url": "https://www.assemblyai.com/app",
        "signup_url": "https://www.assemblyai.com",
        "pricing_url": "https://www.assemblyai.com/pricing",
        "pricing_note_ar": "$50 رصيد مجاني · $0.37/ساعة",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "media", "priority": "low",
    },
    # ════════════════════════════════════════════════════════════════════
    # 💳 Payments
    # ════════════════════════════════════════════════════════════════════
    {
        "id": "razorpay",
        "name": "Razorpay",
        "name_ar": "Razorpay (الخليج/الهند)",
        "powers_ar": "بديل/إضافي لـStripe — مدفوعات الشرق الأوسط",
        "env_var": "RAZORPAY_KEY_ID", "key_prefix": "rzp_",
        "console_url": "https://dashboard.razorpay.com/app/keys",
        "signup_url": "https://razorpay.com/signup",
        "pricing_url": "https://razorpay.com/pricing",
        "pricing_note_ar": "2% per transaction",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "payments", "priority": "low",
    },
    {
        "id": "lemonsqueezy",
        "name": "Lemon Squeezy",
        "name_ar": "Lemon Squeezy (Subscriptions)",
        "powers_ar": "اشتراكات بسيطة + Merchant of Record (يهتم بالضرائب)",
        "env_var": "LEMONSQUEEZY_API_KEY", "key_prefix": "",
        "console_url": "https://app.lemonsqueezy.com/settings/api",
        "signup_url": "https://www.lemonsqueezy.com",
        "pricing_url": "https://www.lemonsqueezy.com/pricing",
        "pricing_note_ar": "5% per transaction (شامل الضرائب)",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "payments", "priority": "low",
    },
    # ════════════════════════════════════════════════════════════════════
    # 🗄️ Storage / Database
    # ════════════════════════════════════════════════════════════════════
    {
        "id": "supabase",
        "name": "Supabase",
        "name_ar": "Supabase (Postgres + Auth + Storage)",
        "powers_ar": "قاعدة بيانات بديلة + Auth جاهز + تخزين ملفات",
        "env_var": "SUPABASE_URL", "key_prefix": "https://",
        "console_url": "https://supabase.com/dashboard",
        "signup_url": "https://supabase.com",
        "pricing_url": "https://supabase.com/pricing",
        "pricing_note_ar": "مجاني حتى 500MB · $25/شهر للـPro",
        "fallback_env": None, "fallback_label_ar": "اختياري (MongoDB المستخدم حالياً)",
        "category": "storage", "priority": "low",
    },
    {
        "id": "firebase",
        "name": "Firebase",
        "name_ar": "Firebase (Real-time DB + Auth)",
        "powers_ar": "قاعدة بيانات حقيقية الوقت + Push notifications",
        "env_var": "FIREBASE_CREDENTIALS_JSON", "key_prefix": "",
        "console_url": "https://console.firebase.google.com",
        "signup_url": "https://firebase.google.com",
        "pricing_url": "https://firebase.google.com/pricing",
        "pricing_note_ar": "مجاني (Spark plan) · Pay-as-you-go للـBlaze",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "storage", "priority": "low",
    },
    {
        "id": "aws",
        "name": "AWS (S3, Lambda, ...)",
        "name_ar": "AWS — S3, Lambda, SES, SQS",
        "powers_ar": "تخزين S3 + sending emails + serverless functions",
        "env_var": "AWS_ACCESS_KEY_ID", "key_prefix": "AKIA",
        "console_url": "https://console.aws.amazon.com/iam",
        "signup_url": "https://aws.amazon.com",
        "pricing_url": "https://aws.amazon.com/pricing",
        "pricing_note_ar": "Pay-as-you-go · Free tier سنة كاملة",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "storage", "priority": "low",
    },
    {
        "id": "cloudflare",
        "name": "Cloudflare (R2 + Workers)",
        "name_ar": "Cloudflare — R2 Storage + Workers + Stream",
        "powers_ar": "تخزين رخيص (بدون رسوم خروج) + edge functions",
        "env_var": "CLOUDFLARE_API_TOKEN", "key_prefix": "",
        "console_url": "https://dash.cloudflare.com/profile/api-tokens",
        "signup_url": "https://dash.cloudflare.com/sign-up",
        "pricing_url": "https://www.cloudflare.com/plans",
        "pricing_note_ar": "مجاني (10GB R2 + 100k req/يوم Workers)",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "storage", "priority": "medium",
    },
    {
        "id": "mapbox",
        "name": "Mapbox",
        "name_ar": "Mapbox (خرائط متقدمة)",
        "powers_ar": "خرائط + Geocoding + Directions",
        "env_var": "MAPBOX_ACCESS_TOKEN", "key_prefix": "pk.",
        "console_url": "https://account.mapbox.com/access-tokens",
        "signup_url": "https://account.mapbox.com/auth/signup",
        "pricing_url": "https://www.mapbox.com/pricing",
        "pricing_note_ar": "مجاني 50k load/شهر",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "storage", "priority": "low",
    },
    # ════════════════════════════════════════════════════════════════════
    # 📨 Messaging
    # ════════════════════════════════════════════════════════════════════
    {
        "id": "resend",
        "name": "Resend",
        "name_ar": "Resend (إيميلات للمطورين)",
        "powers_ar": "إرسال إيميلات (تأكيد التسجيل، إشعارات، ...)",
        "env_var": "RESEND_API_KEY", "key_prefix": "re_",
        "console_url": "https://resend.com/api-keys",
        "signup_url": "https://resend.com",
        "pricing_url": "https://resend.com/pricing",
        "pricing_note_ar": "3000 إيميل/شهر مجاني · $20/شهر للـ50k",
        "fallback_env": None, "fallback_label_ar": "إيميلات معطّلة",
        "category": "messaging", "priority": "high",
    },
    {
        "id": "sendgrid",
        "name": "SendGrid",
        "name_ar": "SendGrid (إيميلات تقليدي)",
        "powers_ar": "إرسال إيميلات (بديل Resend)",
        "env_var": "SENDGRID_API_KEY", "key_prefix": "SG.",
        "console_url": "https://app.sendgrid.com/settings/api_keys",
        "signup_url": "https://sendgrid.com",
        "pricing_url": "https://sendgrid.com/pricing",
        "pricing_note_ar": "100 إيميل/يوم مجاني · $19.95 للـEssentials",
        "fallback_env": "RESEND_API_KEY", "fallback_label_ar": "بديل لـResend",
        "category": "messaging", "priority": "low",
    },
    {
        "id": "twilio",
        "name": "Twilio (SMS/WhatsApp)",
        "name_ar": "Twilio (SMS + WhatsApp)",
        "powers_ar": "إرسال SMS + WhatsApp + رسائل صوتية",
        "env_var": "TWILIO_ACCOUNT_SID", "key_prefix": "AC",
        "console_url": "https://console.twilio.com",
        "signup_url": "https://www.twilio.com/try-twilio",
        "pricing_url": "https://www.twilio.com/pricing",
        "pricing_note_ar": "$15 رصيد تجريبي · ~$0.0075/SMS",
        "fallback_env": None, "fallback_label_ar": "SMS معطّل",
        "category": "messaging", "priority": "medium",
    },
    {
        "id": "telegram",
        "name": "Telegram Bot",
        "name_ar": "Telegram Bot API",
        "powers_ar": "بوت Telegram للإشعارات/الدعم",
        "env_var": "TELEGRAM_BOT_TOKEN", "key_prefix": "",
        "console_url": "https://t.me/BotFather",
        "signup_url": "https://t.me/BotFather",
        "pricing_url": "https://core.telegram.org/bots",
        "pricing_note_ar": "مجاني تماماً",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "messaging", "priority": "low",
    },
    # ════════════════════════════════════════════════════════════════════
    # 🚀 Deployment & DevOps
    # ════════════════════════════════════════════════════════════════════
    {
        "id": "railway",
        "name": "Railway",
        "name_ar": "Railway (نشر تلقائي)",
        "powers_ar": "الـAuto-Coder يقدر ينشر بنفسه + يدير الـ Services",
        "env_var": "RAILWAY_TOKEN", "key_prefix": "",
        "console_url": "https://railway.app/account/tokens",
        "signup_url": "https://railway.app",
        "pricing_url": "https://railway.app/pricing",
        "pricing_note_ar": "$5 رصيد مجاني · Pay-as-you-go بعدها",
        "fallback_env": None, "fallback_label_ar": "نشر يدوي عبر Git",
        "category": "devops", "priority": "high",
    },
    {
        "id": "vercel",
        "name": "Vercel",
        "name_ar": "Vercel (نشر Frontend)",
        "powers_ar": "نشر الـ frontend برمجياً + Edge functions",
        "env_var": "VERCEL_TOKEN", "key_prefix": "",
        "console_url": "https://vercel.com/account/tokens",
        "signup_url": "https://vercel.com/signup",
        "pricing_url": "https://vercel.com/pricing",
        "pricing_note_ar": "Hobby مجاني · $20/شهر للـ Pro",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "devops", "priority": "medium",
    },
    {
        "id": "sentry",
        "name": "Sentry",
        "name_ar": "Sentry (تتبع الأخطاء)",
        "powers_ar": "رصد الأخطاء في production + Performance monitoring",
        "env_var": "SENTRY_DSN", "key_prefix": "https://",
        "console_url": "https://sentry.io/settings",
        "signup_url": "https://sentry.io/signup",
        "pricing_url": "https://sentry.io/pricing",
        "pricing_note_ar": "5k events/شهر مجاني · $26/شهر بعدها",
        "fallback_env": None, "fallback_label_ar": "الأخطاء بس في logs",
        "category": "devops", "priority": "medium",
    },
    # ════════════════════════════════════════════════════════════════════
    # 📊 Analytics
    # ════════════════════════════════════════════════════════════════════
    {
        "id": "posthog",
        "name": "PostHog",
        "name_ar": "PostHog (Analytics + Session Replay)",
        "powers_ar": "تتبع المستخدمين + إعادة عرض الجلسات + A/B testing",
        "env_var": "POSTHOG_API_KEY", "key_prefix": "phc_",
        "console_url": "https://app.posthog.com/project/settings",
        "signup_url": "https://posthog.com/signup",
        "pricing_url": "https://posthog.com/pricing",
        "pricing_note_ar": "1M events/شهر مجاني · Pay-as-you-go بعدها",
        "fallback_env": None, "fallback_label_ar": "Analytics معطّل",
        "category": "analytics", "priority": "medium",
    },
    {
        "id": "mixpanel",
        "name": "Mixpanel",
        "name_ar": "Mixpanel (Event Analytics)",
        "powers_ar": "تحليلات الأحداث المتقدمة + Funnels + Retention",
        "env_var": "MIXPANEL_TOKEN", "key_prefix": "",
        "console_url": "https://mixpanel.com/settings",
        "signup_url": "https://mixpanel.com/register",
        "pricing_url": "https://mixpanel.com/pricing",
        "pricing_note_ar": "100k MTU/شهر مجاني · $24/شهر بعدها",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "analytics", "priority": "low",
    },
    # ════════════════════════════════════════════════════════════════════
    # 🔐 Auth (بدائل لـ JWT المستخدم حالياً)
    # ════════════════════════════════════════════════════════════════════
    {
        "id": "clerk",
        "name": "Clerk",
        "name_ar": "Clerk (Auth جاهز — Google/Apple/SMS)",
        "powers_ar": "تسجيل دخول اجتماعي + إدارة المستخدمين جاهز",
        "env_var": "CLERK_SECRET_KEY", "key_prefix": "sk_",
        "console_url": "https://dashboard.clerk.com",
        "signup_url": "https://clerk.com",
        "pricing_url": "https://clerk.com/pricing",
        "pricing_note_ar": "مجاني حتى 10k MAU · $25/شهر بعدها",
        "fallback_env": None, "fallback_label_ar": "JWT المستخدم حالياً",
        "category": "auth", "priority": "low",
    },
    {
        "id": "auth0",
        "name": "Auth0 (Okta)",
        "name_ar": "Auth0 (Enterprise auth)",
        "powers_ar": "Auth متقدم + SAML + SSO",
        "env_var": "AUTH0_DOMAIN", "key_prefix": "",
        "console_url": "https://manage.auth0.com",
        "signup_url": "https://auth0.com/signup",
        "pricing_url": "https://auth0.com/pricing",
        "pricing_note_ar": "مجاني 25k MAU · $23/شهر بعدها",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "auth", "priority": "low",
    },
    # ════════════════════════════════════════════════════════════════════
    # 🎮 Specialty
    # ════════════════════════════════════════════════════════════════════
    {
        "id": "meshy",
        "name": "Meshy AI",
        "name_ar": "Meshy AI (نماذج 3D)",
        "powers_ar": "توليد نماذج 3D من نص/صورة",
        "env_var": "MESHY_API_KEY", "key_prefix": "msy_",
        "console_url": "https://www.meshy.ai/settings/api",
        "signup_url": "https://www.meshy.ai",
        "pricing_url": "https://www.meshy.ai/pricing",
        "pricing_note_ar": "$20 رصيد مجاني · $19.99/شهر للـPro",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "media", "priority": "low",
    },
    {
        "id": "thirdweb",
        "name": "Thirdweb (Web3)",
        "name_ar": "Thirdweb (NFT + Web3)",
        "powers_ar": "تكامل Web3 + NFT minting بسهولة",
        "env_var": "THIRDWEB_CLIENT_ID", "key_prefix": "",
        "console_url": "https://thirdweb.com/dashboard/settings/api-keys",
        "signup_url": "https://thirdweb.com",
        "pricing_url": "https://thirdweb.com/pricing",
        "pricing_note_ar": "مجاني (محدود) · $99/شهر للـStarter",
        "fallback_env": None, "fallback_label_ar": "اختياري",
        "category": "data", "priority": "low",
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
        total_used = 0           # high-priority core only
        optional_set = 0          # set keys outside core
        optional_total = 0
        for ig in INTEGRATIONS:
            check = _check(ig["env_var"], ig.get("key_prefix", ""))
            using_fallback = (not check["valid_format"]) and bool(ig.get("fallback_env")) and bool(os.environ.get(ig["fallback_env"], "").strip())
            is_independent = check["valid_format"]
            status_label = (
                "🔓 مستقل" if is_independent
                else ("⚡ يستخدم Emergent" if using_fallback else "❌ غير مفعّل")
            )
            status_color = "green" if is_independent else ("amber" if using_fallback else "red")
            # Score: count only HIGH-priority keys as "core"
            if ig["category"] != "fallback":
                if ig.get("priority") == "high":
                    total_used += 1
                    if is_independent:
                        independent_count += 1
                else:
                    optional_total += 1
                    if is_independent:
                        optional_set += 1
            items.append({
                **ig,
                "configured": check["set"],
                "valid_format": check["valid_format"],
                "preview": check["preview"],
                "key_source": check.get("source"),
                "is_independent": is_independent,
                "using_fallback": using_fallback,
                "status_label": status_label,
                "status_color": status_color,
            })
        return {
            "independent_count": independent_count,
            "total_count": total_used,
            "all_independent": independent_count == total_used and total_used > 0,
            "optional_set": optional_set,
            "optional_total": optional_total,
            "integrations": items,
            "railway_tutorial": RAILWAY_TUTORIAL,
            "owner_id": owner.get("id"),
        }

    @router.get("/integration-tutorial/{integration_id}")
    async def tutorial(integration_id: str, owner=Depends(require_owner)):
        """Return the per-integration tutorial (Arabic steps + YouTube search URL)."""
        # Find integration
        ig = next((i for i in INTEGRATIONS if i["id"] == integration_id), None)
        if not ig:
            raise HTTPException(status_code=404, detail=f"integration '{integration_id}' not found")
        tut = get_tutorial(
            integration_id,
            name=ig.get("name", ""),
            console_url=ig.get("console_url", ""),
        )
        return {
            "ok": True,
            "id": integration_id,
            "integration": {
                "name_ar": ig.get("name_ar"),
                "env_var": ig.get("env_var"),
                "console_url": ig.get("console_url"),
                "pricing_note_ar": ig.get("pricing_note_ar"),
            },
            "tutorial": tut,
            "railway_tutorial": RAILWAY_TUTORIAL,
        }

    return router
