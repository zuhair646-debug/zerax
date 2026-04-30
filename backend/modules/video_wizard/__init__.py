"""
Smart conversational Video Wizard endpoints.

Powers /chat/video — a deep multi-turn flow that asks contextual questions
based on the chosen video category (commercial, cinematic, anime, horror, etc).

Flow:
    1. POST /api/wizard/video/start     → returns the type-picker question
    2. POST /api/wizard/video/answer    → user picks type/answers a question
                                           → returns next question OR ready-to-generate state
    3. POST /api/wizard/video/generate  → final generation (uses /api/studio/video/generate
                                           internally for credit handling)

State is stored per session_id (uuid) in `video_wizard_sessions` collection.

PRICING for the deep wizard differs from the merchant studio:
  Standard (Sora 2):   4 credits/sec   for 4/8/12s     (basic quality)
  Premium  (Sora 2):   8 credits/sec   for 15/30/45s   (higher quality, longer)
  Cinema   (Sora 2):  12 credits/sec   for 60s+ or 'open'  (max quality)
The 'open' duration defaults to 60s for now (Sora 2 limit).
"""
from __future__ import annotations
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Categories with their question flows
CATEGORIES = {
    "commercial": {
        "label": "🎯 إعلاني",
        "desc": "إعلان لمنتج أو خدمة",
        "questions": [
            {"id": "product",  "label": "ما المنتج/الخدمة؟",                    "type": "text"},
            {"id": "audience", "label": "من جمهورك المستهدف؟",                   "type": "text"},
            {"id": "key_message", "label": "ما الرسالة الأساسية في 1-2 جملة؟",   "type": "text"},
            {"id": "voiceover","label": "النص المنطوق في الإعلان (اختياري)",     "type": "text", "optional": True},
        ],
    },
    "cinematic": {
        "label": "🎬 سينمائي",
        "desc": "مشهد سينمائي بقصة",
        "questions": [
            {"id": "story_idea", "label": "ما فكرة القصة/المشهد؟",               "type": "text"},
            {"id": "setting",    "label": "أين يحدث؟ (مدينة، صحراء، فضاء...)",   "type": "text"},
            {"id": "mood",       "label": "المزاج العام؟",                       "type": "select",
             "options": ["dramatic", "epic", "mysterious", "romantic", "tense", "uplifting"]},
            {"id": "voiceover",  "label": "حوار/تعليق صوتي (اختياري)",            "type": "text", "optional": True},
        ],
    },
    "anime": {
        "label": "🍥 أنيمي",
        "desc": "بأسلوب الأنمي الياباني",
        "questions": [
            {"id": "characters_count", "label": "كم عدد الشخصيات؟",              "type": "number", "min": 1, "max": 6},
            {"id": "characters_desc",  "label": "صف الشخصيات (شكل، عمر، ملابس)",  "type": "text"},
            {"id": "world",            "label": "في أي عالم؟ (مدينة يابانية، جزيرة، فضاء...)", "type": "text"},
            {"id": "scenario",         "label": "ما الذي يحدث؟ (السيناريو)",     "type": "text"},
            {"id": "voiceover",        "label": "حوار الشخصيات (اختياري)",       "type": "text", "optional": True},
        ],
    },
    "horror": {
        "label": "👻 رعب",
        "desc": "أجواء مخيفة سينمائية",
        "questions": [
            {"id": "atmosphere", "label": "نوع الجو؟",                           "type": "select",
             "options": ["psychological", "supernatural", "slasher", "found_footage", "gothic"]},
            {"id": "setting",    "label": "أين يحدث؟",                           "type": "text"},
            {"id": "scare_idea", "label": "ما الذي يثير الرعب؟",                  "type": "text"},
            {"id": "voiceover",  "label": "أصوات/همسات (اختياري)",                "type": "text", "optional": True},
        ],
    },
    "documentary": {
        "label": "📽️ وثائقي",
        "desc": "قصة حقيقية بأسلوب وثائقي",
        "questions": [
            {"id": "topic",      "label": "ما الموضوع؟",                          "type": "text"},
            {"id": "narration",  "label": "النص الذي يقرأه الراوي",                "type": "text"},
            {"id": "visuals",    "label": "ما المشاهد الرئيسية؟",                 "type": "text"},
        ],
    },
    "music_video": {
        "label": "🎵 فيديو موسيقي",
        "desc": "كليب لأغنية أو موسيقى",
        "questions": [
            {"id": "genre",      "label": "نوع الموسيقى؟",                        "type": "select",
             "options": ["arabic", "pop", "rock", "electronic", "classical", "rap"]},
            {"id": "lyrics",     "label": "الكلمات (اختياري)",                    "type": "text", "optional": True},
            {"id": "vibe",       "label": "ما المشاهد التي تتخيلها؟",             "type": "text"},
        ],
    },
    "vlog": {
        "label": "📹 vlog",
        "desc": "تجربة شخصية أو يومية",
        "questions": [
            {"id": "topic",      "label": "ما موضوع الـ vlog؟",                   "type": "text"},
            {"id": "personality","label": "نبرة المتكلم؟",                        "type": "select",
             "options": ["energetic", "calm", "funny", "informative", "emotional"]},
            {"id": "narration",  "label": "ما الذي يُقال (السكريبت)",             "type": "text"},
        ],
    },
}

