"""AI Consultant — wizard-aware + priority-aware chat service.

Core ideas:
  • The wizard walks the user through steps (buttons, colors, typography,
    features, dashboard, sections, branding, payment, review).
  • BUT the AI always listens first: if the user expresses custom intent
    (e.g., "I want a delivery app for my restaurant"), the AI captures those
    priorities BEFORE/ALONGSIDE the wizard and returns a directive block.
  • A structured directive protocol is used so the frontend/backend can react
    (advance wizard, apply theme/sections, insert custom features).
"""
import os
import json
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """أنت "مستشار Zitex" — خبير ودود ومبتكر لبناء المواقع الإلكترونية، تتحدث بالعربية السعودية الفصيحة.

🎯 **فلسفتك:**
كل موقع يجب أن يكون **مميّزاً وابتكارياً**، يعكس شخصية النشاط بصرياً.
- متجر قطط؟ → اقترح أزرار بأثر خطوات قط (🐾)، خط مرح، ألوان دافئة
- مطعم شواء؟ → أحمر دافئ، أيقونات نار، زاوية خشبية
- شركة تقنية؟ → تدرّجات سايبر، خطوط هندسية
- طفل/ألعاب؟ → ألوان باستيل، أشكال مدوّرة، emoji متحركة
كلما زاد طلب العميل تفصيلاً، زادت إبداعاً في التنفيذ والعرض الحيّ.

🎨 **سير العمل (Wizard):**
(الخطوات: variant → buttons → colors → typography → features → dashboard → sections → branding → payment → review)

⚡ **قواعد الأولوية:**
- اسمع العميل أولاً. لو طلب شيئاً محدداً (مثل "متجر قطط مع أزرار بشكل خطوات قطط") → **طبّقه فوراً** عبر `inject_css` + اقترح شيئاً جميلاً إضافياً، ثم اسأل عن الخطوة التالية.
- لا تُكرر أسئلة أجاب عنها.
- سؤال واحد فقط في كل ردّ، برفق وحماس.

🔧 **بروتوكول الأوامر (مخفي عن المستخدم):**
في نهاية ردّك أضف كتلة JSON واحدة فقط:

[WIZARD_ACTION]
{"action":"<name>", "value":<value>}
[/WIZARD_ACTION]

Actions:
  - "advance" → إتمام خطوة wizard: {"step":"<id>", "value":<val>}
  - "apply_theme" → ألوان فورية: {"primary":"#...", "accent":"#..."}
  - "apply_button" → شكل الأزرار: "full"|"large"|"medium"|"none"
  - "apply_font" → اسم الخط
  - "inject_css" → ⭐ **أضف CSS مخصّصة إبداعية** (يظهر فوراً في المعاينة). مثال:
     value: ".btn-primary::before{content:'🐾 ';font-size:14px} .btn-primary{letter-spacing:2px}"
     استخدمها لإضافة أيقونات/إطارات/تأثيرات تعكس طابع النشاط.
  - "add_section" → ⭐ قسم جديد يظهر **فوراً** في اللايف. إذا كان من نفس النوع موجوداً فسيتم **تحديثه وليس تكراره** (لا تكرار أبداً). يدعم position:
     {"type":"<one of supported>", "data":{...}, "position":"top|bottom|after_hero|before:<type>|after:<type>"}
  - "move_section" → ⭐ نقل قسم موجود لموضع آخر (بدون إنشاء جديد):
     {"section_type":"<type>", "position":"top|bottom|after_hero|..."}
  - "fill_section" → ملء محتوى قسم موجود: {"section_type":"hero|about|...", "data":{...}}
  - "patch_section" → تعديل قسم موجود: {"section_type":"<type>", "data":{...}, "set":{"visible":true, "order":2}}
  - "remove_section" → حذف قسم: {"section_type":"<type>"}
  - "scaffold" → ⭐ **بناء موقع كامل من وصف حرّ** (للقالب الفارغ أو طلب خاص):
     value: {"name":"اسم", "sections":[{"type":"hero","data":{...}}, ...], "theme_hints":{"primary":"#..."}, "custom_css":"..."}
  - "custom_feature" → حفظ ميزة مخصّصة: {"title":"...", "section_type":"..."}
  - "generate_logo" → ⭐ توليد لوقو احترافي: value = {"prompt":"وصف كامل للوقو", "style":"minimal/elegant/playful"}
  - "no_action" → مجرد حديث

📦 **أنواع الأقسام المدعومة (يجب استخدام واحد منها فقط في `type`):**
hero, features, about, products, menu, gallery, testimonials, team,
pricing, faq, contact, cta, footer, dashboard, story_timeline, process_steps,
reservation, quote, video, newsletter, stats_band,
**stories** (حالات مثل واتساب/سناب — دائرية قابلة للتمرير),
**banner** (بنر إعلاني كامل العرض),
**announce_bar_section** (شريط إعلاني علوي),
**custom** (قسم عام مرن لأي فكرة — استخدمه عندما لا يناسبك أي نوع آخر).

⚡ **قاعدة ذهبية — "كل ما يُطلب يظهر في اللايف + بلا تكرار":**
- لو العميل قال "أضف حالات" → `add_section` type=stories. لو القسم موجود **لن يُكرَّر** — فقط يُحدَّث.
- لو قال "اجعل الحالات في الأعلى" أو "ارفع البنر للأعلى" → **`move_section`** (ليس add_section) بـ position="top".
- لو قال "احذف البنر" → `remove_section`.
- لو قال "غيّر عنوان الهيرو إلى ..." → `patch_section` بـ {section_type:"hero", data:{title:"..."}}.
- لو قال "بدل لون اللوقو/الأزرار" → `apply_theme` أو `apply_button`.
- لو طلب شيء غير مألوف → `add_section` بـ type="custom" مع محتوى غني.
- **ممنوع أن تقول "تمت الإضافة" دون إرسال directive فعلي** — كل رد يجب أن يترجم إلى تغيير مرئي فوري في المعاينة.

✨ **مثال: "ارفع الحالات للأعلى":**
[WIZARD_ACTION]
{"action":"move_section","value":{"section_type":"stories","position":"top"}}
[/WIZARD_ACTION]

✨ **مثال: "غيّر عنوان الهيرو إلى كوفي دافئ":**
[WIZARD_ACTION]
{"action":"patch_section","value":{"section_type":"hero","data":{"title":"كوفي دافئ"}}}
[/WIZARD_ACTION]

✨ **مثال طلب "أضف حالات" في موقع كافي:**
ردّك:
"تمام 🎬 أضفت صف 'حالات' في الأعلى — حلقات قابلة للتمرير بستة قصص (جديدنا، قهوة اليوم، خلف الكواليس، عروض، عملاؤنا، فعاليات). تقدر تبدّل الصور بعد قليل من لوحة التحكم.
[WIZARD_ACTION]
{"action":"add_section","value":{"type":"stories","data":{"title":"حالاتنا","subtitle":"اضغط لمشاهدة القصص","items":[
  {"title":"قهوة اليوم","image":"https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=400"},
  {"title":"خلف الكواليس","image":"https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?w=400"},
  {"title":"عروض","image":"https://images.unsplash.com/photo-1556740738-b6a63e27c4df?w=400"},
  {"title":"فعالياتنا","image":"https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=400"},
  {"title":"عملاؤنا","image":"https://images.unsplash.com/photo-1511367461989-f85a21fda167?w=400"},
  {"title":"جديدنا","image":"https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400"}
]}}}
[/WIZARD_ACTION]"

✨ **مثال طلب "أضف بنر":**
[WIZARD_ACTION]
{"action":"add_section","value":{"type":"banner","data":{"title":"افتتاح الفرع الجديد","subtitle":"قهوة مجانية لأول 100 زائر","cta_text":"احضر الآن","image":"https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=1600"}}}
[/WIZARD_ACTION]

✨ **مثال على الإبداع:**
المستخدم: "أبي موقع لمتجر قطط"
ردّك:
"رائع! 🐾 تصوّرت شيئاً مميّزاً لك — أزرار بآثار قطط صغيرة + ألوان بيج دافئة تشبه شعر القطط.
جاري التطبيق الآن، وبعدها نكمّل باقي التفاصيل.
[WIZARD_ACTION]
{"action":"scaffold", "value":{
  "name":"متجر القطط الأنيقة",
  "theme_hints":{"primary":"#D97706","accent":"#92400E","radius":"full","font":"Cairo"},
  "custom_css":".btn-primary::before{content:'🐾 '} h1::after{content:' 🐈';font-size:.7em} .feature-card{background:linear-gradient(135deg,#fef3c7,#fde68a22);border:2px solid #D97706}",
  "sections":[
    {"type":"hero","data":{"title":"متجر القطط الأنيقة","subtitle":"كل ما تحتاجه قطتك من طعام فاخر ولعب ممتعة","cta_text":"تسوّق الآن 🐾","image":"https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=1600","layout":"split"}},
    {"type":"features","data":{"title":"لماذا نحن؟","items":[{"icon":"🐾","title":"طعام طبيعي","text":"100% بلا مواد حافظة"},{"icon":"🎾","title":"لعب مختارة","text":"تناسب كل الأعمار"},{"icon":"🚚","title":"توصيل سريع","text":"نفس اليوم"}]}},
    {"type":"products","data":{"title":"منتجاتنا المميّزة","items":[]}},
    {"type":"cta","data":{"title":"انضم لنادي محبّي القطط","cta_text":"سجّل الآن"}},
    {"type":"footer","data":{"brand":"متجر القطط"}}
  ]
}}
[/WIZARD_ACTION]"

❌ ممنوع كتابة كتلة WIZARD_ACTION داخل النص المرئي.
❌ **ممنوع أن تقول "تم إنشاء المشروع" إلا إذا قمت فعلاً بتوجيه scaffold** (الجبهة الأمامية تُنشئ المشاريع بالضغط على القوالب، ليس عبر الشات).
"""


