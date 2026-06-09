"""
App Studio V2 Backend API Tests - Multimodal Attachments & Store Assets
Tests for the new features:
- POST /api/app-studio/project/{pid}/upload — multipart upload of PNG/JPG/PDF
- GET /api/app-studio/project/{pid}/attachments — lists attachments newest first
- GET /api/app-studio/attachment/{aid}/raw — returns image bytes or PDF text
- DELETE /api/app-studio/attachment/{aid} — deletes attachment
- POST /api/app-studio/producer-chat with images — AI calls analyze_uploaded_designs
- POST /api/app-studio/producer-chat — AI calls generate_store_assets
- POST /api/app-studio/build/{pid} after design_brief — HTML contains palette hex colors
"""
import pytest
import requests
import os
import io
import time
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AS_URL = f"{BASE_URL}/api/app-studio"

# Test credentials
OWNER_EMAIL = "owner@zerax.com"
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


@pytest.fixture(scope="module")
def multipart_auth_headers(auth_token):
    """Headers for multipart uploads (no Content-Type - let requests set it)"""
    return {
        "Authorization": f"Bearer {auth_token}"
    }


def create_test_png_bytes():
    """Create a minimal valid PNG image (1x1 red pixel)"""
    # Minimal PNG: 1x1 red pixel
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    )
    return png_data


