"""User Storage Quota + Recovery Request endpoints.

Goal: give every customer an honest, byte-accurate view of how much space
their projects take, defined tiers (free + paid for big users), and a one-
click "recover my data" channel that lands as an owner notification so the
team can restore from backup.

What counts toward a user's quota:
  • Every text message in every project (UTF-8 bytes)
  • Every engineering doc (`freebuild_project_docs`)
  • Every generated/uploaded asset file on disk (`uploads/freebuild_media/<uid>/`)
  • Every html_snapshot stored inline in the project (text length)

Tier definitions live in `STORAGE_TIERS` at the top and can be tuned without
touching the rest of the codebase.
"""
from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/me/storage", tags=["storage"])

try:
    from server import db  # type: ignore
except Exception:  # pragma: no cover
    _client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = _client[os.environ["DB_NAME"]]


# ─── Storage Tiers ────────────────────────────────────────────────────────────
# Free is generous on purpose — most casual users will never hit it. Paid tiers
# are for power users with full series / many projects / large video archives.
# Sizes in BYTES (1 GB = 1024**3 = 1_073_741_824).
GB = 1024 ** 3
MB = 1024 ** 2

STORAGE_TIERS: List[Dict[str, Any]] = [
    {
        "id": "free", "name_ar": "مجاني", "name_en": "Free",
        "quota_bytes": 500 * MB, "price_usd": 0,
        "description_ar": "ابدأ بمشاريع صغيرة وجرّب كل شي — 500 ميجا تكفي ~10 مشاريع فيديو قصيرة",
        "features": ["مشاريع غير محدودة العدد", "كل أدوات الذكاء", "نسخ احتياطية يومية"],
    },
    {
        "id": "creator", "name_ar": "المبدع", "name_en": "Creator",
        "quota_bytes": 5 * GB, "price_usd": 5,  # $5/شهر = ~18 ريال
        "description_ar": "5 جيجا — مناسب لمسلسل أنمي قصير (10-20 حلقة قصيرة)",
        "features": ["كل ميزات المجاني", "5 جيجا تخزين", "أولوية في الدعم"],
    },
    {
        "id": "studio", "name_ar": "الاستوديو", "name_en": "Studio",
        "quota_bytes": 50 * GB, "price_usd": 25,  # $25/شهر = ~95 ريال
        "description_ar": "50 جيجا — للمسلسلات الكبيرة وأفلام طويلة بجودة عالية",
        "features": ["كل ميزات المبدع", "50 جيجا تخزين", "استرداد فوري من النسخ"],
    },
    {
        "id": "enterprise", "name_ar": "المؤسسة", "name_en": "Enterprise",
        "quota_bytes": 500 * GB, "price_usd": 99,
        "description_ar": "نصف تيرابايت — للمحترفين والوكالات",
        "features": ["كل ميزات الاستوديو", "500 جيجا", "نسخ خارجية على GitHub", "SLA"],
    },
]


def _tier_by_id(tid: str) -> Dict[str, Any]:
    for t in STORAGE_TIERS:
        if t["id"] == tid:
            return t
    return STORAGE_TIERS[0]


def _utf8_len(s: Any) -> int:
    """Cheap byte-count for stored text. Falls back to 0 on weird types."""
    try:
        return len(str(s).encode("utf-8"))
    except Exception:
        return 0


async def _calc_text_bytes(user_id: str) -> Dict[str, int]:
    """Walk every project + every doc owned by this user and tally byte counts.

    Returns a category breakdown — never throws on bad data, callers can trust
    the numbers are >= 0.
    """
    msg_bytes = 0
    snap_bytes = 0
    html_bytes = 0
    project_count = 0
    msg_count = 0
    proj_cur = db.freebuild_projects.find(
        {"user_id": user_id, "status": {"$ne": "deleted"}},
        {"_id": 0, "id": 1, "messages": 1, "html_snapshots": 1, "current_html": 1},
    )
    async for p in proj_cur:
        project_count += 1
        for m in p.get("messages") or []:
            msg_count += 1
            msg_bytes += _utf8_len(m.get("content", ""))
            for img in m.get("inline_images") or []:
                msg_bytes += _utf8_len(img.get("url", "")) + _utf8_len(img.get("caption", ""))
            for au in m.get("inline_audio") or []:
                msg_bytes += _utf8_len(au.get("url", "")) + _utf8_len(au.get("caption", ""))
        for s in p.get("html_snapshots") or []:
            snap_bytes += _utf8_len(s.get("html", "")) + _utf8_len(s.get("summary", ""))
        if p.get("current_html"):
            html_bytes += _utf8_len(p["current_html"])

    # Engineering docs (decisions, character_sheet, ...)
    doc_bytes = 0
    doc_count = 0
    doc_cur = db.freebuild_project_docs.find({"user_id": user_id}, {"content": 1, "_id": 0})
    async for d in doc_cur:
        doc_count += 1
        doc_bytes += _utf8_len(d.get("content", ""))
    return {
        "project_count": project_count, "msg_count": msg_count, "doc_count": doc_count,
        "msg_bytes": msg_bytes, "snap_bytes": snap_bytes,
        "html_bytes": html_bytes, "doc_bytes": doc_bytes,
    }


def _calc_file_bytes(user_id: str) -> Dict[str, int]:
    """Sum on-disk media files. Falls back to 0 on missing dir (e.g. dev box)."""
    root = Path(f"/app/backend/uploads/freebuild_media/{user_id}")
    if not root.exists():
        return {"file_count": 0, "file_bytes": 0}
    total = 0
    count = 0
    try:
        for f in root.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
                count += 1
    except (OSError, PermissionError):
        pass
    return {"file_count": count, "file_bytes": total}


