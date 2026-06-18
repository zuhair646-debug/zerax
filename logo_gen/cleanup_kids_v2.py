"""Second cleanup pass — remove dead bot-submit scripts + pwa-sw-inline + kids-experience-v12."""
import asyncio
import os
import re
import datetime
from motor.motor_asyncio import AsyncIOMotorClient

SLUG = "zenrex-kids-pro"


def remove_section(html: str, section_id: str) -> tuple:
    """Remove a <section id="..."> block correctly handling nesting."""
    pattern = re.compile(
        r'<section\s+id=["\']' + re.escape(section_id) + r'["\'][^>]*>',
        re.IGNORECASE,
    )
    m = pattern.search(html)
    if not m:
        return html, 0
    start = m.start()
    pos = m.end()
    depth = 1
    while depth > 0 and pos < len(html):
        next_open = html.find("<section", pos)
        next_close = html.find("</section>", pos)
        if next_close == -1:
            return html, 0
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + len("<section")
        else:
            depth -= 1
            pos = next_close + len("</section>")
    return html[:start] + f"\n<!-- removed: {section_id} -->\n" + html[pos:], pos - start


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    d = c[os.environ["DB_NAME"]]
    doc = await d.freebuild_published_sites.find_one({"slug": SLUG})
    html = doc["current_html"]
    print(f"BEFORE: {len(html)} bytes")

    # 1. Remove pwa-sw-inline + kids-experience-v12 sections (missed earlier)
    for sec in ["pwa-sw-inline", "kids-experience-v12"]:
        html, removed = remove_section(html, sec)
        print(f"  remove <{sec}>: {removed} bytes")

    # 2. Remove top-level <script> blocks that bind to dead #bot-submit
    # These are the two scripts at lines ~1086-1294 (Smart Bot Logic blocks)
    pattern = re.compile(
        r"<script>\s*//\s*=+\s*\n\s*//\s*Smart Bot Logic[^<]*?<\s*/script>",
        re.IGNORECASE | re.DOTALL,
    )
    before = len(html)
    html = pattern.sub("<!-- removed: Smart Bot Logic dead script -->", html)
    after_smart = len(html)
    print(f"  remove Smart Bot Logic <script>s: {before - after_smart} bytes")

    # 3. Generic catch — any remaining script that references bot-submit (dead button)
    # Find <script>...bot-submit...</script> blocks
    pattern2 = re.compile(
        r"<script>(?:(?!</script>).)*?bot-submit(?:(?!</script>).)*?</script>",
        re.DOTALL,
    )
    before = len(html)
    html = pattern2.sub("<!-- removed: dead bot-submit script -->", html)
    after_bs = len(html)
    print(f"  remove remaining bot-submit scripts: {before - after_bs} bytes")

    print(f"AFTER: {len(html)} bytes")

    await d.freebuild_published_sites.update_one(
        {"slug": SLUG},
        {"$set": {"current_html": html, "updated_at": datetime.datetime.utcnow().isoformat()}},
    )
    print("✅ Saved")
    c.close()


if __name__ == "__main__":
    asyncio.run(main())
