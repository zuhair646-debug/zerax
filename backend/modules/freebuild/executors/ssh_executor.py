"""
🔌 SSH Remote Executor — run commands on customer's own VPS.

Customer provides SSH credentials (host + key OR password). We connect
via asyncssh and execute Docker / build / heavy workloads on their machine.

Credentials are stored in vault keyed by user_id.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("zenrex.ssh_executor")


async def test_connection(host: str, port: int, username: str,
                           password: Optional[str] = None,
                           private_key: Optional[str] = None) -> Dict[str, Any]:
    """Quick connectivity check. Returns {ok, message, os?}."""
    try:
        import asyncssh  # type: ignore
    except ImportError:
        return {"ok": False, "message": "asyncssh not installed (pip install asyncssh)"}

    try:
        opts = {"username": username, "known_hosts": None, "client_keys": None}
        if password:
            opts["password"] = password
        if private_key:
            opts["client_keys"] = [private_key]
        async with await asyncssh.connect(host, port=port, **opts) as conn:
            r = await conn.run("uname -a", check=False, timeout=10)
            return {"ok": True, "message": "متصل", "os": (r.stdout or "").strip()[:200]}
    except Exception as e:
        return {"ok": False, "message": f"خطأ: {type(e).__name__}: {str(e)[:200]}"}


async def run_remote(host: str, port: int, username: str,
                     command: str,
                     password: Optional[str] = None,
                     private_key: Optional[str] = None,
                     timeout: int = 300) -> Dict[str, Any]:
    """Execute a single command on remote. Returns {ok, stdout, stderr, exit_status}."""
    try:
        import asyncssh  # type: ignore
    except ImportError:
        return {"ok": False, "error": "asyncssh not installed"}

    try:
        opts = {"username": username, "known_hosts": None}
        if password: opts["password"] = password
        if private_key: opts["client_keys"] = [private_key]
        async with await asyncssh.connect(host, port=port, **opts) as conn:
            r = await conn.run(command, check=False, timeout=timeout)
            return {
                "ok": r.exit_status == 0,
                "exit_status": r.exit_status,
                "stdout": (r.stdout or "")[:8000],
                "stderr": (r.stderr or "")[:4000],
            }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"}


async def run_workflow(host: str, port: int, username: str,
                        commands: list,
                        password: Optional[str] = None,
                        private_key: Optional[str] = None) -> Dict[str, Any]:
    """Run multiple commands sequentially on remote. Stops on first failure."""
    results = []
    for cmd in commands:
        r = await run_remote(host, port, username, cmd, password, private_key)
        results.append({"command": cmd, **r})
        if not r.get("ok"):
            return {"ok": False, "results": results, "failed_at": cmd}
    return {"ok": True, "results": results}
