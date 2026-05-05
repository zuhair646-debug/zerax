"""
Tool Registry for the Zitex Agent System.

Each tool is a callable async function with a JSON Schema describing its
arguments (compatible with OpenAI function-calling). The agent can invoke
any tool during a turn to fetch real data, generate media, or build
websites — instead of hallucinating.

Available tools:
    • quran_reciter_lookup   — verified mp3quran.net URLs
    • quran_verse_fetch      — real verse text via alquran.cloud API
    • web_fetch              — fetch + parse a real URL
    • web_search             — free DuckDuckGo HTML search
    • generate_image_url     — Nano Banana on-demand image
    • saudi_official_sources — verified Saudi institution sources
    • sports_team_lookup     — TheSportsDB real player rosters
    • build_website          — generate complete HTML SPA from a brief
    • update_website         — surgical edit existing site
    • generate_audio         — ElevenLabs sound/music generation
"""
from __future__ import annotations
import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import uuid
from pathlib import Path
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
#  TOOL: Saudi Official Sources Lookup
# ════════════════════════════════════════════════════════════════════════
async def saudi_official_sources(domain: str) -> Dict[str, Any]:
    """Return verified Saudi government / official sources for a given domain.
    Use this whenever the user asks for a Saudi-context site (education, health,
    sports, government services, real estate, etc) so the AI references real
    institutions instead of inventing them.
    """
    sources = {
        "education": [
            {"name": "وزارة التعليم", "url": "https://moe.gov.sa", "desc": "الجهة الرسمية للتعليم في المملكة"},
            {"name": "هيئة تقويم التعليم والتدريب", "url": "https://etec.gov.sa", "desc": "الجهة المُعتمِدة للمؤسسات التعليمية"},
            {"name": "منصة مدرستي", "url": "https://schools.madrasati.sa", "desc": "المنصة الرسمية للتعليم عن بُعد"},
            {"name": "منصة FutureX", "url": "https://www.futurex.sa", "desc": "تدريب مهني معتمد"},
            {"name": "رواق", "url": "https://www.rwaq.org", "desc": "أكبر منصة تعليم عربية مفتوحة"},
            {"name": "جامعة الملك سعود", "url": "https://www.ksu.edu.sa"},
            {"name": "جامعة الإمام محمد بن سعود الإسلامية", "url": "https://www.imamu.edu.sa"},
            {"name": "الجامعة الإسلامية بالمدينة المنورة", "url": "https://www.iu.edu.sa"},
        ],
        "health": [
            {"name": "وزارة الصحة", "url": "https://moh.gov.sa"},
            {"name": "صحة (مركز موثق)", "url": "https://sehha.sa"},
            {"name": "الهيئة السعودية للتخصصات الصحية", "url": "https://scfhs.org.sa"},
            {"name": "مستشفى الملك فيصل التخصصي", "url": "https://kfshrc.edu.sa"},
            {"name": "تطبيق صحتي", "url": "https://www.moh.gov.sa/eServices/Pages/sehhty-app.aspx"},
            {"name": "تطبيق توكلنا الصحة", "url": "https://ta.sdaia.gov.sa"},
        ],
        "sports": [
            {"name": "وزارة الرياضة", "url": "https://mos.gov.sa"},
            {"name": "الهيئة العامة للرياضة (سابقاً)", "url": "https://www.gsa.gov.sa"},
            {"name": "الاتحاد السعودي لكرة القدم", "url": "https://www.saff.com.sa"},
            {"name": "دوري روشن السعودي", "url": "https://www.spl.com.sa"},
            {"name": "نادي الهلال", "url": "https://www.alhilal.com"},
            {"name": "نادي النصر", "url": "https://www.alnassr.sa"},
            {"name": "نادي الاتحاد", "url": "https://www.ittihadclub.com.sa"},
            {"name": "نادي الأهلي", "url": "https://www.alahli.sa"},
        ],
        "religion": [
            {"name": "وزارة الشؤون الإسلامية والدعوة والإرشاد", "url": "https://www.moia.gov.sa"},
            {"name": "الرئاسة العامة لشؤون المسجد الحرام والمسجد النبوي", "url": "https://www.gph.gov.sa"},
            {"name": "مجمع الملك فهد لطباعة المصحف الشريف", "url": "https://qurancomplex.gov.sa"},
            {"name": "هيئة كبار العلماء", "url": "https://senagate.alifta.gov.sa"},
            {"name": "رابطة العالم الإسلامي", "url": "https://themwl.org/ar"},
        ],
        "ecommerce": [
            {"name": "هيئة التجارة الإلكترونية", "url": "https://mc.gov.sa"},
            {"name": "معروف (تحقق المتاجر)", "url": "https://maroof.sa"},
            {"name": "وزارة التجارة", "url": "https://mc.gov.sa"},
            {"name": "هيئة المنشآت الصغيرة (منشآت)", "url": "https://www.monshaat.gov.sa"},
        ],
        "government": [
            {"name": "منصة أبشر", "url": "https://www.absher.sa"},
            {"name": "منصة توكلنا", "url": "https://ta.sdaia.gov.sa"},
            {"name": "بوابة العمل عن بُعد", "url": "https://amlmenbiad.com"},
            {"name": "منصة ناجز (وزارة العدل)", "url": "https://najiz.sa"},
        ],
        "realestate": [
            {"name": "وزارة الشؤون البلدية والقروية والإسكان", "url": "https://www.momra.gov.sa"},
            {"name": "هيئة العقار", "url": "https://rega.gov.sa"},
            {"name": "صندوق التنمية العقارية (سكني)", "url": "https://sakani.sa"},
            {"name": "إيجار", "url": "https://www.ejar.sa"},
        ],
        "tech": [
            {"name": "وزارة الاتصالات وتقنية المعلومات", "url": "https://www.mcit.gov.sa"},
            {"name": "هيئة الاتصالات وتقنية المعلومات (CITC)", "url": "https://citc.gov.sa"},
            {"name": "الهيئة السعودية للذكاء الاصطناعي (سدايا)", "url": "https://sdaia.gov.sa"},
            {"name": "الاتحاد السعودي للأمن السيبراني", "url": "https://safcsp.org.sa"},
        ],
    }
    domain_lc = (domain or "").lower().strip()
    # Heuristic mapping
    cat = "government"
    if any(k in domain_lc for k in ["تعليم", "education", "school", "academy", "مدرس"]):
        cat = "education"
    elif any(k in domain_lc for k in ["صحة", "health", "طب", "clinic", "مستشفى"]):
        cat = "health"
    elif any(k in domain_lc for k in ["رياض", "sports", "كرة", "نادي"]):
        cat = "sports"
    elif any(k in domain_lc for k in ["قرآن", "إسلام", "religion", "دين", "مسجد"]):
        cat = "religion"
    elif any(k in domain_lc for k in ["متجر", "shop", "ecommerce", "بيع", "تجارة"]):
        cat = "ecommerce"
    elif any(k in domain_lc for k in ["عقار", "real-estate", "بيت", "فيلا"]):
        cat = "realestate"
    elif any(k in domain_lc for k in ["تقنية", "tech", "ai", "ذكاء"]):
        cat = "tech"

    return {"ok": True, "category": cat, "sources": sources.get(cat, [])}


