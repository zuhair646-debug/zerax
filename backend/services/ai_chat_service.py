"""
Zitex AI Chat Service - Simplified for independent hosting
"""
import os
import uuid
import base64
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

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs.types import VoiceSettings
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    ElevenLabs = None
    VoiceSettings = None


class AIAssistant:
    def __init__(self, db: AsyncIOMotorDatabase, api_key: str = None, elevenlabs_key: str = None, openai_key: str = None):
        self.db = db
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.elevenlabs_key = elevenlabs_key
        
        self.eleven_client = None
        if ELEVENLABS_AVAILABLE and elevenlabs_key:
            try:
                self.eleven_client = ElevenLabs(api_key=elevenlabs_key)
            except:
                pass
        
        self.openai_client = None
        if OPENAI_AVAILABLE and self.api_key:
            try:
                self.openai_client = openai.OpenAI(api_key=self.api_key)
            except:
                pass
    
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
        
        ai_response = "مرحباً! كيف يمكنني مساعدتك؟"
        
        if self.openai_client:
            try:
                messages = [{"role": "system", "content": "أنت مساعد ذكي اسمك زيتكس. أجب بالعربية."}]
                for msg in session.get("messages", [])[-10:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                messages.append({"role": "user", "content": message})
                
                completion = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                ai_response = completion.choices[0].message.content
            except Exception as e:
                logger.error(f"OpenAI error: {e}")
                ai_response = f"عذراً، حدث خطأ. يرجى المحاولة لاحقاً."
        
        assistant_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": ai_response,
            "message_type": "text",
            "attachments": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.chat_sessions.update_one(
            {"id": session_id},
            {
                "$push": {"messages": {"$each": [user_msg, assistant_msg]}},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        if len(session.get("messages", [])) == 0:
            title = message[:50] + "..." if len(message) > 50 else message
            await self.db.chat_sessions.update_one({"id": session_id}, {"$set": {"title": title}})
        
        return {"session_id": session_id, "user_message": user_msg, "assistant_message": assistant_msg}
    
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
