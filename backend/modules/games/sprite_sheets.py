"""
🎞️ Sprite-Sheet & Animation Extras
═══════════════════════════════════════════════════════════════════════
Beyond the existing `<<ANIMATE>>` (image-to-video via Kling), this
module produces **sprite sheets** — a grid of 8 character frames in
the same pose family (idle, walk, attack) suitable for engines like
Unity, Godot, Phaser.

Approach: generate 8 paralleled Flux Pro Ultra renders with the same
character prompt + a per-frame action delta, then composite them
into a single PNG sheet.

Endpoint: POST /api/games/project/{id}/sprite-sheet
Body: { "character": "old wizard with blue robe",
         "action": "walk" | "idle" | "attack" | "death",
         "frames": 8 }
"""
from __future__ import annotations
import os, io, uuid, asyncio, logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Per-action frame deltas — the AI sees these as scene directions
ACTION_DELTAS = {
    "idle":   [
        "neutral pose, slight breathing motion", "very small shift right",
        "slight shoulder rise", "slight head tilt left", "neutral pose",
        "slight shoulder drop", "small shift left", "neutral resting",
    ],
    "walk":   [
        "left foot forward, right arm forward", "weight on left foot, body slightly lifted",
        "passing pose, both feet aligned", "right foot forward, left arm forward",
        "weight on right foot, body slightly lifted", "passing pose, both feet aligned",
        "left foot starting forward again", "neutral standing pose",
    ],
    "attack": [
        "preparing strike, arm pulled back", "winding up, full backstroke",
        "swinging forward, arm mid-arc", "impact frame, weapon at target",
        "follow-through, arm forward", "recoil, weapon recoils back",
        "stepping back to neutral", "returning to ready pose",
    ],
    "death":  [
        "hit reaction, body jerks back", "stumbling, off-balance",
        "knee buckling, falling forward", "mid-fall, body horizontal",
        "impact with ground, dust rising", "lying still, slight twitch",
        "completely still, body relaxed", "fully dead pose",
    ],
}


async def generate_sprite_sheet(
    character_prompt: str,
    action: str,
    project_id: str,
    frames: int = 8,
) -> Dict[str, Any]:
    """Generate an `frames`-frame sprite sheet PNG. Returns asset dict."""
    deltas = ACTION_DELTAS.get(action.lower(), ACTION_DELTAS["idle"])
    deltas = deltas[:frames] + deltas[:max(0, frames - len(deltas))]

    from modules.games.fal_tools import generate_flux_pro

    common = (
        f"{character_prompt}, full body view, transparent background, "
        f"side-view, game sprite, consistent lighting and proportions, "
        f"character isolated, no environment"
    )

    tasks = []
    for delta in deltas:
        tasks.append(generate_flux_pro(
            prompt=f"{common}, action: {delta}",
            project_id=project_id,
            style_profile="stylized",
        ))
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful = [r for r in results if isinstance(r, dict) and r.get("_bytes")]
    if len(successful) < max(2, frames // 2):
        raise RuntimeError(f"Sprite-sheet failed: only {len(successful)}/{frames} frames generated")

    # Composite into a grid
    try:
        from PIL import Image
    except Exception:
        raise RuntimeError("Pillow not installed. Add `pillow` to requirements.")

    frame_size = 512  # standard
    cols = min(4, frames)
    rows = (len(successful) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * frame_size, rows * frame_size), (0, 0, 0, 0))
    for i, fa in enumerate(successful):
        img = Image.open(io.BytesIO(fa["_bytes"])).convert("RGBA")
        img.thumbnail((frame_size, frame_size), Image.LANCZOS)
        x = (i % cols) * frame_size + (frame_size - img.width) // 2
        y = (i // cols) * frame_size + (frame_size - img.height) // 2
        sheet.paste(img, (x, y), img)

    buf = io.BytesIO()
    sheet.save(buf, "PNG")
    sheet_bytes = buf.getvalue()

    asset_id = str(uuid.uuid4())
    return {
        "id": asset_id,
        "type": "sprite_sheet",
        "subtype": action,
        "name": f"{character_prompt[:40]} — {action} ({len(successful)} frames)",
        "image_url": f"/api/games/asset-image/{project_id}/{asset_id}.png",
        "_bytes": sheet_bytes,
        "frame_count": len(successful),
        "frame_size": frame_size,
        "cols": cols,
        "rows": rows,
        "approved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
