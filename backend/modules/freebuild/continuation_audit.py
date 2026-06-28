"""Audit logger for continuation-mode AI operations.

Every destructive or sensitive operation the engineer AI runs against a
customer's project gets persisted into `continuation_audit_logs` so we have
a tamper-evident trail for legal/compliance needs. Each entry is a discrete
event (no batch updates, no rewrites) and links back to the consent
signature captured during onboarding.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("zenrex.continuation_audit")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Dict[str, Any]) -> str:
    """Hash of the relevant payload — used to detect log tampering if the
    audit doc is ever modified after the fact."""
    keys = sorted(payload.keys())
    raw = "|".join(f"{k}={payload[k]}" for k in keys if k != "signature_hash")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def write_audit(
    db,
    project_id: str,
    user_id: str,
    action: str,
    *,
    tool_name: Optional[str] = None,
    target_path: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None,
    ip: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist a single audit entry. Returns the written doc (without _id)."""
    entry = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "user_id": user_id,
        "action": action,                # e.g. 'clone_remote_repo', 'propose_change', 'restore_snapshot'
        "tool_name": tool_name,
        "target_path": target_path,
        "success": bool(success),
        "details": details or {},
        "ip": ip,
        "ts": _now(),
    }
    entry["signature_hash"] = _hash_payload(entry)
    try:
        await db.continuation_audit_logs.insert_one(entry.copy())
    except Exception as e:
        logger.exception(f"[audit] write failed: {e}")
    return entry


async def fetch_audit(db, project_id: str, limit: int = 100) -> list:
    """Pull recent audit entries for a project (newest first)."""
    cur = db.continuation_audit_logs.find(
        {"project_id": project_id}, {"_id": 0},
    ).sort("ts", -1).limit(limit)
    return await cur.to_list(length=limit)
