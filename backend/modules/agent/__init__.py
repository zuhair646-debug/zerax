"""
Zitex AI Agent — an open, conversational agent that behaves like Claude/ChatGPT.

Unlike the architect (which is rigid and optimised for HTML generation), this
agent is a FREE-FORM chat that:
    • Streams natural Arabic responses
    • Calls the 7 FreeBuild v2 tools freely (up to 20 iterations)
    • Keeps conversation memory across turns (MongoDB)
    • Lets the user pick model: claude-sonnet-4-5 or gpt-4o
    • Exposes the live tool activity so the user sees 'the thinking'

Endpoints:
    POST /api/agent/chat         — stream responses
    GET  /api/agent/conversations — list user conversations
    GET  /api/agent/conversation/{id}
    DELETE /api/agent/conversation/{id}
"""
from __future__ import annotations
import os
import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ════════════════════════════════════════════════════════════════════════
#  System prompt — open, conversational, tool-using
# ════════════════════════════════════════════════════════════════════════
AGENT_SYSTEM_PROMPT = """أنت مساعد ذكاء اصطناعي عربي ذكي ومبدع (Zitex Agent).

🎯 شخصيتك:
- تتحدث اللغة العربية بأسلوب سعودي طبيعي وحيوي (مو رسمي جاف)
- مبدع، ما تعطي نفس الإجابة مرتين، تقترح زوايا جديدة
- صادق — لو ما تعرف شي، تقول "ما أعرف" وتستخدم أدواتك
- عملي — تفكّر خطوة خطوة، تشرح رأيك، وتسأل لما تحتاج توضيح

🛠️ عندك أدوات حقيقية تقدر تستخدمها بحرية:
- `web_search(query)` — بحث حقيقي في الإنترنت (DuckDuckGo)
- `web_fetch(url)` — جلب محتوى أي صفحة فعلي
- `quran_reciter_lookup(name)` — 20 قارئ بأصوات mp3quran.net حقيقية
- `quran_verse_fetch(surah, ayah)` — نص أي آية من مصحف المدينة
- `saudi_official_sources(domain)` — 40+ مصدر سعودي معتمد
- `sports_team_lookup(team_name)` — لاعبين حقيقيين من TheSportsDB
- `generate_image_url(description)` — توليد صور AI (Nano Banana)

🔑 قواعد ذهبية:
1. **استخدم الأدوات بدل الاختراع**. لو المستخدم سأل عن قارئ، نادي رياضي، مؤسسة — استدعِ الأداة المناسبة.
2. **فكّر قبل ما تستدعي الأداة** — قل للمستخدم "راح أبحث عن كذا…" قبل الاستدعاء.
3. **اعرض نتائج الأدوات بتنسيق جميل** — استخدم markdown (جداول، قوائم، روابط).
4. **لا تبني مواقع HTML كاملة** — هذي مهمة صفحة /build-from-zero. أنت للتفكير والاستشارة والبحث.
5. **اقترح أفكار مختلفة** — لو المستخدم طلب تصميم، اقترح 3 زوايا مختلفة مو واحد.
6. **تعلم من المحادثة** — لو المستخدم قال "ما أبي X" تذكّرها في باقي المحادثة.

🎨 لما المستخدم يسأل عن أي موضوع سعودي:
- استدعِ `saudi_official_sources(domain)` أولاً
- ثم `web_search` لو احتجت أرقام أو تفاصيل حديثة
- قدّم المعلومات بتنسيق جذّاب مع روابط المصادر

💡 أمثلة على طريقة تفكيرك:
المستخدم: "أفكار لموقع قرآن للأطفال"
أنت: "فكرت في 3 زوايا مختلفة:
1. **لعبة تحفيظ** — الطفل يكمل الآية، يكسب نجوم (gamification)
2. **رحلة تفاعلية** — كل سورة = محطة في خريطة كرتونية
3. **تحدي العائلة** — الأب يتابع تقدم الأبناء، مكافآت حقيقية
أي واحدة تعجبك؟ أقدر أفصّل لك تفاصيل أكثر."
"""


# ════════════════════════════════════════════════════════════════════════
#  Router factory
# ════════════════════════════════════════════════════════════════════════
class ChatIn(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=4000)
    model: Optional[str] = "claude-sonnet-4-5"  # or "gpt-4o"


