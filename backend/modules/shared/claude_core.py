"""
Shared Claude streaming agent core — used by every AI section across Zerax
(FreeBuild, Game Studio, App Studio, Marketing, Companion, Mobile Builder, ...).

Goals:
- ONE model everywhere: Claude Sonnet 4.5 (same family as the platform AI)
- ONE streaming pattern: SSE with text_delta, tool_building (live snippets),
  heartbeat pings every 3s, graceful errors
- ONE tool-use loop: producer/consumer asyncio queue so even silent Anthropic
  generation phases don't drop the connection
- Sections plug in their own:
    - system_prompt   → the section's voice + scope
    - tools_schema    → section-specific tools (web tools, image tools, ...)
    - tools_executor  → async callable(name, input) → result dict
    - on_done(captured) → optional persist hook fired when the loop ends

Why centralize?
- Quality parity: every section feels as capable as the main platform AI
- One place to upgrade model versions, add new event types, fix bugs
- Sections stay focused on their DOMAIN (their tools/prompt), not plumbing

NOTE: This module does NOT import any module-specific code (freebuild,
games, etc.) — sections wire themselves into it, not vice versa.
"""
from __future__ import annotations
import os
import json
import asyncio
import logging
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("zerax.shared.claude_core")

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_MAX_TOKENS = 8000
DEFAULT_MAX_ITERATIONS = 15
HEARTBEAT_INTERVAL_SEC = 3.0
SNIPPET_BYTES_THRESHOLD = 400
SNIPPET_TAIL_CHARS = 280


