"""
🧬 Brand DNA Extractor — converts a user brief into a structured brand identity.

Input: "صالة قهوة عُمانية فاخرة بشخصية أنيقة هادئة"
Output: {
  palette: ["#2D1B0E", "#8B5A2B", "#D4A574", "#F5E6D3"],
  tone: "warm-luxe",
  voice: "أنيق، ودود، مُلهم",
  language: "ar-SA (Khaleeji)",
  fonts: ["Cairo", "Playfair Display"],
  glossary: {"المحمصة": "roastery", "مذاق": "taste-profile"},
  archetypes: ["The Sage", "The Lover"]
}

The Brand DNA gets saved into shared_memory.brand_dna and reused across all
future cortex calls in the same project — ensuring consistent identity.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger("zenrex.brand_dna")


_BRAND_DNA_SYSTEM_PROMPT = """أنت **Brand DNA Extractor** — محلل هوية تجارية.

من الـ brief للعميل، استخرج هوية تجارية متناسقة. أرجع JSON صرف:

{
  "name_hint": "<اسم مقترح إن وُجد>",
  "category": "fintech|restaurant|saas|portfolio|ecommerce|landing|gaming|other",
  "palette": ["#hex1", "#hex2", "#hex3", "#hex4", "#hex5"],
  "tone": "وصف نبرة من 2-4 كلمات (مثل: warm-luxe / bold-tech / soft-pastel)",
  "voice": "نبرة الكتابة (مثل: 'أنيق، ودود، مُلهم')",
  "language": "ar-SA|ar-EG|ar-LV|en-US",
  "fonts": ["Font 1", "Font 2"],
  "glossary": {"مصطلح عربي": "english equivalent"},
  "archetypes": ["The Sage", "The Lover", "The Hero", "The Outlaw", "The Magician", "The Innocent", "The Explorer", "The Creator", "The Ruler", "The Caregiver", "The Everyman", "The Jester"],
  "do_not": ["لا تستخدم gradient بنفسجي", "لا تخلط أكثر من 3 خطوط"],
  "do": ["spacing سخي", "صور حقيقية مش stock", "typography كبير"]
}

**القواعد:**
- اختر 4-6 ألوان متناسقة (60-30-10 rule).
- اختر 1-2 archetype من القائمة (لا تخترع).
- glossary: 3-7 مصطلحات يجب التزامها.
- لا تشرح، رد JSON فقط.
"""


async def extract_brand_dna(brief: str, user_language: str = "ar") -> Optional[Dict[str, Any]]:
    """Extract structured Brand DNA from a free-text brief.

    Returns None if EMERGENT_LLM_KEY missing or LLM call fails.
    """
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        return _fallback_brand_dna(brief)

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        session_id = f"brand_dna_{uuid.uuid4().hex[:8]}"
        chat = LlmChat(
            api_key=emergent_key,
            session_id=session_id,
            system_message=_BRAND_DNA_SYSTEM_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        resp = await chat.send_message(UserMessage(text=f"Brief:\n{brief}"))
        raw = resp if isinstance(resp, str) else str(resp)
        # Extract JSON
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                data = json.loads(m.group(0))
                # Validate minimum fields
                if "palette" in data and "tone" in data:
                    return _normalize_dna(data, brief)
            except Exception as e:
                logger.warning(f"[brand_dna] JSON parse failed: {e}")
    except Exception as e:
        logger.warning(f"[brand_dna] LLM call failed: {e}")

    return _fallback_brand_dna(brief)


def _normalize_dna(dna: Dict[str, Any], brief: str) -> Dict[str, Any]:
    """Ensure all expected keys are present + cap sizes."""
    return {
        "name_hint": (dna.get("name_hint") or "")[:60],
        "category": (dna.get("category") or "landing")[:40],
        "palette": (dna.get("palette") or [])[:8],
        "tone": (dna.get("tone") or "")[:60],
        "voice": (dna.get("voice") or "")[:150],
        "language": (dna.get("language") or "ar")[:10],
        "fonts": (dna.get("fonts") or [])[:4],
        "glossary": dict(list((dna.get("glossary") or {}).items())[:10]),
        "archetypes": (dna.get("archetypes") or [])[:3],
        "do_not": (dna.get("do_not") or [])[:5],
        "do": (dna.get("do") or [])[:5],
        "source_brief": brief[:300],
    }


def _fallback_brand_dna(brief: str) -> Dict[str, Any]:
    """Cheap heuristic fallback when LLM unavailable."""
    msg = (brief or "").lower()
    # Crude category detection
    if any(k in msg for k in ["قهوة", "مطعم", "مقهى", "restaurant", "cafe"]):
        category, tone = "restaurant", "warm-luxe"
        palette = ["#1a0f08", "#3d2817", "#c19a6b", "#e8a838", "#f5ebd7"]
        fonts = ["Cairo", "Playfair Display"]
    elif any(k in msg for k in ["تداول", "مالي", "fintech", "trading"]):
        category, tone = "fintech", "bold-tech"
        palette = ["#0d0d0d", "#1a1a1a", "#d4af37", "#10b981", "#ef4444"]
        fonts = ["JetBrains Mono", "Inter"]
    elif any(k in msg for k in ["لعبة", "ألعاب", "game", "gaming"]):
        category, tone = "gaming", "neon-synthwave"
        palette = ["#0d0221", "#ff006e", "#00f5ff", "#fb5607", "#ffbe0b"]
        fonts = ["Press Start 2P", "Audiowide"]
    else:
        category, tone = "landing", "minimal-luxe"
        palette = ["#ffffff", "#0a0a0a", "#ff5e1a", "#f5f5f5", "#1f1f1f"]
        fonts = ["Inter", "Cairo"]

    return {
        "name_hint": "",
        "category": category,
        "palette": palette,
        "tone": tone,
        "voice": "محايد، واضح، احترافي",
        "language": "ar",
        "fonts": fonts,
        "glossary": {},
        "archetypes": ["The Sage"],
        "do_not": [],
        "do": [],
        "source_brief": (brief or "")[:300],
        "fallback": True,
    }


def render_brand_dna_hint(dna: Dict[str, Any]) -> str:
    """Render Brand DNA as a compact system-prompt hint."""
    if not dna:
        return ""
    lines = ["🧬 **Brand DNA المحفوظة (التزم بها صرفاً):**"]
    if dna.get("category"):
        lines.append(f"  • Category: {dna['category']}")
    if dna.get("tone"):
        lines.append(f"  • Tone: {dna['tone']}")
    if dna.get("voice"):
        lines.append(f"  • Voice: {dna['voice']}")
    if dna.get("palette"):
        lines.append(f"  • Palette: {', '.join(dna['palette'])}")
    if dna.get("fonts"):
        lines.append(f"  • Fonts: {', '.join(dna['fonts'])}")
    if dna.get("language"):
        lines.append(f"  • Language: {dna['language']}")
    if dna.get("glossary"):
        gloss = ", ".join(f"{k}→{v}" for k, v in list(dna["glossary"].items())[:5])
        lines.append(f"  • Glossary: {gloss}")
    if dna.get("archetypes"):
        lines.append(f"  • Archetypes: {', '.join(dna['archetypes'])}")
    if dna.get("do"):
        lines.append(f"  • ✅ Do: {' | '.join(dna['do'][:3])}")
    if dna.get("do_not"):
        lines.append(f"  • ❌ Don't: {' | '.join(dna['do_not'][:3])}")
    return "\n".join(lines)
