"""
Zenrex Action-Based Pricing — strict, transparent, deterministic.

Every user message is classified into ONE intent before the agent starts
streaming. The intent maps to a MIN/MAX credit cost so:

  1. Pre-flight gate can refuse turns when balance < min_cost (no mid-turn
     credit exhaustion, no surprise drops).
  2. Per-turn deduction respects a per-operation floor — the AI cannot
     execute a "create_page" turn for 25 credits even if token usage was tiny.
  3. UI can preview "this operation will cost ~N credits" for large ops.

Numbers were chosen on 2026-02-21 after market research:
  • Margin 4-6× on creative ops  • Margin ~2× on media gen
  • Floor ≥ Lovable competitive baseline  • Ceiling ≤ $0.80/turn worst-case
"""
from __future__ import annotations
import re
from typing import Dict, Tuple, Optional


# ─── Action catalog ─────────────────────────────────────────────────────────
# (min_credits, max_credits, recharge_recommendation_label)
ACTION_COSTS: Dict[str, Tuple[int, int, str]] = {
    "chat":           (25,  80,  "Free tier (100 شعلة)"),
    "inspection":     (15,  50,  "Free tier"),
    "edit":           (80,  250, "Starter ($9 / 12K شعلة)"),
    "section_add":    (120, 350, "Starter ($9)"),
    "page_creation":  (200, 500, "Indie ($29 / 50K شعلة)"),
    "full_site":      (300, 800, "Indie ($29)"),
    "deletion":       (25,  60,  "Free tier"),
    "repair":         (60,  200, "Starter ($9)"),
    "media":          (75,  300, "Indie ($29)"),  # image_nano_banana minimum
}

# Per-tool floor: when a tool runs successfully, the turn's TOTAL charge
# cannot fall below this number. Token-based billing still applies — we just
# pick the MAX(token_charge, op_floor) so cheap tokens can't cheat the system.
TOOL_OP_FLOORS: Dict[str, Tuple[int, str]] = {
    # Mutating tools — real value to the user
    "write_full_html":  (300, "full_site"),
    "apply_section":    (80,  "edit"),         # bumped to 120 for op='append'
    "remove_section":   (25,  "deletion"),
    "create_page":      (200, "page_creation"),
    "delete_page":      (25,  "deletion"),
    "switch_page":      (5,   "inspection"),
    "update_nav":       (40,  "edit"),
    # Inspection — light reads
    "list_pages":       (5,   "inspection"),
    "list_sections":    (5,   "inspection"),
    "read_current_html":(5,   "inspection"),
    "read_html_section":(5,   "inspection"),
    "search_html":      (5,   "inspection"),
    "audit_html":       (15,  "inspection"),
    # Media — already charged separately via image_nano_banana / video catalog
    "generate_image":   (75,  "media"),
    "publish_site":     (10,  "inspection"),
}


# ─── Intent classifier ──────────────────────────────────────────────────────
# Patterns are checked in priority order; first match wins.
#
# Arabic-normalization NOTE: real users type Arabic with mixed diacritics and
# without the hamza — e.g. "انشئ" instead of "أنشئ", "تنشئ" instead of
# "أنشئ", "اضف" instead of "أضف", "بأنشئ" / "بأنفذ" (colloquial future
# tense). We normalize the input string before pattern matching so a single
# pattern matches all these spellings.
_HAMZA_NORM = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
                              "ؤ": "و", "ئ": "ي", "ة": "ه",
                              "ى": "ي", "ـ": ""})
_DIACRITIC_RE = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")


def _normalize_ar(s: str) -> str:
    """Strip diacritics, normalize hamza/alif/ya/ta-marbuta, lowercase."""
    if not s:
        return ""
    s = _DIACRITIC_RE.sub("", s).translate(_HAMZA_NORM)
    return s.lower()


