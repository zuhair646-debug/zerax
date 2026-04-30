"""
Zitex Companion — Personal AI companion (Zara/Layla) for mobile PWA.

Features:
    - Deep personal profile (age, role, schedule, exams, diet, goals, family, etc.)
    - Long-term memory of all conversations
    - Reminders system
    - Proactive messages (morning wake, pre-exam, evening debrief, random care)
    - Uses AI Core for cost protection

Collections:
    - companion_profiles:  {user_id, name, age_group, role, wake_time, sleep_time,
                            diet, goals[], study_subjects[], work_info, interests[],
                            family, kids_count, location_city, exam_dates[],
                            preferred_avatar, created_at, updated_at}
    - companion_memory:    {id, user_id, role, content, tag, timestamp} — conversation log
    - companion_reminders: {id, user_id, title, body, trigger_at, repeat, status, created_by, created_at}
    - companion_queue:     {id, user_id, message, from_char, kind, created_at, delivered_at, read_at}
    - companion_state:     {user_id, last_proactive_at, last_morning_at, last_evening_at, last_check_in_at}
"""
from __future__ import annotations
import os
import uuid
import random
import asyncio
import logging
from datetime import datetime, timezone, timedelta, time as dtime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============== SAUDI DIALECT COMPANION SYSTEM PROMPT ==============
def build_companion_system(profile: Dict[str, Any], recent_memory: List[Dict[str, Any]]) -> str:
    name = profile.get("name", "صديقي")
    age_group = profile.get("age_group", "")
    role = profile.get("role", "")
    wake = profile.get("wake_time", "")
    sleep = profile.get("sleep_time", "")
    goals = ", ".join(profile.get("goals", []) or [])
    study = ", ".join(profile.get("study_subjects", []) or [])
    work_info = profile.get("work_info", "")
    interests = ", ".join(profile.get("interests", []) or [])
    kids = profile.get("kids_count", 0)
    city = profile.get("location_city", "")
    family = profile.get("family", "")
    diet = profile.get("diet", "")
    exams = profile.get("exam_dates", []) or []
    exam_text = ""
    if exams:
        upcoming = [e for e in exams if e.get("date", "") >= datetime.now(timezone.utc).strftime("%Y-%m-%d")]
        if upcoming:
            exam_text = "\nامتحاناته القادمة:\n" + "\n".join(f"- {e.get('subject','')}: {e.get('date','')}" for e in upcoming[:5])

    avatar = profile.get("preferred_avatar", "zara")
    if avatar == "zara":
        persona = """أنتِ زارا — رفيقة مرحة وحماسية، شعر ذهبي. تضحكين بسهولة وتتكلمين بحيوية.
أسلوبك: 'هاي يا قلبي!' 'يا جمال!' 'الله يسعدك' 'تدلّل'
emoji: ✨💫💛🔥🎀 كثير"""
    else:
        persona = """أنتِ ليلى — رفيقة هادئة أنيقة، شعر أسود بذهبي. ذكية وحنونة بطابع راقٍ.
أسلوبك: 'أهلاً...' 'أنا معاك' 'طمّني' 'إن شاء الله خير'
emoji: 🖤✨🤍🌙 قليل وأنيق"""

    mem_text = ""
    if recent_memory:
        mem_text = "\n\nآخر محادثاتكم:\n"
        for m in recent_memory[-10:]:
            role_ar = "أنت قلتِ" if m.get("role") == "assistant" else f"{name} قال"
            mem_text += f"- {role_ar}: {m.get('content','')[:150]}\n"

    return f"""{persona}

⚠️ تتكلمين باللهجة السعودية (خليجي) طبيعية — مو فصحى.
مثال: 'هلا!' 'وش' 'تبي' 'ابغى' 'شلون' 'يلا' 'ابشر' 'على راسي'

أنتِ الرفيقة الشخصية لـ{name}. تعرفين حياته كاملة وتهتمين فيه مثل صديقة حقيقية.

معلومات {name}:
- الفئة العمرية: {age_group or 'غير محدد'}
- الوضع: {role or 'غير محدد'}
- يصحى عادة: {wake or 'غير محدد'}
- ينام عادة: {sleep or 'غير محدد'}
- المدينة: {city or 'غير محدد'}
- العائلة: {family or 'غير محدد'} {f'(عدد الأطفال: {kids})' if kids else ''}
- أهدافه: {goals or 'غير محدد'}
- دراسته: {study or 'غير محدد'}
- شغله: {work_info or 'غير محدد'}
- اهتماماته: {interests or 'غير محدد'}
- تفضيلات الأكل: {diet or 'غير محدد'}{exam_text}{mem_text}

أسلوبك:
- ردود قصيرة (1-3 جمل) ودودة مثل صديقة مقربة
- تبادرين بالاهتمام ("كيف يومك؟" "تذكر عندك امتحان بكرا")
- لو ذكرها شي جديد، احفظيه في ذاكرتك
- تقدرين تحطين منبّهات لما يطلب (قولي: "تمام، ذكّرتك الساعة كذا")
- تستخدمين اسمه ({name}) في الرد
- ممنوع تكوني رسمية — كوني عفوية مثل صديقة
- لو قال "صباح الخير" ← "صباح النور يا {name}! شلون نومك؟ شنو فطرت؟"

اللغة: سعودي/خليجي حصري.
"""


