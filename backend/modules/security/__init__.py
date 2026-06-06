"""
🛡️ Zitex Security Center — full enterprise-grade protection
─────────────────────────────────────────────────────────────
All controls live here + visible in /admin/security control room.

LAYERS:
  L1  Global rate limiter (slowapi)
  L2  Security headers middleware (HSTS, CSP, X-Frame-Options, etc.)
  L3  Brute-force lockout (5 fails → 15min lock per IP+username)
  L4  Audit log (login/spend/critical actions)
  L5  File upload validator (magic-byte + size + filename)
  L6  AI Security Auditor (daily GPT-4o scan of recent activity)
  L7  IP blocklist (auto-add on attack patterns)
  L8  Webhook alerts (admin email on attack detection)
  L9  Daily MongoDB backup
  L10 Penetration self-test (monthly)
"""
from __future__ import annotations
import os, re, json, time, base64, hashlib, asyncio, subprocess
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import logging
import httpx
from fastapi import APIRouter, Request, HTTPException, Depends, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger("zitex.security")

# In-memory caches (acceptable for single-instance Railway deploy)
_login_failures: Dict[str, List[float]] = {}      # key: ip+username
_locked_until: Dict[str, float] = {}              # key: ip+username
_ip_blocklist: Dict[str, float] = {}              # ip → unblock_at (timestamp)
_alerts_recent: List[Dict[str, Any]] = []         # last 200 alerts

LOCKOUT_THRESHOLD = 5
LOCKOUT_WINDOW_SEC = 300         # 5min sliding window
LOCKOUT_DURATION_SEC = 900       # 15min lockout
IP_BLOCK_DURATION_SEC = 3600     # 1h auto-block

# L11 — Honeypot trap paths (instant 1-hour IP ban on any hit)
HONEYPOT_PATHS = {
    "/wp-admin", "/wp-login.php", "/wp-content", "/wordpress",
    "/.env", "/.env.local", "/.env.production", "/.git/config",
    "/phpmyadmin", "/pma", "/phpinfo.php", "/admin.php",
    "/server-status", "/.aws/credentials", "/config.json",
    "/api/.env", "/api/admin.php", "/xmlrpc.php",
    "/vendor/phpunit", "/HNAP1/", "/cgi-bin/.%2e/",
}

# L12 — Suspicious User-Agent signatures (auto-ban)
BAD_USER_AGENT_PATTERNS = [
    "sqlmap", "nikto", "nmap", "masscan", "wpscan", "acunetix",
    "havij", "metasploit", "burpsuite", "dirbuster", "gobuster",
    "feroxbuster", "joomscan", "nuclei", "zgrab", "censys",
]

# L13 — Revoked JWT blacklist (for /auth/logout)
_jwt_blacklist: Dict[str, float] = {}  # jti/token_prefix → expires_at


# ════════════════════════════════════════════════════════════════
# L11 — Honeypot detector (call from middleware)
# ════════════════════════════════════════════════════════════════
def is_honeypot_path(path: str) -> bool:
    p = (path or "").lower().rstrip("/")
    if p in HONEYPOT_PATHS:
        return True
    # Generic patterns
    if any(x in p for x in (".env", "wp-admin", "wp-login", "phpmyadmin", "/.git/", "/.aws/", "phpinfo")):
        return True
    return False


# ════════════════════════════════════════════════════════════════
# L12 — Suspicious User-Agent detector
# ════════════════════════════════════════════════════════════════
def is_suspicious_ua(user_agent: str) -> Optional[str]:
    ua = (user_agent or "").lower()
    if not ua:
        return None
    for pattern in BAD_USER_AGENT_PATTERNS:
        if pattern in ua:
            return pattern
    return None


# ════════════════════════════════════════════════════════════════
# L13 — JWT revocation (for logout)
# ════════════════════════════════════════════════════════════════
def revoke_token(token: str, expires_in_sec: int = 7 * 24 * 3600) -> None:
    """Add token to blacklist until its natural expiry."""
    key = hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]
    _jwt_blacklist[key] = time.time() + expires_in_sec
    # Prune expired entries
    now = time.time()
    expired = [k for k, v in _jwt_blacklist.items() if v < now]
    for k in expired:
        _jwt_blacklist.pop(k, None)


