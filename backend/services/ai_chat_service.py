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
BACKEND_URL = os.environ.get('BACKEND_URL', '')
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

## قواعد جودة التصميم والكود (مهم جداً - التزم بها حرفياً):
- استخدم Tailwind CSS فقط عبر هذا السكربت بالضبط: <script src="https://cdn.tailwindcss.com"></script>
  لا تستخدم أي رابط آخر لـ Tailwind مثل jsdelivr أو unpkg - فقط cdn.tailwindcss.com
- استخدم Font Awesome فقط عبر: <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
- استخدم Google Fonts للخطوط العربية: <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
- استخدم تدرجات وخلفيات غنية، ليس ألوان مسطحة
- أضف ظلال (shadow-lg, shadow-xl)، زوايا مدورة (rounded-xl)، شفافية (backdrop-blur)
- تصميم responsive يعمل على جميع الشاشات (استخدم md: و lg:)
- أضف hover effects و transitions و animations لكل العناصر التفاعلية
- التصميم يجب أن يبدو احترافي وجاهز للنشر من أول مرحلة
- الكود يجب أن يكون HTML كامل يبدأ بـ <!DOCTYPE html> وينتهي بـ </html>
- لا تستخدم أي مكتبات خارجية بدون CDN صحيح ومعروف
- اللغة العربية واتجاه RTL في كل الصفحات: <html lang="ar" dir="rtl">
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

قاعدة ذهبية للألعاب: الكود يجب أن يكون لعبة حقيقية مرسومة بـ SVG وليس إيموجي أو صفحة ويب!

