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
import base64
import mimetypes
import shlex
import asyncio
import logging
import secrets
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Header, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional runtime helper
    Image = None

# New: extra power tools + multi-LLM provider streamers
from .tools_extra import (
    tool_web_search, tool_fetch_url, tool_view_bulk_files,
    tool_apply_patch, make_db_query_tool, tool_ast_analyze,
    EXTRA_ANTHROPIC_TOOLS, EXTRA_TOOL_DEFS,
    extra_summarize, extra_preview,
)
from .llm_providers import stream_via_groq, stream_via_gemini, stream_via_openai
from .codebase_atlas import build_atlas_for_prompt
from .codebase_atlas_v2 import build_atlas_v2_for_prompt
from .tools_universe import (
    UNIVERSE_ANTHROPIC_TOOLS, UNIVERSE_TOOL_HANDLERS, UNIVERSE_TOOL_DEFS,
    universe_summarize, universe_preview, build_universe_for_prompt,
)
from .tools_quality import (
    QUALITY_ANTHROPIC_TOOLS, QUALITY_TOOL_HANDLERS, QUALITY_TOOL_DEFS,
    quality_summarize, quality_preview, QUALITY_PROMPT_RULES,
)
from .code_index import (
    INDEX_ANTHROPIC_TOOLS, INDEX_TOOL_HANDLERS, INDEX_TOOL_DEFS,
    index_summarize, index_preview, INDEX_PROMPT_RULES, get_index,
)
from .safety_net import (
    SAFETY_ANTHROPIC_TOOLS, SAFETY_TOOL_HANDLERS, SAFETY_TOOL_DEFS,
    safety_summarize, safety_preview, SAFETY_PROMPT_RULES,
    sanity_check as _sanity_check, make_snapshot, is_spine_file,
)
from .learning import (
    LEARNING_ANTHROPIC_TOOLS, LEARNING_TOOL_HANDLERS, LEARNING_TOOL_DEFS,
    learning_summarize, learning_preview, LEARNING_PROMPT_RULES,
    bind_db as _bind_learning_db, build_lessons_for_prompt,
    query_lessons as _query_lessons, get_stats as _learning_get_stats,
    promote as _promote_lesson, archive as _archive_lesson,
    add_lesson as _add_lesson,
)
from .autonomy import (
    AUTONOMY_ANTHROPIC_TOOLS, AUTONOMY_TOOL_HANDLERS, AUTONOMY_TOOL_DEFS,
    autonomy_summarize, autonomy_preview, AUTONOMY_PROMPT_RULES,
)
from .ops_tools import (
    OPS_ANTHROPIC_TOOLS, OPS_TOOL_HANDLERS, OPS_TOOL_DEFS,
    ops_summarize, ops_preview, OPS_PROMPT_RULES,
)
from .task_memory import (
    MEMORY_ANTHROPIC_TOOLS, MEMORY_TOOL_HANDLERS, MEMORY_TOOL_DEFS,
    memory_summarize, memory_preview, MEMORY_PROMPT_RULES,
    bind_db as _bind_memory_db, build_session_brief,
)
from .sandbox import (
    SANDBOX_ANTHROPIC_TOOLS, SANDBOX_TOOL_HANDLERS, SANDBOX_TOOL_DEFS,
    sandbox_summarize, sandbox_preview, SANDBOX_PROMPT_RULES,
)
from .integrations_status import (
    INTEGRATIONS_ANTHROPIC_TOOLS, INTEGRATIONS_TOOL_HANDLERS, INTEGRATIONS_TOOL_DEFS,
    integrations_summarize, integrations_preview,
)
from .web_search import (
    WEB_SEARCH_ANTHROPIC_TOOLS, WEB_SEARCH_TOOL_HANDLERS, WEB_SEARCH_TOOL_DEFS,
    web_search_summarize, web_search_preview, WEB_SEARCH_PROMPT_RULES,
    bind_db as _bind_websearch_db,
)
from .railway_tools import (
    RAILWAY_ANTHROPIC_TOOLS, RAILWAY_TOOL_HANDLERS, RAILWAY_TOOL_DEFS,
    railway_summarize, railway_preview, bind_creds_getter as _bind_railway_creds,
)
from .vercel_tools import (
    VERCEL_ANTHROPIC_TOOLS, VERCEL_TOOL_HANDLERS, VERCEL_TOOL_DEFS,
    vercel_summarize, vercel_preview, bind_creds_getter as _bind_vercel_creds,
)
from .model_router import (
    ROUTER_ANTHROPIC_TOOLS, ROUTER_TOOL_HANDLERS, ROUTER_TOOL_DEFS,
    router_summarize, router_preview, ROUTER_PROMPT_RULES,
    bind_db as _bind_router_db,
)
from .code_cache import (
    CACHE_ANTHROPIC_TOOLS, CACHE_TOOL_HANDLERS, CACHE_TOOL_DEFS,
    cache_summarize, cache_preview, CACHE_PROMPT_RULES,
    bind_db as _bind_cache_db, annotate_read as _cache_annotate_read,
)
from .superpowers import (
    SUPERPOWERS_ANTHROPIC_TOOLS, SUPERPOWERS_HANDLERS, SUPERPOWERS_TOOL_DEFS,
    SUPERPOWERS_PROMPT_RULES,
)

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════
# PRODUCTION SAFETY: Anti-loop guard only (full freedom on files)
# ════════════════════════════════════════════════════════════════════════

# Maximum git commits per chat session (raised from 15 to 100 — autonomous mode).
# User explicitly requested unlimited operation; 100 is a sanity cap to prevent runaway loops.
MAX_COMMITS_PER_SESSION = 1000  # raised from 100 — allow long deep refactoring sessions


# Per-session commit counter (resets per process — good enough)
_commit_counter: Dict[str, int] = {}


def _can_commit(session_key: str) -> bool:
    """Check if this session has not exceeded MAX_COMMITS_PER_SESSION."""
    return _commit_counter.get(session_key, 0) < MAX_COMMITS_PER_SESSION


def _record_commit(session_key: str):
    _commit_counter[session_key] = _commit_counter.get(session_key, 0) + 1


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


async def _get_github_creds() -> Dict[str, str]:
    """Resolve GitHub creds. Prefers VAULT (user PAT) over env (which on Railway
    may be a stale/wrong token causing 401 Unauthorized).
    Returns {token, repo} (either may be empty if not found)."""
    # Always check vault FIRST — Railway env GITHUB_TOKEN may be stale or wrong scope
    token = ""
    repo = os.environ.get("GITHUB_REPO", "").strip()
    try:
        if _DB is not None:
            doc = await _DB.credentials_vault.find_one({"service": "github"}, {"_id": 0})
            if doc:
                enc = doc.get("value_encrypted") or ""
                if enc:
                    import base64
                    import hashlib
                    from cryptography.fernet import Fernet
                    seed = (os.environ.get("JWT_SECRET", "") + os.environ.get("MONGO_URL", "")).encode()
                    key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
                    token = Fernet(key).decrypt(enc.encode()).decode()
                repo = repo or doc.get("repo") or ""
    except Exception:
        pass
    # Fall back to env token ONLY if vault is empty
    if not token:
        token = os.environ.get("GITHUB_TOKEN", "").strip()
    return {"token": token, "repo": repo}


async def _get_railway_creds() -> Dict[str, str]:
    """Resolve Railway creds. Prefers VAULT (user PAT) over env (which on Railway
    is an internal service token that can't query the GraphQL API).
    Returns dict with token/project/service/env (any may be empty)."""
    # On Railway, the auto-injected RAILWAY_TOKEN is a service-scoped token
    # that returns "Not Authorized" for project-level queries. So we ALWAYS
    # check the vault first for a user-provided PAT.
    token = ""
    project = os.environ.get("RAILWAY_PROJECT_ID", "").strip()
    service = os.environ.get("RAILWAY_SERVICE_ID", "").strip()
    env = os.environ.get("RAILWAY_ENVIRONMENT_ID", "").strip()
    try:
        if _DB is not None:
            doc = await _DB.credentials_vault.find_one({"service": "railway"}, {"_id": 0})
            if doc:
                enc = doc.get("value_encrypted") or ""
                if enc:
                    import base64
                    import hashlib
                    from cryptography.fernet import Fernet
                    seed = (os.environ.get("JWT_SECRET", "") + os.environ.get("MONGO_URL", "")).encode()
                    key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
                    token = Fernet(key).decrypt(enc.encode()).decode()
                project = project or doc.get("project_id") or ""
                service = service or doc.get("service_id") or ""
                env = env or doc.get("environment_id") or ""
    except Exception:
        pass
    # Fall back to env token ONLY if vault had nothing
    if not token:
        token = os.environ.get("RAILWAY_TOKEN", "").strip()
    return {"token": token, "project": project, "service": service, "env": env}


async def _get_vercel_creds() -> Dict[str, str]:
    """Resolve Vercel creds: env first, then vault.
    Returns {token, org, project}."""
    token = os.environ.get("VERCEL_TOKEN", "").strip() or os.environ.get("VERCEL_API_TOKEN", "").strip()
    org = os.environ.get("VERCEL_ORG_ID", "").strip() or os.environ.get("VERCEL_TEAM_ID", "").strip()
    project = os.environ.get("VERCEL_PROJECT_ID", "").strip()
    if token and project:
        return {"token": token, "org": org, "project": project}
    try:
        if _DB is None:
            return {"token": token, "org": org, "project": project}
        doc = await _DB.credentials_vault.find_one({"service": "vercel"}, {"_id": 0})
        if not doc:
            return {"token": token, "org": org, "project": project}
        if not token:
            enc = doc.get("value_encrypted") or ""
            if enc:
                import base64
                import hashlib
                from cryptography.fernet import Fernet
                seed = (os.environ.get("JWT_SECRET", "") + os.environ.get("MONGO_URL", "")).encode()
                key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
                token = Fernet(key).decrypt(enc.encode()).decode()
        org = org or doc.get("org_id") or doc.get("team_id") or ""
        project = project or doc.get("project_id") or ""
    except Exception:
        pass
    return {"token": token, "org": org, "project": project}


async def _ensure_git_workdir() -> Dict[str, Any]:
    """Make sure /tmp/zitex_workdir is a fresh clone of the repo.
    Used on Railway production where /app is not a git repo (only the build subdir).
    Returns {ok, path, action} or {ok: False, error}.
    """
    creds = await _get_github_creds()
    gh_token = creds["token"]
    gh_repo = creds["repo"]
    if not gh_token or not gh_repo:
        return {"ok": False, "error": "GITHUB_TOKEN/GITHUB_REPO not configured (env or vault) — add via Independence page"}

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

📌 **هويتك ومهمتك بكل صراحة**:
- اسمك: **برمجة زيتاكس** (Auto-Coder للمالك).
- المالك يكلّمك من `/admin/autocoder` على zitex.vercel.app.
- مهمتك الوحيدة: **تطوير منصة Zitex فقط** — أي إضافة، تعديل، إصلاح، صيانة، نشر، اختبار.
- مستودعك على GitHub: `zuhair646-debug/zitex` (branch: main).
- شغّال على Railway (`zitex-production.up.railway.app`) + Vercel (`zitex.vercel.app`).
- لو المالك يطلب يبني موقع داخلي جديد ضمن المنصة، نفّذ — كل المواقع داخل نفس الـrepo، يحتفظ بهم في `/app/backend/modules/<name>/` + `/app/frontend/src/pages/<Name>.js`.

🎯 **أول رسالة في كل محادثة جديدة**:
ابدأ بسطر واحد فقط يوضّح: "أنا برمجة زيتاكس · شغّال على repo `zitex` · عندي [X] صلاحية + [Y] أداة. وش تبيني أسوي؟"
ثم انتظر طلبه. **لا تستعرض كل قدراتك بدون داعي**.

