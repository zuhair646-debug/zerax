"""
🍳 Creative Recipes — 30 pre-made design recipes that combine libs + shaders + assets.

A recipe is a complete "wow factor" blueprint the orchestrator can apply
in one shot instead of bargaining from scratch each request.

Usage:
  from modules.freebuild.creative_recipes import (
      get_recipe, find_recipe_for_intent, list_recipes
  )
  recipe = find_recipe_for_intent("اعمل لي موقع فضائي كوني")
  # → {id: "cosmic_immersive_landing", libraries: [...], shaders: [...]}
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.creative_recipes")

_RECIPES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "creative_recipes.json"
_CACHE: Dict[str, Any] = {}


def _load() -> Dict[str, Any]:
    if "data" not in _CACHE or _CACHE.get("path_mtime") != _RECIPES_PATH.stat().st_mtime:
        try:
            with open(_RECIPES_PATH, encoding="utf-8") as f:
                _CACHE["data"] = json.load(f)
                _CACHE["path_mtime"] = _RECIPES_PATH.stat().st_mtime
        except Exception as e:
            logger.error(f"failed to load recipes: {e}")
            _CACHE["data"] = {"recipes": []}
    return _CACHE["data"]


def list_recipes() -> List[Dict[str, Any]]:
    """All recipes (id + ar_label + category + vibe)."""
    data = _load()
    return [
        {"id": r["id"], "ar_label": r["ar_label"], "category": r["category"], "vibe": r["vibe"]}
        for r in data.get("recipes", [])
    ]


def get_recipe(recipe_id: str) -> Optional[Dict[str, Any]]:
    data = _load()
    for r in data.get("recipes", []):
        if r["id"] == recipe_id:
            return r
    return None


# Arabic + English keyword → recipe-id mapping for fast intent matching
_INTENT_KEYWORDS = {
    "cosmic_immersive_landing": ["كون", "فضاء", "كوكب", "نجم", "interstellar", "space", "cosmic", "nebula", "galaxy"],
    "fintech_dashboard_pro": ["فينتك", "تداول", "أسهم", "مالي", "تحليل", "fintech", "trading", "stocks", "portfolio", "dashboard"],
    "restaurant_pwa_warmth": ["مطعم", "مأكولات", "طبخ", "قهوة", "كافيه", "restaurant", "cafe", "food", "menu"],
    "saas_landing_minimal_luxe": ["saas", "منتج رقمي", "اشتراك", "subscription", "software"],
    "ecommerce_perfume_atelier": ["عطر", "عطور", "perfume", "fragrance", "أتيلييه", "بوتيك", "boutique"],
    "portfolio_brutalist_artist": ["فنان", "بورتفوليو", "brutalist", "brutalism", "artist", "portfolio"],
    "gaming_neon_arcade": ["لعبة", "ألعاب", "آركيد", "gaming", "arcade", "game", "esports", "synthwave"],
    "medical_clinic_calm": ["عيادة", "طبية", "صحة", "doctor", "clinic", "medical", "health"],
    "real_estate_luxury": ["عقار", "فيلا", "شقة", "real estate", "villa", "property", "apartment"],
    "education_kids_playful": ["أطفال", "تعليم أطفال", "kids", "preschool", "children"],
    "agency_creative_bold": ["وكالة", "agency", "branding", "creative agency"],
    "podcast_warm_audio": ["بودكاست", "podcast", "audio show"],
    "fitness_energetic_dark": ["لياقة", "جيم", "fitness", "gym", "workout"],
    "wedding_elegant_pastel": ["زفاف", "عرس", "wedding", "marriage"],
    "travel_explorer_vivid": ["سفر", "سياحة", "رحلات", "travel", "tourism", "trip"],
    "news_editorial_serious": ["أخبار", "جريدة", "news", "magazine", "editorial"],
    "blockchain_dao_futurist": ["بلوكتشين", "كريبتو", "web3", "blockchain", "crypto", "dao", "nft"],
    "kindergarten_soft_clouds": ["روضة", "حضانة", "kindergarten", "nursery"],
    "luxury_hotel_calm": ["فندق", "منتجع", "hotel", "resort"],
    "tech_conference_bold": ["مؤتمر", "حدث", "conference", "summit", "event"],
    "music_artist_immersive": ["موسيقي", "مغني", "music artist", "singer", "band"],
    "law_firm_authoritative": ["محاماة", "محامي", "قانون", "law firm", "lawyer", "attorney", "legal"],
    "nonprofit_hopeful": ["تبرع", "خيري", "nonprofit", "charity", "ngo", "donation"],
    "automotive_supercar": ["سيارة", "سوبر كار", "automotive", "supercar", "car"],
    "writers_blog_minimal": ["مدونة", "كاتب", "writer", "blog", "essays"],
    "saas_pricing_focused": ["تسعير", "pricing page", "plans"],
    "fashion_lookbook": ["أزياء", "موضة", "fashion", "lookbook", "clothing"],
    "developer_terminal": ["مطور", "developer", "terminal", "hacker"],
    "kids_storybook_interactive": ["قصة", "حكاية", "storybook", "children story"],
    "construction_industrial": ["إنشاءات", "بناء", "construction", "contractor"],
}


def find_recipe_for_intent(user_message: str) -> Optional[Dict[str, Any]]:
    """Return the best-matching recipe (or None) based on Arabic+English keywords."""
    if not user_message:
        return None
    msg = user_message.lower()
    best_id = None
    best_score = 0
    for rid, kws in _INTENT_KEYWORDS.items():
        score = sum(1 for kw in kws if kw.lower() in msg)
        if score > best_score:
            best_score = score
            best_id = rid
    if best_id and best_score >= 1:
        return get_recipe(best_id)
    return None


def recipe_to_prompt_hint(recipe: Dict[str, Any], max_chars: int = 800) -> str:
    """Render a recipe into a compact system-prompt hint."""
    if not recipe:
        return ""
    lines = [
        f"🎨 **Recipe: {recipe.get('ar_label', recipe.get('id', '?'))}** ({recipe.get('category', '?')})",
        f"**Vibe:** {recipe.get('vibe', '-')}",
        f"**Sections (use this order):** {' → '.join(recipe.get('sections', []))}",
        f"**Colors:** {', '.join(recipe.get('color_palette', []))}",
        f"**Fonts:** {', '.join(recipe.get('fonts', []))}",
    ]
    libs = recipe.get("libraries") or []
    if libs:
        lines.append(f"**Inject libraries:** {', '.join(libs)} (use `inject_library`)")
    shaders = recipe.get("shaders") or []
    if shaders:
        lines.append(f"**Inject shaders:** {', '.join(shaders)} (from shaders_library.json)")
    assets = recipe.get("assets") or []
    if assets:
        kinds = ", ".join(a.get("type", "?") for a in assets)
        lines.append(f"**Generate assets:** {kinds} (via VisualCortex / AudioCortex)")
    out = "\n".join(lines)
    return out[:max_chars]


def render_recipes_atlas(max_chars: int = 1800) -> str:
    """Render all recipes as a compact catalog for the system prompt."""
    data = _load()
    lines = [f"📖 **Creative Recipe Book — {len(data.get('recipes', []))} وصفة جاهزة:**"]
    for r in data.get("recipes", []):
        lines.append(f"  • `{r['id']}` ({r['category']}) — {r['ar_label']}: {r['vibe'][:80]}")
    out = "\n".join(lines)
    return out[:max_chars]
