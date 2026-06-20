"""
Credits Guard Middleware — global safety net.

Intercepts every POST request to AI-heavy endpoints (chat, generate, message,
producer-chat, agent-chat…) and returns HTTP 402 Payment Required with a
JSON body if the authenticated user has 0 credits.

This is defense-in-depth on top of per-endpoint credit deduction — even if a
route forgets to call `charge_user()`, the user still cannot consume AI calls
without credits.

Owner / admin / super_admin roles bypass the check.
"""
from __future__ import annotations

import os
import logging
import re
from typing import Optional

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

log = logging.getLogger(__name__)

# Routes that consume AI/LLM resources — match by substring on the URL path.
# Order matters only marginally; first match wins (we just need any to match).
_PROTECTED_PATTERNS = re.compile(
    r"/api/(?:"
    r"freebuild/project/[^/]+/(?:chat|agent-chat|agent-chat-stream)"
    r"|freebuild-chat/"
    r"|freebuild-v2/chat"
    r"|ai-core/chat"
    r"|ai/chat"
    r"|companion/(?:chat|voice-chat)"
    r"|avatar/chat"
    r"|merchant/avatar/[^/]+/chat"
    r"|autocoder/chat"
    r"|mobile-app-builder/chat"
    r"|video-studio/(?:chat|production/producer-chat)"
    r"|app-studio/producer-chat"
    r"|agent/chat"
    r"|games/project/[^/]+/chat"
    r"|generate/(?:image|video)"
    r")"
)

_BYPASS_ROLES = {"owner", "admin", "super_admin"}


def _extract_user_id(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        secret = os.environ.get("JWT_SECRET") or os.environ.get("SECRET_KEY") or "zenrex-secret"
        for algo in ("HS256", "HS512"):
            try:
                payload = jwt.decode(token, secret, algorithms=[algo])
                return payload.get("user_id") or payload.get("sub")
            except Exception:
                continue
        # Last-resort: try unverified decode to extract user_id (read-only check)
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload.get("user_id") or payload.get("sub")
    except Exception:
        return None


class CreditsGuardMiddleware(BaseHTTPMiddleware):
    """Block AI requests when the user has zero credits."""

    def __init__(self, app, db_getter):
        super().__init__(app)
        # db_getter is a callable returning the motor DB — lazy so we don't
        # import the connection at module load time.
        self._db_getter = db_getter

    async def dispatch(self, request: Request, call_next):
        # Only inspect mutating requests that hit AI endpoints
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)
        if not _PROTECTED_PATTERNS.search(request.url.path):
            return await call_next(request)

        user_id = _extract_user_id(request)
        if not user_id:
            # Unauthenticated — let the route's own auth deal with it
            return await call_next(request)

        try:
            db = self._db_getter()
            user = await db.users.find_one(
                {"id": user_id},
                {"_id": 0, "credits": 1, "role": 1, "is_owner": 1},
            )
        except Exception as e:
            log.warning(f"[CreditsGuard] DB lookup failed: {e}")
            return await call_next(request)

        if not user:
            return await call_next(request)

        role = (user.get("role") or "").lower()
        if role in _BYPASS_ROLES or user.get("is_owner"):
            return await call_next(request)

        balance = int(user.get("credits") or 0)
        if balance > 0:
            return await call_next(request)

        # No credits → block with friendly 402
        return JSONResponse(
            status_code=402,
            content={
                "ok": False,
                "blocked": True,
                "code": "NO_CREDITS",
                "credits": 0,
                "pricing_url": "/pricing",
                "message": (
                    "رصيد النقاط انتهى. اشحن باقة جديدة لمواصلة الاستخدام — "
                    "كل النقاط تُضاف فوراً بعد الدفع."
                ),
                "message_en": "Out of credits. Recharge to continue.",
            },
        )