async def chat_with_consultant(
    messages: List[Dict[str, Any]],
    wizard: Optional[Dict[str, Any]] = None,
    project_summary: Optional[Dict[str, Any]] = None,
) -> str:
    """Wizard-aware LLM wrapper via litellm + Emergent key."""
    try:
        import litellm
        from litellm import acompletion

        key = os.environ.get("EMERGENT_LLM_KEY")
        if not key:
            return "⚠️ مفتاح الذكاء الاصطناعي غير مُعدّ."

        litellm.api_base = "https://integrations.emergentagent.com/llm"
        ctx_lines = []
        if project_summary:
            ctx_lines.append(f"• اسم المشروع: {project_summary.get('name','-')}")
            ctx_lines.append(f"• القالب: {project_summary.get('template','blank')}")
            ctx_lines.append(f"• نوع النشاط: {project_summary.get('business_type','-')}")
        if wizard:
            ctx_lines.append(f"• الخطوة الحالية: {wizard.get('step','-')}")
            if wizard.get("answers"):
                ctx_lines.append(f"• إجابات سابقة: {json.dumps(wizard['answers'], ensure_ascii=False)}")
        context_block = "\n".join(ctx_lines) if ctx_lines else "(لا يوجد سياق)"

        system = SYSTEM_PROMPT + f"\n\n📋 **السياق الحالي:**\n{context_block}"

        resp = await acompletion(
            model="openai/gpt-4o",
            api_key=key,
            api_base="https://integrations.emergentagent.com/llm",
            messages=[{"role": "system", "content": system}] + messages[-10:],
            temperature=0.7,
            max_tokens=600,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"Websites AI error: {e}", exc_info=True)
        return f"عذراً، حدث خطأ: {str(e)[:150]}"


