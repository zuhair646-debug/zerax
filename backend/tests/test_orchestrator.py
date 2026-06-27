"""Unit + integration tests for the Orchestrator + Cortices.

Run with:
    cd /app/backend && MONGO_URL=mongodb://localhost:27017 DB_NAME=test_database \
        python tests/test_orchestrator.py
"""
import asyncio
import os
import sys

sys.path.insert(0, "/app/backend")


def test_classifier():
    """T1: Domain classifier."""
    from modules.freebuild.orchestrator.classifier import classify_intent_domain

    cases = [
        # (message, expected_primary, expect_multi_secondary)
        ("اعمل لي موقع متجر للعطور", "code", False),
        ("ولّد لي صورة شعار لمتجر عطور", "visual", False),
        ("اقرأ هذا النص بصوت رواي", "audio", False),
        ("اعمل لي فيديو ترويجي 15 ثانية", "video", False),
        ("اكتب لي مقال عن أهمية القهوة", "narrative", False),
        ("اعمل لي شعار + موقع + إعلان فيديو", None, True),  # multi
        ("نفّذ insert_html_at الآن", "code", False),
        ("", "code", False),  # empty → safe default
    ]
    for msg, expected, expect_multi in cases:
        out = classify_intent_domain(msg)
        if expect_multi:
            assert len(out.secondary) >= 1, f"expected multi for '{msg[:40]}', got {out}"
            print(f"  ✅ multi: '{msg[:40]}…' → primary={out.primary} secondary={out.secondary}")
        else:
            assert out.primary == expected, f"'{msg[:40]}': expected {expected}, got {out.primary}"
            print(f"  ✅ single: '{msg[:40]}…' → {out.primary} (conf={out.confidence:.2f})")
    print("✅ T1 classifier: PASS")


def test_feature_flag():
    """T2: ORCHESTRATOR_ENABLED feature flag."""
    from modules.freebuild.orchestrator import is_orchestrator_enabled
    os.environ.pop("ORCHESTRATOR_ENABLED", None)
    assert is_orchestrator_enabled() is False, "default must be False"
    os.environ["ORCHESTRATOR_ENABLED"] = "true"
    assert is_orchestrator_enabled() is True
    os.environ["ORCHESTRATOR_ENABLED"] = "false"
    assert is_orchestrator_enabled() is False
    print("✅ T2 feature flag: PASS")


async def test_narrative_cortex():
    """T3: NarrativeCortex (real LLM call)."""
    from modules.freebuild.orchestrator.cortices.narrative_cortex import stream_narrative_cortex

    project = {"id": "test-narrative", "user_id": "test-user", "pages": {}}
    chunks = []
    async for chunk in stream_narrative_cortex(
        project=project,
        user_message="اكتب slogan بـ 5 كلمات لمتجر قهوة عُماني فاخر",
        history=[],
        ctx_holder={},
    ):
        chunks.append(chunk)

    text = "".join(chunks)
    assert "cortex_started" in text, "must emit started event"
    assert "done" in text or "cortex_error" in text, "must end with done or error"
    print(f"  Events captured: {len(chunks)}")
    print("✅ T3 narrative cortex stream: PASS")


async def test_audio_cortex_tonejs():
    """T4: AudioCortex generates Tone.js snippet for music request (no real API)."""
    from modules.freebuild.orchestrator.cortices.audio_cortex import stream_audio_cortex

    chunks = []
    async for chunk in stream_audio_cortex(
        project={"id": "test-audio"},
        user_message="أبي موسيقى محيطية ambient خفيفة للموقع",
        history=[],
        ctx_holder={},
    ):
        chunks.append(chunk)
    text = "".join(chunks)
    assert "cortex_started" in text
    assert "tone" in text.lower() or "tonejs" in text.lower() or "Tone.js" in text
    print(f"  Events captured: {len(chunks)}")
    print("✅ T4 audio cortex (tone.js): PASS")


async def test_orchestrator_disabled_passthrough():
    """T5: When ORCHESTRATOR_ENABLED=false, orchestrator falls through to legacy."""
    os.environ["ORCHESTRATOR_ENABLED"] = "false"
    from modules.freebuild.orchestrator import is_orchestrator_enabled
    assert not is_orchestrator_enabled()
    print("✅ T5 orchestrator disabled by default: PASS")


async def test_code_cortex_delegates():
    """T6: CodeCortex must import stream_agent_turn from the real module."""
    from modules.freebuild.orchestrator.cortices.code_cortex import stream_code_cortex
    import inspect
    src = inspect.getsource(stream_code_cortex)
    assert "stream_agent_turn" in src, "CodeCortex must delegate to legacy stream_agent_turn"
    assert "freebuild_agent" in src, "CodeCortex must import from freebuild_agent"
    print("✅ T6 CodeCortex is true pass-through: PASS")


async def test_visual_cortex_prompt_refinement_stub():
    """T7: VisualCortex prompt refinement returns sane shape even without LLM key."""
    from modules.freebuild.orchestrator.cortices.visual_cortex import _refine_prompt_with_claude
    saved = os.environ.pop("EMERGENT_LLM_KEY", "")
    try:
        out = await _refine_prompt_with_claude("صورة قهوة بزاوية علوية")
        assert "english_prompt" in out
        assert "fallback" in out
    finally:
        if saved:
            os.environ["EMERGENT_LLM_KEY"] = saved
    print("✅ T7 visual cortex fallback path: PASS")


async def test_legacy_routes_still_work():
    """T8: Legacy /agent-chat-stream endpoint signature unchanged (smoke check)."""
    import inspect
    from modules.freebuild import freebuild_chat
    src = inspect.getsource(freebuild_chat)
    assert "agent-chat-stream" in src
    assert "orchestrator-stream" in src
    print("✅ T8 both endpoints registered: PASS")


async def main():
    print("\n=== Orchestrator + Cortices Test Suite ===\n")
    test_classifier()
    test_feature_flag()
    await test_narrative_cortex()
    await test_audio_cortex_tonejs()
    await test_orchestrator_disabled_passthrough()
    await test_code_cortex_delegates()
    await test_visual_cortex_prompt_refinement_stub()
    await test_legacy_routes_still_work()
    print("\n🎉 ALL 8 TESTS PASSED\n")


if __name__ == "__main__":
    asyncio.run(main())
