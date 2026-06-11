"""
Code Index — One-time scan of the codebase that the AI queries instead of
re-reading files.

The AI's biggest token waste was calling list_dir → read_file → grep → read_file
repeatedly. With this index, a single `code_lookup("voice recording")` returns:

  • Files matching that feature
  • Functions inside each file (with line numbers)
  • Relevant snippet (~20 lines around the match)
  • API endpoints called
  • Imports

That's usually all the AI needs. read_file is then only called for the
actual edit operation, not for exploration.

Index is built once per process and cached to disk (with mtime checks for
auto-invalidation). Survives restarts.
"""
from __future__ import annotations
import os
import re
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path("/app")
INDEX_FILE = Path("/tmp/zenrex_code_index.json")

# Only index source files
INDEXED_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "build", "dist", ".next",
             "venv", ".venv", "coverage", ".cache", "static_uploads"}
SKIP_FILES_OVER_BYTES = 200_000   # 200KB — anything bigger is likely generated

# Pre-compiled regex
_PY_DEF = re.compile(r"^\s*(?:async\s+)?def\s+([a-zA-Z_]\w*)\s*\(", re.MULTILINE)
_PY_CLASS = re.compile(r"^\s*class\s+([a-zA-Z_]\w*)", re.MULTILINE)
_PY_IMPORT = re.compile(r"^\s*(?:from\s+(\S+)\s+import|import\s+(\S+))", re.MULTILINE)

_JS_FUNC = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function|const|let)\s+([a-zA-Z_][\w]*)\s*[=(:]",
    re.MULTILINE,
)
_JS_CLASS = re.compile(r"^\s*(?:export\s+)?class\s+([a-zA-Z_]\w*)", re.MULTILINE)
_JS_EXPORT_DEFAULT = re.compile(
    r"^\s*export\s+default\s+(?:function\s+)?([a-zA-Z_]\w*)", re.MULTILINE
)
_JS_IMPORT = re.compile(r"^\s*import\s+(?:.+?\s+from\s+)?['\"]([^'\"]+)['\"]", re.MULTILINE)
_API_CALL = re.compile(r"['\"`](/api/[^\s'\"`?#]+)")
_FASTAPI_ROUTE = re.compile(r'@(?:router|app)\.(get|post|put|delete|patch)\(["\'](/[^"\']+)["\']')


def _extract_py(text: str) -> Dict[str, Any]:
    funcs: List[Dict[str, Any]] = []
    for m in _PY_DEF.finditer(text):
        line_no = text[: m.start()].count("\n") + 1
        funcs.append({"name": m.group(1), "line": line_no, "kind": "def"})
    classes: List[Dict[str, Any]] = []
    for m in _PY_CLASS.finditer(text):
        line_no = text[: m.start()].count("\n") + 1
        classes.append({"name": m.group(1), "line": line_no})
    imports = list({(m.group(1) or m.group(2)).split(".")[0] for m in _PY_IMPORT.finditer(text)})
    routes: List[Dict[str, Any]] = []
    for m in _FASTAPI_ROUTE.finditer(text):
        line_no = text[: m.start()].count("\n") + 1
        routes.append({"method": m.group(1).upper(), "path": m.group(2), "line": line_no})
    api_calls = list({m.group(1) for m in _API_CALL.finditer(text)})
    return {"functions": funcs, "classes": classes, "imports": imports[:30],
            "routes": routes, "api_calls": api_calls[:20]}


def _extract_js(text: str) -> Dict[str, Any]:
    funcs: List[Dict[str, Any]] = []
    seen = set()
    for m in _JS_EXPORT_DEFAULT.finditer(text):
        line_no = text[: m.start()].count("\n") + 1
        n = m.group(1)
        if n not in seen:
            funcs.append({"name": n, "line": line_no, "kind": "export_default"})
            seen.add(n)
    for m in _JS_FUNC.finditer(text):
        line_no = text[: m.start()].count("\n") + 1
        n = m.group(1)
        if n not in seen and len(n) > 1:
            funcs.append({"name": n, "line": line_no, "kind": "func"})
            seen.add(n)
    classes: List[Dict[str, Any]] = []
    for m in _JS_CLASS.finditer(text):
        line_no = text[: m.start()].count("\n") + 1
        classes.append({"name": m.group(1), "line": line_no})
    imports = list({m.group(1) for m in _JS_IMPORT.finditer(text)})
    api_calls = list({m.group(1) for m in _API_CALL.finditer(text)})
    return {"functions": funcs[:40], "classes": classes, "imports": imports[:30],
            "routes": [], "api_calls": api_calls[:20]}


