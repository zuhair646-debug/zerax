"""
Smart conversational Image Wizard endpoints.

Powers /chat/image — a deep multi-turn flow that adapts questions
based on the chosen image category (social_ad, product_shot, banner, portrait, scene).

Flow:
    1. POST /api/wizard/image/start     → returns the category-picker question
    2. POST /api/wizard/image/answer    → user picks category/answers a question
                                           → returns next question OR ready state
    3. POST /api/wizard/image/generate  → final generation via Gemini Nano Banana

Pricing:
    Standard:  5 points/image
    Premium:   10 points/image (higher detail, text-heavy scenes)
"""
from __future__ import annotations
import os
import uuid
import base64
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

CATEGORIES: Dict[str, Dict[str, Any]] = {
    "social_ad": {
        "label": "📱 إعلان سوشيال",
        "desc": "منشور للسوشيال ميديا",
        "preferred_model": "gemini",
        "questions": [
            {"id": "product",   "label": "وش المنتج/الخدمة اللي تبي تعلن لها؟",      "type": "text"},
            {"id": "offer",     "label": "فيه عرض أو سعر خاص؟",                     "type": "text", "optional": True},
            {"id": "audience",  "label": "مين الجمهور المستهدف؟",                    "type": "text"},
            {"id": "mood",      "label": "المزاج العام؟",                            "type": "select",
             "options": ["energetic", "luxurious", "playful", "minimal", "dramatic"]},
        ],
    },
    "product_shot": {
        "label": "🛍️ صورة منتج",
        "desc": "لقطة احترافية لمنتج واحد",
        "preferred_model": "openai",
        "questions": [
            {"id": "product",    "label": "وش المنتج بالضبط؟",                       "type": "text"},
            {"id": "background", "label": "الخلفية؟ (بيضاء، خشبية، طبيعية...)",       "type": "text"},
            {"id": "lighting",   "label": "نوع الإضاءة؟",                            "type": "select",
             "options": ["golden_hour", "studio_bright", "soft_diffused", "dramatic_side", "natural_daylight"]},
            {"id": "extras",     "label": "عناصر إضافية؟ (زهور، ورق، ديكور...)",      "type": "text", "optional": True},
        ],
    },
    "banner": {
        "label": "🖼️ بنر سينمائي",
        "desc": "بنر أفقي سينمائي 16:9",
        "preferred_model": "gemini",
        "questions": [
            {"id": "concept",    "label": "وش الفكرة العامة؟",                       "type": "text"},
            {"id": "headline",   "label": "عبارة البنر (إذا بتضيفها كـوصف بصري)",     "type": "text", "optional": True},
            {"id": "scene",      "label": "وين يصير المشهد؟",                         "type": "text"},
            {"id": "style",      "label": "الأسلوب البصري؟",                          "type": "select",
             "options": ["cinematic", "modern", "retro", "futuristic", "minimal"]},
        ],
    },
    "logo": {
        "label": "✨ لوقو/شعار",
        "desc": "هوية بصرية احترافية",
        "preferred_model": "openai",
        "questions": [
            {"id": "brand_name", "label": "اسم العلامة/البراند؟",                     "type": "text"},
            {"id": "industry",   "label": "وش مجال البراند؟",                          "type": "text"},
            {"id": "personality","label": "شخصية البراند؟",                            "type": "select",
             "options": ["luxurious", "playful", "minimalist", "bold", "elegant", "tech", "organic"]},
            {"id": "style_hint", "label": "أسلوب الشعار المفضّل؟",                      "type": "select",
             "options": ["wordmark", "monogram", "icon_mark", "lockup", "calligraphic_arabic", "geometric"]},
        ],
    },
    "poster": {
        "label": "🎨 بوستر إعلاني",
        "desc": "بوستر فني للأحداث/الأفلام",
        "preferred_model": "gemini",
        "questions": [
            {"id": "topic",      "label": "موضوع البوستر؟",                            "type": "text"},
            {"id": "title_text", "label": "العنوان الرئيسي على البوستر؟",                "type": "text"},
            {"id": "vibe",       "label": "الإحساس العام؟",                            "type": "select",
             "options": ["minimal", "vintage", "vibrant", "mysterious", "epic", "playful"]},
            {"id": "format",     "label": "الشكل؟",                                   "type": "select",
             "options": ["movie_poster", "event_poster", "concert", "exhibition", "campaign"]},
        ],
    },
    "thumbnail": {
        "label": "🎬 ثَمب نيل يوتيوب",
        "desc": "صورة جذب للقنوات",
        "preferred_model": "openai",
        "questions": [
            {"id": "video_topic","label": "موضوع الفيديو؟",                            "type": "text"},
            {"id": "hook",       "label": "نقطة الجذب (الإثارة/الفضول)؟",              "type": "text"},
            {"id": "face_in",    "label": "تبي تظهر شخصية أو وجه؟",                   "type": "select",
             "options": ["person_shocked", "person_excited", "no_face", "object_only"]},
            {"id": "color_punch","label": "ألوان قوية؟",                                "type": "select",
             "options": ["red_yellow_explosive", "blue_orange", "neon_purple_pink", "green_red", "monochrome_punch"]},
        ],
    },
    "ebook_cover": {
        "label": "📕 غلاف كتاب",
        "desc": "كفر احترافي لكتب رقمية",
        "preferred_model": "gemini",
        "questions": [
            {"id": "book_title", "label": "اسم الكتاب؟",                              "type": "text"},
            {"id": "genre",      "label": "نوع الكتاب؟",                              "type": "select",
             "options": ["fiction_literary", "thriller", "romance", "self_help", "biography", "religious", "business", "fantasy"]},
            {"id": "synopsis",   "label": "ملخص بسطر واحد",                            "type": "text"},
            {"id": "tone",       "label": "النبرة البصرية؟",                          "type": "select",
             "options": ["dark_moody", "bright_uplifting", "minimal_clean", "ornate_traditional", "modern_bold"]},
        ],
    },
    "app_icon": {
        "label": "📱 أيقونة تطبيق",
        "desc": "أيقونة iOS/أندرويد",
        "preferred_model": "openai",
        "questions": [
            {"id": "app_name",   "label": "اسم التطبيق؟",                             "type": "text"},
            {"id": "app_purpose","label": "وش يسوي التطبيق؟",                          "type": "text"},
            {"id": "color_hint", "label": "اللون الأساسي؟",                           "type": "text"},
            {"id": "style",      "label": "الأسلوب؟",                                 "type": "select",
             "options": ["glossy_3d", "flat_minimal", "gradient_modern", "skeuomorphic", "abstract_geometric"]},
        ],
    },
    "portrait": {
        "label": "👤 بورتريه",
        "desc": "صورة شخص أو شخصية",
        "preferred_model": "gemini",
        "questions": [
            {"id": "subject",    "label": "صف الشخص (العمر، الشكل، الملابس)",         "type": "text"},
            {"id": "expression", "label": "التعبير؟ (ابتسامة، جدية، ثقة...)",          "type": "text"},
            {"id": "background", "label": "الخلفية؟",                                 "type": "text"},
            {"id": "style",      "label": "الأسلوب؟",                                 "type": "select",
             "options": ["realistic", "editorial", "3d_render", "illustration", "anime"]},
        ],
    },
    "scene": {
        "label": "🌆 مشهد/منظر",
        "desc": "مشهد خيالي أو حقيقي",
        "preferred_model": "gemini",
        "questions": [
            {"id": "location",   "label": "وين المشهد؟ (صحراء، مدينة، غابة...)",       "type": "text"},
            {"id": "time",       "label": "الوقت؟",                                   "type": "select",
             "options": ["sunrise", "daytime", "golden_hour", "sunset", "night", "storm"]},
            {"id": "elements",   "label": "عناصر مميزة في المشهد؟",                    "type": "text"},
            {"id": "mood",       "label": "الإحساس العام؟",                            "type": "select",
             "options": ["peaceful", "epic", "mysterious", "vibrant", "melancholic"]},
        ],
    },
    "food": {
        "label": "🍽️ طعام",
        "desc": "لقطة طعام شهية",
        "preferred_model": "openai",
        "questions": [
            {"id": "dish",       "label": "وش الطبق؟",                                "type": "text"},
            {"id": "style_plate","label": "طريقة التقديم؟",                            "type": "select",
             "options": ["rustic_wood", "modern_ceramic", "traditional_saj", "minimal_white"]},
            {"id": "top_down",   "label": "زاوية التصوير؟",                            "type": "select",
             "options": ["top_down", "45_degree", "eye_level", "close_macro"]},
            {"id": "extras",     "label": "عناصر حوله؟ (بهارات، خضار...)",             "type": "text", "optional": True},
        ],
    },
    "real_estate": {
        "label": "🏠 عقار/معماري",
        "desc": "صورة هندسية لمبنى",
        "preferred_model": "openai",
        "questions": [
            {"id": "property_type", "label": "نوع العقار؟",                           "type": "select",
             "options": ["villa", "apartment", "office", "commercial_storefront", "interior_living", "interior_kitchen"]},
            {"id": "viewpoint",     "label": "زاوية التصوير؟",                         "type": "select",
             "options": ["street_level", "drone_3quarter", "interior_wide", "detail_macro"]},
            {"id": "time_of_day",   "label": "الوقت؟",                                 "type": "select",
             "options": ["blue_hour", "golden_hour", "midday", "night_lit"]},
            {"id": "details",       "label": "تفاصيل خاصة؟",                            "type": "text", "optional": True},
        ],
    },
    "fashion": {
        "label": "👗 أزياء",
        "desc": "صورة موديل/أزياء",
        "preferred_model": "gemini",
        "questions": [
            {"id": "garment",    "label": "وش القطعة؟ (عباية، فستان، جاكيت...)",       "type": "text"},
            {"id": "model_desc", "label": "صف الموديل (اختياري)",                     "type": "text", "optional": True},
            {"id": "setting",    "label": "المكان؟",                                  "type": "select",
             "options": ["studio_minimal", "urban_street", "desert", "luxury_interior", "natural_outdoor"]},
            {"id": "vibe",       "label": "النَفَس البصري؟",                            "type": "select",
             "options": ["editorial_high_fashion", "commercial_clean", "moody_avantgarde", "lifestyle_natural"]},
        ],
    },
    "automotive": {
        "label": "🚗 سيارات",
        "desc": "صورة سيارة سينمائية",
        "preferred_model": "gemini",
        "questions": [
            {"id": "car_type",   "label": "نوع/موديل السيارة؟",                        "type": "text"},
            {"id": "angle",      "label": "زاوية اللقطة؟",                              "type": "select",
             "options": ["3quarter_front", "side_profile", "low_rear", "overhead", "interior_dash"]},
            {"id": "environment","label": "البيئة؟",                                  "type": "select",
             "options": ["mountain_pass", "urban_night", "desert", "salt_flat", "wet_city_street"]},
            {"id": "mood",       "label": "الإحساس؟",                                 "type": "select",
             "options": ["aggressive_sport", "luxury_calm", "rugged_offroad", "futuristic"]},
        ],
    },
}

