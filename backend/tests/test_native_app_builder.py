"""
Backend tests for the Native App Builder flow.

Covers:
  - Auth (login owner@zerax.com)
  - POST /api/freebuild-chat/project with mode='app' + platform in {ios, android, both}
  - GET /api/freebuild-chat/project/{id} returns mode='app', platform, and
    platform-aware greeting message in messages array
  - Backwards compat: website-mode project still works without phone-frame metadata
  - Invalid platform falls back to 'both' (per server logic)
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-cinematic-hub-2.preview.emergentagent.com").rstrip("/")
EMAIL = "owner@zerax.com"
PASSWORD = "owner123"


# --------- fixtures ---------

@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth_token(api_client):
    r = api_client.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"Login failed ({r.status_code}): {r.text[:200]}")
    data = r.json()
    token = data.get("token") or data.get("access_token")
    if not token:
        pytest.skip(f"No token in login response: {data}")
    return token


@pytest.fixture(scope="module")
def authed(api_client, auth_token):
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


# --------- helpers ---------

def _create_app_project(client, platform, name_suffix):
    payload = {
        "name": f"TEST_native_{name_suffix}",
        "description": "automated native app builder test",
        "mode": "app",
        "platform": platform,
    }
    r = client.post(f"{BASE_URL}/api/freebuild-chat/project", json=payload)
    return r


def _delete_project(client, pid):
    try:
        client.delete(f"{BASE_URL}/api/freebuild-chat/project/{pid}")
    except Exception:
        pass


# --------- tests ---------

class TestAppProjectCreation:
    """Create + verify persistence for each platform variant."""

    @pytest.mark.parametrize("platform,label_terms", [
        ("ios", ["iPhone", "iOS"]),
        ("android", ["Android"]),
        ("both", ["iPhone", "Android", "Universal", "Both", "الاثنين"]),
    ])
    def test_create_app_project_platform_persists_and_greeting_mentions_platform(self, authed, platform, label_terms):
        # CREATE
        r = _create_app_project(authed, platform, platform)
        assert r.status_code == 200, f"create failed for platform={platform}: {r.status_code} {r.text[:300]}"
        data = r.json()
        assert data.get("mode") == "app", f"mode not stored as 'app': {data}"
        assert data.get("platform") == platform, f"platform not stored: {data}"
        assert "id" in data
        pid = data["id"]

        # GET — verify persistence
        try:
            g = authed.get(f"{BASE_URL}/api/freebuild-chat/project/{pid}")
            assert g.status_code == 200, f"get failed: {g.status_code} {g.text[:300]}"
            proj = g.json()
            assert proj.get("mode") == "app"
            assert proj.get("platform") == platform
            msgs = proj.get("messages") or []
            assert len(msgs) >= 1, "no greeting messages in project"
            # Concatenate first 3 messages to be safe
            txt = " ".join((m.get("content") or "") for m in msgs[:3])
            assert any(term.lower() in txt.lower() for term in label_terms), (
                f"greeting for platform={platform} did not mention any of {label_terms}.\nGreeting: {txt[:500]}"
            )
        finally:
            _delete_project(authed, pid)

    def test_create_app_project_invalid_platform_defaults_to_both(self, authed):
        """Server validates platform — invalid value should fall back to 'both'."""
        payload = {
            "name": "TEST_native_invalid_platform",
            "description": "invalid platform fallback",
            "mode": "app",
            "platform": "windows-phone",
        }
        r = authed.post(f"{BASE_URL}/api/freebuild-chat/project", json=payload)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        data = r.json()
        assert data.get("mode") == "app"
        assert data.get("platform") == "both", f"expected fallback to 'both', got {data.get('platform')}"
        _delete_project(authed, data["id"])

    def test_create_app_project_missing_platform_defaults_to_both(self, authed):
        """When mode='app' and no platform sent, server should default to 'both'."""
        payload = {
            "name": "TEST_native_no_platform",
            "mode": "app",
        }
        r = authed.post(f"{BASE_URL}/api/freebuild-chat/project", json=payload)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        data = r.json()
        assert data.get("mode") == "app"
        assert data.get("platform") == "both"
        _delete_project(authed, data["id"])


class TestWebsiteBackwardsCompat:
    """Regression: website-mode project still works and stores platform=None."""

    def test_create_website_project_no_platform(self, authed):
        payload = {"name": "TEST_native_website_regression", "description": "regression test"}
        r = authed.post(f"{BASE_URL}/api/freebuild-chat/project", json=payload)
        assert r.status_code == 200
        data = r.json()
        # Default mode should NOT be 'app'
        assert data.get("mode") != "app", f"expected non-app mode, got {data.get('mode')}"
        # platform should be None for website projects
        assert data.get("platform") in (None, ""), f"website project should have null platform, got {data.get('platform')}"

        # Verify GET also returns same
        pid = data["id"]
        try:
            g = authed.get(f"{BASE_URL}/api/freebuild-chat/project/{pid}")
            assert g.status_code == 200
            proj = g.json()
            assert proj.get("mode") != "app"
            assert proj.get("platform") in (None, "")
        finally:
            _delete_project(authed, pid)


class TestExistingSeededAppProject:
    """The main agent referenced an existing app project ID with seeded current_html."""

    SEEDED_PID = "ba0892c8-6d2a-423a-9bdf-ebe6271bb02a"

    def test_seeded_app_project_returns_app_mode(self, authed):
        g = authed.get(f"{BASE_URL}/api/freebuild-chat/project/{self.SEEDED_PID}")
        if g.status_code == 404:
            pytest.skip("seeded project not found (likely owned by different user)")
        if g.status_code == 403:
            pytest.skip("seeded project owned by another user")
        assert g.status_code == 200, f"{g.status_code} {g.text[:200]}"
        proj = g.json()
        assert proj.get("mode") == "app"
        assert proj.get("platform") in ("ios", "android", "both")
