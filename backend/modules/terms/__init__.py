"""Terms & Conditions per-section acceptance.

Stores a tamper-evident record of every legal acceptance a user makes in
`db.terms_acceptances` so we can prove (in any dispute / chargeback case)
that the user explicitly agreed to the section's terms BEFORE using it.

Sections currently shipped: websites, apps, images, videos, longform,
games, deploy, payments.

Each terms document is versioned. If we update the legal text we bump
TERMS_VERSION for that section, and users are asked to re-accept.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel


# ─── Terms catalogue ──────────────────────────────────────────────────────
# Each key = (section_id, locale). Sections must match what the frontend
# passes via TermsGate. Locale fallback chain: requested → en → ar.

TERMS_VERSION: Dict[str, str] = {
    "websites": "1.0.0",
    "apps": "1.0.0",
    "images": "1.0.0",
    "videos": "1.0.0",
    "longform": "1.0.0",
    "games": "1.0.0",
    "deploy": "1.0.0",
    "payments": "1.0.0",
    "site_to_app": "1.0.0",
}

# Localised bodies — Arabic + English shipped first; agent can extend later.
TERMS_BODIES: Dict[str, Dict[str, Dict[str, str]]] = {
    "websites": {
        "ar": {
            "title": "شروط استخدام استوديو المواقع",
            "intro": "قبل ما تبدأ ببناء موقعك، نحتاج موافقتك على النقاط التالية:",
            "bullets": [
                "أنت المسؤول الوحيد عن دقّة المحتوى اللي تطلبه من زنركس AI (نصوص، صور، أسعار، روابط).",
                "زنركس يقدّم لك أفضل أدوات الذكاء الاصطناعي بأعلى جودة، لكن جودة النتيجة تعتمد على وضوح طلباتك ومعلوماتك.",
                "زنركس غير مسؤول عن أي خسائر تجارية أو قانونية ناتجة عن أخطاء معلومات قدّمتها أنت.",
                "ما نقبل أي استرداد مالي لأخطاء سببها معلومات ناقصة أو غير صحيحة منك.",
                "تستطيع طلب التعديل والتحسين عبر الشات ما دام مشروعك نشط.",
                "أي محتوى مخالف للقوانين السعودية/الدولية (تحريض، إباحة، نصب، انتهاك ملكية فكرية) راح يُرفض ويُحذف الحساب.",
            ],
            "agreement": "أوافق على هذه الشروط وأقرّ أنني قرأتها بعناية.",
        },
        "en": {
            "title": "Websites Studio — Terms of Service",
            "intro": "Before you start building your website, please review and accept the following:",
            "bullets": [
                "You are solely responsible for the accuracy of content you ask Zenrex AI to produce (texts, images, prices, links).",
                "Zenrex provides best-in-class AI tools, but the quality of the result depends on how clearly you communicate your needs.",
                "Zenrex is not liable for any commercial or legal losses caused by information you supplied incorrectly.",
                "Refunds are not granted for errors caused by missing or incorrect information you provided.",
                "You can request edits and improvements anytime your project is active.",
                "Content that violates Saudi or international law (incitement, obscenity, fraud, IP infringement) will be rejected and your account suspended.",
            ],
            "agreement": "I have read and accept these terms.",
        },
    },
    "apps": {
        "ar": {
            "title": "شروط استوديو التطبيقات",
            "intro": "تطبيقات الجوال التي تُبنى هنا هي تطبيقات PWA قابلة للتثبيت — نوضّح التالي:",
            "bullets": [
                "تطبيقاتك تُبنى بتقنية PWA — قابلة للتثبيت على iPhone و Android مباشرة من المتصفح، بدون متجر تطبيقات.",
                "إذا أردت رفع التطبيق إلى App Store أو Google Play، تحتاج اشتراك مطوّر لدى Apple ($99/سنة) أو Google ($25 مرّة واحدة) — هذي رسوم على عاتقك أنت.",
                "زنركس مسؤول عن جودة الكود، لكن قبول التطبيق في المتاجر يخضع لسياسات المتاجر، وما نقدر نضمن القبول من طرف ثالث.",
                "كل البيانات اللي يدخلها مستخدمي تطبيقك تكون مسؤوليتك أنت (حسب قانون حماية البيانات السعودي PDPL والقوانين الدولية مثل GDPR).",
                "ما نقبل استرداد مالي بسبب اختلاف توقّعاتك عن النتيجة، طالما الكود يعمل بدون أخطاء فنية.",
            ],
            "agreement": "أوافق على شروط استوديو التطبيقات.",
        },
        "en": {
            "title": "Apps Studio — Terms of Service",
            "intro": "Apps built here are Progressive Web Apps (PWA). Please review:",
            "bullets": [
                "Your apps are built as PWAs — installable on iPhone and Android directly from the browser, no app store needed.",
                "To publish on App Store or Google Play, you need a developer subscription ($99/yr Apple or $25 one-time Google) — paid by you.",
                "Zenrex guarantees code quality, but store acceptance follows store policies — we cannot guarantee approval.",
                "Any data collected by your app's end-users is your responsibility (Saudi PDPL, GDPR, CCPA).",
                "Refunds are not provided for differences between your expectations and the result, as long as the code works without technical defects.",
            ],
            "agreement": "I accept the Apps Studio terms.",
        },
    },
    "images": {
        "ar": {
            "title": "شروط استوديو الصور",
            "intro": "قبل توليد الصور بالذكاء الاصطناعي:",
            "bullets": [
                "الصور تُولَّد بناءً على وصفك أنت — جودتها تعتمد على دقّة وصفك.",
                "زنركس يستخدم أفضل نماذج توليد الصور حالياً، لكن النماذج قد تنتج نتائج غير متوقّعة أحياناً.",
                "أنت المسؤول عن استخدام الصور لأغراض مشروعة فقط — ممنوع توليد صور مسيئة، مخالفة للقوانين، أو تنتهك حقوق الآخرين.",
                "ما نقبل استرداد رسوم توليد إذا تم التوليد فعلياً، حتى لو ما عجبتك النتيجة — تقدر تعيد التوليد بوصف أوضح.",
                "زنركس لا يحتفظ بحقوق الصور المولّدة، الحقوق تعود لك.",
            ],
            "agreement": "أوافق على شروط استوديو الصور.",
        },
        "en": {
            "title": "Images Studio — Terms of Service",
            "intro": "Before generating images with AI:",
            "bullets": [
                "Images are generated based on your prompts — quality depends on the clarity of your description.",
                "Zenrex uses state-of-the-art image generation models, but models may sometimes produce unexpected results.",
                "You are solely responsible for lawful use — generating offensive, illegal, or rights-infringing content is prohibited.",
                "Generation fees are not refundable once images are generated, even if you don't like the result — you can re-generate with a clearer prompt.",
                "Zenrex does not retain rights to generated images; the rights are yours.",
            ],
            "agreement": "I accept the Images Studio terms.",
        },
    },
    "videos": {
        "ar": {
            "title": "شروط استوديو الفيديو",
            "intro": "تذكّر هذي النقاط قبل ما تبدأ بصنع فيديوهات:",
            "bullets": [
                "الفيديوهات تُولَّد بنماذج AI متطوّرة. كل فيديو يستهلك رصيد من حسابك حسب طوله وجودته.",
                "أنت المسؤول عن السكربت والمحتوى — زنركس لا يراجع المحتوى لأسباب قانونية في كل دولة.",
                "ممنوع استخدام النظام لتوليد فيديوهات Deepfake لشخصيات حقيقية بدون إذنهم.",
                "ما نقبل استرداد رصيد بعد بدء عملية التوليد. لو فشل التوليد فنياً، يُعاد الرصيد تلقائياً.",
                "حقوق الفيديوهات المولّدة لك — لكن لو احتوت على عناصر طرف ثالث (موسيقى، شعارات)، تأكد من امتلاكك للحقوق.",
            ],
            "agreement": "أوافق على شروط استوديو الفيديو.",
        },
        "en": {
            "title": "Video Studio — Terms of Service",
            "intro": "Please review before creating videos:",
            "bullets": [
                "Videos are generated by advanced AI models. Each video consumes credits based on length and quality.",
                "You are responsible for the script and content — Zenrex does not pre-screen content for every jurisdiction's laws.",
                "Generating deepfake content of real persons without consent is strictly prohibited.",
                "Credits are not refundable once generation has started. Failed renders are auto-refunded.",
                "Generated video rights are yours — but if your video uses third-party elements (music, logos), ensure you own the rights.",
            ],
            "agreement": "I accept the Video Studio terms.",
        },
    },
    "longform": {
        "ar": {
            "title": "شروط الأفلام والفيديو الطويل",
            "intro": "الأفلام والفيديوهات الطويلة تستهلك موارد كبيرة:",
            "bullets": [
                "الفيلم الواحد قد يستغرق ساعات في التوليد ويستهلك رصيد كبير حسب الجودة والطول.",
                "ينصح بحفظ سكربتك ومراجعته قبل التوليد النهائي — التعديل بعد توليد فيلم كامل يكلّف نفس السعر.",
                "ما نقبل استرداد بعد اكتمال التوليد، حتى لو غيّرت رأيك.",
                "حقوق الفيلم النهائي لك بالكامل.",
            ],
            "agreement": "أوافق على شروط الأفلام.",
        },
        "en": {
            "title": "Long-Form Video & Films — Terms",
            "intro": "Films and long videos consume significant resources:",
            "bullets": [
                "A single film may take hours to render and consume substantial credits based on length and quality.",
                "We recommend reviewing your script before final render — re-rendering after a full film costs the same.",
                "No refunds after generation completes, even if you change your mind.",
                "Final film rights belong entirely to you.",
            ],
            "agreement": "I accept the Long-Form terms.",
        },
    },
    "games": {
        "ar": {
            "title": "شروط استوديو الألعاب",
            "intro": "تذكّر النقاط التالية قبل بناء لعبتك:",
            "bullets": [
                "الألعاب تُبنى بـ HTML5/JavaScript قابلة للتشغيل على المتصفح ومحول إلى تطبيقات لاحقاً.",
                "أنت المسؤول عن أن لعبتك ما تخالف قوانين القمار في الدول اللي يلعبها فيها مستخدمين.",
                "زنركس يستخدم أفضل أدوات تطوير الألعاب بـ AI، لكن جودة اللعبة تعتمد على وضوح تصميمك ومعلوماتك.",
                "ما نقبل استرداد إلا في حالة عيب فني مثبَّت في كود زنركس.",
            ],
            "agreement": "أوافق على شروط استوديو الألعاب.",
        },
        "en": {
            "title": "Games Studio — Terms",
            "intro": "Before building your game:",
            "bullets": [
                "Games are built in HTML5/JavaScript playable in any browser, and can be wrapped as apps later.",
                "You are responsible for ensuring your game complies with gambling laws in countries it will be played in.",
                "Zenrex uses best-in-class AI game-dev tools, but quality depends on your design clarity.",
                "Refunds only granted for verified technical defects in Zenrex code.",
            ],
            "agreement": "I accept the Games Studio terms.",
        },
    },
    "deploy": {
        "ar": {
            "title": "شروط النشر والاستضافة",
            "intro": "قبل نشر مشروعك:",
            "bullets": [
                "النشر يربط مشروعك بمزوّدي خدمة خارجيين (Vercel, Cloudflare, GitHub) — لكل واحد منهم شروطه الخاصة اللي يجب أن تقرأها.",
                "تكاليف الاستضافة بعد الاستخدام الأساسي قد تُحتسب من زنركس أو من المزوّد مباشرة.",
                "الانقطاعات الناتجة عن مزوّد خارجي ليست مسؤولية زنركس — نضمن جودة الكود فقط.",
                "للنشر على دومين مخصص، تحتاج تربط الدومين بنفسك أو تطلب من زنركس مساعدتك.",
            ],
            "agreement": "أوافق على شروط النشر.",
        },
        "en": {
            "title": "Deployment & Hosting — Terms",
            "intro": "Before deploying your project:",
            "bullets": [
                "Deployment connects your project to third-party providers (Vercel, Cloudflare, GitHub) — each has its own terms you must read.",
                "Hosting costs beyond basic usage may be billed by Zenrex or directly by the provider.",
                "Downtime caused by third-party providers is not Zenrex's responsibility — we guarantee code quality only.",
                "To deploy to a custom domain, you'll need to connect the domain yourself or request Zenrex's help.",
            ],
            "agreement": "I accept the Deployment terms.",
        },
    },
    "payments": {
        "ar": {
            "title": "شروط المدفوعات",
            "intro": "قبل أي عملية دفع:",
            "bullets": [
                "المدفوعات تُعالَج عبر Stripe (مزوّد دولي معتمَد). معلومات بطاقتك ما تُحفظ عند زنركس أبداً.",
                "أسعار الباقات قابلة للتغيير بإشعار مسبق ٣٠ يوم. الاشتراكات النشطة محمية بالسعر الأصلي حتى التجديد.",
                "الاسترداد متاح خلال ٧ أيام من الدفع فقط إذا لم تستخدم الميزات المدفوعة. بعد الاستخدام، لا استرداد.",
                "أنت مسؤول عن صحّة بياناتك الضريبية إن طلبتها (VAT number, sales tax).",
            ],
            "agreement": "أوافق على شروط المدفوعات.",
        },
        "en": {
            "title": "Payments — Terms",
            "intro": "Before any payment:",
            "bullets": [
                "Payments are processed via Stripe (certified global provider). Your card details are never stored at Zenrex.",
                "Plan pricing may change with 30-day notice. Active subscriptions are protected at the original price until renewal.",
                "Refunds within 7 days of payment are available only if you haven't used the paid features. After use, no refunds.",
                "You are responsible for the accuracy of your tax info if provided (VAT number, sales tax).",
            ],
            "agreement": "I accept the Payments terms.",
        },
    },
    "site_to_app": {
        "ar": {
            "title": "شروط محوّل المواقع إلى تطبيقات",
            "intro": "قبل تحويل موقعك إلى تطبيق جوال:",
            "bullets": [
                "زنركس يفحص موقعك القائم ويولّد نسخة تطبيق (PWA / Native) بناءً على محتواه.",
                "إذا الموقع يحتوي على عناصر محمية (محتوى مسروق، حقوق طرف ثالث)، أنت المسؤول قانونياً — زنركس مجرد أداة.",
                "بعض ميزات المواقع المعقدة (Forms معقدة، WebGL، Backend خاص) قد تتطلّب إعادة بناء يدوية في التطبيق.",
                "زنركس يخبرك بكل ميزة لا يقدر يحوّلها تلقائياً قبل البدء.",
                "ما نقبل استرداد بعد بدء عملية التحويل.",
            ],
            "agreement": "أوافق على شروط المحوّل.",
        },
        "en": {
            "title": "Site-to-App Converter — Terms",
            "intro": "Before converting your site to an app:",
            "bullets": [
                "Zenrex scans your existing site and generates an app version (PWA / Native) based on its content.",
                "If your site contains protected elements (stolen content, third-party rights), you are legally responsible — Zenrex is just a tool.",
                "Some complex web features (advanced forms, WebGL, custom backends) may require manual re-implementation in the app.",
                "Zenrex tells you about every feature it can't auto-convert before starting.",
                "Refunds are not granted after the conversion process has started.",
            ],
            "agreement": "I accept the Converter terms.",
        },
    },
}


# ─── Pydantic ─────────────────────────────────────────────────────────────
class TermsAcceptanceIn(BaseModel):
    section: str
    locale: str = "ar"


def make_terms_router(db, get_current_user):
    router = APIRouter(prefix="/api/terms", tags=["terms"])

    @router.get("/content")
    async def terms_content(section: str, locale: str = "ar"):
        if section not in TERMS_VERSION:
            raise HTTPException(404, f"Unknown section: {section}")
        bodies = TERMS_BODIES.get(section, {})
        # Fallback chain: requested → en → ar
        body = bodies.get(locale) or bodies.get("en") or bodies.get("ar")
        if not body:
            raise HTTPException(404, "No content for this section")
        return {
            "section": section,
            "version": TERMS_VERSION[section],
            "locale": locale if locale in bodies else ("en" if "en" in bodies else "ar"),
            **body,
        }

    @router.get("/check")
    async def terms_check(section: str, user=Depends(get_current_user)):
        if section not in TERMS_VERSION:
            raise HTTPException(404, "Unknown section")
        latest = TERMS_VERSION[section]
        doc = await db.terms_acceptances.find_one(
            {"user_id": user["user_id"], "section": section, "version": latest},
            {"_id": 0, "accepted_at": 1, "locale": 1, "version": 1},
        )
        return {
            "accepted": bool(doc),
            "version": latest,
            "accepted_doc": doc,
        }

    @router.post("/accept")
    async def terms_accept(payload: TermsAcceptanceIn, request: Request, user=Depends(get_current_user)):
        if payload.section not in TERMS_VERSION:
            raise HTTPException(404, "Unknown section")
        version = TERMS_VERSION[payload.section]
        record = {
            "user_id": user["user_id"],
            "section": payload.section,
            "version": version,
            "locale": payload.locale,
            "accepted_at": datetime.now(timezone.utc).isoformat(),
            "ip": (request.headers.get("x-forwarded-for") or request.client.host or "").split(",")[0].strip(),
            "user_agent": request.headers.get("user-agent", "")[:300],
        }
        # Idempotent: upsert on (user_id, section, version) so re-clicks
        # don't pile duplicates.
        await db.terms_acceptances.update_one(
            {"user_id": user["user_id"], "section": payload.section, "version": version},
            {"$set": record},
            upsert=True,
        )
        return {"ok": True, "version": version, "section": payload.section}

    @router.get("/my-acceptances")
    async def my_acceptances(user=Depends(get_current_user)):
        cur = db.terms_acceptances.find(
            {"user_id": user["user_id"]},
            {"_id": 0, "section": 1, "version": 1, "locale": 1, "accepted_at": 1},
        ).sort("accepted_at", -1)
        return {"items": await cur.to_list(length=100)}

    return router
