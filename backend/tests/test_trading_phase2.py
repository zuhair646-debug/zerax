"""Phase 2 AI Trading Bot — backend API tests.

Tests the public surface of /api/trading/* without Alpaca creds.
- Owner JWT guard
- Halal whitelist enforcement (BEFORE Alpaca check)
- Default settings + persistence
- Endpoints needing live Alpaca correctly return 400 'Alpaca not connected'
"""
import os
import time

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-cinematic-hub-2.preview.emergentagent.com").rstrip("/")
OWNER_EMAIL = "owner@zerax.com"
OWNER_PWD = "owner123"


# ─── Fixtures ───────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def owner_token(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PWD})
    assert r.status_code == 200, f"Owner login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data
    assert data["user"]["role"] == "owner"
    return data["token"]


@pytest.fixture(scope="session")
def auth_headers(owner_token):
    return {"Content-Type": "application/json", "Authorization": f"Bearer {owner_token}"}


@pytest.fixture(scope="session", autouse=True)
def cleanup_creds_before(api, auth_headers):
    """Ensure no Alpaca creds are saved before tests (so 'not connected' scenarios hold)."""
    requests.post(f"{BASE_URL}/api/trading/disconnect", headers=auth_headers)
    yield


# ─── Auth & Status ──────────────────────────────────────────────────────────
class TestAuthAndStatus:
    def test_login_returns_owner_jwt(self, owner_token):
        assert isinstance(owner_token, str) and len(owner_token) > 20

    def test_status_no_auth_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/trading/status")
        assert r.status_code == 401

    def test_status_with_owner(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/trading/status", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["connected"] is False
        assert data["halal_tickers_count"] == 22


# ─── Halal whitelist ────────────────────────────────────────────────────────
class TestHalalStocks:
    def test_halal_stocks_list(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/trading/halal-stocks", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 22
        tickers = {s["t"] for s in data["stocks"]}
        for required in ("AAPL", "MSFT", "XOM"):
            assert required in tickers
        for s in data["stocks"]:
            assert {"t", "n", "s"}.issubset(s.keys())


# ─── Account / trades / suggestions baseline ────────────────────────────────
class TestBaselineEndpoints:
    def test_account_no_creds(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/trading/account", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["connected"] is False
        assert data["balance"] == 0

    def test_recent_trades_empty(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/trading/recent-trades", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert isinstance(data["trades"], list)

    def test_ai_suggestions_empty(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/trading/ai-suggestions", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert isinstance(data["suggestions"], list)


# ─── Settings persistence ───────────────────────────────────────────────────
class TestSettings:
    def test_get_settings_defaults_or_persisted(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/trading/settings", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        for key in ("max_position_pct", "daily_loss_limit_pct", "cooldown_minutes"):
            assert key in data

    def test_post_settings_persists(self, auth_headers):
        payload = {"max_position_pct": 15.0, "daily_loss_limit_pct": 3.5, "cooldown_minutes": 7}
        r = requests.post(f"{BASE_URL}/api/trading/settings", headers=auth_headers, json=payload)
        assert r.status_code == 200
        # GET to confirm persistence
        r2 = requests.get(f"{BASE_URL}/api/trading/settings", headers=auth_headers)
        d2 = r2.json()
        assert d2["max_position_pct"] == 15.0
        assert d2["daily_loss_limit_pct"] == 3.5
        assert d2["cooldown_minutes"] == 7

        # Restore defaults
        defaults = {"max_position_pct": 20.0, "daily_loss_limit_pct": 5.0, "cooldown_minutes": 5}
        requests.post(f"{BASE_URL}/api/trading/settings", headers=auth_headers, json=defaults)

    def test_agent_toggle_running_true(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/trading/agent/toggle?running=true", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["agent_running"] is True
        # confirm via /status
        s = requests.get(f"{BASE_URL}/api/trading/status", headers=auth_headers).json()
        assert s["agent_running"] is True
        # Reset
        requests.post(f"{BASE_URL}/api/trading/agent/toggle?running=false", headers=auth_headers)


# ─── Connect with fake creds (Alpaca validation) ────────────────────────────
class TestConnect:
    def test_connect_fake_creds_rejected(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/trading/connect", headers=auth_headers,
                          json={"api_key_id": "FAKE", "secret_key": "FAKE", "paper": True})
        assert r.status_code == 400
        assert "Invalid Alpaca credentials" in r.text


# ─── Quote endpoint (Halal screening + Alpaca connection) ──────────────────
class TestQuote:
    def test_quote_non_halal_400(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/trading/quote/JPM", headers=auth_headers)
        assert r.status_code == 400
        assert "Halal whitelist" in r.text or "whitelist" in r.text

    def test_quote_halal_but_no_alpaca(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/trading/quote/AAPL", headers=auth_headers)
        assert r.status_code == 400
        assert "Alpaca not connected" in r.text


# ─── Trade endpoint (Halal BEFORE Alpaca check) ─────────────────────────────
class TestTrade:
    def test_trade_non_halal_blocks_before_alpaca(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/trading/trade", headers=auth_headers,
                          json={"ticker": "JPM", "side": "buy", "notional": 50})
        assert r.status_code == 400
        assert "Sharia" in r.text or "whitelist" in r.text

    def test_trade_halal_no_alpaca(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/trading/trade", headers=auth_headers,
                          json={"ticker": "AAPL", "side": "buy", "notional": 50})
        assert r.status_code == 400
        assert "Alpaca not connected" in r.text

    def test_trade_halal_missing_qty_and_notional(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/trading/trade", headers=auth_headers,
                          json={"ticker": "AAPL", "side": "buy"})
        assert r.status_code == 400
        assert "Provide either qty or notional" in r.text


# ─── AI suggest endpoint ────────────────────────────────────────────────────
class TestAISuggest:
    def test_ai_suggest_non_halal(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/trading/ai-suggest", headers=auth_headers,
                          json={"ticker": "JPM"})
        assert r.status_code == 400

    def test_ai_suggest_halal_no_alpaca(self, auth_headers):
        r = requests.post(f"{BASE_URL}/api/trading/ai-suggest", headers=auth_headers,
                          json={"ticker": "AAPL"})
        assert r.status_code == 400
        assert "Alpaca not connected" in r.text


# ─── Market clock ───────────────────────────────────────────────────────────
class TestMarketClock:
    def test_clock_no_alpaca(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/trading/market-clock", headers=auth_headers)
        assert r.status_code == 400


# ─── Non-owner role rejection ───────────────────────────────────────────────
class TestNonOwnerForbidden:
    def test_non_owner_jwt_returns_403(self, api):
        # Try the audit test user from /app/memory/test_credentials.md
        r = api.post(f"{BASE_URL}/api/auth/login",
                     json={"email": "audit_1780793976@test.com", "password": "Test1234!"})
        if r.status_code != 200:
            pytest.skip(f"Non-owner test user login failed: {r.status_code}")
        token = r.json().get("token")
        if not token:
            pytest.skip("No token returned for non-owner login")
        headers = {"Authorization": f"Bearer {token}"}
        r2 = requests.get(f"{BASE_URL}/api/trading/status", headers=headers)
        assert r2.status_code == 403
        assert "Owner only" in r2.text or "Owner" in r2.text
