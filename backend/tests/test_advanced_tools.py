"""
Regression tests for the Advanced Capability Tools (Phase 2 of the Limitless AI Brain).

Run with: cd /app/backend && pytest tests/test_advanced_tools.py -v
"""
import os
import sys
import pytest
import pytest_asyncio
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")

from modules.freebuild.advanced_tools import (
    ADVANCED_TOOL_SCHEMAS,
    ADVANCED_TOOL_NAMES,
    run_shell,
    read_file,
    write_file,
    list_files,
    delete_file,
    move_file,
    db_query,
    db_count,
    deploy_to,
    send_email,
    send_sms,
    generate_video,
    _ws,
    _shell_is_safe,
)
from modules.freebuild.freebuild_agent import (
    TOOLS_SCHEMA,
    TOOL_LABELS_AR,
    FreeBuildToolContext,
    _exec_tool,
    _exec_tool_async,
)

PROJ_ID = "test_advanced_tools_pytest"


@pytest_asyncio.fixture
async def db():
    import motor.motor_asyncio
    client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGO_URL"])
    d = client[os.environ.get("DB_NAME", "zerax")]
    yield d
    client.close()


@pytest.fixture
def ctx(db):
    return FreeBuildToolContext({"id": PROJ_ID, "current_html": "<html><body>hi</body></html>"}, db=db)


@pytest.fixture(autouse=True)
def cleanup_workspace():
    """Wipe workspace dir before and after each test."""
    import shutil
    ws = _ws(PROJ_ID)
    yield
    if ws.exists():
        shutil.rmtree(ws, ignore_errors=True)


# ─── Wiring tests ─────────────────────────────────────────────────────────
def test_advanced_tool_schemas_registered():
    """All 14 advanced tools must appear in the master TOOLS_SCHEMA."""
    master_names = {t["name"] for t in TOOLS_SCHEMA}
    for adv in ADVANCED_TOOL_SCHEMAS:
        assert adv["name"] in master_names, f"missing: {adv['name']}"


def test_advanced_tool_labels_registered():
    for n in ADVANCED_TOOL_NAMES:
        assert n in TOOL_LABELS_AR, f"missing label: {n}"


def test_async_dispatcher_recognizes_advanced_tools(ctx):
    """The sync dispatcher must return the __async__ sentinel for advanced tools."""
    for n in ADVANCED_TOOL_NAMES:
        sentinel = _exec_tool(ctx, n, {})
        assert sentinel.get("__async__") is True, f"{n} not routed as async"


# ─── Shell sandbox ────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_run_shell_basic_echo(ctx):
    r = await run_shell(ctx, {"command": "echo 'hello world'"})
    assert r["ok"] is True
    assert "hello world" in r["stdout"]
    assert r["exit_code"] == 0


@pytest.mark.asyncio
async def test_run_shell_can_use_common_tools(ctx):
    """Verify at least curl is available (the most universally needed tool)."""
    r = await run_shell(ctx, {"command": "command -v curl"})
    assert r["ok"] is True, r.get("stdout", "") + r.get("stderr", "")


@pytest.mark.asyncio
async def test_run_shell_blocks_dangerous_commands(ctx):
    r = await run_shell(ctx, {"command": "rm -rf /etc"})
    assert r["ok"] is False
    assert "rejected" in r["error"].lower()


@pytest.mark.asyncio
async def test_run_shell_blocks_sudo(ctx):
    r = await run_shell(ctx, {"command": "sudo whoami"})
    assert r["ok"] is False


@pytest.mark.asyncio
async def test_run_shell_timeout(ctx):
    r = await run_shell(ctx, {"command": "sleep 5", "timeout": 1})
    assert r["ok"] is False
    assert "timeout" in r["error"].lower()


@pytest.mark.asyncio
async def test_run_shell_uses_workspace_cwd(ctx):
    """Files created via run_shell should land in the workspace."""
    r = await run_shell(ctx, {"command": "echo 'data' > test.txt && cat test.txt"})
    assert r["ok"] is True
    assert "data" in r["stdout"]
    # Verify it ended up in the workspace, not /tmp
    ws_file = _ws(PROJ_ID) / "test.txt"
    assert ws_file.exists()
    assert ws_file.read_text().strip() == "data"


def test_shell_safety_patterns():
    assert _shell_is_safe("ls -la") is None
    assert _shell_is_safe("rm -rf /etc") is not None
    assert _shell_is_safe("sudo apt install") is not None
    assert _shell_is_safe(":(){:|:&};:") is not None
    # tmp is fine
    assert _shell_is_safe("rm -rf /tmp/xxx") is None


# ─── File System ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_write_then_read_file(ctx):
    w = await write_file(ctx, {"path": "src/app.js", "content": "console.log('hi');\n"})
    assert w["ok"] is True
    assert w["bytes"] == len("console.log('hi');\n")

    r = await read_file(ctx, {"path": "src/app.js"})
    assert r["ok"] is True
    assert r["content"] == "console.log('hi');\n"
    assert r["is_binary"] is False


