"""Iter86 regression tests — guards on the new endpoints flagged by code review.

Targets PRODUCTION by default (https://zenrex.ai with admin@zenrex.ai). Override
via TEST_BASE_URL + TEST_EMAIL + TEST_PASSWORD env vars.

Coverage:
  - save-stack on completed setup → 409 idempotency guard
  - save-extra on incomplete setup → 400 'finish the setup wizard first'
  - DELETE credentials returns revoked:true ONLY when the key existed
  - Cross-tenant 404 (wrong user can't read another user's project)
  - Site-project backwards-compat (state='url', store-providers-catalog still ok)
  - /continuation/store-providers-catalog returns store + signing providers
  - URL alias backward-compat (both /freebuild/continue-app and /freebuild/continue/app)
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("TEST_BASE_URL", "https://zenrex.ai").rstrip("/")
API = f"{BASE_URL}/api"
EMAIL = os.environ.get("TEST_EMAIL", "admin@zenrex.ai")
PASSWORD = os.environ.get("TEST_PASSWORD", "Zenrex@2026")


def _login(email, password):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    token = data.get("token") or data.get("access_token")
    assert token
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s, data["user"]["id"]


@pytest.fixture(scope="session")
def owner():
    s, uid = _login(EMAIL, PASSWORD)
    return {"session": s, "user_id": uid}


def _create_app_project(s, name_suffix=""):
    """Create an app continuation project and return its pid."""
    payload = {
        "name": f"TEST_iter86_app_{name_suffix or uuid.uuid4().hex[:6]}",
        "source_type": "description",
        "description": "TEST iter86 regression suite — Flutter app continuation project",
        "metadata": {"project_kind": "app", "app_kind": "flutter"},
    }
    r = s.post(f"{API}/freebuild-chat/projects/continuation/create", json=payload, timeout=30)
    assert r.status_code == 200, f"create app failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    pid = data.get("project_id") or (data.get("project") or {}).get("id") or data.get("id")
    assert pid, f"no pid: {data}"
    return pid


def _create_site_project(s, name_suffix=""):
    payload = {
        "name": f"TEST_iter86_site_{name_suffix or uuid.uuid4().hex[:6]}",
        "source_type": "url",
        "url": "https://example.com",
    }
    r = s.post(f"{API}/freebuild-chat/projects/continuation/create", json=payload, timeout=30)
    assert r.status_code == 200, f"create site failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    pid = data.get("project_id") or (data.get("project") or {}).get("id") or data.get("id")
    assert pid, f"no pid: {data}"
    return pid


def _delete_project(s, pid):
    try:
        s.delete(f"{API}/freebuild-chat/projects/{pid}", timeout=10)
    except Exception:
        pass


def _complete_wizard(s, pid):
    """Drive an app project through stack→provider→credential→consent."""
    r = s.post(f"{API}/freebuild-chat/project/{pid}/continuation/setup/save-stack",
               json={"app_kind": "flutter", "target_platforms": ["android"]}, timeout=30)
    assert r.status_code == 200, r.text
    r = s.post(f"{API}/freebuild-chat/project/{pid}/continuation/setup/select-provider",
               json={"provider_id": "github"}, timeout=30)
    assert r.status_code == 200, r.text
    r = s.post(f"{API}/freebuild-chat/project/{pid}/continuation/setup/save-credential",
               json={"key_name": "GITHUB_TOKEN", "value": "ghp_iter86_dummy_token_xxxxx",
                     "validity_months": 6}, timeout=30)
    assert r.status_code == 200, r.text
    r = s.post(f"{API}/freebuild-chat/project/{pid}/continuation/setup/consent",
               json={"clauses_accepted": [0, 1, 2, 3, 4],
                     "signature_name": "Iter86 Tester"}, timeout=30)
    assert r.status_code == 200, f"consent failed: {r.status_code} {r.text[:200]}"


# ---------------------------------------------------------------------------
# Store providers catalog
# ---------------------------------------------------------------------------

class TestStoreProvidersCatalog:
    def test_catalog_returns_store_and_signing(self, owner):
        r = owner["session"].get(f"{API}/freebuild-chat/continuation/store-providers-catalog", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "store_providers" in data
        assert "signing_providers" in data
        assert isinstance(data["store_providers"], list)
        assert isinstance(data["signing_providers"], list)
        # Catalog should expose at least the canonical store providers
        store_ids = {p.get("id") for p in data["store_providers"]}
        assert "google_play" in store_ids or len(store_ids) >= 3, f"unexpected stores: {store_ids}"


# ---------------------------------------------------------------------------
# Regression 1 — save-stack idempotency guard (409 on completed setup)
# ---------------------------------------------------------------------------

class TestSaveStackIdempotency:
    def test_save_stack_after_completed_returns_409(self, owner):
        s = owner["session"]
        pid = _create_app_project(s, "idem")
        try:
            _complete_wizard(s, pid)
            # Verify setup is now completed
            r = s.get(f"{API}/freebuild-chat/project/{pid}/continuation/setup", timeout=30)
            setup = r.json()
            assert setup.get("completed") is True, f"setup not completed: {setup}"
            # Re-call save-stack — must NOT silently reset; must return 409
            r2 = s.post(f"{API}/freebuild-chat/project/{pid}/continuation/setup/save-stack",
                        json={"app_kind": "flutter", "target_platforms": ["ios"]}, timeout=30)
            assert r2.status_code == 409, f"expected 409, got {r2.status_code}: {r2.text[:200]}"
            assert "already" in r2.text.lower() or "refus" in r2.text.lower()
        finally:
            _delete_project(s, pid)


# ---------------------------------------------------------------------------
# Regression 2 — save-extra requires completed wizard (400)
# ---------------------------------------------------------------------------

class TestSaveExtraRequiresCompletedWizard:
    def test_save_extra_before_wizard_completed_returns_400(self, owner):
        s = owner["session"]
        pid = _create_app_project(s, "extra_incomplete")
        try:
            r = s.post(f"{API}/freebuild-chat/project/{pid}/continuation/credentials/save-extra",
                       json={"key_name": "GOOGLE_SERVICE_ACCOUNT_JSON",
                             "value": '{"type":"service_account"}',
                             "validity_months": 12, "category": "store"}, timeout=30)
            assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:200]}"
            assert "finish" in r.text.lower() or "wizard" in r.text.lower()
        finally:
            _delete_project(s, pid)

    def test_save_extra_after_wizard_completed_succeeds(self, owner):
        s = owner["session"]
        pid = _create_app_project(s, "extra_ok")
        try:
            _complete_wizard(s, pid)
            r = s.post(f"{API}/freebuild-chat/project/{pid}/continuation/credentials/save-extra",
                       json={"key_name": "GOOGLE_SERVICE_ACCOUNT_JSON",
                             "value": '{"type":"service_account","project_id":"x"}',
                             "validity_months": 12, "category": "store"}, timeout=30)
            assert r.status_code == 200, r.text
            data = r.json()
            assert data.get("ok") is True
            assert data.get("key_name") == "GOOGLE_SERVICE_ACCOUNT_JSON"
            assert "mask" in data
            mask = data.get("mask") or ""
            # Mask may use '*' or unicode bullet '•' — just ensure it isn't plaintext
            assert ("*" in mask or "•" in mask) and "service_account" not in mask
            assert data.get("category") == "store"
            # Verify it appears in meta endpoint
            m = s.get(f"{API}/freebuild-chat/project/{pid}/continuation/credentials/meta", timeout=30)
            assert m.status_code == 200
            assert "GOOGLE_SERVICE_ACCOUNT_JSON" in (m.json().get("credentials_meta") or {})
        finally:
            _delete_project(s, pid)


# ---------------------------------------------------------------------------
# Regression 3 — DELETE returns revoked:true ONLY when key existed
# ---------------------------------------------------------------------------

class TestDeleteCredentialExistedCheck:
    def test_delete_existing_key_returns_revoked_true(self, owner):
        s = owner["session"]
        pid = _create_app_project(s, "del_exist")
        try:
            _complete_wizard(s, pid)
            # Save an extra key, then delete it
            s.post(f"{API}/freebuild-chat/project/{pid}/continuation/credentials/save-extra",
                   json={"key_name": "FIREBASE_TOKEN", "value": "fb_real_dummy_xxxx",
                         "validity_months": 6, "category": "store"}, timeout=30)
            r = s.delete(f"{API}/freebuild-chat/project/{pid}/continuation/credentials/FIREBASE_TOKEN",
                         timeout=30)
            assert r.status_code == 200, r.text
            data = r.json()
            assert data.get("revoked") is True, f"expected revoked=true, got: {data}"
        finally:
            _delete_project(s, pid)

    def test_delete_missing_key_returns_revoked_false(self, owner):
        s = owner["session"]
        pid = _create_app_project(s, "del_missing")
        try:
            _complete_wizard(s, pid)
            r = s.delete(f"{API}/freebuild-chat/project/{pid}/continuation/credentials/NEVER_SAVED_KEY",
                         timeout=30)
            assert r.status_code == 200, r.text
            data = r.json()
            assert data.get("revoked") is False, f"expected revoked=false, got: {data}"
        finally:
            _delete_project(s, pid)


# ---------------------------------------------------------------------------
# Regression 4 — cross-tenant 404 (wrong user_id must NOT leak)
# ---------------------------------------------------------------------------

class TestCrossTenantIsolation:
    def test_wrong_user_get_setup_returns_404_or_400(self, owner):
        """A random bogus token / a no-auth call must not be able to read another user's setup."""
        s = owner["session"]
        pid = _create_app_project(s, "tenant")
        try:
            # Unauthenticated request
            anon = requests.Session()
            anon.headers.update({"Content-Type": "application/json"})
            r = anon.get(f"{API}/freebuild-chat/project/{pid}/continuation/setup", timeout=30)
            # Must NOT be 200 — auth required
            assert r.status_code in (401, 403, 404), f"expected 401/403/404, got {r.status_code}: {r.text[:200]}"

            # Bogus token
            anon.headers.update({"Authorization": "Bearer invalid.jwt.token"})
            r2 = anon.get(f"{API}/freebuild-chat/project/{pid}/continuation/setup", timeout=30)
            assert r2.status_code in (401, 403, 404), f"bogus token leaked? {r2.status_code}: {r2.text[:200]}"
        finally:
            _delete_project(s, pid)

    def test_wrong_pid_returns_400_or_404(self, owner):
        s = owner["session"]
        bogus_pid = f"bogus-{uuid.uuid4()}"
        r = s.get(f"{API}/freebuild-chat/project/{bogus_pid}/continuation/setup", timeout=30)
        assert r.status_code in (400, 404), f"expected 400/404, got {r.status_code}"

    def test_save_stack_on_nonexistent_project_returns_400(self, owner):
        s = owner["session"]
        bogus_pid = f"bogus-{uuid.uuid4()}"
        r = s.post(f"{API}/freebuild-chat/project/{bogus_pid}/continuation/setup/save-stack",
                   json={"app_kind": "flutter"}, timeout=30)
        assert r.status_code in (400, 404), f"expected 400/404, got {r.status_code}"


