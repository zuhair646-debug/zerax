"""
🎨 Shaders Library — GLSL + CSS shader/postfx loader.

Loads /app/backend/data/shaders_library.json and provides:
  - get_shader(shader_id) → full snippet
  - find_shaders_for_intent(message) → list of matching shader IDs
  - render_shader_catalog() → compact prompt hint

Each shader is either:
  - GLSL fragment_shader (Three.js ShaderMaterial)
  - CSS-only snippet (no JS needed)
  - JS snippet (Canvas2D / Web Audio)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.shaders")

_SHADERS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "shaders_library.json"
_CACHE: Dict[str, Any] = {}


def _load() -> Dict[str, Any]:
    if "data" not in _CACHE or _CACHE.get("path_mtime") != _SHADERS_PATH.stat().st_mtime:
        try:
            with open(_SHADERS_PATH, encoding="utf-8") as f:
                _CACHE["data"] = json.load(f)
                _CACHE["path_mtime"] = _SHADERS_PATH.stat().st_mtime
        except Exception as e:
            logger.error(f"failed to load shaders: {e}")
            _CACHE["data"] = {"shaders": {}}
    return _CACHE["data"]


def get_shader(shader_id: str) -> Optional[Dict[str, Any]]:
    data = _load()
    return data.get("shaders", {}).get(shader_id)


def list_shaders() -> List[Dict[str, str]]:
    data = _load()
    return [
        {"id": sid, "name": s.get("name", sid), "ar_label": s.get("ar_label", ""), "category": s.get("category", "")}
        for sid, s in data.get("shaders", {}).items()
    ]


_INTENT_KEYWORDS = {
    "nebula": ["سديم", "كون", "فضاء", "nebula", "cosmic", "space"],
    "starfield": ["نجوم", "stars", "starfield"],
    "bloom_postfx": ["bloom", "إشعاع", "وهج", "glow"],
    "glitch": ["glitch", "تشويش", "كسر"],
    "scanlines": ["scanlines", "crt", "خطوط شاشة"],
    "matrix_rain": ["matrix", "ماتركس", "هاكر", "hacker"],
    "wireframe": ["wireframe", "هيكل سلكي", "wire"],
    "chromatic_aberration": ["chromatic", "rgb split"],
    "neon_glow": ["neon", "نيون", "وهج نيون"],
    "audio_visualizer": ["audio visualizer", "مرئيات صوت", "waveform"],
    "particle_burst": ["particles", "جسيمات", "burst", "انفجار"],
    "liquid_distortion": ["liquid", "سائل", "distortion"],
    "film_grain": ["film grain", "حبيبات فيلم"],
    "grain_overlay": ["grain", "حبيبات", "noise paper"],
    "halftone": ["halftone", "هاف-تون", "نقاط طباعة"],
    "dither": ["dither", "ديذر"],
    "chrome_reflection": ["chrome", "كروم", "انعكاس"],
    "carbon_fiber": ["carbon", "كربون"],
    "lens_flare": ["lens flare", "وهج عدسة"],
    "rgb_split": ["rgb split"],
    "vhs": ["vhs", "فيديو قديم"],
    "crt": ["crt", "شاشة قديمة"],
    "motion_blur": ["motion blur", "تشويش حركي"],
    "soft_blur": ["soft blur", "ضبابية"],
    "depth_blur": ["depth of field", "depth blur"],
    "audio_visualizer_simple": ["audio bars", "أعمدة صوت"],
    "paper_texture": ["paper", "ورقي", "ورق"],
    "gradient_mesh": ["gradient mesh", "تدرج"],
    "noise": ["noise", "ضوضاء"],
}


def find_shaders_for_intent(user_message: str, max_results: int = 4) -> List[str]:
    """Return matching shader IDs sorted by relevance."""
    if not user_message:
        return []
    msg = user_message.lower()
    scores: Dict[str, int] = {}
    for sid, kws in _INTENT_KEYWORDS.items():
        s = sum(1 for kw in kws if kw.lower() in msg)
        if s > 0:
            scores[sid] = s
    return [sid for sid, _ in sorted(scores.items(), key=lambda x: -x[1])[:max_results]]


def render_shader_for_inject(shader_id: str) -> Optional[Dict[str, str]]:
    """Get ready-to-inject CSS/JS for a given shader. Returns {kind: 'css|js|three', code, head_inject, body_inject}."""
    s = get_shader(shader_id)
    if not s:
        return None
    if s.get("css_snippet"):
        return {
            "kind": "css",
            "head_inject": f"<style data-shader=\"{shader_id}\">\n{s['css_snippet']}\n</style>",
            "body_inject": "",
            "name": s.get("name", shader_id),
        }
    if s.get("js_snippet"):
        return {
            "kind": "js",
            "head_inject": "",
            "body_inject": f"<script data-shader=\"{shader_id}\">\n{s['js_snippet']}\n</script>",
            "name": s.get("name", shader_id),
        }
    if s.get("init_snippet_three"):
        return {
            "kind": "three",
            "head_inject": "",
            "body_inject": f"<!-- Three.js shader snippet for {s['name']} -->\n<!-- {s['init_snippet_three']} -->",
            "code": s["init_snippet_three"],
            "fragment_shader": s.get("fragment_shader", ""),
            "name": s.get("name", shader_id),
        }
    return None


def render_shader_catalog(max_chars: int = 1400) -> str:
    """Compact catalog for system prompt."""
    data = _load()
    lines = [f"🎨 **Shaders & Post-FX — {len(data.get('shaders', {}))} effect جاهز:**"]
    for sid, s in data.get("shaders", {}).items():
        lines.append(f"  • `{sid}` ({s.get('category', '?')}) — {s.get('ar_label', s.get('name', sid))}")
    return "\n".join(lines)[:max_chars]
