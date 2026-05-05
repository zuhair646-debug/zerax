"""
Zitex AI Agent — open thinking agent with full tool suite.

This is THE single AI brain for Zitex. It thinks, listens, and executes.
It can:
    • Build complete websites (build_website / update_website)
    • Search the web, fetch pages
    • Lookup Quran reciters and verse text
    • Lookup Saudi official sources
    • Lookup real sports teams + players
    • Generate AI images (Nano Banana)
    • Generate ambient music / sound (ElevenLabs)
    • Spawn specialist sub-agents (designer, researcher, copywriter)

Endpoints:
    POST   /api/agent/chat                      — stream a turn (SSE)
    GET    /api/agent/conversations             — list user conversations
    GET    /api/agent/conversation/{id}         — full transcript + current_html
    DELETE /api/agent/conversation/{id}
    GET    /api/agent/conversation/{id}/preview — serves current_html as text/html
    GET    /api/agent/audio/{filename}          — serves generated MP3
"""
from __future__ import annotations
import os
import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse, Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ════════════════════════════════════════════════════════════════════════
#  System prompt — open, conversational, tool-using
# ════════════════════════════════════════════════════════════════════════
AGENT_SYSTEM_PROMPT = """أنت ذكاء Zitex — عقل واحد متكامل قادر يفكّر ويبني وينفّذ.

🎯 شخصيتك (ثابتة، لا تتغيّر):
- تتحدث عربية سعودية طبيعية واضحة (مو رسمي جاف).
- مفكّر، تشرح خطواتك بوضوح.
- صريح: لو ما تعرف شي → استدعِ أداة، لا تخترع.
- حازم: لا تكرّر "عفواً/آسف" — نفّذ.
- فضولي مبدع: كل تصميم/فكرة جديدة، لا تكرّر اللي قبله.

🛠️ أدواتك الكاملة (استخدمها بحرية):
1. **`build_quran_mushaf_reader(surah?, style?)` — 🕌 استخدمها لأي طلب قرآن/مصحف/تلاوة/تحفيظ. تبني موقع متكامل بقارئ مصحف مدمج (نص حقيقي + 14 قارئ + اضغط أي آية تشتغل بصوت القارئ المختار). ممنوع تستخدم build_website للقرآن.**
2. `build_website(brief, style_direction?)` — يبني موقع SPA كامل HTML من الصفر للمواقع غير القرآن.
3. `edit_section(target, instructions)` — **تعديل جراحي لقسم واحد** (hero, menu, contact, pricing...). أسرع وأدق من update_website.
4. `add_page(label, slug?, brief?)` — يضيف صفحة جديدة + رابط في القائمة. سريع (~15ث).
5. `set_theme(palette?, fonts?, mood?)` — يغيّر الـCSS theme فقط (ألوان/خطوط) بدون لمس HTML. سريع جداً (~7ث).
6. `update_website(instructions)` — **آخر خيار** للتعديلات العامة جداً.
7. `web_search(query)` — بحث حقيقي DuckDuckGo.
8. `web_fetch(url)` — جلب محتوى صفحة فعلي.
9. `quran_reciter_lookup(name)` — 20 قارئ من mp3quran.net (للسور الكاملة فقط).
10. `quran_verse_fetch(surah, ayah)` — نص آية بالضبط من مصحف المدينة.
11. `saudi_official_sources(domain)` — مصادر سعودية معتمدة.
12. `sports_team_lookup(team_name)` — لاعبين حقيقيين من TheSportsDB.
13. `generate_image_url(description)` — صور AI (Nano Banana). **استخدمها بحذر** — تجنبها للمواقع الدينية تماماً.
14. `generate_audio(description, duration_seconds)` — موسيقى/صوت محيطي (ElevenLabs).

🔑 قواعد العمل (صارمة):
1. **اسمع العميل بالحرف**. لو قال "أبي موقع تحفيظ قرآن" → ابني تحفيظ قرآن. لا تقترح "ليش ما نسوي مطعم؟".
2. **فكّر قبل ما تنفّذ**. اكتب بضع أسطر تشرح خطتك (3-5 خطوات قصيرة) ثم استدعِ الأدوات.
3. **استخدم الأدوات الحقيقية**. ممنوع تخترع أرقام/أسماء قراء/لاعبين/مصادر — استدعِ الأداة.
4. **🕌 طلب قرآن/مصحف/تلاوة/تحفيظ → `build_quran_mushaf_reader` فوراً**. ممنوع build_website لهذه الطلبات. الموقع المُولّد فيه القرآن الكامل مكتوب من المصحف الرسمي + 14 قارئ + اضغط أي آية تشتغل بصوت القارئ. هذا هو المنتج الذي يبحث عنه العميل.
5. **بناء موقع غير ديني = `build_website`**. الأداة تتولّى التوليد + تركيب الصور.
6. **التعديل = اختر الأداة الجراحية الصح**:
   - "غيّر الألوان / الخط / المزاج" → `set_theme` (سريع جداً)
   - "أضف صفحة / قسم جديد كامل" → `add_page`
   - "غيّر نص الـhero / عدّل المنيو / أضف form للتواصل" → `edit_section(target, instructions)`
   - **ممنوع** تستدعي `build_website` من جديد لتعديل بسيط (يخسر العمل السابق + بطيء).
   - **ممنوع** تستخدم `update_website` إلا كآخر حل لطلب عام جداً.
7. **التنوّع**. لو العميل بنى عندك موقعين بنفس الجلسة، الثاني يكون شكل/لون/layout مختلف 100%.
8. **ممنوع التكرار**. ممنوع تردّ بنفس البنية كل مرّة. لا تستخدم "بسم الله، تشرّفت" في كل ردّ.
9. **ممنوع الاعتذار**. لو شي ما اشتغل، حلّه أو اقترح بديل — لا تقول "عفواً".

🎨 لما العميل يطلب موقع:
- اطرح سؤال واحد ذكي محدّد لو شي غير واضح، وإلا ابدأ مباشرة.
- استدعِ الأدوات الموثّقة (saudi_official_sources, sports_team_lookup, quran_*) قبل build_website لو السياق يحتاج بيانات حقيقية.
- ثم استدعِ `build_website` بـbrief عربي تفصيلي (300+ حرف) يصف الجمهور، الشعور، الأقسام المطلوبة، النصوص الموجزة، اقتراح palette.
- بعد البناء، اعرض على العميل: "✅ بنيت لك الموقع. شف المعاينة على اليمين. تبيني أعدّل شي؟"

🎵 لما العميل يطلب موسيقى/صوت:
- استدعِ `generate_audio` بوصف إنجليزي دقيق (e.g. "calm Arabic-flavored ambient music with soft oud and ney").
- ارجع له الرابط: "هذا الصوت 🎵 [رابط]".

💡 أمثلة على تفكيرك:
العميل: "أبي موقع لمطعم سعودي تراثي اسمه 'بيت الجد'"
أنت: "تمام، بفكر معك:
1. الفكرة: مطعم سعودي تراثي → palette ترابي/ذهبي + خط ديواني + صور تراث.
2. الأقسام: hero مع شعار، عن الجد، المنيو (مأكولات شعبية)، الفروع، احجز طاولة، تواصل.
3. اللغة: نبرة دافئة عائلية.
الحين أبنيها لك..."
[يستدعي build_website ببrief طويل تفصيلي]

📏 طول الردّ النصي قبل/بعد الأدوات: قصير وعملي (3-8 أسطر). الذكاء في الأدوات والمخرجات، مو في الكلام الكثير."""