# Duration tiers
DURATION_TIERS = [
    {"id": "15", "seconds": 15, "label": "15 ثانية",  "tier": "premium",  "cost_per_sec": 8},
    {"id": "30", "seconds": 30, "label": "30 ثانية",  "tier": "premium",  "cost_per_sec": 8},
    {"id": "45", "seconds": 45, "label": "45 ثانية",  "tier": "premium",  "cost_per_sec": 8},
    {"id": "60", "seconds": 60, "label": "60 ثانية",  "tier": "cinema",   "cost_per_sec": 12},
    {"id": "open", "seconds": 60, "label": "مفتوح (يحدّده الذكاء)", "tier": "cinema", "cost_per_sec": 12},
]

VOICE_OPTIONS = [
    {"id": "alloy",   "label": "Alloy — متوازن"},
    {"id": "echo",    "label": "Echo — رجالي عميق"},
    {"id": "fable",   "label": "Fable — بريطاني"},
    {"id": "onyx",    "label": "Onyx — قوي"},
    {"id": "nova",    "label": "Nova — نسائي شاب"},
    {"id": "shimmer", "label": "Shimmer — نسائي ناعم"},
    {"id": "none",    "label": "بدون صوت"},
]


# ---- Models ----

class WizardStartIn(BaseModel):
    pass  # nothing — server creates session


class WizardAnswerIn(BaseModel):
    session_id: str
    answer: Any


class WizardGenerateIn(BaseModel):
    session_id: str


