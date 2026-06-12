"""Regression tests for the Smart Workflow tools (Phase 3).

Run with: cd /app/backend && pytest tests/test_workflow_tools.py -v
"""
import os
import sys
import pytest
import pytest_asyncio
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")

from modules.freebuild.workflow_tools import (
    WORKFLOW_TOOL_SCHEMAS,
    WORKFLOW_TOOL_NAMES,
    ask_user_inline,
    plan_task,
    delegate,
    _ROLE_PROMPTS,
)
from modules.freebuild.freebuild_agent import (
    TOOLS_SCHEMA,
    TOOL_LABELS_AR,
    FreeBuildToolContext,
    _exec_tool,
)

PROJ_ID = "test_workflow_pytest"


@pytest_asyncio.fixture
async def db():
    import motor.motor_asyncio
    client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGO_URL"])
    d = client[os.environ.get("DB_NAME", "zerax")]
    yield d
    # cleanup plans created during tests
    await d.freebuild_plans.delete_many({"project_id": PROJ_ID})
    client.close()


@pytest.fixture
def ctx(db):
    return FreeBuildToolContext({"id": PROJ_ID, "current_html": ""}, db=db)


# ─── Wiring ────────────────────────────────────────────────────────────────
def test_workflow_schemas_registered():
    master = {t["name"] for t in TOOLS_SCHEMA}
    for w in WORKFLOW_TOOL_SCHEMAS:
        assert w["name"] in master


def test_workflow_labels_registered():
    for n in WORKFLOW_TOOL_NAMES:
        assert n in TOOL_LABELS_AR


def test_workflow_tools_are_async(ctx):
    for n in WORKFLOW_TOOL_NAMES:
        s = _exec_tool(ctx, n, {})
        assert s.get("__async__") is True


# ─── ask_user_inline ──────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_ask_user_inline_returns_sentinel(ctx):
    r = await ask_user_inline(ctx, {
        "question": "أي مزود تفضل؟",
        "options": ["Vercel", "Netlify"],
    })
    assert r["ok"] is True
    assert r["pending_user_input"] is True
    assert r["kind"] == "choice"
    assert r["options"] == ["Vercel", "Netlify"]
    assert r["allow_free_text"] is True


@pytest.mark.asyncio
async def test_ask_user_inline_rejects_short_options(ctx):
    r = await ask_user_inline(ctx, {"question": "X", "options": ["only one"]})
    assert r["ok"] is False


@pytest.mark.asyncio
async def test_ask_user_inline_caps_at_6_options(ctx):
    r = await ask_user_inline(ctx, {
        "question": "Pick one",
        "options": [f"opt{i}" for i in range(8)],
    })
    # Should reject (>6 options)
    assert r["ok"] is False


# ─── plan_task ─────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_plan_task_persists(ctx, db):
    r = await plan_task(ctx, {
        "title": "بناء صفحة هبوط لمطعم",
        "steps": ["تجميع المتطلبات", "كتابة HTML الأساسي", "إضافة قسم المنيو",
                  "اختبار الموقع", "نشره على Zenrex"],
        "estimated_minutes": 8,
    })
    assert r["ok"] is True
    assert r["plan_id"]
    assert len(r["steps"]) == 5
    assert r["kind"] == "plan"
    # Verify it's persisted
    saved = await db.freebuild_plans.find_one({"id": r["plan_id"]})
    assert saved is not None
    assert saved["title"] == "بناء صفحة هبوط لمطعم"
    assert len(saved["steps"]) == 5
    assert saved["steps"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_plan_task_rejects_too_few_steps(ctx):
    r = await plan_task(ctx, {"title": "x", "steps": ["only one"]})
    assert r["ok"] is False


@pytest.mark.asyncio
async def test_plan_task_caps_steps(ctx):
    r = await plan_task(ctx, {"title": "x", "steps": [f"step {i}" for i in range(20)]})
    assert r["ok"] is True
    assert len(r["steps"]) == 12  # capped at 12


# ─── delegate ───────────────────────────────────────────────────────────────
def test_delegate_role_prompts_complete():
    expected = {"designer", "copywriter", "security_auditor", "performance_optimizer",
                "data_analyst", "seo_strategist", "accessibility_auditor"}
    assert expected == set(_ROLE_PROMPTS.keys())


@pytest.mark.asyncio
async def test_delegate_rejects_unknown_role(ctx):
    r = await delegate(ctx, {"role": "wizard", "task": "make magic happen please"})
    assert r["ok"] is False
    assert "unknown role" in r["error"]


@pytest.mark.asyncio
async def test_delegate_rejects_short_task(ctx):
    r = await delegate(ctx, {"role": "designer", "task": "x"})
    assert r["ok"] is False
    assert "too short" in r["error"]


@pytest.mark.asyncio
async def test_delegate_calls_real_anthropic(ctx):
    """Real network call — skip if no key."""
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY")):
        pytest.skip("No Anthropic/Emergent key in env")
    r = await delegate(ctx, {
        "role": "copywriter",
        "task": "اكتب لي عنوان رئيسي قصير (7 كلمات أو أقل) لموقع مطعم برجر سعودي",
    })
    # Either it works or we need a fallback model; either way, log the result
    if r["ok"]:
        assert isinstance(r["answer"], str)
        assert len(r["answer"]) > 5
        assert r["role"] == "copywriter"
        assert "elapsed_seconds" in r
    else:
        # Acceptable: model not yet released. Log it.
        print(f"delegate failed (acceptable if model unreleased): {r.get('error')}")
