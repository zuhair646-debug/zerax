"""
Test suite for Zenrex AI Agent endpoints.

Tests:
- POST /api/agent/chat — SSE streaming with tool calls
- GET /api/agent/conversations — list conversations
- GET /api/agent/conversation/{id} — full transcript
- DELETE /api/agent/conversation/{id} — owner-only deletion
- GET /api/agent/conversation/{id}/preview — returns current_html
- GET /api/agent/audio/{filename} — serves MP3 (404 for missing)
- Tool registry verification
"""
import pytest
import requests
import os
import json
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
OWNER_EMAIL = "owner@zenrex.ai"
OWNER_PASSWORD = "owner123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for owner user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Login failed: {response.status_code} - {response.text}")
    data = response.json()
    return data.get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestAgentAuth:
    """Test authentication requirements for agent endpoints"""
    
    def test_chat_requires_auth(self):
        """POST /api/agent/chat should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/agent/chat",
            json={"message": "test"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✅ /api/agent/chat requires authentication")
    
    def test_conversations_requires_auth(self):
        """GET /api/agent/conversations should require authentication"""
        response = requests.get(f"{BASE_URL}/api/agent/conversations")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✅ /api/agent/conversations requires authentication")


class TestAgentConversations:
    """Test conversation listing and management"""
    
    def test_list_conversations(self, auth_headers):
        """GET /api/agent/conversations should return list with has_html field"""
        response = requests.get(
            f"{BASE_URL}/api/agent/conversations",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "conversations" in data, "Response should have 'conversations' key"
        
        # Verify structure if conversations exist
        if data["conversations"]:
            conv = data["conversations"][0]
            assert "id" in conv, "Conversation should have 'id'"
            assert "has_html" in conv, "Conversation should have 'has_html' field"
            print(f"✅ Listed {len(data['conversations'])} conversations with has_html field")
        else:
            print("✅ Conversations list returned (empty)")


class TestAgentChat:
    """Test the main chat SSE streaming endpoint"""
    
    def test_chat_simple_query(self, auth_headers):
        """POST /api/agent/chat with simple query should stream SSE events"""
        # Use a simple query that triggers tool calls (quran reciters)
        response = requests.post(
            f"{BASE_URL}/api/agent/chat",
            headers=auth_headers,
            json={
                "message": "اذكر لي 3 قراء قرآن",  # "list 3 quran reciters"
                "model": "gpt-4o"
            },
            stream=True,
            timeout=120  # Allow time for AI response
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "text/event-stream" in response.headers.get("content-type", ""), \
            "Response should be SSE stream"
        
        # Parse SSE events
        events = []
        conversation_id = None
        has_tool_event = False
        has_text_event = False
        has_saved_event = False
        
        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                try:
                    evt = json.loads(line[6:])
                    events.append(evt)
                    
                    if evt.get("type") == "text":
                        has_text_event = True
                    elif evt.get("type") == "tool":
                        has_tool_event = True
                        print(f"  Tool event: {evt.get('name')} - {evt.get('status')}")
                    elif evt.get("type") == "saved":
                        has_saved_event = True
                        conversation_id = evt.get("conversation_id")
                    elif evt.get("type") == "error":
                        print(f"  Error event: {evt.get('message')}")
                except json.JSONDecodeError:
                    pass
        
        assert len(events) > 0, "Should receive at least one SSE event"
        assert has_saved_event, "Should receive 'saved' event with conversation_id"
        assert conversation_id, "Should have conversation_id from saved event"
        
        print(f"✅ Chat SSE streaming works - received {len(events)} events")
        print(f"  - Text events: {has_text_event}")
        print(f"  - Tool events: {has_tool_event}")
        print(f"  - Conversation ID: {conversation_id}")
        
        return conversation_id
    
    def test_chat_creates_conversation(self, auth_headers):
        """Chat should create a conversation that can be retrieved"""
        # First, send a chat message
        response = requests.post(
            f"{BASE_URL}/api/agent/chat",
            headers=auth_headers,
            json={
                "message": "مرحبا",  # Simple greeting
                "model": "gpt-4o"
            },
            stream=True,
            timeout=60
        )
        
        assert response.status_code == 200
        
        # Extract conversation_id from saved event
        conversation_id = None
        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                try:
                    evt = json.loads(line[6:])
                    if evt.get("type") == "saved":
                        conversation_id = evt.get("conversation_id")
                        break
                except:
                    pass
        
        assert conversation_id, "Should get conversation_id from chat"
        
        # Now verify conversation exists
        conv_response = requests.get(
            f"{BASE_URL}/api/agent/conversation/{conversation_id}",
            headers=auth_headers
        )
        assert conv_response.status_code == 200, f"Should retrieve conversation: {conv_response.text}"
        
        conv_data = conv_response.json()
        assert "messages" in conv_data, "Conversation should have messages"
        assert len(conv_data["messages"]) >= 2, "Should have at least user + assistant messages"
        
        print(f"✅ Chat creates retrievable conversation with {len(conv_data['messages'])} messages")
        return conversation_id


class TestAgentConversationDetail:
    """Test individual conversation retrieval"""
    
    def test_get_conversation_not_found(self, auth_headers):
        """GET /api/agent/conversation/{id} should return 404 for non-existent"""
        response = requests.get(
            f"{BASE_URL}/api/agent/conversation/nonexistent-id-12345",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Non-existent conversation returns 404")


class TestAgentPreview:
    """Test HTML preview endpoint"""
    
    def test_preview_empty_placeholder(self, auth_headers):
        """GET /api/agent/conversation/{id}/preview should return placeholder for no HTML"""
        # First create a conversation without website building
        response = requests.post(
            f"{BASE_URL}/api/agent/chat",
            headers=auth_headers,
            json={"message": "مرحبا", "model": "gpt-4o"},
            stream=True,
            timeout=60
        )
        
        conversation_id = None
        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                try:
                    evt = json.loads(line[6:])
                    if evt.get("type") == "saved":
                        conversation_id = evt.get("conversation_id")
                        break
                except:
                    pass
        
        if not conversation_id:
            pytest.skip("Could not create conversation for preview test")
        
        # Get preview (should be empty placeholder)
        preview_response = requests.get(
            f"{BASE_URL}/api/agent/conversation/{conversation_id}/preview"
        )
        assert preview_response.status_code == 200, f"Preview should return 200: {preview_response.status_code}"
        assert "text/html" in preview_response.headers.get("content-type", ""), \
            "Preview should return HTML"
        
        # Should contain placeholder content
        html = preview_response.text
        assert "المعاينة جاهزة" in html or "<!doctype html>" in html.lower(), \
            "Should return valid HTML placeholder"
        
        print("✅ Preview returns HTML placeholder for conversation without website")


class TestAgentAudio:
    """Test audio serving endpoint"""
    
    def test_audio_not_found(self):
        """GET /api/agent/audio/{filename} should return 404 for missing file"""
        response = requests.get(f"{BASE_URL}/api/agent/audio/nonexistent-file.mp3")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Non-existent audio returns 404")
    
    def test_audio_invalid_filename(self):
        """GET /api/agent/audio/{filename} should reject path traversal"""
        response = requests.get(f"{BASE_URL}/api/agent/audio/../../../etc/passwd")
        assert response.status_code in [400, 404], f"Should reject path traversal: {response.status_code}"
        print("✅ Audio endpoint rejects path traversal")


class TestAgentDelete:
    """Test conversation deletion"""
    
    def test_delete_conversation(self, auth_headers):
        """DELETE /api/agent/conversation/{id} should delete owned conversation"""
        # First create a conversation
        response = requests.post(
            f"{BASE_URL}/api/agent/chat",
            headers=auth_headers,
            json={"message": "test delete", "model": "gpt-4o"},
            stream=True,
            timeout=60
        )
        
        conversation_id = None
        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                try:
                    evt = json.loads(line[6:])
                    if evt.get("type") == "saved":
                        conversation_id = evt.get("conversation_id")
                        break
                except:
                    pass
        
        if not conversation_id:
            pytest.skip("Could not create conversation for delete test")
        
        # Delete it
        delete_response = requests.delete(
            f"{BASE_URL}/api/agent/conversation/{conversation_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200, f"Delete should succeed: {delete_response.text}"
        
        # Verify it's gone
        get_response = requests.get(
            f"{BASE_URL}/api/agent/conversation/{conversation_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404, "Deleted conversation should return 404"
        
        print("✅ Conversation deletion works correctly")
    
    def test_delete_not_found(self, auth_headers):
        """DELETE /api/agent/conversation/{id} should return 404 for non-existent"""
        response = requests.delete(
            f"{BASE_URL}/api/agent/conversation/nonexistent-id-12345",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Delete non-existent conversation returns 404")


class TestToolRegistry:
    """Test that tools are properly registered"""
    
    def test_tools_registered(self):
        """Verify build_website, update_website, generate_audio are in registry"""
        # Import the tools module to check registry
        import sys
        sys.path.insert(0, '/app/backend')
        
        from modules.freebuild_v2.tools import TOOL_REGISTRY, TOOL_SCHEMAS
        
        # Check registry has the required tools
        required_tools = ['build_website', 'update_website', 'generate_audio']
        for tool in required_tools:
            assert tool in TOOL_REGISTRY, f"Tool '{tool}' should be in TOOL_REGISTRY"
            print(f"  ✅ {tool} is registered")
        
        # Check schemas have the tools
        schema_names = [s['function']['name'] for s in TOOL_SCHEMAS]
        for tool in required_tools:
            assert tool in schema_names, f"Tool '{tool}' should have schema in TOOL_SCHEMAS"
        
        print(f"✅ All required tools registered ({len(TOOL_REGISTRY)} total)")


class TestLoginRegression:
    """Regression test: existing login flow should still work"""
    
    def test_owner_login_works(self):
        """Owner login should work and return token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "token" in data, "Response should have token"
        assert "user" in data, "Response should have user"
        assert data["user"]["email"] == OWNER_EMAIL, "User email should match"
        
        print(f"✅ Owner login works - role: {data['user'].get('role')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
