# 🔑 Zitex — دليل المفاتيح المطلوبة (Keys Shopping Guide)

هذا الدليل يحدد بدقّة:
- أيّ مفاتيح تفعّل أيّ إمكانيات في النظام
- وين تجيب كل مفتاح بالضبط (روابط مباشرة)
- هل هو مجاني أو مدفوع (تكلفة تقريبية)
- ترتيب حسب الأولوية والقيمة

> **مهم**: المفاتيح تُحفظ في **Railway → Variables** عشان تكون متاحة للـ production،
> أو في `/root/.zitex/credentials.json` (vault) للـ dev. الذكاء يقرأ من ENV أولاً ثم الـvault.

---

## 🔴 P0 — Core (لازم بدونها النظام ما يعمل أصلاً)

| المفتاح | الفائدة | وين تجيبه | السعر |
|---------|---------|-----------|-------|
| `MONGO_URL` | قاعدة البيانات الرئيسية | Railway تلقائياً ينشئها مع MongoDB plugin | مدمج |
| `JWT_SECRET` | تشفير الجلسات | ولّده بـ `openssl rand -hex 32` | مجاني |
| `GITHUB_TOKEN` أو PAT | الـ AI يعمل push للكود | https://github.com/settings/tokens (Classic, scopes: repo, workflow) | مجاني |

---

## 🟠 P1 — AI Brains (تفعيل دماغ الذكاء)

أنت معك حالياً ✓ (موجودة على Railway):
- `ANTHROPIC_API_KEY` — Claude Sonnet/Opus/Haiku
- `OPENAI_DIRECT_KEY` — GPT-5.5 / GPT-4o
- `GROQ_API_KEY` — Llama 3.3 مجاناً وسريع
- `GEMINI_API_KEY` — Gemini 2.5 Flash مجاناً

**إضافات قوية مقترحة:**

| المفتاح | الفائدة | وين تجيبه | السعر |
|---------|---------|-----------|-------|
| `OPENROUTER_API_KEY` | وصول لـ300+ موديل من API واحد (DeepSeek, Llama, Mistral, ...) | https://openrouter.ai/keys | Pay-as-you-go |
| `MISTRAL_API_KEY` | Mistral Large + Codestral (ممتاز للبرمجة) | https://console.mistral.ai | $0.50-2/M tokens |
| `DEEPSEEK_API_KEY` | DeepSeek V3 (أرخص بكثير من GPT) | https://platform.deepseek.com | $0.14-0.28/M tokens |
| `HF_TOKEN` | Hugging Face Hub + Inference (آلاف الموديلات) | https://huggingface.co/settings/tokens | مجاني (محدود) |

---

## 🎨 Media Generation (توليد محتوى)

| المفتاح | الفائدة | وين تجيبه | السعر |
|---------|---------|-----------|-------|
| `FAL_KEY` | fal.ai — أفضل توليد صور/فيديو حالياً (FLUX, SDXL, Veo, ...) | https://fal.ai/dashboard/keys | Pay-per-image (~$0.01-0.10) |
| `STABILITY_API_KEY` | Stable Diffusion API | https://platform.stability.ai/account/keys | Credits ($10 = ~500 صورة) |
| `RUNWAY_API_KEY` | Runway Gen-3 (فيديو احترافي) | https://dev.runwayml.com | Credits |
| `LUMAAI_API_KEY` | Luma Dream Machine (فيديو) | https://lumalabs.ai/dream-machine/api | Pay-per-video |
| `ELEVENLABS_API_KEY` ✓ | TTS أصوات طبيعية (موجود عندك) | https://elevenlabs.io/app/settings/api-keys | مجاني 10k حرف/شهر |
| `DEEPGRAM_API_KEY` | تفريغ صوتي أسرع/أرخص من Whisper | https://console.deepgram.com | $200 رصيد مجاني |
| `ASSEMBLYAI_API_KEY` | تفريغ + Speaker diarization | https://www.assemblyai.com/dashboard | $50 رصيد مجاني |

