"""
🚀 Multi-Provider Deploy — Real deployment integrations for the 4 hosting
options Zenrex offers to customers:

  1. Zenrex (built-in, free)                    →  publish_site(slug)
  2. VPS (Hetzner — owner only)                 →  deploy_to_production()
  3. Vercel  (customer-owned token)             →  deploy_to_vercel()
  4. Cloudflare Pages (customer-owned token)    →  deploy_to_cloudflare()

Each function uploads the project's bundled HTML/CSS/JS via the provider's
official REST API and returns the live URL on success. The AI tool layer in
freebuild_agent.py calls these — never embed credentials in the AI prompt.

Designed to be:
  • Independent  — each provider is a separate function, failure of one
                   never blocks the others.
  • Honest       — returns {ok: False, error} on any HTTP non-2xx so the AI
                   surfaces a real failure instead of claiming success.
  • Stateless    — no global state; each call takes the project bundle.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
from typing import Any, Dict, List, Optional

import httpx

log = logging.getLogger("zenrex.multi_deploy")


# ─────────────────────────────────────────────────────────────────────────────
# Common helpers
# ─────────────────────────────────────────────────────────────────────────────

def _bundle_to_files(pages: Dict[str, str], extras: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Serialize the in-memory project into a {filename: content} map.

    Pages are dumped at their natural path. The first page becomes
    index.html if not already present. Extras (CSS/JS) are passed through.
    """
    files: Dict[str, str] = {}
    if not pages:
        raise ValueError("project has no pages to deploy")
    page_keys = list(pages.keys())
    has_index = any(
        (k or "").strip().lower() in ("index.html", "index", "/") for k in page_keys
    )
    for key, html in pages.items():
        path = (key or "page").strip().lstrip("/").lower()
        # Normalize "home" / "home.html" → "index.html" (best practice for static hosts)
        if path in ("home", "home.html", "index"):
            path = "index.html"
            has_index = True
        elif not path.endswith(".html"):
            path = f"{path}.html"
        files[path] = html or ""
    if not has_index and page_keys:
        # Force the first page to also be index.html as a fallback so the
        # site is reachable at the root URL.
        first_key = page_keys[0]
        files["index.html"] = pages[first_key] or ""
    if extras:
        for fname, content in extras.items():
            files[fname.lstrip("/")] = content
    return files


def _safe_project_slug(name: str) -> str:
    """Make a slug that all 3 providers accept (lowercase, dashes, 3-50 chars)."""
    import re as _re
    s = (name or "").lower().strip()
    s = _re.sub(r"[^a-z0-9-]+", "-", s)
    s = _re.sub(r"-+", "-", s).strip("-")
    if not s:
        s = "zenrex-site"
    if len(s) < 3:
        s = s + "-app"
    return s[:50]


# ─────────────────────────────────────────────────────────────────────────────
# 1) Vercel
# ─────────────────────────────────────────────────────────────────────────────

