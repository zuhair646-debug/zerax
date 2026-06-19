"""Verify Auto-Resume Reminder endpoints + cadence logic."""

import os
import sys
from datetime import datetime, timezone, timedelta

import httpx
import pytest

API = os.environ.get("PYTEST_API_URL") or os.environ.get(
    "REACT_APP_BACKEND_URL", "https://ai-cinematic-hub-2.preview.emergentagent.com"
)
USER = {"email": "owner@zerax.com", "password": "owner123"}


@pytest.fixture(scope="module")
def token():
    r = httpx.post(f"{API}/api/auth/login", json=USER, timeout=15)
    r.raise_for_status()
    return r.json()["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_get_my_settings_returns_opt_out_bool(token):
    r = httpx.get(f"{API}/api/resume-reminders/me", headers=auth(token), timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "opt_out" in data
    assert isinstance(data["opt_out"], bool)


def test_toggle_opt_out_persists(token):
    # Set true
    r = httpx.post(
        f"{API}/api/resume-reminders/me/opt-out",
        headers=auth(token),
        json={"opt_out": True},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    assert r.json()["opt_out"] is True
    # Read back
    r2 = httpx.get(f"{API}/api/resume-reminders/me", headers=auth(token), timeout=15)
    assert r2.json()["opt_out"] is True
    # Reset
    httpx.post(
        f"{API}/api/resume-reminders/me/opt-out",
        headers=auth(token),
        json={"opt_out": False},
        timeout=15,
    )


def test_my_history_returns_items_list(token):
    r = httpx.get(f"{API}/api/resume-reminders/me/history", headers=auth(token), timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert isinstance(body["items"], list)


def test_admin_run_now_scans_all_sources(token):
    r = httpx.post(
        f"{API}/api/resume-reminders/admin/run-now",
        headers=auth(token),
        json={"force": False},
        timeout=60,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "scanned" in body
    assert "sent" in body
    assert "skipped" in body
    assert "by_source" in body
    # Must scan at least the 3 known sources
    assert "freebuild_projects" in body["by_source"]
    assert "game_projects" in body["by_source"]
    assert "video_series" in body["by_source"]


def test_admin_run_now_requires_admin():
    # Use a non-admin token if one exists; otherwise skip.
    # In dev, we don't have a known plain-user account, so we just verify the
    # endpoint actually exists and rejects missing auth.
    r = httpx.post(f"{API}/api/resume-reminders/admin/run-now", json={}, timeout=15)
    assert r.status_code in (401, 403)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