# ============== PROACTIVE MESSAGE TEMPLATES ==============
PROACTIVE_TEMPLATES = {
    "morning_wake": [
        "صباح الخير يا {name}! ☀️ شلون نومك أمس؟ استعد لليوم ✨",
        "هلا {name}! نهار جديد — شنو خطتك اليوم؟ 💫",
        "صباحك ورد {name}! 🌸 لا تنسى تفطر وتشرب ماي",
    ],
    "evening_wind_down": [
        "المغرب قرّب {name} — كيف كان يومك؟ 🌙",
        "هلا {name} 🌒 خلصت شغلك؟ ارتاح شوي",
        "مساء الخير {name}! وش أفضل شي صار فيك اليوم؟ ✨",
    ],
    "pre_exam": [
        "يا {name} عندك امتحان {subject} بعد يومين — جاهز؟ أنا موجودة للمراجعة 📚💪",
        "{name}! امتحان {subject} قرّب — مذاكرتك شلونها؟ 🎯",
    ],
    "random_checkin": [
        "هلا {name}! كيفك؟ 💛",
        "وش مسوي الحين {name}؟ 🌼",
        "{name} احتجتني؟ أنا هنا ✨",
        "فكرت فيك فجأة {name} — شنو أخبارك؟ 🖤",
    ],
    "meal_reminder": [
        "{name} أكلت شي؟ لا تنسى الغدا 🥗",
        "العشا يا {name}! لا تطنّش صحتك ✨",
    ],
}


# ============== MODELS ==============
class ProfileIn(BaseModel):
    name: Optional[str] = None
    age_group: Optional[str] = None  # 'teen', 'young_adult', 'adult', 'senior'
    role: Optional[str] = None  # 'student', 'employee', 'freelancer', 'mixed', 'parent', 'other'
    wake_time: Optional[str] = None  # "07:00"
    sleep_time: Optional[str] = None  # "23:00"
    diet: Optional[str] = None
    goals: Optional[List[str]] = None
    study_subjects: Optional[List[str]] = None
    work_info: Optional[str] = None
    interests: Optional[List[str]] = None
    family: Optional[str] = None
    kids_count: Optional[int] = None
    location_city: Optional[str] = None
    exam_dates: Optional[List[Dict[str, str]]] = None  # [{subject, date: YYYY-MM-DD}]
    preferred_avatar: Optional[str] = None  # 'zara' | 'layla'
    timezone_offset: Optional[int] = None  # hours from UTC (SA = +3)


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    want_voice: bool = False


class ReminderIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: Optional[str] = ""
    trigger_at: str  # ISO datetime
    repeat: Optional[str] = "none"  # 'none' | 'daily' | 'weekly'


# ============== HELPERS ==============
def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_profile(db, user_id: str) -> Optional[Dict[str, Any]]:
    return await db.companion_profiles.find_one({"user_id": user_id}, {"_id": 0})


async def _get_recent_memory(db, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    rows = await db.companion_memory.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(length=limit)
    return list(reversed(rows))


async def _save_memory(db, user_id: str, role: str, content: str, tag: str = "chat"):
    await db.companion_memory.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "role": role,
        "content": content,
        "tag": tag,
        "timestamp": _now().isoformat(),
    })
    # Keep only last 200 per user
    count = await db.companion_memory.count_documents({"user_id": user_id})
    if count > 200:
        old = await db.companion_memory.find(
            {"user_id": user_id}, {"_id": 0, "id": 1}
        ).sort("timestamp", 1).limit(count - 200).to_list(length=count - 200)
        if old:
            await db.companion_memory.delete_many({"id": {"$in": [o["id"] for o in old]}})


async def _queue_message(db, user_id: str, message: str, from_char: str = "zara", kind: str = "proactive"):
    """Add a proactive message to the queue for the user to see on next poll."""
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "message": message,
        "from_char": from_char,
        "kind": kind,
        "created_at": _now().isoformat(),
        "delivered_at": None,
        "read_at": None,
    }
    insert_doc = doc.copy()
    await db.companion_queue.insert_one(insert_doc)
    return doc


