"""
Ops Tools — production observability & quick fixes.

These tools mirror what a senior engineer (me) does when something breaks:

  • check_deployment()       — is production alive? what's the version? response time?
  • view_logs(service, n)    — tail logs (supervisor or Railway)
  • git_status()             — what's uncommitted? what branch?
  • git_log(n)               — recent commits
  • git_revert(commit)       — revert a specific commit safely
  • rollback_last_push()     — emergency: revert + push immediately
  • service_restart(svc)     — restart backend/frontend supervisor service
  • health_overview()        — single call that runs ALL diagnostics in parallel
"""
from __future__ import annotations
import os
import asyncio
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


async def _sh(cmd: str, timeout: int = 30, cwd: Optional[str] = None) -> Dict[str, Any]:
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


def _prod_url() -> str:
    """Read production URL from frontend .env."""
    try:
        env_path = Path("/app/frontend/.env")
        for ln in env_path.read_text().splitlines():
            if ln.startswith("REACT_APP_BACKEND_URL="):
                return ln.split("=", 1)[1].strip()
    except Exception:
        pass
    return os.environ.get("REACT_APP_BACKEND_URL", "")


# ════════════════════════════════════════════════════════════════════════
# Deployment & health
# ════════════════════════════════════════════════════════════════════════
async def tool_check_deployment() -> Dict[str, Any]:
    """Active probe of production: is it alive? what version is running?"""
    url = _prod_url()
    if not url:
        return {"ok": False, "error": "REACT_APP_BACKEND_URL not configured"}

    started = time.time()
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            # Probe a known endpoint
            health_url = url.rstrip("/") + "/api/"
            r = await client.get(health_url)
            response_time_ms = int((time.time() - started) * 1000)
            return {
                "ok": True,
                "production_url": url,
                "probe_endpoint": health_url,
                "status": r.status_code,
                "alive": r.status_code in (200, 404, 405),  # 404 means routing works, no root
                "response_time_ms": response_time_ms,
                "headers": {k: v for k, v in r.headers.items() if k.lower() in ("server", "x-railway-edge", "via", "x-version")},
                "verdict": "🟢 PRODUCTION ALIVE" if r.status_code in (200, 404, 405) else f"🔴 PRODUCTION ISSUE ({r.status_code})",
            }
    except httpx.TimeoutException:
        return {"ok": False, "alive": False, "error": "timeout — production may be down",
                "production_url": url}
    except Exception as e:
        return {"ok": False, "alive": False, "error": str(e), "production_url": url}


async def tool_view_logs(service: str = "backend", lines: int = 80) -> Dict[str, Any]:
    """Tail recent supervisor logs (err + out) for a service."""
    if service not in ("backend", "frontend"):
        return {"ok": False, "error": "service must be backend|frontend"}
    lines = max(10, min(lines, 500))
    out: Dict[str, Any] = {"service": service, "tails": {}}
    for kind in ("err", "out"):
        log_path = f"/var/log/supervisor/{service}.{kind}.log"
        if not Path(log_path).exists():
            out["tails"][kind] = "(no log file)"
            continue
        try:
            content = Path(log_path).read_text(errors="replace")
            tail = "\n".join(content.splitlines()[-lines:])
            out["tails"][kind] = tail[-4000:]
        except Exception as e:
            out["tails"][kind] = f"(read error: {e})"
    return {"ok": True, **out}


# ════════════════════════════════════════════════════════════════════════
# Git ops
# ════════════════════════════════════════════════════════════════════════
async def tool_git_status() -> Dict[str, Any]:
    """`git status -sb` — what's changed?"""
    r = await _sh("git status -sb 2>&1", cwd="/app")
    lines = r["stdout"].splitlines()
    branch = lines[0] if lines else ""
    changes = lines[1:] if len(lines) > 1 else []
    return {
        "ok": r["exit_code"] == 0,
        "branch": branch,
        "uncommitted_files": len(changes),
        "files": [ln.strip()[:120] for ln in changes[:30]],
        "clean": len(changes) == 0,
    }


async def tool_git_log(n: int = 10) -> Dict[str, Any]:
    """Recent commits."""
    n = max(1, min(n, 50))
    r = await _sh(f"git log --oneline -n {n} 2>&1", cwd="/app")
    if r["exit_code"] != 0:
        return {"ok": False, "error": r["stderr"]}
    commits = []
    for ln in r["stdout"].splitlines():
        parts = ln.strip().split(" ", 1)
        if len(parts) == 2:
            commits.append({"hash": parts[0], "message": parts[1][:200]})
    return {"ok": True, "commits": commits, "count": len(commits)}


