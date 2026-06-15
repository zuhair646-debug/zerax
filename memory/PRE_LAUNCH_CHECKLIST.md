# 📋 Zenrex Pre-Launch Checklist

> قائمة المهام **الإلزامية** قبل نشر zenrex.ai للعموم.
> آخر تحديث: 2026-02-15

---

## 🔐 1. Google OAuth — Production Hardening

### 1.1 إعادة توليد Client Secret ⚠️ **حرجة**
- [ ] **Client Secret الحالي ظهر في شات Emergent** أثناء التطوير
- **الإجراء**:
  1. روح: https://console.cloud.google.com/apis/credentials
  2. افتح "Zenrex Production" OAuth client
  3. اضغط **RESET SECRET**
  4. انسخ الـ Secret الجديد
  5. حدّث في الـ .env على Hetzner:
     ```bash
     ssh root@91.98.154.148
     cd /opt/zerax/backend
     sed -i '/^GOOGLE_CLIENT_SECRET=/d' .env
     echo 'GOOGLE_CLIENT_SECRET=GOCSPX-NEW_SECRET' >> .env
     cd /opt/zerax && docker compose restart backend
     ```
  6. اختبر تسجيل قوقل من جديد للتأكد
- **الأولوية**: 🔴 P0 — لا تنشر بدون هذا

### 1.2 نشر OAuth Consent Screen (Testing → Production)
- [ ] حالياً في Testing mode → فقط Test Users يقدرون يسجلون
- **الإجراء**:
  1. روح: https://console.cloud.google.com/apis/credentials/consent
  2. اضغط **PUBLISH APP**
  3. أكّد ("Push to production")
  4. لو طلب verification:
     - لا يحتاج verification إذا الـ scopes بس openid + email + profile (sensitive scopes غير مطلوبة)
     - لو طلب، قدّم المعلومات وانتظر 4-6 أسابيع
- **الأولوية**: 🔴 P0 — بدونها بس test users يقدرون يستخدمون قوقل

### 1.3 إضافة Privacy Policy + Terms of Service URLs
- [ ] قوقل تتطلب رابط Privacy Policy على OAuth Consent Screen قبل النشر
- **الإجراء**:
  1. أنشئ صفحات `/privacy` و `/terms` على zenrex.ai (موجودة؟ تأكد)
  2. حدّث Google Cloud Console → OAuth consent screen → Application home page + Privacy Policy + Terms of Service
- **الأولوية**: 🟠 P1

---

## 🧹 2. تنظيف الـ Codebase من بقايا Emergent

### 2.1 حذف صفحة `/auth-callback` القديمة
- [ ] الصفحة كانت تستقبل callback من `auth.emergentagent.com`
- ما عاد لها داعي بعد ما حذفنا flow الـ Emergent
- **الإجراء**: ابحث عن `auth-callback` في `/app/frontend/src/App.js` واحذف الـ route + الملف
- **الأولوية**: 🟡 P2

### 2.2 تأكد إن ما فيه أي مكان آخر يستدعي `emergentagent.com`
- **الإجراء**:
  ```bash
  grep -rn "emergentagent" /app/frontend/src /app/backend
  ```
- يفترض ما يطلع نتائج (فحصنا مسبقاً)
- **الأولوية**: 🟢 P3 (تحقق نهائي)

---

## 💰 3. تسعيرات الذكاء الاصطناعي

### 3.1 إصلاح تسعيرة fal.ai في الـ prompt
- [ ] الذكاء كان يقول "$0.01/ثانية" بدون التحقق من Web Search
- **الإجراء**: تأكد إن قاعدة Self-Verification Gate تشمل التسعيرات:
  ```
  ممنوع ذكر سعر بدون web_search أو ask_integration_expert يؤكده
  ```
- **الأولوية**: 🟠 P1

### 3.2 ربط زر "صدّر فيديو حقيقي" بـ fal.ai
- [ ] حالياً يعرض alert فقط — يحتاج تنفيذ كامل
- **التطوير المطلوب**:
  1. أضف endpoint `/api/freebuild-chat/project/{id}/export-real-video`
  2. يحسب التكلفة لكل موديل (Hailuo / Kling / Sora) ويعرضها قبل التأكيد
  3. بعد التأكيد، يستدعي fal.ai لكل keyframe → video segment
  4. ffmpeg يجمع المقاطع + voiceover + subtitles → MP4 1080p نهائي
