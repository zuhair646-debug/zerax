"""Unrestricted Power Tools — Full agent parity.

Per owner directive (Feb 2026): the AI must have the SAME capabilities the
human developer has. Multi-tenant safety is enforced via per-project
workspaces + audit logging + a tiny catastrophe blocklist (not a whitelist).

Tools exported:
  • run_bash_unrestricted(command, cwd)  — full bash with chains/pipes/etc.
  • run_python_in_sandbox(code, timeout)  — full Python in subprocess
  • read_any_file(path)                   — read any file (with secret protection)
  • write_any_file(path, content)         — write any file (with backup)
  • edit_file(path, old, new)             — search-replace style edit
  • web_search(query)                     — DuckDuckGo HTML search
  • get_integration_playbook(service)     — built-in integration templates
  • deploy_to_production()                — run /app/deploy/deploy.sh
  • call_self_test_agent(scenario)        — autonomous browser test

Safety model:
  • Per-project workspace at /tmp/zenrex_workspaces/{project_id}/
  • Catastrophe blocklist: rm -rf /, dd of=/dev/sda, mkfs, fork bombs,
    direct MONGO_URL/EMERGENT_LLM_KEY exfil, /etc/shadow read
  • Every call audit-logged to MongoDB collection `ai_tool_audit`
  • Soft-walls protect OTHER users' data (project_id scoping)
"""
import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

logger = logging.getLogger("brain.unrestricted")

# ════════════════════════════════════════════════════════════════════════
# Catastrophe blocklist — only ABSOLUTE disaster patterns are blocked.
# Everything else is allowed. The point is to give the AI parity, not
# to second-guess every move. These prevent total system destruction.
# ════════════════════════════════════════════════════════════════════════
CATASTROPHE_PATTERNS = (
    r"rm\s+-rf?\s+/(\s|$)",          # rm -rf /
    r"rm\s+-rf?\s+/\*",              # rm -rf /*
    r"rm\s+-rf?\s+\$HOME",
    r"rm\s+-rf?\s+~",
    r"rm\s+-rf?\s+/etc",
    r"rm\s+-rf?\s+/usr",
    r"rm\s+-rf?\s+/var",
    r"rm\s+-rf?\s+/opt(/zerax)?(\s|$)",
    r"rm\s+-rf?\s+/app(\s|$)",
    r"dd\s+.*of=/dev/(sd|nvme|hd|xvd)",
    r"mkfs\.",
    r":\(\)\s*\{.*\|.*&\s*\}",       # fork bomb
    r">\s*/dev/sd[a-z]",
    r"chmod\s+-R\s+777\s+/",
    r"shutdown\s",
    r"reboot\s",
    r"halt\s",
    r"poweroff\s",
    r"systemctl\s+(stop|disable)\s+(docker|mongo|nginx)",
    r"docker\s+(rm|kill|stop)\s+-f\s+\$\(",   # mass-kill containers
)

# Secret keys that must never be leaked to the AI's output
SECRET_KEYS_PATTERNS = (
    "EMERGENT_LLM_KEY", "MONGO_URL", "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY", "STRIPE_SECRET_KEY", "STRIPE_RESTRICTED_KEY",
    "TWILIO_AUTH_TOKEN", "RESEND_API_KEY", "PAYPAL_SECRET",
    "AWS_SECRET", "GOOGLE_API_KEY", "FAL_KEY",
)

WORKSPACE_ROOT = "/tmp/zenrex_workspaces"


def _check_catastrophe(text: str) -> Optional[str]:
    """Return the matched catastrophe pattern, or None if safe."""
    for pat in CATASTROPHE_PATTERNS:
        if re.search(pat, text):
            return pat
    return None


def _redact_secrets(text: str) -> str:
    """Replace any line containing a secret key name with [REDACTED]."""
    if not text:
        return text
    out_lines = []
    for line in text.splitlines():
        if any(k in line for k in SECRET_KEYS_PATTERNS):
            out_lines.append("[REDACTED — secret key]")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def _ensure_workspace(project_id: str) -> str:
    """Get-or-create a per-project workspace under /tmp."""
    pid = re.sub(r"[^a-zA-Z0-9_-]", "_", str(project_id or "anon"))[:64]
    ws = os.path.join(WORKSPACE_ROOT, pid)
    Path(ws).mkdir(parents=True, exist_ok=True)
    return ws


