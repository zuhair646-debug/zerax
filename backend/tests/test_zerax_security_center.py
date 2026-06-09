"""
Test the 10-layer Zerax Security Center.

Coverage:
- L2 security headers on responses
- L3 brute-force lockout via /api/auth/login (5 fails → 429/403)
- L4 audit log writes (login_success, login_failed)
- L7 IP blocklist + unblock endpoint
- Admin /api/admin/security/{status,scan-now,backup-now,unblock-ip,unlock-account,audit-log}
- Non-admin (no token) gets 401/403 on /api/admin/security/*
- Regression: /api/auth/login, /api/auth/me, /api/games/projects still work
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to read from frontend .env (CI safety only)
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.strip().split("=", 1)[1].rstrip("/")

ADMIN_EMAIL = "owner@zerax.com"
ADMIN_PASSWORD = "owner123"

# Use a fresh forwarded IP for brute-force test so we don't lock the runner itself
BRUTE_IP = f"9.9.{int(time.time()) % 250}.{(int(time.time()) // 250) % 250}"
BRUTE_USER = f"bf-{uuid.uuid4().hex[:8]}@example.com"


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(session):
    r = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=20,
    )
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    assert "token" in data
    return data["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ──────────────────────────────────────────────────────────────
# L2 — security headers
# ──────────────────────────────────────────────────────────────
class TestSecurityHeaders:
    def test_security_headers_present(self, session):
        r = session.get(f"{BASE_URL}/api/", timeout=15)
        assert r.status_code in (200, 404), r.text[:200]
        h = {k.lower(): v for k, v in r.headers.items()}
        assert "strict-transport-security" in h, f"HSTS missing. headers={list(h.keys())}"
        assert h.get("x-frame-options", "").upper() == "DENY"
        assert "nosniff" in h.get("x-content-type-options", "").lower()
        assert "content-security-policy" in h


# ──────────────────────────────────────────────────────────────
# Admin auth flow + status
# ──────────────────────────────────────────────────────────────
class TestAdminStatus:
    def test_login_success(self, session):
        r = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=20,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["user"]["email"] == ADMIN_EMAIL
        assert isinstance(data["token"], str) and len(data["token"]) > 10

    def test_auth_me_regression(self, session, admin_headers):
        r = session.get(f"{BASE_URL}/api/auth/me", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        assert r.json().get("email") == ADMIN_EMAIL

    def test_status_endpoint_full_shape(self, session, admin_headers):
        r = session.get(
            f"{BASE_URL}/api/admin/security/status", headers=admin_headers, timeout=20
        )
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data.get("ok") is True
        assert "overall_status" in data
        layers = data.get("layers", {})
        for i in range(1, 11):
            keys = [k for k in layers if k.startswith(f"L{i}_")]
            assert keys, f"layer L{i} missing in status. got={list(layers.keys())}"
        assert "counters" in data
        assert "last_ai_audit" in data
        assert "backups" in data
        assert "recent_alerts" in data
        assert isinstance(data["recent_alerts"], list)

    def test_non_admin_blocked(self, session):
        r = session.get(f"{BASE_URL}/api/admin/security/status", timeout=15)
        # No auth header at all → expect 401/403
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"

    def test_non_admin_blocked_audit(self, session):
        r = session.get(f"{BASE_URL}/api/admin/security/audit-log", timeout=15)
        assert r.status_code in (401, 403)


# ──────────────────────────────────────────────────────────────
# L4 — audit log (login_failed + login_success)
# ──────────────────────────────────────────────────────────────
class TestAuditLog:
    def test_login_failed_writes_audit(self, session, admin_headers):
        bogus = f"audit-test-{uuid.uuid4().hex[:6]}@example.com"
        r = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": bogus, "password": "wrong"},
            headers={"X-Forwarded-For": f"5.5.5.{int(time.time()) % 250}"},
            timeout=15,
        )
        assert r.status_code == 401
        time.sleep(1)  # let audit write
        log = session.get(
            f"{BASE_URL}/api/admin/security/audit-log?limit=200",
            headers=admin_headers,
            timeout=15,
        )
        assert log.status_code == 200
        rows = log.json().get("log", [])
        match = [
            x for x in rows
            if x.get("kind") == "login_failed" and x.get("actor") == bogus
        ]
        assert match, f"login_failed audit for {bogus} not found in last 200 logs"
        assert match[0].get("details", {}).get("reason") == "bad_credentials"

    def test_login_success_writes_audit(self, session, admin_headers):
        # Re-login owner with a unique forwarded IP so audit is fresh
        ip = f"7.7.7.{int(time.time()) % 250}"
        r = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            headers={"X-Forwarded-For": ip},
            timeout=15,
        )
        assert r.status_code == 200
        time.sleep(1)
        log = session.get(
            f"{BASE_URL}/api/admin/security/audit-log?limit=200",
            headers=admin_headers,
            timeout=15,
        )
        rows = log.json().get("log", [])
        match = [
            x for x in rows
            if x.get("kind") == "login_success" and x.get("actor") == ADMIN_EMAIL
        ]
        assert match, "login_success audit for owner not found"


# ──────────────────────────────────────────────────────────────
# L3 + L7 — brute-force lockout + IP block + cleanup
# ──────────────────────────────────────────────────────────────
class TestBruteForce:
    def test_brute_force_triggers_lockout_and_alert(self, session, admin_headers):
        # Send 5 failed attempts for SAME email from SAME forwarded IP
        statuses = []
        for i in range(5):
            r = session.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": BRUTE_USER, "password": "wrong-pass-x"},
                headers={"X-Forwarded-For": BRUTE_IP},
                timeout=15,
            )
            statuses.append(r.status_code)
        # First 5 attempts should return 401 (bad creds)
        assert all(s in (401, 429) for s in statuses), f"unexpected statuses: {statuses}"

        # 6th attempt → expect 429 (lockout) OR 403 (IP block)
        r6 = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": BRUTE_USER, "password": "wrong-pass-x"},
            headers={"X-Forwarded-For": BRUTE_IP},
            timeout=15,
        )
        assert r6.status_code in (429, 403), (
            f"6th attempt expected 429/403, got {r6.status_code}: {r6.text[:200]}"
        )

        # Status endpoint should contain a BRUTE_FORCE high-severity alert
        time.sleep(1)
        st = session.get(
            f"{BASE_URL}/api/admin/security/status",
            headers=admin_headers,
            timeout=15,
        )
        assert st.status_code == 200
        alerts = st.json().get("recent_alerts", [])
        bf_alerts = [a for a in alerts if a.get("kind") == "BRUTE_FORCE"]
        assert bf_alerts, f"BRUTE_FORCE alert not found. alerts={alerts}"
        assert bf_alerts[0].get("severity") in ("high", "critical")
        assert st.json()["counters"]["ips_blocked"] >= 1

    def test_unblock_and_unlock_cleanup(self, session, admin_headers):
        """CRITICAL cleanup so we don't lock ourselves out."""
        ub = session.post(
            f"{BASE_URL}/api/admin/security/unblock-ip",
            params={"ip": BRUTE_IP},
            headers=admin_headers,
            timeout=15,
        )
        assert ub.status_code == 200
        assert ub.json().get("unblocked") == BRUTE_IP

        ul = session.post(
            f"{BASE_URL}/api/admin/security/unlock-account",
            params={"ip": BRUTE_IP, "username": BRUTE_USER},
            headers=admin_headers,
            timeout=15,
        )
        assert ul.status_code == 200
        assert ul.json().get("ok") is True

        # After cleanup, a NEW failed attempt from same IP should be 401 (not 403/429)
        r = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": BRUTE_USER, "password": "wrong"},
            headers={"X-Forwarded-For": BRUTE_IP},
            timeout=15,
        )
        assert r.status_code == 401, (
            f"After unblock/unlock expected 401, got {r.status_code}: {r.text[:200]}"
        )