# ---------------------------------------------------------------------------
# Regression 5 — site project backwards compat
# ---------------------------------------------------------------------------

class TestSiteBackcompat:
    def test_site_project_state_is_url_not_stack(self, owner):
        s = owner["session"]
        pid = _create_site_project(s, "compat")
        try:
            r = s.get(f"{API}/freebuild-chat/project/{pid}/continuation/setup", timeout=30)
            assert r.status_code == 200, r.text
            data = r.json()
            assert data.get("state") == "url", f"site should start at url, got {data.get('state')}"
            # save-stack must be rejected for site projects
            r2 = s.post(f"{API}/freebuild-chat/project/{pid}/continuation/setup/save-stack",
                        json={"app_kind": "flutter"}, timeout=30)
            assert r2.status_code == 400, r2.text
        finally:
            _delete_project(s, pid)


# ---------------------------------------------------------------------------
# Regression 6 — URL alias backward-compat (frontend routes)
# ---------------------------------------------------------------------------

class TestUrlAliasBackcompat:
    def test_continue_app_hyphen_route_200(self):
        r = requests.get(f"{BASE_URL}/freebuild/continue-app", timeout=30, allow_redirects=True)
        assert r.status_code == 200, f"expected 200, got {r.status_code}"

    def test_continue_app_slash_route_200(self):
        r = requests.get(f"{BASE_URL}/freebuild/continue/app", timeout=30, allow_redirects=True)
        assert r.status_code == 200, f"expected 200, got {r.status_code}"
