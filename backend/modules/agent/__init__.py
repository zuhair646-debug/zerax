"""
Zerax AI Agent — open thinking agent with full tool suite.

This is THE single AI brain for Zerax. It thinks, listens, and executes.
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
import re
import json
import uuid
import asyncio
import logging
import base64
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse, Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ════════════════════════════════════════════════════════════════════════
#  System prompt — open, conversational, tool-using
# ════════════════════════════════════════════════════════════════════════
AGENT_SYSTEM_PROMPT = """أنت ذكاء Zerax — عقل واحد متكامل قادر يفكّر ويبني وينفّذ.

🎯 شخصيتك (ثابتة، لا تتغيّر):
- تتحدث عربية سعودية طبيعية واضحة (مو رسمي جاف).
- مفكّر، تشرح خطواتك بوضوح.
- صريح: لو ما تعرف شي → استدعِ أداة، لا تخترع.
- حازم: لا تكرّر "عفواً/آسف" — نفّذ.
- فضولي مبدع: كل تصميم/فكرة جديدة، لا تكرّر اللي قبله.

🛠️ أدواتك (إجمالي 19 أداة — استخدم الأنسب):

📦 **خط البناء (workflow)** — للمواقع الجديدة، استدعِ بالترتيب:
  1. `analyze_intent(brief)` — 🧠 Planner: يحلّل الطلب ويرجع خطة JSON
  2. `web_search` / `quran_*` / `sports_*` / `saudi_official_sources` — 🔎 Researcher: حسب data_sources في الخطة
  3. `pick_design(brief, research_summary)` — 🎨 Designer: يختار palette + typography + layout
  4. **البناء الرئيسي** — اختر بحرية:
     - 🕌 **قرآن بسيط** (مصحف فقط بدون أقسام إضافية): `build_quran_mushaf_reader(surah, style)` — قالب جاهز سريع
     - 🎮 **قرآن إبداعي** (gaming/achievements/dashboard/أي تصميم خاص): استخدم `build_creative_quran_site(brief, surah)` — يضمن 100% أن الآيات الحقيقية + 14 قارئ + audio يظهرون داخل تصميمك (deterministic injection، لا يعتمد على LLM trust). **هذي الأداة الأمثل لأي طلب قرآن مع تصميم خاص.**
     - 🩹 **إصلاح موقع موجود**: لو فيه موقع وقسم القرآن مكسور، استخدم `inject_quran_blocks(surah, target_selector?)` — يصلح القسم فوراً.
     - 🛠️ **بقية المواقع**: `build_website(brief, style_direction)` مباشرة.
  5. `qa_html()` — 🧪 QA: يفحص الجودة بعد البناء (يرجع score 0-100)
  6. `publish_site(slug?, title?)` — 🚀 Deployer: لما العميل يقول "انشره"

✏️ **التعديل الجراحي**:
  - `set_theme(palette?, fonts?, mood?)` — تغيير الـtheme فقط (~7ث)
  - `add_page(label, slug?, brief?)` — إضافة صفحة + nav link (~15ث)
  - `edit_section(target, instructions)` — تعديل قسم محدد (~10ث)
  - `update_website(instructions)` — آخر خيار، فقط للتعديلات العامة جداً

📊 **الأدوات المساندة**:
  - `web_search(query)`، `web_fetch(url)` — بحث وجلب من الإنترنت
  - `quran_reciter_lookup`, `quran_verse_fetch` — قراء + آيات
  - `saudi_official_sources(domain)` — مصادر سعودية معتمدة
  - `sports_team_lookup(team_name)` — لاعبين حقيقيين
  - `geo_lookup(ip?)` — معلومات جغرافية (دولة/عملة)
  - `generate_image_url(description)` — صور AI (تجنبها للمواقع الدينية)
  - `generate_audio(description, duration_seconds)` — موسيقى/صوت محيطي

