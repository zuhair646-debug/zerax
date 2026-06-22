"""Visual Diff + JS Sandbox + Safe Bash — final power tools.

These bring the unified AI to 100% feature parity with the developer
(within the multi-tenant security constraints).

  • capture_visual_snapshot(label) — Playwright screenshot + perceptual hash
  • compare_visuals(before_label, after_label) — pixel + structural diff
  • run_js_in_sandbox(code, timeout) — Node subprocess with strict limits
  • run_safe_bash(command) — whitelisted shell commands only
"""
import asyncio
import hashlib
import io
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("brain.advanced_tools")

# In-memory snapshot store per session (cleared on restart)
_SNAPSHOT_STORE: Dict[str, Dict[str, Any]] = {}


# ════════════════════════════════════════════════════════════════════════
# 1. Visual Snapshot (screenshot + perceptual hash)
# ════════════════════════════════════════════════════════════════════════
async def capture_visual_snapshot(
    project_id: str,
    label: str,
    base_url: str,
    timeout_seconds: int = 20,
) -> Dict[str, Any]:
    """Capture a screenshot + perceptual hash of the live preview.

    Stored under key f"{project_id}:{label}" so subsequent calls can
    compare. Returns:
      { ok, hash, png_size, label }
    """
    try:
        from playwright.async_api import async_playwright
        from PIL import Image
        import imagehash
    except ImportError as e:
        return {"ok": False, "error": f"missing dependency: {e}"}

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True,
            )
            page = await ctx.new_page()
            await page.goto(base_url, wait_until="networkidle",
                              timeout=timeout_seconds * 1000)
            await page.wait_for_timeout(800)
            png_bytes = await page.screenshot(full_page=True, type="png")
            await browser.close()
    except Exception as e:
        return {"ok": False, "error": f"playwright capture failed: {type(e).__name__}: {str(e)[:200]}"}

    img = Image.open(io.BytesIO(png_bytes))
    phash = str(imagehash.phash(img, hash_size=16))
    dhash = str(imagehash.dhash(img, hash_size=16))

    key = f"{project_id}:{label}"
    _SNAPSHOT_STORE[key] = {
        "phash": phash,
        "dhash": dhash,
        "png_size": len(png_bytes),
        "width": img.width,
        "height": img.height,
        "captured_at": time.time(),
        "label": label,
    }
    # Keep store size bounded
    if len(_SNAPSHOT_STORE) > 200:
        oldest = sorted(_SNAPSHOT_STORE.items(),
                         key=lambda kv: kv[1].get("captured_at", 0))[:50]
        for k, _ in oldest:
            _SNAPSHOT_STORE.pop(k, None)

    return {
        "ok": True,
        "label": label,
        "phash": phash,
        "dhash": dhash,
        "png_size": len(png_bytes),
        "dimensions": f"{img.width}x{img.height}",
        "message": f"📸 snapshot '{label}' captured ({len(png_bytes)//1024}KB)",
    }


# ════════════════════════════════════════════════════════════════════════
# 2. Compare Two Snapshots
# ════════════════════════════════════════════════════════════════════════
def compare_visuals(project_id: str, before_label: str,
                     after_label: str) -> Dict[str, Any]:
    """Compute perceptual-hash distance between two stored snapshots.

    Returns:
      { ok, hamming_distance, similarity_pct, verdict, recommendation }

    Verdict thresholds:
      • similarity ≥ 95%  → "minor_tweak"
      • similarity 70-94% → "moderate_change"
      • similarity 40-69% → "major_redesign"  ⚠️
      • similarity < 40%  → "complete_replacement"  🚨
    """
    try:
        import imagehash
    except ImportError as e:
        return {"ok": False, "error": f"imagehash missing: {e}"}

    before = _SNAPSHOT_STORE.get(f"{project_id}:{before_label}")
    after = _SNAPSHOT_STORE.get(f"{project_id}:{after_label}")
    if not before:
        return {"ok": False, "error": f"snapshot '{before_label}' not found",
                "available": [k.split(":", 1)[1] for k in _SNAPSHOT_STORE.keys()
                              if k.startswith(f"{project_id}:")]}
    if not after:
        return {"ok": False, "error": f"snapshot '{after_label}' not found"}

    h1 = imagehash.hex_to_hash(before["phash"])
    h2 = imagehash.hex_to_hash(after["phash"])
    hamming = h1 - h2
    # phash hash_size=16 → 256-bit hash → max distance 256
    max_dist = 256
    similarity = max(0.0, 1.0 - (hamming / max_dist))
    similarity_pct = round(similarity * 100, 1)

    if similarity >= 0.95:
        verdict = "minor_tweak"
        recommendation = "✅ تغيير طفيف، آمن"
    elif similarity >= 0.70:
        verdict = "moderate_change"
        recommendation = "🟡 تغيير معتدل، راجع الاختلاف"
    elif similarity >= 0.40:
        verdict = "major_redesign"
        recommendation = (
            "⚠️ إعادة تصميم كبيرة! لو العميل ما طلب إعادة تصميم، "
            "استدع restore_snapshot فوراً."
        )
    else:
        verdict = "complete_replacement"
        recommendation = (
            "🚨 الموقع تغيّر تماماً. هذي شبه أكيد كارثة. "
            "استدع restore_snapshot فوراً قبل ما يفقد العميل ثقته."
        )

    return {
        "ok": True,
        "before_label": before_label,
        "after_label": after_label,
        "hamming_distance": int(hamming),
        "similarity_pct": similarity_pct,
        "verdict": verdict,
        "recommendation": recommendation,
        "summary": (
            f"🔍 التشابه البصري {similarity_pct}% — {verdict}. {recommendation}"
        ),
    }


