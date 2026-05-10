"""
Codebase Atlas — pre-loaded knowledge map of the Zitex platform.

This file replaces the need for the AI to call read_file/list_dir repeatedly
just to discover the structure. Every system prompt build pulls this so the
AI starts every conversation with FULL awareness of:

  • Every page that exists (no need to scan /pages)
  • Every backend module and what it does
  • API conventions (prefix, auth, env vars, token names)
  • Where to add new features (and where NOT to)
  • Common patterns to copy when building new things

When you add a new page or backend module, update this atlas so the AI
keeps its knowledge fresh without expensive scans.
"""
from __future__ import annotations

# ════════════════════════════════════════════════════════════════════════
# 🗺️ FRONTEND — every page that exists in /app/frontend/src/pages
# ════════════════════════════════════════════════════════════════════════
FRONTEND_PAGES = {
    # Public
    "LandingPage.js": "/ — الصفحة الرئيسية (hero + features)",
    "DemoLanding.js": "/demo — هبوط demo بدون تسجيل",
    "LoginPage.js": "/login — تسجيل دخول",
    "RegisterPage.js": "/register — تسجيل جديد",
    "AuthCallback.js": "/auth-callback — Google OAuth redirect",
    "PricingPage.js": "/pricing — الباقات والأسعار",
    "VrmPreview.js": "/vrm-preview — معاينة avatar VRM",

    # Client (يحتاج تسجيل دخول)
    "ClientDashboard.js": "/dashboard — لوحة العميل الرئيسية",
    "NewRequest.js": "/dashboard/new-request — طلب جديد",
    "MyRequests.js": "/dashboard/requests — طلباتي",
    "RequestDetails.js": "/dashboard/requests/:id — تفاصيل طلب",
    "MyWebsites.js": "/dashboard/websites — مواقعي",
    "ImageGenerator.js": "/dashboard/images — صور AI",
    "VideoGenerator.js": "/dashboard/videos — فيديو AI",
    "ProjectsPage.js": "/dashboard/projects — مشاريعي",
    "PaymentPage.js": "/payment — الدفع",
    "FreeBuild.js": "/build-from-zero — بناء موقع من الصفر (FreeBuild v1)",
    "AIAgent.js": "/ai-agent — محادثة مع الذكاء العام (Agent)",
    "AIChat.js": "/ai-chat — chat بسيط",
    "Companion.js": "/companion — الرفيق Zitex Companion",
    "Affiliate.js": "/affiliate — الإحالات",
    "AvatarSettings.js": "/avatar-settings — إعدادات avatar",
    "ChannelBridge.js": "/bridge — جسر القنوات",
    "Operator.js": "/operator — لوحة المشغّل",
    "OperatorParts.js": "/operator-parts — قطع المشغّل",
    "SourceBrowser.js": "/source — متصفّح المصادر",
    "VisualDesigner.js": "/designer — مصمّم بصري",
    "PublicSite.js": "/site/:slug — موقع عميل علني",

    # Admin (يحتاج role=owner)
    "AdminDashboard.js": "/admin — لوحة المالك",
    "AdminRequests.js": "/admin/requests — كل الطلبات",
    "AdminPayments.js": "/admin/payments — المدفوعات",
    "AdminClients.js": "/admin/clients — العملاء",
    "AdminWebsites.js": "/admin/websites — كل المواقع",
    "AdminCredits.js": "/admin/credits — الكريديتس",
    "AdminAffiliates.js": "/admin/affiliates — برنامج الإحالة",
    "AdminTraining.js": "/admin/training — تدريب الـAI",
    "AdminAICore.js": "/admin/ai-core — تكوين الـAI الأساسي",
    "AdminSettings.js": "/admin/settings — إعدادات الموقع",
    "AdminSiteBanner.js": "/admin/site-banner — لوحة الستوريز",
    "AdminActivity.js": "/admin/activity — سجل النشاط",
    "AdminAutoCoder.js": "/admin/autocoder — المهندس الذاتي (أنت)",
    "AdminIndependence.js": "/admin/independence — لوحة الاستقلالية",
}

# Big shared components (in /app/frontend/src/components/)
FRONTEND_COMPONENTS = {
    "Navbar.js": "شريط التنقل العلوي",
    "ZitexDuo.js + ZitexDuoLauncher.js": "زوج الـAI المساعد العائم",
    "Avatar3D.js + AIAssistantAvatar.js": "الـavatar الـ3D",
    "GlobalAvatarMount.js": "تركيب avatar في كل الصفحات",
    "VoiceChatButton.js + VoicePanel.js + VoiceStage.js": "نظام الصوت",
    "AmbientVoiceAgent.js + WakeWordListener.js": "wake word detection",
    "LiveChat.js": "chat مباشر",
    "SiteBannerStories.js": "ستوريز الـbanner",
    "CharacterSceneEngine.js + CharacterSceneEngine3D.js": "محرّك المشاهد",
    "ProtectedRoute.js": "حارس routes (يطلب تسجيل دخول)",
}

