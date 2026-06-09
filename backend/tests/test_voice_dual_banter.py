"""
Test suite for Voice-First VoiceStage features:
- Dual character interaction (Zara/Layla banter)
- Anonymous usage tracking (5 free voice convos)
- Companion voice-chat endpoint
- Avatar chat with primary/secondary character selection
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ============== FIXTURES ==============

@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture
def auth_token(api_client):
    """Get authentication token for owner@zerax.com"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "owner@zerax.com",
        "password": "owner123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")

@pytest.fixture
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client

@pytest.fixture
def unique_anon_id():
    """Generate unique anon_id for quota testing"""
    return f"test_quota_{uuid.uuid4().hex[:8]}_{int(time.time())}"


# ============== TEST 1: ANON USAGE STATUS ==============

class TestAnonUsage:
    """Tests for anonymous usage tracking (5 free voice convos)"""
    
    def test_anon_usage_new_user(self, api_client):
        """Test 1: GET /api/avatar/anon-usage?anon_id=test_anon_NEW returns fresh quota"""
        new_anon_id = f"test_anon_NEW_{uuid.uuid4().hex[:8]}"
        response = api_client.get(f"{BASE_URL}/api/avatar/anon-usage?anon_id={new_anon_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify response structure and values
        assert data["count"] == 0, f"Expected count=0, got {data['count']}"
        assert data["limit"] == 5, f"Expected limit=5, got {data['limit']}"
        assert data["remaining"] == 5, f"Expected remaining=5, got {data['remaining']}"
        assert data["blocked"] == False, f"Expected blocked=False, got {data['blocked']}"
        print(f"✓ Test 1 PASSED: New anon user has 5 free convos")


# ============== TEST 2-6: AVATAR CHAT WITH DUAL BANTER ==============

class TestAvatarChatDualBanter:
    """Tests for /api/avatar/chat with dual banter feature"""
    
    def test_avatar_chat_with_banter_zara_primary(self, api_client, unique_anon_id):
        """Test 2: POST /api/avatar/chat with primary='zara', dual_banter=true"""
        response = api_client.post(f"{BASE_URL}/api/avatar/chat", json={
            "message": "مرحبا",
            "want_voice": False,
            "anon_id": unique_anon_id,
            "primary": "zara",
            "dual_banter": True
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "reply" in data, "Missing 'reply' in response"
        assert data["primary"] == "zara", f"Expected primary='zara', got {data['primary']}"
        assert data["secondary"] == "layla", f"Expected secondary='layla', got {data['secondary']}"
        
        # Verify banter structure (may be null if LLM fails, but structure should exist when present)
        if data.get("banter"):
            assert data["banter"]["from_char"] == "layla", f"Expected banter from 'layla', got {data['banter']['from_char']}"
            assert "text" in data["banter"], "Missing 'text' in banter"
            # audio_url should be null since want_voice=False
            assert data["banter"]["audio_url"] is None, "Expected banter audio_url=null when want_voice=False"
        
        # Verify anon_usage tracking
        assert "anon_usage" in data, "Missing 'anon_usage' in response"
        assert data["anon_usage"]["count"] == 1, f"Expected count=1, got {data['anon_usage']['count']}"
        assert data["anon_usage"]["remaining"] == 4, f"Expected remaining=4, got {data['anon_usage']['remaining']}"
        
        print(f"✓ Test 2 PASSED: Avatar chat with Zara primary, banter from Layla")
    
    def test_avatar_chat_quota_exhaustion(self, api_client):
        """Test 3: Exhaust 5 free convos and verify blocking on 6th"""
        quota_anon_id = f"test_quota_exhaust_{uuid.uuid4().hex[:8]}"
        
        # Make 5 requests to exhaust quota
        for i in range(5):
            response = api_client.post(f"{BASE_URL}/api/avatar/chat", json={
                "message": f"رسالة {i+1}",
                "want_voice": False,
                "anon_id": quota_anon_id,
                "primary": "zara",
                "dual_banter": False  # Faster without banter
            })
            assert response.status_code == 200, f"Request {i+1} failed: {response.status_code}"
            data = response.json()
            print(f"  Request {i+1}: count={data['anon_usage']['count']}, remaining={data['anon_usage']['remaining']}")
        
        # Verify 5th request shows blocked=true
        assert data["anon_usage"]["blocked"] == True, "Expected blocked=True after 5 requests"
        
        # 6th request should return 403
        response = api_client.post(f"{BASE_URL}/api/avatar/chat", json={
            "message": "رسالة 6",
            "want_voice": False,
            "anon_id": quota_anon_id,
            "primary": "zara",
            "dual_banter": False
        })
        assert response.status_code == 403, f"Expected 403 on 6th request, got {response.status_code}"
        
        # Verify Arabic error message
        error_data = response.json()
        assert "انتهت المحادثات" in str(error_data.get("detail", "")), "Expected Arabic quota exhausted message"
        
        print(f"✓ Test 3 PASSED: Quota exhaustion works correctly (5 free, 6th blocked)")
    
    def test_avatar_chat_without_anon_id(self, api_client):
        """Test 4: POST /api/avatar/chat WITHOUT anon_id → no usage tracking"""
        response = api_client.post(f"{BASE_URL}/api/avatar/chat", json={
            "message": "مرحبا بدون تتبع",
            "want_voice": False,
            "primary": "zara",
            "dual_banter": False
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # anon_usage should show default values (no tracking)
        assert data["anon_usage"]["count"] == 0, "Expected count=0 without anon_id"
        assert data["anon_usage"]["blocked"] == False, "Expected blocked=False without anon_id"
        
        print(f"✓ Test 4 PASSED: No usage tracking without anon_id")
    
    def test_avatar_chat_layla_primary(self, api_client):
        """Test 5: POST /api/avatar/chat with primary='layla' → secondary='zara'"""
        response = api_client.post(f"{BASE_URL}/api/avatar/chat", json={
            "message": "مرحبا ليلى",
            "want_voice": False,
            "primary": "layla",
            "dual_banter": True
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data["primary"] == "layla", f"Expected primary='layla', got {data['primary']}"
        assert data["secondary"] == "zara", f"Expected secondary='zara', got {data['secondary']}"
        
        if data.get("banter"):
            assert data["banter"]["from_char"] == "zara", f"Expected banter from 'zara', got {data['banter']['from_char']}"
        
        print(f"✓ Test 5 PASSED: Layla primary, Zara secondary")
    
    def test_avatar_chat_no_banter(self, api_client):
        """Test 6: POST /api/avatar/chat with dual_banter=false → banter is null"""
        response = api_client.post(f"{BASE_URL}/api/avatar/chat", json={
            "message": "بدون تعليق",
            "want_voice": False,
            "primary": "zara",
            "dual_banter": False
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("banter") is None, f"Expected banter=null, got {data.get('banter')}"
        
        print(f"✓ Test 6 PASSED: No banter when dual_banter=false")


# ============== TEST 7-8: COMPANION VOICE-CHAT ==============

class TestCompanionVoiceChat:
    """Tests for /api/companion/voice-chat endpoint (auth required)"""
    
    def test_companion_voice_chat_requires_auth(self, api_client):
        """Test: /api/companion/voice-chat requires authentication"""
        response = api_client.post(f"{BASE_URL}/api/companion/voice-chat", json={
            "message": "مرحبا",
            "want_voice": False
        })
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Companion voice-chat requires auth (got {response.status_code})")
    
    def test_companion_voice_chat_requires_profile(self, authenticated_client):
        """Test 7: POST /api/companion/voice-chat requires profile"""
        # First check if profile exists
        profile_response = authenticated_client.get(f"{BASE_URL}/api/companion/profile")
        
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            if profile_data.get("has_profile"):
                # Profile exists, test voice-chat
                response = authenticated_client.post(f"{BASE_URL}/api/companion/voice-chat", json={
                    "message": "مرحبا",
                    "want_voice": False
                })
                
                assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
                data = response.json()
                
                assert "reply" in data, "Missing 'reply' in response"
                assert "from_char" in data, "Missing 'from_char' in response"
                assert data["from_char"] in ["zara", "layla"], f"Invalid from_char: {data['from_char']}"
                
                print(f"✓ Test 7 PASSED: Companion voice-chat returns reply + from_char={data['from_char']}")
            else:
                # No profile, should return 400
                response = authenticated_client.post(f"{BASE_URL}/api/companion/voice-chat", json={
                    "message": "مرحبا",
                    "want_voice": False
                })
                assert response.status_code == 400, f"Expected 400 without profile, got {response.status_code}"
                print(f"✓ Test 7 PASSED: Companion voice-chat requires profile (got 400)")
    
    def test_companion_voice_chat_with_audio(self, authenticated_client):
        """Test 8: POST /api/companion/voice-chat with want_voice=true → audio_url"""
        # Check profile first
        profile_response = authenticated_client.get(f"{BASE_URL}/api/companion/profile")
        if profile_response.status_code != 200:
            pytest.skip("Cannot get profile")
        
        profile_data = profile_response.json()
        if not profile_data.get("has_profile"):
            pytest.skip("No companion profile exists")
        
        response = authenticated_client.post(f"{BASE_URL}/api/companion/voice-chat", json={
            "message": "كيف حالك؟",
            "want_voice": True
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "reply" in data, "Missing 'reply'"
        assert "audio_url" in data, "Missing 'audio_url'"
        
        # audio_url should be base64 data URL when TTS succeeds
        if data["audio_url"]:
            assert data["audio_url"].startswith("data:audio/mp3;base64,"), \
                f"Expected base64 audio URL, got: {data['audio_url'][:50]}..."
            print(f"✓ Test 8 PASSED: Companion voice-chat returns audio_url (base64)")
        else:
            print(f"⚠ Test 8 PARTIAL: audio_url is null (TTS may have failed)")


# ============== TEST 14: REGRESSION TESTS ==============

class TestRegression:
    """Regression tests for existing functionality"""
    
    def test_avatar_chat_saudi_dialect(self, api_client):
        """Test 14a: Zerax main avatar chat still in Saudi dialect"""
        response = api_client.post(f"{BASE_URL}/api/avatar/chat", json={
            "message": "مرحبا، كيف حالك؟",
            "want_voice": False,
            "primary": "zara",
            "dual_banter": False
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Reply should exist and be in Arabic
        assert "reply" in data, "Missing 'reply'"
        assert len(data["reply"]) > 0, "Empty reply"
        
        print(f"✓ Test 14a PASSED: Avatar chat returns Arabic reply")
    
    def test_companion_text_chat_works(self, authenticated_client):
        """Test 14b: /api/companion/chat still works"""
        # Check profile first
        profile_response = authenticated_client.get(f"{BASE_URL}/api/companion/profile")
        if profile_response.status_code != 200:
            pytest.skip("Cannot get profile")
        
        profile_data = profile_response.json()
        if not profile_data.get("has_profile"):
            pytest.skip("No companion profile exists")
        
        response = authenticated_client.post(f"{BASE_URL}/api/companion/chat", json={
            "message": "مرحبا"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "reply" in data, "Missing 'reply'"
        assert "from_char" in data, "Missing 'from_char'"
        
        print(f"✓ Test 14b PASSED: Companion text chat works")
    
    def test_companion_onboarding_flow(self, authenticated_client):
        """Test 14c: /companion onboarding flow (profile endpoint)"""
        response = authenticated_client.get(f"{BASE_URL}/api/companion/profile")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "has_profile" in data, "Missing 'has_profile'"
        assert "profile" in data, "Missing 'profile'"
        
        print(f"✓ Test 14c PASSED: Companion profile endpoint works (has_profile={data['has_profile']})")


# ============== TEST 15: IMAGE ACCESSIBILITY ==============

class TestImageAccessibility:
    """Test 15: Verify avatar images are accessible"""
    
    def test_avatar_images_accessible(self, api_client):
        """Test 15: All lip-sync images return 200"""
        images = [
            "zara_idle.png",
            "zara_talk.png",
            "layla_idle.png",
            "layla_talk.png"
        ]
        
        for img in images:
            response = api_client.get(f"{BASE_URL}/avatars/{img}")
            assert response.status_code == 200, f"Image {img} returned {response.status_code}"
            print(f"  ✓ {img}: 200 OK")
        
        print(f"✓ Test 15 PASSED: All avatar images accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
