"""
Extra power tools for the Auto-Coder so the AI has FULL capability.

Adds:
  • web_search       — free DuckDuckGo HTML search (no key required)
  • fetch_url        — fetch any HTTP URL and return text
  • view_bulk_files  — read multiple files in one call (efficient)
  • apply_patch      — apply unified-diff to multiple files (atomic)
  • db_query         — read-only MongoDB query (inspect production data)
  • ast_analyze      — Python AST: list functions/classes/imports

These are imported and registered by autocoder/__init__.py.
"""
from __future__ import annotations
import os
import re
import ast
import html
import json
import shlex
import asyncio
import logging
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

REPO_ROOT = Path("/app")


def _resolve_path(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = REPO_ROOT / p
    return p.resolve()


def _strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


# ─────────────────────────────────────────────────────────────────────
# 🔎 web_search — DuckDuckGo HTML (free, no API key)
# ─────────────────────────────────────────────────────────────────────
async def tool_web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    if not query.strip():
        return {"ok": False, "error": "empty query"}
    max_results = max(1, min(int(max_results or 5), 10))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    }
    # Try DDG HTML POST first (bot-friendlier than GET)
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r = await c.post(
                "https://html.duckduckgo.com/html/",
                headers=headers,
                data={"q": query, "kl": "wt-wt"},
            )
        if r.status_code != 200:
            # Fallback: lite endpoint (very simple HTML)
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
                r = await c.get(
                    f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}",
                    headers=headers,
                )
        if r.status_code != 200:
            return {"ok": False, "error": f"ddg returned {r.status_code}"}

        text = r.text
        results: List[Dict[str, str]] = []

        # Pattern 1: full DDG html result blocks
        pattern_full = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>'
            r'.*?(?:<a[^>]+class="result__snippet"[^>]*>(?P<snippet>.*?)</a>|$)',
            re.DOTALL,
        )
        for m in pattern_full.finditer(text):
            raw_url = m.group("url") or ""
            if raw_url.startswith("/l/") or raw_url.startswith("//duckduckgo.com/l/"):
                qs = urllib.parse.urlparse(raw_url).query
                params = urllib.parse.parse_qs(qs)
                raw_url = (params.get("uddg") or params.get("u") or [raw_url])[0]
            results.append({
                "url": raw_url,
                "title": _strip_html(m.group("title") or "")[:200],
                "snippet": _strip_html(m.group("snippet") or "")[:400],
            })
            if len(results) >= max_results:
                break

        # Pattern 2: lite endpoint — different markup (simple <a class="result-link">)
        if not results:
            pattern_lite = re.compile(
                r'<a[^>]+(?:class="result-link"|rel="nofollow")[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>',
                re.DOTALL | re.IGNORECASE,
            )
            for m in pattern_lite.finditer(text):
                raw_url = m.group("url") or ""
                if raw_url.startswith("//"):
                    raw_url = "https:" + raw_url
                if not raw_url.startswith("http"):
                    continue
                results.append({
                    "url": raw_url,
                    "title": _strip_html(m.group("title") or "")[:200],
                    "snippet": "",
                })
                if len(results) >= max_results:
                    break

        if not results:
            return {"ok": False, "error": "no results parsed (DDG layout may have changed)",
                    "html_preview": text[:500]}

        return {
            "ok": True,
            "query": query,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


# ─────────────────────────────────────────────────────────────────────
# 🌐 fetch_url — pull any URL as text (for docs, GitHub READMEs, errors)
# ─────────────────────────────────────────────────────────────────────
async def tool_fetch_url(url: str, max_chars: int = 8000) -> Dict[str, Any]:
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "url must start with http(s)://"}
    max_chars = max(500, min(int(max_chars or 8000), 30000))
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as c:
            r = await c.get(url, headers={
                "User-Agent": "Mozilla/5.0 ZitexBot/1.0",
                "Accept": "text/html,text/plain,application/json,*/*",
            })
        ctype = r.headers.get("content-type", "").split(";")[0].strip()
        text = r.text or ""
        # Strip HTML if html
        if "html" in ctype.lower():
            # remove <script> and <style>
            text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = _strip_html(text)
        return {
            "ok": r.status_code == 200,
            "status": r.status_code,
            "content_type": ctype,
            "url": str(r.url),
            "length": len(text),
            "content": text[:max_chars],
            "truncated": len(text) > max_chars,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


# ─────────────────────────────────────────────────────────────────────
# 📚 view_bulk_files — read up to 6 files in one call
# ─────────────────────────────────────────────────────────────────────
async def tool_view_bulk_files(paths: List[str], max_lines_per_file: int = 400) -> Dict[str, Any]:
    if not paths:
        return {"ok": False, "error": "paths is empty"}
    paths = paths[:6]  # cap
    max_lines_per_file = max(50, min(int(max_lines_per_file or 400), 1500))
    out: List[Dict[str, Any]] = []
    for raw in paths:
        try:
            p = _resolve_path(raw)
            if not p.exists() or not p.is_file():
                out.append({"path": str(p), "ok": False, "error": "not a file"})
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            shown = min(max_lines_per_file, len(lines))
            out.append({
                "path": str(p),
                "ok": True,
                "total_lines": len(lines),
                "shown": shown,
                "content": "\n".join(lines[:shown])[:30000],
                "truncated": shown < len(lines),
            })
        except Exception as e:
            out.append({"path": raw, "ok": False, "error": str(e)[:200]})
    return {"ok": True, "files": out, "count": len(out)}


# ─────────────────────────────────────────────────────────────────────
# 🩹 apply_patch — apply a unified diff (multi-file, atomic)
# Uses GNU patch (available on Linux containers).
# ─────────────────────────────────────────────────────────────────────
async def tool_apply_patch(patch: str, strip: int = 0, dry_run: bool = False) -> Dict[str, Any]:
    if not patch or not patch.strip():
        return {"ok": False, "error": "empty patch"}
    strip = max(0, min(int(strip or 0), 5))
    try:
        # Write to temp file
        import tempfile
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False)
        tmp.write(patch)
        tmp.close()

        flags = f"-p{strip}"
        if dry_run:
            flags += " --dry-run"

        cmd = (
            f"cd {shlex.quote(str(REPO_ROOT))} && "
            f"patch {flags} -i {shlex.quote(tmp.name)} 2>&1"
        )
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=60)
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

        out_s = (out or b"").decode("utf-8", errors="replace")
        err_s = (err or b"").decode("utf-8", errors="replace")
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": out_s[:6000],
            "stderr": err_s[:3000],
            "dry_run": dry_run,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


