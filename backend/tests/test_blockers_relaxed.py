"""
Tests verifying ALL Python-level guardrails have been removed per user request.

User: "احذف لكل شيء فيه موانع. الحفاظ على الادوات فقط والحفاظ على الذكاء
الصناعي فقط. من غير اي قواعد."

Translation: Remove every blocker. Keep only the tools and the AI's
intelligence. No rules at all.

What remains:
  • Tool argument validation in the dispatcher (id required, html required,
    page must exist, etc.) — this is a tool contract, not a flow rule.
  • The system prompt (workflow_engine phase banner: Discovery → Skeleton
    → Wiring → Surgical) — pure guidance, no Python enforcement.

What is gone:
  • PRE-FINISH GATE
  • LYING GUARD
  • Stall-recovery / FAKE-ACHIEVEMENT / FALSE-FAILURE detectors
  • Preemptive force_tool_use (action-intent forcing)
  • Post-write force_tool_use on duplicate IDs
  • Post-turn placeholder audit warning (`_pending_audit_warning`)
  • Anti-Hallucination Lie Detector (post-turn)
  • `_pending_audit_warning` re-injection on the next turn
  • DESIGN-DESTRUCTION GUARD / SURGICAL-EDIT GUARD / SURGICAL-HARDBLOCK
    (already advisories from the previous iteration)
  • DESIGN_LOCKED / DESIGN_PRESERVATION hard blocks
"""
import inspect

from backend.modules.freebuild import freebuild_agent as fa


def _src() -> str:
    return inspect.getsource(fa)


class TestAllBlockersRemoved:
    def test_pre_finish_gate_removed(self):
        src = _src()
        assert "PRE-FINISH GATE — رفض إنهاء المهمة" not in src
        assert "pre_finish_gate_block" not in src

    def test_lying_guard_removed(self):
        src = _src()
        assert "lying_guard" not in src
        assert "ادّعيت إتمام التغيير لكن" not in src

    def test_stall_recovery_removed(self):
        src = _src()
        assert "stall_recovery_used" not in src
        assert "FAKE-achievement" not in src
        assert "FALSE-failure" not in src
        assert "FAKE_ACHIEVEMENT_MARKERS" not in src
        assert "FALSE_FAILURE_MARKERS" not in src

    def test_preemptive_force_removed(self):
        src = _src()
        assert "PREEMPTIVE force_tool_use" not in src
        assert "PREEMPTIVE FORCING for action intents" not in src

    def test_post_turn_audit_removed(self):
        src = _src()
        # Old audit-guard persist line must be gone
        assert '"_pending_audit_warning": audit_warning_text' not in src
        # `audit_warning_text` variable must no longer exist
        assert "audit_warning_text = None" not in src

    def test_anti_hallucination_lie_detector_removed(self):
        src = _src()
        assert "Anti-Hallucination Lie Detector" not in src
        assert "SYSTEM LIE DETECTOR" not in src
        assert "lie_warning = " not in src

    def test_pending_audit_injection_removed(self):
        src = _src()
        # The pending_audit_prefix construction on the next turn must be gone
        assert "pending_audit_prefix" not in src
        assert 'project.get("_pending_audit_warning")' not in src

    def test_design_destruction_hard_block_removed(self):
        src = _src()
        assert "DESIGN-DESTRUCTION GUARD: تحاول" not in src
        assert "design_destruction_guard_block" not in src

    def test_design_locked_hard_block_removed(self):
        src = _src()
        assert '"error": "DESIGN_LOCKED"' not in src
        assert '"error": "DESIGN_PRESERVATION"' not in src


class TestToolContractsPreserved:
    """Tool argument validation is the only remaining check. Not a blocker —
    it just tells the AI when its call is malformed."""

    def test_apply_section_validates_id(self):
        src = _src()
        assert '"id is required"' in src

    def test_create_page_validates_filename(self):
        src = _src()
        assert "filename must end with .html" in src

    def test_write_full_html_validates_html(self):
        src = _src()
        assert '"html cannot be empty"' in src
