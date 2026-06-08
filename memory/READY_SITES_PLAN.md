# Ready-Made Sites — Restructure Plan (P0)

## الهدف
إعادة هيكلة قسم "المواقع الجاهزة" بحيث يبقى مع توحيد UI الشات مع FreeBuild، وتجربة موجّهة بدون تعديل العميل.

## المتطلبات (من المحادثة)

### 1. توحيد الشات مع FreeBuild
- نفس واجهة الشات (SSE streaming, Cursor-style live snippets, auto-scroll, heartbeat)
- نفس الـ agent core (Claude Sonnet 4.5 + 16K tokens + auto-resume)
- خيار: استخدام نفس `freebuild_agent.py` مع template-mode flag

### 2. هيكل العمل
- **العميل ما عنده حق التعديل** على المكونات الجاهزة
- يطلب التطبيق فقط ويختار النمط
- الـ AI يبني التصميم من الصفر **بدون قوالب جاهزة** (designed from scratch in the style)

### 3. اختيار النمط (Template Style)
**3-4 أنماط** لكل نوع موقع:
- **نمط 1 (Top Menu)**: قائمة فوق الصفحة الرئيسية → تنقل بين صفحات
- **نمط 2 (Vertical Hero+Products)**: بنر علوي + منتجات أسفل (طولي/scroll)
- **نمط 3**: مختلف (TBD — ربما sidebar layout)
- **نمط 4**: مختلف (TBD — ربما card grid)

العميل يختار النمط من **شاشة بصرية** فيها previews واضحة قبل البدء.

### 4. اللوجو
العميل عنده 3 خيارات:
- **A**: يرفق لوجو جاهز (PNG/SVG upload)
- **B**: يطلب من AI يصمم لوجو حسب وصفه (يستخدم gemini nano banana / gpt image 1)
- **C**: يكتفي بـ text logo (اسم الموقع كنص)

### 5. أعماق الأقسام
- كل قسم (مطعم/متجر/مدونة/إلخ) يكون عميق ومتكامل
- أدوات داخلية كاملة: shopping cart, contact form, admin panel, etc.
- AI يبني الكود الكامل (frontend + backend mock + admin)

## الأنواع المطلوبة (متابعة)
*المستخدم سيكمل التفاصيل في رسالة منفصلة:*
- ⏳ ما هي الأنواع المحددة؟ (مطعم، متجر، عيادة، صالون، عقارات، ...)
- ⏳ كم نمط بالضبط لكل نوع؟ 3 أم 4؟
- ⏳ مواصفات الأدوات لكل نوع؟
- ⏳ هل اللوجو AI يستخدم Gemini nano banana أم OpenAI gpt image 1؟
- ⏳ نموذج التسعير للنوع الكامل (free / paid؟)

## 6. النشر التلقائي (Auto-Deploy to Live) — ✅ مضاف
بعد اعتماد العميل النهائي للتصميم + اللوجو + النمط:
- **رفع تلقائي للموقع للسيرفر** (live) باللوجو والتصميم الجديد
- **نموذج التكلفة الشهرية الشفاف**:
  - **Option A**: يستضيف على سيرفرنا → اشتراك شهري ثابت ($X/شهر) — يشمل الـ hosting + maintenance
  - **Option B**: ينقل لسيرفره الخاص (DigitalOcean/AWS/Hostinger) → رسوم setup مرة واحدة ($Y) + يدفع هو للهوست
- **شفافية**: قبل النشر، نعرض للعميل تفاصيل التكاليف بوضوح
- ⏳ المبالغ المحددة (شهري + setup) — منتظر منك

## 7. فيديو تعريفي لكل قسم — ✅ مضاف
لما العميل يدخل قسم نوع معين (مثلاً "مطاعم"):
- **فيديو ترحيبي** يبدأ تلقائياً (أو بضغطة play)
- محتوى الفيديو:
  - شنو راح يتكون الموقع/التطبيق (الصفحات، الأدوات)
  - الخدمات والمميزات (cart, ordering, menu management, etc.)
  - **عرض تصميم مثال** بنفس الأدوات لكن بتصميم مختلف (proof of concept)
- **الهدف**: العميل يقرر هل يكمل أو لا قبل ما يدخل عملية التصميم
- ⏳ من ينتج الفيديوهات؟
  - **Option A**: نولّدها بـ AI (Sora 2 / Veo / Kling) لما تطلب
  - **Option B**: تصورها أنت / نتعاقد مع مصمم
  - **Option C**: hybrid (AI أولاً، ثم استبدال بفيديو احترافي لاحقاً)

## التنفيذ المخطط (لما تكتمل المتطلبات)
1. **Backend**: 
   - `modules/ready_sites/` — types catalog + style templates + agent wrapper
   - `modules/ready_sites/deploy.py` — auto-deploy logic (مع Coolify/Caddy/Cloudflare Pages)
   - `modules/ready_sites/billing.py` — subscription tiers للـ hosting
2. **Frontend**:
   - `ReadyMadeChooser.js` — wizard: نوع → فيديو تعريفي → نمط → لوجو → سعر النشر → تأكيد
   - `ReadyMadeChat.js` — يعيد استخدام `FreeBuildChat.js` مع `template_id` و `style_id` + auto-deploy CTA عند الانتهاء
3. **Agent**: `freebuild_agent.py` يقبل `style_directive` + `template_type`
4. **Logo Generation**: integration مع Nano Banana أو DALL·E عبر Emergent LLM Key
5. **Hosting**: 
   - **Phase 1**: subdomains على نطاقنا (e.g. `{slug}.zitex.app`) — Coolify auto-deploy
   - **Phase 2**: custom domain على سيرفر العميل (نولّد له deployment script)
