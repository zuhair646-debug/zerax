"""Website renderer — orchestrator.

Split into sub-modules:
  • renderer_helpers — _esc, _humanize_type
  • content_renderer — generic sections (hero, about, gallery, team, pricing, etc.)
  • ecommerce_renderer — products, menu, product grid with filters
  • booking_renderer — reservation form, booking widget
  • portfolio_renderer — stock/gold tickers, realty listings, portfolio overlay
  • dashboard_renderer — admin dashboard panel + items
  • overlay_renderer — auth+commerce overlay, floating widgets
  • base_css — large CSS generator
"""
from typing import Dict, Any, List

from .widget_styles import get_styles_css as _widget_css
from .renderer_helpers import _esc, _humanize_type
from .content_renderer import (
    _section_hero, _section_features, _section_story_timeline, _section_process_steps,
    _section_quote, _section_about, _section_gallery, _section_testimonials,
    _section_team, _section_pricing, _section_faq, _section_contact, _section_cta,
    _section_footer, _section_video, _section_newsletter, _section_stats_band,
    _section_stories, _section_banner, _section_announce_bar, _section_map_embed,
    _section_delivery_banner, _section_custom,
)
from .ecommerce_renderer import (
    _section_products, _section_menu, _section_product_grid_filters,
)
from .booking_renderer import _section_reservation, _section_booking_widget
from .portfolio_renderer import (
    _section_stock_ticker, _section_gold_ticker, _section_listings_grid,
    _portfolio_overlay,
)
from .dashboard_renderer import _section_dashboard
from .overlay_renderer import _auth_and_commerce_overlay, _floating_widgets
from .chatbot_widget import chatbot_widget as _chatbot_widget
from .stories_widget import stories_widget as _stories_widget
from .base_css import _base_css


# Section-type → renderer function map (single source of truth)
RENDERERS = {
    "hero": _section_hero,
    "features": _section_features,
    "about": _section_about,
    "products": _section_products,
    "menu": _section_menu,
    "services": _section_features,  # alias
    "gallery": _section_gallery,
    "testimonials": _section_testimonials,
    "reviews": _section_testimonials,  # alias
    "team": _section_team,
    "pricing": _section_pricing,
    "faq": _section_faq,
    "contact": _section_contact,
    "cta": _section_cta,
    "footer": _section_footer,
    "dashboard": _section_dashboard,
    "admin_dashboard": _section_dashboard,
    "reservation": _section_reservation,
    "story_timeline": _section_story_timeline,
    "process_steps": _section_process_steps,
    "quote": _section_quote,
    "video": _section_video,
    "newsletter": _section_newsletter,
    "newsletter_section": _section_newsletter,
    "stats": _section_stats_band,
    "stats_band": _section_stats_band,
    "stories": _section_stories,
    "story_reel": _section_stories,
    "highlights": _section_stories,
    "banner": _section_banner,
    "promo_banner": _section_banner,
    "announce_bar_section": _section_announce_bar,
    "map_embed": _section_map_embed,
    "map": _section_map_embed,
    "delivery_banner": _section_delivery_banner,
    "custom": _section_custom,
    # Vertical-specific sections
    "booking_widget": _section_booking_widget,
    "product_grid_filters": _section_product_grid_filters,
    "stock_ticker": _section_stock_ticker,
    "hero_ticker": _section_stock_ticker,
    "gold_ticker": _section_gold_ticker,
    "listings_grid": _section_listings_grid,
}


def render_website_to_html(project: Dict[str, Any]) -> str:
    """Render a Website Project dict to full HTML."""
    lang = project.get("lang", "ar")
    direction = project.get("direction", "rtl")
    theme = project.get("theme", {})
    sections = sorted(project.get("sections", []), key=lambda s: s.get("order", 0))
    meta = project.get("meta", {})
    title = _esc(meta.get("title") or project.get("name") or "موقعي")

    # 🆕 Replace {IMG_1}/{IMG_2}/{IMG_3} tokens in custom_css with category-specific photos
    # so each archetype gets relevant imagery (no more makeup photos in restaurant templates).
    try:
        from .category_images import pick_images_for_archetype
        cat_id = project.get("template") or project.get("business_type") or meta.get("category_id") or "blank"
        arch_id = (meta.get("layout_id") or "").split("__", 1)[-1] or "default"
        imgs = pick_images_for_archetype(cat_id, arch_id, count=4)
        css = theme.get("custom_css", "")
        if css and "{IMG_" in css:
            css = (css.replace("{IMG_1}", imgs[0])
                      .replace("{IMG_2}", imgs[1])
                      .replace("{IMG_3}", imgs[2])
                      .replace("{IMG_4}", imgs[3]))
            theme = {**theme, "custom_css": css}
    except Exception:
        pass

    body_parts: List[str] = []
    for sec in sections:
        if not sec.get("visible", True):
            continue
        stype = sec.get("type", "")
        # Unknown types fall back to the generic `custom` renderer so they're ALWAYS visible
        renderer = RENDERERS.get(stype) or _section_custom
        try:
            data = sec.get("data", {}) or {}
            if renderer is _section_custom and stype and "title" not in data:
                data = {**data, "title": data.get("title") or _humanize_type(stype)}
            body_parts.append(renderer(data, theme))
        except Exception:
            continue

    manifest_link = ""
    if project.get("slug"):
        manifest_link = (
            f'<link rel="manifest" href="/api/websites/public/{project.get("slug")}/manifest.json">'
            f'<meta name="theme-color" content="{theme.get("primary", "#FFD700")}">'
            f'<meta name="apple-mobile-web-app-capable" content="yes">'
            f'<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
        )

    return f"""<!DOCTYPE html>
<html lang="{lang}" dir="{direction}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<link href="https://fonts.googleapis.com/css2?family={theme.get('font', 'Tajawal').replace(' ', '+')}:wght@400;700;900&display=swap" rel="stylesheet">
{manifest_link}
<style>{_base_css(theme)}</style>
<style>{theme.get('custom_css', '')}</style>
</head>
<body>
{_stories_widget(project.get('slug') or '')}
{_floating_widgets(theme)}
{_chatbot_widget(project.get('slug') or '', project)}
{''.join(body_parts)}
{_auth_and_commerce_overlay(project.get('slug'))}
{_portfolio_overlay(project.get('slug')) if project.get('vertical') == 'stocks' else ''}
{_widget_css(project)}
</body>
</html>"""
