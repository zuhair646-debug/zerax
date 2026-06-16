"""Owner Notifications router.

The AI agent (in `workflow_tools.notify_owner`) silently inserts entries into
`owner_notifications` whenever an integration fails — e.g. fal.ai key rejected,
quota exceeded, OpenAI 429. This router exposes them to the admin dashboard's
bell-icon component so the platform team gets alerted without bothering the
end user.

Scope: ONLY users with role ∈ {owner, admin, superuser} can read/mark these.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient

router = APIRouter(prefix="/api/owner/notifications", tags=["owner-notifications"])

# Reuse the shared Mongo connection. Importing from server avoids a second
# connection pool. Falls back to a local client only if used outside server.py.
try:
    from server import db  # type: ignore
except Exception:  # pragma: no cover
    _client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = _client[os.environ["DB_NAME"]]


async def _require_owner(user=None):
    """Lazy import to avoid circular dependency with auth router."""
    from server import get_current_user  # type: ignore
    if user is None:
        # FastAPI will inject via Depends below; this branch only executes
        # when someone calls _require_owner manually.
        raise HTTPException(401, "auth required")
    role = (user.get("role") or "").lower()
    if role not in {"owner", "admin", "superuser"}:
        raise HTTPException(403, "owner-only endpoint")
    return user


# We need `get_current_user` as a Depends. Re-import lazily.
def _auth_dep():
    from server import get_current_user  # type: ignore
    return get_current_user


@router.get("")
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    user=Depends(_auth_dep()),
):
    role = (user.get("role") or "").lower()
    if role not in {"owner", "admin", "superuser"}:
        raise HTTPException(403, "owner-only endpoint")
    q: Dict[str, Any] = {}
    if unread_only:
        q["read"] = False
    cur = db.owner_notifications.find(q, {"_id": 0}).sort("created_at", -1).limit(limit)
    items: List[Dict[str, Any]] = []
    async for d in cur:
        items.append(d)
    unread = await db.owner_notifications.count_documents({"read": False})
    return {"items": items, "unread_count": unread, "total": len(items)}


@router.post("/{nid}/read")
async def mark_read(nid: str, user=Depends(_auth_dep())):
    role = (user.get("role") or "").lower()
    if role not in {"owner", "admin", "superuser"}:
        raise HTTPException(403, "owner-only endpoint")
    r = await db.owner_notifications.update_one({"id": nid}, {"$set": {"read": True}})
    return {"ok": True, "matched": r.matched_count}


@router.post("/mark-all-read")
async def mark_all_read(user=Depends(_auth_dep())):
    role = (user.get("role") or "").lower()
    if role not in {"owner", "admin", "superuser"}:
        raise HTTPException(403, "owner-only endpoint")
    r = await db.owner_notifications.update_many({"read": False}, {"$set": {"read": True}})
    return {"ok": True, "updated": r.modified_count}
