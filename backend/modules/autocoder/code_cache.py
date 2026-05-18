"""
Code Cache — Smart caching layer to drastically reduce LLM token spend.

Three layers of caching:

  1. **FILE CACHE** (`autocoder_file_cache` collection):
     Keyed by absolute path. Stores SHA-256 of file content, line counts,
     AI-generated summaries, and per-function/class indices. When the
     auto-coder asks to read a file we already analysed AND the SHA is
     unchanged, we return the cached summary instead of forcing the AI to
     re-ingest the entire file.

  2. **QUERY CACHE** (`autocoder_query_cache` collection):
     Keyed by SHA of normalized question. Optionally embedded via OpenAI
     `text-embedding-3-small` so semantically similar questions hit the
     cache even when wording differs. Stores the assistant's final answer,
     the files it touched, and the model used.

  3. **STATS** (`autocoder_cache_stats` collection, singleton):
     Tracks cumulative token savings, hit/miss counts so we can show the
     owner a live dashboard.

Cost model (Feb 2026):
  • text-embedding-3-small: $0.02 / 1M tokens (~free for our use).
  • A typical 800-line file ≈ 3,000 tokens; one cache hit saves ~3,000
    input tokens. Across an autonomous session with 30 file reads this is
    ~90,000 tokens saved. At Claude Sonnet 4.5 input cost ($3/M) that's
    ~$0.27 per session. At GPT-5 input ($1.25/M) ~$0.11/session.

Design notes:
  • All MongoDB operations are wrapped in try/except — caching is an
    optimisation, not a hard dependency. If Mongo is unreachable we
    degrade gracefully to no-op (the AI still works, just spends tokens).
  • SHA-256 over file bytes — guarantees byte-exact equality before we
    return cached state.
  • Embeddings are cached in-process for the lifetime of the worker, so
    we never re-embed the same query twice.
"""
from __future__ import annotations
import os
import re
import time
import json
import hashlib
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_DB: Any = None

# Tunables ───────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dims, $0.02 / 1M tokens
EMBEDDING_DIMS = 1536
SEMANTIC_SIMILARITY_THRESHOLD = 0.92  # cosine; conservative to avoid false hits
QUERY_CACHE_TTL_DAYS = 14
FILE_CACHE_MAX_SUMMARY_CHARS = 8_000
TOKENS_PER_CHAR_APPROX = 0.25  # rough heuristic for token-savings reporting

# In-process embedding cache: query_sha -> vector
_EMB_CACHE: Dict[str, List[float]] = {}
_EMB_CACHE_MAX = 512


def bind_db(db) -> None:
    global _DB
    _DB = db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_sha256(path: str) -> str:
    try:
        p = Path(path)
        if not p.exists() or p.is_dir():
            return ""
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception:
        return ""


