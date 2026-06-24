"""
Tests verifying over-strict guardrails have been relaxed to advisories.

User complaint: AI was refusing to build because internal "blockers" rejected
legitimate tool calls (DESIGN-DESTRUCTION GUARD, SURGICAL-EDIT GUARD,
SURGICAL-HARDBLOCK, DESIGN_PRESERVATION). These have been converted to
log-only advisories. The AI is no longer prevented from executing its tools.

Essential rules KEPT (per user request "leave some basic rules"):
  • BLANK PAGE DETECTOR  — warning text injected to AI to fill empty pages.
  • PRE-FINISH GATE      — `finish` rejected when pages are blank.
  • LYING GUARD          — AI must call a tool when user requests action.
"""
import inspect

from backend.modules.freebuild import freebuild_agent as fa


def _src() -> str:
    return inspect.getsource(fa)


class TestBlockersRelaxed:
    def test_design_destruction_is_advisory(self):
        src = _src()
        assert "DESIGN-DESTRUCTION ADVISORY" in src
        # Old hard-block string must be gone
        assert "DESIGN-DESTRUCTION GUARD: تحاول" not in src

    def test_surgical_guard_is_advisory(self):
        src = _src()
        assert "surgical_guard_advisory" in src
        assert "SURGICAL-EDIT GUARD: العميل طلب" not in src

    def test_surgical_hardblock_removed(self):
        src = _src()
        assert "SURGICAL-HARDBLOCK removed" in src
        # The old log message that signalled toolset removal must be gone
        assert "SURGICAL-HARDBLOCK: write_full_html removed from toolset" not in src

    def test_design_preservation_is_advisory(self):
        src = _src()
        # New advisory log line
        assert "overwriting existing design" in src
        # Old hard-block error code and suggestion key must be gone
        assert '"error": "DESIGN_PRESERVATION"' not in src
        assert "use_apply_section_instead" not in src

    def test_design_locked_is_advisory(self):
        src = _src()
        assert "design_locked=True — proceeding anyway" in src
        # Old hard-block return body must be gone
        assert '"error": "DESIGN_LOCKED"' not in src


class TestEssentialRulesPreserved:
    def test_blank_page_detector_kept(self):
        src = _src()
        assert "BLANK PAGE DETECTOR" in src

    def test_pre_finish_gate_kept(self):
        src = _src()
        assert "PRE-FINISH GATE" in src
        assert "pre_finish_gate_block" in src

    def test_lying_guard_kept(self):
        src = _src()
        assert "lying_guard" in src
