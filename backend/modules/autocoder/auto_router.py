"""
Auto-Coder Smart Router — Quality-First Edition (v2.0)
═══════════════════════════════════════════════════════════════════════════
الفلسفة: الجودة أولاً. السعر ثاني. أبداً ما نستخدم موديل ضعيف لمجرد
أنه مجاني أو سريع.

كيف يقرّر:
  1. صنّف الطلب (برمجة معقدة / تصميم / محادثة عربية / تفكير عميق ...)
  2. اختار من بين نخبة الموديلات (Top-Tier فقط) الأفضل في هذا التخصص
  3. لو متساويين في الجودة، اختار الأرخص.

الموديلات المُعتمدة (4 فِرَق متخصصة):
  💎 Tier-Premium (نتائج لا تقبل المساومة):
     - Claude Sonnet 4.5  (برمجة معقدة، تفكير عميق، agentic)
     - GPT-5.5            (إبداع، تفكير معقد، تعدد المهام)
     - Gemini 3 Pro       (سياق طويل جداً، عربي ممتاز، رؤية)

  ⚡ Tier-Strong (جودة عالية بسعر أفضل):
     - DeepSeek V3        (تفكير + كود بسعر منخفض)
     - Kimi K2            (عربي طبيعي + سياق 200K)
     - Qwen 2.5 72B       (عربي/سعودي ممتاز)

❌ تم استبعاد:
     - Groq Llama 3.3 (سريع لكن سطحي — ما يصلح للجودة العالية)
     - GPT-4o-mini    (يكتب بسرعة لكن ضعيف الجودة)
     - أي موديل أقل من 70B parameter

استخدام:
    pick_provider(user_message, has_attachments, keyinfo_mode)
"""
from __future__ import annotations
import re
import os
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════
# Pricing per 1M tokens (input/output, USD) — Feb 2026
# Only quality-tier models. NO budget models (no Groq, no mini variants).
# ════════════════════════════════════════════════════════════════════════
PROVIDER_PRICING: Dict[str, Tuple[float, float]] = {
    "claude":   (3.00, 15.00),   # Claude Sonnet 4.5 — top-tier reasoning + coding
    "openai":   (5.00, 15.00),   # GPT-5.5 — top creative + reasoning
    "gemini":   (1.25, 5.00),    # Gemini 3 Pro — long ctx + vision + Arabic
    "deepseek": (0.27, 1.10),    # DeepSeek V3 — strong reasoning at low cost
    "kimi":     (0.60, 2.50),    # Kimi K2 — natural Arabic + long ctx
    "qwen":     (0.40, 1.20),    # Qwen 2.5 72B — best for Arabic / Saudi dialect
}

# Quality score (1-10) for each provider per task class.
# Used to choose: among capable models, prefer highest quality; tiebreak by price.
QUALITY_SCORE: Dict[str, Dict[str, int]] = {
    "coding_hard":       {"claude": 10, "openai": 9, "deepseek": 8, "kimi": 7, "gemini": 8, "qwen": 7},
    "coding":            {"claude": 10, "openai": 9, "deepseek": 9, "kimi": 8, "gemini": 8, "qwen": 8},
    "agentic":           {"claude": 10, "openai": 9, "deepseek": 7, "kimi": 7, "gemini": 8, "qwen": 6},
    "reasoning_hard":    {"claude": 10, "openai": 10, "deepseek": 9, "kimi": 8, "gemini": 9, "qwen": 7},
    "vision":            {"gemini": 10, "openai": 9, "claude": 9, "deepseek": 0, "kimi": 0, "qwen": 0},
    "long_context":      {"gemini": 10, "kimi": 9, "claude": 8, "openai": 7, "deepseek": 6, "qwen": 7},
    "design_creative":   {"claude": 10, "openai": 10, "kimi": 8, "gemini": 8, "qwen": 7, "deepseek": 6},
    "arabic_native":     {"qwen": 10, "kimi": 10, "claude": 9, "gemini": 9, "openai": 8, "deepseek": 7},
    "translation":       {"claude": 10, "gemini": 9, "openai": 9, "qwen": 9, "kimi": 8, "deepseek": 7},
    "quick_qa":          {"claude": 10, "gemini": 9, "openai": 9, "qwen": 8, "kimi": 8, "deepseek": 8},
}


def _env_set(*keys: str) -> bool:
    return any(bool(os.environ.get(k, "").strip()) for k in keys)


