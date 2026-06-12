"""Regression tests for Phase 5 (Browser Use) tools.

Run with: cd /app/backend && pytest tests/test_browser_use_tools.py -v
"""
import os
import sys
import pytest
import pytest_asyncio
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")

from modules.freebuild.browser_use_tools import (
    PHASE5_TOOL_SCHEMAS,
    PHASE5_TOOL_NAMES,
    browser_start,
    browser_goto,
    browser_screenshot,
    browser_save_session,
    browser_list_accounts,
    browser_close,
    _SESSIONS,
    _save_storage_state_encrypted,
    _load_storage_state,
)
from modules.freebuild.freebuild_agent import (
    TOOLS_SCHEMA,
    TOOL_LABELS_AR,
    FreeBuildToolContext,
    _exec_tool,
)

PROJ_ID = "test_browser_pytest"


@pytest_asyncio.fixture
async def db():
    import motor.motor_asyncio
    client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGO_URL"])
    d = client[os.environ.get("DB_NAME", "zerax")]
    yield d
    await d.freebuild_browser_sessions.delete_many({"project_id": PROJ_ID})
    client.close()


@pytest.fixture
def ctx(db):
    return FreeBuildToolContext({"id": PROJ_ID, "current_html": ""}, db=db)


@pytest_asyncio.fixture(autouse=True)
async def cleanup_sessions():
    yield
    # Close any leaked sessions from tests
    for sid in list(_SESSIONS.keys()):
        try:
            s = _SESSIONS.get(sid)
            if s and s.get("context"):
                await s["context"].close()
            if s and s.get("browser"):
                await s["browser"].close()
            if s and s.get("playwright"):
                await s["playwright"].stop()
        except Exception:
            pass
        _SESSIONS.pop(sid, None)


# ─── Wiring ────────────────────────────────────────────────────────────────
def test_phase5_schemas_registered():
    master = {t["name"] for t in TOOLS_SCHEMA}
    for t in PHASE5_TOOL_SCHEMAS:
        assert t["name"] in master


def test_phase5_labels_registered():
    for n in PHASE5_TOOL_NAMES:
        assert n in TOOL_LABELS_AR


def test_phase5_tools_async_routing(ctx):
    for n in PHASE5_TOOL_NAMES:
        s = _exec_tool(ctx, n, {})
        assert s.get("__async__") is True


# ─── Storage state encryption round-trip ───────────────────────────────────
@pytest.mark.asyncio
async def test_storage_state_encryption_roundtrip(db):
    sample_state = {"cookies": [{"name": "x", "value": "y", "domain": "example.com"}], "origins": []}
    ok = await _save_storage_state_encrypted(db, PROJ_ID, "test_acct", sample_state)
    assert ok is True
    loaded = await _load_storage_state(db, PROJ_ID, "test_acct")
    assert loaded == sample_state


@pytest.mark.asyncio
async def test_load_missing_storage_state(db):
    loaded = await _load_storage_state(db, PROJ_ID, "nonexistent_acct")
    assert loaded is None


# ─── browser_list_accounts ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_browser_list_accounts_empty(ctx):
    r = await browser_list_accounts(ctx, {})
    assert r["ok"] is True
    assert isinstance(r["accounts"], list)


@pytest.mark.asyncio
async def test_browser_list_accounts_after_save(ctx, db):
    await _save_storage_state_encrypted(db, PROJ_ID, "acc1", {"cookies": [], "origins": []})
    await _save_storage_state_encrypted(db, PROJ_ID, "acc2", {"cookies": [], "origins": []})
    r = await browser_list_accounts(ctx, {})
    assert r["ok"] is True
    labels = [a["account_label"] for a in r["accounts"]]
    assert "acc1" in labels and "acc2" in labels


# ─── Basic browser session lifecycle ───────────────────────────────────────
@pytest.mark.asyncio
async def test_browser_start_and_close(ctx):
    r = await browser_start(ctx, {"headless": True})
    assert r["ok"] is True, r.get("error")
    sid = r["session_id"]
    assert sid.startswith("br_")
    assert sid in _SESSIONS

    # Take a screenshot
    s = await browser_screenshot(ctx, {"session_id": sid})
    assert s["ok"] is True

    # Close
    c = await browser_close(ctx, {"session_id": sid})
    assert c["ok"] is True
    assert sid not in _SESSIONS


@pytest.mark.asyncio
async def test_browser_goto_real_url(ctx):
    r = await browser_start(ctx, {"headless": True})
    assert r["ok"] is True
    sid = r["session_id"]
    g = await browser_goto(ctx, {"session_id": sid, "url": "https://example.com", "wait_seconds": 1})
    assert g["ok"] is True, g.get("error")
    assert "example" in g["final_url"].lower()
    assert g["title"]
    assert g["screenshot_b64"]
    await browser_close(ctx, {"session_id": sid})


@pytest.mark.asyncio
async def test_browser_save_session_after_visit(ctx, db):
    r = await browser_start(ctx, {"headless": True})
    sid = r["session_id"]
    await browser_goto(ctx, {"session_id": sid, "url": "https://example.com", "wait_seconds": 1})
    # Save session
    save = await browser_save_session(ctx, {"session_id": sid, "account_label": "example_acct"})
    assert save["ok"] is True
    # Verify persisted
    doc = await db.freebuild_browser_sessions.find_one({"project_id": PROJ_ID, "account_label": "example_acct"})
    assert doc is not None
    assert doc.get("storage_enc")
    await browser_close(ctx, {"session_id": sid})


@pytest.mark.asyncio
async def test_browser_start_loads_saved_session(ctx, db):
    # 1. Start + save a session
    r = await browser_start(ctx, {"headless": True})
    sid1 = r["session_id"]
    await browser_goto(ctx, {"session_id": sid1, "url": "https://example.com", "wait_seconds": 1})
    await browser_save_session(ctx, {"session_id": sid1, "account_label": "reload_test"})
    await browser_close(ctx, {"session_id": sid1})

    # 2. Start new session WITH the saved label
    r2 = await browser_start(ctx, {"account_label": "reload_test", "headless": True})
    assert r2["ok"] is True
    assert r2["session_loaded_from_save"] is True
    await browser_close(ctx, {"session_id": r2["session_id"]})


@pytest.mark.asyncio
async def test_browser_goto_requires_valid_session(ctx):
    r = await browser_goto(ctx, {"session_id": "nonexistent_sid", "url": "https://example.com"})
    assert r["ok"] is False
    assert "session" in r["error"].lower()


@pytest.mark.asyncio
async def test_browser_save_requires_label(ctx):
    r = await browser_start(ctx, {"headless": True})
    sid = r["session_id"]
    s = await browser_save_session(ctx, {"session_id": sid, "account_label": ""})
    assert s["ok"] is False
    await browser_close(ctx, {"session_id": sid})


@pytest.mark.asyncio
async def test_session_isolated_by_project(ctx, db):
    """Session from project A cannot be touched by project B."""
    r = await browser_start(ctx, {"headless": True})
    sid = r["session_id"]
    # Try to use the session from a different project ctx
    other_ctx = FreeBuildToolContext({"id": "other_project_xyz", "current_html": ""}, db=db)
    g = await browser_goto(other_ctx, {"session_id": sid, "url": "https://example.com"})
    assert g["ok"] is False
    assert "not belong" in g["error"].lower() or "not in this project" in g["error"].lower()
    await browser_close(ctx, {"session_id": sid})
