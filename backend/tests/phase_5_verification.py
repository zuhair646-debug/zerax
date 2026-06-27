"""
🔬 PHASE 5 — Concierge + Executors comprehensive verification.

Tests:
  - Credential Vault: encrypt/decrypt/list/delete round-trip
  - State Machine: transitions + persistence
  - Knowledge Base: detection + rendering
  - Setup Wizard: all card types
  - Validators: format checks (no real API calls)
  - WebContainer Executor: enqueue + render HTML wrapper
  - Pyodide Executor: enqueue + render
  - EAS Build: function signatures
  - Liveblocks integrator: snippets
  - E2B / SSH: signature checks
  - HTTP endpoints: integrations list, detect-needs
"""
import asyncio
import json
import os
import sys
import uuid
sys.path.insert(0, "/app/backend")

P = 0; F = 0; FAILS = []
def ok(n, m=""):
    global P; P += 1
    print(f"  ✅ {n}" + (f" — {m}" if m else ""))
def fail(n, m):
    global F; F += 1; FAILS.append(f"{n}: {m}")
    print(f"  ❌ {n} — {m}")
def section(t): print(f"\n=== {t} ===")


async def _db():
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


async def test_vault():
    section("1) Credential Vault — encrypt/decrypt/list")
    from modules.freebuild.concierge.credential_vault import (
        store_credential, get_credential, list_credentials,
        has_credential, delete_credential, mark_validated, mask_for_display,
    )
    db = await _db()
    uid = f"test_{uuid.uuid4().hex[:6]}"

    # Clean
    await db.user_credentials.delete_many({"user_id": uid})

    saved = await store_credential(db, uid, "STRIPE_SECRET_KEY", "sk_test_abcdef12345_xyz")
    if saved: ok("vault-store")
    else: fail("vault-store", "store returned False")

    has = await has_credential(db, uid, "STRIPE_SECRET_KEY")
    if has: ok("vault-has")
    else: fail("vault-has", "has=False after store")

    val = await get_credential(db, uid, "STRIPE_SECRET_KEY")
    if val == "sk_test_abcdef12345_xyz": ok("vault-decrypt-roundtrip")
    else: fail("vault-decrypt-roundtrip", f"got {val!r}")

    # Verify cipher is NOT stored plaintext
    raw = await db.user_credentials.find_one({"user_id": uid, "key_name": "STRIPE_SECRET_KEY"})
    if raw and "sk_test_abcdef" not in (raw.get("encrypted_value") or ""):
        ok("vault-encryption-at-rest")
    else: fail("vault-encryption-at-rest", "plaintext leaked!")

    creds = await list_credentials(db, uid)
    if any(c.get("key_name") == "STRIPE_SECRET_KEY" and "encrypted_value" not in c for c in creds):
        ok("vault-list-no-plaintext")
    else: fail("vault-list-no-plaintext", str(creds)[:200])

    await mark_validated(db, uid, "STRIPE_SECRET_KEY", True)
    creds = await list_credentials(db, uid)
    if creds[0].get("valid") is True: ok("vault-mark-validated")
    else: fail("vault-mark-validated", str(creds[0]))

    m = mask_for_display("sk_test_abcdef12345_xyz")
    if m.startswith("sk_t") and m.endswith("_xyz") and "•" in m:
        ok("vault-mask")
    else: fail("vault-mask", m)

    deleted = await delete_credential(db, uid, "STRIPE_SECRET_KEY")
    if deleted: ok("vault-delete")
    else: fail("vault-delete")
    await db.user_credentials.delete_many({"user_id": uid})