### طريقة بناء الألعاب - استخدم هذا القالب الأساسي:
عند بناء لعبة استراتيجية، ابدأ دائماً بهذا الهيكل في الـ head:
<script src="https://cdn.tailwindcss.com"></script>
<style>
  *{margin:0;padding:0;box-sizing:border-box;font-family:Tajawal,sans-serif}
  body{overflow:hidden}
  .game-world{position:relative;width:100vw;height:100vh;background:linear-gradient(180deg,#87CEEB 0%,#5BA3D9 25%,#90EE90 25%,#4A8B3F 100%);overflow:hidden}
  .resource-bar{position:fixed;top:0;left:0;right:0;z-index:100;display:flex;justify-content:center;gap:20px;padding:10px;background:rgba(0,0,0,0.7);backdrop-filter:blur(10px)}
  .res-item{display:flex;align-items:center;gap:5px;background:rgba(255,255,255,0.1);padding:5px 15px;border-radius:20px;color:white;font-weight:bold}
  .building{position:absolute;cursor:pointer;transition:transform 0.3s;filter:drop-shadow(2px 4px 6px rgba(0,0,0,0.4))}
  .building:hover{transform:scale(1.15);z-index:50}
  .tooltip{display:none;position:absolute;bottom:105%;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.85);color:white;padding:8px 12px;border-radius:10px;white-space:nowrap;font-size:12px;z-index:99}
  .building:hover .tooltip{display:block}
  .cloud{position:absolute;animation:float-cloud linear infinite;opacity:0.8}
  .tree-sway{animation:sway 3s ease-in-out infinite}
  .action-bar{position:fixed;bottom:0;left:0;right:0;z-index:100;display:flex;justify-content:center;gap:10px;padding:15px;background:rgba(0,0,0,0.7);backdrop-filter:blur(10px)}
  .action-btn{padding:10px 20px;border:2px solid rgba(255,215,0,0.5);border-radius:12px;background:rgba(255,215,0,0.15);color:#FFD700;font-weight:bold;cursor:pointer;transition:all 0.3s}
  .action-btn:hover{background:rgba(255,215,0,0.3);transform:translateY(-2px)}
  @keyframes float-cloud{0%{transform:translateX(-150px)}100%{transform:translateX(calc(100vw + 150px))}}
  @keyframes sway{0%,100%{transform:rotate(-2deg)}50%{transform:rotate(2deg)}}
  @keyframes bounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
  .path{position:absolute;height:8px;background:#8B6914;border-radius:4px;opacity:0.6}
  .fence{position:absolute;width:4px;background:#8B5E3C;border-radius:2px}
  .grass-patch{position:absolute;width:15px;height:10px;border-radius:50% 50% 0 0}
</style>

ثم ضع عناصر اللعبة في body بهذا الشكل:
- div.game-world يحتوي كل العناصر
- div.resource-bar في الأعلى (ذهب، خشب، طعام، حجر، جنود) كل واحد مع SVG أيقونة صغيرة
- كل مبنى div.building مع position absolute وبداخله SVG كامل
- div.cloud مع SVG للغيوم
- div.action-bar في الأسفل (بناء، تدريب، ترقية، هجوم)
- JavaScript: موارد ديناميكية، بناء مباني جديدة عند الضغط، ترقية، مؤقتات

### قاعدة حرجة - ملء الخريطة بالكامل:
يجب أن تكون الخريطة مليئة مثل الصورة المرجعية!
ضع على الأقل:
- القلعة: حجم كبير (width:120px+) في المركز
- 5+ بيوت بأحجام وأماكن مختلفة
- 3+ مزارع
- 1+ منجم
- 8+ أشجار (كبيرة وصغيرة)
- 3+ غيوم متحركة
- 3+ جنود
- ممرات/طرق بين المباني
- سياج خشبي حول القرية
- زهور وشجيرات صغيرة كديكور
- تلال في الخلفية
لا مساحات فارغة!

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
- ابنِ الكود فوراً في [CODE_BLOCK]
- انظر للصورة المرجعية المرفقة وطابق ألوانها وأسلوبها

للألعاب الاستراتيجية وبناء القرى، استخدم محرك Zitex الجاهز:
كود بسيط جداً ينتج لعبة مليئة بالعناصر (40+ عنصر: قلاع، بيوت، أشجار، مزارع، جنود، غيوم، زهور):

[CODE_BLOCK]
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>لعبة بناء القرى</title>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap" rel="stylesheet">
</head>
<body>
<div id="game-world"></div>
<script src="/api/game-engine.js"></script>
<script>
ZitexGame.init({
  theme: 'medieval',
  buildings: 6,
  trees: 12,
  soldiers: 4,
  farms: 3,
  clouds: 4,
  flowers: 20,
  bushes: 8,
  rocks: 5
});
</script>
</body>
</html>
[/CODE_BLOCK]

عدّل الأرقام حسب طلب العميل (مثلاً buildings:10 لقرية أكبر).
لأنواع أخرى من الألعاب (سباق، ألغاز، أكشن): ابنِ الكود من الصفر باستخدام Canvas أو SVG.
اكتب: "تم بناء المرحلة 1 في اللايف! شوف المعاينة."

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
    "image_preview": 5,         # صور تجريبية للمشاهد
    "image_multiple": 15,
    # تطبيقات الموبايل
    "mobile_flutter": 30,
    "mobile_react_native": 30,
    "mobile_swift": 35,
    "mobile_kotlin": 35,
    "mobile_ui_advanced": 15,
    "mobile_backend": 20,
    # فيديوهات سينمائية
    "video_cinematic_4": 50,
    "video_cinematic_8": 80,
    "video_cinematic_12": 120,
    # فيديوهات مضحكة
    "video_funny_4": 30,
    "video_funny_8": 50,
    "video_funny_12": 70,
    # فيديوهات إعلانية
    "video_advertising_4": 60,
    "video_advertising_8": 100,
    "video_advertising_12": 150,
    # فيديوهات تعليمية
    "video_educational_4": 40,
    "video_educational_8": 65,
    "video_educational_12": 90,
    # إضافات
    "voice_over": 10,           # تعليق صوتي
    "voice_preview": 5,         # معاينة صوتية
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
        "sizes": ["1024x1792", "1080x1920"],  # Portrait
        "cost_base": 30
    },
    "cinematic": {
        "name": "فيديوهات سينمائية",
        "name_en": "Cinematic Videos",
        "description": "أفلام قصيرة، مشاهد درامية",
        "durations": [8, 12],
        "sizes": ["1792x1024", "1280x720"],  # Widescreen
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
    # قوالب تطبيقات الموبايل
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


# ============== GAME ENGINE FORCE-INJECTION ==============
GAME_GENRE_KEYWORDS = {
    "strategy": ["استراتيج", "قرية", "قلعة", "مبان", "جيش", "ممالك", "حرب", "مدينة", "بناء", "كلاش", "village", "castle", "kingdom", "rts", "clash"],
    "racing":   ["سباق", "سيار", "race", "racing", "car", "drift"],
    "platformer": ["منصات", "ماريو", "platformer", "mario", "قفز", "jump", "sonic"],
    "snake":    ["ثعبان", "أفعى", "snake"],
    "shooter":  ["فضاء", "إطلاق", "إطلاق نار", "سفينة", "space", "shooter", "invaders", "shoot"],
    "match3":   ["ألغاز", "جواهر", "مطابقة", "candy", "puzzle", "match", "crush", "gems"],
    "memory":   ["ذاكرة", "بطاقات", "memory", "match cards", "flip"],
    "breakout": ["كسر الطوب", "طوب", "breakout", "arkanoid"],
    "flappy":   ["طائر", "طيران", "flappy", "bird"],
}


def detect_game_genre(text: str, fallback: str = "strategy") -> str:
    """Pick a game genre based on Arabic/English keywords in the full chat context."""
    if not text:
        return fallback
    t = text.lower()
    scores = {}
    for genre, words in GAME_GENRE_KEYWORDS.items():
        scores[genre] = sum(1 for w in words if w.lower() in t)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else fallback


def detect_game_genre_prioritized(primary: str, context: str = "", fallback: str = "strategy") -> str:
    """First try to detect a genre from the primary (current) user message.
    Only fall back to the broader conversation context if the primary is inconclusive.
    This avoids cases where welcome messages or earlier generic words (e.g. "بناء")
    drown out a clear request like "ثعبان" or "سباق"."""
    g = detect_game_genre(primary, fallback="__none__")
    if g != "__none__":
        return g
    g = detect_game_genre(context, fallback="__none__")
    if g != "__none__":
        return g
    return fallback


def build_game_html(genre: str, title: str = "لعبة Zitex", hint: str = "", engine_url: str = "/api/game-engine.js", design_image_url: Optional[str] = None) -> str:
    """Generate a bulletproof HTML shell that loads the Zitex multi-genre game engine.

    If design_image_url is provided, we render an "image-backed" variant where the
    approved design image is used as the actual playable background with an
    interactive transparent overlay (HUD, hotspots, controls) on top — guaranteeing
    the live preview matches the generated design 1:1 instead of a stylized mock.
    """
    safe_hint = (hint or "").replace('"', "'").replace("\n", " ")[:600]
    safe_title = (title or "لعبة Zitex").replace('"', "'")[:80]

    # === IMAGE-BACKED MODE ===
    # For ANY approved design image, use it as the literal game background.
    if design_image_url:
        return _build_image_backed_game(genre, safe_title, safe_hint, design_image_url)

    # === GENERIC ENGINE MODE (no design image yet) ===
    cfg_map = {
        "strategy":  "{ genre:'strategy', theme:'medieval', buildings:8, trees:14, soldiers:5, farms:3, clouds:5, flowers:25, bushes:10, rocks:6 }",
        "racing":    "{ genre:'racing' }",
        "platformer":"{ genre:'platformer', theme:'forest' }",
        "snake":     "{ genre:'snake' }",
        "shooter":   "{ genre:'shooter' }",
        "match3":    "{ genre:'match3' }",
        "memory":    "{ genre:'memory' }",
        "breakout":  "{ genre:'breakout' }",
        "flappy":    "{ genre:'flappy' }",
    }
    cfg = cfg_map.get(genre, cfg_map["strategy"])

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<title>{safe_title}</title>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap" rel="stylesheet">
<style>
  html,body{{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:#0b1020;font-family:Tajawal,sans-serif}}
  #game-world{{width:100vw;height:100vh}}
  #zg-loading{{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;color:#FFD700;font-size:18px;background:radial-gradient(circle,#1a1f3a,#050818);z-index:500}}
</style>
</head>
<body>
<div id="zg-loading">⏳ جاري تحميل اللعبة...</div>
<div id="game-world"></div>
<script src="{engine_url}"></script>
<script>
(function(){{
  function boot(){{
    if (typeof ZitexGame === 'undefined') {{ setTimeout(boot, 100); return; }}
    document.getElementById('zg-loading').remove();
    try {{ ZitexGame.init({cfg}); }}
    catch(e){{ console.error(e); document.body.innerHTML = '<div style="color:#fff;padding:40px;text-align:center">خطأ في تحميل المحرك: '+e.message+'</div>'; }}
  }}
  boot();
}})();
</script>
<!-- Zitex: hint="{safe_hint}" genre="{genre}" -->
</body>
</html>"""


def _build_image_backed_game(genre: str, title: str, hint: str, image_url: str) -> str:
    """Live preview that uses the approved design image as the real background,
    with a transparent interactive overlay so the preview matches the image exactly."""

    # Per-genre overlay controls (HUD/foot/gameplay)
    if genre in ("strategy", "rts") or genre == "strategy":
        hud = """
        <div class="zg-chip">💰 <span id="rg">500</span></div>
        <div class="zg-chip">🪵 <span id="rw">300</span></div>
        <div class="zg-chip">🌾 <span id="rf">400</span></div>
        <div class="zg-chip">🪨 <span id="rs">150</span></div>
        <div class="zg-chip">⚔️ <span id="rsl">4</span></div>"""
        foot = """
        <button class="zg-btn" onclick="ZG.act('build')">🏠 بناء</button>
        <button class="zg-btn" onclick="ZG.act('train')">⚔️ تدريب</button>
        <button class="zg-btn" onclick="ZG.act('upgrade')">⭐ ترقية</button>
        <button class="zg-btn" onclick="ZG.act('attack')">🔥 هجوم</button>"""
    elif genre == "racing":
        hud = '<div class="zg-chip">🏁 <span id="rg">0</span> م</div><div class="zg-chip">❤️ <span id="rsl">3</span></div>'
        foot = '<span style="color:#FFD700;align-self:center;font-size:12px">← → للمسار</span>'
    elif genre == "platformer":
        hud = '<div class="zg-chip">🪙 <span id="rg">0</span></div><div class="zg-chip">❤️ <span id="rsl">3</span></div>'
        foot = '<span style="color:#FFD700;align-self:center;font-size:12px">← → للحركة | Space للقفز</span>'
    else:
        hud = '<div class="zg-chip">🏆 <span id="rg">0</span></div><div class="zg-chip">❤️ <span id="rsl">3</span></div>'
        foot = '<button class="zg-btn" onclick="ZG.act(\'play\')">▶️ العب</button>'

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<title>{title}</title>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap" rel="stylesheet">
<style>
  *{{margin:0;padding:0;box-sizing:border-box;font-family:Tajawal,sans-serif}}
  html,body{{width:100%;height:100%;overflow:hidden;background:#000}}
  .scene{{position:fixed;inset:0;background-image:url('{image_url}');background-size:cover;background-position:center;background-repeat:no-repeat}}
  .scene::after{{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.35),transparent 25%,transparent 75%,rgba(0,0,0,.45));pointer-events:none}}
  .zg-hud{{position:fixed;top:0;left:0;right:0;z-index:100;display:flex;justify-content:space-between;padding:10px 16px;background:linear-gradient(180deg,rgba(0,0,0,0.75),rgba(0,0,0,0.2));backdrop-filter:blur(10px);color:#fff;font-weight:700}}
  .zg-hud .left,.zg-hud .right{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
  .zg-chip{{display:flex;align-items:center;gap:6px;background:rgba(255,255,255,0.12);padding:6px 12px;border-radius:20px;font-size:13px;border:1px solid rgba(255,215,0,0.3)}}
  .zg-foot{{position:fixed;bottom:0;left:0;right:0;z-index:100;display:flex;justify-content:center;gap:8px;padding:10px;background:rgba(0,0,0,0.6);backdrop-filter:blur(10px)}}
  .zg-btn{{padding:9px 18px;border:2px solid rgba(255,215,0,0.5);border-radius:12px;background:rgba(255,215,0,0.15);color:#FFD700;font-weight:700;cursor:pointer;transition:all .25s;font-size:13px;font-family:inherit}}
  .zg-btn:hover{{background:rgba(255,215,0,0.35);transform:translateY(-2px);box-shadow:0 4px 14px rgba(255,215,0,0.3)}}
  .hotspot{{position:absolute;width:80px;height:80px;border-radius:50%;cursor:pointer;transition:all .3s;display:flex;align-items:center;justify-content:center;color:#FFD700;font-size:11px;font-weight:700;text-align:center;text-shadow:0 1px 3px rgba(0,0,0,.9)}}
  .hotspot::before{{content:"";position:absolute;inset:0;border-radius:50%;background:radial-gradient(circle,rgba(255,215,0,.35) 0%,rgba(255,215,0,0) 70%);animation:pulse 2s ease-in-out infinite}}
  .hotspot:hover{{transform:scale(1.15)}}
  .hotspot:hover::before{{background:radial-gradient(circle,rgba(255,215,0,.6) 0%,rgba(255,215,0,0) 70%)}}
  .tt{{display:none;position:absolute;bottom:calc(100% + 6px);left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.92);color:#fff;padding:6px 12px;border-radius:8px;white-space:nowrap;font-size:12px;border:1px solid rgba(255,215,0,0.3);z-index:99}}
  .hotspot:hover .tt{{display:block}}
  .zg-overlay{{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.78);z-index:200;backdrop-filter:blur(6px)}}
  .zg-card{{background:linear-gradient(135deg,#1a1f3a,#2a2f5a);padding:28px 36px;border-radius:18px;text-align:center;color:#fff;border:2px solid rgba(255,215,0,0.4);box-shadow:0 20px 60px rgba(0,0,0,.5);min-width:280px;animation:pop .35s ease}}
  .zg-card h1{{font-size:24px;color:#FFD700;margin-bottom:8px}}
  .zg-card p{{font-size:14px;opacity:.9;margin-bottom:16px;line-height:1.6}}
  .zg-badge{{position:fixed;bottom:60px;right:10px;z-index:90;font-size:10px;color:rgba(255,255,255,.45);background:rgba(0,0,0,.4);padding:3px 8px;border-radius:10px}}
  @keyframes pulse{{0%,100%{{transform:scale(1);opacity:.9}}50%{{transform:scale(1.15);opacity:.5}}}}
  @keyframes pop{{0%{{transform:scale(.7);opacity:0}}100%{{transform:scale(1);opacity:1}}}}
</style>
</head>
<body>
<div class="scene"></div>
<div class="zg-hud"><div class="left">{hud}</div><div class="right"><div class="zg-chip">🎮 {title}</div></div></div>
<div id="hot-layer"></div>
<div class="zg-foot">{foot}</div>
<div class="zg-badge">Zitex Engine · Image-backed</div>
<script>
(function(){{
  const genre = '{genre}';
  const state = {{ gold:500, wood:300, food:400, stone:150, soldiers:4, dist:0, lives:3, score:0 }};
  const upd = () => {{
    const map = {{rg:state.gold, rw:state.wood, rf:state.food, rs:state.stone, rsl:state.soldiers}};
    if (genre==='racing'){{ map.rg = state.dist; map.rsl = state.lives; }}
    if (genre==='platformer'){{ map.rg = state.score; map.rsl = state.lives; }}
    Object.entries(map).forEach(([k,v])=>{{ const el=document.getElementById(k); if(el) el.textContent=v; }});
  }};
  const overlay = (title,msg,btn,onBtn) => {{
    const o = document.createElement('div'); o.className='zg-overlay';
    o.innerHTML = '<div class="zg-card"><h1>'+title+'</h1><p>'+msg+'</p><button class="zg-btn">'+btn+'</button></div>';
    document.body.appendChild(o);
    o.querySelector('button').onclick = () => {{ o.remove(); if(onBtn) onBtn(); }};
  }};

  // Auto place interactive hotspots across the background image (plausible building locations)
  // The image fills the viewport via background-size:cover; hotspots are placed in relative % coords.
  const hotspots = [
    {{x:50, y:32, icon:'🏰', label:'القلعة الرئيسية - المستوى 5', action:'castle'}},
    {{x:24, y:50, icon:'🏠', label:'بيت - المستوى 2', action:'house'}},
    {{x:72, y:48, icon:'🏠', label:'بيت - المستوى 3', action:'house'}},
    {{x:18, y:68, icon:'🏡', label:'بيت - المستوى 1', action:'house'}},
    {{x:80, y:65, icon:'🏠', label:'بيت - المستوى 2', action:'house'}},
    {{x:38, y:72, icon:'🌾', label:'مزرعة - +5 طعام/ث', action:'farm'}},
    {{x:62, y:75, icon:'🌾', label:'مزرعة - +4 طعام/ث', action:'farm'}},
    {{x:88, y:80, icon:'⛏️', label:'منجم - +3 حجر/ث', action:'mine'}},
    {{x:45, y:55, icon:'⚔️', label:'جندي - قوة 20', action:'soldier'}},
    {{x:55, y:58, icon:'⚔️', label:'جندي - قوة 18', action:'soldier'}},
    {{x:12, y:30, icon:'🌲', label:'غابة - خشب', action:'forest'}},
    {{x:88, y:28, icon:'🌲', label:'غابة - خشب', action:'forest'}},
  ];
  const layer = document.getElementById('hot-layer');
  if (genre === 'strategy') {{
    hotspots.forEach(h => {{
      const d = document.createElement('div');
      d.className = 'hotspot';
      d.style.cssText = 'left:calc('+h.x+'% - 40px);top:calc('+h.y+'% - 40px)';
      d.innerHTML = '<div class="tt">'+h.label+'</div>'+h.icon;
      d.onclick = () => {{
        if (h.action === 'house') {{ state.gold += 10; state.wood += 5; upd(); }}
        else if (h.action === 'farm') {{ state.food += 15; upd(); }}
        else if (h.action === 'mine') {{ state.stone += 10; state.gold += 5; upd(); }}
        else if (h.action === 'forest') {{ state.wood += 20; upd(); }}
        else if (h.action === 'soldier') {{ overlay('⚔️ الجندي','قوة الهجوم: 20','موافق'); }}
        else if (h.action === 'castle') {{ overlay('🏰 القلعة الرئيسية','المستوى 5 · السلامة 100%','موافق'); }}
      }};
      layer.appendChild(d);
    }});
    // Passive income
    setInterval(()=>{{ state.gold+=5; state.wood+=3; state.food+=4; state.stone+=2; upd(); }}, 3000);
  }}

  window.ZG = {{
    state, upd, overlay,
    act(kind){{
      if (genre !== 'strategy') return overlay('قريباً','هذا الإجراء سيُضاف في المرحلة التالية','موافق');
      if (kind === 'build')  {{ if (state.wood>=50 && state.stone>=30){{ state.wood-=50; state.stone-=30; upd(); overlay('🏠 بُني بيت جديد','تمت إضافة مبنى جديد للقرية','رائع'); }} else overlay('موارد غير كافية','تحتاج 50 خشب و 30 حجر','موافق'); }}
      else if (kind === 'train')  {{ if (state.food>=30 && state.gold>=20){{ state.food-=30; state.gold-=20; state.soldiers++; upd(); overlay('⚔️ جندي جديد','انضم جندي للجيش','رائع'); }} else overlay('موارد غير كافية','تحتاج 30 طعام و 20 ذهب','موافق'); }}
      else if (kind === 'upgrade'){{ if (state.gold>=100){{ state.gold-=100; upd(); overlay('✨ ترقية','ارتقت القلعة لمستوى أعلى','رائع'); }} else overlay('ذهب غير كاف','تحتاج 100 ذهب','موافق'); }}
      else if (kind === 'attack') {{ overlay('⚔️ هجوم','جيشك يتقدم نحو قرية العدو...','انتظار النصر'); }}
    }}
  }};
  upd();
}})();
</script>
<!-- Zitex: hint="{hint}" genre="{genre}" image-backed -->
</body>
</html>"""


def render_design_to_html(design: dict) -> str:
    """Render a user-crafted design (JSON of elements with exact coords) into a
    fully playable HTML game. Each element renders via SVG at the EXACT position
    the user placed it — guaranteed 1:1 match between editor and live preview."""
    canvas = design.get("canvas") or {}
    w = int(canvas.get("width") or 1280)
    h = int(canvas.get("height") or 720)
    bg_img = canvas.get("background_image_url") or ""
    bg_color = canvas.get("background_color") or "#87CEEB"
    name = (design.get("name") or "لعبة Zitex").replace('"', "'")[:80]
    genre = design.get("genre") or "strategy"
    elements = design.get("elements") or []

    # Build element HTML
    parts = []
    for el in sorted(elements, key=lambda e: e.get("z_index", 0)):
        etype = el.get("type") or "rect"
        x = float(el.get("x", 0))
        y = float(el.get("y", 0))
        ew = float(el.get("width", 100))
        eh = float(el.get("height", 100))
        rot = float(el.get("rotation", 0))
        sx = float(el.get("scale_x", 1))
        sy = float(el.get("scale_y", 1))
        props = el.get("props") or {}
        label = (props.get("label") or "").replace('"', "'")[:60]
        eid = (el.get("id") or "").replace('"', "'")[:40]
        transform = f"translate({x}px,{y}px) rotate({rot}deg) scale({sx},{sy})"
        tip = f'<div class="tt">{label}</div>' if label else ''

        # User-extracted element (cropped from AI-generated image)
        if etype == "user_element":
            src = (props.get("source_image_url") or "").replace('"', "'")
            crop = props.get("crop") or {}
            cx = float(crop.get("x", 0))
            cy = float(crop.get("y", 0))
            cw = float(crop.get("w", 100))
            ch = float(crop.get("h", 100))
            # Scale the background so the crop window covers exactly the element box
            natural_w = float(props.get("natural_width") or 0)
            natural_h = float(props.get("natural_height") or 0)
            if natural_w > 0 and natural_h > 0 and cw > 0 and ch > 0:
                bg_w = natural_w * (ew / cw)
                bg_h = natural_h * (eh / ch)
                bg_x = -cx * (ew / cw)
                bg_y = -cy * (eh / ch)
                bg_style = (f"background-image:url('{src}');"
                            f"background-size:{bg_w}px {bg_h}px;"
                            f"background-position:{bg_x}px {bg_y}px;"
                            f"background-repeat:no-repeat")
            else:
                bg_style = f"background-image:url('{src}');background-size:cover"
            data_cat = (props.get("category") or "custom").replace('"', "'")[:30]
            parts.append(
                f'<div class="el el-user" data-id="{eid}" data-type="user_element" data-category="{data_cat}" '
                f'style="width:{ew}px;height:{eh}px;transform:{transform};z-index:{el.get("z_index",0)};{bg_style}">'
                f'{tip}</div>'
            )
        else:
            svg_inner = _element_svg(etype, props)
            parts.append(
                f'<div class="el" data-id="{eid}" data-type="{etype}" '
                f'style="width:{ew}px;height:{eh}px;transform:{transform};z-index:{el.get("z_index",0)}">'
                f'{tip}{svg_inner}</div>'
            )

    bg_layer = (
        f'<div class="bg-img" style="background-image:url(\'{bg_img}\')"></div>' if bg_img else ''
    )

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<title>{name}</title>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap" rel="stylesheet">
<style>
  *{{margin:0;padding:0;box-sizing:border-box;font-family:Tajawal,sans-serif}}
  html,body{{width:100%;height:100%;overflow:hidden;background:#0b1020}}
  .stage{{position:fixed;inset:50px 0 60px 0;display:flex;align-items:center;justify-content:center}}
  .frame{{position:relative;width:{w}px;height:{h}px;background:{bg_color};border-radius:12px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.5);max-width:96%;max-height:96%}}
  .bg-img{{position:absolute;inset:0;background-size:cover;background-position:center;background-repeat:no-repeat}}
  .bg-img::after{{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.2),transparent 30%,transparent 70%,rgba(0,0,0,.3));pointer-events:none}}
  .el{{position:absolute;top:0;left:0;cursor:pointer;transition:transform .2s,filter .2s;transform-origin:top left;filter:drop-shadow(2px 4px 6px rgba(0,0,0,.4))}}
  .el:hover{{filter:drop-shadow(2px 4px 14px rgba(255,215,0,.6)) brightness(1.1);z-index:999 !important}}
  .el svg{{width:100%;height:100%;display:block;pointer-events:none}}
  .tt{{display:none;position:absolute;bottom:100%;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.92);color:#fff;padding:6px 12px;border-radius:8px;white-space:nowrap;font-size:12px;border:1px solid rgba(255,215,0,.3);z-index:99}}
  .el:hover .tt{{display:block}}
  .zg-hud{{position:fixed;top:0;left:0;right:0;z-index:100;display:flex;justify-content:space-between;padding:10px 16px;background:linear-gradient(180deg,rgba(0,0,0,.78),rgba(0,0,0,.2));backdrop-filter:blur(10px);color:#fff;font-weight:700}}
  .zg-hud .g{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
  .zg-chip{{display:flex;align-items:center;gap:6px;background:rgba(255,255,255,.1);padding:6px 12px;border-radius:20px;font-size:13px;border:1px solid rgba(255,215,0,.25)}}
  .zg-foot{{position:fixed;bottom:0;left:0;right:0;z-index:100;display:flex;justify-content:center;gap:8px;padding:10px;background:rgba(0,0,0,.6);backdrop-filter:blur(10px)}}
  .zg-btn{{padding:9px 18px;border:2px solid rgba(255,215,0,.5);border-radius:12px;background:rgba(255,215,0,.12);color:#FFD700;font-weight:700;cursor:pointer;transition:all .25s;font-size:13px;font-family:inherit}}
  .zg-btn:hover{{background:rgba(255,215,0,.3);transform:translateY(-2px)}}
  .badge{{position:fixed;bottom:62px;right:10px;z-index:90;font-size:10px;color:rgba(255,255,255,.45);background:rgba(0,0,0,.4);padding:3px 8px;border-radius:10px}}
</style>
</head>
<body>
<div class="zg-hud">
  <div class="g">
    <div class="zg-chip">💰 <span id="r_gold">500</span></div>
    <div class="zg-chip">🪵 <span id="r_wood">300</span></div>
    <div class="zg-chip">🌾 <span id="r_food">400</span></div>
    <div class="zg-chip">🪨 <span id="r_stone">150</span></div>
    <div class="zg-chip">⚔️ <span id="r_sold">4</span></div>
  </div>
  <div class="g"><div class="zg-chip">🎮 {name}</div></div>
</div>
<div class="stage">
  <div class="frame">
    {bg_layer}
    {''.join(parts)}
  </div>
</div>
<div class="zg-foot">
  <button class="zg-btn" onclick="ZD.act('build')">🏠 بناء</button>
  <button class="zg-btn" onclick="ZD.act('train')">⚔️ تدريب</button>
  <button class="zg-btn" onclick="ZD.act('upgrade')">⭐ ترقية</button>
  <button class="zg-btn" onclick="ZD.act('attack')">🔥 هجوم</button>
</div>
<div class="badge">Zitex · من تصميم العميل</div>
<script>
(function(){{
  const state = {{gold:500,wood:300,food:400,stone:150,sold:4}};
  const upd = () => Object.entries(state).forEach(([k,v])=>{{ const el=document.getElementById('r_'+k); if(el) el.textContent=v; }});
  const alert2 = (t,m) => {{
    const o = document.createElement('div');
    o.style.cssText='position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.75);z-index:500;backdrop-filter:blur(6px)';
    o.innerHTML = '<div style="background:linear-gradient(135deg,#1a1f3a,#2a2f5a);padding:26px 36px;border-radius:16px;color:#fff;text-align:center;border:2px solid rgba(255,215,0,.4);box-shadow:0 20px 60px rgba(0,0,0,.5);min-width:280px"><h3 style="color:#FFD700;margin-bottom:8px;font-size:22px">'+t+'</h3><p style="margin-bottom:14px;opacity:.9">'+m+'</p><button class="zg-btn">موافق</button></div>';
    document.body.appendChild(o);
    o.querySelector('button').onclick = () => o.remove();
  }};
  // Per-element behaviour by type
  document.querySelectorAll('.el').forEach(el => {{
    const t = el.dataset.type;
    el.addEventListener('click', () => {{
      if (t === 'wheat_field')  {{ state.food += 15; upd(); alert2('🌾 حقل قمح','+15 طعام'); }}
      else if (t === 'clay_field')  {{ state.stone += 10; state.gold += 3; upd(); alert2('🏺 حقل طين','+10 حجر ، +3 ذهب'); }}
      else if (t === 'house')    {{ state.gold += 10; state.wood += 5; upd(); alert2('🏠 بيت','+10 ذهب ، +5 خشب'); }}
      else if (t === 'castle')   {{ alert2('🏰 القلعة','قاعدة الحكم - المستوى 5'); }}
      else if (t === 'mine')     {{ state.stone += 12; upd(); alert2('⛏️ منجم','+12 حجر'); }}
      else if (t === 'soldier')  {{ alert2('⚔️ جندي','قوة الهجوم: 20'); }}
      else if (t === 'tree')     {{ state.wood += 8; upd(); alert2('🌲 شجرة','+8 خشب'); }}
      else if (t === 'farm')     {{ state.food += 10; upd(); alert2('🚜 مزرعة','+10 طعام'); }}
      else {{ alert2('عنصر','تفاعل قيد التطوير'); }}
    }});
  }});
  window.ZD = {{
    state, upd, alert2,
    act(kind){{
      if (kind==='build'){{ if(state.wood>=50 && state.stone>=30){{ state.wood-=50; state.stone-=30; upd(); alert2('🏠 بناء','جاهز لوضع المبنى'); }} else alert2('موارد ناقصة','تحتاج 50 خشب و 30 حجر'); }}
      else if (kind==='train'){{ if(state.food>=30 && state.gold>=20){{ state.food-=30; state.gold-=20; state.sold++; upd(); alert2('⚔️ جندي جديد','انضم جندي جديد'); }} else alert2('موارد ناقصة','تحتاج 30 طعام و 20 ذهب'); }}
      else if (kind==='upgrade'){{ if(state.gold>=100){{ state.gold-=100; upd(); alert2('✨ ترقية','ترقية ناجحة'); }} else alert2('ذهب ناقص','تحتاج 100 ذهب'); }}
      else if (kind==='attack'){{ alert2('⚔️ هجوم','جيشك يتقدم'); }}
    }}
  }};
  setInterval(()=>{{ state.gold+=5; state.wood+=3; state.food+=4; state.stone+=2; upd(); }}, 3000);
  upd();
}})();
</script>
</body>
</html>"""


# ============== ELEMENT SVG LIBRARY (for designer + renderer) ==============
def _element_svg(etype: str, props: Optional[dict] = None) -> str:
    """Return the raw SVG markup for a given element type.
    Stays in sync with the Designer UI on the frontend."""
    props = props or {}
    v = props.get("variant", 0)
    color = props.get("color")

    if etype == "castle":
        return """<svg viewBox="0 0 120 110"><defs><linearGradient id="cgR" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#A08060"/><stop offset="100%" stop-color="#7A6040"/></linearGradient></defs><rect x="25" y="45" width="70" height="55" fill="url(#cgR)" rx="3"/><rect x="10" y="28" width="18" height="72" fill="#8B7355"/><rect x="92" y="28" width="18" height="72" fill="#8B7355"/><rect x="48" y="22" width="24" height="78" fill="#9B8465"/><polygon points="10,28 19,10 28,28" fill="#C41E3A"/><polygon points="92,28 101,10 110,28" fill="#C41E3A"/><polygon points="48,22 60,5 72,22" fill="#C41E3A"/><rect x="50" y="62" width="20" height="38" fill="#4A3322" rx="10 10 0 0"/><rect x="30" y="52" width="12" height="12" fill="#87CEEB" rx="2"/><rect x="78" y="52" width="12" height="12" fill="#87CEEB" rx="2"/><polygon points="54,8 63,0 72,8" fill="#FFD700"/></svg>"""
    if etype == "house":
        colors = [('#D4A574','#8B4513'), ('#C49464','#7A3A12'), ('#B88454','#6B3010'), ('#DDB584','#9B5523')]
        c, r = colors[v % 4]
        return f"""<svg viewBox="0 0 80 70"><rect x="10" y="35" width="60" height="35" fill="{c}" rx="2"/><polygon points="5,35 40,12 75,35" fill="{r}"/><rect x="30" y="45" width="14" height="25" fill="#4A3322" rx="5 5 0 0"/><rect x="13" y="40" width="11" height="10" fill="#87CEEB" rx="1"/><rect x="56" y="40" width="11" height="10" fill="#87CEEB" rx="1"/><rect x="62" y="16" width="6" height="19" fill="#8B7355"/></svg>"""
    if etype == "tree":
        greens = ['#2D8B2D', '#1E7A1E', '#3AA63A', '#228B22']
        g1 = color or greens[v % 4]
        g2 = greens[(v + 1) % 4]
        return f"""<svg viewBox="0 0 60 80"><rect x="25" y="52" width="10" height="23" fill="#6B4226" rx="3"/><ellipse cx="30" cy="35" rx="24" ry="26" fill="{g1}"/><ellipse cx="22" cy="30" rx="14" ry="16" fill="{g2}" opacity="0.9"/><ellipse cx="38" cy="32" rx="13" ry="15" fill="{g1}" opacity="0.85"/></svg>"""
    if etype == "wheat_field":
        return """<svg viewBox="0 0 90 60"><rect x="5" y="15" width="80" height="40" fill="#8B6914" rx="4"/><line x1="5" y1="25" x2="85" y2="25" stroke="#6B4F12" stroke-width="1"/><line x1="5" y1="35" x2="85" y2="35" stroke="#6B4F12" stroke-width="1"/><line x1="5" y1="45" x2="85" y2="45" stroke="#6B4F12" stroke-width="1"/><rect x="12" y="18" width="3" height="12" fill="#228B22"/><rect x="22" y="18" width="3" height="14" fill="#228B22"/><rect x="32" y="18" width="3" height="11" fill="#228B22"/><rect x="42" y="18" width="3" height="13" fill="#228B22"/><rect x="52" y="18" width="3" height="12" fill="#228B22"/><rect x="62" y="18" width="3" height="14" fill="#228B22"/><rect x="72" y="18" width="3" height="11" fill="#228B22"/><circle cx="22" cy="16" r="4" fill="#FFD700"/><circle cx="42" cy="16" r="4" fill="#FFD700"/><circle cx="62" cy="16" r="4" fill="#FFD700"/></svg>"""
    if etype == "clay_field":
        return """<svg viewBox="0 0 90 60"><rect x="5" y="15" width="80" height="40" fill="#C08060" rx="4"/><ellipse cx="20" cy="35" rx="10" ry="6" fill="#A56040" opacity=".6"/><ellipse cx="55" cy="40" rx="12" ry="7" fill="#9F5030" opacity=".55"/><ellipse cx="72" cy="28" rx="8" ry="5" fill="#B87858" opacity=".5"/><circle cx="30" cy="28" r="3" fill="#6D4025"/><circle cx="62" cy="50" r="3" fill="#6D4025"/><circle cx="15" cy="48" r="2.5" fill="#6D4025"/></svg>"""
    if etype == "farm":
        return _element_svg("wheat_field")
    if etype == "soldier":
        return """<svg viewBox="0 0 40 60"><circle cx="20" cy="12" r="8" fill="#FDBCB4"/><rect x="12" y="20" width="16" height="20" fill="#C41E3A" rx="3"/><rect x="7" y="22" width="7" height="14" fill="#A01030" rx="2"/><rect x="26" y="22" width="7" height="14" fill="#A01030" rx="2"/><rect x="14" y="40" width="5" height="14" fill="#4A3728" rx="2"/><rect x="21" y="40" width="5" height="14" fill="#4A3728" rx="2"/><ellipse cx="20" cy="5" rx="10" ry="4" fill="#808080"/><circle cx="16" cy="10" r="1.5" fill="#333"/><circle cx="24" cy="10" r="1.5" fill="#333"/></svg>"""
    if etype == "mine":
        return """<svg viewBox="0 0 80 60"><polygon points="20,55 40,15 60,55" fill="#696969"/><polygon points="10,55 25,25 40,55" fill="#808080"/><polygon points="45,55 60,20 75,55" fill="#A9A9A9"/><rect x="35" y="30" width="5" height="20" fill="#6B4226"/><polygon points="32,30 40,18 48,30" fill="#555"/><circle cx="28" cy="42" r="4" fill="#FFD700"/><circle cx="55" cy="48" r="3" fill="#FFD700"/></svg>"""
    if etype == "rock":
        return """<svg viewBox="0 0 40 30"><polygon points="8,28 20,8 35,28" fill="#808080"/><polygon points="2,28 12,15 22,28" fill="#696969"/></svg>"""
    if etype == "flower":
        cols = ['#FF6B6B', '#FFD700', '#FF69B4', '#9370DB', '#FF8C00']
        cl = color or cols[v % 5]
        return f"""<svg viewBox="0 0 20 25"><rect x="9" y="12" width="2" height="13" fill="#228B22"/><circle cx="10" cy="9" r="5" fill="{cl}"/><circle cx="10" cy="9" r="2.5" fill="#FFD700"/></svg>"""
    if etype == "bush":
        return """<svg viewBox="0 0 40 25"><ellipse cx="20" cy="15" rx="18" ry="10" fill="#2D8B2D"/><ellipse cx="12" cy="13" rx="10" ry="8" fill="#3AA63A"/><ellipse cx="28" cy="14" rx="9" ry="7" fill="#248F24"/></svg>"""
    if etype == "cloud":
        return """<svg viewBox="0 0 120 45"><ellipse cx="60" cy="28" rx="50" ry="16" fill="white" opacity=".9"/><ellipse cx="35" cy="22" rx="30" ry="14" fill="white" opacity=".92"/><ellipse cx="85" cy="24" rx="28" ry="12" fill="white" opacity=".88"/></svg>"""
    if etype == "pond":
        return """<svg viewBox="0 0 80 50"><ellipse cx="40" cy="25" rx="38" ry="22" fill="#4DA6FF"/><ellipse cx="40" cy="22" rx="32" ry="17" fill="#87CEEB" opacity=".6"/><circle cx="25" cy="18" r="2" fill="white" opacity=".8"/><circle cx="52" cy="30" r="1.5" fill="white" opacity=".7"/></svg>"""
    if etype == "circle":
        cl = color or "#FFD700"
        return f"""<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="{cl}"/></svg>"""
    if etype == "rect":
        cl = color or "#4a3aff"
        return f"""<svg viewBox="0 0 100 100"><rect x="0" y="0" width="100" height="100" fill="{cl}" rx="8"/></svg>"""
    if etype == "text":
        txt = (props.get("text") or "نص").replace('<', '&lt;').replace('>', '&gt;')[:40]
        cl = color or "#FFD700"
        size = int(props.get("font_size") or 24)
        return f"""<svg viewBox="0 0 200 40"><text x="100" y="26" text-anchor="middle" font-family="Tajawal,sans-serif" font-size="{size}" fill="{cl}" font-weight="900">{txt}</text></svg>"""
    if etype == "star":
        return """<svg viewBox="0 0 50 50"><polygon points="25,3 31,18 48,19 35,30 39,47 25,38 11,47 15,30 2,19 19,18" fill="#FFD700" stroke="#B8860B" stroke-width="1.5"/></svg>"""
    return """<svg viewBox="0 0 100 100"><rect x="5" y="5" width="90" height="90" fill="#888" stroke="#333" stroke-width="2" rx="8"/></svg>"""


def should_override_game_code(code: Optional[str], has_design_image: bool = False) -> bool:
    """Decide if GPT's game output should be replaced by the engine template.

    If the session already has an approved design image, we ALWAYS override —
    because the user explicitly wants the live preview to match that image 1:1,
    and any GPT-generated SVG/Canvas scene will inevitably drift from the image.
    Without a design image, fall back to a quality heuristic.
    """
    # guarantees match-to-design, so we always prefer it.
    if has_design_image:
        # Respect GPT only if it explicitly wired in our engine
        if code and ("game-engine.js" in code or "ZitexGame.init" in code):
            return False
        return True

    if not code:
        return True
    c = code.strip()
    if len(c) < 200:
        return True
    # If GPT already wired in our engine, keep it
    if "game-engine.js" in c or "ZitexGame.init" in c:
        return False
    # Heuristic: simplistic HTML with very few nodes -> weak
    svg_count = c.lower().count("<svg")
    div_count = c.lower().count("<div")
    has_script = "<script" in c.lower()
    has_canvas = "<canvas" in c.lower()
    if not has_script and not has_canvas and svg_count + div_count < 20:
        return True
    # If GPT just dropped raw SVG with no game loop
    if not has_script and not has_canvas:
        return True
    return False


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
                "has_buttons": has_buttons,
                "image_urls": [a["url"] for a in attachments if a.get("type") == "image" and a.get("url")]
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
        
        # First try CODE_BLOCK format with backticks
        code_block_match = re.search(r'\[CODE_BLOCK\]\s*```(?:html|javascript|js)?\n?([\s\S]*?)```\s*\[/CODE_BLOCK\]', ai_response)
        if code_block_match:
            code = code_block_match.group(1).strip()
        else:
            # Try CODE_BLOCK without backticks (direct HTML)
            code_block_match2 = re.search(r'\[CODE_BLOCK\]\s*(<!DOCTYPE[\s\S]*?</html>)\s*\[/CODE_BLOCK\]', ai_response, re.IGNORECASE)
            if code_block_match2:
                code = code_block_match2.group(1).strip()
            else:
                # Try CODE_BLOCK with any content
                code_block_match3 = re.search(r'\[CODE_BLOCK\]\s*([\s\S]*?)\s*\[/CODE_BLOCK\]', ai_response)
                if code_block_match3:
                    code = code_block_match3.group(1).strip()
                    code = re.sub(r'^```(?:html|javascript|js)?\s*', '', code)
                    code = re.sub(r'```\s*$', '', code)
                    code = code.strip()
                else:
                    # Try any tag like [CODES] [CODE] etc
                    alt_match = re.search(r'\[CODE\w*\]\s*(<!DOCTYPE[\s\S]*?</html>)\s*\[/CODE\w*\]', ai_response, re.IGNORECASE)
                    if alt_match:
                        code = alt_match.group(1).strip()
                    else:
                        # Try raw HTML without any tags
                        raw_match = re.search(r'(<!DOCTYPE\s+html[\s\S]*?</html>)', ai_response, re.IGNORECASE)
                        if raw_match:
                            code = raw_match.group(1).strip()
                        else:
                            # Fall back to regular code block
                            code_match = re.search(r'```(?:html|javascript|js)?\n?([\s\S]*?)```', ai_response)
                            if code_match:
                                code = code_match.group(1).strip()
        
        if code:
            # === FORCE GAME ENGINE OVERRIDE ===
            # For game requests, guarantee a real playable game by injecting the Zitex engine template
            # whenever GPT's output is weak (short, no <script>, basic SVG scene, etc.).
            if request_type in ("game", "game_3d"):
                try:
                    # Look up the latest design image from the session (may have been saved earlier in this turn)
                    fresh = await self.db.chat_sessions.find_one({"id": session_id}, {"_id": 0, "project_data": 1}) or {}
                    design_url = (fresh.get("project_data") or {}).get("last_design_image") \
                                 or (session.get("project_data") or {}).get("last_design_image")
                    if should_override_game_code(code, has_design_image=bool(design_url)):
                        # Build full conversational context for genre detection
                        ctx_text = ""
                        for m in session.get("messages", [])[-10:]:
                            ctx_text += " " + (m.get("content") or "")
                        genre = detect_game_genre_prioritized(primary=message, context=ctx_text, fallback="strategy")
                        title = session.get("title") or "لعبة Zitex"
                        overridden = build_game_html(genre=genre, title=title, hint=message[:400], design_image_url=design_url)
                        logger.info(f"GAME OVERRIDE: genre={genre}, original_len={len(code)}, new_len={len(overridden)}")
                        code = overridden
                        # Surface a friendly note to the user about auto-boosting
                        ai_response = ai_response + f"\n\n✨ تم تفعيل محرك Zitex للألعاب تلقائياً (نوع: {genre}) لضمان لعبة كاملة وقابلة للعب."
                        assistant_msg["content"] = ai_response
                except Exception as ge:
                    logger.error(f"Game override failed: {ge}")

            code_with_badge = inject_zitex_badge(code)
            update_data["$set"]["generated_code"] = code_with_badge
            # Store code in metadata for frontend to use
            assistant_msg["metadata"]["generated_code"] = code_with_badge
            assistant_msg["metadata"]["has_preview"] = True
            logger.info(f"CODE EXTRACTED: {len(code)} chars, saved to session")
        else:
            # Debug: log why code wasn't found
            has_doctype = '<!DOCTYPE' in ai_response
            has_codeblock = '[CODE_BLOCK]' in ai_response
            has_codetag = '[CODE' in ai_response
            logger.warning(f"NO CODE EXTRACTED from response. has_doctype={has_doctype}, has_codeblock={has_codeblock}, has_codetag={has_codetag}, response_len={len(ai_response)}")

            # === GAME FALLBACK ===
            # If user clearly approved building a game but GPT failed to emit code, build the
            # engine-backed game ourselves so the live preview is never empty for games.
            if request_type in ("game", "game_3d"):
                approval_hits = ["ممتاز", "رائع", "حلو", "جميل", "موافق", "ابنِ", "ابن", "كمّل", "كمل", "المرحلة التالية", "ابدأ", "تمام", "اوكي", "ok", "yes", "نعم"]
                msg_lower = message.lower()
                is_approval = any(w.lower() in msg_lower for w in approval_hits)
                if is_approval:
                    try:
                        ctx_text = ""
                        for m in session.get("messages", [])[-10:]:
                            ctx_text += " " + (m.get("content") or "")
                        genre = detect_game_genre_prioritized(primary=message, context=ctx_text, fallback="strategy")
                        title = session.get("title") or "لعبة Zitex"
                        fresh = await self.db.chat_sessions.find_one({"id": session_id}, {"_id": 0, "project_data": 1}) or {}
                        design_url = (fresh.get("project_data") or {}).get("last_design_image") \
                                     or (session.get("project_data") or {}).get("last_design_image")
                        generated = build_game_html(genre=genre, title=title, hint=message[:400], design_image_url=design_url)
                        code_with_badge = inject_zitex_badge(generated)
                        update_data["$set"]["generated_code"] = code_with_badge
                        assistant_msg["metadata"]["generated_code"] = code_with_badge
                        assistant_msg["metadata"]["has_preview"] = True
                        ai_response = ai_response + f"\n\n✨ تم بناء اللعبة تلقائياً باستخدام محرك Zitex (نوع: {genre}). شوف المعاينة!"
                        assistant_msg["content"] = ai_response
                        code = generated
                        logger.info(f"GAME FALLBACK TRIGGERED: genre={genre}, code_len={len(generated)}")
                    except Exception as ge:
                        logger.error(f"Game fallback failed: {ge}")
        
        result = await self.db.chat_sessions.update_one({"id": session_id}, update_data)
        logger.info(f"Session update: matched={result.matched_count}, modified={result.modified_count}")
        
        # === SELF-LEARNING SYSTEM ===
        await self._auto_learn(session_id, user_id, message, ai_response, code, request_type, session)
        
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
    
    # ============== SELF-LEARNING SYSTEM ==============
    
    APPROVAL_WORDS = ["ممتاز", "رائع", "حلو", "جميل", "موافق", "ابنِ", "كمّل", "المرحلة التالية", "ابدأ", "تمام", "اوكي", "ok", "great", "perfect", "عظيم", "يجنن"]
    REJECTION_WORDS = ["عدّل", "غيّر", "ما عجبني", "سيء", "بشع", "خطأ", "مو كذا", "غلط", "لا", "ما يصلح", "ضعيف", "بدائي"]
    
    async def _auto_learn(self, session_id: str, user_id: str, user_message: str, ai_response: str, code: Optional[str], request_type: str, session: Dict):
        """Self-learning: analyze user feedback and auto-save successful patterns"""
        try:
            msg_lower = user_message.lower().strip()
            
            # 1. Detect approval words
            is_approval = any(word in msg_lower for word in self.APPROVAL_WORDS)
            is_rejection = any(word in msg_lower for word in self.REJECTION_WORDS)
            
            # Get the previous code from session (the one built before this message)
            prev_code = session.get("generated_code")
            
            # If user approved AND there's existing code, save it
            if is_approval and prev_code and len(prev_code) > 500:
                await self._save_successful_project(session, prev_code, request_type, user_message)
            
            # If new code was just generated in THIS response, track quality
            if code and len(code) > 500:
                await self._track_generated_code(session_id, code, request_type)
                
                # Also save the new code if user gave approval in same message (like "ممتاز ابنِ الكود")
                if is_approval:
                    await self._save_successful_project(session, code, request_type, user_message)
            
            # Learn from rejection
            if is_rejection:
                await self._learn_from_rejection(session, user_message, request_type)
            
        except Exception as e:
            logger.error(f"Auto-learn error: {e}")
    
    async def _save_successful_project(self, session: Dict, code: str, request_type: str, approval_msg: str):
        """Auto-save approved code as a training example"""
        try:
            # Check if already saved
            title = session.get("title", "مشروع بدون عنوان")
            existing = await self.db.training_examples.find_one({"title": title, "source": "auto_learned"})
            if existing:
                return
            
            # Determine category
            cat_map = {"game": "game", "game_3d": "game", "website": "website", "webapp": "website", "mobile": "mobile"}
            category = cat_map.get(request_type, "website")
            
            example = {
                "id": str(uuid.uuid4()),
                "category": category,
                "subcategory": "",
                "title": title,
                "description": f"تم اعتماده تلقائياً - رد العميل: {approval_msg[:100]}",
                "design_image_url": "",
                "html_code": code[:15000],
                "tags": [category, "auto-learned", "client-approved"],
                "is_active": True,
                "usage_count": 0,
                "source": "auto_learned",
                "quality_score": 8,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await self.db.training_examples.insert_one(example)
            logger.info(f"Auto-learned: saved approved project '{title}' as training example")
        except Exception as e:
            logger.error(f"Save successful project error: {e}")
    
    async def _learn_from_rejection(self, session: Dict, rejection_msg: str, request_type: str):
        """Learn from negative feedback - save as knowledge rule"""
        try:
            # Extract the insight from rejection
            insight = {
                "id": str(uuid.uuid4()),
                "type": "rejection_pattern",
                "category": request_type,
                "user_feedback": rejection_msg[:500],
                "session_title": session.get("title", ""),
                "lesson": "",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Auto-categorize the rejection
            msg = rejection_msg.lower()
            if any(w in msg for w in ["لون", "ألوان", "غامق", "فاتح", "داكن"]):
                insight["lesson"] = "العميل غير راضي عن الألوان - يجب تنويع التدرجات"
                insight["rule_type"] = "colors"
            elif any(w in msg for w in ["بسيط", "بدائي", "ضعيف", "فاضي"]):
                insight["lesson"] = "الكود بسيط جداً - يجب إضافة تفاصيل وتأثيرات أكثر"
                insight["rule_type"] = "complexity"
            elif any(w in msg for w in ["حجم", "كبير", "صغير", "خط"]):
                insight["lesson"] = "مشكلة في الأحجام والخطوط"
                insight["rule_type"] = "sizing"
            elif any(w in msg for w in ["ما يشتغل", "خطأ", "خربان", "ما يتحرك"]):
                insight["lesson"] = "الكود فيه أخطاء تقنية - يجب اختبار JavaScript"
                insight["rule_type"] = "bugs"
            else:
                insight["lesson"] = f"عدم رضا: {rejection_msg[:200]}"
                insight["rule_type"] = "general"
            
            await self.db.knowledge_base.insert_one(insight)
            logger.info(f"Learned from rejection: {insight['rule_type']}")
        except Exception as e:
            logger.error(f"Learn from rejection error: {e}")
    
    async def _track_generated_code(self, session_id: str, code: str, request_type: str):
        """Track generated code for quality analysis"""
        try:
            # Simple quality scoring
            score = 0
            if "cdn.tailwindcss.com" in code: score += 2
            if "font-awesome" in code.lower(): score += 1
            if "gradient" in code: score += 1
            if "hover:" in code: score += 1
            if "transition" in code or "animation" in code: score += 1
            if "addEventListener" in code or "onclick" in code.lower(): score += 1
            if len(code) > 3000: score += 1
            if "responsive" in code.lower() or "md:" in code: score += 1
            if "Tajawal" in code: score += 1
            
            await self.db.code_quality_log.insert_one({
                "session_id": session_id,
                "request_type": request_type,
                "code_length": len(code),
                "quality_score": score,
                "max_score": 10,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error(f"Track code error: {e}")
    
    async def _get_knowledge_rules(self, request_type: str) -> str:
        """Fetch accumulated knowledge rules for the prompt"""
        try:
            # Get top insights from knowledge base
            rules = await self.db.knowledge_base.find(
                {"category": {"$in": [request_type, "general"]}},
                {"_id": 0, "lesson": 1, "rule_type": 1}
            ).sort("created_at", -1).limit(10).to_list(10)
            
            if not rules:
                return ""
            
            # Deduplicate by rule_type
            seen_types = set()
            unique_rules = []
            for r in rules:
                rt = r.get("rule_type", "general")
                if rt not in seen_types:
                    seen_types.add(rt)
                    unique_rules.append(r["lesson"])
            
            if not unique_rules:
                return ""
            
            rules_text = "\n\n## قواعد مستفادة من تجارب سابقة (مهم - تعلّمتها من ملاحظات العملاء):\n"
            for i, rule in enumerate(unique_rules, 1):
                rules_text += f"{i}. {rule}\n"
            
            return rules_text
        except Exception as e:
            logger.error(f"Get knowledge rules error: {e}")
            return ""
    
    async def get_learning_stats(self) -> Dict:
        """Get self-learning statistics"""
        try:
            auto_learned = await self.db.training_examples.count_documents({"source": "auto_learned", "is_active": True})
            knowledge_rules = await self.db.knowledge_base.count_documents({})
            quality_logs = await self.db.code_quality_log.count_documents({})
            
            # Average quality score
            avg_quality = 0
            if quality_logs > 0:
                pipeline = [{"$group": {"_id": None, "avg": {"$avg": "$quality_score"}}}]
                result = await self.db.code_quality_log.aggregate(pipeline).to_list(1)
                if result:
                    avg_quality = round(result[0]["avg"], 1)
            
            return {
                "auto_learned_examples": auto_learned,
                "knowledge_rules": knowledge_rules,
                "total_generations": quality_logs,
                "avg_quality_score": avg_quality,
                "max_quality_score": 10
            }
        except Exception as e:
            logger.error(f"Learning stats error: {e}")
            return {}
    
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
        
        # معالجة أمر توليد صورة تصميم [DESIGN_IMAGE]
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
                    
                    # Persist the latest design image so the game template can use it as background
                    try:
                        await self.db.chat_sessions.update_one(
                            {"id": session_id},
                            {"$set": {
                                "project_data.last_design_image": design_url,
                                "project_data.last_design_prompt": design_prompt,
                            }}
                        )
                    except Exception as _e:
                        logger.warning(f"Failed to persist last_design_image: {_e}")
                    
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
            size = video_match.group(6).strip() if video_match.group(6) else "1280x720"
            
            # حساب التكلفة
            cost_key = f"video_{video_type}_{duration}"
            video_cost = SERVICE_COSTS.get(cost_key, 60)
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
        
        # معالجة أمر الاستيحاء من صورة [IMAGE_INSPIRE]
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
        
        # معالجة أمر تعديل صورة [IMAGE_EDIT]
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
            
            # Download reference image and analyze it with vision
            ref_description = ""
            try:
                ref_resp = requests.get(reference_url, timeout=15)
                if ref_resp.status_code == 200:
                    ref_b64 = base64.b64encode(ref_resp.content).decode('utf-8')
                    # Use GPT-4o to describe the reference image
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
            
            # Generate new image inspired by the reference
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
                    return f"{BACKEND_URL}/api/storage/images/{image_id}.png"
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
            
            # Describe original image first
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
            
            # Generate edited version
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
                    return f"{BACKEND_URL}/api/storage/images/{image_id}.png"
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
            
            # Ensure duration is valid (4, 8, or 12)
            valid_durations = [4, 8, 12]
            if duration not in valid_durations:
                duration = min(valid_durations, key=lambda x: abs(x - duration))
            
            # Ensure size is valid
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
                # رفع الفيديو إلى Object Storage
                video_id = str(uuid.uuid4())
                video_path = f"{APP_NAME}/videos/{user_id}/{video_id}.mp4"
                
                upload_result = upload_to_storage(video_path, video_bytes, "video/mp4")
                
                if upload_result:
                    video_url = f"{BACKEND_URL}/api/storage/videos/{user_id}/{video_id}.mp4"
                    
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
                    image_url = f"{BACKEND_URL}/api/storage/images/{image_id}.png"
                    return image_url
                else:
                    # إذا فشل الرفع، إرجاع base64
                    image_base64 = base64.b64encode(images[0]).decode('utf-8')
                    return f"data:image/png;base64,{image_base64}"
            
            return None
            
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return None
    
    async def _get_training_examples(self, request_type: str, message: str) -> str:
        """Fetch relevant training examples for few-shot learning"""
        try:
            # Map request types to categories
            category_map = {
                "game": "game", "game_3d": "game",
                "website": "website", "webapp": "website",
                "image": None, "video": None,
                "mobile": "mobile"
            }
            category = category_map.get(request_type)
            if not category:
                return ""
            
            # Find matching examples
            query = {"is_active": True, "category": category}
            
            # Try to find subcategory match from message
            subcategories = {
                "game": ["استراتيجية", "أكشن", "سباق", "ألغاز", "مطعم", "أطفال", "strategy", "action", "racing", "puzzle", "restaurant"],
                "website": ["شركة", "متجر", "مدونة", "هبوط", "بورتفوليو", "company", "shop", "blog", "landing", "portfolio"],
            }
            
            for sub in subcategories.get(category, []):
                if sub in message.lower():
                    query["$or"] = [{"subcategory": sub}, {"tags": sub}]
                    break
            
            examples = await self.db.training_examples.find(
                query, {"_id": 0, "html_code": 1, "title": 1, "category": 1, "subcategory": 1}
            ).sort("usage_count", -1).limit(2).to_list(2)
            
            if not examples:
                # Fallback: get any example from this category
                examples = await self.db.training_examples.find(
                    {"is_active": True, "category": category},
                    {"_id": 0, "html_code": 1, "title": 1}
                ).limit(1).to_list(1)
            
            if not examples:
                return ""
            
            # Build examples context (limit code to 3000 chars each to save tokens)
            examples_text = "\n\n## أمثلة مرجعية لجودة الكود المطلوبة (التزم بنفس المستوى أو أفضل):\n"
            for i, ex in enumerate(examples):
                code = ex.get("html_code", "")[:3000]
                examples_text += f"\nمثال {i+1} - {ex.get('title', '')}:\n[CODE_BLOCK]\n{code}\n[/CODE_BLOCK]\n"
                # Update usage count
                await self.db.training_examples.update_one(
                    {"title": ex.get("title")},
                    {"$inc": {"usage_count": 1}}
                )
            
            examples_text += "\nالتزم بنفس مستوى الجودة والتفاصيل في الأمثلة أعلاه. لا تبنِ كود أبسط منها.\n"
            return examples_text
            
        except Exception as e:
            logger.error(f"Training examples error: {e}")
            return ""
    
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
        
        # Add training examples for few-shot learning
        training_context = await self._get_training_examples(request_type, message)
        if training_context:
            system_prompt += training_context
        
        # Add accumulated knowledge rules from user feedback
        knowledge_rules = await self._get_knowledge_rules(request_type)
        if knowledge_rules:
            system_prompt += knowledge_rules
        
        # Extract image URLs from message
        image_urls = re.findall(r'(https?://\S+\.(?:png|jpg|jpeg|gif|webp))', message, re.IGNORECASE)
        # Also check for objstore URLs
        image_urls += re.findall(r'(https?://integrations\.emergentagent\.com/objstore/\S+)', message)
        
        # KEY FEATURE: When user approves design (says ممتاز/ابنِ), find the last design image
        # and attach it so GPT-4o can SEE the design and build code that matches it
        is_build_request = any(w in message.lower() for w in ["ممتاز", "ابنِ", "ابني", "ابن", "الكود", "موافق", "نعم ابدأ"])
        if is_build_request and not image_urls:
            # Find the most recent design image from session attachments
            for msg in reversed(session.get("messages", [])):
                if msg.get("attachments"):
                    for att in msg["attachments"]:
                        if att.get("type") == "image" and att.get("url") and att.get("image_type") == "design_mockup":
                            design_url = att["url"]
                            # Convert relative URL to full URL
                            if design_url.startswith("/api/"):
                                design_url = f"{BACKEND_URL}{design_url}" if BACKEND_URL else design_url
                            image_urls.append(design_url)
                            logger.info(f"Auto-attached design image for code building: {design_url[:80]}")
                            break
                if msg.get("metadata", {}).get("image_urls"):
                    for img_url in msg["metadata"]["image_urls"]:
                        image_urls.append(img_url)
                        logger.info(f"Auto-attached design image from metadata: {img_url[:80]}")
                        break
                if image_urls:
                    break
        
        # Build conversation history (strip base64 data to avoid token explosion)
        conversation_history = ""
        for msg in session.get("messages", [])[-8:]:
            role_label = "المستخدم" if msg["role"] == "user" else "زيتكس"
            msg_content = msg['content']
            # Remove base64 image data from message content
            msg_content = re.sub(r'data:image/[^;]+;base64,[A-Za-z0-9+/=]+', '[صورة مرفقة]', msg_content)
            # Remove very long code blocks from history (keep first 500 chars)
            if '[CODE_BLOCK]' in msg_content:
                msg_content = re.sub(r'\[CODE_BLOCK\][\s\S]*?\[/CODE_BLOCK\]', '[CODE_BLOCK]...كود تم بناؤه...[/CODE_BLOCK]', msg_content)
            # Limit each message to 2000 chars max
            if len(msg_content) > 2000:
                msg_content = msg_content[:2000] + "...[تم اختصار الرسالة]"
            conversation_history += f"\n{role_label}: {msg_content}\n"
            # Include image URLs from attachments so AI can reference them
            if msg.get("metadata", {}).get("image_urls"):
                for img_url in msg["metadata"]["image_urls"]:
                    conversation_history += f"[صورة مولّدة: {img_url}]\n"
            elif msg.get("attachments"):
                for att in msg["attachments"]:
                    if att.get("type") == "image" and att.get("url"):
                        conversation_history += f"[صورة مولّدة: {att['url']}]\n"
        
        # Clean base64 from current message too
        clean_message = re.sub(r'data:image/[^;]+;base64,[A-Za-z0-9+/=]+', '[صورة مرفقة]', message)
        
        # If building code and design image is attached, add instruction to match it
        if is_build_request and image_urls:
            clean_message += "\n\n[تعليمة مهمة: الصورة المرفقة هي التصميم المعتمد. ابنِ كود HTML يطابق هذا التصميم بالضبط - نفس الألوان، نفس التخطيط، نفس العناصر، نفس الأسلوب. انظر للصورة بعناية وطابق كل تفصيلة فيها.]"
        
        full_prompt = f"{conversation_history}\nالمستخدم: {clean_message}"
        
        try:
            # Try Emergent LLM first (preferred)
            if EMERGENT_LLM_AVAILABLE and self.emergent_key:
                chat = LlmChat(
                    api_key=self.emergent_key,
                    session_id=session.get("id", "default"),
                    system_message=system_prompt
                )
                chat.with_model("openai", "gpt-4o")
                
                # Build message with image support
                file_contents = []
                if image_urls:
                    for img_url in image_urls[:3]:  # Max 3 images
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
                    max_tokens=16384
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
        """توليد صوت من النص باستخدام OpenAI TTS"""
        if not text or len(text.strip()) == 0:
            return None
        
        # Limit text length
        text = text[:4000]
        
        # Remove buttons and code blocks from text
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
            type: Phaser.AUTO,
            width: 800,
            height: 600,
            parent: 'game-container',
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
    <div id="controls">استخدم الأسهم للتحكم | ↑ تسريع | ↓ فرامل | → ← التوجيه</div>
    <script>
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x1a1a2e);
        scene.fog = new THREE.Fog(0x1a1a2e, 50, 200);
        
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        document.body.appendChild(renderer.domElement);
        
        // Lights
        const ambient = new THREE.AmbientLight(0x404040, 2);
        scene.add(ambient);
        const directional = new THREE.DirectionalLight(0xffffff, 1);
        directional.position.set(50, 50, 50);
        scene.add(directional);
        
        // Road
        const roadGeo = new THREE.PlaneGeometry(20, 1000);
        const roadMat = new THREE.MeshStandardMaterial({ color: 0x333333 });
        const road = new THREE.Mesh(roadGeo, roadMat);
        road.rotation.x = -Math.PI / 2;
        road.position.z = -450;
        scene.add(road);
        
        // Car (simple box for now)
        const carGeo = new THREE.BoxGeometry(2, 1, 4);
        const carMat = new THREE.MeshStandardMaterial({ color: 0xffd700 });
        const car = new THREE.Mesh(carGeo, carMat);
        car.position.y = 0.5;
        scene.add(car);
        
        // Trees
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
        """نشر المشروع على نطاق فرعي مع استضافة حقيقية"""
        import re
        
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
        
        # Upload to Object Storage for real hosting
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
            {"_id": 0, "code": 0}
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
