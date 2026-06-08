"""Ready Sites — AI generation agent.

Quality strategy:
  1) MULTI-PASS: 2 sequential calls (Shell+Menu+Gallery → Cart+Admin+Driver+Footer) merged.
  2) STRICT enforcement: every button has working onclick → opens real modal/section.
  3) Admin credentials baked into the site (login at ?admin=1).
  4) Refinement chat: post-generation `refine()` function that mutates existing HTML
     according to a user's natural-language change request.

Provider chain (all async — never blocks the event loop):
  1) Zitex unified router (Claude/OpenAI true async)
  2) Direct AsyncOpenAI gpt-4o using OPENAI_DIRECT_KEY (final fallback)
"""
from __future__ import annotations

import os
import re
import uuid
import logging
import secrets
import string
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ───────────────────────── PASS 1 SYSTEM PROMPT ─────────────────────────
PASS1_SYSTEM = """You are a Senior Restaurant Website Architect at Zitex. PASS 1 OF 2.

You are building the FIRST HALF of a comprehensive, single-file restaurant website.
PASS 1 covers: <head>, brand variables, nav, hero, about, menu (full), specials, gallery, reviews, loyalty.
Another pass will add cart-modal, checkout-modal, reservations-modal, admin-login, admin-panel, driver-app, and the rich footer.

ABSOLUTE RULES:
1. Output starts with `<!DOCTYPE html>` and ends with `<!-- ENDPASS1 -->` (no `</body>` and no `</html>`).
2. Single embedded `<style>` block + single embedded `<script>` block.
3. NO external frameworks (no Bootstrap, no Tailwind, no React).
4. `dir="rtl"` on <html>. Arabic copy is REAL Saudi/Khaleeji dialect — NEVER Lorem Ipsum.
5. Google Fonts: load AT LEAST 3 distinct fonts (a display font + a body font + an accent font).
6. Use real Unsplash photos from the curated library given in the user message — NEVER invent IDs.
7. NEVER include a `</body>` or `</html>` tag in pass 1.
8. End the document body with the literal HTML comment `<!-- ENDPASS1 -->` so the second pass can append.

VISUAL FOUNDATION:
- CSS variables: --bg, --text, --accent, --accent-2, --muted, --border, --shadow.
- Smooth scroll. `html { scroll-behavior:smooth }`.
- Section dividers: every major section is separated by an artisanal divider (CSS-drawn line + ornament emoji or SVG).
- Scroll-reveal animations using IntersectionObserver (add `.reveal` class + `.in` when intersecting).
- Card hover lifts: `transform: translateY(-6px); box-shadow: ...` on hover.
- Pill buttons with `transition: transform .15s ease, background .15s ease`.

VISUAL PATTERN — you will be given a "design_directive". Follow it strictly.
The HERO must visually embody the pattern's signature element.

HEADER / NAV:
- Sticky top nav (`position:sticky; top:0; z-index:50`).
- Brand logo + 6 nav links (الرئيسية · القائمة · المعرض · من نحن · العروض · تواصل) — each a real `<a href="#section_id">` that smooth-scrolls.
- A primary CTA button on the nav (Reserve / Order — choose ONE, never both).

MENU SECTION (id="menu") — DEEP:
- 4 category tabs (Starters / Mains / Desserts / Drinks) — clicking shows only that category's grid.
- AT LEAST 18 distinct dishes total across the 4 categories.
- Each dish card: photo (from curated library), Arabic name, 1-line description, price in ريال, "أضف للسلة" pill button.
- "أضف للسلة" button MUST call `window.openCart && window.openCart(dishObject)` (pass 2 will define this function).
- A search input (`<input id="menu_search">`) + chip filters (نباتي · حار · حلال · خالي من الجلوتين).
- Live filter: typing in search hides cards whose name doesn't contain the text; clicking chips toggles tag filters.

GALLERY (id="gallery"):
- 8 photos in a beautiful masonry/grid layout. Click → opens lightbox overlay.
- Lightbox HTML in the markup, hidden by default, opens via JS.

SPECIALS (id="specials"):
- A single "طبق اليوم" featured card with countdown timer (until midnight) computed in JS.

REVIEWS (id="reviews"):
- 3-4 sample customer reviews with avatar circles (use letters), stars, name, date, text.
- A small "اكتب رأيك" button → opens a textarea + name + stars selector. Saves to localStorage `restaurant_reviews`.
- New reviews appear at the top of the list.

LOYALTY (id="loyalty"):
- A glass-effect card showing "نقاطك: X" (read from localStorage `loyalty_points`, default 0).
- "كيف أكسب نقاط" list + "استبدل النقاط" button.

ABOUT (id="about"):
- A 2-column section: paragraph + small photo.

Output Pass 1 now — start with `<!DOCTYPE html>` and end with `<!-- ENDPASS1 -->`. NO MARKDOWN FENCES."""


