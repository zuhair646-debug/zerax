"""Regression tests for Phase 4 tools: memory + audit + plan tracking.

Run with: cd /app/backend && pytest tests/test_memory_audit_tools.py -v
"""
import os
import sys
import pytest
import pytest_asyncio
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")

from modules.freebuild.memory_audit_tools import (
    PHASE4_TOOL_SCHEMAS,
    PHASE4_TOOL_NAMES,
    update_plan_step,
    memory_save,
    memory_recall,
    memory_list,
    memory_delete,
    audit_project,
    load_project_memories_for_prompt,
)
from modules.freebuild.workflow_tools import plan_task
from modules.freebuild.freebuild_agent import (
    TOOLS_SCHEMA,
    TOOL_LABELS_AR,
    FreeBuildToolContext,
    _exec_tool,
)

PROJ_ID = "test_phase4_pytest"


@pytest_asyncio.fixture
async def db():
    import motor.motor_asyncio
    client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGO_URL"])
    d = client[os.environ.get("DB_NAME", "zerax")]
    yield d
    # cleanup
    await d.freebuild_plans.delete_many({"project_id": PROJ_ID})
    await d.freebuild_memories.delete_many({"project_id": PROJ_ID})
    await d.freebuild_audits.delete_many({"project_id": PROJ_ID})
    client.close()


@pytest.fixture
def ctx(db):
    sample_html = """<!doctype html><html dir="rtl" lang="ar">
<head><meta charset="utf-8"><title>متجر اختبار</title></head>
<body><h1>مرحباً</h1><p>اختبار</p></body></html>"""
    return FreeBuildToolContext({
        "id": PROJ_ID,
        "current_html": sample_html,
        "merchant_id": "test_merchant_999",
    }, db=db)


# ─── Wiring ───────────────────────────────────────────────────────────
def test_phase4_schemas_registered():
    master = {t["name"] for t in TOOLS_SCHEMA}
    for t in PHASE4_TOOL_SCHEMAS:
        assert t["name"] in master


def test_phase4_labels_registered():
    for n in PHASE4_TOOL_NAMES:
        assert n in TOOL_LABELS_AR


def test_phase4_tools_async_routing(ctx):
    for n in PHASE4_TOOL_NAMES:
        s = _exec_tool(ctx, n, {})
        assert s.get("__async__") is True


# ─── update_plan_step ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_update_plan_step_marks_done(ctx, db):
    # Create a plan
    p = await plan_task(ctx, {
        "title": "اختبار",
        "steps": ["خطوة أ", "خطوة ب", "خطوة ج"],
    })
    plan_id = p["plan_id"]
    # Mark step 1 in progress
    r = await update_plan_step(ctx, {
        "plan_id": plan_id, "step_index": 1, "status": "in_progress",
    })
    assert r["ok"] is True
    assert r["status"] == "in_progress"
    assert r["kind"] == "plan_step_update"
    # Mark step 1 done with a note
    r = await update_plan_step(ctx, {
        "plan_id": plan_id, "step_index": 1, "status": "done", "note": "اكتمل بنجاح",
    })
    assert r["ok"] is True
    assert r["note"] == "اكتمل بنجاح"
    # Verify persisted
    plan_doc = await db.freebuild_plans.find_one({"id": plan_id})
    assert plan_doc["steps"][1]["status"] == "done"
    assert plan_doc["steps"][1]["note"] == "اكتمل بنجاح"


@pytest.mark.asyncio
async def test_update_plan_step_rejects_unknown_plan(ctx):
    r = await update_plan_step(ctx, {
        "plan_id": "nonexistent", "step_index": 0, "status": "done",
    })
    assert r["ok"] is False


@pytest.mark.asyncio
async def test_update_plan_step_rejects_bad_status(ctx, db):
    p = await plan_task(ctx, {"title": "x", "steps": ["a", "b"]})
    r = await update_plan_step(ctx, {
        "plan_id": p["plan_id"], "step_index": 0, "status": "bogus",
    })
    assert r["ok"] is False


# ─── Memory tools ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_memory_save_and_recall(ctx):
    r = await memory_save(ctx, {"key": "brand_color", "value": "ذهبي ملكي #D4AF37"})
    assert r["ok"] is True
    assert r["scope"] == "project"
    r = await memory_recall(ctx, {"key": "brand_color"})
    assert r["ok"] is True
    assert "ذهبي" in r["value"]


@pytest.mark.asyncio
async def test_memory_list_returns_all(ctx):
    await memory_save(ctx, {"key": "color", "value": "أحمر"})
    await memory_save(ctx, {"key": "font", "value": "Tajawal"})
    r = await memory_list(ctx, {})
    assert r["ok"] is True
    keys = [m["key"] for m in r["memories"]]
    assert "color" in keys and "font" in keys


@pytest.mark.asyncio
async def test_memory_delete(ctx):
    await memory_save(ctx, {"key": "to_remove", "value": "x"})
    r = await memory_delete(ctx, {"key": "to_remove", "scope": "project"})
    assert r["ok"] is True
    assert r["deleted_count"] == 1


@pytest.mark.asyncio
async def test_memory_rejects_bad_key(ctx):
    r = await memory_save(ctx, {"key": "Bad Key!", "value": "x"})
    assert r["ok"] is False


@pytest.mark.asyncio
async def test_memory_rejects_huge_value(ctx):
    r = await memory_save(ctx, {"key": "huge", "value": "x" * 1500})
    assert r["ok"] is False


@pytest.mark.asyncio
async def test_load_project_memories_for_prompt(ctx, db):
    await memory_save(ctx, {"key": "shop_name", "value": "متجر السحاب"})
    await memory_save(ctx, {"key": "main_dish", "value": "برجر"})
    block = await load_project_memories_for_prompt(db, PROJ_ID, "test_merchant_999")
    assert "shop_name" in block
    assert "متجر السحاب" in block
    assert "main_dish" in block


# ─── audit_project ────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_audit_project_returns_scored_report(ctx, db):
    # Disable specialist + visual to keep test fast and offline
    r = await audit_project(ctx, {
        "include_visual_test": False,
        "include_specialists": False,
    })
    assert r["ok"] is True
    assert r["kind"] == "audit_report"
    assert "html" in r["scores"]
    assert "js" in r["scores"]
    assert "overall_score" in r
    assert "grade" in r
    assert r["audit_id"]
    # Verify persisted
    saved = await db.freebuild_audits.find_one({"audit_id": r["audit_id"]})
    assert saved is not None


@pytest.mark.asyncio
async def test_audit_project_with_no_html_fails(db):
    ctx = FreeBuildToolContext({"id": PROJ_ID, "current_html": ""}, db=db)
    r = await audit_project(ctx, {})
    assert r["ok"] is False
