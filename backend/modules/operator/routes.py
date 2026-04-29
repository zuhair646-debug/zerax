"""
Operator routes — owner + agency-developers only.

Endpoints:
  GET    /api/operator/access            — check if current user sees the panel
  GET    /api/operator/developers        — owner list of emails with panel access
  POST   /api/operator/developers        — add email to allowlist
  DELETE /api/operator/developers/{email}

  GET    /api/operator/clients           — list all client projects
  POST   /api/operator/clients           — create one
  GET    /api/operator/clients/{id}      — fetch details (secrets masked)
  PATCH  /api/operator/clients/{id}      — update fields / credentials
  DELETE /api/operator/clients/{id}

  POST   /api/operator/clients/{id}/actions/github/test
  POST   /api/operator/clients/{id}/actions/github/put-file
  POST   /api/operator/clients/{id}/actions/railway/test
  POST   /api/operator/clients/{id}/actions/railway/redeploy
  POST   /api/operator/clients/{id}/actions/railway/latest
  POST   /api/operator/clients/{id}/actions/railway/set-env
  POST   /api/operator/clients/{id}/actions/vercel/test
  POST   /api/operator/clients/{id}/actions/vercel/redeploy
"""
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import os
import uuid
import json as _json
import logging as _logging

from . import vault
from . import actions as ops


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mask_client_for_ui(c: Dict[str, Any]) -> Dict[str, Any]:
    """Strip encrypted tokens from response; only return a masked tail for visual confirmation."""
    out = {k: v for k, v in c.items() if not k.endswith("_enc")}

    def _tail(enc: str) -> str:
        plain = vault.decrypt(enc or "")
        return vault.mask(plain, 4) if plain else ""

    gh = c.get("github") or {}
    rw = c.get("railway") or {}
    vc = c.get("vercel") or {}
    mg = c.get("mongo") or {}
    out["github"] = {
        "repo": gh.get("repo", ""),
        "branch": gh.get("branch", "main"),
        "token_mask": _tail(gh.get("token_enc", "")),
        "has_token": bool(gh.get("token_enc")),
    }
    out["railway"] = {
        "project_id": rw.get("project_id", ""),
        "environment_id": rw.get("environment_id", ""),
        "service_id": rw.get("service_id", ""),
        "token_mask": _tail(rw.get("token_enc", "")),
        "has_token": bool(rw.get("token_enc")),
    }
    out["vercel"] = {
        "project_id": vc.get("project_id", ""),
        "token_mask": _tail(vc.get("token_enc", "")),
        "has_token": bool(vc.get("token_enc")),
    }
    out["mongo"] = {
        "db_name": mg.get("db_name", ""),
        "url_mask": _tail(mg.get("url_enc", "")),
        "has_url": bool(mg.get("url_enc")),
    }
    return out


