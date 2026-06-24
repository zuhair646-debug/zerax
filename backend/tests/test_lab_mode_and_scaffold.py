"""Iteration 66 — Lab Mode + Scaffold Stripping + Page Completeness Gate

Tests focus on:
1. _strip_scaffold_placeholders helper removes 'محتوى الصفحة قيد البناء' text
   and SCAFFOLD_PLACEHOLDER comment.
2. mark_page_built rejects skeleton/blank pages (sections < 2, text < 600 chars,
   or placeholder text like 'قريباً' / 'Lorem ipsum').
3. write_full_html returns `incomplete_warning` when result is sub-threshold.
4. Lab-mode branch (mode=lab) exists in agent_chat_stream and uses
   stream_agent_turn directly without Brain orchestrator.
5. The published-sites GET endpoints invoke _strip_scaffold_placeholders on
   the served HTML.
"""
import os
import sys
import re
import inspect
import asyncio

import pytest

# Make backend package importable
sys.path.insert(0, "/app/backend")

# ── Module imports ────────────────────────────────────────────────────
from modules.freebuild import freebuild_chat as fc_mod  # noqa: E402
from modules.freebuild import freebuild_agent as fa_mod  # noqa: E402


# ════════════════════════════════════════════════════════════════════════
# 1. _strip_scaffold_placeholders helper
# ════════════════════════════════════════════════════════════════════════
class TestStripScaffoldPlaceholders:
    """Unit tests on the helper that cleans serve-time scaffold leftovers."""

    def test_helper_exists(self):
        assert hasattr(fc_mod, "_strip_scaffold_placeholders")
        assert callable(fc_mod._strip_scaffold_placeholders)

    def test_strips_arabic_placeholder_text(self):
        dirty = (
            "<html><body>"
            "<section id='page-header'>"
            "<p data-scaffold='true'>محتوى الصفحة قيد البناء — أضف أقسامك</p>"
            "<!-- SCAFFOLD_PLACEHOLDER: AI MUST add real sections -->"
            "</section>"
            "<section id='hero'><h1>Real content</h1></section>"
            "</body></html>"
        )
        clean = fc_mod._strip_scaffold_placeholders(dirty)
        assert "قيد البناء" not in clean, "Arabic scaffold text must be removed"
        assert "SCAFFOLD_PLACEHOLDER" not in clean, "comment marker must be removed"
        assert "Real content" in clean, "real content must be preserved"

    def test_strips_scaffold_data_paragraphs(self):
        dirty = "<div><p data-scaffold='true'>قيد البناء</p><p>keep me</p></div>"
        clean = fc_mod._strip_scaffold_placeholders(dirty)
        assert "data-scaffold" not in clean
        assert "keep me" in clean

    def test_strips_html_comment_marker(self):
        dirty = "<!-- SCAFFOLD_PLACEHOLDER: AI MUST add sections -->\n<p>x</p>"
        clean = fc_mod._strip_scaffold_placeholders(dirty)
        assert "SCAFFOLD_PLACEHOLDER" not in clean

    def test_idempotent_on_clean_html(self):
        clean_html = "<html><body><h1>All clean</h1></body></html>"
        assert fc_mod._strip_scaffold_placeholders(clean_html) == clean_html

    def test_none_passthrough(self):
        assert fc_mod._strip_scaffold_placeholders(None) is None
        assert fc_mod._strip_scaffold_placeholders("") == ""

    def test_strips_orphan_arabic_text(self):
        """Even if the wrapping section was removed, orphan 'قيد البناء'
        text on its own must be scrubbed."""
        dirty = "<div>محتوى الصفحة قيد البناء — مؤقت</div>"
        clean = fc_mod._strip_scaffold_placeholders(dirty)
        assert "قيد البناء" not in clean


# ════════════════════════════════════════════════════════════════════════
# 2. Published-sites endpoint wiring
# ════════════════════════════════════════════════════════════════════════
class TestPublishedSitesEndpointWiring:
    """Source-level confirmation that the helper is called on both serve
    handlers (the only deployed copies of published HTML)."""

    def test_helper_wired_in_index_handler(self):
        src = inspect.getsource(fc_mod)
        # Must be called at least twice (once for / handler, once for
        # /{filename}). Count the calls to be safe against future refactors.
        n = src.count("_strip_scaffold_placeholders(html)")
        assert n >= 2, f"_strip_scaffold_placeholders should be called in both serve handlers (found {n})"

    def test_helper_called_before_footer_injection(self):
        """The strip must happen BEFORE footer injection so the Zenrex footer
        is never accidentally stripped, and the cleanup runs on the AI's
        page content only."""
        src = inspect.getsource(fc_mod)
        # find first occurrence of strip + first occurrence of footer inject
        strip_idx = src.find("_strip_scaffold_placeholders(html)")
        footer_idx = src.find("_inject_zenrex_footer(html)")
        assert strip_idx > 0 and footer_idx > 0
        assert strip_idx < footer_idx, "strip must run before footer injection"


