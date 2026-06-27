"""
🔍 SEO Cortex — injects schema.org JSON-LD, sitemap, robots, meta tags.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


def build_jsonld(schema_type: str, data: Dict[str, Any]) -> str:
    """Build schema.org JSON-LD for a given type (Organization, Product, Article, LocalBusiness, etc)."""
    ld = {"@context": "https://schema.org", "@type": schema_type, **data}
    return f'<script type="application/ld+json">\n{json.dumps(ld, ensure_ascii=False, indent=2)}\n</script>'


def build_meta_tags(
    title: str,
    description: str,
    canonical_url: Optional[str] = None,
    og_image: Optional[str] = None,
    twitter_card: str = "summary_large_image",
    lang: str = "ar",
) -> str:
    """Build a complete <head> meta block."""
    parts = [
        f'<title>{_escape(title)}</title>',
        f'<meta name="description" content="{_escape(description)}">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta charset="UTF-8">',
        f'<meta property="og:title" content="{_escape(title)}">',
        f'<meta property="og:description" content="{_escape(description)}">',
        f'<meta property="og:type" content="website">',
        f'<meta name="twitter:card" content="{twitter_card}">',
        f'<meta name="twitter:title" content="{_escape(title)}">',
        f'<meta name="twitter:description" content="{_escape(description)}">',
    ]
    if canonical_url:
        parts.append(f'<link rel="canonical" href="{canonical_url}">')
        parts.append(f'<meta property="og:url" content="{canonical_url}">')
    if og_image:
        parts.append(f'<meta property="og:image" content="{og_image}">')
        parts.append(f'<meta name="twitter:image" content="{og_image}">')
    return "\n".join(parts)


def build_sitemap_xml(urls: List[Dict[str, Any]], base_url: str = "https://example.com") -> str:
    """Build sitemap.xml from list of {loc, lastmod, priority}."""
    items = []
    for u in urls:
        loc = u.get("loc", "/")
        full = loc if loc.startswith("http") else f"{base_url.rstrip('/')}{loc}"
        items.append(
            f"  <url>\n    <loc>{full}</loc>\n"
            f"    <lastmod>{u.get('lastmod', '2026-02-01')}</lastmod>\n"
            f"    <changefreq>{u.get('changefreq', 'weekly')}</changefreq>\n"
            f"    <priority>{u.get('priority', '0.8')}</priority>\n  </url>"
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(items)}
</urlset>"""


def build_robots_txt(sitemap_url: str = "/sitemap.xml", disallow: Optional[List[str]] = None) -> str:
    lines = ["User-agent: *"]
    for path in (disallow or []):
        lines.append(f"Disallow: {path}")
    lines.append("Allow: /")
    lines.append(f"Sitemap: {sitemap_url}")
    return "\n".join(lines)


def audit_seo(html: str) -> Dict[str, Any]:
    """Audit an HTML page for SEO completeness."""
    issues = []
    head_m = re.search(r"<head>([\s\S]*?)</head>", html, re.IGNORECASE)
    head = head_m.group(1) if head_m else ""
    title_m = re.search(r"<title>([^<]+)</title>", head, re.IGNORECASE)
    if not title_m or len(title_m.group(1)) < 5:
        issues.append({"severity": "high", "issue": "<title> ناقص أو قصير"})
    elif len(title_m.group(1)) > 60:
        issues.append({"severity": "medium", "issue": f"<title> طويل ({len(title_m.group(1))} حرف، الأمثل 50-60)"})
    if not re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)', head, re.IGNORECASE):
        issues.append({"severity": "high", "issue": "missing meta description"})
    if not re.search(r'<meta\s+property=["\']og:image["\']', head, re.IGNORECASE):
        issues.append({"severity": "medium", "issue": "missing og:image"})
    if not re.search(r'<link\s+rel=["\']canonical["\']', head, re.IGNORECASE):
        issues.append({"severity": "low", "issue": "missing canonical link"})
    if not re.search(r'application/ld\+json', head, re.IGNORECASE):
        issues.append({"severity": "medium", "issue": "no schema.org JSON-LD"})
    return {"issues": issues, "score": max(0, 100 - len(issues) * 15)}


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
