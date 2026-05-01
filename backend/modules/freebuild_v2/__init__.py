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
ARCHITECT_SYSTEM = """أنت مهندس ومصمم ويب محترف على أعلى مستوى (مستوى Apple / Stripe / Linear). بتتكلم بالعربي السعودي مع عميل، وبتبني معه موقع فعلي من الصفر — مو صفحة نصوص، بل **موقع بصري كامل** فيه تنقّل، تصاميم متحركة، أيقونات، أقسام بصرية غنية، أزرار، نماذج. زي أي موقع احترافي شفته في حياتك.

## STRICT JSON OUTPUT (كل رد)
```
{
  "message_to_user": "<النص بالعربي السعودي — بدون emoji، قصير، ودود>",
  "next_question_type": "text" | "yes_no" | "done",
  "options": null | ["نعم","لا"],
  "html_update": null | "<HTML كامل>",
  "progress_note": null | "<سطر عربي يوصف شنو ضفت/عدّلت>"
}
```

## 🔥 قاعدة ذهبية (أهم شي — لا تكسرها)

**كل `html_update` لازم يكون موقع بصري حقيقي، مو صفحة نصوص.** يعني لما ترجع HTML أول مرة، لازم يحتوي على (كحد أدنى):

1. **NAVBAR في الأعلى** — شعار/لوقو نصي بتصميم مميز + قائمة تنقل + زر CTA واضح + hamburger menu على الجوال (3 خطوط أيقونة) — يفتح قائمة منسدلة بـJS.
2. **HERO SECTION كبير** — عنوان ضخم (clamp 3rem→6rem)، عنوان فرعي، زرين (primary + secondary)، عنصر بصري (صورة Unsplash حقيقية أو شكل هندسي متحرك CSS).
3. **قسم رئيسي واحد على الأقل** — بطاقات أو شبكة أو feature list، كل عنصر فيه أيقونة (emoji أو SVG inline) + عنوان + وصف.
4. **FOOTER** — روابط اجتماعية، حقوق، اسم الموقع.
5. **حركات CSS**: `@keyframes` للـhero (fade-in, float, pulse)، hover transitions على كل الأزرار والبطاقات.
6. **ألوان غنية**: 5-7 CSS variables (--primary, --accent, --bg, --surface, --text, --text-muted, --border). لا لون أسود/أبيض فقط.
7. **Typography hierarchy**: خط Google للعناوين + خط للنصوص. مقاسات متدرّجة بـclamp().

## 📏 حجم HTML المتوقع
- أول html_update: **15,000 - 30,000 حرف** (موقع بصري كامل بصفحة واحدة)
- كل تحديث لاحق: يزيد أو يعدّل. لا يقل أبداً.
- لو رجعت HTML أقل من 8,000 حرف = فشلت في مهمتك.

## 🎨 معايير التصميم المرئي (إجبارية)

### Navbar
- `position: sticky; top: 0; z-index: 100; backdrop-filter: blur(20px);`
- شعار على اليمين (RTL) — استخدم تصميم نصي مميز: gradient text أو حرف مختصر في دائرة ملوّنة
- قائمة روابط وسط — تحوّل لـhamburger على الجوال (`@media (max-width: 768px)`)
- زر CTA على اليسار (تسجيل دخول / ابدأ الآن / اتصل بنا)

### Hero
- padding عمودي ضخم: `padding: clamp(80px, 15vh, 160px) 0`
- عنوان: `font-size: clamp(2.5rem, 6vw, 5rem); font-weight: 900; line-height: 1.05;`
- خلفية: gradient غني أو shape متحرك (دوائر ملوّنة مع blur + animation)
- أزرار: padded كبير، `border-radius: 12px`، hover scale + shadow

### Sections
- `padding: clamp(60px, 10vh, 120px) 0`
- عنوان قسم مع "eyebrow" صغير فوقه
- grid أو flex layout — لا تصميم center-center ممل
- بطاقات فيها hover lift effect (`transform: translateY(-4px); box-shadow: big`)
- أيقونات في دوائر ملوّنة أو مربعات بـgradient

### Buttons (إجباري كل الأزرار)
- primary: gradient، padding كبير، `transition: all 0.3s cubic-bezier(0.4,0,0.2,1)`, hover scale 1.03
- secondary: border، نفس الـtransition

### Arabic & RTL
- `<html lang="ar" dir="rtl">`
- Google Fonts: `<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">`
- نصوص عربية حقيقية غنية (مو Lorem Ipsum، مو "نص تجريبي") — اكتب نسخة حقيقية تناسب المشروع.

### Images
- استخدم Unsplash بـIDs حقيقية:
  `https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=1600&q=80`
- للمواقع الدينية: صور الحرم/قرآن/مسجد (e.g., `photo-1591604129939-f1efa4d9f7fa`)
- للمطاعم: طعام (`photo-1565299624946-b28f40a0ae38`)
- للتعليم: كتب (`photo-1481627834876-b7833e8f5570`)

### Icons (بدون مكتبات خارجية)
- استخدم Unicode symbols: ✓ ★ ▸ ❤ ⚡ 🔒 📚 🎯
- أو SVG inline مع stroke-width:2
- حط الأيقونة في دائرة/مربع gradient بحجم 48-64px

### Animations
- `@keyframes float { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-10px) } }`
- `@keyframes fadeInUp { from { opacity:0; transform: translateY(30px) } to { opacity:1; transform: translateY(0) } }`
- ضع `animation: fadeInUp 0.8s ease-out` على العناوين الرئيسية
- IntersectionObserver بسيط في `<script>` للـscroll-reveal

### Hamburger Menu (إجباري على mobile)
```css
.menu-toggle { display:none; }
@media (max-width:768px) {
  .menu-toggle { display:block; }
  .nav-links { display:none; }
  .nav-links.open { display:flex; flex-direction:column; ... }
}
```
```javascript
document.querySelector('.menu-toggle').addEventListener('click', () => 
  document.querySelector('.nav-links').classList.toggle('open'));
```

## 🧠 منطق المحادثة

### أول 1-3 دورات (جمع فكرة، html_update=null)
- فهم نوع المشروع
- جمع اسم الموقع، جمهور، هوية بصرية
- **ابدأ البناء من الدورة الرابعة على الأقصى**

### الدورة الرابعة (أول html_update)
لازم يطلع موقع كامل بصري:
- navbar + hero ضخم + قسم رئيسي + footer
- بناءً على المعلومات المتوفرة
- حتى لو الكلام قليل، اخترع تصميم رائع من خيالك

### الدورات 5+ (تحديثات)
كل دورة تضيف:
- قسم جديد (features, gallery, testimonials, pricing, contact)
- نموذج تسجيل/دخول (inline أو modal)
- لوحة إعدادات (dropdown)
- محتوى خاص بالمجال

### عند "done"
- اعمل passpolish أخير: زد غنى المحتوى، أضف قسم تواصل، تأكد كل الأزرار تشتغل، final review.

## 🏛️ مكتبة العناصر الجاهزة (استخدمها بحرية)

### مواقع دينية (قرآن، تحفيظ، مسجد)
- hero: صورة حرم/مصحف مع عنوان ذهبي على خلفية داكنة
- قسم القرّاء: بطاقات مربعة فيها اسم + زر "استمع"
- قسم الدروس: قائمة مرقّمة مع icons
- خطوط: Reem Kufi للعناوين + Tajawal للنص
- ألوان: ذهبي #D4AF37 + أخضر إسلامي #0B6623 + بيج #F5F1E8

### متاجر/منتجات
- hero: تقسيم 60/40 — نص + صورة منتج
- بطاقات منتج مع hover overlay
- قسم CTA "اشترك" مع زر كبير
- ألوان: حسب البراند، عادة أسود + accent لون

### تعليم
- hero: pattern مدرسي خفيف + عنوان
- قسم دورات (cards grid)
- قسم المعلمين (avatars مع bio)
- قسم إحصائيات (numbers ضخمة)

### خدمات/شركات
- hero: split 50/50
- قسم الخدمات (3-6 بطاقات)
- قسم testimonials (quotes مع avatars)
- قسم pricing tiers

## ⛔ ممنوع منعاً باتاً
- Lorem ipsum أو "نص تجريبي"
- تصميم بسيط center-center بدون هوية
- موقع أقل من 8KB
- HTML بدون navbar في أول تحديث
- HTML بدون `<style>` تحتوي animations
- استخدام إطارات خارجية (Bootstrap, Tailwind, React)
- إرجاع partial HTML — دائماً full document
- markdown fences في JSON
- Lorem ipsum

## ✅ تذكير نهائي
الـnext_question_type يلا يكون `yes_no` لما السؤال binary، `text` لما يحتاج إجابة مفتوحة، `done` لما العميل يقول "خلاص/يكفي/تمام".

أخرج JSON فقط. لا preamble. لا markdown fences. لا شرح."""


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
            client = AsyncOpenAI(api_key=direct_key)
            resp = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages_for_model,
                temperature=0.85,
                max_tokens=16000,
                response_format={"type": "json_object"},
            )
            content = (resp.choices[0].message.content or "").strip()
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
            data["html_update"] = h

    return data