def _norm_query(q: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation that doesn't change meaning."""
    q = (q or "").strip().lower()
    q = re.sub(r"\s+", " ", q)
    q = re.sub(r"[\"'`،,\.\?!:؛]", "", q)
    return q[:2000]


def _query_sha(q: str) -> str:
    return hashlib.sha256(_norm_query(q).encode("utf-8")).hexdigest()


def _approx_tokens_saved(chars: int) -> int:
    return int(chars * TOKENS_PER_CHAR_APPROX)


# ════════════════════════════════════════════════════════════════════════
# Embedding helper (OpenAI text-embedding-3-small)
# ════════════════════════════════════════════════════════════════════════
async def _embed(text: str) -> Optional[List[float]]:
    if not text:
        return None
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if sha in _EMB_CACHE:
        return _EMB_CACHE[sha]
    key = (os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        return None
    try:
        # Use openai>=1.0 async client if available; fall back to httpx for portability.
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": EMBEDDING_MODEL, "input": text[:8000]},
            )
            if r.status_code != 200:
                logger.warning(f"embed failed {r.status_code}: {r.text[:200]}")
                return None
            data = r.json()
            vec = data.get("data", [{}])[0].get("embedding")
            if vec and isinstance(vec, list):
                if len(_EMB_CACHE) >= _EMB_CACHE_MAX:
                    # naive LRU: drop one
                    _EMB_CACHE.pop(next(iter(_EMB_CACHE)))
                _EMB_CACHE[sha] = vec
                return vec
    except Exception as e:
        logger.warning(f"embed exception: {e}")
    return None


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    num = sum(x * y for x, y in zip(a, b))
    da = sum(x * x for x in a) ** 0.5
    db = sum(y * y for y in b) ** 0.5
    if da == 0 or db == 0:
        return 0.0
    return num / (da * db)


# ════════════════════════════════════════════════════════════════════════
# STATS helpers
# ════════════════════════════════════════════════════════════════════════
async def _bump_stats(*, hit: bool, tokens_saved: int = 0, layer: str = "file") -> None:
    if _DB is None:
        return
    try:
        await _DB.autocoder_cache_stats.update_one(
            {"_id": "main"},
            {
                "$inc": {
                    f"{layer}_hits": 1 if hit else 0,
                    f"{layer}_misses": 0 if hit else 1,
                    "total_tokens_saved": tokens_saved,
                },
                "$set": {"updated_at": _now()},
            },
            upsert=True,
        )
    except Exception as e:
        logger.debug(f"stats bump failed: {e}")


async def get_stats() -> Dict[str, Any]:
    if _DB is None:
        return {"ok": False, "error": "DB not bound"}
    try:
        doc = await _DB.autocoder_cache_stats.find_one({"_id": "main"}, {"_id": 0})
        if not doc:
            doc = {}
        # Total entries
        files = await _DB.autocoder_file_cache.count_documents({})
        queries = await _DB.autocoder_query_cache.count_documents({})
        return {
            "ok": True,
            "file_hits": doc.get("file_hits", 0),
            "file_misses": doc.get("file_misses", 0),
            "query_hits": doc.get("query_hits", 0),
            "query_misses": doc.get("query_misses", 0),
            "total_tokens_saved": doc.get("total_tokens_saved", 0),
            "files_cached": files,
            "queries_cached": queries,
            "updated_at": doc.get("updated_at"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ════════════════════════════════════════════════════════════════════════
# FILE CACHE
# ════════════════════════════════════════════════════════════════════════
async def get_file_entry(path: str) -> Optional[Dict[str, Any]]:
    if _DB is None:
        return None
    try:
        return await _DB.autocoder_file_cache.find_one({"path": path}, {"_id": 0})
    except Exception:
        return None


async def check_file_cache(path: str) -> Dict[str, Any]:
    """Return cache state for a file. Does NOT bump stats."""
    if _DB is None:
        return {"cached": False, "reason": "no_db"}
    current_sha = _file_sha256(path)
    if not current_sha:
        return {"cached": False, "reason": "file_missing"}
    entry = await get_file_entry(path)
    if not entry:
        return {"cached": False, "reason": "no_entry", "current_sha256": current_sha}
    same = entry.get("sha256") == current_sha
    return {
        "cached": same,
        "reason": "unchanged" if same else "changed",
        "current_sha256": current_sha,
        "cached_sha256": entry.get("sha256"),
        "summary": entry.get("summary") if same else None,
        "total_lines": entry.get("total_lines") if same else None,
        "size": entry.get("size") if same else None,
        "updated_at": entry.get("updated_at"),
        "hit_count": entry.get("hit_count", 0),
        "structure": entry.get("structure") if same else None,
    }


async def upsert_file_entry(path: str, *, summary: str = "", structure: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if _DB is None:
        return {"ok": False, "error": "no_db"}
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {"ok": False, "error": "file_not_found"}
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"ok": False, "error": f"read_failed: {e}"}
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    total_lines = text.count("\n") + 1
    size = len(text)
    doc = {
        "path": str(path),
        "sha256": sha,
        "total_lines": total_lines,
        "size": size,
        "summary": (summary or "")[:FILE_CACHE_MAX_SUMMARY_CHARS],
        "structure": structure or {},
        "updated_at": _now(),
    }
    try:
        await _DB.autocoder_file_cache.update_one(
            {"path": str(path)},
            {"$set": doc, "$setOnInsert": {"created_at": _now(), "hit_count": 0}},
            upsert=True,
        )
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "path": str(path), "sha256": sha, "summary_len": len(doc["summary"])}


async def record_file_hit(path: str, tokens_saved: int) -> None:
    if _DB is None:
        return
    try:
        await _DB.autocoder_file_cache.update_one(
            {"path": path},
            {"$inc": {"hit_count": 1, "tokens_saved": tokens_saved}, "$set": {"last_hit_at": _now()}},
        )
    except Exception:
        pass


async def invalidate_file(path: str) -> Dict[str, Any]:
    if _DB is None:
        return {"ok": False, "error": "no_db"}
    try:
        res = await _DB.autocoder_file_cache.delete_one({"path": path})
        return {"ok": True, "deleted": res.deleted_count}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ════════════════════════════════════════════════════════════════════════
# QUERY CACHE (semantic)
# ════════════════════════════════════════════════════════════════════════
async def find_similar_query(question: str, *, top_k: int = 5) -> Optional[Dict[str, Any]]:
    """Return the most-similar cached question above the similarity threshold."""
    if _DB is None:
        return None
    nq = _norm_query(question)
    if not nq:
        return None
    # Exact-hash fast path first.
    sha = _query_sha(question)
    try:
        exact = await _DB.autocoder_query_cache.find_one({"query_sha": sha}, {"_id": 0})
        if exact:
            return {**exact, "similarity": 1.0, "match_type": "exact"}
    except Exception:
        pass
    # Semantic path
    vec = await _embed(nq)
    if not vec:
        return None
    try:
        cur = _DB.autocoder_query_cache.find(
            {"embedding": {"$exists": True}},
            {"_id": 0},
        ).sort([("updated_at", -1)]).limit(200)
        candidates = await cur.to_list(200)
    except Exception:
        return None
    best: Optional[Dict[str, Any]] = None
    best_sim = 0.0
    for c in candidates:
        sim = _cosine(vec, c.get("embedding") or [])
        if sim > best_sim:
            best_sim = sim
            best = c
    if best and best_sim >= SEMANTIC_SIMILARITY_THRESHOLD:
        return {**best, "similarity": best_sim, "match_type": "semantic"}
    return None


async def save_query_answer(
    question: str,
    answer: str,
    *,
    files_used: Optional[List[str]] = None,
    model: str = "",
) -> Dict[str, Any]:
    if _DB is None:
        return {"ok": False, "error": "no_db"}
    if not question or not answer:
        return {"ok": False, "error": "empty"}
    nq = _norm_query(question)
    sha = _query_sha(question)
    vec = await _embed(nq)
    doc = {
        "query_sha": sha,
        "query_norm": nq,
        "question": question[:4000],
        "answer": answer[:20000],
        "files_used": files_used or [],
        "model": model[:80],
        "updated_at": _now(),
        "hit_count": 0,
    }
    if vec:
        doc["embedding"] = vec
    try:
        await _DB.autocoder_query_cache.update_one(
            {"query_sha": sha},
            {"$set": doc, "$setOnInsert": {"created_at": _now()}},
            upsert=True,
        )
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "query_sha": sha, "has_embedding": bool(vec)}


async def bump_query_hit(query_sha: str) -> None:
    if _DB is None:
        return
    try:
        await _DB.autocoder_query_cache.update_one(
            {"query_sha": query_sha},
            {"$inc": {"hit_count": 1}, "$set": {"last_hit_at": _now()}},
        )
    except Exception:
        pass


async def clear_cache(*, scope: str = "all") -> Dict[str, Any]:
    """scope: 'files' | 'queries' | 'all'."""
    if _DB is None:
        return {"ok": False, "error": "no_db"}
    deleted = {"files": 0, "queries": 0, "stats_reset": False}
    try:
        if scope in ("files", "all"):
            r = await _DB.autocoder_file_cache.delete_many({})
            deleted["files"] = r.deleted_count
        if scope in ("queries", "all"):
            r = await _DB.autocoder_query_cache.delete_many({})
            deleted["queries"] = r.deleted_count
        if scope == "all":
            await _DB.autocoder_cache_stats.delete_one({"_id": "main"})
            deleted["stats_reset"] = True
        return {"ok": True, "deleted": deleted}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ════════════════════════════════════════════════════════════════════════
# Transparent integration helpers — called from tool_read_file
# ════════════════════════════════════════════════════════════════════════
async def annotate_read(path: str, content_chars: int) -> Dict[str, Any]:
    """Called every time the AI reads a file. Returns a tiny annotation
    block that we attach to the read result so the AI sees the cache state
    and learns to cache summaries. Also bumps stats."""
    if _DB is None:
        return {}
    state = await check_file_cache(path)
    if state.get("cached"):
        # Cache hit — AI already analysed this file at this sha.
        saved = _approx_tokens_saved(content_chars)
        await record_file_hit(path, saved)
        await _bump_stats(hit=True, tokens_saved=saved, layer="file")
        ann = {
            "cache": "HIT",
            "previous_summary": (state.get("summary") or "")[:400],
            "hit_count": (state.get("hit_count") or 0) + 1,
            "tokens_saved_now": saved,
            "hint": "هذا الملف لم يتغيّر منذ آخر قراءة. لا تعيد التحليل من الصفر — استعمل الملخّص أعلاه.",
        }
        return ann
    # Miss — file changed or never seen.
    await _bump_stats(hit=False, layer="file")
    return {
        "cache": "MISS",
        "reason": state.get("reason"),
        "hint": (
            "هذه أوّل قراءة (أو الملف تغيّر). بعد ما تفهم الملف، استدعِ "
            "cache_file_summary(path, summary='ملخص قصير لما تعلمته') عشان نوفّر التوكنز في القراءات القادمة."
        ),
    }


# ════════════════════════════════════════════════════════════════════════
# AI Tool wrappers
# ════════════════════════════════════════════════════════════════════════
async def tool_cache_check_file(path: str) -> Dict[str, Any]:
    """🔍 افحص هل قرأت هذا الملف سابقاً وهل ما زال على نفس النسخة."""
    state = await check_file_cache(path)
    return {"ok": True, **state}


async def tool_cache_file_summary(path: str, summary: str = "", structure: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """💾 احفظ ملخّص ما تعلمته من هذا الملف. سيُسترجع تلقائياً في كل قراءة قادمة طالما الملف لم يتغيّر."""
    return await upsert_file_entry(path, summary=summary, structure=structure)


async def tool_cache_invalidate(path: str = "", scope: str = "") -> Dict[str, Any]:
    """🧹 امسح كاش ملف معيّن (path) أو كل الكاش (scope='all'|'files'|'queries')."""
    if path:
        return await invalidate_file(path)
    if scope:
        return await clear_cache(scope=scope)
    return {"ok": False, "error": "specify path or scope"}


async def tool_cache_query_similar(question: str) -> Dict[str, Any]:
    """🧠 ابحث عن سؤال مشابه سُئل من قبل. لو وجد، استرجع الإجابة المخزّنة بدل ما تستهلك توكنز جديدة."""
    hit = await find_similar_query(question)
    if not hit:
        await _bump_stats(hit=False, layer="query")
        return {"ok": True, "found": False}
    # rough token savings: length of cached answer
    saved = _approx_tokens_saved(len(hit.get("answer") or ""))
    await _bump_stats(hit=True, tokens_saved=saved, layer="query")
    await bump_query_hit(hit.get("query_sha", ""))
    return {
        "ok": True,
        "found": True,
        "match_type": hit.get("match_type"),
        "similarity": round(hit.get("similarity", 0.0), 4),
        "question": hit.get("question"),
        "answer": hit.get("answer"),
        "files_used": hit.get("files_used", []),
        "model": hit.get("model"),
        "tokens_saved_now": saved,
    }


async def tool_cache_save_answer(question: str, answer: str, files_used: Optional[List[str]] = None, model: str = "") -> Dict[str, Any]:
    """💾 احفظ السؤال + الجواب النهائي لإعادة استخدامه لاحقاً عند تكرار طلب مشابه."""
    return await save_query_answer(question, answer, files_used=files_used or [], model=model)


async def tool_cache_stats() -> Dict[str, Any]:
    """📊 إحصائيات الكاش: ضربات، إخفاقات، توكنز موفّرة، عدد الملفات/الأسئلة المخزّنة."""
    return await get_stats()


# ════════════════════════════════════════════════════════════════════════
# Tool schemas (Anthropic format)
# ════════════════════════════════════════════════════════════════════════
CACHE_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "cache_check_file",
        "description": (
            "🔍 افحص حالة كاش ملف. لو رجع cached=true، الملف لم يتغيّر منذ آخر قراءة "
            "والملخّص متاح. **استدعها دائماً قبل read_file** لتوفير التوكنز."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "مسار الملف"}},
            "required": ["path"],
        },
    },
    {
        "name": "cache_file_summary",
        "description": (
            "💾 احفظ ملخّصاً مكتوباً من عندك لهذا الملف (وحدات، دوال رئيسية، عقد API، فخاخ). "
            "في القراءات القادمة سيعود الملخّص تلقائياً ما دام الملف لم يتغيّر."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "summary": {"type": "string", "description": "ملخّص مكثّف (200-2000 حرف). اذكر: الدور، الـAPIs، الـDB collections، أي gotchas."},
                "structure": {"type": "object", "description": "(اختياري) JSON ببنية الملف: functions/classes/imports."},
            },
            "required": ["path", "summary"],
        },
    },
    {
        "name": "cache_invalidate",
        "description": "🧹 احذف كاش ملف محدد (path) أو نطاق كامل (scope='files'|'queries'|'all').",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "scope": {"type": "string", "enum": ["files", "queries", "all", ""]},
            },
            "required": [],
        },
    },
    {
        "name": "cache_query_similar",
        "description": (
            "🧠 ابحث عن سؤال مشابه أجبت عليه سابقاً (semantic search عبر OpenAI embeddings). "
            "**استدعها قبل أي تحليل معقّد** — لو في إجابة مخزّنة على سؤال مشابه، استرجعها بدل ما تستهلك توكنز."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
        },
    },
    {
        "name": "cache_save_answer",
        "description": (
            "💾 احفظ سؤال المالك + جوابك النهائي عشان تستفيد منه في المرات القادمة. "
            "استدعها فقط بعد ما تنتهي من المهمة فعلاً (مش وسط التفكير)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "answer": {"type": "string"},
                "files_used": {"type": "array", "items": {"type": "string"}},
                "model": {"type": "string"},
            },
            "required": ["question", "answer"],
        },
    },
    {
        "name": "cache_stats",
        "description": "📊 إحصائيات الكاش: عدد ضربات الإصابة، التوكنز الموفّرة، الملفات/الأسئلة المخزّنة.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

CACHE_TOOL_HANDLERS = {
    "cache_check_file": tool_cache_check_file,
    "cache_file_summary": tool_cache_file_summary,
    "cache_invalidate": tool_cache_invalidate,
    "cache_query_similar": tool_cache_query_similar,
    "cache_save_answer": tool_cache_save_answer,
    "cache_stats": tool_cache_stats,
}

CACHE_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "cache_check_file", "desc": "check if a file is cached (unchanged)", "args": ["path"]},
    {"name": "cache_file_summary", "desc": "store a written summary of a file", "args": ["path", "summary", "structure?"]},
    {"name": "cache_invalidate", "desc": "drop a file's cache entry or all entries", "args": ["path?", "scope?"]},
    {"name": "cache_query_similar", "desc": "semantic lookup of a similar previous question", "args": ["question"]},
    {"name": "cache_save_answer", "desc": "persist a final answer for future re-use", "args": ["question", "answer", "files_used?", "model?"]},
    {"name": "cache_stats", "desc": "cache hit/miss + tokens-saved counters", "args": []},
]


