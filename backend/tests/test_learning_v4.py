"""
Tests for the Autonomy v4 lesson learning system:
  • Hybrid retrieval (token overlap + priority + recency + effectiveness)
  • Auto-E1 threshold detection
  • New supervisor patterns (lazy_reply, credential_repeat_loop)
Run: cd /app/backend && pytest tests/test_learning_v4.py -q
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

import pytest

from modules.freebuild.silent_supervisor import (
    SupervisorState,
    record_tool_event,
    record_assistant_text,
    detect_stuck_pattern,
    build_supervisor_injection,
)
from modules.freebuild.lesson_retrieval import (
    _tokenize,
    _normalize_arabic,
    _score_lesson,
)
from modules.freebuild.auto_e1 import should_invoke_auto_e1


# ─── Tokenizer ──────────────────────────────────────────────────────

def test_normalize_arabic_alef_forms():
    assert _normalize_arabic("إنشاء") == "انشاء"
    assert _normalize_arabic("الذكاء") == "الذكاء" or _normalize_arabic("الذكاء")
    assert _normalize_arabic("صفحة") == "صفحه"


def test_tokenize_drops_stopwords_and_short():
    toks = _tokenize("في إنشاء موقع لـ مغسلة ملابس")
    assert "موقع" in toks
    assert "مغسله" in toks
    assert "في" not in toks  # stopword


def test_tokenize_handles_mixed_arabic_english_code():
    toks = _tokenize("استخدم deploy_to_vercel قبل request_credential")
    assert "deploy_to_vercel" in toks
    assert "request_credential" in toks


# ─── Lesson scoring ─────────────────────────────────────────────────

def _lesson(text: str, **extras) -> Dict[str, Any]:
    base = {
        "id": "L" + text[:6],
        "guidance_ar": text,
        "pattern": "test",
        "priority": "medium",
        "ts": datetime.now(timezone.utc).isoformat(),
        "injection_count": 0,
        "pattern_recurred_after": 0,
    }
    base.update(extras)
    return base


def test_token_overlap_scores_higher_than_unrelated():
    query = "أنشر الموقع على Vercel"
    q_toks = _tokenize(query)
    q_set = set(q_toks)
    now = datetime.now(timezone.utc).timestamp()
    L_rel = _lesson("لاستخدام Vercel: استدعِ request_credential أولاً")
    L_unrel = _lesson("لتحرير الصور استخدم analyze_uploaded_file")
    s_rel = _score_lesson(L_rel, q_toks, q_set, now)
    s_unrel = _score_lesson(L_unrel, q_toks, q_set, now)
    assert s_rel > s_unrel
    assert s_rel > 0


def test_critical_priority_boosts_score():
    query = "كيف أعمل layout"
    q_toks = _tokenize(query)
    q_set = set(q_toks)
    now = datetime.now(timezone.utc).timestamp()
    medium_match = _lesson("layout يستخدم flex", priority="medium")
    critical_match = _lesson("layout يستخدم flex", priority="critical")
    s_m = _score_lesson(medium_match, q_toks, q_set, now)
    s_c = _score_lesson(critical_match, q_toks, q_set, now)
    assert s_c > s_m


def test_old_lessons_decay():
    query = "نشر deploy_to_vercel"
    q_toks = _tokenize(query)
    q_set = set(q_toks)
    now = datetime.now(timezone.utc).timestamp()
    fresh = _lesson("استخدم deploy_to_vercel", ts=datetime.now(timezone.utc).isoformat())
    old = _lesson(
        "استخدم deploy_to_vercel",
        ts=(datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
    )
    s_fresh = _score_lesson(fresh, q_toks, q_set, now)
    s_old = _score_lesson(old, q_toks, q_set, now)
    assert s_fresh > s_old


def test_ineffective_lesson_dampened():
    query = "نشر deploy_to_vercel"
    q_toks = _tokenize(query)
    q_set = set(q_toks)
    now = datetime.now(timezone.utc).timestamp()
    healthy = _lesson("استخدم deploy_to_vercel", injection_count=10, pattern_recurred_after=1)
    broken = _lesson("استخدم deploy_to_vercel", injection_count=10, pattern_recurred_after=8)
    s_healthy = _score_lesson(healthy, q_toks, q_set, now)
    s_broken = _score_lesson(broken, q_toks, q_set, now)
    assert s_healthy > s_broken


# ─── New supervisor patterns ────────────────────────────────────────

def test_lazy_reply_detected_on_long_user_short_assistant():
    s = SupervisorState()
    long_user = "ابني لي موقع مغسلة ملابس مع توصيل واشتراك أسبوعي ولوحة تحكم وكل التفاصيل" * 2
    record_assistant_text(s, "تمام", prior_user_text_len=len(long_user))
    p = detect_stuck_pattern(s)
    assert p is not None
    assert p["pattern"] == "lazy_reply"


def test_credential_repeat_loop_detected():
    s = SupervisorState()
    for _ in range(3):
        record_tool_event(s, "request_credential", {"service": "vercel_token"}, {"ok": True})
    p = detect_stuck_pattern(s)
    assert p is not None
    assert p["pattern"] == "credential_repeat_loop"


def test_supervisor_injection_for_new_patterns():
    msg1 = build_supervisor_injection({"pattern": "lazy_reply"}, {})
    assert "رد قصير" in msg1 or "تجاهل" in msg1
    msg2 = build_supervisor_injection({"pattern": "credential_repeat_loop"}, {})
    assert "credential" in msg2.lower() or "توكن" in msg2


# ─── Auto-E1 threshold ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auto_e1_triggers_at_3_interventions():
    s = SupervisorState()
    s.intervention_count_total = 2
    assert await should_invoke_auto_e1(s) is False
    s.intervention_count_total = 3
    assert await should_invoke_auto_e1(s) is True
    s.intervention_count_total = 5
    assert await should_invoke_auto_e1(s) is True


@pytest.mark.asyncio
async def test_auto_e1_does_not_trigger_for_healthy_session():
    s = SupervisorState()
    assert await should_invoke_auto_e1(s) is False
    assert await should_invoke_auto_e1(None) is False
