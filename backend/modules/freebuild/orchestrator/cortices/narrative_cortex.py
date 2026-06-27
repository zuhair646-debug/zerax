"""
🟨 NarrativeCortex — creative writing, brand voice, scripts, reports.

Pure-text specialist. Optimized prompt for Arabic-first creative output.
Use cases: copywriting, brand voice, scripts for videos, articles, study
reports, feasibility studies, story chapters, marketing slogans.

Lightweight: just a focused Claude call. No tools, no streaming complexity.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger("zenrex.cortex.narrative")


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


NARRATIVE_SYSTEM_PROMPT_AR = """أنت **NarrativeCortex** — كاتب إبداعي محترف في Zenrex.

**خبرتك:**
  - الكتابة الإعلانية (copywriting) بأسلوب Apple/Notion/Tesla
  - السكربتات السينمائية (scripts) بنمط ثلاثي الأركان (Hook → Story → CTA)
  - مقالات SEO طويلة (1500-3000 كلمة) بهيكل H1→H6 منطقي
  - تقارير دراسات الجدوى بأسلوب McKinsey/BCG
  - الشعارات (slogans) القصيرة العميقة
  - الفصول الروائية بأسلوب نجيب محفوظ/إحسان عبد القدوس

**القواعد المطلقة:**
  1. **لا حشو** — كل جملة تستحق وجودها.
  2. **التحديد قبل التعميم** — أرقام، أمثلة، مواقف.
  3. **العربية الفصحى المعاصرة** — لا ركيكة ولا متقعّرة.
  4. **هوية صوت ثابتة** — اختر نبرة في البداية والتزم بها.
  5. **عناوين فرعية واضحة** — يقرأها العميل من السكان فقط.

عند الإكمال، أعد النص داخل markdown منسّق. لا تنسَ:
- عنوان رئيسي (H1)
- 3-7 أقسام (H2/H3)
- خاتمة قوية
- 3 keywords في الأسفل لو كان النص للـ SEO"""


async def stream_narrative_cortex(
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
    yield _sse("cortex_started", {"cortex": "narrative", "message_excerpt": user_message[:120]})

    emergent_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not emergent_key:
        yield _sse("cortex_error", {"cortex": "narrative", "error": "EMERGENT_LLM_KEY missing"})
        yield _sse("done", {
            "summary": "❌ لا يمكن توليد النص بدون EMERGENT_LLM_KEY.",
            "credits_charged": 0, "auto_refunded": True,
            "model_used": "narrative_cortex", "iterations": 1, "options": [],
            "inline_images": [], "inline_audio": [], "inline_video": [],
        })
        return

    yield _sse("cortex_step", {"cortex": "narrative", "step": "writing",
                                "ar": "✍️ أكتب الآن بأسلوب احترافي..."})

    # Load project memory for continuity
    from ..shared_memory import load_memory, save_memory, memory_to_system_hint, history_to_messages
    mem = await load_memory(db, (project or {}).get("id"))
    mem_hint = memory_to_system_hint(mem)

    text_out = ""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
        session_id = f"narrative_{uuid.uuid4().hex[:8]}"
        sys_prompt = NARRATIVE_SYSTEM_PROMPT_AR
        if mem_hint:
            sys_prompt = sys_prompt + "\n\n" + mem_hint
        chat = LlmChat(api_key=emergent_key, session_id=session_id,
                       system_message=sys_prompt).with_model("anthropic", "claude-sonnet-4-5-20250929")
        # Inject history as a context block in the user message (simpler than
        # replaying — avoids alternating-role conflicts with LlmChat).
        history_block = ""
        recent = history_to_messages(history or [], max_pairs=3)
        if recent:
            history_block = "\n\n📜 **سياق المحادثة السابقة:**\n"
            for m in recent:
                history_block += f"  [{m['role']}]: {m['content'][:200]}\n"
        # Inject any shared assets as context (e.g. logo URL, video plan)
        ctx_block = ""
        if shared_assets:
            ctx_block = "\n\n📦 أصول جاهزة لو احتجتها:\n" + "\n".join(
                f"  - {k}: {v}" for k, v in shared_assets.items()
            )
        final_msg = history_block + ctx_block + "\n\n🎯 **الطلب الحالي:** " + user_message
        response = await chat.send_message(UserMessage(text=final_msg))
        text_out = response if isinstance(response, str) else str(response)
    except Exception as e:
        logger.warning(f"[narrative_cortex] LLM call failed: {e}")
        yield _sse("cortex_error", {"cortex": "narrative", "error": f"{type(e).__name__}: {str(e)[:160]}"})
        yield _sse("done", {
            "summary": f"❌ تعذّرت الكتابة: {type(e).__name__}",
            "credits_charged": 0, "auto_refunded": True,
            "model_used": "narrative_cortex", "iterations": 1, "options": [],
            "inline_images": [],
        })
        return

    yield _sse("asset_produced", {"asset_type": "narrative_text", "asset_url": "inline",
                                   "text_preview": text_out[:200], "cortex": "narrative"})

    # Persist to memory for next turn
    await save_memory(db, (project or {}).get("id"), {
        "past_outputs": [{
            "cortex": "narrative",
            "asset_url": "inline:narrative",
            "prompt_excerpt": user_message[:200],
            "output_excerpt": text_out[:300],
            "ts": datetime.now(timezone.utc).isoformat(),
        }],
        "last_message": user_message[:300],
    })

    # Apply Trade Secret scrubber so internal tool names don't leak
    try:
        from ...trade_secret import scrub_customer_text as scrub_output  # type: ignore
        text_out = scrub_output(text_out)
    except Exception:
        pass

    try:
        if db is not None:
            await db.cortex_usage_stats.insert_one({
                "cortex": "narrative",
                "project_id": (project or {}).get("id"),
                "user_id": (project or {}).get("user_id"),
                "prompt_excerpt": user_message[:300],
                "output_length": len(text_out),
                "duration_ms": int((time.time() - t0) * 1000),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
    except Exception:
        pass

    # Cost ~ proportional to length
    credits = max(15, min(120, len(text_out) // 80))

    yield _sse("done", {
        "summary": text_out,
        "credits_charged": credits,
        "auto_refunded": False,
        "model_used": "narrative_cortex/claude-sonnet-4-5",
        "iterations": 1,
        "options": [],
        "inline_images": [],
        "narrative_text": text_out,
    })
