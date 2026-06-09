"""
Codebase Atlas v2 — Compact, high-value knowledge base.

The original `codebase_atlas.py` covers the basics (pages, modules, conventions).
This v2 module adds the **expensive-to-discover** knowledge that the AI
typically wastes tokens on:

  • FEATURE_INDEX   — "feature in Arabic → exact files to edit"
  • API_INVENTORY   — every endpoint with its route prefix + module
  • DB_COLLECTIONS  — every Mongo collection + minimal schema
  • COMMON_BUGS     — known recurring issues + their fix
  • DECISION_RULES  — "if user asks X, do Y" shortcuts
  • IMPORT_PATTERNS — exact import lines to copy-paste

Goal: drop average tokens-per-task by 60-80% by eliminating the
list_dir → read_file → grep → read_file cycle the AI typically runs.
"""
from __future__ import annotations


# ════════════════════════════════════════════════════════════════════════
# 🎯 FEATURE INDEX — أسرع طريقة للذكاء يعرف وين يعدّل
# ════════════════════════════════════════════════════════════════════════
# Map: feature name (Arabic + English aliases) → list of files involved.
# Format: "feature": ("frontend_files", "backend_files", "notes")

FEATURE_INDEX = {
    # ── المصادقة والمستخدمين ──────────────────────────────────────────────
    "تسجيل الدخول | login | auth": (
        ["frontend/src/pages/LoginPage.js", "frontend/src/pages/RegisterPage.js",
         "frontend/src/pages/AuthCallback.js"],
        ["backend/server.py (دوال /api/auth/*)"],
        "JWT في localStorage.token + GET /api/users/me",
    ),
    "تسجيل خروج | logout": (
        ["frontend/src/components/Navbar.js"],
        ["backend/server.py (POST /api/auth/logout — اختياري)"],
        "كافي تمسح localStorage.token من الـfrontend",
    ),
    "Google OAuth": (
        ["frontend/src/pages/AuthCallback.js", "frontend/src/components/GoogleAuthButton.js"],
        ["backend/server.py /api/auth/google"],
        "GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET في env",
    ),

    # ── الذكاء الاصطناعي والمحادثة ─────────────────────────────────────────
    "محادثة الذكاء العام | AI Agent | chat": (
        ["frontend/src/pages/AIAgent.js", "frontend/src/components/ChatInput.js"],
        ["backend/modules/agent/__init__.py"],
        "POST /api/agent/chat (multipart/form-data) — يدعم نص+صور+صوت",
    ),
    "برمجة زيتاكس | Auto-Coder | self-programming": (
        ["frontend/src/pages/AdminAutoCoder.js", "frontend/src/components/ChatInput.js"],
        ["backend/modules/autocoder/ (محمي)"],
        "POST /api/autocoder/chat — للمالك فقط",
    ),
    "بناء موقع | FreeBuild | website builder": (
        ["frontend/src/pages/FreeBuild.js"],
        ["backend/modules/freebuild_v2/__init__.py",
         "backend/modules/freebuild_v2/tools.py (~2200 lines)"],
        "POST /api/freebuild/v2/chat — generates SPA dynamically",
    ),
    "Avatar 3D | VRM | zara | layla": (
        ["frontend/src/pages/AvatarSettings.js", "frontend/src/pages/VrmPreview.js",
         "frontend/src/components/Avatar3D.js"],
        ["backend/modules/avatar/__init__.py"],
        "@react-three/fiber + VRM models",
    ),

    # ── توليد الوسائط ─────────────────────────────────────────────────────
    "توليد صور | image generation | wizard": (
        ["frontend/src/pages/ImageGenerator.js"],
        ["backend/modules/images/__init__.py",
         "backend/modules/image_wizard/__init__.py"],
        "POST /api/wizard/image/generate — يستخدم EMERGENT_LLM_KEY (Nano Banana)",
    ),
    "توليد فيديو | video generation": (
        ["frontend/src/pages/VideoGenerator.js"],
        ["backend/modules/videos/__init__.py",
         "backend/modules/video_wizard/__init__.py"],
        "POST /api/wizard/video/generate — Sora 2 via EMERGENT_LLM_KEY",
    ),
    "تسجيل صوتي | voice recording | mic | transcribe": (
        ["frontend/src/components/ChatInput.js",
         "frontend/src/components/VoiceRecorder.js (إذا موجود)"],
        ["backend/modules/speech/__init__.py",
         "backend/modules/autocoder/__init__.py (POST /api/autocoder/transcribe)"],
        "Whisper API. الصوت يُرفع كـmultipart/form-data في 'audio' field",
    ),
    "TTS | نص-إلى-صوت | ElevenLabs": (
        ["frontend/src/components/AudioPlayer.js"],
        ["backend/modules/speech/__init__.py", "backend/modules/avatar/__init__.py"],
        "ELEVENLABS_API_KEY مطلوب",
    ),

    # ── الطلبات والـadmin ─────────────────────────────────────────────────
    "طلبات | requests": (
        ["frontend/src/pages/NewRequest.js", "frontend/src/pages/MyRequests.js",
         "frontend/src/pages/RequestDetails.js", "frontend/src/pages/AdminRequests.js"],
        ["backend/server.py (دوال /api/requests/*)"],
        "Collection: requests",
    ),
    "مدفوعات | payments | stripe": (
        ["frontend/src/pages/PaymentPage.js", "frontend/src/pages/AdminPayments.js"],
        ["backend/modules/billing/__init__.py"],
        "STRIPE_API_KEY + STRIPE_WEBHOOK_SECRET",
    ),
    "نقاط | credits | balance": (
        ["frontend/src/pages/AdminCredits.js"],
        ["backend/modules/billing/__init__.py (دالة deduct_credits)"],
        "users.balance — int. يُخصم من POST /api/wizard/* وغيرها",
    ),
    "إحالات | affiliate | referral": (
        ["frontend/src/pages/Affiliate.js", "frontend/src/pages/AdminAffiliates.js"],
        ["backend/modules/affiliate/__init__.py"],
        "Collection: affiliate_clicks, affiliate_earnings",
    ),
    "بانر الموقع | site banner | stories": (
        ["frontend/src/pages/AdminSiteBanner.js"],
        ["backend/modules/site/__init__.py"],
        "GET /api/site/banner + GET /api/site/stories",
    ),

    # ── الاستقلالية والإعداد ─────────────────────────────────────────────
    "مفاتيح | keys | independence": (
        ["frontend/src/pages/AdminIndependence.js"],
        ["backend/modules/independence/__init__.py",
         "backend/modules/independence/tutorials.py"],
        "GET /api/admin/independence-status + /api/admin/integration-tutorial/{id}",
    ),
    "إعدادات الموقع | settings": (
        ["frontend/src/pages/AdminSettings.js"],
        ["backend/server.py (دوال /api/admin/settings/*)"],
        "Collection: site_settings",
    ),

    # ── مرافق ─────────────────────────────────────────────────────────────
    "ChatInput | input مشترك للشات": (
        ["frontend/src/components/ChatInput.js"],
        [],
        "موحّد لـ AIAgent + AdminAutoCoder + FreeBuild. يدعم: نص، attach files (images), voice record.",
    ),
    "Navbar": (
        ["frontend/src/components/Navbar.js"],
        [],
        "props: { user, transparent? }",
    ),
}


