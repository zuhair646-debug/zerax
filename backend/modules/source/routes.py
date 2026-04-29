"""
Source Code Downloader
──────────────────────
يسمح للـ owner بتصفّح وتحميل ملفات المشروع واحداً واحداً (لنقلها إلى GitHub repo خاص أو سيرفر آخر).

Security:
- يتطلب JWT للـ owner (Authorization header OR ?token=<jwt> query param)
- يقصر الوصول على whitelisted prefixes فقط (backend/, frontend/src/, frontend/public/, …)
- يمنع أي ملفات حسّاسة (.env, .git, node_modules, __pycache__, secrets)
- يمنع أي محاولة path traversal (..)
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pathlib import Path
from typing import List, Dict, Any, Optional
import os
import io
import zipfile
import time
import jwt as _jwt
import mimetypes


# Whitelisted top-level prefixes (relative to /app)
ALLOWED_PREFIXES = (
    "backend/",
    "frontend/src/",
    "frontend/public/",
    "frontend/package.json",
    "frontend/yarn.lock",
    "frontend/.env.example",
    "frontend/tailwind.config.js",
    "frontend/postcss.config.js",
    "frontend/craco.config.js",
    "frontend/jsconfig.json",
    "frontend/components.json",
    "backend/requirements.txt",
    "backend/.env.example",
    "README.md",
    "DEPLOY.md",
    "memory/PRD.md",
)

# Hard-blocked patterns — sensitive files / build artifacts / large dirs
BLOCKED_SUBSTRINGS = (
    ".git/",
    "node_modules/",
    "__pycache__/",
    ".pytest_cache/",
    ".DS_Store",
    "/build/",
    "/dist/",
    ".pyc",
    ".key",
    ".pem",
    ".zip",            # never include leftover zip artifacts
    "test_credentials",
    "credentials.json",
    "service-account",
    ".emergent/",
)


def _safe_resolve(rel_path: str) -> Path:
    """Resolve a relative path under /app safely. Raise 400 on traversal or 403 on blocked, 404 on missing."""
    if not rel_path or ".." in rel_path or rel_path.startswith("/"):
        raise HTTPException(400, "Invalid path")
    norm = rel_path.replace("\\", "/")
    # Block secret .env files (but allow .env.example, .env.template)
    if norm.endswith("/.env") or norm == ".env":
        raise HTTPException(403, "Blocked: .env file")
    for bad in BLOCKED_SUBSTRINGS:
        if bad in norm:
            raise HTTPException(403, f"Blocked path: {bad}")
    # Whitelist
    if not any(norm.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        raise HTTPException(403, "Path not in allowed source tree")
    full = (Path("/app") / rel_path).resolve()
    if not str(full).startswith("/app/"):
        raise HTTPException(400, "Path outside /app")
    if not full.exists():
        raise HTTPException(404, "File not found")
    return full


def _is_secret_env(rel_path: str) -> bool:
    """Returns True iff this is an actual secret .env (not .env.example/.template)."""
    p = rel_path.replace("\\", "/")
    return p.endswith("/.env") or p == ".env"


def init_routes(database, auth_dep) -> APIRouter:
    r = APIRouter(prefix="/source", tags=["source"])

    JWT_SECRET = os.environ.get("JWT_SECRET", "change-me")

    async def _flex_auth(request: Request, token: Optional[str] = Query(None)) -> dict:
        """
        Owner auth that works via either:
          • Authorization: Bearer <jwt>  (used by the SourceBrowser UI)
          • ?token=<jwt> in the URL       (used by direct browser links)
        """
        raw = ""
        auth_h = request.headers.get("authorization") or ""
        if auth_h.lower().startswith("bearer "):
            raw = auth_h.split(" ", 1)[1].strip()
        if not raw and token:
            raw = token.strip()
        if not raw:
            raise HTTPException(401, "Missing token. Pass Authorization: Bearer <jwt> header OR ?token=<jwt> in URL.")
        try:
            payload = _jwt.decode(raw, JWT_SECRET, algorithms=["HS256"])
        except _jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token expired")
        except _jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")
        if not payload.get("user_id"):
            raise HTTPException(401, "Invalid token payload")
        if payload.get("role") != "owner":
            raise HTTPException(403, "Owner access only")
        return {"user_id": payload["user_id"], "role": payload.get("role")}

    @r.get("/manifest")
    async def _manifest(current_user: dict = Depends(_flex_auth)):
        """
        Owner-only — return the full file tree (relative paths + sizes) of the codebase
        for download. Excludes any sensitive/blocked file.
        """
        root = Path("/app")
        out: List[Dict[str, Any]] = []
        for prefix in ALLOWED_PREFIXES:
            full = root / prefix
            if full.is_file():
                out.append({
                    "path": prefix,
                    "size": full.stat().st_size,
                    "type": "file",
                })
                continue
            if not full.is_dir():
                continue
            for fp in full.rglob("*"):
                if not fp.is_file():
                    continue
                rel = str(fp.relative_to(root)).replace("\\", "/")
                if any(bad in rel for bad in BLOCKED_SUBSTRINGS):
                    continue
                if _is_secret_env(rel):
                    continue
                try:
                    sz = fp.stat().st_size
                except Exception:
                    continue
                # Skip very large files (>2 MB) — likely binary assets
                if sz > 2 * 1024 * 1024:
                    continue
                out.append({"path": rel, "size": sz, "type": "file"})
        # Sort by path for stable order
        out.sort(key=lambda x: x["path"])
        return {"files": out, "total": len(out), "root": "/app"}

    @r.get("/file")
    async def _file(
        path: str = Query(..., description="Relative path under /app (e.g. backend/server.py)"),
        current_user: dict = Depends(_flex_auth),
    ):
        """Owner-only — return the raw text content of a single source file."""
        full = _safe_resolve(path)
        try:
            text = full.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise HTTPException(415, "Binary file — not downloadable as text")
        # Determine content-type for browser hint
        ctype, _ = mimetypes.guess_type(str(full))
        if not ctype or not ctype.startswith("text/"):
            ctype = "text/plain; charset=utf-8"
        return PlainTextResponse(content=text, media_type=ctype)

    @r.get("/info")
    async def _info(
        path: str = Query(...),
        current_user: dict = Depends(_flex_auth),
    ):
        """Owner-only — return metadata for a single file (size, lines, mtime)."""
        full = _safe_resolve(path)
        st = full.stat()
        try:
            text = full.read_text(encoding="utf-8")
            lines = text.count("\n") + (0 if text.endswith("\n") else 1)
        except Exception:
            lines = 0
        return {
            "path": path,
            "size": st.st_size,
            "lines": lines,
            "mtime": int(st.st_mtime),
        }

    # ─────────────────────────────────────────────────────────────────
    # ZIP exports — bulk download whole project or specific folder
    # ─────────────────────────────────────────────────────────────────
    def _build_zip(prefix_filter: str = "") -> bytes:
        """
        Walk the allowed prefixes (optionally restricted to a single one) and
        zip every safe file into an in-memory archive. Returns the bytes.
        """
        root = Path("/app")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for prefix in ALLOWED_PREFIXES:
                if prefix_filter and not prefix.startswith(prefix_filter):
                    continue
                full = root / prefix
                if full.is_file():
                    rel = prefix
                    if any(bad in rel for bad in BLOCKED_SUBSTRINGS) or _is_secret_env(rel):
                        continue
                    try:
                        zf.write(full, arcname=rel)
                    except Exception:
                        pass
                    continue
                if not full.is_dir():
                    continue
                for fp in full.rglob("*"):
                    if not fp.is_file():
                        continue
                    rel = str(fp.relative_to(root)).replace("\\", "/")
                    if prefix_filter and not rel.startswith(prefix_filter):
                        continue
                    if any(bad in rel for bad in BLOCKED_SUBSTRINGS) or _is_secret_env(rel):
                        continue
                    try:
                        if fp.stat().st_size > 5 * 1024 * 1024:
                            continue
                        zf.write(fp, arcname=rel)
                    except Exception:
                        continue
        return buf.getvalue()

    @r.get("/zip")
    async def _zip_all(current_user: dict = Depends(_flex_auth)):
        """Owner-only — full project ZIP, ready to push to GitHub or upload to a server."""
        data = _build_zip()
        ts = time.strftime("%Y%m%d-%H%M%S")
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="zitex-{ts}.zip"',
                "Content-Length": str(len(data)),
            },
        )

    @r.get("/zip-folder")
    async def _zip_folder(
        prefix: str = Query(..., description="Folder prefix (e.g. 'backend/' or 'frontend/src/')"),
        current_user: dict = Depends(_flex_auth),
    ):
        """Owner-only — ZIP of a single folder/prefix."""
        prefix = prefix.strip().rstrip("/") + "/"
        if not any(p.startswith(prefix) or prefix.startswith(p) for p in ALLOWED_PREFIXES):
            raise HTTPException(400, "Prefix not in allowed source tree")
        data = _build_zip(prefix_filter=prefix)
        if not data or len(data) < 22:  # empty zip header is 22 bytes
            raise HTTPException(404, "No files matched this prefix")
        ts = time.strftime("%Y%m%d-%H%M%S")
        safe = prefix.replace("/", "-").rstrip("-") or "all"
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="zitex-{safe}-{ts}.zip"',
                "Content-Length": str(len(data)),
            },
        )

    @r.get("/links")
    async def _links(request: Request, current_user: dict = Depends(_flex_auth)):
        """
        Owner-only — returns a ready-to-click URL list (with the JWT embedded as ?token=)
        so the owner can simply paste each link into a new browser tab and view/copy code.
        """
        # Extract the raw token used for this request
        auth_h = request.headers.get("authorization") or ""
        raw_token = ""
        if auth_h.lower().startswith("bearer "):
            raw_token = auth_h.split(" ", 1)[1].strip()
        # Fallback: ?token= query (would have authenticated _flex_auth already)
        if not raw_token:
            raw_token = request.query_params.get("token") or ""

        base = str(request.base_url).rstrip("/")
        # Build manifest first
        root = Path("/app")
        files: List[Dict[str, Any]] = []
        for prefix in ALLOWED_PREFIXES:
            full = root / prefix
            if full.is_file():
                rel = prefix
                if any(b in rel for b in BLOCKED_SUBSTRINGS) or _is_secret_env(rel):
                    continue
                files.append({"path": rel, "size": full.stat().st_size})
                continue
            if not full.is_dir():
                continue
            for fp in full.rglob("*"):
                if not fp.is_file():
                    continue
                rel = str(fp.relative_to(root)).replace("\\", "/")
                if any(b in rel for b in BLOCKED_SUBSTRINGS) or _is_secret_env(rel):
                    continue
                try:
                    sz = fp.stat().st_size
                except Exception:
                    continue
                if sz > 2 * 1024 * 1024:
                    continue
                files.append({"path": rel, "size": sz})
        files.sort(key=lambda x: x["path"])

        out_files = [
            {
                "path": f["path"],
                "size": f["size"],
                "url": f"{base}/api/source/file?path={f['path']}&token={raw_token}",
            }
            for f in files
        ]

        return {
            "zip_full": f"{base}/api/source/zip?token={raw_token}",
            "zip_backend": f"{base}/api/source/zip-folder?prefix=backend/&token={raw_token}",
            "zip_frontend_src": f"{base}/api/source/zip-folder?prefix=frontend/src/&token={raw_token}",
            "manifest": f"{base}/api/source/manifest?token={raw_token}",
            "files": out_files,
            "total": len(out_files),
            "instructions_ar": (
                "1) لتحميل المشروع كاملاً ZIP: افتح zip_full في تبويب جديد. "
                "2) لعرض أي ملف نص خام: افتح أي رابط من files[i].url — انسخ المحتوى والصقه في GitHub. "
                "3) الروابط صالحة لمدة صلاحية الـ JWT الحالي (24 ساعة عادةً)."
            ),
        }

    return r
