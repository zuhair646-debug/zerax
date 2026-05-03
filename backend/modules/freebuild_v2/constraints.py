"""
Persistent Constraints System for FreeBuild v2.

When the user says things like:
    "ما أبي اللون الأحمر"
    "لا تحط صور قرآن مع كلمات ظاهرة"
    "خلّي الخط بسيط"
    "ممنوع الإيموجي"

We extract these as CONSTRAINTS and save them on the session. Every subsequent
turn injects these constraints into the system prompt, so the architect can't
"drift back" to old behavior after a few turns.

Also supports:
    - Manual constraint CRUD (user can add/remove explicitly)
    - Surgical edit-scope detection: "عدّل القسم الفلاني بس" → restrict edit to that section
"""
from typing import List, Dict, Optional, Any
import re
from datetime import datetime, timezone


# ────────────────────────────────────────────────────────────────────────
#  CONSTRAINT AUTO-EXTRACTION PATTERNS
# ────────────────────────────────────────────────────────────────────────
# Each pattern is: (regex, category, template) — category describes what the
# constraint is about; template is how we store it in a normalized way.
_EXTRACT_PATTERNS = [
    # Color bans: "ما أبي اللون الأحمر", "لا تحط أحمر", "ابعد الأحمر", "ما أبي الأحمر"
    (r"(?:ما\s+أب[ياه]ه?|لا\s+تحط|لا\s+تستخدم|ابعد|ابعدي|تجنّب|بدون|بلا)\s+(?:ال)?لون\s+(الأحمر|الأصفر|الأزرق|الأخضر|الوردي|البنفسجي|الأسود|الأبيض|الذهبي|البرتقالي|الرمادي|البني)",
     "color_ban",
     "ممنوع استخدام اللون {match} نهائياً في الموقع (خلفيات، أزرار، نصوص، حدود، gradients، shadows)"),
    (r"(?:ما\s+أب[ياه]ه?|لا\s+تحط|لا\s+تستخدم|ابعد|تجنّب|بدون|بلا)\s+(الأحمر|الأصفر|الأزرق|الأخضر|الوردي|البنفسجي|الأسود|الأبيض|الذهبي|البرتقالي|الرمادي|البني)",
     "color_ban",
     "ممنوع استخدام اللون {match} نهائياً في الموقع (خلفيات، أزرار، نصوص، حدود، gradients، shadows)"),
    # Quran text ban — many phrasings
    (r"(?:ما\s+أب[ياه]ه?|لا\s+تحط|لا\s+تظهر|بدون)\s+(?:كلمات|نص|آيات|كلام|حروف)\s*(?:ال)?قرآن",
     "quran_text_ban",
     "ممنوع عرض آيات القرآن كنص مكتوب في HTML (الذكاء يحرّفها). استخدم فقط صور decorative تصف مصحف بإضاءة ذهبية بدون نص واضح"),
    (r"(?:القرآن|قرآن|مصحف|المصحف)[^.،\n]*(?:ما\s+تحط|لا\s+تظهر|بدون|غير\s+واضح|مخفي|مو\s+واضح|مش\s+واضح)",
     "quran_text_ban",
     "ممنوع عرض آيات القرآن كنص مكتوب في HTML (الذكاء يحرّفها). استخدم فقط صور decorative تصف مصحف بإضاءة ذهبية بدون نص واضح"),
    (r"(?:صورة|صور)\s+(?:رجل|رجال|شخص)[^.،\n]*(?:قرآن|مصحف)[^.،\n]*(?:غير\s+واضح|بدون\s+كلمات|مخفي)",
     "quran_text_ban",
     "استخدم صور شخص أمامه مصحف بدون نص واضح في الصورة — بس illusion بصرية"),
    # Font ban
    (r"(?:ما\s+أب[ياه]ه?|لا\s+تستخدم|بدون|تجنّب)\s+خط\s+(\w+)",
     "font_ban",
     "ممنوع استخدام خط {match}"),
    # Emoji ban
    (r"(?:ممنوع|ما\s+أب[ياه]ه?|بدون|لا\s+تحط)\s+(?:إيموجي|emoji|رموز\s+تعبيرية)",
     "emoji_ban",
     "ممنوع استخدام إيموجي في أي مكان. استخدم أيقونات SVG inline فقط"),
    # Preserve-others (surgical edit signal, but also a persistent constraint while stated)
    (r"لا\s+(?:تلمس|تغيّر|تمس|تعدّل)\s+باقي\s+(?:الموقع|الصفحات|الأقسام)",
     "preserve_others",
     "عند كل تعديل: ممنوع تلمس أي قسم إلا المطلوب صراحة. حافظ على باقي الأقسام حرفياً"),
    # Generic ban: "ممنوع X"
    (r"ممنوع\s+([^.،\n]{3,60})",
     "generic_ban",
     "ممنوع: {match}"),
]


def extract_constraints_from_text(text: str) -> List[Dict[str, Any]]:
    """Parse a user message and return zero or more constraint dicts."""
    if not text:
        return []
    out: List[Dict[str, Any]] = []
    seen: set = set()
    for pattern, category, template in _EXTRACT_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            match = m.group(1) if m.groups() else m.group(0)
            rule = template.format(match=match.strip())
            key = (category, rule[:80])
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "id": f"c_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{len(out)}",
                "category": category,
                "rule": rule,
                "raw_text": m.group(0),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
    return out


