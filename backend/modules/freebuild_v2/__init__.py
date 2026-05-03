"""
Zitex FreeBuild v2 — CONVERSATIONAL LIVE BUILDER.

Philosophy:
    NO fixed wizard. NO templates. The user has a natural conversation with a
    senior web architect AI. The AI asks ONE question at a time (dynamically
    chooses text/yes-no). After enough context, it starts BUILDING LIVE — each
    chat turn incrementally updates the HTML, which renders instantly in a side
    preview pane. The user sees the site materialize step-by-step.

Flow example:
    AI: "هلا! وش فكرة الموقع؟"                        (qtype: text)
    USER: "موقع لتحفيظ القرآن الكريم"
    AI: "تمام، مشروع مبارك. تبيه يدعم التسجيل؟"         (qtype: yes_no)
    USER: "نعم"
    AI: "يلا أبدأ بالهيكل الأساسي..." + html_update
    → preview shows hero with Quran theme
    AI: "تبي مكتبة قرّاء في القسم الثاني؟"              (qtype: yes_no)
    USER: "نعم — ١٠ قرّاء"
    AI: "عطني أسماء ٣ قرّاء تفضلهم"                   (qtype: text)
    USER: "السديس، الشريم، المعيقلي"
    AI: "ممتاز." + html_update  (adds readers grid)
    ... and so on.

Endpoints:
    POST /api/freebuild/v2/start          — creates session + first AI message
    POST /api/freebuild/v2/chat           — submit user message, get AI reply + (optional) html_update
    GET  /api/freebuild/v2/session/{id}   — fetch full state (messages + html)
    GET  /api/freebuild/v2/preview/{id}   — live HTML preview
    POST /api/freebuild/v2/save-as-project — lock current HTML as a permanent project
    GET  /api/freebuild/v2/projects       — list saved projects
    DELETE /api/freebuild/v2/project/{id}
"""
from __future__ import annotations
import os
import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---- Pricing ----
# A turn that updates HTML costs this many credits. Pure Q&A turns are free.
TURN_UPDATE_COST = 3
# Saving a session as a permanent named project is free (they already paid per update).

# Hard cap on chat turns per session to prevent runaway costs.
MAX_TURNS_PER_SESSION = 60


# ---- Architect System Prompt ----
ARCHITECT_SYSTEM = """أنت مهندس ومصمم ويب محترف على أعلى مستوى (مستوى Apple / Stripe / Linear). بتتكلم بالعربي السعودي مع عميل، وبتبني معه **تطبيق ويب متكامل من عدة صفحات داخلية** — مو صفحة وحدة فقط. زي أي تطبيق حقيقي: صفحة رئيسية + تسجيل دخول + لوحة تحكم + صفحات داخلية للمميزات.

## STRICT JSON OUTPUT (كل رد)
```
{
  "message_to_user": "<النص بالعربي السعودي — بدون emoji، قصير، ودود>",
  "next_question_type": "text" | "yes_no" | "done",
  "options": null | ["نعم","لا"],
  "html_update": null | "<HTML كامل — تطبيق متعدد الصفحات في ملف واحد>",
  "progress_note": null | "<سطر عربي يوصف شنو ضفت/عدّلت/بنيت>"
}
```

## 🏛️ الفلسفة الأساسية — MULTI-PAGE SPA (single HTML file)

أنت تبني **Single-Page Application** (SPA) في ملف HTML واحد يحتوي على عدة صفحات داخلية. كل "صفحة" هي `<section class="page" id="page-X">` مع CSS `display:none` ما عدا الصفحة النشطة. التنقل عبر hash routing: `#/home`, `#/login`, `#/dashboard`, `#/readers`, etc.

### 🎯 الحد الأدنى من الصفحات في أول html_update

أول تحديث HTML لازم يحتوي على هذه الصفحات (كحد أدنى، كلها في نفس الملف):

1. **#/home** — الصفحة الرئيسية: navbar + hero ضخم + قسم مميزات (3-6 بطاقات) + قسم ثاني + footer
2. **#/login** — صفحة تسجيل دخول: form أنيق (email + password + زر دخول + link لـ register)
3. **#/register** — صفحة إنشاء حساب: form (name + email + password + confirm + زر التسجيل)
4. **#/dashboard** — لوحة تحكم: sidebar + main area + user greeting + stats cards
5. **صفحة داخلية واحدة على الأقل خاصة بالمجال** (حسب نوع الموقع):
   - تحفيظ قرآن → **#/readers** (مكتبة قرّاء)، **#/lessons** (الدروس)
   - متجر → **#/products** (المنتجات)، **#/cart** (السلة)
   - عيادة → **#/book** (حجز موعد)، **#/doctors** (الأطباء)
   - تعليم → **#/courses** (الدورات)، **#/teachers** (المعلمون)

### 🔀 Router JS (إجباري في كل تحديث)
```javascript
// Hash-based router
function navigate() {
  const hash = window.location.hash.slice(2) || 'home';  // #/page → page
  document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
  const target = document.getElementById('page-' + hash);
  if (target) target.style.display = 'block';
  else document.getElementById('page-home').style.display = 'block';
  document.querySelectorAll('.nav-link').forEach(l => {
    l.classList.toggle('active', l.getAttribute('href') === '#/' + hash);
  });
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', navigate);
window.addEventListener('DOMContentLoaded', navigate);
```

### 🎨 Navbar
- sticky أعلى الصفحة، backdrop-filter blur
- لوقو + روابط `<a href="#/home">` `<a href="#/readers">` إلخ
- أيقونة حساب (avatar) على اليسار — عليها hover يظهر dropdown فيه "الملف الشخصي" و "الإعدادات" و "تسجيل خروج"
- hamburger menu على الجوال

### 🎛️ Account Dropdown (إجباري)
```html
<div class="user-menu">
  <button class="avatar-btn">
    <span class="avatar">أ</span>
  </button>
  <div class="dropdown">
    <a href="#/profile">الملف الشخصي</a>
    <a href="#/settings">الإعدادات</a>
    <hr>
    <a href="#/login" class="logout">تسجيل خروج</a>
  </div>
</div>
```
+ CSS لإظهار الـdropdown عند hover

### 📐 Dashboard Layout
```html
<section class="page" id="page-dashboard">
  <div class="dash-layout">
    <aside class="sidebar">
      <!-- قائمة جانبية للأقسام الداخلية -->
    </aside>
    <main class="dash-main">
      <header class="dash-header">مرحباً، [اسم المستخدم]</header>
      <div class="stats-grid"><!-- 4 stat cards --></div>
      <!-- محتوى اللوحة -->
    </main>
  </div>
</section>
```

### 🔐 Forms (Login/Register)
```html
<form class="auth-form" onsubmit="event.preventDefault(); window.location.hash='#/dashboard';">
  <h1>تسجيل الدخول</h1>
  <input type="email" placeholder="البريد الإلكتروني" required>
  <input type="password" placeholder="كلمة المرور" required>
  <button type="submit" class="btn-primary">دخول</button>
  <p>ما عندك حساب؟ <a href="#/register">سجّل الآن</a></p>
</form>
```
+ CSS: gradient background، centered card، inputs مع focus states

### ⚙️ Settings Page (#/settings)
- form فيه توجيهات: اسم المستخدم، البريد، تغيير كلمة المرور، لغة الواجهة، إشعارات (toggle switches)

## 🎨 المعايير المرئية الإجبارية
- حجم أول html_update: **20,000 - 50,000 حرف** (تطبيق كامل متعدد الصفحات)
- كل تحديث لاحق: يضيف صفحة أو يوسّع واحدة موجودة
- CSS variables ≥ 7 ألوان
- خطوط Google Arabic (Tajawal + Cairo + Reem Kufi for Quran sites)
- @keyframes (fadeInUp, float, pulse على الأقل)
- hover transitions على كل الأزرار والبطاقات
- responsive — navbar يتحوّل hamburger على ≤768px
- Real Arabic content — مو Lorem Ipsum

## 🧠 منطق المحادثة

### الدورة 1-2 (جمع سريع، html_update=null إن احتجت)
- اجمع: اسم المشروع، الجمهور، الألوان/الهوية

### الدورة 2-3 (أول بناء إجباري)
- ابنِ **التطبيق الكامل** بكل الصفحات المذكورة فوق
- لو ما عندك تفاصيل، خذ افتراضات منطقية

### الدورات اللاحقة (توسيع)
- أضف صفحات جديدة (حسب طلب العميل)
- وسّع الصفحات الموجودة
- حسّن التصميم

## ⛔ قواعد صارمة — لا تكسرها

1. **لا تسأل العميل عن اسم المشروع** — هذا نحفظه في زر "حفظ" منفصل. ما يهمك أصلاً.
2. **لا تعلن انتهاء المشروع من نفسك** — العميل هو اللي يقرر متى يخلص. خلي `next_question_type` دائماً يكون `text` أو `yes_no` (اسأل عن تحسين جديد). **لا ترجع `done` إلا لو العميل قال صراحة "خلاص انتهيت احفظه" أو "تمام كذا يكفي".**
3. **لا تبني صفحة واحدة فقط** — الحد الأدنى هو SPA بـ5 صفحات (home + login + register + dashboard + inner).
4. **لا تستخدم frameworks خارجية** (Bootstrap, Tailwind, React).
5. **لا Lorem ipsum**. محتوى عربي حقيقي غني يناسب المجال.
6. **لا markdown fences** في JSON الرد.
7. **لا تكرر "راح أصمم"** — صمّم الآن.

## 🏆 قالب مرجعي للـSPA الناجح

```html
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>اسم المشروع</title>
  <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap" rel="stylesheet">
  <style>
    :root { --primary: #...; --accent: #...; --bg: #...; ... }
    * { margin:0; padding:0; box-sizing:border-box }
    body { font-family: 'Tajawal', sans-serif; background: var(--bg); color: var(--text) }
    .page { display: none; min-height: 100vh }
    .page.active { display: block }
    /* navbar */
    .navbar { ... sticky ... }
    .nav-link.active { color: var(--primary) }
    /* pages */
    #page-home { ... }
    #page-login { display: flex; align-items: center; justify-content: center; min-height:100vh }
    #page-dashboard .dash-layout { display: grid; grid-template-columns: 260px 1fr }
    /* dropdown, forms, cards ... */
    /* keyframes */
    @keyframes fadeInUp { from { opacity:0; transform: translateY(30px) } to { opacity:1; transform: translateY(0) } }
    /* media */
    @media (max-width:768px) { .nav-links { display:none } ... }
  </style>
</head>
<body>
  <!-- navbar (يظهر في كل الصفحات ما عدا login/register) -->
  <header class="navbar"> ... </header>

  <!-- HOME -->
  <section class="page" id="page-home">
    <section class="hero"> ... </section>
    <section class="features"> ... </section>
    <footer> ... </footer>
  </section>

  <!-- LOGIN -->
  <section class="page" id="page-login"> <form class="auth-form"> ... </form> </section>

  <!-- REGISTER -->
  <section class="page" id="page-register"> <form class="auth-form"> ... </form> </section>

  <!-- DASHBOARD -->
  <section class="page" id="page-dashboard"> <div class="dash-layout"> ... </div> </section>

  <!-- INNER PAGES -->
  <section class="page" id="page-readers"> ... </section>
  <section class="page" id="page-lessons"> ... </section>

  <script>
    function navigate() { /* router code */ }
    window.addEventListener('hashchange', navigate);
    window.addEventListener('DOMContentLoaded', navigate);
  </script>
</body>
</html>
```

## ✅ تذكير نهائي
- أخرج JSON فقط
- لا preamble، لا markdown fences، لا شرح
- لا تسأل عن اسم المشروع (زر "حفظ" يتولى ذلك)
- لا تنهي المحادثة من نفسك
- كل html_update يجب أن يكون SPA متعدد الصفحات بـ≥20KB"""