def _summarize_file(rel_path: str, text: str) -> str:
    """One-line summary — extract first meaningful comment / docstring."""
    lines = text.split("\n")[:30]
    # Python docstring
    if rel_path.endswith(".py"):
        for i, ln in enumerate(lines):
            s = ln.strip()
            if s.startswith('"""') or s.startswith("'''"):
                inner = s.strip('"\'')
                if inner:
                    return inner[:120]
                # try next non-empty line
                for nxt in lines[i + 1: i + 3]:
                    if nxt.strip():
                        return nxt.strip()[:120]
                break
    # JS top comment
    for ln in lines:
        s = ln.strip()
        if s.startswith("//"):
            return s[2:].strip()[:120]
        if s.startswith("/*"):
            inner = s.lstrip("/*").rstrip("*/").strip()
            if inner:
                return inner[:120]
    return ""


def _scan_one_file(abs_path: Path) -> Optional[Dict[str, Any]]:
    try:
        size = abs_path.stat().st_size
        if size > SKIP_FILES_OVER_BYTES:
            return None
        text = abs_path.read_text(encoding="utf-8", errors="replace")
        rel = str(abs_path.relative_to(REPO_ROOT))
        ext = abs_path.suffix
        if ext == ".py":
            meta = _extract_py(text)
        else:
            meta = _extract_js(text)
        return {
            "path": rel,
            "size": size,
            "lines": text.count("\n") + 1,
            "mtime": int(abs_path.stat().st_mtime),
            "summary": _summarize_file(rel, text),
            **meta,
        }
    except Exception as e:
        logger.debug(f"index skip {abs_path}: {e}")
        return None


def _walk_repo() -> List[Path]:
    out: List[Path] = []
    for root, dirs, files in os.walk(REPO_ROOT):
        # Filter out skip dirs in-place
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            ext = "." + f.rsplit(".", 1)[-1] if "." in f else ""
            if ext in INDEXED_EXTENSIONS:
                out.append(Path(root) / f)
    return out


# ════════════════════════════════════════════════════════════════════════
# Build / load
# ════════════════════════════════════════════════════════════════════════
_INDEX_CACHE: Optional[Dict[str, Any]] = None
_INDEX_LOCK = asyncio.Lock()


def _build_index_sync() -> Dict[str, Any]:
    started = time.time()
    paths = _walk_repo()
    files: Dict[str, Any] = {}
    by_function: Dict[str, List[str]] = {}
    by_api: Dict[str, List[str]] = {}
    by_route: Dict[str, List[str]] = {}
    for p in paths:
        meta = _scan_one_file(p)
        if not meta:
            continue
        rel = meta["path"]
        files[rel] = meta
        for f in meta.get("functions", []):
            by_function.setdefault(f["name"], []).append(rel)
        for c in meta.get("classes", []):
            by_function.setdefault(c["name"], []).append(rel)
        for a in meta.get("api_calls", []):
            by_api.setdefault(a, []).append(rel)
        for r in meta.get("routes", []):
            by_route.setdefault(r["path"], []).append(rel)
    elapsed = time.time() - started
    return {
        "files": files,
        "by_function": by_function,
        "by_api": by_api,
        "by_route": by_route,
        "total_files": len(files),
        "generated_at": int(time.time()),
        "build_seconds": round(elapsed, 2),
        "version": 1,
    }


def _save_index(index: Dict[str, Any]) -> None:
    try:
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = INDEX_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
        tmp.replace(INDEX_FILE)
    except Exception as e:
        logger.warning(f"save index failed: {e}")


def _load_index_from_disk() -> Optional[Dict[str, Any]]:
    if not INDEX_FILE.exists():
        return None
    try:
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        # Quick freshness check — if more than 30% of files are stale, rebuild
        if data.get("version") != 1:
            return None
        return data
    except Exception:
        return None


