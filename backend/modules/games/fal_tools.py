"""
🎮 FAL.AI tools for Games Studio
─────────────────────────────────
Unified asset-generation module that powers the AAA-quality game production
pipeline. Each function downloads the result to /app/backend/uploads/games/...
and returns a local URL the frontend can render inline.

Supported tags (parsed from AI chat response):
   <<IMG_PRO: prompt>>             → Flux Pro Ultra 1.1 — cinematic 4K image
   <<3D: prompt>>                  → Trellis — text-to-3D (.glb)
   <<ANIMATE: prompt | img: url>>  → Kling 1.6 image-to-video animation
   <<MUSIC: prompt | dur: 30>>     → CassetteAI — game soundtrack
   <<SFX: prompt | dur: 5>>        → MMAudio v2 — sound effects

The basic <<IMG: ...>> tag is still served by OpenAI gpt-image-1 (handled in
game_router.py) — fast & cheap drafts. Use IMG_PRO for hero shots.
"""
from __future__ import annotations
import os
import re
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

UPLOAD_ROOT = "/app/backend/uploads/games"


def _ensure_fal_key() -> str:
    """Resolve a working FAL_KEY. Source priority:
       1. MongoDB credentials_kv  ← PERSISTS across Railway restarts ✅
       2. Local JSON vault       ← legacy / dev
       3. Env variable           ← Railway fallback
       Supports multi-key rotation via FAL_KEYS = "k1,k2,k3".
    """
    candidates: list[str] = []

    # 1) MongoDB (PERSISTENT)
    try:
        from modules.games.creds_store import kv_get_sync as _kvg
        multi_db = (_kvg("FAL_KEYS") or "").strip()
        if multi_db:
            candidates += [k.strip() for k in multi_db.split(",") if k.strip()]
        single_db = (_kvg("FAL_KEY") or "").strip()
        if single_db and single_db not in candidates:
            candidates.append(single_db)
    except Exception:
        pass

    # 2) JSON vault (legacy)
    try:
        from modules.autocoder.credentials_vault import vault_get as _vget
        multi = (_vget("FAL_KEYS") or "").strip()
        if multi:
            for k in [k.strip() for k in multi.split(",") if k.strip()]:
                if k not in candidates:
                    candidates.append(k)
        single = (_vget("FAL_KEY") or _vget("FAL_API_KEY") or "").strip()
        if single and single not in candidates:
            candidates.append(single)
    except Exception:
        pass

    # 3) Env
    envk = (os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY") or "").strip()
    if envk and envk not in candidates:
        candidates.append(envk)

    if not candidates:
        raise RuntimeError("FAL_KEY missing — set it via FalKeyManager")

    os.environ["FAL_KEY"] = candidates[0]
    os.environ["_FAL_KEYS_LIST"] = ",".join(candidates)
    return candidates[0]


def _try_fal_with_rotation(fn, *, max_retries: int = None):
    """Run a sync fal_client call, rotating through all known keys when one
    fails with 'invalid key credentials' or 'unauthorized'. Returns the first
    successful response, or re-raises the last error.
    """
    _ensure_fal_key()
    keys = (os.environ.get("_FAL_KEYS_LIST") or os.environ.get("FAL_KEY") or "").split(",")
    keys = [k.strip() for k in keys if k.strip()]
    if not keys:
        raise RuntimeError("No FAL keys available")
    if max_retries is None:
        max_retries = len(keys)
    last_err = None
    import logging as _l
    log = _l.getLogger(__name__)
    for i, k in enumerate(keys[:max_retries]):
        try:
            os.environ["FAL_KEY"] = k
            return fn()
        except Exception as e:
            msg = str(e).lower()
            last_err = e
            if any(t in msg for t in ("invalid key credentials", "unauthorized", "forbidden", "401", "403")):
                log.warning(f"[fal-rotate] key #{i+1} ({k[:8]}...) failed: {msg[:80]} — trying next")
                continue
            # Other errors (network, 5xx, prompt safety) — don't waste keys
            raise
    raise last_err if last_err else RuntimeError("All FAL keys exhausted")


async def _download_to(url: str, dest_path: str, timeout: float = 120.0) -> None:
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(r.content)


async def _fal_submit(model_endpoint: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Submit a fal.ai job and wait for completion. Returns the result dict."""
    _ensure_fal_key()
    import fal_client  # lazy import — only loaded if FAL_KEY is set

    def _sync_submit():
        # fal_client.submit() is sync; we wrap in run_in_executor for async use
        handler = fal_client.submit(model_endpoint, arguments=arguments)
        return handler.get()  # blocks until job finishes

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_submit)


# ════════════════════════════════════════════════════════════════
# 🎨 PROMPT BOOSTER — auto-augments every image prompt so the result
# matches AAA-studio quality (Fortnite / Epic Games / Riot Games level).
# Picks the right "style anchor" depending on the project's style_profile.
# ════════════════════════════════════════════════════════════════
STYLE_PROFILES = {
    "realistic": (
        "AAA game studio quality, photorealistic textures, Unreal Engine 5 render, "
        "ray-traced global illumination, volumetric lighting, 8K ultra-detailed, "
        "cinematic depth of field, ArtStation trending, masterpiece"
    ),
    "stylized": (
        "AAA stylized realism in the style of Fortnite and Riot Games, "
        "soft physically-based shaders, hand-painted textures with PBR depth, "
        "cinematic key lighting, vibrant saturated colors, Unreal Engine 5, "
        "ultra-detailed, ArtStation hero quality"
    ),
    "anime": (
        "high-end anime game art, Genshin Impact style, cel-shaded with subtle gradients, "
        "vibrant colors, sharp linework, cinematic composition, masterpiece quality, 8K"
    ),
    "low_poly": (
        "modern low-poly game art, clean flat shading, vibrant pastel palette, "
        "soft ambient occlusion, isometric or 3/4 view, professional polish"
    ),
    "pixel": (
        "premium 32-bit pixel art, crisp pixels, careful anti-aliasing, "
        "vibrant retro palette, professional game studio quality (Octopath Traveler caliber)"
    ),
}

_BANNED_TERMS = ("childish", "amateur", "scribble", "doodle", "stick figure", "rough sketch")


def boost_prompt(prompt: str, style_profile: str = "stylized") -> str:
    """Auto-augment a raw prompt with quality boosters & a style anchor.
    The booster is only added if the prompt doesn't already contain its own
    explicit style anchor (e.g. user wrote "pixel art" — we trust them).
    """
    p = (prompt or "").strip()
    lowered = p.lower()
    # If the AI already specified the strong style anchors, don't double-boost
    has_anchor = any(
        kw in lowered
        for kw in (
            "unreal engine", "octane", "render", "8k", "4k ultra",
            "photorealistic", "fortnite", "genshin", "pixel art",
            "low poly", "cel-shade", "cel shade", "anime style",
        )
    )
    if has_anchor:
        booster = ""
    else:
        booster = ", " + STYLE_PROFILES.get(style_profile, STYLE_PROFILES["stylized"])
    # Strip banned amateur-quality terms users might accidentally include
    for bad in _BANNED_TERMS:
        if bad in lowered:
            p = re.sub(re.escape(bad), "", p, flags=re.IGNORECASE)
    return f"{p}{booster}".strip(" ,")


def _save_image_bytes(img_bytes: bytes, project_id: str) -> Dict[str, Any]:
    """Helper: save image bytes locally and return the games-asset dict skeleton."""
    asset_id = str(uuid.uuid4())
    dest = f"{UPLOAD_ROOT}/{project_id}/assets/{asset_id}.png"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as fh:
        fh.write(img_bytes)
    return {
        "id": asset_id,
        "dest": dest,
        "image_url": f"/api/games/asset-image/{project_id}/{asset_id}.png",
    }


async def _img_via_openai_direct(prompt: str, aspect_ratio: str) -> bytes:
    """🥇 PRIMARY — GPT-Image-1 via DIRECT OpenAI key (truly independent of Emergent)."""
    oai_key = (os.environ.get("OPENAI_DIRECT_KEY") or
               os.environ.get("OPENAI_API_KEY") or "").strip()
    if not oai_key:
        raise RuntimeError("OPENAI_DIRECT_KEY/OPENAI_API_KEY not set")
    size_map = {"16:9": "1536x1024", "9:16": "1024x1536", "1:1": "1024x1024",
                "4:3": "1536x1024", "3:4": "1024x1536"}
    size = size_map.get(aspect_ratio, "1536x1024")
    import base64 as _b64
    async with httpx.AsyncClient(timeout=180.0) as c:
        r = await c.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {oai_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-image-1",
                "prompt": prompt[:32000],
                "size": size,
                "n": 1,
                "quality": "high",
            },
        )
        if r.status_code != 200:
            raise RuntimeError(f"gpt-image-1 {r.status_code}: {r.text[:300]}")
        j = r.json()
        b64 = j["data"][0].get("b64_json")
        if not b64:
            # Some accounts return url instead
            img_url = j["data"][0].get("url")
            if not img_url:
                raise RuntimeError(f"gpt-image-1 returned no b64/url: {j}")
            rr = await c.get(img_url, timeout=120)
            rr.raise_for_status()
            return rr.content
        return _b64.b64decode(b64)


async def _img_via_nano_banana(prompt: str) -> bytes:
    """🥈 FALLBACK — Nano Banana (Gemini 2.5 Flash Image) via Emergent universal key.
    Proven working in production via /app/backend/modules/autocoder/media_tools.py."""
    em_key = (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
    if not em_key:
        raise RuntimeError("EMERGENT_LLM_KEY not set")
    import base64 as _b64
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=em_key,
        session_id=f"games-img-{uuid.uuid4().hex[:8]}",
        system_message="You generate high-quality cinematic game art images.",
    )
    chat.with_model("gemini", "gemini-2.5-flash-image-preview")
    res = await chat.send_message(UserMessage(text=prompt))
    img_b64 = None
    if hasattr(res, "images") and res.images:
        img_b64 = res.images[0]
    if not img_b64 and isinstance(res, str) and "base64," in res:
        img_b64 = res.split("base64,", 1)[1]
    if not img_b64:
        raise RuntimeError("nano_banana returned no image bytes")
    return _b64.b64decode(img_b64.split(",")[-1])


async def _img_via_fal_flux(prompt: str, aspect_ratio: str) -> bytes:
    """🥉 PREMIUM — Fal Flux Pro Ultra 1.1 (cinematic AAA quality if key works)."""
    result = await _fal_submit(
        "fal-ai/flux-pro/v1.1-ultra",
        {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "num_images": 1,
            "enable_safety_checker": True,
            "safety_tolerance": "5",
            "output_format": "png",
            "raw": False,
        },
    )
    img_url = (result.get("images") or [{}])[0].get("url")
    if not img_url:
        raise RuntimeError(f"flux_pro returned no image: {result}")
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as c:
        rr = await c.get(img_url)
        rr.raise_for_status()
        return rr.content


# ════════════════════════════════════════════════════════════════
# 1) AAA hero image — 3-tier independent waterfall
#    OpenAI Direct → Nano Banana → Fal Flux Pro Ultra
# ════════════════════════════════════════════════════════════════
async def generate_flux_pro(prompt: str, project_id: str, aspect_ratio: str = "16:9", style_profile: str = "stylized") -> Dict[str, Any]:
    """High-end cinematic game image. 3-tier independent waterfall:
       1) GPT-Image-1 via DIRECT OpenAI key (independent, top quality, ALWAYS works)
       2) Nano Banana (Gemini) via Emergent universal key (proven in production)
       3) Fal Flux Pro Ultra (premium AAA, used last because of Railway 401 instability)
    Returns the same asset dict shape as before, so all callers keep working."""
    boosted = boost_prompt(prompt, style_profile=style_profile)
    providers = [
        ("openai-gpt-image-1", lambda: _img_via_openai_direct(boosted, aspect_ratio)),
        ("nano-banana-gemini", lambda: _img_via_nano_banana(boosted)),
        ("flux-pro-ultra", lambda: _img_via_fal_flux(boosted, aspect_ratio)),
    ]
    errors: list[str] = []
    for subtype, fn in providers:
        try:
            img_bytes = await fn()
            if not img_bytes or len(img_bytes) < 512:
                raise RuntimeError(f"{subtype} returned empty/tiny payload ({len(img_bytes) if img_bytes else 0}b)")
            saved = _save_image_bytes(img_bytes, project_id)
            logger.info(f"[games][img] ✅ {subtype} succeeded ({len(img_bytes)//1024}KB)")
            return {
                "id": saved["id"],
                "type": "image",
                "subtype": subtype,
                "image_url": saved["image_url"],
                "cdn_url": None,
                "_bytes": img_bytes,
                "prompt": prompt,
                "name": prompt[:80],
                "approved": False,
                "fallback": subtype != "openai-gpt-image-1",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            err_short = str(e)[:200]
            errors.append(f"{subtype}: {err_short}")
            logger.warning(f"[games][img] ⚠️ {subtype} failed → {err_short}")
            continue
    raise RuntimeError(
        "كل مزودات توليد الصور فشلت. التفاصيل:\n• " + "\n• ".join(errors)
    )


# ════════════════════════════════════════════════════════════════
# 2) Trellis — text-to-3D (.glb mesh)
# ════════════════════════════════════════════════════════════════
async def generate_3d_model(prompt: str, project_id: str, reference_image_url: Optional[str] = None) -> Dict[str, Any]:
    """Generate a real 3D model (.glb) from text or image. ~$0.30, ~1-3 min."""
    # If we have a reference image, use trellis image-to-3D, else fall back to hyper3d-rodin (text-to-3D)
    if reference_image_url:
        model_id = "fal-ai/trellis"
        args = {"image_url": reference_image_url}
    else:
        # Hyper3D Rodin is the best text-to-3D currently on fal
        model_id = "fal-ai/hyper3d/rodin"
        args = {"prompt": prompt, "geometry_file_format": "glb"}

    result = await _fal_submit(model_id, args)
    # Extract glb URL — different fields per model
    model_url = None
    if "model_mesh" in result:
        mm = result["model_mesh"]
        model_url = mm.get("url") if isinstance(mm, dict) else mm
    elif "mesh" in result:
        m = result["mesh"]
        model_url = m.get("url") if isinstance(m, dict) else m
    elif "output_mesh" in result:
        model_url = result["output_mesh"].get("url") if isinstance(result["output_mesh"], dict) else result["output_mesh"]
    if not model_url:
        raise RuntimeError(f"3d model returned no mesh url: {result}")
    asset_id = str(uuid.uuid4())
    dest = f"{UPLOAD_ROOT}/{project_id}/3d/{asset_id}.glb"
    await _download_to(model_url, dest, timeout=180.0)
    try:
        with open(dest, "rb") as fh:
            file_bytes = fh.read()
    except Exception:
        file_bytes = None
    return {
        "id": asset_id,
        "type": "3d",
        "subtype": "hyper3d-rodin" if not reference_image_url else "trellis",
        "model_url": f"/api/games/asset-3d/{project_id}/{asset_id}.glb",
        "cdn_url": model_url,
        "_bytes": file_bytes,
        "prompt": prompt,
        "name": prompt[:80],
        "approved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ════════════════════════════════════════════════════════════════
# 3) Kling 1.6 — image-to-video animation
# ════════════════════════════════════════════════════════════════
async def animate_image(prompt: str, image_url: str, project_id: str, duration: int = 5) -> Dict[str, Any]:
    """Animate a still image into a 5-10s video clip. ~$0.50, ~1-2 min."""
    result = await _fal_submit(
        "fal-ai/kling-video/v1.6/standard/image-to-video",
        {
            "prompt": prompt,
            "image_url": image_url,
            "duration": str(duration),  # "5" or "10"
            "aspect_ratio": "16:9",
        },
    )
    video_url = (result.get("video") or {}).get("url") if isinstance(result.get("video"), dict) else None
    if not video_url:
        raise RuntimeError(f"kling returned no video: {result}")
    asset_id = str(uuid.uuid4())
    dest = f"{UPLOAD_ROOT}/{project_id}/videos/{asset_id}.mp4"
    await _download_to(video_url, dest, timeout=180.0)
    try:
        with open(dest, "rb") as fh:
            file_bytes = fh.read()
    except Exception:
        file_bytes = None
    return {
        "id": asset_id,
        "type": "video",
        "subtype": "kling-1.6",
        "video_url": f"/api/games/asset-video/{project_id}/{asset_id}.mp4",
        "cdn_url": video_url,
        "_bytes": file_bytes,
        "prompt": prompt,
        "name": prompt[:80],
        "duration_sec": duration,
        "approved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ════════════════════════════════════════════════════════════════
# 4) CassetteAI — text-to-music for game soundtracks
# ════════════════════════════════════════════════════════════════
async def generate_music(prompt: str, project_id: str, duration: int = 30) -> Dict[str, Any]:
    """Generate game background music. ~$0.03/30sec, ~10-30 sec."""
    result = await _fal_submit(
        "cassetteai/music-generator",
        {
            "prompt": prompt,
            "duration": min(int(duration), 180),
        },
    )
    audio_url = (result.get("audio_file") or {}).get("url") if isinstance(result.get("audio_file"), dict) else result.get("url")
    if not audio_url:
        raise RuntimeError(f"music gen returned no audio: {result}")
    asset_id = str(uuid.uuid4())
    dest = f"{UPLOAD_ROOT}/{project_id}/audio/{asset_id}.wav"
    await _download_to(audio_url, dest)
    try:
        with open(dest, "rb") as fh:
            file_bytes = fh.read()
    except Exception:
        file_bytes = None
    return {
        "id": asset_id,
        "type": "music",
        "subtype": "cassetteai",
        "audio_url": f"/api/games/asset-audio/{project_id}/{asset_id}.wav",
        "cdn_url": audio_url,
        "_bytes": file_bytes,
        "prompt": prompt,
        "name": prompt[:80],
        "duration_sec": duration,
        "approved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ════════════════════════════════════════════════════════════════
# 5) ElevenLabs SFX (via fal) — text-to-sound effects
# ════════════════════════════════════════════════════════════════
async def generate_sfx(prompt: str, project_id: str, duration: int = 5) -> Dict[str, Any]:
    """Generate a game sound effect via CassetteAI (jump, hit, coin, etc). ~$0.01, ~3-5 sec."""
    result = await _fal_submit(
        "cassetteai/sound-effects-generator",
        {
            "prompt": prompt,
            "duration": min(max(int(duration), 1), 30),
        },
    )
    audio_url = (result.get("audio_file") or {}).get("url") if isinstance(result.get("audio_file"), dict) else result.get("url")
    if not audio_url:
        raise RuntimeError(f"sfx returned no audio: {result}")
    asset_id = str(uuid.uuid4())
    dest = f"{UPLOAD_ROOT}/{project_id}/audio/{asset_id}.wav"
    await _download_to(audio_url, dest)
    try:
        with open(dest, "rb") as fh:
            file_bytes = fh.read()
    except Exception:
        file_bytes = None
    return {
        "id": asset_id,
        "type": "sfx",
        "subtype": "cassetteai-sfx",
        "audio_url": f"/api/games/asset-audio/{project_id}/{asset_id}.wav",
        "cdn_url": audio_url,
        "_bytes": file_bytes,
        "prompt": prompt,
        "name": prompt[:80],
        "duration_sec": duration,
        "approved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ════════════════════════════════════════════════════════════════
# Tag parser + dispatcher
# ════════════════════════════════════════════════════════════════
# Accept: <<IMG_PRO: ...>>, <<MODEL3D ...>>, <<3D-MODEL ...>>, full-width colon, missing colon, etc.
# Normalised tag names below mapped to canonical generator types.
TAG_RE = re.compile(
    r"<<\s*"
    r"(IMG[_\s-]?PRO|IMG[_\s-]?REF|IMG[_\s-]?EDIT|COMPOSE|BATCH|MODEL[_\s-]?3D|3D[_\s-]?MODEL|3D|ANIM(?:ATE)?|SOUNDTRACK|MUSIC|SOUND[_\s-]?FX|SFX)"
    r"\s*[:：\-]?\s*"
    r"(.+?)"
    r"\s*>>",
    re.DOTALL | re.IGNORECASE,
)


def _canon_tag(raw: str) -> str:
    """Map the many shapes the LLM may produce to one of the canonical types."""
    t = (raw or "").strip().upper().replace("-", "_").replace(" ", "_")
    if t in ("IMG_PRO", "IMGPRO"):
        return "IMG_PRO"
    if t in ("IMG_REF", "IMGREF"):
        return "IMG_REF"
    if t in ("IMG_EDIT", "IMGEDIT"):
        return "IMG_EDIT"
    if t in ("COMPOSE",):
        return "COMPOSE"
    if t in ("BATCH",):
        return "BATCH"
    if t in ("3D", "MODEL_3D", "MODEL3D", "3D_MODEL", "3DMODEL"):
        return "3D"
    if t in ("ANIM", "ANIMATE"):
        return "ANIMATE"
    if t in ("MUSIC", "SOUNDTRACK"):
        return "MUSIC"
    if t in ("SFX", "SOUND_FX", "SOUNDFX"):
        return "SFX"
    return t


async def parse_and_generate_assets(
    ai_response: str,
    project_id: str,
    max_assets_per_turn: int = 3,
    style_profile: str = "stylized",
    db=None,
) -> List[Dict[str, Any]]:
    """
    Parse all asset tags from the AI's response and generate them concurrently.
    Returns a list of generated asset dicts (ready to be appended to project + sent to frontend).

    The basic <<IMG: ...>> tag is NOT handled here (kept in game_router for backward compat).
    """
    # 🎨 LoRA lookup — if this project has a trained style LoRA we'll route IMG_PRO through it
    project_lora_url: Optional[str] = None
    project_trigger_word: str = ""
    if db is not None:
        try:
            _proj = await db.game_projects.find_one(
                {"id": project_id},
                {"lora.status": 1, "lora.lora_url": 1, "lora.trigger_word": 1},
            )
            _l = (_proj or {}).get("lora") or {}
            if _l.get("status") == "ready" and _l.get("lora_url"):
                project_lora_url = _l.get("lora_url")
                project_trigger_word = _l.get("trigger_word") or ""
        except Exception:
            pass

    matches = TAG_RE.findall(ai_response)
    # 📊 Learn from unparsed tag attempts (anything with <<…>> brackets we didn't match)
    if db is not None:
        try:
            all_brackets = re.findall(r"<<[^>]{1,200}>>", ai_response)
            matched_raw = set()
            for raw_t, raw_b in matches:
                matched_raw.add(f"<<{raw_t}:{raw_b}".strip())
            for raw in all_brackets:
                # Cheap check — if regex didn't match it, it's unparsed
                if not TAG_RE.search(raw):
                    from datetime import datetime as _dt, timezone as _tz
                    await db.games_unparsed_tags.update_one(
                        {"raw": raw[:300]},
                        {
                            "$inc": {"count": 1},
                            "$set": {"last_seen": _dt.now(_tz.utc).isoformat(),
                                      "last_project": project_id},
                            "$setOnInsert": {"first_seen": _dt.now(_tz.utc).isoformat()},
                        },
                        upsert=True,
                    )
        except Exception as ue:
            logger.warning(f"[fal][unparsed-log] skipped: {ue}")

    if not matches:
        return []

    matches = matches[:max_assets_per_turn]
    # 🚨 SAFETY: drop tags that look like template placeholders (AI emitting literal 'prompt'/'ID')
    _PLACEHOLDER_PATTERNS = re.compile(
        r"^(prompt|english\s+prompt|english\s+new\s+subject|english\s+edit|english\s+scene|english\s+motion\s+prompt|description|ID|ASSET_ID|<.*>|placeholder)\s*$",
        re.IGNORECASE,
    )
    filtered_matches = []
    for raw_tag, raw_body in matches:
        body_text = (raw_body or "").strip()
        if _PLACEHOLDER_PATTERNS.match(body_text):
            logger.warning(f"[fal] dropping placeholder tag <<{raw_tag}: {body_text}>> — AI used template text literally")
            continue
        # Also reject tags whose first segment is bare 'prompt'
        first_seg = body_text.split("|", 1)[0].strip()
        if _PLACEHOLDER_PATTERNS.match(first_seg):
            logger.warning(f"[fal] dropping tag with placeholder first segment: {body_text[:80]}")
            continue
        filtered_matches.append((raw_tag, raw_body))
    matches = filtered_matches
    tasks = []

    # 🔍 Build a quick lookup of project's approved images by asset_id (for IMG_REF/IMG_EDIT/COMPOSE)
    approved_by_id: Dict[str, Dict[str, Any]] = {}
    if db is not None:
        try:
            _proj_full = await db.game_projects.find_one(
                {"id": project_id},
                {"phases": 1},
            )
            for _phase in ((_proj_full or {}).get("phases") or {}).values():
                for _msg in (_phase.get("messages") or []):
                    for _a in (_msg.get("generated_assets") or []):
                        if (_a.get("type") == "image" and _a.get("approved")
                                and _a.get("id") and _a.get("image_url")):
                            approved_by_id[_a["id"]] = _a
        except Exception as _le:
            logger.warning(f"[fal] approved lookup failed: {_le}")

    def _resolve_ref(ref_str: str) -> Optional[str]:
        """Given an asset id or partial id, return the full local file path
        if the image exists on disk. Returns None if missing."""
        ref_str = (ref_str or "").strip()
        if not ref_str:
            return None
        # Exact id match first
        asset = approved_by_id.get(ref_str)
        if not asset:
            # Try prefix match (LLM may abbreviate UUID)
            for aid, a in approved_by_id.items():
                if aid.startswith(ref_str) or ref_str.startswith(aid[:8]):
                    asset = a
                    break
        if not asset:
            return None
        fname = (asset.get("image_url") or "").rsplit("/", 1)[-1]
        fpath = f"{UPLOAD_ROOT}/{project_id}/assets/{fname}"
        return fpath if os.path.exists(fpath) else None

    for raw_tag_type, raw_body in matches:
        tag_type = _canon_tag(raw_tag_type)
        body = raw_body.strip()
        try:
            if tag_type == "IMG_PRO":
                if project_lora_url:
                    # Route through trained LoRA for style-locked output
                    from modules.games.lora_training import generate_with_project_lora
                    tasks.append(generate_with_project_lora(
                        body, project_id, project_lora_url, project_trigger_word
                    ))
                else:
                    tasks.append(generate_flux_pro(body, project_id, style_profile=style_profile))
            elif tag_type == "IMG_REF":
                # syntax: <<IMG_REF: english prompt | ref: ASSET_ID>>
                ref_id, prompt_part = "", body
                if "ref:" in body.lower():
                    parts = re.split(r"\|", body, maxsplit=1)
                    prompt_part = parts[0].strip()
                    if len(parts) > 1:
                        ref_id = re.sub(r"^\s*ref\s*[:=]\s*", "", parts[1].strip(), flags=re.IGNORECASE).strip()
                ref_path = _resolve_ref(ref_id)
                if not ref_path:
                    logger.warning(f"[fal] IMG_REF: ref '{ref_id}' not found in approved — falling back to plain IMG_PRO")
                    tasks.append(generate_flux_pro(prompt_part, project_id, style_profile=style_profile))
                else:
                    # Use Flux Redux to remix the approved image with the new prompt
                    # (keeps style/colors/composition while changing the subject)
                    tasks.append(_img_ref_remix(ref_path, prompt_part, project_id, style_profile))
            elif tag_type == "IMG_EDIT":
                # syntax: <<IMG_EDIT: edit prompt | ref: ASSET_ID>>
                ref_id, edit_prompt = "", body
                if "ref:" in body.lower():
                    parts = re.split(r"\|", body, maxsplit=1)
                    edit_prompt = parts[0].strip()
                    if len(parts) > 1:
                        ref_id = re.sub(r"^\s*ref\s*[:=]\s*", "", parts[1].strip(), flags=re.IGNORECASE).strip()
                ref_path = _resolve_ref(ref_id)
                if not ref_path:
                    logger.warning(f"[fal] IMG_EDIT: ref '{ref_id}' not found — skipping")
                    continue
                # Build a /api/games/asset-image URL for edit_image_with_prompt
                asset = approved_by_id.get(ref_id) or next(
                    (a for aid, a in approved_by_id.items() if aid.startswith(ref_id)),
                    None,
                )
                if asset:
                    tasks.append(edit_image_with_prompt(asset["image_url"], edit_prompt, project_id))
            elif tag_type == "COMPOSE":
                # syntax: <<COMPOSE: scene description | refs: id1, id2, id3>>
                refs_str, scene_desc = "", body
                if "refs:" in body.lower() or "ref:" in body.lower():
                    parts = re.split(r"\|", body, maxsplit=1)
                    scene_desc = parts[0].strip()
                    if len(parts) > 1:
                        refs_str = re.sub(r"^\s*refs?\s*[:=]\s*", "", parts[1].strip(), flags=re.IGNORECASE).strip()
                ref_ids = [r.strip() for r in re.split(r"[,،]", refs_str) if r.strip()]
                ref_paths = [_resolve_ref(rid) for rid in ref_ids]
                ref_paths = [p for p in ref_paths if p]
                if len(ref_paths) < 2:
                    logger.warning(f"[fal] COMPOSE: need ≥2 valid refs (got {len(ref_paths)}) — falling back to IMG_PRO")
                    tasks.append(generate_flux_pro(scene_desc, project_id, style_profile=style_profile))
                else:
                    tasks.append(_compose_scene_from_refs(ref_paths, scene_desc, project_id))
            elif tag_type == "BATCH":
                # syntax: <<BATCH: english prompt | count: 6 | variations: slight|moderate|high>>
                # Returns N images generated in parallel, all variants of the same prompt.
                # Variations are seeded by appending subtle modifiers per index.
                prompt_part = body
                count = 4
                variations = "slight"
                # Parse all "key: value" pairs after the first "|"
                if "|" in body:
                    segments = [s.strip() for s in body.split("|")]
                    prompt_part = segments[0]
                    for seg in segments[1:]:
                        kv = re.match(r"\s*(count|variations|var)\s*[:=]\s*(.+)", seg, re.IGNORECASE)
                        if kv:
                            k = kv.group(1).lower()
                            v = kv.group(2).strip()
                            if k == "count":
                                try:
                                    count = max(2, min(int(v), 6))  # cap 2..6 for cost
                                except Exception:
                                    pass
                            elif k in ("variations", "var"):
                                vv = v.lower()
                                if vv in ("slight", "moderate", "high"):
                                    variations = vv
                # Build N variant prompts
                variant_modifiers = {
                    "slight": [
                        "early morning soft light",
                        "midday bright sunlight",
                        "warm golden hour",
                        "blue hour twilight",
                        "overcast diffused light",
                        "slightly different camera angle, same subject",
                    ],
                    "moderate": [
                        "morning, slightly younger growth",
                        "midday, fully mature",
                        "evening, autumn tones",
                        "after rain, glossy",
                        "windy, motion in foliage",
                        "wider shot showing surroundings",
                    ],
                    "high": [
                        "lush variant, very rich detail",
                        "minimal variant, sparse",
                        "stylized variant, painterly",
                        "realistic variant, photoreal",
                        "stormy variant, dramatic mood",
                        "night variant, with moonlight",
                    ],
                }
                mods = variant_modifiers[variations]
                for i in range(count):
                    variant_prompt = f"{prompt_part}. Variant {i+1}/{count}: {mods[i % len(mods)]}."
                    tasks.append(generate_flux_pro(variant_prompt, project_id, style_profile=style_profile))
            elif tag_type == "3D":
                tasks.append(generate_3d_model(body, project_id))
            elif tag_type == "ANIMATE":
                # syntax: <<ANIMATE: prompt | img: URL>>
                img_url = None
                if "img:" in body:
                    parts = body.split("|", 1)
                    prompt = parts[0].strip()
                    img_part = parts[1].strip()
                    img_url = img_part.replace("img:", "").strip()
                else:
                    prompt = body
                if not img_url:
                    logger.warning("[fal] ANIMATE tag missing img: URL — skipping")
                    continue
                tasks.append(animate_image(prompt, img_url, project_id))
            elif tag_type == "MUSIC":
                dur = 30
                if "dur:" in body:
                    parts = body.rsplit("|", 1)
                    prompt = parts[0].strip()
                    try:
                        dur = int(parts[1].replace("dur:", "").strip())
                    except Exception:
                        dur = 30
                else:
                    prompt = body
                tasks.append(generate_music(prompt, project_id, duration=dur))
            elif tag_type == "SFX":
                dur = 5
                if "dur:" in body:
                    parts = body.rsplit("|", 1)
                    prompt = parts[0].strip()
                    try:
                        dur = int(parts[1].replace("dur:", "").strip())
                    except Exception:
                        dur = 5
                else:
                    prompt = body
                tasks.append(generate_sfx(prompt, project_id, duration=dur))
        except Exception as e:
            logger.exception(f"[fal] failed to queue {tag_type}: {e}")

    if not tasks:
        return []

    results: List[Dict[str, Any]] = []
    settled = await asyncio.gather(*tasks, return_exceptions=True)
    for res in settled:
        if isinstance(res, Exception):
            logger.exception(f"[fal] asset generation failed: {res}")
        else:
            results.append(res)
    return results


# ════════════════════════════════════════════════════════════════
# 8) Flux Pro Redux — edit / re-style an EXISTING image
# Useful when owner says "ابي اعدل الصورة الفلانية" or "خلّي الإضاءة أحلى"
# ════════════════════════════════════════════════════════════════
async def edit_image_with_prompt(
    source_image_url: str,
    edit_prompt: str,
    project_id: str,
    aspect_ratio: str = "16:9",
) -> Dict[str, Any]:
    """Re-imagine an existing asset. Tries Fal Flux Pro Redux (img2img) first,
    falls back to Nano Banana (Gemini) which is excellent at instruction-based edits.
    The original image is preserved — caller keeps both versions."""
    errors: list[str] = []
    # 🥇 Try Fal Flux Pro Redux first (best img2img quality)
    try:
        result = await _fal_submit(
            "fal-ai/flux-pro/v1.1-ultra/redux",
            {
                "image_url": source_image_url,
                "prompt": edit_prompt,
                "aspect_ratio": aspect_ratio,
                "num_images": 1,
                "enable_safety_checker": True,
                "safety_tolerance": "5",
                "output_format": "png",
            },
        )
        img_url = (result.get("images") or [{}])[0].get("url")
        if not img_url:
            raise RuntimeError(f"flux redux returned no image: {result}")
        asset_id = str(uuid.uuid4())
        dest = f"{UPLOAD_ROOT}/{project_id}/assets/{asset_id}.png"
        await _download_to(img_url, dest)
        with open(dest, "rb") as fh:
            img_bytes = fh.read()
        return {
            "id": asset_id,
            "type": "image",
            "subtype": "flux-redux-edit",
            "image_url": f"/api/games/asset-image/{project_id}/{asset_id}.png",
            "cdn_url": img_url,
            "_bytes": img_bytes,
            "prompt": edit_prompt,
            "name": edit_prompt[:80],
            "source_image_url": source_image_url,
            "approved": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        errors.append(f"flux-redux: {str(e)[:160]}")
        logger.warning(f"[games][edit] Flux Redux failed → {e}; trying Nano Banana edit")

    # 🥈 Fallback: Nano Banana image editing (excellent at instruction edits)
    em_key = (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
    if em_key:
        try:
            import base64 as _b64
            # Download source bytes for Nano Banana
            src_bytes = b""
            if source_image_url.startswith("http"):
                async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
                    rr = await c.get(source_image_url)
                    rr.raise_for_status()
                    src_bytes = rr.content
            elif source_image_url.startswith("/api/games/asset-image/"):
                # local file
                parts = source_image_url.rsplit("/", 2)
                _pid, _fname = parts[-2], parts[-1]
                local = f"{UPLOAD_ROOT}/{_pid}/assets/{_fname}"
                with open(local, "rb") as fh:
                    src_bytes = fh.read()
            if not src_bytes:
                raise RuntimeError("could not load source image bytes")

            from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
            chat = LlmChat(
                api_key=em_key,
                session_id=f"games-edit-{uuid.uuid4().hex[:8]}",
                system_message="You edit images based on instructions. Return the edited image.",
            )
            chat.with_model("gemini", "gemini-2.5-flash-image-preview")
            res = await chat.send_message(UserMessage(
                text=edit_prompt,
                file_contents=[ImageContent(image_base64=_b64.b64encode(src_bytes).decode())],
            ))
            img_b64 = None
            if hasattr(res, "images") and res.images:
                img_b64 = res.images[0]
            if not img_b64 and isinstance(res, str) and "base64," in res:
                img_b64 = res.split("base64,", 1)[1]
            if not img_b64:
                raise RuntimeError("nano-banana edit returned no image")
            img_bytes = _b64.b64decode(img_b64.split(",")[-1])
            saved = _save_image_bytes(img_bytes, project_id)
            return {
                "id": saved["id"],
                "type": "image",
                "subtype": "nano-banana-edit",
                "image_url": saved["image_url"],
                "cdn_url": None,
                "_bytes": img_bytes,
                "prompt": edit_prompt,
                "name": edit_prompt[:80],
                "source_image_url": source_image_url,
                "approved": False,
                "fallback": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            errors.append(f"nano-banana-edit: {str(e)[:160]}")
    raise RuntimeError("تعديل الصورة فشل من كل المزودات: " + " | ".join(errors))


# ════════════════════════════════════════════════════════════════
# 9) IMG_REF — generate a NEW image that locks onto an approved image's style
# Uses Nano Banana (Gemini) with the approved image as a style anchor.
# Falls back to Flux Pro Ultra with a textual style-extraction prompt if vision fails.
# ════════════════════════════════════════════════════════════════
async def _img_ref_remix(
    ref_local_path: str,
    new_prompt: str,
    project_id: str,
    style_profile: str = "stylized",
) -> Dict[str, Any]:
    """Generate a new image that copies the visual DNA of the reference image
    but renders a NEW subject defined by `new_prompt`.
    Order:
      1) Nano Banana (Gemini) — accepts image + text, best for style-lock.
      2) Flux Pro Ultra fallback (textual style anchor only).
    """
    em_key = (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
    if em_key:
        try:
            import base64 as _b64
            with open(ref_local_path, "rb") as fh:
                ref_bytes = fh.read()
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            try:
                from emergentintegrations.llm.chat import ImageContent  # type: ignore
            except Exception:
                ImageContent = None  # type: ignore
            chat = LlmChat(
                api_key=em_key,
                session_id=f"games-imgref-{uuid.uuid4().hex[:8]}",
                system_message=(
                    "You are an expert game art director. Given a reference image and a new subject, "
                    "you render the new subject in the EXACT same style (colors, lighting, brushwork, "
                    "perspective, mood) as the reference."
                ),
            )
            chat.with_model("gemini", "gemini-2.5-flash-image-preview")
            prompt = (
                f"Reference style attached. Render this new subject in the EXACT same visual DNA: "
                f"{new_prompt}. Match the reference's lighting angle, color palette, brush style, "
                f"and perspective. Output a single high-quality image."
            )
            msg_args: Dict[str, Any] = {"text": prompt}
            if ImageContent is not None:
                try:
                    msg_args["file_contents"] = [ImageContent(image_base64=_b64.b64encode(ref_bytes).decode())]
                except Exception:
                    pass
            res = await chat.send_message(UserMessage(**msg_args))
            img_b64 = None
            if hasattr(res, "images") and res.images:
                img_b64 = res.images[0]
            if not img_b64 and isinstance(res, str) and "base64," in res:
                img_b64 = res.split("base64,", 1)[1]
            if img_b64:
                img_bytes = _b64.b64decode(img_b64.split(",")[-1])
                saved = _save_image_bytes(img_bytes, project_id)
                logger.info(f"[games][img_ref] ✅ nano-banana style-locked render ({len(img_bytes)//1024}KB)")
                return {
                    "id": saved["id"],
                    "type": "image",
                    "subtype": "img-ref-nano-banana",
                    "image_url": saved["image_url"],
                    "cdn_url": None,
                    "_bytes": img_bytes,
                    "prompt": new_prompt,
                    "name": new_prompt[:80],
                    "approved": False,
                    "ref_source": ref_local_path,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as e:
            logger.warning(f"[games][img_ref] nano-banana failed: {e} — trying Flux Pro fallback")

    # Fallback: plain Flux Pro Ultra with an explicit "match this style" anchor
    augmented = f"{new_prompt}. Style: identical to the previously approved asset (same palette, lighting, perspective, brush). Maintain visual consistency."
    return await generate_flux_pro(augmented, project_id, style_profile=style_profile)


# ════════════════════════════════════════════════════════════════
# 10) COMPOSE — combine multiple approved images into one cohesive scene
# Uses existing scene_composer module (Flux Redux multi-image merge).
# ════════════════════════════════════════════════════════════════
async def _compose_scene_from_refs(
    ref_local_paths: List[str],
    scene_description: str,
    project_id: str,
) -> Dict[str, Any]:
    """Combine 2-4 approved images into one cohesive composite scene.
    Uses Nano Banana (Gemini) — supports multi-image input + text instruction.
    Falls back to Flux Pro Ultra with strong textual description if Gemini fails.
    """
    em_key = (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
    refs = ref_local_paths[:4]
    if em_key and refs:
        try:
            import base64 as _b64
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            try:
                from emergentintegrations.llm.chat import ImageContent  # type: ignore
            except Exception:
                ImageContent = None  # type: ignore
            chat = LlmChat(
                api_key=em_key,
                session_id=f"games-compose-{uuid.uuid4().hex[:8]}",
                system_message=(
                    "You are a master art director. Compose ONE cohesive cinematic scene that "
                    "includes all the reference subjects in a single environment with unified "
                    "lighting and color grade. Maintain each reference's identity."
                ),
            )
            chat.with_model("gemini", "gemini-2.5-flash-image-preview")
            prompt = (
                f"Compose ONE cohesive cinematic scene that includes ALL of the reference subjects "
                f"in a single environment. {scene_description}. Maintain each reference's "
                f"identity (silhouette, palette, signature details). Apply a unified light source, "
                f"color grade, and depth-of-field. AAA studio composition."
            )
            msg_args: Dict[str, Any] = {"text": prompt}
            if ImageContent is not None:
                file_contents = []
                for p in refs:
                    try:
                        with open(p, "rb") as fh:
                            file_contents.append(ImageContent(image_base64=_b64.b64encode(fh.read()).decode()))
                    except Exception:
                        pass
                if file_contents:
                    msg_args["file_contents"] = file_contents
            res = await chat.send_message(UserMessage(**msg_args))
            img_b64 = None
            if hasattr(res, "images") and res.images:
                img_b64 = res.images[0]
            if not img_b64 and isinstance(res, str) and "base64," in res:
                img_b64 = res.split("base64,", 1)[1]
            if img_b64:
                img_bytes = _b64.b64decode(img_b64.split(",")[-1])
                saved = _save_image_bytes(img_bytes, project_id)
                logger.info(f"[games][compose] ✅ nano-banana composed scene from {len(refs)} refs ({len(img_bytes)//1024}KB)")
                return {
                    "id": saved["id"],
                    "type": "image",
                    "subtype": "compose-nano-banana",
                    "image_url": saved["image_url"],
                    "cdn_url": None,
                    "_bytes": img_bytes,
                    "prompt": scene_description,
                    "name": scene_description[:80],
                    "approved": False,
                    "composed_from": len(refs),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as e:
            logger.warning(f"[games][compose] nano-banana failed: {e} — falling back to Flux Pro textual")
    # Fallback: Flux Pro Ultra with a detailed compositional prompt
    listing = ", ".join(f"subject #{i+1} (preserve its identity)" for i in range(len(refs)))
    prompt = (
        f"Single cinematic composition featuring: {listing}, arranged in a believable layout. "
        f"Scene goal: {scene_description}. Cohesive lighting from one source, unified color grade, "
        f"AAA game studio composition, ultra-detailed."
    )
    return await generate_flux_pro(prompt, project_id, style_profile="stylized")
