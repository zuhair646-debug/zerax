"""
Iteration 80 — V3 Sandbox Tools + stream_hooks Refactor Verification
=====================================================================
1. Verify 4 new self-healing sandbox tools (run_js_sandbox, run_python_sandbox,
   validate_html_sandbox, autofix_code_loop) are wired and dispatch correctly.
2. Verify stream_hooks.py extracted module exports the 3 functions and works
   with mock inputs (run_classifier_fast_paths, spawn_brand_dna_extraction,
   run_auto_reviewer_on_html).
3. Verify capabilities_addendum mentions new tools and is capped at 6000 chars.
"""
from __future__ import annotations

import asyncio
import pytest


# ────────────── 1. New 4 sandbox tools in schema ──────────────
class TestSandboxToolsRegistered:
    def test_tools_schema_has_4_new_sandbox_tools(self):
        from modules.freebuild.freebuild_agent import TOOLS_SCHEMA
        names = {t["name"] for t in TOOLS_SCHEMA}
        expected = {"run_js_sandbox", "run_python_sandbox",
                    "validate_html_sandbox", "autofix_code_loop"}
        missing = expected - names
        assert not missing, f"missing sandbox tools in TOOLS_SCHEMA: {missing}"
        assert len(TOOLS_SCHEMA) == 176, f"expected 176 tools, got {len(TOOLS_SCHEMA)}"

    def test_tool_handlers_has_31_with_sandbox(self):
        from modules.freebuild.cortex_tools import TOOL_HANDLERS
        assert len(TOOL_HANDLERS) == 31, f"expected 31 handlers, got {len(TOOL_HANDLERS)}"
        for n in ("run_js_sandbox", "run_python_sandbox",
                  "validate_html_sandbox", "autofix_code_loop"):
            assert n in TOOL_HANDLERS, f"missing handler: {n}"


# ────────────── 2. Dispatch the 4 sandbox tools ──────────────
class TestDispatchSandboxTools:
    def _dispatch(self, name, args, ctx=None):
        from modules.freebuild.cortex_tools import dispatch

        async def _run():
            return await dispatch(name, args, ctx)
        return asyncio.run(_run())

    def test_dispatch_run_js_sandbox(self):
        result = self._dispatch("run_js_sandbox", {"code": "console.log(2+2)"})
        assert isinstance(result, dict), result
        # node may or may not be installed — accept either ok=True OR node_missing error
        if result.get("error") == "node_missing":
            pytest.skip("node not installed in sandbox environment")
        assert result.get("ok") is True, f"run_js_sandbox failed: {result}"
        assert "4" in (result.get("stdout") or ""), f"expected '4' in stdout: {result}"

    def test_dispatch_run_python_sandbox(self):
        result = self._dispatch("run_python_sandbox", {"code": "print(sum(range(10)))"})
        assert isinstance(result, dict), result
        assert result.get("ok") is True, f"run_python_sandbox failed: {result}"
        assert "45" in (result.get("stdout") or ""), f"expected '45' in stdout: {result}"

    def test_dispatch_validate_html_sandbox_missing_doctype(self):
        # HTML missing DOCTYPE should yield ok=False with that issue noted
        result = self._dispatch("validate_html_sandbox",
                                {"html": "<html><body><h1>Hi</h1></body></html>"})
        assert isinstance(result, dict), result
        assert result.get("ok") is False, f"expected ok=False (missing DOCTYPE): {result}"
        issues = result.get("issues") or []
        assert any("DOCTYPE" in i for i in issues), f"DOCTYPE issue missing: {issues}"

    def test_dispatch_validate_html_sandbox_full_doc(self):
        # Well-formed HTML5 with DOCTYPE should yield ok=True
        good = "<!DOCTYPE html><html><body><h1>Hi</h1></body></html>"
        result = self._dispatch("validate_html_sandbox", {"html": good})
        assert isinstance(result, dict), result
        assert result.get("ok") is True, f"expected ok=True for valid HTML: {result}"

    def test_dispatch_autofix_code_loop_simple_correct(self):
        # Simple correct JS should pass in 1 attempt without LLM
        result = self._dispatch("autofix_code_loop",
                                {"code": "console.log(1)", "language": "js",
                                 "max_attempts": 2})
        assert isinstance(result, dict), result
        if (result.get("error") or "") in ("node_missing",):
            pytest.skip("node not installed")
        # Some autofix_loop impls put attempts in different keys; check common ones
        assert result.get("ok") is True, f"autofix_code_loop failed on correct code: {result}"
        attempts = (result.get("total_attempts")
                    or result.get("attempts")
                    or result.get("iterations"))
        if attempts is not None:
            assert attempts == 1, f"expected 1 attempt on correct code, got: {result}"


