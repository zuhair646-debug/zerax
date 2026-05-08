"""
Zitex Auto-Coder — Owner-only AI agent that can read/write/execute on the
Zitex codebase itself ("برمجة زيتاكس").

Security layers:
  1. Owner role enforcement (require_owner) on every endpoint
  2. Passcode lock (bcrypt-hashed) — first-time setup creates passcode + 6 recovery codes
  3. Session token (4 hours TTL) — required for chat + tool execution
  4. All actions logged to `autocoder_audit` collection

Endpoints:
  GET    /api/autocoder/status                  — is_setup, is_unlocked
  POST   /api/autocoder/setup                   — first-time: set passcode → returns recovery codes
  POST   /api/autocoder/unlock                  — passcode → session_token (4h)
  POST   /api/autocoder/recover                 — recovery_code + new_passcode
  POST   /api/autocoder/lock                    — invalidate session
  POST   /api/autocoder/reset-passcode          — change passcode (requires current)
  POST   /api/autocoder/chat                    — SSE streaming chat (header X-AutoCoder-Token)
  GET    /api/autocoder/conversations           — list owner's autocoder convs
  GET    /api/autocoder/conversation/{id}       — full transcript
  DELETE /api/autocoder/conversation/{id}
  GET    /api/autocoder/audit                   — recent audit log
"""
from __future__ import annotations
import os
import re
import json
import uuid
import shlex
import asyncio
import logging
import secrets
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

REPO_ROOT = Path("/app")
GIT_WORKDIR = Path("/tmp/zitex_workdir")  # Where the AI clones+commits the repo on production
SESSION_TTL_HOURS = 4
RECOVERY_CODE_COUNT = 6
PASSCODE_MIN_LEN = 6


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _gen_recovery_code() -> str:
    # 4 groups of 4 hex chars: ABCD-1234-EF56-7890
    raw = secrets.token_hex(8).upper()
    return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}-{raw[12:16]}"


