# Zenrex Farm — PRD (Product Requirements Document)

## 🚨 CRITICAL FOR ANY AGENT READING THIS — DEPLOYMENT INSTRUCTIONS 🚨
**SEE `/app/memory/DEPLOYMENT_INSTRUCTIONS.md` FOR FULL DETAILS**

Quick summary: العميل يملك VPS Hetzner. أي تعديل تعمله، شغّل **`bash /app/deploy/deploy.sh zenrex.ai`** فوراً.
SSH key موجود في `/root/.ssh/zerax_deploy`. **لا تسأل، لا تعتذر، انشر مباشرة.**

## 2026-06-19 (الجلسة 13) — 🔁 Site-to-App Converter + ⚖️ Legal Terms Gate

**Status**: ✅ مُنجَز — 12/12 backend pytest PASS، نُشر على https://zenrex.ai/

### Site-to-App Converter (مسار جديد `/native/convert`):
- **Backend** — `/app/backend/modules/site_to_app/__init__.py`:
  - `POST /api/site-to-app/scan` — يقبل `source: 'url'|'project'`، يجلب HTML ويحلّله بـ BeautifulSoup (لغة، عنوان، أقسام، روابط قائمة، صور، نماذج، ميزات: ecommerce/booking/blog/contact_form/video/auth).
  - `POST /api/site-to-app/plan` — يولّد خطّة مرحلية + قائمة المعلومات المطلوبة (Stripe, calendar, logo, ألوان) + الأمور التي لا يمكن تحويلها تلقائياً.
  - `POST /api/site-to-app/start` — ينشئ `freebuild_projects` doc بـ `mode='app'` + `tech_stack` + رسالة افتتاحية تفصيلية + الخطّة محفوظة.
  - يستخدم `db.site_to_app_scans` لحفظ نتائج الفحص.
- **Frontend** — `/app/frontend/src/pages/SiteToAppWizard.jsx`:
  - 4 خطوات: المصدر → الفحص → التقنية → الخطّة.
  - يدعم اختيار من مشاريع موجودة (مواقع website mode فقط) أو لصق رابط خارجي.
  - 5 خيارات Tech Stack (PWA موصى به، React Native، Flutter، Native iOS، Native Android).
  - 6 تصنيفات (ecommerce/services/content/community/productivity/other).
  - يعرض الميزات المكتشفة كـ pills خضراء/رمادية، الخطة المرحلية، المعلومات المطلوبة، الأمور غير القابلة للتحويل.

### Legal Terms Gate (لكل قسم):
- **Backend** — `/app/backend/modules/terms/__init__.py`:
  - 9 أقسام محدّدة: websites, apps, images, videos, longform, games, deploy, payments, site_to_app.
  - كل قسم له `TERMS_VERSION` + نصّ كامل بـ `ar` + `en` (يقابل الـ16 bullet للنقاط الأساسية).
  - `GET /api/terms/content?section=X&locale=Y` — يرجع المحتوى مع fallback chain (requested→en→ar).
  - `GET /api/terms/check?section=X` — يفحص قبول المستخدم.
  - `POST /api/terms/accept` — idempotent upsert يحفظ {user_id, section, version, locale, accepted_at, ip, user_agent}.
  - `GET /api/terms/my-acceptances` — سجل المستخدم الكامل.
- **Frontend** — `/app/frontend/src/components/TermsGate.js`:
  - مكوّن `<TermsGate section="...">` يلفّ أي صفحة.
  - يكتشف لغة المستخدم تلقائياً من `localStorage`/`<html lang>`/`navigator.language`.
  - Modal بالـ RTL/LTR يطلب موافقة قبل دخول القسم.
  - يحفظ Date/Time/IP لأغراض قانونية.
- **مطبّق على**: `/freebuild/chat` (websites), `/native/new` (apps), `/native/convert` (site_to_app).

### Files Added:
- `/app/backend/modules/terms/__init__.py`
- `/app/backend/modules/site_to_app/__init__.py`
- `/app/backend/tests/test_terms_and_site_to_app.py` (12/12 PASS)
- `/app/frontend/src/components/TermsGate.js`
- `/app/frontend/src/pages/SiteToAppWizard.jsx`

### Files Modified:
- `/app/backend/server.py` — مُسجَّل الـ2 موديول.
- `/app/frontend/src/App.js` — Routes `/native/convert`, ولفّ `/freebuild/chat` و `/native/new` بـ TermsGate.
- `/app/frontend/src/pages/NativeAppNew.jsx` — أُضيف زر CTA "حوّل موقعك إلى تطبيق".

## 2026-06-19 (الجلسة 12) — 🔔 Auto-Resume Reminders (كل أنواع المشاريع)

**Status**: ✅ مُنجَز — 5/5 pytest PASS، نُشر على https://zenrex.ai/

### ما تم:
1. **Module جديد** `/app/backend/modules/resume_reminder/__init__.py`:
   - Scheduler يشتغل كل ساعة (`SCAN_INTERVAL_SECONDS=3600`)
   - يفحص: `freebuild_projects` (مواقع/تطبيقات/استوديو)، `game_projects` (ألعاب)، `video_series` (فيديو طويل)
   - Cadence: 24h → 72h → 168h (٧ أيام)، ثم يتوقف
   - Idempotent عبر `db.resume_reminders` tracker (sent_count + last_reminder_at + history)
   - يحترم `user.reminder_opt_out` flag
2. **إيميل HTML** بهوية زنركس (لوغو ذهبي + RTL + tone متدرج حسب رقم التذكير) عبر Resend.
3. **Endpoints**:
   - `GET /api/resume-reminders/me` — قراءة الـopt_out
   - `POST /api/resume-reminders/me/opt-out` — تفعيل/إيقاف
   - `GET /api/resume-reminders/me/history` — سجل التذكيرات المُرسلة
   - `POST /api/resume-reminders/admin/run-now` — تشغيل يدوي (admin only)
4. **UI في `/freebuild/projects`**:
   - زر toggle "🔔 تذكيرات مفعّلة / موقوفة" في الـheader
   - Banner أصفر تحت الفلاتر يشرح آلية التذكيرات + رابط إيقاف سريع
5. **مُسجَّل في `server.py`** بعد Companion module عبر `register_resume_reminders(db, app, get_current_user)`.
6. **Pytest** — `/app/backend/tests/test_resume_reminders.py` — 5/5 PASS.
7. **نُشر** — على prod مع log: `[RESUME-REMINDER] scheduler running (every 3600s)`.

## 2026-06-19 (الجلسة 11) — Branding + Connections Help + Storage + My Projects

**Status**: ✅ مُنجَز — Backend 100% PASS، Frontend verified، نُشر على https://zenrex.ai/