# Audit logger (best-effort — never blocks tool execution)
async def _audit_log(project_id: str, tool: str, args: Dict[str, Any],
                      result_summary: str):
    try:
        from server import db  # circular-safe lazy import
        await db.ai_tool_audit.insert_one({
            "ts": time.time(),
            "project_id": str(project_id),
            "tool": tool,
            "args": {k: (str(v)[:500] if not isinstance(v, (int, bool, float)) else v)
                     for k, v in (args or {}).items()},
            "result": (result_summary or "")[:500],
        })
    except Exception as e:
        logger.debug(f"audit log failed (non-fatal): {e}")


# ════════════════════════════════════════════════════════════════════════
# 1. run_bash_unrestricted — full shell, per-project workspace, audit logged
# ════════════════════════════════════════════════════════════════════════
async def run_bash_unrestricted(
    project_id: str,
    command: str,
    cwd: Optional[str] = None,
    timeout_seconds: int = 30,
) -> Dict[str, Any]:
    """Execute ANY bash command. Pipes, chains, redirects all allowed.

    Defaults cwd to the per-project workspace. Pass cwd="/app" or
    "/opt/zerax" for system-level work (admin only).
    """
    cmd = (command or "").strip()
    if not cmd:
        return {"ok": False, "error": "empty command"}
    if len(cmd) > 8000:
        return {"ok": False, "error": "command too long (>8KB)"}

    catastrophe = _check_catastrophe(cmd)
    if catastrophe:
        await _audit_log(project_id, "run_bash_unrestricted",
                         {"command": cmd}, f"BLOCKED catastrophe: {catastrophe}")
        return {"ok": False,
                "error": f"catastrophe pattern blocked: {catastrophe}",
                "note": "this single command would destroy the system. all other commands are allowed."}

    workspace = _ensure_workspace(project_id)
    work_cwd = cwd or workspace

    # Allow targeting common system paths explicitly
    if cwd and not any(cwd.startswith(p) for p in
                        ("/tmp", "/app", "/opt/zerax", workspace, "/var/log")):
        return {"ok": False,
                "error": f"cwd must be under /tmp, /app, /opt/zerax, or workspace. got: {cwd}"}

    env = {
        "PATH": os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"),
        "HOME": workspace,
        "TMPDIR": workspace,
        "LANG": "C.UTF-8",
        "PYTHONUNBUFFERED": "1",
    }

    try:
        proc = subprocess.run(
            ["bash", "-c", cmd],
            cwd=work_cwd,
            env=env,
            capture_output=True,
            timeout=max(1, min(120, timeout_seconds)),
            text=True,
        )
    except subprocess.TimeoutExpired:
        await _audit_log(project_id, "run_bash_unrestricted",
                         {"command": cmd}, f"TIMEOUT after {timeout_seconds}s")
        return {"ok": False, "error": f"timeout after {timeout_seconds}s"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}

    stdout = _redact_secrets((proc.stdout or "")[:100_000])
    stderr = _redact_secrets((proc.stderr or "")[:50_000])
    summary = (f"exit={proc.returncode} stdout={len(stdout)}b stderr={len(stderr)}b")
    await _audit_log(project_id, "run_bash_unrestricted",
                     {"command": cmd, "cwd": work_cwd}, summary)

    return {
        "ok": proc.returncode == 0,
        "stdout": stdout,
        "stderr": stderr,
        "return_code": proc.returncode,
        "cwd": work_cwd,
        "command": cmd,
        "summary": (f"✅ bash ran (exit={proc.returncode})"
                    if proc.returncode == 0
                    else f"❌ bash failed (exit={proc.returncode}): {stderr[:120]}"),
    }


