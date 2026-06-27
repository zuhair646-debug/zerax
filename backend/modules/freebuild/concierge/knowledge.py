"""
📚 Concierge Knowledge Loader — loads concierge_knowledge.json + intent detection.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.concierge.kb")

_KB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "concierge_knowledge.json"
_CACHE: Dict[str, Any] = {}


def _load() -> Dict[str, Any]:
    if "data" not in _CACHE or _CACHE.get("path_mtime") != _KB_PATH.stat().st_mtime:
        try:
            with open(_KB_PATH, encoding="utf-8") as f:
                _CACHE["data"] = json.load(f)
                _CACHE["path_mtime"] = _KB_PATH.stat().st_mtime
        except Exception as e:
            logger.error(f"failed to load concierge KB: {e}")
            _CACHE["data"] = {"integrations": {}}
    return _CACHE["data"]


def list_integrations() -> List[Dict[str, Any]]:
    data = _load()
    return [
        {"id": iid, "ar_label": i.get("ar_label", iid), "en_label": i.get("en_label", iid),
         "category": i.get("category", "")}
        for iid, i in data.get("integrations", {}).items()
    ]


def get_integration(integration_id: str) -> Optional[Dict[str, Any]]:
    return _load().get("integrations", {}).get(integration_id)


def detect_required_integrations(user_message: str, language: str = "auto") -> List[str]:
    """Detect which integrations are needed based on user message keywords."""
    if not user_message:
        return []
    msg = user_message.lower()
    matched: List[str] = []
    data = _load()
    for iid, integration in data.get("integrations", {}).items():
        triggers = integration.get("triggers", {})
        all_kw: List[str] = []
        if language in ("ar", "auto"):
            all_kw.extend(triggers.get("ar", []))
        if language in ("en", "auto"):
            all_kw.extend(triggers.get("en", []))
        if any(kw.lower() in msg for kw in all_kw):
            matched.append(iid)
    return matched


def render_setup_instructions_ar(integration_id: str) -> str:
    """Render full setup instructions in Arabic."""
    integ = get_integration(integration_id)
    if not integ:
        return ""
    lines = [f"## 🔑 إعداد: {integ.get('ar_label', integration_id)}\n"]
    prereqs = integ.get("prerequisites_ar") or []
    if prereqs:
        lines.append("**المتطلبات قبل البدء:**")
        for p in prereqs:
            lines.append(f"  • {p}")
        lines.append("")
    for cred in integ.get("required_credentials") or []:
        lines.append(f"### {cred.get('ar_label', cred['key'])}:")
        wtg = cred.get("where_to_get", {}).get("ar", "")
        if wtg:
            lines.append(wtg)
        lines.append("")
    cost = integ.get("cost_to_user") or {}
    if cost:
        lines.append("**التكلفة:**")
        if "free_tier" in cost: lines.append(f"  • 🆓 مجاني: {cost['free_tier']}")
        if "paid" in cost: lines.append(f"  • 💰 مدفوع: {cost['paid']}")
    mistakes = integ.get("common_mistakes_ar") or []
    if mistakes:
        lines.append("\n**أخطاء شائعة لتجنبها:**")
        for m in mistakes:
            lines.append(f"  ⚠️ {m}")
    return "\n".join(lines)


def render_setup_instructions_en(integration_id: str) -> str:
    """Render full setup instructions in English."""
    integ = get_integration(integration_id)
    if not integ:
        return ""
    lines = [f"## 🔑 Setup: {integ.get('en_label', integration_id)}\n"]
    prereqs = integ.get("prerequisites_en") or []
    if prereqs:
        lines.append("**Prerequisites:**")
        for p in prereqs:
            lines.append(f"  • {p}")
        lines.append("")
    for cred in integ.get("required_credentials") or []:
        lines.append(f"### {cred.get('en_label', cred['key'])}:")
        wtg = cred.get("where_to_get", {}).get("en", "")
        if wtg:
            lines.append(wtg)
        lines.append("")
    cost = integ.get("cost_to_user") or {}
    if cost:
        lines.append("**Cost:**")
        if "free_tier" in cost: lines.append(f"  • 🆓 Free: {cost['free_tier']}")
        if "paid" in cost: lines.append(f"  • 💰 Paid: {cost['paid']}")
    mistakes = integ.get("common_mistakes_en") or []
    if mistakes:
        lines.append("\n**Common pitfalls:**")
        for m in mistakes:
            lines.append(f"  ⚠️ {m}")
    return "\n".join(lines)