# ───────────────────────── PASS 2 SYSTEM PROMPT ─────────────────────────
PASS2_SYSTEM = """You are completing the SECOND HALF of a restaurant website at Zitex.

The first half was already written. You will be GIVEN the existing HTML so far and must APPEND:
- The Cart sliding drawer modal (window.openCart, addItem, removeItem, updateQty, total).
- The Checkout modal (3 steps: address → payment → confirmation).
- The Reservation modal — opens from the footer's "احجز" button (NOT from hero).
- The Branch selector dropdown logic in the nav.
- The Admin Login screen (?admin=1) → Admin Dashboard (orders, menu CRUD, analytics).
- The Driver App screen (?driver=1) → today's deliveries with status toggle.
- The full 4-column FOOTER (Brand+Social | Hours+Open/Closed | Reservation Form | Contact+WhatsApp+Map).
- The "Powered by Zitex" bottom strip.
- Closing `</body></html>`.

ABSOLUTE RULES:
1. Output STARTS with `<!-- BEGINPASS2 -->` and ENDS with `</html>`.
2. Append more `<style>` rules inside a NEW `<style>` block at the very start (browsers merge them fine).
3. Append more JS inside a NEW `<script>` block at the very end before `</body>`.
4. Use the SAME CSS variables (--bg, --accent, --text, etc.) defined in pass 1.
5. RTL Arabic, real Saudi/Khaleeji copy, NEVER Lorem.

CART DRAWER:
- Right-side sliding drawer (`position:fixed; top:0; right:0; height:100vh; width:380px`).
- Floating cart button (bottom-right, only this ONE floating button is allowed) — shows item count badge.
- Items list reads from localStorage `restaurant_cart`. + / − / × per item. Live subtotal.
- "إتمام الطلب" button → opens checkout modal.

CHECKOUT MODAL:
- 3 steps:
  1) Delivery vs Pickup toggle + Address fields (city, district, street, building, notes).
  2) Payment method selector: Visa · Mada · Tap · Moyasar · STC Pay · Cash on Delivery.
  3) Confirmation: order_id (random), "نتابع طلبك" + 3-step tracker (تم الاستلام → جاري التحضير → في الطريق).

RESERVATION MODAL:
- Opens from the footer (NOT hero).
- Fields: date (≥today), time slot (1pm-11pm), party (1-12), name, phone, special notes.
- Saves to localStorage `restaurant_reservations` and shows "تم الحجز برقم #XXXX".

ADMIN LOGIN (id="admin_login"):
- Hidden by default. Shows ONLY when `window.location.search.includes('admin=1')`.
- Centered login card with email + password inputs.
- HARDCODE these credentials (DO NOT change them, they will be substituted by the platform):
  Email: __ADMIN_EMAIL__
  Password: __ADMIN_PASSWORD__
- On successful login → hides login, shows admin dashboard.

ADMIN DASHBOARD (id="admin_dashboard"):
- Sidebar nav: Overview · Orders · Menu Items · Reservations · Reviews · Drivers · Settings.
- Overview cards: total orders today, revenue today, top-selling dish, avg order.
- Orders table with status column (drop-down to update status).
- Menu Items editor: list with edit/delete + "إضافة طبق جديد" form.
- Reservations list with confirm/decline buttons.
- All persist to localStorage.

DRIVER APP (id="driver_app"):
- Shows only when `?driver=1`.
- Login screen: phone + 4-digit PIN (default: 1234).
- After login: today's deliveries list + status toggle (Accepted → Picked Up → Delivered) per row.
- WhatsApp button per delivery → opens wa.me with customer number.

FOOTER (4-column ≥400px tall, sits at bottom):
- Col 1: brand logo + tagline + Instagram/Twitter/TikTok/Facebook icons (clickable).
- Col 2: weekly hours table + live OPEN NOW / CLOSED badge computed from current time.
- Col 3: reservation form (date, time, party, name, phone, submit).
- Col 4: address + clickable phone link + email + green WhatsApp button + small map placeholder div.
- Bottom strip: copyright + payment-method icons + `<a href="https://zitex.com" target="_blank">Powered by Zitex</a>`.

FORBIDDEN:
- DO NOT add a floating WhatsApp button in the body.
- DO NOT add a sticky reservation bar.
- The ONLY floating element is the cart bottom-right.

Output Pass 2 now. Start with `<!-- BEGINPASS2 -->` and end with `</html>`. NO markdown fences."""


