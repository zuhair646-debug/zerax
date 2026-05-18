"""Tests for the Shared Agent Core (SectionAgent + intent detection)."""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.shared import (  # noqa: E402
    SectionAgent, detect_intent, out_of_scope_message, SECTION_CONFIG,
    bind_db, session_create, session_get, session_append_turn,
)


class _Coll:
    def __init__(self):
        self.docs = []

    async def find_one(self, filt, proj=None):
        for d in self.docs:
            if all(d.get(k) == v for k, v in filt.items()):
                return {k: v for k, v in d.items() if k != "_id"}
        return None

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, filt, update, upsert=False):
        for d in self.docs:
            if all(d.get(k) == v for k, v in filt.items()):
                if "$set" in update:
                    for k, v in update["$set"].items():
                        if "." in k:
                            head, *rest = k.split(".")
                            d.setdefault(head, {})
                            d[head][".".join(rest)] = v
                        else:
                            d[k] = v
                if "$push" in update:
                    for k, v in update["$push"].items():
                        d.setdefault(k, []).append(v)
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        d[k] = d.get(k, 0) + v
                return
        if upsert:
            new = dict(filt)
            if "$set" in update:
                new.update(update["$set"])
            self.docs.append(new)

    def find(self, filt=None, proj=None):
        results = [
            {k: v for k, v in d.items() if k != "_id"}
            for d in self.docs
            if not filt or all(d.get(k) == v for k, v in filt.items() if not isinstance(v, dict))
        ]

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
        return len([d for d in self.docs if not filt or all(d.get(k) == v for k, v in filt.items())])


class _DB:
    def __init__(self):
        self.shared_agent_sessions = _Coll()
        self.shared_agent_qa_cache = _Coll()


@pytest.fixture()
def db():
    d = _DB()
    bind_db(d)
    yield d


# ── Intent detection ────────────────────────────────────────────────────


def test_detect_intent_video():
    assert detect_intent("ابغى فيديو سينمائي 8 ثواني") == "video"
    assert detect_intent("اعمل لي حلقة جديدة من السلسلة") == "video"


def test_detect_intent_image():
    assert detect_intent("صمم لي لوقو لمتجر") == "image"
    assert detect_intent("ابغى بوستر إعلاني") == "image"


def test_detect_intent_website():
    assert detect_intent("ابغى موقع لشركتي") == "website"


def test_detect_intent_app():
    assert detect_intent("ابي تطبيق جوال") == "app"


def test_detect_intent_none_for_neutral():
    assert detect_intent("شلونك") is None


# ── Out-of-scope routing ────────────────────────────────────────────────


def test_out_of_scope_image_to_video():
    r = out_of_scope_message("image", "video")
    assert r is not None
    assert r["to_route"] == "/chat/video"
    assert "قسم الفيديو" in r["to_label"]


def test_out_of_scope_owner_has_no_redirects():
    assert out_of_scope_message("owner", "image") is None


# ── Section configs sanity ──────────────────────────────────────────────


def test_all_scopes_have_persona():
    for scope, cfg in SECTION_CONFIG.items():
        assert "persona" in cfg and len(cfg["persona"]) > 30, scope
        assert "label" in cfg, scope


# ── Session persistence ────────────────────────────────────────────────


def test_session_create_and_get(db):
    s = asyncio.run(session_create("user1", "video"))
    assert s["scope"] == "video"
    fetched = asyncio.run(session_get(s["id"], "user1"))
    assert fetched is not None and fetched["id"] == s["id"]


def test_session_append_turn(db):
    s = asyncio.run(session_create("user1", "image"))
    asyncio.run(session_append_turn(s["id"], "user", "ابي لوقو"))
    fetched = asyncio.run(session_get(s["id"], "user1"))
    assert len(fetched.get("turns", [])) == 1
    assert fetched["turns"][0]["content"] == "ابي لوقو"


# ── SectionAgent redirect behaviour (no LLM call) ──────────────────────


def test_section_agent_redirects_out_of_scope(db, monkeypatch):
    # Patch _call_llm to fail loudly so we know it's not called
    from modules.shared import _call_llm as _orig  # noqa: F401

    async def _fake_llm(*a, **kw):
        raise AssertionError("LLM should not be called on redirect")

    monkeypatch.setattr("modules.shared._call_llm", _fake_llm)
    agent = SectionAgent("image")
    result = asyncio.run(agent.chat("u1", "ابي فيديو إعلاني 8 ثواني"))
    assert result["ok"] is True
    assert result.get("redirect")
    assert result["redirect"]["to_route"] == "/chat/video"


def test_section_agent_calls_llm_in_scope(db, monkeypatch):
    async def _fake_llm(scope, messages, max_tokens=1200):
        return f"reply for scope={scope}, turns={len(messages)}"

    monkeypatch.setattr("modules.shared._call_llm", _fake_llm)
    agent = SectionAgent("image", strict_scope=True)
    result = asyncio.run(agent.chat("u1", "ابي لوقو لمتجر تمور"))
    assert result["ok"] is True
    assert "reply for scope=image" in result["reply"]
    assert "redirect" not in result or not result.get("redirect")


def test_section_agent_owner_no_scope_lock(db, monkeypatch):
    async def _fake_llm(scope, messages, max_tokens=1200):
        return "owner reply"

    monkeypatch.setattr("modules.shared._call_llm", _fake_llm)
    agent = SectionAgent("owner")
    # Owner can ask about anything — no redirect
    result = asyncio.run(agent.chat("owner1", "اعمل لي صورة لوقو"))
    assert result["ok"] is True
    assert not result.get("redirect")