# ---- Pydantic Models ----

class StartIn(BaseModel):
    pass

class ChatIn(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1, max_length=2000)

class SaveProjectIn(BaseModel):
    session_id: str
    name: str = Field(..., min_length=1, max_length=80)

class RefineIn(BaseModel):
    project_id: str
    instruction: str = Field(..., min_length=4, max_length=600)

class RegenImagesIn(BaseModel):
    session_id: str
    style_seed: Optional[str] = ""

class NavEditIn(BaseModel):
    session_id: str
    action: str  # 'rename' | 'delete' | 'add' | 'reorder'
    # For 'rename'
    route_id: Optional[str] = None  # e.g. "rewards" (without "#/")
    new_label: Optional[str] = None
    # For 'add'
    new_label_for_add: Optional[str] = None
    new_brief: Optional[str] = None  # what the new page should contain
    # For 'reorder'
    ordered_ids: Optional[List[str]] = None

class ConstraintAddIn(BaseModel):
    session_id: str
    rule: str = Field(..., min_length=3, max_length=400)
    category: Optional[str] = "manual"


# ---- Helpers ----

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _openai_architect_turn(messages_for_model: List[Dict[str, str]]) -> Dict[str, Any]:
    """Call an LLM with JSON response format, return parsed dict.
    Tries OPENAI_DIRECT_KEY first (user's own billing). Falls back to EMERGENT_LLM_KEY.
    Raises a specific HTTPException if neither key is configured.
    """
    direct_key = os.environ.get("OPENAI_DIRECT_KEY", "").strip()
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    content = ""

    last_error = None

    # ===== Try OpenAI direct =====
    if direct_key:
        try:
            from openai import AsyncOpenAI
            from .tools import TOOL_SCHEMAS, execute_tool_call
            client = AsyncOpenAI(api_key=direct_key)

            # ── Tool-calling loop (max 4 iterations) ──
            local_msgs = list(messages_for_model)
            for _iter in range(4):
                resp = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=local_msgs,
                    temperature=0.85,
                    max_tokens=16000,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                )
                msg = resp.choices[0].message
                # If model wants to call tools, execute them and feed back
                if msg.tool_calls:
                    local_msgs.append({
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {"id": tc.id, "type": "function",
                             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                            for tc in msg.tool_calls
                        ],
                    })
                    # Execute each tool call concurrently
                    async def _run(tc):
                        try:
                            args = json.loads(tc.function.arguments or "{}")
                        except Exception:
                            args = {}
                        result = await execute_tool_call(tc.function.name, args)
                        logger.info(f"[FB2-TOOL] {tc.function.name}({list(args.keys())}) → ok={result.get('ok')}")
                        return tc.id, result
                    pairs = await asyncio.gather(*[_run(tc) for tc in msg.tool_calls])
                    for tid, result in pairs:
                        local_msgs.append({
                            "role": "tool",
                            "tool_call_id": tid,
                            "content": json.dumps(result, ensure_ascii=False)[:8000],
                        })
                    continue  # loop back so model can now produce final JSON
                # No tool call → final answer; force it through json mode now
                # Re-call with response_format=json_object on the same context
                final = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=local_msgs + [{"role": "user", "content": "أرجع الآن الـJSON النهائي فقط."}],
                    temperature=0.5,
                    max_tokens=16000,
                    response_format={"type": "json_object"},
                )
                content = (final.choices[0].message.content or "").strip()
                break
            else:
                # 4 iterations of tool calls without final → force one more
                final = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=local_msgs + [{"role": "user", "content": "أرجع الـJSON النهائي الآن. لا أدوات إضافية."}],
                    temperature=0.5,
                    max_tokens=16000,
                    response_format={"type": "json_object"},
                )
                content = (final.choices[0].message.content or "").strip()
        except Exception as e:
            last_error = f"OpenAI direct: {type(e).__name__}: {str(e)[:200]}"
            logger.warning(f"[FREEBUILD] OpenAI direct failed, trying emergent: {last_error}")
            content = ""

    # ===== Fallback: Emergent universal key =====
    if not content and emergent_key:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            # Build a single concatenated prompt since LlmChat takes one message
            system_parts = [m["content"] for m in messages_for_model if m["role"] == "system"]
            user_parts = [m["content"] for m in messages_for_model if m["role"] == "user"]
            sys_combined = "\n\n".join(system_parts)
            # The last user message is the current turn
            last_user_msg = user_parts[-1] if user_parts else ""
            # Prior user turns as context
            prior = "\n\n".join([f"[عميل سابق] {u}" for u in user_parts[:-1]])
            user_combined = (prior + "\n\n" + f"[عميل الآن] {last_user_msg}").strip()

            chat = LlmChat(
                api_key=emergent_key,
                session_id=f"fb2-{uuid.uuid4()}",
                system_message=sys_combined,
            )
            chat.with_model("openai", "gpt-4o")
            # Emergent wrapper doesn't support response_format; emphasize JSON in prompt
            user_combined += "\n\n⚠️ أعد فقط JSON كما هو موضّح في الـsystem prompt. لا markdown، لا شيء آخر."
            content = (await chat.send_message(UserMessage(text=user_combined)) or "").strip()
        except Exception as e:
            last_error = (last_error + " | " if last_error else "") + f"Emergent: {type(e).__name__}: {str(e)[:200]}"
            logger.warning(f"[FREEBUILD] Emergent fallback failed: {str(e)[:200]}")
            content = ""

    if not content:
        if not direct_key and not emergent_key:
            raise RuntimeError(
                "مفتاح الذكاء الاصطناعي غير مُعدّ. محتاج تضيف OPENAI_DIRECT_KEY (مفضّل) "
                "أو EMERGENT_LLM_KEY في Railway/Render environment variables."
            )
        raise RuntimeError(
            f"فشل الاتصال بالذكاء (تأكد من شحن رصيد OpenAI أو Emergent): {last_error}"
        )

    # Strip accidental markdown fences
    if content.startswith("```"):
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    # Some models wrap JSON in extra text — extract {...}
    if not content.startswith("{"):
        i = content.find("{")
        j = content.rfind("}")
        if i >= 0 and j > i:
            content = content[i:j + 1]

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"[FREEBUILD] JSON parse failed. Raw: {content[:500]}")
        raise RuntimeError(f"AI returned invalid JSON: {e}")

    # Validate shape
    required = ["message_to_user", "next_question_type"]
    for k in required:
        if k not in data:
            raise RuntimeError(f"AI response missing field: {k}")

    if data["next_question_type"] not in ("text", "yes_no", "done"):
        data["next_question_type"] = "text"

    data.setdefault("options", None)
    data.setdefault("html_update", None)
    data.setdefault("progress_note", None)

    # Strip markdown fences in html if AI added them
    html = data.get("html_update")
    if html and isinstance(html, str):
        h = html.strip()
        if h.startswith("```"):
            lines = h.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            h = "\n".join(lines).strip()
        if "<html" not in h.lower():
            # Invalid HTML — treat as null
            logger.warning("[FREEBUILD] html_update missing <html>, discarding")
            data["html_update"] = None
        else:
            # AI-GENERATE every image inline via Nano Banana, then save the
            # resulting HTML. Falls back to Unsplash library only if AI fails.
            try:
                from .image_gen import post_process_html_with_ai_images
                from .resources import resolve_image_for_keyword
                h = await post_process_html_with_ai_images(
                    h,
                    style_seed="",
                    fallback_resolver=resolve_image_for_keyword,
                )
            except Exception as _imgerr:
                logger.warning(f"[FREEBUILD] AI image post-process failed: {_imgerr}")
                # Last-resort: keep old behavior so the page still renders
                try:
                    from .resources import post_process_html_images
                    h = post_process_html_images(h)
                except Exception:
                    pass
            data["html_update"] = h

    return data


