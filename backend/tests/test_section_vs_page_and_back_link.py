"""Tests for: section vs page intent disambiguation + auto-injected back-link."""
import pytest
from modules.freebuild.freebuild_agent import FreeBuildToolContext, _exec_tool
from modules.freebuild.action_pricing import classify_intent


# ─── Section vs Page intent ─────────────────────────────────────────────

class TestSectionVsPage:
    @pytest.mark.parametrize("msg", [
        "سوي لي قسم منفصل للأفلام",
        "اضف قسم جديد لعرض المنتجات",
        "اعمل لي قسم تعريفي",
        "ضيف قسم مميزات",
        "add a new section for testimonials",
    ])
    def test_section_intent_detected(self, msg):
        # These must classify as section_add — NOT page_creation
        assert classify_intent(msg) == "section_add", f"failed for {msg!r}"

    @pytest.mark.parametrize("msg", [
        "اضف صفحة منفصلة عن الأفلام",
        "انشئ صفحة about.html",
        "سوي صفحة جديدة للمنتجات",
        "create a new page for movies",
    ])
    def test_page_intent_still_works(self, msg):
        i = classify_intent(msg)
        assert i in ("page_creation", "move_section"), f"failed for {msg!r} → {i}"


# ─── Auto-injected back-to-home link ────────────────────────────────────

def test_create_page_auto_injects_home_link_when_missing():
    """If AI passes custom_html without an index.html link, the server
    must inject one so the user can navigate back."""
    proj = {
        "id": "p1", "user_id": "u1", "active_page": "index.html",
        "pages": {"index.html": "<html><body><nav></nav>home</body></html>"},
    }
    ctx = FreeBuildToolContext(proj)
    ctx.current_html = proj["pages"]["index.html"]
    bad_html = (
        '<!doctype html><html><body>'
        '<nav>  </nav>'
        '<h1>صفحة الأفلام</h1>'
        '<p>محتوى</p>'
        '</body></html>'
    )
    r = _exec_tool(ctx, "create_page", {
        "filename": "movies.html",
        "title": "الأفلام",
        "html": bad_html,
    })
    assert r["ok"], r
    assert "movies.html" in ctx.pages
    movies = ctx.pages["movies.html"]
    assert 'href="index.html"' in movies, f"home link missing! got: {movies}"


def test_create_page_with_existing_home_link_unchanged():
    proj = {
        "id": "p1", "user_id": "u1", "active_page": "index.html",
        "pages": {"index.html": "<html><body><nav></nav>home</body></html>"},
    }
    ctx = FreeBuildToolContext(proj)
    ctx.current_html = proj["pages"]["index.html"]
    good_html = (
        '<!doctype html><html><body>'
        '<nav><a href="index.html">الرئيسية</a></nav>'
        '<h1>صفحة الأفلام</h1>'
        '</body></html>'
    )
    r = _exec_tool(ctx, "create_page", {
        "filename": "movies.html",
        "title": "الأفلام",
        "html": good_html,
    })
    assert r["ok"]
    # Should still have exactly one home link (not duplicated)
    assert ctx.pages["movies.html"].count('href="index.html"') == 1


def test_create_page_no_nav_injects_full_nav_block():
    """If AI passes HTML without any <nav>/<header>, server injects a full
    nav block with the home link."""
    proj = {
        "id": "p1", "user_id": "u1", "active_page": "index.html",
        "pages": {"index.html": "<html><body><nav></nav>home</body></html>"},
    }
    ctx = FreeBuildToolContext(proj)
    ctx.current_html = proj["pages"]["index.html"]
    ugly_html = (
        '<!doctype html><html><body>'
        '<h1>صفحة الأفلام</h1>'
        '<div>محتوى</div>'
        '</body></html>'
    )
    r = _exec_tool(ctx, "create_page", {
        "filename": "movies.html",
        "title": "الأفلام",
        "html": ugly_html,
    })
    assert r["ok"]
    out = ctx.pages["movies.html"]
    assert "<nav" in out.lower()
    assert 'href="index.html"' in out
