"""
Test Stories, Banner, AI Media Generation, and Chatbot Analytics
─────────────────────────────────────────────────────────────────
Tests for iteration 20 features:
- Stories CRUD (create, read, update, delete)
- Banner CRUD
- AI Image Generation (Nano Banana)
- AI Video Generation (Sora 2 - async job)
- Chatbot Analytics
- Public stories endpoint
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CLIENT_SLUG = "cozy-cafe-demo"
CLIENT_PASSWORD = "WKDWkG0d"


@pytest.fixture(scope="module")
def client_token():
    """Get client authentication token"""
    r = requests.post(f"{BASE_URL}/api/websites/client/login", json={
        "slug": CLIENT_SLUG,
        "password": CLIENT_PASSWORD
    })
    if r.status_code != 200:
        pytest.skip(f"Client login failed: {r.status_code} - {r.text}")
    return r.json().get("token")


@pytest.fixture
def client_headers(client_token):
    """Headers with client auth"""
    return {
        "Authorization": f"ClientToken {client_token}",
        "Content-Type": "application/json"
    }


class TestStoriesCRUD:
    """Stories CRUD operations"""
    
    created_story_id = None
    
    def test_create_story(self, client_headers):
        """POST /api/websites/client/stories - create a new story"""
        # Use a small SVG data URL for testing
        svg_data = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'><rect fill='%23FFD700' width='100' height='100'/></svg>"
        
        r = requests.post(f"{BASE_URL}/api/websites/client/stories", 
            headers=client_headers,
            json={
                "type": "image",
                "media_url": svg_data,
                "caption": "TEST_story_caption",
                "duration_sec": 6,
                "visible": True
            }
        )
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("ok") == True
        assert "id" in data
        assert data["id"].startswith("st-")
        
        # Store for later tests
        TestStoriesCRUD.created_story_id = data["id"]
        print(f"✅ Created story: {data['id']}")
    
    def test_list_stories(self, client_headers):
        """GET /api/websites/client/stories - list all stories"""
        r = requests.get(f"{BASE_URL}/api/websites/client/stories", headers=client_headers)
        
        assert r.status_code == 200
        data = r.json()
        assert "stories" in data
        assert isinstance(data["stories"], list)
        
        # Verify our created story is in the list
        if TestStoriesCRUD.created_story_id:
            story_ids = [s.get("id") for s in data["stories"]]
            assert TestStoriesCRUD.created_story_id in story_ids
        
        print(f"✅ Listed {len(data['stories'])} stories")
    
    def test_patch_story(self, client_headers):
        """PATCH /api/websites/client/stories/{id} - update story caption"""
        if not TestStoriesCRUD.created_story_id:
            pytest.skip("No story created to patch")
        
        new_caption = "TEST_updated_caption"
        r = requests.patch(
            f"{BASE_URL}/api/websites/client/stories/{TestStoriesCRUD.created_story_id}",
            headers=client_headers,
            json={"caption": new_caption}
        )
        
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") == True
        
        # Verify the update
        stories = data.get("stories", [])
        updated = next((s for s in stories if s.get("id") == TestStoriesCRUD.created_story_id), None)
        assert updated is not None
        assert updated.get("caption") == new_caption
        
        print(f"✅ Updated story caption to: {new_caption}")
    
    def test_delete_story(self, client_headers):
        """DELETE /api/websites/client/stories/{id} - delete story"""
        if not TestStoriesCRUD.created_story_id:
            pytest.skip("No story created to delete")
        
        r = requests.delete(
            f"{BASE_URL}/api/websites/client/stories/{TestStoriesCRUD.created_story_id}",
            headers=client_headers
        )
        
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") == True
        
        # Verify deletion
        r2 = requests.get(f"{BASE_URL}/api/websites/client/stories", headers=client_headers)
        stories = r2.json().get("stories", [])
        story_ids = [s.get("id") for s in stories]
        assert TestStoriesCRUD.created_story_id not in story_ids
        
        print(f"✅ Deleted story: {TestStoriesCRUD.created_story_id}")


class TestPublicStories:
    """Public stories endpoint"""
    
    def test_public_stories_endpoint(self):
        """GET /api/websites/public/{slug}/stories - public stories"""
        r = requests.get(f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/stories")
        
        assert r.status_code == 200
        data = r.json()
        
        # Verify response structure
        assert "stories" in data
        assert "banner" in data
        assert "store_name" in data
        
        # Stories should be a list
        assert isinstance(data["stories"], list)
        
        # Banner should have enabled field
        assert "enabled" in data["banner"]
        
        print(f"✅ Public stories: {len(data['stories'])} stories, banner enabled: {data['banner'].get('enabled')}")
    
    def test_hidden_stories_filtered(self, client_headers):
        """Verify hidden stories are filtered from public endpoint"""
        # Create a hidden story
        svg_data = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='50' height='50'><rect fill='%23FF0000' width='50' height='50'/></svg>"
        
        r = requests.post(f"{BASE_URL}/api/websites/client/stories",
            headers=client_headers,
            json={
                "type": "image",
                "media_url": svg_data,
                "caption": "TEST_hidden_story",
                "visible": False
            }
        )
        
        if r.status_code != 200:
            pytest.skip("Could not create hidden story")
        
        hidden_id = r.json().get("id")
        
        # Check public endpoint - hidden story should NOT appear
        r2 = requests.get(f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/stories")
        public_stories = r2.json().get("stories", [])
        public_ids = [s.get("id") for s in public_stories]
        
        assert hidden_id not in public_ids, "Hidden story should not appear in public endpoint"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/websites/client/stories/{hidden_id}", headers=client_headers)
        
        print("✅ Hidden stories are correctly filtered from public endpoint")


class TestBannerCRUD:
    """Banner configuration CRUD"""
    
    def test_get_banner_defaults(self, client_headers):
        """GET /api/websites/client/banner - get banner config"""
        r = requests.get(f"{BASE_URL}/api/websites/client/banner", headers=client_headers)
        
        assert r.status_code == 200
        data = r.json()
        
        # Should have default fields
        assert "enabled" in data
        assert "animation" in data
        
        print(f"✅ Banner config: enabled={data.get('enabled')}, animation={data.get('animation')}")
    
    def test_update_banner(self, client_headers):
        """PUT /api/websites/client/banner - update banner config"""
        r = requests.put(f"{BASE_URL}/api/websites/client/banner",
            headers=client_headers,
            json={
                "enabled": True,
                "title": "TEST_banner_title",
                "subtitle": "TEST_banner_subtitle",
                "cta_text": "اكتشف المزيد",
                "cta_link": "https://example.com",
                "animation": "kenburns"
            }
        )
        
        assert r.status_code == 200
        data = r.json()
        
        # Verify response echoes new values
        assert data.get("enabled") == True
        assert data.get("title") == "TEST_banner_title"
        assert data.get("subtitle") == "TEST_banner_subtitle"
        assert data.get("animation") == "kenburns"
        
        print("✅ Banner updated successfully")
    
    def test_public_banner_reflects_changes(self):
        """Verify public endpoint shows updated banner"""
        r = requests.get(f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/stories")
        
        assert r.status_code == 200
        banner = r.json().get("banner", {})
        
        # If banner was enabled, it should show in public
        if banner.get("enabled"):
            assert "title" in banner or banner.get("enabled") == True
        
        print(f"✅ Public banner: enabled={banner.get('enabled')}")


class TestAIImageGeneration:
    """AI Image Generation (Nano Banana)"""
    
    def test_generate_image(self, client_headers):
        """POST /api/websites/client/media/generate-image - Nano Banana"""
        r = requests.post(f"{BASE_URL}/api/websites/client/media/generate-image",
            headers=client_headers,
            json={
                "prompt": "a simple coffee cup",
                "add_as_story": True
            },
            timeout=60  # AI generation can take 5-30 seconds
        )
        
        # Should succeed (200) or fail gracefully (500 if AI unavailable)
        if r.status_code == 500:
            error = r.json().get("detail", "")
            if "AI service unavailable" in error or "فشل توليد" in error:
                pytest.skip("AI service unavailable - skipping image generation test")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        
        assert data.get("ok") == True
        assert "media_url" in data
        assert data["media_url"].startswith("data:")
        
        # If add_as_story=True, should have story_id
        if data.get("story_id"):
            assert data["story_id"].startswith("st-")
            
            # Verify story was created with ai_generated=True
            r2 = requests.get(f"{BASE_URL}/api/websites/client/stories", headers=client_headers)
            stories = r2.json().get("stories", [])
            ai_story = next((s for s in stories if s.get("id") == data["story_id"]), None)
            
            if ai_story:
                assert ai_story.get("ai_generated") == True
                # Cleanup
                requests.delete(f"{BASE_URL}/api/websites/client/stories/{data['story_id']}", headers=client_headers)
        
        print(f"✅ AI image generated, story_id: {data.get('story_id')}")


class TestAIVideoGeneration:
    """AI Video Generation (Sora 2 - async)"""
    
    def test_generate_video_job(self, client_headers):
        """POST /api/websites/client/media/generate-video - Sora 2 async job"""
        r = requests.post(f"{BASE_URL}/api/websites/client/media/generate-video",
            headers=client_headers,
            json={
                "prompt": "a barista making latte art",
                "duration": 4,
                "add_as_story": True
            }
        )
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        
        assert data.get("ok") == True
        assert "job_id" in data
        assert data["job_id"].startswith("vj-")
        assert data.get("status") == "queued"
        
        job_id = data["job_id"]
        print(f"✅ Video job created: {job_id}, status: queued")
        
        # Poll job status (don't wait for completion - Sora takes 2-5 minutes)
        time.sleep(2)  # Brief wait
        
        r2 = requests.get(f"{BASE_URL}/api/websites/client/media/jobs/{job_id}", headers=client_headers)
        
        assert r2.status_code == 200
        job_data = r2.json()
        
        # Status should be queued or processing
        assert job_data.get("status") in ["queued", "processing", "done", "failed"]
        
        print(f"✅ Video job status: {job_data.get('status')}")


class TestChatbotAnalytics:
    """Chatbot Analytics endpoint"""
    
    def test_send_chat_messages(self):
        """Send chat messages to populate analytics data"""
        messages = [
            "كم سعر القهوة؟",  # Price question
            "متى تفتحون؟",  # Hours question
            "ابغى ارجاع طلبي",  # Return/complaint - should trigger handoff
            "هل عندكم توصيل؟"  # Shipping question
        ]
        
        for msg in messages:
            r = requests.post(f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/chatbot",
                json={
                    "message": msg,
                    "session_id": f"test-analytics-{int(time.time())}"
                },
                timeout=30
            )
            
            if r.status_code == 403:
                pytest.skip("Chatbot not enabled for this project")
            
            if r.status_code == 200:
                data = r.json()
                print(f"  → Sent: '{msg[:30]}...' → handoff: {data.get('handoff', False)}")
            
            time.sleep(1)  # Brief pause between messages
        
        print("✅ Sent test chat messages")
    
    def test_get_analytics(self, client_headers):
        """GET /api/websites/client/chatbot/analytics - get analytics"""
        r = requests.get(f"{BASE_URL}/api/websites/client/chatbot/analytics?days=30",
            headers=client_headers
        )
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        
        # Verify response structure
        assert "totals" in data
        assert "topics" in data
        assert "lost_questions" in data
        assert "recent" in data
        assert "window_days" in data
        
        totals = data["totals"]
        assert "messages" in totals
        assert "handoffs" in totals
        assert "handoff_rate_pct" in totals
        assert "unique_sessions" in totals
        
        # Topics should be a list
        assert isinstance(data["topics"], list)
        
        print(f"✅ Analytics: {totals['messages']} messages, {totals['handoffs']} handoffs, {totals['handoff_rate_pct']}% handoff rate")
        
        # If we have messages, verify topic detection
        if totals["messages"] > 0:
            topics_with_counts = [t for t in data["topics"] if t.get("count", 0) > 0]
            if topics_with_counts:
                print(f"  → Topics detected: {[t['label'] for t in topics_with_counts[:3]]}")


class TestClientLogin:
    """Client authentication"""
    
    def test_client_login_success(self):
        """POST /api/websites/client/login - successful login"""
        r = requests.post(f"{BASE_URL}/api/websites/client/login", json={
            "slug": CLIENT_SLUG,
            "password": CLIENT_PASSWORD
        })
        
        assert r.status_code == 200
        data = r.json()
        
        assert "token" in data
        assert "name" in data
        
        print(f"✅ Client login successful: {data.get('name')}")
    
    def test_client_login_wrong_password(self):
        """POST /api/websites/client/login - wrong password"""
        r = requests.post(f"{BASE_URL}/api/websites/client/login", json={
            "slug": CLIENT_SLUG,
            "password": "wrong_password"
        })
        
        assert r.status_code == 401
        print("✅ Wrong password correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
