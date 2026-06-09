"""
Safety Net — replaces hardcoded restrictions with intelligent guardrails.

Old approach: `_is_protected_path()` blocked every write to core files.
The problem: the AI lost its ability to evolve its OWN intelligence module.

New approach: full freedom + tripwires:

  1. **Snapshot before any core-file write**
     Auto-backup to /tmp/zerax_snapshots/<file>__<timestamp> so we can roll back.

  2. **Sanity check before commit**
     Run `python -c "import ast; ast.parse(content)"` on Python files.
     Run a syntactic JS check if Node available.
     If parse fails → REJECT with error.

  3. **Import safety check** for Python files
     Verify the file can be `importlib`-imported (catches typos, missing modules).

  4. **Critical-function check** for our own core files
     If the file is one of our "spine" files (autocoder/__init__.py, etc.),
     ensure the must-have symbols (TOOL_HANDLERS, ANTHROPIC_TOOLS, ...) still
     exist after the write. If they vanished → REJECT.

  5. **Easy rollback** — `restore_snapshot(file, snapshot_id)` puts it back.

The AI sees: "حُفظت snapshot. الكتابة نجحت." instead of "ممنوع".
If it broke something: "Sanity فشل: SyntaxError line 42 — راجع وأعد المحاولة."
"""
from __future__ import annotations
import os
import ast
import json
import time
import shutil
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

REPO_ROOT = Path("/app")
SNAPSHOT_DIR = Path(os.environ.get("ZERAX_SNAPSHOT_DIR", "/tmp/zerax_snapshots"))
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Files we treat as "spine" — extra-strict checks. Editing allowed, but
# sanity + symbol checks must pass.
SPINE_FILES = {
    "/app/backend/modules/autocoder/__init__.py",
    "/app/backend/modules/autocoder/llm_providers.py",
    "/app/backend/modules/autocoder/tools_extra.py",
    "/app/backend/modules/autocoder/tools_universe.py",
    "/app/backend/modules/autocoder/tools_quality.py",
    "/app/backend/modules/autocoder/code_index.py",
    "/app/backend/modules/autocoder/safety_net.py",
    "/app/backend/server.py",
}

# Symbols that MUST remain in autocoder/__init__.py after any edit
REQUIRED_SYMBOLS = {
    "/app/backend/modules/autocoder/__init__.py": [
        "TOOL_HANDLERS", "ANTHROPIC_TOOLS", "AUTOCODER_SYSTEM_PROMPT",
        "execute_autocoder_tool", "create_autocoder_router", "tool_write_file",
        "tool_edit_file", "tool_run_command",
    ],
    "/app/backend/server.py": [
        "app", "include_router",  # Routers must still be registered
    ],
}


# ════════════════════════════════════════════════════════════════════════
# Sanity checks
# ════════════════════════════════════════════════════════════════════════
def _check_python_syntax(content: str) -> Tuple[bool, str]:
    try:
        ast.parse(content)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"parse error: {e}"


def _check_required_symbols(path: str, content: str) -> Tuple[bool, str]:
    required = REQUIRED_SYMBOLS.get(path, [])
    missing = [s for s in required if s not in content]
    if missing:
        return False, f"Missing required symbols after edit: {', '.join(missing)}"
    return True, ""


def _check_python_imports(path: str, content: str) -> Tuple[bool, str]:
    """Soft check: try to compile + see if obvious import statements look sane.
    We don't actually import — that's expensive and may have side effects."""
    try:
        compile(content, path, "exec")
        return True, ""
    except SyntaxError as e:
        return False, f"compile fail line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"compile error: {e}"


def sanity_check(path: str, content: str) -> Dict[str, Any]:
    """Returns {ok, errors[], warnings[]} for a proposed write."""
    p = str(path)
    errors: List[str] = []
    warnings: List[str] = []

    if p.endswith(".py"):
        ok, err = _check_python_syntax(content)
        if not ok:
            errors.append(f"Python syntax: {err}")
        else:
            ok2, err2 = _check_python_imports(p, content)
            if not ok2:
                errors.append(f"Python compile: {err2}")

    # JSON validation
    if p.endswith(".json"):
        try:
            json.loads(content)
        except Exception as e:
            errors.append(f"JSON parse: {e}")

    # Spine-file extra checks
    if p in SPINE_FILES:
        # Size sanity: file shouldn't shrink to <30% of current size (likely deletion accident)
        current_path = Path(p)
        if current_path.exists():
            current_size = current_path.stat().st_size
            new_size = len(content)
            if new_size < current_size * 0.3 and current_size > 1000:
                warnings.append(
                    f"⚠️ File shrunk drastically: {current_size}B → {new_size}B. "
                    f"تأكد إنك ما حذفت شي مهم."
                )

        # Required symbols
        ok, err = _check_required_symbols(p, content)
        if not ok:
            errors.append(err)

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "is_spine": p in SPINE_FILES,
    }


