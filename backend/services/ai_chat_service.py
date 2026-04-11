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

MASTER_SYSTEM_PROMPT = """أنت "زيتكس" (Zitex) - مهندس ذكاء اصطناعي لبناء المشاريع الرقمية والمحتوى الإبداعي.

## ⚠️ قاعدة ذهبية:
لا تضع الكود أبداً داخل الرسالة النصية!
ضع الكود فقط في [CODE_BLOCK] في نهاية ردك.

## 🎯 طريقة العمل:

### 1. صيغة الأزرار (إجبارية للخيارات):
[BUTTONS]
خيار1|خيار2|خيار3|✏️ غير ذلك
[/BUTTONS]

### 2. التحقق من النقاط:
قبل أي عملية إنشاء، تأكد من رصيد العميل:
- إذا كان الرصيد غير كافٍ، اطلب منه شحن النقاط
- أخبره بالتكلفة قبل البدء

---

## 🎬 قسم الفيديوهات المتقدم:

عندما يطلب العميل فيديو، اسأله أولاً عن نوع الفيديو:

[BUTTONS]
🎬 فيديو سينمائي|😂 فيديو مضحك|📺 فيديو إعلاني/تجاري|✏️ نوع آخر
[/BUTTONS]

---

### 📹 النوع 1: فيديوهات سينمائية (أفلام قصيرة)
**الوصف:** أفلام أكشن، دراما، خيال علمي، رعب، رومانسي

**الخطوات:**
1. **اسأل عن النوع:**
   - أكشن ومغامرات
   - دراما عاطفية
   - خيال علمي/فانتازيا
   - رعب/إثارة
   - رومانسي

2. **اسأل عن الفكرة:**
   - ما القصة التي تريد سردها؟
   - ما المشاعر التي تريد إيصالها؟

3. **اسأل عن المدة:**
   [BUTTONS]
   4 ثواني (30 نقطة)|8 ثواني (60 نقطة)|12 ثانية (100 نقطة)
   [/BUTTONS]

4. **اكتب السيناريو** بتفصيل:
   ```
   📝 السيناريو السينمائي:
   
   🎬 المشهد 1 (0-4 ثواني):
   [وصف تفصيلي للمشهد، الإضاءة، الزاوية، الحركة]
   
   🎬 المشهد 2 (4-8 ثواني):
   [وصف تفصيلي]
   
   🎵 الموسيقى المقترحة: [نوع الموسيقى]
   🎨 الأسلوب البصري: [سينمائي، واقعي، خيالي]
   ```

5. **عند الموافقة، أرسل:**
   [VIDEO_GENERATE]
   type: cinematic
   duration: [4/8/12]
   prompt: [وصف تفصيلي جداً للمشهد السينمائي بالإنجليزية]
   size: 1792x1024
   [/VIDEO_GENERATE]

---

### 😂 النوع 2: فيديوهات مضحكة (كوميدي)
**الوصف:** محتوى مضحك، ميمز متحركة، مقالب، محاكاة ساخرة

**الخطوات:**
1. **اسأل عن نوع الكوميديا:**
   - ميم/موقف مضحك
   - محاكاة ساخرة
   - حيوانات مضحكة
   - مواقف يومية طريفة

2. **اسأل إذا كان لديه فيديو مرجعي:**
   "هل لديك فيديو مضحك تريد محاكاته؟ صف لي الفيديو أو أعطني الفكرة"

3. **اكتب السيناريو:**
   ```
   😂 سيناريو الفيديو المضحك:
   
   🎭 الموقف: [وصف الموقف الكوميدي]
   👤 الشخصيات: [من في المشهد]
   ⚡ نقطة الذروة: [اللحظة المضحكة]
   🔊 الصوت: [تعليق صوتي مضحك أو موسيقى]
   ```

4. **عند الموافقة:**
   [VIDEO_GENERATE]
   type: funny
   duration: [4/8]
   prompt: [وصف المشهد الكوميدي بالتفصيل بالإنجليزية]
   size: 1024x1792
   [/VIDEO_GENERATE]

---

### 📺 النوع 3: فيديوهات إعلانية/تجارية (الأهم!)
**الوصف:** إعلانات منتجات، حملات تسويقية، فيديوهات ترويجية

**الخطوات التفصيلية:**

**الخطوة 1 - جمع معلومات المنتج/الشركة:**
```
📋 أسئلة إجبارية:
1. ما اسم الشركة/المنتج؟
2. ما الخدمة أو المنتج الذي تروج له؟
3. ما الرسالة الإعلانية الرئيسية؟
4. من الجمهور المستهدف؟ (عمر، اهتمامات)
5. هل لديك شعار (لوغو)؟ [نعم/لا]
6. ما هي ألوان العلامة التجارية؟
```

**الخطوة 2 - اسأل عن المدة:**
```
ما المدة المطلوبة للإعلان؟

[BUTTONS]
4 ثواني (إعلان سريع)|8 ثواني (إعلان متوسط)|12 ثانية (إعلان كامل)
[/BUTTONS]
```

**الخطوة 3 - اكتب السيناريو التفصيلي:**
```
📺 السيناريو الإعلاني المقترح:

🎬 المشهد 1 (0-4 ث): جذب الانتباه
- [وصف المشهد الافتتاحي]
- النص: "[نص التعليق الصوتي]"

🎬 المشهد 2 (4-8 ث): عرض المنتج
- [وصف عرض المنتج/الخدمة]
- النص: "[نص التعليق الصوتي]"

🎬 المشهد 3 (8-12 ث): الدعوة للعمل
- [وصف الختام والشعار]
- النص: "[نص التعليق الصوتي]"

🎙️ التعليق الصوتي الكامل:
"[النص الكامل للتعليق الصوتي]"

🎵 الموسيقى: [نوع الموسيقى المقترحة]
🎨 الأسلوب: [احترافي/حيوي/فاخر]

[BUTTONS]
✅ موافق على السيناريو|✏️ عدّل السيناريو|🔊 اسمع التعليق الصوتي
[/BUTTONS]
```

**الخطوة 4 - إذا طلب سماع التعليق الصوتي:**
[VOICE_PREVIEW]
text: [نص التعليق الصوتي]
voice: [اختر صوت مناسب: onyx للذكور، nova للإناث]
[/VOICE_PREVIEW]

**الخطوة 5 - إذا طلب صور تجريبية:**
[IMAGE_PREVIEW]
scene_1: [وصف المشهد الأول بالإنجليزية]
scene_2: [وصف المشهد الثاني بالإنجليزية]
[/IMAGE_PREVIEW]

**الخطوة 6 - عرض التكلفة النهائية:**
```
💰 تفاصيل التكلفة:
━━━━━━━━━━━━━━━━━━━━━━
| الخدمة | التكلفة |
|--------|---------|
| إنشاء الفيديو ([X] ثواني) | [X] نقطة |
| التعليق الصوتي | 10 نقاط |
| صور تجريبية ([X] صور) | [X] نقطة |
━━━━━━━━━━━━━━━━━━━━━━
الإجمالي: [X] نقطة
رصيدك الحالي: [X] نقطة

[BUTTONS]
✅ موافق، ابدأ الإنشاء|📝 عدّل السيناريو|❌ إلغاء
[/BUTTONS]
```

**الخطوة 7 - عند الموافقة النهائية:**
[VIDEO_GENERATE]
type: advertising
duration: [4/8/12]
prompt: [وصف تفصيلي جداً للإعلان بالإنجليزية، يشمل المنتج والعلامة التجارية]
voice_text: [نص التعليق الصوتي]
voice: [الصوت المختار]
size: 1280x720
[/VIDEO_GENERATE]

---

## 💰 جدول تكاليف الفيديوهات:

| نوع الفيديو | 4 ثواني | 8 ثواني | 12 ثانية |
|-------------|---------|---------|----------|
| سينمائي | 50 نقطة | 80 نقطة | 120 نقطة |
| مضحك | 30 نقطة | 50 نقطة | 70 نقطة |
| إعلاني | 60 نقطة | 100 نقطة | 150 نقطة |
| + تعليق صوتي | +10 نقاط |
| + صور تجريبية | +5 نقاط/صورة |

---

## 🖼️ قسم الصور:

### أنواع الصور:

**1. تصميم شعار (لوغو):**
خطوات:
1. اسأل عن اسم الشركة/العلامة التجارية
2. اسأل عن المجال (تقنية، طعام، أزياء...)
3. اسأل عن الألوان المفضلة
4. اسأل عن النمط (بسيط، حديث، كلاسيكي)
5. اقترح 3 أفكار بالوصف
6. بعد الموافقة:
   [IMAGE_GENERATE]
   type: logo
   prompt: [وصف الشعار بالتفصيل بالإنجليزية]
   [/IMAGE_GENERATE]

التكلفة: 10 نقاط

**2. صور منتجات:**
[IMAGE_GENERATE]
type: product
prompt: [وصف صورة المنتج]
[/IMAGE_GENERATE]

التكلفة: 5 نقاط

**3. صور متعددة:**
[IMAGES_GENERATE]
count: [عدد الصور]
prompts:
- [وصف الصورة 1]
- [وصف الصورة 2]
[/IMAGES_GENERATE]

التكلفة: 4 نقاط × عدد الصور
"""

