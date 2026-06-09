"""
Per-integration tutorial / help content.

For each integration (by `id`), we provide:
  • steps_ar         — ordered Arabic step-by-step instructions
  • youtube_search   — YouTube search query that opens in new tab (most useful — always finds the latest tutorial)
  • youtube_video_id — (optional) specific embedded video ID when we know a great one
  • screenshots      — (optional) annotated screenshot URLs

Keep this separate from the integration metadata to avoid bloating the
main catalog and to make it easy to translate / extend.
"""
from __future__ import annotations
from typing import Any, Dict


def _yt_search(q: str) -> str:
    from urllib.parse import quote_plus
    return f"https://www.youtube.com/results?search_query={quote_plus(q)}"


# Default Railway "add variable" tutorial — used by every card so the user
# learns the second half of the flow only once.
RAILWAY_TUTORIAL = {
    "title_ar": "كيف تضيف المتغير في Railway",
    "steps_ar": [
        "افتح موقع Railway: https://railway.app",
        "سجّل دخول وافتح المشروع (Zerax)",
        "اختر الخدمة backend (الـService الرئيسي)",
        "اضغط تبويب 'Variables' من فوق",
        "اضغط زر '+ New Variable'",
        "في خانة 'Name' اكتب اسم المتغير بالضبط (مثلاً: OPENROUTER_API_KEY)",
        "في خانة 'Value' الصق المفتاح اللي نسخته",
        "اضغط 'Add' — Railway راح يعيد deploy تلقائياً (~3 دقايق)",
        "ارجع لصفحة الاستقلالية واضغط 'تحديث' للتأكد إن الشارة صارت خضراء",
    ],
    "youtube_search": _yt_search("how to add environment variable in railway tutorial"),
}