async def tool_git_revert(commit: str = "HEAD", push: bool = False) -> Dict[str, Any]:
    """Revert a commit. By default reverts HEAD and stages the revert commit."""
    if not commit:
        return {"ok": False, "error": "commit hash required"}
    r = await _sh(f"git revert --no-edit {commit} 2>&1", cwd="/app", timeout=30)
    if r["exit_code"] != 0:
        # try abort if conflicts
        await _sh("git revert --abort 2>&1", cwd="/app", timeout=10)
        return {"ok": False, "error": f"revert failed: {r['stderr'][:500]}",
                "stdout": r["stdout"][:500]}
    result = {"ok": True, "reverted": commit, "stdout": r["stdout"][-500:]}
    if push:
        push_script = "/root/.zenrex/push.sh"
        if Path(push_script).exists():
            pr = await _sh(f'bash {push_script} "revert: {commit}"', cwd="/app", timeout=60)
            result["push"] = {"exit_code": pr["exit_code"], "stdout": pr["stdout"][-500:]}
    return result


async def tool_rollback_last_push() -> Dict[str, Any]:
    """Emergency: revert the most recent commit AND push it. Use if last deploy broke production."""
    return await tool_git_revert("HEAD", push=True)


# ════════════════════════════════════════════════════════════════════════
# Service restart
# ════════════════════════════════════════════════════════════════════════
async def tool_service_restart(service: str = "backend") -> Dict[str, Any]:
    """Restart a supervisor service (dev only — production handled by Railway)."""
    if service not in ("backend", "frontend"):
        return {"ok": False, "error": "service must be backend|frontend"}
    r = await _sh(f"sudo supervisorctl restart {service} 2>&1", timeout=30)
    return {
        "ok": "started" in r["stdout"].lower() or r["exit_code"] == 0,
        "service": service,
        "output": r["stdout"][-500:],
    }


# ════════════════════════════════════════════════════════════════════════
# Health overview — composite single call
# ════════════════════════════════════════════════════════════════════════
async def tool_health_overview() -> Dict[str, Any]:
    """Run all critical diagnostics in parallel. Single call → full picture."""
    results = await asyncio.gather(
        tool_check_deployment(),
        tool_git_status(),
        tool_git_log(5),
        tool_view_logs("backend", lines=30),
        return_exceptions=True,
    )
    deploy = results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])}
    gstatus = results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])}
    glog = results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])}
    logs = results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])}
    # Quick verdict
    issues = []
    if not deploy.get("alive"):
        issues.append("production down or unreachable")
    if not gstatus.get("clean"):
        issues.append(f"{gstatus.get('uncommitted_files',0)} uncommitted files")
    return {
        "ok": len(issues) == 0,
        "deployment": deploy,
        "git_status": gstatus,
        "recent_commits": glog.get("commits", [])[:5],
        "logs_preview": logs,
        "issues": issues,
        "verdict": "🟢 كل شي تمام" if not issues else f"⚠️ {len(issues)} مشكلة: " + " · ".join(issues),
    }


# ════════════════════════════════════════════════════════════════════════
# Anthropic schemas
# ════════════════════════════════════════════════════════════════════════
OPS_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "check_deployment",
        "description": "Probe production server (Railway). Returns alive/status/response_time. **استخدمها دائماً بعد git_push** للتأكد من نجاح الـdeploy.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "view_logs",
        "description": "Tail recent supervisor logs (backend.err + backend.out). الأداة الأولى لما يصير شي غريب.",
        "input_schema": {"type": "object", "properties": {
            "service": {"type": "string", "description": "backend|frontend"},
            "lines": {"type": "integer", "description": "default 80"},
        }, "required": []},
    },
    {
        "name": "git_status",
        "description": "What's uncommitted? What branch?",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "git_log",
        "description": "Recent commit history.",
        "input_schema": {"type": "object", "properties": {"n": {"type": "integer"}}, "required": []},
    },
    {
        "name": "git_revert",
        "description": ("Safely revert a specific commit. Set push=true to immediately push the revert. "
                       "استخدمها لو commit حديث كسر شي."),
        "input_schema": {"type": "object", "properties": {
            "commit": {"type": "string", "description": "default HEAD"},
            "push": {"type": "boolean", "description": "auto-push the revert"},
        }, "required": []},
    },
    {
        "name": "rollback_last_push",
        "description": ("🚨 EMERGENCY: revert the most recent push and re-push the revert. "
                       "استخدمها لو آخر deploy خرّب production."),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "service_restart",
        "description": "Restart a supervisor service in dev (production restart handled by Railway).",
        "input_schema": {"type": "object", "properties": {
            "service": {"type": "string", "description": "backend|frontend"},
        }, "required": []},
    },
    {
        "name": "health_overview",
        "description": ("🔥 الأداة الأهم — تشغّل 4 diagnostics بالتوازي وترجع صورة كاملة عن الحالة. "
                       "استدعها أول شي لما المالك يقول 'في مشكلة' أو 'الموقع ما يشتغل'."),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

OPS_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "check_deployment", "desc": "probe production", "args": []},
    {"name": "view_logs", "desc": "tail supervisor logs", "args": ["service?", "lines?"]},
    {"name": "git_status", "desc": "uncommitted changes", "args": []},
    {"name": "git_log", "desc": "recent commits", "args": ["n?"]},
    {"name": "git_revert", "desc": "revert a commit", "args": ["commit?", "push?"]},
    {"name": "rollback_last_push", "desc": "emergency rollback", "args": []},
    {"name": "service_restart", "desc": "restart backend/frontend", "args": ["service?"]},
    {"name": "health_overview", "desc": "full diagnostics in parallel", "args": []},
]

