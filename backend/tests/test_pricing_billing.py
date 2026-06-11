"""
Backend tests for Zenrex Pricing & Billing system (iteration_35).

Covers:
- Public catalog endpoints: /api/pricing/plans, /packs, /tax-config, /service-costs
- Promo validation: LAUNCH50 valid, max cap, invalid code, WELCOME25 scope
- Authenticated user endpoints: /me, /invoices, /checkout (subscription + pack)
- Admin endpoints: /stats, /orders, /promos (GET+POST), /test-paypal
- Auth guards: 401 unauth, 403 non-admin
- PDF generation via reportlab on mock invoice
- Regression: /api/auth/login, /api/auth/me, /api/admin/security/status
"""
import os
import uuid
import pytest
import requests

def _load_base_url():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        # fall back to frontend/.env
        try:
            with open("/app/frontend/.env") as fp:
                for line in fp:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    assert url, "REACT_APP_BACKEND_URL not configured"
    return url.rstrip("/")


BASE_URL = _load_base_url()
ADMIN_EMAIL = "owner@zenrex.ai"
ADMIN_PASSWORD = "owner123"


# ───────────────────── Fixtures ─────────────────────
@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                      timeout=20)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    return r.json()["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def fresh_user():
    """Register a brand new client user to test first-purchase bonus + promo flows."""
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_pricing_{suffix}@example.com"
    password = "Passw0rd123"
    payload = {"email": email, "password": password, "name": "Pricing Test",
               "country": "SA", "gender": "male"}
    r = requests.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=20)
    if r.status_code not in (200, 201):
        pytest.skip(f"User register failed: {r.status_code} {r.text[:200]}")
    # login
    r2 = requests.post(f"{BASE_URL}/api/auth/login",
                       json={"email": email, "password": password}, timeout=20)
    assert r2.status_code == 200, r2.text
    return {"email": email, "token": r2.json()["token"]}


@pytest.fixture(scope="session")
def user_headers(fresh_user):
    return {"Authorization": f"Bearer {fresh_user['token']}", "Content-Type": "application/json"}


# ───────────────────── Public catalog ─────────────────────
class TestCatalog:
    def test_plans(self):
        r = requests.get(f"{BASE_URL}/api/pricing/plans", timeout=15)
        assert r.status_code == 200, r.text
        plans = r.json()["plans"]
        ids = {p["id"] for p in plans}
        expected = {"free", "starter", "indie", "studio", "pro_studio", "enterprise"}
        assert expected.issubset(ids), f"Missing plan ids. Got: {ids}"
        # prices
        by_id = {p["id"]: p for p in plans}
        assert by_id["free"]["price_monthly_usd"] == 0
        assert by_id["starter"]["price_monthly_usd"] == 9
        assert by_id["indie"]["price_monthly_usd"] == 29
        assert by_id["studio"]["price_monthly_usd"] == 79
        assert by_id["pro_studio"]["price_monthly_usd"] == 199
        # arabic name present
        assert by_id["indie"].get("name_ar") == "المبدع المستقل"

    def test_packs(self):
        r = requests.get(f"{BASE_URL}/api/pricing/packs", timeout=15)
        assert r.status_code == 200
        packs = r.json()["packs"]
        ids = {p["id"] for p in packs}
        expected = {"pack_mini", "pack_standard", "pack_power", "pack_mega", "pack_ultra"}
        assert expected.issubset(ids), f"Missing pack ids: {ids}"
        for p in packs:
            assert "bonus_pct" in p, f"pack {p['id']} missing bonus_pct"

    def test_service_costs(self):
        r = requests.get(f"{BASE_URL}/api/pricing/service-costs", timeout=15)
        assert r.status_code == 200
        items = r.json()["items"]
        assert isinstance(items, dict) and len(items) > 0
        # must include some core entries
        for key in ["text_gpt4o_1k", "image_nano_banana", "video_fal_5s"]:
            assert key in items, f"missing {key}"
            assert "credits" in items[key]

    def test_tax_config(self):
        r = requests.get(f"{BASE_URL}/api/pricing/tax-config", timeout=15)
        assert r.status_code == 200
        cfg = r.json()
        assert cfg.get("enabled") is True
        assert cfg.get("rate_percent") == 0
        assert cfg.get("label") == "ضريبة القيمة المضافة"


