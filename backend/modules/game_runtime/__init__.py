"""
🎮 Zitex Game Runtime — Backend-as-a-Service for AI-generated games
─────────────────────────────────────────────────────────────────────
Provides EVERY backend primitive a Zitex-generated game needs, so games
deployed via the existing static-site live preview can still have:
  • Player auth (per-project namespace, JWT)
  • Save/load player progress (cross-device)
  • Leaderboards (MongoDB sorted set)
  • Real-time multiplayer rooms (WebSocket)
  • In-game chat
  • Achievements
  • Server-validated game economy

Each endpoint is sandboxed by `project_id` so games can't read each other's data.
A lightweight JS SDK is exposed at `/api/game-runtime/{project_id}/sdk.js`
that the AI can drop into any generated HTML game with one <script> tag.
"""
from __future__ import annotations
import os
import json
import jwt
import time
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header
from fastapi.responses import Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# JWT secret for player tokens (scoped per project)
PLAYER_JWT_SECRET = os.environ.get("PLAYER_JWT_SECRET") or os.environ.get("JWT_SECRET") or "zitex-player-fallback"
PLAYER_TOKEN_TTL_HOURS = 24 * 14  # 2 weeks


# ═══════════════════════════════════════════════════════════════
# Models
# ═══════════════════════════════════════════════════════════════
class PlayerSignup(BaseModel):
    username: str = Field(min_length=2, max_length=24)
    password: Optional[str] = None  # optional; guest = anonymous
    display_name: Optional[str] = None


class PlayerLogin(BaseModel):
    username: str
    password: Optional[str] = None


class SaveSlot(BaseModel):
    slot: str = "default"
    payload: Dict[str, Any] = Field(default_factory=dict)


class LeaderboardEntry(BaseModel):
    leaderboard: str = "default"
    score: float
    metadata: Optional[Dict[str, Any]] = None


class AchievementUnlock(BaseModel):
    achievement_id: str
    metadata: Optional[Dict[str, Any]] = None


class ChatMessage(BaseModel):
    room: str = "lobby"
    text: str


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════
def _player_token(project_id: str, player_id: str, username: str) -> str:
    return jwt.encode(
        {
            "pid": project_id,
            "uid": player_id,
            "u": username,
            "exp": int((datetime.utcnow() + timedelta(hours=PLAYER_TOKEN_TTL_HOURS)).timestamp()),
        },
        PLAYER_JWT_SECRET,
        algorithm="HS256",
    )


def _verify_player_token(token: str, expected_project: str) -> Dict[str, Any]:
    try:
        data = jwt.decode(token, PLAYER_JWT_SECRET, algorithms=["HS256"])
    except Exception as e:
        raise HTTPException(401, f"invalid token: {e}")
    if data.get("pid") != expected_project:
        raise HTTPException(403, "token does not belong to this project")
    return data


