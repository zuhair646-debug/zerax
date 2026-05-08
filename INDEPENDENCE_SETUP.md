# 🔓 جعل Zitex مستقلاً 100% عن Emergent

هذا الدليل يخلّي **برمجة زيتاكس** والذكاء الرئيسي (`/api/agent/chat`) يستخدمون مفاتيحك الخاصة مباشرة، بحيث ما تنخصم أي نقاط من حساب Emergent عند الاستخدام.

---

## 1. احصل على مفتاح Anthropic (Claude)

1. افتح [console.anthropic.com](https://console.anthropic.com) وسجّل حساب
2. اضغط على Profile (يمين فوق) → **API Keys** → **Create Key**
3. سمّ المفتاح: مثلاً `Zitex Production`
4. **انسخ المفتاح فوراً** (يبدأ بـ `sk-ant-...`) — Anthropic ما يعرضه ثاني مرة
5. اضغط **Plans & Billing** → اختار **Build plan** وأضف credit card

**التكلفة لـClaude Sonnet 4.5**:
- Input: ~$3 / مليون token
- Output: ~$15 / مليون token
- محادثة عادية = أقل من سنت واحد ✅

---

## 2. أضف المفتاح على Railway

### للـbackend production:
1. افتح [railway.app](https://railway.app) → مشروع Zitex → **Variables**
2. اضغط **+ New Variable**:
   - Name: `ANTHROPIC_API_KEY`
   - Value: `sk-ant-...` (المفتاح اللي نسختَه)
3. احفظ → Railway يعيد deploy تلقائياً

### للتجربة المحلية / preview environment:
أضف المفتاح في `/app/backend/.env`:
```
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```
ثم أعد تشغيل الـbackend:
```bash
sudo supervisorctl restart backend
```

---

## 3. تحقق من أن المفتاح شغّال

افتح `/admin/autocoder` كمالك. شف الـbadge فوق:
- 🔓 **"مستقل — مفتاحك الخاص"** (أخضر) → ✅ كل شي على حسابك مباشرة
- ⚡ **"مفتاح Emergent (نقاط تنخصم)"** (أصفر) → المفتاح ما تم تحميله بعد

أو من curl:
```bash
curl https://your-zitex-domain.com/api/autocoder/key-status \
  -H "Authorization: Bearer YOUR_OWNER_JWT"
```

النتيجة المطلوبة:
```json
{
  "mode": "direct",
  "is_independent": true,
  "label": "🔓 مستقل — مفتاحك الخاص",
  "source": "ANTHROPIC_API_KEY"
}
```

---

## 4. أين تُستخدم هذه المفاتيح؟

| الميزة | المفتاح المستخدم لما يكون موجود | Fallback |
|---|---|---|
| `/admin/autocoder` (برمجة زيتاكس) | `ANTHROPIC_API_KEY` | EMERGENT_LLM_KEY |
| `/ai-agent` (الذكاء الرئيسي - Claude path) | `ANTHROPIC_API_KEY` | EMERGENT_LLM_KEY |
| `/ai-agent` (GPT-4o path) | `OPENAI_DIRECT_KEY` (موجود) | — |
| توليد الصور (Nano Banana) | EMERGENT_LLM_KEY | — |
| توليد الصوت (ElevenLabs) | `ELEVENLABS_API_KEY` (موجود) | — |
| Stripe | `STRIPE_API_KEY` (موجود) | — |

**ملاحظة**: لتوليد الصور (Nano Banana) لسه يستخدم EMERGENT_LLM_KEY لأنها ميزة حصرية لـEmergent. لو تبي استقلال كامل عنها، لازم تستخدم direct OpenAI gpt-image-1 (متوفر في الكود لبعض الأقسام).

---

## 5. اختبار سريع

بعد ما تضيف المفتاح، جرّب من برمجة زيتاكس:
```
اقرأ /app/backend/.env واعرض لي المفاتيح المضبوطة (بدون قيمها).
```

لو رد بسرعة وبدون أخطاء = شغّال 100%. الذكاء يكلّمك على حسابك مباشرة، بدون أي خصم من Emergent.

---

## أمان

- ✅ المفاتيح ما تتسرّب أبداً للـfrontend (تبقى في server-side .env فقط)
- ✅ `/api/autocoder/key-status` يرجّع metadata فقط (mode/source) — مو المفتاح نفسه
- ✅ الـlogs ما يطبعون المفتاح
- 🚨 لا تـcommit `.env` على GitHub — `.gitignore` يحميك بس راجع كل push

---

تم إعداد الاستقلال ✅
