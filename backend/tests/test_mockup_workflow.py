"""Smoke tests for the Mockup-Driven Workflow tools.

Validates:
  • `save_page_mockup` stores the mockup under project.mockups[filename]
  • `present_mockups_for_approval` requires saved mockups and flips stage
    to mockup_approval
  • `lock_blueprint` sets blueprint_locked + advances stage to visual_skeleton
  • `mark_page_built` appends to workflow_state.built_pages and reports
    remaining pages
"""
from __future__ import annotations
import importlib


def _ctx_at_mockup_design():
    fa = importlib.import_module("modules.freebuild.freebuild_agent")
    project = {
        "id": "TEST_proj_mockup",
        "user_id": "TEST_user",
        "pages": {},
        "current_html": "",
        "workflow_state": {
            "stage": "mockup_design",
            "discovery_answers": {
                "site_purpose": "x",
                "page_count_and_names": "x",
                "page_contents": "x",
                "style_preference": "x",
            },
        },
    }
    return fa, fa.FreeBuildToolContext(project, auth_token=None, db=None, is_owner=True)


def test_save_page_mockup_persists_to_project():
    fa, ctx = _ctx_at_mockup_design()
    res = fa._exec_tool(ctx, "save_page_mockup", {
        "page_filename": "index.html",
        "page_title": "الصفحة الرئيسية",
        "image_url": "https://example.com/mockup-index.png",
        "description": "Modern cinema homepage with hero banner",
    })
    assert res["ok"] is True
    assert "index.html" in res["mockups_saved"]
    assert ctx.project["mockups"]["index.html"]["image_url"].endswith("mockup-index.png")


def test_save_page_mockup_appends_html_extension():
    fa, ctx = _ctx_at_mockup_design()
    res = fa._exec_tool(ctx, "save_page_mockup", {
        "page_filename": "movies",  # without .html
        "page_title": "الأفلام",
        "image_url": "https://x/y.png",
    })
    assert res["ok"] is True
    assert "movies.html" in res["mockups_saved"]


def test_save_page_mockup_rejects_missing_url():
    fa, ctx = _ctx_at_mockup_design()
    res = fa._exec_tool(ctx, "save_page_mockup", {
        "page_filename": "index.html",
        "page_title": "X",
        "image_url": "",
    })
    assert res["ok"] is False


def test_present_mockups_for_approval_requires_saved_mockups():
    fa, ctx = _ctx_at_mockup_design()
    res = fa._exec_tool(ctx, "present_mockups_for_approval",
                        {"message": "هل توافق؟"})
    assert res["ok"] is False
    assert "save_page_mockup" in res["error"]


def test_present_mockups_for_approval_flips_stage_to_approval():
    fa, ctx = _ctx_at_mockup_design()
    fa._exec_tool(ctx, "save_page_mockup", {
        "page_filename": "index.html", "page_title": "الرئيسية",
        "image_url": "https://x/i.png",
    })
    res = fa._exec_tool(ctx, "present_mockups_for_approval",
                        {"message": "هل توافق؟"})
    assert res["ok"] is True
    assert res["ask_user"] is True
    assert res["kind"] == "mockup_approval"
    assert ctx.project["workflow_state"]["stage"] == "mockup_approval"
    assert any(m["image_url"] == "https://x/i.png" for m in res["mockups"])


def test_lock_blueprint_requires_mockups():
    fa, ctx = _ctx_at_mockup_design()
    res = fa._exec_tool(ctx, "lock_blueprint", {})
    assert res["ok"] is False


def test_lock_blueprint_sets_locked_flag_and_advances_to_visual_skeleton():
    fa, ctx = _ctx_at_mockup_design()
    fa._exec_tool(ctx, "save_page_mockup", {
        "page_filename": "index.html", "page_title": "الرئيسية",
        "image_url": "https://x/i.png",
    })
    fa._exec_tool(ctx, "save_page_mockup", {
        "page_filename": "movies.html", "page_title": "الأفلام",
        "image_url": "https://x/m.png",
    })
    res = fa._exec_tool(ctx, "lock_blueprint", {})
    assert res["ok"] is True
    assert res["blueprint_locked"] is True
    assert res["stage"] == "visual_skeleton"
    assert res["next_page_to_build"] == "index.html"  # index always first
    assert ctx.project["blueprint_locked"] is True
    assert ctx.project["workflow_state"]["stage"] == "visual_skeleton"


def test_mark_page_built_requires_existing_page():
    fa, ctx = _ctx_at_mockup_design()
    res = fa._exec_tool(ctx, "mark_page_built", {"filename": "missing.html"})
    assert res["ok"] is False


def test_mark_page_built_tracks_progress_and_advises_next():
    fa, ctx = _ctx_at_mockup_design()
    fa._exec_tool(ctx, "save_page_mockup", {
        "page_filename": "index.html", "page_title": "x",
        "image_url": "https://x/i.png",
    })
    fa._exec_tool(ctx, "save_page_mockup", {
        "page_filename": "movies.html", "page_title": "x",
        "image_url": "https://x/m.png",
    })
    fa._exec_tool(ctx, "lock_blueprint", {})
    # Simulate that index.html has been COMPLETED (2 sections + 600+ chars)
    real_text = "هذا نص حقيقي طويل لقسم البطل. " * 30
    ctx.project["pages"]["index.html"] = (
        "<!DOCTYPE html><html><body><main>"
        f"<section id='hero'><h1>Hero</h1><p>{real_text}</p></section>"
        f"<section id='features'><h2>Features</h2><p>{real_text}</p></section>"
        "</main></body></html>"
    )
    res = fa._exec_tool(ctx, "mark_page_built", {"filename": "index.html"})
    assert res["ok"] is True, f"failed: {res}"
    assert "index.html" in res["built_pages"]
    assert res["all_done"] is False
    assert res["remaining_pages"] == ["movies.html"]
    assert "movies.html" in res["next_action"]


def test_mark_page_built_rejects_blank_page():
    fa, ctx = _ctx_at_mockup_design()
    fa._exec_tool(ctx, "save_page_mockup", {
        "page_filename": "index.html", "page_title": "x",
        "image_url": "https://x/i.png",
    })
    fa._exec_tool(ctx, "lock_blueprint", {})
    # Page is essentially blank
    ctx.project["pages"]["index.html"] = "<html><body><section id='hero'></section></body></html>"
    res = fa._exec_tool(ctx, "mark_page_built", {"filename": "index.html"})
    assert res["ok"] is False
    assert res["error"] == "page_incomplete"
    assert "غير مكتملة" in res["message_ar"]


def test_mark_page_built_rejects_placeholder_text():
    fa, ctx = _ctx_at_mockup_design()
    fa._exec_tool(ctx, "save_page_mockup", {
        "page_filename": "index.html", "page_title": "x",
        "image_url": "https://x/i.png",
    })
    fa._exec_tool(ctx, "lock_blueprint", {})
    long = "Lorem ipsum " * 60
    ctx.project["pages"]["index.html"] = (
        "<!DOCTYPE html><html><body><main>"
        f"<section id='hero'><p>{long}</p></section>"
        f"<section id='cta'><p>قريباً</p></section>"
        "</main></body></html>"
    )
    res = fa._exec_tool(ctx, "mark_page_built", {"filename": "index.html"})
    assert res["ok"] is False
    assert "placeholders_found" in res
    assert len(res["placeholders_found"]) > 0
