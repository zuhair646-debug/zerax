"""Tests for the 6 gap-closing tools added during the second audit pass:
delete_sandbox_file, move_sandbox_file, apply_patch,
get_continuation_status, inspect_saved_credentials, read_continuation_audit.
"""
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from cryptography.fernet import Fernet

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/backend")


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.freebuild_projects = MagicMock()
    db.freebuild_projects.find_one = AsyncMock()
    db.freebuild_projects.update_one = AsyncMock()
    db.continuation_audit_logs = MagicMock()
    db.continuation_audit_logs.insert_one = AsyncMock()
    db.continuation_audit_logs.find = MagicMock()
    return db


@pytest.fixture
def ctx_factory(mock_db):
    class _Ctx:
        db = mock_db
        user_id = "test-user"
        project_id = "test-pid"
    return _Ctx


# ─── delete_sandbox_file ───────────────────────────────────────────
@pytest.mark.asyncio
async def test_delete_file_works_when_unlocked(mock_db, ctx_factory, tmp_path):
    from backend.modules.freebuild import continuation_tools as ct
    from backend.modules.freebuild.continuation_app_tools import handle_delete_sandbox_file
    ct.SANDBOX_ROOT = tmp_path
    sandbox = ct._ensure_sandbox("test-pid")
    (sandbox / "x.txt").write_text("delete me")
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"first_update_delivered": False, "continuation_unlocked": False},  # no paywall yet
    ]
    res = await handle_delete_sandbox_file({"project_id": "test-pid", "path": "x.txt"}, ctx_factory())
    assert res["ok"] is True
    assert res["deleted"] == "x.txt"
    assert not (sandbox / "x.txt").exists()


@pytest.mark.asyncio
async def test_delete_file_blocked_by_paywall(mock_db, ctx_factory, tmp_path):
    from backend.modules.freebuild import continuation_tools as ct
    from backend.modules.freebuild.continuation_app_tools import handle_delete_sandbox_file
    ct.SANDBOX_ROOT = tmp_path
    sandbox = ct._ensure_sandbox("test-pid")
    (sandbox / "x.txt").write_text("dont delete me")
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"first_update_delivered": True, "continuation_unlocked": False},  # locked
    ]
    res = await handle_delete_sandbox_file({"project_id": "test-pid", "path": "x.txt"}, ctx_factory())
    assert res["ok"] is False
    assert res["code"] == "PAYWALL_LOCKED"
    assert (sandbox / "x.txt").exists(), "file must NOT be deleted when locked"


# ─── move_sandbox_file ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_move_file_renames(mock_db, ctx_factory, tmp_path):
    from backend.modules.freebuild import continuation_tools as ct
    from backend.modules.freebuild.continuation_app_tools import handle_move_sandbox_file
    ct.SANDBOX_ROOT = tmp_path
    sandbox = ct._ensure_sandbox("test-pid")
    (sandbox / "old.txt").write_text("hello")
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"first_update_delivered": False, "continuation_unlocked": False},
    ]
    res = await handle_move_sandbox_file(
        {"project_id": "test-pid", "source": "old.txt", "destination": "new.txt"},
        ctx_factory(),
    )
    assert res["ok"] is True
    assert (sandbox / "new.txt").exists()
    assert not (sandbox / "old.txt").exists()


@pytest.mark.asyncio
async def test_move_refuses_destination_exists(mock_db, ctx_factory, tmp_path):
    from backend.modules.freebuild import continuation_tools as ct
    from backend.modules.freebuild.continuation_app_tools import handle_move_sandbox_file
    ct.SANDBOX_ROOT = tmp_path
    sandbox = ct._ensure_sandbox("test-pid")
    (sandbox / "src.txt").write_text("a")
    (sandbox / "dst.txt").write_text("b")
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"first_update_delivered": False, "continuation_unlocked": False},
    ]
    res = await handle_move_sandbox_file(
        {"project_id": "test-pid", "source": "src.txt", "destination": "dst.txt"},
        ctx_factory(),
    )
    assert res["ok"] is False
    assert res["error"] == "destination_exists"


# ─── apply_patch ──────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_apply_patch_basic(mock_db, ctx_factory, tmp_path):
    from backend.modules.freebuild import continuation_tools as ct
    from backend.modules.freebuild.continuation_app_tools import handle_apply_patch
    ct.SANDBOX_ROOT = tmp_path
    sandbox = ct._ensure_sandbox("test-pid")
    target = sandbox / "code.py"
    target.write_text("def hello():\n    print('hi')\n")
    patch = (
        "--- a/code.py\n"
        "+++ b/code.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def hello():\n"
        "-    print('hi')\n"
        "+    print('hello world')\n"
    )
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"first_update_delivered": False, "continuation_unlocked": False},
    ]
    res = await handle_apply_patch(
        {"project_id": "test-pid", "path": "code.py", "patch_text": patch},
        ctx_factory(),
    )
    assert res["ok"] is True, f"patch failed: {res}"
    assert "hello world" in target.read_text()


