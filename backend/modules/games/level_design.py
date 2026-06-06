"""
🗺️ Level Design Generator
═══════════════════════════════════════════════════════════════════════
Uses Claude to design playable levels as a structured tilemap JSON.
Output is consumed by:
  • The HTML5 builder (renders a tile-grid on canvas)
  • The Unity SDK (imports as a ScriptableObject)
  • The frontend's Live View tab (shows a 2D preview)

Endpoint: POST /api/games/project/{id}/generate-level
Body: { "description": "forest village with shops and a dungeon entrance",
         "size": 24, "style": "top-down" | "side-scroller" | "isometric" }
"""
from __future__ import annotations
import os, json, logging, uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Universal tile vocabulary so different style profiles still produce
# consistent JSON the engine can interpret.
TILE_LEGEND = {
    "FLOOR":   "0",
    "WALL":    "1",
    "DOOR":    "2",
    "WATER":   "3",
    "GRASS":   "4",
    "TREE":    "5",
    "ROCK":    "6",
    "SAND":    "7",
    "LAVA":    "8",
    "CHEST":   "9",
    "SPAWN":   "S",
    "EXIT":    "E",
    "ENEMY":   "X",
    "NPC":     "N",
    "SHOP":    "$",
    "BOSS":    "B",
    "EMPTY":   ".",
}

SYSTEM_PROMPT = """You are a senior game level designer. Output ONLY valid JSON, no prose.
Return a tilemap as:
{
  "name": "...",
  "size": { "w": INT, "h": INT },
  "legend": { "0":"floor","1":"wall","S":"spawn","E":"exit","X":"enemy","N":"npc","$":"shop","B":"boss","9":"chest","2":"door","3":"water","4":"grass","5":"tree","6":"rock","7":"sand","8":"lava",".":"empty" },
  "grid": ["...row1...", "...row2..."],
  "spawns": [{"id":"player1","x":INT,"y":INT}],
  "objectives": ["Reach the exit","Defeat the boss"],
  "lore": "1-3 sentence flavour text"
}

Rules:
- grid uses single-character codes from the legend.
- size.w must equal len(grid[0]); size.h must equal len(grid).
- Always place ONE "S" (player spawn) and at least one "E" (exit).
- Keep walls connected around the borders to prevent escape.
- For top-down levels, design rooms connected by corridors.
- For side-scroller, place "1" floor tiles at the bottom 2-3 rows and platforms above.
- For isometric, follow top-down layout.
"""


async def generate_level(
    description: str,
    size: int = 20,
    style: str = "top-down",
) -> Dict[str, Any]:
    """Call Claude (via Emergent) to design a level, return parsed JSON.
    Raises RuntimeError if Claude returns invalid JSON after 1 retry.
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    sess = str(uuid.uuid4())[:8]
    chat = LlmChat(
        api_key=os.environ.get("EMERGENT_LLM_KEY", ""),
        session_id=f"level-{sess}",
        system_message=SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-20250514").with_max_tokens(3500)

    user_prompt = (
        f"Design a {size}x{size} {style} level. Theme: {description}. "
        f"Make it interesting with branching paths and at least 2 spawns. "
        f"Return ONLY the JSON object, no markdown code fences."
    )

    raw = await chat.send_message(UserMessage(text=user_prompt))
    raw = (raw or "").strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1] if "```" in raw[3:] else raw[3:]
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        data = json.loads(raw)
    except Exception as e:
        logger.warning(f"[level] first parse failed: {e}; retrying with stricter prompt")
        # Retry once with even stricter instruction
        retry = await chat.send_message(UserMessage(
            text="Your last response was not valid JSON. Reply with ONLY the JSON object, nothing else. No markdown, no prose."
        ))
        retry = (retry or "").strip()
        if retry.startswith("```"):
            retry = retry.split("```", 2)[1] if "```" in retry[3:] else retry[3:]
            if retry.lower().startswith("json"):
                retry = retry[4:]
            retry = retry.rsplit("```", 1)[0].strip()
        try:
            data = json.loads(retry)
        except Exception as e2:
            raise RuntimeError(f"Level JSON invalid after retry: {e2}")

    # Inject metadata
    data["id"] = str(uuid.uuid4())
    data["style"] = style
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    data["tile_legend"] = TILE_LEGEND  # canonical mapping for clients
    return data
