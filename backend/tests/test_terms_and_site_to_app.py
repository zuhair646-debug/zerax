"""Tests for Terms gate + Site-to-App converter modules."""
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-cinematic-hub-2.preview.emergentagent.com").rstrip("/")
LOGIN_EMAIL = "owner@zerax.com"
LOGIN_PASSWORD = "owner123"


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ───────── Terms module ─────────
class TestTerms:
    def test_content_websites_ar(self):
        r = requests.get(f"{BASE_URL}/api/terms/content", params={"section": "websites", "locale": "ar"}, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["section"] == "websites"
        assert d["locale"] == "ar"
        assert d["version"]
        assert d["title"] and d["intro"] and d["agreement"]
        assert isinstance(d["bullets"], list) and len(d["bullets"]) >= 5

    def test_content_apps_en(self):
        r = requests.get(f"{BASE_URL}/api/terms/content", params={"section": "apps", "locale": "en"}, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["locale"] == "en"
        assert len(d["bullets"]) >= 4
        assert d["title"]

    def test_content_invalid_section_404(self):
        r = requests.get(f"{BASE_URL}/api/terms/content", params={"section": "invalid_xyz"}, timeout=20)
        assert r.status_code == 404

    def test_accept_then_check_and_idempotent(self, auth_headers):
        # Use a section that owner@zerax.com may not yet have accepted - pick site_to_app
        section = "site_to_app"
        r = requests.post(f"{BASE_URL}/api/terms/accept", json={"section": section, "locale": "ar"}, headers=auth_headers, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        assert d["section"] == section
        version = d["version"]

        # check
        r2 = requests.get(f"{BASE_URL}/api/terms/check", params={"section": section}, headers=auth_headers, timeout=20)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["accepted"] is True
        assert d2["version"] == version
        assert d2["accepted_doc"]["version"] == version
        assert d2["accepted_doc"]["locale"]
        assert d2["accepted_doc"]["accepted_at"]

        # Idempotent: accept twice → still only 1 acceptance via my-acceptances
        r3 = requests.post(f"{BASE_URL}/api/terms/accept", json={"section": section, "locale": "ar"}, headers=auth_headers, timeout=20)
        assert r3.status_code == 200

        ml = requests.get(f"{BASE_URL}/api/terms/my-acceptances", headers=auth_headers, timeout=20)
        assert ml.status_code == 200
        items = ml.json()["items"]
        count = sum(1 for it in items if it["section"] == section and it["version"] == version)
        assert count == 1, f"expected idempotent (1 row), got {count}"

    def test_check_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/terms/check", params={"section": "websites"}, timeout=20)
        assert r.status_code in (401, 403)


# ───────── Site-to-App module ─────────
class TestSiteToApp:
    @pytest.fixture(scope="class")
    def scan_url(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/site-to-app/scan",
            json={"source": "url", "url": "https://example.com"},
            headers=auth_headers,
            timeout=60,
        )
        assert r.status_code == 200, f"scan url failed: {r.status_code} {r.text}"
        return r.json()

    def test_scan_url_shape(self, scan_url):
        d = scan_url
        assert "scan_id" in d
        assert d["source_label"]
        an = d["analysis"]
        assert "title" in an
        assert "lang" in an
        assert "nav_links" in an and isinstance(an["nav_links"], list)
        assert "images_count" in an
        f = an["features"]
        for k in ("ecommerce", "booking", "blog", "contact_form", "video", "auth"):
            assert k in f, f"missing feature key {k}"
            assert isinstance(f[k], bool)

    def test_scan_url_missing_url_400(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/site-to-app/scan",
            json={"source": "url"},
            headers=auth_headers,
            timeout=20,
        )
        assert r.status_code == 400

    def test_scan_invalid_source_400(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/site-to-app/scan",
            json={"source": "xyz"},
            headers=auth_headers,
            timeout=20,
        )
        assert r.status_code == 400

    def test_plan_with_scan(self, auth_headers, scan_url):
        r = requests.post(
            f"{BASE_URL}/api/site-to-app/plan",
            json={"scan_id": scan_url["scan_id"], "platform": "both", "tech_stack": "pwa"},
            headers=auth_headers,
            timeout=30,
        )
        assert r.status_code == 200, r.text
        plan = r.json()["plan"]
        assert plan["platform"] == "both"
        assert plan["tech_stack"] == "pwa"
        assert isinstance(plan["phases"], list) and len(plan["phases"]) >= 2
        titles = [p["title"] for p in plan["phases"]]
        assert "هيكل التطبيق" in titles, f"missing phase: {titles}"
        assert "الشاشة الرئيسية" in titles, f"missing phase: {titles}"
        assert "must_collect" in plan and isinstance(plan["must_collect"], list)
        assert "cant_auto_convert" in plan
        assert isinstance(plan["estimated_total_minutes"], int)

    def test_start_creates_project_with_app_mode(self, auth_headers, scan_url):
        r = requests.post(
            f"{BASE_URL}/api/site-to-app/start",
            json={"scan_id": scan_url["scan_id"], "platform": "both", "tech_stack": "pwa"},
            headers=auth_headers,
            timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        pid = d["project_id"]
        assert pid

        # Verify via freebuild-chat get
        gp = requests.get(f"{BASE_URL}/api/freebuild-chat/project/{pid}", headers=auth_headers, timeout=20)
        assert gp.status_code == 200, gp.text
        proj = gp.json()
        assert proj.get("mode") == "app", f"mode={proj.get('mode')}"
        assert proj.get("platform") == "both"
        assert proj.get("tech_stack") == "pwa"
        assert proj.get("site_to_app_scan_id") == scan_url["scan_id"]
        msgs = proj.get("messages") or []
        assert len(msgs) >= 1
        first = msgs[0]
        assert first["role"] == "assistant"
        assert first["content"].startswith("مرحبا بك في المحوّل"), f"got: {first['content'][:80]}"

    def test_scan_project_source(self, auth_headers):
        # Find an existing website project with current_html
        lst = requests.get(f"{BASE_URL}/api/freebuild-chat/projects", headers=auth_headers, timeout=20)
        if lst.status_code != 200:
            pytest.skip("cannot list projects")
        items = lst.json() if isinstance(lst.json(), list) else lst.json().get("projects", [])
        target = None
        for p in items:
            pid = p.get("id")
            if not pid:
                continue
            full = requests.get(f"{BASE_URL}/api/freebuild-chat/project/{pid}", headers=auth_headers, timeout=20)
            if full.status_code == 200 and full.json().get("current_html"):
                target = full.json()
                break
        if not target:
            pytest.skip("no website project with current_html found")
        r = requests.post(
            f"{BASE_URL}/api/site-to-app/scan",
            json={"source": "project", "project_id": target["id"]},
            headers=auth_headers,
            timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert "scan_id" in d
        assert d["source_label"].startswith("مشروع Zenrex:")

    def test_scan_requires_auth(self):
        r = requests.post(
            f"{BASE_URL}/api/site-to-app/scan",
            json={"source": "url", "url": "https://example.com"},
            timeout=20,
        )
        assert r.status_code in (401, 403)
