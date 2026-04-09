from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import jwt
import os
import json
import asyncio
from typing import Dict, List

router = APIRouter(tags=["WebSocket"])

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')

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
            except:
                message = data
            
            if message:
                await websocket.send_json({
                    "type": "progress",
                    "step": 1,
                    "total_steps": 4,
                    "status": "analyzing",
                    "message": "جاري تحليل طلبك...",
                    "percent": 25
                })
                await asyncio.sleep(1)
                
                await websocket.send_json({
                    "type": "progress",
                    "step": 2,
                    "total_steps": 4,
                    "status": "processing",
                    "message": "جاري المعالجة...",
                    "percent": 50
                })
                await asyncio.sleep(1)
                
                await websocket.send_json({
                    "type": "progress",
                    "step": 3,
                    "total_steps": 4,
                    "status": "generating",
                    "message": "جاري التوليد...",
                    "percent": 75
                })
                await asyncio.sleep(1)
                
                await websocket.send_json({
                    "type": "progress",
                    "step": 4,
                    "total_steps": 4,
                    "status": "complete",
                    "message": "تم بنجاح!",
                    "percent": 100
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

**أخبرني لما تخلص وأعطيك الخطوة 2**
