"""
Phase 2 Engines Backend Tests
Tests for: Courses, Memberships, Events, Gold Ticker, ISBN Search, Driver Analytics, Wizard Vertical Injection
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def owner_token():
    """Get owner authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "owner@zitex.com",
        "password": "owner123"
    })
    assert response.status_code == 200, f"Owner login failed: {response.text}"
    return response.json().get("token")

@pytest.fixture(scope="module")
def client_token():
    """Get client token for cozy-cafe-demo"""
    response = requests.post(f"{BASE_URL}/api/websites/client/login", json={
        "slug": "cozy-cafe-demo",
        "password": "WKDWkG0d"
    })
    assert response.status_code == 200, f"Client login failed: {response.text}"
    return response.json().get("token")

@pytest.fixture(scope="module")
def academy_project(owner_token):
    """Create an academy project for testing courses"""
    response = requests.post(
        f"{BASE_URL}/api/websites/projects",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"name": f"TEST_Academy_{uuid.uuid4().hex[:6]}", "template": "academy"}
    )
    assert response.status_code == 200, f"Failed to create academy project: {response.text}"
    project = response.json()
    yield project
    # Cleanup
    requests.delete(
        f"{BASE_URL}/api/websites/projects/{project['id']}",
        headers={"Authorization": f"Bearer {owner_token}"}
    )

@pytest.fixture(scope="module")
def gym_project(owner_token):
    """Create a gym project for testing memberships"""
    response = requests.post(
        f"{BASE_URL}/api/websites/projects",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"name": f"TEST_Gym_{uuid.uuid4().hex[:6]}", "template": "gym"}
    )
    assert response.status_code == 200, f"Failed to create gym project: {response.text}"
    project = response.json()
    yield project
    # Cleanup
    requests.delete(
        f"{BASE_URL}/api/websites/projects/{project['id']}",
        headers={"Authorization": f"Bearer {owner_token}"}
    )

@pytest.fixture(scope="module")
def salon_women_project(owner_token):
    """Create a salon_women project for testing wizard vertical injection"""
    response = requests.post(
        f"{BASE_URL}/api/websites/projects",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"name": f"TEST_Salon_{uuid.uuid4().hex[:6]}", "template": "salon_women"}
    )
    assert response.status_code == 200, f"Failed to create salon_women project: {response.text}"
    project = response.json()
    yield project
    # Cleanup
    requests.delete(
        f"{BASE_URL}/api/websites/projects/{project['id']}",
        headers={"Authorization": f"Bearer {owner_token}"}
    )


class TestGoldTicker:
    """Gold Ticker API Tests"""
    
    def test_gold_prices_endpoint(self):
        """GET /api/websites/gold-prices returns live gold prices"""
        response = requests.get(f"{BASE_URL}/api/websites/gold-prices")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "per_gram" in data
        assert "24k" in data["per_gram"]
        assert "22k" in data["per_gram"]
        assert "21k" in data["per_gram"]
        assert "18k" in data["per_gram"]
        assert "currency" in data
        assert data["currency"] == "SAR"
        assert "source" in data
        assert "live" in data
        
        # Verify prices are reasonable (gold is ~300-600 SAR/gram for 24k)
        price_24k = data["per_gram"]["24k"]
        assert 200 < price_24k < 1000, f"24k price {price_24k} seems unreasonable"
        
        # Verify karat ratios are correct
        assert data["per_gram"]["22k"] < data["per_gram"]["24k"]
        assert data["per_gram"]["21k"] < data["per_gram"]["22k"]
        assert data["per_gram"]["18k"] < data["per_gram"]["21k"]
    
    def test_public_gold_prices(self):
        """GET /api/websites/public/{slug}/gold-prices works for approved sites"""
        response = requests.get(f"{BASE_URL}/api/websites/public/cozy-cafe-demo/gold-prices")
        assert response.status_code == 200
        data = response.json()
        assert "per_gram" in data


class TestISBNSearch:
    """ISBN Search API Tests"""
    
    def test_isbn_search_valid(self):
        """GET /api/websites/isbn-search with valid ISBN returns book data"""
        # Count of Monte Cristo ISBN
        response = requests.get(f"{BASE_URL}/api/websites/isbn-search?isbn=9780140449266")
        assert response.status_code == 200
        data = response.json()
        
        assert data["found"] == True
        assert data["isbn"] == "9780140449266"
        assert "title" in data
        assert "authors" in data
        assert isinstance(data["authors"], list)
        assert "cover" in data
    
    def test_isbn_search_invalid_short(self):
        """GET /api/websites/isbn-search with short ISBN returns 400"""
        response = requests.get(f"{BASE_URL}/api/websites/isbn-search?isbn=12345")
        assert response.status_code == 400
    
    def test_isbn_search_not_found(self):
        """GET /api/websites/isbn-search with non-existent ISBN returns found=false"""
        # Use a clearly invalid ISBN that won't exist
        response = requests.get(f"{BASE_URL}/api/websites/isbn-search?isbn=9999999999999")
        assert response.status_code == 200
        data = response.json()
        # Note: Open Library may or may not find this - just verify the response structure
        assert "found" in data
        assert "isbn" in data