# ─────────────────────────────────────────────────────────────────────
# 🗄️ db_query — read-only MongoDB query (inspect production data)
# Restricted to find/count/distinct (no insert/update/delete).
# ─────────────────────────────────────────────────────────────────────
def make_db_query_tool(db):
    """Factory that binds the MongoDB instance."""
    async def tool_db_query(
        collection: str,
        filter: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        operation: str = "find",
    ) -> Dict[str, Any]:
        if db is None:
            return {"ok": False, "error": "db not bound"}
        if not collection or not isinstance(collection, str):
            return {"ok": False, "error": "collection name required"}
        if operation not in ("find", "count", "distinct", "find_one"):
            return {"ok": False, "error": "operation must be: find|find_one|count|distinct"}
        limit = max(1, min(int(limit or 20), 100))
        filter = filter or {}
        # Default projection: hide _id (BSON not JSON-friendly)
        proj = projection or {"_id": 0}
        try:
            coll = db[collection]
            if operation == "find":
                cur = coll.find(filter, proj).limit(limit)
                docs = []
                async for d in cur:
                    # Convert remaining ObjectIds / datetimes to str
                    docs.append(_jsonify(d))
                return {"ok": True, "operation": "find", "collection": collection,
                        "count": len(docs), "results": docs}
            if operation == "find_one":
                d = await coll.find_one(filter, proj)
                return {"ok": True, "operation": "find_one", "collection": collection,
                        "result": _jsonify(d) if d else None}
            if operation == "count":
                n = await coll.count_documents(filter)
                return {"ok": True, "operation": "count", "collection": collection, "count": n}
            if operation == "distinct":
                field = (projection or {}).get("field") if projection else None
                if not field:
                    return {"ok": False, "error": "for distinct, pass projection={'field': '<fieldname>'}"}
                values = await coll.distinct(field, filter)
                return {"ok": True, "operation": "distinct", "collection": collection,
                        "field": field, "values": values[:limit]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}
        return {"ok": False, "error": "unreachable"}

    return tool_db_query