async def sports_team_lookup(team_name: str) -> Dict[str, Any]:
    """Look up a sports team using TheSportsDB free API. Returns players,
    coach, stadium, recent results. Use for sports-club websites."""
    if not team_name.strip():
        return {"ok": False, "error": "team_name required"}
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(
                "https://www.thesportsdb.com/api/v1/json/3/searchteams.php",
                params={"t": team_name},
            )
        if r.status_code != 200:
            return {"ok": False, "error": f"HTTP {r.status_code}"}
        data = r.json() or {}
        teams = data.get("teams") or []
        if not teams:
            return {"ok": False, "error": "team not found"}
        t = teams[0]
        team_id = t.get("idTeam")
        # Fetch players
        players: List[Dict[str, str]] = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as c2:
                pr = await c2.get(
                    "https://www.thesportsdb.com/api/v1/json/3/lookup_all_players.php",
                    params={"id": team_id},
                )
            if pr.status_code == 200:
                pd = pr.json() or {}
                for p in (pd.get("player") or [])[:25]:
                    players.append({
                        "name": p.get("strPlayer", ""),
                        "position": p.get("strPosition", ""),
                        "nationality": p.get("strNationality", ""),
                        "thumb": p.get("strThumb", ""),
                        "number": p.get("strNumber", ""),
                    })
        except Exception:
            pass
        return {
            "ok": True,
            "team": {
                "name": t.get("strTeam"),
                "country": t.get("strCountry"),
                "league": t.get("strLeague"),
                "stadium": t.get("strStadium"),
                "founded": t.get("intFormedYear"),
                "description": (t.get("strDescriptionEN") or t.get("strDescriptionAR") or "")[:600],
                "logo": t.get("strLogo") or t.get("strBadge"),
                "banner": t.get("strBanner") or t.get("strFanart1"),
                "website": t.get("strWebsite"),
            },
            "players_count": len(players),
            "players": players,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:160]}


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
    {
        "type": "function",
        "function": {
            "name": "saudi_official_sources",
            "description": (
                "Lookup VERIFIED Saudi government / institutional sources for a "
                "given domain category. Use this whenever building any Saudi-context "
                "website (education, health, sports, religion, ecommerce, realestate, "
                "tech, government). Returns real URLs & names you should reference "
                "in 'about', 'partners', or 'official sources' sections."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": (
                            "Free-form domain hint in Arabic or English. "
                            "Categories: education, health, sports, religion, "
                            "ecommerce, realestate, tech, government."
                        ),
                    },
                },
                "required": ["domain"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sports_team_lookup",
            "description": (
                "Lookup a real sports team via TheSportsDB (free public API). "
                "Returns team info + up to 25 real players with positions, "
                "nationalities, photos, jersey numbers. Use for any sports/club "
                "website to populate the players section with REAL data — never "
                "invent player names."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "team_name": {
                        "type": "string",
                        "description": (
                            "Team name in English (works best). e.g. 'Al Hilal', "
                            "'Al Nassr', 'Real Madrid', 'Manchester United'."
                        ),
                    },
                },
                "required": ["team_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_website",
            "description": (
                "Generate a complete single-file HTML SPA from a brief. Use this "
                "the FIRST time the user asks for a website. The brief MUST be "
                "very detailed in Arabic: domain, audience, mood, must-have "
                "sections, content hints. Returns the full HTML string. "
                "After you call this, the website is shown live to the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "brief": {
                        "type": "string",
                        "description": "Detailed Arabic brief describing the site",
                    },
                    "style_direction": {
                        "type": "string",
                        "description": "Optional palette/layout/mood hint",
                    },
                },
                "required": ["brief"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_website",
            "description": (
                "Apply a surgical edit to the current website HTML. Use AFTER "
                "build_website when the user wants to change/add/remove specific "
                "sections. The agent system auto-injects current_html — you only "
                "provide the instructions in Arabic."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "instructions": {
                        "type": "string",
                        "description": "Specific Arabic instructions for the change",
                    },
                },
                "required": ["instructions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_audio",
            "description": (
                "Generate ambient music or sound effects (1-22 seconds) via "
                "ElevenLabs. Use for: background music for websites, intro jingles, "
                "ambient soundscapes, audio logos. Returns a public MP3 URL the "
                "user can embed in their site."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "English description e.g. 'calm ambient piano for a meditation site'",
                    },
                    "duration_seconds": {
                        "type": "number",
                        "description": "1-22 seconds",
                        "default": 8,
                    },
                },
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_theme",
            "description": (
                "Surgically rewrite ONLY the CSS theme (palette, fonts, mood) "
                "without touching HTML structure or images. FAST (~5-10s). Use this "
                "whenever the user wants color/typography/mood changes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "palette": {"type": "string", "description": "e.g. 'dark navy + gold accents'"},
                    "fonts": {"type": "string", "description": "e.g. 'modern sans-serif Arabic'"},
                    "mood": {"type": "string", "description": "e.g. 'minimalist', 'luxury', 'playful'"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_page",
            "description": (
                "Append a new page (section) to the SPA + add a nav link. "
                "Generates ONE focused section with content matching the brief. "
                "FAST (~10-15s). Use whenever the user wants to add a page."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "Arabic page label shown in nav"},
                    "slug": {"type": "string", "description": "URL slug (auto-derived if omitted)"},
                    "brief": {"type": "string", "description": "What goes on this page"},
                },
                "required": ["label"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_section",
            "description": (
                "Surgical edit of ONE section in the current site. Use for any "
                "targeted change like 'change the hero text', 'update the menu', "
                "'add a contact form to the contact page'. FASTER and more reliable "
                "than update_website. Always prefer this over update_website."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Section identifier hint: 'hero', 'menu', 'contact', 'pricing', 'home', 'about', 'features' etc.",
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Arabic instructions describing the change",
                    },
                },
                "required": ["target", "instructions"],
            },
        },
    },
]