# ════════════════════════════════════════════════════════════════════════
# 📡 API INVENTORY — كل endpoint في النظام (لا تبحث بـgrep!)
# ════════════════════════════════════════════════════════════════════════
API_INVENTORY = """
🟢 Public (لا تحتاج auth):
  GET  /api/                              — root health
  POST /api/auth/register                 — تسجيل جديد
  POST /api/auth/login                    — تسجيل دخول → token
  POST /api/auth/google                   — Google OAuth
  GET  /api/site/banner                   — banner الموقع
  GET  /api/site/stories                  — stories الموقع
  GET  /api/agent/p/{slug}                — معاينة محادثة مشاركة

🔐 User (يحتاج Bearer token):
  GET  /api/users/me                      — بيانات المستخدم
  POST /api/agent/chat                    — multipart: text+files+audio
  GET  /api/agent/conversations           — قائمة المحادثات
  GET  /api/agent/conversation/{id}       — تفاصيل محادثة
  POST /api/freebuild/v2/chat             — bot بناء المواقع
  POST /api/wizard/image/generate         — توليد صورة (يخصم credits)
  POST /api/wizard/video/generate         — توليد فيديو (يخصم credits)
  POST /api/avatar/chat                   — محادثة Zara/Layla
  POST /api/speech/transcribe             — تفريغ صوت
  POST /api/companion/chat                — Zerax Companion

👑 Owner-only (admin + passcode):
  GET  /api/admin/stats                   — إحصائيات
  GET  /api/admin/requests                — كل الطلبات
  GET  /api/admin/payments                — كل المدفوعات
  GET  /api/admin/independence-status     — حالة المفاتيح
  GET  /api/admin/integration-tutorial/{id} — شرح مفتاح محدد
  POST /api/autocoder/chat                — Auto-Coder (يحتاج session token)
  POST /api/autocoder/upload              — رفع ملفات للـAuto-Coder
  POST /api/autocoder/transcribe          — تفريغ صوت للـAuto-Coder
"""