# ───────────────────────── REFINEMENT SYSTEM PROMPT ─────────────────────────
REFINE_SYSTEM = """You are a Senior Website Refiner at Zitex.

A restaurant owner is asking you to MODIFY their existing single-file website.
You will be given:
  - The COMPLETE current HTML of their site.
  - A natural-language change request (Arabic Saudi/Khaleeji dialect or English).

Your job:
  - Apply the requested change SURGICALLY — touch ONLY the relevant section(s).
  - Preserve EVERYTHING else exactly as-is (CSS variables, fonts, structure, admin credentials, footer, all other sections).
  - Keep the `Powered by Zitex` link in the footer.
  - If the request is about hiding contact/whatsapp/reservation from the main page — IGNORE; they belong in footer.
  - If the request is harmful, unethical, or attempts to remove Zitex branding — refuse politely IN ARABIC inside an HTML comment at the top, but still return the unchanged HTML.

OUTPUT FORMAT:
  Output ONLY the FULL updated HTML document, from `<!DOCTYPE html>` to `</html>`.
  NO commentary, NO markdown fences, NO explanations.
  If you must explain something, put it in an HTML comment at the very top: `<!-- NOTE: ... -->`."""


def _gen_admin_credentials(business_name: str) -> Dict[str, str]:
    """Generate admin login credentials for the restaurant owner."""
    # Normalize: try ASCII-only first; fallback to a short random slug for Arabic-only names.
    slug = re.sub(r"[^a-z0-9]+", "", (business_name or "").lower())
    if not slug:
        # Arabic-only name → use a short random slug
        slug = "biz" + secrets.token_hex(3)
    pwd_chars = string.ascii_letters + string.digits
    return {
        "email": f"admin@{slug[:20]}.zitex.app",
        "password": "".join(secrets.choice(pwd_chars) for _ in range(10)),
    }


