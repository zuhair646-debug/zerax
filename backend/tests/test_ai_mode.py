"""Unit tests for the Hybrid AI Mode router with 3 modes:
claude_only, hybrid_gpt (GPT-5.5), hybrid_glm (GLM-5.2).
"""
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
    GLM_PROVIDER,
    GLM_MODEL,
    VALID_MODES,
    DEFAULT_MODE,
    LEGACY_HYBRID_ALIAS,
)


# ─── classify_phase ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("msg, project, expected", [
    ("ابني موقع متجر إلكتروني", {"current_html": ""}, PHASE_FIRST_DESIGN),
    ("سوّي لي تطبيق محادثات", {}, PHASE_FIRST_DESIGN),
    ("Create a SaaS landing page", {"current_html": ""}, PHASE_FIRST_DESIGN),
    ("ابدأ", {"current_html": ""}, PHASE_FIRST_DESIGN),
    ("احذف قسم newsletter", {"current_html": "x" * 1000}, PHASE_SURGICAL),
    ("غيّر اللون للأحمر", {"current_html": "x" * 600}, PHASE_SURGICAL),
    ("كمّل الأقسام", {"current_html": "x" * 800}, PHASE_SURGICAL),
    ("من الصفر اعد بناء الموقع", {"current_html": "x" * 1000}, PHASE_FIRST_DESIGN),
    ("rebuild from scratch", {"current_html": "x" * 1000}, PHASE_FIRST_DESIGN),
    ("احذف كل شي وابدأ من جديد", {"current_html": "x" * 1000}, PHASE_FIRST_DESIGN),
])
def test_classify_phase(msg, project, expected):
    assert classify_phase(msg, project) == expected


# ─── pick_provider — claude_only ────────────────────────────────────────────

def test_claude_only_always_picks_claude():
    for phase in (PHASE_FIRST_DESIGN, PHASE_SURGICAL):
        prov, model = pick_provider("claude_only", phase)
        assert prov == CLAUDE_PROVIDER
        assert model == CLAUDE_MODEL


# ─── pick_provider — hybrid_gpt ─────────────────────────────────────────────

def test_hybrid_gpt_first_design_picks_gpt(monkeypatch):
    monkeypatch.setenv("OPENAI_DIRECT_KEY", "sk-test-xxx")
    prov, model = pick_provider("hybrid_gpt", PHASE_FIRST_DESIGN)
    assert prov == GPT_PROVIDER
    assert model == GPT_MODEL


def test_hybrid_gpt_surgical_picks_claude(monkeypatch):
    monkeypatch.setenv("OPENAI_DIRECT_KEY", "sk-test-xxx")
    prov, model = pick_provider("hybrid_gpt", PHASE_SURGICAL)
    assert prov == CLAUDE_PROVIDER


def test_hybrid_gpt_falls_back_to_claude_when_no_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_DIRECT_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    prov, _ = pick_provider("hybrid_gpt", PHASE_FIRST_DESIGN)
    assert prov == CLAUDE_PROVIDER


# ─── pick_provider — hybrid_glm ─────────────────────────────────────────────

def test_hybrid_glm_first_design_picks_glm(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-xxx")
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
    prov, model = pick_provider("hybrid_glm", PHASE_FIRST_DESIGN)
    assert prov == GLM_PROVIDER
    assert model == GLM_MODEL


def test_hybrid_glm_surgical_picks_claude(monkeypatch):
    """Surgical edits always go to Claude regardless of which Hybrid mode is set."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-xxx")
    prov, _ = pick_provider("hybrid_glm", PHASE_SURGICAL)
    assert prov == CLAUDE_PROVIDER


def test_hybrid_glm_falls_back_to_claude_when_no_keys(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
    prov, _ = pick_provider("hybrid_glm", PHASE_FIRST_DESIGN)
    assert prov == CLAUDE_PROVIDER


def test_hybrid_glm_works_with_legacy_zhipu_key(monkeypatch):
    """Backwards-compat: ZHIPU_API_KEY still works if OpenRouter is unset."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("ZHIPU_API_KEY", "zhipu-test")
    prov, _ = pick_provider("hybrid_glm", PHASE_FIRST_DESIGN)
    assert prov == GLM_PROVIDER


def test_hybrid_modes_do_not_cross_keys(monkeypatch):
    """hybrid_gpt should NOT pick GLM even if OpenRouter key exists."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.delenv("OPENAI_DIRECT_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    prov, _ = pick_provider("hybrid_gpt", PHASE_FIRST_DESIGN)
    assert prov == CLAUDE_PROVIDER


# ─── describe_choice ────────────────────────────────────────────────────────

def test_describe_choice_hybrid_gpt(monkeypatch):
    monkeypatch.setenv("OPENAI_DIRECT_KEY", "sk-test-xxx")
    s = describe_choice("hybrid_gpt", PHASE_FIRST_DESIGN)
    assert "GPT-5.5" in s


def test_describe_choice_hybrid_glm(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    s = describe_choice("hybrid_glm", PHASE_FIRST_DESIGN)
    assert "GLM-4.6" in s


def test_describe_choice_claude_default():
    s = describe_choice("claude_only", PHASE_SURGICAL)
    assert "Claude" in s


# ─── constants ──────────────────────────────────────────────────────────────

def test_valid_modes_contains_all_three():
    assert "claude_only" in VALID_MODES
    assert "hybrid_gpt" in VALID_MODES
    assert "hybrid_glm" in VALID_MODES
    assert len(VALID_MODES) == 3


def test_default_mode_is_claude_only():
    assert DEFAULT_MODE == "claude_only"


def test_gpt_model_is_latest():
    assert GPT_MODEL == "gpt-5.5"


def test_glm_model_is_latest():
    """z-ai/glm-4.6 is Zhipu's latest stable production identifier via OpenRouter."""
    assert GLM_MODEL == "z-ai/glm-4.6"


def test_legacy_alias_constant():
    """LEGACY_HYBRID_ALIAS must equal 'hybrid' for backwards compat with pre-GLM saves."""
    assert LEGACY_HYBRID_ALIAS == "hybrid"
