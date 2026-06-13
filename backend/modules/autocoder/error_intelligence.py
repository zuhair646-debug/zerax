"""
Error Intelligence — the AI's autonomous problem-solving brain.

When the AI hits an error or unfamiliar issue, instead of guessing or
hallucinating, it follows this protocol automatically:

  1. recall_lessons(query) → have I seen this before?
  2. research_error(error, context) → search StackOverflow + GitHub + web
  3. propose_fix(...) → write the plan
  4. try_until_works(plan) → execute with retries
  5. learn_from_error(...) → save the lesson for next time

Three new tools:
  • research_error(error, context?, language?) — multi-source search
  • learn_from_error(error, root_cause, fix, tags?) — structured lesson save
  • diagnose_and_research(symptom) — auto_diagnose + research in one call

Sources searched:
  • StackOverflow Q&A (api.stackexchange.com — public, no key needed)
  • GitHub Issues + Code (api.github.com — uses GITHUB_PAT if available)
  • Tavily web search (existing tool) for docs and articles
"""
from __future__ import annotations
import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

_DB: Any = None


def bind_db(db) -> None:
    global _DB
    _DB = db


# ════════════════════════════════════════════════════════════════════════
# StackOverflow search (Stack Exchange API v2.3, no key needed for low volume)
# ════════════════════════════════════════════════════════════════════════
async def _search_stackoverflow(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    url = "https://api.stackexchange.com/2.3/search/advanced"
    params = {
        "order": "desc",
        "sort": "relevance",
        "q": query,
        "site": "stackoverflow",
        "pagesize": min(max_results, 10),
        "filter": "default",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params=params)
        if r.status_code != 200:
            return []
        data = r.json()
    except Exception as e:
        logger.warning(f"[SO] search failed: {e}")
        return []
    items = []
    for q in (data.get("items") or [])[:max_results]:
        items.append({
            "title": q.get("title", "")[:200],
            "url": q.get("link", ""),
            "score": q.get("score", 0),
            "answer_count": q.get("answer_count", 0),
            "is_answered": q.get("is_answered", False),
            "tags": q.get("tags", [])[:5],
            "creation_date": q.get("creation_date"),
        })
    return items


# ════════════════════════════════════════════════════════════════════════
# GitHub Issues + Code search (api.github.com)
# ════════════════════════════════════════════════════════════════════════
async def _search_github_issues(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    url = "https://api.github.com/search/issues"
    pat = os.environ.get("GITHUB_PAT") or os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if pat:
        headers["Authorization"] = f"Bearer {pat}"
    params = {"q": query, "per_page": min(max_results, 10), "sort": "reactions"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params=params, headers=headers)
        if r.status_code != 200:
            return []
        data = r.json()
    except Exception as e:
        logger.warning(f"[GH] issues search failed: {e}")
        return []
    items = []
    for it in (data.get("items") or [])[:max_results]:
        items.append({
            "title": it.get("title", "")[:200],
            "url": it.get("html_url", ""),
            "state": it.get("state"),
            "comments": it.get("comments", 0),
            "reactions": (it.get("reactions") or {}).get("total_count", 0),
            "repo": "/".join((it.get("repository_url", "") or "").split("/")[-2:]),
            "body_excerpt": (it.get("body") or "")[:300],
        })
    return items


# ════════════════════════════════════════════════════════════════════════
# Tool: research_error
# ════════════════════════════════════════════════════════════════════════
async def tool_research_error(
    error: str,
    context: str = "",
    language: str = "",
    max_per_source: int = 4,
) -> Dict[str, Any]:
    """Search StackOverflow + GitHub Issues + (optionally) Tavily web for an error.

    Args:
        error: the error text / stack trace / message (1st 300 chars used for SO query)
        context: optional surrounding info (lib name, framework, what you tried)
        language: optional lang filter ('python', 'javascript', 'react'...)
        max_per_source: 1-10, results per source (default 4)
    """
    if not error or not error.strip():
        return {"ok": False, "error": "error text فاضي"}

    # Build a cleaner query: strip file paths, line numbers, hex addresses
    cleaned = re.sub(r"/[\w/.\-]+:\d+", "", error)
    cleaned = re.sub(r"0x[0-9a-fA-F]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()[:300]
    so_query = cleaned
    if language:
        so_query = f"[{language}] {so_query}"
    gh_query = cleaned
    if language:
        gh_query += f" language:{language}"

    max_per = max(1, min(int(max_per_source or 4), 10))

    # Parallel search
    import asyncio
    so_task = _search_stackoverflow(so_query, max_per)
    gh_task = _search_github_issues(gh_query, max_per)
    web_task = None
    try:
        from .web_search import tool_web_search
        web_query = f"{cleaned} {language} fix solution"
        web_task = tool_web_search(query=web_query, max_results=max_per, search_depth="basic")
    except Exception:
        web_task = None

    if web_task is not None:
        so_results, gh_results, web_results = await asyncio.gather(so_task, gh_task, web_task, return_exceptions=True)
    else:
        so_results, gh_results = await asyncio.gather(so_task, gh_task, return_exceptions=True)
        web_results = None

    so_results = so_results if isinstance(so_results, list) else []
    gh_results = gh_results if isinstance(gh_results, list) else []
    web_block = (web_results or {}) if isinstance(web_results, dict) else {}

    # Also pull prior lessons matching the error
    similar_lessons: List[Dict[str, Any]] = []
    try:
        from .learning import query_lessons
        keywords = " ".join(cleaned.split()[:6])
        similar_lessons = await query_lessons(query=keywords, limit=5)
    except Exception:
        pass

    return {
        "ok": True,
        "query": cleaned,
        "language": language or None,
        "stackoverflow": {"count": len(so_results), "items": so_results},
        "github_issues": {"count": len(gh_results), "items": gh_results},
        "web": {
            "answer": (web_block.get("answer") or "")[:1200],
            "count": len((web_block.get("results") or [])),
            "items": (web_block.get("results") or [])[:max_per],
        },
        "prior_lessons": {
            "count": len(similar_lessons),
            "items": [{
                "task_summary": ls.get("task_summary"),
                "lesson": ls.get("lesson"),
                "tags": ls.get("tags", []),
            } for ls in similar_lessons],
        },
        "guidance": (
            "Now combine: (a) prior_lessons (most trusted — you've solved this before), "
            "(b) high-score answered SO threads, (c) GitHub Issues with high reactions = real bugs, "
            "(d) web answer for context. Propose a concrete fix and call try_until_works."
        ),
    }


# ════════════════════════════════════════════════════════════════════════
# Tool: learn_from_error  (structured wrapper around record_lesson)
# ════════════════════════════════════════════════════════════════════════
async def tool_learn_from_error(
    error: str,
    root_cause: str,
    fix: str,
    tags: str = "",
    code_pattern: str = "",
) -> Dict[str, Any]:
    """Record a structured error-recovery lesson. Call this AFTER you've verified
    a fix actually worked. Keeps the lesson format consistent so recall is sharp.

    Args:
        error: the error text or symptom (≤300 chars)
        root_cause: what was actually wrong (≤300 chars)
        fix: what you did to fix it (≤500 chars)
        tags: comma-separated, e.g. 'frontend,react,hooks'
        code_pattern: optional code snippet that demonstrates the fix
    """
    if not error or not root_cause or not fix:
        return {"ok": False, "error": "error + root_cause + fix كلها مطلوبة"}
    try:
        from .learning import add_lesson
    except Exception as e:
        return {"ok": False, "error": f"learning module not loaded: {e}"}

    summary = f"خطأ: {error[:200]}"
    lesson = f"السبب: {root_cause[:300]}\n→ الحل: {fix[:500]}"
    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    # Always add 'error-recovery' tag so we can filter these specially
    if "error-recovery" not in tag_list:
        tag_list.append("error-recovery")
    return await add_lesson(
        task_summary=summary,
        lesson=lesson,
        source="system",
        code_pattern=code_pattern or None,
        tags=tag_list,
    )


# ════════════════════════════════════════════════════════════════════════
# Tool: diagnose_and_research  (chain: auto_diagnose → research_error)
# ════════════════════════════════════════════════════════════════════════
async def tool_diagnose_and_research(
    symptom: str,
    scope: str = "all",
    language: str = "",
) -> Dict[str, Any]:
    """One-shot: run auto_diagnose to gather facts, then research_error on the
    most salient symptom. Use this for opaque "something's broken" reports.
    """
    if not symptom or not symptom.strip():
        return {"ok": False, "error": "symptom فاضي"}
    # Late import to avoid circular
    try:
        # tool_auto_diagnose is defined in __init__.py
        from . import tool_auto_diagnose as _diag
    except Exception:
        _diag = None
    diag_out: Dict[str, Any] = {}
    if _diag is not None:
        try:
            diag_out = await _diag(symptom, scope)
        except Exception as e:
            diag_out = {"ok": False, "error": str(e)[:200]}
    # Build a stronger query using diag findings
    facts = (diag_out.get("findings") or "") if isinstance(diag_out, dict) else ""
    research_query = symptom + " " + (facts[:200] or "")
    research = await tool_research_error(error=research_query, language=language)
    return {
        "ok": True,
        "symptom": symptom[:200],
        "diagnosis": diag_out,
        "research": research,
        "next_step": "Use 'try_until_works' with a plan derived from research.web.answer + top SO answer.",
    }


# ════════════════════════════════════════════════════════════════════════
# Anthropic schemas
# ════════════════════════════════════════════════════════════════════════
ERROR_INTEL_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "research_error",
        "description": (
            "🔬 ابحث عن حل لخطأ من مصادر متعددة بالتوازي: StackOverflow + GitHub Issues + "
            "بحث الويب + ذاكرتك الخاصة (autocoder_lessons). استخدمها قبل ما تخمّن. "
            "ترجع نتائج مرتّبة حسب الجودة (SO score, GH reactions) عشان تختار الأنسب."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "error": {"type": "string", "description": "نص الخطأ أو الـ stack trace (≤300 حرف يكفي)"},
                "context": {"type": "string", "description": "(اختياري) سياق إضافي: المكتبة، الإطار، اللي حاولته"},
                "language": {"type": "string", "description": "(اختياري) python, javascript, react, etc."},
                "max_per_source": {"type": "integer", "description": "1-10 (افتراضي 4)"},
            },
            "required": ["error"],
        },
    },
    {
        "name": "learn_from_error",
        "description": (
            "📚 سجّل درس مهيكل بعد ما تتأكد إن الحل اشتغل فعلاً. تستدعيها بعد try_until_works ينجح. "
            "هذا يضمن إنك ما تكرر نفس الخطأ في جلسات لاحقة."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "error": {"type": "string", "description": "نص الخطأ / العَرَض"},
                "root_cause": {"type": "string", "description": "السبب الحقيقي"},
                "fix": {"type": "string", "description": "وش سويت بالضبط عشان تصلحه"},
                "tags": {"type": "string", "description": "(اختياري) tags بفاصلة"},
                "code_pattern": {"type": "string", "description": "(اختياري) snippet كود مفيد"},
            },
            "required": ["error", "root_cause", "fix"],
        },
    },
    {
        "name": "diagnose_and_research",
        "description": (
            "🩺🔬 سلسلة موحّدة: شغّل auto_diagnose ثم research_error على أبرز نتائجه. "
            "الأنسب لما المالك يقول 'في خلل' بدون تفاصيل دقيقة."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symptom": {"type": "string", "description": "العَرَض اللي شفته"},
                "scope": {"type": "string", "description": "all|backend|frontend|deployment"},
                "language": {"type": "string", "description": "(اختياري)"},
            },
            "required": ["symptom"],
        },
    },
]


