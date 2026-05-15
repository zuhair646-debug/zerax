"""
Sandbox Mode — give the Auto-Coder a safe playground to test ideas before
pushing them to production.

The sandbox lives at `/tmp/zitex_sandbox` and is a clone of the relevant
parts of `/app` (backend + frontend src). The AI can `sandbox_write` files
in it, run validation (`sandbox_validate`), preview the result, and finally
`sandbox_promote` to copy back into `/app` once happy.

Tools:
  - sandbox_init() — fresh copy of /app's key dirs into the sandbox
  - sandbox_status() — what files differ from /app
  - sandbox_read(path) — read a file from the sandbox
  - sandbox_write(path, content) — write inside the sandbox only
  - sandbox_run(cmd) — execute bash *inside* the sandbox dir
  - sandbox_validate() — python compile + import check on changed files
  - sandbox_diff(path?) — diff sandbox ↔ /app
  - sandbox_promote(paths?) — copy specific paths (or all changed) back to /app
  - sandbox_reset() — wipe the sandbox

Storage: file-system only. No Mongo state. Process-local.
"""
from __future__ import annotations
import os
import shutil
import asyncio
import shlex
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path("/app")
SANDBOX_ROOT = Path("/tmp/zitex_sandbox")

# Subdirs that get copied into the sandbox (small subset to keep it light).
SYNC_PAIRS = [
    ("backend/modules", "backend/modules"),
    ("backend/server.py", "backend/server.py"),
    ("frontend/src", "frontend/src"),
    ("memory", "memory"),
]


def _ensure_init() -> Dict[str, Any]:
    SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "path": str(SANDBOX_ROOT)}


def _resolve_in_sandbox(path: str) -> Path:
    """Anything inside SANDBOX_ROOT only. Block path traversal."""
    p = (SANDBOX_ROOT / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    # If user passed /app/... rewrite to sandbox equivalent
    try:
        if str(p).startswith(str(REPO_ROOT) + os.sep):
            rel = p.relative_to(REPO_ROOT)
            p = (SANDBOX_ROOT / rel).resolve()
    except Exception:
        pass
    if not str(p).startswith(str(SANDBOX_ROOT)):
        raise ValueError(f"path escapes sandbox: {p}")
    return p


# ════════════════════════════════════════════════════════════════════════
# Tools
# ════════════════════════════════════════════════════════════════════════
async def tool_sandbox_init() -> Dict[str, Any]:
    """Wipe + recreate the sandbox with current /app content."""
    if SANDBOX_ROOT.exists():
        shutil.rmtree(SANDBOX_ROOT, ignore_errors=True)
    SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)
    copied = []
    for src_rel, dst_rel in SYNC_PAIRS:
        src = REPO_ROOT / src_rel
        dst = SANDBOX_ROOT / dst_rel
        if not src.exists():
            continue
        try:
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            copied.append(dst_rel)
        except Exception as e:
            return {"ok": False, "error": f"copy failed for {src_rel}: {e}"}
    return {"ok": True, "sandbox": str(SANDBOX_ROOT), "copied": copied}


async def tool_sandbox_status() -> Dict[str, Any]:
    if not SANDBOX_ROOT.exists():
        return {"ok": False, "error": "sandbox not initialised — call sandbox_init() first"}
    # Diff every file under SYNC_PAIRS
    changed: List[str] = []
    new: List[str] = []
    for src_rel, _ in SYNC_PAIRS:
        sb = SANDBOX_ROOT / src_rel
        if not sb.exists():
            continue
        if sb.is_dir():
            for f in sb.rglob("*"):
                if not f.is_file():
                    continue
                rel = f.relative_to(SANDBOX_ROOT)
                orig = REPO_ROOT / rel
                if not orig.exists():
                    new.append(str(rel))
                    continue
                try:
                    if f.read_bytes() != orig.read_bytes():
                        changed.append(str(rel))
                except Exception:
                    continue
        else:
            rel = sb.relative_to(SANDBOX_ROOT)
            orig = REPO_ROOT / rel
            if not orig.exists():
                new.append(str(rel))
            elif sb.read_bytes() != orig.read_bytes():
                changed.append(str(rel))
    return {"ok": True, "changed": changed[:100], "new": new[:100],
            "total_changed": len(changed), "total_new": len(new)}


