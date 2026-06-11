"""
Zenrex AI Core — Unified AI Orchestrator
========================================
Single source of truth for all AI agent calls in the platform.
  • Uses EMERGENT_LLM_KEY via emergentintegrations
  • Loads merchant_ai_profile automatically to personalize responses
  • Applies strict domain rules (medicines/food/electronics/clothes/cosmetics)
  • Returns structured JSON suitable for product editor / sites / chatbots

The merchant never trains the AI manually — Zenrex pre-trains it during the
onboarding flow when a Ready Site is delivered. The AI then behaves per-merchant
without any manual configuration.

Owner: Zenrex Platform (Feb 2026)
"""
from __future__ import annotations

import os
import json
import logging
import uuid
from typing import Optional, Dict, Any, List

from motor.motor_asyncio import AsyncIOMotorClient

log = logging.getLogger("claude_core")

_mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _mongo[os.environ["DB_NAME"]]


# ═══════════════════════════════════════════════════════════════════════════
# CORE SYSTEM RULES — mirrored in admin.html as ZENREX_AI_SYSTEM_RULES
# This is the SINGLE source of truth for AI behaviour platform-wide.
# ═══════════════════════════════════════════════════════════════════════════
ZENREX_AI_CORE_RULES = {
    "identity": "Zenrex Product AI — مساعد ذكي عربي لإضافة المنتجات وإدارة المتاجر",
    "language": "Saudi Arabic dialect primary, English fallback",
    "must_obey": [
        "Honor user-specified COLOR exactly — never substitute",
        "Honor user-specified BACKGROUND exactly — never improvise",
        "Honor user-specified COUNT of images",
        "Research thoroughly before generating — never invent specs",
        "Return COMPLETE info (specs + benefits + usage + warnings + warranty)",
        "Save user credits — output exactly what was asked, no padding",
    ],
    "domain_rules": {
        "medicines": ["dosage", "benefits", "usage_instructions", "warnings", "contraindications", "active_ingredients", "warranty:none"],
        "food": ["ingredients", "calories", "allergens", "expiry", "storage_conditions"],
        "clothes": ["fabric", "available_sizes", "wash_instructions", "gender", "season"],
        "electronics": ["specs", "warranty", "compatibility", "battery_life", "dimensions"],
        "cosmetics": ["skin_type", "ingredients", "expiry", "usage_steps", "warnings"],
        "perfume": ["volume", "notes", "concentration", "gender", "longevity"],
        "shoes": ["material", "available_sizes", "gender", "season"],
        "home": ["material", "dimensions", "warranty", "assembly_required"],
        "kids": ["age_range", "material", "warranty", "safety_warnings"],
        "books": ["language", "pages", "isbn", "publisher", "genre"],
    },
    "forbidden": [
        "Invent warranty URLs that don't exist",
        "Deviate from user's color/background specification",
        "Generate identical images to pad count",
        "Add promotional fluff the user didn't ask for",
        "Provide unverified medical/health claims",
    ],
}


# ───────────────────────────────────────────────────────────────────────────
# Merchant context loader
# ───────────────────────────────────────────────────────────────────────────
async def load_merchant_context(merchant_id: str) -> Dict[str, Any]:
    """Load the merchant's AI profile to personalize AI behaviour."""
    if not merchant_id:
        return {}
    p = await db.merchant_ai_profiles.find_one({"merchant_id": merchant_id}, {"_id": 0})
    return p or {}


def _build_system_message(merchant_ctx: Dict[str, Any], task: str) -> str:
    """Assemble the system prompt: core rules + merchant context + task-specific guidance."""
    rules_json = json.dumps(ZENREX_AI_CORE_RULES, ensure_ascii=False, indent=2)
    parts = [
        f"You are {ZENREX_AI_CORE_RULES['identity']}.",
        f"Language: {ZENREX_AI_CORE_RULES['language']}.",
        "",
        "═══ CORE RULES (MUST FOLLOW) ═══",
        rules_json,
        "",
    ]
    if merchant_ctx:
        parts += [
            "═══ MERCHANT CONTEXT (auto-trained at store handover) ═══",
            f"Industry: {merchant_ctx.get('industry', 'general')}",
            f"Sub-categories: {', '.join(merchant_ctx.get('sub_categories', []))}",
            f"Target markets: {', '.join(merchant_ctx.get('target_markets', ['sa']))}",
            f"Brand tone: {merchant_ctx.get('brand_tone', 'professional')}",
            f"Photography style: {merchant_ctx.get('photography_style', 'product')}",
            f"Color palette: {', '.join(merchant_ctx.get('typical_color_palette', []))}",
            f"Notes from onboarding: {merchant_ctx.get('notes', '—')}",
            "",
        ]
    parts.append(f"═══ CURRENT TASK ═══\n{task}")
    return "\n".join(parts)