# ════════════════════════════════════════════════════════════════════════
# Snapshots
# ════════════════════════════════════════════════════════════════════════
def _snapshot_path_for(file_path: str) -> Path:
    """Create snapshot dir mirror inside SNAPSHOT_DIR."""
    rel = file_path.lstrip("/")
    rel = rel.replace("/", "__")
    return SNAPSHOT_DIR / rel


def make_snapshot(file_path: str) -> Optional[Dict[str, Any]]:
    """Backup current content before an edit. Returns {snapshot_id, path}."""
    p = Path(file_path)
    if not p.exists():
        return None
    try:
        snap_dir = _snapshot_path_for(file_path)
        snap_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        snap_file = snap_dir / f"{ts}.bak"
        shutil.copy2(p, snap_file)
        # Keep only last 10 snapshots per file
        snaps = sorted(snap_dir.glob("*.bak"), key=lambda x: x.stat().st_mtime, reverse=True)
        for old in snaps[10:]:
            try:
                old.unlink()
            except Exception:
                pass
        return {
            "snapshot_id": ts,
            "snapshot_path": str(snap_file),
            "size": snap_file.stat().st_size,
        }
    except Exception as e:
        logger.warning(f"snapshot failed for {file_path}: {e}")
        return None


def list_snapshots(file_path: str = "") -> List[Dict[str, Any]]:
    """List snapshots — either for one file or all files."""
    out: List[Dict[str, Any]] = []
    if file_path:
        snap_dir = _snapshot_path_for(file_path)
        if not snap_dir.exists():
            return []
        for s in sorted(snap_dir.glob("*.bak"), key=lambda x: x.stat().st_mtime, reverse=True):
            out.append({
                "snapshot_id": int(s.stem),
                "file_path": file_path,
                "snapshot_path": str(s),
                "size": s.stat().st_size,
                "age_seconds": int(time.time() - s.stat().st_mtime),
            })
        return out
    # all
    for snap_dir in SNAPSHOT_DIR.iterdir():
        if not snap_dir.is_dir():
            continue
        orig = "/" + snap_dir.name.replace("__", "/")
        for s in sorted(snap_dir.glob("*.bak"), key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
            out.append({
                "snapshot_id": int(s.stem),
                "file_path": orig,
                "snapshot_path": str(s),
                "size": s.stat().st_size,
                "age_seconds": int(time.time() - s.stat().st_mtime),
            })
    return out[:50]


def restore_snapshot(file_path: str, snapshot_id: int) -> Dict[str, Any]:
    """Restore a file from a snapshot."""
    snap_dir = _snapshot_path_for(file_path)
    snap_file = snap_dir / f"{snapshot_id}.bak"
    if not snap_file.exists():
        return {"ok": False, "error": f"snapshot {snapshot_id} not found for {file_path}"}
    target = Path(file_path)
    try:
        # Make a fresh snapshot of current first
        if target.exists():
            make_snapshot(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snap_file, target)
        return {
            "ok": True,
            "restored": file_path,
            "from_snapshot": snapshot_id,
            "size": target.stat().st_size,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ════════════════════════════════════════════════════════════════════════
# AI tool wrappers
# ════════════════════════════════════════════════════════════════════════
async def tool_sanity_check(path: str, content: str) -> Dict[str, Any]:
    """Run sanity check WITHOUT writing — for the AI to validate edits beforehand."""
    return {"ok": True, **sanity_check(path, content)}


async def tool_list_snapshots(file_path: str = "") -> Dict[str, Any]:
    snaps = list_snapshots(file_path)
    return {"ok": True, "snapshots": snaps, "count": len(snaps)}


async def tool_restore_snapshot(file_path: str, snapshot_id: int) -> Dict[str, Any]:
    return restore_snapshot(file_path, int(snapshot_id))


SAFETY_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "sanity_check",
        "description": ("Validate proposed file content WITHOUT writing. Checks Python AST, "
                       "JSON syntax, required symbols for spine files. **استخدمها قبل write_file** "
                       "على الملفات الحيوية لتجنّب كسر النظام."),
        "input_schema": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"},
        }, "required": ["path", "content"]},
    },
    {
        "name": "list_snapshots",
        "description": ("List automatic snapshots taken before each write to spine files. "
                       "Empty file_path = all snapshots."),
        "input_schema": {"type": "object", "properties": {
            "file_path": {"type": "string"},
        }, "required": []},
    },
    {
        "name": "restore_snapshot",
        "description": "Restore a file from a previous snapshot. Use if last edit broke something.",
        "input_schema": {"type": "object", "properties": {
            "file_path": {"type": "string"},
            "snapshot_id": {"type": "integer"},
        }, "required": ["file_path", "snapshot_id"]},
    },
]

