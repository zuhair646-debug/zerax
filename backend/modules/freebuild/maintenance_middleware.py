"""
Maintenance Mode Middleware
───────────────────────────
Reads `zenrex_maintenance` collection (one doc per section) and short-circuits
incoming requests to maintained sections with HTTP 503 + a friendly Arabic
JSON banner. The owner toggles sections via the Owner Engineer Portal.

Section→path-prefix map:
    images   → /api/images/*, /api/fal/*, /api/flux/*
    videos   → /api/videos/*, /api/sora/*, /api/cinema/*
    games    → /api/games/*, /api/game_runtime/*, /api/game_toolkit/*
    global   → ANY /api/* request (except this one + auth + admin/engineer)

To avoid hammering Mongo on every request, we cache the active list for 15s.
"""
from __future__ import annotations

import time
from typing import Dict, Any, List, Tuple
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


_SECTION_PREFIXES: Dict[str, Tuple[str, ...]] = {
    "images": ("/api/images", "/api/fal", "/api/flux"),
    "videos": ("/api/videos", "/api/sora", "/api/cinema", "/api/sora2"),
    "games": ("/api/games", "/api/game_runtime", "/api/game_toolkit"),
}

# Paths that must NEVER be blocked even during a global maintenance, so the
# owner can still access the engineer console + unblock the system.
_NEVER_BLOCK_PREFIXES: Tuple[str, ...] = (
    "/api/auth",
    "/api/freebuild-chat/owner/engineer",
    "/api/freebuild-chat/maintenance/active",
    "/api/admin",
    "/api/health",
)


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, db):
        super().__init__(app)
        self._db = db
        self._cache: List[Dict[str, Any]] = []
        self._cache_at: float = 0.0
        self._cache_ttl = 15.0

    async def _load_active(self) -> List[Dict[str, Any]]:
        now = time.time()
        if (now - self._cache_at) < self._cache_ttl and self._cache_at > 0:
            return self._cache
        items: List[Dict[str, Any]] = []
        try:
            async for m in self._db.zenrex_maintenance.find(
                {"active": True},
                {"_id": 0, "section": 1, "banner_ar": 1, "ends_at": 1, "started_at": 1},
            ):
                items.append(m)
        except Exception:
            pass
        self._cache = items
        self._cache_at = now
        return items

    def _match(self, path: str, active: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        for prefix in _NEVER_BLOCK_PREFIXES:
            if path.startswith(prefix):
                return None
        for m in active:
            sec = (m.get("section") or "").lower()
            if sec == "global":
                return m
            prefixes = _SECTION_PREFIXES.get(sec, ())
            for p in prefixes:
                if path.startswith(p):
                    return m
        return None

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)
        active = await self._load_active()
        if not active:
            return await call_next(request)
        hit = self._match(path, active)
        if not hit:
            return await call_next(request)
        return JSONResponse(
            status_code=503,
            content={
                "maintenance": True,
                "section": hit.get("section"),
                "banner_ar": hit.get("banner_ar")
                or "⚙️ هذا القسم في تحديث جزئي. باقي الموقع شغّال.",
                "ends_at": hit.get("ends_at"),
                "started_at": hit.get("started_at"),
            },
            headers={"Retry-After": "60"},
        )


def install_maintenance_middleware(app, db) -> None:
    """Idempotent installer — safe to call multiple times during reload."""
    if getattr(app.state, "_maintenance_middleware_installed", False):
        return
    app.add_middleware(MaintenanceModeMiddleware, db=db)
    app.state._maintenance_middleware_installed = True