### ما تم:
1. **`ZenrexBrand` + لوغو رسمي** (`/zenrex-logo.png` — Z+تاج ذهبي) — مستبدل أي ذكر للموديل.
2. **`ZCrownSpinner` محدّث** — يستخدم اللوغو الحقيقي PNG مع رنين ذهبي وعنوان "زنركس AI".
3. **`ConnectionHelpModal`** — لكل provider (github/vercel/cloudflare/domain/stripe/brand_logo):
   - مقدمة بالعربي
   - رابط مباشر للموقع الرسمي
   - Screenshot من الصفحة الفعلية (من docs الرسمية)
   - 5-7 خطوات مرقّمة بالتفصيل
   - أخطاء شائعة (Pitfalls)
   - يفتح من زر ❓ بجنب كل صف اتصال
4. **ConnectionsPanel UX**:
   - 🔴 pill أحمر متحرّك "غير مربوط" + ⚠️ icon
   - 🟢 pill أخضر نابض "مربوط · ghp_..." بعد الحفظ
   - زر ❓ بجنب كل عنوان provider + رابط "دليل خطوة بخطوة + صور"
5. **`StorageIndicator`** — pill أخضر/كهرماني/أحمر يعرض MB المستخدمة و عدد المشاريع، يفتح Modal للترقية ($9 Pro / $29 Studio).
6. **Backend `/api/freebuild-chat/storage/usage`** — يحسب bytes_used من current_html + messages + assets، يقارنها بحدود الباقة (free 100MB/3, pro 5GB/20, studio 50GB/∞).
7. **`MyProjects` page** (`/freebuild/projects` + `/my-projects`):
   - مجموعات: مواقع 🌐 / تطبيقات 📱 / استوديو 🎨
   - فلاتر، كرت لكل مشروع مع "أكمل العمل" + حذف + دعم فني
   - StorageIndicator + Brand في الـheader
8. **تحديث Top Bar في FreeBuildChat** — Brand + Storage + شارة "📱 استوديو التطبيقات" عند `isAppMode`.
9. **Pytest** — `/app/backend/tests/test_storage_quota.py` — 6/6 PASS.
10. **نُشر للإنتاج** — https://zenrex.ai/api/freebuild-chat/storage/usage يعمل، Frontend مع build جديد.

### ملاحظات تقنية:
- Tailwind JIT لا يدعم class names ديناميكية (`bg-${color}-500`) — استخدمت static maps في `MyProjects.jsx`.
- `ZenrexBrand` فيه fallback `<Z>` لو فشل تحميل اللوغو.
- `FreeBuildChat.js` صار ~4500 سطر — يحتاج تقسيم في session قادم (ConnectionsPanel, FinalizeModal, CookiesManager، CredentialModal مرشّحون للاستخراج).

## 2026-06-19 (الجلسة العاشرة) — 📱 Native App Builder (PWA Studio)

**Status**: ✅ مُنجَز — اختبار E2E ناجح 100% (7/7 backend + frontend) + نُشِر على https://zenrex.ai/

### ما تم في هذه الجلسة:
1. **`/native/new`** — صفحة منفصلة لاختيار النظام (iPhone / Android / الاثنين) + اسم ووصف. JSX جاهز في `/app/frontend/src/pages/NativeAppNew.jsx`.
2. **Route مربوط** — `/native/new` و `/native/chat/:id` في `App.js`.
3. **Backend — `platform` field**:
   - `ProjectIn` Pydantic أُضيف لها `platform: Optional[str]`
   - `create_project` يتحقق من القيمة `ios|android|both` ويحفظها على `freebuild_projects` document
   - Greeting الافتتاحي يتكيّف حسب الاختيار: "اخترت تطوير تطبيقك لـ iPhone / Android / Universal PWA"
4. **System Prompt — `app_ctx`** (PWA Mode):
   - تعليمات صارمة: manifest.json inline base64، Service Worker inline، meta tags (viewport, theme-color, apple-mobile-web-app-*), Bottom Tab Bar, Touch-friendly (≥44px)، Safe Areas (env(safe-area-inset-*))، max-width 480px، 100dvh، Material Ripple للأندرويد، Dynamic Island/notch awareness.
   - مفعّل حصرياً عندما `proj.get('mode') == 'app'`
5. **Phone Frame في `FreeBuildChat.js`**:
   - `isAppMode` flag + `appDevice` state (iphone | android)
   - عند `mode === 'app'`، الـ live preview يلتف داخل إطار جوال CSS:
     - iPhone: 390×844px، border-radius 52px، Dynamic Island notch، home indicator
     - Android: 390×844px، border-radius 32px، camera dot، home bar
   - زر تبديل iPhone ↔ Android (`device-iphone-btn` / `device-android-btn`)
   - تفعيل تلقائي للـ mobile preview mode عند فتح مشروع app
6. **CTA على `/freebuild/chat` landing**: رابط "أو ابني تطبيق جوال من الصفر (PWA)" → `/native/new`
7. **اختبار** — 7/7 backend pytest + frontend Playwright PASS (`/app/test_reports/iteration_45.json`)
8. **نشر للإنتاج** — https://zenrex.ai/ → API + UI verified live

### Files Created/Modified:
- ✏️ `/app/backend/modules/freebuild/freebuild_chat.py` — ProjectIn, create_project, greeting override, app_ctx system prompt block
- ✏️ `/app/frontend/src/App.js` — `/native/new` route added
- ✏️ `/app/frontend/src/pages/FreeBuildChat.js` — phone-frame wrapper + device toggle + native CTA
- ✅ `/app/frontend/src/pages/NativeAppNew.jsx` — already existed, now routed
- ✅ `/app/backend/tests/test_native_app_builder.py` — new pytest suite (7 tests)

## 2026-06-19 (الجلسة السابعة) — 🎭 White-Label AI Branding

**Status**: ✅ مُنجَز — تأكيد بصري وبرمجي (No 'claude' anywhere in page)

### ما تم:
1. **إزالة حرف Z الأحمر** من spinner المحادثة (استُبدل بـ3 نقاط ملوّنة + نص "يحلل ويكتب...")
2. **إخفاء model_used تماماً**: 
   - Backend يرجع `model_used: ""` في كل endpoints
   - Frontend ما يعرض الـmodel حتى لو وُجد
3. **حذف أسماء النماذج من task labels**:
   - "🎨 يصمم (Claude Opus 4.5)" → "🎨 يصمم"
   - "💻 يكتب الكود (Kimi K2.6)" → "💻 يكتب الكود"
   - "🛠️ يصلّح أخطاء برمجية (GPT-5 / Opus)" → "🛠️ يصلّح أخطاء برمجية"
   - "🤖 Agent (N خطوة)" → "🤖 يعمل (N خطوة)"
4. **حذف SSE provider disclosure**: 
   - "🧠 يستخدم claude-sonnet..." → "🧠 الذكاء الصناعي يحلل..."
   - "🚀 الذكاء بدأ التحليل..." → "🚀 يحلل ويبدأ..."

### الفائدة:
العميل يحس إن Zenrex منصة مستقلة بذكاء صناعي خاص بها (white-label experience). لا يدري إن الـbackend يستخدم Claude/Opus/Kimi/etc — أسرار تشغيلية محفوظة.




