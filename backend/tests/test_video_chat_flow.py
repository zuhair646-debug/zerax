"""
Zitex Video Chat Flow Tests
Tests for the video consultation system with 3 video types:
- Cinematic (سينمائي)
- Funny (مضحك)
- Advertising (إعلاني)

Test credentials: owner@zitex.com / owner123
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-cinematic-hub-2.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "owner@zitex.com"
TEST_PASSWORD = "owner123"


class TestAuthAndSetup:
    """Authentication and setup tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for owner user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_login_success(self):
        """Test login with owner credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        print(f"✅ Login successful for {TEST_EMAIL}")
    
    def test_get_user_info(self, auth_headers):
        """Test getting user info"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_EMAIL
        # Owner should have is_owner=True or role=owner
        is_owner = data.get("is_owner", False) or data.get("role") == "owner"
        print(f"✅ User info retrieved - is_owner: {is_owner}, credits: {data.get('credits', 0)}")


class TestChatSessionCreation:
    """Tests for creating chat sessions"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = response.json()["token"]
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def test_create_video_session(self, auth_headers):
        """Test creating a video type session"""
        response = requests.post(
            f"{BASE_URL}/api/chat/sessions",
            headers=auth_headers,
            json={"session_type": "video"}
        )
        assert response.status_code == 200, f"Failed to create session: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["session_type"] == "video"
        assert "messages" in data
        
        # Check welcome message exists
        messages = data.get("messages", [])
        assert len(messages) > 0, "No welcome message in session"
        
        welcome_msg = messages[0]
        assert welcome_msg["role"] == "assistant"
        assert "[BUTTONS]" in welcome_msg["content"], "Welcome message should have buttons"
        
        print(f"✅ Video session created: {data['id']}")
        return data["id"]
    
    def test_create_general_session(self, auth_headers):
        """Test creating a general session"""
        response = requests.post(
            f"{BASE_URL}/api/chat/sessions",
            headers=auth_headers,
            json={"session_type": "general"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_type"] == "general"
        print(f"✅ General session created: {data['id']}")
    
    def test_get_sessions_list(self, auth_headers):
        """Test getting list of sessions"""
        response = requests.get(
            f"{BASE_URL}/api/chat/sessions",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Retrieved {len(data)} sessions")


class TestVideoConsultationFlow:
    """Tests for the video consultation flow"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = response.json()["token"]
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def video_session(self, auth_headers):
        """Create a video session for testing"""
        response = requests.post(
            f"{BASE_URL}/api/chat/sessions",
            headers=auth_headers,
            json={"session_type": "video"}
        )
        return response.json()
    
    def test_send_advertising_video_request(self, auth_headers, video_session):
        """Test sending a request for advertising video"""
        session_id = video_session["id"]
        
        # Send message requesting advertising video
        response = requests.post(
            f"{BASE_URL}/api/chat/sessions/{session_id}/messages",
            headers=auth_headers,
            json={"message": "أريد فيديو إعلاني لشركتي"}
        )
        
        assert response.status_code == 200, f"Failed to send message: {response.text}"
        data = response.json()
        
        assert "assistant_message" in data
        assistant_msg = data["assistant_message"]
        
        # Check that AI responds with consultation questions or buttons
        content = assistant_msg.get("content", "")
        
        # The AI should ask about video type or provide options
        has_buttons = "[BUTTONS]" in content
        has_questions = any(q in content for q in ["اسم", "شركة", "منتج", "نوع", "المدة", "الجمهور"])
        
        assert has_buttons or has_questions, f"AI should ask consultation questions or show buttons. Got: {content[:200]}"
        
        print(f"✅ Advertising video request processed")
        print(f"   Response has buttons: {has_buttons}")
        print(f"   Response has questions: {has_questions}")
    
    def test_send_cinematic_video_request(self, auth_headers, video_session):
        """Test sending a request for cinematic video"""
        session_id = video_session["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/chat/sessions/{session_id}/messages",
            headers=auth_headers,
            json={"message": "🎬 فيديو سينمائي"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        content = data["assistant_message"]["content"]
        # AI should respond with cinematic video options
        print(f"✅ Cinematic video request processed")
    
    def test_send_funny_video_request(self, auth_headers):
        """Test sending a request for funny video"""
        # Create new session for this test
        session_response = requests.post(
            f"{BASE_URL}/api/chat/sessions",
            headers=auth_headers,
            json={"session_type": "video"}
        )
        session_id = session_response.json()["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/chat/sessions/{session_id}/messages",
            headers=auth_headers,
            json={"message": "😂 فيديو مضحك"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        content = data["assistant_message"]["content"]
        print(f"✅ Funny video request processed")


class TestServiceCostsAndPricing:
    """Tests for service costs verification"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = response.json()["token"]
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def test_get_pricing_config(self):
        """Test getting pricing configuration"""
        response = requests.get(f"{BASE_URL}/api/pricing")
        assert response.status_code == 200
        data = response.json()
        
        # Check service costs exist
        assert "service_costs" in data
        costs = data["service_costs"]
        
        # Verify video costs are defined
        assert "video_4_seconds" in costs or "video_12_seconds" in costs
        
        print(f"✅ Pricing config retrieved")
        print(f"   Service costs: {costs}")
    
    def test_get_user_balance(self, auth_headers):
        """Test getting user balance with service costs"""
        response = requests.get(
            f"{BASE_URL}/api/user/balance",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "credits" in data
        assert "service_costs" in data
        
        print(f"✅ User balance retrieved: {data['credits']} credits")


class TestTemplatesAndAssets:
    """Tests for templates and assets"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = response.json()["token"]
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def test_get_templates(self, auth_headers):
        """Test getting available templates"""
        response = requests.get(
            f"{BASE_URL}/api/chat/templates",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "templates" in data
        templates = data["templates"]
        
        print(f"✅ Retrieved {len(templates)} templates")
    
    def test_get_game_libraries(self, auth_headers):
        """Test getting game libraries"""
        response = requests.get(
            f"{BASE_URL}/api/chat/game-libraries",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "libraries" in data
        print(f"✅ Retrieved game libraries")


class TestChatMessageFlow:
    """Tests for complete chat message flow"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = response.json()["token"]
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def test_full_video_consultation_flow(self, auth_headers):
        """Test complete video consultation flow"""
        # Step 1: Create session
        session_response = requests.post(
            f"{BASE_URL}/api/chat/sessions",
            headers=auth_headers,
            json={"session_type": "video", "title": "TEST_video_consultation"}
        )
        assert session_response.status_code == 200
        session = session_response.json()
        session_id = session["id"]
        
        print(f"✅ Step 1: Session created - {session_id}")
        
        # Step 2: Request advertising video
        msg1_response = requests.post(
            f"{BASE_URL}/api/chat/sessions/{session_id}/messages",
            headers=auth_headers,
            json={"message": "📺 فيديو إعلاني/تجاري"}
        )
        assert msg1_response.status_code == 200
        msg1_data = msg1_response.json()
        
        # Wait for AI processing
        time.sleep(2)
        
        content1 = msg1_data["assistant_message"]["content"]
        print(f"✅ Step 2: Advertising video selected")
        print(f"   AI Response preview: {content1[:150]}...")
        
        # Step 3: Provide company details
        msg2_response = requests.post(
            f"{BASE_URL}/api/chat/sessions/{session_id}/messages",
            headers=auth_headers,
            json={"message": "شركة زيتكس للتقنية، نقدم خدمات الذكاء الاصطناعي"}
        )
        assert msg2_response.status_code == 200
        msg2_data = msg2_response.json()
        
        time.sleep(2)
        
        content2 = msg2_data["assistant_message"]["content"]
        print(f"✅ Step 3: Company details provided")
        print(f"   AI Response preview: {content2[:150]}...")
        
        # Step 4: Get session to verify messages
        get_session_response = requests.get(
            f"{BASE_URL}/api/chat/sessions/{session_id}",
            headers=auth_headers
        )
        assert get_session_response.status_code == 200
        final_session = get_session_response.json()
        
        messages = final_session.get("messages", [])
        assert len(messages) >= 4, f"Expected at least 4 messages, got {len(messages)}"
        
        print(f"✅ Step 4: Session verified with {len(messages)} messages")
        
        # Cleanup - delete session
        delete_response = requests.delete(
            f"{BASE_URL}/api/chat/sessions/{session_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200
        print(f"✅ Step 5: Session cleaned up")


class TestButtonsAndChoices:
    """Tests for button/choice functionality in chat"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = response.json()["token"]
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def test_welcome_message_has_buttons(self, auth_headers):
        """Test that welcome message contains choice buttons"""
        # Create session
        response = requests.post(
            f"{BASE_URL}/api/chat/sessions",
            headers=auth_headers,
            json={"session_type": "general"}
        )
        assert response.status_code == 200
        session = response.json()
        
        messages = session.get("messages", [])
        assert len(messages) > 0, "No messages in session"
        
        welcome_msg = messages[0]
        content = welcome_msg.get("content", "")
        
        # Check for BUTTONS tag
        assert "[BUTTONS]" in content, f"Welcome message should have [BUTTONS] tag. Got: {content[:200]}"
        assert "[/BUTTONS]" in content, "Welcome message should have closing [/BUTTONS] tag"
        
        # Extract buttons
        import re
        buttons_match = re.search(r'\[BUTTONS\]\n?(.*?)\[/BUTTONS\]', content, re.DOTALL)
        if buttons_match:
            buttons_text = buttons_match.group(1).strip()
            buttons = [b.strip() for b in buttons_text.split('|') if b.strip()]
            print(f"✅ Welcome message has {len(buttons)} buttons: {buttons}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/chat/sessions/{session['id']}", headers=auth_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
