"""Tests for unrestricted power tools — full agent parity."""
import asyncio
import os
import pytest
from modules.brain.power_tools.unrestricted import (
    run_bash_unrestricted, run_python_in_sandbox,
    read_any_file, write_any_file, edit_file,
    web_search, get_integration_playbook,
    _check_catastrophe, _redact_secrets, _ensure_workspace,
    CATASTROPHE_PATTERNS, INTEGRATION_PLAYBOOKS,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture(autouse=True)
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestCatastropheBlocker:
    def test_rm_rf_root_blocked(self):
        assert _check_catastrophe("rm -rf /") is not None
        assert _check_catastrophe("rm -rf /*") is not None
        assert _check_catastrophe("rm -rf /etc") is not None
        assert _check_catastrophe("rm -rf /opt/zerax") is not None

    def test_mkfs_blocked(self):
        assert _check_catastrophe("mkfs.ext4 /dev/sda1") is not None

    def test_fork_bomb_blocked(self):
        assert _check_catastrophe(":(){ :|:& };:") is not None

    def test_shutdown_blocked(self):
        assert _check_catastrophe("shutdown -h now") is not None

    def test_dd_to_disk_blocked(self):
        assert _check_catastrophe("dd if=/dev/zero of=/dev/sda") is not None

    def test_normal_commands_allowed(self):
        for safe in [
            "ls -la /tmp",
            "rm /tmp/myfile.txt",
            "rm -rf /tmp/myproject",  # not /
            "find . -name '*.py' | xargs grep TODO",
            "git clone https://github.com/x/y.git",
            "npm install && npm run build",
            "python3 -c 'print(1)'",
            "curl https://api.github.com",
        ]:
            assert _check_catastrophe(safe) is None, f"falsely blocked: {safe}"


class TestSecretRedaction:
    def test_redacts_mongo_url(self):
        text = "MONGO_URL=mongodb://user:pass@host\nFoo=bar"
        out = _redact_secrets(text)
        assert "REDACTED" in out
        assert "Foo=bar" in out

    def test_redacts_emergent_llm_key(self):
        out = _redact_secrets("EMERGENT_LLM_KEY=sk-emergent-xxx")
        assert "REDACTED" in out
        assert "sk-emergent-xxx" not in out

    def test_no_secret_no_redact(self):
        text = "hello world\nfoo=bar"
        assert _redact_secrets(text) == text


class TestRunBashUnrestricted:
    def test_simple_command(self):
        r = _run(run_bash_unrestricted("test1", "echo hello"))
        assert r["ok"]
        assert "hello" in r["stdout"]

    def test_pipes_allowed(self):
        r = _run(run_bash_unrestricted("test1", "echo 'a\\nb\\nc' | grep b"))
        assert r["ok"]
        assert "b" in r["stdout"]

    def test_chains_allowed(self):
        r = _run(run_bash_unrestricted("test1", "echo first && echo second"))
        assert r["ok"]
        assert "first" in r["stdout"] and "second" in r["stdout"]

    def test_catastrophe_blocked(self):
        r = _run(run_bash_unrestricted("test1", "rm -rf /"))
        assert not r["ok"]
        assert "catastrophe" in r["error"].lower()

    def test_workspace_isolated(self):
        # Each project gets its own dir
        ws1 = _ensure_workspace("proj_a")
        ws2 = _ensure_workspace("proj_b")
        assert ws1 != ws2
        assert os.path.isdir(ws1) and os.path.isdir(ws2)


class TestPythonSandbox:
    def test_basic_python(self):
        r = _run(run_python_in_sandbox("t1", "print(2+3)"))
        assert r["ok"]
        assert "5" in r["stdout"]

    def test_stdlib_works(self):
        code = """
import json, re
data = {'name':'zenrex','count':42}
print(json.dumps(data))
print(re.findall(r'\\d+', 'a1b22c333'))
"""
        r = _run(run_python_in_sandbox("t1", code))
        assert r["ok"]
        assert "zenrex" in r["stdout"]
        assert "['1', '22', '333']" in r["stdout"]

    def test_timeout(self):
        r = _run(run_python_in_sandbox("t1", "while True: pass",
                                         timeout_seconds=2))
        assert not r["ok"]


class TestFileOps:
    def test_write_read_cycle(self, tmp_path):
        path = str(tmp_path / "hello.txt")
        wr = _run(write_any_file("t1", path, "world"))
        assert wr["ok"]
        rr = _run(read_any_file("t1", path))
        assert rr["ok"]
        assert rr["content"] == "world"

    def test_env_write_blocked(self, tmp_path):
        path = str(tmp_path / ".env")
        r = _run(write_any_file("t1", path, "SECRET=xxx"))
        assert not r["ok"]

    def test_backup_on_overwrite(self, tmp_path):
        path = str(tmp_path / "f.txt")
        _run(write_any_file("t1", path, "v1"))
        r = _run(write_any_file("t1", path, "v2"))
        assert r["ok"]
        assert r["backup_path"]
        assert os.path.exists(r["backup_path"])

    def test_edit_file_simple(self, tmp_path):
        path = str(tmp_path / "x.txt")
        _run(write_any_file("t1", path, "hello world"))
        r = _run(edit_file("t1", path, "world", "zenrex"))
        assert r["ok"]
        rr = _run(read_any_file("t1", path))
        assert rr["content"] == "hello zenrex"

    def test_edit_ambiguous_match(self, tmp_path):
        path = str(tmp_path / "y.txt")
        _run(write_any_file("t1", path, "a a a"))
        r = _run(edit_file("t1", path, "a", "b"))
        assert not r["ok"]  # multiple matches without replace_all
        r2 = _run(edit_file("t1", path, "a", "b", replace_all=True))
        assert r2["ok"]


class TestIntegrationPlaybook:
    def test_stripe(self):
        r = get_integration_playbook("stripe")
        assert r["ok"]
        assert "STRIPE_SECRET_KEY" in r["env_vars"]
        assert "import stripe" in r["backend_snippet"]

    def test_alias(self):
        r1 = get_integration_playbook("gpt-5")
        assert r1["ok"]
        assert r1 == get_integration_playbook("openai")

    def test_unknown(self):
        r = get_integration_playbook("nonexistent_service")
        assert not r["ok"]
        assert "available" in r


class TestWebSearch:
    def test_search_returns_results(self):
        # Network test — may flake. Just check shape.
        r = _run(web_search("python asyncio docs", num_results=3))
        if r.get("ok"):
            assert isinstance(r["results"], list)
            assert len(r["results"]) > 0
            for item in r["results"]:
                assert "title" in item
                assert "url" in item
        else:
            # Network failure is acceptable in CI; just don't crash
            assert "error" in r
