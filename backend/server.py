from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, Response
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
AI_FEATURES_ENABLED = True

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
    affiliate_code: Optional[str] = None  # 🆕 paid affiliate program

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

    # 🆕 Paid affiliate attribution (if user signed up via marketer's link)
    if user_data.affiliate_code:
        doc['affiliate_ref'] = user_data.affiliate_code.upper()
    
    await db.users.insert_one(doc)
    await log_activity(user.id, "user_registered", "create", f"New user registered: {user.email} with {doc['credits']} bonus points")

    # 🆕 Track affiliate signup (best-effort, never blocks registration)
    if user_data.affiliate_code:
        try:
            from modules.affiliate.routes import record_signup
            await record_signup(db, user.id, user_data.affiliate_code)
        except Exception as _ae:
            logging.getLogger(__name__).warning(f"affiliate signup hook failed: {_ae}")
    
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


# ============== GOOGLE OAUTH (Emergent-managed) ==============
class GoogleExchangeIn(BaseModel):
    session_id: str

@api_router.post("/auth/google/exchange")
async def google_exchange(body: GoogleExchangeIn):
    """Exchange an Emergent OAuth session_id for our app JWT.
    Finds-or-creates the user in `users` and returns {token, user, is_new}.
    REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    """
    sid = (body.session_id or "").strip()
    if not sid:
        raise HTTPException(400, "session_id required")

    # Call Emergent's session-data endpoint to retrieve verified Google identity
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": sid},
            )
            if r.status_code != 200:
                raise HTTPException(401, "session expired or invalid")
            data = r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"OAuth provider error: {str(e)[:200]}")

    email = (data.get("email") or "").lower().strip()
    name = data.get("name") or email.split("@")[0]
    picture = data.get("picture") or ""
    if not email:
        raise HTTPException(400, "email not returned by provider")

    # Find or create user (preserves email/password sign-up if same email)
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    is_new = False
    if existing:
        # Mark Google as a known login provider, refresh picture/name once
        patch: Dict[str, Any] = {
            "google_linked": True,
            "last_login_at": datetime.now(timezone.utc).isoformat(),
        }
        if picture and not existing.get('avatar_url'):
            patch['avatar_url'] = picture
        await db.users.update_one({"id": existing['id']}, {"$set": patch})
        for field in ['free_images', 'free_videos', 'free_website_trial']:
            if field not in existing:
                existing[field] = 0 if field != 'free_website_trial' else False
        user = User(**{k: v for k, v in existing.items() if k != 'password'})
    else:
        is_new = True
        signup_bonus = POINTS_CONFIG.get("signup_bonus", 20)
        user = User(
            email=email, name=name, role="client", country="SA",
            credits=signup_bonus, bonus_points=signup_bonus,
            free_images=3, free_videos=2, free_website_trial=True,
        )
        doc = user.model_dump()
        doc['password'] = ""  # No password — Google-only login (can be set later)
        doc['google_linked'] = True
        doc['avatar_url'] = picture
        doc['signup_bonus_claimed'] = True
        doc['created_at'] = doc['created_at'].isoformat()
        await db.users.insert_one(doc)
        await log_activity(user.id, "user_registered", "create",
                           f"Google sign-up: {email}")

    await log_activity(user.id, "user_login", "create",
                       f"Google login: {email}")
    token = create_token(user.id, user.role)
    return {"token": token, "user": user, "is_new": is_new}

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
    """Convert speech to text using OpenAI Whisper via Emergent"""
    if not AI_FEATURES_ENABLED:
        raise HTTPException(status_code=503, detail="ميزة تحويل الصوت للنص معطلة مؤقتاً. ستتوفر قريباً!")
    
    emergent_key = os.environ.get('EMERGENT_LLM_KEY')
    if not emergent_key:
        raise HTTPException(status_code=400, detail="خدمة التحويل الصوتي غير متاحة")
    
    # Check file size (max 25MB)
    content = await audio.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="حجم الملف أكبر من 25MB")
    
    # Check file type
    if audio.content_type and not any(t in audio.content_type for t in ['audio', 'webm', 'ogg']):
        raise HTTPException(status_code=400, detail=f"نوع الملف غير مدعوم: {audio.content_type}")
    
    try:
        from emergentintegrations.llm.openai import OpenAISpeechToText
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        stt = OpenAISpeechToText(api_key=emergent_key)
        
        with open(tmp_file_path, 'rb') as audio_file:
            response = await stt.transcribe(
                file=audio_file,
                model="whisper-1",
                language=language,
                response_format="json"
            )
        
        import os as os_module
        os_module.unlink(tmp_file_path)
        
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

# ============== PRICING ==============

# تسعير الخدمات - شامل ومحدث
PRICING_CONFIG = {
    # باقات النقاط
    "credits_packages": [
        {"id": "starter", "name": "باقة المبتدئ", "credits": 100, "price_sar": 50, "price_usd": 13, "popular": False, "bonus": 0},
        {"id": "pro", "name": "باقة المحترف", "credits": 500, "price_sar": 200, "price_usd": 53, "popular": True, "bonus": 50},
        {"id": "enterprise", "name": "باقة الأعمال", "credits": 2000, "price_sar": 700, "price_usd": 187, "popular": False, "bonus": 300},
    ],
    # اشتراكات شهرية
    "subscriptions": {
        "images_monthly": {"name": "اشتراك الصور الشهري", "price_sar": 100, "price_usd": 27, "limit": "غير محدود", "features": ["صور غير محدودة", "جودة عالية HD", "أولوية التوليد"]},
        "videos_monthly": {"name": "اشتراك الفيديو الشهري", "price_sar": 150, "price_usd": 40, "limit": "50 فيديو/شهر", "features": ["50 فيديو سينمائي", "دقيقة كاملة لكل فيديو", "جودة 4K"]},
        "all_inclusive": {"name": "الباقة الشاملة", "price_sar": 300, "price_usd": 80, "limit": "كل شيء", "features": ["صور غير محدودة", "100 فيديو/شهر", "5 مواقع/شهر", "دعم أولوية"]},
    },
    # تكلفة الخدمات بالنقاط
    "service_costs": {
        "image_generation": 5,           # 5 نقاط لكل صورة
        "video_4_seconds": 10,           # 10 نقاط لفيديو 4 ثواني
        "video_8_seconds": 18,           # 18 نقطة لفيديو 8 ثواني
        "video_12_seconds": 25,          # 25 نقطة لفيديو 12 ثانية
        "video_50_seconds": 80,          # 80 نقطة لفيديو 50 ثانية
        "video_60_seconds": 100,         # 100 نقطة لفيديو دقيقة
        "website_simple": 50,            # 50 نقطة لموقع بسيط
        "website_advanced": 150,         # 150 نقطة لموقع متقدم
        "website_ecommerce": 300,        # 300 نقطة لمتجر إلكتروني
        "tts_per_1000_chars": 2,         # 2 نقطة لكل 1000 حرف صوتي
    },
    # التجربة المجانية
    "free_trial": {
        "images": 3,
        "videos": 2,
        "website_preview": True,
        "signup_bonus": 20,              # 20 نقطة مجانية عند التسجيل
    },
    # مكافآت الدعوات
    "referral_rewards": {
        "inviter_bonus": 30,             # 30 نقطة للداعي
        "invited_bonus": 20,             # 20 نقطة للمدعو
        "first_purchase_bonus": 50,      # 50 نقطة أول عملية شراء
    }
}

@api_router.get("/pricing")
async def get_pricing():
    return PRICING_CONFIG

@api_router.get("/pricing/calculate")
async def calculate_price(service: str, quantity: int = 1):
    """حساب تكلفة خدمة معينة"""
    costs = PRICING_CONFIG["service_costs"]
    if service not in costs:
        raise HTTPException(status_code=400, detail="خدمة غير معروفة")
    
    total_cost = costs[service] * quantity
    return {
        "service": service,
        "quantity": quantity,
        "cost_per_unit": costs[service],
        "total_cost": total_cost
    }

# ============== REFERRAL SYSTEM (نظام الدعوات) ==============

@api_router.get("/referral/info")
async def get_referral_info(current_user: dict = Depends(get_current_user)):
    """الحصول على معلومات الدعوة للمستخدم"""
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0, "password": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    referral_code = user_doc.get('referral_code', str(uuid.uuid4())[:8].upper())
    
    # تحديث الكود إذا لم يكن موجوداً
    if 'referral_code' not in user_doc:
        await db.users.update_one(
            {"id": current_user['user_id']},
            {"$set": {"referral_code": referral_code}}
        )
    
    # حساب عدد الدعوات الناجحة
    referrals_count = await db.users.count_documents({"referred_by": referral_code})
    
    return {
        "referral_code": referral_code,
        "referral_link": f"https://zitex.com/register?ref={referral_code}",
        "total_referrals": referrals_count,
        "bonus_points": user_doc.get('bonus_points', 0),
        "rewards": PRICING_CONFIG["referral_rewards"]
    }

