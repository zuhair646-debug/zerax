"""
Zitex AI Chat Service - GPT-5.2 + Sora 2 + GPT Image 1 + TTS
دعم: الصور، الفيديوهات السينمائية مع تعليق صوتي، المواقع، الألعاب 3D
"""
import os
import uuid
import logging
import json
import re
import httpx
import base64
import tempfile
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# OpenAI for Chat and Images
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

# Emergent Integrations for Sora 2
try:
    from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
    SORA_AVAILABLE = True
except ImportError:
    SORA_AVAILABLE = False
    OpenAIVideoGeneration = None

AI_FEATURES_ENABLED = True

class AIAssistant:
    def __init__(self, db: AsyncIOMotorDatabase, api_key: str = None, elevenlabs_key: str = None, **kwargs):
        self.db = db
        self.openai_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.emergent_key = os.environ.get('EMERGENT_LLM_KEY')
        self.vercel_token = os.environ.get('VERCEL_TOKEN')
        self.elevenlabs_key = elevenlabs_key or os.environ.get('ELEVENLABS_API_KEY')
        
        # OpenAI Client for GPT-5.2 and Images
        self.openai_client = None
        if OPENAI_AVAILABLE and self.openai_key:
            try:
                self.openai_client = OpenAI(api_key=self.openai_key)
                logger.info("✅ OpenAI client initialized (GPT-5.2, GPT Image 1)")
            except Exception as e:
                logger.error(f"OpenAI init error: {e}")
        
        # ElevenLabs for TTS
        self.eleven_client = None
        try:
            from elevenlabs.client import ElevenLabs
            from elevenlabs.types import VoiceSettings
            if self.elevenlabs_key:
                self.eleven_client = ElevenLabs(api_key=self.elevenlabs_key)
                self.VoiceSettings = VoiceSettings
                logger.info("✅ ElevenLabs client initialized")
        except ImportError:
            logger.warning("⚠️ ElevenLabs not available")
    
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
    
    async def chat_gpt5(self, messages: list, system_prompt: str = None) -> str:
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        chat_messages.extend(messages)
        response = self.openai_client.chat.completions.create(
            model="gpt-5.2",
            messages=chat_messages,
            max_tokens=4096,
            temperature=0.7
        )
        return response.choices[0].message.content
       async def generate_image_gpt(self, prompt: str, size: str = "1024x1024") -> str:
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        response = self.openai_client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size=size,
            quality="high",
            n=1
        )
        # gpt-image-1 returns b64_json, not url
        if response.data[0].b64_json:
            return f"data:image/png;base64,{response.data[0].b64_json}"
        elif response.data[0].url:
            return response.data[0].url
        else:
            raise ValueError("No image data returned")
    
    async def generate_video_sora2(self, prompt: str, duration: int = 8, size: str = "1792x1024") -> Dict:
        api_key = self.emergent_key or self.openai_key
        if not api_key:
            raise ValueError("No API key available for video generation")
        if not SORA_AVAILABLE:
            raise ValueError("emergentintegrations library not installed")
        valid_durations = [4, 8, 12]
        if duration not in valid_durations:
            duration = min(valid_durations, key=lambda x: abs(x - duration))
        valid_sizes = ["1280x720", "1792x1024", "1024x1792", "1024x1024"]
        if size not in valid_sizes:
            size = "1792x1024"
        logger.info(f"🎬 Generating Sora 2 video: {prompt[:50]}... (duration: {duration}s, size: {size})")
        try:
            video_gen = OpenAIVideoGeneration(api_key=api_key)
            video_bytes = video_gen.text_to_video(
                prompt=prompt,
                model="sora-2",
                size=size,
                duration=duration,
                max_wait_time=600
            )
            if video_bytes:
                temp_path = f"/tmp/video_{uuid.uuid4().hex[:8]}.mp4"
                video_gen.save_video(video_bytes, temp_path)
                with open(temp_path, 'rb') as f:
                    video_b64 = base64.b64encode(f.read()).decode()
                os.remove(temp_path)
                video_url = f"data:video/mp4;base64,{video_b64}"
                logger.info(f"✅ Video generated successfully ({duration}s, {size})")
                return {"url": video_url, "duration": duration, "size": size, "model": "sora-2"}
            else:
                raise ValueError("Video generation returned no data")
        except Exception as e:
            logger.error(f"Sora 2 error: {e}")
            raise
    
    async def generate_voiceover(self, text: str, voice: str = "alloy") -> str:
        if self.openai_client:
            try:
                response = self.openai_client.audio.speech.create(
                    model="tts-1-hd",
                    voice=voice,
                    input=text
                )
                audio_b64 = base64.b64encode(response.content).decode()
                return f"data:audio/mp3;base64,{audio_b64}"
            except Exception as e:
                logger.error(f"OpenAI TTS error: {e}")
        if self.eleven_client:
            try:
                voice_settings = self.VoiceSettings(stability=0.5, similarity_boost=0.75)
                audio_generator = self.eleven_client.text_to_speech.convert(
                    text=text,
                    voice_id="21m00Tcm4TlvDq8ikWAM",
                    model_id="eleven_multilingual_v2",
                    voice_settings=voice_settings
                )
                audio_data = b""
                for chunk in audio_generator:
                    audio_data += chunk
                audio_b64 = base64.b64encode(audio_data).decode()
                return f"data:audio/mpeg;base64,{audio_b64}"
            except Exception as e:
                logger.error(f"ElevenLabs TTS error: {e}")
        return None
    
    async def deploy_to_vercel(self, project_name: str, files: dict) -> Dict:
        if not self.vercel_token:
            return {"success": False, "error": "Vercel token not configured"}
        try:
            vercel_files = []
            for filename, content in files.items():
                if isinstance(content, str):
                    vercel_files.append({"file": filename, "data": content})
                else:
                    vercel_files.append({"file": filename, "data": json.dumps(content)})
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.vercel.com/v13/deployments",
                    headers={
                        "Authorization": f"Bearer {self.vercel_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "name": project_name.lower().replace(" ", "-").replace("_", "-"),
                        "files": vercel_files,
                        "projectSettings": {"framework": None}
                    },
                    timeout=120.0
                )
                if response.status_code in [200, 201]:
                    data = response.json()
                    return {
                        "success": True,
                        "url": f"https://{data.get('url', '')}",
                        "deployment_id": data.get('id', ''),
                        "status": "deployed"
                    }
                else:
                    return {"success": False, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def process_message(self, session_id: str, user_id: str, message: str, settings: Dict[str, Any] = None) -> Dict:
        session = await self.get_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found")
         settings = settings or {}
        
        # === خصم النقاط ===
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0})
        is_owner = user and (user.get("is_owner", False) or user.get("role") == "owner")
        user_credits = user.get("credits", 0) if user else 0
        
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
        
        image_keywords = ['صورة', 'صور', 'أنشئ صورة', 'ارسم', 'image', 'اريد صورة', 'ولد صورة', 'اصنع صورة']
        video_keywords = ['فيديو', 'فديو', 'مقطع', 'أنشئ فيديو', 'video', 'اريد فيديو', 'اصنع فيديو', 'ولد فيديو', 'سينمائي']
        website_keywords = ['موقع', 'صفحة ويب', 'website', 'html', 'أنشئ موقع', 'اصنع موقع', 'ولد موقع', 'صفحة']
        game_keywords = ['لعبة', 'game', '3d', 'ثلاثية', 'العاب', 'أنشئ لعبة', 'اصنع لعبة', 'babylon']
        app_keywords = ['تطبيق', 'برنامج', 'app', 'application', 'أنشئ تطبيق', 'اصنع تطبيق', 'موبايل']
        deploy_keywords = ['انشر', 'deploy', 'رفع', 'نشر', 'ارفع', 'publish']
        voiceover_keywords = ['تعليق صوتي', 'صوت', 'voiceover', 'narration', 'تعليق', 'راوي']
        
        is_image = any(kw in msg_lower for kw in image_keywords)
        is_video = any(kw in msg_lower for kw in video_keywords)
        is_website = any(kw in msg_lower for kw in website_keywords)
        is_game = any(kw in msg_lower for kw in game_keywords)
        is_app = any(kw in msg_lower for kw in app_keywords)
        is_deploy = any(kw in msg_lower for kw in deploy_keywords)
        wants_voiceover = any(kw in msg_lower for kw in voiceover_keywords)
        
        if not self.openai_client:
            ai_response = "عذراً، خدمة الذكاء الاصطناعي غير متاحة. تأكد من إعداد OPENAI_API_KEY."
        
        elif is_video:
            try:
                duration = 8
                if '12' in msg_lower or 'طويل' in msg_lower:
                    duration = 12
                elif '4' in msg_lower or 'قصير' in msg_lower:
                    duration = 4
                size = "1792x1024"
                
                video_result = await self.generate_video_sora2(message, duration, size)
                
                if video_result and video_result.get("url"):
                    voiceover_url = None
                    if wants_voiceover:
                        voiceover_text = await self.chat_gpt5(
                            [{"role": "user", "content": f"اكتب تعليق صوتي قصير (20-30 كلمة) لفيديو عن: {message}"}],
                            "اكتب تعليق صوتي احترافي بالعربية. قصير ومؤثر."
                        )
                        voiceover_url = await self.generate_voiceover(voiceover_text)
                    
                    asset = {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "session_id": session_id,
                        "asset_type": "video",
                        "url": video_result["url"],
                        "voiceover_url": voiceover_url,
                        "prompt": message,
                        "duration": duration,
                        "size": size,
                        "model": "sora-2",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    await self.db.generated_assets.insert_one(asset)
                    
                    voiceover_msg = "\n🎙️ تعليق صوتي: متاح" if voiceover_url else ""
                     # خصم النقاط للفيديو
                    if not is_owner and user_credits >= 20:
                        await self.db.users.update_one({"id": user_id}, {"$inc": {"credits": -20}})
                    ai_response = f"✅ تم إنشاء الفيديو السينمائي بنجاح! 🎬 (تم خصم 20 نقطة)\n\n📹 المدة: {duration} ثانية\n📐 الدقة: {size} (Full HD+)\n🤖 النموذج: Sora 2{voiceover_msg}"\n\n📹 المدة: {duration} ثانية\n📐 الدقة: {size} (Full HD+)\n🤖 النموذج: Sora 2{voiceover_msg}"
                    
                    attachment_data = {"type": "video", "url": video_result["url"], "duration": duration, "size": size, "id": asset["id"]}
                    if voiceover_url:
                        attachment_data["voiceover_url"] = voiceover_url
                    attachments = [attachment_data]
                    msg_type = "video"
                else:
                    ai_response = "عذراً، فشل في إنشاء الفيديو. حاول مرة أخرى."
            except Exception as e:
                logger.error(f"Video error: {e}")
                ai_response = f"عذراً، حدث خطأ في الفيديو: {str(e)[:150]}"
        
        elif is_image:
            try:
                image_url = await self.generate_image_gpt(message)
                asset = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "session_id": session_id,
                    "asset_type": "image",
                    "url": image_url,
                    "prompt": message,
                    "model": "gpt-image-1",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await self.db.generated_assets.insert_one(asset)
                # خصم النقاط للصورة
                if not is_owner and user_credits >= 5:
                    await self.db.users.update_one({"id": user_id}, {"$inc": {"credits": -5}})
                ai_response = "✅ تم إنشاء الصورة بنجاح! 🎨 (تم خصم 5 نقاط)\n🤖 النموذج: GPT Image 1"
                attachments = [{"type": "image", "url": image_url, "id": asset["id"]}]
                msg_type = "image"
            except Exception as e:
                logger.error(f"Image error: {e}")
                ai_response = f"عذراً، حدث خطأ في الصورة: {str(e)[:100]}"
        
        elif is_game:
        
        elif is_game:
            try:
                completion = self.openai_client.chat.completions.create(
                    model="gpt-5.2",
                    messages=[
                        {"role": "system", "content": "أنت مطور ألعاب محترف. أنشئ لعبة ثلاثية الأبعاد باستخدام Babylon.js. استخدم CDN وأنشئ مشهد 3D كامل مع إضاءة وكاميرا وتفاعل. أرجع ملف HTML واحد كامل فقط بدون شرح."},
                        {"role": "user", "content": f"أنشئ لعبة 3D: {message}"}
                    ],
                    max_tokens=4096
                )
                code = completion.choices[0].message.content.replace("```html", "").replace("```", "").strip()
                asset = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "session_id": session_id,
                    "asset_type": "game",
                    "code": code,
                    "prompt": message,
                    "tech": "babylon.js",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await self.db.generated_assets.insert_one(asset)
                deploy_result = None
                if is_deploy and self.vercel_token:
                    deploy_result = await self.deploy_to_vercel(f"zitex-game-{asset['id'][:8]}", {"index.html": code})
                if deploy_result and deploy_result.get("success"):
                    ai_response = f"✅ تم إنشاء اللعبة ونشرها! 🎮\n\n🔗 الرابط: {deploy_result.get('url')}"
                    attachments = [{"type": "game", "code": code, "id": asset["id"], "url": deploy_result.get('url')}]
                else:
                    ai_response = "✅ تم إنشاء اللعبة بنجاح! 🎮\n\nقل 'انشر اللعبة' لرفعها على رابط مباشر!"
                    attachments = [{"type": "game", "code": code, "id": asset["id"]}]
                msg_type = "game"
            except Exception as e:
                logger.error(f"Game error: {e}")
                ai_response = f"عذراً، حدث خطأ: {str(e)[:100]}"
        
        elif is_website:
            try:
                completion = self.openai_client.chat.completions.create(
                    model="gpt-5.2",
                    messages=[
                        {"role": "system", "content": "أنت مطور ويب محترف. أنشئ موقع HTML+CSS+JS كامل وعصري responsive مع ألوان جميلة. أرجع الكود فقط."},
                        {"role": "user", "content": f"أنشئ موقع: {message}"}
                    ],
                    max_tokens=4096
                )
                code = completion.choices[0].message.content.replace("```html", "").replace("```", "").strip()
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
                deploy_result = None
                if is_deploy and self.vercel_token:
                    deploy_result = await self.deploy_to_vercel(f"zitex-site-{asset['id'][:8]}", {"index.html": code})
                if deploy_result and deploy_result.get("success"):
                    ai_response = f"✅ تم إنشاء الموقع ونشره! 🌐\n\n🔗 الرابط: {deploy_result.get('url')}"
                    attachments = [{"type": "website", "code": code, "id": asset["id"], "url": deploy_result.get('url')}]
                else:
                    ai_response = "✅ تم إنشاء الموقع بنجاح! 🌐\n\nقل 'انشر الموقع' لرفعه على رابط مباشر!"
                    attachments = [{"type": "website", "code": code, "id": asset["id"]}]
                msg_type = "website"
            except Exception as e:
                logger.error(f"Website error: {e}")
                ai_response = f"عذراً، حدث خطأ: {str(e)[:100]}"
        
        elif is_deploy:
            try:
                last_asset = await self.db.generated_assets.find_one(
                    {"user_id": user_id, "asset_type": {"$in": ["website", "game", "app"]}},
                    {"_id": 0},
                    sort=[("created_at", -1)]
                )
                if last_asset and last_asset.get("code"):
                    deploy_result = await self.deploy_to_vercel(
                        f"zitex-{last_asset['asset_type']}-{last_asset['id'][:8]}",
                        {"index.html": last_asset["code"]}
                    )
                    if deploy_result.get("success"):
                        await self.db.generated_assets.update_one(
                            {"id": last_asset["id"]},
                            {"$set": {"deployed_url": deploy_result.get('url')}}
                        )
                        ai_response = f"✅ تم النشر بنجاح! 🚀\n\n🔗 الرابط: {deploy_result.get('url')}"
                        attachments = [{"type": "deployment", "url": deploy_result.get('url')}]
                    else:
                        ai_response = f"عذراً، فشل النشر: {deploy_result.get('error', 'خطأ غير معروف')}"
                else:
                    ai_response = "لم أجد مشروع سابق للنشر. أنشئ موقع أو لعبة أولاً!"
            except Exception as e:
                ai_response = f"عذراً، حدث خطأ في النشر: {str(e)[:100]}"
        
        elif is_app:
            try:
                completion = self.openai_client.chat.completions.create(
                    model="gpt-5.2",
                    messages=[
                        {"role": "system", "content": "أنت مطور تطبيقات محترف. أنشئ كود React Native للتطبيق المطلوب مع تعليقات توضيحية."},
                        {"role": "user", "content": f"أنشئ تطبيق: {message}"}
                    ],
                    max_tokens=4096
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
                ai_response = f"✅ تم إنشاء التطبيق! 📱\n\n{code[:2500]}"
                attachments = [{"type": "app", "code": code, "id": asset["id"]}]
                msg_type = "app"
            except Exception as e:
                ai_response = f"عذراً، حدث خطأ: {str(e)[:100]}"
        
        else:
            try:
                messages_list = [{"role": "system", "content": "أنت زيتكس، مساعد ذكي يعمل بـ GPT-5.2. قدراتك: 🎨 صور، 🎬 فيديو (4/8/12 ثانية)، 🎙️ تعليق صوتي، 🌐 مواقع، 🎮 ألعاب 3D، 📱 تطبيقات، 🚀 نشر تلقائي. أجب بالعربية."}]
                for msg in session.get("messages", [])[-10:]:
                    messages_list.append({"role": msg["role"], "content": msg["content"]})
                messages_list.append({"role": "user", "content": message})
                ai_response = await self.chat_gpt5(messages_list)
            except Exception as e:
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
