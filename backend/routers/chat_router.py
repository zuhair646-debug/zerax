"""
Zitex Chat API Router
راوتر API للشات الذكي
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import jwt
import os

router = APIRouter(prefix="/chat", tags=["Chat"])
security = HTTPBearer()

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')


# Pydantic models for API
class CreateSessionRequest(BaseModel):
    session_type: str = "general"  # general, image, video, website
    title: Optional[str] = None


class SendMessageRequest(BaseModel):
    message: str
    settings: Dict[str, Any] = {}


class SessionResponse(BaseModel):
    id: str
    title: str
    session_type: str
    status: str
    created_at: str
    updated_at: str
    message_count: int = 0


# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=['HS256'])
        user_id = payload.get('user_id')
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {'user_id': user_id}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Global AI assistant instance (will be set from main server)
ai_assistant = None


def set_ai_assistant(assistant):
    """Set the AI assistant instance"""
    global ai_assistant
    ai_assistant = assistant


@router.post("/sessions")
async def create_session(
    request: CreateSessionRequest,
    current_user: dict = Depends(get_current_user)
):
    """إنشاء جلسة محادثة جديدة"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    session = await ai_assistant.create_session(
        user_id=current_user['user_id'],
        session_type=request.session_type,
        title=request.title
    )
    
    # Return full session with messages (including welcome message)
    return {
        "id": session['id'],
        "title": session['title'],
        "session_type": session['session_type'],
        "status": session['status'],
        "created_at": session['created_at'],
        "updated_at": session['updated_at'],
        "message_count": len(session.get('messages', [])),
        "messages": session.get('messages', [])
    }


