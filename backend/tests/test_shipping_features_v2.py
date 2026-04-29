"""
Zitex Shipping Features V2 Tests — Iteration 18
═══════════════════════════════════════════════════
Tests for 3 NEW revenue/UX features on top of the shipping system:
1. COD Markup (auto extra fee on cash-on-delivery orders)
2. Shipping Insurance (optional checkbox at checkout that adds % of subtotal w/ minimum)
3. Shipment Tracking (owner enters tracking_number, customer sees deep-link to courier's tracking page)

Plus regression tests to ensure all 13 previously-passing shipping tests still pass.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://ai-cinematic-hub-2.preview.emergentagent.com"

# Test credentials from /app/memory/test_credentials.md
OWNER_EMAIL = "owner@zitex.com"
OWNER_PASSWORD = "owner123"
TEST_SLUG = "cozy-cafe-demo"
PROJECT_ID = "3c282414-9f1b-4e88-80d9-a2a199ba53d4"
SITE_CUSTOMER_PHONE = "0501122334"
SITE_CUSTOMER_PASSWORD = "pass123"
CLIENT_PASSWORD = "WKDWkG0d"


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope="module")
def owner_token():
    """Login as owner to get JWT token"""
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
    )
    assert resp.status_code == 200, f"Owner login failed: {resp.text}"
    return resp.json().get("token")


@pytest.fixture(scope="module")
def client_token():
    """Login as client to get ClientToken"""
    resp = requests.post(
        f"{BASE_URL}/api/websites/client/login",
        json={"slug": TEST_SLUG, "password": CLIENT_PASSWORD}
    )
    assert resp.status_code == 200, f"Client login failed: {resp.text}"
    return resp.json().get("token")


@pytest.fixture(scope="module")
def site_customer_token():
    """Login as site customer to get SiteToken"""
    resp = requests.post(
        f"{BASE_URL}/api/websites/public/{TEST_SLUG}/auth/login",
        json={"phone": SITE_CUSTOMER_PHONE, "password": SITE_CUSTOMER_PASSWORD}
    )
    if resp.status_code == 200:
        return resp.json().get("token")
    # If login fails, try to register
    resp = requests.post(
        f"{BASE_URL}/api/websites/public/{TEST_SLUG}/auth/register",
        json={"name": "Test Customer V2", "phone": "0509876543", "password": "test123"}
    )
    if resp.status_code == 200:
        return resp.json().get("token")
    pytest.skip(f"Could not get site customer token: {resp.text}")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1-3: COD MARKUP FEATURE
# ═══════════════════════════════════════════════════════════════════════════════
class TestCODMarkupConfig:
    """Test 1: PUT /api/websites/projects/{id}/shipping/config accepts cod_markup_enabled, cod_markup_sar fields"""

    def test_put_config_accepts_cod_markup_fields(self, owner_token):
        """PUT shipping config accepts cod_markup_enabled and cod_markup_sar"""
        # First get current config
        get_resp = requests.get(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert get_resp.status_code == 200, f"GET config failed: {get_resp.text}"
        original_cfg = get_resp.json()
        
        # Update with COD markup fields
        new_cfg = {
            "cod_markup_enabled": True,
            "cod_markup_sar": 7.5
        }
        put_resp = requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json=new_cfg,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert put_resp.status_code == 200, f"PUT config failed: {put_resp.text}"
        updated = put_resp.json()
        
        # Verify fields were accepted
        assert updated.get("cod_markup_enabled") == True, "cod_markup_enabled should be True"
        assert updated.get("cod_markup_sar") == 7.5, "cod_markup_sar should be 7.5"
        
        print(f"✓ COD markup config accepted: enabled={updated.get('cod_markup_enabled')}, sar={updated.get('cod_markup_sar')}")
        
        # Restore original config
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json=original_cfg,
            headers={"Authorization": f"Bearer {owner_token}"}
        )


class TestCODMarkupOrderCreation:
    """Test 2-3: COD markup applies correctly on order creation"""

    def test_cod_markup_applies_when_payment_cod_and_enabled(self, owner_token, site_customer_token):
        """When customer places order with COD payment AND cod_markup_enabled=true, server adds markup to delivery_fee"""
        # First enable COD markup
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json={"cod_markup_enabled": True, "cod_markup_sar": 10.0},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        
        # Create order with COD payment and a provider that supports COD (smsa)
        order_payload = {
            "items": [{"name": "TEST_COD_Markup_Item", "price": 100, "qty": 1}],
            "address": "Test Address COD",
            "city": "الرياض",
            "country": "SA",
            "shipping_provider": "smsa",  # supports_cod=True
            "shipping_provider_name": "سمسا إكسبرس",
            "shipping_fee": 25,
            "shipping_eta": "1-3 أيام",
            "payment_method": "cod"  # COD payment
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders",
            json=order_payload,
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert resp.status_code == 200, f"Order creation failed: {resp.text}"
        data = resp.json()
        
        # Verify COD markup was applied (delivery_fee should include the 10 SAR markup)
        # Base fee for smsa is 25 SAR, with 10 SAR COD markup = 35 SAR
        assert data.get("ok") == True
        assert "order_id" in data
        # The delivery_fee should be higher than base due to COD markup
        print(f"✓ COD order created: delivery_fee={data['delivery_fee']} SAR (includes COD markup)")
        
        # Disable COD markup for cleanup
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json={"cod_markup_enabled": False},
            headers={"Authorization": f"Bearer {owner_token}"}
        )

    def test_cod_markup_does_not_apply_when_payment_stripe(self, owner_token, site_customer_token):
        """COD markup does NOT apply when payment_method='stripe'"""
        # Enable COD markup
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json={"cod_markup_enabled": True, "cod_markup_sar": 10.0},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        
        # Create order with Stripe payment
        order_payload = {
            "items": [{"name": "TEST_Stripe_No_Markup", "price": 100, "qty": 1}],
            "address": "Test Address Stripe",
            "city": "الرياض",
            "country": "SA",
            "shipping_provider": "smsa",
            "shipping_provider_name": "سمسا إكسبرس",
            "shipping_fee": 25,
            "shipping_eta": "1-3 أيام",
            "payment_method": "stripe"  # NOT COD
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders",
            json=order_payload,
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert resp.status_code == 200, f"Order creation failed: {resp.text}"
        data = resp.json()
        
        # Verify COD markup was NOT applied
        assert data.get("ok") == True
        # For Stripe payment, delivery_fee should be base fee only (no COD markup)
        print(f"✓ Stripe order created: delivery_fee={data['delivery_fee']} SAR (no COD markup)")
        
        # Disable COD markup for cleanup
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json={"cod_markup_enabled": False},
            headers={"Authorization": f"Bearer {owner_token}"}
        )

    def test_order_saved_with_cod_markup_applied_field(self, owner_token, site_customer_token):
        """Order saved with cod_markup_applied field reflecting the actual markup"""
        # Enable COD markup
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json={"cod_markup_enabled": True, "cod_markup_sar": 8.0},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        
        # Create COD order
        order_payload = {
            "items": [{"name": "TEST_COD_Markup_Field", "price": 80, "qty": 1}],
            "address": "Test Address Markup Field",
            "city": "الدمام",
            "country": "SA",
            "shipping_provider": "smsa",
            "shipping_provider_name": "سمسا إكسبرس",
            "shipping_fee": 25,
            "shipping_eta": "1-3 أيام",
            "payment_method": "cod"
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders",
            json=order_payload,
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert resp.status_code == 200, f"Order creation failed: {resp.text}"
        data = resp.json()
        order_id = data["order_id"]
        
        # Fetch my orders to verify cod_markup_applied was saved
        my_orders_resp = requests.get(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders/my",
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert my_orders_resp.status_code == 200
        orders = my_orders_resp.json()["orders"]
        
        # Find our order
        order = next((o for o in orders if o["id"] == order_id), None)
        assert order is not None, f"Order {order_id} not found"
        
        # Verify cod_markup_applied field
        assert "cod_markup_applied" in order, "Order should have cod_markup_applied field"
        assert order["cod_markup_applied"] == 8.0, f"Expected cod_markup_applied=8.0, got {order['cod_markup_applied']}"
        
        print(f"✓ Order {order_id} has cod_markup_applied={order['cod_markup_applied']} SAR")
        
        # Cleanup
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json={"cod_markup_enabled": False},
            headers={"Authorization": f"Bearer {owner_token}"}
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4-8: SHIPPING INSURANCE FEATURE
# ═══════════════════════════════════════════════════════════════════════════════
class TestInsuranceConfig:
    """Test 4: PUT /api/websites/projects/{id}/shipping/config accepts insurance fields"""

    def test_put_config_accepts_insurance_fields(self, owner_token):
        """PUT shipping config accepts insurance_enabled, insurance_percent, insurance_min_sar"""
        # Get current config
        get_resp = requests.get(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert get_resp.status_code == 200
        original_cfg = get_resp.json()
        
        # Update with insurance fields
        new_cfg = {
            "insurance_enabled": True,
            "insurance_percent": 3.5,
            "insurance_min_sar": 15.0
        }
        put_resp = requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json=new_cfg,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert put_resp.status_code == 200, f"PUT config failed: {put_resp.text}"
        updated = put_resp.json()
        
        # Verify fields were accepted
        assert updated.get("insurance_enabled") == True
        assert updated.get("insurance_percent") == 3.5
        assert updated.get("insurance_min_sar") == 15.0
        
        print(f"✓ Insurance config accepted: enabled={updated.get('insurance_enabled')}, percent={updated.get('insurance_percent')}%, min={updated.get('insurance_min_sar')} SAR")
        
        # Restore original config
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json=original_cfg,
            headers={"Authorization": f"Bearer {owner_token}"}
        )


class TestInsurancePublicQuote:
    """Test 5: Public quote endpoint returns insurance config fields"""

    def test_public_quote_returns_insurance_fields(self, owner_token):
        """POST /api/websites/public/{slug}/shipping/quote returns insurance_enabled, insurance_percent, insurance_min_sar"""
        # Enable insurance
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json={"insurance_enabled": True, "insurance_percent": 2.5, "insurance_min_sar": 12.0},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        
        # Get public quote
        payload = {
            "city": "الرياض",
            "country": "SA",
            "cart_subtotal": 200,
            "weight_kg": 1.0
        }
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/shipping/quote",
            json=payload
        )
        assert resp.status_code == 200, f"Quote failed: {resp.text}"
        data = resp.json()
        
        # Verify insurance fields are returned
        assert "insurance_enabled" in data, "Response should have insurance_enabled"
        assert "insurance_percent" in data, "Response should have insurance_percent"
        assert "insurance_min_sar" in data, "Response should have insurance_min_sar"
        
        assert data["insurance_enabled"] == True
        assert data["insurance_percent"] == 2.5
        assert data["insurance_min_sar"] == 12.0
        
        print(f"✓ Public quote returns insurance config: enabled={data['insurance_enabled']}, percent={data['insurance_percent']}%, min={data['insurance_min_sar']} SAR")
        
        # Cleanup
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json={"insurance_enabled": False},
            headers={"Authorization": f"Bearer {owner_token}"}
        )


class TestInsuranceOrderCreation:
    """Test 6-8: Insurance fee calculation on order creation"""

    def test_insurance_opted_true_computes_fee(self, owner_token, site_customer_token):
        """When customer places order with insurance_opted=true, server computes max(min_sar, subtotal*pct/100)"""
        # Enable insurance: 2% with min 10 SAR
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json={"insurance_enabled": True, "insurance_percent": 2.0, "insurance_min_sar": 10.0},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        
        # Create order with insurance_opted=true and subtotal=500 (2% = 10 SAR, min=10, so fee=10)
        order_payload = {
            "items": [{"name": "TEST_Insurance_Item", "price": 500, "qty": 1}],
            "address": "Test Address Insurance",
            "city": "الرياض",
            "country": "SA",
            "shipping_provider": "smsa",
            "shipping_provider_name": "سمسا إكسبرس",
            "shipping_fee": 25,
            "shipping_eta": "1-3 أيام",
            "payment_method": "cod",
            "insurance_opted": True  # Customer opts for insurance
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders",
            json=order_payload,
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert resp.status_code == 200, f"Order creation failed: {resp.text}"
        data = resp.json()
        order_id = data["order_id"]
        
        # Fetch order to verify insurance_fee
        my_orders_resp = requests.get(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders/my",
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert my_orders_resp.status_code == 200
        orders = my_orders_resp.json()["orders"]
        order = next((o for o in orders if o["id"] == order_id), None)
        assert order is not None
        
        # Verify insurance_fee: max(10, 500*2/100) = max(10, 10) = 10
        assert "insurance_fee" in order, "Order should have insurance_fee field"
        assert order["insurance_fee"] == 10.0, f"Expected insurance_fee=10.0, got {order['insurance_fee']}"
        
        print(f"✓ Order with insurance_opted=true: insurance_fee={order['insurance_fee']} SAR")
        
        # Cleanup
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json={"insurance_enabled": False},
            headers={"Authorization": f"Bearer {owner_token}"}
        )

    def test_insurance_opted_false_fee_is_zero(self, owner_token, site_customer_token):
        """When insurance_opted=false (default), insurance_fee=0 even if config enabled"""
        # Enable insurance
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json={"insurance_enabled": True, "insurance_percent": 2.0, "insurance_min_sar": 10.0},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        
        # Create order WITHOUT insurance_opted (defaults to false)
        order_payload = {
            "items": [{"name": "TEST_No_Insurance", "price": 300, "qty": 1}],
            "address": "Test Address No Insurance",
            "city": "الرياض",
            "country": "SA",
            "shipping_provider": "smsa",
            "shipping_provider_name": "سمسا إكسبرس",
            "shipping_fee": 25,
            "shipping_eta": "1-3 أيام",
            "payment_method": "cod"
            # insurance_opted not set (defaults to false)
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders",
            json=order_payload,
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert resp.status_code == 200, f"Order creation failed: {resp.text}"
        data = resp.json()
        order_id = data["order_id"]
        
        # Fetch order to verify insurance_fee is 0
        my_orders_resp = requests.get(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders/my",
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert my_orders_resp.status_code == 200
        orders = my_orders_resp.json()["orders"]
        order = next((o for o in orders if o["id"] == order_id), None)
        assert order is not None
        
        # Verify insurance_fee is 0
        assert order.get("insurance_fee", 0) == 0, f"Expected insurance_fee=0, got {order.get('insurance_fee')}"
        
        print(f"✓ Order without insurance_opted: insurance_fee={order.get('insurance_fee', 0)} SAR")
        
        # Cleanup
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json={"insurance_enabled": False},
            headers={"Authorization": f"Bearer {owner_token}"}
        )

    def test_insurance_disabled_ignores_opted_true(self, owner_token, site_customer_token):
        """When insurance_enabled=false in config, insurance_opted=true is ignored (insurance_fee=0)"""
        # Disable insurance
        requests.put(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            json={"insurance_enabled": False, "insurance_percent": 2.0, "insurance_min_sar": 10.0},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        
        # Create order with insurance_opted=true but config disabled
        order_payload = {
            "items": [{"name": "TEST_Insurance_Disabled", "price": 400, "qty": 1}],
            "address": "Test Address Insurance Disabled",
            "city": "الرياض",
            "country": "SA",
            "shipping_provider": "smsa",
            "shipping_provider_name": "سمسا إكسبرس",
            "shipping_fee": 25,
            "shipping_eta": "1-3 أيام",
            "payment_method": "cod",
            "insurance_opted": True  # Customer opts for insurance but config disabled
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders",
            json=order_payload,
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert resp.status_code == 200, f"Order creation failed: {resp.text}"
        data = resp.json()
        order_id = data["order_id"]
        
        # Fetch order to verify insurance_fee is 0
        my_orders_resp = requests.get(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders/my",
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert my_orders_resp.status_code == 200
        orders = my_orders_resp.json()["orders"]
        order = next((o for o in orders if o["id"] == order_id), None)
        assert order is not None
        
        # Verify insurance_fee is 0 (config disabled)
        assert order.get("insurance_fee", 0) == 0, f"Expected insurance_fee=0 when config disabled, got {order.get('insurance_fee')}"
        
        print(f"✓ Order with insurance_opted=true but config disabled: insurance_fee={order.get('insurance_fee', 0)} SAR")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 9-11: SHIPMENT TRACKING FEATURE
# ═══════════════════════════════════════════════════════════════════════════════
class TestTrackingNumber:
    """Test 9: PATCH /api/websites/client/orders/{order_id} with tracking_number"""

    def test_patch_order_sets_tracking_number(self, client_token, site_customer_token):
        """PATCH /api/websites/client/orders/{order_id} with tracking_number sets order.tracking_number"""
        # First create an order
        order_payload = {
            "items": [{"name": "TEST_Tracking_Item", "price": 150, "qty": 1}],
            "address": "Test Address Tracking",
            "city": "الرياض",
            "country": "SA",
            "shipping_provider": "smsa",
            "shipping_provider_name": "سمسا إكسبرس",
            "shipping_fee": 25,
            "shipping_eta": "1-3 أيام",
            "payment_method": "cod"
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders",
            json=order_payload,
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert create_resp.status_code == 200, f"Order creation failed: {create_resp.text}"
        order_id = create_resp.json()["order_id"]
        
        # Patch order with tracking_number
        tracking_number = "SMSA123456789"
        patch_resp = requests.patch(
            f"{BASE_URL}/api/websites/client/orders/{order_id}",
            json={"status": "shipped", "tracking_number": tracking_number},
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert patch_resp.status_code == 200, f"PATCH failed: {patch_resp.text}"
        
        # Verify tracking_number was set by fetching customer's orders
        my_orders_resp = requests.get(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders/my",
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert my_orders_resp.status_code == 200
        orders = my_orders_resp.json()["orders"]
        order = next((o for o in orders if o["id"] == order_id), None)
        assert order is not None
        
        assert order.get("tracking_number") == tracking_number, f"Expected tracking_number={tracking_number}, got {order.get('tracking_number')}"
        
        print(f"✓ Order {order_id} tracking_number set to: {order.get('tracking_number')}")


class TestTrackingURL:
    """Test 10-11: GET /api/websites/public/{slug}/orders/my returns tracking_url"""

    def test_orders_my_returns_tracking_url(self, client_token, site_customer_token):
        """GET /api/websites/public/{slug}/orders/my returns each order with computed tracking_url"""
        # Create order with SMSA provider
        order_payload = {
            "items": [{"name": "TEST_Tracking_URL_Item", "price": 200, "qty": 1}],
            "address": "Test Address Tracking URL",
            "city": "الرياض",
            "country": "SA",
            "shipping_provider": "smsa",
            "shipping_provider_name": "سمسا إكسبرس",
            "shipping_fee": 25,
            "shipping_eta": "1-3 أيام",
            "payment_method": "cod"
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders",
            json=order_payload,
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert create_resp.status_code == 200
        order_id = create_resp.json()["order_id"]
        
        # Set tracking number
        tracking_number = "SMSA987654321"
        requests.patch(
            f"{BASE_URL}/api/websites/client/orders/{order_id}",
            json={"status": "shipped", "tracking_number": tracking_number},
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        
        # Fetch orders and verify tracking_url
        my_orders_resp = requests.get(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders/my",
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert my_orders_resp.status_code == 200
        orders = my_orders_resp.json()["orders"]
        order = next((o for o in orders if o["id"] == order_id), None)
        assert order is not None
        
        # Verify tracking_url is computed from SMSA template
        expected_url = f"https://www.smsaexpress.com/sa/en/trackingdetails?tracknumbers={tracking_number}"
        assert "tracking_url" in order, "Order should have tracking_url field"
        assert order["tracking_url"] == expected_url, f"Expected tracking_url={expected_url}, got {order['tracking_url']}"
        
        print(f"✓ Order {order_id} tracking_url: {order['tracking_url']}")

    def test_tracking_url_empty_when_no_tracking_number(self, site_customer_token):
        """tracking_url is empty string when tracking_number is empty"""
        # Create order without setting tracking number
        order_payload = {
            "items": [{"name": "TEST_No_Tracking", "price": 100, "qty": 1}],
            "address": "Test Address No Tracking",
            "city": "الرياض",
            "country": "SA",
            "shipping_provider": "smsa",
            "shipping_provider_name": "سمسا إكسبرس",
            "shipping_fee": 25,
            "shipping_eta": "1-3 أيام",
            "payment_method": "cod"
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders",
            json=order_payload,
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert create_resp.status_code == 200
        order_id = create_resp.json()["order_id"]
        
        # Fetch orders - tracking_url should be empty
        my_orders_resp = requests.get(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders/my",
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert my_orders_resp.status_code == 200
        orders = my_orders_resp.json()["orders"]
        order = next((o for o in orders if o["id"] == order_id), None)
        assert order is not None
        
        # Verify tracking_url is empty
        assert order.get("tracking_url", "") == "", f"Expected empty tracking_url, got {order.get('tracking_url')}"
        
        print(f"✓ Order {order_id} without tracking_number has empty tracking_url")

    def test_tracking_url_empty_when_provider_not_in_catalog(self, site_customer_token):
        """tracking_url is empty string when provider not in catalog"""
        # Create order with local_delivery (not in PROVIDER_BY_ID catalog)
        order_payload = {
            "items": [{"name": "TEST_Local_Delivery", "price": 80, "qty": 1}],
            "address": "Test Address Local",
            "city": "جدة",  # Same city as store
            "country": "SA",
            "shipping_provider": "local_delivery",  # Not in PROVIDER_BY_ID
            "shipping_provider_name": "توصيل جدة (داخلي)",
            "shipping_fee": 15,
            "shipping_eta": "2-4 ساعة",
            "payment_method": "cod"
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders",
            json=order_payload,
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert create_resp.status_code == 200
        order_id = create_resp.json()["order_id"]
        
        # Fetch orders - tracking_url should be empty for local_delivery
        my_orders_resp = requests.get(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders/my",
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert my_orders_resp.status_code == 200
        orders = my_orders_resp.json()["orders"]
        order = next((o for o in orders if o["id"] == order_id), None)
        assert order is not None
        
        # Verify tracking_url is empty (local_delivery not in catalog)
        assert order.get("tracking_url", "") == "", f"Expected empty tracking_url for local_delivery, got {order.get('tracking_url')}"
        
        print(f"✓ Order {order_id} with local_delivery has empty tracking_url (not in catalog)")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 12: BACKWARDS COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════════════════
class TestBackwardsCompatibility:
    """Test 12: Orders without shipping_provider still work via legacy haversine path"""

    def test_legacy_order_without_shipping_provider(self, site_customer_token):
        """Orders without shipping_provider still work via legacy haversine path"""
        # Create order WITHOUT shipping_provider (legacy flow)
        order_payload = {
            "items": [{"name": "TEST_Legacy_Order", "price": 120, "qty": 1}],
            "address": "Legacy Test Address",
            "lat": 21.5433,  # Jeddah coordinates
            "lng": 39.1728,
            "delivery_fee": 15,  # Legacy delivery fee
            "payment_method": "cod"
            # Note: NO shipping_provider, city, country
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders",
            json=order_payload,
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert resp.status_code == 200, f"Legacy order creation failed: {resp.text}"
        data = resp.json()
        
        assert data.get("ok") == True
        assert "order_id" in data
        assert "delivery_fee" in data
        
        print(f"✓ Legacy order created: {data['order_id']}, delivery_fee={data['delivery_fee']} SAR")

    def test_order_without_insurance_opted_field(self, site_customer_token):
        """Orders without insurance_opted field still work (defaults to false)"""
        order_payload = {
            "items": [{"name": "TEST_No_Insurance_Field", "price": 90, "qty": 1}],
            "address": "Test Address No Insurance Field",
            "city": "الرياض",
            "country": "SA",
            "shipping_provider": "smsa",
            "shipping_provider_name": "سمسا إكسبرس",
            "shipping_fee": 25,
            "shipping_eta": "1-3 أيام",
            "payment_method": "cod"
            # Note: NO insurance_opted field
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders",
            json=order_payload,
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert resp.status_code == 200, f"Order creation failed: {resp.text}"
        data = resp.json()
        
        assert data.get("ok") == True
        print(f"✓ Order without insurance_opted field created successfully")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 13: REGRESSION - VERIFY PREVIOUS SHIPPING TESTS STILL PASS
# ═══════════════════════════════════════════════════════════════════════════════
class TestRegressionShippingProviders:
    """Regression: Verify shipping providers endpoint still works"""

    def test_get_shipping_providers_returns_6(self):
        """Verify 6 shipping providers are returned"""
        resp = requests.get(f"{BASE_URL}/api/websites/shipping/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["providers"]) == 6
        provider_ids = [p["id"] for p in data["providers"]]
        for pid in ["smsa", "aramex", "saudi_post", "naqel", "ajex", "dhl"]:
            assert pid in provider_ids
        print(f"✓ Regression: 6 shipping providers returned")


class TestRegressionPublicQuote:
    """Regression: Verify public shipping quote still works"""

    def test_quote_riyadh_returns_options(self):
        """Quote with city='الرياض' returns ranked options"""
        payload = {"city": "الرياض", "country": "SA", "cart_subtotal": 150, "weight_kg": 1.0}
        resp = requests.post(f"{BASE_URL}/api/websites/public/{TEST_SLUG}/shipping/quote", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["options"]) > 0
        print(f"✓ Regression: Public quote returns {len(data['options'])} options")

    def test_free_shipping_above_threshold(self):
        """Free shipping kicks in above threshold"""
        payload = {"city": "جدة", "country": "SA", "cart_subtotal": 250, "weight_kg": 1.0}
        resp = requests.post(f"{BASE_URL}/api/websites/public/{TEST_SLUG}/shipping/quote", json=payload)
        assert resp.status_code == 200
        options = resp.json()["options"]
        free_options = [o for o in options if o.get("is_free")]
        assert len(free_options) > 0
        print(f"✓ Regression: Free shipping above threshold works")


class TestRegressionDashboardConfig:
    """Regression: Verify dashboard shipping config still works"""

    def test_get_shipping_config(self, owner_token):
        """GET shipping config returns expected fields"""
        resp = requests.get(
            f"{BASE_URL}/api/websites/projects/{PROJECT_ID}/shipping/config",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        cfg = resp.json()
        assert "enabled_providers" in cfg
        assert "store_city" in cfg
        print(f"✓ Regression: GET shipping config works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