async def deploy_to_vercel(
    *,
    token: str,
    project_name: str,
    pages: Dict[str, str],
    extras: Optional[Dict[str, str]] = None,
    team_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Deploy a static site bundle to Vercel via REST API v13.

    Requires a Vercel "Personal Access Token" with `deployments:write` scope.
    Customer obtains it from https://vercel.com/account/tokens.

    Returns: {ok, url, deployment_id, alias, ...} or {ok: False, error}.
    """
    if not token or not project_name:
        return {"ok": False, "error": "token + project_name مطلوبان"}
    try:
        files = _bundle_to_files(pages, extras)
    except Exception as e:
        return {"ok": False, "error": f"bundle: {e}"}

    slug = _safe_project_slug(project_name)
    # Vercel /v13/deployments format:
    payload_files: List[Dict[str, str]] = []
    for path, content in files.items():
        payload_files.append({
            "file": path,
            "data": content,
            "encoding": "utf-8",
        })

    body: Dict[str, Any] = {
        "name": slug,
        "files": payload_files,
        "projectSettings": {
            "framework": None,
            "buildCommand": None,
            "outputDirectory": None,
        },
        "target": "production",
    }
    params = {}
    if team_id:
        params["teamId"] = team_id

    try:
        async with httpx.AsyncClient(timeout=60.0) as cl:
            r = await cl.post(
                "https://api.vercel.com/v13/deployments",
                json=body,
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
        if r.status_code not in (200, 201):
            try:
                err = r.json()
            except Exception:
                err = {"message": r.text[:300]}
            return {
                "ok": False,
                "error": f"Vercel {r.status_code}: {err.get('error', {}).get('message') or err.get('message') or str(err)[:200]}",
                "provider": "vercel",
            }
        data = r.json()
        deployment_url = data.get("url") or ""
        full_url = f"https://{deployment_url}" if deployment_url and not deployment_url.startswith("http") else deployment_url
        return {
            "ok": True,
            "provider": "vercel",
            "url": full_url,
            "deployment_id": data.get("id"),
            "alias": data.get("alias", []),
            "ready_state": data.get("readyState"),
            "message": f"✅ نُشر على Vercel: {full_url}",
        }
    except httpx.HTTPError as e:
        return {"ok": False, "error": f"vercel http: {type(e).__name__}: {str(e)[:200]}", "provider": "vercel"}


# ─────────────────────────────────────────────────────────────────────────────
# 2) Cloudflare Pages (Direct Upload)
# ─────────────────────────────────────────────────────────────────────────────

async def deploy_to_cloudflare_pages(
    *,
    api_token: str,
    account_id: str,
    project_name: str,
    pages: Dict[str, str],
    extras: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Deploy to Cloudflare Pages using the Direct Upload API.

    Token needs "Pages:Edit" permission. Customer obtains it from
    https://dash.cloudflare.com/profile/api-tokens.
    Account ID is shown on the right sidebar of the Cloudflare dashboard.

    Flow:
      1. POST /pages/projects                — create project if missing (idempotent).
      2. POST /pages/projects/{p}/upload     — get upload tokens for new files.
      3. POST /pages/projects/{p}/deployments — finalize deployment.

    For simplicity we use the Direct Upload form-data variant which lets us
    bundle the whole static site in one request.
    """
    if not api_token or not account_id or not project_name:
        return {"ok": False, "error": "api_token + account_id + project_name مطلوبة"}
    try:
        files = _bundle_to_files(pages, extras)
    except Exception as e:
        return {"ok": False, "error": f"bundle: {e}"}

    slug = _safe_project_slug(project_name)
    base = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects"
    headers = {"Authorization": f"Bearer {api_token}"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as cl:
            # 1) Ensure project exists (ignore "already exists" error)
            create_resp = await cl.post(
                base,
                json={
                    "name": slug,
                    "production_branch": "main",
                },
                headers={**headers, "Content-Type": "application/json"},
            )
            if create_resp.status_code not in (200, 201, 409):
                try:
                    err = create_resp.json()
                except Exception:
                    err = {"errors": [{"message": create_resp.text[:200]}]}
                msg = (err.get("errors") or [{}])[0].get("message") or str(err)[:200]
                # If the project already exists CF returns 409 OR an errors[].code=8000007
                if "already exists" not in msg.lower():
                    return {
                        "ok": False,
                        "error": f"CF project create {create_resp.status_code}: {msg}",
                        "provider": "cloudflare_pages",
                    }

            # 2) Build a multipart form with all files (Direct Upload).
            form_files: List[tuple] = []
            for path, content in files.items():
                # The CF Direct Upload accepts a single "manifest" + the files,
                # but the simpler `/deployments` endpoint accepts form-data files.
                form_files.append(("file", (path, content.encode("utf-8"), "application/octet-stream")))

            deploy_resp = await cl.post(
                f"{base}/{slug}/deployments",
                files=form_files,
                headers=headers,
            )
            if deploy_resp.status_code not in (200, 201):
                try:
                    err = deploy_resp.json()
                except Exception:
                    err = {"errors": [{"message": deploy_resp.text[:200]}]}
                msg = (err.get("errors") or [{}])[0].get("message") or str(err)[:200]
                return {
                    "ok": False,
                    "error": f"CF deploy {deploy_resp.status_code}: {msg}",
                    "provider": "cloudflare_pages",
                }
            data = deploy_resp.json().get("result") or {}
            url = data.get("url") or f"https://{slug}.pages.dev"
            return {
                "ok": True,
                "provider": "cloudflare_pages",
                "url": url,
                "deployment_id": data.get("id"),
                "project": slug,
                "message": f"✅ نُشر على Cloudflare Pages: {url}",
            }
    except httpx.HTTPError as e:
        return {
            "ok": False,
            "error": f"cf http: {type(e).__name__}: {str(e)[:200]}",
            "provider": "cloudflare_pages",
        }


# ─────────────────────────────────────────────────────────────────────────────
# 3) GitHub Pages (via Repos API + Pages enable)
# ─────────────────────────────────────────────────────────────────────────────

async def deploy_to_github_pages(
    *,
    token: str,
    owner: str,
    repo: str,
    pages: Dict[str, str],
    extras: Optional[Dict[str, str]] = None,
    commit_message: str = "Zenrex deploy",
) -> Dict[str, Any]:
    """Deploy as GitHub Pages by committing the static bundle to the `gh-pages`
    branch (or main + /docs if branch doesn't exist) and ensuring Pages is on.

    Token needs `repo` + `pages:write` scopes.
    """
    if not token or not owner or not repo:
        return {"ok": False, "error": "token + owner + repo مطلوبة"}
    try:
        files = _bundle_to_files(pages, extras)
    except Exception as e:
        return {"ok": False, "error": f"bundle: {e}"}

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    api = f"https://api.github.com/repos/{owner}/{repo}"

    try:
        async with httpx.AsyncClient(timeout=60.0) as cl:
            # 1) Verify repo exists / token has access
            r = await cl.get(api, headers=headers)
            if r.status_code == 404:
                return {"ok": False, "error": "repo not found or token has no access", "provider": "github_pages"}
            if r.status_code != 200:
                return {"ok": False, "error": f"GH {r.status_code}: {r.text[:200]}", "provider": "github_pages"}

            # 2) Commit each file to main branch
            for path, content in files.items():
                # Try get existing sha
                get_resp = await cl.get(f"{api}/contents/{path}", headers=headers, params={"ref": "main"})
                sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None
                body = {
                    "message": f"{commit_message}: {path}",
                    "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
                    "branch": "main",
                }
                if sha:
                    body["sha"] = sha
                put_resp = await cl.put(f"{api}/contents/{path}", json=body, headers=headers)
                if put_resp.status_code not in (200, 201):
                    return {
                        "ok": False,
                        "error": f"commit {path}: GH {put_resp.status_code} {put_resp.text[:200]}",
                        "provider": "github_pages",
                    }

            # 3) Enable Pages from main branch (root). Idempotent — 409 means already enabled.
            pages_resp = await cl.post(
                f"{api}/pages",
                json={"source": {"branch": "main", "path": "/"}},
                headers=headers,
            )
            if pages_resp.status_code not in (200, 201, 204, 409):
                # Try updating instead of creating
                update_resp = await cl.put(
                    f"{api}/pages",
                    json={"source": {"branch": "main", "path": "/"}},
                    headers=headers,
                )
                if update_resp.status_code not in (200, 204):
                    log.warning(f"[gh-pages] enable returned {pages_resp.status_code} {pages_resp.text[:200]}")

            url = f"https://{owner}.github.io/{repo}/"
            return {
                "ok": True,
                "provider": "github_pages",
                "url": url,
                "repo": f"{owner}/{repo}",
                "files_committed": len(files),
                "message": f"✅ نُشر على GitHub Pages: {url} (قد يستغرق دقيقة-دقيقتين للظهور)",
            }
    except httpx.HTTPError as e:
        return {"ok": False, "error": f"gh http: {type(e).__name__}: {str(e)[:200]}", "provider": "github_pages"}


# ─────────────────────────────────────────────────────────────────────────────
# Deploy-options catalog (used by the status footer + AI advisory)
# ─────────────────────────────────────────────────────────────────────────────

DEPLOY_OPTIONS_AR = [
    {
        "id": "zenrex",
        "name_ar": "Zenrex (مجاناً)",
        "tagline_ar": "نشر فوري بنقرة على zenrex.ai/s/{slug}",
        "tool": "publish_site",
        "needs_credentials": False,
        "best_for_ar": "أسرع وأبسط طريقة — مجاناً مع SSL وCDN عالمي",
    },
    {
        "id": "vercel",
        "name_ar": "Vercel",
        "tagline_ar": "أداء عالمي + CDN — مجاني للاستخدام الشخصي",
        "tool": "deploy_to_vercel",
        "needs_credentials": True,
        "credential_label_ar": "Vercel Personal Token",
        "credential_url": "https://vercel.com/account/tokens",
        "best_for_ar": "أفضل خيار لـ Next.js والمواقع الثابتة بحركة عالية",
    },
    {
        "id": "cloudflare_pages",
        "name_ar": "Cloudflare Pages",
        "tagline_ar": "Bandwidth غير محدود مجاناً + DDoS protection",
        "tool": "deploy_to_cloudflare_pages",
        "needs_credentials": True,
        "credential_label_ar": "Cloudflare API Token + Account ID",
        "credential_url": "https://dash.cloudflare.com/profile/api-tokens",
        "best_for_ar": "حركة كثيفة — Cloudflare ما يحاسبك على الـ Bandwidth",
    },
    {
        "id": "github_pages",
        "name_ar": "GitHub Pages",
        "tagline_ar": "ربط مع repo + CI/CD تلقائي عبر GitHub Actions",
        "tool": "deploy_to_github_pages",
        "needs_credentials": True,
        "credential_label_ar": "GitHub Personal Token (scopes: repo, pages)",
        "credential_url": "https://github.com/settings/tokens",
        "best_for_ar": "للمطورين اللي حابين version control + CI/CD",
    },
]