### مكوّنات جديدة:
1. **`/app/backend/modules/freebuild/health_score.py`** — Site Health Score 0-100
   - 5 أبعاد بأوزان: 🎨 تصميم (25), 🔍 SEO (20), ⚡ أداء (20), ♿ Accessibility (15), 🛡️ امتثال سعودي (20)
   - يولّد grade (A+, A, B+, B, C, D, F) + emoji + top_suggestions قابلة للنقر
   - يُحفظ في `last_health` على كل تحديث HTML

2. **`/app/backend/modules/freebuild/brand_kit.py`** — AI Memory عبر المشاريع
   - `get_brand_kit()` يجيب تفضيلات العميل من DB
   - `format_brand_kit_for_prompt()` يُحقن في system prompt
   - `learn_from_project()` يستخرج ألوان، خطوط، قطاع تجاري تلقائياً بعد كل HTML
   - مع الوقت AI يعرف العميل أكثر فأكثر

3. **Stripe Checkout كامل** في `freebuild_chat.py`:
   - 3 باقات (server-side):
     - `code_only` $100 (دفعة واحدة، كود ملكية كاملة)
     - `code_pro` $249 (كود + Multi-Page + استشارة)
     - `hosting_month` $25 (اشتراك شهري)
   - `POST /project/{pid}/checkout` يولّد Stripe session
   - `GET /payments/status/{session_id}` يفحص الحالة مع idempotent unlock
   - `POST /api/webhook/stripe` (global في server.py) يعالج Webhook events
   - `payment_transactions` collection يحفظ كل المعاملات

4. **`/app/frontend/src/pages/FreebuildCheckout.jsx`** — صفحة قرار النهائي:
   - 3 بطاقات gradient احترافية
   - Stripe redirect + polling status
   - Success/Cancel routes

5. **Health Card في FreeBuildChat.js**:
   - Sidebar فيها bar chart للـ5 أبعاد
   - Top suggestions بصيغة زر — كل نقرة تضيف الاقتراح لـcomposer
   - Upgrade CTA "احصد الكود — $100" يفتح صفحة Checkout

### اختبار شامل (موقع صالون تجميل):
- ✅ HTML built (28.5KB)
- ✅ Validator: `✅ OK (29.0KB, 0 ملاحظات)` — autoheal not needed
- ✅ Health Score: **73/100 (B+ 🟡)** 
  - 🎨 تصميم 22/25 (88%)
  - 🔍 SEO 11/20 (55%) ← فرصة upsell واضحة
  - ⚡ أداء 14/20 (70%)
  - ♿ Accessibility 7/15 (47%) ← فرصة تحسين كبيرة
  - 🛡️ امتثال سعودي 19/20 (95%)
- ✅ Top suggestions: Open Graph, Twitter Card, Schema.org, aria-label, input labels
- ✅ Brand Kit auto-learned: ألوان بنفسجي/وردي، قطاع salon

### ما يحتاج جلسة قادمة (لأسباب نطاق):
- 🟡 **Multi-Page Architecture**: يحتاج تحديث جذري للـAI prompt + export endpoint لتوليد عدة صفحات HTML بدل واحدة. مدة تقديرية: نصف يوم.
- 🟡 **Visual Guardian**: يحتاج screenshot + Gemini/Claude Vision لفحص بصري آلي. مدة تقديرية: 3-4 ساعات.

### Trail of sessions in this work block:
- Session 1: AI Compliance Layer + 4-stage machine + 15/15 امتثال + رفض المحتوى الممنوع
- Session 2: UI polish + text glitch fix + Information First rule
- Session 3: Source Code Export (ZIP) + E2E hosted
- Session 4: Zenrex Guardian (silent supervisor) + Admin Dashboard
- Session 5: HTML Validator + Auto-Heal
- Session 6 (الحالية): Site Health Score + Brand Kit + Stripe Checkout + UI cards


**Status**: ✅ Implemented, tested, E2E confirmed on independent hosting

### ما تم بناؤه:
1. **`/app/backend/modules/freebuild/html_validator.py`** (جديد) — 8 طبقات فحص:
   - بنية HTML (DOCTYPE, html, head, body, title, lang, dir, viewport)
   - تطابق الـtags (parser ذكي يكتشف unclosed/mismatched)
   - الروابط الداخلية (`<a href="#X">` بدون `<section id="X">`)
   - الصور (alt + ممنوع localhost/backend URLs)
   - تحليل JS basic (تطابق أقواس)
   - تحليل CSS (تطابق braces)
   - فحص أمني (يكتشف Stripe keys, AWS keys, GitHub tokens مسربة)
   - حجم الـHTML
   - يُرجع `{ok, summary, critical[], major[], minor[]}`

2. **Auto-Heal Loop في chat endpoint**:
   - بعد كل توليد HTML، الـValidator يفحص آلياً
   - لو فيه مشاكل → استدعاء Claude Sonnet 4.5 بـ`format_validation_for_ai()` يطلب الإصلاح
   - يفحص المُحَسَّن، يقبله **فقط** لو قلّ عدد المشاكل
   - يخزن `last_validation` على المشروع للوحة الأدمن

3. **Paywall على Export**: `export-source` يرجع HTTP 402 إن `code_unlocked=false`

### E2E Test (موقع لياقة بدنية → استضافة مستقلة):
1. ✅ AI ولّد HTML نظيف من المرة الأولى (32.9KB, validator: ✅ OK)
2. ✅ محاولة export قبل الدفع → HTTP 402 "ميزة مدفوعة"
3. ✅ تفعيل unlock بـ$100 tier=code_only → success
4. ✅ تصدير ZIP (7.8KB) → 3 ملفات نظيفة (index.html + README + LICENSE)
5. ✅ رفع على `python3 -m http.server 9100` (استضافة مستقلة تماماً)
6. ✅ تشغيل في playwright → 200 OK، title صحيح، 0 console errors
7. ✅ 11/11 امتثال (DOCTYPE, RTL, viewport, privacy, terms, WhatsApp, NO Zenrex، NO localhost)
8. ✅ تصميم احترافي: Hero قوي، CTA مزدوج، Stats، WhatsApp button

### اختبار الـValidator على HTML مكسور حقيقي (unit test):
- Input: div بدون closing, broken anchor, localhost image, missing title/viewport, broken JS
- Output: 1 critical + 7 major + 4 minor = ✗ FAIL
- Heal prompt مُولَّد جاهز للـAI

### Future Tier-2 / Tier-3 (مقترحات سابقة):
- 🟡 P1: Multi-Page Architecture (index + about + contact + products)
- 🟡 P1: Site Health Score (0-100 بطاقة تقييم)
- 🟢 P2: AI Memory & Brand Kit (تذكر تفضيلات العميل عبر المشاريع)
- 🟢 P2: Proactive Guardian (تنبؤ بالفشل قبل ما يحصل)
- 🟢 P2: Visual Guardian (لقطة شاشة + Vision LLM)

