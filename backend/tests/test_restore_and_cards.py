"""Tests for restore_snapshot + intent_lock + card-dummy detection."""
import pytest
from modules.freebuild.freebuild_agent import (
    FreeBuildToolContext, _exec_tool, _scan_for_dummy_ui,
)
from modules.freebuild.action_pricing import classify_intent


# ─── Restore intent classifier ─────────────────────────────────────────

class TestRestoreIntent:
    @pytest.mark.parametrize("msg", [
        "ارجع للتصميم السابق",
        "رجع لي للتصميم القديم",
        "الغ آخر تعديل",
        "ما عجبني الجديد ارجع للقديم",
        "undo",
        "rollback",
        "restore",
        "تراجع عن التعديل",
    ])
    def test_restore_detected(self, msg):
        assert classify_intent(msg) == "restore", f"failed for {msg!r}"

    @pytest.mark.parametrize("msg", [
        "ابني لي موقع",
        "اضف زر",
        "غير اللون",
        "احذف القسم",
    ])
    def test_non_restore_not_matched(self, msg):
        assert classify_intent(msg) != "restore", f"false positive: {msg!r}"


# ─── restore_snapshot tool ─────────────────────────────────────────────

def _ctx_with_snapshots():
    """Set up a context with multiple HTML snapshots."""
    proj = {
        "id": "p1", "user_id": "u1",
        "active_page": "index.html",
        "pages": {"index.html": "<html><body>v3-current</body></html>"},
        "html_snapshots": [
            {"id": "snap-1", "html": "<html><body>v1-oldest</body></html>",
             "created_at": "2026-01-01", "summary": "النسخة الأقدم"},
            {"id": "snap-2", "html": "<html><body>v2-middle</body></html>",
             "created_at": "2026-01-02", "summary": "النسخة الوسطى"},
        ],
    }
    ctx = FreeBuildToolContext(proj)
    ctx.current_html = proj["pages"]["index.html"]
    return ctx


def test_restore_snapshot_default_offset():
    ctx = _ctx_with_snapshots()
    r = _exec_tool(ctx, "restore_snapshot", {})
    assert r["ok"], r
    assert r["restored_snapshot_id"] == "snap-2"
    assert "v2-middle" in ctx.current_html


def test_restore_snapshot_by_id():
    ctx = _ctx_with_snapshots()
    r = _exec_tool(ctx, "restore_snapshot", {"snapshot_id": "snap-1"})
    assert r["ok"]
    assert "v1-oldest" in ctx.current_html


def test_restore_snapshot_unknown_id():
    ctx = _ctx_with_snapshots()
    r = _exec_tool(ctx, "restore_snapshot", {"snapshot_id": "snap-nope"})
    assert not r["ok"]
    assert "not found" in r["error"].lower()


def test_restore_snapshot_offset_out_of_range():
    ctx = _ctx_with_snapshots()
    r = _exec_tool(ctx, "restore_snapshot", {"offset": 99})
    assert not r["ok"]
    assert "out of range" in r["error"]


def test_restore_snapshot_no_snapshots():
    proj = {"id": "p1", "user_id": "u1", "active_page": "index.html",
            "pages": {"index.html": "x"}, "html_snapshots": []}
    ctx = FreeBuildToolContext(proj)
    ctx.current_html = "x"
    r = _exec_tool(ctx, "restore_snapshot", {})
    assert not r["ok"]
    assert "no snapshots" in r["error"].lower()


def test_list_snapshots():
    ctx = _ctx_with_snapshots()
    r = _exec_tool(ctx, "list_snapshots", {})
    assert r["ok"]
    assert r["count"] == 2
    # Newest first
    assert r["snapshots"][0]["id"] == "snap-2"
    assert r["snapshots"][1]["id"] == "snap-1"


# ─── Card-dummy detection ──────────────────────────────────────────────

def test_dead_movie_card_caught():
    html = (
        '<!doctype html><html><body>'
        '<div class="movies-grid">'
        '  <div class="movie-card">'
        '    <h3>فيلم 1</h3>'
        '    <p>وصف...</p>'
        '  </div>'
        '  <div class="movie-card">'
        '    <h3>فيلم 2</h3>'
        '  </div>'
        '</div>'
        '<script>console.log("nothing wired");</script>'
        '</body></html>'
    )
    r = _scan_for_dummy_ui(html)
    assert not r["ok"]
    card_problems = [b for b in r["dead_buttons"] if "card:movie-card" in b["text"]]
    assert len(card_problems) >= 2, f"expected ≥2 dead cards, got {r['dead_buttons']}"


def test_card_wrapped_in_link_is_clean():
    html = (
        '<!doctype html><html><body>'
        '<a href="movies.html?id=1"><div class="movie-card"><h3>فيلم</h3></div></a>'
        '<a href="movies.html?id=2"><div class="movie-card"><h3>فيلم 2</h3></div></a>'
        '</body></html>'
    )
    r = _scan_for_dummy_ui(html)
    # No dead cards should be flagged
    card_problems = [b for b in r["dead_buttons"] if "card:" in b["text"]]
    assert len(card_problems) == 0


def test_card_with_onclick_is_clean():
    html = (
        '<!doctype html><html><body>'
        '<div class="product-card" onclick="openProduct(1)"><h3>منتج</h3></div>'
        '</body></html>'
    )
    r = _scan_for_dummy_ui(html)
    card_problems = [b for b in r["dead_buttons"] if "card:product-card" in b["text"]]
    assert len(card_problems) == 0


def test_card_with_data_id_is_clean():
    html = (
        '<!doctype html><html><body>'
        '<article class="movie-card" data-movie-id="42"><h3>فيلم</h3></article>'
        '<script>document.querySelectorAll(".movie-card").forEach(c => c.addEventListener("click", openMovie));</script>'
        '</body></html>'
    )
    r = _scan_for_dummy_ui(html)
    card_problems = [b for b in r["dead_buttons"] if "card:" in b["text"]]
    assert len(card_problems) == 0
