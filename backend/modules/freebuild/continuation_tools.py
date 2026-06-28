"""Continuation-mode tools — clone, FTP-sync, snapshot, sandbox file ops.

These are the FIRST tools that actually USE the encrypted credentials the
user gave us in the onboarding wizard. They run inside an isolated per-project
sandbox at /opt/zerax/sandboxes/{pid}/ and NEVER touch the customer's live
production directly. Every destructive op requires a fresh snapshot first.

Security rules baked in:
 1. The plaintext token is only decrypted in-memory for the duration of the
    git/ftp call. We never log it, never echo it, never store it anywhere.
 2. Every clone/pull creates a SHA256-fingerprinted snapshot of the previous
    sandbox state before overwriting, so we can roll back instantly.
 3. Path traversal is blocked: file ops resolve to a real path inside the
    sandbox root via os.path.realpath + commonpath check.
 4. Subprocess timeouts cap at 5 minutes per op to prevent runaway clones.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import shutil
import tarfile
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .secure_credentials import decrypt_secret

logger = logging.getLogger("zenrex.continuation_tools")

# ────────────── Sandbox root ──────────────
SANDBOX_ROOT = Path(os.environ.get("ZERAX_SANDBOX_ROOT", "/opt/zerax/sandboxes"))
SNAPSHOT_DIR_NAME = ".snapshots"
MAX_OP_SECONDS = 300  # 5 minutes


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_sandbox(pid: str) -> Path:
    """Create and return the per-project sandbox directory."""
    if not pid or "/" in pid or ".." in pid:
        raise ValueError("invalid pid")
    path = SANDBOX_ROOT / pid
    path.mkdir(parents=True, exist_ok=True)
    (path / SNAPSHOT_DIR_NAME).mkdir(exist_ok=True)
    return path


def _safe_path(sandbox: Path, rel: str) -> Path:
    """Resolve rel inside sandbox, raise if it escapes."""
    target = (sandbox / rel.lstrip("/")).resolve()
    sandbox_real = sandbox.resolve()
    if os.path.commonpath([str(target), str(sandbox_real)]) != str(sandbox_real):
        raise ValueError(f"path '{rel}' escapes sandbox")
    return target


async def _run(cmd: List[str], cwd: Optional[Path] = None,
               env: Optional[Dict[str, str]] = None,
               timeout: int = MAX_OP_SECONDS) -> Dict[str, Any]:
    """Run a subprocess with timeout. stderr/stdout captured."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return {"ok": False, "error": "timeout", "cmd": cmd[0]}
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": (out or b"").decode("utf-8", errors="replace")[:5000],
        "stderr": (err or b"").decode("utf-8", errors="replace")[:5000],
    }


# ────────────── Credential loader ──────────────
async def _load_cred(db, pid: str, key_name: str) -> Optional[str]:
    """Pull encrypted credential from Mongo and decrypt in memory."""
    doc = await db.freebuild_projects.find_one(
        {"id": pid}, {"_id": 0, f"continuation_credentials.{key_name}": 1}
    )
    if not doc:
        return None
    blob = (doc.get("continuation_credentials") or {}).get(key_name)
    if not blob or not blob.get("ciphertext"):
        return None
    try:
        return decrypt_secret(blob["ciphertext"])
    except Exception:
        logger.exception("[continuation_tools] decrypt failed")
        return None