## 2026-06-19 (الجلسة الرابعة) — 🛡️ Zenrex Guardian (Silent AI Supervisor)
- ✅ Distress Detection (20+ كلمة عربية بأوزان)
- ✅ Auto-intervention بـClaude Sonnet 4.5
- ✅ Admin Dashboard على `/admin/guardian`
- ✅ Cooldown ذكي + سجل تدخلات

## 2026-06-19 (الجلسة الثالثة) — Source Code Export
- ✅ ZIP فيه index.html + assets + README + LICENSE
- ✅ يحذف Zenrex footer للسورس المدفوع

## 2026-06-19 (الجلسة الثانية) — UI Polish + AI Behavior
- ✅ إزالة Z الأحمر، إصلاح text glitch، قاعدة Information First

## 2026-06-19 (الجلسة الأولى) — AI Compliance Layer
- ✅ 4-stage machine + 15/15 امتثال + رفض المحتوى الممنوع


- ✅ `GET /export-source` يولّد ZIP (index.html + assets + README + LICENSE)
- ✅ يحذف Zenrex footer للسورس المدفوع
- ✅ اختبار على موقع غريب (متحف الجوارب) — رُفع على استضافة مستقلة وعمل 100%

## 2026-06-19 (الجلسة الثانية) — UI Polish + AI Behavior
- ✅ إزالة شعار Z الأحمر من الـthinking bubble
- ✅ إصلاح text glitch (polling يحافظ على `agent_steps`)
- ✅ قاعدة "Information First" في الـprompt

## 2026-06-19 (الجلسة الأولى) — AI Compliance Layer
- ✅ 4-stage machine + 15/15 امتثال + رفض المحتوى الممنوع

## Original Problem Statement
Deploy Zenrex Farm to the cloud, expand the Zenrex AI Brain to specialized modes, sever ties with Emergent integrations for 100% independence, and build a unified Brand Manager. Within Zenrex Farm, develop a "Kids PWA" — a TikTok-style video aggregator for kids with strict Parent/Child roles, automated targeted scraping, pre-caching for instant playback, and dedicated sections for prayers and rewards.

## User
- **Owner**: Zoheer Z. (Saudi, Arabic Saudi dialect preferred)
- **Children**: Hussein (~10 yrs, older, fuller face, voluminous curly hair) & Abbas (~7-8 yrs, younger, slimmer face, tidier curls)

## Production Infrastructure
- **VPS**: Hetzner — `91.98.154.148`, domain `zenrex.ai`
- **SSH key**: `/root/.ssh/zerax_deploy`
- **Web root**: `/opt/zerax/frontend/build/` (React build) + `/var/www/pwa_kids/` (Kids PWA assets)
- **Backend**: Docker compose at `/opt/zerax` (FastAPI + MongoDB)
- **Deploy script**: `/app/deploy/deploy.sh`

## Kids PWA (Production Status)
- **URL**: `https://zenrex.ai/kids`
- **Manifest**: `/var/www/pwa_kids/manifest.webmanifest` → name "زنركس كيدز برو"
- **Service Worker**: `/var/www/pwa_kids/sw.js` (v5 — bumped Jun 18, 2026)
- **Icons**: `/var/www/pwa_kids/icon-192.png`, `icon-512.png`
- **Auth**: Parent (`zoheer@zenrex.ai` / `Zenrex@2026`), Child accounts in MongoDB
- **Features Live**: Parent dashboard (dynamic kid mgmt, manual URL download, auto-bot config),
  Child TikTok-style feed with SW media caching, achievements tab, prayer tab.


## Kids PWA (Zenrex Play /play) — 2026-06-18 Refresh
- **URL**: `https://zenrex.ai/play` (legacy `/kids` redirects here)
- **Production assets**: `/var/www/pwa_play/` on VPS — synced via rsync from `/app/zenrex_play/`
- **Source-of-truth (this repo)**: `/app/zenrex_play/` (index.html, app.js, sw.js, manifest.webmanifest, icon-192.png, icon-512.png)
- **Service Worker**: `zenrex-play-v2-quran-mushaf` (no-cache HTML, cache-first shell assets)
- **Bottom Nav (5 tabs)**: 🏠 الرئيسية · 📿 الدين · 📖 القرآن · 🎯 المهام · 👤 حسابي
- **Quran Tab**:
  - Memorization Map (114 surahs colored: 🟩 approved · 🟨 pending · ⬜ empty)
  - Parent-assigned plan progress bar
  - Surah list with reciter selector (11 sheikhs)
  - Read mode + **Tasmee'** mode (blur text, child must recite, "أظهر الآية" reveal button)
  - Audio repetition (×1 / ×3)
  - Child audio recording → parent review → points
  - **🕋 Mushaf Viewer**: 604 pages rendered as authentic Madinah-style pages
    (cream paper background, Amiri Quran font, golden ayah-number circles)
    using `api.alquran.cloud/v1/page/{N}/quran-uthmani`. Tap any ayah →
    plays audio via `cdn.islamic.network/quran/audio/{128|64|192}/{reciter}/{global_ayah}.mp3`.

## Deployment (2026-06-18)
- `bash /app/deploy/deploy.sh zenrex.ai` now also rsyncs `/app/zenrex_play/` → VPS `/var/www/pwa_play/`.
- Backend (`freebuild_chat.py`) was out-of-sync — pulled fresh from VPS to local (5083 lines), now matches.

## 2026-06-19 — Parent View-as-User + Weekly Challenge + Random Shuffle
- **Parent View-as-User toggle**: Parent dashboard top-right `👤 وضع المستخدم` button →
  switches the same authenticated parent into a child-like browsing experience
  (videos, religion, Quran, mushaf, tasks, profile). Floating top-left
  `🔙 لوحة ولي الأمر` button restores parent dashboard. State persisted in
  `localStorage.zp_view_as_user`. The parent's browsing is NOT counted in any
  kids' competition / leaderboard (frontend-only toggle, no extra account needed).
- **Weekly Challenge** (new parent tab `🏆 التحدي الأسبوعي`):
  - Backend (`/app/backend/modules/freebuild/freebuild_chat.py` ~lines 3505–3650):
    - `POST /kids/challenge/create` — body: `surah_nums (JSON)`, `days`, `mode (manual|random)`, `random_count`
    - `GET  /kids/challenge/active` — returns current challenge + per-child leaderboard
    - `POST /kids/challenge/end` — declares winner & awards 100 pts via `kids_points`
    - `GET  /kids/challenge/history`
    - Mongo collection: `kids_weekly_challenges` `{id, parent_id, surah_nums[], days, start_at, end_at, mode, status, winner_email}`
    - Progress is computed dynamically by joining `kids_quran_submissions` (status='approved',
      surah_num ∈ challenge.surah_nums, reviewed_at within window).
    - Ranking: unique surahs done ▶ total approved count ▶ accumulated points.
  - Frontend (parent UI): create form with manual/random modes (1–10 surahs random),
    1–30 day duration; live leaderboard with progress bars & 🥇🥈🥉 badges; end-now button.
  - Frontend (child UI): banner at the top of Quran tab showing active challenge,
    days remaining, target surahs, and live leaderboard pills (own row highlighted).