def _auth_dep():
    from server import get_current_user  # type: ignore
    return get_current_user


@router.get("/usage")
async def my_storage_usage(user=Depends(_auth_dep())):
    """Honest byte-accurate breakdown. The bar the user sees comes from here."""
    uid = user["user_id"]
    text = await _calc_text_bytes(uid)
    files = _calc_file_bytes(uid)
    total_bytes = (text["msg_bytes"] + text["snap_bytes"] + text["html_bytes"]
                   + text["doc_bytes"] + files["file_bytes"])

    # Look up user's tier (defaults to free)
    tier_id = "free"
    try:
        u = await db.users.find_one({"id": uid}, {"storage_tier": 1, "_id": 0}) or {}
        tier_id = u.get("storage_tier") or "free"
    except Exception:
        pass
    tier = _tier_by_id(tier_id)

    quota = tier["quota_bytes"]
    pct = round((total_bytes / quota) * 100, 2) if quota > 0 else 0
    return {
        "tier": tier,
        "used_bytes": total_bytes,
        "quota_bytes": quota,
        "used_pct": pct,
        "over_quota": total_bytes > quota,
        "breakdown": {
            "messages_text": text["msg_bytes"],
            "html_snapshots": text["snap_bytes"],
            "current_html": text["html_bytes"],
            "engineering_docs": text["doc_bytes"],
            "media_files_on_disk": files["file_bytes"],
        },
        "counts": {
            "projects": text["project_count"],
            "messages": text["msg_count"],
            "docs": text["doc_count"],
            "files": files["file_count"],
        },
    }


@router.get("/tiers")
async def list_tiers():
    """Public — anyone can see the pricing ladder."""
    return {"tiers": STORAGE_TIERS}


# ─── Recovery Requests ───────────────────────────────────────────────────────
# Customer presses "I lost data" → we file an owner_notifications entry +
# a recovery_requests row. The owner sees both in the admin dashboard and
# can restore the affected project from the relevant daily backup archive.

class RecoveryIn(BaseModel):
    project_id: str | None = Field(None, description="Optional — narrow recovery to one project")
    description: str = Field(..., min_length=10, max_length=2000,
                             description="What was lost? When did the user notice?")
    contact_method: str = Field("in_app", description="email | whatsapp | in_app")


@router.post("/recovery-request")
async def request_recovery(payload: RecoveryIn, user=Depends(_auth_dep())):
    rid = str(uuid.uuid4())
    doc = {
        "id": rid,
        "user_id": user["user_id"],
        "user_email": user.get("email"),
        "project_id": payload.project_id,
        "description": payload.description.strip()[:2000],
        "contact_method": payload.contact_method[:30],
        "status": "pending",  # pending → in_progress → resolved | rejected
        "created_at": time.time(),
        "resolved_at": None,
        "owner_note": None,
    }
    await db.recovery_requests.insert_one(doc)
    # Also push to owner notifications so the bell rings
    await db.owner_notifications.insert_one({
        "id": str(uuid.uuid4()),
        "created_at": time.time(),
        "category": "user_complaint",
        "severity": "high",
        "summary": f"طلب استرداد بيانات من {user.get('email') or user.get('user_id')}",
        "details": (f"recovery_id={rid}\nproject={payload.project_id or '(الكل)'}"
                    f"\ncontact={payload.contact_method}\n\nالشكوى:\n{payload.description}"),
        "project_id": payload.project_id,
        "user_id": user["user_id"],
        "read": False,
    })
    return {"ok": True, "recovery_id": rid,
            "message": "تم استلام طلبك. سيتواصل معك الفريق خلال 24 ساعة لاسترداد بياناتك من النسخ الاحتياطية."}


@router.get("/recovery-requests/mine")
async def my_recovery_requests(user=Depends(_auth_dep())):
    """User can track their own recovery tickets."""
    cur = db.recovery_requests.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).limit(50)
    items = [d async for d in cur]
    return {"items": items, "count": len(items)}


# ─── Owner endpoints (for the admin dashboard) ────────────────────────────────
def _require_owner_dep():
    from server import get_current_user  # type: ignore
    async def _inner(user=Depends(get_current_user)):
        role = (user.get("role") or "").lower()
        if role not in {"owner", "admin", "superuser"}:
            raise HTTPException(403, "owner-only endpoint")
        return user
    return _inner


@router.get("/owner/all-recovery-requests")
async def owner_list_recoveries(user=Depends(_require_owner_dep())):
    cur = db.recovery_requests.find({}, {"_id": 0}).sort("created_at", -1).limit(200)
    items = [d async for d in cur]
    return {"items": items, "count": len(items)}


class RecoveryResolveIn(BaseModel):
    status: str = Field(..., description="resolved | rejected | in_progress")
    note: str = Field("", max_length=2000)


@router.post("/owner/recovery-requests/{rid}/resolve")
async def owner_resolve_recovery(
    rid: str, payload: RecoveryResolveIn, user=Depends(_require_owner_dep()),
):
    if payload.status not in {"resolved", "rejected", "in_progress"}:
        raise HTTPException(400, "invalid status")
    update = {"status": payload.status, "owner_note": payload.note.strip()}
    if payload.status in {"resolved", "rejected"}:
        update["resolved_at"] = time.time()
    r = await db.recovery_requests.update_one({"id": rid}, {"$set": update})
    return {"ok": True, "matched": r.matched_count}
