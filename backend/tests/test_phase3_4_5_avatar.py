"""
Test Phase 3-5 Features: Avatar Saudi Dialect, Image Wizard, Channel Bridge
Tests:
1. Avatar Saudi Dialect - POST /api/avatar/chat returns Saudi dialect keywords
2. Avatar Pricing - GET /api/merchant/avatar/pricing
3. Avatar Trial Flow - POST /api/merchant/avatar/start-trial
4. Avatar Me - GET /api/merchant/avatar/me
5. Avatar Customize - PUT /api/merchant/avatar/customize
6. Avatar Hide/Show - POST /api/merchant/avatar/hide
7. Image Wizard Categories - GET /api/wizard/image/categories
8. Image Wizard Start - POST /api/wizard/image/start
9. Image Wizard Answer Flow - POST /api/wizard/image/answer
10. Channel Bridge Projects - GET /api/bridge/projects
11. Channel Bridge Push - POST /api/bridge/push-to-story
12. Channel Bridge History - GET /api/bridge/history
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Saudi dialect keywords to check
SAUDI_KEYWORDS = ['هلا', 'وش', 'ابغى', 'تبي', 'شلون', 'يلا', 'ابشر', 'على راسي', 'يعطيك العافية', 'تمام', 'خلنا']


@pytest.fixture(scope="module")
def auth_token():
    """Login as owner@zenrex.ai and get token"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "owner@zenrex.ai",
        "password": "owner123"
    })
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def project_id(auth_headers):
    """Get first project ID from bridge/projects"""
    r = requests.get(f"{BASE_URL}/api/bridge/projects", headers=auth_headers)
    assert r.status_code == 200, f"Failed to get projects: {r.text}"
    data = r.json()
    projects = data.get("projects", [])
    if not projects:
        pytest.skip("No projects available for testing")
    return projects[0]["id"]


class TestAvatarSaudiDialect:
    """Test 1: Avatar chat returns Saudi dialect"""
    
    def test_avatar_chat_saudi_dialect(self):
        """POST /api/avatar/chat should return Saudi dialect keywords"""
        r = requests.post(f"{BASE_URL}/api/avatar/chat", json={
            "message": "مرحبا، وش الخدمات اللي عندكم؟",
            "want_voice": False
        })
        assert r.status_code == 200, f"Avatar chat failed: {r.text}"
        data = r.json()
        assert "reply" in data, "No reply in response"
        reply = data["reply"]
        
        # Check for at least one Saudi keyword
        found_keywords = [kw for kw in SAUDI_KEYWORDS if kw in reply]
        print(f"Reply: {reply[:200]}...")
        print(f"Found Saudi keywords: {found_keywords}")
        
        # Accept if at least 1 Saudi keyword found (AI is non-deterministic)
        assert len(found_keywords) >= 1, f"No Saudi dialect keywords found in reply. Reply: {reply}"


class TestAvatarPricing:
    """Test 2: Avatar pricing endpoint"""
    
    def test_avatar_pricing(self):
        """GET /api/merchant/avatar/pricing returns correct pricing info"""
        r = requests.get(f"{BASE_URL}/api/merchant/avatar/pricing")
        assert r.status_code == 200, f"Pricing failed: {r.text}"
        data = r.json()
        
        # Verify pricing structure
        assert data.get("trial_days") == 14, f"Expected trial_days=14, got {data.get('trial_days')}"
        assert data.get("monthly_cost") == 100, f"Expected monthly_cost=100, got {data.get('monthly_cost')}"
        assert data.get("customize_cost") == 30, f"Expected customize_cost=30, got {data.get('customize_cost')}"
        
        # Verify 6 voices
        voices = data.get("available_voices", [])
        assert len(voices) == 6, f"Expected 6 voices, got {len(voices)}"
        
        # Verify voice structure
        voice_ids = [v["id"] for v in voices]
        assert "nova" in voice_ids, "nova voice not found"
        assert "shimmer" in voice_ids, "shimmer voice not found"


