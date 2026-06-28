"""Paywall test suite for Continuation mode.

Verifies the $150/month subscription gate end-to-end at the unit level:
  • mark_first_update tool flips first_update_delivered=True
  • Idempotency: calling twice is a no-op
  • Subscription-locked tools refuse with PAYWALL_LOCKED after the flag flips
  • Read tools (list/read) keep working even when locked
  • Once continuation_unlocked=True, write tools work again
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from cryptography.fernet import Fernet


# ─── Fixtures ──────────────────────────────────────────────────────────
@pytest.fixture
def mock_db():
    db = MagicMock()
    db.freebuild_projects = MagicMock()
    db.freebuild_projects.find_one = AsyncMock()
    db.freebuild_projects.update_one = AsyncMock()
    db.continuation_audit_logs = MagicMock()
    db.continuation_audit_logs.insert_one = AsyncMock()
    return db


@pytest.fixture
def ctx_factory(mock_db):
    class _Ctx:
        db = mock_db
        user_id = "test-user"
        project_id = "test-pid"
    return _Ctx


@pytest.fixture
def fernet_key():
    """Ensure encryption is wired so _load_cred works in tests."""
    from backend.modules.freebuild import secure_credentials as sc
    key = Fernet.generate_key()
    os.environ["CONTINUATION_FERNET_KEY"] = key.decode()
    sc._FERNET = Fernet(key)
    return sc


# ─── mark_first_update behaviour ───────────────────────────────────────
@pytest.mark.asyncio
async def test_mark_first_update_flips_flag(mock_db, ctx_factory):
    from backend.modules.freebuild.continuation_tools import handle_mark_first_update
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},  # _guard_continuation_mode
        {"first_update_delivered": False, "continuation_unlocked": False},  # idempotency check
    ]
    res = await handle_mark_first_update(
        {"project_id": "test-pid", "summary": "استبدلت صورة البطل"}, ctx_factory(),
    )
    assert res["ok"] is True
    assert res["first_update_delivered"] is True
    assert res["monthly_price_usd"] == 150.0
    # update_one must have been called with the flag flip
    call_args = mock_db.freebuild_projects.update_one.call_args
    assert call_args is not None
    payload = call_args[0][1]["$set"]
    assert payload["first_update_delivered"] is True
    assert payload["first_update_summary"] == "استبدلت صورة البطل"


@pytest.mark.asyncio
async def test_mark_first_update_idempotent(mock_db, ctx_factory):
    from backend.modules.freebuild.continuation_tools import handle_mark_first_update
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"first_update_delivered": True, "continuation_unlocked": False},
    ]
    res = await handle_mark_first_update({"project_id": "test-pid", "summary": "x"}, ctx_factory())
    assert res["ok"] is True
    assert res["already_marked"] is True
    # No write should have happened
    mock_db.freebuild_projects.update_one.assert_not_called()


@pytest.mark.asyncio
async def test_mark_first_update_refuses_non_continuation(mock_db, ctx_factory):
    from backend.modules.freebuild.continuation_tools import handle_mark_first_update
    mock_db.freebuild_projects.find_one.return_value = {"mode": "regular"}
    res = await handle_mark_first_update({"project_id": "test-pid", "summary": "x"}, ctx_factory())
    assert res["ok"] is False
    assert "continuation" in res["error"].lower()


# ─── Paywall gate behaviour ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_propose_change_locked_after_first_update(mock_db, ctx_factory, tmp_path):
    """The core paywall: propose_sandbox_change must refuse after the flag is set."""
    from backend.modules.freebuild import continuation_tools as ct
    ct.SANDBOX_ROOT = tmp_path

    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},  # _guard_continuation_mode
        {"first_update_delivered": True, "continuation_unlocked": False},  # paywall guard
    ]
    res = await ct.handle_propose_sandbox_change(
        {"project_id": "test-pid", "path": "src/x.js", "new_content": "hacker code"},
        ctx_factory(),
    )
    assert res["ok"] is False
    assert res["error"] == "subscription_required"
    assert res["code"] == "PAYWALL_LOCKED"
    assert res["monthly_price_usd"] == 150.0
    assert "اشتراك" in res["message_ar"] or "150" in res["message_ar"]


@pytest.mark.asyncio
async def test_propose_change_works_when_unlocked(mock_db, ctx_factory, tmp_path):
    """After payment (continuation_unlocked=True), write tools work again."""
    from backend.modules.freebuild import continuation_tools as ct
    ct.SANDBOX_ROOT = tmp_path

    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"first_update_delivered": True, "continuation_unlocked": True},  # PAID
    ]
    res = await ct.handle_propose_sandbox_change(
        {"project_id": "test-pid", "path": "src/x.js", "new_content": "/* legitimate */"},
        ctx_factory(),
    )
    assert res["ok"] is True
    assert "wrote" in res


@pytest.mark.asyncio
async def test_propose_change_works_before_first_update(mock_db, ctx_factory, tmp_path):
    """The FREE first update path: before the flag, writes are allowed."""
    from backend.modules.freebuild import continuation_tools as ct
    ct.SANDBOX_ROOT = tmp_path

    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"first_update_delivered": False, "continuation_unlocked": False},
    ]
    res = await ct.handle_propose_sandbox_change(
        {"project_id": "test-pid", "path": "src/x.js", "new_content": "first edit"},
        ctx_factory(),
    )
    assert res["ok"] is True


@pytest.mark.asyncio
async def test_deploy_vps_locked_after_first_update(mock_db, ctx_factory, tmp_path):
    from backend.modules.freebuild import continuation_tools as ct
    ct.SANDBOX_ROOT = tmp_path
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"first_update_delivered": True, "continuation_unlocked": False},
    ]
    res = await ct.handle_deploy_to_live_vps({"project_id": "test-pid"}, ctx_factory())
    assert res["ok"] is False
    assert res["code"] == "PAYWALL_LOCKED"


@pytest.mark.asyncio
async def test_deploy_ftp_locked_after_first_update(mock_db, ctx_factory, tmp_path):
    from backend.modules.freebuild import continuation_tools as ct
    ct.SANDBOX_ROOT = tmp_path
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"first_update_delivered": True, "continuation_unlocked": False},
    ]
    res = await ct.handle_deploy_to_live_ftp({"project_id": "test-pid"}, ctx_factory())
    assert res["ok"] is False
    assert res["code"] == "PAYWALL_LOCKED"


@pytest.mark.asyncio
async def test_push_to_review_branch_locked_after_first_update(mock_db, ctx_factory, fernet_key, tmp_path):
    from backend.modules.freebuild import continuation_tools as ct
    ct.SANDBOX_ROOT = tmp_path
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"first_update_delivered": True, "continuation_unlocked": False},
    ]
    res = await ct.handle_push_to_review_branch(
        {"project_id": "test-pid", "commit_message": "test"}, ctx_factory(),
    )
    assert res["ok"] is False
    assert res["code"] == "PAYWALL_LOCKED"


# ─── Read tools remain unblocked ───────────────────────────────────────
@pytest.mark.asyncio
async def test_read_tools_not_blocked_by_paywall(tmp_path):
    """list_sandbox_files & read_sandbox_file must keep working when locked
    so the AI can still answer customer questions about what's in the sandbox."""
    from backend.modules.freebuild import continuation_tools as ct
    ct.SANDBOX_ROOT = tmp_path
    sandbox = ct._ensure_sandbox("test-pid")
    (sandbox / "x.txt").write_text("hello")

    # list_sandbox_files doesn't check paywall — should work
    res = await ct.handle_list_sandbox_files({"project_id": "test-pid"})
    assert res["ok"] is True
    assert any(f["path"] == "x.txt" for f in res["files"])

    res2 = await ct.handle_read_sandbox_file({"project_id": "test-pid", "path": "x.txt"})
    assert res2["ok"] is True
    assert res2["content"] == "hello"
