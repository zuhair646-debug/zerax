# 🚫 NO EMERGENT COUPLING — هذا المشروع مستقل تماماً

> **يجب على أي وكيل (Agent) قادم قراءة هذا الملف قبل لمس أي ربط بـ LLM.**

## القاعدة الذهبية
نظام **Zenrex Farm** نظام مستقل بالكامل. يعمل على سيرفر `zenrex.ai` الخاص بالعميل، وبمفاتيح API خاصة به موجودة محلياً في `/app/backend/.env`.

## ❌ لا يجوز إطلاقاً
- استخدام `EMERGENT_LLM_KEY` لأي ميزة جديدة
- استخدام مكتبة `emergentintegrations` لأي ميزة جديدة
- اقتراح "Emergent Universal" أو "Zenrex Universal (Emergent)" كخيار للعميل في أي واجهة
- ربط أي endpoint جديد بـ APIs على دومين Emergent

## ✅ يجب
- استخدام مفاتيح العميل الخاصة من `/app/backend/.env`:
  - `ANTHROPIC_API_KEY` (الرئيسي — لـ Claude Sonnet)
  - `OPENAI_DIRECT_KEY` (لـ GPT)
  - `GEMINI_API_KEY` (لـ Gemini)
  - `GROQ_API_KEY` (لـ Llama/Mixtral)
- استدعاء هذه المفاتيح مباشرة عبر SDK الرسمي للمزوّد (anthropic, openai, google-generativeai, groq)

## 🔗 الاستثناء الوحيد المسموح
قسم الدعم في لوحة التحكم (`/admin` → Staff Chat) — هذا هو الرابط الوحيد المسموح به مع Emergent، ومخصّص فقط للتواصل مع موظفي Emergent عند الحاجة. لا يجوز توسيعه ولا الاعتماد عليه لأي شيء آخر.

## 🧹 الكود القديم
بعض الملفات القديمة في الكودبيس لا تزال تستخدم `EMERGENT_LLM_KEY` (موروثة من جلسات سابقة):
- `backend/modules/freebuild/freebuild_agent.py` (embeddings عبر litellm)
- `backend/server.py`
- `backend/routers/*`

**هذه يجب استبدالها تدريجياً** بمفاتيح العميل المستقلة، لكن لا تكسر functionality قائمة. اطلب إذن صريح من العميل قبل أي refactor واسع.

## 🔒 شيك إجباري قبل أي ميزة جديدة
1. هل أضفت أي مرجع لـ `EMERGENT_LLM_KEY`؟ → احذفه
2. هل أضفت `emergentintegrations`؟ → احذفه
3. هل واجهتي تذكر "Emergent" بأي شكل للعميل؟ → احذفه

---
**آخر تحديث:** 2026-06-28 — جلسة إصلاح إجباري بعد ربط خاطئ في معالج "تكملة مشروع"