- **Stronger video randomness**: `loadVideos()` now uses `crypto.getRandomValues`-backed
  Fisher-Yates; fresh/old interleave is followed by a FINAL random pass over the whole
  merged list so EVERY login = a completely different feed order. Added top-bar
  `🎲` shuffle button that reorders the current feed (no refetch) and scrolls back

## 2026-06-19 — Critical Fixes (Mushaf, Anti-Cheat, Parent Review, Videos)

### 🐛 Critical Bugs Fixed
- **deploy.sh wiped uploaded videos**: rsync `--delete` was deleting `/opt/zerax/backend/backend/uploads/*` on every deploy. Added `--exclude="uploads/" --exclude="backend/uploads/" --exclude="static/uploads/" --exclude="static/videos/"`. Cleaned 39 orphan DB records pointing to deleted files.
- **Mushaf disabled buttons swapped**: `mushaf-prev` (forward) was disabled at page 1 instead of 604. Fixed.
- **Surah → page mapping bug**: Al-Baqarah (surah 2) had start_page=1 instead of 2. Updated full 114-surah verified array.

### 🛡️ Anti-Cheat System (CRITICAL)
- **24h Cooldown per task**: `kids_upload_recording` rejects with HTTP 429 if same `(child_email, task_id)` was submitted in last 24h.
  - Exception: two-step tasks allow `phase='after'` if previous was `phase='before'`.
- **No more auto-points for tasks/dhikr**: Only `prayer` recordings auto-award. Tasks/dhikr now save with `status='pending'` and `proposed_points`, awaiting parent approval.
- **`/kids/points/award` also enforces 24h cooldown** when `kind='task'` and `meta.task_id` set.

### 👨‍👩‍👧 Parent Review Workflow
- New endpoints:
  - `POST /kids/recordings/{rec_id}/approve` → awards `proposed_points`, marks status='approved'
  - `POST /kids/recordings/{rec_id}/reject` → marks status='rejected', stores reason
  - `GET  /kids/notifications/count` → returns `pending_recordings + pending_quran`
  - `GET  /kids/tasks/today_status?child_email=` → per-task: `locked_today`, `pending_review`
- Parent dashboard:
  - 🔴 Red notification badge with pending count on tabs `📹 التسجيلات` and `📖 مراجعة القرآن`
  - Auto-refresh every 30s while parent dashboard is open
  - Each pending recording has ✅ اعتمد / ❌ ارفض buttons (with reason prompt)
  - Recordings sorted: pending first
- Child UX:
  - Upload toast now shows "⏳ أُرسل لولي أمرك للمراجعة" instead of fake "+5 نقطة"
  - Tasks completed today appear with badge "⏳ ينتظر المراجعة" or "✅ تم اليوم — بكرة!"
  - Locked tasks are dim + button disabled

### 🎮 Gamification Roadmap (Backlog — was requested to organize)
- Persistent badges: بطل الأسبوع 🏆 · أسطورة الشهر 🌟 · حافظ المبتدئ 📖 · حافظ السبع الطوال 🕋
- Fair design: تحدّي تعويضي · مضاعفة نقاط الأخ الأصغر · سور Bonus اليوم
- Engagement: عدّاد تنازلي · push notifications · صوت + كونفيتي عند الموافقة · شريط تقدّم يومي
- Insights: إحصائيات الوقت الأفضل · السور الصعبة · تقرير شهري PDF
- Beyond Quran: تحدّي الأذكار · تحدّي الصلوات · تحدّي المهام البيتية
- Father's personal space: مجلد قراء مفضّلين + ملاحظات تدبّر + Word-by-word highlight


  to top — kids can spin a new order on demand.
- **Auth fix**: logout now also clears `zp_view_as_user` so a fresh login starts in
  the correct role.




## Changelog

- **2026-06-18 (v35 — CRITICAL: Root SW hijacking + Category labeling bug)**:
  **ROOT CAUSE FOUND** after user reported "حرف ز شعار" splash + broken site +
  no videos showing. Two compounding bugs:
  
  **BUG #1 — Root PWA hijacking `/kids` (the "two versions" problem)**:
  - The main Zenrex platform (`https://zenrex.ai/`) registered a SW at `scope='/'`
    via `/service-worker.js`, which intercepted EVERY navigation including `/kids`.
  - Users who had installed the Zenrex main PWA: when they opened `/kids`,
    the root SW returned the cached React index.html instead of the Kids HTML,
    showing the "Z" splash + main app shell over the kids page.
  - **Fix A** (`/opt/zerax/frontend/build/service-worker.js` + public):
    * Bumped CACHE_VERSION to `zenrex-pwa-v2-skipkids` (forces re-install)
    * Added `if (url.pathname === '/kids' || url.pathname.startsWith('/kids/')) return;`
      at top of fetch handler — bypass /kids completely
    * Removed `/kids` from the `caches.match('/')` offline fallback
  - **Fix B** (`critical-fixes-v35` section in kids HTML — runs EARLY):
    * On load, calls `navigator.serviceWorker.getRegistrations()` and
      unregisters any SW whose scope doesn't contain `/kids`
    * Deletes any cache key starting with `zenrex-pwa` / `zenrex-shell`
    * This force-evicts the hostile SW even on installed PWAs
  
  **BUG #2 — All videos hardcoded `category='curated'`**:
  - The legacy `loadAndShuffleChildFeed` (v17) mapped every video to
    `category: 'curated'` regardless of its real DB value.
  - Result: every category filter showed 0 videos (no video matched
    `quran`, `educational`, etc.). Looked like "no videos".
  - **Fix** (v35): Override `loadAndShuffleChildFeed` with a new
    `v35ForceRenderFeed()` that uses `it.category` from the API.
    Also runs every 8s as a self-healer: if videos array is empty OR all
    tagged `curated`, re-fetches.
  
  **Other additions in v35**:
  - Full-screen loading UI (`#v35-feed-loading`) with spinner + retry button.
    Hidden once videos render successfully. Times out after 3 failed attempts.
  
  **Verified end-to-end via Playwright on real prod URL**:
  - SW scopes after page load: `['https://zenrex.ai/kids']` only (root SW gone)
  - Cache keys: only `zenrex-kids-*` (no `zenrex-pwa-*`)
  - `APP_STATE.videos`: 26 items with real categories `['أخبار','educational','quran']`
  - 26 `.video-slide` elements in DOM, 26 `<video>` elements
  - 1 video playing simultaneously (single-video fix from v34 confirmed)
  - `muted=false, volume=1` after first body click (audio unlock works)
  - Title "زنركس كيدز برو" (correct PWA, not main app)
  - SW bumped to `zenrex-kids-v11-v35`

## Changelog

