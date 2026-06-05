"""
🎮 Game Studio Router v3.0 — Professional Game Development Workflow

✨ NEW FEATURES:
  • Programming Type Selection (Flutter, Native Android/iOS, React Native, Unity, HTML5)
  • Live Preview URL for each stage
  • Asset Storage with approval system
  • Memory system — AI remembers approved assets
  • Professional AI prompts for actual code generation

📋 Workflow:
  Web Games: 8 phases (Discovery → Deployment)
  App Games: 9 phases (Discovery → Store Publishing)
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone
import logging
import os
import httpx
import base64
import json

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 🎯 Programming Types
# ═══════════════════════════════════════════════════════════════
PROGRAMMING_TYPES = {
    "web": [
        {"id": "html5_canvas", "name": "HTML5 Canvas (Pure)", "desc": "رسم مباشر بدون مكتبات"},
        {"id": "phaser", "name": "Phaser.js", "desc": "محرك ألعاب 2D احترافي"},
        {"id": "threejs", "name": "Three.js", "desc": "ألعاب 3D في المتصفح"},
        {"id": "unity_webgl", "name": "Unity WebGL", "desc": "تصدير من Unity للويب"},
        {"id": "custom", "name": "Custom Framework", "desc": "إطار عمل خاص"}
    ],
    "app": [
        {"id": "flutter", "name": "Flutter", "desc": "تطبيق واحد لـ Android + iOS"},
        {"id": "native_android", "name": "Native Android (Kotlin)", "desc": "Android فقط"},
        {"id": "native_ios", "name": "Native iOS (Swift)", "desc": "iOS فقط"},
        {"id": "react_native", "name": "React Native", "desc": "JavaScript لكلا المنصتين"},
        {"id": "unity", "name": "Unity", "desc": "محرك ألعاب احترافي"},
        {"id": "godot", "name": "Godot", "desc": "محرك مفتوح المصدر"}
    ]
}

# ═══════════════════════════════════════════════════════════════
# 🎯 Phase Definitions (Web Games)
# ═══════════════════════════════════════════════════════════════
WEB_GAME_PHASES = [
    {
        "id": "discovery",
        "title": "🔍 Discovery & GDD",
        "description": "فهم الفكرة + كتابة Game Design Document",
        "credits": 50,
        "deliverables": ["GDD.md", "Genre", "Target Audience", "Core Mechanics"],
        "requires_approval": True
    },
    {
        "id": "mechanics",
        "title": "⚙️ Core Mechanics Design",
        "description": "تصميم آليات اللعب الأساسية",
        "credits": 100,
        "deliverables": ["Mechanics Doc", "Flowchart", "Prototype Sketch"],
        "requires_approval": True
    },
    {
        "id": "characters",
        "title": "🎭 Character Design",
        "description": "تصميم الشخصيات (مظهر، قدرات، animations)",
        "credits": 150,
        "deliverables": ["Character Sheets", "Concept Art", "Sprite Assets"],
        "requires_approval": True,
        "asset_type": "characters"
    },
    {
        "id": "environment",
        "title": "🏞️ Environment Design",
        "description": "تصميم البيئات (خلفيات، tiles، obstacles)",
        "credits": 200,
        "deliverables": ["Environment Sketches", "Tileset", "Background Assets"],
        "requires_approval": True,
        "asset_type": "environments"
    },
    {
        "id": "assets",
        "title": "🎨 Assets Generation",
        "description": "توليد كل الأصول (UI, sounds, effects)",
        "credits": 100,
        "deliverables": ["UI Kit", "Sound Effects", "Visual Effects"],
        "requires_approval": True,
        "asset_type": "ui"
    },
    {
        "id": "programming",
        "title": "💻 Programming & Integration",
        "description": "برمجة اللعبة + تكامل الأصول",
        "credits": 300,
        "deliverables": ["Playable Build", "Source Code", "Documentation"],
        "requires_approval": False,
        "asset_type": "code",
        "generates_preview": True
    },
    {
        "id": "testing",
        "title": "🧪 Testing & QA",
        "description": "اختبار شامل + إصلاح bugs",
        "credits": 100,
        "deliverables": ["Test Report", "Bug Fixes", "Performance Optimization"],
        "requires_approval": False
    },
    {
        "id": "deployment",
        "title": "🚀 Deployment & Delivery",
        "description": "نشر اللعبة + تسليم نهائي",
        "credits": 150,
        "deliverables": ["Live Game URL", "Source Package", "User Guide"],
        "requires_approval": False,
        "generates_preview": True
    }
]

# ═══════════════════════════════════════════════════════════════
# 🎯 Phase Definitions (App Games)
# ═══════════════════════════════════════════════════════════════
APP_GAME_PHASES = [
    {
        "id": "discovery",
        "title": "🔍 Discovery & GDD",
        "description": "فهم الفكرة + Game Design Document",
        "credits": 80,
        "deliverables": ["GDD.md", "Platform Choice", "Monetization Strategy"],
        "requires_approval": True
    },
    {
        "id": "architecture",
        "title": "🏗️ Architecture & Tech Stack",
        "description": "اختيار المحرك + بنية المشروع",
        "credits": 120,
        "deliverables": ["Tech Stack Doc", "Project Structure", "Dependencies"],
        "requires_approval": True
    },
    {
        "id": "mechanics",
        "title": "⚙️ Core Mechanics Design",
        "description": "تصميم آليات اللعب",
        "credits": 150,
        "deliverables": ["Mechanics Doc", "Flowchart", "Prototype"],
        "requires_approval": True
    },
    {
        "id": "characters",
        "title": "🎭 Character Design",
        "description": "تصميم الشخصيات",
        "credits": 200,
        "deliverables": ["Character Sheets", "3D Models", "Animations"],
        "requires_approval": True,
        "asset_type": "characters"
    },
    {
        "id": "environment",
        "title": "🏞️ Environment Design",
        "description": "تصميم البيئات",
        "credits": 250,
        "deliverables": ["Environment Sketches", "3D Assets", "Lighting Setup"],
        "requires_approval": True,
        "asset_type": "environments"
    },
    {
        "id": "assets",
        "title": "🎨 Assets & UI",
        "description": "توليد UI + sound + effects",
        "credits": 150,
        "deliverables": ["UI Mockups", "Sound Library", "Particle Effects"],
        "requires_approval": True,
        "asset_type": "ui"
    },
    {
        "id": "programming",
        "title": "💻 Programming & Integration",
        "description": "برمجة التطبيق + تكامل",
        "credits": 400,
        "deliverables": ["APK/IPA Build", "Source Code", "Documentation"],
        "requires_approval": False,
        "asset_type": "code",
        "generates_preview": True
    },
    {
        "id": "testing",
        "title": "🧪 Testing & QA",
        "description": "اختبار شامل",
        "credits": 150,
        "deliverables": ["Test Report", "Bug Fixes", "Performance"],
        "requires_approval": False
    },
    {
        "id": "publishing",
        "title": "📱 Store Publishing",
        "description": "نشر على Play Store / App Store",
        "credits": 200,
        "deliverables": ["Store Listing", "Screenshots", "Published APK/IPA"],
        "requires_approval": False,
        "generates_preview": True
    }
]

# ═══════════════════════════════════════════════════════════════
# 🎯 Pydantic Models
# ═══════════════════════════════════════════════════════════════
class ProjectCreate(BaseModel):
    game_type: str  # "web" or "app"
    title: str
    description: str
    programming_type: str  # from PROGRAMMING_TYPES

class ChatMessage(BaseModel):
    message: str
    phase_id: Optional[str] = None

class AssetApproval(BaseModel):
    asset_id: str
    approved: bool
    feedback: Optional[str] = None

# ═══════════════════════════════════════════════════════════════
# 🧠 Async helper — auto-refresh AI notes/GDD in the background
# ═══════════════════════════════════════════════════════════════
async def _auto_refresh_notes(db, project_id: str):
    """Regenerate the project's AI memory/GDD from full chat history.
    Called as a background asyncio task after every few messages so the user
    can see a live-updating Game Design Document in the "ذاكرة AI" tab.
    """
    try:
        project = await db.game_projects.find_one({"id": project_id})
        if not project:
            return
        all_msgs = []
        for ph_id, ph in (project.get("phases") or {}).items():
            for m in (ph.get("messages") or [])[-20:]:
                all_msgs.append(
                    f"[{ph_id}] U: {(m.get('user') or '')[:200]}\nA: {(m.get('assistant') or '')[:400]}"
                )
        chat_digest = "\n\n".join(all_msgs[-30:])
        if not chat_digest:
            return
        summary_prompt = (
            "أنت محرر فني لمشروع لعبة. اقرأ محادثة المالك مع AI واكتب ملخصاً مفصّلاً ومستديماً "
            "(Living Project Memory / Game Design Document) بصيغة Markdown يضم: الرؤية العامة، "
            "نوع اللعبة، الجمهور المستهدف، الـart style المتفق عليه، العناصر المعتمدة (قائمة)، "
            "القرارات الرئيسية، ما تم إنجازه، ما تبقى. اكتبها بضمير المتكلم 'أنا فهمت كذا'. "
            "نقاط مرقّمة، عربية واضحة، حد 1500 كلمة.\n\n"
            f"تفاصيل المشروع:\nالعنوان: {project.get('title','')}\nالوصف: {project.get('description','')}\n\n"
            f"المحادثة:\n{chat_digest[:30000]}"
        )
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        notes = ""
        try:
            if gemini_key:
                async with httpx.AsyncClient(timeout=60.0) as cli:
                    r = await cli.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
                        json={
                            "contents": [{"parts": [{"text": summary_prompt}]}],
                            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 3000},
                        },
                    )
                    if r.status_code == 200:
                        notes = (
                            r.json().get("candidates", [{}])[0]
                            .get("content", {}).get("parts", [{}])[0]
                            .get("text", "")
                        )
            if not notes and anthropic_key:
                async with httpx.AsyncClient(timeout=60.0) as cli:
                    r = await cli.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": anthropic_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json={
                            "model": "claude-sonnet-4-5-20250929",
                            "max_tokens": 3000,
                            "messages": [{"role": "user", "content": summary_prompt}],
                        },
                    )
                    if r.status_code == 200:
                        blocks = r.json().get("content", [])
                        notes = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except Exception as llm_err:
            logger.warning(f"[games][auto-notes] LLM call failed: {llm_err}")
            return
        if notes:
            await db.game_projects.update_one(
                {"id": project_id},
                {"$set": {"ai_notes": notes, "notes_updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            logger.info(f"[games][auto-notes] refreshed notes for project {project_id} ({len(notes)} chars)")
    except Exception as e:
        logger.warning(f"[games][auto-notes] background refresh failed: {e}")


# ═══════════════════════════════════════════════════════════════
# 📚 Async helper — Auto-extract & store a lesson learned from each
# game-studio exchange. Reuses the AutoCoder learning journal so all
# AI sub-systems share one growing brain visible at /admin/learning.
# ═══════════════════════════════════════════════════════════════
async def _auto_learn_from_exchange(
    db,
    project_id: str,
    project_title: str,
    game_type: str,
    user_msg: str,
    ai_msg: str,
    actor_id: str,
    had_uploads: bool,
):
    """Decide if this exchange contains a teachable signal; if yes, store
    a concise lesson in `autocoder_lessons` so it appears in the admin
    learning dashboard alongside AutoCoder's own lessons."""
    try:
        if not user_msg or not ai_msg or len(user_msg.strip()) < 5:
            return
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        # Lightweight prompt — ask LLM to either extract a lesson or say "skip"
        meta_prompt = (
            "أنت محرر يبني journal تعلم لمساعد AI يبني ألعاب. "
            "اقرأ تبادل المالك مع AI. لو فيه درس مفيد للمستقبل (تفضيل بصري، نمط أخطاء، "
            "أسلوب يحبه المالك، خطوة سير عمل ذكية)، استخرج درساً واحداً قصيراً. لو لا، رد \"SKIP\".\n\n"
            f"السياق: {game_type} game studio | المشروع: {project_title}\n"
            f"المالك رفع صور مرجعية؟ {'نعم' if had_uploads else 'لا'}\n\n"
            f"رسالة المالك: {user_msg[:800]}\n\n"
            f"رد AI: {ai_msg[:1500]}\n\n"
            "أجب بـ JSON فقط:\n"
            "{\"skip\": true} → لو ما فيه درس\n"
            "{\"skip\": false, \"summary\": \"≤120 حرف وصف للسياق\", \"lesson\": \"≤300 حرف الدرس بالعربي\", \"tags\": [\"game-studio\", \"web\" أو \"app\", بقية tags]} → لو فيه درس"
        )
        raw = ""
        try:
            if gemini_key:
                async with httpx.AsyncClient(timeout=40.0) as cli:
                    r = await cli.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
                        json={
                            "contents": [{"parts": [{"text": meta_prompt}]}],
                            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400, "responseMimeType": "application/json"},
                        },
                    )
                    if r.status_code == 200:
                        raw = (r.json().get("candidates", [{}])[0]
                               .get("content", {}).get("parts", [{}])[0]
                               .get("text", ""))
            if not raw and anthropic_key:
                async with httpx.AsyncClient(timeout=40.0) as cli:
                    r = await cli.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                        json={
                            "model": "claude-sonnet-4-5-20250929",
                            "max_tokens": 400,
                            "messages": [{"role": "user", "content": meta_prompt}],
                        },
                    )
                    if r.status_code == 200:
                        blocks = r.json().get("content", [])
                        raw = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except Exception as le:
            logger.warning(f"[games][auto-learn] LLM call failed: {le}")
            return
        if not raw:
            return
        import json as _json
        import re as _re
        # Strip potential ```json fences
        cleaned = _re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=_re.MULTILINE).strip()
        try:
            parsed = _json.loads(cleaned)
        except Exception:
            return
        if parsed.get("skip"):
            return
        summary = (parsed.get("summary") or "").strip()
        lesson = (parsed.get("lesson") or "").strip()
        if not summary or not lesson:
            return
        tags = parsed.get("tags") or []
        if not isinstance(tags, list):
            tags = []
        tags = [str(t)[:30] for t in tags][:8]
        if "game-studio" not in tags:
            tags.append("game-studio")
        if game_type and game_type not in tags:
            tags.append(game_type)
        # Store
        try:
            from modules.autocoder.learning import add_lesson
            await add_lesson(
                task_summary=summary[:400],
                lesson=lesson[:1200],
                source="user",
                actor_id=actor_id,
                tags=tags,
            )
            logger.info(f"[games][auto-learn] stored lesson for project {project_id} | tags={tags}")
        except Exception as se:
            logger.warning(f"[games][auto-learn] store failed: {se}")
    except Exception as e:
        logger.warning(f"[games][auto-learn] background exception: {e}")