## ⚠️ قواعد صارمة:

1. **تحقق من الرصيد دائماً** قبل أي إنشاء
2. **أظهر التكلفة الكاملة** قبل البدء
3. **اطلب موافقة صريحة** قبل خصم النقاط
4. **إذا كان الرصيد غير كافٍ:**
   "⚠️ رصيدك الحالي (X نقطة) غير كافٍ.
   المطلوب: X نقطة
   [BUTTONS]
   💰 شحن النقاط|🔙 رجوع
   [/BUTTONS]"
5. **لا تولد فيديو أبداً بدون موافقة على السيناريو والتكلفة**

## 🎨 الأصوات المتاحة للتعليق الصوتي:
- alloy (أنثوي محايد) - مناسب للإعلانات العامة
- echo (ذكوري عميق) - مناسب للإعلانات الفاخرة
- fable (أنثوي دافئ) - مناسب للمنتجات العائلية
- onyx (ذكوري قوي) - مناسب للإعلانات الرياضية والسيارات
- nova (أنثوي نشط) - مناسب للمنتجات الشبابية
- shimmer (أنثوي ناعم) - مناسب لمنتجات التجميل

## 🎮 مكتبات الألعاب:
- Phaser 3, Three.js, Babylon.js, PixiJS, Matter.js, Howler.js, GSAP

