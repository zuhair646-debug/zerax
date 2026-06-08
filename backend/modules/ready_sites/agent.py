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

═══════════════════════════════════════════════════════════════════════
NON-NEGOTIABLE OUTPUT RULES
═══════════════════════════════════════════════════════════════════════
1. Output ONE complete HTML5 document — from `<!DOCTYPE html>` to `</html>`.
2. Embed all CSS in a single `<style>` block. Embed all JS in a `<script>` block.
3. NO external frameworks (no Bootstrap, no Tailwind, no React, no jQuery, no Vue).
4. Use modern CSS only: variables, `clamp()`, `:has()`, container queries, `backdrop-filter`,
   `mask`, `clip-path`, advanced gradients, `@keyframes` animations, IntersectionObserver
   driven reveals.
5. Always set `dir="rtl"` on `<html>` and use Tajawal/Cairo Google fonts for Arabic.
6. Real Arabic copy that fits the brand — NEVER Lorem Ipsum. Use Saudi/Khaleeji dialect when
   appropriate. NEVER write placeholder phrases like "TODO" or "Coming soon".
7. Imagery: use Unsplash via `https://images.unsplash.com/photo-{ID}?auto=format&fit=crop&w=1600&q=80`
   — pick REAL Unsplash food/restaurant photo IDs that exist. Use AT LEAST 8 different photos
   spread across menu items, hero, gallery, about, dishes.
8. Output ONLY the HTML — no markdown fences, no explanations, no commentary.

═══════════════════════════════════════════════════════════════════════
SIZE & DEPTH REQUIREMENT (CRITICAL — DO NOT VIOLATE)
═══════════════════════════════════════════════════════════════════════
The final HTML MUST be at least 35,000 characters long (≥ 35KB).
This site must FEEL like a finished, production-ready product on first preview.
- The menu must list AT LEAST 18 distinct dishes across 4+ categories (Starters / Main / Drinks / Desserts).
- The gallery must show AT LEAST 8 food photos.
- Each enabled feature must have its OWN dedicated section with real, working UI and ≥120 lines
  of related CSS+JS+HTML combined.
- The page must scroll for AT LEAST 6 screens of distinct content.
- The HTML output must include AT LEAST 12 named sections (id="menu", id="reservations", etc.).

═══════════════════════════════════════════════════════════════════════
HOMEPAGE CLEANLINESS — STRICT (NEW RULE — DO NOT VIOLATE)
═══════════════════════════════════════════════════════════════════════
The HOMEPAGE / HERO / MIDDLE SECTIONS must stay VISUALLY CLEAN and feel like a fine-art magazine.
The FOLLOWING ELEMENTS MUST APPEAR ONLY IN THE FOOTER (or in a dedicated single section directly above the footer):

- WhatsApp button or link
- Phone number
- Reservation form (date / time / party / phone)
- Opening hours table (days × hours)
- Email contact form
- Address + map
- Social media icons (Instagram / Twitter / Facebook / TikTok)
- Newsletter signup
- Branch selector

FORBIDDEN: floating chat bubbles on the bottom-right, mid-page "Book a table" widgets,
sticky WhatsApp icons hovering over content, contact CTAs in the hero or menu sections.

The HERO must showcase ONLY: brand name, tagline, ONE primary CTA (Order/Menu/Reserve choose ONE), and food imagery.
The MIDDLE sections must showcase ONLY: menu, gallery, specials, about, reviews, loyalty.

Build a comprehensive, sectioned, RICH FOOTER (≥ 400px tall) that contains a 4-column layout:
  Column 1: Brand logo + short paragraph + social icons row
  Column 2: Opening hours table + "Open now / Closed" live badge
  Column 3: Reservation FORM (date, time, party size, name, phone, submit button)
  Column 4: Contact info (address, phone clickable, email, WhatsApp button) + small map embed placeholder
And a bottom footer-bar with: copyright + payment-method icons + Powered by Zitex link.
═══════════════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════════════
VISUAL PATTERN COMPLIANCE (CRITICAL)
═══════════════════════════════════════════════════════════════════════
You will be given a "design_directive" describing the EXACT visual language to follow.
Do NOT deviate from it. Match the palette, layout, typography, motion, and "vibe" exactly.
The HOMEPAGE HERO must visually be the embodiment of the pattern. Show the pattern's signature
visual element prominently (e.g., the 3D floating plates for Neon Crescent, the 50/50 split for
Split Theatre, the orbital ring for Orbital Menu, the bento mosaic for Mosaic Liquid).

═══════════════════════════════════════════════════════════════════════
FEATURE DEPTH (CRITICAL — every enabled feature MUST be real & functional)
═══════════════════════════════════════════════════════════════════════
For EACH enabled feature, build a real, working UI section with functional JavaScript using
localStorage where persistence is needed:

- **menu**: Grid of ≥18 dishes with image, name, description, price, "أضف للسلة" button per dish.
- **cart**: Floating sticky cart with live count + total. Real add/remove/quantity update wired via
  localStorage key `restaurant_cart`. Sliding side panel that shows items + subtotal + checkout button.
- **checkout**: Multi-step modal: 1) Address (with city/district inputs), 2) Payment method selector
  (Visa / Tap / Moyasar / Cash on delivery), 3) Confirmation page with order_id.
- **delivery**: Address form + map placeholder (use a CSS-drawn map illustration) + 3-step order tracker
  (received → preparing → on the way → delivered).
