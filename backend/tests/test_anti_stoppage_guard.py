"""
Regression test for the Anti-Announce-and-Stop guard.

When the AI returns text-only with a phrase like "راح أسوي ... انتظر دقيقة ⌛"
WITHOUT any tool_use, the orchestrator must re-prompt the AI with
tool_choice={"type": "any"} instead of breaking the loop. This kills the
"AI wrote a plan then froze" bug the user reported on prod.

We only unit-test the regex helper here (not the full streaming loop, which
needs an Anthropic key and is exercised by integration tests). The regex IS
the heart of the fix — false negatives let the bug through, false positives
make the AI loop forever when legitimately finished.
"""
import re
import pytest


_STOPPAGE_PATTERNS = [
    r"سأبدأ", r"راح أ", r"الآن أ", r"خلّيني أ", r"خليني أ",
    r"انتظر\s*(?:دقيقة|لحظة|قليلاً|ثانية)", r"⌛", r"⏳",
    r"يبدأ\s*التنفيذ", r"يبدأ\s*الآن", r"بعدها\s*أ", r"ثم\s*أ",
    r"\.\.\.\s*$", r":\s*$", r"Let me\s+",
    r"I'll\s+(?:start|begin|now)",
    r"سوف\s*أ", r"بحاول\s*أ",
]
STOPPAGE_RE = re.compile("|".join(_STOPPAGE_PATTERNS), re.IGNORECASE | re.MULTILINE)


def looks_like_unfulfilled_promise(text: str) -> bool:
    if not text:
        return False
    return bool(STOPPAGE_RE.search(text[-500:]))


@pytest.mark.parametrize("text,expected", [
    # ── TRUE POSITIVES (must trigger retry) ────────────────────────
    (
        "🔬 فحص هندسي شامل\nZenrex Films\nتمام! راح أسوي لكفحص هندسي كامل للموقع على 7 مستويات:\n"
        "1. HTML Structure ✅\n2. JavaScript Handlers 🪛\n3. Navigation Graph 🌐\n"
        "4. Visual Test 🎨 (متصفح حقيقي)\n5. Security Review 🔒\n6. Performance ⚡\n"
        "7. SEO & Accessibility 🎯\n\nانتظر دقيقة واحدة... ⌛",
        True,
    ),
    ("سأبدأ التنفيذ", True),
    ("Let me start by reading the file", True),
    ("خلّيني أصلح الـ placeholders", True),
    ("سأقوم الآن بفحص الكود وأبدأ بإصلاح المشاكل...", True),
    ("راح أسوي لك تصميم جديد", True),
    ("الآن أكتب الكود", True),
    ("سوف أنفذ التعديل", True),
    ("ثم أبني الـ navbar", True),
    ("بعدها أضيف الـ footer", True),

    # ── TRUE NEGATIVES (legitimate completion — must NOT trigger retry) ──
    ("تم — أضفت قسم hero بنجاح ✅", False),
    ("الموقع الآن جاهز للعرض. اضغط على الرابط", False),
    ("✅ تم النشر على https://zenrex.ai/s/my-site-v1", False),
    ("لا أستطيع تنفيذ هذا — يحتاج صلاحية إضافية.", False),
    ("النتيجة: 0 placeholders، 0 أخطاء", False),
    ("", False),
    # Tricky: "I will start" without "Let me" must NOT trigger (English)
    ("I will start now", False),
])
def test_unfulfilled_promise_detection(text, expected):
    assert looks_like_unfulfilled_promise(text) is expected, (
        f"FAIL: expected {expected} for: {text[:80]!r}"
    )


def test_only_tail_500_chars_checked():
    """Long legitimate answer ending with a clean status should NOT trigger,
    even if the body mentions 'سأبدأ' earlier."""
    text = (
        "في البداية كنت سأبدأ ببناء الصفحة الرئيسية فقط، لكن قررت أن أكمل كل الصفحات. "
        + ("نص طويل جداً. " * 200)
        + "✅ تم بناء 4 صفحات بنجاح، الموقع جاهز للنشر."
    )
    assert looks_like_unfulfilled_promise(text) is False


def test_short_promise_at_end_does_trigger():
    """Even after a long answer, if the tail ends with a promise → trigger."""
    text = ("نص طويل. " * 200) + "خلّيني أصلح ذا الشي الآن..."
    assert looks_like_unfulfilled_promise(text) is True
