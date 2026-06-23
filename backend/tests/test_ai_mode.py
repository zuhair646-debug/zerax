"""Unit tests for the Hybrid AI Mode router (Iteration 3)."""
from __future__ import annotations
import pytest

from backend.modules.freebuild.ai_mode import (
    classify_phase,
    pick_provider,
    describe_choice,
    PHASE_FIRST_DESIGN,
    PHASE_SURGICAL,
    CLAUDE_PROVIDER,
    CLAUDE_MODEL,
    GPT_PROVIDER,
    GPT_MODEL,
    VALID_MODES,
    DEFAULT_MODE,
)


# ─── classify_phase ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("msg, project, expected", [
    # Empty project + build verbs → first_design
    ("ابني موقع متجر إلكتروني", {"current_html": ""}, PHASE_FIRST_DESIGN),
    ("سوّي لي تطبيق محادثات", {}, PHASE_FIRST_DESIGN),
    ("Create a SaaS landing page", {"current_html": ""}, PHASE_FIRST_DESIGN),
    # Empty project + ambiguous → still first_design
    ("ابدأ", {"current_html": ""}, PHASE_FIRST_DESIGN),
    # Existing project + surgical phrasing → surgical
    ("احذف قسم newsletter", {"current_html": "x" * 1000}, PHASE_SURGICAL),
    ("غيّر اللون للأحمر", {"current_html": "x" * 600}, PHASE_SURGICAL),
    ("كمّل الأقسام", {"current_html": "x" * 800}, PHASE_SURGICAL),
    # Existing project + explicit rebuild markers → first_design
    ("من الصفر اعد بناء الموقع", {"current_html": "x" * 1000}, PHASE_FIRST_DESIGN),
    ("rebuild from scratch", {"current_html": "x" * 1000}, PHASE_FIRST_DESIGN),
    ("احذف كل شي وابدأ من جديد", {"current_html": "x" * 1000}, PHASE_FIRST_DESIGN),
])
def test_classify_phase(msg, project, expected):
    assert classify_phase(msg, project) == expected


# ─── pick_provider ──────────────────────────────────────────────────────────

def test_claude_only_always_picks_claude():
    """claude_only mode never routes to GPT."""
    for phase in (PHASE_FIRST_DESIGN, PHASE_SURGICAL):
        prov, model = pick_provider("claude_only", phase)
        assert prov == CLAUDE_PROVIDER
        assert model == CLAUDE_MODEL


def test_hybrid_first_design_picks_gpt(monkeypatch):
    """hybrid + first_design → GPT-5.5 (when key is present)."""
    monkeypatch.setenv("OPENAI_DIRECT_KEY", "sk-test-xxx")
    prov, model = pick_provider("hybrid", PHASE_FIRST_DESIGN)
    assert prov == GPT_PROVIDER
    assert model == GPT_MODEL


def test_hybrid_surgical_picks_claude(monkeypatch):
    """hybrid + surgical → still Claude (only first_design goes to GPT)."""
    monkeypatch.setenv("OPENAI_DIRECT_KEY", "sk-test-xxx")
    prov, model = pick_provider("hybrid", PHASE_SURGICAL)
    assert prov == CLAUDE_PROVIDER
    assert model == CLAUDE_MODEL


def test_hybrid_falls_back_to_claude_when_no_openai_key(monkeypatch):
    """hybrid + first_design BUT no OpenAI key → fall back to Claude."""
    monkeypatch.delenv("OPENAI_DIRECT_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    prov, model = pick_provider("hybrid", PHASE_FIRST_DESIGN)
    assert prov == CLAUDE_PROVIDER
    assert model == CLAUDE_MODEL


# ─── describe_choice ────────────────────────────────────────────────────────

def test_describe_choice_hybrid_gpt(monkeypatch):
    monkeypatch.setenv("OPENAI_DIRECT_KEY", "sk-test-xxx")
    s = describe_choice("hybrid", PHASE_FIRST_DESIGN)
    assert "GPT-5.5" in s


def test_describe_choice_claude_default():
    s = describe_choice("claude_only", PHASE_SURGICAL)
    assert "Claude" in s


# ─── constants ──────────────────────────────────────────────────────────────

def test_valid_modes_contains_both():
    assert "claude_only" in VALID_MODES
    assert "hybrid" in VALID_MODES


def test_default_mode_is_claude_only():
    """Hybrid is opt-in; default must remain claude_only for safety."""
    assert DEFAULT_MODE == "claude_only"


def test_gpt_model_is_latest():
    """Per the latest Feb-2026 playbook, gpt-5.5 is the most recent OpenAI model."""
    assert GPT_MODEL == "gpt-5.5"
