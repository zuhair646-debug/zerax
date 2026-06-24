"""Tests for Smart-Merge — protects against destructive write_full_html calls.

When the AI calls `write_full_html` on an established page (≥800 chars) and
omits sections that existed before, Smart-Merge splices the missing sections
back in automatically. This was added because the AI repeatedly destroyed
approved sections when asked for surgical edits.
"""
import re

from backend.modules.freebuild import freebuild_agent as fa


SECTION_HERO = (
    '<section id="hero"><h1>Hero</h1>'
    '<p>' + ('x' * 400) + '</p></section>'
)
SECTION_FEATURES = (
    '<section id="features"><h2>Features</h2>'
    '<ul><li>One</li><li>Two</li><li>Three</li></ul></section>'
)
SECTION_PRICING = (
    '<section id="pricing"><h2>Pricing</h2>'
    '<p>$10/month</p></section>'
)


def _full(*sections: str) -> str:
    body = "\n".join(sections)
    return f"<!DOCTYPE html><html><body><main>{body}</main></body></html>"


class TestSmartMergeHelper:
    def test_returns_new_html_unchanged_when_no_sections_missing(self):
        old = _full(SECTION_HERO, SECTION_FEATURES)
        new = _full(SECTION_HERO, SECTION_FEATURES)
        merged, preserved = fa._smart_merge_preserve_sections(old, new)
        assert preserved == []
        assert merged == new

    def test_splices_missing_section_before_main_close(self):
        old = _full(SECTION_HERO, SECTION_FEATURES, SECTION_PRICING)
        # AI writes new HTML that forgot #features and #pricing
        new = _full(SECTION_HERO)
        merged, preserved = fa._smart_merge_preserve_sections(old, new)
        assert set(preserved) == {"features", "pricing"}
        # All three section IDs must be present in the merged result
        ids = set(re.findall(
            r'<section\b[^>]*\bid\s*=\s*["\']([a-zA-Z0-9_\-]+)["\']',
            merged, re.IGNORECASE,
        ))
        assert {"hero", "features", "pricing"} <= ids
        # The spliced sections sit before </main>
        assert merged.index("</main>") > merged.index("<section id=\"features\"")
        assert merged.index("</main>") > merged.index("<section id=\"pricing\"")

    def test_splices_before_body_when_no_main(self):
        old = (
            "<!DOCTYPE html><html><body>"
            + SECTION_HERO + SECTION_FEATURES
            + "</body></html>"
        )
        new = "<!DOCTYPE html><html><body>" + SECTION_HERO + "</body></html>"
        merged, preserved = fa._smart_merge_preserve_sections(old, new)
        assert preserved == ["features"]
        assert "<section id=\"features\"" in merged
        # Spliced before </body>
        assert merged.index("</body>") > merged.index("<section id=\"features\"")

    def test_handles_empty_inputs_gracefully(self):
        assert fa._smart_merge_preserve_sections("", "<html></html>") == ("<html></html>", [])
        assert fa._smart_merge_preserve_sections("<html></html>", "") == ("", [])

    def test_preserves_section_order_from_original(self):
        # When 3 sections are missing, they are spliced in original order
        old = _full(SECTION_HERO, SECTION_FEATURES, SECTION_PRICING)
        new = _full(
            '<section id="new"><h1>New</h1><p>brand new</p></section>'
        )
        merged, preserved = fa._smart_merge_preserve_sections(old, new)
        assert preserved == ["hero", "features", "pricing"]
        # The original order must be respected in the spliced block
        hero_pos = merged.index("<section id=\"hero\"")
        features_pos = merged.index("<section id=\"features\"")
        pricing_pos = merged.index("<section id=\"pricing\"")
        assert hero_pos < features_pos < pricing_pos


class TestSmartMergeIntegrationWithWriteFullHtml:
    def _ctx(self, html: str):
        project = {
            "id": "test-project",
            "user_id": "test-user",
            "pages": {"index.html": html},
            "active_page": "index.html",
            "current_html": html,
            # Bypass the discovery soft-gate so write_full_html runs the
            # Smart-Merge logic we are exercising in these tests.
            "workflow_state": {"stage": "surgical_edit", "discovery_answers": {}},
        }
        return fa.FreeBuildToolContext(project)

    def test_write_full_html_preserves_forgotten_sections(self):
        old = _full(SECTION_HERO, SECTION_FEATURES, SECTION_PRICING)
        ctx = self._ctx(old)
        # AI tries to "fix the hero" but writes a new doc that only has #hero
        new = _full(SECTION_HERO.replace("Hero", "Brand-new Hero"))
        result = fa._exec_tool(ctx, "write_full_html", {"html": new})
        assert result.get("ok") is True
        assert set(result.get("preserved_sections", [])) == {"features", "pricing"}
        # The active page now contains all three sections
        final = ctx.pages["index.html"]
        ids = set(re.findall(
            r'<section\b[^>]*\bid\s*=\s*["\']([a-zA-Z0-9_\-]+)["\']',
            final, re.IGNORECASE,
        ))
        assert {"hero", "features", "pricing"} <= ids
        # The new hero content was honoured
        assert "Brand-new Hero" in final

    def test_allow_full_rewrite_bypasses_smart_merge(self):
        old = _full(SECTION_HERO, SECTION_FEATURES, SECTION_PRICING)
        ctx = self._ctx(old)
        new = _full(SECTION_HERO)
        result = fa._exec_tool(
            ctx, "write_full_html",
            {"html": new, "allow_full_rewrite": True},
        )
        assert result.get("ok") is True
        # When the user explicitly approves a full rewrite, Smart-Merge stays out.
        assert "preserved_sections" not in result
        ids = set(re.findall(
            r'<section\b[^>]*\bid\s*=\s*["\']([a-zA-Z0-9_\-]+)["\']',
            ctx.pages["index.html"], re.IGNORECASE,
        ))
        assert ids == {"hero"}

    def test_skipped_on_small_existing_html(self):
        small = "<html><body><p>tiny</p></body></html>"
        ctx = self._ctx(small)
        new = _full(SECTION_HERO)
        result = fa._exec_tool(ctx, "write_full_html", {"html": new})
        assert result.get("ok") is True
        # No preservation needed (existing HTML was too small).
        assert "preserved_sections" not in result


class TestPagesOverviewHelper:
    def test_lists_each_page_with_section_ids(self):
        pages = {
            "index.html": _full(SECTION_HERO, SECTION_FEATURES),
            "movies.html": _full(
                '<section id="catalog"><h2>Catalog</h2></section>'
                '<section id="filters"><h2>Filters</h2></section>'
            ),
            "points.html": _full(
                '<section id="balance"><h2>Balance</h2></section>'
            ),
        }
        out = fa._build_pages_overview(pages, "index.html")
        assert "خريطة المشروع" in out
        assert "index.html" in out
        assert "movies.html" in out
        assert "points.html" in out
        assert "#hero" in out
        assert "#features" in out
        assert "#catalog" in out
        assert "#filters" in out
        assert "#balance" in out
        # Active marker on index.html
        assert "(active)" in out

    def test_empty_pages_returns_empty_string(self):
        assert fa._build_pages_overview({}, "index.html") == ""
