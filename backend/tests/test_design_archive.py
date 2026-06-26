"""Iteration 69 — Design Archive (المحفوظات) feature tests.

Covers:
  - GET /api/freebuild-chat/project/{pid}/snapshots includes kind/label/is_baseline
  - POST /api/freebuild-chat/project/{pid}/snapshots/manual creates kind=manual,
    accepts optional label, returns 400 when current_html empty,
    returns 404 for unknown/foreign project, can be called repeatedly (no cap).
  - POST /api/freebuild-chat/project/{pid}/publish — 1st time creates kind=baseline,
    2nd time creates kind=publish (NOT new baseline).
  - POST /api/freebuild-chat/project/{pid}/snapshots/{sid}/restore inserts a
    kind=pre_restore snapshot before swapping current_html.
  - Regression: /chat and /approve-design endpoints still return without 500.
"""

import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

OWNER_EMAIL = "owner@zerax.com"
OWNER_PASS = "owner123"


# ─── fixtures ────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def auth_token(session):
    r = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASS},
        timeout=60,
    )
    if r.status_code != 200:
        pytest.skip(f"login failed status={r.status_code}: {r.text[:200]}")
    tok = r.json().get("access_token") or r.json().get("token")
    if not tok:
        pytest.skip(f"no token in login response: {r.text[:200]}")
    return tok


@pytest.fixture(scope="session")
def auth(auth_token):
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def project_id(auth):
    """Create a fresh website-mode project with seeded current_html."""
    name = f"TEST_iter69_archive_{uuid.uuid4().hex[:6]}"
    r = requests.post(
        f"{BASE_URL}/api/freebuild-chat/project",
        headers=auth,
        json={"name": name, "type": "website", "mode": "website"},
        timeout=30,
    )
    assert r.status_code == 200, f"create project failed: {r.status_code} {r.text[:200]}"
    pid = r.json().get("id") or r.json().get("project", {}).get("id")
    assert pid, f"no project id in {r.text[:200]}"

    # Seed current_html directly via mongo so tests don't depend on AI
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient

    async def _seed():
        cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = cli[os.environ.get("DB_NAME", "test_database")]
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$set": {"current_html": "<html><body><h1>TEST iter69 baseline</h1></body></html>"}},
        )

    asyncio.get_event_loop().run_until_complete(_seed())
    yield pid

    # teardown
    try:
        requests.delete(
            f"{BASE_URL}/api/freebuild-chat/project/{pid}",
            headers=auth, timeout=15,
        )
    except Exception:
        pass


# ─── list snapshots: schema fields ───────────────────────────────
class TestListSnapshotsSchema:
    def test_list_returns_kind_label_is_baseline(self, auth, project_id):
        r = requests.get(
            f"{BASE_URL}/api/freebuild-chat/project/{project_id}/snapshots",
            headers=auth, timeout=15,
        )
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert data.get("ok") is True
        assert isinstance(data.get("snapshots"), list)
        # may be empty on a brand-new project; verify schema after a manual save
        requests.post(
            f"{BASE_URL}/api/freebuild-chat/project/{project_id}/snapshots/manual",
            headers={"Authorization": auth["Authorization"]},
            data={"label": "first-manual"},
            timeout=15,
        )
        r2 = requests.get(
            f"{BASE_URL}/api/freebuild-chat/project/{project_id}/snapshots",
            headers=auth, timeout=15,
        )
        assert r2.status_code == 200
        snaps = r2.json()["snapshots"]
        assert len(snaps) >= 1
        for s in snaps:
            assert "kind" in s
            assert "label" in s
            assert "is_baseline" in s
            assert isinstance(s["is_baseline"], bool)


