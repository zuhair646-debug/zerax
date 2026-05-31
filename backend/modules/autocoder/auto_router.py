"""
Auto-Coder Smart Router
═══════════════════════════════════════════════════════════════════════════
Selects the cheapest *capable* provider for each user turn — based on:
  • Task class detected from the user message (coding, design, reasoning,
    quick QA, translation, vision, agentic/tool-heavy, etc.)
  • Live availability of API keys
  • Real-world pricing (Feb 2026)

Objective:  highest quality at lowest cost. Quality > savings on hard tasks.

Used by `_autocoder_stream` when `model == "auto"`.
"""
from __future__ import annotations
import re
import os
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════
# Pricing per 1M tokens (input/output, USD) — Feb 2026
# ════════════════════════════════════════════════════════════════════════
PROVIDER_PRICING: Dict[str, Tuple[float, float]] = {
    "groq":     (0.00, 0.00),   # free tier Llama
    "gemini":   (0.00, 0.00),   # free tier 2.5 Flash
    "deepseek": (0.27, 1.10),   # DeepSeek V3 — cheapest coder
    "kimi":     (0.60, 2.50),   # Kimi K2.6
    "openai":   (5.00, 15.00),  # GPT-5.5
    "claude":   (3.00, 15.00),  # Claude Sonnet 4.5
}


def _env_set(*keys: str) -> bool:
    return any(bool(os.environ.get(k, "").strip()) for k in keys)


def availability(keyinfo_mode: str = "missing") -> Dict[str, bool]:
    """Return which providers have keys configured."""
    return {
        "claude":   keyinfo_mode != "missing",
        "openai":   _env_set("OPENAI_API_KEY", "OPENAI_DIRECT_KEY"),
        "kimi":     _env_set("MOONSHOT_API_KEY", "KIMI_API_KEY"),
        "deepseek": _env_set("DEEPSEEK_API_KEY"),
        "groq":     _env_set("GROQ_API_KEY"),
        "gemini":   _env_set("GEMINI_API_KEY"),
    }


# ════════════════════════════════════════════════════════════════════════
# Task classifier — keyword-based, fast (<1ms)
# ════════════════════════════════════════════════════════════════════════
TASK_KEYWORDS = {
    "vision": [
        r"\bصور\b", r"\bمخطط", r"\bmockup",
        r"\bphoto", r"\bimage", r"\bdiagram", r"UI ?screenshot",
        r"شف الصورة", r"حلّل الصورة", r"اقرأ المخطط",
    ],
    "coding_hard": [
        r"\bbug\b", r"\bfix\b", r"\bcrash", r"\bsegfault", r"refactor",
        r"\boptimize\b", r"performance", r"\bracing\b", r"deadlock",
        r"إصلاح", r"خلل", r"عطل", r"\bحل\b المشكلة", r"أصلح",
    ],
    "coding": [
        r"\bcode\b", r"\bfunction\b", r"\bclass\b", r"\bAPI\b", r"endpoint",
        r"\bschema\b", r"\bquery\b", r"\bdatabase\b", r"\bSQL\b",
        r"احذف", r"عدّل", r"أنشئ", r"اضف", r"نفّذ", r"حدّث",
        r"قسم", r"\bmodule\b", r"git ", r"deploy",
        r"\.py\b", r"\.js\b", r"\.tsx?\b", r"\.json\b", r"\.yaml?\b",
    ],
    "design_creative": [
        r"اقترح اسم", r"اقترح عنوان", r"\bcopy\b", r"تسويق", r"slogan",
        r"\bbrand", r"إعلان", r"محتوى تسويقي",
    ],
    "translation": [
        r"\btranslate\b", r"ترجم", r"ترجمة", r"إلى الإنجليزية", r"إلى العربية",
        r"للإنجليزية", r"للعربية",
    ],
    "quick_qa": [
        r"^كم\b", r"^وش\b", r"^ايش\b", r"^كيف\b.*؟$", r"^ما هو", r"^متى",
        r"^أين", r"\bdefine\b", r"\bwhat is\b",
    ],
    "long_context": [
        r"اقرأ كامل", r"كل الملف", r"اشرح المشروع", r"\bentire\b",
        r"\bwhole project\b", r"كامل المنصة",
    ],
    "reasoning_hard": [
        r"\barchitect", r"\bdesign pattern", r"trade.?off", r"\bcompare\b", r"قارن",
        r"خطّط", r"استراتيجية", r"تحليل عميق",
        r"\bplan\b.*\bsteps\b", r"\bROI\b",
    ],
}


def classify_task(user_message: str, has_attachments: bool = False) -> str:
    """Returns one of:
    vision / coding_hard / coding / design_creative / translation /
    quick_qa / long_context / reasoning_hard / agentic (default)
    """
    if has_attachments:
        return "vision"
    text = (user_message or "")[:2000]
    word_count = len(text.split())

    # short single-line questions → quick_qa
    if word_count <= 6 and "؟" in text:
        return "quick_qa"

    matches: Dict[str, int] = {}
    for task, patterns in TASK_KEYWORDS.items():
        c = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
        if c:
            matches[task] = c

    if not matches:
        # Default to agentic (multi-tool Auto-Coder flow) → needs strong tool-calling
        return "agentic"
    return max(matches.items(), key=lambda kv: kv[1])[0]


