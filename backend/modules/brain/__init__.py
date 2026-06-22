"""Zenrex Brain v2 — Unified intelligent agent for all platform sections.

Public API:
    from modules.brain import BrainOrchestrator, BrainConfig

The Brain is designed to be section-agnostic: FreeBuild, Maker, Studio, and
future modules all import BrainOrchestrator and pass their domain-specific
tool catalog. The Brain handles:
  • Discovery (questions before action)
  • Planning (plan-then-approve contract)
  • Execution (strict state machine, no for-loop chaos)
  • Verification (visual diff + design lock)
  • Memory (per-project persistent context)
  • Strict completion (no "تم بنجاح" text — only complete_task tool)
"""
from .core import BrainOrchestrator, BrainConfig
from .states import BrainState
from .memory import ProjectMemory

__all__ = ["BrainOrchestrator", "BrainConfig", "BrainState", "ProjectMemory"]