async def _ensure_git_workdir() -> Dict[str, Any]:
    """Make sure /tmp/zitex_workdir is a fresh clone of the repo.
    Used on Railway production where /app is not a git repo (only the build subdir).
    Returns {ok, path, action} or {ok: False, error}.
    """
    gh_token = os.environ.get("GITHUB_TOKEN", "").strip()
    gh_repo = os.environ.get("GITHUB_REPO", "").strip()
    if not gh_token or not gh_repo:
        return {"ok": False, "error": "GITHUB_TOKEN/GITHUB_REPO env vars missing — set them in Railway Variables"}

    auth_url = f"https://x-access-token:{gh_token}@github.com/{gh_repo}.git"
    if (GIT_WORKDIR / ".git").exists():
        # Pull latest
        proc = await asyncio.create_subprocess_shell(
            f"cd {shlex.quote(str(GIT_WORKDIR))} && "
            f"git remote set-url origin {shlex.quote(auth_url)} && "
            f"git fetch origin && git reset --hard origin/HEAD",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            return {"ok": False, "error": (err or out).decode("utf-8", errors="replace")[:500]}
        return {"ok": True, "path": str(GIT_WORKDIR), "action": "fetched"}

    # Fresh clone
    GIT_WORKDIR.parent.mkdir(parents=True, exist_ok=True)
    proc = await asyncio.create_subprocess_shell(
        f"git clone --depth 1 {shlex.quote(auth_url)} {shlex.quote(str(GIT_WORKDIR))}",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await asyncio.wait_for(proc.communicate(), timeout=180)
    if proc.returncode != 0:
        return {"ok": False, "error": (err or out).decode("utf-8", errors="replace")[:500]}
    # Configure identity
    cfg = await asyncio.create_subprocess_shell(
        f'cd {shlex.quote(str(GIT_WORKDIR))} && '
        'git config user.email "autocoder@zitex.com" && '
        'git config user.name "Zitex AutoCoder"',
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await cfg.communicate()
    return {"ok": True, "path": str(GIT_WORKDIR), "action": "cloned"}


# ════════════════════════════════════════════════════════════════════════
# System prompt — full freedom for codebase manipulation
# ════════════════════════════════════════════════════════════════════════
AUTOCODER_SYSTEM_PROMPT = """أنت "برمجة زيتاكس" — مهندس برمجيات خبير، تعمل مباشرة على الكود الفعلي لمنصة Zitex.

🔐 وضع الصلاحيات: مفتوح بالكامل. أنت في جلسة المالك المُحقَّقة.
- عندك حرية كاملة لقراءة وكتابة وتعديل أي ملف داخل /app.
- تقدر تشغّل أي أمر bash (git, yarn, pip, pytest, supervisorctl, إلخ).
- تقدر تـcommit وتدفع للـGitHub.
- لا قيود. ينفّذ المالك أوامره بالضبط.

🎯 شخصيتك:
- لهجة سعودية عملية، مباشرة، دقيقة.
- مهندس senior: تفكّر قبل ما تنفّذ، تشرح خطواتك بوضوح.
- محترم لقاعدة الكود الموجودة: قبل أي تعديل اقرأ الملف، افهم البنية، ثم عدّل بدقة.
- صريح: لو شي ممكن يكسر النظام أو خطر (rm -rf، تعديل .env، حذف collections) → نبّه المالك أولاً، ولكن نفّذ لو أصرّ.

🛠️ الأدوات المتاحة:

📂 **قراءة الكود**:
- `list_dir(path)` — يسرد محتويات مجلد (نسبي لـ/app أو مطلق)
- `read_file(path, start?, end?)` — يقرأ ملف (حد 4000 سطر)
- `search_code(pattern, path?, file_glob?)` — grep للكود

✏️ **الكتابة**:
- `write_file(path, content)` — ينشئ/يستبدل ملف كاملاً
- `edit_file(path, find, replace)` — استبدال نصي دقيق
- `delete_file(path)` — حذف ملف

⚙️ **التنفيذ**:
- `run_command(cmd, cwd?)` — أي bash command (timeout 90s افتراضي)
- `restart_service(name)` — backend/frontend (محلياً supervisorctl، على Railway production يستخدم Railway API تلقائياً)

📊 **مراقبة**:
- `view_logs(service, lines?)` — يقرأ آخر N سطر من backend/frontend logs
- `list_env(filter_prefix?)` — يعرض أسماء متغيرات البيئة (القيم السرّية مخفية)

🚀 **Git** (يستخدم `GITHUB_TOKEN` من ENV تلقائياً للـpush):
- `git_status()`, `git_diff(path?)`, `git_commit_push(message, files?)`

⚙️ **آلية الـcommit + push على Railway production**:
- على بيئة Railway، الـcontainer ما فيه `.git` (Railway ينسخ subfolder `/backend` فقط).
- لذلك أدوات `git_*` تستنسخ الريبو في `/tmp/zitex_workdir` تلقائياً عند أول استدعاء.
- لما تستدعي `git_commit_push`:
  1. يـsync تلقائياً كل تعديلاتك على `/app/backend` و `/app/frontend/src` و `/app/memory` لـ `/tmp/zitex_workdir`
  2. يعمل `git add -A`, `git commit`, `git push` في الـworkdir
  3. Railway يكتشف الـpush تلقائياً ويعيد البناء (~3-5 دقايق)
- يعني: أنت **عدّل في `/app` كما لو كنت في dev** → استدعِ `git_commit_push` → Railway ينشر.

📐 خريطة الكود (ملخص):
- `/app/backend/server.py` — الـmain FastAPI app
- `/app/backend/modules/<name>/__init__.py` — كل ميزة في module مستقل (agent, freebuild_v2, autocoder, إلخ)
- `/app/backend/modules/freebuild_v2/tools.py` — كل أدوات بناء المواقع (~2200 سطر)
- `/app/frontend/src/App.js` — الـrouter
- `/app/frontend/src/pages/<Name>.js` — الصفحات
- `/app/frontend/src/components/<Name>.js` — المكوّنات
- `/app/memory/PRD.md` — خطة المنتج

🔑 قواعد العمل:
1. **اقرأ قبل ما تكتب**. لو طلب تعديل، استدعِ `read_file` أولاً، افهم الكود، ثم استدعِ `edit_file` أو `write_file`.
2. **خطوات صغيرة**. قسّم العمل لخطوات منطقية، نفّذ أداة واحدة كل مرة، اشرح للمالك ماذا فعلت بعد كل خطوة.
3. **اختبر بعد التعديل**. لو غيّرت backend → `run_command("sudo supervisorctl status backend")`. لو غيّرت frontend → فحص browser console.
4. **commit بعد ما تخلص**. نهاية كل feature/fix → `git_commit_push("feat: ...")` مع رسالة وصفية.
5. **ممنوع تخترع كود**. لو ما متأكد من API endpoint أو شكل dict، اقرأ الملف الحقيقي.
6. **حافظ على .env**. ممنوع تكتب أو تطبع المفاتيح السرية إلا لو طلب صريح.
7. **بعد modification المهم**: اعرض على المالك ملخص قصير: "✅ سويت X و Y. تبيني أعمل commit؟"

🚫 **ممنوع منعاً باتاً**:
- **لا تقول "ناقص" أو "غير متاح" بدون اختبار `run_command` حقيقي أولاً.** لو شككت أن أداة OS غير موجودة → شغّل `which <tool>` أو `<tool> --version` قبل ما تجزم.
- **لا تفترض من الذاكرة**. البيئة قد تختلف بين preview و Railway production. اختبر دايماً.
- **لا تهلوس عن قائمة tools متاحة**. عندك بالضبط الأدوات اللي محددة في schema هذي الجلسة (11 أداة + view_logs + list_env). أي شي ثاني → run_command.

🌐 **بيئة التشغيل**:
- محلياً (preview): فيه supervisor + git + curl + كل شي
- على Railway production: فيه git + curl + jq + python (مثبتين في Dockerfile). `supervisorctl` غير موجود — استخدم `restart_service` (يستدعي Railway API تلقائياً).
- لاكتشاف وين أنت: `run_command("env | grep RAILWAY_ | head -5")`. لو رجع متغيرات → أنت على Railway.

📏 طول الردّ: قصير عملي. الذكاء في الأدوات.
"""


# ════════════════════════════════════════════════════════════════════════
# Tool implementations
# ════════════════════════════════════════════════════════════════════════
def _resolve_path(path: str) -> Path:
    """Resolve path safely. Allow anything inside /app."""
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = REPO_ROOT / p
    return p.resolve()


async def tool_list_dir(path: str = ".") -> Dict[str, Any]:
    try:
        p = _resolve_path(path)
        if not p.exists():
            return {"ok": False, "error": f"path not found: {p}"}
        if not p.is_dir():
            return {"ok": False, "error": f"not a directory: {p}"}
        entries = []
        for child in sorted(p.iterdir()):
            try:
                entries.append({
                    "name": child.name,
                    "type": "dir" if child.is_dir() else "file",
                    "size": child.stat().st_size if child.is_file() else None,
                })
            except Exception:
                continue
        return {"ok": True, "path": str(p), "entries": entries[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_read_file(path: str, start: int = 1, end: Optional[int] = None) -> Dict[str, Any]:
    try:
        p = _resolve_path(path)
        if not p.exists() or not p.is_file():
            return {"ok": False, "error": f"file not found: {p}"}
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        total = len(lines)
        if end is None:
            end = min(start + 4000, total)
        end = min(end, total)
        start = max(1, start)
        chunk = "\n".join(lines[start - 1:end])
        return {
            "ok": True, "path": str(p), "total_lines": total,
            "shown": [start, end], "content": chunk[:200000],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_write_file(path: str, content: str) -> Dict[str, Any]:
    try:
        p = _resolve_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        existed = p.exists()
        p.write_text(content, encoding="utf-8")
        return {
            "ok": True, "path": str(p),
            "action": "overwritten" if existed else "created",
            "size": len(content),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_edit_file(path: str, find: str, replace: str) -> Dict[str, Any]:
    try:
        p = _resolve_path(path)
        if not p.exists():
            return {"ok": False, "error": f"file not found: {p}"}
        text = p.read_text(encoding="utf-8", errors="replace")
        if find not in text:
            return {"ok": False, "error": "find string not found in file"}
        count = text.count(find)
        if count > 1:
            return {"ok": False, "error": f"find string is not unique ({count} matches) — make it more specific"}
        new = text.replace(find, replace, 1)
        p.write_text(new, encoding="utf-8")
        return {"ok": True, "path": str(p), "replacements": 1, "new_size": len(new)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_delete_file(path: str) -> Dict[str, Any]:
    try:
        p = _resolve_path(path)
        if not p.exists():
            return {"ok": False, "error": "file not found"}
        if p.is_dir():
            return {"ok": False, "error": "use run_command(rm -rf) for directories"}
        p.unlink()
        return {"ok": True, "path": str(p), "action": "deleted"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_search_code(pattern: str, path: str = ".", file_glob: str = "") -> Dict[str, Any]:
    try:
        p = _resolve_path(path)
        cmd = ["grep", "-rn", "--color=never", "-E", pattern, str(p)]
        if file_glob:
            cmd.extend(["--include", file_glob])
        # exclude common heavy dirs
        for ex in ("node_modules", ".git", "__pycache__", ".next", "dist", "build"):
            cmd.extend(["--exclude-dir", ex])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        out = result.stdout[:60000]
        lines = out.splitlines()[:300]
        return {
            "ok": True, "pattern": pattern, "matches": len(lines),
            "results": "\n".join(lines),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "search timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_run_command(cmd: str, cwd: str = "/app", timeout: int = 90) -> Dict[str, Any]:
    try:
        cwd_p = _resolve_path(cwd)
        proc = await asyncio.create_subprocess_shell(
            cmd, cwd=str(cwd_p),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return {"ok": False, "error": f"command timed out after {timeout}s"}
        out = (stdout or b"").decode("utf-8", errors="replace")[:50000]
        err = (stderr or b"").decode("utf-8", errors="replace")[:20000]
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": out, "stderr": err, "cmd": cmd,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_restart_service(name: str) -> Dict[str, Any]:
    if name not in ("backend", "frontend", "all"):
        return {"ok": False, "error": "name must be backend|frontend|all"}
    # On Railway production, supervisor doesn't exist — use Railway API redeploy
    rw_token = os.environ.get("RAILWAY_TOKEN", "").strip()
    rw_service = os.environ.get("RAILWAY_SERVICE_ID", "").strip()
    rw_env = os.environ.get("RAILWAY_ENVIRONMENT_ID", "").strip()
    on_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT"))
    if on_railway and rw_token and rw_service and rw_env:
        try:
            import httpx
            q = (
                'mutation Redeploy($s: String!, $e: String!) { '
                'serviceInstanceRedeploy(serviceId: $s, environmentId: $e) }'
            )
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(
                    "https://backboard.railway.com/graphql/v2",
                    headers={"Authorization": f"Bearer {rw_token}",
                             "Content-Type": "application/json"},
                    json={"query": q, "variables": {"s": rw_service, "e": rw_env}},
                )
            data = r.json()
            if "errors" in data:
                return {"ok": False, "error": str(data["errors"])[:200]}
            return {"ok": True, "exit_code": 0, "stdout":
                    f"Railway redeploy triggered for service {rw_service[:8]}…",
                    "method": "railway-api"}
        except Exception as e:
            return {"ok": False, "error": f"railway api: {e}"}
    # Local fallback: supervisorctl
    target = "all" if name == "all" else name
    return await tool_run_command(f"sudo supervisorctl restart {target}")


async def tool_git_status() -> Dict[str, Any]:
    setup = await _ensure_git_workdir()
    if not setup.get("ok"):
        return setup
    return await tool_run_command(
        f"cd {shlex.quote(str(GIT_WORKDIR))} && "
        "git status --short 2>&1 && echo '---' && git log -5 --oneline 2>&1"
    )


async def tool_git_diff(path: str = "") -> Dict[str, Any]:
    setup = await _ensure_git_workdir()
    if not setup.get("ok"):
        return setup
    cmd = f"cd {shlex.quote(str(GIT_WORKDIR))} && "
    cmd += "git diff" if not path else f"git diff -- {shlex.quote(path)}"
    return await tool_run_command(cmd)


async def tool_git_commit_push(message: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
    """Commit + push from the working clone (/tmp/zitex_workdir).

    The agent's `write_file` and `edit_file` write to /app for live testing,
    but to actually persist changes to GitHub, those changes must also exist
    inside the working clone. We rsync them from /app to GIT_WORKDIR before
    committing. This way the agent never has to worry about two paths.
    """
    setup = await _ensure_git_workdir()
    if not setup.get("ok"):
        return setup

    gh_token = os.environ.get("GITHUB_TOKEN", "").strip()
    gh_repo = os.environ.get("GITHUB_REPO", "").strip()
    auth_url = f"https://x-access-token:{gh_token}@github.com/{gh_repo}.git" if gh_token and gh_repo else None

    # Sync working files from /app into the workdir (only the relevant subdirs)
    # This keeps /tmp/zitex_workdir in sync with the agent's edits to /app.
    sync_cmds = []
    sync_pairs = [
        ("/app/backend", str(GIT_WORKDIR / "backend")),
        ("/app/frontend/src", str(GIT_WORKDIR / "frontend/src")),
        ("/app/frontend/public", str(GIT_WORKDIR / "frontend/public")),
        ("/app/frontend/package.json", str(GIT_WORKDIR / "frontend/package.json")),
        ("/app/memory", str(GIT_WORKDIR / "memory")),
    ]
    for src, dst in sync_pairs:
        src_p = Path(src)
        if not src_p.exists():
            continue
        if src_p.is_dir():
            # rsync without --delete to be safe — agent must explicitly delete
            sync_cmds.append(
                f"mkdir -p {shlex.quote(dst)} && "
                f"cp -r {shlex.quote(src)}/. {shlex.quote(dst)}/ 2>/dev/null || true"
            )
        else:
            dst_dir = str(Path(dst).parent)
            sync_cmds.append(f"mkdir -p {shlex.quote(dst_dir)} && cp {shlex.quote(src)} {shlex.quote(dst)}")

    pre_sync = " && ".join(sync_cmds) if sync_cmds else "true"

    parts = [f"cd {shlex.quote(str(GIT_WORKDIR))}"]
    parts.append('git config user.email "autocoder@zitex.com" 2>/dev/null || true')
    parts.append('git config user.name "Zitex AutoCoder" 2>/dev/null || true')
    if auth_url:
        parts.append(f'git remote set-url origin {shlex.quote(auth_url)} 2>/dev/null || true')

    # Run the sync first (outside the workdir cd block)
    full_cmd = f"{pre_sync} && " + " && ".join(parts)

    # Stage
    if files:
        # Files are given as absolute /app paths or repo-relative — accept both
        rel_files = []
        for f in files:
            if f.startswith("/app/"):
                rel_files.append(f[5:])
            else:
                rel_files.append(f.lstrip("/"))
        quoted = " ".join(shlex.quote(f) for f in rel_files)
        full_cmd += f" && git add {quoted}"
    else:
        full_cmd += " && git add -A"

    safe_msg = message.replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    full_cmd += f' && git commit -m "{safe_msg}" 2>&1 || echo "(nothing to commit)"'
    full_cmd += ' && BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)'
    full_cmd += ' && [ "$BRANCH" = "HEAD" ] && BRANCH=main; git push origin "HEAD:$BRANCH" 2>&1'

    r = await tool_run_command(full_cmd, timeout=180)

    # Scrub token from output
    if gh_token:
        for k in ("stdout", "stderr"):
            if isinstance(r.get(k), str):
                r[k] = r[k].replace(gh_token, "***GITHUB_TOKEN***")
    r["workdir"] = str(GIT_WORKDIR)
    r["synced"] = setup.get("action")
    return r


async def tool_view_logs(service: str = "backend", lines: int = 100) -> Dict[str, Any]:
    """Read recent logs. Tries multiple known paths."""
    if service not in ("backend", "frontend"):
        return {"ok": False, "error": "service must be backend|frontend"}
    candidates = [
        f"/var/log/supervisor/{service}.err.log",
        f"/var/log/supervisor/{service}.out.log",
        f"/app/logs/{service}.log",
        f"/tmp/logs/{service}.log",
    ]
    on_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT"))
    if on_railway:
        # On Railway, app logs go to stdout — direct file logs may not exist.
        # We'll return a hint to use Railway API or dashboard.
        return {
            "ok": True,
            "method": "railway-stdout",
            "info": "On Railway, application logs stream to Railway dashboard. View at: https://railway.app/dashboard → service → Deployments → View Logs",
            "stdout": "(use Railway dashboard to view live logs)",
        }
    for p in candidates:
        try:
            from pathlib import Path as _P
            fp = _P(p)
            if fp.exists():
                content = fp.read_text(encoding="utf-8", errors="replace")
                tail = "\n".join(content.splitlines()[-lines:])
                return {"ok": True, "path": str(fp), "lines": min(lines, len(content.splitlines())),
                        "stdout": tail[:30000]}
        except Exception:
            continue
    return {"ok": False, "error": "no log files found"}


async def tool_list_env(filter_prefix: str = "") -> Dict[str, Any]:
    """List ENV var names (NOT values) so the AI can see what's configured.
    Sensitive values are never returned — only key names + masked previews."""
    SAFE_PREFIXES = ("RAILWAY_", "BACKEND_", "FRONTEND_", "CORS_", "DB_", "PORT")
    out = []
    for k, v in sorted(os.environ.items()):
        if filter_prefix and not k.startswith(filter_prefix):
            continue
        # Show value only for non-sensitive
        is_sensitive = any(x in k.upper() for x in
                           ("KEY", "TOKEN", "SECRET", "PASSWORD", "API"))
        if is_sensitive:
            preview = (v[:6] + "..." + v[-4:]) if v and len(v) > 14 else "***"
            out.append({"name": k, "set": True, "preview": preview, "sensitive": True})
        elif k.startswith(SAFE_PREFIXES) or k in ("PATH", "HOME"):
            out.append({"name": k, "set": True, "value": v[:200], "sensitive": False})
        else:
            out.append({"name": k, "set": True, "preview": "***", "sensitive": True})
    return {"ok": True, "count": len(out), "vars": out[:200]}


# Tool registry for the LLM (legacy, used by UI for icons/labels)
TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "list_dir", "desc": "list files and folders at path", "args": ["path"]},
    {"name": "read_file", "desc": "read file content (optionally start/end line numbers)", "args": ["path", "start?", "end?"]},
    {"name": "write_file", "desc": "create or overwrite file", "args": ["path", "content"]},
    {"name": "edit_file", "desc": "find-and-replace exact unique string in file", "args": ["path", "find", "replace"]},
    {"name": "delete_file", "desc": "delete a single file", "args": ["path"]},
    {"name": "search_code", "desc": "grep -rn pattern across codebase", "args": ["pattern", "path?", "file_glob?"]},
    {"name": "run_command", "desc": "run any bash command (full power)", "args": ["cmd", "cwd?", "timeout?"]},
    {"name": "restart_service", "desc": "supervisor restart (backend|frontend|all)", "args": ["name"]},
    {"name": "git_status", "desc": "git status + last 5 commits", "args": []},
    {"name": "git_diff", "desc": "show current diff (optionally for path)", "args": ["path?"]},
    {"name": "git_commit_push", "desc": "stage all + commit + push to remote", "args": ["message", "files?"]},
    {"name": "view_logs", "desc": "read recent log lines (backend|frontend)", "args": ["service", "lines?"]},
    {"name": "list_env", "desc": "list env var NAMES (values masked for secrets)", "args": ["filter_prefix?"]},
]

# Anthropic-compatible tool schemas (native tool calling)
ANTHROPIC_TOOLS = [
    {
        "name": "list_dir",
        "description": "List files and folders at given path (relative to /app or absolute).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "directory path, default '.'"},
            },
            "required": [],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file's contents. Returns text with line numbers shown range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start": {"type": "integer", "description": "start line (1-indexed)"},
                "end": {"type": "integer", "description": "end line"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Create a new file or overwrite an existing one with the full new content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string", "description": "full file content"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Find a UNIQUE exact string in a file and replace it. Fails if find string is not unique or not found. Use for surgical edits.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "find": {"type": "string", "description": "exact text to find (must be unique)"},
                "replace": {"type": "string", "description": "replacement text"},
            },
            "required": ["path", "find", "replace"],
        },
    },
    {
        "name": "delete_file",
        "description": "Delete a single file (not a directory). For directories use run_command with rm -rf.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "search_code",
        "description": "grep -rn pattern across codebase (excludes node_modules, .git, __pycache__, dist, build).",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "regex pattern"},
                "path": {"type": "string", "description": "search root, default '.'"},
                "file_glob": {"type": "string", "description": "glob like '*.py' or '*.js'"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "run_command",
        "description": "Execute any bash command. Full power — use carefully. Default cwd /app, timeout 90s.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cmd": {"type": "string"},
                "cwd": {"type": "string"},
                "timeout": {"type": "integer", "description": "seconds, max 300"},
            },
            "required": ["cmd"],
        },
    },
    {
        "name": "restart_service",
        "description": "supervisorctl restart (backend, frontend, or all).",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "enum": ["backend", "frontend", "all"]}},
            "required": ["name"],
        },
    },
    {
        "name": "git_status",
        "description": "Show git status + last 5 commits.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "git_diff",
        "description": "Show current uncommitted diff (optionally scoped to a path).",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": [],
        },
    },
    {
        "name": "git_commit_push",
        "description": "Stage files (or all if files=None) + commit with message + push to current remote branch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}, "description": "list of paths to stage; if omitted, stages all"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "view_logs",
        "description": "Read recent application log lines for backend or frontend service.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "enum": ["backend", "frontend"]},
                "lines": {"type": "integer", "description": "number of trailing lines, default 100"},
            },
            "required": ["service"],
        },
    },
    {
        "name": "list_env",
        "description": "List environment variable NAMES with masked values (real values never returned for secrets). Lets you discover what's configured.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filter_prefix": {"type": "string", "description": "optional prefix filter, e.g. 'RAILWAY_'"},
            },
            "required": [],
        },
    },
]

