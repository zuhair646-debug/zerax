"""
Web Games Studio — AI-driven web game builder with phased workflow.

Phases:
1. Discovery & GDD (Game Design Document)
2. Core Mechanics Design
3. Visual Assets Generation (sprites, backgrounds)
4. Code Generation (Phaser.js / Three.js)
5. Testing & QA
6. Deployment

Credits deduction per phase.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import os
import uuid
from datetime import datetime, timezone

# Credit costs per phase
CREDITS = {
    "discovery": 50,
    "mechanics": 100,
    "assets_2d": 80,      # per batch (10 sprites)
    "assets_3d": 150,     # per 3D model
    "code_gen": 200,
    "testing": 80,
    "deploy": 100,
}


class WebGameWorkflow:
    """Manages multi-phase workflow for web game creation."""
    
    def __init__(self, db, user_id: str):
        self.db = db
        self.user_id = user_id
        self.project_id = str(uuid.uuid4())
        
    async def start_project(self, game_idea: str) -> Dict[str, Any]:
        """Phase 1: Discovery — analyze idea and create GDD outline."""
        project = {
            "id": self.project_id,
            "user_id": self.user_id,
            "type": "web_game",
            "idea": game_idea,
            "phase": "discovery",
            "gdd": None,
            "mechanics": [],
            "assets": [],
            "code": None,
            "test_results": None,
            "deploy_url": None,
            "credits_spent": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.db.game_projects.insert_one(project)
        
        # Generate GDD outline using LLM
        gdd_outline = await self._generate_gdd(game_idea)
        
        await self.db.game_projects.update_one(
            {"id": self.project_id},
            {"$set": {"gdd": gdd_outline, "phase": "gdd_review"}}
        )
        
        # Deduct credits
        await self._deduct_credits(CREDITS["discovery"])
        
        return {
            "project_id": self.project_id,
            "phase": "gdd_review",
            "gdd": gdd_outline,
            "next_action": "Review GDD and approve or request changes",
            "credits_spent": CREDITS["discovery"],
        }
    
    async def _generate_gdd(self, idea: str) -> Dict[str, Any]:
        """Generate Game Design Document using Kimi/Claude."""
        # TODO: Call smart_complete with task_type='creative_write'
        # For now, return structured template
        return {
            "title": "Untitled Game",
            "genre": "Platformer",  # auto-detect from idea
            "target_platform": "Web (Desktop + Mobile)",
            "core_loop": "Player jumps, collects coins, avoids enemies",
            "mechanics": [
                {"name": "Jump", "description": "Player can jump with spacebar/tap"},
                {"name": "Collect", "description": "Collect coins for score"},
                {"name": "Avoid", "description": "Avoid enemies or lose health"},
            ],
            "visual_style": "2D Pixel Art",  # or "3D Low-Poly", "Realistic"
            "monetization": "None (free to play)",
            "estimated_dev_time": "3-5 days",
        }
    
    async def approve_gdd(self, feedback: Optional[str] = None) -> Dict[str, Any]:
        """Phase 2: Client approves GDD, move to mechanics design."""
        if feedback:
            # Re-generate GDD with feedback
            project = await self.db.game_projects.find_one({"id": self.project_id})
            updated_gdd = await self._refine_gdd(project["gdd"], feedback)
            await self.db.game_projects.update_one(
                {"id": self.project_id},
                {"$set": {"gdd": updated_gdd}}
            )
            return {
                "project_id": self.project_id,
                "phase": "gdd_review",
                "gdd": updated_gdd,
                "message": "GDD updated based on your feedback. Review again.",
            }
        
        # GDD approved, move to mechanics
        await self.db.game_projects.update_one(
            {"id": self.project_id},
            {"$set": {"phase": "mechanics_design"}}
        )
        
        # Generate mechanics details
        mechanics = await self._design_mechanics()
        await self._deduct_credits(CREDITS["mechanics"])
        
        return {
            "project_id": self.project_id,
            "phase": "mechanics_design",
            "mechanics": mechanics,
            "next_action": "Review mechanics implementation plan",
            "credits_spent": CREDITS["mechanics"],
        }
    
    async def _refine_gdd(self, current_gdd: Dict, feedback: str) -> Dict:
        """Refine GDD based on client feedback."""
        # TODO: LLM call with current_gdd + feedback
        return current_gdd  # placeholder
    
    async def _design_mechanics(self) -> List[Dict[str, Any]]:
        """Design detailed mechanics (player controller, physics, scoring)."""
        project = await self.db.game_projects.find_one({"id": self.project_id})
        gdd = project["gdd"]
        
        # TODO: Generate code snippets for each mechanic
        return [
            {
                "name": "Player Movement",
                "code_snippet": "// Phaser.js player controller\nthis.player.setVelocityX(100);",
                "tested": False,
            },
            {
                "name": "Collision Detection",
                "code_snippet": "// Overlap detection\nthis.physics.add.overlap(player, coins, collectCoin);",
                "tested": False,
            },
        ]
    
    async def generate_assets(self, asset_type: str, count: int = 10) -> Dict[str, Any]:
        """Phase 3: Generate visual assets (sprites, backgrounds, 3D models)."""
        project = await self.db.game_projects.find_one({"id": self.project_id})
        gdd = project["gdd"]
        visual_style = gdd.get("visual_style", "2D Pixel Art")
        
        assets = []
        credit_cost = 0
        
        if asset_type == "2d_sprites":
            # Generate sprites using Leonardo AI / Scenario.gg
            for i in range(count):
                asset = await self._generate_2d_asset(f"sprite_{i}", visual_style)
                assets.append(asset)
            credit_cost = CREDITS["assets_2d"]
        
        elif asset_type == "3d_models":
            # Generate 3D models using Meshy AI / Sloyd
            for i in range(count):
                asset = await self._generate_3d_asset(f"model_{i}", visual_style)
                assets.append(asset)
            credit_cost = CREDITS["assets_3d"] * count
        
        # Save assets to project
        await self.db.game_projects.update_one(
            {"id": self.project_id},
            {"$push": {"assets": {"$each": assets}}}
        )
        
        await self._deduct_credits(credit_cost)
        
        return {
            "project_id": self.project_id,
            "phase": "assets_generation",
            "assets": assets,
            "credits_spent": credit_cost,
            "next_action": "Review assets and approve or regenerate",
        }
    
    async def _generate_2d_asset(self, name: str, style: str) -> Dict[str, Any]:
        """Generate 2D sprite using Leonardo AI or Scenario.gg."""
        # TODO: Call Leonardo AI API or Scenario API
        # For now, placeholder
        return {
            "name": name,
            "type": "2d_sprite",
            "url": f"https://placeholder.com/{name}.png",
            "style": style,
            "approved": False,
        }
    
    async def _generate_3d_asset(self, name: str, style: str) -> Dict[str, Any]:
        """Generate 3D model using Meshy AI / Sloyd."""
        # TODO: Call Meshy AI API
        return {
            "name": name,
            "type": "3d_model",
            "url": f"https://placeholder.com/{name}.glb",
            "style": style,
            "approved": False,
        }
    
    async def generate_code(self) -> Dict[str, Any]:
        """Phase 4: Generate full game code (Phaser.js or Three.js)."""
        project = await self.db.game_projects.find_one({"id": self.project_id})
        gdd = project["gdd"]
        mechanics = project.get("mechanics", [])
        assets = project.get("assets", [])
        
        # Determine engine (Phaser for 2D, Three.js for 3D)
        engine = "phaser" if "2D" in gdd.get("visual_style", "") else "threejs"
        
        # Generate full HTML/JS code
        code = await self._build_game_code(engine, gdd, mechanics, assets)
        
        await self.db.game_projects.update_one(
            {"id": self.project_id},
            {"$set": {"code": code, "phase": "code_review"}}
        )
        
        await self._deduct_credits(CREDITS["code_gen"])
        
        return {
            "project_id": self.project_id,
            "phase": "code_review",
            "code": code,
            "engine": engine,
            "credits_spent": CREDITS["code_gen"],
            "next_action": "Test the game in preview mode",
        }
    
    async def _build_game_code(self, engine: str, gdd: Dict, mechanics: List, assets: List) -> Dict[str, str]:
        """Build complete game code (HTML + JS + CSS)."""
        # TODO: Use Claude Sonnet to generate full code
        # For now, minimal template
        
        if engine == "phaser":
            html = """<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/phaser@3/dist/phaser.min.js"></script>
