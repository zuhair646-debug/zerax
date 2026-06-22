"""Tests for layout unification — fixes the multi-page consistency bug."""
from modules.brain.power_tools.unify import (
    extract_layout_shell, inject_layout_shell, unify_pages_layout,
    _find_top_nav, _find_bottom_nav, _safe_bs4,
)


# Canonical reference HTML — what index.html looks like in a typical
# multi-page Arabic RTL Tailwind project (like Zaheer Market)
REF_HTML = """<!doctype html>
<html dir="rtl" lang="ar">
<head>
<title>الصفحة الرئيسية</title>
<meta charset="utf-8">
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/font-awesome/css/all.css">
<style>
:root { --accent: #d4af37; --bg: #0a0a0a; }
.btn-pill { border-radius: 999px; }
</style>
</head>
<body class="bg-slate-950 text-white min-h-screen rtl-layout" dir="rtl" data-theme="dark">
<header class="px-6 py-4 flex justify-between bg-gradient-to-r from-purple-900 to-pink-900">
  <a href="index.html" class="font-bold text-xl">🛒 زاهر ماركت</a>
  <nav><a href="contests.html">المسابقات</a> <a href="cart.html">السلة</a></nav>
</header>
<main>
  <h1>أهلاً</h1>
  <p>محتوى الرئيسية الفريد</p>
</main>
<footer class="text-center py-6 border-t border-white/10">© 2026 Zaheer</footer>
<nav class="fixed bottom-0 left-0 right-0 bg-black/80 backdrop-blur-md px-6 py-3 flex justify-around">
  <a href="index.html" class="w-12 h-12 rounded-full bg-pink-500 flex items-center justify-center">🏠</a>
  <a href="delivery.html" class="w-12 h-12 rounded-full bg-pink-500 flex items-center justify-center">🚚</a>
  <a href="contests.html" class="w-12 h-12 rounded-full bg-pink-500 flex items-center justify-center">🏆</a>
  <a href="cart.html" class="w-12 h-12 rounded-full bg-pink-500 flex items-center justify-center">🛒</a>
</nav>
</body>
</html>
"""


# A delivery page that looks DIFFERENT (the bug we're fixing)
BUG_PAGE = """<!doctype html>
<html lang="ar">
<head>
<title>التوصيل</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-blue-950">
<nav class="bg-blue-700 px-4 py-3">
  <a href="index.html">الرئيسية</a>
</nav>
<main>
  <h1>تتبع طلبك</h1>
</main>
<nav class="fixed bottom-0 bg-green-600 px-4 py-2 flex">
  <a href="index.html" class="w-10 h-10 rounded-md bg-green-500">🏠</a>
  <a href="delivery.html" class="w-10 h-10 rounded-md bg-green-500">🚚</a>
</nav>
</body>
</html>
"""


class TestShellExtraction:
    def test_extracts_top_and_bottom_nav(self):
        shell = extract_layout_shell(REF_HTML)
        assert shell["ok"]
        assert shell["has_top_nav"]
        assert shell["has_bottom_nav"]
        assert shell["has_footer"]
        # Bottom nav must contain the pink circles
        assert "fixed bottom-0" in shell["bottom_nav_html"]
        assert "bg-pink-500" in shell["bottom_nav_html"]
        # Top nav must be the <header> with the purple/pink gradient
        assert "زاهر ماركت" in shell["top_nav_html"]
        assert "from-purple-900" in shell["top_nav_html"]
        # Theme
        assert shell["theme_dir"] == "rtl"
        assert shell["theme_lang"] == "ar"
        # Body classes captured
        assert "bg-slate-950" in shell["body_classes"]

    def test_extracts_head_styles(self):
        shell = extract_layout_shell(REF_HTML)
        assert "tailwindcss" in shell["head_cdn"]
        assert ":root" in shell["head_styles"]
        assert "--accent" in shell["head_styles"]
        assert "font-awesome" in shell["head_styles"]

    def test_empty_html_returns_no_shell(self):
        shell = extract_layout_shell("<html></html>")
        assert shell["ok"]
        assert not shell["has_top_nav"]
        assert not shell["has_bottom_nav"]


