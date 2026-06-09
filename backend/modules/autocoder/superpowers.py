"""Autocoder superpowers — Project Memory, Vision (screenshot URLs), Planning, PRD writer.

These tools give the AutoCoder the same 6 capabilities the main E1 agent has:
  1. project_context — auto-loads PRD/CHANGELOG/design_guidelines/test_creds/commits
  2. screenshot_url — captures a live URL via Playwright → returns image for Claude Vision
  3. plan_create / plan_update — visible TodoList in the UI
  4. update_prd — appends to /app/memory/PRD.md and CHANGELOG.md
  5. read_recent_changes — git diff of last N commits
  6. project_health — runs lint + status checks + returns summary
"""
import asyncio
import base64
import json
import logging
import os
import secrets
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zerax.autocoder.superpowers")

MEMORY_DIR = Path("/app/memory")
PRD_PATH = MEMORY_DIR / "PRD.md"
CHANGELOG_PATH = MEMORY_DIR / "CHANGELOG.md"
DESIGN_PATH = Path("/app/design_guidelines.md")
TEST_CREDS_PATH = MEMORY_DIR / "test_credentials.md"
PLAN_PATH = MEMORY_DIR / "autocoder_plan.json"


def _read(path: Path, max_chars: int = 12000) -> str:
    try:
        if path.exists() and path.is_file():
            content = path.read_text(encoding="utf-8", errors="replace")
            if len(content) > max_chars:
                return content[:max_chars] + f"\n\n...[truncated, total {len(content)} chars]"
            return content
    except Exception as e:
        return f"[error reading {path}: {e}]"
    return f"[{path.name} not found]"


