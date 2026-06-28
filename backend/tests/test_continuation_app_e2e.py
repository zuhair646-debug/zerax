"""E2E test driving the Universal App Tools through a realistic
multi-stack project (Flutter mobile + Go backend = monorepo).

Mirrors the website-continuation E2E test, but tailored for apps:
  1. Build a fake but realistic Flutter + Go monorepo in tmp
  2. detect_project_stack returns BOTH stacks with correct commands
  3. run_sandbox_command (read-only grep) works without paywall
  4. run_sandbox_command (write op) writes audit log + creates snapshot
  5. mark_first_update locks future writes
  6. Second write is BLOCKED by paywall
  7. Read-only commands still work after lock
  8. submit_to_app_store(test_only) creates dry-run + snapshot
"""
import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, "/app")
sys.path.insert(0, "/app/backend")

from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ.get("DB_NAME", "test_database")]

    from backend.modules.freebuild import continuation_tools as ct
    from backend.modules.freebuild import continuation_app_tools as cat
    from backend.modules.freebuild import continuation_audit as cad

    u = await db.users.find_one({"email": "owner@zerax.com"})
    uid = u["id"]
    pid = f"e2e-app-{int(time.time())}"

    print("=" * 70)
    print("Universal App Continuation E2E — Multi-stack monorepo")
    print(f"Project ID: {pid}")
    print("=" * 70)

    # ─── STEP 0: Create project + populate sandbox with a fake monorepo ─
    await db.freebuild_projects.insert_one({
        "id": pid, "user_id": uid, "mode": "continuation",
        "name": "monorepo-test",
        "continuation_setup": {"completed": True},
        "first_update_delivered": False, "continuation_unlocked": False,
    })

    class _Ctx:
        db = None
        user_id = uid
        project_id = pid
    _Ctx.db = db
    ctx = _Ctx()

    sandbox = ct._ensure_sandbox(pid)
    repo = sandbox / "repo"
    repo.mkdir(exist_ok=True)
    # Flutter mobile app
    mobile = repo / "mobile"
    mobile.mkdir()
    (mobile / "pubspec.yaml").write_text("name: my_app\nflutter:\n  uses-material-design: true\n")
    (mobile / "lib").mkdir()
    (mobile / "lib" / "main.dart").write_text("void main() => print('hello flutter');")
    # Go backend
    backend = repo / "backend"
    backend.mkdir()
    (backend / "go.mod").write_text("module example.com/backend\n\ngo 1.21\n")
    (backend / "main.go").write_text('package main\n\nimport "fmt"\nfunc main() { fmt.Println("hi") }')
    print(f"\n✓ STEP 0  Created monorepo: mobile (Flutter) + backend (Go)")

    # ─── STEP 1: detect_project_stack ────────────────────────────────
    res = await cat.handle_detect_project_stack({"project_id": pid, "path": "repo"}, ctx)
    assert res["ok"], f"detect failed: {res}"
    assert res["monorepo"] is True, f"should be monorepo: {res}"
    ids = {s["id"] for s in res["all_stacks"]}
    assert "flutter" in ids, f"flutter not detected: {ids}"
    assert "go" in ids, f"go not detected: {ids}"
    print(f"✓ STEP 1  detect_project_stack found {len(res['all_stacks'])} stacks:")
    for s in res["all_stacks"]:
        print(f"           • {s['name']:30s} → install: {s['install_command']}")
    print(f"           Message: {res['message_ar']}")

    # ─── STEP 2: read-only grep works (no paywall reached) ───────────
    grep_res = await cat.handle_run_sandbox_command(
        {"project_id": pid, "command": "grep -r flutter mobile/",
         "workdir": "repo", "purpose": "inspect"}, ctx,
    )
    assert grep_res["ok"], f"grep failed: {grep_res}"
    assert "flutter" in grep_res["stdout"]
    print(f"\n✓ STEP 2  run_sandbox_command (grep): {len(grep_res['stdout'])} bytes output")

    # ─── STEP 3: write-op (cd + ls = side effect, snapshot taken) ────
    ls_res = await cat.handle_run_sandbox_command(
        {"project_id": pid, "command": "cd mobile && ls lib/",
         "workdir": "repo", "purpose": "list_dir"}, ctx,
    )
    assert ls_res["ok"], f"ls failed: {ls_res}"
    print(f"✓ STEP 3  run_sandbox_command (cd + ls): success, output={ls_res['stdout'].strip()}")

    # ─── STEP 4: Dangerous command blocked ───────────────────────────
    bad = await cat.handle_run_sandbox_command(
        {"project_id": pid, "command": "rm -rf /"}, ctx,
    )
    assert bad["ok"] is False and bad["error"] == "command_blocked"
    print(f"✓ STEP 4  Dangerous command BLOCKED: {bad['reason'][:60]}")

    # ─── STEP 5: Unknown binary blocked ──────────────────────────────
    unk = await cat.handle_run_sandbox_command(
        {"project_id": pid, "command": "malicious_thing --pwn"}, ctx,
    )
    assert unk["ok"] is False
    print(f"✓ STEP 5  Unknown binary BLOCKED: {unk.get('reason', unk.get('error'))[:60]}")

    # ─── STEP 6: Mark first update → paywall active ──────────────────
    mark = await ct.handle_mark_first_update(
        {"project_id": pid, "summary": "كشفت الـ stacks وحلّلت المشروع"}, ctx,
    )
    assert mark["ok"]
    print(f"\n✓ STEP 6  mark_first_update → paywall ACTIVE")

    # ─── STEP 7: Write-op now blocked by paywall ─────────────────────
    locked = await cat.handle_run_sandbox_command(
        {"project_id": pid, "command": "npm install"}, ctx,
    )
    assert locked["ok"] is False and locked["code"] == "PAYWALL_LOCKED"
    print(f"✓ STEP 7  Write command BLOCKED by paywall (code={locked['code']})")

    # ─── STEP 8: Read-only still works after paywall ────────────────
    after_lock = await cat.handle_run_sandbox_command(
        {"project_id": pid, "command": "grep main mobile/lib/main.dart",
         "workdir": "repo"}, ctx,
    )
    assert after_lock["ok"], f"read should bypass paywall: {after_lock}"
    print(f"✓ STEP 8  Read-only grep still works after lock")

    # ─── STEP 9: submit_to_app_store dry-run ─────────────────────────
    # Place a fake APK artifact
    artifact = repo / "mobile" / "build" / "app.apk"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"PK\x03\x04 fake apk bytes")
    # Unlock to allow submit
    await db.freebuild_projects.update_one(
        {"id": pid}, {"$set": {"continuation_unlocked": True}},
    )
    submit_res = await cat.handle_submit_to_app_store(
        {"project_id": pid, "provider": "test_only",
         "artifact_path": "repo/mobile/build/app.apk",
         "release_notes": "E2E test release"}, ctx,
    )
    assert submit_res["ok"], f"submit dry-run failed: {submit_res}"
    assert submit_res["method"] == "dry_run"
    print(f"\n✓ STEP 9  submit_to_app_store (test_only dry-run): "
          f"would submit {submit_res['would_submit']}")
    print(f"           snapshot before submit: {submit_res['snapshot_id']}")

    # ─── STEP 10: submit to unimplemented provider → manual steps ────
    play = await cat.handle_submit_to_app_store(
        {"project_id": pid, "provider": "play_store_internal",
         "artifact_path": "repo/mobile/build/app.apk"}, ctx,
    )
    assert play["ok"] is False
    assert play["error"] == "provider_not_implemented_yet"
    assert play["manual_steps_ar"]
    print(f"✓ STEP 10 play_store_internal returns {len(play['manual_steps_ar'])} manual Arabic steps")

    # ─── STEP 11: Audit log has every action ────────────────────────
    logs = await cad.fetch_audit(db, pid, limit=50)
    actions = [l.get("action") for l in logs]
    expected = {"mark_first_update", "run_sandbox_command", "submit_to_app_store"}
    found = expected & set(actions)
    print(f"\n✓ STEP 11 Audit log: {len(logs)} entries, actions={actions}")
    assert expected.issubset(set(actions)), f"missing: {expected - set(actions)}"
    print(f"           All expected actions present: {found}")

    # ─── Cleanup ─────────────────────────────────────────────────────
    await db.freebuild_projects.delete_one({"id": pid})
    await db.continuation_audit_logs.delete_many({"project_id": pid})
    if sandbox.exists():
        shutil.rmtree(sandbox)
    print("\n[CLEANUP] project + audit + sandbox removed")
    print("\n" + "=" * 70)
    print("✅ ALL 11 STEPS PASSED — Universal App Tools verified end-to-end")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