def init_routes(database, auth_dep) -> APIRouter:
    r = APIRouter(prefix="/operator", tags=["operator"])

    # ── Access control: owner OR email in operator_developers allowlist ──
    async def _require_operator(current_user: dict = Depends(auth_dep)) -> dict:
        if (current_user or {}).get("role") == "owner":
            return current_user
        # Fallback: check allowlist
        email = (current_user or {}).get("email") or ""
        doc = await database.operator_settings.find_one({"_id": "global"}, {"_id": 0, "developers": 1})
        allow = {e.lower() for e in ((doc or {}).get("developers") or [])}
        if email and email.lower() in allow:
            return current_user
        raise HTTPException(403, "Operator panel access required")

    async def _require_owner(current_user: dict = Depends(auth_dep)) -> dict:
        if (current_user or {}).get("role") != "owner":
            raise HTTPException(403, "Owner access only")
        return current_user

    # ────────────────────────────────────────────────────────
    # Access & developers allowlist
    # ────────────────────────────────────────────────────────
    @r.get("/access")
    async def _access(current_user: dict = Depends(auth_dep)):
        try:
            await _require_operator(current_user)
            return {"has_access": True, "role": current_user.get("role"), "email": current_user.get("email")}
        except HTTPException:
            return {"has_access": False}

    @r.get("/developers")
    async def _devs_list(_u: dict = Depends(_require_owner)):
        doc = await database.operator_settings.find_one({"_id": "global"}, {"_id": 0, "developers": 1})
        return {"developers": (doc or {}).get("developers") or []}

    class DevIn(BaseModel):
        email: str

    @r.post("/developers")
    async def _devs_add(body: DevIn, _u: dict = Depends(_require_owner)):
        email = (body.email or "").strip().lower()
        if not email or "@" not in email:
            raise HTTPException(400, "Invalid email")
        await database.operator_settings.update_one(
            {"_id": "global"},
            {"$addToSet": {"developers": email}, "$set": {"updated_at": _iso_now()}},
            upsert=True,
        )
        return {"ok": True, "email": email}

    @r.delete("/developers/{email}")
    async def _devs_remove(email: str, _u: dict = Depends(_require_owner)):
        await database.operator_settings.update_one(
            {"_id": "global"},
            {"$pull": {"developers": email.lower()}, "$set": {"updated_at": _iso_now()}},
        )
        return {"ok": True}

    # ────────────────────────────────────────────────────────
    # Client projects CRUD
    # ────────────────────────────────────────────────────────
    class GithubIn(BaseModel):
        repo: Optional[str] = ""          # e.g. "user/repo"
        branch: Optional[str] = "main"
        token: Optional[str] = None        # plaintext on input; will be encrypted
        clear_token: Optional[bool] = False

    class RailwayIn(BaseModel):
        project_id: Optional[str] = ""
        environment_id: Optional[str] = ""
        service_id: Optional[str] = ""
        token: Optional[str] = None
        clear_token: Optional[bool] = False

    class VercelIn(BaseModel):
        project_id: Optional[str] = ""
        token: Optional[str] = None
        clear_token: Optional[bool] = False

    class MongoIn(BaseModel):
        db_name: Optional[str] = ""
        url: Optional[str] = None
        clear_url: Optional[bool] = False

    class ClientCreate(BaseModel):
        name: str
        client_email: Optional[str] = ""
        notes: Optional[str] = ""
        github: Optional[GithubIn] = None
        railway: Optional[RailwayIn] = None
        vercel: Optional[VercelIn] = None
        mongo: Optional[MongoIn] = None

    class ClientUpdate(BaseModel):
        name: Optional[str] = None
        client_email: Optional[str] = None
        notes: Optional[str] = None
        auto_fix_enabled: Optional[bool] = None  # 🆕 enables autonomous repair on failure
        github: Optional[GithubIn] = None
        railway: Optional[RailwayIn] = None
        vercel: Optional[VercelIn] = None
        mongo: Optional[MongoIn] = None

    def _apply_github(existing: Dict[str, Any], inp: Optional[GithubIn]) -> Dict[str, Any]:
        out = dict(existing or {})
        if inp is None:
            return out
        if inp.repo is not None and inp.repo != "":
            out["repo"] = inp.repo.strip()
        if inp.branch is not None and inp.branch != "":
            out["branch"] = inp.branch.strip() or "main"
        if inp.clear_token:
            out["token_enc"] = ""
        elif inp.token is not None and inp.token != "":
            out["token_enc"] = vault.encrypt(inp.token.strip())
        return out

    def _apply_railway(existing: Dict[str, Any], inp: Optional[RailwayIn]) -> Dict[str, Any]:
        out = dict(existing or {})
        if inp is None:
            return out
        for k in ("project_id", "environment_id", "service_id"):
            v = getattr(inp, k, None)
            if v is not None and v != "":
                out[k] = v.strip()
        if inp.clear_token:
            out["token_enc"] = ""
        elif inp.token is not None and inp.token != "":
            out["token_enc"] = vault.encrypt(inp.token.strip())
        return out

    def _apply_vercel(existing: Dict[str, Any], inp: Optional[VercelIn]) -> Dict[str, Any]:
        out = dict(existing or {})
        if inp is None:
            return out
        if inp.project_id is not None and inp.project_id != "":
            out["project_id"] = inp.project_id.strip()
        if inp.clear_token:
            out["token_enc"] = ""
        elif inp.token is not None and inp.token != "":
            out["token_enc"] = vault.encrypt(inp.token.strip())
        return out

    def _apply_mongo(existing: Dict[str, Any], inp: Optional[MongoIn]) -> Dict[str, Any]:
        out = dict(existing or {})
        if inp is None:
            return out
        if inp.db_name is not None and inp.db_name != "":
            out["db_name"] = inp.db_name.strip()
        if inp.clear_url:
            out["url_enc"] = ""
        elif inp.url is not None and inp.url != "":
            out["url_enc"] = vault.encrypt(inp.url.strip())
        return out

    @r.get("/clients")
    async def _clients_list(_u: dict = Depends(_require_operator)):
        docs = await database.operator_clients.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"clients": [_mask_client_for_ui(d) for d in docs]}

    @r.post("/clients")
    async def _clients_create(body: ClientCreate, user: dict = Depends(_require_operator)):
        doc: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "name": body.name.strip(),
            "client_email": (body.client_email or "").strip(),
            "notes": (body.notes or ""),
            "github": _apply_github({}, body.github),
            "railway": _apply_railway({}, body.railway),
            "vercel": _apply_vercel({}, body.vercel),
            "mongo": _apply_mongo({}, body.mongo),
            "created_by": user.get("email") or user.get("user_id"),
            "created_at": _iso_now(),
            "updated_at": _iso_now(),
        }
        await database.operator_clients.insert_one(doc)
        doc.pop("_id", None)
        return _mask_client_for_ui(doc)

    @r.get("/clients/{cid}")
    async def _client_get(cid: str, _u: dict = Depends(_require_operator)):
        doc = await database.operator_clients.find_one({"id": cid}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Client not found")
        return _mask_client_for_ui(doc)

    @r.patch("/clients/{cid}")
    async def _client_update(cid: str, body: ClientUpdate, _u: dict = Depends(_require_operator)):
        existing = await database.operator_clients.find_one({"id": cid}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Client not found")
        patch: Dict[str, Any] = {"updated_at": _iso_now()}
        if body.name is not None:
            patch["name"] = body.name.strip()
        if body.client_email is not None:
            patch["client_email"] = body.client_email.strip()
        if body.notes is not None:
            patch["notes"] = body.notes
        if body.auto_fix_enabled is not None:
            patch["auto_fix_enabled"] = bool(body.auto_fix_enabled)
        if body.github is not None:
            patch["github"] = _apply_github(existing.get("github") or {}, body.github)
        if body.railway is not None:
            patch["railway"] = _apply_railway(existing.get("railway") or {}, body.railway)
        if body.vercel is not None:
            patch["vercel"] = _apply_vercel(existing.get("vercel") or {}, body.vercel)
        if body.mongo is not None:
            patch["mongo"] = _apply_mongo(existing.get("mongo") or {}, body.mongo)
        await database.operator_clients.update_one({"id": cid}, {"$set": patch})
        fresh = await database.operator_clients.find_one({"id": cid}, {"_id": 0})
        return _mask_client_for_ui(fresh)

    @r.delete("/clients/{cid}")
    async def _client_delete(cid: str, _u: dict = Depends(_require_operator)):
        res = await database.operator_clients.delete_one({"id": cid})
        return {"deleted": res.deleted_count}

    # ────────────────────────────────────────────────────────
    # Action helpers (resolve & decrypt tokens per-request)
    # ────────────────────────────────────────────────────────
    async def _load_client(cid: str) -> Dict[str, Any]:
        doc = await database.operator_clients.find_one({"id": cid}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Client not found")
        return doc

    async def _log_action(cid: str, user: dict, action: str, ok: bool, detail: str = ""):
        await database.operator_actions.insert_one(
            {
                "client_id": cid,
                "action": action,
                "ok": ok,
                "detail": detail[:500],
                "by": user.get("email") or user.get("user_id"),
                "at": _iso_now(),
            }
        )

    # ── GitHub actions ──
    @r.post("/clients/{cid}/actions/github/test")
    async def _gh_test(cid: str, user: dict = Depends(_require_operator)):
        c = await _load_client(cid)
        gh = c.get("github") or {}
        token = vault.decrypt(gh.get("token_enc", ""))
        if not token or not gh.get("repo"):
            raise HTTPException(400, "GitHub token and repo required")
        try:
            info = await ops.github_test(token, gh["repo"])
            await _log_action(cid, user, "github.test", True, gh["repo"])
            return {"ok": True, "repo": info}
        except Exception as e:
            await _log_action(cid, user, "github.test", False, str(e))
            raise HTTPException(400, str(e))

    class GhPutIn(BaseModel):
        path: str
        content: str
        message: Optional[str] = ""

    @r.post("/clients/{cid}/actions/github/put-file")
    async def _gh_put(cid: str, body: GhPutIn, user: dict = Depends(_require_operator)):
        c = await _load_client(cid)
        gh = c.get("github") or {}
        token = vault.decrypt(gh.get("token_enc", ""))
        if not token or not gh.get("repo"):
            raise HTTPException(400, "GitHub token and repo required")
        try:
            res = await ops.github_put_file(
                token, gh["repo"], body.path, body.content, body.message or "", gh.get("branch", "main")
            )
            await _log_action(cid, user, "github.put_file", True, body.path)
            return res
        except Exception as e:
            await _log_action(cid, user, "github.put_file", False, f"{body.path}: {e}")
            raise HTTPException(400, str(e))

    # ── Railway actions ──
    @r.post("/clients/{cid}/actions/railway/test")
    async def _rw_test(cid: str, user: dict = Depends(_require_operator)):
        c = await _load_client(cid)
        rw = c.get("railway") or {}
        token = vault.decrypt(rw.get("token_enc", ""))
        if not token:
            raise HTTPException(400, "Railway token required")
        try:
            info = await ops.railway_test(token)
            await _log_action(cid, user, "railway.test", True)
            return {"ok": True, "account": info}
        except Exception as e:
            await _log_action(cid, user, "railway.test", False, str(e))
            raise HTTPException(400, str(e))

    @r.post("/clients/{cid}/actions/railway/redeploy")
    async def _rw_redeploy(cid: str, user: dict = Depends(_require_operator)):
        c = await _load_client(cid)
        rw = c.get("railway") or {}
        token = vault.decrypt(rw.get("token_enc", ""))
        if not (token and rw.get("service_id") and rw.get("environment_id")):
            raise HTTPException(400, "Railway token, service_id and environment_id required")
        try:
            res = await ops.railway_redeploy(token, rw["service_id"], rw["environment_id"])
            await _log_action(cid, user, "railway.redeploy", True)
            return res
        except Exception as e:
            await _log_action(cid, user, "railway.redeploy", False, str(e))
            raise HTTPException(400, str(e))

    @r.post("/clients/{cid}/actions/railway/latest")
    async def _rw_latest(cid: str, user: dict = Depends(_require_operator)):
        c = await _load_client(cid)
        rw = c.get("railway") or {}
        token = vault.decrypt(rw.get("token_enc", ""))
        if not (token and rw.get("service_id") and rw.get("environment_id")):
            raise HTTPException(400, "Railway token, service_id and environment_id required")
        try:
            dep = await ops.railway_latest_deploy(token, rw["service_id"], rw["environment_id"])
            await _log_action(cid, user, "railway.latest", True, dep.get("status", ""))
            return dep
        except Exception as e:
            await _log_action(cid, user, "railway.latest", False, str(e))
            raise HTTPException(400, str(e))

    class RwEnvIn(BaseModel):
        name: str
        value: str

    @r.post("/clients/{cid}/actions/railway/set-env")
    async def _rw_setenv(cid: str, body: RwEnvIn, user: dict = Depends(_require_operator)):
        c = await _load_client(cid)
        rw = c.get("railway") or {}
        token = vault.decrypt(rw.get("token_enc", ""))
        if not (token and rw.get("project_id") and rw.get("environment_id") and rw.get("service_id")):
            raise HTTPException(400, "Railway token + project_id + environment_id + service_id required")
        try:
            res = await ops.railway_upsert_variable(
                token, rw["project_id"], rw["environment_id"], rw["service_id"], body.name, body.value
            )
            await _log_action(cid, user, "railway.set_env", True, body.name)
            return res
        except Exception as e:
            await _log_action(cid, user, "railway.set_env", False, f"{body.name}: {e}")
            raise HTTPException(400, str(e))

    # ── Vercel actions ──
    @r.post("/clients/{cid}/actions/vercel/test")
    async def _vc_test(cid: str, user: dict = Depends(_require_operator)):
        c = await _load_client(cid)
        vc = c.get("vercel") or {}
        token = vault.decrypt(vc.get("token_enc", ""))
        if not token:
            raise HTTPException(400, "Vercel token required")
        try:
            info = await ops.vercel_test(token)
            projs = await ops.vercel_list_projects(token)
            await _log_action(cid, user, "vercel.test", True)
            return {"ok": True, "account": info, "projects": projs}
        except Exception as e:
            await _log_action(cid, user, "vercel.test", False, str(e))
            raise HTTPException(400, str(e))

    @r.post("/clients/{cid}/actions/vercel/redeploy")
    async def _vc_redeploy(cid: str, user: dict = Depends(_require_operator)):
        c = await _load_client(cid)
        vc = c.get("vercel") or {}
        token = vault.decrypt(vc.get("token_enc", ""))
        if not token or not vc.get("project_id"):
            raise HTTPException(400, "Vercel token + project_id required")
        try:
            res = await ops.vercel_redeploy(token, vc["project_id"])
            await _log_action(cid, user, "vercel.redeploy", True)
            return res
        except Exception as e:
            await _log_action(cid, user, "vercel.redeploy", False, str(e))
            raise HTTPException(400, str(e))

    # ── Action history ──
    @r.get("/clients/{cid}/actions/log")
    async def _log_get(cid: str, limit: int = Query(50, ge=1, le=500), _u: dict = Depends(_require_operator)):
        docs = await database.operator_actions.find({"client_id": cid}, {"_id": 0}).sort("at", -1).limit(limit).to_list(limit)
        return {"entries": docs}

    # ──────────────────────────────────────────────────
    # AI DevOps Agent — autonomous per-client chat
    # ──────────────────────────────────────────────────
    class ChatSendIn(BaseModel):
        text: str
        session_id: Optional[str] = None  # reuse to continue a thread

    @r.get("/clients/{cid}/chat/sessions")
    async def _chat_sessions(cid: str, _u: dict = Depends(_require_operator)):
        """List chat sessions for a client (most recent first)."""
        pipeline = [
            {"$match": {"client_id": cid}},
            {"$sort": {"at": -1}},
            {"$group": {
                "_id": "$session_id",
                "last_at": {"$first": "$at"},
                "first_text": {"$last": "$text"},
                "messages": {"$sum": 1},
            }},
            {"$sort": {"last_at": -1}},
            {"$limit": 30},
        ]
        raw = await database.operator_chats.aggregate(pipeline).to_list(30)
        out = [{"session_id": r["_id"], "last_at": r["last_at"], "title": (r.get("first_text") or "")[:60], "messages": r["messages"]} for r in raw]
        return {"sessions": out}

    @r.get("/clients/{cid}/chat/{session_id}")
    async def _chat_history(cid: str, session_id: str, _u: dict = Depends(_require_operator)):
        """Fetch full message + step history for a session."""
        docs = await database.operator_chats.find(
            {"client_id": cid, "session_id": session_id}, {"_id": 0}
        ).sort("at", 1).to_list(500)
        return {"messages": docs, "session_id": session_id}

    @r.post("/clients/{cid}/chat")
    async def _chat_send(cid: str, body: ChatSendIn, user: dict = Depends(_require_operator)):
        """Send a user turn to the DevOps AI Agent. Returns the final answer + tool trace."""
        from .agent import AgentRunner
        client_doc = await database.operator_clients.find_one({"id": cid}, {"_id": 0})
        if not client_doc:
            raise HTTPException(404, "Client not found")
        session_id = (body.session_id or str(uuid.uuid4())).strip()
        text = (body.text or "").strip()
        if not text:
            raise HTTPException(400, "text required")

        now = _iso_now()
        # Persist user turn
        await database.operator_chats.insert_one({
            "id": str(uuid.uuid4()),
            "client_id": cid,
            "session_id": session_id,
            "role": "user",
            "text": text,
            "by": user.get("email") or user.get("user_id"),
            "at": now,
        })

        runner = AgentRunner(database, client_doc, session_id, user.get("email") or user.get("user_id") or "owner")
        result = await runner.run(text)

        # Persist assistant turn (with the tool-step trace for UI replay)
        await database.operator_chats.insert_one({
            "id": str(uuid.uuid4()),
            "client_id": cid,
            "session_id": session_id,
            "role": "assistant",
            "text": result.get("final") or "",
            "steps": result.get("steps") or [],
            "at": _iso_now(),
        })

        return {
            "session_id": session_id,
            "final": result.get("final") or "",
            "steps": result.get("steps") or [],
        }

    @r.delete("/clients/{cid}/chat/{session_id}")
    async def _chat_delete(cid: str, session_id: str, _u: dict = Depends(_require_operator)):
        res = await database.operator_chats.delete_many({"client_id": cid, "session_id": session_id})
        return {"deleted": res.deleted_count}

    # ──────────────────────────────────────────────────
    # 🆕 WebSocket — live agent streaming (real-time tool steps)
    # ──────────────────────────────────────────────────
    @r.websocket("/ws/agent/{cid}")
    async def _ws_agent(ws: WebSocket, cid: str, token: str = ""):
        """Real-time agent. Frontend opens this WS, sends {text, session_id?},
        and receives streamed events: thinking / tool_start / tool_done / final / error."""
        import jwt as _jwt
        # JWT validation (same as get_current_user)
        try:
            secret = os.environ.get("JWT_SECRET", "your-secret-key")
            payload = _jwt.decode(token, secret, algorithms=["HS256"])
            user_id = payload.get("user_id")
            role = payload.get("role")
            if not user_id:
                await ws.close(code=4401)
                return
        except Exception:
            await ws.close(code=4401)
            return

        # Resolve email + ensure operator allowlist (owner bypasses)
        email = ""
        if role != "owner":
            udoc = await database.users.find_one({"id": user_id}, {"_id": 0, "email": 1})
            email = ((udoc or {}).get("email") or "").lower()
            doc = await database.operator_settings.find_one({"_id": "global"}, {"_id": 0, "developers": 1})
            allow = {e.lower() for e in ((doc or {}).get("developers") or [])}
            if not email or email not in allow:
                await ws.close(code=4403)
                return
        else:
            udoc = await database.users.find_one({"id": user_id}, {"_id": 0, "email": 1})
            email = ((udoc or {}).get("email") or "owner")

        client_doc = await database.operator_clients.find_one({"id": cid}, {"_id": 0})
        if not client_doc:
            await ws.close(code=4404)
            return

        await ws.accept()
        try:
            await ws.send_json({"kind": "ready", "client_name": client_doc.get("name", "")})
            while True:
                raw = await ws.receive_json()
                text = (raw or {}).get("text", "").strip()
                session_id = (raw or {}).get("session_id") or str(uuid.uuid4())
                if not text:
                    await ws.send_json({"kind": "error", "error": "text required"})
                    continue

                now = _iso_now()
                # Persist user turn
                await database.operator_chats.insert_one({
                    "id": str(uuid.uuid4()),
                    "client_id": cid,
                    "session_id": session_id,
                    "role": "user",
                    "text": text,
                    "by": email or user_id,
                    "at": now,
                })
                await ws.send_json({"kind": "user_saved", "session_id": session_id})

                # Streamed agent run
                from .agent import AgentRunner
                runner = AgentRunner(database, client_doc, session_id, email or user_id or "owner")

                async def _on_step(ev):
                    try:
                        await ws.send_json({"session_id": session_id, **ev})
                    except Exception:
                        pass

                try:
                    result = await runner.run(text, on_step=_on_step)
                except Exception as e:
                    await ws.send_json({"kind": "error", "error": str(e)[:300]})
                    continue

                # Persist assistant turn
                await database.operator_chats.insert_one({
                    "id": str(uuid.uuid4()),
                    "client_id": cid,
                    "session_id": session_id,
                    "role": "assistant",
                    "text": result.get("final") or "",
                    "steps": result.get("steps") or [],
                    "at": _iso_now(),
                })
                await ws.send_json({"kind": "complete", "session_id": session_id, "final": result.get("final") or ""})
        except WebSocketDisconnect:
            pass
        except Exception as e:
            _logging.getLogger(__name__).warning(f"operator ws error: {e}")
            try:
                await ws.send_json({"kind": "error", "error": str(e)[:300]})
            except Exception:
                pass

    # ──────────────────────────────────────────────────
    # Memory (long-term per-client)
    # ──────────────────────────────────────────────────
    @r.get("/clients/{cid}/memory")
    async def _memory_get(cid: str, _u: dict = Depends(_require_operator)):
        doc = await database.operator_clients.find_one({"id": cid}, {"_id": 0, "memory": 1})
        return {"memory": (doc or {}).get("memory") or []}

    @r.delete("/clients/{cid}/memory")
    async def _memory_clear(cid: str, _u: dict = Depends(_require_operator)):
        await database.operator_clients.update_one({"id": cid}, {"$set": {"memory": []}})
        return {"ok": True}

    class MemAdd(BaseModel):
        fact: str

    @r.post("/clients/{cid}/memory")
    async def _memory_add(cid: str, body: MemAdd, _u: dict = Depends(_require_operator)):
        if not body.fact.strip():
            raise HTTPException(400, "fact required")
        await database.operator_clients.update_one(
            {"id": cid},
            {"$push": {"memory": {"$each": [{"fact": body.fact[:600], "at": _iso_now()}], "$slice": -40}}},
        )
        return {"ok": True}

    # ──────────────────────────────────────────────────
    # Health, Dashboard, Alerts
    # ──────────────────────────────────────────────────
    @r.get("/dashboard")
    async def _dashboard(_u: dict = Depends(_require_operator)):
        """Multi-client overview: name, last health, billing, memory size."""
        clients = await database.operator_clients.find({}, {"_id": 0}).sort("name", 1).to_list(500)
        out = []
        for c in clients:
            lh = c.get("last_health") or {}
            rw = lh.get("railway") or {}
            billing = c.get("billing") or {}
            ym = datetime.now(timezone.utc).strftime("%Y-%m")
            out.append({
                "id": c.get("id"),
                "name": c.get("name"),
                "client_email": c.get("client_email", ""),
                "checked_at": c.get("last_health_at"),
                "railway_state": rw.get("state", "n/a"),
                "railway_status": rw.get("status", ""),
                "railway_url": rw.get("url", ""),
                "memory_count": len((c.get("memory") or [])),
                "agent_calls_month": (billing.get(ym) or {}).get("agent_calls", 0),
                "agent_calls_total": (c.get("billing_total") or {}).get("agent_calls", 0),
                "has_github": bool((c.get("github") or {}).get("token_enc")),
                "has_railway": bool((c.get("railway") or {}).get("token_enc")),
                "has_vercel": bool((c.get("vercel") or {}).get("token_enc")),
            })
        # Aggregate counts
        summary = {
            "total": len(out),
            "healthy": sum(1 for c in out if c["railway_state"] == "healthy"),
            "failing": sum(1 for c in out if c["railway_state"] == "failing"),
            "pending": sum(1 for c in out if c["railway_state"] == "pending"),
            "unconfigured": sum(1 for c in out if c["railway_state"] in ("n/a", "unknown")),
        }
        return {"summary": summary, "clients": out}

    @r.post("/health-check/run")
    async def _health_run_now(_u: dict = Depends(_require_operator)):
        """Run an on-demand health-check pass over all clients."""
        from .health import run_all_health_checks
        return await run_all_health_checks(database)

    @r.get("/clients/{cid}/health/history")
    async def _health_history(cid: str, _u: dict = Depends(_require_operator)):
        doc = await database.operator_health_history.find_one({"client_id": cid}, {"_id": 0})
        snaps = (doc or {}).get("snapshots") or []
        return {"snapshots": snaps[-100:]}

    @r.get("/alerts")
    async def _alerts_list(unseen: bool = False, _u: dict = Depends(_require_operator)):
        q: Dict[str, Any] = {}
        if unseen:
            q["seen"] = False
        docs = await database.operator_alerts.find(q, {"_id": 0}).sort("at", -1).limit(100).to_list(100)
        return {"alerts": docs, "count": len(docs)}

    @r.post("/alerts/mark-seen")
    async def _alerts_mark(_u: dict = Depends(_require_operator)):
        res = await database.operator_alerts.update_many({"seen": False}, {"$set": {"seen": True}})
        return {"updated": res.modified_count}

    # ──────────────────────────────────────────────────
    # Global operator settings (alerts phone, etc.)
    # ──────────────────────────────────────────────────
    @r.get("/settings")
    async def _settings_get(_u: dict = Depends(_require_owner)):
        doc = await database.operator_settings.find_one({"_id": "global"}, {"_id": 0}) or {}
        return doc

    class SettingsIn(BaseModel):
        alert_phone: Optional[str] = None
        alert_email: Optional[str] = None

    @r.put("/settings")
    async def _settings_put(body: SettingsIn, _u: dict = Depends(_require_owner)):
        patch: Dict[str, Any] = {"updated_at": _iso_now()}
        if body.alert_phone is not None:
            patch["alert_phone"] = body.alert_phone.strip()
        if body.alert_email is not None:
            patch["alert_email"] = body.alert_email.strip()
        await database.operator_settings.update_one({"_id": "global"}, {"$set": patch}, upsert=True)
        return {"ok": True}

    return r
