"""SAFE cleanup pass — careful removal that preserves HTML structure."""
import asyncio
import os
import re
import datetime
from motor.motor_asyncio import AsyncIOMotorClient

SLUG = "zenrex-kids-pro"


def find_section_bounds(html: str, section_id: str):
    """Find exact [start, end] bytes of a <section id="X">...</section> block.
    Uses careful nesting counting. Returns (start, end) or None if not found.
    """
    pattern = re.compile(
        r'<section\s+id=["\']' + re.escape(section_id) + r'["\'][^>]*>',
        re.IGNORECASE,
    )
    m = pattern.search(html)
    if not m:
        return None
    start = m.start()
    pos = m.end()
    depth = 1
    # Pattern to find next <section ...> or </section>
    while depth > 0:
        # Find next section-related tag
        open_re = re.compile(r'<section\b[^>]*>', re.IGNORECASE)
        close_re = re.compile(r'</section\s*>', re.IGNORECASE)
        open_m = open_re.search(html, pos)
        close_m = close_re.search(html, pos)
        if not close_m:
            return None  # unbalanced, abort
        if open_m and open_m.start() < close_m.start():
            depth += 1
            pos = open_m.end()
        else:
            depth -= 1
            pos = close_m.end()
    return (start, pos)


# Order matters! Remove dependent sections in this order to avoid breaking nesting.
SECTIONS_TO_REMOVE = [
    # Old bot page with archive.org placeholders (has nested scripts inside)
    "bot-page",
    # Old navigation - now consolidated
    "bottom-nav-update",
    "bottom-nav-fixed",
    # PWA blob SW (replaced by /kids/sw.js)
    "pwa-sw-inline",
    # Legacy fixes (already applied or superseded)
    "fixes-core",
    "init-app-fix",
    "bot-save-fix",
    "auto-scheduler",
    "approval-system",
    "reference-samples",
    "add-by-url",
    "cookies-link",
    "approval-preview",
    "onetime-cleanup",
    "ui-bugfixes-v6",
    "ui-cleanup-v7",
    "directed-scraping-v9",
    # Superseded versions
    "auth-roles-v10",       # v11 canonical
    "kids-experience-v12",  # v17 canonical
    "kids-experience-v13",
    "kids-experience-v16",
    "dynamic-children-v19", # v21 canonical
]


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    d = c[os.environ["DB_NAME"]]
    doc = await d.freebuild_published_sites.find_one({"slug": SLUG})
    html = doc["current_html"]
    original_len = len(html)
    print(f"BEFORE: {original_len} bytes")

    total_removed = 0
    for sec_id in SECTIONS_TO_REMOVE:
        bounds = find_section_bounds(html, sec_id)
        if bounds is None:
            print(f"  - skipped <{sec_id}> (not found / unbalanced)")
            continue
        start, end = bounds
        size = end - start
        if size > 50000:
            print(f"  ⚠️  REFUSING <{sec_id}>: {size} bytes seems too big (likely unbalanced HTML)")
            continue
        html = html[:start] + f"\n<!-- removed: {sec_id} -->\n" + html[end:]
        print(f"  ✓ removed <{sec_id}> ({size} bytes)")
        total_removed += size

    # Now NEUTRALIZE any remaining dead handlers that reference missing #bot-submit
    # Instead of removing, wrap in safety check
    before = len(html)
    pattern = re.compile(
        r"document\.getElementById\('bot-submit'\)\.addEventListener\(",
        re.IGNORECASE,
    )
    safety_replace = "document.getElementById('bot-submit')?.addEventListener?.("
    html = pattern.sub(safety_replace, html)
    pattern2 = re.compile(
        r"document\.getElementById\('bot-(request|category|limit|status|log)'\)\.",
    )
    html = pattern2.sub(lambda m: m.group(0)[:-1] + "?.", html)
    print(f"  ✓ neutralized dead bot-submit handlers ({before - len(html)} bytes delta, safer null-handling)")

    print(f"AFTER: {len(html)} bytes (removed {original_len - len(html)} bytes total)")

    await d.freebuild_published_sites.update_one(
        {"slug": SLUG},
        {"$set": {"current_html": html, "updated_at": datetime.datetime.utcnow().isoformat()}},
    )
    print("✅ Saved")
    c.close()


if __name__ == "__main__":
    asyncio.run(main())
