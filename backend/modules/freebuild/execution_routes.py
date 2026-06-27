"""
🛰️ Execution Task Routes — bridge between cloud orchestrator and remote runners.

  POST /api/execution/enqueue/webcontainer    → backend queues a JS task
  POST /api/execution/enqueue/pyodide         → backend queues a Python task
  GET  /api/execution/tasks/{task_id}         → frontend polls / opens iframe
  POST /api/execution/tasks/{task_id}/result  → runner posts result back
  GET  /api/execution/runner/{task_id}.html   → returns the iframe HTML to execute
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .executors.pyodide_executor import enqueue_python, render_pyodide_html_wrapper
from .executors.webcontainer_executor import (
    enqueue_execution, get_task_result, post_task_result, render_webcontainer_html_wrapper,
)

logger = logging.getLogger("zenrex.execution.routes")

router = APIRouter(prefix="/api/execution", tags=["execution"])


async def _get_db(request: Request):
    db = getattr(request.app.state, "db", None)
    if db is None:
        db = getattr(request.app.state, "mongo", None)
    if db is None:
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            client = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db = client[os.environ["DB_NAME"]]
            request.app.state.db = db
        except Exception as e:
            raise HTTPException(500, f"db not available: {e}")
    return db


async def _get_user_id(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user and getattr(user, "id", None):
        return str(user.id)
    if isinstance(user, dict) and user.get("id"):
        return str(user["id"])
    client = request.client.host if request.client else "anon"
    return f"anon_{client}"


class EnqueueJsBody(BaseModel):
    code: str
    files: Optional[Dict[str, str]] = None
    entry_command: str = "node index.js"
    timeout_sec: int = 30
    project_id: str = "default"


class EnqueuePyBody(BaseModel):
    code: str
    packages: Optional[List[str]] = None
    project_id: str = "default"


@router.post("/enqueue/webcontainer")
async def enqueue_wc(body: EnqueueJsBody, request: Request):
    db = await _get_db(request)
    uid = await _get_user_id(request)
    return await enqueue_execution(db, uid, body.project_id, body.code, body.files,
                                    body.entry_command, body.timeout_sec)


@router.post("/enqueue/pyodide")
async def enqueue_py(body: EnqueuePyBody, request: Request):
    db = await _get_db(request)
    uid = await _get_user_id(request)
    return await enqueue_python(db, uid, body.project_id, body.code, body.packages)


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, request: Request):
    db = await _get_db(request)
    task = await get_task_result(db, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    return task


@router.post("/tasks/{task_id}/result")
async def post_result(task_id: str, payload: Dict[str, Any], request: Request):
    db = await _get_db(request)
    ok = await post_task_result(db, task_id, payload)
    return {"received": ok}


@router.get("/runner/{task_id}.html", response_class=HTMLResponse)
async def runner_html(task_id: str, request: Request):
    """Return the executable HTML page for a queued task."""
    db = await _get_db(request)
    task = await get_task_result(db, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    if task.get("kind") == "webcontainer":
        return HTMLResponse(render_webcontainer_html_wrapper(
            task_id, task.get("files") or {}, task.get("entry_command", "node index.js"),
        ))
    elif task.get("kind") == "pyodide":
        return HTMLResponse(render_pyodide_html_wrapper(
            task_id, task.get("code", ""), task.get("packages") or [],
        ))
    raise HTTPException(400, f"unknown task kind: {task.get('kind')}")


def include_execution_routes(app):
    app.include_router(router)
