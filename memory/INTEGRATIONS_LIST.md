# 💳 قائمة المنصات المدفوعة في Zenrex (Feb 2026)

كل ما هو "Active" هذا اللي مكوَّن حالياً ويسحب من رصيدك.
كل صف فيه: **الرابط للوحة التحكم** + **المفتاح المُكوَّن** + **نوع الاستخدام**.

---

## 🤖 1. الذكاء الاصطناعي (Text + Tools)

| الخدمة | الاستخدام | لوحة التحكم (افتح ودخّل) | المفتاح في .env | الحالة |
|---|---|---|---|---|
| **Anthropic Claude** | الدماغ الرئيسي للذكاء (Sonnet 4.5) — كل الشات | https://console.anthropic.com/settings/billing | `ANTHROPIC_API_KEY` | ✅ Active |
| **OpenAI** | احتياطي + GPT-Image-1 + Whisper STT + TTS | https://platform.openai.com/settings/organization/billing/overview | `OPENAI_DIRECT_KEY` | ✅ Active |
| **Google Gemini** | احتياطي + Nano Banana لتوليد الصور | https://aistudio.google.com/app/apikey | `GEMINI_API_KEY` | ✅ Active |
| **Groq** | سرعة عالية للأسئلة البسيطة | https://console.groq.com/keys | `GROQ_API_KEY` | ✅ Active |
| **Zhipu (GLM)** | احتياطي صيني للنصوص | https://bigmodel.cn/usercenter/proj-mgmt/apikeys | `ZHIPU_API_KEY` | ✅ Active |
| **Emergent LLM Key** | باقي يكون احتياطي عام | (تُدار من إعدادات Emergent) | `EMERGENT_LLM_KEY` | ✅ Active |

---

## 🎬 2. توليد الفيديو (الأهم لمنتجك)

| الخدمة | النموذج | السعر/ثانية | لوحة التحكم | المفتاح | الحالة |
|---|---|---:|---|---|---|
| **fal.ai** | LTX-Video | $0.005 | https://fal.ai/dashboard/billing | `FAL_KEY` | ✅ Active |
| **fal.ai** | MiniMax Hailuo 02 | $0.04 | ↑ نفس الرابط | `FAL_KEY` | ✅ Active |
| **fal.ai** | Kling v1 Standard | $0.07 | ↑ نفس الرابط | `FAL_KEY` | ✅ Active |
| **fal.ai** | Kling v1 Pro | $0.15 | ↑ نفس الرابط | `FAL_KEY` | ✅ Active |
| **fal.ai** | Sora 2 Turbo | $0.10 | ↑ نفس الرابط | `FAL_KEY` | ✅ Active |
| **fal.ai** | Sora 2 Pro | $0.30 | ↑ نفس الرابط | `FAL_KEY` | ✅ Active |

🔗 **افتح هنا للتأكد من رصيد fal.ai**: https://fal.ai/dashboard/billing

---

## 🎙️ 3. الصوت + التعليق الصوتي

| الخدمة | الاستخدام | لوحة التحكم | المفتاح | الحالة |
|---|---|---|---|---|
| **ElevenLabs** | TTS عالي الجودة (كوري، عربي، إلخ) + Dubbing | https://elevenlabs.io/app/usage | `ELEVENLABS_API_KEY` | ✅ Active |
| **OpenAI TTS** | TTS رخيص (بديل ElevenLabs) | https://platform.openai.com/usage (نفس لوحة OpenAI) | `OPENAI_DIRECT_KEY` | ✅ Active |
| **OpenAI Whisper** | تفريغ صوتي (Speech→Text) | ↑ نفس | `OPENAI_DIRECT_KEY` | ✅ Active |
| **Pollinations TTS** | TTS مجاني (للمسودات) | https://pollinations.ai (بدون مفتاح) | لا يحتاج | ✅ مجاني |

---

## 🎨 4. توليد الصور

| الخدمة | الاستخدام | لوحة التحكم | المفتاح | الحالة |
|---|---|---|---|---|
| **fal.ai (FLUX/SDXL)** | صور احترافية، شخصيات، Storyboard keyframes | https://fal.ai/dashboard/billing | `FAL_KEY` | ✅ Active |
| **OpenAI GPT-Image-1** | صور عالية الجودة | https://platform.openai.com/usage | `OPENAI_DIRECT_KEY` | ✅ Active |
| **Gemini Nano Banana** | صور سريعة ورخيصة | https://aistudio.google.com/app/billing | `GEMINI_API_KEY` | ✅ Active |
| **Pollinations** | صور مجانية (للأمثلة + Welcome cards) | https://pollinations.ai (بدون مفتاح) | لا يحتاج | ✅ مجاني |

