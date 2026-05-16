"""
Web search tool for the Auto-Coder — powered by Tavily AI search.

Lets the AI look up:
  - Current API documentation (Stripe, Google OAuth, fal.ai, etc.)
  - "Where do I get an API key for X?" walkthroughs
  - Latest version numbers / breaking changes / migration guides
  - News (when the user asks about a recent event)

Endpoint: POST https://api.tavily.com/search
Auth:     Authorization: Bearer tvly-XXX
Pricing:  Free tier 1000 credits/month. basic=1 credit, advanced=2.
Docs:     https://docs.tavily.com/documentation/api-reference/endpoint/search

Tools added:
  • web_search(query, max_results?, topic?, search_depth?, include_answer?)
  • where_to_get_key(service)   — convenience: searches Tavily for the
                                   official "create API key" docs page
"""
from __future__ import annotations
import os
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

TAVILY_ENDPOINT = "https://api.tavily.com/search"

_DB: Optional[Any] = None  # mongo handle (for vault-stored fallback key)


def bind_db(db) -> None:
    global _DB
    _DB = db


async def _get_tavily_key() -> str:
    """env first, then encrypted vault."""
    k = os.environ.get("TAVILY_API_KEY", "").strip()
    if k:
        return k
    if _DB is None:
        return ""
    try:
        doc = await _DB.credentials_vault.find_one({"service": "tavily"}, {"_id": 0})
        if not doc:
            return ""
        enc = doc.get("value_encrypted") or ""
        if not enc:
            return ""
        import base64
        import hashlib
        from cryptography.fernet import Fernet
        seed = (os.environ.get("JWT_SECRET", "") + os.environ.get("MONGO_URL", "")).encode()
        key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
        return Fernet(key).decrypt(enc.encode()).decode()
    except Exception as e:
        logger.warning(f"[tavily] vault read failed: {e}")
        return ""


async def tool_web_search(
    query: str,
    max_results: int = 5,
    topic: str = "general",
    search_depth: str = "basic",
    include_answer: bool = True,
    time_range: Optional[str] = None,
) -> Dict[str, Any]:
    """Search the live web via Tavily.

    Args:
        query: natural-language search string
        max_results: 1-10 (default 5)
        topic: 'general' | 'news' (default general)
        search_depth: 'basic' (1 credit) | 'advanced' (2 credits)
        include_answer: ask Tavily to return a 1-paragraph LLM answer (recommended)
        time_range: optional 'd'|'w'|'m'|'y' to bias toward recent results
    """
    if not query or not query.strip():
        return {"ok": False, "error": "query فاضي"}

    api_key = await _get_tavily_key()
    if not api_key:
        return {
            "ok": False,
            "error": "TAVILY_API_KEY غير مهيأ",
            "where_to_get": "https://app.tavily.com (سجل دخول → API Keys → Create) — مجاني 1000 credits/شهر",
            "after_obtaining": "أعطه للمالك يضيفه في /admin/independence أو يحفظه عبر credentials_vault",
        }

    # Bound parameters to avoid runaway credit usage
    max_results = max(1, min(int(max_results or 5), 10))
    if topic not in ("general", "news"):
        topic = "general"
    if search_depth not in ("basic", "advanced"):
        search_depth = "basic"

    payload: Dict[str, Any] = {
        "query": query.strip()[:400],
        "max_results": max_results,
        "topic": topic,
        "search_depth": search_depth,
        "include_answer": "advanced" if include_answer else False,
        "include_raw_content": False,
        "include_images": False,
    }
    if time_range and time_range in ("d", "w", "m", "y"):
        payload["time_range"] = time_range

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(TAVILY_ENDPOINT, json=payload, headers=headers)
        if resp.status_code == 401:
            return {"ok": False, "error": "Tavily 401 — التوكن غير صحيح"}
        if resp.status_code == 429:
            return {"ok": False, "error": "Tavily 429 — تجاوزت حد الـrate limit، انتظر دقيقة"}
        if resp.status_code >= 400:
            return {"ok": False, "error": f"Tavily {resp.status_code}: {resp.text[:200]}"}
        data = resp.json()
    except httpx.RequestError as e:
        return {"ok": False, "error": f"شبكة: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"خطأ: {e}"}

    # Distill response — keep only what's useful for tool reasoning
    results = []
    for r in (data.get("results") or [])[:max_results]:
        results.append({
            "title": (r.get("title") or "")[:200],
            "url": r.get("url"),
            "content": (r.get("content") or "")[:600],
            "score": round(float(r.get("score") or 0), 3),
        })

    return {
        "ok": True,
        "query": data.get("query") or query,
        "answer": (data.get("answer") or "")[:1500],
        "results": results,
        "result_count": len(results),
        "response_time_sec": round(float(data.get("response_time") or 0), 2),
    }


async def tool_where_to_get_key(service: str) -> Dict[str, Any]:
    """Convenience wrapper: searches the Tavily index for the official
    'create API key' / 'get API token' page of a given third-party service.

    Returns a curated answer + the top-3 most relevant pages.
    """
    if not service or not service.strip():
        return {"ok": False, "error": "service مطلوب (مثلاً: stripe, openrouter, fal)"}

    q = f"how to create an API key for {service.strip()} 2026 official docs"
    res = await tool_web_search(
        query=q, max_results=5, topic="general",
        search_depth="basic", include_answer=True,
    )
    if not res.get("ok"):
        return res

    # Heuristic: prefer results from official docs domains
    service_low = service.lower()
    sorted_results = sorted(
        res["results"],
        key=lambda r: (
            0 if any(k in (r.get("url") or "").lower() for k in (
                f"{service_low}.com/docs", f"docs.{service_low}", f"{service_low}.ai/docs",
                f"{service_low}.dev/docs", "developers.", "platform.", "console.", "dashboard.",
            )) else 1,
            -r.get("score", 0),
        ),
    )
    return {
        "ok": True,
        "service": service.strip(),
        "answer": res.get("answer", ""),
        "top_3": sorted_results[:3],
        "all_results": sorted_results,
    }


# ════════════════════════════════════════════════════════════════════════
# Anthropic schemas + handlers
# ════════════════════════════════════════════════════════════════════════
WEB_SEARCH_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "web_search",
        "description": (
            "🌐 ابحث في الويب الحي عبر Tavily. استخدمها لما تحتاج: "
            "(١) توثيق API محدّث (Stripe, OpenAI, Google Cloud...) "
            "(٢) رقم إصدار حالي أو breaking changes "
            "(٣) أخبار حديثة. لا تستخدمها لأسئلة معرفية عامة. "
            "basic=1 credit, advanced=2 (الحد المجاني 1000 credit/شهر)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "السؤال بالطبيعي (إنجليزي يعطي نتائج أفضل)"},
                "max_results": {"type": "integer", "description": "1-10 (افتراضي 5)"},
                "topic": {"type": "string", "enum": ["general", "news"], "description": "news للأحداث الحديثة"},
                "search_depth": {"type": "string", "enum": ["basic", "advanced"]},
                "include_answer": {"type": "boolean", "description": "افتراضي true — Tavily يلخّص بفقرة واحدة"},
                "time_range": {"type": "string", "enum": ["d", "w", "m", "y"], "description": "حصر النتائج لآخر يوم/أسبوع/شهر/سنة"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "where_to_get_key",
        "description": (
            "🔑 ابحث عن صفحة الـAPI keys الرسمية لخدمة معيّنة. "
            "مفيد لما تبي ترشد المالك يحصل على مفتاح Stripe/OpenRouter/Fal/إلخ. "
            "يرجع answer ملخّص + روابط مرتّبة (docs الرسمية أولاً)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "اسم الخدمة (مثل: stripe, openrouter, fal, sentry)"},
            },
            "required": ["service"],
        },
    },
]


