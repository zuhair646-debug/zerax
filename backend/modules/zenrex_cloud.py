"""Cloud-hosted Zenrex Farm.

We mount the zenrex_farm.py FastAPI app (designed to run on the user's
PC) directly under `/api/zenrex` of the main backend so the user can
access the *entire* dashboard from his browser without installing
anything locally. A small middleware rewrites the absolute `/api/...`
URLs the dashboard's JavaScript uses so they end up under
`/api/zenrex/api/...` and reach the mounted sub-app.

Set `ZENREX_NO_BUILDWORKER=1` (and similar) so heavyweight workers do
NOT auto-start on the cloud; the user starts them from the dashboard.
"""

from __future__ import annotations

import os
import sys
import asyncio
import logging
from typing import Iterable

# Make the desktop_agent package importable. We probe several locations
# because the layout differs between dev (preview container) and prod
# (Docker compose on the Hetzner VPS).
for candidate in (
    "/app/desktop_agent",          # dev / preview
    "/desktop_agent",              # prod docker mount
    os.path.join(os.path.dirname(__file__), "..", "..", "desktop_agent"),
):
    cand = os.path.abspath(candidate)
    if os.path.isfile(os.path.join(cand, "zenrex_farm.py")):
        if cand not in sys.path:
            sys.path.insert(0, cand)
        break

# Flag this process as the cloud host so endpoints can short-circuit work
# that only makes sense when running on the user's PC (self-update, beacon).
os.environ.setdefault("ZENREX_CLOUD", "1")
os.environ.setdefault("ZENREX_NO_BUILDWORKER", "1")
os.environ.setdefault("ZENREX_NO_BEACON", "1")

logger = logging.getLogger("zenrex_cloud")

# Use a cloud-writable data dir so SQLite doesn't crash inside the container
os.environ.setdefault("ZENREX_HOME", "/app/.zenrex-cloud")
os.makedirs(os.environ["ZENREX_HOME"], exist_ok=True)

try:
    import zenrex_farm  # noqa: E402
    zenrex_app = zenrex_farm.app
    # Mounted sub-apps don't always run their own startup events, so
    # initialise the DB schema explicitly right now.
    try:
        zenrex_farm.init_db()
        logger.info("[zenrex-cloud] init_db() done")
    except Exception as _idb:
        logger.warning(f"[zenrex-cloud] init_db failed: {_idb}")

    # One-time live HTTP probe of all Travian Legends URLs so the user
    # sees real, currently-responding servers (not just static seed).
    # Runs in a background thread; no blocking of import.
    def _initial_probe():
        try:
            worlds = zenrex_farm.probe_live_worlds()
            saved = zenrex_farm._save_worlds(worlds)
            logger.info(f"[zenrex-cloud] initial probe: {len(worlds)} live worlds, {saved} saved")
        except Exception as e:
            logger.warning(f"[zenrex-cloud] initial probe failed: {e}")

    import threading
    threading.Thread(target=_initial_probe, daemon=True).start()

    logger.info(f"[zenrex-cloud] loaded zenrex_farm v{zenrex_farm.APP_VERSION}")
except Exception as exc:  # pragma: no cover
    logger.exception(f"[zenrex-cloud] failed to import zenrex_farm: {exc}")
    zenrex_app = None  # type: ignore[assignment]


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Mount path used in the main backend's server.py
MOUNT_PREFIX = "/api/zenrex"


class _RewriteAbsoluteUrlsMiddleware(BaseHTTPMiddleware):
    """Rewrite `/api/...` → `/api/zenrex/api/...` inside HTML/JS bodies.

    The dashboard's JavaScript calls `fetch('/api/villages')` etc. After
    mounting under `/api/zenrex/`, these need to become
    `/api/zenrex/api/villages`. Doing it here once keeps the original
    zenrex_farm.py untouched.
    """

    REWRITES: tuple[tuple[bytes, bytes], ...] = (
        # The dashboard's JS uses these exact prefixes to call its own API.
        # We keep the rewrites STRICTLY anchored to a function name so we
        # never double-rewrite (i.e. we never see `fetch(...)` inside our
        # own rewritten output).
        (b"fetch('/api/",        b"fetch('" + MOUNT_PREFIX.encode() + b"/api/"),
        (b'fetch("/api/',        b'fetch("' + MOUNT_PREFIX.encode() + b'/api/'),
        (b"fetch(`/api/",        b"fetch(`" + MOUNT_PREFIX.encode() + b"/api/"),
        (b"axios.get('/api/",    b"axios.get('" + MOUNT_PREFIX.encode() + b"/api/"),
        (b"axios.post('/api/",   b"axios.post('" + MOUNT_PREFIX.encode() + b"/api/"),
        # Anchor tags + form actions
        (b" href='/api/",        b" href='" + MOUNT_PREFIX.encode() + b"/api/"),
        (b' href="/api/',        b' href="' + MOUNT_PREFIX.encode() + b'/api/'),
        (b" action='/api/",      b" action='" + MOUNT_PREFIX.encode() + b"/api/"),
        (b' action="/api/',      b' action="' + MOUNT_PREFIX.encode() + b'/api/'),
        # `${...}/api/...` template fragments often used to compose URLs
        (b"= '/api/",            b"= '" + MOUNT_PREFIX.encode() + b"/api/"),
        (b'= "/api/',            b'= "' + MOUNT_PREFIX.encode() + b'/api/'),
        (b"= `/api/",            b"= `" + MOUNT_PREFIX.encode() + b"/api/"),
    )

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        ct = response.headers.get("content-type", "").lower()
        if not (ct.startswith("text/html") or
                "javascript" in ct or
                ct.startswith("text/css")):
            return response

        # Buffer the streamed body
        chunks: list[bytes] = []
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            chunks.append(chunk)
        body = b"".join(chunks)

        for old, new in self.REWRITES:
            body = body.replace(old, new)

        # Drop hop-by-hop / mismatched headers
        new_headers = {
            k: v for k, v in response.headers.items()
            if k.lower() not in {"content-length", "content-encoding"}
        }
        return Response(
            content=body,
            status_code=response.status_code,
            headers=new_headers,
            media_type=response.media_type,
        )


if zenrex_app is not None:
    zenrex_app.add_middleware(_RewriteAbsoluteUrlsMiddleware)


def mount(main_app) -> None:
    """Mount the Zenrex Farm dashboard onto the main FastAPI app."""
    if zenrex_app is None:
        logger.warning("[zenrex-cloud] zenrex_app is None; mount skipped")
        return
    main_app.mount(MOUNT_PREFIX, zenrex_app)
    logger.info(f"[zenrex-cloud] mounted at {MOUNT_PREFIX}/")