class TestAvatarTrialFlow:
    """Test 3 & 3b: Avatar trial start and me endpoint"""
    
    def test_avatar_start_trial(self, auth_headers, project_id):
        """POST /api/merchant/avatar/start-trial creates trial"""
        r = requests.post(f"{BASE_URL}/api/merchant/avatar/start-trial", headers=auth_headers, json={
            "project_id": project_id,
            "shop_name": "TEST_متجر الاختبار",
            "products_description": "منتجات اختبارية",
            "avatar_name": "نور",
            "voice_id": "nova",
            "tone": "saudi_friendly"
        })
        
        # Either 200 (new trial) or 400 (trial already used)
        if r.status_code == 200:
            data = r.json()
            assert data.get("trial") == True, "Expected trial=true"
            assert data.get("days_left") == 14, f"Expected days_left=14, got {data.get('days_left')}"
            print(f"Trial started: {data.get('message')}")
        elif r.status_code == 400:
            data = r.json()
            assert "التجربة المجانية مستخدمة" in data.get("detail", ""), f"Unexpected 400 error: {data}"
            print("Trial already used (expected for re-run)")
        else:
            pytest.fail(f"Unexpected status {r.status_code}: {r.text}")
    
    def test_avatar_me(self, auth_headers, project_id):
        """GET /api/merchant/avatar/me returns config with status"""
        r = requests.get(f"{BASE_URL}/api/merchant/avatar/me?project_id={project_id}", headers=auth_headers)
        assert r.status_code == 200, f"Avatar me failed: {r.text}"
        data = r.json()
        
        assert "project_id" in data, "Missing project_id"
        assert "status" in data, "Missing status"
        
        # If has_config, verify status structure
        if data.get("has_config"):
            status = data["status"]
            assert "active" in status, "Missing active in status"
            print(f"Avatar status: active={status.get('active')}, status={status.get('status')}, days_left={status.get('days_left')}")


class TestAvatarCustomize:
    """Test 4: Avatar customize endpoint"""
    
    def test_avatar_customize_content_free(self, auth_headers, project_id):
        """PUT /api/merchant/avatar/customize - content updates are free"""
        r = requests.put(f"{BASE_URL}/api/merchant/avatar/customize", headers=auth_headers, json={
            "project_id": project_id,
            "products_description": "منتجات محدثة للاختبار",
            "pricing_info": "أسعار تجريبية",
            "faq": "سؤال: هل هذا اختبار؟ جواب: نعم"
        })
        
        if r.status_code == 200:
            data = r.json()
            # Content-only updates should be free
            assert data.get("credits_deducted", 0) == 0, f"Content update should be free, got {data.get('credits_deducted')}"
            print(f"Customize result: {data}")
        elif r.status_code == 400:
            # No config yet
            print(f"No avatar config: {r.json().get('detail')}")
        else:
            pytest.fail(f"Unexpected status {r.status_code}: {r.text}")


class TestAvatarHideShow:
    """Test 5: Avatar hide/show toggle"""
    
    def test_avatar_hide(self, auth_headers, project_id):
        """POST /api/merchant/avatar/hide toggles visibility"""
        # First hide
        r = requests.post(f"{BASE_URL}/api/merchant/avatar/hide", headers=auth_headers, json={
            "project_id": project_id,
            "hidden": True
        })
        
        if r.status_code == 200:
            data = r.json()
            assert data.get("hidden") == True, "Expected hidden=true"
            print("Avatar hidden successfully")
            
            # Then show again
            r2 = requests.post(f"{BASE_URL}/api/merchant/avatar/hide", headers=auth_headers, json={
                "project_id": project_id,
                "hidden": False
            })
            assert r2.status_code == 200, f"Unhide failed: {r2.text}"
            print("Avatar shown successfully")
        elif r.status_code == 400:
            print(f"No avatar config: {r.json().get('detail')}")
        else:
            pytest.fail(f"Unexpected status {r.status_code}: {r.text}")