async def test_state_machine():
    section("2) State Machine — transitions + history")
    from modules.freebuild.concierge.state_machine import (
        ConciergeState, load_state, save_state, transition,
        add_required_integration, get_required_integrations,
        mark_integration_satisfied,
    )
    db = await _db()
    pid = f"test_state_{uuid.uuid4().hex[:6]}"
    await db.concierge_state.delete_many({"project_id": pid})

    s = await load_state(db, pid)
    if s["state"] == ConciergeState.GATHERING_BRIEF.value:
        ok("state-initial-gathering")
    else: fail("state-initial-gathering", str(s))

    # Valid transition
    if await transition(db, pid, ConciergeState.CONFIRMING_SCOPE):
        ok("state-transition-valid")
    else: fail("state-transition-valid")

    # Invalid transition (CONFIRMING_SCOPE → DELIVERED not allowed)
    if not await transition(db, pid, ConciergeState.DELIVERED):
        ok("state-transition-blocks-illegal")
    else: fail("state-transition-blocks-illegal", "illegal transition succeeded")

    # Add required integration
    await add_required_integration(db, pid, "stripe_payments")
    await add_required_integration(db, pid, "expo_eas_build")
    reqs = await get_required_integrations(db, pid)
    if len(reqs) == 2:
        ok("state-required-integrations")
    else: fail("state-required-integrations", str(reqs))

    # Mark one satisfied
    await mark_integration_satisfied(db, pid, "stripe_payments")
    s = await load_state(db, pid)
    if "stripe_payments" in s.get("satisfied_integrations", []) and \
       "stripe_payments" not in s.get("required_integrations", []):
        ok("state-mark-satisfied")
    else: fail("state-mark-satisfied", str(s))

    # History is recorded
    s = await load_state(db, pid)
    if len(s.get("history", [])) >= 1:
        ok("state-history-recorded", f"{len(s['history'])} entries")
    else: fail("state-history-recorded", str(s))

    await db.concierge_state.delete_many({"project_id": pid})


def test_knowledge_base():
    section("3) Knowledge Base — detection + rendering")
    from modules.freebuild.concierge.knowledge import (
        list_integrations, get_integration, detect_required_integrations,
        render_setup_instructions_ar, render_setup_instructions_en,
    )
    integs = list_integrations()
    if len(integs) >= 9:
        ok("kb-list-count", f"{len(integs)} integrations")
    else: fail("kb-list-count", f"only {len(integs)}")

    eas = get_integration("expo_eas_build")
    if eas and eas.get("required_credentials"):
        ok("kb-get-eas")
    else: fail("kb-get-eas")

    # Arabic detection
    detected = detect_required_integrations("أبي تطبيق موبايل مع stripe", "ar")
    if "expo_eas_build" in detected and "stripe_payments" in detected:
        ok("kb-detect-arabic", str(detected))
    else: fail("kb-detect-arabic", str(detected))

    # English detection
    detected = detect_required_integrations("I need mobile app with payments", "en")
    if "expo_eas_build" in detected and "stripe_payments" in detected:
        ok("kb-detect-english", str(detected))
    else: fail("kb-detect-english", str(detected))

    # Empty input
    if detect_required_integrations("", "ar") == []:
        ok("kb-empty-input")
    else: fail("kb-empty-input")

    # Render AR
    ar = render_setup_instructions_ar("expo_eas_build")
    if "إعداد" in ar and "expo.dev" in ar and "Apple" in ar:
        ok("kb-render-ar")
    else: fail("kb-render-ar", ar[:200])

    # Render EN
    en = render_setup_instructions_en("liveblocks_realtime")
    if "Setup" in en and "liveblocks.io" in en:
        ok("kb-render-en")
    else: fail("kb-render-en", en[:200])


def test_setup_wizard():
    section("4) Setup Wizard — card builders")
    from modules.freebuild.concierge.setup_wizard import (
        card_intro, card_key_input, card_checklist, card_success,
        card_cost_summary, card_skip_alternative, build_wizard_flow,
    )
    intro = card_intro("expo_eas_build", "ar")
    if intro.get("card_type") == "setup_intro" and intro.get("integration_id") == "expo_eas_build":
        ok("wizard-intro-card")
    else: fail("wizard-intro-card", str(intro))

    from modules.freebuild.concierge.knowledge import get_integration
    eas = get_integration("expo_eas_build")
    ki = card_key_input("expo_eas_build", eas["required_credentials"][0], "ar")
    if ki["card_type"] == "key_input_validate" and "validation_endpoint" in ki:
        ok("wizard-key-input-card")
    else: fail("wizard-key-input-card", str(ki))

    chk = card_checklist("x", ["step1"], ["step2", "step3"], "ar")
    if len(chk["steps"]) == 3 and chk["steps"][0]["done"] is True:
        ok("wizard-checklist-card")
    else: fail("wizard-checklist-card", str(chk))

    succ = card_success("expo_eas_build", {"account": "test"}, "ar")
    if succ["card_type"] == "setup_success":
        ok("wizard-success-card")
    else: fail("wizard-success-card")

    cost = card_cost_summary(["expo_eas_build", "stripe_payments"], "ar")
    if len(cost.get("items", [])) == 2:
        ok("wizard-cost-summary")
    else: fail("wizard-cost-summary", str(cost))

    skip = card_skip_alternative("openai_api", "استخدم مفتاحنا المجاني", "Use our free key")
    if skip["card_type"] == "skip_alternative":
        ok("wizard-skip-alt")
    else: fail("wizard-skip-alt")

    flow = build_wizard_flow("stripe_payments", "ar")
    if len(flow) >= 2:  # intro + at least one key input
        ok("wizard-full-flow", f"{len(flow)} cards")
    else: fail("wizard-full-flow", str(flow))