# ═══════════════════════════════════════════════════════════════
# 🚀 Async helper — run the live-site build off-thread so the HTTP
# request returns immediately (LLM builds can take 60-180s).
# ═══════════════════════════════════════════════════════════════
async def _auto_vision_verify(db, project_id: str, asset_id: str, image_bytes: bytes, prompt: str):
    """Have Claude SEE the generated image and verify it matches the prompt.
    Stores a `verification` dict on the asset:
      { match: 0-100, issues: [str], suggestions: [str], analyzed_at: iso }
    Owner can read it from the asset dict on the frontend (warning badge if match<70).
    """
    try:
        import base64 as _b64v
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not anthropic_key or not prompt or not image_bytes:
            return
        b64 = _b64v.b64encode(image_bytes).decode()
        review_prompt = (
            "أنت art director محترف. هذه صورة ولّدها AI بناءً على الـ prompt التالي:\n"
            f"\"{prompt[:600]}\"\n\n"
            "افحص الصورة فحص دقيق وأرجع JSON فقط (بدون markdown fences):\n"
            "{\n"
            '  "match": رقم 0-100 يمثل نسبة مطابقة الصورة للـ prompt,\n'
            '  "issues": ["مشكلة 1", "مشكلة 2"] حد أقصى 4 — أي خلل بصري أو فني أو منطقي،\n'
            '  "suggestions": ["اقتراح إعادة توليد دقيق 1", "..."] حد أقصى 3,\n'
            '  "verdict": "✅ ممتاز" أو "⚠️ تعديل ينصح به" أو "❌ يلزم إعادة توليد"\n'
            "}\n"
            "كن صارم: لو فيه يد فيها 6 أصابع، أو عمارة عائمة، أو نص محرّف، أو نسب جسم غلط، اذكرها."
        )
        async with httpx.AsyncClient(timeout=60.0) as cli:
            r = await cli.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-5-20250929",
                    "max_tokens": 600,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                            {"type": "text", "text": review_prompt},
                        ],
                    }],
                },
            )
            if r.status_code != 200:
                return
            blocks = r.json().get("content", [])
            raw = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        import json as _json_v
        import re as _re_v
        cleaned = _re_v.sub(r"^```(?:json)?|```$", "", raw, flags=_re_v.MULTILINE).strip()
        try:
            parsed = _json_v.loads(cleaned)
        except Exception:
            return
        verification = {
            "match": int(parsed.get("match") or 0),
            "issues": parsed.get("issues") or [],
            "suggestions": parsed.get("suggestions") or [],
            "verdict": parsed.get("verdict") or "",
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        # Find and patch the asset inside the assets.images bucket
        proj = await db.game_projects.find_one({"id": project_id}, {"assets.images": 1})
        if not proj:
            return
        imgs = (proj.get("assets") or {}).get("images") or []
        patched = False
        for a in imgs:
            if a.get("id") == asset_id:
                a["verification"] = verification
                patched = True
                break
        if patched:
            await db.game_projects.update_one(
                {"id": project_id},
                {"$set": {"assets.images": imgs}},
            )
            logger.info(f"[games][vision-verify] asset={asset_id} match={verification['match']}")
    except Exception as e:
        logger.warning(f"[games][vision-verify] background exception: {e}")


async def _run_build_in_background(db, project_id: str, requester_id: str):
    try:
        from modules.games.builder import build_and_deploy
        result = await build_and_deploy(db, project_id, requester_id)
        if result.get("ok"):
            await db.game_projects.update_one(
                {"id": project_id},
                {"$set": {"build_status": "ready", "build_error": None}},
            )
            logger.info(f"[games][build] success project={project_id} size={result.get('size_bytes')}")
        else:
            await db.game_projects.update_one(
                {"id": project_id},
                {"$set": {"build_status": "error", "build_error": result.get("error") or "unknown"}},
            )
            logger.warning(f"[games][build] failure project={project_id} err={result.get('error')}")
    except Exception as e:
        await db.game_projects.update_one(
            {"id": project_id},
            {"$set": {"build_status": "error", "build_error": str(e)[:300]}},
        )
        logger.error(f"[games][build] exception project={project_id}: {e}")


# ═══════════════════════════════════════════════════════════════
# 🔬 Async helper — QA analysis of the built HTML (Claude)
# ═══════════════════════════════════════════════════════════════
async def _run_qa_in_background(db, project_id: str):
    try:
        from modules.games.builder import load_bundle_html
        html = await load_bundle_html(db, project_id)
        if not html:
            await db.game_projects.update_one(
                {"id": project_id},
                {"$set": {"qa_status": "error", "qa_error": "No build yet — click 'ابني وانشر اللايف' first."}},
            )
            return
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not anthropic_key:
            await db.game_projects.update_one(
                {"id": project_id},
                {"$set": {"qa_status": "error", "qa_error": "Anthropic key not configured"}},
            )
            return
        review_prompt = (
            "أنت QA Lead محترف. اقرأ HTML اللعبة وأعطني تقرير QA بالعربية فيه:\n"
            "1) ✅ نقاط القوة (3 نقاط)\n"
            "2) 🐛 أخطاء/مشاكل محتملة (مع شرح كيف نصلحها)\n"
            "3) ⚡ تحسينات الأداء (lazy load، z-index، DOM size، CSS الزائد)\n"
            "4) ♿ accessibility (alt texts، aria-labels، keyboard nav)\n"
            "5) 📱 responsiveness (هل يشتغل صح على mobile؟)\n"
            "6) 🎯 توصيات نهائية مرتبة بالأولوية.\n"
            "اكتب التقرير بـ Markdown. حد ٢٠٠٠ كلمة.\n\n"
            f"═══ HTML للمراجعة (حجم: {len(html.encode('utf-8'))} bytes) ═══\n"
            f"{html[:60000]}"
        )
        async with httpx.AsyncClient(timeout=240.0) as cli:
            r = await cli.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-5-20250929",
                    "max_tokens": 3000,
                    "messages": [{"role": "user", "content": review_prompt}],
                },
            )
            if r.status_code != 200:
                await db.game_projects.update_one(
                    {"id": project_id},
                    {"$set": {"qa_status": "error", "qa_error": f"Claude HTTP {r.status_code}"}},
                )
                return
            blocks = r.json().get("content", [])
            report = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        await db.game_projects.update_one(
            {"id": project_id},
            {"$set": {
                "qa_status": "ready",
                "qa_error": None,
                "last_qa_report": report,
                "last_qa_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        logger.info(f"[games][qa] ready project={project_id} report={len(report)} chars")
    except Exception as e:
        await db.game_projects.update_one(
            {"id": project_id},
            {"$set": {"qa_status": "error", "qa_error": str(e)[:300]}},
        )
        logger.error(f"[games][qa] exception project={project_id}: {e}")


# ═══════════════════════════════════════════════════════════════
# 🎯 Router Factory
# ═══════════════════════════════════════════════════════════════
def create_game_router(db, get_current_user):
    router = APIRouter(prefix="/api/games", tags=["games"])
    GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
    
    # ───────────────────────────────────────────────────────────
    # 📋 GET /programming-types — List available tech stacks
    # ───────────────────────────────────────────────────────────
    @router.get("/programming-types")
    async def get_programming_types(game_type: str):
        """Return available programming types for web or app"""
        if game_type not in PROGRAMMING_TYPES:
            raise HTTPException(400, f"Invalid game_type: {game_type}")
        return {"types": PROGRAMMING_TYPES[game_type]}

    # ───────────────────────────────────────────────────────────
    # 🖼️ GET /asset-image/{project_id}/{filename} — serve generated PNG
    # ───────────────────────────────────────────────────────────
    @router.get("/asset-image/{project_id}/{filename}")
    async def serve_asset_image(project_id: str, filename: str):
        """Serve generated game asset image with 3-level persistence fallback:
        local disk → MongoDB GridFS → cdn_url redirect → 404.
        Ensures images survive container redeploys (ephemeral disk on Railway/Vercel).
        """
        from fastapi.responses import FileResponse, Response, RedirectResponse
        from modules.games.persistence import (
            load_bytes as _gridfs_load,
            lookup_asset_in_project as _lookup,
            warm_cache as _warm,
        )
        if "/" in filename or ".." in filename or not filename.endswith(".png"):
            raise HTTPException(400, "Invalid filename")
        path = f"/app/backend/uploads/games/{project_id}/assets/{filename}"
        # 1. Local disk
        if os.path.exists(path):
            return FileResponse(path, media_type="image/png")
        asset_id = filename[:-4]  # strip ".png"
        # 2. GridFS
        data = await _gridfs_load(db, asset_id)
        if data:
            await _warm(path, data)  # repopulate local cache
            return Response(content=data, media_type="image/png")
        # 3. cdn_url redirect (Fal CDN)
        asset = await _lookup(db, project_id, asset_id)
        cdn = (asset or {}).get("cdn_url")
        if cdn:
            return RedirectResponse(url=cdn, status_code=302)
        raise HTTPException(404, "Asset not found")

    @router.get("/asset-3d/{project_id}/{filename}")
    async def serve_asset_3d(project_id: str, filename: str):
        """Serve generated 3D model (.glb) with same 3-level fallback."""
        from fastapi.responses import FileResponse, Response, RedirectResponse
        from modules.games.persistence import (
            load_bytes as _gridfs_load,
            lookup_asset_in_project as _lookup,
            warm_cache as _warm,
        )
        if "/" in filename or ".." in filename or not filename.endswith(".glb"):
            raise HTTPException(400, "Invalid filename")
        path = f"/app/backend/uploads/games/{project_id}/3d/{filename}"
        if os.path.exists(path):
            return FileResponse(path, media_type="model/gltf-binary")
        asset_id = filename[:-4]
        data = await _gridfs_load(db, asset_id)
        if data:
            await _warm(path, data)
            return Response(content=data, media_type="model/gltf-binary")
        asset = await _lookup(db, project_id, asset_id)
        cdn = (asset or {}).get("cdn_url")
        if cdn:
            return RedirectResponse(url=cdn, status_code=302)
        raise HTTPException(404, "3D model not found")

    @router.get("/asset-video/{project_id}/{filename}")
    async def serve_asset_video(project_id: str, filename: str):
        """Serve generated video (.mp4) with same 3-level fallback."""
        from fastapi.responses import FileResponse, Response, RedirectResponse
        from modules.games.persistence import (
            load_bytes as _gridfs_load,
            lookup_asset_in_project as _lookup,
            warm_cache as _warm,
        )
        if "/" in filename or ".." in filename or not filename.endswith(".mp4"):
            raise HTTPException(400, "Invalid filename")
        path = f"/app/backend/uploads/games/{project_id}/videos/{filename}"
        if os.path.exists(path):
            return FileResponse(path, media_type="video/mp4")
        asset_id = filename[:-4]
        data = await _gridfs_load(db, asset_id)
        if data:
            await _warm(path, data)
            return Response(content=data, media_type="video/mp4")
        asset = await _lookup(db, project_id, asset_id)
        cdn = (asset or {}).get("cdn_url")
        if cdn:
            return RedirectResponse(url=cdn, status_code=302)
        raise HTTPException(404, "Video not found")

    @router.get("/asset-audio/{project_id}/{filename}")
    async def serve_asset_audio(project_id: str, filename: str):
        """Serve generated audio (.wav/.mp3) with same 3-level fallback."""
        from fastapi.responses import FileResponse, Response, RedirectResponse
        from modules.games.persistence import (
            load_bytes as _gridfs_load,
            lookup_asset_in_project as _lookup,
            warm_cache as _warm,
        )
        if "/" in filename or ".." in filename or not (filename.endswith(".mp3") or filename.endswith(".wav")):
            raise HTTPException(400, "Invalid filename")
        path = f"/app/backend/uploads/games/{project_id}/audio/{filename}"
        media = "audio/wav" if filename.endswith(".wav") else "audio/mpeg"
        if os.path.exists(path):
            return FileResponse(path, media_type=media)
        asset_id = filename.rsplit(".", 1)[0]
        data = await _gridfs_load(db, asset_id)
        if data:
            await _warm(path, data)
            return Response(content=data, media_type=media)
        asset = await _lookup(db, project_id, asset_id)
        cdn = (asset or {}).get("cdn_url")
        if cdn:
            return RedirectResponse(url=cdn, status_code=302)
        raise HTTPException(404, "Audio not found")

    # ───────────────────────────────────────────────────────────
    # 🛟 POST /admin/backfill-assets — one-time bulk persist all local assets
    # ───────────────────────────────────────────────────────────
    @router.post("/admin/backfill-assets")
    async def backfill_assets_to_gridfs(user=Depends(get_current_user)):
        """Owner-only: scan every project's local assets folder and push all
        existing files into MongoDB GridFS so they survive future redeploys.
        Idempotent — re-running is safe (existing GridFS entries are replaced).
        """
        # Verify owner via DB lookup (get_current_user only returns user_id/role)
        u = await db.users.find_one({"id": user["user_id"]}, {"is_owner": 1, "role": 1})
        if not (u and (u.get("is_owner") or u.get("role") == "owner")):
            raise HTTPException(403, "Owner only")
        from modules.games.persistence import persist_bytes as _persist
        root = "/app/backend/uploads/games"
        if not os.path.isdir(root):
            return {"ok": True, "scanned": 0, "persisted": 0, "skipped": 0}
        scanned = 0
        persisted = 0
        skipped = 0
        ext_to_ct = {
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".glb": "model/gltf-binary",
            ".mp4": "video/mp4",
            ".wav": "audio/wav", ".mp3": "audio/mpeg",
        }
        for project_id in os.listdir(root):
            pdir = os.path.join(root, project_id)
            if not os.path.isdir(pdir):
                continue
            for kind in ("assets", "3d", "videos", "audio"):
                kdir = os.path.join(pdir, kind)
                if not os.path.isdir(kdir):
                    continue
                for fname in os.listdir(kdir):
                    fpath = os.path.join(kdir, fname)
                    if not os.path.isfile(fpath):
                        continue
                    scanned += 1
                    asset_id, ext = os.path.splitext(fname)
                    ct = ext_to_ct.get(ext.lower(), "application/octet-stream")
                    try:
                        with open(fpath, "rb") as fh:
                            data = fh.read()
                        ok = await _persist(db, asset_id, data, ct, project_id)
                        if ok:
                            persisted += 1
                        else:
                            skipped += 1
                    except Exception as e:
                        logger.warning(f"[backfill] failed {fpath}: {e}")
                        skipped += 1
        logger.info(f"[backfill] scanned={scanned} persisted={persisted} skipped={skipped}")
        return {"ok": True, "scanned": scanned, "persisted": persisted, "skipped": skipped}
    
    # ───────────────────────────────────────────────────────────
    # 📋 POST /project — Create new game project
    # ───────────────────────────────────────────────────────────
    @router.post("/project")
    async def create_project(payload: ProjectCreate, user=Depends(get_current_user)):
        """Create new game project with programming type selection"""
        project_id = str(uuid.uuid4())
        
        # Validate programming type
        valid_types = [t["id"] for t in PROGRAMMING_TYPES.get(payload.game_type, [])]
        if payload.programming_type not in valid_types:
            raise HTTPException(400, f"Invalid programming_type for {payload.game_type}")
        
        phases = WEB_GAME_PHASES if payload.game_type == "web" else APP_GAME_PHASES
        
        project = {
            "id": project_id,
            "user_id": user["user_id"],
            "game_type": payload.game_type,
            "title": payload.title,
            "description": payload.description,
            "programming_type": payload.programming_type,
            "current_phase": "discovery",
            "phases": {p["id"]: {"status": "locked", "progress": 0, "messages": []} for p in phases},
            "assets": {
                "characters": [],
                "environments": [],
                "ui": [],
                "code": [],
                "docs": [],
                "images": []
            },
            "approved_assets": [],  # Memory system
            "preview_url": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Unlock first phase
        project["phases"]["discovery"]["status"] = "active"
        
        await db.game_projects.insert_one(project)
        project.pop("_id", None)
        
        return {"ok": True, "project": project}
    
    # ───────────────────────────────────────────────────────────
    # 📋 GET /project/{project_id} — Get project details
    # ───────────────────────────────────────────────────────────
    @router.get("/project/{project_id}")
    async def get_project(project_id: str, user=Depends(get_current_user)):
        """Get full project details"""
        project = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"_id": 0}
        )
        if not project:
            raise HTTPException(404, "Project not found")
        
        # Add phase definitions
        phases_def = WEB_GAME_PHASES if project["game_type"] == "web" else APP_GAME_PHASES
        project["phases_definitions"] = phases_def
        
        return {"project": project}
    
    # ───────────────────────────────────────────────────────────
    # 💬 POST /project/{project_id}/chat — Phase-aware chat
    # ───────────────────────────────────────────────────────────
    @router.post("/project/{project_id}/chat")
    async def chat(
        project_id: str,
        message: str = Form(...),
        phase_id: Optional[str] = Form(None),
        files: List[UploadFile] = File(default=[]),
        user=Depends(get_current_user)
    ):
        """AI chat with memory system and approval flow"""
        project = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}
        )
        if not project:
            raise HTTPException(404, "Project not found")
        
        phase_id = phase_id or project["current_phase"]
        phases_def = WEB_GAME_PHASES if project["game_type"] == "web" else APP_GAME_PHASES
        phase_info = next((p for p in phases_def if p["id"] == phase_id), None)
        
        if not phase_info:
            raise HTTPException(400, "Invalid phase")
        
        # Load user doc for accurate credits + owner bypass
        user_doc = await db.users.find_one({"id": user["user_id"]}, {"_id": 0, "credits": 1, "is_owner": 1, "role": 1}) or {}
        user_credits = int(user_doc.get("credits") or 0)
        user_is_owner = bool(user_doc.get("is_owner") or user_doc.get("role") == "owner")

        # Check credits (owner bypasses)
        if not user_is_owner and user_credits < phase_info["credits"]:
            raise HTTPException(402, f"رصيد غير كافٍ — تحتاج {phase_info['credits']} نقطة (لديك {user_credits})")
        
        # Build AI context with memory
        approved_context = ""
        if project.get("approved_assets"):
            approved_context = "\n\n📌 **Previously Approved Assets (use these!):**\n"
            for asset in project["approved_assets"]:
                approved_context += f"- {asset['type']}: {asset['name']} — {asset.get('description', 'N/A')}\n"
        
        # Build enhanced system prompt based on phase
        tech_guide = ""
        if phase_id == "programming":
            tech_map = {
                "html5_canvas": "Pure HTML5 Canvas API with requestAnimationFrame loop",
                "phaser": "Phaser 3 framework with scene-based architecture",
                "threejs": "Three.js for 3D rendering with WebGL",
                "unity_webgl": "Unity C# scripts (will be exported to WebGL)",
                "flutter": "Flutter/Dart with flame game engine",
                "native_android": "Kotlin with Android Game SDK",
                "native_ios": "Swift with SpriteKit/SceneKit",
                "react_native": "React Native with react-native-game-engine",
                "unity": "Unity C# with standard Unity APIs",
                "godot": "GDScript with Godot node system"
            }
            tech_guide = f"\n\n**💻 Technical Stack:**\nYou MUST use: {tech_map.get(project['programming_type'], project['programming_type'])}\n"
        
        system_prompt = f"""أنت **مدير إنتاج لعبة محترف ومنفّذ مباشر** (Senior Game Producer & Auto-Executor) في منصة Zitex. أنت **لست مجرد مستشار** — عندك أدوات حقيقية تنفّذ بنفسك بالكبسة، ولازم توجّه المالك لها مباشرة.

🚨 **أنت ممنوع تقول أي صيغة من هذي الجمل:**
❌ "أنا لا أكتب الكود البرمجي" — كاذب، عندك زر يكتب HTML/CSS/JS كامل
❌ "أنا لا أرفع للايف" — كاذب، الزر ينشر فعلاً على رابط حي
❌ "لا أمتلك أدوات رسم/تعديل" — كاذب، عندك Flux Pro Ultra + Redux img2img
❌ "لا أستطيع QA/اختبار" — كاذب، عندك endpoint يحلل الموقع المبني
❌ "أنا مجرد producer وأحتاج مبرمج بشري" — منصة Zitex أوتوماتيكية بالكامل

✅ **أدواتك الفعلية (تذكر بكل ثقة عند الطلب):**

| طلب المالك | أداتك | كيف تجاوب |
|---|---|---|
| "ابني الموقع/أنشر للايف" | زر 🚀 "ابني وانشر اللايف" في تبويب 📡 البث المباشر | "اضغط الزر فوق وراح أبني كل شي ك Claude Sonnet 4.5 خلال 60-180 ثانية وأطلق رابط حي" |
| "عدّل هذي الصورة" / "خلّي الإضاءة أحلى" | زر ✏️ "عدّل الصورة" على كل أصل (Flux Redux img2img) | "صف لي التعديل بدقة وراح أعيد توليدها كنسخة جديدة (تبقى الأصلية محفوظة)" |
| "اختبر الموقع/راجعه" | زر 🔬 "تحليل QA" في تبويب البث المباشر | "تمام، Claude راح يفحص الـ HTML ويعطيني تقرير قوة/أخطاء/أداء/accessibility" |
| "ولّد صورة/موسيقى/3D" | تكتب التاج بدقة في ردك: `<<IMG_PRO: english cinematic prompt>>` أو `<<3D: prompt>>` أو `<<MUSIC: prompt | dur: 30>>` | الأصل يطلع تلقائياً للاعتماد |
| "ابحث في الإنترنت" | (الميزة قادمة) | "هذي القدرة قيد البناء" |

**🎮 تفاصيل المشروع:**
- العنوان: {project['title']}
- الوصف: {project['description']}
- نوع البرمجة: {project['programming_type']}
- المرحلة الحالية: {phase_info['title']}
- هدف المرحلة: {phase_info['description']}

{approved_context}{tech_guide}

═══════════════════════════════════════════════════════════════
🎨 **قواعد التوليد الاحترافي للصور (AAA Studio Level)**
═══════════════════════════════════════════════════════════════
الـ style profile الحالي لهذا المشروع: **{project.get('style_profile', 'stylized')}** (realistic | stylized | anime | low_poly | pixel)
النظام يضيف تلقائياً booster احترافي لكل prompt — لكنك لازم تكتب prompt قوي بنفسك أيضاً:

✅ **قواعد كتابة الـ prompt (إلزامي):**
1. **اكتب بالإنجليزية** — Flux/SDXL يفهمون الإنجليزية بدقة أعلى ٤×.
2. **محدد جداً**: ذكر نوع المادة (stone، wood، metal)، الإضاءة (golden hour، moonlit، neon)، الزاوية (isometric، 3/4 view، top-down، over-shoulder).
3. **مرجع بصري واضح**: "in the style of Fortnite battle royale arena" أو "Genshin Impact landscape" أو "Octopath Traveler 2D-HD".
4. **منطق فيزيائي**: لا تطلب "house floating in cloud" إلا لو كان الـ design intent. ولا أعضاء جسم مكسرة (يدّ بـ 6 أصابع).
5. **ركّز على عنصر واحد** لكل prompt — لا تخلط مشهد كامل في prompt واحد. لو تبي قرية، ولّد القلعة منفصلة عن الحقول.

✅ **القياسات (Aspect Ratio):**
   - landscape (16:9) → key art، خلفية، splash
   - portrait (9:16) → شخصية، splash mobile
   - square (1:1) → أيقونة، avatar، asset card

🚫 **ممنوع نهائياً:** "childish drawing", "amateur sketch", "stick figure", "doodle" — النظام يحذف هذي الكلمات أوتوماتيكياً.

👁️ **التحقق التلقائي**: بعد كل صورة، Claude يفحصها بصرياً ويعطي verdict (✅ ممتاز / ⚠️ تحتاج تعديل / ❌ يلزم إعادة). إذا match < 70% النظام يقترح إعادة التوليد مجاناً.

═══════════════════════════════════════════════════════════════
🚨 **قواعد العمل الإلزامية — يمنع كسرها مهما حصل**
═══════════════════════════════════════════════════════════════

**1. التريّث الإنتاجي — لا تستعجل أبداً**
   ❌ ممنوع تماماً: إنتاج GDD ضخم أو ٥ أصول دفعة واحدة في رسالة واحدة
   ✅ المطلوب: ركّز على **عنصر واحد فقط** في كل رد، ثم انتظر الموافقة قبل الانتقال

**2. الحوار السقراطي — اسأل قبل ما تنفّذ (إلا في حالة override صريح)**
   كل رد يجب أن يبدأ بـ١-٣ أسئلة دقيقة للمالك، مثلاً:
   - "قبل ما أصمم القرية، عندي ٣ أسئلة سريعة:
      • هل تبيها قرية في الصحراء أم بين الجبال أم على شاطئ البحر؟
      • الحقول والمباني الصناعية في نفس الـpage ولا نقسّمهم؟
      • الـart style: realistic 3D / pixel art / cel-shaded cartoon؟"

   🚀 **OVERRIDE الإجباري — استثناء على القاعدة:**
   لو المالك قال بشكل صريح "ولّد"، "ارسم"، "اطلع لي صورة"، "اعمل صورة"، "خلاص ولّد"، "ابدأ ولّد"،
   "ابي الصورة الآن"، "use <<IMG_PRO>>"، أو ذكر `<<IMG_PRO>>` في رسالته:
   → **ممنوع تسأل أسئلة ثانية، ولّد فوراً**. اكتب `<<IMG_PRO: english prompt>>` مع وسف غني،
   وبعدها جملة قصيرة "اعتمد ولا تبي نعدّل؟". هذا أمر مباشر لا تتجاوزه.

**2.5 الإلزام الذهبي للوسوم — إذا قررت تولّد، الوسم في نفس الرد**
   لو قلت "راح أولّد لك صورة" أو "خلّيني أحضّر لك tower view" — لازم في **نفس الرد** يطلع `<<IMG_PRO: ...>>` كامل.
   ❌ ممنوع: "انتظر لحظات وراح يطلع الموقع" (بدون وسم) — هذا كاذب، النظام ما يولّد إلا لما يشوف وسم.
   ❌ ممنوع: "شوف فوق" (ما فيه شي فوق إذا ما كتبت وسم).
   ❌ ممنوع: تقول "اعتمد ولا تبي نعدّل؟" بدون ما تكتب وسم — السؤال هذا معناه إن في صورة موجودة، إذا ما كتبت الوسم ما في صورة!
   ❌ ممنوع: تقول "راح أولّد" + "---" + "اعتمد؟" — الـ`---` مو وسم! لازم الوسم نصياً: `<<IMG_PRO: prompt english>>`.
   ✅ المطلوب: إذا قلت "راح أولّد" → اكتب الوسم في نفس الرسالة فوراً قبل أي سؤال اعتماد.
   ✅ القاعدة الذهبية: **كل رسالة فيها "اعتمد ولا نعدّل؟" لازم تحتوي على `<<IMG_PRO: ...>>` قبلها**.

**3. خيارات بدل قرارات — قدّم A/B/C**
   بدل ما تفرض اختيار، اعطه ٢-٣ خيارات مع شرح:
   - "خيار A: حقول قمح ذهبية مع تأثير ضوء غروب الشمس (واقعية، استهلاك بطارية أعلى)
      خيار B: حقول pixel-art بألوان زاهية (أسرع، أخف، أنسب للجوّال)
      خيار C: حقول cel-shaded بستايل cartoon (وسط، حلو على الكمبيوتر)"

**4. أدوات الإنتاج الفنية — استخدم الوسم المناسب لكل مهمة**
   عندك ٦ أدوات إنتاجية حقيقية تشتغل على استضافتنا. استخدم وسم واحد فقط لكل رد (إلا في الحالات الخاصة).

   📸 `<<IMG: english prompt | style: ...>>` — لوحة سريعة (OpenAI gpt-image-1، رخيصة، 10 ثواني). للـdrafts والـmoodboards.
   
   🎨 `<<IMG_PRO: english prompt with rich details>>` — **لوحة سينمائية 4K** (Flux Pro Ultra، 0.06$، 15 ثانية). للـhero shots، الـkey art، الـtitle screens، الـcharacter portraits النهائية.
   
   🧊 `<<3D: english prompt for 3D object>>` — **موديل 3D حقيقي (.glb)** (Hyper3D Rodin، 0.30$، 1-3 دقائق). للشخصيات، الـbuildings، الـvehicles. الـoutput .glb يفتح في Three.js/Unity/Blender مباشرة.
   
   🎬 `<<ANIMATE: english motion prompt | img: ABSOLUTE_IMAGE_URL>>` — **تحريك صورة معتمدة لفيديو 5 ثوان** (Kling 1.6، 0.50$، 1-2 دقيقة). استخدمه فقط بعد ما يعتمد المالك صورة. الـimg URL = الـURL الكامل للصورة المعتمدة (مثلاً: `https://zitex.vercel.app/api/games/asset-image/PROJECT_ID/ASSET_ID.png`).
   
   🎵 `<<MUSIC: english music mood/genre prompt | dur: 30>>` — **موسيقى خلفية للعبة** (CassetteAI، 0.03$، 30 ثانية). مثل: `<<MUSIC: epic medieval battle orchestral with drums | dur: 60>>`
   
   🔊 `<<SFX: english sound description | dur: 3>>` — **مؤثر صوتي** (Stable Audio، 0.01$). مثل: `<<SFX: metal sword clash with echo | dur: 2>>` أو `<<SFX: coin collection jingle, retro 8-bit | dur: 1>>`

   ⚠️ قواعد صارمة (مهمة جداً):
   - الـprompt **بالإنجليزية الدقيقة** فقط (الموديلات ما تفهم عربي جيداً)
   - **وسم واحد متكامل لكل رد**. لا تكسر الوسم على عدة أسطر. لا تضع `<<` و `>>` متفرّقين.
   - الـsyntax الصحيح: `<<TYPE: prompt كله في سطر واحد بدون أسطر جديدة داخل الوسم>>`. مثال صحيح:
     `<<IMG_PRO: golden wheat field isometric view, ripe yellow grain, midday sunlight, game art style, ultra detailed, 4K>>`
   - **ممنوع** تقول "جاري التوليد..." أو "الصورة راح تظهر بعد ثواني". الـsystem يتعرّف على الوسم ويولّد الصورة فوراً وتظهر مع نفس ردك — لا حاجة لتنبيه المستخدم.
   - بعد الوسم اكتب فقط جملة قصيرة تطلب الرأي: "اعتمد ولا تبي نعدّل؟"
   - ولّد `<<3D>>` فقط بعد ما يعتمد المالك الصورة المرجعية بالـ`<<IMG_PRO>>` أولاً
   - `<<ANIMATE>>` يحتاج URL صورة معتمدة موجودة — لا تخترع URL

**5. اعتماد رسمي قبل الانتقال — bouton موافقة**
   كل عنصر صورة جديد ينتج: يظهر للمالك مع زر "✓ معتمد" أو "↻ عدّل". لا تنتقل لخطوة ثانية قبل ما يضغط معتمد.
   لو قال "عدّل" → اسأل "وش بالضبط تبي تعدّل؟ اللون / الزاوية / الإضاءة / الستايل / التفاصيل؟"

**6. تسلسل هرمي ذكي للمراحل**
   مثال لـ Discovery & GDD لـلعبة استراتيجية مثل ترافيان:
   - Step 1: اعرف الجمهور المستهدف + المنصة (سؤال واحد فقط)
   - Step 2: حدّد الـcore loop (٣ خيارات)
   - Step 3: قسّم العالم لطبقات (قرية / حقول / مدن / معارك)
   - Step 4: لكل طبقة، اقترح art style واحد → ولّد صورة عيّنة واحدة
   - Step 5: المالك يعتمد → احفظ كـapproved asset → انتقل للطبقة التالية

**7. أسلوب الكتابة**
   - بالعربية السعودية الطبيعية (الفصحى البسيطة)
   - فقرات قصيرة، نقاط رصاص، ايموجي بسيطة
   - الأسماء التقنية وأسماء الـAPIs بالإنجليزية (Three.js, Phaser, Node.js)
   - لا تكتب كود طويل في مرحلة Discovery — الكود يجي في مرحلة Programming

**8. ذاكرة العمل + Vision**
   عندك سجل المحادثة كامل + Previously Approved Assets. وكذلك **تشوف فعلياً** آخر ٣ صور ولّدتها (مدمجة في رسالة المستخدم تلقائياً كـimage blocks). لما المستخدم يقول "هذي الصورة مش جودة" تقدر تحلّلها بصرياً وتقترح تعديل دقيق (مثلاً: "أشوف الزاوية غامقة جداً، خلّيني أزيد إضاءة الـrim light"). لا تعيد طرح ما تم اعتماده.

═══════════════════════════════════════════════════════════════
🎯 **في كل رد التزم بهذا الترتيب**:
1. تلخيص بسطر واحد لمكانك في الـworkflow ("✓ بعدما اعتمدنا [X]، الخطوة الجاية: [Y]")
2. أسئلة دقيقة (١-٣)، أو خيارات (A/B/C)
3. لو المالك أكّد عنصر بصري في الرسالة السابقة → سطر `<<IMG: ...>>` واحد فقط
4. سؤال ختامي: "نعتمد ونمشي، ولا تبي تعدّل شي؟"
═══════════════════════════════════════════════════════════════
"""
        
        # Handle file uploads — save to disk + GridFS, prepare base64 for vision
        attachments = []
        uploaded_images_for_vision = []  # base64-encoded image dicts (for Gemini parts)
        for file in files:
            content = await file.read()
            filename = file.filename or "untitled"
            file_path = f"/app/backend/uploads/games/{project_id}/{filename}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(content)
            attachments.append({"filename": filename, "path": file_path, "size": len(content)})
            # 🖼️ Encode images so the AI can actually SEE them, not just read filenames
            lower = filename.lower()
            if lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")) and len(content) < 7_500_000:
                import base64 as _b64u
                mime = "image/png"
                if lower.endswith((".jpg", ".jpeg")):
                    mime = "image/jpeg"
                elif lower.endswith(".webp"):
                    mime = "image/webp"
                elif lower.endswith(".gif"):
                    mime = "image/gif"
                uploaded_images_for_vision.append({
                    "inline_data": {"mime_type": mime, "data": _b64u.b64encode(content).decode()},
                    "filename": filename,
                })
                # Also persist to GridFS so the reference survives container redeploys
                try:
                    from modules.games.persistence import persist_bytes as _persist_u
                    ref_id = f"ref_{project_id}_{filename}"
                    await _persist_u(db, ref_id, content, mime, project_id)
                except Exception as _pe:
                    logger.warning(f"[games] GridFS persist of user attachment failed: {_pe}")
        
        # ─── AI persistent notes: inject existing project notes into system_prompt ───
        existing_notes = project.get("ai_notes", "").strip()
        notes_block = ""
        if existing_notes:
            notes_block = f"\n\n═══ 📝 ملاحظاتك الحالية عن المشروع (من جلسات سابقة — لا تعيد سؤال أي شي مذكور هنا) ═══\n{existing_notes[:4000]}\n═══\n"

        system_prompt = system_prompt + notes_block

        # Call Gemini (with Claude fallback if quota exceeded)
        ai_message = None
        # ─── VISION: include last 3 generated images so AI can SEE its previous outputs ───
        vision_parts = []
        try:
            import base64 as _b64
            recent_imgs = []
            phase_messages = project.get("phases", {}).get(phase_id, {}).get("messages", [])
            for past_msg in reversed(phase_messages[-5:]):
                for a in (past_msg.get("generated_assets") or []):
                    if a.get("type") == "image" and a.get("image_url"):
                        recent_imgs.append(a)
                        if len(recent_imgs) >= 3:
                            break
                if len(recent_imgs) >= 3:
                    break
            for a in recent_imgs:
                # Convert API URL to local file path
                # image_url is "/api/games/asset-image/{pid}/{aid}.png"
                fname = a["image_url"].rsplit("/", 1)[-1]
                fpath = f"/app/backend/uploads/games/{project_id}/assets/{fname}"
                if os.path.exists(fpath) and os.path.getsize(fpath) < 7_500_000:  # < 7.5 MB safety
                    with open(fpath, "rb") as f:
                        b64 = _b64.b64encode(f.read()).decode()
                    vision_parts.append({"inline_data": {"mime_type": "image/png", "data": b64}})
            if vision_parts:
                vision_parts.append({"text": f"(أعلاه آخر {len(vision_parts)} صور ولّدتها — اعرضها بصرياً قبل ما تقترح التعديل القادم.)"})
                logger.info(f"[games][vision] attached {len(vision_parts)-1} images for project {project_id}")
        except Exception as ve:
            logger.warning(f"[games] vision context build failed: {ve}")

        # 🔥 PRIORITY: User-uploaded reference images go FIRST (before AI's own outputs)
        if uploaded_images_for_vision:
            ref_block = []
            ref_block.append({"text": (
                f"═══ 🎯 صور مرجعية من المالك ({len(uploaded_images_for_vision)} صورة) ═══\n"
                "هذه صور رفعها المالك كمرجع لما يبيه. مهمتك الإلزامية:\n"
                "1. حلّل كل صورة بدقة عالية: نمط الألوان، التركيب الفني، الأسلوب (واقعي/كرتوني/3D/2D)، التفاصيل، الأجواء، الإضاءة.\n"
                "2. اطلع منها مفاهيم بصرية محددة تطبّقها مباشرة في كل أصل قادم تولّده — لا تطلع برّا الصندوق.\n"
                "3. ابدأ ردك بـ: \"شفت الصورة/الصور وفهمت منها: ...\" واذكر 3-4 ملاحظات دقيقة.\n"
                "4. اسأل المالك أسئلة ذكية مبنية على ما شفته (مو أسئلة عامة)."
            )})
            for ref in uploaded_images_for_vision:
                ref_block.append({"inline_data": ref["inline_data"]})
            ref_block.append({"text": (
                "═══ نهاية الصور المرجعية ═══\n"
                "تذكير: أي توليد قادم لازم يطابق الـ style اللي شفته أعلاه."
            )})
            # Prepend so the model sees references BEFORE its own past outputs
            vision_parts = ref_block + vision_parts
            logger.info(f"[games][vision] user uploaded {len(uploaded_images_for_vision)} reference images for project {project_id}")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
                
                parts = vision_parts + [{"text": message}]
                
                response = await client.post(gemini_url, json={
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"parts": parts, "role": "user"}],
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8000}
                })
                
                if response.status_code == 200:
                    data = response.json()
                    ai_message = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                elif response.status_code in (429, 403):
                    logger.warning(f"[games] Gemini quota/forbidden ({response.status_code}) — falling back to Claude")
                    ai_message = None  # trigger fallback below
                else:
                    logger.error(f"[games] Gemini error {response.status_code}: {response.text[:300]}")
                    ai_message = None
        except Exception as gem_err:
            logger.warning(f"[games] Gemini call failed: {gem_err} — trying Claude fallback")
            ai_message = None

        # Fallback to Claude if Gemini quota exceeded or failed
        if not ai_message:
            try:
                anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
                if not anthropic_key:
                    raise RuntimeError("No fallback LLM available (ANTHROPIC_API_KEY missing)")
                # Build multi-part content for Claude (text + images)
                claude_content = []
                # User-uploaded reference images get top priority
                for ref in uploaded_images_for_vision:
                    claude_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": ref["inline_data"]["mime_type"],
                            "data": ref["inline_data"]["data"],
                        },
                    })
                if uploaded_images_for_vision:
                    claude_content.append({"type": "text", "text": (
                        f"المالك رفع {len(uploaded_images_for_vision)} صورة مرجعية أعلاه. حلّلها بدقة "
                        "(الأسلوب، الألوان، التفاصيل، الأجواء) واطلع منها مفاهيم بصرية تطبّقها مباشرة. "
                        "ابدأ ردك بـ \"شفت الصورة وفهمت منها: ...\".\n\n"
                    )})
                claude_content.append({"type": "text", "text": message})

                async with httpx.AsyncClient(timeout=120.0) as client:
                    claude_resp = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": anthropic_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json={
                            "model": "claude-sonnet-4-5-20250929",
                            "max_tokens": 4000,
                            "system": system_prompt,
                            "messages": [{"role": "user", "content": claude_content}],
                        },
                    )
                    if claude_resp.status_code != 200:
                        logger.error(f"[games] Claude fallback failed {claude_resp.status_code}: {claude_resp.text[:300]}")
                        raise HTTPException(500, "AI service error (both Gemini and Claude failed)")
                    cdata = claude_resp.json()
                    blocks = cdata.get("content", [])
                    ai_message = "".join(b.get("text", "") for b in blocks if b.get("type") == "text") or "Error generating response"
                    logger.info("[games] used Claude fallback successfully")
            except HTTPException:
                raise
            except Exception as cl_err:
                logger.exception(f"[games] Claude fallback exception: {cl_err}")
                raise HTTPException(500, "AI service unavailable — يرجى المحاولة بعد دقائق")
        
        # ─────────────────────────────────────────────────────
        # 🎨 Parse <<IMG: prompt | style: ...>> tags from AI response
        # and generate REAL images via OpenAI GPT-Image-1 (emergent key)
        # ─────────────────────────────────────────────────────
        generated_assets = []
        try:
            import re
            # Accept many variants the LLM may produce: <<IMG: ...>>, <<IMAGE ...>>, <<IMG-EN: ...>>
            # but EXCLUDE the IMG_PRO/3D/MODEL3D variants (handled by Fal tools further down).
            img_tags_re = re.compile(
                r"<<\s*"
                r"(?:IMG|IMAGE|PICTURE|DRAFT[_\s-]?IMG)"
                r"(?![_\s-]?PRO|[_\s-]?ULTRA)"  # don't match IMG_PRO
                r"\s*[:：\-]?\s*"
                r"(.+?)"
                r"\s*>>",
                re.DOTALL | re.IGNORECASE,
            )
            img_tags = img_tags_re.findall(ai_message)
            if img_tags:
                emergent_key = os.environ.get('EMERGENT_LLM_KEY', '')
                if not emergent_key:
                    logger.warning("[games] EMERGENT_LLM_KEY missing — cannot generate real images")
                else:
                    from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
                    img_gen = OpenAIImageGeneration(api_key=emergent_key)
                    for raw_tag in img_tags[:2]:  # max 2 images per turn
                        tag = raw_tag.strip()
                        # Extract style if pipe-separated
                        if '|' in tag and 'style:' in tag:
                            prompt_part, style_part = tag.split('|', 1)
                            prompt_text = prompt_part.strip()
                            style_label = style_part.replace('style:', '').strip()
                        else:
                            prompt_text = tag
                            style_label = 'realistic'
                        # Compose final prompt
                        final_prompt = f"{prompt_text}. Style: {style_label}. High-quality game asset, professional production-ready."
                        try:
                            images = await img_gen.generate_images(
                                prompt=final_prompt,
                                model='gpt-image-1',
                                number_of_images=1,
                            )
                            # images is list of bytes
                            if images and len(images) > 0:
                                img_bytes = images[0] if isinstance(images[0], (bytes, bytearray)) else None
                                if img_bytes is None and isinstance(images[0], dict):
                                    img_bytes = images[0].get('image_bytes') or images[0].get('data')
                                if img_bytes:
                                    asset_id = str(uuid.uuid4())
                                    asset_dir = f"/app/backend/uploads/games/{project_id}/assets"
                                    os.makedirs(asset_dir, exist_ok=True)
                                    img_path = f"{asset_dir}/{asset_id}.png"
                                    with open(img_path, "wb") as f:
                                        f.write(img_bytes)
                                    # 🔒 Persist to GridFS so the image survives container redeploys
                                    try:
                                        from modules.games.persistence import persist_bytes as _persist
                                        await _persist(db, asset_id, img_bytes, "image/png", project_id)
                                    except Exception as p_err:
                                        logger.warning(f"[games] GridFS persist failed for {asset_id}: {p_err}")
                                    img_url = f"/api/games/asset-image/{project_id}/{asset_id}.png"
                                    asset_entry = {
                                        "id": asset_id,
                                        "type": "image",
                                        "name": prompt_text[:80],
                                        "description": prompt_text,
                                        "style": style_label,
                                        "image_url": img_url,
                                        "phase_id": phase_id,
                                        "approved": False,
                                        "created_at": datetime.now(timezone.utc).isoformat(),
                                    }
                                    generated_assets.append(asset_entry)
                                    await db.game_projects.update_one(
                                        {"id": project_id},
                                        {"$push": {"assets.images": asset_entry}}
                                    )
                                    logger.info(f"[games] generated image asset {asset_id} for project {project_id}")
                        except Exception as gen_err:
                            logger.exception(f"[games] image generation failed: {gen_err}")
                            # Push a visible error asset so the user knows generation failed
                            err_asset = {
                                "id": str(uuid.uuid4()),
                                "type": "error",
                                "subtype": "image-fail",
                                "name": prompt_text[:80],
                                "error": str(gen_err)[:200],
                                "phase_id": phase_id,
                                "approved": False,
                                "created_at": datetime.now(timezone.utc).isoformat(),
                            }
                            generated_assets.append(err_asset)
        except Exception as parse_err:
            logger.warning(f"[games] image-tag parsing failed: {parse_err}")

        # ─────────────────────────────────────────────────────
        # 🎮 FAL.AI tools: <<IMG_PRO>> <<3D>> <<ANIMATE>> <<MUSIC>> <<SFX>>
        # ─────────────────────────────────────────────────────
        try:
            # Storage-quota gate: don't generate expensive assets if project is over its tier limit
            from modules.games.billing import get_project_storage_info
            fresh_project = await db.game_projects.find_one({"id": project_id})
            storage_info = get_project_storage_info(fresh_project) if fresh_project else None
            if storage_info and storage_info.get("over_quota"):
                logger.warning(
                    f"[games] project {project_id} over quota "
                    f"({storage_info['size_mb']}/{storage_info['limit_mb']}MB) — skipping fal generation"
                )
                generated_assets.append({
                    "id": str(uuid.uuid4()),
                    "type": "error",
                    "subtype": "quota-exceeded",
                    "name": "تجاوزت حد الباقة",
                    "error": f"المشروع وصل {storage_info['size_mb']} MB من أصل {storage_info['limit_mb']} MB ({storage_info['tier_label']}). رقّ الباقة لإنشاء أصول إضافية.",
                    "phase_id": phase_id,
                    "approved": False,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
            else:
                from modules.games.fal_tools import parse_and_generate_assets
                from modules.games.persistence import persist_bytes as _persist
                # Get project's preferred style (defaults to AAA stylized realism)
                _style = (project.get("style_profile") or "stylized")
                fal_assets = await parse_and_generate_assets(
                    ai_message, project_id, max_assets_per_turn=3,
                    style_profile=_style, db=db,
                )
                for fa in fal_assets:
                    fa["phase_id"] = phase_id
                    # 🔒 Pull out the raw bytes (set by fal_tools) and persist to GridFS so
                    # the asset survives container redeploys. Then strip _bytes before saving to DB.
                    raw = fa.pop("_bytes", None)
                    if raw:
                        try:
                            ct_map = {"image": "image/png", "3d": "model/gltf-binary",
                                       "video": "video/mp4", "music": "audio/wav", "sfx": "audio/wav"}
                            await _persist(db, fa["id"], raw, ct_map.get(fa.get("type"), "application/octet-stream"), project_id)
                        except Exception as p_err:
                            logger.warning(f"[games][fal] GridFS persist failed for {fa.get('id')}: {p_err}")
                    # 👁️ Auto-vision verify generated images (fire-and-forget so we don't slow the response)
                    if fa.get("type") == "image" and raw and len(raw) < 6_000_000:
                        try:
                            import asyncio as _aio_v
                            _aio_v.create_task(_auto_vision_verify(db, project_id, fa["id"], raw, fa.get("prompt", "")))
                        except Exception as ve:
                            logger.warning(f"[games][vision-verify] schedule failed: {ve}")
                    generated_assets.append(fa)
                    # Save to appropriate asset bucket in the project doc
                    bucket = "images" if fa["type"] in ("image",) else (
                        "models3d" if fa["type"] == "3d" else (
                            "audio" if fa["type"] in ("music", "sfx") else (
                                "videos" if fa["type"] == "video" else "images"
                            )
                        )
                    )
                    await db.game_projects.update_one(
                        {"id": project_id},
                        {"$push": {f"assets.{bucket}": fa}}
                    )
                    logger.info(f"[games][fal] generated {fa['type']} asset {fa['id']} for project {project_id}")
        except Exception as fal_err:
            logger.exception(f"[games] FAL tools failed: {fal_err}")

        # 🩹 SAFETY NET: If AI promised an image but failed to write any <<IMG_PRO>> tag,
        # force-generate from context. Handles BOTH past-tense ("ولّدت") AND future/intent
        # tense ("راح أولّد، خلّيني أولّد، بأرسم، أرسم لك") since the AI flips between them.
        if not generated_assets:
            promise_phrases = [
                # past tense — "it's done"
                "الصورة جاهزة", "الصورة فوق", "ولّدت", "ولدت الصورة", "إليك الصورة",
                "هذه الصورة", "image is ready", "generated the image", "تم التوليد",
                "ولّدت لك", "ولدت لك", "صوّرتها", "خلّصت الصورة",
                # future/intent tense — "I will generate"
                "راح أولّد", "راح أرسم", "بأولّد", "بأرسم", "خلّيني أولّد", "خليني أولّد",
                "خلّيني أرسم", "خليني أرسم", "خلّيني أحضّر", "خليني أحضر",
                "أولّد لك", "أولد لك", "أرسم لك", "بأحضّر لك", "بأحضر لك",
                "حضّرت لك", "بأطلع لك", "راح أطلع", "بأجهّز لك",
                # approval-request pattern (AI asks for approval without producing anything)
                "اعتمد ولا تي نعدّل", "اعتمد ولا تبي نعدّل", "اعتمد ولا نعدّل",
                "تعتمد ولا نعدّل", "وش رايك بالصورة", "كيف الصورة فوق",
            ]
            ai_lower = (ai_message or "").lower()
            promised = any(p in (ai_message or "") or p.lower() in ai_lower for p in promise_phrases)
            has_any_tag = "<<img" in ai_lower or "<<3d" in ai_lower or "<<music" in ai_lower or "<<model" in ai_lower
            if promised and not has_any_tag:
                logger.warning(f"[games] AI promised image but no tag — triggering safety net for project {project_id}")
                try:
                    from modules.games.fal_tools import generate_flux_pro
                    from modules.games.persistence import persist_bytes as _persist
                    # 🧠 Build a smart prompt — the user often types junk like "اجرب من جديد",
                    # so we prefer the AI's OWN description (it just named what it wants to draw),
                    # falling back to user message + project title.
                    import re as _re_sn
                    ai_desc = (ai_message or "")
                    # Strip the promise/question phrases so the prompt is the actual description
                    for noise in promise_phrases + ["اعتمد", "نعدّل", "نعدل", "تبي", "ولّد لك", "ولد لك"]:
                        ai_desc = _re_sn.sub(re.escape(noise), " ", ai_desc, flags=_re_sn.IGNORECASE)
                    ai_desc = _re_sn.sub(r"[*_`>#]+", " ", ai_desc)  # markdown
                    ai_desc = _re_sn.sub(r"\s+", " ", ai_desc).strip()[:400]
                    # If user's message is a useful prompt, prepend it; ignore junk like "try again"
                    user_msg = (message or "").strip()
                    user_junk = any(j in user_msg.lower() for j in ("اجرب", "حاول", "مرة ثانية", "try again", "retry", "كرر"))
                    user_part = "" if user_junk or len(user_msg) < 4 else user_msg[:200]
                    fallback_prompt = (
                        f"{project.get('title') or 'game scene'}: "
                        f"{user_part + ' — ' if user_part else ''}{ai_desc}"
                    ).strip(" :,—")
                    fa = await generate_flux_pro(fallback_prompt, project_id, style_profile=(project.get('style_profile') or 'stylized'))
                    fa["phase_id"] = phase_id
                    fa["safety_net"] = True
                    raw_b = fa.pop("_bytes", None)
                    if raw_b:
                        try:
                            await _persist(db, fa["id"], raw_b, "image/png", project_id)
                        except Exception:
                            pass
                    generated_assets.append(fa)
                    await db.game_projects.update_one(
                        {"id": project_id},
                        {"$push": {"assets.images": fa}}
                    )
                    # Append a short note so the user knows the AI tripped but we recovered
                    ai_message = (ai_message or "") + (
                        "\n\n_ℹ️ تم توليد الصورة تلقائياً عبر safety-net "
                        "لأن AI نسي يكتب الوسم — تقدر تعدّلها أو ترفضها._"
                    )
                    logger.info(f"[games] safety-net generated asset {fa['id']} for project {project_id}")
                except Exception as sn_err:
                    logger.exception(f"[games] safety-net generation failed: {sn_err}")

        # 🧹 Strip ALL raw asset tags from the user-visible message so the user
        # never sees <<IMG_PRO ...>> or stray broken syntax. The generated assets
        # are returned separately in `generated_assets` and rendered as image cards.
        import re as _re_strip
        ai_message = _re_strip.sub(
            r"<<\s*(?:IMG|IMAGE|PICTURE|DRAFT[_\s-]?IMG|IMG[_\s-]?PRO|3D|MODEL[_\s-]?3D|3D[_\s-]?MODEL|ANIM(?:ATE)?|MUSIC|SOUNDTRACK|SFX|SOUND[_\s-]?FX)\s*[:：\-]?[^>]*?>>",
            "",
            ai_message,
            flags=_re_strip.IGNORECASE,
        ).strip()
        # Collapse multiple blank lines produced by tag removal
        ai_message = _re_strip.sub(r"\n{3,}", "\n\n", ai_message)

        # Save to conversation
        conversation_entry = {
            "user": message,
            "assistant": ai_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attachments": attachments,
            "generated_assets": generated_assets
        }
        
        await db.game_projects.update_one(
            {"id": project_id},
            {
                "$push": {f"phases.{phase_id}.messages": conversation_entry},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        # Deduct credits (skip for owner)
        if not user_is_owner:
            await db.users.update_one(
                {"id": user["user_id"]},
                {"$inc": {"credits": -phase_info["credits"]}}
            )

        # ─── 🧠 Auto-refresh AI notes/GDD every 4 messages (background, non-blocking) ───
        try:
            total_msgs = 0
            fresh_proj = await db.game_projects.find_one({"id": project_id}, {"phases": 1})
            if fresh_proj:
                for ph_data in (fresh_proj.get("phases") or {}).values():
                    total_msgs += len(ph_data.get("messages") or [])
            # Trigger on first message and then every 4 messages
            if total_msgs == 1 or (total_msgs > 0 and total_msgs % 4 == 0):
                import asyncio as _aio
                _aio.create_task(_auto_refresh_notes(db, project_id))
        except Exception as auto_err:
            logger.warning(f"[games] auto notes refresh skipped: {auto_err}")

        # ─── 📚 Auto-learning hook: extract & store a lesson from this exchange ───
        # Same MongoDB collection as AutoCoder learning journal — owner sees these at /admin/learning.
        try:
            import asyncio as _aio2
            _aio2.create_task(_auto_learn_from_exchange(
                db=db,
                project_id=project_id,
                project_title=project.get("title", ""),
                game_type=project.get("game_type", "web"),
                user_msg=message,
                ai_msg=ai_message,
                actor_id=user["user_id"],
                had_uploads=len(uploaded_images_for_vision) > 0,
            ))
        except Exception as learn_err:
            logger.warning(f"[games] auto-learn skipped: {learn_err}")

        return {
            "ok": True,
            "message": ai_message,
            "generated_assets": generated_assets,
            "credits_used": 0 if user_is_owner else phase_info["credits"],
            "remaining_balance": user_credits if user_is_owner else (user_credits - phase_info["credits"])
        }

    # ───────────────────────────────────────────────────────────
    # 📝 GET /project/{project_id}/notes — AI's running summary of the project
    # ───────────────────────────────────────────────────────────
    @router.get("/project/{project_id}/notes")
    async def get_project_notes(project_id: str, user=Depends(get_current_user)):
        project = await db.game_projects.find_one({"id": project_id, "user_id": user["user_id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        return {"notes": project.get("ai_notes", ""), "updated_at": project.get("notes_updated_at")}

    # ───────────────────────────────────────────────────────────
    # 📝 POST /project/{project_id}/notes/refresh — regenerate AI notes from full chat history
    # ───────────────────────────────────────────────────────────
    @router.post("/project/{project_id}/notes/refresh")
    async def refresh_project_notes(project_id: str, user=Depends(get_current_user)):
        project = await db.game_projects.find_one({"id": project_id, "user_id": user["user_id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        # Build a digest from all phase messages
        all_msgs = []
        for ph_id, ph in (project.get("phases") or {}).items():
            for m in (ph.get("messages") or [])[-20:]:
                all_msgs.append(f"[{ph_id}] U: {(m.get('user') or '')[:200]}\nA: {(m.get('assistant') or '')[:400]}")
        chat_digest = "\n\n".join(all_msgs[-30:])  # last 30 exchanges
        if not chat_digest:
            return {"notes": "", "updated": False}
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        summary_prompt = (
            "أنت محرر فني لمشروع لعبة. اقرأ محادثة المالك مع AI أدناه واكتب ملخصاً مفصّلاً ومستديماً (Living Project Memory) "
            "بصيغة Markdown يضم: الرؤية العامة، نوع اللعبة، الجمهور، الـart style المتفق عليه، العناصر المعتمدة "
            "(قائمة)، القرارات الرئيسية، ما تم إنجازه، ما تبقى. اكتبها بضمير المتكلم 'أنا فهمت كذا وكذا'. "
            "نقاط مرقّمة، عربية واضحة. حد 1500 كلمة.\n\n"
            f"تفاصيل المشروع:\nالعنوان: {project.get('title','')}\nالوصف: {project.get('description','')}\n\n"
            f"المحادثة:\n{chat_digest[:30000]}"
        )
        notes = ""
        try:
            if gemini_key:
                async with httpx.AsyncClient(timeout=60.0) as cli:
                    r = await cli.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
                        json={"contents": [{"parts": [{"text": summary_prompt}]}], "generationConfig": {"temperature": 0.3, "maxOutputTokens": 3000}},
                    )
                    if r.status_code == 200:
                        notes = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if not notes and anthropic_key:
                async with httpx.AsyncClient(timeout=60.0) as cli:
                    r = await cli.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                        json={"model": "claude-sonnet-4-5-20250929", "max_tokens": 3000, "messages": [{"role": "user", "content": summary_prompt}]},
                    )
                    if r.status_code == 200:
                        blocks = r.json().get("content", [])
                        notes = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except Exception as e:
            logger.warning(f"[games] notes refresh failed: {e}")
        if notes:
            await db.game_projects.update_one(
                {"id": project_id},
                {"$set": {"ai_notes": notes, "notes_updated_at": datetime.now(timezone.utc).isoformat()}},
            )
        return {"notes": notes, "updated": bool(notes)}

    # ───────────────────────────────────────────────────────────
    # 📂 GET /projects — list all current user's projects (for "My Projects" page)
    # ───────────────────────────────────────────────────────────
    @router.get("/projects")
    async def list_user_projects(user=Depends(get_current_user), game_type: Optional[str] = None):
        from modules.games.billing import get_project_storage_info
        query = {"user_id": user["user_id"], "deleted_at": {"$in": [None, ""]}}
        if game_type:
            query["game_type"] = game_type
        cursor = db.game_projects.find(query, {"_id": 0}).sort("created_at", -1)
        items = []
        async for p in cursor:
            info = get_project_storage_info(p)
            items.append({
                "id": p["id"],
                "title": p.get("title", ""),
                "description": (p.get("description") or "")[:200],
                "game_type": p.get("game_type"),
                "programming_type": p.get("programming_type"),
                "current_phase": p.get("current_phase"),
                "created_at": p.get("created_at"),
                "updated_at": p.get("updated_at"),
                "tier": info.get("tier"),
                "tier_label": info.get("tier_label"),
                "size_mb": info.get("size_mb"),
                "limit_mb": info.get("limit_mb"),
                "expires_at": info.get("expires_at"),
                "has_notes": bool(p.get("ai_notes")),
                "asset_count": sum(len(p.get("assets", {}).get(k, [])) for k in ("images", "models3d", "audio", "videos")),
            })
        return {"projects": items}

    # ───────────────────────────────────────────────────────────
    # 🗑️ Soft-delete & restore — 30-day trash bin
    # ───────────────────────────────────────────────────────────
    TRASH_DAYS = 30

    @router.delete("/project/{project_id}")
    async def soft_delete_project(project_id: str, user=Depends(get_current_user)):
        """Move project to trash. Auto-purged after 30 days. Restorable until then."""
        r = await db.game_projects.update_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"$set": {"deleted_at": datetime.now(timezone.utc).isoformat()}},
        )
        if r.matched_count == 0:
            raise HTTPException(404, "Project not found")
        return {"ok": True, "trashed": True, "expires_in_days": TRASH_DAYS}

    @router.post("/project/{project_id}/restore")
    async def restore_project(project_id: str, user=Depends(get_current_user)):
        """Restore a trashed project."""
        r = await db.game_projects.update_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"$set": {"deleted_at": None}},
        )
        if r.matched_count == 0:
            raise HTTPException(404, "Project not found")
        return {"ok": True, "restored": True}

    @router.delete("/project/{project_id}/asset/{asset_id}")
    async def soft_delete_asset(project_id: str, asset_id: str, user=Depends(get_current_user)):
        """Soft-delete an asset (image / 3d / audio / video) by stamping deleted_at."""
        project = await db.game_projects.find_one({"id": project_id, "user_id": user["user_id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        now_iso = datetime.now(timezone.utc).isoformat()
        # Update inside assets buckets
        modified = False
        assets = project.get("assets") or {}
        for bucket in ("images", "models3d", "audio", "videos"):
            items = assets.get(bucket) or []
            for a in items:
                if a.get("id") == asset_id and not a.get("deleted_at"):
                    a["deleted_at"] = now_iso
                    modified = True
            if modified:
                await db.game_projects.update_one(
                    {"id": project_id},
                    {"$set": {f"assets.{bucket}": items}},
                )
                break
        # Also stamp the asset inside any phase message's generated_assets so chat history reflects deletion
        phases = project.get("phases") or {}
        for ph_id, ph in phases.items():
            msgs = ph.get("messages") or []
            ph_modified = False
            for m in msgs:
                for a in (m.get("generated_assets") or []):
                    if a.get("id") == asset_id and not a.get("deleted_at"):
                        a["deleted_at"] = now_iso
                        ph_modified = True
            if ph_modified:
                await db.game_projects.update_one(
                    {"id": project_id},
                    {"$set": {f"phases.{ph_id}.messages": msgs}},
                )
                modified = True
        if not modified:
            raise HTTPException(404, "Asset not found")
        return {"ok": True, "trashed": True, "expires_in_days": TRASH_DAYS}

    @router.post("/project/{project_id}/asset/{asset_id}/restore")
    async def restore_asset(project_id: str, asset_id: str, user=Depends(get_current_user)):
        """Restore a soft-deleted asset."""
        project = await db.game_projects.find_one({"id": project_id, "user_id": user["user_id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        modified = False
        assets = project.get("assets") or {}
        for bucket in ("images", "models3d", "audio", "videos"):
            items = assets.get(bucket) or []
            for a in items:
                if a.get("id") == asset_id and a.get("deleted_at"):
                    a["deleted_at"] = None
                    modified = True
            if modified:
                await db.game_projects.update_one(
                    {"id": project_id},
                    {"$set": {f"assets.{bucket}": items}},
                )
                break
        phases = project.get("phases") or {}
        for ph_id, ph in phases.items():
            msgs = ph.get("messages") or []
            ph_modified = False
            for m in msgs:
                for a in (m.get("generated_assets") or []):
                    if a.get("id") == asset_id and a.get("deleted_at"):
                        a["deleted_at"] = None
                        ph_modified = True
            if ph_modified:
                await db.game_projects.update_one(
                    {"id": project_id},
                    {"$set": {f"phases.{ph_id}.messages": msgs}},
                )
                modified = True
        if not modified:
            raise HTTPException(404, "Asset not found")
        return {"ok": True, "restored": True}

    @router.get("/trash")
    async def list_trash(user=Depends(get_current_user)):
        """List all soft-deleted projects + assets for the current user (≤30 days old)."""
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=TRASH_DAYS)).isoformat()
        # Trashed projects (not yet purged)
        trashed_projects = []
        async for p in db.game_projects.find(
            {"user_id": user["user_id"], "deleted_at": {"$gte": cutoff}}, {"_id": 0}
        ).sort("deleted_at", -1):
            trashed_projects.append({
                "id": p["id"],
                "title": p.get("title", ""),
                "description": (p.get("description") or "")[:120],
                "game_type": p.get("game_type"),
                "deleted_at": p.get("deleted_at"),
            })
        # Trashed assets across all (still-alive) projects
        trashed_assets = []
        async for p in db.game_projects.find(
            {"user_id": user["user_id"], "deleted_at": {"$in": [None, ""]}}, {"_id": 0}
        ):
            for bucket in ("images", "models3d", "audio", "videos"):
                for a in (p.get("assets", {}) or {}).get(bucket, []) or []:
                    if a.get("deleted_at") and a["deleted_at"] >= cutoff:
                        trashed_assets.append({
                            "id": a["id"],
                            "project_id": p["id"],
                            "project_title": p.get("title", ""),
                            "name": a.get("name") or a.get("prompt", "")[:80],
                            "type": a.get("type"),
                            "image_url": a.get("image_url"),
                            "audio_url": a.get("audio_url"),
                            "video_url": a.get("video_url"),
                            "model_url": a.get("model_url"),
                            "cdn_url": a.get("cdn_url"),
                            "deleted_at": a["deleted_at"],
                        })
        return {"projects": trashed_projects, "assets": trashed_assets, "expires_in_days": TRASH_DAYS}
    
    # ───────────────────────────────────────────────────────────
    # 💰 GET /project/{project_id}/billing — storage usage + tier info
    # ───────────────────────────────────────────────────────────
    @router.get("/project/{project_id}/billing")
    async def get_project_billing(project_id: str, user=Depends(get_current_user)):
        """Return tier, current storage usage, limit, expiry date, percent used."""
        from modules.games.billing import get_project_storage_info, TIERS
        project = await db.game_projects.find_one({"id": project_id, "user_id": user["user_id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        info = get_project_storage_info(project)
        info["all_tiers"] = TIERS  # so frontend can show upgrade options
        return info

    # ───────────────────────────────────────────────────────────
    # 🪙 POST /project/{project_id}/upgrade — switch project tier
    # Note: real Stripe checkout is handled at /api/billing/checkout
    # ───────────────────────────────────────────────────────────
    @router.post("/project/{project_id}/upgrade")
    async def upgrade_project_tier(project_id: str, tier: str = Form(...), user=Depends(get_current_user)):
        """Mark project as upgraded after successful payment.
        Only callable internally or via verified webhook in production.
        For owner role we allow direct upgrade (no payment required)."""
        from modules.games.billing import TIERS
        if tier not in TIERS:
            raise HTTPException(400, f"Unknown tier: {tier}")
        # Verify ownership
        project = await db.game_projects.find_one({"id": project_id, "user_id": user["user_id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        # Owner can switch tier freely; regular users would go through Stripe checkout first
        user_doc = await db.users.find_one({"id": user["user_id"]}, {"role": 1, "is_owner": 1})
        is_owner = bool((user_doc or {}).get("is_owner") or (user_doc or {}).get("role") == "owner")
        if not is_owner and tier != "free":
            raise HTTPException(402, "الترقية تتطلب الدفع — استخدم /api/billing/checkout")
        await db.game_projects.update_one(
            {"id": project_id},
            {"$set": {"billing_tier": tier, "tier_updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        return {"ok": True, "tier": tier}

    # ───────────────────────────────────────────────────────────
    # 🧹 POST /admin/games/cleanup-expired — manual trigger (also runs nightly)
    # ───────────────────────────────────────────────────────────
    @router.post("/admin/cleanup-expired")
    async def cleanup_expired(user=Depends(get_current_user)):
        """Owner-only: delete expired free-tier projects + their files."""
        user_doc = await db.users.find_one({"id": user["user_id"]}, {"role": 1, "is_owner": 1})
        if not (user_doc and (user_doc.get("is_owner") or user_doc.get("role") == "owner")):
            raise HTTPException(403, "Owner only")
        from modules.games.billing import cleanup_expired_projects
        result = await cleanup_expired_projects(db)
        return {"ok": True, **result}
    
    # ───────────────────────────────────────────────────────────
    # ✅ POST /project/{project_id}/approve-asset — Approve/reject asset
    # ───────────────────────────────────────────────────────────
    @router.post("/project/{project_id}/approve-asset")
    async def approve_asset(
        project_id: str,
        payload: AssetApproval,
        user=Depends(get_current_user)
    ):
        """Client approves or rejects an asset"""
        project = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}
        )
        if not project:
            raise HTTPException(404, "Project not found")
        
        # Find asset in project.assets
        asset = None
        asset_type = None
        for atype, assets_list in project.get("assets", {}).items():
            for a in assets_list:
                if a.get("id") == payload.asset_id:
                    asset = a
                    asset_type = atype
                    break
        
        if not asset:
            raise HTTPException(404, "Asset not found")
        
        # Update approval status
        asset["approved"] = payload.approved
        asset["feedback"] = payload.feedback
        
        # If approved, add to memory
        if payload.approved:
            await db.game_projects.update_one(
                {"id": project_id},
                {
                    "$push": {
                        "approved_assets": {
                            "id": asset["id"],
                            "type": asset_type,
                            "name": asset.get("name", "Unnamed"),
                            "description": asset.get("description", ""),
                            "url": asset.get("url"),
                            "approved_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                }
            )
        
        # Update asset in place
        await db.game_projects.update_one(
            {"id": project_id},
            {"$set": {f"assets.{asset_type}": project["assets"][asset_type]}}
        )
        
        return {"ok": True, "asset": asset}
    
    # ───────────────────────────────────────────────────────────
    # 🔓 POST /project/{project_id}/unlock-phase — Unlock next phase
    # ───────────────────────────────────────────────────────────
    @router.post("/project/{project_id}/unlock-phase")
    async def unlock_phase(project_id: str, phase_id: str, user=Depends(get_current_user)):
        """Unlock a phase (no restrictions)"""
        project = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}
        )
        if not project:
            raise HTTPException(404, "Project not found")
        
        if phase_id not in project["phases"]:
            raise HTTPException(400, "Invalid phase")
        
        await db.game_projects.update_one(
            {"id": project_id},
            {
                "$set": {
                    f"phases.{phase_id}.status": "active",
                    "current_phase": phase_id,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        return {"ok": True}
    
    # ───────────────────────────────────────────────────────────
    # 🎨 POST /project/{project_id}/add-asset — Manually add asset
    # ───────────────────────────────────────────────────────────
    @router.post("/project/{project_id}/add-asset")
    async def add_asset(
        project_id: str,
        asset_type: str,
        name: str,
        description: str,
        url: Optional[str] = None,
        user=Depends(get_current_user)
    ):
        """Manually add asset (for testing or external uploads)"""
        project = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}
        )
        if not project:
            raise HTTPException(404, "Project not found")
        
        if asset_type not in ["characters", "environments", "ui", "code", "docs"]:
            raise HTTPException(400, "Invalid asset_type")
        
        asset = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "url": url,
            "approved": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.game_projects.update_one(
            {"id": project_id},
            {
                "$push": {f"assets.{asset_type}": asset},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        return {"ok": True, "asset": asset}
    
    # ───────────────────────────────────────────────────────────
    # 🌐 POST /project/{project_id}/set-preview — Set live preview URL
    # ───────────────────────────────────────────────────────────
    @router.post("/project/{project_id}/set-preview")
    async def set_preview(
        project_id: str,
        preview_url: str,
        user=Depends(get_current_user)
    ):
        """Set live preview URL for the game"""
        await db.game_projects.update_one(
            {"id": project_id, "user_id": user["user_id"]},
            {
                "$set": {
                    "preview_url": preview_url,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        return {"ok": True}

    # ───────────────────────────────────────────────────────────
    # 🚀 POST /project/{id}/build — kick off background build, return immediately
    # GET  /project/{id}/build-info — current build metadata + status
    # ───────────────────────────────────────────────────────────
    @router.post("/project/{project_id}/build")
    async def build_live_site(project_id: str, user=Depends(get_current_user)):
        """Kick off background build job. Returns 202 immediately — UI polls /build-info for status."""
        proj = await db.game_projects.find_one({"id": project_id})
        if not proj:
            raise HTTPException(404, "Project not found")
        if proj.get("user_id") != user["user_id"]:
            raise HTTPException(403, "Not your project")
        # Prevent double-fires
        if proj.get("build_status") == "building":
            return {"ok": True, "status": "building", "started_at": proj.get("build_started_at")}
        await db.game_projects.update_one(
            {"id": project_id},
            {"$set": {
                "build_status": "building",
                "build_error": None,
                "build_started_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        import asyncio as _aio_b
        _aio_b.create_task(_run_build_in_background(db, project_id, user["user_id"]))
        return {"ok": True, "status": "building", "poll_url": f"/api/games/project/{project_id}/build-info"}

    @router.get("/project/{project_id}/build-info")
    async def build_info(project_id: str, user=Depends(get_current_user)):
        proj = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"preview_url": 1, "last_built_at": 1, "build_size_bytes": 1,
             "build_status": 1, "build_error": 1, "build_started_at": 1, "_id": 0},
        )
        if not proj:
            raise HTTPException(404, "Project not found")
        return {
            "preview_url": proj.get("preview_url"),
            "last_built_at": proj.get("last_built_at"),
            "build_size_bytes": proj.get("build_size_bytes"),
            "status": proj.get("build_status") or ("ready" if proj.get("preview_url") else "idle"),
            "error": proj.get("build_error"),
            "started_at": proj.get("build_started_at"),
        }

    # ───────────────────────────────────────────────────────────
    # 🌐 GET /games-live/{project_id}/ — serve the live built bundle (public)
    # Note: kept under /api/ so Kubernetes ingress routes it to the backend.
    # The url stamped on `project.preview_url` is /api/games-live/{id}/
    # ───────────────────────────────────────────────────────────
    @router.get("/games-live/{project_id}/")
    @router.get("/games-live/{project_id}")
    async def serve_live_bundle(project_id: str):
        from fastapi.responses import HTMLResponse
        from modules.games.builder import load_bundle_html
        html = await load_bundle_html(db, project_id)
        if not html:
            return HTMLResponse(
                "<!doctype html><html dir='rtl'><head><meta charset='utf-8'>"
                "<title>الموقع غير منشور بعد</title>"
                "<style>body{font-family:system-ui;background:#0a0a0a;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}"
                ".card{padding:2rem;border:1px solid #333;border-radius:1rem;max-width:480px}</style></head>"
                "<body><div class='card'><h1>🛠️ الموقع غير منشور بعد</h1>"
                "<p>روح للاستوديو واضغط زر <b>🚀 ابني وانشر اللايف</b> عشان يطلع لك الموقع هنا.</p></div></body></html>",
                status_code=404,
            )
        return HTMLResponse(html)

    # ───────────────────────────────────────────────────────────
    # ✏️ POST /project/{id}/asset/{aid}/edit — Flux Redux img2img edit
    # ───────────────────────────────────────────────────────────
    @router.post("/project/{project_id}/asset/{asset_id}/edit")
    async def edit_asset(
        project_id: str,
        asset_id: str,
        request: Request,
        user=Depends(get_current_user)
    ):
        """Re-imagine an existing asset using Flux Redux. Body: { edit_prompt: str }"""
        body = await request.json()
        edit_prompt = (body.get("edit_prompt") or "").strip()
        if not edit_prompt:
            raise HTTPException(400, "edit_prompt required")
        proj = await db.game_projects.find_one({"id": project_id, "user_id": user["user_id"]})
        if not proj:
            raise HTTPException(404, "Project not found")
        # Find source asset (use CDN url if available — survives redeploys)
        src_asset = None
        for bucket in ("images",):
            for a in (proj.get("assets", {}) or {}).get(bucket, []) or []:
                if a.get("id") == asset_id and not a.get("deleted_at"):
                    src_asset = a
                    break
        if not src_asset:
            raise HTTPException(404, "Source asset not found")
        src_url = src_asset.get("cdn_url") or src_asset.get("image_url") or ""
        # If only local URL, build absolute
        if src_url.startswith("/api/"):
            src_url = f"{os.environ.get('REACT_APP_BACKEND_URL', '')}{src_url}"
        try:
            from modules.games.fal_tools import edit_image_with_prompt
            from modules.games.persistence import persist_bytes as _persist
            new_asset = await edit_image_with_prompt(src_url, edit_prompt, project_id)
            raw = new_asset.pop("_bytes", None)
            if raw:
                try:
                    await _persist(db, new_asset["id"], raw, "image/png", project_id)
                except Exception as pe:
                    logger.warning(f"[edit] persist failed: {pe}")
            new_asset["phase_id"] = src_asset.get("phase_id")
            new_asset["edited_from"] = asset_id
            await db.game_projects.update_one(
                {"id": project_id},
                {"$push": {"assets.images": new_asset}},
            )
            return {"ok": True, "asset": {k: v for k, v in new_asset.items() if not k.startswith("_")}}
        except Exception as e:
            logger.exception(f"[edit] failed: {e}")
            raise HTTPException(500, f"Edit failed: {str(e)[:200]}")

    # ───────────────────────────────────────────────────────────
    # 🔬 POST /project/{id}/qa-analyze — Claude reviews the live HTML
    # ───────────────────────────────────────────────────────────
    @router.post("/project/{project_id}/qa-analyze")
    async def qa_analyze_live(project_id: str, user=Depends(get_current_user)):
        """Kick off async QA review. Returns 202 immediately, poll /qa-status."""
        proj = await db.game_projects.find_one({"id": project_id, "user_id": user["user_id"]})
        if not proj:
            raise HTTPException(404, "Project not found")
        if proj.get("qa_status") == "running":
            return {"ok": True, "status": "running"}
        await db.game_projects.update_one(
            {"id": project_id},
            {"$set": {"qa_status": "running", "qa_error": None}},
        )
        import asyncio as _aio_qa
        _aio_qa.create_task(_run_qa_in_background(db, project_id))
        return {"ok": True, "status": "running"}

    @router.get("/project/{project_id}/qa-status")
    async def qa_status(project_id: str, user=Depends(get_current_user)):
        proj = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"qa_status": 1, "qa_error": 1, "last_qa_report": 1, "last_qa_at": 1, "_id": 0},
        )
        if not proj:
            raise HTTPException(404, "Project not found")
        return {
            "status": proj.get("qa_status") or "idle",
            "error": proj.get("qa_error"),
            "report": proj.get("last_qa_report"),
            "at": proj.get("last_qa_at"),
        }

    # ───────────────────────────────────────────────────────────
    # 🎨 PUT /project/{id}/style-profile — set the art-direction preset
    # Valid: realistic, stylized (default), anime, low_poly, pixel
    # ───────────────────────────────────────────────────────────
    @router.put("/project/{project_id}/style-profile")
    async def set_style_profile(project_id: str, request: Request, user=Depends(get_current_user)):
        body = await request.json()
        style = (body.get("style_profile") or "").strip().lower()
        if style not in ("realistic", "stylized", "anime", "low_poly", "pixel"):
            raise HTTPException(400, "Invalid style_profile")
        r = await db.game_projects.update_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"$set": {"style_profile": style}},
        )
        if r.matched_count == 0:
            raise HTTPException(404, "Project not found")
        return {"ok": True, "style_profile": style}

    # ───────────────────────────────────────────────────────────
    # 📊 GET /admin/unparsed-tags — owner sees AI tag variations the parser missed
    # ───────────────────────────────────────────────────────────
    @router.get("/admin/unparsed-tags")
    async def list_unparsed_tags(user=Depends(get_current_user), limit: int = 50):
        u = await db.users.find_one({"id": user["user_id"]}, {"is_owner": 1, "role": 1})
        if not (u and (u.get("is_owner") or u.get("role") == "owner")):
            raise HTTPException(403, "Owner only")
        items = []
        async for it in db.games_unparsed_tags.find({}, {"_id": 0}).sort("count", -1).limit(min(limit, 200)):
            items.append(it)
        return {"items": items, "total": len(items)}

    # ───────────────────────────────────────────────────────────
    # 🎨 LoRA STYLE TRAINING — train a project-specific Flux LoRA on
    # the approved images so future generations stay 100% consistent.
    # ───────────────────────────────────────────────────────────
    @router.post("/project/{project_id}/train-style")
    async def start_style_training(project_id: str, user=Depends(get_current_user)):
        proj = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"assets.images": 1, "lora": 1, "title": 1},
        )
        if not proj:
            raise HTTPException(404, "Project not found")

        # Block double-trigger while already in flight
        cur = (proj.get("lora") or {})
        if cur.get("status") in ("queued", "training"):
            return {"ok": True, "already_running": True, **cur}

        # Sanity-check we have enough approved images
        imgs = ((proj.get("assets") or {}).get("images") or [])
        approved = [a for a in imgs if a.get("approved")]
        from modules.games.lora_training import MIN_TRAIN_IMAGES, run_style_training_background
        if len(approved) < MIN_TRAIN_IMAGES:
            raise HTTPException(
                400,
                f"تحتاج على الأقل {MIN_TRAIN_IMAGES} صور معتمدة لتدريب نمط (الحالي: {len(approved)})."
            )

        await db.game_projects.update_one(
            {"id": project_id},
            {"$set": {
                "lora.status": "queued",
                "lora.error": None,
                "lora.started_at": datetime.now(timezone.utc).isoformat(),
            }},
        )

        # Fire-and-forget background task. Training takes 5-10 min.
        import asyncio as _aio
        _aio.create_task(run_style_training_background(db, project_id))

        return {
            "ok": True,
            "status": "queued",
            "num_images": len(approved),
            "message": "بدأ تدريب نمط الصور. خذ راحة ~5-10 دقايق ثم رجع تابع الحالة.",
        }

    @router.get("/project/{project_id}/train-style")
    async def get_style_training_status(project_id: str, user=Depends(get_current_user)):
        proj = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"lora": 1, "assets.images": 1},
        )
        if not proj:
            raise HTTPException(404, "Project not found")
        cur = (proj.get("lora") or {})
        imgs = ((proj.get("assets") or {}).get("images") or [])
        approved_count = sum(1 for a in imgs if a.get("approved"))
        return {
            "ok": True,
            "status": cur.get("status") or "idle",   # idle | queued | training | ready | error
            "lora_url": cur.get("lora_url"),
            "trigger_word": cur.get("trigger_word"),
            "num_images": cur.get("num_images"),
            "error": cur.get("error"),
            "started_at": cur.get("started_at"),
            "finished_at": cur.get("finished_at"),
            "approved_images_available": approved_count,
        }

    @router.delete("/project/{project_id}/train-style")
    async def reset_style_training(project_id: str, user=Depends(get_current_user)):
        """Owner-only: wipe the trained LoRA so the project falls back to default Flux Pro Ultra."""
        r = await db.game_projects.update_one(
            {"id": project_id, "user_id": user["user_id"]},
            {"$unset": {"lora": ""}},
        )
        if r.matched_count == 0:
            raise HTTPException(404, "Project not found")
        return {"ok": True, "reset": True}

    # ───────────────────────────────────────────────────────────
    # 🩺 GET /health — public lightweight diagnostic for production debug
    # Returns version markers so the owner can verify backend deployment.
    # ───────────────────────────────────────────────────────────
    @router.get("/health")
    async def health_check():
        """Anyone can hit this to verify backend is up + which version is live.
        Use from any browser: GET /api/games/health → shows the latest features."""
        return {
            "ok": True,
            "service": "games",
            "build_marker": "v8_2026_06_05_safety_net_future_tense",  # bump when shipping features
            "features": {
                "image_generation": True,
                "vision_verification": True,
                "style_profiles": ["realistic", "stylized", "anime", "low_poly", "pixel"],
                "live_deploy": True,
                "image_edit_redux": True,
                "qa_analyze": True,
                "soft_delete_trash": True,
                "override_socratic_when_explicit": True,  # ← commit fd8f2de
                "tag_parser_lenient": True,  # ← commit 0f7ddda
                "lora_style_training": True,  # ← NEW: per-project Flux LoRA
            },
            "fal_configured": bool(os.environ.get("FAL_KEY")),
            "anthropic_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return router
