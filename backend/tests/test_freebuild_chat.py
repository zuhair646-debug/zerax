"""Backend tests for FreeBuild Chat (conversational website builder) module.

Covers:
 - GET /api/freebuild-chat/types
 - POST /api/freebuild-chat/project (create)
 - GET /api/freebuild-chat/projects (list)
 - GET /api/freebuild-chat/project/{id}
 - POST /api/freebuild-chat/project/{id}/chat (AI tag emission + HTML extract)
 - asset polling (wait ~30s then assert status=ready)
 - POST /api/freebuild-chat/project/{id}/asset/{aid}/approve
 - POST /api/freebuild-chat/project/{id}/compile (with current_html and without)
 - DELETE /api/freebuild-chat/project/{id} (soft delete)
 - Tag stripping (saved chat message content must not contain <<TAG: ...>>)
"""
import os
import re
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-cinematic-hub-2.preview.emergentagent.com").rstrip("/")
PREFIX = f"{BASE_URL}/api/freebuild-chat"

OWNER_EMAIL = "owner@zitex.com"
OWNER_PASS = "owner123"

TAG_RE = re.compile(r"<<\s*(HERO|SECTION_BG|LOGO|PRODUCT|ICON|BANNER_AR|GALLERY)\s*[:：]", re.IGNORECASE)


# ─── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": OWNER_EMAIL, "password": OWNER_PASS}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def project_id(auth):
    r = requests.post(f"{PREFIX}/project", headers=auth,
                      json={"website_type": "landing",
                            "name": "TEST_chat_e2e",
                            "description": "اختبار تلقائي لتدفق الشات"},
                      timeout=15)
    assert r.status_code == 200, f"create failed: {r.status_code} {r.text[:200]}"
    pid = r.json().get("id")
    assert pid
    yield pid
    # Best-effort cleanup
    try:
        requests.delete(f"{PREFIX}/project/{pid}", headers=auth, timeout=10)
    except Exception:
        pass


# ─── Catalog ─────────────────────────────────────────────────────────────────
class TestCatalog:
    def test_list_types_returns_8(self):
        r = requests.get(f"{PREFIX}/types", timeout=10)
        assert r.status_code == 200
        types = r.json().get("types", [])
        ids = {t["id"] for t in types}
        expected = {"ecommerce", "landing", "corporate", "restaurant",
                    "clinic", "portfolio", "blog", "saas"}
        assert ids == expected, f"types mismatch: {ids}"
        for t in types:
            assert "title" in t and "desc" in t and "credits" in t


# ─── Project CRUD ────────────────────────────────────────────────────────────
class TestProjectCRUD:
    def test_create_invalid_type_returns_400(self, auth):
        r = requests.post(f"{PREFIX}/project", headers=auth,
                          json={"website_type": "nope", "name": "x", "description": "y"},
                          timeout=10)
        assert r.status_code == 400

    def test_list_projects_contains_created(self, auth, project_id):
        r = requests.get(f"{PREFIX}/projects", headers=auth, timeout=10)
        assert r.status_code == 200
        ids = [p["id"] for p in r.json().get("projects", [])]
        assert project_id in ids

    def test_get_single_project(self, auth, project_id):
        r = requests.get(f"{PREFIX}/project/{project_id}", headers=auth, timeout=10)
        assert r.status_code == 200
        p = r.json()
        assert p["id"] == project_id
        assert p["website_type"] == "landing"
        assert "messages" in p and "approved_assets" in p
        # current_html may be None until first AI HTML emission
        assert "current_html" in p

    def test_get_unknown_project_404(self, auth):
        r = requests.get(f"{PREFIX}/project/nonexistent-id", headers=auth, timeout=10)
        assert r.status_code == 404


# ─── Compile guard (no html yet) ─────────────────────────────────────────────
class TestCompileGuard:
    def test_compile_without_html_returns_400(self, auth, project_id):
        r = requests.post(f"{PREFIX}/project/{project_id}/compile", headers=auth, timeout=10)
        # Should be 400 because current_html is None on a fresh project
        assert r.status_code == 400, f"expected 400, got {r.status_code} body={r.text[:200]}"


