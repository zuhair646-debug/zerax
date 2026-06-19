"""Validate AI Usage Meter endpoints + quota logic."""

import os
import httpx
import pytest

API = os.environ.get("PYTEST_API_URL") or os.environ.get(
    "REACT_APP_BACKEND_URL", "https://ai-cinematic-hub-2.preview.emergentagent.com"
)
USER = {"email": "owner@zerax.com", "password": "owner123"}


@pytest.fixture(scope="module")
def token():
    r = httpx.post(f"{API}/api/auth/login", json=USER, timeout=45)
    r.raise_for_status()
    return r.json()["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_usage_me_shape(token):
    r = httpx.get(f"{API}/api/usage/me", headers=auth(token), timeout=45)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "today" in body
    assert "tokens_in" in body["today"]
    assert "tokens_out" in body["today"]
    assert "calls" in body["today"]
    assert "cost_usd" in body["today"]
    assert "quota" in body
    assert "allowed" in body["quota"]


def test_usage_admin_totals(token):
    r = httpx.get(f"{API}/api/usage/admin/totals", headers=auth(token), timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "last_24h" in body
    assert "last_30d" in body
    for k in ("tokens", "cost_usd", "calls"):
        assert k in body["last_24h"]
        assert k in body["last_30d"]


def test_usage_admin_top_spenders(token):
    r = httpx.get(f"{API}/api/usage/admin/top-spenders?limit=5", headers=auth(token), timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    assert body["since_days"] == 30


def test_usage_admin_by_project(token):
    r = httpx.get(f"{API}/api/usage/admin/by-project?limit=5", headers=auth(token), timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["items"], list)


def test_section_briefs_loads():
    """Section briefs module must import without errors and cover the 8 main sections."""
    import sys
    sys.path.insert(0, "/app/backend")
    from modules.ai_core.section_briefs import brief_for_mode, get_section_brief, SECTION_BRIEFS
    assert "websites" in SECTION_BRIEFS
    assert "apps" in SECTION_BRIEFS
    assert "site_to_app" in SECTION_BRIEFS
    assert "videos" in SECTION_BRIEFS
    assert "games" in SECTION_BRIEFS
    # brief_for_mode covers default
    assert len(brief_for_mode(None)) > 1000  # universal rules + website brief
    assert "زنركس AI" in brief_for_mode("app")
    assert "PWA" in brief_for_mode("app")
