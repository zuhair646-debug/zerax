"""
Zitex AI Chat Service - Full Features
دعم: الصور، الفيديوهات، المواقع، التطبيقات، الصوت
"""
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    import replicate
    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False
    replicate = None

AI_FEATURES_ENABLED = True


class AIAssistant:
    def __init__(self, db: AsyncIOMotorDatabase, api_key: str = None, **kwargs):
        self.db = db
        self.openai_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.replicate_token = os.environ.get('REPLICATE_API_TOKEN')
        
        self.openai_client = None
        if OPENAI_AVAILABLE and self.openai_key:
            try:
                self.openai_client = openai.OpenAI(api_key=self.openai_key)
            except Exception as e:
                logger.error(f"OpenAI init error: {e}")
    
    async def create_session(self, user_id: str, session_type: str = "general", title: str = None) -> Dict:
        session = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title or "محادثة جديدة",
            "session_type": session_type,
            "messages": [],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await self.db.chat_sessions.insert_one(session)
        return session
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict]:
        return await self.db.chat_sessions.find_one({"id": session_id, "user_id": user_id}, {"_id": 0})
    
    async def get_user_sessions(self, user_id: str, limit: int = 50) -> List[Dict]:
        return await self.db.chat_sessions.find(
            {"user_id": user_id, "status": "active"}, {"_id": 0}
        ).sort("updated_at", -1).limit(limit).to_list(limit)
    
    async def process_message(self, session_id: str, user_id: str, message: str, settings: Dict[str, Any] = None) -> Dict:
        session = await self.get_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found")
        
        user_msg = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": message,
            "message_type": "text",
            "attachments": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        ai_response = ""
        attachments = []
        msg_type = "text"
        
        msg_lower = message.lower()
        
        # Keywords
        image_keywords = ['صورة', 'صور', 'أنشئ صورة', 'ارسم', 'image', 'اريد صورة', 'ولد صورة', 'اصنع صورة']
        video_keywords = ['فيديو', 'فديو', 'مقطع', 'أنشئ فيديو', 'video', 'اريد فيديو', 'اصنع فيديو', 'ولد فيديو']
        website_keywords = ['موقع', 'صفحة ويب', 'website', 'html', 'أنشئ موقع', 'اصنع موقع', 'ولد موقع', 'صفحة']
        app_keywords = ['تطبيق', 'برنامج', 'app', 'application', 'أنشئ تطبيق', 'اصنع تطبيق', 'موبايل']
        voice_keywords = ['صوت', 'اقرأ', 'تحدث', 'voice', 'audio', 'speak', 'نطق', 'حول لصوت', 'اسمع']
        
        is_image = any(kw in msg_lower for kw in image_keywords)
        is_video = any(kw in msg_lower for kw in video_keywords)
        is_website = any(kw in msg_lower for kw in website_keywords)
        is_app = any(kw in msg_lower for kw in app_keywords)
        is_voice = any(kw in msg_lower for kw in voice_keywords)
        
        if not self.openai_client:
            ai_response = "عذراً، خدمة الذكاء الاصطناعي غير متاحة."
        
        # === VIDEO GENERATION ===
        elif is_video:
            try:
                if not self.replicate_token or not REPLICATE_AVAILABLE:
                    ai_response = "عذراً، خدمة توليد الفيديو غير مفعّلة."
                else:
                    os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
                    
                    output = replicate.run(
                        "minimax/video-01",
                        input={
                            "prompt": message,
                            "prompt_optimizer": True
                        }
                    )
                    
                    video_url = str(output) if output else None
                    
                    if video_url:
                        asset = {
                            "id": str(uuid.uuid4()),
                            "user_id": user_id,
                            "session_id": session_id,
                            "asset_type": "video",
                            "url": video_url,
                            "prompt": message,
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }
                        await self.db.generated_assets.insert_one(asset)
                        ai_response = "تم إنشاء الفيديو بنجاح! 🎬"
                        attachments = [{"type": "video", "url": video_url}]
                        msg_type = "video"
                    else:
                        ai_response = "عذراً، فشل في إنشاء الفيديو."
            except Exception as e:
                logger.error(f"Video error: {e}")
                ai_response = f"عذراً، حدث خطأ في الفيديو: {str(e)[:150]}"
        
        # === IMAGE GENERATION ===
        elif is_image:
            try:
                response = self.openai_client.images.generate(
                    model="dall-e-3",
                    prompt=message,
                    size="1024x1024",
                    n=1
                )
                image_url = response.data[0].url
                asset = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "session_id": session_id,
                    "asset_type": "image",
                    "url": image_url,
                    "prompt": message,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await self.db.generated_assets.insert_one(asset)
                ai_response = "تم إنشاء الصورة بنجاح! 🎨"
                attachments = [{"type": "image", "url": image_url}]
                msg_type = "image"
            except Exception as e:
                logger.error(f"Image error: {e}")
                ai_response = f"عذراً، حدث خطأ في الصورة: {str(e)[:100]}"
        
        # === WEBSITE GENERATION ===
        elif is_website:
            try:
                completion = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": """أنت مطور ويب محترف. أنشئ كود HTML+CSS+JS كامل وجميل وعصري للموقع المطلوب.
                        - استخدم تصميم responsive
                        - أضف ألوان جميلة ومتناسقة
                        - أضف animations بسيطة
                        - اجعل الكود في ملف واحد
                        - أرجع الكود فقط بدون شرح"""},
                        {"role": "user", "content": f"أنشئ موقع: {message}"}
                    ]
                )
                code = completion.choices[0].message.content
                code = code.replace("```html", "").replace("```", "").strip()
                
                asset = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "session_id": session_id,
                    "asset_type": "website",
                    "code": code,
                    "prompt": message,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await self.db.generated_assets.insert_one(asset)
                ai_response = f"تم إنشاء الموقع بنجاح! 🌐\n\n```html\n{code[:2500]}\n```"
                attachments = [{"type": "website", "code": code, "id": asset["id"]}]
                msg_type = "website"
            except Exception as e:
                logger.error(f"Website error: {e}")
                ai_response = f"عذراً، حدث خطأ: {str(e)[:100]}"
        
        # === APP GENERATION ===
        elif is_app:
            try:
                completion = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": """أنت مطور تطبيقات محترف. أنشئ كود React Native أو Flutter للتطبيق المطلوب.
                        - اكتب كود نظيف ومنظم
                        - أضف تعليقات توضيحية
                        - اجعله قابل للتشغيل
                        - أرجع الكود مع شرح بسيط للتثبيت"""},
                        {"role": "user", "content": f"أنشئ تطبيق: {message}"}
                    ]
                )
                code = completion.choices[0].message.content
                
                asset = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "session_id": session_id,
                    "asset_type": "app",
                    "code": code,
                    "prompt": message,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await self.db.generated_assets.insert_one(asset)
                ai_response = f"تم إنشاء كود التطبيق بنجاح! 📱\n\n{code[:3000]}"
                attachments = [{"type": "app", "code": code, "id": asset["id"]}]
                msg_type = "app"
            except Exception as e:
                logger.error(f"App error: {e}")
                ai_response = f"عذراً، حدث خطأ: {str(e)[:100]}"
        
        # === VOICE/AUDIO GENERATION ===
        elif is_voice:
            try:
                text_to_speak = message.replace("صوت", "").replace("اقرأ", "").replace("تحدث", "").strip()
                if len(text_to_speak) < 5:
                    text_to_speak = "مرحباً، أنا زيتكس مساعدك الذكي."
                
                speech_response = self.openai_client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",
                    input=text_to_speak
                )
                
                audio_filename = f"audio_{uuid.uuid4().hex[:8]}.mp3"
                audio_path = f"/tmp/{audio_filename}"
                
                with open(audio_path, "wb") as f:
                    f.write(speech_response.content)
                
                asset = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "session_id": session_id,
                    "asset_type": "audio",
                    "text": text_to_speak,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await self.db.generated_assets.insert_one(asset)
                ai_response = f"تم إنشاء الصوت بنجاح! 🔊\nالنص: {text_to_speak[:100]}"
                attachments = [{"type": "audio", "text": text_to_speak}]
                msg_type = "audio"
            except Exception as e:
                logger.error(f"Voice error: {e}")
                ai_response = f"عذراً، حدث خطأ في الصوت: {str(e)[:100]}"
        
        # === REGULAR CHAT ===
        else:
            try:
                messages = [{"role": "system", "content": """أنت زيتكس، مساعد ذكي متعدد القدرات. يمكنك:
                - توليد الصور (قل: أنشئ صورة...)
                - توليد الفيديوهات (قل: أنشئ فيديو...)
                - إنشاء المواقع (قل: أنشئ موقع...)
                - إنشاء التطبيقات (قل: أنشئ تطبيق...)
                - تحويل النص لصوت (قل: حول لصوت...)
                أجب بالعربية دائماً وكن مفيداً."""}]
                
                for msg in session.get("messages", [])[-10:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                messages.append({"role": "user", "content": message})
                
                completion = self.openai_client.chat.completions.create(model="gpt-4o", messages=messages)
                ai_response = completion.choices[0].message.content
            except Exception as e:
                logger.error(f"Chat error: {e}")
                ai_response = f"عذراً، حدث خطأ: {str(e)[:100]}"
        
        assistant_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": ai_response,
            "message_type": msg_type,
            "attachments": attachments,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.chat_sessions.update_one(
            {"id": session_id},
            {"$push": {"messages": {"$each": [user_msg, assistant_msg]}}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {"session_id": session_id, "user_message": user_msg, "assistant_message": assistant_msg}
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        result = await self.db.chat_sessions.update_one({"id": session_id, "user_id": user_id}, {"$set": {"status": "archived"}})
        return result.modified_count > 0
    
    async def get_session_assets(self, session_id: str, user_id: str) -> List[Dict]:
        return await self.db.generated_assets.find({"session_id": session_id, "user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    async def get_video_requests(self, user_id: str, session_id: str = None) -> List[Dict]:
        query = {"user_id": user_id}
        if session_id:
            query["session_id"] = session_id
        return await self.db.video_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
