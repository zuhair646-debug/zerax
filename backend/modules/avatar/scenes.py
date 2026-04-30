"""
Avatar Scene Videos — Sora 2 generated living animations for Zara/Layla.

Pre-generates short (4s) vertical clips of the avatars doing realistic actions
(sweeping, playing ball, jumping, dancing, sipping coffee, typing) and serves
them from the frontend's `/public/avatar-videos/` directory so they deploy
statically with the frontend.

Generation is admin-only and slow (Sora 2 takes 2-5 min per clip), so this
runs as a background task and updates a manifest.json consumed by the client.
"""
from __future__ import annotations
import os
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Where clips are stored (frontend public → served same-origin with the SPA)
PUBLIC_DIR = Path("/app/frontend/public/avatar-videos")
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH = PUBLIC_DIR / "manifest.json"

# ===== Character descriptions for consistent Sora 2 prompts =====
ZARA_DESC = (
    "a young 3D anime-style Saudi girl named Zara with long straight blonde hair, "
    "wearing a cream-colored soft sweater and blue jeans, brown ankle boots, "
    "warm cheerful expression, big expressive eyes, cinematic lighting"
)
LAYLA_DESC = (
    "a young 3D anime-style Saudi girl named Layla with long wavy dark brown hair, "
    "wearing an elegant black silk blouse and black tailored pants, "
    "calm confident expression, graceful posture, cinematic lighting"
)

BG_DESC = (
    "dark cosmic purple gradient background with subtle glowing stars, "
    "slight volumetric light from above, studio vibe, photo-real anime style, "
    "smooth 24fps animation, no camera shake, full body shot tightly centered, "
    "character fills about 70% of frame height, minimal empty space on sides"
)

# ===== Scene catalog =====
# Each scene: id, title, action_zara, action_layla (or shared)
SCENE_CATALOG: List[Dict[str, str]] = [
    {
        "id": "sweeping",
        "title": "تكنس الأرض",
        "action": "gently sweeping the floor with a broom, swaying slightly, looking content, in rhythm",
    },
    {
        "id": "football",
        "title": "تلعب كرة قدم",
        "action": "playfully kicking a small soccer ball, smiling, light footwork, ball bounces",
    },
    {
        "id": "jumping",
        "title": "تقفز بحماس",
        "action": "jumping up and down excitedly, arms raised in celebration, bouncy motion",
    },
    {
        "id": "dancing",
        "title": "ترقص بخفة",
        "action": "doing a soft light dance with gentle hand sways and small steps, happy",
    },
    {
        "id": "coffee",
        "title": "تشرب قهوة",
        "action": "slowly sipping from a white coffee cup, relaxed expression, steam rising",
    },
    {
        "id": "typing",
        "title": "تكتب على اللابتوب",
        "action": "sitting cross-legged, typing on a silver laptop, focused but smiling",
    },
    {
        "id": "wave",
        "title": "تلوح بحماس",
        "action": "waving hello with one hand energetically, making warm eye contact, friendly smile",
    },
]

CHARACTERS = {
    "zara": ZARA_DESC,
    "layla": LAYLA_DESC,
}


def _load_manifest() -> Dict[str, Any]:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"zara": [], "layla": [], "jobs": {}, "updated_at": None}


def _save_manifest(data: Dict[str, Any]) -> None:
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_prompt(character: str, scene_id: str) -> Optional[str]:
    desc = CHARACTERS.get(character)
    scene = next((s for s in SCENE_CATALOG if s["id"] == scene_id), None)
    if not desc or not scene:
        return None
    return (
        f"{desc}, {scene['action']}. {BG_DESC}. "
        f"The character is doing: {scene['action']}. "
        "Keep the same character appearance throughout, smooth loopable motion, "
        "no text, no logos, no watermark."
    )


def _generate_clip_sync(character: str, scene_id: str, out_path: str) -> Optional[str]:
    """Blocking Sora 2 call (runs in worker thread)."""
    from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY missing")
    prompt = _build_prompt(character, scene_id)
    if not prompt:
        raise ValueError(f"Unknown scene: {character}/{scene_id}")
    vg = OpenAIVideoGeneration(api_key=key)
    video_bytes = vg.text_to_video(
        prompt=prompt,
        model="sora-2",
        size="1280x720",  # only 1280x720 / 720x1280 accepted by Sora 2 API
        duration=4,
        max_wait_time=600,
    )
    if video_bytes:
        vg.save_video(video_bytes, out_path)
        return out_path
    return None


class GenerateSceneIn(BaseModel):
    character: str = Field(..., pattern="^(zara|layla)$")
    scene_id: str


class GenerateBatchIn(BaseModel):
    characters: List[str] = Field(default_factory=lambda: ["zara", "layla"])
    scene_ids: Optional[List[str]] = None  # None → all scenes


