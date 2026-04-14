"""
Zitex AI Chat Service - Progressive Builder Edition
خدمة الشات الذكي - النسخة التدريجية
Version 7.0 - Real Hosting + Full Game Support
"""
import os
import uuid
import base64
import logging
import re
import asyncio
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

AI_FEATURES_ENABLED = True

# ============== Object Storage for Real Hosting ==============
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get('EMERGENT_LLM_KEY')
APP_NAME = "zitex-hosting"
storage_key = None

def init_storage():
    """Initialize storage connection - call once at startup"""
    global storage_key
    if storage_key:
        return storage_key
    try:
        resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
        resp.raise_for_status()
        storage_key = resp.json()["storage_key"]
        logger.info("Object Storage initialized successfully")
        return storage_key
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        return None

def upload_to_storage(path: str, data: bytes, content_type: str) -> Optional[dict]:
    """Upload file to object storage"""
    key = init_storage()
    if not key:
        return None
    try:
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return None

def get_from_storage(path: str) -> Optional[Tuple[bytes, str]]:
    """Download file from storage"""
    key = init_storage()
    if not key:
        return None
    try:
        resp = requests.get(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key}, timeout=60
        )
        resp.raise_for_status()
        return resp.content, resp.headers.get("Content-Type", "text/html")
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None

# Try to import emergentintegrations for LLM chat
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    EMERGENT_LLM_AVAILABLE = True
except ImportError:
    EMERGENT_LLM_AVAILABLE = False
    LlmChat = None
    UserMessage = None

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs.types import VoiceSettings
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    ElevenLabs = None
    VoiceSettings = None

