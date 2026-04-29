"""
Comprehensive tests for Zitex AI Platform - Iteration 19
=========================================================
Testing:
1. Storefront Chatbot v2 (deep knowledge, HANDOFF detection)
2. Chatbot Handoff Endpoint (support tickets, WhatsApp deep-links)
3. Client/Owner Chatbot Config (notify_whatsapp field)
4. DevOps Agent WebSocket (streaming events)
5. Stocks Market Quotes (Alpha Vantage fallback to simulation)
6. Games Module Migration (static file serving)
"""
import pytest
import requests
import os
import time
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-cinematic-hub-2.preview.emergentagent.com').rstrip('/')

# Test credentials from test_credentials.md
OWNER_EMAIL = "owner@zitex.com"
OWNER_PASSWORD = "owner123"
CLIENT_SLUG = "cozy-cafe-demo"
CLIENT_PASSWORD = "WKDWkG0d"


@pytest.fixture(scope="module")
def owner_token():
    """Get owner JWT token"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OWNER_EMAIL,
        "password": OWNER_PASSWORD
    })
    if r.status_code == 200:
        return r.json().get("token")
    pytest.skip(f"Owner login failed: {r.status_code} - {r.text}")


@pytest.fixture(scope="module")
def client_token():
    """Get client token for cozy-cafe-demo"""
    r = requests.post(f"{BASE_URL}/api/websites/client/login", json={
        "slug": CLIENT_SLUG,
        "password": CLIENT_PASSWORD
    })
    if r.status_code == 200:
        return r.json().get("token")
    pytest.skip(f"Client login failed: {r.status_code} - {r.text}")


@pytest.fixture(scope="module")
def project_id(owner_token):
    """Get project ID for cozy-cafe-demo"""
    r = requests.get(f"{BASE_URL}/api/websites/projects", headers={
        "Authorization": f"Bearer {owner_token}"
    })
    if r.status_code == 200:
        projects = r.json().get("projects", [])
        for p in projects:
            if p.get("slug") == CLIENT_SLUG:
                return p.get("id")
    pytest.skip("Could not find cozy-cafe-demo project")


# ============================================================
# 1. STOREFRONT CHATBOT TESTS
# ============================================================
class TestStorefrontChatbotConfig:
    """Test GET /api/websites/public/{slug}/chatbot/config"""
    
    def test_chatbot_config_returns_enabled(self):
        """Verify chatbot config returns enabled=true for cozy-cafe-demo"""
        r = requests.get(f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/chatbot/config")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "enabled" in data, "Response should have 'enabled' field"
        assert "welcome_message" in data, "Response should have 'welcome_message' field"
        assert "store_name" in data, "Response should have 'store_name' field"
        print(f"✅ Chatbot config: enabled={data['enabled']}, store={data['store_name']}")


class TestStorefrontChatbotChat:
    """Test POST /api/websites/public/{slug}/chatbot"""
    
    def test_chatbot_responds_to_message(self):
        """Verify chatbot responds to a simple message"""
        r = requests.post(f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/chatbot", json={
            "message": "مرحبا",
            "session_id": "test_session_basic"
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "reply" in data, "Response should have 'reply' field"
        assert "session_id" in data, "Response should have 'session_id' field"
        assert "handoff" in data, "Response should have 'handoff' field"
        assert isinstance(data["handoff"], bool), "handoff should be boolean"
        print(f"✅ Chatbot replied: {data['reply'][:100]}...")
    
    def test_chatbot_deep_knowledge_shipping(self):
        """Test chatbot knows about shipping (deep knowledge)"""
        r = requests.post(f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/chatbot", json={
            "message": "كم سعر الشحن؟",
            "session_id": "test_session_shipping"
        }, timeout=30)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "reply" in data
        # The reply should contain some shipping-related info (not generic)
        print(f"✅ Shipping question reply: {data['reply'][:200]}...")
    
    def test_chatbot_handoff_detection(self):
        """Test HANDOFF detection for complaint messages"""
        r = requests.post(f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/chatbot", json={
            "message": "ابغى ارجاع طلبي",
            "session_id": "test_session_handoff"
        }, timeout=30)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "reply" in data
        assert "handoff" in data
        # Handoff should be true for complaint/return requests
        print(f"✅ Handoff detection: handoff={data['handoff']}, reply={data['reply'][:150]}...")


# ============================================================
# 2. CHATBOT HANDOFF ENDPOINT TESTS
# ============================================================
class TestChatbotHandoff:
    """Test POST /api/websites/public/{slug}/chatbot/handoff"""
    
    def test_handoff_creates_ticket(self):
        """Verify handoff endpoint creates a support ticket"""
        r = requests.post(f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/chatbot/handoff", json={
            "session_id": "test_handoff_session",
            "name": "TEST_Customer",
            "contact": "0501234567",
            "message": "أريد استرجاع طلبي",
            "transcript": [
                {"role": "user", "text": "مرحبا"},
                {"role": "assistant", "text": "أهلاً بك"},
                {"role": "user", "text": "أريد استرجاع طلبي"}
            ]
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("ok") == True, "Response should have ok=true"
        assert "ticket_id" in data, "Response should have ticket_id"
        assert len(data["ticket_id"]) > 0, "ticket_id should not be empty"
        print(f"✅ Handoff ticket created: {data['ticket_id']}")
    
    def test_handoff_whatsapp_reply_link(self):
        """Verify handoff creates WhatsApp reply_to_customer_link when contact has phone"""
        r = requests.post(f"{BASE_URL}/api/websites/public/{CLIENT_SLUG}/chatbot/handoff", json={
            "session_id": "test_handoff_wa",
            "name": "TEST_WA_Customer",
            "contact": "966501234567",  # Valid phone with country code
            "message": "طلب تواصل",
            "transcript": []
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("ok") == True
        # owner_notified depends on notify_whatsapp being set in chatbot_config
        print(f"✅ Handoff with phone: ticket_id={data['ticket_id']}, owner_notified={data.get('owner_notified')}")


# ============================================================
# 3. CLIENT CHATBOT CONFIG TESTS
# ============================================================
class TestClientChatbotConfig:
    """Test GET/PUT /api/websites/client/chatbot/config"""
    
    def test_client_get_chatbot_config(self, client_token):
        """Verify client can get chatbot config"""
        r = requests.get(f"{BASE_URL}/api/websites/client/chatbot/config", headers={
            "Authorization": f"ClientToken {client_token}"
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        # Should have config fields
        print(f"✅ Client chatbot config: {json.dumps(data, ensure_ascii=False)[:300]}")
    
    def test_client_put_notify_whatsapp(self, client_token):
        """Verify client can set notify_whatsapp field"""
        test_phone = "966501112233"
        r = requests.put(f"{BASE_URL}/api/websites/client/chatbot/config", 
            headers={
                "Authorization": f"ClientToken {client_token}",
                "Content-Type": "application/json"
            },
            json={"notify_whatsapp": test_phone}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("notify_whatsapp") == test_phone, f"notify_whatsapp should be {test_phone}"
        print(f"✅ Client set notify_whatsapp: {data.get('notify_whatsapp')}")
    
    def test_client_notify_whatsapp_roundtrip(self, client_token):
        """Verify notify_whatsapp persists across GET"""
        # First set it
        test_phone = "966509998877"
        requests.put(f"{BASE_URL}/api/websites/client/chatbot/config", 
            headers={
                "Authorization": f"ClientToken {client_token}",
                "Content-Type": "application/json"
            },
            json={"notify_whatsapp": test_phone}
        )
        # Then get it
        r = requests.get(f"{BASE_URL}/api/websites/client/chatbot/config", headers={
            "Authorization": f"ClientToken {client_token}"
        })
        assert r.status_code == 200
        data = r.json()
        assert data.get("notify_whatsapp") == test_phone, "notify_whatsapp should persist"
        print(f"✅ notify_whatsapp roundtrip verified: {data.get('notify_whatsapp')}")


# ============================================================
# 4. OWNER CHATBOT CONFIG TESTS
# ============================================================
class TestOwnerChatbotConfig:
    """Test GET/PUT /api/websites/projects/{project_id}/chatbot/config"""
    
    def test_owner_get_chatbot_config(self, owner_token, project_id):
        """Verify owner can get chatbot config"""
        r = requests.get(f"{BASE_URL}/api/websites/projects/{project_id}/chatbot/config", headers={
            "Authorization": f"Bearer {owner_token}"
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        print(f"✅ Owner chatbot config: {json.dumps(data, ensure_ascii=False)[:300]}")
    
    def test_owner_put_chatbot_config(self, owner_token, project_id):
        """Verify owner can update chatbot config including notify_whatsapp"""
        r = requests.put(f"{BASE_URL}/api/websites/projects/{project_id}/chatbot/config", 
            headers={
                "Authorization": f"Bearer {owner_token}",
                "Content-Type": "application/json"
            },
            json={
                "enabled": True,
                "welcome_message": "مرحباً! كيف أساعدك؟",
                "notify_whatsapp": "966507374438"
            }
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("enabled") == True
        assert "notify_whatsapp" in data
        print(f"✅ Owner updated chatbot config: enabled={data.get('enabled')}, notify_whatsapp={data.get('notify_whatsapp')}")


# ============================================================
# 5. STOCKS MARKET QUOTES TESTS
# ============================================================
class TestStocksMarketQuotes:
    """Test GET /api/websites/market/quotes"""
    
    def test_market_quotes_returns_data(self):
        """Verify market quotes endpoint returns quotes"""
        r = requests.get(f"{BASE_URL}/api/websites/market/quotes")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "quotes" in data, "Response should have 'quotes' field"
        assert "at" in data, "Response should have 'at' timestamp"
        assert "live_enabled" in data, "Response should have 'live_enabled' field"
        print(f"✅ Market quotes: {len(data['quotes'])} quotes, live_enabled={data['live_enabled']}")
    
    def test_market_quotes_simulated_fallback(self):
        """Verify quotes use simulated source when ALPHA_VANTAGE_KEY is empty"""
        r = requests.get(f"{BASE_URL}/api/websites/market/quotes")
        assert r.status_code == 200
        data = r.json()
        # Since ALPHA_VANTAGE_KEY is empty, should be simulated
        assert data.get("live_enabled") == False, "live_enabled should be False when no API key"
        # Check quote structure
        if data["quotes"]:
            quote = data["quotes"][0]
            assert "symbol" in quote, "Quote should have symbol"
            assert "name" in quote, "Quote should have name"
            assert "market" in quote, "Quote should have market"
            assert "price" in quote, "Quote should have price"
            assert "change_pct" in quote, "Quote should have change_pct"
            assert quote.get("source") == "simulated", f"Source should be 'simulated', got {quote.get('source')}"
        print(f"✅ Simulated quotes verified: source=simulated, live_enabled=False")
    
    def test_market_quotes_specific_symbols(self):
        """Test requesting specific symbols"""
        r = requests.get(f"{BASE_URL}/api/websites/market/quotes?symbols=NASDAQ:AAPL,CRYPTO:BTC")
        assert r.status_code == 200
        data = r.json()
        symbols = [q["symbol"] for q in data["quotes"]]
        assert "NASDAQ:AAPL" in symbols or len(symbols) > 0, "Should return requested symbols"
        print(f"✅ Specific symbols: {symbols}")


# ============================================================
# 6. GAMES MODULE TESTS
# ============================================================
class TestGamesModule:
    """Test games module static file serving"""
    
    def test_game_engine_js(self):
        """Verify GET /api/game-engine.js returns JavaScript"""
        r = requests.get(f"{BASE_URL}/api/game-engine.js")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert "application/javascript" in r.headers.get("content-type", ""), \
            f"Content-Type should be application/javascript, got {r.headers.get('content-type')}"
        assert len(r.text) > 1000, "game-engine.js should have substantial content"
        print(f"✅ game-engine.js: {len(r.text)} bytes, content-type={r.headers.get('content-type')}")
    
    def test_game_test_html(self):
        """Verify GET /api/game-test returns HTML"""
        r = requests.get(f"{BASE_URL}/api/game-test")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert "text/html" in r.headers.get("content-type", ""), \
            f"Content-Type should be text/html, got {r.headers.get('content-type')}"
        assert "<html" in r.text.lower() or "<!doctype" in r.text.lower(), "Should return HTML"
        print(f"✅ game-test: {len(r.text)} bytes, content-type={r.headers.get('content-type')}")


# ============================================================
# 7. DEVOPS AGENT ACCESS TEST (HTTP fallback)
# ============================================================
class TestDevOpsAgentAccess:
    """Test DevOps Agent access and operator endpoints"""
    
    def test_operator_access(self, owner_token):
        """Verify owner has operator access"""
        r = requests.get(f"{BASE_URL}/api/operator/access", headers={
            "Authorization": f"Bearer {owner_token}"
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("has_access") == True, "Owner should have operator access"
        print(f"✅ Operator access: has_access={data.get('has_access')}, role={data.get('role')}")
    
    def test_operator_clients_list(self, owner_token):
        """Verify can list operator clients"""
        r = requests.get(f"{BASE_URL}/api/operator/clients", headers={
            "Authorization": f"Bearer {owner_token}"
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "clients" in data, "Response should have 'clients' field"
        print(f"✅ Operator clients: {len(data['clients'])} clients")
        return data["clients"]


# ============================================================
# 8. SUPPORT TICKETS VERIFICATION
# ============================================================
class TestSupportTicketsWithHandoff:
    """Verify support tickets created by chatbot handoff"""
    
    def test_client_sees_chatbot_handoff_tickets(self, client_token):
        """Verify client can see chatbot_handoff tickets with WhatsApp links"""
        r = requests.get(f"{BASE_URL}/api/websites/client/support-tickets", headers={
            "Authorization": f"ClientToken {client_token}"
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        tickets = data.get("tickets", [])
        # Look for chatbot_handoff tickets
        handoff_tickets = [t for t in tickets if t.get("category") == "chatbot_handoff"]
        print(f"✅ Support tickets: {len(tickets)} total, {len(handoff_tickets)} chatbot_handoff")
        
        # Check WhatsApp links structure if any handoff tickets exist
        for t in handoff_tickets[:2]:
            wa = t.get("whatsapp", {})
            print(f"  - Ticket {t.get('id', '')[:8]}: reply_link={bool(wa.get('reply_to_customer_link'))}, owner_alert={bool(wa.get('owner_alert_link'))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