def _jsonify(d: Any) -> Any:
    """Recursively make a dict JSON-safe (ObjectId → str, datetime → iso)."""
    if d is None:
        return None
    if isinstance(d, dict):
        out = {}
        for k, v in d.items():
            if k == "_id":
                continue  # always drop
            out[k] = _jsonify(v)
        return out
    if isinstance(d, list):
        return [_jsonify(x) for x in d]
    # ObjectId / datetime → str
    cls = type(d).__name__
    if cls in ("ObjectId", "datetime", "Datetime"):
        return str(d)
    if isinstance(d, (str, int, float, bool)):
        return d
    try:
        return str(d)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────
# 🧬 ast_analyze — extract functions/classes/imports/calls from a Python file
# ─────────────────────────────────────────────────────────────────────
async def tool_ast_analyze(path: str) -> Dict[str, Any]:
    try:
        p = _resolve_path(path)
        if not p.exists() or not p.is_file():
            return {"ok": False, "error": "file not found"}
        if not p.suffix == ".py":
            return {"ok": False, "error": "ast_analyze only works on .py files"}
        source = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(p))

        functions: List[Dict[str, Any]] = []
        classes: List[Dict[str, Any]] = []
        imports: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [a.arg for a in node.args.args],
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "decorators": [_node_name(d) for d in node.decorator_list][:5],
                })
            elif isinstance(node, ast.ClassDef):
                methods = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "bases": [_node_name(b) for b in node.bases][:5],
                    "methods": methods[:30],
                })
            elif isinstance(node, ast.Import):
                for n in node.names:
                    imports.append(n.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for n in node.names:
                    imports.append(f"{mod}.{n.name}" if mod else n.name)

        return {
            "ok": True,
            "path": str(p),
            "lines": len(source.splitlines()),
            "functions": functions[:80],
            "classes": classes[:30],
            "imports": list(dict.fromkeys(imports))[:60],  # dedup, preserve order
        }
    except SyntaxError as e:
        return {"ok": False, "error": f"SyntaxError: {e.msg} at line {e.lineno}"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


def _node_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        try:
            return f"{_node_name(node.value)}.{node.attr}"
        except Exception:
            return node.attr
    if isinstance(node, ast.Call):
        return _node_name(node.func)
    return type(node).__name__


# ─────────────────────────────────────────────────────────────────────
# Anthropic-format tool schemas for the new tools
# ─────────────────────────────────────────────────────────────────────
EXTRA_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "web_search",
        "description": "Search the public web (DuckDuckGo, no key required). Use for: looking up error messages, finding API documentation, checking current best practices, researching libraries. Returns top results with title + snippet + URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "search query"},
                "max_results": {"type": "integer", "description": "1-10, default 5"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_url",
        "description": "Fetch any HTTP(S) URL and return its text content (HTML stripped). Use after web_search to read the actual page (docs, GitHub READMEs, error pages, JSON APIs).",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "max_chars": {"type": "integer", "description": "500-30000, default 8000"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "view_bulk_files",
        "description": "Read up to 6 files at once — much more efficient than calling read_file repeatedly. Use when you need to compare files or understand a feature spanning multiple modules.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {"type": "array", "items": {"type": "string"}, "description": "list of file paths (max 6)"},
                "max_lines_per_file": {"type": "integer", "description": "default 400"},
            },
            "required": ["paths"],
        },
    },
    {
        "name": "apply_patch",
        "description": "Apply a unified-diff patch to one or many files atomically using GNU `patch`. Use this for multi-file refactors instead of multiple edit_file calls. Test first with dry_run=true.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patch": {"type": "string", "description": "unified diff text (---/+++ headers + @@ hunks)"},
                "strip": {"type": "integer", "description": "patch -p N, default 0"},
                "dry_run": {"type": "boolean", "description": "preview without writing"},
            },
            "required": ["patch"],
        },
    },
    {
        "name": "db_query",
        "description": "Run a READ-ONLY MongoDB query against the live production database. Operations: find, find_one, count, distinct. Inspect users, conversations, audit logs, etc. Never modifies data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {"type": "string", "description": "e.g. 'users', 'autocoder_audit'"},
                "filter": {"type": "object", "description": "Mongo filter, default {}"},
                "projection": {"type": "object", "description": "Mongo projection. For distinct, use {'field': '<name>'}"},
                "limit": {"type": "integer", "description": "1-100, default 20"},
                "operation": {"type": "string", "enum": ["find", "find_one", "count", "distinct"]},
            },
            "required": ["collection"],
        },
    },
    {
        "name": "ast_analyze",
        "description": "Parse a Python file's AST to extract: all functions (with args + line numbers), classes (with methods), and imports. Faster than read_file for understanding structure.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
]