# ════════════════════════════════════════════════════════════════════════
# 🔧 BACKEND — every module in /app/backend/modules
# ════════════════════════════════════════════════════════════════════════
BACKEND_MODULES = {
    "agent":        "الذكاء العام للمستخدمين (chat + tools — Quran API, web search, etc)",
    "autocoder":    "🛡️ هذي وحدتك أنت! (محمية من التعديل)",
    "freebuild":    "بناء مواقع v1 (legacy)",
    "freebuild_v2": "بناء مواقع v2 — المستخدم حالياً (~2200 سطر في tools.py)",
    "websites":     "إدارة المواقع المنشورة + autopilot scheduler",
    "studio":       "Visual Studio لتعديل المواقع",
    "image_wizard": "مرشد صور AI (متعدد الأنماط)",
    "video_wizard": "مرشد فيديو AI",
    "images":       "REST لإدارة الصور",
    "videos":       "REST لإدارة الفيديوهات",
    "billing":      "Stripe + balance management",
    "site":         "metadata الموقع العام (banner, stories)",
    "source":       "اللي يعرض كود المواقع المُنشأة",
    "operator":     "المشغّل + scheduler",
    "affiliate":    "برنامج الإحالة",
    "bridge":       "جسر القنوات (telegram/whatsapp)",
    "ai_core":      "تكوين الذكاء العام (system prompts, models)",
    "avatar":       "إعدادات الـavatar الـ3D",
    "companion":    "Zitex Companion + scheduler",
    "games":        "ألعاب",
    "independence": "حالة الاستقلالية (مفاتيح المالك المباشرة)",
}

# ════════════════════════════════════════════════════════════════════════
# 📡 API conventions — كل request/response في الموقع يلتزم بهذي
# ════════════════════════════════════════════════════════════════════════
API_CONVENTIONS = """
1. **كل API endpoint بادئتها /api/...** (إلا /api/storage/{file} للملفات)
2. **Auth header**: `Authorization: Bearer ${token}` حيث token من login response
3. **Frontend**:
   - Base URL من `process.env.REACT_APP_BACKEND_URL`
   - token من `localStorage.getItem('token')` (مش 'session_token' أو غيره)
   - User object من `localStorage.getItem('user')` (JSON)
4. **Backend**:
   - كل route يدعم `Depends(get_current_user)` للـauth
   - admin routes تستخدم `Depends(require_owner)`
   - DB من `motor` (async) — اسم الـdatabase من `os.environ['DB_NAME']`
   - **لا تخرج _id من MongoDB** — استخدم `{"_id": 0}` في projection
5. **Module pattern**:
   - كل module في `/app/backend/modules/<name>/__init__.py`
   - يصدّر دالة `create_<name>_router(db, get_current_user, require_owner)`
   - server.py يستوردها ويسجّل: `app.include_router(_xxx_router, prefix="/api")`
"""

# ════════════════════════════════════════════════════════════════════════
# 🌍 Environment variables — اللي عندك متاحة دايماً (من Railway production)
# ════════════════════════════════════════════════════════════════════════
KNOWN_ENV_VARS = [
    # Auth
    "JWT_SECRET", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
    # DB
    "MONGO_URL", "DB_NAME",
    # LLMs (المالك مستقل بمفاتيحه)
    "ANTHROPIC_API_KEY", "OPENAI_DIRECT_KEY", "GROQ_API_KEY", "GEMINI_API_KEY",
    "EMERGENT_LLM_KEY",  # احتياط
    # Voice
    "ELEVENLABS_API_KEY",
    # Payment
    "STRIPE_API_KEY",
    # Self-deployment (Auto-Coder)
    "GITHUB_TOKEN", "GITHUB_REPO",
    "RAILWAY_TOKEN", "RAILWAY_PROJECT_ID", "RAILWAY_SERVICE_ID", "RAILWAY_ENVIRONMENT_ID",
    # Misc
    "ALPHA_VANTAGE_API_KEY",
    # Set automatically by Railway:
    "RAILWAY_ENVIRONMENT", "RAILWAY_STATIC_URL", "PORT",
]