TOOL_HANDLERS = {
    "list_dir": tool_list_dir,
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "edit_file": tool_edit_file,
    "delete_file": tool_delete_file,
    "search_code": tool_search_code,
    "run_command": tool_run_command,
    "restart_service": tool_restart_service,
    "git_status": tool_git_status,
    "git_diff": tool_git_diff,
    "git_commit_push": tool_git_commit_push,
}


async def execute_autocoder_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return {"ok": False, "error": f"unknown tool: {name}"}
    try:
        return await handler(**args)
    except TypeError as e:
        return {"ok": False, "error": f"bad args: {e}"}
    except Exception as e:
        logger.exception(f"[AUTOCODER] tool {name} failed")
        return {"ok": False, "error": str(e)}


# ════════════════════════════════════════════════════════════════════════
# Pydantic models
# ════════════════════════════════════════════════════════════════════════
class SetupIn(BaseModel):
    passcode: str = Field(..., min_length=PASSCODE_MIN_LEN, max_length=128)


class UnlockIn(BaseModel):
    passcode: str = Field(..., min_length=1, max_length=128)


class RecoverIn(BaseModel):
    recovery_code: str = Field(..., min_length=8, max_length=64)
    new_passcode: str = Field(..., min_length=PASSCODE_MIN_LEN, max_length=128)