# ─── Tool 1: project_context ───────────────────────────────
async def tool_project_context() -> Dict[str, Any]:
    """Auto-loads memory files + recent commits + repo overview.

    Call this FIRST on a new conversation to understand what's been built.
    Equivalent to the E1 agent reading handoff_summary + PRD + last 5 commits.
    """
    out: Dict[str, Any] = {"ok": True}
    out["prd"] = _read(PRD_PATH, max_chars=20000)
    out["changelog"] = _read(CHANGELOG_PATH, max_chars=8000)
    out["design_guidelines"] = _read(DESIGN_PATH, max_chars=5000)
    out["test_credentials"] = _read(TEST_CREDS_PATH, max_chars=4000)

    # Recent commits (last 15)
    try:
        proc = await asyncio.create_subprocess_shell(
            "cd /app && git log --pretty=format:'%h %ai %an | %s' -15",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        out["recent_commits"] = (stdout or b"").decode("utf-8", errors="replace")
    except Exception as e:
        out["recent_commits"] = f"[error: {e}]"

    # Current git status (modified files)
    try:
        proc = await asyncio.create_subprocess_shell(
            "cd /app && git status --short && echo --- && git rev-parse HEAD",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        out["git_status"] = (stdout or b"").decode("utf-8", errors="replace")
    except Exception as e:
        out["git_status"] = f"[error: {e}]"

    # Repo overview
    try:
        proc = await asyncio.create_subprocess_shell(
            "cd /app && fd . backend/modules frontend/src/pages -d 1 -t d 2>/dev/null | head -30",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        out["repo_overview"] = (stdout or b"").decode("utf-8", errors="replace")
    except Exception:
        out["repo_overview"] = "[skipped]"

    return out


# ─── Tool 2: screenshot_url (Vision) ───────────────────────
async def tool_screenshot_url(url: str, viewport: str = "1920x1080", wait_ms: int = 5000) -> Dict[str, Any]:
    """Capture a screenshot of a live URL using Playwright.

    Returns base64-encoded JPEG. The AutoCoder router will convert this
    to a Claude Vision content block on the next turn so the AI can SEE
    the deployed site (just like E1).
    """
    try:
        try:
            w, h = viewport.split("x")
            w, h = int(w), int(h)
        except Exception:
            w, h = 1920, 1080

        # Use a small Python script via Playwright (already installed for screenshot_tool)
        script = f"""
import asyncio
from playwright.async_api import async_playwright
import base64, sys

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = await browser.new_page(viewport={{'width': {w}, 'height': {h}}})
        errors = []
        page.on('console', lambda m: errors.append(f'[{{m.type}}] {{m.text[:200]}}') if m.type in ('error','warning') else None)
        page.on('pageerror', lambda e: errors.append(f'[pageerror] {{str(e)[:200]}}'))
        try:
            # First domcontentloaded so we don't block forever on slow third-party scripts
            await page.goto({url!r}, wait_until='domcontentloaded', timeout=45000)
            # Then try to reach networkidle so React/SPAs finish rendering
            try:
                await page.wait_for_load_state('networkidle', timeout=15000)
            except Exception:
                pass
            await page.wait_for_timeout({wait_ms})
            img = await page.screenshot(type='jpeg', quality=55, full_page=False)
            title = await page.title()
            body_len = len(await page.locator('body').text_content() or '')
            body_preview = (await page.locator('body').text_content() or '')[:600]
            url_final = page.url
        finally:
            await browser.close()
        import json
        print(json.dumps({{
            'image_b64': base64.b64encode(img).decode(),
            'title': title,
            'url_final': url_final,
            'body_len': body_len,
            'body_preview': body_preview,
            'console_errors': errors[:20],
        }}))

asyncio.run(main())
"""
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", script,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
        if proc.returncode != 0:
            return {"ok": False, "error": f"playwright failed: {(stderr or b'').decode()[:500]}"}
        data = json.loads(stdout.decode())
        return {
            "ok": True,
            "image_b64": data["image_b64"],  # for vision passthrough
            "image_size_kb": len(data["image_b64"]) * 3 // 4 // 1024,
            "title": data.get("title"),
            "url_final": data.get("url_final"),
            "body_text_length": data.get("body_len"),
            "body_preview": data.get("body_preview", ""),
            "console_errors": data.get("console_errors", []),
            "summary": (
                f"📸 screenshot of {url} · title='{(data.get('title') or '')[:50]}' · "
                f"body={data.get('body_len',0)} chars · "
                f"console_errors={len(data.get('console_errors',[]))}"
            ),
        }
    except asyncio.TimeoutError:
        return {"ok": False, "error": "screenshot timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


# ─── Tools 3+4: plan_create / plan_update (TodoList) ───────
def _load_plan() -> Dict[str, Any]:
    if PLAN_PATH.exists():
        try:
            return json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"plan_id": secrets.token_hex(6), "title": "", "items": [], "updated_at": ""}


def _save_plan(plan: Dict[str, Any]) -> None:
    plan["updated_at"] = datetime.now(timezone.utc).isoformat()
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    PLAN_PATH.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


async def tool_plan_create(title: str, items: List[str]) -> Dict[str, Any]:
    """Create a new TodoList for the current task. Visible in UI."""
    plan = {
        "plan_id": secrets.token_hex(6),
        "title": title,
        "items": [{"text": it, "done": False, "skipped": False} for it in items],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_plan(plan)
    return {"ok": True, "plan_id": plan["plan_id"], "count": len(plan["items"]),
            "summary": f"خطة جديدة '{title}' بـ{len(items)} خطوة"}


async def tool_plan_update(index: int, done: Optional[bool] = None, skipped: Optional[bool] = None,
                           new_text: Optional[str] = None) -> Dict[str, Any]:
    """Mark an item done/skipped or rewrite it."""
    plan = _load_plan()
    items = plan.get("items", [])
    if not 0 <= index < len(items):
        return {"ok": False, "error": f"index out of range (have {len(items)} items)"}
    if done is not None:
        items[index]["done"] = bool(done)
    if skipped is not None:
        items[index]["skipped"] = bool(skipped)
    if new_text:
        items[index]["text"] = new_text
    _save_plan(plan)
    done_count = sum(1 for it in items if it.get("done"))
    return {"ok": True, "progress": f"{done_count}/{len(items)}",
            "summary": f"تم تحديث الخطوة {index+1}: {items[index].get('text','')[:80]}"}


async def tool_plan_show() -> Dict[str, Any]:
    plan = _load_plan()
    items = plan.get("items", [])
    done_count = sum(1 for it in items if it.get("done"))
    return {"ok": True, "title": plan.get("title", ""), "items": items,
            "progress": f"{done_count}/{len(items)}",
            "summary": f"الخطة: {plan.get('title','')} · {done_count}/{len(items)} مكتمل"}


# ─── Tool 5: update_prd (write to memory) ─────────────────
async def tool_update_prd(section: str, content: str, append: bool = True) -> Dict[str, Any]:
    """Update /app/memory/PRD.md by adding a section or replacing.

    section: heading name (e.g. "🆕 Jun 5 2026 — Marketing UI launched")
    content: markdown content
    append: True = add at top under main title (recommended for new entries)
    """
    try:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        existing = PRD_PATH.read_text(encoding="utf-8") if PRD_PATH.exists() else "# Zerax AI Platform - PRD\n\n"

        new_block = f"\n### {section}\n\n{content.strip()}\n\n---\n"
        if append and existing.startswith("#"):
            # Insert right after the H1 title
            lines = existing.split("\n", 2)
            updated = lines[0] + "\n" + new_block + ("\n".join(lines[1:]) if len(lines) > 1 else "")
        else:
            updated = existing + new_block

        PRD_PATH.write_text(updated, encoding="utf-8")

        # Also mirror into CHANGELOG.md
        ts = datetime.now(timezone.utc).isoformat()[:19]
        try:
            cl_existing = CHANGELOG_PATH.read_text(encoding="utf-8") if CHANGELOG_PATH.exists() else "# Zerax Changelog\n\n"
            cl_new = f"\n## {ts} — {section}\n\n{content.strip()}\n"
            CHANGELOG_PATH.write_text(cl_existing + cl_new, encoding="utf-8")
        except Exception:
            pass

        return {"ok": True, "path": str(PRD_PATH), "size_bytes": len(updated),
                "summary": f"تم تحديث PRD.md: {section}"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


# ─── Tool 6: project_health ───────────────────────────────
async def tool_project_health() -> Dict[str, Any]:
    """Quick health check: supervisor status + last 50 backend log lines + git status."""
    out: Dict[str, Any] = {"ok": True}
    cmds = {
        "supervisor": "sudo supervisorctl status 2>&1 | head -10",
        "backend_logs": "tail -30 /var/log/supervisor/backend.err.log 2>&1 | tail -30",
        "frontend_logs": "tail -10 /var/log/supervisor/frontend.err.log 2>&1 | tail -10",
        "git_status": "cd /app && git status --short && echo --- && git rev-parse --short HEAD",
        "disk": "df -h / | tail -1",
    }
    for name, cmd in cmds.items():
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            out[name] = (stdout or b"").decode("utf-8", errors="replace")[:3000]
        except Exception as e:
            out[name] = f"[error: {e}]"
    return out


# ─── Anthropic tool schemas ───────────────────────────────
SUPERPOWERS_ANTHROPIC_TOOLS = [
    {
        "name": "project_context",
        "description": "اقرأ سياق المشروع كاملاً: PRD + CHANGELOG + design_guidelines + test_credentials + آخر 15 commit + حالة git. **استدعِ هذي الأداة أول شي على بداية أي محادثة جديدة** لتفهم وش بُني، وش قيد العمل، ووش الأولويات. زي ما يفعل E1 agent.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "screenshot_url",
        "description": "خذ screenshot للـ URL منشور (Vercel/Railway/preview) — يستخدم Playwright. ترجع الصورة بـbase64 + الـconsole errors + body text length. **استخدمه بعد كل push على Vercel** للتحقق البصري إن التغيير ظهر فعلاً.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "الـURL الكامل (e.g. https://zerax.vercel.app/games/web)"},
                "viewport": {"type": "string", "description": "WxH (default 1920x1080)"},
                "wait_ms": {"type": "integer", "description": "كم millisecond ينتظر قبل الـscreenshot (default 3000)"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "plan_create",
        "description": "أنشئ TodoList للمهمة الحالية. خطوات واضحة قابلة للتنفيذ. **استدعها قبل ما تبدأ أي مهمة معقدة** (3+ خطوات). تظهر في الـUI للمالك.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "عنوان المهمة"},
                "items": {"type": "array", "items": {"type": "string"}, "description": "قائمة الخطوات"},
            },
            "required": ["title", "items"],
        },
    },
    {
        "name": "plan_update",
        "description": "حدّث خطوة في الـTodoList: done=true لما تخلص خطوة، skipped=true لو ما لزمت، new_text لإعادة صياغة.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index": {"type": "integer", "description": "رقم الخطوة (0-based)"},
                "done": {"type": "boolean"},
                "skipped": {"type": "boolean"},
                "new_text": {"type": "string"},
            },
            "required": ["index"],
        },
    },
    {
        "name": "plan_show",
        "description": "اعرض الـTodoList الحالية مع التقدم.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "update_prd",
        "description": "أضف entry جديد لـ /app/memory/PRD.md (أعلى الملف) وأيضاً لـ CHANGELOG.md. **استدعها بعد كل feature مكتمل** عشان الذكاء في الجلسات القادمة يقدر يقرأ التاريخ.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {"type": "string", "description": "عنوان مع تاريخ (e.g. '🆕 Jun 5 2026 — Marketing UI launched')"},
                "content": {"type": "string", "description": "محتوى Markdown يلخص ما تم"},
                "append": {"type": "boolean", "description": "True = أضف أعلى الملف (افتراضي)"},
            },
            "required": ["section", "content"],
        },
    },
    {
        "name": "project_health",
        "description": "فحص صحة سريع: supervisor status + backend logs (30 سطر) + frontend logs + git status + disk usage. **استدعها قبل ما تبدأ تشخيص أي مشكلة.**",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

SUPERPOWERS_HANDLERS = {
    "project_context": tool_project_context,
    "screenshot_url": tool_screenshot_url,
    "plan_create": tool_plan_create,
    "plan_update": tool_plan_update,
    "plan_show": tool_plan_show,
    "update_prd": tool_update_prd,
    "project_health": tool_project_health,
}


SUPERPOWERS_PROMPT_RULES = """

🦸‍♂️ **قدرات خارقة جديدة (Superpowers)** — استخدمها بذكاء:

1. **`project_context`** — استدعها **أول شي** في أي محادثة جديدة (قبل أي قراءة ملف). ترجع لك PRD + CHANGELOG + design_guidelines + test_credentials + آخر 15 commit + git status. هذي ذاكرتك بين الجلسات. لا تعيد كل اشتغلت عليه قبل — اقرأ السياق أولاً.

2. **`screenshot_url`** — بعد أي push على Vercel/Railway، خذ screenshot للـURL المنشور وتأكد إن التغيير ظهر فعلاً. الصورة ترجع base64 وأنت قادر تشوفها (Vision). افتح console_errors لو فيه أخطاء.

3. **`plan_create` + `plan_update` + `plan_show`** — قبل أي مهمة معقدة (3+ خطوات)، أنشئ TodoList واضحة. حدّث كل خطوة لما تخلصها. هذا يخلّي المالك يشوف تقدّمك.

4. **`update_prd`** — بعد كل feature مكتمل، أضف entry جديد لـ `/app/memory/PRD.md` (وعلى CHANGELOG.md تلقائياً) عشان الجلسات القادمة تعرف وش بنيت.

5. **`project_health`** — قبل أي تشخيص لمشكلة، شغّلها لتفهم حالة supervisor + آخر backend/frontend logs + git status.

⚡️ **القاعدة الذهبية**: لا تشتغل أعمى. اقرأ السياق → خطّط → نفّذ → تحقّق بـscreenshot → حدّث الـPRD.
"""


SUPERPOWERS_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "project_context", "desc": "read PRD/CHANGELOG/design/creds/commits", "args": []},
    {"name": "screenshot_url", "desc": "capture live URL via playwright", "args": ["url", "viewport?", "wait_ms?"]},
    {"name": "plan_create", "desc": "create TodoList", "args": ["title", "items"]},
    {"name": "plan_update", "desc": "update TodoList item", "args": ["index", "done?", "skipped?", "new_text?"]},
    {"name": "plan_show", "desc": "show current TodoList", "args": []},
    {"name": "update_prd", "desc": "append entry to PRD.md + CHANGELOG.md", "args": ["section", "content", "append?"]},
    {"name": "project_health", "desc": "supervisor+logs+git status", "args": []},
]