def register_scene_routes(router: APIRouter, db, require_admin_dep):
    """Register scene-video endpoints on the avatar router."""

    @router.get("/avatar/scenes/catalog")
    async def get_catalog():
        """Public: list all available scene slots."""
        return {
            "characters": list(CHARACTERS.keys()),
            "scenes": SCENE_CATALOG,
        }

    @router.get("/avatar/scenes/manifest")
    async def get_manifest():
        """Public: list of generated clips per character."""
        m = _load_manifest()
        return {
            "zara": m.get("zara", []),
            "layla": m.get("layla", []),
            "updated_at": m.get("updated_at"),
        }

    @router.post("/avatar/scenes/generate")
    async def generate_one(
        body: GenerateSceneIn,
        bg: BackgroundTasks,
        admin=Depends(require_admin_dep),
    ):
        """Admin only. Kicks off a Sora 2 generation job in the background."""
        if not _build_prompt(body.character, body.scene_id):
            raise HTTPException(400, "unknown character/scene")
        filename = f"{body.character}-{body.scene_id}.mp4"
        out_path = str(PUBLIC_DIR / filename)
        manifest = _load_manifest()
        manifest.setdefault("jobs", {})
        job_key = f"{body.character}:{body.scene_id}"
        manifest["jobs"][job_key] = {
            "status": "queued",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_manifest(manifest)

        async def _run():
            try:
                m2 = _load_manifest()
                m2.setdefault("jobs", {})
                m2["jobs"][job_key] = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()}
                _save_manifest(m2)
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, _generate_clip_sync, body.character, body.scene_id, out_path)
                m3 = _load_manifest()
                m3.setdefault("jobs", {})
                if result and Path(out_path).exists():
                    entry = {
                        "scene_id": body.scene_id,
                        "url": f"/avatar-videos/{filename}",
                        "filename": filename,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    clips = [c for c in m3.get(body.character, []) if c.get("scene_id") != body.scene_id]
                    clips.append(entry)
                    m3[body.character] = clips
                    m3["jobs"][job_key] = {"status": "done", "finished_at": datetime.now(timezone.utc).isoformat()}
                    logger.info(f"[SORA2] ✅ {job_key} → {out_path}")
                else:
                    m3["jobs"][job_key] = {"status": "failed", "error": "no bytes returned"}
                    logger.error(f"[SORA2] ❌ {job_key}: no bytes returned")
                _save_manifest(m3)
            except Exception as e:
                logger.error(f"[SORA2] ❌ {job_key}: {e}", exc_info=True)
                m4 = _load_manifest()
                m4.setdefault("jobs", {})
                m4["jobs"][job_key] = {"status": "failed", "error": str(e)[:200]}
                _save_manifest(m4)

        bg.add_task(_run)
        return {"ok": True, "job": job_key, "status": "queued"}

    @router.post("/avatar/scenes/generate-batch")
    async def generate_batch(
        body: GenerateBatchIn,
        bg: BackgroundTasks,
        admin=Depends(require_admin_dep),
    ):
        """Admin only. Queue generation of multiple clips."""
        scene_ids = body.scene_ids or [s["id"] for s in SCENE_CATALOG]
        queued = []
        manifest = _load_manifest()
        manifest.setdefault("jobs", {})
        for ch in body.characters:
            if ch not in CHARACTERS:
                continue
            for sid in scene_ids:
                if not _build_prompt(ch, sid):
                    continue
                job_key = f"{ch}:{sid}"
                manifest["jobs"][job_key] = {
                    "status": "queued",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                }
                queued.append(job_key)
        _save_manifest(manifest)

        async def _run_all():
            for job_key in queued:
                ch, sid = job_key.split(":", 1)
                filename = f"{ch}-{sid}.mp4"
                out_path = str(PUBLIC_DIR / filename)
                try:
                    m = _load_manifest()
                    m.setdefault("jobs", {})
                    m["jobs"][job_key] = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()}
                    _save_manifest(m)
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, _generate_clip_sync, ch, sid, out_path)
                    m2 = _load_manifest()
                    m2.setdefault("jobs", {})
                    if result and Path(out_path).exists():
                        entry = {
                            "scene_id": sid,
                            "url": f"/avatar-videos/{filename}",
                            "filename": filename,
                            "generated_at": datetime.now(timezone.utc).isoformat(),
                        }
                        clips = [c for c in m2.get(ch, []) if c.get("scene_id") != sid]
                        clips.append(entry)
                        m2[ch] = clips
                        m2["jobs"][job_key] = {"status": "done", "finished_at": datetime.now(timezone.utc).isoformat()}
                        logger.info(f"[SORA2-batch] ✅ {job_key}")
                    else:
                        m2["jobs"][job_key] = {"status": "failed", "error": "no bytes returned"}
                    _save_manifest(m2)
                except Exception as e:
                    logger.error(f"[SORA2-batch] ❌ {job_key}: {e}")
                    m3 = _load_manifest()
                    m3.setdefault("jobs", {})
                    m3["jobs"][job_key] = {"status": "failed", "error": str(e)[:200]}
                    _save_manifest(m3)

        bg.add_task(_run_all)
        return {"ok": True, "queued": queued, "count": len(queued)}

    @router.get("/avatar/scenes/jobs")
    async def get_jobs(admin=Depends(require_admin_dep)):
        """Admin: see in-flight / completed generation jobs."""
        m = _load_manifest()
        return {"jobs": m.get("jobs", {})}

    @router.delete("/avatar/scenes/{character}/{scene_id}")
    async def delete_clip(character: str, scene_id: str, admin=Depends(require_admin_dep)):
        """Admin: delete a generated clip."""
        filename = f"{character}-{scene_id}.mp4"
        p = PUBLIC_DIR / filename
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
        m = _load_manifest()
        if character in m:
            m[character] = [c for c in m[character] if c.get("scene_id") != scene_id]
        _save_manifest(m)
        return {"ok": True}