# ───────────────────── Promo validation ─────────────────────
class TestPromos:
    def test_launch50_valid_subscription(self, user_headers):
        r = requests.post(f"{BASE_URL}/api/pricing/promo/check", headers=user_headers,
                          json={"code": "LAUNCH50", "item_type": "subscription", "base_amount_usd": 29},
                          timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("valid") is True, d
        assert abs(d.get("discount_usd", 0) - 14.5) < 0.01
        assert abs(d.get("final_usd", 0) - 14.5) < 0.01

    def test_launch50_max_cap(self, user_headers):
        r = requests.post(f"{BASE_URL}/api/pricing/promo/check", headers=user_headers,
                          json={"code": "LAUNCH50", "item_type": "subscription", "base_amount_usd": 300},
                          timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("valid") is True
        # 50% of 300 = 150, capped at 100
        assert abs(d.get("discount_usd", 0) - 100) < 0.01, d
        assert abs(d.get("final_usd", 0) - 200) < 0.01

    def test_invalid_code(self, user_headers):
        r = requests.post(f"{BASE_URL}/api/pricing/promo/check", headers=user_headers,
                          json={"code": "NOPE", "item_type": "subscription", "base_amount_usd": 29},
                          timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("valid") is False
        # arabic error message
        msg = d.get("message", "")
        assert any(ord(c) > 127 for c in msg), f"expected arabic message, got: {msg}"

    def test_welcome25_wrong_scope(self, user_headers):
        r = requests.post(f"{BASE_URL}/api/pricing/promo/check", headers=user_headers,
                          json={"code": "WELCOME25", "item_type": "subscription", "base_amount_usd": 29},
                          timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("valid") is False, d


# ───────────────────── User-side billing ─────────────────────
class TestUserBilling:
    def test_me(self, user_headers):
        r = requests.get(f"{BASE_URL}/api/pricing/me", headers=user_headers, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "balance" in d
        # may not include sub for fresh user, but structure should not crash

    def test_invoices_empty(self, user_headers):
        r = requests.get(f"{BASE_URL}/api/pricing/invoices", headers=user_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "invoices" in d
        assert isinstance(d["invoices"], list)

    def test_checkout_subscription_with_launch50(self, user_headers):
        body = {
            "item_type": "subscription",
            "item_id": "indie",
            "billing_cycle": "monthly",
            "promo_code": "LAUNCH50",
            "return_url": "https://zenrex.ai/billing/return",
            "cancel_url": "https://zenrex.ai/billing/cancel",
        }
        r = requests.post(f"{BASE_URL}/api/pricing/checkout", headers=user_headers,
                          json=body, timeout=45)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "order_id" in d and d["order_id"]
        assert "approval_url" in d and "paypal.com" in d["approval_url"], d["approval_url"]
        assert abs(d["total_usd"] - 14.5) < 0.01
        assert d["credits_to_add"] == 50000
        # first purchase bonus pct should be 25 for fresh user
        assert d.get("first_purchase_bonus_pct") == 25, d

    def test_checkout_pack_power(self, user_headers):
        # New fresh checkout on a credit pack — no promo (LAUNCH50 already used once)
        body = {
            "item_type": "pack",
            "item_id": "pack_power",
            "billing_cycle": "monthly",
            "return_url": "https://zenrex.ai/billing/return",
            "cancel_url": "https://zenrex.ai/billing/cancel",
        }
        r = requests.post(f"{BASE_URL}/api/pricing/checkout", headers=user_headers,
                          json=body, timeout=45)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total_usd"] == 50
        assert d["credits_to_add"] == 60000
        assert "paypal.com" in d["approval_url"]


# ───────────────────── Admin endpoints ─────────────────────
class TestAdmin:
    def test_stats(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/pricing/stats", headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["total_revenue_usd", "total_orders", "active_subscriptions",
                  "last_30d_revenue_usd", "promo_redemptions"]:
            assert k in d, f"missing key {k} in stats"

    def test_orders(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/pricing/orders?limit=10",
                         headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "orders" in d and isinstance(d["orders"], list)
        assert "count" in d

    def test_list_promos_defaults(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/pricing/promos",
                         headers=admin_headers, timeout=15)
        assert r.status_code == 200
        promos = r.json()["promos"]
        codes = {p["code"] for p in promos}
        assert "LAUNCH50" in codes, f"LAUNCH50 missing — found {codes}"
        assert "WELCOME25" in codes, f"WELCOME25 missing — found {codes}"

    def test_create_promo(self, admin_headers):
        code = f"TESTBLACK20_{uuid.uuid4().hex[:4].upper()}"
        body = {"code": code, "type": "percent", "value": 20, "applies_to": "all",
                "max_discount_usd": 50, "min_order_usd": 5, "active": True}
        r = requests.post(f"{BASE_URL}/api/admin/pricing/promos",
                          headers=admin_headers, json=body, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True
        # verify it appears in list
        r2 = requests.get(f"{BASE_URL}/api/admin/pricing/promos",
                          headers=admin_headers, timeout=15)
        codes = {p["code"] for p in r2.json()["promos"]}
        assert code.upper() in codes
        # cleanup — deactivate
        requests.delete(f"{BASE_URL}/api/admin/pricing/promos/{code}",
                        headers=admin_headers, timeout=15)

    def test_test_paypal(self, admin_headers):
        r = requests.post(f"{BASE_URL}/api/admin/pricing/test-paypal",
                          headers=admin_headers, timeout=45)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ok") is True, d
        assert d.get("mode") == "live", d
        assert "paypal.com" in d.get("approval_url", "")


# ───────────────────── Auth guards ─────────────────────
class TestAuthGuards:
    def test_unauth_me(self):
        r = requests.get(f"{BASE_URL}/api/pricing/me", timeout=15)
        assert r.status_code in (401, 403), r.status_code

    def test_unauth_checkout(self):
        r = requests.post(f"{BASE_URL}/api/pricing/checkout",
                          json={"item_type": "pack", "item_id": "pack_mini",
                                "return_url": "x", "cancel_url": "x"},
                          timeout=15)
        assert r.status_code in (401, 403), r.status_code

    def test_unauth_capture(self):
        r = requests.post(f"{BASE_URL}/api/pricing/capture",
                          json={"order_id": "x"}, timeout=15)
        assert r.status_code in (401, 403), r.status_code

    def test_non_admin_blocked(self, user_headers):
        # fresh_user has role=client → should be 403 on admin
        endpoints = ["/api/admin/pricing/stats",
                     "/api/admin/pricing/orders",
                     "/api/admin/pricing/promos"]
        for ep in endpoints:
            r = requests.get(f"{BASE_URL}{ep}", headers=user_headers, timeout=15)
            assert r.status_code == 403, f"{ep} expected 403 got {r.status_code}: {r.text[:160]}"


# ───────────────────── PDF generation smoke ─────────────────────
class TestPDFGeneration:
    def test_invoice_pdf_smoke(self):
        """Direct unit-style test of generate_invoice_pdf with mock dict."""
        import sys
        sys.path.insert(0, "/app/backend")
        from modules.pricing.invoices import generate_invoice_pdf
        mock_invoice = {
            "invoice_number": "INV-TEST-0001",
            "customer_name": "أحمد الزهراني",
            "customer_email": "test@example.com",
            "issued_at_display": "2026-01-01 12:00 UTC",
            "items": [{"desc": "اشتراك Indie - شهري", "qty": 1,
                       "unit_price": 29.0, "total": 29.0}],
            "subtotal_usd": 29.0,
            "discount_usd": 14.5,
            "promo_code": "LAUNCH50",
            "tax_enabled": True, "tax_rate_pct": 0,
            "tax_label": "ضريبة القيمة المضافة",
            "tax_id": "", "tax_usd": 0,
            "total_usd": 14.5,
            "credits_added": 50000, "bonus_credits": 12500,
        }
        pdf_bytes = generate_invoice_pdf(mock_invoice)
        assert isinstance(pdf_bytes, (bytes, bytearray))
        assert len(pdf_bytes) > 500
        assert pdf_bytes[:4] == b"%PDF", "Not a PDF header"


# ───────────────────── Regression ─────────────────────
class TestRegression:
    def test_login_works(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
        assert r.status_code == 200
        assert "token" in r.json()

    def test_auth_me(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text

    def test_security_status(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/security/status",
                         headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
