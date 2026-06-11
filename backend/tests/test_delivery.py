"""Tests for Zenrex Delivery + Driver Management API."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or os.environ.get("BACKEND_URL", "").rstrip("/")
# Fallback to internal so tests can run if env not set
if not BASE_URL:
    BASE_URL = "http://localhost:8001"

API = f"{BASE_URL}/api/delivery"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ── Health & Stats ──────────────────────────────────────────────────────────
def test_health(session):
    r = session.get(f"{API}/health", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "ok"
    assert data["drivers"] >= 5
    assert data["orders"] >= 5
    assert data["zones"] == 5


def test_stats(session):
    r = session.get(f"{API}/stats", timeout=15)
    assert r.status_code == 200
    data = r.json()
    by_status = data["by_status"]
    for k in ("pending", "assigned", "picked_up", "delivering", "delivered", "cancelled"):
        assert k in by_status
    assert data["total_drivers"] >= 5
    assert "active_drivers" in data
    assert "revenue_today_sar" in data


# ── Drivers CRUD ────────────────────────────────────────────────────────────
def test_list_drivers(session):
    r = session.get(f"{API}/drivers", timeout=15)
    assert r.status_code == 200
    data = r.json()
    drivers = data["drivers"]
    assert len(drivers) >= 5
    sample = drivers[0]
    for f in ("id", "name", "phone", "vehicle", "area", "status", "rating", "deliveries_today", "earnings_today_sar"):
        assert f in sample, f"missing {f}"


def test_create_driver_and_upsert(session):
    phone = "0509998888"
    payload = {"name": "TEST_driver_one", "phone": phone, "vehicle": "موتر", "area": "central"}
    r1 = session.post(f"{API}/drivers", json=payload, timeout=15)
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1["phone"] == phone
    assert "id" in d1
    first_id = d1["id"]

    # Upsert same phone — should not duplicate
    payload2 = {"name": "TEST_driver_updated", "phone": phone, "vehicle": "دباب", "area": "central"}
    r2 = session.post(f"{API}/drivers", json=payload2, timeout=15)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["id"] == first_id
    assert d2["name"] == "TEST_driver_updated"

    # cleanup
    session.delete(f"{API}/drivers/{first_id}", timeout=15)


def test_patch_driver(session):
    drivers = session.get(f"{API}/drivers").json()["drivers"]
    drv = drivers[0]
    r = session.patch(f"{API}/drivers/{drv['id']}", json={"status": "offline"}, timeout=15)
    assert r.status_code == 200
    assert r.json()["status"] == "offline"
    # restore
    session.patch(f"{API}/drivers/{drv['id']}", json={"status": drv["status"]}, timeout=15)


def test_delete_driver_unassigns_orders(session):
    # Create a driver and an order assigned to them
    pr = session.post(f"{API}/drivers", json={"name": "TEST_to_delete", "phone": "0500000123", "area": "central", "status": "online"}, timeout=15)
    drv = pr.json()
    did = drv["id"]
    # create an order then assign
    o = session.post(f"{API}/orders", json={
        "customer_name": "TEST_c", "customer_phone": "0500000999",
        "address": "test", "zone": "central",
        "items": [{"name": "x", "qty": 1, "sar": 10}],
        "total_sar": 10, "payment_method": "cash"
    }, timeout=15).json()
    session.patch(f"{API}/orders/{o['id']}/assign", json={"driver_id": did}, timeout=15)

    r = session.delete(f"{API}/drivers/{did}", timeout=15)
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # order should be unassigned + pending again
    o2 = session.get(f"{API}/orders/{o['id']}").json()
    assert o2["driver_id"] is None
    assert o2["status"] == "pending"


# ── Orders ───────────────────────────────────────────────────────────────────
def test_list_orders_filters(session):
    r = session.get(f"{API}/orders", timeout=15)
    assert r.status_code == 200
    all_orders = r.json()["orders"]
    assert len(all_orders) >= 5

    r2 = session.get(f"{API}/orders?status=pending", timeout=15)
    assert r2.status_code == 200
    for o in r2.json()["orders"]:
        assert o["status"] == "pending"

    # filter by driver
    a_driver = session.get(f"{API}/drivers").json()["drivers"][1]["id"]
    r3 = session.get(f"{API}/orders?driver_id={a_driver}", timeout=15)
    assert r3.status_code == 200
    for o in r3.json()["orders"]:
        assert o["driver_id"] == a_driver


def test_create_order_auto_assign(session):
    payload = {
        "customer_name": "TEST_auto_customer",
        "customer_phone": "0500001111",
        "address": "حي اختبار",
        "zone": "central",
        "items": [{"name": "test item", "qty": 1, "sar": 50}],
        "total_sar": 50,
        "payment_method": "cash"
    }
    r = session.post(f"{API}/orders", json=payload, timeout=15)
    assert r.status_code == 200
    o = r.json()
    # auto_assign is on by default — should have driver_id
    assert o["status"] in ("pending", "assigned")
    # delivery_fee_sar threshold (200) — 50 < 200 -> fee>0
    assert o["delivery_fee_sar"] > 0

    # large order = free delivery
    p2 = dict(payload, total_sar=500, items=[{"name": "big", "qty": 1, "sar": 500}])
    r2 = session.post(f"{API}/orders", json=p2, timeout=15)
    assert r2.status_code == 200
    assert r2.json()["delivery_fee_sar"] == 0


# ── Driver auth ──────────────────────────────────────────────────────────────
def test_driver_login_unknown(session):
    r = session.post(f"{API}/driver/login", json={"phone": "0599999999"}, timeout=15)
    assert r.status_code == 404
    # arabic message
    detail = r.json().get("detail", "")
    assert any(ord(c) > 127 for c in detail)


def test_driver_login_and_verify(session):
    phone = "0552222222"
    r = session.post(f"{API}/driver/login", json={"phone": phone}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["demo_code"] == "1234"

    # wrong otp
    rb = session.post(f"{API}/driver/verify-otp", json={"phone": phone, "code": "0000"}, timeout=15)
    assert rb.status_code == 401

    rv = session.post(f"{API}/driver/verify-otp", json={"phone": phone, "code": "1234"}, timeout=15)
    assert rv.status_code == 200
    body = rv.json()
    assert "token" in body
    assert body["driver"]["phone"] == phone


@pytest.fixture(scope="module")
def driver_token(session):
    phone = "0552222222"
    session.post(f"{API}/driver/login", json={"phone": phone}, timeout=15)
    r = session.post(f"{API}/driver/verify-otp", json={"phone": phone, "code": "1234"}, timeout=15)
    body = r.json()
    return body["token"], body["driver"]


def test_driver_me(session, driver_token):
    token, drv = driver_token
    r = session.get(f"{API}/driver/me", headers={"Authorization": f"DriverToken {token}"}, timeout=15)
    assert r.status_code == 200
    assert r.json()["id"] == drv["id"]
    assert r.json()["phone"] == "0552222222"

    # bad token
    rb = session.get(f"{API}/driver/me", headers={"Authorization": "DriverToken bad"}, timeout=15)
    assert rb.status_code == 401


def test_driver_feed(session, driver_token):
    token, drv = driver_token
    r = session.get(f"{API}/driver/feed", headers={"Authorization": f"DriverToken {token}"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "driver" in data
    assert "active" in data
    assert "done_today" in data
    assert "summary" in data
    summary = data["summary"]
    for k in ("deliveries_today", "earnings_today_sar", "earnings_week_sar", "rating"):
        assert k in summary


# ── Order status by driver ──────────────────────────────────────────────────
def test_status_change_permission_and_delivered_increments(session, driver_token):
    token, drv = driver_token

    # Create an order, assign to *another* driver, ensure 403
    other = next(d for d in session.get(f"{API}/drivers").json()["drivers"] if d["id"] != drv["id"])
    o = session.post(f"{API}/orders", json={
        "customer_name": "TEST_perm", "customer_phone": "0500002222",
        "address": "x", "zone": "central",
        "items": [{"name": "i", "qty": 1, "sar": 30}],
        "total_sar": 30, "payment_method": "cash"
    }, timeout=15).json()
    session.patch(f"{API}/orders/{o['id']}/assign", json={"driver_id": other["id"]}, timeout=15)

    rbad = session.patch(f"{API}/orders/{o['id']}/status",
                         json={"status": "picked_up"},
                         headers={"Authorization": f"DriverToken {token}"}, timeout=15)
    assert rbad.status_code == 403

    # Now assign to current driver and walk through to delivered
    session.patch(f"{API}/orders/{o['id']}/assign", json={"driver_id": drv["id"]}, timeout=15)

    drv_before = session.get(f"{API}/drivers").json()["drivers"]
    me_before = next(d for d in drv_before if d["id"] == drv["id"])
    deliv_before = me_before["deliveries_today"]
    earn_before = me_before["earnings_today_sar"]

    rok = session.patch(f"{API}/orders/{o['id']}/status",
                        json={"status": "delivered"},
                        headers={"Authorization": f"DriverToken {token}"}, timeout=15)
    assert rok.status_code == 200
    assert rok.json()["status"] == "delivered"

    me_after = next(d for d in session.get(f"{API}/drivers").json()["drivers"] if d["id"] == drv["id"])
    assert me_after["deliveries_today"] == deliv_before + 1
    assert me_after["earnings_today_sar"] == earn_before + 18


def test_location_update(session, driver_token):
    token, drv = driver_token
    # Create order and assign
    o = session.post(f"{API}/orders", json={
        "customer_name": "TEST_loc", "customer_phone": "0500003333",
        "address": "x", "zone": "central",
        "items": [{"name": "i", "qty": 1, "sar": 30}],
        "total_sar": 30, "payment_method": "cash"
    }, timeout=15).json()
    session.patch(f"{API}/orders/{o['id']}/assign", json={"driver_id": drv["id"]}, timeout=15)

    r = session.post(f"{API}/orders/{o['id']}/location",
                     json={"lat": 24.71, "lng": 46.68},
                     headers={"Authorization": f"DriverToken {token}"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["location"]["lat"] == 24.71

    # Confirm on order
    o2 = session.get(f"{API}/orders/{o['id']}").json()
    assert o2["current_location"]["lat"] == 24.71


# ── Public tracking ─────────────────────────────────────────────────────────
def test_public_track(session):
    # find an assigned-or-later order
    orders = session.get(f"{API}/orders").json()["orders"]
    target = next((o for o in orders if o.get("driver_id")), None)
    assert target is not None
    r = requests.get(f"{API}/orders/{target['id']}/track", timeout=15)  # no session = no headers
    assert r.status_code == 200
    data = r.json()
    for k in ("id", "status", "status_log", "eta_min", "address", "items", "total_sar", "delivery_fee_sar", "driver"):
        assert k in data
    # ensure internal fields are not present
    assert "notes" not in data
    assert "payment_method" not in data
    if data["driver"]:
        for k in ("name", "phone", "vehicle", "rating"):
            assert k in data["driver"]


# ── Settings ────────────────────────────────────────────────────────────────
def test_settings_update(session):
    r = session.patch(f"{API}/settings", json={"base_fee_sar": 17}, timeout=15)
    assert r.status_code == 200
    assert r.json()["base_fee_sar"] == 17
    g = session.get(f"{API}/settings").json()
    assert g["base_fee_sar"] == 17
    # restore
    session.patch(f"{API}/settings", json={"base_fee_sar": 15}, timeout=15)
