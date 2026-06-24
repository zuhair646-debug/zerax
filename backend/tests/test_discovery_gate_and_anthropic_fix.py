"""Regression tests for the two critical bugs in iteration 8 follow-up:

1. The Discovery stage was ignored by the LLM — it jumped straight to
   create_page / apply_section. Server-side gate now blocks these
   construction tools during the discovery stage.

2. Anthropic 400 BadRequest: "tool_use ids were found without tool_result
   blocks immediately after". Caused by free-standing user text messages
   inserted between tool_results in a multi-tool-use response. Fixed by
   merging the post-write verification message INTO the just-appended
   tool_result content (Anthropic) instead of a separate user block.
"""
from __future__ import annotations


def test_discovery_stage_blocks_construction_tools_at_source():
    """The dispatcher gate must exist BEFORE the workflow_engine tools block."""
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    assert "DISCOVERY STAGE HARD GATE" in src, "discovery hard gate marker missing"
    # The gate must reference the construction tool set explicitly
    assert '"apply_section", "create_page", "write_full_html"' in src
    # It must check the stage
    assert "STAGE_DISCOVERY" in src
    # The error message must guide the AI to save_discovery_answer
    assert "save_discovery_answer" in src


def test_discovery_gate_is_above_tool_dispatch():
    """The gate must run BEFORE the regular tool execution branches so it
    can short-circuit construction calls."""
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    gate_pos = src.find("DISCOVERY STAGE HARD GATE")
    workflow_tools_pos = src.find("# ── Workflow Engine tools ──")
    assert gate_pos > 0 and workflow_tools_pos > 0
    assert gate_pos < workflow_tools_pos, (
        "discovery gate must be ABOVE the workflow tools dispatcher"
    )


def test_post_write_verification_merges_into_tool_result_not_separate_user_msg():
    """Anthropic crashes if a user text message is inserted between
    tool_uses. The verification must MERGE into the last tool_result
    content for Anthropic providers."""
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    # The fix must reference the merge approach
    assert 'tool_use_id") == tu["id"]' in src
    # And it must NOT have the old broken pattern (text-only user msg after tool_result)
    # Allow legacy non-Anthropic branch (which still uses plain str content)
    assert "merge failed" in src.lower() or "[post-write-verify] merge" in src
    # The OpenAI branch still uses a plain user message which is fine
    assert 'messages.append({"role": "user", "content": _verif_msg})' in src


def test_old_broken_user_text_after_tool_result_pattern_is_removed():
    """The old broken pattern was:
       messages.append({"role": "user",
                         "content": [{"type": "text", "text": _verif_msg}]})
    immediately after the tool_result. This must NOT appear in the verify
    block (it can still appear elsewhere for explicit user text injections
    that are not following a tool_use)."""
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    # Locate the verification block, then check the snippet around it
    verify_idx = src.find("POST-WRITE VERIFICATION")
    assert verify_idx > 0
    # Look at the next 3500 chars (covers the merge logic)
    section = src[verify_idx:verify_idx + 4000]
    # The broken pattern must NOT exist here
    assert '"content": [{"type": "text", "text": _verif_msg}]' not in section, (
        "Old broken Anthropic verify-msg append pattern still present!"
    )
