"""
Zitex WebSocket Router - Real-time Chat
شات حي مع تحديثات التقدم
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import jwt
import os
import json
import asyncio
from typing import Dict, List
from datetime import datetime, timezone

router = APIRouter(tags=["WebSocket"])

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
    
    async def send_progress(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()

# Global AI assistant instance
ai_assistant = None

def set_ai_assistant(assistant):
    global ai_assistant
    ai_assistant = assistant


async def process_with_progress(websocket: WebSocket, user_id: str, session_id: str, message: str):
    """معالجة الرسالة مع إرسال تحديثات التقدم"""
    
    try:
        # Step 1: Analyzing
        await websocket.send_json({
            "type": "progress",
            "step": 1,
            "total_steps": 4,
            "status": "analyzing",
            "message": "🔍 جاري تحليل طلبك...",
            "percent": 10
        })
        await asyncio.sleep(0.5)
        
        # Detect request type
        msg_lower = message.lower()
        image_keywords = ['صورة', 'صور', 'ارسم', 'image']
        video_keywords = ['فيديو', 'فديو', 'مقطع', 'video']
        website_keywords = ['موقع', 'صفحة', 'website', 'html']
        app_keywords = ['تطبيق', 'برنامج', 'app']
        voice_keywords = ['صوت', 'اقرأ', 'تحدث', 'voice']
        
        is_image = any(kw in msg_lower for kw in image_keywords)
        is_video = any(kw in msg_lower for kw in video_keywords)
        is_website = any(kw in msg_lower for kw in website_keywords)
        is_app = any(kw in msg_lower for kw in app_keywords)
        is_voice = any(kw in msg_lower for kw in voice_keywords)
        
        # Step 2: Processing type
        if is_image:
            task_name = "الصورة"
            task_emoji = "🎨"
        elif is_video:
            task_name = "الفيديو"
            task_emoji = "🎬"
        elif is_website:
            task_name = "الموقع"
            task_emoji = "🌐"
        elif is_app:
            task_name = "التطبيق"
            task_emoji = "📱"
        elif is_voice:
            task_name = "الصوت"
            task_emoji = "🔊"
        else:
            task_name = "الرد"
            task_emoji = "💬"
        
        await websocket.send_json({
            "type": "progress",
            "step": 2,
            "total_steps": 4,
            "status": "processing",
            "message": f"{task_emoji} جاري إنشاء {task_name}...",
            "percent": 30
        })
        
        # Step 3: Generating
        await websocket.send_json({
            "type": "progress",
            "step": 3,
            "total_steps": 4,
            "status": "generating",
            "message": "⚡ جاري التوليد بالذكاء الاصطناعي...",
            "percent": 60
        })
        
        # Actually process the message
        if ai_assistant:
            result = await ai_assistant.process_message(
                session_id=session_id,
                user_id=user_id,
                message=message
            )
        else:
            result = {
                "assistant_message": {
                    "content": "عذراً، خدمة الذكاء الاصطناعي غير متاحة.",
                    "message_type": "text",
                    "attachments": []
                }
            }
        
        # Step 4: Complete
        await websocket.send_json({
            "type": "progress",
            "step": 4,
            "total_steps": 4,
            "status": "complete",
            "message": f"✅ تم إنشاء {task_name} بنجاح!",
            "percent": 100
        })
        
        await asyncio.sleep(0.3)
        
        # Send final result
        await websocket.send_json({
            "type": "message",
            "data": result
        })
        
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": f"حدث خطأ: {str(e)[:100]}"
        })


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str, token: str = None):
    """WebSocket endpoint للشات الحي"""
    
    # Verify token
    user_id = None
    try:
        if token:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = payload.get('user_id')
    except Exception:
        await websocket.close(code=4001)
        return
    
    if not user_id:
        await websocket.close(code=4001)
        return
    
    await manager.connect(websocket, user_id)
    
    try:
        # Send connection success
        await websocket.send_json({
            "type": "connected",
            "message": "تم الاتصال بنجاح! 🟢",
            "session_id": session_id
        })
        
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                message = message_data.get('message', '')
                
                if message:
                    # Process with progress updates
                    await process_with_progress(
                        websocket=websocket,
                        user_id=user_id,
                        session_id=session_id,
                        message=message
                    )
            except json.JSONDecodeError:
                # Plain text message
                if data.strip():
                    await process_with_progress(
                        websocket=websocket,
                        user_id=user_id,
                        session_id=session_id,
                        message=data
                    )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception:
        manager.disconnect(websocket, user_id)
