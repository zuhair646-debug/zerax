"""Tests for move_section_to_page + keep_only_sections + new intent classifications.

Run: pytest /app/backend/tests/test_move_keep_tools.py -v
"""
import pytest
from modules.freebuild.freebuild_agent import FreeBuildToolContext, _exec_tool
from modules.freebuild.action_pricing import classify_intent


# ─── Intent classifier additions ─────────────────────────────────────────────

class TestNewIntents:
    @pytest.mark.parametrize("msg,expected", [
        # keep_only — describe what to KEEP
        ("خلّي لي بس المنتجات", "keep_only"),
        ("اخلي بس المنتجات والسلة", "keep_only"),
        ("احتفظ فقط بقسم المنتجات", "keep_only"),
        ("ابقي بس المنتجات لو سمحت", "keep_only"),
        ("keep only the products section", "keep_only"),
        # move_section — describe what to MOVE
        ("انقل القسم لصفحة منفصلة", "move_section"),
        ("انقل قسم السلة في صفحه مستقله", "move_section"),
        ("حط الخريطه في صفحه لحالها", "move_section"),
        ("حول قسم المنتجات لصفحه منفصله", "move_section"),
        ("move the cart section to its own page", "move_section"),
        # baseline — make sure we didn't break old intents
        ("احذف قسم الفوتر", "deletion"),
        ("شيل الفوتر", "deletion"),
        ("اصلح الزر", "repair"),
        ("hi", "chat"),
    ])
    def test_intent(self, msg, expected):
        assert classify_intent(msg) == expected, f"{msg!r} → got {classify_intent(msg)}"


# ─── move_section_to_page ────────────────────────────────────────────────────

def _make_ctx_with_sections():
    """Build a context with index.html containing 3 sections + a nav."""
    html = (
        '<!doctype html><html dir="rtl" lang="ar"><head><title>متجر</title></head><body>\n'
        '<nav>\n'
        '  <a href="#products" class="nav-link">المنتجات</a>\n'
        '  <a href="#cart" class="nav-link">السلة</a>\n'
        '  <a href="#map" class="nav-link">الخريطة</a>\n'
        '</nav>\n'
        '<section id="products"><h2>المنتجات</h2><div>منتج 1</div></section>\n'
        '<section id="cart"><h2>السلة</h2><button onclick="checkout()">اشتر</button></section>\n'
        '<section id="map"><h2>خريطة</h2><div id="leaflet"></div></section>\n'
        '<footer><a href="#cart">السلة</a></footer>\n'
        '</body></html>'
    )
    proj = {
        "id": "p1", "user_id": "u1",
        "active_page": "index.html",
        "pages": {"index.html": html},
        "current_html": "",
    }
    ctx = FreeBuildToolContext(proj)
    ctx.current_html = html
    return ctx


def test_move_section_extracts_from_source():
    ctx = _make_ctx_with_sections()
    r = _exec_tool(ctx, "move_section_to_page", {
        "section_id": "cart",
        "target_filename": "cart.html",
        "target_title": "سلة المشتريات",
    })
    assert r["ok"], r
    # Source page no longer contains the cart section
    src = ctx.pages["index.html"]
    assert 'id="cart"' not in src, f"cart still in index: {src[:200]}"
    # But still has products and map
    assert 'id="products"' in src
    assert 'id="map"' in src


def test_move_section_inserts_into_target():
    ctx = _make_ctx_with_sections()
    _exec_tool(ctx, "move_section_to_page", {
        "section_id": "cart",
        "target_filename": "cart.html",
        "target_title": "السلة",
    })
    assert "cart.html" in ctx.pages
    tgt = ctx.pages["cart.html"]
    assert 'id="cart"' in tgt
    assert 'onclick="checkout()"' in tgt


def test_move_section_rewrites_anchors_to_real_page():
    """After moving #cart to cart.html, any <a href="#cart"> in remaining
    pages must not survive — either stripped (in nav) or rewritten."""
    ctx = _make_ctx_with_sections()
    _exec_tool(ctx, "move_section_to_page", {
        "section_id": "cart",
        "target_filename": "cart.html",
        "target_title": "السلة",
    })
    src = ctx.pages["index.html"]
    # No broken #cart anchor should remain
    assert 'href="#cart"' not in src, f"broken #cart anchor still present: {src}"


def test_move_section_creates_target_if_missing():
    ctx = _make_ctx_with_sections()
    assert "map.html" not in ctx.pages
    r = _exec_tool(ctx, "move_section_to_page", {
        "section_id": "map",
        "target_filename": "map.html",
        "target_title": "خريطة الفروع",
    })
    assert r["ok"]
    assert "map.html" in ctx.pages


def test_move_section_rejects_invalid_target():
    ctx = _make_ctx_with_sections()
    r = _exec_tool(ctx, "move_section_to_page", {
        "section_id": "cart",
        "target_filename": "index.html",
        "target_title": "x",
    })
    assert not r["ok"]
    assert "index.html" in r["error"]


def test_move_section_rejects_missing_section():
    ctx = _make_ctx_with_sections()
    r = _exec_tool(ctx, "move_section_to_page", {
        "section_id": "nonexistent",
        "target_filename": "x.html",
        "target_title": "X",
    })
    assert not r["ok"]
    assert "not found" in r["error"].lower()


# ─── keep_only_sections ──────────────────────────────────────────────────────

def test_keep_only_sections_removes_others():
    ctx = _make_ctx_with_sections()
    r = _exec_tool(ctx, "keep_only_sections", {"keep_ids": ["products"]})
    assert r["ok"], r
    src = ctx.pages["index.html"]
    assert 'id="products"' in src
    assert 'id="cart"' not in src
    assert 'id="map"' not in src
    assert set(r["removed_ids"]) == {"cart", "map"}


def test_keep_only_sections_keeps_multiple():
    ctx = _make_ctx_with_sections()
    r = _exec_tool(ctx, "keep_only_sections", {"keep_ids": ["products", "cart"]})
    assert r["ok"]
    src = ctx.pages["index.html"]
    assert 'id="products"' in src
    assert 'id="cart"' in src
    assert 'id="map"' not in src


def test_keep_only_sections_rejects_empty():
    ctx = _make_ctx_with_sections()
    r = _exec_tool(ctx, "keep_only_sections", {"keep_ids": []})
    assert not r["ok"]


def test_keep_only_sections_noop_when_already_matches():
    ctx = _make_ctx_with_sections()
    r = _exec_tool(ctx, "keep_only_sections",
                    {"keep_ids": ["products", "cart", "map"]})
    # Nothing to delete is an error (so the AI doesn't claim success on noop)
    assert not r["ok"]
