"""Ready Sites — AI generation agent.

Hybrid quality strategy (post Feb 2026):
  • Python DATA FACTORY (data_factory.py) generates ALL seed data deterministically:
    branding, hours, 6 categories, 60 products w/ Saudi pricing + calories + ingredients,
    30 sample orders, 20 customers, 5 drivers, analytics, reviews.
  • The seed JS (`window.SITE = {...}; window.ADMIN_DATA = {...};`) is INJECTED into
    the AI's pass 1 output AT THE TOP OF THE <script> block deterministically — so the
    AI doesn't waste any of its 16K token budget on data generation.
  • AI focuses ONLY on the UI shell: HTML structure, CSS, routing JS, modals,
    admin dashboard layout. Result: ALWAYS 60+ products, 30 orders, 20 customers.

Provider chain (all async): zitex_chat → AsyncOpenAI gpt-4o direct.
"""
from __future__ import annotations

import os
import re
import uuid
import logging
import secrets
import string
from typing import Any, Dict, List, Optional

from .data_factory import (
    seed_restaurant, seed_to_js,
    render_categories_html, render_products_html,
    render_admin_orders_html, render_admin_customers_html,
    render_admin_full_app, render_cart_module,
    render_zitex_enhancements,
)

logger = logging.getLogger(__name__)