QUALITY_TIERS = [
    {"id": "standard", "label": "عادي",   "cost": 5,  "desc": "مناسب للسوشيال ميديا اليومي"},
    {"id": "premium",  "label": "فاخر",   "cost": 10, "desc": "تفاصيل أعلى، مناسب للإعلانات"},
]

ASPECT_OPTIONS = [
    {"id": "1:1",  "label": "مربع 1:1",     "desc": "منشورات سوشيال"},
    {"id": "9:16", "label": "عمودي 9:16",  "desc": "Story / Reels"},
    {"id": "16:9", "label": "أفقي 16:9",   "desc": "بنر / YouTube"},
    {"id": "4:5",  "label": "بورتريه 4:5", "desc": "Instagram"},
]


class WizardStartIn(BaseModel):
    pass


class WizardAnswerIn(BaseModel):
    session_id: str
    answer: Any


class WizardGenerateIn(BaseModel):
    session_id: str


def create_image_wizard_router(db, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/api/wizard/image", tags=["image-wizard"])

    async def _get_credits(user_id: str) -> int:
        u = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
        return (u or {}).get("credits", 0) or 0

    @router.get("/categories")
    async def get_categories():
        return {
            "categories": [
                {"id": k, "label": v["label"], "desc": v["desc"]} for k, v in CATEGORIES.items()
            ],
            "quality_tiers": QUALITY_TIERS,
            "aspect_options": ASPECT_OPTIONS,
        }

    @router.post("/start")
    async def wizard_start(_: WizardStartIn, user=Depends(get_current_user)):
        sid = str(uuid.uuid4())
        await db.image_wizard_sessions.insert_one({
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
                "label": "هلا! يلا نصمم صورة تجنن 💫 أول شي، وش نوع الصورة؟",
                "options": [{"id": k, "label": v["label"], "desc": v["desc"]} for k, v in CATEGORIES.items()],
            },
        }

    @router.post("/answer")
    async def wizard_answer(payload: WizardAnswerIn, user=Depends(get_current_user)):
        sess = await db.image_wizard_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not sess:
            raise HTTPException(404, "session not found")

        # Step 0: category
        if not sess.get("category"):
            cat = str(payload.answer)
            if cat not in CATEGORIES:
                raise HTTPException(400, "invalid category")
            await db.image_wizard_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"category": cat, "step": 1}}
            )
            first_q = CATEGORIES[cat]["questions"][0]
            total = len(CATEGORIES[cat]["questions"]) + 2
            return {
                "next_question": {**first_q, "kind": "category_question", "step_label": f"1 / {total}"},
                "category": cat,
                "category_label": CATEGORIES[cat]["label"],
            }

        cat = sess["category"]
        questions = CATEGORIES[cat]["questions"]
        step = sess.get("step", 1)
        total = len(questions) + 2

        # Category question answered
        if step <= len(questions):
            current_q = questions[step - 1]
            answers = dict(sess.get("answers") or {})
            answers[current_q["id"]] = payload.answer
            new_step = step + 1
            await db.image_wizard_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"answers": answers, "step": new_step}}
            )
            if new_step <= len(questions):
                next_q = questions[new_step - 1]
                return {
                    "next_question": {**next_q, "kind": "category_question",
                                      "step_label": f"{new_step} / {total}"},
                }
            # Done with category Qs → ask aspect
            return {
                "next_question": {
                    "kind": "aspect_picker",
                    "id": "aspect",
                    "label": "تمام! الحين اختر مقاس الصورة:",
                    "options": ASPECT_OPTIONS,
                    "step_label": f"{len(questions) + 1} / {total}",
                },
            }

        # Aspect
        if step == len(questions) + 1:
            aspect = str(payload.answer)
            if not any(a["id"] == aspect for a in ASPECT_OPTIONS):
                raise HTTPException(400, "invalid aspect")
            answers = dict(sess.get("answers") or {})
            answers["aspect_ratio"] = aspect
            await db.image_wizard_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"answers": answers, "step": step + 1}}
            )
            return {
                "next_question": {
                    "kind": "quality_picker",
                    "id": "quality",
                    "label": "آخر خطوة! اختر مستوى الجودة:",
                    "options": QUALITY_TIERS,
                    "step_label": f"{total} / {total}",
                },
            }

        # Quality → ready
        if step == len(questions) + 2:
            qid = str(payload.answer)
            tier = next((q for q in QUALITY_TIERS if q["id"] == qid), None)
            if not tier:
                raise HTTPException(400, "invalid quality")
            answers = dict(sess.get("answers") or {})
            answers["quality"] = qid
            answers["cost"] = tier["cost"]
            await db.image_wizard_sessions.update_one(
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
                    "estimated_cost": tier["cost"],
                    "credits_balance": credits,
                    "can_afford": credits >= tier["cost"],
                },
            }

        raise HTTPException(400, "wizard already complete")

    @router.get("/session/{session_id}")
    async def get_session(session_id: str, user=Depends(get_current_user)):
        sess = await db.image_wizard_sessions.find_one(
            {"id": session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not sess:
            raise HTTPException(404, "session not found")
        return sess

    @router.post("/generate")
    async def wizard_generate(payload: WizardGenerateIn, user=Depends(get_current_user)):
        sess = await db.image_wizard_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not sess or not sess.get("ready"):
            raise HTTPException(400, "session not ready")

        ans = sess.get("answers") or {}
        cat = sess["category"]
        cat_def = CATEGORIES[cat]

        # Build a rich brief from user answers (in Arabic for context)
        brief_lines = [f"النوع: {cat_def['label']}"]
        for q in cat_def["questions"]:
            v = ans.get(q["id"])
            if v:
                brief_lines.append(f"{q['label']} {v}")
        aspect = ans.get("aspect_ratio", "1:1")
        quality = ans.get("quality", "standard")
        brief_lines.append(f"المقاس: {aspect}")
        brief_lines.append(f"الجودة: {quality}")
        brief = "\n".join(str(b) for b in brief_lines)

        cost = ans.get("cost", 5)

        # Deduct credits atomically
        result = await db.users.update_one(
            {"id": user["user_id"], "credits": {"$gte": cost}},
            {"$inc": {"credits": -cost},
             "$push": {"credit_history": {
                 "amount": -cost,
                 "reason": f"image_wizard_{cat}_{quality}",
                 "timestamp": datetime.now(timezone.utc).isoformat(),
             }}}
        )
        if result.modified_count == 0:
            raise HTTPException(402, f"رصيدك ما يكفي ({cost} نقطة مطلوبة)")

        try:
            # ======= STAGE 1: Expert prompt engineering via Claude =======
            from .expert_prompts import get_expert
            expert = get_expert(cat)
            polished_prompt = await _engineer_prompt_with_expert(expert["system"], brief, aspect, quality)
            logger.info(f"[IMAGE-WIZARD] Expert={expert['persona_name']} brief_len={len(brief)} polished_len={len(polished_prompt)}")

            # ======= STAGE 2: Generate image (preferred provider per category, fallback chain) =======
            preferred = cat_def.get("preferred_model", "gemini")
            img_bytes, provider_used = await _generate_image_multiprovider(
                polished_prompt=polished_prompt,
                aspect=aspect,
                quality=quality,
                preferred=preferred,
            )
            if not img_bytes:
                raise RuntimeError("All image providers failed")

            image_id = str(uuid.uuid4())
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            data_url = f"data:image/png;base64,{img_b64}"

            doc = {
                "id": image_id,
                "user_id": user["user_id"],
                "category": cat,
                "session_id": payload.session_id,
                "media_url": data_url,
                "prompt_used": polished_prompt,
                "expert_persona": expert["persona_name"],
                "provider": provider_used,
                "aspect_ratio": aspect,
                "quality": quality,
                "credits_spent": cost,
                "answers": ans,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.image_wizard_results.insert_one(doc.copy())
            await db.image_wizard_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"completed": True, "result_id": image_id}}
            )
            doc.pop("_id", None)
            return {
                "ok": True,
                "asset": {k: v for k, v in doc.items() if k != "_id"},
                "credits_spent": cost,
                "credits_remaining": await _get_credits(user["user_id"]),
                "provider": provider_used,
                "expert": expert["persona_name"],
            }
        except Exception as e:
            # Refund
            await db.users.update_one(
                {"id": user["user_id"]},
                {"$inc": {"credits": cost},
                 "$push": {"credit_history": {
                     "amount": cost,
                     "reason": f"refund_image_wizard_failed: {str(e)[:80]}",
                     "timestamp": datetime.now(timezone.utc).isoformat(),
                 }}}
            )
            logger.exception(f"[IMAGE-WIZARD] Generate failed: {e}")
            raise HTTPException(500, f"فشل توليد الصورة. تمت إعادة النقاط. ({str(e)[:120]})")

    return router


