"""
🟩 VideoCortex — video generation + scene planning (Sora 2 / Kling / Hailuo).

Strategy:
  - For now we delegate the actual video generation to the existing
    workflow_tools.py `generate_video` (it has fal.ai + provider routing).
  - The cortex adds an LLM planning step: turn the brief into a structured
    scene plan (shots, durations, transitions) BEFORE generation, so the
    user gets predictable output.
  - VideoCortex can call AudioCortex internally for soundtrack when the
    request mentions music/voiceover.

If the workflow_tools module isn't available, we degrade to text-only
scene planning (no actual video generated, but the plan is delivered).
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger("zenrex.cortex.video")


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


VIDEO_SYSTEM_PROMPT_AR = """أنت **VideoCortex** — متخصص التخطيط السينمائي في Zenrex.

**مهمتك:** تحويل وصف الفيديو لـ scene plan احترافي.

أرجع JSON بهذا الشكل:
{
  "title": "<عنوان قصير>",
  "duration_seconds": <عدد>,
  "scenes": [
    {
      "id": 1,
      "duration": 3,
      "shot": "wide shot of a black coffee shop facade at dusk",
      "camera_motion": "slow dolly forward",
      "lighting": "warm tungsten, neon accent",
      "audio_cue": "ambient city sounds, distant traffic"
    },
    ...
  ],
  "music_brief": "<وصف الموسيقى المرافقة>",
  "voiceover_text": "<نص الراوي إن وُجد>",
  "aspect_ratio": "16:9" أو "9:16" أو "1:1"
}