# ════════════════════════════════════════════════════════════════════════
# Decision matrix — task class → ordered provider preferences
# Each list is ordered from preferred to fallback.
# Quality-first when the task is hard; cost-first when cheap models suffice.
# ════════════════════════════════════════════════════════════════════════
TASK_PROVIDER_RANK: Dict[str, List[str]] = {
    "vision":          ["gemini", "openai", "claude"],            # gemini 2.5 free + multimodal
    "coding_hard":     ["claude", "openai", "deepseek", "kimi"],  # accuracy first
    "coding":          ["deepseek", "kimi", "claude", "openai"],  # cheap+capable coder
    "design_creative": ["kimi", "claude", "openai", "gemini"],    # Kimi strong on Chinese/Arabic
    "translation":     ["gemini", "deepseek", "openai"],          # free first
    "quick_qa":        ["gemini", "groq", "deepseek"],            # free tier
    "long_context":    ["kimi", "gemini", "claude"],              # Kimi 200k ctx, gemini 1M, claude 200k
    "reasoning_hard":  ["openai", "claude", "kimi"],              # GPT-5.5 wins reasoning bench
    "agentic":         ["claude", "openai", "kimi"],              # tool-calling reliability
}


def pick_provider(user_message: str,
                  has_attachments: bool = False,
                  keyinfo_mode: str = "missing") -> Dict[str, str]:
    """Return {provider, task, reason, est_cost_per_1k_tokens}."""
    task = classify_task(user_message, has_attachments)
    avail = availability(keyinfo_mode)
    ranked = TASK_PROVIDER_RANK.get(task, TASK_PROVIDER_RANK["agentic"])

    for prov in ranked:
        if avail.get(prov):
            in_p, out_p = PROVIDER_PRICING[prov]
            # Estimate for a typical ~2K in / 1K out turn
            est_per_turn = (2.0 * in_p + 1.0 * out_p) / 1000.0
            return {
                "provider": prov,
                "task": task,
                "reason": _why(task, prov),
                "est_cost_usd_per_turn": round(est_per_turn, 5),
                "fallback_chain": [p for p in ranked if avail.get(p)],
            }

    # Nothing available — surface a clear error rather than guessing
    return {
        "provider": "claude",  # last-resort default; backend will error gracefully
        "task": task,
        "reason": "لا يوجد أي مفتاح مضبوط — أضف ANTHROPIC_API_KEY أو غيره.",
        "est_cost_usd_per_turn": 0.0,
        "fallback_chain": [],
    }


def _why(task: str, prov: str) -> str:
    reasons = {
        ("vision", "gemini"):       "Gemini 2.5 Flash مجاني + رؤية ممتازة",
        ("vision", "openai"):       "GPT-4o vision قوي جداً للتصاميم",
        ("vision", "claude"):       "Claude يفهم الصور ممتاز",
        ("coding_hard", "claude"):  "Claude Sonnet 4.5 أعلى دقة لإصلاح الأخطاء المعقّدة",
        ("coding_hard", "openai"):  "GPT-5.5 codex استثنائي للأخطاء المعقّدة",
        ("coding", "deepseek"):     "DeepSeek V3 الأرخص ودقيق جداً للبرمجة",
        ("coding", "kimi"):         "Kimi K2.6 ممتاز بسعر معقول",
        ("coding", "claude"):       "Claude Sonnet 4.5 إذا تبي أعلى جودة",
        ("design_creative", "kimi"): "Kimi قوي بالعربي والإبداع، أرخص من Claude",
        ("design_creative", "claude"): "Claude أفضل للكتابة الإبداعية العربية",
        ("translation", "gemini"):  "Gemini مجاني وترجمة دقيقة",
        ("translation", "deepseek"): "DeepSeek رخيص جداً للترجمة",
        ("quick_qa", "gemini"):     "سؤال سريع — Gemini مجاني وكفاية",
        ("quick_qa", "groq"):       "Groq أسرع وبدون كلفة",
        ("long_context", "kimi"):   "Kimi 200K context — مناسب للملفات الطويلة",
        ("long_context", "gemini"): "Gemini 1M context — يبتلع المنصة كاملة",
        ("reasoning_hard", "openai"): "GPT-5.5 يتصدّر بنشمارك التفكير المعقّد",
        ("reasoning_hard", "claude"): "Claude Sonnet 4.5 يفكّر بعمق ودقة",
        ("agentic", "claude"):      "Claude الأكثر موثوقية في tool-calling",
        ("agentic", "openai"):      "GPT-5.5 موثوق جداً في الأدوات",
    }
    return reasons.get((task, prov), f"{prov} متاح ومناسب لمهمة {task}")


def explain_for_ui(decision: Dict[str, str]) -> str:
    """Compact one-liner shown above the streamed reply."""
    return f"🤖 Auto · {decision['task']} → **{decision['provider']}** · {decision['reason']}"