- **2026-06-18 (v34 — COMPREHENSIVE PARENT DASHBOARD + Audio/Video fixes)**:
  Complete rebuild of parent dashboard from scratch (no widget relocations).
  Fixes for audio overlap, slow video preload, broken category filter, camera permissions.
  
  **Backend additions**:
  - `POST /kids/video-metadata`: yt-dlp --dump-json title/thumb/duration without download
  - `GET /kids/parent-summary`: aggregated kids+stats endpoint
  
  **Frontend `parent-final-v34` (282KB total page)**:
  - **Audio fix**: `enforceSingleVideo()` pauses all others when one plays + IntersectionObserver aggressively pauses off-screen videos
  - **Preload speedup**: real `<link rel="preload" as="video">` for next 2 + preload=auto only for current ±2 + strips harmful crossOrigin
  - **Category filter works**: drawer → `zkApplyCategory(id)` → display:none on non-matching slides + scroll to first visible
  - **9-tab parent dashboard** (Videos/Cats/Tasks/Dhikr/Prayers/Kids/Stats/Bot/Settings) all self-contained, no relocations
  - **Camera permission wrapper**: friendly modal with retry on NotAllowedError/NotFoundError/etc + auto-fallback constraints
  - **Sticky red Logout button** on parent bar
  - **Video URL preview**: paste URL → 🔍 معاينة → see title/thumb/duration → 📥 download + AI categorize
  - **Stats panel**: per-kid cards with total points, monthly SAR, prayer/task recording counts, recent activity ledger + recordings with ▶ playback link
  - Child UI completely untouched (4-tab UX preserved)
  
  **SW bumped** to `zenrex-kids-v10-v34`.


  Major restructure of parent dashboard into a proper control center plus
  P0 bug fixes for audio and video preload.
  
  **Backend additions (`/opt/zerax/backend/modules/freebuild/freebuild_chat.py`)**:
  - **`/kids/categories` (GET/POST/DELETE)**: Parent-managed video categories.
    Defaults seeded per parent: الكل, ألعاب, قرآن, تعليمي.
  - **`/kids/parent-tasks` (GET/POST/DELETE)**: Parent-managed daily tasks.
    Includes `needs_camera` flag, `points` per task, `icon`. Defaults seeded.
  - **`/kids/auto-categorize` (POST)**: Single video AI categorization via
    Claude Haiku 4.5 (Emergent LLM Key). Reads video title, returns category id.
  - **`/kids/auto-categorize/all` (POST)**: Batch categorize all uncategorized
    approved videos (max 50/call). Uses helper `_categorize_one`.
  - **Fallback**: When LLM unavailable, falls back to keyword matching.
  - **Default categories/tasks** are auto-seeded on first GET call per parent.
  
  **Frontend `parent-console-v33` section**:
  - **AUDIO FIX**: Removes harmful `crossOrigin='anonymous'` set by v22 (was
    preventing playback on Chrome Android per v25 PRD note). Force-unmutes
    all videos on first user tap (touchstart/click capture once).
  - **VIDEO PRELOAD FIX**: Prefetches next 2 videos as no-cors fetch warm-up,
    sets `preload="auto"` only for current+next-2, `preload="metadata"` for rest.
    Eliminates the slow-to-start issue.
  - **Categories drawer**: Pills bar (`.pills-bar`) hidden. Replaced with
    floating `🏷️` button (`#v33-cat-fab`) → opens bottom sheet drawer.
    Selecting a category triggers the existing pill click for filter logic.
  - **Parent dashboard restructure**: 7 tabs strip at top of parent-page:
    🎬 Videos / 🏷️ Categories / 🎯 Tasks / 📿 Dhikr / 🕌 Prayers / 📊 Stats / ⚙️ Settings.
    Legacy parent UI is relocated into the appropriate tabs.
  - **Logout button**: Prominent red button on parent bar (sticky top) + 
    full-width button in Settings tab. Clears all localStorage + reloads.
  - **Categories CRUD UI**: Inline form (icon + title) + list with delete buttons.
    System categories (like "الكل") can't be deleted.
  - **Tasks CRUD UI**: Inline form (icon + title + points + needs_camera) + list.
    Soft-delete (sets `is_active=false`).
  - **Stats tab**: Per-child cards showing total points, today, streak, monthly SAR.
    Recent activity ledger. Pulls from `/kids/points/summary`.
  - **AI button**: "🤖 إعادة تصنيف الفيديوهات الموجودة" in Videos tab
    calls `/kids/auto-categorize/all` to retro-categorize all videos.
  - **Service Worker bumped** to `zenrex-kids-v9-v33`.
  
  **Child UI untouched** (per user instruction). Only parent role sees the
  new dashboard via `body[data-zk-role="parent"]` CSS selector.
  
  **Verified end-to-end**:
  - `GET /kids/categories`: returns 4-5 default + custom categories ✓
  - `GET /kids/parent-tasks`: returns 6 default tasks ✓
  - `POST /kids/auto-categorize` (single): Claude Haiku correctly tagged
    "تحصَّن بالقرآن العظيم" → category=`quran` ✓
  - `POST /kids/auto-categorize/all` (batch): 25 videos categorized in ~60s ✓
  - Pills-bar `display: none`, FAB + drawer present in DOM ✓

## Changelog

- **2026-06-18 (v32 — Real points engine + production polish)**:
  Closed the loop on the points/rewards system end-to-end so kids' actions
  actually persist server-side instead of localStorage-only.
  
  **Backend changes (`/opt/zerax/backend/modules/freebuild/freebuild_chat.py`)**:
  - **Relaxed child_email validation**: Now accepts any `@kids.*` domain (was hardcoded
    to `@kids.local`). Fixes upload 403 for the real `@kids.zenrex.ai` accounts.
  - **`POST /kids/recordings/upload`**: New fields `rec_type` (prayer|task|dhikr),
    `task_id`, `task_title`, `points`. Auto-awards points (default: prayer=10, task=5)
    on successful upload by inserting into new `kids_points` ledger.
  - **`POST /kids/points/award`** (NEW): Client-driven point award.
    Form: `child_email`, `kind`, `value`, `meta_json`. Returns running total.
  - **`GET /kids/points/summary?child_email=...`** (NEW): Real totals, today/week
    breakdown, by_kind aggregation, streak (consecutive days), monthly SAR.
  - **`GET /kids/achievements`**: Refactored to use real `kids_points` + 
    `kids_recordings` collections (dropped hardcoded `hussain@kids.local` baselines).
  
  **Frontend `production-polish-v32` section (in MongoDB published HTML)**:
  - **Hide reactions on non-home tabs**: Real CSS selectors targeting
    `.side-controls`, `#share-btn`, `#comment-drawer` (v31 had wrong selectors).
  - **Backend points sync**: Intercepts `window.alert` calls matching dhikr/task
    completion messages and POSTs to `/kids/points/award`. Also wraps `window.fetch`
    so any task recording upload gets `rec_type=task` + correct `points` injected.
  - **Live profile stats**: Pulls from `/kids/points/summary` on profile tab,
    overrides localStorage display with real total, streak, and adds a
    "today" pill (`#v32-today-pill`).
  - **Strong headphones warning** (`#v32-headphones`): Red banner shown on prayer
    card click ("لازم تلبس السماعة... عشان صوت أبوك ما يدخل في تسجيل صلاتك").
  - **Auto-pause home videos when leaving home tab** (battery + audio focus).
  - **Service Worker bumped** to `zenrex-kids-v8-v32` to force update on existing
    PWA installs.
  
  **Verified end-to-end via prod curl + Playwright**:
  - `POST /kids/points/award` returns running total.
  - `GET /kids/points/summary` returns correct aggregations by kind + streak.
  - `POST /kids/recordings/upload` with `rec_type=task` awards points automatically.
  - `GET /kids/achievements` shows real prayer/task counts.
  - CSS `display:none` confirmed on `.side-controls` when body[data-tab=profile].
  - Login API works for `حسين@kids.zenrex.ai` with PIN 1234.


