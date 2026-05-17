"""
Railway API tools — self-deploy + debug logs.

Lets the Auto-Coder:
  • Trigger a redeploy after a fix (without waiting for GitHub webhook)
  • Fetch build logs of any deployment (to diagnose why a build failed)
  • Fetch runtime logs of the active deployment
  • Trigger a rollback to a known-good deployment
"""
from __future__ import annotations
import os
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://backboard.railway.com/graphql/v2"


async def _railway_query(token: str, query: str, variables: Optional[Dict] = None) -> Dict:
    import httpx
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            GRAPHQL_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"query": query, "variables": variables or {}},
        )
        return r.json()


# Lazy bound by autocoder __init__ to share _get_railway_creds
_get_creds = None


def bind_creds_getter(fn):
    global _get_creds
    _get_creds = fn


async def _creds():
    if _get_creds is None:
        raise RuntimeError("railway_tools not bound — call bind_creds_getter()")
    return await _get_creds()


async def tool_railway_redeploy() -> Dict[str, Any]:
    """🚂 Trigger a fresh Railway deployment of the latest commit on the configured service.
    Use this AFTER a `git_commit_push` if you don't want to wait for the GitHub webhook,
    or if the auto-deploy doesn't seem to be picking up new commits.
    """
    c = await _creds()
    if not c["token"] or not c["service"] or not c["env"]:
        return {"ok": False, "error": "Railway creds missing (token/service/env)"}
    q = (
        'mutation Redeploy($s: String!, $e: String!) { '
        'serviceInstanceRedeploy(serviceId: $s, environmentId: $e) }'
    )
    try:
        data = await _railway_query(c["token"], q, {"s": c["service"], "e": c["env"]})
        if "errors" in data:
            return {"ok": False, "error": str(data["errors"])[:300]}
        return {"ok": True, "triggered": True,
                "verdict": "🚂 redeploy triggered — انتظر 3-5 دقائق ثم check_deployment_status"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


async def tool_railway_build_logs(deployment_id: Optional[str] = None, limit: int = 200) -> Dict[str, Any]:
    """📜 Get build logs of a specific deployment (or the latest one if omitted).
    Vital for diagnosing why a Railway build failed (dependency conflicts,
    missing files, OOM, etc.).
    """
    c = await _creds()
    if not c["token"]:
        return {"ok": False, "error": "RAILWAY_TOKEN missing"}

    if not deployment_id:
        # Auto-pick the most recent deployment
        q_list = (
            'query Deps($p: String, $s: String!, $e: String!) { '
            'deployments(first: 1, input: { projectId: $p, serviceId: $s, environmentId: $e }) { '
            '  edges { node { id status } } } }'
        )
        try:
            data = await _railway_query(c["token"], q_list, {
                "p": c["project"] or None, "s": c["service"], "e": c["env"],
            })
            edges = (data.get("data", {}).get("deployments") or {}).get("edges", [])
            if not edges:
                return {"ok": False, "error": "no deployments found"}
            deployment_id = edges[0]["node"]["id"]
        except Exception as e:
            return {"ok": False, "error": f"failed to list deployments: {e}"}

    q = (
        'query Logs($id: String!, $limit: Int) { '
        'buildLogs(deploymentId: $id, limit: $limit) { message timestamp severity } }'
    )
    try:
        data = await _railway_query(c["token"], q, {"id": deployment_id, "limit": int(limit)})
        if "errors" in data:
            return {"ok": False, "error": str(data["errors"])[:300]}
        logs = (data.get("data") or {}).get("buildLogs") or []
        # Compress to text
        lines = []
        for lo in logs:
            msg = (lo.get("message") or "").rstrip()
            if not msg.strip():
                continue
            sev = (lo.get("severity") or "")[:4]
            lines.append(f"[{sev}] {msg[:300]}")
        text = "\n".join(lines[-int(limit):])
        # Highlight likely error lines
        errors = [ln for ln in lines if "error" in ln.lower() or "[erro" in ln.lower() or "fail" in ln.lower()]
        return {
            "ok": True, "deployment_id": deployment_id,
            "line_count": len(lines),
            "text_tail": text[-12000:],
            "likely_errors": errors[-10:],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


async def tool_railway_runtime_logs(limit: int = 200) -> Dict[str, Any]:
    """🩺 Get runtime/HTTP logs of the currently running deployment.
    Useful to diagnose 500 errors, slow requests, traceback in production.
    """
    c = await _creds()
    if not c["token"]:
        return {"ok": False, "error": "RAILWAY_TOKEN missing"}
    # Pick latest SUCCESS deployment
    q_list = (
        'query Deps($p: String, $s: String!, $e: String!) { '
        'deployments(first: 5, input: { projectId: $p, serviceId: $s, environmentId: $e }) { '
        '  edges { node { id status } } } }'
    )
    try:
        data = await _railway_query(c["token"], q_list, {
            "p": c["project"] or None, "s": c["service"], "e": c["env"],
        })
        edges = (data.get("data", {}).get("deployments") or {}).get("edges", [])
        deployment_id = None
        for e in edges:
            if e["node"]["status"] == "SUCCESS":
                deployment_id = e["node"]["id"]
                break
        if not deployment_id and edges:
            deployment_id = edges[0]["node"]["id"]
        if not deployment_id:
            return {"ok": False, "error": "no deployment found"}
    except Exception as e:
        return {"ok": False, "error": f"list failed: {e}"}

    q = (
        'query DepLogs($id: String!, $limit: Int) { '
        'deploymentLogs(deploymentId: $id, limit: $limit) { message timestamp severity } }'
    )
    try:
        data = await _railway_query(c["token"], q, {"id": deployment_id, "limit": int(limit)})
        if "errors" in data:
            return {"ok": False, "error": str(data["errors"])[:300]}
        logs = (data.get("data") or {}).get("deploymentLogs") or []
        lines = []
        for lo in logs:
            msg = (lo.get("message") or "").rstrip()
            if not msg.strip():
                continue
            lines.append(msg[:300])
        text = "\n".join(lines[-int(limit):])
        errors = [ln for ln in lines if any(k in ln.lower() for k in ("error", "traceback", "exception", " 500 "))]
        return {
            "ok": True, "deployment_id": deployment_id,
            "line_count": len(lines),
            "text_tail": text[-12000:],
            "likely_errors": errors[-10:],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


async def tool_railway_env_vars(action: str = "list", key: Optional[str] = None, value: Optional[str] = None) -> Dict[str, Any]:
    """🔑 Manage Railway environment variables.
    action='list' → returns all current vars (values redacted).
    action='set'  → sets/updates a var (provide key + value).
    action='unset' → deletes a var (provide key).
    """
    c = await _creds()
    if not c["token"] or not c["service"] or not c["env"] or not c["project"]:
        return {"ok": False, "error": "Railway project/service/env/token must all be set"}

    if action == "list":
        q = (
            'query Vars($p: String!, $s: String!, $e: String!) { '
            'variables(projectId: $p, environmentId: $e, serviceId: $s) }'
        )
        try:
            data = await _railway_query(c["token"], q, {
                "p": c["project"], "s": c["service"], "e": c["env"],
            })
            if "errors" in data:
                return {"ok": False, "error": str(data["errors"])[:300]}
            vars_obj = (data.get("data") or {}).get("variables") or {}
            keys = sorted(vars_obj.keys())
            # Redact values
            return {"ok": True, "keys": keys, "count": len(keys),
                    "sample_redacted": {k: (vars_obj[k][:4] + "***" + vars_obj[k][-2:] if vars_obj.get(k) else "") for k in keys[:8]}}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    if action == "set":
        if not key or value is None:
            return {"ok": False, "error": "key + value required for set"}
        q = (
            'mutation Upsert($input: VariableUpsertInput!) { variableUpsert(input: $input) }'
        )
        try:
            data = await _railway_query(c["token"], q, {"input": {
                "projectId": c["project"], "environmentId": c["env"],
                "serviceId": c["service"], "name": key, "value": value,
            }})
            if "errors" in data:
                return {"ok": False, "error": str(data["errors"])[:300]}
            return {"ok": True, "set": key, "verdict": "✅ تم — بيتم redeploy تلقائياً"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    if action == "unset":
        if not key:
            return {"ok": False, "error": "key required for unset"}
        q = (
            'mutation Del($input: VariableDeleteInput!) { variableDelete(input: $input) }'
        )
        try:
            data = await _railway_query(c["token"], q, {"input": {
                "projectId": c["project"], "environmentId": c["env"],
                "serviceId": c["service"], "name": key,
            }})
            if "errors" in data:
                return {"ok": False, "error": str(data["errors"])[:300]}
            return {"ok": True, "unset": key}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    return {"ok": False, "error": "action must be list|set|unset"}


# ════════════════════════════════════════════════════════════════════════
# Anthropic schemas
# ════════════════════════════════════════════════════════════════════════
RAILWAY_ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "railway_redeploy",
        "description": "🚂 يطلق redeploy جديد على Railway. استخدمها بعد git push لو ما اشتغل الـauto-deploy، أو بعد ما تصلح build error.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "railway_build_logs",
        "description": "📜 يجيب logs الـbuild لأي deployment (افتراضياً آخر واحد). مهم لتشخيص سبب فشل البناء.",
        "input_schema": {"type": "object", "properties": {
            "deployment_id": {"type": "string"}, "limit": {"type": "integer"},
        }, "required": []},
    },
    {
        "name": "railway_runtime_logs",
        "description": "🩺 يجيب runtime logs من الـdeployment الشغّال (HTTP / errors / tracebacks).",
        "input_schema": {"type": "object", "properties": {"limit": {"type": "integer"}}, "required": []},
    },
    {
        "name": "railway_env_vars",
        "description": "🔑 إدارة متغيرات البيئة على Railway. action: list|set|unset. set يحتاج key+value.",
        "input_schema": {"type": "object", "properties": {
            "action": {"type": "string", "enum": ["list", "set", "unset"]},
            "key": {"type": "string"}, "value": {"type": "string"},
        }, "required": ["action"]},
    },
]


RAILWAY_TOOL_HANDLERS = {
    "railway_redeploy": tool_railway_redeploy,
    "railway_build_logs": tool_railway_build_logs,
    "railway_runtime_logs": tool_railway_runtime_logs,
    "railway_env_vars": tool_railway_env_vars,
}


RAILWAY_TOOL_DEFS: List[Dict[str, Any]] = [
    {"name": "railway_redeploy", "desc": "trigger fresh Railway deploy", "args": []},
    {"name": "railway_build_logs", "desc": "build logs (debug failures)", "args": ["deployment_id?", "limit?"]},
    {"name": "railway_runtime_logs", "desc": "production runtime logs", "args": ["limit?"]},
    {"name": "railway_env_vars", "desc": "list/set/unset env vars", "args": ["action", "key?", "value?"]},
]


def railway_summarize(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in RAILWAY_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return f"🚂✗ {(result.get('error') or '')[:120]}"
    if name == "railway_redeploy":
        return "🚂 redeploy triggered"
    if name == "railway_build_logs":
        errs = len(result.get("likely_errors") or [])
        return f"📜 {result.get('line_count', 0)} سطر · {errs} خطأ محتمل"
    if name == "railway_runtime_logs":
        errs = len(result.get("likely_errors") or [])
        return f"🩺 {result.get('line_count', 0)} سطر · {errs} خطأ"
    if name == "railway_env_vars":
        if result.get("keys"):
            return f"🔑 {result.get('count', 0)} متغير على Railway"
        if result.get("set"):
            return f"🔑 set {result['set']}"
        if result.get("unset"):
            return f"🔑 unset {result['unset']}"
    return None


def railway_preview(name: str, result: Dict[str, Any]) -> Optional[str]:
    if name not in RAILWAY_TOOL_HANDLERS:
        return None
    if not result.get("ok"):
        return None
    if name in ("railway_build_logs", "railway_runtime_logs"):
        out = []
        if result.get("likely_errors"):
            out.append("⚠️ أخطاء محتملة:")
            out.extend(f"  {x[:180]}" for x in result["likely_errors"][-5:])
        out.append("📄 آخر السطور:")
        out.append((result.get("text_tail") or "")[-800:])
        return "\n".join(out)[:1500]
    if name == "railway_env_vars" and result.get("keys"):
        return "🔑 المفاتيح:\n  " + "\n  ".join(result["keys"][:30])
    return None
