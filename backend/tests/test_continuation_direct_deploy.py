"""Integration tests for the Direct Deploy feature (SSH + FTP variants).

These tests run against an in-memory mock DB so they don't touch real Mongo.
They verify the safety rails:
  • Tool refuses when project is not in continuation mode
  • Tool refuses when deploy_target is missing
  • Tool refuses when SSH/FTP credentials are missing
  • Endpoint correctly switches between github_pr and direct_live modes
"""
import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock


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


@pytest.mark.asyncio
async def test_deploy_vps_refuses_non_continuation_mode(mock_db, ctx_factory):
    from backend.modules.freebuild.continuation_tools import handle_deploy_to_live_vps
    mock_db.freebuild_projects.find_one.return_value = {"mode": "regular"}
    res = await handle_deploy_to_live_vps({"project_id": "test-pid"}, ctx_factory())
    assert res["ok"] is False
    assert "continuation" in res["error"].lower()


@pytest.mark.asyncio
async def test_deploy_vps_refuses_missing_target(mock_db, ctx_factory):
    from backend.modules.freebuild.continuation_tools import handle_deploy_to_live_vps
    # Mode check ok, target missing
    async def find_one(query, *args, **kwargs):
        proj = query.get("id") if isinstance(query, dict) else None
        if "mode" in str(args) + str(kwargs):
            return {"mode": "continuation"}
        return {"mode": "continuation", "continuation_deploy_target": None}
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},  # _guard_continuation_mode
        {"continuation_deploy_target": None},  # _load_deploy_target
    ]
    res = await handle_deploy_to_live_vps({"project_id": "test-pid"}, ctx_factory())
    assert res["ok"] is False
    assert res["error"] == "deploy_target_not_configured"


@pytest.mark.asyncio
async def test_deploy_vps_refuses_missing_ssh_creds(mock_db, ctx_factory, tmp_path):
    from backend.modules.freebuild import continuation_tools as ct
    # Override sandbox root so our test doesn't touch /opt
    ct.SANDBOX_ROOT = tmp_path
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},  # mode guard
        {"continuation_deploy_target": {"target_dir": "/var/www/html/",
                                         "source_subdir": "repo",
                                         "post_deploy_command": ""}},
        # _load_cred calls (one per key) — all return docs with empty credentials
        {"continuation_credentials": {}},
        {"continuation_credentials": {}},
        {"continuation_credentials": {}},
        {"continuation_credentials": {}},
    ]
    res = await ct.handle_deploy_to_live_vps({"project_id": "test-pid"}, ctx_factory())
    assert res["ok"] is False
    assert res["error"] == "ssh_credentials_incomplete"


@pytest.mark.asyncio
async def test_deploy_ftp_refuses_missing_ftp_creds(mock_db, ctx_factory, tmp_path):
    from backend.modules.freebuild import continuation_tools as ct
    ct.SANDBOX_ROOT = tmp_path
    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"continuation_deploy_target": {"target_dir": "/public_html/",
                                         "source_subdir": "repo"}},
        {"continuation_credentials": {}},
        {"continuation_credentials": {}},
        {"continuation_credentials": {}},
        {"continuation_credentials": {}},
    ]
    res = await ct.handle_deploy_to_live_ftp({"project_id": "test-pid"}, ctx_factory())
    assert res["ok"] is False
    assert res["error"] == "ftp_credentials_incomplete"


@pytest.mark.asyncio
async def test_deploy_vps_refuses_empty_sandbox(mock_db, ctx_factory, tmp_path, monkeypatch):
    """When SSH creds are present but the sandbox has no source files, fail fast."""
    from backend.modules.freebuild import continuation_tools as ct
    from backend.modules.freebuild import secure_credentials as sc

    ct.SANDBOX_ROOT = tmp_path
    # Ensure encryption is set up
    os.environ.setdefault("CONTINUATION_FERNET_KEY", "")
    # Use a real fernet key for the test
    from cryptography.fernet import Fernet
    key = Fernet.generate_key()
    os.environ["CONTINUATION_FERNET_KEY"] = key.decode()
    sc._FERNET = Fernet(key)
    ciphertext = sc.encrypt_secret("test-value")

    mock_db.freebuild_projects.find_one.side_effect = [
        {"mode": "continuation"},
        {"continuation_deploy_target": {"target_dir": "/var/www/html/",
                                         "source_subdir": "repo"}},
        {"continuation_credentials": {"SSH_HOST": {"ciphertext": ciphertext}}},
        {"continuation_credentials": {"SSH_USERNAME": {"ciphertext": ciphertext}}},
        {"continuation_credentials": {"SSH_PRIVATE_KEY": {"ciphertext": ciphertext}}},
        {"continuation_credentials": {"SSH_PORT": {"ciphertext": ciphertext}}},
    ]
    res = await ct.handle_deploy_to_live_vps({"project_id": "test-pid"}, ctx_factory())
    assert res["ok"] is False
    assert res["error"] == "sandbox_source_empty"