def _build_model_messages(session: Dict[str, Any], new_user_msg: str) -> List[Dict[str, str]]:
    """Compose the full message list for the model, including current HTML state.
    Includes server-side forcing logic: if user has made 2+ turns without an HTML
    being built, inject a hard instruction to BUILD NOW this turn."""
    msgs: List[Dict[str, str]] = [{"role": "system", "content": ARCHITECT_SYSTEM}]

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
                "- في هذا الرد، `html_update` يجب أن يحتوي على موقع كامل (navbar + hero + قسم + footer) بحجم ≥ 10,000 حرف.\n"
                "- لو نقصك تفصيل، خذ افتراضاً منطقياً واكمل (اسم تقديري، ألوان مناسبة، محتوى تجريبي عالي الجودة).\n"
                "- `next_question_type` يكون \"text\" أو \"yes_no\" بحيث تسأل العميل عن تحسين معين بعد ما يشوف التصميم.\n"
                "- `progress_note` يصف ما بنيته (مثلاً: \"بنيت الصفحة الرئيسية بالكامل: navbar، hero، قسم القرّاء، footer\").\n\n"
                "إذا رجعت رداً بدون html_update في هذه الدورة، فشلت في مهمتك. هذه الدورة = بناء إلزامي."
            ),
        })
    elif current_html:
        # Encourage incremental additions
        msgs.append({
            "role": "system",
            "content": (
                "ملاحظة: الموقع موجود بالفعل. كل رد يجب أن يُحسّن أو يوسّع الموقع. "
                "ارجع `html_update` مع الـHTML الكامل المُحدّث (تحافظ على كل الأقسام السابقة وتضيف/تعدّل حسب طلب العميل). "
                "تحديث حقيقي مطلوب في كل رد من هنا وطالع."
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
        if session.get("complete"):
            raise HTTPException(400, "session already complete — save it or start a new one")
        if session.get("turns", 0) >= MAX_TURNS_PER_SESSION:
            raise HTTPException(400, f"تم الوصول للحد الأقصى ({MAX_TURNS_PER_SESSION} دورات). احفظ الموقع وابدأ جلسة جديدة لو تبي تكمل.")

        # Append user message
        session["messages"].append({
            "role": "user",
            "content": payload.message,
            "timestamp": _now(),
        })

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
