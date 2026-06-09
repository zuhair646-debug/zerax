"""
Auto-Coder — Media generation tools (image / video / audio / screenshot).
These give the Owner Auto-Coder the ability to actually CREATE assets while
building Zerax (logos, hero images, voiceovers, video clips, visual diffs).

Each tool returns a dict with `ok`, a `url` to the produced asset (when
applicable) and any provider metadata. URLs use the static mount that
already exists in server.py (`/static/...`).
"""
from __future__ import annotations
import os
import io
import base64
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

MEDIA_ROOT = "/app/backend/static/autocoder_media"
os.makedirs(MEDIA_ROOT, exist_ok=True)


def _save_bytes(data: bytes, ext: str = "png") -> str:
    """Save bytes to MEDIA_ROOT and return the public path."""
    fname = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(MEDIA_ROOT, fname)
    with open(path, "wb") as f:
        f.write(data)
    return f"/static/autocoder_media/{fname}"


# ════════════════════════════════════════════════════════════════════════
# 🎨 IMAGE — Nano Banana (Gemini) primary, GPT-Image-1 fallback
# ════════════════════════════════════════════════════════════════════════
async def tool_generate_image(
    prompt: str,
    style: str = "modern",
    aspect: str = "1:1",
    save_as: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate an image with Nano Banana (Gemini) → fallback GPT-Image-1.
    aspect: '1:1', '16:9', '9:16', '4:3'.
    """
    if not prompt or len(prompt) < 5:
        return {"ok": False, "error": "prompt قصير جداً"}

    enriched = f"{prompt}. Style: {style}, high quality, professional."

    # --- Try Nano Banana via emergentintegrations ---
    em_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if em_key:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            chat = LlmChat(api_key=em_key, session_id=f"img-{uuid.uuid4().hex[:8]}",
                           system_message="You generate high-quality images.")
            chat.with_model("gemini", "gemini-2.5-flash-image-preview")
            try:
                from emergentintegrations.llm.chat import ImageContent  # type: ignore
            except Exception:
                ImageContent = None  # type: ignore
            res = await chat.send_message(UserMessage(text=enriched))
            # Nano Banana returns base64 in `.images` or in `_metadata['images']`
            img_b64 = None
            if hasattr(res, "images") and res.images:
                img_b64 = res.images[0]
            if not img_b64 and isinstance(res, str) and "base64," in res:
                img_b64 = res.split("base64,", 1)[1]
            if img_b64:
                data = base64.b64decode(img_b64.split(",")[-1])
                url = _save_bytes(data, "png")
                return {"ok": True, "provider": "nano_banana", "url": url,
                        "prompt": prompt, "aspect": aspect, "bytes": len(data)}
        except Exception as e:
            logger.warning(f"nano_banana image gen failed: {e}")

    # --- Fallback: GPT-Image-1 ---
    oai_key = (os.environ.get("OPENAI_API_KEY", "") or
               os.environ.get("OPENAI_DIRECT_KEY", "")).strip()
    if oai_key:
        try:
            size_map = {"1:1": "1024x1024", "16:9": "1792x1024",
                        "9:16": "1024x1792", "4:3": "1408x1024"}
            size = size_map.get(aspect, "1024x1024")
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={"Authorization": f"Bearer {oai_key}",
                             "Content-Type": "application/json"},
                    json={"model": "gpt-image-1", "prompt": enriched,
                          "size": size, "n": 1, "response_format": "b64_json"},
                )
                if r.status_code == 200:
                    j = r.json()
                    b64 = j["data"][0]["b64_json"]
                    data = base64.b64decode(b64)
                    url = _save_bytes(data, "png")
                    return {"ok": True, "provider": "gpt-image-1", "url": url,
                            "prompt": prompt, "aspect": aspect, "bytes": len(data)}
                return {"ok": False, "error": f"gpt-image-1 returned {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            return {"ok": False, "error": f"gpt-image-1 failed: {e}"}

    return {"ok": False, "error": "ما فيه مفاتيح متاحة: EMERGENT_LLM_KEY أو OPENAI_API_KEY"}


# ════════════════════════════════════════════════════════════════════════
# 🔊 AUDIO — ElevenLabs voiceover (primary), OpenAI TTS fallback
# ════════════════════════════════════════════════════════════════════════
async def tool_generate_audio(
    text: str,
    voice: str = "arabic_male",
    format: str = "mp3",
) -> Dict[str, Any]:
    """Generate voiceover audio. `voice` is a logical name; we map it."""
    if not text or len(text) < 2:
        return {"ok": False, "error": "نص فارغ"}

    el_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if el_key:
        try:
            voice_map = {
                "arabic_male": "pNInz6obpgDQGcFmaJgB",   # Adam (multilingual)
                "arabic_female": "EXAVITQu4vr4xnSDxMaL", # Bella
                "english_male": "TxGEqnHWrfWFTfGW9XjX",  # Josh
                "english_female": "21m00Tcm4TlvDq8ikWAM", # Rachel
            }
            voice_id = voice_map.get(voice, voice)
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={"xi-api-key": el_key, "Content-Type": "application/json"},
                    json={"text": text, "model_id": "eleven_multilingual_v2",
                          "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
                )
                if r.status_code == 200:
                    url = _save_bytes(r.content, "mp3")
                    return {"ok": True, "provider": "elevenlabs", "url": url,
                            "voice": voice, "bytes": len(r.content),
                            "duration_estimate_s": len(text.split()) / 2.5}
                return {"ok": False, "error": f"elevenlabs {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            logger.warning(f"elevenlabs failed: {e}")

    # Fallback: OpenAI TTS
    oai_key = (os.environ.get("OPENAI_API_KEY", "") or
               os.environ.get("OPENAI_DIRECT_KEY", "")).strip()
    if oai_key:
        try:
            openai_voice = "onyx" if "male" in voice else "nova"
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={"Authorization": f"Bearer {oai_key}",
                             "Content-Type": "application/json"},
                    json={"model": "tts-1-hd", "input": text[:4000],
                          "voice": openai_voice, "response_format": "mp3"},
                )
                if r.status_code == 200:
                    url = _save_bytes(r.content, "mp3")
                    return {"ok": True, "provider": "openai-tts", "url": url,
                            "voice": openai_voice, "bytes": len(r.content)}
                return {"ok": False, "error": f"openai-tts {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            return {"ok": False, "error": f"openai-tts failed: {e}"}

    return {"ok": False, "error": "ما فيه مفاتيح: ELEVENLABS_API_KEY أو OPENAI_API_KEY"}


# ════════════════════════════════════════════════════════════════════════
# 🎬 VIDEO — Sora 2 (via existing Owner key)
# ════════════════════════════════════════════════════════════════════════
async def tool_generate_video(
    prompt: str,
    seconds: int = 5,
    aspect: str = "16:9",
) -> Dict[str, Any]:
    """Trigger Sora 2 video generation (returns job_id, NOT the final file —
    rendering takes 1-3 min. Use tool_check_video_status to poll)."""
    if not prompt or len(prompt) < 8:
        return {"ok": False, "error": "prompt قصير جداً (≥8 chars)"}
    if seconds < 1 or seconds > 30:
        return {"ok": False, "error": "seconds must be 1-30"}

    oai_key = (os.environ.get("OPENAI_API_KEY", "") or
               os.environ.get("OPENAI_DIRECT_KEY", "")).strip()
    if not oai_key:
        return {"ok": False, "error": "OPENAI_API_KEY غير متاح"}

    size_map = {"16:9": "1280x720", "9:16": "720x1280", "1:1": "1024x1024"}
    size = size_map.get(aspect, "1280x720")
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                "https://api.openai.com/v1/videos",
                headers={"Authorization": f"Bearer {oai_key}",
                         "Content-Type": "application/json"},
                json={"model": "sora-2", "prompt": prompt[:2000],
                      "seconds": str(seconds), "size": size},
            )
            if r.status_code in (200, 201):
                j = r.json()
                return {"ok": True, "provider": "sora-2", "job_id": j.get("id"),
                        "status": j.get("status", "queued"), "prompt": prompt,
                        "seconds": seconds, "aspect": aspect,
                        "note": "استدعِ tool_check_video_status بعد 1-3 دقائق."}
            return {"ok": False, "error": f"sora-2 {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": f"sora-2 failed: {e}"}


async def tool_check_video_status(job_id: str) -> Dict[str, Any]:
    oai_key = (os.environ.get("OPENAI_API_KEY", "") or
               os.environ.get("OPENAI_DIRECT_KEY", "")).strip()
    if not oai_key:
        return {"ok": False, "error": "OPENAI_API_KEY غير متاح"}
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(
                f"https://api.openai.com/v1/videos/{job_id}",
                headers={"Authorization": f"Bearer {oai_key}"},
            )
            if r.status_code == 200:
                j = r.json()
                status = j.get("status")
                out = {"ok": True, "status": status, "job_id": job_id}
                if status == "completed":
                    # Download the video
                    vr = await c.get(
                        f"https://api.openai.com/v1/videos/{job_id}/content",
                        headers={"Authorization": f"Bearer {oai_key}"},
                    )
                    if vr.status_code == 200:
                        url = _save_bytes(vr.content, "mp4")
                        out["url"] = url
                        out["bytes"] = len(vr.content)
                return out
            return {"ok": False, "error": f"status {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ════════════════════════════════════════════════════════════════════════
# 👀 SCREENSHOT — Playwright
# ════════════════════════════════════════════════════════════════════════
async def tool_screenshot_page(
    url: str,
    width: int = 1366,
    height: int = 768,
    full_page: bool = False,
    wait_ms: int = 2000,
) -> Dict[str, Any]:
    """Open a URL in a headless browser and capture a screenshot."""
    try:
        from playwright.async_api import async_playwright
    except Exception:
        return {"ok": False,
                "error": "playwright غير مثبّت. ركّض: pip install playwright && playwright install chromium"}
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                ctx = await browser.new_context(viewport={"width": width, "height": height})
                page = await ctx.new_page()
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(wait_ms)
                buf = await page.screenshot(full_page=full_page, type="jpeg", quality=70)
                saved = _save_bytes(buf, "jpg")
                return {"ok": True, "url": saved, "source_url": url,
                        "width": width, "height": height, "full_page": full_page,
                        "bytes": len(buf),
                        "captured_at": datetime.now(timezone.utc).isoformat()}
            finally:
                await browser.close()
    except Exception as e:
        return {"ok": False, "error": f"screenshot failed: {str(e)[:300]}"}


# ════════════════════════════════════════════════════════════════════════
# 🌱 SEED DATABASE — quick test data for new sections
# ════════════════════════════════════════════════════════════════════════
async def tool_seed_db(db, collection: str, docs: list,
                       drop_first: bool = False) -> Dict[str, Any]:
    """Insert test documents into a MongoDB collection.
    Safety: refuses to touch core collections (users, sessions, payments)
    unless `drop_first=False` and inserts only."""
    PROTECTED = {"users", "credit_history", "payments", "stripe_events"}
    if collection in PROTECTED:
        return {"ok": False, "error": f"collection محمية: {collection}. ممنوع التعديل المباشر."}
    if not isinstance(docs, list) or not docs:
        return {"ok": False, "error": "docs لازم تكون list فيها وثائق"}
    if len(docs) > 500:
        return {"ok": False, "error": "حد أقصى 500 وثيقة في المرة الواحدة"}
    try:
        coll = db[collection]
        if drop_first:
            await coll.delete_many({"_test_seed": True})
        # Stamp every doc so we can clean up later
        for d in docs:
            d.setdefault("_test_seed", True)
            d.setdefault("created_at",
                         datetime.now(timezone.utc).isoformat())
            d.setdefault("id", uuid.uuid4().hex)
        await coll.insert_many(docs)
        # Return only ids, not full docs
        ids = [d.get("id") for d in docs]
        return {"ok": True, "collection": collection,
                "inserted": len(docs), "ids": ids[:20],
                "note": "كل وثائق test مختومة بـ_test_seed=True (سهل حذفها لاحقاً)"}
    except Exception as e:
        return {"ok": False, "error": f"seed failed: {str(e)[:300]}"}


async def tool_clear_test_seed(db, collection: str) -> Dict[str, Any]:
    """Remove all documents stamped with _test_seed=True from a collection."""
    if collection in {"users", "credit_history", "payments"}:
        return {"ok": False, "error": "collection محمية"}
    try:
        r = await db[collection].delete_many({"_test_seed": True})
        return {"ok": True, "collection": collection, "deleted": r.deleted_count}
    except Exception as e:
        return {"ok": False, "error": str(e)}
