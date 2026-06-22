"""Power Tools — capabilities that bring the AI closer to a human developer.

This module is imported by the freebuild agent and exposes 4 tools the AI
can call inside the VERIFYING state to actually TEST its own work before
declaring completion.

  • verify_my_work(scenarios, base_url)
      Runs Playwright on the live preview, executes user-style scenarios
      (click button, fill form, navigate to page), returns pass/fail.

  • check_navigation_graph(pages)
      Static analysis: walks every page's <a href> graph, ensures every
      page reachable from index, every page can return to index, no dead
      ends. Returns broken links + orphan pages.

  • validate_js_handlers(html)
      For every onclick="foo()" / onsubmit="bar()" attribute in the HTML,
      verifies a matching `function foo` is defined in inline JS. Catches
      the #1 "dead button" pattern: handler reference without definition.

  • fetch_unsplash_image(query, orientation)
      Whitelisted HTTP fetch — returns real image URLs from Unsplash
      Source API (no key required) so AI can use REAL imagery instead
      of placeholders.
"""
import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

logger = logging.getLogger("brain.power_tools")


# ════════════════════════════════════════════════════════════════════════
# 1. JS Function Handler Validator (static, no browser needed)
# ════════════════════════════════════════════════════════════════════════
def validate_js_handlers(html: str) -> Dict[str, Any]:
    """Scan HTML for onclick/onsubmit attributes referencing functions that
    are NOT defined anywhere in the inline JS. This is the most common
    cause of "dead clicks" the user complained about: AI writes
        <button onclick="openMovie(1)">  but never defines openMovie.
    """
    if not html:
        return {"ok": True, "broken_handlers": [], "defined_functions": [],
                "summary": "empty html"}

    # Extract all inline JS
    js_blocks = re.findall(
        r"<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>", html, re.I,
    )
    js_text = "\n".join(js_blocks)

    # Functions defined in JS (covers: function foo, const foo = , let foo =,
    # var foo =, async function foo, window.foo = function, foo: function in obj)
    defined = set()
    for m in re.finditer(
        r"(?:function\s+|"
        r"(?:const|let|var)\s+|"
        r"window\.|"
        r"async\s+function\s+)"
        r"([a-zA-Z_$][\w$]*)\s*(?:=\s*(?:async\s+)?(?:function|\(|\w+\s*=>)|\()",
        js_text,
    ):
        defined.add(m.group(1))
    # Also: function foo() {...}
    for m in re.finditer(r"\bfunction\s+([a-zA-Z_$][\w$]*)\s*\(", js_text):
        defined.add(m.group(1))
    # Common globals/built-ins to allow
    BUILTINS = {
        "alert", "confirm", "prompt", "console", "Math", "JSON",
        "Date", "Array", "Object", "Number", "String", "Boolean",
        "parseInt", "parseFloat", "isNaN", "encodeURI", "decodeURI",
        "encodeURIComponent", "decodeURIComponent",
        "setTimeout", "clearTimeout", "setInterval", "clearInterval",
        "localStorage", "sessionStorage", "fetch", "XMLHttpRequest",
        "document", "window", "navigator", "location", "history",
        "event", "this", "self", "globalThis", "Promise",
        "FormData", "URLSearchParams", "Blob", "File", "FileReader",
        "addEventListener", "removeEventListener",
    }

    # Scan for handler references in HTML attributes
    broken: List[Dict[str, str]] = []
    seen = set()
    for attr in ("onclick", "onsubmit", "onchange", "oninput", "onload",
                  "onmouseover", "onmouseout", "onfocus", "onblur",
                  "onkeyup", "onkeydown", "onkeypress"):
        for m in re.finditer(
            rf'\b{attr}\s*=\s*["\']\s*([^"\']+?)\s*["\']', html, re.I,
        ):
            code = m.group(1).strip()
            if not code or code in ("javascript:void(0)", ";"):
                continue
            # Extract identifier calls — e.g. "openMovie(1)" → openMovie
            for fcall in re.finditer(r"([a-zA-Z_$][\w$]*)\s*\(", code):
                fname = fcall.group(1)
                if fname in BUILTINS or fname in defined:
                    continue
                # Allow `this.xxx()` / `obj.method()` patterns — check prior char
                idx = fcall.start()
                if idx > 0 and code[idx - 1] == ".":
                    continue
                key = f"{attr}={fname}"
                if key in seen:
                    continue
                seen.add(key)
                broken.append({
                    "attr": attr,
                    "function": fname,
                    "code_excerpt": code[:80],
                    "reason": f"Function '{fname}' referenced but NOT defined in inline JS",
                })

    return {
        "ok": len(broken) == 0,
        "broken_handlers": broken,
        "defined_functions": sorted(defined),
        "total_problems": len(broken),
        "summary": (f"✅ كل {len(seen)} handler متصل بدالة معرّفة"
                     if not broken
                     else f"❌ {len(broken)} handler يستدعي دوال غير معرّفة"),
    }


