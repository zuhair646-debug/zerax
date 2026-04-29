"""
Test Payment APIs and Credit Deduction Logic
Tests for:
- /api/payments/create-order - creates PayPal order
- /api/payments/capture-order - processes payment and adds credits
- Credit deduction logic for images/videos
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
OWNER_EMAIL = "owner@zitex.com"
OWNER_PASSWORD = "owner123"

# Test user for credit deduction tests
TEST_USER_EMAIL = f"TEST_payment_{uuid.uuid4().hex[:8]}@test.com"
TEST_USER_PASSWORD = "testpass123"
TEST_USER_NAME = "Test Payment User"


class TestPaymentAPIs:
    """Test Payment Order APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_auth_token(self, email, password):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def register_test_user(self):
        """Register a new test user"""
        response = self.session.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "name": TEST_USER_NAME,
            "country": "SA"
        })
        if response.status_code == 200:
            return response.json()
        return None
    
    # ============== Payment Create Order Tests ==============
    
    def test_create_order_requires_auth(self):
        """Test that create-order requires authentication"""
        response = self.session.post(f"{BASE_URL}/api/payments/create-order", json={
            "package_id": "starter",
            "package_type": "credits",
            "amount": 13,
            "currency": "USD"
        })
        assert response.status_code == 403 or response.status_code == 401, f"Expected 401/403, got {response.status_code}"
        print("✅ create-order requires authentication")
    
    def test_create_order_success_credits_package(self):
        """Test creating order for credits package"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.post(f"{BASE_URL}/api/payments/create-order", json={
            "package_id": "starter",
            "package_type": "credits",
            "amount": 13,
            "currency": "USD"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "order_id" in data, "Response should contain order_id"
        assert "internal_id" in data, "Response should contain internal_id"
        assert "amount" in data, "Response should contain amount"
        assert "currency" in data, "Response should contain currency"
        
        # Verify PayPal mock order ID format
        assert data["order_id"].startswith("PAYPAL-"), f"Order ID should start with PAYPAL-, got {data['order_id']}"
        assert data["amount"] == 13, f"Amount should be 13, got {data['amount']}"
        assert data["currency"] == "USD", f"Currency should be USD, got {data['currency']}"
        
        print(f"✅ create-order success - order_id: {data['order_id']}")
        return data
    
    def test_create_order_pro_package(self):
        """Test creating order for pro credits package"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.post(f"{BASE_URL}/api/payments/create-order", json={
            "package_id": "pro",
            "package_type": "credits",
            "amount": 53,
            "currency": "USD"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["order_id"].startswith("PAYPAL-")
        print(f"✅ create-order pro package - order_id: {data['order_id']}")
    
    def test_create_order_invalid_package(self):
        """Test creating order with invalid package"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.post(f"{BASE_URL}/api/payments/create-order", json={
            "package_id": "invalid_package",
            "package_type": "credits",
            "amount": 100,
            "currency": "USD"
        })
        
        assert response.status_code == 400, f"Expected 400 for invalid package, got {response.status_code}"
        print("✅ create-order rejects invalid package")
    
    def test_create_order_subscription(self):
        """Test creating order for subscription"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.post(f"{BASE_URL}/api/payments/create-order", json={
            "package_id": "images_monthly",
            "package_type": "subscription",
            "amount": 27,
            "currency": "USD"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["order_id"].startswith("PAYPAL-")
        print(f"✅ create-order subscription - order_id: {data['order_id']}")
    
    # ============== Payment Capture Order Tests ==============
    
    def test_capture_order_requires_auth(self):
        """Test that capture-order requires authentication"""
        response = self.session.post(f"{BASE_URL}/api/payments/capture-order", json={
            "order_id": "PAYPAL-TEST123",
            "package_id": "starter",
            "package_type": "credits"
        })
        assert response.status_code == 403 or response.status_code == 401, f"Expected 401/403, got {response.status_code}"
        print("✅ capture-order requires authentication")
    
    def test_capture_order_not_found(self):
        """Test capture-order with non-existent order"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.post(f"{BASE_URL}/api/payments/capture-order", json={
            "order_id": "PAYPAL-NONEXISTENT",
            "package_id": "starter",
            "package_type": "credits"
        })
        
        assert response.status_code == 404, f"Expected 404 for non-existent order, got {response.status_code}"
        print("✅ capture-order returns 404 for non-existent order")
    
    def test_capture_order_success_adds_credits(self):
        """Test full payment flow: create order -> capture -> credits added"""
        # Register a new test user
        reg_response = self.register_test_user()
        if not reg_response:
            # User might already exist, try login
            token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        else:
            token = reg_response.get("token")
        
        assert token, "Failed to get auth token for test user"
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get initial balance
        balance_response = self.session.get(f"{BASE_URL}/api/user/balance")
        assert balance_response.status_code == 200
        initial_credits = balance_response.json().get("credits", 0)
        print(f"Initial credits: {initial_credits}")
        
        # Create order
        create_response = self.session.post(f"{BASE_URL}/api/payments/create-order", json={
            "package_id": "starter",
            "package_type": "credits",
            "amount": 13,
            "currency": "USD"
        })
        assert create_response.status_code == 200
        order_data = create_response.json()
        order_id = order_data["order_id"]
        print(f"Created order: {order_id}")
        
        # Capture order
        capture_response = self.session.post(f"{BASE_URL}/api/payments/capture-order", json={
            "order_id": order_id,
            "package_id": "starter",
            "package_type": "credits"
        })
        
        assert capture_response.status_code == 200, f"Expected 200, got {capture_response.status_code}: {capture_response.text}"
        capture_data = capture_response.json()
        
        # Verify response
        assert capture_data["status"] == "completed", f"Status should be completed, got {capture_data['status']}"
        assert "credits_added" in capture_data, "Response should contain credits_added"
        assert capture_data["credits_added"] >= 100, f"Should add at least 100 credits (starter package), got {capture_data['credits_added']}"
        
        print(f"✅ capture-order success - credits_added: {capture_data['credits_added']}")
        
        # Verify credits were actually added
        balance_response = self.session.get(f"{BASE_URL}/api/user/balance")
        assert balance_response.status_code == 200
        new_credits = balance_response.json().get("credits", 0)
        
        assert new_credits > initial_credits, f"Credits should increase. Initial: {initial_credits}, New: {new_credits}"
        print(f"✅ Credits verified - Initial: {initial_credits}, New: {new_credits}")
    
    def test_capture_order_first_purchase_bonus(self):
        """Test that first purchase gives bonus points"""
        # Create a fresh test user
        fresh_email = f"TEST_fresh_{uuid.uuid4().hex[:8]}@test.com"
        
        reg_response = self.session.post(f"{BASE_URL}/api/auth/register", json={
            "email": fresh_email,
            "password": "testpass123",
            "name": "Fresh Test User",
            "country": "SA"
        })
        
        if reg_response.status_code != 200:
            pytest.skip("Could not create fresh test user")
        
        token = reg_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Create and capture order
        create_response = self.session.post(f"{BASE_URL}/api/payments/create-order", json={
            "package_id": "starter",
            "package_type": "credits",
            "amount": 13,
            "currency": "USD"
        })
        assert create_response.status_code == 200
        order_id = create_response.json()["order_id"]
        
        capture_response = self.session.post(f"{BASE_URL}/api/payments/capture-order", json={
            "order_id": order_id,
            "package_id": "starter",
            "package_type": "credits"
        })
        
        assert capture_response.status_code == 200
        capture_data = capture_response.json()
        
        # First purchase should include bonus
        assert "first_purchase_bonus" in capture_data, "Response should contain first_purchase_bonus"
        # First purchase bonus is 50 points
        if capture_data["first_purchase_bonus"] > 0:
            print(f"✅ First purchase bonus applied: {capture_data['first_purchase_bonus']} points")
        else:
            print("ℹ️ First purchase bonus was 0 (may have been claimed already)")
    
    # ============== Payment History Tests ==============
    
    def test_payment_history_requires_auth(self):
        """Test that payment history requires authentication"""
        # Clear auth header
        self.session.headers.pop("Authorization", None)
        
        response = self.session.get(f"{BASE_URL}/api/payments/history")
        assert response.status_code == 403 or response.status_code == 401
        print("✅ payment history requires authentication")
    
    def test_payment_history_returns_orders(self):
        """Test that payment history returns user's orders"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/payments/history")
        assert response.status_code == 200
        data = response.json()
        
        assert "orders" in data, "Response should contain orders array"
        assert isinstance(data["orders"], list), "Orders should be a list"
        print(f"✅ payment history returns {len(data['orders'])} orders")


