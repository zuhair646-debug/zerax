"""
Zerax Template Renderer — Template-First Engine
================================================
Generates production-ready sites from 3 hand-crafted master templates:
  • app_mode      → e-commerce, services, stores
  • story_mode    → restaurants, cafés, cinematic narratives
  • showroom_mode → jewelry, luxury, real estate

ZERO AI = ZERO hallucinations.
Each site is hydrated with the merchant's branding + products + market data.
The rendered HTML is a fully self-contained, PWA-ready static page.
"""
from __future__ import annotations
import json
import os
import re
from typing import Any

TEMPLATES_DIR = "/app/frontend/public/mockups"

TEMPLATE_FILES = {
    "app_mode": "app_mode_full.html",
    "story_mode": "story_mode_full.html",
    "showroom_mode": "showroom_mode_full.html",
}

TEMPLATE_LABELS = {
    "app_mode": {"ar": "متجر / تطبيق", "en": "App / Store"},
    "story_mode": {"ar": "مطعم / قصة", "en": "Restaurant / Story"},
    "showroom_mode": {"ar": "فاخر / مجوهرات", "en": "Luxury / Showroom"},
}

# Map business types → recommended template mode
TYPE_TO_TEMPLATE = {
    # App mode (e-commerce / services)
    "store": "app_mode",
    "ecommerce": "app_mode",
    "fashion": "app_mode",
    "electronics": "app_mode",
    "clinic": "app_mode",
    "services": "app_mode",
    "salon": "app_mode",
    "gym": "app_mode",
    # Story mode (restaurants, hospitality)
    "restaurant": "story_mode",
    "cafe": "story_mode",
    "hotel": "story_mode",
    "tourism": "story_mode",
    # Showroom mode (luxury)
    "jewelry": "showroom_mode",
    "real_estate": "showroom_mode",
    "luxury": "showroom_mode",
    "art": "showroom_mode",
    "automotive": "showroom_mode",
}


def get_recommended_template(type_id: str) -> str:
    """Map business type to its best-fit template."""
    return TYPE_TO_TEMPLATE.get(type_id, "app_mode")


def _build_config(
    branding: dict,
    products: list | None,
    market_id: str,
    project_id: str,
) -> dict:
    """Build the JSON config injected into the template at runtime."""
    return {
        "BRAND": branding.get("business_name") or "متجري",
        "TAGLINE": branding.get("tagline") or "",
        "PRIMARY_COLOR": branding.get("primary_color") or "#7c3aed",
        "ACCENT_COLOR": branding.get("accent_color") or branding.get("primary_color") or "#a855f7",
        "PHONE": branding.get("phone") or "+966512345678",
        "WHATSAPP": branding.get("whatsapp") or branding.get("phone") or "",
        "EMAIL": branding.get("email") or "hello@example.com",
        "ADDRESS_AR": branding.get("address_ar") or branding.get("address") or "",
        "ADDRESS_EN": branding.get("address_en") or branding.get("address") or "",
        "LOGO_URL": branding.get("logo_url") or "",
        "DEFAULT_MARKET": market_id or "sa",
        "PRODUCTS": products or [],
        "PROJECT_ID": project_id,
    }


