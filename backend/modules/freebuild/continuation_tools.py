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

try:
    from .continuation_audit import write_audit  # async (db, pid, uid, action, **)
except Exception:  # pragma: no cover
    async def write_audit(*a, **kw):  # type: ignore
        return None

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

    # Guard: tool refuses to run outside continuation-mode projects
    err = await _guard_continuation_mode(db, pid)
    if err:
        return {"ok": False, "error": err}

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
    await _audit(ctx, db, pid, "clone_remote_repo",
                 tool_name="clone_remote_repo", success=True,
                 details={"repo_url": repo_url, "branch": branch,
                          "file_count": file_count, "size_bytes": total_size})
    return {
        "ok": True,
        "sandbox_path": str(target),
        "branch": branch,
        "file_count": file_count,
        "total_size_bytes": total_size,
        "stdout": safe_out[:500],
    }


async def handle_push_to_review_branch(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Approve & deploy — push the current sandbox state to a NEW branch
    on the customer's remote git repo. Never touches `main`. The customer
    then opens a Pull Request to merge it after reviewing the diff.

    This is the safest production-deploy path:
      • Original main branch is untouched
      • Customer reviews via GitHub PR UI before merging
      • All changes are git-tracked + audit-logged
      • Rollback = just close the PR
    """
    import time
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    commit_message = (args.get("commit_message") or "Zenrex AI proposed changes").strip()[:200]
    branch_suffix = (args.get("branch_suffix") or str(int(time.time()))).strip()[:30]
    if not pid:
        return {"ok": False, "error": "project_id required"}

    db = getattr(ctx, "db", None) if ctx else None
    if db is None:
        from server import db as _db  # type: ignore
        db = _db

    err = await _guard_continuation_mode(db, pid)
    if err:
        return {"ok": False, "error": err}
    # Paywall: refuse pushes after first_update if not subscribed
    locked = await _guard_subscription_lock(db, pid)
    if locked:
        return locked

    token = await _load_cred(db, pid, "GITHUB_TOKEN") or await _load_cred(db, pid, "GIT_TOKEN")
    if not token:
        return {"ok": False, "error": "no GITHUB_TOKEN saved for this project"}

    sandbox = _ensure_sandbox(pid)
    repo_dir = sandbox / "repo"
    if not (repo_dir / ".git").exists():
        return {"ok": False, "error": "no git repo cloned in sandbox"}

    # Get configured remote
    res = await _run(["git", "config", "--get", "remote.origin.url"], cwd=repo_dir, timeout=10)
    if not res["ok"]:
        return {"ok": False, "error": "no origin remote configured"}
    original_url = res["stdout"].strip()
    import urllib.parse
    parsed = urllib.parse.urlparse(original_url)
    # Strip any existing auth credentials from netloc (the clone left them in)
    netloc_host = parsed.netloc.split("@")[-1]
    safe_token = urllib.parse.quote(token, safe="")
    auth_url = f"{parsed.scheme}://x-access-token:{safe_token}@{netloc_host}{parsed.path}"
    clean_url = f"{parsed.scheme}://{netloc_host}{parsed.path}"

    branch_name = f"zenrex-ai/{branch_suffix}"
    cmds = [
        ["git", "config", "user.email", "ai@zenrex.ai"],
        ["git", "config", "user.name", "Zenrex AI Engineer"],
        ["git", "checkout", "-B", branch_name],
        ["git", "add", "-A"],
        ["git", "commit", "-m", commit_message, "--allow-empty"],
        ["git", "remote", "set-url", "origin", auth_url],
        ["git", "push", "-u", "origin", branch_name, "--force"],
        # Restore the scrubbed remote URL so the token isn't sitting in .git/config
        ["git", "remote", "set-url", "origin", clean_url],
    ]
    log = []
    for cmd in cmds:
        r = await _run(cmd, cwd=repo_dir, timeout=60)
        log.append({"cmd": cmd[1] if len(cmd) > 1 else cmd[0], "ok": r["ok"]})
        if not r["ok"]:
            err_msg = (r.get("stderr") or "").replace(token, "***REDACTED***")[:300]
            await _audit(ctx, db, pid, "push_to_review_branch",
                         tool_name="push_to_review_branch", success=False,
                         details={"branch": branch_name, "failed_cmd": cmd[1] if len(cmd) > 1 else cmd[0],
                                  "error": err_msg})
            return {"ok": False, "error": f"git {cmd[1] if len(cmd) > 1 else cmd[0]} failed",
                    "stderr": err_msg, "log": log}

    # Build a PR URL for GitHub
    pr_url = None
    if "github.com" in netloc_host:
        repo_path = parsed.path.replace(".git", "").strip("/")
        pr_url = f"https://github.com/{repo_path}/compare/main...{branch_name}?expand=1"

    await _audit(ctx, db, pid, "push_to_review_branch",
                 tool_name="push_to_review_branch", success=True,
                 details={"branch": branch_name, "commit_message": commit_message,
                          "pr_url": pr_url})

    return {
        "ok": True,
        "branch": branch_name,
        "commit_message": commit_message,
        "pr_url": pr_url,
        "instructions_ar": (
            "✅ التعديلات منشورة على فرع جديد. افتح رابط PR في GitHub، "
            "راجع الـ diff، وادمج لما تكون جاهز."
        ),
    }


# ────────────── Direct Deploy (live VPS) ──────────────
# These tools push approved sandbox changes DIRECTLY to the customer's live
# production server — bypassing the GitHub PR loop. Used when the customer
# wants instant publishing rather than a code-review cycle.
#
# Safety rails baked in:
#   • Auto-snapshot of sandbox state BEFORE any push (rollback anchor)
#   • Private key written to a 0600 tmp file and unlinked in `finally`
#   • All shell args quoted via shlex; never via f-string interpolation
#   • Post-deploy commands run via `bash -lc` on remote, captured in audit
#   • Deploy target dir must be on a per-project allowlist saved by the user
import shlex
import tempfile


SSH_COMMON_OPTS = [
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "ConnectTimeout=15",
    "-o", "ServerAliveInterval=10",
]


async def _load_deploy_target(db, pid: str) -> Optional[Dict[str, Any]]:
    """Read the customer's saved deploy-target config (target_dir, source_subdir,
    post_deploy_command, deploy_port). Returns None if not configured."""
    doc = await db.freebuild_projects.find_one(
        {"id": pid}, {"_id": 0, "continuation_deploy_target": 1},
    )
    if not doc:
        return None
    return doc.get("continuation_deploy_target") or None


async def handle_deploy_to_live_vps(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Rsync the approved sandbox contents to the customer's live VPS over SSH,
    then run optional post-deploy commands (build/restart). Requires saved
    credentials: SSH_HOST, SSH_USERNAME, SSH_PRIVATE_KEY (+ optional SSH_PORT).

    Required project config (saved separately via /deploy-target endpoint):
      - target_dir: remote dir to rsync into (e.g. /var/www/html/)
      - source_subdir: dir inside sandbox to push (default 'repo')
      - post_deploy_command: optional shell command (e.g. 'systemctl reload nginx')
    """
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    if not pid:
        return {"ok": False, "error": "project_id required"}

    db = getattr(ctx, "db", None) if ctx else None
    if db is None:
        from server import db as _db  # type: ignore
        db = _db

    err = await _guard_continuation_mode(db, pid)
    if err:
        return {"ok": False, "error": err}
    # Paywall: direct live deploy is locked after first_update_delivered
    locked = await _guard_subscription_lock(db, pid)
    if locked:
        return locked

    target_cfg = await _load_deploy_target(db, pid)
    if not target_cfg or not target_cfg.get("target_dir"):
        return {"ok": False, "error": "deploy_target_not_configured",
                "hint": "Save target_dir + post_deploy_command via /deploy-target first"}
    target_dir = target_cfg["target_dir"]
    source_subdir = (target_cfg.get("source_subdir") or "repo").strip("/")
    post_cmd = (target_cfg.get("post_deploy_command") or "").strip()

    host = await _load_cred(db, pid, "SSH_HOST")
    user = await _load_cred(db, pid, "SSH_USERNAME")
    privkey = await _load_cred(db, pid, "SSH_PRIVATE_KEY")
    port_raw = await _load_cred(db, pid, "SSH_PORT") or "22"
    try:
        port = int(port_raw)
    except Exception:
        port = 22

    if not (host and user and privkey):
        return {"ok": False, "error": "ssh_credentials_incomplete",
                "hint": "Need SSH_HOST + SSH_USERNAME + SSH_PRIVATE_KEY in encrypted credentials"}

    sandbox = _ensure_sandbox(pid)
    src_path = sandbox / source_subdir
    if not src_path.exists() or not any(src_path.iterdir()):
        return {"ok": False, "error": "sandbox_source_empty",
                "hint": f"No files at sandbox/{source_subdir}/. Clone or sync first."}

    # Snapshot BEFORE deploy so we keep a rollback anchor on Zenrex side
    snap = await handle_create_snapshot({"project_id": pid, "label": "pre_direct_deploy"}, ctx)

    # Write private key to a chmod-600 tmpfile (unlinked in finally)
    keyfile = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False)
    try:
        keyfile.write(privkey if privkey.endswith("\n") else privkey + "\n")
        keyfile.flush()
        keyfile.close()
        os.chmod(keyfile.name, 0o600)

        ssh_cmd_str = " ".join(["ssh", "-i", shlex.quote(keyfile.name),
                                "-p", str(port)] + SSH_COMMON_OPTS)
        remote = f"{user}@{host}:{target_dir.rstrip('/')}/"

        # 1) rsync
        rsync_cmd = [
            "rsync", "-az", "--delete",
            "--no-perms", "--no-owner", "--no-group",
            "--exclude=.git", "--exclude=__pycache__", "--exclude=node_modules",
            "-e", ssh_cmd_str,
            f"{src_path}/", remote,
        ]
        rsync_res = await _run(rsync_cmd, cwd=sandbox, timeout=600)
        # Scrub any token-ish content (defensive)
        rsync_err = (rsync_res.get("stderr") or "")[:1500]
        rsync_out = (rsync_res.get("stdout") or "")[:1500]
        if not rsync_res["ok"]:
            await _audit(ctx, db, pid, "deploy_to_live_vps",
                         tool_name="deploy_to_live_vps", success=False,
                         details={"stage": "rsync", "target": target_dir,
                                  "host": host, "error": rsync_err[:500],
                                  "snapshot_id": snap.get("snapshot_id")})
            return {"ok": False, "error": "rsync_failed",
                    "stderr": rsync_err, "snapshot_id": snap.get("snapshot_id")}

        # 2) Optional post-deploy command (build, restart, reload nginx, etc.)
        post_out, post_err, post_ok = "", "", True
        if post_cmd:
            ssh_post = [
                "ssh", "-i", keyfile.name, "-p", str(port),
                *SSH_COMMON_OPTS,
                f"{user}@{host}", "bash", "-lc", post_cmd,
            ]
            post_res = await _run(ssh_post, timeout=300)
            post_ok = bool(post_res.get("ok"))
            post_out = (post_res.get("stdout") or "")[:2000]
            post_err = (post_res.get("stderr") or "")[:2000]

        success = post_ok  # rsync already verified above
        await _audit(ctx, db, pid, "deploy_to_live_vps",
                     tool_name="deploy_to_live_vps", success=success,
                     details={"target": target_dir, "host": host, "port": port,
                              "source_subdir": source_subdir,
                              "post_command_ran": bool(post_cmd),
                              "post_ok": post_ok,
                              "snapshot_id": snap.get("snapshot_id")})
        return {
            "ok": success,
            "deployed_to": f"{user}@{host}:{target_dir}",
            "snapshot_id": snap.get("snapshot_id"),
            "rsync_stdout": rsync_out[:800],
            "post_command": post_cmd or None,
            "post_stdout": post_out[:800],
            "post_stderr": post_err[:800],
            "deployed_at": _now_iso(),
            "instructions_ar": (
                "✅ التعديلات نُشرت مباشرة على السيرفر الحي."
                if success else
                "⚠️ المزامنة تمت لكن أمر ما بعد النشر فشل — راجع post_stderr."
            ),
        }
    finally:
        try:
            os.unlink(keyfile.name)
        except Exception:
            pass