- **الأولوية**: 🟢 P2

---

## 🔄 4. Backend Maintenance

### 4.1 تجديد `GITHUB_TOKEN`
- [ ] التوكن منتهي → سكربت النسخ الاحتياطي معطّل
- **الإجراء**: 
  1. روح: https://github.com/settings/tokens?type=beta
  2. أنشئ Fine-grained personal access token
  3. Repository: `zuhair646-debug/zenrex`
  4. Permissions: Contents (Read+Write)
  5. حدّث في `.env` على Hetzner: `GITHUB_TOKEN=ghp_...`
- **الأولوية**: 🟠 P1

### 4.2 تقسيم `zenrex_farm.py` (7,400 سطر)
- [ ] ملف عملاق يحتاج تقسيم إلى modules
- **التقسيم المقترح**:
  - `/app/desktop_agent/workers/build_worker.py`
  - `/app/desktop_agent/workers/sync_worker.py`
  - `/app/desktop_agent/routes/`
  - `/app/desktop_agent/db/`
- **الأولوية**: 🟢 P2 (تحسين قابلية الصيانة)

---

## 🎨 5. ميزات معلّقة من المحادثات السابقة

### 5.1 أوضاع AI Brain الـ 9 في الواجهة
- [ ] backend فيه 9 modes (apps/games/anime/longform/etc) لكن UI ما يعرضها
- **الإجراء**: أضف dropdown/cards في `AdminAICore.js`
- **الأولوية**: 🟢 P2

### 5.2 صفحة هبوط بـ 9 كروت
- [ ] للتسويق + Conversion
- **الأولوية**: 🟢 P3

### 5.3 auto-switch tabs في video studio
- [ ] لما العميل يوافق على السيناريو → تنتقل تلقائياً لـ tab المعتمدات
- **الأولوية**: 🟡 P2

### 5.4 تكامل Travian (محجوب)
- [ ] محتاج: اشتراك 2captcha + Residential Proxy من المالك
- **الأولوية**: 🟢 P3 (backlog)

---

## 📊 6. Monitoring & Observability

### 6.1 إضافة Sentry أو error tracking
- [ ] لرصد أخطاء production
- **الأولوية**: 🟢 P2

### 6.2 logs aggregation
- [ ] حالياً logs في docker logs فقط
- اقتراح: شحنها لـ Logtail أو Better Stack
- **الأولوية**: 🟢 P3

---

## ✅ اللي خلصناه فعلاً (Done)

- [x] Hetzner deployment على zenrex.ai
- [x] فك التبعية الكاملة عن Emergent LLM Proxy
- [x] 9 AI Brain modes في backend
- [x] Brand Manager + PWA dynamic manifest
- [x] حذف مشاريع Vercel/Railway القديمة
- [x] Studio Preview بـ watermark protection
- [x] دعم Korean في video catalog (6 أصوات)
- [x] generate_voiceover يستخدم OpenAI TTS تلقائياً
- [x] generate_subtitles مع ترجمة دقيقة
- [x] Anthropic Prompt Caching (90% توفير)
- [x] خبراء متخصصين 4 (design/testing/troubleshoot/integration)
- [x] قواعد E1 الانضباطية في الـ system prompt
- [x] ذاكرة المشروع الدائمة (PRD/Changelog/Decisions)
- [x] Self-Verification Gate (ممنوع "خلصت" بدون دليل tool)
- [x] mode_blocked guard (ممنوع write_full_html في وضع الفيديو)
- [x] Direct Google OAuth (لا تبعية لـ emergentagent.com)

---

## 🎯 تسلسل الأولويات الموصى به للنشر

1. **الآن**: 1.1 (إعادة Secret) + 1.2 (نشر Consent Screen)
2. **خلال أسبوع**: 1.3 (Privacy/Terms) + 3.1 (تسعيرة fal.ai) + 4.1 (GITHUB_TOKEN)
3. **بعد النشر**: 2.1 + 5.1 + 5.3 (تحسينات UX)
4. **مستقبل**: 4.2 + 5.2 + 6.x (Scalability)