# ============================================================================
# Expert prompt engineering + multi-provider image generation
# ============================================================================

async def _engineer_prompt_with_expert(expert_system: str, brief: str, aspect: str, quality: str) -> str:
    """Run the user brief through OpenAI (direct key) playing the expert persona to produce
    a polished, dense, professional image-generation prompt.
    Falls back to a deterministic English prompt if no key is available.
    """
    user_msg = (
        f"## CLIENT BRIEF (Arabic)\n{brief}\n\n"
        f"## OUTPUT REQUIREMENTS\n"
        f"- Aspect ratio: {aspect}\n"
        f"- Quality tier: {quality} (premium = ultra-detailed, gallery-grade)\n"
        f"- Output language: English (image models perform best with English prompts).\n"
        f"- Output format: ONE single flowing-line prompt of 60-100 words. NO bullet points. NO markdown. NO 'here is the prompt:' preamble. JUST the prompt itself."
    )

    direct_key = os.environ.get("OPENAI_DIRECT_KEY", "").strip()
    polished = ""
    try:
        if direct_key:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=direct_key)
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": expert_system},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.75,
                max_tokens=400,
            )
            polished = (resp.choices[0].message.content or "").strip()
        else:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            api_key = os.environ.get("EMERGENT_LLM_KEY")
            if not api_key:
                raise RuntimeError("no LLM key")
            chat = LlmChat(api_key=api_key, session_id=f"imgexpert-{uuid.uuid4()}", system_message=expert_system)
            chat.with_model("openai", "gpt-4o-mini")
            polished = (await chat.send_message(UserMessage(text=user_msg)) or "").strip()

        if polished.startswith('"') and polished.endswith('"'):
            polished = polished[1:-1]
        if polished.startswith("```"):
            lines = polished.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            polished = "\n".join(lines).strip()
        if len(polished) < 30:
            raise RuntimeError("expert prompt too short")
        return polished
    except Exception as e:
        logger.warning(f"[IMAGE-WIZARD] expert prompt failed, using brief: {e}")
        return f"Professional, high quality, well-composed image. {brief}. Detailed, sharp, cinematic lighting, masterpiece."