def cache_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in CACHE_TOOL_HANDLERS:
        return None
    if not result.get("ok") and result.get("ok") is False:
        return f"✗ {(result.get('error') or '')[:120]}"
    if name == "cache_check_file":
        if result.get("cached"):
            return f"✓ HIT (sha {result.get('current_sha256','')[:8]}, hits {result.get('hit_count',0)})"
        return f"✗ MISS ({result.get('reason','')})"
    if name == "cache_file_summary":
        return f"💾 saved {result.get('summary_len',0)} chars"
    if name == "cache_invalidate":
        d = result.get("deleted")
        if isinstance(d, dict):
            return f"🧹 files={d.get('files',0)} queries={d.get('queries',0)}"
        return f"🧹 deleted {d}"
    if name == "cache_query_similar":
        if not result.get("found"):
            return "✗ no similar question"
        return f"✓ {result.get('match_type')} sim={result.get('similarity'):.3f} saved≈{result.get('tokens_saved_now',0)}t"
    if name == "cache_save_answer":
        return f"💾 saved (embed={result.get('has_embedding', False)})"
    if name == "cache_stats":
        fh, fm = result.get("file_hits", 0), result.get("file_misses", 0)
        qh, qm = result.get("query_hits", 0), result.get("query_misses", 0)
        return f"files {fh}/{fh+fm} · queries {qh}/{qh+qm} · saved≈{result.get('total_tokens_saved',0)}t"
    return None


