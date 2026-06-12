"""
Zenrex AI Brain — Smart Workflow Tools (Phase 3).

Three high-leverage tools that close the gap between Zenrex AI and a senior
human engineer:

1. ask_user_inline   — pause the agent mid-turn and pop a choice Modal in the UI.
2. plan_task          — explicit, user-visible roadmap so the human sees what's
                        about to happen before it happens.
3. delegate           — spawn a focused specialist (designer / copywriter /
                        security_auditor / performance_optimizer / data_analyst)
                        for a narrow, expert task.

All tools are async, return JSON-serialisable dicts, never raise.
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("zenrex.workflow_tools")


WORKFLOW_TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "ask_user_inline",
        "description": (
            "🔌 PAUSE the conversation mid-turn and pop a Modal in the UI with a "
            "specific question + multiple-choice options. Use this WHENEVER you need "
            "a decision before continuing (e.g. 'هل تبيني أنشر على Vercel ولا Netlify؟', "
            "'أي قالب تفضل؟ a/b/c'). DO NOT continue calling other tools after this — "
            "the agent loop will end naturally; the user's choice arrives as the next "
            "chat message and you continue from there. Far better than burying a "
            "question in prose — the UI gives clickable buttons."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Arabic question shown to the user (one sentence ideally)."},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Up to 6 short choice labels (e.g. 'Vercel', 'Netlify', 'Cloudflare Pages').",
                    "minItems": 2,
                    "maxItems": 6,
                },
                "allow_free_text": {"type": "boolean", "default": True,
                                    "description": "If true, the Modal also shows a 'Other...' text input."},
                "context": {"type": "string",
                            "description": "Optional one-line explanation of why you're asking."},
            },
            "required": ["question", "options"],
        },
    },
    {
        "name": "plan_task",
        "description": (
            "📋 Announce a structured roadmap BEFORE starting a complex (3+ step) task. "
            "Renders as a beautiful checklist card in the chat so the user sees exactly "
            "what you're about to do and can approve or redirect. Use for multi-step "
            "tasks like 'build a full landing page', 'integrate Stripe', 'migrate to a "
            "new design'. For trivial 1-2-step tasks, skip this."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short Arabic title of the overall goal."},
                "steps": {
                    "type": "array",
                    "items": {"type": "string", "description": "One concrete step (Arabic ok). Verb-first preferred."},
                    "minItems": 2,
                    "maxItems": 12,
                },
                "estimated_minutes": {"type": "integer", "default": 5, "minimum": 1, "maximum": 60},
            },
            "required": ["title", "steps"],
        },
    },
    {
        "name": "delegate",
        "description": (
            "🧠 Delegate a focused task to a specialist sub-agent (a Claude call with "
            "a role-tuned system prompt). Use for narrow expert work where you want a "
            "second perspective. Returns the specialist's analysis/output that you "
            "then incorporate into the main flow.\n\n"
            "Available roles:\n"
            "  • 'designer'              — visual design critique + CSS suggestions for one section\n"
            "  • 'copywriter'            — Arabic marketing copy / headlines / CTAs\n"
            "  • 'security_auditor'      — review code/HTML for vulnerabilities (XSS, injection, leaked keys)\n"
            "  • 'performance_optimizer' — find slow CSS/JS, image bloat, render-blocking issues\n"
            "  • 'data_analyst'          — analyse merchant data (sales trends, top SKUs, customer cohorts)\n"
            "  • 'seo_strategist'        — Arabic SEO recommendations, meta tags, schema.org\n"
            "  • 'accessibility_auditor' — WCAG 2.1 AA issues, RTL/Arabic-specific concerns"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["designer", "copywriter", "security_auditor",
                             "performance_optimizer", "data_analyst",
                             "seo_strategist", "accessibility_auditor"],
                },
                "task": {"type": "string", "description": "Specific task / question for the specialist (Arabic ok)."},
                "context": {"type": "string",
                            "description": "Optional HTML snippet / data / context the specialist needs (max 8000 chars)."},
            },
            "required": ["role", "task"],
        },
    },
]


WORKFLOW_TOOL_LABELS_AR: Dict[str, Dict[str, str]] = {
    "ask_user_inline": {"running": "⏸️ ينتظر اختيارك...",         "done": "✅ تم استلام الاختيار"},
    "plan_task":       {"running": "📋 يرسم خطة العمل...",         "done": "✅ الخطة جاهزة"},
    "delegate":        {"running": "🧠 يستشير المتخصص...",        "done": "✅ رأي المتخصص جاهز"},
}


WORKFLOW_TOOL_NAMES: tuple = tuple(t["name"] for t in WORKFLOW_TOOL_SCHEMAS)


# ─── Role-tuned system prompts for `delegate` ─────────────────────────────────
_ROLE_PROMPTS = {
    "designer": (
        "أنت مصمم بصري سعودي محترف بخبرة 15 سنة في تصميم المواقع العربية. "
        "تحلل التصميمات بدقة وتقترح تحسينات على CSS فقط — لا تكتب JS ولا تغيّر "
        "البنية. تركّز على: التباين اللوني، الـ spacing، الـ typography العربية، "
        "RTL، الـ hierarchy البصرية. أجب بالعربية. قدّم: 1) نقد محدد لما تشاهده، "
        "2) 3-5 تحسينات ملموسة مع CSS snippets، 3) ترتيب الأولوية."
    ),
    "copywriter": (
        "أنت كاتب إعلانات سعودي محترف. تكتب نصوص تسويقية باللهجة السعودية الراقية "
        "أو الفصحى المُبسّطة. تركّز على: hooks في 7 كلمات أو أقل، CTAs واضحة، "
        "تجنّب الكلام الإنشائي. ارجع: 1) عنوان رئيسي، 2) 3 عناوين فرعية، "
        "3) فقرة وصفية قصيرة، 4) نص CTA الزر، 5) شرح موجز للاختيارات."
    ),
    "security_auditor": (
        "أنت مدقّق أمن تطبيقات ويب. تقرأ الكود وترصد ثغرات XSS، SQL injection، "
        "CSRF، تسريب مفاتيح في الكود، اعتمادات ضعيفة، CORS فضفاض. أجب بقائمة "
        "مرتبة بالخطورة: 🔴 حرجة → 🟠 عالية → 🟡 متوسطة → 🟢 منخفضة. لكل ثغرة: "
        "المكان، الوصف، التأثير، طريقة الإصلاح بالكود."
    ),
    "performance_optimizer": (
        "أنت مهندس أداء ويب. تحلل HTML/CSS/JS وترصد: صور غير مضغوطة، JS غير "
        "ضروري في الـ critical path، render-blocking CSS، layout shifts، missing "
        "lazy loading. ارجع 5 توصيات قابلة للتنفيذ مع تقدير الفائدة (ms) وكود الإصلاح."
    ),
    "data_analyst": (
        "أنت محلل بيانات تجزئة. تأخذ بيانات الطلبات/المنتجات/العملاء وترصد: "
        "أكثر المنتجات مبيعاً، أوقات الذروة، عملاء كبار، منتجات راكدة، فرص "
        "تكرار. أجب بالعربية بأرقام دقيقة (لا تخمن) + توصية عملية واحدة لكل نمط."
    ),
    "seo_strategist": (
        "أنت خبير SEO عربي. تحلل الصفحة وترصد: ضعف الـ meta tags، عناوين H1-H6 "
        "غير مرتبة، schema.org ناقصة، روابط داخلية ضعيفة، صور بدون alt عربي، "
        "كلمات مفتاحية مهمة مفقودة. ارجع تحسينات محددة وكود جاهز للنسخ."
    ),
    "accessibility_auditor": (
        "أنت مدقّق وصولية WCAG 2.1 AA مع تخصص في RTL/العربية. ترصد: تباين لوني "
        "غير كافٍ، أزرار بدون aria-label، خرائط تنقل لوحة المفاتيح مكسورة، "
        "تباين نصوص RTL غير كافٍ، dir غير صحيح، اعتمادات على اللون فقط. ارجع "
        "قائمة مرتبة بالأولوية مع التصحيحات."
    ),
}


# ─── Tool implementations ─────────────────────────────────────────────────────
async def ask_user_inline(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    """Emit a sentinel that the frontend Modal layer will detect."""
    question = (args.get("question") or "").strip()
    options = args.get("options") or []
    if not question:
        return {"ok": False, "error": "question is required"}
    if not isinstance(options, list) or not (2 <= len(options) <= 6):
        return {"ok": False, "error": "options must be a list of 2-6 strings"}
    options = [str(o).strip()[:80] for o in options if str(o).strip()]
    allow_free = bool(args.get("allow_free_text", True))
    ctxt = (args.get("context") or "").strip()
    return {
        "ok": True,
        "pending_user_input": True,
        "kind": "choice",
        "question": question,
        "options": options,
        "allow_free_text": allow_free,
        "context": ctxt,
        "message": "⏸️ STOP — waiting for user choice via Modal. Do not call any more tools this turn.",
    }


async def plan_task(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    """Record + announce a roadmap. UI renders it as a checklist card."""
    title = (args.get("title") or "").strip()
    steps = args.get("steps") or []
    if not title or not isinstance(steps, list) or len(steps) < 2:
        return {"ok": False, "error": "title and at least 2 steps required"}
    steps = [str(s).strip()[:160] for s in steps if str(s).strip()][:12]
    eta = max(1, min(int(args.get("estimated_minutes") or 5), 60))
    plan_id = str(uuid.uuid4())[:12]

    # Persist on the project so the UI can re-render it later
    if ctx.db is not None and ctx.project_id:
        try:
            await ctx.db.freebuild_plans.insert_one({
                "id": plan_id,
                "project_id": ctx.project_id,
                "title": title,
                "steps": [{"text": s, "status": "pending"} for s in steps],
                "estimated_minutes": eta,
                "created_at": time.time(),
            })
        except Exception as e:
            logger.warning(f"plan_task persist failed: {e}")

    return {
        "ok": True,
        "kind": "plan",
        "plan_id": plan_id,
        "title": title,
        "steps": steps,
        "estimated_minutes": eta,
        "message": f"📋 خطة من {len(steps)} خطوات معتمدة. أبدأ التنفيذ الآن.",
    }


async def delegate(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    """Spawn a focused specialist Claude call with a role-tuned system prompt."""
    role = (args.get("role") or "").strip().lower()
    task = (args.get("task") or "").strip()
    sys_prompt = _ROLE_PROMPTS.get(role)
    if not sys_prompt:
        return {"ok": False, "error": f"unknown role '{role}'. Available: {list(_ROLE_PROMPTS.keys())}"}
    if not task or len(task) < 8:
        return {"ok": False, "error": "task too short — describe specifically what you want."}
    context_blob = (args.get("context") or "")[:8000]

    user_msg = task if not context_blob else f"{task}\n\n=== CONTEXT ===\n{context_blob}"

    # Use Anthropic directly (Claude Haiku 4.5 for speed/cost on specialist work,
    # falls back to Sonnet if available). We do NOT route via the universal key
    # here because specialist calls are short and should be fast.
    api_key = (
        os.environ.get("ANTHROPIC_API_KEY", "").strip()
        or os.environ.get("EMERGENT_LLM_KEY", "").strip()
    )
    if not api_key:
        return {"ok": False, "error": "No Anthropic key available (ANTHROPIC_API_KEY or EMERGENT_LLM_KEY)."}

    # Try Sonnet first (better quality), fall back to Haiku
    models_to_try = [
        "claude-haiku-4-5-20251001",
        "claude-3-5-haiku-20241022",
    ]
    last_err: Optional[str] = None
    started = time.time()
    for model in models_to_try:
        try:
            async with httpx.AsyncClient(timeout=45) as cl:
                r = await cl.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 2000,
                        "system": sys_prompt,
                        "messages": [{"role": "user", "content": user_msg}],
                    },
                )
                if r.status_code == 200:
                    d = r.json()
                    blocks = d.get("content") or []
                    answer = "\n".join((b.get("text") or "") for b in blocks if b.get("type") == "text").strip()
                    elapsed = round(time.time() - started, 2)
                    return {
                        "ok": True,
                        "role": role,
                        "model_used": model,
                        "elapsed_seconds": elapsed,
                        "answer": answer[:8000],
                        "tokens": (d.get("usage") or {}),
                        "message": f"✅ المتخصص '{role}' رد ({elapsed}s, {len(answer)} حرف).",
                    }
                if r.status_code == 404:
                    last_err = f"model '{model}' not found"
                    continue
                last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                # 401/403 won't be fixed by trying another model
                if r.status_code in (401, 403):
                    break
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:200]}"
            continue
    return {"ok": False, "error": f"delegate failed: {last_err}"}


# ─── Master dispatcher ────────────────────────────────────────────────────────
async def dispatch_workflow(ctx, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    fn_map = {
        "ask_user_inline": ask_user_inline,
        "plan_task": plan_task,
        "delegate": delegate,
    }
    fn = fn_map.get(name)
    if not fn:
        return {"ok": False, "error": f"unknown workflow tool: {name}"}
    try:
        return await fn(ctx, args)
    except Exception as e:
        logger.exception(f"workflow tool {name} failed")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
