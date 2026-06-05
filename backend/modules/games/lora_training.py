"""
🎨 Fal.ai Flux LoRA Style Training
═══════════════════════════════════════════════════════════════════════
Trains a project-specific LoRA (Low-Rank Adapter) on the approved image
assets of a game project, so every subsequent image generation uses the
SAME visual DNA — characters look identical, props look identical, the
whole art direction stays 100% consistent.

Endpoints exposed via `game_router.py`:
  • POST /api/games/project/{id}/train-style
        Kicks off a background training job. Returns immediately with
        `status: "queued"`. Frontend polls the GET endpoint below.
  • GET  /api/games/project/{id}/train-style
        Returns `{ status, lora_url, trigger_word, error, started_at,
        finished_at, num_images }` reflecting the latest training run.

Project document fields added by this module (under `lora`):
  status         : queued | training | ready | error
  lora_url       : URL to the trained `diffusers_lora_file` (used in gen)
  trigger_word   : short token to mention in prompts (auto: zitex_{id8})
  num_images     : how many images were sent to training
  started_at     : ISO timestamp
  finished_at    : ISO timestamp
  error          : str (if status == error)

After training is `ready`, the existing `generate_flux_pro` call in
fal_tools.py automatically switches to `fal-ai/flux-lora` with the
trained weights — no other code changes required.
"""
from __future__ import annotations
import os
import io
import asyncio
import logging
import zipfile
import tempfile
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

# Fal Flux LoRA fast trainer — ~5-10 min, ~$2 per training
FAL_TRAIN_MODEL = "fal-ai/flux-lora-fast-training"

# Min/max images we will accept for a training run
MIN_TRAIN_IMAGES = 5
MAX_TRAIN_IMAGES = 30


def _ensure_fal_key() -> str:
    key = os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY") or ""
    if not key:
        raise RuntimeError("FAL_KEY missing — set it in /app/backend/.env")
    os.environ["FAL_KEY"] = key
    return key


async def _collect_training_images(db, project_id: str) -> List[bytes]:
    """Pull APPROVED image bytes from GridFS for this project.
    Falls back to CDN download if a particular file is not in GridFS yet.
    """
    proj = await db.game_projects.find_one(
        {"id": project_id},
        {"assets.images": 1},
    )
    if not proj:
        return []
    imgs = ((proj.get("assets") or {}).get("images") or [])
    approved = [a for a in imgs if a.get("approved") and a.get("type") == "image"]
    # Newest first, capped
    approved = approved[-MAX_TRAIN_IMAGES:]
    out: List[bytes] = []

    # Try GridFS first via persistence.load_bytes
    try:
        from modules.games.persistence import load_bytes as _load_bytes
    except Exception:
        _load_bytes = None

    for a in approved:
        asset_id = a.get("id")
        cdn_url = a.get("cdn_url")
        raw: Optional[bytes] = None
        if _load_bytes and asset_id:
            try:
                raw = await _load_bytes(db, asset_id)
            except Exception:
                raw = None
        if (not raw) and cdn_url:
            try:
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as cli:
                    r = await cli.get(cdn_url)
                    if r.status_code == 200 and r.content:
                        raw = r.content
            except Exception as e:
                logger.warning(f"[lora] CDN fetch failed for {asset_id}: {e}")
        if raw:
            out.append(raw)
    return out


def _make_training_zip(image_bytes_list: List[bytes]) -> str:
    """Create a temp ZIP file of training images and return its path.
    Each image is renamed to image_NN.png inside the archive (fal expects
    a flat zip of images; no captions = use trigger_word instead).
    """
    fd, path = tempfile.mkstemp(prefix="zitex_lora_", suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
        for i, b in enumerate(image_bytes_list, start=1):
            zf.writestr(f"image_{i:02d}.png", b)
    return path


async def _upload_to_fal(zip_path: str) -> str:
    """Upload local zip to fal CDN and return the URL."""
    _ensure_fal_key()
    import fal_client  # lazy import

    def _sync_upload() -> str:
        return fal_client.upload_file(zip_path)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_upload)


async def _submit_training(images_data_url: str, trigger_word: str) -> Dict[str, Any]:
    """Block until fal-ai/flux-lora-fast-training finishes."""
    _ensure_fal_key()
    import fal_client

    def _sync_submit() -> Dict[str, Any]:
        handler = fal_client.submit(
            FAL_TRAIN_MODEL,
            arguments={
                "images_data_url": images_data_url,
                "trigger_word": trigger_word,
                "is_style": True,        # style LoRA = great for art-direction consistency
                "create_masks": False,   # masks help character LoRA, not style
                "steps": 1000,
            },
        )
        return handler.get()

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_submit)