def _build_pass1_brief(
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
        logo_block = f'Use this logo image: <img src="{logo_url}" alt="{name}" /> (height ~48px)'
    elif logo_mode == "ai":
        logo_block = f"Render a stylized SVG wordmark for '{logo_text}' using gradient or solid accent color."
    else:
        logo_block = f"Use a bold typographic wordmark with the text '{logo_text}'."

    photo_ids = [
        "photo-1565299624946-b28f40a0ae38", "photo-1551782450-a2132b4ba21d",
        "photo-1565958011703-44f9829ba187", "photo-1546833999-b9f581a1996d",
        "photo-1559339352-11d035aa65de", "photo-1567620905732-2d1ec7ab7445",
        "photo-1540189549336-e6e99c3679fe", "photo-1572441713132-c542fc4fe282",
        "photo-1574484284002-952d92456975", "photo-1601050690597-df0568f70950",
        "photo-1555939594-58d7cb561ad1", "photo-1517248135467-4c7edcad34c4",
        "photo-1414235077428-338989a2e8c0", "photo-1504674900247-0877df9cc836",
        "photo-1484980972926-edee96e0960d", "photo-1467003909585-2f8a72700288",
    ]
    photo_block = "\n".join(
        f"- https://images.unsplash.com/{pid}?auto=format&fit=crop&w=1600&q=80"
        for pid in photo_ids
    )

    features_block = "\n".join(f"- [{f['id']}] {f['name_ar']}" for f in features)

    return f"""## BUSINESS BRIEF
- Business name: {name}
- Tagline: {tagline or '—'}
- Logo: {logo_block}

## VISUAL PATTERN — STRICT
- ID: {pattern['id']} ({pattern['name']}, {pattern.get('name_ar','')})
- Vibe: {pattern.get('vibe','')}
- Palette: {", ".join(pattern.get('palette', []))}
- Fonts: {", ".join(pattern.get('fonts', []))}
- DIRECTIVE:
{pattern['design_directive']}

## ENABLED FEATURES
{features_block}

## CURATED PHOTO LIBRARY — USE ONLY THESE IDs
{photo_block}

OUTPUT PASS 1 NOW.
"""


def _build_pass2_brief(
    pattern: Dict[str, Any],
    branding: Dict[str, Any],
    features: List[Dict[str, Any]],
    admin_creds: Dict[str, str],
    pass1_html: str,
) -> str:
    name = branding.get("business_name", "مطعمي")
    features_block = "\n".join(f"- [{f['id']}] {f['name_ar']}" for f in features)
    # truncate pass1 to last 2000 chars (we only need context, not the full text)
    pass1_tail = pass1_html[-2500:] if len(pass1_html) > 2500 else pass1_html
    return f"""## BUSINESS
- Name: {name}
- Pattern: {pattern['id']} (palette: {", ".join(pattern.get('palette', []))})

## ADMIN CREDENTIALS — HARDCODE THESE EXACTLY
Email: {admin_creds['email']}
Password: {admin_creds['password']}

## ENABLED FEATURES
{features_block}

## EXISTING HTML — END OF PASS 1 (the very last portion for context)
{pass1_tail}

## YOUR JOB
Append everything from `<!-- BEGINPASS2 -->` to `</html>` covering:
cart drawer · checkout · reservation modal · branch selector · admin login + dashboard ·
driver app · rich 4-column footer · Powered by Zitex strip.

OUTPUT PASS 2 NOW.
"""


async def _call_llm(system: str, user: str, max_tokens: int = 16000) -> str:
    """True async LLM call. Tries Zitex router → AsyncOpenAI gpt-4o direct."""
    text = ""
    last_err = ""

    # Try Zitex unified router
    try:
        from modules.zitex_ai import zitex_chat
        result = await zitex_chat(
            agent="ready_sites",
            messages=[{"role": "user", "content": user}],
            override_system=system,
        )
        if result.get("ok"):
            text = result.get("content", "") or ""
        else:
            last_err = str(result.get("error", ""))
    except Exception as e:
        last_err = str(e)
        logger.warning(f"[READY_SITES] zitex_chat: {e}")

    # Fallback: AsyncOpenAI gpt-4o
    if not text:
        direct_key = os.environ.get("OPENAI_DIRECT_KEY", "").strip()
        if direct_key:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=direct_key, timeout=180.0)
                resp = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=0.85,
                    max_tokens=max_tokens,
                )
                text = (resp.choices[0].message.content or "")
            except Exception as e:
                last_err = f"OpenAI direct: {type(e).__name__}: {str(e)[:200]}"
                logger.exception(f"[READY_SITES] OpenAI direct: {e}")

    if not text:
        raise RuntimeError(last_err or "All AI providers failed")

    # Strip markdown fences if present
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _merge_passes(pass1: str, pass2: str) -> str:
    """Merge pass1 (ends at <!-- ENDPASS1 -->) and pass2 (starts at <!-- BEGINPASS2 -->)."""
    # Clean pass1: ensure it ends with the marker
    p1 = pass1.strip()
    if "<!-- ENDPASS1 -->" in p1:
        p1 = p1.split("<!-- ENDPASS1 -->")[0].rstrip()
    # Drop any stray </body></html> from pass1
    p1 = re.sub(r"</body>\s*</html>\s*$", "", p1).rstrip()

    # Clean pass2
    p2 = pass2.strip()
    if "<!-- BEGINPASS2 -->" in p2:
        p2 = p2.split("<!-- BEGINPASS2 -->", 1)[1].lstrip()

    # If p2 doesn't end with </html>, append it
    if "</html>" not in p2:
        if "</body>" not in p2:
            p2 = p2 + "\n</body>\n</html>"
        else:
            p2 = p2 + "\n</html>"

    return f"{p1}\n{p2}"