OPS_TOOL_HANDLERS = {
    "check_deployment": tool_check_deployment,
    "view_logs": tool_view_logs,
    "git_status": tool_git_status,
    "git_log": tool_git_log,
    "git_revert": tool_git_revert,
    "rollback_last_push": tool_rollback_last_push,
    "service_restart": tool_service_restart,
    "health_overview": tool_health_overview,
}


def ops_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in OPS_TOOL_HANDLERS:
        return None
    if not result.get("ok") and "verdict" not in result:
        return f"✗ {(result.get('error') or '')[:120]}"
    if name == "check_deployment":
        return result.get("verdict", "") + f" · {result.get('response_time_ms','?')}ms"
    if name == "health_overview":
        return result.get("verdict", "")
    if name == "git_status":
        return f"branch={result.get('branch','?')} · uncommitted={result.get('uncommitted_files',0)}"
    if name == "git_log":
        return f"{result.get('count', 0)} commit"
    if name == "view_logs":
        return f"{result.get('service')} logs (err/out)"
    if name == "git_revert":
        return f"↩ reverted {result.get('reverted','HEAD')[:8]}"
    if name == "rollback_last_push":
        push = result.get("push", {})
        return f"🚨 rollback {result.get('reverted','HEAD')[:8]}" + (
            f" · pushed exit={push.get('exit_code')}" if push else ""
        )
    if name == "service_restart":
        return f"♻ {result.get('service')} restarted"
    return None


def ops_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name == "health_overview":
        d = result.get("deployment", {})
        gs = result.get("git_status", {})
        out = [
            f"🌐 Production: {d.get('verdict', '?')}",
            f"📦 Git: {gs.get('branch', '?')} · {gs.get('uncommitted_files', 0)} uncommitted",
        ]
        for c in result.get("recent_commits", [])[:3]:
            out.append(f"  • {c['hash']} {c['message'][:60]}")
        if result.get("issues"):
            out.append("⚠️ Issues:")
            for i in result["issues"]:
                out.append(f"  - {i}")
        return "\n".join(out)
    if name == "view_logs":
        tails = result.get("tails", {})
        out = []
        if tails.get("err"):
            out.append("─── stderr ───")
            out.append(tails["err"][-1500:])
        if tails.get("out"):
            out.append("─── stdout ───")
            out.append(tails["out"][-800:])
        return "\n".join(out)
    if name == "git_log":
        return "\n".join(f"  • {c['hash']} {c['message'][:80]}" for c in result.get("commits", []))
    if name == "git_status":
        return "\n".join(f"  {f}" for f in result.get("files", [])[:15])
    if name == "check_deployment":
        return f"URL: {result.get('production_url')}\nstatus: {result.get('status')} · {result.get('response_time_ms')}ms"
    return None


OPS_PROMPT_RULES = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 OPS — كن مهندس senior، لا مساعد متردد
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ سير العمل الـsenior (التزم به):

1. لما المالك يقول "في مشكلة" / "ما يشتغل":
   → استدعِ **health_overview** فوراً (تشغّل 4 fees بالتوازي)
   → النتيجة: production status + git status + recent commits + logs preview
   → بناءً عليها قرّر: rollback أم fix?

2. لما تـ git_push:
   → بعدها مباشرة استدعِ **check_deployment**
   → لو فشل (alive=false أو timeout): **استدعِ view_logs(backend)** فوراً
   → لو شفت traceback واضح في logs: اصلحه + push مرة ثانية
   → لو ما عرفت تصلحه فوراً: **rollback_last_push** (يرجع للحالة السابقة + push)

3. لما تكتشف bug:
   → git_log(5) — اشوف آخر commits، لو فيها relation للـbug → git_revert المناسب
   → بعد revert push تلقائياً (push=true)

4. لما تشتغل على dev (هنا):
   → service_restart('backend') بعد أي تعديل على .env
   → view_logs لمتابعة الأحداث

🔥 **القاعدة الذهبية للـops**: شك بعد كل تغيير. الإثبات > الافتراض.
   كل push = check_deployment.
   كل bug = health_overview.
   كل failure = view_logs.
"""