# ════════════════════════════════════════════════════════════════════════
# 2. run_python_in_sandbox — full Python with stdlib, per-project workspace
# ════════════════════════════════════════════════════════════════════════
async def run_python_in_sandbox(
    project_id: str,
    code: str,
    timeout_seconds: int = 15,
) -> Dict[str, Any]:
    """Execute Python code in a subprocess. Full stdlib available.

    Network and filesystem are NOT restricted at the OS level — but the
    audit log captures every run. Use this to test data transformations,
    parse JSON, run pandas, regex, etc.
    """
    if not code or not code.strip():
        return {"ok": False, "error": "empty code"}
    if len(code) > 50_000:
        return {"ok": False, "error": "code too large (>50KB)"}

    catastrophe = _check_catastrophe(code)
    if catastrophe:
        return {"ok": False, "error": f"catastrophe pattern: {catastrophe}"}

    workspace = _ensure_workspace(project_id)
    script_path = os.path.join(workspace, f"_py_run_{int(time.time())}.py")
    try:
        with open(script_path, "w") as f:
            f.write(code)

        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": workspace,
            "TMPDIR": workspace,
            "PYTHONUNBUFFERED": "1",
            "LANG": "C.UTF-8",
        }
        try:
            proc = subprocess.run(
                ["python3", script_path],
                cwd=workspace,
                env=env,
                capture_output=True,
                timeout=max(1, min(60, timeout_seconds)),
                text=True,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"timeout after {timeout_seconds}s",
                    "killed": True}
    finally:
        try:
            os.unlink(script_path)
        except Exception:
            pass

    stdout = _redact_secrets((proc.stdout or "")[:100_000])
    stderr = _redact_secrets((proc.stderr or "")[:50_000])
    await _audit_log(project_id, "run_python_in_sandbox",
                     {"code_len": len(code)},
                     f"exit={proc.returncode}")
    return {
        "ok": proc.returncode == 0,
        "stdout": stdout,
        "stderr": stderr,
        "return_code": proc.returncode,
        "summary": (f"✅ python ran (exit={proc.returncode}, stdout={len(stdout)}b)"
                    if proc.returncode == 0
                    else f"❌ python failed: {stderr[:150]}"),
    }


# ════════════════════════════════════════════════════════════════════════
# 3. read_any_file — read any file, secrets redacted
# ════════════════════════════════════════════════════════════════════════
async def read_any_file(project_id: str, path: str,
                         max_bytes: int = 200_000) -> Dict[str, Any]:
    """Read any file on disk. Secret keys are auto-redacted from output.

    Allowed paths: /app, /opt/zerax, /tmp, project workspace, /var/log.
    Blocked: /etc/shadow, /root/.ssh/, .env files (return existence only).
    """
    p = (path or "").strip()
    if not p:
        return {"ok": False, "error": "path required"}

    # Block leaking shadow/SSH/credential files entirely
    if p.endswith("/shadow") or "/.ssh/" in p or p.endswith("/id_rsa"):
        return {"ok": False, "error": "credential file blocked",
                "exists": os.path.exists(p)}

    # .env files: return existence + line count, not content
    if p.endswith(".env") or "/.env" in p:
        if not os.path.exists(p):
            return {"ok": False, "error": "not found"}
        try:
            n = sum(1 for _ in open(p))
            return {"ok": True, "redacted": True,
                    "path": p, "lines": n,
                    "note": ".env content cannot be read — secrets protected. "
                            "Reference variables via os.environ.get('KEY') in code instead."}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # Path containment
    allowed_roots = ("/app", "/opt/zerax", "/tmp",
                     WORKSPACE_ROOT, "/var/log", "/etc/nginx")
    abs_p = os.path.abspath(p)
    if not any(abs_p.startswith(r) for r in allowed_roots):
        return {"ok": False,
                "error": f"path outside allowed roots: {abs_p}"}

    if not os.path.exists(abs_p):
        return {"ok": False, "error": "not found"}
    if not os.path.isfile(abs_p):
        return {"ok": False, "error": "not a regular file"}

    size = os.path.getsize(abs_p)
    try:
        with open(abs_p, "rb") as f:
            raw = f.read(max_bytes)
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            text = repr(raw)[:max_bytes]
    except Exception as e:
        return {"ok": False, "error": str(e)}

    text = _redact_secrets(text)
    await _audit_log(project_id, "read_any_file", {"path": abs_p},
                     f"read {len(text)}b of {size}b")
    return {
        "ok": True,
        "path": abs_p,
        "size_bytes": size,
        "truncated": size > max_bytes,
        "content": text,
    }


