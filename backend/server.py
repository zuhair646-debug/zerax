from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import base64
import httpx
import io

# AI Features disabled for independent hosting
# To enable: install openai, elevenlabs, Pillow and configure API keys
AI_FEATURES_ENABLED = False

# Optional imports for AI features
try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs.types import VoiceSettings
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    ElevenLabs = None
    VoiceSettings = None

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageDraw = None
    ImageFont = None

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="Zitex API", description="AI-Powered Creative Platform")
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Server is running"}

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Server is running"}
api_router = APIRouter(prefix="/api")

security = HTTPBearer()
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OWNER_WHATSAPP = os.environ.get('OWNER_WHATSAPP', '966507374438')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID')
PAYPAL_SECRET = os.environ.get('PAYPAL_SECRET')

# Initialize PayPal
try:
    import paypalrestsdk
    PAYPAL_AVAILABLE = True
    if PAYPAL_CLIENT_ID and PAYPAL_SECRET:
        paypalrestsdk.configure({
            "mode": "live",  # LIVE MODE - Production
            "client_id": PAYPAL_CLIENT_ID,
            "client_secret": PAYPAL_SECRET
        })
except ImportError:
    PAYPAL_AVAILABLE = False
    paypalrestsdk = None

# Initialize OpenAI client (for TTS/STT when enabled)
openai_client = None
if OPENAI_AVAILABLE and OPENAI_API_KEY:
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize ElevenLabs client
eleven_client = None
if ELEVENLABS_AVAILABLE and ELEVENLABS_API_KEY:
    eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# ============== MODELS ==============

# Role levels: owner (100) > super_admin (80) > admin (50) > client (10)
ROLE_LEVELS = {
    "owner": 100,
    "super_admin": 80,
    "admin": 50,
    "client": 10
}

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    country: str = "SA"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    role: str = "client"
    country: str = "SA"
    credits: float = 0
    free_images: int = 3
    free_videos: int = 3
    free_website_trial: bool = True
    subscription_type: Optional[str] = None
    subscription_expires: Optional[str] = None
    is_owner: bool = False
    is_active: bool = True
    # نظام الدعوات والنقاط
    referral_code: str = Field(default_factory=lambda: str(uuid.uuid4())[:8].upper())
    referred_by: Optional[str] = None
    total_referrals: int = 0
    bonus_points: int = 0
    first_purchase_bonus_claimed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ActivityLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    user_name: str
    user_email: str
    action: str  # image_generated, video_generated, website_requested, payment_created, download, etc.
    action_type: str  # create, download, edit, delete
    details: Optional[str] = None
    metadata: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VoiceInfo(BaseModel):
    voice_id: str
    name: str
    category: str
    gender: str
    language: str
    accent: str

# TTS Models
class TTSRequest(BaseModel):
    text: str
    provider: Literal["openai", "elevenlabs"] = "openai"
    voice: str = "alloy"
    speed: float = 1.0

class TTSVoice(BaseModel):
    id: str
    name: str
    provider: str
    language: str = "ar"
    preview_url: Optional[str] = None

# نظام الدعوات والنقاط
class ReferralInfo(BaseModel):
    referral_code: str
    total_referrals: int
    bonus_points: int
    referral_link: str

class ApplyReferralRequest(BaseModel):
    referral_code: str

# ============== PAYMENT MODELS ==============

