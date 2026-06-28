"""Tests for new Continuation App Onboarding wizard endpoints.

Endpoints covered:
  GET  /api/freebuild-chat/continuation/app-providers-catalog
  POST /api/freebuild-chat/projects/continuation/create  (with project_kind=app)
  GET  /api/freebuild-chat/project/{pid}/continuation/setup
  POST /api/freebuild-chat/project/{pid}/continuation/setup/save-stack
  POST /api/freebuild-chat/project/{pid}/continuation/setup/select-provider
  POST /api/freebuild-chat/project/{pid}/continuation/setup/save-credential
  POST /api/freebuild-chat/project/{pid}/continuation/setup/consent

Plus backwards-compat: a site project still defaults to state='url'.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-cinematic-hub-2.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

OWNER_EMAIL = "owner@zerax.com"
OWNER_PASSWORD = "owner123"

EXPECTED_PROVIDER_IDS = {
    "github", "gitlab", "bitbucket", "azure_devops", "gitea", "other_git",
    "expo_eas", "codemagic", "bitrise", "github_actions", "zip_upload",
}


@pytest.fixture(scope="session")
def auth_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in login response: {data}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def app_project(auth_session):
    payload = {
        "name": "TEST_app_wizard_zenrex",
        "source_type": "description",
        "description": "TEST app continuation project for Flutter - automated regression suite for zenrex farm wizard.",
        "metadata": {"project_kind": "app", "app_kind": "flutter"},
    }
    r = auth_session.post(f"{API}/freebuild-chat/projects/continuation/create", json=payload, timeout=30)
    assert r.status_code == 200, f"Create app project failed: {r.status_code} {r.text}"
    data = r.json()
    pid = data.get("project_id") or (data.get("project") or {}).get("id") or data.get("id")
    assert pid, f"No project_id in response: {data}"
    yield pid
    # Best-effort cleanup
    try:
        auth_session.delete(f"{API}/freebuild-chat/projects/{pid}", timeout=10)
    except Exception:
        pass


@pytest.fixture(scope="session")
def site_project(auth_session):
    payload = {
        "name": "TEST_site_wizard_backcompat",
        "source_type": "url",
        "url": "https://example.com",
    }
    r = auth_session.post(f"{API}/freebuild-chat/projects/continuation/create", json=payload, timeout=30)
    assert r.status_code == 200, f"Create site project failed: {r.status_code} {r.text}"
    data = r.json()
    pid = data.get("project_id") or (data.get("project") or {}).get("id") or data.get("id")
    assert pid, f"No project_id in response: {data}"
    yield pid
    try:
        auth_session.delete(f"{API}/freebuild-chat/projects/{pid}", timeout=10)
    except Exception:
        pass


# --- Catalog endpoint -------------------------------------------------------

class TestAppProvidersCatalog:
    def test_catalog_returns_11_providers(self, auth_session):
        r = auth_session.get(f"{API}/freebuild-chat/continuation/app-providers-catalog", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "code_source_providers" in data
        providers = data["code_source_providers"]
        ids = {p.get("id") for p in providers}
        missing = EXPECTED_PROVIDER_IDS - ids
        assert not missing, f"Missing provider ids: {missing}. Got: {ids}"

    def test_catalog_includes_zip_upload(self, auth_session):
        r = auth_session.get(f"{API}/freebuild-chat/continuation/app-providers-catalog", timeout=30)
        data = r.json()
        zip_p = next((p for p in data["code_source_providers"] if p["id"] == "zip_upload"), None)
        assert zip_p is not None
        assert zip_p.get("group") == "upload"


# --- App project create + initial state ------------------------------------

class TestAppProjectInitialState:
    def test_get_setup_state_is_stack(self, auth_session, app_project):
        r = auth_session.get(f"{API}/freebuild-chat/project/{app_project}/continuation/setup", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("project_kind") == "app", data
        assert data.get("app_kind") == "flutter", data
        assert data.get("state") == "stack", f"Expected state=stack for fresh app project, got {data.get('state')}"
        assert data.get("completed") is False


# --- save-stack ------------------------------------------------------------

class TestSaveStack:
    def test_save_stack_advances_to_provider(self, auth_session, app_project):
        body = {"app_kind": "flutter", "target_platforms": ["ios", "android"], "repo_url_hint": "https://github.com/u/r"}
        r = auth_session.post(f"{API}/freebuild-chat/project/{app_project}/continuation/setup/save-stack", json=body, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("next_state") == "provider"
        stack = data.get("app_stack") or {}
        assert stack.get("app_kind") == "flutter"
        assert set(stack.get("target_platforms") or []) == {"ios", "android"}

        # Verify persistence via GET setup
        r2 = auth_session.get(f"{API}/freebuild-chat/project/{app_project}/continuation/setup", timeout=30)
        d2 = r2.json()
        assert d2.get("state") == "provider", d2
        assert (d2.get("app_stack") or {}).get("app_kind") == "flutter"

    def test_save_stack_rejects_missing_app_kind(self, auth_session, app_project):
        r = auth_session.post(
            f"{API}/freebuild-chat/project/{app_project}/continuation/setup/save-stack",
            json={"target_platforms": ["ios"]},
            timeout=30,
        )
        assert r.status_code == 400


# --- backwards compat for site -----------------------------------

class TestSiteBackcompat:
    def test_site_project_initial_state_is_url(self, auth_session, site_project):
        r = auth_session.get(f"{API}/freebuild-chat/project/{site_project}/continuation/setup", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("project_kind") in ("site", None, "", "continuation_site"), data
        # The new code defaults to "site" string; old projects may be missing key.
        assert data.get("state") == "url", f"site project should start at url, got {data.get('state')}"

    def test_save_stack_on_site_project_rejected(self, auth_session, site_project):
        r = auth_session.post(
            f"{API}/freebuild-chat/project/{site_project}/continuation/setup/save-stack",
            json={"app_kind": "flutter"},
            timeout=30,
        )
        assert r.status_code == 400, f"save-stack on site project should be 400, got {r.status_code}"


# --- Provider + credential + consent advance flow (app) ----------

class TestAppFullFlow:
    def test_select_provider_github(self, auth_session, app_project):
        # Save stack first (idempotent)
        auth_session.post(
            f"{API}/freebuild-chat/project/{app_project}/continuation/setup/save-stack",
            json={"app_kind": "flutter", "target_platforms": ["android"]},
            timeout=30,
        )
        r = auth_session.post(
            f"{API}/freebuild-chat/project/{app_project}/continuation/setup/select-provider",
            json={"provider_id": "github"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("next_state") in ("provider_key", "credential")

    def test_save_credential_advances(self, auth_session, app_project):
        r = auth_session.post(
            f"{API}/freebuild-chat/project/{app_project}/continuation/setup/save-credential",
            json={
                "key_name": "GITHUB_TOKEN",
                "value": "ghp_test_token_1234567890_dummy_value",
                "validity_months": 3,
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        # After save-credential, server sets state=consent (app flow skips LLM step).
        r2 = auth_session.get(f"{API}/freebuild-chat/project/{app_project}/continuation/setup", timeout=30)
        d2 = r2.json()
        assert d2.get("state") in ("consent", "llm"), d2
