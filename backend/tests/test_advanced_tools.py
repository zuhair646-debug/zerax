"""Tests for advanced power tools: visual diff, JS sandbox, safe bash."""
import pytest
from modules.brain.power_tools import (
    compare_visuals, run_js_in_sandbox, run_safe_bash,
)
from modules.brain.power_tools.advanced import _SNAPSHOT_STORE


class TestVisualDiff:
    def test_identical_snapshots_high_similarity(self):
        _SNAPSHOT_STORE["p1:a"] = {"phash": "0" * 64, "dhash": "0" * 64,
                                    "captured_at": 1}
        _SNAPSHOT_STORE["p1:b"] = {"phash": "0" * 64, "dhash": "0" * 64,
                                    "captured_at": 2}
        r = compare_visuals("p1", "a", "b")
        assert r["ok"]
        assert r["similarity_pct"] == 100.0
        assert r["verdict"] == "minor_tweak"

    def test_totally_different_snapshots(self):
        _SNAPSHOT_STORE["p2:a"] = {"phash": "0" * 64, "dhash": "0" * 64,
                                    "captured_at": 1}
        _SNAPSHOT_STORE["p2:b"] = {"phash": "f" * 64, "dhash": "f" * 64,
                                    "captured_at": 2}
        r = compare_visuals("p2", "a", "b")
        assert r["ok"]
        assert r["similarity_pct"] < 50.0
        assert r["verdict"] in ("major_redesign", "complete_replacement")

    def test_missing_snapshot(self):
        r = compare_visuals("p99", "nonexistent_a", "nonexistent_b")
        assert not r["ok"]


class TestJSSandbox:
    def test_simple_logic_works(self):
        r = run_js_in_sandbox("console.log(1 + 2);")
        assert r["ok"]
        assert "3" in r["stdout"]

    def test_cart_logic_works(self):
        code = """
        function addToCart(cart, item) { cart.push(item); return cart.length; }
        console.log(addToCart([], {id: 1}));
        console.log(addToCart([{id:1}], {id: 2}));
        """
        r = run_js_in_sandbox(code)
        assert r["ok"]
        assert "1" in r["stdout"]
        assert "2" in r["stdout"]

    def test_forbidden_fs_blocked(self):
        r = run_js_in_sandbox("require('fs').readFileSync('/etc/passwd');")
        assert not r["ok"]
        assert "forbidden" in r["error"].lower()

    def test_timeout(self):
        r = run_js_in_sandbox("while(true){}", timeout_seconds=2)
        assert not r["ok"]
        assert r.get("killed") or "timeout" in r.get("error", "").lower()


class TestSafeBash:
    def test_simple_ls(self):
        r = run_safe_bash("ls /tmp")
        assert r["ok"]

    def test_rm_blocked(self):
        r = run_safe_bash("rm -rf /app")
        assert not r["ok"]
        assert "forbidden" in r["error"].lower()

    def test_chain_blocked(self):
        r = run_safe_bash("ls && cat /etc/passwd")
        assert not r["ok"]
        assert "forbidden" in r["error"].lower()

    def test_pipe_blocked(self):
        r = run_safe_bash("cat /tmp/file | grep secret")
        assert not r["ok"]

    def test_unknown_command_blocked(self):
        r = run_safe_bash("nmap -sV target.com")
        assert not r["ok"]

    def test_env_access_blocked(self):
        r = run_safe_bash("cat .env")
        assert not r["ok"]