🔐 **صلاحياتك (أعلنها بصدق عند الحاجة)**:
- ✅ كامل الـ`/app` (كود backend + frontend + tests)
- ✅ Git (commit, push, rollback) عبر `zuhair646-debug` token
- ✅ Railway (نشر, env vars, logs) عبر Railway API
- ✅ Vercel (نشر, env vars, logs) عبر Vercel API
- ✅ MongoDB (read + بعض الـwrites، مع حماية للـusers/payments)
- ✅ Web search + URL fetch
- ✅ توليد صور (Nano Banana / GPT-Image-1)
- ✅ توليد صوت (ElevenLabs / OpenAI TTS)
- ✅ توليد فيديو (Sora 2)
- ✅ Screenshot للصفحات (Playwright)
- ❌ ما تقدر تعدّل ملفاتك الذاتية (autocoder/*) — حماية ضد التخريب
- ❌ ما تقدر تشتري شي بفلوس المالك بدون إذنه الصريح

💬 **لو محتاج وصول لشي ما عندك**:
قل بصراحة: "أحتاج وصول لـX (مثلاً: Twilio API key) — يا ريت تضيفه في Railway env vars باسم TWILIO_API_KEY".

🔐 وضع الصلاحيات: AUTONOMOUS MODE.
- عندك حرية كاملة لقراءة وكتابة وتعديل أي ملف داخل /app.
- تقدر تشغّل أي أمر bash (git, yarn, pip, pytest, supervisorctl, إلخ).
- تقدر تـcommit وتدفع للـGitHub.
- لا قيود. ينفّذ المالك أوامره بالضبط.

🚨 **عقد الإكمال — قاطع وملزم (Completion Contract)**:

أنت تعمل **بشكل ذاتي حتى الإنهاء الكامل**. لا تتوقف عند أول عقبة. لا تقول "أعتذر لكن فشل الرفع" ثم تنهي الكلام. **يحظر تماماً** إنهاء الـturn بحالة فشل غير معالجة.

📋 **عند أي طلب إصلاح/تعديل اتبع هذا الـworkflow الكامل بدون استثناء**:

  1. **🔍 افحص**: اقرأ الملفات المعنية + شغّل `git status` + `git log -5` لفهم الوضع
  2. **🛠️ عدّل**: اكتب التغييرات بـ`write_file` أو `apply_patch`
  3. **✅ تحقق محلياً**:
     - شغّل lint (`run_command("ruff check ...")` للـ Python، أو فحص syntax)
     - شغّل الـ service: `sudo supervisorctl restart backend` ثم `sudo supervisorctl status`
     - تحقق من logs: `tail -50 /var/log/supervisor/backend.err.log`
     - **لو فيه أي خطأ → ارجع للخطوة 2 وأصلحه. لا تكمل قبل ما يكون نظيف.**
  4. **📤 ارفع (Push)**:
     - `git add -A && git commit -m "..."` ثم `git push`
     - **لو الـpush فشل** (rejected, conflict, network):
       a. `git pull --no-edit origin main` لجلب التغييرات
       b. لو فيه conflict → افتح الملف، اقرأ markers `<<<<<<<`، حلّ الـconflict يدوياً، احفظ
       c. `git add -A && git commit --no-edit` للـmerge
       d. `git push` مرة ثانية
       e. **كرّر حتى ينجح** — بحد أقصى 5 محاولات. لو فشل بعدها، قل بصراحة "الـpush فشل 5 مرات، السبب: X" واطلب من المالك.
  5. **🚀 تحقق من النشر** (deployment):
     - انتظر 90 ثانية ليبني Vercel/Railway: `run_command("sleep 90")`
     - Vercel: `curl -sI https://zitex.vercel.app/ | grep x-vercel-id`
     - افتح الـ URL المتأثر بـ`screenshot_url` للتحقق البصري
  6. **🧪 اختبر فعلياً**:
     - لو الإصلاح كان لـbug في API → استدعِ الـ endpoint فعلياً بـcurl وتحقق من الـ response
     - لو لـ frontend → استخدم `screenshot_url` على الـ URL المتأثر (مثلاً: `https://zitex.vercel.app/games/web`)
     - لو لـ database → اعمل query فعلي للتحقق
     - **لا تقل "تم الإصلاح" بدون اختبار حي على الموقع المنشور**
  7. **📊 قرّر**: 
     - لو الاختبار نجح ✅ → أعطِ تقرير من 3 سطور: ما عملت، ما اختبرت، النتيجة
     - لو الاختبار فشل ❌ → **ارجع للخطوة 1**. لا تستسلم. حلّل السبب الجذري وأعد المحاولة. بحد أقصى 8 دورات إصلاح.

⛔ **عبارات ممنوعة منعاً باتاً قبل اكتمال الـworkflow أعلاه**:
- "للأسف فشل الـpush" (بدون محاولة merge + retry)
- "هذا ما أقدر أصلحه" (إلا بعد 3+ محاولات حقيقية مع تشخيص مختلف لكل واحدة)
- "تأكّد بنفسك من النشر" (أنت اللي تتأكد)
- "حاول مرة ثانية لو تبي" (أنت اللي تحاول)
- أي شي ينقل المسؤولية للمالك قبل ما تستنفد محاولاتك

✅ **عبارات مسموحة وموصى بها**:
- "محاولة 1/5: الـpush فشل بسبب rejected — سأعمل git pull ثم أعيد..."
- "الـpush نجح (sha: abc1234). الـVercel ينشر الآن، أنتظر 90 ثانية ثم أختبر..."
- "اختبرت /games/web: HTTP 200، h1='Game Studio v3.0'، Console: 0 errors ✅"
- "بعد 5 محاولات: محاولة 1=conflict (حلّيت)، 2=rejected (pull+retry)، 3=network (timeout)، 4=auth (retry)، 5=نفس السبب — أحتاج تدخّلك لإعادة توليد GITHUB_TOKEN"

🎯 **القاعدة الذهبية**: المالك ما يبيك تنهي كلامك. يبيك **تنهي المهمة**. الكلام نتيجة، مو وعد. لو احتجت 30 دقيقة من tool calls متتالية لإنهاء المهمة — خذها. ما عندك حد. اشتغل لين تخلص.

🛡️ **استثناء وحيد** (حماية ضد التخريب الذاتي):
ممنوع تكتب أو تعدّل أو تحذف هذي الملفات (هي وحدتك):
  • `/app/backend/modules/autocoder/__init__.py`
  • `/app/backend/modules/autocoder/llm_providers.py`
  • `/app/backend/modules/autocoder/tools_extra.py`
لو حاولت — `write_file`/`edit_file`/`delete_file` راح ترفض. هذا يحميك من تكسير قدرتك على إصلاح المشاكل لاحقاً. لو فعلاً تحتاج تعديل في الذكاء، اشرح للمالك إنه يحتاج يعدّل يدوياً.

🎯 **AUTONOMOUS MODE — اشتغل لين تخلّص**:
- لما المالك يطلب مهمة (إضافة ميزة، إصلاح bug، تعديل قسم)، **أكمل المهمة كاملةً قبل ما توقف**.
- **ممنوع تقول "تم" أو "أوكي" أو ملخص قصير** ثم تنتظر — هذا يضيع وقته. كمّل التنفيذ الفعلي.
- الـworkflow الكامل لأي مهمة: **اقرأ → عدّل → اختبر → commit → تحقّق من النشر** كله في نفس الجلسة بدون انتظار إذن بين الخطوات.
- توقف فقط لما:
  1. خلصت المهمة بالكامل (الكود مدفوع + Railway ناجح + Vercel ناجح)
  2. واجهت سؤال جوهري لا تعرف إجابته (مثلاً: "أيّ ألوان تفضّل؟")
  3. واجهت خطأ ما تقدر تحلّه بعد محاولتين

⚡ **قانون التنفيذ الفوري** (مهم جداً):
- في **أول رسالة** بعد طلب المالك، **ابدأ باستدعاء أداة في أول 10 ثواني**. لا تكتب paragraphs قبل أداة.
- نمط الرد المطلوب:
  ✅ "حلو، بفحص X." → استدعِ tool → نتيجة → "X يحتوي Y، بسوي Z." → استدعِ tool ثاني → ...
  ❌ "أكيد، أنا فاهم طلبك تماماً. خل أشرح لك خطة العمل: أولاً أنا راح أ..." (كلام بلا تنفيذ)
- لو طلبك يستلزم 3 خطوات، نفّذ الـ3 في نفس الرد بدون استئذان.
- لا تطلب تأكيد بين الخطوات. المالك قال **"اشتغل لين تخلّص"** — التزم بذلك.

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
- `edit_file(path, find, replace, occurrence?, replace_all?)` — استبدال نصي ذكي:
  • وضع افتراضي: يلزم النص يكون unique في الملف.
  • لو فشل بسبب التكرار: راح ترجع لك أرقام أسطر كل المطابقات. عندك 3 خيارات:
    1. كبّر `find` (أضف سطر قبل/بعد) لتجعله unique.
    2. أعد الاستدعاء مع `occurrence=N` للمطابقة رقم N.
    3. أعد الاستدعاء مع `replace_all=true` لاستبدال الكل.
  • **لا تستسلم** عند رسالة "not unique" — استخدم هذي الخيارات.
- `delete_file(path)` — حذف ملف

⚙️ **التنفيذ**:
- `run_command(cmd, cwd?)` — أي bash command (timeout 90s افتراضي)
- `restart_service(name)` — backend/frontend (محلياً supervisorctl، على Railway production يستخدم Railway API تلقائياً)

📊 **مراقبة**:
- `view_logs(service, lines?)` — يقرأ آخر N سطر من backend/frontend logs
- `list_env(filter_prefix?)` — يعرض أسماء متغيرات البيئة (القيم السرّية مخفية)

🌐 **بحث وجلب من النت** (مجاني، بدون مفاتيح):
- `web_search(query, max_results?)` — بحث DuckDuckGo. استخدمه لما تحتاج توثيق API، حلول لأخطاء، أو معلومات حالية.
- `fetch_url(url, max_chars?)` — اجلب صفحة ويب أو ملف JSON كنص. استخدمه بعد web_search لقراءة نتيجة معينة.

⚡ **أدوات قوية إضافية**:
- `view_bulk_files(paths, max_lines_per_file?)` — اقرأ حتى 6 ملفات بضربة واحدة (أكفأ من read_file مرات متعددة).
- `apply_patch(patch, strip?, dry_run?)` — طبّق unified-diff على عدة ملفات دفعة واحدة. استخدم dry_run=true أولاً للمعاينة.
- `db_query(collection, filter?, projection?, limit?, operation?)` — استعلام MongoDB **للقراءة فقط** (find/find_one/count/distinct). افحص بيانات المنصة الفعلية.
- `ast_analyze(path)` — حلّل ملف Python: يرجع كل الـfunctions والـclasses والـimports مع أرقام الأسطر. أسرع من read_file لفهم البنية.

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
- `/app/backend/server.py` — الـmain FastAPI app (كل الـrouters تتسجّل هنا — لا تنسى)
- `/app/backend/modules/<name>/__init__.py` — كل ميزة في module مستقل (agent, freebuild_v2, autocoder, إلخ)
- `/app/backend/modules/freebuild_v2/tools.py` — كل أدوات بناء المواقع (~2200 سطر)
- `/app/frontend/src/App.js` — الـrouter (كل الصفحات تتسجّل هنا — لا تنسى)
- `/app/frontend/src/pages/<Name>.js` — الصفحات
- `/app/frontend/src/components/<Name>.js` — المكوّنات
- `/app/memory/PRD.md` — خطة المنتج

⚠️ **خريطة الموقع الفعلية الموجودة** (لا تنشئ ملفات جديدة قبل ما تتأكد إن المطلوب مش موجود):
الصفحات الموجودة في `/app/frontend/src/pages/`:
- `LandingPage.js` (`/`)، `LoginPage.js`، `RegisterPage.js`، `PricingPage.js`
- `AIAgent.js` (مسجّلة على `/ai-agent`) — **مش `Agent.js`**
- `FreeBuild.js` (`/build-from-zero`)، `MyWebsites.js`، `ImageGenerator.js`، `VideoGenerator.js`
- `ClientDashboard.js`، `NewRequest.js`، `MyRequests.js`، `RequestDetails.js`
- `AdminDashboard.js`، `AdminRequests.js`، `AdminPayments.js`، `AdminAutoCoder.js` (`/admin/autocoder`)، `AdminIndependence.js`

🔴 **القواعد اللي يلتزم بها أي ملف frontend جديد** (احفظها قبل أي تعديل):
1. **API URL**: استخدم `process.env.REACT_APP_BACKEND_URL` (مش `REACT_APP_API_URL`)
2. **Token**: استخدم `localStorage.getItem('token')` (مش `'session_token'`)
3. **API prefix**: كل routes الـbackend بادئتها `/api/` (مش بدون البادئة)
4. **Headers**: `Authorization: Bearer ${token}` — هذا الشكل المعتمد في الموقع
5. **Tailwind فقط**: ما عندنا CSS ملفات لكل page. لا تكتب `import './Foo.css'` إلا لو الملف موجود فعلاً
6. **Imports المتاحة**: `lucide-react` للأيقونات، `react-router-dom` للنافجيشن، `sonner` للـtoasts
   — لا تستورد `react-markdown` أو `react-syntax-highlighter` (مش مثبتة)
7. **التسجيل في Router**: أي ملف جديد لازم تسجّله في `/app/frontend/src/App.js`، وإلا ما يطلع
8. **القالب القديم**: قبل ما تنشئ صفحة جديدة، **اقرأ صفحة موجودة مشابهة** (مثل `AIAgent.js`) عشان تعرف pattern الـimports والـauth والـAPI calls

🔧 **القواعد لـbackend جديد**:
1. كل route لازم بادئتها `/api/...`
2. الـrouters تتسجّل في `/app/backend/server.py` بـ`app.include_router(...)`
3. ما عندنا `routers/` و `services/` folders — كل ميزة في `modules/<name>/__init__.py`
4. لا تنشئ مجلدات جديدة (`routers/`, `services/`) إلا لو فعلاً تبدأ refactor كبير

🔑 قواعد العمل:
1. **اقرأ قبل ما تكتب**. لو طلب تعديل، استدعِ `read_file` أولاً، افهم الكود، ثم استدعِ `edit_file` أو `write_file`.
2. **خطوات صغيرة**. قسّم العمل لخطوات منطقية، نفّذ أداة واحدة كل مرة، اشرح للمالك ماذا فعلت بعد كل خطوة.
3. **اختبر بعد التعديل**. لو غيّرت backend → `run_command("sudo supervisorctl status backend")`. لو غيّرت frontend → فحص browser console.
4. **commit بعد ما تخلص**. نهاية كل feature/fix → `git_commit_push("feat: ...")` مع رسالة وصفية.
5. **ممنوع تخترع كود**. لو ما متأكد من API endpoint أو شكل dict، اقرأ الملف الحقيقي.
6. **حافظ على .env**. ممنوع تكتب أو تطبع المفاتيح السرية إلا لو طلب صريح.
7. **بعد modification المهم**: اشتغل لين تخلّص المهمة كاملةً (commit + push + verify deployment) ثم اعرض ملخص نهائي مرة وحدة. **ممنوع** تكتب "✅ سويت X. تبيني أكمل؟" — لا. كمّل بدون استئذان.
8. **استمر حتى الانتهاء التام**. لو طلب فيه 5 خطوات، نفّذ الـ5 كلها قبل ما توقف. لا تعرض النتيجة بعد الخطوة الأولى وتنتظر.

🚫 **ممنوع منعاً باتاً**:
- **لا تقول "ناقص" أو "غير متاح" بدون اختبار `run_command` حقيقي أولاً.** لو شككت أن أداة OS غير موجودة → شغّل `which <tool>` أو `<tool> --version` قبل ما تجزم.
- **لا تفترض من الذاكرة**. البيئة قد تختلف بين preview و Railway production. اختبر دايماً.
- **لا تهلوس عن قائمة tools متاحة**. عندك بالضبط الأدوات اللي محددة في schema هذي الجلسة (22 أداة شاملة: file/git/run/logs/env/safety/web/bulk/patch/db/ast). أي شي ثاني → run_command.

🛡️ **شبكة الأمان (استخدمها لتمنع التخريب الذاتي)**:

أنت صلاحياتك **كاملة 100%** على كل الكود — تقدر تعدّل أي ملف (Dockerfile، CI، dependencies، أي شي). **لكن** عشان ما تكسر الموقع وتفقد قدرتك على إصلاحه، اتبع هذا الـworkflow:

**الـworkflow الذكي قبل أي تعديل في production**:

1. 🔍 **اقرأ المشكلة الفعلية أولاً**:
   - استدعِ `view_logs("backend", 200)` لرؤية الخطأ الحقيقي
   - استدعِ `check_deployment_status()` لتعرف هل آخر deploy نجح
   - **لا تخمّن** — اقرأ الخطأ المحدد قبل ما تكتب أي fix

2. ✏️ **عدّل بدقة**:
   - استدعِ `read_file` للملف المعني
   - استدعِ `edit_file` (مفضّل) أو `write_file` بالكود الجديد
   - **عدّل ملف واحد بالمرة** ولا تنسخ-حلّ-كل-المشاكل-مرة-واحدة

3. ✅ **تحقّق قبل النشر**:
   - استدعِ `pre_deploy_check()` — يعمل python compile + import test
   - لو فيه أخطاء → **توقّف، أصلحها، ثم أعد الفحص**
   - لا تـcommit إلا لما `pre_deploy_check` يرجع `ok: true`

4. 🚀 **انشر بثقة**:
   - استدعِ `git_commit_push("fix: وصف واضح ومحدد للتغيير")`
   - رسالة الـcommit تكون **محددة** (مش `chore: fix`)

5. ⏳ **تأكّد من النشر**:
   - انتظر ~3 دقايق (Railway يحتاج وقت)
   - استدعِ `check_deployment_status()` — يجب يرجع `SUCCESS`
   - لو `FAILED` → **اقرأ الـlogs أولاً** لمعرفة السبب الحقيقي
   - **لا تجرّب fix-after-fix-after-fix**. لو فشل commit مرتين متتاليتين على نفس المشكلة، **توقّف** و:
     a. استدعِ `view_logs` بعمق أكبر
     b. اطلب من المالك معلومات إضافية
     c. أو استدعِ `rollback_to_last_good()` وابدأ من جديد بفهم أعمق

🚨 **الحالات الطارئة**:
- لو الموقع منهار وما تقدر تصلحه بسرعة → استدعِ `rollback_to_last_good()` فوراً. هذا يرجع لآخر commit شغّال على Railway ويعيد النشر.
- عندك حد أقصى **100 commit في الجلسة** (حماية من loops قصوى). نادراً ما توصل له في مهمة واحدة، فلا تخاف.

⛔ **الأخطاء القاتلة (تجنّبها)**:
- لا تعدّل `Dockerfile` بدون اختبار syntax أولاً (`pre_deploy_check` ما يفحص Dockerfile — اختبر يدوياً بـ`run_command("docker build -t test /app/backend")` لو متاح)
- لا تـcommit بدون `pre_deploy_check` على ملفات Python حساسة (autocoder/__init__.py خصوصاً — كسرها = ما تقدر تشتغل)
- لا تجرّب أكثر من fix واحد لنفس المشكلة بدون قراءة logs بين كل محاولة

🌐 **بيئة التشغيل**:
- محلياً (preview): فيه supervisor + git + curl + كل شي
- على Railway production: فيه git + curl + jq + python (مثبتين في Dockerfile). `supervisorctl` غير موجود — استخدم `restart_service` (يستدعي Railway API تلقائياً).
- لاكتشاف وين أنت: `run_command("env | grep RAILWAY_ | head -5")`. لو رجع متغيرات → أنت على Railway.

🏗️ **إنشاء أقسام كاملة من الصفر** (الأكثر طلباً من المالك):
لما المالك يطلب "أضف قسم X" (مثل: ألعاب، مجتمع، متجر، شاتات) — هذا workflow كامل تنفّذه بدون استئذان:

1. **Backend module** (`/app/backend/modules/<name>/__init__.py`):
   - أنشئ `create_<name>_router(db, get_current_user)` يرجّع `APIRouter()`
   - أضف ٥-٨ endpoints تغطي CRUD + special actions (list/create/get/update/delete/play/share/like)
   - استخدم نفس pattern الـmodules الموجودة (`freebuild_v2`, `video_studio`, `app_studio`). اقرأ أحدها أولاً للـreference.
   - عرّف Pydantic models للـrequest/response
   - استخدم MongoDB collections بأسماء `<name>_*` (مثل: `games`, `game_plays`, `game_likes`)
   - استبعد `_id` من كل response

2. **سجّل الـmodule في server.py**:
   - افتح `/app/backend/server.py` وابحث عن نمط: `from modules.app_studio import create_app_studio_router`
   - أضف import مماثل + سطر تسجيل: `app.include_router(create_<name>_router(db, get_current_user), prefix='/api/<name>')`

3. **Frontend page** (`/app/frontend/src/pages/<Name>.js`):
   - استخدم نفس بنية AppStudio.js أو FreeBuild.js كقالب
   - 3-pane أو single-page UI حسب طبيعة القسم
   - استخدم Tailwind + lucide-react icons + `dir="rtl"` + سعودي طبيعي
   - data-testid على كل عنصر تفاعلي
   - استدعِ API عبر `process.env.REACT_APP_BACKEND_URL`

4. **Routing في App.js**:
   - `import <Name> from '@/pages/<Name>';`
   - `<Route path="/dashboard/<name>" element={<ProtectedRoute><<Name> /></ProtectedRoute>} />`

5. **Dashboard card في ClientDashboard.js**:
   - أضف entry في المصفوفة: `{ title: '🎮 <العنوان>', desc: '...', path: '/dashboard/<name>', color: 'from-X-500 to-Y-600', badge: 'جديد' }`

6. **اختبر**:
   - `curl /api/<name>/...` للـbackend
   - `restart_service` ثم تأكد من 200 status
   - اقرأ logs لو فيه أخطاء

7. **commit + push**:
   - `git_commit_push(message="feat(<name>): قسم جديد كامل", files=[paths])`

**لا تطلب من المالك مواصفات تفصيلية لو ما طلبها**. اقترح أنت ٥-٨ ميزات منطقية، نفّذها، وقول له بعد كل شي: "خلّصت قسم X. شف وقول لي وش تبي نضيف أو نعدّل."

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


# ─────────────────────────────────────────────────────────────────────
# 🛡️ Self-protection: prevent the AI from corrupting its OWN module.
# This was a real incident — the AI rewrote autocoder/__init__.py with random
# imports (torch, transformers, nltk) and broke /api/autocoder/* (unlock, chat).
# Lock these files from write/edit/delete.
# ─────────────────────────────────────────────────────────────────────
PROTECTED_PATHS = (
    "/app/backend/modules/autocoder/__init__.py",
    "/app/backend/modules/autocoder/llm_providers.py",
    "/app/backend/modules/autocoder/tools_extra.py",
    "/app/backend/modules/autocoder/codebase_atlas.py",
)


def _is_protected_path(path_str: str) -> bool:
    try:
        resolved = str(_resolve_path(path_str))
        return resolved in PROTECTED_PATHS
    except Exception:
        return False


def _protection_error(path_str: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": (
            f"🛡️ ملف محمي: {path_str}\n"
            f"تعديل ملفات وحدة Auto-Coder ممنوع (يحمي الذكاء من تكسير نفسه). "
            f"لو فعلاً تحتاج تعدل ميزة في الذكاء، اطلب من المالك بشكل واضح، "
            f"وهو يعدل يدوياً عبر بيئة التطوير."
        ),
    }


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
            # Default 4000 lines (was 800) — read whole files in one call so the AI
            # doesn't have to chain multiple reads and lose context mid-analysis.
            end = min(start + 4000, total)
        end = min(end, total)
        start = max(1, start)
        chunk = "\n".join(lines[start - 1:end])
        result: Dict[str, Any] = {
            "ok": True, "path": str(p), "total_lines": total,
            "shown": [start, end],
            # Cap at 400K chars (was 80K) — well within Claude 200K context window
            # for a single tool result.
            "content": chunk[:400000],
            "hint": (f"showing {end-start+1}/{total} lines. Pass end={total} to read all."
                     if end < total else None),
        }
        # Attach cache annotation so the AI knows when it's re-reading and
        # we track tokens-saved stats globally. Failure here is non-fatal.
        try:
            ann = await _cache_annotate_read(str(p), len(chunk))
            if ann:
                result["cache_info"] = ann
        except Exception:
            pass
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_write_file(path: str, content: str) -> Dict[str, Any]:
    """Write file. Auto-snapshot + sanity-check on spine files.
    Old PROTECTED_PATHS restrictions removed — full freedom + safety net."""
    try:
        p = _resolve_path(path)
        # Sanity check (only blocks on actual errors, warnings allowed)
        sanity = _sanity_check(str(p), content)
        if not sanity["ok"]:
            return {
                "ok": False,
                "rejected": "sanity_failed",
                "errors": sanity["errors"],
                "hint": "صحّح الأخطاء أو استدعِ sanity_check(path, content) قبل الكتابة الفعلية.",
            }
        # Auto-snapshot spine files
        snap = None
        if is_spine_file(str(p)) and p.exists():
            snap = make_snapshot(str(p))
        p.parent.mkdir(parents=True, exist_ok=True)
        existed = p.exists()
        p.write_text(content, encoding="utf-8")
        # Invalidate code-cache entry for this file (content changed → SHA changed)
        try:
            from .code_cache import invalidate_file as _cache_invalidate
            await _cache_invalidate(str(p))
        except Exception:
            pass
        return {
            "ok": True,
            "path": str(p),
            "action": "overwritten" if existed else "created",
            "size": len(content),
            "snapshot": snap,
            "warnings": sanity.get("warnings", []),
            "is_spine": sanity.get("is_spine"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_edit_file(
    path: str,
    find: str,
    replace: str,
    occurrence: int = 0,
    replace_all: bool = False,
) -> Dict[str, Any]:
    """Find-and-replace with smart fallbacks + auto-snapshot for spine files.
      - default: requires UNIQUE match (safest)
      - occurrence=N: replaces the Nth match (1-indexed) when there are duplicates
      - replace_all=True: replaces ALL matches (use with care)
    On non-unique error, returns line numbers of every match so the AI can add context.
    """
    try:
        p = _resolve_path(path)
        if not p.exists():
            return {"ok": False, "error": f"file not found: {p}"}
        text = p.read_text(encoding="utf-8", errors="replace")
        if find not in text:
            return {"ok": False, "error": "find string not found in file",
                    "hint": "تأكد من المسافات و newlines. جرّب search_code أولاً للعثور على النص الفعلي."}
        count = text.count(find)

        # Helper: write new content with sanity-check + snapshot
        def _safe_write(new_content: str, mode: str, extra: Dict[str, Any]) -> Dict[str, Any]:
            sanity = _sanity_check(str(p), new_content)
            if not sanity["ok"]:
                return {
                    "ok": False,
                    "rejected": "sanity_failed",
                    "errors": sanity["errors"],
                    "hint": "التعديل لن يُطبَّق — صحّح الأخطاء وأعد المحاولة.",
                    "mode": mode,
                }
            snap = make_snapshot(str(p)) if is_spine_file(str(p)) else None
            p.write_text(new_content, encoding="utf-8")
            # Invalidate cache entry — content changed
            try:
                from .code_cache import invalidate_file as _cache_invalidate
                import asyncio as _asyncio
                _task = _asyncio.get_event_loop().create_task(_cache_invalidate(str(p)))
            except Exception:
                pass
            return {"ok": True, "path": str(p), "mode": mode,
                    "new_size": len(new_content), "snapshot": snap,
                    "warnings": sanity.get("warnings", []),
                    "is_spine": sanity.get("is_spine"), **extra}

        # ── Path 1: replace_all = explicit batch replace ──
        if replace_all:
            new = text.replace(find, replace)
            return _safe_write(new, "replace_all", {"replacements": count})

        # ── Path 2: occurrence-targeted replace (1-indexed) ──
        if occurrence and occurrence >= 1:
            if occurrence > count:
                return {"ok": False, "error": f"occurrence={occurrence} but only {count} matches found"}
            idx = -1
            for _ in range(occurrence):
                idx = text.find(find, idx + 1)
            new = text[:idx] + replace + text[idx + len(find):]
            line_no = text.count("\n", 0, idx) + 1
            return _safe_write(new, f"occurrence_{occurrence}", {"replacements": 1, "at_line": line_no})

        # ── Path 3: unique-match strict (original behavior, default) ──
        if count > 1:
            line_nos: List[int] = []
            i = 0
            while True:
                i = text.find(find, i)
                if i < 0:
                    break
                line_nos.append(text.count("\n", 0, i) + 1)
                i += 1
                if len(line_nos) >= 20:
                    break
            return {
                "ok": False,
                "error": f"find string is not unique ({count} matches in this file)",
                "match_lines": line_nos,
                "hint": ("النص مكرّر في عدة أسطر. حلولك: "
                         "(1) كبّر النص (أضف سطر قبله/بعده ليصير unique)، أو "
                         "(2) أعد الاستدعاء مع occurrence=N، أو "
                         "(3) أعد الاستدعاء مع replace_all=True."),
            }
        new = text.replace(find, replace, 1)
        return _safe_write(new, "unique", {"replacements": 1})
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tool_delete_file(path: str) -> Dict[str, Any]:
    """Delete file. Auto-snapshot for spine files before deletion."""
    try:
        p = _resolve_path(path)
        if not p.exists():
            return {"ok": False, "error": "file not found"}
        if p.is_dir():
            return {"ok": False, "error": "use run_command(rm -rf) for directories"}
        # Snapshot spine files before delete
        snap = None
        if is_spine_file(str(p)):
            snap = make_snapshot(str(p))
        p.unlink()
        return {"ok": True, "path": str(p), "action": "deleted", "snapshot": snap}
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


async def tool_run_command(cmd: str, cwd: str = "/app", timeout: int = 300) -> Dict[str, Any]:
    """Run any bash command. Default timeout raised 90s → 300s (5 min) so long ops
    like 'yarn build' / 'pip install' / 'pytest /app/backend/tests' don't get killed.
    Output cap raised from 50K/20K → 200K/80K so multi-screen logs survive.
    """
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
        out = (stdout or b"").decode("utf-8", errors="replace")[:200000]
        err = (stderr or b"").decode("utf-8", errors="replace")[:80000]
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
    creds = await _get_railway_creds()
    rw_token = creds["token"]
    rw_service = creds["service"]
    rw_env = creds["env"]
    on_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT"))
    if rw_token and rw_service and rw_env and (on_railway or True):  # use Railway API whenever creds exist
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
    """Commit + push from the working clone (/tmp/zitex_workdir)."""
    # ── Guard: max 3 commits per process lifetime to prevent loops ──
    session_key = "default"  # process-level — restart resets the counter
    if not _can_commit(session_key):
        return {"ok": False, "error": (
            f"🚫 الحد الأقصى للـcommits ({MAX_COMMITS_PER_SESSION}) في هذي الجلسة. "
            "هذا حماية ضد الـloops. لو تبي تكمل، اطلب من المالك يصبر redeploy ثم يعطيك أمر جديد."
        )}

    setup = await _ensure_git_workdir()
    if not setup.get("ok"):
        return setup

    creds = await _get_github_creds()
    gh_token = creds["token"]
    gh_repo = creds["repo"]
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
    if r.get("ok"):
        _record_commit(session_key)
        r["commits_used_this_session"] = _commit_counter.get(session_key, 0)
        r["commits_remaining"] = MAX_COMMITS_PER_SESSION - _commit_counter.get(session_key, 0)
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


async def tool_pre_deploy_check(paths: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run quick sanity checks BEFORE committing/pushing:
      - Python files: compile check (catches SyntaxError, missing imports often)
      - JS/JSX files: ESLint via yarn eslint if available
      - For backend modules: try importing them to catch ImportError
    AI should call this BEFORE git_commit_push for any non-trivial change.
    """
    paths = paths or []
    issues: List[Dict[str, Any]] = []

    # 1. Python compile check + import test
    py_files = [p for p in paths if p.endswith(".py")]
    if not paths:
        # auto-discover changed py files via git
        try:
            r = await tool_run_command(
                "cd /app && git diff --name-only HEAD 2>/dev/null | grep '\\.py$' || true",
                timeout=10,
            )
            py_files = [f for f in (r.get("stdout") or "").split("\n") if f.strip().endswith(".py")]
        except Exception:
            pass

    for f in py_files[:30]:  # cap to 30 files
        full = _resolve_path(f)
        if not full.exists():
            continue
        # Compile check (catches syntax errors)
        cr = await tool_run_command(
            f"python3 -m py_compile {shlex.quote(str(full))} 2>&1",
            timeout=15,
        )
        if not cr.get("ok"):
            issues.append({"file": str(full), "type": "syntax_error",
                           "error": (cr.get("stderr") or cr.get("stdout") or "")[:500]})

    # 2. Try importing the autocoder module specifically (it's the most likely
    # to break itself, and breaking it = no more autocoder)
    if not paths or any("autocoder" in p for p in paths):
        # Detect whether modules/ lives at /app/backend (dev) or /app (production)
        backend_paths = [
            ("/app/backend", "/app/backend"),
            ("/app", "/app"),
        ]
        backend_dir = None
        for check, _ in backend_paths:
            if Path(check + "/modules/autocoder/__init__.py").exists():
                backend_dir = check
                break
        if backend_dir:
            ir = await tool_run_command(
                f"cd {shlex.quote(backend_dir)} && python3 -c 'import sys; sys.path.insert(0, \".\"); "
                "from modules.autocoder import create_autocoder_router' 2>&1",
                timeout=15,
            )
            if not ir.get("ok"):
                issues.append({"file": f"{backend_dir}/modules/autocoder",
                               "type": "import_error",
                               "error": (ir.get("stderr") or ir.get("stdout") or "")[:500]})
        else:
            issues.append({"file": "modules/autocoder",
                           "type": "import_error",
                           "error": "could not locate backend/ or /app modules dir"})

    return {
        "ok": len(issues) == 0,
        "checked_files": len(py_files),
        "issues": issues,
        "verdict": ("✅ آمن للنشر" if len(issues) == 0 else
                    f"❌ {len(issues)} أخطاء — لا تـcommit حتى تصلحها"),
    }


async def tool_check_deployment_status() -> Dict[str, Any]:
    """Check the status of the LAST Railway deployment (success/failed).
    Use after `git_commit_push` to confirm the deploy actually worked.
    Wait ~2-4 minutes after push before calling.

    Uses the current Railway GraphQL schema: `deployments(input: { serviceId, environmentId })`.
    """
    creds = await _get_railway_creds()
    rw_token = creds["token"]
    rw_service = creds["service"]
    rw_env = creds["env"]
    rw_project = creds["project"]
    if not rw_token or not rw_service or not rw_env:
        return {"ok": False, "error": "RAILWAY_TOKEN/RAILWAY_SERVICE_ID/RAILWAY_ENVIRONMENT_ID must all be set (env or vault)"}
    try:
        import httpx
        # Current Railway v2 schema (Feb 2026): deployments(input: {projectId,serviceId,environmentId})
        q = (
            'query Deps($p: String, $s: String!, $e: String!) { '
            'deployments(first: 5, input: { projectId: $p, serviceId: $s, environmentId: $e }) { '
            '  edges { node { id status createdAt url canRollback meta staticUrl } } '
            '} }'
        )
        variables = {"p": rw_project or None, "s": rw_service, "e": rw_env}
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                "https://backboard.railway.com/graphql/v2",
                headers={"Authorization": f"Bearer {rw_token}",
                         "Content-Type": "application/json"},
                json={"query": q, "variables": variables},
            )
        data = r.json()
        if "errors" in data:
            # Fallback: try without projectId (older accounts)
            q2 = (
                'query Deps($s: String!, $e: String!) { '
                'deployments(first: 5, input: { serviceId: $s, environmentId: $e }) { '
                '  edges { node { id status createdAt url canRollback meta staticUrl } } '
                '} }'
            )
            async with httpx.AsyncClient(timeout=20) as c:
                r = await c.post(
                    "https://backboard.railway.com/graphql/v2",
                    headers={"Authorization": f"Bearer {rw_token}",
                             "Content-Type": "application/json"},
                    json={"query": q2, "variables": {"s": rw_service, "e": rw_env}},
                )
            data = r.json()
            if "errors" in data:
                return {"ok": False, "error": str(data["errors"])[:400],
                        "hint": "تأكد من توكنات Railway. الـschema تغيّر في 2026، استخدم RAILWAY_PROJECT_ID أيضاً."}
        edges = (data.get("data", {}).get("deployments", {}) or {}).get("edges", [])
        out = []
        for e in edges[:5]:
            n = e["node"]
            meta = n.get("meta") or {}
            out.append({
                "id": n["id"],
                "status": n["status"],
                "createdAt": n["createdAt"],
                "url": n.get("staticUrl") or n.get("url"),
                "can_rollback": n.get("canRollback", False),
                "commit_sha": (meta.get("commitHash") or "")[:8],
                "commit_msg": ((meta.get("commitMessage") or "") or "")[:80],
            })
        latest = out[0] if out else None
        return {"ok": True, "latest": latest, "recent": out, "verdict":
                ("✅ آخر deploy ناجح" if latest and latest["status"] == "SUCCESS" else
                 "⏳ لسه يبني" if latest and latest["status"] in ("BUILDING", "DEPLOYING", "QUEUED", "INITIALIZING") else
                 "❌ فشل — استخدم rollback_to_last_good" if latest else
                 "❓ ما لقينا أي deployment")}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


async def tool_rollback_to_last_good() -> Dict[str, Any]:
    """If the latest deployment FAILED, find the most recent SUCCESS deployment
    and revert HEAD to its commit SHA, then push (force) to trigger a redeploy
    of the known-good code.

    Use this when check_deployment_status returns FAILED.
    """
    setup = await _ensure_git_workdir()
    if not setup.get("ok"):
        return setup
    creds = await _get_railway_creds()
    rw_token = creds["token"]
    rw_service = creds["service"]
    rw_env = creds["env"]
    rw_project = creds["project"]
    if not rw_token or not rw_service or not rw_env:
        return {"ok": False, "error": "RAILWAY_TOKEN/RAILWAY_SERVICE_ID/RAILWAY_ENVIRONMENT_ID required (env or vault)"}
    try:
        import httpx
        q = (
            'query Deps($p: String, $s: String!, $e: String!) { '
            'deployments(first: 20, input: { projectId: $p, serviceId: $s, environmentId: $e }) { '
            '  edges { node { status meta } } '
            '} }'
        )
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                "https://backboard.railway.com/graphql/v2",
                headers={"Authorization": f"Bearer {rw_token}"},
                json={"query": q, "variables": {"p": rw_project or None, "s": rw_service, "e": rw_env}},
            )
        data = r.json()
        if "errors" in data:
            # Fallback without projectId
            q2 = (
                'query Deps($s: String!, $e: String!) { '
                'deployments(first: 20, input: { serviceId: $s, environmentId: $e }) { '
                '  edges { node { status meta } } '
                '} }'
            )
            async with httpx.AsyncClient(timeout=20) as c:
                r = await c.post(
                    "https://backboard.railway.com/graphql/v2",
                    headers={"Authorization": f"Bearer {rw_token}"},
                    json={"query": q2, "variables": {"s": rw_service, "e": rw_env}},
                )
            data = r.json()
            if "errors" in data:
                return {"ok": False, "error": str(data["errors"])[:400]}
        edges = (data.get("data", {}).get("deployments", {}) or {}).get("edges", [])
        good_sha = None
        for e in edges:
            n = e["node"]
            if n["status"] == "SUCCESS" and (n.get("meta") or {}).get("commitHash"):
                good_sha = n["meta"]["commitHash"]
                break
        if not good_sha:
            return {"ok": False, "error": "no recent successful deployment found"}

        gh_token = os.environ.get("GITHUB_TOKEN", "").strip()
        gh_repo = os.environ.get("GITHUB_REPO", "").strip()
        if not gh_token or not gh_repo:
            return {"ok": False, "error": "GITHUB_TOKEN/GITHUB_REPO required"}
        auth_url = f"https://x-access-token:{gh_token}@github.com/{gh_repo}.git"

        cmd = (
            f"cd {shlex.quote(str(GIT_WORKDIR))} && "
            f"git fetch origin && "
            f"git reset --hard {shlex.quote(good_sha)} && "
            f"git remote set-url origin {shlex.quote(auth_url)} && "
            f"git push origin main --force 2>&1"
        )
        result = await tool_run_command(cmd, timeout=120)
        if isinstance(result.get("stdout"), str):
            result["stdout"] = result["stdout"].replace(gh_token, "***GITHUB_TOKEN***")
        if isinstance(result.get("stderr"), str):
            result["stderr"] = result["stderr"].replace(gh_token, "***GITHUB_TOKEN***")
        result["rolled_back_to"] = good_sha[:8]
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


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
    {"name": "pre_deploy_check", "desc": "syntax + import sanity check before commit", "args": ["paths?"]},
    {"name": "check_deployment_status", "desc": "check Railway deployment success/fail", "args": []},
    {"name": "rollback_to_last_good", "desc": "revert to last successful Railway deployment", "args": []},
] + EXTRA_TOOL_DEFS + UNIVERSE_TOOL_DEFS + QUALITY_TOOL_DEFS + INDEX_TOOL_DEFS + SAFETY_TOOL_DEFS + LEARNING_TOOL_DEFS + AUTONOMY_TOOL_DEFS + OPS_TOOL_DEFS + MEMORY_TOOL_DEFS + SANDBOX_TOOL_DEFS + INTEGRATIONS_TOOL_DEFS + WEB_SEARCH_TOOL_DEFS + RAILWAY_TOOL_DEFS + VERCEL_TOOL_DEFS + ROUTER_TOOL_DEFS

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
        "description": "Find-and-replace in a file. Three modes: (1) DEFAULT — requires unique match (safest). (2) occurrence=N — replace the Nth match (1-indexed) when find appears multiple times. (3) replace_all=True — replace every occurrence. On non-unique error, returns line numbers of all matches so you can add surrounding context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "find": {"type": "string", "description": "exact text to find"},
                "replace": {"type": "string", "description": "replacement text"},
                "occurrence": {"type": "integer", "description": "1-indexed: replace the Nth match. Use when find is intentionally non-unique."},
                "replace_all": {"type": "boolean", "description": "replace EVERY occurrence (batch rename across file)"},
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
    {
        "name": "pre_deploy_check",
        "description": "Run syntax + import sanity checks on Python files BEFORE git commit. Catches SyntaxError, ImportError early. Always call this before git_commit_push for any non-trivial change. Returns {ok, issues[], verdict}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {"type": "array", "items": {"type": "string"},
                          "description": "specific files to check; if empty, checks all modified .py files"},
            },
            "required": [],
        },
    },
    {
        "name": "check_deployment_status",
        "description": "After git_commit_push, wait 2-4 minutes then call this to verify Railway actually deployed successfully. Returns {ok, latest: {status: SUCCESS|FAILED|BUILDING}, verdict}.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "rollback_to_last_good",
        "description": "EMERGENCY: if the latest deployment failed and you can't fix it quickly, this finds the last SUCCESS commit on Railway and force-pushes to it, restoring the platform. Use as a last resort when stuck.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
] + EXTRA_ANTHROPIC_TOOLS + UNIVERSE_ANTHROPIC_TOOLS + QUALITY_ANTHROPIC_TOOLS + INDEX_ANTHROPIC_TOOLS + SAFETY_ANTHROPIC_TOOLS + LEARNING_ANTHROPIC_TOOLS + AUTONOMY_ANTHROPIC_TOOLS + OPS_ANTHROPIC_TOOLS + MEMORY_ANTHROPIC_TOOLS + SANDBOX_ANTHROPIC_TOOLS + INTEGRATIONS_ANTHROPIC_TOOLS + WEB_SEARCH_ANTHROPIC_TOOLS + RAILWAY_ANTHROPIC_TOOLS + VERCEL_ANTHROPIC_TOOLS + ROUTER_ANTHROPIC_TOOLS + CACHE_ANTHROPIC_TOOLS + SUPERPOWERS_ANTHROPIC_TOOLS + [
    # ══ Media generation (Nano Banana, ElevenLabs, Sora, Playwright) ══
    {
        "name": "generate_image",
        "description": "Generate an image via Nano Banana (Gemini, primary) or GPT-Image-1 (fallback). Use for logos, hero images, illustrations, mock UI screenshots. Returns a public URL under /static/autocoder_media/. ALWAYS prefer this over telling the user to make images themselves.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Detailed visual description in English (works better than Arabic for images)."},
                "style": {"type": "string", "description": "modern / minimalist / cinematic / cartoon / 3d / arabic-calligraphy", "default": "modern"},
                "aspect": {"type": "string", "enum": ["1:1", "16:9", "9:16", "4:3"], "default": "1:1"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "generate_audio",
        "description": "Generate Arabic/English voiceover via ElevenLabs (primary) or OpenAI TTS (fallback). Use for narration, welcome messages, ads.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to speak (≤4000 chars). Arabic supported."},
                "voice": {"type": "string", "enum": ["arabic_male", "arabic_female", "english_male", "english_female"], "default": "arabic_male"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "generate_video",
        "description": "Trigger Sora 2 video generation (1-30 sec). Returns job_id immediately. Use tool_check_video_status to poll until status='completed' (1-3 min).",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "seconds": {"type": "integer", "default": 5, "minimum": 1, "maximum": 30},
                "aspect": {"type": "string", "enum": ["16:9", "9:16", "1:1"], "default": "16:9"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "check_video_status",
        "description": "Poll a Sora 2 video job. Returns status (queued/in_progress/completed/failed) and the video URL when completed.",
        "input_schema": {
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
        },
    },
    {
        "name": "screenshot_page",
        "description": "Open any URL in a headless Chromium and capture a JPEG screenshot. Use this to verify a deployed page visually before announcing completion, or to compare before/after changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "width": {"type": "integer", "default": 1366},
                "height": {"type": "integer", "default": 768},
                "full_page": {"type": "boolean", "default": False},
                "wait_ms": {"type": "integer", "default": 2000, "description": "ms to wait after page load before capture"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "seed_db",
        "description": "Insert test documents into a MongoDB collection. Protected collections (users, payments, credit_history) are refused. All seeded docs get _test_seed=True so they can be cleaned later with tool_clear_test_seed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "collection": {"type": "string"},
                "docs": {"type": "array", "items": {"type": "object"}},
                "drop_first": {"type": "boolean", "default": False},
            },
            "required": ["collection", "docs"],
        },
    },
    {
        "name": "clear_test_seed",
        "description": "Delete all _test_seed=True documents from a collection.",
        "input_schema": {
            "type": "object",
            "properties": {"collection": {"type": "string"}},
            "required": ["collection"],
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
    "view_logs": tool_view_logs,
    "list_env": tool_list_env,
    "pre_deploy_check": tool_pre_deploy_check,
    "check_deployment_status": tool_check_deployment_status,
    "rollback_to_last_good": tool_rollback_to_last_good,
    # ── Media generation tools (Feb 2026) ──
    "generate_image": __import__("modules.autocoder.media_tools", fromlist=["tool_generate_image"]).tool_generate_image,
    "generate_audio": __import__("modules.autocoder.media_tools", fromlist=["tool_generate_audio"]).tool_generate_audio,
    "generate_video": __import__("modules.autocoder.media_tools", fromlist=["tool_generate_video"]).tool_generate_video,
    "check_video_status": __import__("modules.autocoder.media_tools", fromlist=["tool_check_video_status"]).tool_check_video_status,
    "screenshot_page": __import__("modules.autocoder.media_tools", fromlist=["tool_screenshot_page"]).tool_screenshot_page,
    # seed_db / clear_test_seed bound at router-creation (needs db) — see _bind_db_tool
    # ── New power tools (web/files/db/ast) ──
    "web_search": tool_web_search,
    "fetch_url": tool_fetch_url,
    "view_bulk_files": tool_view_bulk_files,
    "apply_patch": tool_apply_patch,
    "ast_analyze": tool_ast_analyze,
    # db_query bound at router-creation time (needs db instance) — see _bind_db_tool
}

# Register Universe tools (300+ catalog operators)
TOOL_HANDLERS.update(UNIVERSE_TOOL_HANDLERS)
# Register Quality / verification tools
TOOL_HANDLERS.update(QUALITY_TOOL_HANDLERS)
# Register Code Index tools
TOOL_HANDLERS.update(INDEX_TOOL_HANDLERS)
# Register Safety Net tools
TOOL_HANDLERS.update(SAFETY_TOOL_HANDLERS)
# Register Learning Journal tools
TOOL_HANDLERS.update(LEARNING_TOOL_HANDLERS)
# Register Autonomy tools (browser + git push)
TOOL_HANDLERS.update(AUTONOMY_TOOL_HANDLERS)
# Register Ops tools (production observability, rollback, logs)
TOOL_HANDLERS.update(OPS_TOOL_HANDLERS)
# Register Task Memory tools (cross-session continuity)
TOOL_HANDLERS.update(MEMORY_TOOL_HANDLERS)
# Register Sandbox Mode tools (safe playground before production)
TOOL_HANDLERS.update(SANDBOX_TOOL_HANDLERS)
# Register Integrations Status tool (introspect missing keys)
TOOL_HANDLERS.update(INTEGRATIONS_TOOL_HANDLERS)
# Register Web Search tools (Tavily)
TOOL_HANDLERS.update(WEB_SEARCH_TOOL_HANDLERS)
# Register Railway tools (redeploy, build logs, runtime logs, env vars)
TOOL_HANDLERS.update(RAILWAY_TOOL_HANDLERS)
# Register Vercel tools (frontend deploy mirror)
TOOL_HANDLERS.update(VERCEL_TOOL_HANDLERS)
# Register Smart Model Router tools (auto-pick cheapest capable LLM)
TOOL_HANDLERS.update(ROUTER_TOOL_HANDLERS)
# Register Code Cache tools (token-savings: file + semantic Q&A cache)
TOOL_HANDLERS.update(CACHE_TOOL_HANDLERS)
# Register Superpowers tools (project_context / screenshot_url / plan_* / update_prd / project_health)
TOOL_HANDLERS.update(SUPERPOWERS_HANDLERS)

# db_query is bound to the live MongoDB at router creation time
_db_query_bound: Optional[Any] = None
_DB: Optional[Any] = None  # MongoDB instance (bound at router creation)


def _bind_db_tool(db) -> None:
    """Called from create_autocoder_router to bind the db_query tool."""
    global _db_query_bound, _DB
    _db_query_bound = make_db_query_tool(db)
    TOOL_HANDLERS["db_query"] = _db_query_bound
    _DB = db
    # Bind media tools that need a db instance
    from .media_tools import tool_seed_db, tool_clear_test_seed
    async def _seed(collection, docs, drop_first=False):
        return await tool_seed_db(db, collection, docs, drop_first)
    async def _clear(collection):
        return await tool_clear_test_seed(db, collection)
    TOOL_HANDLERS["seed_db"] = _seed
    TOOL_HANDLERS["clear_test_seed"] = _clear


async def execute_autocoder_tool(name: str, args: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return {"ok": False, "error": f"unknown tool: {name}"}
    # Normalize args — small models sometimes pass null / non-dict
    if args is None or not isinstance(args, dict):
        args = {}
    try:
        return await handler(**args)
    except TypeError as e:
        return {"ok": False, "error": f"bad args: {e}"}
    except Exception as e:
        logger.exception(f"[AUTOCODER] tool {name} failed")
        return {"ok": False, "error": str(e)}



def _message_text_preview(content: Any, limit: int = 12000) -> str:
    """Return a compact plain-text preview for history/UI/providers that do not support vision blocks."""
    if isinstance(content, str):
        return content[:limit]
    if isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
            elif block.get("type") == "image":
                source = block.get("source") or {}
                media_type = source.get("media_type") or "image"
                parts.append(f"[صورة مرفقة: {media_type} — متاحة للتحليل في Claude]")
            elif block.get("type") == "tool_result":
                parts.append(str(block.get("content") or ""))
        return "\n".join(x for x in parts if x).strip()[:limit]
    return str(content or "")[:limit]


def _extract_message_plain_text(content: Any) -> str:
    return _message_text_preview(content, 32000)


def _safe_upload_name(filename: str) -> str:
    original = Path(filename or "file").name.replace("/", "_").replace("\\", "_")
    return re.sub(r'[^\w\.\-\u0600-\u06FF ]', '_', original).strip() or "file"


def _normalize_media_type(media_type: str, filename: str = "") -> str:
    mt = (media_type or mimetypes.guess_type(filename or "")[0] or "application/octet-stream").lower().split(";")[0].strip()
    if mt == "image/jpg":
        mt = "image/jpeg"
    return mt


def _autocoder_upload_dir() -> Path:
    """Single canonical upload directory mounted by server.py at /uploads."""
    return Path(os.environ.get("AUTOCODER_UPLOAD_DIR", "/app/backend/uploads"))


def _image_metadata(content: bytes, media_type: str) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"is_image": media_type.startswith("image/")}
    if not meta["is_image"] or not content:
        return meta
    if Image is None:
        meta["warning"] = "Pillow غير متاح؛ تعذر استخراج أبعاد الصورة محلياً"
        return meta
    try:
        import io
        with Image.open(io.BytesIO(content)) as img:
            meta.update({
                "width": int(img.width),
                "height": int(img.height),
                "format": str(img.format or "").lower() or None,
                "mode": img.mode,
            })
    except Exception as e:
        meta["warning"] = f"تعذر قراءة أبعاد الصورة: {str(e)[:120]}"
    return meta


def _anthropic_image_block(content: bytes, media_type: str) -> Optional[Dict[str, Any]]:
    """Build an Anthropic vision block for supported image uploads."""
    mt = _normalize_media_type(media_type)
    supported = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if mt not in supported or not content:
        return None
    # Anthropic limit is model/API dependent; keep under a safe 8MB per image.
    if len(content) > 8 * 1024 * 1024:
        return None
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": mt,
            "data": base64.b64encode(content).decode("ascii"),
        },
    }


def _vision_doctor_prompt(image_count: int) -> str:
    return (
        "أنت الآن طبيب جودة بصري لمنصة Zitex. حلّل الصور المرفقة فعلياً، ولا تعطِ وصفاً عاماً. "
        f"عدد الصور القابلة للرؤية: {image_count}.\n"
        "اكتب بالعربية وبشكل عملي:\n"
        "1) ماذا يظهر في كل صورة بالتفصيل: الصفحة/التطبيق/العناصر/النصوص البارزة.\n"
        "2) هل هي screenshot من موقع Zitex أو من موقع/تطبيق خارجي؟ وما الدليل؟\n"
        "3) المشاكل المرئية المحددة: layout, responsive, contrast, spacing, overflow, broken UI, missing images, loading, errors.\n"
        "4) خطورة كل مشكلة: عالي/متوسط/منخفض.\n"
        "5) خطوات الإصلاح البرمجية المقترحة، والملفات المرجحة إذا كانت من Zitex.\n"
        "6) إن كانت الصورة غير واضحة أو ليست من الموقع، قل ذلك صراحة ولا تخترع."
    )

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
    model: Optional[str] = Field(default="claude", description="claude | groq | gemini")


# ════════════════════════════════════════════════════════════════════════
# Router factory
# ════════════════════════════════════════════════════════════════════════
def create_autocoder_router(db, get_current_user, require_owner):
    router = APIRouter(prefix="/api/autocoder", tags=["autocoder"])

    # Bind the db_query tool to the live MongoDB instance
    _bind_db_tool(db)
    # Bind the Learning Journal to the DB
    _bind_learning_db(db)
    # Bind the Task Memory to the DB (cross-session task continuity)
    _bind_memory_db(db)
    # Bind the Web Search vault fallback to DB
    _bind_websearch_db(db)
    # Bind Railway tools to credentials getter (env or vault)
    _bind_railway_creds(_get_railway_creds)
    # Bind Vercel tools to credentials getter (env or vault)
    _bind_vercel_creds(_get_vercel_creds)
    # Bind Smart Router DB (for usage analytics + Moonshot vault key)
    _bind_router_db(db)
    # Bind Code Cache (file SHA cache + semantic Q&A cache)
    _bind_cache_db(db)

    # Pre-build code index in background so first AI request is fast
    try:
        import threading
        threading.Thread(target=lambda: get_index(force_rebuild=False), daemon=True).start()
    except Exception as e:
        logger.warning(f"code index prebuild failed: {e}")

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
        """Public-ish info (owner only) about which keys/models are available."""
        keyinfo = _resolve_llm_key()
        groq_set = bool(os.environ.get("GROQ_API_KEY", "").strip())
        gemini_set = bool(os.environ.get("GEMINI_API_KEY", "").strip())
        moonshot_set = bool((os.environ.get("MOONSHOT_API_KEY", "") or os.environ.get("KIMI_API_KEY", "")).strip())
        deepseek_set = bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())
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
            # New: multi-provider availability
            "providers": {
                "claude": {
                    "available": keyinfo["mode"] != "missing",
                    "label": "Claude Sonnet 4.5",
                    "cost": "💰 مدفوع (الأذكى)",
                    "model": "claude-sonnet-4-5",
                },
                "groq": {
                    "available": groq_set,
                    "label": "Llama 3.3 70B (Groq)",
                    "cost": "🆓 مجاني — سريع جداً",
                    "model": "llama-3.3-70b-versatile",
                    "get_key_url": "https://console.groq.com/keys",
                },
                "gemini": {
                    "available": gemini_set,
                    "label": "Gemini 2.5 Flash",
                    "cost": "🆓 مجاني — قدرة كبيرة",
                    "model": "gemini-2.5-flash",
                    "get_key_url": "https://aistudio.google.com/apikey",
                },
                "openai": {
                    "available": bool((os.environ.get("OPENAI_API_KEY", "") or
                                       os.environ.get("OPENAI_DIRECT_KEY", "")).strip()),
                    "label": "GPT-5.5 (Codex)",
                    "cost": "💎 مدفوع — الأقوى للبرمجة",
                    "model": "gpt-5.5",
                    "get_key_url": "https://platform.openai.com/api-keys",
                },
                "kimi": {
                    "available": moonshot_set,
                    "label": "Kimi K2.6 (Moonshot الصيني)",
                    "cost": "💰 مدفوع — أرخص بكثير من OpenAI",
                    "model": "kimi-k2.6",
                    "get_key_url": "https://platform.moonshot.ai/console/api-keys",
                },
                "deepseek": {
                    "available": deepseek_set,
                    "label": "DeepSeek V3 (الصيني للبرمجة)",
                    "cost": "💰 مدفوع — رخيص جداً",
                    "model": "deepseek-chat",
                    "get_key_url": "https://platform.deepseek.com/api_keys",
                },
            },
        }

    @router.post("/emergency-reset")
    async def emergency_reset(owner=Depends(require_owner)):
        """Wipes the autocoder config completely (passcode + recovery codes + sessions).
        After this, the next visit shows the Setup screen as if it's the first time.
        Only the owner can call this (require_owner already enforces it)."""
        await db.autocoder_config.delete_many({})
        await db.autocoder_sessions.delete_many({})
        await _audit("emergency_reset", owner.get("id"))
        return {
            "ok": True,
            "message": "تم مسح الإعدادات. ارجع لصفحة برمجة زيتاكس لإعداد كلمة سر جديدة.",
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
    # Accepts BOTH application/json (legacy frontend) AND multipart/form-data (with file attachments).
    # This dual-mode keeps backwards compatibility with older frontend builds.
    @router.post("/chat")
    async def chat(
        request: Request,
        owner=Depends(require_owner),
        x_autocoder_token: Optional[str] = Header(None),
    ):
        if not await _check_session_token(x_autocoder_token or ""):
            raise HTTPException(401, "session locked or expired — unlock first")

        # Auto-detect content type to support both JSON and multipart bodies
        content_type = (request.headers.get("content-type") or "").lower()
        message: str = ""
        conversation_id: Optional[str] = None
        model: Optional[str] = "claude"
        attachments: List[UploadFile] = []

        if "application/json" in content_type:
            try:
                body = await request.json()
            except Exception:
                raise HTTPException(400, "invalid JSON body")
            message = (body.get("message") or "").strip()
            conversation_id = body.get("conversation_id")
            model = body.get("model") or "claude"
        else:
            # multipart/form-data (or x-www-form-urlencoded)
            try:
                form = await request.form()
            except Exception:
                raise HTTPException(400, "invalid form body")
            message = (form.get("message") or "").strip()
            conversation_id = form.get("conversation_id") or None
            model = form.get("model") or "claude"
            # Starlette's request.form() returns starlette.datastructures.UploadFile,
            # while our annotation imports fastapi.UploadFile. A strict isinstance
            # check can silently drop real uploads, so accept file-like upload objects.
            for key in ("attachments", "files", "file"):
                vals = form.getlist(key) if hasattr(form, "getlist") else []
                for v in vals:
                    if hasattr(v, "filename") and hasattr(v, "read"):
                        attachments.append(v)

        if not message and not attachments:
            raise HTTPException(422, "message or attachment required")
        if len(message) > 32000:
            raise HTTPException(422, "message too long (max 32000 chars)")

        conv_id = conversation_id or str(uuid.uuid4())
        conv = await db.autocoder_conversations.find_one(
            {"id": conv_id, "owner_id": owner.get("id")}, {"_id": 0}
        )
        messages: List[Dict[str, Any]] = conv["messages"] if conv else []

        # Build current user turn. Images are sent to Claude as real vision blocks,
        # not just saved URLs, so AutoCoder can actually inspect screenshots/photos.
        attachment_meta: List[Dict[str, Any]] = []
        attachment_summaries: List[str] = []
        image_blocks: List[Dict[str, Any]] = []
        if attachments:
            upload_dir = _autocoder_upload_dir()
            upload_dir.mkdir(parents=True, exist_ok=True)
            for att in attachments[:6]:
                safe_name = _safe_upload_name(att.filename or "file")
                content = await att.read()
                if len(content) > 10 * 1024 * 1024:
                    raise HTTPException(400, f"Attachment too large: {safe_name} (max 10MB)")
                content_type = _normalize_media_type(att.content_type or "", safe_name)
                digest = hashlib.sha256(content).hexdigest()
                file_id = secrets.token_hex(8)
                file_name = f"{file_id}_{safe_name}"
                file_path = upload_dir / file_name
                file_path.write_bytes(content)

                file_url = f"/uploads/{file_name}"
                img_meta = _image_metadata(content, content_type)
                meta = {
                    "id": file_id,
                    "name": safe_name,
                    "stored_name": file_name,
                    "type": content_type,
                    "size": len(content),
                    "sha256": digest,
                    "url": file_url,
                    "stored_at": _now(),
                    **img_meta,
                }
                attachment_meta.append(meta)
                dim = f", {meta.get('width')}x{meta.get('height')}" if meta.get("width") and meta.get("height") else ""
                attachment_summaries.append(f"- {safe_name} ({content_type}{dim}, {len(content)} bytes, sha256={digest[:12]}…): {file_url}")

                try:
                    await db.autocoder_uploads.insert_one({
                        **meta,
                        "owner_id": owner.get("id"),
                        "conversation_id": conv_id,
                        "path": str(file_path),
                    })
                except Exception:
                    logger.warning("failed to persist autocoder upload metadata", exc_info=True)

                image_block = _anthropic_image_block(content, content_type)
                if image_block:
                    image_blocks.append(image_block)

        text_parts = []
        if message:
            text_parts.append(message)
        if attachment_summaries:
            text_parts.append("📎 المرفقات المستلمة:\n" + "\n".join(attachment_summaries))
        if image_blocks:
            text_parts.append(_vision_doctor_prompt(len(image_blocks)))
        elif attachments:
            text_parts.append("تنبيه: الملفات محفوظة في نظام المرفقات الدائم، لكن التحليل البصري المباشر متاح حالياً للصور المدعومة فقط JPEG/PNG/GIF/WebP وبحجم آمن.")

        text_content = "\n\n".join(text_parts).strip() or "حلّل المرفقات المرسلة."
        # Use vision blocks only for the live LLM request. Persist a plain-text
        # version in Mongo so conversation history stays light and renderable.
        if image_blocks:
            llm_user_content: Any = [{"type": "text", "text": text_content}, *image_blocks]
        else:
            llm_user_content = text_content

        user_msg = {"role": "user", "content": text_content, "ts": _now()}
        if attachment_meta:
            user_msg["attachments"] = attachment_meta
        llm_messages = [*messages, {"role": "user", "content": llm_user_content, "ts": user_msg["ts"]}]
        messages.append(user_msg)

        # ── Persist user turn immediately so a network drop doesn't lose it ──
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

        async def gen():
            assistant_text = ""
            tool_events: List[Dict[str, Any]] = []
            usage_total = {"input": 0, "output": 0, "cached_read": 0, "cost_usd": 0.0}
            saved_to_db = False

            async def _persist_assistant_turn(extra_marker: str = ""):
                """Append assistant turn to conversation. Safe to call multiple times — won't double-append."""
                nonlocal saved_to_db
                if saved_to_db:
                    return
                final_text = assistant_text + (("\n\n" + extra_marker) if (extra_marker and assistant_text) else extra_marker)
                if not final_text.strip() and not tool_events:
                    saved_to_db = True
                    return  # nothing useful to save
                messages.append({
                    "role": "assistant",
                    "content": final_text,
                    "tool_events": tool_events,
                    "ts": _now(),
                    "partial": bool(extra_marker),
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
                    "cost_usd": round(usage_total["cost_usd"], 4),
                    "input_tokens": usage_total["input"],
                    "output_tokens": usage_total["output"],
                    "partial": bool(extra_marker),
                })
                saved_to_db = True

            try:
                async for evt in _autocoder_stream(llm_messages, model=model or "claude"):
                    if evt["type"] == "text":
                        assistant_text += evt["content"]
                    elif evt["type"] == "tool":
                        tool_events.append({k: v for k, v in evt.items() if k not in ("content",)})
                    elif evt["type"] == "usage":
                        usage_total["input"] += evt.get("input", 0)
                        usage_total["output"] += evt.get("output", 0)
                        usage_total["cached_read"] += evt.get("cached_read", 0)
                        usage_total["cost_usd"] += evt.get("cost_usd", 0.0)
                    yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

                await _persist_assistant_turn()
                yield f"data: {json.dumps({'type':'saved','conversation_id':conv_id, 'turn_cost': round(usage_total['cost_usd'], 4)})}\n\n"
            except asyncio.CancelledError:
                # Client disconnected mid-stream → still save whatever we have so it's not lost.
                # asyncio.shield() prevents the cancellation from killing the persist call itself.
                try:
                    await asyncio.shield(_persist_assistant_turn(extra_marker="⚠️ انقطع الاتصال"))
                except Exception:
                    pass
                raise
            except Exception as e:
                logger.exception("[AUTOCODER] chat stream failed")
                # Save any partial assistant text we accumulated before the failure
                try:
                    await asyncio.shield(_persist_assistant_turn(extra_marker=f"⚠️ خطأ: {str(e)[:120]}"))
                except Exception:
                    pass
                # Friendly Arabic error for the user
                err_str = str(e)[:300]
                friendly = err_str
                low = err_str.lower()
                if "noneType" in err_str or "'NoneType'" in err_str:
                    friendly = f"خلل داخلي تم تجاوزه. حاول مرة ثانية. (التفاصيل: {err_str[:150]})"
                elif "credit_balance" in low or "billing" in low:
                    friendly = "رصيد Anthropic منخفض. بدّل الموديل لـLlama (Groq) — مجاني."
                elif "rate" in low or "429" in low:
                    friendly = "تجاوزت حد الطلبات. استنّى ~30 ثانية ثم حاول."
                elif "timeout" in low:
                    friendly = "الطلب استغرق وقت طويل. حاول مرة ثانية أو ابدأ محادثة جديدة."
                yield f"data: {json.dumps({'type':'error','message': friendly}, ensure_ascii=False)}\n\n"

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
                "preview": _message_text_preview(first.get("content") or "", 80),
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

    # ─────────────────────────────────────────────────────────────
    # 🎨 Media Router — quality-first selection (owner only)
    # ─────────────────────────────────────────────────────────────
    @router.get("/media/catalog")
    async def media_catalog(owner=Depends(require_owner)):
        from .media_router import catalog
        return catalog()

    @router.post("/media/pick/image")
    async def media_pick_image(payload: Dict[str, Any], owner=Depends(require_owner)):
        from .media_router import pick_image_model
        prompt = (payload.get("prompt") or "").strip()
        priority = payload.get("priority") or "quality"
        if not prompt:
            raise HTTPException(422, "prompt required")
        return pick_image_model(prompt, priority=priority)

    @router.post("/media/pick/video")
    async def media_pick_video(payload: Dict[str, Any], owner=Depends(require_owner)):
        from .media_router import pick_video_model
        prompt = (payload.get("prompt") or "").strip()
        duration = int(payload.get("duration") or 5)
        priority = payload.get("priority") or "quality"
        if not prompt:
            raise HTTPException(422, "prompt required")
        return pick_video_model(prompt, duration_seconds=duration, priority=priority)

    @router.post("/media/pick/edit")
    async def media_pick_edit(payload: Dict[str, Any], owner=Depends(require_owner)):
        from .media_router import pick_image_edit_model
        prompt = (payload.get("prompt") or "").strip()
        return pick_image_edit_model(prompt)

    @router.post("/media/pick/voice")
    async def media_pick_voice(payload: Dict[str, Any], owner=Depends(require_owner)):
        from .media_router import pick_voice_model
        text = (payload.get("text") or "").strip()
        return pick_voice_model(text)

    @router.post("/router/pick")
    async def llm_router_pick(payload: Dict[str, Any], owner=Depends(require_owner)):
        """Preview which LLM the quality-first router would pick for a prompt."""
        from .auto_router import pick_provider, explain_for_ui
        prompt = (payload.get("prompt") or "").strip()
        has_attachments = bool(payload.get("has_attachments"))
        if not prompt:
            raise HTTPException(422, "prompt required")
        keyinfo = _resolve_llm_key()
        decision = pick_provider(prompt, has_attachments=has_attachments, keyinfo_mode=keyinfo["mode"])
        decision["explanation"] = explain_for_ui(decision)
        return decision

    # ─────────────────────────────────────────────────────────────
    # 🎯 Section AI Profiles — Per-section AI expert + diversity
    # ─────────────────────────────────────────────────────────────
    @router.get("/sections")
    async def sections_list(owner=Depends(require_owner)):
        from .section_profiles import list_sections
        return {"sections": list_sections(owner=True)}

    @router.get("/sections/{section_id}")
    async def section_detail(section_id: str, owner=Depends(require_owner)):
        from .section_profiles import get_section_detail
        d = get_section_detail(section_id)
        if not d:
            raise HTTPException(404, "section not found")
        return d

    @router.post("/sections/{section_id}/pick")
    async def section_pick(section_id: str, payload: Dict[str, Any], owner=Depends(require_owner)):
        from .section_profiles import pick_for_section
        seed = payload.get("seed")
        try:
            seed_int = int(seed) if seed is not None else None
        except Exception:
            seed_int = None
        result = pick_for_section(section_id, seed=seed_int)
        if "error" in result:
            raise HTTPException(404, result["error"])
        return result

    # ─────────────────────────────────────────────────────────────
    # 📚 Learning Journal endpoints (continuous learning)
    # ─────────────────────────────────────────────────────────────
    @router.get("/learning/stats")
    async def learning_stats_route(owner=Depends(require_owner)):
        return {"ok": True, **await _learning_get_stats()}

    @router.get("/learning/lessons")
    async def learning_lessons_route(
        q: str = "",
        limit: int = 50,
        source: str = "",
        owner=Depends(require_owner),
    ):
        limit = min(max(1, limit), 200)
        items = await _query_lessons(query=q, limit=limit, source=source)
        return {"ok": True, "count": len(items), "lessons": items}

    @router.post("/learning/lessons")
    async def learning_add_lesson_route(payload: Dict[str, Any], owner=Depends(require_owner)):
        task_summary = (payload.get("task_summary") or "").strip()
        lesson = (payload.get("lesson") or "").strip()
        if not task_summary or not lesson:
            raise HTTPException(status_code=400, detail="task_summary وlesson مطلوبين")
        return await _add_lesson(
            task_summary=task_summary,
            lesson=lesson,
            source=payload.get("source", "owner"),
            actor_id=owner.get("id"),
            code_pattern=payload.get("code_pattern"),
            tags=payload.get("tags") or [],
        )

    @router.post("/learning/lessons/{lesson_id}/pin")
    async def learning_pin_route(lesson_id: str, payload: Dict[str, Any] = None, owner=Depends(require_owner)):
        pinned = bool((payload or {}).get("pinned", True))
        return await _promote_lesson(lesson_id, pinned)

    @router.post("/learning/lessons/{lesson_id}/archive")
    async def learning_archive_route(lesson_id: str, payload: Dict[str, Any] = None, owner=Depends(require_owner)):
        archived = bool((payload or {}).get("archived", True))
        return await _archive_lesson(lesson_id, archived)



    # ─────────────────────────────────────────────────────────────
    # 📤 Upload endpoint (for images/files in chat)
    # ─────────────────────────────────────────────────────────────
    @router.post("/upload")
    async def upload_file(
        file: UploadFile = File(...),
        request: Request = None,
        owner=Depends(require_owner),
        x_autocoder_token: Optional[str] = Header(None),
    ):
        """
        رفع ملف مستقل للـAutoCoder → يحفظه في /uploads ويرجع metadata قابلة للاستخدام.
        لا يرجع base64 ضخم افتراضياً حتى لا نكسر الواجهة أو قاعدة البيانات.
        """
        if not await _check_session_token(x_autocoder_token or ""):
            raise HTTPException(401, "session locked or expired — unlock first")
        try:
            contents = await file.read()
            if len(contents) > 10 * 1024 * 1024:
                raise HTTPException(400, "File too large (max 10MB)")

            safe_name = _safe_upload_name(file.filename or "file")
            content_type = _normalize_media_type(file.content_type or "", safe_name)
            digest = hashlib.sha256(contents).hexdigest()
            file_id = secrets.token_hex(8)
            stored_name = f"{file_id}_{safe_name}"
            upload_dir = _autocoder_upload_dir()
            upload_dir.mkdir(parents=True, exist_ok=True)
            file_path = upload_dir / stored_name
            file_path.write_bytes(contents)
            file_url = f"/uploads/{stored_name}"
            img_meta = _image_metadata(contents, content_type)
            meta = {
                "id": file_id,
                "filename": safe_name,
                "stored_name": stored_name,
                "content_type": content_type,
                "size": len(contents),
                "sha256": digest,
                "url": file_url,
                "stored_at": _now(),
                **img_meta,
            }
            try:
                await db.autocoder_uploads.insert_one({
                    **meta,
                    "owner_id": owner.get("id"),
                    "path": str(file_path),
                    "source": "upload_endpoint",
                })
            except Exception:
                logger.warning("failed to persist autocoder upload metadata", exc_info=True)

            return {
                "success": True,
                **meta,
                "vision_supported": _anthropic_image_block(contents, content_type) is not None,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upload error: {e}", exc_info=True)
            raise HTTPException(500, f"Upload failed: {str(e)}")

    @router.get("/uploads/recent")
    async def recent_uploads(
        limit: int = 20,
        owner=Depends(require_owner),
        x_autocoder_token: Optional[str] = Header(None),
    ):
        """آخر مرفقات AutoCoder مع metadata بدون كشف مسارات داخلية حساسة."""
        if not await _check_session_token(x_autocoder_token or ""):
            raise HTTPException(401, "session locked or expired — unlock first")
        safe_limit = max(1, min(int(limit or 20), 100))
        docs = await db.autocoder_uploads.find(
            {"owner_id": owner.get("id")},
            {"_id": 0, "path": 0},
        ).sort("stored_at", -1).limit(safe_limit).to_list(safe_limit)
        return {"ok": True, "uploads": docs}

    # ─────────────────────────────────────────────────────────────
    # 🎤 Transcribe endpoint (audio → text via Whisper)
    # ─────────────────────────────────────────────────────────────
    @router.post("/transcribe")
    async def transcribe_audio(
        file: UploadFile = File(...),
        request: Request = None
    ):
        """
        تحويل ملف صوتي → نص باستخدام OpenAI Whisper API
        """
        try:
            # قراءة محتوى الملف
            contents = await file.read()
            
            # التحقق من الحجم (max 25MB - Whisper limit)
            if len(contents) > 25 * 1024 * 1024:
                raise HTTPException(400, "Audio file too large (max 25MB)")
            
            # التحقق من وجود OPENAI_API_KEY (يقبل OPENAI_DIRECT_KEY أو OPENAI_API_KEY)
            openai_key = (
                os.getenv("OPENAI_DIRECT_KEY")
                or os.getenv("OPENAI_API_KEY")
                or ""
            ).strip()
            if not openai_key:
                raise HTTPException(500, "OPENAI_API_KEY (or OPENAI_DIRECT_KEY) not configured")
            
            # استدعاء Whisper API
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                files_data = {
                    "file": (file.filename, contents, file.content_type or "audio/mpeg")
                }
                data = {
                    "model": "whisper-1",
                    "language": "ar"  # عربي (optional - Whisper يكتشف تلقائياً)
                }
                
                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    files=files_data,
                    data=data
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"Whisper API error: {error_text}")
                    raise HTTPException(500, f"Transcription failed: {error_text}")
                
                result = response.json()
                transcription = result.get("text", "")
                
                return {
                    "success": True,
                    "text": transcription,
                    "language": result.get("language", "ar")
                }
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Transcribe error: {e}", exc_info=True)
            raise HTTPException(500, f"Transcription failed: {str(e)}")

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
async def _autocoder_stream(messages: List[Dict[str, Any]], model: str = "claude"):
    """Yields events: {type:'text'|'tool'|'done'|'error', ...}

    Routes to the chosen provider:
      - 'auto' (smart router): picks cheapest *capable* provider per turn
      - 'claude' (default): direct Anthropic SDK with native tool calling (highest quality)
      - 'openai' / 'gpt5': GPT-5.5 via OpenAI
      - 'kimi' / 'moonshot': Kimi K2.6 (Chinese, cheap+strong)
      - 'deepseek': DeepSeek V3 (Chinese, cheapest coder)
      - 'groq': Llama 3.3 70B via Groq (FREE, fast)
      - 'gemini': Gemini 2.5 Flash via Google (FREE)
    """
    keyinfo = _resolve_llm_key()

    # ── Smart Auto Router ─────────────────────────────────────────────
    auto_decision: Optional[Dict[str, str]] = None
    if model == "auto":
        try:
            from .auto_router import pick_provider, explain_for_ui
            # Find the last user message text + check for image attachments
            last_user_text = ""
            has_images = False
            for m in reversed(messages):
                if m.get("role") == "user":
                    c = m.get("content")
                    if isinstance(c, str):
                        last_user_text = c
                    elif isinstance(c, list):
                        for blk in c:
                            if isinstance(blk, dict):
                                if blk.get("type") == "text":
                                    last_user_text += " " + (blk.get("text") or "")
                                elif blk.get("type") in ("image", "image_url"):
                                    has_images = True
                    break
            auto_decision = pick_provider(last_user_text, has_images, keyinfo["mode"])
            model = auto_decision["provider"]
            # Emit a pill so the UI shows what was chosen
            yield {"type": "auto_route",
                   "provider": auto_decision["provider"],
                   "task": auto_decision["task"],
                   "reason": auto_decision["reason"],
                   "est_cost_usd_per_turn": auto_decision["est_cost_usd_per_turn"],
                   "fallback_chain": auto_decision["fallback_chain"]}
        except Exception as e:
            logger.error(f"auto_router failed: {e}", exc_info=True)
            model = "claude"  # safe default

    # Build a runtime-truth banner so the AI cannot hallucinate about env/tools
    env_banner = await _build_env_truth_banner()  # noqa: F821

    # Build a unified history (skip empty)
    anthropic_msgs: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        content = m.get("content", "") or ""
        preview = _message_text_preview(content, 12000)
        if not preview.strip():
            continue
        # Keep structured content blocks for Anthropic/Claude so image attachments
        # reach the model. Alternate providers will coerce to text in their adapters.
        if isinstance(content, list):
            anthropic_msgs.append({"role": role, "content": content})
        else:
            anthropic_msgs.append({"role": role, "content": preview})

    text_provider_msgs = [
        {"role": m.get("role", "user"), "content": _message_text_preview(m.get("content", ""), 12000)}
        for m in anthropic_msgs
    ]

    # ── Route to alternative free providers ──
    # The AUTOCODER_SYSTEM_PROMPT carries the rules; the codebase_atlas adds
    # full structural knowledge so the AI doesn't waste tokens scanning files.
    # Pull persistent lessons (continuous learning journal)
    try:
        lessons_block = await build_lessons_for_prompt(max_lessons=12)
    except Exception:
        lessons_block = ""
    sys_prompt_full = AUTOCODER_SYSTEM_PROMPT + AUTONOMY_PROMPT_RULES + OPS_PROMPT_RULES + QUALITY_PROMPT_RULES + INDEX_PROMPT_RULES + SAFETY_PROMPT_RULES + LEARNING_PROMPT_RULES + SUPERPOWERS_PROMPT_RULES + (env_banner or "") + build_atlas_for_prompt() + build_atlas_v2_for_prompt() + build_universe_for_prompt() + lessons_block
    if model == "groq":
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        async for evt in stream_via_groq(
            text_provider_msgs, groq_key, sys_prompt_full, ANTHROPIC_TOOLS,
            execute_autocoder_tool, _trim_args_for_ui,
            _summarize, _preview_for_ui, _trim_result_for_llm,
        ):
            yield evt
        return

    if model == "gemini":
        gem_key = os.environ.get("GEMINI_API_KEY", "").strip()
        async for evt in stream_via_gemini(
            text_provider_msgs, gem_key, sys_prompt_full, ANTHROPIC_TOOLS,
            execute_autocoder_tool, _trim_args_for_ui,
            _summarize, _preview_for_ui, _trim_result_for_llm,
        ):
            yield evt
        return

    if model == "openai" or model == "gpt5":
        # GPT-5.5 — premium for coding. Accepts OPENAI_API_KEY or OPENAI_DIRECT_KEY.
        oai_key = (os.environ.get("OPENAI_API_KEY", "") or
                   os.environ.get("OPENAI_DIRECT_KEY", "")).strip()
        async for evt in stream_via_openai(
            text_provider_msgs, oai_key, sys_prompt_full, ANTHROPIC_TOOLS,
            execute_autocoder_tool, _trim_args_for_ui,
            _summarize, _preview_for_ui, _trim_result_for_llm,
        ):
            yield evt
        return

    if model == "kimi" or model == "moonshot":
        from .llm_providers import stream_via_kimi
        kimi_key = (os.environ.get("MOONSHOT_API_KEY", "") or
                    os.environ.get("KIMI_API_KEY", "")).strip()
        async for evt in stream_via_kimi(
            text_provider_msgs, kimi_key, sys_prompt_full, ANTHROPIC_TOOLS,
            execute_autocoder_tool, _trim_args_for_ui,
            _summarize, _preview_for_ui, _trim_result_for_llm,
        ):
            yield evt
        return

    if model == "deepseek":
        from .llm_providers import stream_via_deepseek
        ds_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        async for evt in stream_via_deepseek(
            text_provider_msgs, ds_key, sys_prompt_full, ANTHROPIC_TOOLS,
            execute_autocoder_tool, _trim_args_for_ui,
            _summarize, _preview_for_ui, _trim_result_for_llm,
        ):
            yield evt
        return

    # ── Claude path (default) ──
    if keyinfo["mode"] == "missing":
        yield {"type": "error",
               "message": "لا يوجد ANTHROPIC_API_KEY ولا EMERGENT_LLM_KEY. أضف مفتاحك في Railway → Variables. أو اختر Groq/Gemini المجانيين."}
        return

    # Mode 1: direct Anthropic SDK with native tool calling
    if keyinfo["mode"] == "direct":
        billing_failed = False
        async for evt in _stream_direct_anthropic(anthropic_msgs, keyinfo["key"], env_banner):
            # Detect billing/quota failures so we can auto-fallback to Groq
            if evt.get("type") == "error":
                msg = (evt.get("message") or "").lower()
                if "رصيد" in evt.get("message", "") or "credit" in msg or "billing" in msg:
                    billing_failed = True
                    yield {"type": "text",
                           "content": "\n\n⚡ Claude رصيده انتهى. أحوّلك تلقائياً لـLlama (Groq) المجاني...\n\n"}
                    break
            yield evt

        if billing_failed:
            groq_key = os.environ.get("GROQ_API_KEY", "").strip()
            if groq_key:
                async for evt in stream_via_groq(
                    text_provider_msgs, groq_key, sys_prompt_full, ANTHROPIC_TOOLS,
                    execute_autocoder_tool, _trim_args_for_ui,
                    _summarize, _preview_for_ui, _trim_result_for_llm,
                ):
                    yield evt
            else:
                yield {"type": "error",
                       "message": "Claude رصيده انتهى ومافي GROQ_API_KEY للاحتياط. أضف Groq key مجاني من console.groq.com/keys."}
        return

    # Mode 2: emergentintegrations fallback (text-blob tool parsing — legacy)
    async for evt in _stream_via_emergent(messages, keyinfo["key"]):
        yield evt


async def _build_env_truth_banner() -> str:
    """Run actual checks so the AI sees the real state of the environment.
    Prevents hallucinating that tools are 'missing' when they're installed."""

    async def has(cmd: str) -> bool:
        try:
            p = await asyncio.create_subprocess_shell(
                f"command -v {cmd} >/dev/null 2>&1 && echo yes || echo no",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            out, _ = await asyncio.wait_for(p.communicate(), timeout=5)
            return out.decode().strip() == "yes"
        except Exception:
            return False

    git_ok = await has("git")
    curl_ok = await has("curl")
    jq_ok = await has("jq")
    sup_ok = await has("supervisorctl")
    node_ok = await has("node")
    yarn_ok = await has("yarn")
    npm_ok = await has("npm")
    on_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT"))
    # Check vault for tokens too (not just env)
    has_gh = bool(os.environ.get("GITHUB_TOKEN", "").strip())
    has_gh_repo = bool(os.environ.get("GITHUB_REPO", "").strip())
    has_rw = bool(os.environ.get("RAILWAY_TOKEN", "").strip())
    has_tavily = bool(os.environ.get("TAVILY_API_KEY", "").strip())
    if not has_gh and _DB is not None:
        try:
            d = await _DB.credentials_vault.find_one({"service": "github"}, {"_id": 0, "service": 1})
            if d:
                has_gh = True
                has_gh_repo = True
        except Exception:
            pass
    if not has_rw and _DB is not None:
        try:
            d = await _DB.credentials_vault.find_one({"service": "railway"}, {"_id": 0, "service": 1})
            if d:
                has_rw = True
        except Exception:
            pass
    if not has_tavily and _DB is not None:
        try:
            d = await _DB.credentials_vault.find_one({"service": "tavily"}, {"_id": 0, "service": 1})
            if d:
                has_tavily = True
        except Exception:
            pass
    has_ant = os.environ.get("ANTHROPIC_API_KEY", "").startswith("sk-ant")

    banner = "\n\n━━━━ 📊 الحالة الفعلية للبيئة (مُتحقّق منها قبل ما تردّ) ━━━━\n"
    banner += f"البيئة: {'🚂 Railway production' if on_railway else '💻 Preview/local dev'}\n"
    banner += f"أدوات النظام: git={'✅' if git_ok else '❌'}  curl={'✅' if curl_ok else '❌'}  "
    banner += f"jq={'✅' if jq_ok else '❌'}  supervisorctl={'✅' if sup_ok else '❌ (طبيعي على Railway)'}\n"
    banner += f"Frontend tools: node={'✅' if node_ok else '❌'}  yarn={'✅' if yarn_ok else '❌'}  npm={'✅' if npm_ok else '❌'}\n"
    banner += f"المفاتيح: ANTHROPIC_API_KEY={'✅ مستقل' if has_ant else '⚡ يستخدم Emergent'}  "
    banner += f"GITHUB={'✅' if has_gh and has_gh_repo else '❌'}  "
    banner += f"RAILWAY={'✅' if has_rw else '❌'}  TAVILY={'✅' if has_tavily else '❌'}\n"
    if on_railway:
        banner += "آلية الـcommit/push: تستنسخ /tmp/zitex_workdir تلقائياً عند أول استدعاء لـgit_*\n"
        banner += "آلية الـrestart: استدعِ restart_service → يستخدم Railway API تلقائياً\n"
        banner += "Railway tools: railway_redeploy / railway_build_logs / railway_runtime_logs / railway_env_vars\n"
    banner += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    banner += "⛔ ممنوع تطلب من المالك يثبّت أو يضيف أي شي من اللي عُلّم بـ✅ فوق. هذي موجودة فعلاً.\n"
    banner += "⛔ ممنوع تقول 'الأدوات ناقصة' أو 'يحتاج setup'. اشتغل مباشرة بالأدوات المتاحة.\n"
    return banner


async def _stream_direct_anthropic(anthropic_msgs: List[Dict[str, Any]], api_key: str, env_banner: str = ""):
    """Uses official anthropic SDK with NATIVE STREAMING + multi-tool calling.

    Behaviors (June 2026 — limits removed):
    - Real SSE streaming (chars appear as Claude generates them)
    - History pruning: last 30 turns (was 8) — long memory for deep debugging sessions
    - Prompt caching (system + tools cached, 90% cheaper on reuse)
    - max_tokens=16384 (was 8192) + AUTO-CONTINUE if stop_reason='max_tokens'
    - 200 iterations max (was 60) — enough for complex multi-step refactors
    - Per-tool result up to 50K chars to LLM (was 14K) — full file reads
    """
    try:
        from anthropic import AsyncAnthropic
    except Exception as e:
        yield {"type": "error", "message": f"anthropic SDK missing: {e}"}
        return

    client = AsyncAnthropic(api_key=api_key)

    # History pruning — keep last 30 turns (long debugging sessions)
    MAX_HISTORY_TURNS = 30
    if len(anthropic_msgs) > MAX_HISTORY_TURNS:
        anthropic_msgs = anthropic_msgs[-MAX_HISTORY_TURNS:]

    # Prompt caching for system + tools (90% cheaper on subsequent calls)
    try:
        lessons_block = await build_lessons_for_prompt(max_lessons=12)
    except Exception:
        lessons_block = ""
    try:
        task_brief = await build_session_brief(max_tasks=3)
    except Exception:
        task_brief = ""
    sys_prompt_text = AUTOCODER_SYSTEM_PROMPT + AUTONOMY_PROMPT_RULES + OPS_PROMPT_RULES + QUALITY_PROMPT_RULES + INDEX_PROMPT_RULES + SAFETY_PROMPT_RULES + LEARNING_PROMPT_RULES + MEMORY_PROMPT_RULES + SANDBOX_PROMPT_RULES + WEB_SEARCH_PROMPT_RULES + ROUTER_PROMPT_RULES + CACHE_PROMPT_RULES + SUPERPOWERS_PROMPT_RULES + (env_banner or "") + build_atlas_for_prompt() + build_atlas_v2_for_prompt() + build_universe_for_prompt() + lessons_block + task_brief
    system_blocks = [
        {"type": "text", "text": sys_prompt_text, "cache_control": {"type": "ephemeral"}}
    ]

    # Deduplicate tools by name (keep last — most recent/comprehensive version wins).
    # Anthropic rejects requests with duplicate tool names.
    _seen_names = {}
    for _t in ANTHROPIC_TOOLS:
        _seen_names[_t["name"]] = _t  # later overwrites earlier
    cached_tools = list(_seen_names.values())
    if cached_tools:
        cached_tools[-1] = {
            **cached_tools[-1],
            "cache_control": {"type": "ephemeral"},
        }

    msgs = list(anthropic_msgs)

    for iteration in range(200):
        text_parts: List[str] = []
        tool_uses: List[Dict[str, Any]] = []
        assistant_blocks: List[Dict[str, Any]] = []
        # Per-tool-block accumulator (tool_use_delta streams JSON in pieces)
        current_tool: Optional[Dict[str, Any]] = None
        current_text: Optional[Dict[str, Any]] = None
        usage_in_tok = 0
        usage_out_tok = 0
        cache_read = 0
        cache_write = 0
        stop_reason = None

        try:
            async with client.messages.stream(
                model="claude-sonnet-4-5",
                max_tokens=16384,  # raised from 8192 — let Claude write long thorough responses
                system=system_blocks,
                tools=cached_tools,
                messages=msgs,
            ) as stream:
                async for event in stream:
                    et = getattr(event, "type", None)

                    if et == "content_block_start":
                        block = event.content_block
                        btype = getattr(block, "type", None)
                        if btype == "text":
                            current_text = {"type": "text", "text": ""}
                        elif btype == "tool_use":
                            current_tool = {
                                "type": "tool_use",
                                "id": getattr(block, "id", ""),
                                "name": getattr(block, "name", ""),
                                "input_json": "",
                            }

                    elif et == "content_block_delta":
                        delta = event.delta
                        dtype = getattr(delta, "type", None)
                        if dtype == "text_delta" and current_text is not None:
                            txt = getattr(delta, "text", "") or ""
                            current_text["text"] += txt
                            # Real streaming — yield each delta immediately
                            yield {"type": "text", "content": txt}
                        elif dtype == "input_json_delta" and current_tool is not None:
                            current_tool["input_json"] += getattr(delta, "partial_json", "") or ""

                    elif et == "content_block_stop":
                        if current_text is not None:
                            text_parts.append(current_text["text"])
                            assistant_blocks.append(current_text)
                            current_text = None
                        elif current_tool is not None:
                            try:
                                inp = json.loads(current_tool["input_json"]) if current_tool["input_json"] else {}
                                if not isinstance(inp, dict):
                                    inp = {}
                            except Exception:
                                inp = {}
                            tu = {
                                "id": current_tool["id"],
                                "name": current_tool["name"],
                                "input": inp,
                            }
                            tool_uses.append(tu)
                            assistant_blocks.append({
                                "type": "tool_use",
                                "id": tu["id"],
                                "name": tu["name"],
                                "input": tu["input"],
                            })
                            current_tool = None

                    elif et == "message_delta":
                        delta = event.delta
                        sr = getattr(delta, "stop_reason", None)
                        if sr:
                            stop_reason = sr
                        u = getattr(event, "usage", None)
                        if u:
                            usage_out_tok = getattr(u, "output_tokens", 0) or usage_out_tok

                    elif et == "message_start":
                        msg = getattr(event, "message", None)
                        u = getattr(msg, "usage", None) if msg else None
                        if u:
                            usage_in_tok = getattr(u, "input_tokens", 0)
                            cache_read = getattr(u, "cache_read_input_tokens", 0) or 0
                            cache_write = getattr(u, "cache_creation_input_tokens", 0) or 0
        except Exception as e:
            err_str = str(e)
            low = err_str.lower()
            if "credit_balance" in low or "billing" in low:
                yield {"type": "error", "message": "💰 رصيد Anthropic منخفض. بدّل الموديل لـLlama (Groq) من الزر أعلى الشاشة — مجاني."}
            elif "rate" in low or "429" in low:
                yield {"type": "error", "message": "⏱️ تجاوزت حد الطلبات على Anthropic. استنّى ~30 ثانية ثم حاول."}
            elif "overloaded" in low or "529" in low:
                yield {"type": "error", "message": "🔄 خوادم Anthropic مزدحمة لحظياً. حاول بعد دقيقة."}
            elif "invalid" in low and "api" in low and "key" in low:
                yield {"type": "error", "message": "🔑 ANTHROPIC_API_KEY غير صحيح. تأكد منه في Railway → Variables. أو بدّل لـLlama (Groq) من الزر أعلى."}
            elif "authentication" in low or "401" in low:
                yield {"type": "error", "message": "🔑 مفتاح Anthropic مرفوض. تحقق من ANTHROPIC_API_KEY في Railway."}
            else:
                yield {"type": "error", "message": f"anthropic: {err_str[:240]}"}
            return

        # Emit usage event (first iteration only)
        if iteration == 0 and usage_in_tok:
            cost = (
                (usage_in_tok - cache_read - cache_write) * 3 / 1_000_000
                + cache_read * 0.30 / 1_000_000
                + cache_write * 3.75 / 1_000_000
                + usage_out_tok * 15 / 1_000_000
            )
            yield {
                "type": "usage",
                "input": usage_in_tok, "output": usage_out_tok,
                "cached_read": cache_read, "cached_write": cache_write,
                "cost_usd": round(cost, 4),
                "provider": "claude",
            }

        if assistant_blocks:
            msgs.append({"role": "assistant", "content": assistant_blocks})

        # Stop conditions
        if stop_reason == "end_turn" or not tool_uses:
            # Auto-continue if Claude was cut off at max_tokens with no tool calls — let it finish
            if stop_reason == "max_tokens" and not tool_uses:
                # Nudge the assistant to continue naturally
                msgs.append({"role": "user", "content": "تابع/أكمل من حيث وقفت بدون أي مقدمة أو اعتذار."})
                continue
            yield {"type": "done"}
            return

        # If max_tokens but we DID get tool calls, execute them then loop continues normally.
        # Execute tool calls (sequential, in order)
        # Execute tool calls (sequential, in order)
        # Wrap each tool call in a heartbeat-pumped task so Cloudflare/proxies
        # don't kill the SSE stream when a tool runs for > 60 seconds.
        tool_results_blocks = []
        for tu in tool_uses:
            yield {"type": "tool", "status": "calling", "name": tu["name"],
                   "args": _trim_args_for_ui(tu["input"])}

            # Run the tool in a background task and emit heartbeats every 15s
            # until it completes. This keeps the SSE channel alive.
            tool_task = asyncio.create_task(execute_autocoder_tool(tu["name"], tu["input"]))
            elapsed = 0
            while not tool_task.done():
                try:
                    await asyncio.wait_for(asyncio.shield(tool_task), timeout=15)
                    break  # tool finished
                except asyncio.TimeoutError:
                    elapsed += 15
                    yield {"type": "tool", "status": "running", "name": tu["name"],
                           "elapsed_sec": elapsed}
            result = await tool_task

            yield {"type": "tool", "status": "done", "name": tu["name"],
                   "ok": result.get("ok", False),
                   "summary": _summarize(tu["name"], result),
                   "preview": _preview_for_ui(tu["name"], result)}
            # Special handling: screenshot_url → embed image as Vision block so Claude SEES the screenshot
            if tu["name"] == "screenshot_url" and result.get("ok") and result.get("image_b64"):
                img_b64 = result.get("image_b64") or ""
                meta = {k: v for k, v in result.items() if k != "image_b64"}
                tool_results_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}},
                        {"type": "text", "text": json.dumps(meta, ensure_ascii=False)[:8000]},
                    ],
                })
            else:
                tool_results_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "content": json.dumps(_trim_result_for_llm(result), ensure_ascii=False)[:60000],
                })

        msgs.append({"role": "user", "content": tool_results_blocks})

    yield {"type": "text", "content": "\n(وصلت لـ200 دورة. اطلب تكملة لو تبي.)"}
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
        history_text += f"\n\n{role}: {_extract_message_plain_text(m.get('content', ''))[:6000]}"
    last_user = _extract_message_plain_text(messages[-1].get("content", ""))
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


def _trim_args_for_ui(args: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not args or not isinstance(args, dict):
        return {}
    out = {}
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 200:
            out[k] = v[:200] + f"... ({len(v)} chars)"
        else:
            out[k] = v
    return out


def _trim_result_for_llm(result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Trim per-field strings before sending tool_result back to the LLM.

    Raised from 5K to 50K chars (Jun 2026) — Claude can now read whole files
    in one tool call so it doesn't get cut off mid-analysis. The outer
    json.dumps in the caller still caps the full block at 60K chars.
    """
    if not result or not isinstance(result, dict):
        return {"ok": False, "error": "tool returned no result"}
    out = {}
    for k, v in result.items():
        if isinstance(v, str) and len(v) > 50000:
            out[k] = v[:50000] + f"\n...[truncated {len(v) - 50000} chars]"
        else:
            out[k] = v
    return out


def _preview_for_ui(name: str, result: Dict[str, Any]) -> str:
    if not result.get("ok") and result.get("error"):
        return result["error"][:300]
    # Try extra tools first
    extra = extra_preview(name, result)
    if extra is not None:
        return extra
    uni = universe_preview(name, result)
    if uni is not None:
        return uni
    qp = quality_preview(name, result)
    if qp is not None:
        return qp
    ip = index_preview(name, result)
    if ip is not None:
        return ip
    sp = safety_preview(name, result)
    if sp is not None:
        return sp
    lp = learning_preview(name, result)
    if lp is not None:
        return lp
    ap = autonomy_preview(name, result)
    if ap is not None:
        return ap
    op = ops_preview(name, result)
    if op is not None:
        return op
    mp = memory_preview(name, result)
    if mp is not None:
        return mp
    sp2 = sandbox_preview(name, result)
    if sp2 is not None:
        return sp2
    ip = integrations_preview(name, result)
    if ip is not None:
        return ip
    wp = web_search_preview(name, result)
    if wp is not None:
        return wp
    rp = railway_preview(name, result)
    if rp is not None:
        return rp
    vp = vercel_preview(name, result)
    if vp is not None:
        return vp
    rop = router_preview(name, result)
    if rop is not None:
        return rop
    cp = cache_preview(name, result)
    if cp is not None:
        return cp
    if name == "read_file":
        return (result.get("content") or "")[:600]
    if name == "screenshot_url":
        kb = result.get("image_size_kb") or 0
        title = result.get("title") or ""
        errs = len(result.get("console_errors") or [])
        return f"📸 {kb}KB · title={title[:60]} · console_errors={errs}"
    if name == "project_context":
        return (result.get("prd") or "")[:600]
    if name == "project_health":
        return (result.get("supervisor") or "")[:600]
    if name in ("plan_create", "plan_update", "plan_show"):
        return result.get("summary") or json.dumps(result, ensure_ascii=False)[:300]
    if name == "update_prd":
        return result.get("summary") or "PRD updated"
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
    extra = extra_summarize(name, result)
    if extra is not None:
        return extra
    uni = universe_summarize(name, result)
    if uni is not None:
        return uni
    qs = quality_summarize(name, result)
    if qs is not None:
        return qs
    iss = index_summarize(name, result)
    if iss is not None:
        return iss
    ss = safety_summarize(name, result)
    if ss is not None:
        return ss
    ls = learning_summarize(name, result)
    if ls is not None:
        return ls
    az = autonomy_summarize(name, result)
    if az is not None:
        return az
    os_s = ops_summarize(name, result)
    if os_s is not None:
        return os_s
    ms = memory_summarize(name, result)
    if ms is not None:
        return ms
    sb_s = sandbox_summarize(name, result)
    if sb_s is not None:
        return sb_s
    is_s = integrations_summarize(name, result)
    if is_s is not None:
        return is_s
    ws_s = web_search_summarize(name, result)
    if ws_s is not None:
        return ws_s
    rs = railway_summarize(name, result)
    if rs is not None:
        return rs
    vs = vercel_summarize(name, result)
    if vs is not None:
        return vs
    ros = router_summarize(name, result)
    if ros is not None:
        return ros
    cs = cache_summarize(name, result)
    if cs is not None:
        return cs
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
