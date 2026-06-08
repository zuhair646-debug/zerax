# Zitex Changelog


## 2026-02-15 (c) — 🚀 تغيير اللغة الفوري الكامل + Auto-Detect + Banner ✅

**الشكوى**: "لما أغير اللغة لازم أعمل refresh، والأقسام الأساسية (إنشاء المواقع، التطبيقات...) ما تتغير". + "اسم الموقع Zitex ما يتغير".

**Root cause** (3 طبقات):
1. **Lazy chunk loading**: `pageTranslator` كان lazy-imported، فلو فشل chunk، الترجمة ما تشتغل.
2. **Early return عند `target === currentTarget`**: منع re-sweep بعد re-renders من React.
3. **خنق Connection pool**: الـ sweeps المتعددة المتداخلة تطلق نفس fetch لنفس النصوص متوازية → الـ proxy connection pool يتشبع → كل الـ requests تنتظر إلى الأبد.

**الحل**:
- **استيراد مباشر** لـ `pageTranslator` (مش lazy) — يضمن توفره دايماً
- **شطب الـ early return** — كل تغيير لغة يطلق re-sweep كامل
- **Multiple staggered sweeps** (400ms, 1.2s, 2.8s, 5.5s, 9s, 14s) للقبض على المحتوى الـ lazy / async
- **Scroll-listener sweep** debounced 180ms — للأقسام تحت الـ fold
- **Single-flight sweep mutex** (`sweepRunning`/`sweepQueued`) — sweep واحد فقط في وقت واحد
- **In-flight fetch deduplication** (`inflight: Map<key, Promise>`) — لا تطلب نفس النص مرتين متوازية
- **Parallel chunk fetching** عبر `Promise.all` (بدل sequential)
- **`data-no-translate="true"`** على Navbar logo (اسم Zitex) + LanguagePicker trigger + options + DetectedLanguageBanner

**نتائج الاختبار (Playwright live)**:
| السيناريو | leftover_count |
|-----------|----------------|
| AR → EN (16s wait) | **0** ✅ |
| EN → FR (16s wait) | **1** (~99%) ✅ |
| FR → AR (3s) | restore فوري بدون reload ✅ |

اسم "Zitex" بقي **Zitex** في الـ 3 لغات بدون أي ترجمة.

**الميزة الإضافية**: `DetectedLanguageBanner` — toast صغير يظهر لما الـ geo detection يغير اللغة، يعرض "🇫🇷 Français · تم اكتشاف لغتك تلقائياً" مع زر "العربية" للتراجع. يختفي بعد 8 ثواني أو dismiss.

**ملفات معدلة/جديدة**:
- `/app/frontend/src/i18n/pageTranslator.js` (مكتوب من جديد — single-flight + dedup + Promise.all)
- `/app/frontend/src/i18n/index.js` (direct import + custom event dispatch)
- `/app/frontend/src/components/DetectedLanguageBanner.js` (جديد)
- `/app/frontend/src/components/Navbar.js` (`data-no-translate` على logo)
- `/app/frontend/src/components/LanguagePicker.js` (`data-no-translate` على trigger)
- `/app/frontend/src/App.js` (تركيب `<DetectedLanguageBanner />`)

---


## 2026-02-15 (b) — 🌐 Auto-Detect Visitor Language by Geo + Browser ✅

**الطلب**: المستخدم يبي اللغة تتعين تلقائياً حسب منطقة الزائر، بدون ما يحتاج يفتح الـ Picker. ولو غيّر يدوياً، نحترم اختياره.

**الحل** — اكتشاف بثلاث طبقات (`/app/frontend/src/i18n/geoLanguage.js`):
1. **Manual override يفوز دايماً**: مفتاح `zitex_lang_manual` في localStorage — يُحفظ فقط عند الاختيار اليدوي من Picker
2. **Browser language (instant)**: `navigator.language` (مثلاً `fr-FR` → `fr`) — يُطبَّق قبل أول render
3. **IP geolocation (background)**: ipapi.co + ipwho.is + geojs.io (fallbacks) — يرفع اللغة لـ country-based لو الزائر فرنسي ومتصفحه إنجليزي

