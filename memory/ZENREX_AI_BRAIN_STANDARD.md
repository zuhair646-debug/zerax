# 🦁 Zenrex AI Brain — المعيار المعتمد رسمياً

> **آخر تحديث**: ١٢ يونيو ٢٠٢٦
> **الحالة**: ✅ **معتمد ومثبّت** — هذا هو المعيار الموحّد لكل أقسام Zenrex
> **بناءً على طلب المالك**: "أي تحديث نحطه على الذكاء الاصطناعي في قسم إنشاء المواقع من الصفر — نصلّح كل شي ونعتمده من الآن ونخلّيه جاهز"

---

## 🎯 القاعدة الأساسية:
**كل أقسام Zenrex التي تستخدم AI (FreeBuild, Ready Sites, Image Studio, Video Studio,
Cinema Studio) تستخدم نفس الـ AI Brain أدناه. تبديل السلوك يكون فقط عبر `mode` parameter.**

---

## 🤖 النموذج الأساسي:
```
claude-sonnet-4-5-20250929 (Anthropic)
Fallback chain:
  1. ANTHROPIC_API_KEY (direct)
  2. EMERGENT_LLM_KEY (proxied)
Max iterations: 30 per turn
Context window: 200K tokens
Output: 64K tokens
```

---

## 🛠️ الأدوات المعتمدة (21 أداة)

### القراءة والفحص (5)
- `read_current_html` — قراءة الـ HTML الحالي
- `list_sections` — قائمة الأقسام
- `search_html(pattern)` — بحث بـ regex
- `validate_html` — فحص أخطاء HTML
- `lint_javascript(code)` — فحص JS

### الكتابة والتعديل (3)
- `write_full_html(html)` — كتابة موقع كامل
- `apply_section(id, html, op)` — قسم محدد
- `update_nav(items)` — قائمة التنقل

### الويب والبحث (2)
- `web_search(query, max_results)` — بحث Tavily + DuckDuckGo
- `fetch_url(url)` — جلب محتوى URL

### الميديا (3)
- `generate_image(description, w, h)` — Gemini Nano Banana
- `download_media(url, format)` — yt-dlp (1000+ موقع)
- `test_page(url)` — Playwright + Chromium

### السينما (5)
- `list_voices(language, limit)` — ElevenLabs + samples
- `generate_voiceover(text, voice_id, model)` — TTS MP3
- `write_script(title, logline, ...)` — سيناريو منظّم
- `generate_storyboard(scenes, style)` — keyframes Gemini
- `update_world_bible(...)` — ذاكرة المسلسلات

### النشر والصلاحيات (3)
- `publish_site(slug)` — نشر فوري على zenrex.ai/s/{slug}
- `request_credential(service, label, instructions)` — طلب مفاتيح
- `finish(summary)` — إنهاء التيرن

---

## 🦁 العقلية المعتمدة (System Prompt Rules)

1. ❌ **ممنوع**: "ما أعرف"، "ما أقدر"، "unknown tool"، "الأداة غير مفعّلة"
2. 🚨 **ممنوع**: ادعاء فشل أداة قبل استدعائها فعلياً
3. 📋 **إلزامي**: مراجعة قائمة الأدوات الـ 21 قبل الادعاء
4. 🔬 **إلزامي**: عرض رسائل الخطأ **حرفياً** بدون اختراع تفسيرات
5. 🧠 **إلزامي**: ذاكرة طويلة — لا إعادة تصميم إلا بطلب صريح
6. 💪 **إلزامي**: 3 مقاربات قبل الاستسلام
7. 🚀 **إلزامي**: تنفيذ، لا سؤال
8. 🛡️ **إلزامي**: فحص ذاتي (validate_html + lint_javascript) قبل finish
9. ⏱️ **إلزامي**: ≤ 20 turn للمشاريع المتوسطة

---

## 🎨 الـ Modes الثلاثة (نفس النموذج، نفس الأدوات، system prompt متغيّر)

| Mode | الـ Addendum | الاستخدام |
|---|---|---|
| `website` (default) | الـ prompt الأساسي | بناء مواقع HTML |
| `image_studio` | Image Studio addendum | معارض صور AI |
| `video_studio` | Cinema/Video addendum | أفلام + إعلانات + reels |

---

## 🔑 المفاتيح المعتمدة في `.env`

| Service | الحالة |
|---|---|
| ANTHROPIC_API_KEY | ✅ Active |
| EMERGENT_LLM_KEY | ✅ Active (fallback) |
| GEMINI_API_KEY | ✅ Active |
| OPENAI_DIRECT_KEY | ✅ Active |
| ELEVENLABS_API_KEY | ⚠️ **يحتاج تجديد** (401 Unauthorized) |
| FAL_AI_KEY | ❌ **مفقود** — يحتاجه Veo 3/Kling |
| TAVILY_API_KEY | ✅ Active |

---

## 🏗️ البنية التحتية المعتمدة

| المكوّن | الحالة |
|---|---|
| Nginx SSE streaming (proxy_buffering off للـ /agent-chat-stream) | ✅ |
| Nginx route `/s/{slug}` للمواقع المنشورة | ✅ |
| yt-dlp 2026.06.09 + ffmpeg 7.1.4 في container | ✅ |
| Playwright + Chromium 147 (headless) في container | ✅ |
| MongoDB Atlas | ✅ |
| Cloudflare + Let's Encrypt SSL | ✅ |

---

## 📜 قاعدة التطوير المستقبلية:

**أي تحديث على الـ AI من الآن فصاعداً يجب أن يحدث في:**
1. `/app/backend/modules/freebuild/freebuild_agent.py`
2. ينتشر تلقائياً لكل الأقسام التي تستخدم نفس الـ chat (FreeBuild, Ready Sites, Image Studio, Video Studio, Cinema)

**لا يجوز إنشاء AI brain منفصل لقسم آخر**. الـ mode parameter كافٍ.

---

**هذا الملف هو المرجع الموثوق. أي agent جديد يأتي للمشروع يجب أن يقرأه أولاً.**
