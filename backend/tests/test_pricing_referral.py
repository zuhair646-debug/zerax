"""
Test suite for Zitex Pricing and Referral System APIs
Tests: /api/pricing, /api/user/balance, /api/referral/info, /api/referral/apply, registration with referral
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-cinematic-hub-2.preview.emergentagent.com').rstrip('/')

class TestPricingAPI:
    """Tests for /api/pricing endpoint"""
    
    def test_pricing_returns_200(self):
        """Test that pricing endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/pricing")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ /api/pricing returns 200")
    
    def test_pricing_has_credits_packages(self):
        """Test that pricing contains credits_packages array"""
        response = requests.get(f"{BASE_URL}/api/pricing")
        data = response.json()
        
        assert "credits_packages" in data, "Missing credits_packages"
        assert isinstance(data["credits_packages"], list), "credits_packages should be a list"
        assert len(data["credits_packages"]) >= 3, "Should have at least 3 packages"
        
        # Verify package structure
        for pkg in data["credits_packages"]:
            assert "id" in pkg, "Package missing id"
            assert "name" in pkg, "Package missing name"
            assert "credits" in pkg, "Package missing credits"
            assert "price_sar" in pkg, "Package missing price_sar"
            assert "price_usd" in pkg, "Package missing price_usd"
        
        print(f"✅ credits_packages has {len(data['credits_packages'])} packages with correct structure")
    
    def test_pricing_has_subscriptions(self):
        """Test that pricing contains subscriptions object"""
        response = requests.get(f"{BASE_URL}/api/pricing")
        data = response.json()
        
        assert "subscriptions" in data, "Missing subscriptions"
        assert isinstance(data["subscriptions"], dict), "subscriptions should be a dict"
        
        # Check for expected subscription types
        expected_subs = ["images_monthly", "videos_monthly", "all_inclusive"]
        for sub_key in expected_subs:
            assert sub_key in data["subscriptions"], f"Missing subscription: {sub_key}"
            sub = data["subscriptions"][sub_key]
            assert "name" in sub, f"{sub_key} missing name"
            assert "price_sar" in sub, f"{sub_key} missing price_sar"
            assert "features" in sub, f"{sub_key} missing features"
        
        print(f"✅ subscriptions has all expected types: {expected_subs}")
    
    def test_pricing_has_service_costs(self):
        """Test that pricing contains service_costs"""
        response = requests.get(f"{BASE_URL}/api/pricing")
        data = response.json()
        
        assert "service_costs" in data, "Missing service_costs"
        
        expected_costs = ["image_generation", "video_12_seconds", "video_60_seconds", "website_simple"]
        for cost_key in expected_costs:
            assert cost_key in data["service_costs"], f"Missing service cost: {cost_key}"
            assert isinstance(data["service_costs"][cost_key], (int, float)), f"{cost_key} should be numeric"
        
        print(f"✅ service_costs has all expected keys")
    
    def test_pricing_has_referral_rewards(self):
        """Test that pricing contains referral_rewards"""
        response = requests.get(f"{BASE_URL}/api/pricing")
        data = response.json()
        
        assert "referral_rewards" in data, "Missing referral_rewards"
        
        expected_rewards = ["inviter_bonus", "invited_bonus", "first_purchase_bonus"]
        for reward_key in expected_rewards:
            assert reward_key in data["referral_rewards"], f"Missing reward: {reward_key}"
        
        # Verify values
        assert data["referral_rewards"]["inviter_bonus"] == 30, "inviter_bonus should be 30"
        assert data["referral_rewards"]["invited_bonus"] == 20, "invited_bonus should be 20"
        
        print(f"✅ referral_rewards has correct values")


