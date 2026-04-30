"""
Zitex AI Avatar — premium animated assistant module.

Provides:
    POST /api/avatar/chat                  — chat with Zitex main-site avatar (Zara/Layla)
    GET  /api/merchant/avatar/pricing      — pricing & trial info
    GET  /api/merchant/avatar/me           — owner fetches their avatar config
    POST /api/merchant/avatar/start-trial  — owner starts 14-day free trial (one-time)
    POST /api/merchant/avatar/subscribe    — owner subscribes (100 points/month)
    PUT  /api/merchant/avatar/customize    — owner customizes (name/voice/hide) — 30 points/change
    POST /api/merchant/avatar/hide         — owner hides/shows the avatar on their site
    GET  /api/merchant/avatar/{slug}       — public config lookup
    POST /api/merchant/avatar/{slug}/chat  — public visitor chat with merchant's avatar

Pricing model:
    - 14-day FREE TRIAL (one-time per project) — unlimited avatar use during trial
    - After trial: 100 points/month to keep avatar active
    - Each customization (name/voice/hide-toggle): 30 points — but FREE during trial
"""
from __future__ import annotations
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ===== Pricing =====
AVATAR_MONTHLY_COST = 100       # points/month after trial
AVATAR_CUSTOMIZE_COST = 30      # points per customization (name/voice/hide) after trial
AVATAR_TRIAL_DAYS = 14          # one-time free trial per project

# ===== Available voices (OpenAI TTS) =====
AVAILABLE_VOICES = [
    {"id": "nova",    "label": "نوفا (أنثى دافئة)",     "gender": "female"},
    {"id": "shimmer", "label": "شيمر (أنثى ناعمة)",      "gender": "female"},
    {"id": "alloy",   "label": "ألوي (محايد واضح)",      "gender": "neutral"},
    {"id": "echo",    "label": "إيكو (ذكر هادئ)",        "gender": "male"},
    {"id": "onyx",    "label": "أونيكس (ذكر عميق)",      "gender": "male"},
    {"id": "fable",   "label": "فيبل (أنثى حيوية)",      "gender": "female"},
]

# ===== System messages =====
# Saudi dialect — natural, friendly, warm
ZITEX_AVATAR_SYSTEM = """أنت زارا أو ليلى — مساعدة صوتية على منصة Zitex.

قواعد الكلام (مهم جداً):
- لهجة سعودية طبيعية فقط: "هلا" "وش" "ابغى" "تبي" "شلون" "أبشر" "تمام"
- ردود قصيرة جداً جداً: 1-2 جملة فقط (الصوت يسمع، فلا تطول)
- لا emojis في الرد (الصوت يقرأها بشكل غريب)
- اسم المستخدم لو موجود استخدميه مباشرة
- بدون مقدمات ولا تكرار

شخصيتك:
- زارا: مرحة حماسية ("ابشر يا قلبي!" "يا سلام!")
- ليلى: هادئة أنيقة ("تمام معاك" "أنا أسمعك")

خدمات Zitex (لو سأل):
- مواقع جاهزة (25 تخصص)
- توليد صور AI (5 نقاط)
- توليد فيديو AI (4-12 نقطة/ثانية)
- مساعدة ذكية لمتجرك

Intent routing — لو طلب شي محدد، فهمي القصد:
- يبغى صورة → اكتشفي الموضوع وردي: "تمام، خلنا نسوي صورة [الموضوع]. أنقلك للاستوديو الآن"
- يبغى فيديو → "تمام، فيديو [النوع]. أحوّلك للويزارد"
- يبغى موقع → "ممتاز، موقع [النوع]. أوديك لصفحة المواقع"

اللهجة: سعودي خفيف فقط — لا فصحى ثقيلة.
"""