def create_agent_router(db, get_current_user):
    router = APIRouter(prefix="/api/agent", tags=["ai-agent"])

    @router.post("/chat")
    async def chat(payload: ChatIn, user=Depends(get_current_user)):
        """Stream a conversational response. Uses SSE-style chunks."""
        conv_id = payload.conversation_id or str(uuid.uuid4())
        conv = await db.agent_conversations.find_one(
            {"id": conv_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        messages: List[Dict[str, Any]]
        if conv:
            messages = conv.get("messages", [])
        else:
            messages = []

        # Add user message
        messages.append({
            "role": "user",
            "content": payload.message,
            "timestamp": _now(),
        })

        model_pick = (payload.model or "claude-sonnet-4-5").lower()

        async def stream_generator():
            try:
                from modules.freebuild_v2.tools import TOOL_SCHEMAS, execute_tool_call
                assistant_text = ""
                tool_events: List[Dict[str, Any]] = []

                if model_pick.startswith("claude"):
                    # Use emergentintegrations LlmChat with Claude + tools
                    async for evt in _claude_stream(messages, AGENT_SYSTEM_PROMPT):
                        if evt["type"] == "text":
                            assistant_text += evt["content"]
                            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                        elif evt["type"] == "tool":
                            tool_events.append(evt)
                            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                        elif evt["type"] == "done":
                            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                else:
                    # GPT-4o with tool-calling loop
                    async for evt in _gpt_stream(messages, AGENT_SYSTEM_PROMPT):
                        if evt["type"] == "text":
                            assistant_text += evt["content"]
                            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                        elif evt["type"] == "tool":
                            tool_events.append(evt)
                            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                        elif evt["type"] == "done":
                            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

                # Persist
                messages.append({
                    "role": "assistant",
                    "content": assistant_text,
                    "tool_events": tool_events,
                    "timestamp": _now(),
                    "model": model_pick,
                })
                await db.agent_conversations.update_one(
                    {"id": conv_id},
                    {"$set": {
                        "id": conv_id,
                        "user_id": user["user_id"],
                        "messages": messages,
                        "updated_at": _now(),
                    },
                    "$setOnInsert": {
                        "created_at": _now(),
                    }},
                    upsert=True,
                )
                yield f"data: {json.dumps({'type':'saved','conversation_id':conv_id})}\n\n"
            except Exception as e:
                logger.exception("[AGENT] chat stream failed")
                err = {"type": "error", "message": str(e)[:240]}
                yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @router.get("/conversations")
    async def list_conversations(user=Depends(get_current_user)):
        cur = db.agent_conversations.find(
            {"user_id": user["user_id"]},
            {"_id": 0, "id": 1, "messages": {"$slice": 1}, "updated_at": 1},
        ).sort("updated_at", -1).limit(50)
        out = []
        async for c in cur:
            first = (c.get("messages") or [{}])[0]
            preview = (first.get("content") or "")[:80]
            out.append({
                "id": c["id"],
                "preview": preview,
                "updated_at": c.get("updated_at"),
            })
        return {"conversations": out}

    @router.get("/conversation/{cid}")
    async def get_conversation(cid: str, user=Depends(get_current_user)):
        c = await db.agent_conversations.find_one(
            {"id": cid, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not c:
            raise HTTPException(404, "not found")
        return c

    @router.delete("/conversation/{cid}")
    async def delete_conversation(cid: str, user=Depends(get_current_user)):
        r = await db.agent_conversations.delete_one(
            {"id": cid, "user_id": user["user_id"]}
        )
        if r.deleted_count == 0:
            raise HTTPException(404, "not found")
        return {"ok": True}

    return router


# ════════════════════════════════════════════════════════════════════════
#  GPT-4o streaming with tool-calling loop
# ════════════════════════════════════════════════════════════════════════
async def _gpt_stream(messages: List[Dict[str, Any]], system: str):
    """Yields events: {type: 'text'|'tool'|'done', ...}"""
    from openai import AsyncOpenAI
    from modules.freebuild_v2.tools import TOOL_SCHEMAS, execute_tool_call

    key = os.environ.get("OPENAI_DIRECT_KEY")
    if not key:
        yield {"type": "error", "message": "OPENAI_DIRECT_KEY missing"}
        return
    client = AsyncOpenAI(api_key=key)
    local = [{"role": "system", "content": system}]
    for m in messages:
        if m["role"] in ("user", "assistant"):
            local.append({"role": m["role"], "content": m.get("content", "")})

    for iteration in range(8):
        resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=local,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.85,
        )
        msg = resp.choices[0].message
        if msg.tool_calls:
            local.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name,
                                  "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}
                yield {"type": "tool", "status": "calling",
                       "name": tc.function.name, "args": args}
                result = await execute_tool_call(tc.function.name, args)
                yield {"type": "tool", "status": "done",
                       "name": tc.function.name, "ok": result.get("ok"),
                       "summary": _tool_summary(tc.function.name, result)}
                local.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False)[:6000],
                })
            continue
        text = msg.content or ""
        # Stream the text in chunks
        chunk_size = 40
        for i in range(0, len(text), chunk_size):
            yield {"type": "text", "content": text[i:i+chunk_size]}
            await asyncio.sleep(0.02)
        yield {"type": "done"}
        return
    yield {"type": "text", "content": "\n(وصلت للحد الأقصى من استخدام الأدوات — أرجع لك بما عندي الآن)"}
    yield {"type": "done"}