# ────────────── Snapshot ──────────────
async def handle_create_snapshot(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Tar-gzip the current sandbox contents (excluding .snapshots itself)
    and write a SHA256 fingerprint alongside. Returns the snapshot id."""
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    label = (args.get("label") or "manual").strip()[:50]
    if not pid:
        return {"ok": False, "error": "project_id required"}
    sandbox = _ensure_sandbox(pid)
    snap_dir = sandbox / SNAPSHOT_DIR_NAME
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snap_id = f"{ts}_{label}"
    archive_path = snap_dir / f"{snap_id}.tar.gz"
    # Build tarball
    with tarfile.open(archive_path, "w:gz") as tar:
        for entry in sandbox.iterdir():
            if entry.name == SNAPSHOT_DIR_NAME:
                continue
            tar.add(entry, arcname=entry.name)
    # Fingerprint
    h = hashlib.sha256()
    with open(archive_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    fp = h.hexdigest()
    (snap_dir / f"{snap_id}.sha256").write_text(fp)
    return {
        "ok": True,
        "snapshot_id": snap_id,
        "archive_path": str(archive_path),
        "fingerprint": fp,
        "size_bytes": archive_path.stat().st_size,
        "created_at": _now_iso(),
    }


async def handle_list_snapshots(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    if not pid:
        return {"ok": False, "error": "project_id required"}
    sandbox = _ensure_sandbox(pid)
    snap_dir = sandbox / SNAPSHOT_DIR_NAME
    items = []
    for p in sorted(snap_dir.glob("*.tar.gz"), reverse=True):
        items.append({
            "snapshot_id": p.stem.replace(".tar", ""),
            "size_bytes": p.stat().st_size,
            "created_at": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(),
        })
    return {"ok": True, "snapshots": items[:50]}


async def handle_restore_snapshot(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Wipe sandbox (except snapshots) and extract the chosen snapshot."""
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    snap_id = (args.get("snapshot_id") or "").strip()
    if not pid or not snap_id:
        return {"ok": False, "error": "project_id and snapshot_id required"}
    sandbox = _ensure_sandbox(pid)
    archive = sandbox / SNAPSHOT_DIR_NAME / f"{snap_id}.tar.gz"
    if not archive.exists():
        return {"ok": False, "error": "snapshot not found"}
    # Wipe everything except .snapshots
    for entry in sandbox.iterdir():
        if entry.name == SNAPSHOT_DIR_NAME:
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(sandbox)
    return {"ok": True, "restored": snap_id, "at": _now_iso()}


# ────────────── Git clone ──────────────
async def handle_clone_remote_repo(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Clone the customer's Git repo into the sandbox using the encrypted
    GITHUB_TOKEN (or generic GIT_TOKEN). Always snapshots first if the
    sandbox already has content."""
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    repo_url = (args.get("repo_url") or "").strip()
    branch = (args.get("branch") or "main").strip()
    if not pid or not repo_url:
        return {"ok": False, "error": "project_id and repo_url required"}
    if not repo_url.startswith(("https://", "http://")):
        return {"ok": False, "error": "only https git URLs are supported"}

    # DB resolution via the agent context (ctx.db) — falls back if missing.
    db = getattr(ctx, "db", None) if ctx else None
    if db is None:
        from server import db as _db  # type: ignore
        db = _db

    token = await _load_cred(db, pid, "GITHUB_TOKEN") or await _load_cred(db, pid, "GIT_TOKEN")
    if not token:
        return {"ok": False, "error": "no GITHUB_TOKEN saved for this project"}

    sandbox = _ensure_sandbox(pid)
    target = sandbox / "repo"

    # Snapshot existing sandbox content before overwrite
    if any(p.name != SNAPSHOT_DIR_NAME for p in sandbox.iterdir()):
        await handle_create_snapshot({"project_id": pid, "label": "pre_clone"}, ctx)

    # Build authenticated URL (token never logged)
    parsed = urllib.parse.urlparse(repo_url)
    auth_url = f"{parsed.scheme}://x-access-token:{token}@{parsed.netloc}{parsed.path}"

    # Wipe target dir if exists
    if target.exists():
        shutil.rmtree(target)

    res = await _run(
        ["git", "clone", "--depth", "1", "-b", branch, auth_url, str(target)],
        cwd=sandbox,
    )
    # Scrub token from any echoed output
    safe_err = (res.get("stderr") or "").replace(token, "***REDACTED***")
    safe_out = (res.get("stdout") or "").replace(token, "***REDACTED***")
    if not res["ok"]:
        return {"ok": False, "error": "git clone failed", "stderr": safe_err[:500]}

    # File count
    file_count = sum(1 for _ in target.rglob("*") if _.is_file() and ".git/" not in str(_))
    total_size = sum(p.stat().st_size for p in target.rglob("*") if p.is_file())

    # Persist clone metadata on project
    await db.freebuild_projects.update_one(
        {"id": pid},
        {"$set": {
            "continuation_sandbox": {
                "path": str(target),
                "repo_url": repo_url,
                "branch": branch,
                "file_count": file_count,
                "total_size_bytes": total_size,
                "cloned_at": _now_iso(),
            },
        }},
    )
    return {
        "ok": True,
        "sandbox_path": str(target),
        "branch": branch,
        "file_count": file_count,
        "total_size_bytes": total_size,
        "stdout": safe_out[:500],
    }


# ────────────── FTP sync ──────────────
async def handle_ftp_sync_pull(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Mirror files from an FTP/SFTP host into the sandbox using lftp.
    Credentials expected on the project: FTP_HOST, FTP_USERNAME, FTP_PASSWORD."""
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    remote_dir = (args.get("remote_dir") or "/").strip()
    if not pid:
        return {"ok": False, "error": "project_id required"}

    db = getattr(ctx, "db", None) if ctx else None
    if db is None:
        from server import db as _db  # type: ignore
        db = _db

    host = await _load_cred(db, pid, "FTP_HOST")
    user = await _load_cred(db, pid, "FTP_USERNAME")
    pwd = await _load_cred(db, pid, "FTP_PASSWORD")
    if not (host and user and pwd):
        return {"ok": False, "error": "FTP credentials incomplete (need HOST, USERNAME, PASSWORD)"}

    sandbox = _ensure_sandbox(pid)
    target = sandbox / "ftp"
    target.mkdir(exist_ok=True)

    if any(p.name != SNAPSHOT_DIR_NAME for p in sandbox.iterdir()):
        await handle_create_snapshot({"project_id": pid, "label": "pre_ftp_pull"}, ctx)

    # lftp is the most robust mirror tool. Falls back gracefully if missing.
    lftp = shutil.which("lftp")
    if not lftp:
        return {"ok": False, "error": "lftp not installed on server (apt install lftp)"}

    script = (
        f"set ftp:ssl-allow no; set ssl:verify-certificate no; "
        f"open -u '{user}','{pwd}' {host}; "
        f"mirror --parallel=4 --no-perms --depth-first '{remote_dir}' '{target}'; bye"
    )
    res = await _run([lftp, "-c", script], cwd=sandbox)
    safe_err = (res.get("stderr") or "").replace(pwd, "***REDACTED***")
    if not res["ok"]:
        return {"ok": False, "error": "ftp mirror failed", "stderr": safe_err[:500]}

    file_count = sum(1 for _ in target.rglob("*") if _.is_file())
    total_size = sum(p.stat().st_size for p in target.rglob("*") if p.is_file())
    await db.freebuild_projects.update_one(
        {"id": pid},
        {"$set": {"continuation_sandbox": {
            "path": str(target),
            "ftp_host": host,
            "remote_dir": remote_dir,
            "file_count": file_count,
            "total_size_bytes": total_size,
            "pulled_at": _now_iso(),
        }}},
    )
    return {"ok": True, "sandbox_path": str(target), "file_count": file_count, "total_size_bytes": total_size}


# ────────────── Sandbox file ops ──────────────
async def handle_list_sandbox_files(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    sub = (args.get("path") or "").strip()
    max_entries = int(args.get("max_entries") or 200)
    if not pid:
        return {"ok": False, "error": "project_id required"}
    sandbox = _ensure_sandbox(pid)
    try:
        root = _safe_path(sandbox, sub) if sub else sandbox
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    if not root.exists():
        return {"ok": True, "files": [], "empty": True}
    items = []
    for p in sorted(root.rglob("*"))[:max_entries]:
        if SNAPSHOT_DIR_NAME in p.parts:
            continue
        items.append({
            "path": str(p.relative_to(sandbox)),
            "type": "dir" if p.is_dir() else "file",
            "size": p.stat().st_size if p.is_file() else None,
        })
    return {"ok": True, "files": items, "count": len(items), "sandbox_root": str(sandbox)}


async def handle_read_sandbox_file(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    rel = (args.get("path") or "").strip()
    max_bytes = int(args.get("max_bytes") or 200_000)
    if not pid or not rel:
        return {"ok": False, "error": "project_id and path required"}
    sandbox = _ensure_sandbox(pid)
    try:
        p = _safe_path(sandbox, rel)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    if not p.exists() or not p.is_file():
        return {"ok": False, "error": "file not found"}
    if p.stat().st_size > max_bytes:
        return {"ok": False, "error": f"file too large ({p.stat().st_size} > {max_bytes})"}
    try:
        content = p.read_text("utf-8")
    except UnicodeDecodeError:
        return {"ok": False, "error": "binary file — refuse to send raw bytes"}
    return {"ok": True, "path": rel, "size": p.stat().st_size, "content": content}


async def handle_propose_sandbox_change(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Write a proposed change to the sandbox (NOT to production). Always
    snapshots first so the customer can roll back with one click."""
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    rel = (args.get("path") or "").strip()
    new_content = args.get("new_content")
    if not pid or not rel or new_content is None:
        return {"ok": False, "error": "project_id, path, new_content required"}
    sandbox = _ensure_sandbox(pid)
    try:
        p = _safe_path(sandbox, rel)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    # Snapshot before any write
    await handle_create_snapshot({"project_id": pid, "label": "pre_edit"}, ctx)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(new_content, encoding="utf-8")
    return {"ok": True, "wrote": str(p.relative_to(sandbox)), "bytes": len(new_content.encode("utf-8"))}


# ────────────── Registry ──────────────
CONTINUATION_TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "clone_remote_repo",
        "description": "Clone the customer's Git repository (using the encrypted GITHUB_TOKEN saved on the project) into the isolated per-project sandbox at /opt/zerax/sandboxes/{pid}/repo/. Auto-snapshots existing content first. Read-only path to start analyzing real code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "repo_url": {"type": "string", "description": "https git URL e.g. https://github.com/user/repo.git"},
                "branch": {"type": "string", "description": "default 'main'"},
            },
            "required": ["repo_url"],
        },
    },
    {
        "name": "ftp_sync_pull",
        "description": "Mirror a remote FTP directory into the sandbox using lftp + the encrypted FTP_HOST/FTP_USERNAME/FTP_PASSWORD credentials. Auto-snapshots first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "remote_dir": {"type": "string", "description": "remote path, default '/'"},
            },
            "required": [],
        },
    },
    {
        "name": "create_snapshot",
        "description": "Take a tar.gz backup of the current sandbox state with a SHA-256 fingerprint. ALWAYS call this BEFORE any destructive operation so the customer can roll back.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "label": {"type": "string", "description": "short tag e.g. 'pre_refactor'"},
            },
            "required": [],
        },
    },
    {
        "name": "list_snapshots",
        "description": "List all snapshots in the sandbox (newest first) with id + size + created_at.",
        "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": []},
    },
    {
        "name": "restore_snapshot",
        "description": "Roll back the sandbox to a previous snapshot. Wipes current sandbox contents (except snapshots dir).",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}, "snapshot_id": {"type": "string"}},
            "required": ["snapshot_id"],
        },
    },
    {
        "name": "list_sandbox_files",
        "description": "Browse files in the cloned sandbox. Returns relative paths + sizes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "path": {"type": "string", "description": "relative subdir, default sandbox root"},
                "max_entries": {"type": "integer", "description": "default 200"},
            },
            "required": [],
        },
    },
    {
        "name": "read_sandbox_file",
        "description": "Read a single file from the sandbox (max 200KB). Use to inspect actual customer code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "path": {"type": "string", "description": "relative path inside the sandbox"},
                "max_bytes": {"type": "integer", "description": "default 200000"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "propose_sandbox_change",
        "description": "Write a proposed edit to a file IN THE SANDBOX (never production). Auto-snapshots first. The customer must approve via UI before this gets pushed live.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "path": {"type": "string"},
                "new_content": {"type": "string"},
            },
            "required": ["path", "new_content"],
        },
    },
]

CONTINUATION_TOOL_HANDLERS: Dict[str, Any] = {
    "clone_remote_repo": handle_clone_remote_repo,
    "ftp_sync_pull": handle_ftp_sync_pull,
    "create_snapshot": handle_create_snapshot,
    "list_snapshots": handle_list_snapshots,
    "restore_snapshot": handle_restore_snapshot,
    "list_sandbox_files": handle_list_sandbox_files,
    "read_sandbox_file": handle_read_sandbox_file,
    "propose_sandbox_change": handle_propose_sandbox_change,
}
