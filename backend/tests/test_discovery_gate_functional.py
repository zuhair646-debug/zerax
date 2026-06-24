"""Functional smoke tests for the DISCOVERY HARD GATE in _exec_tool.

These complement the source-pattern tests in test_discovery_gate_and_anthropic_fix.py
by actually invoking _exec_tool with synthetic contexts to verify runtime behavior.
"""
from __future__ import annotations

import sys
import os
import pytest

sys.path.insert(0, "/app/backend")


@pytest.fixture
def make_ctx():
    """Factory for building a minimal FreeBuildToolContext at a given stage."""
    from modules.freebuild.freebuild_agent import FreeBuildToolContext

    def _make(stage: str):
        project = {
            "id": "test-project-id",
            "name": "test",
            "html": "<html><body></body></html>",
            "pages": {"index.html": "<html><body></body></html>"},
            "active_page": "index.html",
            "workflow_state": {"stage": stage, "discovery_answers": {}},
        }
        # FreeBuildToolContext signature: (project, ...) — inspect to build minimally
        try:
            ctx = FreeBuildToolContext(project=project)
        except TypeError:
            # fallback: construct via __new__ + manual fields
            ctx = FreeBuildToolContext.__new__(FreeBuildToolContext)
            ctx.project = project
            ctx.tool_log = []
            ctx.workflow_state_dirty = False
        return ctx

    return _make


def test_discovery_stage_blocks_apply_section(make_ctx):
    """Gate must fire and produce save_discovery_answer hint."""
    from modules.freebuild.freebuild_agent import _exec_tool

    ctx = make_ctx("discovery")
    result = _exec_tool(ctx, "apply_section", {"page": "index.html", "html": "<div/>"})
    assert isinstance(result, dict)
    assert result.get("ok") is False
    err = result.get("error", "")
    assert "save_discovery_answer" in err, (
        f"Expected gate error mentioning save_discovery_answer, got: {err!r}"
    )


def test_discovery_stage_blocks_create_page(make_ctx):
    from modules.freebuild.freebuild_agent import _exec_tool

    ctx = make_ctx("discovery")
    result = _exec_tool(ctx, "create_page", {"name": "about.html"})
    assert result.get("ok") is False
    assert "save_discovery_answer" in result.get("error", "")


def test_discovery_stage_blocks_write_full_html(make_ctx):
    from modules.freebuild.freebuild_agent import _exec_tool

    ctx = make_ctx("discovery")
    result = _exec_tool(ctx, "write_full_html", {"html": "<html/>"})
    assert result.get("ok") is False
    assert "save_discovery_answer" in result.get("error", "")


def test_visual_skeleton_stage_does_not_trigger_discovery_gate(make_ctx):
    """At stage='visual_skeleton', the discovery gate must NOT fire.
    The tool may still fail for other reasons, but the gate error must not appear."""
    from modules.freebuild.freebuild_agent import _exec_tool

    ctx = make_ctx("visual_skeleton")
    result = _exec_tool(ctx, "apply_section", {"page": "index.html", "html": "<div/>"})
    # We do not require ok=True (downstream may complain about args), but the
    # discovery-gate-specific error must NOT be present.
    err = str(result.get("error", ""))
    assert "ممنوع استدعاء" not in err, (
        f"Discovery gate fired during visual_skeleton stage! err={err!r}"
    )
    assert "save_discovery_answer" not in err or result.get("ok") is True, (
        f"Gate-hint message appeared in non-discovery stage: {err!r}"
    )


def test_save_discovery_answer_works_in_discovery_stage(make_ctx):
    """Non-construction tool must succeed in discovery stage."""
    from modules.freebuild.freebuild_agent import _exec_tool
    from modules.freebuild.workflow_engine import DISCOVERY_QUESTIONS

    ctx = make_ctx("discovery")
    # Pick the first valid discovery question key
    first_key = DISCOVERY_QUESTIONS[0]["key"]
    result = _exec_tool(ctx, "save_discovery_answer",
                        {"key": first_key, "value": "Acme Corp — a B2B SaaS for invoicing"})
    assert result.get("ok") is True, f"save_discovery_answer should work in discovery: {result!r}"
    assert result.get("key") == first_key
    assert "progress" in result