---

## 💳 Payments & Commerce (تحصيل أموال)

| المفتاح | الفائدة | وين تجيبه | السعر |
|---------|---------|-----------|-------|
| `STRIPE_SECRET_KEY` + `STRIPE_PUBLISHABLE_KEY` | مدفوعات عالمية | https://dashboard.stripe.com/apikeys | 2.9% + $0.30 |
| `PAYPAL_CLIENT_ID` + `PAYPAL_CLIENT_SECRET` | PayPal | https://developer.paypal.com/dashboard/applications | 2.9% + fee |
| `RAZORPAY_KEY_ID` + `RAZORPAY_KEY_SECRET` | مدفوعات الهند/الخليج | https://dashboard.razorpay.com/app/keys | 2% |
| `LEMONSQUEEZY_API_KEY` | Subscriptions بسيطة | https://app.lemonsqueezy.com/settings/api | 5% (Merchant of Record) |

---

## 🗄️ Storage & Database (تخزين بديل)

| المفتاح | الفائدة | وين تجيبه | السعر |
|---------|---------|-----------|-------|
| `SUPABASE_URL` + `SUPABASE_KEY` | Postgres + Auth + Storage جاهز | https://supabase.com/dashboard | مجاني حتى 500MB |
| `FIREBASE_CREDENTIALS_JSON` | Firebase (real-time DB + Auth) | https://console.firebase.google.com → Project Settings → Service Accounts | مجاني |
| `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` | S3, Lambda, الخ | https://console.aws.amazon.com/iam | Pay-as-you-go |
| `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` | R2 storage, Workers, Pages | https://dash.cloudflare.com/profile/api-tokens | مجاني (10GB R2) |
| `MAPBOX_ACCESS_TOKEN` | خرائط متقدمة | https://account.mapbox.com/access-tokens | مجاني 50k load/شهر |

---

## 📨 Messaging (تواصل مع المستخدمين)

| المفتاح | الفائدة | وين تجيبه | السعر |
|---------|---------|-----------|-------|
| `RESEND_API_KEY` | إيميلات (أحسن DX للمطورين) | https://resend.com/api-keys | 3000 إيميل/شهر مجاني |
| `SENDGRID_API_KEY` | إيميلات (legacy، أكثر features) | https://app.sendgrid.com/settings/api_keys | 100 إيميل/يوم مجاني |
| `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` | SMS + WhatsApp | https://console.twilio.com | $15 رصيد تجريبي |
| `TELEGRAM_BOT_TOKEN` | بوت تلغرام | https://t.me/BotFather → /newbot | مجاني |
| `SLACK_BOT_TOKEN` | تكامل سلاك | https://api.slack.com/apps | مجاني |
| `DISCORD_BOT_TOKEN` | بوت ديسكورد | https://discord.com/developers/applications | مجاني |

---

## 🚀 Deployment & DevOps

| المفتاح | الفائدة | وين تجيبه | السعر |
|---------|---------|-----------|-------|
| `RAILWAY_TOKEN` | الـ AI يدير الـ deployments بنفسه | https://railway.app/account/tokens | مجاني |
| `VERCEL_TOKEN` | نشر الـ frontend برمجياً | https://vercel.com/account/tokens | مجاني |
| `NETLIFY_AUTH_TOKEN` | بديل Vercel | https://app.netlify.com/user/applications#personal-access-tokens | مجاني |
| `DOCKERHUB_TOKEN` | نشر صور Docker | https://hub.docker.com/settings/security | مجاني |
| `SENTRY_DSN` | تتبع الأخطاء في production | https://sentry.io/settings/account/api/auth-tokens | مجاني 5k events/شهر |

---

## 📊 Analytics & Monitoring

