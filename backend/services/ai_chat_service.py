"""
Zitex AI Chat Service
خدمة الشات الذكي لزيتكس
"""
import os
import re
import uuid
import json
import logging
import asyncio
import base64
import httpx
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check for AI features
AI_FEATURES_ENABLED = True
EMERGENT_LLM_AVAILABLE = False
OPENAI_AVAILABLE = False
ELEVENLABS_AVAILABLE = False

try:
    from emergentintegrations.llm.chat import LlmChat
    from emergentintegrations.llm.chat.models import UserMessage
    EMERGENT_LLM_AVAILABLE = True
    logger.info("Emergent LLM integration available")
except ImportError:
    logger.warning("Emergent LLM not available")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("OpenAI not available")

try:
    from elevenlabs import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    logger.warning("ElevenLabs not available")

# Storage configuration
STORAGE_URL = os.environ.get('STORAGE_URL', 'https://storage.emergentagent.com/api/v1/storage')
APP_NAME = os.environ.get('APP_NAME', 'zitex')
EMERGENT_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Initialize storage key
storage_key = EMERGENT_KEY

def init_storage():
    """Initialize storage with available key"""
    global storage_key
    storage_key = EMERGENT_KEY or os.environ.get('OPENAI_API_KEY', '')
    return bool(storage_key)