async def run_style_training_background(db, project_id: str) -> None:
    """The actual long-running task. Updates the project doc as it progresses."""
    trigger_word = f"zitex_{project_id[:8].replace('-', '')}"
    started_at = datetime.now(timezone.utc).isoformat()

    # mark as training
    await db.game_projects.update_one(
        {"id": project_id},
        {"$set": {
            "lora.status": "training",
            "lora.trigger_word": trigger_word,
            "lora.started_at": started_at,
            "lora.error": None,
            "lora.finished_at": None,
        }},
    )

    try:
        images = await _collect_training_images(db, project_id)
        if len(images) < MIN_TRAIN_IMAGES:
            raise RuntimeError(
                f"تحتاج على الأقل {MIN_TRAIN_IMAGES} صور معتمدة (الحالي: {len(images)})."
            )

        zip_path = _make_training_zip(images)
        try:
            data_url = await _upload_to_fal(zip_path)
            logger.info(f"[lora] uploaded {len(images)} images for project={project_id} → {data_url}")
            result = await _submit_training(data_url, trigger_word)
        finally:
            try:
                os.unlink(zip_path)
            except Exception:
                pass

        # Result shape: { "diffusers_lora_file": { "url": "..." }, "config_file": { "url": "..." } }
        lora_node = result.get("diffusers_lora_file") if isinstance(result, dict) else None
        lora_url = (lora_node.get("url") if isinstance(lora_node, dict) else lora_node) or ""
        if not lora_url:
            raise RuntimeError(f"Training returned no diffusers_lora_file: {result}")

        await db.game_projects.update_one(
            {"id": project_id},
            {"$set": {
                "lora.status": "ready",
                "lora.lora_url": lora_url,
                "lora.num_images": len(images),
                "lora.finished_at": datetime.now(timezone.utc).isoformat(),
                "lora.error": None,
            }},
        )
        logger.info(f"[lora] ✅ training ready for project={project_id} url={lora_url}")
    except Exception as e:
        logger.exception(f"[lora] training failed for project={project_id}: {e}")
        await db.game_projects.update_one(
            {"id": project_id},
            {"$set": {
                "lora.status": "error",
                "lora.error": str(e)[:400],
                "lora.finished_at": datetime.now(timezone.utc).isoformat(),
            }},
        )


# ───────────────────────────────────────────────────────────
# Inference helper — generate using the trained LoRA
# Called from fal_tools.generate_flux_pro when project has a ready LoRA.
# ───────────────────────────────────────────────────────────
async def generate_with_project_lora(
    prompt: str,
    project_id: str,
    lora_url: str,
    trigger_word: str = "",
    aspect_ratio: str = "16:9",
) -> Dict[str, Any]:
    """Run fal-ai/flux-lora with the project's trained weights.
    Returns the same shape as generate_flux_pro (id, image_url, cdn_url,
    _bytes, prompt, name, approved, created_at, subtype="flux-lora").
    """
    _ensure_fal_key()
    import fal_client

    # Inject trigger_word into the prompt so the LoRA activates strongly
    enriched = prompt
    if trigger_word and trigger_word.lower() not in (prompt or "").lower():
        enriched = f"{trigger_word} style, {prompt}"

    def _sync_submit() -> Dict[str, Any]:
        handler = fal_client.submit(
            "fal-ai/flux-lora",
            arguments={
                "prompt": enriched,
                "loras": [{"path": lora_url, "scale": 1.0}],
                "image_size": "landscape_16_9" if aspect_ratio == "16:9" else "square_hd",
                "num_inference_steps": 32,
                "guidance_scale": 3.5,
                "num_images": 1,
                "enable_safety_checker": True,
                "output_format": "png",
            },
        )
        return handler.get()

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _sync_submit)

    img_url = (result.get("images") or [{}])[0].get("url")
    if not img_url:
        raise RuntimeError(f"flux-lora returned no image: {result}")

    # Re-use the same download helper as fal_tools to keep paths identical
    from modules.games.fal_tools import _download_to, UPLOAD_ROOT  # safe internal import
    asset_id = str(uuid.uuid4())
    dest = f"{UPLOAD_ROOT}/{project_id}/assets/{asset_id}.png"
    await _download_to(img_url, dest)
    try:
        with open(dest, "rb") as fh:
            img_bytes = fh.read()
    except Exception:
        img_bytes = None
    return {
        "id": asset_id,
        "type": "image",
        "subtype": "flux-lora",  # so the UI badge can show "Trained Style"
        "image_url": f"/api/games/asset-image/{project_id}/{asset_id}.png",
        "cdn_url": img_url,
        "_bytes": img_bytes,
        "prompt": prompt,
        "name": prompt[:80],
        "approved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "used_lora": True,
    }
