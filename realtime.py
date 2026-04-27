"""Design variants — multiple visual styles for the same business template.

Each variant modifies the theme (colors, radius, font) without changing sections.
So one template (e.g., restaurant) produces 10 distinct-looking designs."""
from typing import List, Dict, Any
from .templates import TEMPLATES


# 10 visual styles applicable to any template
STYLE_VARIANTS: List[Dict[str, Any]] = [
    {"id": "classic",    "name": "كلاسيكي أنيق",  "theme_override": {"primary": "#D4AF37", "secondary": "#1a1f3a", "accent": "#8B0000", "radius": "medium", "font": "Tajawal"}},
    {"id": "modern",     "name": "عصري حيوي",    "theme_override": {"primary": "#3B82F6", "secondary": "#0f172a", "accent": "#22D3EE", "radius": "large", "font": "Cairo"}},
    {"id": "warm",       "name": "دافئ وعائلي",  "theme_override": {"primary": "#F59E0B", "secondary": "#18181b", "accent": "#EF4444", "radius": "large", "font": "Tajawal"}},
    {"id": "minimal",    "name": "بسيط نقي",     "theme_override": {"primary": "#000000", "secondary": "#ffffff", "accent": "#6B7280", "background": "#ffffff", "text": "#18181b", "radius": "none", "font": "Readex Pro"}},
    {"id": "luxury",     "name": "فاخر ذهبي",    "theme_override": {"primary": "#D4AF37", "secondary": "#0a0a0a", "accent": "#B8860B", "background": "#0a0a0a", "radius": "small", "font": "Amiri"}},
    {"id": "playful",    "name": "مرح وملوّن",   "theme_override": {"primary": "#EC4899", "secondary": "#18181b", "accent": "#8B5CF6", "radius": "large", "font": "Cairo"}},
    {"id": "nature",     "name": "طبيعي أخضر",   "theme_override": {"primary": "#10B981", "secondary": "#064e3b", "accent": "#F59E0B", "radius": "medium", "font": "Tajawal"}},
    {"id": "bold",       "name": "جريء قوي",     "theme_override": {"primary": "#DC2626", "secondary": "#18181b", "accent": "#FBBF24", "radius": "none", "font": "Cairo"}},
    {"id": "pastel",     "name": "ألوان هادئة",   "theme_override": {"primary": "#A78BFA", "secondary": "#FDF2F8", "accent": "#F472B6", "background": "#FDF2F8", "text": "#581c87", "radius": "large", "font": "Readex Pro"}},
    {"id": "dark_pro",   "name": "داكن احترافي", "theme_override": {"primary": "#06B6D4", "secondary": "#020617", "accent": "#F59E0B", "background": "#020617", "radius": "medium", "font": "Tajawal"}},
]


def list_style_variants() -> List[Dict[str, Any]]:
    """List all 10 visual styles available."""
    return [{"id": v["id"], "name": v["name"], "theme": v["theme_override"]} for v in STYLE_VARIANTS]


def get_variant_project(template_id: str, variant_id: str) -> Dict[str, Any]:
    """Return a project dict combining template sections + variant theme.
    Used for rendering preview thumbnails and creating projects."""
    template = TEMPLATES.get(template_id) or TEMPLATES["blank"]
    variant = next((v for v in STYLE_VARIANTS if v["id"] == variant_id), STYLE_VARIANTS[0])
    merged_theme = {**template["theme"], **variant["theme_override"]}
    return {
        "name": f"{template['name']} — {variant['name']}",
        "business_type": template["business_type"],
        "theme": merged_theme,
        "sections": [s.copy() for s in template["sections"]],
        "meta": {"title": template["name"]},
        "template": template_id,
        "variant": variant_id,
    }


def list_variants_for_template(template_id: str) -> List[Dict[str, Any]]:
    """Return all 10 variants for a given business template, each with a stable id."""
    template = TEMPLATES.get(template_id) or TEMPLATES["blank"]
    out = []
    for v in STYLE_VARIANTS:
        merged_theme = {**template["theme"], **v["theme_override"]}
        out.append({
            "id": v["id"],
            "name": v["name"],
            "theme": merged_theme,
            "template_id": template_id,
            "business_type": template["business_type"],
        })
    return out