# ════════════════════════════════════════════════════════════════════════
# 3. Page-completeness gate on mark_page_built
# ════════════════════════════════════════════════════════════════════════
def _make_ctx(pages: dict, active: str = "index.html"):
    project = {
        "id": "TEST_proj",
        "user_id": "TEST_user",
        "pages": pages,
        "active_page": active,
        "current_html": pages.get(active, ""),
        "workflow_state": {
            "stage": "surgical_edit",
            "discovery_answers": {"_test": "yes"},
            "build_queue": [active],
            "built_pages": [],
        },
    }
    return fa_mod.FreeBuildToolContext(project)


class TestMarkPageBuiltGate:
    def test_rejects_zero_section_skeleton(self):
        skeleton = "<html><body><h1>hi</h1></body></html>"
        ctx = _make_ctx({"about.html": skeleton}, active="about.html")
        res = fa_mod._exec_tool(ctx, "mark_page_built", {"filename": "about.html"})
        assert res.get("ok") is False
        assert res.get("error") == "page_incomplete"
        assert res.get("section_count") == 0

    def test_rejects_single_section_with_short_text(self):
        html = (
            "<html><body>"
            "<section id='hero'><h1>X</h1><p>short</p></section>"
            "</body></html>"
        )
        ctx = _make_ctx({"about.html": html}, active="about.html")
        res = fa_mod._exec_tool(ctx, "mark_page_built", {"filename": "about.html"})
        assert res.get("ok") is False
        assert res.get("error") == "page_incomplete"
        assert res.get("section_count") == 1
        assert res.get("meaningful_chars", 0) < 600

    def test_rejects_two_sections_with_lorem_ipsum_placeholder(self):
        long_text = " Lorem ipsum dolor sit amet, " * 50
        html = (
            "<html><body>"
            f"<section id='hero'><h1>Title</h1><p>{long_text}</p></section>"
            f"<section id='content'><p>{long_text}</p></section>"
            "</body></html>"
        )
        ctx = _make_ctx({"about.html": html}, active="about.html")
        res = fa_mod._exec_tool(ctx, "mark_page_built", {"filename": "about.html"})
        assert res.get("ok") is False, f"Lorem ipsum placeholder must be detected: {res}"
        assert res.get("error") == "page_incomplete"
        assert any("lorem" in p.lower() for p in (res.get("placeholders_found") or []))

    def test_rejects_with_qareeban_placeholder(self):
        long_text = "محتوى حقيقي وأصلي للصفحة. " * 60
        html = (
            "<html><body>"
            f"<section id='hero'><h1>عنوان</h1><p>{long_text}</p></section>"
            f"<section id='content'><p>{long_text} قريباً المزيد</p></section>"
            "</body></html>"
        )
        ctx = _make_ctx({"about.html": html}, active="about.html")
        res = fa_mod._exec_tool(ctx, "mark_page_built", {"filename": "about.html"})
        assert res.get("ok") is False
        assert "قريبا" in str(res.get("placeholders_found")) or "قريباً" in str(res.get("placeholders_found"))

    def test_accepts_complete_page(self):
        body = "محتوى حقيقي وكامل عن الصفحة بدون أي شيء مؤقت أو ناقص. " * 30
        html = (
            "<html><body>"
            f"<section id='hero'><h1>عنوان رئيسي</h1><p>{body}</p></section>"
            f"<section id='features'><h2>المزايا</h2><p>{body}</p></section>"
            f"<section id='cta'><h2>ابدأ الآن</h2><p>{body}</p></section>"
            "</body></html>"
        )
        ctx = _make_ctx({"about.html": html}, active="about.html")
        res = fa_mod._exec_tool(ctx, "mark_page_built", {"filename": "about.html"})
        assert res.get("ok") is True, f"complete page should be accepted: {res}"
        assert "about.html" in (res.get("built_pages") or [])

    def test_unknown_filename_rejected(self):
        ctx = _make_ctx({"index.html": "<html></html>"}, active="index.html")
        res = fa_mod._exec_tool(ctx, "mark_page_built", {"filename": "ghost.html"})
        assert res.get("ok") is False
        assert "غير موجودة" in (res.get("error") or "")


# ════════════════════════════════════════════════════════════════════════
# 4. write_full_html incomplete_warning
# ════════════════════════════════════════════════════════════════════════
class TestWriteFullHtmlIncompleteWarning:
    def test_warning_emitted_for_sub_threshold_output(self):
        sparse = "<html><body><section id='hero'><h1>X</h1><p>tiny</p></section></body></html>"
        ctx = _make_ctx({"index.html": "<html><body></body></html>"})
        res = fa_mod._exec_tool(
            ctx, "write_full_html",
            {"html": sparse, "allow_full_rewrite": True},
        )
        # ok=True (write succeeded) but a warning should be present.
        assert res.get("ok") is True
        assert "incomplete_warning" in res, f"warning missing: {res}"
        assert res.get("section_count") == 1
        assert res.get("meaningful_chars", 0) < 600

    def test_no_warning_for_complete_output(self):
        body = "نص حقيقي وغني بالمعلومات للصفحة الكاملة. " * 40
        html = (
            "<html><body>"
            f"<section id='hero'><h1>عنوان</h1><p>{body}</p></section>"
            f"<section id='body'><p>{body}</p></section>"
            "</body></html>"
        )
        ctx = _make_ctx({"index.html": "<html><body></body></html>"})
        res = fa_mod._exec_tool(
            ctx, "write_full_html",
            {"html": html, "allow_full_rewrite": True},
        )
        assert res.get("ok") is True
        assert "incomplete_warning" not in res, "complete page must NOT trigger warning"
        assert res.get("section_count") >= 2
        assert res.get("meaningful_chars", 0) >= 600