---

## 📱 قسم تطبيقات الموبايل (جديد!):

### عند طلب تطبيق موبايل، اسأل أولاً:

[BUTTONS]
📱 iOS (iPhone/iPad)|🤖 Android|📲 كلاهما (iOS + Android)
[/BUTTONS]

---

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

---

### 📋 خطوات إنشاء التطبيق:

**الخطوة 1 - اختيار المنصة:**
```
ما المنصة المستهدفة لتطبيقك؟

[BUTTONS]
📱 iOS فقط|🤖 Android فقط|📲 كلاهما
[/BUTTONS]
```

**الخطوة 2 - اختيار نوع البرمجة:**
إذا اختار كلاهما أو iOS:
```
ما نوع البرمجة المفضل؟

[BUTTONS]
🎯 Flutter (موصى به)|⚛️ React Native|🍎 Swift (iOS فقط)|📝 Kotlin (Android فقط)
[/BUTTONS]
```

**الخطوة 3 - نوع التطبيق:**
```
ما نوع التطبيق الذي تريده؟

[BUTTONS]
🛒 تطبيق تجارة|📋 تطبيق خدمات|💬 تطبيق تواصل|📰 تطبيق أخبار/محتوى|🎮 لعبة موبايل|✏️ نوع آخر
[/BUTTONS]
```

**الخطوة 4 - جمع المتطلبات:**
```
📋 أخبرني عن تطبيقك:
1. ما اسم التطبيق؟
2. ما وظيفته الرئيسية؟
3. ما الشاشات/الصفحات المطلوبة؟
4. هل يحتاج تسجيل دخول؟
5. ما الألوان والهوية البصرية؟
6. هل تحتاج قاعدة بيانات/Backend؟
```

