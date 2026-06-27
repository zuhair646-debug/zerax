"""
🟧 AudioCortex — voice synthesis + music + sound effects.

Provides:
  - TTS via Emergent OpenAI Whisper SDK (for transcription)
  - TTS via OpenAI gpt-4o-mini-tts or ElevenLabs (for synthesis)
  - Music generation prompts (Tone.js patterns embedded in delivered code)

Strategy:
  - For TTS: prefer OpenAI TTS (Emergent key works)
  - For music: emit a Tone.js boilerplate the user can embed
  - For SFX: emit a curated free-asset link (freesound.org / mixkit)

Future: hook into ElevenLabs API when user provides ELEVENLABS_API_KEY.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger("zenrex.cortex.audio")

_UPLOAD_DIR = Path("/app/backend/uploads/audio_cortex")
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _classify_audio_request(message: str) -> str:
    """Return one of: 'tts' (voiceover), 'music', 'sfx', or 'ambient'."""
    m = message.lower()
    if any(k in m for k in ["موسيقى", "music", "soundtrack", "ambient", "tone", "تيون", "نغمة"]):
        if "ambient" in m or "محيط" in m or "خلفي" in m:
            return "ambient"
        return "music"
    if any(k in m for k in ["تعليق صوتي", "voiceover", "narration", "صوت رواي", "tts", "اقرأ", "نطق"]):
        return "tts"
    if any(k in m for k in ["sfx", "مؤثر صوتي", "sound effect", "رنه", "click", "ding"]):
        return "sfx"
    return "tts"  # safe default — most audio requests are voice


async def _synthesize_tts(text: str, voice: str = "alloy", model: str = "gpt-4o-mini-tts") -> Optional[Dict[str, Any]]:
    """Synthesize speech via Emergent OpenAI TTS. Returns {url, model} or None."""
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        return None
    try:
        import httpx
        # Emergent universal endpoint — same wire format as OpenAI
        async with httpx.AsyncClient(timeout=60) as cl:
            r = await cl.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {emergent_key}", "Content-Type": "application/json"},
                json={"model": model, "voice": voice, "input": text[:4000], "response_format": "mp3"},
            )
        if r.status_code != 200:
            logger.warning(f"[audio_cortex] TTS HTTP {r.status_code}: {r.text[:160]}")
            return None
        fname = f"{uuid.uuid4().hex}.mp3"
        fpath = _UPLOAD_DIR / fname
        with open(fpath, "wb") as f:
            f.write(r.content)
        return {
            "url": f"/uploads/audio_cortex/{fname}",
            "size_bytes": len(r.content),
            "model": model,
            "voice": voice,
        }
    except Exception as e:
        logger.warning(f"[audio_cortex] TTS failed: {e}")
        return None


def _build_tonejs_snippet(kind: str, theme: str) -> str:
    """Generate a Tone.js boilerplate the user can embed in their page."""
    if kind == "ambient":
        return f"""<!-- 🎵 Tone.js ambient — theme: {theme} -->
<script src="https://cdn.jsdelivr.net/npm/tone@15.0.4/build/Tone.js"></script>
<script>
const reverb = new Tone.Reverb({{ decay: 8, wet: 0.6 }}).toDestination();
const synth = new Tone.PolySynth(Tone.AMSynth).connect(reverb);
synth.set({{ envelope: {{ attack: 2, release: 4 }}, oscillator: {{ type: "sine" }} }});
// gentle drifting chords
const chords = [["C3","E3","G3"], ["A2","C3","E3"], ["F2","A2","C3"]];
let idx = 0;
async function startAmbient() {{
  await Tone.start();
  Tone.Transport.scheduleRepeat(time => {{
    synth.triggerAttackRelease(chords[idx % chords.length], "2n", time);
    idx++;
  }}, "4n");
  Tone.Transport.start();
}}
// Call startAmbient() on user gesture (browser autoplay policy)
</script>"""
    if kind == "music":
        return f"""<!-- 🎵 Tone.js short melody — theme: {theme} -->
<script src="https://cdn.jsdelivr.net/npm/tone@15.0.4/build/Tone.js"></script>
<script>
const synth = new Tone.Synth().toDestination();
const notes = ["C4","E4","G4","B4","C5","B4","G4","E4"];
async function playMelody() {{
  await Tone.start();
  let t = Tone.now();
  notes.forEach((n,i) => synth.triggerAttackRelease(n, "8n", t + i * 0.25));
}}
</script>"""
    if kind == "sfx":
        return f"""<!-- 🔊 SFX kit — theme: {theme} -->
