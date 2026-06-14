"""اختبار حيّ لدالة lobby_auto_login على lobby.legends.travian.com
نشغّلها مع إيميل وهمي عشان نشوف:
- هل يقبل بانر الكوكيز؟
- هل يلاقي حقل الإيميل؟
- هل يعبّيه؟
- هل يضغط زر الدخول؟
- ايش رد Travian؟ (متوقّع: credentials_rejected لأن الإيميل وهمي)
يحفظ 4 سكرين شوتات في /tmp/zenrex_test/.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from zenrex_farm import lobby_auto_login, lobby_accept_cookies, fingerprint_seed, build_stealth_js

OUT = Path("/tmp/zenrex_test")
OUT.mkdir(exist_ok=True)


async def main():
    from playwright.async_api import async_playwright

    fake_village = {
        "id": "test_live_001",
        "name": "TestPlayer",
        "email": "zenrex.live.test@example.com",
        "password": "FakePassword123!",
        "user_agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"),
        "screen_w": 1920, "screen_h": 1080,
        "locale": "en-US", "timezone": "Europe/Berlin",
    }

    print("\n[1/6] إقلاع Playwright...")
    pw = await async_playwright().start()

    print("[2/6] إنشاء سياق متصفح مع بصمة فريدة + Stealth 2.0...")
    profile = OUT / "browser_profile"
    profile.mkdir(exist_ok=True)
    ctx = await pw.chromium.launch_persistent_context(
        user_data_dir=str(profile),
        headless=True,  # في الـ container ما عندنا display
        user_agent=fake_village["user_agent"],
        viewport={"width": 1366, "height": 768},
        locale="en-US", timezone_id="Europe/Berlin",
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-first-run", "--no-default-browser-check",
            "--no-sandbox",  # مطلوب داخل الـ container
        ],
    )
    fp = fingerprint_seed(fake_village["id"])
    await ctx.add_init_script(build_stealth_js(fp, fake_village))
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    print("[3/6] انتقال إلى https://lobby.legends.travian.com ...")
    try:
        await page.goto("https://lobby.legends.travian.com",
                        wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"  ! خطأ في التحميل: {e}")
    await asyncio.sleep(2)
    await page.screenshot(path=str(OUT / "01_landed.png"))
    print(f"  ✓ صورة بعد التحميل: {OUT / '01_landed.png'}")
    print(f"  URL الحالي: {page.url}")

    print("[4/6] قبول بانر الكوكيز (CMP)...")
    cookie_ok = await lobby_accept_cookies(page)
    await asyncio.sleep(1)
    await page.screenshot(path=str(OUT / "02_after_cookies.png"))
    print(f"  ✓ قبل الكوكيز؟ {cookie_ok}  |  صورة: 02_after_cookies.png")

    print("[5/6] فحص العناصر اللي بنستخدمها للتسجيل...")
    selectors_to_check = [
        ("input[name='email']", "Email field by name"),
        ("input[type='email']", "Email field by type"),
        ("input[name='password']", "Password field by name"),
        ("input[type='password']", "Password field by type"),
        ("button[type='submit']", "Submit button"),
        (".loginButton", "Login button (class)"),
    ]
    for sel, label in selectors_to_check:
        try:
            count = await page.locator(sel).count()
            visible = False
            if count > 0:
                try:
                    visible = await page.locator(sel).first.is_visible(timeout=600)
                except Exception:
                    visible = False
            mark = "✓" if count else "✗"
            print(f"  {mark} {label:35s}  ({sel:30s})  count={count}, visible={visible}")
        except Exception as e:
            print(f"  ! {label}: {e}")

    print("[6/6] تشغيل دالة lobby_auto_login() الفعلية...")
    result = await lobby_auto_login(page, fake_village)
    # Verify fields were actually filled before submit (re-fetch values)
    try:
        email_val = await page.locator("input[name='name']").first.input_value(timeout=600)
    except Exception:
        email_val = "<not found>"
    try:
        pass_val = await page.locator("input[name='password']").first.input_value(timeout=600)
        pass_filled = bool(pass_val) and len(pass_val) > 0
    except Exception:
        pass_filled = False
    print(f"  → قيمة حقل الإيميل بعد التعبئة: '{email_val}'")
    print(f"  → الباسوورد متعبّى؟ {pass_filled}")
    await asyncio.sleep(2)
    await page.screenshot(path=str(OUT / "03_after_login_attempt.png"))
    print(f"\n  ━━━ النتيجة ━━━")
    print(f"  ok      = {result.get('ok')}")
    print(f"  stage   = {result.get('stage')}")
    print(f"  detail  = {result.get('detail')}")
    print(f"  URL النهائي: {page.url}")

    # Final screenshot with annotation
    await page.screenshot(path=str(OUT / "04_final.png"), full_page=True)
    print(f"\n  صور الاختبار محفوظة في: {OUT}")
    print(f"  - 01_landed.png        (بعد تحميل اللوبي)")
    print(f"  - 02_after_cookies.png (بعد قبول الكوكيز)")
    print(f"  - 03_after_login_attempt.png (بعد محاولة الدخول)")
    print(f"  - 04_final.png         (الحالة النهائية)")

    await ctx.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