# ════════════════════════════════════════════════════════════════════════
# 📦 Available NPM packages — لا تستورد غيرها بدون yarn add أولاً
# ════════════════════════════════════════════════════════════════════════
AVAILABLE_NPM_PACKAGES = [
    # Core
    "react", "react-dom", "react-router-dom",
    # UI
    "lucide-react",       # أيقونات (المعتمدة في الموقع)
    "sonner",             # toasts
    "tailwindcss",        # styling
    # 3D / Avatar
    "@react-three/fiber", "@react-three/drei", "three",
    # API / fetching (use native fetch usually)
    "axios",
    # Forms
    "react-hook-form",
    # Auth
    "@react-oauth/google",
    # State
    "zustand",
]

# Packages NOT installed — لا تستوردها قبل yarn add
PACKAGES_TO_AVOID = [
    "react-markdown",         # ❌
    "react-syntax-highlighter",  # ❌
    "@chakra-ui/*",           # ❌ نستخدم Tailwind فقط
    "@mui/*",                 # ❌
    "antd",                   # ❌
    "bootstrap",              # ❌
]

# ════════════════════════════════════════════════════════════════════════
# 🎨 Frontend styling rules
# ════════════════════════════════════════════════════════════════════════
STYLING_RULES = """
1. **Tailwind فقط** — لا CSS files منفصلة لكل page (إلا globals.css و App.css)
2. **اللون الأساسي للموقع**: amber (تدرّجات amber-400/500) على dark background (zinc-900/950)
3. **Container**: عادة `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`
4. **Cards**: `bg-zinc-900/50 backdrop-blur border border-white/10 rounded-2xl p-6`
5. **Buttons primary**: `bg-amber-500 hover:bg-amber-400 text-black font-bold rounded-xl`
6. **Buttons secondary**: `bg-white/10 hover:bg-white/15 text-white border border-white/15`
7. **Inputs**: `bg-black/40 border border-white/15 rounded-xl px-4 py-3 focus:border-amber-400 outline-none`
8. **اتجاه**: الموقع RTL في معظم الصفحات (`dir="rtl"` على الـmain wrapper). استخدم `text-right`، `start-*`/`end-*` بدل left/right
9. **Toasts**: `import { toast } from 'sonner'` — ثم `toast.success(...)`, `toast.error(...)`
"""

# ════════════════════════════════════════════════════════════════════════
# 🚦 Where you CAN work freely (no restrictions, just guidance)
# ════════════════════════════════════════════════════════════════════════
SAFE_TO_MODIFY = """
بكامل الحرية تقدر تعدّل أو تنشئ في:
  ✅ /app/backend/server.py — للـrouters الجديدة (شف pattern: include_router)
  ✅ /app/backend/modules/<أي module> — عدا autocoder/ (محمية)
  ✅ /app/backend/modules/<NEW_NAME>/__init__.py — module جديد
  ✅ /app/frontend/src/pages/<أي صفحة> — عدا AdminAutoCoder.js نفسها (لتجنّب الكسر الذاتي)
  ✅ /app/frontend/src/components/<أي component>
  ✅ /app/frontend/src/App.js — لتسجيل routes جديدة
  ✅ /app/frontend/tailwind.config.js — لإضافة theme tokens
  ✅ /app/backend/requirements.txt — pip install + pip freeze (لا تكتبها يدوياً)
  ✅ /app/frontend/package.json — yarn add (لا تكتبها يدوياً)
"""

DO_NOT_TOUCH = """
🛡️ ممنوع تعدّل/تكتب/تحذف:
  ❌ /app/backend/modules/autocoder/__init__.py
  ❌ /app/backend/modules/autocoder/llm_providers.py
  ❌ /app/backend/modules/autocoder/tools_extra.py
  ❌ /app/backend/modules/autocoder/codebase_atlas.py (هذا الملف نفسه)
  ❌ /app/.git/* — لا تعبث في الـgit history مباشرة، استخدم git_commit_push
  ❌ /app/backend/.env — لا تكتب أو تطبع المفاتيح السرّية إلا لو طلب صريح
  ❌ Frontend pages اللي تتعامل مع الـAuto-Coder الجلسة الحالية (AdminAutoCoder.js) — قد تكسر اتصالك
"""

