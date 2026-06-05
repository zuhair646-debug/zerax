"""
🎮 Game Studio Router — Web Games + App Games (Phase-Based Workflow) v2.0

Features:
  • 8 مراحل لـWeb Games، 9 لـApp Games
  • دعم رفع ملفات (مراجع، صور، GDD)
  • تخزين منظّم للـassets (characters, environments, ui, code, docs)
  • لا قيود — كل المراحل مفتوحة للتجربة والتعديل
  • Gemini Flash 2.5 للذكاء السريع
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

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 🎯 Phase Definitions (Web Games)
# ═══════════════════════════════════════════════════════════════
WEB_GAME_PHASES = [
    {
        "id": "discovery",
        "title": "🔍 Discovery & GDD",
        "description": "فهم الفكرة + كتابة Game Design Document",
        "credits": 50,
        "deliverables": ["GDD.md", "Genre", "Target Audience", "Core Mechanics"]
    },
    {
        "id": "mechanics",
        "title": "⚙️ Core Mechanics Design",
        "description": "تصميم آليات اللعب الأساسية",
        "credits": 100,
        "deliverables": ["Mechanics Doc", "Flowchart", "Prototype Sketch"]
    },
    {
        "id": "characters",
        "title": "🎭 Character Design",
        "description": "تصميم الشخصيات (مظهر، قدرات، animations)",
        "credits": 150,
        "deliverables": ["Character Sheets", "Concept Art", "Sprite Assets"]
    },
    {
        "id": "environment",
        "title": "🏞️ Environment Design",
        "description": "تصميم البيئات (خلفيات، tiles، obstacles)",
        "credits": 200,
        "deliverables": ["Environment Sketches", "Tileset", "Background Assets"]
    },
    {
        "id": "assets",
        "title": "🎨 Assets Generation",
        "description": "توليد كل الأصول (UI, sounds, effects)",
        "credits": 100,
        "deliverables": ["UI Kit", "Sound Effects", "Visual Effects"]
    },
    {
        "id": "programming",
        "title": "💻 Programming & Integration",
        "description": "برمجة اللعبة + تكامل الأصول",
        "credits": 300,
        "deliverables": ["Playable Build", "Source Code", "Documentation"]
    },
    {
        "id": "testing",
        "title": "🧪 Testing & QA",
        "description": "اختبار شامل + إصلاح bugs",
        "credits": 100,
        "deliverables": ["Test Report", "Bug Fixes", "Performance Optimization"]
    },
    {
        "id": "deployment",
        "title": "🚀 Deployment & Delivery",
        "description": "نشر اللعبة + تسليم نهائي",
        "credits": 150,
        "deliverables": ["Live Game URL", "Source Package", "User Guide"]
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
        "deliverables": ["GDD.md", "Platform Choice", "Monetization Strategy"]
    },
    {
        "id": "architecture",
        "title": "🏗️ Architecture & Tech Stack",
        "description": "اختيار المحرك (Unity/Godot/Flutter) + بنية المشروع",
        "credits": 120,
        "deliverables": ["Tech Stack Doc", "Project Structure", "Dependencies"]
    },
    {
        "id": "ui_ux",
        "title": "🎨 UI/UX Design",
        "description": "تصميم واجهات + تجربة المستخدم",
        "credits": 150,
        "deliverables": ["Wireframes", "Mockups", "Interactive Prototype"]
    },
    {
        "id": "characters",
        "title": "🎭 Character & Asset Design",
        "description": "تصميم الشخصيات + الأصول المرئية",
        "credits": 200,
        "deliverables": ["Character Models", "Animations", "Icon Set"]
    },
    {
        "id": "backend",
        "title": "🔧 Backend & Multiplayer",
        "description": "بناء الـbackend (leaderboards, accounts, multiplayer)",
        "credits": 250,
        "deliverables": ["API Endpoints", "Database Schema", "Auth System"]
    },
    {
        "id": "programming",
        "title": "💻 Core Programming",
        "description": "برمجة اللعبة + تكامل الأصول",
        "credits": 400,
        "deliverables": ["Alpha Build", "Core Gameplay", "Source Code"]
    },
    {
        "id": "testing",
        "title": "🧪 Testing & QA",
        "description": "اختبار على أجهزة حقيقية + إصلاح bugs",
        "credits": 150,
        "deliverables": ["Beta Build", "Test Report", "Device Compatibility"]
    },
    {
        "id": "store_deployment",
        "title": "🚀 Store Deployment",
        "description": "نشر على App Store / Google Play",
        "credits": 300,
        "deliverables": ["App Store Listing", "APK/IPA", "Store Approval"]
    },
    {
        "id": "live_ops",
        "title": "📊 Live Ops & Updates",
        "description": "إدارة + تحديثات بعد النشر",
        "credits": 100,
        "deliverables": ["Update Plan", "Analytics Setup", "User Support"]
    }
]

# ═══════════════════════════════════════════════════════════════
# 🤖 Gemini Flash 2.5 Helper
# ═══════════════════════════════════════════════════════════════
async def call_gemini(system: str, user_msg: str, history: List[Dict], images: List[bytes] = []) -> str:
    """استدعاء Gemini 2.5 Flash مع دعم الصور."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise HTTPException(500, "GEMINI_API_KEY not configured")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    
    # Build contents
    contents = []
    
    # History
    for msg in history[-10:]:
        contents.append({
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [{"text": msg["content"]}]
        })
    
    # Current message + images
    current_parts = [{"text": f"{system}\n\n{user_msg}"}]
    for img_bytes in images:
        current_parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(img_bytes).decode()
            }
        })
    contents.append({"role": "user", "parts": current_parts})
    
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json={"contents": contents})
        if resp.status_code != 200:
            logger.error(f"Gemini error: {resp.text}")
            raise HTTPException(500, f"Gemini failed: {resp.status_code}")
        
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

