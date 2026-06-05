"""
🎮 FAL.AI tools for Games Studio
─────────────────────────────────
Unified asset-generation module that powers the AAA-quality game production
pipeline. Each function downloads the result to /app/backend/uploads/games/...
and returns a local URL the frontend can render inline.

Supported tags (parsed from AI chat response):
   <<IMG_PRO: prompt>>             → Flux Pro Ultra 1.1 — cinematic 4K image
   <<3D: prompt>>                  → Trellis — text-to-3D (.glb)
   <<ANIMATE: prompt | img: url>>  → Kling 1.6 image-to-video animation
   <<MUSIC: prompt | dur: 30>>     → CassetteAI — game soundtrack
   <<SFX: prompt | dur: 5>>        → MMAudio v2 — sound effects

The basic <<IMG: ...>> tag is still served by OpenAI gpt-image-1 (handled in
game_router.py) — fast & cheap drafts. Use IMG_PRO for hero shots.
"""
from __future__ import annotations
import os
import re
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

UPLOAD_ROOT = "/app/backend/uploads/games"


def _ensure_fal_key() -> str:
    key = os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY") or ""
    if not key:
        raise RuntimeError("FAL_KEY missing — set it in /app/backend/.env")
    # fal-client reads from FAL_KEY env var automatically
    os.environ["FAL_KEY"] = key
    return key


async def _download_to(url: str, dest_path: str, timeout: float = 120.0) -> None:
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(r.content)


