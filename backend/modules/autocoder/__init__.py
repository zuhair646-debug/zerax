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
- `restart_service(name)` — backend/frontend (supervisorctl)

🚀 **Git**:
- `git_status()` — حالة الريبو
- `git_diff(path?)` — diff الحالي
- `git_commit_push(message, files?)` — commit + push للـmain

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
    target = "all" if name == "all" else name
    return await tool_run_command(f"sudo supervisorctl restart {target}")


async def tool_git_status() -> Dict[str, Any]:
    return await tool_run_command("git status --short && echo '---' && git log -5 --oneline")


async def tool_git_diff(path: str = "") -> Dict[str, Any]:
    cmd = "git diff" if not path else f"git diff -- {shlex.quote(path)}"
    r = await tool_run_command(cmd)
    return r


async def tool_git_commit_push(message: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
    """Stage, commit, and push to current branch."""
    parts = []
    if files:
        quoted = " ".join(shlex.quote(f) for f in files)
        parts.append(f"git add {quoted}")
    else:
        parts.append("git add -A")
    safe_msg = message.replace('"', '\\"').replace("`", "\\`")
    parts.append(f'git commit -m "{safe_msg}" || echo "nothing to commit"')
    parts.append("git push origin HEAD")
    cmd = " && ".join(parts)
    r = await tool_run_command(cmd, timeout=120)
    return r


# Tool registry for the LLM
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
        return {
            "is_setup": bool(cfg and cfg.get("passcode_hash")),
            "owner_id": owner.get("id"),
            "session_ttl_hours": SESSION_TTL_HOURS,
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
# Claude streaming agent loop with autocoder tools
# ════════════════════════════════════════════════════════════════════════
async def _autocoder_stream(messages: List[Dict[str, Any]]):
    """Yields events: {type:'text'|'tool'|'done'|'error', ...}"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:
        yield {"type": "error", "message": f"emergentintegrations missing: {e}"}
        return

    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        yield {"type": "error", "message": "EMERGENT_LLM_KEY missing"}
        return

    tool_hint = (
        "\n\n🛠️ كيف تستدعي أداة — اكتب block بهذا الشكل بالضبط:\n"
        "```tool_call\n"
        '{"name":"<tool_name>","args":{...}}\n'
        "```\n"
        "ممكن تستدعي عدة أدوات في نفس الردّ (block منفصل لكل واحدة). سأرجّع لك النتائج وتكمل.\n\n"
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
        api_key=key,
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
                summary = _summarize(name, result)
                yield {"type": "tool", "status": "done", "name": name,
                       "ok": result.get("ok", False), "summary": summary,
                       "preview": _preview_for_ui(name, result)}
                results.append({"name": name, "result": _trim_result_for_llm(result)})

            results_text = "\n\nنتائج الأدوات:\n"
            for r in results:
                trimmed = json.dumps(r["result"], ensure_ascii=False)[:8000]
                results_text += f"\n• {r['name']}: {trimmed}\n"
            full_input = results_text + "\n\nأكمل ردّك للمالك (استدعِ أدوات أخرى لو تحتاج، وإلا اعرض ملخص قصير)."
            continue

        # No tool calls — final text
        for i in range(0, len(text), 40):
            yield {"type": "text", "content": text[i:i + 40]}
            await asyncio.sleep(0.01)
        yield {"type": "done"}
        return

    yield {"type": "text", "content": "\n(وصلت لـ40 دورة استدعاء — أكمل بما عندي. اطلب تكملة لو تبي.)"}
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
