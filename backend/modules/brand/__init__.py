"""Brand Manager — centralised name/logo/colour for the whole platform.

GET  /api/brand              public: current brand JSON
PUT  /api/brand              owner-only: update brand fields
GET  /api/brand/manifest.json public: dynamic PWA manifest (auto-updated)
GET  /api/brand/version      public: monotonically-increasing version int

Whenever a field is updated, `version` is incremented so any installed PWA
service worker can detect the change and prompt for re-install.
"""

from __future__ import annotations

import os
import time
import json
import logging
from typing import Optional, Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger("brand")
router = APIRouter(prefix="/api/brand", tags=["brand"])

_MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
_DB_NAME   = os.environ.get("DB_NAME", "test_database")
_client = AsyncIOMotorClient(_MONGO_URL)
_db = _client[_DB_NAME]
_col = _db["brand_settings"]
_DOC_ID = "current"

DEFAULT_BRAND = {
    "_id":          _DOC_ID,
    "name":         "Zenrex",
    "name_long":    "Zenrex — منصة الإبداع بالذكاء الاصطناعي",
    "tagline_ar":   "اصنع، انشر، أبدع — بالذكاء الاصطناعي",
    "tagline_en":   "Build, publish, create — with AI",
    "logo_url":     "/logo512.png",
    "favicon_url":  "/favicon.ico",
    "icon_192":     "/logo192.png",
    "icon_512":     "/logo512.png",
    "theme_color":  "#08080f",
    "bg_color":     "#08080f",
    "primary":      "#f59e0b",
    "version":      1,
    "updated_at":   int(time.time()),
}


class BrandUpdate(BaseModel):
    name:        Optional[str] = None
    name_long:   Optional[str] = None
    tagline_ar:  Optional[str] = None
    tagline_en:  Optional[str] = None
    logo_url:    Optional[str] = None
    favicon_url: Optional[str] = None
    icon_192:    Optional[str] = None
    icon_512:    Optional[str] = None
    theme_color: Optional[str] = None
    bg_color:    Optional[str] = None
    primary:     Optional[str] = None


async def _get() -> dict[str, Any]:
    doc = await _col.find_one({"_id": _DOC_ID})
    if not doc:
        await _col.insert_one(DEFAULT_BRAND)
        return dict(DEFAULT_BRAND)
    return doc


def _is_owner(req: Request) -> bool:
    """Best-effort owner check via the existing auth header.

    The platform already populates `request.state.user` for authenticated
    requests; an owner has `role == 'owner'` or `is_owner == True`.
    """
    user = getattr(req.state, "user", None) or {}
    return bool(user.get("is_owner") or user.get("role") == "owner")


@router.get("")
async def get_brand():
    doc = await _get()
    doc.pop("_id", None)
    return {"ok": True, "brand": doc}


@router.get("/version")
async def get_version():
    doc = await _get()
    return {"version": int(doc.get("version", 1)),
            "updated_at": int(doc.get("updated_at", 0))}


@router.put("")
async def update_brand(payload: BrandUpdate, request: Request):
    if not _is_owner(request):
        raise HTTPException(status_code=403, detail="owner_only")
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="no_fields")
    updates["version"] = int((await _get()).get("version", 1)) + 1
    updates["updated_at"] = int(time.time())
    await _col.update_one({"_id": _DOC_ID}, {"$set": updates}, upsert=True)
    new_doc = await _get()
    new_doc.pop("_id", None)
    logger.info(f"[brand] updated: keys={list(updates.keys())} v={new_doc['version']}")
    return {"ok": True, "brand": new_doc}


@router.get("/manifest.json")
async def dynamic_manifest():
    """Live PWA manifest — always reflects the latest brand."""
    b = await _get()
    body = {
        "name":        b.get("name_long") or b.get("name", "Zenrex"),
        "short_name":  b.get("name", "Zenrex"),
        "description": b.get("tagline_ar") or b.get("tagline_en") or "",
        "start_url":   "/",
        "display":     "standalone",
        "orientation": "portrait-primary",
        "theme_color": b.get("theme_color", "#08080f"),
        "background_color": b.get("bg_color", "#08080f"),
        "lang":        "ar",
        "dir":         "rtl",
        "icons": [
            {"src": b.get("icon_192", "/logo192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": b.get("icon_512", "/logo512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
        "version": str(b.get("version", 1)),
    }
    return Response(content=json.dumps(body, ensure_ascii=False),
                    media_type="application/manifest+json",
                    headers={"Cache-Control": "public, max-age=60"})