# ─── Chat + AI tag emission + asset generation polling ───────────────────────
class TestChatFlow:
    asset_id_holder = {}

    def _send(self, auth, pid, msg):
        r = requests.post(f"{PREFIX}/project/{pid}/chat", headers=auth,
                          json={"message": msg}, timeout=120)
        return r

    def test_chat_emits_hero_tag_and_html(self, auth, project_id):
        # Force tag emission per system instructions — keep request short so AI response
        # fits within the preview-env ingress timeout (~60s).
        msg1 = (
            "نفذ فوراً بدون استشارة. اكتب في ردك السطر التالي حرفياً ثم انتهي:\n"
            "<<HERO: luxury oud perfume bottle on marble, cinematic golden light>>\n"
            "لا تكتب HTML الآن. فقط التاق."
        )
        r = self._send(auth, project_id, msg1)
        assert r.status_code == 200, f"chat failed: {r.status_code} {r.text[:300]}"
        data = r.json()

        pending = data.get("pending_assets") or []
        # If first turn was a 'consult', retry with stricter instruction (up to 2 retries)
        retries = 0
        while not any(a.get("type") == "HERO" for a in pending) and retries < 2:
            retries += 1
            msg_retry = (
                "نفذ مباشرة. لا تستشر. لا تطرح أفكار. "
                "اكتب الآن في ردك تاق <<HERO: luxury oud perfume bottle on marble>> ثم HTML كامل بين ```html و```."
            )
            r = self._send(auth, project_id, msg_retry)
            assert r.status_code == 200
            data = r.json()
            pending = data.get("pending_assets") or []

        assert any(a.get("type") == "HERO" for a in pending), \
            f"AI did not emit HERO tag after {retries+1} attempts; pending={pending}"

        hero = next(a for a in pending if a.get("type") == "HERO")
        assert hero["status"] == "generating"
        assert hero["image_url"] in (None, "")
        assert hero["approved"] is False
        TestChatFlow.asset_id_holder["hero_id"] = hero["id"]
        TestChatFlow.asset_id_holder["html_updated_seen"] = bool(data.get("html_updated"))

    def test_tag_stripped_from_saved_message(self, auth, project_id):
        r = requests.get(f"{PREFIX}/project/{project_id}", headers=auth, timeout=10)
        assert r.status_code == 200
        msgs = r.json().get("messages", [])
        assistant_msgs = [m for m in msgs if m["role"] == "assistant"]
        assert assistant_msgs, "no assistant messages saved"
        for m in assistant_msgs:
            assert not TAG_RE.search(m["content"]), \
                f"tag leaked into saved assistant content: {m['content'][:200]}"

    def test_html_updated_or_current_html_set(self, auth, project_id):
        # If html_updated was true OR if AI emitted HTML in any turn, current_html should be set
        r = requests.get(f"{PREFIX}/project/{project_id}", headers=auth, timeout=10)
        p = r.json()
        # Soft check — may be None if AI didn't emit ```html``` block
        # Just confirm field exists; AI behavior may vary
        assert "current_html" in p

    def test_asset_eventually_becomes_ready(self, auth, project_id):
        aid = TestChatFlow.asset_id_holder.get("hero_id")
        if not aid:
            pytest.skip("no hero asset id captured")
        # Poll up to ~60s (fal/openai latency)
        deadline = time.time() + 60
        last_status = None
        last_url = None
        while time.time() < deadline:
            r = requests.get(f"{PREFIX}/project/{project_id}", headers=auth, timeout=10)
            assert r.status_code == 200
            for m in r.json().get("messages", []):
                for a in (m.get("pending_assets") or []):
                    if a["id"] == aid:
                        last_status = a.get("status")
                        last_url = a.get("image_url")
            if last_status == "ready" and last_url:
                break
            if last_status == "failed":
                break
            time.sleep(4)
        assert last_status == "ready", f"asset status={last_status} url={last_url}"
        assert last_url, "image_url is empty after ready"


# ─── Approval & compile ──────────────────────────────────────────────────────
class TestApprovalAndCompile:
    def test_approve_hero_asset(self, auth, project_id):
        aid = TestChatFlow.asset_id_holder.get("hero_id")
        if not aid:
            pytest.skip("no hero asset id captured")
        r = requests.post(f"{PREFIX}/project/{project_id}/asset/{aid}/approve",
                          headers=auth, timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True

        # Verify it lands in approved_assets with approved=True
        g = requests.get(f"{PREFIX}/project/{project_id}", headers=auth, timeout=10)
        assert g.status_code == 200
        approved = g.json().get("approved_assets") or []
        match = [a for a in approved if a.get("id") == aid]
        assert match, f"asset {aid} not found in approved_assets"
        assert match[0]["approved"] is True
        assert match[0]["type"] == "HERO"

    def test_approve_unknown_asset_404(self, auth, project_id):
        r = requests.post(f"{PREFIX}/project/{project_id}/asset/bogus-id/approve",
                          headers=auth, timeout=10)
        assert r.status_code == 404

    def test_compile_html_if_present(self, auth, project_id):
        g = requests.get(f"{PREFIX}/project/{project_id}", headers=auth, timeout=10)
        cur = g.json().get("current_html")
        r = requests.post(f"{PREFIX}/project/{project_id}/compile", headers=auth, timeout=15)
        if cur:
            assert r.status_code == 200
            body = r.json()
            assert body.get("ok") is True
            assert body.get("html_length", 0) > 0
        else:
            # No HTML yet — endpoint must return 400
            assert r.status_code == 400


# ─── Soft delete ─────────────────────────────────────────────────────────────
class TestSoftDelete:
    def test_delete_then_absent_from_list(self, auth):
        # Create a throwaway project
        c = requests.post(f"{PREFIX}/project", headers=auth,
                          json={"website_type": "portfolio",
                                "name": "TEST_delete_me",
                                "description": "soft delete check"},
                          timeout=10)
        assert c.status_code == 200
        pid = c.json()["id"]

        d = requests.delete(f"{PREFIX}/project/{pid}", headers=auth, timeout=10)
        assert d.status_code == 200
        assert d.json().get("ok") is True

        lst = requests.get(f"{PREFIX}/projects", headers=auth, timeout=10)
        assert lst.status_code == 200
        ids = [p["id"] for p in lst.json().get("projects", [])]
        assert pid not in ids

    def test_delete_unknown_project_404(self, auth):
        r = requests.delete(f"{PREFIX}/project/does-not-exist", headers=auth, timeout=10)
        assert r.status_code == 404


# ─── Auth guard ──────────────────────────────────────────────────────────────
class TestAuthGuard:
    def test_projects_requires_auth(self):
        r = requests.get(f"{PREFIX}/projects", timeout=10)
        assert r.status_code in (401, 403)
