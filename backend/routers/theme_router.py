"""
Zerax Theme Router — Per-merchant theme customization
======================================================
Stores merchant theme overrides (colors / fonts / radius).
Theme is applied automatically to: admin.html (their dashboard),
app_mode_full.html (their storefront), driver_app.html (their drivers).

The default theme is the elegant DARK aesthetic; merchant can tweak.
The customer/driver UIs READ the merchant theme at load time
so each store looks unique without code changes.

Owner: Zerax Platform (Feb 2026)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from routers.store_router import merchant_user, db as _db

log = logging.getLogger("theme_router")
router = APIRouter(prefix="/api/theme", tags=["theme"])
db = _db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Default Zerax dark theme — used when merchant hasn't customized
DEFAULT_THEME: Dict[str, Any] = {
    "mode": "dark",
    "colors": {
        "bg":            "#0a0a14",
        "bg2":           "#0f0f1c",
        "surface":       "#14142b",
        "surface2":      "#1a1a2e",
        "border":        "#2d2d4a",
        "accent":        "#7c3aed",
        "accent2":       "#a855f7",
        "amber":         "#fbbf24",
        "success":       "#10b981",
        "danger":        "#ef4444",
        "text":          "#f1f5f9",
        "text_soft":     "#cbd5e1",
        "text_mute":     "#94a3b8",
    },
    "font_family":   "Tajawal",
    "radius_scale":  1.0,   # 1.0 = default; 0.5 = sharper, 1.5 = rounder
    "buttons_style": "gradient",  # gradient | solid | outline | pill
    "use_glass":     True,
    "logo_url":      "",
    "store_name":    "",
    "tagline":       "",
}


class ThemeIn(BaseModel):
    mode: Optional[str] = None
    colors: Optional[Dict[str, str]] = None
    font_family: Optional[str] = None
    radius_scale: Optional[float] = Field(default=None, ge=0.5, le=2.0)
    buttons_style: Optional[str] = None
    use_glass: Optional[bool] = None
    logo_url: Optional[str] = None
    store_name: Optional[str] = None
    tagline: Optional[str] = None


@router.get("/defaults")
async def get_defaults():
    """Public — returns the platform default theme."""
    return DEFAULT_THEME


@router.get("/merchant/me")
async def get_my_theme(u: dict = Depends(merchant_user)):
    """Returns the merchant's current theme (default if not customized)."""
    t = await db.merchant_themes.find_one({"merchant_id": u["user_id"]}, {"_id": 0})
    if not t:
        return {**DEFAULT_THEME, "merchant_id": u["user_id"], "is_default": True}
    return {**DEFAULT_THEME, **t, "is_default": False}


@router.get("/by-merchant/{merchant_id}")
async def get_theme_by_merchant(merchant_id: str):
    """Public — used by customer storefront + driver app to load merchant's theme."""
    t = await db.merchant_themes.find_one({"merchant_id": merchant_id}, {"_id": 0})
    if not t:
        return DEFAULT_THEME
    return {**DEFAULT_THEME, **t}


@router.put("/merchant/me")
async def update_my_theme(body: ThemeIn, u: dict = Depends(merchant_user)):
    """Merchant updates their theme. Only sent fields are overwritten."""
    update: Dict[str, Any] = {}
    for k in ("mode", "font_family", "radius_scale", "buttons_style", "use_glass", "logo_url", "store_name", "tagline"):
        v = getattr(body, k)
        if v is not None:
            update[k] = v
    if body.colors:
        # Merge with existing colors so partial updates work
        existing = await db.merchant_themes.find_one({"merchant_id": u["user_id"]}) or {}
        merged = {**DEFAULT_THEME["colors"], **(existing.get("colors") or {}), **body.colors}
        update["colors"] = merged
    update["updated_at"] = _now()
    await db.merchant_themes.update_one(
        {"merchant_id": u["user_id"]},
        {"$set": update, "$setOnInsert": {"merchant_id": u["user_id"], "created_at": _now()}},
        upsert=True,
    )
    return await db.merchant_themes.find_one({"merchant_id": u["user_id"]}, {"_id": 0})


@router.post("/merchant/reset")
async def reset_my_theme(u: dict = Depends(merchant_user)):
    """Reset to platform default."""
    await db.merchant_themes.delete_one({"merchant_id": u["user_id"]})
    return {"ok": True, "theme": DEFAULT_THEME}


@router.get("/health")
async def health():
    return {
        "ok": True,
        "total_customized": await db.merchant_themes.count_documents({}),
    }