class ResetIn(BaseModel):
    current_passcode: str
    new_passcode: str = Field(..., min_length=PASSCODE_MIN_LEN, max_length=128)


class ChatIn(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=32000)


# ════════════════════════════════════════════════════════════════════════
# Router factory
# ════════════════════════════════════════════════════════════════════════
def create_autocoder_router(db, get_current_user, require_owner):
    router = APIRouter(prefix="/api/autocoder", tags=["autocoder"])

    async def _get_config() -> Optional[Dict[str, Any]]:
        return await db.autocoder_config.find_one({"_id": "main"}, {"_id": 0})

    async def _check_session_token(token: str) -> bool:
        if not token:
            return False
        sess = await db.autocoder_sessions.find_one({"token": token}, {"_id": 0})
        if not sess:
            return False
        try:
            exp = datetime.fromisoformat(sess["expires_at"])
        except Exception:
            return False
        return exp > datetime.now(timezone.utc)

    async def _audit(action: str, owner_id: str, meta: Optional[Dict[str, Any]] = None):
        try:
            await db.autocoder_audit.insert_one({
                "id": str(uuid.uuid4()),
                "action": action,
                "owner_id": owner_id,
                "meta": meta or {},
                "at": _now(),
            })
        except Exception:
            pass

    # ---- Setup / Unlock / Recover ----
    @router.get("/status")
    async def status(owner=Depends(require_owner)):
        cfg = await _get_config()
        keyinfo = _resolve_llm_key()
        return {
            "is_setup": bool(cfg and cfg.get("passcode_hash")),
            "owner_id": owner.get("id"),
            "session_ttl_hours": SESSION_TTL_HOURS,
            "llm_mode": keyinfo["mode"],
            "llm_label": keyinfo["label"],
            "llm_source": keyinfo["source"],
        }

    @router.get("/key-status")
    async def key_status(owner=Depends(require_owner)):
        """Public-ish info (owner only) about which key is being used."""
        keyinfo = _resolve_llm_key()
        # Don't return the key itself — just metadata
        return {
            "mode": keyinfo["mode"],
            "label": keyinfo["label"],
            "source": keyinfo["source"],
            "is_independent": keyinfo["mode"] == "direct",
            "instructions": (
                "أضف ANTHROPIC_API_KEY في إعدادات Railway (Variables) لجعل الذكاء مستقلاً تماماً عن نقاط Emergent."
                if keyinfo["mode"] != "direct" else
                "ممتاز — الذكاء يستخدم مفتاحك الخاص. لا تنخصم نقاط من Emergent."
            ),
        }

    @router.post("/setup")
    async def setup(payload: SetupIn, owner=Depends(require_owner)):
        cfg = await _get_config()
        if cfg and cfg.get("passcode_hash"):
            raise HTTPException(400, "already setup — use /reset-passcode")
        recovery_codes = [_gen_recovery_code() for _ in range(RECOVERY_CODE_COUNT)]
        recovery_hashes = [_hash(c) for c in recovery_codes]
        await db.autocoder_config.update_one(
            {"_id": "main"},
            {"$set": {
                "passcode_hash": _hash(payload.passcode),
                "recovery_hashes": recovery_hashes,
                "owner_id": owner.get("id"),
                "created_at": _now(),
                "updated_at": _now(),
            }},
            upsert=True,
        )
        await _audit("setup", owner.get("id"))
        return {
            "ok": True,
            "recovery_codes": recovery_codes,
            "warning": "احفظ هذه الرموز في مكان آمن. كل رمز يُستخدم مرة واحدة فقط لاسترجاع الوصول لو نسيت كلمة السر.",
        }

    @router.post("/unlock")
    async def unlock(payload: UnlockIn, owner=Depends(require_owner)):
        cfg = await _get_config()
        if not cfg or not cfg.get("passcode_hash"):
            raise HTTPException(400, "not setup — call /setup first")
        if not _verify(payload.passcode, cfg["passcode_hash"]):
            await _audit("unlock_failed", owner.get("id"))
            raise HTTPException(401, "invalid passcode")
        token = secrets.token_urlsafe(48)
        expires = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)
        await db.autocoder_sessions.insert_one({
            "token": token,
            "owner_id": owner.get("id"),
            "created_at": _now(),
            "expires_at": expires.isoformat(),
        })
        await _audit("unlock", owner.get("id"))
        return {"ok": True, "session_token": token, "expires_at": expires.isoformat()}

    @router.post("/recover")
    async def recover(payload: RecoverIn, owner=Depends(require_owner)):
        cfg = await _get_config()
        if not cfg:
            raise HTTPException(400, "not setup")
        rec_hashes: List[str] = cfg.get("recovery_hashes") or []
        matched_idx = -1
        for i, h in enumerate(rec_hashes):
            if _verify(payload.recovery_code.strip().upper(), h):
                matched_idx = i
                break
        if matched_idx < 0:
            await _audit("recover_failed", owner.get("id"))
            raise HTTPException(401, "invalid recovery code")
        # consume the code (one-time use), update passcode
        new_hashes = [h for i, h in enumerate(rec_hashes) if i != matched_idx]
        # if all consumed, generate fresh ones
        new_codes_to_return: List[str] = []
        if not new_hashes:
            new_codes_to_return = [_gen_recovery_code() for _ in range(RECOVERY_CODE_COUNT)]
            new_hashes = [_hash(c) for c in new_codes_to_return]
        await db.autocoder_config.update_one(
            {"_id": "main"},
            {"$set": {
                "passcode_hash": _hash(payload.new_passcode),
                "recovery_hashes": new_hashes,
                "updated_at": _now(),
            }},
        )
        # invalidate all old sessions
        await db.autocoder_sessions.delete_many({})
        await _audit("recover", owner.get("id"), {"regen_recovery": bool(new_codes_to_return)})
        return {
            "ok": True,
            "remaining_recovery_codes": len(new_hashes) if not new_codes_to_return else 0,
            "new_recovery_codes": new_codes_to_return,
        }

    @router.post("/reset-passcode")
    async def reset_passcode(payload: ResetIn, owner=Depends(require_owner)):
        cfg = await _get_config()
        if not cfg or not _verify(payload.current_passcode, cfg.get("passcode_hash", "")):
            raise HTTPException(401, "invalid current passcode")
        await db.autocoder_config.update_one(
            {"_id": "main"},
            {"$set": {"passcode_hash": _hash(payload.new_passcode), "updated_at": _now()}},
        )
        await db.autocoder_sessions.delete_many({})
        await _audit("reset_passcode", owner.get("id"))
        return {"ok": True}

    @router.post("/lock")
    async def lock(
        owner=Depends(require_owner),
        x_autocoder_token: Optional[str] = Header(None),
    ):
        if x_autocoder_token:
            await db.autocoder_sessions.delete_one({"token": x_autocoder_token})
        await _audit("lock", owner.get("id"))
        return {"ok": True}

    # ---- Chat (gated by session token) ----
    @router.post("/chat")
    async def chat(
        payload: ChatIn,
        request: Request,
        owner=Depends(require_owner),
        x_autocoder_token: Optional[str] = Header(None),
    ):
        if not await _check_session_token(x_autocoder_token or ""):
            raise HTTPException(401, "session locked or expired — unlock first")

        conv_id = payload.conversation_id or str(uuid.uuid4())
        conv = await db.autocoder_conversations.find_one(
            {"id": conv_id, "owner_id": owner.get("id")}, {"_id": 0}
        )
        messages: List[Dict[str, Any]] = conv["messages"] if conv else []
        messages.append({"role": "user", "content": payload.message, "ts": _now()})

        async def gen():
            try:
                assistant_text = ""
                tool_events: List[Dict[str, Any]] = []
                async for evt in _autocoder_stream(messages):
                    if evt["type"] == "text":
                        assistant_text += evt["content"]
                    elif evt["type"] == "tool":
                        tool_events.append({k: v for k, v in evt.items() if k not in ("content",)})
                    yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

                messages.append({
                    "role": "assistant",
                    "content": assistant_text,
                    "tool_events": tool_events,
                    "ts": _now(),
                })
                await db.autocoder_conversations.update_one(
                    {"id": conv_id},
                    {"$set": {
                        "id": conv_id,
                        "owner_id": owner.get("id"),
                        "messages": messages,
                        "updated_at": _now(),
                    }, "$setOnInsert": {"created_at": _now()}},
                    upsert=True,
                )
                await _audit("chat_turn", owner.get("id"), {
                    "conv_id": conv_id, "tools": [t.get("name") for t in tool_events],
                })
                yield f"data: {json.dumps({'type':'saved','conversation_id':conv_id})}\n\n"
            except Exception as e:
                logger.exception("[AUTOCODER] chat stream failed")
                yield f"data: {json.dumps({'type':'error','message': str(e)[:240]}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @router.get("/conversations")
    async def list_convs(owner=Depends(require_owner)):
        cur = db.autocoder_conversations.find(
            {"owner_id": owner.get("id")},
            {"_id": 0, "id": 1, "messages": {"$slice": 1}, "updated_at": 1},
        ).sort("updated_at", -1).limit(100)
        out = []
        async for c in cur:
            first = (c.get("messages") or [{}])[0]
            out.append({
                "id": c["id"],
                "preview": (first.get("content") or "")[:80],
                "updated_at": c.get("updated_at"),
            })
        return {"conversations": out}

    @router.get("/conversation/{cid}")
    async def get_conv(cid: str, owner=Depends(require_owner)):
        c = await db.autocoder_conversations.find_one(
            {"id": cid, "owner_id": owner.get("id")}, {"_id": 0}
        )
        if not c:
            raise HTTPException(404, "not found")
        return c

    @router.delete("/conversation/{cid}")
    async def del_conv(cid: str, owner=Depends(require_owner)):
        r = await db.autocoder_conversations.delete_one(
            {"id": cid, "owner_id": owner.get("id")}
        )
        if r.deleted_count == 0:
            raise HTTPException(404, "not found")
        return {"ok": True}

    @router.get("/audit")
    async def audit(limit: int = 50, owner=Depends(require_owner)):
        limit = min(max(1, limit), 200)
        cur = db.autocoder_audit.find(
            {"owner_id": owner.get("id")}, {"_id": 0}
        ).sort("at", -1).limit(limit)
        items = [a async for a in cur]
        return {"audit": items}

    return router


