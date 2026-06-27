"""
Regression test for the cancellation-quota retention bug (Feb 2026).

Bug: When a user cancels an active subscription, their quota was instantly
dropping to the trial 2MB limit instead of retaining the paid quota until
`current_period_end`.

Fix: `_evaluate_subscription_state` now flips a stale 'cancelled' status back
to 'active' while `current_period_end` is in the future, and
`_quota_for_subscription` has a defensive fallback for the same case.

Run:  cd /app/backend && pytest tests/test_cancellation_quota_retention.py -q
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone, timedelta

import pytest

from modules.storage_billing import (
    _evaluate_subscription_state,
    _quota_for_subscription,
)


class _FakeCollection:
    def __init__(self, doc):
        self._doc = doc
        self.updates = []

    async def find_one(self, *args, **kwargs):
        if not self._doc:
            return None
        return dict(self._doc)

    async def update_one(self, query, update, upsert=False):
        self.updates.append((query, update, upsert))
        # Apply the $set to the doc so subsequent reads see the change
        new_vals = update.get("$set", {})
        if self._doc is None:
            self._doc = {}
        self._doc.update(new_vals)


class _FakeDB:
    def __init__(self, sub_doc):
        self.storage_subscriptions = _FakeCollection(sub_doc)
        self.users = _FakeCollection({})
        self.freebuild_projects = _FakeCollection(None)


@pytest.mark.asyncio
async def test_cancelled_with_future_period_end_keeps_paid_quota():
    """User cancelled but period_end is 20 days away → still has 50MB quota."""
    now = datetime.now(timezone.utc)
    future = (now + timedelta(days=20)).isoformat()
    sub_doc = {
        "user_id": "u1",
        "plan_id": "s50",
        "status": "cancelled",   # ← stale state, simulating webhook race
        "current_period_end": future,
        "cancelled_at": now.isoformat(),
        "auto_renew": False,
    }
    db = _FakeDB(sub_doc)
    sub = await _evaluate_subscription_state(db, "u1")

    # Eval should flip status back to 'active' until period_end.
    assert sub["status"] == "active", f"expected active, got {sub['status']}"

    info = _quota_for_subscription(sub)
    assert info["quota_mb"] == 50, f"expected 50MB quota, got {info['quota_mb']}"
    assert info["locked"] is False, "user must NOT be locked while paid period is active"


@pytest.mark.asyncio
async def test_cancelled_with_past_period_end_archives_user():
    """User cancelled + period_end already passed → archived (locked)."""
    now = datetime.now(timezone.utc)
    past = (now - timedelta(days=1)).isoformat()
    sub_doc = {
        "user_id": "u2",
        "plan_id": "s50",
        "status": "cancelled",
        "current_period_end": past,
        "cancelled_at": (now - timedelta(days=35)).isoformat(),
        "auto_renew": False,
    }
    db = _FakeDB(sub_doc)
    sub = await _evaluate_subscription_state(db, "u2")
    assert sub["status"] == "archived"
    info = _quota_for_subscription(sub)
    assert info["locked"] is True


@pytest.mark.asyncio
async def test_active_with_autorenew_false_past_period_end_archives():
    """Active+auto_renew=false (cancelled mid-period) once period_end passes → archived."""
    now = datetime.now(timezone.utc)
    past = (now - timedelta(hours=1)).isoformat()
    sub_doc = {
        "user_id": "u3",
        "plan_id": "s100",
        "status": "active",
        "auto_renew": False,
        "current_period_end": past,
        "cancelled_at": (now - timedelta(days=10)).isoformat(),
    }
    db = _FakeDB(sub_doc)
    sub = await _evaluate_subscription_state(db, "u3")
    # Cancelled + period over → archive directly (no extra grace).
    assert sub["status"] == "archived"


@pytest.mark.asyncio
async def test_quota_safety_net_for_stale_cancelled_status():
    """Direct call to _quota_for_subscription must also respect future period_end."""
    future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    sub = {
        "user_id": "u4",
        "plan_id": "s100",
        "status": "cancelled",
        "current_period_end": future,
        "auto_renew": False,
    }
    info = _quota_for_subscription(sub)
    assert info["quota_mb"] == 100
    assert info["locked"] is False