# ─── get_continuation_status ──────────────────────────────────────
@pytest.mark.asyncio
async def test_get_status_returns_paywall_flag(mock_db, ctx_factory):
    from backend.modules.freebuild.continuation_app_tools import handle_get_continuation_status
    mock_db.freebuild_projects.find_one.return_value = {
        "mode": "continuation", "project_kind": "app", "app_kind": "flutter",
        "first_update_delivered": True, "continuation_unlocked": False,
        "continuation_sandbox": {"file_count": 100},
        "continuation_credentials": {"GITHUB_TOKEN": {"ciphertext": "x"}},
        "continuation_subscription_monthly_usd": 150.0,
    }
    res = await handle_get_continuation_status({"project_id": "test-pid"}, ctx_factory())
    assert res["ok"] is True
    assert res["project_kind"] == "app"
    assert res["app_kind"] == "flutter"
    assert res["paywall_active"] is True
    assert res["sandbox_ready"] is True
    assert "GITHUB_TOKEN" in res["saved_credential_keys"]


@pytest.mark.asyncio
async def test_get_status_refuses_unknown_project(mock_db, ctx_factory):
    from backend.modules.freebuild.continuation_app_tools import handle_get_continuation_status
    mock_db.freebuild_projects.find_one.return_value = None
    res = await handle_get_continuation_status({"project_id": "test-pid"}, ctx_factory())
    assert res["ok"] is False
    assert res["error"] == "project_not_found"


# ─── inspect_saved_credentials ────────────────────────────────────
@pytest.mark.asyncio
async def test_inspect_creds_never_returns_values(mock_db, ctx_factory):
    """Critical safety test: this tool MUST never leak secret values."""
    from backend.modules.freebuild.continuation_app_tools import handle_inspect_saved_credentials
    secret_blob = {"ciphertext": "gAAAAAxxxSECRETxxxx==", "saved_at": "2026"}
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"continuation_credentials": {
            "GITHUB_TOKEN": secret_blob,
            "SSH_PRIVATE_KEY": secret_blob,
            "FIREBASE_TOKEN": secret_blob,
        }},
    ]
    res = await handle_inspect_saved_credentials({"project_id": "test-pid"}, ctx_factory())
    assert res["ok"] is True
    # CRITICAL: result must contain only KEY NAMES, not values
    assert "saved_keys" in res
    assert set(res["saved_keys"]) == {"GITHUB_TOKEN", "SSH_PRIVATE_KEY", "FIREBASE_TOKEN"}
    # No values should appear anywhere
    serialized = str(res)
    assert "gAAAAA" not in serialized, "secret value leaked!"
    assert "ciphertext" not in serialized, "raw ciphertext leaked!"
    assert res["has_firebase"] is False, "FIREBASE_APP_ID missing so has_firebase = False"


@pytest.mark.asyncio
async def test_inspect_creds_detects_complete_ssh(mock_db, ctx_factory):
    from backend.modules.freebuild.continuation_app_tools import handle_inspect_saved_credentials
    blob = {"ciphertext": "x"}
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"continuation_credentials": {
            "SSH_HOST": blob, "SSH_USERNAME": blob, "SSH_PRIVATE_KEY": blob,
        }},
    ]
    res = await handle_inspect_saved_credentials({"project_id": "test-pid"}, ctx_factory())
    assert res["has_ssh"] is True
    assert res["has_ftp"] is False


# ─── read_continuation_audit ──────────────────────────────────────
@pytest.mark.asyncio
async def test_read_audit_returns_action_timeline(mock_db, ctx_factory, monkeypatch):
    from backend.modules.freebuild.continuation_app_tools import handle_read_continuation_audit
    fake_logs = [
        {"ts": "2026-01-01T00:00:00", "action": "clone_remote_repo",
         "target_path": None, "success": True, "details": {"command": "git clone..."}},
        {"ts": "2026-01-01T00:05:00", "action": "propose_sandbox_change",
         "target_path": "src/x.js", "success": True, "details": {"summary": "swapped img"}},
    ]
    # Monkeypatch the fetch_audit import inside the handler
    import backend.modules.freebuild.continuation_audit as cad
    monkeypatch.setattr(cad, "fetch_audit", AsyncMock(return_value=fake_logs))
    mock_db.freebuild_projects.find_one.return_value = {"mode": "continuation"}
    res = await handle_read_continuation_audit({"project_id": "test-pid", "limit": 10}, ctx_factory())
    assert res["ok"] is True
    assert res["count"] == 2
    assert res["logs"][0]["action"] == "clone_remote_repo"
    assert res["logs"][1]["summary"] == "swapped img"
    # Signatures should NOT appear in trimmed output
    assert all("signature_hash" not in entry for entry in res["logs"])