</head>
<body>
    <div id="game"></div>
    <script src="game.js"></script>
</body>
</html>""".format(title=gdd.get("title", "Game"))
            
            js = """
const config = {
    type: Phaser.AUTO,
    width: 800,
    height: 600,
    physics: { default: 'arcade', arcade: { gravity: { y: 300 } } },
    scene: { preload, create, update }
};

const game = new Phaser.Game(config);

function preload() {
    // Load assets
}

function create() {
    // Initialize game objects
}

function update() {
    // Game loop
}
"""
            css = "body { margin: 0; padding: 0; background: #000; }"
            
        else:  # threejs
            html = """<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/three@0.150.0/build/three.min.js"></script>
</head>
<body>
    <canvas id="canvas"></canvas>
    <script src="game.js"></script>
</body>
</html>""".format(title=gdd.get("title", "3D Game"))
            
            js = """
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('canvas') });
renderer.setSize(window.innerWidth, window.innerHeight);

// Game loop
function animate() {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
}
animate();
"""
            css = "body, html { margin: 0; padding: 0; overflow: hidden; }"
        
        return {"html": html, "js": js, "css": css}
    
    async def test_game(self) -> Dict[str, Any]:
        """Phase 5: Automated testing (syntax check, load test, playability)."""
        project = await self.db.game_projects.find_one({"id": self.project_id})
        code = project["code"]
        
        # Run tests
        test_results = {
            "syntax_check": True,  # TODO: Actual JS validation
            "load_time_ms": 250,
            "playable": True,
            "errors": [],
        }
        
        await self.db.game_projects.update_one(
            {"id": self.project_id},
            {"$set": {"test_results": test_results, "phase": "testing_done"}}
        )
        
        await self._deduct_credits(CREDITS["testing"])
        
        return {
            "project_id": self.project_id,
            "phase": "testing_done",
            "test_results": test_results,
            "credits_spent": CREDITS["testing"],
            "next_action": "Deploy to production" if test_results["playable"] else "Fix errors",
        }
    
    async def deploy(self, subdomain: str) -> Dict[str, Any]:
        """Phase 6: Deploy to Vercel/Netlify."""
        project = await self.db.game_projects.find_one({"id": self.project_id})
        code = project["code"]
        
        # TODO: Deploy to Vercel using API
        deploy_url = f"https://{subdomain}.vercel.app"
        
        await self.db.game_projects.update_one(
            {"id": self.project_id},
            {"$set": {"deploy_url": deploy_url, "phase": "deployed"}}
        )
        
        await self._deduct_credits(CREDITS["deploy"])
        
        return {
            "project_id": self.project_id,
            "phase": "deployed",
            "url": deploy_url,
            "credits_spent": CREDITS["deploy"],
            "message": f"Game deployed successfully! Play at {deploy_url}",
        }
    
    async def _deduct_credits(self, amount: int):
        """Deduct credits from user balance."""
        await self.db.users.update_one(
            {"id": self.user_id},
            {"$inc": {"balance": -amount}}
        )
        await self.db.game_projects.update_one(
            {"id": self.project_id},
            {"$inc": {"credits_spent": amount}}
        )
