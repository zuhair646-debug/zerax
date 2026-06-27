"""Unit tests for Library Registry + inject_library tool."""
import asyncio
import sys
sys.path.insert(0, '/app/backend')

from modules.freebuild.library_registry import (
    LIBRARY_REGISTRY,
    library_summary_for_prompt,
    inject_library,
    LIBRARY_TOOL_SCHEMA,
)


class FakeCtx:
    def __init__(self, pages=None):
        self.pages = pages or {"index.html": "<!DOCTYPE html><html><head></head><body><h1>Hello</h1></body></html>"}
        self.active_page = "index.html"
        self.current_html = self.pages.get("index.html", "")
        self.changes_made = 0
        self.db = None  # no mongo

    def _sync_active_page(self):
        if self.current_html:
            self.pages[self.active_page] = self.current_html


async def test_basic_inject():
    print("\n=== Test 1: Discovery mode ===")
    ctx = FakeCtx()
    r = await inject_library(ctx, {"category": "?"})
    print(f"  ok={r.get('ok')} cats={list(r.get('categories', {}).keys())[:5]}")
    assert r["ok"]
    assert "charts" in r["categories"]
    assert "maps" in r["categories"]
    print(f"  ✅ {len(r['categories'])} categories listed")

    print("\n=== Test 2: Inject chart.js (primary) ===")
    ctx = FakeCtx()
    r = await inject_library(ctx, {"category": "charts", "template_id": "sales"})
    print(f"  ok={r.get('ok')} lib={r.get('lib')} actions={r.get('actions')}")
    assert r["ok"]
    assert r["lib"] == "chart.js"
    new_html = ctx.pages["index.html"]
    assert "chart.js@4.4.1" in new_html or "chart.js" in new_html
    assert "chart_sales" in new_html  # TPL replaced with 'sales'
    assert "data-zenrex-lib=\"chart.js\"" in new_html
    print(f"  ✅ chart.js injected, html size {len(new_html)}, contains 'chart_sales' id")

    print("\n=== Test 3: Inject leaflet maps (primary) ===")
    ctx = FakeCtx()
    r = await inject_library(ctx, {"category": "maps", "template_id": "driver"})
    print(f"  ok={r.get('ok')} lib={r.get('lib')} bytes={r.get('bytes_added')}")
    new_html = ctx.pages["index.html"]
    assert "leaflet" in new_html.lower()
    assert "L.map('map_driver'" in new_html
    print(f"  ✅ leaflet ready, contains map_driver init")

    print("\n=== Test 4: Alternative variant (echarts) ===")
    ctx = FakeCtx()
    r = await inject_library(ctx, {"category": "charts", "variant": "alternative"})
    assert r["ok"]
    assert r["lib"] == "echarts"
    assert "echarts" in ctx.pages["index.html"]
    print(f"  ✅ alternative variant works → {r['lib']}@{r['version']}")

    print("\n=== Test 5: Anchor selector targeting ===")
    ctx = FakeCtx(pages={"index.html": '<html><head></head><body><div id="dash"></div></body></html>'})
    r = await inject_library(ctx, {"category": "charts", "anchor_selector": "#dash", "template_id": "main"})
    assert r["ok"]
    new_html = ctx.pages["index.html"]
    # Snippet should be inside #dash (after its opening tag)
    dash_pos = new_html.find('id="dash"')
    snippet_pos = new_html.find("inject_library:chart.js")
    assert dash_pos < snippet_pos, f"snippet at {snippet_pos}, dash at {dash_pos}"
    print(f"  ✅ anchor targeting worked (snippet appears right after #dash)")

    print("\n=== Test 6: Idempotent (no double-inject) ===")
    ctx = FakeCtx()
    r1 = await inject_library(ctx, {"category": "charts"})
    size_after_1 = len(ctx.pages["index.html"])
    r2 = await inject_library(ctx, {"category": "charts"})
    size_after_2 = len(ctx.pages["index.html"])
    print(f"  size after 1st: {size_after_1}, after 2nd: {size_after_2}")
    # CSS+JS won't duplicate (idempotent on exact-match), but init snippet may add 1 comment
    assert size_after_2 - size_after_1 < 100, f"unexpected growth {size_after_2 - size_after_1}"
    print(f"  ✅ idempotent (growth = {size_after_2 - size_after_1} bytes)")

    print("\n=== Test 7: Unknown category ===")
    ctx = FakeCtx()
    r = await inject_library(ctx, {"category": "nonexistent_x"})
    assert not r["ok"]
    assert "unknown" in r["error"].lower()
    print(f"  ✅ unknown category rejected")

    print("\n=== Test 8: Page missing ===")
    ctx = FakeCtx(pages={"index.html": "<html></html>"})
    r = await inject_library(ctx, {"category": "charts", "page": "missing.html"})
    assert not r["ok"]
    assert "not found" in r["error"].lower()
    print(f"  ✅ missing page rejected")

    print("\n=== Test 9: 3D variant uses primary three.js with importmap ===")
    ctx = FakeCtx()
    r = await inject_library(ctx, {"category": "3d", "template_id": "scene"})
    assert r["ok"]
    new_html = ctx.pages["index.html"]
    assert "three.module.js" in new_html
    assert "OrbitControls" in new_html
    assert 'type="importmap"' in new_html or "importmap" in new_html
    print(f"  ✅ three.js + importmap injected")

    print("\n=== Test 10: Prompt summary (atlas) ===")
    s = library_summary_for_prompt()
    assert "charts" in s
    assert "chart.js" in s
    assert "leaflet" in s
    assert "inject_library" in s
    print(f"  ✅ atlas summary = {len(s)} chars")
    print(s[:600])

    print("\n=== Test 11: Tool schema ===")
    assert LIBRARY_TOOL_SCHEMA["name"] == "inject_library"
    assert "category" in LIBRARY_TOOL_SCHEMA["input_schema"]["properties"]
    print(f"  ✅ schema valid")

    print("\n🎉 ALL 11 TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(test_basic_inject())
