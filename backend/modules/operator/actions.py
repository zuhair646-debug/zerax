"""
Actions module — low-level GitHub / Railway / Vercel operations.
Each function accepts decrypted tokens (from vault) and performs one operation.
All secrets are kept in memory only; never logged or persisted.
"""
import base64
import httpx
from typing import Dict, Any, List, Optional


GITHUB_API = "https://api.github.com"
RAILWAY_API = "https://backboard.railway.com/graphql/v2"
VERCEL_API = "https://api.vercel.com"


# ──────────────────────────────────────────────────────────────────────────
# GitHub
# ──────────────────────────────────────────────────────────────────────────

async def github_test(token: str, repo: str) -> Dict[str, Any]:
    """Verify the token can read a repo. Returns repo meta or raises Exception."""
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(
            f"{GITHUB_API}/repos/{repo}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        if r.status_code == 401:
            raise Exception("GitHub token rejected (401). Regenerate with read+write contents scope.")
        if r.status_code == 404:
            raise Exception(f"Repo not found or no access: {repo}")
        r.raise_for_status()
        d = r.json()
        return {
            "full_name": d.get("full_name"),
            "default_branch": d.get("default_branch"),
            "private": d.get("private"),
            "updated_at": d.get("updated_at"),
            "html_url": d.get("html_url"),
        }


async def github_get_file(token: str, repo: str, path: str, branch: str = "main") -> Dict[str, Any]:
    """Fetch a single file's content + sha (needed to update it)."""
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(
            f"{GITHUB_API}/repos/{repo}/contents/{path}",
            params={"ref": branch},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        if r.status_code == 404:
            return {"exists": False}
        r.raise_for_status()
        d = r.json()
        try:
            content = base64.b64decode(d.get("content", "").encode()).decode("utf-8")
        except Exception:
            content = ""
        return {"exists": True, "sha": d.get("sha"), "content": content, "path": path}


async def github_put_file(
    token: str, repo: str, path: str, content: str, message: str, branch: str = "main"
) -> Dict[str, Any]:
    """Create or update a file. Auto-fetches sha if updating an existing file."""
    info = await github_get_file(token, repo, path, branch)
    body: Dict[str, Any] = {
        "message": message or f"Update {path}",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if info.get("exists"):
        body["sha"] = info["sha"]
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.put(
            f"{GITHUB_API}/repos/{repo}/contents/{path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json=body,
        )
        if r.status_code not in (200, 201):
            raise Exception(f"GitHub PUT failed ({r.status_code}): {r.text[:200]}")
        d = r.json()
        return {
            "sha": d.get("commit", {}).get("sha", ""),
            "html_url": d.get("commit", {}).get("html_url", ""),
            "path": path,
        }


# ──────────────────────────────────────────────────────────────────────────
# Railway (GraphQL)
# ──────────────────────────────────────────────────────────────────────────

async def _railway_call(token: str, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            RAILWAY_API,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"query": query, "variables": variables or {}},
        )
        r.raise_for_status()
        d = r.json()
        if "errors" in d and d["errors"]:
            msg = "; ".join(e.get("message", "?") for e in d["errors"])
            raise Exception(f"Railway: {msg}")
        return d.get("data", {})


async def railway_test(token: str) -> Dict[str, Any]:
    """Return the first few projects the token has access to."""
    q = "query { me { name email projects { edges { node { id name } } } } }"
    d = await _railway_call(token, q)
    me = d.get("me") or {}
    projects = [e["node"] for e in (me.get("projects", {}).get("edges") or [])]
    return {
        "name": me.get("name"),
        "email": me.get("email"),
        "projects": projects[:20],
    }


async def railway_redeploy(token: str, service_id: str, environment_id: str) -> Dict[str, Any]:
    """Trigger a redeploy of the current deployment."""
    q = """
    mutation($serviceId: String!, $environmentId: String!) {
      serviceInstanceRedeploy(serviceId: $serviceId, environmentId: $environmentId)
    }
    """
    d = await _railway_call(token, q, {"serviceId": service_id, "environmentId": environment_id})
    return {"triggered": bool(d.get("serviceInstanceRedeploy"))}


async def railway_latest_deploy(token: str, service_id: str, environment_id: str) -> Dict[str, Any]:
    """Fetch the latest deployment status + URL for a service."""
    q = """
    query($serviceId: String!, $environmentId: String!) {
      deployments(first: 1, input: {serviceId: $serviceId, environmentId: $environmentId}) {
        edges { node { id status createdAt staticUrl url canRedeploy } }
      }
    }
    """
    d = await _railway_call(token, q, {"serviceId": service_id, "environmentId": environment_id})
    edges = (d.get("deployments") or {}).get("edges") or []
    if not edges:
        return {"status": "none"}
    return edges[0]["node"]


async def railway_upsert_variable(
    token: str, project_id: str, environment_id: str, service_id: str, name: str, value: str
) -> Dict[str, Any]:
    """Create or update an environment variable on a Railway service."""
    q = """
    mutation($input: VariableUpsertInput!) { variableUpsert(input: $input) }
    """
    d = await _railway_call(
        token,
        q,
        {
            "input": {
                "projectId": project_id,
                "environmentId": environment_id,
                "serviceId": service_id,
                "name": name,
                "value": value,
            }
        },
    )
    return {"ok": bool(d.get("variableUpsert"))}


# ──────────────────────────────────────────────────────────────────────────
# Vercel
# ──────────────────────────────────────────────────────────────────────────

async def vercel_test(token: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(
            f"{VERCEL_API}/v2/user",
            headers={"Authorization": f"Bearer {token}"},
        )
        if r.status_code == 401:
            raise Exception("Vercel token rejected (401).")
        r.raise_for_status()
        u = r.json().get("user") or {}
        return {"id": u.get("id"), "username": u.get("username"), "email": u.get("email")}


async def vercel_list_projects(token: str) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(
            f"{VERCEL_API}/v9/projects?limit=20",
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return [
            {"id": p.get("id"), "name": p.get("name"), "framework": p.get("framework")}
            for p in (r.json().get("projects") or [])
        ]


async def vercel_redeploy(token: str, project_id: str) -> Dict[str, Any]:
    """Trigger a redeploy of the most recent production deployment."""
    async with httpx.AsyncClient(timeout=30) as c:
        dep = await c.get(
            f"{VERCEL_API}/v6/deployments?projectId={project_id}&limit=1&target=production",
            headers={"Authorization": f"Bearer {token}"},
        )
        dep.raise_for_status()
        arr = (dep.json().get("deployments") or [])
        if not arr:
            raise Exception("No previous deployment to redeploy")
        last = arr[0]
        r = await c.post(
            f"{VERCEL_API}/v13/deployments",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "name": last.get("name"),
                "deploymentId": last.get("uid"),
                "target": "production",
                "meta": {"trigger": "zitex-operator"},
            },
        )
        r.raise_for_status()
        d = r.json()
        return {"id": d.get("id"), "url": d.get("url"), "status": d.get("readyState")}