# Map of tool name → callable (populated at module bottom after all defs)
TOOL_REGISTRY: Dict[str, Callable[..., Awaitable[Dict[str, Any]]]] = {}


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


# ════════════════════════════════════════════════════════════════════════
#  TOOL: Build Website (full SPA from a brief)
# ════════════════════════════════════════════════════════════════════════
WEBSITE_BUILDER_SYSTEM = """أنت مهندس واجهات أمامي عبقري. مهمتك: بناء موقع SPA كامل (HTML واحد) عربي RTL فخم بناء على وصف العميل.

🎯 المعايير الإلزامية:
1. **HTML واحد كامل**: يبدأ بـ `<!doctype html>` ينتهي بـ `</html>`. Inline CSS + JS داخل `<style>` و `<script>`.
2. **RTL + خط Tajawal/Cairo + Arabic copy حقيقي**: ممنوع Lorem Ipsum. كل النصوص عربية ذات معنى.
3. **SPA navigation**: كل القائمة تستخدم hash routing (`#/home`, `#/about`...). صفحات `<section data-page="home">` و JS بسيط يبدّلها.
4. **تصميم مختلف 100%**: ممنوع تكرار نفس الـpalette/layout عبر المواقع. اختر هوية بصرية فريدة (gradient/colors/typography/grid).
5. **Hero فخم + 4-8 أقسام محتوى متنوعة**: features, gallery, testimonials, pricing, FAQ, contact, إلخ.
6. **صور**: استخدم `<img src="@@IMG/auto@@" alt="<وصف غني بالعربي>">` — السيرفر يولّدها بـNano Banana تلقائياً. ممنوع روابط Unsplash.
7. **Animations**: إستخدم CSS transitions + transforms + scroll reveals.
8. **Responsive**: mobile-first مع breakpoints عند 768/1024.
9. **Accessibility**: aria-labels, focus states, semantic HTML.
10. **عمق إنتاجي حقيقي**: لا تكتفِ بالأساسيات — أضف microinteractions, hover states, badges, stats counters.

🔄 إذا أعطاك المستخدم HTML سابق وطلب تعديل، احتفظ بكل الأقسام ثم عدّل القسم/الجزء المطلوب فقط بدقة جراحية.

أرجع HTML فقط، بدون شرح أو markdown."""


