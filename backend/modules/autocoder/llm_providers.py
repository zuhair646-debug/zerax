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
GEMINI_MODEL = "gemini-2.0-flash-exp"
MAX_HISTORY_TURNS = 6
MAX_ITERATIONS = 15


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

    # Prune history
    if len(anthropic_msgs) > MAX_HISTORY_TURNS:
        anthropic_msgs = anthropic_msgs[-MAX_HISTORY_TURNS:]

    msgs = anthropic_msgs_to_openai(anthropic_msgs, system_prompt)
    openai_tools = anthropic_tools_to_openai(tools_anthropic)

    total_in = total_out = 0
    for iteration in range(MAX_ITERATIONS):
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                resp = await c.post(
                    GROQ_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "messages": msgs,
                        "tools": openai_tools,
                        "tool_choice": "auto",
                        "temperature": 0.3,
                        "max_tokens": 4096,
                    },
                )
        except Exception as e:
            yield {"type": "error", "message": f"groq api: {str(e)[:240]}"}
            return

        if resp.status_code != 200:
            try:
                err_body = resp.json()
                err_msg = err_body.get("error", {}).get("message", resp.text[:300])
            except Exception:
                err_msg = resp.text[:300]
            yield {"type": "error", "message": f"groq {resp.status_code}: {err_msg}"}
            return

        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        usage = data.get("usage") or {}
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        total_in += in_tok
        total_out += out_tok
        if iteration == 0:
            yield {
                "type": "usage",
                "input": in_tok, "output": out_tok,
                "cached_read": 0, "cost_usd": 0.0,  # Groq free tier
                "provider": "groq",
            }

        text = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []

        # Stream the text portion (chunked)
        if text:
            for i in range(0, len(text), 40):
                yield {"type": "text", "content": text[i:i + 40]}
                await asyncio.sleep(0.005)

        # Append assistant turn to history
        assistant_entry: Dict[str, Any] = {"role": "assistant", "content": text or ""}
        if tool_calls:
            assistant_entry["tool_calls"] = tool_calls
        msgs.append(assistant_entry)

        finish_reason = choice.get("finish_reason")
        if not tool_calls or finish_reason == "stop":
            yield {"type": "done"}
            return

        # Execute each tool call
        for tc in tool_calls:
            fn = (tc.get("function") or {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}
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

    yield {"type": "text", "content": "\n(وصلت لحد الـiterations — اطلب تكملة لو تبي.)"}
    yield {"type": "done"}


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
                        "systemInstruction": {"parts": [{"text": system_prompt}]},
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
