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
_INTENT_PATTERNS: list = [
    # full website build — most specific (must come first)
    ("full_site", re.compile(
        r"(?:ابن(?:ي|)|أنشئ|اصنع|سو(?:ي|)|اعمل)\s+(?:لي\s+|له\s+|)\s*"
        r"(?:موقع|تطبيق|متجر)\s+(?:كامل|كاملاً)|"
        r"build\s+(?:me\s+)?(?:a\s+)?(?:full|complete|whole|entire)\s+"
        r"(?:site|website|app|store)|"
        r"build\s+(?:me\s+)?(?:a\s+)?(?:site|website|app|store)|"
        r"موقع\s+كامل\s+(?:من|بـ|للـ)|كامل\s+من\s+الصفر",
        re.IGNORECASE)),
    # new page creation
    ("page_creation", re.compile(
        r"(?:أنشئ|اصنع|سوّ?(?:ي|)|اعمل|أضف|ضيف)\s+(?:لي\s+|له\s+|)\s*"
        r"صفحة(?:\s+(?:جديدة|منفصلة|باسم|عنوان|اسم)|\s+\S+)|"
        r"create\s+(?:a\s+|new\s+)?page|new\s+page|"
        r"create\s+(?:a\s+|new\s+)?(?:html\s+)?page",
        re.IGNORECASE)),
    # deletion
    ("deletion", re.compile(
        r"(?:احذف|شيل|أزل|أزله|إحذف|امسح)\b|"
        r"\b(?:remove|delete|drop)\b",
        re.IGNORECASE)),
    # repair / fix
    ("repair", re.compile(
        r"(?:أصلح|صلح|اصلح|الزر ما يشتغل|"
        r"\bfix\b|\brepair\b|"
        r"broken|doesn'?t work|مكسور|معطّل|خطأ|\bbug\b|اللي مو شغّال)",
        re.IGNORECASE)),
    # section addition (after deletion + repair to avoid false-positives)
    ("section_add", re.compile(
        r"(?:أضف|ضيف|اعمل|أنشئ|اصنع)\s+(?:لي\s+|له\s+|)\s*(?:قسم|section)|"
        r"\badd\s+(?:a\s+|me\s+a\s+|me\s+|)(?:new\s+)?section",
        re.IGNORECASE)),
    # edits
    ("edit", re.compile(
        r"(?:غيّر|بدّل|عدّل|حدّث|اعدل|update|edit|modify|change)",
        re.IGNORECASE)),
    # inspection
    ("inspection", re.compile(
        r"(?:اعرض|أرني|اعطني|ورّني|كم|ما\s+هي|\blist\b|\bshow\b|"
        r"what\s+(?:is|are)|أرى|أشوف|كيف)",
        re.IGNORECASE)),
]


def classify_intent(message: str) -> str:
    """Map a free-form user message to an action intent. Defaults to 'chat'."""
    if not message or not isinstance(message, str):
        return "chat"
    msg = message.strip()
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