async def build_website(brief: str, style_direction: str = "", current_html: str = "") -> Dict[str, Any]:
    """Generate a complete single-file HTML SPA from a brief.
    
    Args:
        brief: Arabic description of what the user wants
        style_direction: Optional palette/layout hint (e.g. "minimalist + neon green")
        current_html: If provided, this is treated as a refinement / next iteration
    """
    if not brief or len(brief.strip()) < 5:
        return {"ok": False, "error": "brief too short"}
    
    direct_key = os.environ.get("OPENAI_DIRECT_KEY", "").strip()
    if not direct_key:
        return {"ok": False, "error": "OPENAI_DIRECT_KEY missing"}
    
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=direct_key)
        
        sys_prompt = WEBSITE_BUILDER_SYSTEM
        if style_direction:
            sys_prompt += f"\n\n🎨 توجيه أسلوب من المستخدم: {style_direction}"
        
        user_prompt = f"المطلوب: {brief}"
        if current_html and len(current_html) > 200:
            user_prompt = (
                f"المطلوب (تعديل/تطوير): {brief}\n\n"
                f"الـHTML الحالي:\n{current_html[:60000]}\n\n"
                "أرجع الـHTML الكامل المُحدَّث."
            )
        
        resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.9,
            max_tokens=16000,
        )
        html = (resp.choices[0].message.content or "").strip()
        # Strip markdown fences if model added them
        html = re.sub(r"^```(?:html)?\s*", "", html)
        html = re.sub(r"\s*```\s*$", "", html)
        if "<html" not in html.lower():
            return {"ok": False, "error": "model did not return valid HTML"}
        
        # Post-process: replace @@IMG/auto@@ placeholders with AI-generated images
        try:
            from .image_gen import post_process_html_with_ai_images
            html = await post_process_html_with_ai_images(html, style_seed=style_direction or brief[:40])
        except Exception as e:
            logger.warning(f"[BUILD_WEBSITE] image post-process failed: {e}")
        
        return {
            "ok": True,
            "html": html,
            "size_kb": round(len(html) / 1024, 1),
            "summary": f"موقع كامل مولّد ({round(len(html)/1024,1)} KB)",
        }
    except Exception as e:
        logger.exception("[BUILD_WEBSITE] failed")
        return {"ok": False, "error": str(e)[:200]}


