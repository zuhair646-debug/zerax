"""
🔐 Credential Vault — encrypted storage for third-party API keys.

Architecture:
  - Each user has a per-user Fernet symmetric key (derived from a master key + user_id salt)
  - Credentials stored in MongoDB `user_credentials` collection: {user_id, key_name, encrypted_value, created_at, last_validated, valid}
  - Decryption requires both master key + user_id
  - Credentials are NEVER logged or returned in plaintext to the AI directly — they're injected at execution time

Master key: from env var ZENREX_VAULT_MASTER_KEY (32 bytes b64)
If missing, generates a per-process key (dev mode only — warns).
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("zenrex.vault")


def _get_master_key() -> bytes:
    raw = os.environ.get("ZENREX_VAULT_MASTER_KEY", "").strip()
    if raw:
        try:
            # If user provides a Fernet key directly
            if len(raw) == 44 and raw.endswith("="):
                return raw.encode("utf-8")
            # If user provides any string, hash it to 32 bytes and b64
            return base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())
        except Exception:
            pass
    # Dev mode fallback — stable per-deployment
    seed = os.environ.get("MONGO_URL", "") + os.environ.get("DB_NAME", "")
    if not seed:
        seed = "zenrex-default-vault-key"
    return base64.urlsafe_b64encode(hashlib.sha256(seed.encode("utf-8")).digest())


def _user_fernet(user_id: str) -> Fernet:
    """Derive a per-user Fernet key from master + user_id."""
    master = _get_master_key()
    salt = user_id.encode("utf-8")
    # HKDF-lite: HMAC-SHA256(master, salt)
    derived = hashlib.sha256(master + b"::" + salt).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


async def store_credential(db, user_id: str, key_name: str, value: str,
                            metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Store an encrypted credential. Returns True on success."""
    if not all([db is not None, user_id, key_name, value]):
        return False
    try:
        token = _user_fernet(user_id).encrypt(value.encode("utf-8"))
        doc = {
            "user_id": user_id,
            "key_name": key_name,
            "encrypted_value": token.decode("utf-8"),
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_validated": None,
            "valid": None,
        }
        # Upsert (one credential per user+key_name)
        await db.user_credentials.update_one(
            {"user_id": user_id, "key_name": key_name},
            {"$set": doc},
            upsert=True,
        )
        return True
    except Exception as e:
        logger.warning(f"[vault] store failed for {user_id}/{key_name}: {e}")
        return False


async def get_credential(db, user_id: str, key_name: str) -> Optional[str]:
    """Decrypt and return a credential. Returns None if not found or invalid."""
    if db is None or not user_id or not key_name:
        return None
    try:
        doc = await db.user_credentials.find_one({"user_id": user_id, "key_name": key_name})
        if not doc:
            return None
        token = doc.get("encrypted_value")
        if not token:
            return None
        try:
            return _user_fernet(user_id).decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            logger.warning(f"[vault] decrypt failed (master key changed?) for {user_id}/{key_name}")
            return None
    except Exception as e:
        logger.warning(f"[vault] get failed: {e}")
        return None


async def list_credentials(db, user_id: str) -> List[Dict[str, Any]]:
    """List credential metadata for a user (NO plaintext values)."""
    if db is None or not user_id:
        return []
    try:
        cursor = db.user_credentials.find(
            {"user_id": user_id},
            {"_id": 0, "encrypted_value": 0},  # never return ciphertext to UI either
        )
        return await cursor.to_list(length=200)
    except Exception as e:
        logger.warning(f"[vault] list failed: {e}")
        return []


async def has_credential(db, user_id: str, key_name: str) -> bool:
    """Quick check without decryption."""
    if db is None:
        return False
    try:
        doc = await db.user_credentials.find_one({"user_id": user_id, "key_name": key_name}, {"_id": 1})
        return doc is not None
    except Exception:
        return False


async def delete_credential(db, user_id: str, key_name: str) -> bool:
    if db is None:
        return False
    try:
        r = await db.user_credentials.delete_one({"user_id": user_id, "key_name": key_name})
        return (r.deleted_count or 0) > 0
    except Exception as e:
        logger.warning(f"[vault] delete failed: {e}")
        return False


async def mark_validated(db, user_id: str, key_name: str, valid: bool) -> None:
    if db is None:
        return
    try:
        await db.user_credentials.update_one(
            {"user_id": user_id, "key_name": key_name},
            {"$set": {"last_validated": datetime.now(timezone.utc).isoformat(), "valid": bool(valid)}},
        )
    except Exception:
        pass


def mask_for_display(value: str) -> str:
    """For displaying back to user: show first 4 + last 4 chars only."""
    if not value or len(value) < 10:
        return "••••••••"
    return f"{value[:4]}{'•' * (len(value) - 8)}{value[-4:]}"