def upload_to_storage(path: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
    """Upload data to object storage"""
    if not storage_key:
        logger.warning("No storage key available")
        return False
    
    try:
        import httpx
        headers = {
            "Authorization": f"Bearer {storage_key}",
            "Content-Type": content_type
        }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.put(
                f"{STORAGE_URL}/{path}",
                content=data,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Uploaded to storage: {path}")
                return True
            else:
                logger.error(f"Storage upload failed: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"Storage upload error: {e}")
        return False

def get_from_storage(path: str) -> Optional[Tuple[bytes, str]]:
    """Get data from object storage"""
    if not storage_key:
        return None
    
    try:
        import httpx
        headers = {"Authorization": f"Bearer {storage_key}"}
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{STORAGE_URL}/{path}", headers=headers)
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "application/octet-stream")
                return response.content, content_type
            return None
    except Exception as e:
        logger.error(f"Storage get error: {e}")
        return None


MASTER_SYSTEM_PROMPT = """أنت "زيتكس" (Zitex) - مهندس ذكاء اصطناعي لبناء المشاريع الرقمية والمحتوى الإبداعي.

## 🎯 مهمتك الأساسية:
أنت مستشار محترف تساعد العملاء في إنشاء:
- مواقع ويب احترافية
- تطبيقات موبايل (Flutter, React Native, Swift, Kotlin)
- ألعاب 2D و 3D
- فيديوهات سينمائية ومضحكة وإعلانية (15-60 ثانية)
- صور وشعارات احترافية

## 🔄 أسلوب العمل الاستشاري:
1. **اسأل أولاً** - لا تبدأ مباشرة، افهم احتياجات العميل
2. **قدم خيارات** - استخدم الأزرار التفاعلية دائماً
3. **وضح التكلفة** - أخبر العميل بتكلفة كل خدمة قبل البدء
4. **اطلب الموافقة** - لا تنفذ أي شيء بدون موافقة صريحة

## 📋 صيغة الأزرار التفاعلية:
استخدم هذه الصيغة دائماً لعرض الخيارات:
[BUTTONS]
خيار 1|خيار 2|خيار 3
[/BUTTONS]

مثال:
ما نوع المشروع الذي تريده؟
[BUTTONS]
🌐 موقع ويب|📱 تطبيق موبايل|🎮 لعبة|🎬 فيديو
[/BUTTONS]

## 💰 جدول الأسعار:
- رسالة عادية: 1 نقطة
- موقع ويب: 15 نقطة
- تطبيق ويب/لوحة تحكم: 20 نقطة
- لعبة 2D: 15 نقطة
- لعبة 3D: 25 نقطة
- صورة عادية: 5 نقاط
- شعار/لوغو: 10 نقاط
- تطبيق موبايل (Flutter/React Native): 30 نقطة
- تطبيق موبايل (Swift/Kotlin): 35 نقطة

### أسعار الفيديوهات:
| المدة | سينمائي | مضحك | إعلاني |
|-------|---------|------|--------|
| 15 ثانية | 80 نقطة | 50 نقطة | 100 نقطة |
| 30 ثانية | 150 نقطة | 90 نقطة | 180 نقطة |
| 45 ثانية | 220 نقطة | 130 نقطة | 260 نقطة |
| 60 ثانية | 300 نقطة | 170 نقطة | 350 نقطة |
| مخصص | حسب المدة | حسب المدة | حسب المدة |

- تعليق صوتي: 10 نقاط
- نشر المشروع: 100 نقطة

## ⚠️ قواعد صارمة:

1. **تحقق من الرصيد دائماً** قبل أي إنشاء
2. **أظهر التكلفة الكاملة** قبل البدء
3. **اطلب موافقة صريحة** قبل خصم النقاط
4. **إذا كان الرصيد غير كافٍ:**
   أرسل هذه الرسالة:
   ⚠️ رصيدك الحالي (X نقطة) غير كافٍ.
   المطلوب: X نقطة
   [BUTTONS]
   💰 شحن النقاط|🔙 رجوع
   [/BUTTONS]
5. **لا تولد فيديو أبداً بدون موافقة على السيناريو والتكلفة**

## 🎬 قسم الفيديوهات:

### عند طلب فيديو، اسأل أولاً عن النوع:
[BUTTONS]
🎬 فيديو سينمائي|😂 فيديو مضحك|📺 فيديو إعلاني|✏️ نوع آخر
[/BUTTONS]

### ثم اسأل عن المدة:
[BUTTONS]
⏱️ 15 ثانية|⏱️ 30 ثانية|⏱️ 45 ثانية|⏱️ 60 ثانية (دقيقة)|✏️ مدة مخصصة
[/BUTTONS]

### خطوات إنشاء الفيديو:
1. اسأل عن نوع الفيديو
2. اسأل عن المدة المطلوبة
3. اسأل عن الفكرة أو السيناريو
4. اقترح سيناريو مفصل للمشاهد
5. اسأل إذا يريد تعليق صوتي
6. أظهر التكلفة الإجمالية
7. اطلب الموافقة قبل البدء
8. عند الموافقة، استخدم أمر توليد الفيديو

### أمر توليد الفيديو:
[VIDEO_GENERATE]
type: cinematic/funny/advertising
duration: 15/30/45/60
prompt: وصف تفصيلي للمشهد بالإنجليزية
voice_text: نص التعليق الصوتي (اختياري)
voice: alloy/echo/fable/onyx/nova/shimmer
size: 1920x1080
[/VIDEO_GENERATE]

## 🎨 الأصوات المتاحة للتعليق الصوتي:
- alloy (أنثوي محايد) - مناسب للإعلانات العامة
- echo (ذكوري عميق) - مناسب للإعلانات الفاخرة
- fable (أنثوي دافئ) - مناسب للمنتجات العائلية
- onyx (ذكوري قوي) - مناسب للإعلانات الرياضية والسيارات
- nova (أنثوي نشط) - مناسب للمنتجات الشبابية
- shimmer (أنثوي ناعم) - مناسب لمنتجات التجميل

## 🎮 مكتبات الألعاب:
- Phaser 3, Three.js, Babylon.js, PixiJS, Matter.js, Howler.js, GSAP

## 📱 قسم تطبيقات الموبايل:

### عند طلب تطبيق موبايل، اسأل أولاً:
[BUTTONS]
📱 iOS (iPhone/iPad)|🤖 Android|📲 كلاهما (iOS + Android)
[/BUTTONS]

### 🔧 أنواع البرمجة المتاحة:

**1. Flutter (موصى به للمنصتين):**
- كود واحد يعمل على iOS و Android
- أداء ممتاز وواجهة جميلة
- اللغة: Dart
- التكلفة: 30 نقطة

**2. React Native:**
- JavaScript/TypeScript
- مناسب لمطوري الويب
- مجتمع كبير ومكتبات متنوعة
- التكلفة: 30 نقطة

**3. Swift (Native iOS فقط):**
- أفضل أداء لـ iPhone/iPad
- تصميم Apple الأصلي
- التكلفة: 35 نقطة

**4. Kotlin (Native Android فقط):**
- أفضل أداء لأجهزة Android
- تصميم Material Design
- التكلفة: 35 نقطة

### 📋 خطوات إنشاء التطبيق:

**الخطوة 1 - اختيار المنصة:**
ما المنصة المستهدفة لتطبيقك؟
[BUTTONS]
📱 iOS فقط|🤖 Android فقط|📲 كلاهما
[/BUTTONS]

**الخطوة 2 - اختيار نوع البرمجة:**
ما نوع البرمجة المفضل؟
[BUTTONS]
🎯 Flutter (موصى به)|⚛️ React Native|🍎 Swift (iOS فقط)|📝 Kotlin (Android فقط)
[/BUTTONS]

**الخطوة 3 - نوع التطبيق:**
ما نوع التطبيق الذي تريده؟
[BUTTONS]
🛒 تطبيق تجارة|📋 تطبيق خدمات|💬 تطبيق تواصل|📰 تطبيق أخبار/محتوى|🎮 لعبة موبايل|✏️ نوع آخر
[/BUTTONS]

**الخطوة 4 - جمع المتطلبات:**
📋 أخبرني عن تطبيقك:
1. ما اسم التطبيق؟
2. ما وظيفته الرئيسية؟
3. ما الشاشات/الصفحات المطلوبة؟
4. هل يحتاج تسجيل دخول؟
5. ما الألوان والهوية البصرية؟
6. هل تحتاج قاعدة بيانات/Backend؟

**الخطوة 5 - عرض التكلفة والبدء:**
💰 ملخص المشروع:
━━━━━━━━━━━━━━━━━━━━━━
📱 التطبيق: [اسم التطبيق]
🔧 التقنية: [Flutter/React Native/Swift/Kotlin]
📲 المنصة: [iOS/Android/كلاهما]
━━━━━━━━━━━━━━━━━━━━━━
التكلفة: [X] نقطة
رصيدك: [X] نقطة

[BUTTONS]
✅ ابدأ البناء|📝 تعديل المتطلبات|❌ إلغاء
[/BUTTONS]

اجعل كل تفاعل احترافياً ومنظماً!
"""

WELCOME_MESSAGE = """## 👋 مرحباً بك في زيتكس!

أنا مهندسك الذكي لبناء المشاريع الرقمية. 
سأبني لك المشروع خطوة بخطوة وتشاهده مباشرة في المعاينة!

ماذا تريد أن نبني اليوم؟

[BUTTONS]
🌐 موقع ويب|📱 تطبيق موبايل|🎮 لعبة|🎬 فيديو|🖼️ صورة/لوغو|✏️ فكرة أخرى
[/BUTTONS]"""


ZITEX_BADGE = '''<!-- Zitex Badge -->
<div id="zitex-badge" style="position:fixed;bottom:20px;right:20px;background:linear-gradient(135deg,#1a1a2e,#16213e);padding:10px 20px;border-radius:25px;box-shadow:0 4px 15px rgba(0,0,0,0.3);z-index:9999;display:flex;align-items:center;gap:10px;cursor:pointer;border:1px solid rgba(255,215,0,0.3);" onclick="window.open('https://zitex.vercel.app','_blank')">
    <div style="width:30px;height:30px;background:linear-gradient(135deg,#ffd700,#ffaa00);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;color:#000;font-size:16px;">Z</div>
    <span style="color:#ffd700;font-size:14px;font-weight:500;">Powered by Zitex</span>
</div>'''


SERVICE_COSTS = {
    "message": 1,
    "website": 15,
    "webapp": 20,
    "pwa": 20,
    "game": 15,
    "game_3d": 25,
    "image": 5,
    "image_logo": 10,
    "image_preview": 5,
    "image_multiple": 15,
    # تطبيقات الموبايل
    "mobile_flutter": 30,
    "mobile_react_native": 30,
    "mobile_swift": 35,
    "mobile_kotlin": 35,
    "mobile_ui_advanced": 15,
    "mobile_backend": 20,
    # فيديوهات سينمائية (المدد الجديدة)
    "video_cinematic_15": 80,
    "video_cinematic_30": 150,
    "video_cinematic_45": 220,
    "video_cinematic_60": 300,
    # فيديوهات مضحكة
    "video_funny_15": 50,
    "video_funny_30": 90,
    "video_funny_45": 130,
    "video_funny_60": 170,
    # فيديوهات إعلانية
    "video_advertising_15": 100,
    "video_advertising_30": 180,
    "video_advertising_45": 260,
    "video_advertising_60": 350,
    # إضافات
    "voice_over": 10,
    "voice_preview": 5,
    "modification": 5,
    "export": 50,
    "deploy": 100,
    "save_template": 10,
    "use_template": 5
}

# ============== Video Categories ==============
VIDEO_CATEGORIES = {
    "short": {
        "name": "مقاطع قصيرة",
        "name_en": "Short Clips",
        "description": "ريلز، تيك توك، ستوري",
        "durations": [15, 30],
        "sizes": ["1080x1920", "1024x1792"],
        "cost_base": 50
    },
    "cinematic": {
        "name": "فيديوهات سينمائية",
        "name_en": "Cinematic Videos",
        "description": "أفلام قصيرة، مشاهد درامية",
        "durations": [15, 30, 45, 60],
        "sizes": ["1920x1080", "1792x1024"],
        "cost_base": 80
    },
    "advertising": {
        "name": "فيديوهات إعلانية",
        "name_en": "Advertising Videos",
        "description": "حملات إعلانية، ترويج منتجات",
        "durations": [15, 30, 45, 60],
        "sizes": ["1920x1080", "1080x1080", "1080x1920"],
        "cost_base": 100
    },
    "funny": {
        "name": "فيديوهات مضحكة",
        "name_en": "Funny Videos",
        "description": "محتوى ترفيهي وكوميدي",
        "durations": [15, 30, 45, 60],
        "sizes": ["1920x1080", "1080x1920"],
        "cost_base": 50
    }
}

# ============== Image Categories ==============
IMAGE_CATEGORIES = {
    "logo": {
        "name": "تصميم شعار",
        "name_en": "Logo Design",
        "description": "شعارات احترافية للشركات",
        "sizes": ["1024x1024"],
        "styles": ["minimal", "modern", "vintage", "3d", "mascot"],
        "cost": 10
    },
    "banner": {
        "name": "بانر إعلاني",
        "name_en": "Banner",
        "description": "بانرات للمواقع والسوشيال ميديا",
        "sizes": ["1792x1024", "1024x1792"],
        "cost": 8
    },
    "product": {
        "name": "صور منتجات",
        "name_en": "Product Images",
        "description": "صور احترافية للمنتجات",
        "sizes": ["1024x1024"],
        "cost": 5
    },
    "social": {
        "name": "سوشيال ميديا",
        "name_en": "Social Media",
        "description": "بوستات انستقرام، فيسبوك",
        "sizes": ["1024x1024", "1024x1792"],
        "cost": 5
    },
    "multiple": {
        "name": "صور متعددة",
        "name_en": "Multiple Images",
        "description": "مجموعة صور متناسقة",
        "count_options": [3, 5, 10],
        "cost_per_image": 4
    }
}


# ============== Templates System ==============
DEFAULT_TEMPLATES = [
    {
        "id": "landing-dark",
        "name": "صفحة هبوط داكنة",
        "category": "landing",
        "preview_image": "/api/templates/preview/landing-dark",
        "description": "صفحة هبوط احترافية بتصميم داكن وأنيق",
        "is_premium": False,
        "cost": 0,
        "tags": ["landing", "dark", "professional"]
    },
    {
        "id": "ecommerce-gold",
        "name": "متجر ذهبي",
        "category": "ecommerce",
        "preview_image": "/api/templates/preview/ecommerce-gold",
        "description": "متجر إلكتروني بتصميم ذهبي فاخر",
        "is_premium": True,
        "cost": 20,
        "tags": ["shop", "gold", "luxury"]
    },
    {
        "id": "portfolio-minimal",
        "name": "معرض أعمال بسيط",
        "category": "portfolio",
        "preview_image": "/api/templates/preview/portfolio-minimal",
        "description": "معرض أعمال بتصميم بسيط وأنيق",
        "is_premium": False,
        "cost": 0,
        "tags": ["portfolio", "minimal", "clean"]
    },
    {
        "id": "dashboard-pro",
        "name": "لوحة تحكم احترافية",
        "category": "dashboard",
        "preview_image": "/api/templates/preview/dashboard-pro",
        "description": "لوحة تحكم متكاملة مع رسوم بيانية",
        "is_premium": True,
        "cost": 25,
        "tags": ["dashboard", "admin", "charts"]
    },
    {
        "id": "game-2d-platformer",
        "name": "لعبة منصات 2D",
        "category": "game",
        "preview_image": "/api/templates/preview/game-2d-platformer",
        "description": "لعبة منصات بتقنية Phaser.js",
        "is_premium": True,
        "cost": 30,
        "tags": ["game", "2d", "platformer", "phaser"]
    },
    {
        "id": "game-3d-racing",
        "name": "لعبة سباق 3D",
        "category": "game",
        "preview_image": "/api/templates/preview/game-3d-racing",
        "description": "لعبة سباق سيارات بتقنية Three.js",
        "is_premium": True,
        "cost": 35,
        "tags": ["game", "3d", "racing", "threejs"]
    },
    {
        "id": "mobile-flutter-ecommerce",
        "name": "تطبيق متجر Flutter",
        "category": "mobile",
        "preview_image": "/api/templates/preview/mobile-flutter-ecommerce",
        "description": "تطبيق متجر إلكتروني بتقنية Flutter",
        "is_premium": True,
        "cost": 30,
        "tags": ["mobile", "flutter", "ecommerce", "ios", "android"],
        "tech": "flutter"
    },
    {
        "id": "mobile-react-native-social",
        "name": "تطبيق تواصل React Native",
        "category": "mobile",
        "preview_image": "/api/templates/preview/mobile-react-native-social",
        "description": "تطبيق تواصل اجتماعي بتقنية React Native",
        "is_premium": True,
        "cost": 30,
        "tags": ["mobile", "react-native", "social", "ios", "android"],
        "tech": "react_native"
    }
]

# ============== Mobile App Frameworks ==============
MOBILE_FRAMEWORKS = {
    "flutter": {
        "name": "Flutter",
        "language": "Dart",
        "platforms": ["ios", "android"],
        "description": "كود واحد للمنصتين - أداء ممتاز",
        "cost": 30
    },
    "react_native": {
        "name": "React Native",
        "language": "JavaScript/TypeScript",
        "platforms": ["ios", "android"],
        "description": "مناسب لمطوري الويب - مجتمع كبير",
        "cost": 30
    },
    "swift": {
        "name": "Swift (SwiftUI)",
        "language": "Swift",
        "platforms": ["ios"],
        "description": "أفضل أداء لـ iOS - تصميم Apple الأصلي",
        "cost": 35
    },
    "kotlin": {
        "name": "Kotlin",
        "language": "Kotlin",
        "platforms": ["android"],
        "description": "أفضل أداء لـ Android - Material Design",
        "cost": 35
    }
}

# ============== Game Libraries & CDN Links ==============
GAME_LIBRARIES = {
    "phaser": {
        "name": "Phaser 3",
        "cdn": "https://cdn.jsdelivr.net/npm/phaser@3.70.0/dist/phaser.min.js",
        "description": "محرك ألعاب 2D قوي وسهل الاستخدام",
        "use_cases": ["platformer", "puzzle", "arcade", "rpg_2d"]
    },
    "threejs": {
        "name": "Three.js",
        "cdn": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js",
        "description": "مكتبة 3D متكاملة للويب",
        "use_cases": ["3d_games", "racing", "simulation", "fps"]
    },
    "babylonjs": {
        "name": "Babylon.js",
        "cdn": "https://cdn.babylonjs.com/babylon.js",
        "description": "محرك ألعاب 3D احترافي",
        "use_cases": ["3d_games", "rpg", "mmorpg", "simulation"]
    },
    "pixijs": {
        "name": "PixiJS",
        "cdn": "https://cdn.jsdelivr.net/npm/pixi.js@7.3.2/dist/pixi.min.js",
        "description": "مكتبة 2D سريعة للرسوميات",
        "use_cases": ["2d_games", "cards", "slot", "arcade"]
    },
    "matter": {
        "name": "Matter.js",
        "cdn": "https://cdn.jsdelivr.net/npm/matter-js@0.19.0/build/matter.min.js",
        "description": "محرك فيزياء 2D",
        "use_cases": ["physics", "puzzle", "simulation"]
    },
    "howler": {
        "name": "Howler.js",
        "cdn": "https://cdn.jsdelivr.net/npm/howler@2.2.4/dist/howler.min.js",
        "description": "مكتبة صوتيات للألعاب",
        "use_cases": ["audio", "sound_effects", "music"]
    },
    "gsap": {
        "name": "GSAP",
        "cdn": "https://cdn.jsdelivr.net/npm/gsap@3.12.4/dist/gsap.min.js",
        "description": "مكتبة تحريك احترافية",
        "use_cases": ["animation", "ui", "transitions"]
    }
}


def detect_request_type(message: str, session_type: str = "general") -> str:
    message_lower = message.lower()
    
    # Mobile app detection (priority)
    if any(word in message for word in ["تطبيق موبايل", "تطبيق جوال", "تطبيق هاتف", "📱 تطبيق"]):
        return "mobile"
    if any(word in message_lower for word in ["flutter", "react native", "swift", "kotlin"]):
        return "mobile"
    if any(word in message for word in ["ios", "iphone", "ipad", "أيفون", "آيفون"]):
        return "mobile"
    if any(word in message for word in ["android", "أندرويد", "اندرويد"]):
        return "mobile"
    
    # Direct button selections
    if "موقع ويب" in message or "🌐 موقع" in message:
        return "website"
    elif "تطبيق ويب" in message or "لوحة" in message_lower:
        return "webapp"
    elif "لعبة" in message_lower or "game" in message_lower or "🎮" in message:
        return "game"
    elif "صورة" in message_lower or "شعار" in message_lower or "لوغو" in message_lower or "🖼️" in message:
        return "image"
    elif "فيديو" in message_lower or "🎬" in message:
        return "video"
    
    # 3D detection
    if "3d" in message_lower or "ثلاثي" in message_lower or "سباق" in message_lower:
        return "game_3d"
    
    if session_type and session_type != "general":
        return session_type
    
    return "general"


def inject_zitex_badge(html_code: str) -> str:
    if '</body>' in html_code:
        return html_code.replace('</body>', f'{ZITEX_BADGE}\n</body>')
    elif '</html>' in html_code:
        return html_code.replace('</html>', f'{ZITEX_BADGE}\n</html>')
    return html_code + '\n' + ZITEX_BADGE


class AIAssistant:
    def __init__(self, db: AsyncIOMotorDatabase, api_key: str = None, elevenlabs_key: str = None, openai_key: str = None):
        self.db = db
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.elevenlabs_key = elevenlabs_key
        self.openai_key = openai_key or self.api_key
        self.emergent_key = os.environ.get('EMERGENT_LLM_KEY')
        
        self.eleven_client = None
        if ELEVENLABS_AVAILABLE and elevenlabs_key:
            try:
                self.eleven_client = ElevenLabs(api_key=elevenlabs_key)
            except Exception:
                pass
        
        self.openai_client = None
        if OPENAI_AVAILABLE and self.openai_key:
            try:
                self.openai_client = openai.OpenAI(api_key=self.openai_key)
            except Exception:
                pass
        
        # Check if we have any LLM capability
        self.llm_available = bool(self.emergent_key) or bool(self.openai_client)
    
    async def create_session(self, user_id: str, session_type: str = "general", title: str = None) -> Dict:
        welcome_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": WELCOME_MESSAGE,
            "message_type": "text",
            "attachments": [],
            "metadata": {"is_welcome": True, "has_buttons": True},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        session = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title or "محادثة جديدة",
            "session_type": session_type,
            "messages": [welcome_msg],
            "project_data": {},
            "generated_code": None,
            "conversation_stage": "type_selection",
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
    
    async def get_user_credits(self, user_id: str) -> int:
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
        return user.get("credits", 0) if user else 0
    
    async def deduct_credits(self, user_id: str, amount: int, reason: str) -> bool:
        result = await self.db.users.update_one(
            {"id": user_id, "credits": {"$gte": amount}},
            {
                "$inc": {"credits": -amount},
                "$push": {
                    "credit_history": {
                        "amount": -amount,
                        "reason": reason,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
            }
        )
        return result.modified_count > 0

    async def process_message(self, session_id: str, user_id: str, message: str, settings: Dict[str, Any] = None) -> Dict:
        settings = settings or {}
        
        session = await self.get_session(session_id, user_id)
        if not session:
            raise ValueError("Session not found")
        
        credits = await self.get_user_credits(user_id)
        
        user_msg = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": message,
            "message_type": "text",
            "attachments": [],
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        request_type = detect_request_type(message, session.get("session_type", "general"))
        
        ai_response = ""
        attachments = []
        credits_used = 0
        has_buttons = False
        
        if not AI_FEATURES_ENABLED or not self.llm_available:
            ai_response = "⚠️ خدمة غير متاحة حالياً. يرجى إضافة مفتاح API."
        else:
            required_credits = SERVICE_COSTS.get(request_type, 1)
            
            if credits < required_credits:
                ai_response = f"""## ⚠️ رصيد غير كافٍ

رصيدك: **{credits} نقطة**
المطلوب: **{required_credits} نقطة**

[BUTTONS]
💰 شحن الرصيد
[/BUTTONS]"""
                has_buttons = True
            else:
                try:
                    # Generate GPT response first
                    ai_response, credits_used, has_buttons = await self._generate_with_gpt(session, message, request_type, credits, settings)
                    
                    # Process special commands in AI response
                    ai_response, extra_attachments, extra_credits = await self._process_ai_commands(
                        ai_response, user_id, session_id, credits - credits_used
                    )
                    attachments.extend(extra_attachments)
                    credits_used += extra_credits
                    
                    if credits_used > 0:
                        await self.deduct_credits(user_id, credits_used, f"{request_type}")
                        
                except Exception as e:
                    logger.error(f"Error: {e}")
                    ai_response = "❌ حدث خطأ، حاول مرة أخرى"
        
        # Check if response has buttons
        if "[BUTTONS]" in ai_response:
            has_buttons = True
        
        assistant_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": ai_response.strip(),
            "message_type": "text",
            "attachments": attachments,
            "metadata": {
                "request_type": request_type,
                "credits_used": credits_used,
                "credits_remaining": credits - credits_used,
                "has_buttons": has_buttons
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        update_data = {
            "$push": {"messages": {"$each": [user_msg, assistant_msg]}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
        
        # Update session type
        if request_type != "general":
            update_data["$set"]["session_type"] = request_type
        
        # Extract code from [CODE_BLOCK] or regular code blocks
        code = None
        
        # First try CODE_BLOCK format
        code_block_match = re.search(r'\[CODE_BLOCK\]\s*```(?:html|javascript|js)?\n?([\s\S]*?)```\s*\[/CODE_BLOCK\]', ai_response)
        if code_block_match:
            code = code_block_match.group(1).strip()
        else:
            # Fall back to regular code block
            code_match = re.search(r'```(?:html|javascript|js)?\n?([\s\S]*?)```', ai_response)
            if code_match:
                code = code_match.group(1).strip()
        
        if code:
            code_with_badge = inject_zitex_badge(code)
            update_data["$set"]["generated_code"] = code_with_badge
            # Store code in metadata for frontend to use
            assistant_msg["metadata"]["generated_code"] = code_with_badge
            assistant_msg["metadata"]["has_preview"] = True
        
        await self.db.chat_sessions.update_one({"id": session_id}, update_data)
        
        # Update title
        non_welcome = [m for m in session.get("messages", []) if not m.get("metadata", {}).get("is_welcome")]
        if len(non_welcome) == 0:
            title = self._generate_title(message, request_type)
            await self.db.chat_sessions.update_one({"id": session_id}, {"$set": {"title": title}})
        
        return {
            "session_id": session_id,
            "user_message": user_msg,
            "assistant_message": assistant_msg,
            "credits_used": credits_used
        }
    
    async def _generate_image(self, user_id: str, session_id: str, prompt: str, credits: int) -> Tuple[str, List[Dict], int]:
        try:
            image_response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=f"High quality: {prompt}",
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = image_response.data[0].url
            
            asset = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "session_id": session_id,
                "asset_type": "image",
                "url": image_url,
                "prompt": prompt,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await self.db.generated_assets.insert_one(asset)
            
            response = f"""## ✅ تم إنشاء الصورة!

> التكلفة: 5 نقاط | المتبقي: {credits - 5} نقطة

[BUTTONS]
🎨 صورة جديدة|✏️ تعديل|💾 حفظ
[/BUTTONS]"""
            
            return response, [{"type": "image", "url": image_url, "prompt": prompt}], 5
            
        except Exception as e:
            logger.error(f"Image error: {e}")
            return "❌ خطأ في توليد الصورة", [], 0

    async def _process_ai_commands(self, ai_response: str, user_id: str, session_id: str, available_credits: int) -> Tuple[str, List[Dict], int]:
        """معالجة الأوامر الخاصة في رد الذكاء الاصطناعي"""
        attachments = []
        total_credits = 0
        processed_response = ai_response
        
        # معالجة أمر توليد الفيديو [VIDEO_GENERATE]
        video_match = re.search(
            r'\[VIDEO_GENERATE\]\s*'
            r'type:\s*(\w+)\s*'
            r'duration:\s*(\d+)\s*'
            r'prompt:\s*([^\[]+?)\s*'
            r'(?:voice_text:\s*([^\[]+?)\s*)?'
            r'(?:voice:\s*(\w+)\s*)?'
            r'(?:size:\s*([^\[]+?)\s*)?'
            r'\[/VIDEO_GENERATE\]',
            ai_response, re.IGNORECASE | re.DOTALL
        )
        
        if video_match:
            video_type = video_match.group(1).strip()
            duration = int(video_match.group(2))
            prompt = video_match.group(3).strip()
            voice_text = video_match.group(4).strip() if video_match.group(4) else None
            voice = video_match.group(5).strip() if video_match.group(5) else "onyx"
            size = video_match.group(6).strip() if video_match.group(6) else "1920x1080"
            
            # حساب التكلفة بناءً على المدد الجديدة
            cost_key = f"video_{video_type}_{duration}"
            video_cost = SERVICE_COSTS.get(cost_key, 80)
            voice_cost = SERVICE_COSTS.get("voice_over", 10) if voice_text else 0
            total_video_cost = video_cost + voice_cost
            
            if available_credits >= total_video_cost:
                # توليد الفيديو
                video_result = await self._generate_video(
                    user_id, session_id, prompt, duration, size, video_type
                )
                
                if video_result:
                    attachments.append({
                        "type": "video",
                        "url": video_result["url"],
                        "prompt": prompt,
                        "duration": duration,
                        "video_type": video_type
                    })
                    total_credits += video_cost
                    
                    # توليد التعليق الصوتي إذا مطلوب
                    if voice_text:
                        audio_url = await self.generate_tts(voice_text, "openai", voice)
                        if audio_url:
                            attachments.append({
                                "type": "audio",
                                "url": audio_url,
                                "text": voice_text,
                                "voice": voice
                            })
                            total_credits += voice_cost
                    
                    # تحديث الرد
                    success_msg = f"""
## ✅ تم إنشاء الفيديو بنجاح!

🎬 النوع: {video_type}
⏱️ المدة: {duration} ثانية
💰 التكلفة: {total_video_cost} نقطة

[BUTTONS]
📥 تحميل الفيديو|🎬 فيديو جديد|✏️ تعديل
[/BUTTONS]"""
                    processed_response = re.sub(
                        r'\[VIDEO_GENERATE\][\s\S]*?\[/VIDEO_GENERATE\]',
                        success_msg,
                        processed_response
                    )
                else:
                    processed_response = re.sub(
                        r'\[VIDEO_GENERATE\][\s\S]*?\[/VIDEO_GENERATE\]',
                        "❌ فشل إنشاء الفيديو. حاول مرة أخرى.",
                        processed_response
                    )
            else:
                processed_response = re.sub(
                    r'\[VIDEO_GENERATE\][\s\S]*?\[/VIDEO_GENERATE\]',
                    f"⚠️ رصيد غير كافٍ! المطلوب: {total_video_cost} نقطة، المتوفر: {available_credits} نقطة",
                    processed_response
                )
        
        # معالجة أمر معاينة الصوت [VOICE_PREVIEW]
        voice_preview_match = re.search(
            r'\[VOICE_PREVIEW\]\s*'
            r'text:\s*([^\[]+?)\s*'
            r'(?:voice:\s*(\w+)\s*)?'
            r'\[/VOICE_PREVIEW\]',
            ai_response, re.IGNORECASE | re.DOTALL
        )
        
        if voice_preview_match:
            text = voice_preview_match.group(1).strip()
            voice = voice_preview_match.group(2).strip() if voice_preview_match.group(2) else "onyx"
            
            voice_cost = SERVICE_COSTS.get("voice_preview", 5)
            if available_credits >= voice_cost:
                audio_url = await self.generate_tts(text, "openai", voice)
                if audio_url:
                    attachments.append({
                        "type": "audio_preview",
                        "url": audio_url,
                        "text": text,
                        "voice": voice
                    })
                    total_credits += voice_cost
                    
                    processed_response = re.sub(
                        r'\[VOICE_PREVIEW\][\s\S]*?\[/VOICE_PREVIEW\]',
                        f"""
🔊 **معاينة التعليق الصوتي**
الصوت: {voice}

[BUTTONS]
✅ أعجبني الصوت|🔄 صوت آخر|✏️ تعديل النص
[/BUTTONS]""",
                        processed_response
                    )
        
        # معالجة أمر معاينة الصور [IMAGE_PREVIEW]
        image_preview_match = re.search(
            r'\[IMAGE_PREVIEW\]\s*([\s\S]*?)\[/IMAGE_PREVIEW\]',
            ai_response, re.IGNORECASE
        )
        
        if image_preview_match:
            scenes_text = image_preview_match.group(1).strip()
            scenes = re.findall(r'scene_\d+:\s*(.+)', scenes_text)
            
            preview_cost = SERVICE_COSTS.get("image_preview", 5) * len(scenes)
            if available_credits >= preview_cost and scenes:
                preview_images = []
                for i, scene_prompt in enumerate(scenes):
                    image_url = await self._generate_single_image(scene_prompt.strip())
                    if image_url:
                        preview_images.append({
                            "type": "image_preview",
                            "url": image_url,
                            "scene": i + 1,
                            "prompt": scene_prompt.strip()
                        })
                
                if preview_images:
                    attachments.extend(preview_images)
                    total_credits += SERVICE_COSTS.get("image_preview", 5) * len(preview_images)
                    
                    processed_response = re.sub(
                        r'\[IMAGE_PREVIEW\][\s\S]*?\[/IMAGE_PREVIEW\]',
                        f"""
🖼️ **صور تجريبية للمشاهد** ({len(preview_images)} صور)

[BUTTONS]
✅ موافق على المشاهد|✏️ تعديل المشاهد|🔄 صور جديدة
[/BUTTONS]""",
                        processed_response
                    )
        
        # معالجة أمر توليد صورة [IMAGE_GENERATE]
        image_gen_match = re.search(
            r'\[IMAGE_GENERATE\]\s*'
            r'type:\s*(\w+)\s*'
            r'prompt:\s*([^\[]+?)\s*'
            r'\[/IMAGE_GENERATE\]',
            ai_response, re.IGNORECASE | re.DOTALL
        )
        
        if image_gen_match:
            image_type = image_gen_match.group(1).strip()
            prompt = image_gen_match.group(2).strip()
            
            cost_key = f"image_{image_type}" if image_type in ["logo", "product"] else "image"
            image_cost = SERVICE_COSTS.get(cost_key, 5)
            
            if available_credits >= image_cost:
                image_url = await self._generate_single_image(prompt)
                if image_url:
                    attachments.append({
                        "type": "image",
                        "url": image_url,
                        "image_type": image_type,
                        "prompt": prompt
                    })
                    total_credits += image_cost
                    
                    processed_response = re.sub(
                        r'\[IMAGE_GENERATE\][\s\S]*?\[/IMAGE_GENERATE\]',
                        f"""
## ✅ تم إنشاء الصورة!

💰 التكلفة: {image_cost} نقطة

[BUTTONS]
🎨 صورة جديدة|✏️ تعديل|💾 حفظ
[/BUTTONS]""",
                        processed_response
                    )
        
        return processed_response, attachments, total_credits

    async def _generate_video(self, user_id: str, session_id: str, prompt: str, duration: int, size: str, video_type: str) -> Optional[Dict]:
        """توليد فيديو باستخدام Sora 2"""
        try:
            from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
            
            video_gen = OpenAIVideoGeneration(api_key=self.emergent_key)
            
            # المدد المدعومة الجديدة (15, 30, 45, 60 ثانية)
            valid_durations = [15, 30, 45, 60]
            if duration not in valid_durations:
                duration = min(valid_durations, key=lambda x: abs(x - duration))
            
            # Ensure size is valid
            valid_sizes = ["1920x1080", "1080x1920", "1080x1080", "1792x1024", "1024x1792"]
            if size not in valid_sizes:
                size = "1920x1080"
            
            logger.info(f"Generating video: type={video_type}, duration={duration}, size={size}")
            
            video_bytes = video_gen.text_to_video(
                prompt=prompt,
                model="sora-2",
                size=size,
                duration=duration,
                max_wait_time=900  # 15 دقيقة للفيديوهات الطويلة
            )
            
            if video_bytes:
                # رفع الفيديو إلى Object Storage
                video_id = str(uuid.uuid4())
                video_path = f"{APP_NAME}/videos/{user_id}/{video_id}.mp4"
                
                upload_result = upload_to_storage(video_path, video_bytes, "video/mp4")
                
                if upload_result:
                    video_url = f"{STORAGE_URL.replace('/api/v1/storage', '')}/videos/{user_id}/{video_id}.mp4"
                    
                    # حفظ في قاعدة البيانات
                    asset = {
                        "id": video_id,
                        "user_id": user_id,
                        "session_id": session_id,
                        "asset_type": "video",
                        "video_type": video_type,
                        "url": video_url,
                        "prompt": prompt,
                        "duration": duration,
                        "size": size,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    await self.db.generated_assets.insert_one(asset)
                    
                    return {"url": video_url, "id": video_id}
            
            return None
            
        except Exception as e:
            logger.error(f"Video generation error: {e}")
            return None
    
    async def _generate_single_image(self, prompt: str) -> Optional[str]:
        """توليد صورة واحدة باستخدام GPT Image"""
        try:
            from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
            import base64
            
            image_gen = OpenAIImageGeneration(api_key=self.emergent_key)
            
            images = await image_gen.generate_images(
                prompt=prompt,
                model="gpt-image-1",
                number_of_images=1
            )
            
            if images and len(images) > 0:
                # رفع الصورة إلى Object Storage
                image_id = str(uuid.uuid4())
                image_path = f"{APP_NAME}/images/{image_id}.png"
                
                upload_result = upload_to_storage(image_path, images[0], "image/png")
                
                if upload_result:
                    image_url = f"{STORAGE_URL.replace('/api/v1/storage', '')}/images/{image_id}.png"
                    return image_url
                else:
                    # إذا فشل الرفع، إرجاع base64
                    image_base64 = base64.b64encode(images[0]).decode('utf-8')
                    return f"data:image/png;base64,{image_base64}"
            
            return None
            
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return None
    
    async def _generate_with_gpt(self, session: Dict, message: str, request_type: str, credits: int, settings: Dict) -> Tuple[str, int, bool]:
        # Build context about the project
        project_data = session.get("project_data", {})
        stage = session.get("conversation_stage", "initial")
        
        context = f"""
رصيد العميل: {credits} نقطة
مرحلة المحادثة: {stage}
بيانات المشروع حتى الآن: {project_data}
"""
        
        system_prompt = MASTER_SYSTEM_PROMPT + context
        
        # Build conversation history
        conversation_history = ""
        for msg in session.get("messages", [])[-12:]:
            role_label = "المستخدم" if msg["role"] == "user" else "زيتكس"
            conversation_history += f"\n{role_label}: {msg['content']}\n"
        
        full_prompt = f"{conversation_history}\nالمستخدم: {message}"
        
        try:
            # Try Emergent LLM first (preferred)
            if EMERGENT_LLM_AVAILABLE and self.emergent_key:
                chat = LlmChat(
                    api_key=self.emergent_key,
                    session_id=session.get("id", "default"),
                    system_message=system_prompt
                )
                chat.with_model("openai", "gpt-4o")
                
                user_message = UserMessage(text=full_prompt)
                response = await chat.send_message(user_message)
            
            # Fall back to direct OpenAI client
            elif self.openai_client:
                messages = [{"role": "system", "content": system_prompt}]
                for msg in session.get("messages", [])[-12:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                messages.append({"role": "user", "content": message})
                
                completion = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=8000
                )
                response = completion.choices[0].message.content
            else:
                return "⚠️ خدمة الذكاء الاصطناعي غير متاحة. يرجى إضافة مفتاح API.", 0, False
            
            # Determine credits based on content
            credits_used = 1  # Base cost for conversation
            
            # Check if response contains code (in CODE_BLOCK or regular code block)
            has_code = '[CODE_BLOCK]' in response or ('```html' in response and '[CODE_BLOCK]' not in response) or '```javascript' in response
            
            if has_code:
                credits_used = SERVICE_COSTS.get(request_type, 15)
            
            has_buttons = "[BUTTONS]" in response
            
            return response, credits_used, has_buttons
            
        except Exception as e:
            logger.error(f"GPT error: {e}")
            return f"❌ خطأ في المعالجة: {str(e)}", 0, False
    
    def _generate_title(self, message: str, request_type: str) -> str:
        icons = {"image": "🎨", "video": "🎬", "website": "🌐", "game": "🎮", "webapp": "💻", "pwa": "📱", "mobile": "📱"}
        prefix = icons.get(request_type, "💬")
        title = message[:25].strip()
        if len(message) > 25:
            title += "..."
        return f"{prefix} {title}"
    
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
        return await self.db.video_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)

    async def generate_tts(self, text: str, provider: str = "openai", voice: str = "alloy", speed: float = 1.0) -> Optional[str]:
        """توليد صوت من النص باستخدام OpenAI TTS"""
        if not text or len(text.strip()) == 0:
            return None
        
        # Limit text length
        text = text[:4000]
        
        # Remove buttons and code blocks from text
        text = re.sub(r'\[BUTTONS\][\s\S]*?\[/BUTTONS\]', '', text)
        text = re.sub(r'\[CODE_BLOCK\][\s\S]*?\[/CODE_BLOCK\]', '', text)
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = text.strip()
        
        if not text:
            return None
        
        try:
            from emergentintegrations.llm.openai import OpenAITextToSpeech
            
            tts = OpenAITextToSpeech(api_key=self.emergent_key)
            
            # Generate audio as base64
            audio_base64 = await tts.generate_speech_base64(
                text=text,
                model="tts-1",
                voice=voice,
                speed=speed
            )
            
            # Return as data URL
            return f"data:audio/mp3;base64,{audio_base64}"
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None
    
    async def update_session_code(self, session_id: str, user_id: str, code: str) -> bool:
        code_with_badge = inject_zitex_badge(code)
        result = await self.db.chat_sessions.update_one(
            {"id": session_id, "user_id": user_id},
            {"$set": {"generated_code": code_with_badge, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        return result.modified_count > 0
    
    async def get_session_code(self, session_id: str, user_id: str) -> Optional[str]:
        session = await self.get_session(session_id, user_id)
        return session.get("generated_code") if session else None
    
    # ============== Templates System ==============
    async def save_as_template(self, user_id: str, session_id: str, name: str, description: str = "", category: str = "custom") -> Dict:
        """حفظ المشروع كقالب"""
        session = await self.get_session(session_id, user_id)
        if not session or not session.get("generated_code"):
            raise ValueError("لا يوجد كود للحفظ")
        
        # Check credits
        credits = await self.get_user_credits(user_id)
        cost = SERVICE_COSTS["save_template"]
        if credits < cost:
            raise ValueError(f"رصيد غير كافٍ. المطلوب: {cost} نقطة")
        
        template = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": name,
            "description": description,
            "category": category,
            "code": session["generated_code"],
            "session_type": session.get("session_type", "website"),
            "preview_image": None,
            "is_public": False,
            "is_premium": False,
            "cost": 0,
            "uses_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.templates.insert_one(template)
        await self.deduct_credits(user_id, cost, "save_template")
        
        return {
            "id": template["id"],
            "name": template["name"],
            "message": f"✅ تم حفظ القالب بنجاح! (-{cost} نقطة)"
        }
    
    async def get_templates(self, user_id: str = None, category: str = None, include_public: bool = True) -> List[Dict]:
        """استرجاع القوالب"""
        templates = []
        
        # Add default templates
        for t in DEFAULT_TEMPLATES:
            if category and t["category"] != category:
                continue
            templates.append({**t, "is_default": True, "user_id": None})
        
        # Add user templates
        query = {}
        if user_id:
            if include_public:
                query = {"$or": [{"user_id": user_id}, {"is_public": True}]}
            else:
                query = {"user_id": user_id}
        elif include_public:
            query = {"is_public": True}
        
        if category:
            query["category"] = category
        
        user_templates = await self.db.templates.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
        templates.extend([{**t, "is_default": False} for t in user_templates])
        
        return templates
    
    async def use_template(self, user_id: str, template_id: str, session_id: str = None) -> Dict:
        """استخدام قالب"""
        # Check if default template
        default_template = next((t for t in DEFAULT_TEMPLATES if t["id"] == template_id), None)
        
        if default_template:
            template = default_template
            code = self._get_default_template_code(template_id)
        else:
            template = await self.db.templates.find_one({"id": template_id}, {"_id": 0})
            if not template:
                raise ValueError("القالب غير موجود")
            code = template.get("code", "")
        
        # Check credits for premium templates
        cost = template.get("cost", SERVICE_COSTS["use_template"])
        if cost > 0:
            credits = await self.get_user_credits(user_id)
            if credits < cost:
                raise ValueError(f"رصيد غير كافٍ. المطلوب: {cost} نقطة")
            await self.deduct_credits(user_id, cost, "use_template")
        
        # Update uses count
        if not default_template:
            await self.db.templates.update_one(
                {"id": template_id},
                {"$inc": {"uses_count": 1}}
            )
        
        # Create or update session with template code
        if session_id:
            await self.update_session_code(session_id, user_id, code)
        else:
            session = await self.create_session(user_id, template.get("session_type", "website"), f"من قالب: {template['name']}")
            session_id = session["id"]
            await self.update_session_code(session_id, user_id, code)
        
        return {
            "session_id": session_id,
            "code": inject_zitex_badge(code),
            "template_name": template["name"],
            "cost": cost
        }

    def _get_default_template_code(self, template_id: str) -> str:
        """كود القوالب الافتراضية"""
        templates_code = {
            "landing-dark": '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>صفحة هبوط</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#0a0a12] text-white min-h-screen">
    <nav class="fixed top-0 w-full bg-black/50 backdrop-blur-xl border-b border-amber-500/20 z-50">
        <div class="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
            <h1 class="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500">Logo</h1>
            <div class="flex gap-6">
                <a href="#" class="text-gray-300 hover:text-amber-400 transition">الرئيسية</a>
                <a href="#" class="text-gray-300 hover:text-amber-400 transition">الخدمات</a>
                <a href="#" class="text-gray-300 hover:text-amber-400 transition">تواصل</a>
            </div>
        </div>
    </nav>
    <section class="pt-32 pb-20 px-6">
        <div class="max-w-4xl mx-auto text-center">
            <h1 class="text-5xl md:text-6xl font-bold mb-6 text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500">
                عنوان رئيسي جذاب
            </h1>
            <p class="text-xl text-gray-400 mb-8">وصف مختصر يشرح ما تقدمه من خدمات أو منتجات بشكل واضح ومباشر</p>
            <button class="px-8 py-4 bg-gradient-to-r from-amber-600 to-yellow-600 rounded-full text-lg font-bold hover:from-amber-700 hover:to-yellow-700 transition shadow-lg shadow-amber-500/30">
                ابدأ الآن
            </button>
        </div>
    </section>
</body>
</html>''',
            "ecommerce-gold": '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>متجر إلكتروني</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#0a0a12] text-white min-h-screen">
    <nav class="bg-black/80 backdrop-blur border-b border-amber-500/20 sticky top-0 z-50">
        <div class="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
            <h1 class="text-2xl font-bold text-amber-400">المتجر</h1>
            <div class="flex items-center gap-4">
                <input type="text" placeholder="ابحث..." class="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-sm">
                <button class="relative p-2">🛍️<span class="absolute -top-1 -right-1 bg-amber-500 text-black text-xs w-5 h-5 rounded-full flex items-center justify-center">3</span></button>
            </div>
        </div>
    </nav>
    <section class="py-12 px-6">
        <div class="max-w-6xl mx-auto">
            <h2 class="text-3xl font-bold text-amber-400 mb-8">المنتجات المميزة</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="bg-slate-800/50 border border-slate-700 rounded-2xl overflow-hidden hover:border-amber-500/50 transition">
                    <div class="h-48 bg-gradient-to-br from-amber-500/20 to-yellow-500/20 flex items-center justify-center text-6xl">📱</div>
                    <div class="p-4">
                        <h3 class="text-lg font-bold text-white">منتج 1</h3>
                        <p class="text-gray-400 text-sm mb-3">وصف المنتج</p>
                        <div class="flex justify-between items-center">
                            <span class="text-amber-400 font-bold">199 ر.س</span>
                            <button class="px-4 py-2 bg-amber-600 rounded-lg text-sm hover:bg-amber-700">أضف للسلة</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>
</body>
</html>''',
            "portfolio-minimal": '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>معرض الأعمال</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#0a0a12] text-white min-h-screen">
    <section class="min-h-screen flex items-center justify-center px-6">
        <div class="text-center">
            <div class="w-32 h-32 bg-gradient-to-br from-amber-500 to-yellow-500 rounded-full mx-auto mb-6 flex items-center justify-center text-4xl">👤</div>
            <h1 class="text-4xl font-bold mb-2">اسمك هنا</h1>
            <p class="text-amber-400 text-xl mb-6">مصمم | مطور | مبدع</p>
            <p class="text-gray-400 max-w-md mx-auto mb-8">نبذة مختصرة عنك وعن خبراتك ومهاراتك في مجال عملك</p>
            <div class="flex justify-center gap-4">
                <a href="#" class="px-6 py-3 bg-amber-600 rounded-lg hover:bg-amber-700 transition">أعمالي</a>
                <a href="#" class="px-6 py-3 border border-amber-500 rounded-lg hover:bg-amber-500/20 transition">تواصل معي</a>
            </div>
        </div>
    </section>
</body>
</html>''',
            "dashboard-pro": '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة التحكم</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#0a0a12] text-white min-h-screen flex">
    <aside class="w-64 bg-[#0d0d18] border-l border-slate-800 p-4 hidden md:block">
        <h1 class="text-xl font-bold text-amber-400 mb-8">📊 Dashboard</h1>
        <nav class="space-y-2">
            <a href="#" class="flex items-center gap-3 px-4 py-3 bg-amber-500/20 border border-amber-500/30 rounded-xl text-amber-400">🏠 الرئيسية</a>
            <a href="#" class="flex items-center gap-3 px-4 py-3 hover:bg-slate-800 rounded-xl text-gray-400">📈 الإحصائيات</a>
            <a href="#" class="flex items-center gap-3 px-4 py-3 hover:bg-slate-800 rounded-xl text-gray-400">👥 المستخدمين</a>
            <a href="#" class="flex items-center gap-3 px-4 py-3 hover:bg-slate-800 rounded-xl text-gray-400">⚙️ الإعدادات</a>
        </nav>
    </aside>
    <main class="flex-1 p-6">
        <h2 class="text-2xl font-bold mb-6">مرحباً بك 👋</h2>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div class="bg-gradient-to-br from-amber-500/20 to-yellow-500/20 border border-amber-500/30 rounded-2xl p-6">
                <p class="text-gray-400 text-sm">إجمالي المبيعات</p>
                <p class="text-3xl font-bold text-amber-400">12,450</p>
            </div>
            <div class="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
                <p class="text-gray-400 text-sm">المستخدمين</p>
                <p class="text-3xl font-bold">2,340</p>
            </div>
            <div class="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
                <p class="text-gray-400 text-sm">الطلبات</p>
                <p class="text-3xl font-bold">456</p>
            </div>
            <div class="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
                <p class="text-gray-400 text-sm">الإيرادات</p>
                <p class="text-3xl font-bold">89,200</p>
            </div>
        </div>
    </main>
</body>
</html>''',

            "game-2d-platformer": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2D Platformer Game</title>
    <script src="https://cdn.jsdelivr.net/npm/phaser@3.70.0/dist/phaser.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #1a1a2e; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        #game { border-radius: 12px; overflow: hidden; box-shadow: 0 0 30px rgba(255,215,0,0.3); }
    </style>
</head>
<body>
    <div id="game"></div>
    <script>
        const config = {
            type: Phaser.AUTO,
            width: 800,
            height: 600,
            parent: 'game',
            backgroundColor: '#16213e',
            physics: { default: 'arcade', arcade: { gravity: { y: 800 }, debug: false } },
            scene: { preload, create, update }
        };
        
        let player, cursors, platforms, coins, score = 0, scoreText;
        const game = new Phaser.Game(config);
        
        function preload() {
            this.load.setBaseURL('https://labs.phaser.io');
            this.load.image('ground', 'assets/sprites/platform.png');
            this.load.image('star', 'assets/sprites/star.png');
            this.load.spritesheet('dude', 'assets/sprites/dude.png', { frameWidth: 32, frameHeight: 48 });
        }
        
        function create() {
            platforms = this.physics.add.staticGroup();
            platforms.create(400, 568, 'ground').setScale(2).refreshBody();
            platforms.create(600, 400, 'ground');
            platforms.create(50, 250, 'ground');
            platforms.create(750, 220, 'ground');
            
            player = this.physics.add.sprite(100, 450, 'dude');
            player.setBounce(0.2);
            player.setCollideWorldBounds(true);
            
            this.anims.create({ key: 'left', frames: this.anims.generateFrameNumbers('dude', { start: 0, end: 3 }), frameRate: 10, repeat: -1 });
            this.anims.create({ key: 'turn', frames: [{ key: 'dude', frame: 4 }], frameRate: 20 });
            this.anims.create({ key: 'right', frames: this.anims.generateFrameNumbers('dude', { start: 5, end: 8 }), frameRate: 10, repeat: -1 });
            
            coins = this.physics.add.group();
            for (let i = 0; i < 12; i++) {
                const coin = coins.create(70 + i * 70, 0, 'star');
                coin.setBounceY(Phaser.Math.FloatBetween(0.4, 0.8));
            }
            
            scoreText = this.add.text(16, 16, 'Score: 0', { fontSize: '32px', fill: '#ffd700' });
            
            this.physics.add.collider(player, platforms);
            this.physics.add.collider(coins, platforms);
            this.physics.add.overlap(player, coins, collectCoin, null, this);
            
            cursors = this.input.keyboard.createCursorKeys();
        }
        
        function update() {
            if (cursors.left.isDown) { player.setVelocityX(-200); player.anims.play('left', true); }
            else if (cursors.right.isDown) { player.setVelocityX(200); player.anims.play('right', true); }
            else { player.setVelocityX(0); player.anims.play('turn'); }
            if (cursors.up.isDown && player.body.touching.down) player.setVelocityY(-500);
        }
        
        function collectCoin(player, coin) {
            coin.disableBody(true, true);
            score += 10;
            scoreText.setText('Score: ' + score);
        }
    </script>
</body>
</html>''',
            "game-3d-racing": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Racing Game</title>
    <script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #000; overflow: hidden; }
        #ui { position: fixed; top: 20px; left: 20px; color: #ffd700; font-family: Arial; font-size: 24px; z-index: 100; }
        #speed { font-size: 48px; font-weight: bold; }
    </style>
</head>
<body>
    <div id="ui">
        <div>Speed: <span id="speed">0</span> km/h</div>
        <div style="margin-top:10px;font-size:14px;">Use Arrow Keys to Drive</div>
    </div>
    <script>
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x1a1a2e);
        scene.fog = new THREE.Fog(0x1a1a2e, 50, 200);
        
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        document.body.appendChild(renderer.domElement);
        
        const ambient = new THREE.AmbientLight(0x404040, 2);
        scene.add(ambient);
        const directional = new THREE.DirectionalLight(0xffffff, 1);
        directional.position.set(50, 50, 50);
        scene.add(directional);
        
        const roadGeo = new THREE.PlaneGeometry(20, 1000);
        const roadMat = new THREE.MeshStandardMaterial({ color: 0x333333 });
        const road = new THREE.Mesh(roadGeo, roadMat);
        road.rotation.x = -Math.PI / 2;
        road.position.z = -450;
        scene.add(road);
        
        const carGeo = new THREE.BoxGeometry(2, 1, 4);
        const carMat = new THREE.MeshStandardMaterial({ color: 0xffd700 });
        const car = new THREE.Mesh(carGeo, carMat);
        car.position.y = 0.5;
        scene.add(car);
        
        for (let i = 0; i < 50; i++) {
            const treeGeo = new THREE.ConeGeometry(2, 8, 8);
            const treeMat = new THREE.MeshStandardMaterial({ color: 0x228b22 });
            const tree = new THREE.Mesh(treeGeo, treeMat);
            tree.position.set((Math.random() > 0.5 ? 15 : -15), 4, -i * 20);
            scene.add(tree);
        }
        
        camera.position.set(0, 5, 10);
        camera.lookAt(car.position);
        
        let speed = 0;
        const keys = {};
        document.addEventListener('keydown', e => keys[e.code] = true);
        document.addEventListener('keyup', e => keys[e.code] = false);
        
        function animate() {
            requestAnimationFrame(animate);
            
            if (keys['ArrowUp']) speed = Math.min(speed + 0.5, 100);
            if (keys['ArrowDown']) speed = Math.max(speed - 1, 0);
            if (keys['ArrowLeft']) car.position.x = Math.max(car.position.x - 0.2, -8);
            if (keys['ArrowRight']) car.position.x = Math.min(car.position.x + 0.2, 8);
            
            speed *= 0.99;
            car.position.z -= speed * 0.1;
            camera.position.z = car.position.z + 10;
            camera.lookAt(car.position);
            
            document.getElementById('speed').textContent = Math.round(speed);
            renderer.render(scene, camera);
        }
        animate();
        
        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });
    </script>
</body>
</html>''',
            "mobile-flutter-ecommerce": '''// Flutter E-Commerce App
// Run: flutter create my_app && cd my_app && flutter run

import 'package:flutter/material.dart';

void main() => runApp(const MyApp());

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'متجر إلكتروني',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.amber,
        scaffoldBackgroundColor: const Color(0xFF0a0a12),
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('المتجر'),
        backgroundColor: const Color(0xFF0d0d18),
      ),
      body: GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          childAspectRatio: 0.75,
        ),
        itemCount: 10,
        itemBuilder: (context, index) => Card(
          color: const Color(0xFF16213e),
          child: Column(
            children: [
              Expanded(child: Icon(Icons.shopping_bag, size: 64, color: Colors.amber)),
              Padding(
                padding: const EdgeInsets.all(8),
                child: Text('منتج ${index + 1}', style: const TextStyle(color: Colors.white)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}''',
            "mobile-react-native-social": '''// React Native Social App
// Run: npx react-native init MyApp && cd MyApp && npx react-native run-android

import React from 'react';
import { View, Text, FlatList, StyleSheet, SafeAreaView } from 'react-native';

const App = () => {
  const posts = [
    { id: '1', user: 'أحمد', content: 'مرحباً بالجميع!' },
    { id: '2', user: 'سارة', content: 'يوم جميل' },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>التواصل</Text>
      </View>
      <FlatList
        data={posts}
        keyExtractor={item => item.id}
        renderItem={({ item }) => (
          <View style={styles.post}>
            <Text style={styles.user}>{item.user}</Text>
            <Text style={styles.content}>{item.content}</Text>
          </View>
        )}
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0a12' },
  header: { padding: 16, backgroundColor: '#0d0d18' },
  title: { fontSize: 24, fontWeight: 'bold', color: '#ffd700' },
  post: { margin: 16, padding: 16, backgroundColor: '#16213e', borderRadius: 12 },
  user: { color: '#ffd700', fontWeight: 'bold' },
  content: { color: '#ccc', marginTop: 8 },
});

export default App;'''
        }
        return templates_code.get(template_id, templates_code["landing-dark"])

    
    # ============== Deployment System ==============
    async def deploy_project(self, user_id: str, session_id: str, subdomain: str) -> Dict:
        """نشر المشروع على نطاق فرعي"""
        
        # Validate subdomain
        subdomain = subdomain.lower().strip()
        if not re.match(r'^[a-z0-9][a-z0-9-]{2,30}[a-z0-9]$', subdomain):
            raise ValueError("اسم النطاق غير صالح. استخدم حروف إنجليزية صغيرة وأرقام وشرطات فقط (4-32 حرف)")
        
        # Check if subdomain is taken
        existing = await self.db.deployments.find_one({"subdomain": subdomain, "status": "active"})
        if existing:
            raise ValueError(f"النطاق {subdomain}.zitex.app محجوز بالفعل")
        
        # Get session code
        session = await self.get_session(session_id, user_id)
        if not session or not session.get("generated_code"):
            raise ValueError("لا يوجد كود للنشر")
        
        # Check credits
        credits = await self.get_user_credits(user_id)
        cost = SERVICE_COSTS["deploy"]
        if credits < cost:
            raise ValueError(f"رصيد غير كافٍ. المطلوب: {cost} نقطة")
        
        # Upload to Object Storage
        storage_path = f"{APP_NAME}/sites/{subdomain}/index.html"
        html_code = session["generated_code"]
        
        # Ensure code is bytes
        if isinstance(html_code, str):
            html_code = html_code.encode('utf-8')
        
        upload_result = upload_to_storage(storage_path, html_code, "text/html")
        
        if not upload_result:
            raise ValueError("فشل رفع الملف. حاول مرة أخرى")
        
        # Generate public URL
        public_url = f"https://{subdomain}.zitex.app"
        storage_url = f"{STORAGE_URL.replace('/api/v1/storage', '')}/sites/{subdomain}/index.html"
        
        # Create deployment record
        deployment = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "session_id": session_id,
            "subdomain": subdomain,
            "url": public_url,
            "storage_path": storage_path,
            "storage_url": storage_url,
            "status": "active",
            "visits": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": None
        }
        
        await self.db.deployments.insert_one(deployment)
        await self.deduct_credits(user_id, cost, f"deploy:{subdomain}")
        
        # Update session with deployment info
        await self.db.chat_sessions.update_one(
            {"id": session_id},
            {"$set": {
                "deployment": {
                    "id": deployment["id"],
                    "subdomain": subdomain,
                    "url": public_url,
                    "storage_path": storage_path,
                    "status": "active"
                }
            }}
        )
        
        return {
            "id": deployment["id"],
            "url": public_url,
            "storage_url": storage_url,
            "subdomain": subdomain,
            "message": f"🚀 تم نشر المشروع بنجاح!\n\n🔗 الرابط: {public_url}\n\n💰 التكلفة: {cost} نقطة"
        }
    
    async def update_deployment(self, user_id: str, deployment_id: str, new_code: str) -> Dict:
        """تحديث مشروع منشور"""
        deployment = await self.db.deployments.find_one(
            {"id": deployment_id, "user_id": user_id, "status": "active"},
            {"_id": 0}
        )
        
        if not deployment:
            raise ValueError("المشروع غير موجود")
        
        # Upload updated code
        storage_path = deployment["storage_path"]
        if isinstance(new_code, str):
            new_code = new_code.encode('utf-8')
        
        upload_result = upload_to_storage(storage_path, new_code, "text/html")
        
        if not upload_result:
            raise ValueError("فشل تحديث الملف")
        
        # Update record
        await self.db.deployments.update_one(
            {"id": deployment_id},
            {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {"message": "تم تحديث المشروع بنجاح", "url": deployment["url"]}
    
    async def get_user_deployments(self, user_id: str) -> List[Dict]:
        """استرجاع مشاريع المستخدم المنشورة"""
        deployments = await self.db.deployments.find(
            {"user_id": user_id, "status": "active"},
            {"_id": 0}
        ).sort("created_at", -1).to_list(50)
        return deployments
    
    async def get_deployment_by_subdomain(self, subdomain: str) -> Optional[Dict]:
        """استرجاع مشروع منشور بالنطاق"""
        return await self.db.deployments.find_one(
            {"subdomain": subdomain, "status": "active"},
            {"_id": 0}
        )
    
    async def delete_deployment(self, user_id: str, deployment_id: str) -> bool:
        """حذف مشروع منشور"""
        result = await self.db.deployments.update_one(
            {"id": deployment_id, "user_id": user_id},
            {"$set": {"status": "deleted"}}
        )
        return result.modified_count > 0

    # ============== Export & Social Media ==============
    async def export_for_social(self, user_id: str, asset_id: str, platform: str) -> Dict:
        """تصدير الأصول لمنصات التواصل الاجتماعي"""
        asset = await self.db.generated_assets.find_one(
            {"id": asset_id, "user_id": user_id},
            {"_id": 0}
        )
        
        if not asset:
            raise ValueError("الملف غير موجود")
        
        # Platform dimensions
        dimensions = {
            "instagram_post": {"width": 1080, "height": 1080},
            "instagram_story": {"width": 1080, "height": 1920},
            "instagram_reel": {"width": 1080, "height": 1920},
            "tiktok": {"width": 1080, "height": 1920},
            "youtube_short": {"width": 1080, "height": 1920},
            "youtube_video": {"width": 1920, "height": 1080},
            "facebook_post": {"width": 1200, "height": 630},
            "twitter_post": {"width": 1200, "height": 675},
            "linkedin_post": {"width": 1200, "height": 627}
        }
        
        if platform not in dimensions:
            raise ValueError("المنصة غير مدعومة")
        
        return {
            "asset_id": asset_id,
            "platform": platform,
            "dimensions": dimensions[platform],
            "original_url": asset.get("url"),
            "message": f"✅ جاهز للنشر على {platform}"
        }
    
    # ============== Analytics ==============
    async def get_user_analytics(self, user_id: str) -> Dict:
        """إحصائيات المستخدم"""
        # Count sessions
        total_sessions = await self.db.chat_sessions.count_documents({"user_id": user_id})
        active_sessions = await self.db.chat_sessions.count_documents({"user_id": user_id, "status": "active"})
        
        # Count assets
        total_images = await self.db.generated_assets.count_documents({"user_id": user_id, "asset_type": "image"})
        total_videos = await self.db.generated_assets.count_documents({"user_id": user_id, "asset_type": "video"})
        
        # Count deployments
        total_deployments = await self.db.deployments.count_documents({"user_id": user_id, "status": "active"})
        
        # Get user credits
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1, "credit_history": 1})
        credits = user.get("credits", 0) if user else 0
        
        # Calculate total spent
        credit_history = user.get("credit_history", []) if user else []
        total_spent = sum(abs(h.get("amount", 0)) for h in credit_history if h.get("amount", 0) < 0)
        
        return {
            "sessions": {
                "total": total_sessions,
                "active": active_sessions
            },
            "assets": {
                "images": total_images,
                "videos": total_videos,
                "total": total_images + total_videos
            },
            "deployments": total_deployments,
            "credits": {
                "current": credits,
                "total_spent": total_spent
            }
        }
    
    # ============== Admin Functions ==============
    async def get_all_users_stats(self) -> Dict:
        """إحصائيات جميع المستخدمين (للأدمن)"""
        total_users = await self.db.users.count_documents({})
        total_sessions = await self.db.chat_sessions.count_documents({})
        total_assets = await self.db.generated_assets.count_documents({})
        total_deployments = await self.db.deployments.count_documents({"status": "active"})
        
        return {
            "users": total_users,
            "sessions": total_sessions,
            "assets": total_assets,
            "deployments": total_deployments
        }
    
    async def add_credits_to_user(self, admin_id: str, target_user_id: str, amount: int, reason: str = "admin_add") -> bool:
        """إضافة نقاط لمستخدم (للأدمن)"""
        result = await self.db.users.update_one(
            {"id": target_user_id},
            {
                "$inc": {"credits": amount},
                "$push": {
                    "credit_history": {
                        "amount": amount,
                        "reason": reason,
                        "admin_id": admin_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
            }
        )
        return result.modified_count > 0

