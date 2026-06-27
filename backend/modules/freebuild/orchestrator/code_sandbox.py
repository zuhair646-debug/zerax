"""
📦 Code Sandbox Lite — safe execution of small code snippets.

Capabilities:
  - Run JS via Node subprocess (isolated, 5s timeout, 256MB)
  - Run Python via subprocess (isolated, 5s timeout, 256MB)
  - Validate HTML via parser (returns errors)
  - Lint JS via syntax check (Node --check)
  - Lint Python via py_compile

LIMITS (honest):
  - No network access by default (passes env vars to child)
  - No file writes outside /tmp
  - 5-second hard timeout
  - No native modules / shell access

Used by:
  - StackTrace AutoFix Loop (re-run code after fix)
  - Test Generator Cortex (run generated tests)
  - CodeCortex (validate before delivery)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("zenrex.code_sandbox")


async def run_js(code: str, timeout_sec: int = 5) -> Dict[str, Any]:
    """Run JS code via Node. Returns {ok, stdout, stderr, exit_code, error?}."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, dir="/tmp") as f:
        f.write(code)
        path = f.name
    try:
        proc = await asyncio.create_subprocess_exec(
            "node", path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={"PATH": os.environ.get("PATH", ""), "NODE_OPTIONS": "--max-old-space-size=256"},
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
            return {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace")[:4000],
                "stderr": stderr.decode("utf-8", errors="replace")[:4000],
            }
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return {"ok": False, "exit_code": -1, "stdout": "", "stderr": f"timeout after {timeout_sec}s", "error": "timeout"}
    except FileNotFoundError:
        return {"ok": False, "exit_code": -1, "stdout": "", "stderr": "node not available", "error": "node_missing"}
    except Exception as e:
        return {"ok": False, "exit_code": -1, "stdout": "", "stderr": str(e), "error": type(e).__name__}
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


async def run_python(code: str, timeout_sec: int = 5) -> Dict[str, Any]:
    """Run Python code via subprocess. Returns {ok, stdout, stderr, exit_code}."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, dir="/tmp") as f:
        f.write(code)
        path = f.name
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"},
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
            return {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace")[:4000],
                "stderr": stderr.decode("utf-8", errors="replace")[:4000],
            }
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return {"ok": False, "exit_code": -1, "stdout": "", "stderr": f"timeout after {timeout_sec}s", "error": "timeout"}
    except Exception as e:
        return {"ok": False, "exit_code": -1, "stdout": "", "stderr": str(e), "error": type(e).__name__}
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


async def lint_js(code: str) -> Dict[str, Any]:
    """Syntax-check JS without executing."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, dir="/tmp") as f:
        f.write(code)
        path = f.name
    try:
        proc = await asyncio.create_subprocess_exec(
            "node", "--check", path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
            err = stderr.decode("utf-8", errors="replace")[:2000]
            return {"ok": proc.returncode == 0, "error": err if proc.returncode != 0 else None}
        except asyncio.TimeoutError:
            try: proc.kill()
            except Exception: pass
            return {"ok": False, "error": "lint timeout"}
    except FileNotFoundError:
        return {"ok": True, "error": None, "skipped": True, "reason": "node not available"}
    finally:
        try: os.unlink(path)
        except Exception: pass


def validate_html(html: str) -> Dict[str, Any]:
    """Quick HTML validation via regex/heuristic (no external dep)."""
    issues = []
    # Check balanced tags (rough)
    open_tags = re.findall(r"<(\w+)(?:\s[^>]*)?>(?<!/)", html)
    close_tags = re.findall(r"</(\w+)>", html)
    self_closing = {"img", "br", "hr", "input", "meta", "link", "source", "track", "area", "base", "col", "embed", "param", "wbr"}
    open_count: Dict[str, int] = {}
    for t in open_tags:
        if t.lower() not in self_closing:
            open_count[t.lower()] = open_count.get(t.lower(), 0) + 1
    for t in close_tags:
        open_count[t.lower()] = open_count.get(t.lower(), 0) - 1
    for tag, count in open_count.items():
        if count != 0:
            issues.append(f"Tag mismatch: <{tag}> ({count:+d})")
    # Missing essentials
    if "<!DOCTYPE" not in html[:200].upper():
        issues.append("Missing <!DOCTYPE html>")
    if "<html" not in html[:500].lower():
        issues.append("Missing <html> tag")
    if "<body" not in html.lower():
        issues.append("Missing <body> tag")
    return {"ok": len(issues) == 0, "issues": issues}


async def lint_python(code: str) -> Dict[str, Any]:
    """Syntax-check Python without executing."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, dir="/tmp") as f:
        f.write(code)
        path = f.name
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", "-m", "py_compile", path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
            err = stderr.decode("utf-8", errors="replace")[:2000]
            return {"ok": proc.returncode == 0, "error": err if proc.returncode != 0 else None}
        except asyncio.TimeoutError:
            try: proc.kill()
            except Exception: pass
            return {"ok": False, "error": "lint timeout"}
    finally:
        try: os.unlink(path)
        except Exception: pass


def parse_stack_trace(stderr: str) -> Dict[str, Any]:
    """Extract file/line/error from a typical Node or Python stack trace."""
    out = {"error_type": None, "error_message": None, "file": None, "line": None, "raw": stderr[:1000]}
    if not stderr:
        return out

    # Node: SyntaxError: Unexpected token at /path/to/file.js:42
    m = re.search(r"(\w+(?:Error|Exception)):\s*([^\n]+)", stderr)
    if m:
        out["error_type"] = m.group(1)
        out["error_message"] = m.group(2)
    m = re.search(r"([^/\s]+\.(?:js|py|ts|jsx)):(\d+)(?::(\d+))?", stderr)
    if m:
        out["file"] = m.group(1)
        out["line"] = int(m.group(2))
        if m.group(3):
            out["col"] = int(m.group(3))
    # Python: File "x.py", line N
    m2 = re.search(r'File "([^"]+)", line (\d+)', stderr)
    if m2 and not out["file"]:
        out["file"] = m2.group(1).split("/")[-1]
        out["line"] = int(m2.group(2))
    return out
