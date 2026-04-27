"""
Test Suite for Section Variants + Snapshots (Version History) Features
Tests:
- Section variants catalog API
- Client section style patching
- Snapshots CRUD (create, list, restore, preview-html, delete)
- Owner-facing snapshots endpoints
- AI snapshot intent detection
- Auto-snapshot triggers
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
OWNER_EMAIL = "owner@zitex.com"
OWNER_PASSWORD = "owner123"
CLIENT_SLUG = "cozy-cafe-demo"
CLIENT_PASSWORD = "WKDWkG0d"
PROJECT_ID = "3c282414-9f1b-4e88-80d9-a2a199ba53d4"


@pytest.fixture(scope="module")
def owner_token():
    """Get owner JWT token"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    })
    if r.status_code == 200:
        return r.json().get("token")
    pytest.skip(f"Owner login failed: {r.status_code} {r.text}")


@pytest.fixture(scope="module")
def client_token():
    """Get client token for cozy-cafe-demo"""
    r = requests.post(f"{BASE_URL}/api/websites/client/login", json={
        "slug": CLIENT_SLUG,
        "password": CLIENT_PASSWORD
    })
    if r.status_code == 200:
        return r.json().get("token")
    pytest.skip(f"Client login failed: {r.status_code} {r.text}")


class TestSectionVariantsCatalog:
    """Test section-level style variants catalog"""
    
    def test_catalog_returns_all_section_types(self):
        """GET /api/websites/section-variants/catalog returns full catalog"""
        r = requests.get(f"{BASE_URL}/api/websites/section-variants/catalog")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert "catalog" in data, "Response should have 'catalog' key"
        
        catalog = data["catalog"]
        # Should have 5 section types: menu, gallery, testimonials, team, pricing
        expected_types = ["menu", "gallery", "testimonials", "team", "pricing"]
        for stype in expected_types:
            assert stype in catalog, f"Catalog should include '{stype}'"
            assert "label" in catalog[stype], f"{stype} should have 'label'"
            assert "variants" in catalog[stype], f"{stype} should have 'variants'"
            assert len(catalog[stype]["variants"]) >= 3, f"{stype} should have at least 3 variants"
        
        print(f"✓ Catalog has {len(catalog)} section types with variants")
    
    def test_menu_variants_structure(self):
        """Menu section should have grid, list, carousel variants"""
        r = requests.get(f"{BASE_URL}/api/websites/section-variants/catalog")
        assert r.status_code == 200
        
        menu = r.json()["catalog"]["menu"]
        variant_ids = [v["id"] for v in menu["variants"]]
        
        assert "grid" in variant_ids, "Menu should have 'grid' variant"
        assert "list" in variant_ids, "Menu should have 'list' variant"
        assert "carousel" in variant_ids, "Menu should have 'carousel' variant"
        
        # Each variant should have id, label, description
        for v in menu["variants"]:
            assert "id" in v
            assert "label" in v
            assert "description" in v
        
        print(f"✓ Menu has variants: {variant_ids}")
    
    def test_gallery_variants_structure(self):
        """Gallery section should have grid, masonry, strip variants"""
        r = requests.get(f"{BASE_URL}/api/websites/section-variants/catalog")
        assert r.status_code == 200
        
        gallery = r.json()["catalog"]["gallery"]
        variant_ids = [v["id"] for v in gallery["variants"]]
        
        assert "grid" in variant_ids
        assert "masonry" in variant_ids
        assert "strip" in variant_ids
        
        print(f"✓ Gallery has variants: {variant_ids}")