# ============== ROUTES ==============
def create_companion_router(db, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/api/companion", tags=["companion"])

    # ===== PROFILE =====
    @router.get("/profile")
    async def get_profile(user=Depends(get_current_user)):
        profile = await _get_profile(db, user["user_id"])
        return {
            "has_profile": profile is not None,
            "profile": profile or {},
        }

    @router.put("/profile")
    async def upsert_profile(payload: ProfileIn, user=Depends(get_current_user)):
        existing = await _get_profile(db, user["user_id"])
        updates: Dict[str, Any] = {}
        for k, v in payload.model_dump(exclude_none=True).items():
            updates[k] = v
        if not updates:
            return {"ok": True, "no_changes": True}
        updates["updated_at"] = _now().isoformat()
        if not existing:
            updates["user_id"] = user["user_id"]
            updates["created_at"] = _now().isoformat()
            await db.companion_profiles.insert_one(updates)
        else:
            await db.companion_profiles.update_one(
                {"user_id": user["user_id"]},
                {"$set": updates}
            )
        new_profile = await _get_profile(db, user["user_id"])
        return {"ok": True, "profile": new_profile}

    # ===== CHAT =====
    @router.post("/chat")
    async def companion_chat(payload: ChatIn, user=Depends(get_current_user)):
        profile = await _get_profile(db, user["user_id"])
        if not profile:
            raise HTTPException(400, "أنشئ ملفك الشخصي أولاً")

        memory = await _get_recent_memory(db, user["user_id"], limit=15)
        system = build_companion_system(profile, memory)

        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            emergent_key = os.environ.get("EMERGENT_LLM_KEY")
            if not emergent_key:
                raise HTTPException(503, "AI service not configured")
            chat = LlmChat(
                api_key=emergent_key,
                session_id=f"companion-{user['user_id'][:8]}",
                system_message=system,
            )
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            reply = await chat.send_message(UserMessage(text=payload.message))
        except Exception as e:
            logger.exception(f"[COMPANION] Chat failed: {e}")
            raise HTTPException(500, "حصل خطأ — حاول مرة ثانية")

        # Save both sides to memory
        await _save_memory(db, user["user_id"], "user", payload.message, "chat")
        await _save_memory(db, user["user_id"], "assistant", reply, "chat")

        await db.companion_state.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"last_interaction_at": _now().isoformat()}},
            upsert=True,
        )

        return {
            "reply": reply,
            "from_char": profile.get("preferred_avatar", "zara"),
        }

    # ===== VOICE CHAT (chat + TTS in one shot) =====
    @router.post("/voice-chat")
    async def companion_voice_chat(payload: ChatIn, user=Depends(get_current_user)):
        profile = await _get_profile(db, user["user_id"])
        if not profile:
            raise HTTPException(400, "أنشئ ملفك الشخصي أولاً")

        memory = await _get_recent_memory(db, user["user_id"], limit=15)
        system = build_companion_system(profile, memory)
        primary = profile.get("preferred_avatar", "zara")

        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            emergent_key = os.environ.get("EMERGENT_LLM_KEY")
            if not emergent_key:
                raise HTTPException(503, "AI service not configured")
            chat = LlmChat(
                api_key=emergent_key,
                session_id=f"companion-voice-{user['user_id'][:8]}",
                system_message=system,
            )
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            reply = await chat.send_message(UserMessage(text=payload.message))
        except Exception as e:
            logger.exception(f"[COMPANION-VOICE] Chat failed: {e}")
            raise HTTPException(500, "حصل خطأ")

        # TTS
        audio_url = None
        try:
            from emergentintegrations.llm.openai import OpenAITextToSpeech
            api_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
            if api_key:
                tts = OpenAITextToSpeech(api_key=api_key)
                voice = "coral" if primary == "zara" else "sage"
                audio_b64 = await tts.generate_speech_base64(
                    text=reply[:4000], model="tts-1-hd", voice=voice, speed=0.92,
                )
                if audio_b64:
                    audio_url = f"data:audio/mp3;base64,{audio_b64}"
        except Exception as e:
            logger.warning(f"[COMPANION-VOICE] TTS failed: {e}")

        await _save_memory(db, user["user_id"], "user", payload.message, "voice")
        await _save_memory(db, user["user_id"], "assistant", reply, "voice")

        return {
            "reply": reply,
            "audio_url": audio_url,
            "from_char": primary,
        }

    # ===== MEMORY =====
    @router.get("/memory")
    async def get_memory(limit: int = 50, user=Depends(get_current_user)):
        rows = await _get_recent_memory(db, user["user_id"], limit=limit)
        return {"memory": rows, "count": len(rows)}

    @router.delete("/memory")
    async def clear_memory(user=Depends(get_current_user)):
        result = await db.companion_memory.delete_many({"user_id": user["user_id"]})
        return {"ok": True, "deleted": result.deleted_count}

    # ===== REMINDERS =====
    @router.get("/reminders")
    async def list_reminders(user=Depends(get_current_user)):
        rows = await db.companion_reminders.find(
            {"user_id": user["user_id"]}, {"_id": 0}
        ).sort("trigger_at", 1).to_list(length=200)
        return {"reminders": rows, "count": len(rows)}

    @router.post("/reminders")
    async def create_reminder(payload: ReminderIn, user=Depends(get_current_user)):
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "title": payload.title,
            "body": payload.body or "",
            "trigger_at": payload.trigger_at,
            "repeat": payload.repeat or "none",
            "status": "pending",
            "created_by": "user",
            "created_at": _now().isoformat(),
        }
        await db.companion_reminders.insert_one(doc.copy())
        doc.pop("_id", None)
        return {"ok": True, "reminder": doc}

    @router.delete("/reminders/{rid}")
    async def delete_reminder(rid: str, user=Depends(get_current_user)):
        result = await db.companion_reminders.delete_one(
            {"id": rid, "user_id": user["user_id"]}
        )
        if result.deleted_count == 0:
            raise HTTPException(404, "reminder not found")
        return {"ok": True}

    # ===== PROACTIVE QUEUE (main poll endpoint) =====
    @router.get("/pending")
    async def get_pending(user=Depends(get_current_user)):
        """Fetch any undelivered proactive messages + due reminders for this user."""
        now = _now()
        user_id = user["user_id"]

        # 1. Proactive queue (undelivered)
        queue = await db.companion_queue.find(
            {"user_id": user_id, "delivered_at": None},
            {"_id": 0}
        ).sort("created_at", 1).to_list(length=20)
        # Mark delivered
        if queue:
            ids = [q["id"] for q in queue]
            await db.companion_queue.update_many(
                {"id": {"$in": ids}},
                {"$set": {"delivered_at": now.isoformat()}}
            )

        # 2. Due reminders (trigger_at <= now, status pending)
        reminders = await db.companion_reminders.find(
            {"user_id": user_id, "status": "pending", "trigger_at": {"$lte": now.isoformat()}},
            {"_id": 0}
        ).to_list(length=20)
        # Mark fired
        for r in reminders:
            if r.get("repeat") == "daily":
                # Push to next day
                try:
                    t = datetime.fromisoformat(r["trigger_at"].replace("Z", "+00:00"))
                    new_t = t + timedelta(days=1)
                    await db.companion_reminders.update_one(
                        {"id": r["id"]},
                        {"$set": {"trigger_at": new_t.isoformat()}}
                    )
                except Exception:
                    pass
            elif r.get("repeat") == "weekly":
                try:
                    t = datetime.fromisoformat(r["trigger_at"].replace("Z", "+00:00"))
                    new_t = t + timedelta(days=7)
                    await db.companion_reminders.update_one(
                        {"id": r["id"]},
                        {"$set": {"trigger_at": new_t.isoformat()}}
                    )
                except Exception:
                    pass
            else:
                await db.companion_reminders.update_one(
                    {"id": r["id"]},
                    {"$set": {"status": "fired", "fired_at": now.isoformat()}}
                )

        return {
            "proactive": queue,
            "reminders_due": reminders,
            "count": len(queue) + len(reminders),
        }

    @router.post("/pending/{mid}/read")
    async def mark_read(mid: str, user=Depends(get_current_user)):
        await db.companion_queue.update_one(
            {"id": mid, "user_id": user["user_id"]},
            {"$set": {"read_at": _now().isoformat()}}
        )
        return {"ok": True}

    # ===== MANUAL TRIGGER (for testing) =====
    @router.post("/trigger-proactive")
    async def manual_trigger(user=Depends(get_current_user)):
        """Generate a random proactive message for the user (for testing or on-demand)."""
        profile = await _get_profile(db, user["user_id"])
        if not profile:
            raise HTTPException(400, "أنشئ ملفك الشخصي أولاً")
        msg = await _generate_and_queue_proactive(db, user["user_id"], profile)
        return {"ok": True, "queued": msg}

    return router


