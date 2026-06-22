"""Brain v2 State Machine — replaces the chaotic for-loop with a strict FSM.

The brain can only call tools allowed in its current state. This stops the
old failure mode where the AI would jump from "discovery" to "writing 30KB
of HTML" in a single turn without ever asking a question or showing a plan.
"""
from enum import Enum
from typing import Dict, List, Set


class BrainState(str, Enum):
    """Six explicit phases. Each turn the brain enters one state and may
    transition to a *strictly defined* next state."""

    # ── Discovery: ask the user 3-5 sharp questions about the project ────
    DISCOVERY = "discovery"
    # ── Planning: build a JSON plan from collected answers ───────────────
    PLANNING = "planning"
    # ── Awaiting Approval: present the plan, wait for user decision ──────
    AWAITING_APPROVAL = "awaiting_approval"
    # ── Executing: run plan steps in order, one tool call at a time ──────
    EXECUTING = "executing"
    # ── Verifying: scan output, screenshot diff, fix violations ──────────
    VERIFYING = "verifying"
    # ── Idle: between turns, awaiting next user message ──────────────────
    IDLE = "idle"


# Allowed transitions — any other transition is a programming error
ALLOWED_TRANSITIONS: Dict[BrainState, Set[BrainState]] = {
    BrainState.IDLE: {BrainState.DISCOVERY, BrainState.PLANNING, BrainState.EXECUTING},
    BrainState.DISCOVERY: {BrainState.DISCOVERY, BrainState.PLANNING, BrainState.IDLE},
    BrainState.PLANNING: {BrainState.AWAITING_APPROVAL, BrainState.DISCOVERY, BrainState.IDLE},
    BrainState.AWAITING_APPROVAL: {BrainState.EXECUTING, BrainState.PLANNING, BrainState.IDLE},
    BrainState.EXECUTING: {BrainState.VERIFYING, BrainState.EXECUTING, BrainState.IDLE},
    BrainState.VERIFYING: {BrainState.EXECUTING, BrainState.IDLE},
}


# Tools allowed in each state — strict enforcement at orchestrator level
TOOLS_BY_STATE: Dict[BrainState, Set[str]] = {
    BrainState.IDLE: set(),  # no tools — brain just received a message
    BrainState.DISCOVERY: {
        "ask_user", "request_clarification", "read_current_html",
        "search_html", "read_project_memory",
    },
    BrainState.PLANNING: {
        "read_current_html", "search_html", "read_project_memory",
        "build_plan", "present_plan",
    },
    BrainState.AWAITING_APPROVAL: {
        "present_plan", "refine_plan", "request_clarification",
    },
    BrainState.EXECUTING: {
        # Standard HTML tools (delegated to freebuild executor)
        "read_current_html", "search_html", "audit_html",
        "apply_section", "write_full_html", "remove_section",
        "update_nav", "create_page", "switch_page",
        "move_section_to_page", "keep_only_sections",
        # Power tools
        "fetch_image", "fetch_font", "self_test", "visual_snapshot",
        # Memory
        "update_project_memory",
    },
    BrainState.VERIFYING: {
        "audit_html", "visual_snapshot", "compare_design", "self_test",
        "read_current_html", "search_html",
        # The ONLY way to legitimately finish a turn:
        "complete_task",
        # Or admit failure:
        "report_failure",
    },
}


def can_transition(from_state: BrainState, to_state: BrainState) -> bool:
    """Return True if from_state may transition to to_state."""
    return to_state in ALLOWED_TRANSITIONS.get(from_state, set())


def tools_for_state(state: BrainState) -> Set[str]:
    """Return the whitelist of tool names callable in this state."""
    return TOOLS_BY_STATE.get(state, set())