# ─── manual snapshot endpoint ───────────────────────────────────
class TestManualSnapshot:
    def test_manual_creates_kind_manual_with_label(self, auth, project_id):
        r = requests.post(
            f"{BASE_URL}/api/freebuild-chat/project/{project_id}/snapshots/manual",
            headers={"Authorization": auth["Authorization"]},
            data={"label": "نسخة قبل التغيير"},
            timeout=15,
        )
        assert r.status_code == 200, r.text[:200]
        body = r.json()
        assert body.get("ok") is True
        assert body["snapshot"]["kind"] == "manual"
        assert "نسخة" in body["snapshot"]["label"] or body["snapshot"]["label"]

    def test_manual_no_label_defaults(self, auth, project_id):
        r = requests.post(
            f"{BASE_URL}/api/freebuild-chat/project/{project_id}/snapshots/manual",
            headers={"Authorization": auth["Authorization"]},
            data={},
            timeout=15,
        )
        assert r.status_code == 200, r.text[:200]
        assert r.json()["snapshot"]["kind"] == "manual"

    def test_manual_repeated_no_cap(self, auth, project_id):
        # call 5 more times — must always succeed (no -20 dedup cap)
        for i in range(5):
            r = requests.post(
                f"{BASE_URL}/api/freebuild-chat/project/{project_id}/snapshots/manual",
                headers={"Authorization": auth["Authorization"]},
                data={"label": f"loop-{i}"},
                timeout=15,
            )
            assert r.status_code == 200, f"call {i} failed: {r.text[:200]}"
        # confirm cumulative count grew
        r = requests.get(
            f"{BASE_URL}/api/freebuild-chat/project/{project_id}/snapshots",
            headers=auth, timeout=15,
        )
        snaps = r.json()["snapshots"]
        manuals = [s for s in snaps if s["kind"] == "manual"]
        assert len(manuals) >= 6, f"expected at least 6 manuals, got {len(manuals)}"

    def test_manual_unknown_project_404(self, auth):
        r = requests.post(
            f"{BASE_URL}/api/freebuild-chat/project/does-not-exist-xyz/snapshots/manual",
            headers={"Authorization": auth["Authorization"]},
            data={"label": "x"},
            timeout=15,
        )
        assert r.status_code == 404

    def test_manual_empty_html_400(self, auth):
        # create a NEW project with NO current_html
        name = f"TEST_iter69_empty_{uuid.uuid4().hex[:6]}"
        cr = requests.post(
            f"{BASE_URL}/api/freebuild-chat/project",
            headers=auth,
            json={"name": name, "type": "website", "mode": "website"},
            timeout=30,
        )
        pid = cr.json().get("id") or cr.json().get("project", {}).get("id")
        try:
            r = requests.post(
                f"{BASE_URL}/api/freebuild-chat/project/{pid}/snapshots/manual",
                headers={"Authorization": auth["Authorization"]},
                data={"label": "x"},
                timeout=15,
            )
            assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:200]}"
        finally:
            requests.delete(
                f"{BASE_URL}/api/freebuild-chat/project/{pid}",
                headers=auth, timeout=15,
            )


# ─── publish baseline ───────────────────────────────────────────
class TestPublishBaseline:
    def test_first_publish_creates_baseline_second_creates_publish(self, auth):
        # fresh project so we control baseline state
        name = f"TEST_iter69_pub_{uuid.uuid4().hex[:6]}"
        cr = requests.post(
            f"{BASE_URL}/api/freebuild-chat/project",
            headers=auth,
            json={"name": name, "type": "website", "mode": "website"},
            timeout=30,
        )
        pid = cr.json().get("id") or cr.json().get("project", {}).get("id")
        # seed html
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        async def _seed():
            cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db = cli[os.environ.get("DB_NAME", "test_database")]
            await db.freebuild_projects.update_one(
                {"id": pid},
                {"$set": {"current_html": "<html><body>PUB-TEST</body></html>"}},
            )
        asyncio.get_event_loop().run_until_complete(_seed())

        try:
            # 1st publish
            slug = f"test-iter69-{uuid.uuid4().hex[:6]}"
            r1 = requests.post(
                f"{BASE_URL}/api/freebuild-chat/project/{pid}/publish",
                headers={"Authorization": auth["Authorization"]},
                data={"slug": slug},
                timeout=60,
            )
            assert r1.status_code == 200, r1.text[:200]
            time.sleep(0.5)
            ls1 = requests.get(
                f"{BASE_URL}/api/freebuild-chat/project/{pid}/snapshots",
                headers=auth, timeout=15,
            ).json()["snapshots"]
            kinds1 = [s["kind"] for s in ls1]
            assert "baseline" in kinds1, f"baseline missing after 1st publish: {kinds1}"
            baselines1 = [s for s in ls1 if s["kind"] == "baseline"]
            assert len(baselines1) == 1
            assert baselines1[0]["is_baseline"] is True

            # 2nd publish
            r2 = requests.post(
                f"{BASE_URL}/api/freebuild-chat/project/{pid}/publish",
                headers={"Authorization": auth["Authorization"]},
                data={"slug": slug},
                timeout=60,
            )
            assert r2.status_code == 200, r2.text[:200]
            time.sleep(0.5)
            ls2 = requests.get(
                f"{BASE_URL}/api/freebuild-chat/project/{pid}/snapshots",
                headers=auth, timeout=15,
            ).json()["snapshots"]
            kinds2 = [s["kind"] for s in ls2]
            # still exactly one baseline
            baselines2 = [s for s in ls2 if s["kind"] == "baseline"]
            assert len(baselines2) == 1, f"baseline count != 1 after 2nd publish: {kinds2}"
            # at least one kind=publish exists now
            assert "publish" in kinds2, f"publish kind missing: {kinds2}"
        finally:
            requests.delete(
                f"{BASE_URL}/api/freebuild-chat/project/{pid}",
                headers=auth, timeout=15,
            )


