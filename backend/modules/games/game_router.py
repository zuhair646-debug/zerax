"""
🎮 Game Studio Router — Web Games + App Games (Phase-Based Workflow)

Endpoints:
  POST /api/games/web/start          — بداية مشروع Web Game
  POST /api/games/web/chat           — محادثة تدريجية (phases)
  POST /api/games/app/start          — بداية مشروع App Game
  POST /api/games/app/chat           — محادثة تدريجية (phases)
  GET  /api/games/projects           — قائمة مشاريع العميل
  GET  /api/games/project/{id}       — تفاصيل مشروع
  POST /api/games/project/{id}/phase — تأكيد مرحلة + الانتقال للتالي
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone
import logging
import os
import httpx

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
        "description": "تصميم آليات اللعب الأساسية (حركة، تفاعل، نظام النقاط)",
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
        "deliverables": ["GDD.md", "Platform Choice (iOS/Android/Both)", "Monetization Strategy"]
    },
    {
        "id": "architecture",
        "title": "🏗️ Architecture & Tech Stack",
        "description": "اختيار المحرك (Unity/Godot/React Native) + بنية المشروع",
        "credits": 120,
        "deliverables": ["Tech Stack Doc", "Project Structure", "Dependencies"]
    },
    {
        "id": "ui_ux",
        "title": "🎨 UI/UX Design",
        "description": "تصميم واجهات الـapp + تجربة المستخدم",
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
        "title": "🔧 Backend & Multiplayer (if needed)",
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
        "description": "نشر على Google Play / App Store + تسليم",
        "credits": 200,
        "deliverables": ["Published App", "Store Listing", "Release APK/IPA"]
    }
]

# ═══════════════════════════════════════════════════════════════
# 🎯 Models
# ═══════════════════════════════════════════════════════════════
class GameStartRequest(BaseModel):
    idea: str
    game_type: str  # "web" or "app"

class GameChatRequest(BaseModel):
    project_id: str
    message: str
    attachments: Optional[List[str]] = []

class PhaseConfirmRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None

# ═══════════════════════════════════════════════════════════════
# 🎯 AI Helper — Gemini Flash (للمحادثات التدريجية)
# ═══════════════════════════════════════════════════════════════
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def call_gemini(system: str, user: str, conversation_history: List[Dict] = None) -> str:
    """استدعاء Gemini 2.0 Flash للمحادثات التدريجية."""
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY غير موجود")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"
    
    contents = []
    if conversation_history:
        for msg in conversation_history[-10:]:  # آخر 10 رسائل
            contents.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [{"text": msg["content"]}]
            })
    
    contents.append({"role": "user", "parts": [{"text": user}]})
    
    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2000
        }
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload)
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
    async def start_web_game(req: GameStartRequest, user=Depends(get_current_user)):
        """بداية مشروع Web Game — ينشئ project + يبدأ Phase 1."""
        project_id = str(uuid.uuid4())
        
        project = {
            "id": project_id,
            "user_id": user["id"],
            "type": "web_game",
            "idea": req.idea,
            "phases": WEB_GAME_PHASES,
            "current_phase": 0,
            "status": "in_progress",
            "conversation": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "total_credits_spent": 0
        }
        
        await db.game_projects.insert_one(project)
        
        # Phase 1 intro
        phase = WEB_GAME_PHASES[0]
        intro = f"""
# {phase['title']}

{phase['description']}

**التكلفة**: {phase['credits']} نقطة  
**ما راح نسلّمه**:  
{chr(10).join(f"• {d}" for d in phase['deliverables'])}

---

**عشان نبدأ، حدثني أكثر عن اللعبة**:
1. وش نوع اللعبة (platformer, puzzle, RPG, strategy...)?
2. مين الجمهور المستهدف (أطفال، مراهقين، كبار)?
3. وش الميزة الرئيسية اللي تبيها تميّز اللعبة؟
        """.strip()
        
        project["conversation"].append({
            "role": "assistant",
            "content": intro,
            "phase": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        await db.game_projects.update_one(
            {"id": project_id},
            {"$set": {"conversation": project["conversation"]}}
        )
        
        return {
            "ok": True,
            "project_id": project_id,
            "message": intro,
            "phase": phase
        }
    
    # ═══════════════════════════════════════════════════════════
    # 🟢 Web Games — Chat
    # ═══════════════════════════════════════════════════════════
    @router.post("/web/chat")
    async def web_game_chat(req: GameChatRequest, user=Depends(get_current_user)):
        """محادثة تدريجية في مشروع Web Game."""
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "المشروع غير موجود")
        
        # أضف رسالة العميل
        project["conversation"].append({
            "role": "user",
            "content": req.message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # الـphase الحالي
        phase_idx = project["current_phase"]
        phase = WEB_GAME_PHASES[phase_idx]
        
        # System prompt للـAI
        system = f"""
