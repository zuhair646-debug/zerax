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
async def web_fetch(url: str, max_chars: int = 30000) -> Dict[str, Any]:
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
                    "max_chars": {"type": "integer", "default": 30000},
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
    {
        "type": "function",
        "function": {
            "name": "build_creative_quran_site",
            "description": (
                "🎮 BULLETPROOF: build a creative Quran site (gaming/achievements/"
                "dashboard/multi-page) with REAL Quran content GUARANTEED embedded. "
                "Solves: edit_section refusing long HTML, build_website ignoring blocks. "
                "Uses deterministic post-processing: AI designs the wrapper, system "
                "auto-injects real ayahs + reciters + audio wiring. Use this for ANY "
                "creative Quran site — full design freedom, guaranteed working."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "brief": {"type": "string", "description": "Detailed Arabic brief"},
                    "surah": {"type": "integer", "description": "Surah 1-114 (default 1)", "default": 1},
                    "style_direction": {"type": "string", "description": "Optional palette/mood hint"},
                },
                "required": ["brief"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inject_quran_blocks",
            "description": (
                "🩹 FIX broken Quran section in an existing site. Use when "
                "build_website built a site but the Quran section is empty/broken — "
                "this tool injects REAL ayahs + reciters + audio into the matching "
                "section (or appends a new one if none found). Auto-injects default "
                "CSS if none exists. Guaranteed to work."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "surah": {"type": "integer", "default": 1},
                    "target_selector": {"type": "string", "description": "Optional hint for which section to fix"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_quran_blocks",
            "description": (
                "🧩 Fetch real Quran content as ready-to-embed HTML blocks + audio JS. "
                "USE THIS when you need REAL Quran (real text + 14 reciters + working "
                "audio) inside a CUSTOM creative website (gaming theme, achievements, "
                "parent dashboard, multi-page app, etc.). Workflow: call this FIRST to "
                "get the blocks, then call build_website with a brief that includes "
                "instructions to embed those exact blocks. This unlocks full creative "
                "freedom for Quran sites — no more limited template."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "surah": {"type": "integer", "description": "Surah number 1-114", "default": 1},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_quran_mushaf_reader",
            "description": (
                "🕌 USE THIS for ANY Quran/Mushaf/تلاوة/تحفيظ/قرآن request. "
                "Builds a COMPLETE single-page integrated Quran reader site that combines: "
                "REAL Quran text (from Madinah Mushaf via alquran.cloud), 14 verified "
                "reciter selector with avatars, click-any-verse-to-play with the chosen "
                "reciter, repeat/continuous controls, surah selector. NO random AI images — "
                "uses Islamic geometric ornaments only. This is the CORRECT way to handle "
                "Quran sites — DO NOT call build_website for Quran. The text is fetched "
                "from official sources (no LLM rewriting that corrupts diacritics)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "surah": {"type": "integer", "description": "Surah number 1-114 (default 1=الفاتحة)", "default": 1},
                    "style": {"type": "string", "enum": ["classic", "modern", "minimal", "royal"], "default": "classic"},
                    "site_title": {"type": "string", "description": "Site title in Arabic", "default": "مصحف زيتكس"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_intent",
            "description": (
                "🧠 PLANNER agent — analyze the user's brief and return a structured plan: "
                "domain, audience, tone, sections, data_sources needed, integrations, mood. "
                "ALWAYS call this FIRST when the user asks to build a new site (it's the "
                "Planner phase of multi-agent workflow). Skip only for simple edits."
            ),
            "parameters": {
                "type": "object",
                "properties": {"brief": {"type": "string"}},
                "required": ["brief"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pick_design",
            "description": (
                "🎨 DESIGNER agent — pick a unique visual direction (palette + typography + "
                "layout style + mood). Call AFTER analyze_intent and AFTER any research, "
                "BEFORE build_website. Ensures every site has a fresh distinct look."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "brief": {"type": "string"},
                    "research_summary": {"type": "string", "description": "Optional summary of research findings"},
                },
                "required": ["brief"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "qa_html",
            "description": (
                "🧪 QA agent — scan the current site for issues (missing pages, empty "
                "sections, broken images, leftover placeholders, Lorem Ipsum, RTL issues). "
                "Returns a quality score 0-100 and a list of issues with severity. "
                "ALWAYS call this AFTER build_website / build_quran_mushaf_reader to verify."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "geo_lookup",
            "description": (
                "🌍 Geo-lookup via free ip-api.com (no key needed). Returns country, city, "
                "timezone, currency. Use for sites that need geo-localized content."
            ),
            "parameters": {
                "type": "object",
                "properties": {"ip": {"type": "string", "description": "IP address or empty for server's own"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "publish_site",
            "description": (
                "🚀 Publish the current_html as a public site at /p/{slug}. The user "
                "gets a shareable URL they can send to anyone. Use when the user says "
                "'publish', 'انشره', 'انشره للناس', 'أبي رابط أشاركه'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "URL slug, auto-generated if empty"},
                    "title": {"type": "string", "description": "Site title for the public page"},
                },
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
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not direct_key and not emergent_key:
        return {"ok": False, "error": "no LLM key configured"}
    
    try:
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
        
        html = await _gpt_rewrite(sys_prompt, user_prompt, max_tokens=16000, temperature=0.9)
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
async def _gpt_rewrite(system: str, user: str, max_tokens: int = 4000, json_mode: bool = False, temperature: float = 0.7) -> str:
    """Helper: one-shot LLM text generation. Tries OpenAI first, falls back to
    Claude (via Emergent LLM Key) on quota/auth errors."""
    direct_key = os.environ.get("OPENAI_DIRECT_KEY", "").strip()
    last_err: Optional[Exception] = None
    if direct_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=direct_key)
            kwargs: Dict[str, Any] = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = await client.chat.completions.create(**kwargs)
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "billing" in err_str or "insufficient" in err_str or "401" in err_str:
                logger.warning(f"[LLM] OpenAI failed ({err_str[:80]}), falling back to Claude")
                last_err = e
            else:
                raise
    # Claude fallback via emergentintegrations
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        raise RuntimeError(f"OpenAI failed and no EMERGENT_LLM_KEY: {last_err}")
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"rewrite-{uuid.uuid4().hex[:8]}",
            system_message=system + ("\n\nأرجع JSON صالح فقط، لا شرح." if json_mode else ""),
        )
        chat.with_model("anthropic", "claude-sonnet-4-5")
        result = await chat.send_message(UserMessage(text=user))
        out = str(result or "").strip()
        if json_mode:
            # Strip markdown fences if Claude added them
            out = re.sub(r"^```(?:json)?\s*", "", out)
            out = re.sub(r"\s*```\s*$", "", out)
        return out
    except Exception as e:
        raise RuntimeError(f"All LLMs failed: openai={last_err} · claude={e}")


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
        new_section = await _gpt_rewrite(sys_prompt, user_prompt, max_tokens=8000)
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
        new_section = await _gpt_rewrite(sys_prompt, user_prompt, max_tokens=10000)
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


# ════════════════════════════════════════════════════════════════════════
#  ORCHESTRATION HELPERS — Planner, Designer, QA (multi-agent style)
# ════════════════════════════════════════════════════════════════════════
async def analyze_intent(brief: str) -> Dict[str, Any]:
    """🧠 PLANNER agent — analyzes the user's brief and returns a structured plan."""
    if not brief or len(brief.strip()) < 5:
        return {"ok": False, "error": "brief too short"}
    
    sys_prompt = (
        "أنت Planner Agent. مهمتك: تحليل طلب العميل وإرجاع خطة منظّمة JSON.\n"
        "أرجع JSON فقط بهذا الشكل بالضبط:\n"
        "{\n"
        '  "domain": "<quran|sports|restaurant|ecommerce|education|medical|realestate|fintech|portfolio|generic>",\n'
        '  "audience": "<وصف موجز للجمهور المستهدف>",\n'
        '  "tone": "<formal|casual|friendly|luxury|playful|spiritual>",\n'
        '  "sections": [<قائمة الأقسام المطلوبة>],\n'
        '  "data_sources": [<أي بيانات حقيقية يحتاجها: quran_verse|reciters|sports_team|saudi_sources|web_search|geo_data|none>],\n'
        '  "integrations": [<api| stripe| whatsapp| audio| video| none>],\n'
        '  "mood": "<وصف بصري موجز للنمط>"\n'
        "}\n"
        "لا شرح، لا ```، JSON فقط."
    )
    try:
        raw = await _gpt_rewrite(sys_prompt, f"الطلب: {brief}", max_tokens=1500, json_mode=True, temperature=0.5)
        plan = json.loads(raw)
        plan["ok"] = True
        plan["agent"] = "planner"
        plan["summary"] = f"المجال: {plan.get('domain','?')} · {len(plan.get('sections',[]))} قسم"
        return plan
    except Exception as e:
        logger.exception("[ANALYZE_INTENT] failed")
        return {"ok": False, "error": str(e)[:200]}


async def pick_design(brief: str, research_summary: str = "") -> Dict[str, Any]:
    """🎨 DESIGNER agent — picks visual direction (palette + typography + layout)."""
    sys_prompt = (
        "أنت Designer Agent. مهمتك: اختيار اتجاه بصري متماسك للموقع.\n"
        "أرجع JSON فقط:\n"
        "{\n"
        '  "palette_name": "<اسم palette مبدع>",\n'
        '  "primary_color": "#hex",\n'
        '  "secondary_color": "#hex",\n'
        '  "accent_color": "#hex",\n'
        '  "bg_color": "#hex (داكن أو فاتح)",\n'
        '  "text_color": "#hex",\n'
        '  "heading_font": "<google font name e.g. Aref Ruqaa, Tajawal Black>",\n'
        '  "body_font": "<google font name e.g. Tajawal>",\n'
        '  "layout_style": "<asymmetric|grid|magazine|minimal|brutalist|luxe>",\n'
        '  "mood_keywords": [<3-5 كلمات وصفية>]\n'
        "}\n"
        "اختر مزيجاً جريئاً مختلفاً عن المعتاد. لا تكرّر الذهبي/الأسود في كل موقع."
    )
    try:
        user_msg = f"الطلب: {brief}"
        if research_summary:
            user_msg += f"\n\nنتائج البحث: {research_summary[:1500]}"
        raw = await _gpt_rewrite(sys_prompt, user_msg, max_tokens=800, json_mode=True, temperature=0.95)
        design = json.loads(raw)
        design["ok"] = True
        design["agent"] = "designer"
        design["summary"] = f"{design.get('palette_name','?')} · {design.get('layout_style','?')}"
        return design
    except Exception as e:
        logger.exception("[PICK_DESIGN] failed")
        return {"ok": False, "error": str(e)[:200]}


async def qa_html(current_html: str = "") -> Dict[str, Any]:
    """🧪 QA agent — scans the current site and reports issues + auto-fix suggestions.
    
    Checks:
        - All nav links have matching <section data-page="..."> targets
        - No empty sections (sections with <p>... or just whitespace)
        - All <img> have non-empty src
        - No broken anchor refs
    """
    if not current_html or len(current_html) < 200:
        return {"ok": False, "error": "no current_html"}
    
    issues: List[Dict[str, str]] = []
    
    # 1. Nav links → page targets
    nav_links = re.findall(r'<a[^>]+href="#/([^"]+)"', current_html)
    page_targets = set(re.findall(r'data-page="([^"]+)"', current_html))
    missing_pages = [link for link in nav_links if link not in page_targets and link != "home"]
    for mp in missing_pages:
        issues.append({"severity": "high", "type": "missing_page", "detail": f"رابط #/{mp} في القائمة لكن ما فيه <section data-page=\"{mp}\">"})
    
    # 2. Empty sections
    empty_sections = re.findall(r'<section[^>]*data-page="([^"]+)"[^>]*>\s*</section>', current_html)
    for es in empty_sections:
        issues.append({"severity": "medium", "type": "empty_section", "detail": f"قسم data-page=\"{es}\" فارغ"})
    
    # 3. Broken images
    broken_imgs = re.findall(r'<img[^>]+src=""', current_html)
    if broken_imgs:
        issues.append({"severity": "medium", "type": "broken_image", "detail": f"{len(broken_imgs)} صور بدون src"})
    
    # 4. @@IMG/auto@@ leftovers (post-process didn't run)
    leftover = current_html.count("@@IMG/")
    if leftover > 0:
        issues.append({"severity": "high", "type": "image_placeholder_leftover", "detail": f"{leftover} placeholder صور لم تُعالج"})
    
    # 5. Lorem Ipsum check
    if "lorem ipsum" in current_html.lower() or "Lorem ipsum" in current_html:
        issues.append({"severity": "high", "type": "lorem_ipsum", "detail": "نص Lorem Ipsum موجود — يجب استبداله"})
    
    # 6. RTL check
    if 'dir="rtl"' not in current_html.lower():
        issues.append({"severity": "low", "type": "no_rtl", "detail": "ما فيه dir=\"rtl\" في <html>"})
    
    score = max(0, 100 - sum(20 if i["severity"] == "high" else (10 if i["severity"] == "medium" else 5) for i in issues))
    return {
        "ok": True,
        "agent": "qa",
        "score": score,
        "issues_count": len(issues),
        "issues": issues,
        "summary": f"الجودة: {score}/100 · {len(issues)} مشكلة",
    }


# ════════════════════════════════════════════════════════════════════════
#  GEO TOOL (free, no API key needed)
# ════════════════════════════════════════════════════════════════════════
async def geo_lookup(ip: str = "") -> Dict[str, Any]:
    """🌍 Lookup geographic info via free ip-api.com (no key needed).
    
    If ip is empty, looks up the requesting server's IP (fallback).
    Use for content localization (currency, language hints, regional services).
    """
    target = ip.strip() if ip else ""
    url = f"http://ip-api.com/json/{target}" if target else "http://ip-api.com/json"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url, params={"fields": "status,country,countryCode,region,regionName,city,timezone,currency,query"})
        if r.status_code != 200:
            return {"ok": False, "error": f"HTTP {r.status_code}"}
        d = r.json() or {}
        if d.get("status") != "success":
            return {"ok": False, "error": d.get("message", "lookup failed")}
        return {
            "ok": True,
            "country": d.get("country"),
            "country_code": d.get("countryCode"),
            "region": d.get("regionName"),
            "city": d.get("city"),
            "timezone": d.get("timezone"),
            "currency": d.get("currency"),
            "ip": d.get("query"),
            "summary": f"{d.get('city','?')}, {d.get('country','?')} ({d.get('countryCode','?')})",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


# ════════════════════════════════════════════════════════════════════════
#  PUBLISH TOOL — saves current_html to a public-accessible site
# ════════════════════════════════════════════════════════════════════════
async def publish_site(slug: str = "", title: str = "موقع زيتكس", current_html: str = "") -> Dict[str, Any]:
    """🚀 Publish current_html as a public site at /p/{slug}.
    
    The agent system handles persistence — this tool just returns a request
    payload that the agent will pass to the DB writer in __init__.py.
    Requires current_html (auto-injected by agent) to prevent publish-before-build.
    """
    if not current_html or len(current_html) < 200:
        return {
            "ok": False,
            "error": "ما فيه موقع للنشر — استدعِ build_website أو build_quran_mushaf_reader أولاً، ثم استدعِ publish_site.",
        }
    if not slug:
        slug = uuid.uuid4().hex[:10]
    slug = re.sub(r"[^a-z0-9-]", "-", slug.lower())[:40].strip("-")
    if not slug:
        slug = uuid.uuid4().hex[:10]
    return {
        "ok": True,
        "agent": "deployer",
        "_publish_request": True,  # marker for agent loop to handle DB write
        "slug": slug,
        "title": title,
        "url_path": f"/api/p/{slug}",
        "summary": f"تم تجهيز رابط النشر: /api/p/{slug}",
    }


# ════════════════════════════════════════════════════════════════════════
#  TOOL: Build Quran Site (GENERATIVE — never repeats)
# ════════════════════════════════════════════════════════════════════════
import random as _rand

QURAN_LAYOUT_SEEDS = [
    "vertical scroll mushaf with floating reciter dock at bottom",
    "horizontal pages flipping like a real mushaf, swipe between pages",
    "immersive single-ayah focus mode — one verse fills the screen, swipe to next",
    "split view: left=reciters grid with stats, right=verses with translation hover",
    "magazine layout: hero verse + sidebar of reciters as profile cards + bottom waveform player",
    "gallery of reciter portraits, click one and verses appear in a luxe modal with audio",
    "minimal monochrome reading mode with hidden controls, hover to reveal",
    "calligraphic centerpiece: each ayah is a hand-drawn piece on parchment",
    "ottoman-inspired ornate frames around each ayah, gold filigree, deep emerald bg",
    "modernist brutalist: huge typography, black/white, single accent color, no decorations",
    "night sky theme: deep navy with stars, ayahs glow softly when active",
    "dawn theme: warm gradient (peach → gold), serene typography, slow fade animations",
]

QURAN_PALETTE_SEEDS = [
    "deep emerald green + antique gold",
    "midnight navy + warm copper",
    "ivory parchment + chocolate brown + crimson",
    "obsidian black + electric teal accent",
    "burgundy maroon + soft cream",
    "sage green + warm terracotta",
    "royal purple + champagne gold",
    "charcoal + dusty rose pink",
    "pure white + jet black + single saffron accent",
    "twilight blue + silver moonlight",
    "desert sand + indigo + burnt orange",
    "matte black + rose-gold + bone white",
]


async def build_quran_mushaf_reader(
    surah: int = 1,
    style: str = "",  # IGNORED now — kept for backward compat
    site_title: str = "",
) -> Dict[str, Any]:
    """🕌 GENERATIVE Quran site builder with server-side pre-fetched ayahs and audit retry.
    
    Pre-fetches the surah text from alquran.cloud server-side, embeds it inline
    so ayahs are visible IMMEDIATELY (not on async load). Then runs a strict
    static audit + retries up to 2x if essential elements are missing.
    """
    try:
        surah = int(surah)
    except (TypeError, ValueError):
        return {"ok": False, "error": "surah must be an integer 1-114"}
    if not (1 <= surah <= 114):
        return {"ok": False, "error": "surah must be 1..114"}
    
    # PRE-FETCH the actual ayahs server-side — never trust LLM to write them
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(f"https://api.alquran.cloud/v1/surah/{surah}/quran-uthmani")
        data = r.json() if r.status_code == 200 else {}
        ayahs_data = (data.get("data") or {}).get("ayahs") or []
        surah_meta = (data.get("data") or {})
        if not ayahs_data:
            return {"ok": False, "error": "failed to fetch surah from alquran.cloud"}
    except Exception as e:
        return {"ok": False, "error": f"alquran.cloud unreachable: {e}"}
    
    # Build the inline ayah HTML the LLM MUST embed verbatim
    ayahs_inline = []
    for a in ayahs_data:
        n = a.get("numberInSurah")
        text = a.get("text", "")
        ayahs_inline.append({"n": n, "text": text})
    
    surah_name_ar = _get_surah_name_ar(surah)
    surah_name_en = (surah_meta.get("englishName") or "").strip()
    revelation_type = (surah_meta.get("revelationType") or "Meccan")
    
    # Random creative seeds for diversity
    layout_seed = _rand.choice(QURAN_LAYOUT_SEEDS)
    palette_seed = _rand.choice(QURAN_PALETTE_SEEDS)
    motif_seed = _rand.choice([
        "Islamic geometric tessellation patterns (SVG)",
        "Ottoman tughra-inspired calligraphic flourishes",
        "Andalusian arabesque borders",
        "Mamluk star-and-cross interlace",
        "Persian floral arabesque",
        "Modernist linework only — no traditional motifs",
        "Pure typography focus — no decoration at all",
        "Sacred geometry: hexagons, octagrams, golden-ratio spirals",
    ])
    site_title = site_title or _rand.choice([
        "مصحف زيتكس", "مصحفي", "تلاوة", "نور المصحف", "آيات", "مرتل",
        "مصحف القراء", "صدى التلاوة", "ترتيل", "مصحف الإمام",
    ])
    
    # Build the verbatim ayah HTML block the LLM MUST embed (we won't trust LLM with text)
    ayahs_html_block = "\n".join(
        f'  <div class="ayah-row" data-ayah="{a["n"]}" role="button" tabindex="0">'
        f'<span class="ayah-text">{a["text"]}</span>'
        f'<span class="ayah-num" data-num="{a["n"]}">{a["n"]}</span>'
        f'</div>'
        for a in ayahs_inline
    )
    
    # Build inline reciter strip block — LLM must embed too
    RECITERS_LIST = [
        {"id":"alafasy","name":"مشاري العفاسي"},{"id":"sudais","name":"عبد الرحمن السديس"},
        {"id":"shuraim","name":"سعود الشريم"},{"id":"husary","name":"محمود الحصري"},
        {"id":"minshawi","name":"محمد المنشاوي"},{"id":"abdulbasit","name":"عبد الباسط"},
        {"id":"ghamdi","name":"سعد الغامدي"},{"id":"ajmi","name":"أحمد العجمي"},
        {"id":"dossary","name":"ياسر الدوسري"},{"id":"shatri","name":"أبو بكر الشاطري"},
        {"id":"juhany","name":"عبد الله الجهني"},{"id":"hthfi","name":"علي الحذيفي"},
        {"id":"ayyub","name":"محمد أيوب"},{"id":"maher","name":"ماهر المعيقلي"},
    ]
    reciters_html_block = "\n".join(
        f'  <button class="reciter-card" data-reciter="{r["id"]}" type="button">'
        f'<span class="reciter-avatar">{r["name"][0]}</span>'
        f'<span class="reciter-name">{r["name"]}</span>'
        f'</button>'
        for r in RECITERS_LIST
    )
    
    sys_prompt = f"""أنت معماري واجهات إسلامي عبقري. مهمتك: بناء صفحة HTML واحدة كاملة لقارئ قرآن SPA.

🔒 قواعد البيانات (إلزامية صارمة):
- يجب تضمين السكريبت: `<script src="/api/agent/primitives/quran.js"></script>` قبل أي JS تكتبه.
- روابط الصوت فقط عبر `ZitexQuran.audioUrl(reciterId, surahN, ayahN)` (تستخدم everyayah.com).
- ⚠️ سأعطيك كتلتين HTML جاهزتين (الآيات + القراء). يجب أن تنسخهما **حرفياً** داخل containers في موقعك. ممنوع تعديل النصوص أو الأسماء.

🎨 الإلزام الإبداعي (اختلف 100% عن أي تصميم سابق):
- اتجاه التصميم: {layout_seed}
- لوحة الألوان: {palette_seed}
- نمط الزخرفة: {motif_seed}
- ممنوع تكرار الأسود/الذهبي التقليدي إلا لو palette_seed قال كذا.

📋 المتطلبات الوظيفية الإلزامية:
1. RTL، lang="ar"، Tajawal/Aref Ruqaa/Amiri Quran من Google Fonts.
2. ⚠️ كتلة الـ{len(ayahs_inline)} آية (ستُعطى لك) منسوخة كما هي داخل container.
3. ⚠️ كتلة الـ14 قارئ (ستُعطى لك) منسوخة كما هي داخل container.
4. **تنسيق ذكي**: لما المستخدم يفتح الصفحة، يشوف الآيات والقراء فوراً، **بدون** انتظار JS async.
5. activeReciter (state) — أول قارئ افتراضياً (alafasy). الضغط على .reciter-card يبدّله.
6. الضغط على .ayah-row → 
   ```
   const audio = new Audio(window.ZitexQuran.audioUrl(activeReciter, {surah}, parseInt(this.dataset.ayah)));
   audio.play();
   ```
7. الآية اللي تُشغّل تأخذ class="playing" (glow/scale).
8. controls: تكرار الآية / تشغيل متصل / السابقة / التالية.
9. selectbox/menu لاختيار سورة 1-114 → يفتح `?s={{n}}` (نحن نعيد البناء).
10. responsive، SVG decorations فقط.

📦 المخرجات:
- ملف HTML واحد كامل من `<!doctype html>` إلى `</html>`.
- inline CSS و JS فقط، ممنوع شرح، ممنوع markdown fences.

ابدع — لكن **تذكر**: بدون آيات ظاهرة + بدون 14 قارئ ظاهرين + بدون click listener = الموقع غير مكتمل ومرفوض."""

    user_prompt = f"""العنوان: {site_title}
السورة: {surah} ({surah_name_ar} / {surah_name_en}) — {revelation_type} — {len(ayahs_inline)} آية

🔒 الكتلة 1 — الآيات (انسخها كما هي داخل container):

```html
{ayahs_html_block}
```

🔒 الكتلة 2 — القراء (انسخها كما هي داخل container منفصل):

```html
{reciters_html_block}
```

ابنِ الموقع الكامل الآن. الكتلتان أعلاه يجب أن تظهرا في الـHTML النهائي حرفياً."""
    
    # Build with audit-retry up to 3 attempts
    last_html = ""
    last_audit: Dict[str, Any] = {}
    for attempt in range(3):
        try:
            html = await _gpt_rewrite(sys_prompt, user_prompt, max_tokens=14000, temperature=1.0)
            html = re.sub(r"^```(?:html)?\s*", "", html)
            html = re.sub(r"\s*```\s*$", "", html)
            if "<html" not in html.lower():
                continue
            # Ensure primitives script is included
            if "/api/agent/primitives/quran.js" not in html:
                html = html.replace(
                    "</head>",
                    '<script src="/api/agent/primitives/quran.js"></script>\n</head>',
                    1,
                )
            audit = _audit_quran_html(html, expected_ayahs=len(ayahs_inline))
            last_html = html
            last_audit = audit
            if audit["ok"]:
                return {
                    "ok": True,
                    "html": html,
                    "size_kb": round(len(html) / 1024, 1),
                    "surah": surah,
                    "layout": layout_seed,
                    "palette": palette_seed,
                    "audit": audit,
                    "attempts": attempt + 1,
                    "summary": f"✅ قارئ قرآن مكتمل ({surah_name_ar} · {audit['ayahs_found']}/{len(ayahs_inline)} آية · {audit['reciters_found']}/14 قارئ)",
                }
            # Audit failed — append issues to the prompt and retry
            issues_text = "\n".join(f"- {i}" for i in audit["missing"])
            user_prompt = (
                f"المحاولة السابقة فشلت في الـaudit:\n{issues_text}\n\n"
                "أعد البناء — هذه المرة احرص أن:\n"
                "1. الآيات الـ" + str(len(ayahs_inline)) + " كلها موجودة بصرياً (class='ayah').\n"
                "2. الـ14 قارئ كلهم في عنصر يحمل صفة data-reciter أو class تحتوي على reciter.\n"
                "3. <script src='/api/agent/primitives/quran.js'> موجود.\n"
                "4. event listener على .ayah للضغط.\n\n"
                f"السورة: {surah_name_ar}\n\nكتلة الآيات (انسخها):\n```html\n{ayahs_html_block}\n```"
            )
        except Exception as e:
            logger.exception("[BUILD_QURAN] attempt %d failed", attempt + 1)
            last_audit = {"ok": False, "error": str(e)[:200]}
    
    # All retries failed — return last attempt with audit details
    if last_html:
        return {
            "ok": True,  # we have a result, just imperfect
            "html": last_html,
            "size_kb": round(len(last_html) / 1024, 1),
            "surah": surah,
            "audit": last_audit,
            "attempts": 3,
            "warning": "audit_imperfect",
            "summary": f"⚠️ بُني بعد 3 محاولات، الـaudit ناقص: {last_audit.get('missing', [])}",
        }
    return {"ok": False, "error": last_audit.get("error", "all retries failed")}


def _audit_quran_html(html: str, expected_ayahs: int) -> Dict[str, Any]:
    """Static audit of generated Quran HTML. Verifies presence of essential
    UI elements without needing a real browser."""
    missing: List[str] = []
    
    # 1. Ayah rows rendered inline (count `data-ayah=` attributes — exact)
    ayah_data_matches = re.findall(r'data-ayah="(\d+)"', html)
    ayahs_found = len(set(ayah_data_matches))
    if ayahs_found < expected_ayahs:
        missing.append(f"ayahs: {ayahs_found}/{expected_ayahs} (need all {expected_ayahs} as <... data-ayah='N'>)")
    
    # 2. Reciter cards (count `data-reciter=` attributes)
    reciter_data_matches = re.findall(r'data-reciter="([^"]+)"', html)
    reciters_found = len(set(reciter_data_matches))
    if reciters_found < 14:
        missing.append(f"reciters: only {reciters_found}/14 found (need all 14 as <... data-reciter='id'>)")
    
    # 3. primitives.js script tag
    if "/api/agent/primitives/quran.js" not in html:
        missing.append("primitives script tag missing")
    
    # 4. audioUrl usage
    if "audioUrl" not in html and "everyayah.com" not in html:
        missing.append("no audio playback wiring (audioUrl never referenced)")
    
    # 5. click event listener
    has_listener = bool(re.search(r"addEventListener\s*\(\s*['\"]click", html)) or "onclick" in html
    if not has_listener:
        missing.append("no click event listener (interactions broken)")
    
    # 6. Surah selector — optional for creative sites (only flag as soft warning, not blocker)
    # Removed strict check — creative sites may not have a selector by design.
    
    return {
        "ok": len(missing) == 0,
        "ayahs_found": ayahs_found,
        "ayahs_expected": expected_ayahs,
        "reciters_found": reciters_found,
        "missing": missing,
    }


def _get_surah_name_ar(n: int) -> str:
    SURAHS = ["الفاتحة","البقرة","آل عمران","النساء","المائدة","الأنعام","الأعراف","الأنفال","التوبة","يونس","هود","يوسف","الرعد","إبراهيم","الحجر","النحل","الإسراء","الكهف","مريم","طه","الأنبياء","الحج","المؤمنون","النور","الفرقان","الشعراء","النمل","القصص","العنكبوت","الروم","لقمان","السجدة","الأحزاب","سبأ","فاطر","يس","الصافات","ص","الزمر","غافر","فصلت","الشورى","الزخرف","الدخان","الجاثية","الأحقاف","محمد","الفتح","الحجرات","ق","الذاريات","الطور","النجم","القمر","الرحمن","الواقعة","الحديد","المجادلة","الحشر","الممتحنة","الصف","الجمعة","المنافقون","التغابن","الطلاق","التحريم","الملك","القلم","الحاقة","المعارج","نوح","الجن","المزمل","المدثر","القيامة","الإنسان","المرسلات","النبأ","النازعات","عبس","التكوير","الانفطار","المطففين","الانشقاق","البروج","الطارق","الأعلى","الغاشية","الفجر","البلد","الشمس","الليل","الضحى","الشرح","التين","العلق","القدر","البينة","الزلزلة","العاديات","القارعة","التكاثر","العصر","الهمزة","الفيل","قريش","الماعون","الكوثر","الكافرون","النصر","المسد","الإخلاص","الفلق","الناس"]
    return SURAHS[n - 1] if 1 <= n <= 114 else "?"


# ════════════════════════════════════════════════════════════════════════
#  TOOL: fetch_quran_blocks — gives the AI ready-to-embed HTML/JS pieces
#  so it can integrate REAL Quran content into ANY creative design via
#  build_website (gaming/achievements/parent dashboard, etc.)
# ════════════════════════════════════════════════════════════════════════
async def fetch_quran_blocks(surah: int = 1) -> Dict[str, Any]:
    """🧩 Fetch real Quran data as ready-to-embed HTML/JS blocks.
    
    The AI can paste these blocks into ANY website design (built via
    build_website with a custom brief). This unlocks full creative freedom
    for Quran sites: gaming theme, achievement system, parent dashboard,
    multi-page apps, etc. — all with REAL Quran text + 14 reciters.
    
    Returns:
        ayahs_html: <div class="ayah-row" data-ayah="N">verse text + N</div> × ayah_count
        reciters_html: <button class="reciter-card" data-reciter="id">name</button> × 14
        primitives_script: <script src="/api/agent/primitives/quran.js"></script>
        audio_snippet: minimal JS to wire ayah clicks to audio playback
        surah_meta: {n, name_ar, name_en, type, ayah_count}
    """
    try:
        surah = int(surah)
    except (TypeError, ValueError):
        return {"ok": False, "error": "surah must be an integer 1-114"}
    if not (1 <= surah <= 114):
        return {"ok": False, "error": "surah must be 1..114"}
    
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(f"https://api.alquran.cloud/v1/surah/{surah}/quran-uthmani")
        data = r.json() if r.status_code == 200 else {}
        ayahs_data = (data.get("data") or {}).get("ayahs") or []
        meta = data.get("data") or {}
        if not ayahs_data:
            return {"ok": False, "error": "failed to fetch surah from alquran.cloud"}
    except Exception as e:
        return {"ok": False, "error": f"alquran.cloud unreachable: {e}"}
    
    ayahs_html = "\n".join(
        f'<div class="ayah-row" data-ayah="{a.get("numberInSurah")}" role="button" tabindex="0">'
        f'<span class="ayah-text">{a.get("text","")}</span>'
        f'<span class="ayah-num" data-num="{a.get("numberInSurah")}">{a.get("numberInSurah")}</span>'
        f'</div>'
        for a in ayahs_data
    )
    
    RECITERS_LIST = [
        {"id":"alafasy","name":"مشاري العفاسي"},{"id":"sudais","name":"عبد الرحمن السديس"},
        {"id":"shuraim","name":"سعود الشريم"},{"id":"husary","name":"محمود الحصري"},
        {"id":"minshawi","name":"محمد المنشاوي"},{"id":"abdulbasit","name":"عبد الباسط"},
        {"id":"ghamdi","name":"سعد الغامدي"},{"id":"ajmi","name":"أحمد العجمي"},
        {"id":"dossary","name":"ياسر الدوسري"},{"id":"shatri","name":"أبو بكر الشاطري"},
        {"id":"juhany","name":"عبد الله الجهني"},{"id":"hthfi","name":"علي الحذيفي"},
        {"id":"ayyub","name":"محمد أيوب"},{"id":"maher","name":"ماهر المعيقلي"},
    ]
    reciters_html = "\n".join(
        f'<button class="reciter-card" data-reciter="{r["id"]}" type="button">'
        f'<span class="reciter-avatar">{r["name"][0]}</span>'
        f'<span class="reciter-name">{r["name"]}</span>'
        f'</button>'
        for r in RECITERS_LIST
    )
    
    primitives_script = '<script src="/api/agent/primitives/quran.js"></script>'
    
    audio_snippet = """<script>
(function(){
  let activeReciter = 'alafasy';
  let currentAudio = null;
  const SURAH_N = """ + str(surah) + """;
  
  function play(ayahN, el) {
    if (currentAudio) { currentAudio.pause(); }
    document.querySelectorAll('.ayah-row.playing').forEach(e => e.classList.remove('playing'));
    if (el) el.classList.add('playing');
    currentAudio = new Audio(window.ZitexQuran.audioUrl(activeReciter, SURAH_N, ayahN));
    currentAudio.play().catch(e => console.error('audio failed:', e));
  }
  
  document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('.reciter-card').forEach(btn => {
      btn.addEventListener('click', function(){
        activeReciter = this.dataset.reciter;
        document.querySelectorAll('.reciter-card.active').forEach(e => e.classList.remove('active'));
        this.classList.add('active');
      });
    });
    document.querySelectorAll('.ayah-row').forEach(row => {
      row.addEventListener('click', function(){
        play(parseInt(this.dataset.ayah), this);
      });
    });
    const firstReciter = document.querySelector('.reciter-card[data-reciter="alafasy"]');
    if (firstReciter) firstReciter.classList.add('active');
  });
})();
</script>"""
    
    return {
        "ok": True,
        "ayahs_html": ayahs_html,
        "reciters_html": reciters_html,
        "primitives_script": primitives_script,
        "audio_snippet": audio_snippet,
        "surah_meta": {
            "n": surah,
            "name_ar": _get_surah_name_ar(surah),
            "name_en": (meta.get("englishName") or "").strip(),
            "type": meta.get("revelationType", "Meccan"),
            "ayah_count": len(ayahs_data),
        },
        "summary": f"كتل قرآن جاهزة (سورة {_get_surah_name_ar(surah)} · {len(ayahs_data)} آية)",
        "usage_hint": (
            "اللصق في build_website: ضع primitives_script في <head>، ضع ayahs_html و reciters_html "
            "داخل containers بأي تصميم تختاره، وضع audio_snippet قبل </body>. الكل سيعمل تلقائياً."
        ),
    }


# ════════════════════════════════════════════════════════════════════════
#  TOOL: build_creative_quran_site — bulletproof Quran + creative design
# ════════════════════════════════════════════════════════════════════════
async def build_creative_quran_site(
    brief: str,
    surah: int = 1,
    style_direction: str = "",
) -> Dict[str, Any]:
    """🎮 BULLETPROOF: build a creative Quran site with REAL Quran content
    GUARANTEED embedded via deterministic post-processing (not LLM trust).
    
    Use for gaming/achievement/dashboard/multi-page Quran sites where you
    need full creative freedom but guaranteed real Quran content.
    """
    if not brief or len(brief.strip()) < 5:
        return {"ok": False, "error": "brief too short"}
    try:
        surah = int(surah)
    except (TypeError, ValueError):
        return {"ok": False, "error": "surah must be an integer 1-114"}
    if not (1 <= surah <= 114):
        return {"ok": False, "error": "surah must be 1..114"}
    
    blocks = await fetch_quran_blocks(surah=surah)
    if not blocks.get("ok"):
        return {"ok": False, "error": f"could not fetch quran blocks: {blocks.get('error')}"}
    
    surah_name = _get_surah_name_ar(surah)
    ayah_count = blocks["surah_meta"]["ayah_count"]
    
    sys_prompt = f"""أنت معماري واجهات. مهمتك: تصميم موقع HTML واحد كامل حسب طلب العميل، يتضمن قارئ قرآن مدمج.

🎨 الإلزام الإبداعي:
- الموقع كامل: hero، أقسام إضافية حسب الطلب (achievements/dashboard/أي شيء)، footer.
- صمم بحرية مطلقة: gaming/luxury/minimal/brutalist/أي شيء يطابق الطلب.
- ممنوع تكتب آيات بنفسك. ممنوع تخترع قراء.

🔒 المتطلبات الإلزامية:
1. RTL، lang="ar"، Tajawal/Aref Ruqaa/Amiri Quran.
2. ضع هذين الـcomments داخل قسم المصحف:
   - <!-- ZITEX_QURAN_AYAHS -->  (سيُستبدل بـ {ayah_count} آية حقيقية)
   - <!-- ZITEX_QURAN_RECITERS --> (سيُستبدل بأزرار 14 قارئ)
3. لا تكتب الآيات أو القراء — فقط ضع الـcomments. النظام يحقن المحتوى الحقيقي.
4. اضمن CSS جميل لـ class="ayah-row" و class="reciter-card" داخل التصميم.
5. ⚠️ ممنوع تضع <script src="/api/agent/primitives/quran.js"> — النظام يحقنه.
6. ⚠️ ممنوع تكتب JS لتشغيل الصوت — النظام يحقنه.

📦 المخرجات: HTML واحد كامل من <!doctype html> إلى </html>. ممنوع شرح، ممنوع markdown fences."""
    
    user_prompt = f"""طلب العميل: {brief}

السورة المطلوبة في قسم المصحف: {surah_name} ({ayah_count} آية)
{f"توجيه التصميم: {style_direction}" if style_direction else ""}

تذكر: ضع <!-- ZITEX_QURAN_AYAHS --> و <!-- ZITEX_QURAN_RECITERS --> في قسم المصحف.

ابنِ الموقع الكامل الآن."""
    
    last_html = ""
    last_audit: Dict[str, Any] = {}
    for attempt in range(3):
        try:
            html = await _gpt_rewrite(sys_prompt, user_prompt, max_tokens=14000, temperature=0.95)
            html = re.sub(r"^```(?:html)?\s*", "", html)
            html = re.sub(r"\s*```\s*$", "", html)
            if "<html" not in html.lower():
                continue
            
            # DETERMINISTIC INJECTION
            if "<!-- ZITEX_QURAN_AYAHS -->" in html:
                html = html.replace("<!-- ZITEX_QURAN_AYAHS -->", blocks["ayahs_html"], 1)
            else:
                fallback = f'<section class="quran-section"><div class="ayahs-container">{blocks["ayahs_html"]}</div></section>'
                html = html.replace("</body>", fallback + "\n</body>", 1)
            
            if "<!-- ZITEX_QURAN_RECITERS -->" in html:
                html = html.replace("<!-- ZITEX_QURAN_RECITERS -->", blocks["reciters_html"], 1)
            else:
                rec_block = f'<div class="reciters-strip">{blocks["reciters_html"]}</div>'
                if 'class="ayahs-container"' in html:
                    html = html.replace('<div class="ayahs-container">', rec_block + '\n<div class="ayahs-container">', 1)
                else:
                    html = html.replace("</body>", rec_block + "\n</body>", 1)
            
            if "/api/agent/primitives/quran.js" not in html:
                html = html.replace("</head>", blocks["primitives_script"] + "\n</head>", 1)
            has_click_wiring = bool(re.search(r"\.ayah-row.*addEventListener", html, re.DOTALL))
            if not has_click_wiring:
                html = html.replace("</body>", blocks["audio_snippet"] + "\n</body>", 1)
            
            audit = _audit_quran_html(html, expected_ayahs=ayah_count)
            last_html = html
            last_audit = audit
            if audit["ok"]:
                return {
                    "ok": True,
                    "html": html,
                    "size_kb": round(len(html) / 1024, 1),
                    "surah": surah,
                    "audit": audit,
                    "attempts": attempt + 1,
                    "summary": f"✅ موقع قرآن إبداعي مكتمل (سورة {surah_name} · {audit['ayahs_found']} آية · 14 قارئ)",
                }
            issues_text = "\n".join(f"- {i}" for i in audit["missing"])
            user_prompt += f"\n\nالمحاولة السابقة فشلت:\n{issues_text}\n\nأعد البناء مع الالتزام الكامل."
        except Exception as e:
            logger.exception("[BUILD_CREATIVE_QURAN] attempt %d failed", attempt + 1)
            last_audit = {"ok": False, "error": str(e)[:200]}
    
    if last_html:
        return {
            "ok": True,
            "html": last_html,
            "size_kb": round(len(last_html) / 1024, 1),
            "surah": surah,
            "audit": last_audit,
            "attempts": 3,
            "warning": "audit_imperfect",
            "summary": f"⚠️ بُني بعد 3 محاولات: {last_audit.get('missing', [])}",
        }
    return {"ok": False, "error": last_audit.get("error", "all retries failed")}


# ════════════════════════════════════════════════════════════════════════
#  TOOL: inject_quran_blocks — fix existing site with broken Quran section
# ════════════════════════════════════════════════════════════════════════
async def inject_quran_blocks(
    surah: int = 1,
    target_selector: str = "",
    current_html: str = "",
) -> Dict[str, Any]:
    """🩹 Inject real Quran blocks into an EXISTING site (fix broken section)."""
    if not current_html or len(current_html) < 50:
        return {"ok": False, "error": "no current_html — use build_creative_quran_site instead"}
    
    blocks = await fetch_quran_blocks(surah=surah)
    if not blocks.get("ok"):
        return {"ok": False, "error": f"could not fetch quran blocks: {blocks.get('error')}"}
    
    new_html = current_html
    target_lc = (target_selector or "").strip().lower()
    
    quran_keywords = ['quran', 'mushaf', 'reader', 'ayah', 'verse', 'مصحف', 'قران', 'قرآن', 'تلاوة']
    
    section_re = re.compile(r"<section\b[^>]*>([\s\S]*?)</section>", re.IGNORECASE)
    matches = list(section_re.finditer(new_html))
    target_match = None
    for m in matches:
        opening_tag = m.group(0)[:m.group(0).find(">") + 1].lower()
        kw_pool = quran_keywords + ([target_lc] if target_lc else [])
        if any(kw in opening_tag for kw in kw_pool):
            target_match = m
            break
    
    inner = (
        f'<div class="reciters-strip">{blocks["reciters_html"]}</div>\n'
        f'<div class="ayahs-container">{blocks["ayahs_html"]}</div>'
    )
    
    if target_match:
        opening = re.match(r"(<section\b[^>]*>)", target_match.group(0)).group(1)
        new_section = opening + "\n" + inner + "\n</section>"
        new_html = new_html[: target_match.start()] + new_section + new_html[target_match.end():]
        location = "replaced existing quran section"
    else:
        new_section = f'<section class="quran-section" id="quran-reader" style="padding:3rem 1rem;max-width:900px;margin:0 auto;">\n{inner}\n</section>'
        new_html = new_html.replace("</body>", new_section + "\n</body>", 1)
        location = "appended new quran section"
    
    if "/api/agent/primitives/quran.js" not in new_html:
        new_html = new_html.replace("</head>", blocks["primitives_script"] + "\n</head>", 1)
    has_click_wiring = bool(re.search(r"\.ayah-row.*addEventListener", new_html, re.DOTALL))
    if not has_click_wiring:
        new_html = new_html.replace("</body>", blocks["audio_snippet"] + "\n</body>", 1)
    
    if ".ayah-row" not in new_html:
        default_css = """<style>
.ayah-row{cursor:pointer;padding:1.2rem 1.5rem;margin:.5rem 0;border-radius:.8rem;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);display:flex;align-items:center;gap:1rem;transition:all .3s}
.ayah-row:hover{background:rgba(251,191,36,.1);border-color:rgba(251,191,36,.3);transform:translateX(-4px)}
.ayah-row.playing{background:rgba(251,191,36,.18);border-color:#fbbf24;box-shadow:0 0 24px rgba(251,191,36,.4)}
.ayah-text{font-family:'Amiri Quran','Aref Ruqaa',serif;font-size:1.6rem;line-height:2.6;flex:1;text-align:right}
.ayah-num{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;background:#fbbf24;color:#000;font-weight:900;font-size:.85rem;flex-shrink:0}
.reciters-strip{display:flex;gap:.5rem;flex-wrap:wrap;justify-content:center;padding:1rem;margin-bottom:1.5rem}
.reciter-card{display:inline-flex;align-items:center;gap:.5rem;padding:.6rem 1rem;border-radius:999px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);color:inherit;cursor:pointer;font-size:.85rem;transition:all .25s}
.reciter-card:hover{background:rgba(251,191,36,.12);border-color:rgba(251,191,36,.3)}
.reciter-card.active{background:#fbbf24;color:#000;border-color:#fbbf24;font-weight:700}
.reciter-avatar{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:rgba(0,0,0,.2);font-weight:900}
</style>"""
        new_html = new_html.replace("</head>", default_css + "\n</head>", 1)
    
    audit = _audit_quran_html(new_html, expected_ayahs=blocks["surah_meta"]["ayah_count"])
    return {
        "ok": True,
        "html": new_html,
        "size_kb": round(len(new_html) / 1024, 1),
        "audit": audit,
        "location": location,
        "summary": f"✅ تم زرع كتل القرآن ({location} · {audit['ayahs_found']} آية · {audit['reciters_found']} قارئ)",
    }


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
    "build_quran_mushaf_reader": build_quran_mushaf_reader,
    "fetch_quran_blocks": fetch_quran_blocks,
    "build_creative_quran_site": build_creative_quran_site,
    "inject_quran_blocks": inject_quran_blocks,
    "analyze_intent": analyze_intent,
    "pick_design": pick_design,
    "qa_html": qa_html,
    "geo_lookup": geo_lookup,
    "publish_site": publish_site,
})
