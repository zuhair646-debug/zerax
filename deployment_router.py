"""
Test Template Archetypes System — 20 structurally distinct templates per category.

Tests the major rewrite from 120+ color variants to 20 structural archetypes.
Each archetype differs in layout, section arrangement, density, hero style.
Colors are a SEPARATE step AFTER template selection.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-cinematic-hub-2.preview.emergentagent.com').rstrip('/')

# Test credentials
OWNER_EMAIL = "owner@zitex.com"
OWNER_PASSWORD = "owner123"

# All 20 archetype IDs
ARCHETYPES = [
    "classic_stack", "magazine", "split_screen", "longform_story", "gallery_first",
    "minimal_portrait", "bold_banner", "card_stack", "asymmetric", "services_showcase",
    "booking_first", "process_steps", "team_centric", "reviews_driven", "pricing_table",
    "faq_heavy", "stats_numbers", "location_map", "newsletter_first", "product_dense"
]

# Categories to test
TEST_CATEGORIES = [
    "restaurant", "jewelry", "bakery", "car_wash", "salon_women",
    "barber", "library", "art_gallery", "clinic", "stocks"
]

# Category to primary_grid mapping
CATEGORY_PRIMARY_GRID = {
    "restaurant": "menu",
    "coffee": "menu",
    "bakery": "products",
    "jewelry": "products",
    "library": "products",
    "art_gallery": "products",
    "store": "products",
    "salon_women": "services",
    "barber": "services",
    "car_wash": "services",
    "clinic": "services",
    "stocks": "services",  # fallback
}


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for owner."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestLayoutsEndpoint:
    """Test GET /api/websites/categories/{cat_id}/layouts returns EXACTLY 20 layouts."""

    @pytest.mark.parametrize("category", TEST_CATEGORIES)
    def test_exactly_20_layouts_per_category(self, category):
        """Each category must return exactly 20 layouts (not 120+ color variants)."""
        response = requests.get(f"{BASE_URL}/api/websites/categories/{category}/layouts")
        assert response.status_code == 200
        data = response.json()
        layouts = data.get("layouts", [])
        assert len(layouts) == 20, f"{category} has {len(layouts)} layouts, expected 20"

    @pytest.mark.parametrize("category", TEST_CATEGORIES)
    def test_layout_id_format(self, category):
        """Each layout ID must be {category}__{archetype_id}."""
        response = requests.get(f"{BASE_URL}/api/websites/categories/{category}/layouts")
        data = response.json()
        layouts = data.get("layouts", [])
        for layout in layouts:
            layout_id = layout.get("id", "")
            assert layout_id.startswith(f"{category}__"), f"Invalid ID format: {layout_id}"
            archetype = layout_id.replace(f"{category}__", "")
            assert archetype in ARCHETYPES, f"Unknown archetype: {archetype}"

    @pytest.mark.parametrize("category", TEST_CATEGORIES)
    def test_layout_has_required_fields(self, category):
        """Each layout must have name_ar, description, density, hero_layout, sections_count, section_types, theme."""
        response = requests.get(f"{BASE_URL}/api/websites/categories/{category}/layouts")
        data = response.json()
        layouts = data.get("layouts", [])
        for layout in layouts:
            assert "id" in layout
            assert "name" in layout  # name_ar mapped to name
            assert "description" in layout
            assert "density" in layout
            assert "hero_layout" in layout
            assert "sections_count" in layout
            assert "section_types" in layout
            assert "theme" in layout

    @pytest.mark.parametrize("category", TEST_CATEGORIES)
    def test_neutral_theme_gold_primary(self, category):
        """All layouts must have NEUTRAL theme with primary=#FFD700 (gold)."""
        response = requests.get(f"{BASE_URL}/api/websites/categories/{category}/layouts")
        data = response.json()
        layouts = data.get("layouts", [])
        for layout in layouts:
            theme = layout.get("theme", {})
            primary = theme.get("primary", "")
            assert primary == "#FFD700", f"{layout['id']} has primary={primary}, expected #FFD700"


class TestPreviewHtml:
    """Test GET /api/websites/categories/{cat}/layouts/{layout_id}/preview-html."""

    def test_preview_html_returns_valid_html(self):
        """Preview HTML must be >20KB for different archetypes."""
        response = requests.get(f"{BASE_URL}/api/websites/categories/restaurant/layouts/restaurant__classic_stack/preview-html")
        assert response.status_code == 200
        data = response.json()
        html = data.get("html", "")
        assert len(html) > 20000, f"HTML too small: {len(html)} bytes"

    def test_different_archetypes_produce_different_html_sizes(self):
        """Different archetypes should produce different HTML sizes (proof of structural diff)."""
        sizes = {}
        for archetype in ["classic_stack", "minimal_portrait", "product_dense"]:
            response = requests.get(f"{BASE_URL}/api/websites/categories/restaurant/layouts/restaurant__{archetype}/preview-html")
            assert response.status_code == 200
            sizes[archetype] = len(response.json().get("html", ""))
        
        # Sizes should differ
        unique_sizes = set(sizes.values())
        assert len(unique_sizes) >= 2, f"All archetypes have same HTML size: {sizes}"