async def test_validators():
    section("5) Validators — format checks (no API calls)")
    from modules.freebuild.concierge.validators import (
        validate_liveblocks_key, validate_stripe_secret, validate_mapbox_token,
        validate_openai_key, validate_resend_key, validate_by_key_name,
    )

    r = await validate_liveblocks_key("invalid_format")
    if not r["valid"] and "صيغة" in r["message"]:
        ok("validate-liveblocks-bad-format")
    else: fail("validate-liveblocks-bad-format", str(r))

    r = await validate_stripe_secret("notakey")
    if not r["valid"]:
        ok("validate-stripe-bad-format")
    else: fail("validate-stripe-bad-format", str(r))

    r = await validate_mapbox_token("invalid")
    if not r["valid"]:
        ok("validate-mapbox-bad-format")
    else: fail("validate-mapbox-bad-format")

    r = await validate_openai_key("invalid")
    if not r["valid"]:
        ok("validate-openai-bad-format")
    else: fail("validate-openai-bad-format")

    r = await validate_resend_key("invalid")
    if not r["valid"]:
        ok("validate-resend-bad-format")
    else: fail("validate-resend-bad-format")

    # Dispatch
    r = await validate_by_key_name("UNKNOWN_KEY", "anything")
    if r["valid"]:
        ok("validate-dispatch-unknown-allows")
    else: fail("validate-dispatch-unknown-allows", str(r))


async def test_executors():
    section("6) Executors — enqueue + render")
    from modules.freebuild.executors.webcontainer_executor import (
        enqueue_execution, render_webcontainer_html_wrapper, get_task_result,
        post_task_result,
    )
    from modules.freebuild.executors.pyodide_executor import (
        enqueue_python, render_pyodide_html_wrapper,
    )
    db = await _db()
    uid = f"exec_{uuid.uuid4().hex[:6]}"

    # WebContainer
    r = await enqueue_execution(db, uid, "p1", "console.log('hi')", entry_command="node index.js")
    if r["task_id"] and r["status"] == "queued":
        ok("webcontainer-enqueue")
    else: fail("webcontainer-enqueue", str(r))
    task = await get_task_result(db, r["task_id"])
    if task and task["status"] == "queued":
        ok("webcontainer-task-fetch")
    else: fail("webcontainer-task-fetch")

    html = render_webcontainer_html_wrapper(r["task_id"], {"index.js": "console.log('hi')"}, "node index.js")
    if "WebContainer" in html and "esm.sh/@webcontainer/api" in html:
        ok("webcontainer-render-html")
    else: fail("webcontainer-render-html", html[:200])

    # Simulate result post
    ok_post = await post_task_result(db, r["task_id"], {"status": "done", "stdout": "hi\n"})
    task = await get_task_result(db, r["task_id"])
    if ok_post and task["status"] == "done":
        ok("webcontainer-post-result")
    else: fail("webcontainer-post-result", str(task))

    # Pyodide
    r = await enqueue_python(db, uid, "p1", "print(2+2)", packages=[])
    if r["task_id"]:
        ok("pyodide-enqueue")
    else: fail("pyodide-enqueue")

    html = render_pyodide_html_wrapper(r["task_id"], "print(2+2)", [])
    if "loadPyodide" in html and "Pyodide" in html:
        ok("pyodide-render-html")
    else: fail("pyodide-render-html")

    # Cleanup
    await db.execution_tasks.delete_many({"user_id": uid})


