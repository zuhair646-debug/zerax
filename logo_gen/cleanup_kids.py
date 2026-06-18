"""COMPREHENSIVE CLEANUP of /kids HTML.
Removes obsolete duplicate sections + ensures new bot-config widget appears in parent-page.
Run inside backend container (has motor + MongoDB access).
"""
import asyncio
import os
import re
import datetime
from motor.motor_asyncio import AsyncIOMotorClient


SLUG = "zenrex-kids-pro"

# Sections to REMOVE (obsolete / superseded / legacy junk)
SECTIONS_TO_REMOVE = [
    # Old bot page with archive.org placeholders
    "bot-page",
    # Old navigation
    "bottom-nav-update",
    "bottom-nav-fixed",
    # Legacy patches (already applied)
    "fixes-core",
    "init-app-fix",
    "bot-save-fix",
    "auto-scheduler",
    # Old approval/reference system (superseded by bot-config-v20)
    "approval-system",
    "reference-samples",
    "add-by-url",          # replaced by parent-add-video-v18
    "cookies-link",        # replaced by bot-config-v20
    "approval-preview",
    # One-time patches
    "onetime-cleanup",
    "ui-bugfixes-v6",
    "ui-cleanup-v7",
    # Old scraping UI
    "directed-scraping-v9",
    # Superseded versions
    "auth-roles-v10",            # v11 is canonical
    "kids-experience-v12",       # v17 is canonical
    "kids-experience-v13",
    "kids-experience-v16",
    "dynamic-children-v19",      # server-children-v21 is canonical
]


def remove_section(html: str, section_id: str) -> tuple:
    """Remove a <section id="..."> block. Returns (new_html, removed_bytes)."""
    pattern = re.compile(
        r'<section\s+id=["\']' + re.escape(section_id) + r'["\'][^>]*>',
        re.IGNORECASE,
    )
    m = pattern.search(html)
    if not m:
        return html, 0
    start = m.start()
    # Find matching </section> by counting nesting
    pos = m.end()
    depth = 1
    while depth > 0 and pos < len(html):
        next_open = html.find("<section", pos)
        next_close = html.find("</section>", pos)
        if next_close == -1:
            return html, 0  # malformed
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + len("<section")
        else:
            depth -= 1
            pos = next_close + len("</section>")
    end = pos
    removed = end - start
    new_html = html[:start] + f"\n<!-- removed: {section_id} -->\n" + html[end:]
    return new_html, removed


# After cleanup, ensure bot-config-v20's buildWidget targets parent-page.
# Check the current selector and force it.
BUILD_WIDGET_SELECTOR_FIX_OLD = """  function buildWidget(){
    if (localStorage.getItem('zk_role') !== 'parent') return;
    const dash = document.querySelector('#parent-page .parent-stats')?.parentElement || document.querySelector('#parent-page');
    if (!dash) { setTimeout(buildWidget, 600); return; }"""

BUILD_WIDGET_SELECTOR_FIX_NEW = """  function buildWidget(){
    if (localStorage.getItem('zk_role') !== 'parent') return;
    // Always inject into parent-page (the bot tab no longer exists post-cleanup)
    const dash = document.getElementById('parent-page');
    if (!dash) { setTimeout(buildWidget, 600); return; }"""


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    d = c[os.environ["DB_NAME"]]

    doc = await d.freebuild_published_sites.find_one({"slug": SLUG})
    html = doc["current_html"]
    original_len = len(html)
    print(f"BEFORE: {original_len} bytes")

    total_removed = 0
    for sec_id in SECTIONS_TO_REMOVE:
        html, removed = remove_section(html, sec_id)
        if removed:
            print(f"  ✓ removed <{sec_id}> ({removed} bytes)")
            total_removed += removed
        else:
            print(f"  - skipped <{sec_id}> (not found)")

    # Patch buildWidget selectors in remaining sections to ensure correct injection
    if BUILD_WIDGET_SELECTOR_FIX_OLD in html:
        html = html.replace(BUILD_WIDGET_SELECTOR_FIX_OLD, BUILD_WIDGET_SELECTOR_FIX_NEW)
        print("  ✓ patched buildWidget selector to use #parent-page")
    else:
        print("  - buildWidget selector already patched or not found")

    # Remove any references to bot-page from the bottom nav
    # find data-page="bot-page" buttons/items and hide them
    html_before_nav = html
    html = re.sub(
        r'<[^>]*data-page=["\']bot-page["\'][^>]*>.*?</[^>]+>',
        '',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if html != html_before_nav:
        print("  ✓ removed bot-page nav button(s)")

    final_len = len(html)
    print(f"AFTER: {final_len} bytes (removed {original_len - final_len} bytes total)")

    await d.freebuild_published_sites.update_one(
        {"slug": SLUG},
        {
            "$set": {
                "current_html": html,
                "updated_at": datetime.datetime.utcnow().isoformat(),
            }
        },
    )
    print(f"\n✅ Saved cleanup to MongoDB. Removed {total_removed} bytes from obsolete sections.")
    c.close()


if __name__ == "__main__":
    asyncio.run(main())