WEB_SEARCH_TOOL_HANDLERS = {
    "web_search": tool_web_search,
    "where_to_get_key": tool_where_to_get_key,
}


WEB_SEARCH_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "web_search", "desc": "live web search (Tavily)", "args": ["query", "max_results?", "topic?", "search_depth?"]},
    {"name": "where_to_get_key", "desc": "find official API-key page", "args": ["service"]},
]


def web_search_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in WEB_SEARCH_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return f"🌐✗ {(result.get('error') or '')[:120]}"
    if name == "web_search":
        return f"🌐 {result.get('result_count', 0)} نتيجة في {result.get('response_time_sec', 0)}ث"
    if name == "where_to_get_key":
        return f"🔑 {result.get('service')}: {len(result.get('top_3', []))} رابط رسمي"
    return None


def web_search_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in WEB_SEARCH_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return None
    if name == "web_search":
        out = []
        if result.get("answer"):
            out.append(f"📝 {result['answer'][:300]}")
        for r in (result.get("results") or [])[:3]:
            out.append(f"• {r.get('title', '')[:80]} — {r.get('url', '')}")
        return "\n".join(out)[:800]
    if name == "where_to_get_key":
        out = [f"📝 {result.get('answer', '')[:200]}"]
        for r in result.get("top_3", []):
            out.append(f"• {r.get('title', '')[:80]} — {r.get('url', '')}")
        return "\n".join(out)[:800]
    return None


WEB_SEARCH_PROMPT_RULES = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 Web Search (Tavily) — متى تستخدم
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

استخدم `web_search` لما:
  • تحتاج رقم إصدار حالي (gpt-X.X, claude-X.X, إلخ)
  • تبحث عن breaking changes أو migration guide
  • السؤال عن خبر/حدث حديث
  • تحتاج توثيق API ما تتذكره بدقة

استخدم `where_to_get_key` لما:
  • المالك يطلب تكامل جديد (Stripe, OpenRouter, Fal...)
  • تبي تعطيه الرابط الرسمي + الخطوات لإصدار المفتاح
  • قبل ما تطلب منه المفتاح اعرف وين يصدّره من

⚠️ لا تستخدمها للمعرفة العامة — وفّر الـcredits.
الحد المجاني 1000 credit/شهر · basic=1 · advanced=2.

كل بحث ينتهي بقائمة روابط — اذكر للمالك المصدر دائماً.
"""
