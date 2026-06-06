"""
🔐 MongoDB-backed Credentials Store
═══════════════════════════════════════════════════════════════════════
Persistent key/value storage that SURVIVES Railway container restarts.
The previous JSON-file vault (/root/.zitex/credentials.json) gets wiped
when Railway redeploys, causing FAL_KEY to vanish.

This module stores the same keys in MongoDB collection `credentials_kv`
which is permanent. _ensure_fal_key() reads from MongoDB FIRST, then
falls back to the JSON vault, then env.

Schema:
  credentials_kv
    { _id: "FAL_KEY"|"FAL_KEYS"|"ELEVENLABS_API_KEY"|...,
      value: str,
      updated_at: iso,
      updated_by: user_id }
"""
from __future__ import annotations
import os, logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Cached singleton client to avoid creating one per call
_db = None
_db_init_tried = False


def _get_db():
    """Lazy DB connection. Returns None if unable (env not configured)."""
    global _db, _db_init_tried
    if _db is not None:
        return _db
    if _db_init_tried:
        return _db
    _db_init_tried = True
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME")
        if not mongo_url or not db_name:
            return None
        client = AsyncIOMotorClient(mongo_url)
        _db = client[db_name]
        return _db
    except Exception as e:
        logger.warning(f"[creds_store] DB init failed: {e}")
        return None


async def kv_get(key: str) -> Optional[str]:
    """Async fetch. Returns None if not found."""
    db = _get_db()
    if db is None:
        return None
    try:
        doc = await db.credentials_kv.find_one({"_id": key})
        return (doc or {}).get("value")
    except Exception as e:
        logger.warning(f"[creds_store] kv_get({key}) failed: {e}")
        return None


async def kv_set(key: str, value: str, user_id: str = "system") -> bool:
    db = _get_db()
    if db is None:
        return False
    try:
        await db.credentials_kv.update_one(
            {"_id": key},
            {"$set": {
                "value": value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": user_id,
            }},
            upsert=True,
        )
        return True
    except Exception as e:
        logger.exception(f"[creds_store] kv_set({key}) failed: {e}")
        return False


async def kv_delete(key: str) -> bool:
    db = _get_db()
    if db is None:
        return False
    try:
        await db.credentials_kv.delete_one({"_id": key})
        return True
    except Exception as e:
        logger.exception(f"[creds_store] kv_delete({key}) failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────
# Sync wrappers for code paths that can't await (e.g., fal_tools._ensure_fal_key)
# Uses pymongo (sync) — same MONGO_URL.
# ─────────────────────────────────────────────────────────────
_sync_db = None
_sync_init_tried = False

def _get_sync_db():
    global _sync_db, _sync_init_tried
    if _sync_db is not None:
        return _sync_db
    if _sync_init_tried:
        return _sync_db
    _sync_init_tried = True
    try:
        from pymongo import MongoClient
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME")
        if not mongo_url or not db_name:
            return None
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=3000)
        _sync_db = client[db_name]
        return _sync_db
    except Exception as e:
        logger.warning(f"[creds_store] sync DB init failed: {e}")
        return None


def kv_get_sync(key: str) -> Optional[str]:
    db = _get_sync_db()
    if db is None:
        return None
    try:
        doc = db.credentials_kv.find_one({"_id": key})
        return (doc or {}).get("value")
    except Exception as e:
        logger.warning(f"[creds_store] kv_get_sync({key}) failed: {e}")
        return None


def kv_set_sync(key: str, value: str, user_id: str = "system") -> bool:
    db = _get_sync_db()
    if db is None:
        return False
    try:
        db.credentials_kv.update_one(
            {"_id": key},
            {"$set": {
                "value": value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": user_id,
            }},
            upsert=True,
        )
        return True
    except Exception as e:
        logger.exception(f"[creds_store] kv_set_sync({key}) failed: {e}")
        return False
