"""
Zitex AI Chat Service - Business Edition
خدمة الشات الذكي - النسخة التجارية
Version 4.0 - Consultative AI Assistant
"""
import os
import uuid
import base64
import logging
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

AI_FEATURES_ENABLED = True

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs.types import VoiceSettings
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    ElevenLabs = None
    VoiceSettings = None


MASTER_SYSTEM_PROMPT = """أنت "زيتكس" (Zitex) - مستشار ذكاء اصطناعي محترف لبناء المشاريع الرقمية.

## هويتك ودورك
أنت مستشار محترف تساعد العملاء في بناء مواقع ويب، تطبيقات جوال، تطبيقات ويب، وألعاب تفاعلية.

## آلية العمل

### المرحلة 1: فهم المشروع
عندما يبدأ العميل، اسأله:

---
## 👋 مرحباً بك في زيتكس!

**ما نوع المشروع الذي تريد بناءه؟**

| الخيار | النوع | الوصف |
|--------|-------|-------|
| **أ** | 🌐 موقع ويب | موقع كامل يعمل على المتصفح |
| **ب** | 📱 تطبيق جوال | تطبيق للهواتف |
| **ج** | 💻 تطبيق ويب | نظام أو لوحة تحكم |
| **د** | 🎮 لعبة | لعبة تفاعلية |

> 💡 اختر حرفاً (أ، ب، ج، أو د)
---

### المرحلة 2: جمع التفاصيل
بعد معرفة النوع، اسأل أسئلة محددة عن المجال والأقسام والألوان.

### المرحلة 3: تأكيد الفهم
قبل البدء، لخص ما فهمته في جدول واسأل: هل هذا صحيح؟

### المرحلة 4: البناء
بعد التأكيد، أنشئ الكود الكامل مع شارة Zitex.

## قواعد تنسيق الردود
- استخدم **عناوين** و **جداول** و **إيموجي**
- استخدم > للملاحظات المهمة
- استخدم --- بين الأقسام
- الكود يكون كاملاً 100% داخل ```html

## نظام النقاط
| الخدمة | النقاط |
|--------|--------|
| رسالة استشارة | 1 |
| بناء موقع | 15 |
| بناء تطبيق | 20 |
| بناء لعبة | 15-25 |
| توليد صورة | 5 |
| تعديل | 5 |

عند كل عملية، أخبر العميل:
> 💰 **التكلفة:** X نقطة | **رصيدك:** Y نقطة

## قواعد مهمة
✅ اسأل أسئلة قبل البناء
✅ استخدم تنسيق غني
✅ أخبر العميل بالتكلفة
✅ أضف شارة Zitex
✅ اكتب كود كامل"""


WELCOME_MESSAGE = """## 👋 مرحباً بك في زيتكس!

أنا مستشارك الذكي لبناء مشروعك الرقمي.

---

### 🎯 ما نوع المشروع الذي تريد بناءه؟

| الخيار | النوع | الوصف |
|--------|-------|-------|
| **أ** | 🌐 موقع ويب | موقع كامل يعمل على المتصفح |
| **ب** | 📱 تطبيق جوال | تطبيق للهواتف (Android/iOS) |
| **ج** | 💻 تطبيق ويب | نظام إدارة أو لوحة تحكم |
| **د** | 🎮 لعبة | لعبة تفاعلية 2D أو 3D |
| **هـ** | 🎨 تصميم/صورة | شعار أو تصميم جرافيكي |
| **و** | 🎬 فيديو | فيديو سينمائي |

---

> 💡 **اختر حرفاً** أو اكتب فكرتك مباشرة!

> 💰 **رصيدك الحالي:** {credits} نقطة"""


ZITEX_BADGE = '''<!-- Zitex Badge -->
<div id="zitex-badge" style="position:fixed;bottom:20px;right:20px;background:linear-gradient(135deg,#1a1a2e,#16213e);padding:10px 20px;border-radius:25px;box-shadow:0 4px 15px rgba(0,0,0,0.3);z-index:9999;display:flex;align-items:center;gap:10px;cursor:pointer;border:1px solid rgba(255,215,0,0.3);" onclick="window.open('https://zitex.vercel.app','_blank')">
    <div style="width:30px;height:30px;background:linear-gradient(135deg,#ffd700,#ffaa00);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;color:#000;font-size:16px;">Z</div>
    <span style="color:#ffd700;font-size:14px;font-weight:500;">Powered by Zitex</span>
</div>'''