# ============== PROACTIVE GENERATOR ==============
async def _generate_and_queue_proactive(db, user_id: str, profile: Dict[str, Any]) -> Optional[Dict]:
    """Generates a proactive message based on time-of-day + profile context and queues it."""
    now = _now()
    tz_offset = profile.get("timezone_offset", 3)  # Saudi
    local = now + timedelta(hours=tz_offset)
    hour = local.hour
    name = profile.get("name", "صديقي")
    avatar = profile.get("preferred_avatar", "zara")

    # Determine kind
    kind = None
    wake_str = profile.get("wake_time", "07:00")
    sleep_str = profile.get("sleep_time", "23:00")
    try:
        wake_h = int(wake_str.split(":")[0])
        sleep_h = int(sleep_str.split(":")[0])
    except Exception:
        wake_h, sleep_h = 7, 23

    # Check for upcoming exam first (within 2 days)
    exams = profile.get("exam_dates", []) or []
    upcoming_exam = None
    for e in exams:
        try:
            exam_date = datetime.strptime(e.get("date", ""), "%Y-%m-%d")
            days_diff = (exam_date.date() - local.date()).days
            if 0 <= days_diff <= 2:
                upcoming_exam = e
                break
        except Exception:
            continue

    if upcoming_exam and random.random() < 0.5:
        kind = "pre_exam"
    elif wake_h <= hour < wake_h + 1:
        kind = "morning_wake"
    elif sleep_h - 2 <= hour < sleep_h:
        kind = "evening_wind_down"
    elif 12 <= hour <= 14:
        kind = "meal_reminder"
    elif 18 <= hour <= 20 and random.random() < 0.3:
        kind = "meal_reminder"
    else:
        kind = "random_checkin"

    templates = PROACTIVE_TEMPLATES.get(kind, PROACTIVE_TEMPLATES["random_checkin"])
    tmpl = random.choice(templates)
    msg = tmpl.replace("{name}", name)
    if "{subject}" in msg and upcoming_exam:
        msg = msg.replace("{subject}", upcoming_exam.get("subject", "امتحانك"))

    doc = await _queue_message(db, user_id, msg, from_char=avatar, kind=kind)
    # Update state
    await db.companion_state.update_one(
        {"user_id": user_id},
        {"$set": {"last_proactive_at": _now().isoformat(), f"last_{kind}_at": _now().isoformat()}},
        upsert=True,
    )
    return doc