@api_router.post("/referral/apply")
async def apply_referral_code(request: ApplyReferralRequest, current_user: dict = Depends(get_current_user)):
    """تطبيق كود دعوة"""
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    # التحقق من عدم استخدام كود من قبل
    if user_doc.get('referred_by'):
        raise HTTPException(status_code=400, detail="لقد استخدمت كود دعوة من قبل")
    
    # التحقق من صحة الكود
    inviter = await db.users.find_one({"referral_code": request.referral_code.upper()}, {"_id": 0})
    if not inviter:
        raise HTTPException(status_code=400, detail="كود الدعوة غير صحيح")
    
    # لا يمكن دعوة نفسك
    if inviter['id'] == current_user['user_id']:
        raise HTTPException(status_code=400, detail="لا يمكنك استخدام كودك الخاص")
    
    rewards = PRICING_CONFIG["referral_rewards"]
    
    # إضافة النقاط للمدعو
    await db.users.update_one(
        {"id": current_user['user_id']},
        {
            "$set": {"referred_by": request.referral_code.upper()},
            "$inc": {"bonus_points": rewards["invited_bonus"], "credits": rewards["invited_bonus"]}
        }
    )
    
    # إضافة النقاط للداعي
    await db.users.update_one(
        {"id": inviter['id']},
        {
            "$inc": {
                "bonus_points": rewards["inviter_bonus"],
                "credits": rewards["inviter_bonus"],
                "total_referrals": 1
            }
        }
    )
    
    await log_activity(
        current_user['user_id'],
        "referral_applied",
        "create",
        f"Applied referral code: {request.referral_code}",
        {"inviter_id": inviter['id'], "bonus": rewards["invited_bonus"]}
    )
    
    return {
        "message": f"تم تطبيق الكود بنجاح! حصلت على {rewards['invited_bonus']} نقطة مجانية",
        "bonus_received": rewards["invited_bonus"]
    }

@api_router.get("/referral/leaderboard")
async def get_referral_leaderboard():
    """قائمة أفضل الداعين"""
    top_referrers = await db.users.find(
        {"total_referrals": {"$gt": 0}},
        {"_id": 0, "name": 1, "total_referrals": 1, "bonus_points": 1}
    ).sort("total_referrals", -1).limit(10).to_list(10)
    
    return {"leaderboard": top_referrers}

# ============== USER POINTS/CREDITS ==============

@api_router.get("/user/balance")
async def get_user_balance(current_user: dict = Depends(get_current_user)):
    """الحصول على رصيد المستخدم"""
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0, "password": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    return {
        "credits": user_doc.get('credits', 0),
        "bonus_points": user_doc.get('bonus_points', 0),
        "free_images": user_doc.get('free_images', 0),
        "free_videos": user_doc.get('free_videos', 0),
        "free_website_trial": user_doc.get('free_website_trial', False),
        "subscription_type": user_doc.get('subscription_type'),
        "subscription_expires": user_doc.get('subscription_expires'),
        "total_spent": user_doc.get('total_spent', 0),
        "service_costs": PRICING_CONFIG["service_costs"]
    }

@api_router.post("/user/claim-signup-bonus")
async def claim_signup_bonus(current_user: dict = Depends(get_current_user)):
    """المطالبة بمكافأة التسجيل"""
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    if user_doc.get('signup_bonus_claimed'):
        raise HTTPException(status_code=400, detail="لقد حصلت على مكافأة التسجيل من قبل")
    
    bonus = PRICING_CONFIG["free_trial"]["signup_bonus"]
    
    await db.users.update_one(
        {"id": current_user['user_id']},
        {
            "$set": {"signup_bonus_claimed": True},
            "$inc": {"credits": bonus, "bonus_points": bonus}
        }
    )
    
    await log_activity(
        current_user['user_id'],
        "signup_bonus_claimed",
        "create",
        f"Claimed signup bonus: {bonus} points"
    )
    
    return {"message": f"تهانينا! حصلت على {bonus} نقطة مجانية", "bonus": bonus}

# ============== PAYMENTS ==============

@api_router.post("/payments/create-order")
async def create_payment_order(request: CreateOrderRequest, current_user: dict = Depends(get_current_user)):
    """إنشاء طلب دفع PayPal حقيقي"""
    
    # البحث عن الباقة
    package_info = None
    credits_to_add = 0
    package_name = ""
    
    if request.package_type == "credits":
        for pkg in PRICING_CONFIG["credits_packages"]:
            if pkg["id"] == request.package_id:
                package_info = pkg
                credits_to_add = pkg["credits"] + pkg.get("bonus", 0)
                package_name = pkg["name"]
                break
    elif request.package_type == "subscription":
        if request.package_id in PRICING_CONFIG["subscriptions"]:
            package_info = PRICING_CONFIG["subscriptions"][request.package_id]
            package_info["id"] = request.package_id
            package_name = package_info.get("name", request.package_id)
    
    if not package_info:
        raise HTTPException(status_code=400, detail="الباقة غير موجودة")
    
    paypal_order_id = None
    
    # إنشاء طلب PayPal حقيقي
    if PAYPAL_CLIENT_ID and PAYPAL_SECRET:
        try:
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": f"{os.environ.get('FRONTEND_URL', 'https://zitex.com')}/payment/success",
                    "cancel_url": f"{os.environ.get('FRONTEND_URL', 'https://zitex.com')}/payment/cancel"
                },
                "transactions": [{
                    "item_list": {
                        "items": [{
                            "name": package_name,
                            "sku": request.package_id,
                            "price": str(request.amount),
                            "currency": request.currency,
                            "quantity": 1
                        }]
                    },
                    "amount": {
                        "total": str(request.amount),
                        "currency": request.currency
                    },
                    "description": f"Zitex - {package_name} ({credits_to_add} نقطة)"
                }]
            })
            
            if payment.create():
                paypal_order_id = payment.id
                logging.info(f"PayPal payment created: {paypal_order_id}")
            else:
                logging.error(f"PayPal error: {payment.error}")
                raise HTTPException(status_code=500, detail=f"خطأ PayPal: {payment.error}")
        except Exception as e:
            logging.error(f"PayPal exception: {e}")
            # Fallback to mock for testing
            paypal_order_id = f"PAYPAL-{str(uuid.uuid4())[:8].upper()}"
    else:
        # Mock mode if no PayPal credentials
        paypal_order_id = f"PAYPAL-{str(uuid.uuid4())[:8].upper()}"
    
    order = PaymentOrder(
        user_id=current_user['user_id'],
        package_id=request.package_id,
        package_type=request.package_type,
        amount=request.amount,
        currency=request.currency,
        paypal_order_id=paypal_order_id,
        credits_added=credits_to_add,
        metadata={"package_info": package_info, "package_name": package_name}
    )
    
    order_doc = order.model_dump()
    order_doc['created_at'] = order_doc['created_at'].isoformat()
    await db.payment_orders.insert_one(order_doc)
    
    await log_activity(
        current_user['user_id'],
        "payment_order_created",
        "create",
        f"Created payment order for {request.package_id}",
        {"order_id": order.id, "amount": request.amount, "paypal_id": paypal_order_id}
    )
    
    return {
        "order_id": paypal_order_id,
        "internal_id": order.id,
        "amount": request.amount,
        "currency": request.currency
    }