def _inject_config_and_pwa(html: str, config: dict, project_id: str) -> str:
    """Inject the runtime config + PWA manifest + Zerax branding footer into the template."""
    cfg_json = json.dumps(config, ensure_ascii=False)
    head_injection = (
        '<link rel="manifest" href="/api/ready-sites/manifest/' + project_id + '.webmanifest">\n'
        '<meta name="theme-color" content="' + config["PRIMARY_COLOR"] + '">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
        '<meta name="apple-mobile-web-app-title" content="' + config["BRAND"] + '">\n'
        '<script>window.ZERAX_CONFIG=' + cfg_json + ';</script>\n'
        '<style>'
        # Gold shimmer for the in-footer brand mark — does NOT float over the page
        '@keyframes zerax-gold-shine{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}'
        '@keyframes zerax-gold-glow{0%,100%{filter:drop-shadow(0 0 4px rgba(212,175,55,.35))}'
        '50%{filter:drop-shadow(0 0 12px rgba(212,175,55,.75))}}'
        # Wrapper: full-width band placed AFTER the site footer
        '.zerax-credit{display:flex;justify-content:center;align-items:center;'
        'padding:20px 16px;background:#000;border-top:1px solid rgba(212,175,55,.18);position:relative}'
        '.zerax-credit::before{content:"";position:absolute;left:0;right:0;top:-1px;height:1px;'
        'background:linear-gradient(90deg,transparent,rgba(212,175,55,.6),transparent)}'
        # The clickable pill (matches Zerax logo: dark glass + gold accents)
        '.zerax-credit a{display:inline-flex;align-items:center;gap:10px;padding:7px 18px 7px 8px;border-radius:99px;'
        'background:linear-gradient(135deg,#0a0a14,#0e0a18);border:1px solid rgba(212,175,55,.35);'
        'text-decoration:none;animation:zerax-gold-glow 3s ease-in-out infinite;transition:transform .25s;cursor:pointer}'
        '.zerax-credit a:hover{transform:translateY(-1px) scale(1.03)}'
        # Real Zerax logo image inside a circular dark frame
        '.zerax-credit .zerax-mark{width:32px;height:32px;border-radius:50%;display:inline-flex;'
        'align-items:center;justify-content:center;background:#000;'
        'border:1.5px solid rgba(212,175,55,.5);padding:3px;box-shadow:inset 0 0 8px rgba(212,175,55,.15)}'
        '.zerax-credit .zerax-mark img{width:100%;height:100%;object-fit:contain;'
        'filter:drop-shadow(0 0 3px rgba(212,175,55,.5))}'
        '.zerax-credit .zerax-txt{display:flex;flex-direction:column;line-height:1.15;font-family:-apple-system,Tajawal,sans-serif}'
        '.zerax-credit .zerax-txt small{color:#9ca3af;font-size:9px;letter-spacing:2.5px;font-weight:700;text-transform:uppercase}'
        '.zerax-credit .zerax-txt b{font-size:13px;letter-spacing:3px;font-weight:900;'
        'background:linear-gradient(135deg,#f4d77a,#d4af37,#b8862f);background-size:200% 100%;'
        '-webkit-background-clip:text;background-clip:text;color:transparent;'
        'animation:zerax-gold-shine 4s linear infinite}'
        '@media print{.zerax-credit{display:none}}'
        '</style>\n'
    )
    html = html.replace("</head>", head_injection + "</head>", 1)

    # PWA gating script: runs ONCE on page load
    pwa_script = (
        '<script>'
        '(function(){'
        "var pid='" + project_id + "';"
        "fetch('/api/care/pwa-status/'+pid).then(function(r){return r.json()}).then(function(s){"
        "  window.ZERAX_PWA_ENABLED=!!s.pwa_enabled;"
        "  if(!s.pwa_enabled){"
        "    var m=document.querySelector('link[rel=manifest]');if(m)m.remove();return;"
        "  }"
        "  if('serviceWorker' in navigator){"
        "    navigator.serviceWorker.register('/sw.js').catch(function(){});"
        "  }"
        "}).catch(function(){});"
        '})();'
        '</script>\n'
    )

    # In-flow branding band — placed at the absolute end of the document
    # (after the site footer, before </body>). Does not float, does not overlap UI.
    brand_band = (
        '<div class="zerax-credit" role="contentinfo" aria-label="Powered by Zerax">'
        '<a href="https://zerax.com?ref=' + project_id + '" target="_blank" rel="noopener noreferrer" '
        'onclick="event.stopPropagation();window.open(this.href,\'_blank\');return false;">'
        '<span class="zerax-mark"><img src="/zerax-logo.png" alt="Zerax" /></span>'
        '<span class="zerax-txt"><small>POWERED BY</small><b>ZERAX</b></span>'
        '</a>'
        '</div>\n'
        # Hide legacy in-template brand pill (any variant) so we only have ONE brand mark
        '<style>.zx-zerax-brand,.zx-zitex-brand,.zx-zerax-bar a.zx-zerax-brand{display:none!important}</style>\n'
    )
    html = html.replace("</body>", brand_band + pwa_script + "</body>", 1)
    return html