def _build_model_messages(session: Dict[str, Any], new_user_msg: str) -> List[Dict[str, str]]:
    """Compose the full message list for the model, including current HTML state.
    Includes server-side forcing logic: if user has made 2+ turns without an HTML
    being built, inject a hard instruction to BUILD NOW this turn."""
    msgs: List[Dict[str, str]] = [{"role": "system", "content": ARCHITECT_SYSTEM}]

    # Inject the resource library so the architect has real Unsplash IDs +
    # Quran audio CDN URLs + SVG icons + verse design templates ready to use.
    try:
        from .resources import build_resources_block
        msgs.append({"role": "system", "content": build_resources_block()})
    except Exception as _re:
        logger.warning(f"[FREEBUILD] resources block failed: {_re}")

    # 🧠 DOMAIN INTELLIGENCE — inject the matching blueprint based on what
    # the user has said so far. This gives the architect a senior-consultant
    # checklist of pages, features, flows, and cohesion rules per domain.
    try:
        from .blueprints import detect_domain, render_blueprint_block, LINKING_RULES
        # Build a single blob from all user turns + the incoming new message
        user_text_blob = " ".join(
            (m.get("content", "") for m in session.get("messages", []) if m.get("role") == "user")
        ) + " " + (new_user_msg or "")
        domain_key = detect_domain(user_text_blob)
        if domain_key:
            logger.info(f"[FREEBUILD] domain detected: {domain_key}")
        msgs.append({"role": "system", "content": render_blueprint_block(domain_key)})
        msgs.append({"role": "system", "content": LINKING_RULES})
    except Exception as _bpe:
        logger.warning(f"[FREEBUILD] blueprint inject failed: {_bpe}")

    # ⚓ VERIFIED SOURCES — no invented URLs / names / statistics
    try:
        from .verified_sources import build_verified_sources_block
        msgs.append({"role": "system", "content": build_verified_sources_block(domain_key)})
    except Exception as _vse:
        logger.warning(f"[FREEBUILD] verified sources inject failed: {_vse}")

    # 🚫 PERSISTENT CONSTRAINTS — user's hard rules + optional edit scope
    try:
        from .constraints import render_constraints_block, detect_edit_scope
        saved_constraints = session.get("constraints") or []
        edit_scope = detect_edit_scope(new_user_msg or "")
        cblock = render_constraints_block(saved_constraints, edit_scope)
        if cblock:
            msgs.append({"role": "system", "content": cblock})
    except Exception as _ce:
        logger.warning(f"[FREEBUILD] constraints inject failed: {_ce}")

    # 🛠️ TOOL USAGE INSTRUCTIONS — empower the architect to call real tools
    msgs.append({"role": "system", "content": (
        "## 🛠️ نظام الأدوات (Tool Calling) — قدراتك الجديدة\n"
        "أنت الآن agent يقدر **ينفّذ أدوات حقيقية** بدلاً من الاختراع. الأدوات المتاحة:\n\n"
        "1. **`quran_reciter_lookup(name, surah)`** — يرجع روابط mp3quran.net الحقيقية لقارئ "
        "محدد. **استخدمها لازم** قبل ما تكتب أي `<audio src='...'>` في موقع قرآن.\n"
        "2. **`quran_verse_fetch(surah, ayah)`** — يجلب نص آية بالضبط من alquran.cloud. "
        "**استخدمها لازم** قبل ما تعرض أي آية كنص (لأنك تحرّف).\n"
        "3. **`web_search(query, num)`** — DuckDuckGo بحث حقيقي. استخدمها لجلب أمثلة، "
        "منافسين، أرقام، شراكات.\n"
        "4. **`web_fetch(url, max_chars)`** — يجلب نص صفحة فعلية. استخدمها بعد web_search "
        "لاستخراج تفاصيل دقيقة.\n"
        "5. **`generate_image_url(description)`** — توليد صورة AI لو احتجت URL مباشر "
        "(عادة استعمل `@@IMG/auto@@` بدل هذا، أوفر).\n\n"
        "### متى تستخدم الأدوات؟\n"
        "- موقع قرآن → استدعِ `quran_reciter_lookup` لكل قارئ تبي تذكره. لا تخترع slugs.\n"
        "- العميل طلب نموذج/مرجع/منافس → استدعِ `web_search` ثم `web_fetch` للنتيجة الأهم.\n"
        "- آية محددة → استدعِ `quran_verse_fetch`.\n\n"
        "### قاعدة ذهبية:\n"
        "**ممنوع** تخترع رابط، رقم سورة، اسم سلج (slug)، أو إحصائية. لو احتجت بيانات "
        "حقيقية، استدعِ الأداة المناسبة. هذا الفرق بين موقع احترافي وموقع شعبي.\n"
    )})

    # 🔥 NEW IMAGE SYSTEM (Feb 2026) — every image is AI-generated server-side
    # The architect must NOT write hardcoded image URLs. It just writes <img>
    # with a vivid Arabic `alt=""` and (optionally) `@@IMG/<keyword>@@` as src.
    # The server reads alt + nearest heading + class hint and generates a
    # bespoke AI image (Nano Banana) for each <img>. Same alt → same image.
    msgs.append({"role": "system", "content": (
        "## 🎨 نظام الصور الجديد (إجباري)\n"
        "كل صورة في الموقع راح تُولَّد بالذكاء الاصطناعي تلقائياً (Gemini Nano Banana) "
        "بناءً على وصف الـalt + أقرب عنوان h1/h2/h3 + اسم الكلاس.\n\n"
        "**القواعد**:\n"
        "1. اكتب `<img src=\"@@IMG/auto@@\" alt=\"<وصف عربي تفصيلي للمشهد المطلوب>\">` — "
        "السيرفر يستبدل src بصورة AI حقيقية.\n"
        "2. الـalt لازم يكون **وصف بصري غني بالعربي** (5-15 كلمة) عن المشهد المطلوب — "
        "مو مجرد كلمة. مثلاً:\n"
        "   - بدل `alt=\"مكافآت\"` اكتب `alt=\"كأس ذهبي وهدايا ملوّنة ونجوم متطايرة في احتفال بالأطفال\"`\n"
        "   - بدل `alt=\"مسجد\"` اكتب `alt=\"المسجد النبوي الشريف وقت الغروب بإضاءة ذهبية روحانية\"`\n"
        "   - بدل `alt=\"تلاوة\"` اكتب `alt=\"مصحف مفتوح بإضاءة دافئة وأحرف ذهبية وخلفية روحانية\"`\n"
        "3. ممنوع كتابة روابط Unsplash مباشرة (images.unsplash.com/photo-xxxxx). السيرفر سيرفضها.\n"
        "4. لـbackground-image في CSS: استعمل `background-image: url(@@IMG/auto@@)` "
        "وضع class وصفي قوي على نفس العنصر (مثلاً `class=\"hero-rewards-section\"`) "
        "ليلتقطه السيرفر كسياق.\n"
        "5. الـalt هو **الـprompt** للذكاء — كلما كان أوضح وأغنى، الصورة تطلع أحسن.\n"
        "6. لا تقلق من 'تكرار' الصور — الـcache عبر hash، ولكل alt مختلف صورة مختلفة.\n"
    )})

    # Append the conversation history
    for m in session.get("messages", []):
        role = m.get("role")
        content = m.get("content", "")
        if role in ("user", "assistant"):
            if role == "assistant":
                content = m.get("message_to_user", content) or content
            msgs.append({"role": role, "content": content})

    # Count user turns so far (excluding the incoming one)
    user_turns_so_far = sum(1 for m in session.get("messages", []) if m.get("role") == "user")
    current_html = session.get("html") or ""

    # Inject current HTML state as a system reminder
    if current_html:
        msgs.append({
            "role": "system",
            "content": (
                "## CURRENT_HTML_STATE (modify from this baseline when you return html_update)\n"
                "```html\n" + current_html + "\n```"
            ),
        })

    # ═══════════════════════════════════════════════════════════════════
    # 🔥 SERVER-SIDE FORCING: prevent AI from asking endless questions
    # ═══════════════════════════════════════════════════════════════════
    # user_turns_so_far counts prior turns (the incoming one not yet in session)
    # So by turn count 2 (this is the 3rd user message), we ALREADY have 2 answers.
    # If still no HTML by then, FORCE the build on this turn.
    #
    # Rules applied on each incoming user turn (inclusive of this one):
    #   Incoming turn 1 (user_turns_so_far == 0): gather — natural conversation
    #   Incoming turn 2 (user_turns_so_far == 1): gather — second question OK
    #   Incoming turn 3+ (user_turns_so_far >= 2) AND html empty: FORCE BUILD
    #   Any turn where html exists: incremental update encouraged
    incoming_turn_index = user_turns_so_far + 1  # 1-based for this incoming message

    if not current_html and incoming_turn_index >= 3:
        # HARD INSTRUCTION — model MUST build this turn
        msgs.append({
            "role": "system",
            "content": (
                "🚨 ORDER FROM THE USER & PLATFORM — DO NOT IGNORE 🚨\n\n"
                "العميل قدّم معلومات كافية بالفعل. مننتظر تصميماً حقيقياً الآن.\n"
                "- لا تطلب أي معلومة إضافية.\n"
                "- لا تكرّر 'راح أصمم' — صمّم فعلياً هذه اللحظة.\n"
                "- في هذا الرد، `html_update` يجب أن يحتوي على **SPA متعدد الصفحات** (≥5 صفحات) بحجم ≥ 18,000 حرف.\n"
                "- صور Unsplash إجبارية: ≥4 صور `<img>` أو background-image في الموقع.\n"
                "- إذا الموقع قرآني/ديني: ≥3 بطاقات قارئ مع `<audio src='https://server*.mp3quran.net/...'>` + ≥1 آية بتصميم عثماني.\n"
                "- SVG icons من المكتبة المُعطاة لك (≥6 أيقونات في الموقع).\n"
                "- لو نقصك تفصيل، خذ افتراضاً منطقياً واكمل.\n"
                "- `next_question_type` = \"text\" أو \"yes_no\" (سؤال تحسين).\n"
                "- `progress_note` يصف ما بنيته بدقة.\n\n"
                "إذا رجعت رداً بدون html_update غني (≥18KB، صور حقيقية، صوتيات إن كان قرآني، أيقونات SVG)، فشلت في مهمتك."
            ),
        })
    elif current_html:
        # Encourage incremental additions — and remind about visual richness
        msgs.append({
            "role": "system",
            "content": (
                "ملاحظة: الموقع موجود بالفعل. كل رد يجب أن يُحسّن أو يوسّع الموقع.\n"
                "ارجع `html_update` مع الـHTML الكامل المُحدّث (تحافظ على كل الأقسام السابقة وتضيف/تعدّل حسب طلب العميل).\n"
                "تذكير: استخدم مكتبة الموارد (Unsplash IDs + mp3quran CDN + SVG icons + Quran verse template) في كل تحديث."
            ),
        })

    msgs.append({"role": "user", "content": new_user_msg})
    return msgs


