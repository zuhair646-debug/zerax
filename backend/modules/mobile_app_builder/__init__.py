"""
Zerax Mobile App Builder — conversational builder for mobile-style apps.

Generates a self-contained SPA optimised for an iPhone-frame preview.
Categories: 🎮 Games (canvas+JS), 📱 Apps (lists/forms/dashboards), 🛠️ Tools
(calculators, converters), 🧒 Kids (interactive toys).

Endpoints:
    POST /api/mobile-app/start
    POST /api/mobile-app/chat
    GET  /api/mobile-app/session/{id}
    GET  /api/mobile-app/preview/{id}        — serves the HTML (iframe target)
    POST /api/mobile-app/save                — persist to mobile_apps collection
    GET  /api/mobile-app/projects
    DELETE /api/mobile-app/project/{id}
    GET  /api/mobile-app/public/{id}         — public, unauthenticated preview
    GET  /api/mobile-app/categories          — preset templates
"""
from __future__ import annotations
import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

TURN_UPDATE_COST = 3
MAX_TURNS_PER_SESSION = 50


CATEGORIES = [
    {"id": "game", "label": "🎮 لعبة", "examples": ["لعبة ثعبان", "tic-tac-toe", "Memory match", "Flappy bird"]},
    {"id": "app", "label": "📱 تطبيق", "examples": ["To-Do list", "متجر صغير", "مفكرة يومية", "حاسبة سعرات"]},
    {"id": "tool", "label": "🛠️ أداة", "examples": ["محول وحدات", "QR generator", "حاسبة قروض", "مولّد كلمات سر"]},
    {"id": "kids", "label": "🧒 للأطفال", "examples": ["تعليم حروف", "ألوان وأصوات", "رسم بالأصابع", "أرقام تفاعلية"]},
]


ARCHITECT_SYSTEM = """أنت مهندس تطبيقات موبايل محترف. تتكلم بالعربي السعودي مع المالك وتبني تطبيقاً واحد-صفحة جاهز للجوال داخل محادثة.

# OUTPUT JSON STRICT
كل ردّ لازم يكون JSON صالح بالشكل:
{
  "message_to_user": "ردّك للمالك بالعربي السعودي (1-3 جمل قصيرة)",
  "next_question_type": "text" | "yes_no" | "done",
  "options": null أو ["نعم","لا"] لو يس_نو,
  "progress_note": "ملاحظة قصيرة عن اللي تم (اختياري)",
  "html_update": "<!doctype html>...</html>" أو null
}

# قواعد البناء (حاسمة):
1. **mobile-first**: 375×812px (iPhone). استخدم viewport meta و touch-friendly buttons (≥44px).
2. **standalone HTML** كامل: <!doctype>, <html>, <head> (meta viewport, <style>), <body>, <script>. كل CSS و JS مدمج (لا cdn خارجي للأصول الأساسية، يجوز Google Fonts و CDN library واحد لو لازم).
3. **RTL + Arabic** افتراضياً (`dir="rtl"`, `lang="ar"`), خطوط: Tajawal أو Cairo من Google Fonts.
4. **اللعبة/التطبيق شغّال فوراً**: ما يحتاج build/install. لو لعبة → Canvas + requestAnimationFrame. لو to-do → localStorage. لو حاسبة → دوال JS محلية.
5. **بدون فريموركس ثقيلة**: لا React/Vue/Angular. Vanilla JS فقط أو Alpine.js لو فعلاً لازم.
6. **state داخل localStorage** للبيانات الدائمة (notes, scores, settings).
7. **تحديث incremental**: في أول turn تبني نسخة minimum-viable شغّالة. كل turn بعده يضيف ميزة أو يحسّن.
8. **ممنوع placeholders**: ما تقول "/* TODO */" أو "// add logic". الكود الكامل لازم يشتغل.
9. **اللون والذوق**: حدّد palette جذابة (gradient header، accent color واضح، dark/light mode حسب طلب المالك). استخدم CSS variables.
10. **animations خفيفة**: transitions/keyframes لتحسين الإحساس (button press, score popup, screen transition).
11. **زر "حول التطبيق"** أو modal صغير يوضّح كيف يشتغل.
12. **اختبر منطقياً**: قبل ما ترجع html_update، تأكد إن الدوال الرئيسية مذكورة وتنادي بعض صحيح.

# تدفّق المحادثة:
- turn 1: اسأل عن النوع (لعبة/تطبيق/أداة/أطفال) — yes_no مش مناسب → text أو options.
- turn 2-3: اسأل عن الميزات الأساسية (سؤال واحد بالمرة).
- turn 4: ابدأ تبني (html_update=النسخة الأولى) + اسأل "تبي أضيف X؟".
- turn 5+: مع كل "نعم" → html_update محدّث + ميزة جديدة.
- لما المالك يقول "كفاية"/"خلاص"/"حلو" → next_question_type="done".

تذكر: المالك يشوف معاينة مباشرة على iPhone frame في الجانب. خل البناء يبدو حلو من أول لمحة."""


