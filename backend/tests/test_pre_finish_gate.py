"""PRE-FINISH GATE was removed per user request.

The user explicitly asked to strip every Python-level guardrail
("احذف كل الموانع. الحفاظ على الأدوات فقط والذكاء الصناعي فقط.").
The gate no longer exists in production; this file documents that removal
and verifies the marker is in source.
"""


def test_pre_finish_gate_marker_records_removal():
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    assert "PRE-FINISH GATE removed per user request" in src


def test_pre_finish_gate_blocking_logic_absent():
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    # The old block label that drove the rejection must NOT exist anywhere.
    assert "PRE-FINISH GATE — رفض إنهاء المهمة" not in src
    assert "pre_finish_gate_block" not in src