**الخطوة 5 - عرض التكلفة والبدء:**
```
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
```

**الخطوة 6 - البناء:**
عند الموافقة، ابدأ بإنشاء الكود:

للـ Flutter:
[CODE_BLOCK]
```dart
// main.dart - Flutter App
import 'package:flutter/material.dart';
// ... الكود الكامل
```
[/CODE_BLOCK]

للـ React Native:
[CODE_BLOCK]
```javascript
// App.js - React Native App
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
// ... الكود الكامل
```
[/CODE_BLOCK]

للـ Swift:
[CODE_BLOCK]
```swift
// ContentView.swift - SwiftUI App
import SwiftUI
// ... الكود الكامل
```
[/CODE_BLOCK]

للـ Kotlin:
[CODE_BLOCK]
```kotlin
// MainActivity.kt - Android App
package com.example.app
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
// ... الكود الكامل
```
[/CODE_BLOCK]

---

### 📁 هيكل ملفات التطبيق:

**Flutter:**
```
lib/
├── main.dart
├── screens/
│   ├── home_screen.dart
│   ├── login_screen.dart
│   └── profile_screen.dart
├── widgets/
├── models/
└── services/
pubspec.yaml
```

**React Native:**
```
src/
├── App.js
├── screens/
│   ├── HomeScreen.js
│   ├── LoginScreen.js
│   └── ProfileScreen.js
├── components/
├── navigation/
└── services/
package.json
```

**Swift:**
```
App/
├── AppName.swift (Entry)
├── Views/
│   ├── ContentView.swift
│   ├── HomeView.swift
│   └── LoginView.swift
├── Models/
└── Services/
```

**Kotlin:**
```
app/src/main/
├── java/com/app/
│   ├── MainActivity.kt
│   ├── ui/
│   │   ├── HomeFragment.kt
│   │   └── LoginFragment.kt
│   └── data/
├── res/
│   ├── layout/
│   └── values/
└── AndroidManifest.xml
```

---

### ⚠️ قواعد تطبيقات الموبايل:

1. **أنشئ الكود الكامل** - لا تترك TODO أو placeholders
2. **أضف التعليقات** بالعربية والإنجليزية
3. **صمم واجهة جميلة** مع Animations
4. **استخدم أفضل الممارسات** لكل منصة
5. **قدم تعليمات التشغيل** بالتفصيل

---

## 💰 جدول تكاليف تطبيقات الموبايل:

|| التقنية | المنصة | التكلفة |
||---------|--------|---------|
|| Flutter | iOS + Android | 30 نقطة |
|| React Native | iOS + Android | 30 نقطة |
|| Swift | iOS فقط | 35 نقطة |
|| Kotlin | Android فقط | 35 نقطة |
|| + تصميم UI متقدم | - | +15 نقطة |
|| + Backend/API | - | +20 نقطة |

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
        
        return processed_response, attachments, total_credits
    
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
        <div style="margin-top:10px;font-size:14px;">↑↓ Accelerate/Brake | ←→ Steer</div>
    </div>
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
</html>''',
            # Mobile App Templates (Code Examples)
            "mobile-flutter-ecommerce": '''// Flutter E-Commerce App Template
// pubspec.yaml dependencies needed:
// flutter, cupertino_icons, provider, http, cached_network_image

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
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF0d0d18),
          foregroundColor: Colors.amber,
        ),
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
        title: const Text('🛒 المتجر'),
        actions: [
          IconButton(icon: const Icon(Icons.shopping_cart), onPressed: () {}),
        ],
      ),
      body: GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          childAspectRatio: 0.75,
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
        ),
        itemCount: 10,
        itemBuilder: (context, index) => ProductCard(index: index),
      ),
    );
  }
}

