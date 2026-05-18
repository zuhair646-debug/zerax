"""
Tests for the Auto-Coder code cache module.

We exercise:
  • File hash cache hit/miss across content changes.
  • Stats counters & token-savings.
  • Cache invalidation when a write happens.
  • Semantic query cache: exact-hash hit when embeddings are unavailable.
  • Tool wrappers report the right shape.
"""
from __future__ import annotations
import os
import sys
import tempfile
import asyncio
from pathlib import Path

import pytest

# Make the backend modules importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.autocoder import code_cache  # noqa: E402


class _MockCollection:
    def __init__(self):
        self.docs = []

    async def find_one(self, filt, proj=None):
        for d in self.docs:
            if all(d.get(k) == v for k, v in filt.items()):
                return {k: v for k, v in d.items() if k != "_id"}
        return None

    def find(self, filt=None, proj=None):
        results = [
            {k: v for k, v in d.items() if k != "_id"}
            for d in self.docs
            if not filt or all(d.get(k) == v for k, v in filt.items() if not isinstance(v, dict))
        ]

        class _Cur:
            def __init__(self, items):
                self._items = items

            def sort(self, *_a, **_kw):
                return self

            def limit(self, n):
                self._items = self._items[:n]
                return self

            async def to_list(self, n):
                return self._items[:n]

        return _Cur(results)

    async def update_one(self, filt, update, upsert=False):
        for d in self.docs:
            if all(d.get(k) == v for k, v in filt.items()):
                if "$set" in update:
                    d.update(update["$set"])
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        d[k] = d.get(k, 0) + v
                if "$setOnInsert" in update:
                    pass  # only on insert
                return
        if upsert:
            new = dict(filt)
            if "$set" in update:
                new.update(update["$set"])
            if "$inc" in update:
                new.update(update["$inc"])
            if "$setOnInsert" in update:
                new.update(update["$setOnInsert"])
            self.docs.append(new)

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def delete_one(self, filt):
        class R:
            deleted_count = 0
        r = R()
        for d in list(self.docs):
            if all(d.get(k) == v for k, v in filt.items()):
                self.docs.remove(d)
                r.deleted_count += 1
                break
        return r

    async def delete_many(self, filt):
        class R:
            deleted_count = 0
        r = R()
        for d in list(self.docs):
            if not filt or all(d.get(k) == v for k, v in filt.items()):
                self.docs.remove(d)
                r.deleted_count += 1
        return r

    async def count_documents(self, filt):
        return len([d for d in self.docs if not filt or all(d.get(k) == v for k, v in filt.items())])


class _MockDB:
    def __init__(self):
        self.autocoder_file_cache = _MockCollection()
        self.autocoder_query_cache = _MockCollection()
        self.autocoder_cache_stats = _MockCollection()


@pytest.fixture()
def db():
    d = _MockDB()
    code_cache.bind_db(d)
    yield d


@pytest.fixture()
def tmp_file(tmp_path):
    p = tmp_path / "sample.py"
    p.write_text("def hello():\n    return 1\n", encoding="utf-8")
    return p


# ──────────────────────────────────────────────────────────────────────


def test_check_file_cache_miss_when_empty(db, tmp_file):
    res = asyncio.run(code_cache.check_file_cache(str(tmp_file)))
    assert res["cached"] is False
    assert res["reason"] == "no_entry"
    assert len(res["current_sha256"]) == 64


def test_upsert_and_hit(db, tmp_file):
    up = asyncio.run(code_cache.upsert_file_entry(str(tmp_file), summary="returns 1"))
    assert up["ok"] is True
    state = asyncio.run(code_cache.check_file_cache(str(tmp_file)))
    assert state["cached"] is True
    assert state["summary"] == "returns 1"