class TestUserBalanceAPI:
    """Tests for /api/user/balance endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for owner user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@zitex.com",
            "password": "owner123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_balance_requires_auth(self):
        """Test that balance endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/user/balance")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✅ /api/user/balance requires authentication")
    
    def test_balance_returns_correct_fields(self, auth_token):
        """Test that balance returns all expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/user/balance",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        expected_fields = [
            "credits", "bonus_points", "free_images", "free_videos",
            "free_website_trial", "subscription_type", "subscription_expires",
            "service_costs"
        ]
        
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify types
        assert isinstance(data["credits"], (int, float)), "credits should be numeric"
        assert isinstance(data["free_images"], int), "free_images should be int"
        assert isinstance(data["free_videos"], int), "free_videos should be int"
        assert isinstance(data["free_website_trial"], bool), "free_website_trial should be bool"
        
        print(f"✅ /api/user/balance returns all expected fields")
        print(f"   Credits: {data['credits']}, Free Images: {data['free_images']}, Free Videos: {data['free_videos']}")


class TestReferralInfoAPI:
    """Tests for /api/referral/info endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for owner user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@zitex.com",
            "password": "owner123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_referral_info_requires_auth(self):
        """Test that referral info requires authentication"""
        response = requests.get(f"{BASE_URL}/api/referral/info")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✅ /api/referral/info requires authentication")
    
    def test_referral_info_returns_correct_fields(self, auth_token):
        """Test that referral info returns all expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/referral/info",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        expected_fields = ["referral_code", "referral_link", "total_referrals", "bonus_points", "rewards"]
        
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify referral code format (8 chars uppercase)
        assert len(data["referral_code"]) == 8, "referral_code should be 8 characters"
        assert data["referral_code"].isupper(), "referral_code should be uppercase"
        
        # Verify referral link contains the code
        assert data["referral_code"] in data["referral_link"], "referral_link should contain referral_code"
        
        print(f"✅ /api/referral/info returns correct structure")
        print(f"   Referral Code: {data['referral_code']}, Total Referrals: {data['total_referrals']}")


class TestRegistrationWithReferral:
    """Tests for registration with referral code"""
    
    @pytest.fixture
    def owner_referral_code(self):
        """Get owner's referral code"""
        # Login as owner
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@zitex.com",
            "password": "owner123"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            # Get referral info
            ref_response = requests.get(
                f"{BASE_URL}/api/referral/info",
                headers={"Authorization": f"Bearer {token}"}
            )
            if ref_response.status_code == 200:
                return ref_response.json().get("referral_code")
        pytest.skip("Could not get owner referral code")
    
    def test_registration_without_referral_gives_20_points(self):
        """Test that new user without referral gets 20 signup bonus points"""
        unique_email = f"TEST_noreferral_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "test123",
            "name": "Test No Referral",
            "country": "SA"
        })
        
        assert response.status_code == 200, f"Registration failed: {response.text}"
        
        data = response.json()
        assert "user" in data, "Response missing user"
        assert "welcome_message" in data, "Response missing welcome_message"
        
        # User should have 20 points (signup bonus only)
        assert data["user"]["credits"] == 20, f"Expected 20 credits, got {data['user']['credits']}"
        assert data["user"]["bonus_points"] == 20, f"Expected 20 bonus_points, got {data['user']['bonus_points']}"
        
        print(f"✅ Registration without referral gives 20 points")
    
    def test_registration_with_referral_gives_40_points(self, owner_referral_code):
        """Test that new user with referral gets 40 points (20 signup + 20 referral)"""
        unique_email = f"TEST_withreferral_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "test123",
            "name": "Test With Referral",
            "country": "SA",
            "referral_code": owner_referral_code
        })
        
        assert response.status_code == 200, f"Registration failed: {response.text}"
        
        data = response.json()
        assert "user" in data, "Response missing user"
        
        # User should have 40 points (20 signup + 20 referral bonus)
        assert data["user"]["credits"] == 40, f"Expected 40 credits, got {data['user']['credits']}"
        assert data["user"]["bonus_points"] == 40, f"Expected 40 bonus_points, got {data['user']['bonus_points']}"
        
        # Welcome message should mention referral bonus
        assert "نقطة من الدعوة" in data.get("welcome_message", ""), "Welcome message should mention referral bonus"
        
        print(f"✅ Registration with referral gives 40 points (20 + 20)")
    
    def test_registration_with_invalid_referral_still_works(self):
        """Test that registration with invalid referral code still works (just no bonus)"""
        unique_email = f"TEST_invalidref_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "test123",
            "name": "Test Invalid Referral",
            "country": "SA",
            "referral_code": "INVALID1"
        })
        
        assert response.status_code == 200, f"Registration failed: {response.text}"
        
        data = response.json()
        # Should still get signup bonus
        assert data["user"]["credits"] == 20, f"Expected 20 credits, got {data['user']['credits']}"
        
        print(f"✅ Registration with invalid referral still works (20 points)")


class TestPricingCalculate:
    """Tests for /api/pricing/calculate endpoint"""
    
    def test_calculate_image_cost(self):
        """Test calculating image generation cost"""
        response = requests.get(f"{BASE_URL}/api/pricing/calculate?service=image_generation&quantity=5")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["service"] == "image_generation"
        assert data["quantity"] == 5
        assert data["cost_per_unit"] == 5
        assert data["total_cost"] == 25
        
        print(f"✅ /api/pricing/calculate works for image_generation")
    
    def test_calculate_video_cost(self):
        """Test calculating video generation cost"""
        response = requests.get(f"{BASE_URL}/api/pricing/calculate?service=video_60_seconds&quantity=2")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["service"] == "video_60_seconds"
        assert data["total_cost"] == 200  # 100 * 2
        
        print(f"✅ /api/pricing/calculate works for video_60_seconds")
    
    def test_calculate_invalid_service(self):
        """Test that invalid service returns 400"""
        response = requests.get(f"{BASE_URL}/api/pricing/calculate?service=invalid_service&quantity=1")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        print(f"✅ /api/pricing/calculate returns 400 for invalid service")


class TestReferralApply:
    """Tests for /api/referral/apply endpoint"""
    
    @pytest.fixture
    def new_user_token(self):
        """Create a new user and return their token"""
        unique_email = f"TEST_applyref_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": unique_email,
            "password": "test123",
            "name": "Test Apply Referral",
            "country": "SA"
        })
        
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Could not create new user")
    
    @pytest.fixture
    def owner_referral_code(self):
        """Get owner's referral code"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@zitex.com",
            "password": "owner123"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            ref_response = requests.get(
                f"{BASE_URL}/api/referral/info",
                headers={"Authorization": f"Bearer {token}"}
            )
            if ref_response.status_code == 200:
                return ref_response.json().get("referral_code")
        pytest.skip("Could not get owner referral code")
    
    def test_apply_referral_requires_auth(self):
        """Test that apply referral requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/referral/apply",
            json={"referral_code": "TESTCODE"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✅ /api/referral/apply requires authentication")
    
    def test_apply_invalid_referral_code(self, new_user_token):
        """Test that invalid referral code returns error"""
        response = requests.post(
            f"{BASE_URL}/api/referral/apply",
            headers={"Authorization": f"Bearer {new_user_token}"},
            json={"referral_code": "INVALID1"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✅ /api/referral/apply returns 400 for invalid code")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