ERROR_INTEL_TOOL_HANDLERS = {
    "research_error": tool_research_error,
    "learn_from_error": tool_learn_from_error,
    "diagnose_and_research": tool_diagnose_and_research,
}


ERROR_INTEL_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "research_error", "desc": "multi-source error search (SO+GH+web+lessons)", "args": ["error", "context?", "language?"]},
    {"name": "learn_from_error", "desc": "structured lesson after a fix", "args": ["error", "root_cause", "fix", "tags?"]},
    {"name": "diagnose_and_research", "desc": "auto_diagnose + research in one", "args": ["symptom", "scope?", "language?"]},
]


def error_intel_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in ERROR_INTEL_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return f"🔬✗ {(result.get('error') or '')[:120]}"
    if name == "research_error":
        so = result.get("stackoverflow", {}).get("count", 0)
        gh = result.get("github_issues", {}).get("count", 0)
        wb = result.get("web", {}).get("count", 0)
        lt = result.get("prior_lessons", {}).get("count", 0)
        return f"🔬 SO:{so} · GH:{gh} · Web:{wb} · ذاكرة:{lt}"
    if name == "learn_from_error":
        return f"📚 تم تسجيل درس استرداد ({result.get('lesson_id','')[:8]}…)"
    if name == "diagnose_and_research":
        r = result.get("research", {})
        return f"🩺🔬 SO:{r.get('stackoverflow',{}).get('count',0)} · GH:{r.get('github_issues',{}).get('count',0)}"
    return None


