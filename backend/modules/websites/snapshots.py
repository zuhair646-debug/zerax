"""
Project Snapshots — Version History for website_projects.

Stores snapshots of project state (theme + sections + extras + wizard + widget_styles
+ payment_gateways.settings) so the client can restore any previous design
at any time. Auto-snapshot triggers on:

  • Wizard step advance (after user confirms)
  • AI chat action applied (add_section / apply_theme / apply_button / etc.)
  • Variant applied (apply-variant)
  • Manual save from client dashboard

Design decisions:
  - Stored INLINE inside project doc as `project.snapshots: List[Snapshot]`
    to avoid a separate collection. Keeps atomicity simple.
  - Max 30 snapshots per project (LRU eviction) — prevents bloat.
  - Each snapshot is small (~20-80KB), so 30 × 80KB = 2.4MB max per project,
    well under Mongo's 16MB doc limit.
  - `id` (ulid-like), `label` (human description), `origin` (trigger),
    `created_at`, `payload` (snapshot of state).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

MAX_SNAPSHOTS = 30


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


SNAPSHOT_FIELDS = ("theme", "sections", "extras", "wizard", "widget_styles", "name")


def build_snapshot(project: Dict[str, Any], label: str, origin: str = "manual") -> Dict[str, Any]:
    """Extract the snapshot payload from a project doc."""
    payload = {k: project.get(k) for k in SNAPSHOT_FIELDS}
    return {
        "id": f"snap_{uuid.uuid4().hex[:10]}",
        "label": label,
        "origin": origin,   # manual | wizard | ai_chat | variant | auto
        "created_at": _iso_now(),
        "sections_count": len(project.get("sections") or []),
        "payload": payload,
    }


def push_snapshot(project: Dict[str, Any], label: str, origin: str = "auto") -> List[Dict[str, Any]]:
    """Return the new snapshots list after appending; caller persists it."""
    snaps: List[Dict[str, Any]] = list(project.get("snapshots") or [])
    snap = build_snapshot(project, label=label, origin=origin)
    # Dedupe: skip if last snapshot has identical sections+theme (avoid noise)
    if snaps:
        last = snaps[-1]
        last_payload = last.get("payload") or {}
        if (
            last_payload.get("sections") == snap["payload"].get("sections")
            and last_payload.get("theme") == snap["payload"].get("theme")
            and last_payload.get("extras") == snap["payload"].get("extras")
        ):
            return snaps  # no-op
    snaps.append(snap)
    if len(snaps) > MAX_SNAPSHOTS:
        snaps = snaps[-MAX_SNAPSHOTS:]
    return snaps


def list_snapshots_summary(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return safe metadata list (NO full payload) — for catalogue display."""
    out = []
    for s in reversed(project.get("snapshots") or []):  # newest first
        out.append({
            "id": s.get("id"),
            "label": s.get("label"),
            "origin": s.get("origin"),
            "created_at": s.get("created_at"),
            "sections_count": s.get("sections_count"),
        })
    return out


def find_snapshot(project: Dict[str, Any], snapshot_id: str) -> Optional[Dict[str, Any]]:
    for s in project.get("snapshots") or []:
        if s.get("id") == snapshot_id:
            return s
    return None


def apply_snapshot(project: Dict[str, Any], snapshot_id: str) -> Optional[Dict[str, Any]]:
    """Return a dict of fields to $set on the project doc to restore the snapshot.
    Also pushes a NEW snapshot capturing the PRE-restore state so the user
    can undo the restore if they change their mind."""
    snap = find_snapshot(project, snapshot_id)
    if not snap:
        return None
    payload = snap.get("payload") or {}
    # Push pre-restore snapshot so user can undo
    new_snaps = push_snapshot(project, label=f"قبل الاستعادة إلى: {snap.get('label')}", origin="auto")
    update = {k: payload.get(k) for k in SNAPSHOT_FIELDS if payload.get(k) is not None}
    update["snapshots"] = new_snaps
    update["updated_at"] = _iso_now()
    return update