# ────────────── 3. stream_hooks unit tests ──────────────
class TestStreamHooksImports:
    def test_stream_hooks_imports(self):
        from modules.freebuild.stream_hooks import (
            run_classifier_fast_paths,
            spawn_brand_dna_extraction,
            run_auto_reviewer_on_html,
        )
        assert callable(run_classifier_fast_paths)
        assert callable(spawn_brand_dna_extraction)
        assert callable(run_auto_reviewer_on_html)


class TestStreamHooksBehavior:
    def test_run_classifier_fast_paths_does_not_throw(self):
        from modules.freebuild.stream_hooks import run_classifier_fast_paths

        async def _run():
            q = asyncio.Queue()
            captured: dict = {}
            try:
                matched = await run_classifier_fast_paths(
                    message="hello, what time is it",
                    project={},
                    event_queue=q,
                    captured=captured,
                )
            except Exception as e:
                pytest.fail(f"run_classifier_fast_paths raised: {e}")
            # No assertion on return value — non-architect/non-review msg
            # should return False (or at least not crash)
            assert isinstance(matched, bool), f"expected bool, got {type(matched)}"
            # A 'classifier' event should have been emitted regardless
            events = []
            while not q.empty():
                events.append(q.get_nowait())
            assert any("classifier" in e for e in events), \
                f"no classifier event emitted: {events[:3]}"

        asyncio.run(_run())

    def test_spawn_brand_dna_extraction_skips_when_history_long(self):
        from modules.freebuild.stream_hooks import spawn_brand_dna_extraction

        async def _run():
            q = asyncio.Queue()
            # history length > 1 → must NOT spawn
            class _FakeDB:
                class _Coll:
                    async def update_one(self, *a, **kw):
                        raise AssertionError("update_one should NOT be called")
                freebuild_projects = _Coll()

            # Should return cleanly (no spawn)
            try:
                spawn_brand_dna_extraction(
                    db=_FakeDB(),
                    project_id="pid",
                    project={},
                    history=[{"role": "user", "content": "a"},
                             {"role": "assistant", "content": "b"}],
                    message="second msg",
                    event_queue=q,
                )
            except Exception as e:
                pytest.fail(f"spawn_brand_dna_extraction raised: {e}")

            # Allow event loop to settle; ensure queue stays empty
            await asyncio.sleep(0.1)
            assert q.empty(), "no event should be emitted when history > 1"

        asyncio.run(_run())

    def test_run_auto_reviewer_on_html_skips_when_not_updated(self):
        from modules.freebuild.stream_hooks import run_auto_reviewer_on_html

        async def _run():
            q = asyncio.Queue()
            captured: dict = {}
            done_in = {"html_updated": False, "summary": "ok"}
            done_out = await run_auto_reviewer_on_html(
                done=done_in,
                current_html=None,
                event_queue=q,
                captured=captured,
            )
            assert done_out == done_in, "done dict should be unchanged"
            assert q.empty(), "no auto_review event should be emitted"

        asyncio.run(_run())


# ────────────── 4. Capabilities addendum mentions new tools ──────────────
class TestCapabilitiesAddendum:
    def test_addendum_mentions_new_tools_and_capped(self):
        from modules.freebuild.capabilities_addendum import get_capabilities_addendum
        text = get_capabilities_addendum()
        assert isinstance(text, str)
        assert len(text) <= 6000, f"addendum exceeds 6000 char cap: {len(text)}"
        for needle in ("autofix_code_loop",
                       "generate_nextjs_project",
                       "recommend_state_management"):
            assert needle in text, f"addendum missing mention of: {needle}"