# ---- Router factory ----

def create_freebuild_v2_router(db, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/api/freebuild/v2", tags=["freebuild-v2"])

    async def _credits(uid: str) -> int:
        u = await db.users.find_one({"id": uid}, {"_id": 0, "credits": 1})
        return int((u or {}).get("credits", 0) or 0)

    async def _deduct(uid: str, amount: int, reason: str) -> bool:
        r = await db.users.update_one(
            {"id": uid, "credits": {"$gte": amount}},
            {"$inc": {"credits": -amount},
             "$push": {"credit_history": {"amount": -amount, "reason": reason, "timestamp": _now()}}}
        )
        return r.modified_count > 0

    # ===== HEALTH / DIAGNOSTIC =====
    @router.get("/health")
    async def health():
        """Public diagnostic — tells the deployer which keys are set.
        Never leaks the key values themselves."""
        direct = bool(os.environ.get("OPENAI_DIRECT_KEY", "").strip())
        emergent = bool(os.environ.get("EMERGENT_LLM_KEY", "").strip())
        eleven = bool(os.environ.get("ELEVENLABS_API_KEY", "").strip())
        return {
            "service": "freebuild-v2",
            "ok": direct or emergent,
            "keys_configured": {
                "OPENAI_DIRECT_KEY": direct,
                "EMERGENT_LLM_KEY": emergent,
                "ELEVENLABS_API_KEY": eleven,
            },
            "recommendation": (
                None if (direct or emergent)
                else "أضف OPENAI_DIRECT_KEY أو EMERGENT_LLM_KEY في environment variables"
            ),
        }

    # ===== START =====
    @router.post("/start")
    async def start(_: StartIn, user=Depends(get_current_user)):
        sid = str(uuid.uuid4())
        first_ai_message = (
            "هلا والله، أنا المهندس الذكي اللي بيبني موقعك من الصفر. "
            "قبل نبدأ — احكيلي فكرة الموقع بكلمتين. وش تبي تسوي؟ "
            "(مثلاً: موقع لتحفيظ القرآن، متجر عطور، عيادة أسنان، بورتفوليو شخصي...)"
        )
        session = {
            "id": sid,
            "user_id": user["user_id"],
            "messages": [{
                "role": "assistant",
                "content": first_ai_message,
                "message_to_user": first_ai_message,
                "next_question_type": "text",
                "options": None,
                "timestamp": _now(),
            }],
            "html": "",
            "turns": 0,
            "complete": False,
            "credits_spent": 0,
            "created_at": _now(),
            "updated_at": _now(),
        }
        await db.freebuild_v2_sessions.insert_one(session.copy())
        return {
            "session_id": sid,
            "assistant_message": first_ai_message,
            "next_question_type": "text",
            "options": None,
            "html": "",
            "progress_note": None,
            "credits_balance": await _credits(user["user_id"]),
        }

    # ===== CHAT =====
    @router.post("/chat")
    async def chat(payload: ChatIn, user=Depends(get_current_user)):
        session = await db.freebuild_v2_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not session:
            raise HTTPException(404, "session not found")
        # NOTE: we intentionally allow chatting even after a prior 'done' was emitted
        # so the user can keep refining freely until they explicitly save.
        if session.get("turns", 0) >= MAX_TURNS_PER_SESSION:
            raise HTTPException(400, f"تم الوصول للحد الأقصى ({MAX_TURNS_PER_SESSION} دورات). احفظ الموقع وابدأ جلسة جديدة لو تبي تكمل.")

        # Append user message
        session["messages"].append({
            "role": "user",
            "content": payload.message,
            "timestamp": _now(),
        })

        # 🚫 AUTO-EXTRACT CONSTRAINTS from the incoming user message and
        # persist them on the session so every future turn respects them.
        try:
            from .constraints import extract_constraints_from_text
            new_constraints = extract_constraints_from_text(payload.message)
            if new_constraints:
                existing = session.get("constraints") or []
                # Deduplicate by (category, first 60 chars of rule)
                seen_keys = {(c.get("category"), (c.get("rule") or "")[:60]) for c in existing}
                for nc in new_constraints:
                    k = (nc["category"], nc["rule"][:60])
                    if k not in seen_keys:
                        existing.append(nc)
                        seen_keys.add(k)
                session["constraints"] = existing
                logger.info(f"[FREEBUILD] extracted {len(new_constraints)} constraint(s); total={len(existing)}")
        except Exception as _cee:
            logger.warning(f"[FREEBUILD] constraint extract failed: {_cee}")

        # Call the architect
        try:
            model_msgs = _build_model_messages(session, payload.message)
            ai = await _openai_architect_turn(model_msgs)
        except Exception as e:
            err = str(e)[:400]
            logger.exception(f"[FREEBUILD-V2] architect call failed: {err}")
            # Detect common failure causes and give an actionable message
            if "مفتاح الذكاء" in err or "not configured" in err.lower():
                raise HTTPException(500,
                    "مفتاح الذكاء الاصطناعي غير مُعدّ على السيرفر. "
                    "تأكد من إضافة OPENAI_DIRECT_KEY في Environment Variables."
                )
            if "insufficient_quota" in err.lower() or "billing" in err.lower() or "exceeded" in err.lower():
                raise HTTPException(500,
                    "رصيد OpenAI انتهى. اشحن من dashboard.openai.com → Billing، "
                    "أو استخدم EMERGENT_LLM_KEY كبديل."
                )
            if "rate" in err.lower() and "limit" in err.lower():
                raise HTTPException(429, "طلبات كثيرة جداً. انتظر ثانيتين وحاول مرة ثانية.")
            if "invalid" in err.lower() and "key" in err.lower() or "401" in err:
                raise HTTPException(500, "مفتاح OpenAI غير صحيح. تحقق من OPENAI_DIRECT_KEY.")
            raise HTTPException(500, f"فشل الذكاء المعماري: {err[:140]}")

        html_update = ai.get("html_update")
        charge = 0

        # Deduct credits ONLY if this turn actually updated HTML
        if html_update:
            ok = await _deduct(user["user_id"], TURN_UPDATE_COST, "freebuild_v2_turn_update")
            if not ok:
                # Drop the html update but save the assistant's text reply
                html_update = None
                ai["html_update"] = None
                ai["message_to_user"] = (
                    "رصيدك ما يكفي للتحديث ({} نقاط مطلوبة). اشحن رصيدك وارجع — المحادثة محفوظة."
                ).format(TURN_UPDATE_COST)
            else:
                charge = TURN_UPDATE_COST

        # Append assistant message
        assistant_entry = {
            "role": "assistant",
            "content": ai["message_to_user"],
            "message_to_user": ai["message_to_user"],
            "next_question_type": ai["next_question_type"],
            "options": ai.get("options"),
            "progress_note": ai.get("progress_note"),
            "had_html_update": bool(html_update),
            "timestamp": _now(),
        }
        session["messages"].append(assistant_entry)

        update_fields = {
            "messages": session["messages"],
            "turns": session.get("turns", 0) + 1,
            "updated_at": _now(),
            "constraints": session.get("constraints") or [],
        }
        if html_update:
            update_fields["html"] = html_update
            update_fields["credits_spent"] = session.get("credits_spent", 0) + charge
        if ai["next_question_type"] == "done":
            update_fields["complete"] = True

        await db.freebuild_v2_sessions.update_one(
            {"id": payload.session_id},
            {"$set": update_fields}
        )

        return {
            "assistant_message": ai["message_to_user"],
            "next_question_type": ai["next_question_type"],
            "options": ai.get("options"),
            "html_updated": bool(html_update),
            "progress_note": ai.get("progress_note"),
            "complete": ai["next_question_type"] == "done",
            "turns": update_fields["turns"],
            "credits_spent_this_turn": charge,
            "credits_balance": await _credits(user["user_id"]),
            "constraints": session.get("constraints") or [],
        }

    # ===== GET SESSION =====
    @router.get("/session/{session_id}")
    async def get_session(session_id: str, user=Depends(get_current_user)):
        s = await db.freebuild_v2_sessions.find_one(
            {"id": session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not s:
            raise HTTPException(404, "session not found")
        # Slim the messages payload for transport (strip full HTML from each)
        return {
            "id": s["id"],
            "messages": [
                {k: v for k, v in m.items() if k != "html_update"}
                for m in s.get("messages", [])
            ],
            "html": s.get("html", ""),
            "turns": s.get("turns", 0),
            "complete": s.get("complete", False),
            "credits_spent": s.get("credits_spent", 0),
            "constraints": s.get("constraints", []),
            "created_at": s.get("created_at"),
            "updated_at": s.get("updated_at"),
        }

    # ===== LIVE PREVIEW =====
    @router.get("/preview/{session_id}")
    async def preview(session_id: str):
        # Live preview is public-readable (no auth) so iframe can load freely
        s = await db.freebuild_v2_sessions.find_one(
            {"id": session_id}, {"_id": 0, "html": 1}
        )
        if not s or not s.get("html"):
            # Return a pleasant "empty state" HTML
            return Response(
                content=_empty_preview_html(),
                media_type="text/html; charset=utf-8",
            )
        return Response(content=s["html"], media_type="text/html; charset=utf-8")

    # ===== SAVE AS PERMANENT PROJECT =====
    @router.post("/save-as-project")
    async def save_as_project(payload: SaveProjectIn, user=Depends(get_current_user)):
        s = await db.freebuild_v2_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not s:
            raise HTTPException(404, "session not found")
        if not s.get("html"):
            raise HTTPException(400, "لا يوجد موقع محفوظ في هذه الجلسة بعد")

        pid = str(uuid.uuid4())
        slug = payload.name.strip().replace(" ", "-").lower()[:40] or "site"
        proj = {
            "id": pid,
            "user_id": user["user_id"],
            "source_session_id": payload.session_id,
            "name": payload.name.strip(),
            "slug": f"{slug}-{pid[:6]}",
            "html": s["html"],
            "credits_spent": s.get("credits_spent", 0),
            "version": 1,
            "history": [{"version": 1, "html": s["html"], "created_at": _now(), "instruction": "initial save"}],
            "created_at": _now(),
            "updated_at": _now(),
        }
        await db.freebuild_v2_projects.insert_one(proj.copy())
        await db.freebuild_v2_sessions.update_one(
            {"id": payload.session_id},
            {"$set": {"saved_project_id": pid, "complete": True}}
        )
        return {
            "ok": True,
            "project_id": pid,
            "preview_url": f"/api/freebuild/v2/project-preview/{pid}",
        }

    # ===== LIST PROJECTS =====
    @router.get("/projects")
    async def list_projects(user=Depends(get_current_user)):
        cursor = db.freebuild_v2_projects.find(
            {"user_id": user["user_id"]},
            {"_id": 0, "html": 0, "history": 0}
        ).sort("created_at", -1)
        items = await cursor.to_list(length=100)
        return {"projects": items, "count": len(items)}

    # ===== PROJECT PREVIEW (saved) =====
    @router.get("/project-preview/{project_id}")
    async def project_preview(project_id: str):
        p = await db.freebuild_v2_projects.find_one(
            {"id": project_id}, {"_id": 0, "html": 1}
        )
        if not p or not p.get("html"):
            raise HTTPException(404, "project not found")
        return Response(content=p["html"], media_type="text/html; charset=utf-8")

    # ===== REFINE PROJECT (post-save) =====
    @router.post("/refine")
    async def refine(payload: RefineIn, user=Depends(get_current_user)):
        p = await db.freebuild_v2_projects.find_one(
            {"id": payload.project_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "project not found")

        ok = await _deduct(user["user_id"], TURN_UPDATE_COST, "freebuild_v2_refine")
        if not ok:
            raise HTTPException(402, f"رصيدك ما يكفي ({TURN_UPDATE_COST} نقاط مطلوبة)")

        try:
            # One-shot refinement with current HTML as context
            msgs = [
                {"role": "system", "content": ARCHITECT_SYSTEM},
                {"role": "system", "content": f"## CURRENT_HTML\n```html\n{p.get('html','')}\n```"},
                {"role": "user", "content": f"طبّق هذا التعديل على الموقع: {payload.instruction.strip()}"},
            ]
            ai = await _openai_architect_turn(msgs)
            new_html = ai.get("html_update") or p.get("html")
            new_version = int(p.get("version", 1)) + 1
            history = list(p.get("history") or [])
            history.append({
                "version": new_version,
                "html": new_html,
                "instruction": payload.instruction.strip(),
                "created_at": _now(),
            })
            history = history[-10:]
            await db.freebuild_v2_projects.update_one(
                {"id": payload.project_id},
                {"$set": {
                    "html": new_html,
                    "version": new_version,
                    "history": history,
                    "updated_at": _now(),
                }}
            )
            return {
                "ok": True,
                "version": new_version,
                "credits_balance": await _credits(user["user_id"]),
            }
        except Exception as e:
            # refund
            await db.users.update_one(
                {"id": user["user_id"]},
                {"$inc": {"credits": TURN_UPDATE_COST},
                 "$push": {"credit_history": {
                     "amount": TURN_UPDATE_COST,
                     "reason": f"refund_fb2_refine: {str(e)[:80]}",
                     "timestamp": _now(),
                 }}}
            )
            logger.exception(f"[FREEBUILD-V2] refine failed: {e}")
            raise HTTPException(500, f"فشل التحديث. تمت إعادة النقاط. ({str(e)[:120]})")

    # ===== DELETE PROJECT =====
    @router.delete("/project/{project_id}")
    async def delete_project(project_id: str, user=Depends(get_current_user)):
        r = await db.freebuild_v2_projects.delete_one(
            {"id": project_id, "user_id": user["user_id"]}
        )
        if r.deleted_count == 0:
            raise HTTPException(404, "project not found")
        return {"ok": True}

    # ===== SERVE AI-GENERATED IMAGE FILE (public, no auth — iframes need this) =====
    @router.get("/img/{filename}")
    async def serve_image(filename: str):
        from pathlib import Path as _P
        # path-traversal guard
        if "/" in filename or "\\" in filename or ".." in filename:
            raise HTTPException(400, "invalid filename")
        if not filename.endswith(".png"):
            raise HTTPException(400, "only .png supported")
        fp = _P("/app/backend/static/fb2_images") / filename
        if not fp.exists() or not fp.is_file():
            raise HTTPException(404, "image not found")
        try:
            data = fp.read_bytes()
        except Exception:
            raise HTTPException(500, "read failed")
        return Response(
            content=data,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    # ===== REGENERATE ALL IMAGES IN A SESSION (different visual variant) =====
    @router.post("/regenerate-images")
    async def regenerate_images(payload: RegenImagesIn, user=Depends(get_current_user)):
        """Re-roll every image in the current session with a different style seed.
        This keeps the HTML structure but produces a fresh visual variant.
        Costs same as a normal turn update."""
        s = await db.freebuild_v2_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not s:
            raise HTTPException(404, "session not found")
        html = s.get("html") or ""
        if not html:
            raise HTTPException(400, "لا يوجد موقع في الجلسة")

        ok = await _deduct(user["user_id"], TURN_UPDATE_COST, "freebuild_v2_regen_imgs")
        if not ok:
            raise HTTPException(402, f"رصيدك ما يكفي ({TURN_UPDATE_COST} نقاط مطلوبة)")

        # First, restore @@IMG/<keyword>@@ placeholders by replacing existing
        # /api/freebuild/v2/img/* URLs back to plain alt-based contexts is not
        # needed — the post-processor reads alt+heading on every <img> tag, so
        # we just re-run with a new style seed to force a fresh hash → fresh PNG.
        try:
            from .image_gen import post_process_html_with_ai_images
            from .resources import resolve_image_for_keyword
            # Use a unique style seed per call so cache misses → genuine variants
            seed = (payload.style_seed or "").strip() or f"variant-{uuid.uuid4().hex[:8]}"
            new_html = await post_process_html_with_ai_images(
                html,
                style_seed=seed,
                fallback_resolver=resolve_image_for_keyword,
            )
            await db.freebuild_v2_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"html": new_html, "updated_at": _now()}}
            )
            return {
                "ok": True,
                "style_seed": seed,
                "credits_balance": await _credits(user["user_id"]),
            }
        except Exception as e:
            await db.users.update_one(
                {"id": user["user_id"]},
                {"$inc": {"credits": TURN_UPDATE_COST},
                 "$push": {"credit_history": {
                     "amount": TURN_UPDATE_COST,
                     "reason": f"refund_fb2_regen: {str(e)[:80]}",
                     "timestamp": _now(),
                 }}}
            )
            logger.exception(f"[FREEBUILD-V2] regen images failed: {e}")
            raise HTTPException(500, f"فشل التوليد. أعيدت النقاط. ({str(e)[:120]})")

    # ===== CONSTRAINTS CRUD (persistent user rules) =====
    @router.get("/constraints/{session_id}")
    async def list_constraints(session_id: str, user=Depends(get_current_user)):
        s = await db.freebuild_v2_sessions.find_one(
            {"id": session_id, "user_id": user["user_id"]},
            {"_id": 0, "constraints": 1},
        )
        if not s:
            raise HTTPException(404, "session not found")
        return {"constraints": s.get("constraints") or []}

    @router.post("/constraints/add")
    async def add_constraint(payload: ConstraintAddIn, user=Depends(get_current_user)):
        s = await db.freebuild_v2_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]},
            {"_id": 0, "constraints": 1},
        )
        if not s:
            raise HTTPException(404, "session not found")
        existing = s.get("constraints") or []
        new_c = {
            "id": f"m_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            "category": payload.category or "manual",
            "rule": payload.rule.strip(),
            "raw_text": payload.rule.strip(),
            "created_at": _now(),
        }
        existing.append(new_c)
        await db.freebuild_v2_sessions.update_one(
            {"id": payload.session_id},
            {"$set": {"constraints": existing, "updated_at": _now()}}
        )
        return {"ok": True, "constraint": new_c, "constraints": existing}

    @router.delete("/constraints/{session_id}/{constraint_id}")
    async def delete_constraint(session_id: str, constraint_id: str, user=Depends(get_current_user)):
        s = await db.freebuild_v2_sessions.find_one(
            {"id": session_id, "user_id": user["user_id"]},
            {"_id": 0, "constraints": 1},
        )
        if not s:
            raise HTTPException(404, "session not found")
        existing = [c for c in (s.get("constraints") or []) if c.get("id") != constraint_id]
        await db.freebuild_v2_sessions.update_one(
            {"id": session_id},
            {"$set": {"constraints": existing, "updated_at": _now()}}
        )
        return {"ok": True, "constraints": existing}

    # ===== NAVIGATION EDITOR (rename/delete/add/reorder tabs) =====
    @router.post("/edit-nav")
    async def edit_nav(payload: NavEditIn, user=Depends(get_current_user)):
        s = await db.freebuild_v2_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not s:
            raise HTTPException(404, "session not found")
        html = s.get("html") or ""
        if not html:
            raise HTTPException(400, "ما في موقع في الجلسة")

        action = (payload.action or "").lower()

        # ── Local-only mutations (rename/delete/reorder) — no LLM call ──
        if action == "rename":
            if not payload.route_id or not payload.new_label:
                raise HTTPException(400, "route_id + new_label مطلوبة")
            rid = payload.route_id.strip().lstrip("#/").strip()
            new_label = payload.new_label.strip()[:60]
            # Replace label inside any <a href="#/<rid>">…</a> in nav
            import re as _re
            pat = _re.compile(rf'(<a[^>]*href="#/{_re.escape(rid)}"[^>]*>)([^<]*)(</a>)', _re.IGNORECASE)
            html = pat.sub(rf'\1{new_label}\3', html)
            await db.freebuild_v2_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"html": html, "updated_at": _now()}}
            )
            return {"ok": True, "action": "rename", "credits_balance": await _credits(user["user_id"])}

        if action == "delete":
            if not payload.route_id:
                raise HTTPException(400, "route_id مطلوب")
            rid = payload.route_id.strip().lstrip("#/").strip()
            if rid == "home":
                raise HTTPException(400, "لا يمكن حذف الصفحة الرئيسية")
            import re as _re
            # Remove any <a> link in nav pointing to this route
            html = _re.sub(rf'<a[^>]*href="#/{_re.escape(rid)}"[^>]*>[^<]*</a>', "", html, flags=_re.IGNORECASE)
            # Remove the section page itself
            html = _re.sub(
                rf'<section[^>]*id="page-{_re.escape(rid)}"[^>]*>.*?</section>',
                "",
                html,
                flags=_re.IGNORECASE | _re.DOTALL,
            )
            await db.freebuild_v2_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"html": html, "updated_at": _now()}}
            )
            return {"ok": True, "action": "delete", "credits_balance": await _credits(user["user_id"])}

        if action == "reorder":
            if not payload.ordered_ids:
                raise HTTPException(400, "ordered_ids مطلوبة")
            import re as _re
            # Find the <nav class="nav-pills"> ... </nav> block (or the first <nav>)
            nav_match = _re.search(r"<nav[^>]*class=\"[^\"]*nav-pills[^\"]*\"[^>]*>(.*?)</nav>", html, _re.IGNORECASE | _re.DOTALL)
            if not nav_match:
                nav_match = _re.search(r"<nav[^>]*>(.*?)</nav>", html, _re.IGNORECASE | _re.DOTALL)
            if not nav_match:
                raise HTTPException(400, "ما لقيت navbar للتبديل")
            inner = nav_match.group(1)
            # Extract all <a href="#/..."> ... </a> with their labels
            link_re = _re.compile(r'<a[^>]*href="#/([^"]+)"[^>]*>([^<]*)</a>', _re.IGNORECASE)
            existing = {m.group(1).strip(): m.group(0) for m in link_re.finditer(inner)}
            # Build new inner in order, fall back to existing for missing ones
            new_inner_parts = [existing[r] for r in payload.ordered_ids if r in existing]
            # Append any remaining links not in ordered_ids
            for r, tag in existing.items():
                if r not in payload.ordered_ids:
                    new_inner_parts.append(tag)
            new_inner = "\n".join(new_inner_parts)
            new_nav = nav_match.group(0).replace(inner, new_inner)
            html = html.replace(nav_match.group(0), new_nav, 1)
            await db.freebuild_v2_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"html": html, "updated_at": _now()}}
            )
            return {"ok": True, "action": "reorder", "credits_balance": await _credits(user["user_id"])}

        if action == "add":
            label = (payload.new_label_for_add or "").strip()
            brief = (payload.new_brief or "").strip()
            if not label:
                raise HTTPException(400, "new_label_for_add مطلوب")
            ok = await _deduct(user["user_id"], TURN_UPDATE_COST, "freebuild_v2_add_nav")
            if not ok:
                raise HTTPException(402, f"رصيدك ما يكفي ({TURN_UPDATE_COST} نقاط مطلوبة)")
            try:
                # Ask the architect to add a new sub-page only — minimal, focused
                add_msgs = [
                    {"role": "system", "content": ARCHITECT_SYSTEM},
                    {"role": "system", "content": (
                        f"## CURRENT_HTML\n```html\n{html}\n```"
                    )},
                    {"role": "user", "content": (
                        f"أضف صفحة فرعية جديدة باسم '{label}' للموقع. "
                        f"المحتوى المطلوب: {brief or 'صمّم محتوى احترافي مناسب لهذا التبويب بناءً على نوع الموقع.'}\n"
                        f"التعليمات:\n"
                        f"1. أضف رابط للنafbar مع `<a href=\"#/{label}\" class=\"pill\">{label}</a>` "
                        f"(اختر معرّف لاتيني قصير معقول لو الاسم بالعربي).\n"
                        f"2. أضف `<section class=\"page\" id=\"page-XYZ\">` بمحتوى غني (hero + 3-5 أقسام).\n"
                        f"3. اربط هذه الصفحة بصفحات أخرى لو فيه ترابط منطقي.\n"
                        f"4. ارجع HTML كامل محدّث + رسالة قصيرة للمستخدم."
                    )},
                ]
                ai = await _openai_architect_turn(add_msgs)
                new_html = ai.get("html_update") or html
                await db.freebuild_v2_sessions.update_one(
                    {"id": payload.session_id},
                    {"$set": {"html": new_html, "updated_at": _now(),
                              "credits_spent": s.get("credits_spent", 0) + TURN_UPDATE_COST}}
                )
                return {
                    "ok": True,
                    "action": "add",
                    "ai_message": ai.get("message_to_user"),
                    "credits_balance": await _credits(user["user_id"]),
                }
            except Exception as e:
                # refund
                await db.users.update_one(
                    {"id": user["user_id"]},
                    {"$inc": {"credits": TURN_UPDATE_COST},
                     "$push": {"credit_history": {
                         "amount": TURN_UPDATE_COST,
                         "reason": f"refund_fb2_addnav: {str(e)[:80]}",
                         "timestamp": _now(),
                     }}}
                )
                logger.exception(f"[FREEBUILD-V2] add nav failed: {e}")
                raise HTTPException(500, f"فشل إضافة التبويب. أعيدت النقاط. ({str(e)[:120]})")

        raise HTTPException(400, f"action غير معروف: {action}")

    # ===== EXTRACT NAV STRUCTURE (for the editor UI to populate) =====
    @router.get("/nav/{session_id}")
    async def get_nav(session_id: str, user=Depends(get_current_user)):
        s = await db.freebuild_v2_sessions.find_one(
            {"id": session_id, "user_id": user["user_id"]}, {"_id": 0, "html": 1}
        )
        if not s:
            raise HTTPException(404, "session not found")
        html = s.get("html") or ""
        if not html:
            return {"links": []}
        import re as _re
        nav_match = _re.search(r"<nav[^>]*class=\"[^\"]*nav-pills[^\"]*\"[^>]*>(.*?)</nav>", html, _re.IGNORECASE | _re.DOTALL)
        if not nav_match:
            nav_match = _re.search(r"<nav[^>]*>(.*?)</nav>", html, _re.IGNORECASE | _re.DOTALL)
        inner = nav_match.group(1) if nav_match else ""
        link_re = _re.compile(r'<a[^>]*href="#/([^"]+)"[^>]*>([^<]*)</a>', _re.IGNORECASE)
        links = [{"id": m.group(1).strip(), "label": m.group(2).strip()} for m in link_re.finditer(inner)]
        return {"links": links}

    return router