# ───────────────────────── PASS 1 SYSTEM PROMPT ─────────────────────────
PASS1_SYSTEM = """You are a Senior Restaurant Website Architect at Zitex. PASS 1 OF 2.

You are building the FIRST HALF of a deeply-functional restaurant SPA (Single Page App in one HTML file).

PASS 1 covers: <head>, brand variables, sticky nav, hero, about, full DATA LAYER, menu (categories grid), reviews, loyalty.

═══════════════════════════════════════════════════════════════════
ABSOLUTE OUTPUT RULES
═══════════════════════════════════════════════════════════════════
1. Output starts with `<!DOCTYPE html>` and ends with `<!-- ENDPASS1 -->`.
2. NO `</body>` or `</html>` tags in pass 1.
3. One `<style>` block + one `<script>` block.
4. `dir="rtl"`, Arabic Saudi/Khaleeji dialect, NEVER Lorem.
5. 3+ Google Fonts (display + body + accent).
6. NO markdown fences.

═══════════════════════════════════════════════════════════════════
DATA LAYER (MOST CRITICAL — this powers EVERYTHING)
═══════════════════════════════════════════════════════════════════
At the START of your <script> tag, define `window.SITE` as a global constant containing:

```js
window.SITE = {
  branding: { name: "...", tagline: "...", phone: "+966512345678", whatsapp: "+966512345678",
              email: "info@brand.com", address: "...", city: "الرياض", maps_query: "..." },
  hours: { saturday: {open:"11:00",close:"23:00"}, sunday: {...}, ... },
  categories: [
    { id:"pizza", name:"البيتزا", desc:"...", img:"https://images.unsplash.com/photo-..." },
    { id:"broast", name:"بروست", desc:"...", img:"..." },
    { id:"salads", name:"سلطات", desc:"...", img:"..." },
    { id:"meat",   name:"لحوم",   desc:"...", img:"..." },
    { id:"chicken",name:"دجاج",   desc:"...", img:"..." },
    { id:"shawarma",name:"شاورما",desc:"...",img:"..." }
  ],
  products: [
    // ≥10 products PER category × 6 categories = 60+ items total
    // Each product:
    { id:"p1", category:"pizza", name:"بيتزا مارجريتا", price:35, calories:850,
      desc:"طماطم سان مارزانو، موزاريلا الجاموس الطازج، أوراق ريحان، زيت زيتون بكر",
      ingredients:["دقيق إيطالي 00","صلصة طماطم","موزاريلا","ريحان","زيت زيتون"],
      tags:["نباتي","حلال"], img:"https://images.unsplash.com/photo-...",
      prep_time:"15-20 دقيقة", rating:4.7, reviews_count:142 },
    ... 60+ total products ...
  ],
  reviews: [ {name, stars, date, text}, ... 4-5 sample reviews ]
};
```

Generate REAL prices in ر.س. matching market rates (10-150 SAR).
Generate REAL calorie counts (200-1200 kcal).
Use the curated Unsplash photo IDs given in the user message — pick varied ones across products.

═══════════════════════════════════════════════════════════════════
ROUTING (SPA — uses hash routes, NO page reloads)
═══════════════════════════════════════════════════════════════════
Use hash-based routing. The body has these views (mutually exclusive `.view`):
  - `#/` or no hash → view-home (hero + about + reviews + loyalty)
  - `#/menu` → view-menu (the 6 category cards grid)
  - `#/category/{id}` → view-category (header showing category name + grid of products in that category)
  - `#/product/{id}` → view-product-detail (full product info: large image, name, price, description, calories card, ingredients list, "أضف للسلة" button, related products)
  - `#/cart` → view-cart (pass 2 will populate this)
  - `#/about` → view-about

The nav links use `href="#/menu"` etc.
Implement `router()` function that reads `location.hash`, hides all `.view`, shows the matching one, scrolls to top.
`window.addEventListener('hashchange', router); window.addEventListener('load', router);`

═══════════════════════════════════════════════════════════════════
MENU LANDING (view-menu)
═══════════════════════════════════════════════════════════════════
- Section title with ornamental divider.
- Grid of 6 category cards (3×2). Each card has the category photo (Unsplash), name, short desc, hover-lift effect.
- The ENTIRE card is a clickable anchor `<a href="#/category/${cat.id}">` — clicking transitions to the category view.

═══════════════════════════════════════════════════════════════════
CATEGORY PAGE (view-category — populated dynamically)
═══════════════════════════════════════════════════════════════════
- Big header with category name + breadcrumb (الرئيسية / القائمة / {category}).
- Grid of products in that category (rendered from `window.SITE.products.filter(p => p.category === currentCategoryId)`).
- Each product card: image, name, calories badge, description, price chip, "تفاصيل" button (→ #/product/{id}) + "أضف للسلة" button.

═══════════════════════════════════════════════════════════════════
PRODUCT DETAIL PAGE (view-product-detail — populated dynamically)
═══════════════════════════════════════════════════════════════════
- Left: large product image. Right: name, rating stars, price, description.
- Below: 2-column "السعرات والمكونات" section (calories big number + ingredient list as chips).
- Quantity selector + "أضف للسلة" (calls window.openCart from pass 2 with the product).
- "منتجات مشابهة" carousel from same category at the bottom.

═══════════════════════════════════════════════════════════════════
NAV / HEADER / HERO
═══════════════════════════════════════════════════════════════════
- Sticky top nav with these 5 links ONLY:
  الرئيسية(#/) · القائمة(#/menu) · المعرض(#/#gallery) · العروض(#/#specials) · عن المطعم(#/about)
- DO NOT add "احجز طاولة" link in the nav — the platform owns the reservation modal.
- DO NOT add "تواصل / Contact" link — the platform injects a unified contact section in the footer.
- Hero embodies the visual pattern. ONE CTA only — "تصفّح القائمة" → #/menu.
- DO NOT BUILD ANY FOOTER. The platform injects a complete unified footer (hours, contact, social, Zitex tracking).

═══════════════════════════════════════════════════════════════════
REVIEWS + LOYALTY (on home view)
═══════════════════════════════════════════════════════════════════
- 4 review cards rendered from `window.SITE.reviews`.
- Loyalty card showing points balance from localStorage `loyalty_points` (default 0).

VISUAL PATTERN: follow the design_directive STRICTLY.
ANIMATIONS: scroll-reveal with IntersectionObserver, card hover-lift, smooth transitions.

OUTPUT PASS 1 NOW — start with `<!DOCTYPE html>` and end with `<!-- ENDPASS1 -->`. NO MARKDOWN."""


