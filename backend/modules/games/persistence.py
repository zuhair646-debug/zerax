"""
🗄️ Permanent asset persistence for game studio.

Stores generated images/audio/3d/video bytes in MongoDB GridFS so they survive
container redeploys (Railway/Vercel ephemeral disks). Also keeps the original
CDN URL (when available) as a third-level fallback.

Lookup order in serve_asset_*:
  1. Local disk cache  (fastest)
  2. MongoDB GridFS    (permanent, survives redeploys)
  3. cdn_url redirect  (Fal CDN — eventually expires)
  4. 404
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorGridFSBucket

logger = logging.getLogger(__name__)


def _bucket(db) -> AsyncIOMotorGridFSBucket:
    """Get/create the games_assets GridFS bucket on the given motor db."""
    return AsyncIOMotorGridFSBucket(db, bucket_name="games_assets")


async def persist_bytes(db, asset_id: str, content: bytes, content_type: str, project_id: str) -> bool:
    """Upload bytes to GridFS using asset_id as filename (idempotent — overwrites by deleting first)."""
    try:
        bucket = _bucket(db)
        # Drop any existing entry with the same filename so we never duplicate
        async for f in bucket.find({"filename": asset_id}):
            try:
                await bucket.delete(f["_id"])
            except Exception:
                pass
        await bucket.upload_from_stream(
            asset_id,
            content,
            metadata={"project_id": project_id, "content_type": content_type},
        )
        return True
    except Exception as e:
        logger.warning(f"[persistence] GridFS upload failed for {asset_id}: {e}")
        return False


async def load_bytes(db, asset_id: str) -> Optional[bytes]:
    """Download bytes from GridFS, or None if missing."""
    try:
        bucket = _bucket(db)
        cursor = bucket.find({"filename": asset_id}).limit(1)
        async for f in cursor:
            stream = await bucket.open_download_stream(f._id)
            data = await stream.read()
            return data
        return None
    except Exception as e:
        logger.warning(f"[persistence] GridFS download failed for {asset_id}: {e}")
        return None


async def lookup_asset_in_project(db, project_id: str, asset_id: str) -> Optional[dict]:
    """Find a single asset dict by its id inside a project's conversation history."""
    proj = await db.game_projects.find_one({"id": project_id})
    if not proj:
        return None
    # 1) Check assets buckets (newer layout)
    for bucket_name in ("images", "models3d", "audio", "videos"):
        for a in (proj.get("assets", {}) or {}).get(bucket_name, []) or []:
            if a.get("id") == asset_id:
                return a
    # 2) Fallback — walk through every message's generated_assets
    for ph in (proj.get("phases") or {}).values():
        for m in (ph.get("messages") or []):
            for a in (m.get("generated_assets") or []):
                if a.get("id") == asset_id:
                    return a
    return None


def local_path(project_id: str, kind: str, asset_id: str, ext: str) -> str:
    """Build local disk path for an asset; kind in {assets, 3d, audio, videos}."""
    return f"/app/backend/uploads/games/{project_id}/{kind}/{asset_id}.{ext}"


async def warm_cache(local_path_str: str, content: bytes) -> bool:
    """Best-effort write-through cache from GridFS or CDN back to local disk."""
    try:
        os.makedirs(os.path.dirname(local_path_str), exist_ok=True)
        with open(local_path_str, "wb") as f:
            f.write(content)
        return True
    except Exception as e:
        logger.warning(f"[persistence] local cache write failed: {e}")
        return False