async def _generate_image_multiprovider(polished_prompt: str, aspect: str, quality: str, preferred: str = "gemini"):
    """Try preferred provider first, fall back to others. Returns (bytes, provider_name)."""
    providers = [preferred] + [p for p in ("openai", "gemini") if p != preferred]
    last_err = None
    for prov in providers:
        try:
            if prov == "openai":
                bytes_ = await _gen_openai(polished_prompt, aspect, quality)
                if bytes_:
                    return bytes_, "openai_gpt_image_1"
            elif prov == "gemini":
                bytes_ = await _gen_gemini(polished_prompt, aspect, quality)
                if bytes_:
                    return bytes_, "gemini_nano_banana"
        except Exception as e:
            last_err = e
            logger.warning(f"[IMAGE-WIZARD] provider {prov} failed: {e}")
            continue
    raise RuntimeError(f"All providers failed: {last_err}")


async def _gen_gemini(prompt: str, aspect: str, quality: str):
    from emergentintegrations.llm.gemini.image_generation import GeminiImageGeneration
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("no EMERGENT_LLM_KEY")
    gen = GeminiImageGeneration(api_key=api_key)
    images = await gen.generate_images(
        prompt=prompt,
        model="gemini-2.5-flash-image-preview",
        number_of_images=1,
    )
    if images and images[0]:
        return images[0]
    return None