def _sse(event: str, data: Dict[str, Any]) -> str:
    """Format one Server-Sent Event chunk."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class _ProviderUnavailable(Exception):
    """Raised when Anthropic credit/key issues block the call."""


def _get_anthropic_client():
    """Returns AsyncAnthropic configured from env. Raises if no key."""
    key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        raise _ProviderUnavailable(
            "⚠️ مفتاح Anthropic غير مهيّأ. أضف ANTHROPIC_API_KEY في الإعدادات."
        )
    from anthropic import AsyncAnthropic
    return AsyncAnthropic(api_key=key, timeout=180.0)


async def run_claude_agent(
    *,
    system_prompt: str,
    user_message: str,
    history_messages: List[Dict[str, str]],
    tools_schema: List[Dict[str, Any]],
    tools_executor: Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]],
    section_label: str = "agent",
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    model: str = DEFAULT_MODEL,
    captured: Optional[Dict[str, Any]] = None,
    finish_tool_name: str = "finish",
    tool_labels_ar: Optional[Dict[str, Dict[str, str]]] = None,
) -> AsyncGenerator[str, None]:
    """
    Stream one full agent turn for any section.

    Yields SSE chunks (raw strings). The caller wraps these in a
    StreamingResponse(media_type='text/event-stream').

    `tools_executor(name, input_dict) -> dict` runs the actual tool body
    server-side. The result dict is sent back to Claude as tool_result.
    The dict may include `"label"` (Arabic friendly label shown in UI).

    `captured` is populated with: summary, options, iterations, model_used,
    tool_log, html_updated. Caller persists from this dict after the
    generator completes.

    `tool_labels_ar` maps tool_name → {"running": "🔍 ...", "done": "✓ ..."}
    for nicer Arabic UI; if omitted, raw tool names are used.
    """
    captured = captured if captured is not None else {}
    labels = tool_labels_ar or {}
    accumulated_text: List[str] = []
    all_tool_log: List[Dict[str, Any]] = []
    summary = ""
    options: List[str] = []
    iterations = 0
    model_used = model

    try:
        client = _get_anthropic_client()
    except _ProviderUnavailable as e:
        yield _sse("error", {"message": str(e)})
        yield _sse("done", {"summary": str(e), "options": [], "iterations": 0,
                            "model_used": "", "html_updated": False, "tool_log": []})
        return

    yield _sse("start", {"section": section_label, "model": model})
    yield _sse("provider", {"name": "anthropic"})

    # Build messages array for Claude (history + new user msg)
    messages: List[Dict[str, Any]] = []
    for m in history_messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    finished = False

    for step in range(max_iterations):
        iterations += 1
        logger.info(f"[{section_label}-stream] iter={iterations} start")

        text_chunks: List[str] = []
        tool_uses: List[Dict[str, Any]] = []
        assistant_blocks: List[Dict[str, Any]] = []
        final_msg = None
        current_text = ""
        tool_input_bytes = 0
        last_tool_emit = 0
        tool_input_snapshot = ""
        current_tool_name = ""
        queue: asyncio.Queue = asyncio.Queue()
        _SF, _SE = "__final__", "__error__"

        async def _produce():
            try:
                async with client.messages.stream(
                    model=model, system=system_prompt, max_tokens=max_tokens,
                    tools=tools_schema, messages=messages,
                ) as st:
                    async for ev in st:
                        await queue.put(("event", ev))
                    fm = await st.get_final_message()
                await queue.put((_SF, fm))
            except Exception as exc:
                await queue.put((_SE, exc))

        producer = asyncio.create_task(_produce())
        stream_err: Optional[BaseException] = None
        try:
            while True:
                try:
                    kind, payload = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL_SEC)
                except asyncio.TimeoutError:
                    yield _sse("ping", {"t": int(asyncio.get_event_loop().time()), "step": iterations})
                    await asyncio.sleep(0)
                    continue
                if kind == _SF:
                    final_msg = payload
                    break
                if kind == _SE:
                    stream_err = payload
                    break
                ev = payload
                et = getattr(ev, "type", "")
                if et == "text":
                    delta = getattr(ev, "text", "") or ""
                    if delta:
                        current_text += delta
                        yield _sse("text_delta", {"text": delta, "step": iterations})
                        await asyncio.sleep(0)
                elif et == "content_block_start":
                    cb = getattr(ev, "content_block", None)
                    if cb is not None and getattr(cb, "type", "") == "tool_use":
                        current_tool_name = getattr(cb, "name", "") or ""
                        tool_input_snapshot = ""
                        tool_input_bytes = 0
                        last_tool_emit = 0
                        running = labels.get(current_tool_name, {}).get("running", f"⚙️ {current_tool_name}")
                        yield _sse("tool_building", {
                            "step": iterations, "tool_name": current_tool_name,
                            "snippet": "", "bytes": 0, "label": running, "starting": True,
                        })
                        await asyncio.sleep(0)
                elif et == "input_json":
                    partial = getattr(ev, "partial_json", "") or ""
                    tool_input_snapshot += partial
                    tool_input_bytes = len(tool_input_snapshot)
                    if tool_input_bytes - last_tool_emit >= SNIPPET_BYTES_THRESHOLD or last_tool_emit == 0:
                        tail = tool_input_snapshot[-SNIPPET_TAIL_CHARS:] if len(tool_input_snapshot) > SNIPPET_TAIL_CHARS else tool_input_snapshot
                        yield _sse("tool_building", {
                            "step": iterations, "tool_name": current_tool_name,
                            "snippet": tail, "bytes": tool_input_bytes,
                            "label": f"⚙️ يكتب الكود... ({tool_input_bytes:,} حرف)",
                        })
                        await asyncio.sleep(0)
                        last_tool_emit = tool_input_bytes
                elif et == "content_block_stop":
                    if current_text.strip():
                        yield _sse("text_end", {"step": iterations})
                        await asyncio.sleep(0)
                    if tool_input_bytes > 0:
                        yield _sse("tool_building", {
                            "step": iterations, "tool_name": current_tool_name,
                            "snippet": "", "bytes": tool_input_bytes,
                            "label": f"✨ تم توليد الكود ({tool_input_bytes:,} حرف)",
                            "done": True,
                        })
                        await asyncio.sleep(0)
                    current_text = ""
                    tool_input_bytes = 0
                    last_tool_emit = 0
                    tool_input_snapshot = ""
                    current_tool_name = ""
        finally:
            if not producer.done():
                producer.cancel()
                try:
                    await producer
                except (asyncio.CancelledError, Exception):
                    pass

        if stream_err is not None:
            msg = f"{type(stream_err).__name__}: {str(stream_err)[:200]}"
            logger.exception(f"[{section_label}] anthropic stream failed", exc_info=stream_err)
            if any(k in msg.lower() for k in ["credit", "balance", "401", "402", "429", "quota"]):
                err = "⚠️ رصيد Anthropic منتهي. شحن من: console.anthropic.com/settings/billing"
                yield _sse("error", {"message": err})
                yield _sse("done", {"summary": err, "options": [], "iterations": iterations,
                                    "model_used": "", "html_updated": captured.get("html_updated", False),
                                    "tool_log": all_tool_log})
                return
            yield _sse("error", {"message": msg})
            break

        model_used = getattr(final_msg, "model", model)
        stop_reason = getattr(final_msg, "stop_reason", "?")
        logger.info(f"[{section_label}-stream] iter={iterations} done. stop={stop_reason}")

        for block in (final_msg.content or []):
            bt = getattr(block, "type", "")
            if bt == "text":
                text_chunks.append(block.text)
                accumulated_text.append(block.text)
                assistant_blocks.append({"type": "text", "text": block.text})
            elif bt == "tool_use":
                assistant_blocks.append({"type": "tool_use", "id": block.id,
                                         "name": block.name, "input": block.input})
                tool_uses.append({"id": block.id, "name": block.name, "input": block.input})
        messages.append({"role": "assistant", "content": assistant_blocks})

        if not tool_uses:
            summary = "\n".join(text_chunks).strip()
            break

        tool_results: List[Dict[str, Any]] = []
        for tu in tool_uses:
            tn = tu["name"]
            running_lbl = labels.get(tn, {}).get("running", f"⚙️ {tn}")
            yield _sse("tool", {"name": tn, "phase": "running", "label": running_lbl, "step": iterations})
            await asyncio.sleep(0)
            try:
                if tn == finish_tool_name:
                    inp = tu["input"] or {}
                    summary = (inp.get("summary") or "").strip()
                    options = inp.get("options") or []
                    finished = True
                    done_lbl = labels.get(tn, {}).get("done", "✅ تم")
                    yield _sse("tool", {"name": tn, "phase": "done", "label": done_lbl,
                                        "step": iterations, "result_preview": "finished"})
                    all_tool_log.append({"name": tn, "input": inp, "result": "finished"})
                    break
                result = await tools_executor(tn, tu["input"] or {})
                result_label = (result or {}).get("label") or labels.get(tn, {}).get("done", f"✓ {tn}")
                yield _sse("tool", {"name": tn, "phase": "done", "label": result_label,
                                    "step": iterations,
                                    "result_preview": (result or {}).get("preview") or "ok"})
                all_tool_log.append({"name": tn, "input": tu["input"], "result": result})
                tool_results.append({
                    "type": "tool_result", "tool_use_id": tu["id"],
                    "content": json.dumps(result or {"ok": True}, ensure_ascii=False)[:8000],
                })
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                logger.exception(f"[{section_label}] tool {tn} failed")
                yield _sse("tool", {"name": tn, "phase": "error", "label": f"❌ خطأ: {err[:100]}",
                                    "step": iterations})
                tool_results.append({
                    "type": "tool_result", "tool_use_id": tu["id"],
                    "content": json.dumps({"error": err}), "is_error": True,
                })

        if finished:
            break
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    if not summary or len(summary.strip()) < 8:
        joined = "\n\n".join(t.strip() for t in accumulated_text if t and t.strip())
        if joined:
            summary = joined.strip()
        else:
            summary = "تمام، فهمت طلبك. قول لي تفاصيل أكثر وأبدأ مباشرة."

    captured["summary"] = summary
    captured["options"] = options
    captured["iterations"] = iterations
    captured["model_used"] = model_used
    captured["tool_log"] = all_tool_log

    yield _sse("done", {
        "summary": summary, "options": options, "iterations": iterations,
        "model_used": model_used, "html_updated": captured.get("html_updated", False),
        "tool_log": all_tool_log,
    })
