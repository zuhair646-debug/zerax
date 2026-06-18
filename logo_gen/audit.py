"""Audit ALL parent dashboard buttons + sections. Identify dead/duplicate code."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 420, "height": 900})
        page = await ctx.new_page()

        # Capture all console + network failures
        console_msgs = []
        net_fails = []
        page.on("console", lambda m: console_msgs.append(f"[{m.type}] {m.text}"))
        page.on("requestfailed", lambda r: net_fails.append(f"FAILED {r.url} - {r.failure}"))
        page.on("response", lambda r: net_fails.append(f"HTTP {r.status} {r.url}") if r.status >= 400 else None)

        await page.goto("https://zenrex.ai/kids", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2500)

        # Login as parent - use visible inputs only
        inputs = await page.query_selector_all('input:visible')
        print(f"VISIBLE inputs at login: {len(inputs)}")
        if len(inputs) >= 2:
            await inputs[0].fill("zoheer@zenrex.ai")
            await inputs[1].fill("Zenrex@2026")
            login_btn = await page.query_selector("button:visible:has-text('دخول')")
            if login_btn:
                await login_btn.click()
        await page.wait_for_timeout(4000)

        # Check role + token
        state = await page.evaluate("""() => ({
            role: localStorage.getItem('zk_role'),
            token: localStorage.getItem('token') ? 'YES' : 'NO',
            curPage: document.querySelector('.page.active')?.id || 'none'
        })""")
        print("AFTER LOGIN:", state)

        # Try to click each nav-item and see if page changes
        nav_items = await page.query_selector_all(".nav-item[data-page]:visible")
        print(f"Nav items found: {len(nav_items)}")
        for nav in nav_items:
            text = await nav.inner_text()
            page_target = await nav.get_attribute("data-page")
            try:
                await nav.click()
                await page.wait_for_timeout(800)
                cur = await page.evaluate("document.querySelector('.page.active')?.id")
                pin = await page.evaluate("document.getElementById('parent-pin')?.classList.contains('active')")
                print(f"  NAV[{text.strip()}] -> data-page={page_target} | active page={cur} | pin-shown={pin}")
                if pin:
                    # Enter PIN 1234
                    for d in "1234":
                        b = await page.query_selector(f"#parent-pin button:has-text('{d}')")
                        if b: 
                            await b.click()
                            await page.wait_for_timeout(150)
                    await page.wait_for_timeout(1500)
                    cur2 = await page.evaluate("document.querySelector('.page.active')?.id")
                    print(f"    after PIN -> active page={cur2}")
            except Exception as e:
                print(f"  NAV click FAIL: {e}")

        # On parent page now (hopefully), enumerate all visible interactive buttons
        await page.evaluate("document.getElementById('parent-page')?.classList.add('active')")
        await page.wait_for_timeout(2000)

        all_buttons = await page.query_selector_all("#parent-page button, .parent-section button")
        print(f"\nButtons on parent page: {len(all_buttons)}")
        seen = set()
        for btn in all_buttons[:40]:
            bid = await btn.get_attribute("id") or ""
            txt = (await btn.inner_text() or "")[:40]
            vis = await btn.is_visible()
            key = (bid, txt)
            if key not in seen:
                seen.add(key)
                print(f"  - id={bid:30} | visible={vis} | text={txt!r}")

        # Check for duplicate function definitions in window
        dup_check = await page.evaluate("""() => {
            const html = document.documentElement.outerHTML;
            const fns = ['buildWidget','loadPending','loadApproved','renderVideos','init'];
            const result = {};
            fns.forEach(name => {
                const re = new RegExp('function\\\\s+' + name + '\\\\s*\\\\(', 'g');
                result[name] = (html.match(re) || []).length;
            });
            return result;
        }""")
        print(f"\nDuplicate function definitions in HTML: {dup_check}")

        # Sections with class="page"
        pages = await page.evaluate("""() => Array.from(document.querySelectorAll('.page, [class*="page"]')).filter(e=>e.id).map(e => ({id: e.id, visible: e.offsetParent !== null, classes: e.className}))""")
        print(f"\nPages found: {len(pages)}")
        for pg in pages:
            print(f"  - {pg}")

        # Network errors during load
        print("\n=== Network errors (4xx/5xx) ===")
        bad = [n for n in net_fails if "HTTP 4" in n or "HTTP 5" in n or "FAILED" in n]
        for n in bad[:20]:
            print(f"  {n}")

        # Console errors
        print("\n=== Console errors ===")
        errs = [m for m in console_msgs if '[error]' in m.lower() or '[warning]' in m.lower()]
        for e in errs[:15]:
            print(f"  {e[:200]}")

        await browser.close()


asyncio.run(main())