# ═══════════════════════════════════════════════════════════════
# 🎯 Router Creation
# ═══════════════════════════════════════════════════════════════
def create_game_router(db, get_current_user):
    router = APIRouter(prefix="/api/games", tags=["games"])
    
    # ═══════════════════════════════════════════════════════════
    # 🟢 Web Games — Start
    # ═══════════════════════════════════════════════════════════
    @router.post("/web/start")
    async def start_web_game(idea: str = Form(...), user=Depends(get_current_user)):
        """بداية مشروع Web Game."""
        project_id = str(uuid.uuid4())
        
        project = {
            "id": project_id,
            "user_id": user["id"],
            "type": "web_game",
            "idea": idea,
            "phases": WEB_GAME_PHASES,
            "current_phase": 0,
            "status": "in_progress",
            "messages": [],
            "assets": {
                "characters": [],
                "environments": [],
                "ui": [],
                "sounds": [],
                "code": [],
                "docs": []
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "total_credits_spent": 0
        }
        
        # Phase 1 intro
        phase = WEB_GAME_PHASES[0]
        intro = f"""# {phase['title']}

{phase['description']}

**التكلفة**: {phase['credits']} نقطة  
**ما راح نسلّمه**:  
{chr(10).join(f"• {d}" for d in phase['deliverables'])}

---

**عشان نبدأ، حدثني أكثر عن اللعبة**:
1. وش نوع اللعبة (platformer, puzzle, RPG, strategy...)?
2. مين الجمهور المستهدف (أطفال، مراهقين، كبار)?
3. وش الميزة الرئيسية اللي تبيها تميّز اللعبة؟

يمكنك أيضاً رفع صور مرجعية أو مستندات GDD إذا عندك.
        """.strip()
        
        project["messages"].append({
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": intro,
            "phase": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        await db.game_projects.insert_one(project)
        
        return {
            "ok": True,
            "project_id": project_id,
            "message": intro
        }
    
    # ═══════════════════════════════════════════════════════════
    # 🟢 Web Games — Chat
    # ═══════════════════════════════════════════════════════════
    @router.post("/web/chat")
    async def web_game_chat(
        message: Optional[str] = Form(None),
        files: List[UploadFile] = File(default=[]),
        audio: Optional[UploadFile] = File(None),
        user=Depends(get_current_user)
    ):
        """محادثة Web Game مع دعم رفع ملفات."""
        # احصل على آخر مشروع web_game للعميل
        project = await db.game_projects.find_one(
            {"user_id": user["id"], "type": "web_game"},
            sort=[("created_at", -1)]
        )
        if not project:
            raise HTTPException(404, "لم تبدأ أي مشروع بعد. ابدأ مشروع جديد أولاً.")
        
        # رفع الملفات (إذا موجودة)
        attachments = []
        images_bytes = []
        for f in files:
            content = await f.read()
            filename = f"{uuid.uuid4()}_{f.filename}"
            # حفظ في /tmp أو S3 (هنا نبسّطها بـbase64 في DB)
            attachments.append({
                "name": f.filename,
                "type": f.content_type,
                "size": len(content),
                "data": base64.b64encode(content).decode() if len(content) < 100000 else None
            })
            if f.content_type.startswith("image/"):
                images_bytes.append(content)
        
        # أضف رسالة العميل
        user_msg = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": message or "📎 ملفات مرفقة",
            "attachments": attachments,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        project["messages"].append(user_msg)
        
        # الـphase الحالي
        phase_idx = project["current_phase"]
        phase = WEB_GAME_PHASES[phase_idx] if phase_idx < len(WEB_GAME_PHASES) else WEB_GAME_PHASES[-1]
        
        # System prompt
        system = f"""أنت مصمم ألعاب ويب محترف.

**المشروع**: {project['idea']}

**المرحلة الحالية**: {phase['title']}
{phase['description']}

**يجب تسليم**:
{chr(10).join(f"• {d}" for d in phase['deliverables'])}

**دورك**:
- اسأل أسئلة محددة عشان تفهم احتياجات العميل
- اقترح تصاميم وأفكار احترافية
- لما تكمل المرحلة، اعرض ملخص واضح واطلب الموافقة
- استخدم markdown للتنسيق
- **لا قيود** — العميل حر في التجربة والتعديل

إذا رفع العميل صور، حللها واقترح أفكار بناءً عليها.
""".strip()
        
        # استدعِ Gemini
        response = await call_gemini(system, message or "شف الصور المرفقة", project["messages"][-10:], images_bytes)
        
        # أضف رد الذكاء
        ai_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": response,
            "phase": phase_idx,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        project["messages"].append(ai_msg)
        
        # حفظ
        await db.game_projects.update_one(
            {"id": project["id"]},
            {"$set": {
                "messages": project["messages"],
                "assets": project.get("assets", {})
            }}
        )
        
        return {
            "ok": True,
            "messages": project["messages"],
            "assets": project.get("assets", {}),
            "current_phase": phase_idx
        }
    
    # ═══════════════════════════════════════════════════════════
    # 🟢 App Games — Start
    # ═══════════════════════════════════════════════════════════
    @router.post("/app/start")
    async def start_app_game(idea: str = Form(...), user=Depends(get_current_user)):
        """بداية مشروع App Game."""
        project_id = str(uuid.uuid4())
        
        project = {
            "id": project_id,
            "user_id": user["id"],
            "type": "app_game",
            "idea": idea,
            "phases": APP_GAME_PHASES,
            "current_phase": 0,
            "status": "in_progress",
            "messages": [],
            "assets": {
                "characters": [],
                "ui": [],
                "code": [],
                "builds": [],
                "docs": []
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "total_credits_spent": 0
        }
        
        phase = APP_GAME_PHASES[0]
        intro = f"""# {phase['title']}

{phase['description']}

**التكلفة**: {phase['credits']} نقطة  
**ما راح نسلّمه**:  
{chr(10).join(f"• {d}" for d in phase['deliverables'])}

---

**عشان نبدأ، حدثني عن التطبيق**:
1. المنصة المستهدفة (iOS, Android, كلاهما)?
2. نوع اللعبة (2D, 3D, Puzzle, Multiplayer...)?
3. الميزانية والجدول الزمني المتوقع؟
4. أي ألعاب مشابهة تعجبك (مرجع)?
        """.strip()
        
        project["messages"].append({
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": intro,
            "phase": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        await db.game_projects.insert_one(project)
        
        return {
            "ok": True,
            "project_id": project_id,
            "message": intro
        }
    
    # ═══════════════════════════════════════════════════════════
    # 🟢 App Games — Chat
    # ═══════════════════════════════════════════════════════════
    @router.post("/app/chat")
    async def app_game_chat(
        message: Optional[str] = Form(None),
        files: List[UploadFile] = File(default=[]),
        audio: Optional[UploadFile] = File(None),
        user=Depends(get_current_user)
    ):
        """محادثة App Game مع دعم رفع ملفات."""
        project = await db.game_projects.find_one(
            {"user_id": user["id"], "type": "app_game"},
            sort=[("created_at", -1)]
        )
        if not project:
            raise HTTPException(404, "لم تبدأ أي مشروع بعد. ابدأ مشروع جديد أولاً.")
        
        # رفع الملفات
        attachments = []
        images_bytes = []
        for f in files:
            content = await f.read()
            attachments.append({
                "name": f.filename,
                "type": f.content_type,
                "size": len(content)
            })
            if f.content_type.startswith("image/"):
                images_bytes.append(content)
        
        user_msg = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": message or "📎 ملفات مرفقة",
            "attachments": attachments,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        project["messages"].append(user_msg)
        
        phase_idx = project["current_phase"]
        phase = APP_GAME_PHASES[phase_idx] if phase_idx < len(APP_GAME_PHASES) else APP_GAME_PHASES[-1]
        
        system = f"""أنت مطوّر ألعاب تطبيقات محترف.

**المشروع**: {project['idea']}

**المرحلة**: {phase['title']}
{phase['description']}

**يجب تسليم**:
{chr(10).join(f"• {d}" for d in phase['deliverables'])}

**دورك**:
- اقترح محركات (Unity 3D, Godot, Flutter لـ2D)
- صمم UI/UX احترافي
- خطط لـmultiplayer/backend إذا مطلوب
- وضّح خطوات النشر على المتاجر
- **لا قيود** — كل الأفكار مقبولة
""".strip()
        
        response = await call_gemini(system, message or "شف الصور", project["messages"][-10:], images_bytes)
        
        ai_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": response,
            "phase": phase_idx,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        project["messages"].append(ai_msg)
        
        await db.game_projects.update_one(
            {"id": project["id"]},
            {"$set": {"messages": project["messages"]}}
        )
        
        return {
            "ok": True,
            "messages": project["messages"],
            "assets": project.get("assets", {}),
            "current_phase": phase_idx
        }
    
    # ═══════════════════════════════════════════════════════════
    # 📋 Projects List
    # ═══════════════════════════════════════════════════════════
    @router.get("/projects")
    async def list_projects(user=Depends(get_current_user)):
        """قائمة مشاريع العميل."""
        projects = await db.game_projects.find(
            {"user_id": user["id"]},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        return {"ok": True, "projects": projects}
    
    # ═══════════════════════════════════════════════════════════
    # 📋 Project Details
    # ═══════════════════════════════════════════════════════════
    @router.get("/project/{project_id}")
    async def get_project(project_id: str, user=Depends(get_current_user)):
        """تفاصيل مشروع."""
        project = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["id"]},
            {"_id": 0}
        )
        if not project:
            raise HTTPException(404, "المشروع غير موجود")
        return {"ok": True, "project": project}
    
    # ═══════════════════════════════════════════════════════════
    # ✅ Approve Phase
    # ═══════════════════════════════════════════════════════════
    @router.post("/project/{project_id}/phase")
    async def approve_phase(project_id: str, user=Depends(get_current_user)):
        """تأكيد المرحلة والانتقال للتالي."""
        project = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["id"]}
        )
        if not project:
            raise HTTPException(404, "المشروع غير موجود")
        
        current = project["current_phase"]
        phases = project["phases"]
        
        if current >= len(phases) - 1:
            return {"ok": False, "error": "أنت في المرحلة الأخيرة"}
        
        # انتقل للمرحلة التالية
        next_phase = current + 1
        await db.game_projects.update_one(
            {"id": project_id},
            {"$set": {"current_phase": next_phase}}
        )
        
        project["current_phase"] = next_phase
        
        return {"ok": True, "project": project}
    
    return router
