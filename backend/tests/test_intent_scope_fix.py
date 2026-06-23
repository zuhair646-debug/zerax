"""Regression test for the `_intent` UnboundLocalError bug.

Before this fix, `_intent` and `_has_content` were defined ONLY inside the
Anthropic provider branch. When the provider was `openai_direct` (Hybrid
mode), downstream code at lines 9237 (SURGICAL-HARDBLOCK) and 9693
(DESIGN-DESTRUCTION GUARD) tried to read `_intent` and crashed with:

    UnboundLocalError: cannot access local variable '_intent'
    where it is not associated with a value

The fix lifts the classification out of the provider branch so it runs
exactly once at the top of stream_one_provider, ensuring `_intent` and
`_has_content` are defined for EVERY provider.
"""
from __future__ import annotations
import re


def test_classifier_runs_before_provider_branch():
    """The global classifier block MUST appear in source BEFORE the
    closest `if provider in ("anthropic", "emergent_anthropic"):` branch
    that follows it (i.e. the one inside _stream_one_provider).
    """
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()

    classifier_match = re.search(r"GLOBAL CLASSIFIER", src)
    assert classifier_match is not None, "Global classifier marker missing"

    # Find the NEXT provider branch after the classifier
    after_classifier = src[classifier_match.end():]
    branch_match = re.search(
        r'if provider in \("anthropic", "emergent_anthropic"\):', after_classifier
    )
    assert branch_match is not None, (
        "Expected an `if provider in (anthropic, ...)` branch AFTER the "
        "GLOBAL CLASSIFIER block. The classifier should sit directly above "
        "the provider switch in _stream_one_provider."
    )


def test_intent_assigned_outside_provider_branch():
    """`_intent = classify_user_intent(...)` must be assigned at indentation
    level that is OUTSIDE both branches (not nested inside an `if provider`
    block).
    """
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    # Find every occurrence of `_intent = classify_user_intent`
    matches = [
        (m.start(), src[max(0, m.start() - 200):m.start()])
        for m in re.finditer(r"_intent = classify_user_intent", src)
    ]
    assert matches, "_intent assignment not found at all"

    # At least one assignment must be outside the Anthropic-only branch.
    # We check that one of the matches has the 'GLOBAL CLASSIFIER' marker
    # within the preceding 600 chars.
    has_global = any(
        "GLOBAL CLASSIFIER" in src[max(0, pos - 600):pos]
        for pos, _ in matches
    )
    assert has_global, (
        "Expected `_intent = classify_user_intent` under the GLOBAL CLASSIFIER block. "
        "Without it, openai_direct provider crashes with UnboundLocalError."
    )


def test_has_content_assigned_outside_provider_branch():
    """`_has_content = ...` must also live outside the provider branch."""
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    matches = [
        m.start()
        for m in re.finditer(r"_has_content = bool\(", src)
    ]
    assert matches, "_has_content assignment not found"
    has_global = any(
        "GLOBAL CLASSIFIER" in src[max(0, pos - 600):pos]
        for pos in matches
    )
    assert has_global, (
        "Expected `_has_content` to be assigned under the GLOBAL CLASSIFIER block."
    )


def test_fallback_values_set_on_classifier_exception():
    """If classification fails, `_intent` and `_has_content` must still have
    safe fallback values so downstream guards don't crash.
    """
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    # Look for the fallback block (Python ast would be more robust but
    # substring is sufficient for this regression guard).
    assert '_intent = "new_build"' in src, (
        "Missing safe fallback assignment for _intent on classification error"
    )
    assert "_has_content = False" in src, (
        "Missing safe fallback assignment for _has_content on classification error"
    )


def test_no_duplicate_intent_assignment_inside_anthropic_branch():
    """After the fix, the inline `_intent = classify_user_intent` inside the
    Anthropic branch should be REMOVED — otherwise we have a divergence
    between the global value and a branch-local one.
    """
    src = open("/app/backend/modules/freebuild/freebuild_agent.py").read()
    # Count total assignments
    total = len(re.findall(r"_intent = classify_user_intent", src))
    # Only one expected (the global one)
    assert total == 1, (
        f"Expected exactly 1 `_intent = classify_user_intent` assignment "
        f"(global), found {total}. Duplicate inside provider branch would "
        f"shadow the global value and re-introduce subtle bugs."
    )