# ════════════════════════════════════════════════════════════════════════
# Key resolver — picks the user's own ANTHROPIC_API_KEY first, then falls
# back to EMERGENT_LLM_KEY only as last resort.
# ════════════════════════════════════════════════════════════════════════
def _resolve_llm_key() -> Dict[str, Any]:
    """Returns dict {key, source, mode} where mode is 'direct' or 'emergent'."""
    direct = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if direct and direct.startswith("sk-ant"):
        return {"key": direct, "source": "ANTHROPIC_API_KEY", "mode": "direct",
                "label": "🔓 مستقل — مفتاحك الخاص"}
    emergent = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if emergent:
        return {"key": emergent, "source": "EMERGENT_LLM_KEY", "mode": "emergent",
                "label": "⚡ مفتاح Emergent (نقاط تنخصم)"}
    return {"key": "", "source": None, "mode": "missing", "label": "❌ لا يوجد مفتاح"}


# ════════════════════════════════════════════════════════════════════════
# Claude streaming via DIRECT Anthropic SDK with native tool calling.
# Uses ANTHROPIC_API_KEY (user's own) when present, falls back to
# EMERGENT_LLM_KEY (with emergentintegrations) only as last resort.
# ════════════════════════════════════════════════════════════════════════
async def _autocoder_stream(messages: List[Dict[str, Any]]):
    """Yields events: {type:'text'|'tool'|'done'|'error', ...}"""
    keyinfo = _resolve_llm_key()
    if keyinfo["mode"] == "missing":
        yield {"type": "error",
               "message": "لا يوجد ANTHROPIC_API_KEY ولا EMERGENT_LLM_KEY. أضف مفتاحك في /app/backend/.env"}
        return

    # Build Anthropic-format message history (skip the last user message; we'll send fresh)
    anthropic_msgs: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        content = m.get("content", "") or ""
        if not content.strip():
            continue
        # If saved message had tool_events, we'd need to reconstruct content blocks,
        # but our stored messages keep `content` as plain text + `tool_events` summary.
        # For history purposes, plain text is sufficient (Claude will re-plan).
        anthropic_msgs.append({"role": role, "content": content[:12000]})

    # Mode 1: direct Anthropic SDK with native tool calling
    if keyinfo["mode"] == "direct":
        async for evt in _stream_direct_anthropic(anthropic_msgs, keyinfo["key"]):
            yield evt
        return

    # Mode 2: emergentintegrations fallback (text-blob tool parsing — legacy)
    async for evt in _stream_via_emergent(messages, keyinfo["key"]):
        yield evt


