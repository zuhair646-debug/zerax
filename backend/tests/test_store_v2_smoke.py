#!/usr/bin/env python3
"""
Smoke tests for Zenrex Store V2 + AI router.
Run: python3 /app/backend/tests/test_store_v2_smoke.py
"""
import os
import sys
import json
import requests

BASE = os.environ.get("ZENREX_BASE_URL", "https://ai-cinematic-hub-2.preview.emergentagent.com")
ADMIN_EMAIL = "owner@zenrex.ai"
ADMIN_PASS = "owner123"
PHONE = "0552222222"
OTP = "1234"

PASS = 0
FAIL = 0


def _ok(name: str, cond: bool, extra: str = ""):
    global PASS, FAIL
    mark = "✓" if cond else "✗"
    print(f"  {mark} {name} {extra}")
    if cond:
        PASS += 1
    else:
        FAIL += 1


def _login_admin() -> str:
    r = requests.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=10)
    if r.status_code == 200:
        return r.json().get("token") or r.json().get("access_token") or ""
    print(f"  ! admin login: {r.status_code} {r.text[:200]}")
    return ""


def _login_customer() -> str:
    requests.post(f"{BASE}/api/store/customer/request-otp", json={"phone": PHONE}, timeout=10)
    r = requests.post(f"{BASE}/api/store/customer/verify-otp", json={"phone": PHONE, "code": OTP}, timeout=10)
    if r.status_code == 200:
        return r.json().get("token", "")
    print(f"  ! customer OTP: {r.status_code} {r.text[:200]}")
    return ""


def test_health():
    print("\n[1] Health endpoints")
    for ep in ["/api/store/health", "/api/store/v2/health", "/api/ai/health", "/api/ai/rules", "/api/payments/catalog"]:
        r = requests.get(f"{BASE}{ep}", timeout=5)
        _ok(f"GET {ep}", r.status_code == 200, f"({r.status_code})")


def test_customer_wallet(cust_tok: str):
    print("\n[2] Store Credit Wallet")
    r = requests.get(f"{BASE}/api/store/v2/wallet", headers={"Authorization": f"Bearer {cust_tok}"}, timeout=10)
    _ok("GET /wallet", r.status_code == 200 and "balance" in r.json())


def test_branches(merch_tok: str):
    print("\n[3] Branches CRUD")
    r = requests.post(
        f"{BASE}/api/store/v2/branches",
        headers={"Authorization": f"Bearer {merch_tok}"},
        json={"name": "فرع الرياض - حي العليا", "address": "الرياض - العليا", "lat": 24.7136, "lng": 46.6753, "delivery_radius_km": 30, "shipping_fee": 20},
        timeout=10,
    )
    _ok("POST /branches", r.status_code in (200, 201), f"({r.status_code})")
    branch_id = r.json().get("id") if r.status_code in (200, 201) else None

    # Nearest branches with coords (Jeddah)
    r2 = requests.get(f"{BASE}/api/store/v2/branches?lat=21.4858&lng=39.1925", timeout=10)
    _ok("GET /branches?lat=&lng=", r2.status_code == 200)

    if branch_id:
        r3 = requests.delete(f"{BASE}/api/store/v2/branches/{branch_id}", headers={"Authorization": f"Bearer {merch_tok}"}, timeout=10)
        _ok("DELETE /branches/{id}", r3.status_code == 200)


def test_checkout_flow(cust_tok: str):
    print("\n[4] Checkout + Orders flow")
    # Get a product to order
    p = requests.get(f"{BASE}/api/store/products", timeout=10)
    items = p.json().get("items", [])
    if not items:
        _ok("(no products to checkout)", False)
        return
    prod = items[0]
    r = requests.post(
        f"{BASE}/api/store/v2/checkout",
        headers={"Authorization": f"Bearer {cust_tok}"},
        json={
            "items": [{"product_id": prod["id"], "qty": 1, "price": prod.get("price", 100), "name": prod.get("name", "")}],
            "shipping_address": {"city": "الرياض", "street": "حي العليا", "shipping_fee": 15},
            "payment_method": "cod",
        },
        timeout=15,
    )
    _ok("POST /checkout", r.status_code == 200, f"({r.status_code})")
    order_id = r.json().get("order", {}).get("id") if r.status_code == 200 else None

    r2 = requests.get(f"{BASE}/api/store/v2/orders", headers={"Authorization": f"Bearer {cust_tok}"}, timeout=10)
    _ok("GET /orders (customer)", r2.status_code == 200 and r2.json().get("count", 0) >= 1)

    if order_id:
        r3 = requests.get(f"{BASE}/api/store/v2/orders/{order_id}", headers={"Authorization": f"Bearer {cust_tok}"}, timeout=10)
        _ok(f"GET /orders/{order_id[:12]}…", r3.status_code == 200)