**خريطة دولة → لغة** (curated): 130+ دولة مغطّاة (الخليج + شمال أفريقيا → ar، أوروبا → اللغات المحلية، أمريكا اللاتينية → es/pt، آسيا → اللغة الرئيسية لكل دولة...).

**حماية ضد الـ override الخاطئ**: لو `navigator.language` يطابق اللغة الحالية، ما نسمح للـ geo IP يبدلها (المستخدم وضع لغة متصفحه قصداً).

**التحقق (Screenshot Test)**:
- ✅ زائر بـ `navigator.language = fr-FR` يفتح الصفحة → كل النصوص ظهرت بالفرنسي مباشرة:
  - "Commencer gratuitement" (Start Free)
  - "Connexion" (Login)
  - "Tarifs" (Pricing)
  - "Construisez votre jeu" (Build your game)
  - "Plateforme Zitex — Créez des sites, applications, images et vidéos par IA"
  - شريط الإعلان: "Réduction de 20% sur l'abonnement Premium cette semaine · Utilisez le code ZITEX20"
- ✅ لما المستخدم يختار يدوياً من Picker، يُحفظ كـ manual choice → ما يُتدخّل فيه مرة ثانية
- ✅ الـ geo detection يجري بعد 600ms من البوت (ما يبطئ أول render)

**ملفات معدّلة/جديدة**:
- `/app/frontend/src/i18n/geoLanguage.js` (جديد — 145 سطر)
- `/app/frontend/src/i18n/index.js` (استبدال `localStorage.getItem('zitex_lang') || 'ar'` بـ `getInitialLanguage()` + background geo invocation)
- `/app/frontend/src/components/LanguagePicker.js` (`markManualChoice(code)` عند الاختيار اليدوي)

---


## 2026-02-15 — 🌍 Dynamic Full-Page Translation (97+ Languages) ✅

**المشكلة**: المستخدم اشتكى إن تغيير اللغة من Language Picker ما يترجم النصوص العربية الموجودة على الصفحة فعلياً.

**الحل** (`/app/frontend/src/i18n/pageTranslator.js` — أعيدت كتابته كامل):
- **MutationObserver قوي** يراقب `childList + subtree + characterData` معاً
- **معالجة re-renders من React**: لما React يبدل nodeValue للنص الأصلي (شائع جداً بسبب state updates)، نعيد تطبيق الترجمة من الكاش فوراً بدون API call
- **WeakMap لكل عقدة**: تخزين النص الأصلي + الترجمة المطبّقة حالياً لكل text node — يمكّن:
  - الرجوع للعربي بدون reload (instant restore)
  - منع double-translation
- **Self-mutation guard (`isApplying`)**: علم يحمي من اللوبات اللانهائية
- **كاش ثنائي**: في-الذاكرة `Map` + localStorage (cache forever per browser)
- **Debounced batching**: تجميع 250ms ثم batch من 35 نص في طلب واحد لـ Claude
- **استثناءات ذكية**: scripts/styles/code/inputs/contenteditable/`data-no-translate="true"`/إيموجي/أرقام بحتة

**التحقق (Screenshot Test)**:
- ✅ الصفحة العربية → اختيار English → كل النصوص اتترجمت (Start Free, Login, Pricing, Zitex AI Platform, Create your website or app with AI, Cinematic videos with Sora 2, …)
- ✅ `html.lang=en` و `html.dir=ltr` يتحدثان فوراً
- ✅ شريط الإعلان العلوي يتترجم
- ✅ Language Picker نفسه محمي بـ `data-no-translate` (الأسماء الأصلية تبقى بلغتها)
- ✅ Claude batch endpoint `/api/i18n/translate-batch` يرد 200 OK وترجمات دقيقة

