"""Regression tests for the workflow stage enforcement upgrades:

1. Auto-advance: save_discovery_answer auto-promotes the stage to
   visual_skeleton as soon as the 4 required topics are filled — the LLM
   no longer needs to explicitly call advance_workflow_stage.

2. Stage banner: the system-prompt addendum is now prefixed with a strong
   visual banner that names the current stage at the TOP of the prompt so
   it cannot be silently overridden by downstream rules.
"""
from __future__ import annotations


def test_auto_advance_logic_in_source():
    """save_discovery_answer must check discovery_complete and flip stage."""
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    # Locate the dispatcher block
    idx = src.find('if name == "save_discovery_answer":')
    assert idx > 0
    block = src[idx:idx + 2200]
    assert "auto_advanced" in block
    assert "STAGE_VISUAL_SKELETON" in block
    assert "discovery_complete(ws)" in block


def test_stage_banner_in_addendum_assembly():
    """The workflow addendum must be prefixed with a stage banner that
    names the current stage prominently."""
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    assert "_stage_banner" in src
    assert "المرحلة الحالية" in src
    assert "stage_banner" in src.lower() or "_stage_banner" in src


def test_save_discovery_answer_returns_progress_with_required_count():
    """The return shape uses the 4-required-topic denominator."""
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    idx = src.find('if name == "save_discovery_answer":')
    block = src[idx:idx + 2200]
    # The progress string must reference 4 (the required topic count) or use total_req
    assert "موضوع أساسي" in block
    assert "total_req" in block or "DISCOVERY_REQUIRED_TOPICS" in block


def test_old_8_progress_pattern_removed():
    """The legacy progress \"X/8\" string must be gone from save_discovery_answer."""
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    idx = src.find('if name == "save_discovery_answer":')
    block = src[idx:idx + 2200]
    assert '"progress": f"{answered}/8"' not in block



# ── Functional simulation tests ─────────────────────────────────────────
# Reproduce a real save_discovery_answer dispatch on a fresh fake project
# and verify the auto-advance branch fires exactly at the 4th required key.

def _make_ctx():
    """Build a minimal FreeBuildToolContext on a fresh empty project."""
    import importlib
    fa = importlib.import_module("modules.freebuild.freebuild_agent")
    project = {
        "id": "TEST_proj_autoadvance",
        "user_id": "TEST_user",
        "pages": {},
        "current_html": "",
    }
    return fa, fa.FreeBuildToolContext(project, auth_token=None, db=None, is_owner=True)


def test_functional_auto_advance_on_fourth_required_key():
    """Call save_discovery_answer 4 times with required keys; assert auto-advance fires on the 4th call only."""
    fa, ctx = _make_ctx()
    from modules.freebuild.workflow_engine import STAGE_VISUAL_SKELETON, STAGE_DISCOVERY

    required_sequence = [
        ("site_purpose", "متجر إلكتروني لبيع الكتب"),
        ("page_count_and_names", "3 صفحات: الرئيسية، الكتب، عن المتجر"),
        ("page_contents", "الرئيسية: عرض، الكتب: قائمة، عن: نص"),
        ("style_preference", "مودرن مع ألوان دافئة"),
    ]
    results = []
    for i, (k, v) in enumerate(required_sequence, start=1):
        res = fa._exec_tool(ctx, "save_discovery_answer", {"key": k, "value": v})
        assert res["ok"] is True, f"call {i} failed: {res}"
        results.append(res)

    # First three calls must NOT auto-advance
    for i in range(3):
        assert results[i]["auto_advanced_to_visual_skeleton"] is False, (
            f"unexpected auto-advance at call {i+1}: {results[i]}"
        )
        # progress denominator should reference total_req (4)
        assert results[i]["progress"].endswith("موضوع أساسي")
        assert results[i]["progress"].startswith(f"{i+1}/4")
        assert results[i]["complete"] is False

    # 4th call MUST auto-advance
    final = results[3]
    assert final["auto_advanced_to_visual_skeleton"] is True, f"4th call did not auto-advance: {final}"
    assert final["complete"] is True
    assert final["progress"].startswith("4/4")

    # ctx.project.workflow_state.stage must be visual_skeleton
    ws = ctx.project["workflow_state"]
    assert ws["stage"] == STAGE_VISUAL_SKELETON, f"stage not flipped: {ws}"
    assert ctx.workflow_state_dirty is True

    # next_action hint for the 4th call must direct to Visual Skeleton
    assert "Visual Skeleton" in final["next_action"]


def test_functional_no_auto_advance_with_only_three_required():
    """With only 3 of 4 required keys filled, stage must remain discovery."""
    fa, ctx = _make_ctx()
    from modules.freebuild.workflow_engine import STAGE_DISCOVERY, STAGE_VISUAL_SKELETON

    only_three = [
        ("site_purpose", "موقع مطعم"),
        ("page_count_and_names", "صفحتين: الرئيسية، القائمة"),
        ("page_contents", "الرئيسية: ترحيب، القائمة: أصناف"),
    ]
    for k, v in only_three:
        res = fa._exec_tool(ctx, "save_discovery_answer", {"key": k, "value": v})
        assert res["ok"] is True
        assert res["auto_advanced_to_visual_skeleton"] is False
        assert res["complete"] is False
        ws = ctx.project.get("workflow_state") or {}
        # Stage must remain discovery throughout
        assert ws.get("stage") != STAGE_VISUAL_SKELETON, (
            f"stage prematurely advanced after key={k}: {ws}"
        )

    # Final state assertion
    ws = ctx.project["workflow_state"]
    assert ws["stage"] == STAGE_DISCOVERY


def test_functional_optional_key_does_not_trigger_advance():
    """Filling an optional key without the 4 required keys must NOT advance."""
    fa, ctx = _make_ctx()
    from modules.freebuild.workflow_engine import STAGE_VISUAL_SKELETON

    # Fill optional + 3 required (missing style_preference)
    sequence = [
        ("site_purpose", "موقع"),
        ("page_count_and_names", "صفحة واحدة"),
        ("page_contents", "محتوى"),
        ("target_audience", "شباب"),  # optional
    ]
    for k, v in sequence:
        res = fa._exec_tool(ctx, "save_discovery_answer", {"key": k, "value": v})
        assert res["ok"] is True
        assert res["auto_advanced_to_visual_skeleton"] is False

    assert ctx.project["workflow_state"]["stage"] != STAGE_VISUAL_SKELETON


def test_functional_invalid_key_rejected():
    """Unknown keys must be rejected without modifying state."""
    fa, ctx = _make_ctx()
    res = fa._exec_tool(ctx, "save_discovery_answer", {"key": "not_a_real_key", "value": "x"})
    assert res["ok"] is False
    assert "key" in res.get("error", "").lower() or "غير معروف" in res.get("error", "")


def test_functional_empty_value_rejected():
    """Empty value must be rejected."""
    fa, ctx = _make_ctx()
    res = fa._exec_tool(ctx, "save_discovery_answer", {"key": "site_purpose", "value": "  "})
    assert res["ok"] is False
