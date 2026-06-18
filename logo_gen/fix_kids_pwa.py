"""Fix /kids PWA HTML to make it installable as a separate standalone PWA."""
import re
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
SLUG = "zenrex-kids-pro"

# Proper PWA <head> snippet (idempotent — single source of truth)
PROPER_HEAD = """  <!-- Zenrex Kids PWA — proper install setup (auto-applied) -->
  <link rel="manifest" href="/kids/manifest.webmanifest" data-pwa="kids">
  <link rel="apple-touch-icon" href="/kids/icon-512.png">
  <link rel="apple-touch-icon" sizes="192x192" href="/kids/icon-192.png">
  <link rel="apple-touch-icon" sizes="512x512" href="/kids/icon-512.png">
  <link rel="icon" type="image/png" sizes="192x192" href="/kids/icon-192.png">
  <link rel="icon" type="image/png" sizes="512x512" href="/kids/icon-512.png">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="زنركس كيدز">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="application-name" content="زنركس كيدز">
  <meta name="theme-color" content="#ff2d55">
"""

# Service worker registration snippet — register at /kids scope only
PROPER_SW_REG = """<script>
// PWA — register Service Worker at /kids scope so it's a standalone PWA
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/kids/sw.js', { scope: '/kids' })
    .then(reg => console.log('[kids-pwa] SW registered:', reg.scope))
    .catch(err => console.warn('[kids-pwa] SW reg failed:', err));
}
</script>
"""


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    doc = await db.freebuild_published_sites.find_one({"slug": SLUG})
    if not doc:
        print(f"❌ slug '{SLUG}' not found")
        sys.exit(1)
    html = doc["current_html"]
    original_len = len(html)
    print(f"Original HTML: {original_len} bytes")

    # ─── 1. Strip ALL existing <link rel="manifest" ...> tags (greedy across newlines)
    html, n_manifest = re.subn(
        r'<link[^>]*rel=["\']manifest["\'][^>]*>',
        '',
        html,
        flags=re.IGNORECASE,
    )
    print(f"  removed {n_manifest} <link rel='manifest'> tags")

    # ─── 2. Strip ALL <meta name="theme-color" ...> (we'll add our own)
    html, n_theme = re.subn(
        r'<meta[^>]*name=["\']theme-color["\'][^>]*>',
        '',
        html,
        flags=re.IGNORECASE,
    )
    print(f"  removed {n_theme} theme-color metas")

    # ─── 3. Strip the "section #head" abomination from the body
    html, n_sec = re.subn(
        r'<section\s+id=["\']head["\'][^>]*>.*?</section>',
        '',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    print(f"  removed {n_sec} <section id='head'> blocks")

    # ─── 4. Strip old apple-touch-icon / apple-mobile-web-app-capable
    html, n_apple = re.subn(
        r'<link[^>]*rel=["\']apple-touch-icon["\'][^>]*>',
        '',
        html,
        flags=re.IGNORECASE,
    )
    html, n_amwc = re.subn(
        r'<meta[^>]*name=["\']apple-mobile-web-app-capable["\'][^>]*>',
        '',
        html,
        flags=re.IGNORECASE,
    )
    print(f"  removed {n_apple} apple-touch-icon, {n_amwc} apple-mobile-web-app-capable")

    # ─── 5. Strip OLD service-worker registrations targeting root scope
    html, n_oldsw = re.subn(
        r"navigator\.serviceWorker\.register\(['\"]\/?sw\.js['\"][^)]*\)\s*\.[^;]+;",
        '/* removed old SW reg */',
        html,
        flags=re.IGNORECASE,
    )
    print(f"  removed {n_oldsw} root-scope SW registrations")

    # ─── 6. Insert PROPER_HEAD right after <meta charset...> (first occurrence)
    if 'data-pwa="kids"' in html:
        print("  (already has data-pwa='kids' — skipping injection)")
    else:
        # Insert after the first <head> tag content (after meta charset)
        new_html, n_ins = re.subn(
            r'(<head[^>]*>\s*<meta\s+charset=["\']UTF-?8["\'][^>]*>)',
            r'\1\n' + PROPER_HEAD,
            html,
            count=1,
            flags=re.IGNORECASE,
        )
        if n_ins == 0:
            # Fallback: insert right after <head>
            new_html, n_ins = re.subn(
                r'(<head[^>]*>)',
                r'\1\n' + PROPER_HEAD,
                html,
                count=1,
                flags=re.IGNORECASE,
            )
        html = new_html
        print(f"  injected proper PWA head ({n_ins} place)")

    # ─── 7. Add the proper SW registration right before </body> if not present
    if "navigator.serviceWorker.register('/kids/sw.js'" not in html:
        html = re.sub(
            r'</body>',
            PROPER_SW_REG + '</body>',
            html,
            count=1,
            flags=re.IGNORECASE,
        )
        print("  injected /kids/sw.js registration")
    else:
        print("  (/kids/sw.js already registered — skipping)")

    final_len = len(html)
    print(f"Final HTML: {final_len} bytes (delta {final_len - original_len:+d})")

    # ─── Save back
    await db.freebuild_published_sites.update_one(
        {"slug": SLUG},
        {"$set": {"current_html": html, "updated_at": __import__("datetime").datetime.utcnow().isoformat()}},
    )
    print(f"✅ Saved {SLUG} HTML back to MongoDB")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
