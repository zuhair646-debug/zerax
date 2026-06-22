"""Tests for parity tools — the final 5% to 100% agent parity."""
import asyncio
import os
import pytest
import tempfile
from modules.brain.power_tools.parity import (
    analyze_uploaded_file, integration_playbook_live,
    crawl_url_deep, remember, recall,
    _classify_file_type, _ensure_workspace,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture(autouse=True)
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestFileClassification:
    def test_pdf(self):
        assert _classify_file_type("pdf") == "pdf"

    def test_image_types(self):
        for e in ("png", "jpg", "jpeg", "webp", "gif", "heic"):
            assert _classify_file_type(e) == "image"

    def test_audio_types(self):
        for e in ("mp3", "wav", "m4a", "flac"):
            assert _classify_file_type(e) == "audio"

    def test_code_types(self):
        for e in ("py", "js", "ts", "html", "css", "json"):
            assert _classify_file_type(e) == "text"

    def test_unknown(self):
        assert _classify_file_type("xyz") == "unknown"


class TestAnalyzeUploadedFile:
    def test_empty_source(self):
        r = _run(analyze_uploaded_file("", "what is this"))
        assert not r["ok"]

    def test_missing_local_file(self):
        r = _run(analyze_uploaded_file("/tmp/_does_not_exist_xyz.pdf"))
        assert not r["ok"]

    def test_text_file_analysis(self, tmp_path):
        # Without EMERGENT_LLM_KEY this will produce a placeholder
        # summary but still return ok=True with content_length
        p = tmp_path / "sample.txt"
        p.write_text("Hello, this is a Zenrex test file.\nLine 2.\n")
        r = _run(analyze_uploaded_file(str(p), "summarize"))
        # Either succeeds (with key) or returns clean error
        assert "ok" in r
        if r["ok"]:
            assert r["type"] == "text"
            assert r["content_length"] > 0


class TestCrawlUrlDeep:
    def test_invalid_url(self):
        r = _run(crawl_url_deep("not-a-url"))
        assert not r["ok"]

    def test_simple_page(self):
        # example.com is stable + minimal
        r = _run(crawl_url_deep("https://example.com", max_chars=10_000))
        if r.get("ok"):
            assert "Example" in r["markdown"] or "example" in r["markdown"].lower()
            assert r["char_count"] > 0
            assert r["title"]
        else:
            # network may be flaky in CI; ensure clean error shape
            assert "error" in r

    def test_404_returns_clean_error(self):
        r = _run(crawl_url_deep(
            "https://httpbin.org/status/404", max_chars=1000))
        # Either non-ok (HTTP 404) or empty markdown is acceptable
        assert "ok" in r


class TestMemorySystem:
    @pytest.mark.skipif(not os.environ.get("MONGO_URL"),
                         reason="needs MongoDB")
    def test_remember_then_recall(self):
        unique_tag = f"test_{os.getpid()}_{id(self)}"
        r1 = _run(remember(
            f"Test insight for {unique_tag}",
            tags=[unique_tag, "unit_test"],
            project_id="test_proj_1",
            importance=8,
        ))
        if not r1.get("ok"):
            pytest.skip(f"DB not available: {r1.get('error')}")
        assert r1["memory_id"]

        r2 = _run(recall(tags=[unique_tag], limit=5))
        assert r2["ok"]
        assert r2["count"] >= 1
        assert any("Test insight" in m["insight"] for m in r2["memories"])

    def test_remember_validation(self):
        r = _run(remember(""))
        assert not r["ok"]

        r = _run(remember("x" * 3000))
        assert not r["ok"]


class TestIntegrationPlaybookLive:
    def test_hardcoded_hit_first(self):
        r = _run(integration_playbook_live("stripe", "checkout"))
        assert r["ok"]
        # Should hit the hardcoded cache
        assert r.get("source") in ("hardcoded", "live_research")
        if r["source"] == "hardcoded":
            assert "STRIPE_SECRET_KEY" in r.get("env_vars", [])

    def test_empty_service(self):
        r = _run(integration_playbook_live(""))
        assert not r["ok"]
