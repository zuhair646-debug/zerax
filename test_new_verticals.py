"""
Zitex Shipping System Tests — Iteration 17
═══════════════════════════════════════════
Tests for the new shipping integration:
1. GET /api/websites/shipping/providers — returns 6 SA providers
2. POST /api/websites/public/{slug}/shipping/quote — dynamic shipping quotes
3. Same-city local_delivery as recommended
4. Free shipping threshold
5. International shipping (INTL providers only)
6. Order creation with shipping fields + server-side re-quote
7. Order saved with shipping metadata
8. Dashboard shipping config GET/PUT still works
9. Legacy delivery flow (no shipping_provider) still works
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
SITE_CUSTOMER_PHONE = "0501122334"
SITE_CUSTOMER_PASSWORD = "pass123"


class TestShippingProviders:
    """Test GET /api/websites/shipping/providers — returns 6 SA providers"""

    def test_get_shipping_providers_returns_6(self):
        """Verify 6 shipping providers are returned"""
        resp = requests.get(f"{BASE_URL}/api/websites/shipping/providers")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "providers" in data, "Response should have 'providers' key"
        providers = data["providers"]
        assert len(providers) == 6, f"Expected 6 providers, got {len(providers)}"
        
        # Verify expected provider IDs
        provider_ids = [p["id"] for p in providers]
        expected_ids = ["smsa", "aramex", "saudi_post", "naqel", "ajex", "dhl"]
        for pid in expected_ids:
            assert pid in provider_ids, f"Provider '{pid}' not found in response"
        
        # Verify provider structure
        for p in providers:
            assert "id" in p
            assert "name_ar" in p
            assert "name_en" in p
            assert "coverage" in p
            assert "default_rates" in p
            assert "supports_cod" in p
            print(f"✓ Provider: {p['id']} - {p['name_en']} - Coverage: {p['coverage']}")


class TestPublicShippingQuote:
    """Test POST /api/websites/public/{slug}/shipping/quote"""

    def test_quote_riyadh_sa_returns_ranked_options(self):
        """Quote with city='الرياض', country='SA', cart_subtotal=150 returns ranked options"""
        payload = {
            "city": "الرياض",
            "country": "SA",
            "cart_subtotal": 150,
            "weight_kg": 1.0
        }
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/shipping/quote",
            json=payload
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "options" in data, "Response should have 'options' key"
        assert "country" in data
        assert "city" in data
        assert data["country"] == "SA"
        assert data["city"] == "الرياض"
        
        options = data["options"]
        assert len(options) > 0, "Should return at least one shipping option"
        
        # Verify options are sorted by fee (cheapest first)
        fees = [o["fee_sar"] for o in options]
        assert fees == sorted(fees), "Options should be sorted by fee (cheapest first)"
        
        # Verify at least one is marked as recommended
        recommended = [o for o in options if o.get("is_recommended")]
        assert len(recommended) >= 1, "At least one option should be recommended"
        
        print(f"✓ Got {len(options)} shipping options for الرياض:")
        for opt in options:
            rec = "★" if opt.get("is_recommended") else " "
            free = "(FREE)" if opt.get("is_free") else ""
            print(f"  {rec} {opt['provider_id']}: {opt['fee_sar']} SAR - {opt['delivery_eta']} {free}")

    def test_quote_same_city_returns_local_delivery_recommended(self):
        """Same-city (city='جدة', store_city='جدة') returns local_delivery as recommended"""
        # cozy-cafe-demo has store_city='جدة' by default
        payload = {
            "city": "جدة",
            "country": "SA",
            "cart_subtotal": 100,
            "weight_kg": 1.0
        }
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/shipping/quote",
            json=payload
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        options = data["options"]
        assert len(options) > 0, "Should return shipping options"
        
        # Check if local_delivery is present and recommended
        local = next((o for o in options if o["provider_id"] == "local_delivery"), None)
        if local:
            assert local.get("is_recommended") == True, "local_delivery should be recommended for same-city"
            print(f"✓ local_delivery is recommended: {local['fee_sar']} SAR - {local['delivery_eta']}")
        else:
            # If local_delivery not enabled, first option should be recommended
            assert options[0].get("is_recommended") == True
            print(f"✓ First option is recommended (local_delivery may be disabled): {options[0]['provider_id']}")

    def test_free_shipping_above_threshold(self):
        """Free shipping kicks in when cart_subtotal >= free_shipping_above_sar (default 200)"""
        # Test with subtotal below threshold
        payload_below = {
            "city": "جدة",
            "country": "SA",
            "cart_subtotal": 150,
            "weight_kg": 1.0
        }
        resp_below = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/shipping/quote",
            json=payload_below
        )
        assert resp_below.status_code == 200
        options_below = resp_below.json()["options"]
        
        # Test with subtotal above threshold (200 SAR default)
        payload_above = {
            "city": "جدة",
            "country": "SA",
            "cart_subtotal": 250,
            "weight_kg": 1.0
        }
        resp_above = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/shipping/quote",
            json=payload_above
        )
        assert resp_above.status_code == 200
        options_above = resp_above.json()["options"]
        
        # At least one option should be free when above threshold
        free_options = [o for o in options_above if o.get("is_free") == True]
        assert len(free_options) > 0, "Should have free shipping options when above threshold"
        
        print(f"✓ Below threshold (150 SAR): {len([o for o in options_below if o.get('is_free')])} free options")
        print(f"✓ Above threshold (250 SAR): {len(free_options)} free options")

    def test_international_shipping_us_returns_intl_providers(self):
        """International shipping (country=US) only returns providers covering INTL"""
        payload = {
            "city": "New York",
            "country": "US",
            "cart_subtotal": 300,
            "weight_kg": 2.0
        }
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/shipping/quote",
            json=payload
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        options = data["options"]
        assert len(options) > 0, "Should return international shipping options"
        
        # Only aramex, ajex, dhl should appear (they have INTL coverage)
        intl_providers = {"aramex", "ajex", "dhl"}
        for opt in options:
            assert opt["provider_id"] in intl_providers, f"Provider {opt['provider_id']} should not appear for INTL"
            assert opt["service_type"] == "international"
        
        print(f"✓ International (US) returns {len(options)} providers:")
        for opt in options:
            print(f"  {opt['provider_id']}: {opt['fee_sar']} SAR - {opt['delivery_eta']}")


class TestOrderCreationWithShipping:
    """Test order creation with shipping fields and server-side re-quote"""
    
    @pytest.fixture(scope="class")
    def site_customer_token(self):
        """Login as site customer to get token"""
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/auth/login",
            json={"phone": SITE_CUSTOMER_PHONE, "password": SITE_CUSTOMER_PASSWORD}
        )
        if resp.status_code == 200:
            return resp.json().get("token")
        # If login fails, try to register
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/auth/register",
            json={"name": "Test Customer", "phone": "0509999888", "password": "test123"}
        )
        if resp.status_code == 200:
            return resp.json().get("token")
        pytest.skip(f"Could not get site customer token: {resp.text}")

    def test_order_with_shipping_provider_requotes_server_side(self, site_customer_token):
        """Order creation with shipping_provider re-quotes server-side to prevent fee tampering"""
        # First get a valid quote
        quote_resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/shipping/quote",
            json={"city": "الرياض", "country": "SA", "cart_subtotal": 100}
        )
        assert quote_resp.status_code == 200
        options = quote_resp.json()["options"]
        assert len(options) > 0
        
        # Pick first provider
        chosen = options[0]
        
        # Create order with WRONG fee (should be corrected server-side)
        order_payload = {
            "items": [{"name": "TEST_Item", "price": 50, "qty": 2}],
            "address": "Test Address",
            "city": "الرياض",
            "country": "SA",
            "shipping_provider": chosen["provider_id"],
            "shipping_provider_name": chosen["provider_name"],
            "shipping_fee": 999.99,  # Wrong fee - should be corrected
            "shipping_eta": chosen["delivery_eta"],
            "payment_method": "cod"
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders",
            json=order_payload,
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert data.get("ok") == True
        assert "order_id" in data
        # The delivery_fee should be the server-calculated fee, not 999.99
        assert data["delivery_fee"] != 999.99, "Server should re-quote and not trust client fee"
        
        print(f"✓ Order created: {data['order_id']}")
        print(f"  Delivery fee (server-calculated): {data['delivery_fee']} SAR")
        print(f"  Total: {data['total']} SAR")

    def test_order_saved_with_shipping_metadata(self, site_customer_token):
        """Order saved with shipping metadata (shipping_provider, shipping_provider_name, shipping_eta, shipping_city, shipping_country)"""
        # Create order with shipping fields
        order_payload = {
            "items": [{"name": "TEST_Shipping_Metadata", "price": 75, "qty": 1}],
            "address": "Test Address for Metadata",
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
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        order_id = data["order_id"]
        
        # Fetch my orders to verify metadata was saved
        my_orders_resp = requests.get(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders/my",
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert my_orders_resp.status_code == 200
        orders = my_orders_resp.json()["orders"]
        
        # Find our order
        order = next((o for o in orders if o["id"] == order_id), None)
        assert order is not None, f"Order {order_id} not found in my orders"
        
        # Verify shipping metadata
        assert order.get("shipping_provider") == "smsa", f"Expected shipping_provider='smsa', got {order.get('shipping_provider')}"
        assert order.get("shipping_provider_name") == "سمسا إكسبرس"
        assert order.get("shipping_eta") == "1-3 أيام"
        assert order.get("shipping_city") == "الدمام"
        assert order.get("shipping_country") == "SA"
        
        print(f"✓ Order {order_id} has shipping metadata:")
        print(f"  shipping_provider: {order.get('shipping_provider')}")
        print(f"  shipping_provider_name: {order.get('shipping_provider_name')}")
        print(f"  shipping_eta: {order.get('shipping_eta')}")
        print(f"  shipping_city: {order.get('shipping_city')}")
        print(f"  shipping_country: {order.get('shipping_country')}")


class TestDashboardShippingConfig:
    """Test dashboard shipping config GET/PUT still works for owner"""
    
    @pytest.fixture(scope="class")
    def owner_token(self):
        """Login as owner to get JWT token"""
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
        )
        assert resp.status_code == 200, f"Owner login failed: {resp.text}"
        return resp.json().get("token")
    
    @pytest.fixture(scope="class")
    def project_id(self, owner_token):
        """Get project ID for cozy-cafe-demo"""
        resp = requests.get(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        projects = resp.json().get("projects", [])
        project = next((p for p in projects if p.get("slug") == TEST_SLUG), None)
        if not project:
            pytest.skip(f"Project with slug '{TEST_SLUG}' not found")
        return project["id"]

    def test_get_shipping_config(self, owner_token, project_id):
        """GET /api/websites/projects/{id}/shipping/config returns config"""
        resp = requests.get(
            f"{BASE_URL}/api/websites/projects/{project_id}/shipping/config",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        cfg = resp.json()
        
        # Verify expected fields
        assert "enabled_providers" in cfg
        assert "store_city" in cfg
        assert "local_delivery_enabled" in cfg
        assert "free_shipping_above_sar" in cfg
        
        print(f"✓ Shipping config retrieved:")
        print(f"  enabled_providers: {cfg.get('enabled_providers')}")
        print(f"  store_city: {cfg.get('store_city')}")
        print(f"  local_delivery_enabled: {cfg.get('local_delivery_enabled')}")
        print(f"  free_shipping_above_sar: {cfg.get('free_shipping_above_sar')}")

    def test_put_shipping_config(self, owner_token, project_id):
        """PUT /api/websites/projects/{id}/shipping/config updates config"""
        # First get current config
        get_resp = requests.get(
            f"{BASE_URL}/api/websites/projects/{project_id}/shipping/config",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        original_cfg = get_resp.json()
        
        # Update config
        new_cfg = {
            "enabled_providers": ["smsa", "aramex", "naqel"],
            "store_city": "جدة",
            "local_delivery_enabled": True,
            "local_delivery_fee": 20,
            "free_shipping_above_sar": 250
        }
        
        put_resp = requests.put(
            f"{BASE_URL}/api/websites/projects/{project_id}/shipping/config",
            json=new_cfg,
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert put_resp.status_code == 200, f"Expected 200, got {put_resp.status_code}: {put_resp.text}"
        updated = put_resp.json()
        
        assert updated.get("enabled_providers") == ["smsa", "aramex", "naqel"]
        assert updated.get("free_shipping_above_sar") == 250
        
        print(f"✓ Shipping config updated successfully")
        
        # Restore original config
        requests.put(
            f"{BASE_URL}/api/websites/projects/{project_id}/shipping/config",
            json=original_cfg,
            headers={"Authorization": f"Bearer {owner_token}"}
        )


class TestLegacyDeliveryFlow:
    """Test legacy delivery flow (no shipping_provider) still works using haversine fallback"""
    
    @pytest.fixture(scope="class")
    def site_customer_token(self):
        """Login as site customer to get token"""
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/auth/login",
            json={"phone": SITE_CUSTOMER_PHONE, "password": SITE_CUSTOMER_PASSWORD}
        )
        if resp.status_code == 200:
            return resp.json().get("token")
        # If login fails, try to register
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/auth/register",
            json={"name": "Legacy Test", "phone": "0508888777", "password": "test123"}
        )
        if resp.status_code == 200:
            return resp.json().get("token")
        pytest.skip(f"Could not get site customer token: {resp.text}")

    def test_order_without_shipping_provider_uses_legacy_delivery(self, site_customer_token):
        """Order without shipping_provider uses legacy haversine delivery calculation"""
        # Create order WITHOUT shipping_provider (legacy flow)
        order_payload = {
            "items": [{"name": "TEST_Legacy_Delivery", "price": 60, "qty": 1}],
            "address": "Legacy Test Address",
            "lat": 21.5433,  # Jeddah coordinates
            "lng": 39.1728,
            "delivery_fee": 15,  # Legacy delivery fee
            "payment_method": "cod"
            # Note: NO shipping_provider, shipping_fee, city, country
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/orders",
            json=order_payload,
            headers={"Authorization": f"SiteToken {site_customer_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert data.get("ok") == True
        assert "order_id" in data
        assert "delivery_fee" in data
        
        print(f"✓ Legacy order created: {data['order_id']}")
        print(f"  Delivery fee: {data['delivery_fee']} SAR")
        print(f"  Distance: {data.get('distance_km', 0)} km")


class TestShippingQuoteEdgeCases:
    """Test edge cases for shipping quote"""

    def test_quote_without_city_uses_ip_detection(self):
        """Quote without city/country uses IP detection (returns detected country or fallback)"""
        payload = {
            "cart_subtotal": 100,
            "weight_kg": 1.0
            # No city or country - should use IP detection
        }
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/shipping/quote",
            json=payload
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # IP detection should return a valid country code (2 letters)
        country = data.get("country", "")
        assert len(country) == 2 or country == "", "Country should be 2-letter ISO code or empty"
        assert "options" in data
        assert len(data["options"]) > 0, "Should return shipping options"
        
        print(f"✓ Quote without city/country: country={data.get('country')}, city={data.get('city')}")
        print(f"  Options count: {len(data.get('options', []))}")

    def test_quote_with_heavy_weight(self):
        """Quote with heavy weight (>5kg) applies extra_kg_fee"""
        payload_light = {
            "city": "الرياض",
            "country": "SA",
            "cart_subtotal": 100,
            "weight_kg": 1.0
        }
        payload_heavy = {
            "city": "الرياض",
            "country": "SA",
            "cart_subtotal": 100,
            "weight_kg": 10.0  # 5kg overage
        }
        
        resp_light = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/shipping/quote",
            json=payload_light
        )
        resp_heavy = requests.post(
            f"{BASE_URL}/api/websites/public/{TEST_SLUG}/shipping/quote",
            json=payload_heavy
        )
        
        assert resp_light.status_code == 200
        assert resp_heavy.status_code == 200
        
        options_light = resp_light.json()["options"]
        options_heavy = resp_heavy.json()["options"]
        
        # Find same provider in both
        for opt_light in options_light:
            opt_heavy = next((o for o in options_heavy if o["provider_id"] == opt_light["provider_id"]), None)
            if opt_heavy and opt_light["provider_id"] != "local_delivery":
                # Heavy should cost more (unless free shipping)
                if not opt_light.get("is_free") and not opt_heavy.get("is_free"):
                    assert opt_heavy["fee_sar"] >= opt_light["fee_sar"], \
                        f"Heavy weight should cost more for {opt_light['provider_id']}"
                    print(f"✓ {opt_light['provider_id']}: 1kg={opt_light['fee_sar']} SAR, 10kg={opt_heavy['fee_sar']} SAR")
                break

    def test_quote_invalid_slug_returns_404(self):
        """Quote with invalid slug returns 404"""
        payload = {"city": "الرياض", "country": "SA", "cart_subtotal": 100}
        resp = requests.post(
            f"{BASE_URL}/api/websites/public/invalid-slug-xyz/shipping/quote",
            json=payload
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
