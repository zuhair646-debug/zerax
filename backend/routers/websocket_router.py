from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import jwt
import os
import json
import asyncio
import httpx
from typing import Dict, List

router = APIRouter(tags=["WebSocket"])

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8001')

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

manager = ConnectionManager()

@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str, token: str = None):
    user_id = None
    try:
        if token:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = payload.get('user_id')
    except:
        await websocket.close(code=4001)
        return
    
    if not user_id:
        await websocket.close(code=4001)
        return
    
    await manager.connect(websocket, user_id)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "تم الاتصال بنجاح!",
            "session_id": session_id
        })
        
        while True:
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                message = message_data.get('message', '')
                settings = message_data.get('settings', {})
            except:
                message = data
                settings = {}
            
            if message:
                # مرحلة 1: التحليل
                await websocket.send_json({
                    "type": "progress",
                    "step": 1,
                    "total_steps": 4,
                    "status": "analyzing",
                    "message": "جاري تحليل طلبك...",
                    "percent": 25
                })
                await asyncio.sleep(0.5)
                
                # مرحلة 2: المعالجة
                await websocket.send_json({
                    "type": "progress",
                    "step": 2,
                    "total_steps": 4,
                    "status": "processing",
                    "message": "جاري المعالجة...",
                    "percent": 50
                })
                
                # استدعاء API الحقيقي
                try:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        response = await client.post(
                            f"{BACKEND_URL}/api/chat/sessions/{session_id}/messages",
                            json={"message": message, "settings": settings},
                            headers={"Authorization": f"Bearer {token}"}
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            
                            # مرحلة 3: التوليد
                            await websocket.send_json({
                                "type": "progress",
                                "step": 3,
                                "total_steps": 4,
                                "status": "generating",
                                "message": "جاري التوليد...",
                                "percent": 75
                            })
                            await asyncio.sleep(0.3)
                            
                            # مرحلة 4: مكتمل
                            await websocket.send_json({
                                "type": "progress",
                                "step": 4,
                                "total_steps": 4,
                                "status": "complete",
                                "message": "تم بنجاح!",
                                "percent": 100
                            })
                            await asyncio.sleep(0.3)
                            
                            # إرسال النتيجة
                            await websocket.send_json({
                                "type": "message",
                                "data": result
                            })
                        else:
                            await websocket.send_json({
                                "type": "error",
                                "message": "فشل في معالجة الطلب"
                            })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"خطأ: {str(e)[:100]}"
                    })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
