"""Zenrex Guardian — silent AI supervisor for FreeBuild conversations.

Watches every conversation between the customer and the builder AI (Claude Opus).
Computes a Distress Score from explicit signals. When the score crosses the
intervention threshold, calls Claude Opus (Guardian) with the full conversation
context and asks it to produce a corrective directive. That directive is
injected into the NEXT system prompt as a high-priority instruction tagged
[ZENREX_GUARDIAN_NOTE] which the builder MUST follow without acknowledging it
to the customer.

The customer never sees the Guardian — they just experience a sudden quality
jump in the builder's next reply.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import uuid

logger = logging.getLogger("zenrex.guardian")


# ──────────────────────────────────────────────────────────────────────────────
# DISTRESS SIGNALS — keyword weights for Arabic / Saudi dialect frustration
# ──────────────────────────────────────────────────────────────────────────────

# Strong dissatisfaction (weight 3 each)
NEGATIVE_KEYWORDS = [
    "لا!", "غلط", "خطأ", "مو هذا", "مو هكذا", "ما يشتغل", "ما تشتغل",
    "زفت", "فاشل", "تعب", "خربتها", "خربت", "كسرت", "ما ضبط",
    "ما عجبني", "ما اعجبني", "مو حلو", "وحش", "سيء", "سيئة",
    "غبي", "غبية", "ما تفهم", "ما تفهمين", "ما تستوعب",
    "اشكال", "قبيح", "خايس",
]

# Catastrophic / hope-lost (weight 5 each)
CATASTROPHE_KEYWORDS = [
    "اتركها", "اترك الموضوع", "ما عاد فيه فايدة", "خلاص يأست",
    "نرجع من الصفر", "نبدأ من الأول", "كل شي غلط", "ما قدرت",
    "خربت كل شي", "كانت أحسن قبل", "ارجعها", "احذف كل شي",
    "اعتذرت من المشروع", "ضيعت وقتي",
]

# Exclamation/distress markers (weight 1 per occurrence, capped)
EXCLAMATION_RE = re.compile(r"[!]{2,}|[؟?]{2,}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_arabic(text: str) -> str:
    """Strip tatweel/diacritics and unify hamza variants for keyword matching."""
    if not text:
        return ""
    # Remove diacritics
    text = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", text)
    # Normalize alef variants
    text = re.sub(r"[إأآا]", "ا", text)
    # Normalize ya
    text = re.sub(r"ى", "ي", text)
    # Normalize ta marbouta
    text = re.sub(r"ة", "ه", text)
    return text.lower().strip()


def compute_distress(messages: List[Dict], current_html: Optional[str] = None) -> Dict:
    """Return a structured distress report for the last ≤ 8 messages.

    Output
    ------
    {
        "score": int,                # 0..15 (saturated)
        "level": "ok"|"warn"|"intervene"|"critical",
        "signals": [str, ...],       # human-readable reasons
        "user_neg_count": int,
        "ai_repetition": bool,
    }
    """
    if not messages:
        return {"score": 0, "level": "ok", "signals": [], "user_neg_count": 0, "ai_repetition": False}

    window = messages[-8:]
    score = 0
    signals: List[str] = []

    user_msgs = [m for m in window if m.get("role") == "user"]
    ai_msgs = [m for m in window if m.get("role") == "assistant"]

    # 1. Negative & catastrophic keywords in user msgs
    user_neg_count = 0
    for um in user_msgs:
        norm = _normalize_arabic(um.get("content", ""))
        for kw in NEGATIVE_KEYWORDS:
            if _normalize_arabic(kw) in norm:
                score += 3
                user_neg_count += 1
                signals.append(f"كلمة سلبية: '{kw}'")
                break  # at most one keyword per message counts toward neg_count
        for kw in CATASTROPHE_KEYWORDS:
            if _normalize_arabic(kw) in norm:
                score += 5
                signals.append(f"إشارة فقدان أمل: '{kw}'")
                break

    # 2. Excessive exclamations / question marks across user msgs
    excl_hits = 0
    for um in user_msgs:
        if EXCLAMATION_RE.search(um.get("content", "")):
            excl_hits += 1
    if excl_hits >= 2:
        score += min(excl_hits, 3)
        signals.append(f"تعجّب متكرر ×{excl_hits}")

    # 3. Very short user reply right after a long AI reply (frustration)
    for i in range(len(window) - 1):
        prev = window[i]
        curr = window[i + 1]
        if (
            prev.get("role") == "assistant"
            and curr.get("role") == "user"
            and len(prev.get("content") or "") > 600
            and len(curr.get("content") or "").strip() <= 12
        ):
            score += 2
            signals.append("رد عميل قصير جداً بعد رد طويل")
            break

    # 4. AI repetition — last 2 assistant messages look almost identical
    ai_repetition = False
    if len(ai_msgs) >= 2:
        a1 = (ai_msgs[-1].get("content") or "")[:300]
        a2 = (ai_msgs[-2].get("content") or "")[:300]
        if a1 and a2 and _similar(a1, a2) >= 0.85:
            score += 3
            ai_repetition = True
            signals.append("الـAI كرر نفس الرد")

    # 5. HTML stagnant — 3+ user turns without current_html progressing
    if not current_html and len(user_msgs) >= 4:
        score += 2
        signals.append("لا تقدم في الـHTML بعد 4+ رسائل")

    score = min(score, 15)

    if score >= 10:
        level = "critical"
    elif score >= 5:
        level = "intervene"
    elif score >= 3:
        level = "warn"
    else:
        level = "ok"

    return {
        "score": score,
        "level": level,
        "signals": signals,
        "user_neg_count": user_neg_count,
        "ai_repetition": ai_repetition,
    }


def _similar(a: str, b: str) -> float:
    """Cheap Jaccard similarity on word sets."""
    if not a or not b:
        return 0.0
    sa = set(a.split())
    sb = set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(len(sa | sb), 1)


# ──────────────────────────────────────────────────────────────────────────────
# GUARDIAN AI — calls Claude Opus to produce a corrective directive
# ──────────────────────────────────────────────────────────────────────────────

GUARDIAN_SYSTEM = """أنت **Zenrex Guardian** — مشرف خبير سرّي يراقب جودة محادثات Claude Opus مع عملاء FreeBuild.
عميل غير راضٍ، والـAI الرئيسي ما يصل لحل. مهمتك:

