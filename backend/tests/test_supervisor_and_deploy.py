"""
Unit tests for the Silent Supervisor and Multi-Deploy modules (Feb 2026).
Run: cd /app/backend && pytest tests/test_supervisor_and_deploy.py -q
"""
from __future__ import annotations

import asyncio
import pytest

from modules.freebuild.silent_supervisor import (
    SupervisorState,
    record_tool_event,
    record_assistant_text,
    detect_stuck_pattern,
    build_supervisor_injection,
)
from modules.freebuild.multi_deploy import (
    _bundle_to_files,
    _safe_project_slug,
    DEPLOY_OPTIONS_AR,
)


# ─── Silent Supervisor ────────────────────────────────────────────────

def test_supervisor_detects_repeated_tool_failure():
    s = SupervisorState()
    for _ in range(3):
        record_tool_event(s, "write_full_html", {"html": "x"}, {"ok": False, "error": "html too large"})
    p = detect_stuck_pattern(s)
    assert p is not None
    assert p["pattern"] == "repeated_tool_failure"
    assert p["tool_name"] == "write_full_html"
    assert p["count"] >= 3


def test_supervisor_detects_identical_loop():
    s = SupervisorState()
    payload = {"id": "hero", "op": "replace"}
    for _ in range(3):
        record_tool_event(s, "apply_section", payload, {"ok": True})
    p = detect_stuck_pattern(s)
    assert p is not None
    assert p["pattern"] == "loop_same_call"


def test_supervisor_detects_giveup_text():
    s = SupervisorState()
    record_tool_event(s, "test_page", {}, {"ok": True})
    record_assistant_text(s, "أعتذر، لا أستطيع إكمال هذا الطلب")
    p = detect_stuck_pattern(s)
    assert p is not None
    assert p["pattern"] == "assistant_gave_up"


def test_supervisor_returns_none_when_healthy():
    s = SupervisorState()
    record_tool_event(s, "read_current_html", {}, {"ok": True})
    record_tool_event(s, "list_pages", {}, {"ok": True})
    record_tool_event(s, "write_full_html", {"html": "ok"}, {"ok": True})
    assert detect_stuck_pattern(s) is None


def test_supervisor_injection_is_actionable():
    msg = build_supervisor_injection(
        {"pattern": "repeated_tool_failure", "tool_name": "deploy_to_vercel",
         "errors": ["401 invalid token"], "count": 3},
        {"pages": ["index.html"]},
    )
    assert "deploy_to_vercel" in msg
    assert "401 invalid token" in msg
    assert "request_credential" in msg  # nudges toward the right action


# ─── Multi-Deploy bundling ────────────────────────────────────────────

def test_bundle_creates_index_when_missing():
    files = _bundle_to_files({"home": "<html>HOME</html>", "about": "<html>ABOUT</html>"})
    assert "index.html" in files
    assert "about.html" in files


def test_bundle_keeps_existing_index():
    files = _bundle_to_files({"index.html": "<html>I</html>", "blog": "<html>B</html>"})
    assert files["index.html"] == "<html>I</html>"
    assert "blog.html" in files


def test_bundle_includes_extras():
    files = _bundle_to_files(
        {"index.html": "<html>x</html>"},
        extras={"styles.css": "body{}", "app.js": "console.log(1)"},
    )
    assert files["styles.css"] == "body{}"
    assert files["app.js"] == "console.log(1)"


def test_bundle_rejects_empty_pages():
    with pytest.raises(ValueError):
        _bundle_to_files({})


def test_slug_normalization():
    assert _safe_project_slug("My Cool Site!!!") == "my-cool-site"
    assert _safe_project_slug("---") == "zenrex-site"
    assert _safe_project_slug("ab") == "ab-app"
    assert len(_safe_project_slug("a" * 100)) == 50


def test_deploy_catalog_has_four_options():
    assert len(DEPLOY_OPTIONS_AR) == 4
    ids = {o["id"] for o in DEPLOY_OPTIONS_AR}
    assert ids == {"zenrex", "vercel", "cloudflare_pages", "github_pages"}
    # Customer-token providers MUST have a credential_url and label
    for opt in DEPLOY_OPTIONS_AR:
        if opt["needs_credentials"]:
            assert opt.get("credential_url", "").startswith("https://")
            assert opt.get("credential_label_ar")
