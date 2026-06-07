"""
Zitex Free-Build Website Module — fully AI-driven, NO templates.

Philosophy:
    The user does NOT pick from pre-made templates (no "restaurant", "salon", etc.)
    Instead, a specialized "Senior Web Architect" AI conducts a Yes/No interview
    (12-15 binary questions) + 2-3 free-text questions, then synthesizes the answers
    into a unique, single-file HTML+CSS+JS website that reflects the user's
    imagination — never the same twice.

Endpoints:
    POST /api/freebuild/start       — start interview, returns first yes/no Q
    POST /api/freebuild/answer      — submit yes/no answer, returns next Q or 'free_text'
    POST /api/freebuild/free-text   — submit free-text (name, vision)
    POST /api/freebuild/generate    — Claude Sonnet 4.5 generates the full website
    GET  /api/freebuild/projects    — list user's projects
    GET  /api/freebuild/project/{id}
    GET  /api/freebuild/preview/{id} — public HTML preview (text/html)
    PATCH /api/freebuild/project/{id} — rename or refine
    DELETE /api/freebuild/project/{id}

Pricing:
    Generate: 25 credits per website (Claude Sonnet 4.5 reasoning).
    Refine:   10 credits per refinement pass.
"""
from __future__ import annotations
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---- Pricing ----
GENERATE_COST = 25
REFINE_COST = 10

# ---- Yes/No Question Bank ----
# Each question is engineered to extract a strong design signal.
# `dimension` tags are used in the AI synthesis stage to weight the prompt.
QUESTIONS: List[Dict[str, Any]] = [
    {"id": "q_personal", "text": "هل الموقع لشخصك أو علامتك الشخصية (وليس شركة)؟", "dimension": "audience"},
    {"id": "q_dark",     "text": "تبي ثيم داكن (خلفية سوداء/كحلية)؟",                "dimension": "palette"},
    {"id": "q_neon",     "text": "تبي ألوان نيون لامعة (أخضر، بنفسجي، وردي)؟",        "dimension": "palette"},
    {"id": "q_luxury",   "text": "تبي إحساس فخم (ذهبي/أسود/خط Serif)؟",              "dimension": "tone"},
    {"id": "q_minimal",  "text": "تبي تصميم بسيط جداً بمساحات بيضاء واسعة؟",          "dimension": "tone"},
    {"id": "q_animated", "text": "تبي حركات متقدمة (Parallax / scroll-reveal / hover)؟", "dimension": "motion"},
    {"id": "q_3d",       "text": "تبي عناصر ثلاثية الأبعاد أو أشكال هندسية متحركة؟",   "dimension": "motion"},
    {"id": "q_hero_video", "text": "تبي خلفية فيديو في رأس الصفحة؟",                  "dimension": "media"},
    {"id": "q_about",    "text": "تبي قسم \"من نحن\" أو \"عني\"؟",                    "dimension": "section"},
    {"id": "q_services", "text": "تبي قسم خدمات أو منتجات؟",                          "dimension": "section"},
    {"id": "q_portfolio", "text": "تبي معرض أعمال (gallery)؟",                        "dimension": "section"},
    {"id": "q_testimonials", "text": "تبي قسم آراء العملاء؟",                          "dimension": "section"},
    {"id": "q_pricing",  "text": "تبي جدول أسعار/باقات؟",                              "dimension": "section"},
    {"id": "q_contact",  "text": "تبي نموذج تواصل أو زر واتساب؟",                       "dimension": "section"},
    {"id": "q_blog",     "text": "تبي قسم مقالات/مدوّنة؟",                              "dimension": "section"},
    {"id": "q_bilingual", "text": "تبي عربي + إنجليزي (متعدد اللغات)؟",                 "dimension": "i18n"},
    {"id": "q_arabic_only", "text": "تبي عربي فقط (RTL)؟",                              "dimension": "i18n"},
]

FREE_TEXT_QS = [
    {"id": "site_name",   "label": "وش اسم الموقع/المشروع؟ (مثلاً: نور للتصميم)"},
    {"id": "vision",      "label": "اكتب لنا 2-4 جمل عن خيالك للموقع — وش الإحساس اللي تبيه يوصل؟ (المنتج/الخدمة/الجمهور)"},
    {"id": "primary_color", "label": "إذا عندك لون مفضّل اكتبه (مثلاً: ذهبي #D4AF37) — أو اكتب \"اختاره أنت\""},
]