- **2026-06-18**: Generated custom anime PWA logo featuring father (white thobe + glasses) and
  two sons (casual hoodies, peace sign + thumbs-up) on Jeddah Corniche evening background with
  metal railing. Deployed `icon-192.png` & `icon-512.png` to `/var/www/pwa_kids/`. SW bumped v4→v5.
  Old icons backed up as `.bak.<timestamp>`. All approved variations preserved at
  `/app/frontend/public/logo_previews/` (logo_v9_corniche_evening.png is the deployed one).
- **2026-06-18**: Fixed Kids PWA install bug — `/kids` was loading the main Zenrex manifest +
  stale `data:` URI manifest with scope `/`, causing iOS/Android to install it as the main app
  shortcut instead of a separate PWA. Cleaned the published-site HTML in MongoDB — removed 3
  bad manifest links, stale `<section id="head">`, root-scope SW registration. Injected proper
  `<link rel="manifest" data-pwa="kids" data-real="1" href="/kids/manifest.webmanifest">` plus
  apple-touch-icon + apple-mobile-web-app-capable. Fix script at `/app/logo_gen/fix_kids_pwa.py`.

- **2026-06-18**: Added "مكتبة الفيديوهات المعتمدة" section to Parent Dashboard so the parent
  can see ALL approved videos (previously only the empty Pending queue was shown — appeared as
  if videos disappeared). Endpoint: `/api/freebuild-chat/kids/bot/approved` returns 26 docs.
  Each card has video preview + preview link + delete button.

- **2026-06-18 (v25 — CRITICAL PRODUCTION FIX: Video Playback)**:
  Root cause of "videos spin forever and don't play" diagnosed and fully fixed.
  
  **3 layered issues found**:
  1. **HEVC codec everywhere**: 26 of 27 downloaded TikTok videos were H.265/HEVC.
     Most browsers (Chrome on Android, Firefox, older iOS) cannot decode HEVC.
     This is the PRIMARY cause of infinite buffering on mobile.
  2. **Service Worker was caching media** (v5/v6): SW was caching video files which
     broke Range requests — cached 200 responses can't satisfy Range, causing infinite
     buffering after first load. nginx already serves videos with `Cache-Control: max-age=31536000 immutable`
     so HTTP cache handles it perfectly; SW caching was harmful.
  3. **`muted=false` + `crossOrigin='anonymous'`** prevented mobile autoplay + forced
     unnecessary CORS mode.
  
  **Fixes applied**:
  - **Batch transcoded all 27 videos** HEVC → H.264 (libx264 High profile, yuv420p) via
    background ffmpeg. Space went from ~30MB HEVC + ~80MB temp → 18MB H.264. HEVC backups deleted.
  - **SW v7** (`/var/www/pwa_kids/sw.js`): COMPLETE REWRITE. Media files now pass-through
    (no SW interception). Only HTML + manifest + icons cached. Range requests work natively.
    SW activate clears all old `zenrex-kids-v5/v6/media-v1` caches.
  - **yt-dlp download endpoint** (`POST /media/download`) updated to:
    `-f bv*[height<=720][ext=mp4][vcodec*=avc1]+ba[ext=m4a]/...` + `-S vcodec:h264` +
    `--recode-video mp4` + `--postprocessor-args "-c:v libx264 -preset fast -crf 23 -c:a aac -movflags +faststart"`.
    All future downloads will be H.264 + faststart (instant playback, no remux needed).
  - **Frontend video creation**: `muted=true`, `playsinline`, `webkit-playsinline`, `preload=auto`,
    `loop=true` for TikTok-style continuous playback. Removed harmful `crossOrigin='anonymous'`.
  - **New section `video-playback-fix-v25`**:
    * Tap-to-unmute floating banner
    * Auto-detect stuck videos (>8s no progress) → force reload
    * Error overlay with retry button per video
    * Defensive: clears any leftover `media-v1` / `v5` / `v6` caches on every page load
    * Forces SW update on existing PWA installs

- **2026-06-18 (PRAYER MODULE v23)**: Built new Prayer Studio. Parent dashboard gets 5 prayer
  cards (Fajr/Dhuhr/Asr/Maghrib/Isha) with 🎤 سجّل button → records voice via MediaRecorder
  (audio/webm + echoCancellation). Backend adds `DELETE /kids/audio/{id}`, `POST /kids/audio/{id}/prayer`,
  `POST /kids/audio/{id}/order`. Child side has fullscreen camera studio (`#pc-shell`): tap a
  prayer tile → camera opens (front default, flip button) + parent's audio plays via Audio() →
  video+mic recording starts (echoCancellation on child mic; headphones recommended for clean
  audio isolation) → auto-stops at 16 minutes → uploads to `/kids/recordings/upload` for parent review.