# ════════════════════════════════════════════════════════════════════════
# 5. Lab-mode endpoint plumbing (source introspection)
# ════════════════════════════════════════════════════════════════════════
class TestLabModeBranchSource:
    """The /agent-chat-stream endpoint must have a mode='lab' branch that
    uses stream_agent_turn directly (no Brain orchestrator)."""

    def test_endpoint_accepts_mode_form_param(self):
        src = inspect.getsource(fc_mod)
        assert 'mode: str = Form("default")' in src

    def test_lab_branch_uses_stream_agent_turn(self):
        src = inspect.getsource(fc_mod)
        # Find the lab branch and confirm it calls stream_agent_turn
        # (not brain_stream_turn) within ~30 lines.
        idx = src.find('if mode == "lab":')
        assert idx > 0, "lab-mode branch missing"
        snippet = src[idx: idx + 3000]
        assert "stream_agent_turn(" in snippet, "lab branch must call stream_agent_turn"
        # Brain must NOT be invoked inside the lab branch — find the
        # boundary of the else: clause that uses Brain.
        else_idx = snippet.find("else:")
        if else_idx > 0:
            lab_only = snippet[:else_idx]
            assert "brain_stream_turn" not in lab_only, "lab branch must NOT call Brain"

    def test_default_branch_still_uses_brain(self):
        """Backwards compat: when mode != 'lab' the Brain orchestrator
        must still run (no regression)."""
        src = inspect.getsource(fc_mod)
        assert "brain_stream_turn(" in src

    def test_lab_uses_isolated_project_copy(self):
        """The lab branch must use proj_lab (a copy) so the real project's
        workflow_state is not mutated permanently."""
        src = inspect.getsource(fc_mod)
        idx = src.find('if mode == "lab":')
        lab_block = src[idx: idx + 2000]
        assert "proj_lab = dict(proj)" in lab_block, "lab must operate on a project copy"
        # Confirm DB update inside the lab block targets pages/current_html
        # but NEVER writes workflow_state back to the real project doc.
        # (Search for "workflow_state" inside the persist call.)
        persist_idx = lab_block.find("db.freebuild_projects.update_one")
        if persist_idx > 0:
            persist_block = lab_block[persist_idx: persist_idx + 500]
            assert "workflow_state" not in persist_block, (
                "lab persist must NOT write workflow_state to real project"
            )


# ════════════════════════════════════════════════════════════════════════
# 6. create_page emits HTML-comment placeholder only (no visible text)
# ════════════════════════════════════════════════════════════════════════
class TestCreatePageScaffoldNoVisibleText:
    """The new create_page template should NOT write 'محتوى الصفحة قيد
    البناء' as visible text in the body — only as an HTML comment that
    _strip_scaffold_placeholders can clean up at serve time even if the
    AI forgets to overwrite it."""

    def test_create_page_template_has_no_visible_arabic_placeholder(self):
        # Find the create_page handler region
        src = inspect.getsource(fa_mod)
        # locate the section by anchor used by the issue
        anchor = "SCAFFOLD_PLACEHOLDER"
        idx = src.find(anchor)
        assert idx > 0, "SCAFFOLD_PLACEHOLDER anchor not found in create_page"
        # Grab ~2000 chars around it
        region = src[max(0, idx - 2000): idx + 2000]
        # The visible literal "محتوى الصفحة قيد البناء" must not be embedded
        # as a string the template writes into <main> as visible text.
        # We allow it inside a comment only — assert it does NOT appear as
        # a plain Python string literal that goes into <p>/<section>/<main>
        # tags in the same region.
        visible_pattern = re.compile(
            r'<(p|h\d|section|main|div)[^>]*>\s*محتوى الصفحة قيد البناء',
        )
        assert not visible_pattern.search(region), (
            "create_page template must NOT emit visible 'قيد البناء' text"
        )


# ════════════════════════════════════════════════════════════════════════
# 7. Regression — module imports succeed (no syntax/import errors)
# ════════════════════════════════════════════════════════════════════════
class TestRegressionImports:
    def test_freebuild_chat_imports(self):
        assert hasattr(fc_mod, "_strip_scaffold_placeholders")
        assert hasattr(fc_mod, "_inject_zenrex_footer")

    def test_freebuild_agent_imports(self):
        assert hasattr(fa_mod, "FreeBuildToolContext")
        assert hasattr(fa_mod, "_exec_tool")
        assert hasattr(fa_mod, "stream_agent_turn")

    def test_workflow_engine_imports(self):
        from modules.freebuild import workflow_engine as we
        assert hasattr(we, "get_workflow_state")
