"""
⚡ Performance Optimizer — analyzes HTML/JS/CSS and suggests/applies optimizations.

  - Lazy-load below-the-fold images (loading="lazy")
  - Inline critical CSS, defer rest
  - Add async/defer to script tags
  - Compress base64 → external file references
  - Detect unminified inline JS (>50 lines)
  - Suggest code splitting opportunities
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger("zenrex.performance")


def analyze(html: str) -> Dict[str, Any]:
    issues: List[Dict[str, str]] = []
    suggestions: List[Dict[str, str]] = []

    # Images without lazy loading
    imgs = re.findall(r"<img[^>]*>", html, re.IGNORECASE)
    lazy_imgs = re.findall(r'<img[^>]*\sloading=["\']lazy["\'][^>]*>', html, re.IGNORECASE)
    non_lazy = len(imgs) - len(lazy_imgs)
    if non_lazy > 3:
        suggestions.append({"category": "images", "issue": f"{non_lazy} صورة بدون loading=lazy",
                            "fix": "أضف loading='lazy' لكل صورة تحت الـ fold"})

    # Scripts without async/defer
    scripts = re.findall(r"<script\s+[^>]*src=", html, re.IGNORECASE)
    async_defer = re.findall(r"<script[^>]*(?:async|defer)[^>]*src=", html, re.IGNORECASE)
    blocking = len(scripts) - len(async_defer)
    if blocking > 1:
        suggestions.append({"category": "scripts", "issue": f"{blocking} script بدون async/defer",
                            "fix": "أضف defer لكل <script src> غير حرج"})

    # Inline JS > 50 lines = code split candidate
    inline_js = re.findall(r"<script(?![^>]*\ssrc=)[^>]*>([\s\S]*?)</script>", html, re.IGNORECASE)
    for js in inline_js:
        lines = js.count("\n")
        if lines > 50:
            suggestions.append({"category": "code_split", "issue": f"inline <script> بـ {lines} سطر",
                                "fix": "انقل لملف .js مع defer"})
            break

    # Base64 images > 50KB
    b64 = re.findall(r"data:image/[a-z]+;base64,([A-Za-z0-9+/=]+)", html)
    large_b64 = [b for b in b64 if len(b) > 50000]
    if large_b64:
        suggestions.append({"category": "base64", "issue": f"{len(large_b64)} صورة base64 ضخمة",
                            "fix": "احفظها كملف وحمّلها كـ URL"})

    # Missing viewport
    if not re.search(r'<meta[^>]*name=["\']viewport["\']', html, re.IGNORECASE):
        issues.append({"category": "mobile", "severity": "high",
                       "issue": "بدون viewport meta — الموبايل سيتعطل"})

    # Heavy CSS @import chains
    imports = re.findall(r"@import\s+url", html, re.IGNORECASE)
    if len(imports) > 2:
        suggestions.append({"category": "css", "issue": f"{len(imports)} @import يبطّئ التحميل",
                            "fix": "ادمج CSS أو استخدم <link>"})

    return {
        "total_images": len(imgs),
        "lazy_images": len(lazy_imgs),
        "blocking_scripts": blocking,
        "inline_js_blocks": len(inline_js),
        "large_base64": len(large_b64),
        "issues": issues,
        "suggestions": suggestions,
        "score": max(0, 100 - len(issues) * 15 - len(suggestions) * 5),
    }


def apply_lazy_loading(html: str) -> str:
    """Auto-add loading='lazy' to all img tags that don't have it."""
    def _add(m: re.Match) -> str:
        tag = m.group(0)
        if "loading=" in tag.lower():
            return tag
        return tag[:-1].rstrip() + ' loading="lazy" decoding="async">'
    return re.sub(r"<img\b[^>]*>", _add, html, flags=re.IGNORECASE)


def apply_defer_to_scripts(html: str) -> str:
    """Auto-add defer to external <script src>."""
    def _add(m: re.Match) -> str:
        tag = m.group(0)
        if "async" in tag or "defer" in tag or 'type="module"' in tag:
            return tag
        return tag.replace("<script", "<script defer", 1)
    return re.sub(r"<script\s+[^>]*src=[^>]*>", _add, html, flags=re.IGNORECASE)
