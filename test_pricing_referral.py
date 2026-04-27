"""
Zitex AI Chat API Tests
Tests for the new chat system including:
- Session management (create, get, delete)
- Message sending and AI responses
- Voices endpoint
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-cinematic-hub-2.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "owner@zitex.com"
TEST_PASSWORD = "owner123"


class TestChatAPIs:
    """Chat API endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        self.token = data.get("token")
        self.user_id = data.get("user", {}).get("id")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
        
        # Cleanup - no specific cleanup needed
    
    # ============== Session Management Tests ==============
    
    def test_create_session_general(self):
        """Test creating a general chat session"""
        response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "general",
            "title": "TEST_General Chat Session"
        })
        
        assert response.status_code == 200, f"Create session failed: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert data["session_type"] == "general"
        assert data["status"] == "active"
        assert "created_at" in data
        assert "updated_at" in data
        print(f"✓ Created general session: {data['id']}")
        
        # Store for cleanup
        self.created_session_id = data["id"]
    
    def test_create_session_image_type(self):
        """Test creating an image-focused chat session"""
        response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "image",
            "title": "TEST_Image Generation Session"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_type"] == "image"
        print(f"✓ Created image session: {data['id']}")
    
    def test_create_session_video_type(self):
        """Test creating a video-focused chat session"""
        response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "video",
            "title": "TEST_Video Generation Session"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_type"] == "video"
        print(f"✓ Created video session: {data['id']}")
    
    def test_create_session_website_type(self):
        """Test creating a website-focused chat session"""
        response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "website",
            "title": "TEST_Website Building Session"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_type"] == "website"
        print(f"✓ Created website session: {data['id']}")
    
    def test_get_user_sessions(self):
        """Test retrieving user's chat sessions"""
        response = self.session.get(f"{BASE_URL}/api/chat/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Check session structure
        if len(data) > 0:
            session = data[0]
            assert "id" in session
            assert "title" in session
            assert "session_type" in session
            assert "status" in session
            assert "message_count" in session
        
        print(f"✓ Retrieved {len(data)} sessions")
    
    def test_get_specific_session(self):
        """Test retrieving a specific session with messages"""
        # First create a session
        create_response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "general",
            "title": "TEST_Session for Retrieval"
        })
        session_id = create_response.json()["id"]
        
        # Get the session
        response = self.session.get(f"{BASE_URL}/api/chat/sessions/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert "messages" in data
        assert isinstance(data["messages"], list)
        print(f"✓ Retrieved session {session_id} with {len(data['messages'])} messages")
    
    def test_get_nonexistent_session(self):
        """Test retrieving a non-existent session returns 404"""
        response = self.session.get(f"{BASE_URL}/api/chat/sessions/nonexistent-id-12345")
        
        assert response.status_code == 404
        print("✓ Non-existent session returns 404")
    
    def test_delete_session(self):
        """Test deleting (archiving) a session"""
        # Create a session to delete
        create_response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "general",
            "title": "TEST_Session to Delete"
        })
        session_id = create_response.json()["id"]
        
        # Delete the session
        response = self.session.delete(f"{BASE_URL}/api/chat/sessions/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Session archived"
        print(f"✓ Deleted session {session_id}")
        
        # Verify session is no longer in active sessions list
        sessions_response = self.session.get(f"{BASE_URL}/api/chat/sessions")
        sessions = sessions_response.json()
        session_ids = [s["id"] for s in sessions]
        assert session_id not in session_ids, "Deleted session should not appear in active sessions"
        print("✓ Deleted session not in active sessions list")
    
    # ============== Message Tests ==============
    
    def test_send_message_and_get_ai_response(self):
        """Test sending a message and receiving AI response"""
        # Create a session
        create_response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "general",
            "title": "TEST_Message Test Session"
        })
        session_id = create_response.json()["id"]
        
        # Send a message
        response = self.session.post(f"{BASE_URL}/api/chat/sessions/{session_id}/messages", json={
            "message": "مرحبا، كيف يمكنك مساعدتي؟",
            "settings": {}
        })
        
        assert response.status_code == 200, f"Send message failed: {response.text}"
        
        data = response.json()
        assert "session_id" in data
        assert "user_message" in data
        assert "assistant_message" in data
        
        # Verify user message
        user_msg = data["user_message"]
        assert user_msg["role"] == "user"
        assert user_msg["content"] == "مرحبا، كيف يمكنك مساعدتي؟"
        
        # Verify assistant message
        assistant_msg = data["assistant_message"]
        assert assistant_msg["role"] == "assistant"
        assert len(assistant_msg["content"]) > 0
        
        print(f"✓ Sent message and received AI response")
        print(f"  User: {user_msg['content'][:50]}...")
        print(f"  AI: {assistant_msg['content'][:50]}...")
    
    def test_send_message_to_nonexistent_session(self):
        """Test sending message to non-existent session returns error"""
        response = self.session.post(f"{BASE_URL}/api/chat/sessions/nonexistent-id/messages", json={
            "message": "Test message",
            "settings": {}
        })
        
        assert response.status_code == 404
        print("✓ Message to non-existent session returns 404")
    
    def test_session_title_updates_after_first_message(self):
        """Test that session title updates after first message"""
        # Create a session with default title
        create_response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "general"
        })
        session_id = create_response.json()["id"]
        original_title = create_response.json()["title"]
        
        # Send a message
        self.session.post(f"{BASE_URL}/api/chat/sessions/{session_id}/messages", json={
            "message": "أريد إنشاء موقع ويب جديد",
            "settings": {}
        })
        
        # Get session and check title
        get_response = self.session.get(f"{BASE_URL}/api/chat/sessions/{session_id}")
        updated_title = get_response.json()["title"]
        
        # Title should be updated to the message content
        assert updated_title != original_title or "أريد" in updated_title
        print(f"✓ Session title updated from '{original_title}' to '{updated_title}'")
    
    # ============== Voices Endpoint Tests ==============
    
    def test_get_available_voices(self):
        """Test retrieving available voices for TTS"""
        response = self.session.get(f"{BASE_URL}/api/chat/voices")
        
        assert response.status_code == 200
        data = response.json()
        assert "voices" in data
        assert isinstance(data["voices"], list)
        assert len(data["voices"]) > 0
        
        # Check voice structure
        voice = data["voices"][0]
        assert "voice_id" in voice
        assert "name" in voice
        assert "gender" in voice
        assert "language" in voice
        
        print(f"✓ Retrieved {len(data['voices'])} voices")
        for v in data["voices"][:3]:
            print(f"  - {v['name']} ({v['gender']}, {v['language']})")
    
    # ============== Session Assets Tests ==============
    
    def test_get_session_assets(self):
        """Test retrieving assets for a session"""
        # Create a session
        create_response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "general",
            "title": "TEST_Assets Test Session"
        })
        session_id = create_response.json()["id"]
        
        # Get assets (should be empty for new session)
        response = self.session.get(f"{BASE_URL}/api/chat/sessions/{session_id}/assets")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} assets for session")
    
    # ============== Authentication Tests ==============
    
    def test_unauthorized_access(self):
        """Test that endpoints require authentication"""
        # Create a new session without auth
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.get(f"{BASE_URL}/api/chat/sessions")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Unauthorized access properly rejected")
    
    def test_invalid_token(self):
        """Test that invalid token is rejected"""
        invalid_session = requests.Session()
        invalid_session.headers.update({
            "Content-Type": "application/json",
            "Authorization": "Bearer invalid-token-12345"
        })
        
        response = invalid_session.get(f"{BASE_URL}/api/chat/sessions")
        
        assert response.status_code == 401
        print("✓ Invalid token properly rejected")