def _merchant_system_message(config: Dict[str, Any]) -> str:
    shop_name = config.get("shop_name", "المتجر")
    avatar_name = config.get("avatar_name", "المساعدة الذكية")
    products = config.get("products_description", "")
    pricing = config.get("pricing_info", "")
    faq = config.get("faq", "")
    tone = config.get("tone", "saudi_friendly")

    tone_block = ""
    if tone == "saudi_friendly":
        tone_block = """⚠️ تتكلمين باللهجة السعودية الطبيعية (خليجي):
- "هلا وغلا!" "وش تبي؟" "ابشر" "على راسي" "يعطيك العافية"
- استخدمي "تبي/ابغى/شلون/وش" بدل الفصحى
- emoji قليل لطيف ✨"""
    elif tone == "formal":
        tone_block = "أسلوبك: عربي فصيح راقٍ ومحترم."
    else:
        tone_block = "أسلوبك: عربي ودود بسيط."

    return f"""أنت {avatar_name} — المساعدة الذكية لمتجر '{shop_name}'.

{tone_block}

عن المتجر:
{products}

الأسعار:
{pricing}

الأسئلة المتكررة:
{faq}

قواعد الكلام:
- ردود قصيرة (1-3 جمل) مفيدة
- لو سُئلتِ عن منتج مش عندنا: اعتذري بلطف واقترحي بديل
- شجّعي العميل يكمّل الطلب بدون ضغط
- ما تعرفين معلومة؟ قولي بصراحة ووجّهيه للرقم/واتساب المتجر.
"""


# ===== Models =====

class AvatarChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    session_id: Optional[str] = None
    want_voice: bool = True
    primary: Optional[str] = "zara"
    anon_id: Optional[str] = None
    dual_banter: bool = True
    user_name: Optional[str] = None  # for personalization
    detect_intent: bool = True       # extract intent for auto-routing


class StartTrialIn(BaseModel):
    project_id: str
    shop_name: str
    products_description: str = ""
    pricing_info: Optional[str] = ""
    faq: Optional[str] = ""
    avatar_name: Optional[str] = "المساعدة"
    voice_id: Optional[str] = "nova"
    tone: Optional[str] = "saudi_friendly"  # 'saudi_friendly' | 'formal' | 'casual'


class SubscribeIn(BaseModel):
    project_id: str


class CustomizeIn(BaseModel):
    project_id: str
    avatar_name: Optional[str] = None
    voice_id: Optional[str] = None
    tone: Optional[str] = None
    products_description: Optional[str] = None
    pricing_info: Optional[str] = None
    faq: Optional[str] = None