أنت مصمم ألعاب محترف. تشتغل على مشروع Web Game في المرحلة: {phase['title']}.

**الهدف من هذه المرحلة**: {phase['description']}

**ما يجب تسليمه**:
{chr(10).join(f"• {d}" for d in phase['deliverables'])}

**دورك**:
- اسأل أسئلة محددة عشان تفهم احتياجات العميل بالضبط
- اقترح خيارات وأفكار احترافية
- لما تكمل كل متطلبات المرحلة، اعرض ملخص نهائي وقل "جاهز للانتقال للمرحلة التالية"
- **مهم**: لا تنتقل للمرحلة التالية إلا لما العميل يوافق

**معلومات المشروع**:
- الفكرة الأساسية: {project['idea']}
        """.strip()
        
        # استدعِ Gemini
        response = await call_gemini(system, req.message, project["conversation"][-10:])
        
        project["conversation"].append({
            "role": "assistant",
            "content": response,
            "phase": phase_idx,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        await db.game_projects.update_one(
            {"id": req.project_id},
            {"$set": {"conversation": project["conversation"]}}
        )
        
        return {
            "ok": True,
            "message": response,
            "phase": phase,
            "can_proceed": "جاهز للانتقال" in response.lower()
        }
    
    # ═══════════════════════════════════════════════════════════
    # 🟢 App Games — Start
    # ═══════════════════════════════════════════════════════════
    @router.post("/app/start")
    async def start_app_game(req: GameStartRequest, user=Depends(get_current_user)):
        """بداية مشروع App Game."""
        project_id = str(uuid.uuid4())
        
        project = {
            "id": project_id,
            "user_id": user["id"],
            "type": "app_game",
            "idea": req.idea,
            "phases": APP_GAME_PHASES,
            "current_phase": 0,
            "status": "in_progress",
            "conversation": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "total_credits_spent": 0
        }
        
        await db.game_projects.insert_one(project)
        
        phase = APP_GAME_PHASES[0]
        intro = f"""
# {phase['title']}

{phase['description']}

**التكلفة**: {phase['credits']} نقطة  
**ما راح نسلّمه**:  
{chr(10).join(f"• {d}" for d in phase['deliverables'])}

---

**عشان نبدأ، أبيك تجاوب على هالأسئلة**:
1. وش نوع اللعبة (action, puzzle, RPG, casual, multiplayer...)?
2. المنصة المستهدفة (iOS فقط، Android فقط، أو الاثنين)?
3. هل تحتاج multiplayer أو leaderboards?
4. وش استراتيجية الربح (مجانية، مدفوعة، إعلانات، in-app purchases)?
        """.strip()
        
        project["conversation"].append({
            "role": "assistant",
            "content": intro,
            "phase": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        await db.game_projects.update_one(
            {"id": project_id},
            {"$set": {"conversation": project["conversation"]}}
        )
        
        return {
            "ok": True,
            "project_id": project_id,
            "message": intro,
            "phase": phase
        }
    
    # ═══════════════════════════════════════════════════════════
    # 🟢 App Games — Chat
    # ═══════════════════════════════════════════════════════════
    @router.post("/app/chat")
    async def app_game_chat(req: GameChatRequest, user=Depends(get_current_user)):
        """محادثة تدريجية في مشروع App Game."""
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "المشروع غير موجود")
        
        project["conversation"].append({
            "role": "user",
            "content": req.message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        phase_idx = project["current_phase"]
        phase = APP_GAME_PHASES[phase_idx]
        
        system = f"""
أنت مصمم ألعاب تطبيقات محترف. تشتغل على مشروع App Game في المرحلة: {phase['title']}.

**الهدف**: {phase['description']}

**التسليمات المطلوبة**:
{chr(10).join(f"• {d}" for d in phase['deliverables'])}

**دورك**:
- اسأل أسئلة تقنية محددة (المحرك، البنية، الأدوات)
- اقترح حلول احترافية (Unity, Godot, React Native...)
- لما تكمل المرحلة، اعرض ملخص وقل "جاهز للانتقال"