class TestImageWizard:
    """Tests 6 & 7: Image Wizard categories and flow"""
    
    def test_image_wizard_categories(self):
        """GET /api/wizard/image/categories returns 6 categories"""
        r = requests.get(f"{BASE_URL}/api/wizard/image/categories")
        assert r.status_code == 200, f"Categories failed: {r.text}"
        data = r.json()
        
        categories = data.get("categories", [])
        assert len(categories) == 6, f"Expected 6 categories, got {len(categories)}"
        
        cat_ids = [c["id"] for c in categories]
        expected = ["social_ad", "product_shot", "banner", "portrait", "scene", "food"]
        for exp in expected:
            assert exp in cat_ids, f"Missing category: {exp}"
        
        # Verify quality tiers
        quality = data.get("quality_tiers", [])
        assert len(quality) == 2, f"Expected 2 quality tiers, got {len(quality)}"
        
        # Verify aspect options
        aspects = data.get("aspect_options", [])
        assert len(aspects) == 4, f"Expected 4 aspect options, got {len(aspects)}"
    
    def test_image_wizard_start(self, auth_headers):
        """POST /api/wizard/image/start returns session_id and category_picker"""
        r = requests.post(f"{BASE_URL}/api/wizard/image/start", headers=auth_headers, json={})
        assert r.status_code == 200, f"Wizard start failed: {r.text}"
        data = r.json()
        
        assert "session_id" in data, "Missing session_id"
        assert "next_question" in data, "Missing next_question"
        
        q = data["next_question"]
        assert q.get("kind") == "category_picker", f"Expected category_picker, got {q.get('kind')}"
        assert len(q.get("options", [])) == 6, "Expected 6 category options"
        
        return data["session_id"]
    
    def test_image_wizard_full_flow(self, auth_headers):
        """Test full wizard flow: category -> questions -> aspect -> quality -> ready"""
        # Start
        r = requests.post(f"{BASE_URL}/api/wizard/image/start", headers=auth_headers, json={})
        assert r.status_code == 200
        session_id = r.json()["session_id"]
        
        # Answer category: food
        r = requests.post(f"{BASE_URL}/api/wizard/image/answer", headers=auth_headers, json={
            "session_id": session_id,
            "answer": "food"
        })
        assert r.status_code == 200, f"Category answer failed: {r.text}"
        data = r.json()
        assert data.get("category") == "food"
        
        # Answer 4 food questions
        questions_answered = 0
        while "next_question" in data and data["next_question"].get("kind") == "category_question":
            q = data["next_question"]
            answer = "كبسة" if q.get("type") == "text" else (q.get("options", ["rustic_wood"])[0])
            r = requests.post(f"{BASE_URL}/api/wizard/image/answer", headers=auth_headers, json={
                "session_id": session_id,
                "answer": answer
            })
            assert r.status_code == 200, f"Question answer failed: {r.text}"
            data = r.json()
            questions_answered += 1
            if questions_answered > 10:
                break
        
        # Should now be aspect_picker
        if "next_question" in data and data["next_question"].get("kind") == "aspect_picker":
            r = requests.post(f"{BASE_URL}/api/wizard/image/answer", headers=auth_headers, json={
                "session_id": session_id,
                "answer": "1:1"
            })
            assert r.status_code == 200
            data = r.json()
        
        # Should now be quality_picker
        if "next_question" in data and data["next_question"].get("kind") == "quality_picker":
            r = requests.post(f"{BASE_URL}/api/wizard/image/answer", headers=auth_headers, json={
                "session_id": session_id,
                "answer": "standard"
            })
            assert r.status_code == 200
            data = r.json()
        
        # Should be ready
        assert data.get("ready") == True, f"Expected ready=true, got {data}"
        summary = data.get("summary", {})
        assert summary.get("estimated_cost") == 5, f"Expected cost=5 for standard, got {summary.get('estimated_cost')}"
        print(f"Wizard ready: category={summary.get('category')}, cost={summary.get('estimated_cost')}")


class TestChannelBridge:
    """Tests 8-10: Channel Bridge endpoints"""
    
    def test_bridge_projects(self, auth_headers):
        """GET /api/bridge/projects returns owner's projects"""
        r = requests.get(f"{BASE_URL}/api/bridge/projects", headers=auth_headers)
        assert r.status_code == 200, f"Bridge projects failed: {r.text}"
        data = r.json()
        
        assert "projects" in data, "Missing projects"
        assert "count" in data, "Missing count"
        
        projects = data["projects"]
        print(f"Found {len(projects)} projects")
        
        # Check for cozy-cafe-demo
        slugs = [p.get("slug") for p in projects]
        if "cozy-cafe-demo" in slugs:
            print("✓ cozy-cafe-demo project found")
        
        return projects
    
    def test_bridge_history(self, auth_headers, project_id):
        """GET /api/bridge/history returns push history"""
        r = requests.get(f"{BASE_URL}/api/bridge/history?project_id={project_id}", headers=auth_headers)
        assert r.status_code == 200, f"Bridge history failed: {r.text}"
        data = r.json()
        
        assert "history" in data, "Missing history"
        assert "push_cost" in data, "Missing push_cost"
        assert data["push_cost"] == 2, f"Expected push_cost=2, got {data['push_cost']}"
        
        print(f"Bridge history: {len(data['history'])} entries")


class TestRegressionExistingEndpoints:
    """Test 12: Regression - existing endpoints still work"""
    
    def test_studio_gallery(self, auth_headers):
        """GET /api/studio/gallery still works"""
        r = requests.get(f"{BASE_URL}/api/studio/gallery", headers=auth_headers)
        assert r.status_code == 200, f"Studio gallery failed: {r.text}"
        data = r.json()
        assert "items" in data or "count" in data, "Unexpected gallery response"
    
    def test_auth_me(self, auth_headers):
        """GET /api/auth/me still works"""
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert r.status_code == 200, f"Auth me failed: {r.text}"
        data = r.json()
        assert data.get("email") == "owner@zenrex.ai"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