async def tool_sandbox_read(path: str, start: int = 1, end: Optional[int] = None) -> Dict[str, Any]:
    try:
        p = _resolve_in_sandbox(path)
        if not p.exists() or not p.is_file():
            return {"ok": False, "error": f"file not found in sandbox: {p}"}
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        total = len(lines)
        if end is None:
            end = min(start + 600, total)
        end = min(end, total)
        start = max(1, start)
        chunk = "\n".join(lines[start - 1:end])
        return {"ok": True, "path": str(p), "total_lines": total,
                "shown": [start, end], "content": chunk[:60000]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_sandbox_write(path: str, content: str) -> Dict[str, Any]:
    """Write a file ONLY inside the sandbox. Never touches /app."""
    try:
        p = _resolve_in_sandbox(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        existed = p.exists()
        p.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(p), "action": "overwritten" if existed else "created",
                "size": len(content)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_sandbox_run(cmd: str, timeout: int = 60) -> Dict[str, Any]:
    """Run bash inside the sandbox directory. cwd is locked to /tmp/zitex_sandbox."""
    if not SANDBOX_ROOT.exists():
        return {"ok": False, "error": "sandbox not initialised"}
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, cwd=str(SANDBOX_ROOT),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return {"ok": False, "error": f"timeout after {timeout}s"}
        out = (stdout or b"").decode("utf-8", errors="replace")[:40000]
        err = (stderr or b"").decode("utf-8", errors="replace")[:15000]
        return {"ok": proc.returncode == 0, "exit_code": proc.returncode,
                "stdout": out, "stderr": err, "cmd": cmd}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_sandbox_validate() -> Dict[str, Any]:
    """Compile-check every changed .py file in the sandbox."""
    status = await tool_sandbox_status()
    if not status.get("ok"):
        return status
    targets = [p for p in (status.get("changed", []) + status.get("new", []))
               if p.endswith(".py")]
    issues = []
    for rel in targets[:25]:
        full = SANDBOX_ROOT / rel
        r = subprocess.run(
            ["python3", "-m", "py_compile", str(full)],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            issues.append({"file": rel, "error": (r.stderr or r.stdout)[:400]})
    return {"ok": len(issues) == 0, "checked": len(targets), "issues": issues,
            "verdict": ("✅ كل الملفات passed" if not issues else
                        f"❌ {len(issues)} ملف فيه أخطاء")}


async def tool_sandbox_diff(path: Optional[str] = None) -> Dict[str, Any]:
    """diff sandbox vs /app for one file or all changed."""
    if not SANDBOX_ROOT.exists():
        return {"ok": False, "error": "sandbox not initialised"}
    if path:
        rel = path.lstrip("/")
        if rel.startswith("app/"):
            rel = rel[4:]
        sb = SANDBOX_ROOT / rel
        orig = REPO_ROOT / rel
        if not sb.exists():
            return {"ok": False, "error": f"not in sandbox: {rel}"}
        if not orig.exists():
            return {"ok": True, "path": rel, "diff": "(new file — not in /app yet)"}
        r = subprocess.run(
            ["diff", "-u", str(orig), str(sb)],
            capture_output=True, text=True, timeout=10,
        )
        return {"ok": True, "path": rel, "diff": (r.stdout or "")[:30000]}
    # All changed
    status = await tool_sandbox_status()
    diffs = []
    for rel in (status.get("changed", []) + status.get("new", []))[:10]:
        sb = SANDBOX_ROOT / rel
        orig = REPO_ROOT / rel
        if not orig.exists():
            diffs.append({"path": rel, "summary": "NEW FILE"})
            continue
        r = subprocess.run(
            ["diff", "-u", str(orig), str(sb)],
            capture_output=True, text=True, timeout=10,
        )
        diffs.append({"path": rel, "diff": (r.stdout or "")[:4000]})
    return {"ok": True, "diffs": diffs}


async def tool_sandbox_promote(paths: Optional[List[str]] = None) -> Dict[str, Any]:
    """Copy specific paths (or all changed) from sandbox back to /app.
    Only runs after sandbox_validate passes — checks first."""
    if not SANDBOX_ROOT.exists():
        return {"ok": False, "error": "sandbox not initialised"}
    val = await tool_sandbox_validate()
    if not val.get("ok"):
        return {"ok": False, "error": "validation failed — fix issues first",
                "issues": val.get("issues")}
    status = await tool_sandbox_status()
    targets = paths or (status.get("changed", []) + status.get("new", []))
    promoted = []
    for rel in targets:
        rel = rel.lstrip("/")
        if rel.startswith("app/"):
            rel = rel[4:]
        sb = SANDBOX_ROOT / rel
        if not sb.exists() or not sb.is_file():
            continue
        dst = REPO_ROOT / rel
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sb, dst)
            promoted.append(rel)
        except Exception as e:
            return {"ok": False, "error": f"copy failed {rel}: {e}", "promoted": promoted}
    return {"ok": True, "promoted": promoted, "count": len(promoted),
            "next_step": "استدعِ pre_deploy_check ثم git_commit_push للنشر"}


async def tool_sandbox_reset() -> Dict[str, Any]:
    """Wipe the entire sandbox directory."""
    if SANDBOX_ROOT.exists():
        shutil.rmtree(SANDBOX_ROOT, ignore_errors=True)
    return {"ok": True, "action": "reset"}


# ════════════════════════════════════════════════════════════════════════
# Schemas + handlers + helpers
# ════════════════════════════════════════════════════════════════════════
SANDBOX_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "sandbox_init",
        "description": "🧪 أنشئ بيئة sandbox آمنة في /tmp/zitex_sandbox تنسخ /app الحالي. استخدمها قبل أي تغيير محفوف بالمخاطر.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "sandbox_status",
        "description": "عرض الملفات المتغيّرة في الـsandbox عن /app.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "sandbox_read",
        "description": "اقرأ ملف من الـsandbox (مسار نسبي أو يبدأ بـ/app/).",
        "input_schema": {"type": "object", "properties": {
            "path": {"type": "string"}, "start": {"type": "integer"}, "end": {"type": "integer"},
        }, "required": ["path"]},
    },
    {
        "name": "sandbox_write",
        "description": "اكتب ملف داخل الـsandbox فقط (لا يلمس /app).",
        "input_schema": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"},
        }, "required": ["path", "content"]},
    },
    {
        "name": "sandbox_run",
        "description": "نفّذ أمر bash داخل /tmp/zitex_sandbox (cwd مقفول).",
        "input_schema": {"type": "object", "properties": {
            "cmd": {"type": "string"}, "timeout": {"type": "integer"},
        }, "required": ["cmd"]},
    },
    {
        "name": "sandbox_validate",
        "description": "compile-check كل ملفات Python المتغيّرة. لازم تستدعيها قبل promote.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "sandbox_diff",
        "description": "أظهر diff الـsandbox ↔ /app (كله أو ملف معيّن).",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": []},
    },
    {
        "name": "sandbox_promote",
        "description": "انقل التغييرات من sandbox إلى /app (يفشل لو validate ما رجّع ok=true).",
        "input_schema": {"type": "object", "properties": {
            "paths": {"type": "array", "items": {"type": "string"}},
        }, "required": []},
    },
    {
        "name": "sandbox_reset",
        "description": "احذف الـsandbox كاملاً (تعود لـ/app الحالي).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


SANDBOX_TOOL_HANDLERS = {
    "sandbox_init": tool_sandbox_init,
    "sandbox_status": tool_sandbox_status,
    "sandbox_read": tool_sandbox_read,
    "sandbox_write": tool_sandbox_write,
    "sandbox_run": tool_sandbox_run,
    "sandbox_validate": tool_sandbox_validate,
    "sandbox_diff": tool_sandbox_diff,
    "sandbox_promote": tool_sandbox_promote,
    "sandbox_reset": tool_sandbox_reset,
}


SANDBOX_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "sandbox_init", "desc": "init safe playground", "args": []},
    {"name": "sandbox_status", "desc": "list changed files", "args": []},
    {"name": "sandbox_read", "desc": "read file in sandbox", "args": ["path", "start?", "end?"]},
    {"name": "sandbox_write", "desc": "write file in sandbox", "args": ["path", "content"]},
    {"name": "sandbox_run", "desc": "bash inside sandbox", "args": ["cmd", "timeout?"]},
    {"name": "sandbox_validate", "desc": "compile-check changes", "args": []},
    {"name": "sandbox_diff", "desc": "diff vs /app", "args": ["path?"]},
    {"name": "sandbox_promote", "desc": "copy back to /app", "args": ["paths?"]},
    {"name": "sandbox_reset", "desc": "wipe sandbox", "args": []},
]


