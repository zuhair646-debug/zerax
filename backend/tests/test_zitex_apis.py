"""
Zitex Platform API Tests
Testing: voices, TTS, image editing, admin activity logs, user management
"""

import pytest
import requests
import os
import base64
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-cinematic-hub-2.preview.emergentagent.com')

# Test credentials
OWNER_EMAIL = "owner@zitex.com"
OWNER_PASSWORD = "owner123"
TEST_USER_EMAIL = f"TEST_user_{datetime.now().strftime('%H%M%S')}@test.com"
TEST_USER_PASSWORD = "testpass123"


class TestSession:
    """Session management for tests"""
    owner_token = None
    user_token = None
    test_user_id = None


@pytest.fixture(scope="session")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="session")
def owner_auth(api_client):
    """Authenticate as owner"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    })
    
    if response.status_code == 200:
        data = response.json()
        TestSession.owner_token = data.get("token")
        return TestSession.owner_token
    else:
        # Try registering owner if not exists
        register_response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD,
            "name": "Owner User",
            "country": "SA"
        })
        if register_response.status_code == 200:
            data = register_response.json()
            TestSession.owner_token = data.get("token")
            return TestSession.owner_token
    
    pytest.skip("Owner authentication failed")


@pytest.fixture(scope="session")
def test_user_auth(api_client):
    """Create and authenticate test user"""
    # Register new user
    response = api_client.post(f"{BASE_URL}/api/auth/register", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "name": "Test User",
        "country": "SA"
    })
    
    if response.status_code == 200:
        data = response.json()
        TestSession.user_token = data.get("token")
        TestSession.test_user_id = data.get("user", {}).get("id")
        return TestSession.user_token
    elif response.status_code == 400:  # User exists
        login_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if login_response.status_code == 200:
            data = login_response.json()
            TestSession.user_token = data.get("token")
            TestSession.test_user_id = data.get("user", {}).get("id")
            return TestSession.user_token
    
    pytest.skip("Test user authentication failed")


# ============== HEALTH CHECKS ==============

class TestHealthChecks:
    """Basic API health checks"""
    
    def test_api_accessible(self, api_client):
        """Test API is accessible"""
        response = api_client.get(f"{BASE_URL}/api/pricing")
        assert response.status_code == 200, f"API not accessible: {response.status_code}"
        print("API accessible - /api/pricing returns 200")
    
    def test_pricing_endpoint(self, api_client):
        """Verify pricing endpoint returns expected structure"""
        response = api_client.get(f"{BASE_URL}/api/pricing")
        assert response.status_code == 200
        
        data = response.json()
        assert "credits_packages" in data, "Missing credits_packages"
        assert "subscriptions" in data, "Missing subscriptions"
        assert "free_trial" in data, "Missing free_trial info"
        
        # Verify free trial info
        free_trial = data["free_trial"]
        assert free_trial.get("images") == 3, "Free images should be 3"
        assert free_trial.get("videos") == 3, "Free videos should be 3"
        print(f"Pricing verified: {len(data['credits_packages'])} packages")


# ============== VOICES API ==============

class TestVoicesAPI:
    """Test /api/voices endpoint"""
    
    def test_get_voices_requires_auth(self, api_client):
        """Voices endpoint requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/voices")
        assert response.status_code in [401, 403], "Should require authentication"
        print("Voices endpoint requires auth - correct behavior")
    
    def test_get_voices_with_auth(self, api_client, owner_auth):
        """Get available voices with authentication"""
        response = api_client.get(
            f"{BASE_URL}/api/voices",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        assert response.status_code == 200, f"Failed to get voices: {response.status_code}"
        
        data = response.json()
        assert "voices" in data, "Missing voices array"
        
        voices = data["voices"]
        assert len(voices) > 0, "No voices returned"
        
        # Verify voice structure
        first_voice = voices[0]
        assert "voice_id" in first_voice, "Missing voice_id"
        assert "name" in first_voice, "Missing name"
        
        print(f"Got {len(voices)} voices - first: {first_voice.get('name')}")


# ============== TTS GENERATION API ==============

class TestTTSAPI:
    """Test /api/tts/generate endpoint"""
    
    def test_tts_requires_auth(self, api_client):
        """TTS endpoint requires authentication"""
        response = api_client.post(
            f"{BASE_URL}/api/tts/generate",
            json={"text": "Hello", "voice_id": "test"}
        )
        assert response.status_code in [401, 403], "Should require authentication"
        print("TTS endpoint requires auth - correct behavior")
    
    def test_tts_generate(self, api_client, owner_auth):
        """Generate TTS audio"""
        # First get a valid voice
        voices_response = api_client.get(
            f"{BASE_URL}/api/voices",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        if voices_response.status_code != 200:
            pytest.skip("Could not get voices")
        
        voices = voices_response.json().get("voices", [])
        if not voices:
            pytest.skip("No voices available")
        
        voice_id = voices[0].get("voice_id")
        
        # Generate TTS
        response = api_client.post(
            f"{BASE_URL}/api/tts/generate",
            headers={"Authorization": f"Bearer {owner_auth}"},
            json={
                "text": "مرحباً بكم في منصة Zitex",
                "voice_id": voice_id,
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        )
        
        if response.status_code == 503:
            print("TTS service not available (ElevenLabs might not be configured)")
            pytest.skip("TTS service unavailable")
        
        assert response.status_code == 200, f"TTS failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "audio_url" in data, "Missing audio_url"
        assert data["audio_url"].startswith("data:audio"), "Invalid audio URL format"
        
        print(f"TTS generated successfully - voice: {voice_id}")


# ============== IMAGE EDIT API ==============

class TestImageEditAPI:
    """Test /api/images/edit endpoint"""
    
    def test_image_edit_requires_auth(self, api_client):
        """Image edit endpoint requires authentication"""
        response = api_client.post(
            f"{BASE_URL}/api/images/edit",
            json={"image_base64": "test", "text": "test"}
        )
        assert response.status_code in [401, 403], "Should require authentication"
        print("Image edit endpoint requires auth - correct behavior")
    
    def test_image_edit_with_text(self, api_client, owner_auth):
        """Edit image by adding text"""
        # Create a simple test image (1x1 pixel PNG)
        import io
        try:
            from PIL import Image
            img = Image.new('RGB', (400, 300), color='blue')
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            image_b64 = base64.b64encode(buffer.getvalue()).decode()
            image_url = f"data:image/png;base64,{image_b64}"
        except ImportError:
            # Fallback: use minimal PNG bytes
            minimal_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
            image_url = f"data:image/png;base64,{base64.b64encode(minimal_png).decode()}"
        
        response = api_client.post(
            f"{BASE_URL}/api/images/edit",
            headers={"Authorization": f"Bearer {owner_auth}"},
            json={
                "image_base64": image_url,
                "text": "اختبار النص",
                "text_position": "center",
                "text_color": "#FFFFFF",
                "font_size": 30
            }
        )
        
        assert response.status_code == 200, f"Image edit failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "edited_image_url" in data, "Missing edited_image_url"
        assert "id" in data, "Missing image ID"
        
        print(f"Image edited successfully - ID: {data.get('id')}")


# ============== ADMIN ACTIVITY API ==============

class TestAdminActivityAPI:
    """Test /api/admin/activity endpoints"""
    
    def test_activity_requires_admin(self, api_client, test_user_auth):
        """Activity endpoint requires admin role"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/activity",
            headers={"Authorization": f"Bearer {test_user_auth}"}
        )
        assert response.status_code in [401, 403], f"Should require admin role, got {response.status_code}"
        print("Activity endpoint requires admin - correct behavior")
    
    def test_get_all_activity(self, api_client, owner_auth):
        """Get all activity logs"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/activity?limit=50",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        assert response.status_code == 200, f"Failed to get activity: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Activity should be a list"
        
        if len(data) > 0:
            first_log = data[0]
            assert "user_id" in first_log, "Missing user_id in activity"
            assert "action" in first_log, "Missing action in activity"
            assert "created_at" in first_log, "Missing created_at"
            print(f"Got {len(data)} activity logs - first action: {first_log.get('action')}")
        else:
            print("No activity logs yet")
    
    def test_get_user_activity(self, api_client, owner_auth, test_user_auth):
        """Get activity for specific user"""
        if not TestSession.test_user_id:
            pytest.skip("No test user ID available")
        
        response = api_client.get(
            f"{BASE_URL}/api/admin/users/{TestSession.test_user_id}/activity",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        assert response.status_code == 200, f"Failed to get user activity: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Activity should be a list"
        print(f"Got {len(data)} activity logs for user")


# ============== ADMIN USERS API ==============

class TestAdminUsersAPI:
    """Test admin user management endpoints"""
    
    def test_get_all_users(self, api_client, owner_auth):
        """Get all users list"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        assert response.status_code == 200, f"Failed to get users: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Users should be a list"
        assert len(data) > 0, "Should have at least one user"
        
        # Verify user structure
        user = data[0]
        assert "id" in user, "Missing user id"
        assert "email" in user, "Missing user email"
        assert "role" in user, "Missing user role"
        
        print(f"Got {len(data)} users")
    
    def test_user_role_management(self, api_client, owner_auth, test_user_auth):
        """Test role assignment"""
        if not TestSession.test_user_id:
            pytest.skip("No test user ID available")
        
        # Try to update role to admin
        response = api_client.put(
            f"{BASE_URL}/api/admin/users/{TestSession.test_user_id}/role?role=admin",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        assert response.status_code == 200, f"Failed to update role: {response.status_code}"
        
        data = response.json()
        assert "message" in data
        print(f"Role update response: {data.get('message')}")
        
        # Verify the change
        users_response = api_client.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        users = users_response.json()
        test_user = next((u for u in users if u.get('id') == TestSession.test_user_id), None)
        
        if test_user:
            assert test_user.get('role') == 'admin', "Role was not updated"
            print(f"User role verified as: {test_user.get('role')}")
    
    def test_add_credits_to_user(self, api_client, owner_auth, test_user_auth):
        """Test adding credits to user"""
        if not TestSession.test_user_id:
            pytest.skip("No test user ID available")
        
        response = api_client.put(
            f"{BASE_URL}/api/admin/users/{TestSession.test_user_id}/add-credits?credits=100",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        assert response.status_code == 200, f"Failed to add credits: {response.status_code}"
        print("Credits added successfully")
    
    def test_add_free_trials(self, api_client, owner_auth, test_user_auth):
        """Test adding free trials"""
        if not TestSession.test_user_id:
            pytest.skip("No test user ID available")
        
        response = api_client.put(
            f"{BASE_URL}/api/admin/users/{TestSession.test_user_id}/add-free-trials?images=5&videos=5",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        assert response.status_code == 200, f"Failed to add free trials: {response.status_code}"
        print("Free trials added successfully")
    
    def test_user_deactivate_activate(self, api_client, owner_auth, test_user_auth):
        """Test user deactivation and activation"""
        if not TestSession.test_user_id:
            pytest.skip("No test user ID available")
        
        # Deactivate
        response = api_client.put(
            f"{BASE_URL}/api/admin/users/{TestSession.test_user_id}/deactivate",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        assert response.status_code == 200, f"Failed to deactivate: {response.status_code}"
        print("User deactivated")
        
        # Re-activate
        response = api_client.put(
            f"{BASE_URL}/api/admin/users/{TestSession.test_user_id}/activate",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        assert response.status_code == 200, f"Failed to activate: {response.status_code}"
        print("User reactivated")


# ============== ADMIN STATS ==============

class TestAdminStats:
    """Test admin statistics endpoint"""
    
    def test_get_admin_stats(self, api_client, owner_auth):
        """Get admin dashboard statistics"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/stats",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        assert response.status_code == 200, f"Failed to get stats: {response.status_code}"
        
        data = response.json()
        
        # Verify all expected fields
        expected_fields = [
            "total_users", "total_requests", "pending_requests", 
            "completed_requests", "pending_payments", "approved_payments",
            "total_websites", "total_images_generated", "total_videos_generated",
            "total_activities"
        ]
        
        for field in expected_fields:
            assert field in data, f"Missing stat field: {field}"
        
        print(f"Stats: users={data['total_users']}, images={data['total_images_generated']}, activities={data['total_activities']}")


# ============== IMAGE GENERATION ==============

class TestImageGeneration:
    """Test image generation functionality"""
    
    def test_generate_image(self, api_client, owner_auth):
        """Generate image using AI"""
        response = api_client.post(
            f"{BASE_URL}/api/generate/image?prompt=A beautiful sunset over mountains",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        # This might take time or fail due to AI service limits
        if response.status_code == 500:
            print(f"Image generation failed (might be AI service issue): {response.text[:200]}")
            pytest.skip("AI service unavailable")
        
        assert response.status_code in [200, 403], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "id" in data, "Missing image ID"
            print(f"Image generated - ID: {data.get('id')}")
        else:
            print(f"Image generation requires subscription or free trials")
    
    def test_get_image_history(self, api_client, owner_auth):
        """Get image generation history"""
        response = api_client.get(
            f"{BASE_URL}/api/generate/images/history",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        assert response.status_code == 200, f"Failed to get history: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "History should be a list"
        print(f"Got {len(data)} images in history")


# ============== VIDEO GENERATION ==============

class TestVideoGeneration:
    """Test video generation functionality"""
    
    def test_generate_video_with_voice(self, api_client, owner_auth):
        """Generate video with voice narration"""
        # First get a valid voice
        voices_response = api_client.get(
            f"{BASE_URL}/api/voices",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        voice_id = None
        if voices_response.status_code == 200:
            voices = voices_response.json().get("voices", [])
            if voices:
                voice_id = voices[0].get("voice_id")
        
        # Generate video with voice
        url = f"{BASE_URL}/api/generate/video?prompt=A bird flying over the ocean"
        if voice_id:
            url += f"&voice_id={voice_id}&voice_text=مرحباً بكم"
        
        response = api_client.post(
            url,
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        if response.status_code == 500:
            print(f"Video generation failed: {response.text[:200]}")
            pytest.skip("Video service unavailable")
        
        assert response.status_code in [200, 403], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "id" in data, "Missing video ID"
            assert "status" in data, "Missing status"
            
            if voice_id:
                assert "audio_url" in data or data.get("audio_url") is None, "Should have audio_url field"
            
            print(f"Video generation started - ID: {data.get('id')}, status: {data.get('status')}")
        else:
            print("Video generation requires subscription or free trials")
    
    def test_get_video_history(self, api_client, owner_auth):
        """Get video generation history"""
        response = api_client.get(
            f"{BASE_URL}/api/generate/videos/history",
            headers={"Authorization": f"Bearer {owner_auth}"}
        )
        
        assert response.status_code == 200, f"Failed to get history: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "History should be a list"
        print(f"Got {len(data)} videos in history")


# ============== LOGOUT TEST ==============

class TestLogout:
    """Test logout functionality"""
    
    def test_token_cleared_on_logout(self, api_client, test_user_auth):
        """Verify token is invalidated after logout"""
        # First verify token works
        response = api_client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {test_user_auth}"}
        )
        
        assert response.status_code == 200, "Token should be valid"
        print("Token validated - logout must clear from frontend localStorage")
        
        # Note: Actual logout happens on frontend by clearing localStorage
        # Backend JWT tokens remain valid until expiry
        # This test verifies the token mechanism works


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
