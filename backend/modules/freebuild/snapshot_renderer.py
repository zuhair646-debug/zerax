"""
Design-Archive Screenshot Renderer
──────────────────────────────────
Renders an HTML snapshot to a real PNG using headless Chromium. Used by the
Design Archive (المحفوظات) to give the user true visual thumbnails of every
saved design — instead of broken iframe srcdoc previews that miss external
CSS / assets.

Two entry points:
- render_png(html, *, width=1280, full_page=True) → bytes (PNG)
- render_png_base64(html, **kwargs) → str (data: URL ready)

Both are async-safe. Chromium is launched per call (cold-start ~1s) which is
acceptable for an owner-facing archive view. For production traffic we can
later move this to a long-running browser pool.
"""
from __future__ import annotations

import asyncio
import base64
import logging
from typing import Optional

_logger = logging.getLogger(__name__)

# Chromium binary path — set by Docker image, fallback to common locations.
_CHROMIUM_CANDIDATES = [
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
]


def _chromium_path() -> Optional[str]:
    import os
    for p in _CHROMIUM_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


async def render_png(
    html: str,
    *,
    width: int = 1280,
    height: int = 800,
    full_page: bool = True,
    thumbnail_max_width: Optional[int] = None,
    timeout_ms: int = 15000,
) -> Optional[bytes]:
    """Render HTML → PNG bytes. Returns None on failure (never raises)."""
    if not html or len(html) < 30:
        return None
    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        _logger.warning(f"playwright unavailable: {e}")
        return None
    exe = _chromium_path()
    try:
        async with async_playwright() as pw:
            launch_kwargs = {"args": ["--no-sandbox", "--disable-dev-shm-usage"]}
            if exe:
                launch_kwargs["executable_path"] = exe
            browser = await pw.chromium.launch(**launch_kwargs)
            try:
                page = await browser.new_page(viewport={"width": width, "height": height})
                page.set_default_timeout(timeout_ms)
                await page.set_content(html, wait_until="domcontentloaded", timeout=timeout_ms)
                # Tiny settle for fonts / images.
                try:
                    await page.wait_for_load_state("networkidle", timeout=3500)
                except Exception:
                    pass
                png = await page.screenshot(type="png", full_page=full_page)
                if thumbnail_max_width and thumbnail_max_width < width:
                    png = await _downscale_png(png, target_width=thumbnail_max_width)
                return png
            finally:
                await browser.close()
    except Exception as e:
        _logger.warning(f"render_png failed: {e}")
        return None


async def _downscale_png(png_bytes: bytes, *, target_width: int) -> bytes:
    """Best-effort downscale using Pillow if available. Returns original on failure."""
    try:
        from PIL import Image
        import io as _io
        img = Image.open(_io.BytesIO(png_bytes))
        if img.width <= target_width:
            return png_bytes
        ratio = target_width / img.width
        new_h = int(img.height * ratio)
        # Aspect-preserving down-scale.
        # Lanczos enum lookup: Pillow ≥9 uses Image.Resampling.LANCZOS; older
        # versions exposed Image.LANCZOS directly.
        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", 1)
        img2 = img.resize((target_width, new_h), resample)
        out = _io.BytesIO()
        img2.save(out, format="PNG", optimize=True)
        return out.getvalue()
    except Exception as e:
        _logger.warning(f"downscale failed: {e}")
        return png_bytes


async def render_png_base64(html: str, **kwargs) -> Optional[str]:
    png = await render_png(html, **kwargs)
    if not png:
        return None
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


# Synchronous wrapper for fire-and-forget background tasks. NEVER call this
# from an async context — use `await render_png` instead.
def render_png_sync(html: str, **kwargs) -> Optional[bytes]:
    try:
        return asyncio.run(render_png(html, **kwargs))
    except Exception:
        return None