async def _fal_submit(model_endpoint: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Submit a fal.ai job and wait for completion. Returns the result dict."""
    _ensure_fal_key()
    import fal_client  # lazy import — only loaded if FAL_KEY is set

    def _sync_submit():
        # fal_client.submit() is sync; we wrap in run_in_executor for async use
        handler = fal_client.submit(model_endpoint, arguments=arguments)
        return handler.get()  # blocks until job finishes

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_submit)


# ════════════════════════════════════════════════════════════════
# 1) Flux Pro Ultra 1.1 — cinematic hero image
# ════════════════════════════════════════════════════════════════
async def generate_flux_pro(prompt: str, project_id: str, aspect_ratio: str = "16:9") -> Dict[str, Any]:
    """High-end cinematic image generation. ~$0.06/image, ~10-20 sec."""
    result = await _fal_submit(
        "fal-ai/flux-pro/v1.1-ultra",
        {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "num_images": 1,
            "enable_safety_checker": True,
            "safety_tolerance": "5",
            "output_format": "png",
            "raw": False,
        },
    )
    img_url = (result.get("images") or [{}])[0].get("url")
    if not img_url:
        raise RuntimeError(f"flux_pro returned no image: {result}")
    asset_id = str(uuid.uuid4())
    dest = f"{UPLOAD_ROOT}/{project_id}/assets/{asset_id}.png"
    await _download_to(img_url, dest)
    # Read the bytes back so caller can also persist to GridFS (survives redeploys)
    try:
        with open(dest, "rb") as fh:
            img_bytes = fh.read()
    except Exception:
        img_bytes = None
    return {
        "id": asset_id,
        "type": "image",
        "subtype": "flux-pro-ultra",
        "image_url": f"/api/games/asset-image/{project_id}/{asset_id}.png",
        "cdn_url": img_url,  # 🔒 Fal CDN URL as fallback (lives ~weeks)
        "_bytes": img_bytes,  # 🔒 caller must pop & persist to GridFS then delete this key
        "prompt": prompt,
        "name": prompt[:80],
        "approved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ════════════════════════════════════════════════════════════════
# 2) Trellis — text-to-3D (.glb mesh)
# ════════════════════════════════════════════════════════════════
async def generate_3d_model(prompt: str, project_id: str, reference_image_url: Optional[str] = None) -> Dict[str, Any]:
    """Generate a real 3D model (.glb) from text or image. ~$0.30, ~1-3 min."""
    # If we have a reference image, use trellis image-to-3D, else fall back to hyper3d-rodin (text-to-3D)
    if reference_image_url:
        model_id = "fal-ai/trellis"
        args = {"image_url": reference_image_url}
    else:
        # Hyper3D Rodin is the best text-to-3D currently on fal
        model_id = "fal-ai/hyper3d/rodin"
        args = {"prompt": prompt, "geometry_file_format": "glb"}

    result = await _fal_submit(model_id, args)
    # Extract glb URL — different fields per model
    model_url = None
    if "model_mesh" in result:
        mm = result["model_mesh"]
        model_url = mm.get("url") if isinstance(mm, dict) else mm
    elif "mesh" in result:
        m = result["mesh"]
        model_url = m.get("url") if isinstance(m, dict) else m
    elif "output_mesh" in result:
        model_url = result["output_mesh"].get("url") if isinstance(result["output_mesh"], dict) else result["output_mesh"]
    if not model_url:
        raise RuntimeError(f"3d model returned no mesh url: {result}")
    asset_id = str(uuid.uuid4())
    dest = f"{UPLOAD_ROOT}/{project_id}/3d/{asset_id}.glb"
    await _download_to(model_url, dest, timeout=180.0)
    try:
        with open(dest, "rb") as fh:
            file_bytes = fh.read()
    except Exception:
        file_bytes = None
    return {
        "id": asset_id,
        "type": "3d",
        "subtype": "hyper3d-rodin" if not reference_image_url else "trellis",
        "model_url": f"/api/games/asset-3d/{project_id}/{asset_id}.glb",
        "cdn_url": model_url,
        "_bytes": file_bytes,
        "prompt": prompt,
        "name": prompt[:80],
        "approved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ════════════════════════════════════════════════════════════════
# 3) Kling 1.6 — image-to-video animation
# ════════════════════════════════════════════════════════════════
async def animate_image(prompt: str, image_url: str, project_id: str, duration: int = 5) -> Dict[str, Any]:
    """Animate a still image into a 5-10s video clip. ~$0.50, ~1-2 min."""
    result = await _fal_submit(
        "fal-ai/kling-video/v1.6/standard/image-to-video",
        {
            "prompt": prompt,
            "image_url": image_url,
            "duration": str(duration),  # "5" or "10"
            "aspect_ratio": "16:9",
        },
    )
    video_url = (result.get("video") or {}).get("url") if isinstance(result.get("video"), dict) else None
    if not video_url:
        raise RuntimeError(f"kling returned no video: {result}")
    asset_id = str(uuid.uuid4())
    dest = f"{UPLOAD_ROOT}/{project_id}/videos/{asset_id}.mp4"
    await _download_to(video_url, dest, timeout=180.0)
    try:
        with open(dest, "rb") as fh:
            file_bytes = fh.read()
    except Exception:
        file_bytes = None
    return {
        "id": asset_id,
        "type": "video",
        "subtype": "kling-1.6",
        "video_url": f"/api/games/asset-video/{project_id}/{asset_id}.mp4",
        "cdn_url": video_url,
        "_bytes": file_bytes,
        "prompt": prompt,
        "name": prompt[:80],
        "duration_sec": duration,
        "approved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ════════════════════════════════════════════════════════════════
# 4) CassetteAI — text-to-music for game soundtracks
# ════════════════════════════════════════════════════════════════
async def generate_music(prompt: str, project_id: str, duration: int = 30) -> Dict[str, Any]:
    """Generate game background music. ~$0.03/30sec, ~10-30 sec."""
    result = await _fal_submit(
        "cassetteai/music-generator",
        {
            "prompt": prompt,
            "duration": min(int(duration), 180),
        },
    )
    audio_url = (result.get("audio_file") or {}).get("url") if isinstance(result.get("audio_file"), dict) else result.get("url")
    if not audio_url:
        raise RuntimeError(f"music gen returned no audio: {result}")
    asset_id = str(uuid.uuid4())
    dest = f"{UPLOAD_ROOT}/{project_id}/audio/{asset_id}.wav"
    await _download_to(audio_url, dest)
    try:
        with open(dest, "rb") as fh:
            file_bytes = fh.read()
    except Exception:
        file_bytes = None
    return {
        "id": asset_id,
        "type": "music",
        "subtype": "cassetteai",
        "audio_url": f"/api/games/asset-audio/{project_id}/{asset_id}.wav",
        "cdn_url": audio_url,
        "_bytes": file_bytes,
        "prompt": prompt,
        "name": prompt[:80],
        "duration_sec": duration,
        "approved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ════════════════════════════════════════════════════════════════
# 5) ElevenLabs SFX (via fal) — text-to-sound effects
# ════════════════════════════════════════════════════════════════
async def generate_sfx(prompt: str, project_id: str, duration: int = 5) -> Dict[str, Any]:
    """Generate a game sound effect via CassetteAI (jump, hit, coin, etc). ~$0.01, ~3-5 sec."""
    result = await _fal_submit(
        "cassetteai/sound-effects-generator",
        {
            "prompt": prompt,
            "duration": min(max(int(duration), 1), 30),
        },
    )
    audio_url = (result.get("audio_file") or {}).get("url") if isinstance(result.get("audio_file"), dict) else result.get("url")
    if not audio_url:
        raise RuntimeError(f"sfx returned no audio: {result}")
    asset_id = str(uuid.uuid4())
    dest = f"{UPLOAD_ROOT}/{project_id}/audio/{asset_id}.wav"
    await _download_to(audio_url, dest)
    try:
        with open(dest, "rb") as fh:
            file_bytes = fh.read()
    except Exception:
        file_bytes = None
    return {
        "id": asset_id,
        "type": "sfx",
        "subtype": "cassetteai-sfx",
        "audio_url": f"/api/games/asset-audio/{project_id}/{asset_id}.wav",
        "cdn_url": audio_url,
        "_bytes": file_bytes,
        "prompt": prompt,
        "name": prompt[:80],
        "duration_sec": duration,
        "approved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ════════════════════════════════════════════════════════════════
# Tag parser + dispatcher
# ════════════════════════════════════════════════════════════════
TAG_RE = re.compile(r"<<(IMG_PRO|3D|ANIMATE|MUSIC|SFX):\s*(.+?)>>", re.DOTALL)


async def parse_and_generate_assets(
    ai_response: str,
    project_id: str,
    max_assets_per_turn: int = 3,
) -> List[Dict[str, Any]]:
    """
    Parse all asset tags from the AI's response and generate them concurrently.
    Returns a list of generated asset dicts (ready to be appended to project + sent to frontend).

    The basic <<IMG: ...>> tag is NOT handled here (kept in game_router for backward compat).
    """
    matches = TAG_RE.findall(ai_response)
    if not matches:
        return []

    matches = matches[:max_assets_per_turn]
    tasks = []

    for tag_type, raw_body in matches:
        body = raw_body.strip()
        try:
            if tag_type == "IMG_PRO":
                tasks.append(generate_flux_pro(body, project_id))
            elif tag_type == "3D":
                tasks.append(generate_3d_model(body, project_id))
            elif tag_type == "ANIMATE":
                # syntax: <<ANIMATE: prompt | img: URL>>
                img_url = None
                if "img:" in body:
                    parts = body.split("|", 1)
                    prompt = parts[0].strip()
                    img_part = parts[1].strip()
                    img_url = img_part.replace("img:", "").strip()
                else:
                    prompt = body
                if not img_url:
                    logger.warning("[fal] ANIMATE tag missing img: URL — skipping")
                    continue
                tasks.append(animate_image(prompt, img_url, project_id))
            elif tag_type == "MUSIC":
                dur = 30
                if "dur:" in body:
                    parts = body.rsplit("|", 1)
                    prompt = parts[0].strip()
                    try:
                        dur = int(parts[1].replace("dur:", "").strip())
                    except Exception:
                        dur = 30
                else:
                    prompt = body
                tasks.append(generate_music(prompt, project_id, duration=dur))
            elif tag_type == "SFX":
                dur = 5
                if "dur:" in body:
                    parts = body.rsplit("|", 1)
                    prompt = parts[0].strip()
                    try:
                        dur = int(parts[1].replace("dur:", "").strip())
                    except Exception:
                        dur = 5
                else:
                    prompt = body
                tasks.append(generate_sfx(prompt, project_id, duration=dur))
        except Exception as e:
            logger.exception(f"[fal] failed to queue {tag_type}: {e}")

    if not tasks:
        return []

    results: List[Dict[str, Any]] = []
    settled = await asyncio.gather(*tasks, return_exceptions=True)
    for res in settled:
        if isinstance(res, Exception):
            logger.exception(f"[fal] asset generation failed: {res}")
        else:
            results.append(res)
    return results