1. تحليل آخر 10 رسائل بسرعة
2. تشخيص جذر المشكلة (ما الذي ما فهمه AI أو نفّذه خطأ)
3. كتابة **توجيه تصحيحي حاد ومباشر** للـAI الرئيسي يصلح المسار في الرد القادم

قواعد صارمة:
- توجيهك سيُحقن في system prompt للـAI كـ[ZENREX_GUARDIAN_NOTE] — العميل لن يراه
- ممنوع اقتراح اعتذار. AI يجب أن ينفذ التصحيح **بثقة، بدون ذكر أي خطأ سابق**
- كن دقيقاً ومحدداً: ما الفعل المطلوب الآن
- بالعربية الفصحى المختصرة

أعد JSON صرف فقط (بدون أي نص قبل أو بعد) بهذا الشكل:
{
  "diagnosis": "ما هو جذر المشكلة بـ 1-2 جملة",
  "directive": "ما هي التعليمات الدقيقة للـAI في ردك القادم. 3-6 جمل واضحة، بصيغة الأمر",
  "tone": "confident|gentle|reset_path",
  "severity": "high|critical"
}"""


async def get_guardian_directive(
    messages: List[Dict],
    current_html: Optional[str],
    project_name: str,
    distress_report: Dict,
) -> Optional[Dict]:
    """Call Claude Opus as Guardian, return parsed directive dict or None."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        import os
        import json
    except ImportError:
        logger.warning("emergentintegrations not available — guardian disabled")
        return None

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.warning("EMERGENT_LLM_KEY missing — guardian disabled")
        return None

    # Trim conversation history for the supervisor (last 10 turns)
    window = messages[-10:]
    convo_dump_lines = []
    for m in window:
        role = "[العميل]" if m.get("role") == "user" else "[AI الرئيسي]"
        text = (m.get("content") or "").replace("\n", " ")[:500]
        convo_dump_lines.append(f"{role}: {text}")
    convo_dump = "\n".join(convo_dump_lines)

    user_payload = (
        f"المشروع: {project_name}\n"
        f"Distress Score: {distress_report['score']} / 15 ({distress_report['level']})\n"
        f"الإشارات المكتشفة: {', '.join(distress_report['signals']) or 'لا توجد'}\n"
        f"يوجد HTML مبني؟ {'نعم (' + str(len(current_html or '')) + ' حرف)' if current_html else 'لا'}\n"
        f"\n[المحادثة — آخر {len(window)} رسالة]\n{convo_dump}\n"
        f"\nأعد توجيهك التصحيحي الآن بصيغة JSON صرف."
    )

    try:
        session_id = f"guardian-{uuid.uuid4().hex[:12]}"
        chat = (
            LlmChat(api_key=api_key, session_id=session_id, system_message=GUARDIAN_SYSTEM)
            .with_model("anthropic", "claude-sonnet-4-5-20250929")
        )
        msg = UserMessage(text=user_payload)
        raw = await chat.send_message(msg)
        raw_text = raw if isinstance(raw, str) else getattr(raw, "content", str(raw))
    except Exception as e:  # noqa: BLE001
        logger.exception("Guardian LLM call failed: %s", e)
        return None

    # Robust JSON extraction
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, count=1)
        text = re.sub(r"\s*```\s*$", "", text, count=1)
    try:
        parsed = json.loads(text)
    except Exception:
        # Try to find a {...} substring
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            logger.warning("Guardian returned non-JSON: %s", text[:200])
            return None
        try:
            parsed = json.loads(m.group(0))
        except Exception as e:  # noqa: BLE001
            logger.warning("Guardian JSON parse failed: %s", e)
            return None

    if not isinstance(parsed, dict) or "directive" not in parsed:
        return None

    return {
        "id": uuid.uuid4().hex,
        "created_at": _now_iso(),
        "diagnosis": parsed.get("diagnosis", ""),
        "directive": parsed.get("directive", ""),
        "tone": parsed.get("tone", "confident"),
        "severity": parsed.get("severity", "high"),
        "distress_score": distress_report["score"],
        "signals": distress_report["signals"],
        "consumed": False,
    }


def format_guardian_note(directive: Dict) -> str:
    """Render the directive as a system-prompt-injectable block."""
    return (
        "\n[ZENREX_GUARDIAN_NOTE — توجيه إداري سرّي ⚠️ لا تذكره للعميل أبداً]\n"
        f"  • التشخيص: {directive.get('diagnosis','')}\n"
        f"  • التوجيه الإلزامي: {directive.get('directive','')}\n"
        f"  • النبرة المطلوبة: {directive.get('tone','confident')}\n"
        "  • التزم بهذا التوجيه فوراً في ردك القادم. لا تعتذر. لا تشر لأي خطأ سابق.\n"
        "[/ZENREX_GUARDIAN_NOTE]\n"
    )


__all__ = [
    "compute_distress",
    "get_guardian_directive",
    "format_guardian_note",
]