# ───────────────────────────────────────────────────────────────────────────
# Product Research Chat (the new unified entry point)
# ───────────────────────────────────────────────────────────────────────────
async def product_research_chat(
    merchant_id: Optional[str],
    user_prompt: str,
    user_spec: Optional[Dict[str, Any]] = None,
    image_base64: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Single endpoint for product research + chat.
    Returns a structured dict the frontend renders into a chat bubble:
      { title, description, features, specs, benefits, usage, warnings, warranty, images, respects:{color,bg,count} }
    """
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "EMERGENT_LLM_KEY not configured", "fallback": True}

    user_spec = user_spec or {}
    merchant_ctx = await load_merchant_context(merchant_id)

    task = (
        "User has asked you to research and structure a product. "
        "Parse their request, honor exact color/background/count, and return STRICT JSON with these fields:\n"
        "- title (string, full official product name)\n"
        "- description (3-4 marketing sentences in Saudi Arabic)\n"
        "- features (array of 6-10 concrete benefits)\n"
        "- specs (object key→value, 6-10 technical specs)\n"
        "- benefits (array — health/functional benefits)\n"
        "- usage_instructions (array of steps)\n"
        "- warnings (array — for medicine/food/cosmetics; empty otherwise)\n"
        "- warranty (object {duration, official_url}; empty for medicine/food)\n"
        "- recommended_price_sar (number)\n"
        "- respects (object {color: string|null, background: string|null, count: number|null} — echo back what user asked)\n"
        f"User's parsed spec: {json.dumps(user_spec, ensure_ascii=False)}\n"
        "Output ONLY the JSON object — no markdown, no fences, no commentary."
    )
    system_msg = _build_system_message(merchant_ctx, task)

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:
        log.error(f"emergentintegrations import failed: {e}")
        return {"error": str(e), "fallback": True}

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id or f"prod-{uuid.uuid4().hex[:10]}",
            system_message=system_msg,
        )
        # Gemini is fast & multimodal — best for product research
        chat.with_model("gemini", "gemini-2.5-flash")
        msg = UserMessage(text=user_prompt)
        resp = await chat.send_message(msg)
        text = resp if isinstance(resp, str) else getattr(resp, "text", str(resp))
        # Strip optional markdown fences
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1] if "```" in text[3:] else text[3:]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0]
        data = json.loads(text)
        data["_meta"] = {"model": "gemini-2.5-flash", "merchant_id": merchant_id}
        return data
    except json.JSONDecodeError as e:
        log.warning(f"AI returned non-JSON: {e}")
        return {"error": "Invalid AI response", "raw": text[:500], "fallback": True}
    except Exception as e:
        log.error(f"product_research_chat failed: {e}")
        return {"error": str(e), "fallback": True}


# ───────────────────────────────────────────────────────────────────────────
# Onboarding interview — used by Zenrex at store handover
# ───────────────────────────────────────────────────────────────────────────
async def onboarding_extract(merchant_input: str) -> Dict[str, Any]:
    """
    Take free-text input from the merchant during store-setup conversation
    and extract structured AI profile fields. This is what fills the
    `merchant_ai_profiles` collection — the merchant never edits it manually.
    """
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {"error": "EMERGENT_LLM_KEY not configured"}

    task = (
        "Extract the merchant's business profile from their description and return STRICT JSON:\n"
        "{\n"
        '  "industry": "electronics|clothes|food|meds|beauty|home|sports|books|cars|pets|perfume|other",\n'
        '  "sub_categories": ["..."],\n'
        '  "target_markets": ["sa","ae",...],\n'
        '  "brand_tone": "professional|friendly|luxury|casual|youthful",\n'
        '  "languages": ["ar","en"],\n'
        '  "typical_color_palette": ["#hex","#hex"],\n'
        '  "photography_style": "product|lifestyle|luxury|flat|3d",\n'
        '  "notes": "summary of merchant\'s unique positioning"\n'
        "}\n"
        "Output ONLY the JSON object."
    )
    system_msg = _build_system_message({}, task)

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=api_key,
            session_id=f"onboard-{uuid.uuid4().hex[:8]}",
            system_message=system_msg,
        )
        chat.with_model("gemini", "gemini-2.5-flash")
        resp = await chat.send_message(UserMessage(text=merchant_input))
        text = resp if isinstance(resp, str) else getattr(resp, "text", str(resp))
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1] if "```" in text[3:] else text[3:]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0]
        return json.loads(text)
    except Exception as e:
        log.error(f"onboarding_extract failed: {e}")
        return {"error": str(e)}
