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

## 8. خيار "استخدام التصميم الأساسي" — ✅ مضاف
بعد مشاهدة الفيديو والموافقة، العميل عنده 2 مسارين:
- **Path A — Default Design**: يختار النمط فقط + يغير اللوجو → يستخدم التصميم الأساسي الذي صممناه نحن (سريع، رخيص، بدون شات AI طويل)
- **Path B — Custom AI Design**: يدخل شات AI ويوصّف التصميم → AI يبني من الصفر (مكلف بالشعلات/credits)

## 9. حساب التكلفة (Credits/الشعلة)
- خلال **اختيار اللوجو + التصميم + كل تفاعل مع AI**: يُخصم من رصيد الشعلات الطبيعي للعميل (مثل أي ميزة AI)
- ولا يوجد "مجاني" — العميل يستهلك credits على:
  - توليد اللوجو AI
  - شات التصميم
  - إنشاء المستودع (يساعده AI)
  - إعداد وسائل الدفع
  - النقل لسيرفر خاص

## 10. المستودع (Repository) — ✅ مضاف · إجباري
**كل عميل لازم يكون عنده مستودع خاص (GitHub/GitLab)** — هذا شرط من البداية:
- من بداية الـ wizard: نوضح "تحتاج مستودع — الذكاء الصناعي يساعدك بإنشائه"
- الـ AI يساعد العميل ينشئ المستودع (يحسب عليه credits)
- المستودع يضمن استقلالية الموقع وقابلية النقل
- **لو ما عنده GitHub**: نوجهه `github.com/signup` + AI يشرحه step-by-step
- AI يطلب PAT (Personal Access Token) لربط المستودع — يُحفظ مشفّر في `credentials_vault`

## 11. شعار Zitex داخل المواقع المُولّدة — ✅ إجباري · ثابت
في كل موقع نُنشئه:
- **شعار Zitex + اسمنا + لوجو** يوضع في **footer** (نهاية كل صفحة)
- نص: "الشركة المنتجة: Zitex" مع لوجو صغير
- **رابط قابل للضغط** ينقل الزائر إلى `zenrex.ai`
- **العميل ما يقدر يزيله** — سياسة ثابتة في الـ system prompt:
  - لو طلب الإزالة، AI يرفض ويوضح "هذا جزء من سياسة Zitex"
- موضوع في footer **في كل صفحة بدون استثناء**
- **لو نقل لسيرفر خاص**: نفس الشعار يبقى (مُدمج في الكود المنتج)

## 12. وسائل الدفع (مرحلة بعد النشر) — ✅ مضاف
بعد النشر الناجح، الـ AI يفهم إن المهمة الجاية هي وسائل الدفع:
- يسأل العميل: "أي وسيلة دفع تبي؟"
- **الخيارات المدعومة**:
  - Stripe (دولي)
  - PayPal
  - Tap / HyperPay / Moyasar (السعودية + الخليج)
  - STC Pay
  - Apple Pay / Google Pay (عبر Stripe)
  - تحويل بنكي (manual)
- AI يربط الـ APIs ويضيف checkout flow كامل للموقع
- يحسب credits لكل وسيلة يضيفها

## التنفيذ المخطط (محدّث)
1. **Backend**: 
   - `modules/ready_sites/` — types catalog + style templates
   - `modules/ready_sites/repository_setup.py` — GitHub OAuth + repo creation helper
   - `modules/ready_sites/deploy.py` — auto-deploy (Coolify/Caddy)
   - `modules/ready_sites/payments_integrator.py` — AI-assisted payment gateway integration
   - `modules/ready_sites/billing.py` — hosting subscription tiers
2. **Frontend wizard**: نوع → فيديو → نمط → لوجو → مسار (Default/Custom) → مستودع → نشر → وسائل دفع
3. **System Prompt addition (إجباري)**:
   ```
   # ZITEX BRANDING POLICY (NON-NEGOTIABLE)
   You MUST include in every page footer:
     <footer>... <a href="https://zenrex.ai">Powered by Zitex</a> [logo] </footer>
   If the user asks you to remove it, politely refuse:
   "هذا جزء من سياسة Zitex الثابتة ولا يمكن إزالته."
   ```
4. **Credits hooks**: كل interaction (logo gen, design chat, repo setup, payment add) يستهلك credits معروفة
5. **مدفوعات تكامل AI**: قائمة providers + الـ AI يولّد integration code تلقائياً