class TestChatImageGeneration:
    """Tests for image generation through chat"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        
        data = response.json()
        self.token = data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
    
    def test_image_generation_flow(self):
        """Test the full image generation flow through chat"""
        # Create an image session
        create_response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "image",
            "title": "TEST_Image Generation Flow"
        })
        session_id = create_response.json()["id"]
        
        # Send initial request
        response1 = self.session.post(f"{BASE_URL}/api/chat/sessions/{session_id}/messages", json={
            "message": "أريد صورة لقطة بيضاء جميلة",
            "settings": {}
        })
        
        assert response1.status_code == 200
        print("✓ Initial image request sent")
        
        # Send detailed request that should trigger generation
        response2 = self.session.post(f"{BASE_URL}/api/chat/sessions/{session_id}/messages", json={
            "message": "نعم، قطة بيضاء تجلس على نافذة مع إضاءة شمس الغروب",
            "settings": {}
        })
        
        assert response2.status_code == 200
        data = response2.json()
        
        # Check if image was generated (may or may not have attachment depending on AI response)
        assistant_msg = data["assistant_message"]
        print(f"✓ AI Response: {assistant_msg['content'][:100]}...")
        
        if assistant_msg.get("attachments"):
            attachment = assistant_msg["attachments"][0]
            assert attachment["type"] == "image"
            assert "url" in attachment
            print("✓ Image attachment generated")
        else:
            print("ℹ No image attachment in this response (AI may need more details)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