async def _player_dep(project_id: str, authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    return _verify_player_token(authorization.split(" ", 1)[1].strip(), project_id)


def _hash_password(plain: str) -> str:
    import hashlib, secrets as _s
    salt = _s.token_hex(8)
    h = hashlib.sha256(f"{salt}:{plain}".encode()).hexdigest()
    return f"{salt}${h}"


def _verify_password(plain: str, stored: str) -> bool:
    if not stored or "$" not in stored:
        return False
    import hashlib
    salt, h = stored.split("$", 1)
    return hashlib.sha256(f"{salt}:{plain}".encode()).hexdigest() == h


# ═══════════════════════════════════════════════════════════════
# Router factory
# ═══════════════════════════════════════════════════════════════
def create_router(db):
    router = APIRouter(prefix="/api/game-runtime", tags=["game-runtime"])

    # ────────────────────────────────────────────────────────────
    # 1️⃣ PLAYER AUTH (per-project namespace)
    # ────────────────────────────────────────────────────────────
    @router.post("/{project_id}/signup")
    async def signup(project_id: str, payload: PlayerSignup):
        """Register a new player for this game project."""
        # Ensure project exists
        proj = await db.game_projects.find_one({"id": project_id}, {"id": 1})
        if not proj:
            raise HTTPException(404, "game project not found")
        existing = await db.game_players.find_one(
            {"project_id": project_id, "username": payload.username.lower()}
        )
        if existing:
            raise HTTPException(409, "username taken")
        player_id = str(uuid.uuid4())
        await db.game_players.insert_one({
            "_id": player_id,
            "project_id": project_id,
            "username": payload.username.lower(),
            "display_name": payload.display_name or payload.username,
            "password_hash": _hash_password(payload.password) if payload.password else None,
            "is_guest": payload.password is None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "stats": {},
        })
        return {
            "ok": True,
            "player_id": player_id,
            "username": payload.username.lower(),
            "display_name": payload.display_name or payload.username,
            "token": _player_token(project_id, player_id, payload.username),
            "is_guest": payload.password is None,
        }

    @router.post("/{project_id}/login")
    async def login(project_id: str, payload: PlayerLogin):
        """Login existing player. Empty password = guest reconnect (only if was guest)."""
        player = await db.game_players.find_one(
            {"project_id": project_id, "username": payload.username.lower()}
        )
        if not player:
            raise HTTPException(404, "player not found")
        if not player.get("is_guest"):
            if not payload.password or not _verify_password(payload.password, player.get("password_hash", "")):
                raise HTTPException(401, "invalid credentials")
        await db.game_players.update_one(
            {"_id": player["_id"]},
            {"$set": {"last_seen_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {
            "ok": True,
            "player_id": player["_id"],
            "username": player["username"],
            "display_name": player.get("display_name", player["username"]),
            "token": _player_token(project_id, player["_id"], player["username"]),
            "is_guest": player.get("is_guest", False),
        }

    @router.post("/{project_id}/guest")
    async def guest(project_id: str):
        """One-click guest play — no signup needed."""
        username = f"guest_{uuid.uuid4().hex[:6]}"
        return await signup(project_id, PlayerSignup(username=username, display_name=f"Guest-{username[-4:]}"))

    @router.get("/{project_id}/me")
    async def me(project_id: str, player=Depends(_player_dep)):
        p = await db.game_players.find_one({"_id": player["uid"]}, {"password_hash": 0})
        if not p:
            raise HTTPException(404, "player not found")
        p["id"] = p.pop("_id")
        return {"ok": True, "player": p}

    # ────────────────────────────────────────────────────────────
    # 2️⃣ SAVE/LOAD player progress (multiple slots per player)
    # ────────────────────────────────────────────────────────────
    @router.post("/{project_id}/save")
    async def save(project_id: str, payload: SaveSlot, player=Depends(_player_dep)):
        """Cross-device save. JSON payload up to ~1MB."""
        if len(json.dumps(payload.payload)) > 1_048_576:
            raise HTTPException(413, "payload exceeds 1MB")
        await db.game_saves.update_one(
            {"project_id": project_id, "player_id": player["uid"], "slot": payload.slot},
            {"$set": {
                "project_id": project_id,
                "player_id": player["uid"],
                "username": player["u"],
                "slot": payload.slot,
                "payload": payload.payload,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
        return {"ok": True, "slot": payload.slot, "saved_at": datetime.now(timezone.utc).isoformat()}

    @router.get("/{project_id}/load")
    async def load(project_id: str, slot: str = "default", player=Depends(_player_dep)):
        s = await db.game_saves.find_one(
            {"project_id": project_id, "player_id": player["uid"], "slot": slot}
        )
        if not s:
            return {"ok": True, "exists": False, "payload": None}
        return {"ok": True, "exists": True, "payload": s["payload"], "updated_at": s["updated_at"]}

    @router.get("/{project_id}/saves")
    async def list_saves(project_id: str, player=Depends(_player_dep)):
        rows = await db.game_saves.find(
            {"project_id": project_id, "player_id": player["uid"]},
            {"payload": 0},
        ).to_list(length=50)
        for r in rows:
            r.pop("_id", None)
        return {"ok": True, "saves": rows}

    @router.delete("/{project_id}/save")
    async def delete_save(project_id: str, slot: str = "default", player=Depends(_player_dep)):
        await db.game_saves.delete_one(
            {"project_id": project_id, "player_id": player["uid"], "slot": slot}
        )
        return {"ok": True}

    # ────────────────────────────────────────────────────────────
    # 3️⃣ LEADERBOARDS (per-project, multiple boards)
    # ────────────────────────────────────────────────────────────
    @router.post("/{project_id}/leaderboard/submit")
    async def submit_score(project_id: str, entry: LeaderboardEntry, player=Depends(_player_dep)):
        # Only keep the BEST score for this player+board (overwrite if higher)
        existing = await db.game_leaderboards.find_one({
            "project_id": project_id,
            "leaderboard": entry.leaderboard,
            "player_id": player["uid"],
        })
        if existing and float(existing.get("score", 0)) >= float(entry.score):
            return {"ok": True, "improved": False, "current": existing["score"]}
        await db.game_leaderboards.update_one(
            {"project_id": project_id, "leaderboard": entry.leaderboard, "player_id": player["uid"]},
            {"$set": {
                "project_id": project_id,
                "leaderboard": entry.leaderboard,
                "player_id": player["uid"],
                "username": player["u"],
                "score": float(entry.score),
                "metadata": entry.metadata or {},
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
        return {"ok": True, "improved": True}

    @router.get("/{project_id}/leaderboard")
    async def get_leaderboard(project_id: str, name: str = "default", limit: int = 50):
        limit = max(1, min(limit, 200))
        rows = await db.game_leaderboards.find(
            {"project_id": project_id, "leaderboard": name},
            {"_id": 0},
        ).sort("score", -1).limit(limit).to_list(length=limit)
        return {"ok": True, "leaderboard": name, "count": len(rows), "rows": rows}

    @router.get("/{project_id}/leaderboard/me")
    async def my_rank(project_id: str, name: str = "default", player=Depends(_player_dep)):
        mine = await db.game_leaderboards.find_one({
            "project_id": project_id, "leaderboard": name, "player_id": player["uid"],
        }, {"_id": 0})
        if not mine:
            return {"ok": True, "found": False, "rank": None, "score": 0}
        rank = await db.game_leaderboards.count_documents({
            "project_id": project_id,
            "leaderboard": name,
            "score": {"$gt": mine["score"]},
        })
        return {"ok": True, "found": True, "rank": rank + 1, "score": mine["score"]}

    # ────────────────────────────────────────────────────────────
    # 4️⃣ ACHIEVEMENTS
    # ────────────────────────────────────────────────────────────
    @router.post("/{project_id}/achievements/unlock")
    async def unlock_achievement(project_id: str, payload: AchievementUnlock, player=Depends(_player_dep)):
        existed = await db.game_achievements.find_one({
            "project_id": project_id,
            "player_id": player["uid"],
            "achievement_id": payload.achievement_id,
        })
        if existed:
            return {"ok": True, "already_unlocked": True}
        await db.game_achievements.insert_one({
            "project_id": project_id,
            "player_id": player["uid"],
            "username": player["u"],
            "achievement_id": payload.achievement_id,
            "metadata": payload.metadata or {},
            "unlocked_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"ok": True, "already_unlocked": False, "achievement_id": payload.achievement_id}

    @router.get("/{project_id}/achievements")
    async def list_achievements(project_id: str, player=Depends(_player_dep)):
        rows = await db.game_achievements.find(
            {"project_id": project_id, "player_id": player["uid"]},
            {"_id": 0},
        ).to_list(length=500)
        return {"ok": True, "achievements": rows, "count": len(rows)}

    # ────────────────────────────────────────────────────────────
    # 5️⃣ REAL-TIME ROOMS (WebSocket + REST control)
    # ────────────────────────────────────────────────────────────
    # In-memory room registry. For production scale, replace with Redis Pub/Sub.
    _rooms: Dict[str, Dict[str, Any]] = {}  # room_key -> {clients: set[WebSocket], state: {...}}

    def _room_key(project_id: str, room: str) -> str:
        return f"{project_id}::{room}"

    async def _broadcast(room_key: str, message: Dict[str, Any]):
        room = _rooms.get(room_key)
        if not room:
            return
        dead = []
        for ws in list(room["clients"]):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            room["clients"].discard(ws)

    @router.websocket("/{project_id}/ws")
    async def realtime_ws(websocket: WebSocket, project_id: str, room: str = "lobby", token: str = ""):
        """Real-time multiplayer WebSocket. Player connects with their JWT in `?token=`.
        Receives JSON messages of shape: {type: 'chat'|'state'|'event', ...}.
        Broadcasts to all players in the same (project, room)."""
        try:
            player = _verify_player_token(token, project_id)
        except HTTPException as e:
            await websocket.close(code=4401)
            return
        await websocket.accept()
        key = _room_key(project_id, room)
        if key not in _rooms:
            _rooms[key] = {"clients": set(), "state": {}, "created_at": time.time()}
        _rooms[key]["clients"].add(websocket)

        # Announce join
        await _broadcast(key, {
            "type": "player_joined",
            "player_id": player["uid"],
            "username": player["u"],
            "count": len(_rooms[key]["clients"]),
        })
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                msg["_from"] = {"player_id": player["uid"], "username": player["u"]}
                msg["_ts"] = time.time()
                # Server-side state merge for "state" messages
                if msg.get("type") == "state" and isinstance(msg.get("patch"), dict):
                    _rooms[key]["state"].update(msg["patch"])
                # Persist chat messages briefly (last 50 in memory)
                if msg.get("type") == "chat":
                    chats = _rooms[key].setdefault("chats", [])
                    chats.append({
                        "username": player["u"],
                        "text": str(msg.get("text", ""))[:500],
                        "ts": msg["_ts"],
                    })
                    if len(chats) > 50:
                        chats[:] = chats[-50:]
                await _broadcast(key, msg)
        except WebSocketDisconnect:
            pass
        finally:
            _rooms[key]["clients"].discard(websocket)
            await _broadcast(key, {
                "type": "player_left",
                "player_id": player["uid"],
                "username": player["u"],
                "count": len(_rooms[key]["clients"]),
            })
            # Clean up empty rooms after some idle time
            if not _rooms[key]["clients"]:
                _rooms.pop(key, None)

    @router.get("/{project_id}/rooms")
    async def list_rooms(project_id: str):
        out = []
        for key, info in _rooms.items():
            pid, room = key.split("::", 1)
            if pid == project_id:
                out.append({
                    "room": room,
                    "players": len(info["clients"]),
                    "created_at": info["created_at"],
                })
        return {"ok": True, "rooms": out}

    @router.get("/{project_id}/room/{room}/state")
    async def room_state(project_id: str, room: str):
        key = _room_key(project_id, room)
        r = _rooms.get(key)
        if not r:
            return {"ok": True, "exists": False, "state": {}, "players": 0}
        return {
            "ok": True,
            "exists": True,
            "state": r["state"],
            "players": len(r["clients"]),
            "recent_chat": r.get("chats", [])[-20:],
        }

    # ────────────────────────────────────────────────────────────
    # 6️⃣ SDK GENERATOR — drop-in <script> for any HTML game
    # ────────────────────────────────────────────────────────────
    @router.get("/{project_id}/sdk.js")
    async def sdk_js(project_id: str):
        """Returns a JS SDK the AI-generated game can `<script src>` to use
        ALL of the above (auth, save, leaderboard, ws) with one line."""
        backend = os.environ.get("PUBLIC_BACKEND_URL") or os.environ.get("REACT_APP_BACKEND_URL") or ""
        js = _SDK_TEMPLATE.replace("__PROJECT_ID__", project_id).replace("__BACKEND_URL__", backend)
        return Response(content=js, media_type="application/javascript")

    # ────────────────────────────────────────────────────────────
    # 7️⃣ Genre Templates (P1 — task 12)
    # ────────────────────────────────────────────────────────────
    @router.get("/templates/genres")
    async def list_genre_templates():
        return {"ok": True, "templates": GENRE_TEMPLATES}

    @router.get("/templates/genres/{genre_id}")
    async def get_genre_template(genre_id: str):
        t = next((g for g in GENRE_TEMPLATES if g["id"] == genre_id), None)
        if not t:
            raise HTTPException(404, "genre template not found")
        return {"ok": True, "template": t}

    # ────────────────────────────────────────────────────────────
    # 8️⃣ Cost tracking per project (P2 — task 20)
    # ────────────────────────────────────────────────────────────
    @router.get("/{project_id}/cost-summary")
    async def cost_summary(project_id: str):
        """Total credits spent on this game project (aggregated from credit_transactions)."""
        try:
            cursor = db.credit_transactions.find({"project_id": project_id}, {"_id": 0})
            txs = await cursor.to_list(length=2000)
            total = sum(abs(t.get("amount", 0)) for t in txs if t.get("type") in ("spend", "debit"))
            by_kind: Dict[str, float] = {}
            for t in txs:
                if t.get("type") in ("spend", "debit"):
                    k = t.get("reason") or t.get("kind") or "other"
                    by_kind[k] = by_kind.get(k, 0) + abs(t.get("amount", 0))
            return {"ok": True, "total_credits_spent": total, "by_category": by_kind, "transactions_count": len(txs)}
        except Exception as e:
            return {"ok": True, "total_credits_spent": 0, "by_category": {}, "note": f"no transactions yet ({e})"}

    return router


# ═══════════════════════════════════════════════════════════════
# 🎨 GENRE TEMPLATES — for AI workflow guidance (task 12)
# ═══════════════════════════════════════════════════════════════
GENRE_TEMPLATES = [
    {
        "id": "mmo_strategy",
        "name": "⚔️ MMO Strategy (Travian-like)",
        "engine": "html5_canvas",
        "estimated_credits": 5000,
        "stages": [
            {"id": "world", "title": "World Map & Resources", "assets": ["wheat_field", "iron_mine", "wood_forest", "clay_pit"]},
            {"id": "buildings", "title": "Buildings", "assets": ["forum", "barracks", "house", "wall", "marketplace"]},
            {"id": "units", "title": "Military Units", "assets": ["soldier", "knight", "archer", "siege_engine"]},
            {"id": "ui", "title": "UI Panels", "assets": ["resource_bar", "inventory", "build_menu", "battle_report"]},
            {"id": "economy", "title": "Economy Loop", "code": "production_rates + upgrade_costs"},
            {"id": "combat", "title": "Combat System", "code": "turn_based_resolution"},
            {"id": "multiplayer", "title": "Multiplayer (use Zitex Runtime)", "code": "room_state + leaderboard"},
        ],
        "engines": ["zitex_runtime_save", "zitex_runtime_leaderboard", "zitex_runtime_multiplayer"],
    },
    {
        "id": "platformer",
        "name": "🦘 Platformer (Super Mario-like)",
        "engine": "phaser",
        "estimated_credits": 2500,
        "stages": [
            {"id": "character", "title": "Hero Sprite Sheet", "assets": ["idle", "run", "jump", "fall", "hit"]},
            {"id": "tilemaps", "title": "Tilemaps (3 worlds)", "assets": ["world1_tiles", "world2_tiles", "world3_tiles"]},
            {"id": "enemies", "title": "Enemies", "assets": ["goomba_walker", "flying_eye", "boss"]},
            {"id": "collectibles", "title": "Coins & Power-ups", "assets": ["coin", "mushroom", "star"]},
            {"id": "mechanics", "title": "Physics & Movement", "code": "Phaser Arcade Physics + jump curve"},
            {"id": "levels", "title": "Level Design (10 stages)", "code": "JSON tilemap loader"},
            {"id": "save", "title": "Save Progress (Zitex Runtime)", "code": "best_level + collectibles_count"},
        ],
        "engines": ["zitex_runtime_save", "zitex_runtime_achievements"],
    },
    {
        "id": "puzzle_match3",
        "name": "🍬 Puzzle Match-3 (Candy Crush-like)",
        "engine": "phaser",
        "estimated_credits": 1800,
        "stages": [
            {"id": "tokens", "title": "Token Designs (6 colors)", "assets": ["red_gem", "blue_gem", "green_gem", "yellow_gem", "purple_gem", "rainbow_special"]},
            {"id": "board", "title": "Board UI", "assets": ["bg_grid", "score_panel", "moves_panel"]},
            {"id": "matching", "title": "Match Detection", "code": "horizontal/vertical 3+/4+/5+"},
            {"id": "cascades", "title": "Cascade & Refill", "code": "gravity + spawn_top_row"},
            {"id": "powerups", "title": "Power-ups", "code": "row_clear + bomb + color_clear"},
            {"id": "levels", "title": "Level Goals (50 levels)", "code": "objective JSON file"},
            {"id": "leaderboard", "title": "Global Best Scores (Zitex Runtime)", "code": "submit_score per level"},
        ],
        "engines": ["zitex_runtime_leaderboard", "zitex_runtime_save"],
    },
    {
        "id": "idle_clicker",
        "name": "🖱️ Idle/Clicker (Cookie Clicker-like)",
        "engine": "html5_canvas",
        "estimated_credits": 1200,
        "stages": [
            {"id": "main", "title": "Main Clicker Object", "assets": ["cookie_or_thing", "click_burst_fx"]},
            {"id": "buildings", "title": "Auto-producers", "assets": ["grandma", "farm", "factory", "bank", "temple"]},
            {"id": "upgrades", "title": "Upgrades", "assets": ["upgrade_icons"]},
            {"id": "economy", "title": "Production Math", "code": "exponential_growth_curve"},
            {"id": "prestige", "title": "Prestige/Reset System", "code": "soul_currency_loop"},
            {"id": "save", "title": "Auto-save (Zitex Runtime)", "code": "save every 30s"},
            {"id": "achievements", "title": "Achievements (50 unlocks)", "code": "unlock thresholds"},
        ],
        "engines": ["zitex_runtime_save", "zitex_runtime_achievements"],
    },
    {
        "id": "turn_based_rpg",
        "name": "🗡️ Turn-Based RPG (Final Fantasy Tactics-like)",
        "engine": "phaser",
        "estimated_credits": 4000,
        "stages": [
            {"id": "heroes", "title": "Hero Party (4 chars)", "assets": ["knight_portrait", "mage_portrait", "rogue_portrait", "cleric_portrait"]},
            {"id": "enemies", "title": "Enemy Types (12)", "assets": ["goblin", "skeleton", "dragon", "lich"]},
            {"id": "battle_grid", "title": "Battle Grid UI", "assets": ["grid_tile", "highlight_movement", "highlight_attack"]},
            {"id": "items", "title": "Items & Inventory", "assets": ["sword_icon", "potion_icon", "armor_icon"]},
            {"id": "story", "title": "Story Beats (10 chapters)", "code": "dialogue_tree.json"},
            {"id": "combat_math", "title": "Combat Formulas", "code": "atk - def + crit + status"},
            {"id": "save", "title": "Save Anywhere (Zitex Runtime)", "code": "save full party state"},
        ],
        "engines": ["zitex_runtime_save", "zitex_runtime_achievements"],
    },
    {
        "id": "action_fps",
        "name": "🎯 Action FPS (Three.js-based)",
        "engine": "threejs",
        "estimated_credits": 6000,
        "stages": [
            {"id": "arena", "title": "Arena Map (3D)", "assets": ["arena_skybox", "ground_textures", "obstacle_props_x10"]},
            {"id": "weapons", "title": "Weapon Models", "assets": ["pistol_3d", "rifle_3d", "shotgun_3d"]},
            {"id": "enemies", "title": "Enemy NPCs", "assets": ["enemy_grunt_3d", "boss_3d"]},
            {"id": "movement", "title": "WASD + Mouse Look", "code": "PointerLockControls + collision"},
            {"id": "shooting", "title": "Hit Detection", "code": "raycaster + damage falloff"},
            {"id": "rooms", "title": "PvP Rooms (Zitex Runtime)", "code": "WebSocket realtime"},
            {"id": "leaderboard", "title": "K/D Leaderboard (Zitex Runtime)", "code": "submit kills/deaths"},
        ],
        "engines": ["zitex_runtime_multiplayer", "zitex_runtime_leaderboard"],
    },
]


# ═══════════════════════════════════════════════════════════════
# 🧰 JS SDK TEMPLATE — what every Zitex-generated game embeds
# ═══════════════════════════════════════════════════════════════
_SDK_TEMPLATE = r"""/* Zitex Game Runtime SDK
 * ─────────────────────────────────────────────
 * One-line backend for AI-generated games:
 *   <script src="__BACKEND_URL__/api/game-runtime/__PROJECT_ID__/sdk.js"></script>
 *   <script>
 *     await ZitexGame.guest();   // anonymous instant play
 *     await ZitexGame.save({level:5, gold:1200});
 *     const top = await ZitexGame.leaderboard.top();
 *     ZitexGame.unlock('first_blood');
 *     const room = ZitexGame.join('arena-1');
 *     room.onMessage(m => console.log(m));
 *     room.send({type:'shoot', x:120, y:80});
 *   </script>
 */
(function(global){
  const BACKEND = "__BACKEND_URL__";
  const PID = "__PROJECT_ID__";
  const BASE = BACKEND + "/api/game-runtime/" + PID;
  const LSKEY = "zitex_token_" + PID;

  function _hdr(){
    const t = localStorage.getItem(LSKEY);
    return t ? { "Authorization": "Bearer " + t } : {};
  }
  async function _post(path, body){
    const r = await fetch(BASE + path, {
      method: "POST",
      headers: { "Content-Type": "application/json", ..._hdr() },
      body: body ? JSON.stringify(body) : null,
    });
    if(!r.ok) throw new Error((await r.text()).slice(0,200));
    return r.json();
  }
  async function _get(path){
    const r = await fetch(BASE + path, { headers: _hdr() });
    if(!r.ok) throw new Error((await r.text()).slice(0,200));
    return r.json();
  }

  const ZitexGame = {
    backend: BACKEND, projectId: PID,
    player: null,

    // ── Auth
    async signup(username, password, displayName){
      const r = await _post("/signup", { username, password, display_name: displayName });
      localStorage.setItem(LSKEY, r.token);
      this.player = { id: r.player_id, username: r.username, displayName: r.display_name, isGuest: r.is_guest };
      return this.player;
    },
    async login(username, password){
      const r = await _post("/login", { username, password });
      localStorage.setItem(LSKEY, r.token);
      this.player = { id: r.player_id, username: r.username, displayName: r.display_name, isGuest: r.is_guest };
      return this.player;
    },
    async guest(){
      const r = await _post("/guest");
      localStorage.setItem(LSKEY, r.token);
      this.player = { id: r.player_id, username: r.username, displayName: r.display_name, isGuest: true };
      return this.player;
    },
    async me(){ const r = await _get("/me"); this.player = r.player; return r.player; },
    logout(){ localStorage.removeItem(LSKEY); this.player = null; },

    // ── Save/Load
    async save(payload, slot){ return _post("/save", { slot: slot || "default", payload }); },
    async load(slot){ const r = await _get("/load?slot=" + encodeURIComponent(slot || "default")); return r.payload; },
    async listSaves(){ return (await _get("/saves")).saves; },
    async deleteSave(slot){ return fetch(BASE + "/save?slot=" + encodeURIComponent(slot || "default"), { method: "DELETE", headers: _hdr() }); },

    // ── Leaderboard
    leaderboard: {
      async submit(score, board, metadata){ return _post("/leaderboard/submit", { leaderboard: board || "default", score, metadata }); },
      async top(board, limit){ const r = await _get("/leaderboard?name=" + encodeURIComponent(board || "default") + "&limit=" + (limit||50)); return r.rows; },
      async myRank(board){ return _get("/leaderboard/me?name=" + encodeURIComponent(board || "default")); }
    },

    // ── Achievements
    async unlock(achievementId, metadata){ return _post("/achievements/unlock", { achievement_id: achievementId, metadata }); },
    async achievements(){ return (await _get("/achievements")).achievements; },

    // ── Multiplayer rooms (WebSocket)
    join(room){
      const token = localStorage.getItem(LSKEY);
      if(!token) throw new Error("login or guest() first");
      const wsUrl = BACKEND.replace(/^http/, "ws") + "/api/game-runtime/" + PID + "/ws?room=" + encodeURIComponent(room||"lobby") + "&token=" + encodeURIComponent(token);
      const ws = new WebSocket(wsUrl);
      const handlers = { message: [], open: [], close: [] };
      ws.onmessage = e => { try{ const d = JSON.parse(e.data); handlers.message.forEach(fn => fn(d)); }catch(_){} };
      ws.onopen = () => handlers.open.forEach(fn => fn());
      ws.onclose = () => handlers.close.forEach(fn => fn());
      return {
        send(obj){ if(ws.readyState===1) ws.send(JSON.stringify(obj)); },
        onMessage(fn){ handlers.message.push(fn); },
        onOpen(fn){ handlers.open.push(fn); },
        onClose(fn){ handlers.close.push(fn); },
        close(){ ws.close(); },
        ws,
      };
    },
    async rooms(){ return (await _get("/rooms")).rooms; },
  };

  global.ZitexGame = ZitexGame;
})(typeof window !== "undefined" ? window : globalThis);
"""