@router.get("/sessions")
async def get_sessions(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """استرجاع جلسات المستخدم"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    sessions = await ai_assistant.get_user_sessions(
        user_id=current_user['user_id'],
        limit=limit
    )
    
    return [
        {
            "id": s['id'],
            "title": s['title'],
            "session_type": s['session_type'],
            "status": s['status'],
            "created_at": s['created_at'],
            "updated_at": s['updated_at'],
            "message_count": len(s.get('messages', [])),
            "last_message": s.get('messages', [{}])[-1].get('content', '')[:100] if s.get('messages') else None
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """استرجاع جلسة محددة مع رسائلها"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    session = await ai_assistant.get_session(
        session_id=session_id,
        user_id=current_user['user_id']
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """إرسال رسالة في جلسة"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        result = await ai_assistant.process_message(
            session_id=session_id,
            user_id=current_user['user_id'],
            message=request.message,
            settings=request.settings
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """حذف (أرشفة) جلسة"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    success = await ai_assistant.delete_session(
        session_id=session_id,
        user_id=current_user['user_id']
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session archived"}


@router.get("/sessions/{session_id}/assets")
async def get_session_assets(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """استرجاع أصول الجلسة (صور، فيديوهات، ملفات)"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    assets = await ai_assistant.get_session_assets(
        session_id=session_id,
        user_id=current_user['user_id']
    )
    
    return assets


@router.get("/voices")
async def get_available_voices(
    current_user: dict = Depends(get_current_user)
):
    """استرجاع الأصوات المتاحة"""
    # قائمة الأصوات المتاحة
    voices = [
        {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "gender": "female", "language": "en", "accent": "American"},
        {"voice_id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "gender": "female", "language": "en", "accent": "American"},
        {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "gender": "female", "language": "en", "accent": "American"},
        {"voice_id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "gender": "male", "language": "en", "accent": "American"},
        {"voice_id": "VR6AewLTigWG4xSOukaG", "name": "Arnold", "gender": "male", "language": "en", "accent": "American"},
        {"voice_id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "gender": "male", "language": "en", "accent": "American"},
        {"voice_id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam", "gender": "male", "language": "en", "accent": "American"},
        {"voice_id": "onwK4e9ZLuTAKqWW03F9", "name": "Daniel", "gender": "male", "language": "en", "accent": "British"},
        {"voice_id": "XB0fDUnXU5powFXDhCwa", "name": "Charlotte", "gender": "female", "language": "en", "accent": "British"},
    ]
    return {"voices": voices}



@router.get("/video-requests")
async def get_video_requests(
    session_id: str = None,
    current_user: dict = Depends(get_current_user)
):
    """استرجاع طلبات الفيديو"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    requests = await ai_assistant.get_video_requests(
        user_id=current_user['user_id'],
        session_id=session_id
    )
    return requests


@router.get("/video-requests/{request_id}")
async def get_video_request(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """استرجاع طلب فيديو محدد"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    request = await ai_assistant.db.video_requests.find_one(
        {"id": request_id, "user_id": current_user['user_id']},
        {"_id": 0}
    )
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    return request


# ============== Templates API ==============
class SaveTemplateRequest(BaseModel):
    session_id: str
    name: str
    description: str = ""
    category: str = "custom"


class UseTemplateRequest(BaseModel):
    template_id: str
    session_id: Optional[str] = None


@router.get("/templates")
async def get_templates(
    category: str = None,
    current_user: dict = Depends(get_current_user)
):
    """استرجاع القوالب المتاحة"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    templates = await ai_assistant.get_templates(
        user_id=current_user['user_id'],
        category=category,
        include_public=True
    )
    return {"templates": templates}


@router.post("/templates/save")
async def save_template(
    request: SaveTemplateRequest,
    current_user: dict = Depends(get_current_user)
):
    """حفظ المشروع كقالب"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        result = await ai_assistant.save_as_template(
            user_id=current_user['user_id'],
            session_id=request.session_id,
            name=request.name,
            description=request.description,
            category=request.category
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/templates/use")
async def use_template(
    request: UseTemplateRequest,
    current_user: dict = Depends(get_current_user)
):
    """استخدام قالب"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        result = await ai_assistant.use_template(
            user_id=current_user['user_id'],
            template_id=request.template_id,
            session_id=request.session_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates/my")
async def get_my_templates(
    current_user: dict = Depends(get_current_user)
):
    """استرجاع قوالبي فقط"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    templates = await ai_assistant.get_templates(
        user_id=current_user['user_id'],
        include_public=False
    )
    return {"templates": [t for t in templates if t.get("user_id") == current_user['user_id']]}


# ============== Deployment API ==============
class DeployRequest(BaseModel):
    session_id: str
    subdomain: str


@router.post("/deploy")
async def deploy_project(
    request: DeployRequest,
    current_user: dict = Depends(get_current_user)
):
    """نشر المشروع على نطاق فرعي"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        result = await ai_assistant.deploy_project(
            user_id=current_user['user_id'],
            session_id=request.session_id,
            subdomain=request.subdomain
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/deployments")
async def get_deployments(
    current_user: dict = Depends(get_current_user)
):
    """استرجاع المشاريع المنشورة"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    deployments = await ai_assistant.get_user_deployments(current_user['user_id'])
    return {"deployments": deployments}


@router.delete("/deployments/{deployment_id}")
async def delete_deployment(
    deployment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """حذف مشروع منشور"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    success = await ai_assistant.delete_deployment(current_user['user_id'], deployment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return {"message": "تم حذف المشروع"}


# ============== Serve Deployed Sites ==============
from fastapi.responses import HTMLResponse, Response
from services.ai_chat_service import get_from_storage, GAME_LIBRARIES

@router.get("/sites/{subdomain}")
async def serve_deployed_site(subdomain: str):
    """خدمة المواقع المنشورة"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="Service not available")
    
    deployment = await ai_assistant.get_deployment_by_subdomain(subdomain)
    if not deployment:
        raise HTTPException(status_code=404, detail="الموقع غير موجود")
    
    # Increment visit count
    await ai_assistant.db.deployments.update_one(
        {"subdomain": subdomain},
        {"$inc": {"visits": 1}}
    )
    
    # Get code from storage
    result = get_from_storage(deployment.get("storage_path", ""))
    if result:
        content, content_type = result
        return Response(content=content, media_type="text/html")
    
    # Fallback to DB stored code
    if deployment.get("code"):
        return HTMLResponse(content=deployment["code"])
    
    raise HTTPException(status_code=404, detail="محتوى الموقع غير موجود")


@router.get("/templates/preview/{template_id}")
async def get_template_preview(template_id: str):
    """صور مصغرة للقوالب"""
    # Preview colors based on template type
    colors = {
        "landing-dark": ("#1a1a2e", "#ffd700", "صفحة هبوط"),
        "ecommerce-gold": ("#0a0a12", "#ffd700", "متجر ذهبي"),
        "portfolio-minimal": ("#16213e", "#00d4ff", "معرض أعمال"),
        "dashboard-pro": ("#1a1a2e", "#00ff88", "لوحة تحكم"),
        "game-2d-platformer": ("#0a0a12", "#ff6b6b", "🎮 لعبة 2D"),
        "game-3d-racing": ("#1a1a2e", "#ffd700", "🏎️ سباق 3D")
    }
    
    bg, accent, title = colors.get(template_id, ("#1a1a2e", "#ffd700", template_id))
    
    preview_html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ display:flex; align-items:center; justify-content:center; min-height:100vh; background:{bg}; }}
.card {{ width:100%; height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center; }}
.icon {{ font-size:60px; margin-bottom:20px; }}
.title {{ color:{accent}; font-size:24px; font-family:Arial,sans-serif; font-weight:bold; text-align:center; }}
.badge {{ background:{accent}20; border:2px solid {accent}; padding:8px 16px; border-radius:20px; margin-top:15px; color:{accent}; font-size:14px; }}
</style></head>
<body><div class="card">
<div class="icon">{"🎮" if "game" in template_id else "🌐" if "landing" in template_id else "🛒" if "ecommerce" in template_id else "👤" if "portfolio" in template_id else "📊"}</div>
<div class="title">{title}</div>
<div class="badge">Zitex Template</div>
</div></body></html>'''
    return HTMLResponse(content=preview_html)


@router.get("/game-libraries")
async def get_game_libraries():
    """قائمة مكتبات الألعاب المتاحة"""
    return {"libraries": GAME_LIBRARIES}


# ============== TTS API ==============
class TTSRequest(BaseModel):
    text: str
    voice: str = "alloy"
    speed: float = 1.0

@router.post("/tts")
async def generate_tts(
    request: TTSRequest,
    current_user: dict = Depends(get_current_user)
):
    """توليد صوت من نص"""
    if not ai_assistant:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    audio_url = await ai_assistant.generate_tts(
        text=request.text,
        voice=request.voice,
        speed=request.speed
    )
    
    if not audio_url:
        raise HTTPException(status_code=500, detail="فشل توليد الصوت")
    
    return {"audio_url": audio_url}
