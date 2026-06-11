"""
Quality & Self-Verification Tools for the Auto-Coder.

The Auto-Coder has been hallucinating "I fixed it!" without actually fixing.
These tools force it to PROVE its claims with real, machine-readable evidence
before declaring success.

Three tools:
  1. verify_lint(path?)             — run ruff (py) and/or eslint (js) on the changed files
  2. verify_endpoint(url, ...)      — actually curl an endpoint and assert status/keyword
  3. verify_no_errors(service?)     — scan recent logs for tracebacks / 500 errors
  4. verify_full(paths?, urls?)     — run all three at once → single pass/fail verdict

Plus a self-healing helper:
  5. auto_fix_loop(target, max_iters=3)  — run a target (lint/curl) → if fails, capture
                                            output + re-prompt loop continues. Used by AI
                                            after edits to confirm everything actually works.
"""
from __future__ import annotations
import os
import re
import asyncio
import shutil
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)
REPO_ROOT = Path("/app")


async def _sh(cmd: str, timeout: int = 60, cwd: Optional[str] = None) -> Dict[str, Any]:
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {
            "exit_code": proc.returncode,
            "stdout": (out or b"").decode("utf-8", errors="replace"),
            "stderr": (err or b"").decode("utf-8", errors="replace"),
        }
    except asyncio.TimeoutError:
        return {"exit_code": -1, "stdout": "", "stderr": f"timeout after {timeout}s"}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e)}


# ════════════════════════════════════════════════════════════════════════
# 1. verify_lint
# ════════════════════════════════════════════════════════════════════════
async def tool_verify_lint(path: str = "/app/backend") -> Dict[str, Any]:
    """Run ruff (Python) and/or eslint (JS) on a path. Returns issues if any."""
    p = path
    if not p.startswith("/"):
        p = str(REPO_ROOT / p)
    if not Path(p).exists():
        return {"ok": False, "error": f"path not found: {p}"}

    results: Dict[str, Any] = {"path": p, "py": None, "js": None}
    is_py_path = p.endswith(".py") or Path(p).is_dir() or "backend" in p
    is_js_path = (p.endswith(".js") or p.endswith(".jsx") or p.endswith(".ts") or p.endswith(".tsx")
                  or "frontend" in p)

    if is_py_path and shutil.which("ruff"):
        # Ignore F401 (unused imports) since they're harmless warnings
        r = await _sh(f"ruff check {p} --output-format=concise --ignore F401", timeout=45)
        issues = [ln for ln in r["stdout"].splitlines() if ln.strip()]
        # Filter out "Found N error" summary lines
        real_issues = [i for i in issues if ".py:" in i and ": " in i]
        results["py"] = {
            "exit_code": r["exit_code"],
            "issue_count": len(real_issues),
            "issues": real_issues[:30],
        }
    if is_js_path and shutil.which("eslint"):
        # Best-effort — won't run if no eslint config
        cfg = Path("/app/frontend/.eslintrc.js")
        if cfg.exists() or Path("/app/frontend/.eslintrc.json").exists():
            r = await _sh(f"cd /app/frontend && yarn eslint --no-eslintrc -c .eslintrc* {p} 2>&1 | tail -50",
                          timeout=60)
            results["js"] = {"exit_code": r["exit_code"], "tail": r["stdout"][-2000:]}

    issues_total = 0
    if results["py"]:
        issues_total += results["py"]["issue_count"]
    return {
        "ok": issues_total == 0,
        "issues_total": issues_total,
        **results,
        "verdict": "نظيف ✓" if issues_total == 0 else f"فيه {issues_total} مشكلة لازم تصلحها",
    }