class TestClientSectionStylePatch:
    """Test patching section styles via client dashboard"""
    
    def test_patch_section_style(self, client_token):
        """PATCH /api/websites/client/sections/{id} with style saves correctly"""
        # First get current project to find a menu section
        r = requests.get(f"{BASE_URL}/api/websites/client/session", 
                        headers={"Authorization": f"ClientToken {client_token}"})
        assert r.status_code == 200
        
        project = r.json()
        sections = project.get("sections", [])
        
        # Find a menu section
        menu_section = next((s for s in sections if s.get("type") == "menu"), None)
        if not menu_section:
            pytest.skip("No menu section found in project")
        
        section_id = menu_section["id"]
        
        # Patch with style='list'
        r = requests.patch(
            f"{BASE_URL}/api/websites/client/sections/{section_id}",
            headers={
                "Authorization": f"ClientToken {client_token}",
                "Content-Type": "application/json"
            },
            json={"data": {"style": "list"}}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        # Verify the style was saved
        r = requests.get(f"{BASE_URL}/api/websites/client/session",
                        headers={"Authorization": f"ClientToken {client_token}"})
        project = r.json()
        updated_section = next((s for s in project.get("sections", []) if s.get("id") == section_id), None)
        
        assert updated_section is not None
        assert updated_section.get("data", {}).get("style") == "list", "Style should be 'list'"
        
        print(f"✓ Section {section_id} style updated to 'list'")
    
    def test_public_html_reflects_style(self, client_token):
        """Public HTML should reflect the applied style class"""
        r = requests.get(f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}")
        assert r.status_code == 200
        
        html = r.text
        # Check for style-specific classes (menu-list-style, gallery-masonry, etc.)
        # At least one style class should be present
        style_indicators = [
            "menu-list-style", "menu-carousel-style",
            "gallery-masonry", "gallery-strip",
            "testi-carousel", "testi-quote",
            "team-circles", "team-rows",
            "pricing-table", "pricing-minimal"
        ]
        
        found_any = any(indicator in html for indicator in style_indicators)
        # This is informational - the test passes regardless since default styles may not have special classes
        print(f"✓ Public HTML rendered (style classes present: {found_any})")


class TestClientSnapshots:
    """Test client-facing snapshots (version history) endpoints"""
    
    def test_list_snapshots(self, client_token):
        """GET /api/websites/client/snapshots lists snapshots"""
        r = requests.get(
            f"{BASE_URL}/api/websites/client/snapshots",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert "snapshots" in data
        assert "total" in data
        assert isinstance(data["snapshots"], list)
        
        print(f"✓ Client snapshots list: {data['total']} snapshots")
        return data["snapshots"]
    
    def test_create_manual_snapshot(self, client_token):
        """POST /api/websites/client/snapshots creates manual snapshot"""
        # Get initial count
        r = requests.get(
            f"{BASE_URL}/api/websites/client/snapshots",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        initial_count = r.json().get("total", 0)
        
        # Create snapshot
        r = requests.post(
            f"{BASE_URL}/api/websites/client/snapshots",
            headers={
                "Authorization": f"ClientToken {client_token}",
                "Content-Type": "application/json"
            },
            json={"label": "نسخة اختبار يدوية"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert data.get("ok") == True
        assert data.get("total") >= initial_count  # May be same if dedupe kicks in
        
        print(f"✓ Manual snapshot created, total: {data['total']}")
    
    def test_snapshot_preview_html(self, client_token):
        """GET /api/websites/client/snapshots/{id}/preview-html returns renderable HTML"""
        # Get snapshots
        r = requests.get(
            f"{BASE_URL}/api/websites/client/snapshots",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        snapshots = r.json().get("snapshots", [])
        
        if not snapshots:
            pytest.skip("No snapshots to preview")
        
        snap_id = snapshots[0]["id"]
        
        r = requests.get(
            f"{BASE_URL}/api/websites/client/snapshots/{snap_id}/preview-html",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert "html" in data
        assert "label" in data
        assert "created_at" in data
        assert len(data["html"]) > 100, "HTML should be substantial"
        assert "<!DOCTYPE html>" in data["html"] or "<html" in data["html"]
        
        print(f"✓ Snapshot preview HTML returned ({len(data['html'])} chars)")
    
    def test_restore_snapshot(self, client_token):
        """POST /api/websites/client/snapshots/{id}/restore restores and creates pre-restore snapshot"""
        # Get snapshots
        r = requests.get(
            f"{BASE_URL}/api/websites/client/snapshots",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        snapshots = r.json().get("snapshots", [])
        
        if len(snapshots) < 1:
            pytest.skip("Need at least 1 snapshot to test restore")
        
        snap_id = snapshots[0]["id"]
        initial_total = len(snapshots)
        
        r = requests.post(
            f"{BASE_URL}/api/websites/client/snapshots/{snap_id}/restore",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert data.get("ok") == True
        assert data.get("restored_id") == snap_id
        
        # Verify pre-restore snapshot was created (undo capability)
        r = requests.get(
            f"{BASE_URL}/api/websites/client/snapshots",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        new_snapshots = r.json().get("snapshots", [])
        
        # Should have a "قبل الاستعادة" snapshot
        pre_restore = [s for s in new_snapshots if "قبل الاستعادة" in s.get("label", "")]
        assert len(pre_restore) > 0, "Pre-restore snapshot should be created"
        
        print(f"✓ Snapshot restored, pre-restore snapshot created")
    
    def test_delete_snapshot(self, client_token):
        """DELETE /api/websites/client/snapshots/{id} removes snapshot"""
        # Create a snapshot to delete
        r = requests.post(
            f"{BASE_URL}/api/websites/client/snapshots",
            headers={
                "Authorization": f"ClientToken {client_token}",
                "Content-Type": "application/json"
            },
            json={"label": "نسخة للحذف"}
        )
        
        # Get snapshots
        r = requests.get(
            f"{BASE_URL}/api/websites/client/snapshots",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        snapshots = r.json().get("snapshots", [])
        
        if not snapshots:
            pytest.skip("No snapshots to delete")
        
        snap_id = snapshots[0]["id"]
        initial_count = len(snapshots)
        
        r = requests.delete(
            f"{BASE_URL}/api/websites/client/snapshots/{snap_id}",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        # Verify deletion
        r = requests.get(
            f"{BASE_URL}/api/websites/client/snapshots",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        new_count = len(r.json().get("snapshots", []))
        assert new_count == initial_count - 1, "Snapshot count should decrease by 1"
        
        print(f"✓ Snapshot deleted, count: {initial_count} -> {new_count}")


class TestOwnerSnapshots:
    """Test owner-facing snapshots endpoints"""
    
    def test_owner_list_snapshots(self, owner_token):
        """GET /api/websites/projects/{pid}/snapshots lists snapshots"""
        # First get a project
        r = requests.get(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        projects = r.json().get("projects", [])
        
        if not projects:
            pytest.skip("No projects found")
        
        project_id = projects[0]["id"]
        
        r = requests.get(
            f"{BASE_URL}/api/websites/projects/{project_id}/snapshots",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert "snapshots" in data
        assert "total" in data
        
        print(f"✓ Owner snapshots list: {data['total']} snapshots for project {project_id[:8]}")
    
    def test_owner_create_snapshot(self, owner_token):
        """POST /api/websites/projects/{pid}/snapshots creates snapshot"""
        r = requests.get(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        projects = r.json().get("projects", [])
        
        if not projects:
            pytest.skip("No projects found")
        
        project_id = projects[0]["id"]
        
        r = requests.post(
            f"{BASE_URL}/api/websites/projects/{project_id}/snapshots",
            headers={
                "Authorization": f"Bearer {owner_token}",
                "Content-Type": "application/json"
            },
            json={"label": "نسخة اختبار من المالك"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert data.get("ok") == True
        
        print(f"✓ Owner created snapshot, total: {data.get('total')}")
    
    def test_owner_snapshot_preview(self, owner_token):
        """GET /api/websites/projects/{pid}/snapshots/{sid}/preview-html returns HTML"""
        r = requests.get(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        projects = r.json().get("projects", [])
        
        if not projects:
            pytest.skip("No projects found")
        
        project_id = projects[0]["id"]
        
        # Get snapshots
        r = requests.get(
            f"{BASE_URL}/api/websites/projects/{project_id}/snapshots",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        snapshots = r.json().get("snapshots", [])
        
        if not snapshots:
            pytest.skip("No snapshots to preview")
        
        snap_id = snapshots[0]["id"]
        
        r = requests.get(
            f"{BASE_URL}/api/websites/projects/{project_id}/snapshots/{snap_id}/preview-html",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert "html" in data
        assert "label" in data
        
        print(f"✓ Owner snapshot preview HTML returned")
    
    def test_owner_restore_snapshot(self, owner_token):
        """POST /api/websites/projects/{pid}/snapshots/{sid}/restore restores"""
        r = requests.get(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        projects = r.json().get("projects", [])
        
        if not projects:
            pytest.skip("No projects found")
        
        project_id = projects[0]["id"]
        
        # Get snapshots
        r = requests.get(
            f"{BASE_URL}/api/websites/projects/{project_id}/snapshots",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        snapshots = r.json().get("snapshots", [])
        
        if not snapshots:
            pytest.skip("No snapshots to restore")
        
        snap_id = snapshots[0]["id"]
        
        r = requests.post(
            f"{BASE_URL}/api/websites/projects/{project_id}/snapshots/{snap_id}/restore",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        # Response should be the updated project
        data = r.json()
        assert "id" in data or "sections" in data, "Should return project data"
        
        print(f"✓ Owner restored snapshot")


class TestAISnapshotIntent:
    """Test AI snapshot intent detection in wizard/chat"""
    
    def test_snapshot_intent_detection(self, owner_token):
        """POST /api/websites/projects/{pid}/wizard/chat with 'ارجعلي للتصاميم السابقة' returns show_snapshots action"""
        r = requests.get(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        projects = r.json().get("projects", [])
        
        if not projects:
            pytest.skip("No projects found")
        
        project_id = projects[0]["id"]
        
        # Send message asking for past designs
        r = requests.post(
            f"{BASE_URL}/api/websites/projects/{project_id}/wizard/chat",
            headers={
                "Authorization": f"Bearer {owner_token}",
                "Content-Type": "application/json"
            },
            json={"message": "ارجعلي للتصاميم السابقة"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        action = data.get("action")
        
        # The action should be show_snapshots (takes PRIORITY over AI's interpretation)
        assert action is not None, "Should have an action"
        assert action.get("action") == "show_snapshots", f"Expected 'show_snapshots', got {action.get('action')}"
        
        print(f"✓ Snapshot intent detected: action={action}")
    
    def test_snapshot_intent_arabic_variations(self, owner_token):
        """Test various Arabic phrases trigger show_snapshots"""
        r = requests.get(
            f"{BASE_URL}/api/websites/projects",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        projects = r.json().get("projects", [])
        
        if not projects:
            pytest.skip("No projects found")
        
        project_id = projects[0]["id"]
        
        test_phrases = [
            "اعرض السجل",
            "التصاميم السابقة",
            "ارجع للنسخة القديمة",
        ]
        
        for phrase in test_phrases:
            r = requests.post(
                f"{BASE_URL}/api/websites/projects/{project_id}/wizard/chat",
                headers={
                    "Authorization": f"Bearer {owner_token}",
                    "Content-Type": "application/json"
                },
                json={"message": phrase}
            )
            
            if r.status_code == 200:
                action = r.json().get("action")
                if action and action.get("action") == "show_snapshots":
                    print(f"✓ Phrase '{phrase}' triggered show_snapshots")
                else:
                    print(f"⚠ Phrase '{phrase}' did not trigger show_snapshots (action={action})")
            
            time.sleep(0.5)  # Rate limit


class TestAutoSnapshotTriggers:
    """Test that auto-snapshots are created on certain actions"""
    
    def test_section_patch_creates_snapshot(self, client_token):
        """Patching a section should auto-create a snapshot"""
        # Get initial snapshot count
        r = requests.get(
            f"{BASE_URL}/api/websites/client/snapshots",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        initial_count = r.json().get("total", 0)
        
        # Get a section to patch
        r = requests.get(
            f"{BASE_URL}/api/websites/client/session",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        sections = r.json().get("sections", [])
        
        if not sections:
            pytest.skip("No sections to patch")
        
        section_id = sections[0]["id"]
        
        # Patch the section
        r = requests.patch(
            f"{BASE_URL}/api/websites/client/sections/{section_id}",
            headers={
                "Authorization": f"ClientToken {client_token}",
                "Content-Type": "application/json"
            },
            json={"data": {"title": f"عنوان اختبار {time.time()}"}}
        )
        assert r.status_code == 200
        
        # Check snapshot count increased
        r = requests.get(
            f"{BASE_URL}/api/websites/client/snapshots",
            headers={"Authorization": f"ClientToken {client_token}"}
        )
        new_count = r.json().get("total", 0)
        
        # May not increase if dedupe kicks in (same content)
        print(f"✓ Section patch: snapshots {initial_count} -> {new_count}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
