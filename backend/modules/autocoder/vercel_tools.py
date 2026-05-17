"""
Vercel API tools — frontend deployment monitoring + control.

Lets the Auto-Coder:
  • Check the latest Vercel deployment status (parallel to Railway for backend)
  • Fetch deployment logs (if a frontend build fails)
  • List environment variables on Vercel
  • Trigger a redeploy

API docs: https://vercel.com/docs/rest-api/reference
"""
from __future__ import annotations
import os
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

API_BASE = "https://api.vercel.com"


# Bound by autocoder __init__ — provides {token, org, project}
_get_creds = None


def bind_creds_getter(fn):
    global _get_creds
    _get_creds = fn


async def _vercel_get(path: str, params: Optional[Dict] = None) -> Dict:
    import httpx
    c = await _creds()
    if not c.get("token"):
        return {"_error": "VERCEL_TOKEN missing (env or vault)"}
    p = dict(params or {})
    if c.get("org"):
        p["teamId"] = c["org"]
    headers = {"Authorization": f"Bearer {c['token']}"}
    async with httpx.AsyncClient(timeout=20) as cli:
        r = await cli.get(f"{API_BASE}{path}", headers=headers, params=p)
    try:
        return r.json()
    except Exception:
        return {"_error": f"HTTP {r.status_code}: {r.text[:200]}"}


async def _vercel_post(path: str, body: Dict, params: Optional[Dict] = None) -> Dict:
    import httpx
    c = await _creds()
    if not c.get("token"):
        return {"_error": "VERCEL_TOKEN missing"}
    p = dict(params or {})
    if c.get("org"):
        p["teamId"] = c["org"]
    headers = {"Authorization": f"Bearer {c['token']}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as cli:
        r = await cli.post(f"{API_BASE}{path}", headers=headers, params=p, json=body)
    try:
        return r.json()
    except Exception:
        return {"_error": f"HTTP {r.status_code}: {r.text[:200]}"}


async def _creds():
    if _get_creds is None:
        return {"token": "", "org": "", "project": ""}
    return await _get_creds()


async def tool_vercel_check_deployment() -> Dict[str, Any]:
    """🔍 Get latest Vercel deployment for the configured project."""
    c = await _creds()
    if not c.get("project"):
        return {"ok": False, "error": "VERCEL_PROJECT_ID missing"}
    res = await _vercel_get("/v6/deployments", {"projectId": c["project"], "limit": 5})
    if "_error" in res:
        return {"ok": False, "error": res["_error"]}
    deps = res.get("deployments", [])
    if not deps:
        return {"ok": True, "verdict": "❓ ما لقينا أي deployment", "recent": []}
    out = []
    for d in deps[:5]:
        out.append({
            "uid": d.get("uid") or d.get("id"),
            "state": d.get("state") or d.get("readyState"),
            "url": d.get("url"),
            "created": d.get("createdAt"),
            "commit_msg": (d.get("meta", {}).get("githubCommitMessage") or "")[:80],
            "commit_sha": (d.get("meta", {}).get("githubCommitSha") or "")[:8],
            "branch": d.get("meta", {}).get("githubCommitRef") or "",
        })
    latest = out[0]
    state = latest["state"]
    verdict = (
        "✅ آخر Vercel deploy ناجح" if state in ("READY",)
        else "⏳ لسه يبني" if state in ("BUILDING", "QUEUED", "INITIALIZING")
        else f"❌ {state}" if state in ("ERROR", "CANCELED")
        else f"❓ {state}"
    )
    return {"ok": True, "latest": latest, "recent": out, "verdict": verdict}


async def tool_vercel_build_logs(deployment_id: Optional[str] = None, limit: int = 200) -> Dict[str, Any]:
    """📜 Vercel build/runtime logs for a specific deployment (or latest)."""
    if not deployment_id:
        latest = await tool_vercel_check_deployment()
        if not latest.get("ok") or not latest.get("latest"):
            return {"ok": False, "error": "could not resolve latest deployment"}
        deployment_id = latest["latest"]["uid"]
    res = await _vercel_get(f"/v2/deployments/{deployment_id}/events", {"limit": int(limit), "direction": "backward"})
    if "_error" in res:
        return {"ok": False, "error": res["_error"]}
    events = res if isinstance(res, list) else res.get("events", [])
    lines = []
    errs = []
    for e in events:
        msg = e.get("payload", {}).get("text") or e.get("text") or ""
        if not msg.strip():
            continue
        lines.append(msg[:300])
        if any(k in msg.lower() for k in ("error", "fail", "cannot")):
            errs.append(msg[:300])
    return {
        "ok": True, "deployment_id": deployment_id,
        "line_count": len(lines),
        "text_tail": "\n".join(lines[-100:])[:12000],
        "likely_errors": errs[-10:],
    }


async def tool_vercel_redeploy() -> Dict[str, Any]:
    """🚀 Re-trigger the latest Vercel deployment (rebuild from same commit)."""
    latest = await tool_vercel_check_deployment()
    if not latest.get("ok") or not latest.get("latest"):
        return {"ok": False, "error": "no deployment to redeploy"}
    deployment_uid = latest["latest"]["uid"]
    res = await _vercel_post("/v13/deployments?forceNew=1", {"deploymentId": deployment_uid})
    if "_error" in res:
        return {"ok": False, "error": res["_error"]}
    return {"ok": True, "new_deployment": res.get("id") or res.get("uid"),
            "url": res.get("url"), "verdict": "🚀 Vercel redeploy triggered"}


async def tool_vercel_env_vars(action: str = "list", key: Optional[str] = None, value: Optional[str] = None,
                                target: List[str] = None) -> Dict[str, Any]:
    """🔑 Manage Vercel environment variables. action: list|set|unset."""
    c = await _creds()
    if not c.get("project"):
        return {"ok": False, "error": "VERCEL_PROJECT_ID missing"}
    if action == "list":
        res = await _vercel_get(f"/v9/projects/{c['project']}/env", {"decrypt": "false"})
        if "_error" in res:
            return {"ok": False, "error": res["_error"]}
        envs = res.get("envs", [])
        keys = sorted({e["key"] for e in envs})
        return {"ok": True, "keys": keys, "count": len(keys),
                "by_target": {e["key"]: e.get("target") for e in envs[:30]}}
    if action == "set":
        if not key or value is None:
            return {"ok": False, "error": "key + value required"}
        res = await _vercel_post(f"/v10/projects/{c['project']}/env",
                                  {"key": key, "value": value, "type": "encrypted",
                                   "target": target or ["production", "preview", "development"]})
        if "_error" in res:
            return {"ok": False, "error": res["_error"]}
        return {"ok": True, "set": key, "verdict": "✅ — اعمل redeploy عشان يتفعّل"}
    if action == "unset":
        if not key:
            return {"ok": False, "error": "key required"}
        # Have to find env id first
        listing = await _vercel_get(f"/v9/projects/{c['project']}/env")
        if "_error" in listing:
            return {"ok": False, "error": listing["_error"]}
        target_envs = [e for e in listing.get("envs", []) if e["key"] == key]
        if not target_envs:
            return {"ok": False, "error": f"key {key} not found"}
        import httpx
        creds = c
        async with httpx.AsyncClient(timeout=15) as cli:
            for env in target_envs:
                await cli.delete(
                    f"{API_BASE}/v9/projects/{creds['project']}/env/{env['id']}",
                    headers={"Authorization": f"Bearer {creds['token']}"},
                    params={"teamId": creds.get("org") or ""},
                )
        return {"ok": True, "unset": key, "removed_count": len(target_envs)}
    return {"ok": False, "error": "action must be list|set|unset"}


# ════════════════════════════════════════════════════════════════════════
# Anthropic schemas
# ════════════════════════════════════════════════════════════════════════
VERCEL_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "vercel_check_deployment",
        "description": "🔍 يفحص آخر deploy على Vercel ويرجع status (READY/BUILDING/ERROR) + commit + URL.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "vercel_build_logs",
        "description": "📜 logs بناء Vercel (افتراضياً آخر deploy). يبرز سطور الأخطاء.",
        "input_schema": {"type": "object", "properties": {
            "deployment_id": {"type": "string"}, "limit": {"type": "integer"},
        }, "required": []},
    },
    {
        "name": "vercel_redeploy",
        "description": "🚀 يعيد بناء آخر deploy على Vercel (force rebuild من نفس الـcommit).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "vercel_env_vars",
        "description": "🔑 إدارة متغيرات Vercel. action: list|set|unset. set يحتاج key+value + اختياري target=['production','preview','development'].",
        "input_schema": {"type": "object", "properties": {
            "action": {"type": "string", "enum": ["list", "set", "unset"]},
            "key": {"type": "string"}, "value": {"type": "string"},
            "target": {"type": "array", "items": {"type": "string"}},
        }, "required": ["action"]},
    },
]