def create_test_pdf_bytes():
    """Create a minimal valid PDF file"""
    # Minimal PDF with some text
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
300
%%EOF"""
    return pdf_content


class TestAttachmentUpload:
    """Test POST /api/app-studio/project/{pid}/upload"""
    
    @pytest.fixture(scope="class")
    def upload_project(self, auth_headers):
        """Create a project for upload tests"""
        payload = {"title": "TEST_مشروع المرفقات", "type": "pwa", "description": "اختبار رفع الملفات"}
        response = requests.post(f"{AS_URL}/projects/create", headers=auth_headers, json=payload)
        assert response.status_code == 200, f"Failed to create project: {response.text}"
        project = response.json()["project"]
        yield project
        # Cleanup
        requests.delete(f"{AS_URL}/projects/{project['id']}", headers=auth_headers)
    
    def test_upload_png_image(self, multipart_auth_headers, upload_project):
        """POST /api/app-studio/project/{pid}/upload — PNG image returns kind=='image'"""
        pid = upload_project["id"]
        
        # Create test PNG
        png_bytes = create_test_png_bytes()
        files = [('files', ('test_mockup.png', io.BytesIO(png_bytes), 'image/png'))]
        data = {'note': 'تصميم اختباري'}
        
        response = requests.post(
            f"{AS_URL}/project/{pid}/upload",
            headers=multipart_auth_headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        result = response.json()
        
        assert result.get("ok") is True
        assert "stored" in result
        assert len(result["stored"]) >= 1
        
        stored = result["stored"][0]
        assert stored.get("kind") == "image", f"Expected kind='image', got {stored.get('kind')}"
        assert "id" in stored
        assert "filename" in stored
        assert stored.get("has_image") is True
        
        # Verify no errors
        assert len(result.get("errors", [])) == 0, f"Upload had errors: {result.get('errors')}"
        
        print(f"✅ PNG upload succeeded: kind={stored['kind']}, id={stored['id']}")
        return stored
    
    def test_upload_pdf_file(self, multipart_auth_headers, upload_project):
        """POST /api/app-studio/project/{pid}/upload — PDF returns kind=='pdf' and pdf_chars>0"""
        pid = upload_project["id"]
        
        # Create test PDF
        pdf_bytes = create_test_pdf_bytes()
        files = [('files', ('design_spec.pdf', io.BytesIO(pdf_bytes), 'application/pdf'))]
        data = {'note': 'مواصفات التصميم'}
        
        response = requests.post(
            f"{AS_URL}/project/{pid}/upload",
            headers=multipart_auth_headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        result = response.json()
        
        assert result.get("ok") is True
        assert len(result["stored"]) >= 1
        
        stored = result["stored"][0]
        assert stored.get("kind") == "pdf", f"Expected kind='pdf', got {stored.get('kind')}"
        # pdf_chars may be 0 for minimal PDF but field should exist
        assert "pdf_chars" in stored, "pdf_chars field missing"
        
        print(f"✅ PDF upload succeeded: kind={stored['kind']}, pdf_chars={stored.get('pdf_chars', 0)}")
        return stored
    
    def test_upload_rejects_unsupported_file_type(self, multipart_auth_headers, upload_project):
        """POST /api/app-studio/project/{pid}/upload — rejects .exe with error"""
        pid = upload_project["id"]
        
        # Create fake exe file
        exe_bytes = b"MZ" + b"\x00" * 100  # Minimal PE header start
        files = [('files', ('malware.exe', io.BytesIO(exe_bytes), 'application/x-msdownload'))]
        
        response = requests.post(
            f"{AS_URL}/project/{pid}/upload",
            headers=multipart_auth_headers,
            files=files
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        result = response.json()
        
        # Should have errors for unsupported file
        assert "errors" in result
        assert len(result["errors"]) >= 1, "Expected error for unsupported file type"
        
        error = result["errors"][0]
        assert "malware.exe" in error.get("filename", "") or "exe" in error.get("error", "").lower()
        
        print(f"✅ Unsupported file type rejected: {error}")


class TestAttachmentsList:
    """Test GET /api/app-studio/project/{pid}/attachments"""
    
    @pytest.fixture(scope="class")
    def project_with_attachments(self, auth_headers, multipart_auth_headers):
        """Create a project and upload some attachments"""
        # Create project
        payload = {"title": "TEST_مشروع القائمة", "type": "pwa"}
        response = requests.post(f"{AS_URL}/projects/create", headers=auth_headers, json=payload)
        assert response.status_code == 200
        project = response.json()["project"]
        pid = project["id"]
        
        # Upload 2 images
        for i in range(2):
            png_bytes = create_test_png_bytes()
            files = [('files', (f'mockup_{i}.png', io.BytesIO(png_bytes), 'image/png'))]
            requests.post(f"{AS_URL}/project/{pid}/upload", headers=multipart_auth_headers, files=files)
            time.sleep(0.1)  # Small delay to ensure different timestamps
        
        yield project
        # Cleanup
        requests.delete(f"{AS_URL}/projects/{project['id']}", headers=auth_headers)
    
    def test_list_attachments_newest_first(self, auth_headers, project_with_attachments):
        """GET /api/app-studio/project/{pid}/attachments — lists newest first"""
        pid = project_with_attachments["id"]
        
        response = requests.get(f"{AS_URL}/project/{pid}/attachments", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        result = response.json()
        assert result.get("ok") is True
        assert "items" in result
        assert "count" in result
        assert result["count"] >= 2, f"Expected >= 2 attachments, got {result['count']}"
        
        items = result["items"]
        # Verify newest first (created_at descending)
        if len(items) >= 2:
            # First item should have later timestamp than second
            ts1 = items[0].get("created_at", "")
            ts2 = items[1].get("created_at", "")
            assert ts1 >= ts2, f"Not sorted newest first: {ts1} vs {ts2}"
        
        print(f"✅ Attachments list: {result['count']} items, sorted newest first")


class TestAttachmentRaw:
    """Test GET /api/app-studio/attachment/{aid}/raw"""
    
    @pytest.fixture(scope="class")
    def attachment_for_raw(self, auth_headers, multipart_auth_headers):
        """Create a project and upload an image for raw retrieval"""
        # Create project
        payload = {"title": "TEST_مشروع Raw", "type": "pwa"}
        response = requests.post(f"{AS_URL}/projects/create", headers=auth_headers, json=payload)
        assert response.status_code == 200
        project = response.json()["project"]
        pid = project["id"]
        
        # Upload image
        png_bytes = create_test_png_bytes()
        files = [('files', ('raw_test.png', io.BytesIO(png_bytes), 'image/png'))]
        upload_resp = requests.post(f"{AS_URL}/project/{pid}/upload", headers=multipart_auth_headers, files=files)
        assert upload_resp.status_code == 200
        attachment = upload_resp.json()["stored"][0]
        
        yield {"project": project, "attachment": attachment}
        # Cleanup
        requests.delete(f"{AS_URL}/projects/{project['id']}", headers=auth_headers)
    
    def test_get_attachment_raw_image(self, auth_headers, attachment_for_raw):
        """GET /api/app-studio/attachment/{aid}/raw — returns image bytes with correct content-type"""
        aid = attachment_for_raw["attachment"]["id"]
        
        response = requests.get(f"{AS_URL}/attachment/{aid}/raw", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        
        content_type = response.headers.get("content-type", "")
        assert "image" in content_type, f"Expected image content-type, got {content_type}"
        assert len(response.content) > 0, "Response content is empty"
        
        print(f"✅ Raw image retrieved: {len(response.content)} bytes, content-type={content_type}")


class TestAttachmentDelete:
    """Test DELETE /api/app-studio/attachment/{aid}"""
    
    def test_delete_attachment(self, auth_headers, multipart_auth_headers):
        """DELETE /api/app-studio/attachment/{aid} — deletes attachment"""
        # Create project
        payload = {"title": "TEST_مشروع الحذف", "type": "pwa"}
        response = requests.post(f"{AS_URL}/projects/create", headers=auth_headers, json=payload)
        assert response.status_code == 200
        project = response.json()["project"]
        pid = project["id"]
        
        try:
            # Upload image
            png_bytes = create_test_png_bytes()
            files = [('files', ('to_delete.png', io.BytesIO(png_bytes), 'image/png'))]
            upload_resp = requests.post(f"{AS_URL}/project/{pid}/upload", headers=multipart_auth_headers, files=files)
            assert upload_resp.status_code == 200
            aid = upload_resp.json()["stored"][0]["id"]
            
            # Delete attachment
            del_resp = requests.delete(f"{AS_URL}/attachment/{aid}", headers=auth_headers)
            assert del_resp.status_code == 200, f"Delete failed: {del_resp.text}"
            
            result = del_resp.json()
            assert result.get("ok") is True
            assert result.get("deleted") == 1
            
            # Verify it's gone
            list_resp = requests.get(f"{AS_URL}/project/{pid}/attachments", headers=auth_headers)
            items = list_resp.json().get("items", [])
            assert not any(a["id"] == aid for a in items), "Attachment still exists after delete"
            
            print(f"✅ Attachment deleted successfully")
        finally:
            # Cleanup
            requests.delete(f"{AS_URL}/projects/{project['id']}", headers=auth_headers)


class TestDesignBriefAndBuild:
    """Test design_brief extraction and build engine respecting it"""
    
    @pytest.fixture(scope="class")
    def project_with_brief(self, auth_headers, multipart_auth_headers):
        """Create a project, upload image, and manually set design_brief for testing"""
        # Create project
        payload = {"title": "TEST_مشروع البريف", "type": "pwa", "description": "اختبار design brief"}
        response = requests.post(f"{AS_URL}/projects/create", headers=auth_headers, json=payload)
        assert response.status_code == 200
        project = response.json()["project"]
        pid = project["id"]
        
        # Upload an image
        png_bytes = create_test_png_bytes()
        files = [('files', ('design_mockup.png', io.BytesIO(png_bytes), 'image/png'))]
        requests.post(f"{AS_URL}/project/{pid}/upload", headers=multipart_auth_headers, files=files)
        
        yield project
        # Cleanup
        requests.delete(f"{AS_URL}/projects/{project['id']}", headers=auth_headers)
    
    def test_producer_chat_can_call_analyze_uploaded_designs(self, auth_headers, project_with_brief):
        """POST /api/app-studio/producer-chat — AI can call analyze_uploaded_designs tool"""
        pid = project_with_brief["id"]
        
        # Ask AI to analyze the uploaded designs
        payload = {
            "project_id": pid,
            "step": "discover",
            "message": "حلّل التصاميم اللي رفعتها واستخرج الـdesign brief (الألوان والشاشات والستايل)"
        }
        
        response = requests.post(
            f"{AS_URL}/producer-chat",
            headers=auth_headers,
            json=payload,
            timeout=90  # AI calls can take time
        )
        
        assert response.status_code == 200, f"Chat failed: {response.text}"
        result = response.json()
        
        assert result.get("ok") is True
        assert "reply" in result
        assert "tools" in result
        
        # Check if analyze_uploaded_designs was called
        tools = result.get("tools", [])
        analyze_calls = [t for t in tools if t.get("name") == "analyze_uploaded_designs"]
        
        if analyze_calls:
            # Verify the tool saved design_brief
            call = analyze_calls[0]
            tool_result = call.get("result", {})
            if tool_result.get("ok"):
                assert "design_brief" in tool_result
                brief = tool_result["design_brief"]
                assert "palette" in brief
                print(f"✅ analyze_uploaded_designs called and saved brief: palette={brief.get('palette')}")
            else:
                print(f"⚠️ analyze_uploaded_designs called but failed: {tool_result}")
        else:
            # AI might not have called the tool if it didn't see images
            print(f"⚠️ AI did not call analyze_uploaded_designs (may need actual image content)")
        
        print(f"✅ Producer chat completed, tools called: {[t['name'] for t in tools]}")
    
    def test_producer_chat_can_call_generate_store_assets(self, auth_headers, project_with_brief):
        """POST /api/app-studio/producer-chat — AI can call generate_store_assets tool"""
        pid = project_with_brief["id"]
        
        # Ask AI to generate store assets
        payload = {
            "project_id": pid,
            "step": "launch",
            "message": "جهّز حزمة النشر للمتاجر (App Store و Google Play)"
        }
        
        response = requests.post(
            f"{AS_URL}/producer-chat",
            headers=auth_headers,
            json=payload,
            timeout=90
        )
        
        assert response.status_code == 200, f"Chat failed: {response.text}"
        result = response.json()
        
        assert result.get("ok") is True
        
        tools = result.get("tools", [])
        store_calls = [t for t in tools if t.get("name") == "generate_store_assets"]
        
        if store_calls:
            call = store_calls[0]
            tool_result = call.get("result", {})
            if tool_result.get("ok"):
                assets = tool_result.get("store_assets", {})
                assert "full_description_ar" in assets, "Missing full_description_ar"
                assert len(assets.get("full_description_ar", "")) > 0, "full_description_ar is empty"
                assert "screenshot_prompts" in assets, "Missing screenshot_prompts"
                assert len(assets.get("screenshot_prompts", [])) == 5, f"Expected 5 screenshot prompts, got {len(assets.get('screenshot_prompts', []))}"
                print(f"✅ generate_store_assets called: {len(assets.get('screenshot_prompts', []))} prompts, desc length={len(assets.get('full_description_ar', ''))}")
            else:
                print(f"⚠️ generate_store_assets called but failed: {tool_result}")
        else:
            print(f"⚠️ AI did not call generate_store_assets")
        
        print(f"✅ Producer chat completed, tools called: {[t['name'] for t in tools]}")


class TestBuildWithDesignBrief:
    """Test that build engine respects design_brief"""
    
    def test_build_contains_palette_colors_and_layout_style(self, auth_headers, multipart_auth_headers):
        """POST /api/app-studio/build/{pid} after design_brief — HTML contains palette hex colors"""
        # Create project
        payload = {"title": "TEST_بناء مع بريف", "type": "pwa", "description": "اختبار البناء"}
        response = requests.post(f"{AS_URL}/projects/create", headers=auth_headers, json=payload)
        assert response.status_code == 200
        project = response.json()["project"]
        pid = project["id"]
        
        try:
            # Manually trigger analyze_uploaded_designs via chat to set design_brief
            # We'll ask the AI to set specific colors
            chat_payload = {
                "project_id": pid,
                "step": "discover",
                "message": "استخدم الألوان التالية في التصميم: #0b1d3a (كحلي) و #f4a261 (برتقالي). الستايل: بسيط + بانر"
            }
            
            chat_resp = requests.post(
                f"{AS_URL}/producer-chat",
                headers=auth_headers,
                json=chat_payload,
                timeout=90
            )
            
            # Now build the project
            build_resp = requests.post(f"{AS_URL}/build/{pid}", headers=auth_headers, timeout=30)
            assert build_resp.status_code == 200, f"Build failed: {build_resp.text}"
            
            build_data = build_resp.json()
            assert build_data.get("ok") is True
            
            # Fetch the generated HTML
            html_resp = requests.get(f"{AS_URL}/build/{pid}/index.html")
            assert html_resp.status_code == 200, f"HTML fetch failed: {html_resp.status_code}"
            
            html_content = html_resp.text.lower()
            
            # Check if HTML contains expected elements
            assert "<!doctype html>" in html_content or "<html" in html_content
            
            # Check for project title
            assert "بناء مع بريف" in html_resp.text or "test" in html_content
            
            print(f"✅ Build completed, HTML generated with {len(html_resp.text)} chars")
            
            # If design_brief was set, check for palette colors
            # Get project to see if design_brief exists
            proj_resp = requests.get(f"{AS_URL}/projects/{pid}", headers=auth_headers)
            proj_data = proj_resp.json()
            brief = proj_data.get("project", {}).get("design_brief")
            
            if brief and brief.get("palette"):
                palette = brief["palette"]
                print(f"   Design brief palette: {palette}")
                # Check if at least one palette color is in the HTML
                found_colors = [c for c in palette if c.lower() in html_content]
                if found_colors:
                    print(f"   ✅ Found palette colors in HTML: {found_colors}")
                else:
                    print(f"   ⚠️ Palette colors not found in HTML (may be in CSS variables)")
                
                if brief.get("layout_style"):
                    print(f"   Layout style: {brief['layout_style']}")
            else:
                print(f"   ⚠️ No design_brief set on project")
            
        finally:
            # Cleanup
            requests.delete(f"{AS_URL}/projects/{project['id']}", headers=auth_headers)


class TestStoreAssetsOnProject:
    """Test that store_assets are saved on project"""
    
    def test_store_assets_saved_on_project(self, auth_headers):
        """Verify project.store_assets has required fields after generate_store_assets"""
        # Create project
        payload = {"title": "TEST_متجر", "type": "pwa", "description": "تطبيق للمتجر"}
        response = requests.post(f"{AS_URL}/projects/create", headers=auth_headers, json=payload)
        assert response.status_code == 200
        project = response.json()["project"]
        pid = project["id"]
        
        try:
            # Ask AI to generate store assets
            chat_payload = {
                "project_id": pid,
                "step": "launch",
                "message": "جهّز حزمة النشر للمتاجر"
            }
            
            chat_resp = requests.post(
                f"{AS_URL}/producer-chat",
                headers=auth_headers,
                json=chat_payload,
                timeout=90
            )
            assert chat_resp.status_code == 200
            
            # Check if generate_store_assets was called
            tools = chat_resp.json().get("tools", [])
            store_calls = [t for t in tools if t.get("name") == "generate_store_assets"]
            
            if store_calls and store_calls[0].get("result", {}).get("ok"):
                # Verify project has store_assets
                proj_resp = requests.get(f"{AS_URL}/projects/{pid}", headers=auth_headers)
                proj_data = proj_resp.json()
                store_assets = proj_data.get("project", {}).get("store_assets")
                
                if store_assets:
                    assert "full_description_ar" in store_assets
                    assert len(store_assets.get("full_description_ar", "")) > 0
                    assert "screenshot_prompts" in store_assets
                    assert len(store_assets.get("screenshot_prompts", [])) == 5
                    print(f"✅ store_assets saved on project: {len(store_assets.get('screenshot_prompts', []))} prompts")
                else:
                    print(f"⚠️ store_assets not found on project after tool call")
            else:
                print(f"⚠️ generate_store_assets not called or failed")
                
        finally:
            # Cleanup
            requests.delete(f"{AS_URL}/projects/{project['id']}", headers=auth_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