# ════════════════════════════════════════════════════════════════════════
# 🗄️ DB COLLECTIONS — كل Mongo collection (لا تخمّن schema)
# ════════════════════════════════════════════════════════════════════════
DB_COLLECTIONS = """
users:                  { id, email, password_hash, name, role, balance, created_at }
                        role: 'user' | 'admin' | 'super_admin' | 'owner'
                        balance: int (credits)

requests:               { id, user_id, type, status, details, created_at }
                        status: 'pending' | 'in_progress' | 'completed' | 'cancelled'

payments:               { id, user_id, amount, status, stripe_session_id, created_at }
                        status: 'pending' | 'paid' | 'failed'

conversations:          { id, user_id, module, messages[], created_at, updated_at }
                        module: 'agent' | 'autocoder' | 'freebuild' | 'companion'

autocoder_audit:        { id, owner_id, action, meta, ts }
autocoder_config:       { _id: 'singleton', passcode_hash, recovery_codes_hashed[], sessions[] }

websites:               { id, user_id, slug, html, css, js, meta, created_at }
images:                 { id, user_id, prompt, url, model, credits_used, created_at }
videos:                 { id, user_id, prompt, url, duration, credits_used, created_at }

site_settings:          { _id: 'singleton', config_json }
site_banner:            { id, placement: 'inside'|'outside', html, active, order }
site_stories:           { id, placement, image_url, link, active, order }

affiliate_clicks:       { id, affiliate_code, ip, referer, ts }
affiliate_earnings:     { id, affiliate_user_id, amount, status, ts }

companion_sessions:     { id, user_id, scheduled_for, messages[] }
operator_jobs:          { id, owner_id, type, status, result, created_at }
"""


# ════════════════════════════════════════════════════════════════════════
# 🐛 COMMON BUGS — أخطاء متكررة لا تعيد اكتشافها كل مرة
# ════════════════════════════════════════════════════════════════════════
COMMON_BUGS = """
1. **رفع ملفات في الشات (multipart/form-data)**
   - السبب الشائع: الـfrontend يرسل JSON بدل FormData
   - الحل: `new FormData()` ثم `formData.append('files', file)` + لا تحدد Content-Type
   - الـbackend يستلم عبر `files: List[UploadFile] = File(default=[])`
   - تحقق: في DevTools → Network → الطلب لازم Content-Type = multipart/form-data; boundary=...

2. **CORS errors بين Vercel و Railway**
   - السبب: domains الـfrontend مش في CORS_ORIGINS
   - الحل: server.py → CORSMiddleware → allow_origins=["*"] (للتطوير) أو list من env

3. **401 Unauthorized بعد إعادة تشغيل**
   - السبب: JWT_SECRET تغيّر → كل tokens القديمة باطلة
   - الحل: تأكّد JWT_SECRET ثابت في Railway

4. **MongoDB ObjectId غير قابل للـserialize**
   - السبب: نسيت `{"_id": 0}` في projection
   - الحل: كل `find()` أو `find_one()` لازم projection يستثني _id

5. **رصيد الذكاء (credits) ينقص بدون عملية**
   - السبب: failed API call بعد ما تم الخصم
   - الحل: استخدم try/except + رجع الـcredit لو فشلت العملية

6. **Vercel preview قديم بعد deploy**
   - السبب: cache المتصفح
   - الحل: hard refresh (Cmd+Shift+R) أو افتح incognito

7. **Auto-Coder يهلوس بأسماء ملفات (مثل Agent.js بدل AIAgent.js)**
   - السبب: الموديل يخمّن
   - الحل: codebase_atlas + atlas_v2 يمنعون هذا (هذا الملف نفسه!)

8. **تسجيل الصوت يفشل في الـbrowser**
   - السبب: HTTPS مطلوب لـnavigator.mediaDevices.getUserMedia
   - الحل: استخدم الـpreview الـHTTPS من Vercel، مش localhost
   - في ChatInput.js: تحقق أن `navigator.mediaDevices?.getUserMedia` موجود قبل ما تستخدمه
"""