# ════════════════════════════════════════════════════════════════════════
#  TOOL: Update Website (surgical edit)
# ════════════════════════════════════════════════════════════════════════
async def update_website(instructions: str, current_html: str = "") -> Dict[str, Any]:
    """Apply a surgical edit to the current website HTML.
    
    Args:
        instructions: Arabic instructions for the change
        current_html: The existing site HTML (auto-injected by agent)
    """
    if not current_html or len(current_html) < 200:
        return {"ok": False, "error": "no current_html — call build_website first"}
    if not instructions:
        return {"ok": False, "error": "instructions required"}
    return await build_website(brief=instructions, current_html=current_html)


# ════════════════════════════════════════════════════════════════════════
#  TOOL: Generate Audio / Music (ElevenLabs Sound Effects)
# ════════════════════════════════════════════════════════════════════════
_AUDIO_DIR = Path("/app/backend/static/agent_audio")
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


async def generate_audio(description: str, duration_seconds: float = 8.0) -> Dict[str, Any]:
    """Generate ambient music or sound effects via ElevenLabs Sound Generation.
    
    Args:
        description: English/Arabic description (e.g. "calm ambient piano music for a meditation site")
        duration_seconds: 1-22 seconds
    """
    if not description.strip():
        return {"ok": False, "error": "description required"}
    duration_seconds = max(1.0, min(22.0, float(duration_seconds)))
    
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        return {"ok": False, "error": "ELEVENLABS_API_KEY missing"}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                "https://api.elevenlabs.io/v1/sound-generation",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": description,
                    "duration_seconds": duration_seconds,
                    "prompt_influence": 0.5,
                },
            )
        if r.status_code != 200:
            return {"ok": False, "error": f"ElevenLabs HTTP {r.status_code}: {r.text[:200]}"}
        
        # Save and return URL
        audio_id = hashlib.md5(f"{description}::{duration_seconds}::{uuid.uuid4()}".encode()).hexdigest()[:16]
        fname = f"{audio_id}.mp3"
        fpath = _AUDIO_DIR / fname
        fpath.write_bytes(r.content)
        
        # Backend returns relative path; frontend serves via same origin (ingress)
        public_url = f"/api/agent/audio/{fname}"
        
        return {
            "ok": True,
            "url": public_url,
            "duration_seconds": duration_seconds,
            "size_kb": round(len(r.content) / 1024, 1),
            "summary": f"تم توليد الصوت ({round(len(r.content)/1024,1)} KB)",
        }
    except Exception as e:
        logger.exception("[GENERATE_AUDIO] failed")
        return {"ok": False, "error": str(e)[:200]}