@pytest.mark.asyncio
async def test_write_file_path_traversal_blocked(ctx):
    r = await write_file(ctx, {"path": "../../../etc/passwd", "content": "x"})
    assert r["ok"] is False


@pytest.mark.asyncio
async def test_write_file_max_size_enforced(ctx):
    big = "x" * (6 * 1024 * 1024)  # 6MB
    r = await write_file(ctx, {"path": "huge.txt", "content": big})
    assert r["ok"] is False
    assert "too large" in r["error"].lower()


@pytest.mark.asyncio
async def test_list_files(ctx):
    await write_file(ctx, {"path": "a.txt", "content": "A"})
    await write_file(ctx, {"path": "sub/b.txt", "content": "BB"})
    r = await list_files(ctx, {})
    assert r["ok"] is True
    assert r["count"] >= 2
    paths = [f["path"] for f in r["files"]]
    assert "a.txt" in paths
    assert "sub/b.txt" in paths


@pytest.mark.asyncio
async def test_delete_file(ctx):
    await write_file(ctx, {"path": "to_kill.txt", "content": "x"})
    r = await delete_file(ctx, {"path": "to_kill.txt"})
    assert r["ok"] is True
    r2 = await read_file(ctx, {"path": "to_kill.txt"})
    assert r2["ok"] is False


@pytest.mark.asyncio
async def test_move_file(ctx):
    await write_file(ctx, {"path": "old.txt", "content": "value"})
    r = await move_file(ctx, {"src": "old.txt", "dst": "new.txt"})
    assert r["ok"] is True
    r2 = await read_file(ctx, {"path": "new.txt"})
    assert r2["ok"] is True
    assert r2["content"] == "value"


@pytest.mark.asyncio
async def test_write_binary_file(ctx):
    import base64
    raw = b"\x89PNG\r\n\x1a\n"  # PNG header bytes
    b64 = base64.b64encode(raw).decode()
    r = await write_file(ctx, {"path": "img.png", "content": b64, "binary": True})
    assert r["ok"] is True
    r2 = await read_file(ctx, {"path": "img.png"})
    assert r2["ok"] is True
    assert r2["is_binary"] is True
    assert base64.b64decode(r2["content"]) == raw


# ─── DB query ─────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_db_query_rejects_unwhitelisted(ctx):
    r = await db_query(ctx, {"collection": "users"})
    assert r["ok"] is False
    assert "whitelisted" in r["error"]


@pytest.mark.asyncio
async def test_db_query_allowed_collection_returns_list(ctx):
    r = await db_query(ctx, {"collection": "freebuild_chat_projects", "limit": 1})
    assert r["ok"] is True
    assert isinstance(r["results"], list)


@pytest.mark.asyncio
async def test_db_count(ctx):
    r = await db_count(ctx, {"collection": "freebuild_chat_projects"})
    assert r["ok"] is True
    assert isinstance(r["count"], int)


# ─── deploy_to ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_deploy_to_without_credential_returns_helpful_error(ctx, monkeypatch):
    # Clear all possible env fallbacks so we hit the "needs_credential" branch
    for v in ("VERCEL_TOKEN", "VERCEL_API_TOKEN"):
        monkeypatch.delenv(v, raising=False)
    ctx.current_html = "<html><body>test</body></html>"
    r = await deploy_to(ctx, {"provider": "vercel", "project_name": "test"})
    assert r["ok"] is False
    assert r.get("needs_credential") is True
    assert r.get("service") == "vercel_token"


@pytest.mark.asyncio
async def test_deploy_to_unknown_provider(ctx):
    ctx.current_html = "<html></html>"
    r = await deploy_to(ctx, {"provider": "heroku", "project_name": "x"})
    assert r["ok"] is False


# ─── send_email / send_sms ────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_send_email_without_key_returns_helpful_error(ctx, monkeypatch):
    for v in ("RESEND_KEY", "RESEND_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    r = await send_email(ctx, {"to": "a@b.com", "subject": "x", "html": "<p>x</p>"})
    assert r["ok"] is False
    assert r.get("needs_credential") is True


@pytest.mark.asyncio
async def test_send_sms_without_creds_returns_helpful_error(ctx, monkeypatch):
    for v in ("TWILIO_SID", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH", "TWILIO_AUTH_TOKEN",
              "TWILIO_FROM", "TWILIO_PHONE_NUMBER"):
        monkeypatch.delenv(v, raising=False)
    r = await send_sms(ctx, {"to": "+966500000000", "message": "test"})
    assert r["ok"] is False
    assert r.get("needs_credential") is True


# ─── generate_video ──────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_generate_video_without_key_returns_helpful_error(ctx, monkeypatch):
    for v in ("FAL_KEY", "FAL_AI_KEY", "FAL_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    r = await generate_video(ctx, {"prompt": "a cat dancing"})
    assert r["ok"] is False
    assert r.get("needs_credential") is True
    assert r.get("service") == "fal_key"
