#!/usr/bin/env python3
"""Auto-Download Bot — searches YouTube for kid-safe Islamic content and downloads it.

Behavior:
  - Reads cookies from /app/backend/uploads/freebuild_cookies/<user>__youtube.txt
  - Runs yt-dlp search queries for predefined kid-safe topics
  - Downloads top N per topic to MEDIA_DIR
  - Inserts media_assets DB records with category='tiktok_kids' + subcategory tag
  - Skips already-downloaded sources (dedupes by source_url)
"""
import os, json, subprocess, glob, time, uuid
from datetime import datetime, timezone
from pymongo import MongoClient

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "zerax_prod")
MEDIA_DIR = "/app/backend/uploads/freebuild_media"
COOKIES_DIR = "/app/backend/uploads/freebuild_cookies"
HOST = os.environ.get("PUBLIC_HOST", "https://zenrex.ai").rstrip("/")

cl = MongoClient(MONGO_URL)
db = cl[DB_NAME]
admin = db.users.find_one({"email": "admin@zenrex.ai"})
USER_ID = admin["id"]
COOKIES_PATH = os.path.join(COOKIES_DIR, f"{USER_ID}__youtube.txt")
HAS_COOKIES = os.path.exists(COOKIES_PATH)

# Search topics: each generates ~3 videos. Total: 5 categories × 3 = 15 videos per run.
TOPICS = [
    ("quran_video",      "قرآن للأطفال بفيديو ملون أنمي",         3),
    ("latmiyat_kids",    "لطميات حسينية للأطفال",                 3),
    ("duas_kids",        "أدعية مصورة للأطفال دعاء الفرج",        3),
    ("mawalid_kids",     "مولد الإمام علي للأطفال أنمي",          3),
    ("sheikh_stories_k", "قصص أنبياء للأطفال كرتون",             3),
]

print(f"[BOT] Starting auto-download. cookies={'YES' if HAS_COOKIES else 'NO (will likely fail)'}")
print(f"[BOT] User: {USER_ID[:8]}..., Topics: {len(TOPICS)}")

total_ok = 0
total_fail = 0
fail_reasons = []

for subcat, query, limit in TOPICS:
    print(f"\n[BOT] Topic: {subcat} '{query[:40]}' (limit {limit})")
    # Step 1: search YouTube for top URLs
    search_cmd = ["yt-dlp", f"ytsearch{limit}:{query}",
                  "--flat-playlist", "--print", "%(webpage_url)s",
                  "--no-warnings", "--quiet"]
    if HAS_COOKIES:
        search_cmd.extend(["--cookies", COOKIES_PATH])
    try:
        r = subprocess.run(search_cmd, capture_output=True, timeout=60)
        urls = [u.strip() for u in r.stdout.decode("utf-8", "ignore").splitlines() if u.strip().startswith("http")][:limit]
    except subprocess.TimeoutExpired:
        urls = []
        fail_reasons.append(f"{subcat}: search timeout")
    print(f"  Found {len(urls)} URLs")

    for url in urls:
        # Dedupe by source_url
        if db.freebuild_media_assets.find_one({"source_url": url, "user_id": USER_ID}):
            print(f"  ⊖ skip (already downloaded): {url[:50]}")
            continue
        fid = uuid.uuid4().hex[:16]
        out = os.path.join(MEDIA_DIR, f"{fid}.%(ext)s")
        cmd = ["yt-dlp", "--no-playlist", "--no-warnings",
               "--restrict-filenames", "--write-info-json",
               "-f", "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/b[height<=720]",
               "--merge-output-format", "mp4",
               "-o", out]
        if HAS_COOKIES:
            cmd.extend(["--cookies", COOKIES_PATH])
        cmd.append(url)
        try:
            dr = subprocess.run(cmd, capture_output=True, timeout=180)
            if dr.returncode != 0:
                err = dr.stderr.decode("utf-8", "ignore")[-200:]
                total_fail += 1
                if "Sign in to confirm" in err or "403" in err:
                    fail_reasons.append(f"IP_BLOCK on {url[:30]}")
                else:
                    fail_reasons.append(f"yt-dlp err: {err[:80]}")
                print(f"  ✗ {url[:50]}: {err[:80]}")
                continue
            # Find produced file
            produced = [f for f in glob.glob(os.path.join(MEDIA_DIR, f"{fid}.*")) if not f.endswith(".info.json")]
            if not produced:
                print(f"  ✗ no file produced for {url[:50]}")
                total_fail += 1
                continue
            actual = produced[0]
            # Run +faststart for browser compatibility
            fixed = actual + ".fix"
            subprocess.run(["ffmpeg", "-y", "-i", actual, "-c", "copy", "-movflags", "+faststart", fixed],
                           capture_output=True, timeout=60)
            if os.path.exists(fixed) and os.path.getsize(fixed) > 1000:
                os.replace(fixed, actual)
            ext = actual.rsplit(".", 1)[-1]
            # Read metadata
            meta_path = os.path.join(MEDIA_DIR, f"{fid}.info.json")
            title, duration, thumb = "", None, None
            if os.path.exists(meta_path):
                try:
                    meta = json.load(open(meta_path))
                    title = meta.get("title", "")[:200]
                    duration = meta.get("duration")
                    thumb = meta.get("thumbnail")
                except Exception:
                    pass
            db.freebuild_media_assets.insert_one({
                "id": fid,
                "user_id": USER_ID,
                "project_id": "tiktok-kids-bot",
                "filename": os.path.basename(actual),
                "ext": ext,
                "source_url": url,
                "title": title or f"{subcat} video",
                "duration": duration,
                "thumbnail_url": thumb,
                "category": "tiktok_kids",
                "subcategory": subcat,
                "format": "mp4_720p",
                "public_url": f"{HOST}/api/freebuild-chat/media/file/{fid}.{ext}",
                "bot_query": query,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            total_ok += 1
            print(f"  ✓ {title[:50]} ({os.path.getsize(actual)//1024}KB)")
        except subprocess.TimeoutExpired:
            total_fail += 1
            fail_reasons.append(f"timeout on {url[:30]}")
            print(f"  ✗ timeout")
        except Exception as e:
            total_fail += 1
            fail_reasons.append(f"{type(e).__name__}: {str(e)[:60]}")
            print(f"  ✗ exc: {e}")

# Final report
print(f"\n[BOT] Done. ok={total_ok}, failed={total_fail}")
if fail_reasons:
    print(f"[BOT] Failure summary (first 5): {fail_reasons[:5]}")

# Write status to DB for the UI to poll
db.bot_runs.insert_one({
    "ran_at": datetime.now(timezone.utc).isoformat(),
    "ok": total_ok,
    "failed": total_fail,
    "had_cookies": HAS_COOKIES,
    "failure_sample": fail_reasons[:5],
})
print(f"[BOT] Status saved to bot_runs collection")
