"""Regression test for the PRE-FINISH GATE.

Bug: When the AI (especially GPT-5.5 in Hybrid mode) called create_page for
multiple pages and then called finish() while sidebar pages remained as
empty skeletons (≤ 1 section, < 800 chars of meaningful text), the user
ended up with white/blank sidebar pages. The PRE-FINISH GATE rejects
finish() until every page in ctx.pages has real content.
"""
from __future__ import annotations
import re


def test_pre_finish_gate_source_present():
    """Confirm the gate block exists in source with the expected marker."""
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    assert "PRE-FINISH GATE" in src, "PRE-FINISH GATE marker missing"
    assert "pre_finish_gate_block" in src, "log marker missing"


def test_pre_finish_gate_runs_before_finish_assignment():
    """The gate must run BEFORE the `summary = ...` assignment inside
    the finish branch — otherwise the variables are committed before the
    check fires.
    """
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    gate_pos = src.find("PRE-FINISH GATE")
    # The finish branch under _stream_one_provider has the gate at its top,
    # followed by summary = (tu["input"].get("summary") or "").strip()
    summary_pos = src.find('summary = (tu["input"].get("summary") or "").strip()', gate_pos)
    assert gate_pos > 0 and summary_pos > 0, "Markers missing"
    assert gate_pos < summary_pos, (
        "PRE-FINISH GATE must run BEFORE summary assignment inside finish branch."
    )


def test_pre_finish_gate_thresholds_match_blank_detector():
    """The gate uses the same blank-page thresholds as BLANK PAGE DETECTOR
    (≤ 1 section AND < 800 chars). Inconsistency between them would lead
    to confusing UX: detector warns but gate lets through, or vice-versa.
    """
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    # PRE-FINISH GATE section
    gate_idx = src.find("PRE-FINISH GATE")
    gate_section = src[gate_idx:gate_idx + 2500]
    # Both thresholds must appear in the gate section
    assert "_sec_count <= 1" in gate_section, "Gate must use ≤ 1 section threshold"
    assert "< 800" in gate_section, "Gate must use < 800 chars threshold"


def test_pre_finish_gate_uses_continue_to_skip_finish():
    """The gate must use `continue` to skip the rest of the finish branch
    (not break, not return). This is what gives the AI another turn to fix.
    """
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    gate_idx = src.find("PRE-FINISH GATE")
    gate_section = src[gate_idx:gate_idx + 2500]
    assert "continue" in gate_section, (
        "Gate must call `continue` after blocking — otherwise the AI never "
        "gets a chance to fix the blank pages."
    )


def test_pre_finish_gate_handles_both_message_formats():
    """Anthropic uses content=[{type:text,...}] while OpenAI uses plain
    content=str. The gate must inject the tool_result in BOTH formats.
    """
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    gate_idx = src.find("PRE-FINISH GATE")
    gate_section = src[gate_idx:gate_idx + 3500]
    # Anthropic branch
    assert 'provider in ("anthropic", "emergent_anthropic")' in gate_section
    # Both message dict shapes
    assert '"type": "tool_result"' in gate_section
    assert '"role": "tool"' in gate_section
    assert '"tool_call_id"' in gate_section


def test_pre_finish_gate_force_tool_use_next_iter():
    """After blocking, the gate flips force_tool_use_next_iter=True so the
    AI cannot respond with text only on the very next iteration.
    """
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    gate_idx = src.find("PRE-FINISH GATE")
    gate_section = src[gate_idx:gate_idx + 3500]
    assert "force_tool_use_next_iter = True" in gate_section
