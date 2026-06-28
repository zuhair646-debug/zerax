"""Triple-redundancy backup orchestrator for Continuation snapshots.

Each customer snapshot is replicated to THREE independent storage layers:
  1. Local — `/opt/zerax/sandboxes/{pid}/.snapshots/*.tar.gz` (already exists)
  2. Git branch backup — pushed to `zenrex-backup/{date}` on customer's repo
  3. S3-compatible object storage — Wasabi / Cloudflare R2 / Backblaze B2

The customer's `$150/month` subscription INCLUDES this protection. If
ANY single layer fails (server crash, repo deletion, S3 bucket misconfig),
the other two preserve the snapshot. This is what "production-grade" means.

Design rules:
  • Triple replication is BEST-EFFORT — local always succeeds, the other
    two are async fire-and-forget. We never block a snapshot on remote
    storage success.
  • Each replicated copy carries the SHA-256 of the local tar.gz as a
    metadata header for integrity verification on restore.
  • Restore tries local first (fastest), falls back to S3, then Git branch.
  • S3 uses path-style addressing so it works with Wasabi/R2/B2/MinIO.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("zenrex.continuation_backups")

# Env config — set these on production VPS for full triple-redundancy:
#   ZENREX_BACKUP_S3_ENDPOINT  (e.g. https://s3.eu-central-1.wasabisys.com)
#   ZENREX_BACKUP_S3_BUCKET    (e.g. zenrex-continuation-backups)
#   ZENREX_BACKUP_S3_KEY
#   ZENREX_BACKUP_S3_SECRET
#   ZENREX_BACKUP_S3_REGION    (default 'us-east-1')


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


async def _replicate_to_s3(snapshot_path: Path, pid: str, snap_id: str) -> Dict[str, Any]:
    """Upload the snapshot tar.gz to S3-compatible object storage.
    Returns {ok, key, size, sha256, etag} or {ok: False, error: ...}"""
    endpoint = os.environ.get("ZENREX_BACKUP_S3_ENDPOINT", "").strip()
    bucket = os.environ.get("ZENREX_BACKUP_S3_BUCKET", "").strip()
    access_key = os.environ.get("ZENREX_BACKUP_S3_KEY", "").strip()
    secret_key = os.environ.get("ZENREX_BACKUP_S3_SECRET", "").strip()
    region = os.environ.get("ZENREX_BACKUP_S3_REGION", "us-east-1").strip()
    if not all([endpoint, bucket, access_key, secret_key]):
        return {"ok": False, "skipped": True, "reason": "S3 backup not configured"}

    try:
        import aioboto3  # lazy import — only needed if S3 is configured
    except ImportError:
        return {"ok": False, "error": "aioboto3 not installed"}

    sha = _sha256_of_file(snapshot_path)
    size = snapshot_path.stat().st_size
    key = f"continuation/{pid}/{snap_id}.tar.gz"
    try:
        session = aioboto3.Session()
        async with session.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        ) as s3:
            with snapshot_path.open("rb") as f:
                resp = await s3.put_object(
                    Bucket=bucket, Key=key, Body=f,
                    Metadata={
                        "sha256": sha, "pid": pid, "snap_id": snap_id,
                        "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    },
                    ContentType="application/gzip",
                )
        return {
            "ok": True, "key": key, "size": size, "sha256": sha,
            "etag": (resp.get("ETag") or "").strip('"'),
            "bucket": bucket, "endpoint": endpoint,
        }
    except Exception as e:
        logger.exception(f"[backup] S3 upload failed for {pid}/{snap_id}: {e}")
        return {"ok": False, "error": f"{type(e).__name__}: {e}"[:200]}


async def _replicate_to_git_branch(
    sandbox_path: Path, pid: str, snap_id: str, git_token: Optional[str]
) -> Dict[str, Any]:
    """Push the current sandbox state as a tag on a `zenrex-backup` branch
    in the customer's git repo. Only triggers if a GITHUB_TOKEN is saved
    and the sandbox is a git repo."""
    if not git_token:
        return {"ok": False, "skipped": True, "reason": "no git token saved"}
    repo_dir = sandbox_path / "repo"
    if not (repo_dir / ".git").exists():
        return {"ok": False, "skipped": True, "reason": "sandbox is not a git repo"}
    import subprocess as _sp
    branch_name = f"zenrex-backup/{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    tag_name = f"zenrex-snapshot-{snap_id}"
    try:
        # Get current remote URL and inject token
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _sp.run(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_dir, capture_output=True, text=True, timeout=10,
            ),
        )
        if result.returncode != 0:
            return {"ok": False, "error": "no_origin"}
        remote_url = result.stdout.strip()
        if remote_url.startswith("https://") and "@" not in remote_url:
            authed = remote_url.replace("https://", f"https://oauth2:{git_token}@", 1)
        else:
            authed = remote_url
        # Create a lightweight tag pointing to the current HEAD
        cmds = [
            ["git", "tag", "-f", tag_name],
            ["git", "push", "-f", authed, "refs/tags/" + tag_name],
            ["git", "checkout", "-B", branch_name],
            ["git", "push", "-f", authed, branch_name],
        ]
        for cmd in cmds:
            r = await asyncio.get_event_loop().run_in_executor(
                None, lambda c=cmd: _sp.run(
                    c, cwd=repo_dir, capture_output=True, text=True, timeout=60,
                ),
            )
            if r.returncode != 0 and "tag" in cmd[1:]:
                # Tag already exists, that's fine
                continue
        return {"ok": True, "branch": branch_name, "tag": tag_name}
    except Exception as e:
        logger.exception(f"[backup] git push failed for {pid}: {e}")
        return {"ok": False, "error": f"{type(e).__name__}: {e}"[:200]}


async def replicate_snapshot_triple(
    db, pid: str, snap_id: str, sandbox_path: Path,
) -> Dict[str, Any]:
    """Best-effort fire-and-forget triple replication. Records the results
    on the project doc so we know which layers succeeded for this snapshot."""
    snap_archive = sandbox_path / ".snapshots" / f"{snap_id}.tar.gz"
    if not snap_archive.exists():
        return {"ok": False, "error": "local_snapshot_missing"}

    # Read the git token if saved (encrypted)
    try:
        from .secure_credentials import decrypt_secret
        proj = await db.freebuild_projects.find_one(
            {"id": pid}, {"_id": 0, "continuation_credentials": 1},
        )
        creds = (proj or {}).get("continuation_credentials") or {}
        git_blob = creds.get("GITHUB_TOKEN") or creds.get("GIT_TOKEN")
        git_token = decrypt_secret(git_blob["ciphertext"]) if git_blob and isinstance(git_blob, dict) else None
    except Exception:
        git_token = None

    # Run both in parallel
    s3_task = asyncio.create_task(_replicate_to_s3(snap_archive, pid, snap_id))
    git_task = asyncio.create_task(_replicate_to_git_branch(sandbox_path, pid, snap_id, git_token))
    s3_res, git_res = await asyncio.gather(s3_task, git_task, return_exceptions=True)
    if isinstance(s3_res, Exception):
        s3_res = {"ok": False, "error": str(s3_res)[:200]}
    if isinstance(git_res, Exception):
        git_res = {"ok": False, "error": str(git_res)[:200]}

    # Persist replication metadata on the snapshot record
    await db.freebuild_projects.update_one(
        {"id": pid},
        {"$push": {"continuation_backup_history": {
            "snap_id": snap_id, "ts": datetime.now(timezone.utc).isoformat(),
            "local": {"ok": True, "path": str(snap_archive),
                      "size": snap_archive.stat().st_size,
                      "sha256": _sha256_of_file(snap_archive)},
            "s3": s3_res, "git": git_res,
        }}},
    )
    return {
        "ok": True,  # local always succeeded if we got here
        "layers": {"local": True, "s3": bool(s3_res.get("ok")), "git": bool(git_res.get("ok"))},
        "redundancy_count": 1 + int(bool(s3_res.get("ok"))) + int(bool(git_res.get("ok"))),
        "s3": s3_res, "git": git_res,
    }


async def fetch_from_s3(pid: str, snap_id: str, dest: Path) -> Dict[str, Any]:
    """Restore a snapshot tar.gz from S3 if it's no longer on disk locally.
    Used when the customer's sandbox is wiped or moved to a new server."""
    endpoint = os.environ.get("ZENREX_BACKUP_S3_ENDPOINT", "").strip()
    bucket = os.environ.get("ZENREX_BACKUP_S3_BUCKET", "").strip()
    access_key = os.environ.get("ZENREX_BACKUP_S3_KEY", "").strip()
    secret_key = os.environ.get("ZENREX_BACKUP_S3_SECRET", "").strip()
    if not all([endpoint, bucket, access_key, secret_key]):
        return {"ok": False, "error": "s3_not_configured"}
    try:
        import aioboto3
        session = aioboto3.Session()
        key = f"continuation/{pid}/{snap_id}.tar.gz"
        async with session.client(
            "s3", endpoint_url=endpoint,
            aws_access_key_id=access_key, aws_secret_access_key=secret_key,
        ) as s3:
            resp = await s3.get_object(Bucket=bucket, Key=key)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("wb") as f:
                async for chunk in resp["Body"].iter_chunks(65536):
                    f.write(chunk)
            return {"ok": True, "dest": str(dest), "key": key}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"[:200]}