---

## 🔎 5. البحث في الإنترنت + جلب البيانات

| الخدمة | الاستخدام | لوحة التحكم | المفتاح | الحالة |
|---|---|---|---|---|
| **Tavily** | بحث ذكي للذكاء الاصطناعي | https://app.tavily.com/home | `TAVILY_API_KEY` | ✅ Active |
| **Alpha Vantage** | بيانات أسواق مالية (لتحليل الأسهم) | https://www.alphavantage.co/support/#api-key | `ALPHA_VANTAGE_KEY` | ✅ Active |

---

## 📧 6. الإشعارات + Email + SMS

| الخدمة | الاستخدام | لوحة التحكم | المفتاح | الحالة |
|---|---|---|---|---|
| **Resend** | إرسال إيميلات ترحيب/فواتير/إشعارات | https://resend.com/billing | `RESEND_API_KEY` | ✅ Active |

> ⚠️ **Twilio SMS غير مكوَّن حالياً** — لو احتجت SMS للعملاء (OTP، إشعارات طلبات)، تحتاج تشترك في https://console.twilio.com/

---

## 💰 7. المدفوعات

| الخدمة | الاستخدام | لوحة التحكم | المفتاح | الحالة |
|---|---|---|---|---|
| **Stripe** | اشتراكات + دفعات بالكروت | https://dashboard.stripe.com/balance/overview | `STRIPE_API_KEY` | ✅ Active |
| **LemonSqueezy** | بدائل لـ Stripe (تشمل العالم) | https://app.lemonsqueezy.com/billing | `LEMONSQUEEZY_API_KEY` | ✅ Active |

---

## 🚀 8. النشر + DevOps

| الخدمة | الاستخدام | لوحة التحكم | المفتاح | الحالة |
|---|---|---|---|---|
| **Vercel** | نشر مواقع HTML للعملاء | https://vercel.com/account/billing | `VERCEL_TOKEN` | ✅ Active |
| **Railway** | بدائل Vercel لمشاريع Backend | https://railway.com/account/usage | `RAILWAY_TOKEN` | ✅ Active |
| **GitHub** | حفظ الكود + النشر التلقائي | https://github.com/settings/billing/summary | `GITHUB_TOKEN` | ⚠️ منتهي — يحتاج تجديد PAT |

---

## 🖥️ 9. البنية التحتية (Hetzner VPS)

| الخدمة | الاستخدام | لوحة التحكم | الحالة |
|---|---|---|---|
| **Hetzner Cloud** | السيرفر اللي ينشغل عليه `zenrex.ai` | https://console.hetzner.cloud/projects | ✅ Active |
| **MongoDB Atlas** | قاعدة البيانات السحابية | https://cloud.mongodb.com/v2 | ✅ Active |

---

## 🚨 ملخص الأولويات للتحقق من الرصيد

افتح هذي بالترتيب وتأكد فيها رصيد كافٍ:

1. **🔴 الأهم (لإنتاج الفيديو)**: https://fal.ai/dashboard/billing
2. **🔴 الذكاء**: https://console.anthropic.com/settings/billing
3. **🟡 الصوت**: https://elevenlabs.io/app/usage
4. **🟡 الصور احتياطية**: https://platform.openai.com/usage
5. **🟡 الإيميل**: https://resend.com/billing

---

## ⚠️ المشكلة التقنية اللي كانت موجودة (تم حلها)

**السبب الجذري المُكتشف**: اسم أداة `generate_video` كان مكرر في ملفين (`advanced_tools.py` + `workflow_tools.py`).
لما الذكاء يرسل قائمة الأدوات إلى Anthropic، يرفضها بـ:
`"Tool names must be unique"` → الشات يفشل قبل ما يصل لـ fal.ai أصلاً.

**الإصلاح**: حذف النسخة القديمة من `advanced_tools.py` وإبقاء النسخة المحدّثة في `workflow_tools.py` (هي اللي تستخدم `FAL_KEY` من الخادم تلقائياً + ترسل إشعار للمالك لو فشلت).

📅 آخر تحديث: 16 فبراير 2026
