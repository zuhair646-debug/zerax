"""Iteration 58 — End-to-end verification of the 3-mode AI router (claude_only,
hybrid_gpt, hybrid_glm) plus legacy 'hybrid' alias on both READ and WRITE.

Covers explicit review-request items:
  • Legacy alias on READ: db stores {mode:'hybrid'} → get_ai_mode → 'hybrid_gpt'
  • Legacy alias on WRITE: set_ai_mode(db,'hybrid') → persists as 'hybrid_gpt'
  • PUT /api/admin/ai-mode {mode:'hybrid_glm'} → 200, persisted
  • PUT /api/admin/ai-mode {mode:'hybrid'} → 200 + migrated to 'hybrid_gpt'
  • PUT /api/admin/ai-mode {mode:'foobar'} → 400
  • Cross-key isolation: hybrid_gpt with only ZHIPU_API_KEY → falls back to Claude
  • Source introspection: providers chain + zhipu_glm AsyncOpenAI base_url
"""
from __future__ import annotations
import os
import re
import asyncio
import pytest
import requests

import sys
sys.path.insert(0, "/app")

from backend.modules.freebuild.ai_mode import (
    get_ai_mode,
    set_ai_mode,
    pick_provider,
    VALID_MODES,
    LEGACY_HYBRID_ALIAS,
    CLAUDE_PROVIDER,
    GLM_PROVIDER,
    GLM_MODEL,
    PHASE_FIRST_DESIGN,
    SETTINGS_COLLECTION,
    SETTINGS_DOC_ID,
)

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-cinematic-hub-2.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
OWNER_EMAIL = "owner@zerax.com"
OWNER_PASS = "owner123"


# ─── In-memory fake DB for legacy-alias logic tests ─────────────────────────

class _FakeCollection:
    def __init__(self, store):
        self._store = store

    async def find_one(self, q):
        _id = q.get("_id")
        return self._store.get(_id)

    async def update_one(self, q, update, upsert=False):
        _id = q.get("_id")
        if "$set" in update:
            doc = self._store.get(_id, {"_id": _id})
            doc.update(update["$set"])
            self._store[_id] = doc


class _FakeDB:
    def __init__(self):
        self._store = {}

    def __getitem__(self, name):
        assert name == SETTINGS_COLLECTION
        return _FakeCollection(self._store)


# ─── Legacy alias: READ path ────────────────────────────────────────────────

def test_legacy_hybrid_on_read_is_migrated_to_hybrid_gpt():
    db = _FakeDB()
    # Simulate a pre-GLM admin save: raw 'hybrid' in the DB
    db._store[SETTINGS_DOC_ID] = {"_id": SETTINGS_DOC_ID, "mode": LEGACY_HYBRID_ALIAS}
    result = asyncio.run(get_ai_mode(db))
    assert result == "hybrid_gpt", f"Legacy 'hybrid' must auto-migrate to 'hybrid_gpt' on read, got {result!r}"


def test_existing_hybrid_gpt_in_db_passes_through():
    db = _FakeDB()
    db._store[SETTINGS_DOC_ID] = {"_id": SETTINGS_DOC_ID, "mode": "hybrid_gpt"}
    assert asyncio.run(get_ai_mode(db)) == "hybrid_gpt"


def test_existing_hybrid_glm_in_db_passes_through():
    db = _FakeDB()
    db._store[SETTINGS_DOC_ID] = {"_id": SETTINGS_DOC_ID, "mode": "hybrid_glm"}
    assert asyncio.run(get_ai_mode(db)) == "hybrid_glm"


def test_missing_doc_defaults_to_claude_only():
    db = _FakeDB()
    assert asyncio.run(get_ai_mode(db)) == "claude_only"


def test_unknown_mode_in_db_falls_back_to_default():
    db = _FakeDB()
    db._store[SETTINGS_DOC_ID] = {"_id": SETTINGS_DOC_ID, "mode": "garbage"}
    assert asyncio.run(get_ai_mode(db)) == "claude_only"


# ─── Legacy alias: WRITE path ───────────────────────────────────────────────

def test_legacy_hybrid_on_write_persists_as_hybrid_gpt():
    db = _FakeDB()
    asyncio.run(set_ai_mode(db, LEGACY_HYBRID_ALIAS))
    stored = db._store[SETTINGS_DOC_ID]["mode"]
    assert stored == "hybrid_gpt", f"Write of legacy 'hybrid' must store 'hybrid_gpt', got {stored!r}"


def test_set_hybrid_glm_persists_unchanged():
    db = _FakeDB()
    asyncio.run(set_ai_mode(db, "hybrid_glm"))
    assert db._store[SETTINGS_DOC_ID]["mode"] == "hybrid_glm"