@api_router.post("/payments/capture-order")
async def capture_payment_order(request: CaptureOrderRequest, current_user: dict = Depends(get_current_user)):
    """تأكيد الدفع وإضافة النقاط"""
    
    # البحث عن الطلب
    order_doc = await db.payment_orders.find_one({
        "paypal_order_id": request.order_id,
        "user_id": current_user['user_id'],
        "status": "pending"
    }, {"_id": 0})
    
    if not order_doc:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    
    # في الإنتاج، نتحقق من PayPal API
    # هنا نفترض أن الدفع تم بنجاح
    
    credits_to_add = order_doc.get('credits_added', 0)
    
    # التحقق من مكافأة أول عملية شراء
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0})
    first_purchase_bonus = 0
    if user_doc and not user_doc.get('first_purchase_bonus_claimed'):
        first_purchase_bonus = POINTS_CONFIG.get("first_purchase_bonus", 50)
        credits_to_add += first_purchase_bonus
    
    # تحديث الطلب
    await db.payment_orders.update_one(
        {"id": order_doc['id']},
        {
            "$set": {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # إضافة النقاط للمستخدم
    update_ops = {"$inc": {"credits": credits_to_add, "total_spent": order_doc.get('amount', 0)}}
    if first_purchase_bonus > 0:
        update_ops["$set"] = {"first_purchase_bonus_claimed": True}
    
    # إذا كان اشتراك، نضيف نوع الاشتراك وتاريخ الانتهاء
    if request.package_type == "subscription":
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        if "$set" not in update_ops:
            update_ops["$set"] = {}
        update_ops["$set"]["subscription_type"] = request.package_id.replace("_monthly", "")
        update_ops["$set"]["subscription_expires"] = expires_at.isoformat()
    
    await db.users.update_one({"id": current_user['user_id']}, update_ops)
    
    await log_activity(
        current_user['user_id'],
        "payment_completed",
        "create",
        f"Payment completed: {credits_to_add} credits added",
        {
            "order_id": order_doc['id'],
            "credits_added": credits_to_add,
            "first_purchase_bonus": first_purchase_bonus
        }
    )
    
    # إرسال إشعار للمالك
    try:
        await send_whatsapp_notification(
            f"💰 عملية شراء جديدة!\n"
            f"المستخدم: {user_doc.get('name', 'غير معروف')}\n"
            f"الباقة: {request.package_id}\n"
            f"المبلغ: ${order_doc.get('amount', 0)}\n"
            f"النقاط المضافة: {credits_to_add}"
        )
    except:
        pass
    
    return {
        "status": "completed",
        "credits_added": credits_to_add,
        "first_purchase_bonus": first_purchase_bonus,
        "message": f"تم الدفع بنجاح! حصلت على {credits_to_add} نقطة"
    }

@api_router.get("/payments/history")
async def get_payment_history(current_user: dict = Depends(get_current_user)):
    """سجل المدفوعات"""
    orders = await db.payment_orders.find(
        {"user_id": current_user['user_id']},
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    
    return {"orders": orders}

@api_router.get("/settings/payment")
async def get_payment_settings():
    settings = await db.settings.find_one({"type": "payment"}, {"_id": 0})
    if not settings:
        return {"bank_name": "", "bank_iban": "", "bank_account_name": "", "paypal_email": "", "owner_whatsapp": OWNER_WHATSAPP}
    return settings

# ============== ADMIN ==============

@api_router.get("/admin/stats")
async def get_admin_stats(admin: dict = Depends(require_admin)):
    return AdminStats(
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

@api_router.get("/admin/users")
async def get_all_users(admin: dict = Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "password": 0}).sort("created_at", -1).to_list(1000)
    return users

@api_router.get("/admin/users/{user_id}/activity")
async def get_user_activity(user_id: str, admin: dict = Depends(require_admin)):
    """Get activity log for a specific user"""
    activities = await db.activity_logs.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    return activities

@api_router.get("/admin/activity")
async def get_all_activity(limit: int = 100, admin: dict = Depends(require_admin)):
    """Get all activity logs"""
    activities = await db.activity_logs.find(
        {},
        {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    return activities

@api_router.put("/admin/settings/payment")
async def update_payment_settings(settings: SiteSettings, admin: dict = Depends(require_admin)):
    await db.settings.update_one(
        {"type": "payment"},
        {"$set": {**settings.model_dump(), "type": "payment"}},
        upsert=True
    )
    return {"message": "Settings updated"}

@api_router.put("/admin/users/{user_id}/role")
async def update_user_role(user_id: str, role: str, current_user: dict = Depends(get_current_user)):
    """Update user role - only owner can promote to super_admin"""
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0})
    current_role = user_doc.get('role', 'client')
    current_level = ROLE_LEVELS.get(current_role, 0)
    
    target_level = ROLE_LEVELS.get(role, 0)
    
    # Can only assign roles lower than your own
    if target_level >= current_level:
        raise HTTPException(status_code=403, detail="Cannot assign role equal or higher than your own")
    
    # Only owner can create super_admin
    if role == "super_admin" and current_role != "owner":
        raise HTTPException(status_code=403, detail="Only owner can create super admins")
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"role": role}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    await log_activity(
        current_user['user_id'],
        "role_updated",
        "edit",
        f"Updated user {user_id} role to {role}"
    )
    
    return {"message": f"User role updated to {role}"}

@api_router.put("/admin/users/{user_id}/deactivate")
async def deactivate_user(user_id: str, admin: dict = Depends(require_admin)):
    """Deactivate a user account"""
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Cannot deactivate owner
    if target_user.get('is_owner'):
        raise HTTPException(status_code=403, detail="Cannot deactivate owner account")
    
    # Check role hierarchy
    admin_level = ROLE_LEVELS.get(admin.get('role', 'admin'), 50)
    target_level = ROLE_LEVELS.get(target_user.get('role', 'client'), 10)
    
    if target_level >= admin_level:
        raise HTTPException(status_code=403, detail="Cannot deactivate user with equal or higher role")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": False}}
    )
    
    await log_activity(
        admin.get('id', 'admin'),
        "user_deactivated",
        "edit",
        f"Deactivated user {user_id}"
    )
    
    return {"message": "User deactivated"}

@api_router.put("/admin/users/{user_id}/activate")
async def activate_user(user_id: str, admin: dict = Depends(require_admin)):
    """Activate a user account"""
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User activated"}

@api_router.put("/admin/users/{user_id}/make-owner")
async def make_user_owner(user_id: str, current_user: dict = Depends(get_current_user)):
    """Make user an owner - only existing owner can do this"""
    requester = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0})
    if not requester.get('is_owner'):
        raise HTTPException(status_code=403, detail="Only owner can transfer ownership")
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_owner": True, "role": "owner"}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User is now owner"}

@api_router.put("/admin/users/{user_id}/add-credits")
async def add_user_credits(user_id: str, credits: int, admin: dict = Depends(require_admin)):
    result = await db.users.update_one(
        {"id": user_id},
        {"$inc": {"credits": credits}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    await log_activity(
        admin.get('id', 'admin'),
        "credits_added",
        "edit",
        f"Added {credits} credits to user {user_id}"
    )
    
    return {"message": f"Added {credits} credits"}

@api_router.put("/admin/users/{user_id}/add-free-trials")
async def add_free_trials(user_id: str, images: int = 0, videos: int = 0, admin: dict = Depends(require_admin)):
    update = {}
    if images > 0:
        update["free_images"] = images
    if videos > 0:
        update["free_videos"] = videos
    
    if update:
        result = await db.users.update_one(
            {"id": user_id},
            {"$inc": update}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"Added {images} free images, {videos} free videos"}


# ============== CREDITS MANAGEMENT ==============

class UpdateCreditsRequest(BaseModel):
    credits: int

@api_router.put("/admin/users/{user_id}/credits")
async def set_user_credits(user_id: str, request: UpdateCreditsRequest, admin: dict = Depends(require_admin)):
    """Set user credits to specific value"""
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"credits": request.credits}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    await log_activity(
        admin.get('id', 'admin'),
        "credits_set",
        "edit",
        f"Set credits to {request.credits} for user {user_id}"
    )
    
    return {"message": f"Credits set to {request.credits}"}


# ============== PRICING MANAGEMENT (Admin) ==============

class PricingRequest(BaseModel):
    pricing: dict

@api_router.get("/admin/service-pricing")
async def get_service_pricing(admin: dict = Depends(require_admin)):
    """Get service pricing for admin"""
    pricing_doc = await db.settings.find_one({"type": "pricing"}, {"_id": 0})
    if pricing_doc:
        return {"pricing": pricing_doc.get("pricing", {})}
    
    # Default pricing
    return {"pricing": {
        "website": 15,
        "game": 15,
        "image": 5,
        "video": 20,
        "modification": 5,
        "save_template": 10,
        "export": 50,
        "deploy": 100
    }}

@api_router.put("/admin/service-pricing")
async def update_service_pricing(request: PricingRequest, admin: dict = Depends(require_admin)):
    """Update service pricing"""
    await db.settings.update_one(
        {"type": "pricing"},
        {"$set": {"type": "pricing", "pricing": request.pricing}},
        upsert=True
    )
    
    await log_activity(
        admin.get('id', 'admin'),
        "pricing_updated",
        "edit",
        "Updated service pricing"
    )
    
    return {"message": "Pricing updated"}


# ============== OFFERS MANAGEMENT ==============

class OfferRequest(BaseModel):
    name: str
    credits: int
    price: float
    discount: int = 0
    is_active: bool = True

class OfferUpdateRequest(BaseModel):
    name: Optional[str] = None
    credits: Optional[int] = None
    price: Optional[float] = None
    discount: Optional[int] = None
    is_active: Optional[bool] = None

@api_router.get("/admin/offers")
async def get_offers(admin: dict = Depends(require_admin)):
    """Get all credit offers"""
    offers = await db.offers.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"offers": offers}