def _empty_preview_html() -> str:
    """Friendly empty-state HTML shown while the AI hasn't built yet."""
    return """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>الموقع يُبنى الآن</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI','Tahoma',sans-serif;background:#0a0a14;color:#fff;
       height:100vh;display:flex;align-items:center;justify-content:center;overflow:hidden;
       background-image:
         radial-gradient(circle at 20% 30%, rgba(245,158,11,0.15) 0%, transparent 40%),
         radial-gradient(circle at 80% 70%, rgba(217,119,6,0.12) 0%, transparent 40%)}
  .box{text-align:center;padding:48px;max-width:540px}
  h1{font-size:clamp(28px,5vw,44px);font-weight:900;margin-bottom:16px;
     background:linear-gradient(135deg,#fbbf24,#f59e0b);-webkit-background-clip:text;color:transparent}
  p{color:rgba(255,255,255,0.65);font-size:17px;line-height:1.7;margin-bottom:28px}
  .pulse{display:inline-block;width:12px;height:12px;border-radius:50%;
         background:#fbbf24;animation:pulse 1.6s infinite;margin:0 4px}
  .pulse:nth-child(2){animation-delay:0.2s}
  .pulse:nth-child(3){animation-delay:0.4s}
  @keyframes pulse{0%,100%{opacity:0.3;transform:scale(0.8)}50%{opacity:1;transform:scale(1.2)}}
</style>
</head>
<body>
  <div class="box">
    <h1>ابدأ المحادثة مع المهندس الذكي</h1>
    <p>اكتب فكرة موقعك في الشات على اليسار — وبتشوف الموقع يتبنى هنا لحظة بلحظة.</p>
    <div><span class="pulse"></span><span class="pulse"></span><span class="pulse"></span></div>
  </div>
</body>
</html>"""