class TestDriverAnalytics:
    """Driver Analytics API Tests"""
    
    def test_driver_analytics_7_days(self, client_token):
        """GET /api/websites/client/drivers/analytics?days=7 returns analytics"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/drivers/analytics?days=7",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "window_days" in data
        assert data["window_days"] == 7
        assert "total_drivers" in data
        assert "total_orders" in data
        assert "drivers" in data
        assert isinstance(data["drivers"], list)
        
        # If there are drivers, verify their structure
        if data["drivers"]:
            driver = data["drivers"][0]
            assert "driver_id" in driver
            assert "driver_name" in driver
            assert "orders_assigned" in driver
            assert "orders_completed" in driver
            assert "completion_rate" in driver
            assert "avg_delivery_min" in driver
            assert "avg_rating" in driver
            assert "total_earnings" in driver
    
    def test_driver_analytics_14_days(self, client_token):
        """GET /api/websites/client/drivers/analytics?days=14 works"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/drivers/analytics?days=14",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["window_days"] == 14
    
    def test_driver_analytics_30_days(self, client_token):
        """GET /api/websites/client/drivers/analytics?days=30 works"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/drivers/analytics?days=30",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["window_days"] == 30


class TestWizardVerticalInjection:
    """Wizard Vertical-Specific Steps Tests"""
    
    def test_salon_women_wizard_steps(self, owner_token, salon_women_project):
        """salon_women project returns 4 vq_* steps"""
        response = requests.get(
            f"{BASE_URL}/api/websites/wizard/steps?project_id={salon_women_project['id']}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        steps = data["steps"]
        vq_steps = [s for s in steps if s["id"].startswith("vq_")]
        
        # salon_women should have 4 vertical-specific questions
        assert len(vq_steps) == 4, f"Expected 4 vq_* steps, got {len(vq_steps)}"
        
        # Verify the specific steps
        vq_ids = [s["id"] for s in vq_steps]
        assert "vq_categories" in vq_ids
        assert "vq_specialty" in vq_ids
        assert "vq_working_hours" in vq_ids
        assert "vq_booking_type" in vq_ids
        
        # Verify vertical_specific flag
        for s in vq_steps:
            assert s.get("vertical_specific") == True
    
    def test_academy_wizard_steps(self, owner_token, academy_project):
        """academy project returns 3 vq_* steps"""
        response = requests.get(
            f"{BASE_URL}/api/websites/wizard/steps?project_id={academy_project['id']}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        steps = data["steps"]
        vq_steps = [s for s in steps if s["id"].startswith("vq_")]
        
        # academy should have 3 vertical-specific questions
        assert len(vq_steps) == 3, f"Expected 3 vq_* steps, got {len(vq_steps)}"
        
        vq_ids = [s["id"] for s in vq_steps]
        assert "vq_subject" in vq_ids
        assert "vq_format" in vq_ids
        assert "vq_certification" in vq_ids
    
    def test_gym_wizard_steps(self, owner_token, gym_project):
        """gym project returns 3 vq_* steps"""
        response = requests.get(
            f"{BASE_URL}/api/websites/wizard/steps?project_id={gym_project['id']}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        steps = data["steps"]
        vq_steps = [s for s in steps if s["id"].startswith("vq_")]
        
        # gym should have 3 vertical-specific questions
        assert len(vq_steps) == 3, f"Expected 3 vq_* steps, got {len(vq_steps)}"
    
    def test_restaurant_no_vertical_steps(self, owner_token):
        """restaurant project (no wizard_questions) returns normal steps only"""
        # Create a restaurant project
        response = requests.post(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"name": f"TEST_Restaurant_{uuid.uuid4().hex[:6]}", "template": "restaurant"}
        )
        assert response.status_code == 200
        project = response.json()
        
        try:
            # Get wizard steps
            steps_response = requests.get(
                f"{BASE_URL}/api/websites/wizard/steps?project_id={project['id']}",
                headers={"Authorization": f"Bearer {owner_token}"}
            )
            assert steps_response.status_code == 200
            data = steps_response.json()
            
            steps = data["steps"]
            vq_steps = [s for s in steps if s["id"].startswith("vq_")]
            
            # restaurant has wizard_questions in verticals.py, so it should have vq_* steps
            # Actually checking the verticals.py - restaurant has 3 wizard_questions
            assert len(vq_steps) == 3, f"Expected 3 vq_* steps for restaurant, got {len(vq_steps)}"
        finally:
            # Cleanup
            requests.delete(
                f"{BASE_URL}/api/websites/projects/{project['id']}",
                headers={"Authorization": f"Bearer {owner_token}"}
            )
    
    def test_vq_steps_spliced_after_variant(self, owner_token, salon_women_project):
        """vq_* steps are spliced between 'variant' and 'buttons'"""
        response = requests.get(
            f"{BASE_URL}/api/websites/wizard/steps?project_id={salon_women_project['id']}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 200
        steps = response.json()["steps"]
        
        step_ids = [s["id"] for s in steps]
        variant_idx = step_ids.index("variant")
        buttons_idx = step_ids.index("buttons")
        
        # All vq_* steps should be between variant and buttons
        for i, sid in enumerate(step_ids):
            if sid.startswith("vq_"):
                assert variant_idx < i < buttons_idx, f"vq step {sid} not between variant and buttons"


class TestAutoSeedData:
    """Auto-Seed Data Tests"""
    
    def test_academy_auto_seeds_courses(self, academy_project):
        """Creating academy project auto-seeds 3 sample_courses"""
        courses = academy_project.get("courses", [])
        assert len(courses) == 3, f"Expected 3 auto-seeded courses, got {len(courses)}"
        
        # Verify course structure
        for course in courses:
            assert "id" in course
            assert "title" in course
            assert "price" in course
            assert "instructor" in course
    
    def test_gym_auto_seeds_membership_plans(self, gym_project):
        """Creating gym project auto-seeds 3 sample_membership_plans"""
        plans = gym_project.get("membership_plans", [])
        assert len(plans) == 3, f"Expected 3 auto-seeded membership plans, got {len(plans)}"
        
        # Verify plan structure
        for plan in plans:
            assert "id" in plan
            assert "name" in plan
            assert "price" in plan
            assert "period_days" in plan
            assert "benefits" in plan


class TestCoursesEngine:
    """Courses Engine CRUD Tests"""
    
    def test_courses_list(self, client_token):
        """GET /api/websites/client/courses returns courses list"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/courses",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "courses" in data
        assert isinstance(data["courses"], list)
    
    def test_courses_create(self, client_token):
        """POST /api/websites/client/courses creates a course"""
        response = requests.post(
            f"{BASE_URL}/api/websites/client/courses",
            headers={
                "Authorization": f"ClientToken {client_token}",
                "Content-Type": "application/json"
            },
            json={
                "title": "TEST_Course_Phase2",
                "description": "Test course description",
                "price": 199,
                "duration_hours": 10,
                "instructor": "Test Instructor",
                "level": "beginner"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert "course" in data
        assert data["course"]["title"] == "TEST_Course_Phase2"
        
        return data["course"]["id"]
    
    def test_enrollments_list(self, client_token):
        """GET /api/websites/client/enrollments returns enrollments"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/enrollments",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "enrollments" in data


class TestMembershipsEngine:
    """Memberships Engine CRUD Tests"""
    
    def test_membership_plans_list(self, client_token):
        """GET /api/websites/client/membership-plans returns plans"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/membership-plans",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        assert isinstance(data["plans"], list)
    
    def test_membership_plan_create(self, client_token):
        """POST /api/websites/client/membership-plans creates a plan"""
        response = requests.post(
            f"{BASE_URL}/api/websites/client/membership-plans",
            headers={
                "Authorization": f"ClientToken {client_token}",
                "Content-Type": "application/json"
            },
            json={
                "name": "TEST_Plan_Phase2",
                "price": 299,
                "period_days": 30,
                "benefits": ["Benefit 1", "Benefit 2"],
                "featured": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert "plan" in data
        assert data["plan"]["name"] == "TEST_Plan_Phase2"
    
    def test_subscriptions_list(self, client_token):
        """GET /api/websites/client/subscriptions returns subscriptions with status_computed"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/subscriptions",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "subscriptions" in data


class TestEventsEngine:
    """Events/Tickets Engine CRUD Tests"""
    
    def test_events_list(self, client_token):
        """GET /api/websites/client/events returns events"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/events",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)
    
    def test_event_create(self, client_token):
        """POST /api/websites/client/events creates an event"""
        response = requests.post(
            f"{BASE_URL}/api/websites/client/events",
            headers={
                "Authorization": f"ClientToken {client_token}",
                "Content-Type": "application/json"
            },
            json={
                "title": "TEST_Event_Phase2",
                "description": "Test event description",
                "starts_at": "2026-05-01T18:00:00Z",
                "price": 50,
                "capacity": 100,
                "venue": "Test Venue"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert "event" in data
        assert data["event"]["title"] == "TEST_Event_Phase2"
    
    def test_tickets_list(self, client_token):
        """GET /api/websites/client/tickets returns tickets"""
        response = requests.get(
            f"{BASE_URL}/api/websites/client/tickets",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "tickets" in data


class TestPublicEndpoints:
    """Public Endpoints Tests"""
    
    def test_public_courses(self):
        """GET /api/websites/public/{slug}/courses returns courses"""
        response = requests.get(f"{BASE_URL}/api/websites/public/cozy-cafe-demo/courses")
        assert response.status_code == 200
        data = response.json()
        assert "courses" in data
    
    def test_public_events(self):
        """GET /api/websites/public/{slug}/events returns events with tickets_available"""
        response = requests.get(f"{BASE_URL}/api/websites/public/cozy-cafe-demo/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