def cache_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name == "cache_check_file" and result.get("cached"):
        return f"📄 {result.get('summary','')[:600]}"
    if name == "cache_query_similar" and result.get("found"):
        return f"❓ {result.get('question','')[:120]}\n💬 {result.get('answer','')[:600]}"
    if name == "cache_stats":
        return (
            f"file hits: {result.get('file_hits',0)}\n"
            f"file misses: {result.get('file_misses',0)}\n"
            f"query hits: {result.get('query_hits',0)}\n"
            f"query misses: {result.get('query_misses',0)}\n"
            f"tokens saved (approx): {result.get('total_tokens_saved',0):,}\n"
            f"files cached: {result.get('files_cached',0)}\n"
            f"queries cached: {result.get('queries_cached',0)}"
        )
    return None


CACHE_PROMPT_RULES = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 نظام الكاش الذكي — وفّر التوكنز قبل أي عملية
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 **القاعدة #1**: قبل أي `read_file` لملف كبير (>200 سطر):
   ١. استدعِ `cache_check_file(path)` أولاً.
   ٢. لو رجع `cached=true` → الـ`summary` و `structure` متاحين، اكتفِ بهم
      ولا تقرأ الملف كاملاً. الـTOC هذا يكفي لـ80% من المهام.
   ٣. لو احتجت تفاصيل أعمق فقط، اقرأ النطاق المحدد (start/end).