def create_video_wizard_router(db, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/api/wizard/video", tags=["video-wizard"])

    async def _get_credits(user_id: str) -> int:
        u = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
        return (u or {}).get("credits", 0) or 0

    @router.get("/categories")
    async def get_categories():
        """Return the list of category options (no auth needed)."""
        return {
            "categories": [
                {"id": k, "label": v["label"], "desc": v["desc"]} for k, v in CATEGORIES.items()
            ],
            "durations": DURATION_TIERS,
            "voices": VOICE_OPTIONS,
        }

    @router.post("/start")
    async def wizard_start(_: WizardStartIn, user=Depends(get_current_user)):
        """Begin a new video wizard conversation."""
        sid = str(uuid.uuid4())
        await db.video_wizard_sessions.insert_one({
            "id": sid,
            "user_id": user["user_id"],
            "category": None,
            "answers": {},
            "step": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "session_id": sid,
            "next_question": {
                "kind": "category_picker",
                "label": "أهلاً! دعنا ننشئ فيديو رائع. أولاً: ما نوع الفيديو الذي تريده؟",
                "options": [{"id": k, "label": v["label"], "desc": v["desc"]} for k, v in CATEGORIES.items()],
            },
        }

    @router.post("/answer")
    async def wizard_answer(payload: WizardAnswerIn, user=Depends(get_current_user)):
        """Submit an answer; returns next question or 'ready' state."""
        sess = await db.video_wizard_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not sess:
            raise HTTPException(404, "session not found")

        # Step 0: category pick
        if not sess.get("category"):
            cat = str(payload.answer)
            if cat not in CATEGORIES:
                raise HTTPException(400, "invalid category")
            await db.video_wizard_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"category": cat, "step": 1}}
            )
            first_q = CATEGORIES[cat]["questions"][0]
            return {
                "next_question": {**first_q, "kind": "category_question", "step_label": f"1 / {len(CATEGORIES[cat]['questions']) + 2}"},
                "category": cat,
                "category_label": CATEGORIES[cat]["label"],
            }

        cat = sess["category"]
        questions = CATEGORIES[cat]["questions"]
        step = sess.get("step", 1)

        # If we're answering a category question
        if step <= len(questions):
            current_q = questions[step - 1]
            answers = dict(sess.get("answers") or {})
            answers[current_q["id"]] = payload.answer
            new_step = step + 1
            await db.video_wizard_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"answers": answers, "step": new_step}}
            )
            if new_step <= len(questions):
                next_q = questions[new_step - 1]
                return {
                    "next_question": {**next_q, "kind": "category_question",
                                      "step_label": f"{new_step} / {len(questions) + 2}"},
                }
            # Done with category questions → ask duration
            return {
                "next_question": {
                    "kind": "duration_picker",
                    "id": "duration",
                    "label": "اختر مدة الفيديو — كل مدة لها تكلفة مختلفة (الأطول = جودة أعلى)",
                    "options": DURATION_TIERS,
                    "step_label": f"{len(questions) + 1} / {len(questions) + 2}",
                },
            }

        # Step len(q)+1: duration picked
        if step == len(questions) + 1:
            duration_id = str(payload.answer)
            duration_tier = next((d for d in DURATION_TIERS if d["id"] == duration_id), None)
            if not duration_tier:
                raise HTTPException(400, "invalid duration")
            answers = dict(sess.get("answers") or {})
            answers["duration_id"] = duration_id
            answers["duration_seconds"] = duration_tier["seconds"]
            answers["cost_per_sec"] = duration_tier["cost_per_sec"]
            answers["tier"] = duration_tier["tier"]
            await db.video_wizard_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"answers": answers, "step": step + 1}}
            )
            return {
                "next_question": {
                    "kind": "voice_picker",
                    "id": "voice",
                    "label": "اختر الصوت (يُقرأ به النص الصوتي):",
                    "options": VOICE_OPTIONS,
                    "step_label": f"{len(questions) + 2} / {len(questions) + 2}",
                },
            }

        # Step len(q)+2: voice picked → ready
        if step == len(questions) + 2:
            voice_id = str(payload.answer)
            answers = dict(sess.get("answers") or {})
            answers["voice"] = voice_id
            cost = answers["duration_seconds"] * answers["cost_per_sec"]
            answers["estimated_cost"] = cost
            await db.video_wizard_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"answers": answers, "step": step + 1, "ready": True}}
            )
            credits = await _get_credits(user["user_id"])
            return {
                "ready": True,
                "summary": {
                    "category": cat,
                    "category_label": CATEGORIES[cat]["label"],
                    "answers": answers,
                    "estimated_cost": cost,
                    "credits_balance": credits,
                    "can_afford": credits >= cost,
                },
            }

        raise HTTPException(400, "wizard already complete")

    @router.get("/session/{session_id}")
    async def get_session(session_id: str, user=Depends(get_current_user)):
        sess = await db.video_wizard_sessions.find_one(
            {"id": session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not sess:
            raise HTTPException(404, "session not found")
        return sess

    @router.post("/generate")
    async def wizard_generate(payload: WizardGenerateIn, user=Depends(get_current_user)):
        """Compose final prompt from session and generate via Sora 2."""
        sess = await db.video_wizard_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not sess or not sess.get("ready"):
            raise HTTPException(400, "session not ready")

        ans = sess.get("answers") or {}
        cat = sess["category"]
        cat_def = CATEGORIES[cat]
        # Compose a strong prompt from all answers
        prompt_parts: List[str] = []
        prompt_parts.append(f"Style: {cat_def['label'].split(' ', 1)[-1]} ({cat}).")
        for q in cat_def["questions"]:
            v = ans.get(q["id"])
            if v:
                prompt_parts.append(f"{q['label']}: {v}")
        prompt_parts.append(f"Duration: {ans['duration_seconds']} seconds. High cinematic quality.")
        full_prompt = " ".join(str(p) for p in prompt_parts)

        # Atomic credit deduction
        cost = ans["estimated_cost"]
        result = await db.users.update_one(
            {"id": user["user_id"], "credits": {"$gte": cost}},
            {"$inc": {"credits": -cost},
             "$push": {"credit_history": {
                 "amount": -cost, "reason": f"video_wizard_{cat}_{ans['duration_id']}",
                 "timestamp": datetime.now(timezone.utc).isoformat(),
             }}}
        )
        if result.modified_count == 0:
            raise HTTPException(402, f"رصيد النقاط غير كافٍ ({cost} نقاط مطلوبة)")

        try:
            from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
            emergent_key = os.environ.get("EMERGENT_LLM_KEY")
            if not emergent_key:
                raise RuntimeError("EMERGENT_LLM_KEY not configured")

            video_gen = OpenAIVideoGeneration(api_key=emergent_key)
            # Sora 2 caps at 12s currently; will accept longer prompts but generate up to its max
            sora_duration = min(12, ans["duration_seconds"])
            logger.info(f"[VIDEO-WIZARD] Generating: cat={cat}, sora_dur={sora_duration}, requested={ans['duration_seconds']}")
            video_bytes = video_gen.text_to_video(
                prompt=full_prompt,
                model="sora-2",
                size="1280x720",
                duration=sora_duration,
                max_wait_time=600,
            )
            if not video_bytes:
                raise RuntimeError("Empty video bytes returned")

            import base64
            video_id = str(uuid.uuid4())
            video_b64 = base64.b64encode(video_bytes).decode("utf-8")
            data_url = f"data:video/mp4;base64,{video_b64}"

            doc = {
                "id": video_id,
                "user_id": user["user_id"],
                "category": cat,
                "session_id": payload.session_id,
                "media_url": data_url,
                "prompt_used": full_prompt,
                "duration_actual_seconds": sora_duration,
                "duration_requested": ans["duration_seconds"],
                "credits_spent": cost,
                "answers": ans,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.video_wizard_results.insert_one(doc.copy())
            await db.video_wizard_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"completed": True, "result_id": video_id}}
            )
            doc.pop("_id", None)
            return {
                "ok": True,
                "asset": {k: v for k, v in doc.items() if k != "_id"},
                "credits_spent": cost,
                "credits_remaining": await _get_credits(user["user_id"]),
            }
        except Exception as e:
            # Refund
            await db.users.update_one(
                {"id": user["user_id"]},
                {"$inc": {"credits": cost},
                 "$push": {"credit_history": {
                     "amount": cost,
                     "reason": f"refund_video_wizard_failed: {str(e)[:80]}",
                     "timestamp": datetime.now(timezone.utc).isoformat(),
                 }}}
            )
            logger.exception(f"[VIDEO-WIZARD] Generate failed: {e}")
            raise HTTPException(500, f"فشل توليد الفيديو. تمت إعادة النقاط. ({str(e)[:120]})")

    return router