# ════════════════════════════════════════════════════════════════════════
#  Claude streaming via emergentintegrations
# ════════════════════════════════════════════════════════════════════════
async def _claude_stream(messages: List[Dict[str, Any]], system: str):
    """Claude Sonnet 4.5 via emergentintegrations LlmChat.
    Note: current LlmChat doesn't expose native tool calling, so we
    do a simulated approach — the model returns JSON describing tool
    calls when it wants them. Keeps streaming via text chunks."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:
        yield {"type": "error", "message": f"emergentintegrations: {e}"}
        return
    from modules.freebuild_v2.tools import execute_tool_call, TOOL_SCHEMAS

    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        yield {"type": "error", "message": "EMERGENT_LLM_KEY missing"}
        return

    # Prepend tool-usage instructions to the system prompt
    tool_hint = (
        "\n\n🛠️ الأدوات المتاحة (تستدعيها بهذا الصيغة بالضبط عند الحاجة):\n"
        "لاستدعاء أداة، اكتب في ردك block خاص:\n"
        "```tool_call\n"
        "{\"name\":\"tool_name\",\"args\":{...}}\n"
        "```\n"
        "سأقوم بتنفيذها وأرجع لك النتيجة، ثم تكمل ردك.\n"
        "الأدوات: "
        + ", ".join(s["function"]["name"] for s in TOOL_SCHEMAS)
    )

    session_id = f"agent-{uuid.uuid4().hex[:12]}"
    conversation_history_text = ""
    for m in messages[:-1]:
        role = "المستخدم" if m["role"] == "user" else "أنت"
        conversation_history_text += f"\n\n{role}: {m.get('content','')[:1000]}"

    last_user = messages[-1].get("content", "")
    full_input = conversation_history_text + f"\n\nالمستخدم: {last_user}"

    chat = LlmChat(
        api_key=key,
        session_id=session_id,
        system_message=system + tool_hint,
    )
    chat.with_model("anthropic", "claude-sonnet-4-5")

    for iteration in range(6):
        try:
            response = await chat.send_message(UserMessage(text=full_input))
        except Exception as e:
            yield {"type": "error", "message": f"claude error: {str(e)[:200]}"}
            return

        text = str(response or "")
        # Parse tool_call blocks
        import re as _re
        tool_blocks = _re.findall(r"```tool_call\s*(\{[^`]+?\})\s*```", text)

        if tool_blocks:
            # Stream the text BEFORE the first tool_call block
            pre_text = text.split("```tool_call")[0].strip()
            if pre_text:
                for i in range(0, len(pre_text), 40):
                    yield {"type": "text", "content": pre_text[i:i+40]}
                    await asyncio.sleep(0.02)
            results = []
            for blob in tool_blocks:
                try:
                    parsed = json.loads(blob)
                    name = parsed.get("name", "")
                    args = parsed.get("args", {})
                except Exception:
                    continue
                yield {"type": "tool", "status": "calling", "name": name, "args": args}
                result = await execute_tool_call(name, args)
                yield {"type": "tool", "status": "done", "name": name,
                       "ok": result.get("ok"),
                       "summary": _tool_summary(name, result)}
                results.append({"name": name, "result": result})

            # Feed results back and continue
            results_text = "\n\nنتائج الأدوات:\n"
            for r in results:
                trimmed = json.dumps(r["result"], ensure_ascii=False)[:3000]
                results_text += f"• {r['name']}: {trimmed}\n"
            full_input = results_text + "\n\nأكمل ردك للمستخدم بناءً على هذه النتائج (بدون tool_call جديد إلا لو ضروري جداً)."
            continue

        # No tool calls → stream text and done
        for i in range(0, len(text), 40):
            yield {"type": "text", "content": text[i:i+40]}
            await asyncio.sleep(0.02)
        yield {"type": "done"}
        return

    yield {"type": "text", "content": "\n(انتهى حد الاستدعاءات — أرجع لك بالنتائج الحالية)"}
    yield {"type": "done"}


def _tool_summary(name: str, result: Dict[str, Any]) -> str:
    """Short human-readable summary for streaming to UI."""
    if not result.get("ok", True):
        return f"فشل: {result.get('error','')}"
    if name == "web_search":
        return f"وجدت {result.get('count', 0)} نتيجة"
    if name == "web_fetch":
        return f"جلبت: {(result.get('title') or '')[:60]}"
    if name == "quran_reciter_lookup":
        c = result.get("count", 0)
        return f"{c} قارئ"
    if name == "quran_verse_fetch":
        return f"آية {result.get('surah')}:{result.get('ayah')}"
    if name == "saudi_official_sources":
        n = len(result.get("sources", []))
        return f"{n} مصدر سعودي ({result.get('category')})"
    if name == "sports_team_lookup":
        t = result.get("team", {})
        return f"{t.get('name','')} ({result.get('players_count',0)} لاعب)"
    if name == "generate_image_url":
        return "تم توليد الصورة"
    return "تم"
