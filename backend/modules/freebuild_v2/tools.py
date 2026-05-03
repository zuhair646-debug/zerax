"""
Tool Registry for the FreeBuild v2 Agent System.

Each tool is a callable async function with a JSON Schema describing its
arguments (compatible with OpenAI function-calling). The architect agent
can invoke any tool during a turn to fetch real data (Quran reciter URL,
verse text, web page content, sports results) instead of hallucinating.

Available tools (all production-ready, no extra API keys required):
    • quran_reciter_lookup   — verified mp3quran.net URLs
    • quran_verse_fetch      — real verse text via alquran.cloud API
    • web_fetch              — fetch + parse a real URL
    • web_search             — free DuckDuckGo HTML search
    • generate_image_url     — Nano Banana on-demand image
"""
from __future__ import annotations
import asyncio
import json
import logging
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
#  TOOL: Quran Reciter Lookup
# ════════════════════════════════════════════════════════════════════════
async def quran_reciter_lookup(name: str = "", surah: int = 1) -> Dict[str, Any]:
    """Find a verified Quran reciter by Arabic name keyword and return the
    real mp3quran.net URL for the requested surah. If `name` is empty,
    returns the full reciter library.
    """
    from .verified_sources import VERIFIED_QURAN_RECITERS, get_full_surah_url
    if not name:
        return {
            "ok": True,
            "count": len(VERIFIED_QURAN_RECITERS),
            "reciters": [
                {**r, "example_url": get_full_surah_url(r["slug"], r["server"], surah)}
                for r in VERIFIED_QURAN_RECITERS
            ],
        }
    name_lc = name.strip().lower()
    matches = []
    for r in VERIFIED_QURAN_RECITERS:
        if (name_lc in r["name"].lower()
                or name_lc in r["id"].lower()
                or name_lc in r["slug"].lower()):
            matches.append({
                **r,
                "url_fatihah": get_full_surah_url(r["slug"], r["server"], 1),
                "url_baqarah": get_full_surah_url(r["slug"], r["server"], 2),
                "requested_surah_url": get_full_surah_url(r["slug"], r["server"], surah),
            })
    return {"ok": True, "count": len(matches), "matches": matches}


# ════════════════════════════════════════════════════════════════════════
#  TOOL: Quran Verse Fetch (real text from alquran.cloud)
# ════════════════════════════════════════════════════════════════════════
async def quran_verse_fetch(surah: int, ayah: int) -> Dict[str, Any]:
    """Fetch the EXACT Arabic text of an ayah from the official alquran.cloud
    API (backed by Madinah Mushaf). Use this instead of writing verses yourself.
    """
    if not (1 <= surah <= 114):
        return {"ok": False, "error": "surah must be 1..114"}
    if ayah < 1:
        return {"ok": False, "error": "ayah must be >= 1"}
    url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/quran-uthmani"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
        if r.status_code != 200:
            return {"ok": False, "error": f"upstream {r.status_code}"}
        data = r.json()
        if data.get("code") != 200:
            return {"ok": False, "error": data.get("status", "unknown")}
        a = data.get("data", {})
        return {
            "ok": True,
            "surah": surah,
            "ayah": ayah,
            "surah_name_ar": a.get("surah", {}).get("name"),
            "surah_name_en": a.get("surah", {}).get("englishName"),
            "text": a.get("text", ""),
            "juz": a.get("juz"),
            "page": a.get("page"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}


# ════════════════════════════════════════════════════════════════════════
#  TOOL: Web Fetch (real URL → readable text + meta)
# ════════════════════════════════════════════════════════════════════════
async def web_fetch(url: str, max_chars: int = 5000) -> Dict[str, Any]:
    """Fetch a real webpage and return cleaned text + meta. Use when you need
    to verify/extract real-world content (product details, references)."""
    if not url.startswith("http"):
        return {"ok": False, "error": "url must start with http(s)"}
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0 ZitexBot"})
        if r.status_code >= 400:
            return {"ok": False, "error": f"HTTP {r.status_code}"}
        ct = r.headers.get("content-type", "")
        if "html" not in ct and "xml" not in ct:
            return {
                "ok": True, "url": url, "content_type": ct,
                "snippet": r.text[:max_chars],
            }
        soup = BeautifulSoup(r.text, "lxml")
        title = (soup.title.string or "").strip() if soup.title else ""
        meta_desc = ""
        m = soup.find("meta", attrs={"name": "description"})
        if m and m.get("content"):
            meta_desc = m["content"].strip()
        # Strip scripts/styles
        for s in soup(["script", "style", "noscript"]):
            s.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return {
            "ok": True, "url": url, "title": title,
            "description": meta_desc, "text": text[:max_chars],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}


# ════════════════════════════════════════════════════════════════════════
#  TOOL: Web Search (DuckDuckGo HTML - no API key needed)
# ════════════════════════════════════════════════════════════════════════
async def web_search(query: str, num: int = 5) -> Dict[str, Any]:
    """Search the web. Returns top results with title + url + snippet.
    Uses DuckDuckGo HTML interface (free, no API key)."""
    if not query.strip():
        return {"ok": False, "error": "empty query"}
    # Try lite endpoint first — better for bots
    endpoints = [
        ("https://lite.duckduckgo.com/lite/", "POST", {"q": query}),
        ("https://html.duckduckgo.com/html/", "POST", {"q": query}),
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "ar,en;q=0.9",
    }
    for url, method, data in endpoints:
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                if method == "POST":
                    r = await client.post(url, data=data, headers=headers)
                else:
                    r = await client.get(url, params=data, headers=headers)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "lxml")
            results: List[Dict[str, str]] = []
            # Lite layout: each result is a <td class="result-link"><a>
            for a in soup.select("a.result-link")[:num]:
                href = a.get("href", "")
                title = a.get_text(strip=True)
                if href and title:
                    results.append({"title": title[:200], "url": href, "snippet": ""})
            # HTML layout
            if not results:
                for li in soup.select("div.result")[:num]:
                    a = li.select_one("a.result__a")
                    snip = li.select_one(".result__snippet")
                    if a and a.get("href"):
                        results.append({
                            "title": a.get_text(strip=True)[:200],
                            "url": a["href"],
                            "snippet": (snip.get_text(strip=True) if snip else "")[:300],
                        })
            # Generic fallback: any external link
            if not results:
                for a in soup.select("a")[:50]:
                    href = a.get("href", "")
                    title = a.get_text(strip=True)
                    if (href.startswith("http") and "duckduckgo.com" not in href
                            and len(title) > 10):
                        results.append({"title": title[:200], "url": href, "snippet": ""})
                        if len(results) >= num:
                            break
            if results:
                return {"ok": True, "query": query, "count": len(results), "results": results}
        except Exception as e:
            logger.warning(f"[web_search] {url}: {e}")
            continue
    return {"ok": False, "error": "search providers unavailable"}