MASTER_SYSTEM_PROMPT = """أنت "زيتكس" (Zitex) - مهندس ذكاء اصطناعي محترف لبناء المشاريع الرقمية.
أنت مستشار ومنفذ. تفهم المشروع بالكامل ثم تبنيه قسم قسم مع العميل.

## القواعد الأساسية:
1. لا تكتب كود أبداً إلا بعد موافقة العميل على صورة التصميم
2. لا تتوقف - كل رد فيه تقدم (صورة أو كود)
3. احفظ كل تفاصيل المشروع واستخدمها في كل مرحلة
4. الـ prompt في DESIGN_IMAGE يكون تفصيلي جداً بالإنجليزية (100+ كلمة)
5. اذا العميل أعطاك تفاصيل كافية، أرسل [DESIGN_IMAGE] فوراً بدون أسئلة إضافية
6. اذا العميل وافق على التصميم، ابنِ الكود فوراً في [CODE_BLOCK] بدون أسئلة

## قواعد جودة التصميم والكود:
- استخدم Tailwind CSS عبر CDN
- استخدم تدرجات وخلفيات غنية، ليس ألوان مسطحة
- أضف ظلال (shadow-lg, shadow-xl)، زوايا مدورة (rounded-xl)، شفافية (backdrop-blur)
- استخدم Font Awesome للأيقونات
- استخدم Google Fonts للخطوط العربية (Tajawal)
- تصميم responsive يعمل على جميع الشاشات
- أضف hover effects و transitions و animations لكل العناصر التفاعلية
- التصميم يجب أن يبدو احترافي وجاهز للنشر من أول مرحلة
- لا يوجد عذر لتصميم بدائي - قارن تصميمك مع أفضل المواقع والألعاب قبل إرساله
- أنشئ الكود الكامل - لا تترك TODO أو placeholders أو أجزاء ناقصة

## عند اختيار قسم، أظهر خياراته فقط:

اذا اختار موقع:
[BUTTONS]
شركة|متجر|مدونة|هبوط|بورتفوليو|آخر
[/BUTTONS]

اذا اختار لعبة:
[BUTTONS]
استراتيجية|أكشن|سباق|ألغاز|مطعم|أطفال|آخر
[/BUTTONS]

اذا اختار فيديو:
[BUTTONS]
سينمائي|إعلاني|مضحك|تعليمي|آخر
[/BUTTONS]

اذا اختار صورة:
[BUTTONS]
شعار|منتج|فنية|بانر|آخر
[/BUTTONS]

## نظام البناء - مواقع وتطبيقات:

خطوة 1 - فهم المشروع (سريع):
اسأل 2-3 أسئلة أساسية فقط عن: الهدف، الأقسام، الألوان، الجمهور
ثم لخّص ما فهمته وتأكد من العميل

خطوة 2 - تصميم الواجهة الرئيسية:
أرسل صورة تصميم:
[DESIGN_IMAGE]
prompt: [وصف تفصيلي بالإنجليزية - اذكر كل عنصر: header, hero, sections, colors, fonts, layout, buttons, images, style]
[/DESIGN_IMAGE]

"هذا تصميم الصفحة الرئيسية. وش رأيك؟"
[BUTTONS]
ممتاز|عدّل|غيّر الألوان|تصميم مختلف
[/BUTTONS]

خطوة 3 - التعديل حتى الرضا:
اذا العميل طلب تعديل، أرسل [DESIGN_IMAGE] جديدة بالتعديلات
كرر حتى يوافق العميل

خطوة 4 - بناء الكود فوراً (تلقائي بعد الموافقة):
لما العميل يوافق (يقول ممتاز أو موافق أو ابنِ):
- لا تسأل أي سؤال إضافي
- ابنِ الكود فوراً في [CODE_BLOCK] يطابق التصميم المعتمد
- الكود يظهر مباشرة في المعاينة (اللايف)
- الكود يستخدم: Tailwind CSS CDN + خط Tajawal + Font Awesome + تدرجات + ظلال + hover + responsive
- بعد الكود اكتب: "تم بناء المرحلة [X] في اللايف! شوف المعاينة."
[BUTTONS]
ممتاز، المرحلة التالية|عدّل|غيّر
[/BUTTONS]

مهم: في هذا الرد أرسل الكود فقط بدون صورة تصميم جديدة. الصورة تكون في الرد التالي.

خطوة 5 - الانتقال للمرحلة التالية:
لما العميل يقول "المرحلة التالية" أو "كمّل":
- اكتب: "المرحلة [X+1] من [Y]: [وصف المرحلة]"
- أرسل [DESIGN_IMAGE] للمرحلة الجديدة
- لا ترسل كود - انتظر موافقة العميل على التصميم الجديد

## نظام البناء - الألعاب (مهم جداً):

الألعاب تُبنى بنفس المبدأ لكن على مراحل أكثر:

مرحلة 1 - فهم اللعبة:
اسأل عن: نوع اللعبة، الفكرة، الميزات الأساسية
ثم اكتب ملخص كامل لخطة اللعبة:
"فهمت! خطة اللعبة:
- النوع: [مثلاً استراتيجية بناء قرى]
- الميزات: [زراعة، بناء، تجارة، قتال]
- المراحل:
  1. واجهة القرية الرئيسية
  2. نظام المباني والموارد
  3. نظام الجيوش والقتال
  4. نظام التجارة والتحالفات
  5. التحسينات النهائية
نبدأ بالمرحلة الأولى؟"

مرحلة 2 - تصميم الواجهة الرئيسية:
[DESIGN_IMAGE]
prompt: [وصف شاشة اللعبة الرئيسية بالتفصيل - الخريطة، المباني، الموارد، الأزرار، الألوان، الأسلوب الفني]
[/DESIGN_IMAGE]

مرحلة 3 - بناء الواجهة فوراً (بعد الموافقة):
لما العميل يوافق:
- ابنِ الكود فوراً في [CODE_BLOCK] يطابق التصميم
- الكود يظهر في اللايف مباشرة
- اكتب: "تم بناء المرحلة 1 في اللايف! شوف المعاينة."
[BUTTONS]
ممتاز، المرحلة التالية|عدّل|غيّر
[/BUTTONS]
لا ترسل صورة في هذا الرد - فقط الكود

مرحلة 4 - المرحلة التالية:
لما العميل يقول "المرحلة التالية":
- اكتب "المرحلة [X] من [Y]: [وصف]"
- أرسل [DESIGN_IMAGE] للمرحلة الجديدة
- لا ترسل كود - انتظر الموافقة

بعد الموافقة:
- ابنِ كود محدّث يشمل الجديد + القديم في [CODE_BLOCK]
- الكود يتراكم (كل مرحلة تشمل كل اللي قبلها + الجديد)

مرحلة 5 - وهكذا لكل مرحلة:
كل مرحلة = صورة ثم موافقة ثم كود فوري في اللايف ثم انتقال تلقائي للمرحلة التالية
الكود يتراكم (كل مرحلة تشمل كل اللي قبلها + الجديد)

المرحلة الأخيرة - التسليم:
لما كل المراحل تخلص:
"اللعبة/الموقع جاهز بالكامل وشغّال في اللايف!"
[BUTTONS]
انشر على رابط خاص|أبي الأكواد كاملة|تعديلات أخيرة
[/BUTTONS]

اذا العميل قال "أبي الأكواد" أو "أبي أرفعه بره":
- اشرح له خطوة بخطوة كيف يأخذ الكود وينشره
- أعطه الكود كامل مع شرح كل ملف
- علّمه المتطلبات (استضافة، دومين، الخ)

## حفظ تفاصيل المشروع:
في كل رد، تذكّر:
- كل التفاصيل اللي اتفقت عليها مع العميل
- كل التصاميم اللي اعتمدها
- المرحلة الحالية والمراحل القادمة
- أي تعديلات طلبها العميل سابقاً
اذكر المرحلة الحالية في كل رد: "المرحلة [X] من [Y]"

## نظام إنشاء الفيديوهات (مفصّل):

الفيديوهات تُبنى بنفس مبدأ الاستشارة: فهم ثم اقتراح ثم موافقة ثم تنفيذ.

خطوة 1 - فهم الطلب:
اسأل العميل:
1. ما هدف الفيديو؟ (إعلان منتج، محتوى سوشيال، فيلم قصير، شرح خدمة، ترويج علامة تجارية)
2. مين الجمهور المستهدف؟ (شباب، أعمال، أطفال، عام)
3. وين بينشره؟ (يوتيوب، تيك توك، انستقرام ريلز، سناب، موقعه الخاص)
4. هل عنده فكرة محددة أو يبي اقتراحات؟

خطوة 2 - اقتراح النوع والمقاس:
بناءً على المنصة المستهدفة، اقترح المقاس الأنسب:
- تيك توك / ريلز / سناب / ستوري: عمودي (1024x1792)
- يوتيوب / فيسبوك / موقع: أفقي (1792x1024 أو 1280x720)
- انستقرام بوست: مربع (1024x1024)

اعرض الخيارات:
[BUTTONS]
عمودي (ريلز/تيك توك)|أفقي (يوتيوب)|مربع (انستقرام)
[/BUTTONS]

ثم اقترح نوع الفيديو:
[BUTTONS]
سينمائي (دراماتيكي)|إعلاني (ترويجي)|مضحك (كوميدي)|تعليمي (شرح)
[/BUTTONS]

خطوة 3 - بناء السيناريو التفصيلي:
اكتب سيناريو مفصّل مشهد بمشهد:
"السيناريو المقترح:

المشهد الأول (0-3 ثواني): [الافتتاحية - hook يجذب المشاهد]
المشهد الثاني (3-7 ثواني): [المحتوى الرئيسي - الرسالة أو القصة]
المشهد الثالث (7-10 ثواني): [الختام - CTA أو نهاية مؤثرة]

النمط البصري: [سينمائي داكن / ألوان زاهية / مينيمال أنيق]
الإضاءة: [طبيعية دافئة / دراماتيكية / ناعمة احترافية]
حركة الكاميرا: [بطيئة سينمائية / سريعة ديناميكية / ثابتة مع زوم]
الموسيقى المقترحة: [ملحمية / هادئة / حماسية / بدون]"

[BUTTONS]
موافق على السيناريو|عدّل السيناريو|سيناريو مختلف تماماً
[/BUTTONS]

خطوة 4 - التعليق الصوتي (اختياري):
"هل تبي تعليق صوتي على الفيديو؟ (+10 نقاط)"
[BUTTONS]
نعم، أبي تعليق صوتي|لا، بدون صوت|معاينة الأصوات المتاحة
[/BUTTONS]

اذا أراد تعليق صوتي:
- اكتب نص التعليق الصوتي الكامل
- اقترح نوع الصوت المناسب:
  alloy: صوت محايد متعدد الاستخدامات
  echo: صوت رجالي عميق ودافئ
  fable: صوت سردي قصصي
  onyx: صوت رجالي قوي وواثق
  nova: صوت نسائي دافئ وطبيعي
  shimmer: صوت نسائي واضح ومشرق
- أرسل معاينة صوتية:
[VOICE_PREVIEW]
text: [نص المعاينة]
voice: [اسم الصوت]
[/VOICE_PREVIEW]

خطوة 5 - ملخص التكلفة والتأكيد:
قبل التوليد، اعرض ملخص كامل:
"ملخص طلب الفيديو:
- النوع: [سينمائي/إعلاني/مضحك/تعليمي]
- المدة: [4/8/12] ثواني
- المقاس: [أفقي/عمودي/مربع] ([WxH])
- تعليق صوتي: [نعم - صوت X / لا]
- التكلفة الإجمالية: [X] نقطة (فيديو: [Y] + صوت: [Z])
- رصيدك الحالي: [N] نقطة
- المتبقي بعد الخصم: [N-X] نقطة"

[BUTTONS]
موافق، أنشئ الفيديو|تعديل الطلب|إلغاء
[/BUTTONS]

خطوة 6 - التوليد:
بعد الموافقة الصريحة فقط، أرسل أمر التوليد:
[VIDEO_GENERATE]
type: [cinematic/funny/advertising/educational]
duration: [4/8/12]
prompt: [وصف تفصيلي بالإنجليزية - يشمل: المشهد الكامل، الإضاءة، الألوان، حركة الكاميرا، الأسلوب البصري، التفاصيل الدقيقة - 100+ كلمة على الأقل]
voice_text: [نص التعليق الصوتي بالعربية أو الإنجليزية - اذا مطلوب]
voice: [alloy/echo/fable/onyx/nova/shimmer]
size: [1792x1024 أو 1024x1792 أو 1280x720 أو 1024x1024]
[/VIDEO_GENERATE]

بعد التوليد بنجاح:
"تم إنشاء الفيديو بنجاح! شاهده أعلاه."
[BUTTONS]
تحميل الفيديو|فيديو إضافي|تصدير للسوشيال ميديا|تعديلات
[/BUTTONS]

أنماط الفيديو التفصيلية:
1. سينمائي (cinematic): إضاءة دراماتيكية، حركة كاميرا بطيئة وسلسة، ألوان عميقة ومشبعة، أسلوب أفلام هوليوود
2. إعلاني (advertising): ألوان زاهية تجذب العين، نصوص واضحة وكبيرة، CTA قوي، إيقاع سريع وحيوي، تركيز على المنتج
3. مضحك (funny): مواقف كوميدية، حركات مبالغة، ألوان مشرقة، إيقاع سريع مفاجئ
4. تعليمي (educational): رسوم توضيحية واضحة، خطوات مرتبة، خلفية نظيفة، نصوص مصاحبة

تكلفة الفيديوهات:
سينمائي: 4 ثواني = 50 نقطة | 8 ثواني = 80 نقطة | 12 ثانية = 120 نقطة
مضحك: 4 ثواني = 30 نقطة | 8 ثواني = 50 نقطة | 12 ثانية = 70 نقطة
إعلاني: 4 ثواني = 60 نقطة | 8 ثواني = 100 نقطة | 12 ثانية = 150 نقطة
تعليمي: 4 ثواني = 40 نقطة | 8 ثواني = 65 نقطة | 12 ثانية = 90 نقطة
التعليق الصوتي: +10 نقاط إضافية

## الصور:
[IMAGE_GENERATE]
type: [logo/product/banner/social/art]
prompt: [وصف تفصيلي بالإنجليزية - 50+ كلمة]
[/IMAGE_GENERATE]

استيحاء من صورة (10 نقاط):
[IMAGE_INSPIRE]
reference: [رابط الصورة المرجعية]
prompt: [وصف بالإنجليزية للصورة المطلوبة مع ذكر ما يُستوحى من المرجع]
[/IMAGE_INSPIRE]

تعديل صورة (8 نقاط):
[IMAGE_EDIT]
original: [الرابط الفعلي للصورة الأصلية]
changes: [وصف التعديلات المطلوبة بالإنجليزية]
[/IMAGE_EDIT]

## قواعد صارمة:
1. تحقق من الرصيد قبل أي إنشاء
2. صورة التصميم أولاً دائماً قبل الكود (للمواقع والألعاب)
3. لا تكتب كود بدون موافقة على التصميم
4. الكود يتراكم - كل مرحلة تشمل اللي قبلها
5. احفظ كل التفاصيل واستخدمها
6. prompt الصور والفيديوهات يكون تفصيلي جداً بالإنجليزية (100+ كلمة)
7. لا تولد فيديو أبداً بدون موافقة على السيناريو والتكلفة
8. لا تتوقف أبداً - كل رد يجب أن يحتوي على تقدم فعلي
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
    "mobile_flutter": 30,
    "mobile_react_native": 30,
    "mobile_swift": 35,
    "mobile_kotlin": 35,
    "mobile_ui_advanced": 15,
    "mobile_backend": 20,
    "video_cinematic_4": 50,
    "video_cinematic_8": 80,
    "video_cinematic_12": 120,
    "video_funny_4": 30,
    "video_funny_8": 50,
    "video_funny_12": 70,
    "video_advertising_4": 60,
    "video_advertising_8": 100,
    "video_advertising_12": 150,
    "video_educational_4": 40,
    "video_educational_8": 65,
    "video_educational_12": 90,
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
        "durations": [4, 8],
        "sizes": ["1024x1792", "1080x1920"],
        "cost_base": 30
    },
    "cinematic": {
        "name": "فيديوهات سينمائية",
        "name_en": "Cinematic Videos",
        "description": "أفلام قصيرة، مشاهد درامية",
        "durations": [8, 12],
        "sizes": ["1792x1024", "1280x720"],
        "cost_base": 100
    },
    "advertising": {
        "name": "فيديوهات إعلانية",
        "name_en": "Advertising Videos",
        "description": "حملات إعلانية، ترويج منتجات",
        "durations": [4, 8, 12],
        "sizes": ["1280x720", "1024x1024", "1024x1792"],
        "cost_base": 150
    },
    "educational": {
        "name": "فيديوهات تعليمية",
        "name_en": "Educational Videos",
        "description": "شرح خدمات، دروس، محتوى تعليمي",
        "durations": [4, 8, 12],
        "sizes": ["1280x720", "1792x1024", "1024x1024"],
        "cost_base": 90
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
    },
    {
        "id": "mobile-swift-fitness",
        "name": "تطبيق لياقة Swift",
        "category": "mobile",
        "preview_image": "/api/templates/preview/mobile-swift-fitness",
        "description": "تطبيق لياقة وصحة لـ iOS بتقنية Swift",
        "is_premium": True,
        "cost": 35,
        "tags": ["mobile", "swift", "fitness", "ios"],
        "tech": "swift"
    },
    {
        "id": "mobile-kotlin-news",
        "name": "تطبيق أخبار Kotlin",
        "category": "mobile",
        "preview_image": "/api/templates/preview/mobile-kotlin-news",
        "description": "تطبيق أخبار لـ Android بتقنية Kotlin",
        "is_premium": True,
        "cost": 35,
        "tags": ["mobile", "kotlin", "news", "android"],
        "tech": "kotlin"
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
    
    if any(word in message for word in ["تطبيق موبايل", "تطبيق جوال", "تطبيق هاتف", "📱 تطبيق"]):
        return "mobile"
    if any(word in message_lower for word in ["flutter", "react native", "swift", "kotlin"]):
        return "mobile"
    if any(word in message for word in ["ios", "iphone", "ipad", "أيفون", "آيفون"]):
        return "mobile"
    if any(word in message for word in ["android", "أندرويد", "اندرويد"]):
        return "mobile"
    
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
                    ai_response, credits_used, has_buttons = await self._generate_with_gpt(session, message, request_type, credits, settings)
                    
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
                "has_buttons": has_buttons,
                "image_urls": [a["url"] for a in attachments if a.get("type") == "image" and a.get("url")]
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        update_data = {
            "$push": {"messages": {"$each": [user_msg, assistant_msg]}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
        
        if request_type != "general":
            update_data["$set"]["session_type"] = request_type
        
        code = None
        
        code_block_match = re.search(r'\[CODE_BLOCK\]\s*```(?:html|javascript|js)?\n?([\s\S]*?)```\s*\[/CODE_BLOCK\]', ai_response)
        if code_block_match:
            code = code_block_match.group(1).strip()
        else:
            code_block_match2 = re.search(r'\[CODE_BLOCK\]\s*(<!DOCTYPE[\s\S]*?</html>)\s*\[/CODE_BLOCK\]', ai_response, re.IGNORECASE)
            if code_block_match2:
                code = code_block_match2.group(1).strip()
            else:
                code_block_match3 = re.search(r'\[CODE_BLOCK\]\s*([\s\S]*?)\s*\[/CODE_BLOCK\]', ai_response)
                if code_block_match3:
                    code = code_block_match3.group(1).strip()
                    code = re.sub(r'^```(?:html|javascript|js)?\s*', '', code)
                    code = re.sub(r'```\s*$', '', code)
                    code = code.strip()
                else:
                    code_match = re.search(r'```(?:html|javascript|js)?\n?([\s\S]*?)```', ai_response)
                    if code_match:
                        code = code_match.group(1).strip()
        
        if code:
            code_with_badge = inject_zitex_badge(code)
            update_data["$set"]["generated_code"] = code_with_badge
            assistant_msg["metadata"]["generated_code"] = code_with_badge
            assistant_msg["metadata"]["has_preview"] = True
        
        await self.db.chat_sessions.update_one({"id": session_id}, update_data)
        
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
        attachments = []
        total_credits = 0
        processed_response = ai_response
        
        design_match = re.search(
            r'\[DESIGN_IMAGE\]\s*'
            r'prompt:\s*([^\[]+?)\s*'
            r'\[/DESIGN_IMAGE\]',
            processed_response, re.IGNORECASE | re.DOTALL
        )
        
        if design_match:
            design_prompt = design_match.group(1).strip()
            design_cost = 5
            
            if available_credits - total_credits >= design_cost:
                design_url = await self._generate_single_image(design_prompt)
                if design_url:
                    attachments.append({
                        "type": "image",
                        "url": design_url,
                        "image_type": "design_mockup",
                        "prompt": design_prompt
                    })
                    total_credits += design_cost
                    
                    processed_response = re.sub(
                        r'\[DESIGN_IMAGE\][\s\S]*?\[/DESIGN_IMAGE\]',
                        f"""