async def _stream_direct_anthropic(anthropic_msgs: List[Dict[str, Any]], api_key: str):
    """Uses official anthropic SDK with native multi-tool calling."""
    try:
        from anthropic import AsyncAnthropic
    except Exception as e:
        yield {"type": "error", "message": f"anthropic SDK missing: {e}"}
        return

    client = AsyncAnthropic(api_key=api_key)
    msgs = list(anthropic_msgs)

    for iteration in range(40):
        try:
            resp = await client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=8192,
                system=AUTOCODER_SYSTEM_PROMPT,
                tools=ANTHROPIC_TOOLS,
                messages=msgs,
            )
        except Exception as e:
            yield {"type": "error", "message": f"anthropic api: {str(e)[:240]}"}
            return

        # Stream the text portion of this response
        text_parts: List[str] = []
        tool_uses: List[Dict[str, Any]] = []
        assistant_blocks: List[Dict[str, Any]] = []  # for history

        for block in resp.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                txt = getattr(block, "text", "") or ""
                text_parts.append(txt)
                assistant_blocks.append({"type": "text", "text": txt})
                # stream chunked
                for i in range(0, len(txt), 40):
                    yield {"type": "text", "content": txt[i:i + 40]}
                    await asyncio.sleep(0.01)
            elif btype == "tool_use":
                tu = {
                    "id": block.id,
                    "name": block.name,
                    "input": dict(block.input) if block.input else {},
                }
                tool_uses.append(tu)
                assistant_blocks.append({
                    "type": "tool_use", "id": tu["id"], "name": tu["name"], "input": tu["input"],
                })

        # Persist assistant turn (text + tool_use blocks) into history
        if assistant_blocks:
            msgs.append({"role": "assistant", "content": assistant_blocks})

        if resp.stop_reason == "end_turn" or not tool_uses:
            yield {"type": "done"}
            return

        # Execute all tool calls in parallel — Claude supports multi-tool turns
        tool_results_blocks = []
        for tu in tool_uses:
            yield {"type": "tool", "status": "calling", "name": tu["name"],
                   "args": _trim_args_for_ui(tu["input"])}
            result = await execute_autocoder_tool(tu["name"], tu["input"])
            yield {"type": "tool", "status": "done", "name": tu["name"],
                   "ok": result.get("ok", False),
                   "summary": _summarize(tu["name"], result),
                   "preview": _preview_for_ui(tu["name"], result)}
            tool_results_blocks.append({
                "type": "tool_result",
                "tool_use_id": tu["id"],
                "content": json.dumps(_trim_result_for_llm(result), ensure_ascii=False)[:14000],
            })

        msgs.append({"role": "user", "content": tool_results_blocks})

    yield {"type": "text", "content": "\n(وصلت لـ40 دورة — أكمل بما عندي. اطلب تكملة لو تبي.)"}
    yield {"type": "done"}