# ──────────────────────────────────────────────────────────────
# scan-now + backup-now
# ──────────────────────────────────────────────────────────────
class TestAdminActions:
    def test_scan_now_returns_verdict(self, session, admin_headers):
        r = session.post(
            f"{BASE_URL}/api/admin/security/scan-now",
            headers=admin_headers,
            timeout=90,  # AI call may take time
        )
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "verdict" in data
        # Verdict can be CLEAR/ELEVATED/ATTACK_IN_PROGRESS/UNKNOWN/NO_AI_KEY/AUDIT_ERROR
        assert data["verdict"] in (
            "CLEAR", "ELEVATED", "ATTACK_IN_PROGRESS",
            "UNKNOWN", "NO_AI_KEY", "AUDIT_ERROR",
        )
        assert "scanned_at" in data

    def test_backup_now_creates_snapshot(self, session, admin_headers):
        r = session.post(
            f"{BASE_URL}/api/admin/security/backup-now",
            headers=admin_headers,
            timeout=60,
        )
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data.get("ok") is True
        assert "timestamp" in data
        assert "collections" in data
        assert isinstance(data["collections"], dict)
        # Status should reflect at least 1 backup
        st = session.get(
            f"{BASE_URL}/api/admin/security/status",
            headers=admin_headers,
            timeout=15,
        )
        assert len(st.json().get("backups", [])) >= 1


# ──────────────────────────────────────────────────────────────
# Regression: existing endpoints still work
# ──────────────────────────────────────────────────────────────
class TestRegression:
    def test_games_projects_works(self, session, admin_headers):
        r = session.get(
            f"{BASE_URL}/api/games/projects",
            headers=admin_headers,
            timeout=20,
        )
        # Endpoint may return list or dict; just ensure not 5xx and not 403
        assert r.status_code < 500, f"5xx from /api/games/projects: {r.status_code} {r.text[:200]}"
        assert r.status_code != 403, "regression: admin blocked from games endpoint"