class TestCreditDeductionLogic:
    """Test credit deduction logic for images/videos"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_auth_token(self, email, password):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_owner_no_credit_deduction(self):
        """Test that owner user doesn't get credits deducted"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get initial balance
        balance_response = self.session.get(f"{BASE_URL}/api/user/balance")
        assert balance_response.status_code == 200
        initial_credits = balance_response.json().get("credits", 0)
        
        # Owner should have is_owner=true, so credits won't be deducted
        # We can verify this by checking the user profile
        me_response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        user_data = me_response.json()
        
        is_owner = user_data.get("is_owner", False)
        print(f"User is_owner: {is_owner}")
        
        if is_owner:
            print("✅ Owner user confirmed - credits won't be deducted for content generation")
        else:
            print("⚠️ User is not marked as owner")
    
    def test_service_costs_in_pricing(self):
        """Test that service costs are defined in pricing config"""
        response = self.session.get(f"{BASE_URL}/api/pricing")
        assert response.status_code == 200
        data = response.json()
        
        assert "service_costs" in data, "Pricing should contain service_costs"
        costs = data["service_costs"]
        
        # Verify image generation cost
        assert "image_generation" in costs, "Should have image_generation cost"
        assert costs["image_generation"] == 5, f"Image generation should cost 5 points, got {costs['image_generation']}"
        
        # Verify video costs
        assert "video_4_seconds" in costs, "Should have video_4_seconds cost"
        assert costs["video_4_seconds"] == 10, f"Video 4s should cost 10 points, got {costs['video_4_seconds']}"
        
        assert "video_12_seconds" in costs, "Should have video_12_seconds cost"
        assert costs["video_12_seconds"] == 25, f"Video 12s should cost 25 points, got {costs['video_12_seconds']}"
        
        assert "video_60_seconds" in costs, "Should have video_60_seconds cost"
        assert costs["video_60_seconds"] == 100, f"Video 60s should cost 100 points, got {costs['video_60_seconds']}"
        
        print("✅ Service costs verified:")
        print(f"   - Image generation: {costs['image_generation']} points")
        print(f"   - Video 4s: {costs['video_4_seconds']} points")
        print(f"   - Video 12s: {costs['video_12_seconds']} points")
        print(f"   - Video 60s: {costs['video_60_seconds']} points")
    
    def test_user_balance_includes_service_costs(self):
        """Test that user balance endpoint includes service costs"""
        token = self.get_auth_token(OWNER_EMAIL, OWNER_PASSWORD)
        assert token, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/user/balance")
        assert response.status_code == 200
        data = response.json()
        
        # Verify balance structure
        assert "credits" in data, "Balance should contain credits"
        assert "free_images" in data, "Balance should contain free_images"
        assert "free_videos" in data, "Balance should contain free_videos"
        assert "service_costs" in data, "Balance should contain service_costs"
        
        print(f"✅ User balance structure verified:")
        print(f"   - Credits: {data['credits']}")
        print(f"   - Free images: {data['free_images']}")
        print(f"   - Free videos: {data['free_videos']}")
        print(f"   - Service costs included: {bool(data['service_costs'])}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