## 🎨 تصميم المشروع المقترح

💰 التكلفة: {design_cost} نقاط

شوف التصميم أعلاه وقلي رأيك:

[BUTTONS]
✅ ممتاز، ابنِ الكود|✏️ عدّل التصميم|🎨 غيّر الألوان|🔄 تصميم مختلف تماماً
[/BUTTONS]""",
                        processed_response
                    )
                else:
                    processed_response = re.sub(
                        r'\[DESIGN_IMAGE\][\s\S]*?\[/DESIGN_IMAGE\]',
                        "❌ فشل توليد صورة التصميم. حاول مرة أخرى.",
                        processed_response
                    )
        
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
            size = video_match.group(6).strip() if video_match.group(6) else "1280x720"
            
            cost_key = f"video_{video_type}_{duration}"
            video_cost = SERVICE_COSTS.get(cost_key, 60)
            voice_cost = SERVICE_COSTS.get("voice_over", 10) if voice_text else 0
            total_video_cost = video_cost + voice_cost
            
            if available_credits >= total_video_cost:
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
                    
                    success_msg = f"""
## ✅ تم إنشاء الفيديو بنجاح!

🎬 النوع: {video_type}
⏱️ المدة: {duration} ثواني
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
        
        inspire_match = re.search(
            r'\[IMAGE_INSPIRE\]\s*'
            r'reference:\s*(\S+)\s*'
            r'prompt:\s*([^\[]+?)\s*'
            r'\[/IMAGE_INSPIRE\]',
            processed_response, re.IGNORECASE | re.DOTALL
        )
        
        if inspire_match:
            ref_url = inspire_match.group(1).strip()
            inspire_prompt = inspire_match.group(2).strip()
            inspire_cost = 10
            
            if available_credits - total_credits >= inspire_cost:
                inspired_url = await self._generate_inspired_image(ref_url, inspire_prompt)
                if inspired_url:
                    attachments.append({
                        "type": "image",
                        "url": inspired_url,
                        "image_type": "inspired",
                        "prompt": inspire_prompt,
                        "reference": ref_url
                    })
                    total_credits += inspire_cost
                    
                    processed_response = re.sub(
                        r'\[IMAGE_INSPIRE\][\s\S]*?\[/IMAGE_INSPIRE\]',
                        f"""
## ✅ تم إنشاء صورة مستوحاة من المرجع!

💰 التكلفة: {inspire_cost} نقطة

[BUTTONS]
✏️ عدّل الصورة|🎨 نسخة أخرى|💾 حفظ|🔄 مختلفة تماماً
[/BUTTONS]""",
                        processed_response
                    )
                else:
                    processed_response = re.sub(
                        r'\[IMAGE_INSPIRE\][\s\S]*?\[/IMAGE_INSPIRE\]',
                        "❌ فشل توليد الصورة. حاول مرة أخرى.",
                        processed_response
                    )
        
        edit_match = re.search(
            r'\[IMAGE_EDIT\]\s*'
            r'original:\s*(\S+)\s*'
            r'changes:\s*([^\[]+?)\s*'
            r'\[/IMAGE_EDIT\]',
            processed_response, re.IGNORECASE | re.DOTALL
        )
        
        if edit_match:
            original_url = edit_match.group(1).strip()
            edit_changes = edit_match.group(2).strip()
            edit_cost = 8
            
            if available_credits - total_credits >= edit_cost:
                edited_url = await self._edit_image_with_prompt(original_url, edit_changes)
                if edited_url:
                    attachments.append({
                        "type": "image",
                        "url": edited_url,
                        "image_type": "edited",
                        "prompt": edit_changes,
                        "original": original_url
                    })
                    total_credits += edit_cost
                    
                    processed_response = re.sub(
                        r'\[IMAGE_EDIT\][\s\S]*?\[/IMAGE_EDIT\]',
                        f"""
## ✅ تم تعديل الصورة!

💰 التكلفة: {edit_cost} نقطة

[BUTTONS]
✏️ تعديل إضافي|🔄 إعادة التعديل|💾 حفظ|↩️ الرجوع للأصلية
[/BUTTONS]""",
                        processed_response
                    )
                else:
                    processed_response = re.sub(
                        r'\[IMAGE_EDIT\][\s\S]*?\[/IMAGE_EDIT\]',
                        "❌ فشل تعديل الصورة. حاول مرة أخرى.",
                        processed_response
                    )
        
        return processed_response, attachments, total_credits
    
    async def _generate_inspired_image(self, reference_url: str, prompt: str) -> Optional[str]:
        """توليد صورة مستوحاة من صورة مرجعية"""
        try:
            from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
            
            image_gen = OpenAIImageGeneration(api_key=self.emergent_key)
            
            ref_description = ""
            try:
                ref_resp = requests.get(reference_url, timeout=15)
                if ref_resp.status_code == 200:
                    ref_b64 = base64.b64encode(ref_resp.content).decode('utf-8')
                    if EMERGENT_LLM_AVAILABLE and self.emergent_key:
                        from emergentintegrations.llm.chat import FileContent
                        chat = LlmChat(api_key=self.emergent_key, session_id="img-analyze", system_message="You are an expert image analyst. Describe this image in great detail for an artist to recreate it. Focus on: art style, colors, composition, characters, buildings, landscape, UI elements. Be very specific. Answer in English.")
                        chat.with_model("openai", "gpt-4o")
                        content_type = ref_resp.headers.get('Content-Type', 'image/png')
                        fc = FileContent(content_type=content_type, file_content_base64=ref_b64)
                        msg = UserMessage(text="Describe this image in full detail for recreation:", file_contents=[fc])
                        ref_description = await chat.send_message(msg)
            except Exception as e:
                logger.error(f"Failed to analyze reference image: {e}")
            
            full_prompt = f"Create a high quality game art illustration. {prompt}. "
            if ref_description:
                full_prompt += f"Style reference: {ref_description[:500]}"
            
            images = await image_gen.generate_images(
                prompt=full_prompt,
                model="gpt-image-1",
                number_of_images=1
            )
            
            if images and len(images) > 0:
                image_id = str(uuid.uuid4())
                image_path = f"{APP_NAME}/images/{image_id}.png"
                upload_result = upload_to_storage(image_path, images[0], "image/png")
                if upload_result:
                    return f"{STORAGE_URL.replace('/api/v1/storage', '')}/images/{image_id}.png"
                else:
                    return f"data:image/png;base64,{base64.b64encode(images[0]).decode('utf-8')}"
            return None
        except Exception as e:
            logger.error(f"Inspired image generation error: {e}")
            return None
    
    async def _edit_image_with_prompt(self, original_url: str, edit_prompt: str) -> Optional[str]:
        """تعديل صورة بناءً على تعليق العميل"""
        try:
            from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
            
            image_gen = OpenAIImageGeneration(api_key=self.emergent_key)
            
            original_description = ""
            try:
                ref_resp = requests.get(original_url, timeout=15)
                if ref_resp.status_code == 200:
                    ref_b64 = base64.b64encode(ref_resp.content).decode('utf-8')
                    if EMERGENT_LLM_AVAILABLE and self.emergent_key:
                        from emergentintegrations.llm.chat import FileContent
                        chat = LlmChat(api_key=self.emergent_key, session_id="img-edit", system_message="Describe this image in detail in English. Focus on every visual element.")
                        chat.with_model("openai", "gpt-4o")
                        fc = FileContent(content_type="image/png", file_content_base64=ref_b64)
                        msg = UserMessage(text="Describe this image:", file_contents=[fc])
                        original_description = await chat.send_message(msg)
            except Exception as e:
                logger.error(f"Failed to analyze original image: {e}")
            
            full_prompt = f"Recreate this image with modifications: {original_description[:500]}. CHANGES REQUESTED: {edit_prompt}"
            
            images = await image_gen.generate_images(
                prompt=full_prompt,
                model="gpt-image-1",
                number_of_images=1
            )
            
            if images and len(images) > 0:
                image_id = str(uuid.uuid4())
                image_path = f"{APP_NAME}/images/{image_id}.png"
                upload_result = upload_to_storage(image_path, images[0], "image/png")
                if upload_result:
                    return f"{STORAGE_URL.replace('/api/v1/storage', '')}/images/{image_id}.png"
                else:
                    return f"data:image/png;base64,{base64.b64encode(images[0]).decode('utf-8')}"
            return None
        except Exception as e:
            logger.error(f"Image edit error: {e}")
            return None
    
    async def _generate_video(self, user_id: str, session_id: str, prompt: str, duration: int, size: str, video_type: str) -> Optional[Dict]:
        """توليد فيديو باستخدام Sora 2"""
        try:
            from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
            
            video_gen = OpenAIVideoGeneration(api_key=self.emergent_key)
            
            valid_durations = [4, 8, 12]
            if duration not in valid_durations:
                duration = min(valid_durations, key=lambda x: abs(x - duration))
            
            valid_sizes = ["1280x720", "1792x1024", "1024x1792", "1024x1024"]
            if size not in valid_sizes:
                size = "1280x720"
            
            logger.info(f"Generating video: type={video_type}, duration={duration}, size={size}")
            
            video_bytes = video_gen.text_to_video(
                prompt=prompt,
                model="sora-2",
                size=size,
                duration=duration,
                max_wait_time=600
            )
            
            if video_bytes:
                video_id = str(uuid.uuid4())
                video_path = f"{APP_NAME}/videos/{user_id}/{video_id}.mp4"
                
                upload_result = upload_to_storage(video_path, video_bytes, "video/mp4")
                
                if upload_result:
                    video_url = f"{STORAGE_URL.replace('/api/v1/storage', '')}/videos/{user_id}/{video_id}.mp4"
                    
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
                image_id = str(uuid.uuid4())
                image_path = f"{APP_NAME}/images/{image_id}.png"
                
                upload_result = upload_to_storage(image_path, images[0], "image/png")
                
                if upload_result:
                    image_url = f"{STORAGE_URL.replace('/api/v1/storage', '')}/images/{image_id}.png"
                    return image_url
                else:
                    image_base64 = base64.b64encode(images[0]).decode('utf-8')
                    return f"data:image/png;base64,{image_base64}"
            
            return None
            
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return None
    
    async def _generate_with_gpt(self, session: Dict, message: str, request_type: str, credits: int, settings: Dict) -> Tuple[str, int, bool]:
        project_data = session.get("project_data", {})
        stage = session.get("conversation_stage", "initial")
        
        context = f"""
رصيد العميل: {credits} نقطة
مرحلة المحادثة: {stage}
بيانات المشروع حتى الآن: {project_data}
"""
        
        system_prompt = MASTER_SYSTEM_PROMPT + context
        
        image_urls = re.findall(r'(https?://\S+\.(?:png|jpg|jpeg|gif|webp))', message, re.IGNORECASE)
        image_urls += re.findall(r'(https?://integrations\.emergentagent\.com/objstore/\S+)', message)
        
        conversation_history = ""
        for msg in session.get("messages", [])[-12:]:
            role_label = "المستخدم" if msg["role"] == "user" else "زيتكس"
            conversation_history += f"\n{role_label}: {msg['content']}\n"
            if msg.get("metadata", {}).get("image_urls"):
                for img_url in msg["metadata"]["image_urls"]:
                    conversation_history += f"[صورة مولّدة: {img_url}]\n"
            elif msg.get("attachments"):
                for att in msg["attachments"]:
                    if att.get("type") == "image" and att.get("url"):
                        conversation_history += f"[صورة مولّدة: {att['url']}]\n"
        
        full_prompt = f"{conversation_history}\nالمستخدم: {message}"
        
        try:
            if EMERGENT_LLM_AVAILABLE and self.emergent_key:
                chat = LlmChat(
                    api_key=self.emergent_key,
                    session_id=session.get("id", "default"),
                    system_message=system_prompt
                )
                chat.with_model("openai", "gpt-4o")
                
                file_contents = []
                if image_urls:
                    for img_url in image_urls[:3]:
                        try:
                            from emergentintegrations.llm.chat import FileContent
                            img_resp = requests.get(img_url, timeout=15)
                            if img_resp.status_code == 200:
                                img_b64 = base64.b64encode(img_resp.content).decode('utf-8')
                                content_type = img_resp.headers.get('Content-Type', 'image/png')
                                file_contents.append(FileContent(content_type=content_type, file_content_base64=img_b64))
                                logger.info(f"Attached image: {img_url[:50]}...")
                        except Exception as e:
                            logger.error(f"Failed to attach image {img_url}: {e}")
                
                if file_contents:
                    user_message = UserMessage(text=full_prompt, file_contents=file_contents)
                else:
                    user_message = UserMessage(text=full_prompt)
                response = await chat.send_message(user_message)
            
            elif self.openai_client:
                messages = [{"role": "system", "content": system_prompt}]
                for msg in session.get("messages", [])[-12:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                messages.append({"role": "user", "content": message})
                
                completion = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=16384
                )
                response = completion.choices[0].message.content
            else:
                return "⚠️ خدمة الذكاء الاصطناعي غير متاحة. يرجى إضافة مفتاح API.", 0, False
            
            credits_used = 1
            
            has_code = '[CODE_BLOCK]' in response or ('```html' in response and '[CODE_BLOCK]' not in response) or '```javascript' in response
            
            if has_code:
                credits_used = SERVICE_COSTS.get(request_type, 15)
            
            has_buttons = "[BUTTONS]" in response
            
            return response, credits_used, has_buttons
            
        except Exception as e:
            logger.error(f"GPT error: {e}")
            return f"❌ خطأ في المعالجة: {str(e)}", 0, False
    
    def _generate_title(self, message: str, request_type: str) -> str:
        icons = {"image": "🎨", "video": "🎬", "website": "🌐", "game": "🎮", "webapp": "💻", "pwa": "📱"}
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
        if not text or len(text.strip()) == 0:
            return None
        
        text = text[:4000]
        
        import re
        text = re.sub(r'\[BUTTONS\][\s\S]*?\[/BUTTONS\]', '', text)
        text = re.sub(r'\[CODE_BLOCK\][\s\S]*?\[/CODE_BLOCK\]', '', text)
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = text.strip()
        
        if not text:
            return None
        
        try:
            from emergentintegrations.llm.openai import OpenAITextToSpeech
            
            tts = OpenAITextToSpeech(api_key=self.emergent_key)
            
            audio_base64 = await tts.generate_speech_base64(
                text=text,
                model="tts-1",
                voice=voice,
                speed=speed
            )
            
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
        session = await self.get_session(session_id, user_id)
        if not session or not session.get("generated_code"):
            raise ValueError("لا يوجد كود للحفظ")
        
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
        templates = []
        
        for t in DEFAULT_TEMPLATES:
            if category and t["category"] != category:
                continue
            templates.append({**t, "is_default": True, "user_id": None})
        
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
        default_template = next((t for t in DEFAULT_TEMPLATES if t["id"] == template_id), None)
        
        if default_template:
            template = default_template
            code = self._get_default_template_code(template_id)
        else:
            template = await self.db.templates.find_one({"id": template_id}, {"_id": 0})
            if not template:
                raise ValueError("القالب غير موجود")
            code = template.get("code", "")
        
        cost = template.get("cost", SERVICE_COSTS["use_template"])
        if cost > 0:
            credits = await self.get_user_credits(user_id)
            if credits < cost:
                raise ValueError(f"رصيد غير كافٍ. المطلوب: {cost} نقطة")
            await self.deduct_credits(user_id, cost, "use_template")
        
        if not default_template:
            await self.db.templates.update_one(
                {"id": template_id},
                {"$inc": {"uses_count": 1}}
            )
        
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
            <h1 class="text-5xl md:text-6xl font-bold mb-6 text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-yellow-500">عنوان رئيسي جذاب</h1>
            <p class="text-xl text-gray-400 mb-8">وصف مختصر يشرح ما تقدمه من خدمات أو منتجات بشكل واضح ومباشر</p>
            <button class="px-8 py-4 bg-gradient-to-r from-amber-600 to-yellow-600 rounded-full text-lg font-bold hover:from-amber-700 hover:to-yellow-700 transition shadow-lg shadow-amber-500/30">ابدأ الآن</button>
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
            <h1 class="text-2xl font-bold text-amber-400">🛒 المتجر</h1>
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
                <p class="text-3xl font-bold text-green-400">+15%</p>
            </div>
        </div>
    </main>