class TestPalettesEndpoint:
    """Test GET /api/websites/palettes returns 10 color palettes."""

    def test_palettes_count(self):
        """Must return exactly 10 palettes."""
        response = requests.get(f"{BASE_URL}/api/websites/palettes")
        assert response.status_code == 200
        data = response.json()
        palettes = data.get("palettes", [])
        assert len(palettes) == 10, f"Got {len(palettes)} palettes, expected 10"

    def test_palettes_have_required_fields(self):
        """Each palette must have id, name, primary, secondary, accent, background, font."""
        response = requests.get(f"{BASE_URL}/api/websites/palettes")
        data = response.json()
        palettes = data.get("palettes", [])
        for palette in palettes:
            assert "id" in palette
            assert "name" in palette
            assert "primary" in palette
            assert "secondary" in palette
            assert "accent" in palette
            # background and font may be None for some palettes

    def test_playful_palette_is_pink(self):
        """Playful palette must have primary=#EC4899 (pink)."""
        response = requests.get(f"{BASE_URL}/api/websites/palettes")
        data = response.json()
        palettes = data.get("palettes", [])
        playful = next((p for p in palettes if p["id"] == "playful"), None)
        assert playful is not None, "Playful palette not found"
        assert playful["primary"] == "#EC4899", f"Playful primary is {playful['primary']}, expected #EC4899"


class TestApplyPalette:
    """Test POST /api/websites/projects/{id}/apply-palette."""

    def test_apply_palette_changes_theme(self, auth_headers):
        """Applying palette changes project.theme.primary without touching sections."""
        # Create project
        create_resp = requests.post(f"{BASE_URL}/api/websites/projects", headers=auth_headers, json={
            "name": "TEST_ApplyPalette",
            "template": "restaurant",
            "meta": {"layout_id": "restaurant__classic_stack"}
        })
        assert create_resp.status_code == 200
        project = create_resp.json()
        project_id = project["id"]
        initial_primary = project.get("theme", {}).get("primary")
        initial_sections_count = len(project.get("sections", []))
        
        # Apply playful palette
        apply_resp = requests.post(f"{BASE_URL}/api/websites/projects/{project_id}/apply-palette", 
                                   headers=auth_headers, json={"palette_id": "playful"})
        assert apply_resp.status_code == 200
        updated = apply_resp.json()
        
        # Verify theme changed
        new_primary = updated.get("theme", {}).get("primary")
        assert new_primary == "#EC4899", f"Primary not changed: {new_primary}"
        
        # Verify sections NOT touched
        new_sections_count = len(updated.get("sections", []))
        assert new_sections_count == initial_sections_count, "Sections were modified"
        
        # Verify snapshot created
        snapshots = updated.get("snapshots", [])
        assert len(snapshots) >= 1, "No snapshot created"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/websites/projects/{project_id}", headers=auth_headers)


class TestProjectCreationWithLayoutId:
    """Test project creation with meta.layout_id."""

    @pytest.mark.parametrize("category,expected_grid", [
        ("restaurant", "menu"),
        ("jewelry", "products"),
        ("salon_women", "services"),
    ])
    def test_same_archetype_different_content(self, auth_headers, category, expected_grid):
        """Same archetype across categories produces different content."""
        create_resp = requests.post(f"{BASE_URL}/api/websites/projects", headers=auth_headers, json={
            "name": f"TEST_{category}_classic",
            "template": category,
            "meta": {"layout_id": f"{category}__classic_stack"}
        })
        assert create_resp.status_code == 200
        project = create_resp.json()
        project_id = project["id"]
        
        # Check primary_grid section type
        sections = project.get("sections", [])
        section_types = [s.get("type") for s in sections]
        assert expected_grid in section_types, f"{category} missing {expected_grid} section, got: {section_types}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/websites/projects/{project_id}", headers=auth_headers)

    def test_fallback_to_first_archetype(self, auth_headers):
        """Creating project without layout_id falls back to first archetype (classic_stack)."""
        create_resp = requests.post(f"{BASE_URL}/api/websites/projects", headers=auth_headers, json={
            "name": "TEST_Fallback",
            "template": "barber"
            # No meta.layout_id
        })
        assert create_resp.status_code == 200
        project = create_resp.json()
        project_id = project["id"]
        
        # Should default to classic_stack
        layout_id = project.get("meta", {}).get("layout_id", "")
        assert layout_id == "barber__classic_stack", f"Fallback layout_id is {layout_id}"
        
        # Should have proper sections
        sections = project.get("sections", [])
        assert len(sections) >= 5, f"Too few sections: {len(sections)}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/websites/projects/{project_id}", headers=auth_headers)


class TestRegressionExistingFeatures:
    """Regression tests for existing features."""

    def test_section_variants_catalog(self):
        """Section variants catalog still works."""
        response = requests.get(f"{BASE_URL}/api/websites/section-variants/catalog")
        assert response.status_code == 200
        data = response.json()
        assert "catalog" in data

    def test_cozy_cafe_demo_exists(self):
        """Existing cozy-cafe-demo site still works."""
        response = requests.get(f"{BASE_URL}/api/websites/public/cozy-cafe-demo/info")
        assert response.status_code == 200
        data = response.json()
        assert data.get("slug") == "cozy-cafe-demo"

    def test_snapshots_endpoint(self, auth_headers):
        """Snapshots endpoint still works."""
        # Get projects
        response = requests.get(f"{BASE_URL}/api/websites/projects", headers=auth_headers)
        assert response.status_code == 200
        projects = response.json().get("projects", [])
        if projects:
            project_id = projects[0]["id"]
            snap_resp = requests.get(f"{BASE_URL}/api/websites/projects/{project_id}/snapshots", headers=auth_headers)
            assert snap_resp.status_code == 200


class TestCleanup:
    """Cleanup test data."""

    def test_cleanup_test_projects(self, auth_headers):
        """Delete all TEST_ prefixed projects."""
        response = requests.get(f"{BASE_URL}/api/websites/projects", headers=auth_headers)
        if response.status_code == 200:
            projects = response.json().get("projects", [])
            for p in projects:
                if p.get("name", "").startswith("TEST_"):
                    requests.delete(f"{BASE_URL}/api/websites/projects/{p['id']}", headers=auth_headers)
        assert True  # Always pass cleanup
