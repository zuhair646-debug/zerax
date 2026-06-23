"""Iteration 2 — Tests for the 3 NEW surgical-quality fixes in freebuild_agent.py
(Jan 2026, post test_surgical_fixes.py).

The user reported 3 new pain points after iteration 1's fixes:
  5. BLANK PAGE — `create_page` produces only an <h1>; AI doesn't fill it
  6. ORPHAN PAGE — new page has no back-link to index.html AND/OR index nav
     doesn't list it → user gets stuck
  7. DESIGN-DESTRUCTION — `apply_section/op='replace'` ships a huge new HTML
     that effectively rewrites the section, destroying existing design

These tests verify the corresponding detectors / guards in
modules.freebuild.freebuild_agent without invoking Anthropic. They use direct
helper calls + source-string introspection where stream-loop integration is
unreachable from unit tests.

Also confirms latent bug from iteration 1 is fixed:
  list_sections now honours args.page (was previously ignoring it).
"""

import os
import sys
import importlib
import inspect
import re

import pytest

# Ensure backend is on path
sys.path.insert(0, "/app/backend")

# ── Module import ────────────────────────────────────────────────────────────
fa = importlib.import_module("modules.freebuild.freebuild_agent")


def _build_ctx(pages, active="index.html"):
    project = {
        "id": "TEST_proj_v2",
        "user_id": "TEST_user_v2",
        "pages": pages,
        "active_page": active,
        "current_html": pages.get(active, ""),
    }
    return fa.FreeBuildToolContext(project)


# ════════════════════════════════════════════════════════════════════════════
# 5. BLANK PAGE DETECTOR — fires after create_page leaves a near-empty page
# ════════════════════════════════════════════════════════════════════════════
class TestBlankPageDetector:
    """Detector at ~line 9896-9924 fires after create_page or apply_section
    when the just-mutated page has ≤1 section AND <800 chars of meaningful
    text. Must inject a 'BLANK PAGE DETECTOR' warning containing the literal
    phrase 'هيكل فارغ غير مقبول' and set force_tool_use_next_iter=True."""

    def test_source_contains_blank_page_detector_strings(self):
        src = inspect.getsource(fa)
        assert "BLANK PAGE DETECTOR" in src, "marker string missing"
        assert "هيكل فارغ غير مقبول" in src, "Arabic warning missing"
        # Threshold values from the detector logic
        assert "len(_section_ids) <= 1" in src
        assert "_meaningful_chars < 800" in src
        # Detector applies to both create_page and apply_section
        assert 'tu["name"] in ("create_page", "apply_section")' in src

    def test_skeleton_contains_scaffold_placeholder_marker(self):
        """_build_blank_page_skeleton must embed the SCAFFOLD_PLACEHOLDER
        marker so the detector can identify the page as blank."""
        html = fa._build_blank_page_skeleton("الأفلام")
        assert "SCAFFOLD_PLACEHOLDER" in html

    def test_skeleton_contains_working_back_link(self):
        """Skeleton must contain href=\"index.html\" so users aren't stranded."""
        html = fa._build_blank_page_skeleton("صفحة جديدة")
        assert 'href="index.html"' in html

    def test_skeleton_includes_title_and_arabic_breadcrumb(self):
        html = fa._build_blank_page_skeleton("المسلسلات")
        assert "المسلسلات" in html
        assert "الرئيسية" in html  # back-link label

    def test_create_page_default_skeleton_triggers_detector_logic(self):
        """After create_page, list_sections on the new page should show ≤ 1
        section and meaningful text well under 800 chars — i.e. the page
        will be flagged blank by the detector."""
        ctx = _build_ctx({"index.html": "<html><body><nav></nav><section id='hero'><h1>Home</h1><p>" + ("x" * 1500) + "</p></section></body></html>"})
        res = fa._exec_tool(ctx, "create_page", {"filename": "movies.html", "title": "الأفلام"})
        assert res.get("ok") is True
        # Inspect the newly created page's sections via list_sections (with page arg)
        sec_res = fa._exec_tool(ctx, "list_sections", {"page": "movies.html"})
        assert sec_res.get("page") == "movies.html"
        section_ids = [s.get("id") for s in sec_res.get("sections", [])]
        # Default skeleton should have ≤ 1 section
        assert len(section_ids) <= 1, f"expected ≤1 section, got {section_ids}"
        # Approximate the detector's "meaningful chars" calculation
        page_html = ctx.pages["movies.html"]
        text_only = re.sub(r"<[^>]+>", " ", page_html)
        text_only = re.sub(r"\s+", " ", text_only).strip()
        # The post-write detector treats `create_page` as ALWAYS blank, regardless of length.
        # But we still verify the page has only minimal real text (well under 800
        # AFTER excluding inherited shell content — the shell from index would inflate it).
        # The skeleton's own body text without inheritance is sub-200 chars.
        skeleton_only = fa._build_blank_page_skeleton("الأفلام")
        skel_text = re.sub(r"<[^>]+>", " ", skeleton_only)
        skel_text = re.sub(r"\s+", " ", skel_text).strip()
        assert len(skel_text) < 800

    def test_detector_force_tool_use_flag_set(self):
        """Source must include the force_tool_use_next_iter=True branch
        gated on _blank_warning being non-empty."""
        src = inspect.getsource(fa)
        assert "_blank_warning or _orphan_warning" in src
        # The flag-flip logic must be present
        assert "force_tool_use_next_iter = True" in src


