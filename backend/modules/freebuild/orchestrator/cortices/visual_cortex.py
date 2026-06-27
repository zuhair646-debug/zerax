"""
🟪 VisualCortex — focused image generation specialist.

Specialized for:
  - Logos, hero shots, posters, illustrations
  - Mockups, banners, icons, avatars
  - Cosmic/abstract/artistic creative direction

Uses Nano Banana (Gemini-2.5-flash-image-preview) via emergentintegrations.
Falls back to GPT-Image-1 if Nano Banana fails.

The cortex emits a `asset_produced` SSE event so the Orchestrator can
register the generated URL into `shared_assets` for downstream cortices.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger("zenrex.cortex.visual")

# Where to save generated images locally (served via /uploads/...)
_UPLOAD_DIR = Path("/app/backend/uploads/visual_cortex")
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


VISUAL_SYSTEM_PROMPT_AR = """أنت **VisualCortex** — متخصص الإبداع البصري في منظومة Zenrex.

**مهمتك المركّزة فقط:**
  1. فهم وصف الصورة المطلوبة من العميل (عربي/إنجليزي).
  2. تحويلها لـ prompt احترافي بالإنجليزية يستخدم مفردات photography/illustration حقيقية:
     - زاوية الكاميرا (low angle, wide shot, macro)
     - الإضاءة (golden hour, cinematic, soft diffused)
     - الأسلوب (photorealistic, anime, watercolor, isometric 3D)
     - الألوان (palette, mood, contrast)
     - التفاصيل (4K, ultra-detailed, sharp focus)
  3. اقتراح 1-3 prompts متباينة لو الطلب غامض.
  4. تجنّب AI Slop: لا violet gradients، لا generic stock photo look.

**القاعدة الذهبية:** الـ prompt الإنجليزي يقرر 80% من الجودة. لا تكتفِ بترجمة حرفية،
بل أعد صياغة بأسلوب prompt engineering. مثال:

  ❌ "صورة قط أسود"
  ✅ "Photorealistic close-up of a black domestic shorthair cat, golden-hour
     window light from the left, shallow depth of field f/1.8, intense amber
     eyes, fur texture visible, moody dark background, professional cat
     photography, 4K, sharp focus"