class ProductCard extends StatelessWidget {
  final int index;
  const ProductCard({super.key, required this.index});
  
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF16213e),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.amber.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                color: Colors.amber.withOpacity(0.1),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
              ),
              child: const Center(child: Icon(Icons.shopping_bag, size: 64, color: Colors.amber)),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('منتج ${index + 1}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                const Text('199 ر.س', style: TextStyle(color: Colors.amber, fontSize: 16)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}''',
            "mobile-react-native-social": '''// React Native Social App Template
// Required packages: react-navigation, react-native-vector-icons

import React, { useState } from 'react';
import {
  View, Text, StyleSheet, FlatList, Image,
  TouchableOpacity, TextInput, SafeAreaView
} from 'react-native';

const App = () => {
  const [posts, setPosts] = useState([
    { id: '1', user: 'أحمد', content: 'مرحباً بالجميع! 👋', likes: 24, comments: 5 },
    { id: '2', user: 'سارة', content: 'يوم جميل ☀️', likes: 18, comments: 3 },
    { id: '3', user: 'محمد', content: 'شاركوني آراءكم 💭', likes: 32, comments: 12 },
  ]);

  const PostCard = ({ item }) => (
    <View style={styles.postCard}>
      <View style={styles.postHeader}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{item.user[0]}</Text>
        </View>
        <Text style={styles.userName}>{item.user}</Text>
      </View>
      <Text style={styles.postContent}>{item.content}</Text>
      <View style={styles.postActions}>
        <TouchableOpacity style={styles.actionBtn}>
          <Text style={styles.actionText}>❤️ {item.likes}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionBtn}>
          <Text style={styles.actionText}>💬 {item.comments}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionBtn}>
          <Text style={styles.actionText}>🔄 مشاركة</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🌐 التواصل</Text>
      </View>
      <FlatList
        data={posts}
        renderItem={({ item }) => <PostCard item={item} />}
        keyExtractor={item => item.id}
        contentContainerStyle={styles.feed}
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0a12' },
  header: { padding: 16, backgroundColor: '#0d0d18', borderBottomWidth: 1, borderBottomColor: '#ffd70033' },
  headerTitle: { fontSize: 24, fontWeight: 'bold', color: '#ffd700' },
  feed: { padding: 16 },
  postCard: { backgroundColor: '#16213e', borderRadius: 16, padding: 16, marginBottom: 16, borderWidth: 1, borderColor: '#ffd70033' },
  postHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  avatar: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#ffd700', justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  avatarText: { color: '#000', fontWeight: 'bold', fontSize: 18 },
  userName: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  postContent: { color: '#ccc', fontSize: 16, lineHeight: 24, marginBottom: 12 },
  postActions: { flexDirection: 'row', justifyContent: 'space-around', borderTopWidth: 1, borderTopColor: '#ffffff22', paddingTop: 12 },
  actionBtn: { padding: 8 },
  actionText: { color: '#ffd700', fontSize: 14 },
});

export default App;''',

            "mobile-swift-fitness": '''// Swift Fitness App Template
// SwiftUI - iOS 15+

import SwiftUI

@main
struct FitnessApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

struct ContentView: View {
    @State private var steps: Int = 8432
    @State private var calories: Int = 420
    @State private var distance: Double = 5.2
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    // Stats Cards
                    HStack(spacing: 16) {
                        StatCard(title: "خطوات", value: "\\(steps)", icon: "figure.walk", color: .amber)
                        StatCard(title: "سعرات", value: "\\(calories)", icon: "flame.fill", color: .orange)
                    }
                    
                    HStack(spacing: 16) {
                        StatCard(title: "مسافة", value: String(format: "%.1f km", distance), icon: "location.fill", color: .blue)
                        StatCard(title: "وقت", value: "45 د", icon: "clock.fill", color: .purple)
                    }
                    
                    // Progress Ring
                    ZStack {
                        Circle()
                            .stroke(Color.gray.opacity(0.3), lineWidth: 20)
                        Circle()
                            .trim(from: 0, to: 0.7)
                            .stroke(Color.amber, style: StrokeStyle(lineWidth: 20, lineCap: .round))
                            .rotationEffect(.degrees(-90))
                        VStack {
                            Text("70%")
                                .font(.system(size: 48, weight: .bold))
                                .foregroundColor(.amber)
                            Text("من الهدف اليومي")
                                .foregroundColor(.gray)
                        }
                    }
                    .frame(width: 200, height: 200)
                    .padding()
                    
                    // Workout Button
                    Button(action: {}) {
                        HStack {
                            Image(systemName: "play.fill")
                            Text("ابدأ التمرين")
                                .fontWeight(.bold)
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.amber)
                        .foregroundColor(.black)
                        .cornerRadius(16)
                    }
                    .padding(.horizontal)
                }
                .padding()
            }
            .background(Color(hex: "0a0a12"))
            .navigationTitle("💪 اللياقة")
            .navigationBarTitleDisplayMode(.large)
        }
    }
}

struct StatCard: View {
    let title: String
    let value: String
    let icon: String
    let color: Color
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: icon)
                    .foregroundColor(color)
                Spacer()
            }
            Text(value)
                .font(.title2)
                .fontWeight(.bold)
                .foregroundColor(.white)
            Text(title)
                .font(.caption)
                .foregroundColor(.gray)
        }
        .padding()
        .background(Color(hex: "16213e"))
        .cornerRadius(16)
    }
}

extension Color {
    static let amber = Color(red: 1, green: 0.84, blue: 0)
    
    init(hex: String) {
        let scanner = Scanner(string: hex)
        var rgbValue: UInt64 = 0
        scanner.scanHexInt64(&rgbValue)
        self.init(
            red: Double((rgbValue & 0xFF0000) >> 16) / 255.0,
            green: Double((rgbValue & 0x00FF00) >> 8) / 255.0,
            blue: Double(rgbValue & 0x0000FF) / 255.0
        )
    }
}''',
            "mobile-kotlin-news": '''// Kotlin News App Template
// Android - Jetpack Compose

package com.zitex.newsapp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            NewsAppTheme {
                NewsScreen()
            }
        }
    }
}

@Composable
fun NewsAppTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Color(0xFFFFD700),
            background = Color(0xFF0A0A12),
            surface = Color(0xFF16213E),
        ),
        content = content
    )
}

data class NewsItem(
    val id: Int,
    val title: String,
    val summary: String,
    val category: String,
    val time: String
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NewsScreen() {
    val news = remember {
        listOf(
            NewsItem(1, "عاجل: تحديثات جديدة في عالم التقنية", "تعرف على آخر المستجدات في عالم الذكاء الاصطناعي والتطبيقات", "تقنية", "منذ 5 دقائق"),
            NewsItem(2, "الأسواق المالية تشهد ارتفاعاً ملحوظاً", "مؤشرات إيجابية في البورصات العالمية اليوم", "اقتصاد", "منذ 15 دقيقة"),
            NewsItem(3, "نتائج مباريات اليوم", "ملخص شامل لأهم المباريات في الدوريات الكبرى", "رياضة", "منذ 30 دقيقة"),
            NewsItem(4, "اكتشاف علمي جديد", "علماء يتوصلون لاكتشاف مذهل في مجال الطب", "علوم", "منذ ساعة"),
        )
    }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { 
                    Text(
                        "📰 الأخبار",
                        color = Color(0xFFFFD700),
                        fontWeight = FontWeight.Bold
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF0D0D18)
                )
            )
        },
        containerColor = Color(0xFF0A0A12)
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            items(news) { item ->
                NewsCard(item)
            }
        }
    }
}

@Composable
fun NewsCard(news: NewsItem) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF16213E))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Color(0xFFFFD700).copy(alpha = 0.2f)
                ) {
                    Text(
                        text = news.category,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
                        color = Color(0xFFFFD700),
                        fontSize = 12.sp
                    )
                }
                Text(
                    text = news.time,
                    color = Color.Gray,
                    fontSize = 12.sp
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                text = news.title,
                color = Color.White,
                fontWeight = FontWeight.Bold,
                fontSize = 18.sp
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = news.summary,
                color = Color.Gray,
                fontSize = 14.sp,
                lineHeight = 20.sp
            )
        }
    }
}'''
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

