"""In-process unit tests for the Desktop Agent relay.

Tests the pure helper functions (no real WebSocket; uses a fake) so we get
deterministic, fast verification of pairing → command → response flow.

Run:
    cd /app && python -m pytest backend/tests/test_desktop_agent_relay.py -v
"""
import asyncio
import json
import sys

import pytest

sys.path.insert(0, "/app/backend")

from modules.freebuild.local_browser_relay import (
    create_desktop_pairing,
    is_desktop_agent_connected,
    send_command_to_desktop,
    _DESKTOP_ACTIVE_WS,
    _DESKTOP_PAIRINGS,
    _DESKTOP_PENDING,
)


class FakeWS:
    """Minimal stand-in for a Starlette WebSocket."""
    def __init__(self):
        self.sent = []
        self._auto_reply = None

    async def send_json(self, payload):
        self.sent.append(payload)
        # If we have an auto-reply registered, drive the response back immediately
        if self._auto_reply and payload.get("type") == "command":
            req_id = payload["request_id"]
            project_id = self._auto_reply["project_id"]
            fut = _DESKTOP_PENDING.get(project_id, {}).get(req_id)
            if fut and not fut.done():
                fut.set_result(self._auto_reply["payload"])


# ─── tests ───────────────────────────────────────────────────────────────────
def test_pairing_code_unique_and_valid_length():
    a = create_desktop_pairing("p1")
    b = create_desktop_pairing("p2")
    assert a["code"] != b["code"]
    assert len(a["code"]) == 6
    assert a["expires_in_seconds"] > 0


def test_not_connected_by_default():
    create_desktop_pairing("never_connected")
    assert is_desktop_agent_connected("never_connected") is False


@pytest.mark.asyncio
async def test_send_command_no_agent_returns_helpful_error():
    res = await send_command_to_desktop("p_none", "screenshot", {})
    assert res["ok"] is False
    assert res["error"] == "no_desktop_agent_connected"
    assert "نزّل" in res["hint"]


@pytest.mark.asyncio
async def test_send_command_roundtrip_with_fake_ws():
    project_id = "p_roundtrip"
    fake = FakeWS()
    fake._auto_reply = {
        "project_id": project_id,
        "payload": {"ok": True, "width": 1920, "height": 1080},
    }
    _DESKTOP_ACTIVE_WS[project_id] = fake
    _DESKTOP_PENDING.setdefault(project_id, {})
    try:
        res = await send_command_to_desktop(project_id, "screen_size", {})
        assert res["ok"] is True
        assert res["width"] == 1920
        # Verify the command was sent through the fake WS
        assert any(m.get("type") == "command" and m.get("action") == "screen_size"
                   for m in fake.sent)
    finally:
        _DESKTOP_ACTIVE_WS.pop(project_id, None)
        _DESKTOP_PENDING.pop(project_id, None)


@pytest.mark.asyncio
async def test_send_command_timeout():
    """When the agent never replies, the helper times out gracefully."""
    project_id = "p_timeout"

    class SilentWS(FakeWS):
        async def send_json(self, payload):
            self.sent.append(payload)
            # Don't reply — we want timeout

    fake = SilentWS()
    _DESKTOP_ACTIVE_WS[project_id] = fake
    _DESKTOP_PENDING.setdefault(project_id, {})

    # Monkeypatch a short timeout for this test
    import modules.freebuild.local_browser_relay as relay
    original = relay.DESKTOP_COMMAND_TIMEOUT_SECONDS
    relay.DESKTOP_COMMAND_TIMEOUT_SECONDS = 1
    try:
        res = await relay.send_command_to_desktop(project_id, "screenshot", {})
        assert res["ok"] is False
        assert "did not respond" in res["error"]
    finally:
        relay.DESKTOP_COMMAND_TIMEOUT_SECONDS = original
        _DESKTOP_ACTIVE_WS.pop(project_id, None)
        _DESKTOP_PENDING.pop(project_id, None)


# ─── tools layer ─────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_desktop_pair_tool():
    from modules.freebuild.desktop_agent_tools import desktop_pair

    class Ctx:
        project_id = "p_tool"

    res = await desktop_pair(Ctx(), {})
    assert res["ok"] is True
    assert len(res["code"]) == 6
    # Code charset must exclude 0/O/I/1
    for c in res["code"]:
        assert c not in "0OI1", f"invalid char {c} in code {res['code']}"
    assert "download_url" in res
    assert "/api/desktop-agent/download" in res["download_url"]
    # New: explicit verbatim instruction for the model
    assert "display_block" in res
    assert res["code"] in res["display_block"]
    assert "model_instruction" in res
    assert res["code"] in res["model_instruction"]


@pytest.mark.asyncio
async def test_desktop_status_tool_not_connected():
    from modules.freebuild.desktop_agent_tools import desktop_status

    class Ctx:
        project_id = "p_status_off"

    res = await desktop_status(Ctx(), {})
    assert res["ok"] is True
    assert res["connected"] is False


@pytest.mark.asyncio
async def test_desktop_act_tool_dispatches():
    from modules.freebuild.desktop_agent_tools import desktop_act
    project_id = "p_act"
    fake = FakeWS()
    fake._auto_reply = {"project_id": project_id, "payload": {"ok": True, "did": "click"}}
    _DESKTOP_ACTIVE_WS[project_id] = fake
    _DESKTOP_PENDING.setdefault(project_id, {})
    try:
        class Ctx:
            pass
        Ctx.project_id = project_id
        res = await desktop_act(Ctx(), {"action": "click", "params": {"x": 10, "y": 20}})
        assert res["ok"] is True
        assert res["action"] == "click"
        assert res["kind"] == "desktop_step"
    finally:
        _DESKTOP_ACTIVE_WS.pop(project_id, None)
        _DESKTOP_PENDING.pop(project_id, None)


def test_owner_only_includes_desktop_tools():
    from modules.freebuild.freebuild_agent import OWNER_ONLY_TOOL_NAMES, tools_for_user
    for name in ("desktop_pair", "desktop_status", "desktop_act", "desktop_screenshot"):
        assert name in OWNER_ONLY_TOOL_NAMES, f"{name} must be owner-only"

    owner_tools = {t["name"] for t in tools_for_user(is_owner=True)}
    customer_tools = {t["name"] for t in tools_for_user(is_owner=False)}
    assert "desktop_pair" in owner_tools
    assert "desktop_pair" not in customer_tools
    assert "desktop_act" not in customer_tools


def test_desktop_tool_schema_shape():
    """Anthropic tool schema must have name + description + input_schema."""
    from modules.freebuild.desktop_agent_tools import DESKTOP_TOOL_SCHEMAS
    assert len(DESKTOP_TOOL_SCHEMAS) >= 4
    for t in DESKTOP_TOOL_SCHEMAS:
        assert t["name"]
        assert t["description"]
        assert t["input_schema"]["type"] == "object"
