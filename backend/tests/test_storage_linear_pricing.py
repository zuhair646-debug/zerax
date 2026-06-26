"""
Regression test for the linear storage pricing tiers + PayPal-only flow.

Run:  cd /app/backend && pytest tests/test_storage_linear_pricing.py -q
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


# ─── Linear pricing schedule (must mirror STORAGE_PLANS) ──────────────────
EXPECTED_TIERS = [
    ("free",  10,     0),
    ("s50",   50,     5),
    ("s100",  100,   10),
    ("s150",  150,   15),
    ("s200",  200,   20),
    ("s300",  300,   30),
    ("s500",  500,   50),
    ("s1000", 1024, 100),
]


def test_storage_plans_are_linear():
    r = requests.get(f"{API}/api/storage/plans", timeout=30)
    r.raise_for_status()
    data = r.json()
    plans = {p["id"]: p for p in data["plans"]}
    assert set(plans.keys()) == {t[0] for t in EXPECTED_TIERS}
    for pid, quota, price in EXPECTED_TIERS:
        assert plans[pid]["quota_mb"] == quota, f"{pid} quota mismatch"
        assert plans[pid]["price_usd"] == price, f"{pid} price mismatch"


def test_paypal_universal_endpoint_works():
    """The /api/payments/paypal/create endpoint must register (regression for
    the NameError on UniversalCreateIn). Returns 200 with approval_url for
    an authenticated user."""
    token = _login_owner()
    r = requests.post(
        f"{API}/api/payments/paypal/create",
        json={"pkg_id": "storage_s50", "amount_usd": 5, "meta": {"plan_id": "s50"}},
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text[:200]}"
    body = r.json()
    assert "approval_url" in body and body["approval_url"].startswith("https://www.paypal.com")
    assert body["pkg_id"] == "storage_s50"
    assert body["amount_usd"] == 5.0


def test_storage_checkout_uses_paypal():
    """Storage subscription checkout must return a PayPal approval URL —
    Lemon Squeezy was removed in Feb 2026."""
    token = _login_owner()
    r = requests.post(
        f"{API}/api/storage/checkout",
        json={"plan_id": "s100"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert body["method"] == "paypal"
    assert body["checkout_url"].startswith("https://www.paypal.com")
    assert "txn_ref" in body


def test_free_plan_downgrade_is_idempotent():
    token = _login_owner()
    r = requests.post(
        f"{API}/api/storage/checkout",
        json={"plan_id": "free"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    assert r.status_code == 200
    assert r.json().get("downgraded_to") == "free"
