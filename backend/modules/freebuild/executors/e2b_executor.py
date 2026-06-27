"""
🔬 E2B Sandbox Executor — runs ANY code (including Docker compose, GPU,
long-running) in a real isolated VM via E2B's API.

When to use:
  - Code needs network access we can't permit locally
  - Code needs Docker/postgres/redis (i.e. full VM)
  - Long-running tasks (>5 min)
  - GPU workloads

Cost: ~$0.001/second. We can charge customer or absorb.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("zenrex.e2b")

_E2B_API = "https://api.e2b.dev"


async def create_sandbox(api_key: str, template: str = "base", timeout_min: int = 10) -> Optional[Dict[str, Any]]:
    """Create a new sandbox. Returns {sandbox_id, url}."""
    try:
        async with httpx.AsyncClient(timeout=30) as cl:
            r = await cl.post(
                f"{_E2B_API}/sandboxes",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                json={"templateID": template, "timeout": timeout_min * 60},
            )
        if r.status_code in (200, 201):
            return r.json()
        return {"error": f"HTTP {r.status_code}", "body": r.text[:300]}
    except Exception as e:
        return {"error": str(e)}


async def run_command(api_key: str, sandbox_id: str, cmd: str, cwd: str = "/home/user") -> Dict[str, Any]:
    """Run a shell command inside a sandbox."""
    try:
        async with httpx.AsyncClient(timeout=120) as cl:
            r = await cl.post(
                f"{_E2B_API}/sandboxes/{sandbox_id}/process",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                json={"cmd": cmd, "cwd": cwd},
            )
        if r.status_code in (200, 201):
            return r.json()
        return {"ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def write_file(api_key: str, sandbox_id: str, path: str, content: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=30) as cl:
            r = await cl.put(
                f"{_E2B_API}/sandboxes/{sandbox_id}/files",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                json={"path": path, "content": content},
            )
        return r.status_code in (200, 201, 204)
    except Exception:
        return False


async def kill_sandbox(api_key: str, sandbox_id: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=15) as cl:
            r = await cl.delete(f"{_E2B_API}/sandboxes/{sandbox_id}", headers={"X-API-Key": api_key})
        return r.status_code in (200, 204)
    except Exception:
        return False


async def run_full_workflow(
    api_key: str,
    files: Dict[str, str],
    commands: List[str],
    template: str = "base",
    timeout_min: int = 10,
) -> Dict[str, Any]:
    """High-level: create sandbox → write files → run commands → cleanup → return logs."""
    sandbox = await create_sandbox(api_key, template, timeout_min)
    if not sandbox or sandbox.get("error"):
        return {"ok": False, "error": (sandbox or {}).get("error", "sandbox creation failed")}
    sid = sandbox.get("sandboxID") or sandbox.get("id")
    if not sid:
        return {"ok": False, "error": "no sandbox_id returned"}
    logs = []
    try:
        for path, content in files.items():
            ok = await write_file(api_key, sid, path, content)
            if not ok:
                logs.append({"step": f"write {path}", "ok": False})
        for cmd in commands:
            result = await run_command(api_key, sid, cmd)
            logs.append({"step": cmd, **result})
        return {"ok": True, "sandbox_id": sid, "logs": logs}
    finally:
        await kill_sandbox(api_key, sid)