def test_subscriptions(cust_tok: str):
    print("\n[5] Subscriptions")
    p = requests.get(f"{BASE}/api/store/products", timeout=10).json().get("items", [])
    if not p:
        return
    r = requests.post(
        f"{BASE}/api/store/v2/subscriptions",
        headers={"Authorization": f"Bearer {cust_tok}"},
        json={"product_id": p[0]["id"], "qty": 2, "frequency": "monthly"},
        timeout=10,
    )
    _ok("POST /subscriptions", r.status_code == 200, f"({r.status_code})")
    sub_id = r.json().get("id") if r.status_code == 200 else None

    r2 = requests.get(f"{BASE}/api/store/v2/subscriptions", headers={"Authorization": f"Bearer {cust_tok}"}, timeout=10)
    _ok("GET /subscriptions", r2.status_code == 200)

    if sub_id:
        r3 = requests.patch(f"{BASE}/api/store/v2/subscriptions/{sub_id}?action=pause", headers={"Authorization": f"Bearer {cust_tok}"}, timeout=10)
        _ok("PATCH pause sub", r3.status_code == 200)


def test_referrals(cust_tok: str):
    print("\n[6] Referrals")
    r = requests.get(f"{BASE}/api/store/v2/referral/me", headers={"Authorization": f"Bearer {cust_tok}"}, timeout=10)
    _ok("GET /referral/me", r.status_code == 200 and r.json().get("code", "").startswith("REF"))


def test_saved_cards(cust_tok: str):
    print("\n[7] Saved Cards")
    r = requests.post(
        f"{BASE}/api/store/v2/saved-cards",
        headers={"Authorization": f"Bearer {cust_tok}"},
        json={"last4": "4242", "brand": "visa", "holder": "TEST USER", "expiry": "12/28", "gateway_token": "tok_test"},
        timeout=10,
    )
    _ok("POST /saved-cards", r.status_code == 200)
    card_id = r.json().get("id") if r.status_code == 200 else None
    r2 = requests.get(f"{BASE}/api/store/v2/saved-cards", headers={"Authorization": f"Bearer {cust_tok}"}, timeout=10)
    _ok("GET /saved-cards (no token leak)", r2.status_code == 200 and not any("gateway_token" in c for c in r2.json().get("items", [])))
    if card_id:
        r3 = requests.delete(f"{BASE}/api/store/v2/saved-cards/{card_id}", headers={"Authorization": f"Bearer {cust_tok}"}, timeout=10)
        _ok("DELETE /saved-cards/{id}", r3.status_code == 200)


def test_ai_profile(merch_tok: str):
    print("\n[8] Merchant AI Profile (onboarding)")
    r = requests.put(
        f"{BASE}/api/store/v2/merchant/ai-profile",
        headers={"Authorization": f"Bearer {merch_tok}"},
        json={"industry": "electronics", "sub_categories": ["phones", "laptops"], "target_markets": ["sa", "ae"], "brand_tone": "luxury", "photography_style": "luxury", "notes": "متجر إلكترونيات فاخر"},
        timeout=10,
    )
    _ok("PUT /merchant/ai-profile", r.status_code == 200)
    r2 = requests.get(f"{BASE}/api/store/v2/merchant/ai-profile", headers={"Authorization": f"Bearer {merch_tok}"}, timeout=10)
    _ok("GET /merchant/ai-profile", r2.status_code == 200 and r2.json().get("industry") == "electronics")


def main():
    print(f"━━━ Zenrex V2 Smoke Tests · {BASE} ━━━")
    test_health()
    merch_tok = _login_admin()
    cust_tok = _login_customer()
    if not merch_tok or not cust_tok:
        print("\n⚠ Could not log in. Skipping authed tests.")
        sys.exit(1)
    test_customer_wallet(cust_tok)
    test_branches(merch_tok)
    test_checkout_flow(cust_tok)
    test_subscriptions(cust_tok)
    test_referrals(cust_tok)
    test_saved_cards(cust_tok)
    test_ai_profile(merch_tok)
    total = PASS + FAIL
    print(f"\n━━━ Result: {PASS}/{total} passed · {FAIL} failed ━━━")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
