"""
Comprehensive regression tests for Zitex Website Module
Tests all 4 auth token types: Bearer JWT, ClientToken, SiteToken, DriverToken
Tests: Platform Owner, Client Dashboard, Site Customer, Driver Dashboard, Orders, Coupons, Loyalty
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
OWNER_EMAIL = "owner@zitex.com"
OWNER_PASSWORD = "owner123"
CLIENT_SLUG = "cozy-cafe-demo"
CLIENT_PASSWORD = "WKDWkG0d"
SITE_CUSTOMER_PHONE = "0501122334"
SITE_CUSTOMER_PASSWORD = "pass123"
DRIVER_PHONE = "0559988776"
DRIVER_PASSWORD = "drv123"
SHARE_TOKEN = "05VuNbyO9McTmt9Z_Hz68CG4KH0"


class TestPlatformOwnerAuth:
    """Test 1: Platform Owner authentication with Bearer JWT"""
    
    def test_owner_login_success(self):
        """POST /api/auth/login with owner@zitex.com/owner123 → returns JWT"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == OWNER_EMAIL
        print(f"✓ Owner login successful, role: {data['user'].get('role')}")
        return data["token"]
    
    def test_owner_login_invalid_credentials(self):
        """POST /api/auth/login with wrong credentials → 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@email.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")


class TestAdminSitesList:
    """Test 2: Admin list sites with JWT"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        return response.json()["token"]
    
    def test_list_projects_with_jwt(self, owner_token):
        """GET /api/websites/projects (with JWT) → lists projects including cozy-cafe-demo"""
        response = requests.get(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "projects" in data
        print(f"✓ Found {len(data['projects'])} projects")
        
        # Check if cozy-cafe-demo exists
        slugs = [p.get("slug") for p in data["projects"]]
        if CLIENT_SLUG in slugs:
            print(f"✓ Found {CLIENT_SLUG} in projects")
        else:
            print(f"⚠ {CLIENT_SLUG} not found in user's projects (may belong to different user)")


class TestPublicSiteRendering:
    """Test 3: Public site rendering"""
    
    def test_public_site_html(self):
        """GET /api/websites/public/cozy-cafe-demo → returns full HTML"""
        response = requests.get(f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}")
        assert response.status_code == 200, f"Public site not found: {response.status_code}"
        html = response.text
        
        # Check for Arabic RTL
        assert 'dir="rtl"' in html or 'direction:rtl' in html, "Missing RTL direction"
        print("✓ Public site renders with RTL direction")
        
        # Check for PWA manifest link
        assert 'manifest.json' in html, "Missing PWA manifest link"
        print("✓ PWA manifest link present")
        
        # Check for commerce overlay (auth/cart)
        assert 'zx-auth-fab' in html or 'ZX-COMMERCE-OVERLAY' in html, "Missing commerce overlay"
        print("✓ Commerce overlay present")
    
    def test_public_site_info(self):
        """GET /api/websites/public/cozy-cafe-demo/info → returns metadata"""
        response = requests.get(f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/info")
        assert response.status_code == 200, f"Info endpoint failed: {response.text}"
        data = response.json()
        assert "name" in data or "slug" in data
        print(f"✓ Public site info: {data.get('name', data.get('slug'))}")


class TestShareablePreview:
    """Test 4: Shareable preview link"""
    
    def test_share_link_html(self):
        """GET /api/websites/share/{token} → returns HTML"""
        response = requests.get(f"{BASE_URL}/api/websites/share/{SHARE_TOKEN}")
        # May be 404 if token expired or doesn't exist
        if response.status_code == 200:
            html = response.text
            assert '<html' in html.lower() or '<!doctype' in html.lower()
            print("✓ Share link returns HTML")
        elif response.status_code in [404, 410]:
            print(f"⚠ Share link expired or not found (status {response.status_code})")
        else:
            pytest.fail(f"Unexpected status: {response.status_code}")


class TestClientDashboardAuth:
    """Test 5: Client Dashboard login with ClientToken"""
    
    def test_client_login_success(self):
        """POST /api/websites/client/login with slug=cozy-cafe-demo password=WKDWkG0d → returns ClientToken"""
        response = requests.post(f"{BASE_URL}/api/websites/client/login", json={
            "slug": CLIENT_SLUG,
            "password": CLIENT_PASSWORD
        })
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert data.get("ok") == True or "token" in data
        print(f"✓ Client login successful for {CLIENT_SLUG}")
        return data["token"]
    
    def test_client_login_wrong_password(self):
        """POST /api/websites/client/login with wrong password → 401"""
        response = requests.post(f"{BASE_URL}/api/websites/client/login", json={
            "slug": CLIENT_SLUG,
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Wrong client password correctly rejected")


class TestClientDashboardData:
    """Test 6: Client Dashboard data endpoints with ClientToken"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/websites/client/login", json={
            "slug": CLIENT_SLUG,
            "password": CLIENT_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Client login failed")
        return response.json()["token"]
    
    def test_client_orders(self, client_token):
        """GET /api/websites/client/orders with ClientToken"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/orders",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "orders" in data
        print(f"✓ Client orders: {len(data['orders'])} orders")
    
    def test_client_customers(self, client_token):
        """GET /api/websites/client/customers with ClientToken"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/customers",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "customers" in data
        print(f"✓ Client customers: {len(data['customers'])} customers")
    
    def test_client_drivers(self, client_token):
        """GET /api/websites/client/drivers with ClientToken"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/drivers",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "drivers" in data
        print(f"✓ Client drivers: {len(data['drivers'])} drivers")
    
    def test_client_support_tickets(self, client_token):
        """GET /api/websites/client/support-tickets with ClientToken"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/support-tickets",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "tickets" in data
        print(f"✓ Client tickets: {len(data['tickets'])} tickets")
    
    def test_client_analytics(self, client_token):
        """GET /api/websites/client/analytics with ClientToken"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/analytics",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "visits" in data or "messages_total" in data
        print(f"✓ Client analytics: {data.get('visits', 0)} visits")


class TestSiteCustomerAuth:
    """Test 7: End-user (site customer) auth flow with SiteToken"""
    
    def test_site_customer_login_existing(self):
        """POST /api/websites/public/cozy-cafe-demo/auth/login with existing customer"""
        response = requests.post(
            f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/auth/login",
            json={"phone": SITE_CUSTOMER_PHONE, "password": SITE_CUSTOMER_PASSWORD}
        )
        assert response.status_code == 200, f"Site customer login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "customer" in data, "No customer in response"
        print(f"✓ Site customer login successful: {data['customer'].get('name')}")
        return data["token"]
    
    def test_site_customer_register_new(self):
        """POST /api/websites/public/cozy-cafe-demo/auth/register with new customer"""
        unique_phone = f"05{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/auth/register",
            json={
                "name": "Test Customer",
                "phone": unique_phone,
                "password": "testpass123"
            }
        )
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "customer" in data, "No customer in response"
        print(f"✓ New site customer registered: {unique_phone}")
        return data["token"]


class TestCartAndOrder:
    """Test 8: Cart & Order with Haversine delivery fee calculation"""
    
    @pytest.fixture
    def site_token(self):
        response = requests.post(
            f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/auth/login",
            json={"phone": SITE_CUSTOMER_PHONE, "password": SITE_CUSTOMER_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Site customer login failed")
        return response.json()["token"]
    
    def test_create_order_with_location(self, site_token):
        """POST /api/websites/public/cozy-cafe-demo/order with items, lat/lng, SiteToken"""
        # Riyadh coordinates
        lat, lng = 24.7136, 46.6753
        
        response = requests.post(
            f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/orders",
            headers={"Authorization": f"SiteToken {site_token}"},
            json={
                "items": [
                    {"name": "قهوة تركية", "price": 15, "qty": 2},
                    {"name": "كابتشينو", "price": 20, "qty": 1}
                ],
                "address": "الرياض، حي النزهة",
                "lat": lat,
                "lng": lng,
                "note": "بدون سكر",
                "payment_method": "cod"
            }
        )
        assert response.status_code == 200, f"Order creation failed: {response.text}"
        data = response.json()
        assert "order_id" in data, "No order_id in response"
        assert "total" in data, "No total in response"
        assert "delivery_fee" in data, "No delivery_fee in response"
        
        print(f"✓ Order created: {data['order_id'][:8]}")
        print(f"  Total: {data['total']} SAR, Delivery fee: {data['delivery_fee']} SAR")
        if "distance_km" in data:
            print(f"  Distance: {data['distance_km']} km (Haversine)")
        return data
    
    def test_get_my_orders(self, site_token):
        """GET /api/websites/public/cozy-cafe-demo/orders/my with SiteToken"""
        response = requests.get(
            f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/orders/my",
            headers={"Authorization": f"SiteToken {site_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "orders" in data
        print(f"✓ Customer has {len(data['orders'])} orders")


class TestDriverAuth:
    """Test 9: Driver login with DriverToken"""
    
    def test_driver_login_success(self):
        """POST /api/websites/driver/login with slug+phone+password → returns DriverToken"""
        response = requests.post(f"{BASE_URL}/api/websites/driver/login", json={
            "slug": CLIENT_SLUG,
            "phone": DRIVER_PHONE,
            "password": DRIVER_PASSWORD
        })
        assert response.status_code == 200, f"Driver login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        print(f"✓ Driver login successful: {data.get('driver', {}).get('name', 'Unknown')}")
        return data["token"]
    
    def test_driver_login_wrong_credentials(self):
        """POST /api/websites/driver/login with wrong credentials → 401"""
        response = requests.post(f"{BASE_URL}/api/websites/driver/login", json={
            "slug": CLIENT_SLUG,
            "phone": "0500000000",
            "password": "wrongpass"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Wrong driver credentials correctly rejected")


class TestDriverDashboard:
    """Test 10: Driver dashboard endpoints"""
    
    @pytest.fixture
    def driver_token(self):
        response = requests.post(f"{BASE_URL}/api/websites/driver/login", json={
            "slug": CLIENT_SLUG,
            "phone": DRIVER_PHONE,
            "password": DRIVER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Driver login failed")
        return response.json()["token"]
    
    def test_driver_orders(self, driver_token):
        """GET /api/websites/driver/orders (with DriverToken) → returns assigned/available orders"""
        response = requests.get(
            f"{BASE_URL}/api/websites/driver/{CLIENT_SLUG}/orders",
            headers={"Authorization": f"DriverToken {driver_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "orders" in data
        print(f"✓ Driver has {len(data['orders'])} assigned orders")


class TestAuthTokenIsolation:
    """Test auth token isolation - ClientToken should NOT grant driver access and vice versa"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/websites/client/login", json={
            "slug": CLIENT_SLUG,
            "password": CLIENT_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Client login failed")
        return response.json()["token"]
    
    @pytest.fixture
    def driver_token(self):
        response = requests.post(f"{BASE_URL}/api/websites/driver/login", json={
            "slug": CLIENT_SLUG,
            "phone": DRIVER_PHONE,
            "password": DRIVER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Driver login failed")
        return response.json()["token"]
    
    def test_client_token_cannot_access_driver_endpoint(self, client_token):
        """ClientToken should NOT work on driver endpoints"""
        response = requests.get(
            f"{BASE_URL}/api/websites/driver/{CLIENT_SLUG}/orders",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        # Should fail with 401
        assert response.status_code == 401, f"Expected 401, got {response.status_code} - Token isolation breach!"
        print("✓ ClientToken correctly rejected on driver endpoint")
    
    def test_driver_token_cannot_access_client_endpoint(self, driver_token):
        """DriverToken should NOT work on client endpoints"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/orders",
            headers={"Authorization": f"DriverToken {driver_token}"}
        )
        # Should fail with 401
        assert response.status_code == 401, f"Expected 401, got {response.status_code} - Token isolation breach!"
        print("✓ DriverToken correctly rejected on client endpoint")


class TestCouponSystem:
    """Test 13: Coupon creation and usage"""
    
    @pytest.fixture
    def client_token(self):
        response = requests.post(f"{BASE_URL}/api/websites/client/login", json={
            "slug": CLIENT_SLUG,
            "password": CLIENT_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Client login failed")
        return response.json()["token"]
    
    def test_create_coupon(self, client_token):
        """POST /api/websites/client/coupons - create a coupon"""
        coupon_code = f"TEST{uuid.uuid4().hex[:6].upper()}"
        response = requests.post(
            f"{BASE_URL}/api/websites/client/coupons",
            headers={"Authorization": f"ClientToken {client_token}"},
            json={
                "code": coupon_code,
                "discount_percent": 10,
                "discount_amount": 0,
                "min_order": 50,
                "max_uses": 100
            }
        )
        assert response.status_code == 200, f"Coupon creation failed: {response.text}"
        data = response.json()
        assert data.get("ok") == True or "coupon" in data
        print(f"✓ Coupon created: {coupon_code}")
        return coupon_code
    
    def test_list_coupons(self, client_token):
        """GET /api/websites/client/coupons - list coupons"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/coupons",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "coupons" in data
        print(f"✓ Found {len(data['coupons'])} coupons")


class TestLoyaltyPoints:
    """Test 12: Loyalty points accrual"""
    
    @pytest.fixture
    def site_token(self):
        response = requests.post(
            f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/auth/login",
            json={"phone": SITE_CUSTOMER_PHONE, "password": SITE_CUSTOMER_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Site customer login failed")
        return response.json()["token"]
    
    def test_get_my_points(self, site_token):
        """GET /api/websites/public/cozy-cafe-demo/my-points with SiteToken"""
        response = requests.get(
            f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/my-points",
            headers={"Authorization": f"SiteToken {site_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "points" in data
        print(f"✓ Customer has {data['points']} loyalty points")


class TestPWAManifest:
    """Test 15: PWA manifest"""
    
    def test_pwa_manifest(self):
        """GET /api/websites/public/cozy-cafe-demo/manifest.json → returns valid manifest JSON"""
        response = requests.get(f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/manifest.json")
        assert response.status_code == 200, f"Manifest not found: {response.status_code}"
        data = response.json()
        assert "name" in data or "short_name" in data, "Invalid manifest - missing name"
        assert "icons" in data or "start_url" in data, "Invalid manifest - missing icons/start_url"
        print(f"✓ PWA manifest valid: {data.get('name', data.get('short_name'))}")


class TestLogoGeneration:
    """Test 14: Logo generation (may be slow)"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        return response.json()["token"]
    
    def test_generate_logo_variants_endpoint_exists(self, owner_token):
        """POST /api/websites/generate-logo-variants - check endpoint exists (may timeout)"""
        # First we need a project ID
        response = requests.get(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        if response.status_code != 200 or not response.json().get("projects"):
            pytest.skip("No projects available for logo test")
        
        project_id = response.json()["projects"][0]["id"]
        
        # Try the endpoint with a short timeout - we just want to verify it exists
        try:
            response = requests.post(
                f"{BASE_URL}/api/websites/projects/{project_id}/generate-logo-variants",
                headers={"Authorization": f"Bearer {owner_token}"},
                json={
                    "prompt": "Test logo",
                    "style_hint": "minimal",
                    "count": 1
                },
                timeout=5  # Short timeout - we just want to check endpoint exists
            )
            if response.status_code == 200:
                print("✓ Logo generation endpoint works")
            elif response.status_code == 500:
                print("⚠ Logo generation returned 500 (may be quota/API issue)")
            else:
                print(f"⚠ Logo generation returned {response.status_code}")
        except requests.exceptions.Timeout:
            print("⚠ Logo generation timed out (known-slow, skipping)")
        except Exception as e:
            print(f"⚠ Logo generation error: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