class TestNavDetection:
    def test_finds_fixed_bottom_nav(self):
        soup = _safe_bs4(REF_HTML)
        bn = _find_bottom_nav(soup)
        assert bn is not None
        assert "bottom-0" in " ".join(bn.get("class") or [])

    def test_top_nav_is_header_not_bottom(self):
        soup = _safe_bs4(REF_HTML)
        tn = _find_top_nav(soup)
        bn = _find_bottom_nav(soup)
        assert tn is not None
        assert tn is not bn
        assert tn.name == "header"


class TestInjection:
    def test_replaces_bottom_nav_in_buggy_page(self):
        shell = extract_layout_shell(REF_HTML)
        result = inject_layout_shell(BUG_PAGE, shell)
        assert result["ok"]
        patched = result["html"]
        # The buggy green/square nav must be replaced by the pink/round one
        assert "bg-pink-500" in patched
        assert "bg-green-500" not in patched  # bug is fixed
        # Original page's unique content preserved
        assert "تتبع طلبك" in patched
        # Title preserved
        assert "<title>التوصيل</title>" in patched
        # Top nav from source applied (purple/pink gradient)
        assert "from-purple-900" in patched

    def test_preserves_main_content(self):
        shell = extract_layout_shell(REF_HTML)
        result = inject_layout_shell(BUG_PAGE, shell)
        # The <main><h1>تتبع طلبك</h1></main> must still be there
        assert "<h1>تتبع طلبك</h1>" in result["html"]

    def test_applies_body_classes(self):
        shell = extract_layout_shell(REF_HTML)
        result = inject_layout_shell(BUG_PAGE, shell)
        # body should now have bg-slate-950 (from ref), not bg-blue-950
        assert "bg-slate-950" in result["html"]


class TestFullUnification:
    def test_unifies_three_pages(self):
        pages = {
            "index.html": REF_HTML,
            "delivery.html": BUG_PAGE,
            "contests.html": BUG_PAGE.replace("التوصيل", "المسابقات")
                                      .replace("تتبع طلبك", "اربح جوايز"),
        }
        result = unify_pages_layout(pages)
        assert result["ok"]
        assert result["source"] == "index.html"
        assert result["updated_count"] == 2
        assert "delivery.html" in result["updated"]
        assert "contests.html" in result["updated"]
        # Each updated page now has the pink bottom-nav
        for fn in ("delivery.html", "contests.html"):
            patched = result["updated"][fn]
            assert "bg-pink-500" in patched
            assert "from-purple-900" in patched
            # Unique titles preserved
        assert "<title>التوصيل</title>" in result["updated"]["delivery.html"]
        assert "المسابقات" in result["updated"]["contests.html"]

    def test_missing_source_returns_error(self):
        pages = {"only.html": REF_HTML}
        result = unify_pages_layout(pages, source_page="nonexistent.html")
        assert not result["ok"]

    def test_no_shell_in_source_returns_error(self):
        bare = "<html><body><p>no nav or footer</p></body></html>"
        result = unify_pages_layout({"index.html": bare, "x.html": bare})
        assert not result["ok"]
        assert "shell" in result["error"]

    def test_skip_target_pages(self):
        pages = {
            "index.html": REF_HTML,
            "delivery.html": BUG_PAGE,
            "cart.html": BUG_PAGE,
        }
        result = unify_pages_layout(pages, target_pages=["delivery.html"])
        assert result["ok"]
        # Only delivery should be in updated
        assert "delivery.html" in result["updated"]
        assert "cart.html" not in result["updated"]

    def test_idempotent_second_run(self):
        pages = {"index.html": REF_HTML, "delivery.html": BUG_PAGE}
        r1 = unify_pages_layout(pages)
        # Apply the patches
        for fn, html in r1["updated"].items():
            pages[fn] = html
        # Second run: shells already in sync, so even if BS4 serialization
        # creates byte-level diffs, the *content* should still be correct
        r2 = unify_pages_layout(pages)
        assert r2["ok"]
        # If any updates happen on 2nd run, they shouldn't reintroduce the bug
        for fn, html in r2.get("updated", {}).items():
            assert "bg-pink-500" in html
            assert "bg-green-500" not in html
