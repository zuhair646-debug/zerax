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
            "'أي نوع فيديو؟ كرتون/أنمي/سينمائي/رعب'). DO NOT continue calling other "
            "tools after this — the agent loop will end naturally; the user's choice "
            "arrives as the next chat message and you continue from there.\n\n"
            "**Rich options (recommended for visual choices like film type, design "
            "style, theme):** Pass options as objects with `label`, `emoji`, and "
            "optional `image_url` (use https URLs from your generated assets, or "
            "fetched images, or trusted public CDNs). The UI renders these as "
            "beautiful clickable cards with images.\n\n"
            "Plain strings are also fine for simple yes/no/text choices."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Arabic question shown to the user (one sentence ideally)."},
                "options": {
                    "type": "array",
                    "description": (
                        "2-6 choices. Each item is either a plain string (e.g. "
                        "'Vercel') OR an object {label, emoji?, image_url?, "
                        "description?} for rich visual cards."
                    ),
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "object",
                                "properties": {
                                    "label": {"type": "string", "description": "Short Arabic label shown on the card (max 40 chars)."},
                                    "emoji": {"type": "string", "description": "Single emoji that visually represents this choice."},
                                    "image_url": {"type": "string", "description": "Optional https URL to an example image (~16:9 ratio looks best)."},
                                    "description": {"type": "string", "description": "Optional 1-line Arabic explainer (max 80 chars)."},
                                },
                                "required": ["label"],
                            },
                        ]
                    },
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
    {
        "name": "set_current_phase",
        "description": (
            "🎬 Advance the Studio Phase Tracker to the next phase. Call this "
            "**immediately after** the user has approved/answered everything you "
            "need for the current phase.\n\n"
            "The frontend's 7-phase Tracker visually marks the previous phase as "
            "✅ green-done and animates the new one as 🟡 current. The progress "
            "counter increments (e.g. 0/7 → 1/7 → 2/7).\n\n"
            "Also pass `summary_of_decisions` — a 1-2 line recap of what the user "
            "decided in the phase you just finished. This is shown to the user as "
            "confirmation ('فهمت: اخترت أنمي Ghibli، شخصيات: عيون كبيرة...') and "
            "is persisted to the `decisions` doc so all later phases stay loyal "
            "to the user's actual choices (anti-hallucination guard).\n\n"
            "**Valid phases (Video Studio):** film_type → characters → script → "
            "voice → storyboard → preview → render.\n"
            "**Valid phases (Website):** discovery → design → build → review → publish."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "new_phase": {
                    "type": "string",
                    "description": "ID of the phase to MOVE TO (the one that becomes 'current'). The previous one auto-marks as done.",
                },
                "summary_of_decisions": {
                    "type": "string",
                    "description": "1-2 lines summarizing what the user just decided in the phase you're closing. Will be shown to the user.",
                },
            },
            "required": ["new_phase", "summary_of_decisions"],
        },
    },
    {
        "name": "generate_video",
        "description": (
            "🎬 Generate a real animated video clip via fal.ai using the "
            "**server-configured** FAL_KEY. Never ask the user for a key — it is "
            "preloaded on the server. Use this in Phase 7 (Render) after Storyboard "
            "is approved.\n\n"
            "💰 **COST DISCIPLINE — STRICT**\n"
            "  • Default model is `hailuo` (Hailuo Standard $0.04/s). Use this for 90% of clips.\n"
            "  • `kling` (Kling Standard $0.07/s) — only for hero/key shots (1-2 per project).\n"
            "  • `kling-pro` ($0.15/s) and `sora-2-turbo` ($0.10/s) are **PREMIUM tiers** and "
            "    require the user to have explicitly approved them via `ask_user_inline` in "
            "    the SAME conversation. You MUST pass `confirmed_premium=true` for these.\n"
            "  • If you call a premium model without `confirmed_premium=true`, the tool will "
            "    REFUSE and tell you to ask the user first.\n\n"
            "Models (price per second):\n"
            "  • `ltx-video`            → $0.005/s — cheap drafts only\n"
            "  • `hailuo` ⭐ DEFAULT    → $0.04/s — good quality, fast, recommended\n"
            "  • `kling`                → $0.07/s — cinematic key shots\n"
            "  • `kling-pro` ⚠️ PREMIUM → $0.15/s — needs confirmed_premium=true\n"
            "  • `sora-2-turbo` ⚠️ PREMIUM → $0.10/s — needs confirmed_premium=true\n\n"
            "Returns `{ok, video_url, duration_sec, cost_usd, model_used}` on "
            "success. On failure, automatically posts a notification to the owner."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Detailed scene description in English (fal.ai understands English best)."},
                "model": {"type": "string", "description": "One of: ltx-video, hailuo (DEFAULT), kling, kling-pro (premium), sora-2-turbo (premium). Defaults to hailuo."},
                "duration_seconds": {"type": "integer", "minimum": 3, "maximum": 10,
                                     "description": "Clip duration in seconds (3-10). Default 6."},
                "image_url": {"type": "string", "description": "Optional reference image URL (img2video)."},
                "scene_id": {"type": "string", "description": "Optional scene identifier for tracking (e.g. 'scene_1', 'shot_03'). Helps with notifications."},
                "confirmed_premium": {"type": "boolean", "default": False, "description": "Must be true when calling kling-pro or sora-2-turbo. Pass only after explicit user approval via ask_user_inline."},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "notify_owner",
        "description": (
            "🚨 Send an in-app notification to the platform owner when something "
            "goes wrong that the user shouldn't see directly — e.g. an API key "
            "rejected, fal.ai out of credit, integration timeout. The notification "
            "appears in the owner's dashboard bell icon and includes the project "
            "context so they can investigate.\n\n"
            "**Do not** mention key names or technical details to the user — just "
            "say 'صار عطل تقني مؤقت'. THIS tool is how the team gets alerted "
            "instead of bothering the user.\n\n"
            "Categories: `integration_failure`, `quota_exceeded`, `key_invalid`, "
            "`api_timeout`, `user_complaint`, `other`."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string",
                             "enum": ["integration_failure", "quota_exceeded", "key_invalid",
                                      "api_timeout", "user_complaint", "other"]},
                "summary": {"type": "string", "description": "1-line title (e.g. 'fal.ai رفض المفتاح أثناء توليد المشهد 1')."},
                "details": {"type": "string", "description": "Full error context: which tool, which API, full error message, what user was trying to do. Max 2000 chars."},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
            },
            "required": ["category", "summary"],
        },
    },
]


