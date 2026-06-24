"""Unit tests for the 4-stage Workflow Engine."""
from __future__ import annotations
import pytest

from backend.modules.freebuild.workflow_engine import (
    STAGE_DISCOVERY,
    STAGE_VISUAL_SKELETON,
    STAGE_WIRING,
    STAGE_SURGICAL_EDIT,
    VALID_STAGES,
    DISCOVERY_QUESTIONS,
    get_workflow_state,
    discovery_complete,
    can_advance_to,
    stage_prompt_addendum,
    stage_label_ar,
)


# ─── DISCOVERY_QUESTIONS ────────────────────────────────────────────────────

def test_discovery_has_exactly_8_questions():
    assert len(DISCOVERY_QUESTIONS) == 8


def test_discovery_keys_are_unique():
    keys = [q["key"] for q in DISCOVERY_QUESTIONS]
    assert len(keys) == len(set(keys))


def test_each_question_has_arabic_text():
    for q in DISCOVERY_QUESTIONS:
        assert q.get("ar"), f"missing Arabic text for {q.get('key')}"
        assert "؟" in q["ar"] or "?" in q["ar"], f"not a question: {q}"


# ─── get_workflow_state ─────────────────────────────────────────────────────

def test_empty_project_starts_in_discovery():
    state = get_workflow_state({})
    assert state["stage"] == STAGE_DISCOVERY


def test_project_with_existing_content_starts_in_surgical():
    state = get_workflow_state({"current_html": "<html>" + "x" * 1000 + "</html>"})
    assert state["stage"] == STAGE_SURGICAL_EDIT


def test_project_with_pages_dict_starts_in_surgical():
    state = get_workflow_state({"pages": {"index.html": "<html>x</html>"}})
    assert state["stage"] == STAGE_SURGICAL_EDIT


def test_existing_state_is_preserved():
    state = get_workflow_state({"workflow_state": {"stage": STAGE_WIRING}})
    assert state["stage"] == STAGE_WIRING


def test_defaults_fill_missing_keys():
    state = get_workflow_state({"workflow_state": {"stage": STAGE_VISUAL_SKELETON}})
    assert "discovery_answers" in state
    assert "wired_pages" in state
    assert "current_wiring_page" in state


# ─── discovery_complete ─────────────────────────────────────────────────────

def test_discovery_incomplete_when_no_answers():
    assert not discovery_complete({"discovery_answers": {}})


def test_discovery_incomplete_when_partial():
    # Provide answers for 3 of the 4 REQUIRED topics — should still be incomplete
    from backend.modules.freebuild.workflow_engine import DISCOVERY_REQUIRED_TOPICS
    required = list(DISCOVERY_REQUIRED_TOPICS)
    answers = {required[0]: "x", required[1]: "x", required[2]: "x"}
    assert not discovery_complete({"discovery_answers": answers})


def test_discovery_complete_when_all_required_topics_answered():
    """Only the 4 required topics matter — optional ones may stay empty."""
    from backend.modules.freebuild.workflow_engine import DISCOVERY_REQUIRED_TOPICS
    answers = {k: "answer" for k in DISCOVERY_REQUIRED_TOPICS}
    assert discovery_complete({"discovery_answers": answers})


# ─── can_advance_to (gate logic) ────────────────────────────────────────────

def test_cannot_advance_to_visual_skeleton_with_incomplete_discovery():
    project = {"workflow_state": {"stage": STAGE_DISCOVERY, "discovery_answers": {}}}
    ok, reason = can_advance_to(project, STAGE_VISUAL_SKELETON)
    assert not ok
    assert "Discovery" in reason or "discovery" in reason


def test_can_advance_to_visual_skeleton_with_full_discovery():
    answers = {q["key"]: "answer" for q in DISCOVERY_QUESTIONS}
    project = {"workflow_state": {"stage": STAGE_DISCOVERY, "discovery_answers": answers}}
    ok, _ = can_advance_to(project, STAGE_VISUAL_SKELETON)
    assert ok


def test_cannot_skip_visual_skeleton_to_wiring():
    project = {"workflow_state": {"stage": STAGE_DISCOVERY,
                                    "discovery_answers": {q["key"]: "x" for q in DISCOVERY_QUESTIONS}}}
    ok, reason = can_advance_to(project, STAGE_WIRING)
    assert not ok
    assert "Visual Skeleton" in reason


def test_cannot_advance_to_wiring_without_pages():
    project = {"workflow_state": {"stage": STAGE_VISUAL_SKELETON}, "pages": {}}
    ok, reason = can_advance_to(project, STAGE_WIRING)
    assert not ok


def test_can_advance_to_wiring_with_pages():
    project = {
        "workflow_state": {"stage": STAGE_VISUAL_SKELETON},
        "pages": {"index.html": "<html>...</html>"},
    }
    ok, _ = can_advance_to(project, STAGE_WIRING)
    assert ok


