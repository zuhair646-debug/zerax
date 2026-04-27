"""Logo + Hero image generation — uses OpenAI gpt-image-1 via Emergent LLM key."""
import os
import base64
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


async def _generate(prompt: str, system_hint: str) -> Optional[str]:
    """Generate an image and return a data URL, or None on failure."""
    try:
        from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
    except Exception as e:
        logger.error(f"emergentintegrations not available: {e}")
        return None

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.error("EMERGENT_LLM_KEY not set")
        return None

    try:
        image_gen = OpenAIImageGeneration(api_key=api_key)
        full_prompt = f"{system_hint}\n\n{prompt}"
        images = await image_gen.generate_images(
            prompt=full_prompt,
            model="gpt-image-1",
            number_of_images=1,
        )
        if not images:
            return None
        b64 = base64.b64encode(images[0]).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        logger.error(f"image generation error: {e}", exc_info=True)
        return None


async def generate_logo(prompt: str, style_hint: str = "") -> Optional[Tuple[str, str]]:
    """Returns (data_url, session_id) or None."""
    system_hint = (
        "Create a PROFESSIONAL MODERN LOGO. Requirements: clean, minimal, flat design, "
        "memorable iconography, high contrast, symmetric composition, balanced typography if any text, "
        "solid or neutral background, suitable for a website header. "
        f"Style preference: {style_hint or 'modern minimalist'}."
    )
    data_url = await _generate(prompt, system_hint)
    if not data_url:
        return None
    return data_url, "logo"


async def generate_logo_variants(prompt: str, style_hint: str = "", count: int = 3, color_hint: str = "") -> list:
    """Generate N distinct logo variants in PARALLEL. Returns a list of data URLs (may be shorter than N on failures)."""
    import asyncio
    # Slight prompt perturbations so each variant looks different
    perturbations = [
        "variation: symmetric icon-forward layout",
        "variation: wordmark-focused, clean typography",
        "variation: emblem / badge style with subtle flourish",
        "variation: geometric abstract mark",
        "variation: monogram-based mark",
    ]
    color_clause = f" Use color palette: {color_hint}." if color_hint else ""
    base_system = (
        "Create a PROFESSIONAL MODERN LOGO. Clean, minimal, flat design, memorable icon, "
        "high contrast, symmetric composition, balanced typography, suitable for a website header."
        + color_clause
        + f" Style preference: {style_hint or 'modern minimalist'}."
    )
    tasks = []
    for i in range(max(1, min(count, 4))):
        sys_hint = f"{base_system}\n{perturbations[i % len(perturbations)]}"
        tasks.append(_generate(prompt, sys_hint))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, str) and r]


async def generate_hero_image(prompt: str) -> Optional[str]:
    system_hint = (
        "Cinematic wide hero image for a website banner, 16:9 orientation, "
        "high-quality photograph or premium illustration, appropriate lighting, "
        "suitable as a page header background."
    )
    return await _generate(prompt, system_hint)