🔓 **صلاحياتك الكاملة (مفتوحة بالكامل)**:
- لك حرية مطلقة في اختيار الأدوات وترتيبها وتركيبها.
- بإمكانك استدعاء نفس الأداة مرات متعددة، وأي عدد من الأدوات في نفس المحادثة (حتى 30 استدعاء).
- بإمكانك التفكير بصوت عالٍ، تشرح خطواتك، تقترح بدائل.
- لا قيود على نوع المواقع/المجالات. لو طلب العميل قرآن كريم، رياضة، تجارة، صحة، تعليم، دين، أو أي شيء — نفّذ.
- أي شي فيه شك أو غير واضح → ابحث عبر web_search/web_fetch، أو اسأل العميل سؤال محدد، لكن لا ترفض الطلب.
- ممنوع تقول "ما يمكنني" أو "غير مسموح" — أنت مفتوح بالكامل.

🔑 قواعد العمل (صارمة):
1. **اسمع العميل بالحرف**. لو قال "أبي موقع تحفيظ قرآن" → ابني تحفيظ قرآن. لا تقترح "ليش ما نسوي مطعم؟".
2. **فكّر قبل ما تنفّذ**. اكتب بضع أسطر تشرح خطتك (3-5 خطوات قصيرة) ثم استدعِ الأدوات.
3. **استخدم الأدوات الحقيقية**. ممنوع تخترع أرقام/أسماء قراء/لاعبين/مصادر — استدعِ الأداة.
4. **🕌 طلب قرآن/مصحف/تلاوة/تحفيظ**: إذا الطلب بسيط (مصحف فقط) → `build_quran_mushaf_reader`. إذا الطلب إبداعي/معقد (gaming، achievements، dashboards، أقسام إضافية، تصاميم خاصة) → `fetch_quran_blocks(surah)` أولاً، ثم `build_website(brief)` مع التعليمات التفصيلية لزرع الكتل. **النتيجة: قرآن حقيقي + تصميم إبداعي 100%، مدمج في موقع واحد.**
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
10. **ترتيب workflow صارم**: لازم تبني الموقع أولاً، ثم تنشر. ممنوع تستدعي `publish_site` قبل ما يكون فيه `build_*` ناجح. لو العميل قال "ابني وانشر" → خطوتك:
    أولاً analyze_intent → ثم build_quran_mushaf_reader أو build_website (يحدث current_html) → ثم qa_html → ثم publish_site.
11. **بعد النشر**: اعرض الرابط بوضوح للعميل بهذا الشكل: "🚀 موقعك مباشر على: <رابط>"

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
    message: str = Field(..., min_length=1, max_length=32000)
    model: Optional[str] = "gpt-4o"  # gpt-4o or claude-sonnet-4-5