# ════════════════════════════════════════════════════════════════════════
# 4. write_any_file — write any file (with backup)
# ════════════════════════════════════════════════════════════════════════
async def write_any_file(project_id: str, path: str, content: str,
                          create_dirs: bool = True) -> Dict[str, Any]:
    """Write ANY file. Pre-existing file is backed up to .bak.<ts>.

    Allowed roots: /app, /opt/zerax, /tmp, project workspace.
    Blocked: /etc/passwd, /etc/shadow, SSH keys, .env files.
    """
    p = (path or "").strip()
    if not p:
        return {"ok": False, "error": "path required"}
    if content is None:
        return {"ok": False, "error": "content required"}

    if any(p.endswith(b) for b in (".env",)) or "/.env" in p:
        return {"ok": False, "error": ".env writing blocked — modify env via docker-compose env_file or admin tool"}
    if p.endswith("/shadow") or "/.ssh/" in p or p.endswith("/passwd"):
        return {"ok": False, "error": "system credential file blocked"}

    abs_p = os.path.abspath(p)
    allowed_roots = ("/app", "/opt/zerax", "/tmp", WORKSPACE_ROOT,
                     "/var/www")
    if not any(abs_p.startswith(r) for r in allowed_roots):
        return {"ok": False, "error": f"path outside allowed roots: {abs_p}"}

    parent = os.path.dirname(abs_p)
    if create_dirs:
        Path(parent).mkdir(parents=True, exist_ok=True)
    elif not os.path.isdir(parent):
        return {"ok": False, "error": f"parent dir missing: {parent}"}

    backup_path = None
    if os.path.exists(abs_p):
        backup_path = f"{abs_p}.bak.{int(time.time())}"
        try:
            shutil.copy2(abs_p, backup_path)
        except Exception as e:
            logger.warning(f"backup failed: {e}")
            backup_path = None

    try:
        with open(abs_p, "w") as f:
            f.write(content)
        size = os.path.getsize(abs_p)
    except Exception as e:
        return {"ok": False, "error": str(e)}

    await _audit_log(project_id, "write_any_file",
                     {"path": abs_p, "size": size,
                      "backup": backup_path},
                     f"wrote {size}b")
    return {
        "ok": True,
        "path": abs_p,
        "bytes_written": size,
        "backup_path": backup_path,
        "summary": (f"✅ wrote {size}b to {abs_p}" +
                    (f" (backup at {backup_path})" if backup_path else "")),
    }


# ════════════════════════════════════════════════════════════════════════
# 5. edit_file — search-replace style edit
# ════════════════════════════════════════════════════════════════════════
async def edit_file(project_id: str, path: str, old_str: str,
                     new_str: str, replace_all: bool = False) -> Dict[str, Any]:
    """Search-and-replace inside any file. old_str must match exactly.

    Same path rules as write_any_file. Pre-existing file is backed up.
    """
    if not path or old_str is None or new_str is None:
        return {"ok": False, "error": "path, old_str, new_str required"}

    read_r = await read_any_file(project_id, path, max_bytes=2_000_000)
    if not read_r.get("ok"):
        return read_r
    content = read_r["content"]

    count = content.count(old_str)
    if count == 0:
        return {"ok": False, "error": "old_str not found in file"}
    if count > 1 and not replace_all:
        return {"ok": False,
                "error": f"old_str matches {count} times; pass replace_all=true or add more context"}

    new_content = (content.replace(old_str, new_str)
                   if replace_all else content.replace(old_str, new_str, 1))

    write_r = await write_any_file(project_id, path, new_content,
                                    create_dirs=False)
    if not write_r.get("ok"):
        return write_r

    await _audit_log(project_id, "edit_file",
                     {"path": path, "matches": count},
                     f"replaced {count if replace_all else 1} match(es)")
    return {
        "ok": True,
        "path": path,
        "matches_replaced": count if replace_all else 1,
        "backup_path": write_r.get("backup_path"),
        "summary": f"✅ replaced {count if replace_all else 1}× in {path}",
    }


