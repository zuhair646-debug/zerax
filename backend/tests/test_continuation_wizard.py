"""Backend tests for the Continuation Onboarding Wizard.

Covers:
 - POST /api/freebuild-chat/continuation/inspect-url
 - POST /api/freebuild-chat/projects/continuation/create
 - GET  /api/freebuild-chat/project/{pid}/continuation/setup
 - POST /api/freebuild-chat/project/{pid}/continuation/setup/save-url
 - POST /api/freebuild-chat/project/{pid}/continuation/setup/select-provider
 - POST /api/freebuild-chat/project/{pid}/continuation/setup/save-credential
 - POST /api/freebuild-chat/project/{pid}/continuation/setup/save-llm-key
 - POST /api/freebuild-chat/project/{pid}/continuation/setup/consent
 - Duplicate URL rejection across projects
 - Encryption-at-rest verification (motor + decrypt_secret round-trip)
 - Input validation: validity_months<3, bad Anthropic key, missing signature, missing url
"""
import asyncio
import os
import sys
import pytest
import requests

# Ensure backend modules are importable for the mongo + decrypt round-trip check.
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from modules.freebuild.secure_credentials import decrypt_secret  # noqa: E402

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-cinematic-hub-2.preview.emergentagent.com").rstrip("/")
PREFIX = f"{BASE_URL}/api/freebuild-chat"

OWNER_EMAIL = "owner@zerax.com"
OWNER_PASS = "owner123"

PLAINTEXT_GH = "ghp_secret123_TESTABCDEF"


# ─── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def token():
    last_exc = None
    for _ in range(3):
        try:
            r = requests.post(f"{BASE_URL}/api/auth/login",
                              json={"email": OWNER_EMAIL, "password": OWNER_PASS}, timeout=60)
            assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:300]}"
            break
        except Exception as e:
            last_exc = e
    else:
        raise last_exc  # type: ignore
    data = r.json()
    return data.get("token") or data.get("access_token")


@pytest.fixture(scope="session")
def auth(token):
    assert token, "no token from login response"
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session", autouse=True)
def cleanup_prior_wordpress_projects(token):
    """Remove any prior continuation projects for owner that already point to
    https://wordpress.com — otherwise the dupe-URL guard will fire on test_02.
    """
    async def _wipe():
        cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = cli[os.environ.get("DB_NAME", "test_database")]
        # Find owner user_id from token (we already know it from login response,
        # but easier to just match by email lookup in users)
        owner = await db.users.find_one({"email": OWNER_EMAIL}, {"_id": 0, "id": 1})
        if owner:
            uid = owner["id"]
            await db.freebuild_projects.delete_many({
                "user_id": uid,
                "mode": "continuation",
                "continuation_site_url_norm": "https://wordpress.com",
            })
        cli.close()
    asyncio.run(_wipe())
    yield


@pytest.fixture(scope="module")
def project_a(auth):
    """First continuation project — full wizard flow."""
    r = requests.post(f"{PREFIX}/projects/continuation/create", headers=auth,
                      json={"source_type": "description",
                            "description": "TEST_wizard_A - continuation project for wizard e2e flow validation"},
                      timeout=20)
    assert r.status_code == 200, f"create A failed: {r.status_code} {r.text[:300]}"
    pid = r.json().get("project_id")
    assert pid
    yield pid
    try:
        requests.delete(f"{PREFIX}/project/{pid}", headers=auth, timeout=10)
    except Exception:
        pass


@pytest.fixture(scope="module")
def project_b(auth):
    """Second continuation project — used for duplicate-URL test."""
    r = requests.post(f"{PREFIX}/projects/continuation/create", headers=auth,
                      json={"source_type": "description",
                            "description": "TEST_wizard_B - second continuation project for dupe URL test"},
                      timeout=20)
    assert r.status_code == 200, f"create B failed: {r.status_code} {r.text[:300]}"
    pid = r.json().get("project_id")
    assert pid
    yield pid
    try:
        requests.delete(f"{PREFIX}/project/{pid}", headers=auth, timeout=10)
    except Exception:
        pass


# ─── Inspector ───────────────────────────────────────────────────────────────
class TestInspector:
    def test_inspect_url_wordpress(self, auth):
        r = requests.post(f"{PREFIX}/continuation/inspect-url",
                          headers=auth, json={"url": "https://wordpress.com"}, timeout=20)
        assert r.status_code == 200, f"inspect failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        # platform/framework/hints/recommended_provider must be present
        for k in ("url", "domain", "platform", "framework", "hints", "recommended_provider"):
            assert k in data, f"missing field: {k}"
        assert data["domain"].endswith("wordpress.com")
        assert isinstance(data["hints"], list)

    def test_inspect_url_missing_url_returns_400(self, auth):
        r = requests.post(f"{PREFIX}/continuation/inspect-url",
                          headers=auth, json={}, timeout=15)
        assert r.status_code == 400, f"expected 400 got {r.status_code} {r.text[:200]}"