def availability(keyinfo_mode: str = "missing") -> Dict[str, bool]:
    """Return which premium providers have keys configured."""
    return {
        "claude":   keyinfo_mode != "missing",
        "openai":   _env_set("OPENAI_API_KEY", "OPENAI_DIRECT_KEY"),
        "gemini":   _env_set("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "deepseek": _env_set("DEEPSEEK_API_KEY"),
        "kimi":     _env_set("MOONSHOT_API_KEY", "KIMI_API_KEY"),
        "qwen":     _env_set("DASHSCOPE_API_KEY", "QWEN_API_KEY"),
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
        r"إصلاح", r"خلل", r"عطل", r"\bحل\b المشكلة", r"أصلح", r"production",
        r"security", r"\bvulnerab", r"thread.?safe",
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
        r"\bbrand", r"إعلان", r"محتوى تسويقي", r"اكتب نص", r"اكتب مقال",
        r"اكتب قصة", r"\bstory\b", r"\bessay\b",
    ],
    "translation": [
        r"\btranslate\b", r"ترجم", r"ترجمة", r"إلى الإنجليزية", r"إلى العربية",
        r"للإنجليزية", r"للعربية",
    ],
    "arabic_native": [
        r"باللهجة السعودية", r"باللهجة الخليجية", r"بالعربي الفصيح",
        r"اكتب لي بالعربي", r"رد بالعربي", r"تكلم سعودي", r"اشرحلي بالعربي",
    ],
    "quick_qa": [
        r"^كم\b", r"^وش\b", r"^ايش\b", r"^كيف\b.*؟$", r"^ما هو", r"^متى",
        r"^أين", r"\bdefine\b", r"\bwhat is\b",
    ],
    "long_context": [
        r"اقرأ كامل", r"كل الملف", r"اشرح المشروع", r"\bentire\b",
        r"\bwhole project\b", r"كامل المنصة", r"الموقع كله", r"جميع الملفات",
    ],
    "reasoning_hard": [
        r"\barchitect", r"\bdesign pattern", r"trade.?off", r"\bcompare\b", r"قارن",
        r"خطّط", r"استراتيجية", r"تحليل عميق", r"فكر بعمق",
        r"\bplan\b.*\bsteps\b", r"\bROI\b", r"خطة عمل", r"دراسة جدوى",
    ],
}


def classify_task(user_message: str, has_attachments: bool = False) -> str:
    """Returns task class. Default to 'agentic' for general Auto-Coder turns."""
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
        return "agentic"
    return max(matches.items(), key=lambda kv: kv[1])[0]


# ════════════════════════════════════════════════════════════════════════
# Decision logic — QUALITY-FIRST
# Pick the highest-quality available provider for the task.
# If two providers are tied on quality, pick the cheaper one.
# ════════════════════════════════════════════════════════════════════════
# Minimum quality threshold per task. Below this, we don't use the provider.
MIN_QUALITY_THRESHOLD = {
    "coding_hard":     9,   # never compromise on hard bugs
    "agentic":         9,   # tool-calling reliability is critical
    "reasoning_hard":  9,
    "vision":          9,
    "coding":          8,
    "design_creative": 8,
    "long_context":    8,
    "arabic_native":   8,
    "translation":     8,
    "quick_qa":        8,   # even simple Qs deserve quality
}


def pick_provider(user_message: str,
                  has_attachments: bool = False,
                  keyinfo_mode: str = "missing") -> Dict[str, str]:
    """
    Quality-first picker:
      1. Detect task class
      2. Score each available provider on quality for this task
      3. Filter to those >= MIN_QUALITY_THRESHOLD
      4. Among qualifiers, pick highest quality.
      5. If tied on quality, pick cheaper (lower output price).
    """
    task = classify_task(user_message, has_attachments)
    avail = availability(keyinfo_mode)
    scores = QUALITY_SCORE.get(task, QUALITY_SCORE["agentic"]) if task != "agentic" else QUALITY_SCORE.get("coding", {})
    if task == "agentic":
        scores = QUALITY_SCORE["agentic"]
    threshold = MIN_QUALITY_THRESHOLD.get(task, 8)

    # Build candidate list: (provider, quality_score, output_price)
    candidates = []
    for prov, q in scores.items():
        if not avail.get(prov):
            continue
        if q < threshold:
            continue
        _, out_price = PROVIDER_PRICING[prov]
        candidates.append((prov, q, out_price))

    # Sort: highest quality first, then cheapest as tiebreak
    candidates.sort(key=lambda x: (-x[1], x[2]))

    if not candidates:
        # Nothing meets the threshold — relax and pick best-available among Premium.
        # Premium tier: claude, openai, gemini (we never fall below these).
        premium_order = ["claude", "openai", "gemini"]
        for prov in premium_order:
            if avail.get(prov):
                in_p, out_p = PROVIDER_PRICING[prov]
                est = (2.0 * in_p + 1.0 * out_p) / 1000.0
                return {
                    "provider": prov,
                    "task": task,
                    "reason": f"premium fallback — {_why(task, prov)}",
                    "est_cost_usd_per_turn": round(est, 5),
                    "quality_score": scores.get(prov, 9),
                    "fallback_chain": [p for p in premium_order if avail.get(p)],
                }
        # Absolute last-resort default
        return {
            "provider": "claude",
            "task": task,
            "reason": "لا يوجد أي مفتاح مضبوط — أضف ANTHROPIC_API_KEY",
            "est_cost_usd_per_turn": 0.0,
            "quality_score": 0,
            "fallback_chain": [],
        }

    best_prov, best_quality, best_price = candidates[0]
    in_p, out_p = PROVIDER_PRICING[best_prov]
    est_per_turn = (2.0 * in_p + 1.0 * out_p) / 1000.0
    return {
        "provider": best_prov,
        "task": task,
        "reason": _why(task, best_prov),
        "est_cost_usd_per_turn": round(est_per_turn, 5),
        "quality_score": best_quality,
        "fallback_chain": [c[0] for c in candidates],
    }


