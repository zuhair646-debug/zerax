"""Unit tests for the OpenAI parameter compatibility helper.

GPT-5.x and o-series models reject `max_tokens` and require
`max_completion_tokens` instead. The agent loop selects the right kwarg
based on the model identifier prefix.
"""
from __future__ import annotations


def _token_kwarg_for(model: str) -> dict:
    """Mirror of the inline logic in freebuild_agent.py — both
    _run_openai_compat_agent (line ~8669) and _stream_one_provider (line
    ~9441) use this exact pattern.
    """
    _is_gpt5_or_o = isinstance(model, str) and (
        model.startswith("gpt-5") or model.startswith("o")
    )
    return {"max_completion_tokens": 8000} if _is_gpt5_or_o else {"max_tokens": 8000}


def test_gpt_5_5_uses_max_completion_tokens():
    kw = _token_kwarg_for("gpt-5.5")
    assert "max_completion_tokens" in kw
    assert "max_tokens" not in kw


def test_gpt_5_4_uses_max_completion_tokens():
    kw = _token_kwarg_for("gpt-5.4")
    assert "max_completion_tokens" in kw


def test_gpt_5_2_uses_max_completion_tokens():
    kw = _token_kwarg_for("gpt-5.2")
    assert "max_completion_tokens" in kw


def test_gpt_5_uses_max_completion_tokens():
    kw = _token_kwarg_for("gpt-5")
    assert "max_completion_tokens" in kw


def test_o1_uses_max_completion_tokens():
    kw = _token_kwarg_for("o1")
    assert "max_completion_tokens" in kw


def test_o3_uses_max_completion_tokens():
    kw = _token_kwarg_for("o3")
    assert "max_completion_tokens" in kw


def test_o4_mini_uses_max_completion_tokens():
    kw = _token_kwarg_for("o4-mini")
    assert "max_completion_tokens" in kw


def test_gpt_4o_still_uses_max_tokens():
    """Legacy non-gpt5 models still take max_tokens."""
    kw = _token_kwarg_for("gpt-4o")
    assert "max_tokens" in kw
    assert "max_completion_tokens" not in kw


def test_gpt_4_1_still_uses_max_tokens():
    kw = _token_kwarg_for("gpt-4.1")
    assert "max_tokens" in kw


def test_moonshot_kimi_uses_max_tokens():
    kw = _token_kwarg_for("moonshot-v1")
    assert "max_tokens" in kw


def test_source_contains_max_completion_tokens_logic():
    """Source-string check: confirm the inline logic exists in both call
    sites (not silently removed by a refactor).
    """
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    # The conditional kwarg pattern must appear at least twice
    # (in _run_openai_compat_agent + in _stream_one_provider's openai branch).
    occurrences = src.count("max_completion_tokens")
    assert occurrences >= 2, (
        f"Expected the max_completion_tokens fix in BOTH OpenAI call sites; "
        f"found only {occurrences} occurrences."
    )


def test_source_uses_gpt5_or_o_prefix_check():
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    assert 'model.startswith("gpt-5")' in src, "gpt-5 prefix check missing"
    assert 'model.startswith("o")' in src, "o-series prefix check missing"
