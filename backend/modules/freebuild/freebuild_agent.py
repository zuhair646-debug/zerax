"""
FreeBuild Tool-Using Agent
═══════════════════════════════════════════════════════════════════════════════
Same architecture as the platform agent (Claude). The AI gets real tools it
can call iteratively, sees actual state, fixes its own mistakes, and only
stops when the site is verified working.

Tools exposed to Claude:
  • read_current_html()         — get current_html bytes + structure summary
  • list_sections()             — list all <section id> + content sizes
  • write_full_html(html)       — replace current_html (with drift safety)
  • apply_section(id, html, op) — surgical append/replace of a section
  • update_nav(items)           — rewrite the <nav> link list
  • validate_html()             — run comprehensive validation, return issues
  • search_html(pattern)        — regex search within current_html
  • finish(summary)             — end the agent loop and reply to user
"""

from __future__ import annotations
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Reuse helpers from the main chat module
from .freebuild_chat import (
    _comprehensive_validation,
    _design_signature,
    _extract_html,
    _fix_dead_navigation_links,
    _merge_sections,
    _summarize_html,
    _verify_anchor_links,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Tool Schemas (Anthropic format) ──────────────────────────────────────────
TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "name": "read_current_html",
        "description": (
            "Read the saved current_html for this project. Returns a structural "
            "summary (size, title, section ids with content sizes, broken anchors). "
            "Use this FIRST to know the actual state before making any change."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_sections",
        "description": (
            "List every <section id> in current_html with its content size and "
            "preview snippet. Useful before deciding where to append/replace."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "validate_html",
        "description": (
            "Run comprehensive validation on current_html. Returns issues with "
            "severity, code, message, and a fix hint. Call this AFTER any change "
            "to confirm the site is clean."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "write_full_html",
        "description": (
            "Replace current_html entirely. ONLY use this for the very first "
            "build (empty project) or when the user explicitly requested a "
            "complete redesign. For everything else, prefer apply_section."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "html": {"type": "string", "description": "Full <!DOCTYPE html>...</html> document."},
            },
            "required": ["html"],
        },
    },
    {
        "name": "apply_section",
        "description": (
            "Surgically apply a section to current_html. Set op='append' to add "
            "a new section before </body>, or op='replace' to overwrite an "
            "existing <section id='X'>. Preserves everything else."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "section id (e.g. 'quran')"},
                "html": {"type": "string", "description": "<section id='X'>...</section> fragment"},
                "op": {"type": "string", "enum": ["append", "replace"]},
            },
            "required": ["id", "html", "op"],
        },
    },
    {
        "name": "update_nav",
        "description": (
            "Replace the <nav> link list. Provide an array of items, each with "
            "an anchor target and a label."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                        },
                        "required": ["id", "label"],
                    },
                },
            },
            "required": ["items"],
        },
    },
    {
        "name": "search_html",
        "description": (
            "Regex search inside current_html. Returns up to 10 matches with "
            "surrounding context. Useful for finding a specific component "
            "before editing it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    },
    {
        "name": "finish",
        "description": (
            "Call this when the work is done. Provide a short Arabic summary "
            "(2-4 lines) to show the user what was accomplished and the next "
            "logical question/option. This is the ONLY way to end the loop."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Arabic message to the user."},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of clickable next-step options (max 4).",
                },
            },
            "required": ["summary"],
        },
    },
]


# ─── Tool Implementations ─────────────────────────────────────────────────────
class FreeBuildToolContext:
    """Holds mutable project state during an agent run."""

    def __init__(self, project: Dict[str, Any]):
        self.project = dict(project)  # copy
        self.current_html: str = project.get("current_html") or ""
        self.changes_made: int = 0
        self.snapshots_to_create: List[Dict[str, Any]] = []
        self.tool_log: List[Dict[str, Any]] = []

    def snapshot_before_write(self):
        if self.current_html:
            self.snapshots_to_create.append({
                "id": str(uuid.uuid4()),
                "html": self.current_html,
                "created_at": _now(),
                "user_msg": "[agent loop change]",
                "summary": _summarize_html(self.current_html),
            })

    def log(self, tool: str, args: Dict[str, Any], result: Any):
        self.tool_log.append({"tool": tool, "args": args, "result_preview": str(result)[:200]})