# ════════════════════════════════════════════════════════════════════════
#  SURGICAL TOOLS — fast, focused edits without full regeneration
# ════════════════════════════════════════════════════════════════════════
async def _gpt_rewrite(system: str, user: str, max_tokens: int = 4000) -> str:
    """Helper: one-shot GPT-4o call returning a string (for surgical edits)."""
    direct_key = os.environ.get("OPENAI_DIRECT_KEY", "").strip()
    if not direct_key:
        raise RuntimeError("OPENAI_DIRECT_KEY missing")
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=direct_key)
    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


async def set_theme(
    palette: str = "",
    fonts: str = "",
    mood: str = "",
    current_html: str = "",
) -> Dict[str, Any]:
    """Surgically rewrite ONLY the <style>:root variables and typography.
    Does NOT touch HTML structure or images. Fast (~5-10s)."""
    if not current_html or len(current_html) < 200:
        return {"ok": False, "error": "no current_html — call build_website first"}
    
    request_parts = []
    if palette:
        request_parts.append(f"palette: {palette}")
    if fonts:
        request_parts.append(f"fonts: {fonts}")
    if mood:
        request_parts.append(f"mood: {mood}")
    if not request_parts:
        return {"ok": False, "error": "provide at least one of: palette, fonts, mood"}
    request = "; ".join(request_parts)
    
    # Extract first <style>...</style> block
    style_match = re.search(r"(<style[^>]*>)([\s\S]*?)(</style>)", current_html, re.IGNORECASE)
    if not style_match:
        return {"ok": False, "error": "no <style> block found in current site"}
    open_tag, css_body, close_tag = style_match.group(1), style_match.group(2), style_match.group(3)
    
    sys_prompt = (
        "أنت خبير CSS. مهمتك: إعادة كتابة CSS مع تغيير الـtheme فقط (ألوان، خطوط، مزاج).\n"
        "احتفظ بكل selectors والـlayout كما هو، غيّر:\n"
        "- :root CSS variables (--primary, --bg, --text...)\n"
        "- font-family declarations\n"
        "- background gradients عامة\n"
        "أرجع CSS فقط (بدون <style> tags، بدون شرح). التعليقات بالعربي مسموحة."
    )
    user_prompt = (
        f"غيّر الـtheme حسب: {request}\n\n"
        f"الـCSS الحالي:\n{css_body[:14000]}\n\n"
        "أرجع الـCSS الكامل المحدّث."
    )
    try:
        new_css = await _gpt_rewrite(sys_prompt, user_prompt, max_tokens=8000)
        # Strip markdown fences if any
        new_css = re.sub(r"^```(?:css)?\s*", "", new_css)
        new_css = re.sub(r"\s*```\s*$", "", new_css)
        if len(new_css) < 200 or "{" not in new_css:
            return {"ok": False, "error": "model returned invalid CSS"}
        new_html = current_html.replace(
            open_tag + css_body + close_tag,
            open_tag + "\n" + new_css + "\n" + close_tag,
            1,
        )
        return {
            "ok": True,
            "html": new_html,
            "size_kb": round(len(new_html) / 1024, 1),
            "summary": f"تم تحديث الـtheme ({request})",
        }
    except Exception as e:
        logger.exception("[SET_THEME] failed")
        return {"ok": False, "error": str(e)[:200]}