# ────────────────────────────────────────────────────────────────────────
#  SURGICAL EDIT SCOPE DETECTION
# ────────────────────────────────────────────────────────────────────────
# Returns None (full edit) or a scope hint like {"mode":"section", "target":"hero"}
_EDIT_SCOPE_PATTERNS = [
    # "عدّل القسم الفلاني بس" / "غيّر الهيرو فقط"
    (r"(?:عدّل|غيّر|عدل|بدّل)\s+(?:القسم|قسم|بلوك|جزء)\s+([^\s.،]+)(?:\s+(?:بس|فقط|لوحده))?",
     "section"),
    (r"(?:عدّل|غيّر)\s+(الهيرو|hero|الصفحة\s+الرئيسية|الفوتر|footer|النافبار|navbar)\s+(?:بس|فقط)?",
     "section"),
    # "بس" keyword alone with context
    (r"(?:هذا|هذه|القسم\s+هذا|الهيرو\s+هذا).*(?:بس|فقط|لوحده)",
     "section"),
    # "لا تلمس باقي الموقع"
    (r"لا\s+(?:تلمس|تغيّر|تمس)\s+باقي\s+(?:الموقع|الصفحات|الأقسام)",
     "preserve_others"),
]


def detect_edit_scope(text: str) -> Optional[Dict[str, str]]:
    if not text:
        return None
    for pattern, mode in _EDIT_SCOPE_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            target = m.group(1).strip() if m.groups() else ""
            return {"mode": mode, "target": target or "unspecified"}
    return None


# ────────────────────────────────────────────────────────────────────────
#  RENDERING — build a system-prompt block from saved constraints
# ────────────────────────────────────────────────────────────────────────
def render_constraints_block(
    constraints: List[Dict[str, Any]],
    edit_scope: Optional[Dict[str, str]] = None,
) -> str:
    """Format the constraints list + optional edit-scope into a hardened
    system message that gets injected on EVERY turn."""
    if not constraints and not edit_scope:
        return ""

    parts: List[str] = []
    parts.append("# 🚫 القيود الدائمة (لا يمكن تجاوزها أبداً)\n")
    parts.append(
        "هذي قواعد **ثابتة** للمستخدم — لازم تحترمها في كل تحديث HTML تعمله، "
        "حتى لو مرّت عشر أدوار. قبل ترجع الرد، راجع كل قيد وتأكد إن HTML ملتزم.\n"
    )

    if constraints:
        parts.append("\n## القيود المحفوظة:")
        for i, c in enumerate(constraints, 1):
            parts.append(f"{i}. **[{c.get('category','generic')}]** {c.get('rule','')}")

        parts.append(
            "\n### إجراء التحقق الذاتي (قبل كل رد):\n"
            "بعد ما تكتب الـHTML، مرّ على كل قيد فوق وتأكد:\n"
            "- لو القيد لون ممنوع → ابحث في CSS عن اللون ولا تحطه\n"
            "- لو القيد 'ممنوع نص قرآن' → تأكد ما فيه أي آية مكتوبة، فقط صور\n"
            "- لو القيد 'ممنوع إيموجي' → ابحث عن كل إيموجي واستبدله بـSVG\n"
            "لو وجدت أي خرق → أصلحه قبل ما ترسل الرد."
        )

    if edit_scope:
        parts.append(
            "\n## 🔪 Surgical Edit Mode (نطاق هذه المرة فقط)\n"
        )
        if edit_scope["mode"] == "section":
            parts.append(
                f"المستخدم طلب تعديل **قسم محدد فقط**: `{edit_scope['target']}`.\n"
                "**قواعد صارمة**:\n"
                "1. ممنوع تلمس باقي الأقسام. ارجع HTML الكامل لكن مع الحفاظ على كل "
                "section موجود كما هو حرفياً (copy-paste من CURRENT_HTML_STATE).\n"
                "2. عدّل فقط الجزء المطلوب.\n"
                "3. إذا ما تأكدت من القسم المقصود، اسأل سؤال توضيحي (text) قبل التعديل."
            )
        elif edit_scope["mode"] == "preserve_others":
            parts.append(
                "المستخدم قال: 'لا تلمس باقي الموقع'. حافظ على كل شي موجود "
                "(HTML + CSS + JS) كما هو، وعدّل فقط ما طُلب منك بالتحديد الأخير."
            )

    return "\n".join(parts)


# ────────────────────────────────────────────────────────────────────────
#  CONSTRAINT VIOLATION CHECK (server-side safety net)
# ────────────────────────────────────────────────────────────────────────
_COLOR_HEX_MAP = {
    "الأحمر":     ["#ff0000", "#e53e", "#dc26", "#ef44", "#b91", "#f87", "#fca", "red"],
    "الأزرق":     ["#0000ff", "#2563", "#3b82", "#1e40", "blue"],
    "الأصفر":     ["#ffff00", "#facc", "#eab308", "yellow"],
    "الأخضر":     ["#00ff00", "#22c55", "#16a34", "#15803", "green"],
    "الوردي":     ["#ec4899", "#f472", "#db27", "pink"],
    "البنفسجي":   ["#8b5cf6", "#7c3a", "#a855", "purple", "violet"],
    "الذهبي":     ["#d4af37", "#f59e0b", "#fbbf24", "gold", "amber"],
    "البرتقالي":  ["#f97316", "#fb9", "#ea58", "orange"],
}


def check_color_violations(html: str, constraints: List[Dict[str, Any]]) -> List[str]:
    """Return list of violation messages if any color-ban is broken in the HTML."""
    violations: List[str] = []
    if not html:
        return violations
    html_lower = html.lower()
    for c in constraints:
        if c.get("category") != "color_ban":
            continue
        rule = c.get("rule", "")
        # Find color mentioned in the rule
        for color_name, hex_list in _COLOR_HEX_MAP.items():
            if color_name in rule:
                for h in hex_list:
                    if h.lower() in html_lower:
                        violations.append(
                            f"خرق قيد لون: القيد '{rule}' — وجدت {h} في HTML"
                        )
                        break
                break
    return violations