# ════════════════════════════════════════════════════════════════════════
# 🧩 Common patterns — copy-paste templates للمهام الشائعة
# ════════════════════════════════════════════════════════════════════════
PATTERN_NEW_PAGE = """
🔵 إنشاء صفحة frontend جديدة:
1. أنشئ /app/frontend/src/pages/MyNewPage.js
2. القالب الأدنى:
   ```jsx
   import { useState, useEffect } from 'react';
   import { useNavigate } from 'react-router-dom';
   import { toast } from 'sonner';

   const API = process.env.REACT_APP_BACKEND_URL;

   export default function MyNewPage({ user }) {
     const navigate = useNavigate();
     const token = localStorage.getItem('token');
     const [data, setData] = useState(null);

     useEffect(() => {
       fetch(`${API}/api/my-endpoint`, {
         headers: { Authorization: `Bearer ${token}` }
       })
         .then(r => r.json())
         .then(setData)
         .catch(e => toast.error(e.message));
     }, []);

     return (
       <div dir="rtl" className="min-h-screen bg-zinc-950 text-white p-6">
         <div className="max-w-7xl mx-auto">
           <h1 className="text-3xl font-bold mb-6">عنوان الصفحة</h1>
           {/* محتوى */}
         </div>
       </div>
     );
   }
   ```
3. سجّل الـroute في /app/frontend/src/App.js:
   ```jsx
   import MyNewPage from '@/pages/MyNewPage';
   // داخل <Routes>:
   <Route path="/my-page" element={<ProtectedRoute><MyNewPage user={user} /></ProtectedRoute>} />
   ```
"""

PATTERN_NEW_BACKEND_MODULE = """
🟢 إنشاء module backend جديد:
1. أنشئ /app/backend/modules/myfeature/__init__.py
2. القالب:
   ```python
   from fastapi import APIRouter, Depends
   from typing import Optional

   def create_myfeature_router(db, get_current_user, require_owner):
       router = APIRouter(prefix="/api/myfeature", tags=["myfeature"])

       @router.get("/list")
       async def list_items(user=Depends(get_current_user)):
           items = await db.myfeature_items.find(
               {"user_id": user["id"]}, {"_id": 0}
           ).to_list(100)
           return {"items": items}

       @router.post("/create")
       async def create_item(payload: dict, user=Depends(get_current_user)):
           # ...
           return {"ok": True}

       return router
   ```
3. سجّل في /app/backend/server.py:
   ```python
   from modules.myfeature import create_myfeature_router
   _myfeature_router = create_myfeature_router(db, get_current_user, require_owner)
   app.include_router(_myfeature_router)  # already has /api prefix
   ```
"""

PATTERN_PROTECTED_ADMIN_ROUTE = """
🟡 صفحة admin جديدة:
- في App.js: `<Route path="/admin/x" element={<ProtectedRoute adminOnly><AdminX /></ProtectedRoute>} />`
- في AdminX.js: تحقق من user.role === 'owner' أو الـbackend يرفع 403
"""

# ════════════════════════════════════════════════════════════════════════
# 🚀 Ready-to-paste atlas summary — يُضمَّن في system prompt
# ════════════════════════════════════════════════════════════════════════
def build_atlas_for_prompt() -> str:
    pages_listing = "\n".join(f"  - **{name}** → {route}" for name, route in FRONTEND_PAGES.items())
    modules_listing = "\n".join(f"  - **modules/{name}/** → {desc}" for name, desc in BACKEND_MODULES.items())

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🗺️  أطلس موقع زيتاكس (محفوظ في ذاكرتك — لا تستدعي list_dir لاكتشافه)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🖥️  الصفحات الموجودة في /app/frontend/src/pages/:
{pages_listing}

🔧 الـbackend modules في /app/backend/modules/:
{modules_listing}

📡 قواعد الـAPI:
{API_CONVENTIONS}

🎨 قواعد التصميم (Tailwind فقط):
{STYLING_RULES}

📦 NPM packages المتاحة (لا تستورد غيرها):
{', '.join(AVAILABLE_NPM_PACKAGES)}

❌ ممنوع استيرادها (مش مثبتة):
{', '.join(PACKAGES_TO_AVOID)}

🌍 Environment variables المتاحة في الـRailway production:
{', '.join(KNOWN_ENV_VARS)}

✅ المساحات اللي عندك حرية كاملة فيها:
{SAFE_TO_MODIFY}

🛡️ الحدود الأمنية:
{DO_NOT_TOUCH}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧩 قوالب جاهزة (انسخ منها لما تنشئ شي جديد):

{PATTERN_NEW_PAGE}

{PATTERN_NEW_BACKEND_MODULE}

{PATTERN_PROTECTED_ADMIN_ROUTE}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ **استخدام الأطلس بذكاء** (يوفّر فلوس وتوكنز):
- لما المالك يطلب "أضف صفحة X"، انت تعرف **مباشرة** الـpattern المطلوب من الأطلس فوق.
- لا تستدعي `list_dir` على /pages أو /modules — قائمتها هنا.
- لا تستدعي `read_file` على ملفات معروفة لمجرد "تتأكد من الـimports" — استخدم القوالب فوق.
- استخدم `read_file` فقط للملف اللي **بتعدّل عليه فعلياً**، أو لما تحتاج فهم منطق محدد.
- بعد ما تخلّص أي ميزة جديدة، اقترح على المالك تحديث codebase_atlas.py (لكن ما تعدّله بنفسك — هو محمي).
"""
