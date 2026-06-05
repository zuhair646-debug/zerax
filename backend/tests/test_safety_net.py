"""
Unit tests for safety-net logic in game_router.
Simulates the exact failure modes seen in production:
  (a) AI writes broken <<IMG_PRO ... newline ... >> tag → parser misses, safety-net must fire.
  (b) AI writes "خلّيني أولّد" + "اعتمد ولا نعدّل?" + NO tag → safety-net must fire.
  (c) AI writes nothing image-related → safety-net must NOT fire.
"""
import re
import pytest


# Replicate the broken-tag detection from game_router.py
def detect_broken_tag(ai_text: str):
    blocks = re.findall(r"<<\s*[^>]*?>>", ai_text, flags=re.DOTALL)
    if not blocks:
        return None
    return max(blocks, key=len)


def extract_prompt_from_broken(broken: str) -> str:
    inner = re.sub(r"^<<\s*[A-Za-z_\-\s]{0,20}[:：\-]?\s*", "", broken)
    inner = re.sub(r"\s*>>$", "", inner)
    return re.sub(r"\s+", " ", inner).strip()


PROMISE_PHRASES = [
    "الصورة جاهزة", "ولّدت", "إليك الصورة", "تم التوليد",
    "راح أولّد", "خلّيني أولّد", "بأرسم", "أرسم لك",
    "اعتمد ولا تي نعدّل", "اعتمد ولا تبي نعدّل", "اعتمد ولا نعدّل",
    "كعيّنة أولى", "نموذج لـ", "هذا المشهد",
]


def is_promise(ai_text: str) -> bool:
    low = ai_text.lower()
    return any(p in ai_text or p.lower() in low for p in PROMISE_PHRASES)


# ─────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────
def test_broken_tag_with_newlines_is_recovered():
    """Screenshot case: AI wrote tag broken by newlines + Saudi promise phrase."""
    ai = """خلّيني أولّد لك **حقل قمح ذهبي** كعيّنة أولى بأسلوب Hand-drawn Watercolor Isometric المتفق عليه:

<<IMG_PRO: golden wheat field, isometric view,
hand-drawn watercolor style, soft palette,
midday sun, ultra detailed
>>

**اعتمد ولا تي نعدّل؟**"""
    broken = detect_broken_tag(ai)
    assert broken is not None, "Must detect the multi-line tag"
    inner = extract_prompt_from_broken(broken)
    assert "golden wheat field" in inner
    assert "watercolor" in inner.lower()


def test_no_tag_but_promise_phrase_fires_safety():
    ai = """خلّيني أولّد لك حقل قمح ذهبي watercolor isometric.

---

اعتمد ولا تي نعدّل؟"""
    assert is_promise(ai)
    assert detect_broken_tag(ai) is None  # no <<...>> at all


def test_unrelated_message_does_not_fire():
    ai = "هلا! يا هلا. وش الفكرة الأساسية للعبتك؟ هل هي 2D أو 3D؟"
    assert not is_promise(ai)
    assert detect_broken_tag(ai) is None


def test_approval_question_alone_is_promise():
    """Even without 'راح أولّد', if AI ends with 'اعتمد ولا نعدّل' it implies an image existed."""
    ai = "النموذج جاهز للمراجعة.\n\n**اعتمد ولا نعدّل؟**"
    assert is_promise(ai)


def test_concept_art_phrase_fires():
    ai = "هذا المشهد الأولي للقرية في الصحراء، كنموذج أولي للمراجعة."
    assert is_promise(ai)


def test_multiple_broken_tags_longest_wins():
    ai = "<<IMG: small>> some text <<IMG_PRO: this is the long detailed prompt with watercolor isometric style and detailed scenery>>"
    broken = detect_broken_tag(ai)
    assert broken is not None
    inner = extract_prompt_from_broken(broken)
    assert "watercolor" in inner
    assert "this is the long detailed" in inner


def test_tag_with_full_width_colon():
    ai = "<<IMG_PRO： cinematic mountain view>>"  # full-width colon
    broken = detect_broken_tag(ai)
    assert broken is not None
    inner = extract_prompt_from_broken(broken)
    assert "cinematic" in inner


if __name__ == "__main__":
    import sys
    test_broken_tag_with_newlines_is_recovered()
    test_no_tag_but_promise_phrase_fires_safety()
    test_unrelated_message_does_not_fire()
    test_approval_question_alone_is_promise()
    test_concept_art_phrase_fires()
    test_multiple_broken_tags_longest_wins()
    test_tag_with_full_width_colon()
    print("✅ ALL 7 SAFETY-NET TESTS PASSED")