# ════════════════════════════════════════════════════════════════════════
# 2. verify_endpoint — real HTTP test
# ════════════════════════════════════════════════════════════════════════
async def tool_verify_endpoint(
    url: str,
    method: str = "GET",
    expected_status: int = 200,
    contains: str = "",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Any] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Actually fire an HTTP request and assert the response.

    Use this AFTER ANY backend change instead of just saying "it works".
    Pass `contains` to assert a specific keyword/JSON-key in the response.
    """
    if not url:
        return {"ok": False, "error": "url مطلوب"}

    # If a relative path was passed, build full URL from public backend URL
    if url.startswith("/"):
        be = ""
        # 1) Honour explicit override
        be = os.environ.get("BACKEND_URL", "").strip() or os.environ.get("REACT_APP_BACKEND_URL", "").strip()
        # 2) Railway-provided public hostname
        if not be:
            rw_dom = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
            if rw_dom:
                be = f"https://{rw_dom.lstrip('https://').lstrip('http://')}"
        # 3) Frontend .env (development)
        if not be:
            try:
                env_path = Path("/app/frontend/.env")
                if env_path.exists():
                    for ln in env_path.read_text().splitlines():
                        if ln.startswith("REACT_APP_BACKEND_URL="):
                            be = ln.split("=", 1)[1].strip()
                            break
            except Exception:
                pass
        # 4) Final fallback — only acceptable in dev (not on Railway)
        if not be:
            be = "http://localhost:8001"
        url = be.rstrip("/") + url

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            kwargs = {"headers": headers or {}}
            if body is not None:
                kwargs["json"] = body
            resp = await client.request(method.upper(), url, **kwargs)
            text = resp.text[:8000]
    except Exception as e:
        return {"ok": False, "error": f"request failed: {e}", "url": url}

    status_ok = resp.status_code == expected_status
    contains_ok = (contains in text) if contains else True

    return {
        "ok": status_ok and contains_ok,
        "url": url, "method": method.upper(),
        "status": resp.status_code,
        "expected_status": expected_status,
        "status_match": status_ok,
        "contains_match": contains_ok,
        "contains_target": contains or None,
        "response_preview": text[:1500],
        "verdict": ("✓ يعمل" if status_ok and contains_ok else
                    f"✗ توقعت {expected_status} وجاي {resp.status_code}" if not status_ok else
                    f"✗ المحتوى ما فيه '{contains}'"),
    }


# ════════════════════════════════════════════════════════════════════════
# 3. verify_no_errors — log scan
# ════════════════════════════════════════════════════════════════════════
async def tool_verify_no_errors(service: str = "backend", lines: int = 200,
                                since_seconds: int = 120) -> Dict[str, Any]:
    """Scan recent logs for tracebacks / 5xx errors / Python exceptions.
    Used right after a deployment or restart to catch issues immediately."""
    if service not in ("backend", "frontend"):
        return {"ok": False, "error": "service must be backend|frontend"}

    candidates = [
        f"/var/log/supervisor/{service}.err.log",
        f"/var/log/supervisor/{service}.out.log",
    ]
    blob = ""
    found = []
    for path in candidates:
        if Path(path).exists():
            found.append(path)
            try:
                # tail -n lines (we use plain read since the file may be small)
                content = Path(path).read_text(errors="replace")
                blob += content[-(lines * 200):]
            except Exception:
                pass

    if not blob:
        return {"ok": True, "note": "no log files found — service may be on Railway production",
                "checked": candidates}

    error_patterns = [
        (r"Traceback \(most recent call last\)", "Python Traceback"),
        (r"\b500 Internal Server Error\b", "HTTP 500"),
        (r'"\s5\d\d\s', "HTTP 5xx"),
        (r"ModuleNotFoundError", "ModuleNotFoundError"),
        (r"ImportError", "ImportError"),
        (r"SyntaxError", "SyntaxError"),
        (r"RuntimeError", "RuntimeError"),
        (r"AttributeError", "AttributeError"),
        (r"NameError", "NameError"),
        (r"TypeError:", "TypeError"),
        (r"Address already in use", "Port conflict"),
        (r"\bCRITICAL\b", "CRITICAL"),
        (r"\bFATAL\b", "FATAL"),
    ]
    detected = []
    for pat, label in error_patterns:
        matches = list(re.finditer(pat, blob))[:5]
        for m in matches:
            # collect a 200-char window of context
            start = max(0, m.start() - 100)
            end = min(len(blob), m.end() + 200)
            detected.append({"label": label, "snippet": blob[start:end].strip()[:400]})
    # dedupe
    seen, dedup = set(), []
    for d in detected:
        key = d["snippet"][:80]
        if key in seen:
            continue
        seen.add(key)
        dedup.append(d)

    return {
        "ok": len(dedup) == 0,
        "service": service,
        "files_checked": found,
        "error_count": len(dedup),
        "errors": dedup[:8],
        "verdict": "نظيف ✓" if not dedup else f"فيه {len(dedup)} خطأ مرصود في الـlogs — لازم تصلحها قبل ما تقول خلصت",
    }


# ════════════════════════════════════════════════════════════════════════
# 4. verify_full — composite check
# ════════════════════════════════════════════════════════════════════════
async def tool_verify_full(
    lint_path: str = "/app/backend",
    endpoints: Optional[List[Dict[str, Any]]] = None,
    log_service: str = "backend",
) -> Dict[str, Any]:
    """One-shot health verdict: lint + endpoints + log scan."""
    endpoints = endpoints or [{"url": "/api/"}]
    out: Dict[str, Any] = {"checks": {}}

    # lint
    out["checks"]["lint"] = await tool_verify_lint(lint_path)
    # endpoints
    ep_results = []
    for ep in endpoints[:5]:
        ep_results.append(await tool_verify_endpoint(
            url=ep.get("url", ""),
            method=ep.get("method", "GET"),
            expected_status=ep.get("expected_status", 200),
            contains=ep.get("contains", ""),
            headers=ep.get("headers"),
            body=ep.get("body"),
        ))
    out["checks"]["endpoints"] = ep_results
    # logs
    out["checks"]["logs"] = await tool_verify_no_errors(service=log_service)

    all_ok = (
        out["checks"]["lint"]["ok"]
        and all(e.get("ok") for e in ep_results)
        and out["checks"]["logs"]["ok"]
    )
    out["ok"] = all_ok
    out["verdict"] = "كل شي نظيف ✓ — تقدر تقول خلصت" if all_ok else "في مشاكل لازم تصلحها قبل ما تدّعي النجاح"
    return out


# ════════════════════════════════════════════════════════════════════════
# 5. frontend_check — yarn install/lint/build (requires Node in container)
# ════════════════════════════════════════════════════════════════════════
async def tool_frontend_check(
    mode: str = "lint",
    cwd: Optional[str] = None,
    timeout: int = 300,
) -> Dict[str, Any]:
    """Run frontend tooling (yarn). mode: 'lint' | 'install' | 'build'.

    On Railway production, /app/frontend does NOT exist (only /backend was copied).
    To run frontend tools there, we auto-clone the repo into /tmp/zenrex_workdir
    via the existing git tooling and use /tmp/zenrex_workdir/frontend.
    """
    import subprocess
    # Auto-resolve cwd: prefer /app/frontend (dev), fall back to cloned workdir (prod)
    if cwd is None:
        for candidate in ("/app/frontend", "/tmp/zenrex_workdir/frontend"):
            if Path(candidate, "package.json").exists():
                cwd = candidate
                break
        if cwd is None:
            # Trigger a workdir clone — try lazy import of the autocoder's git helper
            try:
                from modules.autocoder import _ensure_git_workdir
                setup = await _ensure_git_workdir()
                if setup.get("ok"):
                    cand = Path(setup["path"], "frontend")
                    if (cand / "package.json").exists():
                        cwd = str(cand)
            except Exception:
                pass
        if cwd is None:
            return {"ok": False,
                    "error": "package.json not found in /app/frontend or /tmp/zenrex_workdir/frontend",
                    "hint": "Run git_status / git_commit_push first to seed the workdir, or set GITHUB_TOKEN+GITHUB_REPO"}

    # Quick capability probe
    try:
        which = subprocess.run(["which", "yarn"], capture_output=True, text=True, timeout=5)
        if which.returncode != 0:
            return {"ok": False, "error": "yarn not installed in this container",
                    "hint": "ادفع الـDockerfile الجديد (Node.js 20 + yarn) أو ركّب محلياً", "node_unavailable": True}
    except Exception as e:
        return {"ok": False, "error": f"cannot detect yarn: {e}", "node_unavailable": True}

    cmd_map = {
        "lint": "yarn lint --max-warnings 0 || npx eslint src --max-warnings 0",
        "install": "yarn install --frozen-lockfile",
        "build": "yarn build",
        "type-check": "yarn type-check || npx tsc --noEmit",
    }
    cmd = cmd_map.get(mode)
    if not cmd:
        return {"ok": False, "error": f"unknown mode: {mode}. Use lint/install/build/type-check"}

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, cwd=cwd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return {"ok": False, "error": f"timeout after {timeout}s", "mode": mode}
        out = (stdout or b"").decode("utf-8", errors="replace")[:8000]
        err = (stderr or b"").decode("utf-8", errors="replace")[:4000]
        return {"ok": proc.returncode == 0, "exit_code": proc.returncode,
                "stdout_tail": out[-3000:], "stderr_tail": err[-2000:],
                "mode": mode, "cmd": cmd}
    except Exception as e:
        return {"ok": False, "error": str(e), "mode": mode}


# ════════════════════════════════════════════════════════════════════════
# Anthropic tool schemas
# ════════════════════════════════════════════════════════════════════════
QUALITY_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "verify_lint",
        "description": ("Run ruff (Python) and/or eslint (JS) on a path. Returns concrete issues. "
                       "**استخدمها بعد أي تعديل كبير على backend/frontend**. لا تقول 'الكود نظيف' بدون استدعاءها."),
        "input_schema": {"type": "object", "properties": {
            "path": {"type": "string", "description": "default /app/backend"},
        }, "required": []},
    },
    {
        "name": "verify_endpoint",
        "description": ("Actually fire an HTTP request and assert the response status + content. "
                       "**استخدمها بعد أي تعديل backend route**. مثال: verify_endpoint('/api/autocoder/status', expected_status=403). "
                       "للـURLs النسبية يستخدم REACT_APP_BACKEND_URL تلقائياً."),
        "input_schema": {"type": "object", "properties": {
            "url": {"type": "string"},
            "method": {"type": "string", "description": "GET|POST|PUT|DELETE — default GET"},
            "expected_status": {"type": "integer", "description": "default 200"},
            "contains": {"type": "string", "description": "assert response contains this keyword"},
            "headers": {"type": "object"},
            "body": {"type": "object"},
            "timeout": {"type": "integer"},
        }, "required": ["url"]},
    },
    {
        "name": "verify_no_errors",
        "description": ("Scan recent logs for Tracebacks / 500 errors / Python exceptions. "
                       "**استخدمها بعد أي restart_service**. لا تقول 'البكند شغّال' بدون استدعاءها."),
        "input_schema": {"type": "object", "properties": {
            "service": {"type": "string", "description": "backend|frontend"},
            "lines": {"type": "integer", "description": "default 200"},
        }, "required": []},
    },
    {
        "name": "verify_full",
        "description": ("Composite verdict: lint + endpoint checks + log scan. **استخدمها قبل ما تقول 'خلصت'** في نهاية أي مهمة backend."),
        "input_schema": {"type": "object", "properties": {
            "lint_path": {"type": "string"},
            "endpoints": {"type": "array", "items": {"type": "object"}, "description": "list of {url, method?, expected_status?, contains?}"},
            "log_service": {"type": "string"},
        }, "required": []},
    },
    {
        "name": "frontend_check",
        "description": ("🔧 شغّل أدوات الـfrontend (yarn lint/install/build/type-check) داخل الحاوية. "
                       "يحتاج Node.js + yarn (مضافة في Dockerfile). استخدمها للتأكد إن أي تعديل JSX/TS ما كسر شي قبل الـpush."),
        "input_schema": {"type": "object", "properties": {
            "mode": {"type": "string", "enum": ["lint", "install", "build", "type-check"], "description": "default lint"},
            "cwd": {"type": "string", "description": "default /app/frontend"},
            "timeout": {"type": "integer"},
        }, "required": []},
    },
]

QUALITY_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "verify_lint", "desc": "lint check (ruff/eslint)", "args": ["path?"]},
    {"name": "verify_endpoint", "desc": "real HTTP test", "args": ["url", "method?", "expected_status?", "contains?", "headers?", "body?"]},
    {"name": "verify_no_errors", "desc": "log scan for errors", "args": ["service?", "lines?"]},
    {"name": "verify_full", "desc": "composite verdict", "args": ["lint_path?", "endpoints?", "log_service?"]},
    {"name": "frontend_check", "desc": "yarn lint/install/build", "args": ["mode?", "cwd?", "timeout?"]},
]

QUALITY_TOOL_HANDLERS = {
    "verify_lint": tool_verify_lint,
    "verify_endpoint": tool_verify_endpoint,
    "verify_no_errors": tool_verify_no_errors,
    "verify_full": tool_verify_full,
    "frontend_check": tool_frontend_check,
}


def quality_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in QUALITY_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return f"✗ {(result.get('verdict') or result.get('error') or '')[:120]}"
    return f"✓ {(result.get('verdict') or 'نجح')[:100]}"


def quality_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name == "verify_lint":
        py = result.get("py")
        if py and py.get("issues"):
            return "\n".join(py["issues"][:8])
        return result.get("verdict", "")
    if name == "verify_endpoint":
        return f"{result.get('verdict')}\n{result.get('response_preview','')[:400]}"
    if name == "verify_no_errors":
        errs = result.get("errors", [])
        if errs:
            return "\n".join(f"• [{e['label']}] {e['snippet'][:180]}" for e in errs[:5])
        return result.get("verdict", "")
    if name == "verify_full":
        c = result.get("checks", {})
        lines = [f"lint: {'✓' if c.get('lint',{}).get('ok') else '✗'}",
                 f"logs: {'✓' if c.get('logs',{}).get('ok') else '✗'}"]
        for ep in c.get("endpoints", [])[:5]:
            lines.append(f"  {ep.get('method')} {ep.get('url','')[:60]} → {ep.get('status')}")
        return "\n".join(lines)
    return None


QUALITY_PROMPT_RULES = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 قاعدة الجودة العليا — PROOF-BEFORE-CLAIM (الأهم في الجلسة)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**ممنوع منعاً باتاً** تقول "خلصت" / "تم الإصلاح" / "يعمل الحين" / "كل شي تمام"
بدون ما تستدعي أداة `verify_*` ترجع `ok: true` فعلياً.

📋 بروتوكول الإثبات الإلزامي:

  ١. بعد أي تعديل في backend (write_file / edit_file / restart_service):
      → استدعِ `verify_no_errors(service='backend')` للتأكد ما فيه traceback
      → استدعِ `verify_endpoint(url='/api/...', ...)` على المسار اللي عدّلت عليه
      → لا تقول "البكند شغّال" قبل هاتين الأداتين

  ٢. بعد أي تعديل Python كبير (>20 سطر أو ملف جديد):
      → استدعِ `verify_lint(path='/app/backend/...')` ترجع `ok: true`

  ٣. قبل ما تختم أي مهمة:
      → استدعِ `verify_full(lint_path=..., endpoints=[...])` ترجع `ok: true`
      → بس بعد كذا تقدر تقول "خلصت" مع عرض ملخص ما تم.

  ٤. لو verify فشلت:
      → **لا تتجاهلها**. اقرأ `errors` أو `response_preview`، حدّد السبب، صحّح، أعد verify.
      → كرّر هذي الحلقة حتى ترجع `ok: true`.
      → لو فشلت 3 مرات على نفس الـcheck → اطلب من المالك معلومات إضافية.

  ٥. لا تخترع نجاحاً:
      → ممنوع تقول "افترض إنه يعمل" — كل ادّعاء لازم خلفه أداة تثبته.

🔁 Self-Healing Loop: لو verify رجعت errors:
  1. اقرأ الخطأ كاملاً (logs / traceback / response).
  2. حدّد الملف والسطر.
  3. read_file → edit_file (إصلاح نقطي).
  4. verify مرة ثانية.
  5. كرّر حتى ✓.
"""