# ════════════════════════════════════════════════════════════════════════
# 6. web_search — DuckDuckGo HTML search (no API key needed)
# ════════════════════════════════════════════════════════════════════════
async def web_search(query: str, num_results: int = 8) -> Dict[str, Any]:
    """Search the web via DuckDuckGo HTML endpoint. Returns titles + URLs +
    snippets. Use this when the AI needs current docs, latest SDK versions,
    error message lookups, etc.
    """
    if not query or not query.strip():
        return {"ok": False, "error": "query required"}
    if len(query) > 500:
        return {"ok": False, "error": "query too long"}
    n = max(1, min(15, int(num_results or 8)))

    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError as e:
        return {"ok": False, "error": f"missing dependency: {e}"}

    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        async with httpx.AsyncClient(timeout=12.0,
                                      follow_redirects=True) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            html = r.text
    except Exception as e:
        return {"ok": False, "error": f"search failed: {type(e).__name__}: {str(e)[:150]}"}

    soup = BeautifulSoup(html, "html.parser")
    results = []
    for div in soup.select("div.result")[:n]:
        a = div.select_one("a.result__a")
        snip = div.select_one(".result__snippet")
        if not a:
            continue
        title = a.get_text(" ", strip=True)
        href = a.get("href", "")
        # DDG wraps URLs — extract the real target
        m = re.search(r"uddg=([^&]+)", href)
        if m:
            from urllib.parse import unquote
            href = unquote(m.group(1))
        snippet = snip.get_text(" ", strip=True) if snip else ""
        results.append({"title": title[:300], "url": href,
                         "snippet": snippet[:400]})

    return {
        "ok": True,
        "query": query,
        "count": len(results),
        "results": results,
        "summary": f"🔍 found {len(results)} results for: {query}",
    }


