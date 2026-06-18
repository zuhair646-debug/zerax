"""Remove the two dead bot-submit script blocks (they bind to a non-existent button)."""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

SLUG = "zenrex-kids-pro"


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    d = c[os.environ["DB_NAME"]]
    doc = await d.freebuild_published_sites.find_one({"slug": SLUG})
    html = doc["current_html"]
    original_len = len(html)

    # Strategy: Find each `<script>` tag that contains the string "bot-submit?.addEventListener"
    # and replace the whole script block with a comment.
    needle = "bot-submit?.addEventListener"
    removed_count = 0
    while needle in html:
        idx = html.find(needle)
        # Walk backward to find the opening <script>
        script_open = html.rfind("<script>", 0, idx)
        if script_open == -1:
            print("no opening <script> found, aborting")
            break
        # Walk forward to find the closing </script>
        script_close = html.find("</script>", idx)
        if script_close == -1:
            print("no closing </script> found, aborting")
            break
        script_close_end = script_close + len("</script>")
        size = script_close_end - script_open
        print(f"  removing script block: {script_open}..{script_close_end} ({size} bytes)")
        html = html[:script_open] + "<!-- removed: dead bot-submit script -->" + html[script_close_end:]
        removed_count += 1

    print(f"Removed {removed_count} dead script blocks. {original_len} -> {len(html)} bytes (delta {len(html)-original_len:+d})")

    await d.freebuild_published_sites.update_one(
        {"slug": SLUG}, {"$set": {"current_html": html}}
    )
    print("✅ Saved")
    c.close()


if __name__ == "__main__":
    asyncio.run(main())
