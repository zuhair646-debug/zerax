"""
🎙️ Voice Acting AI — dialogue → mp3
═══════════════════════════════════════════════════════════════════════
Used by `<<VOICE: dialogue | character: name | mood: angry>>` tag in chat.
Tries (in order):
  1. ElevenLabs   — if user provided ELEVENLABS_API_KEY (best quality).
  2. OpenAI TTS   — via Emergent Universal Key (default, no extra setup).

Voices preset by character archetype (warrior / villain / merchant / etc.)
so the game keeps consistent voice acting across hundreds of lines.
"""
from __future__ import annotations
import os, uuid, asyncio, logging, base64
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Character archetype → voice preset
# ─────────────────────────────────────────────────────────────
ELEVENLABS_VOICES = {
    "warrior":   "21m00Tcm4TlvDq8ikWAM",   # Rachel — calm strong
    "villain":   "ErXwobaYiN019PkySvjV",   # Antoni — deep menacing
    "merchant":  "VR6AewLTigWG4xSOukaG",   # Arnold — warm
    "elder":     "pNInz6obpgDQGcFmaJgB",   # Adam — deep wise
    "child":     "EXAVITQu4vr4xnSDxMaL",   # Bella — bright young
    "narrator":  "5Q0t7uMcjvnagumLfvZi",   # Paul — narration
    "default":   "21m00Tcm4TlvDq8ikWAM",
}

OPENAI_VOICES = {
    "warrior":   "onyx",
    "villain":   "echo",
    "merchant":  "alloy",
    "elder":     "fable",
    "child":     "nova",
    "narrator":  "shimmer",
    "default":   "alloy",
}


async def generate_voice_line(
    text: str,
    character: str = "default",
    mood: str = "neutral",
    project_id: str = "",
) -> Dict[str, Any]:
    """Generate a single voice line and return a downloadable asset dict.
    Always returns the same shape as image generators so the frontend can
    drop it into the chat as a media card.
    """
    asset_id = str(uuid.uuid4())
    voice_key = (character or "default").lower().strip()
    voice_key = voice_key if voice_key in OPENAI_VOICES else "default"

    audio_bytes: Optional[bytes] = None
    provider = "openai"
    error = None

    # ── Attempt 1: ElevenLabs (if key present) ───────────────
    elabs_key = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVEN_LABS_KEY")
    if elabs_key:
        try:
            voice_id = ELEVENLABS_VOICES.get(voice_key, ELEVENLABS_VOICES["default"])
            async with httpx.AsyncClient(timeout=60) as cli:
                r = await cli.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={
                        "xi-api-key": elabs_key,
                        "Content-Type": "application/json",
                        "Accept": "audio/mpeg",
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_multilingual_v2",
                        "voice_settings": {
                            "stability": 0.55,
                            "similarity_boost": 0.85,
                            "style": 0.4 if mood != "neutral" else 0.1,
                        },
                    },
                )
                if r.status_code == 200 and r.content:
                    audio_bytes = r.content
                    provider = "elevenlabs"
                else:
                    error = f"ElevenLabs {r.status_code}: {r.text[:200]}"
                    logger.warning(f"[voice] elevenlabs failed: {error}")
        except Exception as e:
            error = f"ElevenLabs exception: {e}"
            logger.warning(f"[voice] elevenlabs exception: {e}")

    # ── Attempt 2: OpenAI TTS via Emergent (default) ─────────
    if not audio_bytes:
        try:
            from emergentintegrations.llm.openai.tts import OpenAITextToSpeech
            from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration  # noqa: just ensure import path
            voice = OPENAI_VOICES.get(voice_key, "alloy")
            client = OpenAITextToSpeech(api_key=os.environ.get("EMERGENT_LLM_KEY", ""))
            audio_bytes = await client.text_to_speech(
                text=text,
                voice=voice,
                model="gpt-4o-mini-tts",
            )
            provider = "openai-tts"
        except Exception as e:
            logger.exception(f"[voice] openai-tts failed: {e}")
            if not error:
                error = f"OpenAI TTS error: {e}"

    if not audio_bytes:
        return {
            "id": asset_id,
            "type": "error",
            "subtype": "voice",
            "name": (text[:60] + "…") if len(text) > 60 else text,
            "error": error or "Could not synthesize speech",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "id": asset_id,
        "type": "voice",
        "subtype": provider,
        "name": (text[:80] + "…") if len(text) > 80 else text,
        "_bytes": audio_bytes,
        "audio_url": f"/api/games/asset-image/{project_id}/{asset_id}.mp3",
        "character": voice_key,
        "mood": mood,
        "text": text,
        "approved": False,
        "duration_sec": max(1, int(len(text) / 14)),  # rough estimate ~14 chars/sec
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# Tag parser for <<VOICE: text | character: name | mood: angry>>
# ─────────────────────────────────────────────────────────────
import re as _re

VOICE_TAG_RE = _re.compile(r"<<\s*VOICE\s*[:：\-]?\s*([^>]+?)>>", _re.IGNORECASE | _re.DOTALL)


def parse_voice_args(body: str) -> Dict[str, str]:
    """Parse 'text | character: name | mood: m' into a dict."""
    parts = [p.strip() for p in body.split("|") if p.strip()]
    out = {"text": "", "character": "default", "mood": "neutral"}
    if not parts:
        return out
    out["text"] = parts[0].strip()
    for p in parts[1:]:
        if ":" in p:
            k, v = p.split(":", 1)
            k = k.strip().lower()
            v = v.strip()
            if k in out:
                out[k] = v
    return out


async def parse_and_generate_voices(ai_response: str, project_id: str, max_per_turn: int = 2):
    matches = VOICE_TAG_RE.findall(ai_response)
    if not matches:
        return []
    matches = matches[:max_per_turn]
    tasks = []
    for body in matches:
        args = parse_voice_args(body)
        if not args["text"]:
            continue
        tasks.append(generate_voice_line(args["text"], args["character"], args["mood"], project_id))
    if not tasks:
        return []
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, dict)]