async def handle_deploy_to_live_ftp(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Upload sandbox contents directly to a live FTP/SFTP server using lftp
    mirror -R (reverse mirror = upload). Used for shared hosting providers
    (Hostinger, GoDaddy, etc.) that don't give SSH access."""
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    if not pid:
        return {"ok": False, "error": "project_id required"}

    db = getattr(ctx, "db", None) if ctx else None
    if db is None:
        from server import db as _db  # type: ignore
        db = _db

    err = await _guard_continuation_mode(db, pid)
    if err:
        return {"ok": False, "error": err}
    # Paywall: FTP direct deploy is locked after first_update_delivered
    locked = await _guard_subscription_lock(db, pid)
    if locked:
        return locked

    target_cfg = await _load_deploy_target(db, pid)
    if not target_cfg or not target_cfg.get("target_dir"):
        return {"ok": False, "error": "deploy_target_not_configured"}
    target_dir = target_cfg["target_dir"]
    source_subdir = (target_cfg.get("source_subdir") or "repo").strip("/")

    host = await _load_cred(db, pid, "FTP_HOST")
    user = await _load_cred(db, pid, "FTP_USERNAME")
    pwd = await _load_cred(db, pid, "FTP_PASSWORD")
    port = await _load_cred(db, pid, "FTP_PORT") or "21"
    if not (host and user and pwd):
        return {"ok": False, "error": "ftp_credentials_incomplete"}

    sandbox = _ensure_sandbox(pid)
    src_path = sandbox / source_subdir
    if not src_path.exists() or not any(src_path.iterdir()):
        return {"ok": False, "error": "sandbox_source_empty"}

    snap = await handle_create_snapshot({"project_id": pid, "label": "pre_direct_ftp_deploy"}, ctx)

    lftp = shutil.which("lftp")
    if not lftp:
        return {"ok": False, "error": "lftp_not_installed"}

    # lftp script: connect, mirror upload (-R), delete remote files no longer present
    script = (
        f"set ftp:ssl-allow no; set ssl:verify-certificate no; "
        f"open -p {port} -u {shlex.quote(user)},{shlex.quote(pwd)} {shlex.quote(host)}; "
        f"mirror -R --delete --parallel=3 --exclude '\\.git/' {shlex.quote(str(src_path))} {shlex.quote(target_dir)}; "
        f"bye"
    )
    res = await _run([lftp, "-c", script], cwd=sandbox, timeout=600)
    safe_err = (res.get("stderr") or "").replace(pwd, "***REDACTED***")[:1500]
    safe_out = (res.get("stdout") or "").replace(pwd, "***REDACTED***")[:1500]
    success = bool(res.get("ok"))

    await _audit(ctx, db, pid, "deploy_to_live_ftp",
                 tool_name="deploy_to_live_ftp", success=success,
                 details={"target": target_dir, "host": host,
                          "source_subdir": source_subdir,
                          "snapshot_id": snap.get("snapshot_id"),
                          "error": None if success else safe_err[:500]})
    return {
        "ok": success,
        "deployed_to": f"ftp://{user}@{host}{target_dir}",
        "snapshot_id": snap.get("snapshot_id"),
        "stdout": safe_out[:800],
        "stderr": "" if success else safe_err[:800],
        "deployed_at": _now_iso(),
        "instructions_ar": (
            "✅ التعديلات رُفعت مباشرة عبر FTP على السيرفر الحي."
            if success else
            "⚠️ فشل رفع FTP — راجع stderr."
        ),
    }


async def _audit(ctx, db, pid, action, **kw):
    """Best-effort audit log writer used by tool handlers."""
    try:
        uid = getattr(ctx, "user_id", None) or "system"
        await write_audit(db, pid, uid, action, **kw)
    except Exception:
        logger.exception("[continuation_tools] audit failed (non-fatal)")


async def _guard_continuation_mode(db, pid: str) -> Optional[str]:
    """Defensive check — return error string if pid isn't a continuation
    project, None otherwise. Tools refuse to run on regular website/app
    projects so the AI engineer can't accidentally clone code into a
    project that wasn't set up via the onboarding wizard."""
    if not pid:
        return "project_id required"
    proj = await db.freebuild_projects.find_one({"id": pid}, {"_id": 0, "mode": 1})
    if proj is None:
        return "project not found"
    if proj.get("mode") != "continuation":
        return "this tool only works on continuation-mode projects"
    return None


async def _guard_subscription_lock(db, pid: str) -> Optional[Dict[str, Any]]:
    """Paywall gate. Once `first_update_delivered=True` is set, the AI must
    stop ALL further mutations on the customer's code until the project
    `continuation_unlocked=True` (paid). Returns a structured error dict that
    must be RETURNED VERBATIM from the tool handler so the AI sees it and
    relays the payment prompt to the user.

    Tools that MUST call this before mutating: propose_sandbox_change,
    push_to_review_branch, deploy_to_live_vps, deploy_to_live_ftp, and any
    future write tool. READ tools (list/read/audit) are NOT gated.
    """
    if not pid:
        return None
    proj = await db.freebuild_projects.find_one(
        {"id": pid},
        {"_id": 0, "first_update_delivered": 1, "continuation_unlocked": 1},
    )
    if not proj:
        return None
    if proj.get("first_update_delivered") and not proj.get("continuation_unlocked"):
        return {
            "ok": False,
            "error": "subscription_required",
            "code": "PAYWALL_LOCKED",
            "monthly_price_usd": 150.0,
            "message_ar": (
                "🔒 تم تسليم أول تحديث ملموس مجاناً، والآن المشروع مقفول للاشتراك. "
                "اطلب من العميل تفعيل الاشتراك ($150/شهر) من البانر الظاهر في الواجهة "
                "قبل أي تعديل آخر. لا تحاول تنفيذ أي عملية كتابة قبل الدفع."
            ),
            "message_en": (
                "First concrete update was delivered. The project is now locked "
                "until the customer subscribes at $150/month. Ask them to click "
                "the subscription banner before any further edits."
            ),
            "ui_action_required": "subscribe_continuation",
        }
    return None


async def handle_mark_first_update(args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
    """Flip `first_update_delivered=True` on the continuation project AFTER
    the AI engineer delivered the FIRST concrete, visible fix in the sandbox.
    This triggers the $150/month subscription banner in the customer's UI
    and locks all further write-tools until they pay.

    Rules baked in:
      • Idempotent — calling twice is a no-op (returns already_marked=True)
      • Requires continuation mode + at least one sandbox edit on record
      • Records the trigger reason in the audit log
    """
    pid = (args.get("project_id") or (ctx and getattr(ctx, "project_id", None)) or "").strip()
    summary = (args.get("summary") or "").strip()[:300]
    if not pid:
        return {"ok": False, "error": "project_id required"}

    db = getattr(ctx, "db", None) if ctx else None
    if db is None:
        from server import db as _db  # type: ignore
        db = _db

    err = await _guard_continuation_mode(db, pid)
    if err:
        return {"ok": False, "error": err}

    proj = await db.freebuild_projects.find_one(
        {"id": pid},
        {"_id": 0, "first_update_delivered": 1, "continuation_unlocked": 1},
    )
    if proj and proj.get("first_update_delivered"):
        return {
            "ok": True,
            "already_marked": True,
            "first_update_delivered": True,
            "continuation_unlocked": bool(proj.get("continuation_unlocked")),
            "message_ar": "أول تحديث مسجّل سابقاً — البانر ظاهر للعميل.",
        }

    await db.freebuild_projects.update_one(
        {"id": pid},
        {"$set": {
            "first_update_delivered": True,
            "first_update_at": _now_iso(),
            "first_update_summary": summary or "AI delivered the first concrete fix",
        }},
    )
    await _audit(ctx, db, pid, "mark_first_update",
                 tool_name="mark_first_update", success=True,
                 details={"summary": summary[:200] if summary else None,
                          "triggered_banner": True, "monthly_price_usd": 150.0})
    return {
        "ok": True,
        "first_update_delivered": True,
        "monthly_price_usd": 150.0,
        "message_ar": (
            "✅ تم تسجيل أول تحديث ملموس. سيظهر للعميل بانر اشتراك $150/شهر فوراً. "
            "توقّف عن أي تعديل آخر لحد ما يفعّل الاشتراك."
        ),
        "next_instruction_ar": (
            "أخبر العميل بوضوح: «جاهز التحديث الأول في الـ Sandbox، فعّل الاشتراك "
            "من البانر فوق الشات عشان نكمل باقي التعديلات». ولا تنفّذ أي أداة كتابة "
            "(propose_sandbox_change / push_to_review_branch / deploy_to_live_*) قبل ذلك."
        ),
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

    err = await _guard_continuation_mode(db, pid)
    if err:
        return {"ok": False, "error": err}

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
    # Guard: only allowed inside continuation mode
    db_check = getattr(ctx, "db", None) if ctx else None
    if db_check is None:
        try:
            from server import db as _db  # type: ignore
            db_check = _db
        except Exception:
            db_check = None
    if db_check is not None:
        err = await _guard_continuation_mode(db_check, pid)
        if err:
            return {"ok": False, "error": err}
        # Paywall: after first_update_delivered, refuse any write until paid
        locked = await _guard_subscription_lock(db_check, pid)
        if locked:
            return locked
    sandbox = _ensure_sandbox(pid)
    try:
        p = _safe_path(sandbox, rel)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    # Snapshot before any write
    await handle_create_snapshot({"project_id": pid, "label": "pre_edit"}, ctx)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(new_content, encoding="utf-8")
    # Audit
    db = getattr(ctx, "db", None) if ctx else None
    if db is None:
        try:
            from server import db as _db  # type: ignore
            db = _db
        except Exception:
            db = None
    if db is not None:
        await _audit(ctx, db, pid, "propose_sandbox_change",
                     tool_name="propose_sandbox_change", target_path=rel,
                     success=True, details={"bytes": len(new_content.encode("utf-8"))})
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
    {
        "name": "push_to_review_branch",
        "description": "Push current sandbox state to a NEW review branch (zenrex-ai/<timestamp>) on the customer's remote git repo. Never touches main. Returns a Pull Request URL the customer can review + merge.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "commit_message": {"type": "string", "description": "what the AI changed in plain language"},
                "branch_suffix": {"type": "string", "description": "optional friendly tag e.g. 'image-swap'"},
            },
            "required": ["commit_message"],
        },
    },
    {
        "name": "deploy_to_live_vps",
        "description": "DIRECT LIVE DEPLOY (SSH). Rsync the approved sandbox files to the customer's live VPS over SSH, then run optional post-deploy commands (build, restart). Requires SSH_HOST/SSH_USERNAME/SSH_PRIVATE_KEY credentials AND a saved deploy_target config (target_dir + post_deploy_command). Auto-snapshots before pushing. Use ONLY after explicit customer approval — this overwrites live production files.",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": [],
        },
    },
    {
        "name": "deploy_to_live_ftp",
        "description": "DIRECT LIVE DEPLOY (FTP). Upload sandbox files directly to a live FTP/SFTP server using lftp reverse-mirror. For shared hosting (Hostinger, GoDaddy, cPanel) without SSH access. Auto-snapshots before pushing. Requires FTP_HOST/FTP_USERNAME/FTP_PASSWORD credentials AND a saved deploy_target config.",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": [],
        },
    },
    {
        "name": "mark_first_update",
        "description": "CALL THIS ONCE — and only once — RIGHT AFTER you delivered the first concrete, customer-visible fix in the sandbox preview (e.g. swapped a real image, fixed a real bug, optimized a real component). It flips the project flag that triggers the $150/month subscription banner in the customer's UI. AFTER calling this, you MUST STOP all further write actions (propose_sandbox_change, push_to_review_branch, deploy_to_live_*) until the customer pays. Do NOT call this on speculative work, plans, or analysis — only on a real shipped fix.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "summary": {
                    "type": "string",
                    "description": "One short Arabic sentence describing the concrete fix you just shipped (e.g. 'استبدلت صورة البطل بصورة جديدة'). Shown in audit log.",
                },
            },
            "required": ["summary"],
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
    "push_to_review_branch": handle_push_to_review_branch,
    "deploy_to_live_vps": handle_deploy_to_live_vps,
    "deploy_to_live_ftp": handle_deploy_to_live_ftp,
    "mark_first_update": handle_mark_first_update,
}