# ───────────────────────── PASS 2 SYSTEM PROMPT ─────────────────────────
PASS2_SYSTEM = """You are completing the SECOND HALF of a restaurant SPA at Zitex.

The first half established `window.SITE` (branding, hours, categories, products, reviews) and SPA hash routing.
You will be given the existing HTML so far and must APPEND from `<!-- BEGINPASS2 -->` to `</html>`.

═══════════════════════════════════════════════════════════════════
WHAT TO BUILD
═══════════════════════════════════════════════════════════════════
1. Cart sliding drawer — the platform injects a fully-working cart. DO NOT build your own cart drawer.
2. Checkout modal — also platform-injected. SKIP.
3. Reservation form — platform owns this. SKIP.
4. Branch selector dropdown logic.
5. **Admin Dashboard PRE-POPULATED** (?admin=1) — see CRITICAL section below.
6. **Driver App PRE-POPULATED** (?driver=1).
7. FOOTER — DO NOT build any footer. Platform injects a complete unified footer.
8. Closing </body></html>.

═══════════════════════════════════════════════════════════════════
ABSOLUTE RULES
═══════════════════════════════════════════════════════════════════
1. Output STARTS with `<!-- BEGINPASS2 -->` and ENDS with `</html>`.
2. New `<style>` block at start of pass 2 + new `<script>` block at end.
3. Same CSS variables. RTL Arabic, Saudi/Khaleeji dialect.
4. NO floating WhatsApp/reservation widgets. The ONLY floating element is the cart bottom-right.
5. NO markdown fences.

═══════════════════════════════════════════════════════════════════
ADMIN DASHBOARD — DEEP PRE-FILLED (CRITICAL)
═══════════════════════════════════════════════════════════════════
At the very top of your pass-2 <script>, define this realistic seed data:

```js
window.ADMIN_DATA = {
  orders: [
    // 30 sample orders with REAL Saudi names + phones + addresses
    { id:"ORD-1042", customer:"محمد العتيبي", phone:"+966551234567", items:[{name:"بيتزا مارجريتا",qty:2,price:35}],
      total:70, status:"قيد التحضير", time:"قبل 12 دقيقة", payment:"Mada", address:"الرياض - حي العليا - شارع الأمير سلطان",
      driver:"أحمد السبيعي" },
    ... 30 total, mixed statuses (تم الاستلام / قيد التحضير / في الطريق / تم التسليم), realistic SAR totals 40-280 ...
  ],
  customers: [
    // 20 customers with name, phone, total_orders, total_spent, last_order, loyalty_points, status
    { name:"محمد العتيبي", phone:"+966551234567", total_orders:14, total_spent:1240, last_order:"اليوم",
      loyalty_points:680, status:"VIP", wallet:45.00 },
    ... 20 total, mix of New / Regular / VIP ...
  ],
  drivers: [
    { name:"أحمد السبيعي", phone:"+966551111111", status:"متاح", deliveries_today:6, rating:4.8, area:"شمال الرياض" },
    ... 5 drivers total ...
  ],
  analytics: {
    today: { orders: 23, revenue: 1840.50, avg_order: 80.02, top_dish: "بيتزا مارجريتا" },
    week: { orders: 142, revenue: 11280.00, growth_pct: 12.4 },
    top_dishes: [
      { name:"بيتزا مارجريتا", sold:48, revenue:1680 },
      { name:"شاورما لحم", sold:36, revenue:792 },
      ... 6 items ...
    ]
  }
};
```

═══════════════════════════════════════════════════════════════════
ADMIN LOGIN + DASHBOARD UI
═══════════════════════════════════════════════════════════════════
Show admin login when `location.search.includes('admin=1')` AND localStorage has no `admin_session=ok`.
HARDCODE credentials (the platform will substitute these placeholders):
  Email: __ADMIN_EMAIL__
  Password: __ADMIN_PASSWORD__

After successful login → set localStorage `admin_session=ok` → render admin dashboard.

Admin dashboard layout:
- LEFT SIDEBAR (220px): Logo + nav items (نظرة عامة / الطلبات / القائمة / العملاء / السائقين / التقارير / الإعدادات / تسجيل الخروج). Active item highlighted.
- TOP BAR: search input + notifications bell (badge "3") + admin avatar dropdown.
- MAIN: per active section.

PER-SECTION CONTENT:
A. **نظرة عامة (Overview — default)**:
   - 4 metric cards: طلبات اليوم / إيرادات اليوم / متوسط الطلب / الطبق الأكثر مبيعاً (from ADMIN_DATA.analytics).
   - "أحدث الطلبات" table (last 8 from ADMIN_DATA.orders) with status badges (color-coded).
   - "أكثر الأطباق مبيعاً" bar chart (CSS-drawn — use width-percentage divs based on `sold` count).

B. **الطلبات**:
   - Filter chips by status (الكل / قيد التحضير / في الطريق / تم التسليم).
   - Table: ID, Customer, Phone, Items count, Total, Status (with dropdown to update), Action (View).
   - Status dropdown change saves to ADMIN_DATA.orders[i].status in JS.

C. **القائمة**:
   - Table of products from window.SITE.products: image thumb, name, category, price, calories, actions (تعديل / حذف).
   - Top "+إضافة طبق جديد" button → opens modal form (name, category, price, calories, desc, image URL, save to window.SITE.products and update localStorage).

D. **العملاء**:
   - Cards or table of ADMIN_DATA.customers: name, phone, total_orders, total_spent ر.س, loyalty_points, status badge, wallet, "إرسال رسالة واتساب" button (wa.me/{phone}?text=...).
   - Quick CRM filters (الكل / VIP / جدد).

E. **السائقين**:
   - Cards for each driver: name, phone, status badge, deliveries_today, rating stars, area, "تواصل" + "تعليق" buttons.

F. **التقارير**:
   - Simple weekly revenue trend (CSS bar chart 7 days), top dishes, customer growth.

G. **الإعدادات**:
   - Form to edit window.SITE.branding (name, tagline, phone, whatsapp, email, address, hours table).
   - Save → updates localStorage and window.SITE.

═══════════════════════════════════════════════════════════════════
TUTORIAL OVERLAY (FIRST ADMIN LOGIN)
═══════════════════════════════════════════════════════════════════
If localStorage has no `admin_tutorial_done=1`:
  After login, show a full-screen semi-opaque overlay with a 4-step tour:
  Step 1: "نظرة عامة" → highlight the sidebar overview item + tooltip "هنا تشوف الأداء اليومي".
  Step 2: "الطلبات" → "كل الطلبات الجديدة تظهر هنا — حدّث الحالة من القائمة المنسدلة".
  Step 3: "القائمة" → "أضف أو عدّل الأصناف من هنا".
  Step 4: "العملاء" → "كل عملائك مع تواصل واتساب مباشر".
  "إغلاق الجولة" button sets localStorage `admin_tutorial_done=1`.

═══════════════════════════════════════════════════════════════════
DRIVER APP (?driver=1)
═══════════════════════════════════════════════════════════════════
Login: phone + 4-digit PIN (default 1234).
After login: today's deliveries list filtered by `driver` field. Each card:
  - Order ID, customer name, address, items count, total.
  - Status toggle buttons (مقبول → استلمت الطلب → في الطريق → تم التسليم).
  - WhatsApp button → wa.me/{customer_phone}.
  - "افتح في خرائط جوجل" → maps.google.com/?q={address}.

═══════════════════════════════════════════════════════════════════
FOOTER (4-column rich)
═══════════════════════════════════════════════════════════════════
- Col 1: brand + tagline + social icons (Instagram, X, TikTok, Facebook — clickable to wa.me/instagram.com/...).
- Col 2: weekly hours table + live "مفتوح الآن / مغلق" badge computed from current time.
- Col 3: reservation form (date, time slot, party, name, phone, submit).
- Col 4: clickable phone link `tel:+966...`, email link `mailto:...`, big green WhatsApp button (`wa.me/{phone}`), small map iframe-style placeholder showing address.
- Bottom strip: copyright + Mada/Visa/Apple Pay/STC Pay icons + `<a href="https://zitex.com">Powered by Zitex</a>`.

OUTPUT PASS 2 NOW. Start with `<!-- BEGINPASS2 -->` end with `</html>`. NO markdown."""


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
    seed: Dict[str, Any],
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

    features_block = "\n".join(f"- [{f['id']}] {f['name_ar']}" for f in features)

    # Compact data shape preview (so AI knows the structure to consume — NOT to regenerate)
    cat_preview = ", ".join(f"{c['id']} ({c['name']})" for c in seed["categories"])
    sample_product = seed["products"][0]

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

