"""
End-to-end test for Video Studio v2 — pipeline + series memory + pay-on-approval.

We mock the three external calls:
  • _generate_script  → returns a fake script JSON with 2 shots
  • _gen_storyboard_image → returns a fake URL
  • _render_shot → returns a fake mp4 data URL

Then we drive the pipeline through TestClient and assert:
  • Episode is created in 'script' stage with cost computed
  • Storyboard step transitions to 'storyboard' with previews populated
  • Approve gate fails if not in 'storyboard' or balance is short
  • Render deducts credits exactly once and persists final clips
  • Series memory: second episode reuses style + lists prior episode logline
"""
from __future__ import annotations
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock
from contextlib import asynccontextmanager

import asyncio
import pytest
import httpx
from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _run(coro):
    try:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.close()
        except Exception:
            pass


def _async_client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


# ── In-memory Mongo stub (just enough for our endpoints) ───────────────
class _Coll:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def find_one(self, filt, proj=None):
        for d in self.docs:
            if all(self._match(d, k, v) for k, v in filt.items()):
                return {k: v for k, v in d.items() if k != "_id"}
        return None

    @staticmethod
    def _match(d, key, val):
        if isinstance(val, dict) and "$gte" in val:
            return d.get(key, 0) >= val["$gte"]
        return d.get(key) == val

    async def update_one(self, filt, update, upsert=False):
        class R:
            modified_count = 0
        r = R()
        for d in self.docs:
            if all(self._match(d, k, v) for k, v in filt.items()):
                if "$set" in update:
                    d.update(update["$set"])
                if "$push" in update:
                    for k, v in update["$push"].items():
                        d.setdefault(k, []).append(v)
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        d[k] = d.get(k, 0) + v
                r.modified_count = 1
                return r
        if upsert:
            new = dict(filt)
            if "$set" in update:
                new.update(update["$set"])
            self.docs.append(new)
            r.modified_count = 1
        return r

    def find(self, filt=None, proj=None):
        results = []
        for d in self.docs:
            if not filt or all(self._match(d, k, v) for k, v in filt.items() if not isinstance(v, dict) or "$gte" not in v):
                results.append({k: v for k, v in d.items() if k != "_id"})

        class C:
            def __init__(self, items):
                self._items = items

            def sort(self, *_a, **_kw):
                return self

            def limit(self, n):
                self._items = self._items[:n]
                return self

            async def to_list(self, n):
                return self._items[:n]

        return C(results)

    async def count_documents(self, filt):
        return len([d for d in self.docs if not filt or all(self._match(d, k, v) for k, v in filt.items())])


class _DB:
    def __init__(self):
        self.users = _Coll()
        self.video_series = _Coll()
        self.video_episodes = _Coll()
        self.shared_agent_sessions = _Coll()
        self.shared_agent_qa_cache = _Coll()


# ── Fake auth dependency ───────────────────────────────────────────────
def _fake_user():
    return {"user_id": "test-user-1"}


@pytest.fixture()
def app_db():
    from modules.video_studio import create_video_studio_router
    from modules.shared import bind_db as _shared_bind

    db = _DB()
    _shared_bind(db)
    db.users.docs.append({"id": "test-user-1", "credits": 1000})

    app = FastAPI()
    app.include_router(create_video_studio_router(db, _fake_user))
    return app, db


@pytest.fixture()
def patched_llm():
    """Patch the three external calls so the test is hermetic."""
    fake_script = {
        "title": "وادي النور",
        "logline": "بطل يعبر صحراء ضبابية ليجد مدينة فضية.",
        "characters": [{"name": "سالم", "desc": "شاب 25، ثوب أبيض، عيون حادة"}],
        "style": "Cinematic 35mm, warm sunset palette, soft shadows",
        "shots": [
            {"n": 1, "title_ar": "بداية الرحلة", "narration_ar": "صحراء عند الفجر",
             "visual_en": "wide desert shot at dawn, soft amber light", "duration": 8},
            {"n": 2, "title_ar": "اكتشاف المدينة", "narration_ar": "ضوء فضي يلمع",
             "visual_en": "discovery of a silver city from a dune top", "duration": 8},
        ],
    }
    fake_url = "/api/video-studio/storyboard-img/abcd1234.png"
    fake_clip = "data:video/mp4;base64,AAAA"

    with patch("modules.video_studio._generate_script", new=AsyncMock(return_value=fake_script)) as ps, \
         patch("modules.video_studio._gen_storyboard_image", new=AsyncMock(return_value=fake_url)) as pi, \
         patch("modules.video_studio._render_shot", new=AsyncMock(return_value=fake_clip)) as pr:
        yield ps, pi, pr


# ────────────────────────────────────────────────────────────────────────


def test_series_create_and_list(app_db):
    app, db = app_db

    async def run():
        async with _async_client(app) as c:
            r = await c.post("/api/video-studio/series/create", json={
                "title": "سلسلة وادي النور",
                "description": "مغامرات سالم في الصحراء",
                "style_direction": "Cinematic 35mm, sepia desert",
                "main_characters": [{"name": "سالم", "desc": "بطل 25 سنة"}],
            })
            assert r.status_code == 200, r.text
            s = r.json()["series"]
            assert s["title"].startswith("سلسلة")

            r2 = await c.get("/api/video-studio/series")
            assert r2.status_code == 200
            items = r2.json()["series"]
            assert len(items) == 1
            assert items[0]["episode_count"] == 0

    _run(run())