**ملفات معدّلة**:
- `/app/frontend/src/i18n/pageTranslator.js` (re-write كامل، ~270 سطر)
- `/app/frontend/src/components/LanguagePicker.js` (إضافة `data-no-translate="true"`)

---


## 2026-06-05T09:49:30 — 🆕 Jun 5 2026 — AutoCoder Superpowers wired ✅

الـ7 أدوات (project_context, screenshot_url, plan_*, update_prd, project_health) صارت متاحة للـAutoCoder. screenshot_url يربط Vision passthrough تلقائياً.

## 2026-06-05T10:13:23 — 🔥 Jun 5 2026 — AutoCoder LIVE TEST: fixed /games/web routing autonomously

- Owner reported: clicking Games button on Landing → blank page
- Main agent acted as owner, sent task via /api/autocoder/chat as owner
- AutoCoder used 9 tools autonomously: screenshot_url (saw 'No routes matched /games/web' in console errors), read_file App.js + LandingPage.js, identified mismatch (button=/games/web vs route=/dashboard/games/web), edit_file App.js (added redirect route), git_status, git_add+commit+push
- Fix: Lines 127-128 in App.js — Route path /games/web with Navigate to /dashboard/games/web (if user) else /register; same for /games/mobile
- Verified live: /games/web now redirects to /register for guests (no more blank)
- Commit: 2f23385 (AutoCoder authored)

Bug Fixes shipped this session:
- Ghost Chat: asyncio.shield() around _persist_assistant_turn — partial saves now survive client disconnects (proven: conv a69204ba saved 18 tool_events from cut stream)
- screenshot_url: networkidle + 5s wait + 45s nav timeout — React SPAs render before capture
- Tool preview handlers: clean summaries (no base64 floods chat)


## 2026-02-08 — 🌐 FreeBuild Conversational Chat (Game-Studio-style) ✅

- Backend `/app/backend/modules/freebuild/freebuild_chat.py`:
  - 8 endpoints: `GET /types`, `POST /project`, `GET /projects`, `GET /project/{id}`, `POST /project/{id}/chat`, `POST /project/{id}/asset/{aid}/approve`, `POST /project/{id}/compile`, `DELETE /project/{id}`
  - `TAG_RE` parses `<<HERO|SECTION_BG|LOGO|PRODUCT|ICON|BANNER_AR|GALLERY: prompt>>` from AI response
  - `_extract_html` pulls `<!DOCTYPE html>...</html>` from ```html``` code blocks into `current_html`
  - `_strip_tags` removes tags from chat text + collapses blank lines
  - `_generate_assets_bg` background task: spawns `generate_flux_pro` (Fal.ai/OpenAI) per tag, updates asset status via `arrayFilters` (fixed messages.0.pending_assets path bug)
  - `extra_context` includes approved asset URLs so AI can reuse them in HTML
- Frontend `/app/frontend/src/pages/FreeBuildChat.js`:
  - 3 modes: `ProjectList` (no id), `TypePicker` (id=='new'), `ChatWorkspace` (id=uuid)
  - 3-pane layout: **Assets sidebar | Chat | Live Preview iframe** with desktop/mobile toggle and show/hide preview
  - Polls project every 4s for async asset generation status
  - `data-testid` on every interactive element (new-project-btn, type-{id}, create-project-btn, chat-input, chat-send-btn, approve-asset-{id}, preview-iframe, …)
- AI agent ("freebuild" in `zitex_ai`) instructs Claude Sonnet to consult first then emit tags then HTML
- Tested: 16/16 backend pytest pass, frontend smoke ✅ (`/app/test_reports/iteration_37.json`)
- Pytest regression: `/app/backend/tests/test_freebuild_chat.py` (~60s, hits live Claude+Fal)
- Pushed to `main` → Railway auto-redeploys
