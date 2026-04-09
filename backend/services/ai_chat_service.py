"""
Zitex AI Chat Service - GPT-5.2 + Sora 2 + GPT Image 1 + Babylon.js
دعم: الصور، الفيديوهات السينمائية (60 ثانية)، المواقع، الألعاب 3D، التطبيقات
"""
import os
import uuid
import logging
import json
import re
import httpx
import base64
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

AI_FEATURES_ENABLED = True

class AIAssistant:
    def __init__(self, db: AsyncIOMotorDatabase, api_key: str = None, **kwargs):
        self.db = db
        self.openai_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.vercel_token = os.environ.get('VERCEL_TOKEN')
        
        self.openai_client = None
        if OPENAI_AVAILABLE and self.openai_key:
            try:
                self.openai_client = OpenAI(api_key=self.openai_key)
                logger.info("✅ OpenAI client initialized (GPT-5.2, Sora 2, GPT Image 1)")
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
    
    # ============== GPT-5.2 CHAT ==============
    async def chat_gpt5(self, messages: list, system_prompt: str = None) -> str:
        """Chat with GPT-5.2"""
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
    
    # ============== GPT IMAGE 1 ==============
    async def generate_image_gpt(self, prompt: str, size: str = "1024x1024") -> str:
        """Generate image using GPT Image 1"""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        response = self.openai_client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size=size,
            quality="high",
            n=1
        )
        return response.data[0].url
    
    # ============== SORA 2 VIDEO (60 seconds) ==============
    async def generate_video_sora2(self, prompt: str, duration: int = 10, size: str = "1280x720") -> str:
        """Generate video using Sora 2 (up to 60 seconds)"""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        if duration > 60:
            duration = 60
        
        logger.info(f"🎬 Generating Sora 2 video: {prompt[:50]}... (duration: {duration}s)")
        
        response = self.openai_client.videos.generate(
            model="sora-2",
            prompt=prompt,
            duration=duration,
            size=size
        )
        
        logger.info(f"✅ Video generated successfully")
        return response.url
    
    # ============== DESIGN PLAN ==============
    async def create_design_plan(self, user_request: str, project_type: str = "website") -> Dict:
        """Create design plan before building"""
        system_prompt = """أنت مصمم ومطور محترف. عند استلام طلب:

1. حلل الطلب بعناية
2. أنشئ خطة تصميمية شاملة

رد بصيغة JSON فقط:
{
    "title": "عنوان المشروع",
    "description": "وصف تفصيلي",
    "features": ["ميزة 1", "ميزة 2"],
    "tech_stack": ["التقنيات المستخدمة"],
    "estimated_time": "الوقت المتوقع",
    "file_structure": ["الملفات"],
    "preview_description": "وصف قصير للنتيجة"
}"""
        
        messages = [{"role": "user", "content": f"نوع المشروع: {project_type}\n\nالطلب: {user_request}"}]
        response = await self.chat_gpt5(messages, system_prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                plan = json.loads(json_match.group())
                plan['id'] = str(uuid.uuid4())
                plan['status'] = 'pending'
                plan['project_type'] = project_type
                return plan
        except:
            pass
        
        return {
            "id": str(uuid.uuid4()),
            "title": "مشروع جديد",
            "description": response,
            "features": [],
            "tech_stack": [],
            "estimated_time": "غير محدد",
            "status": "pending",
            "project_type": project_type
        }
    
    # ============== VERCEL DEPLOYMENT ==============
    async def deploy_to_vercel(self, project_name: str, files: dict) -> Dict:
        """Deploy to Vercel automatically"""
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
                    logger.error(f"Vercel error: {response.text}")
                    return {"success": False, "error": response.text}
        except Exception as e:
            logger.error(f"Deployment error: {e}")
            return {"success": False, "error": str(e)}
    
    # ============== MAIN PROCESS MESSAGE ==============
    async def process_message(self, session_id: str, user_id: str, message: str, settings: Dict[str, Any] = None) -> Dict:
        session = await self.get_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found")
        
        settings = settings or {}
        
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
        
        # Keywords Detection
        image_keywords = ['صورة', 'صور', 'أنشئ صورة', 'ارسم', 'image', 'اريد صورة', 'ولد صورة', 'اصنع صورة']
        video_keywords = ['فيديو', 'فديو', 'مقطع', 'أنشئ فيديو', 'video', 'اريد فيديو', 'اصنع فيديو', 'ولد فيديو', 'سينمائي']
        website_keywords = ['موقع', 'صفحة ويب', 'website', 'html', 'أنشئ موقع', 'اصنع موقع', 'ولد موقع', 'صفحة']
        game_keywords = ['لعبة', 'game', '3d', 'ثلاثية', 'العاب', 'أنشئ لعبة', 'اصنع لعبة', 'babylon']
        app_keywords = ['تطبيق', 'برنامج', 'app', 'application', 'أنشئ تطبيق', 'اصنع تطبيق', 'موبايل']
        deploy_keywords = ['انشر', 'deploy', 'رفع', 'نشر', 'ارفع', 'publish']
        plan_keywords = ['خطة', 'plan', 'تصميم', 'design', 'خطط']
        
        is_image = any(kw in msg_lower for kw in image_keywords)
        is_video = any(kw in msg_lower for kw in video_keywords)
        is_website = any(kw in msg_lower for kw in website_keywords)
        is_game = any(kw in msg_lower for kw in game_keywords)
        is_app = any(kw in msg_lower for kw in app_keywords)
        is_deploy = any(kw in msg_lower for kw in deploy_keywords)
        is_plan = any(kw in msg_lower for kw in plan_keywords)
        
        if not self.openai_client:
            ai_response = "عذراً، خدمة الذكاء الاصطناعي غير متاحة. تأكد من إعداد OPENAI_API_KEY."
        
        # === DESIGN PLAN ===
        elif is_plan and (is_website or is_game or is_app):
            try:
                project_type = "game" if is_game else ("app" if is_app else "website")
                plan = await self.create_design_plan(message, project_type)
                
                await self.db.design_plans.insert_one({
                    **plan,
                    "user_id": user_id,
                    "session_id": session_id,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                
                ai_response = f"""📋 **خطة المشروع: {plan.get('title', 'مشروع جديد')}**

📝 **الوصف:** {plan.get('description', '')}

✨ **الميزات:**
{chr(10).join(['• ' + f for f in plan.get('features', [])])}

🛠️ **التقنيات:** {', '.join(plan.get('tech_stack', []))}

⏱️ **الوقت المتوقع:** {plan.get('estimated_time', 'غير محدد')}

---
✅ هل توافق على الخطة؟ قل "نعم ابدأ" أو "عدّل الخطة" """
                
                attachments = [{"type": "plan", "data": plan}]
                msg_type = "plan"
            except Exception as e:
                logger.error(f"Plan error: {e}")
                ai_response = f"عذراً، حدث خطأ في إنشاء الخطة: {str(e)[:100]}"
        
        # === VIDEO GENERATION (SORA 2 - 60 seconds) ===
        elif is_video:
            try:
                duration = settings.get('duration', 10)
                size = settings.get('size', '1280x720')
                
                # Check for duration in message
                if 'دقيقة' in msg_lower or 'minute' in msg_lower or '60' in msg_lower:
                    duration = 60
                elif '30' in msg_lower:
                    duration = 30
                
                ai_response = f"🎬 جاري إنشاء فيديو سينمائي ({duration} ثانية) باستخدام Sora 2...\n\nهذا قد يستغرق بضع دقائق."
                
                video_url = await self.generate_video_sora2(message, duration, size)
                
                if video_url:
                    asset = {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "session_id": session_id,
                        "asset_type": "video",
                        "url": video_url,
                        "prompt": message,
                        "duration": duration,
                        "size": size,
                        "model": "sora-2",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    await self.db.generated_assets.insert_one(asset)
                    
                    ai_response = f"✅ تم إنشاء الفيديو السينمائي بنجاح! 🎬\n\n📹 المدة: {duration} ثانية\n📐 الدقة: {size}\n🤖 النموذج: Sora 2"
                    attachments = [{"type": "video", "url": video_url, "duration": duration, "size": size, "id": asset["id"]}]
                    msg_type = "video"
                else:
                    ai_response = "عذراً، فشل في إنشاء الفيديو."
            except Exception as e:
                logger.error(f"Video error: {e}")
                ai_response = f"عذراً، حدث خطأ في الفيديو: {str(e)[:150]}"
        
        # === IMAGE GENERATION (GPT Image 1) ===
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
                
                ai_response = "✅ تم إنشاء الصورة بنجاح! 🎨\n🤖 النموذج: GPT Image 1"
                attachments = [{"type": "image", "url": image_url, "id": asset["id"]}]
                msg_type = "image"
            except Exception as e:
                logger.error(f"Image error: {e}")
                ai_response = f"عذراً، حدث خطأ في الصورة: {str(e)[:100]}"
        
        # === 3D GAME GENERATION (Babylon.js) ===
        elif is_game:
            try:
                completion = self.openai_client.chat.completions.create(
                    model="gpt-5.2",
                    messages=[
                        {"role": "system", "content": """أنت مطور ألعاب محترف. أنشئ لعبة ثلاثية الأبعاد باستخدام Babylon.js.

متطلبات الكود:
- استخدم Babylon.js CDN
- أنشئ مشهد 3D كامل مع إضاءة وكاميرا
- أضف تفاعل مع المستخدم (لوحة المفاتيح/الماوس)
- أضف فيزياء بسيطة
- اجعل اللعبة ممتعة وقابلة للعب
- أرجع ملف HTML واحد كامل

رد بالكود فقط بدون شرح."""},
                        {"role": "user", "content": f"أنشئ لعبة 3D: {message}"}
                    ],
                    max_tokens=4096
                )
                
                code = completion.choices[0].message.content
                code = code.replace("```html", "").replace("```", "").strip()
                
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
                
                # Auto deploy if requested
                deploy_result = None
                if is_deploy and self.vercel_token:
                    deploy_result = await self.deploy_to_vercel(f"zitex-game-{asset['id'][:8]}", {"index.html": code})
                
                if deploy_result and deploy_result.get("success"):
                    ai_response = f"""✅ تم إنشاء اللعبة ونشرها بنجاح! 🎮

🔗 **رابط اللعبة:** {deploy_result.get('url')}

🎯 اللعبة جاهزة للعب الآن!"""
                    attachments = [{"type": "game", "code": code, "id": asset["id"], "url": deploy_result.get('url')}]
                else:
                    ai_response = f"""✅ تم إنشاء اللعبة بنجاح! 🎮

🎯 **التقنية:** Babylon.js (3D)

قل "انشر اللعبة" لرفعها على رابط مباشر!

```html
{code[:2000]}...
```"""
                    attachments = [{"type": "game", "code": code, "id": asset["id"]}]
                
                msg_type = "game"
            except Exception as e:
                logger.error(f"Game error: {e}")
                ai_response = f"عذراً، حدث خطأ في إنشاء اللعبة: {str(e)[:100]}"
        
        # === WEBSITE GENERATION ===
        elif is_website:
            try:
                completion = self.openai_client.chat.completions.create(
                    model="gpt-5.2",
                    messages=[
                        {"role": "system", "content": """أنت مطور ويب محترف. أنشئ موقع HTML+CSS+JS كامل وعصري.

متطلبات:
- تصميم responsive جميل
- ألوان متناسقة وعصرية
- animations سلسة
- ملف HTML واحد كامل
- أرجع الكود فقط"""},
                        {"role": "user", "content": f"أنشئ موقع: {message}"}
                    ],
                    max_tokens=4096
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
                
                # Auto deploy if requested
                deploy_result = None
                if is_deploy and self.vercel_token:
                    deploy_result = await self.deploy_to_vercel(f"zitex-site-{asset['id'][:8]}", {"index.html": code})
                
                if deploy_result and deploy_result.get("success"):
                    ai_response = f"""✅ تم إنشاء الموقع ونشره بنجاح! 🌐

🔗 **رابط الموقع:** {deploy_result.get('url')}

الموقع جاهز للزيارة الآن!"""
                    attachments = [{"type": "website", "code": code, "id": asset["id"], "url": deploy_result.get('url')}]
                else:
                    ai_response = f"""✅ تم إنشاء الموقع بنجاح! 🌐

قل "انشر الموقع" لرفعه على رابط مباشر!

```html
{code[:2000]}...
```"""
                    attachments = [{"type": "website", "code": code, "id": asset["id"]}]
                
                msg_type = "website"
            except Exception as e:
                logger.error(f"Website error: {e}")
                ai_response = f"عذراً، حدث خطأ: {str(e)[:100]}"
        
        # === DEPLOY LAST ASSET ===
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
                        ai_response = f"""✅ تم النشر بنجاح! 🚀

🔗 **الرابط:** {deploy_result.get('url')}

المشروع متاح الآن للجميع!"""
                        attachments = [{"type": "deployment", "url": deploy_result.get('url')}]
                    else:
                        ai_response = f"عذراً، فشل النشر: {deploy_result.get('error', 'خطأ غير معروف')}"
                else:
                    ai_response = "لم أجد مشروع سابق للنشر. أنشئ موقع أو لعبة أولاً!"
            except Exception as e:
                logger.error(f"Deploy error: {e}")
                ai_response = f"عذراً، حدث خطأ في النشر: {str(e)[:100]}"
        
        # === APP GENERATION ===
        elif is_app:
            try:
                completion = self.openai_client.chat.completions.create(
                    model="gpt-5.2",
                    messages=[
                        {"role": "system", "content": """أنت مطور تطبيقات محترف. أنشئ كود React Native للتطبيق المطلوب.
- كود نظيف ومنظم
- تعليقات توضيحية
- قابل للتشغيل
- أرجع الكود مع تعليمات التثبيت"""},
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
                
                ai_response = f"✅ تم إنشاء كود التطبيق بنجاح! 📱\n\n{code[:3000]}"
                attachments = [{"type": "app", "code": code, "id": asset["id"]}]
                msg_type = "app"
            except Exception as e:
                logger.error(f"App error: {e}")
                ai_response = f"عذراً، حدث خطأ: {str(e)[:100]}"
        
        # === REGULAR CHAT (GPT-5.2) ===
        else:
            try:
                messages = [{"role": "system", "content": """أنت زيتكس، مساعد ذكي متعدد القدرات يعمل بـ GPT-5.2.

قدراتي:
🎨 توليد الصور (GPT Image 1) - قل: "أنشئ صورة..."
🎬 توليد فيديوهات سينمائية حتى 60 ثانية (Sora 2) - قل: "أنشئ فيديو..."
🌐 إنشاء المواقع مع نشر تلقائي - قل: "أنشئ موقع..."
🎮 إنشاء ألعاب 3D (Babylon.js) - قل: "أنشئ لعبة..."
📱 إنشاء التطبيقات - قل: "أنشئ تطبيق..."
📋 إنشاء خطة تصميمية - قل: "خطط لموقع/لعبة..."
🚀 نشر تلقائي على Vercel - قل: "انشر..."

أجب بالعربية دائماً وكن مفيداً ومبدعاً."""}]
                
                for msg in session.get("messages", [])[-10:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                messages.append({"role": "user", "content": message})
                
                ai_response = await self.chat_gpt5(messages)
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
            {
                "$push": {"messages": {"$each": [user_msg, assistant_msg]}},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        return {"session_id": session_id, "user_message": user_msg, "assistant_message": assistant_msg}
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        result = await self.db.chat_sessions.update_one(
            {"id": session_id, "user_id": user_id},
            {"$set": {"status": "archived"}}
        )
        return result.modified_count > 0
    
    async def get_session_assets(self, session_id: str, user_id: str) -> List[Dict]:
        return await self.db.generated_assets.find(
            {"session_id": session_id, "user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
    
    async def get_video_requests(self, user_id: str, session_id: str = None) -> List[Dict]:
        query = {"user_id": user_id}
        if session_id:
            query["session_id"] = session_id
        return await self.db.video_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