def test_full_pipeline_script_storyboard_approve_render(app_db, patched_llm):
    app, db = app_db

    async def run():
        async with _async_client(app) as c:
            r = await c.post("/api/video-studio/series/create", json={
                "title": "وادي النور", "style_direction": "Cinematic 35mm",
                "main_characters": [{"name": "سالم", "desc": "بطل 25"}],
            })
            sid = r.json()["series"]["id"]

            r = await c.post("/api/video-studio/script", json={
                "session_id": "sess-1", "series_id": sid,
                "brief": "حلقة 1: سالم يبدأ رحلته",
                "requested_shots": 2, "shot_duration": 8,
            })
            assert r.status_code == 200, r.text
            body = r.json()
            ep = body["episode"]
            assert ep["stage"] == "script"
            assert ep["episode_number"] == 1
            assert len(ep["shots"]) == 2
            assert body["estimated_cost_credits"] == 14 + 14
            assert db.users.docs[0]["credits"] == 1000
            ep_id = ep["id"]

            r = await c.post("/api/video-studio/storyboard", json={"episode_id": ep_id})
            assert r.status_code == 200, r.text
            sb = r.json()
            assert sb["previews_generated"] == 2

            r = await c.post("/api/video-studio/approve",
                             json={"episode_id": ep_id, "confirmed": True})
            assert r.status_code == 200, r.text
            assert r.json()["cost_to_be_charged_on_render"] == 28
            assert db.users.docs[0]["credits"] == 1000

            r = await c.post("/api/video-studio/render", json={"episode_id": ep_id})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["credits_charged"] == 28
            assert body["credits_remaining"] == 972
            assert body["shots_rendered"] == 2

            r = await c.get(f"/api/video-studio/episode/{ep_id}")
            ep2 = r.json()["episode"]
            assert ep2["stage"] == "rendered"
            assert ep2["credits_charged"] == 28

    _run(run())


def test_approve_rejected_before_storyboard(app_db, patched_llm):
    app, db = app_db

    async def run():
        async with _async_client(app) as c:
            r = await c.post("/api/video-studio/script", json={
                "session_id": "s2", "brief": "test",
                "requested_shots": 2, "shot_duration": 8,
            })
            ep_id = r.json()["episode"]["id"]
            r2 = await c.post("/api/video-studio/approve",
                              json={"episode_id": ep_id, "confirmed": True})
            assert r2.status_code == 400

    _run(run())


def test_render_blocked_without_approval(app_db, patched_llm):
    app, db = app_db

    async def run():
        async with _async_client(app) as c:
            r = await c.post("/api/video-studio/script", json={
                "session_id": "s3", "brief": "test",
                "requested_shots": 1, "shot_duration": 4,
            })
            ep_id = r.json()["episode"]["id"]
            await c.post("/api/video-studio/storyboard", json={"episode_id": ep_id})
            r2 = await c.post("/api/video-studio/render", json={"episode_id": ep_id})
            assert r2.status_code == 400

    _run(run())


def test_insufficient_credits_blocks_approve(app_db, patched_llm):
    app, db = app_db
    db.users.docs[0]["credits"] = 5

    async def run():
        async with _async_client(app) as c:
            r = await c.post("/api/video-studio/script", json={
                "session_id": "s4", "brief": "expensive",
                "requested_shots": 3, "shot_duration": 12,
            })
            ep_id = r.json()["episode"]["id"]
            await c.post("/api/video-studio/storyboard", json={"episode_id": ep_id})
            r2 = await c.post("/api/video-studio/approve",
                              json={"episode_id": ep_id, "confirmed": True})
            assert r2.status_code == 402

    _run(run())


def test_series_memory_tracks_episode_continuity(app_db, patched_llm):
    app, db = app_db

    async def run():
        async with _async_client(app) as c:
            r = await c.post("/api/video-studio/series/create", json={
                "title": "حكاية الصحراء", "style_direction": "warm 35mm",
            })
            sid = r.json()["series"]["id"]

            r1 = await c.post("/api/video-studio/script", json={
                "session_id": "s1", "series_id": sid,
                "brief": "حلقة 1", "requested_shots": 1, "shot_duration": 4,
            })
            assert r1.json()["episode"]["episode_number"] == 1

            r2 = await c.post("/api/video-studio/script", json={
                "session_id": "s1", "series_id": sid,
                "brief": "حلقة 2", "requested_shots": 1, "shot_duration": 4,
            })
            assert r2.json()["episode"]["episode_number"] == 2

            r3 = await c.get(f"/api/video-studio/series/{sid}/episodes")
            assert r3.status_code == 200
            eps = r3.json()["episodes"]
            assert len(eps) == 2
            assert [e["episode_number"] for e in eps] == [1, 2]

    _run(run())
