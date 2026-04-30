"""
Zitex AI Avatar — premium animated assistant module.

Provides:
    POST /api/avatar/chat               — chat with avatar (text + voice reply)
    POST /api/merchant/avatar/enable    — merchant subscribes to add avatar to their site
    GET  /api/merchant/avatar/{slug}    — public config for a merchant's avatar
    POST /api/merchant/avatar/{slug}/chat — public visitor chat with merchant's avatar

For the MAIN Zitex site avatar:
- system message describes Zitex platform capabilities
- responds about the products/services Zitex offers
- text + voice (ElevenLabs)

For MERCHANT site avatars:
- system message includes: shop name, products, pricing, FAQ
- visitors talk to the avatar to learn about products
- merchants pay 100 credits/month subscription (renews monthly)
"""
from __future__ import annotations
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ===== Pricing =====
AVATAR_MONTHLY_COST = 100  # credits per month for merchant subscription

# ===== System messages =====
ZITEX_AVATAR_SYSTEM = """أنت إحدى الشخصيتين (زارا أو ليلى) — مساعدتا منصة Zitex الذكية.

شخصيتك:
- زارا: ذهبية الشعر، ودودة، حيوية، تستخدم emoji كثير (✨🎨💫), لغة ودودة ('يا حلو' 'يلا')
- ليلى: سوداء الشعر بذهبي، هادئة أنيقة، ذكية، مستشارة عمل، emoji قليل وأنيق (🖤✨)

قد تظهرين مع رفيقتك (أحياناً يتناقشن لحظياً) — اذكري ذلك بشكل طبيعي ('سأسأل ليلى' أو 'زارا راح تحب هذه الفكرة').

الخدمات الشغّالة على Zitex:
- مواقع جاهزة (25 تخصص: مطاعم، كافيهات، صالونات، عقارات، أسهم...)
- إنشاء صور AI (5 نقاط/صورة)
- إنشاء فيديوهات AI (Sora 2، 8-12 نقاط/ثانية)
- قريباً: تطبيقات موبايل، ألعاب

أسلوب المحادثة المثالي:
- ردود قصيرة (1-3 جمل) مفيدة جداً
- إذا المستخدم طلب شيء غامض (مثل "ابغى صورة") اسأليه أسئلة محددة:
  * أي موضوع؟
  * الجمهور المستهدف؟
  * المزاج العام؟
- لا تطنب في الشرح إلا إذا طُلب
- إذا احتاج العميل مساعدة عملية، وجّهيه للصفحة المناسبة:
  * صور → /chat/image
  * فيديو → /chat/video
  * موقع → /websites
- شجّعي العميل بلطف لإتمام ما يريد

اللغة: عربي فقط بلهجة خليجية سعودية ودودة.
"""


def _merchant_system_message(config: Dict[str, Any]) -> str:
    shop_name = config.get("shop_name", "المتجر")
    products = config.get("products_description", "")
    pricing = config.get("pricing_info", "")
    faq = config.get("faq", "")
    return f"""You are the AI assistant of '{shop_name}' — a friendly knowledgeable assistant.

ABOUT THE SHOP:
{products}

PRICING:
{pricing}

FAQ:
{faq}

PERSONALITY:
- ودود مهتم بالعميل
- ردود قصيرة (1-3 جمل) مفيدة
- استخدم emoji قليل
- إن سُئل عن منتج لا تعرفه: قل بأدب أنه غير متوفر حالياً واقترح بدائل
- شجّع العميل على إتمام الشراء بأسلوب طبيعي غير مزعج

LANGUAGE: Arabic only.
"""


# ===== Models =====

class AvatarChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    session_id: Optional[str] = None
    want_voice: bool = True


class MerchantAvatarEnableIn(BaseModel):
    project_id: str
    shop_name: str
    products_description: str
    pricing_info: Optional[str] = ""
    faq: Optional[str] = ""
    avatar_style: str = "friendly_arab_woman"  # 'friendly_arab_woman' | 'professional_man' | 'cartoon_pet'
    voice_id: Optional[str] = None  # ElevenLabs voice id (uses default if None)


