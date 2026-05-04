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
]


# Map of tool name → callable
TOOL_REGISTRY: Dict[str, Callable[..., Awaitable[Dict[str, Any]]]] = {
    "quran_reciter_lookup": quran_reciter_lookup,
    "quran_verse_fetch": quran_verse_fetch,
    "web_search": web_search,
    "web_fetch": web_fetch,
    "generate_image_url": generate_image_url,
    "saudi_official_sources": saudi_official_sources,
    "sports_team_lookup": sports_team_lookup,
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