</body>
</html>''',
            "game-2d-platformer": '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لعبة منصات 2D</title>
    <script src="https://cdn.jsdelivr.net/npm/phaser@3.70.0/dist/phaser.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0a0a12; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        #game-container { border: 3px solid #ffd700; border-radius: 10px; overflow: hidden; }
        .score { position: absolute; top: 20px; right: 20px; color: #ffd700; font-size: 24px; font-family: Arial; }
    </style>
</head>
<body>
    <div class="score">النقاط: <span id="score">0</span></div>
    <div id="game-container"></div>
    <script>
        let score = 0;
        const config = {
            type: Phaser.AUTO, width: 800, height: 600, parent: 'game-container',
            physics: { default: 'arcade', arcade: { gravity: { y: 500 }, debug: false } },
            scene: { preload, create, update }
        };
        let player, platforms, cursors, stars;
        function preload() {
            this.load.setBaseURL('https://labs.phaser.io');
            this.load.image('sky', 'assets/skies/space3.png');
            this.load.image('ground', 'assets/sprites/platform.png');
            this.load.image('star', 'assets/demoscene/star.png');
            this.load.spritesheet('dude', 'assets/sprites/dude.png', { frameWidth: 32, frameHeight: 48 });
        }
        function create() {
            this.add.image(400, 300, 'sky');
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
            stars = this.physics.add.group({ key: 'star', repeat: 11, setXY: { x: 12, y: 0, stepX: 70 } });
            stars.children.iterate(child => child.setBounceY(Phaser.Math.FloatBetween(0.4, 0.8)));
            this.physics.add.collider(player, platforms);
            this.physics.add.collider(stars, platforms);
            this.physics.add.overlap(player, stars, collectStar, null, this);
            cursors = this.input.keyboard.createCursorKeys();
        }
        function update() {
            if (cursors.left.isDown) { player.setVelocityX(-160); player.anims.play('left', true); }
            else if (cursors.right.isDown) { player.setVelocityX(160); player.anims.play('right', true); }
            else { player.setVelocityX(0); player.anims.play('turn'); }
            if (cursors.up.isDown && player.body.touching.down) player.setVelocityY(-330);
        }
        function collectStar(player, star) {
            star.disableBody(true, true);
            score += 10;
            document.getElementById('score').textContent = score;
        }
        new Phaser.Game(config);
    </script>
</body>
</html>''',
            "game-3d-racing": '''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لعبة سباق 3D</title>
    <script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { overflow: hidden; background: #000; }
        #info { position: absolute; top: 20px; left: 50%; transform: translateX(-50%); color: #ffd700; font-size: 24px; font-family: Arial; z-index: 10; }
        #controls { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); color: #fff; font-size: 14px; font-family: Arial; z-index: 10; }
    </style>
</head>
<body>
    <div id="info">السرعة: <span id="speed">0</span> كم/س</div>
    <div id="controls">استخدم الأسهم للتحكم</div>
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
</html>'''
        }
        return templates_code.get(template_id, templates_code["landing-dark"])
    
    # ============== Deployment System with Real Hosting ==============
    async def deploy_project(self, user_id: str, session_id: str, subdomain: str) -> Dict:
        import re
        
        subdomain = subdomain.lower().strip()
        if not re.match(r'^[a-z0-9][a-z0-9-]{2,30}[a-z0-9]$', subdomain):
            raise ValueError("اسم النطاق غير صالح. استخدم حروف إنجليزية صغيرة وأرقام وشرطات فقط (4-32 حرف)")
        
        existing = await self.db.deployments.find_one({"subdomain": subdomain, "status": "active"})
        if existing:
            raise ValueError(f"النطاق {subdomain}.zitex.app محجوز بالفعل")
        
        session = await self.get_session(session_id, user_id)
        if not session or not session.get("generated_code"):
            raise ValueError("لا يوجد كود للنشر")
        
        credits = await self.get_user_credits(user_id)
        cost = SERVICE_COSTS["deploy"]
        if credits < cost:
            raise ValueError(f"رصيد غير كافٍ. المطلوب: {cost} نقطة")
        
        storage_path = f"{APP_NAME}/sites/{subdomain}/index.html"
        html_code = session["generated_code"]
        
        if isinstance(html_code, str):
            html_code = html_code.encode('utf-8')
        
        upload_result = upload_to_storage(storage_path, html_code, "text/html")
        
        if not upload_result:
            raise ValueError("فشل رفع الملف. حاول مرة أخرى")
        
        public_url = f"https://{subdomain}.zitex.app"
        storage_url = f"{STORAGE_URL.replace('/api/v1/storage', '')}/sites/{subdomain}/index.html"
        
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
        deployment = await self.db.deployments.find_one(
            {"id": deployment_id, "user_id": user_id, "status": "active"},
            {"_id": 0}
        )
        
        if not deployment:
            raise ValueError("المشروع غير موجود")
        
        storage_path = deployment["storage_path"]
        if isinstance(new_code, str):
            new_code = new_code.encode('utf-8')
        
        upload_result = upload_to_storage(storage_path, new_code, "text/html")
        
        if not upload_result:
            raise ValueError("فشل تحديث الملف")
        
        await self.db.deployments.update_one(
            {"id": deployment_id},
            {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {"message": "تم تحديث المشروع بنجاح", "url": deployment["url"]}
    
    async def get_user_deployments(self, user_id: str) -> List[Dict]:
        deployments = await self.db.deployments.find(
            {"user_id": user_id, "status": "active"},
            {"_id": 0, "code": 0}
        ).sort("created_at", -1).to_list(50)
        return deployments
    
    async def get_deployment_by_subdomain(self, subdomain: str) -> Optional[Dict]:
        return await self.db.deployments.find_one(
            {"subdomain": subdomain, "status": "active"},
            {"_id": 0}
        )
    
    async def delete_deployment(self, user_id: str, deployment_id: str) -> bool:
        result = await self.db.deployments.update_one(
            {"id": deployment_id, "user_id": user_id},
            {"$set": {"status": "deleted"}}
        )
        return result.modified_count > 0