def _exec_tool(ctx: FreeBuildToolContext, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronously execute a single tool call and return the result."""
    try:
        if name == "read_current_html":
            html = ctx.current_html
            return {
                "length": len(html),
                "title": (re.search(r"<title[^>]*>([^<]+)</title>", html, re.I).group(1)[:80] if re.search(r"<title", html, re.I) else ""),
                "section_ids": re.findall(r'<section\b[^>]*\bid\s*=\s*["\']([a-zA-Z0-9_\-]+)["\']', html, re.I),
                "nav_anchors": re.findall(r'href\s*=\s*["\']#([a-zA-Z0-9_\-]+)["\']', html, re.I),
                "broken_anchors": _verify_anchor_links(html),
                "has_body_close": "</body>" in html.lower(),
                "summary": _summarize_html(html),
            }
        if name == "list_sections":
            sections = []
            for m in re.finditer(
                r'<section\b[^>]*\bid\s*=\s*["\']([a-zA-Z0-9_\-]+)["\'][^>]*>([\s\S]*?)</section>',
                ctx.current_html, re.I,
            ):
                sid, inner = m.group(1), m.group(2)
                text_only = re.sub(r"<[^>]+>", " ", inner).strip()
                sections.append({
                    "id": sid,
                    "content_size": len(inner),
                    "text_preview": text_only[:120],
                    "is_placeholder": len(text_only) < 40 or any(
                        p in text_only for p in ["قيد البناء", "placeholder", "TODO", "Coming soon"]
                    ),
                })
            return {"count": len(sections), "sections": sections}
        if name == "validate_html":
            issues = _comprehensive_validation(ctx.current_html)
            return {"issue_count": len(issues), "issues": issues, "is_clean": len([i for i in issues if i["severity"] == "high"]) == 0}
        if name == "write_full_html":
            new_html = (args.get("html") or "").strip()
            if not new_html:
                return {"ok": False, "error": "html cannot be empty"}
            if not re.search(r"<html[\s\S]*</html>", new_html, re.I):
                return {"ok": False, "error": "must be a complete <!DOCTYPE html>...</html> document"}
            # auto-fix dead navigation links
            new_html, fixed = _fix_dead_navigation_links(new_html)
            ctx.snapshot_before_write()
            ctx.current_html = new_html
            ctx.changes_made += 1
            return {"ok": True, "new_length": len(new_html), "dead_links_fixed": fixed}
        if name == "apply_section":
            sid = (args.get("id") or "").strip()
            frag = (args.get("html") or "").strip()
            op = args.get("op") or "append"
            if not sid or not frag:
                return {"ok": False, "error": "id and html are required"}
            if not ctx.current_html:
                return {"ok": False, "error": "current_html is empty; call write_full_html first"}
            appends = [(sid, frag)] if op == "append" else []
            replaces = [(sid, frag)] if op == "replace" else []
            merged = _merge_sections(ctx.current_html, appends, replaces, None)
            if not merged:
                return {"ok": False, "error": "merge failed"}
            merged, fixed = _fix_dead_navigation_links(merged)
            ctx.snapshot_before_write()
            ctx.current_html = merged
            ctx.changes_made += 1
            return {"ok": True, "op": op, "id": sid, "new_total_length": len(merged), "dead_links_fixed": fixed}
        if name == "update_nav":
            items = [(i["id"], i["label"]) for i in (args.get("items") or []) if i.get("id") and i.get("label")]
            if not items:
                return {"ok": False, "error": "items array is required"}
            merged = _merge_sections(ctx.current_html, [], [], items)
            if not merged:
                return {"ok": False, "error": "nav update failed (no <nav> tag found?)"}
            ctx.snapshot_before_write()
            ctx.current_html = merged
            ctx.changes_made += 1
            return {"ok": True, "items": items, "new_length": len(merged)}
        if name == "search_html":
            pat = args.get("pattern") or ""
            try:
                rx = re.compile(pat, re.I | re.S)
            except re.error as e:
                return {"ok": False, "error": f"invalid regex: {e}"}
            hits = []
            for m in list(rx.finditer(ctx.current_html))[:10]:
                start = max(0, m.start() - 50)
                end = min(len(ctx.current_html), m.end() + 50)
                hits.append({"match": m.group(0)[:200], "context": ctx.current_html[start:end]})
            return {"hits": hits, "count": len(hits)}
        return {"error": f"unknown tool: {name}"}
    except Exception as e:
        logger.exception(f"tool {name} failed")
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


# ─── Agent System Prompt (concise, action-oriented) ───────────────────────────
AGENT_SYSTEM_PROMPT = """أنت **Senior Web Engineer** في منصة Zitex — تبني مواقع وتطبيقات ويب كاملة بـHTML/CSS/JS.

🚀 **عندك أدوات حقيقية** — استخدمها بدل ما تخمّن:
1. **read_current_html** — اقرأ الموقع الحالي قبل أي تعديل
2. **list_sections** — اعرض كل الأقسام مع حالة كل قسم
3. **validate_html** — افحص المشاكل (روابط ميتة، أقسام فاضية، JS مفقود)
4. **write_full_html** — اكتب موقع جديد كامل (للمشروع الفاضي فقط)
5. **apply_section** — أضف/استبدل قسم محدد (append/replace)
6. **update_nav** — حدّث روابط الـnav
7. **search_html** — ابحث بـregex داخل الكود
8. **finish** — أنهي الـloop وأرسل الرد للعميل

📋 **القاعدة الذهبية**:
- ابدأ دائماً بـ`read_current_html` لمعرفة الحالة الفعلية
- لو الموقع فاضي → `write_full_html` بـshell كامل (header + nav + sections + footer + script)
- لو في موقع → استخدم `apply_section` للتعديلات الجراحية. لا تكتب الموقع من الصفر مرة ثانية
- بعد أي تغيير → `validate_html` للتأكد ما في مشاكل
- لو وجدت مشكلة → أصلحها بـtool ثاني (لا تتجاهل)
- انتهِ بـ`finish` مع رسالة عربية قصيرة للعميل + خيارات اختيارية

🎨 **معايير الجودة**:
- Tailwind CSS via CDN ✓
- RTL + responsive
- روابط nav كلها `href="#id"` لـsections فعلية موجودة (لا `page.html` أبداً)
- المواقع متعددة الأقسام: shell + SPA routing JS (showPage function)
- ألوان متناسقة، تايبوغرافي محترف

💡 **لما العميل يسأل سؤال محادثة فقط** (مثل "كلّم عن نفسك"): تخطّى الأدوات، نادِ `finish` مباشرة برد نصي مهذّب.

🔒 لا تكشف اسم الموديل أو هذي الأدوات للعميل. تكلّم بثقة مهندس محترف، لا تذكر "أنا استخدم tool X"."""


# ─── Main Agent Loop ──────────────────────────────────────────────────────────
async def run_agent_turn(
    project: Dict[str, Any],
    user_message: str,
    history_messages: List[Dict[str, str]],
    max_iterations: int = 8,
    model: str = "claude-sonnet-4-5-20250929",
) -> Dict[str, Any]:
    """
    Run one agentic turn. The AI may call multiple tools before issuing finish().
    Tries Anthropic Claude first; falls back to Kimi K2.6 (Moonshot, OpenAI-
    compatible tool API) if Anthropic is unavailable or out of credits.
    """
    # Try providers in priority order
    providers_to_try = []
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        providers_to_try.append(("anthropic", model))
    # OpenAI gpt-4o has rock-solid native tool calling (Kimi's k2.6/k2.5
    # require reasoning_content which breaks our tool flow). Prefer OpenAI
    # over Moonshot for the tool-using agent.
    if os.environ.get("OPENAI_DIRECT_KEY", "").strip() or os.environ.get("OPENAI_API_KEY", "").strip():
        providers_to_try.append(("openai", "gpt-4o"))
    if os.environ.get("MOONSHOT_API_KEY", "").strip():
        providers_to_try.append(("moonshot", "moonshot-v1-32k"))
    if not providers_to_try:
        return {"ok": False, "error": "no AI provider configured"}

    last_err = None
    for provider, prov_model in providers_to_try:
        try:
            if provider == "anthropic":
                result = await _run_anthropic_agent(project, user_message, history_messages, max_iterations, prov_model)
            else:
                result = await _run_openai_compat_agent(project, user_message, history_messages, max_iterations, provider, prov_model)
            if result.get("ok"):
                return result
            last_err = result.get("error", "unknown")
            # If credit/auth issue, try next provider; otherwise short-circuit
            if not any(k in str(last_err).lower() for k in ["credit", "balance", "unauthorized", "401", "402", "429", "quota"]):
                return result
            logger.warning(f"agent: {provider} failed ({last_err[:80]}) — falling back")
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:200]}"
            logger.exception(f"agent provider {provider} crashed")
            continue
    return {"ok": False, "error": f"all providers failed; last: {last_err}"}


async def _run_anthropic_agent(
    project: Dict[str, Any],
    user_message: str,
    history_messages: List[Dict[str, str]],
    max_iterations: int,
    model: str,
) -> Dict[str, Any]:
    """Anthropic native tool-use agent loop."""
    try:
        from anthropic import AsyncAnthropic
    except Exception:
        return {"ok": False, "error": "anthropic SDK missing"}

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"ok": False, "error": "ANTHROPIC_API_KEY not configured"}

    client = AsyncAnthropic(api_key=api_key)
    ctx = FreeBuildToolContext(project)

    initial_state = _exec_tool(ctx, "read_current_html", {})
    state_summary = (
        f"📍 السياق:\n"
        f"  اسم المشروع: {project.get('name','?')}\n"
        f"  الوصف: {project.get('description','(لم يحدّد)')}\n"
        f"  الموقع الحالي: {initial_state.get('summary','(فارغ)')}\n"
    )

    messages: List[Dict[str, Any]] = []
    for m in history_messages[-12:]:
        if m.get("role") in ("user", "assistant"):
            content = m.get("content", "")
            if isinstance(content, str) and content.strip():
                messages.append({"role": m["role"], "content": content})
    messages.append({"role": "user", "content": f"{state_summary}\n\nالطلب: {user_message}"})

    summary = ""
    options: List[str] = []
    iterations = 0
    model_used = model

    for _step in range(max_iterations):
        iterations += 1
        try:
            resp = await client.messages.create(
                model=model,
                system=AGENT_SYSTEM_PROMPT,
                max_tokens=8000,
                tools=TOOLS_SCHEMA,
                messages=messages,
            )
        except Exception as e:
            return {"ok": False, "error": f"anthropic call failed: {type(e).__name__}: {str(e)[:200]}",
                    "iterations": iterations, "tool_log": ctx.tool_log}

        model_used = getattr(resp, "model", model)
        assistant_blocks: List[Dict[str, Any]] = []
        tool_uses: List[Dict[str, Any]] = []
        for block in resp.content:
            btype = getattr(block, "type", "")
            if btype == "text":
                assistant_blocks.append({"type": "text", "text": block.text})
            elif btype == "tool_use":
                assistant_blocks.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
                tool_uses.append({"id": block.id, "name": block.name, "input": block.input})
        messages.append({"role": "assistant", "content": assistant_blocks})

        if not tool_uses:
            for b in assistant_blocks:
                if b.get("type") == "text":
                    summary = (summary + "\n" + b["text"]).strip()
            break

        tool_results: List[Dict[str, Any]] = []
        finished = False
        for tu in tool_uses:
            if tu["name"] == "finish":
                summary = (tu["input"].get("summary") or "").strip()
                options = [o for o in (tu["input"].get("options") or []) if isinstance(o, str)][:4]
                ctx.log("finish", tu["input"], "agent finished")
                tool_results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": "finished"})
                finished = True
            else:
                result = _exec_tool(ctx, tu["name"], tu["input"])
                ctx.log(tu["name"], tu["input"], result)
                tool_results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": json.dumps(result, ensure_ascii=False)[:6000]})
        messages.append({"role": "user", "content": tool_results})
        if finished:
            break

    return {
        "ok": True,
        "summary": summary or "تم.",
        "options": options,
        "new_html": ctx.current_html if ctx.changes_made > 0 else None,
        "iterations": iterations,
        "tool_log": ctx.tool_log,
        "snapshots": ctx.snapshots_to_create,
        "model_used": model_used,
        "changes_made": ctx.changes_made,
    }


async def _run_openai_compat_agent(
    project: Dict[str, Any],
    user_message: str,
    history_messages: List[Dict[str, str]],
    max_iterations: int,
    provider: str,
    model: str,
) -> Dict[str, Any]:
    """OpenAI-compatible tool-use agent (works for OpenAI, Moonshot/Kimi)."""
    try:
        from openai import AsyncOpenAI
    except Exception:
        return {"ok": False, "error": "openai SDK missing"}

    if provider == "moonshot":
        api_key = os.environ.get("MOONSHOT_API_KEY", "")
        base_url = "https://api.moonshot.ai/v1"
    else:
        api_key = os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY", "")
        base_url = None
    if not api_key:
        return {"ok": False, "error": f"{provider} API key not configured"}

    client = AsyncOpenAI(api_key=api_key, base_url=base_url) if base_url else AsyncOpenAI(api_key=api_key)
    ctx = FreeBuildToolContext(project)

    initial_state = _exec_tool(ctx, "read_current_html", {})
    state_summary = (
        f"📍 السياق:\n"
        f"  اسم المشروع: {project.get('name','?')}\n"
        f"  الوصف: {project.get('description','(لم يحدّد)')}\n"
        f"  الموقع الحالي: {initial_state.get('summary','(فارغ)')}\n"
    )

    # Convert tool schema to OpenAI format
    openai_tools = [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
        for t in TOOLS_SCHEMA
    ]

    messages: List[Dict[str, Any]] = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]
    for m in history_messages[-12:]:
        if m.get("role") in ("user", "assistant"):
            content = m.get("content", "")
            if isinstance(content, str) and content.strip():
                messages.append({"role": m["role"], "content": content})
    messages.append({"role": "user", "content": f"{state_summary}\n\nالطلب: {user_message}"})

    summary = ""
    options: List[str] = []
    iterations = 0
    model_used = model

    for _step in range(max_iterations):
        iterations += 1
        try:
            resp = await client.chat.completions.create(
                model=model, messages=messages, tools=openai_tools, max_tokens=8000,
            )
        except Exception as e:
            return {"ok": False, "error": f"{provider} call failed: {type(e).__name__}: {str(e)[:200]}",
                    "iterations": iterations, "tool_log": ctx.tool_log}

        choice = resp.choices[0]
        msg = choice.message
        model_used = getattr(resp, "model", model)
        text_content = msg.content or ""
        tool_calls = msg.tool_calls or []

        # Persist assistant turn in OpenAI conversation format
        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": text_content or None}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ]
        messages.append(assistant_msg)

        if not tool_calls:
            summary = text_content.strip()
            break

        finished = False
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            if tc.function.name == "finish":
                summary = (args.get("summary") or "").strip()
                options = [o for o in (args.get("options") or []) if isinstance(o, str)][:4]
                ctx.log("finish", args, "agent finished")
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": "finished"})
                finished = True
            else:
                result = _exec_tool(ctx, tc.function.name, args)
                ctx.log(tc.function.name, args, result)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result, ensure_ascii=False)[:6000]})
        if finished:
            break

    return {
        "ok": True,
        "summary": summary or "تم.",
        "options": options,
        "new_html": ctx.current_html if ctx.changes_made > 0 else None,
        "iterations": iterations,
        "tool_log": ctx.tool_log,
        "snapshots": ctx.snapshots_to_create,
        "model_used": model_used,
        "changes_made": ctx.changes_made,
    }