def test_eas_liveblocks_signatures():
    section("7) EAS / Liveblocks / E2B / SSH — module shape")
    from modules.freebuild.executors.eas_build import (
        get_user_info, trigger_build, get_build_status, wait_for_build,
        render_user_instructions_ar,
    )
    instructions = render_user_instructions_ar("build-123", "android", "https://expo.dev/builds/123")
    if "بناء التطبيق" in instructions and "android" in instructions:
        ok("eas-instructions-ar")
    else: fail("eas-instructions-ar")

    from modules.freebuild.executors.liveblocks_integrator import (
        auth_endpoint_fastapi, react_provider_snippet, live_cursors_component,
        live_presence_component, package_json_deps, render_full_integration_files,
    )
    auth = auth_endpoint_fastapi()
    if "liveblocks" in auth.lower() and "FastAPI" in auth or "APIRouter" in auth:
        ok("liveblocks-auth-fastapi")
    else: fail("liveblocks-auth-fastapi", auth[:200])

    cursors = live_cursors_component()
    if "useOthers" in cursors and "useMyPresence" in cursors:
        ok("liveblocks-cursors")
    else: fail("liveblocks-cursors")

    files = render_full_integration_files()
    if len(files) >= 4 and any(".tsx" in f for f in files.keys()):
        ok("liveblocks-files", f"{len(files)} files")
    else: fail("liveblocks-files", str(list(files.keys())))

    deps = package_json_deps()
    if "@liveblocks/react" in deps:
        ok("liveblocks-deps")
    else: fail("liveblocks-deps")

    from modules.freebuild.executors.e2b_executor import (
        create_sandbox, run_command, write_file, kill_sandbox, run_full_workflow,
    )
    # Just verify they're callable
    if callable(create_sandbox) and callable(run_full_workflow):
        ok("e2b-callables")
    else: fail("e2b-callables")

    from modules.freebuild.executors.ssh_executor import test_connection, run_remote, run_workflow
    if callable(test_connection) and callable(run_remote):
        ok("ssh-callables")
    else: fail("ssh-callables")


async def test_endpoints_live():
    section("8) HTTP Endpoints — live calls")
    import httpx
    async with httpx.AsyncClient(base_url="http://localhost:8001", timeout=15) as cl:
        r = await cl.get("/api/concierge/integrations/list")
        if r.status_code == 200 and r.json().get("count", 0) >= 9:
            ok("endpoint-integrations-list")
        else: fail("endpoint-integrations-list", f"{r.status_code} {r.text[:100]}")

        r = await cl.get("/api/concierge/integrations/expo_eas_build?language=ar")
        if r.status_code == 200 and "instructions_ar" in r.json():
            ok("endpoint-integration-detail")
        else: fail("endpoint-integration-detail", f"{r.status_code}")

        r = await cl.post("/api/concierge/project/test-e2e/detect-needs",
                          json={"message": "أبي تطبيق موبايل مع stripe", "language": "ar"})
        if r.status_code == 200:
            data = r.json()
            if "expo_eas_build" in data.get("detected", []) and \
               len(data.get("pending_setup", [])) >= 1:
                ok("endpoint-detect-needs")
            else: fail("endpoint-detect-needs", str(data)[:200])
        else: fail("endpoint-detect-needs", f"{r.status_code}")

        r = await cl.get("/api/concierge/project/test-e2e/state")
        if r.status_code == 200 and "state" in r.json():
            ok("endpoint-project-state")
        else: fail("endpoint-project-state")

        r = await cl.get("/api/concierge/project/test-e2e/wizard?language=ar")
        if r.status_code == 200 and "wizard_flow" in r.json():
            ok("endpoint-project-wizard")
        else: fail("endpoint-project-wizard", f"{r.status_code} {r.text[:200]}")


async def main():
    print("\n" + "█" * 60)
    print("█  PHASE 5 — Concierge + Executors Verification")
    print("█" * 60)
    await test_vault()
    await test_state_machine()
    test_knowledge_base()
    test_setup_wizard()
    await test_validators()
    await test_executors()
    test_eas_liveblocks_signatures()
    await test_endpoints_live()
    print("\n" + "█" * 60)
    print(f"█  RESULT: ✅ {P} pass · ❌ {F} fail")
    print("█" * 60)
    if F:
        for f in FAILS: print(f"  - {f}")
        sys.exit(1)
    print("🎉 PHASE 5 GREEN.\n")


if __name__ == "__main__":
    asyncio.run(main())
