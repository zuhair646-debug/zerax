"""Backend tests for the Zenrex Promo Video Studio (/api/promo-video/*)."""
import os
import time
import requests
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api/promo-video"

# A small, fast Unsplash image used for ffmpeg slideshow tests.
UNSPLASH_IMG = "https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=600&q=70"


# ─── Health ──────────────────────────────────────────────────────────────────
def test_health():
    r = requests.get(f"{API}/health", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["ffmpeg"] is True
    assert "zenrex_male_deep" in data["voices"]


# ─── Storyboard ──────────────────────────────────────────────────────────────
def test_storyboard_arabic_luxury():
    payload = {
        "product_name": "ساعة Apple Watch Ultra 2",
        "duration_seconds": 30,
        "lang": "ar",
        "tone": "luxury",
        "cta": "اطلب الآن",
    }
    r = requests.post(f"{API}/storyboard", json=payload, timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("title")
    scenes = data.get("scenes") or []
    # Spec: ~6 scenes for 30 seconds.  Accept a sensible range.
    assert 4 <= len(scenes) <= 8, f"unexpected scene count {len(scenes)}"
    assert data.get("full_narration")
    assert data.get("cost") == 5
    # Each scene should have narration text.
    for sc in scenes:
        assert sc.get("narration"), f"missing narration: {sc}"


# ─── Packages ────────────────────────────────────────────────────────────────
def test_packages_list():
    r = requests.get(f"{API}/packages", timeout=10)
    assert r.status_code == 200
    pkgs = r.json()["packages"]
    ids = {p["id"] for p in pkgs}
    assert ids == {"starter", "pro", "agency", "enterprise"}
    for p in pkgs:
        assert p["credits"] > 0
        assert p["price_sar"] > 0


# ─── Recharge (mocked gateway) ──────────────────────────────────────────────
def test_recharge_pro_mada():
    r = requests.post(
        f"{API}/recharge",
        json={"package_id": "pro", "payment_method": "mada"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["success"] is True
    assert data["credits_added"] == 2500
    assert data["transaction_id"].startswith("ZX-")
    assert data["package"] == "pro"
    assert data["payment_method"] == "mada"


def test_recharge_invalid_package():
    r = requests.post(
        f"{API}/recharge",
        json={"package_id": "bogus", "payment_method": "mada"},
        timeout=10,
    )
    assert r.status_code == 400


def test_recharge_invalid_method():
    r = requests.post(
        f"{API}/recharge",
        json={"package_id": "pro", "payment_method": "paypal"},
        timeout=10,
    )
    assert r.status_code == 400


# ─── Video generation (real ffmpeg + TTS) ───────────────────────────────────
@pytest.mark.timeout(240)
def test_generate_video_15s():
    payload = {
        "title": "ساعة Apple Watch Ultra 2",
        "duration_seconds": 15,
        "voice": "zenrex_male_deep",
        "cta": "اطلب الآن",
        "scenes": [
            {"seq": 1, "narration": "اكتشف الفخامة في كل تفصيل.",  "image_url": UNSPLASH_IMG},
            {"seq": 2, "narration": "تصميم أنيق وأداء فائق.",       "image_url": UNSPLASH_IMG},
            {"seq": 3, "narration": "اطلبها الآن قبل النفاد.",       "image_url": UNSPLASH_IMG},
        ],
    }
    t0 = time.time()
    r = requests.post(f"{API}/generate", json=payload, timeout=200)
    elapsed = time.time() - t0
    assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
    data = r.json()
    video_url = data.get("video_url")
    assert video_url, f"missing video_url in {data}"
    # Build absolute URL if relative
    full = video_url if video_url.startswith("http") else f"{BASE_URL}{video_url}"

    # HEAD/GET the file.  Some setups don't expose HEAD, so fall back to GET stream.
    h = requests.get(full, timeout=60, stream=True)
    assert h.status_code == 200, f"video fetch {h.status_code} for {full}"
    ctype = h.headers.get("content-type", "")
    assert "video" in ctype or "mp4" in ctype, f"unexpected content-type {ctype}"
    # Read first 16 bytes — MP4 files have 'ftyp' atom near the start.
    chunk = next(h.iter_content(1024))
    assert b"ftyp" in chunk[:32], "file does not look like an MP4 (no ftyp atom)"
    print(f"video generated in {elapsed:.1f}s, size>= {len(chunk)} first bytes, url={full}")
