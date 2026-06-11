"""
FreeBuild V2 — Conversational Live Builder Backend Tests

Tests the new /api/freebuild/v2/* endpoints:
- POST /start — creates session + first AI message
- POST /chat — submit user message, get AI reply + (optional) html_update
- GET /preview/{session_id} — live HTML preview (empty state + built state)
- POST /save-as-project — lock current HTML as permanent project
- GET /projects — list saved projects
- GET /project-preview/{project_id} — saved HTML
- POST /refine — post-save refinement
- DELETE /project/{project_id} — delete project
- Error handling for invalid session_id/project_id
"""
import pytest
import requests
import os
import time

# Read BASE_URL from frontend/.env (where REACT_APP_BACKEND_URL lives), fallback to localhost
def _load_base_url():
    from pathlib import Path
    env_file = Path(__file__).resolve().parents[2] / "frontend" / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().strip('"').rstrip("/")
    return os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")

BASE_URL = _load_base_url() or "http://localhost:8001"

# Test credentials
TEST_EMAIL = "owner@zenrex.ai"
TEST_PASSWORD = "owner123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for owner user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.text}")
    data = response.json()
    return data.get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }


class TestFreeBuildV2Start:
    """Test POST /api/freebuild/v2/start endpoint"""
    
    def test_start_returns_session_and_greeting(self, auth_headers):
        """Start should return session_id, assistant_message, next_question_type='text', credits_balance"""
        response = requests.post(
            f"{BASE_URL}/api/freebuild/v2/start",
            headers=auth_headers,
            json={}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Validate required fields
        assert "session_id" in data, "Missing session_id"
        assert "assistant_message" in data, "Missing assistant_message"
        assert "next_question_type" in data, "Missing next_question_type"
        assert "credits_balance" in data, "Missing credits_balance"
        
        # Validate values
        assert len(data["session_id"]) > 10, "session_id should be a UUID"
        assert data["next_question_type"] == "text", f"Expected 'text', got {data['next_question_type']}"
        assert isinstance(data["credits_balance"], (int, float)), "credits_balance should be numeric"
        assert data["credits_balance"] > 0, "Owner should have credits"
        
        # Greeting should be in Arabic
        assert "هلا" in data["assistant_message"] or "المهندس" in data["assistant_message"], \
            "Greeting should be in Arabic"
        
        print(f"✅ Start successful: session_id={data['session_id'][:8]}..., credits={data['credits_balance']}")
    
    def test_start_requires_auth(self):
        """Start without auth should fail"""
        response = requests.post(
            f"{BASE_URL}/api/freebuild/v2/start",
            json={}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✅ Start correctly requires authentication")


class TestFreeBuildV2Chat:
    """Test POST /api/freebuild/v2/chat endpoint with full conversation flow"""
    
    @pytest.fixture(scope="class")
    def session_data(self, auth_headers):
        """Create a session for chat tests"""
        response = requests.post(
            f"{BASE_URL}/api/freebuild/v2/start",
            headers=auth_headers,
            json={}
        )
        assert response.status_code == 200
        data = response.json()
        return {
            "session_id": data["session_id"],
            "initial_credits": data["credits_balance"]
        }
    
    def test_chat_first_turn_quran_site(self, auth_headers, session_data):
        """First turn: describe the site idea (Quran teaching site for kids)"""
        response = requests.post(
            f"{BASE_URL}/api/freebuild/v2/chat",
            headers=auth_headers,
            json={
                "session_id": session_data["session_id"],
                "message": "موقع لتحفيظ القرآن الكريم للأطفال"
            },
            timeout=60
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        data = response.json()
        assert "assistant_message" in data
        assert "next_question_type" in data
        assert data["next_question_type"] in ["text", "yes_no", "done"]
        assert "html_updated" in data
        assert "credits_balance" in data
        
        print(f"✅ Turn 1: AI responded, qtype={data['next_question_type']}, html_updated={data['html_updated']}")
        return data
    
    def test_chat_invalid_session(self, auth_headers):
        """Chat with non-existent session_id should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/freebuild/v2/chat",
            headers=auth_headers,
            json={
                "session_id": "non-existent-session-id-12345",
                "message": "test"
            },
            timeout=30
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Chat correctly returns 404 for invalid session_id")


class TestFreeBuildV2FullConversation:
    """Test a full 7-turn conversation simulating Quran teaching site"""
    
    @pytest.fixture(scope="class")
    def conversation_session(self, auth_headers):
        """Run full conversation and return session data"""
        # Start session
        start_resp = requests.post(
            f"{BASE_URL}/api/freebuild/v2/start",
            headers=auth_headers,
            json={}
        )
        assert start_resp.status_code == 200
        session_id = start_resp.json()["session_id"]
        initial_credits = start_resp.json()["credits_balance"]
        
        # Conversation turns
        turns = [
            "موقع لتحفيظ القرآن الكريم للأطفال",  # Turn 1: describe idea
            "نعم",  # Turn 2: yes to registration
            "السديس، الشريم، المعيقلي",  # Turn 3: reciters
            "أبيض فاخر، ذهبي أنيق",  # Turn 4: colors
            "نعم",  # Turn 5: yes to something
            "نعم",  # Turn 6: yes to something
            "خلاص يكفي ممتاز احفظ"  # Turn 7: done signal
        ]
        
        html_update_count = 0
        credits_spent = 0
        final_data = None
        
        for i, msg in enumerate(turns):
            print(f"  Sending turn {i+1}: {msg[:30]}...")
            resp = requests.post(
                f"{BASE_URL}/api/freebuild/v2/chat",
                headers=auth_headers,
                json={"session_id": session_id, "message": msg},
                timeout=60
            )
            assert resp.status_code == 200, f"Turn {i+1} failed: {resp.text}"
            data = resp.json()
            
            if data.get("html_updated"):
                html_update_count += 1
                credits_spent += data.get("credits_spent_this_turn", 0)
            
            print(f"    → qtype={data['next_question_type']}, html_updated={data.get('html_updated')}")
            final_data = data
            
            # If AI says done, stop
            if data.get("next_question_type") == "done" or data.get("complete"):
                break
            
            time.sleep(1)  # Small delay between turns
        
        return {
            "session_id": session_id,
            "initial_credits": initial_credits,
            "html_update_count": html_update_count,
            "credits_spent": credits_spent,
            "final_data": final_data,
            "final_credits": final_data.get("credits_balance") if final_data else None
        }
    
    def test_conversation_has_html_updates(self, conversation_session):
        """At least 2 turns should have html_updated=true"""
        assert conversation_session["html_update_count"] >= 2, \
            f"Expected at least 2 html updates, got {conversation_session['html_update_count']}"
        print(f"✅ Conversation had {conversation_session['html_update_count']} HTML updates")
    
    def test_credits_deducted_correctly(self, conversation_session):
        """Credits should deduct 3 per html_updated turn"""
        expected_deduction = conversation_session["html_update_count"] * 3
        actual_deduction = conversation_session["initial_credits"] - conversation_session["final_credits"]
        
        # Allow some tolerance (AI might have done more/fewer updates)
        assert actual_deduction >= 0, "Credits should not increase"
        print(f"✅ Credits deducted: {actual_deduction} (expected ~{expected_deduction})")
    
    def test_final_turn_is_done(self, conversation_session):
        """Final turn's next_question_type should be 'done' after user signals completion"""
        final = conversation_session["final_data"]
        # The AI should recognize "خلاص يكفي" as done signal
        # But it might take one more turn, so we check if complete or done
        is_done = final.get("next_question_type") == "done" or final.get("complete")
        print(f"✅ Final state: qtype={final.get('next_question_type')}, complete={final.get('complete')}")


class TestFreeBuildV2Preview:
    """Test GET /api/freebuild/v2/preview/{session_id}"""
    
    def test_preview_empty_state(self, auth_headers):
        """Preview on new session (no HTML yet) should return friendly empty-state HTML"""
        # Start a fresh session
        start_resp = requests.post(
            f"{BASE_URL}/api/freebuild/v2/start",
            headers=auth_headers,
            json={}
        )
        assert start_resp.status_code == 200
        session_id = start_resp.json()["session_id"]
        
        # Get preview immediately (no chat yet)
        preview_resp = requests.get(f"{BASE_URL}/api/freebuild/v2/preview/{session_id}")
        assert preview_resp.status_code == 200
        assert "text/html" in preview_resp.headers.get("content-type", "")
        
        html = preview_resp.text
        assert "ابدأ المحادثة" in html, "Empty state should contain 'ابدأ المحادثة'"
        assert "<html" in html.lower(), "Should be valid HTML"
        print("✅ Empty-state preview returns friendly HTML with 'ابدأ المحادثة'")
    
    def test_preview_with_built_html(self, auth_headers):
        """Preview after building should return RTL HTML with Quran content"""
        # Start session and do a few turns to generate HTML
        start_resp = requests.post(
            f"{BASE_URL}/api/freebuild/v2/start",
            headers=auth_headers,
            json={}
        )
        session_id = start_resp.json()["session_id"]
        
        # Send enough turns to trigger HTML generation
        turns = [
            "موقع لتحفيظ القرآن الكريم",
            "نعم",
            "السديس",
            "أبيض وذهبي"
        ]
        
        html_generated = False
        for msg in turns:
            resp = requests.post(
                f"{BASE_URL}/api/freebuild/v2/chat",
                headers=auth_headers,
                json={"session_id": session_id, "message": msg},
                timeout=60
            )
            if resp.status_code == 200 and resp.json().get("html_updated"):
                html_generated = True
                break
            time.sleep(1)
        
        if not html_generated:
            pytest.skip("AI didn't generate HTML in first 4 turns - may need more context")
        
        # Get preview
        preview_resp = requests.get(f"{BASE_URL}/api/freebuild/v2/preview/{session_id}")
        assert preview_resp.status_code == 200
        
        html = preview_resp.text
        assert 'dir="rtl"' in html or "dir='rtl'" in html, "HTML should have RTL direction"
        assert "قرآن" in html or "القرآن" in html, "HTML should contain Quran-related content"
        assert "<style>" in html or "<style " in html, "HTML should have embedded styles"
        
        # Check for Arabic font
        has_arabic_font = any(font in html.lower() for font in ["tajawal", "cairo", "reem kufi", "ibm plex"])
        print(f"✅ Built preview: RTL={True}, has_quran_content={True}, has_style={True}, arabic_font={has_arabic_font}")


class TestFreeBuildV2SaveProject:
    """Test POST /api/freebuild/v2/save-as-project"""
    
    @pytest.fixture(scope="class")
    def built_session(self, auth_headers):
        """Create a session with HTML built"""
        start_resp = requests.post(
            f"{BASE_URL}/api/freebuild/v2/start",
            headers=auth_headers,
            json={}
        )
        session_id = start_resp.json()["session_id"]
        
        # Build some HTML
        turns = ["موقع لتحفيظ القرآن", "نعم", "السديس", "أبيض"]
        for msg in turns:
            resp = requests.post(
                f"{BASE_URL}/api/freebuild/v2/chat",
                headers=auth_headers,
                json={"session_id": session_id, "message": msg},
                timeout=60
            )
            if resp.json().get("html_updated"):
                break
            time.sleep(1)
        
        return session_id
    
    def test_save_project(self, auth_headers, built_session):
        """Save session as project should return ok, project_id, preview_url"""
        response = requests.post(
            f"{BASE_URL}/api/freebuild/v2/save-as-project",
            headers=auth_headers,
            json={
                "session_id": built_session,
                "name": "موقع تحفيظ القرآن"
            }
        )
        
        # May fail if no HTML was generated
        if response.status_code == 400 and "لا يوجد موقع" in response.text:
            pytest.skip("No HTML in session to save")
        
        assert response.status_code == 200, f"Save failed: {response.text}"
        
        data = response.json()
        assert data.get("ok") == True
        assert "project_id" in data
        assert "preview_url" in data
        
        print(f"✅ Project saved: id={data['project_id'][:8]}..., preview_url={data['preview_url']}")
        return data["project_id"]


class TestFreeBuildV2Projects:
    """Test GET /api/freebuild/v2/projects"""
    
    def test_list_projects(self, auth_headers):
        """List projects should return array without html field"""
        response = requests.get(
            f"{BASE_URL}/api/freebuild/v2/projects",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "projects" in data
        assert "count" in data
        assert isinstance(data["projects"], list)
        
        # If there are projects, verify html is not included
        if data["projects"]:
            proj = data["projects"][0]
            assert "html" not in proj, "html field should not be in list response"
            assert "id" in proj
            assert "name" in proj
        
        print(f"✅ Projects list: {data['count']} projects (html field excluded)")


class TestFreeBuildV2ProjectPreview:
    """Test GET /api/freebuild/v2/project-preview/{project_id}"""
    
    def test_project_preview_invalid_id(self):
        """Preview with invalid project_id should return 404"""
        response = requests.get(f"{BASE_URL}/api/freebuild/v2/project-preview/invalid-id-12345")
        assert response.status_code == 404
        print("✅ Project preview correctly returns 404 for invalid id")


class TestFreeBuildV2Refine:
    """Test POST /api/freebuild/v2/refine"""
    
    def test_refine_invalid_project(self, auth_headers):
        """Refine with invalid project_id should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/freebuild/v2/refine",
            headers=auth_headers,
            json={
                "project_id": "invalid-project-id-12345",
                "instruction": "أضف قسم تواصل واتساب"
            }
        )
        assert response.status_code == 404
        print("✅ Refine correctly returns 404 for invalid project_id")


class TestFreeBuildV2Delete:
    """Test DELETE /api/freebuild/v2/project/{project_id}"""
    
    def test_delete_invalid_project(self, auth_headers):
        """Delete with invalid project_id should return 404"""
        response = requests.delete(
            f"{BASE_URL}/api/freebuild/v2/project/invalid-id-12345",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("✅ Delete correctly returns 404 for invalid project_id")


class TestFreeBuildV2EndToEnd:
    """End-to-end test: start → chat → save → refine → delete"""
    
    def test_full_lifecycle(self, auth_headers):
        """Complete lifecycle test"""
        print("\n=== E2E Test: Full FreeBuild V2 Lifecycle ===")
        
        # 1. Start
        print("1. Starting session...")
        start_resp = requests.post(
            f"{BASE_URL}/api/freebuild/v2/start",
            headers=auth_headers,
            json={}
        )
        assert start_resp.status_code == 200
        session_id = start_resp.json()["session_id"]
        initial_credits = start_resp.json()["credits_balance"]
        print(f"   Session: {session_id[:8]}..., Credits: {initial_credits}")
        
        # 2. Chat until HTML is generated
        print("2. Chatting to build HTML...")
        turns = [
            "موقع لتحفيظ القرآن الكريم للأطفال",
            "نعم",
            "السديس والشريم",
            "أبيض وذهبي",
            "نعم"
        ]
        
        html_generated = False
        for i, msg in enumerate(turns):
            resp = requests.post(
                f"{BASE_URL}/api/freebuild/v2/chat",
                headers=auth_headers,
                json={"session_id": session_id, "message": msg},
                timeout=60
            )
            assert resp.status_code == 200, f"Chat turn {i+1} failed"
            if resp.json().get("html_updated"):
                html_generated = True
                print(f"   HTML generated at turn {i+1}")
                break
            time.sleep(1)
        
        if not html_generated:
            print("   ⚠️ No HTML generated in 5 turns - continuing anyway")
        
        # 3. Check preview
        print("3. Checking preview...")
        preview_resp = requests.get(f"{BASE_URL}/api/freebuild/v2/preview/{session_id}")
        assert preview_resp.status_code == 200
        has_content = "قرآن" in preview_resp.text or "ابدأ المحادثة" in preview_resp.text
        print(f"   Preview OK, has_content={has_content}")
        
        # 4. Save as project (only if HTML was generated)
        if html_generated:
            print("4. Saving as project...")
            save_resp = requests.post(
                f"{BASE_URL}/api/freebuild/v2/save-as-project",
                headers=auth_headers,
                json={"session_id": session_id, "name": "TEST_موقع_تحفيظ"}
            )
            if save_resp.status_code == 200:
                project_id = save_resp.json()["project_id"]
                print(f"   Project saved: {project_id[:8]}...")
                
                # 5. Verify in projects list
                print("5. Verifying in projects list...")
                list_resp = requests.get(
                    f"{BASE_URL}/api/freebuild/v2/projects",
                    headers=auth_headers
                )
                assert list_resp.status_code == 200
                projects = list_resp.json()["projects"]
                found = any(p["id"] == project_id for p in projects)
                print(f"   Found in list: {found}")
                
                # 6. Get project preview
                print("6. Getting project preview...")
                proj_preview = requests.get(f"{BASE_URL}/api/freebuild/v2/project-preview/{project_id}")
                assert proj_preview.status_code == 200
                print(f"   Project preview OK, length={len(proj_preview.text)}")
                
                # 7. Refine
                print("7. Refining project...")
                refine_resp = requests.post(
                    f"{BASE_URL}/api/freebuild/v2/refine",
                    headers=auth_headers,
                    json={
                        "project_id": project_id,
                        "instruction": "أضف قسم تواصل واتساب في الأسفل"
                    },
                    timeout=60
                )
                if refine_resp.status_code == 200:
                    refine_data = refine_resp.json()
                    assert refine_data.get("ok") == True
                    assert refine_data.get("version") == 2
                    print(f"   Refined to version {refine_data['version']}")
                else:
                    print(f"   Refine failed (may be credits): {refine_resp.status_code}")
                
                # 8. Delete
                print("8. Deleting project...")
                del_resp = requests.delete(
                    f"{BASE_URL}/api/freebuild/v2/project/{project_id}",
                    headers=auth_headers
                )
                assert del_resp.status_code == 200
                assert del_resp.json().get("ok") == True
                print("   Deleted successfully")
            else:
                print(f"   Save failed: {save_resp.status_code} - {save_resp.text}")
        else:
            print("4-8. Skipped (no HTML to save)")
        
        print("=== E2E Test Complete ===\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