# ─── Wizard happy-path (5 steps) ─────────────────────────────────────────────
class TestWizardFlow:
    def test_01_initial_setup_state_is_url(self, auth, project_a):
        r = requests.get(f"{PREFIX}/project/{project_a}/continuation/setup",
                         headers=auth, timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["state"] == "url"
        assert data["completed"] is False

    def test_02_save_url_advances_to_provider(self, auth, project_a):
        r = requests.post(f"{PREFIX}/project/{project_a}/continuation/setup/save-url",
                          headers=auth,
                          json={"url": "https://wordpress.com",
                                "inspection": {"platform": "WordPress Hosting",
                                               "framework": "WordPress"}},
                          timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data.get("ok") is True
        assert data.get("next_state") == "provider"

    def test_03_select_provider_github(self, auth, project_a):
        r = requests.post(f"{PREFIX}/project/{project_a}/continuation/setup/select-provider",
                          headers=auth, json={"provider_id": "github"}, timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["ok"] is True
        assert data["provider_id"] == "github"
        assert data["next_state"] == "provider_key"

    def test_04_save_credential_encrypts_and_masks(self, auth, project_a):
        r = requests.post(f"{PREFIX}/project/{project_a}/continuation/setup/save-credential",
                          headers=auth,
                          json={"key_name": "GITHUB_TOKEN",
                                "value": PLAINTEXT_GH,
                                "validity_months": 6}, timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["ok"] is True
        assert data["key_name"] == "GITHUB_TOKEN"
        assert "mask" in data and "••••" in data["mask"]
        # Mask should end with last 4 chars of plaintext
        assert data["mask"].endswith(PLAINTEXT_GH[-4:])

    def test_05_save_llm_key_emergent(self, auth, project_a):
        r = requests.post(f"{PREFIX}/project/{project_a}/continuation/setup/save-llm-key",
                          headers=auth, json={"provider": "emergent"}, timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["ok"] is True
        assert data["provider"] == "emergent"
        assert data["next_state"] == "consent"

    def test_06_consent_signature_unlocks(self, auth, project_a):
        r = requests.post(f"{PREFIX}/project/{project_a}/continuation/setup/consent",
                          headers=auth,
                          json={"clauses_accepted": ["c1", "c2", "c3", "c4"],
                                "signature_name": "Test Owner"}, timeout=15)
        assert r.status_code == 200, r.text[:300]

    def test_07_get_setup_state_is_ready(self, auth, project_a):
        r = requests.get(f"{PREFIX}/project/{project_a}/continuation/setup",
                         headers=auth, timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["state"] == "ready", f"got state={data.get('state')}"
        assert data["completed"] is True
        # masked credential must be in meta
        meta = data.get("credentials_meta") or {}
        assert "GITHUB_TOKEN" in meta, f"meta keys: {list(meta.keys())}"
        mask = meta["GITHUB_TOKEN"].get("mask", "")
        assert "••••" in mask
        assert mask.endswith(PLAINTEXT_GH[-4:])


# ─── Encryption at rest (Mongo round-trip) ───────────────────────────────────
class TestEncryptionAtRest:
    def test_plaintext_never_stored_in_mongo(self, project_a):
        async def _check():
            cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db = cli[os.environ.get("DB_NAME", "test_database")]
            doc = await db.freebuild_projects.find_one({"id": project_a})
            cli.close()
            return doc
        doc = asyncio.run(_check())
        assert doc is not None, "project not found in mongo"
        creds = doc.get("continuation_credentials") or {}
        assert "GITHUB_TOKEN" in creds, f"creds keys: {list(creds.keys())}"
        ct = creds["GITHUB_TOKEN"].get("ciphertext")
        assert ct, "ciphertext missing"
        # MUST not equal plaintext, and must not contain plaintext substring
        assert ct != PLAINTEXT_GH
        assert PLAINTEXT_GH not in ct
        # Decrypt round-trip must return plaintext
        decrypted = decrypt_secret(ct)
        assert decrypted == PLAINTEXT_GH


# ─── Duplicate URL rejection ─────────────────────────────────────────────────
class TestDuplicateURL:
    def test_second_project_same_url_rejected(self, auth, project_a, project_b):
        # project_a already has https://wordpress.com saved (from TestWizardFlow).
        r = requests.post(f"{PREFIX}/project/{project_b}/continuation/setup/save-url",
                          headers=auth,
                          json={"url": "https://wordpress.com",
                                "inspection": {"platform": "WordPress Hosting"}},
                          timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data.get("ok") is False
        assert data.get("duplicate") is True
        assert data.get("existing_project_id") == project_a
        assert "existing_project_name" in data
        assert isinstance(data.get("message"), str) and len(data["message"]) > 0


# ─── Input validation (P1) ───────────────────────────────────────────────────
class TestValidation:
    def test_validity_months_less_than_3_returns_400(self, auth, project_a):
        r = requests.post(f"{PREFIX}/project/{project_a}/continuation/setup/save-credential",
                          headers=auth,
                          json={"key_name": "GITHUB_TOKEN", "value": "ghp_x",
                                "validity_months": 1}, timeout=15)
        assert r.status_code == 400, f"expected 400 got {r.status_code} {r.text[:200]}"

    def test_bad_anthropic_key_returns_400(self, auth, project_b):
        # project_b state is still 'url' here; the endpoint validates key prefix regardless
        # of state, so we can call it directly.
        r = requests.post(f"{PREFIX}/project/{project_b}/continuation/setup/save-llm-key",
                          headers=auth,
                          json={"provider": "anthropic", "value": "not-a-claude-key"},
                          timeout=15)
        assert r.status_code == 400, f"expected 400 got {r.status_code} {r.text[:200]}"

    def test_consent_missing_signature_returns_400(self, auth, project_b):
        r = requests.post(f"{PREFIX}/project/{project_b}/continuation/setup/consent",
                          headers=auth,
                          json={"clauses_accepted": ["c1", "c2", "c3"],
                                "signature_name": ""}, timeout=15)
        assert r.status_code == 400, f"expected 400 got {r.status_code} {r.text[:200]}"
