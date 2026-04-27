"""
Zitex AI Chat System
نظام المحادثة الذكية لتوليد المحتوى الإبداعي
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid


class ChatMessage(BaseModel):
    """رسالة في المحادثة"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # user, assistant, system
    content: str
    message_type: str = "text"  # text, image, video, audio, code, website
    attachments: List[Dict[str, Any]] = []  # URLs للصور والفيديوهات
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatSession(BaseModel):
    """جلسة محادثة"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str = "محادثة جديدة"
    session_type: str = "general"  # general, image, video, website
    messages: List[ChatMessage] = []
    project_data: Dict[str, Any] = {}  # بيانات المشروع (صور، فيديوهات، كود)
    status: str = "active"  # active, archived
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Project(BaseModel):
    """مشروع إبداعي"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: str
    title: str
    project_type: str  # image_collection, video_film, website
    assets: List[Dict[str, Any]] = []  # الأصول (صور، فيديوهات، ملفات)
    settings: Dict[str, Any] = {}
    status: str = "in_progress"  # in_progress, completed, exported
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GenerationRequest(BaseModel):
    """طلب توليد محتوى"""
    session_id: str
    message: str
    generation_type: Optional[str] = None  # image, video, audio, website, auto
    settings: Dict[str, Any] = {}


class VideoSettings(BaseModel):
    """إعدادات الفيديو"""
    duration: int = 4  # 4, 8, 12 seconds
    size: str = "1280x720"  # 1280x720, 1792x1024, 1024x1792, 1024x1024
    model: str = "sora-2"  # sora-2, sora-2-pro
    voice_id: Optional[str] = None
    voice_text: Optional[str] = None


class ImageSettings(BaseModel):
    """إعدادات الصورة"""
    style: str = "realistic"  # realistic, artistic, anime, etc.
    size: str = "1024x1024"
    quality: str = "high"


class WebsiteSettings(BaseModel):
    """إعدادات الموقع"""
    template_type: str = "modern"  # modern, minimal, business, portfolio
    color_scheme: str = "auto"
    include_responsive: bool = True
    framework: str = "react"  # react, html, nextjs