def sandbox_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in SANDBOX_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return f"sandbox-fail: {(result.get('error') or '')[:120]}"
    if name == "sandbox_init":
        return f"🧪 sandbox جاهز · نُسخ {len(result.get('copied', []))} مسار"
    if name == "sandbox_status":
        return f"📊 {result.get('total_changed', 0)} متغيّر · {result.get('total_new', 0)} جديد"
    if name == "sandbox_validate":
        return result.get("verdict", "validated")
    if name == "sandbox_promote":
        return f"🚀 promoted {result.get('count', 0)} ملف لـ/app"
    if name == "sandbox_write":
        return f"✏️ {result.get('action')}: {result.get('path','').split('/')[-1]}"
    if name == "sandbox_reset":
        return "🧹 sandbox wiped"
    return None


def sandbox_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in SANDBOX_TOOL_HANDLERS:
        return None
    if name == "sandbox_status":
        changed = result.get("changed", [])[:8]
        new = result.get("new", [])[:5]
        out = []
        if changed:
            out.append("📝 متغيّر:\n  " + "\n  ".join(changed))
        if new:
            out.append("✨ جديد:\n  " + "\n  ".join(new))
        return "\n".join(out) or "لا تغييرات"
    if name == "sandbox_diff":
        d = result.get("diff") or "\n".join(x.get("path", "") + ": " + (x.get("summary") or x.get("diff", "")[:300]) for x in result.get("diffs", []))
        return d[:1000]
    if name == "sandbox_read":
        return (result.get("content") or "")[:400]
    return None


SANDBOX_PROMPT_RULES = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 Sandbox Mode — قبل التغييرات المحفوفة بالمخاطر
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

استخدم Sandbox لما المهمة:
  - تشمل تعديلات على ملفات شوكة (server.py, autocoder, freebuild_v2/__init__.py)
  - تجرّب refactor كبير على وحدة كاملة
  - تختبر فكرة جديدة لست متأكد منها

الـworkflow:
  ١. sandbox_init()                            — يجهّز /tmp/zitex_sandbox
  ٢. sandbox_write(path, new_content)          — كرّر للملفات اللي تبي
  ٣. sandbox_validate()                        — compile-check
  ٤. sandbox_diff()                            — راجع التغييرات
  ٥. sandbox_promote()                         — انقل لـ/app لو راضي
  ٦. pre_deploy_check() ثم git_commit_push()   — انشر

لو الـvalidate فشل، sandbox_promote راح يرفض. أصلح في الـsandbox واعد المحاولة بدون لمس /app.
"""
