"""Tests for the In-Turn Dummy Detector + Auto-wire anchor rewriting.

Run: pytest /app/backend/tests/test_dummy_detector.py -v
"""
import pytest
from modules.freebuild.freebuild_agent import _scan_for_dummy_ui


def test_clean_html_passes():
    html = """<!doctype html><html><body>
    <nav><a href="index.html">Home</a><a href="about.html">About</a></nav>
    <button onclick="alert('hi')">Click</button>
    <form action="/submit"><button type="submit">Send</button></form>
    </body></html>"""
    r = _scan_for_dummy_ui(html)
    assert r["ok"]
    assert r["total_problems"] == 0


def test_dead_button_caught():
    html = """<html><body>
    <button>أضف للسلة</button>
    <button onclick="addToCart()">Real</button>
    </body></html>"""
    r = _scan_for_dummy_ui(html)
    assert not r["ok"]
    assert len(r["dead_buttons"]) == 1
    assert r["dead_buttons"][0]["text"] == "أضف للسلة"


def test_dead_button_with_js_wiring_is_clean():
    html = """<html><body>
    <button id="cart-btn">السلة</button>
    <script>document.getElementById('cart-btn').addEventListener('click', ()=>{});</script>
    </body></html>"""
    r = _scan_for_dummy_ui(html)
    assert r["ok"], f"Expected clean, got {r}"


def test_fake_nav_caught():
    html = """<html><body>
    <nav>
      <a href="#">الرئيسية</a>
      <a href="#products">المنتجات</a>
    </nav>
    <section id="products">products here</section>
    </body></html>"""
    r = _scan_for_dummy_ui(html)
    assert len(r["fake_nav_links"]) == 1
    assert r["fake_nav_links"][0]["text"] == "الرئيسية"


def test_broken_anchor_caught():
    html = """<html><body>
    <nav><a href="#products">Products</a><a href="#missing">Gone</a></nav>
    <section id="products">ok</section>
    </body></html>"""
    r = _scan_for_dummy_ui(html)
    assert len(r["broken_anchors"]) == 1
    assert r["broken_anchors"][0]["href"] == "#missing"


def test_dead_form_caught():
    html = """<html><body>
    <form id="contact-form">
      <input name="email"/>
      <button type="submit">Send</button>
    </form>
    </body></html>"""
    r = _scan_for_dummy_ui(html)
    assert len(r["dead_forms"]) == 1


def test_form_with_js_wiring_is_clean():
    html = """<html><body>
    <form id="contact-form">
      <input name="email"/>
      <button type="submit">Send</button>
    </form>
    <script>document.getElementById('contact-form').addEventListener('submit', function(e){});</script>
    </body></html>"""
    r = _scan_for_dummy_ui(html)
    assert r["ok"], f"Got {r}"


def test_social_icons_not_flagged():
    """Social media icons with href='#' are soft placeholders, not 'fake nav'."""
    html = """<html><body>
    <footer>
      <a href="#"><i class="fab fa-instagram"></i></a>
      <a href="#"><i class="fab fa-twitter"></i></a>
      <a href="#">📷</a>
    </footer>
    </body></html>"""
    r = _scan_for_dummy_ui(html)
    assert r["ok"]
    assert r["soft_social_placeholders"] >= 2


def test_create_page_rewrites_anchor_links():
    """When create_page is called with a stem matching existing #anchor links,
    the auto-wire should rewrite them to point to the new file."""
    from modules.freebuild.freebuild_agent import FreeBuildToolContext, _exec_tool
    proj = {
        "id": "p1", "user_id": "u1",
        "active_page": "index.html",
        "pages": {
            "index.html": (
                '<!doctype html><html><body>'
                '<nav>'
                '<a href="#products">المنتجات</a>'
                '<a href="#about">من نحن</a>'
                '<a href="#contact">تواصل</a>'
                '</nav>'
                '<section id="products">prods</section>'
                '<footer><a href="#about">من نحن</a></footer>'
                '</body></html>'
            )
        },
        "current_html": "",
    }
    ctx = FreeBuildToolContext(proj)
    ctx.current_html = ctx.pages["index.html"]
    r = _exec_tool(ctx, "create_page", {"filename": "about.html", "title": "من نحن"})
    assert r["ok"]
    # The two #about anchors in index should now point to about.html
    idx = ctx.pages["index.html"]
    assert idx.count('href="about.html"') >= 2, f"expected 2+ about.html links, got {idx}"
    # The #products anchor should be UNTOUCHED (because <section id='products'> exists)
    assert 'href="#products"' in idx
    # #contact remains as anchor (no contact.html created)
    assert 'href="#contact"' in idx
    assert r["anchors_rewritten"] >= 2


def test_write_full_html_auto_rewrites_anchors_to_existing_pages():
    """After about.html and contact.html exist, writing index.html with
    href='#about' anchors should auto-rewrite to href='about.html'."""
    from modules.freebuild.freebuild_agent import FreeBuildToolContext, _exec_tool
    proj = {
        "id": "p1", "user_id": "u1", "active_page": "index.html",
        "pages": {
            "index.html": "<html><body><h1>old</h1></body></html>",  # ≥800 chars rule bypass
            "about.html": "<html><body>about</body></html>",
            "contact.html": "<html><body>contact</body></html>",
        },
        "current_html": "",
        "design_unlocked": True,  # allow rewrite for the test
    }
    ctx = FreeBuildToolContext(proj)
    new_html = (
        '<!doctype html><html><body>'
        '<nav>'
        '<a href="#home">Home</a>'
        '<a href="#about">About</a>'
        '<a href="#contact">Contact</a>'
        '<a href="#products">Products</a>'
        '</nav>'
        '<section id="hero">Hero</section>'
        '<section id="products">Products section</section>'
        '</body></html>'
    )
    r = _exec_tool(ctx, "write_full_html",
                    {"html": new_html, "allow_full_rewrite": True})
    assert r["ok"], r
    out = ctx.current_html
    assert 'href="about.html"' in out, f"expected about.html link, got {out}"
    assert 'href="contact.html"' in out, f"expected contact.html link, got {out}"
    # #products has a local section → must be preserved as anchor
    assert 'href="#products"' in out
    assert r.get("anchor_to_page_rewrites", 0) >= 2


def test_apply_section_auto_rewrites_anchors():
    """When apply_section adds a nav with #about anchor and about.html exists,
    the anchor should auto-resolve to about.html."""
    from modules.freebuild.freebuild_agent import FreeBuildToolContext, _exec_tool
    proj = {
        "id": "p1", "user_id": "u1", "active_page": "index.html",
        "pages": {
            "index.html": (
                '<!doctype html><html><body>'
                '<section id="nav-host">old nav here</section>'
                '<section id="hero">hero</section>'
                '</body></html>'
            ),
            "about.html": "<html><body>about</body></html>",
        },
        "current_html": "",
    }
    ctx = FreeBuildToolContext(proj)
    ctx.current_html = ctx.pages["index.html"]
    r = _exec_tool(ctx, "apply_section", {
        "id": "nav-host",
        "html": '<section id="nav-host"><a href="#about">من نحن</a></section>',
        "op": "replace",
    })
    assert r["ok"], r
    assert 'href="about.html"' in ctx.current_html
    assert r.get("anchor_to_page_rewrites", 0) >= 1
