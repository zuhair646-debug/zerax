"""
Zerax Security Center — EXTENDED 14-Layer test suite
─────────────────────────────────────────────────────
Covers L1 (actual slowapi rate limit), L11 (honeypot), L12 (bad UA),
L13 (JWT revocation), L14 (password strength) — plus regression on
L2/L3/L4 and /status returning all 14 layers.

Each test uses a UNIQUE X-Forwarded-For IP so they don't interfere.
After IP-block tests we unblock via /api/admin/security/unblock-ip.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fall back to reading frontend env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                    break
    except Exception:
        pass

ADMIN_EMAIL = "owner@zerax.com"
ADMIN_PASSWORD = "owner123"

CLEAN_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


# ════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════
@pytest.fixture(scope="module")
def admin_token():
    fresh_ip = f"200.0.0.{int(time.time()) % 250}"
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"X-Forwarded-For": fresh_ip, "User-Agent": CLEAN_UA},
        timeout=20,
    )
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    tok = r.json().get("token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "User-Agent": CLEAN_UA}


def unblock_ip(admin_headers, ip):
    try:
        requests.post(
            f"{BASE_URL}/api/admin/security/unblock-ip",
            params={"ip": ip},
            headers=admin_headers,
            timeout=10,
        )
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════
# L11 — Honeypot
# ════════════════════════════════════════════════════════════════
class TestL11Honeypot:
    HONEYPOT_IP = "11.11.11.11"

    def test_honeypot_api_env_returns_404(self, admin_headers):
        """
        NOTE: K8s ingress routes non-/api/* paths to the React frontend container,
        so requests to /.env or /wp-admin never reach the FastAPI backend's
        honeypot middleware (they return 200 with the SPA HTML).
        Only /api/* honeypot paths actually reach backend. We test /api/.env here.
        """
        unblock_ip(admin_headers, self.HONEYPOT_IP)
        r = requests.get(
            f"{BASE_URL}/api/.env",
            headers={"X-Forwarded-For": self.HONEYPOT_IP, "User-Agent": CLEAN_UA},
            timeout=10,
        )
        assert r.status_code == 404, f"expected 404 honeypot trap, got {r.status_code}: {r.text[:200]}"

    def test_honeypot_followup_request_is_blocked(self, admin_headers):
        ip = "11.11.11.12"
        unblock_ip(admin_headers, ip)
        # 1. Trigger honeypot via /api/admin.php (reaches backend)
        r1 = requests.get(
            f"{BASE_URL}/api/admin.php",
            headers={"X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
            timeout=10,
        )
        assert r1.status_code == 404, f"trap GET /api/admin.php returned {r1.status_code}"
        # 2. Now any legit request from same IP must be 403-blocked
        r2 = requests.get(
            f"{BASE_URL}/api/games/projects",
            headers={"X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
            timeout=10,
        )
        assert r2.status_code == 403, f"expected 403 after honeypot, got {r2.status_code}: {r2.text[:200]}"
        body = r2.json()
        assert "IP blocked" in (body.get("detail") or ""), f"unexpected body: {body}"
        unblock_ip(admin_headers, ip)

    def test_honeypot_alert_recorded(self, admin_headers):
        ip = "11.11.11.13"
        unblock_ip(admin_headers, ip)
        # Use /api/.env — reaches backend reliably
        requests.get(
            f"{BASE_URL}/api/.env",
            headers={"X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
            timeout=10,
        )
        # Fetch status
        s = requests.get(
            f"{BASE_URL}/api/admin/security/status",
            headers=admin_headers,
            timeout=15,
        )
        assert s.status_code == 200, s.text[:200]
        alerts = s.json().get("recent_alerts", [])
        kinds = {a.get("kind") for a in alerts}
        assert "HONEYPOT_HIT" in kinds, f"HONEYPOT_HIT not in alerts: {kinds}"
        unblock_ip(admin_headers, ip)


# ════════════════════════════════════════════════════════════════
# L11 — NEW: Public honeypot-report endpoint (frontend catch-all)
# ════════════════════════════════════════════════════════════════
class TestL11HoneypotReport:
    """Tests the new POST /api/security/honeypot-report endpoint added
    to close the non-/api scanner gap flagged in iteration_33."""

    def test_honeypot_report_env_bans_ip_and_records_alert(self, admin_headers):
        ip = "33.33.33.33"
        unblock_ip(admin_headers, ip)
        # 1. POST honeypot report with /.env path
        r = requests.post(
            f"{BASE_URL}/api/security/honeypot-report",
            json={"path": "/.env"},
            headers={"X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
            timeout=10,
        )
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text[:200]}"
        body = r.json()
        assert body.get("ok") is True, f"unexpected body: {body}"
        assert body.get("ip_banned") == ip, f"ip_banned mismatch: {body}"

        # 2. Fetch security status — HONEYPOT_HIT must be in recent alerts
        s = requests.get(
            f"{BASE_URL}/api/admin/security/status",
            headers=admin_headers,
            timeout=15,
        )
        assert s.status_code == 200, s.text[:200]
        alerts = s.json().get("recent_alerts", [])
        kinds = {a.get("kind") for a in alerts}
        assert "HONEYPOT_HIT" in kinds, f"HONEYPOT_HIT not in alerts: {kinds}"
        # Verify alert references the IP (field name is 'message')
        env_alerts = [a for a in alerts if a.get("kind") == "HONEYPOT_HIT" and ip in (a.get("message") or "")]
        assert env_alerts, f"no HONEYPOT_HIT alert references {ip}: {alerts[:5]}"

        # 3. Any follow-up request from same IP must be blocked
        r3 = requests.get(
            f"{BASE_URL}/api/games/projects",
            headers={"X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
            timeout=10,
        )
        assert r3.status_code == 403, f"expected IP-block 403, got {r3.status_code}: {r3.text[:200]}"
        unblock_ip(admin_headers, ip)

    def test_honeypot_report_wpadmin_records_alert_for_ip(self, admin_headers):
        ip = "44.44.44.44"
        unblock_ip(admin_headers, ip)
        r = requests.post(
            f"{BASE_URL}/api/security/honeypot-report",
            json={"path": "/wp-admin"},
            headers={"X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
            timeout=10,
        )
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text[:200]}"
        assert r.json().get("ip_banned") == ip

        s = requests.get(
            f"{BASE_URL}/api/admin/security/status",
            headers=admin_headers,
            timeout=15,
        )
        assert s.status_code == 200
        alerts = s.json().get("recent_alerts", [])
        ip_alerts = [a for a in alerts if a.get("kind") == "HONEYPOT_HIT" and ip in (a.get("message") or "")]
        assert ip_alerts, f"no HONEYPOT_HIT alert references {ip}: {alerts[:5]}"
        unblock_ip(admin_headers, ip)

    def test_frontend_catchall_file_exists(self):
        """Validates that the React catch-all HoneypotCatcher page is wired."""
        import os
        hp_path = "/app/frontend/src/pages/HoneypotCatcher.js"
        assert os.path.exists(hp_path), f"{hp_path} missing"
        app_js = "/app/frontend/src/App.js"
        assert os.path.exists(app_js), f"{app_js} missing"
        with open(app_js) as f:
            content = f.read()
        assert "HoneypotCatcher" in content, "App.js does not import HoneypotCatcher"
        assert 'path="*"' in content, 'catch-all <Route path="*" ...> missing in App.js'
        assert "<HoneypotCatcher" in content, "<HoneypotCatcher /> element not used in App.js"


# ════════════════════════════════════════════════════════════════
# L4 — NEW: /auth/logout writes audit-log with real IP (not '?')
# ════════════════════════════════════════════════════════════════
class TestL4LogoutRealIP:
    def test_logout_audit_log_records_real_ip(self, admin_headers):
        ip = "55.55.55.55"
        # Login fresh from this IP
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
            timeout=15,
        )
        assert r.status_code == 200, r.text[:200]
        tok = r.json()["token"]

        # Logout from same IP
        lo = requests.post(
            f"{BASE_URL}/api/auth/logout",
            headers={"Authorization": f"Bearer {tok}", "X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
            timeout=10,
        )
        assert lo.status_code == 200, lo.text[:200]
        time.sleep(1)

        # Fetch audit-log; most recent logout row should carry our IP (not '?')
        a = requests.get(
            f"{BASE_URL}/api/admin/security/audit-log?limit=200",
            headers=admin_headers,
            timeout=15,
        )
        assert a.status_code == 200, a.text[:200]
        rows = a.json().get("log", [])
        logout_rows = [r for r in rows if r.get("kind") == "logout"]
        assert logout_rows, f"no logout rows in audit log; sample: {rows[:5]}"
        # Check that at least one logout has the real IP we used
        real_ip_rows = [r for r in logout_rows if r.get("ip") == ip]
        assert real_ip_rows, (
            f"no logout row has ip={ip}; recent logout rows: "
            f"{[(r.get('ip'), r.get('ts')) for r in logout_rows[:5]]}"
        )
        # And the most recent logout overall must not be '?'
        most_recent_logout = logout_rows[0]
        assert most_recent_logout.get("ip") not in ("?", "", None), (
            f"most recent logout still has placeholder ip: {most_recent_logout}"
        )


# ════════════════════════════════════════════════════════════════
# L12 — Bad User-Agent filter
# ════════════════════════════════════════════════════════════════
class TestL12BadUserAgent:
    def test_sqlmap_ua_blocked(self, admin_headers):
        ip = "12.12.12.12"
        unblock_ip(admin_headers, ip)
        r = requests.get(
            f"{BASE_URL}/api/games/projects",
            headers={"X-Forwarded-For": ip, "User-Agent": "sqlmap/1.7"},
            timeout=10,
        )
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"
        # Subsequent request from same IP with clean UA must also be blocked (IP banned)
        r2 = requests.get(
            f"{BASE_URL}/api/games/projects",
            headers={"X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
            timeout=10,
        )
        assert r2.status_code == 403, f"IP should be banned, got {r2.status_code}"
        unblock_ip(admin_headers, ip)

    def test_nikto_ua_blocked(self, admin_headers):
        ip = "12.12.12.13"
        unblock_ip(admin_headers, ip)
        r = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"X-Forwarded-For": ip, "User-Agent": "Nikto/2.1.6 scanner"},
            timeout=10,
        )
        assert r.status_code == 403, f"expected 403, got {r.status_code}"
        unblock_ip(admin_headers, ip)

    def test_bad_ua_alert_recorded(self, admin_headers):
        ip = "12.12.12.14"
        unblock_ip(admin_headers, ip)
        requests.get(
            f"{BASE_URL}/api/games/projects",
            headers={"X-Forwarded-For": ip, "User-Agent": "nuclei v3.0"},
            timeout=10,
        )
        s = requests.get(
            f"{BASE_URL}/api/admin/security/status",
            headers=admin_headers,
            timeout=15,
        )
        kinds = {a.get("kind") for a in s.json().get("recent_alerts", [])}
        assert "BAD_USER_AGENT" in kinds, f"BAD_USER_AGENT not in alerts: {kinds}"
        unblock_ip(admin_headers, ip)


# ════════════════════════════════════════════════════════════════
# L13 — JWT revocation / logout
# ════════════════════════════════════════════════════════════════
class TestL13JWTRevocation:
    def test_login_logout_then_token_revoked(self):
        ip = "13.13.13.13"
        # Login fresh
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
            timeout=15,
        )
        assert r.status_code == 200, r.text[:200]
        tok = r.json()["token"]
        h = {"Authorization": f"Bearer {tok}", "X-Forwarded-For": ip, "User-Agent": CLEAN_UA}

        # /auth/me works
        me = requests.get(f"{BASE_URL}/api/auth/me", headers=h, timeout=10)
        assert me.status_code == 200, f"/auth/me before logout: {me.status_code} {me.text[:200]}"

        # Logout
        lo = requests.post(f"{BASE_URL}/api/auth/logout", headers=h, timeout=10)
        assert lo.status_code == 200, f"logout failed: {lo.status_code} {lo.text[:200]}"
        assert lo.json().get("ok") is True

        # Same token must now 401
        me2 = requests.get(f"{BASE_URL}/api/auth/me", headers=h, timeout=10)
        assert me2.status_code == 401, f"expected 401 after logout, got {me2.status_code}: {me2.text[:200]}"
        detail = (me2.json().get("detail") or "").lower()
        assert "revoke" in detail, f"detail should mention revoked: {detail}"


# ════════════════════════════════════════════════════════════════
# L14 — Password strength validator
# ════════════════════════════════════════════════════════════════
class TestL14PasswordStrength:
    def _register(self, password, ip):
        email = f"TEST_pw_{uuid.uuid4().hex[:10]}@example.com"
        return requests.post(
            f"{BASE_URL}/api/auth/register",
            json={"email": email, "password": password, "name": "Test User"},
            headers={"X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
            timeout=15,
        )

    def test_password_too_short_123(self):
        r = self._register("123", "14.14.14.10")
        assert r.status_code == 400, f"expected 400 for '123', got {r.status_code}: {r.text[:200]}"
        assert any(ord(c) > 127 for c in r.json().get("detail", "")), "Arabic detail expected"

    def test_password_common_password(self):
        r = self._register("password", "14.14.14.11")
        assert r.status_code == 400, f"expected 400 for 'password', got {r.status_code}"

    def test_password_too_short_abc(self):
        r = self._register("abc", "14.14.14.12")
        assert r.status_code == 400, f"expected 400 for 'abc', got {r.status_code}"

    def test_password_no_letters(self):
        r = self._register("12345678", "14.14.14.13")
        assert r.status_code == 400, f"expected 400 for '12345678', got {r.status_code}"

    def test_password_strong_succeeds(self):
        r = self._register("Abc12345", "14.14.14.14")
        assert r.status_code == 200, f"expected 200 for 'Abc12345', got {r.status_code}: {r.text[:200]}"
        data = r.json()
        assert "token" in data, f"no token in response: {data}"


# ════════════════════════════════════════════════════════════════
# L1 — Rate limit (slowapi default 300/min)
# ════════════════════════════════════════════════════════════════
class TestL1RateLimit:
    def test_burst_triggers_429(self, admin_headers):
        from concurrent.futures import ThreadPoolExecutor
        # Use a unique IP per run to avoid stale bans from previous runs
        ip = f"77.77.77.{int(time.time()) % 200 + 30}"
        unblock_ip(admin_headers, ip)
        h = {"X-Forwarded-For": ip, "User-Agent": CLEAN_UA}

        def _one(_):
            try:
                return requests.get(f"{BASE_URL}/api/games/projects", headers=h, timeout=15).status_code
            except Exception:
                return None

        statuses = []
        # 2 bursts to ensure we cross the 300/min threshold within the window
        with ThreadPoolExecutor(max_workers=40) as ex:
            statuses = list(ex.map(_one, range(320)))
        count_429 = sum(1 for s in statuses if s == 429)
        # Capture body of one 429 for assertion
        last_429_body = ""
        if count_429 > 0:
            r = requests.get(f"{BASE_URL}/api/games/projects", headers=h, timeout=10)
            last_429_body = r.text if r.status_code == 429 else "rate limit"
        assert count_429 >= 10, f"expected >=10 429 responses, got {count_429} (statuses sample: {statuses[:20]})"
        unblock_ip(admin_headers, ip)


# ════════════════════════════════════════════════════════════════
# L3 — Brute-force still works (regression)
# ════════════════════════════════════════════════════════════════
class TestL3BruteForce:
    def test_six_failed_logins_triggers_block(self, admin_headers):
        ip = f"3.3.3.{int(time.time()) % 200 + 20}"
        unblock_ip(admin_headers, ip)
        email = f"bf-{uuid.uuid4().hex[:8]}@example.com"
        statuses = []
        for i in range(7):
            r = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": email, "password": "wrongpass"},
                headers={"X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
                timeout=10,
            )
            statuses.append(r.status_code)
        # After 5 fails we expect at least one 429 OR 403
        blocked = [s for s in statuses if s in (429, 403)]
        assert len(blocked) >= 1, f"expected brute-force lock to kick in, statuses={statuses}"
        # cleanup
        unblock_ip(admin_headers, ip)
        requests.post(
            f"{BASE_URL}/api/admin/security/unlock-account",
            params={"ip": ip, "username": email},
            headers=admin_headers,
            timeout=10,
        )


# ════════════════════════════════════════════════════════════════
# L4 — audit-log shows logout events
# ════════════════════════════════════════════════════════════════
class TestL4AuditLog:
    def test_logout_appears_in_audit_log(self, admin_headers):
        ip = "4.4.4.40"
        # Login + logout to ensure at least one logout entry exists
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
            timeout=15,
        )
        assert r.status_code == 200
        tok = r.json()["token"]
        lo = requests.post(
            f"{BASE_URL}/api/auth/logout",
            headers={"Authorization": f"Bearer {tok}", "X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
            timeout=10,
        )
        assert lo.status_code == 200
        # Allow audit log write to flush
        time.sleep(1)
        a = requests.get(
            f"{BASE_URL}/api/admin/security/audit-log?limit=200",
            headers=admin_headers,
            timeout=15,
        )
        assert a.status_code == 200, a.text[:200]
        body = a.json()
        rows = body.get("log", [])
        kinds = {row.get("kind") for row in rows}
        assert "logout" in kinds, f"'logout' kind not in audit log; kinds present: {sorted(kinds)[:20]}"


# ════════════════════════════════════════════════════════════════
# /status returns ALL 14 layers
# ════════════════════════════════════════════════════════════════
class TestSecurityStatus14Layers:
    def test_all_14_layers_present(self, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/admin/security/status",
            headers=admin_headers,
            timeout=20,
        )
        assert r.status_code == 200, r.text[:200]
        layers = r.json().get("layers", {})
        for i in range(1, 15):
            keys = [k for k in layers if k.startswith(f"L{i}_")]
            assert keys, f"L{i}_* not present in layers; got {list(layers.keys())}"
            v = layers[keys[0]]
            assert v and isinstance(v, str) and len(v) > 0, f"{keys[0]} is empty/non-string: {v}"


# ════════════════════════════════════════════════════════════════
# Regression — core endpoints still work with clean UA + fresh IP
# ════════════════════════════════════════════════════════════════
class TestRegression:
    def test_login_me_projects_with_fresh_ip(self):
        ip = "99.99.99.99"
        h_ip = {"X-Forwarded-For": ip, "User-Agent": CLEAN_UA}
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers=h_ip, timeout=15,
        )
        assert r.status_code == 200, r.text[:200]
        tok = r.json()["token"]
        h = {"Authorization": f"Bearer {tok}", **h_ip}

        me = requests.get(f"{BASE_URL}/api/auth/me", headers=h, timeout=10)
        assert me.status_code == 200, me.text[:200]
        assert me.json().get("email") == ADMIN_EMAIL

        gp = requests.get(f"{BASE_URL}/api/games/projects", headers=h, timeout=15)
        # 200 with list expected
        assert gp.status_code == 200, gp.text[:200]
        assert isinstance(gp.json(), (list, dict)), f"unexpected body type: {type(gp.json())}"


# ════════════════════════════════════════════════════════════════
# L2 — Security headers still present
# ════════════════════════════════════════════════════════════════
class TestSecurityHeaders:
    def test_headers_present(self):
        ip = "98.98.98.98"
        r = requests.get(
            f"{BASE_URL}/api/games/projects",
            headers={"X-Forwarded-For": ip, "User-Agent": CLEAN_UA},
            timeout=10,
        )
        h = {k.lower(): v for k, v in r.headers.items()}
        assert "strict-transport-security" in h, f"HSTS missing; headers: {list(h.keys())}"
        assert h.get("x-frame-options", "").upper() == "DENY", f"X-Frame-Options: {h.get('x-frame-options')}"
        assert h.get("x-content-type-options", "").lower() == "nosniff", f"X-Content-Type-Options: {h.get('x-content-type-options')}"
        assert "content-security-policy" in h, "CSP missing"
