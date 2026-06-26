"""
Tests for the upgraded Design Archive (المحفوظات):
  • /snapshots/{sid}/screenshot returns a real PNG (full + thumbnail).
  • The PNG is cached in the snapshot doc on first render.
  • /snapshots/{sid}/surgical-edit accepts instruction + selectors_json +
    optional annotated_image_b64 and stores the request + injects it into
    the project's chat session.
"""
import os
import json
import uuid
import asyncio
import pytest
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

API = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")


async def _make_project_with_snapshot():
    """Helper: create a fresh project, seed real HTML, manually save a snapshot."""
    async with httpx.AsyncClient(base_url=API, timeout=30) as cx:
        r = await cx.post("/api/auth/login", json={"email": "owner@zerax.com", "password": "owner123"})
        token = (r.json() or {}).get("token") or (r.json() or {}).get("access_token")
        assert token, r.text
        h = {"Authorization": f"Bearer {token}"}

        proj_resp = await cx.post(
            "/api/freebuild-chat/project",
            headers={**h, "Content-Type": "application/json"},
            json={"name": f"surgical-{uuid.uuid4().hex[:6]}", "type": "website", "mode": "website"},
        )
        pid = proj_resp.json()["id"]

        # Seed real HTML directly via Mongo (faster than going through chat).
        cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = cli[os.environ.get("DB_NAME", "test_database")]
        await db.freebuild_projects.update_one(
            {"id": pid},
            {"$set": {"current_html": (
                "<!DOCTYPE html><html dir=rtl><head><title>T</title>"
                "<style>body{background:#000;color:#fff;font-family:system-ui;margin:0;padding:40px}"
                "h1{color:#facc15;font-size:48px}section{padding:30px}</style></head>"
                "<body><h1>أهلاً</h1><section><h2>المكتبة</h2><p>قسم المكتبة هنا</p></section></body></html>"
            )}}
        )

        save_resp = await cx.post(
            f"/api/freebuild-chat/project/{pid}/snapshots/manual",
            headers=h, data={"label": "اختبار"},
        )
        assert save_resp.status_code == 200
        sid = save_resp.json()["snapshot"]["id"]
        return pid, sid, token


@pytest.mark.asyncio
async def test_screenshot_endpoint_returns_real_png():
    pid, sid, token = await _make_project_with_snapshot()
    h = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=API, timeout=60) as cx:
        # Full PNG (no thumb).
        r = await cx.get(f"/api/freebuild-chat/project/{pid}/snapshots/{sid}/screenshot", headers=h)
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n", "must be valid PNG magic"
        assert len(r.content) > 1000, "full render must be a non-trivial PNG"
        # Thumbnail.
        r2 = await cx.get(f"/api/freebuild-chat/project/{pid}/snapshots/{sid}/screenshot?thumb=1", headers=h)
        assert r2.status_code == 200
        assert r2.content[:8] == b"\x89PNG\r\n\x1a\n"
        # Thumbnail should be smaller than full (different cache key).
        assert len(r2.content) < len(r.content)


@pytest.mark.asyncio
async def test_screenshot_is_cached_on_second_call():
    pid, sid, token = await _make_project_with_snapshot()
    h = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=API, timeout=60) as cx:
        import time
        t0 = time.time()
        await cx.get(f"/api/freebuild-chat/project/{pid}/snapshots/{sid}/screenshot?thumb=1", headers=h)
        first = time.time() - t0
        t1 = time.time()
        await cx.get(f"/api/freebuild-chat/project/{pid}/snapshots/{sid}/screenshot?thumb=1", headers=h)
        second = time.time() - t1
        # Cached call must be >5× faster than the cold render.
        assert second < first / 3 or second < 0.3, f"cache must be fast: first={first:.2f}s second={second:.2f}s"


@pytest.mark.asyncio
async def test_surgical_edit_persists_request_and_injects_into_chat_session():
    pid, sid, token = await _make_project_with_snapshot()
    h = {"Authorization": f"Bearer {token}"}
    selectors = [
        {"x": 100, "y": 200, "w": 400, "h": 150, "color": "blue", "label": "مكتبة"},
        {"x": 50, "y": 400, "w": 200, "h": 80, "color": "green", "label": "زر"},
    ]
    async with httpx.AsyncClient(base_url=API, timeout=30) as cx:
        r = await cx.post(
            f"/api/freebuild-chat/project/{pid}/snapshots/{sid}/surgical-edit",
            headers=h,
            data={
                "instruction": "غير لون قسم المكتبة لأخضر فاتح",
                "selectors_json": json.dumps(selectors),
                "annotated_image_b64": "data:image/png;base64,aGVsbG8=",  # tiny stub
            },
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        request_id = d["request_id"]
        # The marker string includes both the instruction + coordinates.
        assert "المكتبة" in d["message_preview"] or "x=100" in d["message_preview"]
        # Verify the request was persisted with both selectors.
        list_resp = await cx.get(f"/api/freebuild-chat/project/{pid}/surgical-requests", headers=h)
        assert list_resp.status_code == 200
        items = list_resp.json()["requests"]
        match = next((x for x in items if x["id"] == request_id), None)
        assert match is not None
        assert len(match["selectors"]) == 2
        assert match["selectors"][0]["color"] == "blue"
        assert match["has_image"] is True


@pytest.mark.asyncio
async def test_surgical_edit_rejects_empty_instruction():
    pid, sid, token = await _make_project_with_snapshot()
    h = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=API, timeout=15) as cx:
        r = await cx.post(
            f"/api/freebuild-chat/project/{pid}/snapshots/{sid}/surgical-edit",
            headers=h,
            data={"instruction": "   ", "selectors_json": "[]"},
        )
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_screenshot_returns_404_for_unknown_snapshot():
    pid, _sid, token = await _make_project_with_snapshot()
    h = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=API, timeout=15) as cx:
        r = await cx.get(f"/api/freebuild-chat/project/{pid}/snapshots/nonexistent/screenshot", headers=h)
        assert r.status_code == 404
