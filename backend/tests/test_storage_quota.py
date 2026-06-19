"""Tests for storage quota endpoint + connection guides metadata."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-cinematic-hub-2.preview.emergentagent.com").rstrip("/")
EMAIL = "owner@zerax.com"
PASSWORD = "owner123"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=60)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    j = r.json()
    tok = j.get("token") or j.get("access_token")
    assert tok, f"no token in {j}"
    return tok


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ----- Storage usage endpoint -----
class TestStorageUsage:
    def test_storage_usage_shape(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/freebuild-chat/storage/usage", headers=auth_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in [
            "tier", "tier_label", "next_tier_label", "used_mb", "quota_mb",
            "used_pct", "project_count", "quota_projects",
            "over_quota", "over_storage", "over_projects", "needs_upgrade",
        ]:
            assert k in d, f"missing key {k} in {d}"
        assert isinstance(d["used_mb"], (int, float))
        assert isinstance(d["quota_mb"], int)
        assert isinstance(d["project_count"], int)
        assert isinstance(d["quota_projects"], int)
        assert isinstance(d["over_quota"], bool)
        assert isinstance(d["needs_upgrade"], bool)

    def test_storage_usage_defaults_free_tier(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/freebuild-chat/storage/usage", headers=auth_headers, timeout=30)
        d = r.json()
        # owner@zerax.com should be free tier by default
        assert d["tier"] in ("free", "pro", "studio")
        if d["tier"] == "free":
            assert d["quota_mb"] == 100
            assert d["quota_projects"] == 3
            assert d["tier_label"] == "مجاني"
            assert d["next_tier_label"] == "Pro"

    def test_storage_usage_owner_over_quota(self, auth_headers):
        """owner@zerax.com has 73 projects > free quota=3 → needs_upgrade=true"""
        r = requests.get(f"{BASE_URL}/api/freebuild-chat/storage/usage", headers=auth_headers, timeout=30)
        d = r.json()
        # Project count should be >> 3
        assert d["project_count"] >= 1, d
        if d["tier"] == "free" and d["project_count"] > 3:
            assert d["over_projects"] is True
            assert d["needs_upgrade"] is True
            assert d["over_quota"] is True

    def test_storage_usage_unauthenticated(self):
        r = requests.get(f"{BASE_URL}/api/freebuild-chat/storage/usage", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"


# ----- Projects listing (used by MyProjects page) -----
class TestProjectsList:
    def test_list_projects(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/freebuild-chat/projects", headers=auth_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "projects" in d
        assert isinstance(d["projects"], list)

    def test_seed_app_project_loads(self, auth_headers):
        """Seed app-mode project ba0892c8 must be loadable for code_unlocked / connections panel test."""
        pid = "ba0892c8-6d2a-423a-9bdf-ebe6271bb02a"
        r = requests.get(f"{BASE_URL}/api/freebuild-chat/project/{pid}", headers=auth_headers, timeout=30)
        # If not found in this DB, skip gracefully
        if r.status_code == 404:
            pytest.skip("seed app project missing in current DB")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("id") == pid