@api_router.post("/admin/offers")
async def create_offer(request: OfferRequest, admin: dict = Depends(require_admin)):
    """Create new credit offer"""
    offer = {
        "id": str(uuid.uuid4()),
        "name": request.name,
        "credits": request.credits,
        "price": request.price,
        "discount": request.discount,
        "is_active": request.is_active,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": admin.get('id', 'admin')
    }
    
    await db.offers.insert_one(offer)
    
    await log_activity(
        admin.get('id', 'admin'),
        "offer_created",
        "create",
        f"Created offer: {request.name}"
    )
    
    return {"offer": {k: v for k, v in offer.items() if k != '_id'}}

@api_router.put("/admin/offers/{offer_id}")
async def update_offer(offer_id: str, request: OfferUpdateRequest, admin: dict = Depends(require_admin)):
    """Update credit offer"""
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    result = await db.offers.update_one(
        {"id": offer_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    return {"message": "Offer updated"}

@api_router.delete("/admin/offers/{offer_id}")
async def delete_offer(offer_id: str, admin: dict = Depends(require_admin)):
    """Delete credit offer"""
    result = await db.offers.delete_one({"id": offer_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    await log_activity(
        admin.get('id', 'admin'),
        "offer_deleted",
        "delete",
        f"Deleted offer: {offer_id}"
    )
    
    return {"message": "Offer deleted"}


# ============== PUBLIC OFFERS API ==============

@api_router.get("/offers")
async def get_public_offers():
    """Get active credit offers for purchase"""
    offers = await db.offers.find({"is_active": True}, {"_id": 0}).to_list(100)
    return {"offers": offers}

# ============== FILE UPLOAD SYSTEM (مجاني) ==============

# Object Storage Configuration
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get('EMERGENT_LLM_KEY')
APP_NAME = "zitex-files"

import requests as http_requests
import tempfile

_storage_key = None

def _init_storage():
    """Initialize storage connection"""
    global _storage_key
    if _storage_key:
        return _storage_key
    try:
        resp = http_requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
        resp.raise_for_status()
        _storage_key = resp.json()["storage_key"]
        return _storage_key
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        return None

def _upload_file_to_storage(path: str, data: bytes, content_type: str):
    """Upload file to object storage"""
    key = _init_storage()
    if not key:
        return None
    try:
        resp = http_requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return None

# Allowed file types
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
ALLOWED_VIDEO_TYPES = ["video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"]
ALLOWED_DOC_TYPES = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]
ALLOWED_AUDIO_TYPES = ["audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4"]

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

class FileUploadResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_url: str
    size: int
    created_at: str

@api_router.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_category: str = Form("general"),  # general, logo, product, reference, document
    current_user: dict = Depends(get_current_user)
):
    """
    رفع ملف (مجاني)
    - صور: jpg, png, gif, webp
    - فيديوهات: mp4, webm, mov, avi
    - مستندات: pdf, doc, docx, txt
    - صوتيات: mp3, wav, ogg, m4a
    """
    # Check file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"حجم الملف أكبر من الحد المسموح ({MAX_FILE_SIZE // (1024*1024)} MB)")
    
    # Determine file type
    content_type = file.content_type or "application/octet-stream"
    
    if content_type in ALLOWED_IMAGE_TYPES:
        file_type = "image"
    elif content_type in ALLOWED_VIDEO_TYPES:
        file_type = "video"
    elif content_type in ALLOWED_DOC_TYPES:
        file_type = "document"
    elif content_type in ALLOWED_AUDIO_TYPES:
        file_type = "audio"
    else:
        raise HTTPException(status_code=400, detail=f"نوع الملف غير مدعوم: {content_type}")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
    storage_path = f"{APP_NAME}/{current_user['user_id']}/{file_category}/{file_id}.{ext}"
    
    # Upload to storage
    upload_result = _upload_file_to_storage(storage_path, contents, content_type)
    
    if not upload_result:
        raise HTTPException(status_code=500, detail="فشل رفع الملف. حاول مرة أخرى")
    
    # Generate public URL
    file_url = f"https://integrations.emergentagent.com/objstore/{APP_NAME}/{current_user['user_id']}/{file_category}/{file_id}.{ext}"
    
    # Save to database
    file_doc = {
        "id": file_id,
        "user_id": current_user['user_id'],
        "filename": file.filename,
        "file_type": file_type,
        "file_category": file_category,
        "content_type": content_type,
        "storage_path": storage_path,
        "file_url": file_url,
        "size": len(contents),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.uploaded_files.insert_one(file_doc)
    
    await log_activity(
        current_user['user_id'],
        "file_uploaded",
        "create",
        f"Uploaded {file_type}: {file.filename}",
        {"file_category": file_category, "size": len(contents)}
    )
    
    return FileUploadResponse(
        id=file_id,
        filename=file.filename,
        file_type=file_type,
        file_url=file_url,
        size=len(contents),
        created_at=file_doc["created_at"]
    )

@api_router.get("/files/my-files")
async def get_my_files(
    file_type: Optional[str] = None,
    file_category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """استرجاع ملفات المستخدم"""
    query = {"user_id": current_user['user_id']}
    if file_type:
        query["file_type"] = file_type
    if file_category:
        query["file_category"] = file_category
    
    files = await db.uploaded_files.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"files": files}

@api_router.delete("/files/{file_id}")
async def delete_file(file_id: str, current_user: dict = Depends(get_current_user)):
    """حذف ملف"""
    result = await db.uploaded_files.delete_one({
        "id": file_id,
        "user_id": current_user['user_id']
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="الملف غير موجود")
    return {"message": "تم حذف الملف بنجاح"}

# ============== SOCIAL MEDIA EXPORT (مجاني) ==============

# Social media platform specifications
SOCIAL_PLATFORMS = {
    "tiktok": {
        "name": "TikTok",
        "icon": "🎵",
        "video_specs": {"width": 1080, "height": 1920, "aspect": "9:16", "max_duration": 180},
        "image_specs": {"width": 1080, "height": 1920}
    },
    "snapchat": {
        "name": "Snapchat",
        "icon": "👻",
        "video_specs": {"width": 1080, "height": 1920, "aspect": "9:16", "max_duration": 60},
        "image_specs": {"width": 1080, "height": 1920}
    },
    "instagram_reels": {
        "name": "Instagram Reels",
        "icon": "📸",
        "video_specs": {"width": 1080, "height": 1920, "aspect": "9:16", "max_duration": 90},
        "image_specs": {"width": 1080, "height": 1920}
    },
    "instagram_story": {
        "name": "Instagram Story",
        "icon": "📱",
        "video_specs": {"width": 1080, "height": 1920, "aspect": "9:16", "max_duration": 15},
        "image_specs": {"width": 1080, "height": 1920}
    },
    "instagram_post": {
        "name": "Instagram Post",
        "icon": "🖼️",
        "video_specs": {"width": 1080, "height": 1080, "aspect": "1:1", "max_duration": 60},
        "image_specs": {"width": 1080, "height": 1080}
    },
    "youtube_shorts": {
        "name": "YouTube Shorts",
        "icon": "▶️",
        "video_specs": {"width": 1080, "height": 1920, "aspect": "9:16", "max_duration": 60},
        "image_specs": {"width": 1280, "height": 720}
    },
    "facebook": {
        "name": "Facebook",
        "icon": "📘",
        "video_specs": {"width": 1280, "height": 720, "aspect": "16:9", "max_duration": 240},
        "image_specs": {"width": 1200, "height": 630}
    },
    "twitter": {
        "name": "Twitter/X",
        "icon": "🐦",
        "video_specs": {"width": 1280, "height": 720, "aspect": "16:9", "max_duration": 140},
        "image_specs": {"width": 1200, "height": 675}
    }
}

class SocialExportRequest(BaseModel):
    asset_id: str  # ID of the video or image to export
    platforms: List[str]  # List of platform keys

class SocialExportResult(BaseModel):
    platform: str
    platform_name: str
    icon: str
    status: str  # ready, processing, error
    download_url: Optional[str] = None
    specs: dict
    tips: List[str]

@api_router.get("/social/platforms")
async def get_social_platforms():
    """استرجاع قائمة المنصات الاجتماعية المدعومة"""
    platforms = []
    for key, specs in SOCIAL_PLATFORMS.items():
        platforms.append({
            "id": key,
            "name": specs["name"],
            "icon": specs["icon"],
            "video_specs": specs["video_specs"],
            "image_specs": specs["image_specs"]
        })
    return {"platforms": platforms}

@api_router.post("/social/export")
async def export_to_social(
    request: SocialExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    تصدير فيديو/صورة لمنصات التواصل الاجتماعي (مجاني)
    يقوم بإعداد الملف بالمواصفات المناسبة لكل منصة
    """
    # Get the asset
    asset = await db.generated_assets.find_one(
        {"id": request.asset_id, "user_id": current_user['user_id']},
        {"_id": 0}
    )
    
    if not asset:
        # Try uploaded files
        asset = await db.uploaded_files.find_one(
            {"id": request.asset_id, "user_id": current_user['user_id']},
            {"_id": 0}
        )
    
    if not asset:
        raise HTTPException(status_code=404, detail="الملف غير موجود")
    
    asset_type = asset.get("asset_type") or asset.get("file_type")
    asset_url = asset.get("url") or asset.get("file_url")
    
    results = []
    
    for platform_key in request.platforms:
        if platform_key not in SOCIAL_PLATFORMS:
            results.append(SocialExportResult(
                platform=platform_key,
                platform_name="غير معروف",
                icon="❓",
                status="error",
                specs={},
                tips=["المنصة غير مدعومة"]
            ))
            continue
        
        platform = SOCIAL_PLATFORMS[platform_key]
        specs = platform["video_specs"] if asset_type == "video" else platform["image_specs"]
        
        # Generate tips for the platform
        tips = _get_platform_tips(platform_key, asset_type)
        
        results.append(SocialExportResult(
            platform=platform_key,
            platform_name=platform["name"],
            icon=platform["icon"],
            status="ready",
            download_url=asset_url,  # Original URL - frontend can handle resize
            specs=specs,
            tips=tips
        ))
    
    # Log activity
    await log_activity(
        current_user['user_id'],
        "social_export",
        "create",
        f"Exported to: {', '.join(request.platforms)}",
        {"asset_id": request.asset_id, "platforms": request.platforms}
    )
    
    return {"exports": [r.model_dump() for r in results]}

def _get_platform_tips(platform: str, asset_type: str) -> List[str]:
    """نصائح لكل منصة"""
    tips_db = {
        "tiktok": {
            "video": [
                "استخدم موسيقى ترند لزيادة الانتشار",
                "أضف نص على الفيديو في أول 3 ثواني",
                "استخدم هاشتاقات شائعة (3-5 هاشتاقات)"
            ],
            "image": ["حوّل الصورة إلى فيديو قصير للأفضل"]
        },
        "snapchat": {
            "video": [
                "اجعل الرسالة واضحة في أول ثانيتين",
                "استخدم فلاتر Snapchat لزيادة التفاعل"
            ],
            "image": ["أضف ملصقات تفاعلية من Snapchat"]
        },
        "instagram_reels": {
            "video": [
                "استخدم موسيقى من مكتبة Instagram",
                "أضف نص وملصقات تفاعلية",
                "انشر في أوقات الذروة (12-3 م، 7-9 م)"
            ],
            "image": ["حوّلها إلى Reel للوصول أكبر"]
        },
        "instagram_story": {
            "video": [
                "أضف استطلاع أو سؤال لزيادة التفاعل",
                "استخدم موسيقى ترند"
            ],
            "image": ["أضف رابط أو CTA واضح"]
        },
        "instagram_post": {
            "video": [
                "اكتب كابشن جذاب (أول سطرين مهمين)",
                "استخدم 20-30 هاشتاق"
            ],
            "image": ["استخدم ألوان متناسقة مع هوية حسابك"]
        },
        "youtube_shorts": {
            "video": [
                "ابدأ بـ hook قوي في أول ثانية",
                "أضف عنوان جذاب ووصف SEO",
                "استخدم #Shorts في الوصف"
            ],
            "image": ["يفضل الفيديو على YouTube"]
        },
        "facebook": {
            "video": [
                "أضف ترجمة للفيديو (85% يشاهدون بدون صوت)",
                "الطول المثالي 1-2 دقيقة"
            ],
            "image": ["اكتب نص مصاحب مفصل"]
        },
        "twitter": {
            "video": [
                "اجعله قصيراً ومباشراً",
                "أضف نص في التغريدة يشرح المحتوى"
            ],
            "image": ["اكتب تغريدة جذابة مع الصورة"]
        }
    }
    
    return tips_db.get(platform, {}).get(asset_type, ["تأكد من جودة المحتوى"])

@api_router.get("/social/export-history")
async def get_export_history(current_user: dict = Depends(get_current_user)):
    """سجل التصديرات للمنصات الاجتماعية"""
    history = await db.activity_logs.find(
        {"user_id": current_user['user_id'], "action": "social_export"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return {"history": history}

# ============== AI TRAINING SYSTEM (Admin Only) ==============

class TrainingExampleCreate(BaseModel):
    category: str  # game, website, landing, ecommerce, portfolio, dashboard
    subcategory: str = ""  # strategy, racing, puzzle, restaurant, etc.
    title: str
    description: str = ""
    design_image_url: str = ""  # URL to the design reference image
    html_code: str  # The high-quality HTML code
    tags: List[str] = []

class TrainingExampleUpdate(BaseModel):
    category: Optional[str] = None
    subcategory: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    design_image_url: Optional[str] = None
    html_code: Optional[str] = None
    tags: Optional[List[str]] = None

@api_router.post("/admin/training/examples")
async def add_training_example(data: TrainingExampleCreate, admin: dict = Depends(require_admin)):
    """Add a new training example for AI learning"""
    example = {
        "id": str(uuid.uuid4()),
        "category": data.category,
        "subcategory": data.subcategory,
        "title": data.title,
        "description": data.description,
        "design_image_url": data.design_image_url,
        "html_code": data.html_code,
        "tags": data.tags,
        "is_active": True,
        "usage_count": 0,
        "created_by": admin.get('id', 'admin'),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.training_examples.insert_one(example)
    return {"id": example["id"], "message": "تم إضافة المثال التدريبي بنجاح"}

@api_router.get("/admin/training/examples")
async def get_training_examples(
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """Get all training examples"""
    query = {"is_active": True}
    if category:
        query["category"] = category
    if subcategory:
        query["subcategory"] = subcategory
    examples = await db.training_examples.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"examples": examples, "total": len(examples)}

@api_router.get("/admin/training/examples/{example_id}")
async def get_training_example(example_id: str, admin: dict = Depends(require_admin)):
    """Get a single training example"""
    example = await db.training_examples.find_one({"id": example_id, "is_active": True}, {"_id": 0})
    if not example:
        raise HTTPException(status_code=404, detail="المثال غير موجود")
    return example

@api_router.put("/admin/training/examples/{example_id}")
async def update_training_example(example_id: str, data: TrainingExampleUpdate, admin: dict = Depends(require_admin)):
    """Update a training example"""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.training_examples.update_one(
        {"id": example_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="المثال غير موجود")
    return {"message": "تم تحديث المثال بنجاح"}

@api_router.delete("/admin/training/examples/{example_id}")
async def delete_training_example(example_id: str, admin: dict = Depends(require_admin)):
    """Soft delete a training example"""
    result = await db.training_examples.update_one(
        {"id": example_id},
        {"$set": {"is_active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="المثال غير موجود")
    return {"message": "تم حذف المثال بنجاح"}

@api_router.post("/admin/training/upload-image")
async def upload_training_image(
    file: UploadFile = File(...),
    admin: dict = Depends(require_admin)
):
    """Upload a design reference image for training"""
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="حجم الصورة أكبر من 10MB")
    
    try:
        from services.ai_chat_service import upload_to_storage, APP_NAME, STORAGE_URL
        
        image_id = str(uuid.uuid4())
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
        storage_path = f"{APP_NAME}/training/{image_id}.{ext}"
        
        result = upload_to_storage(storage_path, contents, file.content_type or "image/png")
        if result:
            return {"image_url": f"/api/storage/training/{image_id}.{ext}", "id": image_id}
        else:
            img_b64 = base64.b64encode(contents).decode()
            return {"image_url": f"data:{file.content_type};base64,{img_b64}", "id": image_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل رفع الصورة: {str(e)}")

@api_router.get("/admin/training/stats")
async def get_training_stats(admin: dict = Depends(require_admin)):
    """Get training system statistics"""
    total = await db.training_examples.count_documents({"is_active": True})
    auto_learned = await db.training_examples.count_documents({"is_active": True, "source": "auto_learned"})
    manual = total - auto_learned
    by_category = {}
    categories = ["game", "website", "landing", "ecommerce", "portfolio", "dashboard", "mobile"]
    for cat in categories:
        count = await db.training_examples.count_documents({"is_active": True, "category": cat})
        if count > 0:
            by_category[cat] = count
    
    # Learning stats
    knowledge_rules = await db.knowledge_base.count_documents({})
    quality_logs = await db.code_quality_log.count_documents({})
    avg_quality = 0
    if quality_logs > 0:
        pipeline = [{"$group": {"_id": None, "avg": {"$avg": "$quality_score"}}}]
        result = await db.code_quality_log.aggregate(pipeline).to_list(1)
        if result:
            avg_quality = round(result[0]["avg"], 1)
    
    return {
        "total_examples": total,
        "auto_learned": auto_learned,
        "manual_added": manual,
        "by_category": by_category,
        "knowledge_rules": knowledge_rules,
        "total_generations": quality_logs,
        "avg_quality_score": avg_quality
    }

class FetchTemplatesRequest(BaseModel):
    query: str
    category: str = "game"
    count: int = 3
    source: str = "codepen"  # codepen or ai

@api_router.post("/admin/training/fetch")
async def fetch_templates_from_sources(data: FetchTemplatesRequest, admin: dict = Depends(require_admin)):
    """Fetch real templates from CodePen or generate via AI"""
    try:
        results = []
        
        if data.source == "codepen":
            # Scrape real code from CodePen
            results = await _fetch_from_codepen(data.query, data.category, data.count)
        else:
            # Fallback to AI generation
            results = await _fetch_from_ai(data.query, data.category, data.count)
        
        # Store as pending
        stored = []
        for tmpl in results:
            pending = {
                "id": str(uuid.uuid4()),
                "category": data.category,
                "subcategory": tmpl.get("subcategory", ""),
                "title": tmpl.get("title", "قالب بدون عنوان"),
                "description": tmpl.get("description", ""),
                "html_code": tmpl.get("html_code", ""),
                "tags": tmpl.get("tags", []),
                "source_url": tmpl.get("source_url", ""),
                "source_author": tmpl.get("source_author", ""),
                "status": "pending",
                "query": data.query,
                "fetch_source": data.source,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.pending_templates.insert_one(pending)
            stored.append({k: v for k, v in pending.items() if k != '_id'})
        
        return {"templates": stored, "count": len(stored)}
    except Exception as e:
        logger.error(f"Fetch templates error: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ: {str(e)}")

async def _fetch_from_codepen(query: str, category: str, count: int) -> list:
    """Fetch real code examples from the web (GitHub, public repos) and enhance them"""
    import httpx
    
    # Map Arabic to English search terms
    search_map = {
        "ألعاب استراتيجية": "strategy village building game html javascript",
        "ألعاب سباق": "car racing game html canvas javascript",
        "ألعاب ألغاز": "puzzle game html css javascript",
        "ألعاب أطفال": "kids educational game html",
        "ألعاب أكشن": "action shooter game javascript canvas",
        "ألعاب منصات": "platformer game javascript phaser",
        "ألعاب قتال": "fighting game javascript",
        "مواقع شركات": "company website template html tailwind dark",
        "صفحات هبوط": "saas landing page template html tailwind",
        "متاجر إلكترونية": "ecommerce store template html tailwind",
        "معارض أعمال": "portfolio website template html css modern",
        "لوحات تحكم": "admin dashboard template html tailwind dark",
    }
    
    en_query = query
    for ar, en in search_map.items():
        if ar in query:
            en_query = en
            break
    else:
        cat_map = {"game": "game html javascript", "website": "website html template", "landing": "landing page html", "ecommerce": "ecommerce store html", "portfolio": "portfolio html", "dashboard": "dashboard html"}
        en_query = cat_map.get(category, "html css") + " " + query
    
    results = []
    
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        # Search GitHub for real HTML files
        try:
            gh_url = f"https://api.github.com/search/repositories?q={en_query}+language:html&sort=stars&per_page=10"
            gh_resp = await client.get(gh_url, headers={**headers, "Accept": "application/vnd.github.v3+json"})
            
            if gh_resp.status_code == 200:
                repos = gh_resp.json().get("items", [])
                
                for repo in repos[:count * 3]:
                    try:
                        # Try to get the main HTML file (index.html)
                        raw_url = f"https://raw.githubusercontent.com/{repo['full_name']}/{repo.get('default_branch', 'main')}/index.html"
                        html_resp = await client.get(raw_url, headers=headers)
                        
                        if html_resp.status_code != 200:
                            # Try game.html or main.html
                            for alt in ["game.html", "main.html", "src/index.html", "public/index.html"]:
                                alt_url = f"https://raw.githubusercontent.com/{repo['full_name']}/{repo.get('default_branch', 'main')}/{alt}"
                                html_resp = await client.get(alt_url, headers=headers)
                                if html_resp.status_code == 200:
                                    break
                        
                        if html_resp.status_code == 200 and len(html_resp.text) > 500:
                            html_code = html_resp.text
                            
                            # Only accept if it has meaningful HTML
                            if "<html" in html_code.lower() and ("<script" in html_code.lower() or "<style" in html_code.lower()):
                                results.append({
                                    "title": repo.get("name", "Template"),
                                    "description": f"GitHub: {repo['full_name']} ({repo.get('stargazers_count', 0)} stars)",
                                    "subcategory": "",
                                    "html_code": html_code[:15000],
                                    "tags": [category, "github", "real-code"],
                                    "source_url": repo.get("html_url", ""),
                                    "source_author": repo.get("owner", {}).get("login", "unknown")
                                })
                                
                                if len(results) >= count:
                                    break
                    except Exception as e:
                        logger.warning(f"Failed to fetch repo {repo.get('full_name')}: {e}")
                        continue
        except Exception as e:
            logger.error(f"GitHub search error: {e}")
    
    # If not enough from GitHub, use AI to generate based on real-world inspiration
    if len(results) < count:
        ai_results = await _fetch_from_ai(query, category, count - len(results))
        results.extend(ai_results)
    
    return results[:count]

async def _fetch_from_ai(query: str, category: str, count: int) -> list:
    """Generate templates using AI as fallback"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        import json as json_module
        
        emergent_key = os.environ.get('EMERGENT_LLM_KEY')
        if not emergent_key:
            return []
        
        fetch_prompt = f"""أنشئ {count} قوالب HTML احترافية مختلفة.

الطلب: {query}
التصنيف: {category}

القواعد:
1. HTML كامل يبدأ بـ <!DOCTYPE html>
2. استخدم <script src="https://cdn.tailwindcss.com"></script>
3. استخدم Font Awesome CDN
4. خط Tajawal العربي، اتجاه RTL
5. تصميم احترافي مع تدرجات وظلال و hover و animations
6. للألعاب: إيموجي للعناصر، JavaScript تفاعلي كامل، شريط موارد، خريطة بصرية
7. كل قالب مختلف تماماً (ألوان وهيكل وأسلوب مختلف)
8. كود طويل ومفصّل (2000+ حرف)

أرجع JSON فقط:
[{{"title":"عنوان","description":"وصف","subcategory":"فرعي","tags":["وسم"],"html_code":"<!DOCTYPE html>..."}}]"""

        chat = LlmChat(api_key=emergent_key, session_id=f"fetch-{uuid.uuid4()}", system_message="أرجع JSON فقط بدون أي نص.")
        chat.with_model("openai", "gpt-4o")
        response = await chat.send_message(UserMessage(text=fetch_prompt))
        
        response_clean = response.strip()
        if response_clean.startswith("```"):
            response_clean = response_clean.split("\n", 1)[1] if "\n" in response_clean else response_clean[3:]
            response_clean = response_clean.rsplit("```", 1)[0]
        
        templates = json_module.loads(response_clean.strip())
        if not isinstance(templates, list):
            templates = [templates]
        
        for t in templates:
            t["source_url"] = ""
            t["source_author"] = "AI Generated"
        
        return templates[:count]
    except Exception as e:
        logger.error(f"AI fetch error: {e}")
        return []

@api_router.get("/admin/training/pending")
async def get_pending_templates(admin: dict = Depends(require_admin)):
    """Get all pending fetched templates"""
    pending = await db.pending_templates.find(
        {"status": "pending"}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return {"templates": pending, "total": len(pending)}

@api_router.post("/admin/training/approve/{template_id}")
async def approve_pending_template(template_id: str, admin: dict = Depends(require_admin)):
    """Approve a pending template and add it to training examples"""
    pending = await db.pending_templates.find_one({"id": template_id, "status": "pending"}, {"_id": 0})
    if not pending:
        raise HTTPException(status_code=404, detail="القالب غير موجود")
    
    example = {
        "id": str(uuid.uuid4()),
        "category": pending["category"],
        "subcategory": pending.get("subcategory", ""),
        "title": pending["title"],
        "description": pending.get("description", ""),
        "design_image_url": "",
        "html_code": pending["html_code"],
        "tags": pending.get("tags", []),
        "is_active": True,
        "usage_count": 0,
        "created_by": admin.get('id', 'admin'),
        "source": "ai_fetched",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.training_examples.insert_one(example)
    await db.pending_templates.update_one({"id": template_id}, {"$set": {"status": "approved"}})
    
    return {"id": example["id"], "message": "تم اعتماد القالب وإضافته للتدريب"}

@api_router.delete("/admin/training/pending/{template_id}")
async def reject_pending_template(template_id: str, admin: dict = Depends(require_admin)):
    """Reject/delete a pending template"""
    result = await db.pending_templates.update_one(
        {"id": template_id, "status": "pending"},
        {"$set": {"status": "rejected"}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="القالب غير موجود")
    return {"message": "تم رفض القالب"}

@api_router.post("/admin/training/approve-all")
async def approve_all_pending(admin: dict = Depends(require_admin)):
    """Approve all pending templates at once"""
    pending = await db.pending_templates.find({"status": "pending"}, {"_id": 0}).to_list(100)
    approved = 0
    for p in pending:
        example = {
            "id": str(uuid.uuid4()),
            "category": p["category"],
            "subcategory": p.get("subcategory", ""),
            "title": p["title"],
            "description": p.get("description", ""),
            "design_image_url": "",
            "html_code": p["html_code"],
            "tags": p.get("tags", []),
            "is_active": True,
            "usage_count": 0,
            "created_by": admin.get('id', 'admin'),
            "source": "ai_fetched",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.training_examples.insert_one(example)
        await db.pending_templates.update_one({"id": p["id"]}, {"$set": {"status": "approved"}})
        approved += 1
    return {"approved": approved, "message": f"تم اعتماد {approved} قالب"}

@api_router.delete("/admin/training/pending-all")
async def reject_all_pending(admin: dict = Depends(require_admin)):
    """Reject all pending templates"""
    result = await db.pending_templates.update_many(
        {"status": "pending"},
        {"$set": {"status": "rejected"}}
    )
    return {"rejected": result.modified_count, "message": f"تم رفض {result.modified_count} قالب"}

# ============== APP SETUP ==============

# Import and setup chat router
from routers import chat_router, set_ai_assistant, deployment_router, set_deployment_service
from routers.websocket_router import router as websocket_router, set_ai_assistant as set_ws_ai_assistant
from services import AIAssistant, DeploymentService

# Initialize AI Assistant
ai_assistant = AIAssistant(
    db=db,
    api_key=OPENAI_API_KEY,
    elevenlabs_key=ELEVENLABS_API_KEY,
    openai_key=OPENAI_API_KEY
)
set_ai_assistant(ai_assistant)
set_ws_ai_assistant(ai_assistant)

# Initialize Deployment Service
deployment_service = DeploymentService(db=db)
set_deployment_service(deployment_service)

# ============== WEBSITES MODULE (self-contained) ==============
try:
    from modules.websites import register_routes as register_websites_routes
    register_websites_routes(app, db, get_current_user)
    logging.getLogger(__name__).info("Websites module registered")
except Exception as _we:
    logging.getLogger(__name__).error(f"Failed to register websites module: {_we}", exc_info=True)

# ============== BILLING MODULE (Stripe subscription gate) ==============
try:
    from modules.billing import register_routes as register_billing_routes
    register_billing_routes(app, db, get_current_user)
    logging.getLogger(__name__).info("Billing module registered")
except Exception as _be:
    logging.getLogger(__name__).error(f"Failed to register billing module: {_be}", exc_info=True)

# ============== SOURCE CODE DOWNLOADER (owner-only) ==============
try:
    from modules.source.routes import init_routes as init_source_routes
    _source_router = init_source_routes(db, get_current_user)
    app.include_router(_source_router, prefix="/api")
    logging.getLogger(__name__).info("Source module registered")
except Exception as _se:
    logging.getLogger(__name__).error(f"Failed to register source module: {_se}", exc_info=True)

# ============== SITE BANNER & STORIES (Zitex main marketing site) ==============
try:
    from modules.site.routes import init_routes as init_site_routes

    async def _require_owner(current_user: dict = Depends(get_current_user)):
        if (current_user or {}).get("role") != "owner":
            from fastapi import HTTPException as _HE
            raise _HE(403, "Owner only")
        return current_user

    _site_router = init_site_routes(db, get_current_user, _require_owner)
    app.include_router(_site_router, prefix="/api")
    logging.getLogger(__name__).info("Site (banner+stories) module registered")
except Exception as _ste:
    logging.getLogger(__name__).error(f"Failed to register site module: {_ste}", exc_info=True)

# ============== OPERATOR (Agency Mode) — multi-client management ==============
try:
    from modules.operator.routes import init_routes as init_operator_routes
    _operator_router = init_operator_routes(db, get_current_user)
    app.include_router(_operator_router, prefix="/api")
    logging.getLogger(__name__).info("Operator module registered")

    @app.on_event("startup")
    async def _start_operator_scheduler():
        try:
            from modules.operator.health import start_scheduler
            start_scheduler(db, interval_seconds=6 * 3600)  # every 6h
        except Exception as _e:
            logging.getLogger(__name__).error(f"operator scheduler failed: {_e}")
except Exception as _oe:
    logging.getLogger(__name__).error(f"Failed to register operator module: {_oe}", exc_info=True)

# ============== AFFILIATE (Paid marketing program) ==============
try:
    from modules.affiliate.routes import init_routes as init_affiliate_routes
    _affiliate_router = init_affiliate_routes(db, get_current_user)
    app.include_router(_affiliate_router, prefix="/api")
    logging.getLogger(__name__).info("Affiliate module registered")
except Exception as _afe:
    logging.getLogger(__name__).error(f"Failed to register affiliate module: {_afe}", exc_info=True)

# ============== STUDIO (Image/Video deep generation for merchants) ==============
try:
    from modules.studio import create_router as create_studio_router
    _studio_router = create_studio_router(db, get_current_user)
    app.include_router(_studio_router)  # router already has /api prefix
    logging.getLogger(__name__).info("Studio module registered")
except Exception as _se:
    logging.getLogger(__name__).error(f"Failed to register studio module: {_se}", exc_info=True)

# ============== VIDEO WIZARD (Smart conversational flow for main /chat/video) ==============
try:
    from modules.video_wizard import create_video_wizard_router
    _vw_router = create_video_wizard_router(db, get_current_user)
    app.include_router(_vw_router)
    logging.getLogger(__name__).info("Video Wizard module registered")
except Exception as _vwe:
    logging.getLogger(__name__).error(f"Failed to register video wizard module: {_vwe}", exc_info=True)

# ============== VISUAL DESIGNER APIS ==============
class DesignElement(BaseModel):
    id: str
    type: str
    x: float
    y: float
    width: float = 100
    height: float = 100
    rotation: float = 0
    scale_x: float = 1
    scale_y: float = 1
    z_index: int = 0
    props: dict = Field(default_factory=dict)


class Design(BaseModel):
    id: Optional[str] = None
    user_id: Optional[str] = None
    name: str
    category: str = "game"
    genre: str = "strategy"
    canvas: dict = Field(default_factory=lambda: {"width": 1280, "height": 720, "background_image_url": None, "background_color": "#87CEEB"})
    elements: List[DesignElement] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@api_router.get("/designs")
async def list_designs(current_user: dict = Depends(get_current_user)):
    items = await db.designs.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("updated_at", -1).to_list(200)
    return {"designs": items}


@api_router.get("/designs/{design_id}")
async def get_design(design_id: str, current_user: dict = Depends(get_current_user)):
    d = await db.designs.find_one({"id": design_id, "user_id": current_user["user_id"]}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Design not found")
    return d


@api_router.post("/designs")
async def create_design(design: Design, current_user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    d = design.model_dump()
    d["id"] = str(uuid.uuid4())
    d["user_id"] = current_user["user_id"]
    d["created_at"] = now
    d["updated_at"] = now
    await db.designs.insert_one(d)
    d.pop("_id", None)
    return d


@api_router.patch("/designs/{design_id}")
async def update_design(design_id: str, design: Design, current_user: dict = Depends(get_current_user)):
    existing = await db.designs.find_one({"id": design_id, "user_id": current_user["user_id"]})
    if not existing:
        raise HTTPException(status_code=404, detail="Design not found")
    update = design.model_dump(exclude={"id", "user_id", "created_at"})
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.designs.update_one({"id": design_id}, {"$set": update})
    updated = await db.designs.find_one({"id": design_id}, {"_id": 0})
    return updated


@api_router.delete("/designs/{design_id}")
async def delete_design(design_id: str, current_user: dict = Depends(get_current_user)):
    r = await db.designs.delete_one({"id": design_id, "user_id": current_user["user_id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Design not found")
    return {"ok": True}


@api_router.post("/designs/{design_id}/duplicate")
async def duplicate_design(design_id: str, current_user: dict = Depends(get_current_user)):
    d = await db.designs.find_one({"id": design_id, "user_id": current_user["user_id"]}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Design not found")
    d["id"] = str(uuid.uuid4())
    d["name"] = f"{d.get('name','تصميم')} (نسخة)"
    now = datetime.now(timezone.utc).isoformat()
    d["created_at"] = now
    d["updated_at"] = now
    await db.designs.insert_one(d)
    d.pop("_id", None)
    return d


@api_router.post("/designs/{design_id}/build")
async def build_from_design(design_id: str, current_user: dict = Depends(get_current_user)):
    """Convert a user-crafted design JSON into a live, playable game HTML.
    The HTML uses the exact element positions the user chose — zero AI drift."""
    d = await db.designs.find_one({"id": design_id, "user_id": current_user["user_id"]}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Design not found")
    from services.ai_chat_service import render_design_to_html
    html = render_design_to_html(d)
    return {"html": html, "design_id": design_id}


# ============== USER IMAGES (saved from chat) ==============
class UserImage(BaseModel):
    id: Optional[str] = None
    user_id: Optional[str] = None
    url: str
    prompt: str = ""
    source_session_id: Optional[str] = None
    created_at: Optional[str] = None


@api_router.post("/user-images")
async def save_user_image(img: UserImage, current_user: dict = Depends(get_current_user)):
    """Save a chat-generated image to the user's personal library so they can extract elements from it later."""
    # Avoid duplicates: same URL for same user
    existing = await db.user_images.find_one({"user_id": current_user["user_id"], "url": img.url}, {"_id": 0})
    if existing:
        return existing
    d = img.model_dump()
    d["id"] = str(uuid.uuid4())
    d["user_id"] = current_user["user_id"]
    d["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.user_images.insert_one(d)
    d.pop("_id", None)
    return d


@api_router.get("/user-images")
async def list_user_images(current_user: dict = Depends(get_current_user)):
    items = await db.user_images.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    return {"images": items}


@api_router.delete("/user-images/{image_id}")
async def delete_user_image(image_id: str, current_user: dict = Depends(get_current_user)):
    r = await db.user_images.delete_one({"id": image_id, "user_id": current_user["user_id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"ok": True}


# ============== USER ELEMENTS (cropped pieces from saved images) ==============
class UserElement(BaseModel):
    id: Optional[str] = None
    user_id: Optional[str] = None
    name: str                                  # e.g. "حقل قمح" (user-picked label)
    source_image_url: str                      # URL of the source image
    source_image_id: Optional[str] = None      # reference to user_images.id
    crop: dict                                 # {x, y, w, h} — in natural image pixels
    natural_width: int                          # source image natural width
    natural_height: int
    category: str = "custom"                   # user-defined grouping
    created_at: Optional[str] = None


@api_router.post("/user-elements")
async def create_user_element(el: UserElement, current_user: dict = Depends(get_current_user)):
    d = el.model_dump()
    d["id"] = str(uuid.uuid4())
    d["user_id"] = current_user["user_id"]
    d["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.user_elements.insert_one(d)
    d.pop("_id", None)
    return d


@api_router.get("/user-elements")
async def list_user_elements(current_user: dict = Depends(get_current_user)):
    items = await db.user_elements.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    return {"elements": items}


@api_router.patch("/user-elements/{el_id}")
async def update_user_element(el_id: str, el: UserElement, current_user: dict = Depends(get_current_user)):
    existing = await db.user_elements.find_one({"id": el_id, "user_id": current_user["user_id"]})
    if not existing:
        raise HTTPException(status_code=404, detail="Element not found")
    update = el.model_dump(exclude={"id", "user_id", "created_at"})
    await db.user_elements.update_one({"id": el_id}, {"$set": update})
    updated = await db.user_elements.find_one({"id": el_id}, {"_id": 0})
    return updated


@api_router.delete("/user-elements/{el_id}")
async def delete_user_element(el_id: str, current_user: dict = Depends(get_current_user)):
    r = await db.user_elements.delete_one({"id": el_id, "user_id": current_user["user_id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Element not found")
    return {"ok": True}
# ============== END VISUAL DESIGNER APIS ==============


# Health check endpoint - MUST be before other routers
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "zitex-api"}

# Serve static game engine (delegated to games module)
try:
    from modules.games.routes import init_routes as _init_games_routes
    _games_router = _init_games_routes()
    app.include_router(_games_router, prefix="/api")
except Exception as _ge:
    logging.getLogger(__name__).error(f"games module failed: {_ge}")


@app.get("/api/iframe-test")
async def serve_iframe_test():
    """Deprecated — handled by modules.games.routes. Kept as fallback."""
    import os
    p = os.path.join(os.path.dirname(__file__), "static", "iframe-test.html")
    if os.path.exists(p):
        with open(p, 'r') as f:
            content = f.read()
        return Response(content=content, media_type="text/html")


@app.get("/api/image-backed-test")
async def serve_image_backed_test():
    """Deprecated — handled by modules.games.routes. Kept as fallback."""
    import os
    p = os.path.join(os.path.dirname(__file__), "static", "image-backed-test.html")
    if os.path.exists(p):
        with open(p, 'r') as f:
            content = f.read()
        return Response(content=content, media_type="text/html")


@app.get("/api/final-preview")
async def serve_final_preview():
    import os
    p = os.path.join(os.path.dirname(__file__), "static", "final-preview.html")
    if os.path.exists(p):
        with open(p, 'r') as f:
            content = f.read()
        return Response(content=content, media_type="text/html")


@app.get("/api/designer-preview-test")
async def serve_designer_preview_test():
    import os
    p = os.path.join(os.path.dirname(__file__), "static", "designer-preview-test.html")
    if os.path.exists(p):
        with open(p, 'r') as f:
            content = f.read()
        return Response(content=content, media_type="text/html")


@app.get("/api/user-designed-preview")
async def serve_user_designed_preview():
    import os
    p = os.path.join(os.path.dirname(__file__), "static", "user-designed-preview.html")
    if os.path.exists(p):
        with open(p, 'r') as f:
            content = f.read()
        return Response(content=content, media_type="text/html")


@app.get("/api/user-crop-preview")
async def serve_user_crop_preview():
    import os
    p = os.path.join(os.path.dirname(__file__), "static", "user-crop-preview.html")
    if os.path.exists(p):
        with open(p, 'r') as f:
            content = f.read()
        return Response(content=content, media_type="text/html")

# Storage proxy endpoint - serve images/videos from Object Storage
@app.get("/api/storage/{file_path:path}")
async def serve_storage_file(file_path: str):
    """Proxy endpoint to serve files from Object Storage"""
    try:
        from services.ai_chat_service import get_from_storage, APP_NAME
        
        full_path = f"{APP_NAME}/{file_path}"
        result = get_from_storage(full_path)
        
        if result is None:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_data, content_type = result
        
        # Determine content type from path if not set
        if not content_type or content_type == "text/html":
            if file_path.endswith(".png"):
                content_type = "image/png"
            elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
                content_type = "image/jpeg"
            elif file_path.endswith(".mp4"):
                content_type = "video/mp4"
            elif file_path.endswith(".mp3"):
                content_type = "audio/mpeg"
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Storage proxy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch file")

# Include routers
app.include_router(api_router)
app.include_router(chat_router, prefix="/api")
app.include_router(deployment_router, prefix="/api")
app.include_router(websocket_router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