SERVICE_COSTS = {
    "message": 1,
    "website": 15,
    "webapp": 20,
    "pwa": 20,
    "game": 15,
    "game_3d": 25,
    "image": 5,
    "video": 20,
    "modification": 5,
    "export": 50,
    "deploy": 100
}


def detect_request_type(message: str, session_type: str = "general") -> str:
    message_lower = message.lower()
    
    if message.strip() in ['أ', 'ا', 'a', 'A']:
        return "website"
    elif message.strip() in ['ب', 'b', 'B']:
        return "pwa"
    elif message.strip() in ['ج', 'c', 'C']:
        return "webapp"
    elif message.strip() in ['د', 'd', 'D']:
        return "game"
    elif message.strip() in ['هـ', 'ه', 'e', 'E']:
        return "image"
    elif message.strip() in ['و', 'f', 'F']:
        return "video"
    
    game_3d_keywords = ['3d', 'ثلاثي', 'ثلاثية', 'سباق', 'سيارات']
    game_2d_keywords = ['لعبة', 'العاب', 'game', 'ألعاب']
    pwa_keywords = ['تطبيق جوال', 'موبايل', 'للجوال', 'اندرويد', 'ايفون']
    webapp_keywords = ['تطبيق ويب', 'لوحة تحكم', 'dashboard', 'نظام']
    website_keywords = ['موقع', 'صفحة', 'ويب', 'متجر', 'مطعم', 'شركة']
    image_keywords = ['صورة', 'صور', 'شعار', 'لوجو', 'تصميم']
    video_keywords = ['فيديو', 'مقطع', 'فلم', 'سينمائي']
    
    if session_type and session_type != "general":
        return session_type
    
    if any(kw in message_lower for kw in game_3d_keywords):
        return "game_3d"
    elif any(kw in message_lower for kw in game_2d_keywords):
        return "game"
    elif any(kw in message_lower for kw in pwa_keywords):
        return "pwa"
    elif any(kw in message_lower for kw in webapp_keywords):
        return "webapp"
    elif any(kw in message_lower for kw in image_keywords):
        return "image"
    elif any(kw in message_lower for kw in video_keywords):
        return "video"
    elif any(kw in message_lower for kw in website_keywords):
        return "website"
    
    return "general"


def inject_zitex_badge(html_code: str) -> str:
    if '</body>' in html_code:
        return html_code.replace('</body>', f'{ZITEX_BADGE}\n</body>')
    elif '</html>' in html_code:
        return html_code.replace('</html>', f'{ZITEX_BADGE}\n</html>')
    return html_code + '\n' + ZITEX_BADGE


