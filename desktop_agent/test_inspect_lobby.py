"""فحص HTML الفعلي لـ Travian Lobby — نقرأ كل input + الـ form attributes."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def main():
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    ctx = await pw.chromium.launch_persistent_context(
        user_data_dir="/tmp/zenrex_inspect",
        headless=True,
        viewport={"width": 1366, "height": 768},
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    await page.goto("https://lobby.legends.travian.com",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(2.5)

    # Try to dismiss cookies
    for sel in ["#cmpwelcomebtnyes a", ".cmpboxbtnyes a",
                "#onetrust-accept-btn-handler"]:
        try:
            await page.locator(sel).first.click(timeout=900)
            await asyncio.sleep(1)
            break
        except Exception:
            continue

    # Dump every input + every form
    inputs = await page.evaluate("""
        () => Array.from(document.querySelectorAll('input, button[type], form'))
              .map(el => ({
                tag: el.tagName.toLowerCase(),
                id: el.id || '',
                name: el.getAttribute('name') || '',
                type: el.getAttribute('type') || '',
                placeholder: el.getAttribute('placeholder') || '',
                autocomplete: el.getAttribute('autocomplete') || '',
                class: el.className || '',
                visible: el.offsetParent !== null,
                action: el.getAttribute('action') || ''
              }))
    """)
    print("\n=== كل العناصر التفاعلية في اللوبي ===")
    for el in inputs:
        if el["tag"] == "form":
            print(f"FORM action={el['action']}  class={el['class'][:60]}")
        elif el["tag"] in ("input", "button"):
            print(f"  {el['tag']:6s} id={el['id']:25s} name={el['name']:18s} "
                  f"type={el['type']:10s} placeholder={el['placeholder'][:25]:25s} "
                  f"autocomp={el['autocomplete']:18s} visible={el['visible']}")

    await ctx.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
