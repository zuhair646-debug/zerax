# Zitex AutoCoder Capability Roadmap

آخر تحديث: 2026-06-04

## القدرات الحالية

برمجة زيتاكس يستطيع العمل end-to-end على منصة Zitex:

- قراءة وتعديل كود backend/frontend داخل `/app`.
- إنشاء modules جديدة تحت `/app/modules/<name>` وربطها في `/app/server.py`.
- إنشاء صفحات React/Tailwind وربطها بالـAPI.
- اختبار backend عبر lint/import checks/endpoints/log scanning.
- اختبار frontend عبر build/browser/screenshot عند توفر ملفات الواجهة.
- commit/push إلى GitHub وتشخيص Railway/Vercel deployments.
- استخدام MongoDB read-only للاستكشاف الآمن.
- استخدام web search وURL fetch والتعامل مع LLM/image/audio/video tools.

## النماذج ومزودو الذكاء المتاحون

- Anthropic Claude: أفضل مسار للكود والتحليل الطويل والمهام agentic.
- OpenAI: عام/vision/structured output/TTS حسب الربط.
- Gemini: سياق طويل، multimodal، عربي.
- Groq: ردود سريعة ومهام خفيفة.
- DeepSeek: reasoning/coding بتكلفة أقل.
- Replicate/ElevenLabs/Sora tools: وسائط وصوت وفيديو حسب الأدوات.

## أهم النواقص المقترحة

### 1. Sentry
المفتاح المطلوب:

```env
SENTRY_DSN=
```

الفائدة: مراقبة أخطاء backend/frontend وتنبيهات وstack traces.

### 2. Cloudflare R2 أو S3
المفاتيح المقترحة:

```env
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=
R2_PUBLIC_URL=
CLOUDFLARE_ACCOUNT_ID=
```

الفائدة: تخزين دائم للمرفقات، الصور، الفيديوهات، وملفات العملاء.

### 3. OpenRouter

```env
OPENROUTER_API_KEY=
```

الفائدة: بوابة نماذج كثيرة مع fallback وتخفيض تكلفة.

### 4. Redis / Queue

```env
REDIS_URL=
```

الفائدة: مهام طويلة بالخلفية، progress، retries، rate limits.

### 5. LiveKit

```env
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
```

الفائدة: مساعد صوتي/مرئي realtime وavatar مباشر.

### 6. Email Provider

```env
RESEND_API_KEY=
EMAIL_FROM=
```

الفائدة: رسائل ترحيب، فواتير، recovery، وتنبيهات.

### 7. Advanced Media

```env
FAL_KEY=
HEYGEN_API_KEY=
RUNWAY_API_KEY=
LUMAAI_API_KEY=
```

الفائدة: صور/فيديو/avatar بجودة تجارية.

### 8. Vector DB / RAG

```env
PINECONE_API_KEY=
PINECONE_INDEX=
```

أو Qdrant/MongoDB Vector Search.

الفائدة: ذاكرة معرفية وبحث دلالي في الكود والمستندات وقرارات المالك.

## توصية هندسية

أنسب مسار تطوير قادم:

1. ربط Sentry.
2. إضافة R2/S3 storage module.
3. توسيع `modules/ai_core` ليصبح router موحد لكل LLM providers مع سياسات:
   - `cheap`
   - `balanced`
   - `best`
   - `coding`
   - `vision`
   - `arabic`
   - `long_context`
4. إضافة Redis queue للمهام الطويلة.
5. إضافة LiveKit للصوت الحي.
6. إضافة Vector DB للذاكرة/RAG.

## API داخلي مضاف

- `GET /api/autocoder-meta/capabilities` — تقرير قدرات ونواقص owner-only.
- `GET /api/autocoder-meta/roadmap` — خارطة مراحل مختصرة owner-only.

