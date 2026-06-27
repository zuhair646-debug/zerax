"""
🌍 i18n Cortex — multi-language support (ar, en, fr, es) with RTL/LTR auto.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.i18n")


SUPPORTED_LANGS = {
    "ar": {"name": "العربية", "dir": "rtl", "font_family": "Cairo, Tajawal, sans-serif"},
    "en": {"name": "English", "dir": "ltr", "font_family": "Inter, system-ui, sans-serif"},
    "fr": {"name": "Français", "dir": "ltr", "font_family": "Inter, system-ui, sans-serif"},
    "es": {"name": "Español", "dir": "ltr", "font_family": "Inter, system-ui, sans-serif"},
    "tr": {"name": "Türkçe", "dir": "ltr", "font_family": "Inter, system-ui, sans-serif"},
    "ur": {"name": "اردو", "dir": "rtl", "font_family": "Noto Nastaliq Urdu, sans-serif"},
}


def extract_translatable_strings(html: str) -> List[Dict[str, Any]]:
    """Pull translatable strings out of HTML. Skips data, code, style blocks."""
    # Strip <script>, <style>
    clean = re.sub(r"<(script|style)[\s\S]*?</\1>", "", html, flags=re.IGNORECASE)
    # Extract text content (>3 chars, not just whitespace/numbers)
    strings: List[Dict[str, Any]] = []
    for m in re.finditer(r">([^<>{}\n]{3,})<", clean):
        s = m.group(1).strip()
        if not s or s.isdigit() or len(s) < 3:
            continue
        if re.match(r"^[\d\s\W]+$", s):
            continue
        # de-dupe
        if any(x["text"] == s for x in strings):
            continue
        strings.append({"text": s, "key": _make_key(s, len(strings))})
    return strings


def _make_key(text: str, idx: int) -> str:
    """Make a stable JSON key from a string."""
    base = re.sub(r"[^a-z0-9]+", "_", text.lower())[:30].strip("_")
    if not base:
        base = f"t_{idx}"
    return f"{base}_{idx}"


async def translate_strings(strings: List[Dict[str, Any]], target_lang: str, source_lang: str = "ar") -> Dict[str, str]:
    """Translate a list of strings via Claude. Returns {key: translated_text}."""
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key or not strings:
        return {}
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        kv = {s["key"]: s["text"] for s in strings}
        prompt = (
            f"Translate the values of this JSON from {source_lang} to {target_lang}. "
            f"Keep the keys unchanged. Return JSON only:\n{json.dumps(kv, ensure_ascii=False)}"
        )
        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"i18n_{uuid.uuid4().hex[:8]}",
            system_message="You are a professional translator. Preserve tone and meaning.",
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        resp = await chat.send_message(UserMessage(text=prompt))
        raw = resp if isinstance(resp, str) else str(resp)
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"[i18n] translation failed: {e}")
    return {}


def render_html_with_lang(html: str, lang: str = "ar") -> str:
    """Inject lang + dir + font_family on <html>."""
    cfg = SUPPORTED_LANGS.get(lang, SUPPORTED_LANGS["ar"])
    if re.search(r'<html[^>]*\slang=', html[:500], re.IGNORECASE):
        return html
    return re.sub(
        r"<html\b",
        f'<html lang="{lang}" dir="{cfg["dir"]}" style="font-family:{cfg["font_family"]}"',
        html, count=1, flags=re.IGNORECASE,
    )


def language_switcher_snippet(current: str, options: List[str]) -> str:
    """Render a small language switcher in HTML."""
    items = []
    for lang in options:
        cfg = SUPPORTED_LANGS.get(lang, {"name": lang})
        active = "font-weight:bold;text-decoration:underline;" if lang == current else ""
        items.append(f'<a href="?lang={lang}" style="{active}padding:4px 8px;" data-lang="{lang}">{cfg["name"]}</a>')
    return f'<div class="lang-switcher" style="display:flex;gap:8px;align-items:center;">\n  {chr(10).join(items)}\n</div>'
