"""
Unit tests for the Honesty Wrapper + Escalation Bridge (Feb 2026).
Run: cd /app/backend && pytest tests/test_honesty_and_escalation.py -q
"""
from __future__ import annotations

import pytest

from modules.freebuild.honesty_wrapper import (
    claims_completion,
    verification_evidence,
    build_honesty_violation_nudge,
)
from modules.freebuild.escalation_bridge import should_escalate
from modules.freebuild.silent_supervisor import SupervisorState


# ─── Honesty Wrapper ─────────────────────────────────────────────────

def test_claims_completion_arabic():
    assert claims_completion("خلصت من بناء الموقع")
    assert claims_completion("الموقع جاهز للاستخدام")
    assert claims_completion("نشرت الموقع على Vercel")
    assert claims_completion("All done! Site deployed successfully.")


def test_claims_completion_negative():
    assert not claims_completion("سأبدأ ببناء الموقع الآن")
    assert not claims_completion("Let me work on this")
    assert not claims_completion("")


def test_verification_evidence_detects_test_page():
    log = [
        {"name": "write_full_html", "result": {"ok": True}},
        {"name": "test_page", "result": {"ok": True, "screenshot": "x"}},
    ]
    ev = verification_evidence(log)
    assert ev["verified"] is True
    assert "test_page" in ev["verification_tools_used"]


def test_verification_evidence_detects_successful_deploy():
    log = [
        {"name": "deploy_to_vercel", "result": {"ok": True, "url": "https://x.vercel.app", "provider": "vercel"}},
    ]
    ev = verification_evidence(log)
    assert ev["verified"] is True
    assert ev["deploys_succeeded"][0]["url"] == "https://x.vercel.app"


def test_verification_evidence_unverified_when_no_test():
    log = [
        {"name": "write_full_html", "result": {"ok": True}},
        {"name": "apply_section", "result": {"ok": True}},
    ]
    ev = verification_evidence(log)
    assert ev["verified"] is False
    assert ev["verification_tools_used"] == []
    assert ev["deploys_succeeded"] == []


def test_failed_deploy_does_not_count_as_verification():
    log = [
        {"name": "deploy_to_vercel", "result": {"ok": False, "error": "invalid token"}},
    ]
    ev = verification_evidence(log)
    assert ev["verified"] is False


def test_nudge_contains_actionable_tools():
    msg = build_honesty_violation_nudge("الموقع جاهز", {"verified": False})
    assert "test_page" in msg
    assert "verify_my_work" in msg
    assert "publish_site" in msg


# ─── Escalation Bridge — decision logic ──────────────────────────────

def test_no_escalation_for_healthy_session():
    s = SupervisorState()
    assert should_escalate(supervisor_state=s, honesty_violation=False) is None


def test_honesty_violation_escalates_low_severity():
    s = SupervisorState()
    esc = should_escalate(supervisor_state=s, honesty_violation=True)
    assert esc is not None
    assert esc["reason"] == "honesty_violation"
    assert esc["severity"] == "low"


def test_thrashing_escalates_with_increasing_severity():
    s = SupervisorState()
    s.intervention_count_total = 3
    esc = should_escalate(supervisor_state=s, honesty_violation=False)
    assert esc["reason"] == "supervisor_thrashing"
    assert esc["severity"] == "medium"
    s.intervention_count_total = 5
    esc2 = should_escalate(supervisor_state=s, honesty_violation=False)
    assert esc2["severity"] == "high"


def test_giveup_escalates_high():
    s = SupervisorState()
    esc = should_escalate(
        supervisor_state=s,
        honesty_violation=False,
        last_pattern={"pattern": "assistant_gave_up"},
    )
    assert esc["reason"] == "assistant_gave_up"
    assert esc["severity"] == "high"