## DATA LAYER — DO NOT GENERATE — IT WILL BE INJECTED
The platform will inject `window.SITE` automatically. Your JS code must READ from it but NEVER define it.
window.SITE shape (read-only — already populated with 60 products, 6 categories, hours, branding, reviews):

  window.SITE.branding = {{ name, tagline, phone, whatsapp, email, address, city, instagram }}
  window.SITE.hours = {{ saturday: {{open, close}}, ..., friday: {{open, close}} }}
  window.SITE.categories = [ {{ id, name, desc, img }} ]   // 6 items
  window.SITE.products = [ {{ id, category, name, price, calories, desc, ingredients[], tags[], img, prep_time, rating, reviews_count, is_new, is_popular }} ]   // 60 items
  window.SITE.reviews = [ {{ name, stars, date, text }} ]   // 5 items

Categories preview: {cat_preview}
Sample product: {sample_product['name']} (price={sample_product['price']} ر.س, calories={sample_product['calories']}, category={sample_product['category']})

YOUR JOB: build the UI shell. Render menus, products, reviews FROM `window.SITE`.
DO NOT write `window.SITE = {{...}}` — the platform owns that data.

OUTPUT PASS 1 NOW (DOCTYPE → <!-- ENDPASS1 -->). NO MARKDOWN.
"""


def _build_pass2_brief(
    pattern: Dict[str, Any],
    branding: Dict[str, Any],
    features: List[Dict[str, Any]],
    admin_creds: Dict[str, str],
    seed: Dict[str, Any],
    pass1_html: str,
) -> str:
    name = branding.get("business_name", "مطعمي")
    features_block = "\n".join(f"- [{f['id']}] {f['name_ar']}" for f in features)
    pass1_tail = pass1_html[-2500:] if len(pass1_html) > 2500 else pass1_html
    sample_order = seed["orders"][0]
    sample_customer = seed["customers"][0]
    return f"""## BUSINESS
