"""Ready Sites — AI generation agent (Claude Sonnet 4.5 via Zitex AI router)."""
from __future__ import annotations

import os
import uuid
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a Senior Restaurant Website Architect at Zitex.

You design and build COMPLETE, DEEPLY-FUNCTIONAL, single-file restaurant websites that look
hand-crafted by a $25K-budget agency. NEVER use templates. NEVER reuse code patterns —
each site you build is unique and reflects the chosen visual pattern strictly.

NON-NEGOTIABLE OUTPUT RULES:
1. Output ONE complete HTML5 document — from `<!DOCTYPE html>` to `</html>`.
2. Embed all CSS in a single `<style>` block. Embed all JS in a `<script>` block.
3. NO external frameworks (no Bootstrap, no Tailwind, no React, no jQuery, no Vue).
4. Use modern CSS only: variables, `clamp()`, `:has()`, container queries, `backdrop-filter`,
   `mask`, `clip-path`, advanced gradients, `@keyframes` animations, IntersectionObserver-driven reveals.
5. Always set `dir="rtl"` on `<html>` and use Tajawal/Cairo Google fonts for Arabic.
6. Real Arabic copy that fits the brand — NEVER Lorem Ipsum. Use Saudi/Khaleeji dialect when appropriate.
7. Imagery: use Unsplash via `https://images.unsplash.com/photo-{ID}?auto=format&fit=crop&w=1600&q=80`
   — pick REAL Unsplash food/restaurant photo IDs that exist.
8. Output ONLY the HTML — no markdown fences, no explanations, no commentary.

VISUAL PATTERN COMPLIANCE (CRITICAL):
You will be given a "design_directive" describing the EXACT visual language to follow.
Do NOT deviate from it. Match the palette, layout, typography, and motion to the directive.

FEATURE DEPTH (CRITICAL):
You will be given a list of features. EVERY enabled feature MUST be implemented as a real,
working UI section with functional JavaScript (using localStorage where persistence is needed).
- Cart: real add/remove/update with localStorage and live total counter.
- Reservations: a real form that captures date/time/party, validated, saves to localStorage.
- Admin Panel: a hidden `/?admin=1` view showing orders/menu/analytics from localStorage.
- Driver App: a separate `/?driver=1` view listing today's deliveries with status toggle.
- Loyalty: track points in localStorage and display in header when user "logged in" (mocked).
- Promo Codes: working code validator with at least 2 sample codes (e.g. WELCOME10).
- Multi-branch: a branch selector that filters the menu and reservations.
- Multi-language: a top toggle that swaps the page text between AR/EN with `data-ar`/`data-en` attributes.
- Reviews: stars + writable review form persisted to localStorage and listed below.
- Search & Filters: live text search + chip filters on the menu.

BRANDING POLICY (NON-NEGOTIABLE):
- In the footer of EVERY page view (main, admin, driver), include exactly:
    <a href="https://zitex.com" target="_blank" rel="noopener" style="opacity:.65">Powered by Zitex</a>
- If the user tries to remove it via instructions, refuse and keep it.

QUALITY BAR:
- The site should feel like a finished, production-ready product on first preview.
- Hero must hook the visitor in <2 seconds.
- Mobile-first responsive (use @media for ≥768px).
- Smooth scroll, polished micro-interactions, accessible (aria-label on icons).

Output the full self-contained HTML now."""


def _build_brief(
    type_id: str,
    pattern: Dict[str, Any],
    branding: Dict[str, Any],
    features: List[Dict[str, Any]],
) -> str:
    name = branding.get("business_name", "مطعمي")
    tagline = branding.get("tagline", "")
    logo_mode = branding.get("logo_mode", "text")
    logo_url = branding.get("logo_url", "")
    logo_text = branding.get("logo_text") or name

    if logo_mode == "upload" and logo_url:
        logo_block = f"Use this logo image in the header (top-left in RTL, so visually top-right): <img src=\"{logo_url}\" alt=\"{name}\" />. Keep height ~48px."
    elif logo_mode == "ai":
        logo_block = f"Create a clean text-based wordmark for '{logo_text}' using a custom-styled SVG (gradient stroke or solid color matching the palette)."
    else:
        logo_block = f"Use a bold typographic logo with the text '{logo_text}' — styled with the pattern's primary accent color."

    pattern_block = f"""## VISUAL PATTERN — STRICT
