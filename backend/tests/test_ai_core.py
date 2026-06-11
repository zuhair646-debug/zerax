"""
AI Core Module Tests — Testing the 5-layer AI cost protection system.

Tests cover:
1. GET /api/ai-core/tiers (public) - tier catalog
2. GET /api/ai-core/usage/me (auth) - user usage stats
3. POST /api/ai-core/chat - smart model routing (cheap/standard/premium)
4. Cache functionality - same message returns cached=true
5. GET /api/ai-core/admin/stats (owner only) - platform stats
6. GET /api/ai-core/admin/cache/stats (owner only) - cache stats
7. POST /api/ai-core/admin/set-tier (owner only) - change user tier
8. Non-owner access control - 403 for admin endpoints
9. Usage cap enforcement - 402 when limit reached
10. Regression tests for existing endpoints
"""
import pytest
import requests
import os
import time
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
OWNER_EMAIL = "owner@zenrex.ai"
OWNER_PASSWORD = "owner123"

class TestAICorePublic:
    """Public endpoints - no auth required"""
    
    def test_tiers_catalog(self):
        """Test 1: GET /api/ai-core/tiers returns 5 tiers with correct structure"""
        response = requests.get(f"{BASE_URL}/api/ai-core/tiers")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "tiers" in data, "Response should have 'tiers' key"
        
        tiers = data["tiers"]
        expected_tiers = ["free", "trial", "basic", "pro", "business"]
        
        for tier_id in expected_tiers:
            assert tier_id in tiers, f"Missing tier: {tier_id}"
            tier = tiers[tier_id]
            
            # Verify required fields
            assert "price_sar" in tier, f"Tier {tier_id} missing price_sar"
            assert "chat_msgs" in tier, f"Tier {tier_id} missing chat_msgs"
            assert "images" in tier, f"Tier {tier_id} missing images"
            assert "videos" in tier, f"Tier {tier_id} missing videos"
            assert "rate_per_min" in tier, f"Tier {tier_id} missing rate_per_min"
            assert "rate_per_hour" in tier, f"Tier {tier_id} missing rate_per_hour"
            assert "label" in tier, f"Tier {tier_id} missing label"
        
        # Verify specific values
        assert tiers["free"]["price_sar"] == 0
        assert tiers["free"]["chat_msgs"] == 50
        assert tiers["business"]["price_sar"] == 299
        assert tiers["business"]["chat_msgs"] == 5000
        assert tiers["pro"]["chat_msgs"] == 2000
        assert tiers["pro"]["images"] == 100
        
        print(f"✓ Tiers catalog: {len(tiers)} tiers returned with correct structure")


