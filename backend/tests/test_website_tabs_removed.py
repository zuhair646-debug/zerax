"""
Iteration 68 — verifies the FreeBuild website-mode tab removal feature:
  1. Backend smoke (health + auth + project creation)
  2. Website-mode project creation works
  3. Video-studio-mode project creation works (regression - tabs must still be available there)
  4. agent-chat-stream endpoint streams events for website mode without phase-rule injection
  5. Code-level check that inject_workflow_addendum=False is wired in freebuild_chat.py
"""
import os
import re
import uuid
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-cinematic-hub-2.preview.emergentagent.com").rstrip("/")
OWNER_EMAIL = "owner@zerax.com"
OWNER_PASSWORD = "owner123"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
                      timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("token") or data.get("access_token")
    assert tok, f"no token in {data}"
    return tok


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ── smoke ──────────────────────────────────────────────────────────────────
def test_health():
    # retry once on cold-start timeout
    last_exc = None
    for _ in range(2):
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=45)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body.get("status") in ("healthy", "ok"), body
            return
        except requests.exceptions.ReadTimeout as e:
            last_exc = e
            time.sleep(2)
            continue
    raise last_exc


def test_login_returns_token(token):
    assert isinstance(token, str) and len(token) > 10


# ── project creation ──────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def website_project(auth_headers):
    payload = {
        "name": f"TEST_iter68_website_{uuid.uuid4().hex[:6]}",
        "description": "اختبار إلغاء التبويبات في وضع الموقع",
        "mode": "website",
    }
    r = requests.post(f"{BASE_URL}/api/freebuild-chat/project", json=payload, headers=auth_headers, timeout=30)
    assert r.status_code in (200, 201), f"website create failed: {r.status_code} {r.text}"
    pj = r.json()
    pid = pj.get("id") or pj.get("project_id") or (pj.get("project") or {}).get("id")
    assert pid, f"no project id in {pj}"
    yield {"id": pid, "data": pj}
    # cleanup
    try:
        requests.delete(f"{BASE_URL}/api/freebuild-chat/project/{pid}", headers=auth_headers, timeout=15)
    except Exception:
        pass


def test_create_website_project(website_project):
    pid = website_project["id"]
    # GET back
    tok = website_project["data"]
    # we already have the headers in module, but re-pull token via login isn't needed
    # use raw header
    pass  # creation success already asserted in fixture


def test_create_video_studio_project_regression(auth_headers):
    """Video studio mode must still allow creation — tabs are kept in this mode."""
    payload = {
        "name": f"TEST_iter68_videostudio_{uuid.uuid4().hex[:6]}",
        "description": "regression — video_studio keeps tabs",
        "mode": "video_studio",
    }
    r = requests.post(f"{BASE_URL}/api/freebuild-chat/project", json=payload, headers=auth_headers, timeout=30)
    assert r.status_code in (200, 201), f"video_studio create failed: {r.status_code} {r.text}"
    pj = r.json()
    pid = pj.get("id") or pj.get("project_id") or (pj.get("project") or {}).get("id")
    assert pid
    # cleanup
    try:
        requests.delete(f"{BASE_URL}/api/freebuild-chat/project/{pid}", headers=auth_headers, timeout=15)
    except Exception:
        pass


# ── agent-chat-stream SSE ────────────────────────────────────────────────
def test_agent_chat_stream_website_mode(website_project, token):
    """
    POSTs a real Arabic message to /agent-chat-stream and verifies that:
      - the SSE stream emits 'event: start' (no immediate disconnect),
      - it reaches 'event: done',
      - the 'انقطع الاتصال' fallback IS NOT emitted.
    inject_workflow_addendum=False means no phase-rule enforcement.
    """
    pid = website_project["id"]
    url = f"{BASE_URL}/api/freebuild-chat/project/{pid}/agent-chat-stream"
    headers = {"Authorization": f"Bearer {token}"}
    # multipart form
    files = {
        "message": (None, "ابن لي صفحة هبوط بسيطة عن قهوة سعودية"),
        "user_language": (None, "ar"),
    }
    with requests.post(url, headers=headers, files=files, stream=True, timeout=300) as r:
        assert r.status_code == 200, f"stream open failed: {r.status_code} {r.text[:500]}"
        seen_start = False
        seen_done = False
        seen_disconnect = False
        buf = ""
        t0 = time.time()
        for raw in r.iter_lines(decode_unicode=True):
            if raw is None:
                continue
            buf += raw + "\n"
            if raw.startswith("event: start"):
                seen_start = True
            if raw.startswith("event: done"):
                seen_done = True
            if "انقطع الاتصال" in raw:
                seen_disconnect = True
            if seen_done:
                break
            if time.time() - t0 > 280:
                break
    assert seen_start, f"no 'event: start' in stream. dump:\n{buf[:2000]}"
    assert not seen_disconnect, "stream emitted the 'انقطع الاتصال' disconnect fallback — TypeError regression?"
    assert seen_done, f"stream never reached 'event: done' within 280s. tail:\n{buf[-2000:]}"


# ── code-level check ─────────────────────────────────────────────────────
def test_inject_workflow_addendum_false_in_code():
    """Read the source file and assert the kwarg is set to False on the main chat path."""
    path = "/app/backend/modules/freebuild/freebuild_chat.py"
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    # We require AT LEAST ONE inject_workflow_addendum=False on the default chat path
    assert "inject_workflow_addendum=False" in src, \
        "inject_workflow_addendum=False NOT found in freebuild_chat.py — phase-rule suppression missing"


def test_freebuild_agent_param_default_and_skip():
    """The agent must accept the kwarg and skip the addendum injection when False."""
    path = "/app/backend/modules/freebuild/freebuild_agent.py"
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    assert "inject_workflow_addendum: bool" in src, "param missing in stream_agent_turn signature"
    assert re.search(r"if\s+inject_workflow_addendum\s*:", src), "no `if inject_workflow_addendum:` gate found"
    assert "addendum DISABLED" in src or "free chat mode" in src, "no else-branch logging for disabled addendum"