# ---- AI Architect System Prompt ----
ARCHITECT_PROMPT = """You are a Senior Web Architect & Creative Director — an elite freelancer
who designs UNIQUE, BESPOKE, single-file websites. You NEVER use templates. Every site you make
is one-of-a-kind, reflecting the client's exact vision and personality.

Your output rules (NON-NEGOTIABLE):
1. Output ONE complete HTML document — `<!DOCTYPE html>` to `</html>` — embedded CSS in `<style>`, embedded JS in `<script>`.
2. NO external frameworks. NO Bootstrap. NO Tailwind. NO React. Pure handcrafted HTML+CSS+JS.
3. CSS uses MODERN features: CSS variables, `clamp()`, `:has()`, container queries, `@layer`,
   custom properties, `backdrop-filter`, `mask`, `clip-path`, advanced gradients.
4. Animations: `@keyframes`, `view-timeline`/`scroll-timeline` where supported, IntersectionObserver
   for scroll-reveal, smooth easing curves (cubic-bezier).
5. Typography: pick from Google Fonts via `<link>` — match the brand tone.
6. Layout: NEVER center everything. Use asymmetric grids, diagonal cuts, overlapping cards,
   broken layouts, sticky elements. Be creative.
7. Colors: build a deep palette with 5-7 colors — not 2 boring brand colors. Use accents.
8. Imagery: use Unsplash via `https://images.unsplash.com/photo-{ID}?auto=format&fit=crop&w=1600&q=80`
   — pick photo IDs that match the brief (real photographic IDs that exist).
9. RTL: if Arabic-only or bilingual, set `dir="rtl"` and use Arabic Google fonts (Tajawal, Cairo, IBM Plex Sans Arabic, Reem Kufi).
10. SEO: include `<meta name="description">` and Open Graph tags.
11. Mobile-first: use `@media` queries. Touch targets ≥ 44px.
12. Accessibility: ARIA labels, semantic HTML5, proper contrast.
13. The result must look like it was hand-crafted by a $20K-budget agency — NOT like a template.

Forbidden:
- "Lorem ipsum" — write real Arabic copy that fits the brief.
- Generic stock phrases like "Welcome to our website".
- Boring centered hero with one button.
- Identical card grids.
- Default browser fonts.

Output ONLY the full HTML — no markdown fences, no explanation, no preamble."""


# ---- Pydantic Models ----

class FreeBuildStartIn(BaseModel):
    pass


class FreeBuildAnswerIn(BaseModel):
    session_id: str
    question_id: str
    answer: bool  # True=yes, False=no


class FreeBuildFreeTextIn(BaseModel):
    session_id: str
    field_id: str
    value: str = Field(..., min_length=1, max_length=600)


class FreeBuildGenerateIn(BaseModel):
    session_id: str


class FreeBuildRefineIn(BaseModel):
    project_id: str
    instruction: str = Field(..., min_length=4, max_length=500)


class FreeBuildRenameIn(BaseModel):
    project_id: str
    name: str = Field(..., min_length=1, max_length=80)