# ════════════════════════════════════════════════════════════════════════
# 3. JS Sandbox (Node subprocess with strict limits)
# ════════════════════════════════════════════════════════════════════════
def run_js_in_sandbox(code: str, timeout_seconds: int = 5,
                      max_output_bytes: int = 50_000) -> Dict[str, Any]:
    """Execute arbitrary JavaScript in an isolated Node subprocess.

    Safety:
      • subprocess timeout (default 5s)
      • output truncated at 50KB
      • runs in a temp dir (no access to /app source)
      • no network env vars
      • no access to MongoDB/secrets

    NOT bulletproof — for true isolation use Docker in production. Good
    enough for AI-generated test scripts.
    """
    if not code or len(code) > 100_000:
        return {"ok": False, "error": "code is empty or too large (>100KB)"}
    if not shutil.which("node"):
        return {"ok": False, "error": "node not installed on this system"}
    # Refuse dangerous patterns at the regex level (cheap defense)
    forbidden = (
        "require(\"fs\")", "require('fs')", "require(\"child_process\")",
        "require('child_process')", "process.env", "require('os')",
        "require(\"os\")", "require('net')", "require(\"net\")",
        "require('http')", "require(\"http\")", "require('https')",
        "require(\"https\")",
    )
    for f in forbidden:
        if f in code:
            return {"ok": False, "error": f"forbidden module/access: {f}"}

    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "user_script.js")
        with open(script_path, "w") as f:
            f.write(code)
        clean_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": tmpdir,
            "TMPDIR": tmpdir,
        }
        try:
            proc = subprocess.run(
                ["node", "--max-old-space-size=128", script_path],
                cwd=tmpdir,
                env=clean_env,
                capture_output=True,
                timeout=timeout_seconds,
                text=True,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"timeout after {timeout_seconds}s",
                    "killed": True}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}

    stdout = (proc.stdout or "")[:max_output_bytes]
    stderr = (proc.stderr or "")[:max_output_bytes]
    return {
        "ok": proc.returncode == 0,
        "stdout": stdout,
        "stderr": stderr,
        "return_code": proc.returncode,
        "summary": (
            f"✅ JS تنفّذ بنجاح (stdout={len(stdout)}b)"
            if proc.returncode == 0
            else f"❌ JS فشل (code={proc.returncode}): {stderr[:150]}"
        ),
    }


# ════════════════════════════════════════════════════════════════════════
# 4. Safe Bash (whitelisted commands only)
# ════════════════════════════════════════════════════════════════════════
SAFE_BASH_WHITELIST = {
    # Read-only inspection commands
    "ls", "pwd", "echo", "cat", "head", "tail", "grep", "find",
    "wc", "sort", "uniq", "cut", "awk", "sed", "tr",
    # Network probes (limited)
    "curl", "wget", "ping",
    # Version checks
    "node", "npm", "python3", "pip",
    # Git read-only
    "git",
    # System info
    "date", "hostname", "uname", "df", "free", "uptime",
    # File ops in temp/project dir only
    "mkdir", "touch", "cp",
}

# Hard blocks even within whitelisted commands
HARD_BLOCK_PATTERNS = (
    "rm ", "rmdir ", "shred ", "dd ", "mkfs",
    " > /etc/", " > /root/", " > /app/",
    "chmod 777", "chmod -R 777", "sudo ", "su -",
    "wget http", "curl ftp",  # exfil-likely patterns
    "ssh ", "scp ", "rsync ",
    "&&", "||", ";", "|", "$(", "`", "\n",  # chained commands forbidden
    "/etc/passwd", "/etc/shadow", "/.ssh/",
    "MONGO_URL", "EMERGENT_LLM_KEY", ".env",
)


def run_safe_bash(command: str, timeout_seconds: int = 8) -> Dict[str, Any]:
    """Execute a SINGLE whitelisted bash command. No pipes, no chains,
    no destructive ops. For audit-able read-mostly operations only.

    For full bash access: route through a Docker sandbox (not implemented
    in this layer to avoid multi-tenant risk).
    """
    cmd = (command or "").strip()
    if not cmd:
        return {"ok": False, "error": "empty command"}
    if len(cmd) > 2000:
        return {"ok": False, "error": "command too long"}

    # Block any compound/chained command
    for bad in HARD_BLOCK_PATTERNS:
        if bad in cmd:
            return {"ok": False, "error": f"forbidden pattern: {bad!r}"}

    parts = cmd.split()
    if not parts:
        return {"ok": False, "error": "empty command"}
    head = parts[0]
    if head not in SAFE_BASH_WHITELIST:
        return {"ok": False,
                "error": f"command '{head}' not in whitelist",
                "whitelist": sorted(SAFE_BASH_WHITELIST)}

    try:
        proc = subprocess.run(
            parts,
            capture_output=True,
            timeout=timeout_seconds,
            text=True,
            cwd="/tmp",
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                  "HOME": "/tmp"},
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout_seconds}s"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}

    out = (proc.stdout or "")[:20_000]
    err = (proc.stderr or "")[:10_000]
    return {
        "ok": proc.returncode == 0,
        "stdout": out,
        "stderr": err,
        "return_code": proc.returncode,
        "command": cmd,
        "summary": (
            f"✅ executed: {head} (return={proc.returncode})"
            if proc.returncode == 0
            else f"❌ failed: {err[:150]}"
        ),
    }