WORKFLOW_TOOL_LABELS_AR: Dict[str, Dict[str, str]] = {
    "ask_user_inline":  {"running": "⏸️ ينتظر اختيارك...",         "done": "✅ تم استلام الاختيار"},
    "plan_task":        {"running": "📋 يرسم خطة العمل...",         "done": "✅ الخطة جاهزة"},
    "delegate":         {"running": "🧠 يستشير المتخصص...",        "done": "✅ رأي المتخصص جاهز"},
    "set_current_phase": {"running": "🎬 ينقلك للمرحلة الجاية...",  "done": "✅ المرحلة الجاية مفتوحة"},
    "notify_owner":     {"running": "✉️ يبلّغ الفريق بصمت...",     "done": "✅ تم التبليغ"},
    "generate_video":   {"running": "🎥 يولّد مشهد فيديو...",       "done": "✅ المشهد جاهز"},
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
    raw_options = args.get("options") or []
    if not question:
        return {"ok": False, "error": "question is required"}
    if not isinstance(raw_options, list) or not (2 <= len(raw_options) <= 6):
        return {"ok": False, "error": "options must be a list of 2-6 items"}

    # Normalize: accept plain strings OR rich objects {label, emoji?, image_url?, description?}
    options: List[Dict[str, Any]] = []
    for o in raw_options:
        if isinstance(o, str):
            lbl = o.strip()[:80]
            if lbl:
                options.append({"label": lbl})
        elif isinstance(o, dict):
            lbl = str(o.get("label") or "").strip()[:80]
            if not lbl:
                continue
            item: Dict[str, Any] = {"label": lbl}
            emoji = str(o.get("emoji") or "").strip()
            if emoji:
                item["emoji"] = emoji[:4]
            img = str(o.get("image_url") or "").strip()
            if img and img.startswith(("http://", "https://", "/")):
                item["image_url"] = img[:500]
            desc = str(o.get("description") or "").strip()
            if desc:
                item["description"] = desc[:120]
            options.append(item)
    if len(options) < 2:
        return {"ok": False, "error": "at least 2 valid options required"}

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


async def set_current_phase(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    """Advance the project's `current_phase` and record the closed-phase decisions.

    Visual side-effect: the frontend Phase Tracker reads `project.current_phase`
    + `project.phase_history` from the DB and renders the appropriate green/
    glowing pills. So we update both atomically.
    """
    new_phase = (args.get("new_phase") or "").strip()
    summary = (args.get("summary_of_decisions") or "").strip()
    if not new_phase or len(new_phase) > 60:
        return {"ok": False, "error": "new_phase is required (max 60 chars)"}
    if not summary or len(summary) < 8:
        return {"ok": False, "error": "summary_of_decisions is required (min 8 chars)"}

    if ctx.db is None or not ctx.project_id:
        return {"ok": False, "error": "no project in context"}

    # Read current state to capture history correctly
    try:
        proj = await ctx.db.freebuild_projects.find_one(
            {"id": ctx.project_id}, {"current_phase": 1, "phase_history": 1, "_id": 0}
        ) or {}
    except Exception as e:
        return {"ok": False, "error": f"read failed: {type(e).__name__}: {str(e)[:120]}"}

    old_phase = proj.get("current_phase") or ""
    history = list(proj.get("phase_history") or [])
    if old_phase and old_phase != new_phase and old_phase not in history:
        history.append(old_phase)

    # Append decision summary to the long-lived `decisions` engineering doc.
    # Later phases auto-read this doc → loyal to user's actual choices,
    # not whatever the AI hallucinates on the next turn.
    decision_line = f"[{old_phase or 'init'} → {new_phase}] {summary}"
    try:
        from .project_docs import update_project_doc  # local import to avoid cycle
        await update_project_doc(ctx.db, ctx.project_id, "decisions", decision_line, mode="append")
    except Exception as e:
        logger.warning(f"decisions doc append failed: {e}")

    try:
        await ctx.db.freebuild_projects.update_one(
            {"id": ctx.project_id},
            {"$set": {
                "current_phase": new_phase,
                "phase_history": history,
                "updated_at": time.time(),
            }},
        )
    except Exception as e:
        return {"ok": False, "error": f"update failed: {type(e).__name__}: {str(e)[:120]}"}

    return {
        "ok": True,
        "kind": "phase_advance",
        "from_phase": old_phase,
        "to_phase": new_phase,
        "history": history,
        "summary": summary,
        "message": (
            f"🎬 المرحلة '{old_phase}' خلصت ✅ — انتقلنا لـ '{new_phase}'. "
            "Phase Tracker اتحدّث في الواجهة."
        ),
    }


async def notify_owner(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    """Insert an admin notification into the `owner_notifications` collection.

    The owner's dashboard polls this collection (or subscribes via SSE) and
    shows a red dot on the bell icon. This is how the agent escalates problems
    silently instead of confessing technical details to end-users.
    """
    category = (args.get("category") or "other").strip()
    summary = (args.get("summary") or "").strip()[:200]
    details = (args.get("details") or "").strip()[:2000]
    severity = (args.get("severity") or "medium").strip().lower()
    if severity not in {"low", "medium", "high", "critical"}:
        severity = "medium"
    if not summary:
        return {"ok": False, "error": "summary required"}
    if ctx.db is None:
        return {"ok": False, "error": "no db"}
    doc = {
        "id": str(uuid.uuid4()),
        "created_at": time.time(),
        "category": category,
        "summary": summary,
        "details": details,
        "severity": severity,
        "project_id": ctx.project_id,
        "user_id": getattr(ctx, "user_id", None),
        "read": False,
    }
    try:
        await ctx.db.owner_notifications.insert_one(doc)
    except Exception as e:
        logger.warning(f"notify_owner insert failed: {e}")
        return {"ok": False, "error": str(e)[:120]}
    logger.warning(f"[OWNER NOTIFY] {severity.upper()} · {category} · {summary}")
    return {
        "ok": True,
        "notification_id": doc["id"],
        "message": "✉️ تم إرسال إشعار للمالك بصمت — استمر بأدب مع العميل بدون ذكر التفاصيل التقنية.",
    }


async def generate_video(ctx, args: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a real animated clip via fal.ai using the server-side FAL_KEY.

    Never asks the user for a key. If FAL_KEY is missing or rejected, this
    function:
      1) Logs the failure
      2) Auto-calls `notify_owner` so the team is alerted
      3) Returns a generic technical-error result the AI can show the user
         without exposing API/key details.
    """
    prompt = (args.get("prompt") or "").strip()
    if not prompt:
        return {"ok": False, "error": "prompt is required"}
    model_slug = (args.get("model") or "hailuo").strip().lower()
    duration = int(args.get("duration_seconds") or 6)
    duration = max(3, min(10, duration))
    image_url = (args.get("image_url") or "").strip() or None
    scene_id = (args.get("scene_id") or "").strip() or None
    confirmed_premium = bool(args.get("confirmed_premium", False))

    # 💰 Cost-Discipline Guardrail (Feb 2026):
    # Premium tiers cost 3-5x more than Hailuo Standard. They MUST NOT fire
    # without an explicit user approval flag set by the agent in the SAME turn.
    PREMIUM_MODELS = {"kling-pro", "sora-2-turbo", "sora-2-pro"}
    if model_slug in PREMIUM_MODELS and not confirmed_premium:
        return {
            "ok": False,
            "error_for_user": None,  # don't surface to user — agent should ask first
            "internal_error": (
                f"PREMIUM_GUARDRAIL: model '{model_slug}' requires confirmed_premium=true. "
                f"You must first call ask_user_inline to get explicit user approval for the "
                f"premium tier (it costs 3-5x more than Hailuo Standard). Then retry with "
                f"confirmed_premium=true. If the user did not approve, fall back to model='hailuo'."
            ),
            "suggested_fallback": "hailuo",
        }

    fal_key = os.environ.get("FAL_KEY", "").strip()
    if not fal_key:
        # No key configured at all — escalate to owner, give user a generic
        # apology that does NOT mention any technical detail.
        await notify_owner(ctx, {
            "category": "key_invalid", "severity": "critical",
            "summary": "FAL_KEY غير مكوَّن على الخادم",
            "details": (f"agent tried generate_video(model={model_slug}, dur={duration}s) "
                        f"but env FAL_KEY is empty. scene={scene_id} project={ctx.project_id}"),
        })
        return {
            "ok": False,
            "error_for_user": "صار عندي عطل تقني مؤقت في خدمة توليد الفيديو. أبلغت الفريق فوراً.",
            "internal_error": "FAL_KEY missing in env",
        }

    # Map our friendly slug → actual fal.ai endpoint + per-second pricing
    model_map = {
        "ltx-video":   ("fal-ai/ltx-video",                 0.005),
        "hailuo":      ("fal-ai/minimax/hailuo-02/standard/text-to-video", 0.04),
        "kling":       ("fal-ai/kling-video/v1/standard/text-to-video",    0.07),
        "kling-pro":   ("fal-ai/kling-video/v1/pro/text-to-video",         0.15),
        "sora-2-turbo": ("fal-ai/sora-2/text-to-video",      0.10),
    }
    endpoint, price_per_sec = model_map.get(model_slug, model_map["hailuo"])
    estimated_cost = round(price_per_sec * duration, 4)

    # Submit job
    payload = {"prompt": prompt[:1500], "duration": duration}
    if image_url:
        payload["image_url"] = image_url
    headers = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}

    try:
        # fal.ai video models (Hailuo/Kling/Sora) often take 2-4 minutes server-side.
        # Use a generous 300s timeout to accommodate peak-load latency. If even
        # this isn't enough, the AI surfaces the timeout to the user gracefully.
        async with httpx.AsyncClient(timeout=300) as cl:
            r = await cl.post(f"https://fal.run/{endpoint}", json=payload, headers=headers)
        if r.status_code == 401 or r.status_code == 403:
            await notify_owner(ctx, {
                "category": "key_invalid", "severity": "critical",
                "summary": f"fal.ai رفض المفتاح (HTTP {r.status_code})",
                "details": (f"endpoint={endpoint} response={r.text[:500]} "
                            f"scene={scene_id} project={ctx.project_id}"),
            })
            return {"ok": False,
                    "error_for_user": "صار عطل تقني مؤقت في توليد الفيديو. أبلغت الفريق."}
        if r.status_code == 402 or r.status_code == 429:
            await notify_owner(ctx, {
                "category": "quota_exceeded", "severity": "high",
                "summary": f"fal.ai رصيد منتهي أو rate-limit (HTTP {r.status_code})",
                "details": f"endpoint={endpoint} body={r.text[:500]} cost_attempted=${estimated_cost}",
            })
            return {"ok": False,
                    "error_for_user": "خدمة توليد الفيديو مزدحمة مؤقتاً. أبلغت الفريق."}
        if r.status_code >= 400:
            await notify_owner(ctx, {
                "category": "integration_failure", "severity": "medium",
                "summary": f"fal.ai رد بـ HTTP {r.status_code}",
                "details": f"endpoint={endpoint} body={r.text[:500]} prompt={prompt[:200]}",
            })
            return {"ok": False,
                    "error_for_user": "صار عطل تقني في توليد المشهد. أبلغت الفريق."}
        data = r.json()
        video_url = (data.get("video") or {}).get("url") or data.get("url") or ""
        if not video_url:
            await notify_owner(ctx, {
                "category": "integration_failure", "severity": "medium",
                "summary": "fal.ai رد بنجاح لكن بدون video_url",
                "details": f"endpoint={endpoint} keys={list(data.keys())[:10]}",
            })
            return {"ok": False,
                    "error_for_user": "صار عطل تقني في توليد المشهد. أبلغت الفريق."}
        return {
            "ok": True,
            "video_url": video_url,
            "duration_sec": duration,
            "model_used": model_slug,
            "cost_usd": estimated_cost,
            "scene_id": scene_id,
        }
    except httpx.TimeoutException:
        await notify_owner(ctx, {
            "category": "api_timeout", "severity": "medium",
            "summary": "fal.ai timeout (180s)",
            "details": f"endpoint={endpoint} prompt={prompt[:200]}",
        })
        return {"ok": False,
                "error_for_user": "خدمة توليد الفيديو بطيئة الآن. أبلغت الفريق وراح يتولّون."}
    except Exception as e:
        await notify_owner(ctx, {
            "category": "integration_failure", "severity": "medium",
            "summary": f"خطأ غير متوقع في generate_video: {type(e).__name__}",
            "details": f"endpoint={endpoint} error={str(e)[:500]}",
        })
        return {"ok": False,
                "error_for_user": "صار عطل تقني مؤقت. أبلغت الفريق."}


# ─── Master dispatcher ────────────────────────────────────────────────────────
async def dispatch_workflow(ctx, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    fn_map = {
        "ask_user_inline": ask_user_inline,
        "plan_task": plan_task,
        "delegate": delegate,
        "set_current_phase": set_current_phase,
        "notify_owner": notify_owner,
        "generate_video": generate_video,
    }
    fn = fn_map.get(name)
    if not fn:
        return {"ok": False, "error": f"unknown workflow tool: {name}"}
    try:
        return await fn(ctx, args)
    except Exception as e:
        logger.exception(f"workflow tool {name} failed")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