**معلومات المشروع**:
{project['idea']}
        """.strip()
        
        response = await call_gemini(system, req.message, project["conversation"][-10:])
        
        project["conversation"].append({
            "role": "assistant",
            "content": response,
            "phase": phase_idx,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        await db.game_projects.update_one(
            {"id": req.project_id},
            {"$set": {"conversation": project["conversation"]}}
        )
        
        return {
            "ok": True,
            "message": response,
            "phase": phase,
            "can_proceed": "جاهز للانتقال" in response.lower()
        }
    
    # ═══════════════════════════════════════════════════════════
    # 🔵 تأكيد مرحلة + الانتقال للتالي
    # ═══════════════════════════════════════════════════════════
    @router.post("/project/{project_id}/phase")
    async def confirm_phase(
        project_id: str,
        req: PhaseConfirmRequest,
        user=Depends(get_current_user)
    ):
        """العميل يوافق على المرحلة → خصم النقاط + الانتقال."""
        project = await db.game_projects.find_one({"id": project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "المشروع غير موجود")
        
        if not req.approved:
            return {"ok": True, "message": "المرحلة لم تُوافق — استمر في المحادثة"}
        
        # خصم النقاط
        phase_idx = project["current_phase"]
        phases = WEB_GAME_PHASES if project["type"] == "web_game" else APP_GAME_PHASES
        phase = phases[phase_idx]
        
        user_balance = await db.users.find_one({"id": user["id"]}, {"balance": 1})
        if not user_balance or user_balance.get("balance", 0) < phase["credits"]:
            raise HTTPException(402, "رصيد غير كافٍ — يُرجى الشحن")
        
        # خصم فعلي
        await db.users.update_one({"id": user["id"]}, {"$inc": {"balance": -phase["credits"]}})
        await db.game_projects.update_one(
            {"id": project_id},
            {
                "$inc": {"current_phase": 1, "total_credits_spent": phase["credits"]},
                "$push": {
                    "conversation": {
                        "role": "system",
                        "content": f"✅ المرحلة {phase['title']} مكتملة — تم خصم {phase['credits']} نقطة",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
            }
        )
        
        # هل خلصت كل المراحل؟
        if phase_idx + 1 >= len(phases):
            await db.game_projects.update_one({"id": project_id}, {"$set": {"status": "completed"}})
            return {
                "ok": True,
                "message": "🎉 المشروع اكتمل! كل المراحل خلصت",
                "completed": True
            }
        
        # المرحلة التالية
        next_phase = phases[phase_idx + 1]
        intro = f"""
---

# {next_phase['title']}

{next_phase['description']}

**التكلفة**: {next_phase['credits']} نقطة  
**التسليمات**:  
{chr(10).join(f"• {d}" for d in next_phase['deliverables'])}

**جاهز؟ ابدأ بإرسال رسالتك الأولى لهذه المرحلة.**
        """.strip()
        
        await db.game_projects.update_one(
            {"id": project_id},
            {"$push": {"conversation": {
                "role": "assistant",
                "content": intro,
                "phase": phase_idx + 1,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }}}
        )
        
        return {
            "ok": True,
            "message": intro,
            "next_phase": next_phase
        }
    
    # ═══════════════════════════════════════════════════════════
    # 🔵 قائمة المشاريع
    # ═══════════════════════════════════════════════════════════
    @router.get("/projects")
    async def list_projects(user=Depends(get_current_user)):
        """قائمة كل مشاريع الألعاب للعميل."""
        projects = await db.game_projects.find(
            {"user_id": user["id"]},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        
        return {"ok": True, "projects": projects}
    
    # ═══════════════════════════════════════════════════════════
    # 🔵 تفاصيل مشروع
    # ═══════════════════════════════════════════════════════════
    @router.get("/project/{project_id}")
    async def get_project(project_id: str, user=Depends(get_current_user)):
        """تفاصيل مشروع واحد."""
        project = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["id"]},
            {"_id": 0}
        )
        if not project:
            raise HTTPException(404, "المشروع غير موجود")
        
        return {"ok": True, "project": project}
    
    # ═══════════════════════════════════════════════════════════
    # 🎮 Play Game (Public)
    # ═══════════════════════════════════════════════════════════
    @router.get("/play/{game_id}", response_class=HTMLResponse)
    async def play_game(game_id: str):
        """Play a deployed game directly (no auth required)."""
        project = await db.game_projects.find_one(
            {"id": game_id, "phase": "deployed"},
            {"_id": 0, "code": 1, "idea": 1, "gdd": 1}
        )
        if not project or not project.get("code"):
            return HTMLResponse(
                content="""
                <html>
                <head><title>Game Not Found</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>🎮 اللعبة غير موجودة</h1>
                    <p>المعرف غير صحيح أو اللعبة لم يتم نشرها بعد.</p>
                </body>
                </html>
                """,
                status_code=404
            )
        
        return HTMLResponse(content=project["code"], status_code=200)
    
    return router