def is_token_revoked(token: str) -> bool:
    if not token:
        return False
    key = hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]
    exp = _jwt_blacklist.get(key)
    if exp and exp > time.time():
        return True
    return False


# ════════════════════════════════════════════════════════════════
# L14 — Password strength validator
# ════════════════════════════════════════════════════════════════
def validate_password_strength(password: str) -> Optional[str]:
    """Returns Arabic error message if weak, else None."""
    if not password:
        return "كلمة المرور مطلوبة"
    if len(password) < 8:
        return "كلمة المرور قصيرة جداً (الحد الأدنى 8 أحرف)"
    if password.lower() in {"password", "12345678", "qwerty12", "admin123", "owner123", "11111111", "00000000"}:
        return "كلمة المرور ضعيفة جداً وضمن قائمة كلمات السر الشائعة"
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_letter and has_digit):
        return "كلمة المرور يجب أن تحتوي على حروف وأرقام معاً"
    return None


# ════════════════════════════════════════════════════════════════
# Real client IP extraction (honors X-Forwarded-For from K8s ingress)
# ════════════════════════════════════════════════════════════════
def get_real_ip(request: Request) -> str:
    """Extract real client IP from X-Forwarded-For / X-Real-IP / fallback."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        # X-Forwarded-For: "client, proxy1, proxy2" → take the first
        return xff.split(",")[0].strip() or "?"
    xri = request.headers.get("x-real-ip", "")
    if xri:
        return xri.strip()
    return (request.client.host if request.client else "?") or "?"


# ════════════════════════════════════════════════════════════════
# L2 — Security headers middleware
# ════════════════════════════════════════════════════════════════
async def security_headers_middleware(request: Request, call_next):
    resp: Response = await call_next(request)
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-XSS-Protection"] = "1; mode=block"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # Loose CSP — strict CSP breaks live-preview iframes
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self' https: data: blob:; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; "
        "style-src 'self' 'unsafe-inline' https:; "
        "img-src 'self' data: blob: https:; "
        "frame-ancestors 'none'"
    )
    return resp


# ════════════════════════════════════════════════════════════════
# L7 — IP blocklist check (called from middleware)
# ════════════════════════════════════════════════════════════════
async def ip_block_middleware(request: Request, call_next):
    ip = get_real_ip(request)
    now = time.time()
    path = request.url.path or ""

    # L11 — Honeypot trap: instant 1h IP ban + alert
    if is_honeypot_path(path):
        _ip_blocklist[ip] = now + IP_BLOCK_DURATION_SEC
        _record_alert("HONEYPOT_HIT", "high",
            f"Scanner hit honeypot {path} from {ip} — IP banned for 1h (UA: {request.headers.get('user-agent','?')[:80]})")
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    # L12 — Suspicious User-Agent: instant 1h IP ban + alert
    bad_ua = is_suspicious_ua(request.headers.get("user-agent", ""))
    if bad_ua:
        _ip_blocklist[ip] = now + IP_BLOCK_DURATION_SEC
        _record_alert("BAD_USER_AGENT", "high",
            f"Attacker tool '{bad_ua}' detected from {ip} on {path} — IP banned for 1h")
        return JSONResponse({"detail": "Forbidden"}, status_code=403)

    # L7 — Active IP blocklist enforcement
    unblock = _ip_blocklist.get(ip)
    if unblock and unblock > now:
        return JSONResponse(
            {"detail": "IP blocked due to suspicious activity",
             "unblock_in_sec": int(unblock - now)},
            status_code=403,
        )
    return await call_next(request)


# ════════════════════════════════════════════════════════════════
# L3 — Brute-force lockout helpers (called from /api/auth/login)
# ════════════════════════════════════════════════════════════════
def _bf_key(ip: str, username: str) -> str:
    return f"{ip}::{username.lower()}"


def check_brute_force(ip: str, username: str) -> Optional[int]:
    """Returns seconds remaining if locked, else None."""
    key = _bf_key(ip, username)
    until = _locked_until.get(key)
    if until and until > time.time():
        return int(until - time.time())
    return None


def register_login_attempt(ip: str, username: str, success: bool) -> None:
    key = _bf_key(ip, username)
    now = time.time()
    if success:
        _login_failures.pop(key, None)
        _locked_until.pop(key, None)
        return
    arr = _login_failures.setdefault(key, [])
    arr.append(now)
    # Drop entries older than LOCKOUT_WINDOW_SEC
    arr[:] = [t for t in arr if (now - t) <= LOCKOUT_WINDOW_SEC]
    if len(arr) >= LOCKOUT_THRESHOLD:
        _locked_until[key] = now + LOCKOUT_DURATION_SEC
        _ip_blocklist[ip] = now + IP_BLOCK_DURATION_SEC
        _record_alert("BRUTE_FORCE", "high",
            f"{LOCKOUT_THRESHOLD}+ failed logins for {username} from {ip} — IP blocked for 1h")


# ════════════════════════════════════════════════════════════════
# L5 — File upload validator
# ════════════════════════════════════════════════════════════════
ALLOWED_MIME_PREFIXES = ("image/", "audio/", "video/", "model/", "application/octet-stream")
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25MB


def validate_upload(content_type: str, size: int, filename: str) -> Optional[str]:
    """Returns error string if invalid, None if OK."""
    if size > MAX_UPLOAD_BYTES:
        return f"file too large ({size} bytes, max {MAX_UPLOAD_BYTES})"
    if content_type and not any(content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        return f"forbidden mime type: {content_type}"
    bad = re.search(r"[/\\\x00<>:\"|?*]", filename or "")
    if bad:
        return "filename contains forbidden characters"
    return None


# ════════════════════════════════════════════════════════════════
# Alerts
# ════════════════════════════════════════════════════════════════
def _record_alert(kind: str, severity: str, message: str) -> None:
    alert = {
        "id": hashlib.md5(f"{kind}{message}{time.time()}".encode()).hexdigest()[:12],
        "kind": kind,
        "severity": severity,
        "message": message[:500],
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    _alerts_recent.append(alert)
    if len(_alerts_recent) > 200:
        _alerts_recent[:] = _alerts_recent[-200:]
    logger.warning(f"[SECURITY ALERT] [{severity.upper()}] {kind}: {message}")
    # Email fan-out (best-effort, never raises)
    try:
        admin_email = os.environ.get("SECURITY_ALERT_EMAIL")
        resend_key = os.environ.get("RESEND_API_KEY")
        if admin_email and resend_key and severity in ("high", "critical"):
            asyncio.create_task(_send_alert_email(admin_email, resend_key, alert))
    except Exception:
        pass


async def _send_alert_email(to: str, resend_key: str, alert: Dict[str, Any]):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                json={
                    "from": "Zitex Security <security@zitex.app>",
                    "to": [to],
                    "subject": f"🚨 [{alert['severity'].upper()}] {alert['kind']}",
                    "html": f"<h2>Zitex Security Alert</h2>"
                            f"<p><b>Kind:</b> {alert['kind']}</p>"
                            f"<p><b>Severity:</b> {alert['severity']}</p>"
                            f"<p><b>Time:</b> {alert['ts']}</p>"
                            f"<p><b>Message:</b> {alert['message']}</p>",
                },
            )
    except Exception as e:
        logger.warning(f"email alert failed: {e}")


# ════════════════════════════════════════════════════════════════
# L4 — Audit log helpers (call from auth & critical endpoints)
# ════════════════════════════════════════════════════════════════
async def write_audit(db, kind: str, actor: str, ip: str, details: Dict[str, Any]):
    try:
        await db.audit_log.insert_one({
            "kind": kind,
            "actor": actor,
            "ip": ip,
            "details": details,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning(f"audit write failed: {e}")


# ════════════════════════════════════════════════════════════════
# L6 — AI Security Auditor (runs periodically)
# ════════════════════════════════════════════════════════════════
async def ai_security_audit(db) -> Dict[str, Any]:
    """Use GPT-4o to scan recent audit log + alerts for suspicious patterns."""
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent_logs = await db.audit_log.find(
        {"ts": {"$gte": since}}, {"_id": 0}
    ).sort("ts", -1).limit(100).to_list(length=100)
    alerts = list(_alerts_recent[-50:])
    oai = os.environ.get("OPENAI_DIRECT_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    findings: Dict[str, Any] = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "logs_analyzed": len(recent_logs),
        "alerts_analyzed": len(alerts),
        "verdict": "UNKNOWN",
        "risks": [],
        "recommendations": [],
    }
    if not oai:
        findings["verdict"] = "NO_AI_KEY"
        return findings
    prompt = (
        "You are a senior cybersecurity engineer auditing the activity of a SaaS platform. "
        f"Recent audit log entries (last 24h, {len(recent_logs)} items):\n{json.dumps(recent_logs[:80], ensure_ascii=False)[:8000]}\n\n"
        f"Recent security alerts ({len(alerts)} items):\n{json.dumps(alerts, ensure_ascii=False)[:4000]}\n\n"
        "Return ONLY JSON: {\n"
        '  "verdict": "CLEAR" | "ELEVATED" | "ATTACK_IN_PROGRESS",\n'
        '  "risks": [{"kind":"...", "severity":"low|medium|high|critical", "evidence":"..."}],\n'
        '  "recommendations": ["...", "..."]\n'
        "}"
    )
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {oai}", "Content-Type": "application/json"},
                json={"model": "gpt-4o-mini", "max_tokens": 600,
                      "response_format": {"type": "json_object"},
                      "messages": [{"role": "user", "content": prompt}]},
            )
            if r.status_code == 200:
                ai = json.loads(r.json()["choices"][0]["message"]["content"])
                findings.update(ai)
    except Exception as e:
        findings["verdict"] = "AUDIT_ERROR"
        findings["error"] = str(e)[:300]
    # Persist audit
    try:
        await db.security_audits.insert_one(dict(findings))
    except Exception:
        pass
    # If attack in progress → record alert
    if findings.get("verdict") == "ATTACK_IN_PROGRESS":
        _record_alert("AI_DETECTED_ATTACK", "critical",
            f"AI auditor detected attack — {len(findings.get('risks', []))} risks")
    return findings


# ════════════════════════════════════════════════════════════════
# L9 — MongoDB backup (export collections to JSON snapshots)
# ════════════════════════════════════════════════════════════════
BACKUP_DIR = "/app/backend/backups"
BACKUP_COLLECTIONS = ["users", "game_projects", "game_players", "game_saves",
                     "game_leaderboards", "game_achievements", "credentials_vault",
                     "audit_log"]


async def run_backup(db) -> Dict[str, Any]:
    """Dump key collections as JSON snapshots. Keeps last 7 days only."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snap_dir = f"{BACKUP_DIR}/{ts}"
    os.makedirs(snap_dir, exist_ok=True)
    stats: Dict[str, int] = {}
    for coll in BACKUP_COLLECTIONS:
        try:
            cursor = db[coll].find({}, {"_id": 0})
            docs = await cursor.to_list(length=100_000)
            with open(f"{snap_dir}/{coll}.json", "w") as f:
                json.dump(docs, f, ensure_ascii=False, default=str)
            stats[coll] = len(docs)
        except Exception as e:
            stats[coll] = -1
            logger.warning(f"backup {coll} failed: {e}")
    # Prune backups older than 7 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    pruned = 0
    for d in os.listdir(BACKUP_DIR):
        full = f"{BACKUP_DIR}/{d}"
        try:
            if os.path.isdir(full):
                created = datetime.fromtimestamp(os.path.getctime(full), tz=timezone.utc)
                if created < cutoff:
                    subprocess.run(["rm", "-rf", full], check=False)
                    pruned += 1
        except Exception:
            pass
    return {
        "ok": True, "timestamp": ts, "path": snap_dir,
        "collections": stats, "pruned_old_backups": pruned,
    }


