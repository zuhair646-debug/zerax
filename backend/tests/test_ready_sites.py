"""Pytest suite for Ready Sites wizard module — /api/ready-sites/*"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-cinematic-hub-2.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

OWNER_EMAIL = "owner@zitex.com"
OWNER_PASSWORD = "owner123"
AUDIT_EMAIL = "audit_1780793976@test.com"
AUDIT_PASSWORD = "Test1234!"


# -------- shared fixtures --------
@pytest.fixture(scope="session")
def http():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(http, email, password):
    r = http.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    if r.status_code != 200:
        return None
    return r.json().get("token") or r.json().get("access_token")


@pytest.fixture(scope="session")
def owner_token(http):
    tok = _login(http, OWNER_EMAIL, OWNER_PASSWORD)
    if not tok:
        pytest.skip("Owner login failed")
    return tok


@pytest.fixture(scope="session")
def audit_token(http):
    tok = _login(http, AUDIT_EMAIL, AUDIT_PASSWORD)
    if not tok:
        pytest.skip("Audit user login failed")
    return tok


def auth(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# -------- Catalog (public, no auth) --------
class TestCatalog:
    def test_catalog_returns_full_structure(self, http):
        r = http.get(f"{API}/ready-sites/catalog", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["types"]) == 4
        assert d["generate_cost"] == 40
        assert len(d["patterns"]["restaurant"]) == 4
        assert len(d["features"]["restaurant"]) == 24
        # Restaurant must be the only available type
        restaurant = next((t for t in d["types"] if t["id"] == "restaurant"), None)
        assert restaurant and restaurant["available"] is True
        # Validate pattern ids
        pat_ids = {p["id"] for p in d["patterns"]["restaurant"]}
        assert pat_ids == {"neon_crescent", "split_theatre", "orbital_menu", "mosaic_liquid"}


# -------- Full wizard happy path --------
class TestWizardFlow:
    def test_full_wizard_flow_until_ready(self, http, owner_token):
        h = auth(owner_token)

        # start
        r = http.post(f"{API}/ready-sites/start", json={}, headers=h, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["phase"] == "select_type"
        sid = d["session_id"]

        # select-type
        r = http.post(f"{API}/ready-sites/select-type",
                      json={"session_id": sid, "type_id": "restaurant"}, headers=h, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["phase"] == "select_pattern"
        assert len(d["patterns"]) == 4

        # select-pattern
        r = http.post(f"{API}/ready-sites/select-pattern",
                      json={"session_id": sid, "pattern_id": "neon_crescent"}, headers=h, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["phase"] == "branding"
        assert d["pattern"]["id"] == "neon_crescent"

        # branding
        r = http.post(f"{API}/ready-sites/branding",
                      json={"session_id": sid, "business_name": "TEST_مطعم زيتاكس",
                            "tagline": "نكهة الأصالة", "logo_mode": "text"},
                      headers=h, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["phase"] == "features"
        assert len(d["default_enabled"]) == 24
        default_enabled = d["default_enabled"]

        # features
        r = http.post(f"{API}/ready-sites/features",
                      json={"session_id": sid, "enabled": default_enabled}, headers=h, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["phase"] == "ready"
        assert d["estimated_cost"] == 40
        assert d["features_count"] == 24
        assert d["can_afford"] is True


# -------- Validation tests --------
class TestValidation:
    def _setup_session(self, http, tok):
        h = auth(tok)
        r = http.post(f"{API}/ready-sites/start", json={}, headers=h)
        return r.json()["session_id"], h

    def test_select_type_unknown_returns_400(self, http, owner_token):
        sid, h = self._setup_session(http, owner_token)
        r = http.post(f"{API}/ready-sites/select-type",
                      json={"session_id": sid, "type_id": "nope"}, headers=h)
        assert r.status_code == 400

    def test_select_pattern_unknown_returns_400(self, http, owner_token):
        sid, h = self._setup_session(http, owner_token)
        http.post(f"{API}/ready-sites/select-type",
                  json={"session_id": sid, "type_id": "restaurant"}, headers=h)
        r = http.post(f"{API}/ready-sites/select-pattern",
                      json={"session_id": sid, "pattern_id": "ghost"}, headers=h)
        assert r.status_code == 400

    def test_branding_empty_business_name_returns_422(self, http, owner_token):
        sid, h = self._setup_session(http, owner_token)
        http.post(f"{API}/ready-sites/select-type",
                  json={"session_id": sid, "type_id": "restaurant"}, headers=h)
        http.post(f"{API}/ready-sites/select-pattern",
                  json={"session_id": sid, "pattern_id": "neon_crescent"}, headers=h)
        r = http.post(f"{API}/ready-sites/branding",
                      json={"session_id": sid, "business_name": ""}, headers=h)
        assert r.status_code == 422

    def test_features_empty_list_returns_400(self, http, owner_token):
        sid, h = self._setup_session(http, owner_token)
        http.post(f"{API}/ready-sites/select-type",
                  json={"session_id": sid, "type_id": "restaurant"}, headers=h)
        http.post(f"{API}/ready-sites/select-pattern",
                  json={"session_id": sid, "pattern_id": "neon_crescent"}, headers=h)
        http.post(f"{API}/ready-sites/branding",
                  json={"session_id": sid, "business_name": "TEST_X", "logo_mode": "text"}, headers=h)
        r = http.post(f"{API}/ready-sites/features",
                      json={"session_id": sid, "enabled": []}, headers=h)
        assert r.status_code == 400

    def test_generate_without_ready_returns_400(self, http, owner_token):
        sid, h = self._setup_session(http, owner_token)
        r = http.post(f"{API}/ready-sites/generate",
                      json={"session_id": sid}, headers=h)
        # Should fail since phase != ready
        assert r.status_code == 400

    def test_auth_required_on_start(self, http):
        r = http.post(f"{API}/ready-sites/start", json={})
        assert r.status_code in (401, 403)


# -------- Low-credit user → 402 --------
class TestCredits:
    def test_low_credit_user_gets_402_on_generate(self, http, audit_token):
        """Audit user has 20 credits, generate costs 40 → must 402."""
        h = auth(audit_token)
        # Check current credits first
        me = http.get(f"{API}/auth/me", headers=h, timeout=15)
        if me.status_code != 200:
            pytest.skip("Cannot fetch user info")
        credits = me.json().get("credits", 0)
        if credits >= 40:
            pytest.skip(f"Audit user has {credits} credits, not below 40 — skip 402 test")

        r = http.post(f"{API}/ready-sites/start", json={}, headers=h)
        sid = r.json()["session_id"]
        http.post(f"{API}/ready-sites/select-type",
                  json={"session_id": sid, "type_id": "restaurant"}, headers=h)
        http.post(f"{API}/ready-sites/select-pattern",
                  json={"session_id": sid, "pattern_id": "neon_crescent"}, headers=h)
        http.post(f"{API}/ready-sites/branding",
                  json={"session_id": sid, "business_name": "TEST_LowCredit",
                        "logo_mode": "text"}, headers=h)
        feat_resp = http.post(f"{API}/ready-sites/features",
                              json={"session_id": sid,
                                    "enabled": ["menu", "cart", "checkout"]}, headers=h)
        assert feat_resp.json()["can_afford"] is False
        r = http.post(f"{API}/ready-sites/generate", json={"session_id": sid}, headers=h)
        assert r.status_code == 402


# -------- Generate → status → preview integration --------
class TestGenerationIntegration:
    """Heavier integration test. Polls up to 3 mins for generation completion."""

    def test_generate_status_preview_and_cleanup(self, http, owner_token):
        h = auth(owner_token)

        # Check owner credits
        me = http.get(f"{API}/auth/me", headers=h)
        if me.status_code != 200:
            pytest.skip("Cannot fetch /auth/me")
        credits_before = me.json().get("credits", 0)
        if credits_before < 40:
            pytest.skip(f"Owner has only {credits_before} credits")

        # Full wizard
        r = http.post(f"{API}/ready-sites/start", json={}, headers=h)
        sid = r.json()["session_id"]
        http.post(f"{API}/ready-sites/select-type",
                  json={"session_id": sid, "type_id": "restaurant"}, headers=h)
        http.post(f"{API}/ready-sites/select-pattern",
                  json={"session_id": sid, "pattern_id": "neon_crescent"}, headers=h)
        http.post(f"{API}/ready-sites/branding",
                  json={"session_id": sid, "business_name": "TEST_AutoGen",
                        "tagline": "اختبار آلي", "logo_mode": "text"}, headers=h)
        default_enabled = [f for f in [
            "menu", "cart", "checkout", "delivery", "pickup", "reservations",
            "gallery", "contact", "hours", "languages", "search", "filters"
        ]]
        feat_resp = http.post(f"{API}/ready-sites/features",
                              json={"session_id": sid, "enabled": default_enabled}, headers=h)
        assert feat_resp.json()["can_afford"]

        # Generate (background)
        gen = http.post(f"{API}/ready-sites/generate",
                        json={"session_id": sid}, headers=h, timeout=15)
        assert gen.status_code == 200, gen.text
        d = gen.json()
        assert d["ok"] is True
        assert d["phase"] == "generating"
        assert d["started"] is True

        # Poll status — max 3 min
        deadline = time.time() + 180
        final_phase = None
        last_error = None
        project_id = None
        while time.time() < deadline:
            time.sleep(5)
            s = http.get(f"{API}/ready-sites/status/{sid}", headers=h, timeout=15)
            assert s.status_code == 200, s.text
            sd = s.json()
            final_phase = sd.get("phase")
            last_error = sd.get("error")
            if final_phase == "done":
                project_id = sd.get("project_id")
                break
            if final_phase == "ready" and last_error:
                # generation failed; credits should be refunded
                break

        if final_phase != "done":
            pytest.fail(f"Generation did not complete. phase={final_phase} error={last_error}")

        assert project_id
        # Preview HTML
        pr = http.get(f"{API}/ready-sites/preview/{project_id}", timeout=15)
        assert pr.status_code == 200
        assert pr.headers.get("content-type", "").startswith("text/html")
        body = pr.text
        assert len(body) > 5000, f"HTML too small: {len(body)} bytes"
        assert "<html" in body.lower()
        assert "<style" in body.lower()
        assert "zitex.com" in body.lower()

        # Projects list contains this id
        plist = http.get(f"{API}/ready-sites/projects", headers=h, timeout=15)
        assert plist.status_code == 200
        ids = {p["id"] for p in plist.json()["projects"]}
        assert project_id in ids

        # Delete the project (cleanup)
        d = http.delete(f"{API}/ready-sites/project/{project_id}", headers=h, timeout=15)
        assert d.status_code == 200

        # Verify deleted
        g = http.get(f"{API}/ready-sites/project/{project_id}", headers=h)
        assert g.status_code == 404