def test_invalidates_when_file_changes(db, tmp_file):
    asyncio.run(code_cache.upsert_file_entry(str(tmp_file), summary="v1"))
    tmp_file.write_text("def hello():\n    return 2\n", encoding="utf-8")
    state = asyncio.run(code_cache.check_file_cache(str(tmp_file)))
    assert state["cached"] is False
    assert state["reason"] == "changed"


def test_annotate_read_bumps_stats_on_miss(db, tmp_file):
    ann = asyncio.run(code_cache.annotate_read(str(tmp_file), 100))
    assert ann["cache"] == "MISS"
    stats = asyncio.run(code_cache.get_stats())
    assert stats["file_misses"] >= 1


def test_annotate_read_records_hit_after_cache(db, tmp_file):
    asyncio.run(code_cache.upsert_file_entry(str(tmp_file), summary="cached"))
    ann = asyncio.run(code_cache.annotate_read(str(tmp_file), 200))
    assert ann["cache"] == "HIT"
    assert ann["tokens_saved_now"] > 0
    stats = asyncio.run(code_cache.get_stats())
    assert stats["file_hits"] >= 1
    assert stats["total_tokens_saved"] >= ann["tokens_saved_now"]


def test_invalidate_file_removes_entry(db, tmp_file):
    asyncio.run(code_cache.upsert_file_entry(str(tmp_file), summary="x"))
    r = asyncio.run(code_cache.invalidate_file(str(tmp_file)))
    assert r["ok"] and r["deleted"] == 1
    state = asyncio.run(code_cache.check_file_cache(str(tmp_file)))
    assert state["cached"] is False


def test_save_query_and_find_exact_hash_hit(db):
    asyncio.run(code_cache.save_query_answer(
        "كيف يشتغل تسجيل الدخول؟",
        "JWT في localStorage.token. server.py /api/auth/*",
        files_used=["backend/server.py"],
        model="claude",
    ))
    hit = asyncio.run(code_cache.find_similar_query("كيف يشتغل تسجيل الدخول؟"))
    assert hit is not None
    assert hit["match_type"] == "exact"
    assert "JWT" in hit["answer"]


def test_find_similar_query_returns_none_without_embeddings_for_different_text(db):
    # No OpenAI key in test env → embed returns None; only exact match should hit
    os.environ.pop("OPENAI_DIRECT_KEY", None)
    os.environ.pop("OPENAI_API_KEY", None)
    asyncio.run(code_cache.save_query_answer(
        "أين توجد دالة تسجيل الدخول؟",
        "في backend/server.py عند /api/auth/login",
    ))
    hit = asyncio.run(code_cache.find_similar_query("وين أحصل تسجيل الدخول؟"))
    # Different wording, no embeddings → expect no hit
    assert hit is None


def test_clear_cache_all(db, tmp_file):
    asyncio.run(code_cache.upsert_file_entry(str(tmp_file), summary="x"))
    asyncio.run(code_cache.save_query_answer("q", "a"))
    r = asyncio.run(code_cache.clear_cache(scope="all"))
    assert r["ok"]
    assert r["deleted"]["files"] >= 1
    assert r["deleted"]["queries"] >= 1
    stats = asyncio.run(code_cache.get_stats())
    assert stats["files_cached"] == 0
    assert stats["queries_cached"] == 0


def test_tool_wrappers_shape(db, tmp_file):
    r = asyncio.run(code_cache.tool_cache_check_file(str(tmp_file)))
    assert r["ok"] is True and r["cached"] is False
    r = asyncio.run(code_cache.tool_cache_file_summary(str(tmp_file), summary="returns 1"))
    assert r["ok"] is True and r["summary_len"] == len("returns 1")
    r = asyncio.run(code_cache.tool_cache_stats())
    assert r["ok"] is True
    assert "total_tokens_saved" in r


def test_summarize_helpers(db):
    s = code_cache.cache_summarize("cache_stats", {
        "ok": True, "file_hits": 5, "file_misses": 2,
        "query_hits": 1, "query_misses": 0, "total_tokens_saved": 12345,
    })
    assert s and "saved" in s.lower()
