"""
💰 Games Billing Module
─────────────────────
Project size calculation + tier limits + auto-cleanup for expired free projects.

Tier definitions:
   free    → 100 MB · 14-day retention · auto-delete after expiry
   starter → 5 GB · 1-year retention   · $9/month
   studio  → 50 GB · permanent          · $29/month
   aaa     → 500 GB · CDN + backup       · $99/month
"""
from __future__ import annotations
import os
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

UPLOAD_ROOT = "/app/backend/uploads/games"

TIERS = {
    "free":    {"label": "مجاني",  "storage_mb": 100,     "retention_days": 14,    "price_usd": 0,   "price_label": "$0"},
    "starter": {"label": "منتج",  "storage_mb": 5_120,    "retention_days": 365,   "price_usd": 9,   "price_label": "$9/شهر"},
    "studio":  {"label": "استوديو", "storage_mb": 51_200,  "retention_days": -1,    "price_usd": 29,  "price_label": "$29/شهر"},
    "aaa":     {"label": "AAA",     "storage_mb": 512_000, "retention_days": -1,    "price_usd": 99,  "price_label": "$99/شهر"},
}


def get_project_dir_size_bytes(project_id: str) -> int:
    """Walk the project's upload dir and sum file sizes."""
    base = f"{UPLOAD_ROOT}/{project_id}"
    if not os.path.isdir(base):
        return 0
    total = 0
    for dirpath, _, filenames in os.walk(base):
        for fn in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, fn))
            except OSError:
                pass
    return total


def get_project_storage_info(project: Dict[str, Any]) -> Dict[str, Any]:
    """Return: tier, size_bytes, size_mb, limit_mb, percent_used, retention_days, expires_at."""
    tier_id = (project.get("billing_tier") or "free").lower()
    tier = TIERS.get(tier_id, TIERS["free"])
    size_bytes = get_project_dir_size_bytes(project["id"])
    size_mb = round(size_bytes / 1_048_576, 2)
    limit_mb = tier["storage_mb"]
    percent_used = round((size_mb / limit_mb) * 100, 1) if limit_mb else 0
    over_quota = size_mb > limit_mb

    expires_at = None
    retention_days = tier["retention_days"]
    if retention_days > 0:
        try:
            created = project.get("created_at", "")
            ts = datetime.fromisoformat(created.replace("Z", "+00:00")) if isinstance(created, str) else None
            if ts:
                exp = ts + timedelta(days=retention_days)
                expires_at = exp.isoformat()
        except Exception:
            pass

    return {
        "tier": tier_id,
        "tier_label": tier["label"],
        "size_bytes": size_bytes,
        "size_mb": size_mb,
        "limit_mb": limit_mb,
        "percent_used": percent_used,
        "over_quota": over_quota,
        "retention_days": retention_days,
        "expires_at": expires_at,
        "price_label": tier["price_label"],
    }


def is_project_expired(project: Dict[str, Any]) -> bool:
    """Return True if the project's free retention period has lapsed."""
    info = get_project_storage_info(project)
    if info["retention_days"] < 0 or not info["expires_at"]:
        return False
    try:
        exp = datetime.fromisoformat(info["expires_at"])
        return datetime.now(timezone.utc) > exp
    except Exception:
        return False


async def cleanup_expired_projects(db) -> Dict[str, int]:
    """Run nightly: delete files + DB record for expired free-tier projects."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=TIERS["free"]["retention_days"])
    cutoff_iso = cutoff.isoformat()
    query = {
        "$and": [
            {"$or": [{"billing_tier": "free"}, {"billing_tier": {"$exists": False}}]},
            {"created_at": {"$lt": cutoff_iso}},
        ]
    }
    deleted_files = 0
    deleted_projects = 0
    async for proj in db.game_projects.find(query):
        try:
            import shutil
            base = f"{UPLOAD_ROOT}/{proj['id']}"
            if os.path.isdir(base):
                # count files before delete
                for _, _, fns in os.walk(base):
                    deleted_files += len(fns)
                shutil.rmtree(base, ignore_errors=True)
            await db.game_projects.delete_one({"id": proj["id"]})
            deleted_projects += 1
            logger.info(f"[billing] auto-deleted expired free project {proj['id']}")
        except Exception as e:
            logger.warning(f"[billing] failed to clean project {proj.get('id')}: {e}")
    return {"deleted_projects": deleted_projects, "deleted_files": deleted_files}