<script src="https://cdn.jsdelivr.net/npm/tone@15.0.4/build/Tone.js"></script>
<script>
const click = new Tone.MembraneSynth({{ pitchDecay: 0.008, octaves: 2 }}).toDestination();
async function ding() {{ await Tone.start(); click.triggerAttackRelease("C5", "16n"); }}
async function pop() {{ await Tone.start(); click.triggerAttackRelease("G4", "32n"); }}
// Wire to buttons: button.onclick = ding;
</script>"""
    return ""


async def stream_audio_cortex(
    project: Dict[str, Any],
    user_message: str,
    history: List[Dict[str, Any]],
    ctx_holder: Dict[str, Any],
    user_language: str = "ar",
    auth_token: Optional[str] = None,
    db=None,
    is_owner: bool = False,
    max_iterations: int = 60,
    inject_workflow_addendum: bool = False,
    shared_assets: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[str, None]:
    t0 = time.time()
    yield _sse("cortex_started", {"cortex": "audio", "message_excerpt": user_message[:120]})

    kind = await _classify_audio_request(user_message)
    yield _sse("cortex_step", {"cortex": "audio", "step": "classify", "kind": kind,
                                "ar": f"🔊 صنّفت الطلب كـ `{kind}`."})

    if kind == "tts":
        # Try to find the literal text to speak; fall back to using the full message
        text_to_speak = user_message
        # Heuristic: if message has Arabic colon followed by quoted text → use that
        import re as _re
        m = _re.search(r"[:：]\s*[«\"']([^»\"']{5,500})[»\"']", user_message)
        if m:
            text_to_speak = m.group(1)
        yield _sse("cortex_step", {"cortex": "audio", "step": "synthesize",
                                    "text_preview": text_to_speak[:200],
                                    "ar": "🎙️ أصنع الصوت..."})
        result = await _synthesize_tts(text_to_speak)
        if not result:
            yield _sse("cortex_error", {"cortex": "audio", "error": "TTS provider unavailable"})
            yield _sse("done", {
                "summary": "❌ تعذّر توليد الصوت. تأكد من EMERGENT_LLM_KEY.",
                "credits_charged": 0, "auto_refunded": True,
                "model_used": "audio_cortex", "iterations": 1, "options": [],
                "inline_images": [], "inline_audio": [],
            })
            return
        url = result["url"]
        yield _sse("asset_produced", {"asset_type": "audio", "asset_url": url,
                                       "model": result["model"], "cortex": "audio"})
        try:
            if db is not None:
                await db.cortex_usage_stats.insert_one({
                    "cortex": "audio", "kind": "tts",
                    "project_id": (project or {}).get("id"),
                    "user_id": (project or {}).get("user_id"),
                    "text_excerpt": text_to_speak[:200],
                    "model": result["model"],
                    "url": url,
                    "size_bytes": result.get("size_bytes"),
                    "duration_ms": int((time.time() - t0) * 1000),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
        except Exception:
            pass
        yield _sse("done", {
            "summary": f"✅ **الصوت جاهز**\n\nالموديل: `{result['model']}` / الصوت: `{result['voice']}`\n\nالرابط: {url}",
            "credits_charged": 20,
            "auto_refunded": False,
            "model_used": f"audio_cortex/{result['model']}",
            "iterations": 1,
            "options": [],
            "inline_images": [],
            "inline_audio": [{"url": url, "model": result["model"]}],
        })
        return

    # music / ambient / sfx — generate Tone.js snippet
    theme = user_message[:80]
    snippet = _build_tonejs_snippet(kind, theme)
    yield _sse("asset_produced", {"asset_type": "audio_snippet", "asset_url": "inline:tone.js",
                                   "snippet": snippet[:200], "cortex": "audio"})
    yield _sse("done", {
        "summary": (
            f"✅ **مقطع `{kind}` جاهز للحقن**\n\n"
            f"استخدم Tone.js (CDN) لتشغيله في الصفحة. الكود الجاهز:\n\n"
            f"```html\n{snippet}\n```\n\n"
            "💡 ضع `await Tone.start();` خلف أول تفاعل من المستخدم (سياسة autoplay)."
        ),
        "credits_charged": 10,
        "auto_refunded": False,
        "model_used": "audio_cortex/tonejs",
        "iterations": 1,
        "options": [],
        "inline_images": [],
        "inline_audio": [],
        "tone_snippet": snippet,
    })