# ════════════════════════════════════════════════════════════════════════
# 2. Navigation Graph Checker
# ════════════════════════════════════════════════════════════════════════
def check_navigation_graph(pages: Dict[str, str]) -> Dict[str, Any]:
    """Build a directed graph of page→page links and ensure:
      • index.html is reachable from every page (back-to-home rule)
      • every page is reachable from index (no orphans)
      • all link targets exist (no broken .html links)
    """
    if not pages:
        return {"ok": True, "summary": "no pages"}

    pages_lower = {fn.lower(): html for fn, html in pages.items()}
    if "index.html" not in pages_lower:
        return {"ok": False, "summary": "index.html missing from project"}

    # Build link graph
    graph: Dict[str, set] = {fn: set() for fn in pages_lower}
    for fn, html in pages_lower.items():
        for m in re.finditer(
            r'<a\b[^>]*\bhref\s*=\s*["\']([a-zA-Z0-9_\-]+\.html)(?:#[^"\']*)?["\']',
            html, re.I,
        ):
            target = m.group(1).lower()
            graph[fn].add(target)

    # Find broken links
    broken_links = []
    for src, targets in graph.items():
        for t in targets:
            if t not in pages_lower:
                broken_links.append({"from": src, "to": t})

    # BFS from index — find unreachable pages
    reachable = {"index.html"}
    frontier = ["index.html"]
    while frontier:
        nxt = []
        for n in frontier:
            for t in graph.get(n, ()):
                if t in pages_lower and t not in reachable:
                    reachable.add(t)
                    nxt.append(t)
        frontier = nxt
    orphans = [fn for fn in pages_lower if fn not in reachable]

    # Reverse BFS — pages that CAN'T return to index
    rev_graph: Dict[str, set] = {fn: set() for fn in pages_lower}
    for src, targets in graph.items():
        for t in targets:
            if t in pages_lower:
                rev_graph[t].add(src)
    can_reach_home = {"index.html"}
    frontier = ["index.html"]
    while frontier:
        nxt = []
        for n in frontier:
            for s in rev_graph.get(n, ()):
                if s not in can_reach_home:
                    can_reach_home.add(s)
                    nxt.append(s)
        frontier = nxt
    no_back_to_home = [fn for fn in pages_lower
                        if fn != "index.html" and fn not in can_reach_home]

    total = len(broken_links) + len(orphans) + len(no_back_to_home)
    return {
        "ok": total == 0,
        "total_problems": total,
        "broken_links": broken_links,
        "orphan_pages": orphans,
        "pages_without_home_link": no_back_to_home,
        "all_pages": list(pages_lower.keys()),
        "summary": (
            f"✅ كل {len(pages_lower)} صفحة مربوطة بشكل سليم"
            if total == 0
            else (
                f"❌ {len(broken_links)} رابط مكسور · "
                f"{len(orphans)} صفحة معزولة · "
                f"{len(no_back_to_home)} صفحة بدون رجوع للرئيسية"
            )
        ),
    }


# ════════════════════════════════════════════════════════════════════════
# 3. Unsplash image fetcher (whitelisted HTTP)
# ════════════════════════════════════════════════════════════════════════
def fetch_unsplash_image(query: str, orientation: str = "landscape",
                          count: int = 1) -> Dict[str, Any]:
    """Return real Unsplash image URLs for `query` without an API key.

    Uses the source.unsplash.com endpoint which returns 302-redirects to
    real CDN URLs. The AI embeds these directly in <img src=>."""
    if not query or len(query.strip()) < 2:
        return {"ok": False, "error": "query too short"}
    q = quote_plus(query.strip()[:60])
    size_map = {
        "landscape": "1600x900",
        "portrait": "900x1600",
        "square": "1200x1200",
    }
    size = size_map.get(orientation.lower(), "1600x900")
    # The source.unsplash.com API returns a redirect to a random matching
    # image. Each unique URL parameter returns a different image.
    urls = []
    for i in range(min(count, 6)):
        urls.append(f"https://source.unsplash.com/{size}/?{q}&sig={i}")
    return {
        "ok": True,
        "images": urls,
        "query": query,
        "orientation": orientation,
        "count": len(urls),
        "message": (
            f"📸 {len(urls)} صورة Unsplash جاهزة. استخدمها مباشرة في "
            f"<img src=\"{urls[0]}\" alt=\"{query}\">"
        ),
    }


