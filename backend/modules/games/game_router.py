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
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
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
        """Serve generated game asset image (public, no auth — needed for <img src> in chat)."""
        from fastapi.responses import FileResponse
        # Sanitize filename to prevent path traversal
        if "/" in filename or ".." in filename or not filename.endswith(".png"):
            raise HTTPException(400, "Invalid filename")
        path = f"/app/backend/uploads/games/{project_id}/assets/{filename}"
        if not os.path.exists(path):
            raise HTTPException(404, "Asset not found")
        return FileResponse(path, media_type="image/png")

    @router.get("/asset-3d/{project_id}/{filename}")
    async def serve_asset_3d(project_id: str, filename: str):
        """Serve generated 3D model (.glb) — used by Three.js viewer in frontend."""
        from fastapi.responses import FileResponse
        if "/" in filename or ".." in filename or not filename.endswith(".glb"):
            raise HTTPException(400, "Invalid filename")
        path = f"/app/backend/uploads/games/{project_id}/3d/{filename}"
        if not os.path.exists(path):
            raise HTTPException(404, "3D model not found")
        return FileResponse(path, media_type="model/gltf-binary")

    @router.get("/asset-video/{project_id}/{filename}")
    async def serve_asset_video(project_id: str, filename: str):
        """Serve generated video clip (Kling/Sora output)."""
        from fastapi.responses import FileResponse
        if "/" in filename or ".." in filename or not filename.endswith(".mp4"):
            raise HTTPException(400, "Invalid filename")
        path = f"/app/backend/uploads/games/{project_id}/videos/{filename}"
        if not os.path.exists(path):
            raise HTTPException(404, "Video not found")
        return FileResponse(path, media_type="video/mp4")

    @router.get("/asset-audio/{project_id}/{filename}")
    async def serve_asset_audio(project_id: str, filename: str):
        """Serve generated music (.wav from CassetteAI) or SFX (.mp3 from ElevenLabs)."""
        from fastapi.responses import FileResponse
        if "/" in filename or ".." in filename or not (filename.endswith(".mp3") or filename.endswith(".wav")):
            raise HTTPException(400, "Invalid filename")
        path = f"/app/backend/uploads/games/{project_id}/audio/{filename}"
        if not os.path.exists(path):
            raise HTTPException(404, "Audio not found")
        media = "audio/wav" if filename.endswith(".wav") else "audio/mpeg"
        return FileResponse(path, media_type=media)
    
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
    # 📋 GET /projects — List user projects
    # ───────────────────────────────────────────────────────────
    @router.get("/projects")
    async def list_projects(user=Depends(get_current_user)):
        """List all game projects for current user"""
        projects = await db.game_projects.find(
            {"user_id": user["user_id"]},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        return {"projects": projects}
    
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
        
        system_prompt = f"""أنت **مدير إنتاج لعبة محترف** (Senior Game Producer) يعمل على مشروع لعبة {project['game_type']} بأعلى مستويات الجودة الإنتاجية.

**🎮 تفاصيل المشروع:**
- العنوان: {project['title']}
- الوصف: {project['description']}
- نوع البرمجة: {project['programming_type']}
- المرحلة الحالية: {phase_info['title']}
- هدف المرحلة: {phase_info['description']}

{approved_context}{tech_guide}

═══════════════════════════════════════════════════════════════
🚨 **قواعد العمل الإلزامية — يمنع كسرها مهما حصل**
═══════════════════════════════════════════════════════════════

**1. التريّث الإنتاجي — لا تستعجل أبداً**
   ❌ ممنوع تماماً: إنتاج GDD ضخم أو ٥ أصول دفعة واحدة في رسالة واحدة
   ✅ المطلوب: ركّز على **عنصر واحد فقط** في كل رد، ثم انتظر الموافقة قبل الانتقال

**2. الحوار السقراطي — اسأل قبل ما تنفّذ**
   كل رد يجب أن يبدأ بـ١-٣ أسئلة دقيقة للمالك، مثلاً:
   - "قبل ما أصمم القرية، عندي ٣ أسئلة سريعة:
      • هل تبيها قرية في الصحراء أم بين الجبال أم على شاطئ البحر؟
      • الحقول والمباني الصناعية في نفس الـpage ولا نقسّمهم؟
      • الـart style: realistic 3D / pixel art / cel-shaded cartoon؟"

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
        
        # Handle file uploads
        attachments = []
        for file in files:
            content = await file.read()
            filename = file.filename or "untitled"
            # Store file
            file_path = f"/app/backend/uploads/games/{project_id}/{filename}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(content)
            attachments.append({"filename": filename, "path": file_path, "size": len(content)})
        
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
                            "messages": [{"role": "user", "content": message}],
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
            img_tags = re.findall(r'<<IMG:\s*(.+?)>>', ai_message, re.DOTALL)
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
                fal_assets = await parse_and_generate_assets(ai_message, project_id, max_assets_per_turn=3)
                for fa in fal_assets:
                    fa["phase_id"] = phase_id
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

        return {
            "ok": True,
            "message": ai_message,
            "generated_assets": generated_assets,
            "credits_used": 0 if user_is_owner else phase_info["credits"],
            "remaining_balance": user_credits if user_is_owner else (user_credits - phase_info["credits"])
        }
    
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
    
    return router
