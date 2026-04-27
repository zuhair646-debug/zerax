"""
Test suite for 8 new verticals and category picker redesign
Tests: salon_women, bakery, car_wash, sports_club, library, art_gallery, maintenance, jewelry
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCategoriesAPI:
    """Test GET /api/websites/categories returns 20 categories with images"""
    
    def test_categories_count(self):
        """Should return 20 categories"""
        response = requests.get(f"{BASE_URL}/api/websites/categories")
        assert response.status_code == 200
        data = response.json()
        categories = data.get('categories', [])
        assert len(categories) == 20, f"Expected 20 categories, got {len(categories)}"
    
    def test_categories_have_images(self):
        """Each category should have an image URL"""
        response = requests.get(f"{BASE_URL}/api/websites/categories")
        assert response.status_code == 200
        data = response.json()
        categories = data.get('categories', [])
        
        for cat in categories:
            assert 'image' in cat, f"Category {cat['id']} missing image"
            assert cat['image'].startswith('https://'), f"Category {cat['id']} has invalid image URL"
    
    def test_categories_have_layouts_count(self):
        """Each category should have layouts_count=120"""
        response = requests.get(f"{BASE_URL}/api/websites/categories")
        assert response.status_code == 200
        data = response.json()
        categories = data.get('categories', [])
        
        for cat in categories:
            assert cat.get('layouts_count') == 120, f"Category {cat['id']} has {cat.get('layouts_count')} layouts, expected 120"
    
    def test_new_categories_present(self):
        """All 8 new categories should be present"""
        response = requests.get(f"{BASE_URL}/api/websites/categories")
        assert response.status_code == 200
        data = response.json()
        categories = data.get('categories', [])
        cat_ids = [c['id'] for c in categories]
        
        new_cats = ['salon_women', 'bakery', 'car_wash', 'sports_club', 'library', 'art_gallery', 'maintenance', 'jewelry']
        for cat in new_cats:
            assert cat in cat_ids, f"New category {cat} not found"


class TestVerticalsAPI:
    """Test GET /api/websites/verticals returns 17 verticals"""
    
    def test_verticals_count(self):
        """Should return 17 verticals"""
        response = requests.get(f"{BASE_URL}/api/websites/verticals")
        assert response.status_code == 200
        data = response.json()
        verticals = data.get('verticals', [])
        assert len(verticals) == 17, f"Expected 17 verticals, got {len(verticals)}"
    
    def test_new_verticals_present(self):
        """All 8 new verticals should be present with Arabic names"""
        response = requests.get(f"{BASE_URL}/api/websites/verticals")
        assert response.status_code == 200
        data = response.json()
        verticals = data.get('verticals', [])
        vert_ids = [v['id'] for v in verticals]
        
        new_verts = ['salon_women', 'bakery', 'car_wash', 'sports_club', 'library', 'art_gallery', 'maintenance', 'jewelry']
        for vert in new_verts:
            assert vert in vert_ids, f"New vertical {vert} not found"
    
    def test_new_verticals_have_arabic_names(self):
        """New verticals should have Arabic names"""
        response = requests.get(f"{BASE_URL}/api/websites/verticals")
        assert response.status_code == 200
        data = response.json()
        verticals = data.get('verticals', [])
        
        expected_names = {
            'salon_women': 'صالون نساء',
            'bakery': 'مخبز وحلويات',
            'car_wash': 'غسيل سيارات متنقل',
            'sports_club': 'نوادي رياضية',
            'library': 'مكتبة وقرطاسية',
            'art_gallery': 'معارض فنية',
            'maintenance': 'فني صيانة منزلية',
            'jewelry': 'مجوهرات وذهب'
        }
        
        for vert in verticals:
            if vert['id'] in expected_names:
                assert vert['name_ar'] == expected_names[vert['id']], f"Vertical {vert['id']} has wrong Arabic name"


class TestCategoryLayouts:
    """Test GET /api/websites/categories/{cat_id}/layouts returns 120 layouts for new categories"""
    
    @pytest.mark.parametrize("category", ['salon_women', 'bakery', 'car_wash', 'sports_club', 'library', 'art_gallery', 'maintenance', 'jewelry'])
    def test_new_category_layouts(self, category):
        """Each new category should have 120 layouts via aliases"""
        response = requests.get(f"{BASE_URL}/api/websites/categories/{category}/layouts")
        assert response.status_code == 200
        data = response.json()
        layouts = data.get('layouts', [])
        assert len(layouts) == 120, f"Category {category} has {len(layouts)} layouts, expected 120"


class TestProjectCreationWithSampleData:
    """Test project creation auto-seeds sample products/services for new categories"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token for owner"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "owner@zitex.com",
            "password": "owner123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_bakery_seeds_products(self, auth_token):
        """Bakery project should seed 3+ products"""
        response = requests.post(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "TEST_مخبز", "template": "bakery"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('vertical') == 'bakery'
        products = data.get('products', [])
        assert len(products) >= 3, f"Bakery should seed 3+ products, got {len(products)}"
    
    def test_jewelry_seeds_products(self, auth_token):
        """Jewelry project should seed 3+ products"""
        response = requests.post(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "TEST_مجوهرات", "template": "jewelry"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('vertical') == 'jewelry'
        products = data.get('products', [])
        assert len(products) >= 3, f"Jewelry should seed 3+ products, got {len(products)}"
    
    def test_library_seeds_products(self, auth_token):
        """Library project should seed 3+ products"""
        response = requests.post(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "TEST_مكتبة", "template": "library"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('vertical') == 'library'
        products = data.get('products', [])
        assert len(products) >= 3, f"Library should seed 3+ products, got {len(products)}"
    
    def test_art_gallery_seeds_products(self, auth_token):
        """Art gallery project should seed 2+ products"""
        response = requests.post(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "TEST_معرض", "template": "art_gallery"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('vertical') == 'art_gallery'
        products = data.get('products', [])
        assert len(products) >= 2, f"Art gallery should seed 2+ products, got {len(products)}"
    
    def test_salon_women_seeds_services(self, auth_token):
        """Salon women project should seed 3+ services"""
        response = requests.post(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "TEST_صالون", "template": "salon_women"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('vertical') == 'salon_women'
        services = data.get('services', [])
        assert len(services) >= 3, f"Salon women should seed 3+ services, got {len(services)}"
    
    def test_car_wash_seeds_services(self, auth_token):
        """Car wash project should seed 3+ services"""
        response = requests.post(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "TEST_غسيل", "template": "car_wash"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('vertical') == 'car_wash'
        services = data.get('services', [])
        assert len(services) >= 3, f"Car wash should seed 3+ services, got {len(services)}"
    
    def test_sports_club_seeds_services(self, auth_token):
        """Sports club project should seed 3+ services"""
        response = requests.post(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "TEST_نادي", "template": "sports_club"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('vertical') == 'sports_club'
        services = data.get('services', [])
        assert len(services) >= 3, f"Sports club should seed 3+ services, got {len(services)}"
    
    def test_maintenance_seeds_services(self, auth_token):
        """Maintenance project should seed 3+ services"""
        response = requests.post(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "TEST_صيانة", "template": "maintenance"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('vertical') == 'maintenance'
        services = data.get('services', [])
        assert len(services) >= 3, f"Maintenance should seed 3+ services, got {len(services)}"


class TestRegressionExistingVerticals:
    """Regression tests for existing verticals"""
    
    def test_cozy_cafe_demo_exists(self):
        """Existing cozy-cafe-demo site should still work"""
        response = requests.get(f"{BASE_URL}/api/websites/public/cozy-cafe-demo/info")
        assert response.status_code == 200
        data = response.json()
        assert data.get('slug') == 'cozy-cafe-demo'
        assert data.get('template') == 'restaurant'
    
    def test_section_variants_catalog(self):
        """Section variants catalog should still work"""
        response = requests.get(f"{BASE_URL}/api/websites/section-variants/catalog")
        assert response.status_code == 200
        data = response.json()
        catalog = data.get('catalog', {})
        assert len(catalog) >= 5, "Should have at least 5 section types with variants"
        
        # Check specific section types
        assert 'menu' in catalog
        assert 'gallery' in catalog
        assert 'testimonials' in catalog