# ════════════════════════════════════════════════════════════════════════
#  Router factory
# ════════════════════════════════════════════════════════════════════════
class ChatIn(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=4000)
    model: Optional[str] = "gpt-4o"  # gpt-4o or claude-sonnet-4-5


_AUDIO_DIR = Path("/app/backend/static/agent_audio")
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


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
        current_html: str = ""
        if conv:
            messages = conv.get("messages", [])
            current_html = conv.get("current_html", "")
        else:
            messages = []

        # Add user message
        messages.append({
            "role": "user",
            "content": payload.message,
            "timestamp": _now(),
        })

        model_pick = (payload.model or "gpt-4o").lower()

        async def stream_generator():
            nonlocal current_html
            try:
                assistant_text = ""
                tool_events: List[Dict[str, Any]] = []
                new_html = current_html

                # Single agent loop: GPT-4o with tools (Claude path uses different mechanism)
                if model_pick.startswith("claude"):
                    gen = _claude_stream(messages, AGENT_SYSTEM_PROMPT, current_html)
                else:
                    gen = _gpt_stream(messages, AGENT_SYSTEM_PROMPT, current_html)

                async for evt in gen:
                    if evt["type"] == "text":
                        assistant_text += evt["content"]
                    elif evt["type"] == "tool":
                        tool_events.append(evt)
                        # Capture HTML output from website-building tools
                        if (
                            evt.get("status") == "done"
                            and evt.get("name") in ("build_website", "update_website", "edit_section", "add_page", "set_theme", "build_quran_mushaf_reader")
                            and isinstance(evt.get("html"), str)
                            and len(evt["html"]) > 200
                        ):
                            new_html = evt["html"]
                            # Notify frontend so it refreshes preview
                            yield f"data: {json.dumps({'type':'html','length':len(new_html)})}\n\n"
                    yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

                # Persist
                messages.append({
                    "role": "assistant",
                    "content": assistant_text,
                    "tool_events": [
                        # strip large html payloads from stored events
                        {k: v for k, v in e.items() if k != "html"}
                        for e in tool_events
                    ],
                    "timestamp": _now(),
                    "model": model_pick,
                })
                update_doc: Dict[str, Any] = {
                    "id": conv_id,
                    "user_id": user["user_id"],
                    "messages": messages,
                    "updated_at": _now(),
                }
                if new_html and new_html != current_html:
                    update_doc["current_html"] = new_html
                await db.agent_conversations.update_one(
                    {"id": conv_id},
                    {"$set": update_doc, "$setOnInsert": {"created_at": _now()}},
                    upsert=True,
                )
                yield f"data: {json.dumps({'type':'saved','conversation_id':conv_id,'has_html': bool(new_html)})}\n\n"
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
            {"_id": 0, "id": 1, "messages": {"$slice": 1}, "updated_at": 1, "current_html": 1},
        ).sort("updated_at", -1).limit(50)
        out = []
        async for c in cur:
            first = (c.get("messages") or [{}])[0]
            preview = (first.get("content") or "")[:80]
            out.append({
                "id": c["id"],
                "preview": preview,
                "updated_at": c.get("updated_at"),
                "has_html": bool(c.get("current_html")),
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

    @router.get("/conversation/{cid}/preview", response_class=HTMLResponse)
    async def preview_html(cid: str):
        """Public-ish preview (no auth — uses cid as random token)."""
        c = await db.agent_conversations.find_one({"id": cid}, {"_id": 0, "current_html": 1})
        if not c or not c.get("current_html"):
            return HTMLResponse(_empty_preview_html(), status_code=200)
        return HTMLResponse(c["current_html"], status_code=200)

    @router.get("/audio/{filename}")
    async def serve_audio(filename: str):
        if "/" in filename or ".." in filename:
            raise HTTPException(400, "invalid filename")
        fp = _AUDIO_DIR / filename
        if not fp.exists():
            raise HTTPException(404, "not found")
        return FileResponse(str(fp), media_type="audio/mpeg")

    return router


def _empty_preview_html() -> str:
    return """<!doctype html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<title>معاينة Zitex</title>
<style>
body{margin:0;background:#0a0a12;color:#fff;font-family:'Tajawal',system-ui;display:grid;place-items:center;min-height:100vh;text-align:center}
.empty{padding:40px;border-radius:24px;background:rgba(255,255,255,.04);border:1px solid rgba(245,158,11,.2)}
h2{color:#fbbf24;font-weight:900}
p{color:rgba(255,255,255,.5);font-size:14px;line-height:1.8}
</style></head><body>
<div class="empty">
<h2>المعاينة جاهزة</h2>
<p>اطلب من الذكاء يبني لك موقع<br>وستظهر هنا فوراً ✨</p>
</div></body></html>"""


# ════════════════════════════════════════════════════════════════════════
#  GPT-4o streaming with tool-calling loop (with current_html injection)
# ════════════════════════════════════════════════════════════════════════
async def _gpt_stream(
    messages: List[Dict[str, Any]],
    system: str,
    current_html: str,
):
    """Yields events: {type: 'text'|'tool'|'done', ...}"""
    from openai import AsyncOpenAI
    from modules.freebuild_v2.tools import TOOL_SCHEMAS, execute_tool_call

    key = os.environ.get("OPENAI_DIRECT_KEY")
    if not key:
        yield {"type": "error", "message": "OPENAI_DIRECT_KEY missing"}
        return
    client = AsyncOpenAI(api_key=key)
    local: List[Dict[str, Any]] = [{"role": "system", "content": system}]
    if current_html:
        local.append({
            "role": "system",
            "content": (
                f"📐 السياق: العميل يملك حالياً موقع HTML قائم بحجم {len(current_html)} حرف. "
                "أي طلب تعديل → استدعِ update_website. ممنوع تستخدم build_website من الصفر إلا "
                "لو طلب صريح بـ'ابدأ من جديد' أو 'موقع جديد'."
            ),
        })
    for m in messages:
        if m["role"] in ("user", "assistant"):
            local.append({"role": m["role"], "content": m.get("content", "") or ""})

    for iteration in range(8):
        try:
            resp = await client.chat.completions.create(
                model="gpt-4o",
                messages=local,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=0.85,
            )
        except Exception as e:
            yield {"type": "error", "message": f"openai: {str(e)[:200]}"}
            return
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
                # Auto-inject current_html for surgical website tools
                if tc.function.name in ("update_website", "edit_section", "add_page", "set_theme"):
                    args["current_html"] = current_html
                yield {"type": "tool", "status": "calling",
                       "name": tc.function.name,
                       "args": {k: v for k, v in args.items() if k != "current_html"}}
                result = await execute_tool_call(tc.function.name, args)
                # Update current_html if a website-building tool succeeded
                evt = {"type": "tool", "status": "done",
                       "name": tc.function.name, "ok": result.get("ok"),
                       "summary": _tool_summary(tc.function.name, result)}
                if (
                    tc.function.name in ("build_website", "update_website", "edit_section", "add_page", "set_theme", "build_quran_mushaf_reader")
                    and result.get("ok")
                    and isinstance(result.get("html"), str)
                ):
                    current_html = result["html"]
                    evt["html"] = current_html  # captured by outer stream_generator
                if tc.function.name == "generate_audio" and result.get("ok"):
                    evt["url"] = result.get("url")
                if tc.function.name == "generate_image_url" and result.get("ok"):
                    evt["url"] = result.get("url")
                yield evt
                # Feed tool result back — but trim HTML payload from the conversation
                tool_payload = {k: v for k, v in result.items() if k != "html"}
                if "html" in result:
                    tool_payload["html_size"] = len(result["html"])
                local.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_payload, ensure_ascii=False)[:6000],
                })
            continue
        text = msg.content or ""
        # Stream the text in chunks
        chunk_size = 40
        for i in range(0, len(text), chunk_size):
            yield {"type": "text", "content": text[i:i+chunk_size]}
            await asyncio.sleep(0.015)
        yield {"type": "done"}
        return
    yield {"type": "text", "content": "\n(وصلت للحد الأقصى من استخدام الأدوات — أرجع لك بما عندي الآن)"}
    yield {"type": "done"}


