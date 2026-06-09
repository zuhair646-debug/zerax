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

logger = logging.getLogger("zerax.i18n.translate")

router = APIRouter(prefix="/i18n", tags=["i18n"])


class TranslateReq(BaseModel):
    text: str
    target: str  # ISO 639-1 / -2 code


class BatchTranslateReq(BaseModel):
    texts: list[str]
    target: str


class TranslateResp(BaseModel):
    translated: str
    cached: bool = False


class BatchTranslateResp(BaseModel):
    translations: list[str]


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


def _batch_translate_via_claude(texts: list[str], target_lang: str) -> Optional[list[str]]:
    """Translate up to ~40 short UI strings in one Claude call (much cheaper
    than N round-trips). Returns the translations in the same order."""
    key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not key or not texts:
        return None
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=key, timeout=30.0)
        lang_name = LANG_NAME_BY_CODE.get(target_lang, target_lang)
        # Number the inputs so Claude returns a parallel numbered list
        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        prompt = (
            f"Translate each numbered Arabic/English UI string into {lang_name} ({target_lang}). "
            "Return ONLY a numbered list in the SAME order — one translation per line, "
            "format `1. <translation>`. Keep each translation short, natural, and idiomatic — "
            "as a UI label/button/heading. Do not add explanations, transliterations, or quotes."
        )
        r = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            system=prompt,
            messages=[{"role": "user", "content": numbered}],
        )
        raw = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        # Parse numbered output back into a list of translations
        out: dict[int, str] = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            # match "12. translated text"
            i = line.find(".")
            if i < 0 or i > 4:
                continue
            num_part = line[:i].strip()
            if not num_part.isdigit():
                continue
            idx = int(num_part) - 1
            val = line[i+1:].strip().strip('"').strip("'")
            if 0 <= idx < len(texts) and val:
                out[idx] = val
        # Fill any missing slots with the source text (safe fallback)
        return [out.get(i, texts[i]) for i in range(len(texts))]
    except Exception:
        logger.exception("i18n batch translate failed")
        return None


@router.post("/translate-batch", response_model=BatchTranslateResp)
async def translate_batch(body: BatchTranslateReq):
    """Translate many strings at once. Used by the live DOM translator
    on the frontend to localize the entire page in 1-2 API calls."""
    texts = [(t or "").strip() for t in (body.texts or [])]
    texts = [t for t in texts if t]
    target = (body.target or "").strip().lower()
    if not texts:
        return BatchTranslateResp(translations=[])
    if not target:
        raise HTTPException(400, "target required")
    if target == "ar":
        return BatchTranslateResp(translations=texts)
    # Chunk to keep each Claude call under ~40 items
    out_all: list[str] = []
    chunk_size = 40
    for i in range(0, len(texts), chunk_size):
        chunk = texts[i:i+chunk_size]
        chunk_out = _batch_translate_via_claude(chunk, target) or chunk
        out_all.extend(chunk_out)
    return BatchTranslateResp(translations=out_all)