def test_set_invalid_mode_raises_value_error():
    db = _FakeDB()
    with pytest.raises(ValueError):
        asyncio.run(set_ai_mode(db, "foobar"))


# ─── Cross-key isolation (review-request critical item) ─────────────────────

def test_hybrid_gpt_with_only_zhipu_key_falls_back_to_claude(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", "zhipu-fake")
    monkeypatch.delenv("OPENAI_DIRECT_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    prov, _ = pick_provider("hybrid_gpt", PHASE_FIRST_DESIGN)
    assert prov == CLAUDE_PROVIDER, "hybrid_gpt must NOT silently use GLM"


def test_hybrid_glm_with_only_openai_key_falls_back_to_claude(monkeypatch):
    monkeypatch.setenv("OPENAI_DIRECT_KEY", "sk-fake")
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
    prov, _ = pick_provider("hybrid_glm", PHASE_FIRST_DESIGN)
    assert prov == CLAUDE_PROVIDER, "hybrid_glm must NOT silently use GPT"


# ─── Source introspection: freebuild_agent.py ───────────────────────────────

def _agent_src() -> str:
    p = "/app/backend/modules/freebuild/freebuild_agent.py"
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def test_agent_providers_chain_handles_glm():
    src = _agent_src()
    assert "GLM_PROVIDER" in src
    assert "ZHIPU_API_KEY" in src
    assert re.search(r"_prov\s*==\s*GLM_PROVIDER", src), "providers chain must check _prov == GLM_PROVIDER"


def test_agent_stream_one_provider_handles_zhipu_glm_with_zai_base_url():
    src = _agent_src()
    assert 'provider == "zhipu_glm"' in src
    assert "base_url=\"https://api.z.ai/api/paas/v4/\"" in src, \
        "zhipu_glm branch must use the z.ai OpenAI-compatible base_url"


# ─── HTTP end-to-end against the real server ───────────────────────────────

@pytest.fixture(scope="module")
def owner_headers():
    try:
        r = requests.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASS}, timeout=45)
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Backend unreachable: {e}")
    if r.status_code != 200:
        pytest.skip(f"Owner login failed: {r.status_code} {r.text[:200]}")
    tok = r.json().get("token") or r.json().get("access_token")
    if not tok:
        pytest.skip("Owner token missing")
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def test_http_get_returns_valid_modes_with_three_entries(owner_headers):
    r = requests.get(f"{API}/admin/ai-mode", headers=owner_headers, timeout=45)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    assert sorted(data["valid_modes"]) == ["claude_only", "hybrid_glm", "hybrid_gpt"]
    assert data["mode"] in {"claude_only", "hybrid_gpt", "hybrid_glm"}


def test_http_put_hybrid_glm_persists(owner_headers):
    put = requests.put(f"{API}/admin/ai-mode", headers=owner_headers, json={"mode": "hybrid_glm"}, timeout=45)
    assert put.status_code == 200, put.text[:200]
    assert put.json().get("mode") == "hybrid_glm"
    get = requests.get(f"{API}/admin/ai-mode", headers=owner_headers, timeout=45)
    assert get.json().get("mode") == "hybrid_glm"


def test_http_put_legacy_hybrid_migrates_to_hybrid_gpt(owner_headers):
    """Critical: PUT {mode:'hybrid'} must succeed (200) and persist as 'hybrid_gpt'."""
    put = requests.put(f"{API}/admin/ai-mode", headers=owner_headers, json={"mode": "hybrid"}, timeout=45)
    assert put.status_code == 200, f"Legacy alias 'hybrid' must be accepted on PUT, got {put.status_code} {put.text[:200]}"
    body = put.json()
    assert body.get("mode") == "hybrid_gpt", \
        f"Legacy 'hybrid' must be migrated to 'hybrid_gpt' on write, got {body.get('mode')!r}"
    get = requests.get(f"{API}/admin/ai-mode", headers=owner_headers, timeout=45)
    assert get.json().get("mode") == "hybrid_gpt", "After PUT 'hybrid', GET must return 'hybrid_gpt'"


def test_http_put_invalid_mode_returns_400(owner_headers):
    r = requests.put(f"{API}/admin/ai-mode", headers=owner_headers, json={"mode": "foobar"}, timeout=45)
    assert r.status_code == 400, f"Expected 400, got {r.status_code} {r.text[:200]}"


def test_http_zz_reset_to_claude_only(owner_headers):
    r = requests.put(f"{API}/admin/ai-mode", headers=owner_headers, json={"mode": "claude_only"}, timeout=45)
    assert r.status_code == 200
    assert r.json().get("mode") == "claude_only"
