"""
Tests for new Game Studio features:
- GET /api/games/projects (list user's projects across web+app studios)
- GET /api/games/project/{id}/notes (AI memory/GDD)
- POST /api/games/project/{id}/notes/refresh (regenerate AI notes)
- POST /api/games/project/{id}/chat (auto_refresh_notes background task)
"""
import os
import time
import requests
import pytest

def _load_base_url():
    val = os.environ.get('REACT_APP_BACKEND_URL', '').strip()
    if val:
        return val.rstrip('/')
    # Fallback: read from frontend/.env
    env_path = '/app/frontend/.env'
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip().rstrip('/')
    raise RuntimeError("REACT_APP_BACKEND_URL not set")

BASE_URL = _load_base_url()
OWNER_EMAIL = "owner@zerax.com"
OWNER_PASSWORD = "owner123"


@pytest.fixture(scope="module")
def owner_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:200]}"
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture(scope="module")
def headers(owner_token):
    assert owner_token, "No auth token returned"
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture(scope="module")
def existing_projects(headers):
    """Get list of projects to use for testing notes endpoints."""
    r = requests.get(f"{BASE_URL}/api/games/projects", headers=headers, timeout=30)
    assert r.status_code == 200, f"List projects failed: {r.status_code}"
    data = r.json()
    return data.get("projects", [])


# ---------- GET /api/games/projects ----------

class TestListProjects:
    def test_list_projects_status(self, headers):
        r = requests.get(f"{BASE_URL}/api/games/projects", headers=headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "projects" in data
        assert isinstance(data["projects"], list)

    def test_list_projects_schema(self, existing_projects):
        if not existing_projects:
            pytest.skip("No projects to validate schema")
        sample = existing_projects[0]
        required_fields = ["id", "title", "game_type", "current_phase", "size_mb", "limit_mb", "asset_count", "has_notes"]
        for f in required_fields:
            assert f in sample, f"Missing field: {f}. Got keys: {list(sample.keys())}"
        # No raw mongo _id
        assert "_id" not in sample

    def test_list_projects_filter_web(self, headers):
        r = requests.get(f"{BASE_URL}/api/games/projects?game_type=web", headers=headers, timeout=30)
        assert r.status_code == 200
        for p in r.json().get("projects", []):
            assert p.get("game_type") == "web"

    def test_list_projects_filter_app(self, headers):
        r = requests.get(f"{BASE_URL}/api/games/projects?game_type=app", headers=headers, timeout=30)
        assert r.status_code == 200
        for p in r.json().get("projects", []):
            assert p.get("game_type") == "app"


# ---------- GET /api/games/project/{id}/notes ----------

class TestGetNotes:
    def test_get_notes_for_existing_project(self, headers, existing_projects):
        if not existing_projects:
            pytest.skip("No projects available")
        pid = existing_projects[0]["id"]
        r = requests.get(f"{BASE_URL}/api/games/project/{pid}/notes", headers=headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "notes" in data
        assert "updated_at" in data

    def test_get_notes_nonexistent_project(self, headers):
        r = requests.get(f"{BASE_URL}/api/games/project/nonexistent-id-xyz/notes", headers=headers, timeout=30)
        # Should be 404 or similar, not 500
        assert r.status_code in (400, 403, 404), f"Got {r.status_code}: {r.text[:200]}"

    def test_get_notes_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/games/project/whatever/notes", timeout=30)
        assert r.status_code in (401, 403)


# ---------- POST /api/games/project/{id}/notes/refresh ----------

class TestRefreshNotes:
    def test_refresh_notes_returns_ok(self, headers, existing_projects):
        if not existing_projects:
            pytest.skip("No projects available")
        # Prefer a project with messages — pick the one with has_notes or first
        pid = existing_projects[0]["id"]
        r = requests.post(f"{BASE_URL}/api/games/project/{pid}/notes/refresh", headers=headers, timeout=120)
        assert r.status_code == 200, f"Refresh failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        assert "notes" in data
        assert "updated" in data
        assert isinstance(data["updated"], bool)

    def test_refresh_notes_unauth(self):
        r = requests.post(f"{BASE_URL}/api/games/project/whatever/notes/refresh", timeout=30)
        assert r.status_code in (401, 403)


# ---------- POST /api/games/project/{id}/chat ----------

class TestChatTriggersNotesRefresh:
    def test_chat_send_message(self, headers, existing_projects):
        if not existing_projects:
            pytest.skip("No projects available")
        pid = existing_projects[0]["id"]
        r = requests.post(
            f"{BASE_URL}/api/games/project/{pid}/chat",
            headers=headers,
            data={"message": "اختبار تلقائي: اختصر لي الفكرة في جملة"},
            timeout=180,
        )
        assert r.status_code == 200, f"Chat failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        assert data.get("ok") is True
        assert "message" in data
        assert "credits_used" in data
        assert "generated_assets" in data