class PaymentOrder(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    package_id: str
    package_type: str  # credits, subscription
    amount: float
    currency: str = "USD"
    status: str = "pending"  # pending, completed, failed, refunded
    payment_method: str = "paypal"
    paypal_order_id: Optional[str] = None
    credits_added: int = 0
    metadata: Optional[dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

class CreateOrderRequest(BaseModel):
    package_id: str
    package_type: str = "credits"
    amount: float
    currency: str = "USD"

class CaptureOrderRequest(BaseModel):
    order_id: str
    package_id: str
    package_type: str = "credits"

# إعدادات النقاط
POINTS_CONFIG = {
    "signup_bonus": 20,                # نقاط التسجيل المجاني
    "first_purchase_bonus": 50,        # نقاط أول شحن
    "referral_bonus_inviter": 30,      # نقاط للداعي
    "referral_bonus_invited": 20,      # نقاط للمدعو
    "points_per_image": 5,             # نقاط لكل صورة
    "points_per_video_4s": 10,         # نقاط لفيديو 4 ثواني
    "points_per_video_8s": 18,         # نقاط لفيديو 8 ثواني
    "points_per_video_12s": 25,        # نقاط لفيديو 12 ثانية
    "points_per_video_50s": 80,        # نقاط لفيديو 50 ثانية
    "points_per_video_60s": 100,       # نقاط لفيديو دقيقة
    "points_per_website_simple": 50,   # نقاط لموقع بسيط
    "points_per_tts_1000": 2,          # نقاط لكل 1000 حرف TTS
}

class ImageEditRequest(BaseModel):
    image_base64: str
    text: Optional[str] = None
    text_position: Optional[str] = "bottom"  # top, center, bottom
    text_color: Optional[str] = "#FFFFFF"
    font_size: Optional[int] = 40

class ImageGeneration(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    prompt: str
    image_url: Optional[str] = None
    edited_image_url: Optional[str] = None
    status: str = "pending"
    is_free: bool = False
    is_edit: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VideoGeneration(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    prompt: str
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    voice_id: Optional[str] = None
    status: str = "pending"
    is_free: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class WebsiteRequestCreate(BaseModel):
    title: str
    description: str
    requirements: str
    business_type: Optional[str] = None
    target_audience: Optional[str] = None
    preferred_colors: Optional[str] = None
    is_trial: bool = False

class WebsiteRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    description: str
    requirements: str
    business_type: Optional[str] = None
    target_audience: Optional[str] = None
    preferred_colors: Optional[str] = None
    ai_suggestions: Optional[str] = None
    status: str = "pending"
    credits_used: float = 0
    is_trial: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PaymentCreate(BaseModel):
    payment_type: str
    amount: float
    proof_base64: Optional[str] = None

class Payment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    payment_type: str
    amount: float
    currency: str
    proof_image_url: Optional[str] = None
    status: str = "pending"
    admin_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Website(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    user_id: str
    url: str
    preview_image: Optional[str] = None
    content: Optional[str] = None
    status: str = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SiteSettings(BaseModel):
    bank_name: Optional[str] = None
    bank_iban: Optional[str] = None
    bank_account_name: Optional[str] = None
    paypal_email: Optional[str] = None
    owner_whatsapp: Optional[str] = None

class AdminStats(BaseModel):
    total_users: int
    total_requests: int
    pending_requests: int
    completed_requests: int
    pending_payments: int
    approved_payments: int
    total_websites: int
    total_images_generated: int
    total_videos_generated: int
    total_activities: int

# ============== HELPERS ==============

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, role: str) -> str:
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=['HS256'])
        user_id = payload.get('user_id')
        role = payload.get('role')
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {'user_id': user_id, 'role': role}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_role(min_role: str, current_user: dict):
    """Check if user has minimum required role level"""
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_role = user_doc.get('role', 'client')
    user_level = ROLE_LEVELS.get(user_role, 0)
    required_level = ROLE_LEVELS.get(min_role, 0)
    
    if user_level < required_level:
        raise HTTPException(status_code=403, detail=f"Requires {min_role} role or higher")
    
    return user_doc

async def require_admin(current_user: dict = Depends(get_current_user)):
    return await require_role("admin", current_user)

async def require_super_admin(current_user: dict = Depends(get_current_user)):
    return await require_role("super_admin", current_user)

async def require_owner(current_user: dict = Depends(get_current_user)):
    return await require_role("owner", current_user)

async def check_user_subscription(user_id: str, sub_type: str) -> bool:
    user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user_doc:
        return False
    if user_doc.get('is_owner'):
        return True
    if user_doc.get('subscription_type') == sub_type:
        expires = user_doc.get('subscription_expires')
        if expires and datetime.fromisoformat(expires) > datetime.now(timezone.utc):
            return True
    return False

async def log_activity(user_id: str, action: str, action_type: str, details: str = None, metadata: dict = None):
    """Log user activity"""
    user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user_doc:
        return
    
    log = ActivityLog(
        user_id=user_id,
        user_name=user_doc.get('name', 'Unknown'),
        user_email=user_doc.get('email', ''),
        action=action,
        action_type=action_type,
        details=details,
        metadata=metadata
    )
    
    doc = log.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.activity_logs.insert_one(doc)

async def send_whatsapp_notification(message: str):
    """Send WhatsApp notification to owner"""
    try:
        phone = OWNER_WHATSAPP
        settings = await db.settings.find_one({"type": "payment"}, {"_id": 0})
        if settings and settings.get('owner_whatsapp'):
            phone = settings.get('owner_whatsapp')
        
        import urllib.parse
        encoded_msg = urllib.parse.quote(message)
        url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_msg}&apikey=123456"
        
        async with httpx.AsyncClient() as client:
            try:
                await client.get(url, timeout=10)
            except:
                pass
        
        logging.info(f"WhatsApp notification sent to {phone}")
        return True
    except Exception as e:
        logging.error(f"WhatsApp notification failed: {str(e)}")
        return False

# ============== AUTH ROUTES ==============

class UserRegisterWithReferral(BaseModel):
    email: EmailStr
    password: str
    name: str
    country: str = "SA"
    referral_code: Optional[str] = None

@api_router.post("/auth/register")
async def register(user_data: UserRegisterWithReferral):
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مسجل مسبقاً")
    
    # نقاط التسجيل المجانية
    signup_bonus = POINTS_CONFIG.get("signup_bonus", 20)
    
    user = User(
        email=user_data.email,
        name=user_data.name,
        role="client",
        country=user_data.country,
        credits=signup_bonus,  # نقاط مجانية عند التسجيل
        bonus_points=signup_bonus,
        free_images=3,
        free_videos=2,
        free_website_trial=True
    )
    
    doc = user.model_dump()
    doc['password'] = hash_password(user_data.password)
    doc['created_at'] = doc['created_at'].isoformat()
    doc['signup_bonus_claimed'] = True  # تم المطالبة تلقائياً
    
    # التحقق من كود الدعوة
    referral_bonus_msg = ""
    if user_data.referral_code:
        inviter = await db.users.find_one({"referral_code": user_data.referral_code.upper()}, {"_id": 0})
        if inviter:
            doc['referred_by'] = user_data.referral_code.upper()
            # إضافة نقاط المدعو
            invited_bonus = POINTS_CONFIG.get("referral_bonus_invited", 20)
            doc['credits'] += invited_bonus
            doc['bonus_points'] += invited_bonus
            referral_bonus_msg = f" + {invited_bonus} نقطة من الدعوة"
            
            # إضافة نقاط الداعي
            inviter_bonus = POINTS_CONFIG.get("referral_bonus_inviter", 30)
            await db.users.update_one(
                {"id": inviter['id']},
                {"$inc": {"credits": inviter_bonus, "bonus_points": inviter_bonus, "total_referrals": 1}}
            )
    
    await db.users.insert_one(doc)
    await log_activity(user.id, "user_registered", "create", f"New user registered: {user.email} with {doc['credits']} bonus points")
    
    token = create_token(user.id, user.role)
    
    # إزالة الحقول الحساسة من الاستجابة
    user_response = user.model_dump()
    user_response['credits'] = doc['credits']
    user_response['bonus_points'] = doc['bonus_points']
    
    return {
        "token": token, 
        "user": user_response,
        "welcome_message": f"🎉 مرحباً {user.name}! حصلت على {doc['credits']} نقطة مجانية{referral_bonus_msg}"
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user_doc or not verify_password(credentials.password, user_doc['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user_doc.get('is_active', True):
        raise HTTPException(status_code=403, detail="Account is deactivated")
    
    for field in ['free_images', 'free_videos', 'free_website_trial']:
        if field not in user_doc:
            user_doc[field] = 0 if field != 'free_website_trial' else False
    
    user = User(**{k: v for k, v in user_doc.items() if k != 'password'})
    await log_activity(user.id, "user_login", "create", "User logged in")
    
    token = create_token(user.id, user.role)
    return {"token": token, "user": user}

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0, "password": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    for field in ['free_images', 'free_videos', 'free_website_trial']:
        if field not in user_doc:
            user_doc[field] = 0 if field != 'free_website_trial' else False
    
    return user_doc

# ============== VOICES ==============

# Pre-defined voices for Arabic and English
AVAILABLE_VOICES = [
    {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "category": "premade", "gender": "female", "language": "en", "accent": "American"},
    {"voice_id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "category": "premade", "gender": "female", "language": "en", "accent": "American"},
    {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "category": "premade", "gender": "female", "language": "en", "accent": "American"},
    {"voice_id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "category": "premade", "gender": "male", "language": "en", "accent": "American"},
    {"voice_id": "VR6AewLTigWG4xSOukaG", "name": "Arnold", "category": "premade", "gender": "male", "language": "en", "accent": "American"},
    {"voice_id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "category": "premade", "gender": "male", "language": "en", "accent": "American"},
    {"voice_id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam", "category": "premade", "gender": "male", "language": "en", "accent": "American"},
    {"voice_id": "onwK4e9ZLuTAKqWW03F9", "name": "Daniel", "category": "premade", "gender": "male", "language": "en", "accent": "British"},
    {"voice_id": "XB0fDUnXU5powFXDhCwa", "name": "Charlotte", "category": "premade", "gender": "female", "language": "en", "accent": "British"},
]

@api_router.get("/voices")
async def get_voices(current_user: dict = Depends(get_current_user)):
    """Get available voices for TTS"""
    try:
        if eleven_client:
            voices_response = eleven_client.voices.get_all()
            voices = []
            for voice in voices_response.voices:
                voices.append({
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "category": voice.category or "premade",
                    "gender": voice.labels.get("gender", "unknown") if voice.labels else "unknown",
                    "language": voice.labels.get("language", "en") if voice.labels else "en",
                    "accent": voice.labels.get("accent", "unknown") if voice.labels else "unknown",
                    "preview_url": voice.preview_url
                })
            return {"voices": voices}
    except Exception as e:
        logging.error(f"Error fetching voices: {str(e)}")
    
    return {"voices": AVAILABLE_VOICES}

@api_router.post("/tts/generate")
async def generate_tts(request: TTSRequest, current_user: dict = Depends(get_current_user)):
    """Generate text-to-speech audio - supports OpenAI and ElevenLabs"""
    if not AI_FEATURES_ENABLED:
        raise HTTPException(status_code=503, detail="ميزة تحويل النص لصوت معطلة مؤقتاً. ستتوفر قريباً!")
    
    try:
        audio_data = None
        
        if request.provider == "openai":
            if not openai_client:
                raise HTTPException(status_code=400, detail="OpenAI TTS غير متاح - يرجى إضافة OPENAI_API_KEY")
            
            # Generate speech with OpenAI
            response = openai_client.audio.speech.create(
                model="tts-1",
                voice=request.voice,
                input=request.text,
                speed=request.speed
            )
            audio_bytes = response.content
            audio_base64 = base64.b64encode(audio_bytes).decode()
            audio_data = f"data:audio/mp3;base64,{audio_base64}"
            
        elif request.provider == "elevenlabs":
            if not eleven_client:
                raise HTTPException(status_code=400, detail="ElevenLabs غير متاح")
            
            voice_settings = VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.5,
                use_speaker_boost=True
            )
            
            audio_generator = eleven_client.text_to_speech.convert(
                text=request.text,
                voice_id=request.voice,
                model_id="eleven_multilingual_v2",
                voice_settings=voice_settings
            )
            
            audio_bytes = b""
            for chunk in audio_generator:
                audio_bytes += chunk
            
            audio_b64 = base64.b64encode(audio_bytes).decode()
            audio_data = f"data:audio/mpeg;base64,{audio_b64}"
        
        else:
            raise HTTPException(status_code=400, detail="مزود غير معروف")
        
        await log_activity(
            current_user['user_id'],
            "tts_generated",
            "create",
            f"Generated speech ({request.provider}): {request.text[:50]}...",
            {"provider": request.provider, "voice": request.voice, "chars": len(request.text)}
        )
        
        return {
            "audio_url": audio_data,
            "provider": request.provider,
            "voice": request.voice,
            "chars": len(request.text)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في توليد الصوت: {str(e)}")

# ============== SPEECH TO TEXT (Voice Input) ==============

@api_router.post("/stt/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form(default="ar"),
    current_user: dict = Depends(get_current_user)
):
    """Convert speech to text using OpenAI Whisper"""
    if not AI_FEATURES_ENABLED:
        raise HTTPException(status_code=503, detail="ميزة تحويل الصوت للنص معطلة مؤقتاً. ستتوفر قريباً!")
    
    if not openai_client:
        raise HTTPException(status_code=400, detail="خدمة التحويل الصوتي غير متاحة - يرجى إضافة OPENAI_API_KEY")
    
    # Check file size (max 25MB)
    content = await audio.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="حجم الملف أكبر من 25MB")
    
    # Check file type
    allowed_types = ['audio/webm', 'audio/mp3', 'audio/mpeg', 'audio/wav', 'audio/mp4', 'audio/m4a', 'audio/ogg']
    if audio.content_type and not any(t in audio.content_type for t in ['audio', 'webm', 'ogg']):
        raise HTTPException(status_code=400, detail=f"نوع الملف غير مدعوم: {audio.content_type}")
    
    try:
        # Create a file-like object
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Transcribe using OpenAI Whisper
        with open(tmp_file_path, 'rb') as audio_file:
            response = openai_client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                language=language,
                response_format="json"
            )
        
        # Clean up temp file
        import os as os_module
        os_module.unlink(tmp_file_path)
        
        # Log activity
        await log_activity(
            current_user['user_id'],
            "stt_transcribed",
            "create",
            f"Transcribed audio: {response.text[:50]}...",
            {"language": language, "chars": len(response.text)}
        )
        
        return {
            "text": response.text,
            "language": language
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في تحويل الصوت: {str(e)}")

# ============== IMAGE GENERATION & EDITING ==============

@api_router.post("/generate/image")
async def generate_image(prompt: str, current_user: dict = Depends(get_current_user)):
    """Generate image - TEMPORARILY DISABLED for independent hosting"""
    if not AI_FEATURES_ENABLED:
        raise HTTPException(status_code=503, detail="ميزة توليد الصور معطلة مؤقتاً. ستتوفر قريباً بعد إعداد OpenAI API!")
    
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0})
    
    is_owner = user_doc.get('is_owner', False)
    has_subscription = await check_user_subscription(current_user['user_id'], "images")
    free_images = user_doc.get('free_images', 0)
    
    is_free_use = False
    
    if is_owner:
        pass
    elif has_subscription:
        pass
    elif free_images > 0:
        is_free_use = True
        await db.users.update_one(
            {"id": current_user['user_id']},
            {"$inc": {"free_images": -1}}
        )
    else:
        raise HTTPException(status_code=403, detail="لا يوجد لديك رصيد مجاني أو اشتراك")
    
    try:
        # Use OpenAI DALL-E for image generation
        if not openai_client:
            raise HTTPException(status_code=400, detail="خدمة توليد الصور غير متاحة - يرجى إضافة OPENAI_API_KEY")
        
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        image_url = response.data[0].url
        
        gen_record = ImageGeneration(
            user_id=current_user['user_id'],
            prompt=prompt,
            image_url=image_url,
            status="completed" if image_url else "failed",
            is_free=is_free_use
        )
        
        doc = gen_record.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.image_generations.insert_one(doc)
        
        await log_activity(
            current_user['user_id'],
            "image_generated",
            "create",
            f"Generated image: {prompt[:50]}...",
            {"is_free": is_free_use, "prompt": prompt}
        )
        
        updated_user = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0, "password": 0})
        
        return {
            "id": gen_record.id, 
            "image_url": image_url, 
            "text": "تم توليد الصورة بنجاح",
            "free_images_remaining": updated_user.get('free_images', 0),
            "was_free": is_free_use
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل توليد الصورة: {str(e)}")

@api_router.post("/images/edit")
async def edit_image(request: ImageEditRequest, current_user: dict = Depends(get_current_user)):
    """Add text to an image"""
    if not PIL_AVAILABLE:
        raise HTTPException(status_code=503, detail="ميزة تحرير الصور معطلة مؤقتاً - Pillow غير مثبتة")
    
    try:
        # Decode base64 image
        if request.image_base64.startswith('data:'):
            header, data = request.image_base64.split(',', 1)
        else:
            data = request.image_base64
        
        image_bytes = base64.b64decode(data)
        image = Image.open(io.BytesIO(image_bytes))
        
        if request.text:
            draw = ImageDraw.Draw(image)
            
            # Try to use a font, fallback to default
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", request.font_size)
            except:
                font = ImageFont.load_default()
            
            # Calculate text position
            text_bbox = draw.textbbox((0, 0), request.text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            img_width, img_height = image.size
            x = (img_width - text_width) // 2
            
            if request.text_position == "top":
                y = 20
            elif request.text_position == "center":
                y = (img_height - text_height) // 2
            else:  # bottom
                y = img_height - text_height - 20
            
            # Add text shadow for better visibility
            shadow_color = "#000000"
            draw.text((x+2, y+2), request.text, font=font, fill=shadow_color)
            draw.text((x, y), request.text, font=font, fill=request.text_color)
        
        # Convert back to base64
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        edited_b64 = base64.b64encode(buffer.getvalue()).decode()
        edited_url = f"data:image/png;base64,{edited_b64}"
        
        # Save to database
        edit_record = ImageGeneration(
            user_id=current_user['user_id'],
            prompt=f"Edited image with text: {request.text}",
            image_url=request.image_base64,
            edited_image_url=edited_url,
            status="completed",
            is_edit=True
        )
        
        doc = edit_record.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.image_generations.insert_one(doc)
        
        await log_activity(
            current_user['user_id'],
            "image_edited",
            "edit",
            f"Added text to image: {request.text[:30]}...",
            {"text": request.text, "position": request.text_position}
        )
        
        return {"id": edit_record.id, "edited_image_url": edited_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error editing image: {str(e)}")

@api_router.post("/images/upload-edit")
async def upload_and_edit_image(
    file: UploadFile = File(...),
    text: str = Form(None),
    text_position: str = Form("bottom"),
    text_color: str = Form("#FFFFFF"),
    font_size: int = Form(40),
    current_user: dict = Depends(get_current_user)
):
    """Upload an image and optionally add text"""
    try:
        contents = await file.read()
        image_b64 = base64.b64encode(contents).decode()
        image_url = f"data:{file.content_type};base64,{image_b64}"
        
        if text:
            request = ImageEditRequest(
                image_base64=image_url,
                text=text,
                text_position=text_position,
                text_color=text_color,
                font_size=font_size
            )
            return await edit_image(request, current_user)
        
        await log_activity(
            current_user['user_id'],
            "image_uploaded",
            "create",
            f"Uploaded image: {file.filename}"
        )
        
        return {"image_url": image_url, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")

@api_router.get("/generate/images/history")
async def get_image_history(current_user: dict = Depends(get_current_user)):
    images = await db.image_generations.find(
        {"user_id": current_user['user_id']},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return images

@api_router.post("/download/log")
async def log_download(item_type: str, item_id: str, current_user: dict = Depends(get_current_user)):
    """Log when user downloads an image or video"""
    await log_activity(
        current_user['user_id'],
        f"{item_type}_downloaded",
        "download",
        f"Downloaded {item_type}: {item_id}",
        {"item_type": item_type, "item_id": item_id}
    )
    return {"message": "Download logged"}

# ============== VIDEO GENERATION ==============

@api_router.post("/generate/video")
async def generate_video(
    prompt: str, 
    voice_id: Optional[str] = None,
    voice_text: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0})
    
    is_owner = user_doc.get('is_owner', False)
    has_subscription = await check_user_subscription(current_user['user_id'], "videos")
    free_videos = user_doc.get('free_videos', 0)
    
    is_free_use = False
    
    if is_owner:
        pass
    elif has_subscription:
        pass
    elif free_videos > 0:
        is_free_use = True
        await db.users.update_one(
            {"id": current_user['user_id']},
            {"$inc": {"free_videos": -1}}
        )
    else:
        raise HTTPException(status_code=403, detail="لا يوجد لديك رصيد مجاني أو اشتراك")
    
    audio_url = None
    if voice_id and voice_text and eleven_client:
        try:
            voice_settings = VoiceSettings(stability=0.5, similarity_boost=0.75)
            audio_generator = eleven_client.text_to_speech.convert(
                text=voice_text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                voice_settings=voice_settings
            )
            
            audio_data = b""
            for chunk in audio_generator:
                audio_data += chunk
            
            audio_b64 = base64.b64encode(audio_data).decode()
            audio_url = f"data:audio/mpeg;base64,{audio_b64}"
        except Exception as e:
            logging.error(f"Error generating audio for video: {str(e)}")
    
    gen_record = VideoGeneration(
        user_id=current_user['user_id'],
        prompt=prompt,
        audio_url=audio_url,
        voice_id=voice_id,
        status="processing",
        is_free=is_free_use
    )
    
    doc = gen_record.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.video_generations.insert_one(doc)
    
    await log_activity(
        current_user['user_id'],
        "video_generated",
        "create",
        f"Generated video: {prompt[:50]}...",
        {"is_free": is_free_use, "has_voice": bool(voice_id), "prompt": prompt}
    )
    
    updated_user = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0, "password": 0})
    
    return {
        "id": gen_record.id, 
        "status": "processing", 
        "message": "جاري توليد الفيديو",
        "audio_url": audio_url,
        "free_videos_remaining": updated_user.get('free_videos', 0),
        "was_free": is_free_use
    }

@api_router.post("/videos/upload")
async def upload_video(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a video for editing"""
    try:
        contents = await file.read()
        video_b64 = base64.b64encode(contents).decode()
        video_url = f"data:{file.content_type};base64,{video_b64}"
        
        await log_activity(
            current_user['user_id'],
            "video_uploaded",
            "create",
            f"Uploaded video: {file.filename}"
        )
        
        return {"video_url": video_url, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading video: {str(e)}")

@api_router.get("/generate/videos/history")
async def get_video_history(current_user: dict = Depends(get_current_user)):
    videos = await db.video_generations.find(
        {"user_id": current_user['user_id']},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return videos

# ============== WEBSITE REQUESTS ==============

@api_router.post("/requests/create", response_model=WebsiteRequest)
async def create_request(request_data: WebsiteRequestCreate, current_user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0})
    is_owner = user_doc.get('is_owner', False)
    credits = user_doc.get('credits', 0)
    has_free_trial = user_doc.get('free_website_trial', False)
    
    is_trial = request_data.is_trial
    required_credits = 50
    
    if is_trial:
        if not has_free_trial and not is_owner:
            raise HTTPException(status_code=403, detail="لقد استخدمت تجربتك المجانية")
        
        if not is_owner:
            await db.users.update_one(
                {"id": current_user['user_id']},
                {"$set": {"free_website_trial": False}}
            )
    else:
        if not is_owner and credits < required_credits:
            raise HTTPException(status_code=403, detail=f"رصيدك غير كافٍ. تحتاج {required_credits} نقطة")
        
        if not is_owner:
            await db.users.update_one(
                {"id": current_user['user_id']},
                {"$inc": {"credits": -required_credits}}
            )
    
    request_obj = WebsiteRequest(
        user_id=current_user['user_id'],
        credits_used=0 if (is_owner or is_trial) else required_credits,
        is_trial=is_trial,
        **{k: v for k, v in request_data.model_dump().items() if k != 'is_trial'}
    )
    
    doc = request_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.website_requests.insert_one(doc)
    
    await log_activity(
        current_user['user_id'],
        "website_requested",
        "create",
        f"Website request: {request_data.title}",
        {"is_trial": is_trial, "credits_used": request_obj.credits_used}
    )
    
    return request_obj

@api_router.post("/requests/{request_id}/generate-suggestions")
async def generate_suggestions(request_id: str, current_user: dict = Depends(get_current_user)):
    """Generate AI suggestions for website - TEMPORARILY DISABLED"""
    if not AI_FEATURES_ENABLED:
        raise HTTPException(status_code=503, detail="ميزة اقتراحات الذكاء الاصطناعي معطلة مؤقتاً. ستتوفر قريباً!")
    
    request_doc = await db.website_requests.find_one({"id": request_id}, {"_id": 0})
    if not request_doc:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request_doc['user_id'] != current_user['user_id'] and current_user['role'] not in ['admin', 'super_admin', 'owner']:
        raise HTTPException(status_code=403, detail="Access denied")
    
    is_trial = request_doc.get('is_trial', False)
    
    try:
        if not openai_client:
            raise HTTPException(status_code=400, detail="خدمة الذكاء الاصطناعي غير متاحة - يرجى إضافة OPENAI_API_KEY")
        
        system_msg = "أنت مصمم مواقع محترف. قم بتقديم اقتراحات تفصيلية لتصميم الموقع بناءً على متطلبات العميل. أجب بالعربية."
        
        if is_trial:
            system_msg += " هذه تجربة مجانية، قدم ملخصاً موجزاً فقط."
        
        prompt = f"""العميل يريد موقع بالمواصفات التالية:
العنوان: {request_doc['title']}
الوصف: {request_doc['description']}
المتطلبات: {request_doc['requirements']}
نوع العمل: {request_doc.get('business_type', 'غير محدد')}
الجمهور المستهدف: {request_doc.get('target_audience', 'غير محدد')}
الألوان المفضلة: {request_doc.get('preferred_colors', 'غير محدد')}

{"تجربة مجانية - ملخص موجز فقط." if is_trial else "قدم اقتراحات احترافية كاملة."}"""
        
        completion = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ]
        )
        response = completion.choices[0].message.content
        
        if is_trial:
            response += "\n\n---\n🔒 **معاينة محدودة**\nللحصول على التصميم الكامل، يرجى شراء نقاط."
        
        await db.website_requests.update_one(
            {"id": request_id},
            {"$set": {"ai_suggestions": response}}
        )
        
        return {"suggestions": response, "is_trial": is_trial}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

@api_router.get("/requests")
async def get_requests(current_user: dict = Depends(get_current_user)):
    if current_user['role'] in ['admin', 'super_admin', 'owner']:
        requests = await db.website_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    else:
        requests = await db.website_requests.find({"user_id": current_user['user_id']}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return requests

@api_router.get("/requests/{request_id}")
async def get_request(request_id: str, current_user: dict = Depends(get_current_user)):
    request_doc = await db.website_requests.find_one({"id": request_id}, {"_id": 0})
    if not request_doc:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request_doc['user_id'] != current_user['user_id'] and current_user['role'] not in ['admin', 'super_admin', 'owner']:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return request_doc

@api_router.put("/requests/{request_id}/status")
async def update_request_status(request_id: str, status: str, admin: dict = Depends(require_admin)):
    result = await db.website_requests.update_one(
        {"id": request_id},
        {"$set": {"status": status}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"message": "Status updated"}

# ============== PAYMENTS ==============

@api_router.post("/payments/create")
async def create_payment(payment_data: PaymentCreate, current_user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0})
    currency = "SAR" if user_doc.get('country') == 'SA' else "USD"
    
    payment = Payment(
        user_id=current_user['user_id'],
        user_name=user_doc.get('name', 'Unknown'),
        user_email=user_doc.get('email', ''),
        payment_type=payment_data.payment_type,
        amount=payment_data.amount,
        currency=currency,
        proof_image_url=payment_data.proof_base64
    )
    
    doc = payment.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.payments.insert_one(doc)
    
    await log_activity(
        current_user['user_id'],
        "payment_created",
        "create",
        f"Payment: {payment_data.payment_type} - {payment_data.amount} {currency}",
        {"payment_type": payment_data.payment_type, "amount": payment_data.amount}
    )
    
    payment_type_ar = {
        "credits": "شراء نقاط",
        "subscription_images": "اشتراك صور",
        "subscription_videos": "اشتراك فيديو",
        "images_monthly": "اشتراك صور شهري",
        "videos_monthly": "اشتراك فيديو شهري"
    }.get(payment_data.payment_type, payment_data.payment_type)
    
    message = f"""💰 دفعة جديدة في Zitex!

👤 العميل: {user_doc.get('name', 'Unknown')}
📧 البريد: {user_doc.get('email', '')}
💳 النوع: {payment_type_ar}
💵 المبلغ: {payment_data.amount} {currency}

🔗 راجع من لوحة التحكم للموافقة"""
    
    await send_whatsapp_notification(message)
    
    return payment

@api_router.get("/payments")
async def get_payments(current_user: dict = Depends(get_current_user)):
    if current_user['role'] in ['admin', 'super_admin', 'owner']:
        payments = await db.payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    else:
        payments = await db.payments.find({"user_id": current_user['user_id']}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return payments

CREDITS_PACKAGES = [
    {"id": "starter", "name": "باقة المبتدئ", "credits": 100, "price_sar": 50, "price_usd": 13},
    {"id": "pro", "name": "باقة المحترف", "credits": 500, "price_sar": 200, "price_usd": 53},
    {"id": "enterprise", "name": "باقة الأعمال", "credits": 2000, "price_sar": 700, "price_usd": 187},
]

@api_router.put("/payments/{payment_id}/approve")
async def approve_payment(payment_id: str, admin_notes: Optional[str] = None, admin: dict = Depends(require_admin)):
    payment_doc = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not payment_doc:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    await db.payments.update_one(
        {"id": payment_id},
        {"$set": {"status": "approved", "admin_notes": admin_notes}}
    )
    
    payment_type = payment_doc['payment_type']
    user_id = payment_doc['user_id']
    
    if payment_type == "credits":
        for pkg in CREDITS_PACKAGES:
            if payment_doc['amount'] == (pkg['price_sar'] if payment_doc['currency'] == 'SAR' else pkg['price_usd']):
                await db.users.update_one(
                    {"id": user_id},
                    {"$inc": {"credits": pkg['credits']}}
                )
                break
    elif payment_type in ["subscription_images", "images_monthly"]:
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"subscription_type": "images", "subscription_expires": expires}}
        )
    elif payment_type in ["subscription_videos", "videos_monthly"]:
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"subscription_type": "videos", "subscription_expires": expires}}
        )
    
    await log_activity(
        admin['id'] if isinstance(admin, dict) and 'id' in admin else 'admin',
        "payment_approved",
        "edit",
        f"Approved payment {payment_id}",
        {"payment_id": payment_id, "user_id": user_id}
    )
    
    return {"message": "Payment approved"}

@api_router.put("/payments/{payment_id}/reject")
async def reject_payment(payment_id: str, admin_notes: Optional[str] = None, admin: dict = Depends(require_admin)):
    result = await db.payments.update_one(
        {"id": payment_id},
        {"$set": {"status": "rejected", "admin_notes": admin_notes}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"message": "Payment rejected"}

# ============== WEBSITES ==============

@api_router.post("/websites/create")
async def create_website(request_id: str, url: str, preview_image: Optional[str] = None, admin: dict = Depends(require_admin)):
    request_doc = await db.website_requests.find_one({"id": request_id}, {"_id": 0})
    if not request_doc:
        raise HTTPException(status_code=404, detail="Request not found")
    
    website = Website(
        request_id=request_id,
        user_id=request_doc['user_id'],
        url=url,
        preview_image=preview_image
    )
    
    doc = website.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.websites.insert_one(doc)
    
    return website

@api_router.get("/websites")
async def get_websites(current_user: dict = Depends(get_current_user)):
    if current_user['role'] in ['admin', 'super_admin', 'owner']:
        websites = await db.websites.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    else:
        websites = await db.websites.find({"user_id": current_user['user_id']}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return websites

@api_router.put("/websites/{website_id}/status")
async def update_website_status(website_id: str, status: str, admin: dict = Depends(require_admin)):
    result = await db.websites.update_one(
        {"id": website_id},
        {"$set": {"status": status}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Website not found")
    return {"message": "Status updated"}

# ============== FILE UPLOAD (FREE) ==============

@api_router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    file_category: str = Form(default="general"),
    current_user: dict = Depends(get_current_user)
):
    """Upload any file - FREE for all users"""
    try:
        # Check file size (50MB limit)
        contents = await file.read()
        if len(contents) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="حجم الملف أكبر من 50MB")
        
        # Generate unique filename
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        
        # For now, store as base64 (in production, use cloud storage)
        file_b64 = base64.b64encode(contents).decode()
        file_url = f"data:{file.content_type};base64,{file_b64}"
        
        # Save to database
        file_doc = {
            "id": str(uuid.uuid4()),
            "user_id": current_user['user_id'],
            "filename": file.filename,
            "unique_filename": unique_filename,
            "content_type": file.content_type,
            "size": len(contents),
            "category": file_category,
            "file_url": file_url,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.uploaded_files.insert_one(file_doc)
        
        await log_activity(
            current_user['user_id'],
            "file_uploaded",
            "create",
            f"Uploaded file: {file.filename} ({file_category})",
            {"filename": file.filename, "size": len(contents), "category": file_category}
        )
        
        return {
            "id": file_doc['id'],
            "filename": file.filename,
            "file_url": file_url,
            "size": len(contents),
            "category": file_category,
            "message": "تم رفع الملف بنجاح (مجاني)"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في رفع الملف: {str(e)}")

@api_router.get("/files/my-files")
async def get_my_files(current_user: dict = Depends(get_current_user)):
    """Get user's uploaded files"""
    files = await db.uploaded_files.find(
        {"user_id": current_user['user_id']},
        {"_id": 0, "file_url": 0}  # Don't return full base64 in list
    ).sort("created_at", -1).to_list(100)
    return {"files": files}

# ============== SOCIAL MEDIA EXPORT (FREE) ==============

SOCIAL_SPECS = {
    "tiktok": {"width": 1080, "height": 1920, "aspect": "9:16", "max_duration": 180},
    "snapchat": {"width": 1080, "height": 1920, "aspect": "9:16", "max_duration": 60},
    "instagram_reels": {"width": 1080, "height": 1920, "aspect": "9:16", "max_duration": 90},
    "instagram_story": {"width": 1080, "height": 1920, "aspect": "9:16", "max_duration": 15},
    "instagram_post": {"width": 1080, "height": 1080, "aspect": "1:1", "max_duration": 60},
    "youtube_shorts": {"width": 1080, "height": 1920, "aspect": "9:16", "max_duration": 60},
    "facebook": {"width": 1280, "height": 720, "aspect": "16:9", "max_duration": 240},
    "twitter": {"width": 1280, "height": 720, "aspect": "16:9", "max_duration": 140}
}

SOCIAL_TIPS = {
    "tiktok": ["استخدم موسيقى ترند", "أضف نص على الفيديو", "اجعل أول 3 ثواني جذابة"],
    "snapchat": ["أضف فلاتر وملصقات", "استخدم النص المتحرك", "اجعله قصير ومباشر"],
    "instagram_reels": ["استخدم الهاشتاقات المناسبة", "أضف موسيقى من مكتبة انستقرام", "تفاعل مع الترندات"],
    "instagram_story": ["أضف استطلاعات وأسئلة", "استخدم الملصقات التفاعلية", "انشر في أوقات الذروة"],
    "instagram_post": ["اكتب وصف جذاب", "استخدم 5-10 هاشتاقات", "رد على التعليقات بسرعة"],
    "youtube_shorts": ["أضف عنوان جذاب", "استخدم الوصف والهاشتاقات", "انشر بانتظام"],
    "facebook": ["شارك في المجموعات المناسبة", "أضف وصف مفصل", "استخدم الإعلانات المدفوعة"],
    "twitter": ["اجعله قصير ومؤثر", "استخدم الهاشتاقات الترند", "انشر في أوقات النشاط"]
}

@api_router.post("/social/export")
async def export_for_social(
    asset_id: str,
    platforms: List[str],
    current_user: dict = Depends(get_current_user)
):
    """Export media for social platforms - FREE"""
    exports = []
    
    for platform in platforms:
        if platform not in SOCIAL_SPECS:
            continue
        
        specs = SOCIAL_SPECS[platform]
        tips = SOCIAL_TIPS.get(platform, [])
        
        # Get platform icon
        icons = {
            "tiktok": "🎵", "snapchat": "👻", "instagram_reels": "📸",
            "instagram_story": "📱", "instagram_post": "🖼️",
            "youtube_shorts": "▶️", "facebook": "📘", "twitter": "🐦"
        }
        
        platform_names = {
            "tiktok": "TikTok", "snapchat": "Snapchat", "instagram_reels": "Instagram Reels",
            "instagram_story": "Instagram Story", "instagram_post": "Instagram Post",
            "youtube_shorts": "YouTube Shorts", "facebook": "Facebook", "twitter": "Twitter/X"
        }
        
        exports.append({
            "platform": platform,
            "platform_name": platform_names.get(platform, platform),
            "icon": icons.get(platform, "📱"),
            "specs": specs,
            "tips": tips,
            "download_url": None,  # In production, this would be a processed file URL
            "status": "ready"
        })
    
    await log_activity(
        current_user['user_id'],
        "social_export",
        "create",
        f"Exported for platforms: {', '.join(platforms)}",
        {"platforms": platforms, "asset_id": asset_id}
    )
    
    return {
        "exports": exports,
        "message": "تم تجهيز الملفات للتصدير (مجاني)"
    }

# ============== ADMIN ROUTES ==============

@api_router.get("/admin/stats")
async def get_admin_stats(admin: dict = Depends(require_admin)):
    stats = AdminStats(
        total_users=await db.users.count_documents({}),
        total_requests=await db.website_requests.count_documents({}),
        pending_requests=await db.website_requests.count_documents({"status": "pending"}),
        completed_requests=await db.website_requests.count_documents({"status": "completed"}),
        pending_payments=await db.payments.count_documents({"status": "pending"}),
        approved_payments=await db.payments.count_documents({"status": "approved"}),
        total_websites=await db.websites.count_documents({}),
        total_images_generated=await db.image_generations.count_documents({}),
        total_videos_generated=await db.video_generations.count_documents({}),
        total_activities=await db.activity_logs.count_documents({})
    )
    return stats

@api_router.get("/admin/users")
async def get_all_users(admin: dict = Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "password": 0}).sort("created_at", -1).to_list(1000)
    return users

@api_router.get("/admin/activities")
async def get_activities(limit: int = 100, admin: dict = Depends(require_admin)):
    activities = await db.activity_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return activities

@api_router.get("/pricing")
async def get_pricing():
    return {
        "credits_packages": CREDITS_PACKAGES,
        "service_costs": POINTS_CONFIG
    }

# ============== CORS & APP SETUP ==============

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the main API router
app.include_router(api_router)

# Import and include chat router
from routers import chat_router, set_ai_assistant
app.include_router(chat_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Zitex API - AI Creative Platform", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "ai_features": AI_FEATURES_ENABLED}