**اللغة في الرد:** عربية للعميل، لكن الـ prompt المرسل للنموذج بالإنجليزية فقط."""


async def _generate_with_emergent_image_gen(prompt: str, size: str = "1024x1024") -> Optional[Dict[str, Any]]:
    """Use emergentintegrations to call Gemini Nano Banana (gemini-2.5-flash-image-preview)
    or GPT-Image-1 as fallback. Returns dict with `url` (data URL or saved path) or None.
    """
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        logger.warning("[visual_cortex] EMERGENT_LLM_KEY missing — cannot generate")
        return None

    try:
        from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration  # type: ignore
    except Exception as e:
        logger.warning(f"[visual_cortex] emergentintegrations image module missing: {e}")
        return None

    try:
        client = OpenAIImageGeneration(api_key=emergent_key)
        # Try gpt-image-1 first (best fidelity for Arabic-aware briefs)
        result = await client.generate_images(
            prompt=prompt,
            model="gpt-image-1",
            number_of_images=1,
            # size param varies by model — fall through if it errors
        )
        # result is typically a list of bytes or dict
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, (bytes, bytearray)):
                # Save to disk + return URL
                fname = f"{uuid.uuid4().hex}.png"
                fpath = _UPLOAD_DIR / fname
                with open(fpath, "wb") as f:
                    f.write(first)
                url = f"/uploads/visual_cortex/{fname}"
                return {"url": url, "size_bytes": len(first), "model": "gpt-image-1"}
            elif isinstance(first, dict):
                # Some shapes return dict with url
                if first.get("url"):
                    return {"url": first["url"], "model": "gpt-image-1"}
                if first.get("b64_json"):
                    data = base64.b64decode(first["b64_json"])
                    fname = f"{uuid.uuid4().hex}.png"
                    fpath = _UPLOAD_DIR / fname
                    with open(fpath, "wb") as f:
                        f.write(data)
                    return {"url": f"/uploads/visual_cortex/{fname}",
                            "size_bytes": len(data), "model": "gpt-image-1"}
        return None
    except Exception as e:
        logger.warning(f"[visual_cortex] gpt-image-1 failed: {e}")
        return None


async def _refine_prompt_with_claude(user_message: str, user_language: str = "ar",
                                       history: Optional[List[Dict[str, Any]]] = None,
                                       memory_hint: str = "") -> Dict[str, Any]:
    """Run a short Claude call to convert the Arabic brief into a polished
    English image-generation prompt + Arabic explanation for the user.
    Uses chat history + project memory hint for continuity.
    """
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        # No LLM — just pass the raw message through (degraded quality)
        return {"english_prompt": user_message, "arabic_explanation": user_message, "fallback": True}

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        from ..shared_memory import history_to_messages
        # Reuse a stable session per project would be ideal, but session_id is per-LlmChat call
        session_id = f"visual_cortex_{uuid.uuid4().hex[:8]}"
        sys_prompt = VISUAL_SYSTEM_PROMPT_AR
        if memory_hint:
            sys_prompt = sys_prompt + "\n\n" + memory_hint
        chat = LlmChat(api_key=emergent_key, session_id=session_id,
                       system_message=sys_prompt).with_model("anthropic", "claude-sonnet-4-5-20250929")
        # Inject history as a context block (safer than role-replay).
        history_block = ""
        recent = history_to_messages(history or [], max_pairs=3)
        if recent:
            history_block = "\n\n📜 سياق سابق:\n" + "\n".join(
                f"  [{m['role']}]: {m['content'][:150]}" for m in recent
            ) + "\n"
        prompt_user = (
            f"{history_block}\n"
            f"طلب العميل الحالي: «{user_message}»\n\n"
            "أرجع JSON فقط بهذا الشكل:\n"
            "{\n"
            '  "english_prompt": "<the polished English image-gen prompt>",\n'
            '  "arabic_explanation": "<شرح موجز للعميل بالعربية ماذا فعلت ولماذا>",\n'
            '  "suggested_size": "1024x1024" أو "1792x1024" أو "1024x1792"\n'
            "}"
        )
        response = await chat.send_message(UserMessage(text=prompt_user))
        # Extract JSON
        raw = response if isinstance(response, str) else str(response)
        # Try to find JSON block
        import re as _re
        m = _re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                parsed = json.loads(m.group(0))
                return parsed
            except Exception:
                pass
        # Fallback — use raw response as both
        return {"english_prompt": user_message, "arabic_explanation": raw[:400], "fallback": True}
    except Exception as e:
        logger.warning(f"[visual_cortex] prompt refine failed: {e}")
        return {"english_prompt": user_message, "arabic_explanation": "تعذر تحسين الـ prompt، سأستخدم النص كما هو.",
                "fallback": True}


async def _generate_with_nano_banana(prompt: str) -> Optional[Dict[str, Any]]:
    """Try Gemini 2.5 Flash Image Preview (Nano Banana) via emergentintegrations.
    Returns dict with saved URL or None.
    """
    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        return None
    try:
        from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration  # type: ignore
        # Some emergent versions ship a dedicated gemini image helper
        try:
            from emergentintegrations.llm.google.image_generation import GeminiImageGeneration  # type: ignore
            client = GeminiImageGeneration(api_key=emergent_key)
            result = await client.generate_images(
                prompt=prompt, model="gemini-2.5-flash-image-preview", number_of_images=1,
            )
        except Exception:
            # Fall through to generic OpenAIImageGeneration with gemini model name
            client = OpenAIImageGeneration(api_key=emergent_key)
            result = await client.generate_images(
                prompt=prompt, model="gemini-2.5-flash-image-preview", number_of_images=1,
            )
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, (bytes, bytearray)):
                fname = f"{uuid.uuid4().hex}.png"
                fpath = _UPLOAD_DIR / fname
                with open(fpath, "wb") as f:
                    f.write(first)
                return {"url": f"/uploads/visual_cortex/{fname}", "size_bytes": len(first),
                        "model": "gemini-2.5-flash-image-preview"}
            if isinstance(first, dict):
                if first.get("url"):
                    return {"url": first["url"], "model": "gemini-2.5-flash-image-preview"}
                if first.get("b64_json"):
                    data = base64.b64decode(first["b64_json"])
                    fname = f"{uuid.uuid4().hex}.png"
                    fpath = _UPLOAD_DIR / fname
                    with open(fpath, "wb") as f:
                        f.write(data)
                    return {"url": f"/uploads/visual_cortex/{fname}", "size_bytes": len(data),
                            "model": "gemini-2.5-flash-image-preview"}
        return None
    except Exception as e:
        logger.warning(f"[visual_cortex] nano-banana failed: {e}")
        return None


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_visual_cortex(
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
    """Generate one or more images for the user request."""
    t0 = time.time()
    yield _sse("cortex_started", {"cortex": "visual", "message_excerpt": user_message[:120]})

    # ── 0. Load project memory (Brand DNA + past outputs) ────────────
    from ..shared_memory import load_memory, save_memory, memory_to_system_hint
    mem = await load_memory(db, (project or {}).get("id"))
    mem_hint = memory_to_system_hint(mem)
    if mem_hint:
        yield _sse("cortex_step", {"cortex": "visual", "step": "memory_loaded",
                                    "past_outputs_count": len(mem.get("past_outputs") or []),
                                    "has_brand_dna": bool(mem.get("brand_dna")),
                                    "ar": "📚 حمّلت ذاكرة المشروع — Brand DNA + الأعمال السابقة."})

    # ── 1. Refine prompt via Claude ────────────────────────────────────
    yield _sse("cortex_step", {"cortex": "visual", "step": "prompt_refinement",
                                "ar": "🧠 أحوّل وصفك إلى prompt احترافي بالإنجليزية..."})
    refined = await _refine_prompt_with_claude(user_message, user_language, history=history, memory_hint=mem_hint)
    en_prompt = refined.get("english_prompt") or user_message
    ar_expl = refined.get("arabic_explanation") or ""
    suggested_size = refined.get("suggested_size") or "1024x1024"

    yield _sse("cortex_step", {"cortex": "visual", "step": "prompt_ready",
                                "english_prompt": en_prompt[:400],
                                "arabic_explanation": ar_expl[:400],
                                "size": suggested_size})

    # ── 2. Generate image — Try Nano Banana FIRST (better quality), then gpt-image-1, then fal.ai ──
    yield _sse("cortex_step", {"cortex": "visual", "step": "generating",
                                "ar": "🎨 أولّد الصورة (Nano Banana → gpt-image-1 → fal.ai)..."})
    result = await _generate_with_nano_banana(en_prompt)
    if not result:
        yield _sse("cortex_step", {"cortex": "visual", "step": "trying_gpt_image",
                                    "ar": "🔄 Nano Banana لم يعمل، أحاول gpt-image-1..."})
        result = await _generate_with_emergent_image_gen(en_prompt, size=suggested_size)
    if not result:
        yield _sse("cortex_step", {"cortex": "visual", "step": "fallback_fal",
                                    "ar": "⚠️ كل المزودات الذكية تعذرت، أحاول fal.ai..."})
        fal_url = await _fallback_fal_flux(en_prompt, suggested_size)
        if fal_url:
            result = {"url": fal_url, "model": "fal-ai/flux/schnell"}
        else:
            yield _sse("cortex_error", {"cortex": "visual", "error": "All image generators failed"})
            yield _sse("done", {
                "summary": "❌ تعذّر توليد الصورة — كل المزودات الخارجية غير متاحة. حاول لاحقاً.",
                "credits_charged": 0,
                "auto_refunded": True,
                "model_used": "visual_cortex",
                "iterations": 1,
                "options": [],
                "inline_images": [],
            })
            return

    img_url = result.get("url")
    model_used = result.get("model", "gpt-image-1")

    # Save to project memory so subsequent turns have context
    await save_memory(db, (project or {}).get("id"), {
        "past_outputs": [{
            "cortex": "visual",
            "asset_url": img_url,
            "model": model_used,
            "prompt_excerpt": en_prompt[:200],
            "ts": datetime.now(timezone.utc).isoformat(),
        }],
        "last_message": user_message[:300],
    })

    # Emit asset_produced so multi-domain coordination captures it
    yield _sse("asset_produced", {"asset_type": "image", "asset_url": img_url,
                                   "model": model_used, "cortex": "visual"})

    # Log usage stats (best-effort)
    try:
        if db is not None:
            await db.cortex_usage_stats.insert_one({
                "cortex": "visual",
                "project_id": (project or {}).get("id"),
                "user_id": (project or {}).get("user_id"),
                "prompt_excerpt": en_prompt[:300],
                "model": model_used,
                "url": img_url,
                "size_bytes": result.get("size_bytes"),
                "duration_ms": int((time.time() - t0) * 1000),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
    except Exception as e:
        logger.warning(f"[visual_cortex] usage stat insert failed: {e}")

    # Charge credits (lightweight — defer real billing to action_pricing if available)
    credits_to_charge = 50  # ~$0.25 per image — single source of truth in action_pricing later

    summary = (
        f"✅ **تم توليد الصورة بنجاح**\n\n"
        f"**الموديل المستخدم:** `{model_used}`\n"
        f"**الـ prompt المُحسّن:**\n```\n{en_prompt[:600]}\n```\n\n"
        f"**شرح ما فعلت:** {ar_expl}\n\n"
        f"**الرابط:** {img_url}\n\n"
        f"💰 الرصيد المستهلك: ~{credits_to_charge} كريدت."
    )

    # Apply trade-secret scrubber so internal tool names don't leak
    try:
        from ...trade_secret import scrub_customer_text as scrub_output  # type: ignore
        summary = scrub_output(summary)
    except Exception:
        pass

    yield _sse("done", {
        "summary": summary,
        "credits_charged": credits_to_charge,
        "auto_refunded": False,
        "model_used": f"visual_cortex/{model_used}",
        "iterations": 1,
        "options": [],
        "inline_images": [{"url": img_url, "alt": en_prompt[:120], "model": model_used}],
        "html_updated": False,
        "tool_log": [],
        "tokens_in": 0,
        "tokens_out": 0,
        "credits_capped": False,
        "no_credits_after": False,
        "auto_republished": None,
    })


async def _fallback_fal_flux(prompt: str, size: str) -> Optional[str]:
    """Fallback to fal.ai if Emergent gen failed."""
    try:
        import httpx
        fal_key = (os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY") or "").strip()
        if not fal_key:
            return None
        aspect = "square_hd"
        if "1792x1024" in size:
            aspect = "landscape_16_9"
        elif "1024x1792" in size:
            aspect = "portrait_9_16"
        async with httpx.AsyncClient(timeout=120) as cl:
            r = await cl.post(
                "https://fal.run/fal-ai/flux/schnell",
                headers={"Authorization": f"Key {fal_key}", "Content-Type": "application/json"},
                json={"prompt": prompt, "image_size": aspect, "num_inference_steps": 4, "num_images": 1},
            )
        if r.status_code != 200:
            return None
        data = r.json()
        imgs = data.get("images") or []
        if not imgs:
            return None
        first = imgs[0]
        return first.get("url") if isinstance(first, dict) else first
    except Exception as e:
        logger.warning(f"[visual_cortex] fal fallback failed: {e}")
        return None
