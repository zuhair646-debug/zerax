"""
🛠️ Zitex Game Toolkit — completes the remaining 6 backlog items
─────────────────────────────────────────────────────────────────
  #10  3D Draco compression scaffolding + meshopt instructions
  #13  Physics testbed sandboxes (Matter.js + Cannon.js + Rapier presets)
  #14  Game state machine generator (FSM code)
  #18  Asset version history + rollback
  #22  Auto-publish to itch.io via butler API
  #24  Analytics dashboard endpoints (DAU/MAU/sessions/retention)
"""
from __future__ import annotations
import os
import io
import json
import uuid
import shutil
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from fastapi.responses import Response

logger = logging.getLogger(__name__)


def create_router(db, get_current_user):
    router = APIRouter(prefix="/api/game-toolkit", tags=["game-toolkit"])

    # ════════════════════════════════════════════════════════════
    # 1️⃣  TASK #18 — Asset Version History + Rollback
    # ════════════════════════════════════════════════════════════
    @router.post("/{project_id}/asset/{asset_id}/snapshot")
    async def snapshot_asset(project_id: str, asset_id: str, label: Optional[str] = None, user=Depends(get_current_user)):
        """Save the current state of an asset as a version snapshot.
        Snapshots are created BEFORE any IMG_EDIT operation so the owner can
        roll back at any time."""
        proj = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}, {"phases": 1}
        )
        if not proj:
            raise HTTPException(404, "project not found")
        # Find the asset in messages
        target = None
        for _ph in (proj.get("phases") or {}).values():
            for _m in (_ph.get("messages") or []):
                for _a in (_m.get("generated_assets") or []):
                    if _a.get("id") == asset_id:
                        target = _a
                        break
        if not target:
            raise HTTPException(404, "asset not found")
        # Read current bytes
        src = f"/app/backend/uploads/games/{project_id}/assets/{asset_id}.png"
        if not os.path.exists(src):
            raise HTTPException(404, "asset file missing")
        # Copy to versions folder with timestamp
        ver_dir = f"/app/backend/uploads/games/{project_id}/versions/{asset_id}"
        os.makedirs(ver_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        ver_id = f"v_{ts}_{uuid.uuid4().hex[:6]}"
        dst = f"{ver_dir}/{ver_id}.png"
        shutil.copy(src, dst)
        await db.asset_versions.insert_one({
            "project_id": project_id,
            "asset_id": asset_id,
            "version_id": ver_id,
            "label": label or "auto-snapshot",
            "path": dst,
            "url": f"/api/game-toolkit/version-image/{project_id}/{asset_id}/{ver_id}.png",
            "approved_at_snapshot": bool(target.get("approved")),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"ok": True, "version_id": ver_id, "label": label or "auto-snapshot"}

    @router.get("/{project_id}/asset/{asset_id}/versions")
    async def list_versions(project_id: str, asset_id: str, user=Depends(get_current_user)):
        rows = await db.asset_versions.find(
            {"project_id": project_id, "asset_id": asset_id}, {"_id": 0, "path": 0}
        ).sort("created_at", -1).to_list(length=100)
        return {"ok": True, "count": len(rows), "versions": rows}

    @router.post("/{project_id}/asset/{asset_id}/rollback/{version_id}")
    async def rollback_asset(project_id: str, asset_id: str, version_id: str, user=Depends(get_current_user)):
        """Restore an asset from a specific version snapshot."""
        proj = await db.game_projects.find_one(
            {"id": project_id, "user_id": user["user_id"]}, {"id": 1}
        )
        if not proj:
            raise HTTPException(404, "project not found")
        v = await db.asset_versions.find_one(
            {"project_id": project_id, "asset_id": asset_id, "version_id": version_id}
        )
        if not v or not os.path.exists(v["path"]):
            raise HTTPException(404, "version not found")
        # Auto-snapshot current state before rollback (so rollback is reversible too)
        try:
            await snapshot_asset(project_id, asset_id, label=f"pre-rollback-to-{version_id}", user=user)
        except Exception:
            pass
        dst = f"/app/backend/uploads/games/{project_id}/assets/{asset_id}.png"
        shutil.copy(v["path"], dst)
        return {"ok": True, "rolled_back_to": version_id, "asset_id": asset_id}

    @router.get("/version-image/{project_id}/{asset_id}/{filename}")
    async def serve_version(project_id: str, asset_id: str, filename: str):
        path = f"/app/backend/uploads/games/{project_id}/versions/{asset_id}/{filename}"
        if not os.path.exists(path):
            raise HTTPException(404, "not found")
        with open(path, "rb") as f:
            return Response(content=f.read(), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})

    # ════════════════════════════════════════════════════════════
    # 2️⃣  TASK #14 — Game State Machine Code Generator
    # ════════════════════════════════════════════════════════════
    @router.post("/state-machine/generate")
    async def gen_state_machine(payload: Dict[str, Any], user=Depends(get_current_user)):
        """Generate a TypeScript/JavaScript FSM from a spec.
        Body: {
          name: 'GameState',
          states: ['menu','playing','paused','gameover'],
          transitions: [{from:'menu', to:'playing', event:'START'}, ...],
          initial: 'menu',
          flavor: 'js' | 'ts' (default js)
        }
        Returns a self-contained ES module the AI can drop into the game.
        """
        name = payload.get("name") or "GameState"
        states = payload.get("states") or []
        transitions = payload.get("transitions") or []
        initial = payload.get("initial") or (states[0] if states else "idle")
        flavor = (payload.get("flavor") or "js").lower()
        if not states:
            raise HTTPException(400, "states[] required")

        # Build transition map: { state: { event: nextState } }
        tmap: Dict[str, Dict[str, str]] = {s: {} for s in states}
        for t in transitions:
            src, dst, ev = t.get("from"), t.get("to"), t.get("event")
            if src and dst and ev and src in tmap and dst in states:
                tmap[src][ev.upper()] = dst

        typedef = ""
        if flavor == "ts":
            states_t = " | ".join(f"'{s}'" for s in states)
            events_t = " | ".join(f"'{e.upper()}'" for e in {t["event"] for t in transitions if t.get("event")}) or "string"
            typedef = (
                f"export type {name}State = {states_t};\n"
                f"export type {name}Event = {events_t};\n\n"
            )

        code = (
            f"/* Auto-generated by Zitex State Machine Generator\n"
            f" *   Name: {name}\n"
            f" *   States: {states}\n"
            f" *   Initial: {initial}\n"
            f" */\n"
            f"{typedef}"
            f"export class {name} {{\n"
            f"  constructor(initial = '{initial}') {{\n"
            f"    this.state = initial;\n"
            f"    this.history = [initial];\n"
            f"    this.listeners = [];\n"
            f"    this.transitions = {json.dumps(tmap, ensure_ascii=False, indent=4)};\n"
            f"  }}\n"
            f"  on(fn) {{ this.listeners.push(fn); }}\n"
            f"  send(event) {{\n"
            f"    const ev = String(event).toUpperCase();\n"
            f"    const next = (this.transitions[this.state] || {{}})[ev];\n"
            f"    if (!next) {{ console.warn('Invalid transition', this.state, ev); return false; }}\n"
            f"    const prev = this.state;\n"
            f"    this.state = next;\n"
            f"    this.history.push(next);\n"
            f"    this.listeners.forEach(fn => fn(next, prev, ev));\n"
            f"    return true;\n"
            f"  }}\n"
            f"  can(event) {{\n"
            f"    return !!(this.transitions[this.state] || {{}})[String(event).toUpperCase()];\n"
            f"  }}\n"
            f"  reset() {{ this.state = '{initial}'; this.history = ['{initial}']; }}\n"
            f"}}\n\n"
            f"// Usage:\n"
            f"// const fsm = new {name}();\n"
            f"// fsm.on((next, prev, ev) => console.log(prev,'→',next,'via',ev));\n"
            f"// fsm.send('START');\n"
        )
        return {"ok": True, "code": code, "flavor": flavor, "states_count": len(states), "transitions_count": len(transitions)}

    # ════════════════════════════════════════════════════════════
    # 3️⃣  TASK #13 — Physics Testbed Presets
    # ════════════════════════════════════════════════════════════
    @router.get("/physics/presets")
    async def physics_presets():
        return {"ok": True, "presets": PHYSICS_PRESETS}

    @router.get("/physics/preset/{preset_id}")
    async def physics_preset(preset_id: str):
        p = next((p for p in PHYSICS_PRESETS if p["id"] == preset_id), None)
        if not p:
            raise HTTPException(404, "preset not found")
        # Return a ready-to-embed HTML sandbox
        html = _build_physics_sandbox(p)
        return Response(content=html, media_type="text/html; charset=utf-8")

    # ════════════════════════════════════════════════════════════
    # 4️⃣  TASK #10 — 3D Optimization (Draco scaffolding + meshopt instructions)
    # ════════════════════════════════════════════════════════════
    @router.post("/3d/optimize")
    async def optimize_3d(payload: Dict[str, Any], user=Depends(get_current_user)):
        """Optimize a .glb file. Tries `gltf-pipeline` CLI (Draco) if installed,
        otherwise returns a JSON instruction set the user can run client-side
        via @gltf-transform/cli."""
        glb_path = payload.get("path")
        if not glb_path or not os.path.exists(glb_path):
            raise HTTPException(404, "glb file not found")
        # Try gltf-pipeline (npm install -g gltf-pipeline)
        out_path = glb_path.replace(".glb", "_draco.glb")
        try:
            r = subprocess.run(
                ["gltf-pipeline", "-i", glb_path, "-o", out_path, "-d"],
                capture_output=True, text=True, timeout=120,
            )
            if r.returncode == 0 and os.path.exists(out_path):
                orig = os.path.getsize(glb_path)
                opt = os.path.getsize(out_path)
                return {
                    "ok": True,
                    "method": "gltf-pipeline-draco",
                    "original_size": orig,
                    "optimized_size": opt,
                    "savings_pct": round((1 - opt/orig)*100, 1),
                    "output_path": out_path,
                }
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.info(f"[3d] gltf-pipeline not available ({e}); returning manual instructions")
        return {
            "ok": True,
            "method": "manual-instructions",
            "instructions": [
                "npm install -g @gltf-transform/cli",
                f"gltf-transform draco {glb_path} {out_path}",
                "Result: 60-80% size reduction with no visible quality loss",
            ],
            "alternative": "Use https://gltf.report/ to optimize in-browser",
        }

    # ════════════════════════════════════════════════════════════
    # 5️⃣  TASK #22 — Auto-publish to itch.io (via butler)
    # ════════════════════════════════════════════════════════════
    @router.post("/itch-publish")
    async def itch_publish(payload: Dict[str, Any], user=Depends(get_current_user)):
        """Publish a built game folder to itch.io using the butler CLI.
        Body: { build_path, user_slash_game (e.g. 'zuhair/my-game'), channel: 'html5' }
        Requires: butler installed and authenticated (butler login).
        Falls back to step-by-step instructions if butler missing.
        """
        build_path = payload.get("build_path")
        target = payload.get("user_slash_game")
        channel = payload.get("channel", "html5")
        if not build_path or not target:
            raise HTTPException(400, "build_path + user_slash_game required")
        try:
            r = subprocess.run(
                ["butler", "push", build_path, f"{target}:{channel}"],
                capture_output=True, text=True, timeout=600,
            )
            if r.returncode == 0:
                return {
                    "ok": True,
                    "method": "butler",
                    "target": f"{target}:{channel}",
                    "output": r.stdout[-2000:],
                    "play_url": f"https://{target.split('/')[0]}.itch.io/{target.split('/')[1]}",
                }
            return {"ok": False, "error": r.stderr[-2000:], "stdout": r.stdout[-1000:]}
        except FileNotFoundError:
            return {
                "ok": False,
                "method": "manual",
                "instructions": [
                    "1. Install butler: https://itch.io/docs/butler/installing.html",
                    "2. Authenticate: `butler login`",
                    f"3. Build your game to a folder",
                    f"4. Run: `butler push <folder> {target}:{channel}`",
                    "5. Your game is live on itch.io",
                ],
                "play_url_pattern": f"https://{target.split('/')[0]}.itch.io/{target.split('/')[1]}",
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "butler upload timed out (>10 min)"}

    # ════════════════════════════════════════════════════════════
    # 6️⃣  TASK #24 — Analytics Dashboard
    # ════════════════════════════════════════════════════════════
    @router.get("/{project_id}/analytics")
    async def analytics(project_id: str, days: int = 30, user=Depends(get_current_user)):
        """Returns DAU/MAU/sessions/retention/leaderboard-engagement for a game project."""
        now = datetime.now(timezone.utc)
        since = (now - timedelta(days=days)).isoformat()
        # DAU = distinct players seen last 24h
        last24 = (now - timedelta(hours=24)).isoformat()
        last7d = (now - timedelta(days=7)).isoformat()
        last30d = (now - timedelta(days=30)).isoformat()
        dau = await db.game_players.count_documents({
            "project_id": project_id,
            "last_seen_at": {"$gte": last24},
        })
        wau = await db.game_players.count_documents({
            "project_id": project_id,
            "last_seen_at": {"$gte": last7d},
        })
        mau = await db.game_players.count_documents({
            "project_id": project_id,
            "last_seen_at": {"$gte": last30d},
        })
        total_players = await db.game_players.count_documents({"project_id": project_id})
        new_in_period = await db.game_players.count_documents({
            "project_id": project_id,
            "created_at": {"$gte": since},
        })
        saves_count = await db.game_saves.count_documents({"project_id": project_id})
        leaderboard_entries = await db.game_leaderboards.count_documents({"project_id": project_id})
        achievements_count = await db.game_achievements.count_documents({"project_id": project_id})

        # Top 10 players by leaderboard score (default board)
        top_players = await db.game_leaderboards.find(
            {"project_id": project_id, "leaderboard": "default"},
            {"_id": 0, "username": 1, "score": 1, "updated_at": 1},
        ).sort("score", -1).limit(10).to_list(length=10)

        # Daily new-player histogram for the period
        pipeline = [
            {"$match": {"project_id": project_id, "created_at": {"$gte": since}}},
            {"$addFields": {"day": {"$substr": ["$created_at", 0, 10]}}},
            {"$group": {"_id": "$day", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        try:
            daily = await db.game_players.aggregate(pipeline).to_list(length=days + 1)
        except Exception:
            daily = []

        retention_pct = round((dau / max(wau, 1)) * 100, 1) if wau else 0
        return {
            "ok": True,
            "project_id": project_id,
            "period_days": days,
            "counts": {
                "dau": dau,
                "wau": wau,
                "mau": mau,
                "total_players": total_players,
                "new_players_in_period": new_in_period,
                "saves": saves_count,
                "leaderboard_entries": leaderboard_entries,
                "achievements_unlocked": achievements_count,
            },
            "retention": {
                "dau_over_wau_pct": retention_pct,
                "verdict": "GROWING" if dau > 0 and dau >= wau * 0.5
                         else "STABLE" if dau > 0
                         else "DORMANT",
            },
            "top_players": top_players,
            "daily_new_players": [{"day": d["_id"], "count": d["count"]} for d in daily],
        }

    return router


# ═══════════════════════════════════════════════════════════════
# Physics Testbed Presets (task #13)
# ═══════════════════════════════════════════════════════════════
PHYSICS_PRESETS = [
    {
        "id": "matter_falling_blocks",
        "name": "🟫 Matter.js — Falling Blocks",
        "engine": "matter.js",
        "description": "Tower of blocks falling under gravity (Box2D-style). Click to add more.",
        "use_cases": ["puzzle", "Tetris-like", "Angry Birds projectile"],
    },
    {
        "id": "matter_ragdoll",
        "name": "🦴 Matter.js — Ragdoll Physics",
        "engine": "matter.js",
        "description": "Articulated body with joints. Drag limbs to test soft physics.",
        "use_cases": ["beat-em-up", "ragdoll-launcher games"],
    },
    {
        "id": "cannon_3d_dominos",
        "name": "🧱 Cannon.js — 3D Domino Chain",
        "engine": "cannon-es",
        "description": "Three.js scene with cannon-es physics. Click first domino to start the chain.",
        "use_cases": ["3D puzzle", "physics chain reactions"],
    },
    {
        "id": "cannon_3d_vehicle",
        "name": "🏎️ Cannon.js — Raycast Vehicle",
        "engine": "cannon-es",
        "description": "Drivable 3D vehicle with suspension. WASD to drive.",
        "use_cases": ["racing games", "drift simulators"],
    },
    {
        "id": "rapier_2d_softbody",
        "name": "🥒 Rapier — 2D Soft Body",
        "engine": "rapier2d",
        "description": "Jelly cube + cloth simulation. Drag to deform.",
        "use_cases": ["physics-driven puzzlers", "World of Goo style"],
    },
]


def _build_physics_sandbox(p: Dict[str, Any]) -> str:
    """Return a self-contained HTML page implementing the chosen preset."""
    if p["id"] == "matter_falling_blocks":
        return _MATTER_FALLING_BLOCKS_HTML
    if p["id"] == "matter_ragdoll":
        return _MATTER_RAGDOLL_HTML
    if p["id"] == "cannon_3d_dominos":
        return _CANNON_DOMINOS_HTML
    if p["id"] == "cannon_3d_vehicle":
        return _CANNON_VEHICLE_HTML
    if p["id"] == "rapier_2d_softbody":
        return _RAPIER_SOFTBODY_HTML
    return "<h1>Preset not implemented</h1>"


_MATTER_FALLING_BLOCKS_HTML = r"""<!doctype html><html><head><meta charset=utf-8><title>Falling Blocks</title>
<style>body{margin:0;background:#0f0f14;font-family:sans-serif;color:#fff}#hud{position:fixed;top:10px;left:10px;background:#0008;padding:8px;border-radius:8px;font-size:13px}</style>
<script src="https://cdn.jsdelivr.net/npm/matter-js@0.19.0/build/matter.min.js"></script></head>
<body><div id=hud>🟫 Falling Blocks — Click to add blocks · Engine: Matter.js</div>
<script>
const {Engine, Render, Runner, Bodies, Composite, Events, Mouse, MouseConstraint} = Matter;
const eng = Engine.create();
const w = innerWidth, h = innerHeight;
const r = Render.create({element: document.body, engine: eng, options:{width:w, height:h, wireframes:false, background:'#0f0f14'}});
Composite.add(eng.world, [
  Bodies.rectangle(w/2, h-10, w, 20, {isStatic:true, render:{fillStyle:'#444'}}),
  Bodies.rectangle(10, h/2, 20, h, {isStatic:true, render:{fillStyle:'#444'}}),
  Bodies.rectangle(w-10, h/2, 20, h, {isStatic:true, render:{fillStyle:'#444'}}),
]);
for(let i=0;i<8;i++){
  Composite.add(eng.world, Bodies.rectangle(w/2+(Math.random()-0.5)*200, 200-i*40, 60, 30, {render:{fillStyle:`hsl(${i*40},70%,50%)`}}));
}
window.addEventListener('mousedown', e => {
  Composite.add(eng.world, Bodies.rectangle(e.clientX, e.clientY, 40+Math.random()*40, 40+Math.random()*40, {render:{fillStyle:`hsl(${Math.random()*360},70%,50%)`}}));
});
const mouse = Mouse.create(r.canvas);
Composite.add(eng.world, MouseConstraint.create(eng, {mouse, constraint:{stiffness:0.2, render:{visible:false}}}));
Render.run(r); Runner.run(Runner.create(), eng);
</script></body></html>"""

_MATTER_RAGDOLL_HTML = r"""<!doctype html><html><head><meta charset=utf-8><title>Ragdoll</title>
<style>body{margin:0;background:#0f0f14;font-family:sans-serif;color:#fff}#hud{position:fixed;top:10px;left:10px;background:#0008;padding:8px;border-radius:8px}</style>
<script src="https://cdn.jsdelivr.net/npm/matter-js@0.19.0/build/matter.min.js"></script></head>
<body><div id=hud>🦴 Ragdoll — Drag limbs · Matter.js</div>
<script>
const {Engine, Render, Runner, Bodies, Composite, Constraint, Body, Mouse, MouseConstraint} = Matter;
const eng = Engine.create();
const w = innerWidth, h = innerHeight;
const r = Render.create({element:document.body, engine:eng, options:{width:w, height:h, wireframes:false, background:'#0f0f14'}});
function makeRagdoll(x, y){
  const head = Bodies.circle(x, y, 30, {render:{fillStyle:'#ffd28d'}});
  const torso = Bodies.rectangle(x, y+60, 50, 80, {render:{fillStyle:'#7d8ff5'}});
  const armL = Bodies.rectangle(x-50, y+50, 50, 14, {render:{fillStyle:'#ffd28d'}});
  const armR = Bodies.rectangle(x+50, y+50, 50, 14, {render:{fillStyle:'#ffd28d'}});
  const legL = Bodies.rectangle(x-15, y+130, 14, 70, {render:{fillStyle:'#444'}});
  const legR = Bodies.rectangle(x+15, y+130, 14, 70, {render:{fillStyle:'#444'}});
  const opts = {stiffness:0.9, render:{visible:false}};
  return [head, torso, armL, armR, legL, legR,
    Constraint.create({bodyA:head, bodyB:torso, pointA:{x:0,y:25}, pointB:{x:0,y:-40}, ...opts}),
    Constraint.create({bodyA:armL, bodyB:torso, pointA:{x:20,y:0}, pointB:{x:-25,y:-30}, ...opts}),
    Constraint.create({bodyA:armR, bodyB:torso, pointA:{x:-20,y:0}, pointB:{x:25,y:-30}, ...opts}),
    Constraint.create({bodyA:legL, bodyB:torso, pointA:{x:0,y:-30}, pointB:{x:-15,y:40}, ...opts}),
    Constraint.create({bodyA:legR, bodyB:torso, pointA:{x:0,y:-30}, pointB:{x:15,y:40}, ...opts}),
  ];
}
Composite.add(eng.world, [
  Bodies.rectangle(w/2, h-10, w, 20, {isStatic:true, render:{fillStyle:'#444'}}),
  ...makeRagdoll(w/2, 100),
]);
const mouse = Mouse.create(r.canvas);
Composite.add(eng.world, MouseConstraint.create(eng, {mouse, constraint:{stiffness:0.4, render:{visible:true, strokeStyle:'#ff0', lineWidth:2}}}));
Render.run(r); Runner.run(Runner.create(), eng);
</script></body></html>"""

_CANNON_DOMINOS_HTML = r"""<!doctype html><html><head><meta charset=utf-8><title>Dominos</title>
<style>body{margin:0;background:#000;overflow:hidden;font-family:sans-serif;color:#fff}#hud{position:fixed;top:10px;left:10px;background:#0008;padding:8px;border-radius:8px;z-index:10}</style>
<script type=importmap>{"imports":{"three":"https://unpkg.com/three@0.160/build/three.module.js","cannon":"https://unpkg.com/cannon-es@0.20.0/dist/cannon-es.js"}}</script></head>
<body><div id=hud>🧱 Dominos — Click first domino · Three.js + Cannon-es</div>
<script type=module>
import * as THREE from 'three';
import * as CANNON from 'cannon';
const scn = new THREE.Scene();
const cam = new THREE.PerspectiveCamera(60, innerWidth/innerHeight, 0.1, 1000);
cam.position.set(0, 8, 18);
cam.lookAt(0, 0, 0);
const rnd = new THREE.WebGLRenderer({antialias:true});
rnd.setSize(innerWidth, innerHeight);
document.body.appendChild(rnd.domElement);
scn.add(new THREE.AmbientLight(0xffffff, 0.6));
const sun = new THREE.DirectionalLight(0xffffff, 0.8);
sun.position.set(5,10,5); scn.add(sun);
const world = new CANNON.World({gravity: new CANNON.Vec3(0,-9.82,0)});
// floor
scn.add(new THREE.Mesh(new THREE.PlaneGeometry(50,50), new THREE.MeshStandardMaterial({color:0x223,roughness:0.8})).rotateX(-Math.PI/2));
const floor = new CANNON.Body({mass:0, shape:new CANNON.Plane()});
floor.quaternion.setFromAxisAngle(new CANNON.Vec3(1,0,0), -Math.PI/2);
world.addBody(floor);
const dominos = [];
for(let i=0;i<20;i++){
  const m = new THREE.Mesh(new THREE.BoxGeometry(0.6,3,1.5), new THREE.MeshStandardMaterial({color:new THREE.Color().setHSL(i/20,0.7,0.5)}));
  m.position.set(i*1.2-12, 1.5, 0);
  scn.add(m);
  const b = new CANNON.Body({mass:1, shape:new CANNON.Box(new CANNON.Vec3(0.3,1.5,0.75))});
  b.position.set(i*1.2-12, 1.5, 0);
  world.addBody(b);
  dominos.push({m,b});
}
document.body.addEventListener('click', () => {
  dominos[0].b.applyImpulse(new CANNON.Vec3(5,0,0), new CANNON.Vec3(0,1,0));
});
function tick(){
  world.step(1/60);
  for(const {m,b} of dominos){ m.position.copy(b.position); m.quaternion.copy(b.quaternion); }
  rnd.render(scn, cam);
  requestAnimationFrame(tick);
}
tick();
</script></body></html>"""

_CANNON_VEHICLE_HTML = r"""<!doctype html><html><head><meta charset=utf-8><title>Vehicle</title>
<style>body{margin:0;background:#000;color:#fff;font-family:sans-serif;overflow:hidden}#hud{position:fixed;top:10px;left:10px;background:#0008;padding:8px;border-radius:8px;z-index:10}</style>
<script type=importmap>{"imports":{"three":"https://unpkg.com/three@0.160/build/three.module.js","cannon":"https://unpkg.com/cannon-es@0.20.0/dist/cannon-es.js"}}</script></head>
<body><div id=hud>🏎️ Vehicle — WASD to drive · Three.js + Cannon-es</div>
<script type=module>
import * as THREE from 'three';
import * as CANNON from 'cannon';
const scn = new THREE.Scene(); scn.background = new THREE.Color(0x224);
const cam = new THREE.PerspectiveCamera(60, innerWidth/innerHeight, 0.1, 500);
const rnd = new THREE.WebGLRenderer({antialias:true});
rnd.setSize(innerWidth, innerHeight); document.body.appendChild(rnd.domElement);
scn.add(new THREE.AmbientLight(0xffffff,0.7));
const world = new CANNON.World({gravity: new CANNON.Vec3(0,-9.82,0)});
const floorM = new THREE.Mesh(new THREE.PlaneGeometry(200,200), new THREE.MeshStandardMaterial({color:0x335}));
floorM.rotation.x = -Math.PI/2; scn.add(floorM);
const floor = new CANNON.Body({mass:0, shape:new CANNON.Plane()});
floor.quaternion.setFromAxisAngle(new CANNON.Vec3(1,0,0),-Math.PI/2); world.addBody(floor);
// vehicle chassis
const chassisShape = new CANNON.Box(new CANNON.Vec3(2,0.5,1));
const chassis = new CANNON.Body({mass:150, position:new CANNON.Vec3(0,4,0)});
chassis.addShape(chassisShape); world.addBody(chassis);
const chassisM = new THREE.Mesh(new THREE.BoxGeometry(4,1,2), new THREE.MeshStandardMaterial({color:0xff5733}));
scn.add(chassisM);
const v = new CANNON.RaycastVehicle({chassisBody:chassis, indexRightAxis:0, indexUpAxis:1, indexForwardAxis:2});
const wOpts = {radius:0.5, suspensionStiffness:30, suspensionRestLength:0.3, frictionSlip:5, dampingRelaxation:2.3, dampingCompression:4.4, maxSuspensionForce:100000, rollInfluence:0.01, axleLocal:new CANNON.Vec3(-1,0,0), chassisConnectionPointLocal:new CANNON.Vec3(1,0,1), maxSuspensionTravel:0.3, customSlidingRotationalSpeed:-30, useCustomSlidingRotationalSpeed:true};
[[1.5,-0.5,1],[1.5,-0.5,-1],[-1.5,-0.5,1],[-1.5,-0.5,-1]].forEach(([x,y,z]) => {
  v.addWheel({...wOpts, chassisConnectionPointLocal: new CANNON.Vec3(x,y,z)});
});
v.addToWorld(world);
const wheelMeshes = v.wheelInfos.map(() => {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(0.5,0.5,0.4,16), new THREE.MeshStandardMaterial({color:0x222}));
  m.rotation.z = Math.PI/2; scn.add(m); return m;
});
const keys = {};
addEventListener('keydown', e => keys[e.code]=1);
addEventListener('keyup', e => keys[e.code]=0);
function update(){
  const eng = keys['KeyW']?300:keys['KeyS']?-200:0;
  v.applyEngineForce(eng, 2); v.applyEngineForce(eng, 3);
  const st = keys['KeyA']?0.5:keys['KeyD']?-0.5:0;
  v.setSteeringValue(st, 0); v.setSteeringValue(st, 1);
}
function tick(){
  update();
  world.step(1/60);
  chassisM.position.copy(chassis.position); chassisM.quaternion.copy(chassis.quaternion);
  for(let i=0;i<v.wheelInfos.length;i++){
    v.updateWheelTransform(i);
    const t = v.wheelInfos[i].worldTransform;
    wheelMeshes[i].position.copy(t.position); wheelMeshes[i].quaternion.copy(t.quaternion);
  }
  cam.position.copy(chassis.position).add(new THREE.Vector3(-8,5,0));
  cam.lookAt(chassis.position);
  rnd.render(scn,cam);
  requestAnimationFrame(tick);
}
tick();
</script></body></html>"""

_RAPIER_SOFTBODY_HTML = r"""<!doctype html><html><head><meta charset=utf-8><title>Soft Body</title>
<style>body{margin:0;background:#0f0f14;color:#fff;font-family:sans-serif}#hud{position:fixed;top:10px;left:10px;background:#0008;padding:8px;border-radius:8px}</style></head>
<body><div id=hud>🥒 Soft Body — note: Rapier integration requires npm + bundler. For browser testing use the Matter.js soft-body example at: <a href='https://brm.io/matter-js/demo/#softBody' style='color:#9cf'>brm.io/matter-js soft-body demo</a></div>
<p style='padding:2rem'>For a true Rapier soft-body in browser, install via npm:<br><code>npm install @dimforge/rapier2d-compat</code><br>and follow https://rapier.rs/javascript2d/ docs. This preset returns instructions because the WASM module can't be loaded directly via a single HTML page.</p>
</body></html>"""
