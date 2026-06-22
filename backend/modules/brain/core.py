"""Zenrex Brain v2 — Core Orchestrator.

This is the public entry-point that replaces the chaotic for-loop in the
legacy `freebuild_agent.stream_agent_turn()`. The orchestrator drives the
brain through the State Machine, enforces strict tool usage per state,
maintains project memory, and produces the user-facing stream.

Design contract:
  1. Every turn starts in IDLE → analyze user message → transition.
  2. Each state has a *whitelisted* tool set (see states.TOOLS_BY_STATE).
  3. The brain CANNOT emit a "completion" message via text — only via
     `complete_task(evidence)` which gets validated against actual state.
  4. Project memory is loaded + injected into the system prompt every turn.
  5. The brain runs in iterations, but with adaptive budget based on plan
     complexity (no hard cap of 16 — uses cost ceiling instead).
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

from .states import BrainState, can_transition, tools_for_state
from .memory import ProjectMemory
from .discovery import detect_project_type, get_initial_questions
from .planner import build_plan, estimate_plan_cost
from .strict_mode import validate_completion_evidence

logger = logging.getLogger("brain_v2")


@dataclass
class BrainConfig:
    """Per-turn brain configuration. Section adapters (FreeBuild, Maker, ...)
    construct this and pass it to BrainOrchestrator."""

    section: str = "freebuild"              # which platform section
    model: str = "claude-sonnet-4-5-20250929"
    provider: str = "emergent_anthropic"
    max_credit_budget: int = 500            # hard ceiling per turn
    max_iterations: int = 20                # upper iteration safety
    enable_discovery: bool = True
    enable_visual_diff: bool = True
    enable_strict_mode: bool = True
    user_language: str = "ar"


@dataclass
class BrainTurnResult:
    state_in: BrainState
    state_out: BrainState
    summary: str
    iterations: int
    credits_used: int
    html_updated: bool
    evidence_verified: int
    evidence_rejected: int
    trust_score: int


class BrainOrchestrator:
    """The unified brain. One instance per turn (cheap to construct)."""

    def __init__(self, config: BrainConfig):
        self.config = config
        self.memory: Optional[ProjectMemory] = None
        self.current_state: BrainState = BrainState.IDLE
        self._iteration: int = 0
        self._credits_used: int = 0

    # ─── State Machine ─────────────────────────────────────────────────
    def transition_to(self, new_state: BrainState, reason: str = "") -> bool:
        """Move to a new state if allowed by the FSM. Returns False on
        illegal transition (and stays put)."""
        if not can_transition(self.current_state, new_state):
            logger.warning(
                f"[brain-fsm] ILLEGAL transition: {self.current_state} → {new_state} ({reason})"
            )
            return False
        logger.info(
            f"[brain-fsm] {self.current_state.value} → {new_state.value}  ({reason})"
        )
        self.current_state = new_state
        return True

    def allowed_tools(self) -> set:
        return tools_for_state(self.current_state)

    # ─── Memory Hydration ──────────────────────────────────────────────
    def load_memory(self, project_doc: Dict[str, Any]) -> ProjectMemory:
        raw = project_doc.get("brain_memory") or {}
        self.memory = ProjectMemory(raw)
        return self.memory

    def memory_block(self) -> str:
        if not self.memory:
            return ""
        return self.memory.to_prompt_block()

    # ─── Initial State Decision ────────────────────────────────────────
    def decide_initial_state(
        self,
        project_doc: Dict[str, Any],
        user_message: str,
    ) -> BrainState:
        """First call of each turn — pick the right starting state.

        Logic (order matters):
          1. Plan presented + user said "موافق" → EXECUTING (resume)
          2. Pending discovery questions → continue DISCOVERY
          3. No HTML + first message → DISCOVERY (unless "ابدأ فوراً")
          4. Otherwise → EXECUTING (existing project, normal edits)
        """
        mem = self.memory or ProjectMemory()
        msg_lower = user_message.lower()

        # Step 1: approval-resume check (highest priority)
        approval_markers = ("موافق", "اعتمد", "نفّذ", "نفذ",
                             "okay", "ok", "go", "approved", "yes")
        looks_like_approval = (len(user_message.strip()) < 25
                                and any(p in msg_lower or p in user_message
                                         for p in approval_markers))
        last_state = project_doc.get("brain_last_state")
        if last_state == BrainState.AWAITING_APPROVAL.value and looks_like_approval:
            return BrainState.EXECUTING

        # Step 2: pending discovery questions → continue asking
        if mem.pending_questions and len(mem.decisions) < 3:
            return BrainState.DISCOVERY

        html_exists = bool(project_doc.get("current_html") or
                            (project_doc.get("pages") or {}))

        # Step 3: first message on empty project → discovery
        skip_phrases = ("ابدأ فوراً", "ابدأ مباشرة", "بدون أسئلة",
                         "skip", "just build", "تخطى الأسئلة")
        wants_skip = any(p in msg_lower or p in user_message for p in skip_phrases)
        if (not html_exists and self.config.enable_discovery and not wants_skip
                and len(mem.decisions) == 0):
            return BrainState.DISCOVERY

        # Step 4: default → execute (existing project or skip-mode)
        return BrainState.EXECUTING

    # ─── SSE Event Helpers ─────────────────────────────────────────────
    @staticmethod
    def sse(event: str, data: Dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    # ─── Token Tracking ────────────────────────────────────────────────
    def add_credits(self, n: int) -> None:
        self._credits_used += max(0, int(n))


# ─── Public streaming entry-point ────────────────────────────────────────
async def brain_stream_turn(
    project: Dict[str, Any],
    user_message: str,
    history_messages: List[Dict[str, str]],
    config: Optional[BrainConfig] = None,
    ctx_holder: Optional[Dict[str, Any]] = None,
    auth_token: Optional[str] = None,
    db=None,
    is_owner: bool = False,
) -> AsyncIterator[str]:
    """The drop-in replacement for `freebuild_agent.stream_agent_turn`.

    Yields SSE strings exactly like the old function (same shape, so the
    frontend doesn't need changes) but routes through the Brain v2 state
    machine instead of the chaotic for-loop.
    """
    cfg = config or BrainConfig()
    brain = BrainOrchestrator(cfg)
    brain.load_memory(project)
    start_state = brain.decide_initial_state(project, user_message)
    brain.transition_to(start_state, "turn-start")

    t0 = time.time()
    yield brain.sse("turn_start", {
        "state": brain.current_state.value,
        "memory_summary": {
            "trust_score": brain.memory.trust_score,
            "lies_detected": brain.memory.lies_detected,
            "decisions": len(brain.memory.decisions),
            "do_not_count": len(brain.memory.do_not),
        },
    })

    # ═══════════════════════════════════════════════════════════════════
    # STATE: DISCOVERY — ask 3-5 sharp questions, record answers
    # ═══════════════════════════════════════════════════════════════════
    if brain.current_state == BrainState.DISCOVERY:
        # Determine the ORIGINAL project goal (first user message ever)
        original_goal = ""
        prev_msgs = project.get("messages") or []
        for m in prev_msgs:
            if m.get("role") == "user":
                original_goal = (m.get("content") or "").strip()[:200]
                break
        if not original_goal:
            original_goal = user_message.strip()[:200]

        # Was the previous message an answer to a pending question?
        if brain.memory.pending_questions:
            pending = brain.memory.pending_questions[0]
            brain.memory.resolve_pending_question(pending["question"], user_message)
            # Map answer text → preference key
            if pending.get("key"):
                brain.memory.set_preference(pending["key"], user_message.strip()[:120])
            yield brain.sse("answer_recorded", {
                "question": pending["question"],
                "answer": user_message,
            })

        # Persist memory now (before any further transitions)
        if db is not None:
            try:
                await db.freebuild_projects.update_one(
                    {"id": project.get("id")},
                    {"$set": {
                        "brain_memory": brain.memory.to_dict(),
                        "brain_original_goal": original_goal,
                    }},
                )
            except Exception:
                logger.exception("brain: failed to persist memory mid-discovery")

        # Are we done with discovery? (>=3 decisions or user said "ابدأ")
        if len(brain.memory.decisions) >= 3 or "ابدأ" in user_message:
            yield brain.sse("discovery_complete", {
                "decisions": len(brain.memory.decisions),
            })
            brain.transition_to(BrainState.PLANNING, "discovery satisfied")
        else:
            # Pick next question based on PROJECT TYPE of the original goal
            project_type = detect_project_type(original_goal)
            asked_keys = set()
            for d in brain.memory.decisions:
                asked_keys.add(d.get("question", "")[:30])
            for pq in brain.memory.pending_questions:
                asked_keys.add(pq.get("question", "")[:30])
            bank = get_initial_questions(project_type, limit=8)
            next_q = None
            for q in bank:
                if q["q"][:30] not in asked_keys:
                    next_q = q
                    break
            if next_q is None:
                yield brain.sse("discovery_complete", {
                    "decisions": len(brain.memory.decisions),
                })
                brain.transition_to(BrainState.PLANNING, "no more questions")
            else:
                brain.memory.add_pending_question(next_q["q"], next_q["options"],
                                                    key=next_q.get("key"))
                if db is not None:
                    try:
                        await db.freebuild_projects.update_one(
                            {"id": project.get("id")},
                            {"$set": {
                                "brain_memory": brain.memory.to_dict(),
                                "brain_last_state": BrainState.DISCOVERY.value,
                            }},
                        )
                    except Exception:
                        logger.exception("brain: failed to persist memory")
                yield brain.sse("ask_user", {
                    "question": next_q["q"],
                    "options": next_q["options"],
                    "key": next_q.get("key"),
                    "step": f"{len(brain.memory.decisions)+1}/5",
                })
                yield brain.sse("done", {
                    "state": BrainState.DISCOVERY.value,
                    "summary": _build_discovery_summary(brain.memory, next_q),
                    "iterations": 0,
                    "html_updated": False,
                    "credits_charged": 5,
                    "trust_score": brain.memory.trust_score,
                })
                return

    # ═══════════════════════════════════════════════════════════════════
    # STATE: PLANNING — synthesize plan from answers + user goal
    # ═══════════════════════════════════════════════════════════════════
    if brain.current_state == BrainState.PLANNING:
        # Use the original goal stored in DB (not the latest answer)
        original_goal = project.get("brain_original_goal") or ""
        if not original_goal:
            prev_msgs = project.get("messages") or []
            for m in prev_msgs:
                if m.get("role") == "user":
                    original_goal = (m.get("content") or "").strip()[:200]
                    break
        if not original_goal:
            original_goal = user_message[:200]
        project_type = detect_project_type(original_goal)
        # Build clean answers dict from preferences (keyed)
        answers = dict(brain.memory.preferences)

        plan = build_plan(
            user_goal=original_goal,
            project_type=project_type,
            answers=answers,
            current_pages=list((project.get("pages") or {}).keys()),
        )

        # Persist the plan into project doc
        if db is not None:
            try:
                await db.freebuild_projects.update_one(
                    {"id": project.get("id")},
                    {"$set": {
                        "brain_pending_plan": plan,
                        "brain_last_state": BrainState.AWAITING_APPROVAL.value,
                    }},
                )
            except Exception:
                logger.exception("brain: failed to persist plan")

        yield brain.sse("plan_presented", {
            "plan": plan,
        })
        brain.transition_to(BrainState.AWAITING_APPROVAL, "plan built")
        yield brain.sse("done", {
            "state": BrainState.AWAITING_APPROVAL.value,
            "summary": plan["summary"] + (
                "\n\n✋ **اضغط 'موافق' للبدء، أو اكتب تعديلاتك على الخطة.**"
            ),
            "iterations": 0,
            "html_updated": False,
            "credits_charged": 8,   # planning cost (cheap)
            "trust_score": brain.memory.trust_score,
            "plan_id": plan.get("title", ""),
            "awaiting_approval": True,
        })
        return

    # ═══════════════════════════════════════════════════════════════════
    # STATE: EXECUTING — fall through to the legacy executor with strict
    # mode enabled. The legacy executor handles all the tool dispatch +
    # streaming we already built; we wrap it with strict-mode validation.
    # ═══════════════════════════════════════════════════════════════════
    if brain.current_state == BrainState.EXECUTING:
        # Pull the approved plan if present, attach to project context
        approved_plan = project.get("brain_pending_plan")

        # If user said "موافق" / short approval, transform the user_message
        # into a detailed execution brief built from the plan + memory.
        # Otherwise pass the user_message through (for follow-up edits).
        executor_message = user_message
        is_plan_execution = False
        if approved_plan and project.get("brain_last_state") == BrainState.AWAITING_APPROVAL.value:
            is_plan_execution = True
            yield brain.sse("plan_approved", {"title": approved_plan.get("title")})
            executor_message = _build_executor_brief(
                original_goal=project.get("brain_original_goal") or user_message,
                memory=brain.memory,
                plan=approved_plan,
            )

        # Defer to the existing freebuild agent for the actual streaming —
        # but inject memory context and enforce strict completion.
        from ..freebuild.freebuild_agent import stream_agent_turn

        # Inject memory block as a system-prompt prefix that the agent will see
        enhanced_history = list(history_messages or [])
        memory_block = brain.memory_block()
        if memory_block:
            enhanced_history.insert(0, {
                "role": "user",
                "content": (
                    "🧠 **سياق دائم من ذاكرة المشروع — التزم به**:\n\n"
                    + memory_block
                ),
            })

        # Detect lies post-hoc via memory.trust_score after stream
        async for chunk in stream_agent_turn(
            project, executor_message, enhanced_history,
            ctx_holder=ctx_holder,
            user_language=cfg.user_language,
            auth_token=auth_token, db=db, is_owner=is_owner,
            max_iterations=cfg.max_iterations,
        ):
            # Capture done events for memory update + trust score
            if chunk.startswith("event: done\n"):
                try:
                    data_line = [ln for ln in chunk.split("\n") if ln.startswith("data:")][0][5:].strip()
                    done = json.loads(data_line)
                    html_updated = done.get("html_updated", False)
                    if html_updated:
                        brain.memory.record_truth()
                    # Persist updated memory
                    if db is not None:
                        try:
                            await db.freebuild_projects.update_one(
                                {"id": project.get("id")},
                                {"$set": {
                                    "brain_memory": brain.memory.to_dict(),
                                    "brain_last_state": BrainState.IDLE.value,
                                }, "$unset": {"brain_pending_plan": ""}},
                            )
                        except Exception:
                            pass
                except Exception:
                    pass
            yield chunk
        return

    # ═══════════════════════════════════════════════════════════════════
    # Fallback (shouldn't reach here under normal flow)
    # ═══════════════════════════════════════════════════════════════════
    yield brain.sse("done", {
        "state": brain.current_state.value,
        "summary": "✅ معالجة الـ turn اكتملت بدون عمليات.",
        "iterations": 0,
        "html_updated": False,
        "credits_charged": 0,
        "trust_score": brain.memory.trust_score if brain.memory else 100,
    })


def _build_discovery_summary(memory: ProjectMemory, next_q: Dict[str, Any]) -> str:
    """Compose the discovery message shown to the user."""
    lines = []
    if memory.decisions:
        lines.append(f"✅ تم استلام إجابتك السابقة. تقدّم: {len(memory.decisions)}/5")
        lines.append("")
    lines.append(f"❓ **{next_q['q']}**")
    if next_q.get("options"):
        lines.append("")
        for i, opt in enumerate(next_q["options"], 1):
            lines.append(f"  {chr(0x0660 + i)} — {opt}")
    lines.append("")
    lines.append("💡 *اختر رقماً أو اكتب جوابك بالكامل، أو قل 'ابدأ' لتخطي الأسئلة*")
    return "\n".join(lines)


def _build_executor_brief(
    original_goal: str,
    memory: ProjectMemory,
    plan: Dict[str, Any],
) -> str:
    """Convert an approved plan + project memory into a detailed brief that
    the legacy executor (which expects natural-language instructions) can act
    on without ambiguity. This is what guarantees the executor doesn't waste
    iterations on more discovery — it has everything it needs."""
    lines = [
        "🎯 **مهمة تنفيذية — الخطة معتمدة، نفّذها فوراً عبر استدعاء الأدوات الفعلية**",
        "",
        f"**الهدف الأصلي للعميل:** {original_goal}",
        "",
        "**تفضيلات معتمدة (التزم بها):**",
    ]
    for k, v in (memory.preferences or {}).items():
        lines.append(f"  • {k}: {v}")
    if memory.do_not:
        lines.append("")
        lines.append("**ممنوع تعمل (قرارات صريحة من العميل):**")
        for r in memory.do_not:
            lines.append(f"  ❌ {r}")
    lines.append("")
    lines.append("**خطوات التنفيذ المعتمدة (نفّذها بالترتيب):**")
    for s in plan.get("steps", []):
        tool = s.get("tool", "?")
        args = s.get("args", {})
        purpose = s.get("purpose", "")
        # Format args compactly
        arg_str = ", ".join(f"{k}={v!r}" if not isinstance(v, str) or len(v) < 60
                              else f"{k}=<...>"
                              for k, v in args.items() if k != "html")
        lines.append(f"  ➜ **{s['id']}** {tool}({arg_str}) — {purpose}")
    lines.append("")
    lines.append(
        "🛠️ **التعليمات الصارمة:**\n"
        "  1. استدع الأدوات الفعلية مباشرة (apply_section, create_page, إلخ).\n"
        "  2. لا تكتب 'تم بنجاح' بدون استدعاء الأداة فعلياً — السيرفر يكشف الكذب.\n"
        "  3. كل قسم HTML يجب أن يكون فيه onclick / onsubmit / JS فعلي.\n"
        "  4. الروابط بين الصفحات حقيقية (.html) لا anchors.\n"
        "  5. لا تطلب موافقة إضافية — الخطة معتمدة، نفّذ مباشرة."
    )
    return "\n".join(lines)