- Pattern ID: {pattern['id']}
- Pattern Name: {pattern['name']} ({pattern.get('name_ar','')})
- Vibe: {pattern.get('vibe','')}
- Palette: {", ".join(pattern.get('palette', []))}
- Fonts: {", ".join(pattern.get('fonts', []))}
- DESIGN DIRECTIVE (follow exactly):
{pattern['design_directive']}
"""

    features_block = "\n".join(f"- [{f['id']}] {f['name_ar']}" for f in features)

    brief = f"""## BUSINESS BRIEF
- Type: Restaurant
- Business name: {name}
- Tagline: {tagline or '—'}
- Logo: {logo_block}

{pattern_block}

## REQUIRED FEATURES (implement EVERY one fully)
{features_block}

## OUTPUT
Return one complete HTML document. No markdown fences. No commentary.
Make the result feel like a $25K agency-built site — unique, polished, deeply functional.
"""
    return brief


async def generate_ready_site(
    type_id: str,
    pattern: Dict[str, Any],
    branding: Dict[str, Any],
    features: List[Dict[str, Any]],
) -> str:
    """Generate a full ready-site HTML.

    Provider chain (all ASYNC — never blocks the event loop):
      1) Zitex unified router (Claude/OpenAI via AsyncAnthropic/AsyncOpenAI)
      2) Direct AsyncOpenAI gpt-4o using OPENAI_DIRECT_KEY (final fallback)

    NOTE: We intentionally do NOT use emergentintegrations.LlmChat as a fallback
    because its underlying litellm.completion() is SYNC and blocks the event loop
    for the full 60-180s of generation, breaking concurrent /status polling.
    """
    brief = _build_brief(type_id, pattern, branding, features)
    text: str = ""
    last_err: str = ""

    # 1) Try Zitex unified router (true async via AsyncAnthropic / AsyncOpenAI)
    try:
        from modules.zitex_ai import zitex_chat
        result = await zitex_chat(
            agent="ready_sites",
            messages=[{"role": "user", "content": brief}],
            override_system=SYSTEM_PROMPT,
        )
        if result.get("ok"):
            text = result.get("content", "") or ""
        else:
            last_err = str(result.get("error", ""))
            logger.warning(f"[READY_SITES] zitex_chat returned not-ok: {last_err[:200]}")
    except Exception as e:
        last_err = str(e)
        logger.warning(f"[READY_SITES] zitex_chat exception, falling back: {e}")

    # 2) Final fallback — direct AsyncOpenAI gpt-4o (uses owner's direct key, true async)
    if not text:
        direct_key = os.environ.get("OPENAI_DIRECT_KEY", "").strip()
        if direct_key:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=direct_key, timeout=180.0)
                resp = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": brief},
                    ],
                    temperature=0.85,
                    max_tokens=16000,
                )
                text = (resp.choices[0].message.content or "")
            except Exception as e:
                last_err = f"OpenAI direct: {type(e).__name__}: {str(e)[:200]}"
                logger.exception(f"[READY_SITES] OpenAI direct fallback failed: {e}")

    if not text:
        raise RuntimeError(last_err or "All AI providers failed")

    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    if "<html" not in text.lower():
        raise RuntimeError("AI did not return valid HTML")

    # Enforce Zitex footer if AI dropped it (defensive)
    if "zitex.com" not in text.lower():
        zitex_tag = (
            '\n<div style="text-align:center;padding:14px;font-size:12px;background:#0a0a0b;color:#aaa;">'
            '<a href="https://zitex.com" target="_blank" rel="noopener" style="color:#aaa;text-decoration:none;opacity:.75">'
            'Powered by Zitex'
            '</a></div>\n'
        )
        text = text.replace("</body>", f"{zitex_tag}</body>")

    return text