- Name: {name}
- Pattern: {pattern['id']} (palette: {", ".join(pattern.get('palette', []))})

## ADMIN CREDENTIALS — HARDCODE THESE EXACTLY
Email: {admin_creds['email']}
Password: {admin_creds['password']}

## ENABLED FEATURES
{features_block}

## DATA LAYER — DO NOT GENERATE — IT WILL BE INJECTED
The platform owns `window.SITE` and `window.ADMIN_DATA`. Your JS must READ from them but NEVER define them.

  window.ADMIN_DATA.orders = [ {{ id, customer, phone, items[], total, status, time, payment, address, driver }} ]   // 30 orders
  window.ADMIN_DATA.customers = [ {{ name, phone, total_orders, total_spent, last_order, loyalty_points, status, wallet }} ]   // 20 customers
  window.ADMIN_DATA.drivers = [ {{ name, phone, status, deliveries_today, rating, area }} ]   // 5 drivers
  window.ADMIN_DATA.analytics = {{ today: {{orders, revenue, avg_order, top_dish}}, week: {{...}}, top_dishes: [{{name, sold, revenue}}] }}

Sample order: {sample_order['id']} → {sample_order['customer']} ({sample_order['phone']}), total={sample_order['total']} ر.س, status={sample_order['status']}
Sample customer: {sample_customer['name']} → {sample_customer['phone']}, orders={sample_customer['total_orders']}, status={sample_customer['status']}

## EXISTING HTML — END OF PASS 1
{pass1_tail}

## YOUR JOB
Build PASS 2: cart drawer + checkout modal + reservation form (in footer) + admin login + admin dashboard
(7 sections reading from `window.ADMIN_DATA`) + tutorial overlay + driver app (reads ADMIN_DATA.drivers
filtered by name) + 4-column rich footer.

OUTPUT PASS 2 NOW (<!-- BEGINPASS2 --> → </html>). NO MARKDOWN.
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
    """Merge pass1 (ends at <!-- ENDPASS1 -->) and pass2 (starts at <!-- BEGINPASS2 -->).
    Guarantees the final HTML has both </body> and </html> for safe injection later."""
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

    merged = f"{p1}\n{p2}"

    # GUARANTEE </body> and </html> exist (AI sometimes omits </body>)
    if "</html>" in merged.lower() and "</body>" not in merged.lower():
        merged = re.sub(r"</html>\s*$", "</body>\n</html>", merged, flags=re.IGNORECASE)
    elif "</body>" not in merged.lower() and "</html>" not in merged.lower():
        merged = merged + "\n</body>\n</html>"
    elif "</body>" in merged.lower() and "</html>" not in merged.lower():
        merged = merged + "\n</html>"

    return merged


def _safe_inject_before_body_end(html: str, payload: str) -> str:
    """Insert payload before </body>. If </body> missing, insert before </html>. Else append."""
    if "</body>" in html.lower():
        idx = html.lower().rfind("</body>")
        return html[:idx] + payload + "\n" + html[idx:]
    if "</html>" in html.lower():
        idx = html.lower().rfind("</html>")
        return html[:idx] + payload + "\n</body>\n" + html[idx:]
    return html + "\n" + payload + "\n</body>\n</html>"


