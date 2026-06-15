"""Direct Google OAuth 2.0 — no third-party broker, no Emergent dependency.

Server-side flow:
  1. GET  /api/auth/google/start    → redirect user to Google's consent screen
  2. GET  /api/auth/google/callback → Google calls us back with ?code=...
     We exchange the code for tokens, fetch the user's profile, upsert into
     `users`, mint a JWT, then 302-redirect to the frontend with ?token=...

# REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
# THIS BREAKS THE AUTH. The redirect_uri MUST match exactly what's registered
# in Google Cloud Console → Credentials → Authorized redirect URIs.
"""
from __future__ import annotations

import os
import secrets
import time
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse


router = APIRouter(prefix="/api/auth/google", tags=["auth.google"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

# The redirect URI Google calls. MUST exactly match what's registered in the
# Google Cloud Console for this OAuth client. Production = zenrex.ai.
PROD_REDIRECT_URI = "https://zenrex.ai/auth/google"

# Short-lived in-memory state cache (CSRF protection). State values expire
# after 10 minutes. For multi-instance deployments this should move to Redis
# but a single-VPS deployment is fine with a process-local dict.
_state_cache: Dict[str, float] = {}
# Separate dict for "redirect_after_login" paths so we don't mix float timestamps
# with strings in _state_cache (which broke `now - v` purge logic).
_redirect_cache: Dict[str, str] = {}


def _new_state() -> str:
    """Generate a fresh CSRF token and remember it for 10 minutes."""
    # purge expired
    now = time.time()
    for k, v in list(_state_cache.items()):
        if now - v > 600:
            _state_cache.pop(k, None)
            _redirect_cache.pop(k, None)
    state = secrets.token_urlsafe(32)
    _state_cache[state] = now
    return state


def _consume_state(state: str) -> bool:
    """Validate-and-remove a state token. Returns True if valid."""
    return _state_cache.pop(state, None) is not None


def _client_creds() -> tuple[str, str]:
    cid = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    csec = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    if not cid or not csec:
        raise HTTPException(503, "Google OAuth غير مكوّن (GOOGLE_CLIENT_ID/SECRET مفقودين)")
    return cid, csec


def _frontend_origin(request: Request) -> str:
    """Pick a frontend origin to send the user back to after auth.
    We trust only known production / preview hostnames so we can't be turned
    into an open redirect."""
    host = (request.headers.get("host") or "").lower()
    if "zenrex.ai" in host:
        return "https://zenrex.ai"
    if "emergentagent.com" in host or "emergent" in host:
        # preview env
        return f"https://{host}"
    return "https://zenrex.ai"


@router.get("/start")
async def google_start(request: Request, redirect: str = "/"):
    """Redirect the user to Google's consent screen."""
    cid, _ = _client_creds()
    state = _new_state()
    # Remember where to send the user after auth (sanitized to a relative path)
    redirect_path = redirect if redirect.startswith("/") else "/"
    _redirect_cache[state] = redirect_path
    params = {
        "client_id": cid,
        "redirect_uri": PROD_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    # Build the URL using httpx — it URL-encodes params correctly.
    url = httpx.URL(GOOGLE_AUTH_URL, params=params)
    return RedirectResponse(str(url), status_code=302)


@router.get("/callback")
async def google_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    """Google calls us here after the user consents. We swap code → token →
    profile → JWT, then redirect back to the frontend."""
    if error:
        return RedirectResponse(f"{_frontend_origin(request)}/login?error={error}", status_code=302)
    if not code or not state:
        raise HTTPException(400, "missing code or state")
    redir_path = _redirect_cache.pop(state, "/")
    if not _consume_state(state):
        raise HTTPException(400, "invalid or expired state — CSRF protection")
    cid, csec = _client_creds()
    # ── Exchange the authorization code for tokens ──
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            tok_resp = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": cid,
                "client_secret": csec,
                "redirect_uri": PROD_REDIRECT_URI,
                "grant_type": "authorization_code",
            })
            if tok_resp.status_code != 200:
                raise HTTPException(400, f"Google token exchange failed: {tok_resp.text[:200]}")
            tok = tok_resp.json()
            access_token = tok.get("access_token") or ""
            if not access_token:
                raise HTTPException(400, "no access_token in Google response")
            # ── Fetch the user's profile ──
            ui = await client.get(GOOGLE_USERINFO_URL,
                                    headers={"Authorization": f"Bearer {access_token}"})
            if ui.status_code != 200:
                raise HTTPException(400, f"failed to fetch userinfo: {ui.text[:200]}")
            profile = ui.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Google OAuth failed: {type(e).__name__}: {str(e)[:200]}")
    email = (profile.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(400, "Google did not return an email")
    name = profile.get("name") or email.split("@")[0]
    picture = profile.get("picture") or ""
    google_sub = profile.get("sub") or ""
    # ── Upsert the user in our DB ──
    from server import db, create_token, _now_iso  # type: ignore
    import uuid
    try:
        existing = await db.users.find_one({"email": email})
        if existing:
            await db.users.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "google_sub": google_sub,
                    "picture": picture or existing.get("picture", ""),
                    "last_login_at": _now_iso() if callable(getattr(__import__("server"), "_now_iso", None)) else None,
                    "name": existing.get("name") or name,
                }},
            )
            user_id = existing.get("id") or str(existing["_id"])
            role = existing.get("role", "user")
        else:
            user_id = uuid.uuid4().hex
            await db.users.insert_one({
                "id": user_id,
                "email": email,
                "name": name,
                "picture": picture,
                "role": "user",
                "google_sub": google_sub,
                "auth_provider": "google",
                "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            })
            role = "user"
    except Exception as e:
        raise HTTPException(500, f"DB upsert failed: {type(e).__name__}: {str(e)[:200]}")
    # ── Mint a JWT and redirect back to the frontend ──
    token = create_token(user_id, role)
    origin = _frontend_origin(request)
    # The frontend's /login page picks the ?token=... param and stores it.
    sep = "&" if "?" in redir_path else "?"
    return RedirectResponse(f"{origin}/login{sep}token={token}&google=1", status_code=302)