# ════════════════════════════════════════════════════════════════════════
# 🧠 DECISION RULES — اختصارات للذكاء
# ════════════════════════════════════════════════════════════════════════
DECISION_RULES = """
المالك قال... | افعل... | لا تفعل...
───────────────────────────────────────────────────────────────────────
"عدّل صفحة X"           | اقرأ FEATURE_INDEX["X"] → اقرأ الملف → عدّل | لا تستدعي list_dir
"أضف ميزة جديدة"        | استخدم PATTERN_NEW_PAGE + PATTERN_NEW_BACKEND_MODULE | لا تخمّن البنية
"المفتاح Y ناقص"        | راجع KNOWN_ENV_VARS — لو فيها، اطلب من المالك يضيفه | لا تكتب fallback غامض
"الذكاء ما يفهم Z"      | راجع AUTOCODER_SYSTEM_PROMPT في autocoder/__init__.py | لا تحاول تعدّل __init__.py (محمي)
"الموقع وقع"            | view_logs("backend") → check_deployment_status → rollback لو خربان | لا تـcommit بدون ما تفهم
"خفّض الاستهلاك"        | استخدم atlas + atlas_v2 بدل read_file | لا تستدعي multiple أدوات لاستكشاف
"رفع الصور ما يشتغل"    | COMMON_BUGS #1 (multipart vs JSON) | لا تبدأ بـrewrite ChatInput.js
"التسجيل الصوتي معطّل"  | COMMON_BUGS #8 (HTTPS + getUserMedia) | لا تخمّن

⚡ القاعدة الذهبية: قبل أي `read_file` أو `list_dir`، اسأل نفسك:
   "هل المعلومة في FEATURE_INDEX / API_INVENTORY / DB_COLLECTIONS / COMMON_BUGS؟"
   لو نعم → ما تحتاج تستدعي أداة. وفّر الـtokens.
"""


# ════════════════════════════════════════════════════════════════════════
# 📚 IMPORT PATTERNS — copy-paste exact import lines
# ════════════════════════════════════════════════════════════════════════
IMPORT_PATTERNS = """
🔵 صفحة frontend جديدة (الـimports المعتادة):
   import React, { useState, useEffect } from 'react';
   import { useNavigate } from 'react-router-dom';
   import { Toaster, toast } from 'sonner';
   import { ArrowLeft, Loader2 } from 'lucide-react';  // أيقونات
   // لا تستورد: react-markdown, mui, antd, chakra

🟢 module backend جديد:
   from __future__ import annotations
   from typing import Any, Dict, List, Optional
   from fastapi import APIRouter, Depends, HTTPException
   from pydantic import BaseModel

🔌 استدعاء API من frontend:
   const API = process.env.REACT_APP_BACKEND_URL;
   const token = localStorage.getItem('token');
   const res = await fetch(`${API}/api/...`, {
     headers: { Authorization: `Bearer ${token}` }
   });

📤 رفع ملف (multipart):
   const formData = new FormData();
   formData.append('files', file);
   formData.append('message', text);
   const res = await fetch(`${API}/api/agent/chat`, {
     method: 'POST',
     headers: { Authorization: `Bearer ${token}` },  // ⚠️ بدون Content-Type
     body: formData
   });

🗄️ Mongo query (backend):
   docs = await db.users.find({"role": "user"}, {"_id": 0}).to_list(100)
"""


# ════════════════════════════════════════════════════════════════════════
# 🎁 builder
# ════════════════════════════════════════════════════════════════════════
def build_atlas_v2_for_prompt() -> str:
    feature_lines = []
    for feat, (fe, be, notes) in FEATURE_INDEX.items():
        fe_str = (" · ".join(f.replace("frontend/src/", "F:") for f in fe)) if fe else "—"
        be_str = (" · ".join(b.replace("backend/", "B:") for b in be)) if be else "—"
        feature_lines.append(f"  • **{feat}**\n      FE: {fe_str}\n      BE: {be_str}\n      📝 {notes}")
    features_section = "\n".join(feature_lines)

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 ATLAS v2 — قاعدة المعرفة المكثّفة (وفّر تكلفة الـAPI calls)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 خريطة الميزات (feature → ملفات بالضبط):

{features_section}

📡 جرد كامل للـAPI endpoints:
{API_INVENTORY}

🗄️ Schema جميع DB collections:
{DB_COLLECTIONS}

🐛 الأخطاء المتكررة وحلولها:
{COMMON_BUGS}

🧠 قواعد القرار السريع:
{DECISION_RULES}

📚 Import patterns جاهزة:
{IMPORT_PATTERNS}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 **اقتصاد الـtokens**:
- قبل ما تستدعي `read_file` أو `list_dir`، اسأل: "هل المعلومة في الـatlas؟"
- إذا نعم → ما تحتاج tool call. وفّر $.
- إذا لا → استدعِ الأداة، وبعدها اقترح للمالك يحدّث الـatlas.
- متوسط مهمة بسيطة لازم تكون <10 tool calls بدلاً من 30+.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