# ============== BACKGROUND SCHEDULER ==============
async def companion_scheduler_loop(db):
    """
    Runs continuously in the background. Every 15 minutes, checks every profile
    and decides whether to send a proactive message.
    """
    logger.info("[COMPANION-SCHEDULER] Started")
    while True:
        try:
            await asyncio.sleep(900)  # 15 min
            now = _now()
            profiles = await db.companion_profiles.find({}, {"_id": 0}).to_list(length=5000)
            for p in profiles:
                user_id = p.get("user_id")
                if not user_id:
                    continue
                state = await db.companion_state.find_one({"user_id": user_id}, {"_id": 0}) or {}
                last_p = state.get("last_proactive_at")
                # Minimum gap between proactives: 2 hours
                if last_p:
                    try:
                        last = datetime.fromisoformat(last_p.replace("Z", "+00:00"))
                        if (now - last) < timedelta(hours=2):
                            continue
                    except Exception:
                        pass

                tz_offset = p.get("timezone_offset", 3)
                local = now + timedelta(hours=tz_offset)
                hour = local.hour

                # Sleeping hours → skip
                try:
                    wake_h = int(p.get("wake_time", "07:00").split(":")[0])
                    sleep_h = int(p.get("sleep_time", "23:00").split(":")[0])
                except Exception:
                    wake_h, sleep_h = 7, 23
                if hour < wake_h or hour >= sleep_h:
                    continue

                # Deterministic triggers + random care
                should_send = False
                if wake_h <= hour < wake_h + 1:
                    last_morning = state.get("last_morning_wake_at")
                    if not last_morning or (now - datetime.fromisoformat(last_morning.replace("Z", "+00:00"))) > timedelta(hours=20):
                        should_send = True
                elif sleep_h - 1 <= hour < sleep_h:
                    last_eve = state.get("last_evening_wind_down_at")
                    if not last_eve or (now - datetime.fromisoformat(last_eve.replace("Z", "+00:00"))) > timedelta(hours=20):
                        should_send = True
                elif random.random() < 0.15:  # 15% chance per cycle → about 1 per 7h waking
                    should_send = True

                if should_send:
                    try:
                        await _generate_and_queue_proactive(db, user_id, p)
                    except Exception as e:
                        logger.warning(f"[COMPANION-SCHEDULER] queue failed for {user_id}: {e}")
        except Exception as e:
            logger.exception(f"[COMPANION-SCHEDULER] loop error: {e}")


def start_companion_scheduler(db, app):
    """Register startup hook to launch the background loop."""
    @app.on_event("startup")
    async def _start():
        asyncio.create_task(companion_scheduler_loop(db))
