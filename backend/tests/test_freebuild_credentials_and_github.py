"""
Regression tests for the new Zenrex AI Brain tools.
Run with: cd /app/backend && pytest tests/test_freebuild_credentials_and_github.py -v
"""
import os
import sys
import pytest
import pytest_asyncio
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")

from modules.freebuild.freebuild_agent import (
    _exec_tool_async,
    FreeBuildToolContext,
    _SERVICE_CATALOG,
    TOOLS_SCHEMA,
)

PROJ_ID = "test_proj_creds_pytest"


@pytest_asyncio.fixture
async def db():
    """Per-test Motor client so the loop matches the test's event loop."""
    import motor.motor_asyncio
    client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGO_URL"])
    d = client[os.environ.get("DB_NAME", "zerax")]
    # cleanup before
    await d.freebuild_credentials.delete_many({"project_id": PROJ_ID})
    yield d
    # cleanup after
    await d.freebuild_credentials.delete_many({"project_id": PROJ_ID})
    client.close()


# ─── Sync catalog tests ────────────────────────────────────────────────────
def test_catalog_has_all_categories():
    expected = {
        "hosting", "payments", "email", "sms", "storage", "auth", "database",
        "analytics", "cdn", "domain", "image_ai", "video_ai", "voice_ai",
        "llm", "monitoring", "backup",
    }
    assert expected <= set(_SERVICE_CATALOG.keys())


def test_tool_schemas_include_new_tools():
    tool_names = {t["name"] for t in TOOLS_SCHEMA}
    new_tools = {
        "save_credential", "validate_credential", "list_credentials",
        "delete_credential", "recommend_service",
        "github_list_repos", "github_create_repo", "github_push_file",
        "github_get_file",
    }
    assert new_tools <= tool_names, f"missing: {new_tools - tool_names}"


# ─── recommend_service ────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_recommend_service_payments_sa():
    ctx = FreeBuildToolContext({"id": None, "current_html": ""}, db=None)
    r = await _exec_tool_async(ctx, "recommend_service",
                                {"category": "payments", "region": "SA"})
    assert r["ok"] is True
    names = [s["name"] for s in r["recommendations"]]
    assert any("Moyasar" in n for n in names), names


@pytest.mark.asyncio
async def test_recommend_service_unknown_category():
    ctx = FreeBuildToolContext({"id": None, "current_html": ""}, db=None)
    r = await _exec_tool_async(ctx, "recommend_service", {"category": "fake_cat"})
    assert r["ok"] is False
    assert "غير مدعومة" in r["error"]


# ─── Credential CRUD ──────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_save_and_list_credential(db):
    ctx = FreeBuildToolContext({"id": PROJ_ID, "current_html": ""}, db=db)
    r = await _exec_tool_async(ctx, "save_credential",
        {"service": "test_key", "value": "abcd1234efgh5678", "label": "Test"})
    assert r["ok"] is True
    assert r["mask"] == "abcd••••••5678"

    rl = await _exec_tool_async(ctx, "list_credentials", {})
    assert rl["ok"] is True
    assert rl["count"] >= 1
    assert any(c["service"] == "test_key" for c in rl["credentials"])


@pytest.mark.asyncio
async def test_save_credential_rejects_short_value(db):
    ctx = FreeBuildToolContext({"id": PROJ_ID, "current_html": ""}, db=db)
    r = await _exec_tool_async(ctx, "save_credential",
        {"service": "test_short", "value": "ab"})
    assert r["ok"] is False
    assert "قصيرة" in r["error"]


@pytest.mark.asyncio
async def test_save_credential_rejects_invalid_service_name(db):
    ctx = FreeBuildToolContext({"id": PROJ_ID, "current_html": ""}, db=db)
    r = await _exec_tool_async(ctx, "save_credential",
        {"service": "BAD NAME!", "value": "valid_value_xxx"})
    assert r["ok"] is False


@pytest.mark.asyncio
async def test_delete_credential(db):
    ctx = FreeBuildToolContext({"id": PROJ_ID, "current_html": ""}, db=db)
    await _exec_tool_async(ctx, "save_credential",
        {"service": "to_delete", "value": "v" * 10, "label": "x"})
    r = await _exec_tool_async(ctx, "delete_credential", {"service": "to_delete"})
    assert r["ok"] is True
    assert r["deleted_count"] == 1


# ─── validate_credential — REAL API calls ─────────────────────────────────
@pytest.mark.asyncio
async def test_validate_real_github_pat(db):
    """The whole point: AI cannot lie. Real PAT must return 200."""
    pat = os.environ.get("GITHUB_PAT", "")
    if not pat:
        pytest.skip("GITHUB_PAT not configured")
    ctx = FreeBuildToolContext({"id": PROJ_ID, "current_html": ""}, db=db)
    await _exec_tool_async(ctx, "save_credential",
        {"service": "github_pat", "value": pat, "label": "test"})
    r = await _exec_tool_async(ctx, "validate_credential", {"service": "github_pat"})
    assert r["ok"] is True
    assert r["valid"] is True
    assert r["http_status"] == 200
    assert r.get("account")


@pytest.mark.asyncio
async def test_validate_fake_github_pat_returns_401(db):
    """Fake PAT must return HTTP 401 (not a hallucinated answer)."""
    ctx = FreeBuildToolContext({"id": PROJ_ID, "current_html": ""}, db=db)
    await _exec_tool_async(ctx, "save_credential",
        {"service": "github_pat",
         "value": "ghp_FAKEFAKEFAKE0000000000000000000000000000",
         "label": "fake"})
    r = await _exec_tool_async(ctx, "validate_credential", {"service": "github_pat"})
    assert r.get("valid") is False
    assert r.get("http_status") == 401


@pytest.mark.asyncio
async def test_validate_unknown_service_returns_stored_only(db):
    """Unknown service should NOT hallucinate 'valid' — must return stored_only."""
    ctx = FreeBuildToolContext({"id": PROJ_ID, "current_html": ""}, db=db)
    await _exec_tool_async(ctx, "save_credential",
        {"service": "custom_svc", "value": "x" * 20, "label": "custom"})
    r = await _exec_tool_async(ctx, "validate_credential", {"service": "custom_svc"})
    assert r["ok"] is True
    assert r.get("stored_only") is True
    assert r.get("valid") is None  # explicit "we don't know"


# ─── github tools — read-only checks against real PAT ─────────────────────
@pytest.mark.asyncio
async def test_github_list_repos_with_env_pat(db):
    if not os.environ.get("GITHUB_PAT"):
        pytest.skip("GITHUB_PAT not configured")
    ctx = FreeBuildToolContext({"id": PROJ_ID, "current_html": ""}, db=db)
    r = await _exec_tool_async(ctx, "github_list_repos", {"limit": 3})
    assert r["ok"] is True
    for repo in r["repos"]:
        assert "full_name" in repo
        assert "html_url" in repo


@pytest.mark.asyncio
async def test_github_tool_without_pat_returns_helpful_error(db, monkeypatch):
    monkeypatch.delenv("GITHUB_PAT", raising=False)
    await db.freebuild_credentials.delete_many(
        {"project_id": PROJ_ID, "service": "github_pat"})
    ctx = FreeBuildToolContext({"id": PROJ_ID, "current_html": ""}, db=db)
    r = await _exec_tool_async(ctx, "github_list_repos", {"limit": 1})
    assert r["ok"] is False
    assert r.get("needs_credential") is True
    assert r.get("service") == "github_pat"