| المفتاح | الفائدة | وين تجيبه | السعر |
|---------|---------|-----------|-------|
| `POSTHOG_API_KEY` | Product analytics + Session replay | https://app.posthog.com/project/settings | 1M events/شهر مجاني |
| `MIXPANEL_TOKEN` | Event analytics متقدم | https://mixpanel.com/settings/project | 100k MTU مجاني |
| `DATADOG_API_KEY` + `DATADOG_APP_KEY` | APM + Logs | https://app.datadoghq.com/organization-settings/api-keys | Trial 14 يوم |

---

## 🔐 Auth (تسجيل دخول جاهز)

| المفتاح | الفائدة | وين تجيبه | السعر |
|---------|---------|-----------|-------|
| `CLERK_PUBLISHABLE_KEY` + `CLERK_SECRET_KEY` | Auth جاهز (Google/Apple/SMS) | https://dashboard.clerk.com/last-active?path=api-keys | مجاني 10k MAU |
| `AUTH0_DOMAIN` + `AUTH0_CLIENT_ID` + `AUTH0_CLIENT_SECRET` | Enterprise auth | https://manage.auth0.com → Applications | مجاني 25k MAU |

---

## 🎮 Specialty / Extras

| المفتاح | الفائدة | وين تجيبه | السعر |
|---------|---------|-----------|-------|
| `MESHY_API_KEY` | توليد نماذج 3D | https://www.meshy.ai/settings/api-keys | $20 رصيد مجاني |
| `THIRDWEB_CLIENT_ID` | Web3 / NFT بسهولة | https://thirdweb.com/dashboard/settings/api-keys | مجاني |
| `MORALIS_API_KEY` | Web3 data | https://admin.moralis.io/account/profile | مجاني (محدود) |
| `ROBOFLOW_API_KEY` | Computer Vision (object detection) | https://app.roboflow.com/account-settings | مجاني (محدود) |
| `LEONARDO_API_KEY` | Leonardo AI art | https://app.leonardo.ai/api-access | $9/شهر |
| `HEYGEN_API_KEY` | Avatar فيديو | https://app.heygen.com/settings/api-keys | $99/شهر |

---

## ⚡ ترتيب الإضافة المُوصى به (لو تبي تبدأ تدريجياً)

**الموجة الأولى — الأهم (مجاني تماماً)**:
1. `RAILWAY_TOKEN` — يسرّع تطوير الذكاء (ينشر بنفسه)
2. `OPENROUTER_API_KEY` — يفتح 300+ موديل ($5 لين بداية)
3. `HF_TOKEN` — وصول لكل موديلات Hugging Face
4. `RESEND_API_KEY` — إيميلات للمستخدمين
5. `SENTRY_DSN` — تتبع أخطاء الـ production

**الموجة الثانية — لتمويل المنصة (Revenue)**:
6. `STRIPE_SECRET_KEY` — مدفوعات
7. `SUPABASE_URL/KEY` — Auth + DB بديل لو احتجت
8. `POSTHOG_API_KEY` — analytics

**الموجة الثالثة — تعزيز قدرات الـ AI**:
9. `FAL_KEY` — صور/فيديو متقدم
10. `DEEPGRAM_API_KEY` — تفريغ صوتي
11. `MESHY_API_KEY` — 3D

---

## 🔧 كيف تضيف مفتاح؟

### الطريقة 1: من Railway (للـ production):
1. افتح: https://railway.app/project/<your-project-id>
2. اختر الـ service (backend)
3. تبويب **Variables** → **+ New Variable**
4. اكتب الاسم والقيمة → Save
5. Railway يعمل redeploy تلقائياً

### الطريقة 2: عبر AI (الذكاء يقدر يضيف في الـ vault):
```
سيف هذا المفتاح في الخزنة:
vault_set(key="FAL_KEY", value="fal_xxx...")
```
وراح يحفظه في `/root/.zitex/credentials.json` ويستخدمه فوراً.

### الطريقة 3: محلياً (للاختبار قبل النشر):
```bash
echo "FAL_KEY=fal_xxx" >> /app/backend/.env
sudo supervisorctl restart backend
```
