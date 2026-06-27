"""
stream_hooks.py — Pre/post-flight hooks for /agent-chat-stream.

Extracted from freebuild_chat.py (lines 8278-8444) to keep the monster file
slimmer and these hooks unit-testable in isolation. The functions here are
called ONLY from freebuild_chat.py's event_stream() in /agent-chat-stream.

Hooks provided:
  • run_classifier_fast_paths()  — Gap #1 (architect / review fast-paths)
  • spawn_brand_dna_extraction() — Gap #3 hook #1 (auto Brand-DNA on 1st msg)
  • run_auto_reviewer_on_html()  — Gap #3 hook #2 (post-flight HTML review)
"""
from __future__ import annotations

import asyncio as _asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("zenrex.stream_hooks")


# ─────────────────────────────────────────────────────────────
# Concierge precheck — Block agent invocation if 3rd-party keys
# are missing for the requested feature. Streams wizard cards.
# ─────────────────────────────────────────────────────────────
async def run_concierge_precheck(
    *,
    db: Any,
    user_id: str,
    project_id: str,
    user_message: str,
    event_queue: _asyncio.Queue,
) -> bool:
    """Return True if the build was paused (caller must stop)."""
    try:
        from .concierge_hooks import precheck_integrations, stream_wizard_as_sse
        check = await precheck_integrations(
            db=db, user_id=user_id, project_id=project_id, user_message=user_message,
        )
        if not check.get("should_block_build"):
            return False
        for evt in stream_wizard_as_sse(check):
            await event_queue.put(evt)
        pending_ids = [p["integration_id"] for p in check["pending"]]
        await event_queue.put(
            f"event: done\ndata: {json.dumps({'paused_for_setup': True, 'pending_integrations': pending_ids, 'summary': '⏸️ بانتظار إعداد المفاتيح المطلوبة. أكمل الـ Setup Wizard بالأعلى ثم سأكمل البناء فوراً.', 'credits_charged': 0, 'auto_refunded': True, 'model_used': 'concierge', 'iterations': 0, 'options': [], 'inline_images': []}, ensure_ascii=False)}\n\n"
        )
        return True
    except Exception as ce:
        logger.warning(f"[concierge_precheck] skipped: {ce}")
        return False


# ─────────────────────────────────────────────────────────────
# Gap #1 — Classifier fast-paths (architect / review)
# ─────────────────────────────────────────────────────────────
async def run_classifier_fast_paths(
    *,
    message: str,
    project: Dict[str, Any],
    event_queue: _asyncio.Queue,
    captured: Dict[str, Any],
) -> bool:
    """If the user intent is `architect` or `review` with high confidence,
    route to the specialized cortex and return True. Caller should then
    stop further processing.

    Returns False if the classifier didn't match a fast-path (normal flow
    via stream_agent_turn should continue).
    """
    try:
        from .orchestrator.classifier import classify_intent_domain
        intent = classify_intent_domain(message)
        await event_queue.put(
            f"event: classifier\ndata: {json.dumps({'primary': intent.primary, 'secondary': intent.secondary, 'confidence': intent.confidence, 'rationale': intent.rationale}, ensure_ascii=False)}\n\n"
        )
        # Architect fast-path
        if intent.primary == "architect" and intent.confidence >= 0.85:
            from .orchestrator.cortices.architect_cortex import stream_architect_cortex
            async for chunk in stream_architect_cortex(
                user_message=message,
                project=project,
                brand_dna=project.get("brand_dna"),
            ):
                await event_queue.put(chunk)
                if chunk.startswith("event: done\n"):
                    try:
                        dl = [ln for ln in chunk.split("\n") if ln.startswith("data:")][0][5:].strip()
                        done = json.loads(dl)
                        captured["summary"] = done.get("summary", "")
                        captured["model_used"] = done.get("model_used", "architect_cortex")
                        captured["iterations"] = done.get("iterations", 1)
                        captured["credits_charged"] = int(done.get("credits_charged") or 0)
                    except Exception:
                        pass
            return True
        # Review fast-path
        if intent.primary == "review" and intent.confidence >= 0.85:
            from .orchestrator.review_cortex import review_code, render_review_report_ar
            rep = review_code(message, "mixed")
            summary_ar = render_review_report_ar(rep)
            await event_queue.put(
                f"event: cortex_step\ndata: {json.dumps({'cortex': 'review', 'score': rep.get('score')}, ensure_ascii=False)}\n\n"
            )
            captured["summary"] = summary_ar
            captured["model_used"] = "static_analyzer"
            captured["iterations"] = 1
            captured["credits_charged"] = 3
            captured["review_report"] = rep
            await event_queue.put(
                f"event: done\ndata: {json.dumps({'summary': summary_ar, 'auto_refunded': False, 'credits_charged': 3, 'model_used': 'static_analyzer', 'iterations': 1, 'options': [], 'inline_images': [], 'review_report': rep}, ensure_ascii=False)}\n\n"
            )
            return True
    except Exception as ce:
        logger.exception(f"[classifier_fast_paths] failed: {ce}")
    return False


