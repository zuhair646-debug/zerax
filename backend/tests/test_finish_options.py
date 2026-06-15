"""Tests for `_normalize_finish_options` and `_normalize_inline_images`.

These guard the contract: the AI's `finish` tool can pass options as plain
strings OR rich `{label, emoji?, image_url?, description?}` objects. Same for
`inline_images` which is `[{url, caption?}, ...]`. Bad inputs get silently
dropped — we never raise.
"""
from modules.freebuild.freebuild_agent import (
    _normalize_finish_options,
    _normalize_inline_images,
)


def test_normalize_options_plain_strings():
    out = _normalize_finish_options(["A", "B", "C"])
    assert out == ["A", "B", "C"]


def test_normalize_options_rich_objects():
    out = _normalize_finish_options([
        {"label": "كرتون", "emoji": "🎨", "image_url": "https://x.com/a.jpg",
         "description": "Pixar"},
        {"label": "أنمي"},
    ])
    assert out[0] == {"label": "كرتون", "emoji": "🎨",
                       "image_url": "https://x.com/a.jpg", "description": "Pixar"}
    assert out[1] == {"label": "أنمي"}


def test_normalize_options_mixed():
    out = _normalize_finish_options(["plain", {"label": "rich", "emoji": "✨"}])
    assert out == ["plain", {"label": "rich", "emoji": "✨"}]


def test_normalize_options_skips_invalid():
    out = _normalize_finish_options([
        "ok",
        {"emoji": "🎨"},  # no label → dropped
        {"label": ""},     # empty label → dropped
        None,
        42,
    ])
    assert out == ["ok"]


def test_normalize_options_caps_at_6():
    out = _normalize_finish_options([f"o{i}" for i in range(10)])
    assert len(out) == 6


def test_normalize_options_rejects_javascript_urls():
    out = _normalize_finish_options([
        {"label": "X", "image_url": "javascript:alert(1)"},
    ])
    assert out == [{"label": "X"}]  # image_url stripped


def test_normalize_options_non_list():
    assert _normalize_finish_options(None) == []
    assert _normalize_finish_options("nope") == []
    assert _normalize_finish_options({}) == []


def test_inline_images_basic():
    out = _normalize_inline_images([
        {"url": "https://x.com/a.jpg", "caption": "ref 1"},
        {"url": "/uploads/b.jpg"},
    ])
    assert out == [
        {"url": "https://x.com/a.jpg", "caption": "ref 1"},
        {"url": "/uploads/b.jpg"},
    ]


def test_inline_images_drops_invalid():
    out = _normalize_inline_images([
        {"url": ""},
        {"caption": "no url"},
        {"url": "javascript:bad"},
        "not a dict",
        {"url": "https://ok.com/x.jpg"},
    ])
    assert out == [{"url": "https://ok.com/x.jpg"}]


def test_inline_images_caps_at_6():
    out = _normalize_inline_images([
        {"url": f"https://x.com/{i}.jpg"} for i in range(10)
    ])
    assert len(out) == 6
