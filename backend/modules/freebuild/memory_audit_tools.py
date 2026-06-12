"""
Zenrex AI Brain — Memory + Audit + Plan-tracking Tools (Phase 4).

Three families of capability:

1. update_plan_step  — Mark a step in an active plan as done/in-progress/failed.
                       Wires the visual plan card to REAL tool progress (no more
                       timer-based animation).

2. memory_save / memory_recall / memory_list / memory_delete
   — Persistent project memory across sessions. Auto-injected into the system
     prompt on every chat turn so the AI never "forgets" customer preferences,
     shop facts, brand guidelines, or technical decisions.

3. audit_project    — Comprehensive multi-angle audit of the current site.
                       Runs HTML validation, JS lint, then spawns 4 specialist
                       reviews (security, performance, SEO, a11y) in parallel,
                       plus a live test_page render. Returns a scored report.
                       Shows live progress to the user via SSE.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.memory_audit_tools")


PHASE4_TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "update_plan_step",
        "description": (
            "🔄 Update a step's status in an active plan card. Call this RIGHT AFTER "
            "you finish a step from a plan you announced with `plan_task`. Status: "
            "'in_progress' when you START the step, 'done' when it succeeds, 'failed' "
            "if it failed. This makes the user's plan card show REAL progress live."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "The plan_id returned by plan_task."},
                "step_index": {"type": "integer", "minimum": 0, "description": "0-based index of the step."},
                "status": {"type": "string", "enum": ["in_progress", "done", "failed"]},
                "note": {"type": "string", "description": "Optional one-line note shown under the step."},
            },
            "required": ["plan_id", "step_index", "status"],
        },
    },
    {
        "name": "memory_save",
        "description": (
            "🧠 Save a piece of long-term memory for this project. Persists ACROSS "
            "chat sessions and gets auto-injected into the system prompt so future "
            "you remembers it. Use for: customer preferences ('يحب الألوان الذهبية'), "
            "shop facts ('متجر برجر، 8 فروع في الرياض'), brand guidelines "
            "('الخط الرئيسي Tajawal'), technical decisions ('قرّرنا نستخدم Moyasar')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "snake_case key, e.g. 'brand_colors', 'preferred_payment'."},
                "value": {"type": "string", "description": "The memory content (max 1000 chars)."},
                "scope": {"type": "string", "enum": ["project", "merchant"], "default": "project",
                           "description": "'project' = this project only. 'merchant' = visible in ALL projects of this merchant."},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "memory_recall",
        "description": (
            "🔍 Recall a specific memory by key. Returns the value or null. Most of "
            "the time you DON'T need this — memories are auto-loaded into your "
            "system prompt at the start of every chat. Use only for very specific lookups."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "scope": {"type": "string", "enum": ["project", "merchant", "any"], "default": "any"},
            },
            "required": ["key"],
        },
    },
    {
        "name": "memory_list",
        "description": "📋 List ALL stored memories for this project + merchant. Returns key/value/scope/updated_at.",
        "input_schema": {
            "type": "object",
            "properties": {
                "scope": {"type": "string", "enum": ["project", "merchant", "any"], "default": "any"},
            },
            "required": [],
        },
    },
    {
        "name": "memory_delete",
        "description": "🗑️ Delete a stored memory by key. Use when info is outdated/wrong.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "scope": {"type": "string", "enum": ["project", "merchant"], "default": "project"},
            },
            "required": ["key"],
        },
    },
    {
        "name": "audit_project",
        "description": (
            "🔍 COMPREHENSIVE multi-angle audit of the current site. Runs in this order: "
            "(1) HTML structure validation, (2) JavaScript lint, (3) live page test via "
            "Playwright (real browser, screenshots, console errors), (4) Security review "
            "by specialist sub-agent, (5) Performance review, (6) SEO review, "
            "(7) Accessibility (RTL/Arabic-aware) review. Returns scored report per "
            "category + overall grade. Takes 30-60 seconds but the user sees every "
            "step live. Use when the user asks 'راجع الموقع' or 'دقّق' or before a "
            "major launch."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "include_visual_test": {"type": "boolean", "default": True,
                                         "description": "Run live test_page (slower, ~10s)."},
                "include_specialists": {"type": "boolean", "default": True,
                                         "description": "Run the 4 specialist reviews (slower, ~20s)."},
                "live_url": {"type": "string",
                             "description": "Optional already-published URL to test. If absent, uses the current_html."},
            },
            "required": [],
        },
    },
]


PHASE4_TOOL_LABELS_AR: Dict[str, Dict[str, str]] = {
    "update_plan_step": {"running": "🔄 يحدّث حالة الخطوة...",
                          "done": "✅ تم تحديث الخطوة"},
    "memory_save":      {"running": "🧠 يحفظ في الذاكرة الطويلة...",
                          "done": "✅ تم الحفظ في الذاكرة"},
    "memory_recall":    {"running": "🔍 يستعيد من الذاكرة...",
                          "done": "✅ تم الاستعادة"},
    "memory_list":      {"running": "📋 يعرض كل الذكريات...",
                          "done": "✅ القائمة جاهزة"},
    "memory_delete":    {"running": "🗑️ يحذف من الذاكرة...",
                          "done": "✅ تم الحذف"},
    "audit_project":    {"running": "🔍 يُجري تدقيقاً شاملاً (قد يستغرق ~30 ثانية)...",
                          "done": "✅ التدقيق اكتمل"},
}


PHASE4_TOOL_NAMES: tuple = tuple(t["name"] for t in PHASE4_TOOL_SCHEMAS)


# ─── update_plan_step ────────────────────────────────────────────────────────
async def update_plan_step(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if ctx.db is None or not ctx.project_id:
        return {"ok": False, "error": "DB or project_id missing"}
    plan_id = (args.get("plan_id") or "").strip()
    idx = args.get("step_index")
    status = (args.get("status") or "").strip().lower()
    note = (args.get("note") or "").strip()[:240]
    if not plan_id or status not in ("in_progress", "done", "failed"):
        return {"ok": False, "error": "plan_id and valid status required"}
    if not isinstance(idx, int) or idx < 0:
        return {"ok": False, "error": "step_index must be a non-negative int"}
    try:
        # Update the specific step inside the plan document
        plan = await ctx.db.freebuild_plans.find_one({"id": plan_id})
        if not plan:
            return {"ok": False, "error": f"plan '{plan_id}' not found"}
        steps = plan.get("steps") or []
        if idx >= len(steps):
            return {"ok": False, "error": f"step_index {idx} out of range (plan has {len(steps)} steps)"}
        steps[idx]["status"] = status
        if note:
            steps[idx]["note"] = note
        steps[idx]["updated_at"] = time.time()
        await ctx.db.freebuild_plans.update_one(
            {"id": plan_id},
            {"$set": {"steps": steps, "last_update": time.time()}},
        )
        return {
            "ok": True,
            "kind": "plan_step_update",
            "plan_id": plan_id,
            "step_index": idx,
            "status": status,
            "note": note,
            "step_text": steps[idx].get("text", ""),
            "message": f"✓ خطوة #{idx + 1} = {status}",
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


# ─── Memory tools ────────────────────────────────────────────────────────────
def _project_merchant_id(ctx) -> Optional[str]:
    try:
        p = ctx.project or {}
        return p.get("merchant_id") or p.get("user_id") or p.get("owner_id")
    except Exception:
        return None


async def memory_save(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if ctx.db is None or not ctx.project_id:
        return {"ok": False, "error": "DB or project_id missing"}
    key = (args.get("key") or "").strip().lower()
    value = (args.get("value") or "").strip()
    scope = (args.get("scope") or "project").strip().lower()
    if not re.match(r"^[a-z][a-z0-9_]{1,60}$", key):
        return {"ok": False, "error": "key must be snake_case, 2-60 chars"}
    if not value or len(value) > 1000:
        return {"ok": False, "error": "value must be 1-1000 chars"}
    if scope not in ("project", "merchant"):
        return {"ok": False, "error": "scope must be 'project' or 'merchant'"}
    try:
        owner = {"project_id": ctx.project_id} if scope == "project" else {"merchant_id": _project_merchant_id(ctx)}
        if scope == "merchant" and not owner.get("merchant_id"):
            return {"ok": False, "error": "no merchant_id on project — cannot save merchant-scoped memory"}
        now = time.time()
        await ctx.db.freebuild_memories.update_one(
            {**owner, "scope": scope, "key": key},
            {"$set": {**owner, "scope": scope, "key": key, "value": value, "updated_at": now},
             "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        return {"ok": True, "key": key, "scope": scope,
                "message": f"🧠 محفوظ في الذاكرة الطويلة ({scope}): {key}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def memory_recall(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if ctx.db is None:
        return {"ok": False, "error": "DB missing"}
    key = (args.get("key") or "").strip().lower()
    scope = (args.get("scope") or "any").strip().lower()
    if not key:
        return {"ok": False, "error": "key required"}
    try:
        # Look in project first, then merchant
        merchant_id = _project_merchant_id(ctx)
        queries = []
        if scope in ("any", "project") and ctx.project_id:
            queries.append({"project_id": ctx.project_id, "scope": "project", "key": key})
        if scope in ("any", "merchant") and merchant_id:
            queries.append({"merchant_id": merchant_id, "scope": "merchant", "key": key})
        for q in queries:
            doc = await ctx.db.freebuild_memories.find_one(q, {"_id": 0})
            if doc:
                return {"ok": True, "key": key, "value": doc["value"], "scope": doc["scope"],
                        "updated_at": doc.get("updated_at")}
        return {"ok": True, "key": key, "value": None, "found": False,
                "message": f"ما فيه ذاكرة بإسم '{key}'."}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def memory_list(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if ctx.db is None:
        return {"ok": False, "error": "DB missing"}
    scope = (args.get("scope") or "any").strip().lower()
    merchant_id = _project_merchant_id(ctx)
    try:
        conditions = []
        if scope in ("any", "project") and ctx.project_id:
            conditions.append({"project_id": ctx.project_id, "scope": "project"})
        if scope in ("any", "merchant") and merchant_id:
            conditions.append({"merchant_id": merchant_id, "scope": "merchant"})
        if not conditions:
            return {"ok": True, "memories": [], "count": 0}
        cursor = ctx.db.freebuild_memories.find({"$or": conditions}, {"_id": 0}).sort("updated_at", -1)
        docs = await cursor.to_list(length=500)
        return {"ok": True, "memories": docs, "count": len(docs)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def memory_delete(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    if ctx.db is None:
        return {"ok": False, "error": "DB missing"}
    key = (args.get("key") or "").strip().lower()
    scope = (args.get("scope") or "project").strip().lower()
    if not key or scope not in ("project", "merchant"):
        return {"ok": False, "error": "key + scope (project|merchant) required"}
    owner = {"project_id": ctx.project_id} if scope == "project" else {"merchant_id": _project_merchant_id(ctx)}
    if not owner.get(list(owner.keys())[0]):
        return {"ok": False, "error": "no project_id / merchant_id available"}
    try:
        r = await ctx.db.freebuild_memories.delete_one({**owner, "scope": scope, "key": key})
        return {"ok": True, "deleted_count": r.deleted_count,
                "message": f"حُذف: {r.deleted_count} ذاكرة." if r.deleted_count else "ما فيه ذاكرة بهذا الاسم."}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def load_project_memories_for_prompt(db, project_id: Optional[str], merchant_id: Optional[str]) -> str:
    """Helper used by freebuild_agent to inject saved memories into the system prompt."""
    if db is None:
        return ""
    try:
        conditions = []
        if project_id:
            conditions.append({"project_id": project_id, "scope": "project"})
        if merchant_id:
            conditions.append({"merchant_id": merchant_id, "scope": "merchant"})
        if not conditions:
            return ""
        cursor = db.freebuild_memories.find({"$or": conditions}, {"_id": 0, "key": 1, "value": 1, "scope": 1})
        docs = await cursor.to_list(length=100)
        if not docs:
            return ""
        lines = ["", "═══════════════════════════════════════════════════════════",
                 "🧠 **الذاكرة الطويلة لهذا المشروع (ذكّر نفسك بها):**", ""]
        for d in docs:
            scope_emoji = "📌" if d.get("scope") == "project" else "🏪"
            lines.append(f"  {scope_emoji} `{d['key']}`: {d['value']}")
        lines.append("")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"load_project_memories failed: {e}")
        return ""


# ─── audit_project ───────────────────────────────────────────────────────────
async def audit_project(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    """Comprehensive multi-angle audit. Runs ~5-7 sub-checks and aggregates."""
    include_visual = bool(args.get("include_visual_test", True))
    include_specialists = bool(args.get("include_specialists", True))
    live_url = (args.get("live_url") or "").strip() or None
    html = (ctx.current_html or "").strip()
    if not html and not live_url:
        return {"ok": False, "error": "no HTML or live_url to audit"}

    report: Dict[str, Any] = {
        "ok": True,
        "kind": "audit_report",
        "audit_id": str(uuid.uuid4())[:12],
        "started_at": time.time(),
        "checks": {},
        "scores": {},
        "summary": "",
    }

    # Import sibling tools lazily to avoid circular import
    from .freebuild_agent import _exec_tool_async
    from .workflow_tools import delegate

    # 1. HTML validation (sync local check)
    try:
        r = await _exec_tool_async(ctx, "validate_html", {})
        report["checks"]["html"] = {"ok": bool(r.get("ok")), "issues": r.get("issues", []),
                                     "issue_count": len(r.get("issues", []))}
        report["scores"]["html"] = 100 if r.get("ok") and not r.get("issues") else max(0, 100 - 10 * len(r.get("issues", [])))
    except Exception as e:
        report["checks"]["html"] = {"ok": False, "error": str(e)[:200]}
        report["scores"]["html"] = 0

    # 2. JavaScript lint
    try:
        r = await _exec_tool_async(ctx, "lint_javascript", {})
        report["checks"]["js"] = {"ok": bool(r.get("ok")), "errors": r.get("errors", []),
                                   "warnings": r.get("warnings", []),
                                   "error_count": len(r.get("errors", []))}
        n_errs = len(r.get("errors", []))
        report["scores"]["js"] = max(0, 100 - 15 * n_errs)
    except Exception as e:
        report["checks"]["js"] = {"ok": False, "error": str(e)[:200]}
        report["scores"]["js"] = 0

    # 3. Live page render test (Playwright)
    if include_visual:
        try:
            target_url = live_url
            if not target_url and ctx.project_id:
                # Try to find a published URL from the project
                target_url = (ctx.project or {}).get("published_url") or (ctx.project or {}).get("preview_url")
            if target_url:
                r = await _exec_tool_async(ctx, "test_page", {"url": target_url})
                report["checks"]["visual"] = {
                    "ok": bool(r.get("ok")),
                    "url": target_url,
                    "console_errors": r.get("console_errors", []),
                    "screenshot_b64": (r.get("screenshot_base64") or "")[:200],
                    "page_metrics": r.get("metrics", {}),
                }
                n_console_errs = len(r.get("console_errors", []))
                report["scores"]["visual"] = max(0, 100 - 20 * n_console_errs)
            else:
                report["checks"]["visual"] = {"ok": False, "skipped": True,
                                               "reason": "no live URL available — publish first via publish_site"}
                report["scores"]["visual"] = None
        except Exception as e:
            report["checks"]["visual"] = {"ok": False, "error": str(e)[:200]}
            report["scores"]["visual"] = 0

    # 4-7. Specialist reviews (in PARALLEL for speed)
    if include_specialists and html:
        html_excerpt = html[:6000]

        async def run_specialist(role: str, task: str) -> Dict[str, Any]:
            try:
                return await delegate(ctx, {"role": role, "task": task, "context": html_excerpt})
            except Exception as e:
                return {"ok": False, "error": str(e)[:200]}

        specialist_tasks = {
            "security": run_specialist(
                "security_auditor",
                "راجع HTML هذا للبحث عن: XSS، تسريب مفاتيح، JS غير آمن، روابط مشبوهة. ارجع قائمة المشاكل (لو فيه) أو 'سليم' لو ما فيه شي.",
            ),
            "performance": run_specialist(
                "performance_optimizer",
                "حلّل HTML هذا لرصد بطء الأداء: صور غير محسّنة، JS ضخم، CSS مكرّر، missing lazy loading. ارجع أهم 3 مشاكل + الإصلاح.",
            ),
            "seo": run_specialist(
                "seo_strategist",
                "راجع HTML للـ SEO: meta tags، عناوين H1-H6، schema.org، lang/dir، alt للصور. ارجع تقييماً واقتراحات.",
            ),
            "accessibility": run_specialist(
                "accessibility_auditor",
                "راجع HTML من ناحية WCAG 2.1 AA (مع تركيز RTL): تباين الألوان، aria-labels، التنقل بلوحة المفاتيح، dir صحيح. ارجع المشاكل مرتبة.",
            ),
        }
        try:
            results = await asyncio.gather(*specialist_tasks.values(), return_exceptions=True)
            for (name, _), result in zip(specialist_tasks.items(), results):
                if isinstance(result, Exception):
                    report["checks"][name] = {"ok": False, "error": str(result)[:200]}
                    report["scores"][name] = 0
                elif result.get("ok"):
                    answer = result.get("answer", "")
                    # Heuristic score: shorter "no issues" answer → higher score
                    lower = answer.lower()
                    if "سليم" in answer or "no issues" in lower or len(answer) < 200:
                        score = 95
                    elif len(answer) < 500:
                        score = 80
                    elif len(answer) < 1500:
                        score = 65
                    else:
                        score = 50
                    report["checks"][name] = {"ok": True, "review": answer[:3000],
                                               "model": result.get("model_used")}
                    report["scores"][name] = score
                else:
                    report["checks"][name] = {"ok": False, "error": result.get("error", "?")[:200]}
                    report["scores"][name] = 0
        except Exception:
            logger.exception("specialist audit gather failed")

    # Final aggregate score
    valid_scores = [s for s in report["scores"].values() if isinstance(s, (int, float))]
    overall = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0
    report["overall_score"] = overall
    if overall >= 90:
        grade = "🟢 ممتاز"
    elif overall >= 75:
        grade = "🟡 جيد جداً"
    elif overall >= 60:
        grade = "🟠 جيد — يحتاج تحسينات"
    elif overall >= 40:
        grade = "🔴 ضعيف — يحتاج مراجعة كاملة"
    else:
        grade = "⚫ خطر — أعد البناء"
    report["grade"] = grade
    report["elapsed_seconds"] = round(time.time() - report["started_at"], 2)
    n_checks = len(report["scores"])
    report["summary"] = (
        f"التقييم الإجمالي: {overall}/100 ({grade}). "
        f"تم فحص {n_checks} جانب في {report['elapsed_seconds']} ثانية."
    )
    report["message"] = report["summary"]

    # Persist for future reference
    try:
        if ctx.db is not None and ctx.project_id:
            await ctx.db.freebuild_audits.insert_one({
                "audit_id": report["audit_id"],
                "project_id": ctx.project_id,
                "overall_score": overall,
                "grade": grade,
                "scores": report["scores"],
                "created_at": time.time(),
            })
    except Exception as e:
        logger.warning(f"audit persist failed: {e}")

    return report


# ─── Master dispatcher ────────────────────────────────────────────────────────
async def dispatch_phase4(ctx, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    fn_map = {
        "update_plan_step": update_plan_step,
        "memory_save": memory_save,
        "memory_recall": memory_recall,
        "memory_list": memory_list,
        "memory_delete": memory_delete,
        "audit_project": audit_project,
    }
    fn = fn_map.get(name)
    if not fn:
        return {"ok": False, "error": f"unknown phase4 tool: {name}"}
    try:
        return await fn(ctx, args)
    except Exception as e:
        logger.exception(f"phase4 tool {name} failed")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
