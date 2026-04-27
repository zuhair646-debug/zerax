"""
Zitex Video Polling API Tests
Tests for the new video generation background task and polling mechanism:
- Video request creation
- Video-requests endpoint
- Polling for status updates
- Session loading with pending requests
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-cinematic-hub-2.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "owner@zitex.com"
TEST_PASSWORD = "owner123"


class TestVideoPollingAPIs:
    """Video polling API endpoint tests"""
    
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
    
    # ============== Video Request Tests ==============
    
    def test_create_video_session(self):
        """Test creating a video chat session"""
        response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "video",
            "title": "TEST_Video Polling Session"
        })
        
        assert response.status_code == 200, f"Create session failed: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert data["session_type"] == "video"
        assert data["status"] == "active"
        print(f"✓ Created video session: {data['id']}")
        
        self.video_session_id = data["id"]
        return data["id"]
    
    def test_send_video_request_and_get_pending_response(self):
        """Test sending a video request and receiving pending response"""
        # Create a video session
        create_response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "video",
            "title": "TEST_Video Request Test"
        })
        session_id = create_response.json()["id"]
        
        # Send a video generation request
        response = self.session.post(f"{BASE_URL}/api/chat/sessions/{session_id}/messages", json={
            "message": "أريد فيديو لشروق الشمس على الجبال",
            "settings": {"duration": 4, "size": "1280x720"}
        })
        
        assert response.status_code == 200, f"Send message failed: {response.text}"
        
        data = response.json()
        assert "session_id" in data
        assert "user_message" in data
        assert "assistant_message" in data
        
        # Verify assistant message contains video_pending attachment
        assistant_msg = data["assistant_message"]
        assert assistant_msg["message_type"] == "video_pending" or len(assistant_msg.get("attachments", [])) > 0
        
        # Check for video_pending attachment
        attachments = assistant_msg.get("attachments", [])
        video_pending = None
        for att in attachments:
            if att.get("type") == "video_pending":
                video_pending = att
                break
        
        assert video_pending is not None, "Expected video_pending attachment"
        assert "requests" in video_pending
        assert len(video_pending["requests"]) > 0
        
        request_id = video_pending["requests"][0]["id"]
        print(f"✓ Video request created with ID: {request_id}")
        print(f"  Prompt: {video_pending['requests'][0].get('prompt', 'N/A')[:50]}...")
        print(f"  Duration: {video_pending['requests'][0].get('duration', 'N/A')} seconds")
        
        return session_id, request_id
    
    def test_video_requests_endpoint_returns_pending(self):
        """Test that video-requests endpoint returns pending requests"""
        # Create session and send video request
        create_response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "video",
            "title": "TEST_Video Requests Endpoint Test"
        })
        session_id = create_response.json()["id"]
        
        # Send video request
        self.session.post(f"{BASE_URL}/api/chat/sessions/{session_id}/messages", json={
            "message": "فيديو لطائر يطير في السماء",
            "settings": {"duration": 4, "size": "1280x720"}
        })
        
        # Check video-requests endpoint
        response = self.session.get(f"{BASE_URL}/api/chat/video-requests?session_id={session_id}")
        
        assert response.status_code == 200, f"Get video requests failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected at least one video request"
        
        # Verify request structure
        request = data[0]
        assert "id" in request
        assert "user_id" in request
        assert "session_id" in request
        assert "prompt" in request
        assert "duration" in request
        assert "size" in request
        assert "status" in request
        assert request["status"] in ["pending", "processing", "completed", "failed"]
        
        print(f"✓ Video requests endpoint returned {len(data)} request(s)")
        print(f"  Status: {request['status']}")
        print(f"  Prompt: {request['prompt'][:50]}...")
    
    def test_video_requests_endpoint_without_session_filter(self):
        """Test video-requests endpoint without session filter returns all user requests"""
        response = self.session.get(f"{BASE_URL}/api/chat/video-requests")
        
        assert response.status_code == 200, f"Get video requests failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Video requests endpoint (no filter) returned {len(data)} request(s)")
    
    def test_load_session_retrieves_pending_video_requests(self):
        """Test that loading a session retrieves pending video requests"""
        # Create session and send video request
        create_response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "video",
            "title": "TEST_Session Load Test"
        })
        session_id = create_response.json()["id"]
        
        # Send video request
        self.session.post(f"{BASE_URL}/api/chat/sessions/{session_id}/messages", json={
            "message": "فيديو لموجات البحر",
            "settings": {"duration": 4, "size": "1280x720"}
        })
        
        # Load the session
        session_response = self.session.get(f"{BASE_URL}/api/chat/sessions/{session_id}")
        assert session_response.status_code == 200
        
        session_data = session_response.json()
        assert "messages" in session_data
        assert len(session_data["messages"]) >= 2  # User message + assistant message
        
        # Check video requests for this session
        video_requests_response = self.session.get(f"{BASE_URL}/api/chat/video-requests?session_id={session_id}")
        assert video_requests_response.status_code == 200
        
        video_requests = video_requests_response.json()
        pending_or_processing = [r for r in video_requests if r["status"] in ["pending", "processing"]]
        
        print(f"✓ Session loaded with {len(session_data['messages'])} messages")
        print(f"  Pending/Processing video requests: {len(pending_or_processing)}")
    
    def test_get_specific_video_request(self):
        """Test getting a specific video request by ID"""
        # Create session and send video request
        create_response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "video",
            "title": "TEST_Specific Request Test"
        })
        session_id = create_response.json()["id"]
        
        # Send video request
        msg_response = self.session.post(f"{BASE_URL}/api/chat/sessions/{session_id}/messages", json={
            "message": "فيديو لنجوم في الليل",
            "settings": {"duration": 4, "size": "1280x720"}
        })
        
        # Get request ID from response
        attachments = msg_response.json()["assistant_message"].get("attachments", [])
        request_id = None
        for att in attachments:
            if att.get("type") == "video_pending" and att.get("requests"):
                request_id = att["requests"][0]["id"]
                break
        
        assert request_id is not None, "Could not find request ID"
        
        # Get specific request
        response = self.session.get(f"{BASE_URL}/api/chat/video-requests/{request_id}")
        
        assert response.status_code == 200, f"Get specific request failed: {response.text}"
        
        data = response.json()
        assert data["id"] == request_id
        assert "status" in data
        print(f"✓ Retrieved specific video request: {request_id}")
        print(f"  Status: {data['status']}")
    
    def test_video_request_status_transitions(self):
        """Test that video request status transitions correctly"""
        # Create session and send video request
        create_response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "video",
            "title": "TEST_Status Transition Test"
        })
        session_id = create_response.json()["id"]
        
        # Send video request
        msg_response = self.session.post(f"{BASE_URL}/api/chat/sessions/{session_id}/messages", json={
            "message": "فيديو قصير للاختبار",
            "settings": {"duration": 4, "size": "1280x720"}
        })
        
        # Get request ID
        attachments = msg_response.json()["assistant_message"].get("attachments", [])
        request_id = None
        for att in attachments:
            if att.get("type") == "video_pending" and att.get("requests"):
                request_id = att["requests"][0]["id"]
                break
        
        assert request_id is not None
        
        # Check initial status (should be pending or processing)
        response = self.session.get(f"{BASE_URL}/api/chat/video-requests/{request_id}")
        initial_status = response.json()["status"]
        
        assert initial_status in ["pending", "processing"], f"Unexpected initial status: {initial_status}"
        print(f"✓ Initial status: {initial_status}")
        
        # Wait a bit and check again (status might change to processing)
        time.sleep(2)
        response = self.session.get(f"{BASE_URL}/api/chat/video-requests/{request_id}")
        current_status = response.json()["status"]
        
        assert current_status in ["pending", "processing", "completed", "failed"]
        print(f"✓ Status after 2s: {current_status}")
    
    # ============== Authentication Tests ==============
    
    def test_video_requests_requires_auth(self):
        """Test that video-requests endpoint requires authentication"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.get(f"{BASE_URL}/api/chat/video-requests")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Video requests endpoint requires authentication")


