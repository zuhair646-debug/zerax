"""
🎴 Setup Wizard — emits structured Card events for the frontend.

Each "card" is a UI component the React side renders. The AI calls
`build_setup_card()` instead of sending plain text. Cards are JSON
objects with a stable schema so the frontend can render them.

Card types:
  - intro: explainer text + "Continue" button
  - link_with_action: external link the user opens (e.g. liveblocks.io)
  - key_input_validate: text input + validate button + helper text
  - checklist: multi-step progress tracker
  - success: confirmation + summary of saved credentials
  - cost_summary: shows expected costs for the chosen path
  - skip_alternative: offers a fallback (e.g. "use our shared key instead")
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .knowledge import get_integration


def card_intro(integration_id: str, language: str = "ar") -> Dict[str, Any]:
    integ = get_integration(integration_id)
    if not integ:
        return {}
    label = integ.get(f"{language}_label", integration_id)
    return {
        "card_id": f"intro_{uuid.uuid4().hex[:6]}",
        "card_type": "setup_intro",
        "integration_id": integration_id,
        "title": f"🔑 إعداد: {label}" if language == "ar" else f"🔑 Setup: {label}",
        "subtitle_ar": "سنحتاج خطوات بسيطة قبل البناء — استرخِ، سأرشدك خطوة بخطوة" if language == "ar" else None,
        "subtitle_en": "We need a few quick setup steps — relax, I'll guide you" if language == "en" else None,
        "estimated_minutes": 3,
        "actions": [
            {"id": "start", "label": "ابدأ الإعداد" if language == "ar" else "Start Setup", "primary": True},
            {"id": "skip_for_now", "label": "تخطّى الآن" if language == "ar" else "Skip for now"},
        ],
    }


def card_key_input(integration_id: str, credential: Dict[str, Any], language: str = "ar") -> Dict[str, Any]:
    cred_label = credential.get(f"{language}_label") or credential.get("ar_label") or credential["key"]
    where = (credential.get("where_to_get", {}) or {}).get(language, "")
    return {
        "card_id": f"key_input_{uuid.uuid4().hex[:6]}",
        "card_type": "key_input_validate",
        "integration_id": integration_id,
        "credential_key": credential["key"],
        "title": f"الصق {cred_label}" if language == "ar" else f"Paste your {cred_label}",
        "instructions_markdown": where,
        "is_secret": credential.get("is_secret", True),
        "format_regex": credential.get("format_regex"),
        "placeholder": credential.get("placeholder", "..."),
        "validation_endpoint": f"/api/concierge/validate/{credential['key']}",
        "actions": [
            {"id": "validate_save", "label": "تحقّق واحفظ" if language == "ar" else "Validate & Save", "primary": True},
            {"id": "open_provider", "label": "افتح صفحة الإصدار" if language == "ar" else "Open provider", "url_field": "where_to_get_url"},
        ],
    }


def card_checklist(integration_id: str, steps_done: List[str], steps_pending: List[str], language: str = "ar") -> Dict[str, Any]:
    return {
        "card_id": f"checklist_{uuid.uuid4().hex[:6]}",
        "card_type": "setup_checklist",
        "integration_id": integration_id,
        "title": "تقدّم الإعداد" if language == "ar" else "Setup Progress",
        "steps": [
            *[{"label": s, "done": True} for s in steps_done],
            *[{"label": s, "done": False} for s in steps_pending],
        ],
    }


def card_success(integration_id: str, account_info: Optional[Dict[str, Any]] = None, language: str = "ar") -> Dict[str, Any]:
    integ = get_integration(integration_id)
    label = (integ or {}).get(f"{language}_label", integration_id)
    return {
        "card_id": f"success_{uuid.uuid4().hex[:6]}",
        "card_type": "setup_success",
        "integration_id": integration_id,
        "title": f"✅ {label} جاهز!" if language == "ar" else f"✅ {label} ready!",
        "account_info": account_info or {},
        "actions": [
            {"id": "continue_build", "label": "أكمل البناء" if language == "ar" else "Continue building", "primary": True},
        ],
    }


def card_cost_summary(integration_ids: List[str], language: str = "ar") -> Dict[str, Any]:
    """Summarize expected costs for chosen integrations."""
    items = []
    for iid in integration_ids:
        integ = get_integration(iid)
        if not integ: continue
        cost = integ.get("cost_to_user") or {}
        items.append({
            "integration_id": iid,
            "label": integ.get(f"{language}_label", iid),
            "free_tier": cost.get("free_tier") or ("مجاني" if language == "ar" else "Free"),
            "paid": cost.get("paid"),
        })
    return {
        "card_id": f"cost_{uuid.uuid4().hex[:6]}",
        "card_type": "cost_summary",
        "title": "💸 ملخّص التكلفة عليك" if language == "ar" else "💸 Cost summary",
        "items": items,
        "note_ar": "أغلب الخدمات لها طبقة مجانية كافية للبدء — لن تدفع شي إذا التزمت بحدودها." if language == "ar" else None,
        "note_en": "Most services have a generous free tier — you'll pay nothing if you stay within limits." if language == "en" else None,
    }


def card_skip_alternative(integration_id: str, alternative_text_ar: str, alternative_text_en: str = "") -> Dict[str, Any]:
    return {
        "card_id": f"skip_{uuid.uuid4().hex[:6]}",
        "card_type": "skip_alternative",
        "integration_id": integration_id,
        "title_ar": "تخطّى الإعداد؟",
        "title_en": "Skip setup?",
        "alternative_ar": alternative_text_ar,
        "alternative_en": alternative_text_en,
        "actions": [
            {"id": "use_alternative", "label": "نعم استخدم البديل", "primary": True},
            {"id": "back_to_setup", "label": "لا، دعنا نُكمل الإعداد"},
        ],
    }


def build_wizard_flow(integration_id: str, language: str = "ar") -> List[Dict[str, Any]]:
    """Build the full sequence of cards for one integration."""
    integ = get_integration(integration_id)
    if not integ:
        return []
    cards = [card_intro(integration_id, language)]
    for cred in integ.get("required_credentials") or []:
        cards.append(card_key_input(integration_id, cred, language))
    return cards