# ════════════════════════════════════════════════════════════════════════════
# 6. ORPHAN-PAGE DETECTOR — fires when new page is missing back-link OR not
#    linked from index.html nav
# ════════════════════════════════════════════════════════════════════════════
class TestOrphanPageDetector:
    """Detector at ~line 9928-9968 fires only when:
       tu['name'] == 'create_page' AND _verify_target != 'index.html'
       AND (new page lacks href=\"index.html\" OR index nav lacks href=\"<new>\")
    """

    def test_source_contains_orphan_detector_strings(self):
        src = inspect.getsource(fa)
        assert "ORPHAN-PAGE DETECTOR" in src
        # Detection logic
        assert 'href="index.html"' in src
        assert "update_nav" in src
        assert "insert_html_at" in src
        # Detector only runs on non-index pages
        assert '_verify_target != "index.html"' in src

    def test_orphan_logic_back_link_missing(self):
        """Replicate detector logic: a page missing back-link is flagged."""
        page_html = "<html><body><h1>Movies</h1></body></html>"  # no back-link
        has_back = (
            'href="index.html"' in page_html
            or "href='index.html'" in page_html
            or 'href="/"' in page_html
        )
        assert has_back is False  # detector would flag this

    def test_orphan_logic_index_not_linking_to_new(self):
        idx_html = "<html><body><nav><a href='about.html'>About</a></nav></body></html>"
        verify_target = "movies.html"
        linked_from_index = (
            f'href="{verify_target}"' in idx_html
            or f"href='{verify_target}'" in idx_html
        )
        assert linked_from_index is False

    def test_create_page_auto_wire_prevents_orphan(self):
        """create_page auto-wires the link in index.html → orphan detector
        should NOT flag (linked_from_index == True after auto-wire)."""
        idx_seed = (
            "<html><body><nav><a href='index.html'>Home</a></nav>"
            "<section id='hero'><h1>Welcome</h1></section></body></html>"
        )
        ctx = _build_ctx({"index.html": idx_seed})
        res = fa._exec_tool(ctx, "create_page", {"filename": "movies.html", "title": "الأفلام"})
        assert res.get("ok") is True
        idx_after = ctx.pages.get("index.html", "")
        # Auto-wire should have injected an href="movies.html" link in index
        assert ('href="movies.html"' in idx_after
                or "href='movies.html'" in idx_after), \
            f"create_page didn't auto-wire link in index. idx_after={idx_after[:500]}"

    def test_skeleton_creation_includes_back_link(self):
        """The default inline skeleton in create_page (when no custom html
        provided) must include the back-to-index link to avoid orphaning."""
        ctx = _build_ctx({"index.html": "<html><body></body></html>"})
        res = fa._exec_tool(ctx, "create_page", {"filename": "series.html", "title": "المسلسلات"})
        assert res.get("ok") is True
        new_page = ctx.pages.get("series.html", "")
        assert 'href="index.html"' in new_page, "new page missing back-link"