# Per-integration tutorial. Keyed by integration `id`.
TUTORIALS: Dict[str, Dict[str, Any]] = {
    "openrouter": {
        "title_ar": "كيف تحصل على مفتاح OpenRouter",
        "intro_ar": "OpenRouter يعطيك وصول لـ300+ موديل (DeepSeek, Llama, Mistral, Qwen, Gemma) من API واحدة بنفس صيغة OpenAI. ممتاز للتنوع وأرخص من OpenAI أحياناً.",
        "steps_ar": [
            "افتح https://openrouter.ai/keys",
            "سجّل دخول بـGoogle أو GitHub",
            "اضغط 'Create Key' فوق",
            "اكتب اسم للمفتاح (مثلاً: Zerax Production)",
            "اختر credit limit (اتركه فاضي = بدون حد)",
            "اضغط 'Create' — راح يظهر المفتاح يبدأ بـ 'sk-or-v1-...'",
            "انسخه فوراً (بعد ما تسكّر الصفحة ما تقدر تشوفه)",
            "اشحن الحساب: Settings → Credits → Add credit ($5 يكفي لشهور)",
        ],
        "youtube_search": _yt_search("OpenRouter API key tutorial how to use"),
    },
    "anthropic": {
        "title_ar": "كيف تحصل على مفتاح Anthropic Claude",
        "intro_ar": "Claude هو الذكاء الرئيسي للـAuto-Coder. أفضل في البرمجة من GPT حالياً.",
        "steps_ar": [
            "افتح https://console.anthropic.com",
            "سجّل دخول أو سجّل حساب جديد",
            "اشحن الحساب: Settings → Billing → Add credit ($5 يكفي للبداية)",
            "روح: Settings → API Keys → Create Key",
            "اكتب اسم (مثلاً: Zerax)، اختر Permissions = All",
            "اضغط 'Add' وانسخ المفتاح (يبدأ بـ sk-ant-...)",
        ],
        "youtube_search": _yt_search("Anthropic Claude API key get tutorial"),
    },
    "openai": {
        "title_ar": "كيف تحصل على مفتاح OpenAI",
        "intro_ar": "OpenAI يفعّل GPT-4o و GPT-5.5 + توليد صور gpt-image-1 + تفريغ صوت Whisper + TTS.",
        "steps_ar": [
            "افتح https://platform.openai.com/api-keys",
            "سجّل دخول",
            "اشحن الحساب: Settings → Billing → Add to credit balance ($5 يكفي)",
            "اضغط '+ Create new secret key'",
            "اكتب اسم، اختر Permissions = All, اضغط 'Create'",
            "انسخ المفتاح فوراً (يبدأ بـ sk-...) — ما يتعرض مرة ثانية",
        ],
        "youtube_search": _yt_search("OpenAI API key get tutorial billing"),
    },
    "gemini": {
        "title_ar": "كيف تحصل على مفتاح Google Gemini (مجاني!)",
        "intro_ar": "Gemini 2.5 Flash مجاني تماماً حتى 1500 طلب/يوم. ممتاز للذكاء الخفيف.",
        "steps_ar": [
            "افتح https://aistudio.google.com/app/apikey",
            "سجّل دخول بحساب Google",
            "اضغط 'Create API key'",
            "اختر مشروع (أو 'Create new project')",
            "انسخ المفتاح المُنشأ",
        ],
        "youtube_search": _yt_search("Google Gemini API key free tutorial"),
    },
    "groq": {
        "title_ar": "كيف تحصل على مفتاح Groq (مجاني وسريع جداً)",
        "intro_ar": "Groq يشغّل Llama 3.3 70B بسرعة 500+ tokens/sec. مجاني لكن محدود الـrate.",
        "steps_ar": [
            "افتح https://console.groq.com",
            "سجّل دخول بـGoogle أو GitHub",
            "روح: API Keys → Create API Key",
            "اكتب اسم، اضغط Submit",
            "انسخ المفتاح (يبدأ بـ gsk_)",
        ],
        "youtube_search": _yt_search("Groq API key tutorial fast llama"),
    },
    "elevenlabs": {
        "title_ar": "كيف تحصل على مفتاح ElevenLabs",
        "intro_ar": "ElevenLabs يولّد أصوات طبيعية جداً + موسيقى محيطية. 10k حرف/شهر مجاني.",
        "steps_ar": [
            "افتح https://elevenlabs.io/sign-up",
            "سجّل بإيميل",
            "أكّد الإيميل",
            "روح: https://elevenlabs.io/app/settings/api-keys",
            "اضغط '+ Create API Key'",
            "اكتب اسم، اختر Permissions = All endpoints",
            "انسخ المفتاح",
        ],
        "youtube_search": _yt_search("ElevenLabs API key tutorial voice"),
    },
    "stripe": {
        "title_ar": "كيف تحصل على مفتاح Stripe (للمدفوعات)",
        "intro_ar": "Stripe يفعّل اشتراكات Studio والمدفوعات. لازم تكمل التحقق التجاري قبل ما يقبل بطاقات حقيقية.",
        "steps_ar": [
            "افتح https://dashboard.stripe.com/register",
            "سجّل بإيميل وفعّل الحساب",
            "املأ بيانات الشركة (Settings → Business settings)",
            "اضغط 'Activate payments' وفعّل البيانات البنكية",
            "روح: https://dashboard.stripe.com/apikeys",
            "انسخ 'Secret key' (يبدأ بـ sk_live_... أو sk_test_... للتجربة)",
        ],
        "youtube_search": _yt_search("Stripe API key tutorial setup"),
    },
    "fal": {
        "title_ar": "كيف تحصل على مفتاح fal.ai",
        "intro_ar": "fal.ai أفضل منصة توليد صور/فيديو حالياً (FLUX, SDXL, Veo, ...). Pay-per-image رخيص.",
        "steps_ar": [
            "افتح https://fal.ai",
            "سجّل بحساب Google أو GitHub",
            "اشحن الرصيد: $5 يكفي لمئات الصور",
            "روح: https://fal.ai/dashboard/keys",
            "اضغط '+ Add API Key'، اكتب اسم",
            "انسخ المفتاح",
        ],
        "youtube_search": _yt_search("fal.ai API key tutorial image generation"),
    },
    "huggingface": {
        "title_ar": "كيف تحصل على مفتاح Hugging Face (مجاني)",
        "intro_ar": "وصول لآلاف الموديلات + Inference API. مجاني لكن محدود الـrate.",
        "steps_ar": [
            "افتح https://huggingface.co/join",
            "سجّل حساب",
            "روح: https://huggingface.co/settings/tokens",
            "اضغط 'New token'",
            "اكتب اسم، اختر Role = Read (أو Write للرفع)",
            "انسخ التوكن (يبدأ بـ hf_)",
        ],
        "youtube_search": _yt_search("Hugging Face token tutorial"),
    },
    "resend": {
        "title_ar": "كيف تحصل على مفتاح Resend (إيميلات)",
        "intro_ar": "Resend أحسن خدمة إيميلات للمطورين. 3000 إيميل/شهر مجاني.",
        "steps_ar": [
            "افتح https://resend.com/signup",
            "سجّل بإيميل",
            "أكّد الإيميل",
            "أضف الدومين تبعك (Add Domain) وحقّق الـDNS records",
            "روح: https://resend.com/api-keys",
            "اضغط 'Create API Key'، اختر Permissions = Full Access",
            "انسخ المفتاح (يبدأ بـ re_)",
        ],
        "youtube_search": _yt_search("Resend API key email tutorial"),
    },
    "railway": {
        "title_ar": "كيف تحصل على Railway Token",
        "intro_ar": "Railway Token يخلّي الذكاء يدير الـ deployments بنفسه (يعيد تشغيل، يفحص logs، إلخ).",
        "steps_ar": [
            "افتح https://railway.app/account/tokens",
            "سجّل دخول",
            "اضغط 'Create New Token'",
            "اكتب اسم (مثلاً: Zerax Auto-Coder)",
            "اختر الـProject scope (يفضّل Account-wide لو تبي وصول كامل)",
            "اضغط Create وانسخ التوكن",
        ],
        "youtube_search": _yt_search("Railway API token tutorial"),
    },
    "vercel": {
        "title_ar": "كيف تحصل على Vercel Token",
        "steps_ar": [
            "افتح https://vercel.com/account/tokens",
            "اضغط 'Create' → اختر Scope (Personal Account)",
            "اكتب اسم، اختر مدّة الصلاحية (No expiration يفضّل)",
            "انسخ التوكن",
        ],
        "youtube_search": _yt_search("Vercel API token tutorial"),
    },
    "sentry": {
        "title_ar": "كيف تحصل على Sentry DSN",
        "intro_ar": "Sentry يرصد أخطاء production تلقائياً + يعطيك stack traces مفصّلة.",
        "steps_ar": [
            "افتح https://sentry.io/signup",
            "أنشئ Organization + Project (اختر Platform = Python)",
            "بعد إنشاء الـProject، Sentry يعطيك DSN URL مباشرة",
            "انسخ الـDSN (يبدأ بـ https://...@sentry.io/...)",
            "متاح أيضاً في: Settings → Projects → [project] → Client Keys",
        ],
        "youtube_search": _yt_search("Sentry DSN setup tutorial"),
    },
    "supabase": {
        "title_ar": "كيف تحصل على Supabase keys",
        "intro_ar": "Supabase = Postgres + Auth + Storage جاهز. مجاني حتى 500MB.",
        "steps_ar": [
            "افتح https://supabase.com → Start your project",
            "سجّل بـGitHub",
            "أنشئ Project جديد (اختر region قريب)",
            "بعد البناء (دقيقتين)، روح: Project Settings → API",
            "انسخ 'Project URL' → SUPABASE_URL",
            "انسخ 'anon public' key → SUPABASE_KEY",
        ],
        "youtube_search": _yt_search("Supabase project setup tutorial"),
    },
    "deepgram": {
        "title_ar": "كيف تحصل على مفتاح Deepgram",
        "intro_ar": "تفريغ صوتي حقيقي الوقت أسرع وأرخص من Whisper. $200 رصيد مجاني عند التسجيل.",
        "steps_ar": [
            "افتح https://console.deepgram.com/signup",
            "سجّل حساب",
            "بعد التحقق، روح: API Keys",
            "اضغط 'Create a New API Key'",
            "اكتب اسم، اختر Permissions = Member",
            "انسخ المفتاح",
        ],
        "youtube_search": _yt_search("Deepgram API key tutorial speech-to-text"),
    },
    "twilio": {
        "title_ar": "كيف تحصل على Twilio credentials",
        "intro_ar": "Twilio يفعّل SMS و WhatsApp. $15 رصيد تجريبي عند التسجيل.",
        "steps_ar": [
            "افتح https://www.twilio.com/try-twilio",
            "سجّل حساب وأكّد رقم جوالك",
            "من Dashboard انسخ:",
            "  • Account SID → TWILIO_ACCOUNT_SID",
            "  • Auth Token → TWILIO_AUTH_TOKEN",
            "اشتري رقم هاتف للإرسال (Phone Numbers → Buy)",
        ],
        "youtube_search": _yt_search("Twilio account SID auth token tutorial"),
    },
    "telegram": {
        "title_ar": "كيف تنشئ بوت تليجرام",
        "intro_ar": "Telegram Bots مجانية تماماً ومثالية للإشعارات.",
        "steps_ar": [
            "افتح تطبيق Telegram",
            "ابحث عن @BotFather وابدأ محادثة",
            "اكتب /newbot",
            "اعطه اسم البوت (مثلاً: Zerax Notifier)",
            "اعطه username ينتهي بـ bot (مثلاً: zerax_alerts_bot)",
            "راح يرجع لك Token — انسخه",
        ],
        "youtube_search": _yt_search("Telegram BotFather create bot tutorial"),
    },
    "posthog": {
        "title_ar": "كيف تحصل على مفتاح PostHog",
        "intro_ar": "PostHog يتتبع المستخدمين + Session replay + A/B testing. 1M event/شهر مجاني.",
        "steps_ar": [
            "افتح https://posthog.com/signup",
            "سجّل حساب",
            "أنشئ Project جديد",
            "في Project Settings انسخ 'Project API Key'",
        ],
        "youtube_search": _yt_search("PostHog setup project API key tutorial"),
    },
}


# Catch-all default for integrations without a specific tutorial
def get_tutorial(integration_id: str, name: str = "", console_url: str = "") -> Dict[str, Any]:
    if integration_id in TUTORIALS:
        return TUTORIALS[integration_id]
    # Generic fallback
    return {
        "title_ar": f"كيف تحصل على مفتاح {name or integration_id}",
        "intro_ar": "نسخة سريعة — التفاصيل تختلف من خدمة لخدمة. اتبع الخطوات أو ابحث الفيديو.",
        "steps_ar": [
            f"افتح صفحة الـAPI Keys: {console_url}" if console_url else "افتح صفحة الـAPI Keys للخدمة",
            "سجّل حساب جديد لو ما عندك",
            "أكّد الإيميل + فعّل الـbilling لو الخدمة مدفوعة",
            "ابحث عن قسم 'API Keys' أو 'Developer' أو 'Tokens'",
            "أنشئ مفتاح جديد بصلاحيات كاملة",
            "انسخ المفتاح فوراً (أكثر الخدمات ما تعرضه مرة ثانية)",
        ],
        "youtube_search": _yt_search(f"{name or integration_id} API key tutorial"),
    }
