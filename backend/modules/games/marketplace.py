"""
🛒 LoRA Asset Marketplace
═══════════════════════════════════════════════════════════════════════
Every trained Flux LoRA (see lora_training.py) can optionally be
published to the marketplace. Other Zerax creators can browse and
install LoRAs into their own projects, instantly inheriting a proven
art style.

Collections:
  `lora_marketplace`  — published LoRAs (public)
    {
      id, owner_id, owner_name,
      project_id, project_title,
      lora_url, trigger_word,
      title, description, tags: [...],
      preview_images: [url, url, url],   # 3 sample renders
      price: 0 | INT (Zerax points),
      installs: INT, rating_avg: FLOAT, rating_count: INT,
      published_at, updated_at,
      is_active: bool
    }

  `lora_installs`     — per-user install history
    { id, user_id, marketplace_id, installed_at, used_in_project: id }
"""
from __future__ import annotations
import uuid, logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


async def publish_lora(
    db,
    user: Dict[str, Any],
    project_id: str,
    title: str,
    description: str = "",
    tags: Optional[List[str]] = None,
    price: int = 0,
) -> Dict[str, Any]:
    """Publish a project's trained LoRA to the marketplace."""
    proj = await db.game_projects.find_one(
        {"id": project_id, "user_id": user["user_id"]},
        {"lora": 1, "assets.images": 1, "title": 1},
    )
    if not proj:
        raise ValueError("Project not found")
    lora = (proj.get("lora") or {})
    if lora.get("status") != "ready" or not lora.get("lora_url"):
        raise ValueError("Project has no trained LoRA. Train it first.")

    # Grab 3 approved images as preview
    imgs = ((proj.get("assets") or {}).get("images") or [])
    approved = [a for a in imgs if a.get("approved") and (a.get("cdn_url") or a.get("image_url"))][:3]
    previews = [a.get("cdn_url") or a.get("image_url") for a in approved]

    entry = {
        "id": str(uuid.uuid4()),
        "owner_id": user["user_id"],
        "owner_name": user.get("email", "anonymous").split("@")[0],
        "project_id": project_id,
        "project_title": proj.get("title", ""),
        "lora_url": lora["lora_url"],
        "trigger_word": lora.get("trigger_word", ""),
        "title": (title or proj.get("title") or "Untitled Style"),
        "description": description or f"Trained on {lora.get('num_images', 'multiple')} approved images.",
        "tags": tags or [],
        "preview_images": previews,
        "price": int(price or 0),
        "installs": 0,
        "rating_avg": 0.0,
        "rating_count": 0,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
    }
    await db.lora_marketplace.insert_one(entry)
    entry.pop("_id", None)  # avoid ObjectId leak
    return entry


async def list_marketplace(
    db,
    search: str = "",
    tags: Optional[List[str]] = None,
    sort: str = "popular",
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    q: Dict[str, Any] = {"is_active": True}
    if search:
        q["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}},
        ]
    if tags:
        q["tags"] = {"$in": tags}

    sort_map = {
        "popular": [("installs", -1), ("published_at", -1)],
        "new":     [("published_at", -1)],
        "rated":   [("rating_avg", -1), ("rating_count", -1)],
    }
    sort_spec = sort_map.get(sort, sort_map["popular"])

    skip = max(0, (page - 1) * page_size)
    cursor = db.lora_marketplace.find(q).sort(sort_spec).skip(skip).limit(page_size)
    items = []
    async for d in cursor:
        d.pop("_id", None)
        items.append(d)
    total = await db.lora_marketplace.count_documents(q)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def install_lora(
    db,
    user: Dict[str, Any],
    marketplace_id: str,
    target_project_id: str,
) -> Dict[str, Any]:
    """Copy a marketplace LoRA into the user's project so subsequent
    image gens use it. Free LoRAs install instantly; paid ones need
    a points deduction (handled by a separate billing flow)."""
    entry = await db.lora_marketplace.find_one({"id": marketplace_id, "is_active": True})
    if not entry:
        raise ValueError("LoRA not found")

    proj = await db.game_projects.find_one(
        {"id": target_project_id, "user_id": user["user_id"]},
        {"id": 1, "title": 1, "lora": 1},
    )
    if not proj:
        raise ValueError("Target project not found")

    # Copy LoRA info onto the project
    await db.game_projects.update_one(
        {"id": target_project_id},
        {"$set": {
            "lora.status": "ready",
            "lora.lora_url": entry["lora_url"],
            "lora.trigger_word": entry["trigger_word"],
            "lora.installed_from": marketplace_id,
            "lora.installed_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    # Track the install
    await db.lora_marketplace.update_one({"id": marketplace_id}, {"$inc": {"installs": 1}})
    await db.lora_installs.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "marketplace_id": marketplace_id,
        "used_in_project": target_project_id,
        "installed_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "lora_url": entry["lora_url"], "trigger_word": entry["trigger_word"]}


async def rate_lora(db, user: Dict[str, Any], marketplace_id: str, rating: int) -> Dict[str, Any]:
    rating = max(1, min(5, int(rating)))
    entry = await db.lora_marketplace.find_one({"id": marketplace_id})
    if not entry:
        raise ValueError("LoRA not found")
    n = (entry.get("rating_count") or 0) + 1
    avg_new = ((entry.get("rating_avg") or 0.0) * (n - 1) + rating) / n
    await db.lora_marketplace.update_one(
        {"id": marketplace_id},
        {"$set": {"rating_avg": round(avg_new, 2), "rating_count": n}},
    )
    return {"ok": True, "rating_avg": round(avg_new, 2), "rating_count": n}