def _enforce_branding_and_credentials(html: str, admin_creds: Dict[str, str]) -> str:
    """Replace placeholder credentials. Zitex branding is now in the unified footer."""
    html = html.replace("__ADMIN_EMAIL__", admin_creds["email"])
    html = html.replace("__ADMIN_PASSWORD__", admin_creds["password"])
    return html


# ───────────────────────── PUBLIC API ─────────────────────────
async def generate_ready_site(
    type_id: str,
    pattern: Dict[str, Any],
    branding: Dict[str, Any],
    features: List[Dict[str, Any]],
    project_id: str = "",
) -> Dict[str, Any]:
    """Generate via TWO-PASS + Python data factory injection → guaranteed-rich output.

    The Python data factory produces ALL seed data (60 products, 30 orders, 20 customers,
    5 drivers, analytics, reviews). The AI focuses ONLY on UI shell. Then we inject the
    seed JS into the merged HTML deterministically.
    """
    admin_creds = _gen_admin_credentials(branding.get("business_name", ""))

    # 1) Python data factory — deterministic seed
    seed = seed_restaurant(
        business_name=branding.get("business_name", "مطعمي"),
        tagline=branding.get("tagline", ""),
    )
    seed_js = seed_to_js(seed)

    # 2) AI builds the UI shell only
    pass1_user = _build_pass1_brief(pattern, branding, features, seed)
    pass1_html = await _call_llm(PASS1_SYSTEM, pass1_user, max_tokens=16000)
    logger.info(f"[READY_SITES] pass1 size: {len(pass1_html)}")

    pass2_user = _build_pass2_brief(pattern, branding, features, admin_creds, seed, pass1_html)
    pass2_html = await _call_llm(PASS2_SYSTEM, pass2_user, max_tokens=16000)
    logger.info(f"[READY_SITES] pass2 size: {len(pass2_html)}")

    # 3) Merge
    merged = _merge_passes(pass1_html, pass2_html)

    # 4) Inject the seed JS at the top of the first <script> block
    merged = _inject_seed(merged, seed_js)

    # 4b) Inject pre-built HTML for categories, products, admin tables
    #     This replaces marker comments OR placeholder divs the AI may have left,
    #     guaranteeing visible content even if the AI didn't write render code.
    merged = _inject_prebuilt_html(merged, seed)

    # 4c) Inject the COMPLETE pre-built admin + driver app (login + dashboard + tabs)
    #     This guarantees ?admin=1 and ?driver=1 always work with working buttons.

    # First — strip any AI-generated `?admin=1` or `?driver=1` handlers that use
    # destructive `document.body.innerHTML = ...` patterns. Those wipe out our
    # injected modules and replace them with broken unstyled forms.
    ai_admin_handler_re = re.compile(
        r"if\s*\(\s*location\.search\.includes\([\"']admin=1[\"']\)\s*\)\s*\{[\s\S]*?document\.body\.innerHTML[\s\S]*?\}\s*",
        re.MULTILINE,
    )
    merged = ai_admin_handler_re.sub("/* AI admin handler removed by Zitex */", merged)
    ai_driver_handler_re = re.compile(
        r"if\s*\(\s*location\.search\.includes\([\"']driver=1[\"']\)\s*\)\s*\{[\s\S]*?document\.body\.innerHTML[\s\S]*?\}\s*",
        re.MULTILINE,
    )
    merged = ai_driver_handler_re.sub("/* AI driver handler removed by Zitex */", merged)

    # Also remove any AI-generated `<div id="adminLogin">` or similar broken UIs
    # so our zx-admin-root is the only admin UI present.
    merged = re.sub(r'<div id="adminLogin"[\s\S]*?</div>\s*</div>', '', merged)

    admin_module = render_admin_full_app(seed, admin_creds["email"], admin_creds["password"])
    merged = _safe_inject_before_body_end(merged, admin_module)

    # 4d) Inject pre-built CART drawer + working addToCart + checkout flow
    #     This overrides any broken AI-defined cart with a guaranteed-working one.
    cart_module = render_cart_module(seed)
    merged = _safe_inject_before_body_end(merged, cart_module)

    # 4e) Strip AI-generated <footer> entirely + احجز طاولة nav links → we own the footer & resv.
    merged = re.sub(r"<footer\b[\s\S]*?</footer>", "", merged, flags=re.IGNORECASE)
    # Strip nav links containing "احجز طاولة" / "reservation" / "book a table" (defensive)
    merged = re.sub(
        r'<a\b[^>]*>\s*(?:احجز\s*طاول[^<]*|reserve|book\s*table|reservation)[^<]*</a>',
        '', merged, flags=re.IGNORECASE
    )
    # Strip any "Powered by Zitex" mini-footer the AI may have produced (we add our own)
    merged = re.sub(
        r'<div\b[^>]*>[^<]*Powered by Zitex[\s\S]{0,300}?</div>',
        '', merged, flags=re.IGNORECASE
    )

    # 4f) Inject UNIFIED Zitex enhancements module (footer, slider, modals, click delegation)
    enhancements = render_zitex_enhancements(seed, project_id=project_id)
    merged = _safe_inject_before_body_end(merged, enhancements)

    # 5) Enforce credentials + branding
    merged = _enforce_branding_and_credentials(merged, admin_creds)
    logger.info(f"[READY_SITES] merged size: {len(merged)}")

    if "<html" not in merged.lower() or "</html>" not in merged.lower():
        raise RuntimeError("Merged output is not valid HTML document")

    return {"html": merged, "admin_credentials": admin_creds, "seed_summary": {
        "products": len(seed["products"]),
        "orders": len(seed["orders"]),
        "customers": len(seed["customers"]),
        "drivers": len(seed["drivers"]),
    }}


