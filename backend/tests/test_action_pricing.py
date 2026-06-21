"""
Tests for Action-Based Pricing (intent classification + pre-flight gate +
per-op floor enforcement).
"""
from __future__ import annotations
import sys, os
import pytest
sys.path.insert(0, "/app/backend")

from modules.freebuild.action_pricing import (
    classify_intent,
    estimate_min_cost,
    preflight_check,
    compute_op_floor,
    ACTION_COSTS,
)


# ─── Intent classification ──────────────────────────────────────────────────
@pytest.mark.parametrize("msg, expected", [
    # full site
    ("ابني لي موقع كامل لمطعمي", "full_site"),
    ("build me a complete website", "full_site"),
    # page creation
    ("أنشئ صفحة جديدة باسم about.html", "page_creation"),
    ("اصنع صفحة منفصلة للتواصل", "page_creation"),
    ("create a new page for services", "page_creation"),
    # deletion
    ("احذف قسم testimonials", "deletion"),
    ("شيل لي القسم الفارغ", "deletion"),
    ("remove the stats section", "deletion"),
    # repair
    ("الزر ما يشتغل، أصلحه", "repair"),
    ("fix the broken navigation", "repair"),
    # section_add (after deletion to test priority)
    ("أضف قسم hero جديد", "section_add"),
    ("ضيف لي قسم آراء العملاء", "section_add"),
    ("add a new section for pricing", "section_add"),
    # edit
    ("غيّر اللون إلى الأزرق", "edit"),
    ("بدّل الخط في قسم hero", "edit"),
    # inspection
    ("اعرض لي قائمة الأقسام", "inspection"),
    ("list all pages", "inspection"),
    # chat (fallback)
    ("شكراً، الموقع جميل", "chat"),
    ("ما رأيك بالألوان؟", "chat"),
])
def test_intent_classification(msg, expected):
    assert classify_intent(msg) == expected, f"'{msg}' should classify as {expected}"


def test_estimate_min_cost_matches_catalog():
    for intent, (mn, _mx, _) in ACTION_COSTS.items():
        assert estimate_min_cost(intent) == mn


# ─── Pre-flight check ───────────────────────────────────────────────────────
def test_preflight_allows_when_sufficient():
    res = preflight_check(balance=1000, message="أضف قسم hero جديد")
    assert res["allowed"] is True
    assert res["intent"] == "section_add"
    assert res["min_cost"] == 120
    assert res["preview_recommended"] is True   # max=350 ≥ 200


def test_preflight_blocks_when_insufficient():
    res = preflight_check(balance=50, message="أنشئ صفحة منفصلة باسم about.html")
    assert res["allowed"] is False
    assert res["intent"] == "page_creation"
    assert res["min_cost"] == 200
    assert res["needed"] == 150
    assert "Indie" in res["recommended_plan"]
    assert res["recharge_url"] == "/billing"
    assert "اشحن" in res["message"]


def test_preflight_chat_low_threshold():
    """Casual questions only need 25 credits — most users should clear."""
    res = preflight_check(balance=30, message="شكراً")
    assert res["allowed"] is True
    assert res["intent"] == "chat"


def test_preflight_zero_balance_blocks_everything():
    res = preflight_check(balance=0, message="أي رسالة")
    assert res["allowed"] is False
    assert res["balance"] == 0


# ─── Op-Floor enforcement ──────────────────────────────────────────────────
def test_op_floor_picks_max_of_seen_tools():
    tool_log = [
        {"name": "read_current_html"},     # 5 floor
        {"name": "apply_section"},          # 80 floor
        {"name": "create_page"},            # 200 floor
        {"name": "audit_html"},             # 15 floor
    ]
    assert compute_op_floor(tool_log) == 200


def test_op_floor_returns_zero_for_empty_log():
    assert compute_op_floor([]) == 0
    assert compute_op_floor(None) == 0


def test_op_floor_handles_unknown_tools():
    tool_log = [{"name": "unknown_tool"}, {"name": "apply_section"}]
    assert compute_op_floor(tool_log) == 80   # ignores unknown, uses apply_section


def test_pre_flight_preview_threshold_at_200():
    # chat max = 80, no preview
    assert preflight_check(1000, "hello")["preview_recommended"] is False
    # page_creation max = 500, preview yes
    assert preflight_check(1000, "أنشئ صفحة about")["preview_recommended"] is True
    # full_site max = 800, preview yes
    assert preflight_check(1000, "ابني لي موقع كامل")["preview_recommended"] is True