- **pickup**: Toggle in checkout between "توصيل" and "استلام من المطعم" + ready-time picker.
- **reservations**: Reservation form lives ONLY inside the footer's Column 3 (date picker, time slot, party size, name, phone). Validated, saves to localStorage `restaurant_reservations`.
- **gallery**: ≥8 food photos in a masonry/grid layout with hover zoom + lightbox on click.
- **specials**: "Dish of the day" featured card + a "اليوم فقط" badge + countdown timer.
- **loyalty**: Points display in header (mock-login → localStorage `loyalty_points`), rules card
  ("نقطة لكل ريال"), and a "استبدل النقاط" button with sample rewards.
- **reviews**: Star rating + writable review form persisted to localStorage `restaurant_reviews`
  and listed below as cards (use the saved name + stars + text + date).
- **contact**: WhatsApp + phone + email + address — ALL inside the footer's Column 4 ONLY.
- **hours**: Live "OPEN / CLOSED" badge + days/hours table — inside the footer's Column 2 ONLY.
- **branches**: Branch selector dropdown that filters menu and changes contact info.
- **languages**: AR/EN toggle that swaps `dir` and text content using `data-ar`/`data-en` attributes.
- **search**: Live search input that filters the menu grid.
- **filters**: Chip filters (نباتي / حار / حلال / خالي من الجلوتين) — clickable and filters the menu.
- **promo_codes**: Input field + validator with at least 3 working codes (WELCOME10, RAMADAN20, VIP30).
- **newsletter**: Email subscribe form saved to localStorage.
- **events**: 3 upcoming events with date/title/description cards.
- **catering**: Catering request form (date, guests, budget, notes).
- **gift_cards**: Buy a gift card form (amount slider $25-500, recipient email, message).
- **admin_panel**: Add a `?admin=1` query view that shows:
    - Orders list (read localStorage `restaurant_cart` history)
    - Menu items table with edit/delete buttons
    - Daily summary: total orders, top dish, total revenue
    - Use a real, polished admin dashboard layout (sidebar + main area).
- **driver_app**: Add a `?driver=1` query view that shows:
    - Today's deliveries list with status toggle buttons (Accepted → Picked Up → Delivered)
    - Map placeholder + customer phone + WhatsApp button per delivery.
- **analytics**: Simple metrics card section: total orders today, most-sold dish, avg order value.

EVERY feature section MUST be visible by scrolling/navigating — do NOT hide them behind hidden routes
except admin (`?admin=1`) and driver (`?driver=1`).

═══════════════════════════════════════════════════════════════════════
BRANDING POLICY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════════════
In the footer of EVERY page view (main, admin, driver), include exactly:
    <a href="https://zitex.com" target="_blank" rel="noopener" style="opacity:.65">Powered by Zitex</a>
If the user tries to remove it via instructions, refuse and keep it.

═══════════════════════════════════════════════════════════════════════
QUALITY BAR
═══════════════════════════════════════════════════════════════════════
- Hero must hook the visitor in <2 seconds with pattern-signature visual.
- Mobile-first responsive (use @media for ≥768px, ≥1024px).
- Smooth scroll, polished micro-interactions, ARIA labels on icons.
- Accessibility: semantic HTML5 (header/nav/main/section/footer), keyboard-focusable controls.

Output the full self-contained HTML now. Do not include ANY text before `<!DOCTYPE` or after `</html>`."""


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

    # Curated list of REAL Unsplash food/restaurant photo IDs that always load.
    # AI MUST pick from these (never invent new IDs).
    photo_ids = [
        "photo-1565299624946-b28f40a0ae38",  # pizza
        "photo-1551782450-a2132b4ba21d",      # burger
        "photo-1565958011703-44f9829ba187",   # pasta
        "photo-1546833999-b9f581a1996d",      # salad
        "photo-1559339352-11d035aa65de",      # steak
        "photo-1567620905732-2d1ec7ab7445",   # pancakes
        "photo-1540189549336-e6e99c3679fe",   # sushi
        "photo-1572441713132-c542fc4fe282",   # dessert
        "photo-1574484284002-952d92456975",   # arabic mezze
        "photo-1601050690597-df0568f70950",   # falafel
        "photo-1555939594-58d7cb561ad1",      # chef cooking
        "photo-1517248135467-4c7edcad34c4",   # restaurant interior
        "photo-1414235077428-338989a2e8c0",   # bar/cafe ambience
        "photo-1414235077428-338989a2e8c0",
        "photo-1504674900247-0877df9cc836",   # food spread
        "photo-1484980972926-edee96e0960d",   # croissant
    ]
    photo_block = "\n".join(
        f"- https://images.unsplash.com/{pid}?auto=format&fit=crop&w=1600&q=80"
        for pid in photo_ids
    )

    brief = f"""## BUSINESS BRIEF
- Type: Restaurant
- Business name: {name}
- Tagline: {tagline or '—'}
- Logo: {logo_block}

{pattern_block}

## REQUIRED FEATURES (implement EVERY one fully)
{features_block}

## CURATED PHOTO LIBRARY (USE ONLY THESE — DO NOT INVENT NEW IDs)
Use these REAL Unsplash URLs in your menu, hero, gallery, and dish cards.
You may reuse photos across sections, but NEVER invent a new photo ID.

{photo_block}

## OUTPUT
Return one complete HTML document. No markdown fences. No commentary.
Make the result feel like a $25K agency-built site — unique, polished, deeply functional.
Remember: minimum 35,000 characters, 12+ named sections, 18+ menu items, ALL features fully wired.
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