def create_avatar_router(db, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["avatar"])

    # ===== Helper: chat with Claude =====
    async def _chat_completion(system: str, user_msg: str, session_id: str) -> str:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        emergent_key = os.environ.get("EMERGENT_LLM_KEY")
        if not emergent_key:
            return "عذراً، خدمة المساعد غير متاحة حالياً."
        chat = LlmChat(api_key=emergent_key, session_id=session_id, system_message=system)
        chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
        response = await chat.send_message(UserMessage(text=user_msg))
        return response

    # ===== Helper: TTS via OpenAI (Emergent LLM Key) =====
    async def _tts(text: str, voice_id: Optional[str] = None) -> Optional[str]:
        """Returns a data:audio/mp3;base64,... URL or None on error."""
        try:
            from emergentintegrations.llm.openai import OpenAITextToSpeech
            api_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
            if not api_key:
                return None
            tts = OpenAITextToSpeech(api_key=api_key)
            voice = voice_id or "nova"  # Nova = warm female voice, good for Arabic
            # Limit to 4096 chars (OpenAI TTS hard cap)
            audio_b64 = await tts.generate_speech_base64(
                text=text[:4000],
                model="tts-1",
                voice=voice,
            )
            if not audio_b64:
                return None
            return f"data:audio/mp3;base64,{audio_b64}"
        except Exception as e:
            logger.warning(f"[AVATAR] TTS failed: {e}")
            return None

    # ===== ZITEX MAIN AVATAR — public, no auth needed =====
    @router.post("/avatar/chat")
    async def zitex_avatar_chat(payload: AvatarChatIn):
        sid = payload.session_id or "zitex-public"
        try:
            text = await _chat_completion(ZITEX_AVATAR_SYSTEM, payload.message, sid)
        except Exception as e:
            logger.exception(f"[AVATAR] Chat failed: {e}")
            raise HTTPException(500, "فشل المساعد. حاول مرة أخرى.")
        audio_url = None
        if payload.want_voice:
            audio_url = await _tts(text)
        await db.avatar_conversations.insert_one({
            "site": "zitex",
            "session_id": sid,
            "user_message": payload.message,
            "assistant_reply": text,
            "had_voice": bool(audio_url),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {"reply": text, "audio_url": audio_url, "session_id": sid}

    # ===== MERCHANT AVATAR — owner enables it (paid) =====
    @router.post("/merchant/avatar/enable")
    async def enable_merchant_avatar(payload: MerchantAvatarEnableIn, user=Depends(get_current_user)):
        # Verify project ownership
        project = await db.website_projects.find_one(
            {"id": payload.project_id, "owner_id": user["user_id"]},
            {"_id": 0}
        )
        if not project:
            raise HTTPException(404, "المشروع غير موجود")

        # Atomic deduct subscription cost
        result = await db.users.update_one(
            {"id": user["user_id"], "credits": {"$gte": AVATAR_MONTHLY_COST}},
            {"$inc": {"credits": -AVATAR_MONTHLY_COST},
             "$push": {"credit_history": {
                 "amount": -AVATAR_MONTHLY_COST,
                 "reason": f"avatar_subscription_{payload.project_id[:8]}",
                 "timestamp": datetime.now(timezone.utc).isoformat(),
             }}}
        )
        if result.modified_count == 0:
            raise HTTPException(402, f"رصيد غير كافٍ ({AVATAR_MONTHLY_COST} نقاط مطلوبة شهرياً)")

        expires = datetime.now(timezone.utc) + timedelta(days=30)
        avatar_config = {
            "project_id": payload.project_id,
            "owner_id": user["user_id"],
            "shop_name": payload.shop_name,
            "products_description": payload.products_description,
            "pricing_info": payload.pricing_info or "",
            "faq": payload.faq or "",
            "avatar_style": payload.avatar_style,
            "voice_id": payload.voice_id,
            "active": True,
            "subscribed_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires.isoformat(),
            "monthly_cost": AVATAR_MONTHLY_COST,
        }
        # Upsert
        await db.merchant_avatars.update_one(
            {"project_id": payload.project_id},
            {"$set": avatar_config},
            upsert=True,
        )
        return {
            "ok": True,
            "active": True,
            "expires_at": expires.isoformat(),
            "credits_deducted": AVATAR_MONTHLY_COST,
        }

    @router.get("/merchant/avatar/{slug}")
    async def get_merchant_avatar(slug: str):
        project = await db.website_projects.find_one(
            {"slug": slug}, {"_id": 0, "id": 1, "name": 1}
        )
        if not project:
            raise HTTPException(404, "متجر غير موجود")
        avatar = await db.merchant_avatars.find_one(
            {"project_id": project["id"], "active": True}, {"_id": 0}
        )
        if not avatar:
            return {"enabled": False}
        # Check expiration
        try:
            expires = datetime.fromisoformat(avatar["expires_at"].replace("Z", "+00:00"))
            if expires < datetime.now(timezone.utc):
                await db.merchant_avatars.update_one(
                    {"project_id": project["id"]},
                    {"$set": {"active": False}}
                )
                return {"enabled": False, "reason": "expired"}
        except Exception:
            pass
        return {
            "enabled": True,
            "shop_name": avatar.get("shop_name"),
            "avatar_style": avatar.get("avatar_style", "friendly_arab_woman"),
        }

    @router.post("/merchant/avatar/{slug}/chat")
    async def chat_with_merchant_avatar(slug: str, payload: AvatarChatIn):
        project = await db.website_projects.find_one(
            {"slug": slug}, {"_id": 0, "id": 1}
        )
        if not project:
            raise HTTPException(404, "متجر غير موجود")
        avatar = await db.merchant_avatars.find_one(
            {"project_id": project["id"], "active": True}, {"_id": 0}
        )
        if not avatar:
            raise HTTPException(403, "المساعد الذكي غير مفعّل لهذا المتجر")
        sid = payload.session_id or f"shop-{project['id'][:8]}-{datetime.now(timezone.utc).timestamp():.0f}"
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {"reply": text, "audio_url": audio_url, "session_id": sid}

    return router