def _apply_branding_strings(html: str, mode: str, config: dict) -> str:
    """Replace hardcoded brand names + contact info with merchant's data."""
    brand = config["BRAND"]
    phone = config["PHONE"]
    email = config["EMAIL"]
    addr_ar = config["ADDRESS_AR"]
    addr_en = config["ADDRESS_EN"]

    # Per-template brand replacements
    placeholders = {
        "app_mode": [
            (r">سوقي<", f">{brand}<"),
            (r">SOUQI<", f">{brand.upper()}<"),
            (r'\+966 51 234 5678', phone),
            (r'\+966512345678', phone.replace(" ", "")),
            (r'hello@souqi\.app', email),
            (r'📍 الرياض، حي العليا', f"📍 {addr_ar or 'الرياض'}"),
            (r'📍 Riyadh, Olaya', f"📍 {addr_en or 'Riyadh'}"),
        ],
        "story_mode": [
            (r">N O I R<", f">{brand}<"),
            (r'\+966 51 234 5678', phone),
            (r'hello@noir\.sa', email),
            (r'King Fahd Rd, Riyadh, SA', addr_en or 'Riyadh, SA'),
            (r'شارع الملك فهد، الرياض', addr_ar or 'الرياض'),
        ],
        "showroom_mode": [
            (r">A R Y A<", f">{brand}<"),
            (r'\+966 51 234 5678', phone),
            (r'private@arya\.sa', email),
            (r'Boulevard, Riyadh, SA', addr_en or 'Riyadh, SA'),
            (r'البوليفارد، الرياض', addr_ar or 'الرياض'),
        ],
    }

    for pattern, replacement in placeholders.get(mode, []):
        html = re.sub(pattern, replacement, html)
    return html


def render_template(
    template_mode: str,
    branding: dict,
    products: list | None = None,
    market_id: str = "sa",
    project_id: str = "preview",
) -> dict[str, Any]:
    """
    Render a ready-site from one of the 3 master templates.
    Returns: { html, template_mode, brand, market_id, product_count }
    """
    if template_mode not in TEMPLATE_FILES:
        template_mode = "app_mode"

    template_path = os.path.join(TEMPLATES_DIR, TEMPLATE_FILES[template_mode])
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file missing: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    config = _build_config(branding or {}, products or [], market_id, project_id)
    html = _apply_branding_strings(html, template_mode, config)
    html = _inject_config_and_pwa(html, config, project_id)

    return {
        "html": html,
        "template_mode": template_mode,
        "brand": config["BRAND"],
        "market_id": market_id,
        "product_count": len(products or []),
        "config": config,
    }


def list_templates() -> list[dict]:
    """Public catalog of available templates (for the Wizard)."""
    return [
        {
            "id": "app_mode",
            "name_ar": "نمط التطبيق",
            "name_en": "App Mode",
            "tagline_ar": "متاجر · خدمات · حجوزات",
            "tagline_en": "Stores · Services · Bookings",
            "best_for_ar": "متاجر إلكترونية، عيادات، صالونات، خدمات يومية",
            "best_for_en": "E-commerce, clinics, salons, daily services",
            "preview_url": "/mockups/app_mode_full.html",
            "icon": "🛒",
        },
        {
            "id": "story_mode",
            "name_ar": "النمط القصصي",
            "name_en": "Story Mode",
            "tagline_ar": "مطاعم · مقاهي · تجارب فاخرة",
            "tagline_en": "Restaurants · Cafés · Cinematic experiences",
            "best_for_ar": "مطاعم فاخرة، مقاهي مميزة، فنادق بوتيك",
            "best_for_en": "Fine dining, boutique cafés, hotels",
            "preview_url": "/mockups/story_mode_full.html",
            "icon": "🎬",
        },
        {
            "id": "showroom_mode",
            "name_ar": "نمط المعرض",
            "name_en": "Showroom Mode",
            "tagline_ar": "مجوهرات · عقارات · سيارات · فن",
            "tagline_en": "Jewelry · Real estate · Cars · Art",
            "best_for_ar": "مجوهرات، عقارات راقية، سيارات فاخرة، أعمال فنية",
            "best_for_en": "Jewelry, luxury real estate, premium cars, fine art",
            "preview_url": "/mockups/showroom_mode_full.html",
            "icon": "💎",
        },
    ]