class HideIn(BaseModel):
    project_id: str
    hidden: bool


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_active(avatar: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Returns {active, reason, status, days_left, expires_at}."""
    if not avatar:
        return {"active": False, "status": "none", "reason": "not_enabled"}
    if avatar.get("hidden"):
        return {"active": False, "status": "hidden", "reason": "hidden_by_owner"}
    try:
        expires_raw = avatar.get("expires_at")
        if not expires_raw:
            return {"active": False, "status": "expired", "reason": "no_expiration"}
        expires = datetime.fromisoformat(str(expires_raw).replace("Z", "+00:00"))
        now = _now()
        if expires < now:
            return {"active": False, "status": "expired", "reason": "expired"}
        days_left = max(0, (expires - now).days)
        status = "trial" if avatar.get("on_trial") else "paid"
        return {"active": True, "status": status, "days_left": days_left, "expires_at": expires.isoformat()}
    except Exception:
        return {"active": False, "status": "error", "reason": "bad_date"}


def create_avatar_router(db, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["avatar"])

    # ===== Helper: chat with Claude =====
    async def _chat_completion(system: str, user_msg: str, session_id: str) -> str:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        emergent_key = os.environ.get("EMERGENT_LLM_KEY")
        if not emergent_key:
            return "معليش، الخدمة مو متاحة حالياً. جرّب بعد شوي."
        chat = LlmChat(api_key=emergent_key, session_id=session_id, system_message=system)
        chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
        response = await chat.send_message(UserMessage(text=user_msg))
        return response

    # ===== Helper: TTS via OpenAI (HD quality + Arabic-optimized) =====
    async def _tts(text: str, voice_id: Optional[str] = None) -> Optional[str]:
        try:
            from emergentintegrations.llm.openai import OpenAITextToSpeech
            api_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
            if not api_key:
                return None
            tts = OpenAITextToSpeech(api_key=api_key)
            voice = voice_id or "coral"

            # Deep text cleaning for better Arabic pronunciation
            import re as _re
            clean = text[:4000]
            # Remove emojis (TTS reads them poorly)
            clean = _re.sub(r'[\U0001F000-\U0001FFFF\U00002600-\U000027BF\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]+', '', clean)
            # Remove Arabic tatweel (stretches pronunciation oddly)
            clean = clean.replace('ـ', '')
            # Fix common speech flow issues
            clean = clean.replace('!', '.').replace('؟', '.').replace('?', '.')
            # Expand common Saudi colloquial abbreviations to proper pronunciation
            replacements = {
                'ان شاء الله': 'إن شاء الله',
                'ماشاء الله': 'ما شاء الله',
                'ولله': 'والله',
                'وشو': 'وش هو',
                'شلونك': 'شلون حالك',
                'مدري': 'ما أدري',
                'AI': 'إيه آي',
                'OK': 'أوكي',
                'ok': 'أوكي',
            }
            for k, v in replacements.items():
                clean = clean.replace(k, v)
            # Collapse whitespace
            clean = _re.sub(r'\s+', ' ', clean).strip()
            # Remove duplicate punctuation
            clean = _re.sub(r'\.{2,}', '.', clean)
            clean = _re.sub(r'،{2,}', '،', clean)

            if not clean:
                return None

            audio_b64 = await tts.generate_speech_base64(
                text=clean,
                model="tts-1-hd",
                voice=voice,
                speed=0.92,  # Slightly slower — much clearer Arabic articulation
            )
            if not audio_b64:
                return None
            return f"data:audio/mp3;base64,{audio_b64}"
        except Exception as e:
            logger.warning(f"[AVATAR] TTS failed: {e}")
            return None

    # ===== Helper: deduct points atomically =====
    async def _deduct(user_id: str, amount: int, reason: str) -> bool:
        result = await db.users.update_one(
            {"id": user_id, "credits": {"$gte": amount}},
            {"$inc": {"credits": -amount},
             "$push": {"credit_history": {
                 "amount": -amount,
                 "reason": reason,
                 "timestamp": _now().isoformat(),
             }}}
        )
        return result.modified_count > 0

    # Banter prompts (secondary character reacts to primary's reply)
    ZARA_BANTER_PROMPT = (
        "أنتِ زارا — حماسية مرحة ذهبية الشعر. رفيقتك ليلى قالت للمستخدم شي — "
        "أضيفي تعليق/ردة فعل قصيرة جداً (جملة واحدة، 3-8 كلمات) باللهجة السعودية. "
        "ممكن: تأييد ('الله أوه عجبتني!')، تعليق مرح ('يا ستّي!')، ملاحظة ('بس لا تنسيه...'). "
        "لا تعيدي كلام ليلى — فقط تعليق قصير spontanious. emoji واحد كحد أقصى."
    )
    LAYLA_BANTER_PROMPT = (
        "أنتِ ليلى — أنيقة هادئة بشعر أسود. رفيقتك زارا قالت للمستخدم شي — "
        "أضيفي تعليق/ردة فعل قصيرة جداً (جملة واحدة، 3-8 كلمات) باللهجة السعودية. "
        "ممكن: تأييد هادئ ('صح كلامها')، إضافة رزينة ('وأنا أقترح أيضاً...')، ملاحظة حكيمة. "
        "لا تعيدي كلام زارا — فقط تعليق قصير أنيق. emoji واحد كحد أقصى."
    )

    ANON_FREE_LIMIT = 5

    async def _check_anon_usage(anon_id: Optional[str]) -> Dict[str, Any]:
        """Returns usage info for anonymous users. None means unlimited (authenticated)."""
        if not anon_id:
            return {"count": 0, "limit": ANON_FREE_LIMIT, "remaining": ANON_FREE_LIMIT, "blocked": False}
        doc = await db.avatar_anon_usage.find_one({"anon_id": anon_id}, {"_id": 0})
        count = (doc or {}).get("count", 0)
        blocked = count >= ANON_FREE_LIMIT
        return {"count": count, "limit": ANON_FREE_LIMIT, "remaining": max(0, ANON_FREE_LIMIT - count), "blocked": blocked}

    async def _inc_anon_usage(anon_id: str):
        await db.avatar_anon_usage.update_one(
            {"anon_id": anon_id},
            {"$inc": {"count": 1}, "$set": {"last_at": _now().isoformat()}},
            upsert=True,
        )

    def _detect_intent_simple(message: str) -> Dict[str, Any]:
        """Fast keyword-based intent detection (no LLM call needed)."""
        m = (message or "").lower()
        # Image keywords
        img_kw = ["صورة", "صور", "تصميم صورة", "اعملي صورة", "ابغى صورة", "ابي صورة", "image"]
        vid_kw = ["فيديو", "فيديوهات", "كليب", "video", "اعملي فيديو"]
        site_kw = ["موقع", "ستور", "متجر", "تطبيق", "website", "site"]
        avatar_kw = ["مساعد", "مساعدة", "ذكاء", "بوت", "avatar"]

        intent = None
        if any(k in m for k in img_kw):
            intent = "image"
        elif any(k in m for k in vid_kw):
            intent = "video"
        elif any(k in m for k in site_kw):
            intent = "site"
        elif any(k in m for k in avatar_kw):
            intent = "avatar"

        if not intent:
            return {"intent": None, "subject": None, "route": None}

        # Extract subject (everything after the keyword + clean it)
        subject = message
        # Remove common prefixes
        for prefix in ["ابغى ", "أبغى ", "ابي ", "أبي ", "اعملي ", "اعمل لي ", "سويلي ", "سوي لي ", "تقدري ", "ممكن "]:
            if subject.startswith(prefix):
                subject = subject[len(prefix):]
                break
        # Remove the keyword itself + connective words
        for kw in img_kw + vid_kw + site_kw + avatar_kw:
            if subject.lower().startswith(kw):
                subject = subject[len(kw):].strip()
                # Strip "ل" "عن" "من" prefixes
                for c in ["لـ", "ل ", "عن ", "حق ", "للـ"]:
                    if subject.startswith(c):
                        subject = subject[len(c):]
                        break
                break

        subject = subject.strip(" ،,.!؟?")
        # Strip leading "لـ" or "ل " preposition that often remains
        for c in ["لـ", "ل ", "عن ", "حق ", "للـ", "ل"]:
            if subject.startswith(c):
                subject = subject[len(c):].lstrip(" ـ")
                break

        routes = {"image": "/chat/image", "video": "/chat/video", "site": "/websites", "avatar": "/dashboard/avatar"}
        return {"intent": intent, "subject": subject or None, "route": routes.get(intent)}

    # ===== ZITEX MAIN AVATAR (public, no auth) =====
    @router.post("/avatar/chat")
    async def zitex_avatar_chat(payload: AvatarChatIn):
        sid = payload.session_id or "zitex-public"
        primary = payload.primary or "zara"
        secondary = "layla" if primary == "zara" else "zara"

        # Anon free-trial enforcement
        usage = await _check_anon_usage(payload.anon_id)
        if usage["blocked"]:
            raise HTTPException(403, f"انتهت المحادثات المجانية ({ANON_FREE_LIMIT}). سجّل حسابك لتكمل ✨")

        try:
            # Build personalized message — inject name into context
            name_prefix = f"اسم المستخدم: {payload.user_name}\n\n" if payload.user_name else ""
            user_msg = name_prefix + payload.message
            text = await _chat_completion(ZITEX_AVATAR_SYSTEM, user_msg, sid)
        except Exception as e:
            logger.exception(f"[AVATAR] Chat failed: {e}")
            raise HTTPException(500, "فشل المساعد. حاول مرة ثانية.")

        # Intent detection — fast, no LLM call
        intent_data = _detect_intent_simple(payload.message) if payload.detect_intent else {"intent": None}

        audio_url = None
        if payload.want_voice:
            # Voice assignments optimized for Arabic: coral (warm friendly female) + sage (wise measured female)
            primary_voice = "coral" if primary == "zara" else "sage"
            audio_url = await _tts(text, primary_voice)

        # Dual banter — secondary character adds a short reaction
        banter_text = None
        banter_audio = None
        if payload.dual_banter and len(text) < 600:
            try:
                banter_sys = ZARA_BANTER_PROMPT if secondary == "zara" else LAYLA_BANTER_PROMPT
                banter_ctx = f"ليلى قالت: '{text}'" if secondary == "zara" else f"زارا قالت: '{text}'"
                banter_text = await _chat_completion(banter_sys, banter_ctx, f"{sid}-banter")
                if banter_text and payload.want_voice:
                    sec_voice = "coral" if secondary == "zara" else "sage"
                    banter_audio = await _tts(banter_text, sec_voice)
            except Exception as e:
                logger.warning(f"[AVATAR] Banter generation failed: {e}")
                banter_text = None

        # Track anon usage
        if payload.anon_id:
            await _inc_anon_usage(payload.anon_id)
            usage = await _check_anon_usage(payload.anon_id)

        await db.avatar_conversations.insert_one({
            "site": "zitex",
            "session_id": sid,
            "user_message": payload.message,
            "assistant_reply": text,
            "primary": primary,
            "banter_reply": banter_text,
            "had_voice": bool(audio_url),
            "anon_id": payload.anon_id,
            "timestamp": _now().isoformat(),
        })
        return {
            "reply": text,
            "audio_url": audio_url,
            "session_id": sid,
            "primary": primary,
            "secondary": secondary,
            "banter": {
                "text": banter_text,
                "audio_url": banter_audio,
                "from_char": secondary,
            } if banter_text else None,
            "anon_usage": usage,
            "intent": intent_data,
        }

    # ===== ZITEX GREETING (auto-greet on entry — fast Haiku-based) =====
    @router.post("/avatar/greet")
    async def zitex_greet(payload: Dict[str, Any]):
        """Quick personalized greeting on app entry. Uses Haiku for speed."""
        primary = payload.get("primary", "zara")
        user_name = payload.get("user_name") or "صديقي"
        time_hint = payload.get("time_hint", "")  # 'morning'|'afternoon'|'evening'|'night'
        want_voice = payload.get("want_voice", True)

        # Build a quick context (no LLM needed for simple greetings — but use LLM for variety)
        time_phrase = {
            "morning": "صباح الخير",
            "afternoon": "مساء النور",
            "evening": "مساء الخير",
            "night": "أهلاً في الليل",
        }.get(time_hint, "هلا")

        char_persona = (
            "أنت زارا، مرحة وحماسية. ردك جملة واحدة قصيرة جداً (5-12 كلمة)."
            if primary == "zara"
            else "أنت ليلى، أنيقة وهادئة. ردك جملة واحدة قصيرة جداً (5-12 كلمة)."
        )
        sys = f"""أنت {primary} على موقع Zitex.
{char_persona}
بدون emoji. لهجة سعودية طبيعية. استخدمي الاسم.
"""
        user_msg = f"المستخدم اسمه {user_name} وفتح الموقع الآن. الوقت: {time_phrase}. حييه ترحيب طبيعي قصير وذكّريه إنه يقدر يطلب صور أو فيديو أو موقع بالكلام."

        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            api_key = os.environ.get("EMERGENT_LLM_KEY")
            if not api_key:
                # Fallback static greeting
                text = f"{time_phrase} {user_name}! وش تحب نسوي اليوم؟"
            else:
                chat = LlmChat(api_key=api_key, session_id=f"greet-{user_name}", system_message=sys)
                # Use Haiku — much faster (claude-haiku-4-5)
                chat.with_model("anthropic", "claude-haiku-4-5-20251001")
                text = await chat.send_message(UserMessage(text=user_msg))
        except Exception as e:
            logger.warning(f"[AVATAR-GREET] LLM failed: {e}")
            text = f"{time_phrase} {user_name}! وش تحب نسوي اليوم؟"

        audio_url = None
        if want_voice:
            voice = "coral" if primary == "zara" else "sage"
            audio_url = await _tts(text, voice)
        return {"reply": text, "audio_url": audio_url, "primary": primary}

    # ===== ANON USAGE STATUS =====
    @router.get("/avatar/anon-usage")
    async def anon_usage_status(anon_id: str):
        usage = await _check_anon_usage(anon_id)
        return usage

    # ===== MERCHANT AVATAR — pricing info =====
    @router.get("/merchant/avatar/pricing")
    async def avatar_pricing():
        return {
            "monthly_cost": AVATAR_MONTHLY_COST,
            "customize_cost": AVATAR_CUSTOMIZE_COST,
            "trial_days": AVATAR_TRIAL_DAYS,
            "available_voices": AVAILABLE_VOICES,
            "features": [
                "مساعد ذكاء اصطناعي يرد على زوار متجرك باللهجة السعودية",
                f"{AVATAR_TRIAL_DAYS} يوم تجربة مجانية (لمرة واحدة فقط)",
                "تقدر تغيّر اسمه، صوته، ونبرته في أي وقت",
                "يعرف كل منتجاتك وخدماتك وأسعارك",
                "يشتغل 24/7 ويرد فوراً",
            ],
        }

    # ===== Owner: fetch my avatar config =====
    @router.get("/merchant/avatar/me")
    async def my_avatar(project_id: str, user=Depends(get_current_user)):
        # Support both owner_id (new) and user_id (legacy) fields
        project = await db.website_projects.find_one(
            {"id": project_id, "$or": [{"owner_id": user["user_id"]}, {"user_id": user["user_id"]}]},
            {"_id": 0}
        )
        if not project:
            raise HTTPException(404, "المشروع مش موجود")
        avatar = await db.merchant_avatars.find_one(
            {"project_id": project_id},
            {"_id": 0, "owner_id": 0}
        )
        status = _is_active(avatar)
        return {
            "project_id": project_id,
            "has_config": avatar is not None,
            "status": status,
            "config": avatar or {},
        }

    # ===== Owner: start 14-day free trial =====
    @router.post("/merchant/avatar/start-trial")
    async def start_trial(payload: StartTrialIn, user=Depends(get_current_user)):
        # Support both owner_id (new) and user_id (legacy) fields
        project = await db.website_projects.find_one(
            {"id": payload.project_id, "$or": [{"owner_id": user["user_id"]}, {"user_id": user["user_id"]}]},
            {"_id": 0}
        )
        if not project:
            raise HTTPException(404, "المشروع مش موجود")

        existing = await db.merchant_avatars.find_one({"project_id": payload.project_id}, {"_id": 0})
        if existing and existing.get("trial_used"):
            raise HTTPException(400, "التجربة المجانية مستخدمة — اشترك بالنقاط للتفعيل")

        expires = _now() + timedelta(days=AVATAR_TRIAL_DAYS)
        config = {
            "project_id": payload.project_id,
            "owner_id": user["user_id"],
            "shop_name": payload.shop_name,
            "avatar_name": payload.avatar_name or "المساعدة",
            "products_description": payload.products_description,
            "pricing_info": payload.pricing_info or "",
            "faq": payload.faq or "",
            "voice_id": payload.voice_id or "nova",
            "tone": payload.tone or "saudi_friendly",
            "active": True,
            "hidden": False,
            "on_trial": True,
            "trial_used": True,
            "trial_started_at": _now().isoformat(),
            "subscribed_at": _now().isoformat(),
            "expires_at": expires.isoformat(),
            "monthly_cost": AVATAR_MONTHLY_COST,
        }
        await db.merchant_avatars.update_one(
            {"project_id": payload.project_id},
            {"$set": config},
            upsert=True,
        )
        return {
            "ok": True,
            "trial": True,
            "expires_at": expires.isoformat(),
            "days_left": AVATAR_TRIAL_DAYS,
            "message": f"🎉 تم تفعيل تجربتك المجانية {AVATAR_TRIAL_DAYS} يوم! استمتع.",
        }

    # ===== Owner: subscribe (paid month) =====
    @router.post("/merchant/avatar/subscribe")
    async def subscribe(payload: SubscribeIn, user=Depends(get_current_user)):
        # Support both owner_id (new) and user_id (legacy) fields
        project = await db.website_projects.find_one(
            {"id": payload.project_id, "$or": [{"owner_id": user["user_id"]}, {"user_id": user["user_id"]}]},
            {"_id": 0}
        )
        if not project:
            raise HTTPException(404, "المشروع مش موجود")

        avatar = await db.merchant_avatars.find_one({"project_id": payload.project_id}, {"_id": 0})
        if not avatar:
            raise HTTPException(400, "ابدأ التجربة المجانية أولاً")

        ok = await _deduct(user["user_id"], AVATAR_MONTHLY_COST, f"avatar_subscription_{payload.project_id[:8]}")
        if not ok:
            raise HTTPException(402, f"رصيدك ما يكفي — محتاج {AVATAR_MONTHLY_COST} نقطة")

        # Extend 30 days from current expires_at (or now, whichever is later)
        try:
            current_expires = datetime.fromisoformat(avatar.get("expires_at", _now().isoformat()).replace("Z", "+00:00"))
        except Exception:
            current_expires = _now()
        base = max(current_expires, _now())
        new_expires = base + timedelta(days=30)

        await db.merchant_avatars.update_one(
            {"project_id": payload.project_id},
            {"$set": {
                "active": True,
                "on_trial": False,
                "expires_at": new_expires.isoformat(),
                "last_renewed_at": _now().isoformat(),
            }},
        )
        return {
            "ok": True,
            "credits_deducted": AVATAR_MONTHLY_COST,
            "expires_at": new_expires.isoformat(),
            "message": "تمّ تجديد اشتراكك شهر كامل",
        }

    # ===== Owner: customize avatar =====
    @router.put("/merchant/avatar/customize")
    async def customize(payload: CustomizeIn, user=Depends(get_current_user)):
        # Support both owner_id (new) and user_id (legacy) fields
        project = await db.website_projects.find_one(
            {"id": payload.project_id, "$or": [{"owner_id": user["user_id"]}, {"user_id": user["user_id"]}]},
            {"_id": 0}
        )
        if not project:
            raise HTTPException(404, "المشروع مش موجود")

        avatar = await db.merchant_avatars.find_one({"project_id": payload.project_id}, {"_id": 0})
        if not avatar:
            raise HTTPException(400, "ابدأ التجربة المجانية أو اشترك أولاً")

        status = _is_active(avatar)
        if not status["active"] and status["status"] != "hidden":
            raise HTTPException(403, "اشتراكك منتهي — جدّد أولاً")

        # Build update dict
        updates: Dict[str, Any] = {}
        charge = False
        if payload.avatar_name is not None:
            nm = payload.avatar_name.strip()[:30]
            if nm and nm != avatar.get("avatar_name"):
                updates["avatar_name"] = nm
                charge = True
        if payload.voice_id is not None and payload.voice_id != avatar.get("voice_id"):
            if not any(v["id"] == payload.voice_id for v in AVAILABLE_VOICES):
                raise HTTPException(400, "الصوت المحدد مش صحيح")
            updates["voice_id"] = payload.voice_id
            charge = True
        if payload.tone is not None and payload.tone in ("saudi_friendly", "formal", "casual"):
            if payload.tone != avatar.get("tone"):
                updates["tone"] = payload.tone
                charge = True
        # Content updates are free always
        if payload.products_description is not None:
            updates["products_description"] = payload.products_description[:2000]
        if payload.pricing_info is not None:
            updates["pricing_info"] = payload.pricing_info[:1500]
        if payload.faq is not None:
            updates["faq"] = payload.faq[:2000]

        if not updates:
            return {"ok": True, "no_changes": True, "message": "ما فيه شي تغيّر"}

        # Charge if identity fields changed AND not on trial
        credits_deducted = 0
        if charge and not avatar.get("on_trial"):
            ok = await _deduct(user["user_id"], AVATAR_CUSTOMIZE_COST, f"avatar_customize_{payload.project_id[:8]}")
            if not ok:
                raise HTTPException(402, f"رصيدك ما يكفي — التخصيص يكلف {AVATAR_CUSTOMIZE_COST} نقطة")
            credits_deducted = AVATAR_CUSTOMIZE_COST

        updates["updated_at"] = _now().isoformat()
        await db.merchant_avatars.update_one(
            {"project_id": payload.project_id},
            {"$set": updates},
        )
        return {
            "ok": True,
            "credits_deducted": credits_deducted,
            "free_on_trial": avatar.get("on_trial", False) and charge,
            "updated_fields": list(updates.keys()),
        }

    # ===== Owner: hide/show avatar =====
    @router.post("/merchant/avatar/hide")
    async def hide_toggle(payload: HideIn, user=Depends(get_current_user)):
        # Support both owner_id (new) and user_id (legacy) fields
        project = await db.website_projects.find_one(
            {"id": payload.project_id, "$or": [{"owner_id": user["user_id"]}, {"user_id": user["user_id"]}]},
            {"_id": 0}
        )
        if not project:
            raise HTTPException(404, "المشروع مش موجود")
        avatar = await db.merchant_avatars.find_one({"project_id": payload.project_id}, {"_id": 0})
        if not avatar:
            raise HTTPException(400, "لا يوجد إعداد للمساعد")

        # Free if on trial or already hidden; otherwise charge when toggling on
        was_hidden = avatar.get("hidden", False)
        if not payload.hidden and was_hidden and not avatar.get("on_trial"):
            ok = await _deduct(user["user_id"], AVATAR_CUSTOMIZE_COST, f"avatar_unhide_{payload.project_id[:8]}")
            if not ok:
                raise HTTPException(402, f"إعادة الإظهار تكلف {AVATAR_CUSTOMIZE_COST} نقطة")

        await db.merchant_avatars.update_one(
            {"project_id": payload.project_id},
            {"$set": {"hidden": payload.hidden, "updated_at": _now().isoformat()}},
        )
        return {"ok": True, "hidden": payload.hidden}

    # ===== PUBLIC: get merchant avatar config =====
    @router.get("/merchant/avatar/{slug}")
    async def get_merchant_avatar(slug: str):
        project = await db.website_projects.find_one(
            {"slug": slug}, {"_id": 0, "id": 1, "name": 1}
        )
        if not project:
            raise HTTPException(404, "متجر مش موجود")
        avatar = await db.merchant_avatars.find_one(
            {"project_id": project["id"]}, {"_id": 0}
        )
        status = _is_active(avatar)
        if not status["active"]:
            return {"enabled": False, "status": status.get("status")}
        return {
            "enabled": True,
            "shop_name": avatar.get("shop_name"),
            "avatar_name": avatar.get("avatar_name", "المساعدة"),
            "voice_id": avatar.get("voice_id", "nova"),
            "tone": avatar.get("tone", "saudi_friendly"),
            "on_trial": avatar.get("on_trial", False),
            "days_left": status.get("days_left", 0),
        }

    @router.post("/merchant/avatar/{slug}/chat")
    async def chat_with_merchant_avatar(slug: str, payload: AvatarChatIn):
        project = await db.website_projects.find_one(
            {"slug": slug}, {"_id": 0, "id": 1}
        )
        if not project:
            raise HTTPException(404, "متجر مش موجود")
        avatar = await db.merchant_avatars.find_one(
            {"project_id": project["id"]}, {"_id": 0}
        )
        status = _is_active(avatar)
        if not status["active"]:
            raise HTTPException(403, "المساعد مو مفعّل لهالمتجر")
        sid = payload.session_id or f"shop-{project['id'][:8]}-{_now().timestamp():.0f}"
        system = _merchant_system_message(avatar)
        try:
            text = await _chat_completion(system, payload.message, sid)
        except Exception as e:
            logger.exception(f"[MERCHANT AVATAR] Chat failed: {e}")
            raise HTTPException(500, "فشل المساعد الذكي")
        audio_url = None
        if payload.want_voice:
            audio_url = await _tts(text, avatar.get("voice_id"))
        await db.avatar_conversations.insert_one({
            "site": slug,
            "project_id": project["id"],
            "session_id": sid,
            "user_message": payload.message,
            "assistant_reply": text,
            "had_voice": bool(audio_url),
            "timestamp": _now().isoformat(),
        })
        return {"reply": text, "audio_url": audio_url, "session_id": sid}

    return router
