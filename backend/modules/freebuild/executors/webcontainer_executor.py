"""
🌐 WebContainer Executor — runs Node.js code in the customer's browser via WASM.

WebContainer (by StackBlitz) is a browser-based Node.js runtime. This module
is the BACKEND side of the bridge — it:
  1. Generates execution tasks with unique IDs
  2. Stores them in a task queue (`webcontainer_tasks` collection)
  3. The frontend polls/subscribes via WebSocket
  4. Frontend executes in WebContainer, posts results back
  5. Backend reads results and resumes the orchestrator flow

Pattern: backend never runs the code — frontend does. Backend just orchestrates.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("zenrex.webcontainer")


async def enqueue_execution(
    db,
    user_id: str,
    project_id: str,
    code: str,
    files: Optional[Dict[str, str]] = None,
    entry_command: str = "node index.js",
    timeout_sec: int = 30,
) -> Dict[str, Any]:
    """Enqueue an execution task for the WebContainer to pick up.

    Returns:
        {
          "task_id": str,
          "status": "queued",
          "subscribe_url": "/api/webcontainer/tasks/{task_id}",
        }
    """
    task_id = str(uuid.uuid4())
    task = {
        "task_id": task_id,
        "user_id": user_id,
        "project_id": project_id,
        "kind": "webcontainer",
        "code": code,
        "files": files or {"index.js": code},
        "entry_command": entry_command,
        "timeout_sec": timeout_sec,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
    }
    if db is not None:
        try:
            await db.execution_tasks.insert_one(task)
        except Exception as e:
            logger.warning(f"[webcontainer] enqueue failed: {e}")
    return {
        "task_id": task_id,
        "status": "queued",
        "subscribe_url": f"/api/execution/tasks/{task_id}",
    }


async def get_task_result(db, task_id: str) -> Optional[Dict[str, Any]]:
    """Poll a task. Returns the result dict if complete, None if still running."""
    if db is None:
        return None
    try:
        doc = await db.execution_tasks.find_one({"task_id": task_id}, {"_id": 0})
        return doc
    except Exception as e:
        logger.warning(f"[webcontainer] get_task failed: {e}")
        return None


async def wait_for_result(db, task_id: str, max_wait_sec: int = 60, poll_interval: float = 1.0) -> Optional[Dict[str, Any]]:
    """Block until a task completes (or timeout)."""
    waited = 0.0
    while waited < max_wait_sec:
        doc = await get_task_result(db, task_id)
        if doc and doc.get("status") in ("done", "failed", "timeout"):
            return doc
        await asyncio.sleep(poll_interval)
        waited += poll_interval
    return {"status": "wait_timeout", "task_id": task_id}


def render_webcontainer_html_wrapper(task_id: str, files: Dict[str, str], entry: str) -> str:
    """Generate an HTML page that the frontend can iframe to execute the task.

    The page loads @webcontainer/api, mounts the files, runs the entry, and
    POSTs results back to /api/execution/tasks/{task_id}/result.
    """
    files_json = json.dumps(files, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>WebContainer Runner</title>
<style>body{{font-family:monospace;background:#0a0a0a;color:#0f0;padding:20px;}}</style>
</head>
<body>
<h3>Executing task: <code>{task_id}</code></h3>
<pre id="log"></pre>
<script type="module">
import {{ WebContainer }} from 'https://esm.sh/@webcontainer/api@1.5.1';

const TASK_ID = {json.dumps(task_id)};
const ENTRY = {json.dumps(entry)};
const FILES = {files_json};

const log = document.getElementById('log');
function w(t) {{ log.textContent += t + '\\n'; window.scrollTo(0, document.body.scrollHeight); }}

async function postResult(payload) {{
  await fetch(`/api/execution/tasks/${{TASK_ID}}/result`, {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify(payload),
  }});
}}

(async () => {{
  try {{
    w('🚀 Booting WebContainer...');
    const wc = await WebContainer.boot();
    w('📦 Mounting files...');
    const tree = {{}};
    for (const [path, content] of Object.entries(FILES)) {{
      const parts = path.split('/');
      let cur = tree;
      parts.slice(0, -1).forEach(p => {{ cur[p] = cur[p] || {{directory: {{}}}}; cur = cur[p].directory; }});
      cur[parts[parts.length-1]] = {{file: {{contents: content}}}};
    }}
    await wc.mount(tree);
    w('▶️ Running: ' + ENTRY);
    const [cmd, ...args] = ENTRY.split(' ');
    const proc = await wc.spawn(cmd, args);
    let out = '';
    proc.output.pipeTo(new WritableStream({{ write(chunk) {{ out += chunk; w(chunk); }} }}));
    const exit = await proc.exit;
    w(`\\n✅ Exited with code ${{exit}}`);
    await postResult({{ status: exit === 0 ? 'done' : 'failed', exit_code: exit, stdout: out }});
  }} catch (e) {{
    w('❌ ' + e.message);
    await postResult({{ status: 'failed', error: e.message }});
  }}
}})();
</script>
</body>
</html>"""


async def post_task_result(db, task_id: str, payload: Dict[str, Any]) -> bool:
    """Called by the frontend after WebContainer execution completes."""
    if db is None:
        return False
    try:
        await db.execution_tasks.update_one(
            {"task_id": task_id},
            {"$set": {
                "status": payload.get("status", "done"),
                "result": payload,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        return True
    except Exception as e:
        logger.warning(f"[webcontainer] post_result failed: {e}")
        return False