_AUDIO_DIR = Path("/app/backend/static/agent_audio")
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def create_agent_router(db, get_current_user):
    router = APIRouter(prefix="/api/agent", tags=["ai-agent"])

    @router.post("/chat")
    async def chat(
        message: str = Form(...),
        model: str = Form("gpt-4o"),
        conversation_id: Optional[str] = Form(None),
        files: List[UploadFile] = File(default=[]),
        user=Depends(get_current_user)
    ):
        """Stream a conversational response. Uses SSE-style chunks."""
        conv_id = conversation_id or str(uuid.uuid4())
        conv = await db.agent_conversations.find_one(
            {"id": conv_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        messages_list: List[Dict[str, Any]]
        current_html: str = ""
        if conv:
            messages_list = conv.get("messages", [])
            current_html = conv.get("current_html", "")
        else:
            messages_list = []

        # Process attachments. Keep public URLs for the UI/history, and keep compact
        # base64 data URLs for the current turn so GPT-4o can actually see images.
        attachment_urls: List[str] = []
        attachment_image_parts: List[Dict[str, Any]] = []
        if files:
            upload_dir = Path("/app/backend/static/agent_uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            for f in files:
                if f.filename:
                    safe_original = Path(f.filename).name.replace("/", "_").replace("\\", "_")
                    fname = f"{uuid.uuid4().hex[:12]}_{safe_original}"
                    fpath = upload_dir / fname
                    content = await f.read()
                    fpath.write_bytes(content)
                    public_url = f"/backend-static/agent_uploads/{fname}"
                    attachment_urls.append(public_url)

                    content_type = (f.content_type or mimetypes.guess_type(safe_original)[0] or "").lower()
                    if content_type.startswith("image/") and content:
                        # Avoid sending huge uploads to the vision model. UI still keeps the file.
                        if len(content) <= 8 * 1024 * 1024:
                            data_url = f"data:{content_type};base64,{base64.b64encode(content).decode('ascii')}"
                            attachment_image_parts.append({
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            })
                        else:
                            logger.warning("Skipping oversized image attachment for vision: %s bytes", len(content))

        # Add user message
        user_msg = {"role": "user", "content": message, "timestamp": _now()}
        if attachment_urls:
            user_msg["attachments"] = attachment_urls
            if attachment_image_parts:
                user_msg["vision_images"] = attachment_image_parts
        messages_list.append(user_msg)

        model_pick = (model or "gpt-4o").lower()
        # Claude path currently receives text-only history. If the user attached images,
        # force the vision-capable GPT-4o path so the assistant can actually inspect them.
        if attachment_image_parts and model_pick.startswith("claude"):
            logger.info("[AGENT] switching image turn from %s to gpt-4o vision", model_pick)
            model_pick = "gpt-4o"

        async def stream_generator():
            nonlocal current_html
            try:
                assistant_text = ""
                tool_events: List[Dict[str, Any]] = []
                new_html = current_html

                # Single agent loop: GPT-4o with tools (Claude path uses different mechanism)
                if model_pick.startswith("claude"):
                    gen = _claude_stream(messages_list, AGENT_SYSTEM_PROMPT, current_html)
                else:
                    gen = _gpt_stream(messages_list, AGENT_SYSTEM_PROMPT, current_html)

                async for evt in gen:
                    if evt["type"] == "text":
                        assistant_text += evt["content"]
                    elif evt["type"] == "tool":
                        tool_events.append(evt)
                        # Capture HTML output from website-building tools
                        if (
                            evt.get("status") == "done"
                            and evt.get("name") in ("build_website", "update_website", "edit_section", "add_page", "set_theme", "build_quran_mushaf_reader", "build_creative_quran_site", "build_quran_website", "inject_quran_blocks")
                            and isinstance(evt.get("html"), str)
                            and len(evt["html"]) > 200
                        ):
                            new_html = evt["html"]
                            # Notify frontend so it refreshes preview
                            yield f"data: {json.dumps({'type':'html','length':len(new_html)})}\n\n"
                        # Handle publish_site: persist current HTML under public slug
                        if (
                            evt.get("status") == "done"
                            and evt.get("name") == "publish_site"
                            and evt.get("_publish_request")
                            and new_html
                            and len(new_html) > 200
                        ):
                            slug = evt.get("slug") or uuid.uuid4().hex[:10]
                            await db.public_agent_sites.update_one(
                                {"slug": slug},
                                {"$set": {
                                    "slug": slug,
                                    "title": evt.get("title") or "موقع زيتكس",
                                    "html": new_html,
                                    "owner_id": user["user_id"],
                                    "updated_at": _now(),
                                }, "$setOnInsert": {"created_at": _now()}},
                                upsert=True,
                            )
                            evt["url"] = f"/api/p/{slug}"
                            evt["summary"] = f"✅ نُشر على /api/p/{slug}"
                    yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

                # Persist
                messages_list.append({
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
                persisted_messages = [
                    {k: v for k, v in msg.items() if k != "vision_images"}
                    for msg in messages_list
                ]
                update_doc: Dict[str, Any] = {
                    "id": conv_id,
                    "user_id": user["user_id"],
                    "messages": persisted_messages,
                    "updated_at": _now(),
                }
                if new_html and new_html != current_html:
                    update_doc["current_html"] = new_html
                await db.agent_conversations.update_one(
                    {"id": conv_id},
                    {"$set": update_doc, "$setOnInsert": {"created_at": _now()}},
                    upsert=True,
                )
                saved_evt = {
                    "type": "saved",
                    "conversation_id": conv_id,
                    "has_html": bool(new_html),
                    "attachments": attachment_urls,
                }
                yield f"data: {json.dumps(saved_evt, ensure_ascii=False)}\n\n"
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
        ).sort("updated_at", -1).limit(200)
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

    @router.get("/primitives/quran.js")
    async def serve_quran_primitives():
        """Static JS exposing ZeraxQuran data primitives (reciters, surahs, fetchSurah, audioUrl)."""
        fp = Path("/app/backend/static/zerax_primitives_quran.js")
        if not fp.exists():
            raise HTTPException(404, "primitives not found")
        return FileResponse(str(fp), media_type="application/javascript")

    return router


def create_public_agent_router(db) -> APIRouter:
    """Public router for serving published agent sites at /api/p/{slug}."""
    router = APIRouter(prefix="/api", tags=["agent-public"])
    
    @router.get("/p/{slug}", response_class=HTMLResponse)
    async def serve_published(slug: str):
        slug = re.sub(r"[^a-z0-9-]", "", slug.lower())[:40]
        if not slug:
            raise HTTPException(404, "not found")
        site = await db.public_agent_sites.find_one({"slug": slug}, {"_id": 0, "html": 1, "title": 1})
        if not site or not site.get("html"):
            return HTMLResponse(_empty_preview_html(), status_code=404)
        return HTMLResponse(site["html"], status_code=200)
    
    return router


def _empty_preview_html() -> str:
    return """<!doctype html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
<title>معاينة Zerax</title>
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
            text = m.get("content", "") or ""
            if m["role"] == "user" and m.get("vision_images"):
                content_parts: List[Dict[str, Any]] = [
                    {
                        "type": "text",
                        "text": (
                            f"{text}\n\n"
                            "[المستخدم أرفق صورة/صور في هذه الرسالة. حلّل الصورة بصرياً بدقة "
                            "وأجب على محتواها مباشرة، ولا تكتفِ بذكر اسم الموقع أو وجود مرفق.]"
                        ),
                    }
                ]
                content_parts.extend(m.get("vision_images", [])[:4])
                local.append({"role": "user", "content": content_parts})
            else:
                local.append({"role": m["role"], "content": text})

    for iteration in range(30):
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
                # Auto-inject current_html for surgical website tools + qa_html + publish_site + inject_quran_blocks
                if tc.function.name in ("update_website", "edit_section", "add_page", "set_theme", "qa_html", "publish_site", "inject_quran_blocks"):
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
                    tc.function.name in ("build_website", "update_website", "edit_section", "add_page", "set_theme", "build_quran_mushaf_reader", "build_creative_quran_site", "build_quran_website", "inject_quran_blocks")
                    and result.get("ok")
                    and isinstance(result.get("html"), str)
                ):
                    current_html = result["html"]
                    evt["html"] = current_html  # captured by outer stream_generator
                # Mark publish_site events for outer handler to persist
                if (
                    tc.function.name == "publish_site"
                    and result.get("ok")
                    and result.get("_publish_request")
                ):
                    evt["_publish_request"] = True
                    evt["slug"] = result.get("slug")
                    evt["title"] = result.get("title")
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
                    "content": json.dumps(tool_payload, ensure_ascii=False)[:32000],
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
    yield {"type": "text", "content": "\n(وصلت لـ30 استدعاء أداة في هذا الدور — أكمّل بما لديّ الآن، ولو احتجت أكثر اطلب مني تكملة)"}
    yield {"type": "done"}


# ════════════════════════════════════════════════════════════════════════
# Claude streaming via DIRECT Anthropic SDK (preferred — uses user's own
# ANTHROPIC_API_KEY) with emergentintegrations as fallback
# ════════════════════════════════════════════════════════════════════════
async def _claude_stream(
    messages: List[Dict[str, Any]],
    system: str,
    current_html: str,
):
    """Claude path. Tries direct Anthropic SDK first (uses owner's
    ANTHROPIC_API_KEY — no Emergent points consumed). Falls back to
    emergentintegrations only if the direct key is missing."""
    direct_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if direct_key.startswith("sk-ant"):
        async for evt in _claude_stream_direct(messages, system, current_html, direct_key):
            yield evt
        return
    async for evt in _claude_stream_emergent(messages, system, current_html):
        yield evt


async def _claude_stream_direct(
    messages: List[Dict[str, Any]],
    system: str,
    current_html: str,
    api_key: str,
):
    """Native tool calling via official anthropic SDK."""
    try:
        from anthropic import AsyncAnthropic
    except Exception as e:
        yield {"type": "error", "message": f"anthropic SDK missing: {e}"}
        return
    from modules.freebuild_v2.tools import TOOL_SCHEMAS, execute_tool_call

    # Convert OpenAI-format tool schemas to Anthropic format
    anthropic_tools = []
    for s in TOOL_SCHEMAS:
        fn = s.get("function") or {}
        anthropic_tools.append({
            "name": fn.get("name"),
            "description": fn.get("description", "")[:1024],
            "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
        })

    client = AsyncAnthropic(api_key=api_key)
    sys_text = system
    if current_html:
        sys_text += (
            f"\n\n📐 السياق: العميل يملك حالياً موقع HTML قائم بحجم {len(current_html)} حرف. "
            "أي طلب تعديل → استدعِ أداة جراحية (set_theme/edit_section/add_page/update_website)."
        )

    msgs: List[Dict[str, Any]] = []
    for m in messages:
        if m.get("role") in ("user", "assistant"):
            txt = (m.get("content") or "")[:12000]
            if txt.strip():
                msgs.append({"role": m["role"], "content": txt})

    for iteration in range(30):
        try:
            resp = await client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=8192,
                system=sys_text,
                tools=anthropic_tools,
                messages=msgs,
            )
        except Exception as e:
            yield {"type": "error", "message": f"anthropic api: {str(e)[:240]}"}
            return

        tool_uses = []
        assistant_blocks = []
        for block in resp.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                txt = getattr(block, "text", "") or ""
                assistant_blocks.append({"type": "text", "text": txt})
                for i in range(0, len(txt), 40):
                    yield {"type": "text", "content": txt[i:i + 40]}
                    await asyncio.sleep(0.01)
            elif btype == "tool_use":
                tu = {"id": block.id, "name": block.name,
                      "input": dict(block.input) if block.input else {}}
                tool_uses.append(tu)
                assistant_blocks.append({
                    "type": "tool_use", "id": tu["id"],
                    "name": tu["name"], "input": tu["input"],
                })

        if assistant_blocks:
            msgs.append({"role": "assistant", "content": assistant_blocks})

        if resp.stop_reason == "end_turn" or not tool_uses:
            yield {"type": "done"}
            return

        tool_results_blocks = []
        for tu in tool_uses:
            args = tu["input"] or {}
            if tu["name"] in ("update_website", "edit_section", "add_page", "set_theme",
                              "qa_html", "publish_site", "inject_quran_blocks"):
                args["current_html"] = current_html
            yield {"type": "tool", "status": "calling", "name": tu["name"],
                   "args": {k: v for k, v in args.items() if k != "current_html"}}
            result = await execute_tool_call(tu["name"], args)
            evt = {"type": "tool", "status": "done", "name": tu["name"],
                   "ok": result.get("ok"),
                   "summary": _tool_summary(tu["name"], result)}
            if (
                tu["name"] in ("build_website", "update_website", "edit_section",
                                "add_page", "set_theme", "build_quran_mushaf_reader",
                                "build_creative_quran_site", "build_quran_website",
                                "inject_quran_blocks")
                and result.get("ok") and isinstance(result.get("html"), str)
            ):
                current_html = result["html"]
                evt["html"] = current_html
            if tu["name"] == "publish_site" and result.get("ok") and result.get("_publish_request"):
                evt["_publish_request"] = True
                evt["slug"] = result.get("slug")
                evt["title"] = result.get("title")
            if tu["name"] in ("generate_audio", "generate_image_url") and result.get("ok"):
                evt["url"] = result.get("url")
            yield evt
            trimmed = {k: v for k, v in result.items() if k != "html"}
            if "html" in result:
                trimmed["html_size"] = len(result["html"])
            tool_results_blocks.append({
                "type": "tool_result",
                "tool_use_id": tu["id"],
                "content": json.dumps(trimmed, ensure_ascii=False)[:14000],
            })

        msgs.append({"role": "user", "content": tool_results_blocks})

    yield {"type": "text", "content": "\n(وصلت لـ30 استدعاء أداة)"}
    yield {"type": "done"}


async def _claude_stream_emergent(
    messages: List[Dict[str, Any]],
    system: str,
    current_html: str,
):
    """Legacy emergentintegrations path (fallback when ANTHROPIC_API_KEY missing).
    Uses text-blob tool parsing."""
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
        history_text += f"\n\n{role}: {m.get('content','')[:8000]}"

    last_user = messages[-1].get("content", "")
    full_input = history_text + f"\n\nالمستخدم: {last_user}"

    chat = LlmChat(
        api_key=key,
        session_id=session_id,
        system_message=system + tool_hint,
    )
    chat.with_model("anthropic", "claude-sonnet-4-5")

    for iteration in range(30):
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
                if name in ("update_website", "edit_section", "add_page", "set_theme", "qa_html", "publish_site", "inject_quran_blocks"):
                    args["current_html"] = current_html
                yield {"type": "tool", "status": "calling", "name": name,
                       "args": {k: v for k, v in args.items() if k != "current_html"}}
                result = await execute_tool_call(name, args)
                evt = {"type": "tool", "status": "done", "name": name,
                       "ok": result.get("ok"),
                       "summary": _tool_summary(name, result)}
                if name in ("build_website", "update_website", "edit_section", "add_page", "set_theme", "build_quran_mushaf_reader", "build_creative_quran_site", "build_quran_website", "inject_quran_blocks") and result.get("ok") and result.get("html"):
                    current_html = result["html"]
                    evt["html"] = current_html
                if name == "publish_site" and result.get("ok") and result.get("_publish_request"):
                    evt["_publish_request"] = True
                    evt["slug"] = result.get("slug")
                    evt["title"] = result.get("title")
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

    yield {"type": "text", "content": "\n(وصلت لـ30 دورة — أكمل بما عندي، اطلب التكملة لو تبي أكثر)"}
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
    if name == "fetch_quran_blocks":
        return result.get("summary", "تم جلب كتل القرآن")
    if name == "build_creative_quran_site":
        return result.get("summary", "تم بناء موقع قرآن إبداعي")
    if name == "build_quran_website":
        return result.get("summary", "تم بناء موقع قرآن")
    if name == "inject_quran_blocks":
        return result.get("summary", "تم زرع كتل القرآن")
    if name == "analyze_intent":
        return result.get("summary", "تم تحليل الطلب")
    if name == "pick_design":
        return result.get("summary", "تم اختيار التصميم")
    if name == "qa_html":
        return result.get("summary", "تم فحص الموقع")
    if name == "geo_lookup":
        return result.get("summary", "تم تحديد الموقع")
    if name == "publish_site":
        return result.get("summary", "تم تجهيز النشر")
    return "تم"