class TestAICoreOwner:
    """Owner-authenticated tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as owner and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        assert response.status_code == 200, f"Owner login failed: {response.text}"
        data = response.json()
        self.token = data["token"]
        self.user = data["user"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        print(f"✓ Logged in as owner: {self.user.get('email')}")
    
    def test_usage_me_owner(self):
        """Test 2: GET /api/ai-core/usage/me returns business tier for owner"""
        response = requests.get(f"{BASE_URL}/api/ai-core/usage/me", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Owner should be auto-upgraded to business tier
        assert data["tier"] == "business", f"Owner should have business tier, got {data['tier']}"
        
        # Verify structure
        assert "chat_used" in data
        assert "chat_limit" in data
        assert "images_used" in data
        assert "images_limit" in data
        assert "videos_used" in data
        assert "videos_limit" in data
        assert "cost_usd" in data
        assert "cost_sar" in data
        assert "revenue_sar" in data
        assert "margin_sar" in data
        assert "margin_pct" in data
        assert "healthy" in data
        assert "period_start" in data
        
        # Business tier limits
        assert data["chat_limit"] == 5000
        assert data["images_limit"] == 300
        assert data["videos_limit"] == 60
        
        print(f"✓ Usage/me: tier={data['tier']}, chat_used={data['chat_used']}/{data['chat_limit']}, healthy={data['healthy']}")
    
    def test_chat_short_arabic_cheap_model(self):
        """Test 3: POST /api/ai-core/chat with short Arabic message uses cheap model"""
        response = requests.post(f"{BASE_URL}/api/ai-core/chat", 
            headers={**self.headers, "Content-Type": "application/json"},
            json={
                "message": "هلا",
                "use_cache": False  # Force fresh call to test model routing
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "reply" in data, "Response should have 'reply'"
        assert "model_tier" in data, "Response should have 'model_tier'"
        assert "cost_usd" in data, "Response should have 'cost_usd'"
        
        # Short greeting should use cheap model
        assert data["model_tier"] == "cheap", f"Short greeting should use cheap model, got {data['model_tier']}"
        assert data["cost_usd"] < 0.01, f"Cheap model cost should be very low, got {data['cost_usd']}"
        assert data["cached"] == False, "First call should not be cached"
        
        # Should return valid Arabic reply
        assert len(data["reply"]) > 0, "Reply should not be empty"
        
        print(f"✓ Chat (short): model_tier={data['model_tier']}, cost_usd={data['cost_usd']}, reply_len={len(data['reply'])}")
        
        return data  # For cache test
    
    def test_chat_cache_hit(self):
        """Test 4: POST /api/ai-core/chat with SAME message returns cached response"""
        # First call - should not be cached
        message = "مرحبا كيف حالك"
        
        response1 = requests.post(f"{BASE_URL}/api/ai-core/chat",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"message": message, "use_cache": True}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Wait a moment for cache to be written
        time.sleep(0.5)
        
        # Second call - should be cached
        response2 = requests.post(f"{BASE_URL}/api/ai-core/chat",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"message": message, "use_cache": True}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Second call should be from cache
        assert data2["model_tier"] == "cache", f"Second call should be from cache, got {data2['model_tier']}"
        assert data2["cached"] == True, "Second call should have cached=true"
        assert data2["cost_usd"] == 0, f"Cached response should have zero cost, got {data2['cost_usd']}"
        
        # Reply should be the same
        assert data2["reply"] == data1["reply"], "Cached reply should match original"
        
        print(f"✓ Cache hit: model_tier={data2['model_tier']}, cached={data2['cached']}, cost_usd={data2['cost_usd']}")
    
    def test_chat_medium_arabic_standard_model(self):
        """Test 5: POST /api/ai-core/chat with medium Arabic message uses standard model"""
        response = requests.post(f"{BASE_URL}/api/ai-core/chat",
            headers={**self.headers, "Content-Type": "application/json"},
            json={
                "message": "كيف أسوق منتج عسل؟",
                "use_cache": False
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Medium question should use standard model
        assert data["model_tier"] == "standard", f"Medium question should use standard model, got {data['model_tier']}"
        assert 0.001 <= data["cost_usd"] <= 0.05, f"Standard model cost should be moderate, got {data['cost_usd']}"
        
        # Should return detailed reply
        assert len(data["reply"]) > 50, f"Reply should be detailed, got {len(data['reply'])} chars"
        
        print(f"✓ Chat (medium): model_tier={data['model_tier']}, cost_usd={data['cost_usd']}, reply_len={len(data['reply'])}")
    
    def test_chat_long_complex_premium_model(self):
        """Test 6: POST /api/ai-core/chat with long/complex message uses premium model"""
        # Message must be >200 chars AND have complex keywords to trigger premium
        # Or have multiple question marks
        complex_message = "اشرح بالتفصيل استراتيجية تسويق شاملة لمنتج عسل فاخر في السوق السعودي، مع تحليل المنافسين وخطة إعلانات لمدة 6 أشهر وتوقع العائد المالي؟ وما هي أفضل القنوات التسويقية؟ وكيف نحسب العائد على الاستثمار؟"
        
        response = requests.post(f"{BASE_URL}/api/ai-core/chat",
            headers={**self.headers, "Content-Type": "application/json"},
            json={
                "message": complex_message,
                "use_cache": False
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Complex question with multiple ? should use premium model
        assert data["model_tier"] == "premium", f"Complex question should use premium model, got {data['model_tier']}"
        assert data["cost_usd"] > 0.005, f"Premium model should have higher cost, got {data['cost_usd']}"
        
        # Should return comprehensive reply
        assert len(data["reply"]) > 100, f"Reply should be comprehensive, got {len(data['reply'])} chars"
        
        print(f"✓ Chat (complex): model_tier={data['model_tier']}, cost_usd={data['cost_usd']}, reply_len={len(data['reply'])}")
    
    def test_admin_stats(self):
        """Test 7: GET /api/ai-core/admin/stats returns platform statistics"""
        response = requests.get(f"{BASE_URL}/api/ai-core/admin/stats?days=1", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert "total_requests" in data
        assert "cache_savings_pct" in data
        assert "total_cost_usd" in data
        assert "total_cost_sar" in data
        assert "by_tier" in data
        assert "top_consumers" in data
        assert "period_days" in data
        
        # by_tier should have breakdown
        by_tier = data["by_tier"]
        for tier in ["cheap", "standard", "premium", "cache"]:
            if tier in by_tier:
                assert "count" in by_tier[tier]
                assert "cost_usd" in by_tier[tier]
        
        # top_consumers should have user info
        if len(data["top_consumers"]) > 0:
            consumer = data["top_consumers"][0]
            assert "user_id" in consumer
            assert "email" in consumer
            assert "tier" in consumer
            assert "requests" in consumer
            assert "cost_usd" in consumer
            assert "is_losing" in consumer
        
        print(f"✓ Admin stats: total_requests={data['total_requests']}, cache_savings={data['cache_savings_pct']}%, cost_sar={data['total_cost_sar']}")
    
    def test_admin_cache_stats(self):
        """Test 8: GET /api/ai-core/admin/cache/stats returns cache statistics"""
        response = requests.get(f"{BASE_URL}/api/ai-core/admin/cache/stats", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert "total_cached_entries" in data
        assert "total_cache_hits" in data
        assert "top_cached_questions" in data
        
        # top_cached_questions should have question info
        if len(data["top_cached_questions"]) > 0:
            q = data["top_cached_questions"][0]
            assert "sample_question" in q
            assert "hits" in q
        
        print(f"✓ Cache stats: entries={data['total_cached_entries']}, hits={data['total_cache_hits']}")
    
    def test_admin_set_tier(self):
        """Test 9: POST /api/ai-core/admin/set-tier updates user tier"""
        # First, get the owner's user_id
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=self.headers)
        assert me_response.status_code == 200
        user_id = me_response.json()["id"]
        
        # Set tier to 'pro'
        response = requests.post(f"{BASE_URL}/api/ai-core/admin/set-tier",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"user_id": user_id, "tier": "pro"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["ok"] == True
        assert data["tier"] == "pro"
        
        # Verify the change (note: owner still gets business tier due to is_owner flag)
        # But the ai_tier field should be updated
        
        # Reset back (optional - owner auto-upgrades anyway)
        requests.post(f"{BASE_URL}/api/ai-core/admin/set-tier",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"user_id": user_id, "tier": "business"}
        )
        
        print(f"✓ Set tier: user_id={user_id[:8]}..., tier=pro (then reset)")


class TestAICoreNonOwner:
    """Non-owner access control tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Register a test user"""
        import uuid
        self.test_email = f"test_aicore_{uuid.uuid4().hex[:8]}@test.com"
        self.test_password = "testpass123"
        
        # Register
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": self.test_email,
            "password": self.test_password,
            "name": "Test AI Core User",
            "country": "SA"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        self.token = data["token"]
        self.user = data["user"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        print(f"✓ Registered test user: {self.test_email}")
    
    def test_non_owner_admin_stats_403(self):
        """Test 10a: Non-owner cannot access admin stats"""
        response = requests.get(f"{BASE_URL}/api/ai-core/admin/stats", headers=self.headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Non-owner gets 403 on admin/stats")
    
    def test_non_owner_set_tier_403(self):
        """Test 10b: Non-owner cannot set tier"""
        response = requests.post(f"{BASE_URL}/api/ai-core/admin/set-tier",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"user_id": self.user["id"], "tier": "pro"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Non-owner gets 403 on admin/set-tier")
    
    def test_non_owner_cache_stats_403(self):
        """Test 10c: Non-owner cannot access cache stats"""
        response = requests.get(f"{BASE_URL}/api/ai-core/admin/cache/stats", headers=self.headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Non-owner gets 403 on admin/cache/stats")
    
    def test_non_owner_can_use_chat(self):
        """Non-owner can still use chat endpoint"""
        response = requests.post(f"{BASE_URL}/api/ai-core/chat",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"message": "مرحبا", "use_cache": True}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Non-owner can use chat endpoint")
    
    def test_non_owner_can_view_usage(self):
        """Non-owner can view their own usage"""
        response = requests.get(f"{BASE_URL}/api/ai-core/usage/me", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # New user should have free tier
        assert data["tier"] == "free", f"New user should have free tier, got {data['tier']}"
        assert data["chat_limit"] == 50, "Free tier should have 50 chat msgs"
        
        print(f"✓ Non-owner usage: tier={data['tier']}, limit={data['chat_limit']}")


class TestAICoreUsageCap:
    """Usage cap enforcement tests"""
    
    def test_usage_cap_enforcement(self):
        """Test 12: User hitting usage cap gets 402"""
        # This test requires direct MongoDB access to simulate hitting the cap
        # We'll use pymongo to insert 50 logs for a test user
        
        from pymongo import MongoClient
        import uuid
        
        # Connect to MongoDB
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'test_database')
        client = MongoClient(mongo_url)
        db = client[db_name]
        
        # Create a test user
        test_email = f"test_cap_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "testpass123"
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": test_password,
            "name": "Test Cap User",
            "country": "SA"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        token = data["token"]
        user_id = data["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Set user to free tier (50 chat msgs)
        # First login as owner to set tier
        owner_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        owner_token = owner_response.json()["token"]
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        
        requests.post(f"{BASE_URL}/api/ai-core/admin/set-tier",
            headers={**owner_headers, "Content-Type": "application/json"},
            json={"user_id": user_id, "tier": "free"}
        )
        
        # Insert 50 logs for this user in current month
        period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        logs = []
        for i in range(50):
            logs.append({
                "user_id": user_id,
                "tier": "free",
                "context_tag": "general",
                "message_length": 10,
                "model_tier": "cheap",
                "tokens_in": 10,
                "tokens_out": 20,
                "cost_usd": 0.0001,
                "cached": False,
                "created_at": period_start.isoformat()
            })
        
        db.ai_core_logs.insert_many(logs)
        print(f"✓ Inserted 50 logs for user {user_id[:8]}...")
        
        # Now try to chat - should get 402
        response = requests.post(f"{BASE_URL}/api/ai-core/chat",
            headers={**headers, "Content-Type": "application/json"},
            json={"message": "مرحبا", "use_cache": False}
        )
        
        # Clean up logs
        db.ai_core_logs.delete_many({"user_id": user_id})
        
        assert response.status_code == 402, f"Expected 402 (payment required), got {response.status_code}: {response.text}"
        
        # Verify error message mentions limit
        error_detail = response.json().get("detail", "")
        assert "الحد" in error_detail or "limit" in error_detail.lower(), f"Error should mention limit: {error_detail}"
        
        print(f"✓ Usage cap enforced: 402 returned with message about limit")


class TestRegressionExistingEndpoints:
    """Test 14: Regression tests for existing endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as owner"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_auth_me_still_works(self):
        """Existing /api/auth/me endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "id" in data
        assert "email" in data
        print("✓ /api/auth/me still works")
    
    def test_avatar_chat_still_works(self):
        """Existing /api/avatar/chat endpoint still works"""
        # Get a project first
        projects_response = requests.get(f"{BASE_URL}/api/bridge/projects", headers=self.headers)
        if projects_response.status_code == 200:
            projects = projects_response.json().get("projects", [])
            if len(projects) > 0:
                project_id = projects[0]["id"]
                response = requests.post(f"{BASE_URL}/api/avatar/chat",
                    headers={**self.headers, "Content-Type": "application/json"},
                    json={"project_id": project_id, "message": "مرحبا"}
                )
                # Should work or return expected error (not 500)
                assert response.status_code in [200, 400, 404], f"Unexpected status: {response.status_code}"
                print(f"✓ /api/avatar/chat still works (status={response.status_code})")
            else:
                print("⚠ No projects found, skipping avatar/chat test")
        else:
            print("⚠ Could not get projects, skipping avatar/chat test")
    
    def test_wizard_video_start_still_works(self):
        """Existing /api/wizard/video/start endpoint still works"""
        response = requests.post(f"{BASE_URL}/api/wizard/video/start",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"category": "product"}
        )
        # Should work or return expected error (not 500)
        assert response.status_code in [200, 400, 404], f"Unexpected status: {response.status_code}"
        print(f"✓ /api/wizard/video/start still works (status={response.status_code})")
    
    def test_studio_credits_still_works(self):
        """Existing /api/studio/credits endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/studio/credits", headers=self.headers)
        # Should work or return expected error (not 500)
        assert response.status_code in [200, 400, 404], f"Unexpected status: {response.status_code}"
        print(f"✓ /api/studio/credits still works (status={response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
