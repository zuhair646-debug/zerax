"""
Iteration 70 — extra regression coverage for the linear storage pricing
flow + PayPal-only payments + Lemon Squeezy removal.

Run: cd /app/backend && pytest tests/test_storage_iter70_extra.py -q
"""
import os
import requests

API = os.environ.get("REACT_APP_BACKEND_URL") or "https://ai-cinematic-hub-2.preview.emergentagent.com"


def _login_owner():
    r = requests.post(
        f"{API}/api/auth/login",
        json={"email": "owner@zerax.com", "password": "owner123"},
        timeout=15,
    )
    r.raise_for_status()
    j = r.json()
    return j.get("access_token") or j.get("token")


# ─── 1. /api/storage/plans → s100 must be highlighted ────────────────────
def test_storage_plans_s100_highlighted():
    r = requests.get(f"{API}/api/storage/plans", timeout=15)
    assert r.status_code == 200
    plans = {p["id"]: p for p in r.json()["plans"]}
    assert "s100" in plans
    assert plans["s100"]["highlight"] is True, "s100 should be most-popular"
    # All other paid plans must NOT be highlighted
    for pid, p in plans.items():
        if pid != "s100":
            assert p.get("highlight") is False, f"{pid} should not be highlighted"


# ─── 2. /api/storage/subscription works for authenticated user ───────────
def test_storage_subscription_authenticated():
    token = _login_owner()
    r = requests.get(
        f"{API}/api/storage/subscription",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    # Must always return a plan_id and quota — fallback to free if old name
    assert "plan_id" in body
    assert "plan_quota_mb" in body
    assert isinstance(body["plan_quota_mb"], (int, float))
    assert body["plan_quota_mb"] > 0
    assert "status" in body


# ─── 3. /api/storage/capture endpoint EXISTS (replaces LS webhook) ──────
def test_storage_capture_endpoint_exists():
    """The endpoint must be registered. Calling without auth must return
    401/403 (not 404). Calling with a bogus txn_ref must return 404."""
    # Without auth → 401/403
    r = requests.post(f"{API}/api/storage/capture",
                      json={"txn_ref": "bogus"}, timeout=10)
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    # With auth + bogus txn → 404 (record not found, NOT 404 route-missing)
    token = _login_owner()
    r = requests.post(
        f"{API}/api/storage/capture",
        json={"txn_ref": "nonexistent-bogus-txn-id"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    # Must return 404 (record not found) but the endpoint itself exists
    assert r.status_code == 404, f"expected 404 record-missing, got {r.status_code}: {r.text[:200]}"
    # Make sure it's a JSON detail (FastAPI), not a route-not-found wrapper
    body = r.json()
    assert "detail" in body


# ─── 4. Lemon Squeezy regression: old endpoints must NOT 500 ────────────
def test_lemonsqueezy_endpoints_dont_crash_server():
    """Old endpoints removed in Feb 2026. They may 404 (acceptable) but
    must not 500 (which would mean dead code still loaded)."""
    token = _login_owner()
    headers = {"Authorization": f"Bearer {token}"}

    # /api/payments/lemonsqueezy/create
    r1 = requests.post(
        f"{API}/api/payments/lemonsqueezy/create",
        json={"package_id": "credits_mini"},
        headers=headers,
        timeout=10,
    )
    assert r1.status_code != 500, f"lemonsqueezy/create returned 500: {r1.text[:200]}"

    # /api/storage/webhook (old LS webhook)
    r2 = requests.post(
        f"{API}/api/storage/webhook",
        json={"meta": {"custom_data": {}}},
        timeout=10,
    )
    assert r2.status_code != 500, f"storage/webhook returned 500: {r2.text[:200]}"


# ─── 5. Universal PayPal create — auth required ─────────────────────────
def test_paypal_universal_requires_auth():
    r = requests.post(
        f"{API}/api/payments/paypal/create",
        json={"pkg_id": "storage_s50", "amount_usd": 5, "meta": {}},
        timeout=10,
    )
    assert r.status_code in (401, 403)


# ─── 6. Universal PayPal create — rejects invalid amount ────────────────
def test_paypal_universal_rejects_bad_amount():
    token = _login_owner()
    # amount 0
    r = requests.post(
        f"{API}/api/payments/paypal/create",
        json={"pkg_id": "storage_s50", "amount_usd": 0, "meta": {}},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert r.status_code == 400
    # amount > 5000
    r2 = requests.post(
        f"{API}/api/payments/paypal/create",
        json={"pkg_id": "storage_s50", "amount_usd": 9999, "meta": {}},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert r2.status_code == 400


# ─── 7. /api/storage/plans contains exactly 8 plans w/ price_usd in linear schedule
def test_storage_plans_linear_price_progression():
    r = requests.get(f"{API}/api/storage/plans", timeout=15)
    plans = r.json()["plans"]
    assert len(plans) == 8
    prices = sorted([p["price_usd"] for p in plans])
    assert prices == [0, 5, 10, 15, 20, 30, 50, 100]