async def add_page(
    label: str,
    slug: str = "",
    brief: str = "",
    current_html: str = "",
) -> Dict[str, Any]:
    """Add a new page (section) to the SPA. Generates a focused new section,
    appends it to the page list, and adds a nav link. Fast (~10-15s)."""
    if not current_html or len(current_html) < 200:
        return {"ok": False, "error": "no current_html — call build_website first"}
    if not label.strip():
        return {"ok": False, "error": "label required"}
    
    # Auto-derive slug if missing
    if not slug:
        slug = re.sub(r"[^a-z0-9-]", "-", label.lower())[:30] or f"page-{uuid.uuid4().hex[:6]}"
    slug = slug.strip("-")
    
    # Check if slug already exists
    if re.search(rf'data-page=["\']{re.escape(slug)}["\']', current_html):
        return {"ok": False, "error": f"page with slug '{slug}' already exists"}
    
    sys_prompt = (
        "أنت مهندس واجهات. مهمتك: إنشاء section واحد كامل لـSPA موجود.\n"
        "القواعد:\n"
        f"- Wrapper: <section data-page=\"{slug}\" class=\"page\">...</section>\n"
        "- محتوى عربي حقيقي (ممنوع Lorem). hero عنوان + 4-8 cards/blocks + CTAs.\n"
        "- استخدم نفس الـCSS variables الموجودة في الموقع (--primary, --bg, إلخ) — لا تكتب inline styles جديدة.\n"
        "- صور كـ <img src=\"@@IMG/auto@@\" alt=\"<وصف عربي>\"> للمعالج التلقائي.\n"
        "- روابط داخلية تستخدم #/slug.\n"
        "أرجع HTML الـsection فقط (بدون <html><body><style> أو شرح)."
    )
    user_prompt = (
        f"اسم الصفحة: {label}\n"
        f"slug: {slug}\n"
        f"وصف المحتوى: {brief or label}\n\n"
        "أرجع section واحد كامل."
    )
    try:
        new_section = await _gpt_rewrite(sys_prompt, user_prompt, max_tokens=4000)
        new_section = re.sub(r"^```(?:html)?\s*", "", new_section)
        new_section = re.sub(r"\s*```\s*$", "", new_section)
        if "<section" not in new_section.lower():
            return {"ok": False, "error": "model did not return a <section>"}
        
        # Post-process the new section's images only
        try:
            from .image_gen import post_process_html_with_ai_images
            new_section = await post_process_html_with_ai_images(new_section, style_seed=label)
        except Exception as e:
            logger.warning(f"[ADD_PAGE] image post-process failed: {e}")
        
        # Inject section: append before last </main> or </body>
        new_html = current_html
        if "</main>" in new_html:
            new_html = new_html.replace("</main>", f"\n{new_section}\n</main>", 1)
        else:
            new_html = new_html.replace("</body>", f"\n{new_section}\n</body>", 1)
        
        # Inject nav link: find first <nav>...</nav> and add a link
        nav_match = re.search(r"(<nav[^>]*>)([\s\S]*?)(</nav>)", new_html, re.IGNORECASE)
        if nav_match:
            nav_open, nav_body, nav_close = nav_match.group(1), nav_match.group(2), nav_match.group(3)
            link = f'<a href="#/{slug}" data-page-link="{slug}">{label}</a>'
            new_nav_body = nav_body.rstrip() + "\n" + link + "\n"
            new_html = new_html.replace(
                nav_open + nav_body + nav_close,
                nav_open + new_nav_body + nav_close,
                1,
            )
        
        return {
            "ok": True,
            "html": new_html,
            "size_kb": round(len(new_html) / 1024, 1),
            "slug": slug,
            "summary": f"تم إضافة صفحة: {label} (#/{slug})",
        }
    except Exception as e:
        logger.exception("[ADD_PAGE] failed")
        return {"ok": False, "error": str(e)[:200]}