async def _gen_openai(prompt: str, aspect: str, quality: str):
    """OpenAI gpt-image-1 via emergent integration. Fallback to direct key if available."""
    # Map aspect ratio → OpenAI size param
    size_map = {
        "1:1":  "1024x1024",
        "16:9": "1536x1024",
        "9:16": "1024x1536",
        "4:5":  "1024x1280",
    }
    size = size_map.get(aspect, "1024x1024")
    quality_param = "high" if quality == "premium" else "medium"

    # Try direct user key first (cleaner billing)
    direct_key = os.environ.get("OPENAI_DIRECT_KEY", "").strip()
    if direct_key:
        try:
            from openai import AsyncOpenAI
            import base64 as _b64
            client = AsyncOpenAI(api_key=direct_key)
            resp = await client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size=size,
                quality=quality_param,
                n=1,
            )
            if resp.data and resp.data[0].b64_json:
                return _b64.b64decode(resp.data[0].b64_json)
        except Exception as e:
            logger.warning(f"[IMAGE-WIZARD] direct OpenAI failed, trying emergent: {e}")

    # Fallback to emergent integration
    try:
        from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise RuntimeError("no EMERGENT_LLM_KEY")
        gen = OpenAIImageGeneration(api_key=api_key)
        images = await gen.generate_images(
            prompt=prompt,
            model="gpt-image-1",
            number_of_images=1,
            size=size,
            quality=quality_param,
        )
        if images and images[0]:
            return images[0]
    except Exception as e:
        logger.warning(f"[IMAGE-WIZARD] emergent OpenAI image failed: {e}")
        raise
    return None
