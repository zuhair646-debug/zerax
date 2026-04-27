"""
Test suite for Zitex Website Studio Wizard Feature
Tests: Templates, Variants, Wizard Steps, Project Creation, Wizard Answers, Independence
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "owner@zitex.com"
TEST_PASSWORD = "owner123"


class TestPublicEndpoints:
    """Public endpoints that don't require authentication"""
    
    def test_get_templates(self):
        """GET /api/websites/templates returns list of templates"""
        response = requests.get(f"{BASE_URL}/api/websites/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) >= 5  # store, restaurant, company, portfolio, saas, blank
        # Verify template structure
        template = data["templates"][0]
        assert "id" in template
        assert "name" in template
        assert "icon" in template
        assert "business_type" in template
        print(f"✓ GET /api/websites/templates - {len(data['templates'])} templates returned")
    
    def test_get_wizard_steps(self):
        """GET /api/websites/wizard/steps returns 10 wizard steps"""
        response = requests.get(f"{BASE_URL}/api/websites/wizard/steps")
        assert response.status_code == 200
        data = response.json()
        assert "steps" in data
        steps = data["steps"]
        assert len(steps) == 10  # buttons, colors, typography, features, dashboard, dashboard_items, sections, branding, payment, review
        
        # Verify expected step IDs
        step_ids = [s["id"] for s in steps]
        expected_ids = ["buttons", "colors", "typography", "features", "dashboard", "dashboard_items", "sections", "branding", "payment", "review"]
        for expected in expected_ids:
            assert expected in step_ids, f"Missing step: {expected}"
        print(f"✓ GET /api/websites/wizard/steps - {len(steps)} steps returned")
    
    def test_get_variants(self):
        """GET /api/websites/variants returns 10 style variants"""
        response = requests.get(f"{BASE_URL}/api/websites/variants")
        assert response.status_code == 200
        data = response.json()
        assert "variants" in data
        assert len(data["variants"]) == 10
        # Verify variant structure
        variant = data["variants"][0]
        assert "id" in variant
        assert "name" in variant
        assert "theme" in variant
        print(f"✓ GET /api/websites/variants - {len(data['variants'])} variants returned")
    
    def test_get_template_variants(self):
        """GET /api/websites/templates/{id}/variants returns 10 variants for template"""
        response = requests.get(f"{BASE_URL}/api/websites/templates/restaurant/variants")
        assert response.status_code == 200
        data = response.json()
        assert "variants" in data
        assert len(data["variants"]) == 10
        # Verify variant has template_id
        variant = data["variants"][0]
        assert variant["template_id"] == "restaurant"
        assert variant["business_type"] == "restaurant"
        print(f"✓ GET /api/websites/templates/restaurant/variants - {len(data['variants'])} variants")
    
    def test_get_variant_preview_html(self):
        """GET /api/websites/templates/{id}/variants/{variant_id}/preview-html returns HTML"""
        response = requests.get(f"{BASE_URL}/api/websites/templates/restaurant/variants/dark_pro/preview-html")
        assert response.status_code == 200
        data = response.json()
        assert "html" in data
        assert "<!DOCTYPE html>" in data["html"]
        assert "مطعم" in data["html"]  # Arabic content
        print("✓ GET /api/websites/templates/restaurant/variants/dark_pro/preview-html - HTML returned")


class TestAuthenticatedEndpoints:
    """Endpoints that require authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.project_id = None
    
    def test_create_project_initializes_wizard(self):
        """POST /api/websites/projects auto-initializes wizard state with step='buttons'"""
        response = requests.post(f"{BASE_URL}/api/websites/projects", 
            headers=self.headers,
            json={
                "name": "TEST_مطعم ويزارد",
                "template": "restaurant",
                "business_type": "restaurant"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify wizard initialization
        assert "wizard" in data
        assert data["wizard"]["active"] == True
        assert data["wizard"]["step"] == "buttons"
        assert data["wizard"]["answers"] == {}
        assert data["wizard"]["completed"] == []
        
        # Verify first question in chat
        assert "chat" in data
        assert len(data["chat"]) >= 1
        assert data["chat"][0]["role"] == "assistant"
        assert "الأزرار" in data["chat"][0]["content"]  # Question about buttons
        
        self.project_id = data["id"]
        print(f"✓ POST /api/websites/projects - wizard initialized with step='buttons'")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/websites/projects/{data['id']}", headers=self.headers)
    
    def test_wizard_answer_buttons_full(self):
        """POST /api/websites/projects/{id}/wizard/answer with step=buttons,value=full sets theme.radius='full'"""
        # Create project first
        create_resp = requests.post(f"{BASE_URL}/api/websites/projects", 
            headers=self.headers,
            json={"name": "TEST_buttons_test", "template": "restaurant", "business_type": "restaurant"}
        )
        project_id = create_resp.json()["id"]
        
        # Answer buttons step
        response = requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers,
            json={"step": "buttons", "value": "full"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify theme.radius is set to 'full'
        assert data["theme"]["radius"] == "full"
        # Verify wizard advanced to 'colors'
        assert data["wizard"]["step"] == "colors"
        assert "buttons" in data["wizard"]["completed"]
        assert data["wizard"]["answers"]["buttons"] == "full"
        
        print("✓ POST wizard/answer step=buttons,value=full - theme.radius='full', advanced to 'colors'")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/websites/projects/{project_id}", headers=self.headers)
    
    def test_wizard_answer_colors_warm(self):
        """POST /api/websites/projects/{id}/wizard/answer with step=colors,value=warm applies warm palette"""
        # Create project and advance to colors
        create_resp = requests.post(f"{BASE_URL}/api/websites/projects", 
            headers=self.headers,
            json={"name": "TEST_colors_test", "template": "restaurant", "business_type": "restaurant"}
        )
        project_id = create_resp.json()["id"]
        
        # Answer buttons first
        requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers, json={"step": "buttons", "value": "full"})
        
        # Answer colors step with 'warm'
        response = requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers,
            json={"step": "colors", "value": "warm"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify warm palette applied (primary=#F59E0B)
        assert data["theme"]["primary"] == "#F59E0B"
        # Verify wizard advanced to 'typography'
        assert data["wizard"]["step"] == "typography"
        
        print("✓ POST wizard/answer step=colors,value=warm - primary=#F59E0B, advanced to 'typography'")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/websites/projects/{project_id}", headers=self.headers)
    
    def test_wizard_answer_features_array(self):
        """POST /api/websites/projects/{id}/wizard/answer with step=features as ARRAY saves multiple values"""
        # Create project and advance to features
        create_resp = requests.post(f"{BASE_URL}/api/websites/projects", 
            headers=self.headers,
            json={"name": "TEST_features_test", "template": "restaurant", "business_type": "restaurant"}
        )
        project_id = create_resp.json()["id"]
        
        # Advance through buttons, colors, typography
        requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers, json={"step": "buttons", "value": "full"})
        requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers, json={"step": "colors", "value": "warm"})
        requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers, json={"step": "typography", "value": "Cairo"})
        
        # Answer features with array
        response = requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers,
            json={"step": "features", "value": ["delivery", "reservation", "whatsapp"]}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify features saved as array
        assert data["wizard"]["answers"]["features"] == ["delivery", "reservation", "whatsapp"]
        # Verify wizard advanced to 'dashboard'
        assert data["wizard"]["step"] == "dashboard"
        
        print("✓ POST wizard/answer step=features as ARRAY - saved multiple values, advanced to 'dashboard'")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/websites/projects/{project_id}", headers=self.headers)
    
    def test_dashboard_items_skip_when_none(self):
        """dashboard_items step should SKIP when dashboard='none' (conditional)"""
        # Create project and advance to dashboard
        create_resp = requests.post(f"{BASE_URL}/api/websites/projects", 
            headers=self.headers,
            json={"name": "TEST_dashboard_skip", "template": "restaurant", "business_type": "restaurant"}
        )
        project_id = create_resp.json()["id"]
        
        # Advance through buttons, colors, typography, features
        requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers, json={"step": "buttons", "value": "full"})
        requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers, json={"step": "colors", "value": "warm"})
        requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers, json={"step": "typography", "value": "Cairo"})
        requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers, json={"step": "features", "value": ["delivery"]})
        
        # Answer dashboard with 'none'
        response = requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers,
            json={"step": "dashboard", "value": "none"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify wizard SKIPPED dashboard_items and went to 'sections'
        assert data["wizard"]["step"] == "sections", f"Expected 'sections', got '{data['wizard']['step']}'"
        assert data["wizard"]["answers"]["dashboard"] == "none"
        
        print("✓ dashboard_items step SKIPPED when dashboard='none' - advanced directly to 'sections'")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/websites/projects/{project_id}", headers=self.headers)
    
    def test_wizard_answer_sections_filters(self):
        """POST /api/websites/projects/{id}/wizard/answer with step=sections filters sections"""
        # Create project and advance to sections
        create_resp = requests.post(f"{BASE_URL}/api/websites/projects", 
            headers=self.headers,
            json={"name": "TEST_sections_filter", "template": "restaurant", "business_type": "restaurant"}
        )
        project_id = create_resp.json()["id"]
        
        # Advance through steps
        requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers, json={"step": "buttons", "value": "full"})
        requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers, json={"step": "colors", "value": "warm"})
        requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers, json={"step": "typography", "value": "Cairo"})
        requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers, json={"step": "features", "value": ["delivery"]})
        requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers, json={"step": "dashboard", "value": "none"})
        
        # Answer sections with specific selection
        response = requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/answer",
            headers=self.headers,
            json={"step": "sections", "value": ["hero", "about", "menu", "contact"]}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify sections filtered (+ footer always added)
        section_types = [s["type"] for s in data["sections"]]
        assert "hero" in section_types
        assert "about" in section_types
        assert "menu" in section_types
        assert "contact" in section_types
        assert "footer" in section_types  # Footer always added
        
        print(f"✓ POST wizard/answer step=sections - filtered to {len(data['sections'])} sections (+footer)")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/websites/projects/{project_id}", headers=self.headers)
    
    def test_apply_variant_keeps_sections(self):
        """POST /api/websites/projects/{id}/apply-variant swaps theme but keeps sections by default"""
        # Create project
        create_resp = requests.post(f"{BASE_URL}/api/websites/projects", 
            headers=self.headers,
            json={"name": "TEST_apply_variant", "template": "restaurant", "business_type": "restaurant"}
        )
        project_id = create_resp.json()["id"]
        original_sections_count = len(create_resp.json()["sections"])
        
        # Apply variant with replace_sections=false
        response = requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/apply-variant",
            headers=self.headers,
            json={"template_id": "restaurant", "variant_id": "dark_pro", "replace_sections": False}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify theme changed to dark_pro
        assert data["theme"]["primary"] == "#06B6D4"
        assert data["theme"]["background"] == "#020617"
        
        # Verify sections count unchanged
        assert len(data["sections"]) == original_sections_count
        
        print("✓ POST apply-variant - theme swapped to dark_pro, sections preserved")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/websites/projects/{project_id}", headers=self.headers)
    
    def test_wizard_chat_free_text(self):
        """POST /api/websites/projects/{id}/wizard/chat accepts free-text and returns response"""
        # Create project
        create_resp = requests.post(f"{BASE_URL}/api/websites/projects", 
            headers=self.headers,
            json={"name": "TEST_wizard_chat", "template": "restaurant", "business_type": "restaurant"}
        )
        project_id = create_resp.json()["id"]
        
        # Send free-text chat
        response = requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/wizard/chat",
            headers=self.headers,
            json={"message": "أريد موقع لمطعم يقدم توصيل"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "project" in data
        assert "response" in data
        assert len(data["response"]) > 0  # AI responded
        
        print(f"✓ POST wizard/chat - free-text accepted, AI response: {data['response'][:50]}...")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/websites/projects/{project_id}", headers=self.headers)
    
    def test_independence_request(self):
        """POST /api/websites/projects/{id}/independence/request returns hosting guides"""
        # Create project
        create_resp = requests.post(f"{BASE_URL}/api/websites/projects", 
            headers=self.headers,
            json={"name": "TEST_independence", "template": "restaurant", "business_type": "restaurant"}
        )
        project_id = create_resp.json()["id"]
        
        # Request independence
        response = requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/independence/request",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response
        assert data["ok"] == True
        assert "guides" in data
        assert len(data["guides"]) == 3  # Vercel, Netlify, GitHub
        
        guide_ids = [g["id"] for g in data["guides"]]
        assert "vercel" in guide_ids
        assert "netlify" in guide_ids
        assert "github" in guide_ids
        
        print("✓ POST independence/request - returns Vercel/Netlify/GitHub guides")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/websites/projects/{project_id}", headers=self.headers)


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_cleanup_test_projects(self):
        """Delete all TEST_ prefixed projects"""
        response = requests.get(f"{BASE_URL}/api/websites/projects", headers=self.headers)
        if response.status_code == 200:
            projects = response.json().get("projects", [])
            deleted = 0
            for p in projects:
                if p.get("name", "").startswith("TEST_"):
                    requests.delete(f"{BASE_URL}/api/websites/projects/{p['id']}", headers=self.headers)
                    deleted += 1
            print(f"✓ Cleanup - deleted {deleted} TEST_ prefixed projects")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