# ════════════════════════════════════════════════════════════════════════
# 4. Playwright-powered verify_my_work (live browser test)
# ════════════════════════════════════════════════════════════════════════
async def verify_my_work(
    base_url: str,
    scenarios: List[Dict[str, Any]],
    timeout_seconds: int = 30,
) -> Dict[str, Any]:
    """Run scenario-based tests on the live preview with Playwright.

    Each scenario is a dict like:
      {"name": "...", "action": "click", "selector": "...", "expect": "..."}

    Supported actions:
      • click  — click selector, check that `expect` text/url appears
      • navigate — go to URL, check page title contains `expect`
      • fill   — fill input, then trigger submit, check `expect`
      • count  — verify selector matches at least N elements

    Returns:
      {ok: bool, results: [{name, passed, error}, ...], total, passed}
    """
    if not base_url or not scenarios:
        return {"ok": False, "error": "base_url and scenarios required"}
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"ok": False, "error": "playwright not installed",
                "fallback": "run validate_js_handlers + check_navigation_graph instead"}

    results = []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True,
            )
            page = await ctx.new_page()
            await page.goto(base_url, wait_until="networkidle",
                              timeout=timeout_seconds * 1000)

            for sc in scenarios[:20]:  # cap at 20 scenarios per turn
                name = sc.get("name") or "unnamed"
                action = sc.get("action", "click")
                selector = sc.get("selector", "")
                expect = sc.get("expect", "")
                passed = False
                err = None
                try:
                    if action == "click":
                        await page.click(selector, timeout=5000, force=True)
                        await page.wait_for_timeout(800)
                        if expect:
                            body_text = await page.evaluate("() => document.body.innerText")
                            url = page.url
                            passed = expect in body_text or expect in url
                            if not passed:
                                err = f"after click, '{expect}' not in body/url"
                        else:
                            passed = True
                    elif action == "navigate":
                        target = sc.get("url") or base_url
                        await page.goto(target, wait_until="networkidle",
                                          timeout=timeout_seconds * 1000)
                        title = await page.title()
                        body = await page.evaluate("() => document.body.innerText")
                        passed = bool(expect) and (expect in title or expect in body)
                        if not passed:
                            err = f"title={title!r} body excerpt={body[:80]!r}"
                    elif action == "fill":
                        value = sc.get("value", "test")
                        await page.fill(selector, value, timeout=5000)
                        submit_sel = sc.get("submit_selector",
                                              "button[type='submit']")
                        try:
                            await page.click(submit_sel, timeout=3000)
                            await page.wait_for_timeout(1200)
                        except Exception:
                            pass
                        if expect:
                            body = await page.evaluate("() => document.body.innerText")
                            passed = expect in body
                            if not passed:
                                err = f"after submit, '{expect}' not in body"
                        else:
                            passed = True
                    elif action == "count":
                        min_count = int(sc.get("min", 1))
                        n = await page.locator(selector).count()
                        passed = n >= min_count
                        if not passed:
                            err = f"expected ≥{min_count} of '{selector}', got {n}"
                    else:
                        err = f"unknown action '{action}'"
                except Exception as e:
                    err = f"{type(e).__name__}: {str(e)[:120]}"
                results.append({"name": name, "action": action,
                                 "passed": passed, "error": err})

            await browser.close()
    except Exception as e:
        logger.exception("verify_my_work failed")
        return {"ok": False, "error": f"playwright failed: {type(e).__name__}: {str(e)[:200]}",
                "results": results}

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    return {
        "ok": passed == total and total > 0,
        "passed": passed,
        "total": total,
        "results": results,
        "summary": (
            f"✅ {passed}/{total} سيناريو نجح"
            if passed == total
            else f"❌ {passed}/{total} سيناريو نجح — أصلح الفشل قبل complete_task"
        ),
    }
