"""HTTP smoke tests for /api/admin/ai-mode (Iteration 3).

Covers:
  • GET default (claude_only) + valid_modes
  • PUT → hybrid → persists across GET
  • PUT invalid mode → 400
  • PUT without auth → 401/403
  • GET with non-admin user token → 403
  • Reset to claude_only at end (test isolation)

Note: admin@zenrex.ai/Zenrex@2026 is not seeded in this local/preview env
(per /app/memory/test_credentials.md). We use owner@zerax.com/owner123
which has role="owner" and passes require_admin.
"""
from __future__ import annotations
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-cinematic-hub-2.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

OWNER_EMAIL = "owner@zerax.com"
OWNER_PASS = "owner123"


@pytest.fixture(scope="module")
def owner_token() -> str:
    last_err = None
    for _ in range(3):
        try:
            r = requests.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASS}, timeout=45)
            break
        except requests.exceptions.RequestException as e:
            last_err = e
            time.sleep(2)
    else:
        pytest.skip(f"Backend unreachable after retries: {last_err}")
    assert r.status_code == 200, f"Owner login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    tok = data.get("token") or data.get("access_token")
    assert isinstance(tok, str) and len(tok) > 100, f"Token too short or missing: {tok!r}"
    return tok


@pytest.fixture(scope="module")
def owner_headers(owner_token: str) -> dict:
    return {"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def non_admin_token() -> str:
    """Register & login a fresh non-admin user. Returns its token."""
    email = f"TEST_nonadmin_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass123!"
    reg = requests.post(
        f"{API}/auth/register",
        json={"email": email, "password": password, "name": "Non Admin Test"},
        timeout=45,
    )
    if reg.status_code not in (200, 201):
        pytest.skip(f"Cannot register non-admin test user: {reg.status_code} {reg.text[:200]}")
    # Some impls return token directly on register, others require login.
    body = reg.json()
    tok = body.get("token") or body.get("access_token")
    if not tok:
        log = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=45)
        if log.status_code != 200:
            pytest.skip(f"Non-admin login after register failed: {log.status_code}")
        tok = log.json().get("token")
    assert isinstance(tok, str) and len(tok) > 50, "Non-admin token invalid"
    return tok


# ────────────────────────────────────────────────────────────────────────────
# 1. Owner can read the AI mode and sees valid_modes
# ────────────────────────────────────────────────────────────────────────────
def test_get_ai_mode_returns_mode_and_valid_modes(owner_headers):
    r = requests.get(f"{API}/admin/ai-mode", headers=owner_headers, timeout=45)
    assert r.status_code == 200, f"GET failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    assert "mode" in data
    assert data["mode"] in {"claude_only", "hybrid_gpt", "hybrid_glm"}
    assert "valid_modes" in data
    assert sorted(data["valid_modes"]) == ["claude_only", "hybrid_glm", "hybrid_gpt"]


# ────────────────────────────────────────────────────────────────────────────
# 2. PUT → hybrid, then GET reflects persistence
# ────────────────────────────────────────────────────────────────────────────
def test_put_ai_mode_hybrid_then_get_persists(owner_headers):
    put = requests.put(
        f"{API}/admin/ai-mode",
        headers=owner_headers,
        json={"mode": "hybrid_gpt"},
        timeout=45,
    )
    assert put.status_code == 200, f"PUT hybrid_gpt failed: {put.status_code} {put.text[:200]}"
    body = put.json()
    assert body.get("ok") is True
    assert body.get("mode") == "hybrid_gpt"

    # Small sleep to allow any eventual-consistency (single-node Mongo so 0 is fine)
    time.sleep(0.2)

    get = requests.get(f"{API}/admin/ai-mode", headers=owner_headers, timeout=45)
    assert get.status_code == 200
    assert get.json().get("mode") == "hybrid_gpt", "Persistence failed: GET did not return 'hybrid_gpt'"


# ────────────────────────────────────────────────────────────────────────────
# 3. PUT invalid mode → 400 with a clear error
# ────────────────────────────────────────────────────────────────────────────
def test_put_ai_mode_invalid_returns_400(owner_headers):
    r = requests.put(
        f"{API}/admin/ai-mode",
        headers=owner_headers,
        json={"mode": "foobar"},
        timeout=45,
    )
    assert r.status_code == 400, f"Expected 400 for invalid mode, got {r.status_code} {r.text[:200]}"
    body = r.json()
    detail = body.get("detail") or body.get("message") or ""
    assert "mode" in str(detail).lower()


# ────────────────────────────────────────────────────────────────────────────
# 4. PUT WITHOUT auth → 401 or 403
# ────────────────────────────────────────────────────────────────────────────
def test_put_ai_mode_no_auth_returns_401_or_403():
    r = requests.put(
        f"{API}/admin/ai-mode",
        headers={"Content-Type": "application/json"},
        json={"mode": "hybrid"},
        timeout=45,
    )
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code} {r.text[:200]}"


# ────────────────────────────────────────────────────────────────────────────
# 5. GET WITHOUT auth → 401 or 403
# ────────────────────────────────────────────────────────────────────────────
def test_get_ai_mode_no_auth_returns_401_or_403():
    r = requests.get(f"{API}/admin/ai-mode", timeout=45)
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code} {r.text[:200]}"


# ────────────────────────────────────────────────────────────────────────────
# 6. Non-admin user → 403
# ────────────────────────────────────────────────────────────────────────────
def test_get_ai_mode_non_admin_returns_403(non_admin_token):
    headers = {"Authorization": f"Bearer {non_admin_token}", "Content-Type": "application/json"}
    r = requests.get(f"{API}/admin/ai-mode", headers=headers, timeout=45)
    assert r.status_code == 403, f"Expected 403 for non-admin, got {r.status_code} {r.text[:200]}"


def test_put_ai_mode_non_admin_returns_403(non_admin_token):
    headers = {"Authorization": f"Bearer {non_admin_token}", "Content-Type": "application/json"}
    r = requests.put(f"{API}/admin/ai-mode", headers=headers, json={"mode": "hybrid"}, timeout=45)
    assert r.status_code == 403, f"Expected 403 for non-admin PUT, got {r.status_code} {r.text[:200]}"


# ────────────────────────────────────────────────────────────────────────────
# 7. Reset back to claude_only so other tests / runtime stay on default
# ────────────────────────────────────────────────────────────────────────────
def test_zz_reset_to_claude_only(owner_headers):
    r = requests.put(
        f"{API}/admin/ai-mode",
        headers=owner_headers,
        json={"mode": "claude_only"},
        timeout=45,
    )
    assert r.status_code == 200
    assert r.json().get("mode") == "claude_only"

    g = requests.get(f"{API}/admin/ai-mode", headers=owner_headers, timeout=45)
    assert g.status_code == 200
    assert g.json().get("mode") == "claude_only"