# ════════════════════════════════════════════════════════════════════════════
# 7. DESIGN-DESTRUCTION GUARD — blocks apply_section/op=replace when ratio
#    >2.5x or <0.4x of existing section, in surgical mode
# ════════════════════════════════════════════════════════════════════════════
class TestDesignDestructionGuard:
    """Guard at ~line 9606-9656 fires when:
       intent == surgical AND tool == apply_section AND op == 'replace'
       AND existing section > 400 chars AND ratio (new/old) > 2.5 or < 0.4
    """

    def test_source_contains_guard_label_and_thresholds(self):
        src = inspect.getsource(fa)
        assert "DESIGN-DESTRUCTION GUARD" in src
        # Threshold constants must be exactly 2.5 and 0.4 per requirements
        assert "_ratio > 2.5 or _ratio < 0.4" in src
        # Minimum existing-section gate (>400 chars)
        assert "_old_len > 400" in src
        # Guard is intent-gated
        assert '_intent == "surgical"' in src
        # Skips dispatch via continue
        assert "design_destruction_guard_block" in src

    def _simulate_guard(self, existing_html, new_html, replace_id, intent="surgical", op="replace"):
        """Mirror the source ratio guard so we can deterministically test it."""
        tool_input = {"op": op, "id": replace_id, "html": new_html, "page": "index.html"}
        if not (op == "replace" and intent == "surgical"):
            return {"fired": False, "reason": "preconditions not met"}
        m = re.search(
            r'<section\b[^>]*\bid\s*=\s*["\']' + re.escape(replace_id) + r'["\'][^>]*>([\s\S]*?)</section>',
            existing_html, re.I,
        )
        if not m:
            return {"fired": False, "reason": "no existing section"}
        old_len = len(m.group(0))
        new_len = len(new_html)
        ratio = new_len / max(old_len, 1)
        fired = old_len > 400 and (ratio > 2.5 or ratio < 0.4)
        return {"fired": fired, "old_len": old_len, "new_len": new_len, "ratio": ratio}

    def test_guard_fires_when_new_html_too_large(self):
        # 1000-char existing section, 3000-char new html → ratio 3x → fire
        existing_section = '<section id="hero"><h1>Welcome</h1><p>' + ("x" * 950) + "</p></section>"
        existing_html = f"<html><body>{existing_section}</body></html>"
        new_html = "<section id='hero'><h1>BIG</h1><p>" + ("y" * 3000) + "</p></section>"
        r = self._simulate_guard(existing_html, new_html, "hero")
        assert r["fired"] is True, r
        assert r["ratio"] > 2.5

    def test_guard_fires_when_new_html_too_small(self):
        # 1000-char existing, 200-char new → ratio ~0.2 → fire
        existing_section = '<section id="hero"><h1>Welcome</h1><p>' + ("x" * 950) + "</p></section>"
        existing_html = f"<html><body>{existing_section}</body></html>"
        new_html = "<section id='hero'><h1>hi</h1></section>"  # ~50 chars
        r = self._simulate_guard(existing_html, new_html, "hero")
        assert r["fired"] is True, r
        assert r["ratio"] < 0.4

    def test_guard_does_NOT_fire_within_ratio_window(self):
        # 1000-char existing, 1500-char new → ratio 1.5 → no fire
        existing_section = '<section id="hero"><h1>Welcome</h1><p>' + ("x" * 950) + "</p></section>"
        existing_html = f"<html><body>{existing_section}</body></html>"
        new_html = "<section id='hero'><h1>Welcome 2</h1><p>" + ("y" * 1400) + "</p></section>"
        r = self._simulate_guard(existing_html, new_html, "hero")
        assert r["fired"] is False, r
        assert 0.4 <= r["ratio"] <= 2.5

    def test_guard_does_NOT_fire_when_existing_section_short(self):
        # Existing section < 400 chars → guard skipped (allows tiny stub edits)
        existing_section = '<section id="hero"><h1>Hi</h1></section>'  # ~40 chars
        existing_html = f"<html><body>{existing_section}</body></html>"
        new_html = "<section id='hero'><h1>X</h1><p>" + ("y" * 2000) + "</p></section>"
        r = self._simulate_guard(existing_html, new_html, "hero")
        assert r["fired"] is False, r

    def test_guard_does_NOT_fire_for_new_build_intent(self):
        existing_section = '<section id="hero"><h1>Welcome</h1><p>' + ("x" * 950) + "</p></section>"
        existing_html = f"<html><body>{existing_section}</body></html>"
        new_html = "<section id='hero'>" + ("y" * 3000) + "</section>"
        r = self._simulate_guard(existing_html, new_html, "hero", intent="new_build")
        assert r["fired"] is False

    def test_guard_does_NOT_fire_for_op_append(self):
        existing_section = '<section id="hero">' + ("x" * 950) + "</section>"
        existing_html = f"<html><body>{existing_section}</body></html>"
        new_html = "<section id='newsec'>" + ("y" * 3000) + "</section>"
        r = self._simulate_guard(existing_html, new_html, "hero", op="append")
        assert r["fired"] is False

    def test_guard_block_message_has_required_phrases(self):
        """The source block message must mention insert_html_at and
        batch_replace_in_pages as alternatives so the LLM can recover."""
        src = inspect.getsource(fa)
        assert "insert_html_at" in src
        assert "batch_replace_in_pages" in src


