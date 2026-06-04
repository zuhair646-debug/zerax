"""
Game Studio Router — Unified API for Web Games + App Games.

Routes:
- POST /api/games/web/start
- POST /api/games/web/approve-gdd
- POST /api/games/web/generate-assets
- POST /api/games/web/generate-code
- POST /api/games/web/test
- POST /api/games/web/deploy

- POST /api/games/app/start
- POST /api/games/app/approve-gdd
- POST /api/games/app/generate-characters
- POST /api/games/app/select-character
- POST /api/games/app/generate-environment
- POST /api/games/app/design-systems
- POST /api/games/app/integrate-unity
- POST /api/games/app/build
- POST /api/games/app/deploy

- GET /api/games/projects
- GET /api/games/project/:id
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from .web_games import WebGameWorkflow, CREDITS as WEB_CREDITS
from .app_games import AppGameWorkflow, CREDITS as APP_CREDITS


# Request models
class StartWebGameRequest(BaseModel):
    game_idea: str

class ApproveGDDRequest(BaseModel):
    project_id: str
    feedback: Optional[str] = None

class GenerateAssetsRequest(BaseModel):
    project_id: str
    asset_type: str  # "2d_sprites" | "3d_models"
    count: int = 10

class GenerateCodeRequest(BaseModel):
    project_id: str

class TestGameRequest(BaseModel):
    project_id: str

class DeployGameRequest(BaseModel):
    project_id: str
    subdomain: str

class StartAppGameRequest(BaseModel):
    game_idea: str
    reference_images: Optional[List[str]] = None

class GenerateCharactersRequest(BaseModel):
    project_id: str
    character_type: str  # "Hero" | "Warrior" | "Archer" | "Villager"
    count: int = 5

class SelectCharacterRequest(BaseModel):
    project_id: str
    character_id: str

class GenerateEnvironmentRequest(BaseModel):
    project_id: str
    env_name: str
    description: str

class DesignSystemsRequest(BaseModel):
    project_id: str

class IntegrateUnityRequest(BaseModel):
    project_id: str

class BuildRequest(BaseModel):
    project_id: str
    platforms: List[str]  # ["Android", "iOS", "Windows"]

class DeployStoresRequest(BaseModel):
    project_id: str
    platforms: List[str]


def create_game_router(db, get_current_user):
    """Create game studio router."""
    router = APIRouter(prefix="/api/games", tags=["games"])
    
    # ============================================
    # WEB GAMES ROUTES
    # ============================================
    
    @router.post("/web/start")
    async def start_web_game(req: StartWebGameRequest, user=Depends(get_current_user)):
        """Phase 1: Start a new web game project."""
        workflow = WebGameWorkflow(db, user["id"])
        result = await workflow.start_project(req.game_idea)
        return result
    
    @router.post("/web/approve-gdd")
    async def approve_web_gdd(req: ApproveGDDRequest, user=Depends(get_current_user)):
        """Phase 2: Approve GDD or provide feedback."""
        # Get project
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        
        workflow = WebGameWorkflow(db, user["id"])
        workflow.project_id = req.project_id
        result = await workflow.approve_gdd(req.feedback)
        return result
    
    @router.post("/web/generate-assets")
    async def generate_web_assets(req: GenerateAssetsRequest, user=Depends(get_current_user)):
        """Phase 3: Generate 2D/3D assets."""
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        
        workflow = WebGameWorkflow(db, user["id"])
        workflow.project_id = req.project_id
        result = await workflow.generate_assets(req.asset_type, req.count)
        return result
    
    @router.post("/web/generate-code")
    async def generate_web_code(req: GenerateCodeRequest, user=Depends(get_current_user)):
        """Phase 4: Generate full game code."""
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        
        workflow = WebGameWorkflow(db, user["id"])
        workflow.project_id = req.project_id
        result = await workflow.generate_code()
        return result
    
    @router.post("/web/test")
    async def test_web_game(req: TestGameRequest, user=Depends(get_current_user)):
        """Phase 5: Test the game."""
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        
        workflow = WebGameWorkflow(db, user["id"])
        workflow.project_id = req.project_id
        result = await workflow.test_game()
        return result
    
    @router.post("/web/deploy")
    async def deploy_web_game(req: DeployGameRequest, user=Depends(get_current_user)):
        """Phase 6: Deploy to Vercel."""
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        
        workflow = WebGameWorkflow(db, user["id"])
        workflow.project_id = req.project_id
        result = await workflow.deploy(req.subdomain)
        return result
    
    # ============================================
    # APP GAMES ROUTES
    # ============================================
    
    @router.post("/app/start")
    async def start_app_game(req: StartAppGameRequest, user=Depends(get_current_user)):
        """Phase 1: Start a new app game project."""
        workflow = AppGameWorkflow(db, user["id"])
        result = await workflow.start_project(req.game_idea, req.reference_images)
        return result
    
    @router.post("/app/approve-gdd")
    async def approve_app_gdd(req: ApproveGDDRequest, user=Depends(get_current_user)):
        """Phase 2: Approve GDD or provide feedback."""
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        
        workflow = AppGameWorkflow(db, user["id"])
        workflow.project_id = req.project_id
        result = await workflow.approve_gdd(req.feedback)
        return result
    
    @router.post("/app/generate-characters")
    async def generate_app_characters(req: GenerateCharactersRequest, user=Depends(get_current_user)):
        """Phase 3: Generate character designs."""
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        
        workflow = AppGameWorkflow(db, user["id"])
        workflow.project_id = req.project_id
        result = await workflow.generate_characters(req.character_type, req.count)
        return result
    
    @router.post("/app/select-character")
    async def select_app_character(req: SelectCharacterRequest, user=Depends(get_current_user)):
        """Client selects a character design."""
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        
        workflow = AppGameWorkflow(db, user["id"])
        workflow.project_id = req.project_id
        result = await workflow.select_character(req.character_id)
        return result
    
    @router.post("/app/generate-environment")
    async def generate_app_environment(req: GenerateEnvironmentRequest, user=Depends(get_current_user)):
        """Phase 4: Generate environment/scene."""
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        
        workflow = AppGameWorkflow(db, user["id"])
        workflow.project_id = req.project_id
        result = await workflow.generate_environment(req.env_name, req.description)
        return result
    
    @router.post("/app/design-systems")
    async def design_app_systems(req: DesignSystemsRequest, user=Depends(get_current_user)):
        """Phase 5: Design gameplay systems."""
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        
        workflow = AppGameWorkflow(db, user["id"])
        workflow.project_id = req.project_id
        result = await workflow.design_gameplay_systems()
        return result
    
    @router.post("/app/integrate-unity")
    async def integrate_app_unity(req: IntegrateUnityRequest, user=Depends(get_current_user)):
        """Phase 6: Create Unity project."""
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        
        workflow = AppGameWorkflow(db, user["id"])
        workflow.project_id = req.project_id
        result = await workflow.integrate_unity()
        return result
    
    @router.post("/app/build")
    async def build_app_game(req: BuildRequest, user=Depends(get_current_user)):
        """Phase 7: Build APK/IPA/EXE."""
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        
        workflow = AppGameWorkflow(db, user["id"])
        workflow.project_id = req.project_id
        result = await workflow.build_and_test(req.platforms)
        return result
    
    @router.post("/app/deploy")
    async def deploy_app_game(req: DeployStoresRequest, user=Depends(get_current_user)):
        """Phase 8: Deploy to stores."""
        project = await db.game_projects.find_one({"id": req.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "Project not found")
        
        workflow = AppGameWorkflow(db, user["id"])
        workflow.project_id = req.project_id
        result = await workflow.deploy_to_stores(req.platforms)
        return result
    
    # ============================================
    # SHARED ROUTES
    # ============================================
    
    @router.get("/projects")
    async def list_projects(user=Depends(get_current_user)):
        """List all game projects for current user."""
        projects = await db.game_projects.find(
            {"user_id": user["id"]},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        return {"projects": projects}
    
    @router.get("/project/{project_id}")
    async def get_project(project_id: str, user=Depends(get_current_user)):
        """Get detailed project info."""
        project = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["id"]},
            {"_id": 0}
        )
        if not project:
            raise HTTPException(404, "Project not found")
        return project
    
    @router.get("/credits")
    async def get_credit_costs():
        """Get credit costs for all phases."""
        return {
            "web_games": WEB_CREDITS,
            "app_games": APP_CREDITS,
        }
    
    return router