# ════════════════════════════════════════════════════════════════════════
#  TOOL: Generate Image URL (Nano Banana on-demand)
# ════════════════════════════════════════════════════════════════════════
async def generate_image_url(description: str, style_seed: str = "") -> Dict[str, Any]:
    """Generate a real AI image (Nano Banana) for a vivid Arabic description
    and return a public URL the architect can drop into <img src='...'>."""
    from .image_gen import generate_image
    url = await generate_image(description, style_seed=style_seed)
    if not url:
        return {"ok": False, "error": "generation failed"}
    return {"ok": True, "url": url}


# ════════════════════════════════════════════════════════════════════════
#  TOOL REGISTRY (OpenAI function-calling schema)
# ════════════════════════════════════════════════════════════════════════
TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "quran_reciter_lookup",
            "description": (
                "Find a verified Quran reciter by Arabic name keyword (e.g. 'السديس', "
                "'العفاسي', 'الحصري'). Returns the EXACT mp3quran.net audio URLs. "
                "Use this whenever you need to embed audio in a Quran site — never "
                "invent reciter URLs yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Arabic name keyword, or empty for full library"},
                    "surah": {"type": "integer", "description": "Surah number 1-114", "default": 1},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "quran_verse_fetch",
            "description": (
                "Fetch the EXACT Arabic text of a Quran verse from the official "
                "alquran.cloud API. Use this instead of writing verses yourself "
                "(LLMs corrupt Arabic diacritics)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "surah": {"type": "integer", "description": "1-114"},
                    "ayah": {"type": "integer", "description": "verse number"},
                },
                "required": ["surah", "ayah"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web (DuckDuckGo) for real-world references, examples, "
                "competitor sites, statistics, news. Returns top 5 results with URLs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "num": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": (
                "Fetch the actual text content of a real URL. Use after web_search "
                "to verify/extract details from the most relevant pages."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "max_chars": {"type": "integer", "default": 5000},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image_url",
            "description": (
                "Generate a real AI image (Nano Banana) for a vivid Arabic description "
                "and return a public URL for use in <img src=...>. Use sparingly — "
                "prefer @@IMG/auto@@ placeholders that the post-processor handles."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "Vivid Arabic description"},
                    "style_seed": {"type": "string", "default": ""},
                },
                "required": ["description"],
            },
        },
    },
]


# Map of tool name → callable
TOOL_REGISTRY: Dict[str, Callable[..., Awaitable[Dict[str, Any]]]] = {
    "quran_reciter_lookup": quran_reciter_lookup,
    "quran_verse_fetch": quran_verse_fetch,
    "web_search": web_search,
    "web_fetch": web_fetch,
    "generate_image_url": generate_image_url,
}


async def execute_tool_call(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch a tool call by name with sanitized args."""
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return {"ok": False, "error": f"unknown tool: {name}"}
    try:
        return await fn(**(args or {}))
    except TypeError as e:
        return {"ok": False, "error": f"invalid arguments: {e}"}
    except Exception as e:
        logger.exception(f"[TOOL:{name}] crashed")
        return {"ok": False, "error": str(e)[:200]}
