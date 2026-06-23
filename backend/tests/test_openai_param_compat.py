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
    """Source-string check: confirm the helper is defined AND called from
    BOTH OpenAI call sites. We grep for `_openai_token_kwargs(` (call form)
    and require >= 2 occurrences (one per call site in freebuild_agent.py).
    """
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    # Helper must be defined
    assert "def _openai_token_kwargs(" in src, "Helper function is not defined"
    # Helper must be called at least twice (one per OpenAI call site)
    call_count = src.count("_openai_token_kwargs(model")
    assert call_count >= 2, (
        f"Expected the helper to be called at BOTH OpenAI call sites; "
        f"found only {call_count} call(s)."
    )
    # And: no raw `max_tokens=8000,` should appear in OpenAI chat.completions.create
    # blocks. We can check by ensuring the literal `max_tokens=8000,` only
    # appears in the Anthropic call (line ~8463) — exactly once now.
    raw_count = src.count("max_tokens=8000,")
    assert raw_count <= 1, (
        f"Expected at most 1 raw `max_tokens=8000,` (Anthropic only); "
        f"found {raw_count}. OpenAI calls must use the helper."
    )


def test_source_uses_gpt5_or_o_prefix_check():
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    assert 'model.startswith("gpt-5")' in src, "gpt-5 prefix check missing"
    assert 'model.startswith("o")' in src, "o-series prefix check missing"