def test_cannot_advance_to_surgical_with_unwired_pages():
    project = {
        "workflow_state": {"stage": STAGE_WIRING, "wired_pages": ["index.html"]},
        "pages": {"index.html": "...", "movies.html": "...", "account.html": "..."},
    }
    ok, reason = can_advance_to(project, STAGE_SURGICAL_EDIT)
    assert not ok
    assert "movies.html" in reason and "account.html" in reason


def test_can_advance_to_surgical_when_all_wired():
    project = {
        "workflow_state": {"stage": STAGE_WIRING,
                            "wired_pages": ["index.html", "movies.html"]},
        "pages": {"index.html": "...", "movies.html": "..."},
    }
    ok, _ = can_advance_to(project, STAGE_SURGICAL_EDIT)
    assert ok


def test_invalid_target_stage_rejected():
    ok, _ = can_advance_to({}, "garbage_stage")
    assert not ok


# ─── stage_prompt_addendum ──────────────────────────────────────────────────

def test_discovery_addendum_lists_remaining_questions():
    state = {"stage": STAGE_DISCOVERY, "discovery_answers": {}}
    addendum = stage_prompt_addendum(state, {})
    assert "Discovery" in addendum
    # All 8 questions referenced
    for q in DISCOVERY_QUESTIONS:
        # The Arabic prompt fragment appears
        assert q["ar"][:25] in addendum, f"missing question {q['key']}"


def test_discovery_addendum_omits_already_answered():
    answers = {DISCOVERY_QUESTIONS[0]["key"]: "موقع للأفلام"}
    state = {"stage": STAGE_DISCOVERY, "discovery_answers": answers}
    addendum = stage_prompt_addendum(state, {})
    # The remaining 7 questions are listed
    for q in DISCOVERY_QUESTIONS[1:]:
        assert q["ar"][:25] in addendum
    # The answered one shows in the summary
    assert "موقع للأفلام" in addendum


def test_visual_skeleton_addendum_keeps_buttons_inert_but_nav_works():
    """New behavior: nav links work from Visual Skeleton stage; only
    functional buttons (forms/purchase/save) stay inert."""
    state = {"stage": STAGE_VISUAL_SKELETON, "discovery_answers": {}}
    addendum = stage_prompt_addendum(state, {})
    assert "Visual Skeleton" in addendum
    assert "data-wiring" in addendum
    # Nav must navigate from this stage
    assert "تنقل" in addendum or "navigate" in addendum.lower()


def test_wiring_addendum_focuses_on_one_page():
    state = {"stage": STAGE_WIRING, "wired_pages": [],
             "current_wiring_page": "index.html"}
    project = {"pages": {"index.html": "...", "movies.html": "..."}}
    addendum = stage_prompt_addendum(state, project)
    assert "Wiring" in addendum
    assert "index.html" in addendum
    assert "mark_page_wired" in addendum


def test_surgical_addendum_lists_alternatives():
    """New surgical addendum teaches the AI WHICH tool to pick for each
    edit type. Threshold raised to 4× (from 2.5×)."""
    state = {"stage": STAGE_SURGICAL_EDIT}
    addendum = stage_prompt_addendum(state, {})
    assert "Surgical" in addendum
    assert "batch_replace_in_pages" in addendum
    assert "insert_html_at" in addendum
    assert "apply_section" in addendum
    # New 4× threshold (raised from 2.5×)
    assert "4×" in addendum or "4x" in addendum


# ─── stage_label_ar ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("stage,expected", [
    (STAGE_DISCOVERY, "اكتشاف"),
    (STAGE_VISUAL_SKELETON, "بصري"),
    (STAGE_WIRING, "تفعيل"),
    (STAGE_SURGICAL_EDIT, "جراح"),
])
def test_stage_labels_are_arabic(stage, expected):
    assert expected in stage_label_ar(stage)


# ─── Source-level integration check ─────────────────────────────────────────

def test_workflow_tools_are_registered_in_schema():
    """The 3 workflow tools must appear in TOOLS_SCHEMA so the LLM can call them."""
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    for tool_name in ("save_discovery_answer", "advance_workflow_stage", "mark_page_wired"):
        assert f'"name": "{tool_name}"' in src, f"tool {tool_name} missing from schema"


def test_workflow_state_persistence_in_agent():
    """The persistence block must run after each agent turn."""
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    assert "WORKFLOW STATE PERSISTENCE" in src
    assert "workflow_state_dirty" in src
    assert 'update_one(' in src  # already there for many things, but the marker block uses it too


def test_workflow_addendum_injected_into_both_provider_prompts():
    """Both Anthropic and OpenAI system_prompt assembly must include `_wf_addendum`."""
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    # _wf_addendum must appear in at least 2 places (Anthropic + OpenAI branches)
    occurrences = src.count("_wf_addendum")
    assert occurrences >= 3, (
        f"Expected _wf_addendum to be used in BOTH provider system_prompt "
        f"assemblies AND in the classifier block; found {occurrences} uses."
    )