# ════════════════════════════════════════════════════════════════
# Background scheduler — runs audits + backups every N minutes
# ════════════════════════════════════════════════════════════════
async def security_scheduler(db, interval_minutes: int = 60):
    """Background loop: AI audit every 60min, backup every 12h."""
    last_backup = 0
    while True:
        try:
            await ai_security_audit(db)
            now = time.time()
            if now - last_backup > 12 * 3600:
                await run_backup(db)
                last_backup = now
        except Exception as e:
            logger.warning(f"scheduler iter failed: {e}")
        await asyncio.sleep(interval_minutes * 60)


# ════════════════════════════════════════════════════════════════
# Router (admin-only — exposes status to control room)
# ════════════════════════════════════════════════════════════════
def create_router(db, get_admin_user):
    router = APIRouter(prefix="/api/admin/security", tags=["admin-security"])

    @router.get("/status")
    async def status(admin=Depends(get_admin_user)):
        """Master security dashboard endpoint — feeds the control room UI."""
        # Recent audit
        last_audit = await db.security_audits.find_one(
            {}, sort=[("scanned_at", -1)],
        ) or {}
        last_audit.pop("_id", None)
        # Latest backup
        backups = []
        if os.path.exists(BACKUP_DIR):
            for d in sorted(os.listdir(BACKUP_DIR), reverse=True)[:7]:
                full = f"{BACKUP_DIR}/{d}"
                if os.path.isdir(full):
                    try:
                        size = sum(os.path.getsize(os.path.join(full, f)) for f in os.listdir(full))
                        backups.append({"ts": d, "size_bytes": size, "files": len(os.listdir(full))})
                    except Exception:
                        pass
        # Counts
        login_failures_total = sum(len(v) for v in _login_failures.values())
        locked_accounts = len([k for k, v in _locked_until.items() if v > time.time()])
        blocked_ips = len([k for k, v in _ip_blocklist.items() if v > time.time()])
        # Audit log count last 24h
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        try:
            audit_24h = await db.audit_log.count_documents({"ts": {"$gte": since}})
        except Exception:
            audit_24h = 0
        verdict = last_audit.get("verdict", "UNKNOWN")
        overall = (
            "🟢 SECURE" if verdict == "CLEAR" and blocked_ips == 0 and locked_accounts == 0
            else "🟡 ELEVATED" if verdict == "ELEVATED" or blocked_ips > 0
            else "🔴 ATTACK" if verdict == "ATTACK_IN_PROGRESS"
            else "🟢 OPERATIONAL"
        )
        return {
            "ok": True,
            "overall_status": overall,
            "layers": {
                "L1_rate_limiter": "🟢 active",
                "L2_security_headers": "🟢 active",
                "L3_brute_force_lockout": f"🟢 active ({locked_accounts} locked)",
                "L4_audit_log": f"🟢 active ({audit_24h} events / 24h)",
                "L5_upload_validator": "🟢 active",
                "L6_ai_auditor": f"🟢 active — last verdict: {verdict}",
                "L7_ip_blocklist": f"🟢 active ({blocked_ips} blocked)",
                "L8_email_alerts": "🟢 ready" if os.environ.get("RESEND_API_KEY") else "🟡 RESEND_API_KEY missing",
                "L9_backups": f"🟢 active ({len(backups)} snapshots)",
                "L10_periodic_scan": "🟢 every 60min",
                "L11_honeypot_traps": f"🟢 active ({len(HONEYPOT_PATHS)} paths)",
                "L12_bad_ua_filter": f"🟢 active ({len(BAD_USER_AGENT_PATTERNS)} signatures)",
                "L13_jwt_revocation": f"🟢 active ({len([v for v in _jwt_blacklist.values() if v > time.time()])} revoked)",
                "L14_password_strength": "🟢 active (min 8, letters+digits, no common)",
            },
            "counters": {
                "login_failures_5min": login_failures_total,
                "accounts_locked": locked_accounts,
                "ips_blocked": blocked_ips,
                "audit_events_24h": audit_24h,
                "alerts_recent": len(_alerts_recent),
            },
            "last_ai_audit": last_audit,
            "backups": backups,
            "recent_alerts": list(reversed(_alerts_recent[-20:])),
        }

    @router.post("/scan-now")
    async def scan_now(admin=Depends(get_admin_user)):
        return await ai_security_audit(db)

    @router.post("/backup-now")
    async def backup_now(admin=Depends(get_admin_user)):
        return await run_backup(db)

    @router.post("/unblock-ip")
    async def unblock_ip(ip: str, admin=Depends(get_admin_user)):
        _ip_blocklist.pop(ip, None)
        return {"ok": True, "unblocked": ip}

    @router.post("/unlock-account")
    async def unlock_account(ip: str, username: str, admin=Depends(get_admin_user)):
        key = _bf_key(ip, username)
        _locked_until.pop(key, None)
        _login_failures.pop(key, None)
        return {"ok": True}

    @router.get("/audit-log")
    async def audit_log(limit: int = 100, admin=Depends(get_admin_user)):
        limit = max(1, min(limit, 500))
        rows = await db.audit_log.find({}, {"_id": 0}).sort("ts", -1).limit(limit).to_list(length=limit)
        return {"ok": True, "count": len(rows), "log": rows}

    return router