EXTRA_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "web_search", "desc": "free DuckDuckGo web search", "args": ["query", "max_results?"]},
    {"name": "fetch_url", "desc": "fetch URL as text", "args": ["url", "max_chars?"]},
    {"name": "view_bulk_files", "desc": "read up to 6 files at once", "args": ["paths", "max_lines_per_file?"]},
    {"name": "apply_patch", "desc": "apply unified diff (multi-file)", "args": ["patch", "strip?", "dry_run?"]},
    {"name": "db_query", "desc": "read-only Mongo query", "args": ["collection", "filter?", "projection?", "limit?", "operation?"]},
    {"name": "ast_analyze", "desc": "Python AST: functions/classes/imports", "args": ["path"]},
]


def extra_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    """Return a one-line summary for new tools, or None if unknown."""
    if not result.get("ok", False):
        return f"فشل: {(result.get('error') or '')[:120]}"
    if name == "web_search":
        # Tolerate both schemas: DuckDuckGo 'count' or Tavily 'result_count'
        n = result.get("count") or result.get("result_count") or len(result.get("results") or [])
        rt = result.get("response_time_sec")
        return f"{n} نتيجة بحث" + (f" • {rt}ث" if rt else "")
    if name == "fetch_url":
        return f"{result.get('status')} • {result.get('length', 0)} حرف"
    if name == "view_bulk_files":
        return f"قرأت {result.get('count', 0)} ملف"
    if name == "apply_patch":
        return f"patch exit={result.get('exit_code')}{' (dry-run)' if result.get('dry_run') else ''}"
    if name == "db_query":
        op = result.get("operation")
        if op == "count":
            return f"count = {result.get('count')}"
        if op == "find":
            return f"find: {result.get('count', 0)} وثيقة"
        if op == "find_one":
            return "find_one: " + ("موجود" if result.get("result") else "غير موجود")
        if op == "distinct":
            return f"distinct: {len(result.get('values', []))} قيمة"
    if name == "ast_analyze":
        return (f"{len(result.get('functions', []))} دالة • "
                f"{len(result.get('classes', []))} class • "
                f"{len(result.get('imports', []))} import")
    return None


def extra_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if not result.get("ok") and result.get("error"):
        return result["error"][:300]
    if name == "web_search":
        rs = result.get("results", [])
        # Tolerate both schemas: DuckDuckGo uses 'snippet', Tavily uses 'content'
        return "\n".join(
            f"• {r.get('title', '')}\n  {r.get('url', '')}\n  {(r.get('snippet') or r.get('content') or '')[:150]}"
            for r in rs[:5]
        )
    if name == "fetch_url":
        return (result.get("content") or "")[:500]
    if name == "view_bulk_files":
        files = result.get("files", [])
        return "\n".join(f"📄 {f.get('path', '')} ({f.get('total_lines', '?')} lines)" for f in files[:6])
    if name == "apply_patch":
        return (result.get("stdout") or "")[:400]
    if name == "db_query":
        return json.dumps(result.get("results") or result.get("result") or result.get("count") or result.get("values"),
                          ensure_ascii=False, default=str)[:500]
    if name == "ast_analyze":
        funcs = result.get("functions", [])[:10]
        return "\n".join(f"def {f['name']}({', '.join(f['args'])}) — line {f['line']}" for f in funcs)
    return None