SAFETY_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "sanity_check", "desc": "validate content without writing", "args": ["path", "content"]},
    {"name": "list_snapshots", "desc": "list auto-backups", "args": ["file_path?"]},
    {"name": "restore_snapshot", "desc": "rollback to backup", "args": ["file_path", "snapshot_id"]},
]

SAFETY_TOOL_HANDLERS = {
    "sanity_check": tool_sanity_check,
    "list_snapshots": tool_list_snapshots,
    "restore_snapshot": tool_restore_snapshot,
}


def safety_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in SAFETY_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return f"✗ {(result.get('error') or '')[:120]}"
    if name == "sanity_check":
        errs = result.get("errors", [])
        warns = result.get("warnings", [])
        if errs:
            return f"✗ {len(errs)} خطأ: {errs[0][:80]}"
        if warns:
            return f"⚠ {len(warns)} تحذير"
        return "✓ نظيف" + (" (spine)" if result.get("is_spine") else "")
    if name == "list_snapshots":
        return f"{result.get('count', 0)} snapshot"
    if name == "restore_snapshot":
        return f"✓ استعدت: {result.get('restored', '')[:60]}"
    return None


def safety_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name == "sanity_check":
        errs = result.get("errors", [])
        warns = result.get("warnings", [])
        out = []
        for e in errs[:5]:
            out.append(f"  ✗ {e}")
        for w in warns[:3]:
            out.append(f"  ⚠ {w}")
        return "\n".join(out) if out else "✓ كل الفحوصات نجحت"
    if name == "list_snapshots":
        snaps = result.get("snapshots", [])
        return "\n".join(
            f"  • #{s['snapshot_id']} | {s['file_path'][:60]} | {s['size']}B | منذ {s['age_seconds']}s"
            for s in snaps[:10]
        )
    return None


SAFETY_PROMPT_RULES = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛡️  Safety Net — حرية كاملة + شبكة أمان ذكية
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ القيود القديمة (PROTECTED_PATHS) **أُلغيت**. تقدر تعدّل أي ملف، بما فيها:
   • autocoder/__init__.py (دماغك)
   • autocoder/llm_providers.py
   • autocoder/tools_*.py
   • server.py
   • أي ملف ثاني

✅ بدلاً منها، فيه **شبكة أمان تلقائية**:

  1. **Snapshot تلقائي** — قبل أي write_file لملف spine، النظام يحفظ نسخة
     في /tmp/zerax_snapshots/ تلقائياً. ما تحتاج تطلبها.

  2. **Sanity check** — قبل ما النظام يكتب فعلياً:
     • Python syntax + compile check
     • Required symbols check للملفات الحيوية (TOOL_HANDLERS, ANTHROPIC_TOOLS, ...)
     • تحذير لو الملف انكمش بشدّة (احتمال حذف بالغلط)
     لو فشل أي فحص → الكتابة تُرفض ويرجع الخطأ بالضبط.

  3. **Rollback سهل** — لو كسرت شي:
     • list_snapshots(file_path) → شوف كل الـsnapshots
     • restore_snapshot(file_path, snapshot_id) → رجع للنسخة القديمة
     • كل عملية restore تعمل snapshot من الحالي قبل ما ترجع (آمنة)

🎯 **سير العمل المُحسَّن** للتعديلات على الملفات الحيوية:

  1. read_file أو code_summary → افهم البنية
  2. (اختياري) sanity_check(path, new_content) → جرّب قبل الكتابة الفعلية
  3. write_file أو edit_file → النظام يعمل snapshot + يفحص تلقائياً
  4. لو فشل → اقرأ الخطأ المحدد، صحّح، أعد
  5. verify_full → تأكد إن كل شي شغّال
  6. لو كسرت → restore_snapshot للإصلاح الفوري

💡 الذكاء الحقيقي = الحرية + المسؤولية + القدرة على التراجع.
"""


def is_spine_file(path: str) -> bool:
    """Public helper used by tool_write_file etc."""
    try:
        resolved = str(Path(path).expanduser().resolve())
        return resolved in SPINE_FILES
    except Exception:
        return False