def _inject_seed(html: str, seed_js: str) -> str:
    """Inject the seed JS at the top of the first <script> tag.
    Removes any AI-generated `window.SITE` / `window.ADMIN_DATA` assignments first.
    """
    html = re.sub(r"window\.SITE\s*=\s*\{[\s\S]*?\}\s*;", "", html, count=1)
    html = re.sub(r"window\.ADMIN_DATA\s*=\s*\{[\s\S]*?\}\s*;", "", html, count=1)
    marker_re = re.compile(r"(<script\b[^>]*>)", re.IGNORECASE)
    m = marker_re.search(html)
    if m:
        idx = m.end()
        return html[:idx] + "\n/* ── Zitex seed data — INJECTED ── */\n" + seed_js + "\n/* ── end seed ── */\n" + html[idx:]
    seed_block = f'\n<script>\n/* ── Zitex seed data — INJECTED ── */\n{seed_js}\n</script>\n'
    return _safe_inject_before_body_end(html, seed_block)


def _inject_prebuilt_html(html: str, seed: Dict[str, Any]) -> str:
    """Inject pre-built HTML for the menu grid, products grid, and admin tables.

    Looks for marker containers and either replaces their inner content or appends to them.
    Markers (in priority order):
      - <div id="categories-grid"> / <div id="menu-grid">
      - <div id="products-grid"> / <div id="all-products">
      - <tbody id="admin-orders-tbody"> / <tbody id="admin-customers-tbody">
    If the AI didn't include any markers at all, we APPEND a full menu section before </body>.
    """
    cats_html = render_categories_html(seed)
    prods_html = render_products_html(seed)
    orders_html = render_admin_orders_html(seed)
    customers_html = render_admin_customers_html(seed)

    found_any = False
    for marker_id in ("categories-grid", "menu-grid", "menu_grid"):
        pat = re.compile(rf'(<div\b[^>]*id=["\']{marker_id}["\'][^>]*>)([\s\S]*?)(</div>)', re.IGNORECASE)
        m = pat.search(html)
        if m:
            html = html[:m.end(1)] + "\n" + cats_html + "\n" + html[m.start(3):]
            found_any = True
            break

    for marker_id in ("products-grid", "all-products", "products_grid"):
        pat = re.compile(rf'(<div\b[^>]*id=["\']{marker_id}["\'][^>]*>)([\s\S]*?)(</div>)', re.IGNORECASE)
        m = pat.search(html)
        if m:
            html = html[:m.end(1)] + "\n" + prods_html + "\n" + html[m.start(3):]
            break

    for marker_id, content in (("admin-orders-tbody", orders_html), ("admin-customers-tbody", customers_html)):
        pat = re.compile(rf'(<tbody\b[^>]*id=["\']{marker_id}["\'][^>]*>)([\s\S]*?)(</tbody>)', re.IGNORECASE)
        m = pat.search(html)
        if m:
            html = html[:m.end(1)] + "\n" + content + "\n" + html[m.start(3):]

    # If AI didn't include any menu markers, inject a fallback menu section near the end
    if not found_any:
        fallback_styles = """
<style id="zitex-injected-menu-styles">
#zitex-menu-fallback { max-width:1200px; margin:60px auto; padding:0 20px; }
#zitex-menu-fallback h2 { font-size:32px; text-align:center; margin-bottom:30px; }
#zitex-menu-fallback .cat-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:20px; margin-bottom:60px; }
@media(max-width:768px){ #zitex-menu-fallback .cat-grid { grid-template-columns:1fr } }
.cat-card { background:#fff; border-radius:18px; overflow:hidden; box-shadow:0 6px 24px rgba(0,0,0,.1); transition:transform .2s; text-decoration:none; color:inherit; display:block; }
.cat-card:hover { transform:translateY(-6px); }
.cat-img { height:200px; background-size:cover; background-position:center; }
.cat-body { padding:18px; text-align:center; }
.cat-name { font-size:20px; font-weight:900; margin-bottom:6px; }
.cat-desc { color:#666; font-size:13px; margin-bottom:10px; }
.cat-cta { color:#a52a2a; font-weight:700; font-size:13px; }
.prod-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:18px; }
@media(max-width:768px){ .prod-grid { grid-template-columns:1fr } }
.product-card { background:#fff; border-radius:14px; overflow:hidden; box-shadow:0 4px 14px rgba(0,0,0,.08); }
.prod-img { height:180px; background-size:cover; background-position:center; position:relative; }
.prod-cal { position:absolute; top:10px; right:10px; background:rgba(0,0,0,.7); color:#fff; padding:4px 10px; border-radius:99px; font-size:11px; }
.prod-new { position:absolute; top:10px; left:10px; background:#22c55e; color:#fff; padding:4px 10px; border-radius:99px; font-size:11px; font-weight:900; }
.prod-pop { position:absolute; bottom:10px; right:10px; background:rgba(245,158,11,.95); color:#000; padding:4px 10px; border-radius:99px; font-size:11px; font-weight:900; }
.prod-body { padding:14px; }
.prod-tags { display:flex; gap:5px; margin-bottom:6px; }
.ptag { background:#fef3c7; color:#a52a2a; padding:2px 8px; border-radius:99px; font-size:10px; font-weight:700; }
.prod-name { font-size:17px; font-weight:900; margin-bottom:4px; }
.prod-desc { color:#666; font-size:12px; line-height:1.5; margin-bottom:10px; min-height:36px; }
.prod-foot { display:flex; justify-content:space-between; align-items:center; }
.prod-price { font-size:18px; font-weight:900; color:#a52a2a; }
.prod-add { background:#a52a2a; color:#fff; border:none; padding:8px 16px; border-radius:99px; font-weight:900; font-size:12px; cursor:pointer; transition:transform .15s; }
.prod-add:hover { transform:scale(1.05); }
</style>"""
        fallback_section = f"""
<section id="zitex-menu-fallback">
  <h2>منيو المطعم</h2>
  <div class="cat-grid">{cats_html}</div>
  <h2 id="all-products-title">كل الأصناف</h2>
  <div class="prod-grid">{prods_html}</div>
</section>
"""
        html = _safe_inject_before_body_end(html, fallback_styles + fallback_section)

    return html


async def refine_ready_site(current_html: str, change_request: str) -> str:
    """Apply a natural-language refinement to an existing site's HTML."""
    user_msg = f"""## CHANGE REQUEST (apply surgically)
{change_request}

## CURRENT HTML
{current_html}

OUTPUT THE FULL UPDATED HTML NOW (entire document, doctype to </html>)."""
    new_html = await _call_llm(REFINE_SYSTEM, user_msg, max_tokens=16000)

    if "<html" not in new_html.lower() or "</html>" not in new_html.lower():
        raise RuntimeError("Refinement output is not valid HTML")

    if "zitex.com" not in new_html.lower():
        new_html = new_html.replace(
            "</body>",
            '\n<div style="text-align:center;padding:14px;font-size:12px;background:#0a0a0b;color:#aaa;">'
            '<a href="https://zitex.com" target="_blank" rel="noopener" style="color:#aaa;text-decoration:none;opacity:.75">'
            'Powered by Zitex</a></div>\n</body>'
        )
    return new_html