# ════════════════════════════════════════════════════════════════════════
#  Claude streaming via emergentintegrations (simulated tool-calling)
# ════════════════════════════════════════════════════════════════════════
async def _claude_stream(
    messages: List[Dict[str, Any]],
    system: str,
    current_html: str,
):
    """Claude path: parses tool_call blocks from text. Less reliable than GPT-4o
    for tool use, so we recommend GPT-4o for website building."""
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

    tool_hint = (
        "\n\n🛠️ الأدوات المتاحة. لاستدعاء أداة، اكتب block بهذا الشكل بالضبط:\n"
        "```tool_call\n"
        "{\"name\":\"tool_name\",\"args\":{...}}\n"
        "```\n"
        "سأنفّذها وأرجع لك النتيجة، ثم تكمل ردّك.\n"
        "الأدوات: " + ", ".join(s["function"]["name"] for s in TOOL_SCHEMAS)
    )
    if current_html:
        tool_hint += f"\n\n📐 يوجد موقع حالي ({len(current_html)} حرف). أي تعديل استخدم update_website."

    session_id = f"agent-{uuid.uuid4().hex[:12]}"
    history_text = ""
    for m in messages[:-1]:
        role = "المستخدم" if m["role"] == "user" else "أنت"
        history_text += f"\n\n{role}: {m.get('content','')[:1000]}"

    last_user = messages[-1].get("content", "")
    full_input = history_text + f"\n\nالمستخدم: {last_user}"

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
        import re as _re
        tool_blocks = _re.findall(r"```tool_call\s*(\{[^`]+?\})\s*```", text)

        if tool_blocks:
            pre_text = text.split("```tool_call")[0].strip()
            if pre_text:
                for i in range(0, len(pre_text), 40):
                    yield {"type": "text", "content": pre_text[i:i+40]}
                    await asyncio.sleep(0.015)
            results = []
            for blob in tool_blocks:
                try:
                    parsed = json.loads(blob)
                    name = parsed.get("name", "")
                    args = parsed.get("args", {})
                except Exception:
                    continue
                if name in ("update_website", "edit_section", "add_page", "set_theme"):
                    args["current_html"] = current_html
                yield {"type": "tool", "status": "calling", "name": name,
                       "args": {k: v for k, v in args.items() if k != "current_html"}}
                result = await execute_tool_call(name, args)
                evt = {"type": "tool", "status": "done", "name": name,
                       "ok": result.get("ok"),
                       "summary": _tool_summary(name, result)}
                if name in ("build_website", "update_website", "edit_section", "add_page", "set_theme", "build_quran_mushaf_reader") and result.get("ok") and result.get("html"):
                    current_html = result["html"]
                    evt["html"] = current_html
                if name in ("generate_audio", "generate_image_url") and result.get("ok"):
                    evt["url"] = result.get("url")
                yield evt
                trimmed = {k: v for k, v in result.items() if k != "html"}
                if "html" in result:
                    trimmed["html_size"] = len(result["html"])
                results.append({"name": name, "result": trimmed})

            results_text = "\n\nنتائج الأدوات:\n"
            for r in results:
                trimmed = json.dumps(r["result"], ensure_ascii=False)[:3000]
                results_text += f"• {r['name']}: {trimmed}\n"
            full_input = results_text + "\n\nأكمل ردّك للمستخدم بناءً على النتائج (بدون tool_call جديد إلا لو ضروري)."
            continue

        for i in range(0, len(text), 40):
            yield {"type": "text", "content": text[i:i+40]}
            await asyncio.sleep(0.015)
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
        return f"{result.get('count', 0)} قارئ"
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
    if name == "generate_audio":
        return result.get("summary", "تم توليد الصوت")
    if name == "build_website":
        return result.get("summary", "تم بناء الموقع")
    if name == "update_website":
        return result.get("summary", "تم تحديث الموقع")
    if name == "set_theme":
        return result.get("summary", "تم تحديث الـtheme")
    if name == "add_page":
        return result.get("summary", "تم إضافة الصفحة")
    if name == "edit_section":
        return result.get("summary", "تم تعديل القسم")
    if name == "build_quran_mushaf_reader":
        return result.get("summary", "تم بناء قارئ المصحف")
    return "تم"