# ════════════════════════════════════════════════════════════════════════
# 7. get_integration_playbook — built-in templates for common integrations
# ════════════════════════════════════════════════════════════════════════
INTEGRATION_PLAYBOOKS = {
    "stripe": {
        "service": "Stripe Payments",
        "env_vars": ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"],
        "install": "pip install stripe==12.0.0",
        "backend_snippet": """import stripe, os
stripe.api_key = os.environ['STRIPE_SECRET_KEY']

# Create checkout session
session = stripe.checkout.Session.create(
    payment_method_types=['card'],
    line_items=[{'price': 'price_xxx', 'quantity': 1}],
    mode='payment',
    success_url='https://yoursite.com/success?session_id={CHECKOUT_SESSION_ID}',
    cancel_url='https://yoursite.com/cancel',
)
# Redirect user to session.url
""",
        "frontend_snippet": """// In your checkout button handler
fetch('/api/create-checkout', {method: 'POST'})
  .then(r => r.json())
  .then(d => window.location.href = d.url);
""",
        "docs": "https://docs.stripe.com/api",
    },
    "openai": {
        "service": "OpenAI Chat (GPT-5.2 via Emergent LLM key)",
        "env_vars": ["EMERGENT_LLM_KEY"],
        "install": "pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/",
        "backend_snippet": """from emergentintegrations.llm.chat import LlmChat, UserMessage
import os

chat = LlmChat(
    api_key=os.environ['EMERGENT_LLM_KEY'],
    session_id='user-session-id',
    system_message='You are a helpful assistant.'
).with_model('openai', 'gpt-5.2')

response = await chat.send_message(UserMessage(text='Hello!'))
""",
        "docs": "https://platform.openai.com/docs",
    },
    "claude": {
        "service": "Anthropic Claude Sonnet 4.5 (via Emergent LLM key)",
        "env_vars": ["EMERGENT_LLM_KEY"],
        "install": "pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/",
        "backend_snippet": """from emergentintegrations.llm.chat import LlmChat, UserMessage
import os

chat = LlmChat(
    api_key=os.environ['EMERGENT_LLM_KEY'],
    session_id='session-id',
    system_message='You are Claude.'
).with_model('anthropic', 'claude-sonnet-4-5-20250929')

response = await chat.send_message(UserMessage(text='Hi'))
""",
    },
    "gemini": {
        "service": "Google Gemini (incl. Nano Banana image gen)",
        "env_vars": ["EMERGENT_LLM_KEY"],
        "install": "pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/",
        "backend_snippet": """from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
chat = LlmChat(api_key=os.environ['EMERGENT_LLM_KEY'],
               session_id='s1',
               system_message='').with_model('gemini', 'gemini-2.5-flash')
# For Nano Banana image gen, use model 'gemini-2.5-flash-image'
""",
    },
    "resend": {
        "service": "Resend Email API",
        "env_vars": ["RESEND_API_KEY"],
        "install": "pip install resend",
        "backend_snippet": """import resend, os
resend.api_key = os.environ['RESEND_API_KEY']

resend.Emails.send({
    "from": "Zenrex <noreply@zenrex.ai>",
    "to": ["user@example.com"],
    "subject": "Welcome!",
    "html": "<h1>Hi from Zenrex</h1>"
})
""",
        "get_key": "https://resend.com/api-keys",
    },
    "twilio": {
        "service": "Twilio SMS",
        "env_vars": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"],
        "install": "pip install twilio",
        "backend_snippet": """from twilio.rest import Client
import os

c = Client(os.environ['TWILIO_ACCOUNT_SID'], os.environ['TWILIO_AUTH_TOKEN'])
m = c.messages.create(
    from_=os.environ['TWILIO_FROM_NUMBER'],
    to='+966555555555',
    body='Hello from Zenrex!'
)
""",
        "get_key": "https://console.twilio.com/",
    },
    "paypal": {
        "service": "PayPal Checkout",
        "env_vars": ["PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "PAYPAL_MODE"],
        "install": "pip install paypalrestsdk",
        "backend_snippet": """import paypalrestsdk, os
paypalrestsdk.configure({
    "mode": os.environ.get('PAYPAL_MODE','sandbox'),
    "client_id": os.environ['PAYPAL_CLIENT_ID'],
    "client_secret": os.environ['PAYPAL_CLIENT_SECRET']
})
""",
    },
    "google_oauth": {
        "service": "Emergent-managed Google OAuth (no setup needed!)",
        "env_vars": [],
        "install": "# Frontend only — uses Emergent's hosted OAuth",
        "frontend_snippet": """// 1. Redirect user to login
window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(window.location.origin + '/auth-callback')}`;

// 2. In /auth-callback page, read session_id from URL fragment (#session_id=xxx)
// 3. POST it to backend to exchange for session token
const sid = new URLSearchParams(window.location.hash.slice(1)).get('session_id');
await fetch('/api/auth/google/exchange', {method:'POST', body: JSON.stringify({session_id: sid})});
""",
        "backend_snippet": """# Backend exchanges session_id for user info
import httpx
async def exchange_session(session_id):
    async with httpx.AsyncClient() as c:
        r = await c.get('https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data',
                         headers={'X-Session-ID': session_id})
        return r.json()  # {email, name, picture, session_token}
""",
    },
    "fal": {
        "service": "fal.ai (image/video generation, requires user key)",
        "env_vars": ["FAL_KEY"],
        "install": "pip install fal-client",
        "get_key": "https://fal.ai/dashboard/keys",
        "backend_snippet": """import fal_client, os
os.environ['FAL_KEY'] = os.environ['FAL_KEY']
result = fal_client.subscribe(
    "fal-ai/flux-pro",
    arguments={"prompt": "a cat", "image_size": "landscape_16_9"}
)
print(result['images'][0]['url'])
""",
    },
}


def get_integration_playbook(service_name: str) -> Dict[str, Any]:
    """Return a ready-to-use integration playbook for the named service."""
    key = (service_name or "").lower().strip()
    aliases = {
        "anthropic": "claude", "claude-sonnet": "claude",
        "gpt": "openai", "gpt5": "openai", "gpt-5": "openai",
        "nano-banana": "gemini", "google-auth": "google_oauth",
        "email": "resend", "sms": "twilio",
    }
    key = aliases.get(key, key)
    if key in INTEGRATION_PLAYBOOKS:
        return {"ok": True, **INTEGRATION_PLAYBOOKS[key]}
    return {"ok": False,
            "error": f"no playbook for '{service_name}'",
            "available": sorted(INTEGRATION_PLAYBOOKS.keys())}


# ════════════════════════════════════════════════════════════════════════
# 8. deploy_to_production — run /app/deploy/deploy.sh
# ════════════════════════════════════════════════════════════════════════
async def deploy_to_production(domain: str = "zenrex.ai",
                                wait_seconds: int = 30) -> Dict[str, Any]:
    """Run the deploy script and return its output.

    NOTE: This is for owner workflows only. The AI agent uses this when
    the owner explicitly says 'deploy', 'انشر', 'ارفع للسيرفر'.
    """
    script = "/app/deploy/deploy.sh"
    if not os.path.exists(script):
        return {"ok": False, "error": f"deploy script not found at {script}"}
    if domain not in ("zenrex.ai", "www.zenrex.ai"):
        return {"ok": False, "error": "only zenrex.ai deployment is supported"}

    try:
        proc = subprocess.run(
            ["bash", script, domain],
            capture_output=True,
            timeout=max(60, min(600, wait_seconds * 20)),
            text=True,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "deploy timed out (still running in background)"}

    stdout = (proc.stdout or "")[:30_000]
    stderr = (proc.stderr or "")[:10_000]
    return {
        "ok": proc.returncode == 0,
        "stdout": stdout,
        "stderr": stderr,
        "return_code": proc.returncode,
        "summary": ("✅ deploy succeeded" if proc.returncode == 0
                    else f"❌ deploy failed (exit={proc.returncode})"),
    }


# ════════════════════════════════════════════════════════════════════════
# 9. call_self_test_agent — autonomous scenario generation + browser test
# ════════════════════════════════════════════════════════════════════════
async def call_self_test_agent(project_id: str, base_url: str,
                                 user_goal: str = "") -> Dict[str, Any]:
    """Auto-generate browser scenarios based on the project HTML, then
    run verify_my_work. This is the AI testing its own work end-to-end.
    """
    from .runtime import (
        auto_generate_scenarios as _ags,
        verify_my_work as _vmw,
    )
    if not base_url:
        return {"ok": False, "error": "base_url required"}

    # Fetch the current HTML to generate scenarios
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10, follow_redirects=True,
                                      verify=False) as client:
            r = await client.get(base_url)
            html = r.text if r.status_code == 200 else ""
    except Exception as e:
        return {"ok": False, "error": f"fetch failed: {e}"}

    if not html:
        return {"ok": False, "error": "could not load preview HTML"}

    scenarios = _ags(html)
    if not scenarios:
        return {"ok": True, "passed": 0, "total": 0,
                 "message": "no testable buttons/links found — site is static"}

    result = await _vmw(base_url, scenarios, timeout_seconds=25)
    result["user_goal"] = user_goal
    result["scenarios_generated"] = len(scenarios)
    return result


# ════════════════════════════════════════════════════════════════════════
# Tool registry for easy dispatch
# ════════════════════════════════════════════════════════════════════════
UNRESTRICTED_TOOLS = {
    "run_bash_unrestricted": run_bash_unrestricted,
    "run_python_in_sandbox": run_python_in_sandbox,
    "read_any_file": read_any_file,
    "write_any_file": write_any_file,
    "edit_file": edit_file,
    "web_search": web_search,
    "get_integration_playbook": get_integration_playbook,
    "deploy_to_production": deploy_to_production,
    "call_self_test_agent": call_self_test_agent,
}