# ---- Helpers ----

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_brief(answers_yn: Dict[str, bool], free_text: Dict[str, str]) -> str:
    """Convert raw answers into a richly-worded brief for the architect AI."""
    yn = answers_yn
    site_name = free_text.get("site_name", "موقع جديد")
    vision = free_text.get("vision", "")
    color = free_text.get("primary_color", "")

    audience = "شخصي / علامة شخصية" if yn.get("q_personal") else "شركة / مشروع تجاري"

    palette_hints = []
    if yn.get("q_dark"):
        palette_hints.append("dark theme (deep black/navy backgrounds)")
    if yn.get("q_neon"):
        palette_hints.append("neon accents (vibrant green/purple/pink glows)")
    if yn.get("q_luxury"):
        palette_hints.append("luxury (gold, ivory, deep charcoal, serif typography like Playfair/Cormorant)")
    if yn.get("q_minimal"):
        palette_hints.append("minimalist with generous whitespace and refined typography")
    if not palette_hints:
        palette_hints.append("balanced modern palette with one strong accent color")

    motion_hints = []
    if yn.get("q_animated"):
        motion_hints.append("rich motion: parallax, scroll-reveal animations, hover micro-interactions")
    if yn.get("q_3d"):
        motion_hints.append("3D-feeling elements: animated geometric shapes, CSS 3D transforms, floating cards")

    media_hints = []
    if yn.get("q_hero_video"):
        media_hints.append("background looped video in the hero (use a relevant Unsplash video or animated gradient as fallback)")

    sections = []
    if yn.get("q_about"):       sections.append("About / من نحن")
    if yn.get("q_services"):    sections.append("Services or Products / خدمات/منتجات")
    if yn.get("q_portfolio"):   sections.append("Portfolio gallery / معرض أعمال")
    if yn.get("q_testimonials"): sections.append("Client testimonials / آراء العملاء")
    if yn.get("q_pricing"):     sections.append("Pricing tiers / باقات الأسعار")
    if yn.get("q_contact"):     sections.append("Contact form + WhatsApp button / تواصل + واتساب")
    if yn.get("q_blog"):        sections.append("Blog / مقالات")
    if not sections:
        sections.append("Hero + brief about + contact (minimal single-page)")

    if yn.get("q_arabic_only"):
        lang_setting = "Arabic only — set dir='rtl' on <html>, use Arabic Google fonts (Tajawal/Cairo/Reem Kufi/IBM Plex Sans Arabic)"
    elif yn.get("q_bilingual"):
        lang_setting = "Bilingual Arabic + English — provide a language switcher button, default to Arabic RTL"
    else:
        lang_setting = "Arabic primary (RTL) with optional English subtitles where appropriate"

    color_block = f"User's preferred primary color: {color}" if color and "اختاره" not in color else "Choose a sophisticated primary color that matches the brand vision."

    brief = f"""## CLIENT BRIEF

**Site Name:** {site_name}
**Audience type:** {audience}
**User's vision (verbatim):** {vision}

### Design Direction
- Palette: {", ".join(palette_hints)}.
- Motion: {", ".join(motion_hints) if motion_hints else "subtle tasteful transitions"}.
- Hero media: {", ".join(media_hints) if media_hints else "still hero with a striking visual composition"}.
- Color: {color_block}

### Required Sections (in this order)
{chr(10).join(f"- {s}" for s in sections)}

### Language / Direction
{lang_setting}

### Critical Constraints
- This site MUST NOT look like a template. It must reflect THIS specific user's vision uniquely.
- Use the site name "{site_name}" prominently.
- Write actual real Arabic copy that matches the vision (not Lorem Ipsum).
- Build a memorable hero — surprise the visitor in the first 2 seconds.
- Include a footer with copyright and a small "{site_name} © " line.
- Output the FULL HTML document only.
"""
    return brief


async def _generate_html_with_claude(brief: str) -> str:
    """Call OpenAI gpt-4o (user's DIRECT API key) with the architect prompt + brief.
    Returns the raw HTML string. Raises on failure.

    Routes through Zitex AI Smart Router → picks the BEST model for website-build task
    (Kimi K2.6 → DeepSeek → Claude Sonnet → GPT-4o). Auto fallback if any provider fails.
    """
    # NEW: route through unified Zitex AI layer with boundaries
    try:
        from modules.zitex_ai import zitex_chat
        result = await zitex_chat(
            agent="freebuild",
            messages=[{"role": "user", "content": brief}],
            override_system=ARCHITECT_PROMPT,  # FreeBuild has its own detailed architect prompt
        )
        if result.get("ok"):
            out = result.get("content", "")
        else:
            raise RuntimeError(f"zitex_chat failed: {result.get('error')}")
    except Exception as e:
        # Fallback to legacy direct call
        direct_key = os.environ.get("OPENAI_DIRECT_KEY", "").strip()
        if not direct_key:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            api_key = os.environ.get("EMERGENT_LLM_KEY")
            if not api_key:
                raise RuntimeError("No LLM key available")
            chat = LlmChat(api_key=api_key, session_id=f"fb-{uuid.uuid4()}", system_message=ARCHITECT_PROMPT)
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            out = await chat.send_message(UserMessage(text=brief))
        else:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=direct_key)
            resp = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": ARCHITECT_PROMPT},
                    {"role": "user", "content": brief},
                ],
                temperature=0.85,
                max_tokens=8000,
            )
            out = (resp.choices[0].message.content or "")

    text = (out or "").strip()
    # Strip accidental markdown fences if AI ignored instructions
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    if "<html" not in text.lower():
        raise RuntimeError("AI did not return valid HTML")
    return text


