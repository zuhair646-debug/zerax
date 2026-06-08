"""
On-demand translation endpoint backed by Claude.
Frontend caches translations in localStorage, so each unique string
is translated exactly once per language across all users of that browser.

POST /api/i18n/translate
  body: {"text": "...", "target": "fr"}
  resp: {"translated": "..."}
"""
from __future__ import annotations
import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .languages_meta import LANG_NAME_BY_CODE

logger = logging.getLogger("zitex.i18n.translate")

router = APIRouter(prefix="/i18n", tags=["i18n"])


class TranslateReq(BaseModel):
    text: str
    target: str  # ISO 639-1 / -2 code


class TranslateResp(BaseModel):
    translated: str
    cached: bool = False


def _translate_via_claude(text: str, target_lang: str) -> Optional[str]:
    key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        return None
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=key, timeout=20.0)
        lang_name = LANG_NAME_BY_CODE.get(target_lang, target_lang)
        prompt = (
            f"Translate the following Arabic/English UI text into {lang_name} ({target_lang}). "
            "Return ONLY the translated text — no quotes, no explanations, no transliteration. "
            "Keep it as a short, natural UI label/button text."
        )
        r = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=200,
            system=prompt,
            messages=[{"role": "user", "content": text}],
        )
        out = "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
        return out or None
    except Exception:
        logger.exception("i18n translate failed")
        return None


@router.post("/translate", response_model=TranslateResp)
async def translate(body: TranslateReq):
    text = (body.text or "").strip()
    target = (body.target or "").strip().lower()
    if not text or not target:
        raise HTTPException(400, "text and target required")
    if target == "ar":
        return TranslateResp(translated=text)
    out = _translate_via_claude(text, target)
    if not out:
        # Last-resort: return source so UI doesn't break
        return TranslateResp(translated=text)
    return TranslateResp(translated=out)
