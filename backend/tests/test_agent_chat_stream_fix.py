"""Iteration 67 — Verify the TypeError regression fix in agent-chat-stream.

The bug: in /app/backend/modules/freebuild/freebuild_chat.py around line 6695,
the default (mode != 'legacy_brain') path was calling stream_agent_turn(ctx=_ctx)
but the real signature is stream_agent_turn(..., ctx_holder=..., ...). Every
chat request raised TypeError and the SSE only emitted the disconnect message.

These tests confirm:
  1. POST /api/freebuild-chat/project/{pid}/agent-chat-stream with no mode field
     (so it takes the default path) does NOT raise TypeError and emits a proper
     SSE stream containing 'event: start' and a final 'event: done'.
  2. mode=lab also uses the same code path and succeeds.
  3. mode=legacy_brain still routes through the Brain orchestrator.
  4. After the chat completes, GET /freebuild-chat/project/{pid} shows the
     user+assistant messages persisted and agent_in_progress cleared.
"""

import os
import time
import json
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fall back to internal supervisor port for local pytest runs
    BASE_URL = "http://localhost:8001"

API = f"{BASE_URL}/api"

# Use owner@zerax.com (admin@zenrex.ai doesn't work on local preview per
# /app/memory/test_credentials.md).
OWNER_EMAIL = "owner@zerax.com"
OWNER_PASS = "owner123"


# ───────────────────────────── fixtures ─────────────────────────────


@pytest.fixture(scope="module")
def auth_token():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASS},
        timeout=15,
    )
    if r.status_code != 200:
        pytest.skip(f"login failed: {r.status_code} {r.text[:200]}")
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def fresh_project(auth_headers):
    """Create a brand new project for each test so streams don't collide."""
    body = {"name": f"TEST_iter67_{uuid.uuid4().hex[:6]}", "mode": "website"}
    r = requests.post(
        f"{API}/freebuild-chat/project",
        json=body,
        headers=auth_headers,
        timeout=15,
    )
    assert r.status_code == 200, f"create project failed: {r.status_code} {r.text[:300]}"
    proj = r.json()
    assert "id" in proj
    pid = proj["id"]
    yield pid
    # Cleanup: best-effort delete
    try:
        requests.delete(
            f"{API}/freebuild-chat/project/{pid}",
            headers=auth_headers,
            timeout=10,
        )
    except Exception:
        pass


# ───────────────────────────── helpers ─────────────────────────────


def _consume_sse(url, data, headers, max_seconds=180):
    """POST and read SSE chunks; returns (event_names, raw_text, status_code).

    Stops once we see 'event: done' OR after max_seconds OR on disconnect.
    """
    events = []
    raw_chunks = []
    start = time.time()
    with requests.post(
        url, data=data, headers=headers, stream=True, timeout=max_seconds
    ) as r:
        status = r.status_code
        if status != 200:
            return events, r.text, status
        for line in r.iter_lines(decode_unicode=True):
            if line is None:
                continue
            raw_chunks.append(line)
            if line.startswith("event: "):
                events.append(line[len("event: "):].strip())
                if events[-1] == "done":
                    # Read one or two more lines to capture the data payload
                    try:
                        for _ in range(3):
                            extra = next(r.iter_lines(decode_unicode=True))
                            if extra:
                                raw_chunks.append(extra)
                    except StopIteration:
                        pass
                    break
            if time.time() - start > max_seconds:
                break
    return events, "\n".join(raw_chunks), status


# ───────────────────────────── tests ─────────────────────────────


# ── TypeError regression: default mode must not crash ──────────────


class TestDefaultModeNoTypeError:
    """The exact failure mode the user reported: chat with no mode field."""

    def test_default_mode_emits_start_and_done(self, fresh_project, auth_headers):
        url = f"{API}/freebuild-chat/project/{fresh_project}/agent-chat-stream"
        # Multipart form, no `mode` field → default path
        data = {"message": "مرحبا", "user_language": "ar"}
        events, raw, status = _consume_sse(url, data, auth_headers, max_seconds=240)

        assert status == 200, f"expected 200, got {status}; body={raw[:400]}"
        # Must NOT contain the disconnect message that indicated the TypeError
        assert "انقطع الاتصال قبل ما أبدأ" not in raw, (
            "TypeError regression returned: stream-disconnect message present. "
            "raw=" + raw[:500]
        )
        # Required SSE event names
        assert "start" in events, f"missing 'start' event. events={events[:30]}"
        assert "done" in events, (
            f"missing 'done' event after {len(events)} events: {events[:40]}"
        )
        # Should have at least one provider/text_delta/tool to prove the agent ran
        assert any(
            e in events for e in ("provider", "text_delta", "tool", "thinking")
        ), f"no streaming model output detected. events={events[:40]}"


# ── mode=lab must also work (same code path) ───────────────────────


class TestLabModeWorks:
    def test_lab_mode_emits_start_and_done(self, fresh_project, auth_headers):
        url = f"{API}/freebuild-chat/project/{fresh_project}/agent-chat-stream"
        data = {"message": "مرحبا", "user_language": "ar", "mode": "lab"}
        events, raw, status = _consume_sse(url, data, auth_headers, max_seconds=240)
        assert status == 200, f"expected 200, got {status}; body={raw[:400]}"
        assert "انقطع الاتصال قبل ما أبدأ" not in raw
        assert "start" in events
        assert "done" in events, f"events={events[:40]}"


# ── mode=legacy_brain must still route through Brain ───────────────


class TestLegacyBrainStillRoutes:
    def test_legacy_brain_mode_emits_done(self, fresh_project, auth_headers):
        url = f"{API}/freebuild-chat/project/{fresh_project}/agent-chat-stream"
        data = {"message": "مرحبا", "user_language": "ar", "mode": "legacy_brain"}
        events, raw, status = _consume_sse(url, data, auth_headers, max_seconds=240)
        assert status == 200, f"expected 200, got {status}; body={raw[:400]}"
        assert "done" in events, (
            f"legacy_brain branch missing 'done'; events={events[:40]}"
        )


# ── persistence: messages saved + agent_in_progress cleared ────────


class TestPersistenceAfterChat:
    def test_messages_persisted_and_progress_cleared(self, fresh_project, auth_headers):
        # Run a default-mode turn first
        url = f"{API}/freebuild-chat/project/{fresh_project}/agent-chat-stream"
        data = {"message": "مرحبا", "user_language": "ar"}
        events, raw, status = _consume_sse(url, data, auth_headers, max_seconds=240)
        assert status == 200
        assert "done" in events, f"chat didn't complete; events={events[:40]}"

        # Give the post-stream persist block a moment
        time.sleep(2)

        # Fetch the project and validate the messages array
        r = requests.get(
            f"{API}/freebuild-chat/project/{fresh_project}",
            headers=auth_headers,
            timeout=15,
        )
        assert r.status_code == 200, f"GET project failed: {r.status_code} {r.text[:300]}"
        proj = r.json()
        msgs = proj.get("messages") or []
        # Should have at least the user message and one assistant reply
        roles = [m.get("role") for m in msgs]
        assert "user" in roles, f"user message not persisted. roles={roles}"
        assert "assistant" in roles, (
            f"assistant reply not persisted. roles={roles}"
        )
        # agent_in_progress must be cleared (false or missing)
        in_progress = proj.get("agent_in_progress")
        assert not in_progress, (
            f"agent_in_progress should be false after stream finished, got {in_progress!r}"
        )