- **2026-06-18 (v24 — 4 user fixes)**:
  1. **Main feed loads for parent too**: `loadAndShuffleChildFeed` now accepts both parent & child
     roles (parent can verify what the kid sees). Random shuffle on every load (Fisher-Yates).
  2. **Inline preview modal** (`#vpm-modal`): Replaced `window.open()` redirect for preview buttons.
     Plays video/audio in a centered black modal — no more redirecting to main Zenrex app.
     Reusable via `window.previewMedia(url, title, type)`.
  3. **Prayer audio supports file upload**: Each prayer card now has 📁 رفع button + 🎤 سجّل button.
     File upload shows confirmation with duration + size + prayer name before uploading.
     Supports any audio/* format. No size limit beyond FastAPI default (~100MB), good for 20+ min recordings.
  4. **YouTube cookies upload UI**: Added prominent red box in URL-download section with step-by-step
     Arabic instructions on how to export cookies via "Get cookies.txt LOCALLY" Chrome extension.
     One-click upload to `POST /media/cookies/upload?platform=youtube`. Fixes YouTube bot-detection.
  
  **Parent side** (in Parent Dashboard, section `pm-parent-1`):
    - 5 prayer cards: الفجر / الظهر / العصر / المغرب / العشاء (each with emoji icon)
    - Tap "🎤 سجّل" → records parent's voice via MediaRecorder (audio/webm)
    - Tap "▶" to preview, "🗑" to delete
    - Status shows "✅ مسجّل" or "لم يُسجّل بعد"
    - Uses echoCancellation + noiseSuppression at capture
    - Backend: POST `/api/freebuild-chat/kids/audio/upload` (existing) +
      `POST /kids/audio/{aid}/prayer` (NEW — tag with prayer id) +
      `DELETE /kids/audio/{aid}` (NEW)
  
  **Child side** (full-screen overlay `#pc-shell` triggered from nav prayer button):
    - Sees 5 prayer tiles in same order as parent's recordings
    - Disabled prayers grayed out if parent hasn't recorded yet
    - Tap a tile → opens fullscreen camera studio
    - Front camera default, "🔄" button switches front/back
    - "●" button starts: video+audio recording (echoCancellation enabled for child mic) +
      parent's audio plays via Audio() element through earphones
    - Timer counter, **auto-stop at 16 minutes** (configurable)
    - Mute/unmute parent audio button (🔊/🔇)
    - On stop: uploads child's recording via `POST /api/freebuild-chat/kids/recordings/upload`
      with audio_track = prayer name → parent can review in their dashboard
    - HEADPHONES REQUIRED warning shown on the screen ("🎧 تأكد من توصيل السماعات قبل البدء")
  
  **Architecture decision**: Since child uses Bluetooth/wired headphones, parent's audio
  goes directly into the child's ear (not played through speakers) → mic only picks up
  child's voice. echoCancellation = belt-and-suspenders defense for any acoustic leakage.

- **2026-06-18 (UI cleanup)**: Removed orphan "عنوان الفيديو / التصنيف" floating overlay
  from bottom-right corner (legacy `.video-info` div, hidden via `display:none`).
  `freebuild_published_sites.zenrex-kids-pro` HTML (308KB → ~108KB = 64% reduction).
  Backup preserved in same doc as `backup_html_pre_cleanup_v1`. Removed sections:
  `bot-page`, `bottom-nav-update`, `bottom-nav-fixed`, `pwa-sw-inline`, `fixes-core`,
  `init-app-fix`, `bot-save-fix`, `auto-scheduler`, `approval-system`, `reference-samples`,
  `add-by-url`, `cookies-link`, `approval-preview`, `onetime-cleanup`, `ui-bugfixes-v6`,
  `ui-cleanup-v7`, `directed-scraping-v9`, `auth-roles-v10`, `kids-experience-v12/v13/v16`,
  `dynamic-children-v19`, plus 2 dead `<script>` blocks binding to removed `#bot-submit`.
  Fixed JS syntax error from orphan `}).catch(...)` left by earlier SW removal.
  Exposed `window.APP_STATE`, `window.renderVideos`, `window.loadApproved` so post-cleanup
  sections (v17/v18/v22 etc.) can access them. Result: app loads with 0 JS errors,
  approved videos render in parent dash (26 cards) and child feed (26 playing videos),
  bottom nav clean (3 buttons), URL-download triggers immediate refresh. Live sections:
  `auth-roles-v11`, `pwa-install-v8`, `kids-experience-v17`, `parent-add-video-v18`,
  `zk-clean-slate`, `bot-config-v20`, `server-children-v21`, `video-preload-v22`.
- **2026-06 (prior)**: Built full Parent/Child backend auth, dynamic child mgmt widget,
  fullscreen TikTok video UI, yt-dlp fallback chain `/best`, manual URL downloader,
  auto-bot config UI (cookies + keywords + targeted usernames), deep DB purge of
  `big_buck_bunny` mocks, SW v3/v4 caching strategy, 1-year HTTP cache for videos.

## Open Issues / Backlog
### P0 (None currently)

### P1 — TikTok Channel Bulk Importer (commercially valuable)
- Single field: paste channel URL → "اسحب كل القناة" button → background job pulls all videos
- Uses existing `yt-dlp` infra + cookies. Progress bar via WebSocket or polling.
- Cleaner UX than current bot-config-v20 widget.
- Status: NOT STARTED.

### P1 — Prayer Module — Reorder UI
- Parent can record per prayer, but cannot YET drag-reorder the 5 cards (currently fixed order Fajr→Isha).
- If needed: add `order` field via existing `POST /kids/audio/{aid}/order` endpoint (already created).

### P1 — Prayer Recordings Review Tab
- Parent dashboard needs a tab showing kid's prayer-recordings (`kids_recordings` collection).
- Endpoint `GET /api/freebuild-chat/kids/recordings` already exists — just needs UI.

### P1 — Failed (Red) Video Downloads Not Cleaned Up
- User reports: videos that failed to download still show as red/failed in DB.
- Previous agent claimed fix but user confirmed it's NOT done.
- Action: Audit `freebuild_media_assets` collection, build cleanup job for failed entries,
  add admin UI to bulk-purge red items.
- Status: NOT STARTED (user explicitly said "نعالجها بعدين").

### P2 — Points & Rewards System
- ✅ **DONE (2026-06-18, v32)**: Real `kids_points` ledger + `/kids/points/award`,
  `/kids/points/summary`, `/kids/achievements` all use real DB data. Frontend syncs
  via fetch interception + alert hooks. Profile shows live total + today pill.

### Future / Backlog
- Automated Travian Account Registration via 2captcha.
- Backblaze B2 integration for storage when Hetzner VPS fills up (currently ~3%).
- Mobile native iOS app wrapper for App Store.

## Commercial Export Plan (Future)
The current Kids PWA serves as a prototype for a multi-tenant commercial product:
- Strip out: prayer module + achievements (those are personal).
- Keep: parent-child auth, TikTok channel bulk import, video moderation flow,
  approved feed, custom branding (logo per tenant).
- Sell as a FreeBuild template: "تطبيق فيديو آمن للأطفال بإشراف ولي الأمر".
- Tenants get their own slug under `/s/{tenant-slug}` with their own branding.

## Architecture Notes
- Monolithic PWA HTML file approaches 300k chars — use `search_replace` carefully.
- All backend routes prefixed `/api`.
- MongoDB collections: `users` (parents + dynamic kids), `freebuild_media_assets`.
- Service Worker: Network-first for HTML, Cache-first for media (1-year HTTP cache).

## Test Credentials
- Parent: `zoheer@zenrex.ai` / `Zenrex@2026`
- Child 1: `حسين@kids.zenrex.ai` / `1234`
- Child 2: `عباس@kids.zenrex.ai` / `5678`

## Recent Logo Reference Assets
- Final approved logo: `/app/frontend/public/logo_previews/logo_v9_corniche_evening.png`
- All variations: `/app/frontend/public/logo_previews/logo_v{5..9}_*.png`
- Master 1024px: `/app/logo_gen/final_icons/icon-1024.png`
- Source reference photos: `/app/logo_gen/real_*.jpg`, `/app/logo_gen/jeddah_*.jpg`
- Generation scripts: `/app/logo_gen/gen_v{2..9}.py`