VERCEL_TOOL_HANDLERS = {
    "vercel_check_deployment": tool_vercel_check_deployment,
    "vercel_build_logs": tool_vercel_build_logs,
    "vercel_redeploy": tool_vercel_redeploy,
    "vercel_env_vars": tool_vercel_env_vars,
}


VERCEL_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "vercel_check_deployment", "desc": "latest Vercel deploy status", "args": []},
    {"name": "vercel_build_logs", "desc": "Vercel build logs", "args": ["deployment_id?", "limit?"]},
    {"name": "vercel_redeploy", "desc": "force Vercel rebuild", "args": []},
    {"name": "vercel_env_vars", "desc": "list/set/unset Vercel env", "args": ["action", "key?", "value?", "target?"]},
]


def vercel_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in VERCEL_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return f"⏵✗ {(result.get('error') or '')[:120]}"
    if name == "vercel_check_deployment":
        lat = result.get("latest")
        return f"⏵ {lat['state']} | {lat.get('commit_sha','')}" if lat else "⏵ no deploy"
    if name == "vercel_redeploy":
        return "🚀 vercel redeploy ok"
    if name == "vercel_env_vars":
        if result.get("keys"):
            return f"🔑 vercel: {result['count']} متغير"
        if result.get("set"):
            return f"🔑 vercel set {result['set']}"
    if name == "vercel_build_logs":
        return f"📜 {result.get('line_count', 0)} سطر · {len(result.get('likely_errors',[]))} خطأ"
    return None


def vercel_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in VERCEL_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return None
    if name == "vercel_check_deployment":
        lat = result.get("latest", {})
        return f"State: {lat.get('state')}\nURL: {lat.get('url')}\nCommit: {lat.get('commit_sha','')} | {lat.get('commit_msg','')[:80]}"
    if name == "vercel_build_logs":
        out = []
        if result.get("likely_errors"):
            out.append("⚠️ أخطاء:")
            out.extend(f"  {x[:200]}" for x in result["likely_errors"][-5:])
        out.append((result.get("text_tail") or "")[-600:])
        return "\n".join(out)[:1500]
    if name == "vercel_env_vars" and result.get("keys"):
        return "🔑 keys:\n  " + "\n  ".join(result["keys"][:20])
    return None