ركّز على لقطات قصيرة (2-4 ثوان) وتسلسل بصري واضح."""


async def _plan_scenes(user_message: str) -> Dict[str, Any]:
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        return {
            "title": user_message[:60],
            "duration_seconds": 10,
            "scenes": [{"id": 1, "duration": 10, "shot": user_message, "camera_motion": "static",
                         "lighting": "natural", "audio_cue": "silence"}],
            "music_brief": "",
            "voiceover_text": "",
            "aspect_ratio": "16:9",
            "fallback": True,
        }
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        session_id = f"video_cortex_{uuid.uuid4().hex[:8]}"
        chat = LlmChat(api_key=emergent_key, session_id=session_id,
                       system_message=VIDEO_SYSTEM_PROMPT_AR).with_model("anthropic", "claude-sonnet-4-5-20250929")
        response = await chat.send_message(UserMessage(text=f"خطّط فيديو لهذا الطلب:\n{user_message}"))
        raw = response if isinstance(response, str) else str(response)
        import re as _re
        m = _re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return {"title": user_message[:60], "duration_seconds": 10, "scenes": [],
                "music_brief": "", "voiceover_text": "", "aspect_ratio": "16:9", "fallback": True}
    except Exception as e:
        logger.warning(f"[video_cortex] plan failed: {e}")
        return {"title": user_message[:60], "duration_seconds": 10, "scenes": [],
                "music_brief": "", "voiceover_text": "", "aspect_ratio": "16:9", "fallback": True}


async def stream_video_cortex(
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
    yield _sse("cortex_started", {"cortex": "video", "message_excerpt": user_message[:120]})

    yield _sse("cortex_step", {"cortex": "video", "step": "planning",
                                "ar": "🎬 أبني خطة المشاهد السينمائية..."})
    plan = await _plan_scenes(user_message)
    yield _sse("cortex_step", {"cortex": "video", "step": "plan_ready",
                                "title": plan.get("title"),
                                "duration": plan.get("duration_seconds"),
                                "scenes_count": len(plan.get("scenes") or []),
                                "aspect_ratio": plan.get("aspect_ratio"),
                                "music_brief": plan.get("music_brief"),
                                "voiceover_text": plan.get("voiceover_text")})

    # ── Optionally trigger audio sub-task (voiceover) ───────────────────
    voiceover_url = None
    if plan.get("voiceover_text") and len(plan["voiceover_text"]) > 5:
        yield _sse("cortex_step", {"cortex": "video", "step": "voiceover",
                                    "ar": "🎙️ أصنع التعليق الصوتي..."})
        try:
            from .audio_cortex import _synthesize_tts
            tts = await _synthesize_tts(plan["voiceover_text"])
            if tts:
                voiceover_url = tts["url"]
                yield _sse("asset_produced", {"asset_type": "voiceover", "asset_url": voiceover_url,
                                               "model": tts["model"], "cortex": "video"})
        except Exception as e:
            logger.warning(f"[video_cortex] voiceover failed: {e}")

    # ── Try to actually generate the video via existing workflow tool ──
    yield _sse("cortex_step", {"cortex": "video", "step": "generating",
                                "ar": "🎥 أحاول توليد الفيديو الفعلي (قد يستغرق دقيقة)..."})
    video_url = None
    used_model = None
    try:
        from ...workflow_tools import generate_video as _gv  # type: ignore
        # Build a single composite prompt from the scene plan
        composite = " | ".join([
            f"Scene {s.get('id',i)}: {s.get('shot','')} ({s.get('camera_motion','')}, {s.get('lighting','')})"
            for i, s in enumerate(plan.get("scenes") or [], start=1)
        ]) or user_message
        # Simulated ctx
        class _FakeCtx:
            project_id = (project or {}).get("id")
            user_id = (project or {}).get("user_id")
            project_obj = project or {}
            db_obj = db
        fake_ctx = _FakeCtx()
        result = await _gv(fake_ctx, {
            "description": composite[:1500],
            "duration_seconds": min(int(plan.get("duration_seconds") or 10), 10),
            "aspect_ratio": plan.get("aspect_ratio") or "16:9",
            "model": "hailuo",  # cheap default; user can request premium explicitly
        })
        if isinstance(result, dict) and result.get("ok") and result.get("video_url"):
            video_url = result["video_url"]
            used_model = result.get("model")
    except Exception as e:
        logger.warning(f"[video_cortex] generate_video failed: {e}")

    if video_url:
        yield _sse("asset_produced", {"asset_type": "video", "asset_url": video_url,
                                       "model": used_model or "hailuo", "cortex": "video"})
        summary = (
            f"✅ **الفيديو جاهز**\n\n"
            f"**العنوان:** {plan.get('title','-')}\n"
            f"**المدة:** {plan.get('duration_seconds','-')}s · **نسبة العرض:** {plan.get('aspect_ratio','-')}\n"
            f"**الموديل:** `{used_model}`\n\n"
            f"**الرابط:** {video_url}\n"
            + (f"\n**التعليق الصوتي:** {voiceover_url}\n" if voiceover_url else "")
        )
        credits = 200
    else:
        summary = (
            f"📋 **خطة الفيديو جاهزة (لكن التوليد الفعلي تعذّر)**\n\n"
            f"**العنوان:** {plan.get('title','-')}\n"
            f"**المدة:** {plan.get('duration_seconds','-')}s\n"
            f"**عدد المشاهد:** {len(plan.get('scenes') or [])}\n\n"
            f"```json\n{json.dumps(plan, ensure_ascii=False, indent=2)[:1500]}\n```\n\n"
            "⚠️ التوليد الفعلي يتطلب FAL_KEY صالح وقد يحتاج تأكيد على الموديل المدفوع. حاول مجدداً أو فعّل المفتاح."
        )
        credits = 5

    try:
        if db is not None:
            await db.cortex_usage_stats.insert_one({
                "cortex": "video",
                "project_id": (project or {}).get("id"),
                "user_id": (project or {}).get("user_id"),
                "plan_title": plan.get("title"),
                "scenes_count": len(plan.get("scenes") or []),
                "video_url": video_url,
                "voiceover_url": voiceover_url,
                "model": used_model,
                "duration_ms": int((time.time() - t0) * 1000),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
    except Exception:
        pass

    yield _sse("done", {
        "summary": summary,
        "credits_charged": credits,
        "auto_refunded": video_url is None,
        "model_used": f"video_cortex/{used_model or 'plan-only'}",
        "iterations": 1,
        "options": [],
        "inline_images": [],
        "inline_video": [{"url": video_url, "model": used_model}] if video_url else [],
        "scene_plan": plan,
    })