def _why(task: str, prov: str) -> str:
    """Human-readable reasoning shown above each streamed reply."""
    reasons = {
        # Vision
        ("vision", "gemini"):       "Gemini 3 Pro — أعلى دقة في فهم الصور والمخططات",
        ("vision", "openai"):       "GPT-5.5 vision — دقّة استثنائية للتفاصيل",
        ("vision", "claude"):       "Claude — يقرأ التفاصيل البصرية بعمق",
        # Coding hard
        ("coding_hard", "claude"):  "Claude Sonnet 4.5 — الأدق في إصلاح الأخطاء المعقدة",
        ("coding_hard", "openai"):  "GPT-5.5 codex — استثنائي للمشاكل الصعبة",
        ("coding_hard", "deepseek"): "DeepSeek V3 — قوي بسعر معقول",
        # Coding general
        ("coding", "claude"):       "Claude Sonnet 4.5 — جودة عالية ومضمونة",
        ("coding", "deepseek"):     "DeepSeek V3 — نفس الجودة، سعر أقل",
        ("coding", "openai"):       "GPT-5.5 — تنفيذ دقيق",
        # Reasoning
        ("reasoning_hard", "openai"): "GPT-5.5 — يتصدّر بنشمارك التفكير العميق",
        ("reasoning_hard", "claude"): "Claude Sonnet 4.5 — تفكير منظّم ومحكم",
        ("reasoning_hard", "deepseek"): "DeepSeek V3 — reasoning قوي بسعر منخفض",
        # Design / creative
        ("design_creative", "claude"): "Claude — أفضل كتابة إبداعية بالعربي",
        ("design_creative", "openai"): "GPT-5.5 — إبداع وحس تسويقي",
        ("design_creative", "kimi"):   "Kimi — أسلوب طبيعي بالعربي بسعر أقل",
        # Arabic native
        ("arabic_native", "qwen"):  "Qwen 2.5 72B — الأفضل في اللهجات العربية",
        ("arabic_native", "kimi"):  "Kimi K2 — عربي طبيعي وفصيح",
        ("arabic_native", "claude"): "Claude — يتقن العربية الفصحى",
        # Translation
        ("translation", "claude"):  "Claude — ترجمة دقيقة وأمينة",
        ("translation", "gemini"):  "Gemini — ترجمة سريعة ودقيقة",
        # Long context
        ("long_context", "gemini"): "Gemini 3 Pro — سياق 1M token، يبتلع المنصة كاملة",
        ("long_context", "kimi"):   "Kimi K2 — 200K context بسعر منخفض",
        ("long_context", "claude"): "Claude — 200K context بدقة عالية",
        # Quick QA — even here we use top-tier
        ("quick_qa", "claude"):     "Claude — جواب موثوق ودقيق",
        ("quick_qa", "gemini"):     "Gemini 3 Pro — دقيق وسريع",
        # Agentic / tool use
        ("agentic", "claude"):      "Claude Sonnet 4.5 — الأعلى موثوقية في استخدام الأدوات",
        ("agentic", "openai"):      "GPT-5.5 — موثوق في تسلسل الأدوات المعقدة",
        ("agentic", "gemini"):      "Gemini 3 Pro — agentic قوي وذكي",
    }
    return reasons.get((task, prov), f"{prov} — أعلى جودة متاحة لمهمة {task}")


def explain_for_ui(decision: Dict[str, str]) -> str:
    """Compact one-liner shown above the streamed reply."""
    q = decision.get("quality_score", 0)
    return f"🤖 {decision['task']} → **{decision['provider']}** (جودة {q}/10) · {decision['reason']}"
