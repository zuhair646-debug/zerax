"""Tests for power tools: validate_js_handlers + check_navigation_graph
+ fetch_unsplash_image."""
import pytest
from modules.brain.power_tools import (
    validate_js_handlers,
    check_navigation_graph,
    fetch_unsplash_image,
)


# ─── validate_js_handlers ───────────────────────────────────────────────

class TestJSHandlerValidator:
    def test_clean_html_passes(self):
        html = """<html><body>
        <button onclick="addToCart(1)">إضافة</button>
        <script>function addToCart(id) { console.log(id); }</script>
        </body></html>"""
        r = validate_js_handlers(html)
        assert r["ok"]
        assert "addToCart" in r["defined_functions"]

    def test_broken_handler_caught(self):
        html = """<html><body>
        <button onclick="openMovie(42)">شاهد</button>
        <button onclick="addToCart()">سلة</button>
        <script>function addToCart() {}</script>
        </body></html>"""
        r = validate_js_handlers(html)
        assert not r["ok"]
        broken = [b["function"] for b in r["broken_handlers"]]
        assert "openMovie" in broken
        assert "addToCart" not in broken

    def test_builtins_allowed(self):
        html = """<html><body>
        <button onclick="alert('hi')">x</button>
        <button onclick="console.log('ok')">y</button>
        <button onclick="localStorage.setItem('a','b')">z</button>
        </body></html>"""
        r = validate_js_handlers(html)
        assert r["ok"]

    def test_method_calls_allowed(self):
        html = """<html><body>
        <button onclick="this.parentNode.remove()">x</button>
        </body></html>"""
        r = validate_js_handlers(html)
        assert r["ok"]

    def test_arrow_function_definitions_detected(self):
        html = """<html><body>
        <button onclick="openMovie(1)">x</button>
        <script>const openMovie = (id) => alert(id);</script>
        </body></html>"""
        r = validate_js_handlers(html)
        assert r["ok"]


# ─── check_navigation_graph ─────────────────────────────────────────────

class TestNavGraph:
    def test_clean_navigation(self):
        pages = {
            "index.html": '<a href="about.html">عن</a><a href="contact.html">تواصل</a>',
            "about.html": '<a href="index.html">رئيسية</a>',
            "contact.html": '<a href="index.html">رئيسية</a>',
        }
        r = check_navigation_graph(pages)
        assert r["ok"], r

    def test_broken_link_caught(self):
        pages = {
            "index.html": '<a href="missing.html">x</a>',
        }
        r = check_navigation_graph(pages)
        assert not r["ok"]
        assert len(r["broken_links"]) == 1

    def test_orphan_page_caught(self):
        pages = {
            "index.html": '<a href="about.html">x</a>',
            "about.html": '<a href="index.html">home</a>',
            "secret.html": '<h1>orphan</h1>',  # not linked from anywhere
        }
        r = check_navigation_graph(pages)
        assert not r["ok"]
        assert "secret.html" in r["orphan_pages"]

    def test_page_without_back_to_home_caught(self):
        pages = {
            "index.html": '<a href="movies.html">أفلام</a>',
            "movies.html": '<h1>أفلام</h1>',  # no link back to index
        }
        r = check_navigation_graph(pages)
        assert not r["ok"]
        assert "movies.html" in r["pages_without_home_link"]

    def test_index_missing(self):
        pages = {"about.html": "x"}
        r = check_navigation_graph(pages)
        assert not r["ok"]


# ─── fetch_unsplash_image ───────────────────────────────────────────────

class TestUnsplashFetch:
    def test_returns_urls(self):
        r = fetch_unsplash_image("red roses", "landscape", count=3)
        assert r["ok"]
        assert len(r["images"]) == 3
        for url in r["images"]:
            assert "unsplash.com" in url
            assert "red+roses" in url or "red%20roses" in url

    def test_empty_query_rejected(self):
        r = fetch_unsplash_image("")
        assert not r["ok"]

    def test_default_orientation_landscape(self):
        r = fetch_unsplash_image("office")
        assert r["ok"]
        assert "1600x900" in r["images"][0]