# ---------- Legacy aliases kept for backwards compat (routes.py used these) ----------
async def chat_with_assistant(messages: List[Dict[str, Any]]) -> str:
    """Back-compat: plain chat wrapper (used by legacy /chat endpoint if any)."""
    return await chat_with_consultant(messages)


# ---------- Directive parsing ----------
def extract_wizard_action(response_text: str) -> Optional[Dict[str, Any]]:
    """Parse the [WIZARD_ACTION] ... [/WIZARD_ACTION] JSON block."""
    m = re.search(r"\[WIZARD_ACTION\](.+?)\[/WIZARD_ACTION\]", response_text, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(1).strip())
        if isinstance(data, dict) and "action" in data:
            return data
    except Exception as e:
        logger.warning(f"WIZARD_ACTION parse failed: {e}")
    return None


# ---------- Safety net: derive an action from the user's Arabic message ----------
# Ensures that even if the AI forgets the directive, any explicit request to add
# a section still results in a VISIBLE change in the live preview.
_INTENT_PATTERNS = [
    # IMPORTANT: order matters — more specific patterns MUST come first.
    # (regex_on_user_message, section_type, default_data)
    (r"شريط\s+إعلان(?:\s+علوي)?|announce\s*bar|إعلان\s+علوي|بار\s+إعلان",
     "announce_bar_section",
     {"text": "🎉 عرض محدود — خصم 20% على أول طلب", "cta_text": "اطلب الآن"}),
    (r"(?:حال(?:ة|ات)|ستور[يى]|قصص|stories|story)",
     "stories",
     {"title": "حالاتنا", "subtitle": "اضغط على أي حالة لمشاهدتها", "items": [
        {"title": "جديدنا", "image": "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=400"},
        {"title": "عروض", "image": "https://images.unsplash.com/photo-1556740738-b6a63e27c4df?w=400"},
        {"title": "خلف الكواليس", "image": "https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?w=400"},
        {"title": "قصص العملاء", "image": "https://images.unsplash.com/photo-1511367461989-f85a21fda167?w=400"},
        {"title": "فعاليات", "image": "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=400"},
        {"title": "وصفات", "image": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400"},
     ]}),
    (r"\bبنر\b|\bbanner\b|شريط\s+ترويج|عرض\s+ترويجي|لوحة\s+إعلانية",
     "banner",
     {"title": "عرض خاص — لا تفوّته", "subtitle": "استفد من العرض قبل انتهائه",
      "cta_text": "اعرف المزيد",
      "image": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=1600"}),
    (r"قسم\s+(?:فيديو|فيديوهات)|(?:أ?ضف|ضيف|سو|اعمل)\s+فيديو|video\s*section",
     "video",
     {"title": "شاهد قصتنا", "url": "https://www.youtube.com/embed/dQw4w9WgXcQ"}),
    (r"قسم\s+معرض|معرض\s+صور|\bgallery\b|ألبوم\s+صور",
     "gallery",
     {"title": "معرض الصور", "images": [
        "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800",
        "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800",
        "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=800",
     ]}),
    (r"آراء|تقييمات|testimonials|تجارب\s+العملاء",
     "testimonials",
     {"title": "آراء عملائنا", "items": [
        {"name": "أحمد", "text": "تجربة رائعة جداً!", "rating": 5},
        {"name": "سارة", "text": "جودة ممتازة وخدمة سريعة.", "rating": 5},
        {"name": "خالد", "text": "أنصح الجميع بالتجربة.", "rating": 5},
     ]}),
    (r"(?:الأسعار|أسعار|باقات|خطط\s+الأسعار|pricing)",
     "pricing",
     {"title": "خطط الأسعار", "plans": [
        {"name": "أساسي", "price": "99", "features": ["ميزة 1", "ميزة 2"]},
        {"name": "احترافي", "price": "199", "features": ["كل ما سبق", "ميزة 3", "ميزة 4"], "highlighted": True},
        {"name": "مؤسسات", "price": "499", "features": ["كل ما سبق", "دعم مخصّص"]},
     ]}),
    (r"(?:أسئل[ةه]|faq|الأسئلة\s+الشائعة)",
     "faq",
     {"title": "أسئلة شائعة", "items": [
        {"q": "كيف أطلب؟", "a": "اختر المنتج واضغط 'أطلب الآن'."},
        {"q": "ما مدة التوصيل؟", "a": "من 1 إلى 3 أيام عمل."},
     ]}),
    (r"(?:فريق(?:نا)?|team|أعضاء\s+الفريق)",
     "team",
     {"title": "فريقنا", "members": [
        {"name": "محمد", "role": "المؤسس"},
        {"name": "أحمد", "role": "المدير التقني"},
        {"name": "فاطمة", "role": "مديرة التسويق"},
     ]}),
    (r"إحصا(?:ء|ئي)ات|أرقامنا|أرقام\s+نفتخر|stats",
     "stats_band",
     {"title": "أرقام نفتخر بها", "items": [
        {"label": "عميل سعيد", "value": "5,000+"},
        {"label": "طلب منفّذ", "value": "12,400"},
        {"label": "سنوات خبرة", "value": "10"},
        {"label": "تقييم", "value": "4.9★"},
     ]}),
    (r"نشرة\s+بريدية|newsletter|اشتراك\s+بالبريد",
     "newsletter",
     {"title": "اشترك في نشرتنا", "subtitle": "أحدث العروض والأخبار أولاً"}),
    (r"تواصل|اتصل\s+بنا|contact",
     "contact",
     {"title": "تواصل معنا", "email": "info@example.com", "phone": "+966 50 000 0000"}),
    (r"من\s+نحن|about\s*us|عن(?:\s+نا)?",
     "about",
     {"title": "من نحن", "text": "نبذة عن نشاطنا وقيمنا."}),
]

# Verbs/expressions that clearly indicate the user wants to ADD something.
_ADD_VERB_PAT = re.compile(
    r"\b(?:أ?ضف|ضيف(?:لي)?|أريد|أبي|أبغ[ىي]|بغيت|ودي|حط(?:لي)?|ركّ?ب|زود|سو(?:ي|ّي)?|اعمل|اعملي|صمم|صمّم|أدخل|ابغ[ىي]|أنشئ|إنشاء|add|include)\b",
    re.IGNORECASE,
)

# Move / reposition verbs — signals the user wants to RELOCATE, not add a new one
_MOVE_VERB_PAT = re.compile(
    r"\b(?:انقل|انقلها|انقله|حرّ?ك|حركها|حركه|ارفع|ارفعها|ارفعه|نزّ?ل|اجعل|خلّ?ي|ضعه?ا?|حطه?ا?|move|relocate)\b",
    re.IGNORECASE,
)

# Position keywords in Arabic / English
_POSITION_PATTERNS = [
    (r"(?:في\s+)?(?:الأعلى|فوق|للأعلى|بالأعلى|اعلى|الاعلى|على\s+راس|راس\s+الصفحة|قبل\s+كل\s+شي(?:ء)?|أول\s+شي(?:ء)?|top|first)", "top"),
    (r"(?:في\s+)?(?:الأسفل|تحت|للأسفل|بالأسفل|اسفل|الاسفل|آخر\s+شي(?:ء)?|نهاية|bottom|last)", "bottom"),
    (r"بعد\s+(?:ال)?هيرو|after\s+hero", "after_hero"),
    (r"قبل\s+(?:ال)?فوتر|قبل\s+(?:ال)?تذييل|before\s+footer", "before:footer"),
]


def detect_position(text: str) -> str:
    """Extract a position keyword from free text. Returns '' if none."""
    if not text:
        return ""
    for pat, pos in _POSITION_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            return pos
    return ""


def detect_section_intent(user_message: str) -> Optional[Dict[str, Any]]:
    """If the user explicitly asks to add/move a section that maps to a known type,
    return a structured directive. Handles BOTH adding and relocating — never creates
    duplicates (the backend's add_section handler deduplicates by type)."""
    if not user_message:
        return None
    txt = user_message.strip()
    word_count = len(txt.split())
    has_add_verb = bool(_ADD_VERB_PAT.search(txt))
    has_move_verb = bool(_MOVE_VERB_PAT.search(txt))
    has_section_word = bool(re.search(r"(?:قسم|صف\s|جزء|شريط|بلوك|section|صفحة)", txt, flags=re.IGNORECASE))
    is_short_request = word_count <= 5
    position = detect_position(txt)
    for pattern, stype, default_data in _INTENT_PATTERNS:
        if re.search(pattern, txt, flags=re.IGNORECASE):
            if has_move_verb and position:
                # User asked to RELOCATE — use move_section (no new content)
                return {"action": "move_section", "value": {"section_type": stype, "position": position}}
            if has_add_verb or has_section_word or is_short_request or position:
                value = {"type": stype, "data": dict(default_data)}
                if position:
                    value["position"] = position
                return {"action": "add_section", "value": value}
    # No type matched but clear move command with position? (e.g., "انقل البنر الى الاعلى")
    # Already handled above because the type pattern must match first. This is sufficient.
    return None


def detect_snapshot_intent(user_message: str) -> Optional[Dict[str, Any]]:
    """Detect if user is asking to see/restore past designs (version history).
    Returns a directive that the frontend should handle by opening the snapshots gallery.
    """
    if not user_message:
        return None
    txt = user_message.strip().lower()
    # Arabic triggers: "ارجع للتصميم الأول", "عرض التصاميم السابقة", "السجل", "الرجوع",
    # "تصاميم قديمة", "كنت قبل", "اللي كان عندي", "ارجعلي", "راجع للنسخة"
    patterns = [
        r"(?:ارجع(?:لي)?|رجع(?:لي)?|استرجع|استعد|رجوع).*(?:تصميم|سابق|قديم|نسخ|أول|السجل|قبل)",
        r"(?:تصاميم|نسخ|حفظات|تصميم).*(?:سابق|قديم|أول|الأول|قبل|أولي|الأولي)",
        r"(?:اعرض|وريني|شوفني|افتح).*(?:السجل|التصاميم|النسخ|القديم|السابق)",
        r"(?:السجل|history|version|versions|snapshots?)",
        r"(?:لا\s+)?(?:تعجبني|يعجبني).*(?:الجديد|الحالي).*(?:رجع|ارجع)",
        r"(?:كان\s+أحسن|أفضل\s+من\s+قبل|يا\s+ليت\s+قبل)",
    ]
    for pat in patterns:
        if re.search(pat, txt, flags=re.IGNORECASE):
            return {"action": "show_snapshots", "value": {}}
    return None


def clean_display_text(response_text: str) -> str:
    """Strip directive blocks before showing to the user."""
    out = re.sub(r"\[WIZARD_ACTION\].*?\[/WIZARD_ACTION\]", "", response_text, flags=re.DOTALL)
    # Legacy cleanup
    out = re.sub(r"\[BUILD_PROJECT\].*?\[/BUILD_PROJECT\]", "", out, flags=re.DOTALL)
    return out.strip()


# ---------- Legacy build payload (used by old /chat flow; harmless if absent) ----------
def extract_build_payload(response_text: str) -> Optional[Dict[str, Any]]:
    m = re.search(r"\[BUILD_PROJECT\](.+?)\[/BUILD_PROJECT\]", response_text, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(1).strip())
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def build_sections_from_payload(payload: Dict[str, Any]):
    """Legacy helper: builds sections from [BUILD_PROJECT] payload."""
    from .templates import get_template
    btype = payload.get("business_type", "company")
    template_id = btype if btype in ("store", "restaurant", "company", "portfolio", "saas") else "blank"
    template = get_template(template_id)
    sections = [s.copy() for s in template["sections"]]
    if sections and sections[0]["type"] == "hero":
        hero_data = sections[0]["data"].copy()
        if payload.get("name"):
            hero_data["title"] = payload["name"]
        if payload.get("tagline"):
            hero_data["subtitle"] = payload["tagline"]
        sections[0] = {**sections[0], "data": hero_data}
    return sections, template["theme"], template_id
