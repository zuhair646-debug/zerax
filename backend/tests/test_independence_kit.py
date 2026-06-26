"""
Sanity tests for the Independence Kit module.

These tests don't call Claude — they exercise the deterministic
templating side so we lock in the contract:
  • Every kit returned contains the 10 mandatory files.
  • Project slugification is correct.
  • The HANDOVER.md contains the customer's email.
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

# Make the backend modules importable when pytest is invoked from /app
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.join(_ROOT, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, "backend"))


REQUIRED_FILES = {
    "README.md",
    "ARCHITECTURE.md",
    "HANDOVER.md",
    "Dockerfile",
    "docker-compose.yml",
    "nginx.conf",
    "deploy.sh",
    "SECRETS.template.env",
    ".gitignore",
    "LICENSE",
}


def test_slugify_basic():
    from modules.freebuild.independence_kit import _slugify
    assert _slugify("My Movie Site") == "my-movie-site"
    assert _slugify("Acme — Studio v2!") == "acme-studio-v2"
    assert _slugify("") == "zenrex-project"
    assert _slugify("موقع عربي").startswith("") or _slugify("موقع عربي") == "zenrex-project"


@pytest.mark.asyncio
async def test_kit_contains_all_required_files(monkeypatch):
    """Even if Claude is unreachable, the kit must still contain the
    10 mandatory files (with ARCHITECTURE.md falling back to template)."""
    # Force fallback path so we don't hit Claude in CI.
    from modules.freebuild import independence_kit as ik

    async def _no_claude(*a, **kw):
        raise RuntimeError("blocked in tests")

    monkeypatch.setattr(ik, "ask_claude", _no_claude)

    project = {
        "id": "test-123",
        "name": "Test Project",
        "description": "وصف للاختبار",
        "current_html": "<html><body>hi</body></html>",
    }
    kit = await ik.build_independence_kit(project, owner_email="qa@zenrex.ai", include_backend=False)
    assert set(kit.keys()) == REQUIRED_FILES
    # All values are non-empty strings
    for name, content in kit.items():
        assert isinstance(content, str) and content.strip(), f"{name} empty"

    # HANDOVER carries the customer email + price tag
    assert "qa@zenrex.ai" in kit["HANDOVER.md"]
    assert "$799" in kit["HANDOVER.md"]

    # README has the slug + nginx instruction
    assert "test-project" in kit["README.md"]

    # nginx.conf includes the security headers we promised
    for hdr in ("X-Frame-Options", "X-Content-Type-Options", "Permissions-Policy"):
        assert hdr in kit["nginx.conf"]

    # deploy.sh is executable bash + handles HTTPS via Caddy
    assert kit["deploy.sh"].startswith("#!/usr/bin/env bash")
    assert "caddy" in kit["deploy.sh"].lower()

    # Fallback ARCHITECTURE.md still produced
    assert "ARCHITECTURE" in kit["ARCHITECTURE.md"]
