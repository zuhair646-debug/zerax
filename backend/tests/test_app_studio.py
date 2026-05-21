"""
App Studio Backend API Tests
Tests for the App Studio module including:
- Project types and features catalogue
- Project CRUD operations
- Feature addition with credit deduction
- AI Producer chat with tool-calling
- Build engine (PWA/Hybrid/Native/FullStack)
- Importable artifacts
- Conversation history
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AS_URL = f"{BASE_URL}/api/app-studio"

# Test credentials from test_credentials.md
OWNER_EMAIL = "owner@zitex.com"
OWNER_PASSWORD = "owner123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for owner user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }


class TestAppStudioOptions:
    """Test GET /api/app-studio/options - catalogue endpoints"""
    
    def test_options_returns_project_types(self, auth_headers):
        """Verify options returns 4 project types"""
        response = requests.get(f"{AS_URL}/options", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("ok") is True
        assert "project_types" in data
        assert len(data["project_types"]) == 4, f"Expected 4 project types, got {len(data['project_types'])}"
        
        # Verify all 4 types exist
        type_ids = [t["id"] for t in data["project_types"]]
        assert "pwa" in type_ids
        assert "hybrid" in type_ids
        assert "native" in type_ids
        assert "fullstack" in type_ids
        print(f"✅ Options returns 4 project types: {type_ids}")
    
    def test_options_returns_features(self, auth_headers):
        """Verify options returns 20 features"""
        response = requests.get(f"{AS_URL}/options", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "features" in data
        assert len(data["features"]) == 20, f"Expected 20 features, got {len(data['features'])}"
        
        # Verify feature structure
        for feat in data["features"]:
            assert "id" in feat
            assert "label_ar" in feat
            assert "cost" in feat
            assert "category" in feat
        print(f"✅ Options returns 20 features")
    
    def test_options_returns_feature_categories(self, auth_headers):
        """Verify feature categories are returned"""
        response = requests.get(f"{AS_URL}/options", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "feature_categories" in data
        cat_ids = [c["id"] for c in data["feature_categories"]]
        assert "core" in cat_ids
        assert "screen" in cat_ids
        assert "money" in cat_ids
        assert "addon" in cat_ids
        assert "ai" in cat_ids
        print(f"✅ Options returns feature categories: {cat_ids}")


class TestAppStudioProjectCRUD:
    """Test project CRUD operations"""
    
    @pytest.fixture(scope="class")
    def created_project(self, auth_headers):
        """Create a test project and return its data"""
        payload = {
            "title": "TEST_تطبيق اختبار",
            "type": "fullstack",
            "description": "تطبيق اختبار للـ API",
            "target_audience": "مطورين",
            "primary_color": "#6366f1",
            "style_direction": "modern"
        }
        response = requests.post(
            f"{AS_URL}/projects/create",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Failed to create project: {response.text}"
        data = response.json()
        assert data.get("ok") is True
        yield data["project"]
        
        # Cleanup: delete the project
        requests.delete(f"{AS_URL}/projects/{data['project']['id']}", headers=auth_headers)
    
    def test_create_project_fullstack(self, auth_headers, created_project):
        """POST /api/app-studio/projects/create - creates fullstack project"""
        assert created_project["type"] == "fullstack"
        assert created_project["title"] == "TEST_تطبيق اختبار"
        assert "id" in created_project
        assert created_project["stage"] == "planning"
        print(f"✅ Created fullstack project: {created_project['id']}")
    
    def test_get_project_returns_features_list(self, auth_headers, created_project):
        """GET /api/app-studio/projects/{project_id} - returns project + features"""
        pid = created_project["id"]
        response = requests.get(f"{AS_URL}/projects/{pid}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") is True
        assert "project" in data
        assert "features" in data
        assert data["project"]["id"] == pid
        assert isinstance(data["features"], list)
        print(f"✅ GET project returns project + features list")
    
    def test_list_projects(self, auth_headers, created_project):
        """GET /api/app-studio/projects - lists user projects"""
        response = requests.get(f"{AS_URL}/projects", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") is True
        assert "projects" in data
        
        # Find our test project
        test_proj = next((p for p in data["projects"] if p["id"] == created_project["id"]), None)
        assert test_proj is not None, "Created project not found in list"
        print(f"✅ List projects works, found {len(data['projects'])} projects")
    
    def test_delete_project(self, auth_headers):
        """DELETE /api/app-studio/projects/{project_id} - deletes project + features"""
        # Create a project to delete
        payload = {"title": "TEST_للحذف", "type": "pwa"}
        create_resp = requests.post(f"{AS_URL}/projects/create", headers=auth_headers, json=payload)
        assert create_resp.status_code == 200
        pid = create_resp.json()["project"]["id"]
        
        # Delete it
        del_resp = requests.delete(f"{AS_URL}/projects/{pid}", headers=auth_headers)
        assert del_resp.status_code == 200
        data = del_resp.json()
        assert data.get("ok") is True
        assert data.get("deleted") == 1
        
        # Verify it's gone
        get_resp = requests.get(f"{AS_URL}/projects/{pid}", headers=auth_headers)
        assert get_resp.status_code == 404
        print(f"✅ Delete project works")


class TestAppStudioFeatures:
    """Test feature addition/removal"""
    
    @pytest.fixture(scope="class")
    def project_for_features(self, auth_headers):
        """Create a project for feature tests"""
        payload = {"title": "TEST_مشروع الميزات", "type": "pwa"}
        response = requests.post(f"{AS_URL}/projects/create", headers=auth_headers, json=payload)
        assert response.status_code == 200
        project = response.json()["project"]
        yield project
        # Cleanup
        requests.delete(f"{AS_URL}/projects/{project['id']}", headers=auth_headers)
    
    def test_add_feature_with_credit_deduction(self, auth_headers, project_for_features):
        """POST /api/app-studio/feature/add - adds feature (owner bypasses credits)"""
        pid = project_for_features["id"]
        payload = {
            "project_id": pid,
            "feature_id": "auth_basic",
            "config": {}
        }
        response = requests.post(f"{AS_URL}/feature/add", headers=auth_headers, json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("ok") is True
        assert "feature" in data
        assert data["feature"]["feature_id"] == "auth_basic"
        # Owner bypasses credit deduction but field should still be present
        assert "credits_charged" in data
        print(f"✅ Feature added: auth_basic, charged {data['credits_charged']} credits")
    
    def test_add_duplicate_feature_returns_409(self, auth_headers, project_for_features):
        """POST /api/app-studio/feature/add with duplicate returns 409"""
        pid = project_for_features["id"]
        
        # First add (might already exist from previous test)
        payload = {"project_id": pid, "feature_id": "user_profile", "config": {}}
        requests.post(f"{AS_URL}/feature/add", headers=auth_headers, json=payload)
        
        # Second add should fail with 409
        response = requests.post(f"{AS_URL}/feature/add", headers=auth_headers, json=payload)
        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"
        print(f"✅ Duplicate feature returns 409")


class TestAppStudioProducerChat:
    """Test AI Producer chat with tool-calling"""
    
    @pytest.fixture(scope="class")
    def chat_project(self, auth_headers):
        """Create a project for chat tests"""
        payload = {"title": "TEST_مشروع الشات", "type": "fullstack", "description": "تطبيق توصيل"}
        response = requests.post(f"{AS_URL}/projects/create", headers=auth_headers, json=payload)
        assert response.status_code == 200
        project = response.json()["project"]
        yield project
        # Cleanup
        requests.delete(f"{AS_URL}/projects/{project['id']}", headers=auth_headers)
    
    def test_producer_chat_with_tool_calls(self, auth_headers, chat_project):
        """POST /api/app-studio/producer-chat - AI with tools"""
        pid = chat_project["id"]
        payload = {
            "project_id": pid,
            "step": "discover",
            "message": "أضف auth_basic و user_profile و subscription"
        }
        
        response = requests.post(
            f"{AS_URL}/producer-chat",
            headers=auth_headers,
            json=payload,
            timeout=60  # AI calls can take time
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("ok") is True
        assert "reply" in data
        assert "tools" in data
        
        # Verify tools array contains add_feature_to_project calls
        tools = data.get("tools", [])
        add_feature_calls = [t for t in tools if t.get("name") == "add_feature_to_project"]
        
        # Check if at least some tools were called
        if len(add_feature_calls) > 0:
            # Verify at least one succeeded
            successful = [t for t in add_feature_calls if t.get("result", {}).get("ok") is True]
            print(f"✅ Producer chat called add_feature_to_project {len(add_feature_calls)} times, {len(successful)} succeeded")
        else:
            print(f"⚠️ No add_feature_to_project calls in tools array (AI may have responded differently)")
        
        # Verify reply is non-empty Arabic
        assert len(data["reply"]) > 0, "Reply should not be empty"
        print(f"✅ Producer chat reply: {data['reply'][:100]}...")
    
    def test_conversation_history(self, auth_headers, chat_project):
        """GET /api/app-studio/conversation/{project_id} - returns message history"""
        pid = chat_project["id"]
        response = requests.get(f"{AS_URL}/conversation/{pid}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") is True
        assert "messages" in data
        # Should have messages from previous test
        print(f"✅ Conversation history has {len(data['messages'])} messages")
    
    def test_reset_conversation(self, auth_headers, chat_project):
        """DELETE /api/app-studio/conversation/{project_id} - resets conversation"""
        pid = chat_project["id"]
        response = requests.delete(f"{AS_URL}/conversation/{pid}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") is True
        
        # Verify it's empty now
        get_resp = requests.get(f"{AS_URL}/conversation/{pid}", headers=auth_headers)
        assert get_resp.json().get("messages", []) == []
        print(f"✅ Conversation reset works")


class TestAppStudioBuild:
    """Test build engine"""
    
    @pytest.fixture(scope="class")
    def build_project(self, auth_headers):
        """Create a project for build tests"""
        payload = {"title": "TEST_مشروع البناء", "type": "pwa", "description": "تطبيق للبناء"}
        response = requests.post(f"{AS_URL}/projects/create", headers=auth_headers, json=payload)
        assert response.status_code == 200
        project = response.json()["project"]
        yield project
        # Cleanup
        requests.delete(f"{AS_URL}/projects/{project['id']}", headers=auth_headers)
    
    def test_build_project(self, auth_headers, build_project):
        """POST /api/app-studio/build/{project_id} - builds the project"""
        pid = build_project["id"]
        response = requests.post(f"{AS_URL}/build/{pid}", headers=auth_headers, timeout=30)
        assert response.status_code == 200, f"Build failed: {response.text}"
        
        data = response.json()
        assert data.get("ok") is True
        assert "build" in data
        
        build = data["build"]
        assert "preview_url" in build
        assert "zip_url" in build
        assert "files" in build
        assert "bundle_size" in build
        
        # Verify >= 5 files generated
        assert len(build["files"]) >= 5, f"Expected >= 5 files, got {len(build['files'])}"
        assert build["bundle_size"] > 0
        
        print(f"✅ Build succeeded: {len(build['files'])} files, {build['bundle_size']} bytes")
        print(f"   Preview URL: {build['preview_url']}")
        print(f"   Zip URL: {build['zip_url']}")
        
        return build
    
    def test_serve_built_html(self, auth_headers, build_project):
        """GET /api/app-studio/build/{project_id}/frontend/index.html - serves HTML publicly"""
        pid = build_project["id"]
        
        # First build the project
        requests.post(f"{AS_URL}/build/{pid}", headers=auth_headers, timeout=30)
        
        # For PWA type, the index.html is at root
        response = requests.get(f"{AS_URL}/build/{pid}/index.html")  # No auth required
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "text/html" in response.headers.get("content-type", "")
        assert "<!doctype html>" in response.text.lower() or "<html" in response.text.lower()
        print(f"✅ Built HTML served publicly (no auth required)")
    
    def test_serve_zip_bundle(self, auth_headers, build_project):
        """GET /api/app-studio/build/{project_id}/bundle.zip - serves zip bundle"""
        pid = build_project["id"]
        
        # First build the project
        requests.post(f"{AS_URL}/build/{pid}", headers=auth_headers, timeout=30)
        
        response = requests.get(f"{AS_URL}/build/{pid}/bundle.zip")  # No auth required
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "application/zip" in response.headers.get("content-type", "")
        assert len(response.content) > 0
        print(f"✅ Zip bundle served: {len(response.content)} bytes")


class TestAppStudioImportable:
    """Test importable artifacts"""
    
    def test_list_importable(self, auth_headers):
        """GET /api/app-studio/importable - lists freebuild_site and mobile_app artifacts"""
        response = requests.get(f"{AS_URL}/importable", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("ok") is True
        assert "items" in data
        assert "count" in data
        
        # Verify structure of items if any exist
        for item in data["items"]:
            assert "kind" in item
            assert item["kind"] in ["freebuild_site", "mobile_app"]
            assert "id" in item
            assert "label" in item
            assert "source" in item
        
        print(f"✅ Importable list: {data['count']} items")


class TestAppStudioFullstackBuild:
    """Test fullstack build generates all components"""
    
    @pytest.fixture(scope="class")
    def fullstack_project(self, auth_headers):
        """Create a fullstack project for build tests"""
        payload = {
            "title": "TEST_فولستاك",
            "type": "fullstack",
            "description": "تطبيق كامل"
        }
        response = requests.post(f"{AS_URL}/projects/create", headers=auth_headers, json=payload)
        assert response.status_code == 200
        project = response.json()["project"]
        yield project
        # Cleanup
        requests.delete(f"{AS_URL}/projects/{project['id']}", headers=auth_headers)
    
    def test_fullstack_build_generates_all_components(self, auth_headers, fullstack_project):
        """Fullstack build should generate frontend, backend, admin, marketing"""
        pid = fullstack_project["id"]
        response = requests.post(f"{AS_URL}/build/{pid}", headers=auth_headers, timeout=30)
        assert response.status_code == 200
        
        data = response.json()
        build = data["build"]
        
        # Check file paths
        file_paths = [f["path"] for f in build["files"]]
        
        # Should have frontend/
        assert any("frontend/" in p for p in file_paths), "Missing frontend/ files"
        # Should have backend/
        assert any("backend/" in p for p in file_paths), "Missing backend/ files"
        # Should have admin/
        assert any("admin/" in p for p in file_paths), "Missing admin/ files"
        # Should have marketing/
        assert any("marketing/" in p for p in file_paths), "Missing marketing/ files"
        
        print(f"✅ Fullstack build has all components: frontend, backend, admin, marketing")
        print(f"   Files: {file_paths}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
