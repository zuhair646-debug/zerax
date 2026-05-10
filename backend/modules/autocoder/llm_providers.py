"""
Multi-LLM provider streaming for the Auto-Coder.
Supports Groq (Llama 3.3) and Gemini (2.0 Flash) as FREE alternatives to Claude.

All providers yield the same event shape as the Claude streamer:
    {type: 'text', content: str}
    {type: 'tool', status: 'calling'|'done', name, ok?, args?, summary?, preview?}
    {type: 'usage', input, output, cached_read, cost_usd}
    {type: 'done'}
    {type: 'error', message}
"""
from __future__ import annotations
import json
import asyncio
import logging
from typing import Any, Dict, List, Callable, Awaitable, Optional

import httpx

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODEL = "gemini-2.5-flash"
MAX_HISTORY_TURNS = 10
MAX_ITERATIONS = 60


# ════════════════════════════════════════════════════════════════════════
# Schema converters
# ════════════════════════════════════════════════════════════════════════
def anthropic_tools_to_openai(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert Anthropic tool schema → OpenAI function-calling schema (for Groq)."""
    out = []
    for t in tools:
        # strip Anthropic-only fields
        schema = {k: v for k, v in t.get("input_schema", {}).items()
                  if k != "cache_control"}
        out.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": schema or {"type": "object", "properties": {}},
            },
        })
    return out


def anthropic_tools_to_gemini(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert Anthropic tool schema → Gemini function declarations."""
    decls = []
    for t in tools:
        schema = dict(t.get("input_schema", {}))
        schema.pop("cache_control", None)
        # Gemini wants "parameters" instead of "input_schema"; type names are same.
        # Sanitize: Gemini doesn't accept some JSON-schema keys (additionalProperties etc.)
        params = _sanitize_gemini_schema(schema)
        decls.append({
            "name": t["name"],
            "description": t.get("description", ""),
            "parameters": params if params else {"type": "object", "properties": {}},
        })
    return [{"functionDeclarations": decls}]


def _sanitize_gemini_schema(s: Any) -> Any:
    """Gemini rejects unknown keys; keep only the safe subset."""
    if not isinstance(s, dict):
        return s
    allowed = {"type", "description", "properties", "required", "items", "enum", "format", "nullable"}
    out: Dict[str, Any] = {}
    for k, v in s.items():
        if k not in allowed:
            continue
        if k == "properties" and isinstance(v, dict):
            out[k] = {pk: _sanitize_gemini_schema(pv) for pk, pv in v.items()}
        elif k == "items":
            out[k] = _sanitize_gemini_schema(v)
        else:
            out[k] = v
    # Gemini requires uppercase types (TYPE_STRING etc) in v1, but v1beta accepts lowercase
    return out


# ════════════════════════════════════════════════════════════════════════
# History converters (anthropic_msgs already used by Claude streamer)
# ════════════════════════════════════════════════════════════════════════
def anthropic_msgs_to_openai(messages: List[Dict[str, Any]], system: str) -> List[Dict[str, Any]]:
    """Convert simple {role, content:str} list to OpenAI chat format."""
    out: List[Dict[str, Any]] = [{"role": "system", "content": system}]
    for m in messages:
        out.append({
            "role": m.get("role", "user"),
            "content": m.get("content", "") if isinstance(m.get("content"), str) else str(m.get("content"))[:4000],
        })
    return out


def anthropic_msgs_to_gemini(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert to Gemini contents array. user→user, assistant→model."""
    contents: List[Dict[str, Any]] = []
    for m in messages:
        role = "user" if m.get("role") == "user" else "model"
        text = m.get("content", "") if isinstance(m.get("content"), str) else str(m.get("content"))[:4000]
        if not text.strip():
            continue
        contents.append({"role": role, "parts": [{"text": text}]})
    return contents


# ════════════════════════════════════════════════════════════════════════
# Groq streamer (Llama 3.3 70B — free)
# ════════════════════════════════════════════════════════════════════════
async def stream_via_groq(
    anthropic_msgs: List[Dict[str, Any]],
    api_key: str,
    system_prompt: str,
    tools_anthropic: List[Dict[str, Any]],
    execute_tool: Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]],
    trim_args_for_ui: Callable[[Dict[str, Any]], Dict[str, Any]],
    summarize: Callable[[str, Dict[str, Any]], str],
    preview: Callable[[str, Dict[str, Any]], str],
    trim_result_for_llm: Callable[[Dict[str, Any]], Dict[str, Any]],
):
    if not api_key:
        yield {"type": "error", "message": "GROQ_API_KEY غير مضبوط في Railway. اضفه ثم جرّب."}
        return

    # Prune history (Groq has tighter context than Claude)
    if len(anthropic_msgs) > MAX_HISTORY_TURNS:
        anthropic_msgs = anthropic_msgs[-MAX_HISTORY_TURNS:]

    # ── Compact system prompt for Groq (free tier has 12k TPM limit) ──
    # The full Claude prompt is ~5k tokens. We compress to ~1.5k for Groq so
    # tokens don't get blown on prompt, and Llama gets clearer tool guidance.
    compact_prompt = _compact_system_prompt_for_free_models(system_prompt)

    msgs = anthropic_msgs_to_openai(anthropic_msgs, compact_prompt)
    openai_tools = anthropic_tools_to_openai(tools_anthropic)

    total_in = total_out = 0
    for iteration in range(MAX_ITERATIONS):
        try:
            text_buffer = ""
            tool_calls_buffer: Dict[int, Dict[str, Any]] = {}
            usage_data: Dict[str, int] = {}
            finish_reason = None

            async with httpx.AsyncClient(timeout=180) as c:
                async with c.stream(
                    "POST",
                    GROQ_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "messages": msgs,
                        "tools": openai_tools,
                        "tool_choice": "auto",
                        "temperature": 0.3,
                        "max_tokens": 4096,
                        "stream": True,
                        "stream_options": {"include_usage": True},
                    },
                ) as resp:
                    if resp.status_code != 200:
                        body_text = ""
                        try:
                            body_text = (await resp.aread()).decode("utf-8", errors="replace")[:600]
                        except Exception:
                            body_text = "(no body)"
                        yield {"type": "error",
                               "message": _humanize_groq_error(resp.status_code, body_text)}
                        return

                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload)
                        except Exception:
                            continue

                        # Capture usage (sent in last chunk)
                        u = chunk.get("usage")
                        if u:
                            usage_data = u

                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        delta = choices[0].get("delta") or {}
                        finish_reason = choices[0].get("finish_reason") or finish_reason

                        # Stream text delta
                        text_delta = delta.get("content")
                        if text_delta:
                            text_buffer += text_delta
                            yield {"type": "text", "content": text_delta}

                        # Accumulate tool call deltas (OpenAI format streams in pieces)
                        for tcd in (delta.get("tool_calls") or []):
                            idx = tcd.get("index", 0)
                            slot = tool_calls_buffer.setdefault(idx, {
                                "id": "", "type": "function",
                                "function": {"name": "", "arguments": ""},
                            })
                            if tcd.get("id"):
                                slot["id"] = tcd["id"]
                            fn = tcd.get("function") or {}
                            if fn.get("name"):
                                slot["function"]["name"] += fn["name"]
                            if fn.get("arguments"):
                                slot["function"]["arguments"] += fn["arguments"]
        except httpx.ReadTimeout:
            yield {"type": "error", "message": "Groq استغرق وقت أطول من المتوقع. حاول مرة ثانية."}
            return
        except Exception as e:
            yield {"type": "error", "message": f"Groq exception: {str(e)[:240]}"}
            return

        # Emit usage event (first iteration)
        if iteration == 0 and usage_data:
            in_tok = usage_data.get("prompt_tokens", 0)
            out_tok = usage_data.get("completion_tokens", 0)
            total_in += in_tok
            total_out += out_tok
            yield {
                "type": "usage",
                "input": in_tok, "output": out_tok,
                "cached_read": 0, "cost_usd": 0.0,
                "provider": "groq",
            }

        tool_calls = list(tool_calls_buffer.values())

        # Build assistant entry for history
        assistant_entry: Dict[str, Any] = {"role": "assistant", "content": text_buffer or ""}
        if tool_calls:
            assistant_entry["tool_calls"] = tool_calls
        msgs.append(assistant_entry)

        # No tool calls → done
        if not tool_calls or finish_reason == "stop":
            yield {"type": "done"}
            return

        # Execute each tool call
        for tc in tool_calls:
            fn = tc.get("function") or {}
            name = fn.get("name", "")
            raw_args = fn.get("arguments")
            try:
                args = json.loads(raw_args) if raw_args else {}
                if not isinstance(args, dict):
                    args = {}
            except Exception as e:
                yield {"type": "tool", "status": "done", "name": name or "?",
                       "ok": False, "summary": f"فشل parse args: {e}"}
                msgs.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "name": name,
                    "content": json.dumps({"ok": False, "error": "invalid JSON arguments"}),
                })
                continue
            yield {"type": "tool", "status": "calling", "name": name,
                   "args": trim_args_for_ui(args)}
            result = await execute_tool(name, args)
            yield {"type": "tool", "status": "done", "name": name,
                   "ok": result.get("ok", False),
                   "summary": summarize(name, result),
                   "preview": preview(name, result)}
            msgs.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "name": name,
                "content": json.dumps(trim_result_for_llm(result), ensure_ascii=False)[:14000],
            })

    yield {"type": "text", "content": "\n(وصلت لحد iterations)"}
    yield {"type": "done"}


# ────────────────────────────────────────────────────────────────────
# Helpers for free models
# ────────────────────────────────────────────────────────────────────
def _humanize_groq_error(status_code: int, body_text: str) -> str:
    """Convert Groq HTTP errors to clear Arabic messages."""
    body_lower = body_text.lower()
    if status_code == 429:
        if "tpm" in body_lower or "tokens per minute" in body_lower:
            return ("تجاوزت حد الـtokens/الدقيقة على Groq Free Tier (12,000 TPM). "
                    "حلول: (1) استنّى ~30 ثانية وحاول، أو (2) ارفع لـDev Tier مجاناً من "
                    "console.groq.com/settings/billing (يحتاج بطاقة، ما تنخصم)، أو (3) بدّل الموديل لـClaude.")
        if "rpm" in body_lower or "requests per" in body_lower:
            return "تجاوزت حد الطلبات/الدقيقة على Groq. استنّى دقيقة وحاول."
        return "تجاوزت حد المعدّل على Groq. استنّى ثم حاول مرة ثانية."
    if status_code == 401 or status_code == 403:
        return "GROQ_API_KEY غير صالح أو منتهي. أنشئ key جديد من console.groq.com/keys"
    if status_code == 413 or "too large" in body_lower or "context" in body_lower:
        return "المحادثة كبرت كثير. ابدأ محادثة جديدة (زر '+ جديدة' فوق)."
    if status_code >= 500:
        return f"Groq يواجه مشكلة مؤقتة (HTTP {status_code}). حاول بعد دقيقة."
    return f"Groq HTTP {status_code}: {body_text[:200]}"


def _compact_system_prompt_for_free_models(full_prompt: str) -> str:
    """Strip the verbose Claude-targeted system prompt down to the essentials
    that smaller models like Llama actually use. Saves ~3000 tokens per call."""
    return (
        "أنت 'برمجة زيتاكس' — مهندس برمجيات سعودي يعمل على الكود الفعلي في /app.\n\n"
        "**صلاحياتك مفتوحة بالكامل**: قراءة، كتابة، تعديل أي ملف؛ تنفيذ أي bash؛ git commit + push.\n\n"
        "🛡️ **استثناء وحيد** — ممنوع تعدّل/تكتب/تحذف هذي الملفات (وحدتك أنت):\n"
        "  - /app/backend/modules/autocoder/__init__.py\n"
        "  - /app/backend/modules/autocoder/llm_providers.py\n"
        "  - /app/backend/modules/autocoder/tools_extra.py\n"
        "لو حاولت → الأداة راح ترفض. هذي حماية ضروري ضد التخريب الذاتي.\n\n"
        "**AUTONOMOUS MODE**: نفّذ المهمة كاملةً قبل ما توقف. لا تستأذن بين الخطوات.\n\n"
        "⚡ **قانون التنفيذ الفوري**:\n"
        "- في أول رسالة، **ابدأ باستدعاء أداة فوراً**. ممنوع كتابة paragraphs قبل tool call.\n"
        "- نمط مطلوب: 'حلو، بفحص X.' → tool → نتيجة → 'فيها Y، بسوي Z.' → tool → ...\n"
        "- ممنوع: 'أكيد، خل أشرح لك خطة العمل أولاً: ...' (كلام بلا تنفيذ).\n\n"
        "**سير العمل لكل خطوة**:\n"
        "1. قبل أي أداة: جملة قصيرة بالعربي تشرح وش راح تسوي.\n"
        "2. استدعِ الأداة.\n"
        "3. بعد الأداة: جملة تلخّص النتيجة.\n"
        "4. كرّر حتى تخلّص. الجملة الأخيرة = ملخص نهائي شامل (3-5 جمل).\n\n"
        "**استخدام الأدوات**:\n"
        "- لا تخمّن. قبل أي تعديل: `read_file`.\n"
        "- لو تبحث: `search_code`.\n"
        "- بعد تعديل python: `pre_deploy_check` قبل الـcommit.\n"
        "- بعد الـpush: `check_deployment_status`.\n"
        "- لو تكسّر الموقع: `rollback_to_last_good`.\n\n"
        "**خريطة الكود**:\n"
        "- /app/backend/server.py (FastAPI main)\n"
        "- /app/backend/modules/<name>/__init__.py (الموديولات: agent, freebuild_v2, websites…)\n"
        "- /app/frontend/src/App.js (router)\n"
        "- /app/frontend/src/pages/<Name>.js + /components/<Name>.js\n\n"
        "**قواعد**:\n"
        "1. اقرأ قبل ما تكتب.\n"
        "2. على Railway production: ما فيه supervisorctl — استخدم restart_service.\n"
        "3. لو edit_file فشل بـ'not unique' → استخدم occurrence=N أو replace_all=true.\n"
        "4. تكلم بالعربي السعودي مع المالك. قصير وعملي.\n"
        "5. عند الانتهاء: commit + push + check_deployment_status + ملخص نهائي.\n"
    )


# ════════════════════════════════════════════════════════════════════════
# Gemini streamer (gemini-2.0-flash — free)
# ════════════════════════════════════════════════════════════════════════
async def stream_via_gemini(
    anthropic_msgs: List[Dict[str, Any]],
    api_key: str,
    system_prompt: str,
    tools_anthropic: List[Dict[str, Any]],
    execute_tool: Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]],
    trim_args_for_ui: Callable[[Dict[str, Any]], Dict[str, Any]],
    summarize: Callable[[str, Dict[str, Any]], str],
    preview: Callable[[str, Dict[str, Any]], str],
    trim_result_for_llm: Callable[[Dict[str, Any]], Dict[str, Any]],
):
    if not api_key:
        yield {"type": "error",
               "message": "GEMINI_API_KEY غير مضبوط. احصل عليه مجاناً من https://aistudio.google.com/apikey وأضفه في Railway."}
        return

    if len(anthropic_msgs) > MAX_HISTORY_TURNS:
        anthropic_msgs = anthropic_msgs[-MAX_HISTORY_TURNS:]

    contents = anthropic_msgs_to_gemini(anthropic_msgs)
    tools_gemini = anthropic_tools_to_gemini(tools_anthropic)
    compact_sys = _compact_system_prompt_for_free_models(system_prompt)

    url = f"{GEMINI_BASE}/{GEMINI_MODEL}:generateContent?key={api_key}"

    total_in = total_out = 0
    yielded_usage = False

    for iteration in range(MAX_ITERATIONS):
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                resp = await c.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "systemInstruction": {"parts": [{"text": compact_sys}]},
                        "contents": contents,
                        "tools": tools_gemini,
                        "toolConfig": {"functionCallingConfig": {"mode": "AUTO"}},
                        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
                    },
                )
        except Exception as e:
            yield {"type": "error", "message": f"gemini api: {str(e)[:240]}"}
            return

        if resp.status_code != 200:
            try:
                err_body = resp.json()
                err_msg = (err_body.get("error") or {}).get("message", resp.text[:300])
            except Exception:
                err_msg = resp.text[:300]
            yield {"type": "error", "message": f"gemini {resp.status_code}: {err_msg}"}
            return

        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            yield {"type": "error", "message": "gemini: no candidates returned"}
            return

        cand = candidates[0]
        cand_content = cand.get("content") or {}
        parts = cand_content.get("parts") or []
        finish_reason = cand.get("finishReason", "")

        # Usage (only first iteration)
        usage = data.get("usageMetadata") or {}
        if not yielded_usage:
            in_tok = usage.get("promptTokenCount", 0)
            out_tok = usage.get("candidatesTokenCount", 0)
            total_in += in_tok
            total_out += out_tok
            yield {
                "type": "usage",
                "input": in_tok, "output": out_tok,
                "cached_read": 0, "cost_usd": 0.0,  # Gemini free tier
                "provider": "gemini",
            }
            yielded_usage = True

        # Collect text + functionCalls
        text_chunks: List[str] = []
        function_calls: List[Dict[str, Any]] = []
        for p in parts:
            if "text" in p and p["text"]:
                text_chunks.append(p["text"])
            elif "functionCall" in p:
                fc = p["functionCall"]
                function_calls.append({
                    "name": fc.get("name", ""),
                    "args": fc.get("args") or {},
                })

        # Append model turn to history (must keep parts intact for tool use)
        if parts:
            contents.append({"role": "model", "parts": parts})

        # Stream text
        text_full = "".join(text_chunks)
        if text_full:
            for i in range(0, len(text_full), 40):
                yield {"type": "text", "content": text_full[i:i + 40]}
                await asyncio.sleep(0.005)

        if not function_calls:
            yield {"type": "done"}
            return

        # Execute tools, then send results back as user message with functionResponse parts
        response_parts = []
        for fc in function_calls:
            name = fc["name"]
            args = fc["args"] or {}
            yield {"type": "tool", "status": "calling", "name": name,
                   "args": trim_args_for_ui(args)}
            result = await execute_tool(name, args)
            yield {"type": "tool", "status": "done", "name": name,
                   "ok": result.get("ok", False),
                   "summary": summarize(name, result),
                   "preview": preview(name, result)}
            response_parts.append({
                "functionResponse": {
                    "name": name,
                    "response": {"content": trim_result_for_llm(result)},
                }
            })

        contents.append({"role": "user", "parts": response_parts})

        if finish_reason == "STOP" and not function_calls:
            yield {"type": "done"}
            return

    yield {"type": "text", "content": "\n(وصلت لحد الـiterations — اطلب تكملة لو تبي.)"}
    yield {"type": "done"}