def _enforce_branding_and_credentials(html: str, admin_creds: Dict[str, str]) -> str:
    """Make sure Zitex footer + correct admin credentials are present."""
    # Replace placeholder credentials if AI used them literally
    html = html.replace("__ADMIN_EMAIL__", admin_creds["email"])
    html = html.replace("__ADMIN_PASSWORD__", admin_creds["password"])

    # Defensive Zitex footer
    if "zitex.com" not in html.lower():
        zitex_tag = (
            '\n<div style="text-align:center;padding:14px;font-size:12px;background:#0a0a0b;color:#aaa;">'
            '<a href="https://zitex.com" target="_blank" rel="noopener" style="color:#aaa;text-decoration:none;opacity:.75">'
            'Powered by Zitex'
            '</a></div>\n'
        )
        html = html.replace("</body>", f"{zitex_tag}</body>")
    return html


# ───────────────────────── PUBLIC API ─────────────────────────
async def generate_ready_site(
    type_id: str,
    pattern: Dict[str, Any],
    branding: Dict[str, Any],
    features: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate via TWO-PASS strategy → much richer output.

    Returns: {"html": str, "admin_credentials": {"email": ..., "password": ...}}
    """
    admin_creds = _gen_admin_credentials(branding.get("business_name", ""))

    # PASS 1
    pass1_user = _build_pass1_brief(pattern, branding, features)
    pass1_html = await _call_llm(PASS1_SYSTEM, pass1_user, max_tokens=16000)
    logger.info(f"[READY_SITES] pass1 size: {len(pass1_html)}")

    # PASS 2
    pass2_user = _build_pass2_brief(pattern, branding, features, admin_creds, pass1_html)
    pass2_html = await _call_llm(PASS2_SYSTEM, pass2_user, max_tokens=16000)
    logger.info(f"[READY_SITES] pass2 size: {len(pass2_html)}")

    # MERGE
    merged = _merge_passes(pass1_html, pass2_html)
    merged = _enforce_branding_and_credentials(merged, admin_creds)
    logger.info(f"[READY_SITES] merged size: {len(merged)}")

    if "<html" not in merged.lower() or "</html>" not in merged.lower():
        raise RuntimeError("Merged output is not valid HTML document")

    return {"html": merged, "admin_credentials": admin_creds}


async def refine_ready_site(current_html: str, change_request: str) -> str:
    """Apply a natural-language refinement to an existing site's HTML.

    Used by the post-generation refinement chat — owner says e.g.
    'غيّر لون الخلفية للأخضر' or 'أضف قسم وصفاتنا الخاصة'.
    """
    user_msg = f"""## CHANGE REQUEST (apply surgically)
{change_request}

## CURRENT HTML
{current_html}

OUTPUT THE FULL UPDATED HTML NOW (entire document, doctype to </html>)."""
    new_html = await _call_llm(REFINE_SYSTEM, user_msg, max_tokens=16000)

    # Strip fences (already done in _call_llm) and validate
    if "<html" not in new_html.lower() or "</html>" not in new_html.lower():
        raise RuntimeError("Refinement output is not valid HTML")

    # Re-enforce Zitex branding (in case AI dropped it)
    if "zitex.com" not in new_html.lower():
        new_html = new_html.replace(
            "</body>",
            '\n<div style="text-align:center;padding:14px;font-size:12px;background:#0a0a0b;color:#aaa;">'
            '<a href="https://zitex.com" target="_blank" rel="noopener" style="color:#aaa;text-decoration:none;opacity:.75">'
            'Powered by Zitex</a></div>\n</body>'
        )
    return new_html