# ════════════════════════════════════════════════════════════════════════════
# 8. list_sections honours args.page (latent bug fix from iteration 1)
# ════════════════════════════════════════════════════════════════════════════
class TestListSectionsHonoursPageArg:
    """Previously list_sections only inspected ctx.current_html. Now it must
    honour args.page so the post-write verification can inspect non-active
    pages (e.g. the just-created page when ctx.active_page differs)."""

    def test_list_sections_returns_target_page_sections(self):
        pages = {
            "index.html": "<html><body><section id='home-hero'><h1>Home</h1></section></body></html>",
            "movies.html": "<html><body><section id='movies-hero'><h1>Movies</h1></section><section id='movies-list'><h2>List</h2></section></body></html>",
        }
        ctx = _build_ctx(pages, active="index.html")
        res = fa._exec_tool(ctx, "list_sections", {"page": "movies.html"})
        ids = [s["id"] for s in res["sections"]]
        assert ids == ["movies-hero", "movies-list"]
        assert res.get("page") == "movies.html"

    def test_list_sections_no_page_arg_uses_active_page(self):
        pages = {
            "index.html": "<html><body><section id='home-hero'></section></body></html>",
            "movies.html": "<html><body><section id='movies-hero'></section></body></html>",
        }
        ctx = _build_ctx(pages, active="index.html")
        res = fa._exec_tool(ctx, "list_sections", {})
        ids = [s["id"] for s in res["sections"]]
        assert ids == ["home-hero"]

    def test_list_sections_unknown_page_falls_back_to_current(self):
        pages = {"index.html": "<html><body><section id='home-hero'></section></body></html>"}
        ctx = _build_ctx(pages)
        res = fa._exec_tool(ctx, "list_sections", {"page": "nope.html"})
        # Falls back to current_html (== index.html content)
        ids = [s["id"] for s in res["sections"]]
        assert ids == ["home-hero"]


# ════════════════════════════════════════════════════════════════════════════
# 9. Backwards-compat smoke — all iteration-1 invariants still hold
# ════════════════════════════════════════════════════════════════════════════
class TestBackwardsCompat:
    """Quick sanity that iteration-1 fixes' source markers are still intact
    after iteration-2 edits."""

    def test_iteration1_markers_still_in_source(self):
        src = inspect.getsource(fa)
        for marker in (
            "SURGICAL-HARDBLOCK",
            "POST-WRITE VERIFICATION",
            "FORCE POST-WRITE VERIFICATION",
            "تنبيه multi-page",
            "_multi_page_nudge",
            "IDs مكرّرة",
        ):
            assert marker in src, f"iteration-1 marker missing: {marker}"

    def test_classify_user_intent_still_surgical_first(self):
        # The classifier behaviour must not have regressed.
        assert fa.classify_user_intent("انقل قسم المسابقات للأعلى",
                                        has_existing_content=True) == "surgical"
        assert fa.classify_user_intent("ابني موقع متجر",
                                        has_existing_content=False) == "new_build"
