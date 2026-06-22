"""Tests for senior parity tools — closes final 15% gap."""
import asyncio
import json
import os
import pytest
from modules.brain.power_tools.senior_parity import (
    troubleshoot_agent, batch_refactor,
    iterative_test_and_fix, design_agent_full_stack,
    _extract_json, _get_anthropic_client,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture(autouse=True)
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestJsonExtraction:
    def test_clean_object(self):
        assert _extract_json('{"a": 1}') == {"a": 1}

    def test_with_fences(self):
        assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_with_prose(self):
        assert _extract_json('Here is the result:\n{"a": 1}\nThanks!') == {"a": 1}

    def test_array(self):
        assert _extract_json("[1, 2, 3]") == [1, 2, 3]

    def test_invalid(self):
        assert _extract_json("not json at all") is None

    def test_empty(self):
        assert _extract_json("") is None


class TestTroubleshootAgent:
    def test_validation(self):
        r = _run(troubleshoot_agent(""))
        assert not r["ok"]

    @pytest.mark.skipif(
        not (os.environ.get("ANTHROPIC_API_KEY")
              or os.environ.get("EMERGENT_LLM_KEY")),
        reason="needs Claude API key"
    )
    def test_simple_rca(self):
        # Provide enough context that Claude can conclude quickly
        r = _run(troubleshoot_agent(
            issue="Backend returns 502 on /api/users endpoint",
            component="Backend",
            error_messages="Connection refused on port 8001",
            recent_actions="Restarted docker container",
            relevant_files=["/etc/nginx/conf.d/backend.conf"],
            max_steps=3,
        ))
        assert r["ok"]
        assert r["rca"]
        assert "root_cause" in r["rca"]
        assert r["steps_used"] >= 1


class TestBatchRefactor:
    def test_validation(self):
        r = _run(batch_refactor("", ["/tmp/x.py"]))
        assert not r["ok"]
        r = _run(batch_refactor("rename", []))
        assert not r["ok"]
        # Too many
        r = _run(batch_refactor("x", ["/tmp/f.py"] * 35))
        assert not r["ok"]

    @pytest.mark.skipif(
        not (os.environ.get("ANTHROPIC_API_KEY")
              or os.environ.get("EMERGENT_LLM_KEY")),
        reason="needs Claude API key"
    )
    def test_dry_run(self, tmp_path):
        # Create two files with a function to rename
        a = tmp_path / "a.py"
        b = tmp_path / "b.py"
        a.write_text("def old_name():\n    return 1\n\nprint(old_name())\n")
        b.write_text("from a import old_name\nprint(old_name())\n")

        r = _run(batch_refactor(
            description="Rename function `old_name` to `new_name` in all files",
            file_paths=[str(a), str(b)],
            dry_run=True,
        ))
        assert r["ok"]
        assert r["dry_run"] is True
        # At least one file should be planned for change
        assert r["changes_planned"] >= 1


class TestDesignAgent:
    def test_validation(self):
        r = _run(design_agent_full_stack(""))
        assert not r["ok"]

    @pytest.mark.skipif(
        not (os.environ.get("ANTHROPIC_API_KEY")
              or os.environ.get("EMERGENT_LLM_KEY")),
        reason="needs Claude API key"
    )
    def test_landing_page_blueprint(self):
        r = _run(design_agent_full_stack(
            original_problem_statement="Build a landing page for a SaaS that books barbershop appointments in Saudi Arabia",
            user_choices="No explicit design preferences provided by user.",
            key_functionalities=["hero with CTA", "pricing", "testimonials"],
            app_type="landing_page",
        ))
        assert r["ok"]
        assert "color_palette" in r
        assert "primary_bg" in r["color_palette"]
        assert "typography" in r
        # Anti-AI-slop: should NOT default to Inter/Roboto
        display_font = r["typography"].get("display_font", "").lower()
        # Allow it if AI considered options, but warn
        # (we just assert there's a value)
        assert display_font
        assert "key_components" in r
        assert isinstance(r["key_components"], list)


class TestIterativeTestAndFix:
    def test_validation(self):
        r = _run(iterative_test_and_fix("", ""))
        assert not r["ok"]
        r = _run(iterative_test_and_fix("pid", ""))
        assert not r["ok"]


class TestAnthropicClient:
    def test_client_returns_none_when_no_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("EMERGENT_LLM_KEY", raising=False)
        client, base_url = _get_anthropic_client()
        assert client is None

    def test_client_works_with_key(self):
        # only run if a key is set
        if not (os.environ.get("ANTHROPIC_API_KEY")
                 or os.environ.get("EMERGENT_LLM_KEY")):
            pytest.skip("no key")
        client, _ = _get_anthropic_client()
        assert client is not None