# ─────────────────────────────────────────────────────────────
# Gap #3 Hook #1 — Brand DNA auto-extraction on first message
# ─────────────────────────────────────────────────────────────
def spawn_brand_dna_extraction(
    *,
    db: Any,
    project_id: str,
    project: Dict[str, Any],
    history: List[Any],
    message: str,
    event_queue: _asyncio.Queue,
) -> None:
    """Spawn a background task that extracts brand DNA from the user's first
    message and persists it onto the project doc. Idempotent — skips if
    project.brand_dna already exists."""
    try:
        if len(history) > 1:
            return
        if (project.get("brand_dna") or {}):
            return  # already extracted

        async def _bg() -> None:
            try:
                from .orchestrator.brand_dna import extract_brand_dna
                dna = await extract_brand_dna(message)
                if not dna:
                    return
                await db.freebuild_projects.update_one(
                    {"id": project_id},
                    {"$set": {
                        "brand_dna": dna,
                        "brand_dna_extracted_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
                try:
                    await event_queue.put(
                        f"event: brand_dna_extracted\ndata: {json.dumps({'palette': dna.get('palette'), 'tone': dna.get('tone'), 'archetypes': dna.get('archetypes')}, ensure_ascii=False)}\n\n"
                    )
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"[brand_dna] bg extraction failed: {e}")

        _asyncio.create_task(_bg())
    except Exception as e:
        logger.warning(f"[brand_dna] hook setup failed: {e}")


# ─────────────────────────────────────────────────────────────
# Gap #3 Hook #2 — Auto-Reviewer after HTML changes
# ─────────────────────────────────────────────────────────────
async def run_auto_reviewer_on_html(
    *,
    done: Dict[str, Any],
    current_html: Optional[str],
    event_queue: _asyncio.Queue,
    captured: Dict[str, Any],
) -> Dict[str, Any]:
    """Called after `done` event when html_updated=True. Runs static review
    on the new HTML, emits `auto_review` SSE event with score, and appends a
    warning to done.summary if critical issues are found.

    Returns the (possibly modified) `done` dict — caller should re-serialize.
    """
    try:
        if not done.get("html_updated"):
            return done
        if not current_html or len(current_html) <= 50:
            return done
        from .orchestrator.review_cortex import review_code
        rep = review_code(current_html, "html")
        crit = [i for i in (rep.get("issues") or []) if i.get("severity") in ("critical", "high")]
        try:
            await event_queue.put(
                f"event: auto_review\ndata: {json.dumps({'score': rep.get('score'), 'passed': rep.get('passed'), 'critical_high_count': len(crit), 'total_issues': len(rep.get('issues') or [])}, ensure_ascii=False)}\n\n"
            )
        except Exception:
            pass
        captured["review_report"] = rep
        if crit:
            done["summary"] = (done.get("summary") or "") + (
                f"\n\n⚠️ **مراجعة تلقائية:** عُثر على {len(crit)} مشاكل حرجة. "
                f"الـ score: {rep.get('score')}/100. "
                "اطلب `run_reviewer` للتفاصيل."
            )
            captured["summary"] = done["summary"]
    except Exception as e:
        logger.warning(f"[auto_review] failed: {e}")
    return done