def get_index(force_rebuild: bool = False) -> Dict[str, Any]:
    global _INDEX_CACHE
    if _INDEX_CACHE is not None and not force_rebuild:
        return _INDEX_CACHE
    if not force_rebuild:
        disk = _load_index_from_disk()
        if disk:
            _INDEX_CACHE = disk
            return _INDEX_CACHE
    _INDEX_CACHE = _build_index_sync()
    _save_index(_INDEX_CACHE)
    return _INDEX_CACHE


# ════════════════════════════════════════════════════════════════════════
# Lookup API — the AI's main tool
# ════════════════════════════════════════════════════════════════════════
def _score_file(rel: str, meta: Dict[str, Any], q: str) -> int:
    q = q.lower().strip()
    if not q:
        return 0
    score = 0
    # Path match (strongest signal)
    if q in rel.lower():
        score += 50
    if q in (meta.get("summary") or "").lower():
        score += 30
    for fn in meta.get("functions", []):
        if q in fn["name"].lower():
            score += 25
            if q == fn["name"].lower():
                score += 50
    for c in meta.get("classes", []):
        if q in c["name"].lower():
            score += 20
    for a in meta.get("api_calls", []):
        if q in a.lower():
            score += 15
    for r in meta.get("routes", []):
        if q in r["path"].lower():
            score += 20
    return score