def error_intel_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in ERROR_INTEL_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return None
    if name == "research_error":
        out: List[str] = []
        web = result.get("web", {})
        if web.get("answer"):
            out.append(f"📝 {web['answer'][:280]}")
        for it in (result.get("stackoverflow", {}).get("items") or [])[:3]:
            mark = "✅" if it.get("is_answered") else "❔"
            out.append(f"  {mark} SO ({it.get('score',0)}): {it.get('title','')[:80]} — {it.get('url')}")
        for it in (result.get("github_issues", {}).get("items") or [])[:2]:
            out.append(f"  🐙 GH ({it.get('reactions',0)}): {it.get('title','')[:80]} — {it.get('url')}")
        for ls in (result.get("prior_lessons", {}).get("items") or [])[:2]:
            out.append(f"  📚 درس سابق: {ls.get('task_summary','')[:80]}")
        return "\n".join(out)[:1500]
    if name == "diagnose_and_research":
        return error_intel_preview("research_error", result.get("research", {})) or ""
    return None


ERROR_INTEL_PROMPT_RULES = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠🔬 بروتوكول استرداد الأخطاء (Error Recovery Protocol)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

لما تواجه خطأ أو سلوك غريب أو فشل أداة، **التزم بهذا الترتيب — ممنوع التخمين**:

  1️⃣  recall_lessons(query=<keywords من الخطأ>)
        → هل عندك درس مسجّل لنفس المشكلة؟ إذا أيوه، طبّقه فوراً.

  2️⃣  إذا ما لقيت درس → research_error(error=<النص>, language=<py/js/...>)
        → بحث متوازي في StackOverflow + GitHub Issues + Tavily + ذاكرتك.
        → ركّز على إجابات SO عالية score + مشاكل GH كثيرة reactions.

  3️⃣  لو الخطأ ضبابي ("في شي مكسور") → diagnose_and_research(symptom=…)
        → يجمع auto_diagnose مع research_error في خطوة واحدة.

  4️⃣  بعد ما تصيغ الحل → try_until_works(plan=[…], max_attempts=3)
        → جرّب فعلياً ولا تدّعي النجاح قبل التحقق.

  5️⃣  بعد ما يشتغل الحل فعلاً → learn_from_error(error, root_cause, fix, tags)
        → سجّل الدرس بصيغة مهيكلة. هذا يضمن إنك ما تتعثّر بنفس الحفرة مرتين.

🚫 ممنوع:
  • تخمين السبب بدون تحقق
  • تجربة حل عشوائي ثاني قبل البحث
  • ادّعاء إن المشكلة "محلولة" بدون اختبار فعلي (try_until_works أو self_verify_claim)
  • تكرار نفس المحاولة الفاشلة بدون تغيير في الـ approach

✅ مطلوب:
  • مصدر لكل حل (SO link أو GH issue أو درس سابق)
  • التحقق العملي بـ try_until_works قبل قول "تم"
  • تسجيل درس بعد كل خطأ مهم تحلّه — حتى لو سهل
"""