class StartIn(BaseModel):
    pass


class ChatIn(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1, max_length=8000)


class SaveIn(BaseModel):
    session_id: str
    name: str = Field(..., min_length=1, max_length=120)
    category: Optional[str] = "app"
    icon_emoji: Optional[str] = "📱"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_messages(session: Dict[str, Any], new_user_msg: str) -> List[Dict[str, str]]:
    msgs: List[Dict[str, str]] = [{"role": "system", "content": ARCHITECT_SYSTEM}]
    history = session.get("messages", [])
    current_html = session.get("html") or ""
    if current_html:
        # Show current HTML so AI can edit it incrementally
        msgs.append({
            "role": "system",
            "content": f"# HTML الحالي للتطبيق (عدّل عليه بدل ما تبدأ من الصفر):\n```html\n{current_html[:14000]}\n```",
        })
    for m in history[-12:]:
        if m.get("role") in ("user", "assistant"):
            msgs.append({"role": m["role"], "content": (m.get("content") or "")[:4000]})
    msgs.append({"role": "user", "content": new_user_msg[:4000]})
    return msgs


async def _llm_turn(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Try OpenAI direct → fallback to Emergent (Claude). Force JSON output."""
    direct_key = os.environ.get("OPENAI_DIRECT_KEY", "").strip()
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    raw = ""
    last_err = None

    # NEW: route through Zerax AI Smart Router first (best model + boundaries)
    try:
        from modules.zitex_ai import zitex_chat
        sys_combined = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        user_msgs = [m for m in messages if m["role"] != "system"]
        result = await zitex_chat(
            agent="mobile_app",
            messages=user_msgs,
            override_system=sys_combined + "\n\n⚠️ ردّك لازم يكون JSON صالح فقط.",
        )
        if result.get("ok"):
            raw = (result.get("content") or "").strip()
            if raw.startswith("```"):
                raw = raw.split("```", 2)[1] if "```" in raw[3:] else raw
                if raw.startswith("json"):
                    raw = raw[4:].strip()
                raw = raw.rstrip("`").strip()
    except Exception as e:
        last_err = f"zitex_ai: {type(e).__name__}: {str(e)[:200]}"
        logger.warning(f"[MOBILE-APP] zitex_ai failed: {last_err}")

    if not raw and direct_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=direct_key)
            resp = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.8,
                max_tokens=16000,
                response_format={"type": "json_object"},
            )
            raw = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            last_err = f"openai: {type(e).__name__}: {str(e)[:200]}"
            logger.warning(f"[MOBILE-APP] openai failed: {last_err}")

    if not raw and emergent_key:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            sys_combined = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
            user_parts = [m["content"] for m in messages if m["role"] == "user"]
            prior = "\n\n".join(f"[سابق] {u}" for u in user_parts[:-1])
            current = user_parts[-1] if user_parts else ""
            chat = LlmChat(
                api_key=emergent_key,
                session_id=f"mobile-app-{uuid.uuid4().hex[:8]}",
                system_message=sys_combined + "\n\n⚠️ ردّك لازم يكون JSON صالح فقط.",
            )
            chat.with_model("anthropic", "claude-sonnet-4-5")
            raw = await chat.send_message(UserMessage(text=(prior + "\n\n[الآن] " + current).strip()))
            raw = (raw or "").strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```", 2)[1] if "```" in raw[3:] else raw
                if raw.startswith("json"):
                    raw = raw[4:].strip()
                raw = raw.rstrip("`").strip()
        except Exception as e:
            last_err = (last_err or "") + f" | claude: {str(e)[:200]}"

    if not raw:
        raise HTTPException(500, f"فشل الذكاء المعماري. {last_err or ''}".strip())

    try:
        data = json.loads(raw)
    except Exception:
        # Sometimes the model emits an extra prefix/suffix. Try to locate the JSON braces.
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(raw[start:end + 1])
            except Exception:
                raise HTTPException(500, "تعذر فهم رد الذكاء (JSON غير صالح).")
        else:
            raise HTTPException(500, "تعذر فهم رد الذكاء (JSON غير موجود).")

    # Normalise
    return {
        "message_to_user": str(data.get("message_to_user") or "تم.")[:2000],
        "next_question_type": (data.get("next_question_type") or "text") if data.get("next_question_type") in ("text", "yes_no", "done") else "text",
        "options": data.get("options") if isinstance(data.get("options"), list) else None,
        "progress_note": (data.get("progress_note") or None),
        "html_update": data.get("html_update") if isinstance(data.get("html_update"), str) and len(data.get("html_update")) > 50 else None,
    }


def create_mobile_app_router(db, get_current_user):
    router = APIRouter(prefix="/api/mobile-app", tags=["mobile-app"])

    async def _credits(uid: str) -> int:
        doc = await db.users.find_one({"id": uid}, {"_id": 0, "credits": 1, "is_owner": 1})
        if not doc:
            return 0
        if doc.get("is_owner"):
            return 999999
        return int(doc.get("credits", 0) or 0)

    async def _deduct(uid: str, amount: int) -> bool:
        doc = await db.users.find_one({"id": uid}, {"_id": 0, "credits": 1, "is_owner": 1})
        if not doc:
            return False
        if doc.get("is_owner"):
            return True
        if int(doc.get("credits", 0) or 0) < amount:
            return False
        await db.users.update_one({"id": uid}, {"$inc": {"credits": -amount}})
        return True

    @router.get("/categories")
    async def categories(user=Depends(get_current_user)):
        return {"categories": CATEGORIES}

    @router.post("/start")
    async def start(_: StartIn = StartIn(), user=Depends(get_current_user)):
        session_id = str(uuid.uuid4())
        greeting = (
            "هلا والله! أنا مهندس تطبيقات موبايل. وش نوع التطبيق اللي تبيني أبنيه؟\n"
            "🎮 لعبة · 📱 تطبيق · 🛠️ أداة · 🧒 للأطفال — أو اكتب فكرتك مباشرة."
        )
        doc = {
            "id": session_id,
            "user_id": user["user_id"],
            "messages": [{"role": "assistant", "content": greeting, "timestamp": _now()}],
            "html": "",
            "turns": 0,
            "complete": False,
            "credits_spent": 0,
            "created_at": _now(),
            "updated_at": _now(),
        }
        await db.mobile_app_sessions.insert_one(doc.copy())
        return {
            "session_id": session_id,
            "assistant_message": greeting,
            "next_question_type": "text",
            "options": None,
            "credits_balance": await _credits(user["user_id"]),
            "categories": CATEGORIES,
        }

    @router.post("/chat")
    async def chat(body: ChatIn, user=Depends(get_current_user)):
        session = await db.mobile_app_sessions.find_one(
            {"id": body.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not session:
            raise HTTPException(404, "session not found")
        if session.get("turns", 0) >= MAX_TURNS_PER_SESSION:
            raise HTTPException(400, f"تم الوصول للحد الأقصى ({MAX_TURNS_PER_SESSION}). احفظ المشروع وابدأ جلسة جديدة.")

        session["messages"].append({"role": "user", "content": body.message, "timestamp": _now()})

        msgs = _build_messages(session, body.message)
        ai = await _llm_turn(msgs)

        html_update = ai.get("html_update")
        charge = 0
        if html_update:
            if not await _deduct(user["user_id"], TURN_UPDATE_COST):
                html_update = None
                ai["html_update"] = None
                ai["message_to_user"] = (
                    f"رصيدك ما يكفي للتحديث ({TURN_UPDATE_COST} نقاط مطلوبة). "
                    "اشحن رصيدك وارجع — المحادثة محفوظة."
                )
            else:
                charge = TURN_UPDATE_COST

        session["messages"].append({
            "role": "assistant",
            "content": ai["message_to_user"],
            "message_to_user": ai["message_to_user"],
            "next_question_type": ai["next_question_type"],
            "options": ai.get("options"),
            "progress_note": ai.get("progress_note"),
            "had_html_update": bool(html_update),
            "timestamp": _now(),
        })

        update_fields = {
            "messages": session["messages"],
            "turns": session.get("turns", 0) + 1,
            "updated_at": _now(),
        }
        if html_update:
            update_fields["html"] = html_update
            update_fields["credits_spent"] = session.get("credits_spent", 0) + charge
        if ai["next_question_type"] == "done":
            update_fields["complete"] = True

        await db.mobile_app_sessions.update_one(
            {"id": body.session_id}, {"$set": update_fields}
        )

        return {
            "assistant_message": ai["message_to_user"],
            "next_question_type": ai["next_question_type"],
            "options": ai.get("options"),
            "progress_note": ai.get("progress_note"),
            "html_updated": bool(html_update),
            "turns": update_fields["turns"],
            "credits_balance": await _credits(user["user_id"]),
            "credits_spent_this_turn": charge,
            "complete": update_fields.get("complete", session.get("complete", False)),
        }

    @router.get("/sessions")
    async def list_sessions(user=Depends(get_current_user)):
        cur = db.mobile_app_sessions.find(
            {"user_id": user["user_id"]},
            {"_id": 0, "id": 1, "title": 1, "messages": 1, "category": 1,
             "saved": 1, "created_at": 1, "updated_at": 1},
        ).sort([("updated_at", -1)]).limit(50)
        items = []
        async for s in cur:
            msgs = s.get("messages") or []
            preview = next((m["content"][:60].strip() for m in msgs
                            if m.get("role") == "user" and m.get("content")), "")
            items.append({
                "id": s["id"],
                "title": (s.get("title") or preview or "تطبيق بلا اسم")[:80],
                "preview": preview[:80],
                "turns": len([m for m in msgs if m.get("role") == "user"]),
                "category": s.get("category"),
                "saved": bool(s.get("saved")),
                "updated_at": s.get("updated_at"),
                "created_at": s.get("created_at"),
            })
        return {"ok": True, "items": items, "count": len(items)}

    @router.delete("/session/{session_id}")
    async def delete_session(session_id: str, user=Depends(get_current_user)):
        r = await db.mobile_app_sessions.delete_one(
            {"id": session_id, "user_id": user["user_id"]}
        )
        return {"ok": True, "deleted": r.deleted_count}

    @router.get("/session/{session_id}")
    async def get_session(session_id: str, user=Depends(get_current_user)):
        s = await db.mobile_app_sessions.find_one(
            {"id": session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not s:
            raise HTTPException(404, "session not found")
        return s

    @router.get("/preview/{session_id}")
    async def preview(session_id: str, user=Depends(get_current_user)):
        s = await db.mobile_app_sessions.find_one(
            {"id": session_id, "user_id": user["user_id"]}, {"_id": 0, "html": 1}
        )
        if not s or not s.get("html"):
            return Response(content="<!doctype html><meta charset='utf-8'><body style='font-family:Tajawal,sans-serif;background:#0a0a14;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center;padding:20px;direction:rtl'><div><div style='font-size:48px'>📱</div><div style='margin-top:10px;opacity:0.7'>لسه ما بنينا التطبيق — كمّل المحادثة</div></div></body>", media_type="text/html")
        return Response(content=s["html"], media_type="text/html")

    @router.post("/save")
    async def save(body: SaveIn, user=Depends(get_current_user)):
        s = await db.mobile_app_sessions.find_one(
            {"id": body.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not s or not s.get("html"):
            raise HTTPException(400, "لا يوجد تطبيق محفوظ في هذه الجلسة.")
        app_id = str(uuid.uuid4())
        doc = {
            "id": app_id,
            "user_id": user["user_id"],
            "session_id": body.session_id,
            "name": body.name,
            "category": body.category or "app",
            "icon_emoji": body.icon_emoji or "📱",
            "html": s["html"],
            "credits_spent": s.get("credits_spent", 0),
            "created_at": _now(),
        }
        await db.mobile_apps.insert_one(doc.copy())
        return {"ok": True, "project_id": app_id, "public_url": f"/api/mobile-app/public/{app_id}"}

    @router.get("/projects")
    async def projects(user=Depends(get_current_user)):
        items = await db.mobile_apps.find(
            {"user_id": user["user_id"]}, {"_id": 0, "html": 0}
        ).sort([("created_at", -1)]).to_list(200)
        return {"projects": items}

    @router.delete("/project/{project_id}")
    async def delete_project(project_id: str, user=Depends(get_current_user)):
        r = await db.mobile_apps.delete_one({"id": project_id, "user_id": user["user_id"]})
        if r.deleted_count == 0:
            raise HTTPException(404, "project not found")
        return {"ok": True}

    @router.get("/public/{project_id}")
    async def public_preview(project_id: str):
        p = await db.mobile_apps.find_one({"id": project_id}, {"_id": 0, "html": 1, "name": 1})
        if not p or not p.get("html"):
            raise HTTPException(404, "project not found")
        return Response(content=p["html"], media_type="text/html")

    # ════════════════════════════════════════════════════════════════════
    # 🎮 TEMPLATES MARKETPLACE — publish, browse, remix
    # ════════════════════════════════════════════════════════════════════
    @router.post("/publish/{project_id}")
    async def publish_template(project_id: str, user=Depends(get_current_user)):
        """Publish a saved project as a public template anyone can remix."""
        proj = await db.mobile_apps.find_one(
            {"id": project_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not proj:
            raise HTTPException(404, "project not found")
        await db.mobile_apps.update_one(
            {"id": project_id},
            {"$set": {"published": True, "published_at": _now(), "remix_count": proj.get("remix_count", 0)}},
        )
        return {"ok": True, "public_url": f"/api/mobile-app/public/{project_id}"}

    @router.post("/unpublish/{project_id}")
    async def unpublish_template(project_id: str, user=Depends(get_current_user)):
        r = await db.mobile_apps.update_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"$set": {"published": False}},
        )
        if r.matched_count == 0:
            raise HTTPException(404, "project not found")
        return {"ok": True}

    @router.get("/marketplace")
    async def marketplace(category: Optional[str] = None, sort: str = "remix"):
        """Public marketplace — no auth needed. Sort: 'remix' (popular) | 'new'."""
        q: Dict[str, Any] = {"published": True}
        if category and category != "all":
            q["category"] = category
        sort_field = "remix_count" if sort == "remix" else "published_at"
        items = await db.mobile_apps.find(
            q, {"_id": 0, "html": 0}
        ).sort([(sort_field, -1)]).limit(60).to_list(60)
        # Enrich with author name
        for it in items:
            try:
                u = await db.users.find_one({"id": it.get("user_id")}, {"_id": 0, "name": 1})
                it["author_name"] = (u or {}).get("name") or "مالك مجهول"
            except Exception:
                it["author_name"] = "مالك مجهول"
        return {"templates": items, "count": len(items)}

    @router.get("/top-creators")
    async def top_creators(window: str = "week"):
        """🏆 Leaderboard of users whose published apps got the most remixes.
        window: 'week' (last 7d) | 'month' (last 30d) | 'all'.
        """
        from datetime import datetime, timezone, timedelta
        match: Dict[str, Any] = {"published": True}
        if window == "week":
            since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            match["published_at"] = {"$gte": since}
        elif window == "month":
            since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            match["published_at"] = {"$gte": since}
        pipeline = [
            {"$match": match},
            {"$group": {
                "_id": "$user_id",
                "total_remixes": {"$sum": {"$ifNull": ["$remix_count", 0]}},
                "apps_published": {"$sum": 1},
                "latest_app_id": {"$last": "$id"},
                "latest_app_name": {"$last": "$name"},
                "latest_app_category": {"$last": "$category"},
            }},
            {"$sort": {"total_remixes": -1, "apps_published": -1}},
            {"$limit": 10},
        ]
        rows = await db.mobile_apps.aggregate(pipeline).to_list(10)
        out = []
        for idx, r in enumerate(rows):
            uid = r.get("_id")
            u = await db.users.find_one({"id": uid}, {"_id": 0, "name": 1, "avatar": 1}) if uid else None
            out.append({
                "rank": idx + 1,
                "user_id": uid,
                "name": (u or {}).get("name") or "مبدع مجهول",
                "avatar": (u or {}).get("avatar"),
                "total_remixes": r.get("total_remixes", 0),
                "apps_published": r.get("apps_published", 0),
                "showcase": {
                    "id": r.get("latest_app_id"),
                    "name": r.get("latest_app_name"),
                    "category": r.get("latest_app_category"),
                },
            })
        return {"window": window, "creators": out, "count": len(out)}

    @router.post("/remix/{project_id}")
    async def remix_template(project_id: str, user=Depends(get_current_user)):
        """Fork a published template into the user's own session so they can edit it."""
        tpl = await db.mobile_apps.find_one(
            {"id": project_id, "published": True}, {"_id": 0}
        )
        if not tpl:
            raise HTTPException(404, "template not published or not found")
        # Bump remix counter
        await db.mobile_apps.update_one({"id": project_id}, {"$inc": {"remix_count": 1}})
        # Create a fresh session seeded with the template's HTML
        new_sid = str(uuid.uuid4())
        greeting = (
            f"تم نسخ القالب «{tpl.get('name', 'بدون اسم')}» — جاهز للتعديل. "
            "وش تبيني أغيّر فيه؟ (ألوان، ميزات، أسماء، أي شي)"
        )
        doc = {
            "id": new_sid,
            "user_id": user["user_id"],
            "messages": [{"role": "assistant", "content": greeting, "timestamp": _now()}],
            "html": tpl["html"],
            "turns": 0,
            "complete": False,
            "credits_spent": 0,
            "remixed_from": project_id,
            "created_at": _now(),
            "updated_at": _now(),
        }
        await db.mobile_app_sessions.insert_one(doc.copy())
        return {
            "session_id": new_sid,
            "assistant_message": greeting,
            "next_question_type": "text",
            "html_present": True,
            "credits_balance": await _credits(user["user_id"]),
        }

    # ════════════════════════════════════════════════════════════════════
    # 📦 REACT NATIVE / EXPO EXPORT
    # ════════════════════════════════════════════════════════════════════
    @router.get("/export-rn/{project_id}")
    async def export_react_native(project_id: str, user=Depends(get_current_user)):
        """Return a React Native (Expo) skeleton that wraps the generated HTML
        in a WebView. The user can run it via `npx expo start` immediately."""
        p = await db.mobile_apps.find_one(
            {"id": project_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "project not found")
        html = (p.get("html") or "").replace("`", "\\`").replace("$", "\\$")
        app_name = p.get("name", "ZeraxApp")
        # Sanitise app_name for the JS string
        safe_name = app_name.replace('"', '\\"').replace("\n", " ")[:80]
        package_json = {
            "name": "zitex-app",
            "version": "1.0.0",
            "main": "node_modules/expo/AppEntry.js",
            "scripts": {
                "start": "expo start",
                "android": "expo start --android",
                "ios": "expo start --ios",
                "web": "expo start --web",
            },
            "dependencies": {
                "expo": "~50.0.0",
                "react": "18.2.0",
                "react-native": "0.73.0",
                "react-native-webview": "13.6.4",
            },
        }
        app_js = (
            "import React from 'react';\n"
            "import { SafeAreaView, StatusBar, StyleSheet } from 'react-native';\n"
            "import { WebView } from 'react-native-webview';\n\n"
            f"const APP_HTML = `{html}`;\n\n"
            "export default function App() {\n"
            "  return (\n"
            "    <SafeAreaView style={styles.root}>\n"
            "      <StatusBar barStyle=\"light-content\" backgroundColor=\"#0a0a14\" />\n"
            "      <WebView\n"
            "        originWhitelist={['*']}\n"
            "        source={{ html: APP_HTML }}\n"
            "        style={styles.web}\n"
            "        javaScriptEnabled={true}\n"
            "        domStorageEnabled={true}\n"
            "      />\n"
            "    </SafeAreaView>\n"
            "  );\n"
            "}\n\n"
            "const styles = StyleSheet.create({\n"
            "  root: { flex: 1, backgroundColor: '#0a0a14' },\n"
            "  web: { flex: 1 },\n"
            "});\n"
        )
        readme = (
            f"# {safe_name}\n\n"
            "تم توليد هذا المشروع تلقائياً عبر **Zerax Mobile App Builder**.\n\n"
            "## كيف تشغّله محلياً\n\n"
            "```bash\n"
            "npm install -g expo-cli\n"
            "yarn install\n"
            "npx expo start\n"
            "```\n\n"
            "بعدها افتح Expo Go على جوالك واسكان QR code. التطبيق راح يفتح فوراً.\n"
            "\n"
            "## النشر على App Store / Play Store\n"
            "```bash\n"
            "npx eas build --platform ios\n"
            "npx eas build --platform android\n"
            "```\n"
        )
        return {
            "ok": True,
            "project_name": safe_name,
            "files": {
                "package.json": json.dumps(package_json, indent=2, ensure_ascii=False),
                "App.js": app_js,
                "README.md": readme,
                "app.json": json.dumps({
                    "expo": {
                        "name": safe_name,
                        "slug": safe_name.lower().replace(" ", "-")[:30],
                        "version": "1.0.0",
                        "orientation": "portrait",
                        "icon": "./assets/icon.png",
                        "userInterfaceStyle": "automatic",
                        "splash": {"backgroundColor": "#0a0a14"},
                        "assetBundlePatterns": ["**/*"],
                        "ios": {"supportsTablet": True},
                        "android": {"package": f"com.zitex.{safe_name.lower().replace(' ', '')[:20]}"},
                        "web": {"favicon": "./assets/favicon.png"},
                    }
                }, indent=2, ensure_ascii=False),
            },
            "instructions": "نزّل الملفات، استخدم `yarn install` ثم `npx expo start`. يحتاج Node 18+ و Expo CLI.",
        }

    return router
