"""Functional simulation of the PRE-FINISH GATE logic.

The companion test_pre_finish_gate.py validates the SOURCE markers (gate
exists, in the right branch, uses correct thresholds). This file
EXECUTES the same regex/threshold logic against synthetic page dicts to
make sure the gate behaves correctly in practice — especially the
critical AND-not-OR threshold and the empty-pages edge case.
"""
from __future__ import annotations
import re


# ---------------------------------------------------------------------------
# Re-implement the gate's blank-detection logic exactly as it appears in
# /app/backend/modules/freebuild/freebuild_agent.py:9676-9689 .
# Keep this in sync if the gate changes.
# ---------------------------------------------------------------------------
def _detect_blank_pages(pages: dict[str, str]) -> list[str]:
    blanks: list[str] = []
    for fn, html in (pages or {}).items():
        if not html:
            blanks.append(fn)
            continue
        sec_count = len(re.findall(
            r'<section\b[^>]*\bid\s*=\s*["\'][^"\']+["\']',
            html, re.I,
        ))
        text_only = re.sub(r"<[^>]+>", " ", html)
        text_only = re.sub(r"\s+", " ", text_only).strip()
        if sec_count <= 1 and len(text_only) < 800:
            blanks.append(fn)
    return blanks


# --- Test fixtures ----------------------------------------------------------
LONG_TEXT = ("لوريم إيبسوم هو نموذج افتراضي يوضع في التصاميم لتوضيح "
             "كيف ستبدو النصوص الحقيقية في الموقع. " * 25)  # ~1700 chars

FULL_HOMEPAGE = (
    "<html><body>"
    f'<section id="hero"><h1>سينما أطراف العالم</h1><p>{LONG_TEXT}</p></section>'
    f'<section id="features"><h2>المميزات</h2><p>{LONG_TEXT}</p></section>'
    f'<section id="movies"><h2>الأفلام</h2><p>{LONG_TEXT}</p></section>'
    "</body></html>"
)

SKELETON_MOVIES = (
    "<html><body><main><h1>مكتبة الأفلام</h1>"
    "<!-- SCAFFOLD_PLACEHOLDER --></main></body></html>"
)

SKELETON_OFFERS = (
    "<html><body><h1>العروض والنقاط</h1></body></html>"
)


# --- The actual cinema-site scenario reported by the user -------------------
def test_cinema_scenario_flags_only_sidebar_pages():
    pages = {
        "index.html": FULL_HOMEPAGE,
        "movies.html": SKELETON_MOVIES,
        "offers.html": SKELETON_OFFERS,
        "account.html": SKELETON_OFFERS,
    }
    blanks = _detect_blank_pages(pages)
    assert "movies.html" in blanks
    assert "offers.html" in blanks
    assert "account.html" in blanks
    assert "index.html" not in blanks, (
        "Homepage with 3 sections + long text must NOT be flagged blank"
    )


def test_empty_pages_dict_returns_no_blanks():
    """Edge case the gate must handle: single-page project where
    ctx.pages is empty/None — the gate must not raise and must not block.
    """
    assert _detect_blank_pages({}) == []
    assert _detect_blank_pages(None) == []  # type: ignore[arg-type]


def test_one_section_but_lots_of_text_is_NOT_blank():
    """Critical AND-not-OR check: a page with exactly 1 section but
    >800 chars of meaningful text must NOT be flagged.
    """
    html = (
        "<html><body>"
        f'<section id="hero"><h1>About</h1><p>{LONG_TEXT}</p></section>'
        "</body></html>"
    )
    assert _detect_blank_pages({"about.html": html}) == []


def test_many_sections_but_no_text_is_NOT_blank():
    """Other half of the AND: many sections (>1) — even if text is tiny —
    must NOT be flagged, because the section count alone already passes.
    """
    html = (
        "<html><body>"
        '<section id="a"><h2>A</h2></section>'
        '<section id="b"><h2>B</h2></section>'
        "</body></html>"
    )
    blanks = _detect_blank_pages({"x.html": html})
    assert blanks == [], (
        "≥ 2 sections must short-circuit the gate even with little text"
    )


def test_one_section_and_short_text_IS_blank():
    """The AND condition both hold → must flag."""
    html = (
        "<html><body>"
        '<section id="hero"><h1>Title</h1><p>short</p></section>'
        "</body></html>"
    )
    blanks = _detect_blank_pages({"sparse.html": html})
    assert blanks == ["sparse.html"]


def test_empty_html_string_flagged():
    """`if not html:` short-circuit."""
    assert _detect_blank_pages({"blank.html": ""}) == ["blank.html"]


def test_section_without_id_does_not_count():
    """The regex requires `id="..."` — a bare `<section>` should NOT
    count towards section_count, otherwise placeholder `<section>` tags
    in the skeleton would falsely bump the count above threshold.
    """
    html = (
        "<html><body>"
        "<section><h1>No id</h1></section>"
        "<section><h2>Also no id</h2></section>"
        "</body></html>"
    )
    # sec_count = 0, text < 800 → blank
    assert _detect_blank_pages({"p.html": html}) == ["p.html"]


def test_scaffold_placeholder_skeleton_is_blank():
    """The real-world `create_page` skeleton (with SCAFFOLD_PLACEHOLDER
    comment) is the exact failure mode that caused the bug. Must flag.
    """
    blanks = _detect_blank_pages({"movies.html": SKELETON_MOVIES})
    assert blanks == ["movies.html"]