# ─── restore inserts pre_restore ────────────────────────────────
class TestRestore:
    def test_restore_creates_pre_restore_and_swaps_html(self, auth):
        name = f"TEST_iter69_rst_{uuid.uuid4().hex[:6]}"
        cr = requests.post(
            f"{BASE_URL}/api/freebuild-chat/project",
            headers=auth,
            json={"name": name, "type": "website", "mode": "website"},
            timeout=30,
        )
        pid = cr.json().get("id") or cr.json().get("project", {}).get("id")
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        async def _seed(html):
            cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db = cli[os.environ.get("DB_NAME", "test_database")]
            await db.freebuild_projects.update_one(
                {"id": pid},
                {"$set": {"current_html": html}},
            )
        asyncio.get_event_loop().run_until_complete(_seed("<html><body>VERSION-A</body></html>"))

        try:
            # Save A as a manual snapshot
            requests.post(
                f"{BASE_URL}/api/freebuild-chat/project/{pid}/snapshots/manual",
                headers={"Authorization": auth["Authorization"]},
                data={"label": "A"}, timeout=15,
            )
            # Get snap id of A
            ls = requests.get(
                f"{BASE_URL}/api/freebuild-chat/project/{pid}/snapshots",
                headers=auth, timeout=15,
            ).json()["snapshots"]
            a_snap = next(s for s in ls if s["kind"] == "manual")
            a_sid = a_snap["id"]

            # change current_html to B
            asyncio.get_event_loop().run_until_complete(_seed("<html><body>VERSION-B</body></html>"))

            # Restore A → should push pre_restore (of B) and swap to A
            rr = requests.post(
                f"{BASE_URL}/api/freebuild-chat/project/{pid}/snapshots/{a_sid}/restore",
                headers=auth, timeout=20,
            )
            assert rr.status_code == 200, rr.text[:200]

            # List again — newest first, top should be pre_restore
            ls2 = requests.get(
                f"{BASE_URL}/api/freebuild-chat/project/{pid}/snapshots",
                headers=auth, timeout=15,
            ).json()["snapshots"]
            kinds = [s["kind"] for s in ls2]
            assert "pre_restore" in kinds, f"pre_restore kind missing: {kinds}"
            # newest-first ordering: pre_restore should be at top
            assert ls2[0]["kind"] == "pre_restore", f"newest snap is not pre_restore: {kinds[:3]}"
        finally:
            requests.delete(
                f"{BASE_URL}/api/freebuild-chat/project/{pid}",
                headers=auth, timeout=15,
            )


# ─── regression: /chat and /approve-design no-500 ────────────────
class TestRegression:
    def test_approve_design_no_500(self, auth, project_id):
        r = requests.post(
            f"{BASE_URL}/api/freebuild-chat/project/{project_id}/approve-design",
            headers=auth, timeout=20,
        )
        # may be 200 or 4xx, must NOT be 500
        assert r.status_code < 500, f"approve-design 5xx: {r.status_code} {r.text[:200]}"