def lookup(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Fuzzy search the index — returns up to `limit` matching files with
    their relevant functions/routes pre-extracted."""
    idx = get_index()
    if not query:
        return []
    q = query.lower().strip()
    # Exact function match shortcut
    exact = idx["by_function"].get(query) or idx["by_function"].get(query.title())
    candidates: Dict[str, int] = {}
    if exact:
        for rel in exact:
            candidates[rel] = candidates.get(rel, 0) + 100
    for rel, meta in idx["files"].items():
        s = _score_file(rel, meta, q)
        if s > 0:
            candidates[rel] = max(candidates.get(rel, 0), s)
    ranked = sorted(candidates.items(), key=lambda x: -x[1])[:limit]
    out: List[Dict[str, Any]] = []
    for rel, score in ranked:
        meta = idx["files"][rel]
        matching_fns = [f for f in meta.get("functions", []) if q in f["name"].lower()][:5]
        matching_routes = [r for r in meta.get("routes", []) if q in r["path"].lower()][:5]
        out.append({
            "path": rel,
            "lines": meta.get("lines"),
            "summary": meta.get("summary"),
            "score": score,
            "match_functions": matching_fns or meta.get("functions", [])[:3],
            "match_routes": matching_routes or meta.get("routes", [])[:3],
            "api_calls": meta.get("api_calls", [])[:5],
            "imports_hint": meta.get("imports", [])[:8],
        })
    return out


def file_summary(path: str) -> Optional[Dict[str, Any]]:
    """Get the full indexed summary of one file (cheap — no disk read)."""
    idx = get_index()
    # Normalize relative path
    norm = path
    if norm.startswith("/app/"):
        norm = norm[len("/app/"):]
    norm = norm.lstrip("/")
    return idx["files"].get(norm)


def search_api(api_path: str) -> List[Dict[str, Any]]:
    """Find all files calling a specific API endpoint."""
    idx = get_index()
    result = []
    api_lower = api_path.lower()
    for api, files in idx["by_api"].items():
        if api_lower in api.lower():
            for f in files:
                result.append({"file": f, "matched_api": api})
    return result[:20]


def stats() -> Dict[str, Any]:
    idx = get_index()
    return {
        "total_files": idx["total_files"],
        "generated_at": idx["generated_at"],
        "build_seconds": idx.get("build_seconds"),
        "age_seconds": int(time.time()) - idx["generated_at"],
        "functions_indexed": len(idx["by_function"]),
        "api_endpoints_indexed": len(idx["by_api"]),
        "routes_indexed": len(idx["by_route"]),
    }


# ════════════════════════════════════════════════════════════════════════
# AI-callable tool wrappers
# ════════════════════════════════════════════════════════════════════════
async def tool_code_lookup(query: str, limit: int = 8) -> Dict[str, Any]:
    """Search the indexed codebase. Use BEFORE list_dir / read_file."""
    if not query:
        return {"ok": False, "error": "query required"}
    matches = lookup(query, limit=limit)
    if not matches:
        return {"ok": True, "query": query, "matches": [],
                "hint": "ما لقيت — جرّب كلمات تانية (function name, API path, feature)"}
    return {"ok": True, "query": query, "count": len(matches), "matches": matches}


async def tool_code_summary(path: str) -> Dict[str, Any]:
    """Full structured summary of one file (functions/routes/imports) — no
    disk read. Use to avoid read_file when you only need to know what's inside."""
    if not path:
        return {"ok": False, "error": "path required"}
    s = file_summary(path)
    if not s:
        return {"ok": False, "error": f"not indexed: {path}",
                "hint": "ممكن الملف خارج /app/backend|frontend — استخدم read_file"}
    return {"ok": True, "summary": s}


async def tool_code_index_stats() -> Dict[str, Any]:
    """Show index health — total files, age, function count."""
    return {"ok": True, "stats": stats()}


async def tool_code_index_refresh() -> Dict[str, Any]:
    """Force rebuild the index from disk. Use after big refactors."""
    async with _INDEX_LOCK:
        started = time.time()
        get_index(force_rebuild=True)
        elapsed = time.time() - started
    return {"ok": True, "rebuilt": True, "took_seconds": round(elapsed, 2), "stats": stats()}


async def tool_code_find_api(api_path: str) -> Dict[str, Any]:
    """Find every file that calls a given API endpoint (e.g. '/api/wizard/image')."""
    if not api_path:
        return {"ok": False, "error": "api_path required"}
    return {"ok": True, "api_path": api_path, "matches": search_api(api_path)}


# ════════════════════════════════════════════════════════════════════════
# Anthropic schemas
# ════════════════════════════════════════════════════════════════════════
INDEX_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "code_lookup",
        "description": ("Search the indexed codebase for a feature/function/keyword. "
                       "**استخدمها قبل list_dir/read_file/grep**. ترجع ملفات + دوال + أرقام أسطر دفعة وحدة. "
                       "أمثلة: code_lookup('voice'), code_lookup('handleGenerate'), code_lookup('/api/wizard/image')."),
        "input_schema": {"type": "object", "properties": {
            "query": {"type": "string", "description": "اسم ميزة/دالة/API path"},
            "limit": {"type": "integer", "description": "default 8"},
        }, "required": ["query"]},
    },
    {
        "name": "code_summary",
        "description": ("Get the structured summary of one file (functions/routes/imports/api_calls) "
                       "WITHOUT reading it. أرخص بكثير من read_file. استخدمها لمعرفة بنية الملف قبل ما تعدّل."),
        "input_schema": {"type": "object", "properties": {
            "path": {"type": "string", "description": "نسبي أو مطلق"},
        }, "required": ["path"]},
    },
    {
        "name": "code_find_api",
        "description": "اعثر على كل الملفات اللي تستدعي endpoint محدد (مثلاً '/api/agent/chat').",
        "input_schema": {"type": "object", "properties": {
            "api_path": {"type": "string"},
        }, "required": ["api_path"]},
    },
    {
        "name": "code_index_stats",
        "description": "إحصائيات الـindex (عدد الملفات، وقت آخر بناء).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "code_index_refresh",
        "description": "أعد بناء الـindex بعد تعديلات كبيرة. عادة ما تحتاجها (التحديث تلقائي).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

INDEX_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "code_lookup", "desc": "fuzzy search indexed codebase", "args": ["query", "limit?"]},
    {"name": "code_summary", "desc": "full file summary w/o reading", "args": ["path"]},
    {"name": "code_find_api", "desc": "find files calling an API endpoint", "args": ["api_path"]},
    {"name": "code_index_stats", "desc": "index health", "args": []},
    {"name": "code_index_refresh", "desc": "force rebuild index", "args": []},
]