class TestVideoPollingIntegration:
    """Integration tests for video polling flow"""
    
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
    
    def test_full_video_request_flow(self):
        """Test the complete video request flow (without waiting for completion)"""
        print("\n=== Full Video Request Flow Test ===")
        
        # Step 1: Create video session
        create_response = self.session.post(f"{BASE_URL}/api/chat/sessions", json={
            "session_type": "video",
            "title": "TEST_Full Flow Test"
        })
        assert create_response.status_code == 200
        session_id = create_response.json()["id"]
        print(f"1. Created session: {session_id}")
        
        # Step 2: Send video request
        msg_response = self.session.post(f"{BASE_URL}/api/chat/sessions/{session_id}/messages", json={
            "message": "أريد فيديو سينمائي لغروب الشمس",
            "settings": {"duration": 4, "size": "1280x720"}
        })
        assert msg_response.status_code == 200
        
        msg_data = msg_response.json()
        assistant_msg = msg_data["assistant_message"]
        print(f"2. Sent video request, got response: {assistant_msg['content'][:50]}...")
        
        # Step 3: Verify video_pending attachment
        attachments = assistant_msg.get("attachments", [])
        video_pending = next((a for a in attachments if a.get("type") == "video_pending"), None)
        assert video_pending is not None, "Expected video_pending attachment"
        
        request_id = video_pending["requests"][0]["id"]
        print(f"3. Video request ID: {request_id}")
        
        # Step 4: Poll video-requests endpoint
        poll_response = self.session.get(f"{BASE_URL}/api/chat/video-requests?session_id={session_id}")
        assert poll_response.status_code == 200
        
        requests_data = poll_response.json()
        assert len(requests_data) > 0
        
        current_request = next((r for r in requests_data if r["id"] == request_id), None)
        assert current_request is not None
        print(f"4. Polled status: {current_request['status']}")
        
        # Step 5: Load session and verify messages
        session_response = self.session.get(f"{BASE_URL}/api/chat/sessions/{session_id}")
        assert session_response.status_code == 200
        
        session_data = session_response.json()
        assert len(session_data["messages"]) >= 2
        print(f"5. Session has {len(session_data['messages'])} messages")
        
        print("=== Flow Test Complete ===\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