🔥 **القاعدة #2**: بعد ما تفهم ملف لأول مرة، احفظ ملخّصك:
   → `cache_file_summary(path, summary='...')`
   الملخّص لازم يحتوي:
     • الدور الرئيسي للملف (سطر واحد)
     • الـAPIs/الدوال الرئيسية وأرقام أسطرها
     • الـDB collections المستخدمة
     • أي gotchas أو bugs معروفة

🔥 **القاعدة #3**: قبل تحليل طلب جديد للمالك، استدعِ:
   → `cache_query_similar(question='...')` 
   لو في إجابة محفوظة مع `similarity ≥ 0.92`، استخدمها فوراً
   (طبعاً عدّلها لو السياق تغيّر).

🔥 **القاعدة #4**: لما تنتهي من مهمة كبيرة بنجاح، احفظ المعرفة:
   → `cache_save_answer(question, answer, files_used=[...])`
   هذا يحوّل المحادثة لمكتبة معرفة دائمة، ويوفّر آلاف التوكنز
   في المرات القادمة.

⚡ **القاعدة الذهبية**: لكل ملف توفّر إعادة قراءته ≈ 3,000 توكن.
   لكل سؤال معقد توفّره ≈ 5,000-15,000 توكن. الكاش رخيص جداً
   (embeddings = $0.02/M) — استخدمه قبل أي عملية ثقيلة.

📊 ادعِ `cache_stats()` كل فترة عشان تشوف كم وفّرت.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
