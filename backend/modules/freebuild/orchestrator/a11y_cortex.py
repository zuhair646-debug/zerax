"""
♿ Accessibility Cortex — WCAG 2.1 AA audit + auto-fix common issues.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


def audit(html: str) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    # 1. Images without alt
    imgs = re.finditer(r"<img\b([^>]*?)/?>", html, re.IGNORECASE)
    missing_alt = 0
    for m in imgs:
        attrs = m.group(1)
        if not re.search(r'\salt=', attrs, re.IGNORECASE):
            missing_alt += 1
    if missing_alt:
        issues.append({"wcag": "1.1.1", "severity": "high",
                       "issue": f"{missing_alt} صورة بدون alt"})

    # 2. Icon-only buttons without aria-label
    btn_icons = re.findall(r'<button[^>]*>\s*<(?:i|svg|span class="(?:fa|icon)[^"]*")[^>]*>(?:</[^>]+>)?\s*</button>', html, re.IGNORECASE)
    btn_with_label = re.findall(r'<button[^>]*\saria-label=["\'][^"\']+["\'][^>]*>\s*<(?:i|svg|span class="(?:fa|icon)[^"]*")', html, re.IGNORECASE)
    icon_btns_missing = len(btn_icons) - len(btn_with_label)
    if icon_btns_missing > 0:
        issues.append({"wcag": "4.1.2", "severity": "high",
                       "issue": f"{icon_btns_missing} زر بأيقونة فقط بدون aria-label"})

    # 3. Form inputs without labels
    inputs = re.findall(r'<input\b(?![^>]*type=["\'](?:hidden|submit|button)["\'])[^>]*>', html, re.IGNORECASE)
    labels = re.findall(r"<label\b[^>]*>", html, re.IGNORECASE)
    if len(inputs) > len(labels):
        issues.append({"wcag": "3.3.2", "severity": "medium",
                       "issue": f"{len(inputs) - len(labels)} input بدون <label> مرتبط"})

    # 4. Empty links / buttons
    empty_a = re.findall(r"<a\b[^>]*>\s*</a>", html, re.IGNORECASE)
    if empty_a:
        issues.append({"wcag": "2.4.4", "severity": "high",
                       "issue": f"{len(empty_a)} رابط فاضي"})

    # 5. Missing lang attribute
    if not re.search(r'<html[^>]*\slang=["\']', html[:500], re.IGNORECASE):
        issues.append({"wcag": "3.1.1", "severity": "medium", "issue": "<html> بدون lang attribute"})

    # 6. Skip-link missing (for keyboard users)
    if not re.search(r'<a[^>]*href=["\']#main[^"\']*["\']', html[:1500], re.IGNORECASE):
        issues.append({"wcag": "2.4.1", "severity": "low",
                       "issue": "بدون skip-to-main-content link"})

    # 7. Heading order (h1 → h2 → h3 etc.)
    headings = re.findall(r"<h([1-6])\b", html, re.IGNORECASE)
    last = 0
    for h in headings:
        n = int(h)
        if last and n > last + 1:
            issues.append({"wcag": "1.3.1", "severity": "low",
                           "issue": f"تخطي مستويات heading من H{last} لـ H{n}"})
            break
        last = n

    return {"issues": issues, "score": max(0, 100 - len(issues) * 10)}


def auto_fix_alt_text(html: str, default_alt: str = "") -> str:
    """Add empty alt="" to <img> without alt (decorative-by-default)."""
    def _fix(m: re.Match) -> str:
        tag = m.group(0)
        if re.search(r'\salt=', tag, re.IGNORECASE):
            return tag
        return tag[:-1].rstrip() + f' alt="{default_alt}">'
    return re.sub(r"<img\b[^>]*>", _fix, html, flags=re.IGNORECASE)


def auto_fix_lang_attribute(html: str, lang: str = "ar") -> str:
    """Add lang attribute to <html> if missing."""
    if re.search(r'<html[^>]*\slang=["\']', html[:500], re.IGNORECASE):
        return html
    return re.sub(r"<html\b", f'<html lang="{lang}" dir="{"rtl" if lang.startswith("ar") else "ltr"}"', html, count=1, flags=re.IGNORECASE)


def inject_skip_link(html: str) -> str:
    """Add a skip-to-main link after <body>."""
    if re.search(r'<a[^>]*href=["\']#main', html, re.IGNORECASE):
        return html
    skip = (
        '<a href="#main" class="skip-link" style="position:absolute;left:-9999px;top:0;'
        'background:#000;color:#fff;padding:8px;z-index:9999;" '
        'onfocus="this.style.left=\'0\'" onblur="this.style.left=\'-9999px\'">تخطي إلى المحتوى</a>'
    )
    return re.sub(r"(<body\b[^>]*>)", r"\1\n" + skip, html, count=1, flags=re.IGNORECASE)