INDEX_TOOL_HANDLERS = {
    "code_lookup": tool_code_lookup,
    "code_summary": tool_code_summary,
    "code_find_api": tool_code_find_api,
    "code_index_stats": tool_code_index_stats,
    "code_index_refresh": tool_code_index_refresh,
}


def index_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in INDEX_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return f"✗ {(result.get('error') or '')[:120]}"
    if name == "code_lookup":
        c = result.get("count", 0)
        return f"{c} ملف مطابق" if c else "ما لقيت — جرّب كلمة أخرى"
    if name == "code_summary":
        s = result.get("summary", {})
        return f"{s.get('lines','?')} سطر · {len(s.get('functions',[]))} دالة · {len(s.get('routes',[]))} route"
    if name == "code_find_api":
        return f"{len(result.get('matches',[]))} ملف يستدعي {result.get('api_path')}"
    if name == "code_index_stats":
        st = result.get("stats", {})
        return f"{st.get('total_files')} ملف · {st.get('functions_indexed')} دالة · عمر {st.get('age_seconds',0)}s"
    if name == "code_index_refresh":
        return f"rebuilt in {result.get('took_seconds')}s"
    return None


def index_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name == "code_lookup":
        out = []
        for m in result.get("matches", [])[:6]:
            out.append(f"📄 {m['path']} ({m.get('lines','?')} سطر)")
            if m.get("summary"):
                out.append(f"   📝 {m['summary'][:80]}")
            for fn in m.get("match_functions", [])[:3]:
                out.append(f"   • {fn['name']} @ line {fn['line']}")
            for rt in m.get("match_routes", [])[:3]:
                out.append(f"   • {rt['method']} {rt['path']} @ line {rt['line']}")
        return "\n".join(out)
    if name == "code_summary":
        s = result.get("summary", {})
        out = [f"📄 {s.get('path')} ({s.get('lines','?')} سطر, {s.get('size','?')}B)"]
        if s.get("summary"):
            out.append(f"📝 {s['summary']}")
        for fn in s.get("functions", [])[:10]:
            out.append(f"  • {fn['name']} @ line {fn['line']}")
        for rt in s.get("routes", [])[:5]:
            out.append(f"  • {rt['method']} {rt['path']} @ line {rt['line']}")
        if s.get("api_calls"):
            out.append(f"  🔌 APIs: {', '.join(s['api_calls'][:5])}")
        return "\n".join(out)
    if name == "code_find_api":
        return "\n".join(f"  📄 {m['file']}" for m in result.get("matches", [])[:10])
    if name == "code_index_stats":
        return json.dumps(result.get("stats", {}), ensure_ascii=False, indent=2)
    return None


INDEX_PROMPT_RULES = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 قاعدة الـINDEX — استكشاف رخيص بدل read_file مكلف
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

تم بناء **index كامل** لكل ملفات /app (frontend + backend) عند تشغيل النظام.
الـindex يحفظ لكل ملف: الدوال، الـclasses، أرقام الأسطر، الـimports، الـAPI calls، الـroutes.

🎯 قبل ما تستدعي `list_dir` أو `read_file`، استخدم **code_lookup** أولاً:

  • code_lookup("voice recording")        → ملفات تسجيل الصوت + الدوال + الأسطر
  • code_lookup("handleSubmit")           → كل ملف فيه دالة بهذا الاسم
  • code_lookup("/api/wizard/image")      → ملفات تستدعي هذا الـAPI
  • code_lookup("AdminAutoCoder")         → الصفحة + الدوال داخلها

📊 توفير حقيقي:
  - بدون index: list_dir → read_file × 5 = ~3,500 tokens
  - مع index:   code_lookup × 1         = ~400 tokens (يعطيك أرقام الأسطر مباشرة)

🔁 **سير العمل الجديد** (التزم به):
  1. code_lookup(query)                    — وين الميزة؟
  2. code_summary(path)                    — وش فيها بدون قراءة كاملة؟
  3. read_file(path, start=N-5, end=N+30)  — اقرأ السطر المحدد بس
  4. edit_file(path, find, replace)        — عدّل بدقة

⚠️ بعد أي `write_file` أو `apply_patch` كبير، استدعِ `code_index_refresh` (ثوانٍ).
"""