# ---- Router factory ----

def create_freebuild_router(db, get_current_user) -> APIRouter:
    router = APIRouter(prefix="/api/freebuild", tags=["freebuild"])

    async def _credits(uid: str) -> int:
        u = await db.users.find_one({"id": uid}, {"_id": 0, "credits": 1})
        return int((u or {}).get("credits", 0) or 0)

    async def _deduct(uid: str, amount: int, reason: str) -> bool:
        r = await db.users.update_one(
            {"id": uid, "credits": {"$gte": amount}},
            {"$inc": {"credits": -amount},
             "$push": {"credit_history": {"amount": -amount, "reason": reason, "timestamp": _now()}}}
        )
        return r.modified_count > 0

    async def _refund(uid: str, amount: int, reason: str):
        await db.users.update_one(
            {"id": uid},
            {"$inc": {"credits": amount},
             "$push": {"credit_history": {"amount": amount, "reason": reason, "timestamp": _now()}}}
        )

    # ===== Question catalog (public) =====
    @router.get("/catalog")
    async def catalog():
        return {
            "questions_count": len(QUESTIONS),
            "free_text_fields": FREE_TEXT_QS,
            "generate_cost": GENERATE_COST,
            "refine_cost": REFINE_COST,
        }

    # ===== Start interview =====
    @router.post("/start")
    async def start(_: FreeBuildStartIn, user=Depends(get_current_user)):
        sid = str(uuid.uuid4())
        await db.freebuild_sessions.insert_one({
            "id": sid,
            "user_id": user["user_id"],
            "step": 0,
            "yn_answers": {},
            "free_text": {},
            "phase": "yn",  # 'yn' | 'free_text' | 'ready' | 'generating' | 'done'
            "created_at": _now(),
        })
        first = QUESTIONS[0]
        return {
            "session_id": sid,
            "phase": "yn",
            "step": 1,
            "total_yn": len(QUESTIONS),
            "question": {"id": first["id"], "text": first["text"], "kind": "yes_no"},
        }

    # ===== Submit yes/no =====
    @router.post("/answer")
    async def answer(payload: FreeBuildAnswerIn, user=Depends(get_current_user)):
        sess = await db.freebuild_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not sess:
            raise HTTPException(404, "session not found")
        if sess.get("phase") != "yn":
            raise HTTPException(400, "interview already past Y/N stage")

        step = sess.get("step", 0)
        if step >= len(QUESTIONS):
            raise HTTPException(400, "no more yn questions")

        expected = QUESTIONS[step]["id"]
        if payload.question_id != expected:
            raise HTTPException(400, f"unexpected question_id (expected {expected})")

        yn = dict(sess.get("yn_answers") or {})
        yn[payload.question_id] = bool(payload.answer)

        new_step = step + 1
        if new_step < len(QUESTIONS):
            await db.freebuild_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"yn_answers": yn, "step": new_step}}
            )
            nxt = QUESTIONS[new_step]
            return {
                "phase": "yn",
                "step": new_step + 1,
                "total_yn": len(QUESTIONS),
                "question": {"id": nxt["id"], "text": nxt["text"], "kind": "yes_no"},
            }

        # Done with yn → free_text phase
        await db.freebuild_sessions.update_one(
            {"id": payload.session_id},
            {"$set": {"yn_answers": yn, "step": new_step, "phase": "free_text"}}
        )
        first_ft = FREE_TEXT_QS[0]
        return {
            "phase": "free_text",
            "field": first_ft,
            "free_text_total": len(FREE_TEXT_QS),
            "free_text_index": 1,
        }

    # ===== Submit free text =====
    @router.post("/free-text")
    async def free_text(payload: FreeBuildFreeTextIn, user=Depends(get_current_user)):
        sess = await db.freebuild_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not sess:
            raise HTTPException(404, "session not found")
        if sess.get("phase") not in ("free_text",):
            raise HTTPException(400, "not in free_text phase")

        valid_ids = {q["id"] for q in FREE_TEXT_QS}
        if payload.field_id not in valid_ids:
            raise HTTPException(400, "invalid field_id")

        ft = dict(sess.get("free_text") or {})
        ft[payload.field_id] = payload.value.strip()

        # find next un-answered field in order
        next_field = None
        for q in FREE_TEXT_QS:
            if q["id"] not in ft:
                next_field = q
                break

        if next_field:
            await db.freebuild_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"free_text": ft}}
            )
            answered = sum(1 for q in FREE_TEXT_QS if q["id"] in ft)
            return {
                "phase": "free_text",
                "field": next_field,
                "free_text_total": len(FREE_TEXT_QS),
                "free_text_index": answered + 1,
            }

        # All free text answered → ready
        credits = await _credits(user["user_id"])
        await db.freebuild_sessions.update_one(
            {"id": payload.session_id},
            {"$set": {"free_text": ft, "phase": "ready"}}
        )
        return {
            "phase": "ready",
            "estimated_cost": GENERATE_COST,
            "credits_balance": credits,
            "can_afford": credits >= GENERATE_COST,
            "summary": {
                "yn_answers": sess.get("yn_answers") or {},
                "free_text": ft,
            },
        }

    # ===== Generate website =====
    @router.post("/generate")
    async def generate(payload: FreeBuildGenerateIn, user=Depends(get_current_user)):
        sess = await db.freebuild_sessions.find_one(
            {"id": payload.session_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not sess:
            raise HTTPException(404, "session not found")
        if sess.get("phase") not in ("ready",):
            raise HTTPException(400, "session not ready (complete the interview first)")

        # Deduct credits atomically
        ok = await _deduct(user["user_id"], GENERATE_COST, "freebuild_generate")
        if not ok:
            raise HTTPException(402, f"رصيدك ما يكفي ({GENERATE_COST} نقطة مطلوبة)")

        # Mark generating
        await db.freebuild_sessions.update_one(
            {"id": payload.session_id},
            {"$set": {"phase": "generating", "generation_started_at": _now()}}
        )

        try:
            yn = sess.get("yn_answers") or {}
            ft = sess.get("free_text") or {}
            brief = _build_brief(yn, ft)
            html = await _generate_html_with_claude(brief)

            project_id = str(uuid.uuid4())
            slug = ft.get("site_name", "site").strip().replace(" ", "-").lower()[:40] or "site"
            project = {
                "id": project_id,
                "user_id": user["user_id"],
                "session_id": payload.session_id,
                "name": ft.get("site_name", "موقعي"),
                "slug": f"{slug}-{project_id[:6]}",
                "html": html,
                "brief": brief,
                "yn_answers": yn,
                "free_text": ft,
                "credits_spent": GENERATE_COST,
                "version": 1,
                "history": [{"version": 1, "html": html, "created_at": _now(), "instruction": "initial"}],
                "created_at": _now(),
                "updated_at": _now(),
            }
            await db.freebuild_projects.insert_one(project.copy())
            await db.freebuild_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"phase": "done", "project_id": project_id}}
            )
            project.pop("_id", None)
            project.pop("history", None)  # heavy field, omit from response
            return {
                "ok": True,
                "project": project,
                "preview_url": f"/api/freebuild/preview/{project_id}",
                "credits_remaining": await _credits(user["user_id"]),
            }
        except Exception as e:
            await _refund(user["user_id"], GENERATE_COST, f"refund_freebuild_failed: {str(e)[:80]}")
            await db.freebuild_sessions.update_one(
                {"id": payload.session_id},
                {"$set": {"phase": "ready", "last_error": str(e)[:200]}}
            )
            logger.exception(f"[FREEBUILD] generate failed: {e}")
            raise HTTPException(500, f"فشل توليد الموقع. تمت إعادة النقاط. ({str(e)[:120]})")

    # ===== List user projects =====
    @router.get("/projects")
    async def list_projects(user=Depends(get_current_user)):
        cursor = db.freebuild_projects.find(
            {"user_id": user["user_id"]},
            {"_id": 0, "html": 0, "history": 0, "brief": 0}
        ).sort("created_at", -1)
        items = await cursor.to_list(length=100)
        return {"projects": items, "count": len(items)}

    # ===== Get one project (auth, full payload) =====
    @router.get("/project/{project_id}")
    async def get_project(project_id: str, user=Depends(get_current_user)):
        p = await db.freebuild_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"_id": 0, "history": 0}
        )
        if not p:
            raise HTTPException(404, "project not found")
        return p

    # ===== Public preview (HTML response) =====
    @router.get("/preview/{project_id}")
    async def preview(project_id: str):
        p = await db.freebuild_projects.find_one(
            {"id": project_id}, {"_id": 0, "html": 1}
        )
        if not p or not p.get("html"):
            raise HTTPException(404, "preview not found")
        return Response(content=p["html"], media_type="text/html; charset=utf-8")

    # ===== Refine (re-generate with extra instructions) =====
    @router.post("/refine")
    async def refine(payload: FreeBuildRefineIn, user=Depends(get_current_user)):
        p = await db.freebuild_projects.find_one(
            {"id": payload.project_id, "user_id": user["user_id"]}, {"_id": 0}
        )
        if not p:
            raise HTTPException(404, "project not found")

        ok = await _deduct(user["user_id"], REFINE_COST, "freebuild_refine")
        if not ok:
            raise HTTPException(402, f"رصيدك ما يكفي ({REFINE_COST} نقطة مطلوبة)")

        try:
            current_html = p.get("html", "")
            instruction = payload.instruction.strip()
            refine_brief = f"""## REFINEMENT REQUEST

You previously built a website. The client now wants this specific change:

**User's instruction (verbatim):**
{instruction}

**The current full HTML is below. Apply the requested change while preserving everything else
that wasn't asked to change. Keep the same overall structure unless the instruction explicitly
asks for a redesign. Output the FULL updated HTML only — no markdown, no commentary.**

---CURRENT HTML---
{current_html}
---END CURRENT HTML---
"""
            new_html = await _generate_html_with_claude(refine_brief)
            new_version = int(p.get("version", 1)) + 1
            history = list(p.get("history") or [])
            history.append({
                "version": new_version,
                "html": new_html,
                "instruction": instruction,
                "created_at": _now(),
            })
            # Cap history to last 10 versions
            history = history[-10:]

            await db.freebuild_projects.update_one(
                {"id": payload.project_id},
                {"$set": {
                    "html": new_html,
                    "version": new_version,
                    "history": history,
                    "updated_at": _now(),
                }}
            )
            return {
                "ok": True,
                "version": new_version,
                "credits_remaining": await _credits(user["user_id"]),
                "preview_url": f"/api/freebuild/preview/{payload.project_id}",
            }
        except Exception as e:
            await _refund(user["user_id"], REFINE_COST, f"refund_freebuild_refine: {str(e)[:80]}")
            logger.exception(f"[FREEBUILD] refine failed: {e}")
            raise HTTPException(500, f"فشل التحديث. تمت إعادة النقاط. ({str(e)[:120]})")

    # ===== Rename =====
    @router.patch("/project/{project_id}")
    async def rename(project_id: str, payload: FreeBuildRenameIn, user=Depends(get_current_user)):
        if payload.project_id != project_id:
            raise HTTPException(400, "id mismatch")
        r = await db.freebuild_projects.update_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"$set": {"name": payload.name.strip(), "updated_at": _now()}}
        )
        if r.matched_count == 0:
            raise HTTPException(404, "project not found")
        return {"ok": True}

    # ===== Delete =====
    @router.delete("/project/{project_id}")
    async def delete_project(project_id: str, user=Depends(get_current_user)):
        r = await db.freebuild_projects.delete_one(
            {"id": project_id, "user_id": user["user_id"]}
        )
        if r.deleted_count == 0:
            raise HTTPException(404, "project not found")
        return {"ok": True}

    return router
