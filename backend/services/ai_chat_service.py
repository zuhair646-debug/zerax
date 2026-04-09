"""
Zitex AI Chat Service - Full Features
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
        image_keywords = ['صورة', 'صور', 'أنشئ صورة', 'ارسم', 'image', 'اريد صورة', 'ولد صورة']
        video_keywords = ['فيديو', 'فديو', 'مقطع', 'أنشئ فيديو', 'video', 'اريد فيديو', 'اصنع فيديو', 'ولد فيديو']
        website_keywords = ['موقع', 'صفحة ويب', 'website', 'html', 'أنشئ موقع', 'اصنع موقع', 'ولد موقع']
        
        is_image = any(kw in msg_lower for kw in image_keywords)
        is_video = any(kw in msg_lower for kw in video_keywords)
        is_website = any(kw in msg_lower for kw in website_keywords)
        
        if not self.openai_client:
            ai_response = "عذراً، خدمة الذكاء الاصطناعي غير متاحة."
        
        elif is_video:
            try:
                if not self.replicate_token or not REPLICATE_AVAILABLE:
                    ai_response = "عذراً، خدمة توليد الفيديو غير مفعّلة."
                else:
                    os.environ["REPLICATE_API_TOKEN"] = self.replicate_token
                    
                    output = replicate.run(
                        "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
                        input={"cond_aug": 0.02, "decoding_t": 7, "input_image": "https://replicate.delivery/pbxt/KRULC43USWlEx4ZVoiRRfAGwLx5D8dHRb9v4wKfBCcO0sobA/rocket.png", "video_length": "14_frames_with_svd", "sizing_strategy": "maintain_aspect_ratio", "motion_bucket_id": 127, "frames_per_second": 6}
                    )
                    
                    video_url = None
                    if output:
                        video_url = str(output)
                    
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
                ai_response = f"عذراً، حدث خطأ في الفيديو: {str(e)[:100]}"
        
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
        
        elif is_website:
            try:
                completion = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "أنت مطور ويب محترف. أنشئ كود HTML+CSS+JS كامل وجميل للموقع المطلوب. أرجع الكود فقط."},
                        {"role": "user", "content": f"أنشئ موقع: {message}"}
                    ]
                )
                code = completion.choices[0].message.content
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
                ai_response = f"تم إنشاء الموقع بنجاح! 🌐\n\n```html\n{code[:3000]}\n```"
                attachments = [{"type": "website", "code": code}]
                msg_type = "website"
            except Exception as e:
                logger.error(f"Website error: {e}")
                ai_response = f"عذراً، حدث خطأ: {str(e)[:100]}"
        
        else:
            try:
                messages = [{"role": "system", "content": "أنت زيتكس، مساعد ذكي. يمكنك توليد الصور (قل: أنشئ صورة) والفيديوهات (قل: أنشئ فيديو) والمواقع (قل: أنشئ موقع). أجب بالعربية."}]
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
