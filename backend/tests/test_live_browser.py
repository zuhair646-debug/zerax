"""Tests for auto_generate_scenarios + quick_browser_check."""
import asyncio
import pytest
from modules.brain.power_tools import (
    auto_generate_scenarios, quick_browser_check, verify_my_work,
)


class TestAutoScenarios:
    def test_extract_buttons(self):
        html = '''<html><body>
        <button id="add-btn">أضف</button>
        <button onclick="x()">دخول</button>
        </body></html>'''
        sc = auto_generate_scenarios(html)
        assert len(sc) == 2
        assert sc[0]["selector"] == "#add-btn"
        assert "أضف" in sc[0]["name"]

    def test_extract_nav_links(self):
        html = '''<html><body>
        <a href="about.html">من نحن</a>
        <a href="contact.html">تواصل</a>
        <a href="index.html">رئيسية</a>
        </body></html>'''
        sc = auto_generate_scenarios(html)
        # index.html is excluded — it's the current page
        names = [s["name"] for s in sc]
        assert any("about.html" in n for n in names)
        assert any("contact.html" in n for n in names)
        assert not any("index.html" in n for n in names)

    def test_empty_html(self):
        assert auto_generate_scenarios("") == []
        assert auto_generate_scenarios("<html></html>") == []

    def test_cap_at_max(self):
        # Should cap at 4 buttons + 3 nav links
        html = "<html><body>"
        for i in range(10):
            html += f'<button>btn{i}</button>'
        for i in range(10):
            html += f'<a href="page{i}.html">link{i}</a>'
        html += "</body></html>"
        sc = auto_generate_scenarios(html)
        assert len(sc) == 7  # 4 buttons + 3 nav links


class TestQuickBrowserCheck:
    @pytest.mark.asyncio
    async def test_loads_about_blank(self):
        r = await quick_browser_check("about:blank", timeout_seconds=10)
        # about:blank has no body content but shouldn't error
        assert "ok" in r

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        r = await quick_browser_check("https://this-domain-does-not-exist-zxy12345.com",
                                        timeout_seconds=5)
        assert not r["ok"]