async def edit_section(
    target: str,
    instructions: str,
    current_html: str = "",
) -> Dict[str, Any]:
    """Surgical edit of ONE section in the current site.
    
    Args:
        target: Section identifier hint (e.g. 'hero', 'menu', 'contact', 'home', 'pricing').
                Matches data-page, id, class, or nearest h1/h2 text.
        instructions: Arabic instructions for what to change in that section.
    """
    if not current_html or len(current_html) < 200:
        return {"ok": False, "error": "no current_html — call build_website first"}
    if not target.strip() or not instructions.strip():
        return {"ok": False, "error": "target and instructions required"}
    
    # Find best matching section
    target_lc = target.strip().lower()
    section_pattern = re.compile(r"<section\b[^>]*>[\s\S]*?</section>", re.IGNORECASE)
    sections = list(section_pattern.finditer(current_html))
    if not sections:
        return {"ok": False, "error": "no <section> tags found"}
    
    best_idx = -1
    best_score = 0
    for i, m in enumerate(sections):
        block = m.group(0)
        score = 0
        # data-page attribute match
        dp = re.search(r'data-page="([^"]+)"', block)
        if dp and target_lc in dp.group(1).lower():
            score += 10
        # id attribute match
        idm = re.search(r'\bid="([^"]+)"', block)
        if idm and target_lc in idm.group(1).lower():
            score += 8
        # class attribute match
        cm = re.search(r'\bclass="([^"]+)"', block)
        if cm and target_lc in cm.group(1).lower():
            score += 5
        # heading text match
        hm = re.search(r"<h[1-3][^>]*>([\s\S]{1,200}?)</h[1-3]>", block)
        if hm and target_lc in hm.group(1).lower():
            score += 6
        # general body match
        if target_lc in block[:2000].lower():
            score += 1
        if score > best_score:
            best_score = score
            best_idx = i
    
    if best_idx < 0 or best_score == 0:
        return {"ok": False, "error": f"no section matching '{target}' — try a different keyword"}
    
    target_section = sections[best_idx].group(0)
    
    sys_prompt = (
        "أنت محرّر HTML جراحي. مهمتك: تعديل section واحد فقط حسب التعليمات.\n"
        "القواعد:\n"
        "- احتفظ بـwrapper الـ<section> كما هو (id, class, data-page).\n"
        "- استخدم نفس الـCSS classes الموجودة (لا تخترع جديدة بدون داعي).\n"
        "- محتوى عربي حقيقي.\n"
        "- صور: <img src=\"@@IMG/auto@@\" alt=\"<وصف>\"> أو احتفظ بالـURLs الموجودة كما هي.\n"
        "أرجع الـsection الكامل المحدّث فقط (بدون شرح أو ```)."
    )
    user_prompt = (
        f"التعليمات: {instructions}\n\n"
        f"الـsection الحالي:\n{target_section[:14000]}\n\n"
        "أرجع الـsection المحدّث."
    )
    try:
        new_section = await _gpt_rewrite(sys_prompt, user_prompt, max_tokens=6000)
        new_section = re.sub(r"^```(?:html)?\s*", "", new_section)
        new_section = re.sub(r"\s*```\s*$", "", new_section)
        if "<section" not in new_section.lower():
            return {"ok": False, "error": "model did not return a <section>"}
        
        # Process only NEW @@IMG/auto@@ placeholders in the new section
        if "@@IMG" in new_section:
            try:
                from .image_gen import post_process_html_with_ai_images
                new_section = await post_process_html_with_ai_images(new_section, style_seed=target)
            except Exception as e:
                logger.warning(f"[EDIT_SECTION] image post-process failed: {e}")
        
        new_html = current_html.replace(target_section, new_section, 1)
        
        # Identify section label for summary
        dp = re.search(r'data-page="([^"]+)"', target_section)
        label = dp.group(1) if dp else target
        return {
            "ok": True,
            "html": new_html,
            "size_kb": round(len(new_html) / 1024, 1),
            "edited": label,
            "summary": f"تم تعديل قسم: {label}",
        }
    except Exception as e:
        logger.exception("[EDIT_SECTION] failed")
        return {"ok": False, "error": str(e)[:200]}


# Populate registry after all functions are defined
TOOL_REGISTRY.update({
    "quran_reciter_lookup": quran_reciter_lookup,
    "quran_verse_fetch": quran_verse_fetch,
    "web_search": web_search,
    "web_fetch": web_fetch,
    "generate_image_url": generate_image_url,
    "saudi_official_sources": saudi_official_sources,
    "sports_team_lookup": sports_team_lookup,
    "build_website": build_website,
    "update_website": update_website,
    "generate_audio": generate_audio,
    "set_theme": set_theme,
    "add_page": add_page,
    "edit_section": edit_section,
})