class AIAssistant:
    def __init__(self, db: AsyncIOMotorDatabase, api_key: str = None, elevenlabs_key: str = None, openai_key: str = None):
        self.db = db
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.elevenlabs_key = elevenlabs_key
        self.openai_key = openai_key or self.api_key
        
        self.eleven_client = None
        if ELEVENLABS_AVAILABLE and elevenlabs_key:
            try:
                self.eleven_client = ElevenLabs(api_key=elevenlabs_key)
            except:
                pass
        
        self.openai_client = None
        if OPENAI_AVAILABLE and self.openai_key:
            try:
                self.openai_client = openai.OpenAI(api_key=self.openai_key)
            except:
                pass
    
    async def create_session(self, user_id: str, session_type: str = "general", title: str = None) -> Dict:
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0})
        credits = user.get("credits", 0) if user else 0
        
        welcome_content = WELCOME_MESSAGE.format(credits=credits)
        
        welcome_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": welcome_content,
            "message_type": "text",
            "attachments": [],
            "metadata": {"is_welcome": True},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        session = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title or "محادثة جديدة",
            "session_type": session_type,
            "messages": [welcome_msg],
            "project_data": {},
            "generated_code": None,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await self.db.chat_sessions.insert_one(session)
        return session
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict]:
        return await self.db.chat_sessions.find_one(
            {"id": session_id, "user_id": user_id},
            {"_id": 0}
        )
    
    async def get_user_sessions(self, user_id: str, limit: int = 50) -> List[Dict]:
        sessions = await self.db.chat_sessions.find(
            {"user_id": user_id, "status": "active"},
            {"_id": 0}
        ).sort("updated_at", -1).limit(limit).to_list(limit)
        return sessions
    
    async def get_user_credits(self, user_id: str) -> int:
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
        return user.get("credits", 0) if user else 0
    
    async def deduct_credits(self, user_id: str, amount: int, reason: str) -> bool:
        result = await self.db.users.update_one(
            {"id": user_id, "credits": {"$gte": amount}},
            {
                "$inc": {"credits": -amount},
                "$push": {
                    "credit_history": {
                        "amount": -amount,
                        "reason": reason,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
            }
        )
        return result.modified_count > 0
    
    async def process_message(self, session_id: str, user_id: str, message: str, settings: Dict[str, Any] = None) -> Dict:
        settings = settings or {}
        
        session = await self.get_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found")
        
        credits = await self.get_user_credits(user_id)
        
        user_msg = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": message,
            "message_type": "text",
            "attachments": [],
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        request_type = detect_request_type(message, session.get("session_type", "general"))
        
        ai_response = ""
        attachments = []
        credits_used = 0
        
        if not AI_FEATURES_ENABLED or not self.openai_client:
            ai_response = """## ⚠️ خدمة غير متاحة

عذراً، خدمات الذكاء الاصطناعي غير متاحة حالياً.

> 💡 يرجى التأكد من إعداد مفتاح OpenAI API."""
        else:
            required_credits = SERVICE_COSTS.get(request_type, 1)
            
            if credits < required_credits:
                ai_response = f"""## ⚠️ رصيد غير كافٍ

عذراً، رصيدك الحالي ({credits} نقطة) غير كافٍ لهذه العملية.

| العملية | التكلفة |
|---------|---------|
| {request_type} | {required_credits} نقطة |

---

> 💡 **الحل:** قم بشحن رصيدك من صفحة [الأسعار](/pricing)"""
            else:
                try:
                    if request_type == "image":
                        ai_response, attachments, credits_used = await self._generate_image(user_id, session_id, message, credits)
                    elif request_type == "video":
                        ai_response = """## 🎬 جاري إنشاء الفيديو...

| التفاصيل | القيمة |
|----------|--------|
| **النوع** | فيديو سينمائي |
| **المدة** | حتى 12 ثانية |
| **التكلفة** | 20 نقطة |

> ⏳ سيتم إشعارك عند الاكتمال"""
                        credits_used = 20
                    else:
                        ai_response, credits_used = await self._generate_with_gpt(session, message, request_type, credits, settings)
                    
                    if credits_used > 0:
                        await self.deduct_credits(user_id, credits_used, f"{request_type} generation")
                        
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    ai_response = """## ❌ حدث خطأ

عذراً، حدث خطأ أثناء المعالجة.

> 🔄 يرجى المحاولة مرة أخرى"""
        
        assistant_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": ai_response.strip(),
            "message_type": "text",
            "attachments": attachments,
            "metadata": {
                "request_type": request_type,
                "credits_used": credits_used,
                "credits_remaining": credits - credits_used
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        update_data = {
            "$push": {"messages": {"$each": [user_msg, assistant_msg]}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
        
        code_match = re.search(r'```(?:html|javascript|js)?\n?([\s\S]*?)```', ai_response)
        if code_match:
            code = code_match.group(1)
            code_with_badge = inject_zitex_badge(code)
            update_data["$set"]["generated_code"] = code_with_badge
            update_data["$set"]["session_type"] = request_type
        
        await self.db.chat_sessions.update_one({"id": session_id}, update_data)
        
        non_welcome_messages = [m for m in session.get("messages", []) if not m.get("metadata", {}).get("is_welcome")]
        if len(non_welcome_messages) == 0:
            title = self._generate_title(message, request_type)
            await self.db.chat_sessions.update_one({"id": session_id}, {"$set": {"title": title}})
        
        return {
            "session_id": session_id,
            "user_message": user_msg,
            "assistant_message": assistant_msg,
            "credits_used": credits_used
        }
    
    async def _generate_image(self, user_id: str, session_id: str, prompt: str, credits: int) -> Tuple[str, List[Dict], int]:
        try:
            enhanced_prompt = f"High quality, professional, detailed: {prompt}"
            
            image_response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = image_response.data[0].url
            
            asset = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "session_id": session_id,
                "asset_type": "image",
                "url": image_url,
                "prompt": prompt,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await self.db.generated_assets.insert_one(asset)
            
            response = f"""## ✅ تم إنشاء الصورة!

| التفاصيل | القيمة |
|----------|--------|
| **الوصف** | {prompt[:50]}... |
| **الجودة** | عالية (1024x1024) |
| **التكلفة** | 5 نقاط |
| **رصيدك المتبقي** | {credits - 5} نقطة |

> 💡 يمكنك طلب تعديلات أو صورة جديدة"""
            
            attachments = [{"type": "image", "url": image_url, "prompt": prompt}]
            return response, attachments, 5
            
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return f"## ❌ خطأ في توليد الصورة\n\n> {str(e)[:100]}", [], 0
    
    async def _generate_with_gpt(self, session: Dict, message: str, request_type: str, credits: int, settings: Dict) -> Tuple[str, int]:
        system_prompt = MASTER_SYSTEM_PROMPT + f"\n\n> معلومات العميل: رصيده الحالي {credits} نقطة"
        
        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in session.get("messages", [])[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        messages.append({"role": "user", "content": message})
        
        try:
            completion = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=8000
            )
            response = completion.choices[0].message.content
            
            credits_used = SERVICE_COSTS.get(request_type, 1)
            if '```html' in response or '```javascript' in response:
                credits_used = SERVICE_COSTS.get(request_type, 15)
            
            return response, credits_used
            
        except Exception as e:
            logger.error(f"GPT generation error: {e}")
            return f"## ❌ خطأ في المعالجة\n\n> {str(e)[:100]}", 0
    
    def _generate_title(self, message: str, request_type: str) -> str:
        type_prefixes = {
            "image": "🎨", "video": "🎬", "website": "🌐",
            "game": "🎮", "game_3d": "🎮", "webapp": "💻",
            "pwa": "📱", "general": "💬"
        }
        prefix = type_prefixes.get(request_type, "💬")
        title = message[:30].strip()
        if len(message) > 30:
            title += "..."
        return f"{prefix} {title}"
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        result = await self.db.chat_sessions.update_one(
            {"id": session_id, "user_id": user_id},
            {"$set": {"status": "archived"}}
        )
        return result.modified_count > 0
    
    async def get_session_assets(self, session_id: str, user_id: str) -> List[Dict]:
        assets = await self.db.generated_assets.find(
            {"session_id": session_id, "user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        return assets
    
    async def get_video_requests(self, user_id: str, session_id: str = None) -> List[Dict]:
        query = {"user_id": user_id}
        if session_id:
            query["session_id"] = session_id
        requests = await self.db.video_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
        return requests
    
    async def generate_tts(self, text: str, provider: str = "openai", voice: str = "alloy", speed: float = 1.0) -> Optional[str]:
        if not AI_FEATURES_ENABLED:
            return None
        try:
            if provider == "openai" and self.openai_client:
                response = self.openai_client.audio.speech.create(model="tts-1", voice=voice, input=text, speed=speed)
                audio_bytes = response.content
                audio_b64 = base64.b64encode(audio_bytes).decode()
                return f"data:audio/mpeg;base64,{audio_b64}"
            elif provider == "elevenlabs" and self.eleven_client and ELEVENLABS_AVAILABLE:
                voice_settings = VoiceSettings(stability=0.5, similarity_boost=0.75)
                audio_generator = self.eleven_client.text_to_speech.convert(text=text, voice_id=voice, model_id="eleven_multilingual_v2", voice_settings=voice_settings)
                audio_bytes = b""
                for chunk in audio_generator:
                    audio_bytes += chunk
                audio_b64 = base64.b64encode(audio_bytes).decode()
                return f"data:audio/mpeg;base64,{audio_b64}"
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
        return None
    
    async def update_session_code(self, session_id: str, user_id: str, code: str) -> bool:
        code_with_badge = inject_zitex_badge(code)
        result = await self.db.chat_sessions.update_one(
            {"id": session_id, "user_id": user_id},
            {"$set": {"generated_code": code_with_badge, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        return result.modified_count > 0
    
    async def get_session_code(self, session_id: str, user_id: str) -> Optional[str]:
        session = await self.get_session(session_id, user_id)
        if session:
            return session.get("generated_code")
        return None