_INTENT_PATTERNS: list = [
    # full website build — most specific (must come first)
    ("full_site", re.compile(
        # Verbs (already hamza-normalized): ابن/ابني/انشئ/اصنع/سوي/اعمل
        r"(?:ابن(?:ي|)|انشي(?:ء)?|اصنع|سو(?:ي|)|اعمل|ابدا)\s+(?:لي\s+|له\s+|)\s*"
        # Allow up to 4 words between verb-object and "كامل" (e.g. "متجر زهور فخم كامل")
        r"(?:موقع|تطبيق|متجر|بلوق|بلوج|مدونه)(?:\s+\S+){0,4}\s+(?:كامل|كامله)|"
        r"build\s+(?:me\s+)?(?:a\s+)?(?:full|complete|whole|entire)\s+"
        r"(?:site|website|app|store)|"
        r"build\s+(?:me\s+)?(?:a\s+)?(?:site|website|app|store)|"
        r"موقع\s+كامل\s+(?:من|بـ|للـ)|كامل\s+من\s+الصفر",
        re.IGNORECASE)),
    # new page creation — covers all colloquial Arabic prefixes:
    # تنشئ / بأنشئ / ننشئ (نحن) / راح أنشئ / بدي أنشئ / أبي أنشئ / بنروح ننشئ ...
    # All have "نشئ" or "نشي" stem after normalization. Same for اصنع/سوي/اعمل/اضف.
    ("page_creation", re.compile(
        r"(?:"
        r"(?:[تنبس]?(?:ا)?نشي(?:ء)?|بانشي(?:ء)?|راح\s+(?:ا|ن)نشي(?:ء)?|"
        r"اصنع|تصنع|نصنع|باصنع|سوي|تسوي|نسوي|باسوي|"
        r"اعمل|تعمل|نعمل|باعمل|"
        r"اضف|تضيف|نضيف|بتضيف|باضيف|ضيف|"
        r"اضيفها|اضيف)\s+(?:لي\s+|له\s+|)\s*"
        r"صفحه(?:\s+(?:جديده|منفصله|مستقله|باسم|عنوان|اسم|اسمها|اسمه)|\s+\S+)"
        r")|"
        # English: create / add / make page
        r"\b(?:create|add|make|build|generate)\s+(?:a\s+|new\s+|me\s+a\s+|me\s+|)(?:html\s+|separate\s+|standalone\s+|)page\b|"
        r"\bnew\s+page\b",
        re.IGNORECASE)),
    # deletion
    ("deletion", re.compile(
        r"(?:احذف|تحذف|باحذف|شيل|تشيل|باشيل|ازل|ازله|امسح|تمسح)\b|"
        r"\b(?:remove|delete|drop)\b",
        re.IGNORECASE)),
    # repair / fix
    ("repair", re.compile(
        r"(?:اصلح|تصلح|باصلح|صلح|الزر\s+ما\s+يشتغل|عالج|تعالج|"
        r"\bfix\b|\brepair\b|"
        r"broken|doesn'?t work|مكسور|معطل|خطا|\bbug\b|اللي\s+مو\s+شغال|مو\s+شغال)",
        re.IGNORECASE)),
    # section addition (after deletion + repair to avoid false-positives)
    ("section_add", re.compile(
        r"(?:اضف|تضيف|باضيف|ضيف|اعمل|تعمل|انشي(?:ء)?|اصنع)\s+(?:لي\s+|له\s+|)\s*(?:قسم|سكشن|section)|"
        r"\badd\s+(?:a\s+|me\s+a\s+|me\s+|)(?:new\s+)?section",
        re.IGNORECASE)),
    # edits — wiring/linking/binding nav links to real pages is an "edit"
    ("edit", re.compile(
        r"(?:غير|تغير|باغير|بدل|تبدل|بابدل|عدل|تعدل|باعدل|"
        r"حدث|تحدث|باحدث|اعدل|اربط|تربط|بنربط|"
        r"update|edit|modify|change|wire|bind|link)",
        re.IGNORECASE)),
    # inspection
    ("inspection", re.compile(
        r"(?:اعرض|ارني|اعطني|ورني|كم|ما\s+هي|\blist\b|\bshow\b|"
        r"what\s+(?:is|are)|اري|اشوف|كيف)",
        re.IGNORECASE)),
]


def classify_intent(message: str) -> str:
    """Map a free-form user message to an action intent. Defaults to 'chat'.

    Input is hamza-normalized first so colloquial spellings (تنشئ، انشئ،
    اضف بدون همزة، الخ) match the same patterns as the formal MSA form.
    """
    if not message or not isinstance(message, str):
        return "chat"
    msg = _normalize_ar(message.strip())
    for intent, pat in _INTENT_PATTERNS:
        if pat.search(msg):
            return intent
    return "chat"


def estimate_min_cost(intent: str) -> int:
    """Return the minimum credits required to start a turn of this intent."""
    return ACTION_COSTS.get(intent, ACTION_COSTS["chat"])[0]


def get_action_label(intent: str) -> Tuple[int, int, str]:
    """Return (min, max, recommended_plan_label) for an intent."""
    return ACTION_COSTS.get(intent, ACTION_COSTS["chat"])


# ─── Pre-flight check ───────────────────────────────────────────────────────
def preflight_check(balance: int, message: str) -> Dict[str, object]:
    """Return a dict that callers can serialize into a 402 response when the
    user's balance can't cover this kind of operation. If allowed, returns
    `{"allowed": True, ...}`.

    Includes a smart, action-aware recharge recommendation so the UI can
    show "اشحن باقة Indie ($29) لتنفيذ ~30 عملية مثل هذه" instead of a
    generic "buy credits" prompt.
    """
    intent = classify_intent(message or "")
    min_cost, max_cost, rec_plan = get_action_label(intent)
    if balance >= min_cost:
        return {
            "allowed": True,
            "intent": intent,
            "min_cost": min_cost,
            "max_cost": max_cost,
            "balance": balance,
            "recommended_plan": rec_plan,
            "preview_recommended": max_cost >= 200,
        }
    return {
        "allowed": False,
        "intent": intent,
        "min_cost": min_cost,
        "max_cost": max_cost,
        "balance": balance,
        "needed": min_cost - balance,
        "recommended_plan": rec_plan,
        "message": (
            f"⛔ الرصيد غير كافٍ لهذه العملية. "
            f"تحتاج ~{min_cost} شعلة، رصيدك {balance}. "
            f"اشحن {rec_plan} لتنفيذ {int(50000 / max(max_cost, 1))}+ عملية مثل هذه."
        ),
        "recharge_url": "/billing",
    }


# ─── Per-turn op floor (applied after token billing) ────────────────────────
def compute_op_floor(tool_log: list) -> int:
    """Given the tools the agent executed this turn, return the OP floor —
    the minimum total credit charge regardless of how few tokens were used.
    Token-based billing still applies; the actual charge is MAX(tokens, this).

    This prevents the AI from running a "create_page" turn that uses cached
    tokens and only bills 30 credits — we floor it at the page-creation rate.
    """
    if not tool_log:
        return 0
    seen_floors: list = []
    for entry in tool_log:
        name = (entry or {}).get("name") or (entry or {}).get("tool")
        if not name:
            continue
        floor, _intent = TOOL_OP_FLOORS.get(name, (0, "chat"))
        if floor > 0:
            seen_floors.append(floor)
    # Use the MAX op floor seen (not the sum — we already cap at 500 elsewhere)
    return max(seen_floors) if seen_floors else 0
