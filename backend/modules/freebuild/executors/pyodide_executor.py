"""
🐍 Pyodide Executor — runs Python code in the customer's browser via WASM.

Same pattern as WebContainer: backend enqueues, frontend runs Pyodide.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zenrex.pyodide")


async def enqueue_python(
    db,
    user_id: str,
    project_id: str,
    code: str,
    packages: Optional[List[str]] = None,
) -> Dict[str, Any]:
    task_id = str(uuid.uuid4())
    task = {
        "task_id": task_id,
        "user_id": user_id,
        "project_id": project_id,
        "kind": "pyodide",
        "code": code,
        "packages": packages or [],
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if db is not None:
        try:
            await db.execution_tasks.insert_one(task)
        except Exception as e:
            logger.warning(f"[pyodide] enqueue failed: {e}")
    return {"task_id": task_id, "status": "queued", "subscribe_url": f"/api/execution/tasks/{task_id}"}


def render_pyodide_html_wrapper(task_id: str, code: str, packages: List[str]) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Pyodide Runner</title>
<style>body{{font-family:monospace;background:#0a0a0a;color:#0f0;padding:20px;}}</style>
</head><body>
<h3>🐍 Pyodide task: <code>{task_id}</code></h3>
<pre id="log"></pre>
<script src="https://cdn.jsdelivr.net/pyodide/v0.25.1/full/pyodide.js"></script>
<script>
const TASK_ID = {json.dumps(task_id)};
const CODE = {json.dumps(code)};
const PKGS = {json.dumps(packages)};
const log = document.getElementById('log');
function w(t){{log.textContent += t + '\\n';}}

async function postResult(p) {{
  await fetch(`/api/execution/tasks/${{TASK_ID}}/result`, {{
    method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(p)
  }});
}}

(async () => {{
  try {{
    w('🐍 Loading Pyodide...');
    const py = await loadPyodide({{stdout: w, stderr: w}});
    if (PKGS.length) {{
      w('📦 Loading packages: ' + PKGS.join(', '));
      await py.loadPackagesFromImports(CODE);
      await py.loadPackage(PKGS);
    }}
    w('▶️ Running...');
    const result = await py.runPythonAsync(CODE);
    w(`\\n✅ Result: ${{result}}`);
    await postResult({{status:'done', stdout: log.textContent, result: String(result)}});
  }} catch (e) {{
    w('❌ ' + e.message);
    await postResult({{status:'failed', error: e.message, stdout: log.textContent}});
  }}
}})();
</script></body></html>"""