async def _stream_via_emergent(messages: List[Dict[str, Any]], api_key: str):
    """Fallback: emergentintegrations with text-blob tool parsing (legacy path).
    Used only when ANTHROPIC_API_KEY is not set."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:
        yield {"type": "error", "message": f"emergentintegrations missing: {e}"}
        return

    tool_hint = (
        "\n\n🛠️ كيف تستدعي أداة — اكتب block بهذا الشكل بالضبط:\n"
        "```tool_call\n"
        '{"name":"<tool_name>","args":{...}}\n'
        "```\n"
        "ممكن تستدعي عدة أدوات في نفس الردّ (block منفصل لكل واحدة).\n\n"
        "**الأدوات المتاحة**:\n"
    )
    for t in TOOL_DEFS:
        tool_hint += f"- `{t['name']}({', '.join(t['args'])})` — {t['desc']}\n"

    session_id = f"autocoder-{uuid.uuid4().hex[:12]}"
    history_text = ""
    for m in messages[:-1]:
        role = "المالك" if m["role"] == "user" else "أنت"
        history_text += f"\n\n{role}: {m.get('content','')[:6000]}"
    last_user = messages[-1].get("content", "")
    full_input = (history_text + f"\n\nالمالك: {last_user}").strip()

    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=AUTOCODER_SYSTEM_PROMPT + tool_hint,
    )
    chat.with_model("anthropic", "claude-sonnet-4-5")

    for iteration in range(40):
        try:
            response = await chat.send_message(UserMessage(text=full_input))
        except Exception as e:
            yield {"type": "error", "message": f"claude error: {str(e)[:200]}"}
            return

        text = str(response or "")
        tool_blocks = re.findall(r"```tool_call\s*(\{[\s\S]+?\})\s*```", text)

        if tool_blocks:
            pre_text = re.split(r"```tool_call", text, maxsplit=1)[0].strip()
            if pre_text:
                for i in range(0, len(pre_text), 40):
                    yield {"type": "text", "content": pre_text[i:i + 40]}
                    await asyncio.sleep(0.01)

            results = []
            for blob in tool_blocks:
                try:
                    parsed = json.loads(blob)
                    name = parsed.get("name", "")
                    args = parsed.get("args", {}) or {}
                except Exception as e:
                    yield {"type": "tool", "status": "error", "name": "?",
                           "summary": f"تعذّر فهم الأمر: {e}"}
                    continue

                yield {"type": "tool", "status": "calling", "name": name,
                       "args": _trim_args_for_ui(args)}
                result = await execute_autocoder_tool(name, args)
                yield {"type": "tool", "status": "done", "name": name,
                       "ok": result.get("ok", False),
                       "summary": _summarize(name, result),
                       "preview": _preview_for_ui(name, result)}
                results.append({"name": name, "result": _trim_result_for_llm(result)})

            results_text = "\n\nنتائج الأدوات:\n"
            for r in results:
                trimmed = json.dumps(r["result"], ensure_ascii=False)[:8000]
                results_text += f"\n• {r['name']}: {trimmed}\n"
            full_input = results_text + "\n\nأكمل ردّك للمالك."
            continue

        for i in range(0, len(text), 40):
            yield {"type": "text", "content": text[i:i + 40]}
            await asyncio.sleep(0.01)
        yield {"type": "done"}
        return

    yield {"type": "text", "content": "\n(وصلت لـ40 دورة)"}
    yield {"type": "done"}


def _trim_args_for_ui(args: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 200:
            out[k] = v[:200] + f"... ({len(v)} chars)"
        else:
            out[k] = v
    return out


def _trim_result_for_llm(result: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in result.items():
        if isinstance(v, str) and len(v) > 12000:
            out[k] = v[:12000] + f"\n...[truncated {len(v) - 12000} chars]"
        else:
            out[k] = v
    return out


def _preview_for_ui(name: str, result: Dict[str, Any]) -> str:
    if not result.get("ok") and result.get("error"):
        return result["error"][:300]
    if name == "read_file":
        return (result.get("content") or "")[:600]
    if name == "list_dir":
        ents = result.get("entries") or []
        return "\n".join(f"{'📁' if e['type']=='dir' else '📄'} {e['name']}" for e in ents[:30])
    if name == "search_code":
        return (result.get("results") or "")[:600]
    if name == "run_command":
        return ((result.get("stdout") or "")[:500] +
                (("\n[stderr]\n" + result.get("stderr")[:200]) if result.get("stderr") else ""))
    if name in ("git_status", "git_diff", "git_commit_push", "restart_service"):
        return ((result.get("stdout") or "")[:500] +
                (("\n[stderr]\n" + result.get("stderr")[:200]) if result.get("stderr") else ""))
    if name in ("write_file", "edit_file", "delete_file"):
        return f"{result.get('action','done')}: {result.get('path','')}"
    return ""


def _summarize(name: str, result: Dict[str, Any]) -> str:
    if not result.get("ok", False):
        err = result.get("error", "")
        return f"فشل: {err[:120]}"
    if name == "read_file":
        return f"قرأت {result.get('total_lines',0)} سطر"
    if name == "list_dir":
        return f"{len(result.get('entries', []))} عنصر"
    if name == "write_file":
        return f"{result.get('action')}: {Path(result.get('path','')).name} ({result.get('size',0)}B)"
    if name == "edit_file":
        return f"استبدلت في {Path(result.get('path','')).name}"
    if name == "delete_file":
        return f"حذفت {Path(result.get('path','')).name}"
    if name == "search_code":
        return f"{result.get('matches',0)} مطابقة"
    if name == "run_command":
        return f"exit={result.get('exit_code')}"
    if name == "restart_service":
        return f"restart exit={result.get('exit_code')}"
    if name == "git_status":
        return "حالة git"
    if name == "git_diff":
        return "diff الحالي"
    if name == "git_commit_push":
        return f"commit + push exit={result.get('exit_code')}"
    return "تم"
